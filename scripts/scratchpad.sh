#!/usr/bin/env bash
# Project manager
# Projects in ~/scratchpad/<name>
# Active symlink at ~/current
# Screenshots to ~/current/screens

set -euo pipefail

BASE="$HOME/scratchpad"
LINK="$HOME/current"
mkdir -p "$BASE"

usage() {
  cat <<'EOF'
Usage:
  scratchpad.sh init [--force] [--no-relink] <name>   Create project and point ~/current to it
  scratchpad.sh link <name>                            Point ~/current to existing project
  scratchpad.sh list                                   List projects (mark current with *)
  scratchpad.sh shot                                   Flameshot to ~/current/screens

Options (init):
  -f, --force     Reuse existing directory if it already exists
  --no-relink     Create project but do not modify ~/current
EOF
}

# Helpers

safe_link() {
  local target="$1" link="$2"
  # don't clobber a real directory at ~/current
  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "[!] $link exists and is NOT a symlink. Move/rename it first." >&2
    exit 1
  fi
  ln -sfn "$target" "$link"   # replace existing symlink
}

mkfile_if_absent() {
  local path="$1" content="${2:-}"
  if [[ ! -e "$path" ]]; then
    mkdir -p "$(dirname "$path")"
    printf "%s" "$content" > "$path"
  fi
}

# Vommands

init_project() {
  local force=0 norelink=0 name=""
  # parse flags for this subcommand
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--force) force=1; shift ;;
      --no-relink) norelink=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) name="$1"; shift ;;
    esac
  done

  [[ -z "${name:-}" ]] && { echo "[!] Project name required"; exit 1; }

  local proj="$BASE/$name"

  if [[ -d "$proj" ]]; then
    if (( force==0 )); then
      echo "[!] $proj already exists. Use --force to reuse." >&2
      exit 1
    fi
  else
    mkdir -p "$proj"/{logs,assets,src,data,screens}
  fi

  # Starter files
  mkfile_if_absent "$proj/README.md" "# $name"
  mkfile_if_absent "$proj/notes.md"  "## Notes"
  mkfile_if_absent "$proj/logs/commands.log" ""

  if (( norelink==0 )); then
    safe_link "$proj" "$LINK"
    echo "[+] Project ready: $proj"
    echo "[+] Symlink set:  $LINK -> $proj"
  else
    echo "[+] Project created: $proj (not relinked)"
  fi
}

link_project() {
  local name="${1:-}"
  [[ -z "$name" ]] && { echo "[!] Project name required"; exit 1; }

  local proj="$BASE/$name"
  [[ -d "$proj" ]] || { echo "[!] $proj does not exist"; exit 1; }

  safe_link "$proj" "$LINK"
  echo "[+] Symlink set: $LINK -> $proj"
}

list_projects() {
  shopt -s nullglob
  for d in "$BASE"/*; do
    [[ -d "$d" ]] || continue
    local mark=""
    if [[ -L "$LINK" && "$(readlink -f "$LINK")" == "$(readlink -f "$d")" ]]; then
      mark=" *"
    fi
    echo "$(basename "$d")$mark"
  done
}

take_screenshot() {
  [[ -L "$LINK" ]] || { echo "[!] No active project (~/current). Use init/link."; exit 1; }
  command -v flameshot >/dev/null || { echo "[!] flameshot not installed"; exit 1; }

  local proj dir file relpath
  proj="$(readlink -f "$LINK")"
  dir="$proj/screens"
  mkdir -p "$dir"
  file="$dir/$(date +%Y%m%d-%H%M%S).png"

  flameshot gui -p "$file" || { echo "[!] flameshot canceled"; return; }

  # relative path for Markdown
  relpath="screens/$(basename "$file")"

  # append to notes.md
  echo -e "\n![screenshot]($relpath)" >> "$proj/notes.md"

  echo "[+] Screenshot saved: $file"
  echo "[+] Linked in: $proj/notes.md"
}


# Dispatcher

cmd="${1:-}"; shift || true
case "$cmd" in
  init) init_project "$@" ;;
  link) link_project "$@" ;;
  list) list_projects ;;
  shot) take_screenshot ;;
  -h|--help|"") usage ;;
  *) echo "[!] Unknown command: $cmd"; usage; exit 1 ;;
esac
