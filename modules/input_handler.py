# ~/Apps/vios/modules/input_handler.py
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
        self.comma_timeout = 2.0
        self.comma_sequence = ""

        self.last_escape_time = 0.0
        self.escape_double_threshold = 0.4

    def _check_operator_timeout(self):
        if self.pending_operator and (time.time() - self.operator_timestamp > self.operator_timeout):
            self.pending_operator = None

    def _check_comma_timeout(self):
        if self.pending_comma and (time.time() - self.comma_timestamp > self.comma_timeout):
            self._reset_comma()

    def _clear_clipboard(self):
        self.nav.clipboard.cleanup()
        self.nav.status_message = "Clipboard cleared"
        self.nav.need_redraw = True

    def _leader_rename(self, selection):
        if not selection:
            curses.flash()
            return
        self.nav.rename_selected()

    def _leader_copy_path(self):
        self.nav.copy_current_path()

    def _leader_bookmark(self, context_path):
        target = context_path or self.nav.dir_manager.current_path
        self.nav.add_bookmark(target)

    def _handle_comma_command(self, key, total: int, selection, context_path, scope_range, target_dir) -> bool:
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
            "sma": lambda: self._set_sort_mode("mtime_asc", "Sort: Modified ↑", context_path),
            "smd": lambda: self._set_sort_mode("mtime_desc", "Sort: Modified ↓", context_path),
            "cl": self._clear_clipboard,
            "nf": lambda: self.nav.create_new_file_no_open(base_dir),
            "nd": lambda: self.nav.create_new_directory(base_dir),
            "rn": lambda: self._leader_rename(selection),
            "cp": self._leader_copy_path,
            "b": lambda: self._leader_bookmark(context_path),
        }

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

    def _jump_to_scope_edge(self, direction: str, scope_range, total: int):
        if scope_range:
            start, end = scope_range
            if start is not None and end is not None and 0 <= start < total and 0 <= end < total:
                target = start if direction == "up" else end
                self.nav.browser_selected = target
                return
        if direction == "up":
            self._set_browser_selected(0)
        else:
            self._set_browser_selected(total - 1 if total else 0)

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

    def _handle_help_scroll(self, key, stdscr):
        lines = len(self.nav.cheatsheet.strip().split('\n'))
        max_y = stdscr.getmaxyx()[0] if stdscr else 0
        max_visible = max(1, max_y - 1)
        max_scroll = max(0, lines - max_visible)

        if key == ord('?'):
            self.nav.show_help = False
            self.nav.help_scroll = 0
            self.nav.need_redraw = True
            return True

        if key in (curses.KEY_UP, ord('k')):
            self.nav.help_scroll = max(0, self.nav.help_scroll - 1)
            self.nav.need_redraw = True
            return True
        if key in (curses.KEY_DOWN, ord('j')):
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
                    self.nav.dir_manager.filter_pattern = self.nav.dir_manager.filter_pattern[:-1]
                else:
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
                return False

        if key == 27:  # Esc outside filter mode
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
                self.nav.status_message = f"Collapsed {os.path.basename(current_path) or current_path}"

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
            self.nav.browser_selected = max(0, min(self.nav.browser_selected, total - 1))
            selection = display_items[self.nav.browser_selected]
            selected_name, selected_is_dir, selected_path, _ = selection
            target_dir = self._determine_target_directory(selected_path, selected_is_dir)
            context_path, scope_range = self._compute_context_scope(display_items, self.nav.browser_selected)

        if key == ord(','):
            self.pending_comma = True
            self.comma_sequence = ""
            self.comma_timestamp = time.time()
            self.nav.leader_sequence = ","
            self.nav.need_redraw = True
            return False

        if self.pending_comma:
            if self._handle_comma_command(key, total, selection, context_path, scope_range, target_dir):
                return False

        if key == 8:  # Ctrl+H
            if self.nav.go_history_back():
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
                self.nav.status_message = "History back"
            else:
                curses.flash()
            return False

        if key == 12:  # Ctrl+L
            if self.nav.go_history_forward():
                self.in_filter_mode = False
                self.nav.dir_manager.filter_pattern = ""
                self.nav.status_message = "History forward"
            else:
                curses.flash()
            return False

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
        if key == ord('?'):
            self.nav.show_help = True
            self.nav.help_scroll = 0
            return False

        if key == ord('.'):
            self.nav.dir_manager.toggle_hidden()
            self.nav.expanded_nodes.clear()
            return False

        if key == ord('t'):
            self.nav.open_terminal()
            return False

        if key == ord('e') and total > 0 and selected_is_dir and selected_path:
            if selected_path in self.nav.expanded_nodes:
                self.nav.collapse_branch(selected_path)
                self.nav.status_message = f"Collapsed {selected_name}"
            else:
                self.nav.expanded_nodes.add(selected_path)
                self.nav.status_message = f"Expanded {selected_name}"
            self.nav.need_redraw = True
            return False

        # === Multi-mark operations ===
        if self.nav.marked_items:
            if key == ord('p'):
                self._copy_marked(target_dir)
                return False
            if key == ord('x'):
                self._delete_marked()
                return False

        # === Single-item paste (only when no marks) ===
        if key == ord('p') and self.nav.clipboard.has_entries:
            try:
                self.nav.clipboard.paste(target_dir)
                count = self.nav.clipboard.entry_count
                noun = "item" if count == 1 else "items"
                self.nav.status_message = f"Pasted {count} {noun}"
            except Exception:
                curses.flash()
            return False

        if key == ord('x') and total > 0 and selected_path:
            try:
                if selected_is_dir:
                    shutil.rmtree(selected_path)
                else:
                    os.remove(selected_path)
                self.nav.status_message = f"Deleted {selected_name}"
            except Exception:
                curses.flash()
            finally:
                self.nav.need_redraw = True
            return False

        # === yy / dd operators ===
        if self.pending_operator == 'd' and key == ord('d'):
            handled = False
            if self.nav.marked_items:
                handled = self._stage_marked_to_clipboard(cut=True)
            elif total > 0:
                try:
                    self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=True)
                    handled = True
                except Exception:
                    curses.flash()
            self.pending_operator = None
            if handled:
                return False

        if self.pending_operator == 'y' and key == ord('y'):
            handled = False
            if self.nav.marked_items:
                handled = self._stage_marked_to_clipboard(cut=False)
            elif total > 0:
                try:
                    self.nav.clipboard.yank(selected_path, selected_name, selected_is_dir, cut=False)
                    handled = True
                except Exception:
                    curses.flash()
            self.pending_operator = None
            if handled:
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
        elif key in (curses.KEY_SR, 11):  # Ctrl+K
            jump = max(1, total // 10) if total > 0 else 0
            self.nav.browser_selected = max(0, self.nav.browser_selected - jump)
        elif key in (curses.KEY_SF, 10):  # Ctrl+J
            jump = max(1, total // 10) if total > 0 else 0
            self.nav.browser_selected = min(total - 1, self.nav.browser_selected + jump) if total > 0 else 0
        elif key in (curses.KEY_LEFT, ord('h')):
            parent = os.path.dirname(self.nav.dir_manager.current_path)
            if parent != self.nav.dir_manager.current_path:
                if self.nav.change_directory(parent):
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
        elif key in (curses.KEY_RIGHT, ord('l'), 10, 13) and total > 0:
            if selected_is_dir:
                if self.nav.change_directory(selected_path):
                    self.in_filter_mode = False
                    self.nav.dir_manager.filter_pattern = ""
            else:
                self.nav.open_file(selected_path)

        return False

    # === Updated multi-mark operations using full paths ===
    def _copy_marked(self, dest_dir):
        self._move_or_copy_marked(dest_dir, copy_only=True)

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

    def _move_or_copy_marked(self, dest_dir, copy_only: bool):
        if not self.nav.marked_items:
            curses.flash()
            return

        if not dest_dir or not os.path.isdir(dest_dir):
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

    def _stage_marked_to_clipboard(self, cut: bool) -> bool:
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
            curses.flash()
            self.nav.marked_items.clear()
            return False

        try:
            self.nav.clipboard.yank_multiple(entries, cut=cut)
            self.nav.marked_items.clear()
            count = len(entries)
            action = "Cut" if cut else "Yanked"
            noun = "item" if count == 1 else "items"
            self.nav.status_message = f"{action} {count} {noun} to clipboard"
            return True
        except Exception:
            curses.flash()
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
