import io

from lcbot.uci import UCIEngine


def make_engine():
    return UCIEngine(out=io.StringIO())


def test_tablebase_off(tmp_path):
    e = make_engine()
    e.cmd_setoption(["name", "TablebasePath", "value", str(tmp_path)])
    e.cmd_go(["depth", "2"])
    e.wait_for_search(timeout=15)
    assert e.searcher.tablebase is None
    assert "bestmove" in e.out.getvalue()


def test_empty_tablebase_dir(tmp_path):
    e = make_engine()
    e.cmd_setoption(["name", "TablebasePath", "value", str(tmp_path)])
    e.cmd_setoption(["name", "UseTablebase", "value", "true"])
    e.cmd_go(["depth", "2"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert e.searcher.tablebase is not None
    assert "info depth" in out
    assert "bestmove" in out


def test_bad_tablebase_path():
    e = make_engine()
    e.cmd_setoption(["name", "TablebasePath", "value", "/tmp/not-a-real-tb-dir-lc-bot"])
    e.cmd_setoption(["name", "UseTablebase", "value", "true"])
    e.cmd_go(["depth", "2"])
    e.wait_for_search(timeout=15)
    out = e.out.getvalue()
    assert "info string tablebase unavailable" in out
    assert e.searcher.tablebase is None
    assert "info depth" in out
    assert "bestmove" in out


def test_path_change(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    e = make_engine()
    e.cmd_setoption(["name", "UseTablebase", "value", "true"])
    e.cmd_setoption(["name", "TablebasePath", "value", str(dir_a)])
    e.cmd_go(["depth", "1"])
    e.wait_for_search(timeout=15)
    first_tb = e._tablebase
    assert e._tablebase_path == str(dir_a)

    e.cmd_setoption(["name", "TablebasePath", "value", str(dir_b)])
    e.cmd_go(["depth", "1"])
    e.wait_for_search(timeout=15)
    assert e._tablebase_path == str(dir_b)
    assert e._tablebase is not first_tb


def test_quit_closes_tablebase(tmp_path):
    e = make_engine()
    e.cmd_setoption(["name", "TablebasePath", "value", str(tmp_path)])
    e.cmd_setoption(["name", "UseTablebase", "value", "true"])
    e.cmd_go(["depth", "1"])
    e.wait_for_search(timeout=15)
    e._close_tablebase()
    assert e._tablebase is None
