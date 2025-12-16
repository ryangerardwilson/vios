#!/usr/bin/env python3
import curses
import sys
import os
from modules.navigator import FileNavigator


def main():
    # Start in the current working directory
    start_path = os.getcwd()
    navigator = FileNavigator(start_path)
    try:
        curses.wrapper(navigator.run)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
