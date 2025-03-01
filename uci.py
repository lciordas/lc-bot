"""UCI (Universal Chess Interface) protocol loop."""

import sys
import threading
import time

from board import Board, STARTING_FEN
from config import EngineConfig
from constants import WHITE
from move import move_to_uci
from movegen import generate_legal_moves
from search import MATE, MATE_THRESHOLD, Searcher

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

        depth = None
        movetime = None  # seconds
        max_nodes = None
        infinite = False
        wtime = btime = winc = binc = None

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
            elif t == "infinite":
                infinite = True; i += 1
            else:
                i += 1  # ignore unsupported tokens (ponder, movestogo, mate, searchmoves, ...)

        if movetime is None and depth is None and not infinite and (wtime is not None or btime is not None):
            my_time = wtime if self.board.side == WHITE else btime
            my_inc = (winc or 0) if self.board.side == WHITE else (binc or 0)
            if my_time is not None:
                movetime = max(0.05, my_time / 30000.0 + my_inc / 1000.0 * 0.8)

        if depth is not None:
            max_depth = depth
        elif infinite or movetime is not None or max_nodes is not None:
            max_depth = 64
        else:
            max_depth = 6  # bare "go" with no limits at all

        self._search_thread = threading.Thread(
            target=self._run_search,
            args=(max_depth, None if infinite else movetime, max_nodes),
            daemon=True,
        )
        self._search_thread.start()

    def cmd_stop(self, _args=None):
        self._stop_search()

    def cmd_quit(self, _args=None):
        self._stop_search()
        sys.exit(0)

    # --- search thread plumbing ---

    def _run_search(self, max_depth, movetime, max_nodes):
        move, _score = self.searcher.search(
            self.board, max_depth=max_depth, movetime=movetime, max_nodes=max_nodes,
            on_info=lambda *a: self._print(format_info_line(*a)),
        )
        self._print(f"bestmove {move_to_uci(move) if move else '0000'}")

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


if __name__ == "__main__":
    UCIEngine().run()
