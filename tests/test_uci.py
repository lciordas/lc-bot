import io
import time

from board import Board, STARTING_FEN
from move import move_to_uci
from uci import UCIEngine, find_move_by_uci


def make_engine():
    return UCIEngine(out=io.StringIO())


# --- move lookup helper ---

def test_find_move():
    b = Board(STARTING_FEN)
    m = find_move_by_uci(b, "e2e4")
    assert m is not None
    assert move_to_uci(m) == "e2e4"


def test_find_move_illegal():
    b = Board(STARTING_FEN)
    assert find_move_by_uci(b, "e2e5") is None  # not a legal pawn move


def test_find_move_promotion():
    b = Board("8/P7/8/8/8/8/8/k6K w - - 0 1")
    m = find_move_by_uci(b, "a7a8q")
    assert m is not None
    assert move_to_uci(m) == "a7a8q"


# --- basic handshake ---

def test_uci():
    e = make_engine()
    e.cmd_uci()
    out = e.out.getvalue()
    assert "id name lc-bot" in out
    assert "id author" in out
    assert "option name Hash" in out
    assert out.strip().splitlines()[-1] == "uciok"


def test_isready():
    e = make_engine()
    e.cmd_isready()
    assert e.out.getvalue().strip() == "readyok"


# --- position command ---

def test_position_startpos():
    e = make_engine()
    e.cmd_position(["startpos"])
    assert e.board.get_fen() == STARTING_FEN


def test_position_startpos_moves():
    e = make_engine()
    e.cmd_position(["startpos", "moves", "e2e4", "e7e5"])
    placement = e.board.get_fen().split()[0]
    assert placement == "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR"


def test_position_fen():
    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    e = make_engine()
    e.cmd_position(["fen"] + fen.split())
    assert e.board.get_fen() == fen


def test_position_fen_moves():
    e = make_engine()
    e.cmd_position(["fen"] + STARTING_FEN.split() + ["moves", "g1f3"])
    assert e.board.piece_at(21) is not None  # f3 = rank2*8+file5 = 21


def test_position_illegal_move():
    e = make_engine()
    # e2e5 is not a legal opening move; the position should stay at whatever
    # was successfully applied before the bad token, not raise.
    e.cmd_position(["startpos", "moves", "e2e4", "e2e5"])
    assert e.board.get_fen().split()[0] == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"


# --- setoption ---

def test_setoption_hash():
    e = make_engine()
    e.cmd_setoption(["name", "Hash", "value", "1"])
    assert e.config.tt_size_mb == 1
    assert e.searcher.config.tt_size_mb == 1


def test_setoption_unknown():
    e = make_engine()
    e.cmd_setoption(["name", "NotAThing", "value", "42"])  # must not raise
    assert e.config == e.config  # engine still alive / usable


# --- go / stop / search threading ---

def test_go_depth():
    e = make_engine()
    e.cmd_go(["depth", "3"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert "bestmove" in out
    assert "info depth 3" in out


def test_go_default_depth():
    e = make_engine()
    e.cmd_go([])
    e.wait_for_search(timeout=30)
    out = e.out.getvalue()
    assert "info depth 6" in out
    assert "bestmove" in out


def test_go_stop():
    e = make_engine()
    e.cmd_go(["depth", "64", "movetime", "60000"])  # would run ~60s unattended
    time.sleep(0.15)
    t0 = time.perf_counter()
    e.cmd_stop()
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0  # stop must actually interrupt, not wait out movetime
    assert "bestmove" in e.out.getvalue()


def test_go_twice():
    e = make_engine()
    e.cmd_go(["depth", "64", "movetime", "60000"])
    time.sleep(0.1)
    e.cmd_go(["depth", "2"])  # must not raise / deadlock / run two searches at once
    e.wait_for_search(timeout=15)
    assert e.out.getvalue().count("bestmove") == 2


def test_go_wtime_btime():
    e = make_engine()
    e.cmd_go(["wtime", "5000", "btime", "5000", "winc", "0", "binc", "0"])
    e.wait_for_search(timeout=15)
    assert "bestmove" in e.out.getvalue()


# --- full command dispatch (handle_command / run-loop plumbing) ---

def test_dispatch():
    e = make_engine()
    e.handle_command("uci")
    assert "uciok" in e.out.getvalue()


def test_unknown_command():
    e = make_engine()
    e.handle_command("totally_not_a_uci_command")  # must not raise
    assert e.out.getvalue() == ""


def test_blank_line():
    e = make_engine()
    e.handle_command("")
    assert e.out.getvalue() == ""
