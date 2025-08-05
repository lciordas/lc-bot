"""Reference NNUE forward pass, rebuilt from scratch on every call.

Slow on purpose: tests check accumulator.py and nnue_packed.py against it.
"""

from constants import WHITE
from features import both_perspectives
from nnue_net import NetParams


def crelu(x: float) -> float:
    """Clipped ReLU on [0, 1]."""
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def accumulate(net: NetParams, feats) -> list:
    """bias + sum of the active feature rows, for one perspective."""
    a = list(net.bias)
    W = net.W
    for f in feats:
        row = W[f]
        for k in range(net.N):
            a[k] += row[k]
    return a


def nn_raw(net: NetParams, board) -> float:
    """The net's output before scaling or clamping."""
    fw, fb = both_perspectives(board)
    aw, ab = accumulate(net, fw), accumulate(net, fb)
    us, them = (aw, ab) if board.side == WHITE else (ab, aw)
    v = net.v
    return sum(v[k] * (crelu(us[k]) - crelu(them[k])) for k in range(net.N))


def nn_cp(net: NetParams, board) -> int:
    """The net's contribution in side-to-move centipawns.

    Truncates toward zero rather than flooring, so it commutes with negation.
    """
    raw = nn_raw(net, board) * net.scale
    v = int(raw) if raw >= 0 else -int(-raw)
    c = net.clampcp
    return -c if v < -c else (c if v > c else v)


def evaluate_ref(net: NetParams, board, base_eval=None) -> int:
    """Full side-to-move evaluation, same convention as `evaluation.evaluate`."""
    if net.mode == "pure":
        return nn_cp(net, board)
    if base_eval is None:
        from evaluation import evaluate as base_eval
    return base_eval(board) + nn_cp(net, board)


def _run_self_test() -> bool:
    from board import Board
    from evaluation import evaluate, _mirror_fen
    from nnue_net import random_net, zero_net
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        ok = ok and cond

    FENS = (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    )

    # A zero hybrid net must reproduce the hand-written eval exactly.
    z = zero_net(N=8)
    if all(evaluate_ref(z, Board(f)) == evaluate(Board(f)) for f in FENS):
        check("zero hybrid net == hand-written evaluate() exactly", True)
    else:
        check("zero hybrid net == hand-written evaluate() exactly", False)

    net = random_net(N=32, seed=7)

    # `_mirror_fen` flips ranks, colours and side to move, so a side-to-move
    # score must be unchanged, not negated.
    worst = 0.0
    for f in FENS:
        a = nn_raw(net, Board(f))
        b = nn_raw(net, Board(_mirror_fen(f)))
        worst = max(worst, abs(a - b))
    check(f"nn_raw invariant under mirror+swap (worst |a-b| = {worst:.2e})",
          worst < 1e-9)
    check("nn_cp invariant under mirror+swap (exact, integer)",
          all(nn_cp(net, Board(f)) == nn_cp(net, Board(_mirror_fen(f)))
              for f in FENS))

    # Flipping only the side to move must negate the score exactly.
    exact = True
    for f in FENS:
        b1 = Board(f)
        b2 = Board(f)
        b2.side ^= 1
        if abs(nn_raw(net, b1) + nn_raw(net, b2)) > 1e-12:
            exact = False
    check("flipping side-to-move negates nn_raw exactly", exact)

    # Force the clamp with a huge scale. Skips the start position, which is
    # symmetric and always scores 0.
    hot = random_net(N=32, seed=7)
    hot.scale = 1e9
    vals = [nn_cp(hot, Board(f)) for f in FENS[1:]]
    check("clamp binds at +/-clampcp",
          all(abs(v) <= 600 for v in vals) and any(abs(v) == 600 for v in vals))

    # A pure net ignores the hand-written eval.
    p = zero_net(N=8, mode="pure")
    check("zero pure net evaluates to exactly 0",
          all(evaluate_ref(p, Board(f)) == 0 for f in FENS))

    print("\n" + ("ALL PASS" if ok else "FAILURES"))
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_self_test() else 1)
