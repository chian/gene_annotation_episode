"""Actual retrieval -> ordinary scientific commission -> actual tool dispatch.

The Store, tools, forms, snapshots, journal and shared Episode loop are real.
Decisions and continuation are explicit engineering fixtures. No biological
relevance evaluation or configured-model scientific demonstration is claimed.
"""
import asyncio
from copy import deepcopy
import json
import shutil

import pytest

from gene_annotation_episode.domain import obj
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_library import independent_source


FORM = obj({
    "status": {"type": "string", "enum": ["unresolved", "measured"]},
    "records": {"type": "array", "items": {"type": "string", "format": "reference"},
        "x-source": "committed_record_refs"},
})
INVESTIGATION = "composition translation codes"
OTHER_INVESTIGATION = "archive inventoried"
GOAL = "Distinguish what the supplied sequence measurements establish"


def action(name, arguments, status=None):
    return {"selection": {"kind": "tool", "tool": name, "arguments": arguments},
        "report_update": {} if status is None else {"status": status}}


def zero_credit(store, scope, **assignment):
    # The caller supplies this fixture unit explicitly. Retrieving contracts,
    # constructing a child, and recording source bytes cannot create a score.
    return 0


class ActualToolCase:
    def __init__(self, tmp_path, store, *, stops=None):
        self.store = store
        self.directory, self.source = tmp_path / "run", tmp_path / "source"
        self.directory.mkdir()
        independent_source(self.source, extra=True)
        self.tools = build_tools(store)
        self.descriptor = prepare_scientific_binding(run_directory=self.directory,
            source_directory=self.source, tool_catalog=self.tools.catalog(),
            child_roles=["scientific_process"])
        self.library = ScientificProcessLibrary(self.directory / "scientific-process-library")
        problem = store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")
        self.scope = {"subject_refs": problem["subject_refs"]}
        self.target = self.scope["subject_refs"][0]
        self.stops = {1: 4, 2: 2} if stops is None else stops
        self.controllers = []

    def factory(self, path, initial):
        controller = FixtureController(str(path), initial, self.stops[len(path)])
        self.controllers.append((tuple(path), controller))
        return controller

    def selection(self, tools, *, thought="P01"):
        return {"version": "scientific_process_selection_v2",
            "annotation_ref": self.library.reference("A01"),
            "thought_ref": self.library.reference(thought), "tools": list(tools)}

    def commission(self, tools, *, thought="P01", revision_origin=None):
        assignment = {"selection": self.selection(tools, thought=thought),
            "evidence_refs": [self.target], "constraints": {"target_only": True},
            "context": {"investigation": INVESTIGATION}}
        if revision_origin is not None:
            assignment["revision_origin"] = revision_origin
        return {"selection": {"kind": "episode_child", "role": "scientific_process",
            "goal": "Assess composition and translation information for this sequence",
            "scope": self.scope,
            "purpose": "Return the bounded interpretation and newly recorded measurements",
            "schema_json": json.dumps(FORM),
            "initial_report_json": '{"status":"unresolved"}', "assignment": assignment},
            "report_update": {}}

    def workflow(self, provider):
        return Workflow(self.store, self.tools, provider, self.directory, "actual-tools-fixture",
            self.factory, zero_credit, project_child_credit=zero_credit,
            episode_binding_descriptors=[self.descriptor], episode_record_receipts=True,
            initial_known_record_refs=[])

    def run(self, provider, *, resume=False):
        return asyncio.run(run_workflow(self.store, self.tools, provider=provider,
            run_dir=self.directory, resume=resume, controller_factory=self.factory,
            project_credit=zero_credit, project_child_credit=zero_credit,
            episode_record_receipts=True, initial_known_record_refs=[],
            **({} if resume else {"episode_binding_descriptors": [self.descriptor]})))


