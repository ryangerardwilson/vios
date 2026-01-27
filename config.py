import json
import os
import shlex
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class UserConfig:
    matrix_mode: bool = False
    handlers: Dict[str, "HandlerSpec"] = field(default_factory=dict)
    file_shortcuts: Dict[str, str] = field(default_factory=dict)
    dir_shortcuts: Dict[str, str] = field(default_factory=dict)
    workspace_shortcuts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    browser_commands: List[List[str]] = field(default_factory=list)
    browser_shortcuts: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def get_handler_commands(self, name: str) -> List[List[str]]:
        return self.get_handler_spec(name).commands

    def get_handler_spec(self, name: str) -> "HandlerSpec":
        spec = self.handlers.get(name)
        if spec is None:
            return HandlerSpec(commands=[], is_internal=False)
        return spec


@dataclass
class HandlerSpec:
    commands: List[List[str]] = field(default_factory=list)
    is_internal: bool = False


def _config_path() -> str:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if not xdg_config:
        xdg_config = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(xdg_config, "o", "config.json")


def _normalize_command(entry) -> List[str]:
    if isinstance(entry, str):
        return shlex.split(entry) if entry.strip() else []
    if isinstance(entry, list):
        if all(isinstance(token, str) for token in entry):
            return [token for token in entry if token]
    return []


def _normalize_handlers(raw_handlers) -> Dict[str, HandlerSpec]:
    handlers: Dict[str, HandlerSpec] = {}

    if not isinstance(raw_handlers, dict):
        return handlers

    for raw_key, raw_value in raw_handlers.items():
        key = raw_key.strip() if isinstance(raw_key, str) else None
        if not key:
            continue

        commands: List[List[str]] = []
        is_internal = False

        if isinstance(raw_value, dict):
            commands_value = raw_value.get("commands")
            if commands_value is None and "command" in raw_value:
                commands_value = raw_value.get("command")
            commands = _normalize_handler_commands(commands_value)
            is_internal = bool(raw_value.get("is_internal"))
        else:
            commands = _normalize_handler_commands(raw_value)
            is_internal = False

        if not commands:
            continue

        handlers[key] = HandlerSpec(commands=commands, is_internal=is_internal)

    return handlers


def _normalize_handler_commands(raw_value) -> List[List[str]]:
    commands: List[List[str]] = []

    if isinstance(raw_value, list):
        # If the value looks like a single command expressed as a list of tokens
        # (e.g. ["vim", "{file}"]), treat it as one entry. Otherwise iterate.
        if raw_value and all(isinstance(entry, str) for entry in raw_value):
            cmd = _normalize_command(raw_value)
            if cmd:
                commands.append(cmd)
        else:
            for entry in raw_value:
                cmd = _normalize_command(entry)
                if cmd:
                    commands.append(cmd)
    else:
        cmd = _normalize_command(raw_value)
        if cmd:
            commands.append(cmd)

    return commands


def _normalize_path(value: str) -> str:
    if not isinstance(value, str):
        return ""
    expanded = os.path.expanduser(value.strip())
    if not expanded:
        return ""
    return os.path.realpath(expanded)


def _normalize_file_shortcuts(raw_shortcuts) -> Tuple[Dict[str, str], List[str]]:
    shortcuts: Dict[str, str] = {}
    warnings: List[str] = []

    if not isinstance(raw_shortcuts, dict):
        return shortcuts, warnings

    for raw_key, raw_value in raw_shortcuts.items():
        if not isinstance(raw_key, str):
            warnings.append("file_shortcuts key ignored (not a string)")
            continue

        token = raw_key.strip().lower()
        if not token:
            warnings.append("file_shortcuts entry ignored (empty key)")
            continue

        if not token.isalnum():
            warnings.append(
                f"file_shortcuts key '{raw_key}' ignored (use alphanumeric tokens)"
            )
            continue

        path = _normalize_path(raw_value)
        if not path:
            warnings.append(f"file_shortcuts '{raw_key}' ignored (empty path)")
            continue

        if not os.path.isfile(path):
            warnings.append(
                f"file_shortcuts '{raw_key}' ignored ({path} is not an existing file)"
            )
            continue

        shortcuts[token] = path

    return shortcuts, warnings


def _normalize_dir_shortcuts(raw_shortcuts) -> Tuple[Dict[str, str], List[str]]:
    shortcuts: Dict[str, str] = {}
    warnings: List[str] = []

    if not isinstance(raw_shortcuts, dict):
        return shortcuts, warnings

    for raw_key, raw_value in raw_shortcuts.items():
        if not isinstance(raw_key, str):
            warnings.append("dir_shortcuts key ignored (not a string)")
            continue

        token = raw_key.strip().lower()
        if not token:
            warnings.append("dir_shortcuts entry ignored (empty key)")
            continue

        if not token.isalnum():
            warnings.append(
                f"dir_shortcuts key '{raw_key}' ignored (use alphanumeric tokens)"
            )
            continue

        path = _normalize_path(raw_value)
        if not path:
            warnings.append(f"dir_shortcuts '{raw_key}' ignored (empty path)")
            continue

        if not os.path.isdir(path):
            warnings.append(
                f"dir_shortcuts '{raw_key}' ignored ({path} is not an existing directory)"
            )
            continue

        shortcuts[token] = path

    return shortcuts, warnings


