"""NNUE float weights and JSON file format.

    a[p]   = bias + sum(W[f] for f in active_features(pos, p))   # per perspective
    nn_raw = sum_k v[k] * (crelu(a[us][k]) - crelu(a[them][k]))
    nn_cp  = clamp(round(nn_raw * scale), -clampcp, +clampcp)

The single output vector v, shared by both perspectives with opposite signs,
keeps the eval exactly antisymmetric. Modes: "hybrid" adds nn_cp to the
hand-written eval (a learned residual); "pure" uses nn_cp alone.
"""

import json

DEFAULT_CLAMP_CP = 600          # hybrid: a residual, so it stays small
PURE_CLAMP_CP = 3000            # pure: must be able to express a won game


class NetParams:
    """Float weights: the training output and the reference for the packed net."""

    __slots__ = ("N", "W", "bias", "v", "scale", "clampcp", "mode")

    def __init__(self, N, W, bias, v, scale=1.0, clampcp=DEFAULT_CLAMP_CP,
                 mode="hybrid"):
        if mode not in ("hybrid", "pure"):
            raise ValueError(f"unknown mode {mode!r}")
        if len(W) != 768:
            raise ValueError(f"W must have 768 rows, got {len(W)}")
        if any(len(row) != N for row in W):
            raise ValueError("every W row must have N entries")
        if len(bias) != N or len(v) != N:
            raise ValueError("bias and v must have N entries")
        self.N, self.W, self.bias, self.v = N, W, bias, v
        self.scale, self.clampcp, self.mode = scale, clampcp, mode

    def save(self, path):
        with open(path, "w") as fh:
            json.dump({
                "format": "lc-bot/float/1",
                "N": self.N, "scale": self.scale,
                "clampcp": self.clampcp, "mode": self.mode,
                "bias": self.bias, "v": self.v, "W": self.W,
            }, fh)

    @staticmethod
    def load(path):
        with open(path) as fh:
            d = json.load(fh)
        fmt = d.get("format")
        if fmt != "lc-bot/float/1":
            raise ValueError(f"unrecognised net format {fmt!r}")
        return NetParams(d["N"], d["W"], d["bias"], d["v"],
                         d["scale"], d["clampcp"], d["mode"])


def random_net(N=256, seed=0, mode="hybrid", scale=None, sigma=0.05):
    """A random net of the right shape, for tests and benchmarks."""
    import random
    rng = random.Random(seed)
    W = [[rng.gauss(0.0, sigma) for _ in range(N)] for _ in range(768)]
    bias = [rng.gauss(0.0, sigma) for _ in range(N)]
    v = [rng.gauss(0.0, sigma) for _ in range(N)]
    clampcp = DEFAULT_CLAMP_CP if mode == "hybrid" else PURE_CLAMP_CP
    if scale is None:
        scale = 100.0
    return NetParams(N, W, bias, v, scale, clampcp, mode)


def zero_net(N=8, mode="hybrid"):
    """A net that evaluates to 0 everywhere; in hybrid mode it matches the hand-written eval."""
    W = [[0.0] * N for _ in range(768)]
    return NetParams(N, W, [0.0] * N, [0.0] * N, 1.0,
                     DEFAULT_CLAMP_CP if mode == "hybrid" else PURE_CLAMP_CP,
                     mode)
