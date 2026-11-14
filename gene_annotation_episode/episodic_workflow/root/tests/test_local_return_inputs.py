"""Connected runtime consumption of original C4/F2 local return evidence.

All returns, credits, providers and event deliveries are engineering fixtures.
The actual Store, Workflow, admission, completion ledger, wait store and standard
signed controller are used; no model, scientific job or native program runs.
"""
import asyncio
from copy import deepcopy
import json
from unittest.mock import patch as fixture_patch

import pytest

from method_loop import EpisodeGoal
from method_loop.archive import ArchivedRecord, JsonArchive
from method_loop.identities import UnitRef

from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.local_return_history import LocalReturnHistory
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.runtime import (ExecutionContextController, Record,
    Workflow, WorkflowError, assemble_workflow, run_workflow)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.wait_estimation_inputs import WaitInputs
from test_local_return_history import BINDING, Case, LATER, STAMP, forbidden
import test_local_return_history as return_fixtures
from test_recursive_monitoring import assignment
from test_runtime import FixtureController, ScriptedProvider, obj


PENDING = {"version": "pending_work_v1", "captured_at": STAMP, "items": []}
RESPONSE = {"selection": {"kind": "tool", "tool": "episode.history",
    "arguments": {"view": "records"}}, "report_update": {}}


class RecordingController:
    def __init__(self):
        self.base = YieldController("explicit-fixture-epoch", 0, 0)
        self.epoch = self.base.epoch
        self.inputs = []

    def observe(self, label, value, *, is_root):
        self.inputs.append(deepcopy(value.as_record()))
        return self.base.observe(label, value, is_root=is_root)

    def state(self):
        return self.base.state()


