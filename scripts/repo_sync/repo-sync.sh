#!/usr/bin/env bash
# Script I made for auto-syncing my non-versioning repos.

set -euo pipefail

eval $(/usr/bin/keychain --quiet --eval id_ed25519)
# Put real git URLs here
SCRIPTS_DIR="$HOME/path-scripts"                     # <-- change local repo path
DOCS_DIR="$HOME/path-docs"                           # <-- change local repo path
SCRIPTS_URL="git@github.com:user/path-scripts.git"   # <-- change to git repo
DOCS_URL="git@github.com:user/path-docs.git"         # <-- change to git repo

# Logging
LOG_DIR="$HOME/.local/var/repo-sync"
LOG_FILE="$LOG_DIR/repo-sync.log"
mkdir -p "$LOG_DIR"
exec >>"$LOG_FILE" 2>&1

timestamp() { date +"%F %T"; }

# Global defaults
git config --global pull.rebase true           # rebase pulls by default
git config --global rebase.autoStash true      # auto-stash on rebase
git config --global fetch.prune true           # clean up stale remote branches
git config --global init.defaultBranch main    # ensure main on new repos
git config --global color.ui auto

ensure_repo() {
  local dir="$1" url="$2"
  if [[ ! -d "$dir/.git" ]]; then
    echo "$(timestamp) [INFO] Cloning $url into $dir"
    mkdir -p "$(dirname "$dir")"
    git clone "$url" "$dir"
  fi
}

sync_repo() {
  local dir="$1"
  echo "$(timestamp) [INFO] Sync start: $dir"

  if [[ ! -d "$dir/.git" ]]; then
    echo "$(timestamp) [ERROR] Not a git repo: $dir"
    return 1
  fi

  pushd "$dir" >/dev/null

  # Branch & remote info
  local branch remote_url
  branch="$(git symbolic-ref -q --short HEAD || echo '')"
  remote_url="$(git remote get-url origin 2>/dev/null || echo 'origin-not-set')"
  echo "$(timestamp) [INFO] Remote: $remote_url | Branch: ${branch:-DETACHED}"

  if [[ -z "$branch" ]]; then
    echo "$(timestamp) [ERROR] Detached HEAD; skipping auto-commit/push"
    popd >/dev/null
    return 1
  fi

  # Avoid committing in the middle of a merge/rebase
  if [[ -e .git/MERGE_HEAD || -d .git/rebase-apply || -d .git/rebase-merge ]]; then
    echo "$(timestamp) [WARN] Rebase/Merge in progress; skipping"
    popd >/dev/null
    return 1
  fi

  # Auto-commit if there are changes
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "$(timestamp) [INFO] Auto-committing local changes"
    git add -A
    if ! git commit -m "Auto-sync: $(date +'%F %T')"; then
      echo "$(timestamp) [ERROR] Commit failed (identity? hooks?); aborting repo"
      popd >/dev/null
      return 1
    fi
  else
    echo "$(timestamp) [INFO] Working tree clean; nothing to commit"
  fi

  # Fetch + rebase (autostash protects from any last-second deltas)
  git fetch --all --prune
  git config pull.rebase true >/dev/null
  git config rebase.autoStash true >/dev/null

  echo "$(timestamp) [INFO] Rebasing onto origin/$branch"
  if ! git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
    echo "$(timestamp) [INFO] No upstream set; setting to origin/$branch"
    git branch --set-upstream-to="origin/$branch" "$branch" 2>/dev/null || true
  fi

  git pull --rebase || {
    echo "$(timestamp) [WARN] Rebase failed; aborting and trying fast-forward"
    git rebase --abort || true
    git pull --ff-only || {
      echo "$(timestamp) [ERROR] Unable to fast-forward; manual resolution required"
      popd >/dev/null
      return 1
    }
  }

  # Push
  echo "$(timestamp) [INFO] Pushing $branch"
  if ! git push -u origin "$branch"; then
    echo "$(timestamp) [ERROR] Push failed (auth/upstream?)"
    popd >/dev/null
    return 1
  fi

  echo "$(timestamp) [INFO] Sync done: $dir"
  popd >/dev/null
}


# MAIN
echo "============================================================"
echo "$(timestamp) [INFO] repo-sync started (PID $$)"

ensure_repo "$SCRIPTS_DIR" "$SCRIPTS_URL"
ensure_repo "$DOCS_DIR"    "$DOCS_URL"

sync_repo "$SCRIPTS_DIR" || true
sync_repo "$DOCS_DIR"    || true

echo "$(timestamp) [INFO] repo-sync finished"
