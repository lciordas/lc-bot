"""Pygame GUI for lc-bot — play against the engine (or
another human, or watch engine-vs-engine) with a mouse-driven board.
"""

import argparse
import os
import sys
import threading

import pygame

from board import Board, STARTING_FEN
from constants import BLACK, KING, PIECE_CHARS, SQUARE_NAMES, WHITE
from bitboard import lsb
from move import move_from, move_to, move_to_uci
from movegen import generate_legal_moves
from search import Searcher

SQUARE_SIZE = 100
BOARD_SIZE = SQUARE_SIZE * 8
STATUS_HEIGHT = 40
SCREEN_WIDTH = BOARD_SIZE
SCREEN_HEIGHT = BOARD_SIZE + STATUS_HEIGHT

LIGHT_COLOR = (238, 215, 192)
DARK_COLOR = (176, 124, 100)
SELECTED_COLOR = (246, 246, 105, 160)
LEGAL_DOT_COLOR = (58, 175, 220)
CAPTURE_RING_COLOR = (200, 60, 60)
CHECK_COLOR = (220, 80, 80, 160)
PROMO_BG_COLOR = (245, 245, 245)
STATUS_BG = (30, 30, 30)
STATUS_FG = (230, 230, 230)

TEXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piece_textures")
PIECE_TEXTURE_FILES = {
    "P": "white-pawn.png", "N": "white-knight.png", "B": "white-bishop.png",
    "R": "white-rook.png", "Q": "white-queen.png", "K": "white-king.png",
    "p": "black-pawn.png", "n": "black-knight.png", "b": "black-bishop.png",
    "r": "black-rook.png", "q": "black-queen.png", "k": "black-king.png",
}
PROMO_CHOICES = ("q", "r", "b", "n")  # top-to-bottom order in the on-board picker


# --- pure logic (no pygame, testable) ---

def square_screen_pos(sq: int, flipped: bool = False) -> tuple:
    """Top-left pixel of square `sq`; White at the bottom unless `flipped`."""
    file, rank = sq % 8, sq // 8
    col = (7 - file) if flipped else file
    row = rank if flipped else (7 - rank)
    return col * SQUARE_SIZE, row * SQUARE_SIZE


def screen_pos_to_square(pos: tuple, flipped: bool = False):
    """Square under pixel `pos`, or None if off the board."""
    x, y = pos
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        return None
    col, row = x // SQUARE_SIZE, y // SQUARE_SIZE
    file = (7 - col) if flipped else col
    rank = row if flipped else (7 - row)
    return rank * 8 + file


def find_matching_move(legal_moves, from_sq, to_sq, promo_char=None):
    """The legal move from `from_sq` to `to_sq` (with optional promo char), or None."""
    target = SQUARE_NAMES[from_sq] + SQUARE_NAMES[to_sq] + (promo_char or "")
    for m in legal_moves:
        if move_to_uci(m) == target:
            return m
    return None


def needs_promotion_choice(legal_moves, from_sq, to_sq) -> bool:
    """True if from_sq->to_sq is legal only as a promotion."""
    if find_matching_move(legal_moves, from_sq, to_sq) is not None:
        return False
    return any(move_from(m) == from_sq and move_to(m) == to_sq for m in legal_moves)


def piece_char_at(board, sq: int):
    """FEN piece char on `sq`, or None."""
    bit = 1 << sq
    for color in (WHITE, BLACK):
        pieces = board.pieces[color]
        for pt in range(6):
            if pieces[pt] & bit:
                char = PIECE_CHARS[pt]
                return char if color == WHITE else char.lower()
    return None


def color_at(board, sq: int):
    bit = 1 << sq
    for color in (WHITE, BLACK):
        for pt in range(6):
            if board.pieces[color][pt] & bit:
                return color
    return None


