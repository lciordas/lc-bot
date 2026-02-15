"""Incremental NNUE accumulator must match a from-scratch rebuild after every make/unmake."""

import random

import pytest

from lcbot.accumulator import FloatAccumulator
from lcbot.board import Board
from lcbot.movegen import generate_legal_moves
from lcbot.nnue_net import random_net
from lcbot.move import move_from, move_to, move_flag

PERFT_FENS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
]

# Small N: these tests are about update-path coverage, not width.
NET = random_net(N=8, seed=4242)


def _fresh(board):
    """A from-scratch accumulator for the current position."""
    a = FloatAccumulator(NET)
    a.refresh(board)
    return a


def _assert_matches(board, acc, context):
    ref = _fresh(board)
    assert acc.aw == pytest.approx(ref.aw, abs=1e-9), f"white perspective: {context}"
    assert acc.ab == pytest.approx(ref.ab, abs=1e-9), f"black perspective: {context}"


@pytest.mark.parametrize("fen", PERFT_FENS)
def test_incremental_matches_scratch(fen):
    rng = random.Random(hash(fen) & 0xFFFF)
    for walk in range(4):
        board = Board(fen)
        acc = _fresh(board)
        board.nnue = acc
        for ply in range(40):
            moves = generate_legal_moves(board)
            if not moves:
                break
            mv = rng.choice(moves)
            board.make_move(mv)
            _assert_matches(board, acc,
                            f"{fen[:20]} walk={walk} ply={ply} move={mv}")


@pytest.mark.parametrize("fen", PERFT_FENS)
def test_unmake_restores(fen):
    board = Board(fen)
    acc = _fresh(board)
    board.nnue = acc
    before_w, before_b = list(acc.aw), list(acc.ab)
    for mv in generate_legal_moves(board):
        board.make_move(mv)
        board.unmake_move()
        assert acc.aw == pytest.approx(before_w, abs=1e-9), f"unmake {mv}"
        assert acc.ab == pytest.approx(before_b, abs=1e-9), f"unmake {mv}"


@pytest.mark.parametrize("fen", PERFT_FENS)
def test_deep_round_trip(fen):
    rng = random.Random(7)
    board = Board(fen)
    acc = _fresh(board)
    board.nnue = acc
    before_w, before_b = list(acc.aw), list(acc.ab)
    played = 0
    for _ in range(12):
        moves = generate_legal_moves(board)
        if not moves:
            break
        board.make_move(rng.choice(moves))
        played += 1
    for _ in range(played):
        board.unmake_move()
    assert acc.aw == pytest.approx(before_w, abs=1e-9)
    assert acc.ab == pytest.approx(before_b, abs=1e-9)


# --- special moves a random walk rarely hits ---

SPECIAL = {
    "en passant capture": ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6"),
    "queenside castling (white)": (
        "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1", "e1c1"),
    "kingside castling (white)": (
        "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1", "e1g1"),
    "queenside castling (black)": (
        "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1", "e8c8"),
    "kingside castling (black)": (
        "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1", "e8g8"),
    "promotion to queen": ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q"),
    "underpromotion to knight": ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8n"),
    "promotion with capture": (
        "1n2k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7b8q"),
    "underpromotion with capture": (
        "1n2k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7b8r"),
    "double pawn push": ("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", "e2e4"),
}


def _find(board, uci):
    from lcbot.uci import find_move_by_uci
    return find_move_by_uci(board, uci)


@pytest.mark.parametrize("label", sorted(SPECIAL))
def test_special_move_paths(label):
    fen, uci = SPECIAL[label]
    board = Board(fen)
    acc = _fresh(board)
    board.nnue = acc
    mv = _find(board, uci)
    assert mv is not None, f"{label}: {uci} not legal in {fen}"
    before_w, before_b = list(acc.aw), list(acc.ab)
    board.make_move(mv)
    _assert_matches(board, acc, label)
    board.unmake_move()
    assert acc.aw == pytest.approx(before_w, abs=1e-9), f"{label} unmake"
    assert acc.ab == pytest.approx(before_b, abs=1e-9), f"{label} unmake"


def test_null_move():
    board = Board(PERFT_FENS[1])
    acc = _fresh(board)
    board.nnue = acc
    before_w, before_b = list(acc.aw), list(acc.ab)
    board.make_null_move()
    _assert_matches(board, acc, "after null move")
    assert acc.aw == pytest.approx(before_w, abs=1e-9)
    board.unmake_null_move()
    assert acc.aw == pytest.approx(before_w, abs=1e-9)
    assert acc.ab == pytest.approx(before_b, abs=1e-9)


def test_off_by_default():
    board = Board()
    assert board.nnue is None
    board.make_move(generate_legal_moves(board)[0])
    assert board.nnue is None
