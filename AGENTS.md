# Component Responsibilities

This file lists the single responsibility of each top-level component file.

## Runtime modules
- `_version.py`: defines the runtime version string used by the CLI.
- `main.py`: parses CLI flags and launches the TUI orchestrator.
- `orchestrator.py`: boots curses and drives the main render/input loop.
- `core_navigator.py`: owns navigation state and high-level user actions.
- `directory_manager.py`: lists, filters, sorts, and caches directory entries.
- `clipboard_manager.py`: manages in-app yank/cut/paste staging via temp storage.
- `file_actions.py`: executes file operations, handlers, and command popups.
- `file_actions_terminal_patch.py`: patches terminal launching behavior for file actions.
- `input_handler.py`: maps keypresses to navigation, commands, and edits.
- `ui_renderer.py`: renders list/matrix layouts and status/popup UI.
- `config.py`: loads and normalizes user configuration and executor settings.
- `constants.py`: stores the static cheatsheet content.
- `keys.py`: centralizes keycode constants and helpers.

## Packaging and docs
- `install.sh`: installs or upgrades the packaged binary release.
- `requirements.txt`: declares Python dependencies for source installs.
- `README.md`: documents usage, installation, and configuration.
