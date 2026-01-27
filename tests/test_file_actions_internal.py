import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import HandlerSpec, UserConfig
from file_actions import FileActionService


def _make_nav() -> SimpleNamespace:
    config = UserConfig()
    renderer = SimpleNamespace(stdscr=None)
    dir_manager = SimpleNamespace(current_path=".")

    def _open_terminal(_base=None, _command=None):
        return False

    return SimpleNamespace(
        config=config,
        renderer=renderer,
        dir_manager=dir_manager,
        open_terminal=_open_terminal,
        status_message="",
        need_redraw=False,
    )


def test_invoke_handler_uses_internal_runner_when_flagged():
    nav = _make_nav()
    service = FileActionService(nav)

    spec = HandlerSpec(commands=[["vixl"]], is_internal=True)

    with patch.object(service, "_run_internal_handler", return_value=True) as mock_internal, patch.object(service, "_run_terminal_handlers", return_value=False) as mock_terminal:
        result = service._invoke_handler(spec, "example.csv", default_strategy="terminal")

    assert result is True
    mock_internal.assert_called_once()
    mock_terminal.assert_not_called()


def test_invoke_handler_delegates_to_terminal_when_external():
    nav = _make_nav()
    service = FileActionService(nav)

    spec = HandlerSpec(commands=[["vixl"]], is_internal=False)

    with patch.object(service, "_run_terminal_handlers", return_value=True) as mock_terminal, patch.object(service, "_run_internal_handler", return_value=False) as mock_internal:
        result = service._invoke_handler(spec, "example.csv", default_strategy="terminal")

    assert result is True
    mock_terminal.assert_called_once()
    mock_internal.assert_not_called()
