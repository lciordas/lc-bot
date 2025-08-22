"""Train the NNUE net (PyTorch) and export it in nnue_net's JSON format."""
import argparse
import json
import math
import os
import random
import time

import torch
import torch.nn as nn

from board import Board
from features import active_features


class NNUE(nn.Module):
    def __init__(self, N=256):
        super().__init__()
        self.N = N
        # Sum of the active feature columns; only touches active rows.
        self.ft = nn.EmbeddingBag(768, N, mode="sum")
        self.bias = nn.Parameter(torch.zeros(N))
        self.v = nn.Parameter(torch.randn(N) * 0.1)
        nn.init.normal_(self.ft.weight, 0.0, 0.02)

    def forward(self, us_idx, us_off, them_idx, them_off):
        a_us = self.ft(us_idx, us_off) + self.bias
        a_them = self.ft(them_idx, them_off) + self.bias
        d = a_us.clamp(0.0, 1.0) - a_them.clamp(0.0, 1.0)
        return (d * self.v).sum(dim=1)

    @torch.no_grad()
    def clip_weights(self, wclip=1.98):
        """Keep weights in a range the 16-bit packing can represent."""
        self.ft.weight.clamp_(-wclip, wclip)
        self.bias.clamp_(-wclip, wclip)


def load_records(path, limit=None):
    recs = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            recs.append(json.loads(line))
            if limit and len(recs) >= limit:
                break
    return recs


LABEL_FIELD = "score"


def featurize(recs):
    """FEN -> (us features, them features), plus the label columns."""
    us_all, them_all, score, static, result = [], [], [], [], []
    for r in recs:
        b = Board(r["fen"])
        us_all.append(active_features(b, b.side))
        them_all.append(active_features(b, b.side ^ 1))
        score.append(float(r[LABEL_FIELD]))
        static.append(float(r["static"]))
        result.append(float(r["result"]))
    return us_all, them_all, score, static, result


