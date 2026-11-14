"""Store-backed wait inputs; no model, child execution or estimator invocation.

The duration samples, controller observations and progress deliveries are
explicit fixtures. Public commission/progress ports retain their real storage
and scope checks; no native/scientific execution is claimed.
"""
from copy import deepcopy
import json

import pytest

from method_loop.durable import canonical
from method_loop.identities import UnitRef

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_commissions import CommissionCoordinator
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_monitoring import FIELDS, ProgressProvider
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory, RunStatistic
from gene_annotation_episode.state import Store
from gene_annotation_episode.wait_estimation_inputs import VERSION, WaitInputs
from test_episode_commissions import setup_case


STAMP = "2026-10-21T12:00:00+00:00"
EMPTY_PENDING = {"version": "pending_work_v1", "captured_at": STAMP, "items": []}


def execution_class(*, phase="protein_homology_search"):
    return ExecutionClass(phase=phase, backend="local", resource_id="caller-local",
        implementation_sha256="a" * 64, parameters_sha256="b" * 64,
        memory_bytes=20 * 2**30, scratch_bytes=4 * 2**30, cpu_threads=2,
        query_residues=253, reference_residues=1000, reference_records=10,
        reference_state="available")


def save_call(journal, episode_id, index, *, expectations=None, native=None, text=""):
    context = {"source_body": text}
    if expectations is not None:
        context["execution_expectations"] = expectations
    if native is not None:
        context["native_execution_expectations"] = native
    journal.save("runtime_model_calls", {"episode_id": episode_id, "call_index": index,
        "purpose": "decision", "request": canonical({"context": context, "schema": {}}),
        "response": canonical({"private_model_body": text})})


def save_episode(journal, episode_id, scope, *, text=""):
    journal.save("runtime_episodes", {"episode_id": episode_id,
        "path": canonical([["annotation", episode_id]]),
        "request": canonical({"goal": {"private_goal": text},
                              "message": {"scope": scope, "private_body": text}}),
        "initial_credit": 0, "state": "active", "completion": None, "archive": None})


def save_observation(journal, episode_id, unit, decision, *, credit, step, text=""):
    journal.save("runtime_observations", {"episode_id": episode_id, "unit_index": unit,
        "observation": canonical({"label": text, "credit": credit, "step": step,
            "unit_ref": UnitRef(episode_id, unit).as_record(), "decision_index": decision})})


def save_pending(journal, episode_id, index, handle, *, kind="child", text=""):
    journal.save("runtime_actions", {"episode_id": episode_id, "decision_index": index,
        "action": canonical({"kind": kind, "private_body": text}),
        "result": canonical({"status": "pending", "pending_handle": handle,
                             "selected_at": STAMP, "private_result_body": text}), "credit": None})


def capture_envelope(snapshot):
    return {"version": "episode_execution_expectation_binding_v3", "status": "available",
            "code": None, "execution_classes": [], "snapshots": [snapshot]}


def test_original_pending_snapshots_survive_new_history_and_reopen(tmp_path):
    history_path = tmp_path / "statistics.sqlite3"
    history = RunHistory(history_path)
    primary_class = execution_class()
    native_class = execution_class(phase="pairwise_sequence_alignment")
    primary = ExecutionExpectations(history_path, by_grain={"annotation": [primary_class]})
    native = ExecutionExpectations(history_path, by_grain={"annotation": [native_class]})
    original = primary.capture("annotation")
    original_native = native.capture("annotation")
    store, journal, backend, operands, _ = setup_case(tmp_path)
    with store:
        parent_id = operands["parent"]["episode_id"]
        operands["expectation_snapshot_refs"] = [row["ref"] for row in
            [*original["snapshots"], *original_native["snapshots"]]]
        save_call(journal, parent_id, 7, expectations=original, native=original_native)
        coordinator = CommissionCoordinator(store, journal, backend)
        coordinator.select(**operands)
        pending = coordinator.pending(parent_id)
        original_call = journal.row("runtime_model_calls", parent_id, 7)
        history.record(primary_class, RunStatistic(attempt_sha256="1" * 64,
            source_sha256="2" * 64, observed_at=STAMP, outcome="succeeded",
            duration_kind="complete", elapsed_seconds=29.5, condition_ref=None))
        current = primary.capture("annotation")
        assert current["snapshots"][0]["ref"] != original["snapshots"][0]["ref"]
        save_call(journal, parent_id, 99, expectations=current)
        backend.calls.clear()
        before_changes = store.db.total_changes
        expected = [*original["snapshots"], *original_native["snapshots"], *current["snapshots"]]
        value = WaitInputs(store, journal, None).capture(parent_id, pending=pending,
            known_progress_refs=[], current_duration_expectations=(current, original_native, current))
        assert value == {"version": VERSION, "progress_records": [],
                         "duration_expectations": expected, "own_completed_action_history": []}
        assert value["duration_expectations"][0]["data"]["history_through_sequence"] == 0
        assert value["duration_expectations"][2]["data"]["statistics"][0]["mean_seconds"] == 29.5
        assert journal.row("runtime_model_calls", parent_id, 7) == original_call
        assert store.db.total_changes == before_changes
        assert backend.calls == []
    history.close()
    # The original data is in the owning parent's saved decision, not a fresh
    # lookup of the shared statistics or a live object retained by the adapter.
    history_path.unlink()
    with Store(tmp_path / "workspace") as reopened:
        journal = Journal(reopened, journal.run_id)
        restored = WaitInputs(reopened, journal, None).capture(parent_id, pending=pending,
            known_progress_refs=[], current_duration_expectations=(current,))
        assert restored == value


