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

    # Whitelist of hidden paths (relative to ~) that should be visible
    ALLOWED_HIDDEN_PATHS = {
        # Top-level dotfiles
        ".gitignore",
        ".XCompose",
        ".bashrc",
        ".tmux.conf",
        ".vimrc",
        ".packages",
        ".Xresources",
        ".sqlfluff",

        # .ssh and contents
        ".ssh",
        ".ssh/config",
        ".ssh/keys",

        # .config and its relevant substructure
        ".config",
        ".config/crontab",
        ".config/hypr",
        ".config/waybar",
        ".config/waybar/style.css",
        ".config/zathura",
        ".config/zathura/zathurarc",
        ".config/vifm",
        ".config/vifm/vifmrc",
        ".config/vifm/colors",
        ".config/vifm/colors/Revelations.vifm",
        ".config/alacritty",
        ".config/alacritty/alacritty.toml",

        # .local and relevant subpath
        ".local",
        ".local/share",
        ".local/share/applications",
        ".local/share/applications/chromium.desktop",
    }

    def change_directory(self, new_path: str):
        new_path = os.path.realpath(os.path.expanduser(new_path))
        if os.path.isdir(new_path):
            self.current_path = new_path
            self.filter_pattern = ""  # Always clear on explicit cd
            return True
        return False

    def _is_allowed_hidden(self, item: str) -> bool:
        """Check if a hidden item should be shown based on whitelist (relative to ~)."""
        if not item.startswith("."):
            return True

        full_path = os.path.join(self.current_path, item)
        try:
            rel_path = os.path.relpath(full_path, os.path.expanduser("~"))
        except ValueError:
            return False

        return rel_path in self.ALLOWED_HIDDEN_PATHS

    def get_items(self):
        try:
            items = os.listdir(self.current_path)
        except PermissionError:
            return []

        visible_items = []

        for item in items:
            # Always include parent directory ".." for navigation
            if item == "..":
                full_path = os.path.join(self.current_path, item)
                visible_items.append((item, os.path.isdir(full_path)))
                continue

            # Skip hidden items unless explicitly whitelisted
            if item.startswith(".") and not self._is_allowed_hidden(item):
                continue

            full_path = os.path.join(self.current_path, item)
            is_dir = os.path.isdir(full_path)
            visible_items.append((item, is_dir))

        # Custom sort:
        # 1. Non-hidden directories (alphabetical)
        # 2. Non-hidden files (alphabetical)
        # 3. Hidden items (both files and dirs, alphabetical)
        def sort_key(entry):
            name, is_dir = entry
            if name.startswith("."):
                # Hidden items go last
                group = 2
            elif is_dir:
                # Non-hidden dirs first
                group = 0
            else:
                # Non-hidden files in the middle
                group = 1
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
        raw_pattern = self.filter_pattern
        if not raw_pattern:
            return all_items
        pattern = self._normalize_pattern(raw_pattern).lower()
        return [
            item for item in all_items
            if fnmatch.fnmatch(item[0].lower(), pattern)
        ]
