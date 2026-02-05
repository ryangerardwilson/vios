import os
import threading
from types import SimpleNamespace

import file_actions
from file_actions import FileActionService


class DummyNavigator:
    def __init__(self, base_path: str, python_cmd, shell_cmd):
        self.dir_manager = SimpleNamespace(current_path=base_path)
        self.config = SimpleNamespace(
            get_executor=lambda name: python_cmd if name == "python" else shell_cmd if name == "shell" else []
        )
        self.status_message = ""
        self.need_redraw = False
        self.command_popup_visible = False
        self.command_popup_lines: list[str] = []
        self.command_popup_header = ""
        self.command_popup_scroll = 0
        self.command_popup_view_rows = 0
        self.command_popup_lock = threading.Lock()
        self.active_execution_job = None

    def open_command_popup(self, header: str, lines: list[str]):
        with self.command_popup_lock:
            self.command_popup_header = header
            self.command_popup_lines = list(lines)
            self.command_popup_scroll = 0
            self.command_popup_view_rows = 0
            self.command_popup_visible = True
        self.status_message = header
        self.need_redraw = True

    def append_command_popup_lines(self, new_lines: list[str]):
        with self.command_popup_lock:
            self.command_popup_lines.extend(new_lines)
        self.need_redraw = True

    def update_command_popup_header(self, header: str):
        with self.command_popup_lock:
            self.command_popup_header = header
        self.status_message = header
        self.need_redraw = True

    def set_active_execution_job(self, job):
        self.active_execution_job = job

    def clear_active_execution_job(self):
        self.active_execution_job = None


class DummyPopen:
    def __init__(self, command, cwd=None, stdout=None, stderr=None, stdin=None, text=None, encoding=None, errors=None, bufsize=None):
        self.args = command
        self.cwd = cwd
        self.stdout = None
        self.stderr = None
        self._returncode = 0

    def poll(self):
        return self._returncode

    def wait(self, timeout=None):
        return self._returncode

    def terminate(self):
        self._returncode = -15

    def kill(self):
        self._returncode = -9


def test_resolve_execution_command_python(tmp_path):
    navigator = DummyNavigator(str(tmp_path), ["python"], ["/bin/bash", "-lc"])
    service = FileActionService(navigator)
    target = tmp_path / "script.py"
    target.write_text("print('hi')", encoding="utf-8")

    command, mode, error = service._resolve_execution_command(str(target))

    assert error is None
    assert mode == "python"
    assert command is not None
    assert command == ["python", str(target)]


def test_resolve_execution_command_shell(tmp_path):
    navigator = DummyNavigator(str(tmp_path), ["python"], ["/bin/bash", "-lc"])
    service = FileActionService(navigator)
    script = tmp_path / "run_me"
    script.write_text("echo hi", encoding="utf-8")
    script.chmod(0o755)

    command, mode, error = service._resolve_execution_command(str(script))

    assert error is None
    assert mode == "shell"
    assert command is not None
    assert command[-1] == "./run_me"
    assert command[:-1] == ["/bin/bash", "-lc"]


def test_run_execution_launches_job(monkeypatch, tmp_path):
    navigator = DummyNavigator(str(tmp_path), ["python"], ["/bin/bash", "-lc"])
    service = FileActionService(navigator)

    target = tmp_path / "demo.py"
    target.write_text("print('demo')", encoding="utf-8")

    collected: dict[str, list[str]] = {}
    seen_job: dict[str, file_actions.ExecutionJob] = {}

    def fake_monitor(self, job):
        seen_job["job"] = job
        collected["command"] = list(job.command)
        job.mark_finished(0)
        self.nav.append_command_popup_lines(["done"])
        self.nav.update_command_popup_header(f"Completed (exit 0): {job.display}")
        self.nav.clear_active_execution_job()

    monkeypatch.setattr(file_actions.FileActionService, "_monitor_execution_job", fake_monitor)
    monkeypatch.setattr(file_actions.subprocess, "Popen", DummyPopen)

    launched = service.run_execution(str(target))

    assert launched is True
    job = seen_job.get("job")
    assert job is not None
    if job.thread is not None:
        job.thread.join(timeout=1)

    assert "command" in collected
    command_list = collected["command"]
    assert command_list == ["python", str(target)]
    with navigator.command_popup_lock:
        assert "done" in navigator.command_popup_lines
        assert navigator.command_popup_visible is True
    assert "Completed" in navigator.status_message
