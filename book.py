"""Polyglot opening-book lookup, via python-chess's `chess.polyglot` reader.

Polyglot uses its own Zobrist key table, unrelated to zobrist.py.
"""

import random as _random

import chess
import chess.polyglot


class OpeningBook:
    """An open Polyglot .bin file. Not thread-safe."""

    def __init__(self, path: str):
        self._reader = chess.polyglot.open_reader(path)

    def close(self) -> None:
        self._reader.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def best_move_uci(self, board, rng=None) -> str | None:
        """Weighted-random book move for `board` as a UCI string, or None.

        `rng` defaults to the `random` module; pass one for deterministic tests.
        """
        cb = chess.Board(board.get_fen())
        entries = list(self._reader.find_all(cb))
        if not entries:
            return None
        rng = rng or _random
        weights = [e.weight for e in entries]
        if sum(weights) <= 0:
            choice = rng.choice(entries)
        else:
            choice = rng.choices(entries, weights=weights, k=1)[0]
        return choice.move.uci()


if __name__ == "__main__":
    import struct
    import sys
    import tempfile
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from board import STARTING_FEN, Board

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
        return cond

    def raises_file_not_found(path):
        try:
            OpeningBook(path)
        except FileNotFoundError:
            return True
        except Exception:
            return False
        return False

    ok = True

    start_key = chess.polyglot.zobrist_hash(chess.Board())
    entries = sorted([
        (start_key, chess.Move.from_uci("e2e4"), 50, 0),
        (start_key, chess.Move.from_uci("d2d4"), 30, 0),
        (start_key, chess.Move.from_uci("g1f3"), 1, 0),
    ], key=lambda e: e[0])

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        for key, move, weight, learn in entries:
            # Polyglot raw move: to_square in bits 0-5, from_square in bits 6-11.
            raw_move = move.to_square | (move.from_square << 6)
            f.write(struct.pack(">QHHI", key, raw_move, weight, learn))
        book_path = f.name

    with OpeningBook(book_path) as book:
        b = Board(STARTING_FEN)
        seen = set()
        for _ in range(50):
            seen.add(book.best_move_uci(b, rng=_random.Random()))
        ok &= check("weighted choice stays within book entries",
                    seen <= {"e2e4", "d2d4", "g1f3"})
        ok &= check("all three entries reachable given enough draws", len(seen) >= 2)

        deterministic = book.best_move_uci(b, rng=_random.Random(1))
        ok &= check("deterministic rng gives a reproducible pick",
                    deterministic == book.best_move_uci(b, rng=_random.Random(1)))

        after_e4 = Board(STARTING_FEN)
        from movegen import generate_legal_moves
        from move import move_to_uci
        mv = next(m for m in generate_legal_moves(after_e4) if move_to_uci(m) == "e2e4")
        after_e4.make_move(mv)
        ok &= check("position not in book returns None", book.best_move_uci(after_e4) is None)

    ok &= check("missing file raises rather than silently returning empty",
                raises_file_not_found("/tmp/definitely-not-a-real-book-xyz.bin"))

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)