class GameState:
    """Non-rendering game state and the background engine search. No pygame,
    so it can be tested without a display."""

    def __init__(self, white_is_human: bool = True, black_is_human: bool = False,
                 ai_depth: int = None, ai_movetime: float = 1.0):
        self.board = Board(STARTING_FEN)
        self.white_is_human = white_is_human
        self.black_is_human = black_is_human
        self.ai_depth = ai_depth
        self.ai_movetime = ai_movetime
        self.flipped = black_is_human and not white_is_human

        self.selected_sq = None
        self.legal_moves_from_selected = []
        self.pending_promotion = None  # (from_sq, to_sq) awaiting a piece choice
        self.status = ""
        self.game_over = False

        self.searcher = Searcher()
        self._ai_thread = None
        self._ai_result = None  # single-item list, filled in by the background thread

    # --- turn / AI bookkeeping ---

    def human_to_move(self) -> bool:
        return self.white_is_human if self.board.side == WHITE else self.black_is_human

    def is_ai_turn(self) -> bool:
        return not self.game_over and not self.human_to_move()

    def start_ai_move(self) -> None:
        if self._ai_thread is not None or self.game_over:
            return
        self.status = "thinking..."
        self._ai_result = []
        board = self.board

        def run():
            move, _score = self.searcher.search(
                board, max_depth=self.ai_depth or 64,
                movetime=None if self.ai_depth else self.ai_movetime,
            )
            self._ai_result.append(move)

        self._ai_thread = threading.Thread(target=run, daemon=True)
        self._ai_thread.start()

    def poll_ai_move(self) -> None:
        """Play the engine's move once its search has finished."""
        if self._ai_thread is None or self._ai_thread.is_alive():
            return
        self._ai_thread = None
        move = self._ai_result[0] if self._ai_result else 0
        if move:
            self.board.make_move(move)
        self._refresh_game_over()

    # --- move input ---

    def select_square(self, sq) -> None:
        if sq is None or self.game_over or not self.human_to_move():
            self.selected_sq = None
            self.legal_moves_from_selected = []
            return
        if color_at(self.board, sq) == self.board.side:
            self.selected_sq = sq
            self.legal_moves_from_selected = [
                m for m in generate_legal_moves(self.board) if move_from(m) == sq
            ]
        else:
            self.selected_sq = None
            self.legal_moves_from_selected = []

    def attempt_move(self, from_sq, to_sq):
        """Try from_sq -> to_sq. Returns True, False, or "promotion" if a
        piece choice is now pending."""
        if self.game_over or from_sq is None or to_sq is None or from_sq == to_sq:
            return False
        if not self.human_to_move():
            return False
        legal = generate_legal_moves(self.board)
        if needs_promotion_choice(legal, from_sq, to_sq):
            self.pending_promotion = (from_sq, to_sq)
            return "promotion"
        move = find_matching_move(legal, from_sq, to_sq)
        if move is None:
            return False
        self._commit(move)
        return True

    def resolve_promotion(self, promo_char: str) -> bool:
        if self.pending_promotion is None:
            return False
        from_sq, to_sq = self.pending_promotion
        self.pending_promotion = None
        move = find_matching_move(generate_legal_moves(self.board), from_sq, to_sq, promo_char)
        if move is None:
            return False
        self._commit(move)
        return True

    def cancel_promotion(self) -> None:
        self.pending_promotion = None

    def _commit(self, move: int) -> None:
        self.board.make_move(move)
        self.selected_sq = None
        self.legal_moves_from_selected = []
        self._refresh_game_over()

    def _refresh_game_over(self) -> None:
        legal = generate_legal_moves(self.board)
        if not legal:
            if self.board.in_check():
                winner = "White" if self.board.side == BLACK else "Black"
                self.status = f"Checkmate — {winner} wins"
            else:
                self.status = "Stalemate — draw"
            self.game_over = True
        elif self.board.is_draw():
            self.status = "Draw"
            self.game_over = True
        else:
            self.status = ""

    # --- misc controls ---

    def new_game(self) -> None:
        self.board = Board(STARTING_FEN)
        self.selected_sq = None
        self.legal_moves_from_selected = []
        self.pending_promotion = None
        self.status = ""
        self.game_over = False
        self._ai_thread = None
        self.searcher = Searcher()

    def undo(self) -> None:
        if self._ai_thread is not None or not self.board.history:
            return
        self.board.unmake_move()
        self.selected_sq = None
        self.legal_moves_from_selected = []
        self.pending_promotion = None
        self.game_over = False
        self.status = ""


# --- pygame-facing rendering ---

def load_textures(size: int = SQUARE_SIZE) -> dict:
    textures = {}
    for char, filename in PIECE_TEXTURE_FILES.items():
        img = pygame.image.load(os.path.join(TEXTURE_DIR, filename))
        textures[char] = pygame.transform.smoothscale(img, (size, size))
    return textures


def promotion_picker_rects(to_sq: int, flipped: bool) -> list:
    """[(promo_char, Rect), ...] for the picker; stacks upward if it would run
    off the bottom of the board."""
    x, y = square_screen_pos(to_sq, flipped)
    icon_size = SQUARE_SIZE // 2
    total_height = icon_size * len(PROMO_CHOICES)
    start_y = y if y + total_height <= BOARD_SIZE else y + SQUARE_SIZE - total_height
    return [
        (p, pygame.Rect(x, start_y + i * icon_size, icon_size, icon_size))
        for i, p in enumerate(PROMO_CHOICES)
    ]


