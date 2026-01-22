import os
import sys
import time
import subprocess
from pathlib import Path
from types import SimpleNamespace


sys.path.append(str(Path(__file__).resolve().parents[1]))

from input_handler import InputHandler
from core_navigator import FileNavigator


class DummyClipboard:
    def cleanup(self):
        self.cleaned = True


class DummyDirManager:
    def __init__(self, current_path):
        self.current_path = current_path
        self.filter_pattern = ""
        self.sort_mode = "alpha"
        self.sort_map = {}
        self.home_path = os.path.realpath("/home/test")

    def set_sort_mode(self, mode: str):
        self.sort_mode = mode

    def set_sort_mode_for_path(self, path: str, mode: str):
        self.sort_map[os.path.realpath(path)] = mode

    @staticmethod
    def pretty_path(path: str) -> str:
        return os.path.realpath(path)


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
        self.collapsed_paths = []
        self.reset_home_called = False
        self.history = [current_path]
        self.history_index = 0
        self.show_help = False
        self.help_scroll = 0
        self.cheatsheet = ""
        self.bookmarks = []
        self.bookmark_index = -1
        self.marked_items = set()
        self.visual_mode = False
        self.visual_anchor_index = None
        self.visual_active_index = None
        self.config = SimpleNamespace(
            file_shortcuts={}, dir_shortcuts={}, workspace_shortcuts={}
        )
        self.opened_paths = []
        self.changed_dirs = []
        self.layout_mode = "list"
        self.terminal_calls = []
        self.terminal_commands = []
        self.renderer = SimpleNamespace(stdscr=None)
        self.command_mode = False
        self.command_buffer = ""
        self.notified_dirs = []

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

    def collapse_expansions_under(self, base_path):
        real = os.path.realpath(base_path)
        prefix = f"{real}{os.sep}"
        to_remove = {
            p for p in self.expanded_nodes if p == real or p.startswith(prefix)
        }
        self.expanded_nodes.difference_update(to_remove)
        self.collapsed_paths.append(real)

    def collapse_branch(self, base_path):
        real = os.path.realpath(base_path)
        new_nodes = set()
        for entry in self.expanded_nodes:
            entry_real = os.path.realpath(entry)
            if entry_real == real or entry_real.startswith(f"{real}{os.sep}"):
                continue
            new_nodes.add(entry)
        self.expanded_nodes = new_nodes

    def reset_to_home(self):
        self.reset_home_called = True
        self.expanded_nodes.clear()
        self.dir_manager.current_path = os.path.realpath(self.dir_manager.home_path)
        if self.bookmarks:
            try:
                self.bookmark_index = self.bookmarks.index(
                    self.dir_manager.current_path
                )
            except ValueError:
                self.bookmark_index = -1
        else:
            self.bookmark_index = -1

    def add_bookmark(self, path=None):
        target = path or self.dir_manager.current_path
        real = os.path.realpath(target)
        if real in self.bookmarks:
            self.bookmark_index = self.bookmarks.index(real)
            self.status_message = f"Bookmark exists: {real}"
        else:
            self.bookmarks.append(real)
            self.bookmark_index = len(self.bookmarks) - 1
            self.status_message = f"Bookmarked {real}"

    def go_history_back(self):
        if not self.bookmarks or self.bookmark_index <= 0:
            return False
        self.bookmark_index -= 1
        self.dir_manager.current_path = self.bookmarks[self.bookmark_index]
        return True

    def go_history_forward(self):
        if not self.bookmarks or self.bookmark_index >= len(self.bookmarks) - 1:
            return False
        self.bookmark_index += 1
        self.dir_manager.current_path = self.bookmarks[self.bookmark_index]
        return True

    def open_file(self, path: str):
        self.opened_paths.append(os.path.realpath(path))

    def change_directory(self, path: str, *, record_history: bool = True):
        real = os.path.realpath(path)
        if not os.path.isdir(real):
            return False
        self.dir_manager.current_path = real
        self.changed_dirs.append(real)
        return True

    def notify_directory_changed(self, *paths):
        normalized = tuple(os.path.realpath(p) for p in paths if p)
        self.notified_dirs.append(normalized)

    def enter_matrix_mode(self):
        self.layout_mode = "matrix"

    def enter_list_mode(self):
        self.layout_mode = "list"

    def open_terminal(self, base_path: str | None = None, command: list[str] | None = None):
        cwd = (
            os.path.realpath(base_path)
            if base_path
            else os.path.realpath(self.dir_manager.current_path)
        )
        self.terminal_calls.append(cwd)
        if command:
            self.terminal_commands.append(command)
            try:
                subprocess.run(command, cwd=cwd, check=False)
            except Exception:
                pass
        return True

    def enter_visual_mode(self, index):
        self.visual_mode = True
        self.visual_anchor_index = index
        self.visual_active_index = index
        self._apply_visual_marks()

    def reanchor_visual_mode(self, index):
        self.enter_visual_mode(index)

    def exit_visual_mode(self, clear_message: bool = True):
        self.visual_mode = False
        self.visual_anchor_index = None
        self.visual_active_index = None

    def update_visual_active(self, index):
        if not self.visual_mode:
            return
        self.visual_active_index = index
        self._apply_visual_marks()

    def get_visual_indices(self, total):
        if (
            not self.visual_mode
            or self.visual_anchor_index is None
            or self.visual_active_index is None
        ):
            return []
        start = min(self.visual_anchor_index, self.visual_active_index)
        end = max(self.visual_anchor_index, self.visual_active_index)
        start = max(0, min(start, total - 1)) if total else 0
        end = max(0, min(end, total - 1)) if total else 0
        if total <= 0:
            return []
        return list(range(start, end + 1))

    def _apply_visual_marks(self):
        if not self.visual_mode:
            return
        total = len(self.display_items)
        indices = self.get_visual_indices(total)
        for idx in indices:
            if 0 <= idx < total:
                path = self.display_items[idx][2]
                self.marked_items.add(path)


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
    context_path, scope_range = handler._compute_context_scope(
        items, nav.browser_selected
    )

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
    context_path, scope_range = handler._compute_context_scope(
        items, nav.browser_selected
    )
    selection = items[nav.browser_selected]

    handler.comma_sequence = ""
    assert context_path is not None
    handler.pending_comma = True
    handler._handle_comma_command(
        ord("k"), len(items), selection, context_path, scope_range, "/proj/src/foo"
    )
    assert nav.browser_selected == 2

    nav.browser_selected = 2
    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("j"),
        len(items),
        items[nav.browser_selected],
        context_path,
        scope_range,
        "/proj/src/foo",
    )
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
    context_path, scope_range = handler._compute_context_scope(
        items, nav.browser_selected
    )
    selection = items[nav.browser_selected]

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("s"), len(items), selection, context_path, scope_range, "/proj/src/foo"
    )
    handler.pending_comma = True
    handler.comma_sequence = "s"
    handler._handle_comma_command(
        ord("a"), len(items), selection, context_path, scope_range, "/proj/src/foo"
    )

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
    context_path, scope_range = handler._compute_context_scope(
        items, nav.browser_selected
    )
    selection = items[nav.browser_selected]

    target_dir = os.path.dirname(selection[2])

    assert context_path is not None
    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("n"), len(items), selection, context_path, scope_range, target_dir
    )
    handler.pending_comma = True
    handler.comma_sequence = "n"
    handler._handle_comma_command(
        ord("f"), len(items), selection, context_path, scope_range, target_dir
    )

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("n"), len(items), selection, context_path, scope_range, target_dir
    )
    handler.pending_comma = True
    handler.comma_sequence = "n"
    handler._handle_comma_command(
        ord("d"), len(items), selection, context_path, scope_range, target_dir
    )

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
    context_path, scope_range = handler._compute_context_scope(
        items, nav.browser_selected
    )
    selection = items[0]
    target_dir = os.path.dirname(selection[2])

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("n"), len(items), selection, context_path, scope_range, target_dir
    )
    handler.pending_comma = True
    handler.comma_sequence = "n"
    handler._handle_comma_command(
        ord("f"), len(items), selection, context_path, scope_range, target_dir
    )

    assert nav.create_calls == [("file", os.path.realpath(target_dir))]


