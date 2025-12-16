import curses
import subprocess
import os

from .directory_manager import DirectoryManager, pretty_path, is_text_file
from .clipboard_manager import ClipboardManager
from .ui_renderer import UIRenderer
from .input_handler import InputHandler


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()

        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)

        self.show_help = False  # Hidden by default
        self.browser_selected = 0
        self.need_redraw = True

        self.cheatsheet = r"""
VIOS CHEATSHEET

Navigation
  h               Parent directory
  l / Enter       Enter directory or open text file in Vim
  j               Down
  k               Up

Clipboard
  y               Start yank (copy) — yy to confirm
  d               Start cut/delete — dd to confirm
  Backspace/Del   Immediate cut selected item
  p               Paste (auto-rename on conflict)
  Ctrl+L          Clear clipboard

Other
  t               Open terminal here
  ?               Toggle this help
  q / Esc         Quit
"""
    def _open_in_vim(self, filepath: str):
        curses.endwin()
        try:
            subprocess.call([
                "vim",
                "-c", f"cd {self.dir_manager.current_path}",
                filepath
            ])
        except FileNotFoundError:
            pass
        finally:
            self.need_redraw = True

    def open_terminal(self):
        try:
            subprocess.Popen(
                ["alacritty", "--working-directory", self.dir_manager.current_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            curses.flash()
        self.need_redraw = True

    def run(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 6):
            curses.init_pair(i, [curses.COLOR_CYAN, curses.COLOR_WHITE, curses.COLOR_YELLOW,
                                 curses.COLOR_RED, curses.COLOR_GREEN][i-1], -1)

        self.renderer.stdscr = stdscr

        while True:
            if self.need_redraw:
                self.renderer.render()
                self.need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue

            if self.input_handler.handle_key(stdscr, key):
                break  # Quit

            self.need_redraw = True
