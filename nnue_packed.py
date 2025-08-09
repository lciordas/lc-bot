"""Packed integer NNUE: the whole accumulator (both perspectives) is one
Python int of 16-bit lanes, so a feature change is one big-int add.
"""

from constants import WHITE, BLACK, PIECE_TYPES
from features import feature_index

L = 16                        # bits per lane
VBITS = L - 1                 # bit 15 is the borrow guard
BIAS = 1 << (VBITS - 1)       # 2^14, offset-binary zero
ONES = (1 << VBITS) - 1
M16 = (1 << L) - 1            # 2^16 - 1, the horizontal-sum modulus
SUM_LIMIT = M16 - 1           # 65534
EXCURSION_LIMIT = BIAS - 384  # headroom below the guard bit

# Max count per piece type for one side, counting promotions.
MAX_COUNT = (8, 10, 10, 10, 9, 1)   # P N B R Q K


def _packlanes(vals):
    """Pack per-lane integers (possibly negative) into one int."""
    r = 0
    for i, v in enumerate(vals):
        r += v << (L * i)
    return r


def _rep(val, n):
    r = 0
    for _ in range(n):
        r = (r << L) | val
    return r


def unpacklanes(x, n):
    m = M16
    return [(x >> (L * i)) & m for i in range(n)]


