"""Singular extensions: _is_tt_move_singular against extreme bars, plus tactics at depths where SE fires."""

import time

from lcbot.board import STARTING_FEN, Board
from lcbot.move import move_to_uci
from lcbot.movegen import generate_legal_moves
from lcbot.search import MATE_THRESHOLD, SE_MIN_DEPTH, Searcher, find_best_move
from lcbot import search
def _ready(s):
    s.start = time.perf_counter()


def test_singular_true():
    b = Board(STARTING_FEN)
    s = Searcher()
    _ready(s)
    moves = generate_legal_moves(b)
    tt_move = moves[0]
    assert s._is_tt_move_singular(b, moves, tt_move, singular_beta=90_000, singular_depth=1, ply=1) is True


def test_singular_false():
    b = Board(STARTING_FEN)
    s = Searcher()
    _ready(s)
    moves = generate_legal_moves(b)
    tt_move = moves[0]
    assert s._is_tt_move_singular(b, moves, tt_move, singular_beta=-90_000, singular_depth=1, ply=1) is False


def test_rook_mate():
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = find_best_move(b, depth=SE_MIN_DEPTH + 3)
    assert move_to_uci(move) == "e1e8"
    assert score >= MATE_THRESHOLD


def test_hanging_queen():
    b = Board("3k4/8/8/3q4/8/3R4/3K4/8 w - - 0 1")
    move, score = find_best_move(b, depth=SE_MIN_DEPTH + 3)
    assert move_to_uci(move) == "d3d5"
    assert score > 500


def test_middlegame_position(monkeypatch):
    """Kiwipete at depth 7 has enough TT hits below the root for SE to run.

    The mate-in-1 trees above are too small to ever trigger it."""
    kiwipete = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    calls = []
    real = Searcher._is_tt_move_singular

    def counting(self, *args, **kwargs):
        calls.append(1)
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Searcher, "_is_tt_move_singular", counting)
    s = Searcher()
    move, score = s.search(Board(kiwipete), max_depth=7)

    assert len(calls) > 0
    assert move != 0
    assert abs(score) < MATE_THRESHOLD
