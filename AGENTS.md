# Repository Guidelines

## Project Structure & Module Organization
This repository is a single-package Python TUI app. Top-level modules each have a focused role:
- Entry/runtime: `main.py`, `orchestrator.py`, `_version.py`
- Navigation and state: `core_navigator.py`, `directory_manager.py`, `clipboard_manager.py`
- Actions and input: `file_actions.py`, `file_actions_terminal_patch.py`, `input_handler.py`
- UI and config: `ui_renderer.py`, `config.py`, `constants.py`, `keys.py`
- Packaging/docs: `install.sh`, `requirements.txt`, `README.md`
- Tests live in `tests/` as `test_*.py`.

## Build, Test, and Development Commands
- `python main.py` - run the app from source.
- `python main.py /path/to/start/dir` - start in a specific directory.
- `pytest -q` - run all tests.
- `pytest -q tests/test_input_handler_filter_vim.py` - run one test module.
- `./install.sh -h` - installer usage and release install options.

Use Python 3.8+ and a terminal with curses support.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation.
- Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.
- Keep modules single-responsibility (match existing file boundaries above).
- Prefer small, explicit functions for key handling and file actions; avoid cross-module side effects.
- Keep comments short and only where intent is not obvious from code.

## Testing Guidelines
- Framework: `pytest`.
- Place tests under `tests/` and name files `test_*.py`.
- Name tests by behavior (example: `test_input_handler_paste_target.py`).
- Add or update tests with every behavior change, especially around input handling, config parsing, and file operations.
- Run `pytest -q` before opening a PR.

## Commit & Pull Request Guidelines
- Current history uses short commits (many are `sync`), but contributors should prefer clear, imperative messages (example: `fix: preserve marks after paste`).
- Keep commits focused and logically grouped.
- Include in every PR: a concise behavior summary, linked issue/context when relevant, and test evidence (`pytest -q` summary).
- Add screenshots or terminal recordings when interaction or rendering changes are user-visible.

## Security & Configuration Tips
- Do not commit local paths, secrets, or machine-specific shell settings.
- Keep user-facing defaults in `config.py` safe and reversible.
