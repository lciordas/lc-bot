from config import EngineConfig


def test_defaults():
    c = EngineConfig()
    assert c.tt_size_mb == 64


def test_set_int():
    c = EngineConfig()
    assert c.set_uci_option("Hash", "128") is True
    assert c.tt_size_mb == 128


def test_set_unknown():
    c = EngineConfig()
    assert c.set_uci_option("NotARealOption", "1") is False
    assert c == EngineConfig()  # nothing mutated


def test_uci_options_lists_all():
    lines = EngineConfig.uci_options()
    for name in ("Hash",):
        assert any(name in line for line in lines), f"{name} missing from uci_options()"


def test_constructor_args():
    c = EngineConfig(tt_size_mb=16)
    assert c.tt_size_mb == 16
