"""A101 construction and receiving boundaries over actual Store/library data."""
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.a101_investigation import A101Subtree, initial_report, report_schema
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a101.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.episode import ScientificProcessEpisode
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.a101.tools import ToolRegistry


PUBLICATION = Path(__file__).resolve().parents[5] / "research/slotted_process_library/publications/2026-10-24-001"


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")["subject_refs"]
        directory = tmp_path / "run"
        prepare_scientific_binding(episode_type=ScientificProcessEpisode, run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=ToolRegistry(store).catalog(), child_roles=("scientific_process",))
        yield store, target, A101Subtree(directory)


def commission(case, **changes):
    store, target, subtree = case
    return subtree.commission(store, **{ "target_ref": target,
        "scope": {"subject_refs": [target]}, "completeness": "unknown",
        "child_tool_info": [{"name": "sequence.inspect", "resources": "local"}],
        "question": "Investigate possible functions of this supplied unnamed sequence.",
        **changes})


@pytest.mark.parametrize("completeness", ["complete", "fragment", "unknown"])
def test_unnamed_material_commission_is_explicit_and_performs_no_science(case, completeness):
    store, target, subtree = case
    count = store.count("observation")
    selection = commission(case, completeness=completeness)
    assignment = selection["assignment"]
    assert assignment["selection"]["evidence_axis"] == subtree.library.reference("A101")
    assert assignment["selection"]["thought_pattern"] == subtree.library.reference("P01")
    material = assignment["context"]["a101_material"]
    assert material["subject_ref"] == target and material["supplied_length"] == 10
    assert material["completeness"] == completeness and material["unit"] == "aa"
    assert assignment["evidence_refs"] == [target]
    assert json.loads(selection["initial_report_json"]) == initial_report()
    assert json.loads(selection["schema_json"]) == report_schema()
    assert store.count("observation") == count and not store.current_assessments()


def test_exact_scope_and_material_metadata_cannot_be_substituted(case):
    store, target, _ = case
    narrow = {"subject_refs": [target], "segments": [
        {"target_ref": target, "start": 0, "end": 4, "unit": "aa"}]}
    with pytest.raises(ContractError, match="material_outside_scope"):
        commission(case, scope=narrow)
    with pytest.raises(ContractError, match="material_context_reserved"):
        commission(case, context={"a101_material": {"completeness": "complete"}})
    with pytest.raises(ContractError, match="completeness_required"):
        commission(case, completeness="assume_complete")
    feature = store.put("feature", {"subject_ref": target, "kind": "protein_domain",
        "segments": [{"start": 0, "end": 4}], "strand": ".", "context_refs": []},
        origin="reasoning")["id"]
    selected = commission(case, target_ref=feature, scope=narrow, completeness="fragment")
    assert selected["assignment"]["context"]["a101_material"]["supplied_length"] == 4


def test_alternate_thought_and_tools_are_new_pinned_selections(case):
    _, _, subtree = case
    first = commission(case)
    second = commission(case, thought_id="P02", child_tool_info=[
        {"name": "sequence.sites", "resources": "local"}])
    assert second["assignment"]["selection"]["thought_pattern"] == subtree.library.reference("P02")
    assert first["assignment"]["selection"]["thought_pattern"] == subtree.library.reference("P01")
    with pytest.raises(ValueError):
        commission(case, child_tool_info=[{"name": "invented.homology", "resources": "hpc"}])
    with pytest.raises(ContractError, match="completed_revision_required"):
        commission(case, revision={"status": "failed", "result": None})


def test_multirecord_file_requires_the_explicit_selected_subject(tmp_path):
    path = tmp_path / "supplied.fa"
    path.write_text(">first\nMARGKKIGYS\n>second\nMACDEFGHIKLMN\n")
    with Store(tmp_path / "state") as store:
        first, second = store.create_problem(path, molecule="protein")["subject_refs"]
        run = tmp_path / "run"
        prepare_scientific_binding(episode_type=ScientificProcessEpisode, run_directory=run, source_directory=PUBLICATION,
            tool_catalog=ToolRegistry(store).catalog(), child_roles=("scientific_process",))
        selected = A101Subtree(run).commission(store, target_ref=second,
            scope={"subject_refs": [second]}, completeness="fragment", child_tool_info=[],
            question="Investigate only the explicitly selected second record.")
        assert selected["assignment"]["context"]["a101_material"]["supplied_length"] == 13
        assert first not in selected["assignment"]["evidence_refs"]