def test_parent_retrieval_fills_multi_tool_child_and_preserves_original_form_on_restore(tmp_path):
    with Store(tmp_path / "state") as store:
        case = ActualToolCase(tmp_path, store)
        retrieved, commissions, child_frames, received = [], [], [], []

        def another_investigation(context):
            result = deepcopy(context["last_local_outcome"])
            assert result["status"] == "completed"
            assert result["record_refs"] == result["changed_record_refs"] == []
            retrieved.append(result["result"])
            return action("process.tools", {"investigation": OTHER_INVESTIGATION})

        def commission_from_retrieval(context):
            retrieved.append(deepcopy(context["last_local_outcome"]["result"]))
            assert retrieved[0]["tools"] != retrieved[1]["tools"]
            selected = retrieved[0]["tools"]
            assert {"sequence.inspect", "translation.codes"} <= set(selected)
            commission = case.commission(selected)
            commissions.append(deepcopy(commission))
            return commission

        def inspect_sequence(context):
            child_frames.append(deepcopy(context))
            assert context["requested_form"] == FORM
            assert context["scientific_process"]["selection"] == case.selection(retrieved[0]["tools"])
            names = {entry["name"] for entry in context["tools"]}
            assert {"sequence.inspect", "translation.codes"} <= names
            assert "source.archive.extract" not in names
            return action("sequence.inspect", {"subject_ref": case.target}, "unresolved")

        def read_translation_codes(context):
            child_frames.append(deepcopy(context))
            assert context["last_local_outcome"]["status"] == "completed"
            assert context["last_local_outcome"]["result"]["length"] == 9
            return action("translation.codes", {}, "measured")

        def receive_original_form(context):
            report, = context["child_reports"]
            received.append(deepcopy(report))
            assert set(report) == {"status", "records"}
            assert report["status"] == "measured"
            assert len(report["records"]) == 2
            assert {store.get(ref)["record_type"] for ref in report["records"]} == {"source", "observation"}
            return action("episode.history", {"view": "index"})

        provider = ScriptedProvider([
            action("process.tools", {"investigation": INVESTIGATION}), another_investigation,
            commission_from_retrieval, inspect_sequence, read_translation_codes, receive_original_form])
        workflow = case.workflow(provider)
        root = workflow.build("annotation", "root", GOAL, case.scope)
        closed = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(closed))

        selected = retrieved[0]["tools"]
        assert all(frame["scientific_process"]["selection"] == case.selection(selected)
            for frame in child_frames)
        rows = store.db.execute("SELECT name,result FROM tool_operations ORDER BY name").fetchall()
        assert [row["name"] for row in rows] == ["sequence.inspect", "translation.codes"]
        outcomes = {row["name"]: json.loads(row["result"]) for row in rows}
        assert outcomes["sequence.inspect"]["status"] == "completed"
        assert outcomes["translation.codes"]["status"] == "completed"
        assert any(code["code"] == 11 for code in outcomes["translation.codes"]["result"]["codes"])
        # Four parent actions and two child actions, regardless of how many
        # contracts retrieval selected. Internal work supplies no parent turns.
        assert [controller.scores for _, controller in case.controllers] == [[0, 0, 0, 0], [0, 0]]
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 6
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 6
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls").fetchone()[0] == 6
        child_row = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()
        original_request = json.loads(child_row["request"])
        assert original_request["message"]["episode_assignment"]["selection"] == case.selection(selected)
        assert original_request["report_contract"]["measurements"]["schema"] == FORM
        assert not store.list("assessment")
        assert len(store.list("observation")) == 1  # Actual measured composition only.

        shutil.rmtree(case.source)
        restored = case.workflow(ScriptedProvider([]))
        restored_root = restored.build("annotation", "root", GOAL, case.scope)
        restored_child = restored.selected(restored_root.source, commissions[0]["selection"], 2).child
        assert restored_child.request.as_record() == original_request
        binding = restored.specialist(restored_child.source)
        assert binding.decision_context(restored.binding_context(restored_child.source), {})[
            "scientific_process"]["selection"] == case.selection(selected)
        assert restored_child.request.report_contract.schema == FORM
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 6