@pytest.mark.parametrize("location", ["current_capture", "saved_native_capture"])
def test_same_reference_with_changed_data_conflicts_without_writes(tmp_path, location):
    store, journal, _, operands, _ = setup_case(tmp_path)
    with store:
        parent_id = operands["parent"]["episode_id"]
        snapshot = {"ref": "original-duration-expectation", "data": {"raw_mean_seconds": 19.25}}
        changed = deepcopy(snapshot)
        changed["data"]["raw_mean_seconds"] = 999
        save_call(journal, parent_id, 7, expectations=capture_envelope(snapshot),
            native=capture_envelope(changed) if location == "saved_native_capture" else None)
        save_pending(journal, parent_id, 7, "selected-handle")
        pending = deepcopy(EMPTY_PENDING)
        pending["items"] = [{"handle": "selected-handle", "role": "improvement",
            "lifecycle_state": "pending", "selected_at": STAMP, "observed_at": STAMP,
            "resource_selection": None, "expectation_snapshot_refs": [snapshot["ref"]],
            "latest_progress_ref": None, "return_available": False}]
        before = store.db.total_changes
        with pytest.raises(ValueError, match="duration_expectation_identity_conflict"):
            WaitInputs(store, journal, None).capture(parent_id, pending=pending, known_progress_refs=[],
                current_duration_expectations=(capture_envelope(changed),)
                    if location == "current_capture" else ())
        assert store.db.total_changes == before


def test_only_actual_own_observations_are_returned_in_completion_order_with_signed_values(tmp_path):
    with Store(tmp_path) as store:
        journal = Journal(store, "run")
        save_episode(journal, "parent", {"subject_refs": ["fixture-subject"]})
        original = [(2, 3, {"credit": 2.125}, {"delta": 0.125, "rank": 3}),
                    (0, 9, {"credit": 5.25}, {"delta": 5.25, "rank": 1}),
                    (1, 1, {"credit": 2.0, "estimation_context": {"raw": -7.25}},
                           {"delta": -3.25, "rank": 2, "band": [-4.125, -0.25]})]
        for unit, decision, credit, step in original:
            save_observation(journal, "parent", unit, decision, credit=credit, step=step)
        save_observation(journal, "child", 0, 0, credit={"credit": 1000}, step={"delta": 1000})
        another_run = Journal(store, "different-run")
        save_observation(another_run, "parent", 0, 0, credit={"credit": 2000}, step={"delta": 2000})
        # Failed/attempted/pending actions and staged but unobserved work supply
        # no synthetic history, regardless of their saved scalar credit.
        journal.save("runtime_actions", {"episode_id": "parent", "decision_index": 100,
            "action": canonical({"kind": "tool"}), "result": canonical({"status": "failed"}),
            "credit": None})
        save_pending(journal, "parent", 101, "pending-child")
        result = WaitInputs(store, journal, None).capture("parent", pending=EMPTY_PENDING,
            known_progress_refs=[])
        assert result["own_completed_action_history"] == [
            {"episode_id": "parent", "unit_index": unit, "decision_index": decision,
             "controller_input": credit, "controller_step": step}
            for unit, decision, credit, step in sorted(original)]
        assert all(set(row) == {"episode_id", "unit_index", "decision_index", "controller_input",
                               "controller_step"} for row in result["own_completed_action_history"])