def to_bag(lists, device):
    """Flatten variable-length index lists into EmbeddingBag (idx, offsets)."""
    offs, flat = [], []
    for l in lists:
        offs.append(len(flat))
        flat.extend(l)
    return (torch.tensor(flat, dtype=torch.long, device=device),
            torch.tensor(offs, dtype=torch.long, device=device))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/train.jsonl")
    ap.add_argument("--out", default="nets/net.json")
    ap.add_argument("--N", type=int, default=256)
    ap.add_argument("--mode", choices=("hybrid", "pure"), default="hybrid")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=8192)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--sigk", type=float, default=400.0,
                    help="centipawns per sigmoid unit")
    ap.add_argument("--lambda-result", type=float, default=0.0,
                    help="blend weight on the game outcome vs the search score. "
                         "Default 0: measured, blending in the outcome improved "
                         "the sigmoid loss while leaving centipawn accuracy flat "
                         "(76.1 vs a 76.5 baseline) and cost -338 Elo in play. "
                         "The outcome label is too noisy at this game count.")
    ap.add_argument("--wclip", type=float, default=1.98)
    ap.add_argument("--label", default="score",
                    choices=("score", "sf_score"),
                    help="which teacher to distil. 'score' is this engine's own "
                         "depth-6 search (measured: +5 Elo at fixed depth — the "
                         "search already knows what it teaches). 'sf_score' is "
                         "Stockfish 18 at depth 14, which can teach the search "
                         "things it cannot find itself.")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--val-frac", type=float, default=0.05)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    global LABEL_FIELD
    LABEL_FIELD = args.label
    dev = torch.device(args.device)
    print(f"loading {args.data} ...", flush=True)
    recs = load_records(args.data, args.limit or None)
    random.Random(0).shuffle(recs)
    print(f"  {len(recs):,} positions", flush=True)

    us_l, them_l, score, static, result = featurize(recs)
    n_val = max(1, int(len(recs) * args.val_frac))
    idx = list(range(len(recs)))
    val_idx, tr_idx = idx[:n_val], idx[n_val:]
    print(f"  train {len(tr_idx):,}  val {n_val:,}", flush=True)

    sc = torch.tensor(score, device=dev)
    st = torch.tensor(static, device=dev)
    rs = torch.tensor(result, device=dev)

    model = NNUE(args.N).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    K = args.sigk
    lam = args.lambda_result

    def batch_loss(bidx):
        ui, uo = to_bag([us_l[i] for i in bidx], dev)
        ti, to_ = to_bag([them_l[i] for i in bidx], dev)
        out = model(ui, uo, ti, to_)
        base = st[bidx] if args.mode == "hybrid" else 0.0
        pred = torch.sigmoid((out + base) / K)
        tgt_score = torch.sigmoid(sc[bidx] / K)
        tgt_res = (rs[bidx] + 1.0) / 2.0
        tgt = (1.0 - lam) * tgt_score + lam * tgt_res
        return ((pred - tgt) ** 2).mean()

    # Baseline loss for a net that outputs zero: hand-written eval alone in
    # hybrid mode, constant 0.5 in pure mode. Training has to beat this.
    with torch.no_grad():
        nb_val = max(1, math.ceil(len(val_idx) / args.batch))
        base_loss = 0.0
        for s0 in range(0, len(val_idx), args.batch):
            b = val_idx[s0:s0 + args.batch]
            base = st[b] if args.mode == "hybrid" else torch.zeros(len(b), device=dev)
            pred = torch.sigmoid(base / K)
            tgt = ((1.0 - lam) * torch.sigmoid(sc[b] / K)
                   + lam * (rs[b] + 1.0) / 2.0)
            base_loss += ((pred - tgt) ** 2).mean().item()
        base_loss /= nb_val
        base_cp = 0.0
        for s0 in range(0, len(val_idx), args.batch):
            b = val_idx[s0:s0 + args.batch]
            base = st[b] if args.mode == "hybrid" else torch.zeros(len(b), device=dev)
            base_cp += (base - sc[b]).abs().mean().item()
        base_cp /= nb_val
    label = "hand-written eval alone" if args.mode == "hybrid" else "constant 0.5"
    print(f"  baseline val loss ({label}): {base_loss:.6f}"
          f"  cp_err {base_cp:.1f}", flush=True)

    best = float("inf")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    for ep in range(1, args.epochs + 1):
        model.train()
        random.shuffle(tr_idx)
        tot, nb = 0.0, 0
        t0 = time.perf_counter()
        for s in range(0, len(tr_idx), args.batch):
            b = tr_idx[s:s + args.batch]
            opt.zero_grad()
            loss = batch_loss(b)
            loss.backward()
            opt.step()
            model.clip_weights(args.wclip)
            tot += loss.item(); nb += 1
        sched.step()
        model.eval()
        with torch.no_grad():
            vl = sum(batch_loss(val_idx[s:s + args.batch]).item()
                     for s in range(0, len(val_idx), args.batch))
            vl /= max(1, math.ceil(len(val_idx) / args.batch))
        with torch.no_grad():
            cp_err = 0.0
            for s0 in range(0, len(val_idx), args.batch):
                b = val_idx[s0:s0 + args.batch]
                ui, uo = to_bag([us_l[i] for i in b], dev)
                ti, to_ = to_bag([them_l[i] for i in b], dev)
                out = model(ui, uo, ti, to_)
                base = st[b] if args.mode == "hybrid" else 0.0
                cp_err += (out + base - sc[b]).abs().mean().item()
            cp_err /= nb_val
        tag = ""
        if vl < best:
            best = vl
            export(model, args.out, args.mode)
            tag = "  <- saved"
        print(f"  epoch {ep:>3}  train {tot/max(nb,1):.6f}  val {vl:.6f}"
              f"  cp_err {cp_err:6.1f}  {time.perf_counter()-t0:5.1f}s{tag}",
              flush=True)

    gain = (base_loss - best) / base_loss * 100.0 if base_loss else 0.0
    print(f"\nbest val loss {best:.6f}  vs baseline {base_loss:.6f}"
          f"  ({gain:+.1f}% improvement) -> {args.out}")


def export(model, path, mode):
    """Write float weights in nnue_net's JSON format."""
    from nnue_net import NetParams, DEFAULT_CLAMP_CP, PURE_CLAMP_CP
    W = model.ft.weight.detach().cpu().tolist()
    bias = model.bias.detach().cpu().tolist()
    v = model.v.detach().cpu().tolist()
    clamp = DEFAULT_CLAMP_CP if mode == "hybrid" else PURE_CLAMP_CP
    # Model output is already centipawns, so scale is 1.0.
    NetParams(model.N, W, bias, v, 1.0, clamp, mode).save(path)


if __name__ == "__main__":
    main()
