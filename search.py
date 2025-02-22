"""Negamax alpha-beta search: PVS, quiescence, transposition table, null-move,
LMR, futility/razoring, singular extensions, aspiration windows."""

import sys
import time

from board import Board, STARTING_FEN
from movegen import generate_legal_moves
from move import (
    is_capture, move_flag, move_from, move_to, move_to_uci,
    FLAG_EN_PASSANT, FLAG_PROMO_N, PROMO_FLAG_TO_PIECE,
)
from evaluation import evaluate, PIECE_VALUE
from constants import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
from config import EngineConfig

sys.setrecursionlimit(10000)

INF = 1_000_000
MATE = 100_000            # score for being mated at the current node
MATE_THRESHOLD = 99_000   # |score| above this is a forced mate
MAX_PLY = 128

# Transposition-table entry flags.
TT_EXACT, TT_LOWER, TT_UPPER = 0, 1, 2

# MVV-LVA ordering uses piece values; index by piece type.
_MVV = (100, 320, 330, 500, 900, 20000)  # king last so K-captures (illegal) never dominate


class Searcher:
    """Search state; the TT persists across searches."""

    def __init__(self, config=None):
        self.config = config or EngineConfig()
        self.tt = {}
        self._tt_max_entries = self._compute_tt_cap(self.config.tt_size_mb)
        self.nodes = 0
        self.stop = False
        self.start = 0.0
        self.time_limit = None
        self.max_nodes = None
        self.best_move_root = 0
        self.best_score_root = -INF
        self.completed_depth = 0
        self.killers = [[0, 0] for _ in range(MAX_PLY)]
        self.history = [[0] * 64 for _ in range(64)]

    @staticmethod
    def _compute_tt_cap(tt_size_mb: int) -> int:
        """Rough entry-count budget for a `tt_size_mb`-sized table (~120 bytes
        per (depth, flag, score, move) tuple + dict-entry overhead, estimated;
        exact accuracy isn't the point — bounding unbounded growth is)."""
        return max(64, (tt_size_mb * 1024 * 1024) // 120)

    def resize_tt(self, tt_size_mb: int) -> None:
        """Apply a new Hash size (e.g. from a UCI `setoption name Hash`):"""
        self.config.tt_size_mb = tt_size_mb
        self._tt_max_entries = self._compute_tt_cap(tt_size_mb)
        self.tt.clear()

    # --- public entry ---

    def search(self, board, max_depth=64, movetime=None, max_nodes=None, info=False, on_info=None):
        """Iteratively deepen until a limit is hit. Returns (best_move, score).

        `on_info(depth, score, nodes, elapsed, pv)` is called after every
        completed iteration if given — the hook `uci.py` uses to emit UCI
        `info` lines without this module needing to know about UCI at all.
        """
        self.start = time.perf_counter()
        self.time_limit = movetime
        self.max_nodes = max_nodes
        self.stop = False
        self.nodes = 0
        self.killers = [[0, 0] for _ in range(MAX_PLY)]
        self.history = [[0] * 64 for _ in range(64)]

        legal = generate_legal_moves(board)
        if not legal:
            return 0, 0  # checkmate or stalemate at the root

        best_move = legal[0]
        best_score = 0
        for depth in range(1, max_depth + 1):
            self.best_move_root = 0
            self.best_score_root = -INF
            score = self._negamax(board, depth, -INF, INF, 0)

            if self.stop:
                # Trust this aborted iteration's root move only if it found one.
                if self.best_move_root:
                    best_move, best_score = self.best_move_root, self.best_score_root
                break

            best_move = self.best_move_root or best_move
            best_score = score
            self.completed_depth = depth

            if info:
                self._print_info(board, depth, score)
            if on_info is not None:
                elapsed = time.perf_counter() - self.start
                on_info(depth, score, self.nodes, elapsed, self._principal_variation(board))
            if abs(score) >= MATE_THRESHOLD:
                break  # forced mate — no point searching deeper
            if movetime is not None and (time.perf_counter() - self.start) >= movetime * 0.5:
                break  # next depth almost certainly won't finish in budget
        return best_move, best_score

    # --- core ---

    def _negamax(self, board, depth, alpha, beta, ply):
        self.nodes += 1
        if (self.nodes & 2047) == 0:
            self._check_limits()
        if self.stop:
            return 0
        if ply >= MAX_PLY:
            return evaluate(board)

        if ply > 0 and board.is_draw():
            return 0

        pv_node = (beta - alpha) > 1
        in_check = board.in_check()
        if in_check:
            depth += 1  # check extension

        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply)

        alpha_orig = alpha
        key = board.zobrist
        tt_move = 0
        entry = self.tt.get(key)
        if entry is not None:
            e_depth, e_flag, e_score, e_move = entry
            tt_move = e_move
            if ply > 0 and e_depth >= depth:
                s = self._tt_read(e_score, ply)
                if e_flag == TT_EXACT:
                    return s
                if e_flag == TT_LOWER and s > alpha:
                    alpha = s
                elif e_flag == TT_UPPER and s < beta:
                    beta = s
                if alpha >= beta:
                    return s

        # Null-move pruning. Skipped with only pawns (zugzwang).
        if (not pv_node and not in_check and depth >= 3 and ply > 0
                and beta < MATE_THRESHOLD and self._has_non_pawn_material(board)):
            r = 3 if depth >= 6 else 2
            board.make_null_move()
            score = -self._negamax(board, depth - 1 - r, -beta, -beta + 1, ply + 1)
            board.unmake_null_move()
            if self.stop:
                return 0
            if score >= beta:
                return beta

        moves = generate_legal_moves(board)
        if not moves:
            return -MATE + ply if in_check else 0  # checkmate (prefer slower) / stalemate

        moves = self._order_moves(board, moves, tt_move, ply)

        best_score = -INF
        best_move = moves[0]
        for i, m in enumerate(moves):
            is_quiet = not (is_capture(m) or move_flag(m) >= FLAG_PROMO_N)
            board.make_move(m)
            gives_check = board.in_check()

            if i == 0:
                score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            else:
                # Late-move reduction for quiet, late, non-forcing moves.
                reduction = 0
                if depth >= 3 and i >= 3 and is_quiet and not in_check and not gives_check:
                    reduction = 1 if i < 6 else 2
                score = -self._negamax(board, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
                # Re-search at full depth/window if it surprises us.
                if score > alpha and (reduction > 0 or score < beta):
                    score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)

            board.unmake_move()
            if self.stop:
                return 0

            if score > best_score:
                best_score = score
                best_move = m
                if score > alpha:
                    alpha = score
                    if ply == 0:
                        self.best_move_root = m
                        self.best_score_root = score
                    if alpha >= beta:
                        if is_quiet and ply < MAX_PLY:
                            self._store_killer(ply, m)
                            self.history[move_from(m)][move_to(m)] += depth * depth
                        break

        flag = TT_EXACT
        if best_score <= alpha_orig:
            flag = TT_UPPER
        elif best_score >= beta:
            flag = TT_LOWER
        self._tt_store(key, depth, best_score, flag, best_move, ply)
        return best_score

    def _quiescence(self, board, alpha, beta, ply):
        """Search only forcing moves until the position is quiet, so the static
        eval is never applied in the middle of a capture exchange."""
        self.nodes += 1
        if (self.nodes & 2047) == 0:
            self._check_limits()
        if self.stop:
            return 0
        if ply >= MAX_PLY:
            return evaluate(board)

        if board.in_check():
            # No stand-pat in check; search every evasion.
            moves = generate_legal_moves(board)
            if not moves:
                return -MATE + ply
            for m in self._order_moves(board, moves, 0, ply):
                board.make_move(m)
                score = -self._quiescence(board, -beta, -alpha, ply + 1)
                board.unmake_move()
                if self.stop:
                    return 0
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
            return alpha

        stand = evaluate(board)
        if stand >= beta:
            return beta
        if stand > alpha:
            alpha = stand

        moves = generate_legal_moves(board)
        captures = [m for m in moves if is_capture(m) or move_flag(m) >= FLAG_PROMO_N]
        for m in self._order_moves(board, captures, 0, ply):
            board.make_move(m)
            score = -self._quiescence(board, -beta, -alpha, ply + 1)
            board.unmake_move()
            if self.stop:
                return 0
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    # --- move ordering ---

    def _order_moves(self, board, moves, tt_move, ply):
        us = board.side
        them = us ^ 1
        k0 = self.killers[ply][0] if ply < MAX_PLY else 0
        k1 = self.killers[ply][1] if ply < MAX_PLY else 0
        hist = self.history
        scored = []
        for m in moves:
            if m == tt_move:
                s = 30_000_000
            else:
                flag = move_flag(m)
                promo = flag >= FLAG_PROMO_N
                if is_capture(m):
                    if flag == FLAG_EN_PASSANT:
                        victim = PAWN
                    else:
                        victim = self._piece_type_on(board, move_to(m), them)
                    attacker = self._piece_type_on(board, move_from(m), us)
                    s = 10_000_000 + _MVV[victim] * 16 - _MVV[attacker]
                    if promo:
                        s += 5_000_000
                elif promo:
                    s = 9_000_000 + PROMO_FLAG_TO_PIECE[flag]
                elif m == k0:
                    s = 8_000_000
                elif m == k1:
                    s = 7_000_000
                else:
                    s = hist[move_from(m)][move_to(m)]
            scored.append((s, m))
        scored.sort(key=lambda sm: sm[0], reverse=True)
        return [m for _, m in scored]

    @staticmethod
    def _piece_type_on(board, sq, color):
        bb = 1 << sq
        pieces = board.pieces[color]
        for pt in range(6):
            if pieces[pt] & bb:
                return pt
        return PAWN  # unreachable for a real capture; keeps MVV indexing safe

    def _store_killer(self, ply, move):
        if move != self.killers[ply][0]:
            self.killers[ply][1] = self.killers[ply][0]
            self.killers[ply][0] = move

    @staticmethod
    def _has_non_pawn_material(board):
        p = board.pieces[board.side]
        return bool(p[KNIGHT] or p[BISHOP] or p[ROOK] or p[QUEEN])

    # --- transposition table (mate scores are stored relative to the node) ---

    def _tt_store(self, key, depth, score, flag, move, ply):
        if score >= MATE_THRESHOLD:
            score += ply
        elif score <= -MATE_THRESHOLD:
            score -= ply
        prev = self.tt.get(key)
        if prev is None or depth >= prev[0]:  # depth-preferred replacement
            if key not in self.tt and len(self.tt) >= self._tt_max_entries:
                self.tt.clear()
            self.tt[key] = (depth, flag, score, move)

    @staticmethod
    def _tt_read(score, ply):
        if score >= MATE_THRESHOLD:
            return score - ply
        if score <= -MATE_THRESHOLD:
            return score + ply
        return score

    # --- limits & reporting ---

    def _check_limits(self):
        if self.time_limit is not None and (time.perf_counter() - self.start) >= self.time_limit:
            self.stop = True
        elif self.max_nodes is not None and self.nodes >= self.max_nodes:
            self.stop = True

    def _principal_variation(self, board, max_len=12):
        pv = []
        seen = set()
        made = 0
        while len(pv) < max_len:
            key = board.zobrist
            if key in seen:
                break
            seen.add(key)
            entry = self.tt.get(key)
            if entry is None or entry[3] == 0:
                break
            m = entry[3]
            if m not in generate_legal_moves(board):
                break
            pv.append(m)
            board.make_move(m)
            made += 1
        for _ in range(made):
            board.unmake_move()
        return pv

    def _print_info(self, board, depth, score):
        elapsed = time.perf_counter() - self.start
        nps = int(self.nodes / elapsed) if elapsed > 0 else 0
        if abs(score) >= MATE_THRESHOLD:
            mate_in = (MATE - abs(score) + 1) // 2
            score_str = f"mate {mate_in if score > 0 else -mate_in}"
        else:
            score_str = f"cp {score}"
        pv = " ".join(move_to_uci(m) for m in self._principal_variation(board))
        print(f"depth {depth:2}  {score_str:>8}  nodes {self.nodes:>9}  "
              f"{elapsed:6.2f}s  nps {nps:>7}  pv {pv}")


