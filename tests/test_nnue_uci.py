"""UCI-level tests for the UseNNUE / NNUEPath / NNUEMode options."""
import io

import pytest

from lcbot.nnue_net import zero_net, random_net
from lcbot.uci import UCIEngine


@pytest.fixture
def zero_net_path(tmp_path):
    p = tmp_path / "zero.json"
    zero_net(N=8).save(str(p))
    return str(p)


@pytest.fixture
def real_net_path(tmp_path):
    p = tmp_path / "rand.json"
    random_net(N=16, seed=3).save(str(p))
    return str(p)


def _engine():
    out = io.StringIO()
    return UCIEngine(out=out), out


def _finish(e, timeout=60.0):
    """Wait for a `go` to finish on its own.

    Not _stop_search(): aborting lands at different points in two engines, so
    comparing their moves would be flaky.
    """
    if e._search_thread is not None:
        e._search_thread.join(timeout=timeout)
        assert not e._search_thread.is_alive(), "search did not finish in time"
    e._search_thread = None


def test_options():
    e, out = _engine()
    e.cmd_uci()
    text = out.getvalue()
    assert "option name UseNNUE type check default false" in text
    assert "option name NNUEPath type string default <empty>" in text
    assert "NNUEMode type combo default hybrid var hybrid var pure" in text


def test_off_by_default():
    e, _ = _engine()
    assert e.searcher.evaluator is None


def test_enable(real_net_path):
    e, _ = _engine()
    e.cmd_setoption(["name", "NNUEPath", "value", real_net_path])
    e.cmd_setoption(["name", "UseNNUE", "value", "true"])
    assert e.searcher.evaluator is not None
    assert e.searcher.evaluator.mode == "hybrid"


def test_mode_switch(real_net_path):
    e, _ = _engine()
    e.cmd_setoption(["name", "NNUEPath", "value", real_net_path])
    e.cmd_setoption(["name", "UseNNUE", "value", "true"])
    e.cmd_setoption(["name", "NNUEMode", "value", "pure"])
    assert e.searcher.evaluator.mode == "pure"


def test_disable(real_net_path):
    from lcbot.evaluation import evaluate
    e, _ = _engine()
    e.cmd_setoption(["name", "NNUEPath", "value", real_net_path])
    e.cmd_setoption(["name", "UseNNUE", "value", "true"])
    e.cmd_setoption(["name", "UseNNUE", "value", "false"])
    assert e.searcher.evaluator is None
    assert e.searcher._eval is evaluate


def test_bad_path():
    from lcbot.evaluation import evaluate
    e, out = _engine()
    e.cmd_setoption(["name", "NNUEPath", "value", "/nonexistent/net.json"])
    e.cmd_setoption(["name", "UseNNUE", "value", "true"])
    assert e.searcher.evaluator is None
    assert e.searcher._eval is evaluate
    assert "info string NNUE unavailable" in out.getvalue()


def test_malformed_net(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"format": "not-a-real-format"}')
    e, out = _engine()
    e.cmd_setoption(["name", "NNUEPath", "value", str(bad)])
    e.cmd_setoption(["name", "UseNNUE", "value", "true"])
    assert e.searcher.evaluator is None
    assert "info string NNUE unavailable" in out.getvalue()


def test_zero_net_same_move(zero_net_path):
    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"

    plain, out_plain = _engine()
    plain.cmd_position(["fen"] + fen.split())
    plain.cmd_go(["depth", "4"])
    _finish(plain)

    nn, out_nn = _engine()
    nn.cmd_setoption(["name", "NNUEPath", "value", zero_net_path])
    nn.cmd_setoption(["name", "UseNNUE", "value", "true"])
    nn.cmd_position(["fen"] + fen.split())
    nn.cmd_go(["depth", "4"])
    _finish(nn)

    def best(text):
        for line in text.splitlines():
            if line.startswith("bestmove"):
                return line
        return None

    assert best(out_plain.getvalue()) is not None
    assert best(out_nn.getvalue()) == best(out_plain.getvalue())


def test_search_with_net(real_net_path):
    e, out = _engine()
    e.cmd_setoption(["name", "NNUEPath", "value", real_net_path])
    e.cmd_setoption(["name", "UseNNUE", "value", "true"])
    e.cmd_position(["startpos"])
    e.cmd_go(["depth", "3"])
    _finish(e)
    assert "bestmove" in out.getvalue()


def test_resync_on_position(real_net_path):
    """A new position from `position` must force an accumulator rebuild."""
    e, _ = _engine()
    e.cmd_setoption(["name", "NNUEPath", "value", real_net_path])
    e.cmd_setoption(["name", "UseNNUE", "value", "true"])
    e.cmd_position(["startpos"])
    e.cmd_go(["depth", "2"])
    _finish(e)
    e.cmd_position(["fen"] + "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1".split())
    e.cmd_go(["depth", "2"])
    _finish(e)
    acc = e.board.nnue
    assert acc is not None
    assert acc.acc == e.searcher.evaluator.pnet.from_board(e.board)
