"""Engineered original Results commissions at the actual preparation boundary.

Store, Journal, typed requests, EPR and receipt traversal are real. No service,
scientific producer or Workflow is executed by these controlled journal frames.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

from method_loop import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


def forbidden(*_args, **_kwargs):
    raise AssertionError("proven Results restoration must not prepare or read native payloads")


def rows(store):
    return {row[0]: sorted(tuple(value) for value in store.db.execute('SELECT * FROM "' + row[0] + '"'))
        for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


class ResultsFrame:
    index = 1

    def __init__(self, store, *, receipts=True):
        self.store, self.run_id = store, "recorded-results-engineering"
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id) if receipts else None
        self.scope = {"subject_refs": store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"]}
        handoff = self.source("original handoff metadata")
        result = self.source("original returned data")
        self.result_ref = result["id"]
        self.assignment = {"version": "execution_results_assignment_v1", "handoff_ref": handoff["id"],
            "selector": {"version": "enrichr_selector_v1", "offset": 0, "limit": 1}}
        self.schema = {"type": "object", "properties": {
            "sources": {"type": "array", "uniqueItems": True, "items": {"type": "string", "format": "reference"},
                "x-source": "execution_result_refs"},
            "completed": {"type": "boolean", "x-source": "execution_completed"}},
            "required": ["sources", "completed"], "additionalProperties": False}
        # Successful return of partial data does not establish a completed
        # scientific endpoint. It still establishes the original assignment.
        self.form = {"sources": [self.result_ref], "completed": False}
        contract = TypedReportContract("Return the selected original data", self.schema, lambda *_: True)
        path = (("scientific_process", "root"),)
        parent_goal = EpisodeGoal.root(objective="Preserve original Results selection", result_contract={"role": "scientific_process"})
        self.parent = self.context(path, parent_goal, {}, None)
        if self.receipts is not None:
            self.receipts.receive(self.parent.episode_id, [handoff["id"]], kind="initial")
        child_goal = EpisodeGoal.child(parent_goal, objective="Read selected original rows", result_contract=contract.schema)
        self.child = self.context((*path, ("results", "child_1")), child_goal, self.assignment, contract,
            parent=self.parent, state="yielded")
        self.key = f"{self.run_id}:{self.parent.episode_id}:{self.index}"
        self.journal.save("runtime_actions", {"episode_id": self.parent.episode_id, "decision_index": self.index,
            "action": canonical({"kind": "episode_child", "role": "results", "assignment": self.assignment,
                "scope": self.scope, "purpose": contract.decision, "schema_json": canonical(self.schema)}),
            "result": canonical({"status": "completed", "record_refs": [self.result_ref], "changed_record_refs": []}),
            "credit": 0})
        self.journal.save("runtime_forms", {"episode_id": self.child.episode_id,
            "facts": canonical({"execution_result_refs": self.form["sources"], "execution_completed": False}),
            "form": canonical(self.form)})
        self.journal.save("runtime_report_attempts", {"parent_episode_id": self.parent.episode_id,
            "decision_index": self.index, "delivery_ref": "delivery_engineering_results", "child_episode_id": self.child.episode_id,
            "contract": canonical(contract.as_record()), "form": canonical(self.form), "failure": None})
        if self.receipts is not None:
            self.receipts.receive(self.parent.episode_id, self.form["sources"], kind="child_form", source_index=self.index)
        self.owner = ExecutionEpisodes.__new__(ExecutionEpisodes)
        self.owner.store, self.owner.run_id, self.owner.resources = store, self.run_id, {}
        for name in ("native_expression_nmf_results", "native_flux_balance_results", "atac_results",
                "native_chromatin_interaction_results", "native_rna_structure_results", "native_genomic_overlap_results"):
            setattr(self.owner, name, None)
        self.owner._retained_masking_target = forbidden
        self.owner.job_progress_provider = SimpleNamespace(targets=SimpleNamespace(read_target=forbidden))

    def source(self, text):
        artifact = self.store.artifact(text)
        return self.store.put("source", {"provider": "engineering.recorded_results", "accession": None,
            "uri": None, "artifact_ref": artifact, "text_ref": None, "request_ref": None,
            "version": "engineering_v1", "retrieved_at": None}, origin="caller")

    def context(self, path, goal, assignment, contract, *, parent=None, state="active"):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        message = {"scope": self.scope, "episode_assignment": assignment, "initial_report": {}}
        if self.receipts is not None:
            message["knowledge_inheritance"] = self.receipts.bind(episode_id,
                None if parent is None else parent.episode_id)
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path), "request": canonical(request),
            "initial_credit": 0, "state": state,
            "completion": canonical({"ended_by": "yield_stop", "actions": 1}) if state == "yielded" else None,
            "archive": None})
        return BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)

    def prepare(self, *, assignment=None, scope=None, key=None):
        return self.owner.prepare_assignment(self.parent, "results",
            self.assignment if assignment is None else assignment,
            self.scope if scope is None else scope, self.key if key is None else key)

    def outcome(self, **changes):
        row = self.journal.row("runtime_actions", self.parent.episode_id, self.index)
        value = json.loads(row["result"])
        value.update(changes)
        self.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(value), self.run_id, self.parent.episode_id, self.index))


@pytest.fixture
def frame(tmp_path):
    with Store(tmp_path / "state") as store:
        yield ResultsFrame(store)


def test_original_results_assignment_is_restored_detached_without_preparation_bytes_or_writes(frame, monkeypatch):
    for path in (frame.store.path / "artifacts").glob("*/*"):
        path.unlink()
    monkeypatch.setattr(frame.store, "get_artifact", forbidden)
    before = rows(frame.store)
    result = frame.prepare()
    assert result == frame.assignment == plain(frame.child.assignment)
    assert result is not frame.assignment
    result["selector"]["offset"] = 99
    assert frame.prepare()["selector"]["offset"] == 0
    assert frame.form["completed"] is False and rows(frame.store) == before


@pytest.mark.parametrize("changed", ["foreign_run", "foreign_parent", "leading_zero", "suffix"])
def test_recorded_results_requires_original_parent_operation_identity(frame, changed):
    key = {"foreign_run": f"other:{frame.parent.episode_id}:1",
        "foreign_parent": f"{frame.run_id}:episode_other:1", "leading_zero": frame.key[:-1] + "01",
        "suffix": frame.key + ":typed_form"}[changed]
    with pytest.raises(ValueError, match="recorded_results_admission_operation_required"):
        frame.prepare(key=key)


@pytest.mark.parametrize("changed", ["current_assignment", "current_scope", "receiver", "original_assignment",
    "original_scope", "child_scope", "child_identity", "slot", "contract", "facts", "selected_kind", "receipt"])
def test_recorded_results_rejects_conflicting_original_or_current_commission_metadata(frame, changed):
    assignment, scope = deepcopy(frame.assignment), deepcopy(frame.scope)
    if changed == "current_assignment":
        assignment["selector"]["offset"] = 1
    elif changed == "current_scope":
        scope["subject_refs"] = []
    elif changed == "receiver":
        frame.parent = replace(frame.parent, scope={"subject_refs": []})
    elif changed in {"original_assignment", "child_scope"}:
        request = plain(frame.child.request)
        if changed == "original_assignment":
            request["message"]["episode_assignment"]["selector"]["offset"] = 1
        else:
            request["message"]["scope"]["subject_refs"] = []
        frame.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), frame.run_id, frame.child.episode_id))
    elif changed in {"original_scope", "selected_kind"}:
        action = json.loads(frame.journal.row("runtime_actions", frame.parent.episode_id, frame.index)["action"])
        if changed == "original_scope":
            action["scope"]["subject_refs"] = []
        else:
            action["kind"] = "child"
        frame.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(action), frame.run_id, frame.parent.episode_id, frame.index))
    elif changed == "child_identity":
        frame.store.db.execute("UPDATE runtime_report_attempts SET child_episode_id=? "
            "WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (frame.parent.episode_id, frame.run_id, frame.parent.episode_id, frame.index))
    elif changed == "slot":
        path = [*plain(frame.child.path[:-1]), ["results", "child_9"]]
        frame.store.db.execute("UPDATE runtime_episodes SET path=? WHERE run_id=? AND episode_id=?",
            (canonical(path), frame.run_id, frame.child.episode_id))
    elif changed == "contract":
        request = plain(frame.child.request)
        request["report_contract"]["decision"] = "changed contract"
        frame.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), frame.run_id, frame.child.episode_id))
    elif changed == "facts":
        frame.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
            (canonical({"execution_result_refs": [], "execution_completed": False}), frame.run_id, frame.child.episode_id))
    else:
        frame.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
            (frame.run_id, frame.parent.episode_id, frame.result_ref))
    with pytest.raises(ValueError, match="recorded_results_"):
        frame.prepare(assignment=assignment, scope=scope)


class LivePreparation(Exception):
    pass


def require_live_path(frame, monkeypatch):
    seen = []
    def live(parent, selected, scope):
        assert parent == frame.parent and selected == frame.assignment and scope == frame.scope
        seen.append(True)
        raise LivePreparation
    monkeypatch.setattr(frame.owner, "_retained_masking_target", live)
    with pytest.raises(LivePreparation):
        frame.prepare()
    assert seen == [True]


@pytest.mark.parametrize("state", ["first", "pending", "partial_status", "legacy", "missing_attempt",
    "failed_return", "active_child"])
def test_results_without_successful_completed_original_projection_keeps_live_preparation(frame, monkeypatch, state):
    key = (frame.run_id, frame.parent.episode_id, frame.index)
    if state == "first":
        frame.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=?", key)
    elif state == "pending":
        frame.outcome(status="completed", pending_handle="execution_engineering_pending", record_refs=[])
    elif state == "partial_status":
        frame.outcome(status="partial")
    elif state == "legacy":
        frame.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical({"status": "completed"}), *key))
    elif state == "missing_attempt":
        frame.store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?", key)
    elif state == "failed_return":
        frame.store.db.execute("UPDATE runtime_report_attempts SET failure=? "
            "WHERE run_id=? AND parent_episode_id=? AND decision_index=?", (canonical({"reason": "not received"}), *key))
    else:
        frame.store.db.execute("UPDATE runtime_episodes SET state='active' WHERE run_id=? AND episode_id=?",
            (frame.run_id, frame.child.episode_id))
    require_live_path(frame, monkeypatch)


def test_results_without_receipt_binding_keeps_live_preparation(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        require_live_path(ResultsFrame(store, receipts=False), monkeypatch)


def test_results_member_projection_without_ordinary_receipt_keeps_live_preparation(frame, monkeypatch):
    material = frame.store.register_material(data=b">engineering\nACGT\n", format="fasta", molecule="dna")
    parsed = frame.store.parse_material(material["id"])
    assert parsed["status"] == "completed"
    member, = frame.store.material_members(parsed["collection_ref"])["members"]
    frame.form["sources"] = [member["id"]]
    frame.outcome(record_refs=[member["id"]])
    frame.store.db.execute("UPDATE runtime_forms SET facts=?,form=? WHERE run_id=? AND episode_id=?",
        (canonical({"execution_result_refs": frame.form["sources"], "execution_completed": False}),
         canonical(frame.form), frame.run_id, frame.child.episode_id))
    frame.store.db.execute("UPDATE runtime_report_attempts SET form=? "
        "WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
        (canonical(frame.form), frame.run_id, frame.parent.episode_id, frame.index))
    frame.receipts.receive(frame.parent.episode_id, [member["id"]], kind="child_form", source_index=frame.index)
    assert member["id"] not in set(frame.receipts.known(frame.parent.episode_id))
    require_live_path(frame, monkeypatch)


def test_current_assignment_schema_is_checked_before_recorded_restoration(frame, monkeypatch):
    assignment = {**frame.assignment, "selector": []}
    monkeypatch.setattr(frame.owner, "_recorded_results_assignment", forbidden)
    with pytest.raises(ValueError, match="invalid_execution_assignment"):
        frame.prepare(assignment=assignment)
