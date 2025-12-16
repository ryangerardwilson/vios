import os
import glob


def is_text_file(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read(1024)
        return True
    except Exception:
        return False


def pretty_path(path: str) -> str:
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):] if path != home else "~"
    return path


class DirectoryManager:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)

    def change_directory(self, new_path: str):
        new_path = os.path.realpath(os.path.expanduser(new_path))
        if os.path.isdir(new_path):
            self.current_path = new_path
            return True
        return False

    def get_items(self):
        """Return list of (name, is_dir) for visible items, sorted."""
        try:
            items = os.listdir(self.current_path)
        except PermissionError:
            return []

        items_with_info = []
        for item in items:
            if item.startswith("."):
                continue
            full_path = os.path.join(self.current_path, item)
            is_dir = os.path.isdir(full_path)
            items_with_info.append((item, is_dir))

        items_with_info.sort(key=lambda x: (not x[1], x[0].lower()))
        return items_with_info

    def get_filtered_items(self):
        # No search term anymore — just return all visible items
        return self.get_items()