class PackedNet:
    """Quantised, packed form of a NetParams. Built once, then read-only."""

    __slots__ = ("N", "P", "K", "lanes", "half", "rows", "base", "gp", "G",
                 "H", "VAL", "LO", "GH", "MASKLO", "clampcp", "mode",
                 "out_scale", "net")

    def __init__(self, net, gain=None):
        self.net = net
        N = self.N = net.N
        self.clampcp = net.clampcp
        self.mode = net.mode
        self.lanes = lanes = 2 * N
        self.half = N * L

        # --- unit ordering: positive output weights first ------------------
        v = net.v
        pos = [k for k in range(N) if v[k] > 0]
        neg = [k for k in range(N) if v[k] <= 0]
        self.P = P = len(pos)

        # --- choose the gain K --------------------------------------------
        # Searched downward: the excursion bound depends on the quantised
        # weights, which depend on K.
        self.K = K = gain if gain is not None else self._pick_gain(pos, neg)
        G = [max(1, round(K * abs(v[k]))) for k in range(N)]
        self.G = G

        # --- lane assignment ----------------------------------------------
        # lane_of[(unit, perspective)] -> lane index
        lane_of = {}
        for i, k in enumerate(pos):
            lane_of[(k, WHITE)] = i
            lane_of[(k, BLACK)] = N + i
        for i, k in enumerate(neg):
            lane_of[(k, BLACK)] = P + i
            lane_of[(k, WHITE)] = N + P + i

        gains = [0] * lanes
        for (k, _persp), ln in lane_of.items():
            gains[ln] = G[k]
        assert sum(gains[:N]) <= SUM_LIMIT, "block0 gain sum overflows hsum"
        assert sum(gains[N:]) <= SUM_LIMIT, "block1 gain sum overflows hsum"

        # --- packed constants ---------------------------------------------
        self.gp = _packlanes(gains)
        self.H = _rep(1 << VBITS, lanes)
        self.VAL = _rep(ONES, lanes)
        self.LO = _rep(BIAS, lanes)
        self.GH = self.gp | self.H
        self.MASKLO = (1 << self.half) - 1

        # --- base (bias lanes) --------------------------------------------
        blane = [0] * lanes
        for k in range(N):
            q = round(G[k] * net.bias[k])
            blane[lane_of[(k, WHITE)]] = BIAS + q
            blane[lane_of[(k, BLACK)]] = BIAS + q
        self.base = _packlanes(blane)

        # --- rows: one packed int per (colour, piece type, square) ---------
        # Indexed by colour*384 + piece_type*64 + square. Each row covers both
        # perspectives, so a piece change is one add.
        W = net.W
        rows = [0] * 768
        for colour in (WHITE, BLACK):
            for pt in PIECE_TYPES:
                for sq in range(64):
                    fw = feature_index(WHITE, colour, pt, sq)
                    fb = feature_index(BLACK, colour, pt, sq)
                    rw, rb = W[fw], W[fb]
                    lane = [0] * lanes
                    for k in range(N):
                        lane[lane_of[(k, WHITE)]] = round(G[k] * rw[k])
                        lane[lane_of[(k, BLACK)]] = round(G[k] * rb[k])
                    rows[colour * 384 + pt * 64 + sq] = _packlanes(lane)
        self.rows = rows

        # nn_cp = trunc(raw * out_scale). IEEE multiply is sign-symmetric and
        # truncation rounds toward zero, so antisymmetry stays exact.
        self.out_scale = net.scale / K

        self._verify_excursion(lane_of, G)

    # ------------------------------------------------------------------ build
    def _pick_gain(self, pos, neg):
        """Largest K such that both packing invariants hold."""
        v, N = self.net.v, self.N
        total = sum(abs(x) for x in v) or 1.0
        K = SUM_LIMIT / total
        while K >= 1:
            G = [max(1, round(K * abs(v[k]))) for k in range(N)]
            if sum(G) <= SUM_LIMIT and self._excursion_ok(G):
                return K
            K *= 0.9
        raise ValueError(
            "cannot quantise this net: even K=1 overflows a lane. The float "
            "weights are too large — clip them during training (--wclip).")

    def _excursion_ok(self, G):
        """Worst-case lane excursion over the maximum legal piece multiset."""
        net = self.net
        W, N = net.W, net.N
        for k in range(N):
            g = G[k]
            for persp in (WHITE, BLACK):
                hi = lo = round(g * net.bias[k])
                for colour in (WHITE, BLACK):
                    for pt in PIECE_TYPES:
                        vals = [round(g * W[feature_index(persp, colour, pt, sq)][k])
                                for sq in range(64)]
                        n = MAX_COUNT[pt]
                        top = sorted(vals, reverse=True)[:n]
                        bot = sorted(vals)[:n]
                        hi += sum(x for x in top if x > 0)
                        lo += sum(x for x in bot if x < 0)
                if hi > EXCURSION_LIMIT or lo < -EXCURSION_LIMIT:
                    return False
        return True

    def _verify_excursion(self, lane_of, G):
        if not self._excursion_ok(G):
            raise ValueError("quantised net violates the lane excursion bound")

    # ------------------------------------------------------------------- head
    def clamp(self, acc):
        """min(max(lane - BIAS, 0), G) per lane, branch-free."""
        LO, VAL = self.LO, self.VAL
        m = ((acc & LO) >> (VBITS - 1)) * ONES
        y = ((acc & m) | LO) - LO
        m = (((self.GH - y) & self.H) >> VBITS) * ONES
        return (y & m) | (self.gp & (m ^ VAL))

    def hsum2(self, y):
        """(sum of block0 lanes, sum of block1 lanes) by modular reduction.
        Exact because 2^16 == 1 (mod 2^16-1) and every block sums <= 65534."""
        return (y & self.MASKLO) % M16, (y >> self.half) % M16

    def raw(self, acc, side_to_move):
        s0, s1 = self.hsum2(self.clamp(acc))
        return (s0 - s1) if side_to_move == WHITE else (s1 - s0)

    def cp(self, acc, side_to_move):
        r = self.raw(acc, side_to_move) * self.out_scale
        v = int(r) if r >= 0 else -int(-r)
        c = self.clampcp
        return -c if v < -c else (c if v > c else v)

    # ------------------------------------------------------------ accumulator
    def from_board(self, board):
        """Build the accumulator from scratch."""
        acc = self.base
        rows = self.rows
        for colour in (WHITE, BLACK):
            base_c = colour * 384
            for pt in PIECE_TYPES:
                bb = board.pieces[colour][pt]
                base_p = base_c + pt * 64
                while bb:
                    sq = (bb & -bb).bit_length() - 1
                    acc += rows[base_p + sq]
                    bb &= bb - 1
        return acc

    def check_lanes(self, acc):
        """True iff every lane is inside [0, 2^15)."""
        if acc < 0:
            return False
        return all(x < (1 << VBITS) for x in unpacklanes(acc, self.lanes))


class PackedAccumulator:
    """Incremental accumulator over a PackedNet. One int, one add per change."""

    __slots__ = ("pnet", "acc", "_stack", "rows")

    def __init__(self, pnet):
        self.pnet = pnet
        self.rows = pnet.rows
        self.acc = pnet.base
        self._stack = []

    def refresh(self, board):
        self.acc = self.pnet.from_board(board)

    def add(self, colour, pt, sq):
        self.acc += self.rows[colour * 384 + pt * 64 + sq]

    def remove(self, colour, pt, sq):
        self.acc -= self.rows[colour * 384 + pt * 64 + sq]

    def push(self):
        self._stack.append(self.acc)

    def pop(self):
        self.acc = self._stack.pop()

    def clear_stack(self):
        self._stack.clear()

    def cp(self, side_to_move):
        return self.pnet.cp(self.acc, side_to_move)
