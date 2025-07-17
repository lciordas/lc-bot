import io

from test_book import write_book
from uci import UCIEngine


def make_engine():
    return UCIEngine(out=io.StringIO())


def test_book_move(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    e = make_engine()
    e.cmd_setoption(["name", "BookPath", "value", str(path)])
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    e.cmd_go(["depth", "10"])
    out = e.out.getvalue()
    assert out.strip() == "bestmove e2e4"
    assert "info depth" not in out
    assert e._search_thread is None


def test_ownbook_off(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    e = make_engine()
    e.cmd_setoption(["name", "BookPath", "value", str(path)])
    e.cmd_go(["depth", "2"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert "info depth" in out
    assert "bestmove" in out


def test_out_of_book(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    e = make_engine()
    e.cmd_setoption(["name", "BookPath", "value", str(path)])
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    e.cmd_position(["startpos", "moves", "g1f3"])  # not the book's keyed position
    e.cmd_go(["depth", "2"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert "info depth" in out
    assert "bestmove" in out


def test_bad_book_path(tmp_path):
    e = make_engine()
    e.cmd_setoption(["name", "BookPath", "value", "/tmp/not-a-real-book-final-engine.bin"])
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    e.cmd_go(["depth", "2"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert "info string opening book unavailable" in out
    assert "info depth" in out
    assert "bestmove" in out


def test_book_path_change(tmp_path):
    path_a = write_book(tmp_path, [(None, "e2e4", 10)])
    b_dir = tmp_path / "b"
    b_dir.mkdir()
    path_b = write_book(b_dir, [(None, "d2d4", 10)])

    e = make_engine()
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    e.cmd_setoption(["name", "BookPath", "value", str(path_a)])
    e.cmd_go(["depth", "1"])
    assert "bestmove e2e4" in e.out.getvalue()

    e.out = io.StringIO()
    e.cmd_setoption(["name", "BookPath", "value", str(path_b)])
    e.cmd_go(["depth", "1"])
    assert "bestmove d2d4" in e.out.getvalue()


def test_quit_closes_book(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    e = make_engine()
    e.cmd_setoption(["name", "BookPath", "value", str(path)])
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    e.cmd_go(["depth", "1"])
    e._close_book()
    assert e._book is None


def test_infinite_no_book(tmp_path):
    """`go infinite` must not send bestmove before `stop`, even on a book hit."""
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    e = make_engine()
    e.cmd_setoption(["name", "BookPath", "value", str(path)])
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    e.cmd_go(["infinite"])
    assert "bestmove" not in e.out.getvalue()
    e.cmd_stop()
    assert "bestmove" in e.out.getvalue()  # only after stop


def test_ponder_no_book(tmp_path):
    """`go ponder` must not send bestmove before `ponderhit`/`stop`, even on a book hit."""
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    e = make_engine()
    e.cmd_setoption(["name", "BookPath", "value", str(path)])
    e.cmd_setoption(["name", "OwnBook", "value", "true"])
    e.cmd_go(["ponder", "wtime", "60000", "btime", "60000"])
    assert "bestmove" not in e.out.getvalue()
    e.cmd_stop()
    assert "bestmove" in e.out.getvalue()  # only after stop


class _IllegalMoveBook:
    """Book returning an illegal move (e.g. a hash mismatch); a real .bin can't produce one."""

    def best_move_uci(self, board):
        return "a1a5"


def test_illegal_book_move():
    e = make_engine()
    e.config.use_opening_book = True
    e.config.book_path = "fake"
    e._book = _IllegalMoveBook()
    e._book_path = "fake"
    e.cmd_go(["depth", "2"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert "info string opening book returned an illegal move" in out
    assert "info depth" in out
    assert "bestmove a1a5" not in out
