import csv

from board import STARTING_FEN
from book import OpeningBook
from config import EngineConfig
from selfplay import GameRecord, MatchSummary, Player, _summarize, log_match_result, play_game, play_match
from test_book import write_book


def test_game_finishes():
    record = play_game(movetime=0.03, max_plies=40)
    assert record.result in ("1-0", "0-1", "1/2-1/2")
    assert record.reason in (
        "checkmate", "stalemate", "fifty_move", "repetition", "insufficient_material", "max_plies",
    )
    assert len(record.positions) > 0


def test_game_positions():
    record = play_game(movetime=0.03, max_plies=20)
    for fen, uci_move in record.positions:
        assert isinstance(fen, str) and len(fen.split()) == 6
        assert isinstance(uci_move, str) and 4 <= len(uci_move) <= 5


def test_max_plies_draw():
    record = play_game(movetime=0.02, max_plies=2)
    assert record.result == "1/2-1/2"
    assert record.reason == "max_plies"
    assert len(record.positions) == 2


def test_match_game_count():
    records, summary = play_match(games=2, movetime=0.02, max_plies=10)
    assert len(records) == 2
    assert summary.games == 2
    assert summary.wins_a + summary.wins_b + summary.draws == 2


def test_match_symmetric():
    """Only checks that the summary bookkeeping is consistent."""
    records, summary = play_match(games=2, movetime=0.02, max_plies=10)
    assert summary.score_a == summary.wins_a + 0.5 * summary.draws
    assert 0 <= summary.score_a <= summary.games


# --- _summarize ---

def _record(result):
    return GameRecord(result=result, reason="checkmate", positions=[])


def test_summarize_white_win():
    records = [_record("1-0")]
    summary = _summarize(records, a_was_white_flags=[True], games=1)
    assert summary == MatchSummary(games=1, wins_a=1, wins_b=0, draws=0, score_a=1.0)


def test_summarize_black_win():
    records = [_record("0-1")]
    summary = _summarize(records, a_was_white_flags=[False], games=1)
    assert summary == MatchSummary(games=1, wins_a=1, wins_b=0, draws=0, score_a=1.0)


def test_summarize_loss():
    records = [_record("0-1")]
    summary = _summarize(records, a_was_white_flags=[True], games=1)
    assert summary == MatchSummary(games=1, wins_a=0, wins_b=1, draws=0, score_a=0.0)


def test_summarize_draws():
    records = [_record("1/2-1/2"), _record("1/2-1/2")]
    summary = _summarize(records, a_was_white_flags=[True, False], games=2)
    assert summary == MatchSummary(games=2, wins_a=0, wins_b=0, draws=2, score_a=1.0)


def test_summarize_mixed():
    records = [_record("1-0"), _record("0-1"), _record("1/2-1/2")]
    flags = [True, True, False]  # A wins as White, A loses as White, draw
    summary = _summarize(records, a_was_white_flags=flags, games=3)
    assert summary == MatchSummary(games=3, wins_a=1, wins_b=1, draws=1, score_a=1.5)


# --- CSV logging ---

def test_log_creates_file(tmp_path):
    path = tmp_path / "results.csv"
    summary = MatchSummary(games=4, wins_a=2, wins_b=1, draws=1, score_a=2.5)
    log_match_result(str(path), "engine_a", "engine_b", summary, timestamp=1234.0)

    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["timestamp", "label_a", "label_b", "games", "wins_a", "wins_b", "draws", "score_a"]
    assert rows[1] == ["1234.0", "engine_a", "engine_b", "4", "2", "1", "1", "2.5"]


def test_log_appends(tmp_path):
    path = tmp_path / "results.csv"
    summary = MatchSummary(games=2, wins_a=1, wins_b=0, draws=1, score_a=1.5)
    log_match_result(str(path), "a", "b", summary, timestamp=1.0)
    log_match_result(str(path), "a", "c", summary, timestamp=2.0)

    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3  # header + 2 data rows
    assert rows[0][0] == "timestamp"
    assert rows[1][0] == "1.0"
    assert rows[2][0] == "2.0"


# --- Player book/tablebase toggles ---

def test_player_defaults():
    p = Player()
    assert isinstance(p.config, EngineConfig)
    assert p.book is None
    assert p.tablebase is None


def test_players_separate_configs():
    """Guards against a shared mutable default EngineConfig."""
    a, b = Player(), Player()
    a.config.use_opening_book = True
    assert b.config.use_opening_book is False


def test_book_enabled(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    with OpeningBook(path) as book:
        cfg = EngineConfig(use_opening_book=True)
        white = Player(config=cfg, book=book)
        record = play_game(white=white, black=Player(), movetime=0.02, max_plies=1)
        assert record.positions[0] == (STARTING_FEN, "e2e4")


def test_book_disabled(tmp_path):
    path = write_book(tmp_path, [(None, "a2a3", 10)])  # search would never pick a2a3
    with OpeningBook(path) as book:
        white = Player(config=EngineConfig(use_opening_book=False), book=book)
        record = play_game(white=white, black=Player(), movetime=0.05, max_plies=1)
        assert record.positions[0][1] != "a2a3"


class _AlwaysWinTablebase:
    def probe_wdl(self, board):
        return 2  # WDL_WIN, for whoever is to move


class _CallCountingTablebase:
    """Counts probe calls."""

    def __init__(self):
        self.calls = 0

    def probe_wdl(self, board):
        self.calls += 1
        return None


def test_tablebase_passed_to_searcher():
    few_pieces_fen = "7k/8/8/8/8/8/8/K5Q1 w - - 0 1"
    white = Player(config=EngineConfig(use_tablebase=True), tablebase=_AlwaysWinTablebase())
    record = play_game(white=white, black=Player(), movetime=0.02, max_plies=1, start_fen=few_pieces_fen)
    assert len(record.positions) == 1


def test_tablebase_disabled():
    few_pieces_fen = "7k/8/8/8/8/8/8/K5Q1 w - - 0 1"
    tb = _CallCountingTablebase()
    white = Player(config=EngineConfig(use_tablebase=False), tablebase=tb)
    play_game(white=white, black=Player(), movetime=0.05, max_plies=1, start_fen=few_pieces_fen)
    assert tb.calls == 0


def test_tablebase_enabled():
    few_pieces_fen = "7k/8/8/8/8/8/8/K5Q1 w - - 0 1"
    tb = _CallCountingTablebase()
    white = Player(config=EngineConfig(use_tablebase=True), tablebase=tb)
    play_game(white=white, black=Player(), movetime=0.05, max_plies=1, start_fen=few_pieces_fen)
    assert tb.calls > 0
