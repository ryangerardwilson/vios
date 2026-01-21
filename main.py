#!/usr/bin/env python3
import curses
import os
import sys

from modules.core_navigator import FileNavigator

os.environ.setdefault("ESCDELAY", "25")


def main(stdscr):
    start_path = os.getcwd()
    navigator = FileNavigator(start_path)

    try:
        navigator.run(stdscr)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    curses.wrapper(main)
