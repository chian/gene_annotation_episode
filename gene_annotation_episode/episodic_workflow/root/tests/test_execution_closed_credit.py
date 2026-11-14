"""Engineering closed-credit frames, real Runtime/family/Store metadata ports.

The original live projection and completed unit are controlled inputs. The
closed archive is written by Workflow's actual on_close callback. No provider,
HTTP request, native work, scientific computation or whole-loop claim is made.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

from method_loop.episode import EpisodeRecord, UnitRecord
from method_loop.identities import EpisodeRef, UnitRef
import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, _CLOSED_CREDIT
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import YieldController, YieldParameters
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


SCHEMA = {"type": "object", "properties": {"completed": {
    "type": "boolean", "x-source": "execution_completed"}},
    "required": ["completed"], "additionalProperties": False}
RAW_VIEW = {"credit": 3, "operational_credit": 3, "new_handoff_count": 1,
    "new_acquired_record_count": 0, "operational_credit_binding": {
        "version": "engineering_original_projection_v1", "handoff_unit": 3,
        "acquired_record_unit": 2, "scientific_credit": False, "monitoring_credit": False}}


def forbidden(*args, **kwargs):
    pytest.fail("Closed operational credit performed another projection or read payload bytes")


class ClosedCreditFrame:
    def __init__(self, store, directory, monkeypatch):
        self.store, self.calls = store, []
        monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", forbidden)
        request = {"version": "enrichr_request_v1", "protocol_profile": "standard_enrichr_v1",
            "library": "Engineering metadata only", "genes": ["ENGINEERING"],
            "identifier_policy": "literal_no_mapping", "species_context": None,
            "description": "no service request", "background": {"policy": "service_native", "genes": None},
            "native_statistic_profile": "uninterpreted"}
        resources = {"enrichr": {"kind": "api", "service": "enrichr",
            "protocol_profile": "standard_enrichr_v1", "base_url": "https://enrichr.invalid/Enrichr",
            "timeout": 2, "response_byte_limit": 4096}}
        factory = ExecutionServiceFactory(resources, {}, 3, 2, .5)
        self.workflow = Workflow(store, ToolRegistry(store), object(), directory, "closed-credit-engineering",
            controller_factory=lambda path, initial: YieldController(str(path), initial, 0, YieldParameters(100, 50)),
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs="actual_tool_registry_v1",
            annotation_child_roles=("launch",), episode_record_receipts=True, initial_known_record_refs=[])
        self.owner = self.workflow.episode_bindings.for_role("launch")
        self.live_view = {**deepcopy(RAW_VIEW), "credit": 0, "operational_credit": 0,
            "new_handoff_count": 0}
        def live(context, selection):
            self.calls.append((context.episode_id, deepcopy(selection)))
            return deepcopy(self.live_view)
        monkeypatch.setattr(self.owner, "_live_project_credit", live)
        monkeypatch.setattr(self.owner, "_live_facts", lambda *_: {"execution_completed": False})
        scope = {"subject_refs": store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"]}
        self.parent = self.workflow.build("annotation", "root", "Engineering credit carrier", scope)
        assignment = {"version": "execution_launch_assignment_v1", "requests": {"enrichr": {
            "version": "api_service_assignment_v1", "resource_id": "enrichr", "service": "enrichr",
            "request": request, "endpoint": "usable_handoff", "constraints": {}}},
            "immutable_input_versions": [], "constraints": {}}
        contract = TypedReportContract("Return the recorded incomplete status", SCHEMA, lambda *_: True)
        self.child = self.workflow.build("launch", "child_0", "Engineering closed credit", scope,
            parent=self.parent.request.goal, parent_path=self.parent.source.path,
            contract=contract, episode_assignment=assignment)
        self.context = self.workflow.binding_context(self.child.source)
        self.workflow.journal.save("runtime_actions", {"episode_id": self.parent.source.episode_id,
            "decision_index": 0, "action": canonical({"kind": "episode_child", "role": "launch",
                "scope": scope, "assignment": assignment, "purpose": contract.decision,
                "goal": "Engineering closed credit", "initial_report_json": "{}",
                "schema_json": canonical(SCHEMA)}), "result": None, "credit": None})
        self.live_view, self.calls = deepcopy(RAW_VIEW), []

    def selection(self):
        return {**self.workflow.record_selection(self.context.episode_id),
            **self.workflow.progress_selection(self.child.source)}

    def close(self, *, observed_credit=None):
        """Supply an explicit completed engineering unit, not a native result."""
        unit_ref = UnitRef(self.context.episode_id, 0)
        value = {"credit": RAW_VIEW["credit"] if observed_credit is None else observed_credit}
        unit = UnitRecord("engineering:0", value, None, "engineering_epoch", unit_ref)
        self.record = EpisodeRecord("launch", "child_0", 1, "engineering_fixture", (unit,), None,
            self.child.request, path=self.child.source.path, end_reason="controlled metadata frame",
            episode_ref=EpisodeRef(self.workflow.run_id, self.child.source.path))
        outcome = {"status": "completed", "record_refs": [], "changed_record_refs": []}
        self.workflow.journal.save("runtime_actions", {"episode_id": self.context.episode_id, "decision_index": 0,
            "action": canonical({"kind": "wait", "condition": {"version": "event_condition_v1",
                "events": [], "reconsider_at": "2026-10-30T00:00:00+00:00"}}),
            "result": canonical(outcome), "credit": value["credit"]})
        self.workflow.journal.save("runtime_observations", {"episode_id": self.context.episode_id, "unit_index": 0,
            "observation": canonical({"label": unit.unit_label, "unit_ref": unit_ref.as_record(),
                "credit": value, "step": None, "decision_index": 0})})
        self.child.source.last_outcome, self.child.source.last_outcome_index = outcome, 0
        self.child.on_close(self.record)

    def freeze(self):
        self.close()
        facts = self.workflow.facts(self.child.source, completion_record=self.record)
        form = form_with_facts({}, SCHEMA, facts)
        self.workflow.journal.save("runtime_forms", {"episode_id": self.context.episode_id,
            "facts": canonical({**facts, "interpretations": {}}), "form": canonical(form)})
        return facts, form

    def saved(self):
        row = self.workflow.journal.row("runtime_forms", self.context.episode_id)
        return json.loads(row["facts"]), json.loads(row["form"])

    def save(self, facts, form):
        self.store.db.execute("UPDATE runtime_forms SET facts=?,form=? WHERE run_id=? AND episode_id=?",
            (canonical(facts), canonical(form), self.workflow.run_id, self.context.episode_id))


@pytest.fixture
def frame(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        yield ClosedCreditFrame(store, tmp_path / "run", monkeypatch)


@pytest.mark.parametrize("monitoring", [False, True])
def test_capture_uses_one_original_projection_and_closed_view_does_not_double_monitoring(frame, monkeypatch, monitoring):
    if monitoring:
        class Timing:
            def __call__(self, *args, **kwargs):
                return {"monitoring_information_credit": 5,
                    "monitoring_information_binding": {"version": "engineering_timing_v1"}}
            def read_details(self, *args, **kwargs):
                return {"native_execution_measurements": []}
        frame.workflow.native_timing_information = Timing()
    facts, form = frame.freeze()
    assert form == {"completed": False}
    assert len(frame.calls) == 1
    snapshot = facts[_CLOSED_CREDIT]
    assert snapshot["view"] == RAW_VIEW
    assert "monitoring_information_credit" not in snapshot["view"]
    before = canonical(frame.saved())
    monkeypatch.setattr(frame.owner, "_live_project_credit", forbidden)
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    assert frame.owner.project_credit(frame.context, frame.selection()) == RAW_VIEW
    assert frame.owner.credit_view(frame.context, frame.selection()) == RAW_VIEW
    result = frame.workflow.source_credit_view(frame.child.source)
    assert result["credit"] == 3 and result["operational_credit"] == 3
    assert result.get("monitoring_information_credit") == (5 if monitoring else None)
    assert canonical(frame.saved()) == before
    assert frame.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1


def test_later_receipt_does_not_change_the_original_closed_credit_or_snapshot(frame, monkeypatch):
    frame.freeze()
    before = canonical(frame.saved())
    later = frame.store.artifact(b"later independently supplied engineering File")
    frame.workflow.receipts.receive(frame.context.episode_id, [later], kind="decision_input", source_index=1)
    monkeypatch.setattr(frame.owner, "_live_project_credit", forbidden)
    assert later in frame.selection()["known_record_refs"]
    assert frame.owner.credit_view(frame.context, frame.selection()) == RAW_VIEW
    assert canonical(frame.saved()) == before


@pytest.mark.parametrize("rejected", [False, True])
def test_incomplete_closed_view_needs_no_successful_parent_return(frame, monkeypatch, rejected):
    facts, form = frame.freeze()
    assert facts["execution_completed"] is False
    if rejected:
        frame.workflow.journal.save("runtime_report_attempts", {"parent_episode_id": frame.parent.source.episode_id,
            "decision_index": 0, "delivery_ref": "delivery_engineering_rejection",
            "child_episode_id": frame.context.episode_id, "contract": canonical(frame.child.request.report_contract.as_record()),
            "form": None, "failure": canonical({"category": "engineering_rejected_return"})})
    monkeypatch.setattr(frame.owner, "_live_project_credit", forbidden)
    assert frame.owner.credit_view(frame.context, frame.selection()) == RAW_VIEW


@pytest.mark.parametrize("change", ["version", "context", "binding", "receipt", "view_count", "view_credit", "view_boolean", "view_float",
    "archive", "completion", "active", "observation", "no_form", "unreceived_selection"])
def test_closed_credit_rejects_substituted_original_metadata_without_projection(frame, monkeypatch, change):
    frame.freeze()
    facts, form = frame.saved()
    value = facts[_CLOSED_CREDIT]
    context, selection = frame.context, frame.selection()
    if change == "version":
        value["version"] = "unrecognized"
    elif change == "context":
        context = replace(context, assignment={**dict(context.assignment), "constraints": {"forged": True}})
    elif change == "binding":
        frame.owner.handoff_unit = 4
    elif change == "receipt":
        frame.store.db.execute("UPDATE runtime_record_receipts SET receipt_kind='decision_input' "
            "WHERE run_id=? AND episode_id=?", (frame.workflow.run_id, frame.parent.source.episode_id))
    elif change == "view_count":
        value["view"]["new_handoff_count"] = 99
    elif change in {"view_credit", "view_boolean", "view_float"}:
        changed = {"view_credit": 4, "view_boolean": True, "view_float": 3.0}[change]
        value["view"]["credit"] = changed
        value["view_sha256"] = digest(value["view"])
    elif change in {"archive", "completion", "active"}:
        field, replacement = {"archive": ("archive", canonical({"file": "0" * 64 + ".json",
            "sha256": "0" * 64, "index_sha256": "0" * 64})), "completion": ("completion",
            canonical({"actions": 1, "ended_by": "changed"})), "active": ("state", "active")}[change]
        frame.store.db.execute("UPDATE runtime_episodes SET " + field + "=? WHERE run_id=? AND episode_id=?",
            (replacement, frame.workflow.run_id, frame.context.episode_id))
    elif change == "observation":
        frame.store.db.execute("UPDATE runtime_observations SET observation=? WHERE run_id=? AND episode_id=?",
            (canonical({"credit": {"credit": 4}}), frame.workflow.run_id, frame.context.episode_id))
    elif change == "no_form":
        frame.store.db.execute("UPDATE runtime_forms SET form=NULL WHERE run_id=? AND episode_id=?",
            (frame.workflow.run_id, frame.context.episode_id))
    else:
        selection["known_record_refs"].append("artifact_" + "0" * 64)
    if change != "no_form":
        frame.save(facts, form)
    monkeypatch.setattr(frame.owner, "_live_project_credit", forbidden)
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    with pytest.raises(ValueError, match="execution_closed_credit_"):
        frame.owner.credit_view(context, selection)


def test_old_form_without_snapshot_uses_the_existing_path_without_backfill(frame, monkeypatch):
    frame.freeze()
    facts, form = frame.saved()
    facts.pop(_CLOSED_CREDIT)
    frame.save(facts, form)
    before = canonical(frame.saved())
    legacy = {"credit": 17, "operational_credit": 17, "legacy_fixture": True}
    monkeypatch.setattr(frame.owner, "_live_project_credit", lambda *_: deepcopy(legacy))
    assert frame.owner.credit_view(frame.context, frame.selection()) == legacy
    assert _CLOSED_CREDIT not in frame.owner.facts(frame.context, {"completion": {
        "ended_by": frame.record.ended_by, "units_consumed": 1}, "operational_credit_snapshot": {
            "view": legacy, "selection": frame.selection()}})
    assert canonical(frame.saved()) == before


def test_active_nonclosure_facts_do_not_create_a_snapshot(frame):
    assert _CLOSED_CREDIT not in frame.workflow.facts(frame.child.source)
    assert frame.workflow.journal.row("runtime_forms", frame.context.episode_id) is None


def test_final_shared_credit_refresh_is_preserved_without_replacing_the_original_observation(frame, monkeypatch):
    frame.close(observed_credit=2)
    facts = frame.workflow.facts(frame.child.source, completion_record=frame.record)
    form = form_with_facts({}, SCHEMA, facts)
    frame.workflow.journal.save("runtime_forms", {"episode_id": frame.context.episode_id,
        "facts": canonical(facts), "form": canonical(form)})
    before = [tuple(row) for row in frame.store.db.execute("SELECT * FROM runtime_observations")]
    assert json.loads(before[0][-1])["credit"]["credit"] == 2
    assert facts["credit"] == facts[_CLOSED_CREDIT]["view"]["credit"] == 3
    monkeypatch.setattr(frame.owner, "_live_project_credit", forbidden)
    assert frame.owner.credit_view(frame.context, frame.selection()) == RAW_VIEW
    assert [tuple(row) for row in frame.store.db.execute("SELECT * FROM runtime_observations")] == before


def test_fresh_store_without_runtime_forms_keeps_the_previous_dispatch(tmp_path):
    with Store(tmp_path / "state") as store:
        owner = object.__new__(ExecutionEpisodes)
        owner.store, owner.run_id = store, "fresh-store-component"
        owner._live_project_credit = lambda *_: {"credit": 0}
        assert owner.credit_view(SimpleNamespace(episode_id="not-a-runtime-frame"), {}) == {"credit": 0}


def _completion_proof(frame):
    return {"version": "practical_completion_v1", "run_id": frame.workflow.run_id,
        "episode_id": frame.context.episode_id, "assignment_sha256": digest(frame.context.assignment),
        "endpoint": "usable_handoff", "operation_key": f"{frame.workflow.run_id}:{frame.context.episode_id}:0",
        "receipt_sha256": "a" * 64, "validation_keys": ["engineering_original_endpoint"]}


def _original_completion_observation(frame, *, mode="verified", bad_original=None):
    """Record the real estimator's verdict with an engineering native verifier.

    The old full verifier's final endpoint reader is the only substituted
    authority. This is not a native endpoint or scientific completion claim.
    """
    from unittest.mock import patch
    from gene_annotation_episode.completion_evidence import validate_completion_evidence
    from gene_annotation_episode.numerical import NumericBand
    from gene_annotation_episode.runtime import Record
    proof, unit = _completion_proof(frame), UnitRef(frame.context.episode_id, 0)
    packet = validate_completion_evidence({"version": "completed_action_evidence_v1",
        "run_id": frame.workflow.run_id, "episode_id": frame.context.episode_id, "unit_ref": unit.as_record(),
        "original_decision_index": 0, "action_kind": "tool", "received_record_refs": [],
        "received_progress_refs": [], "progress_records": [], "child_return": None, "unavailable_reasons": []})
    context = {"current_completion_evidence": packet}
    body = {"credit": 3, "estimation_action_index": 0}
    if mode != "absent_input":
        body["practical_completion"] = deepcopy(proof)
        context["practical_completion"] = {**proof, "action_index": 0, "unit_ref": unit.as_record()}
    controller = YieldController("engineering_epoch", 0, 0, YieldParameters(100, 50),
        estimate_with_context=frame.owner.practical_estimator(frame.context))
    with patch.object(frame.owner, "_proof_for_action", return_value=None if mode == "unverified" else proof):
        step = controller.observe("engineering:0", Record({"credit": 3, "estimation_context": context}), is_root=False)
    step_data = None if mode == "marker_only" else step.as_record()
    observed_unit, decision_index = unit.as_record(), 0
    if bad_original == "unit":
        observed_unit = UnitRef(frame.context.episode_id, 1).as_record()
    elif bad_original == "action":
        decision_index = 1
    elif bad_original == "provenance":
        step_data["estimate"]["provenance"]["version"] = "not_the_practical_estimator"
    elif bad_original == "scope":
        step_data["estimate"]["diagnostics"]["fitting_scope"] = "full_history"
    elif bad_original == "band":
        step_data["estimate"]["expected_next_gain"] = NumericBand.exact(1).as_record()
    elif bad_original == "diagnostic_proof":
        step_data["estimate"]["diagnostics"]["completion_proof"]["receipt_sha256"] = "b" * 64
    observation = {"label": "engineering:0", "unit_ref": observed_unit, "credit": body,
        "step": step_data, "decision_index": decision_index}
    unit_record = UnitRecord("engineering:0", body, None if step_data is None else Record(step_data),
        "engineering_epoch", unit)
    record = EpisodeRecord("launch", "child_0", 1, "engineering_fixture", (unit_record,), controller.state(),
        frame.child.request, path=frame.child.source.path, end_reason="controlled completion-verdict frame",
        episode_ref=EpisodeRef(frame.workflow.run_id, frame.child.source.path))
    outcome = {"status": "completed", "record_refs": [], "changed_record_refs": []}
    frame.workflow.journal.save("runtime_actions", {"episode_id": frame.context.episode_id, "decision_index": 0,
        "action": canonical({"kind": "tool", "tool": "engineering.no_native_operation", "arguments": {}}),
        "result": canonical(outcome), "credit": 3})
    frame.workflow.journal.save("runtime_observations", {"episode_id": frame.context.episode_id,
        "unit_index": 0, "observation": canonical(observation)})
    frame.workflow.journal.save("runtime_estimation_contexts", {"episode_id": frame.context.episode_id,
        "decision_index": 0, "data": canonical(context)})
    frame.child.source.last_outcome, frame.child.source.last_outcome_index = outcome, 0
    frame.child.on_close(record)
    facts = frame.workflow.facts(frame.child.source, completion_record=record)
    frame.workflow.journal.save("runtime_forms", {"episode_id": frame.context.episode_id,
        "facts": canonical(facts), "form": canonical(form_with_facts({}, SCHEMA, facts))})
    return proof, body, unit, step_data


def test_original_verified_completion_replays_existing_controller_without_native_revalidation(frame, monkeypatch):
    from gene_annotation_episode.runtime import ExecutionContextController, Record
    proof, body, unit, original_step = _original_completion_observation(frame)
    before = {table: [tuple(row) for row in frame.store.db.execute("SELECT * FROM " + table)] for table in
        ("runtime_observations", "runtime_estimation_contexts", "runtime_forms", "runtime_actions")}
    monkeypatch.setattr(frame.owner, "_proof_for_action", forbidden)
    monkeypatch.setattr(frame.owner.api_execution, "verify_completion", forbidden)
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    assert frame.owner.verify_completion(frame.context, proof) is True
    controller = YieldController("engineering_epoch", 0, 0, YieldParameters(100, 50),
        estimate_with_context=frame.owner.practical_estimator(frame.context))
    wrapped = ExecutionContextController(controller, frame.workflow.journal, frame.context.episode_id)
    replayed = wrapped.observe_unit("engineering:0", Record(body), unit_ref=unit, is_root=False)
    assert replayed.as_record() == original_step
    assert {table: [tuple(row) for row in frame.store.db.execute("SELECT * FROM " + table)] for table in before} == before


@pytest.mark.parametrize("mode", ["absent_input", "unverified", "marker_only"])
def test_closed_snapshot_alone_does_not_establish_an_original_verified_endpoint(frame, monkeypatch, mode):
    proof, _, _, _ = _original_completion_observation(frame, mode=mode)
    monkeypatch.setattr(frame.owner, "_proof_for_action", forbidden)
    monkeypatch.setattr(frame.owner.api_execution, "verify_completion", forbidden)
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    assert frame.owner.verify_completion(frame.context, proof) is False


@pytest.mark.parametrize("change", ["receipt", "assignment", "keys", "operation", "run", "episode"])
def test_recorded_completion_requires_exact_submitted_original_proof(frame, monkeypatch, change):
    proof, _, _, _ = _original_completion_observation(frame)
    key, value = {"receipt": ("receipt_sha256", "b" * 64), "assignment": ("assignment_sha256", "b" * 64),
        "keys": ("validation_keys", ["different_qualification"]), "operation": ("operation_key", proof["operation_key"] + "1"),
        "run": ("run_id", "different_run"), "episode": ("episode_id", "different_episode")}[change]
    proof[key] = value
    monkeypatch.setattr(frame.owner, "_proof_for_action", forbidden)
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    assert frame.owner.verify_completion(frame.context, proof) is False


@pytest.mark.parametrize("change", ["unit", "action", "provenance", "scope", "band", "diagnostic_proof"])
def test_recorded_completion_requires_original_observed_verdict_identity_and_zero_forecast(frame, monkeypatch, change):
    proof, _, _, _ = _original_completion_observation(frame, bad_original=change)
    monkeypatch.setattr(frame.owner, "_proof_for_action", forbidden)
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    assert frame.owner.verify_completion(frame.context, proof) is False


@pytest.mark.parametrize("change", ["snapshot_binding", "history"])
def test_recorded_completion_cannot_bypass_closed_snapshot_authentication(frame, monkeypatch, change):
    proof, _, _, _ = _original_completion_observation(frame)
    if change == "snapshot_binding":
        facts, form = frame.saved()
        facts[_CLOSED_CREDIT]["binding_sha256"] = "0" * 64
        frame.save(facts, form)
    else:
        row = frame.store.db.execute("SELECT observation FROM runtime_observations WHERE episode_id=?",
            (frame.context.episode_id,)).fetchone()
        value = json.loads(row[0])
        value["credit"]["practical_completion"]["receipt_sha256"] = "b" * 64
        frame.store.db.execute("UPDATE runtime_observations SET observation=? WHERE episode_id=?",
            (canonical(value), frame.context.episode_id))
    monkeypatch.setattr(frame.owner, "_proof_for_action", forbidden)
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    with pytest.raises(ValueError, match="execution_closed_credit_"):
        frame.owner.verify_completion(frame.context, proof)


@pytest.mark.parametrize("state", ["active", "legacy_closed"])
def test_completion_without_closed_snapshot_keeps_the_original_verifier(frame, monkeypatch, state):
    proof = _completion_proof(frame)
    if state == "legacy_closed":
        _original_completion_observation(frame)
        facts, form = frame.saved()
        facts.pop(_CLOSED_CREDIT)
        frame.save(facts, form)
    calls = []
    def original(context, key):
        calls.append((context.episode_id, key))
        return deepcopy(proof)
    monkeypatch.setattr(frame.owner, "_proof_for_action", original)
    assert frame.owner.verify_completion(frame.context, proof) is True
    assert calls == [(frame.context.episode_id, proof["operation_key"])]
