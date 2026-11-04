"""Original local identities/history forwarding, with no execution or scoring."""
from copy import deepcopy

import pytest

from method_loop.durable import canonical
from method_loop.identities import UnitRef

from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.wait_estimation_inputs import (WaitInputs,
    validate_local_return_history)
from gene_annotation_episode.waiting import (WaitError, completed_action_context,
    estimate_wait)


STAMP = "2026-10-21T12:00:00+00:00"
PENDING = {"version": "pending_work_v1", "captured_at": STAMP, "items": []}
CONDITION = {"version": "event_condition_v1", "events": [], "reconsider_at": STAMP}


def save_episode(journal, episode="parent"):
    journal.save("runtime_episodes", {"episode_id": episode,
        "path": canonical([["annotation", episode]]),
        "request": canonical({"message": {"scope": {"subject_refs": ["fixture-subject"]}}}),
        "initial_credit": 0, "state": "active", "completion": None, "archive": None})


def save_observation(journal, index, decision, *, episode="parent", identity=True):
    value = {"decision_index": decision, "credit": {"credit": 1.5 - index},
             "step": {"marginal_credit": -0.25 - index}}
    if identity:
        value.update(unit_ref=UnitRef(episode, index).as_record(), label="same readable label")
    journal.save("runtime_observations", {"episode_id": episode, "unit_index": index,
        "observation": canonical(value)})
    return value


def return_history():
    """The complete E2 output shape, including a signed original raw delta."""
    return {"version": "local_parent_return_history_v1", "run_id": "run", "episode_id": "parent",
        "credit_kind": "scientific", "credit_binding": {"version": "explicit-fixture-binding"},
        "samples": [{"sample_ref": "admission-original", "original_decision_index": 9,
            "completion_sequence": 0, "unit_ref": UnitRef("parent", 0).as_record(),
            "child_handle": "child-original", "child_role": "scientific_process",
            "report_contract_sha256": "a" * 64, "commission_sha256": "b" * 64,
            "return_id": "original-return", "admission_id": "admission-original",
            "admission_state": "admitted", "observation_state": "observed",
            "controller_input": {"credit": 1.5}, "controller_step": {"marginal_credit": -0.25},
            "raw_controller_delta": -0.25, "selected_at": STAMP,
            "returned_at": "2026-10-21T12:00:03+00:00",
            "selection_to_return": {"seconds": 3.0, "measure": "utc_timestamp_difference",
                                    "unavailable_reason": None},
            "received_record_refs": ["actual-record"], "received_progress_refs": [],
            "linked_waits": [{"wait_id": "original-wait", "condition_sha256": "c" * 64,
                "measured_duration_seconds": 1.25, "duration_measure": "measured_wait_intervals",
                "unmeasured_interruption": False}]}], "unavailable_reasons": []}


def test_opt_in_v2_preserves_exact_default_and_original_completion_order(tmp_path):
    with Store(tmp_path) as store:
        journal = Journal(store, "run")
        save_episode(journal)
        first = save_observation(journal, 0, 9)
        second = save_observation(journal, 1, 2)
        save_observation(journal, 0, 0, episode="child")
        save_observation(Journal(store, "other-run"), 0, 99)
        reader = WaitInputs(store, journal, None)
        before = store.db.total_changes
        legacy = reader.capture("parent", pending=PENDING, known_progress_refs=[])
        expected = [{"episode_id": "parent", "unit_index": index,
            "decision_index": value["decision_index"], "controller_input": value["credit"],
            "controller_step": value["step"]} for index, value in enumerate((first, second))]
        assert legacy == {"version": "wait_inputs_v1", "progress_records": [],
            "duration_expectations": [], "own_completed_action_history": expected}
        support = return_history()
        typed = reader.capture("parent", pending=PENDING, known_progress_refs=[],
            include_identities=True, local_return_history=support)
        assert typed == {**legacy, "version": "wait_inputs_v2", "local_return_history": support,
            "own_completed_action_history": [{**row, "unit_ref": UnitRef("parent", index).as_record(),
                "label": "same readable label"} for index, row in enumerate(expected)]}
        support["samples"][0]["raw_controller_delta"] = 999
        assert typed["local_return_history"]["samples"][0]["raw_controller_delta"] == -0.25
        assert store.db.total_changes == before


