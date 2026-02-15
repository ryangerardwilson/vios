# o

o is a lightweight, Vim-inspired directory browser for your terminal. Navigate
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

The installer also creates a desktop entry for reveal mode and sets it as the
default handler for directories and file URLs (so "Show in folder" can open `o`
in a terminal).

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
python main.py /path/to/start/dir
```

## Usage

### Reveal mode

Open a folder and highlight a target item (useful for "Show in folder"
integrations):

```bash
o -r /path/to/file
o -r /path/to/folder
o -r file:///path/to/file
```

- `-r <path>`: start in the parent directory (or the directory itself) and focus the target item.
- Reveal mode always starts in list view. If `o` is launched without a TTY, it
  spawns a detached terminal automatically.

### Picker mode

Use picker mode when another app needs a file or directory selection via the
terminal UI. Use save mode to pick a target path for saving.

```bash
o -p
o -p ~/Downloads
o -p ~/Downloads -ld
o -p ~/Downloads -lf "png,jpeg,JPG,PNG"
o -s ~/Documents -lf "gtkv.html"
```

- `-p [dir]`: start picker mode (defaults to `~/` if omitted).
- `-s [dir]`: save mode (pick a destination path).
- `-ld`: limit selection to directories only.
- `-lf [exts]`: limit selection to files only; optional comma/semicolon separated extensions.
- `-m`: allow multi-select via marks (outputs all marked items).

Picker mode always starts in list view. Use `Enter` to confirm the selection
and `q` to cancel.

Selections are printed to stdout and also written to `~/.cache/o/picker-
selection.txt` (or `${XDG_CACHE_HOME}/o/picker-selection.txt`).

Note: GNOME/Chrome file picker dialogs cannot be replaced with a terminal UI.
Use reveal mode for "Show in folder" flows, and save mode for post-download
moves.

### App developer integration

Use `o` as a lightweight picker/save UI from other apps by launching it in a
terminal and reading the selection from stdout or the cache file. Picker and
save modes both emit the final path(s) the same way.

Picker route (`-p`):

```bash
o -p
o -p ~/Downloads
o -p ~/Downloads -ld
o -p ~/Downloads -lf "png,jpeg,JPG,PNG"
o -p ~/Downloads -m
```

- `-p [dir]` starts picker mode; defaults to `~/` if omitted.
- `-ld` restricts selection to directories only.
- `-lf [exts]` restricts selection to files only; optional comma/semicolon list.
- `-m` enables multi-select output (one path per line).

Save route (`-s`):

```bash
o -s
o -s ~/Documents
o -s ~/Documents -se "gtkv.html"
```

- `-s [dir]` starts save mode; defaults to `~/` if omitted.
- `-se [exts]` optionally suggests/forces a save extension (comma/semicolon list).
  If omitted, any extension is accepted.

Selection delivery:

- `stdout`: `o` prints the selected path(s), one per line.
- Cache file: `~/.cache/o/picker-selection.txt`
  (or `${XDG_CACHE_HOME}/o/picker-selection.txt`).
- When multi-select is enabled, the cache file contains all selected paths.

## Shortcuts and commands

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
- `x`: Prompt to delete marked items or the current selection (type `y` then `Enter` to confirm).
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
- Command and execution output appear in a popup; use `j` / `k` to scroll line by line, `Ctrl+J` / `Ctrl+K` for larger jumps, and `,j` / `,k` to jump to end/start. `Esc` cancels a running job or closes the popup once finished.

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
- `executors` — optional commands used by the `e` shortcut. Provide `python`
  (list or string) for `.py` files and `shell` for extensionless executables. If
  omitted, `o` will attempt to discover a Python interpreter and fall back to
  `/bin/bash -lc` for shell execution.
  ```json
  {
    "handlers": {
      "pdf_viewer": { "commands": [["zathura"]] },
      "image_viewer": { "commands": [["swayimg"]] },
      "csv_viewer": { "commands": [["vixl"]], "is_internal": true },
      "parquet_viewer": { "commands": [["vixl"]], "is_internal": true },
      "h5_viewer": { "commands": [["h5ls"]], "is_internal": true },
      "xlsx_viewer": { "commands": [["libreoffice", "--calc"]] },
      "editor": { "commands": [["vim"]] }
    },
    "executors": {
      "python": "/home/ryan/Venv/bin/python",
      "shell": "/bin/bash -lc"
    }
  }
  ```
  - Each sub-array under `commands` represents a command to try (with optional
    arguments). If a command does **not** include `{file}`, the file path is appended.
  - `is_internal: true` runs the handler inside `o` (the TUI suspends until the
    command exits). Leave it as `false` or omit it to launch the command in a
    new terminal or background process, preserving the existing UI behaviour.
  - `pdf_viewer` and `image_viewer` control the viewers for PDFs and images.
  - `csv_viewer`, `parquet_viewer`, and `h5_viewer` default to external terminals;
    flip `is_internal` to `true` if you prefer terminal-native tools that should
    take over the current UI.
  - `xlsx_viewer` opens `.xlsx` spreadsheets.
  - `editor` (optional) overrides the fallback editor used for other files.
- `executors` configure the `e` shortcut; omit to let `o` discover interpreters automatically.
  - Works best for non-interactive scripts. Programs that expect an attached TTY, background daemons, or long-running TUIs are better launched via your terminal directly.
If a handler command or mapping is missing, `o` simply leaves the file
unopened. Configure viewers/editors explicitly to control how files launch.

Reference template:

```json
{
  "matrix_mode": false,
  "handlers": {
    "pdf_viewer": { "commands": [["evince"]] },
    "image_viewer": { "commands": [["feh"]] },
    "csv_viewer": { "commands": [["libreoffice", "--calc"]] },
    "parquet_viewer": { "commands": [["db-browser-for-sqlite"]] },
    "h5_viewer": { "commands": [["h5ls"]], "is_internal": true },
    "xlsx_viewer": { "commands": [["libreoffice", "--calc"]] }
  },
  "executors": {
    "python": "/usr/bin/python3",
    "shell": "/bin/bash -lc"
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
    "parquet_viewer": { "commands": [["db-browser-for-sqlite"]] },
    "h5_viewer": { "commands": [["h5ls"]], "is_internal": true },
    "xlsx_viewer": { "commands": [["libreoffice", "--calc"]] }
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
  - `h5_viewer`: opens `.h5` files (example uses `h5ls` inside the terminal).
  - `xlsx_viewer`: opens `.xlsx` files (example uses LibreOffice Calc).
  - Set `is_internal` to `true` for terminal-native tools that should replace the
    current `o` UI until they exit (e.g. `vixl`, `less`, `bat`).
Feel free to swap out the sample applications (Evince, Feh, LibreOffice, etc.)
with whatever viewers and editors you have installed.