def test_single_escape_collapses_current_scope():
    nav = DummyNavigator([], "/proj")
    nav.expanded_nodes.update({"/proj/src", "/proj/src/foo", "/other"})
    handler = InputHandler(nav)

    handler.handle_key(None, 27)

    assert os.path.realpath("/proj") in nav.collapsed_paths
    assert "/proj/src" not in nav.expanded_nodes
    assert "/other" in nav.expanded_nodes
    assert nav.status_message.startswith("Collapsed")


def test_double_escape_returns_home_and_clears_expansions():
    nav = DummyNavigator([], "/proj")
    nav.expanded_nodes.update({"/proj/src", "/other"})
    handler = InputHandler(nav)

    handler.handle_key(None, 27)
    handler.handle_key(None, 27)

    assert nav.reset_home_called
    assert nav.expanded_nodes == set()
    assert nav.dir_manager.current_path == os.path.realpath(nav.dir_manager.home_path)
    assert nav.status_message == "Returned to ~"


def test_bookmark_command_adds_current_path(tmp_path):
    root = tmp_path
    sub = root / "sub"
    sub.mkdir()

    nav = FileNavigator(str(root))
    handler = nav.input_handler

    nav.enter_list_mode()

    nav.change_directory(str(sub))
    handler.handle_key(None, ord(","))
    handler.handle_key(None, ord("b"))

    expected = [os.path.realpath(str(sub))]
    assert nav.bookmarks == expected
    assert nav.bookmark_index == 0
    assert "Bookmarked" in nav.status_message

    handler.handle_key(None, ord(","))
    handler.handle_key(None, ord("b"))

    assert nav.bookmarks == []
    assert nav.bookmark_index == -1
    assert "Unbookmarked" in nav.status_message


