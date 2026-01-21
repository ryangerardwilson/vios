# ~/Apps/vios/modules/ui_renderer.py
import curses
from typing import Any, Optional, Tuple, cast
from .directory_manager import DirectoryManager


class UIRenderer:
    def __init__(self, navigator):
        self.nav = navigator
        self.stdscr: Optional[Any] = None

    def render(self):
        stdscr = self.stdscr
        if stdscr is None:
            return
        max_y, max_x = cast(Tuple[int, int], stdscr.getmaxyx())

        try:
            stdscr.erase()
        except Exception:
            try:
                stdscr.clear()
            except Exception:
                pass

        if self.nav.show_help:
            lines = [line.rstrip() for line in self.nav.cheatsheet.strip().split("\n")]
            total_lines = len(lines)
            max_visible = max(1, max_y - 1)
            start = max(0, min(self.nav.help_scroll, max(0, total_lines - max_visible)))
            visible = lines[start : start + max_visible]
            for i, line in enumerate(visible):
                try:
                    stdscr.addstr(i, 0, line[:max_x])
                except curses.error:
                    pass
            status = f"HELP {start + 1}-{start + len(visible)} / {total_lines}"
            try:
                stdscr.move(max_y - 1, 0)
                stdscr.clrtoeol()
                stdscr.addstr(
                    max_y - 1,
                    0,
                    status[: max_x - 1],
                    curses.color_pair(5) | curses.A_BOLD,
                )
            except curses.error:
                pass
            stdscr.refresh()
            return

        display_path = DirectoryManager.pretty_path(self.nav.dir_manager.current_path)
        try:
            stdscr.addstr(
                0, 0, display_path[:max_x], curses.color_pair(2) | curses.A_BOLD
            )
        except curses.error:
            pass

        if max_y > 1:
            try:
                stdscr.move(1, 0)
                stdscr.clrtoeol()
            except curses.error:
                pass

        list_start_y = 2
        available_height = max_y - list_start_y - 1
        if available_height < 0:
            available_height = 0

        for yy in range(list_start_y, max_y - 1):
            try:
                stdscr.move(yy, 0)
                stdscr.clrtoeol()
            except curses.error:
                pass

        items = self.nav.build_display_items()
        total = len(items)

        if total > 0:
            if (
                self.nav.browser_selected >= self.nav.list_offset + available_height
                or self.nav.browser_selected < self.nav.list_offset
            ):
                if self.nav.browser_selected < self.nav.list_offset:
                    self.nav.list_offset = self.nav.browser_selected
                else:
                    self.nav.list_offset = (
                        self.nav.browser_selected - available_height + 1
                    )
            self.nav.list_offset = max(
                0, min(self.nav.list_offset, max(0, total - available_height))
            )
        else:
            self.nav.list_offset = 0

        visible_items = items[
            self.nav.list_offset : self.nav.list_offset + available_height
        ]

        if total == 0:
            msg = (
                "(no matches)"
                if self.nav.dir_manager.filter_pattern
                else "(empty directory)"
            )
            try:
                stdscr.addstr(
                    list_start_y + available_height // 2,
                    max(0, (max_x - len(msg)) // 2),
                    msg,
                    curses.color_pair(3),
                )
            except curses.error:
                pass
        else:
            for i, (name, is_dir, full_path, depth) in enumerate(visible_items):
                global_idx = self.nav.list_offset + i

                arrow = ">" if global_idx == self.nav.browser_selected else " "
                mark = "✓" if full_path in self.nav.marked_items else " "
                sel_block = f"{arrow}{mark} "

                if is_dir:
                    exp_symbol = "▾ " if full_path in self.nav.expanded_nodes else "▸ "
                else:
                    exp_symbol = "  "

                color = (
                    curses.color_pair(1) | curses.A_BOLD
                    if global_idx == self.nav.browser_selected
                    else curses.color_pair(2)
                )
                suffix = "/" if is_dir else ""
                indent = "  " * depth
                line = f"{indent}{sel_block}{exp_symbol}{name}{suffix}"

                y = list_start_y + i
                try:
                    stdscr.move(y, 0)
                    stdscr.clrtoeol()
                    stdscr.addstr(y, 0, line[:max_x], color)
                except curses.error:
                    pass

        # Status bar
        yank_text = ""
        clip_status = self.nav.clipboard.get_status_text()
        if clip_status:
            yank_text = f"  CLIP: {clip_status}"

        filter_text = ""
        if self.nav.dir_manager.filter_pattern:
            fp = self.nav.dir_manager.filter_pattern
            filter_text = f"  {fp if fp.startswith('/') else '/' + fp}"

        leader_text = ""
        leader_seq = getattr(self.nav, "leader_sequence", "")
        if leader_seq:
            leader_text = f"  {leader_seq}"

        hidden_indicator = self.nav.dir_manager.get_hidden_status_text()
        help_hint = "  ? help" if not self.nav.show_help else ""
        scroll_indicator = ""
        if total > available_height:
            top = self.nav.list_offset + 1
            bottom = min(total, self.nav.list_offset + available_height)
            scroll_indicator = f"  [{top}-{bottom}/{total}]"

        mark_text = (
            f"  MARKED: {len(self.nav.marked_items)}" if self.nav.marked_items else ""
        )
        message_text = f"  {self.nav.status_message}" if self.nav.status_message else ""

        status = f"{help_hint}{filter_text}{leader_text}{hidden_indicator}{scroll_indicator}{yank_text}{mark_text}{message_text}"

        try:
            stdscr.move(max_y - 1, 0)
            stdscr.clrtoeol()
            stdscr.addstr(
                max_y - 1, 0, status[: max_x - 1], curses.color_pair(5) | curses.A_BOLD
            )
        except curses.error:
            pass

        stdscr.refresh()
