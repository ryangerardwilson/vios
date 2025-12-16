# ~/Apps/vios/modules/input_handler.py
import curses
import os

from .directory_manager import pretty_path, is_text_file


class InputHandler:
    def __init__(self, navigator):
        self.nav = navigator
        # State for pending Vim-like operators (dd, yy)
        self.pending_operator = None  # None, 'd', or 'y'

    def handle_key(self, stdscr, key):
        # Close help on any key press
        if self.nav.show_help:
            self.nav.show_help = False
            self.pending_operator = None
            return

        # Global: Ctrl+D toggle browser
        if key == 4:  # Ctrl+D
            if not self.nav.completion.in_completion:
                self.nav.show_file_list = not self.nav.show_file_list
                if not self.nav.show_file_list:
                    self.nav.hjkl_mode = False
                    self.pending_operator = None
            return

        # Completion mode has priority
        if self.nav.completion.in_completion:
            result = self.nav.completion.handle_key(stdscr, key)
            if result is not None:
                self.nav.command_buffer = result
                self.nav.cursor_pos = len(self.nav.command_buffer)
                self.nav.completion.in_completion = False
            elif 32 <= key <= 126:  # Printable ASCII characters
                # Insert the typed character and restart completion (incremental narrowing)
                char = chr(key)
                self.nav.command_buffer = (
                    self.nav.command_buffer[:self.nav.cursor_pos] +
                    char +
                    self.nav.command_buffer[self.nav.cursor_pos:]
                )
                self.nav.cursor_pos += 1
                # Restart completion with the new partial
                self.nav.completion.start_completion(self.nav.command_buffer, self.nav.cursor_pos)
            else:
                # Any other unhandled key: exit completion mode
                self.nav.completion.in_completion = False
            self.pending_operator = None
            return

        # HJKL navigation mode
        if self.nav.hjkl_mode and self.nav.show_file_list:
            self._handle_hjkl_mode(stdscr, key)
            return

        # Normal terminal input mode
        self._handle_terminal_mode(stdscr, key)

    def _clamp_selection(self, total):
        """Ensure browser_selected is valid for current item count"""
        if total == 0:
            self.nav.browser_selected = 0
        else:
            self.nav.browser_selected = min(self.nav.browser_selected, total - 1)

    def _get_unique_name(self, dest_dir: str, base_name: str) -> str:
        """Return a unique name in dest_dir, adding (1), (2), etc. if needed"""
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

    def _handle_hjkl_mode(self, stdscr, key):
        items = self.nav.dir_manager.get_filtered_items()
        total = len(items)

        # Always clamp selection after list may have changed
        self._clamp_selection(total)

        if total == 0:
            self.pending_operator = None

        # Safe to access selected item only if total > 0
        selected_name = None
        selected_is_dir = False
        selected_path = None
        if total > 0:
            selected_name, selected_is_dir = items[self.nav.browser_selected]
            selected_path = os.path.join(self.nav.dir_manager.current_path, selected_name)

        # === Handle second key of dd or yy ===
        if self.pending_operator == 'd':
            if key == ord('d') and total > 0:
                try:
                    self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=True)
                except Exception:
                    curses.flash()
            self.pending_operator = None
            return

        if self.pending_operator == 'y':
            if key == ord('y') and total > 0:
                try:
                    self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=False)
                except Exception:
                    curses.flash()
            self.pending_operator = None
            return

        # === First key: start pending operator ===
        if key == ord('d'):
            self.pending_operator = 'd'
            return
        if key == ord('y'):
            self.pending_operator = 'y'
            return

        # === Backspace / Delete → immediate cut ===
        if key in (curses.KEY_BACKSPACE, curses.KEY_DC, 127, 8):
            if total > 0:
                try:
                    self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=True)
                except Exception:
                    curses.flash()
            return

        # === NEW: p → paste yanked/cut item ===
        if key == ord('p'):
            if not self.nav.clipboard.yanked_temp_path:
                curses.flash()
                return

            try:
                new_name = self._get_unique_name(
                    self.nav.dir_manager.current_path,
                    self.nav.clipboard.yanked_original_name
                )
                self.nav.clipboard.paste(self.nav.dir_manager.current_path, new_name)
            except Exception:
                curses.flash()
            return

        # === Existing navigation actions ===
        if key == ord('t'):
            self.nav.open_terminal()

        elif key == 12:  # Ctrl+L
            self.nav.clipboard.cleanup()

        elif key in (curses.KEY_UP, ord('k')) and total > 0:
            self.nav.browser_selected = (self.nav.browser_selected - 1) % total

        elif key in (curses.KEY_DOWN, ord('j')) and total > 0:
            self.nav.browser_selected = (self.nav.browser_selected + 1) % total

        elif key in (curses.KEY_LEFT, ord('h')):
            parent = os.path.dirname(self.nav.dir_manager.current_path)
            if parent != self.nav.dir_manager.current_path:
                self.nav.dir_manager.current_path = parent
                self.nav.browser_selected = 0

        elif key in (curses.KEY_RIGHT, ord('l'), 10, 13) and total > 0:
            path = selected_path
            if selected_is_dir:
                self.nav.dir_manager.current_path = path
                self.nav.browser_selected = 0
            elif is_text_file(path):
                self.nav._open_in_vim(path)
            else:
                curses.flash()

        elif key == 27:  # Esc
            self.nav.hjkl_mode = False
            self.pending_operator = None

    def _handle_terminal_mode(self, stdscr, key):
        if key in (10, 13):  # Enter
            cmd = self.nav.command_buffer.strip()
            self.nav.command_buffer = ""
            self.nav.cursor_pos = 0

            if cmd == "help":
                self.nav.show_help = True
            elif cmd == "hjkl":
                self.nav.show_file_list = True
                self.nav.hjkl_mode = True
            elif cmd:
                if not self.nav.history or self.nav.history[-1] != cmd:
                    self.nav.history.append(cmd)
                self.nav.history_index = len(self.nav.history)
                self.nav.cmd_processor.run_shell_command(cmd)

        elif key == 9:  # Tab
            self.nav.completion.start_completion(self.nav.command_buffer, self.nav.cursor_pos)

        # History navigation
        elif key == 16:  # Ctrl+P
            self._history_up()
        elif key == 14:  # Ctrl+N
            self._history_down()

        # Movement and editing
        elif key in (curses.KEY_LEFT, 2):
            if self.nav.cursor_pos > 0:
                self.nav.cursor_pos -= 1
        elif key in (curses.KEY_RIGHT, 6):
            if self.nav.cursor_pos < len(self.nav.command_buffer):
                self.nav.cursor_pos += 1
        elif key == 1:  # Ctrl+A
            self.nav.cursor_pos = 0
        elif key == 5:  # Ctrl+E
            self.nav.cursor_pos = len(self.nav.command_buffer)
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.nav.cursor_pos > 0:
                self.nav.command_buffer = (self.nav.command_buffer[:self.nav.cursor_pos-1] +
                                           self.nav.command_buffer[self.nav.cursor_pos:])
                self.nav.cursor_pos -= 1
        elif key == 4:  # Ctrl+D delete forward
            if self.nav.cursor_pos < len(self.nav.command_buffer):
                self.nav.command_buffer = (self.nav.command_buffer[:self.nav.cursor_pos] +
                                           self.nav.command_buffer[self.nav.cursor_pos+1:])
        elif key == 23:  # Ctrl+W
            self._delete_word_left()
        elif key == 27:  # Esc → Alt sequences
            self._handle_alt_keys(stdscr)
        elif 32 <= key <= 126:
            self.nav.command_buffer = (self.nav.command_buffer[:self.nav.cursor_pos] +
                                       chr(key) +
                                       self.nav.command_buffer[self.nav.cursor_pos:])
            self.nav.cursor_pos += 1

    def _history_up(self):
        if self.nav.history:
            if self.nav.history_index == len(self.nav.history):
                self.nav.current_input = self.nav.command_buffer
            self.nav.history_index = max(0, self.nav.history_index - 1)
            self.nav.command_buffer = self.nav.history[self.nav.history_index]
            self.nav.cursor_pos = len(self.nav.command_buffer)

    def _history_down(self):
        if self.nav.history and self.nav.history_index < len(self.nav.history):
            self.nav.history_index += 1
            if self.nav.history_index == len(self.nav.history):
                self.nav.command_buffer = self.nav.current_input
            else:
                self.nav.command_buffer = self.nav.history[self.nav.history_index]
            self.nav.cursor_pos = len(self.nav.command_buffer)

    def _delete_word_left(self):
        if self.nav.cursor_pos > 0:
            end = self.nav.cursor_pos
            while end > 0 and self.nav.command_buffer[end-1].isspace():
                end -= 1
            while end > 0 and not self.nav.command_buffer[end-1].isspace():
                end -= 1
            self.nav.command_buffer = self.nav.command_buffer[:end] + self.nav.command_buffer[self.nav.cursor_pos:]
            self.nav.cursor_pos = end

    def _handle_alt_keys(self, stdscr):
        key2 = stdscr.getch()
        if key2 == -1:
            return
        if key2 in (curses.KEY_LEFT, ord('b')):
            while self.nav.cursor_pos > 0 and self.nav.command_buffer[self.nav.cursor_pos-1].isspace():
                self.nav.cursor_pos -= 1
            while self.nav.cursor_pos > 0 and not self.nav.command_buffer[self.nav.cursor_pos-1].isspace():
                self.nav.cursor_pos -= 1
        elif key2 in (curses.KEY_RIGHT, ord('f')):
            while (self.nav.cursor_pos < len(self.nav.command_buffer) and
                   not self.nav.command_buffer[self.nav.cursor_pos].isspace()):
                self.nav.cursor_pos += 1
            while (self.nav.cursor_pos < len(self.nav.command_buffer) and
                   self.nav.command_buffer[self.nav.cursor_pos].isspace()):
                self.nav.cursor_pos += 1
        elif key2 == ord('d'):
            start = self.nav.cursor_pos
            while start < len(self.nav.command_buffer) and not self.nav.command_buffer[start].isspace():
                start += 1
            while start < len(self.nav.command_buffer) and self.nav.command_buffer[start].isspace():
                start += 1
            self.nav.command_buffer = self.nav.command_buffer[:self.nav.cursor_pos] + self.nav.command_buffer[start:]
