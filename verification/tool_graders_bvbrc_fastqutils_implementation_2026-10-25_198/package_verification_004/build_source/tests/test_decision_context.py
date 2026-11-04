"""Model presentation is separate from estimator operands and child messages."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.decision_context import (
    apply_state_frame, model_snapshot, state_frame,
)


def test_large_internal_history_is_replaced_without_changing_numeric_operands():
    raw = {
        "goal": {"objective": "fixture scope"},
        "controller": {"scores": [0] * 140 + [1], "estimate": {"next_gain": .2}},
        "waiting_support": {
            "version": "wait_inputs_v2", "progress_records": [],
            "duration_expectations": [{"ref": "original", "data": {"seconds": 42}}],
            "own_completed_action_history": [{"unit_index": i,
                "controller_step": {"marginal_credit": int(i == 140),
                    "provenance": "recorded provenance " * 160}}
                for i in range(141)],
            "local_return_history": {"samples": [{"raw_controller_delta": 1,
                "controller_step": {"provenance": "another retained original"}}]},
        },
    }
    before = deepcopy(raw)
    table = {"version": "own_decision_yield_table_v1", "rows": [
        {"category": "reason", "completed_actions": 141, "total_yield": 1,
         "expected_yield": {"status": "model_unbound"}}]}
    snapshot = model_snapshot(raw, table)
    assert raw == before
    assert snapshot["action_yields"] == table
    assert snapshot["controller"] == {"estimate": {"next_gain": .2}}
    assert snapshot["waiting_support"]["duration_expectations"] == before["waiting_support"]["duration_expectations"]
    assert "controller_step" not in json.dumps(snapshot)
    assert len(json.dumps(snapshot)) < len(json.dumps(raw)) / 100
    snapshot["action_yields"]["rows"][0]["total_yield"] = 900
    assert table["rows"][0]["total_yield"] == 1
    assert raw == before


def test_updates_reconstruct_state_with_explicit_removals_and_latest_expectations():
    first = {"goal": {"id": "same-goal"}, "action_yields": {"expected": 3},
             "visual_evidence": [{"id": "image"}], "obsolete": {"value": 4}}
    second = {"goal": {"id": "same-goal"}, "action_yields": {"expected": .25},
              "visual_evidence": [], "new_field": None}
    bootstrap = state_frame(first)
    assert apply_state_frame(None, bootstrap) == first
    update = state_frame(second, first)
    assert "goal" not in update["fields"]
    assert update["removed_fields"] == ["obsolete"]
    assert update["fields"]["visual_evidence"] == []
    assert update["fields"]["new_field"] is None
    assert apply_state_frame(first, update) == second
    with pytest.raises(ValueError, match="base_conflict"):
        apply_state_frame(second, update)
    tampered = deepcopy(update)
    tampered["fields"]["action_yields"]["expected"] = 100
    with pytest.raises(ValueError, match="revision_conflict"):
        apply_state_frame(first, tampered)


def test_bootstrap_replaces_obsolete_conversation_state_after_restoration():
    stale = {"old_parent_information": "not in the new scoped state"}
    current = {"scope": {"subject_refs": ["target"]}, "own_attempts": []}
    assert apply_state_frame(stale, state_frame(current)) == current
    frame = state_frame(current)
    frame["removed_fields"] = ["old_parent_information"]
    with pytest.raises(ValueError, match="invalid_decision_bootstrap"):
        apply_state_frame(stale, frame)


def test_delta_rejects_conflicting_and_unknown_removal_fields():
    previous = {"kept": 1, "removed": 2}
    frame = state_frame({"kept": 3}, previous)
    frame["removed_fields"] = ["kept"]
    with pytest.raises(ValueError, match="invalid_decision_frame"):
        apply_state_frame(previous, frame)
    frame = state_frame({"kept": 3}, previous)
    frame["removed_fields"] = ["unknown"]
    with pytest.raises(ValueError, match="removes_unknown"):
        apply_state_frame(previous, frame)


def test_restored_pending_exchange_metadata_does_not_change_state_revision():
    current = {"scope": {"subject_refs": ["target"]}}
    frame = state_frame(current)
    frame.update(restored_pending_decision_index=7,
        restored_public_exchanges=[{"exchange_index": 0,
            "response": {"response_type": "request_context"},
            "lookup_result": {"records": []}}])
    assert apply_state_frame(None, frame) == current
    malformed = deepcopy(frame)
    malformed.pop("restored_pending_decision_index")
    with pytest.raises(ValueError, match="invalid_decision_restoration"):
        apply_state_frame(None, malformed)
    update = state_frame(current, {})
    update.update(restored_pending_decision_index=7, restored_public_exchanges=[])
    with pytest.raises(ValueError, match="invalid_decision_restoration"):
        apply_state_frame({}, update)


@pytest.mark.parametrize("old,new", [(1, 1.0), (1, True),
    ({"nested": [1]}, {"nested": [True]})])
def test_updates_preserve_json_types_even_when_python_values_compare_equal(old, new):
    previous, current = {"value": old}, {"value": new}
    frame = state_frame(current, previous)
    assert "value" in frame["fields"]
    assert json.dumps(apply_state_frame(previous, frame)) == json.dumps(current)