class RuntimeCase:
    """Use the existing immutable-return fixture behind an actual Workflow."""
    def __init__(self, tmp_path, *, wait_inputs_version="wait_inputs_binding_v2"):
        self.case = Case(tmp_path)
        self.store = self.case.store
        self.provider = ScriptedProvider([deepcopy(RESPONSE) for _ in range(20)])
        self.score = 0
        self.projected = []

        def project(store, scope):
            self.projected.append(self.score)
            return self.score

        self.workflow = Workflow(self.store, ToolRegistry(self.store), self.provider,
            tmp_path / "runtime", self.case.journal.run_id,
            lambda path, initial: RecordingController(), project,
            credit_binding=BINDING, episode_record_receipts=True,
            initial_known_record_refs=[], wait_inputs_version=wait_inputs_version)
        # setup_case supplies the immutable source bytes and target. Replace its
        # unused parent fixture with the actual runtime's original root request
        # before selecting or publishing any of the children used here.
        self.store.db.execute("DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.case.journal.run_id, self.case.parent))
        self.root = self.workflow.build("annotation", "root", "Fixture received-information question",
            self.case.base["child"]["scope"])
        self.source = self.root.source
        assert self.source.episode_id == self.case.parent
        self.case.base["parent"]["goal_id"] = self.root.goal.goal_id
        self.case.base["child"]["request"]["goal"] = EpisodeGoal.child(self.root.goal,
            objective="Selected bounded fixture work", result_contract={}).as_record()
        # The actual immutable returns live in this backend. No worker starts.
        self.workflow.execution_backend = self.case.backend
        self.workflow.commissions = self.case.coordinator
        self.workflow.progress_provider = self.case.progress
        self.workflow.wait_inputs = WaitInputs(self.store, self.workflow.journal, self.case.progress)
        self.workflow.local_return_history = LocalReturnHistory(
            self.store, self.workflow.journal, self.case.backend)
        self.controller = RecordingController()
        self.wrapper = ExecutionContextController(self.controller, self.workflow.journal,
            self.source.episode_id)

    def call(self, index):
        self.source.calls = index
        return asyncio.run(self.source.call({"visible_record_refs": [],
            "current_report_update": {}}, obj({})))

    def select(self, index, **kwargs):
        self.call(index)
        # The collector-only fixture deliberately uses a permissive resolver
        # for its unrelated "other" field. Give that fixture interpretation
        # actual constrained meanings before publishing through runtime C4.
        schema = deepcopy(return_fixtures.SCHEMA)
        schema["properties"]["other"] = {"type": "string", "enum": [
            "unknown", "progress_undeclared_value"]}
        with fixture_patch.object(return_fixtures, "SCHEMA", schema):
            return self.case.child(index, defer_admission=True, **kwargs)

    def admit(self, item, monkeypatch, *, score):
        # Fixture delivery order selects from the actual original return page;
        # neither its return records nor its timestamps are reconstructed.
        backend = self.case.backend
        original = backend.return_page
        handle = item[0]["handle"]

        def page(parent, cursor, limit):
            value = original(parent, 0, 128)
            return {**value, "items": ([] if cursor else [
                row for row in value["items"] if row["handle"] == handle])}

        self.score = score
        with monkeypatch.context() as patch:
            patch.setattr(backend, "return_page", page)
            return self.workflow.next_return(self.source)

    def observe(self, slot):
        step = self.wrapper.observe(slot["label"], Record(slot["controller_input"]), is_root=True)
        self.workflow.completions.confirm_observed(self.source.episode_id, slot["sequence"], {
            "label": slot["label"], "credit": slot["controller_input"], "step": step.as_record(),
            "unit_ref": UnitRef(self.source.episode_id, slot["sequence"]).as_record(),
            "decision_index": slot["original_decision_index"]})
        return step

    def support(self):
        return self.workflow.waiting_support(self.source, {"pending_work": PENDING})


def readonly_runtime(case, patch):
    """The context has already acquired pending_work; collection only reads."""
    for name in ("status", "start", "commission", "acknowledge", "publish_return",
                 "return_page", "load_commission", "record_progress", "_claim"):
        patch.setattr(case.case.backend, name, forbidden)
    for name in ("save", "measure", "elapsed_view", "commission_returned"):
        patch.setattr(case.workflow.journal, name, forbidden)
    for name in ("transaction", "artifact", "put", "get", "get_artifact"):
        patch.setattr(case.store, name, forbidden)
    patch.setattr(case.workflow, "source_credit_view", forbidden)
    patch.setattr(case.workflow, "project_credit", forbidden)
    patch.setattr(ArchivedRecord, "load", forbidden)
    patch.setattr(ArchivedRecord, "iter_json", forbidden)
    patch.setattr(JsonArchive, "store", forbidden)
    patch.setattr(case.workflow, "archive_reference", forbidden)
    patch.setattr(case.controller, "observe", forbidden)
    case.store.db.execute("PRAGMA query_only=ON")


def test_actual_workflow_admission_observation_next_decision_preserves_completion_order(tmp_path, monkeypatch):
    fixture = RuntimeCase(tmp_path)
    try:
        first = fixture.select(1)
        second = fixture.select(4)
        third = fixture.select(9, progress=True)
        slots = []
        for item, score in ((third, 5.25), (first, 2.0), (second, 2.125)):
            slot = fixture.admit(item, monkeypatch, score=score)
            slots.append(slot)
            # Admission has committed, but it cannot claim an observation that
            # the owning controller has not received yet.
            sample = next(row for row in fixture.support()["local_return_history"]["samples"]
                if row["child_handle"] == item[0]["handle"])
            assert sample["observation_state"] == "unobserved"
            assert sample["unit_ref"] is sample["raw_controller_delta"] is None
            fixture.observe(slot)
        _, index, context, _ = fixture.call(10)
        support = context["waiting_support"]
        assert index == 10 and support["version"] == "wait_inputs_v2"
        samples = support["local_return_history"]["samples"]
        assert all(row["admission_state"] == "admitted" for row in samples)
        assert [row["original_decision_index"] for row in samples] == [9, 1, 4]
        assert [row["completion_sequence"] for row in samples] == [0, 1, 2]
        assert [row["raw_controller_delta"] for row in samples] == [5.25, -3.25, 0.125]
        assert [row["unit_ref"] for row in samples] == [
            UnitRef(fixture.source.episode_id, i).as_record() for i in range(3)]
        assert [row["unit_ref"] for row in support["own_completed_action_history"]] == [
            row["unit_ref"] for row in samples]
        assert all(row["selected_at"] == STAMP and row["returned_at"] == LATER for row in samples)
        assert all(row["selection_to_return"] == {"seconds": 12.125,
            "measure": "utc_timestamp_difference", "unavailable_reason": None} for row in samples)
        assert samples[0]["received_progress_refs"]
        assert support["local_return_history"]["credit_binding"] == BINDING
        assert support["local_return_history"]["credit_kind"] == "scientific"
        assert len(fixture.controller.inputs) == 3
        assert fixture.store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?",
            (fixture.source.episode_id,)).fetchone()[0] == 3
        before = fixture.store.db.total_changes
        with monkeypatch.context() as patch:
            readonly_runtime(fixture, patch)
            captured = fixture.support()
            assert captured == support
            assert fixture.support() == captured
            assert fixture.store.db.total_changes == before
    finally:
        fixture.store.close()