def test_received_progress_uses_public_read_with_saved_scope_and_never_polls(tmp_path, monkeypatch):
    store, journal, backend, operands, _ = setup_case(tmp_path)
    with store:
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        backend.durable.commission(spec)  # Publish only; no process is started.
        pending = coordinator.pending(spec["parent"]["episode_id"])
        scope = spec["child"]["scope"]
        provider = ProgressProvider(store, backend.durable, run_id=journal.run_id)
        delivered = provider.observe(spec["handle"], list(FIELDS), scope)
        schema = {"type": "object", "properties": {"update": {"type": "string",
            "format": "reference", "x-reference-namespace": "episode_progress"}},
            "required": ["update"], "additionalProperties": False}
        parent_id = spec["parent"]["episode_id"]
        provider.receive_form(parent_id, {"update": delivered["progress_ref"]}, schema,
            scope, "actual-form-delivery")
        provider.expose(spec["handle"], operation_key="later-unreceived-exposure",
            provenance_refs=[operands["input_versions"][0]["reference"]])
        unreceived = provider.observe(spec["handle"], list(FIELDS), scope)
        assert delivered["progress_ref"] != unreceived["progress_ref"]
        pending["items"][0]["latest_progress_ref"] = unreceived["progress_ref"]
        reads = []
        public_read = provider.read_progress

        def read(reference, saved_scope):
            reads.append((reference, deepcopy(saved_scope)))
            return public_read(reference, saved_scope)

        def forbidden(*args, **kwargs):
            raise AssertionError("input capture must not poll or obtain new information")

        refs = provider.received_progress_refs(parent_id)
        monkeypatch.setattr(provider, "read_progress", read)
        monkeypatch.setattr(provider, "observe", forbidden)
        monkeypatch.setattr(provider, "direct_dependencies", forbidden)
        monkeypatch.setattr(backend.durable, "status", forbidden)
        before = store.db.total_changes
        result = WaitInputs(store, journal, provider).capture(parent_id, pending=pending,
            known_progress_refs=[*refs, *refs])
        assert result["progress_records"] == [delivered]
        assert reads == [(delivered["progress_ref"], scope)] * 2
        assert store.db.total_changes == before
        # A published/latest handle is not itself a delivered observation.
        assert WaitInputs(store, journal, provider).capture(parent_id, pending=pending,
            known_progress_refs=[])["progress_records"] == []
        with pytest.raises(ContractError, match="progress_reference_unavailable"):
            WaitInputs(store, journal, provider).capture(parent_id, pending=pending,
                known_progress_refs=["progress_unknown"])
        narrow = {"subject_refs": scope["subject_refs"], "segments": [{
            "target_ref": scope["subject_refs"][0], "start": 0, "end": 1, "unit": "nt"}]}
        save_episode(journal, "narrow-parent", narrow)
        with pytest.raises(ContractError, match="progress_reference_outside_scope"):
            WaitInputs(store, journal, provider).capture("narrow-parent", pending=pending,
                known_progress_refs=refs)
        assert reads[-1] == (delivered["progress_ref"], narrow)


def test_capture_joins_callers_read_snapshot_and_is_read_only(tmp_path):
    with Store(tmp_path) as store, Store(tmp_path) as other:
        journal = Journal(store, "run")
        writer = Journal(other, "run")
        save_episode(journal, "parent", {"subject_refs": ["fixture-subject"]})
        before = store.db.total_changes
        store.db.execute("PRAGMA query_only=ON")
        reader = WaitInputs(store, journal, None)
        with store.read_snapshot():
            empty = reader.capture("parent", pending=EMPTY_PENDING, known_progress_refs=[])
            assert empty == {"version": VERSION, "progress_records": [],
                             "duration_expectations": [], "own_completed_action_history": []}
            save_observation(writer, "parent", 0, 7, credit={"credit": 0}, step={"delta": 0})
            assert store.db.in_transaction
            assert reader.capture("parent", pending=EMPTY_PENDING, known_progress_refs=[]) == empty
            assert store.db.in_transaction
        later = reader.capture("parent", pending=EMPTY_PENDING, known_progress_refs=[])
        assert later["own_completed_action_history"][0]["decision_index"] == 7
        assert store.db.total_changes == before
        assert not store.db.in_transaction


