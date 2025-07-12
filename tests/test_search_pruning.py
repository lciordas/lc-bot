"""Futility pruning and razoring must not hide tactics.

Depths are high enough that futility (depth <= 3) and razoring (depth <= 2) fire throughout the tree.
"""

from board import Board
from move import move_to_uci
from search import MATE_THRESHOLD, find_best_move


def test_rook_mate():
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = find_best_move(b, depth=6)
    assert move_to_uci(move) == "e1e8"
    assert score >= MATE_THRESHOLD


def test_queen_mate():
    b = Board("6k1/5ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1")
    move, score = find_best_move(b, depth=6)
    assert move_to_uci(move) == "d1d8"
    assert score >= MATE_THRESHOLD


def test_hanging_queen():
    b = Board("3k4/8/8/3q4/8/3R4/3K4/8 w - - 0 1")
    move, score = find_best_move(b, depth=8)
    assert move_to_uci(move) == "d3d5"
    assert score > 500


def test_futility_quiet_mate():
    """Re8# is a quiet checking move, which futility pruning must not drop."""
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = find_best_move(b, depth=4)
    assert move_to_uci(move) == "e1e8"
    assert score >= MATE_THRESHOLD


def test_krk_progress():
    """With a large static advantage, pruning must not throw away the win."""
    b = Board("7k/8/8/8/8/8/R7/6K1 w - - 0 1")
    move, score = find_best_move(b, depth=6)
    assert move is not None
    assert score > 400
