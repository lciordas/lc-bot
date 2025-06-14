from config import EngineConfig


def test_defaults():
    c = EngineConfig()
    assert c.use_opening_book is False
    assert c.use_tablebase is False
    assert c.book_path == ""
    assert c.tablebase_path == ""
    assert c.tt_size_mb == 64


def test_set_bool_true():
    c = EngineConfig()
    for truthy in ("true", "True", "1", "yes"):
        c.use_opening_book = False
        assert c.set_uci_option("OwnBook", truthy) is True
        assert c.use_opening_book is True


def test_set_bool_false():
    c = EngineConfig(use_tablebase=True)
    assert c.set_uci_option("UseTablebase", "false") is True
    assert c.use_tablebase is False


def test_set_int():
    c = EngineConfig()
    assert c.set_uci_option("Hash", "128") is True
    assert c.tt_size_mb == 128


def test_set_str():
    c = EngineConfig()
    assert c.set_uci_option("BookPath", "/tmp/book.bin") is True
    assert c.book_path == "/tmp/book.bin"
    assert c.set_uci_option("TablebasePath", "/tmp/tb") is True
    assert c.tablebase_path == "/tmp/tb"


def test_set_unknown():
    c = EngineConfig()
    assert c.set_uci_option("NotARealOption", "1") is False
    assert c == EngineConfig()  # nothing mutated


def test_uci_options_lists_all():
    lines = EngineConfig.uci_options()
    for name in ("Hash", "OwnBook", "BookPath", "UseTablebase", "TablebasePath"):
        assert any(name in line for line in lines), f"{name} missing from uci_options()"


def test_constructor_args():
    a = EngineConfig(use_opening_book=True, use_tablebase=False)
    b = EngineConfig(use_opening_book=False, use_tablebase=True)
    assert a.use_opening_book and not a.use_tablebase
    assert b.use_tablebase and not b.use_opening_book