def test_projections_exclude_old_context_source_bodies_unselected_refs_and_other_episodes(tmp_path):
    with Store(tmp_path) as store:
        journal = Journal(store, "run")
        marker = "OLD_PRIVATE_OR_SOURCE_BODY_MUST_NOT_ENTER_PYTHON"
        body = marker + "x" * 100000
        scope = {"subject_refs": ["fixture-subject"]}
        save_episode(journal, "parent", scope, text=body)
        selected = {"ref": "selected-duration", "data": {"mean_seconds": 9, "queue_wait": None}}
        hidden = {"ref": "unselected-duration", "data": {"private_body": body}}
        envelope = capture_envelope(selected)
        envelope["snapshots"].append(hidden)
        save_call(journal, "parent", 7, expectations=envelope, text=body)
        save_pending(journal, "parent", 7, "selected-handle", text=body)
        save_call(journal, "child", 7, expectations=capture_envelope(hidden), text=body)
        save_pending(journal, "child", 7, "selected-handle", text=body)
        other_run = Journal(store, "another-run")
        save_call(other_run, "parent", 7, expectations=capture_envelope(hidden), text=body)
        save_pending(other_run, "parent", 7, "selected-handle", text=body)
        save_observation(journal, "parent", 0, 3,
            credit={"credit": 1.25}, step={"delta": -0.25}, text=body)
        save_observation(journal, "child", 0, 3,
            credit={"private_body": body}, step={"private_body": body})
        pending = deepcopy(EMPTY_PENDING)
        pending["items"] = [{"handle": "selected-handle", "role": "improvement",
            "lifecycle_state": "pending", "selected_at": STAMP, "observed_at": STAMP,
            "resource_selection": None, "expectation_snapshot_refs": [selected["ref"], "missing-duration"],
            "latest_progress_ref": "unknown-undelivered-progress", "return_available": False}]
        original_db = store.db

        class GuardCursor:
            def __init__(self, cursor):
                self.cursor = cursor

            @staticmethod
            def check(row):
                if row is not None:
                    assert all(not isinstance(value, str) or marker not in value for value in row)
                return row

            def __iter__(self):
                return (self.check(row) for row in self.cursor)

            def fetchone(self):
                return self.check(self.cursor.fetchone())

        class GuardDB:
            def execute(self, *args, **kwargs):
                return GuardCursor(original_db.execute(*args, **kwargs))

            def __getattr__(self, name):
                return getattr(original_db, name)

        # Check values crossing SQLite's boundary, not just the final response.
        store.db = journal.db = GuardDB()
        try:
            value = WaitInputs(store, journal, None).capture("parent", pending=pending,
                known_progress_refs=[])
        finally:
            store.db = journal.db = original_db
        assert value["duration_expectations"] == [selected]
        assert value["progress_records"] == []
        assert value["own_completed_action_history"] == [{"episode_id": "parent", "unit_index": 0,
            "decision_index": 3, "controller_input": {"credit": 1.25},
            "controller_step": {"delta": -0.25}}]
        assert marker not in json.dumps(value)


def test_capture_validates_envelopes_and_connection_ownership_without_inventing_missing_inputs(tmp_path):
    with Store(tmp_path / "one") as store, Store(tmp_path / "two") as other:
        journal = Journal(store, "run")
        with pytest.raises(ValueError, match="same_store_connection"):
            WaitInputs(other, journal, None)
        reader = WaitInputs(store, journal, None)
        with pytest.raises(ValueError, match="episode_unavailable"):
            reader.capture("missing", pending=EMPTY_PENDING, known_progress_refs=[])
        save_episode(journal, "parent", {"subject_refs": ["fixture-subject"]})
        unavailable = ExecutionExpectations(tmp_path / "absent-history.sqlite3",
            by_grain={"annotation": [execution_class()]}).capture("annotation")
        assert unavailable["status"] == "unavailable"
        assert reader.capture("parent", pending=EMPTY_PENDING, known_progress_refs=[],
            current_duration_expectations=(unavailable,))["duration_expectations"] == []
        with pytest.raises(ValueError, match="capture_sequence_required"):
            reader.capture("parent", pending=EMPTY_PENDING, known_progress_refs=[],
                current_duration_expectations=unavailable)
        with pytest.raises(ValueError, match="expectation_capture_required"):
            reader.capture("parent", pending=EMPTY_PENDING, known_progress_refs=[],
                current_duration_expectations=({"ref": "not-a-capture", "data": {}},))
        with pytest.raises(ValueError, match="progress_provider_required"):
            reader.capture("parent", pending=EMPTY_PENDING, known_progress_refs=["unknown"])
