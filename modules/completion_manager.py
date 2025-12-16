# ~/Apps/vios/modules/completion_manager.py
import curses
import os

from .directory_manager import pretty_path


class CompletionManager:
    def __init__(self, dir_manager):
        self.dir_manager = dir_manager
        self.in_completion = False
        self.prefix = ""
        self.base_dir = ""
        self.matches = []
        self.selected = 0

    def start_completion(self, command_buffer: str, cursor_pos: int):
        before_cursor = command_buffer[:cursor_pos].rstrip()
        parts = before_cursor.split()
        if not parts:
            return

        self.prefix = " ".join(parts[:-1])
        if self.prefix:
            self.prefix += " "
        partial = parts[-1]

        self.base_dir = ""
        self._refresh(partial)

    def _refresh(self, partial=""):
        full_partial = os.path.join(self.base_dir, partial)
        matches = self.dir_manager.get_tab_completions(full_partial)

        if len(matches) >= 1:
            self.matches = matches
            self.selected = 0
            self.in_completion = True
            return None

        else:
            self.in_completion = False
            curses.flash()
            return None

    def handle_key(self, stdscr, key):
        if not self.matches:
            self.in_completion = False
            return None

        total = len(self.matches)

        if key in (curses.KEY_UP, ord('k')):
            self.selected = (self.selected - 1) % total
        elif key in (curses.KEY_DOWN, ord('j')):
            self.selected = (self.selected + 1) % total
        elif key in (curses.KEY_LEFT, ord('h')):
            if self.base_dir:
                self.base_dir = os.path.dirname(self.base_dir.rstrip("/"))
                if not self.base_dir or self.base_dir == ".":
                    self.base_dir = ""
                return self._refresh("")
        elif key in (curses.KEY_RIGHT, ord('l')):
            selected_rel = self.matches[self.selected]
            full_path = os.path.join(self.dir_manager.current_path, self.base_dir, selected_rel.rstrip("/"))
            if os.path.isdir(full_path):
                self.base_dir = os.path.join(self.base_dir, selected_rel.rstrip("/")) + "/"
                return self._refresh("")
            else:
                insert = pretty_path(full_path) + " "
                self.in_completion = False
                return self.prefix + insert
        elif key in (10, 13):  # Enter
            current_dir = os.path.join(self.dir_manager.current_path, self.base_dir.rstrip("/"))
            insert = pretty_path(current_dir) + "/ "
            self.in_completion = False
            return self.prefix + insert
        elif key in (9, 27):  # Tab or Esc
            self.in_completion = False

        return None
