import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from input_handler import InputHandler


class DummyClipboard:
    def __init__(self):
        self.has_entries = False
        self.entry_count = 0


class DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyNavigator:
    def __init__(self, root: Path):
        root = Path(root)
        self.dir_manager = SimpleNamespace(current_path=str(root), filter_pattern="")
        self.renderer = SimpleNamespace(stdscr=None)
        self.file_actions = SimpleNamespace(prompt_confirmation=lambda message: True)
        self.clipboard = DummyClipboard()
        self.marked_items: set[str] = set()
        self.expanded_nodes: set[str] = set()
        self.visual_mode = False
        self.status_message = ""
        self.need_redraw = False
        self.browser_selected = 0
        self.layout_mode = "list"
        self.leader_sequence = ""
        self.command_popup_visible = False
        self.show_help = False
        self.command_mode = False
        self.command_history: list[str] = []
        self.command_history_index = None
        self.command_buffer = ""
        self.command_popup_lock = DummyLock()
        self.display_items = []
        self.visual_indices: list[int] = []
        self.notified: list[tuple[str, ...]] = []

    def build_display_items(self):
        return list(self.display_items)

    def get_visual_indices(self, _total):
        return list(self.visual_indices)

    def exit_visual_mode(self, **_kwargs):
        self.visual_mode = False

    def enter_visual_mode(self, _index):  # pragma: no cover
        self.visual_mode = True

    def update_visual_active(self, _idx):
        pass

    def notify_directory_changed(self, *paths):
        if not paths:
            self.notified.append(tuple())
            return
        real = tuple(sorted(os.path.realpath(p) for p in paths if p))
        self.notified.append(real)

    def collapse_expansions_under(self, _path):
        pass

    def reset_to_home(self):  # pragma: no cover
        pass

    def go_history_back(self):
        return False

    def go_history_forward(self):
        return False

    def enter_matrix_mode(self):  # pragma: no cover
        pass

    def enter_list_mode(self):  # pragma: no cover
        pass

    def change_directory(self, _path):
        return False

    def remember_matrix_position(self):  # pragma: no cover
        pass

    def discard_matrix_position(self, _path):  # pragma: no cover
        pass

    def open_file(self, _path):  # pragma: no cover
        pass

    def open_terminal(self):  # pragma: no cover
        pass


@pytest.fixture
def handler(tmp_path):
    nav = DummyNavigator(tmp_path)
    ih = InputHandler(nav)
    return ih, nav


def create_file(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_text("data")
    return path


def create_directory(directory: Path, name: str) -> Path:
    path = directory / name
    path.mkdir()
    (path / "inner.txt").write_text("child")
    return path


def test_delete_marked_requires_confirmation_accept(handler, tmp_path):
    ih, nav = handler
    file_path = create_file(tmp_path, "file.txt")
    nav.marked_items.add(str(file_path))

    prompts = []

    def confirm(message):
        prompts.append(message)
        return True

    nav.file_actions.prompt_confirmation = confirm

    ih._delete_marked()

    assert not file_path.exists()
    assert nav.marked_items == set()
    assert nav.status_message == "Deleted 1 item"
    assert nav.need_redraw is True
    assert prompts and prompts[0].startswith("Delete")
    parent_real = os.path.realpath(tmp_path)
    assert any(parent_real in notice for notice in nav.notified)


def test_delete_marked_cancel(handler, tmp_path):
    ih, nav = handler
    file_path = create_file(tmp_path, "file.txt")
    nav.marked_items.add(str(file_path))

    nav.file_actions.prompt_confirmation = lambda message: False

    ih._delete_marked()

    assert file_path.exists()
    assert str(file_path) in nav.marked_items
    assert nav.status_message == "Deletion cancelled"
    assert nav.need_redraw is True


def test_single_delete_cancel(handler, tmp_path):
    ih, nav = handler
    file_path = create_file(tmp_path, "solo.txt")

    nav.display_items = [("solo.txt", False, str(file_path), 0)]
    nav.browser_selected = 0
    nav.file_actions.prompt_confirmation = lambda message: False

    ih.handle_key(None, ord("x"))

    assert file_path.exists()
    assert nav.status_message == "Deletion cancelled"
    assert nav.need_redraw is True


def test_single_delete_confirm(handler, tmp_path):
    ih, nav = handler
    file_path = create_file(tmp_path, "solo.txt")

    nav.display_items = [("solo.txt", False, str(file_path), 0)]
    nav.browser_selected = 0

    prompts = []
    nav.file_actions.prompt_confirmation = lambda message: prompts.append(message) or True

    ih.handle_key(None, ord("x"))

    assert not file_path.exists()
    assert nav.status_message == "Deleted solo.txt"
    assert nav.need_redraw is True
    assert prompts and '"solo.txt"' in prompts[0]
    parent_real = os.path.realpath(tmp_path)
    assert any(parent_real in notice for notice in nav.notified)


def test_visual_delete_confirm(handler, tmp_path):
    ih, nav = handler
    file_path = create_file(tmp_path, "one.txt")
    dir_path = create_directory(tmp_path, "folder")

    nav.display_items = [
        ("one.txt", False, str(file_path), 0),
        ("folder", True, str(dir_path), 0),
    ]
    nav.visual_mode = True
    nav.visual_indices = [0, 1]
    nav.file_actions.prompt_confirmation = lambda message: True

    ih.handle_key(None, ord("x"))

    assert not file_path.exists()
    assert not dir_path.exists()
    assert nav.status_message == "Deleted 2 items"
    assert nav.visual_mode is False
    assert nav.need_redraw is True


def test_visual_delete_cancel(handler, tmp_path):
    ih, nav = handler
    file_path = create_file(tmp_path, "one.txt")
    dir_path = create_directory(tmp_path, "folder")

    nav.display_items = [
        ("one.txt", False, str(file_path), 0),
        ("folder", True, str(dir_path), 0),
    ]
    nav.visual_mode = True
    nav.visual_indices = [0, 1]
    nav.file_actions.prompt_confirmation = lambda message: False

    ih.handle_key(None, ord("x"))

    assert file_path.exists()
    assert dir_path.exists()
    assert nav.status_message == "Deletion cancelled"
    assert nav.visual_mode is True
    assert nav.need_redraw is True
