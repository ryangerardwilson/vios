#!/usr/bin/env python3
"""Entry point for the `o` terminal navigator."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse, unquote

import config
from orchestrator import Orchestrator
from core_navigator import PickerOptions
from rgw_cli_contract import AppSpec, resolve_install_script_path, run_app

from _version import __version__

INSTALL_SCRIPT = resolve_install_script_path(__file__)
HELP_TEXT = """o

flags:
  o -h
    show this help
  o -v
    print the installed version
  o -u
    upgrade to the latest release
  o conf
    open config in $VISUAL/$EDITOR

features:
  launch the file navigator from the current directory
  # o
  o

  start from a directory, open one or more files detached, or reveal a path in its parent directory
  # o ~/Downloads | o ~/notes/todo.txt | o a.txt b.txt | o -r ~/Downloads/file.txt
  o ~/Downloads
  o ~/notes/todo.txt
  o a.txt b.txt
  o -r ~/Downloads/file.txt

  run picker or save mode with filters
  # o -p ~/src -lf py,md | o -s ~/Downloads -se txt
  o -p ~/src -lf py,md
  o -s ~/Downloads -se txt
"""

REVEAL_ENV = "O_REVEAL_LAUNCHED"
REVEAL_NO_SPAWN_ENV = "O_REVEAL_NO_SPAWN"

os.environ.setdefault("ESCDELAY", "25")


def _launch_reveal_terminal(reveal_path: str) -> bool:
    return _launch_terminal_command(
        ["o", "-r", reveal_path],
        env={REVEAL_ENV: "1"},
    )


def _launch_terminal_command(
    command: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> bool:
    term_env = os.environ.get("TERMINAL")
    commands = []
    if term_env:
        commands.append(shlex.split(term_env))
    commands.extend(
        [
            [cmd]
            for cmd in (
                "alacritty",
                "foot",
                "kitty",
                "wezterm",
                "gnome-terminal",
                "xterm",
            )
        ]
    )

    launch_env = dict(os.environ)
    if env:
        launch_env.update(env)

    for cmd in commands:
        if not cmd:
            continue
        if shutil.which(cmd[0]) is None:
            continue
        launch_cmd = _build_terminal_launch_command(cmd, command)
        if not launch_cmd:
            continue
        try:
            subprocess.Popen(
                launch_cmd,
                cwd=cwd,
                env=launch_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            return True
        except Exception:
            continue

    return False


def _build_terminal_launch_command(
    terminal_cmd: list[str], command: list[str]
) -> list[str]:
    launch_cmd = list(terminal_cmd)
    if any("{cmd}" in token for token in launch_cmd):
        return [token.replace("{cmd}", " ".join(command)) for token in launch_cmd]

    terminal_name = os.path.basename(launch_cmd[0])
    if terminal_name == "xdg-terminal-exec":
        launch_cmd.extend(["--"] + command)
        return launch_cmd

    launch_cmd.extend(["-e"] + command)
    return launch_cmd


def _normalize_target_path(path: str) -> str:
    parsed = urlparse(path)
    if parsed.scheme == "file":
        path = unquote(parsed.path)
    return os.path.realpath(os.path.expanduser(path))


def _parse_args(
    argv: list[str],
) -> tuple[PickerOptions | None, str | None, str | None, list[str]]:
    picker_allowed: str | None = None
    picker_mode = False
    extensions: list[str] = []
    multi_select = False
    save_mode = False
    save_extensions_set = False
    start_path: str | None = None
    picker_start_path: str | None = None
    positional_targets: list[str] = []
    reveal_path: str | None = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "-p":
            picker_mode = True
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
                picker_start_path = argv[i]
        elif arg == "-s":
            save_mode = True
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
                picker_start_path = argv[i]
        elif arg == "-ld":
            if picker_allowed == "file":
                raise ValueError("-ld cannot be used with -lf")
            picker_allowed = "dir"
        elif arg == "-lf":
            if picker_allowed == "dir":
                raise ValueError("-lf cannot be used with -ld")
            picker_allowed = "file"
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
                raw = argv[i]
                parts = [
                    part.strip().lstrip(".")
                    for part in raw.replace(";", ",").split(",")
                ]
                extensions = sorted({part.lower() for part in parts if part})
        elif arg == "-se":
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                raise ValueError("-se requires an extension")
            i += 1
            raw = argv[i]
            parts = [
                part.strip().lstrip(".") for part in raw.replace(";", ",").split(",")
            ]
            extensions = sorted({part.lower() for part in parts if part})
            save_extensions_set = True
        elif arg == "-m":
            multi_select = True
        elif arg == "-r":
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                raise ValueError("-r requires a path")
            i += 1
            reveal_path = argv[i]
        else:
            if arg.startswith("-"):
                raise ValueError(f"Unknown flag '{arg}'")
            positional_targets.append(arg)
        i += 1

    if picker_mode and save_mode:
        raise ValueError("-p cannot be used with -s")

    if reveal_path and (picker_mode or save_mode):
        raise ValueError("-r cannot be used with -p or -s")

    if reveal_path and positional_targets:
        raise ValueError("-r cannot be used with a start path")

    if save_extensions_set and not save_mode:
        raise ValueError("-se requires -s")

    if any([picker_allowed, multi_select, extensions]) and not (
        picker_mode or save_mode
    ):
        if not picker_mode and not save_mode:
            raise ValueError("Picker flags require -p or -s")

    if save_mode and picker_allowed == "dir":
        raise ValueError("-s cannot be used with -ld")

    if save_mode and multi_select:
        raise ValueError("-s cannot be used with -m")

    if picker_mode or save_mode:
        if picker_start_path and positional_targets:
            raise ValueError("Start path already provided for -p/-s")
        if len(positional_targets) > 1:
            raise ValueError("Only one start path is allowed for -p/-s")
        start_path = picker_start_path or (
            positional_targets[0] if positional_targets else None
        )
        if not start_path:
            start_path = os.path.expanduser("~")
        if picker_allowed is None:
            picker_allowed = "any"
    elif positional_targets:
        start_path = positional_targets[0]

    if reveal_path:
        reveal_path = _normalize_target_path(reveal_path)
        if os.path.isdir(reveal_path):
            start_path = reveal_path
        else:
            start_path = os.path.dirname(reveal_path) or os.path.expanduser("~")

    picker_options = None
    if picker_mode or save_mode:
        picker_options = PickerOptions(
            allowed_type=picker_allowed or "any",
            extensions=extensions,
            multi_select=multi_select,
            mode="save" if save_mode else "pick",
        )
    return picker_options, start_path, reveal_path, positional_targets


def _config_path() -> Path:
    return Path(os.path.realpath(os.path.expanduser(config.get_config_path())))


def _open_file_detached(filepath: str) -> tuple[bool, str]:
    from file_actions import FileActionService

    directory = os.path.dirname(filepath) or os.getcwd()
    nav = SimpleNamespace(
        config=config.USER_CONFIG,
        renderer=SimpleNamespace(stdscr=None),
        dir_manager=SimpleNamespace(current_path=directory),
        status_message="",
        need_redraw=False,
    )

    def _open_terminal(base_path: str | None = None, command: list[str] | None = None) -> bool:
        if not command:
            return False
        return _launch_terminal_command(
            command,
            cwd=base_path or nav.dir_manager.current_path,
        )

    nav.open_terminal = _open_terminal
    service = FileActionService(nav)
    opened = service.open_file(filepath, detached=True)
    return opened, str(nav.status_message or "")


def _expand_multi_file_command(
    raw_cmd: list[str], filepaths: list[str]
) -> list[str] | None:
    if not raw_cmd:
        return None

    tokens: list[str] = []
    has_placeholder = False

    for part in raw_cmd:
        if not isinstance(part, str):
            continue
        if part == "{file}":
            tokens.extend(filepaths)
            has_placeholder = True
            continue
        if "{file}" in part:
            if len(filepaths) != 1:
                return None
            part = part.replace("{file}", filepaths[0])
            has_placeholder = True
        tokens.append(part)

    if not tokens:
        return None

    if not has_placeholder:
        tokens.extend(filepaths)

    return tokens


def _resolve_internal_vim_command(filepaths: list[str]) -> list[str] | None:
    from file_actions import is_text_like_file

    if not filepaths or not all(is_text_like_file(path) for path in filepaths):
        return None

    editor_spec = config.USER_CONFIG.get_handler_spec("editor")
    for raw_cmd in editor_spec.commands:
        tokens = _expand_multi_file_command(raw_cmd, filepaths)
        if not tokens:
            continue
        if shutil.which(tokens[0]) is None:
            continue
        if tokens[0] == "vim":
            return tokens
        return None

    fallback = _expand_multi_file_command(["vim"], filepaths)
    if fallback and shutil.which("vim"):
        return fallback
    return None


def _run_internal_command(command: list[str]) -> bool:
    from file_actions import flush_terminal_input

    flush_terminal_input()
    try:
        return subprocess.call(command) == 0
    except FileNotFoundError:
        print(f"{command[0]}: command not found", file=sys.stderr)
        return False
    except Exception as exc:
        print(
            f"Failed to launch {command[0]}: {exc.__class__.__name__}",
            file=sys.stderr,
        )
        return False


def _open_files_detached(filepaths: list[str]) -> bool:
    failures: list[tuple[str, str]] = []

    for filepath in filepaths:
        opened, status = _open_file_detached(filepath)
        if not opened:
            failures.append((filepath, status or "Failed to open"))

    for filepath, status in failures:
        print(f"{filepath}: {status}", file=sys.stderr)

    return not failures


def _dispatch(args: list[str]) -> int:
    picker_options = None
    start_path = None
    reveal_path = None
    positional_targets: list[str] = []

    if args:
        try:
            picker_options, start_path, reveal_path, positional_targets = _parse_args(
                args
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if picker_options is None and reveal_path is None and positional_targets:
        direct_targets = [
            _normalize_target_path(target) for target in positional_targets
        ]
        if len(direct_targets) > 1:
            if any(not os.path.isfile(target) for target in direct_targets):
                print(
                    "Multiple positional targets must all be files",
                    file=sys.stderr,
                )
                return 1
            vim_command = _resolve_internal_vim_command(direct_targets)
            if vim_command is not None:
                return 0 if _run_internal_command(vim_command) else 1
            return 0 if _open_files_detached(direct_targets) else 1

        direct_target = direct_targets[0]
        if os.path.isfile(direct_target):
            return 0 if _open_files_detached([direct_target]) else 1
        start_path = direct_target

    start_dir = start_path or os.getcwd()
    if (
        reveal_path
        and not os.environ.get(REVEAL_ENV)
        and not os.environ.get(REVEAL_NO_SPAWN_ENV)
        and not (sys.stdin.isatty() or sys.stdout.isatty())
        and not os.environ.get("TERM")
    ):
        if _launch_reveal_terminal(reveal_path):
            return 0

    orchestrator = Orchestrator(
        start_path=start_dir,
        picker_options=picker_options,
        reveal_path=reveal_path,
    )
    orchestrator.run()

    if picker_options is not None:
        navigator = orchestrator.navigator
        selection = getattr(navigator, "selection_result", []) if navigator else []
        if selection:
            payload = "\n".join(selection) + "\n"
            sys.stdout.write(payload)
            _write_picker_cache(selection)
            return 0
        return 1
    return 0


APP_SPEC = AppSpec(
    app_name="o",
    version=__version__,
    help_text=HELP_TEXT,
    install_script_path=INSTALL_SCRIPT,
    no_args_mode="dispatch",
    config_path_factory=_config_path,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    return run_app(APP_SPEC, args, _dispatch)


def _write_picker_cache(selection: list[str]) -> None:
    cache_root = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    cache_dir = os.path.join(cache_root, "o")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "picker-selection.txt")
        with open(cache_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(selection) + "\n")
    except OSError:
        return


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
