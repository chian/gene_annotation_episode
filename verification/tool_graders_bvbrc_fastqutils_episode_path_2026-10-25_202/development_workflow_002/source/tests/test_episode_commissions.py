"""Real Store selection/recovery with an explicit C2 execution fixture.

No model, subprocess, scientific finding or controller execution is claimed.
The fixture uses the real backend's immutable commission store, replacing only
start/status so these checks cannot accidentally run a child investigation.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import threading

import pytest

from method_loop import EpisodeGoal
from method_loop.communication import ReportContract
from method_loop.durable import DurableExecutionStore, canonical, content_digest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.episode_commissions import CommissionCoordinator, CommissionError
from gene_annotation_episode.episode_journal import Journal, WorkflowError
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store
from gene_annotation_episode.waiting import validate_pending


class BackendFixture:
    """C2 port: real immutable publication; explicitly simulated execution."""
    def __init__(self, directory, *, store=None):
        self.durable = DurableExecutionStore(directory)
        self.store = store
        self.calls, self.started, self.overrides = [], set(), {}
        self.fail_publication = False

    def commission(self, spec):
        if self.store is not None:
            assert not self.store.db.in_transaction
            # A second connection sees BOTH pieces before any publication.
            with Store(self.store.path) as other:
                action = other.db.execute("SELECT result,credit FROM runtime_actions "
                    "WHERE episode_id=?", (spec["parent"]["episode_id"],)).fetchone()
                assert json.loads(action[0])["pending_handle"] == spec["handle"]
                assert action[1] is None
                assert other.db.execute("SELECT count(*) FROM runtime_commission_intents "
                    "WHERE handle=?", (spec["handle"],)).fetchone()[0] == 1
        self.calls.append(("commission", spec["handle"]))
        if self.fail_publication:
            raise OSError("fixture backend unavailable before publication")
        return self.durable.commission(spec)

    def start(self, handle):
        assert self.store is None or not self.store.db.in_transaction
        self.calls.append(("start", handle))
        self.started.add(handle)  # C2's idempotent physical identity, simulated.
        return self.status(handle)

    def status(self, handle):
        self.calls.append(("status", handle))
        return {**self.durable.status(handle), **self.overrides.get(handle, {})}

    def load_commission(self, handle):
        return self.durable.load_commission(handle)


def setup_case(tmp_path, *, run_id="commission-fixture", parent_key="root"):
    store = Store(tmp_path / "workspace")
    if not store.db.execute("SELECT 1 FROM problem").fetchone():
        store.create_problem(raw_sequence="ATGTGATAA", molecule="dna", role="gene")
    scope = store.validate_scope()
    target = scope["subject_refs"][0]
    artifact = store.artifact("Original supplied bytes α", "text/plain")
    source = store.put("source", {"provider": "fixture", "accession": "original",
        "uri": None, "artifact_ref": artifact, "text_ref": artifact,
        "request_ref": None, "version": "original-v1", "retrieved_at": None}, origin="caller")
    parent_goal = EpisodeGoal.root(objective="Synthetic assigned question", result_contract={})
    child_goal = EpisodeGoal.child(parent_goal, objective="Selected bounded work", result_contract={})
    parent_path = [["annotation", parent_key]]
    child_path = parent_path + [["improvement", "child_7"]]
    parent_id = EpisodeRef(run_id, parent_path).episode_id
    child_id = EpisodeRef(run_id, child_path).episode_id
    schema = {"type": "object", "properties": {"finding": {"enum": ["unknown", "qualified"]}},
              "required": ["finding"], "additionalProperties": False}
    contract = ReportContract("Return requested bounded interpretation", {"schema": schema},
                              {"finding": "Requested evidence qualification"})
    parent_request = {"goal": parent_goal.as_record(), "message": {"scope": scope},
                      "report_contract": None}
    receipts = EpisodeReceipts(store, run_id)
    receipts.bind(parent_id)
    inheritance = receipts.bind(child_id, parent_id)
    child_request = {"goal": child_goal.as_record(), "message": {
        "scope": scope, "initial_report": {"finding": "unknown"},
        "knowledge_inheritance": inheritance}, "report_contract": contract.as_record()}
    journal = Journal(store, run_id)
    for episode_id, path, request in ((parent_id, parent_path, parent_request),
                                      (child_id, child_path, child_request)):
        journal.save("runtime_episodes", {"episode_id": episode_id,
            "path": canonical(path), "request": canonical(request), "initial_credit": 0,
            "state": "active", "completion": None, "archive": None})
    selection = {"kind": "child", "goal": "Selected bounded work", "scope": scope}
    operands = {"parent": {"episode_id": parent_id, "goal_id": parent_goal.goal_id,
                           "path": parent_path},
        "child": {"episode_id": child_id, "role": "improvement", "key": "child_7",
                  "path": child_path, "request": child_request, "scope": scope},
        "original_decision_index": 7, "selection": selection,
        "runtime_binding": {"factory_module": "fixture", "factory_name": "open_commission",
            "arguments": {"original_settings_file": "saved-caller-settings.json"},
            "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64},
        "input_versions": [{"reference": source["id"], "version": "original-v1",
                            "content_sha256": content_digest(source)},
                           {"reference": artifact, "version": None,
                            "content_sha256": hashlib.sha256(store.get_artifact(artifact)).hexdigest()},
                           {"reference": target, "version": None,
                            "content_sha256": content_digest(store.get(target))}],
        "constraints": {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3,
                        "wall_seconds": None, "caller_cpu": 2},
        "resource_selection": {"resource_id": "caller-local", "kind": "local",
            "allocation": {"cpu": 2, "memory_bytes": 20 * 1024**3,
                           "scratch_bytes": 4 * 1024**3, "wall_seconds": None},
            "capability_binding_ref": "saved-caller-capability"},
        "expectation_snapshot_refs": ["original-duration-expectation"],
        "selected_at": "2026-10-21T12:00:00+00:00"}
    journal.save("runtime_model_calls", {"episode_id": parent_id, "call_index": 7,
        "purpose": "decision", "request": canonical({"original_forecast": {"mean": 19}}),
        "response": canonical({"selection": selection})})
    backend = BackendFixture(tmp_path / "backend", store=store)
    return store, journal, backend, operands, receipts


def test_committed_selection_recovers_crash_gap_and_original_inputs_without_credit(tmp_path):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        assert backend.calls == []
        assert spec["handle"] not in {spec["parent"]["episode_id"], spec["child"]["episode_id"]}
        original = deepcopy(spec)
        parent_id = spec["parent"]["episode_id"]
        action = journal.row("runtime_actions", parent_id, 7)
        assert json.loads(action["result"]) == {"status": "pending",
            "pending_handle": spec["handle"], "selected_at": operands["selected_at"]}
        assert action["credit"] is None
        before = tuple(store.db.execute("SELECT * FROM runtime_model_calls").fetchone())
        unpublished_snapshot = coordinator.pending(parent_id)
        validate_pending(unpublished_snapshot)
        unpublished = unpublished_snapshot["items"][0]
        assert unpublished["lifecycle_state"] == "pending"
        assert unpublished["observed_at"] == unpublished_snapshot["captured_at"]
        assert not unpublished["return_available"]
        assert unpublished["latest_progress_ref"] is None
        # New parent knowledge, a newer expectation, and caller mutation cannot
        # change an already selected child's inheritance or original snapshots.
        receipts.receive(parent_id, [operands["input_versions"][0]["reference"]],
                         kind="own_action", source_index=8)
        operands["input_versions"].clear()
        operands["expectation_snapshot_refs"].append("newer-expectation")
        operands["runtime_binding"]["settings_sha256"] = "c" * 64
        spec["child"]["request"]["message"]["scope"]["subject_refs"].clear()
        assert coordinator.recover_selected(parent_id) == [original]
        assert tuple(store.db.execute("SELECT * FROM runtime_model_calls").fetchone()) == before
        receipt_count = store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0]
    # The owner exited after Store commit, before any backend publication.
    with Store(tmp_path / "workspace") as reopened:
        journal = Journal(reopened, "commission-fixture")
        backend.store = reopened
        coordinator = CommissionCoordinator(reopened, journal, backend)
        assert coordinator.recover_selected(parent_id) == [original]
        assert coordinator.dispatch(original["handle"])["handle"] == original["handle"]
        assert backend.load_commission(original["handle"]) == original
        assert reopened.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == receipt_count
        assert reopened.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert reopened.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        assert journal.row("runtime_actions", parent_id, 7)["credit"] is None


def test_repeated_dispatch_uses_same_backend_identity_and_does_not_complete_action(tmp_path):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        original_action = journal.row("runtime_actions", spec["parent"]["episode_id"], 7)
        first = coordinator.dispatch(spec["handle"])
        second = coordinator.dispatch(spec["handle"])
        assert {key: value for key, value in first.items() if key != "observed_at"} == {
            key: value for key, value in second.items() if key != "observed_at"}
        assert backend.started == {spec["handle"]}
        assert [call[0] for call in backend.calls].count("start") == 2
        assert journal.row("runtime_actions", spec["parent"]["episode_id"], 7) == original_action
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_intent_and_original_action_roll_back_as_one_transaction(tmp_path):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        coordinator = CommissionCoordinator(store, journal, backend)
        store.db.execute("CREATE TRIGGER fixture_action_failure BEFORE INSERT ON runtime_actions "
                         "BEGIN SELECT RAISE(ABORT,'fixture action persistence failure'); END")
        with pytest.raises(CommissionError) as error:
            coordinator.select(**operands)
        assert error.value.failure["code"] == "storage_failure"
        assert coordinator.recover_selected(operands["parent"]["episode_id"]) == []
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
        assert backend.calls == []
        store.db.execute("DROP TRIGGER fixture_action_failure")
        # Both helpers join a caller transaction; publication cannot escape it.
        with pytest.raises(RuntimeError, match="rollback outer"):
            with store.transaction():
                spec = coordinator.select(**operands)
                with pytest.raises(WorkflowError, match="requires_committed_store_transaction"):
                    coordinator.dispatch(spec["handle"])
                assert backend.calls == []
                raise RuntimeError("rollback outer")
        assert coordinator.recover_selected(operands["parent"]["episode_id"]) == []
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0


@pytest.mark.parametrize("field", ["selection", "child", "selected_at", "input_versions",
                                  "expectation_snapshot_refs", "runtime_binding", "constraints",
                                  "resource_selection"])
def test_exact_replay_conflicts_on_changed_frozen_selection(tmp_path, field):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        changed = deepcopy(operands)
        if field == "selection":
            changed[field]["goal"] = "Changed original selection"
        elif field == "child":
            changed[field]["request"]["message"]["initial_report"]["finding"] = "qualified"
        elif field == "selected_at":
            changed[field] = "2026-10-21T12:00:01+00:00"
        elif field == "input_versions":
            changed[field][0]["version"] = "newer-v2"
        elif field == "expectation_snapshot_refs":
            changed[field] = ["newer-expectation"]
        elif field == "runtime_binding":
            changed[field]["settings_sha256"] = "d" * 64
        elif field == "constraints":
            changed[field]["caller_cpu"] = 4
        else:
            changed[field]["allocation"]["cpu"] = 4
        with pytest.raises(CommissionError) as error:
            coordinator.select(**changed)
        assert error.value.failure["code"] == "identity_conflict"
        assert coordinator.select(**operands) == spec
        assert backend.calls == []


def test_replay_preserves_existing_timing_forecast_completed_credit_and_closed_parent(tmp_path):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        parent_id = operands["parent"]["episode_id"]
        journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7,
            "action": canonical(operands["selection"]), "result": None, "credit": None,
            "timing": canonical({"original_measured_elapsed_seconds": 2.5})})
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        assert json.loads(journal.row("runtime_actions", parent_id, 7)["timing"]) == {
            "original_measured_elapsed_seconds": 2.5}
        journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7,
            "action": canonical(operands["selection"]),
            "result": canonical({"status": "completed", "record_refs": [], "changed_record_refs": []}),
            "credit": 5})
        store.db.execute("UPDATE runtime_episodes SET state='yielded' WHERE episode_id=?", (parent_id,))
        before = journal.row("runtime_actions", parent_id, 7)
        assert coordinator.select(**operands) == spec
        assert journal.row("runtime_actions", parent_id, 7) == before
        assert coordinator.pending(parent_id)["items"] == []
        assert coordinator.recover_selected(parent_id) == [spec]


def test_publication_failure_retains_selection_and_does_not_retry_backend(tmp_path):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        backend.fail_publication = True
        with pytest.raises(OSError, match="fixture backend unavailable"):
            coordinator.dispatch(spec["handle"])
        assert backend.calls == [("commission", spec["handle"])] and backend.started == set()
        assert coordinator.recover_selected(spec["parent"]["episode_id"]) == [spec]
        assert journal.row("runtime_actions", spec["parent"]["episode_id"], 7)["credit"] is None


@pytest.mark.parametrize("invalid", ["containment", "scope_message", "form", "input_version",
                                    "artifact_digest", "inheritance", "goal_parent"])
def test_initial_assignment_requires_actual_frozen_operands(tmp_path, invalid):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        parent_id, child_id = operands["parent"]["episode_id"], operands["child"]["episode_id"]
        if invalid == "containment":
            parent_request = json.loads(journal.row("runtime_episodes", parent_id)["request"])
            target = operands["child"]["scope"]["subject_refs"][0]
            parent_request["message"]["scope"] = {"subject_refs": [target],
                "segments": [{"target_ref": target, "start": 0, "end": 3, "unit": "nt"}]}
            store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
                             (canonical(parent_request), parent_id))
        elif invalid == "scope_message":
            operands["child"]["request"]["message"]["scope"] = {}
            store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
                (canonical(operands["child"]["request"]), child_id))
        elif invalid == "form":
            operands["child"]["request"]["report_contract"]["decision"] = "Replacement form"
        elif invalid == "input_version":
            operands["input_versions"][0]["version"] = "unsupplied-v2"
        elif invalid == "artifact_digest":
            operands["input_versions"][1]["content_sha256"] = "c" * 64
        elif invalid == "inheritance":
            operands["child"]["request"]["message"]["knowledge_inheritance"]["through_receipt_index"] = 999
            store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
                (canonical(operands["child"]["request"]), child_id))
        else:
            operands["child"]["request"]["goal"]["parent_goal_id"] = "unrelated-goal"
        coordinator = CommissionCoordinator(store, journal, backend)
        with pytest.raises(CommissionError):
            coordinator.select(**operands)
        assert coordinator.recover_selected(parent_id) == []
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
        assert backend.calls == []


def test_pending_exposes_only_own_original_actions_and_public_status(tmp_path):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    with store:
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        coordinator.dispatch(spec["handle"])
        backend.overrides[spec["handle"]] = {"lifecycle_state": "returned", "return_available": True,
            "return_id": "fixture-immutable-return", "observed_at": "2026-10-21T12:10:00+00:00"}
        pending = coordinator.pending(spec["parent"]["episode_id"])
        assert pending["version"] == "pending_work_v1"
        assert pending["items"] == [{"handle": spec["handle"], "role": "improvement",
            "lifecycle_state": "returned", "selected_at": operands["selected_at"],
            "observed_at": "2026-10-21T12:10:00+00:00",
            "resource_selection": operands["resource_selection"],
            "expectation_snapshot_refs": operands["expectation_snapshot_refs"],
            "latest_progress_ref": None, "return_available": True}]
        calls = deepcopy(backend.calls)
        assert coordinator.pending(spec["child"]["episode_id"])["items"] == []
        assert coordinator.recover_selected(spec["child"]["episode_id"]) == []
        assert backend.calls == calls
        other_run = CommissionCoordinator(store, Journal(store, "unrelated-run"), backend)
        assert other_run.pending(spec["parent"]["episode_id"])["items"] == []
        assert other_run.recover_selected(spec["parent"]["episode_id"]) == []


def test_two_store_connections_preserve_one_selection_under_concurrent_conflict(tmp_path):
    store, journal, backend, operands, receipts = setup_case(tmp_path)
    store.close()
    barrier = threading.Barrier(2)
    def select(index):
        with Store(tmp_path / "workspace") as connection:
            coordinator = CommissionCoordinator(connection, Journal(connection, "commission-fixture"), backend)
            selected = deepcopy(operands)
            selected["expectation_snapshot_refs"] = ["original-" + str(index)]
            barrier.wait(timeout=10)
            try:
                return coordinator.select(**selected)
            except CommissionError as error:
                return error.failure
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(select, index) for index in range(2)]
        results = [future.result(timeout=40) for future in futures]
    failures = [result for result in results if "code" in result]
    assert len(failures) == 1 and failures[0]["code"] == "identity_conflict"
    with Store(tmp_path / "workspace") as connection:
        coordinator = CommissionCoordinator(connection, Journal(connection, "commission-fixture"), backend)
        assert len(coordinator.recover_selected(operands["parent"]["episode_id"])) == 1
        assert connection.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
        assert connection.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    assert backend.calls == []
