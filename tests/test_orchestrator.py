import os
from pathlib import Path

import pytest  # type: ignore

from orchestrator import Orchestrator


class DummyClipboard:
    def __init__(self):
        self.cleaned = False

    def cleanup(self):
        self.cleaned = True


class DummyNavigator:
    def __init__(self, start_path: str):
        self.start_path = start_path
        self.clipboard = DummyClipboard()
        self.ran = False

    def run(self, stdscr):
        self.ran = True


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

    ran = {"value": False}

    def fake_wrapper():
        ran["value"] = True

    monkeypatch.setattr(orchestrator, "_run_curses", fake_wrapper)

    orchestrator.run()

    assert ran["value"] is True
    assert dummy.clipboard.cleaned is True
