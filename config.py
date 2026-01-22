import json
import os
import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class UserConfig:
    matrix_mode: bool = False
    handlers: Dict[str, List[List[str]]] = field(default_factory=dict)
    file_shortcuts: Dict[str, str] = field(default_factory=dict)
    dir_shortcuts: Dict[str, str] = field(default_factory=dict)
    workspace_shortcuts: Dict[str, Dict[str, str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def get_handler_commands(self, name: str) -> List[List[str]]:
        return self.handlers.get(name, [])


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


def _normalize_handlers(raw_handlers) -> Dict[str, List[List[str]]]:
    handlers: Dict[str, List[List[str]]] = {}

    if not isinstance(raw_handlers, dict):
        return handlers

    for key, value in raw_handlers.items():
        normalized: List[List[str]] = []
        if isinstance(value, list):
            for entry in value:
                cmd = _normalize_command(entry)
                if cmd:
                    normalized.append(cmd)
        else:
            cmd = _normalize_command(value)
            if cmd:
                normalized.append(cmd)

        if normalized:
            handlers[key] = normalized

    return handlers


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
) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    shortcuts: Dict[str, Dict[str, str]] = {}
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
                f"workspace_shortcuts '{raw_key}' ignored (expected object with paths)"
            )
            continue

        normalized_entry: Dict[str, str] = {}

        for label in ("internal", "external"):
            candidate = raw_value.get(label)
            if candidate is None:
                continue
            if not isinstance(candidate, str):
                warnings.append(
                    f"workspace_shortcuts '{raw_key}' {label} ignored (not a string)"
                )
                continue
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
            normalized_entry[label] = path

        if normalized_entry:
            shortcuts[token] = normalized_entry
        else:
            warnings.append(
                f"workspace_shortcuts '{raw_key}' ignored (no valid paths)"
            )

    return shortcuts, warnings


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

    warnings = file_warnings + dir_warnings + workspace_warnings

    return UserConfig(
        matrix_mode=matrix_mode,
        handlers=handlers,
        file_shortcuts=file_shortcuts,
        dir_shortcuts=dir_shortcuts,
        workspace_shortcuts=workspace_shortcuts,
        warnings=warnings,
    )


USER_CONFIG = load_user_config()


def get_config_path() -> str:
    return _config_path()