def test_ctrl_navigation_uses_bookmarks(tmp_path):
    root = tmp_path
    sub_a = root / "a"
    sub_b = root / "b"
    sub_a.mkdir()
    sub_b.mkdir()

    nav = FileNavigator(str(root))
    handler = nav.input_handler

    nav.enter_list_mode()

    nav.add_bookmark(str(root))
    nav.change_directory(str(sub_a))
    nav.add_bookmark()
    assert "Bookmarked" in nav.status_message
    nav.change_directory(str(sub_b))
    nav.add_bookmark()
    assert "Bookmarked" in nav.status_message

    assert nav.bookmarks == [
        os.path.realpath(str(root)),
        os.path.realpath(str(sub_a)),
        os.path.realpath(str(sub_b)),
    ]

    assert nav.bookmark_index == 2

    handler.handle_key(None, 8)  # Ctrl+H
    assert nav.dir_manager.current_path == os.path.realpath(str(sub_a))

    handler.handle_key(None, 8)  # Ctrl+H again
    assert nav.dir_manager.current_path == os.path.realpath(str(root))

    handler.handle_key(None, 8)  # Ctrl+H at first bookmark should stay put
    assert nav.dir_manager.current_path == os.path.realpath(str(root))

    handler.handle_key(None, 12)  # Ctrl+L
    assert nav.dir_manager.current_path == os.path.realpath(str(sub_a))

    handler.handle_key(None, 12)  # Ctrl+L again
    assert nav.dir_manager.current_path == os.path.realpath(str(sub_b))


def test_bookmark_command_ignores_expanded_context(tmp_path):
    root = tmp_path
    parent = root / "p"
    child = parent / "c"
    inner_file = child / "inner.txt"
    parent.mkdir()
    child.mkdir()
    inner_file.write_text("hello")

    nav = FileNavigator(str(root))
    handler = nav.input_handler

    nav.expanded_nodes.update(
        {
            os.path.realpath(str(parent)),
            os.path.realpath(str(child)),
        }
    )

    items = nav.build_display_items()
    target_path = os.path.realpath(str(inner_file))
    target_index = next(
        i
        for i, (_, _, path, _) in enumerate(items)
        if os.path.realpath(path) == target_path
    )
    nav.browser_selected = target_index

    handler.handle_key(None, ord(","))
    handler.handle_key(None, ord("b"))

    expected = [os.path.realpath(str(root))]
    assert nav.bookmarks == expected
    assert nav.bookmark_index == 0
    assert "Bookmarked" in nav.status_message


