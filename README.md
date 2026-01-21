# o

`o` is a lightweight, Vim-inspired directory browser for your terminal. Navigate
directories, open files in your preferred editor, create new files, yank/cut/
paste, and launch terminals — all from a fast curses interface. By default `o`
opens in a “Matrix” inspired view where each filesystem entry appears as a
falling column; you can toggle back to the classic list view whenever you like.

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

- `-v <x.y.z>`: install a specific tagged release (`v0.3.0`, etc.).
- `-v` (no argument): print the latest available release version without
  installing.
- `-u`: reinstall only if GitHub has a newer release than your current local
  version.
- `-b /path/to/o-linux-x64.tar.gz`: install from a previously downloaded
  archive.
- `-h`: show usage information for the installer.
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

- **Dual UI Modes**
  - **Matrix Mode** *(default)*: falling “raindrop” columns for each entry.
    - Streams pause when focused, marked, or included in a visual selection.
    - `h` / `l` move left/right across streams.
    - `j` drills into the focused directory (or opens the file).
    - `k` returns to the parent directory.
    - `Ctrl+H` / `Ctrl+L` page left/right (jump selection).
  - **List Mode**: classic Vim-like list.
    - `j` / `k` move down/up.
    - `h` goes to the parent directory.
    - `l` enters directories or opens files.
    - `Ctrl+J` / `Ctrl+K` jump roughly 10% down/up the list.
  - `Enter` toggles between Matrix and list views at any time.
- **Leader Commands (press `,` first)**
  - `,j` / `,k` — Jump to bottom/top instantly
  - `,sa` / `,sma` / `,smd` — Sorting shortcuts
  - `,nf` — Create new file (no open)
  - `,nd` — Create new directory
  - `,rn` — Rename selected item
  - `,cp` — Copy `cd` command for current path to system clipboard
  - `,cl` — Clear clipboard contents
  - `,cm` — Clear all marks
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
  - `j` / `k` — Extend or shrink the selection while in visual mode (list view)
  - Matrix view freezes any streams included in the active visual selection
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

### Switching views

- `Enter`: Toggle between Matrix (default) and list mode. (Note: use `l` to enter directories; `Enter` no longer opens files.)

### Navigation (Matrix mode)

- `h` / `l`: Move left/right across streams.
- `j`: Enter the focused directory or open the focused file.
- `k`: Return to the parent directory.
- `Ctrl+H` / `Ctrl+L`: Page across streams (10% jump).

### Navigation (List mode)

- `j` / `k`: Move down/up.
- `h`: Parent dir.
- `l`: Enter dir or open file.
- `Ctrl+J` / `Ctrl+K`: Jump down/up quickly.
- `e`: Expand/collapse selected directory inline.
- `Ctrl+H` / `Ctrl+L`: Jump backward/forward through directory history.
- `Esc`: Collapse all expansions and return to `~`.

### File Operations

- yy: Copy.
- dd: Cut.
- Backspace: Delete.
- p: Paste into the selected directory (or alongside the selected file).

### Visual Mode

- v: Enter visual mode at the cursor. Press v again to append the highlighted range to the marked set (repeat for multiple ranges).
- j / k: Extend or shrink the active visual selection when you are in list mode.
- Matrix mode automatically freezes any streams included in the current visual selection (and the focused stream) so they stay in view.
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
- ,cm: Clear all marks.

---

## Requirements

- Python 3.8+
- Curses (built-in)
- Optional: Vim, Alacritty

---

## License

MIT License.

---

## Configuration

`o` reads an optional XDG-compatible config file. Create
`~/.config/o/config.json` (or `${XDG_CONFIG_HOME}/o/config.json`) to adjust the
defaults. A starter `template_config.json` is included in the repository.

Supported options:

- `matrix_mode` — `true` / `false`. Controls whether Matrix view is the default
  when the app launches.
- `handlers` — map of external programs to launch for certain file types. Each
  entry is an array of command arrays. Examples:
  ```json
  {
    "handlers": {
      "pdf_viewer": [["zathura"]],
      "image_viewer": [["swayimg"]],
      "editor": [["nvim", "-c", "cd {file}"], ["vim"]]
    }
  }
  ```
  - Each sub-array represents a command to try (with optional arguments). If a
    command does **not** include `{file}`, the file path is appended.
  - `pdf_viewer` and `image_viewer` control the viewers for PDFs and images.
  - `editor` (optional) overrides the fallback editor used for other files.

If a handler command or mapping is missing, `o` simply leaves the file unopened.
Configure viewers/editors explicitly to control how files launch.

Reference template (`template_config.json`):

```json
{
  "matrix_mode": false,
  "handlers": {
    "pdf_viewer": [["zathura"]],
    "image_viewer": [["swayimg"]]
  }
}
```
