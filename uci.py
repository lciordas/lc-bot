"""UCI protocol loop over stdin/stdout.

Search runs on a background thread; `stop` sets `Searcher.stop`, a plain bool
the search polls (no lock needed under the GIL).
"""

import sys
import threading

from board import Board, STARTING_FEN
from book import OpeningBook
from config import EngineConfig
from constants import WHITE
from move import move_to_uci
from movegen import generate_legal_moves
from search import MATE, MATE_THRESHOLD, Searcher
from tablebase import Tablebase
from time_management import compute_budget

ENGINE_NAME = "lc-bot"
ENGINE_AUTHOR = "Lucas Ciordas"


def find_move_by_uci(board, uci_str):
    """The legal move matching a UCI string like "e7e8q", or None."""
    for m in generate_legal_moves(board):
        if move_to_uci(m) == uci_str:
            return m
    return None


def format_info_line(depth, score, nodes, elapsed, pv_moves):
    nps = int(nodes / elapsed) if elapsed > 0 else 0
    if abs(score) >= MATE_THRESHOLD:
        mate_in = (MATE - abs(score) + 1) // 2
        score_str = f"mate {mate_in if score > 0 else -mate_in}"
    else:
        score_str = f"cp {score}"
    line = f"info depth {depth} score {score_str} nodes {nodes} nps {nps} time {int(elapsed * 1000)}"
    pv_str = " ".join(move_to_uci(m) for m in pv_moves)
    if pv_str:
        line += f" pv {pv_str}"
    return line


