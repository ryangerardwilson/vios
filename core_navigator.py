# ~/Apps/vios/core_navigator.py
import curses
import subprocess
import os
import shutil
import shlex
from typing import Any, Set, cast, List, Optional

from directory_manager import DirectoryManager
from clipboard_manager import ClipboardManager
from ui_renderer import UIRenderer
from input_handler import InputHandler
from constants import Constants


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()

        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)

        self.show_help = False
        self.help_scroll = 0
        self.browser_selected = 0
        self.list_offset = 0
        self.need_redraw = True

        # Multi-mark support — now using full absolute paths
        self.marked_items = set()  # set of str (absolute paths)
        self.expanded_nodes: Set[str] = set()

        self.cheatsheet = Constants.CHEATSHEET
        self.status_message = ""
        self.leader_sequence = ""
        start_real = os.path.realpath(start_path)
        self.history: List[str] = [start_real]
        self.history_index = 0

        self.bookmarks: List[str] = []
        self.bookmark_index = -1

    def open_file(self, filepath: str):
        import mimetypes
        import zipfile

        if filepath.endswith(".zip"):
            stdscr_opt = self.renderer.stdscr
            if stdscr_opt is None:
                curses.flash()
                self.need_redraw = True
                return
            stdscr = cast(Any, stdscr_opt)
            max_y, max_x = stdscr.getmaxyx()
            try:
                filename = os.path.basename(filepath)
                base_name = os.path.splitext(filename)[0]
                extract_dir = os.path.join(self.dir_manager.current_path, base_name)
                os.makedirs(extract_dir, exist_ok=True)

                status = f"Unzipping {filename} in progress..."
                stdscr.move(max_y - 1, 0)
                stdscr.clrtoeol()
                stdscr.addstr(max_y - 1, 0, status[: max_x - 1], curses.A_BOLD)
                stdscr.refresh()

                with zipfile.ZipFile(filepath) as zf:
                    members = zf.infolist()
                    total = len(members)
                    for i, member in enumerate(members):
                        zf.extract(member, extract_dir)
                        if (i + 1) % 10 == 0 or i + 1 == total:
                            status = f"Unzipping {filename}: {i + 1}/{total}"
                            stdscr.move(max_y - 1, 0)
                            stdscr.clrtoeol()
                            stdscr.addstr(
                                max_y - 1, 0, status[: max_x - 1], curses.A_BOLD
                            )
                            stdscr.refresh()
            except Exception:
                curses.flash()
            self.need_redraw = True
            return

        mime_type, _ = mimetypes.guess_type(filepath)
        _, ext = os.path.splitext(filepath)

        curses.endwin()

        try:
            if ext in (".csv", ".parquet"):
                subprocess.call(["vixl", filepath])
            elif mime_type == "application/pdf":
                subprocess.Popen(
                    ["zathura", filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid,
                )
            elif mime_type and mime_type.startswith("image/"):
                subprocess.Popen(
                    ["swayimg", filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid,
                )
            else:
                subprocess.call(
                    ["vim", "-c", f"cd {self.dir_manager.current_path}", filepath]
                )
        except FileNotFoundError:
            pass
        finally:
            self.need_redraw = True

    def copy_current_path(self):
        current_dir = self.dir_manager.current_path
        text_to_copy = f'cd "{current_dir}"'

        try:
            p = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            stdin_pipe = p.stdin
            if stdin_pipe:
                stdin_pipe.write(text_to_copy.encode())
                stdin_pipe.close()
            p.wait()  # Wait for the parent process to exit (quick, mimics subprocess.run behavior)
            self.status_message = "cd command copied to clipboard!"
        except Exception:
            self.status_message = "Failed to copy cd command"
            pass

    def create_new_file(self):
        stdscr_opt = self.renderer.stdscr
        if stdscr_opt is None:
            return
        stdscr = cast(Any, stdscr_opt)

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.need_redraw = True
            return

        prompt = "New file: "
        prompt_y = max_y - 1
        filename = ""

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[: max_x - 1])
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)  # Block indefinitely for user input
            # No curs_set(1) - keep cursor hidden, like filter mode

            input_x = len(prompt)
            max_input_width = max_x - input_x - 1
            if max_input_width < 10:
                max_input_width = 10

            input_str = ""

            # Initial draw
            stdscr.move(prompt_y, 0)
            stdscr.clrtoeol()
            stdscr.addstr(prompt_y, 0, prompt + input_str)
            stdscr.refresh()

            while True:
                key = stdscr.getch()

                if key in (10, 13, curses.KEY_ENTER):  # Enter to confirm
                    break
                elif key == 27:  # Esc to cancel
                    input_str = ""
                    break
                elif key in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                elif 32 <= key <= 126:  # Printable ASCII characters only
                    if len(input_str) < max_input_width:
                        char = chr(key)
                        input_str += char

                # Redraw the entire prompt line
                stdscr.move(prompt_y, 0)
                stdscr.clrtoeol()
                display_str = prompt + input_str
                stdscr.addstr(prompt_y, 0, display_str[: max_x - 1])
                stdscr.refresh()

            filename = input_str.strip()
        except KeyboardInterrupt:
            filename = ""
        except Exception:
            filename = ""
        finally:
            stdscr.timeout(40)  # Restore run()'s timeout
            self.need_redraw = True

        if not filename:
            return

        unique_name = self.input_handler._get_unique_name(
            self.dir_manager.current_path, filename
        )
        filepath = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            with open(filepath, "w"):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr.addstr(
                prompt_y,
                0,
                f"Error creating file: {str(e)[: max_x - 20]}",
                curses.A_BOLD,
            )
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

        # Open the newly created file in Vim
        self.open_file(filepath)

    def open_terminal(self):
        cwd = self.dir_manager.current_path
        commands: List[list[str]] = []
        term_env = os.environ.get("TERMINAL")
        if term_env:
            commands.append(shlex.split(term_env))
        commands.extend(
            [
                [cmd]
                for cmd in (
                    "alacritty",
                    "foot",
                    "kitty",
                    "wezterm",
                    "gnome-terminal",
                    "xterm",
                )
            ]
        )

        for cmd in commands:
            if not cmd:
                continue
            if shutil.which(cmd[0]) is None:
                continue
            try:
                subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid,
                )
                self.status_message = f"Opened terminal: {cmd[0]}"
                return
            except Exception:
                continue

        self.status_message = "No terminal found"
        curses.flash()

    def _resolve_base_directory(self, base_path: Optional[str]) -> str:
        if base_path:
            candidate = os.path.realpath(base_path)
            if os.path.isdir(candidate):
                return candidate
        return self.dir_manager.current_path

    def create_new_file_no_open(self, base_path: Optional[str] = None):
        stdscr = self.renderer.stdscr
        if not stdscr:
            return

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.need_redraw = True
            return

        prompt = "New file: "
        prompt_y = max_y - 1

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[: max_x - 1])
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)  # Block indefinitely for user input
            # No curs_set(1) - keep cursor hidden, like filter mode

            input_x = len(prompt)
            max_input_width = max_x - input_x - 1
            if max_input_width < 10:
                max_input_width = 10

            input_str = ""

            # Initial draw
            stdscr.move(prompt_y, 0)
            stdscr.clrtoeol()
            stdscr.addstr(prompt_y, 0, prompt + input_str)
            stdscr.refresh()

            while True:
                key = stdscr.getch()

                if key in (10, 13, curses.KEY_ENTER):  # Enter to confirm
                    break
                elif key == 27:  # Esc to cancel
                    input_str = ""
                    break
                elif key in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                elif 32 <= key <= 126:  # Printable ASCII characters only
                    if len(input_str) < max_input_width:
                        char = chr(key)
                        input_str += char

                # Redraw the entire prompt line
                stdscr.move(prompt_y, 0)
                stdscr.clrtoeol()
                display_str = prompt + input_str
                stdscr.addstr(prompt_y, 0, display_str[: max_x - 1])
                stdscr.refresh()

            filename = input_str.strip()
        except KeyboardInterrupt:
            filename = ""
        except Exception:
            filename = ""
        finally:
            stdscr.timeout(40)  # Restore run()'s timeout
            self.need_redraw = True

        if not filename:
            return

        base_dir = self._resolve_base_directory(base_path)
        unique_name = self.input_handler._get_unique_name(base_dir, filename)
        filepath = os.path.join(base_dir, unique_name)

        try:
            with open(filepath, "w"):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr.addstr(
                prompt_y,
                0,
                f"Error creating file: {str(e)[: max_x - 20]}",
                curses.A_BOLD,
            )
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

    def create_new_directory(self, base_path: Optional[str] = None):
        stdscr = self.renderer.stdscr
        if not stdscr:
            return

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.need_redraw = True
            return

        prompt = "New dir: "
        prompt_y = max_y - 1

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[: max_x - 1])
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)  # Block indefinitely for user input
            # No curs_set(1) - keep cursor hidden, like filter mode

            input_x = len(prompt)
            max_input_width = max_x - input_x - 1
            if max_input_width < 10:
                max_input_width = 10

            input_str = ""

            # Initial draw
            stdscr.move(prompt_y, 0)
            stdscr.clrtoeol()
            stdscr.addstr(prompt_y, 0, prompt + input_str)
            stdscr.refresh()

            while True:
                key = stdscr.getch()

                if key in (10, 13, curses.KEY_ENTER):  # Enter to confirm
                    break
                elif key == 27:  # Esc to cancel
                    input_str = ""
                    break
                elif key in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                elif 32 <= key <= 126:  # Printable ASCII characters only
                    if len(input_str) < max_input_width:
                        char = chr(key)
                        input_str += char

                # Redraw the entire prompt line
                stdscr.move(prompt_y, 0)
                stdscr.clrtoeol()
                display_str = prompt + input_str
                stdscr.addstr(prompt_y, 0, display_str[: max_x - 1])
                stdscr.refresh()

            dirname = input_str.strip()
        except KeyboardInterrupt:
            dirname = ""
        except Exception:
            dirname = ""
        finally:
            stdscr.timeout(40)  # Restore run()'s timeout
            self.need_redraw = True

        if not dirname:
            return

        base_dir = self._resolve_base_directory(base_path)
        unique_name = self.input_handler._get_unique_name(base_dir, dirname)
        dirpath = os.path.join(base_dir, unique_name)

        try:
            os.makedirs(dirpath)
        except Exception as e:
            stdscr.addstr(
                prompt_y,
                0,
                f"Error creating dir: {str(e)[: max_x - 20]}",
                curses.A_BOLD,
            )
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

    def rename_selected(self):
        stdscr = self.renderer.stdscr
        if not stdscr:
            return

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.need_redraw = True
            return

        items = self.build_display_items()
        total = len(items)
        if total == 0:
            return

        selected_name, selected_is_dir, selected_path, _ = items[self.browser_selected]
        parent_dir = os.path.dirname(selected_path)

        prompt = "Rename: "
        prompt_y = max_y - 1

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[: max_x - 1])
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)  # Block indefinitely for user input
            # No curs_set(1) - keep cursor hidden, like filter mode

            input_x = len(prompt)
            max_input_width = max_x - input_x - 1
            if max_input_width < 10:
                max_input_width = 10

            input_str = selected_name

            # Initial draw
            stdscr.move(prompt_y, 0)
            stdscr.clrtoeol()
            stdscr.addstr(prompt_y, 0, prompt + input_str)
            stdscr.refresh()

            while True:
                key = stdscr.getch()

                if key in (10, 13, curses.KEY_ENTER):  # Enter to confirm
                    break
                elif key == 27:  # Esc to cancel
                    input_str = ""
                    break
                elif key in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                elif 32 <= key <= 126:  # Printable ASCII characters only
                    if len(input_str) < max_input_width:
                        char = chr(key)
                        input_str += char

                # Redraw the entire prompt line
                stdscr.move(prompt_y, 0)
                stdscr.clrtoeol()
                display_str = prompt + input_str
                stdscr.addstr(prompt_y, 0, display_str[: max_x - 1])
                stdscr.refresh()

            new_name = input_str.strip()
        except KeyboardInterrupt:
            new_name = ""
        except Exception:
            new_name = ""
        finally:
            stdscr.timeout(40)  # Restore run()'s timeout
            self.need_redraw = True

        if not new_name or new_name == selected_name:
            return

        unique_name = self.input_handler._get_unique_name(parent_dir, new_name)
        new_path = os.path.join(parent_dir, unique_name)

        try:
            os.rename(selected_path, new_path)
        except Exception as e:
            stdscr.addstr(
                prompt_y, 0, f"Error renaming: {str(e)[: max_x - 20]}", curses.A_BOLD
            )
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

    def run(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 6):
            curses.init_pair(
                i,
                [
                    curses.COLOR_CYAN,
                    curses.COLOR_WHITE,
                    curses.COLOR_YELLOW,
                    curses.COLOR_RED,
                    curses.COLOR_GREEN,
                ][i - 1],
                -1,
            )

        self.renderer.stdscr = stdscr

        try:
            stdscr.keypad(True)
            stdscr.leaveok(True)
            stdscr.idlok(True)
        except Exception:
            pass

        stdscr.timeout(40)

        while True:
            if self.need_redraw:
                self.renderer.render()
                self.need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue

            if self.input_handler.handle_key(stdscr, key):
                break

            self.need_redraw = True

    def build_display_items(self):
        base_items = self.dir_manager.get_filtered_items()
        display = []

        for name, is_dir in base_items:
            path = os.path.join(self.dir_manager.current_path, name)
            display.append((name, is_dir, path, 0))
            if is_dir and path in self.expanded_nodes:
                self._append_expanded(path, 1, display)

        return display

    def _append_expanded(self, base_path: str, depth: int, collection: list):
        children = self.dir_manager.list_directory(base_path)
        if (
            not children
            and base_path in self.expanded_nodes
            and not os.path.exists(base_path)
        ):
            self.expanded_nodes.discard(base_path)
            return

        for child_name, child_is_dir in children:
            child_path = os.path.join(base_path, child_name)
            collection.append((child_name, child_is_dir, child_path, depth))
            if child_is_dir and child_path in self.expanded_nodes:
                self._append_expanded(child_path, depth + 1, collection)

    def collapse_branch(self, base_path: str):
        if base_path not in self.expanded_nodes and not any(
            p.startswith(f"{base_path}{os.sep}") for p in self.expanded_nodes
        ):
            return
        to_remove = [
            p
            for p in self.expanded_nodes
            if p == base_path or p.startswith(f"{base_path}{os.sep}")
        ]
        for entry in to_remove:
            self.expanded_nodes.discard(entry)

    def collapse_expansions_under(self, base_path: str):
        real_base = os.path.realpath(base_path)
        if not real_base:
            return
        prefix = f"{real_base}{os.sep}"
        to_remove = [
            p for p in self.expanded_nodes if p == real_base or p.startswith(prefix)
        ]
        if not to_remove:
            return
        for entry in to_remove:
            self.expanded_nodes.discard(entry)
        self.need_redraw = True

    def add_bookmark(self, path: Optional[str] = None) -> bool:
        target = path or self.dir_manager.current_path
        if not target:
            return False
        real_target = os.path.realpath(target)
        if not os.path.isdir(real_target):
            return False

        if real_target in self.bookmarks:
            idx = self.bookmarks.index(real_target)
            self.bookmarks.pop(idx)
            if self.bookmarks:
                if idx < len(self.bookmarks):
                    self.bookmark_index = idx
                else:
                    self.bookmark_index = len(self.bookmarks) - 1
            else:
                self.bookmark_index = -1
            pretty = DirectoryManager.pretty_path(real_target)
            self.status_message = f"Unbookmarked {pretty}"
        else:
            self.bookmarks.append(real_target)
            self.bookmark_index = len(self.bookmarks) - 1
            pretty = DirectoryManager.pretty_path(real_target)
            self.status_message = f"Bookmarked {pretty}"

        self.need_redraw = True
        return True

    def change_directory(self, new_path: str, *, record_history: bool = True):
        new_real = os.path.realpath(new_path)
        if not os.path.isdir(new_real):
            return False

        if record_history:
            if self.history_index < len(self.history) - 1:
                self.history = self.history[: self.history_index + 1]
            if not self.history or self.history[-1] != new_real:
                self.history.append(new_real)
                self.history_index = len(self.history) - 1
            else:
                self.history_index = len(self.history) - 1
        self._set_current_path(new_real)
        return True

    def go_history_back(self):
        if not self.bookmarks or self.bookmark_index <= 0:
            self.status_message = "No previous bookmark"
            return False
        self.bookmark_index -= 1
        self._set_current_path(self.bookmarks[self.bookmark_index])
        self.status_message = "Bookmark back"
        return True

    def go_history_forward(self):
        if not self.bookmarks or self.bookmark_index >= len(self.bookmarks) - 1:
            self.status_message = "No next bookmark"
            return False
        self.bookmark_index += 1
        self._set_current_path(self.bookmarks[self.bookmark_index])
        self.status_message = "Bookmark forward"
        return True

    def _set_current_path(self, new_path: str):
        self.dir_manager.current_path = new_path
        self.browser_selected = 0
        self.list_offset = 0
        self.need_redraw = True
        real_path = os.path.realpath(new_path)
        if real_path in self.bookmarks:
            self.bookmark_index = self.bookmarks.index(real_path)
        elif not self.bookmarks:
            self.bookmark_index = -1

    def reset_to_home(self):
        home = self.dir_manager.home_path
        self.expanded_nodes.clear()
        self.dir_manager.filter_pattern = ""
        self.change_directory(home)
