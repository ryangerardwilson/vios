# ~/Apps/vios/core_navigator.py
import subprocess
import os
from typing import Set, List, Optional

from directory_manager import DirectoryManager
from clipboard_manager import ClipboardManager
from ui_renderer import UIRenderer
from input_handler import InputHandler
from constants import Constants
from file_actions import FileActionService
from config import USER_CONFIG


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()

        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)
        self.file_actions = FileActionService(self)

        self.show_help = False
        self.help_scroll = 0
        self.browser_selected = 0
        self.list_offset = 0
        self.need_redraw = True
        self.config = USER_CONFIG
        self.layout_mode = "matrix" if self.config.matrix_mode else "list"

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

        self.visual_mode = False
        self.visual_anchor_index: Optional[int] = None
        self.visual_active_index: Optional[int] = None
        self.matrix_state = None
        self.matrix_return_map: dict[str, int] = {}

    def open_file(self, filepath: str):
        self.file_actions.open_file(filepath)

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
        self.file_actions.create_new_file()

    def open_terminal(self):
        self.file_actions.open_terminal()

    def create_new_file_no_open(self, base_path: Optional[str] = None):
        self.file_actions.create_new_file_no_open(base_path)

    def create_new_directory(self, base_path: Optional[str] = None):
        self.file_actions.create_new_directory(base_path)

    def rename_selected(self):
        self.file_actions.rename_selected()

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

    def notify_directory_changed(self, *paths: Optional[str]):
        real_current = os.path.realpath(self.dir_manager.current_path)
        targets = []
        for path in paths:
            if path:
                targets.append(os.path.realpath(path))
        if not targets:
            targets.append(real_current)

        current_changed = False
        for target in targets:
            self.dir_manager.refresh_cache(target)
            if target == real_current:
                current_changed = True

        if current_changed:
            self.reset_matrix_state()

        self.need_redraw = True

        if current_changed:
            items = self.build_display_items()
            total = len(items)
            if total == 0:
                self.browser_selected = 0
            else:
                self.browser_selected = max(0, min(self.browser_selected, total - 1))

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
        self.exit_visual_mode()
        self.dir_manager.current_path = new_path
        self.browser_selected = 0
        self.list_offset = 0
        self.need_redraw = True
        if self.layout_mode == "matrix":
            self.restore_matrix_position(new_path)
        self.reset_matrix_state()
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

    def enter_matrix_mode(self):
        if self.layout_mode == "matrix":
            return
        self.layout_mode = "matrix"
        self.reset_matrix_state()
        self.matrix_return_map.clear()
        self.status_message = "Matrix view activated"
        self.need_redraw = True

    def enter_list_mode(self):
        if self.layout_mode == "list":
            return
        self.layout_mode = "list"
        self.reset_matrix_state()
        self.matrix_return_map.clear()
        self.status_message = "List view restored"
        self.need_redraw = True

    def toggle_layout_mode(self):
        if self.layout_mode == "list":
            self.enter_matrix_mode()
        else:
            self.enter_list_mode()

    def reset_matrix_state(self):
        self.matrix_state = None

    def remember_matrix_position(self):
        current = os.path.realpath(self.dir_manager.current_path)
        self.matrix_return_map[current] = self.browser_selected

    def discard_matrix_position(self, path: str):
        real = os.path.realpath(path)
        self.matrix_return_map.pop(real, None)

    def restore_matrix_position(self, new_path: str):
        real_path = os.path.realpath(new_path)
        stored = self.matrix_return_map.pop(real_path, None)
        if stored is not None:
            items = self.build_display_items()
            if items:
                self.browser_selected = max(0, min(stored, len(items) - 1))
            else:
                self.browser_selected = 0

    def enter_visual_mode(self, index: int):
        items = self.build_display_items()
        if not items:
            return
        total = len(items)
        if index < 0 or index >= total:
            index = max(0, min(index, total - 1))
        self.visual_mode = True
        self.visual_anchor_index = index
        self.visual_active_index = index
        self._apply_visual_marks()
        self.need_redraw = True

    def reanchor_visual_mode(self, index: int):
        self.enter_visual_mode(index)

    def exit_visual_mode(self, *, clear_message: bool = True):
        if not self.visual_mode:
            return
        self.visual_mode = False
        self.visual_anchor_index = None
        self.visual_active_index = None
        if clear_message and self.status_message.startswith("-- VISUAL"):
            self.status_message = ""
        self.need_redraw = True

    def update_visual_active(self, index: int):
        if not self.visual_mode:
            return
        if self.visual_anchor_index is None:
            self.visual_anchor_index = index
        self.visual_active_index = index
        self._apply_visual_marks()
        self.need_redraw = True

    def get_visual_indices(self, total: int) -> list[int]:
        if (
            not self.visual_mode
            or self.visual_anchor_index is None
            or self.visual_active_index is None
        ):
            return []
        if total <= 0:
            self.exit_visual_mode()
            return []
        anchor = self.visual_anchor_index
        active = self.visual_active_index
        if anchor < 0 or active < 0 or anchor >= total or active >= total:
            self.exit_visual_mode()
            return []
        start = min(anchor, active)
        end = max(anchor, active)
        return list(range(start, end + 1))

    def _apply_visual_marks(self):
        if not self.visual_mode:
            return
        items = self.build_display_items()
        total = len(items)
        indices = self.get_visual_indices(total)
        if not indices:
            return
        added = False
        for idx in indices:
            if 0 <= idx < total:
                path = items[idx][2]
                if path not in self.marked_items:
                    self.marked_items.add(path)
                    added = True
        if added:
            self.need_redraw = True