def test_actual_e2_return_records_forward_without_status_projection_or_observation(tmp_path, monkeypatch):
    from test_local_return_history import Case, read_only

    case = Case(tmp_path)
    try:
        first = case.child(9, credit=5.25)
        second = case.child(1, credit=2.0)
        case.stage(first[2])
        case.stage(second[2])
        before = case.store.db.total_changes
        read_only(case, monkeypatch)
        with case.store.read_snapshot():
            original = case.capture()
            typed = WaitInputs(case.store, case.journal, None).capture(case.parent,
                pending=PENDING, known_progress_refs=[], include_identities=True,
                local_return_history=original)
        assert typed["local_return_history"] == original
        assert [sample["raw_controller_delta"] for sample in original["samples"]] == [5.25, -3.25]
        assert [row["decision_index"] for row in typed["own_completed_action_history"]] == [9, 1]
        assert [row["unit_ref"] for row in typed["own_completed_action_history"]] == [
            sample["unit_ref"] for sample in original["samples"]]
        assert case.store.db.total_changes == before
    finally:
        case.store.close()


def test_legacy_missing_identities_stay_nullable_without_manufactured_references(tmp_path):
    with Store(tmp_path) as store:
        journal = Journal(store, "run")
        save_episode(journal)
        save_observation(journal, 0, 9, identity=False)
        reader = WaitInputs(store, journal, None)
        value = reader.capture("parent", pending=PENDING, known_progress_refs=[], include_identities=True)
        assert "local_return_history" not in value
        row = value["own_completed_action_history"][0]
        assert row["unit_ref"] is None and row["label"] is None
        estimate = estimate_wait(CONDITION, PENDING, [], [], [row])
        assert estimate["local_history_refs"] == []
        assert "local_history_has_no_references" in estimate["unavailable_reasons"]


@pytest.mark.parametrize("changed", [
    UnitRef("foreign", 0).as_record(), UnitRef("parent", 1).as_record(),
    {**UnitRef("parent", 0).as_record(), "unit_id": "forged"},
])
def test_v2_rejects_saved_unit_identity_conflicts_without_changing_legacy(tmp_path, changed):
    with Store(tmp_path) as store:
        journal = Journal(store, "run")
        save_episode(journal)
        observed = save_observation(journal, 0, 9)
        observed["unit_ref"] = changed
        journal.save("runtime_observations", {"episode_id": "parent", "unit_index": 0,
            "observation": canonical(observed)})
        reader = WaitInputs(store, journal, None)
        assert reader.capture("parent", pending=PENDING, known_progress_refs=[])["version"] == "wait_inputs_v1"
        with pytest.raises((ValueError, TypeError)):
            reader.capture("parent", pending=PENDING, known_progress_refs=[], include_identities=True)


@pytest.mark.parametrize("field,value", [
    ("version", "not-v1"), ("run_id", "other-run"), ("episode_id", "other-episode"),
    ("credit_binding", {"unsupported": float("nan")}),
])
def test_supplied_history_requires_original_version_scope_and_finite_json(tmp_path, field, value):
    with Store(tmp_path) as store:
        journal = Journal(store, "run")
        save_episode(journal)
        history = return_history()
        history[field] = value
        before = store.db.total_changes
        with pytest.raises(ValueError, match="invalid_local_return_history"):
            WaitInputs(store, journal, None).capture("parent", pending=PENDING, known_progress_refs=[],
                include_identities=True, local_return_history=history)
        assert store.db.total_changes == before


def test_history_without_identity_mode_and_foreign_sample_are_invalid(tmp_path):
    with Store(tmp_path) as store:
        journal = Journal(store, "run")
        save_episode(journal)
        reader = WaitInputs(store, journal, None)
        history = return_history()
        with pytest.raises(ValueError, match="history_requires_identities"):
            reader.capture("parent", pending=PENDING, known_progress_refs=[], local_return_history=history)
        history["samples"][0]["unit_ref"] = UnitRef("foreign", 0).as_record()
        with pytest.raises(ValueError, match="invalid_local_return_history"):
            validate_local_return_history(history)


