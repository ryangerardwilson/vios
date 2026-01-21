import curses
import os
from typing import Optional, Callable

from core_navigator import FileNavigator


class Orchestrator:
    def __init__(self, start_path: Optional[str] = None, navigator_factory: Optional[Callable[[str], FileNavigator]] = None):
        self.start_path = os.path.realpath(start_path or os.getcwd())
        self.navigator_factory = navigator_factory or FileNavigator
        self.navigator: Optional[FileNavigator] = None

    def setup(self) -> None:
        if self.navigator is None:
            self.navigator = self.navigator_factory(self.start_path)

    def _run_curses(self) -> None:
        assert self.navigator is not None
        curses.wrapper(self.navigator.run)

    def run(self) -> None:
        self.setup()
        try:
            self._run_curses()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self.navigator and hasattr(self.navigator.clipboard, "cleanup"):
            try:
                self.navigator.clipboard.cleanup()
            except Exception:
                pass
