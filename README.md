# o

`o` is a lightweight, Vim-inspired directory browser for your terminal.
Navigate directories, open files in your preferred editor, create new files,
yank/cut/ paste, and launch terminals — all from a fast curses interface. By
default `o` opens in a “Matrix” inspired view where each filesystem entry
appears as a falling column; you can toggle back to the classic list view
whenever you like.

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
  - `,xr` — Toggle inline expansion/collapse for the selected item
  - `,xc` — Collapse all inline expansions in the current view
  - `,xar` — Expand every directory (recursively) in view
  - `,dot` — Toggle dotfile visibility
  - `,conf` — Open your config in Vim and reload it
  - `,j` / `,k` — Jump to bottom/top instantly
  - `,sa` / `,sma` / `,smd` — Sorting shortcuts
  - `,nf` — Create new file (no open)
  - `,nd` — Create new directory
  - `,rn` — Rename selected item
  - `,b` — Toggle bookmark for the current directory
  - `,cl` — Clear clipboard contents
  - `,cm` — Clear all marks
- **Repeat commands**
  - `.` — Repeat the last repeatable command (`m`, `p`, `,xr`, `,xar`, `,dot`, `,conf`, `,nf`, `,nd`, `,rn`, `,b`)
- **Powerful Filtering** (glob-style):
  - `/` — Enter filter mode
    - Type pattern (e.g., `rat`, `*.py`, `*test*`)
    - Implicit `*` at end if no wildcards used
    - Press `Enter` to apply and persist
    - Press `/` again or `Esc` to cancel/clear
  - `Ctrl+R` — Clear filter instantly
- **Clipboard Operations**:
  - `m` — Toggle mark to build a multi-select batch
  - `y` — Yank all marked items into the clipboard immediately
  - `yy` — Yank the current row into the clipboard
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
- `,xr`: Toggle inline expansion/collapse for the selection.
- `,xc`: Collapse all inline expansions while staying in the current directory.
- `,xar`: Expand every directory under the current view.
- `Ctrl+H` / `Ctrl+L`: Jump backward/forward through directory history.
- `Esc`: Collapse inline expansions under the current directory.
- `~`: Collapse all expansions and return to `~`.

### File Operations

- `y`: Copy all marked items to the clipboard in one step.
- `yy`: Copy the current row to the clipboard when nothing is marked.
- `dd`: Cut the current row or marked items to the clipboard.
- `p`: Paste the clipboard into the selected directory (or alongside the selected file).
- `x`: Delete marked items or the current selection immediately (no clipboard).
- `m`: Toggle mark on the current item (auto-advances the cursor).

### Visual Mode

- v: Enter visual mode at the cursor. Press v again to append the highlighted range to the marked set (repeat for multiple ranges).
- j / k: Extend or shrink the active visual selection when you are in list mode.
- Matrix mode automatically freezes any streams included in the current visual selection (and the focused stream) so they stay in view.
- Esc: Exit visual mode without adding the current range.

### Command Mode (`:`)

- Press `:` to enter command mode.
- Run shell commands with `:!<command>` (executed in the directory you've navigated to).
- `Enter` runs the command; `Esc` cancels.
- Command output appears in a popup; use `j` / `k` to scroll and `Esc` to close.

### Open Terminal & Config

- `t`: Launches Alacritty in the current directory.
- `,conf`: Opens your `o` config file in Vim, then reloads it when you exit Vim.

### Quit

- `q`: Quit the application.
- `Ctrl+C`: Force quit.

### Repeat commands

- `.`: Repeat the last repeatable command (`m`, `p`, `,xr`, `,xar`, `,dot`, `,conf`, `,nf`, `,nd`, `,rn`, `,b`).

### Leader Commands (press `,` first)

- ,xr: Toggle inline expansion/collapse for the current selection.
- ,xc: Collapse all inline expansions.
- ,xar: Expand every directory (recursively) in the current view.
- ,dot: Toggle dotfile visibility.
- ,conf: Open the config in Vim and reload it into the running session.
- ,j / ,k: Jump to bottom/top instantly.
- ,sa / ,sma / ,smd: Sort alphabetically, by modified date ascending, or descending.
- ,nf / ,nd: Create a new file / directory without opening it.
- ,rn: Rename the currently selected item.
- ,b: Toggle a bookmark for the current directory.
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
defaults. A reference configuration is included below for convenience.

Supported options:

- `matrix_mode` — `true` / `false`. Controls whether Matrix view is the default
  when the app launches.
- `handlers` — map of programs to launch for specific file types. Each entry can
  be either the legacy list-of-commands or the richer object form shown below.
  ```json
  {
    "handlers": {
      "pdf_viewer": { "commands": [["zathura"]] },
      "image_viewer": { "commands": [["swayimg"]] },
      "csv_viewer": { "commands": [["vixl"]], "is_internal": true },
      "parquet_viewer": { "commands": [["vixl"]], "is_internal": true },
      "editor": { "commands": [["vim"]] }
    }
  }
  ```
  - Each sub-array under `commands` represents a command to try (with optional
    arguments). If a command does **not** include `{file}`, the file path is appended.
  - `is_internal: true` runs the handler inside `o` (the TUI suspends until the
    command exits). Leave it as `false` or omit it to launch the command in a
    new terminal or background process, preserving the existing UI behaviour.
  - `pdf_viewer` and `image_viewer` control the viewers for PDFs and images.
  - `csv_viewer` and `parquet_viewer` default to external terminals; flip
    `is_internal` to `true` if you prefer terminal-native tools that should take
    over the current UI.
  - `editor` (optional) overrides the fallback editor used for other files.
If a handler command or mapping is missing, `o` simply leaves the file unopened.
Configure viewers/editors explicitly to control how files launch.

Reference template:

```json
{
  "matrix_mode": false,
  "handlers": {
    "pdf_viewer": { "commands": [["evince"]] },
    "image_viewer": { "commands": [["feh"]] },
    "csv_viewer": { "commands": [["libreoffice", "--calc"]] },
    "parquet_viewer": { "commands": [["db-browser-for-sqlite"]] }
  }
}
```

### Example configuration explained

Below is a sample configuration along with plain-language notes so you can
adapt it to your own tools and directory structure:

```json
{
  "matrix_mode": true,
  "handlers": {
    "pdf_viewer": { "commands": [["evince"]] },
    "image_viewer": { "commands": [["feh"]] },
    "csv_viewer": { "commands": [["libreoffice", "--calc"]] },
    "parquet_viewer": { "commands": [["db-browser-for-sqlite"]] }
  }
}
```

- `matrix_mode: true` launches `o` in the animated Matrix layout. Set it to
  `false` if you prefer the classic list by default.
- `handlers` define which programs open specific file types. In the example we
  use the object form, where each entry exposes a `commands` array (list of
  command arrays) and optional `is_internal` flag. `{file}` placeholders are
  replaced automatically; if a command omits `{file}`, the file path is appended.
  - `pdf_viewer`: opens PDFs with Evince.
  - `image_viewer`: opens images in Feh.
  - `csv_viewer`: sends CSV files to LibreOffice Calc.
  - `parquet_viewer`: launches a Parquet-friendly tool (replace with whatever you
    use).
  - Set `is_internal` to `true` for terminal-native tools that should replace the
    current `o` UI until they exit (e.g. `vixl`, `less`, `bat`).
Feel free to swap out the sample applications (Evince, Feh, LibreOffice, etc.)
with whatever viewers and editors you have installed.
