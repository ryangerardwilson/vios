# ~/Apps/vios/input_handler.py
import curses
import os
import time
import shutil
import subprocess
from typing import List

import config
from keys import is_ctrl_j, is_enter


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

        self.command_cwd: str | None = None
        self.last_repeat_sequence: list[int] | None = None
        self.is_repeating = False
        self.repeatable_leader_commands = {
            "xr",
            "xar",
            "dot",
            "conf",
            "nf",
            "nd",
            "rn",
            "b",
        }

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

    def _leader_bookmark(self):
        target = self.nav.dir_manager.current_path
        if not self.nav.add_bookmark(target):
            self._flash()

    def _toggle_inline_expansion(self, selection, display_items):
        if not selection:
            self._flash()
            return

        _, is_dir, selected_path, _ = selection

        if not selected_path:
            self._flash()
            return

        if is_dir:
            target_path = selected_path
        else:
            target_path = os.path.dirname(selected_path)

        if not target_path:
            self._flash()
            return

        target_real = os.path.realpath(target_path)
        target_name = os.path.basename(target_path) or target_path

        if target_path in self.nav.expanded_nodes:
            collapse_index = None
            for idx, (_, _, path, _) in enumerate(display_items):
                if os.path.realpath(path) == target_real:
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

    def _toggle_hidden_files(self):
        self.nav.exit_visual_mode()

        toggle_fn = getattr(self.nav.dir_manager, "toggle_hidden", None)
        if not callable(toggle_fn):
            self._flash()
            return

        toggle_fn()
        self.nav.expanded_nodes.clear()

        status = "Showing dotfiles" if getattr(self.nav.dir_manager, "show_hidden", False) else "Hiding dotfiles"
        self.nav.status_message = status
        self.nav.need_redraw = True

    def _collapse_all_expansions(self):
        self.nav.exit_visual_mode()
        if self.nav.expanded_nodes:
            self.nav.expanded_nodes.clear()
            self.nav.status_message = "Collapsed all expansions"
        else:
            self.nav.status_message = "No expansions to collapse"
        self.nav.need_redraw = True

    def _record_repeat_sequence(self, keys: list[int]) -> None:
        if not keys:
            self.last_repeat_sequence = None
            return
        self.last_repeat_sequence = list(keys)

    def _expand_all_directories(self):
        self.nav.exit_visual_mode()

        root = os.path.realpath(self.nav.dir_manager.current_path)
        to_visit = [root]
        visited = set()
        added = 0

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)

            try:
                entries = self.nav.dir_manager.list_directory(current)
            except Exception:
                continue

            for name, is_dir in entries:
                if not is_dir:
                    continue
                child_path = os.path.realpath(os.path.join(current, name))
                to_visit.append(child_path)
                if child_path not in self.nav.expanded_nodes:
                    self.nav.expanded_nodes.add(child_path)
                    added += 1

        if added:
            self.nav.status_message = f"Expanded {added} directories"
        else:
            self.nav.status_message = "No directories expanded"
        self.nav.need_redraw = True

    def _handle_comma_command(
        self,
        key,
        total: int,
        selection,
        context_path,
        scope_range,
        target_dir,
        display_items=None,
    ) -> bool:
        if display_items is None:
            display_items = self.nav.build_display_items()
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
            "b": self._leader_bookmark,
            "cm": self._clear_marked_items,
            "xr": lambda: self._toggle_inline_expansion(selection, display_items),
            "dot": self._toggle_hidden_files,
            "xc": self._collapse_all_expansions,
            "xar": self._expand_all_directories,
            "conf": self._open_user_config,
        }

        if command in command_map:
            command_map[command]()
            if command in self.repeatable_leader_commands:
                sequence = [ord(",")] + [ord(ch) for ch in command]
                self._record_repeat_sequence(sequence)
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

    def _enter_command_mode(self) -> None:
        self.nav.command_mode = True
        self.nav.command_buffer = ""
        self.nav.status_message = ""
        self.nav.leader_sequence = ""

        try:
            self.command_cwd = os.path.realpath(self.nav.dir_manager.current_path)
        except Exception:
            self.command_cwd = self.nav.dir_manager.current_path

        if hasattr(self.nav, "command_history"):
            self.nav.command_history_index = len(self.nav.command_history)

        self.nav.need_redraw = True

    def _handle_command_mode_key(self, key: int) -> None:
        if is_enter(key):
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
            if hasattr(self.nav, "command_history_index"):
                self.nav.command_history_index = None
            return

        if key in (curses.KEY_BACKSPACE, 127, 8):
            if self.nav.command_buffer:
                self.nav.command_buffer = self.nav.command_buffer[:-1]
                self.nav.need_redraw = True
                if hasattr(self.nav, "command_history_index"):
                    self.nav.command_history_index = len(self.nav.command_history)
            else:
                self.nav.command_mode = False
                self.nav.status_message = "Command cancelled"
                self.nav.need_redraw = True
                self.command_cwd = None
                if hasattr(self.nav, "command_history_index"):
                    self.nav.command_history_index = None
            return

        if key == 16:  # Ctrl+P
            if self._command_history_step(-1):
                self.nav.need_redraw = True
            return

        if key == 14:  # Ctrl+N
            if self._command_history_step(1):
                self.nav.need_redraw = True
            return

        char = self._key_to_char(key)
        if char is not None:
            self.nav.command_buffer += char
            self.nav.need_redraw = True
            if hasattr(self.nav, "command_history_index"):
                self.nav.command_history_index = len(self.nav.command_history)

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
                if hasattr(self.nav, "command_history_index"):
                    self.nav.command_history_index = None
                return
            self._run_shell_command(shell_cmd, original_command=command)
            return

        self.nav.status_message = f"Unknown command: {command}"
        self._flash()
        self.nav.command_mode = False
        self.nav.need_redraw = True
        self.command_cwd = None
        if hasattr(self.nav, "command_history_index"):
            self.nav.command_history_index = None

    def _run_shell_command(self, shell_cmd: str, *, original_command: str) -> None:
        cwd_candidate = self.command_cwd or self.nav.dir_manager.current_path
        cwd = os.path.realpath(cwd_candidate)
        if not os.path.isdir(cwd):
            cwd = self.nav.dir_manager.current_path

        return_code = None
        stdout_text = ""
        stderr_text = ""
        error_message = ""

        try:
            result = subprocess.run(
                shell_cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return_code = result.returncode
            stdout_text = result.stdout or ""
            stderr_text = result.stderr or ""
        except Exception as exc:  # pragma: no cover
            error_message = str(exc)

        lines: list[str] = []

        if stdout_text:
            lines.extend(stdout_text.splitlines())
            if stdout_text.endswith("\n"):
                lines.append("")

        if stderr_text:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append("[stderr]")
            lines.extend(stderr_text.splitlines())
            if stderr_text.endswith("\n"):
                lines.append("")

        message = ""
        should_flash = False
        notify_dirs = False

        if return_code is None:
            message = f"! {shell_cmd} failed: {error_message or 'unknown error'}"
            if not lines:
                lines = [error_message or "(no output)"]
            should_flash = True
        else:
            message = f"! {shell_cmd} (exit {return_code})"
            if return_code == 0:
                notify_dirs = True
            else:
                should_flash = True
            if not lines:
                lines = ["(no output)"]

        self.nav.command_popup_lines = lines
        self.nav.command_popup_header = message
        self.nav.command_popup_scroll = 0
        self.nav.command_popup_view_rows = 0
        self.nav.command_popup_visible = True

        if notify_dirs and hasattr(self.nav, "notify_directory_changed"):
            self.nav.notify_directory_changed()

        if should_flash:
            self._flash()

        if return_code == 0 and original_command:
            history = getattr(self.nav, "command_history", None)
            if history is not None:
                history.append(original_command)
                self.nav.command_history_index = None

        self.nav.command_mode = False
        self.nav.status_message = message
        self.nav.need_redraw = True
        self.command_cwd = None
        if hasattr(self.nav, "command_history_index"):
            self.nav.command_history_index = None

    def _command_history_step(self, delta: int) -> bool:
        history = getattr(self.nav, "command_history", None)
        if history is None:
            return False

        length = len(history)
        if length == 0:
            self._flash()
            return False

        index = getattr(self.nav, "command_history_index", None)
        if index is None:
            index = length

        new_index = index + delta

        if new_index < 0:
            self._flash()
            return False

        if new_index > length:
            self._flash()
            return False

        self.nav.command_history_index = new_index
        if new_index == length:
            self.nav.command_buffer = ""
        else:
            self.nav.command_buffer = history[new_index]
        return True

    def _open_user_config(self) -> None:
        config_path = config.get_config_path()
        if not config_path:
            self.nav.status_message = "Config path unavailable"
            self._flash()
            self.nav.need_redraw = True
            return

        target_path = os.path.realpath(os.path.expanduser(config_path))

        try:
            directory = os.path.dirname(target_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
        except Exception:
            self.nav.status_message = "Failed to prepare config directory"
            self._flash()
            self.nav.need_redraw = True
            return

        opened = False
        try:
            opened = self.nav.file_actions._open_with_vim(target_path)
        except Exception:
            opened = False

        pretty = self.nav.dir_manager.pretty_path(target_path)
        if opened:
            try:
                refreshed = config.load_user_config()
                config.USER_CONFIG = refreshed
                self.nav.config = refreshed
                message = f"Config reloaded from {pretty}"
                if refreshed.warnings:
                    message += f" (warn: {refreshed.warnings[0]})"
                self.nav.status_message = message
            except Exception:
                self.nav.status_message = (
                    f"Opened {pretty} in vim (reload failed)"
                )
                self._flash()
        else:
            self.nav.status_message = "Unable to launch vim for config"
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
        if key in (curses.KEY_SR, 11):  # Ctrl+K / Shift+Up
            jump = max(1, max_visible // 2)
            self.nav.help_scroll = max(0, self.nav.help_scroll - jump)
            self.nav.need_redraw = True
            return True
        if is_ctrl_j(key):  # Ctrl+J / Shift+Down
            jump = max(1, max_visible // 2)
            self.nav.help_scroll = min(max_scroll, self.nav.help_scroll + jump)
            self.nav.need_redraw = True
            return True

        return False

    def _handle_command_popup_key(self, key) -> bool:
        lines = getattr(self.nav, "command_popup_lines", []) or []
        visible = max(1, getattr(self.nav, "command_popup_view_rows", 1))
        max_scroll = max(0, len(lines) - visible)

        if key in (27, ord("q")):
            self._close_command_popup()
            return True

        if key in (ord("j"), curses.KEY_DOWN):
            new_scroll = min(max_scroll, self.nav.command_popup_scroll + 1)
            if new_scroll != self.nav.command_popup_scroll:
                self.nav.command_popup_scroll = new_scroll
                self.nav.need_redraw = True
            return True

        if key in (ord("k"), curses.KEY_UP):
            new_scroll = max(0, self.nav.command_popup_scroll - 1)
            if new_scroll != self.nav.command_popup_scroll:
                self.nav.command_popup_scroll = new_scroll
                self.nav.need_redraw = True
            return True

        if key in (curses.KEY_NPAGE,):
            new_scroll = min(max_scroll, self.nav.command_popup_scroll + visible)
            if new_scroll != self.nav.command_popup_scroll:
                self.nav.command_popup_scroll = new_scroll
                self.nav.need_redraw = True
            return True

        if key in (curses.KEY_PPAGE,):
            new_scroll = max(0, self.nav.command_popup_scroll - visible)
            if new_scroll != self.nav.command_popup_scroll:
                self.nav.command_popup_scroll = new_scroll
                self.nav.need_redraw = True
            return True

        return True

    def _close_command_popup(self) -> None:
        self.nav.command_popup_visible = False
        self.nav.command_popup_lines = []
        self.nav.command_popup_header = ""
        self.nav.command_popup_scroll = 0
        self.nav.command_popup_view_rows = 0
        self.nav.status_message = ""
        self.nav.need_redraw = True

    def _key_to_char(self, key):
        if 32 <= key <= 126:
            return chr(key)
        return None

    def handle_key(self, stdscr, key):
        if getattr(self.nav, "command_popup_visible", False):
            if self._handle_command_popup_key(key):
                return False

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
            if is_enter(key):
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
                return False

            self._reset_comma()
            self.pending_operator = None
            self.in_filter_mode = False
            self.nav.dir_manager.filter_pattern = ""

            current_path = self.nav.dir_manager.current_path
            self.nav.collapse_expansions_under(current_path)
            self.nav.status_message = (
                f"Collapsed {os.path.basename(current_path) or current_path}"
            )

            return False

        if key == ord("~"):
            self.nav.exit_visual_mode()
            self._reset_comma()
            self.pending_operator = None
            self.in_filter_mode = False
            self.nav.dir_manager.filter_pattern = ""
            self.nav.reset_to_home()
            self.nav.status_message = "Returned to ~"
            self.nav.need_redraw = True
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
                key,
                total,
                selection,
                context_path,
                scope_range,
                target_dir,
                display_items,
            ):
                return False

        if is_enter(key):
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
            if total > 0 and selected_path:
                full_path = selected_path
                if full_path in self.nav.marked_items:
                    self.nav.marked_items.remove(full_path)
                else:
                    self.nav.marked_items.add(full_path)
                # Auto-advance after marking
                self.nav.browser_selected = (self.nav.browser_selected + 1) % total
                self._record_repeat_sequence([ord("m")])
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
        if key == ord("."):
            if self.is_repeating:
                return False
            if not self.last_repeat_sequence:
                self.nav.status_message = "Nothing to repeat"
                self._flash()
                self.nav.need_redraw = True
                return False

            sequence = list(self.last_repeat_sequence)
            self.is_repeating = True
            result = False
            try:
                for seq_key in sequence:
                    result = self.handle_key(None, seq_key)
                    if result:
                        break
            finally:
                self.is_repeating = False
            return result

        if key == ord("?"):
            self.nav.show_help = True
            self.nav.help_scroll = 0
            return False

        if key == ord("q"):
            self.nav.exit_visual_mode()
            self.nav.status_message = "Quit"
            self.nav.need_redraw = True
            return True

        if key == ord("t"):
            self.nav.open_terminal()
            return False

        # === Multi-mark operations ===
        if self.nav.marked_items:
            if key == ord("p"):
                self._copy_marked(target_dir)
                self._record_repeat_sequence([ord("p")])
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
                self._record_repeat_sequence([ord("p")])
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
        elif key in (curses.KEY_SR, 11):  # Ctrl+K / Shift+Up
            self._jump_selection(total, "up")
        elif is_ctrl_j(key):  # Ctrl+J / Shift+Down
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
