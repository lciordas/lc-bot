"""Texel tuning: coordinate descent on evaluation.py's constants against game results.

Setters mutate evaluation.py's module globals in place; tests must snapshot and
restore them. PST cells are tuned through evaluation._PST_READING so both
colours' tables stay mirrored.
"""

from dataclasses import dataclass
from typing import Callable

import evaluation
from board import Board

_PIECE_NAMES = ("pawn", "knight", "bishop", "rook", "queen", "king")
_MATERIAL_NAMES = _PIECE_NAMES[:5]  # king excluded: always 0
_PHASE_NAMES = ("mg", "eg")


@dataclass
class Param:
    name: str
    get: Callable[[], int]
    set: Callable[[int], None]
    step: int = 1


def default_params() -> list:
    """Material, mobility/shield/doubled-pawn scalars, and all 768 PST cells."""
    params = [
        Param(
            f"material_{name}",
            (lambda i=i: evaluation.PIECE_VALUE[i]),
            (lambda v, i=i: evaluation.PIECE_VALUE.__setitem__(i, v)),
            step=5,
        )
        for i, name in enumerate(_MATERIAL_NAMES)
    ]
    params.append(Param(
        "mobility_weight",
        lambda: evaluation.MOBILITY_WEIGHT,
        lambda v: setattr(evaluation, "MOBILITY_WEIGHT", v),
    ))
    params.append(Param(
        "shield_bonus",
        lambda: evaluation.SHIELD_BONUS,
        lambda v: setattr(evaluation, "SHIELD_BONUS", v),
    ))
    params.append(Param(
        "doubled_pen",
        lambda: evaluation.DOUBLED_PEN,
        lambda v: setattr(evaluation, "DOUBLED_PEN", v),
    ))
    params.extend(pst_params())
    return params


def _set_pst_cell(pt: int, phase_idx: int, idx: int, v: int) -> None:
    """Set one reading-order cell and rebuild only that piece type/phase's MG/EG tables."""
    evaluation._PST_READING[pt][phase_idx][idx] = v
    evaluation._update_pst_pt_phase(pt, phase_idx)


def pst_params(step: int = 5) -> list:
    """One Param per PST cell: 6 piece types x (mg, eg) x 64 squares."""
    params = []
    for pt, piece_name in enumerate(_PIECE_NAMES):
        for phase_idx, phase_name in enumerate(_PHASE_NAMES):
            for idx in range(64):
                params.append(Param(
                    f"pst_{piece_name}_{phase_name}_{idx}",
                    (lambda pt=pt, phase_idx=phase_idx, idx=idx: evaluation._PST_READING[pt][phase_idx][idx]),
                    (lambda v, pt=pt, phase_idx=phase_idx, idx=idx: _set_pst_cell(pt, phase_idx, idx, v)),
                    step=step,
                ))
    return params


def _outcome_from_white(result: str) -> float:
    return {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[result]


def sigmoid(score: float, k: float) -> float:
    """White's expected score from a White-relative centipawn eval."""
    return 1.0 / (1.0 + 10 ** (-k * score / 400.0))


def training_positions(records, skip_plies=6):
    """Yield (fen, outcome_from_white) for each position after the first `skip_plies`.

    Positions are labelled with the game result; no quiet-position filter.
    """
    for record in records:
        outcome = _outcome_from_white(record.result)
        for ply_index, (fen, _move) in enumerate(record.positions):
            if ply_index < skip_plies:
                continue
            yield fen, outcome


def mean_squared_error(boards_and_outcomes, k: float) -> float:
    total = 0.0
    n = 0
    for board, outcome in boards_and_outcomes:
        predicted = sigmoid(evaluation.evaluate_white(board), k)
        total += (outcome - predicted) ** 2
        n += 1
    return total / n if n else 0.0


def tune(records, params=None, k=1.0, skip_plies=6, max_rounds=10, on_round=None):
    """Tune `params` in place. Returns the final MSE, or None if there was no data."""
    params = params if params is not None else default_params()
    boards_and_outcomes = [
        (Board(fen), outcome) for fen, outcome in training_positions(records, skip_plies=skip_plies)
    ]
    if not boards_and_outcomes:
        return None

    best_error = mean_squared_error(boards_and_outcomes, k)
    for round_num in range(max_rounds):
        improved = False
        for p in params:
            original = p.get()
            for direction in (p.step, -p.step):
                p.set(original + direction)
                error = mean_squared_error(boards_and_outcomes, k)
                if error < best_error:
                    best_error = error
                    improved = True
                    break
                p.set(original)
        if on_round is not None:
            on_round(round_num, best_error)
        if not improved:
            break
    return best_error


if __name__ == "__main__":
    import sys

    from config import EngineConfig
    from selfplay import play_match, Player

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
        return cond

    ok = True

    original = {p.name: p.get() for p in default_params()}
    try:
        records, _summary = play_match(
            Player(EngineConfig()), Player(EngineConfig()), games=2, movetime=0.03, max_plies=30,
        )
        error_before = mean_squared_error(
            [(Board(fen), out) for fen, out in training_positions(records, skip_plies=0)], k=1.0,
        )
        error_after = tune(records, skip_plies=0, max_rounds=3)
        ok &= check("tune() ran on real self-play games without crashing", error_after is not None)
        ok &= check("hill-climbing never increases error", error_after is None or error_after <= error_before)
    finally:
        for p in default_params():
            p.set(original[p.name])

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)
