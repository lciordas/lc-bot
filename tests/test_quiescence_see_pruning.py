"""SEE pruning in quiescence must not let a losing capture distort the result."""

from board import Board
from move import move_to_uci
from search import Searcher


def test_skips_losing_capture():
    """Qxd5 loses the queen (SEE -800); Rxh8 wins a rook (SEE +500)."""
    b = Board("4k2r/8/2p5/3p4/8/8/3Q3R/4K3 w - - 0 1")
    s = Searcher()
    move, score = s.search(b, max_depth=3)
    assert move_to_uci(move) == "h2h8"
    assert score > 400


def test_qsearch_losing_capture():
    from movegen import generate_legal_captures

    b = Board("4k2r/8/2p5/3p4/8/8/3Q3R/4K3 w - - 0 1")
    s = Searcher()
    captures = generate_legal_captures(b)
    assert len(captures) >= 2  # Qxd5 and Rxh8
    score = s._quiescence(b, -1_000_000, 1_000_000, ply=1)
    assert score > 400
