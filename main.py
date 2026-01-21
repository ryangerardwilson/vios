#!/usr/bin/env python3
"""Entry point for the `o` terminal navigator."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence

from orchestrator import Orchestrator

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
        "  o -u         Reinstall latest release if a newer version exists"
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
        stderr = curl.stderr.read().decode("utf-8", errors="replace") if curl.stderr else ""
        if stderr:
            sys.stderr.write(stderr)
        return curl_rc

    return bash_rc


def _parse_args(argv: Sequence[str]) -> tuple[bool, bool, bool]:
    show_help = False
    show_version = False
    do_upgrade = False

    for arg in argv:
        if arg in {"-h", "--help"}:
            show_help = True
        elif arg in {"-v", "--version", "-V"}:
            show_version = True
        elif arg in {"-u", "--upgrade"}:
            do_upgrade = True
        else:
            raise ValueError(f"Unknown flag '{arg}'")
    return show_help, show_version, do_upgrade


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if args:
        try:
            show_help, show_version, do_upgrade = _parse_args(args)
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

    orchestrator = Orchestrator(start_path=os.getcwd())
    orchestrator.run()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
