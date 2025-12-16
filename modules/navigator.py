# ~/Apps/vios/modules/navigator.py
import curses
import os
import subprocess
import shutil

from .directory_manager import DirectoryManager, is_text_file, pretty_path
from .clipboard_manager import ClipboardManager
from .command_processor import CommandProcessor


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()
        self.cmd_processor = CommandProcessor(self.dir_manager, self._open_in_vim)

        self.command_mode = False
        self.show_file_list = False
        self.command_buffer = ""

        # Completion state
        self.in_completion = False
        self.completion_prefix = ""
        self.completion_base_dir = ""      # e.g. "Documents/data_analytics/"
        self.completion_matches = []
        self.completion_selected = 0

        self.browser_selected = 0

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

    def open_terminal(self):
        try:
            subprocess.Popen(
                ["alacritty", "--working-directory", self.dir_manager.current_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            curses.flash()

    def prompt_new_name(self, stdscr, original_name: str) -> str | None:
        curses.curs_set(1)
        stdscr.nodelay(False)
        max_y, max_x = stdscr.getmaxyx()
        curses.echo()

        prompt = f"Name exists: {original_name} -> New name: "
        input_str = original_name

        while True:
            stdscr.clear()
            try:
                stdscr.addstr(max_y//2 - 1, max(0, (max_x - len(prompt + input_str))//2),
                              prompt + input_str, curses.A_BOLD)
                stdscr.addstr(max_y//2 + 1, max(0, (max_x - 40)//2),
                              "Enter = confirm, ESC = cancel", curses.color_pair(2))
            except curses.error:
                pass
            stdscr.refresh()

            key = stdscr.getch()
            if key in (10, 13):
                new_name = input_str.strip()
                if new_name:
                    curses.noecho()
                    curses.curs_set(0)
                    stdscr.nodelay(True)
                    return new_name
            elif key == 27:
                break
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                input_str = input_str[:-1]
            elif 32 <= key <= 126:
                input_str += chr(key)

        curses.noecho()
        curses.curs_set(0)
        stdscr.nodelay(True)
        return None

    def run(self, stdscr):
        curses.curs_set(1)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_GREEN, -1)
        stdscr.bkgd(" ", curses.color_pair(2))
        stdscr.nodelay(True)

        need_redraw = True

        while True:
            # Display logic
            if self.in_completion and self.completion_matches:
                display_items = []
                for rel_name in self.completion_matches:
                    full_path = os.path.join(self.dir_manager.current_path, self.completion_base_dir, rel_name.rstrip("/"))
                    display_items.append((rel_name, os.path.isdir(full_path)))
                display_selected = self.completion_selected
                total_display = len(display_items)
            elif self.show_file_list:
                display_items = self.dir_manager.get_filtered_items()
                display_selected = self.browser_selected
                total_display = len(display_items)
            else:
                display_items = []
                display_selected = 0
                total_display = 0

            if display_selected >= total_display:
                display_selected = max(0, total_display - 1)

            max_y, max_x = stdscr.getmaxyx()

            if need_redraw:
                stdscr.clear()

                display_path = pretty_path(self.dir_manager.current_path)
                try:
                    stdscr.addstr(0, max(0, (max_x - len(display_path)) // 2),
                                  display_path[:max_x], curses.color_pair(2))
                    stdscr.clrtoeol()
                except curses.error:
                    pass

                if self.show_file_list or self.in_completion:
                    height = max_y - 3
                    if total_display > 0:
                        for i in range(min(height, total_display)):
                            name, is_dir = display_items[i]
                            display_name = name
                            prefix = "> " if i == display_selected else "  "
                            color = curses.color_pair(1) | curses.A_BOLD if i == display_selected else curses.color_pair(2)
                            try:
                                stdscr.addstr(2 + i, 2, f"{prefix}{display_name}"[:max_x-3], color)
                                stdscr.clrtoeol()
                            except curses.error:
                                pass
                    else:
                        msg = "(no matches)" if self.in_completion else "(empty directory)"
                        try:
                            stdscr.addstr(max_y//2, max(0, (max_x - len(msg))//2), msg, curses.color_pair(2))
                        except curses.error:
                            pass

                mode_text = "[CMD]" if self.command_mode else "[TERM]"
                browser_text = " [Browser]" if self.show_file_list else ""
                comp_text = " [Completing]" if self.in_completion else ""
                yank_text = f"  CUT: {self.clipboard.yanked_original_name}{'/' if self.clipboard.yanked_is_dir else ''}" if self.clipboard.yanked_temp_path else ""

                status_line = f"{mode_text}{browser_text}{comp_text} {self.command_buffer}{yank_text}"
                try:
                    stdscr.addstr(max_y - 1, 0, status_line[:max_x-1],
                                  curses.color_pair(5) | curses.A_BOLD if self.in_completion else curses.color_pair(3))
                    stdscr.clrtoeol()
                except curses.error:
                    pass

                cursor_x = len(f"{mode_text}{browser_text}{comp_text} {self.command_buffer}")
                try:
                    stdscr.move(max_y - 1, min(cursor_x, max_x - 1))
                except curses.error:
                    pass

                stdscr.refresh()
                need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue
            need_redraw = True

            if key == 4:  # Ctrl+D
                if not self.in_completion:
                    self.show_file_list = not self.show_file_list
                    if not self.show_file_list:
                        self.command_mode = False
                continue

            if key == 23:  # Ctrl+W
                if self.show_file_list and not self.in_completion:
                    self.command_mode = not self.command_mode
                continue

            # === COMPLETION MODE ===
            if self.in_completion:
                if key in (curses.KEY_UP, ord('k')):
                    if total_display > 0:
                        self.completion_selected = (self.completion_selected - 1) % total_display

                elif key in (curses.KEY_DOWN, ord('j')):
                    if total_display > 0:
                        self.completion_selected = (self.completion_selected + 1) % total_display

                elif key in (curses.KEY_LEFT, ord('h')):
                    if self.completion_base_dir:
                        self.completion_base_dir = os.path.dirname(self.completion_base_dir.rstrip("/"))
                        if not self.completion_base_dir or self.completion_base_dir == ".":
                            self.completion_base_dir = ""
                        self._refresh_completion("")
                    continue

                elif key in (curses.KEY_RIGHT, ord('l')):
                    if total_display == 0:
                        continue
                    selected_rel = self.completion_matches[self.completion_selected]
                    full_path = os.path.join(self.dir_manager.current_path, self.completion_base_dir, selected_rel.rstrip("/"))
                    if os.path.isdir(full_path):
                        # Drill into directory
                        self.completion_base_dir = os.path.join(self.completion_base_dir, selected_rel.rstrip("/")) + "/"
                        self._refresh_completion("")
                    else:
                        # File → accept and insert pretty path
                        pretty_insert = pretty_path(full_path)
                        self.command_buffer = self.completion_prefix + pretty_insert + " "
                        self.in_completion = False
                    continue

                elif key in (10, 13):  # Enter → accept current directory
                    current_full_dir = os.path.join(self.dir_manager.current_path, self.completion_base_dir.rstrip("/"))
                    pretty_dir = pretty_path(current_full_dir) + "/"
                    self.command_buffer = self.completion_prefix + pretty_dir + " "
                    self.in_completion = False
                    continue

                elif key in (9, 27):  # Tab or Esc → cancel
                    self.in_completion = False
                    continue

                continue

            # === NORMAL BROWSER MODE ===
            if self.command_mode and self.show_file_list:
                if key == ord('t'):
                    self.open_terminal()
                elif key == 12:
                    self.clipboard.cleanup()
                elif key in (curses.KEY_UP, ord('k')):
                    if total_display > 0:
                        self.browser_selected = (self.browser_selected - 1) % total_display
                elif key in (curses.KEY_DOWN, ord('j')):
                    if total_display > 0:
                        self.browser_selected = (self.browser_selected + 1) % total_display
                elif key in (curses.KEY_LEFT, ord('h')):
                    parent = os.path.dirname(self.dir_manager.current_path)
                    if parent != self.dir_manager.current_path:
                        self.dir_manager.current_path = parent
                        self.browser_selected = 0
                elif key in (curses.KEY_RIGHT, ord('l'), 10, 13):
                    items = self.dir_manager.get_filtered_items()
                    if total_display > 0:
                        name, is_dir = items[self.browser_selected]
                        path = os.path.join(self.dir_manager.current_path, name)
                        if is_dir:
                            self.dir_manager.current_path = path
                            self.browser_selected = 0
                        elif is_text_file(path):
                            self._open_in_vim(path)
                        else:
                            curses.flash()
                elif key == 27:
                    self.clipboard.cleanup()
                    return
                continue

            # === TERMINAL MODE ===
            if key in (10, 13):
                cmd = self.command_buffer.strip()
                self.command_buffer = ""
                if cmd:
                    self.cmd_processor.run_shell_command(cmd)

            elif key == 9:  # Tab
                parts = self.command_buffer.rstrip().split()
                if parts:
                    self.completion_prefix = " ".join(parts[:-1])
                    if self.completion_prefix:
                        self.completion_prefix += " "
                    self.completion_base_dir = ""
                    partial = parts[-1]
                    self._refresh_completion(partial)

            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if self.command_buffer:
                    self.command_buffer = self.command_buffer[:-1]

            elif 32 <= key <= 126:
                self.command_buffer += chr(key)

    def _refresh_completion(self, partial=""):
        full_partial = os.path.join(self.completion_base_dir, partial)
        matches = self.dir_manager.get_tab_completions(full_partial)

        if len(matches) == 1:
            full_insert_path = os.path.join(self.dir_manager.current_path, self.completion_base_dir, matches[0].rstrip("/"))
            pretty_insert = pretty_path(full_insert_path)
            if matches[0].endswith("/"):
                pretty_insert += "/"
            self.command_buffer = self.completion_prefix + pretty_insert + " "
            self.in_completion = False
        elif len(matches) > 1:
            self.completion_matches = matches
            self.completion_selected = 0
            self.in_completion = True
        else:
            self.in_completion = False
            curses.flash()
