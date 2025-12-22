import curses
import os
import time
import shutil


class InputHandler:
    def __init__(self, navigator):
        self.nav = navigator
        self.pending_operator = None
        self.operator_timestamp = 0.0
        self.operator_timeout = 1.0
        self.in_filter_mode = False

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

        # === FILTER MODE ===
        if key == ord('/'):
            if self.in_filter_mode:
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
            elif self.nav.dir_manager.filter_pattern:
                self.nav.dir_manager.filter_pattern = ""
            else:
                self.in_filter_mode = True
                self.nav.dir_manager.filter_pattern = "/"
            return False

        if key == 18:  # Ctrl+R
            self.in_filter_mode = False
            self.nav.dir_manager.filter_pattern = ""
            return False

        if self.in_filter_mode:
            if key in (10, 13, curses.KEY_ENTER):
                self.in_filter_mode = False
                pattern = self.nav.dir_manager.filter_pattern.lstrip("/")
                self.nav.dir_manager.filter_pattern = pattern if pattern else ""
                return False
            if key == 27:  # Esc
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
                return False
            if 32 <= key <= 126:
                char = chr(key)
                if self.nav.dir_manager.filter_pattern == "/":
                    self.nav.dir_manager.filter_pattern = "/" + char
                else:
                    self.nav.dir_manager.filter_pattern += char
                return False
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if len(self.nav.dir_manager.filter_pattern) > 1:
                    self.nav.dir_manager.filter_pattern = self.nav.dir_manager.filter_pattern[:-1]
                else:
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
                return False

        items = self.nav.dir_manager.get_filtered_items()
        total = len(items)
        self.nav.browser_selected = max(0, min(self.nav.browser_selected, total - 1)) if total else 0

        selected_name = None
        selected_is_dir = False
        selected_path = None
        if total > 0:
            selected_name, selected_is_dir = items[self.nav.browser_selected]
            selected_path = os.path.join(self.nav.dir_manager.current_path, selected_name)

        # === Toggle mark with 'm' — now using full path ===
        if key == ord('m'):
            if total > 0:
                full_path = selected_path
                if full_path in self.nav.marked_items:
                    self.nav.marked_items.remove(full_path)
                else:
                    self.nav.marked_items.add(full_path)
                # Auto-advance after marking
                self.nav.browser_selected = (self.nav.browser_selected + 1) % total
            return False

        # === CREATE NEW FILE with 'v' ===
        if key == ord('v'):
            self.nav.create_new_file()
            return False

        # === Other single-key commands ===
        if key == ord('t'):
            self.nav.open_terminal()
            return False

        if key == 12:  # Ctrl+L
            self.nav.clipboard.cleanup()
            return False

        if key == ord('?'):
            self.nav.show_help = True
            return False

        if key == ord(','):
            self.pending_comma = True
            self.comma_timestamp = time.time()
            return False

        if self.pending_comma:
            if key == ord('j') and total:
                self.nav.browser_selected = total - 1
            elif key == ord('k'):
                self.nav.browser_selected = 0
            self.pending_comma = False
            return False

        if key == ord('.'):
            self.nav.dir_manager.toggle_hidden()
            return False

        # === Multi-mark operations ===
        if self.nav.marked_items:
            if key == ord('p'):
                self._copy_marked()
                return False
            if key == ord('x'):
                self._cut_marked()
                return False
            if key == ord('d'):
                self._delete_marked()
                return False

        # === Single-item paste (only when no marks) ===
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

        # === yy / dd operators ===
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

        if self.pending_operator:
            self.pending_operator = None

        # === Navigation ===
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

    # === Updated multi-mark operations using full paths ===
    def _copy_marked(self):
        self._move_or_copy_marked(copy_only=True)

    def _cut_marked(self):
        self._move_or_copy_marked(copy_only=False)

    def _delete_marked(self):
        if not self.nav.marked_items:
            curses.flash()
            return

        success = True
        for full_path in list(self.nav.marked_items):
            try:
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
            except Exception:
                success = False
                break

        if success:
            self.nav.marked_items.clear()
        else:
            curses.flash()

        self.nav.need_redraw = True

    def _move_or_copy_marked(self, copy_only: bool):
        if not self.nav.marked_items:
            curses.flash()
            return

        dest_dir = self.nav.dir_manager.current_path
        success = True

        for full_path in list(self.nav.marked_items):
            if not os.path.exists(full_path):
                success = False
                break

            name = os.path.basename(full_path)
            dest_path = os.path.join(dest_dir, name)

            try:
                # Remove existing destination if it exists (overwrite)
                if os.path.exists(dest_path):
                    if os.path.isdir(dest_path):
                        shutil.rmtree(dest_path)
                    else:
                        os.remove(dest_path)

                if copy_only:
                    if os.path.isdir(full_path):
                        shutil.copytree(full_path, dest_path)
                    else:
                        shutil.copy2(full_path, dest_path)
                else:
                    shutil.move(full_path, dest_path)
            except Exception:
                success = False
                break

        if success:
            self.nav.marked_items.clear()
        else:
            curses.flash()

        self.nav.need_redraw = True

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
