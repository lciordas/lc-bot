import io
import time

import pytest
from board import Board, STARTING_FEN
from move import move_to_uci
from search import Searcher
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
    for name in ("Hash", "OwnBook", "BookPath", "UseTablebase", "TablebasePath"):
        assert f"option name {name}" in out
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


def test_setoption_ownbook():
    e = make_engine()
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    assert e.config.use_opening_book is True


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


def test_go_uses_own_clock():
    """White to move: wtime and btime differ, so the resulting budget must
    reflect wtime specifically (proves the wtime/btime -> my_time selection
    picks the mover's own clock, not always the same one)."""
    from time_management import compute_budget

    e = make_engine()
    e.cmd_go(["wtime", "6000", "btime", "500", "winc", "0", "binc", "0"])
    e.wait_for_search(timeout=15)
    expected = compute_budget(6000, 0, moves_to_go=None)
    assert e.searcher.time_limit == pytest.approx(expected.hard_limit)


def test_go_movestogo():
    from time_management import compute_budget

    e = make_engine()
    e.cmd_go(["wtime", "1500", "btime", "1500", "winc", "0", "binc", "0", "movestogo", "5"])
    e.wait_for_search(timeout=15)
    expected = compute_budget(1500, 0, moves_to_go=5)
    assert e.searcher.time_limit == pytest.approx(expected.hard_limit)


def test_go_depth_no_clock():
    """An explicit depth limit must bypass wtime/btime budgeting entirely
    (time_limit should stay None, i.e. no hard cutoff from the clock)."""
    e = make_engine()
    e.cmd_go(["depth", "2", "wtime", "60000", "btime", "60000"])
    e.wait_for_search(timeout=15)
    assert e.searcher.time_limit is None


# --- pondering (go ponder / ponderhit) ---

