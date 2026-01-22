# ~/Apps/vios/input_handler.py
import curses
import os
import time
import shutil
import subprocess
import sys
import termios
import tty
import select
from typing import List


class InputHandler:
    def __init__(self, navigator):
        self.nav = navigator
        self.pending_operator = None
        self.operator_timestamp = 0.0
        self.operator_timeout = 1.0
        self.in_filter_mode = False

        self.pending_comma = False
        self.comma_timestamp = 0.0
        self.comma_timeout = 2.0
        self.comma_sequence = ""

        self.last_escape_time = 0.0
        self.escape_double_threshold = 0.4
        self.command_cwd: str | None = None

    def _check_operator_timeout(self):
        if self.pending_operator and (
            time.time() - self.operator_timestamp > self.operator_timeout
        ):
            self.pending_operator = None

    def _check_comma_timeout(self):
        if self.pending_comma and (
            time.time() - self.comma_timestamp > self.comma_timeout
        ):
            self._reset_comma()

    def _flash(self):
        try:
            curses.flash()
        except curses.error:
            pass

    def _clear_clipboard(self):
        self.nav.clipboard.cleanup()
        self.nav.status_message = "Clipboard cleared"
        self.nav.need_redraw = True

    def _clear_marked_items(self):
        if self.nav.marked_items:
            self.nav.marked_items.clear()
            self.nav.status_message = "Cleared marks"
        else:
            self.nav.status_message = "No marks to clear"
        self.nav.need_redraw = True

    def _leader_rename(self, selection):
        if not selection:
            self._flash()
            return
        self.nav.rename_selected()

    def _leader_copy_path(self):
        self.nav.copy_current_path()

    def _leader_bookmark(self):
        target = self.nav.dir_manager.current_path
        if not self.nav.add_bookmark(target):
            self._flash()

    def _handle_comma_command(
        self, key, total: int, selection, context_path, scope_range, target_dir
    ) -> bool:
        ch = self._key_to_char(key)
        if ch is None:
            self._reset_comma()
            return True

        self.comma_sequence += ch
        command = self.comma_sequence
        self.nav.leader_sequence = "," + command
        self.nav.need_redraw = True

        base_dir = context_path or target_dir or self.nav.dir_manager.current_path

        command_map = {
            "j": lambda: self._jump_to_scope_edge("down", scope_range, total),
            "k": lambda: self._jump_to_scope_edge("up", scope_range, total),
            "sa": lambda: self._set_sort_mode("alpha", "Sort: Name", context_path),
            "sma": lambda: self._set_sort_mode(
                "mtime_asc", "Sort: Modified ↑", context_path
            ),
            "smd": lambda: self._set_sort_mode(
                "mtime_desc", "Sort: Modified ↓", context_path
            ),
            "cl": self._clear_clipboard,
            "nf": lambda: self.nav.create_new_file_no_open(base_dir),
            "nd": lambda: self.nav.create_new_directory(base_dir),
            "rn": lambda: self._leader_rename(selection),
            "cp": self._leader_copy_path,
            "b": self._leader_bookmark,
            "cm": self._clear_marked_items,
        }

        file_shortcuts = getattr(self.nav.config, "file_shortcuts", {}) or {}

        def _file_handler(token: str, command_repr: str):
            return (
                lambda shortcut_token=token,
                command_display=command_repr: self._launch_file_shortcut(
                    shortcut_token, command_display
                )
            )

        for token in sorted(file_shortcuts):
            primary_key = f"fo{token}"
            if primary_key not in command_map:
                command_map[primary_key] = _file_handler(token, primary_key)

            if (
                token.startswith("f")
                and len(token) == 2
                and token[1].isdigit()
                and token not in command_map
            ):
                command_map[token] = _file_handler(token, token)

        dir_shortcuts = getattr(self.nav.config, "dir_shortcuts", {}) or {}
        for token in sorted(dir_shortcuts):
            for command_key, change_dir, open_term in (
                (f"do{token}", True, False),
                (f"to{token}", False, True),
            ):
                if command_key in command_map:
                    continue
                command_map[command_key] = (
                    lambda shortcut_token=token,
                    do_change=change_dir,
                    launch_term=open_term,
                    prefix=command_key: self._invoke_directory_shortcut(
                        shortcut_token,
                        change_dir=do_change,
                        open_terminal=launch_term,
                        command_prefix=prefix,
                    )
                )

        workspace_shortcuts = getattr(self.nav.config, "workspace_shortcuts", {}) or {}
        for token in sorted(workspace_shortcuts):
            command_key = f"w{token}"
            if command_key in command_map:
                continue
            command_map[command_key] = (
                lambda shortcut_token=token,
                prefix=command_key: self._invoke_workspace_shortcut(
                    shortcut_token, command_prefix=prefix
                )
            )

        browser_shortcuts = getattr(self.nav.config, "browser_shortcuts", {}) or {}
        for token in sorted(browser_shortcuts):
            command_key = f"i{token}"
            if command_key in command_map:
                continue
            command_map[command_key] = (
                lambda shortcut_token=token,
                prefix=command_key: self._invoke_browser_shortcut(
                    shortcut_token, command_prefix=prefix
                )
            )

        if command in command_map:
            command_map[command]()
            self._reset_comma()
            return True

        if any(cmd.startswith(command) for cmd in command_map if cmd != command):
            return True

        self._reset_comma()
        return True

    def _set_browser_selected(self, index: int):
        items = self.nav.build_display_items()
        total = len(items)
        if total == 0:
            self.nav.browser_selected = 0
            return
        self.nav.browser_selected = max(0, min(index, total - 1))
        self.nav.update_visual_active(self.nav.browser_selected)

    def _jump_to_scope_edge(self, direction: str, scope_range, total: int):
        if scope_range:
            start, end = scope_range
            if (
                start is not None
                and end is not None
                and 0 <= start < total
                and 0 <= end < total
            ):
                target = start if direction == "up" else end
                self.nav.browser_selected = target
                self.nav.update_visual_active(self.nav.browser_selected)
                return
        if direction == "up":
            self._set_browser_selected(0)
        else:
            self._set_browser_selected(total - 1 if total else 0)

    def _move_selection(self, total: int, delta: int):
        if total <= 0:
            return
        self.nav.browser_selected = (self.nav.browser_selected + delta) % total
        self.nav.update_visual_active(self.nav.browser_selected)

    def _jump_selection(self, total: int, direction: str):
        if total <= 0:
            return
        jump = max(1, total // 10)
        if direction == "up":
            self.nav.browser_selected = max(0, self.nav.browser_selected - jump)
        else:
            self.nav.browser_selected = (
                min(total - 1, self.nav.browser_selected + jump) if total else 0
            )
        self.nav.update_visual_active(self.nav.browser_selected)

    def _notify_directories(self, dirs):
        real_dirs = {os.path.realpath(d) for d in dirs if d}
        if real_dirs:
            self.nav.notify_directory_changed(*real_dirs)
        else:
            self.nav.notify_directory_changed()

    def _set_sort_mode(self, mode: str, message: str, context_path):
        if context_path:
            self.nav.dir_manager.set_sort_mode_for_path(context_path, mode)
            pretty = os.path.basename(context_path.rstrip(os.sep)) or context_path
            self.nav.status_message = f"{message} ({pretty})"
        else:
            self.nav.dir_manager.set_sort_mode(mode)
            self.nav.status_message = message
        self.nav.need_redraw = True

    def _compute_context_scope(self, items, selected_index):
        if not items or selected_index < 0 or selected_index >= len(items):
            return (None, None)

        _, is_dir, selected_path, depth = items[selected_index]
        context_index = None

        if depth > 0:
            context_index = self._find_context_directory_index(items, selected_index)
        elif is_dir and selected_path in self.nav.expanded_nodes:
            context_index = selected_index

        if context_index is None:
            return (None, None)

        context_entry = items[context_index]
        context_path = os.path.realpath(context_entry[2])
        scope_range = self._find_scope_range_for_directory(items, context_index)
        return (context_path, scope_range)

    def _find_context_directory_index(self, items, selected_index):
        if selected_index < 0 or selected_index >= len(items):
            return None

        _, is_dir, _, depth = items[selected_index]
        if is_dir:
            return selected_index

        current_depth = depth

        for idx in range(selected_index - 1, -1, -1):
            _, candidate_is_dir, _, candidate_depth = items[idx]
            if candidate_depth < current_depth:
                if candidate_is_dir:
                    return idx
                current_depth = candidate_depth

        return None

    def _find_scope_range_for_directory(self, items, dir_index):
        if dir_index < 0 or dir_index >= len(items):
            return None

        base_depth = items[dir_index][3]
        first_child = None
        last_child = None

        for idx in range(dir_index + 1, len(items)):
            _, _, _, depth = items[idx]
            if depth <= base_depth:
                break
            if first_child is None:
                first_child = idx
            last_child = idx

        if first_child is None:
            first_child = dir_index
            last_child = dir_index

        if last_child is None:
            last_child = first_child

        return (first_child, last_child)

    def _reset_comma(self):
        self.pending_comma = False
        self.comma_sequence = ""
        self.nav.leader_sequence = ""
        self.nav.need_redraw = True

    def _launch_file_shortcut(self, token: str, command_display: str) -> None:
        shortcuts = getattr(self.nav.config, "file_shortcuts", {}) or {}
        path = shortcuts.get(token)

        if not path:
            self.nav.status_message = (
                f"No file shortcut configured for ,{command_display}"
            )
            self.nav.need_redraw = True
            self._flash()
            return

        if not os.path.isfile(path):
            self.nav.status_message = f"Shortcut ,{command_display} target missing: {os.path.basename(path) or path}"
            self.nav.need_redraw = True
            self._flash()
            return

        self.nav.open_file(path)
        self.nav.need_redraw = True

    def _enter_command_mode(self) -> None:
        self.nav.command_mode = True
        self.nav.command_buffer = ""
        self.nav.status_message = ""
        self.nav.leader_sequence = ""

        try:
            self.command_cwd = os.path.realpath(self.nav.dir_manager.current_path)
        except Exception:
            self.command_cwd = self.nav.dir_manager.current_path

        self.nav.need_redraw = True

    def _handle_command_mode_key(self, key: int) -> None:
        if key in (10, 13, curses.KEY_ENTER):
            command = self.nav.command_buffer.strip()
            self.nav.command_buffer = ""
            self._execute_command(command)
            return

        if key == 27:  # Esc
            self.nav.command_mode = False
            self.nav.command_buffer = ""
            self.nav.status_message = "Command cancelled"
            self.nav.need_redraw = True
            self.command_cwd = None
            return

        if key in (curses.KEY_BACKSPACE, 127, 8):
            if self.nav.command_buffer:
                self.nav.command_buffer = self.nav.command_buffer[:-1]
                self.nav.need_redraw = True
            else:
                self.nav.command_mode = False
                self.nav.status_message = "Command cancelled"
                self.nav.need_redraw = True
                self.command_cwd = None
            return

        char = self._key_to_char(key)
        if char is not None:
            self.nav.command_buffer += char
            self.nav.need_redraw = True

    def _execute_command(self, command: str) -> None:
        if not command:
            self.nav.command_mode = False
            self.nav.status_message = "No command entered"
            self.nav.need_redraw = True
            self.command_cwd = None
            return

        if command.startswith("!"):
            shell_cmd = command[1:].strip()
            if not shell_cmd:
                self.nav.command_mode = False
                self.nav.status_message = "Empty shell command"
                self.nav.need_redraw = True
                self.command_cwd = None
                return
            self._run_shell_command(shell_cmd)
            return

        self.nav.status_message = f"Unknown command: {command}"
        self._flash()
        self.nav.command_mode = False
        self.nav.need_redraw = True
        self.command_cwd = None

    def _run_shell_command(self, shell_cmd: str) -> None:
        stdscr_opt = getattr(self.nav.renderer, "stdscr", None)
        suspended = False
        if stdscr_opt is not None:
            try:
                curses.def_prog_mode()
            except curses.error:
                pass
            try:
                curses.endwin()
            except curses.error:
                pass
            suspended = True

        cwd_candidate = self.command_cwd or self.nav.dir_manager.current_path
        cwd = os.path.realpath(cwd_candidate)
        if not os.path.isdir(cwd):
            cwd = self.nav.dir_manager.current_path
        return_code = None
        error_message = ""

        try:
            result = subprocess.run(shell_cmd, shell=True, cwd=cwd)
            return_code = result.returncode
        except Exception as exc:  # pragma: no cover
            error_message = str(exc)

        message = ""
        should_flash = False
        notify_dirs = False

        if return_code is None:
            message = f"! {shell_cmd} failed: {error_message}"
            should_flash = True
        else:
            message = f"! {shell_cmd} (exit {return_code})"
            if return_code == 0:
                notify_dirs = True
            else:
                should_flash = True

        waited = False
        if sys.stdin.isatty():
            print(f"\n{message}", flush=True)
            print("Press ESC to return to o...", flush=True)
            self._wait_for_escape_key()
            waited = True

        if suspended and stdscr_opt is not None:
            try:
                curses.reset_prog_mode()
            except curses.error:
                pass
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            try:
                stdscr_opt.refresh()
            except Exception:
                pass

        if notify_dirs and hasattr(self.nav, "notify_directory_changed"):
            self.nav.notify_directory_changed()

        if should_flash and (not sys.stdin.isatty() or not waited):
            self._flash()

        self.nav.command_mode = False
        self.nav.status_message = message
        self.nav.need_redraw = True
        self.command_cwd = None

    def _wait_for_escape_key(self) -> None:
        stdin = sys.stdin
        if not stdin.isatty():
            return

        fd = stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                ready, _, _ = select.select([stdin], [], [], None)
                if not ready:
                    continue
                ch = stdin.read(1)
                if ch == "\x1b" or ch == "":
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _run_workspace_commands(
        self, commands: List[List[str]], *, background: bool
    ) -> bool:
        if not commands:
            return False

        success = False

        stdscr_opt = getattr(self.nav.renderer, "stdscr", None)

        def _suspend_curses():
            if stdscr_opt is None:
                return
            try:
                curses.def_prog_mode()
            except curses.error:
                pass
            try:
                curses.endwin()
            except curses.error:
                pass

        def _resume_curses():
            if stdscr_opt is None:
                return
            try:
                curses.reset_prog_mode()
            except curses.error:
                pass
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            try:
                stdscr_opt.refresh()
            except Exception:
                pass

        cwd = self.nav.dir_manager.current_path

        for raw_tokens in commands:
            tokens = [os.path.expanduser(tok) for tok in raw_tokens]
            if not tokens:
                continue

            if background:
                if self.nav.open_terminal(None, tokens):
                    success = True
                    break
                continue

            _suspend_curses()
            try:
                result = subprocess.run(tokens, cwd=cwd)
                if result.returncode == 0:
                    success = True
                    break
            except FileNotFoundError:
                continue
            except Exception:
                continue
            finally:
                _resume_curses()

        return success

    def _invoke_browser_shortcut(self, token: str, *, command_prefix: str) -> None:
        shortcuts = getattr(self.nav.config, "browser_shortcuts", {}) or {}
        command = f",{command_prefix}"

        url = shortcuts.get(token)
        if not url:
            self.nav.status_message = (
                f"No browser shortcut configured for {command}"
            )
            self.nav.need_redraw = True
            self._flash()
            return

        open_url_fn = getattr(self.nav.file_actions, "open_url", None)
        opened = False
        if callable(open_url_fn):
            try:
                opened = bool(open_url_fn(url))
            except Exception:
                opened = False

        if opened:
            self.nav.status_message = f"Opened URL {url}"
        else:
            self.nav.status_message = f"Failed to open URL for {command}"
            self._flash()

        self.nav.need_redraw = True

    def _invoke_directory_shortcut(
        self,
        token: str,
        *,
        change_dir: bool,
        open_terminal: bool,
        command_prefix: str,
    ) -> None:
        shortcuts = getattr(self.nav.config, "dir_shortcuts", {}) or {}
        path = shortcuts.get(token)

        command = f",{command_prefix}"
        if not path:
            self.nav.status_message = f"No directory shortcut configured for {command}"
            self.nav.need_redraw = True
            self._flash()
            return

        if not os.path.isdir(path):
            pretty = os.path.basename(path.rstrip(os.sep)) or path
            self.nav.status_message = f"Shortcut {command} missing directory: {pretty}"
            self.nav.need_redraw = True
            self._flash()
            return

        pretty = self.nav.dir_manager.pretty_path(path)
        change_success = True

        if change_dir:
            change_success = self.nav.change_directory(path)
            if not change_success:
                self.nav.status_message = f"Failed to jump to {pretty}"
                self.nav.need_redraw = True
                self._flash()
                return

        if open_terminal:
            base_path = path if not change_dir else None
            self.nav.open_terminal(base_path)

        if change_dir and open_terminal:
            self.nav.status_message = f"Jumped to {pretty} and opened terminal"
        elif change_dir:
            self.nav.status_message = f"Jumped to {pretty}"
        elif open_terminal:
            self.nav.status_message = f"Opened terminal at {pretty}"

        self.nav.need_redraw = True

    def _invoke_workspace_shortcut(self, token: str, *, command_prefix: str) -> None:
        shortcuts = getattr(self.nav.config, "workspace_shortcuts", {}) or {}
        entry = shortcuts.get(token)

        command = f",{command_prefix}"
        if not entry:
            self.nav.status_message = f"No workspace shortcut configured for {command}"
            self.nav.need_redraw = True
            self._flash()
            return

        fragments = []
        issues = []
        success = False

        internal_path = entry.get("internal_path")
        external_path = entry.get("external_path")
        internal_commands = entry.get("internal_commands", [])
        external_commands = entry.get("external_commands", [])

        if external_commands:
            if self._run_workspace_commands(external_commands, background=True):
                fragments.append("external command")
                success = True
            else:
                issues.append("external commands failed")

        if external_path:
            if not os.path.exists(external_path):
                issues.append(
                    f"external missing {os.path.basename(external_path) or external_path}"
                )
            elif os.path.isdir(external_path):
                self.nav.open_terminal(external_path)
                pretty = os.path.basename(external_path.rstrip(os.sep)) or external_path
                fragments.append(f"terminal at {pretty}")
                success = True
            else:
                self.nav.open_file(external_path)
                fragments.append(
                    f"external {os.path.basename(external_path) or external_path}"
                )
                success = True

        if internal_commands:
            if self._run_workspace_commands(internal_commands, background=False):
                fragments.append("internal command")
                success = True
                if hasattr(self.nav, "notify_directory_changed"):
                    self.nav.notify_directory_changed()
            else:
                issues.append("internal commands failed")

        if internal_path:
            if not os.path.exists(internal_path):
                issues.append(
                    f"internal missing {os.path.basename(internal_path) or internal_path}"
                )
            elif os.path.isdir(internal_path):
                if self.nav.change_directory(internal_path):
                    pretty = (
                        os.path.basename(internal_path.rstrip(os.sep)) or internal_path
                    )
                    fragments.append(f"jumped to {pretty}")
                    success = True
                else:
                    issues.append(
                        f"failed to enter {os.path.basename(internal_path) or internal_path}"
                    )
            else:
                self.nav.open_file(internal_path)
                fragments.append(
                    f"opened {os.path.basename(internal_path) or internal_path}"
                )
                success = True

        if success:
            message = f"Workspace {command}: " + "; ".join(fragments)
            if issues:
                message += f" (issues: {'; '.join(issues)})"
            self.nav.status_message = message
        else:
            issue_text = "; ".join(issues) if issues else "no actions available"
            self.nav.status_message = f"Workspace {command} unavailable ({issue_text})"
            self._flash()

        self.nav.need_redraw = True

    def _handle_help_scroll(self, key, stdscr):
        lines = len(self.nav.cheatsheet.strip().split("\n"))
        max_y = stdscr.getmaxyx()[0] if stdscr else 0
        max_visible = max(1, max_y - 1)
        max_scroll = max(0, lines - max_visible)

        if key == ord("?"):
            self.nav.show_help = False
            self.nav.help_scroll = 0
            self.nav.need_redraw = True
            return True

        if key in (curses.KEY_UP, ord("k")):
            self.nav.help_scroll = max(0, self.nav.help_scroll - 1)
            self.nav.need_redraw = True
            return True
        if key in (curses.KEY_DOWN, ord("j")):
            self.nav.help_scroll = min(max_scroll, self.nav.help_scroll + 1)
            self.nav.need_redraw = True
            return True
        if key in (curses.KEY_SR, 11):  # Ctrl+K
            jump = max(1, max_visible // 2)
            self.nav.help_scroll = max(0, self.nav.help_scroll - jump)
            self.nav.need_redraw = True
            return True
        if key in (curses.KEY_SF, 10):  # Ctrl+J
            jump = max(1, max_visible // 2)
            self.nav.help_scroll = min(max_scroll, self.nav.help_scroll + jump)
            self.nav.need_redraw = True
            return True

        return False

    def _key_to_char(self, key):
        if 32 <= key <= 126:
            return chr(key)
        return None

    def handle_key(self, stdscr, key):
        self.nav.status_message = ""
        if self.nav.show_help:
            handled = self._handle_help_scroll(key, stdscr)
            if handled:
                return False
            return False

        if getattr(self.nav, "command_mode", False):
            self._handle_command_mode_key(key)
            return False

        self._check_operator_timeout()
        self._check_comma_timeout()

        # === FILTER MODE ===
        if not self.in_filter_mode and key == ord(":"):
            self.nav.exit_visual_mode()
            self._enter_command_mode()
            return False

        if key == ord("/"):
            self.nav.exit_visual_mode()
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
            self.nav.exit_visual_mode()
            self.in_filter_mode = False
            self.nav.dir_manager.filter_pattern = ""
            self.nav.expanded_nodes.clear()
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
                    self.nav.dir_manager.filter_pattern = (
                        self.nav.dir_manager.filter_pattern[:-1]
                    )
                else:
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
                return False

        if key == 27:  # Esc outside filter mode
            if getattr(self.nav, "visual_mode", False):
                self.nav.exit_visual_mode()
                self.last_escape_time = 0.0
                return False
            now = time.time()
            is_double = (now - self.last_escape_time) <= self.escape_double_threshold
            self.last_escape_time = 0.0 if is_double else now

            self._reset_comma()
            self.pending_operator = None
            self.in_filter_mode = False
            self.nav.dir_manager.filter_pattern = ""

            if is_double:
                self.nav.reset_to_home()
                self.nav.status_message = "Returned to ~"
            else:
                current_path = self.nav.dir_manager.current_path
                self.nav.collapse_expansions_under(current_path)
                self.nav.status_message = (
                    f"Collapsed {os.path.basename(current_path) or current_path}"
                )

            return False

        display_items = self.nav.build_display_items()
        total = len(display_items)
        selection = None
        selected_name = selected_path = selected_is_dir = None
        target_dir = self.nav.dir_manager.current_path
        context_path = None
        scope_range = None

        if total == 0:
            self.nav.browser_selected = 0
        else:
            self.nav.browser_selected = max(
                0, min(self.nav.browser_selected, total - 1)
            )
            selection = display_items[self.nav.browser_selected]
            selected_name, selected_is_dir, selected_path, _ = selection
            target_dir = self._determine_target_directory(
                selected_path, selected_is_dir
            )
            context_path, scope_range = self._compute_context_scope(
                display_items, self.nav.browser_selected
            )

        if key == ord(","):
            self.pending_comma = True
            self.comma_sequence = ""
            self.comma_timestamp = time.time()
            self.nav.leader_sequence = ","
            self.nav.need_redraw = True
            return False

        if self.pending_comma:
            if self._handle_comma_command(
                key, total, selection, context_path, scope_range, target_dir
            ):
                return False

        if key in (10, 13, curses.KEY_ENTER):
            if self.nav.layout_mode == "list":
                self.nav.enter_matrix_mode()
            else:
                self.nav.enter_list_mode()
            return False

        if key == 8:  # Ctrl+H
            self.nav.exit_visual_mode()
            if self.nav.layout_mode == "matrix":
                self._jump_selection(total, "up")
                return False
            if self.nav.go_history_back():
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
            else:
                self._flash()
            return False

        if key == 12:  # Ctrl+L
            self.nav.exit_visual_mode()
            if self.nav.layout_mode == "matrix":
                self._jump_selection(total, "down")
                return False
            if self.nav.go_history_forward():
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
            else:
                self._flash()
            return False

        # === Toggle mark with 'm' — now using full path ===
        if key == ord("m"):
            self.nav.exit_visual_mode()
            if total > 0:
                full_path = selected_path
                if full_path in self.nav.marked_items:
                    self.nav.marked_items.remove(full_path)
                else:
                    self.nav.marked_items.add(full_path)
                # Auto-advance after marking
                self.nav.browser_selected = (self.nav.browser_selected + 1) % total
            return False

        # === VISUAL MODE TOGGLE ===
        if key == ord("v"):
            if total > 0:
                if getattr(self.nav, "visual_mode", False):
                    self._commit_visual_selection(display_items)
                else:
                    self.nav.enter_visual_mode(self.nav.browser_selected)
            else:
                self.nav.exit_visual_mode()
            return False

        # === Other single-key commands ===
        if key == ord("?"):
            self.nav.show_help = True
            self.nav.help_scroll = 0
            return False

        if key == ord("."):
            self.nav.exit_visual_mode()
            self.nav.dir_manager.toggle_hidden()
            self.nav.expanded_nodes.clear()
            return False

        if key == ord("t"):
            self.nav.open_terminal()
            return False

        if key == ord("e") and total > 0 and selected_path:
            self.nav.exit_visual_mode()
            if selected_is_dir:
                target_path = selected_path
            else:
                target_path = os.path.dirname(selected_path)

            if not target_path:
                self._flash()
                return False

            target_name = os.path.basename(target_path) or target_path
            if target_path in self.nav.expanded_nodes:
                collapse_index = None
                for idx, (_, _, path, _) in enumerate(display_items):
                    if os.path.realpath(path) == os.path.realpath(target_path):
                        collapse_index = idx
                        break

                self.nav.collapse_branch(target_path)
                if collapse_index is not None:
                    self.nav.browser_selected = collapse_index
                    self.nav.update_visual_active(self.nav.browser_selected)
                self.nav.status_message = f"Collapsed {target_name}"
            else:
                self.nav.expanded_nodes.add(target_path)
                self.nav.status_message = f"Expanded {target_name}"
            self.nav.need_redraw = True
            return False

        # === Multi-mark operations ===
        if self.nav.marked_items:
            if key == ord("p"):
                self._copy_marked(target_dir)
                return False
            if key == ord("x"):
                self._delete_marked()
                return False

        # === Single-item paste (only when no marks) ===
        if key == ord("p") and self.nav.clipboard.has_entries:
            try:
                self.nav.clipboard.paste(target_dir)
                count = self.nav.clipboard.entry_count
                noun = "item" if count == 1 else "items"
                self.nav.status_message = f"Pasted {count} {noun}"
                self._notify_directories({target_dir})
            except Exception:
                self._flash()
            return False

        if key == ord("x"):
            if getattr(self.nav, "visual_mode", False):
                entries = self._collect_visual_entries(display_items)
                if not entries:
                    self.nav.exit_visual_mode()
                    return False
                success = True
                dirs = set()
                for path, _, is_dir_entry in entries:
                    try:
                        if is_dir_entry:
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        dirs.add(os.path.dirname(path))
                    except Exception:
                        success = False
                        break
                if success:
                    count = len(entries)
                    noun = "item" if count == 1 else "items"
                    self.nav.status_message = f"Deleted {count} {noun}"
                    self.nav.exit_visual_mode()
                    self._notify_directories(dirs)
                else:
                    self._flash()
                self.nav.need_redraw = True
                return False

        if key == ord("x") and total > 0 and selected_path:
            try:
                if selected_is_dir:
                    shutil.rmtree(selected_path)
                else:
                    os.remove(selected_path)
                self.nav.status_message = f"Deleted {selected_name}"
            except Exception:
                self._flash()
            finally:
                self.nav.need_redraw = True
                parent_dir = os.path.dirname(
                    selected_path or self.nav.dir_manager.current_path
                )
                self._notify_directories({parent_dir})
            return False

        # === yy / dd operators ===
        if self.pending_operator == "d" and key == ord("d"):
            handled = False
            if getattr(self.nav, "visual_mode", False):
                entries = self._collect_visual_entries(display_items)
                handled = self._stage_visual_to_clipboard(entries, cut=True)
            elif self.nav.marked_items:
                handled = self._stage_marked_to_clipboard(cut=True)
            elif total > 0:
                try:
                    self.nav.clipboard.yank(
                        selected_path, selected_name, selected_is_dir, cut=True
                    )
                    parent_dir = os.path.dirname(
                        selected_path or self.nav.dir_manager.current_path
                    )
                    self._notify_directories({parent_dir})
                    handled = True
                except Exception:
                    self._flash()
            self.pending_operator = None
            if handled:
                return False

        if self.pending_operator == "y" and key == ord("y"):
            handled = False
            if getattr(self.nav, "visual_mode", False):
                entries = self._collect_visual_entries(display_items)
                handled = self._stage_visual_to_clipboard(entries, cut=False)
            elif self.nav.marked_items:
                handled = self._stage_marked_to_clipboard(cut=False)
            elif total > 0:
                try:
                    self.nav.clipboard.yank(
                        selected_path, selected_name, selected_is_dir, cut=False
                    )
                    handled = True
                except Exception:
                    self._flash()
            self.pending_operator = None
            if handled:
                return False

        if key == ord("d"):
            self.pending_operator = "d"
            self.operator_timestamp = time.time()
            return False

        if key == ord("y"):
            self.pending_operator = "y"
            self.operator_timestamp = time.time()
            return False

        if self.pending_operator:
            self.pending_operator = None

        is_matrix = self.nav.layout_mode == "matrix"

        if is_matrix:
            if key == ord("h"):
                if total > 0:
                    self._move_selection(total, -1)
                else:
                    self._flash()
                return False
            if key == ord("l"):
                if total > 0:
                    self._move_selection(total, 1)
                else:
                    self._flash()
                return False
            if key == ord("j"):
                if total > 0:
                    if selected_is_dir and selected_path:
                        previous_path = self.nav.dir_manager.current_path
                        self.nav.remember_matrix_position()
                        if self.nav.change_directory(selected_path):
                            self.in_filter_mode = False
                            self.nav.dir_manager.filter_pattern = ""
                            self.nav.exit_visual_mode()
                            self.nav.update_visual_active(self.nav.browser_selected)
                        else:
                            self.nav.discard_matrix_position(previous_path)
                    elif selected_path:
                        self.nav.open_file(selected_path)
                else:
                    self._flash()
                return False
            if key == ord("k"):
                parent = os.path.dirname(self.nav.dir_manager.current_path)
                if parent and parent != self.nav.dir_manager.current_path:
                    if self.nav.change_directory(parent):
                        self.in_filter_mode = False
                        self.nav.dir_manager.filter_pattern = ""
                        self.nav.exit_visual_mode()
                        self.nav.update_visual_active(self.nav.browser_selected)
                else:
                    self._flash()
                return False
        else:
            if key == ord("j"):
                if total > 0:
                    self._move_selection(total, 1)
                else:
                    self._flash()
                return False
            if key == ord("k"):
                if total > 0:
                    self._move_selection(total, -1)
                else:
                    self._flash()
                return False
            if key == ord("h"):
                parent = os.path.dirname(self.nav.dir_manager.current_path)
                if parent and parent != self.nav.dir_manager.current_path:
                    if self.nav.change_directory(parent):
                        self.in_filter_mode = False
                        self.nav.dir_manager.filter_pattern = ""
                        self.nav.exit_visual_mode()
                else:
                    self._flash()
                return False
            if key == ord("l"):
                if total > 0:
                    if selected_is_dir and selected_path:
                        if self.nav.change_directory(selected_path):
                            self.in_filter_mode = False
                            self.nav.dir_manager.filter_pattern = ""
                            self.nav.exit_visual_mode()
                    elif selected_path:
                        self.nav.open_file(selected_path)
                else:
                    self._flash()
                return False

        if key == curses.KEY_UP and total > 0:
            self._move_selection(total, -1)
        elif key == curses.KEY_DOWN and total > 0:
            self._move_selection(total, 1)
        elif key in (curses.KEY_SR, 11):  # Ctrl+K
            self._jump_selection(total, "up")
        elif key in (curses.KEY_SF, 10):  # Ctrl+J
            self._jump_selection(total, "down")
        elif key == curses.KEY_LEFT:
            parent = os.path.dirname(self.nav.dir_manager.current_path)
            if parent and parent != self.nav.dir_manager.current_path:
                if self.nav.change_directory(parent):
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
                    self.nav.exit_visual_mode()
        elif key == curses.KEY_RIGHT and total > 0:
            if selected_is_dir and selected_path:
                if self.nav.change_directory(selected_path):
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
                    self.nav.exit_visual_mode()
            elif selected_path:
                self.nav.open_file(selected_path)

        return False

    # === Updated multi-mark operations using full paths ===
    def _copy_marked(self, dest_dir):
        self.nav.exit_visual_mode()
        self._move_or_copy_marked(dest_dir, copy_only=True)

    def _delete_marked(self):
        self.nav.exit_visual_mode()
        if not self.nav.marked_items:
            self._flash()
            return

        success = True
        affected_dirs = set()
        for full_path in list(self.nav.marked_items):
            try:
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
                affected_dirs.add(os.path.dirname(full_path))
            except Exception:
                success = False
                break

        if success:
            self.nav.marked_items.clear()
            self._notify_directories(affected_dirs)
        else:
            self._flash()

        self.nav.need_redraw = True

    def _move_or_copy_marked(self, dest_dir, copy_only: bool):
        self.nav.exit_visual_mode()
        if not self.nav.marked_items:
            self._flash()
            return

        if not dest_dir or not os.path.isdir(dest_dir):
            dest_dir = self.nav.dir_manager.current_path
        dest_dir_real = os.path.realpath(dest_dir)
        success = True
        source_dirs = set()

        for full_path in list(self.nav.marked_items):
            if not os.path.exists(full_path):
                success = False
                break

            name = os.path.basename(full_path)
            dest_path = os.path.join(dest_dir, name)
            source_dirs.add(os.path.dirname(full_path))

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
            notify_dirs = set()
            if not copy_only:
                notify_dirs.update(source_dirs)
            notify_dirs.add(dest_dir_real)
            self._notify_directories(notify_dirs)
        else:
            self._flash()

        self.nav.need_redraw = True

    def _stage_marked_to_clipboard(self, cut: bool) -> bool:
        self.nav.exit_visual_mode()
        if not self.nav.marked_items:
            return False

        entries = []
        for full_path in sorted(self.nav.marked_items):
            if not os.path.exists(full_path):
                continue
            name = os.path.basename(full_path)
            is_dir = os.path.isdir(full_path)
            entries.append((full_path, name, is_dir))

        if not entries:
            self._flash()
            self.nav.marked_items.clear()
            return False

        try:
            self.nav.clipboard.yank_multiple(entries, cut=cut)
            self.nav.marked_items.clear()
            count = len(entries)
            action = "Cut" if cut else "Yanked"
            noun = "item" if count == 1 else "items"
            self.nav.status_message = f"{action} {count} {noun} to clipboard"
            if cut:
                dirs = {os.path.dirname(path) for path, _, _ in entries}
                self._notify_directories(dirs)
            return True
        except Exception:
            self._flash()
            return False

    def _determine_target_directory(self, selected_path, selected_is_dir):
        if selected_path:
            if selected_is_dir:
                return selected_path
            parent = os.path.dirname(selected_path)
            if parent:
                return parent
        return self.nav.dir_manager.current_path

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

    def _collect_visual_entries(self, items):
        if not getattr(self.nav, "visual_mode", False):
            return []
        indices = self.nav.get_visual_indices(len(items))
        entries = []
        for idx in indices:
            if 0 <= idx < len(items):
                name, is_dir, path, _ = items[idx]
                entries.append((path, name, is_dir))
        return entries

    def _stage_visual_to_clipboard(self, entries, cut: bool) -> bool:
        if not entries:
            return False
        try:
            self.nav.clipboard.yank_multiple(entries, cut=cut)
        except Exception:
            self._flash()
            return False

        count = len(entries)
        action = "Cut" if cut else "Yanked"
        noun = "item" if count == 1 else "items"
        self.nav.status_message = f"{action} {count} {noun} to clipboard"
        self.nav.exit_visual_mode()
        if cut:
            dirs = {os.path.dirname(path) for path, _, _ in entries}
            self._notify_directories(dirs)
        return True

    def _commit_visual_selection(self, items):
        if not getattr(self.nav, "visual_mode", False):
            return
        indices = self.nav.get_visual_indices(len(items))
        if not indices:
            self.nav.exit_visual_mode()
            return

        unique_paths = []
        for idx in indices:
            if 0 <= idx < len(items):
                path = items[idx][2]
                if path not in unique_paths:
                    unique_paths.append(path)

        count = len(unique_paths)
        noun = "item" if count == 1 else "items"
        self.nav.exit_visual_mode(clear_message=False)
        if count:
            self.nav.status_message = f"Pinned {count} {noun}"
