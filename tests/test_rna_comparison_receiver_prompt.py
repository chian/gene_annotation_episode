"""Annotation/legacy parent text from selected synthetic RNA comparison returns.

These check the receiving text boundary; they do not run a model or RNA tool.
"""
from copy import deepcopy
import builtins
import importlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.decision_context import INSTRUCTIONS as EXCHANGE_INSTRUCTIONS
from gene_annotation_episode.rna_structure_comparison_views import (
    PROJECTION_SOURCE, rna_comparison_fact_sources,
)
from gene_annotation_episode.rna_structure_comparison_presentation import render_rna_comparison_projections
from gene_annotation_episode.scientific_process_prompt import text_instructions
import gene_annotation_episode.rna_structure_comparison_receiver_prompt as prompt
from test_rna_comparison_presentation import pair, scan


SUPPLIED_INSTRUCTIONS = (
    "Determine what the supplied segment supports about a functional annotation. "
    "Begin with its supplied sequence and selected file excerpt; a candidate name is not required. "
    "Compare competing explanations, keep measured facts separate from interpretation, and choose "
    "the next permitted child or reasoning action from actual outcomes. Keep the original segment "
    "boundaries and caller constraints. The configured controller owns continuation."
)
CHILD_OPTIONS = (
    "A scientific_process child receives a narrower objective, the fixed subject scope, constraints, "
    "selected evidence-axis/thought/tool choices and a closed typed return form. It owns subsequent "
    "iterative choices. Choose a results child only with an available retained-input handoff and "
    "its explicitly requested comparison fields."
)
LIFECYCLE = "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment."


def root_state(rows=()):
    """Controlled shape from DecisionSource.next and EpisodeGoal.root."""
    return {
        "goal": {"goal_id": "HOST_GOAL", "parent_goal_id": "HOST_PARENT",
            "objective": "Determine an evidence-grounded annotation for segment Q.",
            "task_context": {
                "root_objective": "Determine an evidence-grounded annotation for segment Q.",
                "root_result_contract": {"role": "annotation"},
                "caller_context": "Q is a supplied RNA segment; no public accession or candidate function was supplied."},
            "result_contract": {"role": "annotation"}},
        "scope": {"subject_refs": ["input_" + "1" * 24], "segments": [
            {"subject_ref": "input_" + "1" * 24, "start": 0, "end": 9}]},
        "selected_constraints": {
            "material": "Use Q and the supplied excerpt only unless a child is explicitly assigned additional acquisition.",
            "local_memory_bytes": 21474836480, "local_scratch_bytes": 4294967296, "wall_seconds": None},
        "working_state": {
            "subjects": [{"id": "input_" + "1" * 24, "name": "Q", "molecule": "RNA",
                "sequence": "GGGAAACCC", "length": 9, "unit": "nt", "record_type": "input",
                "source_ref": "source_" + "3" * 24, "sha256": "HOST_SUBJECT_HASH"}],
            "materials": [{"id": "material_" + "2" * 24, "name": "selected.txt", "use": "context",
                "text": "Supplied excerpt: Q lies between two reported coding regions; their functions are unspecified.",
                "record_type": "material", "created_at": "HOST_MATERIAL_TIME"}],
            "collections": [], "material_links": [], "target_binding": "sequence_targets",
            "read_library_access": [], "supplied_context_source_refs": ["source_" + "3" * 24],
            "sources": [{"id": "source_unused", "text": "UNREQUESTED_SOURCE_BODY"}],
            "observations": [{"id": "observation_unused", "value": "UNREQUESTED_OBSERVATION"}],
            "annotations": [], "interpretation_accounts": []},
        "selected_launch_instructions": {"library_id": "HOST_MANUAL_LIBRARY", "sections": [
            {"entry_id": "rna-models", "section_id": "interpretation", "section_sha256": "HOST_MANUAL_HASH",
                "text": "Keep retained RNA model results qualified by their actual inputs and model compatibility. "
                    "Energy, site correspondence and scan population questions request different return fields."}]},
        "child_options": CHILD_OPTIONS,
        "requested_report_purpose": None, "requested_form": None,
        "available_report_facts": {"unused": {"meaning": "UNREQUESTED_FACT_CATALOG"}},
        "report_lifecycle": LIFECYCLE,
        "received_rna_comparison_values": [{"fact_source": PROJECTION_SOURCE, "facts": deepcopy(list(rows))}],
        "child_reports": [], "current_report_update": {}, "current_report_basis_refs": [],
        "last_local_outcome": None, "feedback": None,
        "action_yields": {"rows": [{"category": "child/results", "completed_actions": 1,
            "total_yield": 0, "attempted_uncompleted": 0, "expected_yield": {
                "status": "unavailable", "unavailable_reason": "insufficient completed actions", "band": None}}]},
        "current_credit": 4, "annotation_score": 2,
        "pending_work": {"items": []},
    }


