"""Fast pin-aware generate_legal_moves vs the make/unmake reference generator.

Compares full move sets, which is stronger than perft node counts.
"""

from board import Board
from bitboard import lsb
from constants import KING
from move import move_from
from movegen import _check_and_pin_info, _generate_legal_moves_reference, generate_legal_moves
from perft import PERFT_SUITE


def _assert_matches_reference(board, context=""):
    fast = sorted(generate_legal_moves(board))
    reference = sorted(_generate_legal_moves_reference(board))
    assert fast == reference, (
        f"mismatch at {board.get_fen()} ({context}): "
        f"fast-only={sorted(set(fast) - set(reference))} "
        f"reference-only={sorted(set(reference) - set(fast))}"
    )


def test_perft_positions():
    for name, fen, _expected in PERFT_SUITE:
        _assert_matches_reference(Board(fen), context=name)


def test_random_walks():
    """Random walks chosen from the reference generator, compared at every ply."""
    import random

    rng = random.Random(0xC0FFEE)
    for name, fen, _expected in PERFT_SUITE:
        for walk in range(6):
            board = Board(fen)
            for ply in range(40):
                reference = _generate_legal_moves_reference(board)
                if not reference:
                    break
                _assert_matches_reference(board, context=f"{name} walk={walk} ply={ply}")
                move = rng.choice(reference)
                board.make_move(move)


# --- hand-constructed edge cases ---

def test_double_check():
    # Knight d3 and rook e8 both check the king on e1.
    board = Board("4r3/8/8/8/8/3n4/8/2R1K3 w - - 0 1")
    checkers_count, *_ = _check_and_pin_info(board)
    assert checkers_count == 2, "test position doesn't actually produce double check"
    _assert_matches_reference(board, context="double check")
    king_sq = lsb(board.pieces[board.side][KING])
    non_king_moves = [m for m in generate_legal_moves(board) if move_from(m) != king_sq]
    assert non_king_moves == []


def test_pinned_bishop():
    # Bishop f1 pinned along rank 1 by rook h1: it has no legal moves.
    board = Board("4k3/8/8/8/8/8/8/4KB1r w - - 0 1")
    checkers_count, _mask, pinned_bb, _rays = _check_and_pin_info(board)
    assert checkers_count == 0
    assert pinned_bb != 0, "test position doesn't actually produce a pin"
    _assert_matches_reference(board, context="pinned bishop")


def test_pinned_rook():
    # Rook e4 pinned on the e-file can still move along it.
    board = Board("4r3/8/8/8/4R3/8/8/4K3 w - - 0 1")
    checkers_count, _mask, pinned_bb, _rays = _check_and_pin_info(board)
    assert checkers_count == 0
    assert pinned_bb != 0, "test position doesn't actually produce a pin"
    _assert_matches_reference(board, context="pinned rook")
    rook_moves = [m for m in generate_legal_moves(board) if move_from(m) == lsb(board.pieces[board.side][3])]
    assert rook_moves != []  # 3 = ROOK piece-type index


def test_single_check():
    # Rook e8 checks; knight d2 can block on e4.
    board = Board("4r3/8/8/8/8/8/3N4/4K3 w - - 0 1")
    checkers_count, *_ = _check_and_pin_info(board)
    assert checkers_count == 1
    _assert_matches_reference(board, context="single check, blockable")


def test_en_passant_discovered_check():
    """exd6 e.p. clears d5 and e5 at once, exposing Kh5 to Ra5 along the rank."""
    board = Board("4k3/8/8/r2pP2K/8/8/8/8 w - d6 0 1")
    pseudo_ep_candidates = [
        m for m in _generate_legal_moves_reference(board)
    ]
    assert pseudo_ep_candidates != [], "test position has no legal replies at all"
    _assert_matches_reference(board, context="en passant discovered check")

    from move import move_to_uci
    fast_uci = {move_to_uci(m) for m in generate_legal_moves(board)}
    assert "e5d6" not in fast_uci, "illegal en passant capture (discovered check) was not excluded"
