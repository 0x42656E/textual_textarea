from typing import Optional
from textual.geometry import Offset

import os


class Buffer:
    """
    A buffer.
    """

    def __init__(self) -> None:
        self._lines = [[]]

    @property
    def max_y(self) -> int:
        """
        Returns:
            The line count of the buffer.
        """
        return len(self._lines)

    @property
    def max_x(self) -> int:
        """
        Returns:
            The longest line of the buffer.
        """
        return max(len(line) for line in self._lines)

    def get_line_length(self, y: int) -> Optional[int]:
        """
        Get the line length by y if reachable.
        The lines of the buffer are 0-index based.

        Returns:
            The line length
        """
        try:
            return len(self._lines[y])
        except IndexError:
            return None

    def write(self) -> str:
        """
        Write out the entire buffer.

        Returns:
            The written buffer.
        """
        lines = map(lambda line: "".join(line), self._lines)
        return os.linesep.join(lines)

    def insert_linebreak(self, position: Offset) -> None:
        """
        Insert a linebreak at the given position.

        Args:
            position: The position at which the line break is to be inserted.
        """
        x, y = position
        line = self._lines[y][x:]
        del self._lines[y][x:]
        self._lines.insert(y + 1, line)

    def insert_text(self, position: Offset, text: str) -> None:
        """
        Insert text at the given position.

        Args:
            position: The position at which the text is to be inserted.
            text: The text.
        """
        x, y = position
        if text == os.linesep:
            self.insert_linebreak(position)
            return
        for char in text:
            self._lines[y].insert(x, char)

    def delete_text(self, position: Offset) -> None:
        """
        Delete text at the given position.

        Args:
            position: The position at which the text is to be deleted.
        """
        x, y = position
        del self._lines[y][x]
