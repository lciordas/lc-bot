"""Runtime NNUE wiring: load a net, attach an accumulator, hand back an
evaluator with the same signature and conventions as `evaluation.evaluate`.
"""

from evaluation import evaluate as hand_written
from nnue_net import NetParams
from nnue_packed import PackedNet, PackedAccumulator


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
        """Re-sync after the position changed underneath us."""
        if board.nnue is None:
            self.attach(board)
        else:
            board.nnue.refresh(board)
            board.nnue.clear_stack()

    # --- evaluation -------------------------------------------------------
    def __call__(self, board) -> int:
        acc = board.nnue
        if acc is None:                     # not attached: fall back safely
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
