from typing import ClassVar, Iterable, List, Optional, Sequence

from rich.segment import Segment
from rich.syntax import Syntax
from rich.style import Style

from textual import events
from textual.binding import Binding, BindingType
from textual.geometry import Offset, Region, Size
from textual.reactive import var
from textual.scroll_view import ScrollView
from textual.strip import Strip

from ._buffer import Buffer


def _get_segment_index_from_cell_index(
    cell_index: int, line: Sequence[Segment]
) -> Optional[int]:
    """
    Get the index of the segment based on the cell index.

    Args:
        cell_index: Index of the cell.
        line: Line to be searched.

    Returns:
        The segment index if found or None
    """
    length = 0
    for segment_index, segment in enumerate(line):
        cell_length = segment.cell_length
        length += cell_length
        if cell_index in range(length - cell_length, length):
            return segment_index
    return None


def _set_cursor(index: int, line: List[Segment], style: Style) -> List[Segment]:
    """
    Set the cursor on the line with the specified index and style.

    Args:
        index: Cursor index.
        line: Line on which to set the cursor.
        style: Cursor style.

    Returns:
        A new line with the set cursor.
    """
    line_length = Segment.get_line_length(line)
    segments = Segment.divide(line, (0, index, index + 1, line_length))
    segments = [segment for line in segments for segment in line]
    segments = Segment.adjust_line_length(segments, line_length + 1)

    cursor_segment_index = _get_segment_index_from_cell_index(index, segments)
    if cursor_segment_index is None:
        return line

    cursor_segment = segments[cursor_segment_index]
    cursor_segment = Segment(cursor_segment.text, style)
    segments[cursor_segment_index] = cursor_segment
    return segments


def _is_negative(number: int) -> bool:
    """
    Returns:
        True if number is less then 0.
    """
    return number < 0


class TextArea(ScrollView, can_focus=True):
    BINDINGS: ClassVar[List[BindingType]] = [
        Binding("left", "cursor_left", "cursor left"),
        Binding("right", "cursor_right", "cursor right"),
        Binding("up", "cursor_up", "cursor up"),
        Binding("down", "cursor_down", "cursor down"),
        Binding("enter", "insert_linebreak_at_cursor", "insert linebreak at cursor"),
    ]

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "textarea--cursor",
    }

    DEFAULT_CSS = """
    TextArea>.textarea--cursor {
        background: white;
        color: black;
    }
    """

    lines: var[List[List[Segment]]] = var([])
    cursor_offset: var[Offset] = var(Offset())
    cursor_y: var[int] = var(0)
    cursor_x: var[int] = var(0)

    def __init__(self) -> None:
        self._buffer = Buffer()
        super().__init__()

    def watch_cursor_offset(
        self, previous_cursor_offset: Offset, cursor_offset: Offset
    ) -> None:
        def get_cursor_region(cursor_offset: Offset) -> Region:
            x, y = cursor_offset
            line = self.lines[y]
            line_length = Segment.get_line_length(line) - x + 1
            region = Region(x, y, line_length, 1)
            region = region.translate(-self.scroll_offset)
            return region

        try:
            self.refresh(get_cursor_region(previous_cursor_offset))
            self.refresh(get_cursor_region(cursor_offset))
        except IndexError:
            pass

    def compute_cursor_offset(self) -> Offset:
        return Offset(self.cursor_x, self.cursor_y)

    def action_cursor_left(self) -> None:
        self.cursor_x -= 1

    def action_cursor_right(self) -> None:
        self.cursor_x += 1

    def action_cursor_up(self) -> None:
        self.cursor_y -= 1

    def action_cursor_down(self) -> None:
        self.cursor_y += 1

    def action_insert_linebreak_at_cursor(self) -> None:
        self._buffer.insert_linebreak(self.cursor_offset)
        self.action_cursor_down()
        self.cursor_x = 0
        self._update_lines()

    def validate_cursor_x(self, cursor_x: int) -> int:
        if _is_negative(0):
            return 0
        line_length = self._buffer.get_line_length(self.cursor_y)
        if line_length is None:
            return cursor_x
        if cursor_x > line_length:
            return line_length
        return cursor_x

    def validate_cursor_y(self, cursor_y: int) -> int:
        if _is_negative(cursor_y):
            return 0
        last_line = self._buffer.max_y - 1
        if cursor_y > last_line:
            return last_line
        return cursor_y

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        y += scroll_y
        cursor_style = self.get_component_rich_style("textarea--cursor")
        try:
            segments = self.lines[y]
        except IndexError:
            if not y:
                return Strip.blank(1, cursor_style)
            return Strip.blank(0)

        cursor_x, cursor_y = self.cursor_offset
        if y == cursor_y:
            segments = _set_cursor(cursor_x, segments, cursor_style)

        line = Strip(segments)
        line = line.crop(scroll_x, scroll_x + self.size.width)
        return line

    def insert_text_at_cursor(self, text: str) -> None:
        """
        Insert the text at the cursor offset.
        """
        self._buffer.insert_text(self.cursor_offset, text)
        self._update_lines()
        self.cursor_x += len(text)

    def _update_lines(self) -> None:
        """
        Update the lines and refresh the widget.
        """
        self.lines = self._make_lines()
        self.virtual_size = Size(self._buffer.max_x, self._buffer.max_y)

    def _make_lines(self) -> List[List[Segment]]:
        """
        Make the lines from the buffer.
        """
        syntax = Syntax(self._buffer.write(), "")

        # set the render options
        options = self._console.options
        options.max_width = self._buffer.max_x
        options.height = self._buffer.max_y

        return self._console.render_lines(syntax, options)

    async def _on_key(self, event: events.Key) -> None:
        # Do the key bindings first
        if await self.handle_key(event):
            event.prevent_default()
            event.stop()
            return
        elif event.is_printable:
            event.stop()
            assert event.character is not None
            self.insert_text_at_cursor(event.character)
            event.prevent_default()
