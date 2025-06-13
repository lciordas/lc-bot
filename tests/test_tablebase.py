"""Tablebase wrapper against an empty directory: error/fallback paths and python-chess's built-in KvK case."""

import pytest

from board import Board
from tablebase import Tablebase


def test_missing_dir():
    with pytest.raises(FileNotFoundError):
        Tablebase("/tmp/definitely-not-a-real-tb-dir-final-engine")


def test_empty_dir(tmp_path):
    with Tablebase(str(tmp_path)) as tb:
        assert tb is not None


def test_material_not_covered(tmp_path):
    # KQ vs K needs a loaded KQvK table; an empty directory has none.
    b = Board("7k/8/8/8/8/8/8/K5Q1 w - - 0 1")
    with Tablebase(str(tmp_path)) as tb:
        assert tb.probe_wdl(b) is None


def test_kvk(tmp_path):
    b = Board("8/8/8/8/8/8/8/K1k5 w - - 0 1")
    with Tablebase(str(tmp_path)) as tb:
        assert tb.probe_wdl(b) == 0


def test_context_manager(tmp_path):
    with Tablebase(str(tmp_path)) as tb:
        pass
    # second close must not raise
    tb.close()
