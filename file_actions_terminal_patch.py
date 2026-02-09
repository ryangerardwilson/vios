import curses
import os
import shlex
import shutil
import subprocess
from typing import List, Optional


def _open_terminal_impl(
    service,
    base_path: Optional[str] = None,
    command: Optional[List[str]] = None,
) -> bool:
    cwd = service._resolve_base_directory(base_path)
    commands = []
    term_env = os.environ.get("TERMINAL")
    if term_env:
        commands.append(shlex.split(term_env))
    commands.extend(
        [
            [cmd]
            for cmd in (
                "alacritty",
                "foot",
                "kitty",
                "wezterm",
                "gnome-terminal",
                "xterm",
            )
        ]
    )

    for cmd in commands:
        if not cmd:
            continue
        if shutil.which(cmd[0]) is None:
            continue
        launch_cmd = list(cmd)
        if command:
            if any("{cmd}" in token for token in launch_cmd):
                launch_cmd = [
                    token.replace("{cmd}", " ".join(command))
                    for token in launch_cmd
                ]
            else:
                launch_cmd.extend(["-e"] + command)
        try:
            subprocess.Popen(
                launch_cmd,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            service.nav.status_message = f"Opened terminal: {launch_cmd[0]}"
            return True
        except Exception:
            continue

    service.nav.status_message = "No terminal found"
    try:
        curses.flash()
    except curses.error:
        pass
    return False


def _patch_file_action_service():
    from file_actions import FileActionService

    def open_terminal(
        self,
        base_path: Optional[str] = None,
        command: Optional[List[str]] = None,
    ) -> bool:
        return _open_terminal_impl(self, base_path, command)

    FileActionService.open_terminal = open_terminal


_patch_file_action_service()
