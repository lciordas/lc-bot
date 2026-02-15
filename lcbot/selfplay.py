"""In-process self-play between two engine setups, recording positions for tuning."""

import csv
import os
import time
from dataclasses import dataclass, field

from lcbot.board import Board, STARTING_FEN
from lcbot.config import EngineConfig
from lcbot.constants import BLACK, WHITE
from lcbot.move import move_to_uci
from lcbot.movegen import generate_legal_moves
from lcbot.search import Searcher
from lcbot.uci import find_move_by_uci


@dataclass
class Player:
    """One side's setup. `book` and `tablebase` are used only if the config enables them."""
    config: EngineConfig = field(default_factory=EngineConfig)
    book: object = None
    tablebase: object = None
    max_depth: int = None


@dataclass
class GameRecord:
    result: str    # "1-0" | "0-1" | "1/2-1/2"
    reason: str    # checkmate, stalemate, fifty_move, repetition,
                    # insufficient_material, max_plies
    positions: list  # [(fen_before_move, uci_move), ...]


@dataclass
class MatchSummary:
    games: int
    wins_a: int
    wins_b: int
    draws: int
    score_a: float  # wins_a + 0.5 * draws


def play_game(white=None, black=None, movetime=0.05, max_plies=200, start_fen=STARTING_FEN):
    """Play one game; adjudicated a draw at `max_plies`. `movetime` is seconds per move."""
    white = white or Player()
    black = black or Player()
    board = Board(start_fen)
    searchers = {
        WHITE: Searcher(config=white.config, tablebase=white.tablebase if white.config.use_tablebase else None),
        BLACK: Searcher(config=black.config, tablebase=black.tablebase if black.config.use_tablebase else None),
    }
    players = {WHITE: white, BLACK: black}
    positions = []

    for _ply in range(max_plies):
        if board.is_draw():
            return GameRecord("1/2-1/2", _draw_reason(board), positions)

        legal = generate_legal_moves(board)
        if not legal:
            if board.in_check():
                winner_result = "0-1" if board.side == WHITE else "1-0"
                return GameRecord(winner_result, "checkmate", positions)
            return GameRecord("1/2-1/2", "stalemate", positions)

        player = players[board.side]
        fen_before = board.get_fen()
        move = None
        if player.config.use_opening_book and player.book is not None:
            book_uci = player.book.best_move_uci(board)
            if book_uci is not None:
                move = find_move_by_uci(board, book_uci)
        if move is None:
            move, _score = searchers[board.side].search(
                board, max_depth=player.max_depth or 64, movetime=movetime,
            )

        positions.append((fen_before, move_to_uci(move)))
        board.make_move(move)

    return GameRecord("1/2-1/2", "max_plies", positions)


def _draw_reason(board) -> str:
    if board.halfmove >= 100:
        return "fifty_move"
    if board.is_repetition():
        return "repetition"
    return "insufficient_material"


def play_match(setup_a=None, setup_b=None, games=10, movetime=0.05, max_plies=200, start_fens=None):
    """Play `games`, alternating colours. Returns (records, summary from A's side)."""
    setup_a = setup_a or Player()
    setup_b = setup_b or Player()
    fens = start_fens or [STARTING_FEN]

    records = []
    a_was_white_flags = []
    for i in range(games):
        start_fen = fens[i % len(fens)]
        a_is_white = (i % 2 == 0)
        white, black = (setup_a, setup_b) if a_is_white else (setup_b, setup_a)
        records.append(play_game(white, black, movetime=movetime, max_plies=max_plies, start_fen=start_fen))
        a_was_white_flags.append(a_is_white)

    return records, _summarize(records, a_was_white_flags, games)


def _summarize(records, a_was_white_flags, games) -> MatchSummary:
    wins_a = wins_b = draws = 0
    for record, a_was_white in zip(records, a_was_white_flags):
        if record.result == "1/2-1/2":
            draws += 1
        elif (record.result == "1-0") == a_was_white:
            wins_a += 1
        else:
            wins_b += 1
    return MatchSummary(games, wins_a, wins_b, draws, wins_a + 0.5 * draws)


def log_match_result(path, label_a, label_b, summary, timestamp=None):
    """Append a row to the CSV log at `path`, writing a header if the file is new."""
    is_new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "label_a", "label_b", "games", "wins_a", "wins_b", "draws", "score_a"])
        writer.writerow([
            timestamp if timestamp is not None else time.time(),
            label_a, label_b, summary.games, summary.wins_a, summary.wins_b, summary.draws, summary.score_a,
        ])


if __name__ == "__main__":
    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
        return cond

    ok = True

    fast_config = EngineConfig()
    record = play_game(Player(fast_config), Player(fast_config), movetime=0.05, max_plies=40)
    ok &= check("play_game reaches a terminal result", record.result in ("1-0", "0-1", "1/2-1/2"))
    ok &= check("play_game records at least one position", len(record.positions) > 0)

    records, summary = play_match(Player(fast_config), Player(fast_config), games=2, movetime=0.03, max_plies=20)
    ok &= check("play_match plays the requested number of games", len(records) == 2)
    ok &= check("play_match summary accounts for every game",
                summary.wins_a + summary.wins_b + summary.draws == 2)

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    import sys
    sys.exit(0 if ok else 1)
