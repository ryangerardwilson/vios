import curses
import os
from typing import Optional, Callable, Any

from core_navigator import FileNavigator


class Orchestrator:
    def __init__(
        self,
        start_path: Optional[str] = None,
        navigator_factory: Optional[Callable[[str], Any]] = None,
    ):
        self.start_path = os.path.realpath(start_path or os.getcwd())
        self.navigator_factory = navigator_factory or FileNavigator
        self.navigator: Optional[Any] = None

    def setup(self) -> None:
        if self.navigator is None:
            self.navigator = self.navigator_factory(self.start_path)

    def _curses_main(self, stdscr) -> None:
        assert self.navigator is not None
        navigator = self.navigator

        navigator.renderer.stdscr = stdscr

        curses.curs_set(0)
        try:
            curses.start_color()
            curses.use_default_colors()
        except Exception:
            pass

        try:
            stdscr.keypad(True)
            stdscr.leaveok(True)
            stdscr.idlok(True)
        except Exception:
            pass

        stdscr.timeout(40)
        navigator.need_redraw = True

        while True:
            should_render = navigator.need_redraw or navigator.layout_mode == "matrix"
            if should_render:
                navigator.renderer.render()
                if navigator.layout_mode != "matrix":
                    navigator.need_redraw = False
                else:
                    navigator.need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue

            if navigator.input_handler.handle_key(stdscr, key):
                break

            navigator.need_redraw = True

    def _run_curses(self) -> None:
        curses.wrapper(self._curses_main)

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
