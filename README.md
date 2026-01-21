# o

`o` is a lightweight, Vim-inspired directory browser for your terminal. Navigate
directories, open files in your preferred editor, create new files, yank/cut/
paste, and launch terminals — all from a clean, fast curses interface.

Built with Python and curses, `o` turns your terminal into a "Vi-like Operating
System" focused purely on efficient file management.

---

## Installation

### Prebuilt binary (Linux x86_64)

`o` publishes PyInstaller bundles with each GitHub release. The quickest way to
install the latest release is via the helper script:

```bash
curl -fsSL https://raw.githubusercontent.com/ryangerardwilson/o/main/install.sh | bash
```

The script downloads the `o-linux-x64.tar.gz` artifact, extracts it into
`~/.o/app`, and drops a shim in `~/.o/bin`. It will attempt to add that
directory to your `PATH` (unless you opt out) so you can just run `o` from any
shell.

Installer flags of note:

- `--version <x.y.z>` or `-v <x.y.z>`: install a specific tagged release
  (`v0.3.0`, etc.).
- `--version` (no argument): print the latest available release version without
  installing.
- `--upgrade`: reinstall only if GitHub has a newer release than your current
  local version.
- `--binary /path/to/o-linux-x64.tar.gz`: install from a previously downloaded
  archive.
- `--no-modify-path`: skip auto-updating shell config files; the script will
  print the PATH export you should add manually.

Once installed, the binary itself also supports:

- `o -v` to print the installed version
- `o -u` to reinstall via the latest installer script if a newer release exists

You can also download the archive directly from the releases page and run
`install.sh --binary` if you prefer.

### From source

If you’d rather run directly from the repo (handy for development or non-Linux
hosts), clone the repository and launch `python main.py` directly:

```bash
git clone https://github.com/ryangerardwilson/o.git
cd o
python main.py
```

---

## Features

- **Vim-style Navigation**:
  - `h` — Go to parent directory (resets filter)
  - `l` / `Enter` — Enter directory or open file
  - `j` / `k` — Move down/up in selection
  - `Ctrl+J` / `Ctrl+K` — Jump roughly 10% down/up the list
  - `e` — Expand/collapse the selected directory inline
  - `Ctrl+H` / `Ctrl+L` — Go backward/forward through directory history
  - `Esc` — Collapse all expansions and return to `~`
- **Leader Commands (press `,` first)**:
  - `,j` / `,k` — Jump to bottom/top instantly
  - `,sa` / `,sma` / `,smd` — Sorting shortcuts
  - `,nf` — Create new file (no open)
  - `,nd` — Create new directory
  - `,rn` — Rename selected item
  - `,cp` — Copy `cd` command for current path to system clipboard
  - `,cl` — Clear clipboard contents
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
  - `p` — Paste the clipboard into the selected directory (or next to the selected file)
- **Visual Mode**:
  - `v` — Enter visual mode anchored at the current row; press `v` again to add the highlighted range to your marks (supports multiple ranges)
  - `j` / `k` — Extend or shrink the selection while in visual mode
  - `Esc` — Exit visual mode without adding the selection
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

---

## Usage

### Navigation

- j/k: Up/down.
- h: Parent dir.
- l/Enter: Enter dir or open file in Vim.
- /: Search (type to filter, Enter to open).
- Ctrl+J / Ctrl+K: Jump down/up quickly.
- e: Expand/collapse selected directory inline.
- Ctrl+H / Ctrl+L: Jump backward/forward through directory history.
- Esc: Collapse all expansions and return to `~`.

### File Operations

- yy: Copy.
- dd: Cut.
- Backspace: Delete.
- p: Paste into the selected directory (or alongside the selected file).

### Visual Mode

- v: Enter visual mode at the cursor. Press v again to append the highlighted range to the marked set (repeat for multiple ranges).
- j / k: Extend or shrink the active visual selection.
- Esc: Exit visual mode without adding the current range.

### Command Mode (`i`)

- Type commands like : cp old.txt new.txt.
- Tab: Auto-complete filenames/dirs.
- Enter: Run silently.
- Esc: Exit mode.

### Open Terminal

- t: Launches Alacritty in current dir.
- Quit: Esc.

### Leader Commands (press `,` first)

- ,j / ,k: Jump to bottom/top instantly.
- ,sa / ,sma / ,smd: Sort alphabetically, by modified date ascending, or descending.
- ,nf: Create new file (no open).
- ,nd: Create new directory.
- ,rn: Rename the currently selected item.
- ,cp: Copy a `cd` command for the current directory to the system clipboard.
- ,cl: Clear the multi-item clipboard buffer.

---

## Requirements

- Python 3.8+
- Curses (built-in)
- Optional: Vim, Alacritty

---

## License

MIT License.
