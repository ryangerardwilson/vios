import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from modules.input_handler import InputHandler


class DummyClipboard:
    def cleanup(self):
        self.cleaned = True


class DummyDirManager:
    def __init__(self, current_path):
        self.current_path = current_path
        self.filter_pattern = ""
        self.sort_mode = "alpha"
        self.sort_map = {}

    def set_sort_mode(self, mode: str):
        self.sort_mode = mode

    def set_sort_mode_for_path(self, path: str, mode: str):
        self.sort_map[os.path.realpath(path)] = mode


class DummyNavigator:
    def __init__(self, display_items, current_path):
        self.dir_manager = DummyDirManager(current_path)
        self.clipboard = DummyClipboard()
        self.expanded_nodes = set()
        self.display_items = display_items
        self.create_calls = []
        self.status_message = ""
        self.leader_sequence = ""
        self.need_redraw = False
        self.browser_selected = 0

    def build_display_items(self):
        return list(self.display_items)

    def create_new_file_no_open(self, base_dir):
        self.create_calls.append(("file", os.path.realpath(base_dir)))

    def create_new_directory(self, base_dir):
        self.create_calls.append(("dir", os.path.realpath(base_dir)))

    def rename_selected(self):
        pass

    def copy_current_path(self):
        pass
def test_scope_detection_for_nested_selection():
    items = [
        ("src", True, "/proj/src", 0),
        ("foo", True, "/proj/src/foo", 1),
        ("alpha.py", False, "/proj/src/foo/alpha.py", 2),
        ("beta.py", False, "/proj/src/foo/beta.py", 2),
        ("bar", True, "/proj/src/bar", 1),
    ]

    nav = DummyNavigator(items, "/proj")
    nav.expanded_nodes.update({"/proj/src", "/proj/src/foo"})
    handler = InputHandler(nav)

    nav.browser_selected = 3
    context_path, scope_range = handler._compute_context_scope(items, nav.browser_selected)

    assert context_path is not None
    assert context_path == os.path.realpath("/proj/src/foo")
    assert scope_range == (2, 3)


def test_jump_commands_stay_within_scope():
    items = [
        ("src", True, "/proj/src", 0),
        ("foo", True, "/proj/src/foo", 1),
        ("alpha.py", False, "/proj/src/foo/alpha.py", 2),
        ("beta.py", False, "/proj/src/foo/beta.py", 2),
        ("bar", True, "/proj/src/bar", 1),
    ]

    nav = DummyNavigator(items, "/proj")
    nav.expanded_nodes.update({"/proj/src", "/proj/src/foo"})
    handler = InputHandler(nav)

    nav.browser_selected = 3
    context_path, scope_range = handler._compute_context_scope(items, nav.browser_selected)
    selection = items[nav.browser_selected]

    handler.comma_sequence = ""
    assert context_path is not None
    handler.pending_comma = True
    handler._handle_comma_command(ord('k'), len(items), selection, context_path, scope_range, "/proj/src/foo")
    assert nav.browser_selected == 2

    nav.browser_selected = 2
    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(ord('j'), len(items), items[nav.browser_selected], context_path, scope_range, "/proj/src/foo")
    assert nav.browser_selected == 3


def test_sorting_scoped_to_expanded_directory():
    items = [
        ("src", True, "/proj/src", 0),
        ("foo", True, "/proj/src/foo", 1),
        ("alpha.py", False, "/proj/src/foo/alpha.py", 2),
        ("beta.py", False, "/proj/src/foo/beta.py", 2),
    ]

    nav = DummyNavigator(items, "/proj")
    nav.expanded_nodes.update({"/proj/src", "/proj/src/foo"})
    handler = InputHandler(nav)

    nav.browser_selected = 2
    context_path, scope_range = handler._compute_context_scope(items, nav.browser_selected)
    selection = items[nav.browser_selected]

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(ord('s'), len(items), selection, context_path, scope_range, "/proj/src/foo")
    handler.pending_comma = True
    handler.comma_sequence = "s"
    handler._handle_comma_command(ord('a'), len(items), selection, context_path, scope_range, "/proj/src/foo")

    assert context_path is not None
    key = os.path.realpath(context_path)
    assert nav.dir_manager.sort_map[key] == "alpha"
    assert "Sort: Name" in nav.status_message


def test_creation_commands_use_context_directory():
    items = [
        ("src", True, "/proj/src", 0),
        ("foo", True, "/proj/src/foo", 1),
        ("alpha.py", False, "/proj/src/foo/alpha.py", 2),
    ]

    nav = DummyNavigator(items, "/proj")
    nav.expanded_nodes.update({"/proj/src", "/proj/src/foo"})
    handler = InputHandler(nav)

    nav.browser_selected = 2
    context_path, scope_range = handler._compute_context_scope(items, nav.browser_selected)
    selection = items[nav.browser_selected]

    target_dir = os.path.dirname(selection[2])

    assert context_path is not None
    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(ord('n'), len(items), selection, context_path, scope_range, target_dir)
    handler.pending_comma = True
    handler.comma_sequence = "n"
    handler._handle_comma_command(ord('f'), len(items), selection, context_path, scope_range, target_dir)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(ord('n'), len(items), selection, context_path, scope_range, target_dir)
    handler.pending_comma = True
    handler.comma_sequence = "n"
    handler._handle_comma_command(ord('d'), len(items), selection, context_path, scope_range, target_dir)

    assert nav.create_calls == [
        ("file", os.path.realpath(context_path)),
        ("dir", os.path.realpath(context_path)),
    ]


def test_creation_falls_back_to_current_directory_when_no_context():
    items = [
        ("README.md", False, "/proj/README.md", 0),
    ]

    nav = DummyNavigator(items, "/proj")
    handler = InputHandler(nav)

    nav.browser_selected = 0
    context_path, scope_range = handler._compute_context_scope(items, nav.browser_selected)
    selection = items[0]
    target_dir = os.path.dirname(selection[2])

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(ord('n'), len(items), selection, context_path, scope_range, target_dir)
    handler.pending_comma = True
    handler.comma_sequence = "n"
    handler._handle_comma_command(ord('f'), len(items), selection, context_path, scope_range, target_dir)

    assert nav.create_calls == [("file", os.path.realpath(target_dir))]
