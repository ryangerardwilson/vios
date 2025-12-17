import curses

from .directory_manager import pretty_path


class UIRenderer:
    def __init__(self, navigator):
        self.nav = navigator
        self.stdscr = None

    def render(self):
        if not self.stdscr:
            return
        stdscr = self.stdscr
        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()

        # === FULL-SCREEN CHEATSHEET WHEN SHOWN ===
        if self.nav.show_help:
            lines = [line.rstrip() for line in self.nav.cheatsheet.strip().split('\n')]
            content_height = len(lines)

            panel_width = 64
            panel_height = content_height + 4
            panel_width = min(panel_width, max_x - 4)
            panel_height = min(panel_height, max_y - 2)

            start_y = (max_y - panel_height) // 2
            start_x = (max_x - panel_width) // 2

            # Top border with title
            title = "VIOS CHEATSHEET"
            top_border = "─" + title.center(panel_width - 2, "─") + "─"
            try:
                stdscr.addstr(start_y, start_x, top_border[:panel_width], curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

            # Content lines
            for i, line in enumerate(lines):
                y = start_y + 2 + i
                if y >= max_y - 2:
                    break
                attr = curses.color_pair(2)
                if line.startswith(("Navigation", "Clipboard", "Other")):
                    attr |= curses.A_BOLD
                try:
                    stdscr.addstr(y, start_x + 2, line.ljust(panel_width - 4), attr)
                except curses.error:
                    pass

            # Bottom border with close hint
            quit_hint = "Press ? to close"
            bottom_border = "─".ljust(panel_width - len(quit_hint) - 2, "─") + " " + quit_hint + " "
            try:
                stdscr.addstr(start_y + panel_height - 2, start_x, bottom_border[:panel_width], curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

            # Side borders
            for y in range(start_y + 1, start_y + panel_height - 1):
                try:
                    stdscr.addstr(y, start_x, "│", curses.color_pair(5))
                except curses.error:
                    pass
                try:
                    stdscr.addstr(y, start_x + panel_width - 1, "│", curses.color_pair(5))
                except curses.error:
                    pass

            stdscr.refresh()
            return  # Nothing else drawn during help

        # === NORMAL BROWSER VIEW ===
        # Current path centered at top
        display_path = pretty_path(self.nav.dir_manager.current_path)
        try:
            stdscr.addstr(0, max(0, (max_x - len(display_path)) // 2),
                          display_path[:max_x], curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass

        # File list
        list_start_y = 2
        available_height = max_y - list_start_y - 1  # Reserve status bar

        items = self.nav.dir_manager.get_filtered_items()
        total = len(items)

        if total == 0:
            if self.nav.dir_manager.filter_pattern:
                msg = "(no matches)"
            else:
                msg = "(empty directory)"
            try:
                stdscr.addstr(list_start_y + available_height // 2,
                              max(0, (max_x - len(msg)) // 2), msg, curses.color_pair(3))
            except curses.error:
                pass
        else:
            for i in range(min(available_height, total)):
                name, is_dir = items[i]
                prefix = "> " if i == self.nav.browser_selected else "  "
                color = (curses.color_pair(1) | curses.A_BOLD
                         if i == self.nav.browser_selected else curses.color_pair(2))
                suffix = '/' if is_dir else ''
                line = f"{prefix}{name}{suffix}"
                try:
                    stdscr.addstr(list_start_y + i, 2, line[:max_x-3], color)
                except curses.error:
                    pass

        # Status bar – shows /pattern when active or persisted
        yank_text = (f"  CUT: {self.nav.clipboard.yanked_original_name}"
                     f"{'/' if self.nav.clipboard.yanked_is_dir else ''}"
                     if self.nav.clipboard.yanked_temp_path else "")
        filter_text = f"  /{self.nav.dir_manager.filter_pattern}" if self.nav.dir_manager.filter_pattern else ""
        help_hint = "  ? help" if not self.nav.show_help else ""
        status = f"[HJKL]{help_hint}{filter_text}{yank_text}"
        try:
            stdscr.addstr(max_y - 1, 0, status[:max_x-1], curses.color_pair(5) | curses.A_BOLD)
        except curses.error:
            pass

        stdscr.refresh()
