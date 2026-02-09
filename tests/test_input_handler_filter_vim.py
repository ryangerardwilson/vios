import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from input_handler import InputHandler


class DummyDirManager:
    def __init__(self):
        self.filter_pattern = ""

    def refresh_cache(self, path=None):
        return None


class DummyFileActions:
    def __init__(self, edited_value, should_succeed=True):
        self.edited_value = edited_value
        self.should_succeed = should_succeed
        self.paths: list[str] = []

    def _open_with_vim(self, path: str):
        self.paths.append(path)
        if not self.should_succeed:
            return False
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.edited_value)
        return True


def make_handler(file_actions):
    dir_manager = DummyDirManager()
    nav = SimpleNamespace(
        dir_manager=dir_manager,
        file_actions=file_actions,
        status_message="",
        need_redraw=False,
        command_popup_visible=False,
        show_help=False,
        command_mode=False,
        leader_sequence="",
    )
    handler = InputHandler(nav)
    return handler, nav


def test_filter_edit_sets_pattern():
    file_actions = DummyFileActions("alpha\n")
    handler, nav = make_handler(file_actions)

    handler.in_filter_mode = True
    nav.dir_manager.filter_pattern = "/"

    assert handler.handle_key(None, ord("v")) is False

    assert nav.dir_manager.filter_pattern == "alpha"
    assert handler.in_filter_mode is False
    assert nav.status_message == "Filter set: alpha"
    assert file_actions.paths
    assert not os.path.exists(file_actions.paths[0])


def test_filter_edit_clears_pattern_when_empty():
    file_actions = DummyFileActions("")
    handler, nav = make_handler(file_actions)

    handler.in_filter_mode = True
    nav.dir_manager.filter_pattern = "/"

    handler.handle_key(None, ord("v"))

    assert nav.dir_manager.filter_pattern == ""
    assert handler.in_filter_mode is False
    assert nav.status_message == "Filter cleared"
    assert file_actions.paths
    assert not os.path.exists(file_actions.paths[0])


def test_filter_edit_failure_keeps_filter_mode():
    file_actions = DummyFileActions("ignored", should_succeed=False)
    handler, nav = make_handler(file_actions)

    handler.in_filter_mode = True
    nav.dir_manager.filter_pattern = "/"

    handler.handle_key(None, ord("v"))

    assert nav.dir_manager.filter_pattern == "/"
    assert handler.in_filter_mode is True
    assert nav.status_message == "Unable to launch vim for filter"
    assert file_actions.paths
    assert not os.path.exists(file_actions.paths[0])
