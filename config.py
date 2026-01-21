import json
import os
import shlex
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UserConfig:
    matrix_mode: bool = False
    handlers: Dict[str, List[List[str]]] = field(default_factory=dict)

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

    return UserConfig(matrix_mode=matrix_mode, handlers=handlers)


USER_CONFIG = load_user_config()


def get_config_path() -> str:
    return _config_path()
