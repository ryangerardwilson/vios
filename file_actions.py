import curses
import mimetypes
import os
import selectors
import shlex
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from typing import Optional, cast, Any, List, Tuple

try:
    import termios
except ImportError:  # pragma: no cover
    termios = None  # type: ignore[assignment]

from config import HandlerSpec


MEDIA_AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".alac",
    ".flac",
    ".m4a",
    ".mka",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}

MEDIA_VIDEO_EXTENSIONS = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
}

TEXT_LIKE_EXTENSIONS = {
    ".py",
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".sh",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}


def is_text_like_file(filepath: str, mime_type: Optional[str] = None) -> bool:
    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(filepath)
    _, ext = os.path.splitext(filepath)
    ext_lower = ext.lower()
    return bool(
        (mime_type and mime_type.startswith("text/"))
        or ext_lower in TEXT_LIKE_EXTENSIONS
    )


def flush_terminal_input() -> None:
    try:
        curses.flushinp()
    except curses.error:
        pass
    except Exception:
        pass

    if termios is None:
        return

    try:
        stdin = sys.stdin
        if stdin is None or not stdin.isatty():
            return
        termios.tcflush(stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        pass


class ExecutionJob:
    def __init__(self, filepath: str, command: List[str], display: str, mode: str):
        self.filepath = filepath
        self.command = command
        self.display = display
        self.mode = mode
        self.process: Optional[subprocess.Popen[str]] = None
        self.thread: Optional[threading.Thread] = None
        self.cancelled = False
        self.exit_code: Optional[int] = None
        self.started_at = time.time()
        self.done_event = threading.Event()

    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def mark_process(self, process: subprocess.Popen[str]) -> None:
        self.process = process

    def mark_finished(self, exit_code: Optional[int]) -> None:
        self.exit_code = exit_code
        self.done_event.set()

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        self.done_event.wait(timeout)
        return self.exit_code

    def terminate(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is not None:
            return
        self.cancelled = True
        try:
            self.process.terminate()
        except Exception:
            pass
        try:
            self.process.wait(timeout=2)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass


class FileActionService:
    def __init__(self, navigator):
        self.nav = navigator

    # === Helpers ===
    @staticmethod
    def _flash() -> None:
        try:
            curses.flash()
        except curses.error:
            pass
        except Exception:
            pass

    def _resolve_base_directory(self, base_path: Optional[str]) -> str:
        if base_path:
            candidate = os.path.realpath(base_path)
            if os.path.isdir(candidate):
                return candidate
        return self.nav.dir_manager.current_path

    def _select_media_handler_spec(self, kind: str) -> HandlerSpec:
        if kind not in {"audio", "video"}:
            return HandlerSpec(commands=[], is_internal=False)

        primary_name = f"{kind}_player"
        primary = self.nav.config.get_handler_spec(primary_name)
        if primary.commands:
            return primary

        # Backward compatibility for older configs.
        return self.nav.config.get_handler_spec("media_player")

    @staticmethod
    def _is_word_char(ch: str) -> bool:
        return ch.isalnum() or ch == "_"

    def _move_word_left(self, text: str, cursor: int) -> int:
        i = max(0, min(cursor, len(text)))
        while i > 0 and not self._is_word_char(text[i - 1]):
            i -= 1
        while i > 0 and self._is_word_char(text[i - 1]):
            i -= 1
        return i

    def _move_word_right(self, text: str, cursor: int) -> int:
        n = len(text)
        i = max(0, min(cursor, n))
        while i < n and not self._is_word_char(text[i]):
            i += 1
        while i < n and self._is_word_char(text[i]):
            i += 1
        return i

    def _delete_prev_word(self, text: str, cursor: int) -> Tuple[str, int]:
        if cursor <= 0:
            return text, cursor
        start = self._move_word_left(text, cursor)
        return text[:start] + text[cursor:], start

    def _read_key_with_meta(self, stdscr: Any) -> Tuple[int, Optional[int]]:
        key = stdscr.getch()
        if key != 27:
            return key, None

        # Distinguish bare ESC (cancel) from Alt/Meta key sequences.
        stdscr.timeout(25)
        next_key = stdscr.getch()
        stdscr.timeout(-1)
        if next_key == -1:
            return 27, None
        return 27, next_key

    def _render_prompt_input(
        self,
        stdscr: Any,
        prompt_y: int,
        max_x: int,
        prompt_display: str,
        text: str,
        cursor: int,
    ) -> None:
        available = max(1, max_x - len(prompt_display) - 1)
        max_start = max(0, len(text) - available)
        viewport_start = max(0, cursor - available + 1)
        if cursor < viewport_start:
            viewport_start = cursor
        if viewport_start > max_start:
            viewport_start = max_start
        visible = text[viewport_start : viewport_start + available]
        cursor_screen_x = min(max_x - 1, len(prompt_display) + (cursor - viewport_start))

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()
        stdscr.addstr(prompt_y, 0, prompt_display)
        if visible:
            stdscr.addstr(prompt_y, len(prompt_display), visible)
        stdscr.move(prompt_y, cursor_screen_x)
        stdscr.refresh()

    def _prompt_for_input(
        self, prompt: str, initial_text: str = "", *, strip_result: bool = True
    ) -> Optional[str]:
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
        prompt_display = prompt[: max_x - 1] if max_x > 0 else ""
        max_input_width = max(10, max_x - len(prompt_display) - 1)
        text = initial_text[:max_input_width]
        cursor = len(text)

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        leaveok_changed = False
        try:
            stdscr.timeout(-1)
            try:
                stdscr.leaveok(False)
                leaveok_changed = True
            except curses.error:
                pass
            except Exception:
                pass
            try:
                curses.curs_set(1)
            except curses.error:
                pass

            self._render_prompt_input(
                stdscr, prompt_y, max_x, prompt_display, text, cursor
            )

            while True:
                key, meta = self._read_key_with_meta(stdscr)

                if key in (10, 13, curses.KEY_ENTER):
                    break
                if key == 27 and meta is None:
                    text = ""
                    break

                handled = False
                if key == 27 and meta is not None:
                    if meta in (ord("b"), ord("B")):
                        cursor = self._move_word_left(text, cursor)
                        handled = True
                    elif meta in (ord("f"), ord("F")):
                        cursor = self._move_word_right(text, cursor)
                        handled = True
                    elif meta in (127, 8, curses.KEY_BACKSPACE):
                        text, cursor = self._delete_prev_word(text, cursor)
                        handled = True
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    if cursor > 0:
                        text = text[: cursor - 1] + text[cursor:]
                        cursor -= 1
                    handled = True
                elif key == curses.KEY_DC:
                    if cursor < len(text):
                        text = text[:cursor] + text[cursor + 1 :]
                    handled = True
                elif key in (curses.KEY_LEFT, 2):  # Left / Ctrl+B
                    cursor = max(0, cursor - 1)
                    handled = True
                elif key in (curses.KEY_RIGHT, 6):  # Right / Ctrl+F
                    cursor = min(len(text), cursor + 1)
                    handled = True
                elif key in (curses.KEY_HOME, 1):  # Home / Ctrl+A
                    cursor = 0
                    handled = True
                elif key in (curses.KEY_END, 5):  # End / Ctrl+E
                    cursor = len(text)
                    handled = True
                elif key == 23:  # Ctrl+W
                    text, cursor = self._delete_prev_word(text, cursor)
                    handled = True
                elif 32 <= key <= 126 and len(text) < max_input_width:
                    text = text[:cursor] + chr(key) + text[cursor:]
                    cursor += 1
                    handled = True

                if handled:
                    self._render_prompt_input(
                        stdscr, prompt_y, max_x, prompt_display, text, cursor
                    )
        except KeyboardInterrupt:
            text = ""
        except Exception:
            text = ""
        finally:
            stdscr.timeout(40)
            if leaveok_changed:
                try:
                    stdscr.leaveok(True)
                except curses.error:
                    pass
                except Exception:
                    pass
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            self.nav.need_redraw = True

        result = text.strip() if strip_result else text
        return result or None

    def prompt_for_input(self, prompt: str) -> Optional[str]:
        return self._prompt_for_input(prompt)

    def _prompt_for_confirmation(self, prompt: str) -> Optional[bool]:
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
        prompt_display = prompt[: max_x - 1] if max_x > 0 else ""

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()
        try:
            stdscr.addstr(prompt_y, 0, prompt_display)
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)
            stdscr.refresh()
            while True:
                key = stdscr.getch()
                if key in (ord("y"), ord("Y")):
                    return True
                if key in (ord("q"), ord("Q")):
                    try:
                        curses.ungetch(key)
                    except curses.error:
                        pass
                    return False
                if key in (ord("n"), ord("N"), 27):
                    return False
        except KeyboardInterrupt:
            return False
        except Exception:
            return None
        finally:
            stdscr.timeout(40)
            self.nav.need_redraw = True

    def prompt_confirmation(self, message: str) -> bool:
        message = message.strip()
        if not message:
            return False
        if message[-1] not in "?:":
            message = f"{message}?"
        prompt = f"{message} (y/N): "
        response = self._prompt_for_confirmation(prompt)
        if response is None:
            return False
        return response

    # === File operations ===
    def open_file(self, filepath: str, *, detached: bool = False) -> bool:
        if filepath.endswith(".zip"):
            stdscr_opt = self.nav.renderer.stdscr
            if stdscr_opt is None:
                self._flash()
                self.nav.need_redraw = True
                return False
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
                            stdscr.addstr(
                                max_y - 1, 0, status[: max_x - 1], curses.A_BOLD
                            )
                            stdscr.refresh()
            except Exception:
                self._flash()
                self.nav.need_redraw = True
                return False
            self.nav.need_redraw = True
            return True

        mime_type, _ = mimetypes.guess_type(filepath)
        _, ext = os.path.splitext(filepath)
        ext_lower = ext.lower()

        handled = False
        is_text_like = False
        try:
            if ext_lower == ".csv":
                handled = self._invoke_handler(
                    self.nav.config.get_handler_spec("csv_viewer"),
                    filepath,
                    default_strategy="terminal",
                    detached=detached,
                )
            elif ext_lower == ".parquet":
                handled = self._invoke_handler(
                    self.nav.config.get_handler_spec("parquet_viewer"),
                    filepath,
                    default_strategy="terminal",
                    detached=detached,
                )
            elif ext_lower == ".h5":
                handled = self._invoke_handler(
                    self.nav.config.get_handler_spec("h5_viewer"),
                    filepath,
                    default_strategy="terminal",
                    detached=detached,
                )
            elif ext_lower == ".xlsx":
                handled = self._invoke_handler(
                    self.nav.config.get_handler_spec("xlsx_viewer"),
                    filepath,
                    default_strategy="external_background",
                    detached=detached,
                )
            elif mime_type == "application/pdf":
                handled = self._invoke_handler(
                    self.nav.config.get_handler_spec("pdf_viewer"),
                    filepath,
                    default_strategy="external_background",
                    detached=detached,
                )
            elif mime_type and mime_type.startswith("image/"):
                handled = self._invoke_handler(
                    self.nav.config.get_handler_spec("image_viewer"),
                    filepath,
                    default_strategy="external_background",
                    detached=detached,
                )
            elif (mime_type and mime_type.startswith("audio/")) or (
                ext_lower in MEDIA_AUDIO_EXTENSIONS
            ):
                handled = self._invoke_handler(
                    self._select_media_handler_spec("audio"),
                    filepath,
                    default_strategy="external_background",
                    detached=detached,
                )
            elif (mime_type and mime_type.startswith("video/")) or (
                ext_lower in MEDIA_VIDEO_EXTENSIONS
            ):
                handled = self._invoke_handler(
                    self._select_media_handler_spec("video"),
                    filepath,
                    default_strategy="external_background",
                    detached=detached,
                )
            else:
                is_text_like = is_text_like_file(filepath, mime_type)
                handled = self._invoke_handler(
                    self.nav.config.get_handler_spec("editor"),
                    filepath,
                    default_strategy="external_foreground",
                    detached=detached,
                )
        except FileNotFoundError:
            pass

        if not handled and is_text_like:
            if detached:
                handled = self._open_with_vim_detached(filepath)
            else:
                handled = self._open_with_vim(filepath)

        if not handled:
            self.nav.status_message = "No handler configured"
            self._flash()
        self.nav.need_redraw = True
        return handled

    def _open_with_vim(self, filepath: str) -> bool:
        flush_terminal_input()
        stdscr_opt = self.nav.renderer.stdscr
        if stdscr_opt is not None:
            try:
                curses.def_prog_mode()
            except curses.error:
                pass
            try:
                curses.endwin()
            except curses.error:
                pass

        try:
            cmd = "vim"
            if shutil.which(cmd):
                try:
                    subprocess.call([cmd, filepath])
                    return True
                except Exception:
                    pass
        finally:
            if stdscr_opt is not None:
                try:
                    curses.reset_prog_mode()
                except curses.error:
                    pass
                try:
                    curses.curs_set(0)
                except curses.error:
                    pass
                try:
                    stdscr = cast(Any, stdscr_opt)
                    stdscr.refresh()
                except Exception:
                    pass

        return False

    def _open_with_vim_detached(self, filepath: str) -> bool:
        if shutil.which("vim") is None:
            return False
        try:
            return bool(self.nav.open_terminal(None, ["vim", filepath]))
        except Exception:
            return False

    def _invoke_handler(
        self,
        spec: HandlerSpec,
        filepath: str,
        *,
        default_strategy: str,
        detached: bool = False,
    ) -> bool:
        if not spec.commands:
            return False

        if detached:
            return self._run_detached_handlers(
                spec.commands,
                filepath,
                default_strategy=default_strategy,
            )

        if spec.is_internal:
            return self._run_internal_handler(spec.commands, filepath)

        if default_strategy == "terminal":
            return self._run_terminal_handlers(spec.commands, filepath)
        if default_strategy == "external_foreground":
            return self._run_external_handlers(
                spec.commands,
                filepath,
                background=False,
            )
        if default_strategy == "external_background":
            return self._run_external_handlers(
                spec.commands,
                filepath,
                background=True,
            )

        return False

    def _run_detached_handlers(
        self,
        handlers: List[List[str]],
        filepath: str,
        *,
        default_strategy: str,
    ) -> bool:
        if default_strategy == "external_background":
            return self._run_external_handlers(
                handlers,
                filepath,
                background=True,
            )

        return self._run_terminal_handlers(handlers, filepath)

    def _run_external_handlers(
        self,
        handlers: List[List[str]],
        filepath: str,
        *,
        background: bool,
    ) -> bool:
        if not handlers:
            return False

        for raw_cmd in handlers:
            tokens = self._expand_command(raw_cmd, filepath)
            if not tokens:
                continue

            cmd_name = tokens[0]
            if shutil.which(cmd_name) is None:
                continue

            try:
                if background:
                    subprocess.Popen(
                        tokens,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        preexec_fn=os.setsid,
                    )
                else:
                    subprocess.call(tokens)
                return True
            except FileNotFoundError:
                continue
            except Exception:
                continue

        return False

    def _run_terminal_handlers(self, handlers: List[List[str]], filepath: str) -> bool:
        if not handlers:
            return False

        for raw_cmd in handlers:
            tokens = self._expand_command(raw_cmd, filepath)
            if not tokens:
                continue

            if self.nav.open_terminal(None, tokens):
                return True

        return False

    def _run_internal_handler(self, handlers: List[List[str]], filepath: str) -> bool:
        stdscr_opt = getattr(self.nav.renderer, "stdscr", None)

        if stdscr_opt is not None:
            try:
                curses.def_prog_mode()
            except curses.error:
                pass
            try:
                curses.endwin()
            except curses.error:
                pass

        succeeded = False
        attempted = False
        last_cmd = None

        try:
            for raw_cmd in handlers:
                tokens = self._expand_command(raw_cmd, filepath)
                if not tokens:
                    continue

                if shutil.which(tokens[0]) is None:
                    continue

                attempted = True
                last_cmd = tokens[0]

                try:
                    return_code = subprocess.call(tokens)
                except FileNotFoundError:
                    continue
                except Exception:
                    continue

                if return_code == 0:
                    succeeded = True
                    break
        finally:
            if stdscr_opt is not None:
                try:
                    curses.reset_prog_mode()
                except curses.error:
                    pass
                try:
                    curses.curs_set(0)
                except curses.error:
                    pass
                try:
                    stdscr = cast(Any, stdscr_opt)
                    stdscr.refresh()
                except Exception:
                    pass

        if succeeded:
            cmd_display = last_cmd or "handler"
            self.nav.status_message = f"Handler exited: {cmd_display}"
            self.nav.need_redraw = True
            return True

        if attempted:
            cmd_display = last_cmd or "handler"
            self.nav.status_message = f"Handler failed: {cmd_display}"
            self.nav.need_redraw = True
            curses.flash()
            return True

        return False

    def _expand_command(self, raw_cmd: List[str], filepath: str) -> List[str] | None:
        if not raw_cmd:
            return None

        tokens: List[str] = []
        has_placeholder = False

        for part in raw_cmd:
            if not isinstance(part, str):
                continue
            replaced = part.replace("{file}", filepath)
            if replaced != part:
                has_placeholder = True
            tokens.append(replaced)

        if not tokens:
            return None

        if not has_placeholder:
            tokens.append(filepath)

        return tokens

    def run_execution(self, filepath: str) -> bool:
        if not filepath or not os.path.isfile(filepath):
            self.nav.status_message = "Not a file"
            self._flash()
            self.nav.need_redraw = True
            return False

        existing_job = getattr(self.nav, "active_execution_job", None)
        if (
            existing_job is not None
            and isinstance(existing_job, ExecutionJob)
            and existing_job.is_running()
        ):
            self.nav.status_message = "Execution already in progress"
            self._flash()
            self.nav.need_redraw = True
            return False

        command, mode, error = self._resolve_execution_command(filepath)
        if not command:
            self.nav.status_message = error or "Unable to execute file"
            self._flash()
            self.nav.need_redraw = True
            return False

        assert mode is not None
        mode_value = cast(str, mode)

        cwd = os.path.dirname(filepath) or self.nav.dir_manager.current_path
        display = shlex.join(command)
        job = ExecutionJob(filepath, command, display, mode_value)

        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except FileNotFoundError:
            self.nav.status_message = f"Executor not found: {command[0]}"
            self._flash()
            self.nav.need_redraw = True
            return False
        except Exception as exc:
            self.nav.status_message = f"Failed to launch: {exc.__class__.__name__}"
            self._flash()
            self.nav.need_redraw = True
            return False

        job.mark_process(process)
        self.nav.set_active_execution_job(job)
        header = f"Running: {display}  (ESC to cancel)"
        self.nav.open_command_popup(header, [])

        thread = threading.Thread(
            target=self._monitor_execution_job, args=(job,), daemon=True
        )
        job.thread = thread
        thread.start()
        return True

    def _resolve_execution_command(
        self, filepath: str
    ) -> Tuple[Optional[List[str]], Optional[str], Optional[str]]:
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        if ext == ".py":
            python_cmd = self.nav.config.get_executor("python")
            if not python_cmd:
                return None, None, "Python executor unavailable"
            tokens = self._prepare_python_command(python_cmd, filepath)
            if not tokens:
                return None, None, "Python executor misconfigured"
            return tokens, "python", None

        if ext:
            return None, None, "File type not supported for execution"

        if not os.access(filepath, os.X_OK):
            return None, None, "File is not executable"

        shell_cmd = self.nav.config.get_executor("shell")
        if not shell_cmd:
            return None, None, "Shell executor unavailable"
        tokens = self._prepare_shell_command(shell_cmd, filepath)
        if not tokens:
            return None, None, "Shell executor misconfigured"
        return tokens, "shell", None

    def _prepare_python_command(self, base_cmd: List[str], filepath: str) -> List[str]:
        return self._expand_command(base_cmd, filepath) or []

    def _prepare_shell_command(self, base_cmd: List[str], filepath: str) -> List[str]:
        if not base_cmd:
            return []

        target = os.path.basename(filepath)
        if not target:
            return []

        relative_target = f"./{target}"
        quoted_target = shlex.quote(relative_target)

        tokens: List[str] = []
        has_placeholder = False

        for part in base_cmd:
            if not isinstance(part, str):
                continue
            if "{file}" in part:
                has_placeholder = True
                tokens.append(part.replace("{file}", quoted_target))
            else:
                tokens.append(part)

        if not tokens:
            return []

        if not has_placeholder:
            tokens.append(quoted_target)

        return tokens

    def _monitor_execution_job(self, job: ExecutionJob) -> None:
        process = job.process
        if process is None:
            return

        selector = selectors.DefaultSelector()

        def register_stream(stream, label):
            if stream is None:
                return
            try:
                selector.register(stream, selectors.EVENT_READ, data=label)
            except Exception:
                pass

        register_stream(process.stdout, "stdout")
        register_stream(process.stderr, "stderr")

        try:
            while True:
                if process.poll() is not None and not selector.get_map():
                    break

                events = selector.select(timeout=0.1)

                if not events:
                    if process.poll() is not None:
                        break
                    continue

                for key, _ in events:
                    label = key.data
                    stream = cast(Any, key.fileobj)
                    try:
                        chunk = stream.readline()  # type: ignore[attr-defined]
                    except Exception:
                        chunk = ""

                    if not chunk:
                        try:
                            selector.unregister(stream)
                        except Exception:
                            pass
                        continue

                    line = chunk.rstrip("\n")
                    formatted = self._format_stream_line(label, line)
                    self.nav.append_command_popup_lines([formatted])

            # Drain remaining buffered output after process finishes
            for label, stream in (
                ("stdout", process.stdout),
                ("stderr", process.stderr),
            ):
                if stream is None:
                    continue
                try:
                    remaining = cast(Any, stream).read()  # type: ignore[attr-defined]
                except Exception:
                    remaining = ""
                if not remaining:
                    continue
                for raw_line in remaining.splitlines():
                    formatted = self._format_stream_line(label, raw_line.rstrip("\n"))
                    self.nav.append_command_popup_lines([formatted])
        finally:
            for stream in (process.stdout, process.stderr):
                if stream and not stream.closed:
                    try:
                        stream.close()
                    except Exception:
                        pass
            try:
                selector.close()
            except Exception:
                pass

        exit_code = process.poll()
        if exit_code is None:
            try:
                exit_code = process.wait()
            except Exception:
                exit_code = process.returncode

        job.mark_finished(exit_code)

        if getattr(self.nav, "active_execution_job", None) is job:
            self.nav.clear_active_execution_job()

        with self.nav.command_popup_lock:
            empty_output = len(self.nav.command_popup_lines) == 0

        if empty_output:
            self.nav.append_command_popup_lines(["(no output)"])

        if job.cancelled:
            header = f"Cancelled: {job.display}"
        elif exit_code == 0:
            header = f"Completed (exit 0): {job.display}"
        else:
            header = f"Failed (exit {exit_code}): {job.display}"

        self.nav.update_command_popup_header(header)

    @staticmethod
    def _format_stream_line(channel: str, text: str) -> str:
        if channel == "stderr":
            return f"[stderr] {text}" if text else "[stderr]"
        return text

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
        new_name = self._prompt_for_input(prompt, initial_text=selected_name)
        if not new_name or new_name == selected_name:
            return

        unique_name = self.nav.input_handler._get_unique_name(parent_dir, new_name)
        new_path = os.path.join(parent_dir, unique_name)

        try:
            os.rename(selected_path, new_path)
        except Exception as e:
            prompt_y = max_y - 1
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
        self.nav.status_message = (
            f"Renamed to {unique_name}" if unique_name != selected_name else "Renamed"
        )
