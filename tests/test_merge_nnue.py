"""Advanced search running with the NNUE evaluator: accumulator sync, switching nets, parallel workers, GUI toggle."""
import io
from pathlib import Path

import pytest

from lcbot.board import Board, STARTING_FEN
from lcbot.evaluation import evaluate
from lcbot.move import move_to_uci
from lcbot.nnue import load_evaluator
from lcbot.nnue_net import random_net
from lcbot.parallel_search import parallel_find_best_move
from lcbot.search import Searcher, MATE_THRESHOLD
from lcbot.uci import UCIEngine

SHIPPING_NET = str(Path(__file__).resolve().parent.parent / "nets" / "sf_hybrid_damped.json")

# Quiet middlegames (razoring/futility fire), a tactical melee (SEE pruning,
# check extensions), an endgame (null-move guard), and a mate (mate scores).
FENS = (
    STARTING_FEN,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1PN2/PP1B1PPP/R2QKB1R w KQ - 0 8",
    "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
)


@pytest.fixture(scope="module")
def shipping_evaluator():
    return load_evaluator(SHIPPING_NET, "hybrid")


def test_handwritten_default():
    s = Searcher()
    assert s.evaluator is None
    assert s._eval is evaluate


@pytest.mark.parametrize("fen", FENS)
def test_accumulator_in_sync(fen, shipping_evaluator):
    """After a search, the accumulator equals a rebuild and its undo stack is empty."""
    board = Board(fen)
    s = Searcher(evaluator=shipping_evaluator)
    move, _score = s.search(board, max_depth=5)
    assert move != 0
    acc = board.nnue
    assert acc is not None
    assert acc._stack == []
    assert acc.acc == shipping_evaluator.pnet.from_board(board)
    assert board.get_fen() == Board(fen).get_fen()


@pytest.mark.parametrize("fen", FENS[1:3])
def test_nnue_changes_eval(fen, shipping_evaluator):
    """The trained net must change the score. FENS[3] is colour-symmetric, so it scores 0 either way."""
    board = Board(fen)
    shipping_evaluator.refresh(board)
    assert shipping_evaluator(board) != evaluate(board)


def test_switch_nets(tmp_path):
    """After switching nets, refresh must rebuild for the new net, not reuse net A's accumulator."""
    net_b = tmp_path / "b.json"
    random_net(N=16, seed=11).save(str(net_b))

    e = UCIEngine(out=io.StringIO())
    e.cmd_setoption("name UseNNUE value true".split())
    e.cmd_setoption(f"name NNUEPath value {SHIPPING_NET}".split())
    e.cmd_position(["fen"] + FENS[2].split())
    e._sync_nnue()
    e.searcher._eval.refresh(e.board)            # board now holds net A's accumulator
    assert e.board.nnue.pnet is e._nnue.pnet

    e.cmd_setoption(f"name NNUEPath value {net_b}".split())
    e.searcher._eval.refresh(e.board)
    fresh = load_evaluator(str(net_b), "hybrid")
    probe = Board(FENS[2])
    fresh.refresh(probe)
    assert e.searcher._eval(e.board) == fresh(probe)


def test_nnue_off_detaches():
    e = UCIEngine(out=io.StringIO())
    e.cmd_setoption("name UseNNUE value true".split())
    e.cmd_setoption(f"name NNUEPath value {SHIPPING_NET}".split())
    e._sync_nnue()
    e.searcher._eval.refresh(e.board)
    assert e.board.nnue is not None
    e.cmd_setoption("name UseNNUE value false".split())
    assert e.board.nnue is None
    assert e.searcher._eval is evaluate


def test_default_net():
    """UseNNUE true with no NNUEPath loads nnue.DEFAULT_NET."""
    from lcbot.nnue import DEFAULT_NET
    e = UCIEngine(out=io.StringIO())
    e.cmd_setoption("name UseNNUE value true".split())
    e._sync_nnue()
    assert e._nnue_key == (DEFAULT_NET, "hybrid")
    assert e.searcher._eval is e._nnue
    assert "NNUE unavailable" not in e.out.getvalue()


def test_parallel_nnue_mate():
    """The caller's accumulator must come back attached and in sync after a parallel search."""
    board = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(board, depth=3, num_workers=2,
                                          nnue_path=SHIPPING_NET)
    assert move_to_uci(move) == "e1e8"
    assert score >= MATE_THRESHOLD
    ev = load_evaluator(SHIPPING_NET, "hybrid")
    assert board.nnue is not None
    assert board.nnue._stack == []
    assert board.nnue.acc == ev.pnet.from_board(board)


def test_parallel_zero_net(tmp_path):
    """A zero-weight hybrid net must reproduce the hand-written parallel search exactly.

    Compared against parallel, not sequential: workers start without a TT, so
    parallel and sequential scores can legitimately differ."""
    from lcbot.nnue_net import zero_net
    zp = tmp_path / "zero.json"
    zero_net(N=8).save(str(zp))
    fen = FENS[2]
    plain = parallel_find_best_move(Board(fen), depth=4, num_workers=2)
    zeroed = parallel_find_best_move(Board(fen), depth=4, num_workers=2, nnue_path=str(zp))
    assert zeroed == plain


def test_parallel_workers_use_net(tmp_path):
    """Worker scores with a large random net must differ from hand-written ones."""
    from lcbot.movegen import generate_legal_moves
    from lcbot.parallel_search import _search_bucket_null_window
    rp = tmp_path / "rand.json"
    random_net(N=16, seed=5, sigma=0.5).save(str(rp))
    fen = FENS[2]
    moves = generate_legal_moves(Board(fen))[:6]
    killers = [[0, 0] for _ in range(64)]
    history = [[0] * 64 for _ in range(64)]
    def run(nnue_path):
        res, _nodes = _search_bucket_null_window(
            (Board(fen), moves, 3, 0, killers, history, None, nnue_path, "hybrid"))
        return [score for _m, score, _f in res]
    assert run(str(rp)) != run(None)


def test_gui_eval_toggle(shipping_evaluator):
    """The GUI's E key toggles hand-written <-> NNUE."""
    from gui import GameState
    st = GameState(evaluator=shipping_evaluator)
    assert st.use_nnue and st.searcher._eval is shipping_evaluator
    st.toggle_eval()
    assert not st.use_nnue and st.searcher._eval is evaluate
    assert st.board.nnue is None
    st.toggle_eval()
    assert st.use_nnue and st.searcher._eval is shipping_evaluator


def test_gui_toggle_no_net():
    from gui import GameState
    st = GameState()
    st.toggle_eval()
    assert not st.use_nnue and st.searcher._eval is evaluate
    assert "--nnue" in st.status
