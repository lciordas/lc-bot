import random
import struct

import chess
import chess.polyglot
import pytest

from board import STARTING_FEN, Board
from book import OpeningBook
from move import move_to_uci
from movegen import generate_legal_moves


def write_book(tmp_path, entries):
    """Write a key-sorted Polyglot .bin from (fen or None, uci, weight) entries; return its path."""
    packed = []
    for fen, uci_str, weight in entries:
        cb = chess.Board(fen) if fen else chess.Board()
        key = chess.polyglot.zobrist_hash(cb)
        move = chess.Move.from_uci(uci_str)
        raw_move = move.to_square | (move.from_square << 6)
        packed.append((key, raw_move, weight, 0))
    packed.sort(key=lambda e: e[0])

    path = tmp_path / "book.bin"
    with open(path, "wb") as f:
        for key, raw_move, weight, learn in packed:
            f.write(struct.pack(">QHHI", key, raw_move, weight, learn))
    return str(path)


def test_single_entry(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    with OpeningBook(path) as book:
        b = Board(STARTING_FEN)
        assert book.best_move_uci(b) == "e2e4"


def test_weighted_choice(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 99), (None, "a2a3", 1)])
    with OpeningBook(path) as book:
        b = Board(STARTING_FEN)
        picks = [book.best_move_uci(b, rng=random.Random(seed)) for seed in range(200)]
        assert picks.count("e2e4") > picks.count("a2a3")
        assert set(picks) == {"e2e4", "a2a3"}


def test_seeded_rng(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 50), (None, "d2d4", 50)])
    with OpeningBook(path) as book:
        b = Board(STARTING_FEN)
        first = book.best_move_uci(b, rng=random.Random(7))
        second = book.best_move_uci(b, rng=random.Random(7))
        assert first == second


def test_not_in_book(tmp_path):
    path = write_book(tmp_path, [(None, "e2e4", 10)])
    with OpeningBook(path) as book:
        b = Board(STARTING_FEN)
        mv = next(m for m in generate_legal_moves(b) if move_to_uci(m) == "g1f3")
        b.make_move(mv)
        assert book.best_move_uci(b) is None


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        OpeningBook("/tmp/definitely-not-a-real-book-xyz-final-engine.bin")


def test_only_legal_moves(tmp_path):
    kiwipete = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    path = write_book(tmp_path, [(kiwipete, "e1g1", 10)])  # kingside castle, only legal there
    with OpeningBook(path) as book:
        start = Board(STARTING_FEN)
        assert book.best_move_uci(start) is None