def test_bestmove_ponder():
    e = make_engine()
    e.cmd_go(["depth", "3"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert " ponder " in out.splitlines()[-1]


def test_bestmove_short_pv():
    """At depth 1, the TT only ever gets an entry for the root position
    itself -- there's nothing to extract a second PV move from, so no
    "ponder" suffix should be printed."""
    e = make_engine()
    e.cmd_go(["depth", "1"])
    e.wait_for_search(timeout=15)
    line = e.out.getvalue().splitlines()[-1]
    assert line.startswith("bestmove")
    assert "ponder" not in line


def test_ponder_unbounded():
    """A ponder search must behave like `go infinite` time-wise: no hard
    cutoff applied while pondering, even though wtime/btime were given --
    ponder time doesn't count against the clock."""
    e = make_engine()
    e.cmd_go(["ponder", "wtime", "60000", "btime", "60000"])
    assert e._pondering is True
    assert e.searcher.time_limit is None
    e.cmd_stop()


def test_ponder_stashes_budget():
    from time_management import compute_budget

    e = make_engine()
    e.cmd_go(["ponder", "wtime", "6000", "btime", "500", "winc", "0", "binc", "0"])
    expected = compute_budget(6000, 0, moves_to_go=None)  # white to move: wtime is "my_time"
    movetime, hard_limit = e._ponder_budget
    assert movetime == pytest.approx(expected.soft_limit)
    assert hard_limit == pytest.approx(expected.hard_limit)
    e.cmd_stop()


def test_ponder_no_clock():
    e = make_engine()
    e.cmd_go(["ponder"])
    assert e._pondering is True
    assert e._ponder_budget == (None, None)
    e.cmd_stop()


def test_ponderhit():
    e = make_engine()
    e.cmd_go(["ponder", "wtime", "3000", "btime", "3000", "winc", "0", "binc", "0"])
    assert e.searcher.time_limit is None  # unbounded while pondering
    e.cmd_ponderhit()
    assert e._pondering is False
    assert e.searcher.time_limit is not None  # the stashed budget is now live
    e.wait_for_search(timeout=15)
    assert "bestmove" in e.out.getvalue()


def test_ponderhit_resets_clock():
    """The budget's hard_limit is measured from searcher.start -- if
    ponderhit didn't reset searcher.start too, whatever time pondering had
    already been running for would wrongly count against the post-ponderhit
    budget, understating how much time is actually left."""
    e = make_engine()
    e.cmd_go(["ponder", "wtime", "3000", "btime", "3000", "winc", "0", "binc", "0"])
    time.sleep(0.2)
    before = e.searcher.start
    e.cmd_ponderhit()
    assert e.searcher.start > before
    e.cmd_stop()


def test_ponderhit_idle():
    e = make_engine()
    e.cmd_ponderhit()  # must not raise
    assert e._pondering is False


def test_ponderhit_after_normal_go():
    """ponderhit only makes sense following a `go ponder`; if the last `go`
    wasn't a ponder search, it must not disturb the running (or finished)
    search's time limit."""
    e = make_engine()
    e.cmd_go(["depth", "64", "movetime", "60000"])
    time.sleep(0.1)
    limit_before = e.searcher.time_limit
    e.cmd_ponderhit()
    assert e.searcher.time_limit == limit_before
    e.cmd_stop()


def test_stop_while_pondering():
    """UCI: the opponent didn't play the predicted move -- the GUI sends
    `stop` (not `ponderhit`). The engine must still interrupt promptly and
    must not leave `_pondering` stuck True for a later, unrelated command."""
    e = make_engine()
    e.cmd_go(["ponder", "wtime", "60000", "btime", "60000"])
    time.sleep(0.1)
    t0 = time.perf_counter()
    e.cmd_stop()
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0
    assert e._pondering is False
    assert "bestmove" in e.out.getvalue()


def test_ponder_default_depth():
    """A bare `go` defaults to depth 6 (see test_go_default_depth)
    -- `go ponder` with no other limits must not fall into that same default,
    since pondering is meant to run until ponderhit/stop, not stop itself
    after 6 plies."""
    e = make_engine()
    e.cmd_go(["ponder"])
    max_depth = e._search_thread._args[0]
    e.cmd_stop()
    assert max_depth == 64


def test_ponder_depth_waits():
    """an earlier version let an explicit `depth` cap override ponder's
        unbounded-depth requirement, so `go ponder depth N` could finish
        quickly and print bestmove/ponder before any stop/ponderhit ever
        arrived -- violating the exact "must never volunteer" contract
        pondering exists to guarantee.
    """
    e = make_engine()
    e.cmd_go(["ponder", "depth", "3"])
    assert "bestmove" not in e.out.getvalue()
    e.cmd_stop()
    assert "bestmove" in e.out.getvalue()


def test_infinite_depth_waits():
    """Same fix, the other pre-existing instance of the identical hole
    (found alongside the ponder case above, while looking at the shared
    max_depth computation): `go infinite depth N` must not self-limit by
    the explicit depth either."""
    e = make_engine()
    e.cmd_go(["infinite", "depth", "3"])
    assert "bestmove" not in e.out.getvalue()
    e.cmd_stop()
    assert "bestmove" in e.out.getvalue()


def test_ponder_move_board(monkeypatch):
    """an earlier
        version re-read self.board for the ponder-move PV lookup after
        search() returned. cmd_position doesn't stop an in-flight search first,
        so a concurrent `position` command reassigning self.board in that
        window would make the PV lookup run against the wrong position
        entirely. Verified directly by spying on exactly which board object
        _principal_variation is called with, and confirming it's the object
        the search itself ran on -- not whatever self.board points to by the
        time the callback fires -- while simulating the race by having the
        (mocked) search reassign self.board just as it returns, exactly the
        window the fix closes.
    """
    e = make_engine()
    e.cmd_position(["startpos"])
    board_used_for_search = e.board

    captured_boards = []
    real_pv = Searcher._principal_variation

    def spy(self, board, max_len=12):
        captured_boards.append(board)
        return real_pv(self, board, max_len=max_len)

    monkeypatch.setattr(Searcher, "_principal_variation", spy)

    real_search = e.searcher.search

    def racing_search(board, **kwargs):
        result = real_search(board, **kwargs)
        e.board = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")  # simulates a concurrent cmd_position
        return result

    e.searcher.search = racing_search
    e.cmd_go(["depth", "3"])
    e.wait_for_search(timeout=15)

    # 3 calls: one per completed depth, from search()'s own on_info-driven
    # PV computation (used for the "info ... pv ..." lines) -- not 4. The
    # fix this test also covers (capturing the last on_info's PV instead of
    # recomputing after search() returns) means _run_search itself no
    # longer makes an extra, separate call here at all.
    assert len(captured_boards) == 3
    assert all(b is board_used_for_search for b in captured_boards)
    assert captured_boards[0] is not e.board  # confirms the simulated race really happened


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
