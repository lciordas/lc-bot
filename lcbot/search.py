"""Negamax alpha-beta search: PVS, quiescence, transposition table, null-move,
LMR, futility/razoring, singular extensions, aspiration windows."""

import sys
import time

from lcbot.bitboard import popcount
from lcbot.board import Board, STARTING_FEN
from lcbot.movegen import generate_legal_captures, generate_legal_moves
from lcbot.move import (
    is_capture, move_flag, move_from, move_to, move_to_uci,
    FLAG_EN_PASSANT, FLAG_PROMO_N, PROMO_FLAG_TO_PIECE,
)
from lcbot.evaluation import evaluate
from lcbot.constants import KNIGHT, BISHOP, ROOK, QUEEN
from lcbot.config import EngineConfig
from lcbot.see import see

sys.setrecursionlimit(10000)

INF = 1_000_000
MATE = 100_000            # score for being mated at the current node
MATE_THRESHOLD = 99_000   # |score| above this is a forced mate
MAX_PLY = 128

# Nodes between time/node limit checks. Low-time budgets can be ~10ms; at
# ~50-90K nps, 64 nodes keeps overshoot to about 1ms.
LIMIT_CHECK_INTERVAL = 64

# Futility margins by depth (index 0 unused). Standard values, untuned.
FUTILITY_MARGIN = (0, 200, 350, 550)
FUTILITY_MAX_DEPTH = 3

RAZOR_MARGIN = 300
RAZOR_MAX_DEPTH = 2

# Initial aspiration half-width (cp); doubles on each fail.
ASPIRATION_WINDOW = 50

# Singular extensions: extend the TT move by a ply if no other move gets near
# its TT score in a reduced-depth null-window search. Requires a deep TT entry
# so the verification searches stay rare.
SE_MIN_DEPTH = 6
SE_TT_DEPTH_MARGIN = 3
SE_MARGIN_PER_PLY = 2
SE_EXTENSION = 1
# An extension cancels the ply decrement, so a line that stays singular would
# never lose depth. Cap extensions per path.
SE_MAX_EXTENSIONS = 16

# Above any eval score, well below MATE_THRESHOLD.
TB_WIN_SCORE = 20_000
TB_PROBE_MAX_PIECES = 7  # Syzygy tables top out at 7-man; cheap popcount guard

# Transposition-table entry flags.
TT_EXACT, TT_LOWER, TT_UPPER = 0, 1, 2

