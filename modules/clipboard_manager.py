# ~/Apps/vios/modules/clipboard_manager.py
import os
import shutil
import tempfile
import uuid


class ClipboardManager:
    def __init__(self):
        self.temp_yank_dir = os.path.join(tempfile.gettempdir(), "vios_yank")
        os.makedirs(self.temp_yank_dir, exist_ok=True)
        self.yanked_temp_path = None
        self.yanked_original_name = None
        self.yanked_is_dir = False

    def cleanup(self):
        if self.yanked_temp_path and os.path.exists(self.yanked_temp_path):
            try:
                if os.path.isdir(self.yanked_temp_path):
                    shutil.rmtree(self.yanked_temp_path)
                else:
                    os.remove(self.yanked_temp_path)
            except Exception:
                pass
        self.yanked_temp_path = None
        self.yanked_original_name = None
        self.yanked_is_dir = False

    def yank(self, src_path: str, name: str, is_dir: bool, cut: bool = False):
        """Copy src_path to temp dir. If cut=True, delete original after copy."""
        self.cleanup()
        unique_id = str(uuid.uuid4())[:8]
        prefix = "cut" if cut else "yank"
        temp_dest = os.path.join(self.temp_yank_dir, f"{prefix}_{unique_id}_{name}")

        try:
            if is_dir:
                shutil.copytree(src_path, temp_dest)
            else:
                shutil.copy2(src_path, temp_dest)
            self.yanked_temp_path = temp_dest
            self.yanked_original_name = name
            self.yanked_is_dir = is_dir

            if cut:
                if is_dir:
                    shutil.rmtree(src_path)
                else:
                    os.remove(src_path)
        except Exception:
            self.cleanup()
            raise

    def paste(self, dest_dir: str, new_name: str | None = None):
        if not self.yanked_temp_path or not os.path.exists(self.yanked_temp_path):
            raise FileNotFoundError("Nothing to paste")

        dest_name = new_name or self.yanked_original_name
        dest_path = os.path.join(dest_dir, dest_name)

        # Overwrite: Remove existing destination if it exists
        if os.path.exists(dest_path):
            if os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            else:
                os.remove(dest_path)

        try:
            if self.yanked_is_dir:
                shutil.copytree(self.yanked_temp_path, dest_path)
            else:
                shutil.copy2(self.yanked_temp_path, dest_path)
        except Exception:
            raise
