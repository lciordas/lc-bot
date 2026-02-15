"""Static Exchange Evaluation tests, with expected values worked out by hand."""

from lcbot.board import Board
from lcbot.move import move_to_uci
from lcbot.movegen import generate_legal_moves
from lcbot.see import see


def find_move(board, uci):
    for m in generate_legal_moves(board):
        if move_to_uci(m) == uci:
            return m
    raise ValueError(f"{uci} not a legal move in this position")


def test_non_capture_is_zero():
    b = Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    m = find_move(b, "e2e3")
    assert see(b, m) == 0


def test_undefended_capture():
    b = Board("3k4/8/8/3q4/8/3R4/3K4/8 w - - 0 1")
    m = find_move(b, "d3d5")
    assert see(b, m) == 900  # queen, nothing recaptures


def test_undefended_rook_capture():
    b = Board("3r4/8/8/8/8/8/8/3RK2k w - - 0 1")
    m = find_move(b, "d1d8")
    assert see(b, m) == 500


def test_losing_capture():
    """QxP defended by a pawn: +100 - 900 = -800."""
    b = Board("4k3/8/2p5/3p4/8/8/3Q4/4K3 w - - 0 1")
    m = find_move(b, "d2d5")
    assert see(b, m) == -800


def test_pawn_trade():
    b = Board("4k3/8/1p6/2p5/3P4/8/8/4K3 w - - 0 1")
    m = find_move(b, "d4c5")
    # dxc5 bxc5
    assert see(b, m) == 0


def test_xray():
    """Doubled rooks take a knight backed by a rook: +320 - 500 + 500 = +320."""
    b = Board("3r1k2/8/8/3n4/8/8/3R4/3R1K2 w - - 0 1")
    m = find_move(b, "d2d5")
    assert see(b, m) == 320


def test_en_passant():
    b = Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    m = find_move(b, "e5d6")
    assert see(b, m) == 100


def test_defended_piece_negative():
    """QxR defended by a pawn: +500 - 900 = -400."""
    b = Board("4k3/8/2p5/3r4/8/8/3Q4/4K3 w - - 0 1")
    m = find_move(b, "d2d5")
    assert see(b, m) == -400


def test_promotion_capture():
    """bxa8=Q undefended: rook 500 + promotion 800 = 1300."""
    b = Board("r3k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
    m = find_move(b, "b7a8q")
    assert see(b, m) == 1300


def test_promotion_recapture():
    """bxa8=Q recaptured: 500 + 800 - 900 = +400, not -400."""
    b = Board("r3k3/1P6/8/3b4/8/8/8/4K3 w - - 0 1")
    m = find_move(b, "b7a8q")
    assert see(b, m) == 400
