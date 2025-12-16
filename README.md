# Vios - Vi Operating System

*A minimal, Vim-inspired file navigator and terminal command runner for your 
terminal.*

Vios is a lightweight, hjkl-powered directory browser that feels like Vim for 
your filesystem. Navigate folders, edit text files in Vim, yank/cut/paste 
files, and run safe shell commands — all without leaving your terminal. It's 
designed for speed and minimalism, perfect for power users.

Built with Python and Curses, Vios turns your terminal into a "Vi Operating 
System" for file management.

## 1. Features

- **Vim Keybindings**: Use `hjkl` to navigate directories and files.
  - `l` / Enter: Enter directory or open text file in Vim.
  - `h`: Go to parent directory.
  - `j` / `k`: Move down/up in the list.
- **Search**: Press `/` for live starts-with search (case-insensitive).
- **Yank/Cut/Delete/Paste**:
  - `yy`: Yank (copy) selected file/dir.
  - `dd`: Cut (copy + delete).
  - Backspace/Delete: Quick delete (no yank).
  - `p`: Paste (with prompt for new name on conflict).
- **Command Mode**: Press `i` to enter `: ` prompt.
  - Run safe commands: `mkdir`, `mv`, `cp`, `rm`, `vim`/`v`.
  - **Tab Auto-Completion**: Press Tab for filename/dir suggestions (cycles 
    on multiple matches).
  - Commands run silently and instantly — no prompts or output screens.
- **Terminal Integration**: Press `t` to open Alacritty in the current 
  directory.
- **Pretty Paths**: Shows `~/path/to/dir` instead of full absolute paths.
- **Minimal & Fast**: No dependencies beyond Python 3 and Alacritty/Vim 
  (optional).

Vios is perfect for Hyprland users — open a terminal with `Super+Return` 
and it starts where you left off in Vios!

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

### 3.2. File Operations:

- yy: Copy.
- dd: Cut.
- Backspace: Delete.
- p: Paste (rename if needed).

### 3.3. Command Mode (i):

- Type commands like : cp old.txt new.txt.
- Tab: Auto-complete filenames/dirs.
- Enter: Run silently.
- Esc: Exit mode.

### 3.4 Open Terminal: 

- t: Launches Alacritty in current dir.
- Quit: Esc.

## 4. Requirements

- Python 3.8+
- Curses (built-in)
- Optional: Vim, Alacritty

## 5. License

MIT License. 