def test_selected_actual_tools_reject_excluded_and_imagined_dispatch(tmp_path):
    with Store(tmp_path / "state") as store:
        case = ActualToolCase(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root = workflow.build("annotation", "root", GOAL, case.scope)
        binding = workflow.scientific_process_binding
        selected = binding.tool_library.retrieve(INVESTIGATION)["tools"]
        child = workflow.selected(root.source, case.commission(selected)["selection"], 0).child
        before = child.request.as_record()
        for name, arguments in [("state.query", {"refs": [case.target]}),
                ("source.archive.members", {"source_ref": case.target}),
                ("invented.annotation.tool", {})]:
            assert name not in selected
            outcome = asyncio.run(workflow.execute(child.source, name, arguments,
                decision_index=0, operation_key="excluded:" + name))
            assert outcome["status"] == "invalid"
            assert outcome["record_refs"] == outcome["changed_record_refs"] == []
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert child.request.as_record() == before
        malformed = case.commission(["invented.annotation.tool"])["selection"]
        with pytest.raises(ValueError):
            workflow.selected(root.source, malformed, 1)
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 2


@pytest.mark.parametrize("drift", ["missing", "schema"])
def test_commission_rejects_changed_selected_contract_before_child_credit(tmp_path, monkeypatch, drift):
    with Store(tmp_path / "state") as store:
        case = ActualToolCase(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root = workflow.build("annotation", "root", GOAL, case.scope)
        selected = workflow.scientific_process_binding.tool_library.retrieve(INVESTIGATION)["tools"]
        actual = deepcopy(case.tools.catalog())
        if drift == "missing":
            del actual["translation.codes"]
        else:
            actual["translation.codes"]["input_schema"] = {"type": "null"}
        monkeypatch.setattr(case.tools, "catalog", lambda scope=None: actual)

        def forbidden_credit(*args, **kwargs):
            pytest.fail("An invalid selected contract reached child initial credit")

        monkeypatch.setattr(workflow, "project_child_credit", forbidden_credit)
        with pytest.raises(ValueError, match="scientific_tool_contract_changed"):
            workflow.selected(root.source, case.commission(selected)["selection"], 0)
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0


def test_interruption_replays_retrieval_and_fixed_child_without_repeating_real_work(tmp_path):
    with Store(tmp_path / "state") as store:
        case = ActualToolCase(tmp_path, store, stops={1: 3, 2: 2})
        retrieved = []

        def commission(context):
            retrieved.append(deepcopy(context["last_local_outcome"]["result"]))
            return case.commission(retrieved[0]["tools"])

        with pytest.raises(KeyboardInterrupt):
            case.run(ScriptedProvider([
                action("process.tools", {"investigation": INVESTIGATION}), commission,
                action("sequence.inspect", {"subject_ref": case.target}, "unresolved"),
                KeyboardInterrupt()]))
        child = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()
        original_request = child["request"]
        retrieval_row = tuple(store.db.execute("SELECT * FROM runtime_actions WHERE decision_index=0 "
            "AND episode_id=(SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1)").fetchone())
        original_actions = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_actions "
            "WHERE episode_id=?", (child["episode_id"],))]
        shutil.rmtree(case.source)
        provider = ScriptedProvider([action("translation.codes", {}, "measured"),
            action("episode.history", {"view": "index"})])
        result = case.run(provider, resume=True)
        assert result["completed_actions"] == 3 and result["credit"] == 0
        assert provider.contexts[0]["scientific_process"]["selection"] == case.selection(retrieved[0]["tools"])
        assert provider.contexts[0]["requested_form"] == FORM
        assert provider.contexts[-1]["child_reports"][0]["status"] == "measured"
        assert store.db.execute("SELECT request FROM runtime_episodes WHERE episode_id=?",
            (child["episode_id"],)).fetchone()[0] == original_request
        assert [tuple(row) for row in store.db.execute("SELECT * FROM runtime_actions "
            "WHERE episode_id=? AND decision_index=0", (child["episode_id"],))] == original_actions
        assert tuple(store.db.execute("SELECT * FROM runtime_actions WHERE decision_index=0 "
            "AND episode_id=(SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1)").fetchone()) == retrieval_row
        assert [row[0] for row in store.db.execute("SELECT name FROM tool_operations ORDER BY name")] == [
            "sequence.inspect", "translation.codes"]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5


def test_revision_prepares_retrieved_tools_for_separate_child_without_mutating_parent(tmp_path):
    with Store(tmp_path / "state") as store:
        case = ActualToolCase(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root = workflow.build("annotation", "root", GOAL, case.scope)
        binding = workflow.scientific_process_binding
        original_tools = binding.tool_library.retrieve(INVESTIGATION)["tools"]
        original = case.commission(original_tools)["selection"]
        child = workflow.selected(root.source, original, 0).child
        original_request = deepcopy(child.request.as_record())
        context = workflow.binding_context(child.source)
        other = asyncio.run(workflow.execute(child.source, "process.tools",
            {"investigation": OTHER_INVESTIGATION}, decision_index=0, operation_key="retrieve-alternative"))
        assert other["status"] == "completed"
        assert other["record_refs"] == other["changed_record_refs"] == []
        other_tools = other["result"]["tools"]
        assert other_tools != original_tools
        arguments = {"thought_ref": case.library.reference("P77"), "tools": other_tools}
        prepared = asyncio.run(workflow.execute(child.source, "process.revise", arguments,
            decision_index=0, operation_key=f"{workflow.run_id}:{child.source.episode_id}:0"))
        assert prepared["status"] == "completed"
        assert prepared["result"]["selection"] == case.selection(other_tools, thought="P77")
        assert prepared["record_refs"] == prepared["changed_record_refs"] == []
        workflow.journal.save("runtime_actions", {"episode_id": child.source.episode_id,
            "decision_index": 0, "action": json.dumps(action("process.revise", arguments)["selection"]),
            "result": json.dumps(prepared), "credit": 0})
        assert workflow.services.scientific_preparation(context, prepared["operation_ref"])[
            "proposal"] == prepared["result"]
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 2
        assert child.request.as_record() == original_request
        nested = case.commission(other_tools, thought="P77",
            revision_origin=prepared["revision_origin"])["selection"]
        grandchild = workflow.selected(child.source, nested, 1).child
        assert grandchild.request.message.as_record()["episode_assignment"]["selection"] == prepared["result"]["selection"]
        assert grandchild.request.message.as_record()["episode_assignment"]["revision_origin"] == prepared["revision_origin"]
        assert child.request.as_record() == original_request
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
