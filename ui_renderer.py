# ~/Apps/vios/ui_renderer.py
import curses
import random
import time
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple, cast

from directory_manager import DirectoryManager


@dataclass
class MatrixStream:
    index: int
    name: str
    path: str
    is_dir: bool
    depth: int
    column: int
    velocity: float
    head: float
    chars: str

    @property
    def length(self) -> int:
        return max(1, len(self.chars))


@dataclass
class MatrixState:
    streams: list[MatrixStream]
    signature: Tuple[str, ...]
    max_height: int
    max_width: int
    last_update: float
    index_map: dict[int, MatrixStream]


@dataclass
class IdleStream:
    column: int
    velocity: float
    head: float
    chars: str


@dataclass
class IdleMatrixState:
    streams: list[IdleStream]
    max_height: int
    max_width: int
    last_update: float


class UIRenderer:
    def __init__(self, navigator):
        self.nav = navigator
        self.stdscr: Optional[Any] = None
        self._idle_matrix_state: Optional[IdleMatrixState] = None

    def render(self):
        stdscr = self.stdscr
        if stdscr is None:
            return

        max_y, max_x = cast(Tuple[int, int], stdscr.getmaxyx())
        self._clear_screen(stdscr)

        if self.nav.show_help:
            self._render_help(stdscr, max_y, max_x)
            stdscr.refresh()
            return

        display_path = DirectoryManager.pretty_path(self.nav.dir_manager.current_path)
        self._render_path_header(stdscr, display_path, max_x)

        if self.nav.layout_mode == "matrix":
            self._render_matrix(stdscr, max_y, max_x)
        else:
            self._render_list(stdscr, max_y, max_x)

        stdscr.refresh()

    # ------------------------------------------------------------------
    # Shared helpers

    def _clear_screen(self, stdscr: Any) -> None:
        try:
            stdscr.erase()
        except Exception:
            try:
                stdscr.clear()
            except Exception:
                pass

    def _render_path_header(self, stdscr: Any, display_path: str, max_x: int) -> None:
        try:
            stdscr.addstr(0, 0, display_path[:max_x])
        except curses.error:
            pass
        try:
            stdscr.move(1, 0)
            stdscr.clrtoeol()
        except curses.error:
            pass

    def _render_status_bar(self, stdscr: Any, text: str, max_y: int, max_x: int, *, bold: bool = True) -> None:
        if max_y <= 0:
            return
        attr = curses.A_BOLD if bold else curses.A_NORMAL
        try:
            stdscr.move(max_y - 1, 0)
            stdscr.clrtoeol()
            stdscr.addstr(max_y - 1, 0, text[: max_x - 1] if max_x > 0 else text, attr)
        except curses.error:
            pass

    def _compose_status(
        self,
        *,
        mode_indicator: str = "",
        scroll_indicator: str = "",
        visual_count: Optional[int] = None,
    ) -> str:
        parts: list[str] = []

        if mode_indicator:
            parts.append(mode_indicator)

        if not self.nav.show_help:
            parts.append("? help")

        if scroll_indicator.strip():
            parts.append(scroll_indicator.strip())

        if self.nav.dir_manager.filter_pattern:
            fp = self.nav.dir_manager.filter_pattern
            parts.append(fp if fp.startswith('/') else '/' + fp)

        leader_seq = getattr(self.nav, "leader_sequence", "")
        if leader_seq:
            parts.append(leader_seq)

        hidden_indicator = self.nav.dir_manager.get_hidden_status_text().strip()
        if hidden_indicator:
            parts.append(hidden_indicator)

        clip_status = self.nav.clipboard.get_status_text()
        if clip_status:
            parts.append(f"CLIP: {clip_status}")

        if self.nav.marked_items:
            parts.append(f"MARKED: {len(self.nav.marked_items)}")

        if visual_count is None and getattr(self.nav, "visual_mode", False):
            items = self.nav.build_display_items()
            indices = getattr(self.nav, "get_visual_indices", lambda _t: [])(len(items))
            visual_count = len(indices)
        if visual_count:
            noun = "item" if visual_count == 1 else "items"
            parts.append(f"-- VISUAL -- ({visual_count} {noun})")

        if self.nav.status_message:
            parts.append(self.nav.status_message)

        if not parts:
            return " "

        return "  ".join(parts)

    # ------------------------------------------------------------------
    # Help view

    def _render_help(self, stdscr: Any, max_y: int, max_x: int) -> None:
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
        self._render_status_bar(stdscr, status, max_y, max_x)

    # ------------------------------------------------------------------
    # List layout

    def _render_list(self, stdscr: Any, max_y: int, max_x: int) -> None:
        list_start_y = 2
        available_height = max_y - list_start_y - 1
        if available_height < 0:
            available_height = 0

        for yy in range(list_start_y, max(0, max_y - 1)):
            try:
                stdscr.move(yy, 0)
                stdscr.clrtoeol()
            except curses.error:
                pass

        items = self.nav.build_display_items()
        total = len(items)
        visual_indices_set = set()
        visual_count = 0
        if hasattr(self.nav, "get_visual_indices"):
            indices = self.nav.get_visual_indices(total)
            visual_indices_set = set(indices)
            visual_count = len(visual_indices_set)

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
                    list_start_y + (available_height // 2 if available_height else 0),
                    max(0, (max_x - len(msg)) // 2),
                    msg,
                    curses.A_DIM,
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

                attr = curses.A_BOLD if global_idx == self.nav.browser_selected else curses.A_NORMAL
                if global_idx in visual_indices_set:
                    attr |= curses.A_REVERSE

                suffix = "/" if is_dir else ""
                indent = "  " * depth
                line = f"{indent}{sel_block}{exp_symbol}{name}{suffix}"

                y = list_start_y + i
                try:
                    stdscr.move(y, 0)
                    stdscr.clrtoeol()
                    stdscr.addstr(y, 0, line[:max_x], attr)
                except curses.error:
                    pass

        scroll_indicator = ""
        if total > available_height and available_height > 0:
            top = self.nav.list_offset + 1
            bottom = min(total, self.nav.list_offset + available_height)
            scroll_indicator = f"  [{top}-{bottom}/{total}]"

        status = self._compose_status(
            mode_indicator="",
            scroll_indicator=scroll_indicator,
            visual_count=visual_count,
        )
        self._render_status_bar(stdscr, status, max_y, max_x, bold=False)

    # ------------------------------------------------------------------
    # Matrix layout

    def _render_matrix(self, stdscr: Any, max_y: int, max_x: int) -> None:
        content_start_y = 2
        available_rows = max_y - content_start_y - 1
        label_row = max_y - 2

        if available_rows <= 0 or max_x <= 0:
            msg = "(matrix view needs more space)"
            try:
                stdscr.addstr(1, 0, msg[:max_x] if max_x > 0 else msg, curses.A_DIM)
            except curses.error:
                pass
            status = self._compose_status(mode_indicator="[Matrix]")
            self._render_status_bar(stdscr, status, max_y, max_x, bold=False)
            return

        matrix_height = max(1, available_rows - 1)
        for y in range(content_start_y, max(0, max_y - 1)):
            try:
                stdscr.move(y, 0)
                stdscr.clrtoeol()
            except curses.error:
                pass

        items = self.nav.build_display_items()
        total = len(items)

        if total == 0:
            self.nav.matrix_state = None
            self._render_idle_matrix(stdscr, content_start_y, label_row, matrix_height, max_x)
            status = self._compose_status(mode_indicator="[Matrix]")
            self._render_status_bar(stdscr, status, max_y, max_x, bold=False)
            return

        self._idle_matrix_state = None
        state = self._ensure_matrix_state(items, matrix_height, max_x)

        now = time.monotonic()
        delta = 0.0 if state.last_update == 0 else now - state.last_update
        state.last_update = now

        selected_index = 0 if total == 0 else max(0, min(self.nav.browser_selected, total - 1))
        if total > 0:
            self.nav.browser_selected = selected_index

        visual_indices: list[int] = []
        if getattr(self.nav, "visual_mode", False):
            visual_indices = getattr(self.nav, "get_visual_indices", lambda _t: [])(total)

        paused_indices = set(visual_indices)
        paused_indices.add(selected_index)

        if self.nav.marked_items:
            index_by_path = {items[idx][2]: idx for idx in range(total)}
            for marked_path in self.nav.marked_items:
                idx = index_by_path.get(marked_path)
                if idx is not None:
                    paused_indices.add(idx)

        for stream in state.streams:
            if stream.index in paused_indices:
                continue
            stream.head = (stream.head + stream.velocity * delta) % matrix_height

        for stream in state.streams:
            col = max(0, min(max_x - 1, stream.column))
            chars = stream.chars or "0"
            for row_offset in range(matrix_height):
                y = content_start_y + row_offset
                if y >= label_row:
                    break
                offset = int((stream.head - row_offset) % stream.length)
                char_index = (stream.length - 1 - offset) % stream.length
                ch = chars[char_index]
                attr = curses.A_DIM
                if stream.index == selected_index:
                    attr = curses.A_BOLD if offset == 0 else curses.A_NORMAL
                elif offset == 0:
                    attr = curses.A_NORMAL
                try:
                    stdscr.addch(y, col, ch, attr)
                except curses.error:
                    pass

        if 0 <= label_row < max_y:
            name, is_dir, *_ = items[selected_index]
            label = name + ("/" if is_dir else "")
            start_x = 0
            try:
                stdscr.move(label_row, 0)
                stdscr.clrtoeol()
                width = max(0, max_x - start_x)
                if width > 0:
                    stdscr.addstr(label_row, start_x, label[:width])
            except curses.error:
                pass

        selection_indicator = f"  [{selected_index + 1}/{total}]"
        status = self._compose_status(
            mode_indicator="[Matrix]",
            scroll_indicator=selection_indicator,
            visual_count=len(visual_indices) if getattr(self.nav, "visual_mode", False) else 0,
        )
        self._render_status_bar(stdscr, status, max_y, max_x, bold=False)

    def _compute_columns(self, count: int, max_x: int) -> list[int]:
        if count <= 0 or max_x <= 0:
            return []
        positions: list[int] = []
        for idx in range(count):
            pos = int((idx + 1) * max_x / (count + 1))
            pos = max(0, min(max_x - 1, pos))
            if positions and pos <= positions[-1]:
                pos = min(max_x - 1, positions[-1] + 1)
            positions.append(pos)
        return positions

    def _ensure_matrix_state(
        self,
        items: Sequence[Tuple[str, bool, str, int]],
        matrix_height: int,
        max_x: int,
    ) -> MatrixState:
        signature = tuple(entry[2] for entry in items)
        state: Optional[MatrixState] = getattr(self.nav, "matrix_state", None)

        if (
            state is None
            or state.signature != signature
            or state.max_height != matrix_height
            or state.max_width != max_x
        ):
            streams: list[MatrixStream] = []
            columns = self._compute_columns(len(items), max_x)
            pattern_length = max(32, matrix_height * 2)
            for idx, (name, is_dir, path, depth) in enumerate(items):
                column = columns[idx] if idx < len(columns) else (idx % max_x)
                velocity = random.uniform(5.0, 12.0)
                head = random.uniform(0, matrix_height - 1 if matrix_height > 1 else 0)
                base_label = name + ("/" if is_dir else "")
                sanitized = base_label.strip()
                if not sanitized:
                    sanitized = "?"
                sanitized = sanitized.replace(" ", "_")
                if len(sanitized) == 1:
                    chars = sanitized * pattern_length
                else:
                    repeats = (pattern_length // len(sanitized)) + 2
                    chars = (sanitized * repeats)[:pattern_length]
                streams.append(
                    MatrixStream(
                        index=idx,
                        name=name,
                        path=path,
                        is_dir=is_dir,
                        depth=depth,
                        column=column,
                        velocity=velocity,
                        head=head,
                        chars=chars,
                    )
                )

            index_map = {stream.index: stream for stream in streams}
            state = MatrixState(
                streams=streams,
                signature=signature,
                max_height=matrix_height,
                max_width=max_x,
                last_update=0.0,
                index_map=index_map,
            )
            self.nav.matrix_state = state

        return state

    def _render_idle_matrix(
        self,
        stdscr: Any,
        content_start_y: int,
        label_row: int,
        matrix_height: int,
        max_x: int,
    ) -> None:
        count = min(12, max_x if max_x > 0 else 12)
        if count <= 0:
            return

        state = self._idle_matrix_state
        if (
            state is None
            or state.max_height != matrix_height
            or state.max_width != max_x
            or not state.streams
        ):
            columns = self._compute_columns(count, max_x) or [min(max_x - 1, i) for i in range(count)]
            length = max(32, matrix_height * 2)
            streams: list[IdleStream] = []
            for idx in range(count):
                column = columns[idx] if idx < len(columns) else min(max_x - 1, idx)
                velocity = random.uniform(4.0, 9.0)
                head = random.uniform(0, matrix_height - 1 if matrix_height > 1 else 0)
                chars = "".join(random.choice("01") for _ in range(length))
                streams.append(IdleStream(column=column, velocity=velocity, head=head, chars=chars))
            state = IdleMatrixState(
                streams=streams,
                max_height=matrix_height,
                max_width=max_x,
                last_update=time.monotonic(),
            )
            self._idle_matrix_state = state

        now = time.monotonic()
        delta = 0.0 if state.last_update == 0 else now - state.last_update
        state.last_update = now

        trail_length = max(32, matrix_height * 2)

        if 0 <= label_row:
            try:
                stdscr.move(label_row, 0)
                stdscr.clrtoeol()
            except curses.error:
                pass

        for stream in state.streams:
            stream.head = (stream.head + stream.velocity * delta) % matrix_height
            if len(stream.chars) < trail_length:
                repeats = (trail_length // max(1, len(stream.chars))) + 2
                stream.chars = (stream.chars * repeats)[: trail_length]
            chars = stream.chars or "0"
            length = len(chars)
            col = max(0, min(max_x - 1, stream.column))
            for row_offset in range(matrix_height):
                y = content_start_y + row_offset
                if y >= label_row:
                    break
                offset = int((stream.head - row_offset) % length)
                char_index = (length - 1 - offset) % length
                ch = chars[char_index]
                attr = curses.A_DIM
                if offset == int(stream.head % length):
                    attr = curses.A_NORMAL
                try:
                    stdscr.addch(y, col, ch, attr)
                except curses.error:
                    pass
