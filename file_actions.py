import curses
import mimetypes
import os
import shlex
import shutil
import subprocess
import zipfile
from typing import Optional, cast, Any, List


class FileActionService:
    def __init__(self, navigator):
        self.nav = navigator

    # === Helpers ===
    def _resolve_base_directory(self, base_path: Optional[str]) -> str:
        if base_path:
            candidate = os.path.realpath(base_path)
            if os.path.isdir(candidate):
                return candidate
        return self.nav.dir_manager.current_path

    def _prompt_for_input(self, prompt: str) -> Optional[str]:
        stdscr_opt = self.nav.renderer.stdscr
        if stdscr_opt is None:
            return None
        stdscr = cast(Any, stdscr_opt)

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.nav.need_redraw = True
            return None

        prompt_y = max_y - 1
        input_str = ""

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[: max_x - 1])
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)
            input_x = len(prompt)
            max_input_width = max(10, max_x - input_x - 1)

            stdscr.move(prompt_y, 0)
            stdscr.clrtoeol()
            stdscr.addstr(prompt_y, 0, prompt)
            stdscr.refresh()

            while True:
                key = stdscr.getch()

                if key in (10, 13, curses.KEY_ENTER):
                    break
                if key == 27:
                    input_str = ""
                    break
                if key in (curses.KEY_BACKSPACE, 127, 8):
                    if input_str:
                        input_str = input_str[:-1]
                elif 32 <= key <= 126 and len(input_str) < max_input_width:
                    input_str += chr(key)

                stdscr.move(prompt_y, 0)
                stdscr.clrtoeol()
                display_str = prompt + input_str
                stdscr.addstr(prompt_y, 0, display_str[: max_x - 1])
                stdscr.refresh()
        except KeyboardInterrupt:
            input_str = ""
        except Exception:
            input_str = ""
        finally:
            stdscr.timeout(40)
            self.nav.need_redraw = True

        result = input_str.strip()
        return result or None

    # === File operations ===
    def open_file(self, filepath: str):
        if filepath.endswith(".zip"):
            stdscr_opt = self.nav.renderer.stdscr
            if stdscr_opt is None:
                curses.flash()
                self.nav.need_redraw = True
                return
            stdscr = cast(Any, stdscr_opt)
            max_y, max_x = stdscr.getmaxyx()
            try:
                filename = os.path.basename(filepath)
                base_name = os.path.splitext(filename)[0]
                extract_dir = os.path.join(self.nav.dir_manager.current_path, base_name)
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
                            stdscr.addstr(max_y - 1, 0, status[: max_x - 1], curses.A_BOLD)
                            stdscr.refresh()
            except Exception:
                curses.flash()
            self.nav.need_redraw = True
            return

        mime_type, _ = mimetypes.guess_type(filepath)
        _, ext = os.path.splitext(filepath)

        suspended = False

        def ensure_suspended():
            nonlocal suspended
            if not suspended:
                curses.endwin()
                suspended = True

        handled = False
        try:
            if ext in (".csv", ".parquet"):
                ensure_suspended()
                subprocess.call(["vixl", filepath])
                handled = True
            elif mime_type == "application/pdf":
                handled = self._run_external_handlers(
                    self.nav.config.get_handler_commands("pdf_viewer"), filepath, background=True, suspend=ensure_suspended
                )
            elif mime_type and mime_type.startswith("image/"):
                handled = self._run_external_handlers(
                    self.nav.config.get_handler_commands("image_viewer"), filepath, background=True, suspend=ensure_suspended
                )
            else:
                handled = self._run_external_handlers(
                    self.nav.config.get_handler_commands("editor"), filepath, background=False, suspend=ensure_suspended
                )
        except FileNotFoundError:
            pass
        finally:
            if not handled:
                self.nav.status_message = "No handler configured"
                curses.flash()
            self.nav.need_redraw = True

    def _run_external_handlers(
        self,
        handlers: List[List[str]],
        filepath: str,
        *,
        background: bool,
        suspend,
    ) -> bool:
        if not handlers:
            return False

        for raw_cmd in handlers:
            if not raw_cmd:
                continue
            tokens = []
            for part in raw_cmd:
                if not isinstance(part, str):
                    continue
                tokens.append(part.replace("{file}", filepath))
            if not tokens:
                continue
            if "{file}" not in ''.join(raw_cmd):
                tokens = tokens + [filepath]

            cmd_name = tokens[0]
            if shutil.which(cmd_name) is None:
                continue

            try:
                if background:
                    suspend()
                    subprocess.Popen(
                        tokens,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        preexec_fn=os.setsid,
                    )
                else:
                    suspend()
                    subprocess.call(tokens)
                return True
            except FileNotFoundError:
                continue
            except Exception:
                continue

        return False

    def create_new_file(self):
        filename = self._prompt_for_input("New file: ")
        if not filename:
            return

        base_dir = self.nav.dir_manager.current_path
        unique_name = self.nav.input_handler._get_unique_name(base_dir, filename)
        filepath = os.path.join(base_dir, unique_name)

        try:
            with open(filepath, "w"):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr = cast(Any, self.nav.renderer.stdscr)
            if stdscr:
                max_y, max_x = stdscr.getmaxyx()
                prompt_y = max_y - 1
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

        self.nav.notify_directory_changed(base_dir)
        self.open_file(filepath)

    def create_new_file_no_open(self, base_path: Optional[str] = None):
        filename = self._prompt_for_input("New file: ")
        if not filename:
            return

        base_dir = self._resolve_base_directory(base_path)
        unique_name = self.nav.input_handler._get_unique_name(base_dir, filename)
        filepath = os.path.join(base_dir, unique_name)

        try:
            with open(filepath, "w"):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr = cast(Any, self.nav.renderer.stdscr)
            if stdscr:
                max_y, max_x = stdscr.getmaxyx()
                prompt_y = max_y - 1
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

        self.nav.notify_directory_changed(base_dir)
        self.nav.status_message = f"Created file: {unique_name}"

    def create_new_directory(self, base_path: Optional[str] = None):
        dirname = self._prompt_for_input("New dir: ")
        if not dirname:
            return

        base_dir = self._resolve_base_directory(base_path)
        unique_name = self.nav.input_handler._get_unique_name(base_dir, dirname)
        dirpath = os.path.join(base_dir, unique_name)

        try:
            os.makedirs(dirpath)
        except Exception as e:
            stdscr = cast(Any, self.nav.renderer.stdscr)
            if stdscr:
                max_y, max_x = stdscr.getmaxyx()
                prompt_y = max_y - 1
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

        self.nav.notify_directory_changed(base_dir)
        self.nav.status_message = f"Created directory: {unique_name}"

    def rename_selected(self):
        stdscr_opt = self.nav.renderer.stdscr
        if stdscr_opt is None:
            return
        stdscr = cast(Any, stdscr_opt)

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.nav.need_redraw = True
            return

        items = self.nav.build_display_items()
        total = len(items)
        if total == 0:
            return

        selected_name, selected_is_dir, selected_path, _ = items[
            self.nav.browser_selected
        ]
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
            stdscr.timeout(-1)
            max_input_width = max(10, max_x - len(prompt) - 1)
            input_str = selected_name

            while True:
                stdscr.move(prompt_y, 0)
                stdscr.clrtoeol()
                display_str = prompt + input_str
                stdscr.addstr(prompt_y, 0, display_str[: max_x - 1])
                stdscr.refresh()

                key = stdscr.getch()
                if key in (10, 13, curses.KEY_ENTER):
                    break
                if key == 27:
                    input_str = ""
                    break
                if key in (curses.KEY_BACKSPACE, 127, 8):
                    if input_str:
                        input_str = input_str[:-1]
                elif 32 <= key <= 126 and len(input_str) < max_input_width:
                    input_str += chr(key)
        except KeyboardInterrupt:
            input_str = ""
        except Exception:
            input_str = ""
        finally:
            stdscr.timeout(40)
            self.nav.need_redraw = True

        new_name = input_str.strip()
        if not new_name or new_name == selected_name:
            return

        unique_name = self.nav.input_handler._get_unique_name(parent_dir, new_name)
        new_path = os.path.join(parent_dir, unique_name)

        try:
            os.rename(selected_path, new_path)
        except Exception as e:
            stdscr.addstr(
                prompt_y,
                0,
                f"Error renaming: {str(e)[: max_x - 20]}",
                curses.A_BOLD,
            )
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

        self.nav.notify_directory_changed(parent_dir)
        self.nav.status_message = f"Renamed to {unique_name}" if unique_name != selected_name else "Renamed"

    def open_terminal(self):
        cwd = self.nav.dir_manager.current_path
        commands = []
        term_env = os.environ.get("TERMINAL")
        if term_env:
            commands.append(shlex.split(term_env))
        commands.extend(
            [[cmd] for cmd in ("alacritty", "foot", "kitty", "wezterm", "gnome-terminal", "xterm")]
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
                self.nav.status_message = f"Opened terminal: {cmd[0]}"
                return
            except Exception:
                continue

        self.nav.status_message = "No terminal found"
        curses.flash()
