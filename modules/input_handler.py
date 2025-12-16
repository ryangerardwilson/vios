# ~/Apps/vios/modules/input_handler.py
import curses
import os

from .directory_manager import is_text_file


class InputHandler:
    def __init__(self, navigator):
        self.nav = navigator
        self.pending_operator = None  # 'd' or 'y'

    def handle_key(self, stdscr, key):
        # If help is shown, only ? (toggle) or q/Esc (quit app) are allowed
        if self.nav.show_help:
            if key == ord('?'):
                self.nav.show_help = False
                return False
            if key in (ord('q'), 27):  # q or Esc → quit entire app
                return True
            return False  # ignore all other keys while help is open

        # Normal browser mode below
        items = self.nav.dir_manager.get_filtered_items()
        total = len(items)
        self._clamp_selection(total)

        selected_name = None
        selected_is_dir = False
        selected_path = None
        if total > 0:
            selected_name, selected_is_dir = items[self.nav.browser_selected]
            selected_path = os.path.join(self.nav.dir_manager.current_path, selected_name)

        # Confirm pending operator
        if self.pending_operator == 'd' and key == ord('d') and total > 0:
            try:
                self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=True)
            except Exception:
                curses.flash()
            self.pending_operator = None
            return False

        if self.pending_operator == 'y' and key == ord('y') and total > 0:
            try:
                self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=False)
            except Exception:
                curses.flash()
            self.pending_operator = None
            return False

        # Start pending operator
        if key == ord('d'):
            self.pending_operator = 'd'
            return False
        if key == ord('y'):
            self.pending_operator = 'y'
            return False

        # Immediate cut
        if key in (curses.KEY_BACKSPACE, curses.KEY_DC, 127, 8) and total > 0:
            try:
                self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=True)
            except Exception:
                curses.flash()
            return False

        # Paste
        if key == ord('p') and self.nav.clipboard.yanked_temp_path:
            new_name = self._get_unique_name(
                self.nav.dir_manager.current_path,
                self.nav.clipboard.yanked_original_name
            )
            try:
                self.nav.clipboard.paste(self.nav.dir_manager.current_path, new_name)
            except Exception:
                curses.flash()
            return False

        # Open terminal
        if key == ord('t'):
            self.nav.open_terminal()
            return False

        # Clear clipboard
        if key == 12:  # Ctrl+L
            self.nav.clipboard.cleanup()
            return False

        # Toggle help
        if key == ord('?'):
            self.nav.show_help = True
            return False

        # Quit (only when not in help screen)
        if key in (ord('q'), 27):
            return True

        # Navigation
        if key in (curses.KEY_UP, ord('k')) and total > 0:
            self.nav.browser_selected = (self.nav.browser_selected - 1) % total
        elif key in (curses.KEY_DOWN, ord('j')) and total > 0:
            self.nav.browser_selected = (self.nav.browser_selected + 1) % total
        elif key in (curses.KEY_LEFT, ord('h')):
            parent = os.path.dirname(self.nav.dir_manager.current_path)
            if parent != self.nav.dir_manager.current_path:
                self.nav.dir_manager.current_path = parent
                self.nav.browser_selected = 0
        elif key in (curses.KEY_RIGHT, ord('l'), 10, 13) and total > 0:
            if selected_is_dir:
                self.nav.dir_manager.current_path = selected_path
                self.nav.browser_selected = 0
            elif is_text_file(selected_path):
                self.nav._open_in_vim(selected_path)
            else:
                curses.flash()

        return False

    def _clamp_selection(self, total):
        if total == 0:
            self.nav.browser_selected = 0
        else:
            self.nav.browser_selected = min(self.nav.browser_selected, total - 1)

    def _get_unique_name(self, dest_dir: str, base_name: str) -> str:
        dest_path = os.path.join(dest_dir, base_name)
        if not os.path.exists(dest_path):
            return base_name
        name, ext = os.path.splitext(base_name)
        counter = 1
        while True:
            new_name = f"{name} ({counter}){ext}"
            if not os.path.exists(os.path.join(dest_dir, new_name)):
                return new_name
            counter += 1
