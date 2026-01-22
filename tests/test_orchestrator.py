import curses
import os
from pathlib import Path


from orchestrator import Orchestrator


class DummyClipboard:
    def __init__(self):
        self.cleaned = False

    def cleanup(self):
        self.cleaned = True


class DummyRenderer:
    def __init__(self):
        self.render_calls = 0
        self.stdscr = None

    def render(self):
        self.render_calls += 1


class DummyInputHandler:
    def __init__(self):
        self.handled = False

    def handle_key(self, stdscr, key):
        self.handled = True
        return True


class DummyNavigator:
    def __init__(self, start_path: str):
        self.start_path = start_path
        self.clipboard = DummyClipboard()
        self.renderer = DummyRenderer()
        self.input_handler = DummyInputHandler()
        self.need_redraw = True


def test_setup_creates_navigator(tmp_path: Path):
    start = tmp_path / "start"
    start.mkdir()

    orchestrator = Orchestrator(
        start_path=str(start),
        navigator_factory=DummyNavigator,
    )

    orchestrator.setup()

    assert isinstance(orchestrator.navigator, DummyNavigator)
    assert orchestrator.navigator.start_path == os.path.realpath(str(start))


def test_run_invokes_curses_wrapper_and_cleanup(monkeypatch):
    dummy = DummyNavigator(os.getcwd())
    orchestrator = Orchestrator(
        start_path=os.getcwd(),
        navigator_factory=lambda _: dummy,
    )

    class FakeStdScr:
        def __init__(self):
            self._first = True

        def getmaxyx(self):
            return (24, 80)

        def keypad(self, flag):
            pass

        def leaveok(self, flag):
            pass

        def idlok(self, flag):
            pass

        def timeout(self, value):
            pass

        def move(self, y, x):
            pass

        def clrtoeol(self):
            pass

        def addstr(self, y, x, string, *args):
            pass

        def refresh(self):
            pass

        def getch(self):
            if self._first:
                self._first = False
                return ord("a")
            return ord("a")

    fake_screen = FakeStdScr()

    monkeypatch.setattr(curses, "wrapper", lambda func: func(fake_screen))
    monkeypatch.setattr(curses, "curs_set", lambda *args, **kwargs: None)
    monkeypatch.setattr(curses, "start_color", lambda *args, **kwargs: None)
    monkeypatch.setattr(curses, "use_default_colors", lambda *args, **kwargs: None)
    monkeypatch.setattr(curses, "init_pair", lambda *args, **kwargs: None)

    orchestrator.run()

    assert dummy.clipboard.cleaned is True
    assert dummy.renderer.render_calls >= 1
    assert dummy.input_handler.handled is True
    assert dummy.renderer.stdscr is fake_screen