def test_completion_forwards_saved_selection_history_then_replays_exactly(tmp_path, monkeypatch):
    fixture = RuntimeCase(tmp_path)
    try:
        first = fixture.select(1)
        fixture.observe(fixture.admit(first, monkeypatch, score=5.25))
        second = fixture.select(2)
        original_call = fixture.workflow.journal.row("runtime_model_calls", fixture.source.episode_id, 2)
        saved_request = original_call["request"]
        selection_history = json.loads(saved_request)["context"]["waiting_support"]["local_return_history"]
        assert len(selection_history["samples"]) == 1
        slot = fixture.admit(second, monkeypatch, score=2.0)
        # Immediately before observing return 2, current history correctly has
        # one new unobserved admission. The selection snapshot cannot contain it.
        current = fixture.support()["local_return_history"]
        assert len(current["samples"]) == 2 and current["samples"][1]["unit_ref"] is None
        fixture.observe(slot)
        supplied = fixture.controller.inputs[-1]["estimation_context"]
        assert supplied["version"] == "completed_action_estimation_context_v4"
        assert supplied["local_return_history_at_selection"] == selection_history
        assert "current_completion" not in supplied
        estimate_row = fixture.store.db.execute("SELECT data FROM runtime_estimation_contexts "
            "WHERE episode_id=? AND decision_index=2", (fixture.source.episode_id,)).fetchone()[0]
        assert json.loads(estimate_row) == supplied
        before = fixture.store.db.total_changes
        with monkeypatch.context() as patch:
            patch.setattr(fixture.workflow, "waiting_support", forbidden)
            patch.setattr(fixture.workflow.local_return_history, "capture", forbidden)
            patch.setattr(fixture.workflow, "pending_work", forbidden)
            patch.setattr(fixture.provider, "complete", forbidden)
            replay_controller = RecordingController()
            replay = ExecutionContextController(replay_controller, fixture.workflow.journal,
                fixture.source.episode_id)
            replay.observe(slot["label"], Record(slot["controller_input"]), is_root=True)
            fixture.source.calls = 2
            _, _, replay_context, _ = asyncio.run(fixture.source.call({"must": "be ignored"}, obj({})))
        assert replay_controller.inputs[0]["estimation_context"] == supplied
        assert replay_context == json.loads(saved_request)["context"]
        assert fixture.workflow.journal.row("runtime_model_calls", fixture.source.episode_id, 2)["request"] == saved_request
        assert fixture.store.db.execute("SELECT data FROM runtime_estimation_contexts "
            "WHERE episode_id=? AND decision_index=2", (fixture.source.episode_id,)).fetchone()[0] == estimate_row
        assert fixture.store.db.total_changes == before
    finally:
        fixture.store.close()


