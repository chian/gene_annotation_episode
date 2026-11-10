"""Real Store admission transactions with synthetic child science and forms.

These fixtures exercise receipt-driven credit and concurrent database users;
they make no claim about configured-model scientific investigation.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
import json
import threading

import pytest

from method_loop import ClosedRecord, EpisodeGoal
from method_loop.archive import JsonArchive
from method_loop.durable import canonical, content_digest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.episode_admission import (
    AdmissionError, ReceiverBindingV1, admit_return)
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.investigation_progress import (
    FindingProgressPolicy, ScientificFindingProgress)
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.state import Store
from test_investigation_progress import put_finding
from test_runtime import obj
from test_scientific_findings import target_question
from test_scientific_hypervolume_runtime import assessment, evidence


@dataclass(frozen=True)
class Value(ClosedRecord):
    value: dict

    def as_record(self):
        return self.value


def setup_case(tmp_path, *, pending=True, sourced=False):
    store = Store(tmp_path / "workspace")
    target, hypothesis = target_question(store)
    saved = put_finding(store, hypothesis, evidence(store, target, "alignment"), target)
    run_id = "admission-fixture-run"
    scope = store.validate_scope({"subject_refs": [target]})
    parent_goal = EpisodeGoal.root(objective="Resolve the synthetic question", result_contract={})
    child_goal = EpisodeGoal.child(parent_goal, objective="Investigate selected evidence", result_contract={})
    parent_path = [["annotation", "root"]]
    child_path = parent_path + [["improvement", "child_7"]]
    parent_id = EpisodeRef(run_id, parent_path).episode_id
    child_id = EpisodeRef(run_id, child_path).episode_id
    schema = obj({"findings": {"type": "array", "items": {"type": "string",
        "format": "reference", "x-reference-namespace": "assessment"}}})
    if sourced:
        schema["properties"]["findings"]["x-source"] = "changed_assessment_refs"
    contract = TypedReportContract("Return requested findings", schema,
        lambda ref, namespace=None: ref in store.reference_subset([ref], scope)
        and (namespace is None or store.get(ref)["record_type"] == namespace))
    parent_request = {"goal": parent_goal.as_record(), "message": {"scope": scope},
                      "report_contract": None}
    child_request = {"goal": child_goal.as_record(), "message": {"scope": scope},
                     "report_contract": contract.as_record()}
    spec = {"version": "episode_commission_v1", "handle": "selected-child-handle",
        "operation_key": "opaque-operation-without-index", "run_id": run_id,
        "parent": {"episode_id": parent_id, "goal_id": parent_goal.goal_id, "path": parent_path},
        "child": {"episode_id": child_id, "role": "improvement", "key": "child_7",
                  "path": child_path, "request": child_request, "scope": scope},
        "input_versions": [], "runtime_binding": {"factory_module": "fixture",
            "factory_name": "open_commission", "arguments": {},
            "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64},
        "constraints": {}, "resource_selection": None,
        "expectation_snapshot_refs": ["original-duration-expectation"]}
    journal = Journal(store, run_id)
    for eid, path, request, state in ((parent_id, parent_path, parent_request, "active"),
                                    (child_id, child_path, child_request, "yielded")):
        journal.save("runtime_episodes", {"episode_id": eid, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": state,
            "completion": None, "archive": None})
    action = {"kind": "child", "goal": "Investigate selected evidence", "scope": scope}
    journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7,
        "action": canonical(action), "result": canonical({"status": "pending",
            "pending_handle": spec["handle"]}) if pending else None,
        "credit": None, "timing": canonical({"original": "timing"})})
    journal.save("runtime_model_calls", {"episode_id": parent_id, "call_index": 7,
        "purpose": "decision", "request": canonical({"original_forecast": {"mean": 19}}),
        "response": canonical({"selection": action})})
    journal.save("runtime_forms", {"episode_id": child_id,
        "facts": canonical({"changed_assessment_refs": [saved["id"]],
                            "changed_record_refs": [saved["id"]], "credit": 123}),
        "form": canonical({"findings": [saved["id"]]})})
    receipts = EpisodeReceipts(store, run_id)
    receipts.bind(parent_id)
    receipts.bind(child_id, parent_id)
    archive = JsonArchive(tmp_path / "archive")
    returned = {"version": "returned_episode_v1", "handle": spec["handle"],
        "return_id": "", "commission_sha256": content_digest(spec),
        "returned_at": "2026-10-21T12:00:00+00:00", "outcome": "closed",
        "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 3},
        "episode_archive": archive.store({"synthetic_own_actions": 3}).descriptor(),
        "result_archive": archive.store({"form": {"findings": [saved["id"]]}}).descriptor(),
        "form": {"findings": [saved["id"]]},
        "facts_archive": archive.store({"changed_assessment_refs": [saved["id"]]}).descriptor(),
        "pending_handles": [], "failure": None}
    seal_return(returned)
    return store, spec, returned, contract, saved, receipts


def seal_return(returned):
    returned["return_id"] = content_digest({k: v for k, v in returned.items() if k != "return_id"})


def receiver_for(store, spec, contract, receipts, *, projector=None):
    scorer = ScientificFindingProgress(FindingProgressPolicy(5))
    parent_id, scope = spec["parent"]["episode_id"], spec["child"]["scope"]
    # Every concurrent/restored receiver resolves against its own connection.
    contract = TypedReportContract(contract.decision, contract.schema,
        lambda ref, namespace=None: ref in store.reference_subset([ref], scope)
        and (namespace is None or store.get(ref)["record_type"] == namespace))

    def receive(form):
        refs = form["findings"]
        receipts.receive(parent_id, refs, kind="child_form", source_index=7)
        return refs

    return ReceiverBindingV1(store, Journal(store, spec["run_id"]), 7, contract,
        lambda form: None, receive, projector or (lambda: scorer(store, scope,
            known_assessment_refs=receipts.known(parent_id, record_type="assessment"))["credit"]),
        lambda index, credit: Value({"credit": credit, "estimation_action_index": index}))


@pytest.mark.parametrize("pending", [False, True])
def test_admission_completes_original_action_and_replays_frozen_received_credit(tmp_path, pending):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path, pending=pending, sourced=True)
    with store:
        receiver = receiver_for(store, spec, contract, receipts)
        original_call = tuple(store.db.execute("SELECT * FROM runtime_model_calls").fetchone())
        admitted = admit_return(spec, returned, receiver)
        assert admitted["state"] == "admitted"
        assert admitted["original_decision_index"] == 7
        assert admitted["controller_input"] == {"credit": 5, "estimation_action_index": 7}
        assert admitted["received_record_refs"] == [saved["id"]]
        action = receiver.journal.row("runtime_actions", spec["parent"]["episode_id"], 7)
        assert json.loads(action["result"])["record_refs"] == [saved["id"]]
        assert json.loads(action["result"])["changed_record_refs"] == [saved["id"]]
        assert action["credit"] == 5 and json.loads(action["timing"]) == {"original": "timing"}
        assert tuple(store.db.execute("SELECT * FROM runtime_model_calls").fetchone()) == original_call
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        snapshot = store.db.execute("SELECT expectation_snapshot_refs,credit_snapshot FROM "
                                    "runtime_return_admissions").fetchone()
        assert json.loads(snapshot[0]) == spec["expectation_snapshot_refs"] and snapshot[1] == 5
        # Scientific withdrawal changes today's projection; history remains the
        # actual original parent receipt and is never repriced on replay.
        put_finding(store, saved["hypothesis_ref"], store.get(saved["observation_ref"]),
                    saved["investigation_finding"]["source_claim"]["subject_refs"][0],
                    revision=saved["revision"], withdraw=True)
        def must_not_reproject():
            raise AssertionError("replay projected new historical credit")
        replay = admit_return(spec, returned, replace(receiver,
            project_received_credit=must_not_reproject,
            receive_references=lambda form: (_ for _ in ()).throw(AssertionError("redelivery"))))
        assert replay == admitted
    # A new connection recovers the same immutable row without a live receiver.
    with Store(tmp_path / "workspace") as reopened:
        new_receipts = EpisodeReceipts(reopened, spec["run_id"])
        receiver = receiver_for(reopened, spec, contract, new_receipts, projector=must_not_reproject)
        assert admit_return(spec, returned, receiver) == admitted


def test_failure_preserves_closed_child_work_and_supports_existing_redelivery(tmp_path):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path, sourced=True)
    with store:
        returned["form"]["findings"] = []  # Violates the actual recorded x-source fact.
        seal_return(returned)
        admitted = admit_return(spec, returned, receiver_for(store, spec, contract, receipts))
        assert admitted["state"] == "delivery_pending"
        assert admitted["delivery_failure"]["code"] == "report_delivery_failed"
        assert admitted["controller_input"] is None
        action = Journal(store, spec['run_id']).row('runtime_actions', spec['parent']['episode_id'], 7)
        assert action['credit'] is None and json.loads(action['result'])['status'] == 'pending'
        assert admitted["received_record_refs"] == [] and list(receipts.known(spec["parent"]["episode_id"])) == []
        assert store.get(saved["id"]) == saved
        attempt = store.db.execute("SELECT * FROM runtime_report_attempts").fetchone()
        assert json.loads(attempt["failure"])["reason"] == "recorded_fact_mismatch"
        assert attempt["child_episode_id"] == spec["child"]["episode_id"]
        assert store.db.execute("SELECT facts,form FROM runtime_forms").fetchone()["form"] is not None
        assert admit_return(spec, returned, receiver_for(store, spec, contract, receipts)) == admitted


def test_closed_receiver_keeps_return_without_receipt_action_or_projection_changes(tmp_path):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path)
    with store:
        receiver = receiver_for(store, spec, contract, receipts,
            projector=lambda: (_ for _ in ()).throw(AssertionError("closed projection")))
        store.db.execute("UPDATE runtime_episodes SET state='yielded' WHERE episode_id=?",
                         (spec["parent"]["episode_id"],))
        before = tuple(store.db.execute("SELECT * FROM runtime_actions").fetchone())
        result = admit_return(spec, returned, receiver)
        assert result["state"] == "receiver_closed" and result["controller_input"] is None
        assert tuple(store.db.execute("SELECT * FROM runtime_actions").fetchone()) == before
        for table in ("runtime_record_receipts", "runtime_report_attempts", "runtime_observations"):
            assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
        assert store.get(saved["id"]) == saved


def test_interruption_rolls_back_receipt_attempt_action_and_admission_together(tmp_path):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path)
    with store:
        receiver = receiver_for(store, spec, contract, receipts)
        def crash_after_receipt():
            # The second connection cannot see half-delivered work.
            with Store(tmp_path / "workspace") as other:
                assert other.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == 0
            raise KeyboardInterrupt("synthetic interruption after receipt")
        with pytest.raises(KeyboardInterrupt):
            admit_return(spec, returned, replace(receiver, project_received_credit=crash_after_receipt))
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        assert receiver.journal.row("runtime_actions", spec["parent"]["episode_id"], 7)["credit"] is None
        assert store.get(saved["id"]) == saved
        assert admit_return(spec, returned, receiver)["controller_input"]["credit"] == 5


def test_concurrent_connections_admit_exactly_once(tmp_path):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path)
    store.close()
    barrier, projected = threading.Barrier(2), []

    def worker():
        with Store(tmp_path / "workspace") as connection:
            own_receipts = EpisodeReceipts(connection, spec["run_id"])
            receiver = receiver_for(connection, spec, contract, own_receipts)
            original = receiver.project_received_credit
            def counted():
                projected.append(1)
                return original()
            barrier.wait(timeout=10)
            return admit_return(spec, returned, replace(receiver, project_received_credit=counted))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result(timeout=40) for future in futures]
    assert results[0] == results[1] and projected == [1]
    with Store(tmp_path / "workspace") as connection:
        assert connection.db.execute("SELECT count(*) FROM runtime_return_admissions").fetchone()[0] == 1
        assert connection.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE record_ref=?",
                                     (saved["id"],)).fetchone()[0] == 1


def test_changed_return_and_original_binding_are_identity_conflicts(tmp_path):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path)
    with store:
        receiver = receiver_for(store, spec, contract, receipts)
        admitted = admit_return(spec, returned, receiver)
        changed = deepcopy(returned)
        changed["returned_at"] = "2026-10-21T12:00:01+00:00"
        seal_return(changed)
        with pytest.raises(AdmissionError) as failure:
            admit_return(spec, changed, receiver)
        assert failure.value.failure["code"] == "identity_conflict"
        with pytest.raises(AdmissionError):
            admit_return(spec, returned, replace(receiver, original_decision_index=8))
        assert admit_return(spec, returned, receiver) == admitted


@pytest.mark.parametrize("outcome,code", [("execution_failed", "execution_failed"),
                                         ("interrupted", "interrupted_execution")])
def test_failed_execution_observes_original_attempt_without_admitting_child_science(tmp_path, outcome, code):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path)
    with store:
        returned.update(outcome=outcome, completion=None, episode_archive=None,
            result_archive=None, form=None, failure={"code": code,
                "affected_refs": [spec["handle"]], "diagnostic_ref": None,
                "partial_record_refs": [saved["id"]]})
        seal_return(returned)
        receiver = receiver_for(store, spec, contract, receipts)
        admitted = admit_return(spec, returned, receiver)
        assert admitted["state"] == "execution_failed"
        assert admitted["controller_input"] == {'credit': 0, 'estimation_action_index': 7}
        assert admitted['report'] is None
        assert admitted["delivery_failure"] == returned["failure"]
        action = receiver.journal.row("runtime_actions", spec["parent"]["episode_id"], 7)
        assert json.loads(action["result"])["status"] == ("interrupted" if outcome == "interrupted" else "failed")
        assert action["credit"] == 0
        for table in ("runtime_record_receipts", "runtime_report_attempts", "runtime_observations"):
            assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
        assert store.get(saved["id"]) == saved
        assert admit_return(spec, returned, receiver) == admitted


def test_concurrent_revision_conflict_preserves_partial_child_work_before_admission(tmp_path):
    store, spec, returned, contract, saved, receipts = setup_case(tmp_path)
    store.close()
    barrier = threading.Barrier(2)

    def update(index):
        with Store(tmp_path / "workspace") as connection:
            payload = {name: [] for name in connection.reasoning_schema()["required"]}
            payload["hypotheses"] = [{"alias": "partial", "subject_refs": spec["child"]["scope"]["subject_refs"],
                "predicate": "biological_role",
                "value": {"type": "enum", "value": "negative" if index else "positive"}, "context_refs": []}]
            row = assessment(saved["hypothesis_ref"], saved["observation_ref"], "incomparable",
                             revision=saved["revision"], alias="revision")
            row["investigation_finding"] = deepcopy(saved["investigation_finding"])
            row["investigation_finding"]["source_claim"]["value"]["value"] = "negative" if index else "unresolved"
            payload["assessments"] = [row]
            barrier.wait(timeout=10)
            return connection.commit_reasoning(payload, spec["child"]["scope"], "revision-attempt:" + str(index))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, range(2)))
    assert sorted(row["status"] for row in results) == ["completed", "partial"], results
    partial = next(row for row in results if row["status"] == "partial")
    assert partial["conflicts"] and len(partial["record_refs"]) == 1
    with Store(tmp_path / "workspace") as connection:
        # The losing worker's independent valid hypothesis and original child
        # work survive. Returning an obsolete assessment cannot silently claim
        # the newer unreceived revision's information.
        assert connection.get(partial["record_refs"][0])["record_type"] == "hypothesis"
        assert connection.get(saved["id"]) == saved
        assert connection.db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 1
        own_receipts = EpisodeReceipts(connection, spec["run_id"])
        result = admit_return(spec, returned, receiver_for(connection, spec, contract, own_receipts))
        assert result["state"] == "admitted" and result["controller_input"]["credit"] == 0
        assert result["received_record_refs"] == [saved["id"]]


def test_journal_constructor_and_timing_participate_in_outer_transaction(tmp_path):
    with Store(tmp_path / "workspace") as store:
        with pytest.raises(RuntimeError, match="rollback"):
            with store.transaction():
                journal = Journal(store, "run")
                journal.save("runtime_actions", {"episode_id": "parent", "decision_index": 0,
                    "action": "{}", "result": None, "credit": None})
                with journal.measure("runtime_actions", "parent", 0):
                    pass
                assert store.db.in_transaction
                raise RuntimeError("rollback")
        assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='runtime_actions'").fetchone()[0] == 0
