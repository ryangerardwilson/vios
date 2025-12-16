import curses
import os
import subprocess
import shutil
import tempfile
import uuid
import glob


def is_text_file(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read(1024)
        return True
    except Exception:
        return False


def pretty_path(path: str) -> str:
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):] if path != home else "~"
    return path


class FileNavigator:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.search_term = ""
        self.in_search = False
        self.temp_yank_dir = os.path.join(tempfile.gettempdir(), "harpoon_yank")
        os.makedirs(self.temp_yank_dir, exist_ok=True)
        self.yanked_temp_path = None
        self.yanked_original_name = None
        self.yanked_is_dir = False
        self.input_buffer = ""
        self.in_insert = False
        self.insert_command = ""
        self.completion_matches = []
        self.completion_index = 0

    def cleanup_yank(self):
        if self.yanked_temp_path and os.path.exists(self.yanked_temp_path):
            try:
                if os.path.isdir(self.yanked_temp_path):
                    shutil.rmtree(self.yanked_temp_path)
                else:
                    os.remove(self.yanked_temp_path)
            except Exception:
                pass
        self.yanked_temp_path = None
        self.yanked_original_name = None
        self.yanked_is_dir = False

    def get_items(self):
        try:
            items = os.listdir(self.current_path)
        except PermissionError:
            items = []

        items_with_info = []
        for item in items:
            if item.startswith("."):
                continue
            full_path = os.path.join(self.current_path, item)
            is_dir = os.path.isdir(full_path)
            items_with_info.append((item, is_dir))

        items_with_info.sort(key=lambda x: (not x[1], x[0].lower()))
        return items_with_info

    def get_filtered_items(self):
        all_items = self.get_items()
        if not self.search_term:
            return all_items
        term = self.search_term.lower()
        return [item for item in all_items if item[0].lower().startswith(term)]

    def open_in_vim(self, filepath: str):
        """Open vim in the current directory, even for new files."""
        curses.endwin()
        try:
            # Change to current_path before launching vim
            os.chdir(self.current_path)
            subprocess.call(["vim", filepath])
            # Optionally change back (not strictly needed, but clean)
            # os.chdir(os.path.dirname(os.path.realpath(__file__)))  # or original cwd
        except FileNotFoundError:
            pass
        finally:
            # Ensure we return to the correct dir for next operations
            os.chdir(self.current_path)

    def open_terminal(self):
        try:
            subprocess.Popen(
                ["alacritty", "--working-directory", self.current_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            curses.flash()

    ALLOWED_COMMANDS = {"mkdir", "mv", "cp", "rm", "vim", "v"}

    def is_command_allowed(self, cmd_line: str) -> bool:
        if not cmd_line.strip():
            return False
        parts = cmd_line.split(";")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            words = part.split()
            base_cmd = words[0] if words else ""
            if base_cmd == "v":
                base_cmd = "vim"
            if base_cmd not in self.ALLOWED_COMMANDS:
                return False
        return True

    def get_tab_completions(self, partial: str) -> list[str]:
        if not partial:
            return []
        pattern = os.path.join(self.current_path, partial + "*")
        matches = glob.glob(pattern)
        rel_matches = []
        for m in matches:
            rel = os.path.basename(m)
            if os.path.isdir(m):
                rel += "/"
            rel_matches.append(rel)
        rel_matches.sort()
        return rel_matches

    def run_shell_command(self, command: str):
        if not self.is_command_allowed(command):
            curses.flash()
            return

        if command.lstrip().startswith("v "):
            command = "vim " + " ".join(command.split()[1:])

        stripped = command.strip()

        if stripped.startswith("vim") or stripped == "v":
            parts = stripped.split()
            target = self.current_path if len(parts) == 1 else " ".join(parts[1:])
            full_path = os.path.join(self.current_path, os.path.expanduser(target))
            self.open_in_vim(full_path if os.path.exists(full_path) or target.startswith(('+', '-')) else target)
            return

        home = os.path.expanduser("~")
        bashrc = os.path.join(home, ".bashrc")
        full_cmd = f"source {bashrc} >/dev/null 2>&1 && {command} >/dev/null 2>&1"

        subprocess.Popen(
            full_cmd,
            shell=True,
            cwd=self.current_path,
            executable="/bin/bash",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

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
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_GREEN, -1)
        stdscr.bkgd(" ", curses.color_pair(2))
        stdscr.nodelay(True)

        selected = 0
        need_redraw = True

        while True:
            items = self.get_filtered_items()
            total_items = len(items)
            if selected >= total_items:
                selected = max(0, total_items - 1)

            max_y, max_x = stdscr.getmaxyx()

            if need_redraw:
                stdscr.clear()

                display_path = pretty_path(self.current_path)
                try:
                    stdscr.addstr(0, max(0, (max_x - len(display_path)) // 2),
                                  display_path[:max_x], curses.color_pair(2))
                    stdscr.clrtoeol()
                except curses.error:
                    pass

                status_line = ""
                if self.in_search:
                    status_line = f"/{self.search_term}"
                elif self.in_insert:
                    status_line = f": {self.insert_command}"
                elif self.yanked_temp_path:
                    status_line = f"CUT: {self.yanked_original_name}{'/' if self.yanked_is_dir else ''}"

                if status_line:
                    color = (curses.color_pair(3) if self.in_search else
                             curses.color_pair(5) | curses.A_BOLD if self.in_insert else
                             curses.color_pair(4) | curses.A_BOLD)
                    try:
                        stdscr.addstr(1, 2, status_line[:max_x-4], color)
                        stdscr.clrtoeol()
                    except curses.error:
                        pass
                else:
                    try:
                        stdscr.move(1, 0)
                        stdscr.clrtoeol()
                    except curses.error:
                        pass

                if total_items == 0:
                    msg = "(no matching items)" if self.search_term else \
                          "(empty directory)" if os.access(self.current_path, os.R_OK) else "(permission denied)"
                    try:
                        stdscr.addstr(max_y // 2, max(0, (max_x - len(msg)) // 2), msg, curses.color_pair(2))
                    except curses.error:
                        pass
                else:
                    start_y = 2 if not (self.in_search or self.in_insert or self.yanked_temp_path) else 3
                    for i in range(min(max_y - start_y, total_items)):
                        name, is_dir = items[i]
                        display_name = name + "/" if is_dir else name
                        prefix = "> " if i == selected else "  "
                        color = curses.color_pair(1) if i == selected else curses.color_pair(2)
                        text = f"{prefix}{display_name}"
                        try:
                            stdscr.addstr(start_y + i, 2, text[:max_x - 3], color)
                            stdscr.clrtoeol()
                        except curses.error:
                            pass

                if self.in_insert:
                    cmd_display = f": {self.insert_command}"
                    cursor_x = 2 + len(cmd_display)
                    try:
                        stdscr.move(1, min(cursor_x, max_x - 1))
                    except curses.error:
                        pass

                stdscr.refresh()
                need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue
            need_redraw = True

            if self.in_insert:
                if key == 27:  # ESC
                    self.in_insert = False
                    self.insert_command = ""
                    self.completion_matches = []
                    self.completion_index = 0
                    curses.curs_set(0)
                elif key in (10, 13):  # Enter
                    cmd = self.insert_command.strip()
                    self.in_insert = False
                    self.insert_command = ""
                    self.completion_matches = []
                    self.completion_index = 0
                    curses.curs_set(0)
                    if cmd:
                        self.run_shell_command(cmd)
                elif key == 9:  # Tab
                    parts = self.insert_command.rstrip().split()
                    if parts:
                        partial = parts[-1]
                        matches = self.get_tab_completions(partial)
                        if matches:
                            if len(matches) == 1:
                                replacement = matches[0]
                                parts[-1] = replacement
                                self.insert_command = " ".join(parts) + " "
                            else:
                                if self.completion_matches != matches:
                                    self.completion_matches = matches
                                    self.completion_index = 0
                                else:
                                    self.completion_index = (self.completion_index + 1) % len(matches)
                                replacement = self.completion_matches[self.completion_index]
                                parts[-1] = replacement
                                self.insert_command = " ".join(parts) + " "
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    self.insert_command = self.insert_command[:-1]
                    self.completion_matches = []
                    self.completion_index = 0
                elif 32 <= key <= 126:
                    self.insert_command += chr(key)
                    self.completion_matches = []
                    self.completion_index = 0

            elif self.in_search:
                if key in (27, ord("/")):
                    self.in_search = False
                    self.search_term = ""
                    selected = 0
                elif key in (10, 13):
                    if total_items > 0:
                        self.in_search = False
                        self.search_term = ""
                        selected_name, is_dir = items[selected]
                        selected_path = os.path.join(self.current_path, selected_name)
                        if is_dir:
                            self.current_path = selected_path
                            selected = 0
                        elif is_text_file(selected_path):
                            self.open_in_vim(selected_path)
                        else:
                            curses.flash()
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    self.search_term = self.search_term[:-1]
                    selected = 0
                elif 32 <= key <= 126:
                    self.search_term += chr(key)
                    selected = 0

            else:
                if key == ord('i'):
                    self.in_insert = True
                    self.insert_command = ""
                    self.completion_matches = []
                    self.completion_index = 0
                    curses.curs_set(1)

                elif key == ord('t'):
                    self.open_terminal()

                elif key == ord('y') and self.input_buffer == "y":
                    if total_items > 0:
                        self.cleanup_yank()
                        name, is_dir = items[selected]
                        src = os.path.join(self.current_path, name)
                        unique_id = str(uuid.uuid4())[:8]
                        temp_dest = os.path.join(self.temp_yank_dir, f"yank_{unique_id}_{name}")
                        try:
                            if is_dir:
                                shutil.copytree(src, temp_dest)
                            else:
                                shutil.copy2(src, temp_dest)
                            self.yanked_temp_path = temp_dest
                            self.yanked_original_name = name
                            self.yanked_is_dir = is_dir
                        except Exception:
                            curses.flash()
                    self.input_buffer = ""

                elif key == ord('d') and self.input_buffer == "d":
                    if total_items > 0:
                        self.cleanup_yank()
                        name, is_dir = items[selected]
                        src = os.path.join(self.current_path, name)
                        unique_id = str(uuid.uuid4())[:8]
                        temp_dest = os.path.join(self.temp_yank_dir, f"cut_{unique_id}_{name}")
                        try:
                            if is_dir:
                                shutil.copytree(src, temp_dest)
                            else:
                                shutil.copy2(src, temp_dest)
                            self.yanked_temp_path = temp_dest
                            self.yanked_original_name = name
                            self.yanked_is_dir = is_dir

                            if is_dir:
                                shutil.rmtree(src)
                            else:
                                os.remove(src)
                        except Exception:
                            curses.flash()
                            self.cleanup_yank()
                    self.input_buffer = ""

                elif key in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
                    if total_items > 0:
                        name, _ = items[selected]
                        full_path = os.path.join(self.current_path, name)
                        try:
                            if os.path.isdir(full_path):
                                shutil.rmtree(full_path)
                            else:
                                os.remove(full_path)
                        except Exception:
                            curses.flash()

                elif key == ord('p'):
                    if self.yanked_temp_path and os.path.exists(self.yanked_temp_path):
                        dest_name = self.yanked_original_name
                        dest_path = os.path.join(self.current_path, dest_name)
                        if os.path.exists(dest_path):
                            new_name = self.prompt_new_name(stdscr, dest_name)
                            if not new_name:
                                continue
                            dest_path = os.path.join(self.current_path, new_name)

                        try:
                            if self.yanked_is_dir:
                                shutil.copytree(self.yanked_temp_path, dest_path)
                            else:
                                shutil.copy2(self.yanked_temp_path, dest_path)
                        except Exception:
                            curses.flash()
                    else:
                        curses.flash()

                elif key == ord('d'):
                    self.input_buffer = "d"
                elif key == ord('y'):
                    self.input_buffer = "y"
                elif key == ord("/"):
                    self.in_search = True
                    self.search_term = ""
                    selected = 0
                    self.input_buffer = ""
                elif key in (curses.KEY_UP, ord("k")) and selected > 0:
                    selected -= 1
                elif key in (curses.KEY_DOWN, ord("j")) and selected < total_items - 1:
                    selected += 1
                elif key in (curses.KEY_LEFT, ord("h")):
                    parent = os.path.dirname(self.current_path)
                    if parent != self.current_path:
                        self.current_path = parent
                        selected = 0
                    else:
                        curses.flash()
                elif key in (curses.KEY_RIGHT, ord("l"), 10, 13):
                    if total_items == 0:
                        continue
                    selected_name, is_dir = items[selected]
                    selected_path = os.path.join(self.current_path, selected_name)
                    if is_dir:
                        self.current_path = selected_path
                        selected = 0
                    elif is_text_file(selected_path):
                        self.open_in_vim(selected_path)
                    else:
                        curses.flash()
                elif key == 27:
                    self.cleanup_yank()
                    return
                else:
                    self.input_buffer = ""
