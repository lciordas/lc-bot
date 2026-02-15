"""_negamax/_quiescence tablebase probing against fake probers: WDL -> score signs, root never probed, piece-count guard."""

from lcbot.board import Board, STARTING_FEN
from lcbot.search import INF, TB_WIN_SCORE, Searcher


class ConstantWDLTablebase:
    """Always answers the same WDL for every position it's asked about."""

    def __init__(self, wdl):
        self.wdl = wdl
        self.calls = 0

    def probe_wdl(self, board):
        self.calls += 1
        return self.wdl


class NeverTablebase:
    """Always returns no data."""

    def probe_wdl(self, board):
        return None


class RootGuardTablebase:
    """Records whether the root position was probed."""

    def __init__(self, root_fen):
        self.root_fen = root_fen
        self.called_with_root = False

    def probe_wdl(self, board):
        if board.get_fen() == self.root_fen:
            self.called_with_root = True
        return None


FEW_PIECES_FEN = "7k/8/8/8/8/8/8/K5Q1 w - - 0 1"  # 3 pieces, under the probe guard


def test_child_win():
    b = Board(FEW_PIECES_FEN)
    s = Searcher(tablebase=ConstantWDLTablebase(2))  # WDL_WIN
    move, score = s.search(b, max_depth=2)
    assert move != 0
    assert score == -(TB_WIN_SCORE - 1)


def test_child_loss():
    b = Board(FEW_PIECES_FEN)
    s = Searcher(tablebase=ConstantWDLTablebase(-2))  # WDL_LOSS
    move, score = s.search(b, max_depth=2)
    assert move != 0
    assert score == TB_WIN_SCORE - 1


def test_draw():
    b = Board(FEW_PIECES_FEN)
    s = Searcher(tablebase=ConstantWDLTablebase(0))  # WDL_DRAW
    move, score = s.search(b, max_depth=2)
    assert move != 0
    assert score == 0


def test_cursed_blessed():
    b = Board(FEW_PIECES_FEN)
    for wdl in (1, -1):  # WDL_CURSED_WIN, WDL_BLESSED_LOSS
        s = Searcher(tablebase=ConstantWDLTablebase(wdl))
        _move, score = s.search(b, max_depth=2)
        assert score == 0


def test_no_hits_same_as_none():
    b1 = Board(STARTING_FEN)
    b2 = Board(STARTING_FEN)
    plain = Searcher()
    with_empty_tb = Searcher(tablebase=NeverTablebase())
    move1, score1 = plain.search(b1, max_depth=3)
    move2, score2 = with_empty_tb.search(b2, max_depth=3)
    assert move1 == move2
    assert score1 == score2


def test_root_not_probed():
    b = Board(STARTING_FEN)
    guard = RootGuardTablebase(root_fen=b.get_fen())
    s = Searcher(tablebase=guard)
    s.search(b, max_depth=3)
    assert guard.called_with_root is False


def test_too_many_pieces():
    b = Board(STARTING_FEN)
    tb = ConstantWDLTablebase(2)
    s = Searcher(tablebase=tb)
    s.search(b, max_depth=2)
    assert tb.calls == 0


def test_few_pieces_probed():
    b = Board("7k/8/8/8/8/8/8/K5Q1 w - - 0 1")
    tb = ConstantWDLTablebase(0)
    s = Searcher(tablebase=tb)
    s.search(b, max_depth=2)
    assert tb.calls > 0


def test_qsearch_probes():
    """Quiescence must probe too: captures there are how material usually drops into TB range."""
    b = Board("7k/8/8/8/8/8/8/K5Q1 w - - 0 1")
    tb = ConstantWDLTablebase(0)
    s = Searcher(tablebase=tb)
    s._quiescence(b, -INF, INF, ply=1)
    assert tb.calls > 0


def test_qsearch_root_not_probed():
    b = Board("7k/8/8/8/8/8/8/K5Q1 w - - 0 1")
    tb = ConstantWDLTablebase(0)
    s = Searcher(tablebase=tb)
    s._quiescence(b, -INF, INF, ply=0)
    assert tb.calls == 0


def test_no_tablebase():
    b1 = Board(STARTING_FEN)
    b2 = Board(STARTING_FEN)
    a = Searcher(tablebase=None)
    b = Searcher()  # default
    move_a, score_a = a.search(b1, max_depth=3)
    move_b, score_b = b.search(b2, max_depth=3)
    assert move_a == move_b
    assert score_a == score_b
