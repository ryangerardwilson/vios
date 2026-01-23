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
  - `,xd` — Toggle inline expansion/collapse for the selected item
  - `,j` / `,k` — Jump to bottom/top instantly
  - `,sa` / `,sma` / `,smd` — Sorting shortcuts
  - `,nf` — Create new file (no open)
  - `,nd` — Create new directory
  - `,rn` — Rename selected item
  - `,b` — Toggle bookmark for the current directory
  - `,fo<token>` — Open configured file shortcut (e.g. `,fonotes`)
  - `,do<token>` — Jump to directory shortcut (e.g. `,doga`)
  - `,to<token>` — Open external terminal at shortcut directory (e.g. `,toga`)
  - `,w<token>` — Launch workspace shortcut (open internal + external targets)
  - `,cp` — Copy `cd` command for current path to system clipboard
  - `,cl` — Clear clipboard contents
  - `,cm` — Clear all marks
  - `,i<token>` — Open configured browser shortcut (e.g. `,ix`)
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
- `,xd`: Toggle inline expansion/collapse for the selection.
- `Ctrl+H` / `Ctrl+L`: Jump backward/forward through directory history.
- `Esc`: Collapse inline expansions under the current directory.
- `~`: Collapse all expansions and return to `~`.

### File Operations

- `yy`: Copy the current row or marked items to the clipboard.
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
- `c`: Opens your `o` config file in Vim (creating directories as needed).

### Quit

- `q`: Quit the application.
- `Ctrl+C`: Force quit.

### Leader Commands (press `,` first)

- ,xd: Toggle inline expansion/collapse for the current selection.
- ,j / ,k: Jump to bottom/top instantly.
- ,sa / ,sma / ,smd: Sort alphabetically, by modified date ascending, or descending.
- ,nf / ,nd: Create a new file / directory without opening it.
- ,rn: Rename the currently selected item.
- ,b: Toggle a bookmark for the current directory.
- ,cp: Copy a `cd` command for the current directory to the system clipboard.
- ,cl: Clear the multi-item clipboard buffer.
- ,cm: Clear all marks.
- ,fo<token>: Open configured file shortcuts (e.g. `,fonotes`).
- ,do<token>: Jump to a directory shortcut (e.g. `,doga`).
- ,to<token>: Open a terminal at a directory shortcut (e.g. `,toga`).
- ,w<token>: Launch workspace shortcuts (e.g. `,w1`).
- ,i<token>: Open configured browser shortcut (e.g. `,ix`).

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
- `handlers` — map of external programs to launch for certain file types. Each
  entry is an array of command arrays. Examples:
  ```json
  {
    "handlers": {
      "pdf_viewer": [["zathura"]],
      "image_viewer": [["swayimg"]],
      "csv_viewer": [["vixl"]],
      "parquet_viewer": [["vixl"]],
      "editor": [["vim"]]
    }
  }
  ```
  - Each sub-array represents a command to try (with optional arguments). If a
    command does **not** include `{file}`, the file path is appended.
  - `pdf_viewer` and `image_viewer` control the viewers for PDFs and images.
  - `csv_viewer` and `parquet_viewer` run inside a fresh external terminal. Be
    sure to configure terminal-friendly commands (CLI tools or wrappers like
    `alacritty -e my-viewer`).
  - `editor` (optional) overrides the fallback editor used for other files.
- `file_shortcuts` — map custom tokens (lowercase alphanumeric) to specific files (absolute paths or with `~`).
  Trigger them with `,fo<token>` to open PDFs, images, or any file using your configured handlers (e.g. `,fo1`, `,fokr`).
- `dir_shortcuts` — map custom tokens (alphanumeric) to directories. Trigger with:
  - `,do<token>` to jump inside the directory (e.g. `,doga` → `~/Apps/genie_allocation`)
  - `,to<token>` to launch an external terminal at the directory without changing focus.
- `workspace_shortcuts` — map tokens to an object with optional `internal` and
  `external` entries. Each entry accepts either a path (string) or a list of
  command arrays (e.g. `[ ["worship"] ]`). Paths behave as before; command arrays on the
  `external` side spawn a new terminal and run there, while `internal` command arrays run
  synchronously inside `o`. Trigger with `,w<token>` to open both targets (internal opens
  inside `o`, external launches via handlers/terminal).