def test_visual_mode_enter_move_and_exit():
    items = [
        ("a.txt", False, "/proj/a.txt", 0),
        ("b.txt", False, "/proj/b.txt", 0),
        ("c.txt", False, "/proj/c.txt", 0),
    ]

    nav = DummyNavigator(items, "/proj")
    handler = InputHandler(nav)

    assert not nav.visual_mode

    handler.handle_key(None, ord("v"))
    assert nav.visual_mode
    assert nav.get_visual_indices(len(items)) == [0]

    handler.handle_key(None, ord("j"))
    assert nav.visual_mode
    assert nav.browser_selected == 1
    assert nav.get_visual_indices(len(items)) == [0, 1]

    handler.handle_key(None, ord("v"))  # Commit to marks
    assert not nav.visual_mode
    assert "/proj/a.txt" in nav.marked_items
    assert "/proj/b.txt" in nav.marked_items

    handler.handle_key(None, ord("v"))  # Start new selection appended to marks
    assert nav.visual_mode
    handler.handle_key(None, ord("j"))
    assert nav.browser_selected == 2
    handler.handle_key(None, ord("v"))  # Commit second selection
    assert not nav.visual_mode
    assert "/proj/c.txt" in nav.marked_items


def test_file_shortcut_opens_file(tmp_path):
    target_file = tmp_path / "doc.pdf"
    target_file.write_text("data")

    nav = DummyNavigator([], str(tmp_path))
    nav.config.file_shortcuts = {"notes": os.path.realpath(str(target_file))}
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("f"), 0, None, None, None, nav.dir_manager.current_path
    )
    assert handler.pending_comma

    handler._handle_comma_command(
        ord("o"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("n"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("o"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("t"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("e"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("s"), 0, None, None, None, nav.dir_manager.current_path
    )

    assert nav.opened_paths == [os.path.realpath(str(target_file))]
    assert not handler.pending_comma


def test_file_shortcut_missing_file(tmp_path):
    missing_file = tmp_path / "missing.pdf"

    nav = DummyNavigator([], str(tmp_path))
    nav.config.file_shortcuts = {"draft": os.path.realpath(str(missing_file))}
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("f"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("o"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("d"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("r"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("a"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("f"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("t"), 0, None, None, None, nav.dir_manager.current_path
    )

    assert nav.opened_paths == []
    assert "missing" in nav.status_message.lower()
    assert not handler.pending_comma


def test_directory_shortcut_changes_directory(tmp_path):
    target_dir = tmp_path / "genie_allocation"
    target_dir.mkdir()

    nav = DummyNavigator([], str(tmp_path))
    nav.config.dir_shortcuts = {"ga": os.path.realpath(str(target_dir))}
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("d"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("o"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("g"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("a"), 0, None, None, None, nav.dir_manager.current_path
    )

    assert nav.changed_dirs == [os.path.realpath(str(target_dir))]
    assert nav.dir_manager.current_path == os.path.realpath(str(target_dir))
    assert "jumped" in nav.status_message.lower()


def test_directory_shortcut_missing_directory(tmp_path):
    missing_dir = tmp_path / "missing"

    nav = DummyNavigator([], str(tmp_path))
    nav.config.dir_shortcuts = {"md": os.path.realpath(str(missing_dir))}
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("d"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("o"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("m"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("d"), 0, None, None, None, nav.dir_manager.current_path
    )

    assert nav.changed_dirs == []
    assert "missing" in nav.status_message.lower()
    assert not handler.pending_comma


def test_directory_shortcut_opens_terminal_without_nav_change(tmp_path):
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    nav = DummyNavigator([], str(tmp_path))
    nav.config.dir_shortcuts = {"pr": os.path.realpath(str(target_dir))}
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("t"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("o"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("p"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("r"), 0, None, None, None, nav.dir_manager.current_path
    )

    assert nav.dir_manager.current_path == os.path.realpath(str(tmp_path))
    assert nav.terminal_calls == [os.path.realpath(str(target_dir))]
    assert "terminal" in nav.status_message.lower()


def test_workspace_shortcut_opens_internal_and_external(tmp_path):
    internal_file = tmp_path / "Bible.md"
    internal_file.write_text("In the beginning")
    external_file = tmp_path / "KJV.pdf"
    external_file.write_text("pdf bytes")

    nav = DummyNavigator([], str(tmp_path))
    nav.config.workspace_shortcuts = {
        "1": {
            "internal_path": os.path.realpath(str(internal_file)),
            "external_path": os.path.realpath(str(external_file)),
        }
    }
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("w"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("1"), 0, None, None, None, nav.dir_manager.current_path
    )

    expected_paths = [
        os.path.realpath(str(external_file)),
        os.path.realpath(str(internal_file)),
    ]
    assert nav.opened_paths == expected_paths
    assert "workspace" in nav.status_message.lower()


def test_workspace_shortcut_directory_and_external_dir(tmp_path):
    internal_dir = tmp_path / "workspace"
    internal_dir.mkdir()
    external_dir = tmp_path / "logs"
    external_dir.mkdir()

    nav = DummyNavigator([], str(tmp_path))
    nav.config.workspace_shortcuts = {
        "wk": {
            "internal_path": os.path.realpath(str(internal_dir)),
            "external_path": os.path.realpath(str(external_dir)),
        }
    }
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("w"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("w"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("k"), 0, None, None, None, nav.dir_manager.current_path
    )

    real_internal = os.path.realpath(str(internal_dir))
    real_external = os.path.realpath(str(external_dir))
    assert nav.dir_manager.current_path == real_internal
    assert real_internal in nav.changed_dirs
    assert nav.terminal_calls == [real_external]
    assert "workspace" in nav.status_message.lower()


def test_workspace_shortcut_missing_paths(tmp_path):
    internal_file = tmp_path / "notes.md"
    internal_file.write_text("hello")

    nav = DummyNavigator([], str(tmp_path))
    nav.config.workspace_shortcuts = {
        "x": {"internal_path": os.path.realpath(str(internal_file))}
    }
    handler = InputHandler(nav)

    internal_file.unlink()

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("w"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("x"), 0, None, None, None, nav.dir_manager.current_path
    )

    assert nav.opened_paths == []
    assert nav.changed_dirs == []
    assert "unavailable" in nav.status_message.lower()


def test_workspace_shortcut_runs_commands(tmp_path):
    external_marker = tmp_path / "external.done"
    internal_marker = tmp_path / "internal.done"

    external_script = tmp_path / "external.sh"
    external_script.write_text(f"#!/bin/sh\ntouch {external_marker}\n")
    external_script.chmod(0o755)

    internal_script = tmp_path / "internal.sh"
    internal_script.write_text(f"#!/bin/sh\ntouch {internal_marker}\n")
    internal_script.chmod(0o755)

    nav = DummyNavigator([], str(tmp_path))
    nav.config.workspace_shortcuts = {
        "2": {
            "internal_commands": [[str(internal_script)]],
            "external_commands": [[str(external_script)]],
        }
    }
    handler = InputHandler(nav)

    handler.pending_comma = True
    handler.comma_sequence = ""
    handler._handle_comma_command(
        ord("w"), 0, None, None, None, nav.dir_manager.current_path
    )
    handler._handle_comma_command(
        ord("2"), 0, None, None, None, nav.dir_manager.current_path
    )

    # External command runs in background; allow brief time for completion
    for _ in range(10):
        if external_marker.exists() and internal_marker.exists():
            break
        time.sleep(0.05)

    assert external_marker.exists()
    assert internal_marker.exists()
    assert nav.terminal_commands and nav.terminal_commands[0] == [str(external_script)]
    assert "workspace" in nav.status_message.lower()


def _enter_command_mode(handler: InputHandler):
    handler.handle_key(None, ord(":"))


def test_parquet_viewer_launches_in_terminal(tmp_path):
    parquet_file = tmp_path / "data.parquet"
    parquet_file.write_bytes(b"PAR1")

    class DummyConfig:
        def __init__(self, mapping):
            self.mapping = mapping

        def get_handler_commands(self, name):
            return self.mapping.get(name, [])

    class DummyDirManager:
        def __init__(self, path):
            self.current_path = path

    class DummyNav:
        def __init__(self):
            self.config = DummyConfig(
                {"parquet_viewer": [["alacritty", "-e", "vixl"]]}
            )
            self.renderer = SimpleNamespace(stdscr=None)
            self.status_message = ""
            self.need_redraw = False
            self.dir_manager = DummyDirManager(str(tmp_path))
            self.terminal_calls = []

        def open_terminal(self, base_path=None, command=None):
            self.terminal_calls.append((base_path, command))
            return True

    nav = DummyNav()
    service = FileActionService(nav)
    service.open_file(str(parquet_file))

    assert nav.terminal_calls
    base_path, command = nav.terminal_calls[0]
    assert command[-1] == str(parquet_file)


def test_command_mode_shell_creates_file(tmp_path):
    nav = FileNavigator(str(tmp_path))
    handler = nav.input_handler

    _enter_command_mode(handler)
    for ch in "!touch cmd_test.txt":
        handler.handle_key(None, ord(ch))
    handler.handle_key(None, 10)

    target = tmp_path / "cmd_test.txt"
    assert target.exists()
    assert "exit 0" in nav.status_message
    assert not nav.command_mode


def test_command_mode_unknown_command(tmp_path):
    nav = FileNavigator(str(tmp_path))
    handler = nav.input_handler

    _enter_command_mode(handler)
    for ch in "test":
        handler.handle_key(None, ord(ch))
    handler.handle_key(None, 10)

    assert "unknown command" in nav.status_message.lower()
    assert not nav.command_mode


def test_command_mode_cancel(tmp_path):
    nav = FileNavigator(str(tmp_path))
    handler = nav.input_handler

    _enter_command_mode(handler)
    handler.handle_key(None, 27)

    assert not nav.command_mode
    assert "cancelled" in nav.status_message.lower()


def _make_nested_items(parent_path: str, child_name: str):
    child_path = os.path.join(parent_path, child_name)
    return [
        (os.path.basename(parent_path), True, parent_path, 0),
        (child_name, False, child_path, 1),
    ]


def test_e_on_file_collapses_parent(tmp_path):
    parent_dir_path = tmp_path / "docs"
    parent_dir_path.mkdir()
    child_name = "notes.txt"
    (parent_dir_path / child_name).write_text("hello")
    parent_dir = os.path.realpath(str(parent_dir_path))
    items = _make_nested_items(parent_dir, child_name)

    nav = DummyNavigator(items, str(tmp_path))
    nav.expanded_nodes.add(parent_dir)
    nav.browser_selected = 1
    handler = InputHandler(nav)

    handler.handle_key(None, ord("e"))

    assert parent_dir not in nav.expanded_nodes
    assert "collapsed" in nav.status_message.lower()
    assert nav.need_redraw


def test_e_on_file_expands_parent(tmp_path):
    parent_dir_path = tmp_path / "docs"
    parent_dir_path.mkdir()
    child_name = "notes.txt"
    (parent_dir_path / child_name).write_text("hello")
    parent_dir = os.path.realpath(str(parent_dir_path))
    items = _make_nested_items(parent_dir, child_name)

    nav = DummyNavigator(items, str(tmp_path))
    nav.browser_selected = 1
    handler = InputHandler(nav)

    handler.handle_key(None, ord("e"))

    assert parent_dir in nav.expanded_nodes
    assert "expanded" in nav.status_message.lower()
    assert nav.need_redraw


def test_e_collapse_positions_cursor(tmp_path):
    parent_dir_path = tmp_path / "docs"
    parent_dir_path.mkdir()
    child_name = "notes.txt"
    (parent_dir_path / child_name).write_text("hello")
    parent_dir = os.path.realpath(str(parent_dir_path))
    items = [
        ("docs", True, parent_dir, 0),
        (child_name, False, os.path.join(parent_dir, child_name), 1),
    ]

    nav = DummyNavigator(items, str(tmp_path))
    nav.expanded_nodes.add(parent_dir)
    nav.browser_selected = 1
    handler = InputHandler(nav)

    handler.handle_key(None, ord("e"))

    assert nav.browser_selected == 0
    assert "collapsed" in nav.status_message.lower()
from file_actions import FileActionService
