"""Current curation and distinct task assignments, without model inference.

The first check uses the actual immutable publication with no A entries. The
second uses an explicitly invented A fixture only to exercise commissioning.
Neither check adopts scientific support content or evaluates retrieval quality.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import obj
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_library import independent_source


PUBLICATION = (Path(__file__).resolve().parents[1] / "research/slotted_process_library"
               / "publications/2026-10-21-001")
FORM = obj({"status": {"type": "string", "enum": ["unresolved", "qualified"]}})


def zero_credit(*args, **kwargs):
    return 0


def setup_workflow(tmp_path, store, source):
    directory = tmp_path / "run"
    tools = build_tools(store)
    descriptor = prepare_scientific_binding(run_directory=directory,
        source_directory=source, tool_catalog=tools.catalog(),
        child_roles=["scientific_process", "literature"])
    workflow = Workflow(store, tools, ScriptedProvider([]), directory,
        "curated-task-boundaries", lambda path, initial: FixtureController(str(path), initial, 2),
        zero_credit, project_child_credit=zero_credit,
        episode_binding_descriptors=[descriptor, LiteratureEpisodes(None).as_record()],
        episode_record_receipts=True, initial_known_record_refs=[])
    problem = store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")
    scope = {"subject_refs": problem["subject_refs"]}
    root = workflow.build("annotation", "root", "Investigate the assigned sequence", scope)
    return workflow, root, scope


def commission(role, scope, assignment):
    return {"kind": "episode_child", "role": role,
        "goal": "Investigate the parent's bounded question", "scope": scope,
        "purpose": "Return the declared qualification status", "schema_json": json.dumps(FORM),
        "initial_report_json": '{"status":"unresolved"}', "assignment": assignment}


def test_current_publication_reconstructs_without_manufacturing_missing_support(tmp_path):
    with Store(tmp_path / "state") as store:
        workflow, root, scope = setup_workflow(tmp_path, store, PUBLICATION)
        library = workflow.scientific_process_binding.library
        assert [row["option_ref"]["option_id"] for row in library.headers()] == [
            f"P{number:02d}" for number in range(1, 20)]
        assert ScientificProcessLibrary(library.directory).as_record() == library.as_record()
        assert workflow.episode_bindings.roles == ("scientific_process", *LiteratureEpisodes.roles)

        outcome = asyncio.run(workflow.execute(root.source, "process.search",
            {"slot": "annotation_distinction", "query": "", "offset": 0, "limit": 99},
            decision_index=0, operation_key="inspect-unavailable-first-slot"))
        assert outcome["status"] == "completed" and outcome["result"]["entries"] == []
        assert outcome["record_refs"] == outcome["changed_record_refs"] == []

        # This deliberately invalid reference cannot turn a real P body into A
        # content, even when its digest and library identity came from real data.
        invalid_a = {**library.reference("P01"), "slot": "annotation_distinction", "option_id": "A01"}
        assignment = {"selection": {"version": "scientific_process_selection_v2",
            "annotation_ref": invalid_a, "thought_ref": library.reference("P01"),
            "tools": ["sequence.inspect"]}, "evidence_refs": [], "constraints": {}, "context": {}}
        with pytest.raises(ValueError, match="scientific_process_option_unknown"):
            workflow.scientific_process_binding.prepare_assignment(
                workflow.binding_context(root.source), "scientific_process", assignment, scope,
                "invalid-support-assignment")
        # Ordinary commissioning also fails before publishing a child: the
        # scientific result-source schema requires a nonempty adopted A catalog.
        with pytest.raises(ValueError, match="scientific_process_result_library_invalid"):
            workflow.selected(root.source, commission("scientific_process", scope, assignment), 0)
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_scientific_slots_and_distinct_literature_keep_separate_assignments(tmp_path):
    source = tmp_path / "invented-source"
    independent_source(source)
    with Store(tmp_path / "state") as store:
        workflow, root, scope = setup_workflow(tmp_path, store, source)
        library = workflow.scientific_process_binding.library
        actual = workflow.tools.catalog()
        selected = {"version": "scientific_process_selection_v2",
            "annotation_ref": library.reference("A01"), "thought_ref": library.reference("P01"),
            "tools": ["source.read", "sequence.inspect"]}
        scientific = workflow.selected(root.source, commission("scientific_process", scope,
            {"selection": selected, "evidence_refs": scope["subject_refs"],
             "constraints": {"engineering_fixture_only": True}, "context": {}}), 0).child
        original_scientific = deepcopy(scientific.request.as_record())
        scientific_binding = workflow.specialist(scientific.source)
        scientific_context = workflow.binding_context(scientific.source)
        frame = scientific_binding.decision_context(scientific_context, {})["scientific_process"]
        assert frame["tools"] == [{"name": name, **actual[name]} for name in selected["tools"]]
        assert frame["permitted_children"] == ["scientific_process", "literature"]

        literal = b"Engineering source fixture; no biological evidence."
        artifact = store.artifact(literal, "text/plain")
        source_ref = store.put("source", {"provider": "fixture.boundary",
            "accession": None, "uri": None, "artifact_ref": artifact, "text_ref": artifact,
            "request_ref": None, "version": "fixture", "retrieved_at": None,
            "parent_source_refs": [], "operand_refs": scope["subject_refs"]}, origin="tool")["id"]
        literature_assignment = {"version": "literature_assignment_v1",
            "question_context_refs": scope["subject_refs"], "source_refs": [source_ref]}
        literature = workflow.selected(scientific.source,
            commission("literature", scope, literature_assignment), 0).child
        literature_binding = workflow.specialist(literature.source)
        literature_context = workflow.binding_context(literature.source)
        assert isinstance(literature_binding, LiteratureEpisodes)
        assert literature_context.as_record()["assignment"] == literature_assignment
        assert "scientific_process" not in literature.request.message.as_record()
        assert "selection" not in literature_context.assignment
        assert literature.request.report_contract.schema == scientific.request.report_contract.schema == FORM
        assert scientific.request.as_record() == original_scientific
        assert not workflow.scientific_library_available(literature.source)

        expected_edges = {"literature": ("literature_strategy",),
            "literature_strategy": ("literature_search",),
            "literature_search": ("literature_page",),
            "literature_page": ("literature_table", "literature_ordered", "literature_targeted"),
            "literature_table": (), "literature_ordered": (), "literature_targeted": ()}
        assert {role: literature_binding.child_roles(role) for role in literature_binding.roles} == expected_edges
        literature_names = {entry["name"] for entry in workflow.catalog(scope, source=literature.source)}
        scientific_names = {entry["name"] for entry in workflow.catalog(scope, source=scientific.source)}
        assert "source.read" in literature_names & scientific_names
        assert "sequence.inspect" in scientific_names - literature_names
        assert "public.literature.search" in literature_names - scientific_names
        assert not any(name.startswith("process.") for name in literature_names)

        # Sharing a real byte-reader operation neither commissions nor converts
        # a literature task. Both dispatch through the actual ordinary registry.
        arguments = {"source_ref": source_ref, "offset": 0, "limit": len(literal), "representation": "original"}
        for current, key in ((scientific, "scientific-source-read"), (literature, "literature-source-read")):
            outcome = asyncio.run(workflow.execute(current.source, "source.read", arguments,
                decision_index=0, operation_key=key))
            assert outcome["status"] == "completed"
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert not store.list("assessment")
