import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

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
