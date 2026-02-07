"""Tests for gui.py logic: coordinate math, move matching and GameState flow (no rendering)."""

import pytest

import gui
from board import Board, STARTING_FEN
from constants import SQUARE_INDEX, WHITE, BLACK
from move import move_to_uci
from movegen import generate_legal_moves


# --- coordinate math ---

def test_square_pos_round_trip():
    """Guards against swapped flip branches, which map every square to sq ^ 56."""
    for sq in range(64):
        for flipped in (False, True):
            pos = gui.square_screen_pos(sq, flipped)
            assert gui.screen_pos_to_square(pos, flipped) == sq


def test_a1_bottom_left():
    x, y = gui.square_screen_pos(SQUARE_INDEX["a1"], flipped=False)
    assert x == 0
    assert y == gui.BOARD_SIZE - gui.SQUARE_SIZE  # bottom row


def test_h8_top_right():
    x, y = gui.square_screen_pos(SQUARE_INDEX["h8"], flipped=False)
    assert x == gui.BOARD_SIZE - gui.SQUARE_SIZE
    assert y == 0


def test_flipped_a1():
    x, y = gui.square_screen_pos(SQUARE_INDEX["a1"], flipped=True)
    assert x == gui.BOARD_SIZE - gui.SQUARE_SIZE
    assert y == 0


def test_click_outside_board():
    assert gui.screen_pos_to_square((10, gui.BOARD_SIZE + 5), flipped=False) is None  # status bar
    assert gui.screen_pos_to_square((-5, 10), flipped=False) is None


# --- move matching / promotion detection ---

def test_find_move():
    b = Board()
    legal = generate_legal_moves(b)
    m = gui.find_matching_move(legal, SQUARE_INDEX["e2"], SQUARE_INDEX["e4"])
    assert m is not None
    assert move_to_uci(m) == "e2e4"


def test_find_move_illegal():
    b = Board()
    legal = generate_legal_moves(b)
    assert gui.find_matching_move(legal, SQUARE_INDEX["e2"], SQUARE_INDEX["e5"]) is None