- `browser_setup` — configure URL launchers for `,i<token>` shortcuts.
  - `command`: list of command arrays to try when opening URLs. Use `{url}` as a placeholder (if omitted, the URL is appended).
  - `shortcuts`: map tokens to URLs (e.g. `{ "x": "https://x.com" }`). Trigger with `,i<token>`.

If a handler command or mapping is missing, `o` simply leaves the file
unopened. Configure viewers/editors explicitly to control how files launch.

Reference template:

```json
{
  "matrix_mode": false,
  "handlers": {
    "pdf_viewer": [["evince"]],
    "image_viewer": [["feh"]],
    "csv_viewer": [["libreoffice", "--calc"]],
    "parquet_viewer": [["db-browser-for-sqlite"]]
  },
  "file_shortcuts": {
    "guide": "~/Documents/guides/getting-started.pdf",
    "notes": "~/Documents/notes/meeting-notes.md",
    "ref": "~/Documents/reference/api-cheatsheet.pdf"
  },
  "dir_shortcuts": {
    "proj": "~/Projects/alpha",
    "docs": "~/Documents",
    "media": "~/Media"
  },
  "workspace_shortcuts": {
    "docs": {
      "internal": "~/Documents",
      "external": [["alacritty", "--working-directory", "~/Documents"]]
    },
    "analysis": {
      "internal": [["code", "~/Projects/alpha"]],
      "external": [["libreoffice", "~/Documents/data/report.csv"]]
    }
  },
  "browser_setup": {
    "command": [["xdg-open"]],
    "shortcuts": {
      "home": "https://example.com"
    }
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
    "pdf_viewer": [["evince"]],
    "image_viewer": [["feh"]],
    "csv_viewer": [["libreoffice", "--calc"]],
    "parquet_viewer": [["db-browser-for-sqlite"]]
  },
  "file_shortcuts": {
    "guide": "~/Documents/guides/getting-started.pdf",
    "notes": "~/Documents/notes/team-notes.md",
    "ref": "~/Documents/reference/on-call-playbook.pdf"
  },
  "dir_shortcuts": {
    "proj": "~/Projects/alpha",
    "docs": "~/Documents",
    "media": "~/Media"
  },
  "workspace_shortcuts": {
    "docs": {
      "internal": "~/Documents",
      "external": [["alacritty", "--working-directory", "~/Documents"]]
    },
    "analysis": {
      "internal": [["code", "~/Projects/alpha"]],
      "external": [["libreoffice", "~/Documents/data/report.csv"]]
    }
  },
  "browser_setup": {
    "command": [["google-chrome-stable"]],
    "shortcuts": {
      "x": "https://x.com",
      "docs": "https://docs.example.com"
    }
  }
}
```

- `matrix_mode: true` launches `o` in the animated Matrix layout. Set it to
  `false` if you prefer the classic list by default.
- `handlers` define which external programs open specific file types. Each
  inner array is a command you could run in a shell. If the command doesn’t
  contain `{file}`, the file path is appended automatically.
  - `pdf_viewer`: opens PDFs with Evince.
  - `image_viewer`: opens images in Feh.
  - `csv_viewer`: sends CSV files to LibreOffice Calc.
  - `parquet_viewer`: launches a Parquet-friendly tool (replace with whatever you
    use).
- `file_shortcuts` attach friendly names to frequently referenced files and can
  be launched with `,fo<token>` (e.g. `,fonotes`).
- `dir_shortcuts` map quick tokens to directories for navigation (` ,do proj`
  jumps into `~/Projects/alpha`, `,to docs` opens a terminal there).
- `workspace_shortcuts` bundle related actions:
  - `docs` jumps inside `~/Documents` and opens a new terminal in the same
    location.
  - `analysis` runs a code editor pointed at your project and opens LibreOffice
    with a dataset in a separate terminal. Each entry accepts either a direct
    path or an array describing a command (CSV/Parquet commands launch in a
    terminal automatically).
- `browser_setup` defines how URLs launch:
  - `command` lists browser commands to try (each entry is a shell command array; `{url}` is replaced automatically or appended if absent).
  - `shortcuts` map tokens to URLs, making `,i<token>` open the URL in your preferred browser.

Feel free to swap out the sample applications (Evince, Feh, LibreOffice, etc.)
with whatever viewers and editors you have installed.
