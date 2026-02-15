"""An exception inside search must still produce a legal bestmove and leave the board unchanged.

Without this, a failing search thread (e.g. a corrupt tablebase file) never
prints bestmove and the GUI hangs; an exception unwinding through _negamax also
skips unmake_move calls, so the board is restored from a FEN snapshot.
"""

import io

from lcbot.board import Board
from lcbot.movegen import generate_legal_moves
from lcbot.uci import UCIEngine


def make_engine():
    return UCIEngine(out=io.StringIO())


class _ExplodingTablebase:
    """Raises something other than MissingTableError, like a corrupt file would."""

    def probe_wdl(self, board):
        raise ValueError("simulated corrupted tablebase file")


def test_exception_still_bestmove():
    # Call _run_search directly: cmd_go's _sync_tablebase() would replace the
    # injected tablebase from config.
    e = make_engine()
    e.searcher.tablebase = _ExplodingTablebase()
    few_pieces_fen = "7k/8/8/8/8/8/8/K5Q1 w - - 0 1"  # under the probe guard
    e.cmd_position(["fen"] + few_pieces_fen.split())
    e._run_search(max_depth=3, movetime=None, max_nodes=None)
    out = e.out.getvalue()
    assert "bestmove" in out
    assert "info string search error" in out


def test_exception_restores_board():
    e = make_engine()
    e.searcher.tablebase = _ExplodingTablebase()
    few_pieces_fen = "7k/8/8/8/8/8/8/K5Q1 w - - 0 1"
    e.cmd_position(["fen"] + few_pieces_fen.split())
    e._run_search(max_depth=3, movetime=None, max_nodes=None)
    assert e.board.get_fen() == few_pieces_fen
    assert e.board.history == []


def test_exception_bestmove_legal():
    from lcbot.move import move_to_uci

    e = make_engine()
    e.searcher.tablebase = _ExplodingTablebase()
    few_pieces_fen = "7k/8/8/8/8/8/8/K5Q1 w - - 0 1"
    e.cmd_position(["fen"] + few_pieces_fen.split())
    e._run_search(max_depth=3, movetime=None, max_nodes=None)
    out = e.out.getvalue()
    bestmove_line = next(line for line in out.splitlines() if line.startswith("bestmove"))
    uci_move = bestmove_line.split()[1]
    legal = {move_to_uci(m) for m in generate_legal_moves(Board(few_pieces_fen))}
    assert uci_move in legal


def test_no_legal_moves():
    """If search raises in a position with no legal moves, the fallback sends 0000."""
    e = make_engine()

    class _AlwaysRaisingSearcher:
        tablebase = None

        def search(self, *args, **kwargs):
            raise RuntimeError("simulated failure")

    e.searcher = _AlwaysRaisingSearcher()
    # Back-rank mate: black has no legal moves.
    e.cmd_position(["fen"] + "1R4k1/5ppp/8/8/8/8/8/6K1 b - - 0 1".split())
    e.cmd_go(["depth", "1"])
    e.wait_for_search(timeout=15)
    assert "bestmove 0000" in e.out.getvalue()
