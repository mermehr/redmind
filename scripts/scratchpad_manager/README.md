# Scratchpad Manager

This evolved into my [Anneses](https://github.com/mermehr/annexes) script.

Simple **bash-based project scratchpad manager** for creating workspaces. Keeps projects organized, tracks the current active workspace with a symlink, and integrates screenshots directly into notes.

---

## Features

- Projects live under `~/scratchpad/<name>`

- Active project symlink at `~/current`

Pre-populated structure:

        README.md
        notes.md
        TODO.md
        logs/commands.log
        assets/
        src/
        data/
        screens/

- `flameshot` integration:
  - Screenshots saved into `~/current/screens/`
  - Automatically appended to `~/current/notes.md` as Markdown image
      links

---

## Installation

Save the script to `~/bin/scratchpad`:

```bash
chmod +x scratchpad.sh
mv scratchpad.sh ~/bin/scratchpad
```

(Make sure `~/bin` is in your `$PATH`.)

Install [flameshot](https://flameshot.org/) if not already installed:

```bash
sudo apt install flameshot
```

---

## Usage

```bash
scratchpad <command> [options] [name]
```

### Commands

- `init <name>` - Create new project under  `~/scratchpad/<name>` and point `~/current` to it.
- `init --force <name>` - Reuse existing project directory if it  already exists.
- `init --no-relink <name>` - Create project but do not update `~/current`.
- `link <name>` - Point `~/current` to an existing project.
- `list` - List all projects under `~/scratchpad`  (marks the active one with `*`).
- `shot` - Take a screenshot with flameshot, save it in `~/current/screens/`, and append to `~/current/notes.md`.

---

### Examples

```bash
# create new project and activate it
scratchpad init bashed

# list projects
scratchpad list
# output:
# bashed *

# switch active project
scratchpad link filetransfer

# take screenshot into current project
scratchpad shot
# notes.md will now contain:
# ![screenshot](screens/20250826-0610.png)
```

---
