# ~/Apps/vios/modules/ui_renderer.py
import curses

from .directory_manager import DirectoryManager


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

        # === HELP SCREEN ===
        if self.nav.show_help:
            lines = [line.rstrip() for line in self.nav.cheatsheet.strip().split('\n')]
            content_height = len(lines)

            panel_width = 64
            panel_height = content_height + 4
            panel_width = min(panel_width, max_x - 4)
            panel_height = min(panel_height, max_y - 2)

            start_y = (max_y - panel_height) // 2
            start_x = (max_x - panel_width) // 2

            title = "VIOS CHEATSHEET"
            top_border = "─" + title.center(panel_width - 2, "─") + "─"
            try:
                stdscr.addstr(start_y, start_x, top_border[:panel_width], curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

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

            quit_hint = "Press ? to close"
            bottom_border = "─".ljust(panel_width - len(quit_hint) - 2, "─") + " " + quit_hint + " "
            try:
                stdscr.addstr(start_y + panel_height - 2, start_x, bottom_border[:panel_width], curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

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
            return

        # === NORMAL VIEW ===
        display_path = DirectoryManager.pretty_path(self.nav.dir_manager.current_path)
        try:
            stdscr.addstr(0, max(0, (max_x - len(display_path)) // 2),
                          display_path[:max_x], curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass

        list_start_y = 2
        available_height = max_y - list_start_y - 1

        items = self.nav.dir_manager.get_filtered_items()
        total = len(items)

        if total > 0:
            # Stable follow-scrolling with buffer at bottom
            min_lines_below = 3  # Try to keep at least 3 lines visible below selection

            # If selection is too close to bottom of current view
            current_bottom = self.nav.list_offset + available_height - 1
            lines_below = total - 1 - self.nav.browser_selected

            if lines_below < min_lines_below and self.nav.browser_selected > current_bottom - min_lines_below:
                # Not enough lines below — pull view up to show more context if possible
                desired_offset = max(0, self.nav.browser_selected - (available_height - min_lines_below - 1))
                self.nav.list_offset = desired_offset
            elif self.nav.browser_selected < self.nav.list_offset:
                # Scrolled above view
                self.nav.list_offset = self.nav.browser_selected
            elif self.nav.browser_selected >= self.nav.list_offset + available_height:
                # Scrolled below view
                self.nav.list_offset = self.nav.browser_selected - available_height + 1

            # Final clamp
            self.nav.list_offset = max(0, min(self.nav.list_offset, max(0, total - available_height)))
        else:
            self.nav.list_offset = 0

        visible_items = items[self.nav.list_offset:self.nav.list_offset + available_height]

        if total == 0:
            msg = "(no matches)" if self.nav.dir_manager.filter_pattern else "(empty directory)"
            try:
                stdscr.addstr(list_start_y + available_height // 2,
                              max(0, (max_x - len(msg)) // 2), msg, curses.color_pair(3))
            except curses.error:
                pass
        else:
            for i, (name, is_dir) in enumerate(visible_items):
                global_idx = self.nav.list_offset + i
                prefix = "> " if global_idx == self.nav.browser_selected else "  "
                color = (curses.color_pair(1) | curses.A_BOLD
                         if global_idx == self.nav.browser_selected else curses.color_pair(2))
                suffix = '/' if is_dir else ''
                line = f"{prefix}{name}{suffix}"
                try:
                    stdscr.addstr(list_start_y + i, 2, line[:max_x-3], color)
                except curses.error:
                    pass

        # === STATUS BAR ===
        yank_text = ""
        if self.nav.clipboard.yanked_temp_path:
            yank_text = f"  CUT: {self.nav.clipboard.yanked_original_name}"
            if self.nav.clipboard.yanked_is_dir:
                yank_text += "/"

        filter_text = ""
        if self.nav.dir_manager.filter_pattern:
            filter_text = f"  /{self.nav.dir_manager.filter_pattern}"

        hidden_indicator = self.nav.dir_manager.get_hidden_status_text()
        help_hint = "  ? help" if not self.nav.show_help else ""

        scroll_indicator = ""
        if total > available_height:
            top = self.nav.list_offset + 1
            bottom = min(total, self.nav.list_offset + available_height)
            scroll_indicator = f"  [{top}-{bottom}/{total}]"

        status = f"[HJKL]{help_hint}{filter_text}{hidden_indicator}{scroll_indicator}{yank_text}"

        try:
            stdscr.addstr(max_y - 1, 0, status[:max_x-1], curses.color_pair(5) | curses.A_BOLD)
        except curses.error:
            pass

        stdscr.refresh()
