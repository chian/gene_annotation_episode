"""Real Store completion/recovery boundaries with synthetic action payloads.

No configured model, native work, controller advancement or backend runs here.
The admission checks use C4's actual form/receipt transaction.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
import json
import threading

import pytest

from method_loop import ClosedRecord
from method_loop.durable import canonical
from method_loop.identities import UnitRef

from gene_annotation_episode.episode_admission import admit_return
from gene_annotation_episode.episode_completion import (
    CompletionLedger, EFFECT_VERSION, SLOT_VERSION, SOURCE_RESTORE_VERSION)
from gene_annotation_episode.episode_journal import Journal, WorkflowError
from gene_annotation_episode.state import Store
from test_episode_admission import receiver_for, seal_return, setup_case


@dataclass(frozen=True)
class Value(ClosedRecord):
    value: dict

    def as_record(self):
        return self.value


def action(journal, index, *, episode="parent", kind="tool", result="completed", credit=0):
    outcome = {"status": result, "record_refs": [], "changed_record_refs": []}
    journal.save("runtime_actions", {"episode_id": episode, "decision_index": index,
        "action": canonical({"kind": kind, "fixture_selection": index}),
        "result": None if result is None else canonical(outcome), "credit": credit})


def call(journal, index, *, episode="parent", response=True):
    journal.save("runtime_model_calls", {"episode_id": episode, "call_index": index,
        "purpose": "decision", "request": canonical({"original_context": index}),
        "response": canonical({"fixture_selection": index}) if response else None})


def effect(state="selected", *, value=1, feedback=None):
    return {"version": EFFECT_VERSION, "state": state,
        "report_values": {"interpretation": value}, "report_basis_refs": ["original-record"],
        "feedback": feedback}


def stage(ledger, index, credit=0, *, episode="parent"):
    return ledger.stage(episode, index, label=f"tool:{index}", kind="own_action",
        controller_input=Value({"credit": credit, "estimation_action_index": index,
            "original_expectation": {"mean_seconds": 19, "unknown_queue_wait": None}}),
        child_return=None)


def observation(slot):
    return {"label": slot["label"], "credit": deepcopy(slot["controller_input"]),
        "step": {"completed_count": slot["sequence"] + 1, "raw_gain": -1},
        "unit_ref": UnitRef(slot["episode_id"], slot["sequence"]).as_record(),
        "decision_index": slot["original_decision_index"]}


def child_reference(admission):
    return {name: admission[name] for name in ("handle", "return_id", "admission_id")}


def child_stage(ledger, spec, admitted):
    return ledger.stage(spec["parent"]["episode_id"], admitted["original_decision_index"],
        label="improvement:7", kind="child_return",
        controller_input=Value(admitted["controller_input"]),
        child_return=child_reference(admitted))


def count_if_installed(store, table):
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone()
    return store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] if exists else 0


def test_completion_order_and_original_inputs_survive_real_store_reopen(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        journal = Journal(store, "original-run")
        ledger = CompletionLedger(store, journal)
        for index, credit in ((3, 5.25), (1, 2.0), (4, 2.125)):
            action(journal, index, credit=credit)
        slots = [stage(ledger, 3, 5.25), stage(ledger, 1, 2.0)]
        # Latest completion is a completion-order fact, not max(decision_index).
        assert ledger.restore_source("parent")["last_completed_decision_index"] == 1
        slots.append(stage(ledger, 4, 2.125))
        for saved in slots:
            ledger.confirm_observed("parent", saved["sequence"], observation(saved))
        assert [saved["original_decision_index"] for saved in slots] == [3, 1, 4]
        assert [saved["sequence"] for saved in slots] == [0, 1, 2]
    with Store(path) as reopened:
        ledger = CompletionLedger(reopened, Journal(reopened, "original-run"))
        assert [ledger.slot("parent", index) for index in range(3)] == slots
        assert ledger.slot("parent", 3) is None
        for saved in slots:
            # No projector/callback is supplied to restoration or staging.
            assert stage(ledger, saved["original_decision_index"],
                         saved["controller_input"]["credit"]) == saved
            ledger.confirm_observed("parent", saved["sequence"], observation(saved))
        recorded = [json.loads(row[0]) for row in reopened.db.execute(
            "SELECT observation FROM runtime_observations ORDER BY unit_index")]
        assert recorded == [observation(saved) for saved in slots]
        assert [row["credit"]["credit"] for row in recorded] == [5.25, 2.0, 2.125]
        assert ledger.restore_source("parent")["unfinished_own_action_indices"] == []


def test_crash_before_on_unit_leaves_one_replayable_slot(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        action(journal, 9, credit=1.125)
        original = stage(ledger, 9, 1.125)
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    with Store(path) as reopened:
        ledger = CompletionLedger(reopened, Journal(reopened, "run"))
        assert ledger.slot("parent", 0) == original
        ledger.confirm_observed("parent", 0, observation(original))
        ledger.confirm_observed("parent", 0, observation(original))
        assert reopened.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        assert ledger.slot("parent", 1) is None


def test_concurrent_connections_allocate_once_and_preserve_committed_order(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        journal = Journal(store, "run")
        CompletionLedger(store, journal)
        for index in (1, 3, 4):
            action(journal, index)
    barrier = threading.Barrier(4)

    def worker(index):
        with Store(path) as store:
            ledger = CompletionLedger(store, Journal(store, "run"))
            barrier.wait(timeout=10)
            return stage(ledger, index)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(worker, (3, 1, 3, 4)))
    assert results[0] == results[2]
    assert sorted({saved["sequence"] for saved in results}) == [0, 1, 2]
    with Store(path) as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        for saved in results:
            assert ledger.slot("parent", saved["sequence"]) == saved
        assert store.db.execute("SELECT count(*) FROM runtime_completion_slots").fetchone()[0] == 3


def test_staged_values_are_detached_and_changed_replay_conflicts(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        action(journal, 0)
        value = {"credit": 0, "original": [1, 2]}
        saved = ledger.stage("parent", 0, label="original", kind="own_action",
            controller_input=Value(value), child_return=None)
        value["original"].append(3)
        saved["controller_input"]["original"].append(4)
        assert ledger.slot("parent", 0)["controller_input"] == {"credit": 0, "original": [1, 2]}
        for changed in ({"label": "changed"}, {"controller_input": Value(value)}):
            arguments = dict(label="original", kind="own_action",
                controller_input=Value({"credit": 0, "original": [1, 2]}), child_return=None)
            with pytest.raises(WorkflowError, match="completion_identity_conflict"):
                ledger.stage("parent", 0, **(arguments | changed))
        assert ledger.slot("parent", 1) is None


@pytest.mark.parametrize("field", ["label", "credit", "step", "unit_ref", "decision_index"])
def test_confirmation_rejects_changed_controller_observation(tmp_path, field):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        action(journal, 3)
        saved = stage(ledger, 3)
        original = observation(saved)
        ledger.confirm_observed("parent", 0, original)
        changed = deepcopy(original)
        changed[field] = ({"credit": 99} if field == "credit" else {"changed": True}
                          if field in {"step", "unit_ref"} else 77)
        with pytest.raises(WorkflowError, match="completion_observation_conflict"):
            ledger.confirm_observed("parent", 0, changed)
        assert json.loads(journal.row("runtime_observations", "parent", 0)["observation"]) == original


def test_admission_and_completion_rollback_together_and_replay_original_credit(tmp_path):
    store, spec, returned, contract, finding, receipts = setup_case(tmp_path, sourced=True)
    with store:
        journal = Journal(store, spec["run_id"])
        ledger = CompletionLedger(store, journal)
        receiver = receiver_for(store, spec, contract, receipts)
        with pytest.raises(KeyboardInterrupt):
            with store.transaction():
                admitted = admit_return(spec, returned, receiver)
                child_stage(ledger, spec, admitted)
                assert store.db.in_transaction
                raise KeyboardInterrupt("crash after admission and stage")
        for table in ("runtime_return_admissions", "runtime_record_receipts",
                      "runtime_report_attempts", "runtime_completion_slots", "runtime_observations"):
            assert count_if_installed(store, table) == 0
        assert journal.row("runtime_actions", spec["parent"]["episode_id"], 7)["credit"] is None
        with store.transaction():
            admitted = admit_return(spec, returned, receiver)
            saved = child_stage(ledger, spec, admitted)
        assert saved["sequence"] == 0 and saved["controller_input"]["credit"] == 5
    with Store(tmp_path / "workspace") as reopened:
        ledger = CompletionLedger(reopened, Journal(reopened, spec["run_id"]))
        def forbidden():
            raise AssertionError("recovery must not project or receive again")
        replay_receiver = receiver_for(reopened, spec, contract, receipts, projector=forbidden)
        replay_receiver = replace(replay_receiver, receive_references=lambda form: forbidden())
        original = admit_return(spec, returned, replay_receiver)
        assert original == admitted
        assert child_stage(ledger, spec, original) == saved
        ledger.confirm_observed(spec["parent"]["episode_id"], 0, observation(saved))
        assert ledger.slot(spec["parent"]["episode_id"], 1) is None


def test_closed_child_delivery_failure_still_stages_one_original_completion(tmp_path):
    store, spec, returned, contract, finding, receipts = setup_case(tmp_path, sourced=True)
    with store:
        ledger = CompletionLedger(store, Journal(store, spec["run_id"]))
        returned["form"]["findings"] = []
        seal_return(returned)
        with store.transaction():
            admitted = admit_return(spec, returned, receiver_for(store, spec, contract, receipts))
            saved = child_stage(ledger, spec, admitted)
        assert admitted["state"] == "delivery_failed"
        assert saved["controller_input"]["credit"] == 0
        assert store.get(finding["id"]) == finding
        assert child_stage(ledger, spec, admitted) == saved
        assert ledger.slot(spec["parent"]["episode_id"], 1) is None


def test_child_reference_must_match_the_actual_c4_admission(tmp_path):
    store, spec, returned, contract, finding, receipts = setup_case(tmp_path)
    with store:
        ledger = CompletionLedger(store, Journal(store, spec["run_id"]))
        admitted = admit_return(spec, returned, receiver_for(store, spec, contract, receipts))
        for field in ("handle", "return_id", "admission_id"):
            changed = child_reference(admitted) | {field: "different"}
            with pytest.raises(WorkflowError, match="completion_child_admission_conflict"):
                ledger.stage(spec["parent"]["episode_id"], 7, label="child:7", kind="child_return",
                    controller_input=Value(admitted["controller_input"]), child_return=changed)
        assert ledger.slot(spec["parent"]["episode_id"], 0) is None


def test_failed_execution_c4_input_is_null_and_cannot_stage(tmp_path):
    store, spec, returned, contract, finding, receipts = setup_case(tmp_path)
    with store:
        ledger = CompletionLedger(store, Journal(store, spec["run_id"]))
        returned.update(outcome="execution_failed", completion=None, episode_archive=None,
            result_archive=None, form=None, failure={"code": "execution_failed",
                "affected_refs": [spec["handle"]], "diagnostic_ref": None,
                "partial_record_refs": [finding["id"]]})
        seal_return(returned)
        def forbidden():
            raise AssertionError("failed execution has no completion projection")
        receiver = receiver_for(store, spec, contract, receipts, projector=forbidden)
        admitted = admit_return(spec, returned, receiver)
        assert admitted["controller_input"] is None
        with pytest.raises(TypeError, match="json_object"):
            child_stage(ledger, spec, admitted)
        assert ledger.slot(spec["parent"]["episode_id"], 0) is None
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_null_or_unrecorded_completion_cannot_create_an_observation(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        with pytest.raises(TypeError, match="closed_record"):
            ledger.stage("parent", 0, label="failed:0", kind="own_action",
                controller_input=None, child_return=None)
        action(journal, 0, result="failed", credit=None)
        with pytest.raises(WorkflowError, match="recorded_outcome_and_credit"):
            stage(ledger, 0)
        with pytest.raises(ValueError):
            ledger.stage("parent", 0, label="failed:0", kind="own_action",
                controller_input=Value({"credit": float("nan")}), child_return=None)
        assert ledger.slot("parent", 0) is None


def test_source_restores_rejections_redelivery_and_unfinished_ordinary_work(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        for index in range(8):
            call(journal, index, response=index != 7)
        action(journal, 0, credit=2)
        stage(ledger, 0, 2)
        ledger.record_decision_effect("parent", 0, effect(value=0))
        rejected = effect("rejected", value=0,
            feedback={"status": "invalid", "category": "action_contract", "detail": "bad selection"})
        ledger.record_decision_effect("parent", 1, rejected)
        ledger.record_decision_effect("parent", 2, effect("redelivery", value=2))
        action(journal, 3, result=None, credit=None)
        action(journal, 4, kind="episode_child", result="pending", credit=None)
        store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND "
            "episode_id='parent' AND decision_index=4",
            (canonical({"status": "pending", "pending_handle": "child-handle"}), journal.run_id))
        action(journal, 5, result="failed", credit=None)
        latest = effect(value=4)
        for index in (3, 4, 5):
            ledger.record_decision_effect("parent", index, latest if index == 5 else effect(value=index))
        # Response 6 exists, but selection/effect commit was interrupted.  It
        # must be revisited before the in-flight unanswered call at index 7.
        action(journal, 6, result="partial", credit=None)
        restored = ledger.restore_source("parent")
        assert restored == {"version": SOURCE_RESTORE_VERSION, "next_call_index": 6,
            "latest_effect": latest, "latest_effect_index": 5, "last_completed_decision_index": 0,
            "unfinished_own_action_indices": [3, 5, 6], "source_state": None}
        assert ledger.record_decision_effect("parent", 1, rejected) == rejected
        with pytest.raises(WorkflowError, match="decision_effect_identity_conflict"):
            ledger.record_decision_effect("parent", 1, effect("rejected", value=999))
    with Store(path) as reopened:
        ledger = CompletionLedger(reopened, Journal(reopened, "run"))
        assert ledger.restore_source("parent") == restored
        ledger.record_decision_effect("parent", 6, effect(value=6))
        assert ledger.restore_source("parent")["next_call_index"] == 7
        with pytest.raises(WorkflowError, match="saved_response"):
            ledger.record_decision_effect("parent", 7, effect("rejected"))


def test_effect_and_selected_action_share_outer_rollback(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        call(journal, 0)
        with pytest.raises(WorkflowError, match="saved_action"):
            ledger.record_decision_effect("parent", 0, effect())
        with pytest.raises(RuntimeError, match="rollback"):
            with store.transaction():
                action(journal, 0, result=None, credit=None)
                ledger.record_decision_effect("parent", 0, effect())
                raise RuntimeError("rollback")
        assert journal.row("runtime_actions", "parent", 0) is None
        assert ledger.restore_source("parent")["next_call_index"] == 0
        assert ledger.restore_source("parent")["latest_effect"] is None


def test_episode_and_run_scopes_and_legacy_calls_do_not_invent_order(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "first-run")
        ledger = CompletionLedger(store, journal)
        call(journal, 0)
        action(journal, 0)
        call(journal, 1)
        # Legacy actions/calls have no recoverable historical completion order.
        assert ledger.slot("parent", 0) is None
        assert ledger.restore_source("parent")["next_call_index"] == 0
        for episode in ("parent", "sibling"):
            action(journal, 0, episode=episode)
            assert stage(ledger, 0, episode=episode)["sequence"] == 0
        other_journal = Journal(store, "second-run")
        other = CompletionLedger(store, other_journal)
        assert other.slot("parent", 0) is None
        assert other.restore_source("parent")["latest_effect"] is None
        assert other.restore_source("parent")["next_call_index"] == 0
        action(other_journal, 0)
        assert stage(other, 0)["version"] == SLOT_VERSION


def test_constructor_joins_outer_store_transaction(tmp_path):
    with Store(tmp_path / "workspace") as store:
        with pytest.raises(RuntimeError, match="rollback"):
            with store.transaction():
                journal = Journal(store, "run")
                CompletionLedger(store, journal)
                raise RuntimeError("rollback")
        for table in ("runtime_completion_slots", "runtime_decision_effects", "runtime_actions"):
            assert store.db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone() is None
