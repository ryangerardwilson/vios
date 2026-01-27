import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import json
from pathlib import Path
from typing import Dict, Any

import config
from config import HandlerSpec, _normalize_handlers


def test_legacy_handler_entries_default_to_external():
    data = {
        "csv_viewer": [["vixl"]],
        "editor": ["vim"],
    }

    handlers = _normalize_handlers(data)

    assert set(handlers.keys()) == {"csv_viewer", "editor"}

    csv_spec = handlers["csv_viewer"]
    assert isinstance(csv_spec, HandlerSpec)
    assert csv_spec.commands == [["vixl"]]
    assert csv_spec.is_internal is False

    editor_spec = handlers["editor"]
    assert editor_spec.commands == [["vim"]]
    assert editor_spec.is_internal is False


def test_object_handler_entries_respect_is_internal_flag():
    data = {
        "csv_viewer": {
            "commands": [["vixl", "--mode", "grid"]],
            "is_internal": True,
        }
    }

    handlers = _normalize_handlers(data)

    assert set(handlers.keys()) == {"csv_viewer"}

    spec = handlers["csv_viewer"]
    assert spec.commands == [["vixl", "--mode", "grid"]]
    assert spec.is_internal is True


def test_load_user_config_ignores_deprecated_shortcuts(tmp_path: Path, monkeypatch):
    payload: Dict[str, Any] = {
        "matrix_mode": True,
        "handlers": {
            "csv_viewer": {"commands": [["vixl"]]},
        },
        "file_shortcuts": {"a": "~/one"},
        "dir_shortcuts": {"b": "~/two"},
        "workspace_shortcuts": {"c": {}},
        "browser_setup": {
            "command": [["xdg-open"]],
            "shortcuts": {"x": "https://example.com"},
        },
        "browser_shortcuts": {"x": "https://example.com"},
    }

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(config, "_config_path", lambda: str(cfg_path), raising=False)

    user_config = config.load_user_config()

    # Deprecated keys should not populate attributes
    assert not hasattr(user_config, "file_shortcuts")
    assert not hasattr(user_config, "dir_shortcuts")
    assert not hasattr(user_config, "workspace_shortcuts")

    # Warnings should mention each ignored key
    warning_text = "\n".join(user_config.warnings)
    assert "file_shortcuts" in warning_text
    assert "dir_shortcuts" in warning_text
    assert "workspace_shortcuts" in warning_text
    assert "browser_setup" in warning_text
    assert "browser_shortcuts" in warning_text
