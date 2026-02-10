#!/usr/bin/env python3
"""Entry point for the `o` terminal navigator."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence
from urllib.parse import urlparse, unquote

from orchestrator import Orchestrator
from core_navigator import PickerOptions

try:
    from _version import __version__
except Exception:  # pragma: no cover - fallback when running from source
    __version__ = "0.0.0"

INSTALL_SH_URL = "https://raw.githubusercontent.com/ryangerardwilson/o/main/install.sh"

os.environ.setdefault("ESCDELAY", "25")


def _print_help() -> None:
    print(
        "o - Vim-inspired terminal file navigator\n\n"
        "Usage:\n"
        "  o            Launch the TUI\n"
        "  o -h         Show this help\n"
        "  o -v         Show installed version\n"
        "  o -u         Reinstall latest release if a newer version exists\n"
        "  o -r PATH    Reveal PATH (open folder, highlight item)\n\n"
        "Picker mode:\n"
        "  -p [dir]     Start picker mode (defaults to ~/)\n"
        "  -s [dir]     Save mode (pick output path)\n"
        "  -ld          Limit selection to directories\n"
        "  -lf [exts]   Limit selection to files, optional extensions\n"
        "  -m           Allow multi-select via marks\n"
        "  -se [ext]    Save extension (save mode only)"
    )


def _run_upgrade() -> int:
    try:
        curl = subprocess.Popen(
            ["curl", "-fsSL", INSTALL_SH_URL],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("Upgrade requires curl", file=sys.stderr)
        return 1

    try:
        bash = subprocess.Popen(["bash", "-s", "--", "-u"], stdin=curl.stdout)
        if curl.stdout is not None:
            curl.stdout.close()
    except FileNotFoundError:
        print("Upgrade requires bash", file=sys.stderr)
        curl.terminate()
        curl.wait()
        return 1

    bash_rc = bash.wait()
    curl_rc = curl.wait()

    if curl_rc != 0:
        stderr = (
            curl.stderr.read().decode("utf-8", errors="replace") if curl.stderr else ""
        )
        if stderr:
            sys.stderr.write(stderr)
        return curl_rc

    return bash_rc


def _parse_args(
    argv: Sequence[str],
) -> tuple[bool, bool, bool, PickerOptions | None, str | None, str | None]:
    show_help = False
    show_version = False
    do_upgrade = False
    picker_allowed: str | None = None
    picker_mode = False
    extensions: list[str] = []
    multi_select = False
    save_mode = False
    save_extensions_set = False
    start_path: str | None = None
    reveal_path: str | None = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"-h", "--help"}:
            show_help = True
        elif arg in {"-v", "--version", "-V"}:
            show_version = True
        elif arg in {"-u", "--upgrade"}:
            do_upgrade = True
        elif arg == "-p":
            picker_mode = True
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
                start_path = argv[i]
        elif arg == "-s":
            save_mode = True
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
                start_path = argv[i]
        elif arg == "-ld":
            if picker_allowed == "file":
                raise ValueError("-ld cannot be used with -lf")
            picker_allowed = "dir"
        elif arg == "-lf":
            if picker_allowed == "dir":
                raise ValueError("-lf cannot be used with -ld")
            picker_allowed = "file"
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
                raw = argv[i]
                parts = [
                    part.strip().lstrip(".")
                    for part in raw.replace(";", ",").split(",")
                ]
                extensions = sorted({part.lower() for part in parts if part})
        elif arg == "-se":
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                raise ValueError("-se requires an extension")
            i += 1
            raw = argv[i]
            parts = [
                part.strip().lstrip(".") for part in raw.replace(";", ",").split(",")
            ]
            extensions = sorted({part.lower() for part in parts if part})
            save_extensions_set = True
        elif arg == "-m":
            multi_select = True
        elif arg == "-r":
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                raise ValueError("-r requires a path")
            i += 1
            reveal_path = argv[i]
        else:
            raise ValueError(f"Unknown flag '{arg}'")
        i += 1

    if picker_mode and save_mode:
        raise ValueError("-p cannot be used with -s")

    if reveal_path and (picker_mode or save_mode):
        raise ValueError("-r cannot be used with -p or -s")

    if save_extensions_set and not save_mode:
        raise ValueError("-se requires -s")

    if any([picker_allowed, multi_select, start_path, extensions]):
        if not picker_mode and not save_mode:
            raise ValueError("Picker flags require -p or -s")

    if save_mode and picker_allowed == "dir":
        raise ValueError("-s cannot be used with -ld")

    if save_mode and multi_select:
        raise ValueError("-s cannot be used with -m")

    if picker_mode or save_mode:
        if not start_path:
            start_path = os.path.expanduser("~")
        if picker_allowed is None:
            picker_allowed = "any"

    if reveal_path:
        parsed = urlparse(reveal_path)
        if parsed.scheme == "file":
            reveal_path = unquote(parsed.path)
        reveal_path = os.path.realpath(os.path.expanduser(reveal_path))
        if os.path.isdir(reveal_path):
            start_path = reveal_path
        else:
            start_path = os.path.dirname(reveal_path) or os.path.expanduser("~")

    picker_options = None
    if picker_mode or save_mode:
        picker_options = PickerOptions(
            allowed_type=picker_allowed or "any",
            extensions=extensions,
            multi_select=multi_select,
            mode="save" if save_mode else "pick",
        )
    return show_help, show_version, do_upgrade, picker_options, start_path, reveal_path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    picker_options = None
    start_path = None
    reveal_path = None

    if args:
        try:
            show_help, show_version, do_upgrade, picker_options, start_path, reveal_path = (
                _parse_args(args)
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        if show_help:
            _print_help()
            return 0
        if show_version:
            print(__version__)
            return 0
        if do_upgrade:
            return _run_upgrade()

    start_dir = start_path or os.getcwd()
    orchestrator = Orchestrator(
        start_path=start_dir,
        picker_options=picker_options,
        reveal_path=reveal_path,
    )
    orchestrator.run()

    if picker_options is not None:
        navigator = orchestrator.navigator
        selection = getattr(navigator, "selection_result", []) if navigator else []
        if selection:
            payload = "\n".join(selection) + "\n"
            sys.stdout.write(payload)
            _write_picker_cache(selection)
            return 0
        return 1
    return 0


def _write_picker_cache(selection: list[str]) -> None:
    cache_root = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    cache_dir = os.path.join(cache_root, "o")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "picker-selection.txt")
        with open(cache_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(selection) + "\n")
    except OSError:
        return


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
