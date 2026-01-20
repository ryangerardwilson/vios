# Vios - Vi Operating System

*A minimal, Vim-inspired file navigator for your terminal.*

Vios is a lightweight, hjkl-powered directory browser that feels like Vim for 
filesystem navigation. Navigate directories, open files in your preferred 
editor, create new files, yank/cut/paste, and launch terminals — all from a 
clean, fast curses interface.

Built with Python and curses, Vios turns your terminal into a "Vi-like 
Operating System" focused purely on efficient file management.

## 1. Features

- **Vim-style Navigation**:
  - `h` — Go to parent directory (resets filter)
  - `l` / `Enter` — Enter directory or open file
  - `j` / `k` — Move down/up in selection
  - `Ctrl+J` / `Ctrl+K` — Jump roughly 10% down/up the list
  - `,k` / `,j` — Jump to top/bottom instantly
  - `e` — Expand/collapse the selected directory inline
  - `Ctrl+H` / `Ctrl+L` — Go backward/forward through directory history
- **Powerful Filtering** (glob-style):
  - `/` — Enter filter mode
    - Type pattern (e.g., `rat`, `*.py`, `*test*`)
    - Implicit `*` at end if no wildcards used
    - Press `Enter` to apply and persist
    - Press `/` again or `Esc` to cancel/clear
  - `Ctrl+R` — Clear filter instantly
- **Clipboard Operations**:
  - `m` — Toggle mark to build a multi-select batch
  - `yy` — Yank marked items (or the current row) into the clipboard
  - `dd` — Cut marked items (or the current row) into the clipboard
  - `Backspace` / `Delete` — Immediate cut (delete without yank)
  - `x` — Delete all marked items or the current selection immediately (bypasses clipboard)
  - `p` — Paste the clipboard batch into the current directory
  - `,cl` — Clear clipboard
- **Sorting Controls**:
  - `,sa` — Sort alphabetically (default)
  - `,sma` — Sort by modified date ascending (oldest first)
  - `,smd` — Sort by modified date descending (newest first)
- **File Creation**:
  - `v` — Create new empty file (prompts for filename at bottom)
- **File Opening**:
  - Text files (`.py`, `.txt`, `.md`, etc.) → opened in **Vim**
  - PDF files → opened in **Zathura** (if available)
  - Image files → opened externally via **swayimg**
- **Terminal Integration**:
  - `t` — Open terminal (Alacritty preferred, falls back to default) in current 
    directory
- **Help Screen**:
  - `?` — Toggle full-screen cheatsheet
- **Quit**:
  - `Ctrl+C` — Exit the application
- **Pretty Paths**: Displays `~` for home directory
- **Minimal & Fast**: No external dependencies beyond Python standard library

Perfect for tiling window manager users (Hyprland, sway, etc.) who want a fast,
modal file browser without leaving the terminal.

## 2. Installation

1. Clone the repo:

   git clone https://github.com/ryangerardwilson/vios.git
   cd vios

2. Make main.py executable:

    chmod +x main.py

3. Run Vios:

    ./main.py

## 3. Usage

### 3.1. Navigation:

- j/k: Up/down.
- h: Parent dir.
- l/Enter: Enter dir or open file in Vim.
- /: Search (type to filter, Enter to open).
- Ctrl+J / Ctrl+K: Jump down/up quickly.
- ,j / ,k: Jump to bottom/top.
- e: Expand/collapse selected directory inline.
- Ctrl+H / Ctrl+L: Jump backward/forward through directory history.

### 3.2. File Operations:

- yy: Copy.
- dd: Cut.
- Backspace: Delete.
- p: Paste (rename if needed).
- ,cl: Clear clipboard.

### 3.3. Command Mode (i):

- Type commands like : cp old.txt new.txt.
- Tab: Auto-complete filenames/dirs.
- Enter: Run silently.
- Esc: Exit mode.

### 3.4 Open Terminal: 

- t: Launches Alacritty in current dir.
- Quit: Esc.

### 3.5 Sorting:

- ,sa: Sort alphabetically.
- ,sma: Sort by modified date ascending.
- ,smd: Sort by modified date descending.

## 4. Requirements

- Python 3.8+
- Curses (built-in)
- Optional: Vim, Alacritty

## 5. License

MIT License. 
- History Navigation:

- Ctrl+H: Go to the previously visited directory.
- Ctrl+L: Go to the next directory in history.
