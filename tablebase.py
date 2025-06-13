"""Syzygy endgame tablebase probing, via python-chess's `chess.syzygy`.

Works with any subset of tables present: positions not covered probe as None.
"""

import chess
import chess.syzygy

# WDL outcome codes (python-chess convention), from the perspective of the
# side to move in the probed position.
WDL_WIN, WDL_CURSED_WIN, WDL_DRAW, WDL_BLESSED_LOSS, WDL_LOSS = 2, 1, 0, -1, -2


class Tablebase:
    """A set of open Syzygy tables. Not thread-safe."""

    def __init__(self, directory: str):
        self._tb = chess.syzygy.open_tablebase(directory)

    def close(self) -> None:
        self._tb.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def probe_wdl(self, board) -> int | None:
        """WDL for the side to move, or None if no loaded table covers it."""
        cb = chess.Board(board.get_fen())
        try:
            return self._tb.probe_wdl(cb)
        except chess.syzygy.MissingTableError:
            return None
