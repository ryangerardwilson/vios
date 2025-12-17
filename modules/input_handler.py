import curses
import os


class InputHandler:
    def __init__(self, navigator):
        self.nav = navigator
        self.pending_operator = None
        self.in_filter_mode = False  # True only while actively typing the filter

    def _normalize_pattern(self, pattern: str) -> str:
        if not pattern:
            return ""
        if any(c in pattern for c in "*?[]"):
            return pattern
        return pattern + "*"

    def handle_key(self, stdscr, key):
        if self.nav.show_help:
            if key == ord('?'):
                self.nav.show_help = False
                return False
            return False

        # === FILTER MODE ===
        if key == ord('/'):
            if self.in_filter_mode:
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
            else:
                self.in_filter_mode = True
                self.nav.dir_manager.filter_pattern = ""
            return False

        if key == 18:  # Ctrl+R
            self.in_filter_mode = False
            self.nav.dir_manager.filter_pattern = ""
            return False

        if self.in_filter_mode:
            if key in (10, 13, curses.KEY_ENTER):
                self.in_filter_mode = False
                return False

            if key == 27:  # Esc
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
                return False

            if 32 <= key <= 126:
                char = chr(key)
                self.nav.dir_manager.filter_pattern += char
                return False

            if key in (curses.KEY_BACKSPACE, 127, 8):
                if self.nav.dir_manager.filter_pattern:
                    self.nav.dir_manager.filter_pattern = self.nav.dir_manager.filter_pattern[:-1]
                return False

            if key in (ord('h'), ord('j'), ord('k'), ord('l'),
                       curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT):
                self.in_filter_mode = False

        items = self.nav.dir_manager.get_filtered_items()
        total = len(items)
        self._clamp_selection(total)

        selected_name = None
        selected_is_dir = False
        selected_path = None
        if total > 0:
            selected_name, selected_is_dir = items[self.nav.browser_selected]
            selected_path = os.path.join(self.nav.dir_manager.current_path, selected_name)

        # Pending operators (yy, dd)
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

        if key == ord('d'):
            self.pending_operator = 'd'
            return False
        if key == ord('y'):
            self.pending_operator = 'y'
            return False

        if key in (curses.KEY_BACKSPACE, curses.KEY_DC, 127, 8) and total > 0:
            try:
                self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=True)
            except Exception:
                curses.flash()
            return False

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

        if key == ord('t'):
            self.nav.open_terminal()
            return False

        if key == ord('v'):
            self.nav.create_new_file()
            return False

        if key == 12:  # Ctrl+L
            self.nav.clipboard.cleanup()
            return False

        if key == ord('?'):
            self.nav.show_help = True
            return False

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
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
        elif key in (curses.KEY_RIGHT, ord('l'), 10, 13) and total > 0:
            if selected_is_dir:
                self.nav.dir_manager.current_path = selected_path
                self.nav.browser_selected = 0
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
            else:
                self.nav.open_file(selected_path)

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
