# ~/Apps/vios/modules/directory_manager.py
import os
import fnmatch


def pretty_path(path: str) -> str:
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):] if path != home else "~"
    return path


class DirectoryManager:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.filter_pattern = ""  # Raw pattern as typed by user

    # Allowed top-level hidden items when in ~
    ALLOWED_TOP_LEVEL_HIDDEN = {
        ".gitignore",
        ".XCompose",
        ".bashrc",
        ".tmux.conf",
        ".vimrc",
        ".packages",
        ".Xresources",
        ".sqlfluff",
        ".ssh",
        ".local",
        ".config",  # Must keep to allow entering .config
    }

    # STRICT whitelist: ONLY these items are visible inside ~/.config
    ALLOWED_IN_CONFIG = {
        "alacritty",
        "crontab",
        "hypr",
        "waybar",
        "zathura",
        # Add more here if needed
    }

    def _is_home_dir(self) -> bool:
        return os.path.realpath(self.current_path) == os.path.realpath(os.path.expanduser("~"))

    def _is_config_dir(self) -> bool:
        return os.path.realpath(self.current_path) == os.path.realpath(os.path.expanduser("~/.config"))

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

            # Filtering logic
            if is_home:
                if item.startswith(".") and item not in self.ALLOWED_TOP_LEVEL_HIDDEN:
                    continue
            elif is_config:
                if item not in self.ALLOWED_IN_CONFIG:
                    continue
            else:
                # Outside home and .config: hide all hidden items
                if item.startswith("."):
                    continue

            visible_items.append((item, is_dir))

        # Custom sorting as requested:
        # 1. Non-hidden dirs
        # 2. Non-hidden files
        # 3. Hidden dirs
        # 4. Hidden files
        def sort_key(entry):
            name, is_dir = entry
            hidden = name.startswith(".")
            if hidden:
                group = 2 if is_dir else 3
            else:
                group = 0 if is_dir else 1
            return (group, name.lower())

        visible_items.sort(key=sort_key)

        return visible_items

    def _normalize_pattern(self, pattern: str) -> str:
        if not pattern:
            return ""
        if any(c in pattern for c in "*?[]"):
            return pattern
        return pattern + "*"

    def get_filtered_items(self):
        all_items = self.get_items()
        if not self.filter_pattern:
            return all_items
        pattern = self._normalize_pattern(self.filter_pattern).lower()
        return [
            item for item in all_items
            if fnmatch.fnmatch(item[0].lower(), pattern)
        ]
