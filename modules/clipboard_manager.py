# ~/Apps/vios/modules/clipboard_manager.py
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass
class ClipboardEntry:
    temp_path: str
    original_name: str
    is_dir: bool


class ClipboardManager:
    def __init__(self):
        self.temp_yank_dir = os.path.join(tempfile.gettempdir(), "vios_yank")
        os.makedirs(self.temp_yank_dir, exist_ok=True)
        self.batch_dir = None
        self.entries: List[ClipboardEntry] = []

    def cleanup(self):
        if self.batch_dir and os.path.exists(self.batch_dir):
            try:
                shutil.rmtree(self.batch_dir)
            except Exception:
                pass
        self.batch_dir = None
        self.entries = []

    def _copy_source(self, src_path: str, dest_path: str, is_dir: bool):
        if is_dir:
            shutil.copytree(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)

    def _remove_source(self, src_path: str, is_dir: bool):
        if is_dir:
            shutil.rmtree(src_path)
        else:
            os.remove(src_path)

    def yank_multiple(self, items: Sequence[Tuple[str, str, bool]], cut: bool = False):
        """Copy a sequence of (path, name, is_dir) items into the clipboard."""
        self.cleanup()
        if not items:
            return

        batch_id = str(uuid.uuid4())[:8]
        prefix = "cut" if cut else "yank"
        self.batch_dir = os.path.join(self.temp_yank_dir, f"{prefix}_{batch_id}")
        os.makedirs(self.batch_dir, exist_ok=True)
        batch_dir = self.batch_dir

        new_entries: List[ClipboardEntry] = []

        for idx, (src_path, name, is_dir) in enumerate(items):
            temp_name = f"{idx}_{name}"
            temp_dest = os.path.join(batch_dir, temp_name)
            try:
                self._copy_source(src_path, temp_dest, is_dir)
                new_entries.append(ClipboardEntry(temp_dest, name, is_dir))
                if cut:
                    self._remove_source(src_path, is_dir)
            except Exception:
                # Best effort cleanup for partially copied batch
                for entry in new_entries:
                    if os.path.isdir(entry.temp_path):
                        shutil.rmtree(entry.temp_path, ignore_errors=True)
                    else:
                        try:
                            os.remove(entry.temp_path)
                        except Exception:
                            pass
                self.cleanup()
                raise

        self.entries = new_entries

    def yank(self, src_path: str, name: str, is_dir: bool, cut: bool = False):
        self.yank_multiple([(src_path, name, is_dir)], cut=cut)

    def paste(self, dest_dir: str, new_name: str | None = None):
        if not self.entries:
            raise FileNotFoundError("Nothing to paste")

        multiple_entries = len(self.entries) > 1

        for entry in self.entries:
            dest_name = entry.original_name
            if new_name and not multiple_entries:
                dest_name = new_name

            dest_path = os.path.join(dest_dir, dest_name)

            if os.path.exists(dest_path):
                if os.path.isdir(dest_path):
                    shutil.rmtree(dest_path)
                else:
                    os.remove(dest_path)

            try:
                self._copy_source(entry.temp_path, dest_path, entry.is_dir)
            except Exception:
                raise

    @property
    def has_entries(self) -> bool:
        return bool(self.entries)

    def get_status_text(self) -> str:
        if not self.entries:
            return ""
        if len(self.entries) == 1:
            entry = self.entries[0]
            suffix = "/" if entry.is_dir else ""
            return f"{entry.original_name}{suffix}"
        return f"{len(self.entries)} items"

    @property
    def entry_count(self) -> int:
        return len(self.entries)
