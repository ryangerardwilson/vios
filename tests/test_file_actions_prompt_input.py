import curses
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from file_actions import FileActionService


class FakeStdScr:
    def __init__(self, keys, max_y=24, max_x=80):
        self.keys = list(keys)
        self.max_y = max_y
        self.max_x = max_x
        self.timeout_calls = []
        self.moves = []

    def getmaxyx(self):
        return self.max_y, self.max_x

    def move(self, y, x):
        self.moves.append((y, x))

    def clrtoeol(self):
        return None

    def addstr(self, *_args, **_kwargs):
        return None

    def refresh(self):
        return None

    def timeout(self, value):
        self.timeout_calls.append(value)

    def getch(self):
        if self.keys:
            return self.keys.pop(0)
        return -1


def _make_nav(stdscr):
    return SimpleNamespace(
        renderer=SimpleNamespace(stdscr=stdscr),
        dir_manager=SimpleNamespace(current_path="."),
        input_handler=SimpleNamespace(_get_unique_name=lambda _base, name: name),
        need_redraw=False,
        status_message="",
        browser_selected=0,
        notify_directory_changed=lambda *args: None,
        build_display_items=lambda: [],
    )


def test_prompt_supports_cursor_insert_and_backspace(monkeypatch):
    events = []
    monkeypatch.setattr("file_actions.curses.curs_set", lambda n: events.append(n))
    stdscr = FakeStdScr(
        [curses.KEY_LEFT, curses.KEY_LEFT, ord("X"), 127, 13]
    )  # left,left,insert,backspace,enter
    nav = _make_nav(stdscr)
    service = FileActionService(nav)

    result = service._prompt_for_input("Rename: ", initial_text="file.txt")

    assert result == "file.txt"
    assert events == [1, 0]
    assert -1 in stdscr.timeout_calls
    assert 40 in stdscr.timeout_calls
    assert nav.need_redraw is True


def test_prompt_supports_ctrl_w_and_meta_word_motion(monkeypatch):
    events = []
    monkeypatch.setattr("file_actions.curses.curs_set", lambda n: events.append(n))
    keys = [
        ord("a"),
        ord("l"),
        ord("p"),
        ord("h"),
        ord("a"),
        ord(" "),
        ord("b"),
        ord("e"),
        ord("t"),
        ord("a"),
        27,
        ord("b"),
        27,
        ord("b"),
        27,
        ord("f"),
        ord("Z"),
        23,  # Ctrl+W
        13,
    ]
    stdscr = FakeStdScr(keys)
    nav = _make_nav(stdscr)
    service = FileActionService(nav)

    result = service._prompt_for_input("New file: ")

    assert result == "beta"
    assert events == [1, 0]


def test_prompt_escape_cancels(monkeypatch):
    events = []
    monkeypatch.setattr("file_actions.curses.curs_set", lambda n: events.append(n))
    stdscr = FakeStdScr([27])
    nav = _make_nav(stdscr)
    service = FileActionService(nav)

    result = service._prompt_for_input("New dir: ", initial_text="temp")

    assert result is None
    assert events == [1, 0]


def test_rename_selected_uses_editor_and_renames(tmp_path, monkeypatch):
    monkeypatch.setattr("file_actions.curses.curs_set", lambda _n: None)
    src = tmp_path / "old.txt"
    src.write_text("x", encoding="utf-8")
    stdscr = FakeStdScr(
        [23, 23, ord("n"), ord("e"), ord("w"), ord("."), ord("t"), ord("x"), ord("t"), 13]
    )
    notified = []

    nav = SimpleNamespace(
        renderer=SimpleNamespace(stdscr=stdscr),
        dir_manager=SimpleNamespace(current_path=str(tmp_path)),
        input_handler=SimpleNamespace(_get_unique_name=lambda _base, name: name),
        need_redraw=False,
        status_message="",
        browser_selected=0,
        notify_directory_changed=lambda *paths: notified.extend(paths),
        build_display_items=lambda: [("old.txt", False, str(src), 0)],
    )
    service = FileActionService(nav)

    service.rename_selected()

    dst = tmp_path / "new.txt"
    assert not src.exists()
    assert dst.exists()
    assert notified
    assert os.path.realpath(notified[0]) == os.path.realpath(tmp_path)
    assert nav.status_message == "Renamed to new.txt"