class UCIEngine:
    def __init__(self, out=None):
        self.out = out or sys.stdout
        self.config = EngineConfig()
        self.board = Board(STARTING_FEN)
        self.searcher = Searcher(config=self.config)
        self._search_thread = None
        self._book = None
        self._book_path = None
        self._tablebase = None
        self._tablebase_path = None
        self._pondering = False
        self._ponder_budget = None

    def _print(self, line: str) -> None:
        self.out.write(line + "\n")
        self.out.flush()

    # --- command handlers ---

    def cmd_uci(self, _args=None):
        self._print(f"id name {ENGINE_NAME}")
        self._print(f"id author {ENGINE_AUTHOR}")
        for line in EngineConfig.uci_options():
            self._print(line)
        self._print("uciok")

    def cmd_isready(self, _args=None):
        self._print("readyok")

    def cmd_ucinewgame(self, _args=None):
        self._stop_search()
        self.board = Board(STARTING_FEN)
        self.searcher = Searcher(config=self.config)
        self._pondering = False
        self._ponder_budget = None

    def cmd_setoption(self, tokens):
        # setoption name <name...> value <value...>
        if not tokens or tokens[0] != "name":
            return
        try:
            value_idx = tokens.index("value")
        except ValueError:
            value_idx = len(tokens)
        name = " ".join(tokens[1:value_idx])
        value = " ".join(tokens[value_idx + 1:]) if value_idx < len(tokens) else ""
        if not self.config.set_uci_option(name, value):
            return
        if name == "Hash":
            self.searcher.resize_tt(self.config.tt_size_mb)

    def cmd_position(self, tokens):
        if not tokens:
            return
        if tokens[0] == "startpos":
            self.board = Board(STARTING_FEN)
            idx = 1
        elif tokens[0] == "fen":
            idx = 1
            fen_fields = []
            while idx < len(tokens) and tokens[idx] != "moves":
                fen_fields.append(tokens[idx])
                idx += 1
            self.board = Board(" ".join(fen_fields))
        else:
            return

        if idx < len(tokens) and tokens[idx] == "moves":
            for mv_str in tokens[idx + 1:]:
                m = find_move_by_uci(self.board, mv_str)
                if m is None:
                    break  # illegal move token: keep the position so far
                self.board.make_move(m)

    def cmd_go(self, tokens):
        self._stop_search()
        self._sync_tablebase()

        depth = None
        movetime = None  # seconds
        max_nodes = None
        infinite = False
        ponder = False
        wtime = btime = winc = binc = movestogo = None

        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t == "depth" and i + 1 < len(tokens):
                depth = int(tokens[i + 1]); i += 2
            elif t == "movetime" and i + 1 < len(tokens):
                movetime = int(tokens[i + 1]) / 1000.0; i += 2
            elif t == "nodes" and i + 1 < len(tokens):
                max_nodes = int(tokens[i + 1]); i += 2
            elif t == "wtime" and i + 1 < len(tokens):
                wtime = int(tokens[i + 1]); i += 2
            elif t == "btime" and i + 1 < len(tokens):
                btime = int(tokens[i + 1]); i += 2
            elif t == "winc" and i + 1 < len(tokens):
                winc = int(tokens[i + 1]); i += 2
            elif t == "binc" and i + 1 < len(tokens):
                binc = int(tokens[i + 1]); i += 2
            elif t == "movestogo" and i + 1 < len(tokens):
                movestogo = int(tokens[i + 1]); i += 2
            elif t == "infinite":
                infinite = True; i += 1
            elif t == "ponder":
                ponder = True; i += 1
            else:
                i += 1  # ignore unsupported tokens (mate, searchmoves, ...)

        # infinite/ponder must not send bestmove before stop/ponderhit, so
        # skip the book in both modes.
        if not infinite and not ponder:
            book_move = self._try_book_move()
            if book_move is not None:
                self._print(f"bestmove {book_move}")
                return

        # Also computed for ponder searches, which stash it for ponderhit.
        hard_limit = None
        if movetime is None and depth is None and not infinite and (wtime is not None or btime is not None):
            my_time = wtime if self.board.side == WHITE else btime
            my_inc = (winc or 0) if self.board.side == WHITE else (binc or 0)
            if my_time is not None:
                budget = compute_budget(my_time, my_inc, moves_to_go=movestogo)
                movetime = budget.soft_limit
                hard_limit = budget.hard_limit

        if infinite or ponder:
            # Ignore any depth limit: finishing early would send bestmove
            # before stop/ponderhit.
            max_depth = 64
        elif depth is not None:
            max_depth = depth
        elif movetime is not None or max_nodes is not None:
            max_depth = 64
        else:
            max_depth = 6  # bare "go" with no limits at all

        self._pondering = ponder
        self._ponder_budget = (movetime, hard_limit) if ponder else None
        actual_movetime = None if (infinite or ponder) else movetime
        actual_hard_limit = None if ponder else hard_limit

        self._search_thread = threading.Thread(
            target=self._run_search,
            args=(max_depth, actual_movetime, max_nodes, actual_hard_limit),
            daemon=True,
        )
        self._search_thread.start()

    def cmd_ponderhit(self, _args=None):
        """Apply the stashed time budget to the running ponder search.

        The budget's clock starts now, so the opponent's think time isn't
        charged to us.
        """
        if not self._pondering:
            return
        self._pondering = False
        movetime, hard_limit = self._ponder_budget or (None, None)
        self.searcher.apply_time_budget(movetime, hard_limit)

    def cmd_stop(self, _args=None):
        self._stop_search()

    def cmd_quit(self, _args=None):
        self._stop_search()
        self._close_book()
        self._close_tablebase()
        sys.exit(0)

    # --- opening book ---

    def _try_book_move(self):
        """Book move for the current position as a UCI string, or None.

        Load errors are reported via `info string`, and the move is checked
        against our own move generator before it is returned.
        """
        if not self.config.use_opening_book or not self.config.book_path:
            return None
        try:
            book = self._book_for_path(self.config.book_path)
        except OSError as e:
            self._print(f"info string opening book unavailable ({self.config.book_path}): {e}")
            return None
        try:
            book_uci = book.best_move_uci(self.board)
        except Exception as e:
            self._print(f"info string opening book lookup failed: {e}")
            return None
        if book_uci is None:
            return None
        if find_move_by_uci(self.board, book_uci) is None:
            self._print(f"info string opening book returned an illegal move ({book_uci}); ignoring")
            return None
        return book_uci

    def _book_for_path(self, path):
        if self._book is None or self._book_path != path:
            self._close_book()
            self._book = OpeningBook(path)
            self._book_path = path
        return self._book

    def _close_book(self):
        if self._book is not None:
            self._book.close()
        self._book = None
        self._book_path = None

    # --- endgame tablebase ---

    def _sync_tablebase(self):
        """Point the searcher at the configured tablebase, or None. A bad path
        is reported and treated as disabled."""
        if not self.config.use_tablebase or not self.config.tablebase_path:
            self.searcher.tablebase = None
            return
        path = self.config.tablebase_path
        if self._tablebase is None or self._tablebase_path != path:
            self._close_tablebase()
            try:
                self._tablebase = Tablebase(path)
                self._tablebase_path = path
            except OSError as e:
                self._print(f"info string tablebase unavailable ({path}): {e}")
        self.searcher.tablebase = self._tablebase

    def _close_tablebase(self):
        if self._tablebase is not None:
            self._tablebase.close()
        self._tablebase = None
        self._tablebase_path = None

    # --- search thread plumbing ---

    def _run_search(self, max_depth, movetime, max_nodes, hard_limit=None):
        # Always print a bestmove, even if search() raises, or the GUI hangs.
        # An exception skips unmake_move calls and leaves the board corrupted,
        # so restore it from the FEN before picking a fallback move.
        fen_before = self.board.get_fen()
        # cmd_position can reassign self.board while we search, so keep our own reference.
        board_for_search = self.board
        # PV of the last completed iteration, reused for the ponder move.
        last_pv = []

        def on_info(depth, score, nodes, elapsed, pv_moves):
            last_pv[:] = pv_moves
            self._print(format_info_line(depth, score, nodes, elapsed, pv_moves))

        try:
            move, _score = self.searcher.search(
                board_for_search, max_depth=max_depth, movetime=movetime, max_nodes=max_nodes,
                hard_limit=hard_limit, on_info=on_info,
            )
        except Exception as e:
            self._print(f"info string search error, falling back to a legal move: {e}")
            self.board = Board(fen_before)
            legal = generate_legal_moves(self.board)
            move = legal[0] if legal else 0
            last_pv = []
        self._pondering = False
        line = f"bestmove {move_to_uci(move) if move else '0000'}"
        if move and len(last_pv) >= 2:
            # Predicted opponent reply: the second PV move is what a GUI
            # would pre-search on its next `go ponder` -- standard UCI
            # ponder-move sourcing.
            line += f" ponder {move_to_uci(last_pv[1])}"
        self._print(line)

    def wait_for_search(self, timeout=30.0):
        """Block until the current search finishes, without stopping it."""
        if self._search_thread:
            self._search_thread.join(timeout=timeout)

    def _stop_search(self, timeout=5.0):
        if self._search_thread and self._search_thread.is_alive():
            self.searcher.stop = True
            self._search_thread.join(timeout=timeout)
        self._search_thread = None

    # --- main loop ---

    _HANDLERS = {
        "uci": "cmd_uci",
        "isready": "cmd_isready",
        "ucinewgame": "cmd_ucinewgame",
        "position": "cmd_position",
        "go": "cmd_go",
        "stop": "cmd_stop",
        "ponderhit": "cmd_ponderhit",
        "setoption": "cmd_setoption",
        "quit": "cmd_quit",
    }

    def handle_command(self, line: str) -> None:
        tokens = line.split()
        if not tokens:
            return
        handler_name = self._HANDLERS.get(tokens[0])
        if handler_name is None:
            return  # UCI: ignore unknown commands
        getattr(self, handler_name)(tokens[1:])

    def run(self) -> None:
        try:
            for line in sys.stdin:
                self.handle_command(line.strip())
        finally:
            self._stop_search(timeout=2.0)
            self._close_book()
            self._close_tablebase()


if __name__ == "__main__":
    UCIEngine().run()