def test_missing_legacy_return_support_and_unobserved_admissions_are_retained():
    history = return_history()
    sample = history["samples"][0]
    sample.update(unit_ref=None, completion_sequence=None, observation_state="unobserved",
                  controller_step=None, raw_controller_delta=None)
    history["unavailable_reasons"] = ["completion_slot_unavailable", "controller_observation_unavailable"]
    assert validate_local_return_history(history) == history
    sample.update(observation_state="observed", controller_step={"custom": "original"})
    history["unavailable_reasons"] = ["observation_unit_ref_unavailable",
        "standard_controller_marginal_credit_unavailable"]
    assert validate_local_return_history(history) == history


def test_estimate_uses_validated_saved_unit_ids_and_never_labels_or_invented_gains():
    unit = UnitRef("parent", 2)
    row = {"episode_id": "parent", "unit_index": 2, "unit_ref": unit.as_record(),
           "label": "not-a-reference", "controller_input": {"credit": 12.5},
           "controller_step": {"marginal_credit": -7.25}, "record_ref": "explicit-old-reference"}
    pending = {**PENDING, "items": [{"handle": "pending-child", "role": "scientific_process",
        "lifecycle_state": "executing", "selected_at": STAMP, "observed_at": STAMP,
        "resource_selection": None, "expectation_snapshot_refs": [],
        "latest_progress_ref": None, "return_available": False}]}
    condition = {**CONDITION, "events": [{"handle": "pending-child", "event": "returned",
                                        "after_cursor": 0}]}
    estimate = estimate_wait(condition, pending, [], [], [row])
    assert estimate["local_history_refs"] == ["explicit-old-reference", unit.unit_id]
    assert estimate["scientific_gain"] is None and estimate["monitoring_gain"] is None
    assert estimate["event_expectations"][0]["probability"] is None
    assert "local_history_has_no_references" not in estimate["unavailable_reasons"]
    label_only = estimate_wait(CONDITION, PENDING, [], [], [{"label": unit.unit_id}])
    assert label_only["local_history_refs"] == []
    row["unit_ref"] = UnitRef("foreign", 2).as_record()
    with pytest.raises(WaitError, match="invalid_wait_record"):
        estimate_wait(CONDITION, PENDING, [], [], [row])


def test_completion_default_is_exact_v3_and_v4_only_forwards_selection_history():
    original = {"original": {"snapshot": 2}}
    v3 = completed_action_context(original, pending_at_selection=PENDING, pending_after_action=PENDING)
    assert v3 == {**original, "version": "completed_action_estimation_context_v3",
        "pending_work_at_selection": PENDING, "pending_work_after_action": PENDING,
        "wait_estimate_at_selection": None, "wait_outcome": None, "progress_records": [],
        "duration_expectations": [], "own_completed_action_history": []}
    history = return_history()
    saved = deepcopy(history)
    v4 = completed_action_context(original, pending_at_selection=PENDING, pending_after_action=PENDING,
        local_return_history_at_selection=history)
    assert v4 == {**v3, "version": "completed_action_estimation_context_v4",
                  "local_return_history_at_selection": saved}
    history["samples"].clear()
    original["original"]["snapshot"] = 99
    assert v4["local_return_history_at_selection"] == saved
    assert v4["original"]["snapshot"] == 2
    assert "current_completion" not in v4


def test_homology_declares_existing_controller_credit_split_without_projection():
    binding = HomologyEpisodes.__new__(HomologyEpisodes)
    binding.credit_binding = {"version": "operational-fixture"}
    binding.monitoring_binding = {"version": "monitoring-fixture"}
    for role, kind in (("job_launch", "operational"), ("job_monitor", "monitoring"),
                       ("job_results", "operational")):
        assert binding.credit_kind(role) == kind
        expected = binding.monitoring_binding if kind == "monitoring" else binding.credit_binding
        assert binding.binding_for(role) == expected
    with pytest.raises(ValueError, match="unknown_job_episode_role"):
        binding.credit_kind("guessed_job_role")
