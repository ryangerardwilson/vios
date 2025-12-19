import curses
import subprocess
import os
import sys

from .directory_manager import DirectoryManager
from .clipboard_manager import ClipboardManager
from .ui_renderer import UIRenderer
from .input_handler import InputHandler


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()

        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)

        self.show_help = False
        self.browser_selected = 0
        self.list_offset = 0            # Scroll offset for long lists
        self.need_redraw = True

        self.cheatsheet = r"""
VIOS CHEATSHEET

Navigation
  h               Parent directory (resets filter)
  l / Enter       Enter directory (resets filter) or open file
  j               Down
  k               Up
  ,k              Jump to top
  ,j              Jump to bottom

Filtering (glob-style)
  /               Enter filter mode (type pattern)
                  • "rat" → matches items starting with "rat"
                  • "*.py" → all Python files
                  • "*test*" → contains "test"
                  • Press Enter to apply and persist filter
                  • Press / again to clear filter
  Ctrl+R          Clear filter and show all items

Clipboard
  y               Start yank (copy) — yy to confirm
  d               Start cut/delete — dd to confirm
  Backspace/Del   Immediate cut selected item
  p               Paste (auto-rename on conflict)
  Ctrl+L          Clear clipboard

File Opening
  • Text files (.py, .txt, .md, etc.) → Vim
  • PDF files → Zathura

Other
  t               Open terminal in current directory
  .               Toggle show hidden files/dirs
  ?               Toggle this help
  Ctrl+C          Quit the app
"""

    def open_file(self, filepath: str):
        import mimetypes

        curses.endwin()

        try:
            mime_type, _ = mimetypes.guess_type(filepath)
            if mime_type == 'application/pdf':
                subprocess.Popen([
                    "zathura", filepath
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid
                )
            else:
                subprocess.call([
                    "vim",
                    "-c", f"cd {self.dir_manager.current_path}",
                    filepath
                ])
        except FileNotFoundError:
            pass
        finally:
            self.need_redraw = True

    def open_terminal(self):
        import subprocess

        # Get the current directory (absolute path)
        current_dir = self.dir_manager.current_path

        # Copy "cd /path/to/current/dir" to Wayland clipboard
        cd_command = f"cd \"{current_dir}\""

        try:
            subprocess.run(
                ["wl-copy", cd_command],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            # wl-copy not available (e.g. not on Wayland or not installed) — silently ignore
            pass
        except Exception:
            pass  # Any other error — just continue to quit

        # Now quit the application cleanly — same as Ctrl+C
        raise KeyboardInterrupt  # This will be caught in main() and exit gracefully

    def create_new_file(self):
        stdscr = self.renderer.stdscr
        if not stdscr:
            return

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.need_redraw = True
            return

        prompt = "New file: "
        prompt_y = max_y - 1

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[:max_x-1])
        except curses.error:
            pass

        # Make getstr() blocking while reading filename
        # (run() sets timeout(40) — override temporarily)
        try:
            stdscr.timeout(-1)         # block indefinitely for user input
            curses.echo()
            curses.curs_set(1)

            input_x = len(prompt)
            max_input_width = max_x - input_x - 1
            if max_input_width < 10:
                max_input_width = 10

            stdscr.move(prompt_y, input_x)
            filename_bytes = stdscr.getstr(prompt_y, input_x, max_input_width)
            filename = filename_bytes.decode('utf-8', errors='ignore').strip()
        except KeyboardInterrupt:
            filename = ""
        except Exception:
            filename = ""
        finally:
            curses.noecho()
            curses.curs_set(0)
            stdscr.timeout(40)         # restore run()'s timeout
            self.need_redraw = True

        if not filename:
            return

        unique_name = self.input_handler._get_unique_name(self.dir_manager.current_path, filename)
        filepath = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            with open(filepath, 'w'):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr.addstr(prompt_y, 0, f"Error creating file: {str(e)[:max_x-20]}", curses.A_BOLD)
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()


    def run(self, stdscr):
        # Basic curses initialization
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 6):
            curses.init_pair(i, [curses.COLOR_CYAN, curses.COLOR_WHITE, curses.COLOR_YELLOW,
                                 curses.COLOR_RED, curses.COLOR_GREEN][i-1], -1)

        # Wire up renderer and optimize stdscr for smoother redraws
        self.renderer.stdscr = stdscr

        # Important: proper key decoding and performance hints
        try:
            stdscr.keypad(True)   # enable decoding of special keys
            stdscr.leaveok(True)  # reduce cursor movement / flicker
            stdscr.idlok(True)    # allow hardware insert/delete line optimizations
        except Exception:
            # Not critical; continue if terminal doesn't support
            pass

        # Small timeout so repeated-key presses are smoother and we don't busy-loop
        stdscr.timeout(40)  # milliseconds; tune if desired

        while True:
            if self.need_redraw:
                self.renderer.render()
                self.need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue

            if self.input_handler.handle_key(stdscr, key):
                break

            self.need_redraw = True

