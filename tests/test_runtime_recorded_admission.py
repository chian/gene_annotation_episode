"""Engineering journal frames for replaying an already admitted child return.

These use real Store, Journal, EpisodeReceipts and EpisodeReturnRecords. They
exercise the Runtime admission boundary without running an episode or provider.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

from method_loop import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_commissions import CommissionCoordinator
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.runtime import Record, TypedReportContract, Workflow
from gene_annotation_episode.state import Store


def forbidden(*_args, **_kwargs):
    raise AssertionError("recorded admission must not rerun delivery or read payload bytes")


def rows(store):
    return {row[0]: sorted(tuple(value) for value in store.db.execute('SELECT * FROM "' + row[0] + '"'))
        for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


class AdmissionFrame:
    index = 1

    def __init__(self, store, *, inherited=False):
        self.store, self.run_id, self.calls = store, "recorded-admission-engineering", []
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.proof = EpisodeReturnRecords(store, self.run_id, failure_prefix="recorded_admission_")
        self.scope = {"subject_refs": store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"]}
        second = store.artifact(b"engineering second scientific file")
        self.dependency = store.artifact(b"engineering dependency; not part of returned projection")
        source = store.put("source", {"provider": "engineering.recorded_admission", "accession": "fixture",
            "uri": None, "artifact_ref": self.dependency, "text_ref": second,
            "request_ref": None, "version": "engineering_v1", "retrieved_at": None}, origin="caller")
        self.references = [second, source["id"]]
        self.schema = {"type": "object", "properties": {
            "files": {"type": "array", "uniqueItems": True, "items": {"type": "string",
                "format": "reference"}, "x-source": "engineering_files"},
            "completed": {"type": "boolean", "x-source": "engineering_completed"}},
            "required": ["files", "completed"], "additionalProperties": False}
        # Scientific completion is deliberately false: successful typed receipt
        # replay does not require a completed scientific endpoint.
        self.form = {"files": list(self.references), "completed": False}
        contract = TypedReportContract("Return only the selected engineering files", self.schema, lambda *_: True)
        ancestor_path = (("annotation", "root"),)
        ancestor_id = EpisodeRef(self.run_id, ancestor_path).episode_id
        ancestor_goal = EpisodeGoal.root(objective="Exercise saved admission", result_contract={"role": "annotation"})
        ancestor_request = EpisodeRequest(ancestor_goal, Record({"scope": self.scope,
            "knowledge_inheritance": self.receipts.bind(ancestor_id)}), None)
        self.save_context(ancestor_path, ancestor_request)
        if inherited:
            self.receipts.receive(ancestor_id, self.references, kind="initial")
        self.path = (*ancestor_path, ("improvement", "child_0"))
        self.episode_id = EpisodeRef(self.run_id, self.path).episode_id
        parent_goal = EpisodeGoal.child(ancestor_goal, objective="Receive original files", result_contract={"role": "improvement"})
        self.request = EpisodeRequest(parent_goal, Record({"scope": self.scope,
            "knowledge_inheritance": self.receipts.bind(self.episode_id, ancestor_id)}), None)
        self.save_context(self.path, self.request)
        child_path = (*self.path, ("improvement", "child_1"))
        self.child_id = EpisodeRef(self.run_id, child_path).episode_id
        child_goal = EpisodeGoal.child(parent_goal, objective="Return engineering files", result_contract=contract.schema)
        child_request = EpisodeRequest(child_goal, Record({"scope": self.scope,
            "knowledge_inheritance": self.receipts.bind(self.child_id, self.episode_id)}), contract)
        self.save_context(child_path, child_request)
        self.journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": self.index,
            "action": canonical({"kind": "episode_child", "role": "improvement", "assignment": {},
                "scope": self.scope, "purpose": contract.decision, "schema_json": canonical(self.schema)}),
            "result": canonical({"status": "completed", "record_refs": self.references, "changed_record_refs": []}),
            "credit": 0})
        self.journal.save("runtime_forms", {"episode_id": self.child_id,
            "facts": canonical({"engineering_files": self.references, "engineering_completed": False}),
            "form": canonical(self.form)})
        self.journal.save("runtime_report_attempts", {"parent_episode_id": self.episode_id,
            "decision_index": self.index, "delivery_ref": "delivery_engineering_original", "child_episode_id": self.child_id,
            "contract": canonical(contract.as_record()), "form": canonical(self.form), "failure": None})
        if not inherited:
            self.receipts.receive(self.episode_id, self.references, kind="child_form", source_index=self.index)
        # EpisodeReceipts actually follows the Source's artifact dependency.
        # That receipt is not part of the original action's returned projection.
        self.source = SimpleNamespace(episode_id=self.episode_id, path=self.path, scope=self.scope, request=self.request)
        self.workflow = Workflow.__new__(Workflow)
        for name in ("store", "run_id", "journal", "receipts"):
            setattr(self.workflow, name, getattr(self, name))
        self.workflow.job_episodes = self.workflow.native_timing_information = None
        self.workflow.progress_provider = SimpleNamespace(receive_form=self.progress)
        self.workflow.episode_bindings = SimpleNamespace(received_form_references=self.references_for_form)

    def save_context(self, path, request):
        self.journal.save("runtime_episodes", {"episode_id": EpisodeRef(self.run_id, path).episode_id,
            "path": canonical(path), "request": canonical(request.as_record()), "initial_credit": 0,
            "state": "active", "completion": None, "archive": None})

    def context(self):
        return self.workflow.binding_context(self.source)

    def replay(self, *, redelivery=False):
        return self.workflow.receive_form(self.source, self.form, self.schema, self.index, redelivery=redelivery)

    def progress(self, *_args):
        self.calls.append("progress")

    def references_for_form(self, *_args):
        self.calls.append("specialist")
        return list(self.references)

    def outcome(self, **changes):
        value = json.loads(self.journal.row("runtime_actions", self.episode_id, self.index)["result"])
        value.update(changes)
        self.store.db.execute("UPDATE runtime_actions SET result=? "
            "WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(value), self.run_id, self.episode_id, self.index))


@pytest.fixture
def frame(tmp_path):
    with Store(tmp_path / "state") as store:
        yield AdmissionFrame(store)


def test_recorded_return_reuses_exact_order_without_callbacks_payloads_or_new_receipts(frame, monkeypatch):
    for path in (frame.store.path / "artifacts").glob("*/*"):
        path.unlink()
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    monkeypatch.setattr(frame.receipts, "receive", forbidden)
    monkeypatch.setattr(frame.workflow.progress_provider, "receive_form", forbidden)
    monkeypatch.setattr(frame.workflow.episode_bindings, "received_form_references", forbidden)
    before = rows(frame.store)
    result = frame.replay()
    assert result == frame.references and result is not frame.references
    assert frame.dependency not in result and frame.form["completed"] is False
    assert rows(frame.store) == before


@pytest.mark.parametrize("kind,index", [("initial", None), ("own_action", 0), ("decision_input", 1)])
def test_reference_already_received_at_original_decision_is_reused(frame, kind, index):
    frame.store.db.execute("UPDATE runtime_record_receipts SET receipt_kind=?,source_index=? "
        "WHERE run_id=? AND episode_id=? AND record_ref<>?",
        (kind, index, frame.run_id, frame.episode_id, frame.dependency))
    assert frame.replay() == frame.references
    assert frame.calls == []


def test_frozen_inherited_reference_is_reused_without_a_new_own_receipt(tmp_path):
    with Store(tmp_path / "state") as store:
        frame = AdmissionFrame(store, inherited=True)
        before = rows(store)
        assert frame.replay() == frame.references
        assert rows(store) == before


@pytest.mark.parametrize("field,value", [("run_id", "another-run"), ("episode_id", "episode_other"),
    ("scope", {"subject_refs": []})])
def test_substituted_receiver_context_is_rejected(frame, field, value):
    context = replace(frame.context(), **{field: value})
    with pytest.raises(ValueError, match="recorded_admission_context_conflict"):
        frame.proof.recorded_admission_references(context, frame.form, frame.schema, frame.index)


@pytest.mark.parametrize("changed", ["form", "boolean_type", "schema", "child_facts", "child_contract",
    "child_identity", "failed_attempt", "selected_role", "selected_kind"])
def test_original_commission_form_schema_and_facts_must_match(frame, changed):
    form, schema = deepcopy(frame.form), deepcopy(frame.schema)
    if changed == "form":
        form["files"].reverse()
    elif changed == "boolean_type":
        form["completed"] = 0
    elif changed == "schema":
        schema["properties"]["completed"]["description"] = "different contract"
    elif changed == "child_facts":
        frame.journal.save("runtime_forms", {"episode_id": frame.child_id,
            "facts": canonical({"engineering_files": [], "engineering_completed": False})})
    elif changed == "child_contract":
        row = frame.journal.row("runtime_episodes", frame.child_id)
        request = json.loads(row["request"])
        request["report_contract"]["decision"] = "substituted purpose"
        frame.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), frame.run_id, frame.child_id))
    elif changed in {"child_identity", "failed_attempt"}:
        field, value = (("child_episode_id", frame.episode_id) if changed == "child_identity"
            else ("failure", canonical({"reason": "not admitted"})))
        frame.store.db.execute("UPDATE runtime_report_attempts SET " + field + "=? "
            "WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (value, frame.run_id, frame.episode_id, frame.index))
    else:
        action = json.loads(frame.journal.row("runtime_actions", frame.episode_id, frame.index)["action"])
        action["role" if changed == "selected_role" else "kind"] = "other"
        frame.journal.save("runtime_actions", {"episode_id": frame.episode_id, "decision_index": frame.index,
            "action": canonical(action)})
    with pytest.raises(ValueError, match="recorded_admission_"):
        frame.proof.recorded_admission_references(frame.context(), form, schema, frame.index)


@pytest.mark.parametrize("changed", ["duplicates", "not_list", "not_reference", "missing_record",
    "record_identity", "extra_unreceived"])
def test_original_action_projection_requires_unique_existing_receipted_references(frame, changed, monkeypatch):
    if changed == "duplicates":
        frame.outcome(record_refs=[frame.references[0]] * 2)
    elif changed == "not_list":
        frame.outcome(record_refs=frame.references[0])
    elif changed == "not_reference":
        frame.outcome(record_refs=[True])
    elif changed == "missing_record":
        frame.store.db.execute("DELETE FROM artifacts WHERE id=?", (frame.references[0],))
    elif changed == "record_identity":
        original_get = frame.store.get
        monkeypatch.setattr(frame.store, "get", lambda ref: {**original_get(ref), "id": "different"})
    else:
        frame.outcome(record_refs=[*frame.references, frame.store.artifact(b"not received")])
    with pytest.raises(ValueError, match="recorded_admission_"):
        frame.replay()
    assert frame.calls == []


@pytest.mark.parametrize("changed", ["missing", "later", "redelivery", "other_run"])
def test_later_or_unrelated_receipt_cannot_authenticate_original_projection(frame, changed):
    key = (frame.run_id, frame.episode_id, frame.references[0])
    if changed == "missing":
        frame.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?", key)
    elif changed == "other_run":
        frame.store.db.execute("UPDATE runtime_record_receipts SET run_id='other' "
            "WHERE run_id=? AND episode_id=? AND record_ref=?", key)
    else:
        kind, index = (("child_form", frame.index + 1) if changed == "later" else ("report_redelivery", frame.index))
        frame.store.db.execute("UPDATE runtime_record_receipts SET receipt_kind=?,source_index=? "
            "WHERE run_id=? AND episode_id=? AND record_ref=?", (kind, index, *key))
    with pytest.raises(ValueError, match="recorded_admission_original_receipt_conflict"):
        frame.replay()
    assert frame.calls == []


@pytest.mark.parametrize("missing", ["action", "result", "projection", "partial_process_revision"])
def test_first_delivery_or_legacy_missing_projection_keeps_full_callbacks(frame, missing):
    if missing == "action":
        frame.store.db.execute("DELETE FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (frame.run_id, frame.episode_id, frame.index))
    elif missing == "result":
        frame.store.db.execute("UPDATE runtime_actions SET result=NULL "
            "WHERE run_id=? AND episode_id=? AND decision_index=?", (frame.run_id, frame.episode_id, frame.index))
    elif missing == "projection":
        frame.store.db.execute("UPDATE runtime_actions SET result=? "
            "WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical({"status": "completed"}), frame.run_id, frame.episode_id, frame.index))
    else:
        # _attempt also supports this existing tool-owned child-return path.
        # A partial outcome is not eligible for the completed-return shortcut.
        frame.journal.save("runtime_actions", {"episode_id": frame.episode_id, "decision_index": frame.index,
            "action": canonical({"kind": "tool", "tool": "process.revise", "arguments": {}})})
        frame.outcome(status="partial")
    assert frame.proof.recorded_admission_references(frame.context(), frame.form, frame.schema, frame.index) is None
    assert frame.replay() == frame.references
    assert frame.calls == ["progress", "specialist"]


def test_paged_member_without_ordinary_receipt_keeps_existing_delivery_path(frame, monkeypatch):
    material = frame.store.register_material(data=b">engineering member\nACGT\n", name="engineering member",
        format="fasta", molecule="dna")
    parsed = frame.store.parse_material(material["id"])
    assert parsed["status"] == "completed" and parsed["valid_records"] == 1
    member, = frame.store.material_members(parsed["collection_ref"])["members"]
    assert frame.store.get(member["id"])["record_type"] == "collection_member"
    frame.references = [member["id"]]
    frame.form["files"] = list(frame.references)
    frame.outcome(record_refs=frame.references)
    frame.journal.save("runtime_forms", {"episode_id": frame.child_id,
        "facts": canonical({"engineering_files": frame.references, "engineering_completed": False}),
        "form": canonical(frame.form)})
    frame.store.db.execute("UPDATE runtime_report_attempts SET form=? "
        "WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
        (canonical(frame.form), frame.run_id, frame.episode_id, frame.index))
    frame.receipts.receive(frame.episode_id, frame.references, kind="child_form", source_index=frame.index)
    assert member["id"] not in set(frame.receipts.known(frame.episode_id))
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    monkeypatch.setattr(frame.store, "material_read", forbidden)
    monkeypatch.setattr(frame.store, "material_member", forbidden)
    assert frame.proof.recorded_admission_references(frame.context(), frame.form, frame.schema, frame.index) is None
    assert frame.replay() == frame.references
    assert frame.calls == ["progress", "specialist"]
    assert member["id"] not in set(frame.receipts.known(frame.episode_id))


def test_explicit_redelivery_keeps_the_new_delivery_path(frame):
    assert frame.replay(redelivery=True) == frame.references
    assert frame.calls == ["progress", "specialist"]


@pytest.mark.parametrize("dispatch_completed", [False, True])
def test_original_pending_commission_still_runs_first_return_admission(frame, dispatch_completed):
    key = (frame.run_id, frame.episode_id, frame.index)
    frame.store.db.execute("DELETE FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?", key)
    frame.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=?",
        (frame.run_id, frame.episode_id))
    child = frame.proof.context(frame.child_id)
    coordinator = CommissionCoordinator(frame.store, frame.journal, SimpleNamespace())
    selected = {"kind": "episode_child", "role": child.role, "assignment": {}, "scope": frame.scope,
        "purpose": "Return only the selected engineering files", "schema_json": canonical(frame.schema)}
    spec = coordinator.select(parent={"episode_id": frame.episode_id, "path": plain(frame.path),
            "goal_id": frame.request.goal.goal_id},
        child={"episode_id": child.episode_id, "role": child.role, "key": child.path[-1][1],
            "path": plain(child.path), "request": plain(child.request), "scope": plain(child.scope)},
        original_decision_index=frame.index, selection=selected,
        runtime_binding={"factory_module": "engineering", "factory_name": "not_dispatched",
            "arguments": {}, "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64},
        input_versions=[], constraints={}, resource_selection=None, expectation_snapshot_refs=[],
        selected_at="2026-10-30T00:00:00+00:00")
    pending = json.loads(frame.journal.row("runtime_actions", frame.episode_id, frame.index)["result"])
    assert pending == {"status": "pending", "pending_handle": spec["handle"],
        "selected_at": "2026-10-30T00:00:00+00:00"}
    if dispatch_completed:
        # A completed dispatch envelope is still a commission, not the child
        # return projection written later by _admit_return.
        frame.outcome(status="completed", record_refs=[])
    assert frame.proof.recorded_admission_references(frame.context(), frame.form, frame.schema, frame.index) is None
    assert frame.replay() == frame.references
    assert frame.calls == ["progress", "specialist"]
    assert set(frame.references) <= set(frame.receipts.known(frame.episode_id))


@pytest.mark.parametrize("mode", ["no_receipts", "job_source"])
def test_nonreceipt_and_job_sources_keep_the_existing_progress_only_path(frame, mode):
    if mode == "no_receipts":
        frame.workflow.receipts = None
    else:
        frame.workflow.job_episodes = SimpleNamespace(roles=(frame.path[-1][0],))
    assert frame.replay() == []
    assert frame.calls == ["progress"]


def _outer_contract(frame, *, schema=None, context=None, recorded=True,
        reference_resolver=forbidden, semantic_validator=forbidden):
    selected_schema = frame.schema if schema is None else schema
    def original_projection(value):
        return frame.proof.recorded_admission_references(
            frame.context() if context is None else context, value, selected_schema, frame.index)
    return TypedReportContract("Return only the selected engineering files", selected_schema,
        reference_resolver, semantic_validator,
        recorded_admission=original_projection if recorded else None)


@pytest.mark.parametrize("projection", ["original", "empty"])
def test_outer_contract_reuses_proven_whole_form_without_live_domain_validation(frame, monkeypatch, projection):
    if projection == "empty":
        # The recorded host projection defines its subset. An empty list is a
        # proven projection, distinct from None / no original admission.
        frame.outcome(record_refs=[])
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    before = rows(frame.store)
    report = _outer_contract(frame).admit(frame.form, audit_identifiers=("original-child-audit-only",))
    assert report.as_record() == frame.form
    assert report._audit_identifiers == ("original-child-audit-only",)
    assert rows(frame.store) == before


def test_outer_recorded_form_still_rejects_current_generic_audit_identifiers(frame):
    from gene_annotation_episode.communication import ReportBoundaryError
    with pytest.raises(ReportBoundaryError, match="Internal audit identity") as error:
        _outer_contract(frame).admit(frame.form, audit_identifiers=(frame.references[0],))
    assert error.value.diagnostic["code"] == "audit_identity"


@pytest.mark.parametrize("changed", ["whole_form", "schema", "receiver", "child_facts"])
def test_outer_recorded_form_requires_exact_original_whole_form_authority(frame, changed):
    form, schema, context = deepcopy(frame.form), deepcopy(frame.schema), None
    if changed == "whole_form":
        form["completed"] = True
    elif changed == "schema":
        schema["properties"]["completed"]["description"] = "substituted schema"
    elif changed == "receiver":
        context = replace(frame.context(), scope={"subject_refs": []})
    else:
        frame.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
            (canonical({"engineering_files": frame.references, "engineering_completed": True}),
             frame.run_id, frame.child_id))
    with pytest.raises(ValueError, match="recorded_admission_"):
        _outer_contract(frame, schema=schema, context=context).admit(form,
            audit_identifiers=("original-child-audit-only",))


@pytest.mark.parametrize("mode", ["first_delivery", "pending_commission", "partial", "no_callback"])
def test_outer_contract_without_a_completed_original_projection_keeps_full_validation(frame, mode):
    events = []
    def resolve(reference, namespace):
        events.append(("reference", reference, namespace))
        return True
    def validate(form):
        assert form == frame.form
        events.append(("semantic",))
    if mode == "first_delivery":
        frame.store.db.execute("UPDATE runtime_actions SET result=NULL "
            "WHERE run_id=? AND episode_id=? AND decision_index=?", (frame.run_id, frame.episode_id, frame.index))
    elif mode == "pending_commission":
        frame.outcome(status="completed", pending_handle="execution_engineering_pending", record_refs=[])
    elif mode == "partial":
        frame.outcome(status="partial")
    report = _outer_contract(frame, recorded=mode != "no_callback", reference_resolver=resolve,
        semantic_validator=validate).admit(frame.form, audit_identifiers=("original-child-audit-only",))
    assert report.as_record() == frame.form
    assert {event[1] for event in events if event[0] == "reference"} == set(frame.references)
    assert events[-1] == ("semantic",) and events.count(("semantic",)) == 1


def test_optional_recorded_callback_does_not_change_serialized_contract_or_schema(frame):
    ordinary, recorded = _outer_contract(frame, recorded=False), _outer_contract(frame)
    assert canonical(ordinary.as_record()) == canonical(recorded.as_record())
    assert ordinary.schema == recorded.schema == frame.schema
    assert set(recorded.as_record()) == {"decision", "measurements", "information"}


def test_ordinary_outer_contract_still_validates_schema_before_semantic_callback(frame):
    from gene_annotation_episode.communication import ReportBoundaryError
    form = {**frame.form, "completed": 0}
    with pytest.raises(ReportBoundaryError):
        _outer_contract(frame, recorded=False).admit(form, audit_identifiers=("original-child-audit-only",))