def test_runtime_wait_and_child_return_remain_separate_observations(tmp_path, monkeypatch):
    fixture = RuntimeCase(tmp_path)
    try:
        child = fixture.select(1)
        fixture.observe(fixture.admit(child, monkeypatch, score=5.25))
        fixture.call(2)
        condition = {"version": "event_condition_v1", "events": [{"handle": child[0]["handle"],
            "event": "returned", "after_cursor": 0}], "reconsider_at": None}

        async def wake(selected):
            return {"version": "event_wake_v1", "reason": "returned", "observed_at": STAMP,
                "events": [{"cursor": 17, "handle": child[0]["handle"], "event": "returned",
                    "record_ref": child[1]["return_id"]}], "reconsider_at": None}

        monkeypatch.setattr(fixture.case.backend, "wait_events", wake)
        value = asyncio.run(fixture.source.execute({"kind": "wait", "condition": condition}, 2))
        assert value.as_record()["credit"] == 5.25
        slot = fixture.workflow.completions.stage(fixture.source.episode_id, 2, label="wait:2",
            kind="own_action", controller_input=value, child_return=None)
        step = fixture.observe(slot)
        assert step.marginal_credit == 0
        _, _, context, _ = fixture.call(3)
        support = context["waiting_support"]
        assert [row["decision_index"] for row in support["own_completed_action_history"]] == [1, 2]
        assert len(support["local_return_history"]["samples"]) == 1
        sample, = support["local_return_history"]["samples"]
        assert sample["raw_controller_delta"] == 5.25
        wait, = sample["linked_waits"]
        assert wait["wait_id"].startswith("wait_") and wait["duration_measure"] == "measured_wait_intervals"
        assert "raw_controller_delta" not in wait and "credit" not in wait
        estimate = fixture.workflow.wait_estimate(fixture.source, condition, context)
        assert estimate["local_history_refs"] == [
            row["unit_ref"]["unit_id"] for row in support["own_completed_action_history"]]
        assert estimate["scientific_gain"] is estimate["monitoring_gain"] is None
        assert len(fixture.controller.inputs) == 2
    finally:
        fixture.store.close()


def test_runtime_support_retains_failed_and_unobserved_samples_read_only(tmp_path, monkeypatch):
    fixture = RuntimeCase(tmp_path)
    try:
        waiting = fixture.select(2)
        slot = fixture.admit(waiting, monkeypatch, score=1)
        failed = fixture.select(0, state="execution_failed")
        assert fixture.admit(failed, monkeypatch, score=1) is None
        malformed = fixture.select(5, state="delivery_failed")
        fixture.observe(fixture.admit(malformed, monkeypatch, score=0))
        with monkeypatch.context() as patch:
            readonly_runtime(fixture, patch)
            support = fixture.support()
        samples = support["local_return_history"]["samples"]
        assert [row["original_decision_index"] for row in samples] == [5, 0, 2]
        assert samples[0]["admission_state"] == "delivery_failed"
        assert samples[0]["raw_controller_delta"] == 0
        assert samples[1]["admission_state"] == "execution_failed"
        assert samples[1]["controller_input"] is samples[1]["unit_ref"] is None
        assert samples[2]["completion_sequence"] == slot["sequence"]
        assert samples[2]["observation_state"] == "unobserved"
        assert samples[2]["raw_controller_delta"] is samples[2]["unit_ref"] is None
        assert [row["decision_index"] for row in support["own_completed_action_history"]] == [5]
    finally:
        fixture.store.close()


