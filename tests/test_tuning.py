"""IMPORTANT: tuning.tune() mutates evaluation.py's live module globals
(PIECE_VALUE, MOBILITY_WEIGHT, SHIELD_BONUS, DOUBLED_PEN) by design -- the
whole point is to change how the engine actually evaluates positions. Since
pytest runs every test file in one process, a test here that doesn't restore
those globals afterward would silently corrupt evaluation.py's behavior for
every test that runs later in the same session (including, notably,
evaluation.py's own balance/antisymmetry assumptions). The autouse fixture
below snapshots and restores them around every test in this file.
"""

import evaluation
import pytest
from board import Board
from selfplay import GameRecord
from tuning import default_params, mean_squared_error, sigmoid, training_positions, tune


@pytest.fixture(autouse=True)
def restore_eval_constants():
    snapshot = {
        "PIECE_VALUE": list(evaluation.PIECE_VALUE),
        "MOBILITY_WEIGHT": evaluation.MOBILITY_WEIGHT,
        "SHIELD_BONUS": evaluation.SHIELD_BONUS,
        "DOUBLED_PEN": evaluation.DOUBLED_PEN,
    }
    yield
    evaluation.PIECE_VALUE[:] = snapshot["PIECE_VALUE"]
    evaluation.MOBILITY_WEIGHT = snapshot["MOBILITY_WEIGHT"]
    evaluation.SHIELD_BONUS = snapshot["SHIELD_BONUS"]
    evaluation.DOUBLED_PEN = snapshot["DOUBLED_PEN"]


# --- sigmoid / outcome mapping ---

def test_sigmoid_zero():
    assert sigmoid(0, k=1.0) == pytest.approx(0.5)


def test_sigmoid_large_positive():
    assert sigmoid(2000, k=1.0) > 0.999


def test_sigmoid_large_negative():
    assert sigmoid(-2000, k=1.0) < 0.001


def test_sigmoid_monotonic():
    scores = [-500, -100, 0, 100, 500]
    values = [sigmoid(s, k=1.0) for s in scores]
    assert values == sorted(values)


# --- training_positions ---

def test_positions_labels():
    record = GameRecord(result="1-0", reason="checkmate", positions=[("fenA", "e2e4"), ("fenB", "e7e5")])
    positions = list(training_positions([record], skip_plies=0))
    assert positions == [("fenA", 1.0), ("fenB", 1.0)]


def test_positions_skip_plies():
    positions_in = [(f"fen{i}", "e2e4") for i in range(10)]
    record = GameRecord(result="0-1", reason="checkmate", positions=positions_in)
    kept = list(training_positions([record], skip_plies=6))
    assert [fen for fen, _outcome in kept] == [f"fen{i}" for i in range(6, 10)]
    assert all(outcome == 0.0 for _fen, outcome in kept)


def test_positions_draw():
    record = GameRecord(result="1/2-1/2", reason="fifty_move", positions=[("fenA", "e2e4")])
    positions = list(training_positions([record], skip_plies=0))
    assert positions == [("fenA", 0.5)]


# --- default_params: get/set wiring ---

def test_default_params():
    names = {p.name for p in default_params()}
    assert names == {
        "material_pawn", "material_knight", "material_bishop", "material_rook", "material_queen",
        "mobility_weight", "shield_bonus", "doubled_pen",
    }


def test_param_roundtrip():
    for p in default_params():
        original = p.get()
        p.set(original + p.step)
        assert p.get() == original + p.step
        p.set(original)  # restored explicitly too, on top of the fixture


def test_material_param():
    params = {p.name: p for p in default_params()}
    params["material_pawn"].set(123)
    assert evaluation.PIECE_VALUE[0] == 123


def test_scalar_param():
    params = {p.name: p for p in default_params()}
    params["mobility_weight"].set(7)
    assert evaluation.MOBILITY_WEIGHT == 7


# --- tune(): the core hill-climbing invariant ---

def _synthetic_records():
    """Positions where the *label* strongly implies white-favoring material
    should score better: White up a queen labeled a White win, and a level
    material position labeled a draw. Not real game data -- just enough
    signal for hill-climbing to have somewhere to go."""
    up_a_queen = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    level = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    return [
        GameRecord(result="1-0", reason="checkmate", positions=[(up_a_queen, "a2a3")] * 3),
        GameRecord(result="1/2-1/2", reason="fifty_move", positions=[(level, "a2a3")] * 3),
    ]


def test_tune_error():
    records = _synthetic_records()
    boards_and_outcomes = [(Board(fen), out) for fen, out in training_positions(records, skip_plies=0)]
    error_before = mean_squared_error(boards_and_outcomes, k=1.0)
    error_after = tune(records, skip_plies=0, max_rounds=5, k=1.0)
    assert error_after is not None
    assert error_after <= error_before + 1e-12  # hill-climbing only ever accepts strict improvements


def test_tune_no_positions():
    record = GameRecord(result="1-0", reason="checkmate", positions=[("fenA", "e2e4")])
    original_pawn_value = evaluation.PIECE_VALUE[0]
    result = tune([record], skip_plies=100, max_rounds=3)  # skip_plies exceeds the game length
    assert result is None
    assert evaluation.PIECE_VALUE[0] == original_pawn_value


def test_tune_given_params():
    """Passing a restricted param list must leave every other tunable
    constant untouched, even across many rounds."""
    records = _synthetic_records()
    only_mobility = [p for p in default_params() if p.name == "mobility_weight"]
    original_pawn_value = evaluation.PIECE_VALUE[0]
    tune(records, params=only_mobility, skip_plies=0, max_rounds=5)
    assert evaluation.PIECE_VALUE[0] == original_pawn_value


def test_tune_on_round():
    records = _synthetic_records()
    rounds_seen = []
    tune(records, skip_plies=0, max_rounds=5, on_round=lambda round_num, error: rounds_seen.append(round_num))
    assert rounds_seen == sorted(rounds_seen)  # monotonically increasing round numbers
    assert len(rounds_seen) >= 1


def test_restore_fixture():
    """Sanity check on the autouse fixture itself: mutate here, and a
    separate test (below) checks the mutation didn't leak."""
    evaluation.PIECE_VALUE[0] = 999999


def test_no_leak():
    assert evaluation.PIECE_VALUE[0] != 999999