class Searcher:
    """Search state; the TT persists across searches."""

    def __init__(self, config=None, tablebase=None, evaluator=None):
        self.config = config or EngineConfig()
        self.tablebase = tablebase  # a tablebase.Tablebase, or None (disabled)
        # None means the hand-written eval. All static evals go through
        # `_eval` so pruning margins see the same score as leaves.
        self.evaluator = evaluator
        self._eval = evaluator if evaluator is not None else evaluate
        self._tt_max_entries = self._compute_tt_cap(self.config.tt_size_mb)
        self.tt = [None] * self._tt_max_entries
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

    def apply_time_budget(self, movetime, hard_limit) -> None:
        """Set the mid-search time cutoff and restart the clock. Also used on
        ponderhit to apply a budget to a running search."""
        self.start = time.perf_counter()
        self.time_limit = hard_limit if hard_limit is not None else movetime

    @staticmethod
    def _compute_tt_cap(tt_size_mb: int) -> int:
        """TT entry count for `tt_size_mb`, assuming ~120 bytes per slot."""
        return max(64, (tt_size_mb * 1024 * 1024) // 120)

    def resize_tt(self, tt_size_mb: int) -> None:
        """Reallocate the TT for a new Hash size, discarding its contents."""
        self.config.tt_size_mb = tt_size_mb
        self._tt_max_entries = self._compute_tt_cap(tt_size_mb)
        self.tt = [None] * self._tt_max_entries

    # --- public entry ---

    def search(self, board, max_depth=64, movetime=None, max_nodes=None, info=False, on_info=None, hard_limit=None):
        """Iteratively deepen until a limit is hit. Returns (best_move, score).

        `movetime` is the soft limit (no new depth after it); `hard_limit`
        (default `movetime`) aborts mid-search. `on_info(depth, score, nodes,
        elapsed, pv)` is called after each completed depth.
        """
        self.apply_time_budget(movetime, hard_limit)
        self.max_nodes = max_nodes
        self.stop = False
        self.nodes = 0
        self.killers = [[0, 0] for _ in range(MAX_PLY)]
        self.history = [[0] * 64 for _ in range(64)]

        # The accumulator only tracks make_move, so rebuild it for a board
        # set up from outside.
        if self.evaluator is not None:
            self.evaluator.refresh(board)

        legal = generate_legal_moves(board)
        if not legal:
            return 0, 0  # checkmate or stalemate at the root

        best_move = legal[0]
        best_score = 0
        for depth in range(1, max_depth + 1):
            # Aspiration window around the last score; full window at depth 1-2.
            if depth <= 2:
                alpha, beta = -INF, INF
            else:
                window = ASPIRATION_WINDOW
                alpha = max(-INF, best_score - window)
                beta = min(INF, best_score + window)

            while True:
                self.best_move_root = 0
                self.best_score_root = -INF
                score = self._negamax(board, depth, alpha, beta, 0)
                if self.stop:
                    break
                if score <= alpha and alpha > -INF:
                    alpha = max(-INF, alpha - window)
                    window *= 2
                elif score >= beta and beta < INF:
                    beta = min(INF, beta + window)
                    window *= 2
                else:
                    break

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
                break  # forced mate
            if movetime is not None and (time.perf_counter() - self.start) >= movetime:
                # Soft limit reached; don't start another depth.
                break
        return best_move, best_score

    # --- core ---

    def _negamax(self, board, depth, alpha, beta, ply, ext_count=0):
        self.nodes += 1
        if self.nodes % LIMIT_CHECK_INTERVAL == 0:
            self._check_limits()
        if self.stop:
            return 0
        if ply >= MAX_PLY:
            return self._eval(board)

        if ply > 0 and board.is_draw():
            return 0

        # Tablebase probe, not at the root (we need a move there). -ply/+ply
        # prefers faster wins and slower losses, as with mate scores.
        if ply > 0 and self.tablebase is not None and popcount(board.all_occupied) <= TB_PROBE_MAX_PIECES:
            wdl = self.tablebase.probe_wdl(board)
            if wdl is not None:
                if wdl >= 2:
                    return TB_WIN_SCORE - ply
                if wdl <= -2:
                    return -TB_WIN_SCORE + ply
                return 0  # draw, cursed win, or blessed loss

        pv_node = (beta - alpha) > 1
        in_check = board.in_check()
        if in_check:
            depth += 1  # check extension

        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply)

        alpha_orig = alpha
        key = board.zobrist
        tt_move = 0
        tt_entry_depth = 0
        tt_entry_flag = None
        tt_score_adj = 0
        entry = self._tt_lookup(key)
        if entry is not None:
            e_depth, e_flag, e_score, e_move = entry
            tt_move = e_move
            tt_entry_depth = e_depth
            tt_entry_flag = e_flag
            tt_score_adj = self._tt_read(e_score, ply)
            if ply > 0 and e_depth >= depth:
                if e_flag == TT_EXACT:
                    return tt_score_adj
                if e_flag == TT_LOWER and tt_score_adj > alpha:
                    alpha = tt_score_adj
                elif e_flag == TT_UPPER and tt_score_adj < beta:
                    beta = tt_score_adj
                if alpha >= beta:
                    return tt_score_adj

        # Null-move pruning. Skipped with only pawns (zugzwang).
        if (not pv_node and not in_check and depth >= 3 and ply > 0
                and beta < MATE_THRESHOLD and self._has_non_pawn_material(board)):
            r = 3 if depth >= 6 else 2
            board.make_null_move()
            score = -self._negamax(board, depth - 1 - r, -beta, -beta + 1, ply + 1, ext_count)
            board.unmake_null_move()
            if self.stop:
                return 0
            if score >= beta:
                return beta

        # Razoring: eval far below alpha at low depth, drop to quiescence.
        if (not pv_node and not in_check and ply > 0 and 1 <= depth <= RAZOR_MAX_DEPTH
                and beta < MATE_THRESHOLD):
            razor_eval = self._eval(board)
            if razor_eval + RAZOR_MARGIN <= alpha:
                score = self._quiescence(board, alpha, beta, ply)
                if self.stop:
                    return 0
                if score <= alpha:
                    return score

        moves = generate_legal_moves(board)
        if not moves:
            return -MATE + ply if in_check else 0  # checkmate (prefer slower) / stalemate

        moves = self._order_moves(board, moves, tt_move, ply)

        # Singular extensions (see SE_* constants).
        singular_move = 0
        if (tt_move != 0 and moves[0] == tt_move and ply > 0 and not in_check
                and depth >= SE_MIN_DEPTH and ext_count < SE_MAX_EXTENSIONS
                and tt_entry_depth >= depth - SE_TT_DEPTH_MARGIN and tt_entry_flag != TT_UPPER
                and abs(tt_score_adj) < MATE_THRESHOLD):
            singular_beta = tt_score_adj - SE_MARGIN_PER_PLY * depth
            singular_depth = (depth - 1) // 2
            if self._is_tt_move_singular(board, moves, tt_move, singular_beta, singular_depth, ply):
                singular_move = tt_move

        # Futility eval is computed lazily, once per node.
        futility_eval = None
        futility_active = not pv_node and not in_check and 1 <= depth <= FUTILITY_MAX_DEPTH

        best_score = -INF
        best_move = moves[0]
        for i, m in enumerate(moves):
            is_quiet = not (is_capture(m) or move_flag(m) >= FLAG_PROMO_N)
            consider_futility = futility_active and is_quiet and i > 0
            if consider_futility and futility_eval is None:
                futility_eval = self._eval(board)

            # Make the move first: checking moves are never futility-pruned.
            board.make_move(m)
            gives_check = board.in_check()

            if (consider_futility and not gives_check
                    and futility_eval + FUTILITY_MARGIN[depth] <= alpha):
                board.unmake_move()
                continue

            if i == 0:
                ext = SE_EXTENSION if singular_move else 0
                score = -self._negamax(board, depth - 1 + ext, -beta, -alpha, ply + 1, ext_count + ext)
            else:
                # Late-move reduction for quiet, late, non-forcing moves.
                reduction = 0
                if depth >= 3 and i >= 3 and is_quiet and not in_check and not gives_check:
                    reduction = 1 if i < 6 else 2
                score = -self._negamax(board, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1, ext_count)
                # Re-search at full depth/window if it surprises us.
                if score > alpha and (reduction > 0 or score < beta):
                    score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1, ext_count)

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
        if self.nodes % LIMIT_CHECK_INTERVAL == 0:
            self._check_limits()
        if self.stop:
            return 0
        if ply >= MAX_PLY:
            return self._eval(board)

        # Probe here too: captures in quiescence are how material usually
        # drops into tablebase range.
        if ply > 0 and self.tablebase is not None and popcount(board.all_occupied) <= TB_PROBE_MAX_PIECES:
            wdl = self.tablebase.probe_wdl(board)
            if wdl is not None:
                if wdl >= 2:
                    return TB_WIN_SCORE - ply
                if wdl <= -2:
                    return -TB_WIN_SCORE + ply
                return 0

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

        captures = generate_legal_captures(board)
        if not captures and not generate_legal_moves(board):
            # Stalemate. Reachable via razoring, which enters quiescence
            # without checking for legal moves.
            return 0

        stand = self._eval(board)
        if stand >= beta:
            return beta
        if stand > alpha:
            alpha = stand

        for m in self._order_moves(board, captures, 0, ply):
            # Losing captures are sorted last, so stop at the first one.
            if is_capture(m) and see(board, m) < 0:
                break
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
                    # Order by SEE; losing captures go below quiet moves.
                    exchange = see(board, m)
                    s = (20_000_000 + exchange) if exchange >= 0 else exchange
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

    def _is_tt_move_singular(self, board, moves, tt_move, singular_beta, singular_depth, ply):
        """True if no move other than `tt_move` (== moves[0]) reaches
        `singular_beta` in a reduced-depth null-window search."""
        assert moves[0] == tt_move
        for m in moves[1:]:
            board.make_move(m)
            score = -self._negamax(board, singular_depth, -singular_beta, -singular_beta + 1, ply + 1)
            board.unmake_move()
            if self.stop:
                return False
            if score >= singular_beta:
                return False
        return True

    def _store_killer(self, ply, move):
        if move != self.killers[ply][0]:
            self.killers[ply][1] = self.killers[ply][0]
            self.killers[ply][0] = move

    @staticmethod
    def _has_non_pawn_material(board):
        p = board.pieces[board.side]
        return bool(p[KNIGHT] or p[BISHOP] or p[ROOK] or p[QUEEN])

    # --- transposition table (mate scores are stored relative to the node) ---
    #
    # Direct-mapped, slot = key % size; slots store the full key to detect
    # collisions. Depth-preferred replacement, even for the same key, so a
    # shallow SE verification search can't evict a deeper entry.

    def _tt_index(self, key: int) -> int:
        return key % self._tt_max_entries

    def _tt_lookup(self, key):
        """(depth, flag, score, move) for `key`, or None."""
        entry = self.tt[self._tt_index(key)]
        if entry is not None and entry[0] == key:
            return entry[1], entry[2], entry[3], entry[4]
        return None

    def _tt_store(self, key, depth, score, flag, move, ply):
        if score >= MATE_THRESHOLD:
            score += ply
        elif score <= -MATE_THRESHOLD:
            score -= ply
        idx = self._tt_index(key)
        existing = self.tt[idx]
        if existing is None or depth >= existing[1]:
            self.tt[idx] = (key, depth, flag, score, move)

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
            entry = self._tt_lookup(key)
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
