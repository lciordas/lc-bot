"""Relabel training positions with Stockfish scores (adds an "sf_score" field).

Scores are side-to-move centipawns; mates are clamped to +/-CLAMP rather than dropped.

    uv run python tools/relabel_sf.py --inp data/train.jsonl --out data/train_sf.jsonl
"""
import argparse
import json
import os
from multiprocessing import Process

import chess
import chess.engine

SF = "/opt/homebrew/bin/stockfish"
CLAMP = 2000        # keep labels on the same scale the eval works in


def worker(wid, lines, depth, out_path, threads=1, hash_mb=64):
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    eng.configure({"Threads": threads, "Hash": hash_mb})
    n = 0
    with open(out_path, "w") as fh:
        for line in lines:
            rec = json.loads(line)
            board = chess.Board(rec["fen"])
            try:
                info = eng.analyse(board, chess.engine.Limit(depth=depth))
                sc = info["score"].relative.score(mate_score=30000)
            except Exception:                       # noqa: BLE001
                continue
            if sc is None:
                continue
            rec["sf_score"] = max(-CLAMP, min(CLAMP, int(sc)))
            fh.write(json.dumps(rec) + "\n")
            n += 1
            if wid == 0 and n % 2000 == 0:
                print(f"  worker0: {n:,} / {len(lines):,}", flush=True)
    eng.quit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", default="data/train.jsonl")
    ap.add_argument("--out", default="data/train_sf.jsonl")
    ap.add_argument("--depth", type=int, default=14)
    ap.add_argument("--workers", type=int, default=14)
    args = ap.parse_args()

    with open(args.inp) as fh:
        lines = fh.readlines()
    print(f"relabelling {len(lines):,} positions with Stockfish depth {args.depth} "
          f"on {args.workers} workers", flush=True)

    shards = [lines[i::args.workers] for i in range(args.workers)]
    parts = [f"{args.out}.part{i}" for i in range(args.workers)]
    procs = [Process(target=worker, args=(i, shards[i], args.depth, parts[i]))
             for i in range(args.workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    total = 0
    with open(args.out, "w") as out:
        for part in parts:
            if not os.path.exists(part):
                continue
            with open(part) as fh:
                for line in fh:
                    out.write(line)
                    total += 1
            os.remove(part)
    print(f"done: {total:,} positions -> {args.out}")


if __name__ == "__main__":
    main()