def test_missing_role_definition_omits_history_without_projection_or_gate(tmp_path, monkeypatch):
    fixture = RuntimeCase(tmp_path)
    try:
        target = fixture.select(1)
        workflow = Workflow(fixture.store, ToolRegistry(fixture.store), fixture.provider,
            tmp_path / "monitor-runtime", fixture.case.journal.run_id,
            lambda path, initial: RecordingController(), lambda *_: 0,
            episode_binding_factories=(MonitorEpisodes,))
        workflow.progress_provider = fixture.case.progress
        # A legacy direct factory can supply a projector with no recorded
        # definition; the absence is exposed, never silently filled with units.
        workflow.role_credit_projectors["monitor"] = lambda context, selection: {"credit": 0}
        monitor = workflow.build("monitor", "missing-definition", "Fixture progress question",
            fixture.source.scope, episode_assignment=assignment(target[0]["handle"]))
        assert workflow.source_controller_credit(monitor.source) is None
        before = fixture.store.db.total_changes
        with monkeypatch.context() as patch:
            patch.setattr(workflow.local_return_history, "capture", forbidden)
            patch.setattr(workflow, "source_credit_view", forbidden)
            support = workflow.waiting_support(monitor.source, {"pending_work": PENDING})
        assert support["version"] == "wait_inputs_v2"
        assert support["local_return_history_unavailable_reason"] == "controller_credit_binding_unavailable"
        assert "local_return_history" not in support
        assert fixture.store.db.total_changes == before
    finally:
        fixture.store.close()


def settings():
    return {"bindings": {"credit": "explicit-fixture-projector", "controller": "explicit-fixture-controller"},
        "binding_versions": {"credit": {"version": "fixture-v1"}, "controller": {"version": "fixture-v1"}},
        "controller": None, "restoration": {"preview_size": 2}}


@pytest.mark.parametrize("marker,expected", [(None, "wait_inputs_v1"),
    ({"version": "wait_inputs_binding_v1"}, "wait_inputs_v1"),
    ({"version": "wait_inputs_binding_v2"}, "wait_inputs_v2")])
def test_assembled_binding_preserves_absent_legacy_marker_and_explicit_versions(tmp_path, marker, expected):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        saved = settings()
        if marker is not None:
            saved["wait_inputs"] = marker
        provider = ScriptedProvider([])
        workflow = assemble_workflow(store, ToolRegistry(store), provider, tmp_path / "runtime", "legacy", saved,
            controller_factory=lambda path, initial: RecordingController(), project_credit=lambda *_: 0)
        root = workflow.build("annotation", "root", "Fixture binding recovery", store.validate_scope())
        support = workflow.waiting_support(root.source, {"pending_work": PENDING})
        assert support["version"] == expected
        assert ("local_return_history" in support) == (expected == "wait_inputs_v2")
        assert provider.contexts == []


@pytest.mark.parametrize("marker", [{}, None, {"version": "wait_inputs_binding_v99"},
    {"version": "wait_inputs_binding_v2", "inferred": True}])
def test_unknown_saved_binding_fails_before_transport_or_factory(tmp_path, monkeypatch, marker):
    with Store(tmp_path / "store") as store:
        saved = {**settings(), "wait_inputs": marker}
        provider = ScriptedProvider([])
        monkeypatch.setattr(provider, "complete", forbidden)
        with pytest.raises(WorkflowError, match="unsupported_wait_inputs_binding"):
            assemble_workflow(store, object(), provider, tmp_path / "runtime", "saved", saved,
                controller_factory=forbidden, project_credit=forbidden)
        assert provider.contexts == []


def test_new_run_pins_v2_and_supplies_versioned_completion_without_detached_execution(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        provider = ScriptedProvider([RESPONSE])
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "runtime", controller_factory=lambda path, initial: FixtureController(
                str(path), initial, 1), project_credit=lambda *_: 0))
        assert result["completed_actions"] == 1
        saved = json.loads(store.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])
        assert saved["wait_inputs"] == {"version": "wait_inputs_binding_v2"}
        context = provider.contexts[0]
        assert context["waiting_support"]["version"] == "wait_inputs_v2"
        estimation = json.loads(store.db.execute("SELECT data FROM runtime_estimation_contexts").fetchone()[0])
        assert estimation["version"] == "completed_action_estimation_context_v5"
        assert estimation["local_return_history_at_selection"] == context["waiting_support"]["local_return_history"]
        assert saved['completed_action_inputs'] == {'version': 'completed_action_inputs_binding_v1'}
        observed = json.loads(store.db.execute('SELECT observation FROM runtime_observations').fetchone()[0])
        assert estimation['current_completion_evidence']['unit_ref'] == observed['unit_ref']
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