def _normalize_workspace_shortcuts(
    raw_shortcuts,
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    shortcuts: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []

    if not isinstance(raw_shortcuts, dict):
        return shortcuts, warnings

    for raw_key, raw_value in raw_shortcuts.items():
        if not isinstance(raw_key, str):
            warnings.append("workspace_shortcuts key ignored (not a string)")
            continue

        token = raw_key.strip().lower()
        if not token:
            warnings.append("workspace_shortcuts entry ignored (empty key)")
            continue

        if not token.isalnum():
            warnings.append(
                f"workspace_shortcuts key '{raw_key}' ignored (use alphanumeric tokens)"
            )
            continue

        if not isinstance(raw_value, dict):
            warnings.append(
                f"workspace_shortcuts '{raw_key}' ignored (expected object with paths or commands)"
            )
            continue

        normalized_entry: Dict[str, Any] = {}

        for label in ("internal", "external"):
            candidate = raw_value.get(label)
            if candidate is None:
                continue

            key_path = f"{label}_path"
            key_commands = f"{label}_commands"

            if isinstance(candidate, str):
                path = _normalize_path(candidate)
                if not path:
                    warnings.append(
                        f"workspace_shortcuts '{raw_key}' {label} ignored (empty path)"
                    )
                    continue
                if not os.path.exists(path):
                    warnings.append(
                        f"workspace_shortcuts '{raw_key}' {label} ignored ({path} missing)"
                    )
                    continue
                normalized_entry[key_path] = path
                continue

            if isinstance(candidate, list):
                commands: List[List[str]] = []
                saw_invalid = False
                for entry in candidate:
                    cmd = _normalize_command(entry)
                    if cmd:
                        commands.append(cmd)
                        continue

                    if isinstance(entry, list):
                        # Treat lists containing only empty/whitespace strings as "no preference"
                        if not entry or all(
                            isinstance(token, str) and not token.strip()
                            for token in entry
                        ):
                            continue
                        if not all(isinstance(token, str) for token in entry):
                            saw_invalid = True
                        else:
                            saw_invalid = True
                        continue

                    if isinstance(entry, str):
                        # Blank strings are also considered "no preference"
                        if not entry.strip():
                            continue
                        saw_invalid = True
                        continue

                    if entry is None:
                        continue

                    saw_invalid = True

                if commands:
                    normalized_entry[key_commands] = commands
                    continue

                if saw_invalid:
                    warnings.append(
                        f"workspace_shortcuts '{raw_key}' {label} ignored (no valid commands)"
                    )
                continue

            warnings.append(
                f"workspace_shortcuts '{raw_key}' {label} ignored (unsupported type)"
            )

        if normalized_entry:
            shortcuts[token] = normalized_entry
        else:
            warnings.append(
                f"workspace_shortcuts '{raw_key}' ignored (no valid paths or commands)"
            )

    return shortcuts, warnings


def _normalize_browser_setup(
    raw_browser,
) -> Tuple[List[List[str]], Dict[str, str], List[str]]:
    commands: List[List[str]] = []
    shortcuts: Dict[str, str] = {}
    warnings: List[str] = []

    if not isinstance(raw_browser, dict):
        return commands, shortcuts, warnings

    raw_commands = raw_browser.get("command")
    if isinstance(raw_commands, list):
        for entry in raw_commands:
            cmd = _normalize_command(entry)
            if cmd:
                commands.append(cmd)
    else:
        cmd = _normalize_command(raw_commands)
        if cmd:
            commands.append(cmd)

    raw_shortcuts = raw_browser.get("shortcuts", {})
    if isinstance(raw_shortcuts, dict):
        for raw_key, raw_value in raw_shortcuts.items():
            if not isinstance(raw_key, str):
                warnings.append("browser shortcut key ignored (not a string)")
                continue

            token = raw_key.strip().lower()
            if not token:
                warnings.append("browser shortcut entry ignored (empty key)")
                continue

            if not token.isalnum():
                warnings.append(
                    f"browser shortcut key '{raw_key}' ignored (use alphanumeric tokens)"
                )
                continue

            if not isinstance(raw_value, str):
                warnings.append(
                    f"browser shortcut '{raw_key}' ignored (URL must be a string)"
                )
                continue

            url = raw_value.strip()
            if not url:
                warnings.append(f"browser shortcut '{raw_key}' ignored (empty URL)")
                continue

            shortcuts[token] = url
    else:
        warnings.append("browser shortcuts ignored (expected object)")

    return commands, shortcuts, warnings


def load_user_config() -> UserConfig:
    path = _config_path()
    data = {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        pass
    except Exception:
        data = {}

    matrix_mode = data.get("matrix_mode")
    if not isinstance(matrix_mode, bool):
        matrix_mode = False

    handlers = _normalize_handlers(data.get("handlers", {}))

    file_shortcuts, file_warnings = _normalize_file_shortcuts(
        data.get("file_shortcuts", {})
    )
    dir_shortcuts, dir_warnings = _normalize_dir_shortcuts(
        data.get("dir_shortcuts", {})
    )

    workspace_shortcuts, workspace_warnings = _normalize_workspace_shortcuts(
        data.get("workspace_shortcuts", {})
    )

    browser_commands, browser_shortcuts, browser_warnings = _normalize_browser_setup(
        data.get("browser_setup")
    )

    warnings = file_warnings + dir_warnings + workspace_warnings + browser_warnings

    return UserConfig(
        matrix_mode=matrix_mode,
        handlers=handlers,
        file_shortcuts=file_shortcuts,
        dir_shortcuts=dir_shortcuts,
        workspace_shortcuts=workspace_shortcuts,
        browser_commands=browser_commands,
        browser_shortcuts=browser_shortcuts,
        warnings=warnings,
    )


USER_CONFIG = load_user_config()


def get_config_path() -> str:
    return _config_path()