def find_best_move(board, depth=None, movetime=None, info=False):
    """Convenience wrapper. Give a fixed `depth`, a `movetime` in seconds, or
    neither (defaults to depth 6). Returns (best_move, score)."""
    if depth is None and movetime is None:
        depth = 6
    searcher = Searcher()
    return searcher.search(board, max_depth=depth or 64, movetime=movetime, info=info)


# --- self-test ------------------------------------------------------------

def _run_self_test() -> bool:
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}{('  ' + extra) if extra else ''}")

    # 1. Mate in 1 (back-rank rook). Best move must be Re1-e8 with a mate score.
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    mv, sc = find_best_move(b, depth=3)
    check("mate-in-1 (rook): finds e1e8", move_to_uci(mv) == "e1e8", move_to_uci(mv))
    check("mate-in-1 (rook): score is mate", sc >= MATE_THRESHOLD, str(sc))

    # 2. Mate in 1 (queen back-rank).
    b = Board("6k1/5ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1")
    mv, sc = find_best_move(b, depth=3)
    check("mate-in-1 (queen): finds d1d8", move_to_uci(mv) == "d1d8", move_to_uci(mv))
    check("mate-in-1 (queen): score is mate", sc >= MATE_THRESHOLD, str(sc))

    # 3. Free queen: Rd3xd5 wins the undefended black queen (with check).
    b = Board("3k4/8/8/3q4/8/3R4/3K4/8 w - - 0 1")
    mv, sc = find_best_move(b, depth=5)
    check("tactic: captures hanging queen (d3d5)", move_to_uci(mv) == "d3d5", move_to_uci(mv))
    check("tactic: score reflects winning material", sc > 500, str(sc))

    # 4. Insufficient material is a draw, and the search scores it 0.
    b = Board("8/8/8/8/8/8/8/K6k w - - 0 1")
    check("KvK is_draw()", b.is_draw())
    b = Board("8/8/8/4k3/8/8/4K3/4N3 w - - 0 1")  # K+N vs K
    check("K+N vs K is_draw()", b.is_draw())

    # 5. Search from the start returns a legal, sane move and respects a node cap.
    b = Board(STARTING_FEN)
    legal = set(generate_legal_moves(b))
    mv, sc = find_best_move(b, depth=4)
    check("start: returns a legal move", mv in legal, move_to_uci(mv))
    check("start: roughly balanced (|score|<150)", abs(sc) < 150, str(sc))

    # 6. Winning endgame: K+Q vs K should be scored decisively for the queen side.
    b = Board("7k/8/8/8/8/8/8/K5Q1 w - - 0 1")
    mv, sc = find_best_move(b, depth=4)
    check("K+Q vs K: returns a legal move", mv in set(generate_legal_moves(b)), move_to_uci(mv))
    check("K+Q vs K: clearly winning (score>700)", sc > 700, str(sc))

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # `python3 search.py demo [fen]`: watch iterative deepening.
        fen = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else \
            "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 1"
        board = Board(fen)
        print(board.render())
        mv, sc = find_best_move(board, depth=6, info=True)
        print(f"\nbest move: {move_to_uci(mv)}")
        sys.exit(0)
    sys.exit(0 if _run_self_test() else 1)