def draw_board(screen, textures, small_textures, state: GameState) -> None:
    board = state.board
    king_in_check_sq = None
    if board.in_check():
        king_in_check_sq = lsb(board.pieces[board.side][KING])
    legal_targets = {move_to(m) for m in state.legal_moves_from_selected}
    capturing_targets = {
        move_to(m) for m in state.legal_moves_from_selected if piece_char_at(board, move_to(m)) is not None
    }

    for sq in range(64):
        x, y = square_screen_pos(sq, state.flipped)
        rect = pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)
        file, rank = sq % 8, sq // 8
        light = (file + rank) % 2 == 1  # a1 is dark
        pygame.draw.rect(screen, LIGHT_COLOR if light else DARK_COLOR, rect)

        if sq == state.selected_sq:
            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            overlay.fill(SELECTED_COLOR)
            screen.blit(overlay, rect)

        if sq == king_in_check_sq:
            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            overlay.fill(CHECK_COLOR)
            screen.blit(overlay, rect)

        char = piece_char_at(board, sq)
        if char:
            screen.blit(textures[char], rect)

        if sq in legal_targets:
            center = rect.center
            if sq in capturing_targets:
                pygame.draw.circle(screen, CAPTURE_RING_COLOR, center, SQUARE_SIZE // 2 - 4, width=4)
            else:
                pygame.draw.circle(screen, LEGAL_DOT_COLOR, center, SQUARE_SIZE // 6)

    if state.pending_promotion is not None:
        _, to_sq = state.pending_promotion
        mover_is_white = board.side == WHITE  # move not committed yet
        for promo_char, rect in promotion_picker_rects(to_sq, state.flipped):
            pygame.draw.rect(screen, PROMO_BG_COLOR, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, width=1)
            char = promo_char.upper() if mover_is_white else promo_char
            screen.blit(small_textures[char], rect)


def draw_status(screen, font, state: GameState) -> None:
    rect = pygame.Rect(0, BOARD_SIZE, SCREEN_WIDTH, STATUS_HEIGHT)
    pygame.draw.rect(screen, STATUS_BG, rect)
    if state.status:
        text = state.status
    else:
        text = f"{'White' if state.board.side == WHITE else 'Black'} to move"
    label = font.render(text, True, STATUS_FG)
    screen.blit(label, (10, BOARD_SIZE + (STATUS_HEIGHT - label.get_height()) // 2))


def handle_promotion_click(state: GameState, pos) -> bool:
    if state.pending_promotion is None:
        return False
    _, to_sq = state.pending_promotion
    for promo_char, rect in promotion_picker_rects(to_sq, state.flipped):
        if rect.collidepoint(pos):
            state.resolve_promotion(promo_char)
            return True
    state.cancel_promotion()
    return True


def run(args) -> None:
    pygame.init()
    pygame.display.set_caption("lc-bot")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    font = pygame.font.SysFont(None, 24)
    textures = load_textures(SQUARE_SIZE)
    small_textures = load_textures(SQUARE_SIZE // 2)
    clock = pygame.time.Clock()

    state = GameState(
        white_is_human=(args.white == "human"),
        black_is_human=(args.black == "human"),
        ai_depth=args.depth,
        ai_movetime=args.movetime,
    )

    mousedown_sq = None
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n:
                    state.new_game()
                elif event.key == pygame.K_f:
                    state.flipped = not state.flipped
                elif event.key == pygame.K_u:
                    state.undo()
                elif state.pending_promotion is not None and event.unicode.lower() in PROMO_CHOICES:
                    state.resolve_promotion(event.unicode.lower())

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if state.pending_promotion is not None:
                    handle_promotion_click(state, event.pos)
                elif state.human_to_move():
                    sq = screen_pos_to_square(event.pos, state.flipped)
                    if sq is not None and state.selected_sq is not None and sq != state.selected_sq:
                        result = state.attempt_move(state.selected_sq, sq)
                        if result is False:
                            state.select_square(sq)
                        mousedown_sq = None
                    else:
                        state.select_square(sq)
                        mousedown_sq = sq

            elif event.type == pygame.MOUSEBUTTONUP:
                if state.pending_promotion is None and state.human_to_move() and mousedown_sq is not None:
                    sq = screen_pos_to_square(event.pos, state.flipped)
                    if sq is not None and sq != mousedown_sq:
                        state.attempt_move(mousedown_sq, sq)
                mousedown_sq = None

        if state.is_ai_turn():
            state.start_ai_move()
        state.poll_ai_move()

        draw_board(screen, textures, small_textures, state)
        draw_status(screen, font, state)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Play lc-bot via a Pygame board.")
    parser.add_argument("--white", choices=["human", "engine"], default="human")
    parser.add_argument("--black", choices=["human", "engine"], default="engine")
    parser.add_argument("--depth", type=int, default=None, help="fixed engine search depth")
    parser.add_argument("--movetime", type=float, default=1.0,
                         help="engine think time per move in seconds (ignored if --depth is given)")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
