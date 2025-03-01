"""Runs uci.py as a subprocess under python-chess's UCI client to check protocol framing."""

import sys
from pathlib import Path

import chess
import chess.engine
import pytest

ENGINE_CMD = [sys.executable, str(Path(__file__).resolve().parent.parent / "uci.py")]


@pytest.fixture
def engine():
    eng = chess.engine.SimpleEngine.popen_uci(ENGINE_CMD)
    try:
        yield eng
    finally:
        eng.quit()


def test_id(engine):
    assert engine.id["name"] == "lc-bot"
    assert engine.id["author"] == "Lucas Ciordas"


def test_options(engine):
    assert "Hash" in engine.options


def test_configure_hash(engine):
    engine.configure({"Hash": 128})


def test_play_startpos(engine):
    board = chess.Board()
    result = engine.play(board, chess.engine.Limit(depth=3))
    assert result.move in board.legal_moves


def test_play_fen(engine):
    board = chess.Board("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")
    result = engine.play(board, chess.engine.Limit(depth=2))
    assert result.move in board.legal_moves


def test_analyse(engine):
    board = chess.Board()
    info = engine.analyse(board, chess.engine.Limit(depth=3))
    assert "pv" in info and len(info["pv"]) > 0
    assert "score" in info


def test_repeated_searches(engine):
    """A stale _search_thread must not block a later go."""
    board = chess.Board()
    for _ in range(3):
        result = engine.play(board, chess.engine.Limit(depth=2))
        assert result.move in board.legal_moves
        board.push(result.move)
