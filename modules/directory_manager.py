# ~/Apps/vios/modules/directory_manager.py
import os
import fnmatch


class DirectoryManager:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.filter_pattern = ""
        self.show_hidden = False  # Default: hide dotfiles/dotdirs
        self.sort_mode = "alpha"
        self.sort_map = {}

        # Keep home_path for pretty_path only
        self.home_path = os.path.realpath(os.path.expanduser("~"))

    @classmethod
    def pretty_path(cls, path: str) -> str:
        """Convert absolute path to pretty ~ form if it's under home."""
        home = os.path.expanduser("~")
        real_home = os.path.realpath(home)
        real_path = os.path.realpath(path)

        if real_path.startswith(real_home):
            if real_path == real_home:
                return "~"
            return "~" + real_path[len(real_home) :]
        return path

    def toggle_hidden(self):
        """Toggle visibility of hidden files/directories"""
        self.show_hidden = not self.show_hidden

    def get_hidden_status_text(self) -> str:
        """Return text for status bar when hidden files are visible"""
        return " .dot" if self.show_hidden else ""

    def get_items(self):
        return self.list_directory(self.current_path)

    def list_directory(self, target_path: str):
        try:
            raw_items = os.listdir(target_path)
        except (PermissionError, FileNotFoundError):
            return []

        visible_items = []

        real_target = os.path.realpath(target_path)
        sort_mode = self.sort_map.get(real_target, self.sort_mode)

        for item in raw_items:
            if item in {".", ".."}:
                continue

            full_path = os.path.join(target_path, item)
            if not os.path.exists(full_path):
                continue

            is_dir = os.path.isdir(full_path)
            is_hidden = item.startswith(".")

            if is_hidden and not self.show_hidden:
                continue

            visible_items.append((item, is_dir))

        if sort_mode == "alpha":
            visible_items.sort(key=self._alpha_sort_key)
        else:
            reverse = sort_mode == "mtime_desc"
            visible_items.sort(
                key=self._mtime_sort_key_factory(target_path), reverse=reverse
            )

        return visible_items

    def _normalize_pattern(self, pattern: str) -> str:
        pattern = pattern.strip()
        if not pattern or pattern == "/":
            return ""
        if any(c in pattern for c in "*?[]"):
            return pattern
        return pattern + "*"

    def get_filtered_items(self):
        all_items = self.get_items()

        if not self.filter_pattern:
            return all_items

        # Remove leading '/' used for visual feedback
        search_pattern = (
            self.filter_pattern[1:]
            if self.filter_pattern.startswith("/")
            else self.filter_pattern
        )

        if not search_pattern:
            return all_items

        normalized = self._normalize_pattern(search_pattern)
        pattern_lower = normalized.lower()

        return [
            item
            for item in all_items
            if fnmatch.fnmatch(item[0].lower(), pattern_lower)
        ]

    def set_sort_mode(self, mode: str):
        if mode in {"alpha", "mtime_asc", "mtime_desc"}:
            self.sort_mode = mode

    def set_sort_mode_for_path(self, path: str, mode: str):
        if mode not in {"alpha", "mtime_asc", "mtime_desc"}:
            return
        if not path:
            return
        real_path = os.path.realpath(path)
        self.sort_map[real_path] = mode

    def _alpha_sort_key(self, entry):
        name, is_dir = entry
        hidden = name.startswith(".")
        if hidden:
            group = 2 if is_dir else 3
        else:
            group = 0 if is_dir else 1
        return (group, name.lower())

    def _mtime_sort_key_factory(self, base_path: str):
        def sorter(entry):
            name, _ = entry
            full_path = os.path.join(base_path, name)
            try:
                mtime = os.path.getmtime(full_path)
            except Exception:
                mtime = 0
            return (mtime, name.lower())

        return sorter
