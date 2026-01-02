# ~/Apps/vios/modules/core_navigator.py
import curses
import subprocess
import os
import sys

from .directory_manager import DirectoryManager
from .clipboard_manager import ClipboardManager
from .ui_renderer import UIRenderer
from .input_handler import InputHandler
from .constants import Constants


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()

        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)

        self.show_help = False
        self.browser_selected = 0
        self.list_offset = 0
        self.need_redraw = True

        # Multi-mark support — now using full absolute paths
        self.marked_items = set()  # set of str (absolute paths)

        self.cheatsheet = Constants.CHEATSHEET

    def open_file(self, filepath: str):
        import mimetypes
        import zipfile

        if filepath.endswith('.zip'):
            stdscr = self.renderer.stdscr
            max_y, max_x = stdscr.getmaxyx()
            try:
                filename = os.path.basename(filepath)
                base_name = os.path.splitext(filename)[0]
                extract_dir = os.path.join(self.dir_manager.current_path, base_name)
                os.makedirs(extract_dir, exist_ok=True)

                status = f"Unzipping {filename} in progress..."
                stdscr.move(max_y - 1, 0)
                stdscr.clrtoeol()
                stdscr.addstr(max_y - 1, 0, status[:max_x-1], curses.A_BOLD)
                stdscr.refresh()

                with zipfile.ZipFile(filepath) as zf:
                    members = zf.infolist()
                    total = len(members)
                    for i, member in enumerate(members):
                        zf.extract(member, extract_dir)
                        if (i + 1) % 10 == 0 or i + 1 == total:
                            status = f"Unzipping {filename}: {i+1}/{total}"
                            stdscr.move(max_y - 1, 0)
                            stdscr.clrtoeol()
                            stdscr.addstr(max_y - 1, 0, status[:max_x-1], curses.A_BOLD)
                            stdscr.refresh()
            except Exception:
                curses.flash()
            self.need_redraw = True
            return

        mime_type, _ = mimetypes.guess_type(filepath)

        curses.endwin()

        try:
            if mime_type == 'application/pdf':
                subprocess.Popen([
                    "zathura", filepath
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid
                )
            else:
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
        current_dir = self.dir_manager.current_path
        cd_command = f"cd \"{current_dir}\""

        try:
            subprocess.run(
                ["wl-copy", cd_command],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        raise KeyboardInterrupt

    def create_new_file(self):
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
            stdscr.addstr(prompt_y, 0, prompt[:max_x-1])
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
                stdscr.addstr(prompt_y, 0, display_str[:max_x-1])
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

        unique_name = self.input_handler._get_unique_name(self.dir_manager.current_path, filename)
        filepath = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            with open(filepath, 'w'):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr.addstr(prompt_y, 0, f"Error creating file: {str(e)[:max_x-20]}", curses.A_BOLD)
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

        # Open the newly created file in Vim
        self.open_file(filepath)

    def create_new_file_no_open(self):
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
            stdscr.addstr(prompt_y, 0, prompt[:max_x-1])
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
                stdscr.addstr(prompt_y, 0, display_str[:max_x-1])
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

        unique_name = self.input_handler._get_unique_name(self.dir_manager.current_path, filename)
        filepath = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            with open(filepath, 'w'):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr.addstr(prompt_y, 0, f"Error creating file: {str(e)[:max_x-20]}", curses.A_BOLD)
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

    def create_new_directory(self):
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
            stdscr.addstr(prompt_y, 0, prompt[:max_x-1])
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
                stdscr.addstr(prompt_y, 0, display_str[:max_x-1])
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

        unique_name = self.input_handler._get_unique_name(self.dir_manager.current_path, dirname)
        dirpath = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            os.makedirs(dirpath)
        except Exception as e:
            stdscr.addstr(prompt_y, 0, f"Error creating dir: {str(e)[:max_x-20]}", curses.A_BOLD)
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

        items = self.dir_manager.get_filtered_items()
        total = len(items)
        if total == 0:
            return

        selected_name, selected_is_dir = items[self.browser_selected]
        selected_path = os.path.join(self.dir_manager.current_path, selected_name)

        prompt = "Rename: "
        prompt_y = max_y - 1

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[:max_x-1])
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
                stdscr.addstr(prompt_y, 0, display_str[:max_x-1])
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

        unique_name = self.input_handler._get_unique_name(self.dir_manager.current_path, new_name)
        new_path = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            os.rename(selected_path, new_path)
        except Exception as e:
            stdscr.addstr(prompt_y, 0, f"Error renaming: {str(e)[:max_x-20]}", curses.A_BOLD)
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

    def run(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 6):
            curses.init_pair(i, [curses.COLOR_CYAN, curses.COLOR_WHITE, curses.COLOR_YELLOW,
                                 curses.COLOR_RED, curses.COLOR_GREEN][i-1], -1)

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
