"""Float NNUE accumulator: the per-perspective first-layer sum, updated
incrementally. A reference for the packed version in nnue_packed.py.

push() saves state before a move and pop() restores it on unmake.
"""

from lcbot.constants import WHITE
from lcbot.features import feature_index, active_features


class FloatAccumulator:
    """Two lists of N floats, one per perspective."""

    __slots__ = ("net", "aw", "ab", "_stack")

    def __init__(self, net):
        self.net = net
        self.aw = list(net.bias)
        self.ab = list(net.bias)
        self._stack = []

    # --- construction ----------------------------------------------------
    def refresh(self, board):
        """Rebuild both perspectives from scratch."""
        net = self.net
        self.aw = list(net.bias)
        self.ab = list(net.bias)
        W, N = net.W, net.N
        for f in active_features(board, WHITE):
            row = W[f]
            for k in range(N):
                self.aw[k] += row[k]
        for f in active_features(board, 1 - WHITE):
            row = W[f]
            for k in range(N):
                self.ab[k] += row[k]

    # --- incremental updates ---------------------------------------------
    def add(self, colour, pt, sq):
        net = self.net
        N = net.N
        rw = net.W[feature_index(WHITE, colour, pt, sq)]
        rb = net.W[feature_index(1 - WHITE, colour, pt, sq)]
        aw, ab = self.aw, self.ab
        for k in range(N):
            aw[k] += rw[k]
            ab[k] += rb[k]

    def remove(self, colour, pt, sq):
        net = self.net
        N = net.N
        rw = net.W[feature_index(WHITE, colour, pt, sq)]
        rb = net.W[feature_index(1 - WHITE, colour, pt, sq)]
        aw, ab = self.aw, self.ab
        for k in range(N):
            aw[k] -= rw[k]
            ab[k] -= rb[k]

    # --- make/unmake stack -----------------------------------------------
    def push(self):
        self._stack.append((list(self.aw), list(self.ab)))

    def pop(self):
        self.aw, self.ab = self._stack.pop()

    def clear_stack(self):
        self._stack.clear()

    # --- evaluation -------------------------------------------------------
    def raw(self, side_to_move):
        """Side-to-move-relative net output, before scale and clamp."""
        from lcbot.nnue_ref import crelu
        net = self.net
        us, them = ((self.aw, self.ab) if side_to_move == WHITE
                    else (self.ab, self.aw))
        v = net.v
        return sum(v[k] * (crelu(us[k]) - crelu(them[k])) for k in range(net.N))

    def cp(self, side_to_move):
        raw = self.raw(side_to_move) * self.net.scale
        v = int(raw) if raw >= 0 else -int(-raw)
        c = self.net.clampcp
        return -c if v < -c else (c if v > c else v)
