# ~/Apps/vios/modules/input_handler.py
import curses
import os
import time


class InputHandler:
    def __init__(self, navigator):
        self.nav = navigator
        self.pending_operator = None
        self.operator_timestamp = 0.0
        self.operator_timeout = 1.0
        self.in_filter_mode = False

        # For ,j / ,k
        self.pending_comma = False
        self.comma_timestamp = 0.0
        self.comma_timeout = 0.5

    def _check_operator_timeout(self):
        if self.pending_operator and (time.time() - self.operator_timestamp > self.operator_timeout):
            self.pending_operator = None

    def _check_comma_timeout(self):
        if self.pending_comma and (time.time() - self.comma_timestamp > self.comma_timeout):
            self.pending_comma = False

    def handle_key(self, stdscr, key):
        if self.nav.show_help:
            if key == ord('?'):
                self.nav.show_help = False
                return False
            return False

        self._check_operator_timeout()
        self._check_comma_timeout()

        # === PRESSING / : ENTER OR CANCEL FILTER ===
        if key == ord('/'):
            if self.in_filter_mode:
                # Already typing → cancel everything
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
            elif self.nav.dir_manager.filter_pattern:
                # Not typing, but a filter is active → clear it (cancel)
                self.nav.dir_manager.filter_pattern = ""
            else:
                # No filter active → enter fresh filter mode
                self.in_filter_mode = True
                self.nav.dir_manager.filter_pattern = "/"   # Visual placeholder
            return False

        if key == 18:  # Ctrl+R
            self.in_filter_mode = False
            self.nav.dir_manager.filter_pattern = ""
            return False

        # === INPUT WHILE IN FILTER MODE ===
        if self.in_filter_mode:
            if key in (10, 13, curses.KEY_ENTER):
                # Apply filter: strip visual '/' and exit mode
                self.in_filter_mode = False
                pattern = self.nav.dir_manager.filter_pattern
                if pattern.startswith("/"):
                    # Remove the leading '/' that was only for visual feedback
                    self.nav.dir_manager.filter_pattern = pattern[1:]
                # If nothing was typed, clear it
                if not self.nav.dir_manager.filter_pattern:
                    self.nav.dir_manager.filter_pattern = ""
                return False

            if key == 27:  # Esc
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
                return False

            if 32 <= key <= 126:
                char = chr(key)
                pattern = self.nav.dir_manager.filter_pattern
                if pattern == "/":
                    self.nav.dir_manager.filter_pattern = "/" + char
                else:
                    self.nav.dir_manager.filter_pattern += char
                return False

            if key in (curses.KEY_BACKSPACE, 127, 8):
                pattern = self.nav.dir_manager.filter_pattern
                if len(pattern) > 1:
                    self.nav.dir_manager.filter_pattern = pattern[:-1]
                elif pattern == "/":
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
                return False

            # Navigation keys exit typing mode but keep the current pattern
            if key in (ord('h'), ord('j'), ord('k'), ord('l'),
                       curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT):
                self.in_filter_mode = False
                # If only placeholder, clear pattern
                if self.nav.dir_manager.filter_pattern == "/":
                    self.nav.dir_manager.filter_pattern = ""

        else:
            # === COMMA COMMANDS ===
            if key == ord(','):
                self.pending_comma = True
                self.comma_timestamp = time.time()
                return False

            if self.pending_comma:
                if key == ord('j'):
                    items = self.nav.dir_manager.get_filtered_items()
                    if items:
                        self.nav.browser_selected = len(items) - 1
                    self.pending_comma = False
                    return False
                elif key == ord('k'):
                    self.nav.browser_selected = 0
                    self.pending_comma = False
                    return False
                else:
                    self.pending_comma = False

            # === DOT TOGGLE ===
            if key == ord('.'):
                self.nav.dir_manager.toggle_hidden()
                return False

        # === NORMAL NAVIGATION AND COMMANDS ===
        items = self.nav.dir_manager.get_filtered_items()
        total = len(items)
        self._clamp_selection(total)

        selected_name = None
        selected_is_dir = False
        selected_path = None
        if total > 0:
            selected_name, selected_is_dir = items[self.nav.browser_selected]
            selected_path = os.path.join(self.nav.dir_manager.current_path, selected_name)

        # Operators
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
            self.operator_timestamp = time.time()
            return False

        if key == ord('y'):
            self.pending_operator = 'y'
            self.operator_timestamp = time.time()
            return False

        if self.pending_operator in ('d', 'y'):
            self.pending_operator = None

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
