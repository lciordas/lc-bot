"""Packed integer NNUE: lane overflow, sum wrap, incremental drift, exact antisymmetry.

Antisymmetry matters because the TT assumes score(side) == -score(other side).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from board import Board
from movegen import generate_legal_moves
from nnue_net import random_net
from nnue_packed import PackedNet, PackedAccumulator
from nnue_ref import nn_cp
from evaluation import _mirror_fen

FENS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
]

NET = random_net(N=16, seed=99)
PNET = PackedNet(NET)


def _walk_positions(seed=0, walks=3, plies=25):
    """Random legal positions reached by playing random moves."""
    rng = random.Random(seed)
    for fen in FENS:
        for _ in range(walks):
            b = Board(fen)
            for _ in range(plies):
                mvs = generate_legal_moves(b)
                if not mvs:
                    break
                b.make_move(rng.choice(mvs))
                yield b


def test_gain_sums_fit():
    """sum(G) <= 65534 per block, or the modular reduction wraps silently."""
    lanes = PNET.lanes
    from nnue_packed import unpacklanes, SUM_LIMIT
    gains = unpacklanes(PNET.gp, lanes)
    assert sum(gains[:PNET.N]) <= SUM_LIMIT
    assert sum(gains[PNET.N:]) <= SUM_LIMIT


def test_lanes_intact():
    """No lane may borrow from its neighbour, in any reachable position."""
    for b in _walk_positions(seed=1):
        acc = PNET.from_board(b)
        assert PNET.check_lanes(acc), f"lane violation at {b.get_fen()}"


def test_matches_float():
    """The packed head must reproduce the float oracle to within quantisation."""
    worst = 0
    for b in _walk_positions(seed=2):
        acc = PNET.from_board(b)
        worst = max(worst, abs(PNET.cp(acc, b.side) - nn_cp(NET, b)))
    assert worst <= 2, f"packed deviates from reference by {worst}cp"


def test_antisymmetric():
    """Flipping only the side to move must negate the score exactly."""
    for b in _walk_positions(seed=3, walks=2, plies=15):
        acc = PNET.from_board(b)
        a = PNET.cp(acc, b.side)
        c = PNET.cp(acc, b.side ^ 1)
        assert a == -c, f"antisymmetry broken: {a} vs {c} at {b.get_fen()}"


def test_mirror():
    """Side-to-move-relative score is unchanged by a colour mirror."""
    for fen in FENS:
        b, m = Board(fen), Board(_mirror_fen(fen))
        x = PNET.cp(PNET.from_board(b), b.side)
        y = PNET.cp(PNET.from_board(m), m.side)
        assert x == y, f"mirror changed the score: {x} vs {y} for {fen}"


@pytest.mark.parametrize("fen", FENS)
def test_incremental(fen):
    rng = random.Random(hash(fen) & 0xFFF)
    for walk in range(4):
        b = Board(fen)
        acc = PackedAccumulator(PNET)
        acc.refresh(b)
        b.nnue = acc
        for ply in range(40):
            mvs = generate_legal_moves(b)
            if not mvs:
                break
            b.make_move(rng.choice(mvs))
            assert acc.acc == PNET.from_board(b), (
                f"incremental drift: {fen[:20]} walk={walk} ply={ply}")


@pytest.mark.parametrize("fen", FENS)
def test_unmake(fen):
    b = Board(fen)
    acc = PackedAccumulator(PNET)
    acc.refresh(b)
    b.nnue = acc
    before = acc.acc
    for mv in generate_legal_moves(b):
        b.make_move(mv)
        b.unmake_move()
        assert acc.acc == before, f"unmake did not restore ({mv})"


def test_zero_net():
    """A zero net must evaluate to exactly 0 after quantisation too."""
    from nnue_net import zero_net
    z = PackedNet(zero_net(N=8), gain=1.0)
    for fen in FENS:
        b = Board(fen)
        assert z.cp(z.from_board(b), b.side) == 0