def legacy_state(rows=(), *, older=False):
    """The two actual scientific_process.decision_context layouts."""
    state = root_state(rows)
    axis_reference = {"version": "scientific_process_option_ref_v1", "library_id": "a" * 64,
        "slot": "annotation_distinction", "option_id": "A01", "entry_sha256": "b" * 64}
    thought_reference = {**axis_reference, "slot": "thought_pattern", "option_id": "P01"}
    tool = {"name": "source.read", "resources": "local", "description": "Read the selected source window.",
        "instructions": "Use source_ref with exact offset and limit.\nRetain the original text and any partial-window qualification."}
    selection = ({"version": "scientific_process_selection_v2", "annotation_ref": axis_reference,
        "thought_ref": thought_reference, "tools": ["source.read"]} if older else
        {"version": "scientific_process_selection_v3", "evidence_axis": axis_reference,
            "thought_pattern": thought_reference, "child_tool_info": [{"name": "source.read", "resources": "local"}]})
    support = {"id": "A01", "name": "Measured activity", "description": "Determine which actual source measurement bears on Q.",
        "support": {"proposition": "A measured molecular activity can inform a candidate role only through its actual subject relationship.",
            "operands": [{"operand_id": "reference_measurement", "observation_kinds": ["enzyme_activity"],
                "hypothesis_predicates": ["has_function"], "assessment_relations": ["supports"],
                "applicabilities": ["indirect"], "extent_bases": ["inferred_extent"],
                "finding_qualifications": ["qualified"], "instruction": "Preserve the source construct and controls before inferring relevance to Q."}],
            "qualifications": ["A changed RNA model energy does not measure the assayed molecular activity."],
            "boundary": "Keep native measurements and function interpretation distinct."}}
    thought = {"id": "P01", "name": "Distinguish plausible functions",
        "description": "Compare the functional explanations using the observations that could distinguish them.",
        "use_when": "The supplied evidence permits more than one interpretation.",
        "live_alternatives": ["Shared molecular activity", "Different substrate recognition"],
        "decision_guidance": ["Request the comparison whose possible outcomes distinguish these alternatives."],
        "outcome_contingencies": [{"if_observed": "A difference occurs only under an unmatched condition",
            "then_consider": "Retain the condition dependence before transferring the functional claim."}],
        "boundary": "Model-energy differences alone do not establish function."}
    state["scientific_process"] = {
        "selection": selection, "initial_selection_sha256": "HOST_SELECTION_HASH",
        "annotation" if older else "evidence_axis": support,
        "thought" if older else "thought_pattern": thought,
        "tools" if older else "child_tool_info": [tool],
        "assignment": {"selection": selection, "constraints": {"candidate_required": False, "fixed_scope": True},
            "context": {"selected_file": "selected.txt", "snippet": "Q sequence: GGGAAACCC", "complete": False},
            "evidence_refs": ["observation_selected"], "revision_origin": {"ignored": "HOST_REVISION"}},
        "permitted_children": ["scientific_process", "results"],
        "annotation_support_routes": {"version": "scientific_support_routes_v1", "status": "unavailable",
            "reason": "annotation_score_unbound", "annotation_binding_sha256": "HOST_BINDING_HASH",
            "projection_version": "HOST_PROJECTION_VERSION", "formula_version": "HOST_FORMULA_VERSION",
            "integration_arithmetic": None, "policy": None, "routes": []},
    }
    state["tools"] = [{"name": "source.read", "description": "Read an exact selected source byte window.",
        "input_schema": {"type": "object", "properties": {"source_ref": {"type": "string"},
            "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1}},
            "required": ["source_ref", "offset", "limit"], "additionalProperties": False}}]
    state["goal"]["objective"] = "Determine which received measurements distinguish plausible functions of Q."
    return state


def task_and_steering(state, *, instructions=SUPPLIED_INSTRUCTIONS, lookup_results=()):
    text = prompt.render_rna_comparison_receiver_prompt(state, instructions, lookup_results=lookup_results)
    assert text.startswith("TASK\n\n") and text.count("\n\nSTEERING\n") == 1
    return text.split("\n\nSTEERING\n", 1)


@pytest.mark.parametrize("context_kind", ["root", "current_legacy", "older_legacy"])
@pytest.mark.parametrize("family_index", range(8))
def test_question_specific_received_family_preserves_its_parent_task(pair, scan, context_kind, family_index):
    row = (pair + scan)[family_index]
    state = (root_state([row]) if context_kind == "root" else
        legacy_state([row], older=context_kind == "older_legacy"))
    before = deepcopy(state)
    task, steering = task_and_steering(state)
    assert SUPPLIED_INSTRUCTIONS in task
    assert state["goal"]["objective"] in task and state["goal"]["task_context"]["root_objective"] in task
    assert state["selected_constraints"]["material"] in task
    assert "21474836480" in task and "4294967296" in task and "wall_seconds | null" in task
    assert "GGGAAACCC" in task and state["working_state"]["materials"][0]["text"] in task
    assert CHILD_OPTIONS in task
    assert state["selected_launch_instructions"]["sections"][0]["text"] in task
    assert LIFECYCLE in task
    expected = render_rna_comparison_projections([row])
    assert expected in steering and expected not in task
    assert steering.count("Requested RNA ") == 1
    assert "| child/results | 1 | 0 | unavailable | insufficient completed actions | 0 |" in steering
    for hidden in ("HOST_GOAL", "HOST_PARENT", "HOST_SUBJECT_HASH", "HOST_MATERIAL_TIME", "HOST_MANUAL_LIBRARY",
            "HOST_MANUAL_HASH", "UNREQUESTED_SOURCE_BODY", "UNREQUESTED_OBSERVATION", "UNREQUESTED_FACT_CATALOG",
            row["result_receipt_key"], row["calculation_key"]):
        assert hidden not in task + steering
    if context_kind == "root":
        assert "scientific_process" not in state and "tools" not in state
        assert "Selected tool:" not in task and "Callable operations" not in task
        assert "Supplied investigation guidance" not in task and "published_investigation" not in task
    if row["family"] != "structures":
        assert "(((...)))" not in steering and "GGGAAAUCC" not in steering
    if row["family"] == "energy_comparison":
        assert "energy delta | -1.0 | kcal/mol" in steering and "variant lower" in steering
    if row["family"] == "structures":
        assert "| WT | Original sequence | GGGAAACCC |" in steering
        assert "| V | Dot-bracket | ((.....)) |" in steering
        assert "kcal/mol" not in steering
    if row["family"] == "scan_energy":
        assert "baseline rank start | 2" in steering and "baseline rank end | 3" in steering
        assert "| rank population count | 4 |" in steering
        assert "Selected member" not in steering and "native minimum free energy" not in steering
    assert state == before


@pytest.mark.parametrize("older", [False, True])
def test_all_actual_legacy_guidance_and_callable_operands_remain_complete(pair, older):
    state = legacy_state([pair[0]], older=older)
    process = state["scientific_process"]
    axis, thought = process["annotation" if older else "evidence_axis"], process["thought" if older else "thought_pattern"]
    task, steering = task_and_steering(state)
    for value in (axis["description"], axis["support"]["proposition"], axis["support"]["operands"][0]["instruction"],
            *axis["support"]["qualifications"], axis["support"]["boundary"], thought["description"], thought["use_when"],
            *thought["live_alternatives"], *thought["decision_guidance"], thought["boundary"],
            *thought["outcome_contingencies"][0].values()):
        assert value in task
    assert process["tools" if older else "child_tool_info"][0]["instructions"] in task
    assert "reference_measurement" in task and "arguments.source_ref" in task and "arguments.limit" in task
    assert "Q sequence: GGGAAACCC" in task and "candidate_required | false" in task
    assert "observation_selected" in task and "annotation_score_unbound" in task
    assert "a" * 64 in task and "b" * 64 in task
    for hidden in ("HOST_SELECTION_HASH", "HOST_REVISION", "HOST_BINDING_HASH", "HOST_PROJECTION_VERSION", "HOST_FORMULA_VERSION"):
        assert hidden not in task + steering
    assert "published_investigation_instructions" not in task


def test_limited_existing_guidance_is_used_as_supplied_without_published_fallback(pair):
    state = legacy_state([pair[0]])
    supplied = "Start with the supplied segment.\n" + "Preserve the measured subject and the stated comparison limits. " * 160
    state["scientific_process"]["evidence_axis"] = {
        "id": "A03", "name": "Existing measurement guidance",
        "instruction_status": "limited_existing_measurement_guidance", "investigation_instructions": supplied}
    task, _ = task_and_steering(state)
    assert supplied in task and "published_investigation_instructions" not in task
    assert "A measured molecular activity" not in task


def test_full_task_repeats_before_first_return_after_update_and_same_decision_lookup(pair):
    first = root_state()
    first["received_rna_comparison_values"] = []
    second = root_state([pair[0]])
    second["feedback"] = {"code": "further_structural_information_not_requested"}
    before = deepcopy((first, second))
    first_task, first_steering = task_and_steering(first)
    second_task, second_steering = task_and_steering(second)
    lookup_task, lookup_steering = task_and_steering(second, lookup_results=[{
        "status": "completed", "result": [deepcopy(pair[1])]}])
    assert first_task == second_task == lookup_task
    assert "Requested RNA " not in first_steering
    assert "further_structural_information_not_requested" in second_steering
    assert lookup_steering.count("Requested RNA structures") == 1
    assert lookup_steering.count("Requested RNA energy comparison") == 1
    assert (first, second) == before


def test_actual_runtime_instructions_retain_full_recurring_task(pair):
    from gene_annotation_episode.runtime import INSTRUCTIONS as RUNTIME_INSTRUCTIONS
    supplied = RUNTIME_INSTRUCTIONS + "\n" + EXCHANGE_INSTRUCTIONS
    task, _ = task_and_steering(root_state([pair[0]]), instructions=supplied)
    assert text_instructions(supplied) in task
    assert "Different wording" not in task
    assert "request_context" in task and "select_action" in task
    assert "decision_bootstrap supplies" not in task


def test_mixed_returns_exact_duplicates_and_interpretations_keep_their_owners(pair):
    state = root_state([pair[0]])
    state["child_reports"] = [{"caller_energy": [deepcopy(pair[0])], "quality": "qualified",
        "mixed": [deepcopy(pair[0]), {"unrelated_fraction": -0.125}]},
        {"second_caller_field": [deepcopy(pair[0])], "completed": True}]
    state["current_report_update"] = {"interpretation": "Functional assignment unresolved", "limits": ["Model prediction only"]}
    before = deepcopy(state)
    task, steering = task_and_steering(state)
    assert steering.count("Requested RNA energy comparison") == 1
    assert "| [0].quality | qualified |" in steering
    assert "| [0].mixed[0].unrelated_fraction | -0.125 |" in steering
    assert "| [1].completed | true |" in steering
    assert "Functional assignment unresolved" in steering and "Model prediction only" in steering
    assert "Functional assignment unresolved" not in task
    assert state == before


def test_requested_return_retains_parent_names_constraints_and_only_requested_source_meanings(pair):
    state = legacy_state([pair[0]])
    source = rna_comparison_fact_sources()[PROJECTION_SOURCE]
    state["requested_report_purpose"] = "Return the requested comparison facts and the constrained functional interpretation."
    state["available_report_facts"].update({PROJECTION_SOURCE: source,
        "changed_record_refs": {"meaning": "Actual changed semantic records from completed work."}})
    form = {"type": "object", "additionalProperties": False, "required": ["parent_chosen_name", "interpretation", "records"],
        "properties": {"parent_chosen_name": deepcopy(source["report_schema"]),
            "interpretation": {"type": "string", "enum": ["unresolved", "qualified"],
                "description": "Current interpretation of possible function, with its limited scope."},
            "records": {"type": "array", "items": {"type": "string", "format": "reference"}, "x-source": "changed_record_refs"}}}
    state["requested_form"] = form
    state["goal"]["result_contract"] = deepcopy(form)
    before = deepcopy(state)
    task, _ = task_and_steering(state)
    assert "return.parent_chosen_name" in task
    assert task.count("Automatically supplied requested RNA comparison facts") == 1
    assert "The parent return form below is this goal's result contract." in task
    assert "Current interpretation of possible function, with its limited scope." in task
    assert "unresolved" in task and "qualified" in task and "additionalProperties | false" in task
    assert "Actual changed semantic records from completed work." in task
    assert "result_receipt_key" not in task and "input_paths" not in task and "oneOf" not in task
    assert "UNREQUESTED_FACT_CATALOG" not in task
    assert state == before


def test_distinct_goal_schema_and_parent_form_keep_both_actual_meanings(pair):
    state = root_state([pair[0]])
    state["goal"]["result_contract"] = {"type": "object", "additionalProperties": False,
        "properties": {"annotation_state": {"type": "string", "enum": ["open", "qualified"]}},
        "required": ["annotation_state"]}
    task, _ = task_and_steering(state)
    assert "return.annotation_state" in task and "open" in task
    assert "Absent: no parent return form was supplied." in task


def test_selected_material_long_strings_are_not_clipped_or_replaced(pair):
    state = root_state([pair[0]])
    sequence = "gGGAAAcCC" * 300
    excerpt = "Supplied context with original case and literal boundaries. " * 240
    state["working_state"]["subjects"][0]["sequence"] = sequence
    state["working_state"]["materials"][0]["text"] = excerpt
    task, _ = task_and_steering(state)
    assert sequence in task and excerpt in task


def test_pure_receiver_does_not_read_hidden_data_calculate_or_invoke_work(pair, monkeypatch):
    state = legacy_state([pair[0]])
    before = deepcopy(state)
    calculations = importlib.import_module("gene_annotation_episode.rna_structure_comparison_calculations")
    views = importlib.import_module("gene_annotation_episode.rna_structure_comparison_views")
    from gene_annotation_episode.state import Store
    def forbidden(*args, **kwargs):
        raise AssertionError("renderer attempted acquisition, calculation, or execution")
    with monkeypatch.context() as patch:
        for target, names in ((builtins, ["open"]), (Path, ["open", "read_text", "read_bytes"]),
                (socket, ["socket", "create_connection"]), (subprocess, ["run", "Popen"]),
                (Store, ["get", "read_snapshot"]),
                (calculations, ["calculate_rna_comparison_components"]), (views, ["project_rna_comparison"])):
            for name in names:
                patch.setattr(target, name, forbidden)
        task, steering = task_and_steering(state)
    assert "Determine which received measurements" in task and "energy delta | -1.0" in steering
    assert state == before


def test_unknown_counts_and_scoped_qualifications_remain_received_facts(scan):
    row = deepcopy(scan[0])
    row["qualification"]["population"]["model_unknown_variant_count"] = None
    row["qualification"]["codes"].append("native_model_missing")
    task, steering = task_and_steering(root_state([row]))
    assert "| model unknown variant count | unavailable |" in steering
    assert "Additional input qualifications (member scope not supplied):" in steering
    assert "baseline rank start | 2" in steering
    assert "native model missing" not in task


def test_record_complete_synthetic_receiver_examples(tmp_path, pair, scan):
    examples = {
        "ROOT_ENERGY": root_state([pair[0]]),
        "ROOT_TWO_STRUCTURES": root_state([pair[1]]),
        "ROOT_SELECTED_SITES": root_state([pair[2]]),
        "ROOT_COMPACT_SCAN": root_state([scan[0]]),
        "LEGACY_CURRENT_SLOTS": legacy_state([pair[0]]),
        "LEGACY_OLDER_SLOTS": legacy_state([pair[0]], older=True),
    }
    for name, state in examples.items():
        text = prompt.render_rna_comparison_receiver_prompt(state, SUPPLIED_INSTRUCTIONS)
        assert text.startswith("TASK\n\n") and text.count("\n\nSTEERING\n") == 1
        (tmp_path / (name + "_TASK_STEERING.txt")).write_text(text + "\n")
        (tmp_path / (name + "_SUPPLIED_STATE.json")).write_text(json.dumps(state, indent=2) + "\n")
