# ~/Apps/vios/modules/directory_manager.py
import os
import fnmatch


class DirectoryManager:
    ALLOWED_TOP_LEVEL_HIDDEN = {
        ".gitignore",
        ".gitinclude",
        ".XCompose",
        ".bashrc",
        ".tmux.conf",
        ".vimrc",
        ".packages",
        ".Xresources",
        ".sqlfluff",
        ".ssh",
        ".local",
        ".config",
    }

    ALLOWED_IN_CONFIG = {
        "alacritty",
        "rtutor",
        "worship",
        "crontab",
        "hypr",
        "waybar",
        "zathura",
        # Add more as needed
    }

    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.filter_pattern = ""

        self.home_path = os.path.realpath(os.path.expanduser("~"))
        self.config_path = os.path.realpath(os.path.join(self.home_path, ".config"))

    @classmethod
    def pretty_path(cls, path: str) -> str:
        home = os.path.expanduser("~")
        real_home = os.path.realpath(home)
        real_path = os.path.realpath(path)

        if real_path.startswith(real_home):
            if real_path == real_home:
                return "~"
            return "~" + real_path[len(real_home):]
        return path

    def _is_home_dir(self) -> bool:
        return self.current_path == self.home_path

    def _is_config_dir(self) -> bool:
        return self.current_path == self.config_path

    def _is_inside_config(self) -> bool:
        return self.current_path.startswith(self.config_path + os.sep)

    def get_items(self):
        try:
            raw_items = os.listdir(self.current_path)
        except PermissionError:
            return []

        visible_items = []

        is_home = self._is_home_dir()
        is_config = self._is_config_dir()

        for item in raw_items:
            if item in {".", ".."}:
                continue

            full_path = os.path.join(self.current_path, item)
            if not os.path.exists(full_path):
                continue

            is_dir = os.path.isdir(full_path)
            is_hidden = item.startswith(".")

            # Visibility rules
            if is_home:
                if is_hidden and item not in self.ALLOWED_TOP_LEVEL_HIDDEN:
                    continue
            elif is_config:
                if item not in self.ALLOWED_IN_CONFIG:
                    continue
            # Else: everywhere else (including inside ~/.config subdirs) → show everything

            visible_items.append((item, is_dir))

        # Custom sorting: 
        # 1. Non-hidden dirs
        # 2. Non-hidden files
        # 3. Hidden dirs
        # 4. Hidden files
        # All groups sorted alphabetically (case-insensitive)
        def sort_key(entry):
            name, is_dir = entry
            hidden = name.startswith(".")
            if hidden:
                group = 2 if is_dir else 3   # hidden dirs = 2, hidden files = 3
            else:
                group = 0 if is_dir else 1   # non-hidden dirs = 0, non-hidden files = 1
            return (group, name.lower())

        visible_items.sort(key=sort_key)

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

        search_pattern = self.filter_pattern[1:] if self.filter_pattern.startswith("/") else self.filter_pattern

        if not search_pattern:
            return all_items

        normalized = self._normalize_pattern(search_pattern)
        pattern_lower = normalized.lower()

        return [
            item for item in all_items
            if fnmatch.fnmatch(item[0].lower(), pattern_lower)
        ]
