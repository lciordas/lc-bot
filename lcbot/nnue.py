"""NNUE evaluator: a drop-in for `evaluation.evaluate` (side-to-move cp).

The accumulator only tracks moves played on the board, so call `refresh`
whenever the position is set from outside the search.
"""

import os

from lcbot.evaluation import evaluate as hand_written
from lcbot.nnue_net import NetParams
from lcbot.nnue_packed import PackedNet, PackedAccumulator

# Best measured net (hybrid, output layer damped x0.3). Used when no NNUEPath is set.
DEFAULT_NET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "nets", "sf_hybrid_adv_damped.json")


class NNUEEvaluator:
    """Callable with the same contract as `evaluation.evaluate(board)`."""

    __slots__ = ("pnet", "mode", "_acc")

    def __init__(self, pnet: PackedNet):
        self.pnet = pnet
        self.mode = pnet.mode
        self._acc = None

    # --- lifetime ---------------------------------------------------------
    def attach(self, board):
        """Bind a fresh accumulator to `board` and sync it to the position."""
        acc = PackedAccumulator(self.pnet)
        acc.refresh(board)
        board.nnue = acc
        self._acc = acc
        return acc

    def detach(self, board):
        board.nnue = None
        self._acc = None

    def refresh(self, board):
        """Re-sync after the position changed underneath us.

        Re-attaches if the board's accumulator was built for a different net;
        its lane layout would not match this net.
        """
        if board.nnue is None or board.nnue.pnet is not self.pnet:
            self.attach(board)
        else:
            board.nnue.refresh(board)
            board.nnue.clear_stack()

    # --- evaluation -------------------------------------------------------
    def __call__(self, board) -> int:
        acc = board.nnue
        if acc is None or acc.pnet is not self.pnet:   # not ours: rebuild safely
            acc = self.attach(board)
        nn = self.pnet.cp(acc.acc, board.side)
        if self.mode == "pure":
            return nn
        return hand_written(board) + nn


def load_evaluator(path: str, mode: str = None) -> NNUEEvaluator:
    """Load a float net from `path`, quantise it, and wrap it."""
    net = NetParams.load(path)
    if mode is not None and mode != net.mode:
        net.mode = mode
    return NNUEEvaluator(PackedNet(net))


def evaluator_from_net(net: NetParams) -> NNUEEvaluator:
    return NNUEEvaluator(PackedNet(net))