def test_needs_promotion_choice():
    b = Board("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    legal = generate_legal_moves(b)
    assert gui.needs_promotion_choice(legal, SQUARE_INDEX["a7"], SQUARE_INDEX["a8"]) is True
    assert gui.needs_promotion_choice(legal, SQUARE_INDEX["h2"], SQUARE_INDEX["h3"]) is False
    assert gui.needs_promotion_choice(legal, SQUARE_INDEX["a7"], SQUARE_INDEX["a6"]) is False


def test_find_move_promotion():
    b = Board("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    legal = generate_legal_moves(b)
    m = gui.find_matching_move(legal, SQUARE_INDEX["a7"], SQUARE_INDEX["a8"], "n")
    assert m is not None
    assert move_to_uci(m) == "a7a8n"


# --- board inspection ---

def test_piece_char_at():
    b = Board("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    assert gui.piece_char_at(b, SQUARE_INDEX["a7"]) == "P"
    assert gui.piece_char_at(b, SQUARE_INDEX["h7"]) == "k"
    assert gui.piece_char_at(b, SQUARE_INDEX["d4"]) is None


def test_color_at():
    b = Board("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    assert gui.color_at(b, SQUARE_INDEX["a7"]) == WHITE
    assert gui.color_at(b, SQUARE_INDEX["h7"]) == BLACK
    assert gui.color_at(b, SQUARE_INDEX["d4"]) is None


# --- promotion picker placement ---

def test_picker_on_board_top():
    rects = gui.promotion_picker_rects(SQUARE_INDEX["a8"], flipped=False)
    for _char, rect in rects:
        assert rect.top >= 0
        assert rect.bottom <= gui.BOARD_SIZE


def test_picker_on_board_bottom():
    """Near the bottom edge the picker must stack upward."""
    rects = gui.promotion_picker_rects(SQUARE_INDEX["a1"], flipped=False)
    for _char, rect in rects:
        assert rect.top >= 0
        assert rect.bottom <= gui.BOARD_SIZE


# --- GameState: turn tracking ---

def test_human_to_move():
    state = gui.GameState(white_is_human=True, black_is_human=False)
    assert state.human_to_move() is True  # white to move, white is human
    assert state.is_ai_turn() is False


def test_is_ai_turn():
    state = gui.GameState(white_is_human=False, black_is_human=True)
    assert state.is_ai_turn() is True


def test_human_vs_human():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.attempt_move(SQUARE_INDEX["e2"], SQUARE_INDEX["e4"])
    assert state.is_ai_turn() is False  # now black to move, also human


# --- GameState: move flow ---

def test_select_own_piece_only():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.select_square(SQUARE_INDEX["e7"])  # black pawn, but white to move
    assert state.selected_sq is None
    state.select_square(SQUARE_INDEX["e2"])  # white pawn, white to move
    assert state.selected_sq == SQUARE_INDEX["e2"]
    assert len(state.legal_moves_from_selected) == 2  # e2e3, e2e4


def test_legal_move():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    result = state.attempt_move(SQUARE_INDEX["e2"], SQUARE_INDEX["e4"])
    assert result is True
    assert gui.piece_char_at(state.board, SQUARE_INDEX["e4"]) == "P"
    assert state.board.side == BLACK
    assert state.selected_sq is None


def test_illegal_move():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    result = state.attempt_move(SQUARE_INDEX["e2"], SQUARE_INDEX["e5"])
    assert result is False
    assert state.board.side == WHITE  # nothing happened


def test_promotion_asks_for_piece():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.board = Board("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    result = state.attempt_move(SQUARE_INDEX["a7"], SQUARE_INDEX["a8"])
    assert result == "promotion"
    assert state.pending_promotion == (SQUARE_INDEX["a7"], SQUARE_INDEX["a8"])
    assert state.board.side == WHITE  # not committed yet


def test_resolve_promotion():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.board = Board("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    state.attempt_move(SQUARE_INDEX["a7"], SQUARE_INDEX["a8"])
    committed = state.resolve_promotion("q")
    assert committed is True
    assert gui.piece_char_at(state.board, SQUARE_INDEX["a8"]) == "Q"
    assert state.pending_promotion is None
    assert state.board.side == BLACK


def test_cancel_promotion():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.board = Board("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    state.attempt_move(SQUARE_INDEX["a7"], SQUARE_INDEX["a8"])
    state.cancel_promotion()
    assert state.pending_promotion is None
    assert state.board.side == WHITE
    assert gui.piece_char_at(state.board, SQUARE_INDEX["a7"]) == "P"


def test_move_on_engine_turn():
    state = gui.GameState(white_is_human=False, black_is_human=True)
    result = state.attempt_move(SQUARE_INDEX["e2"], SQUARE_INDEX["e4"])
    assert result is False
    assert state.board.side == WHITE


# --- GameState: game-over detection ---

def test_checkmate():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.board = Board("4R1k1/5ppp/8/8/8/8/8/6K1 b - - 0 1")
    state._refresh_game_over()
    assert state.game_over is True
    assert "Checkmate" in state.status
    assert "White" in state.status  # white delivered it, black is mated


def test_stalemate():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.board = Board("k7/8/1Q6/2K5/8/8/8/8 b - - 0 1")
    state._refresh_game_over()
    assert state.game_over is True
    assert "Stalemate" in state.status


def test_no_moves_after_game_over():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.board = Board("4R1k1/5ppp/8/8/8/8/8/6K1 b - - 0 1")
    state._refresh_game_over()
    result = state.attempt_move(SQUARE_INDEX["g8"], SQUARE_INDEX["h8"])
    assert result is False


# --- GameState: undo / new game ---

def test_undo():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.attempt_move(SQUARE_INDEX["e2"], SQUARE_INDEX["e4"])
    state.undo()
    assert gui.piece_char_at(state.board, SQUARE_INDEX["e2"]) == "P"
    assert gui.piece_char_at(state.board, SQUARE_INDEX["e4"]) is None
    assert state.board.side == WHITE


def test_undo_empty():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.undo()  # must not raise
    assert state.board.side == WHITE


def test_undo_while_thinking():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.attempt_move(SQUARE_INDEX["e2"], SQUARE_INDEX["e4"])
    state._ai_thread = object()  # pretend a search is running
    state.undo()
    assert gui.piece_char_at(state.board, SQUARE_INDEX["e4"]) == "P"  # unchanged


def test_new_game():
    state = gui.GameState(white_is_human=True, black_is_human=True)
    state.attempt_move(SQUARE_INDEX["e2"], SQUARE_INDEX["e4"])
    state.new_game()
    assert state.board.get_fen().split()[0] == STARTING_FEN.split()[0]
    assert state.game_over is False
    assert state.status == ""
    assert state.selected_sq is None
