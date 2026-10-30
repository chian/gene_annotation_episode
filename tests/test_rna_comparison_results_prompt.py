"""Retained RESULTS text from synthetic assignments/facts; no native/model run."""
from copy import deepcopy
import builtins
import importlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.rna_structure_comparison_contracts import SELECTOR_VERSION, SITE_TRANSITIONS
from gene_annotation_episode.rna_structure_comparison_presentation import render_rna_comparison_projections
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE, rna_comparison_fact_sources
import gene_annotation_episode.rna_structure_comparison_prompt as prompt
from test_rna_comparison_presentation import request, project, receipt


f = importlib.import_module("verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")
PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_rna_results_text_2026-10-27_381"


def assignment(sheet, projections):
    return {"version": "execution_results_assignment_v1", "handoff_ref": "hidden-routing-anchor",
        "selector": {"version": SELECTOR_VERSION, "acquisition": "retained_inputs_only",
            "question": deepcopy(sheet["selected_question"]), "parameters": deepcopy(sheet["parameters"]),
            "projections": deepcopy(projections)}}


def requested_form():
    return {"type": "object", "additionalProperties": False, "properties": {
        "the_parent_chosen_answer": {**rna_comparison_fact_sources()[PROJECTION_SOURCE]["report_schema"],
            "description": "WT rank and gap for the selected population."},
        "conclusion": {"type": "string", "enum": ["lowest", "not_lowest", "unresolved"],
            "description": "Interpret only the comparable supplied population."},
        "basis": {"type": "array", "items": {"type": "integer", "minimum": 0},
            "minItems": 1, "maxItems": 3, "uniqueItems": True},
        "other_measurement": {"type": "number", "x-source": "other_measurement", "description": "Recorded unrelated measurement."},
    }, "required": ["the_parent_chosen_answer", "conclusion", "basis", "other_measurement"]}


def decision_state(sheet, choices, rows=()):
    return {"execution_assignment": assignment(sheet, choices),
        "execution_progress": {PROJECTION_SOURCE: deepcopy(list(rows)), "execution_completed": False},
        "goal": {"objective": "Return the parent's selected retained comparison.",
            "task_context": {"constraint": "Keep the supplied baseline and finite population fixed."},
            "result_contract": {"role": "results"}, "host_id": "HIDDEN_GOAL_TRACKING"},
        "scope": {"subject_refs": ["selected_subject"]},
        "requested_report_purpose": "Return WT's qualified rank, ties and energy gap for this declared scan.",
        "requested_form": requested_form(),
        "available_report_facts": {**rna_comparison_fact_sources(), "other_measurement": {
            "meaning": "Measured signal in the unrelated supplied molecular assay."},
            "unselected_source": {"meaning": "HIDDEN_UNUSED_SOURCE_CATALOG"}},
        "report_lifecycle": "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.",
        "action_yields": {"rows": [{"category": "tool/execution.results.status", "completed_actions": 1,
            "total_yield": 0, "attempted_uncompleted": 0, "expected_yield": {"status": "unavailable",
                "band": None, "unavailable_reason": "insufficient completed actions"}}]},
        "current_report_update": {"conclusion": "unresolved", "basis": [0]},
        "execution_target_description": {"producer_path": "/hidden/producer", "sha256": "HIDDEN_DESCRIPTOR_HASH"}}


@pytest.fixture(scope="module")
def pair_sheet():
    return f.pair(f.feature(energy=-4.0), f.feature("V", "GGGAAAUCC", "((.....))", energy=-5.0),
        selections=[f.site(positions=[0, 6])], energy=f.energy_request())


@pytest.fixture(scope="module")
def scan_sheet():
    return f.scan(extra_members=[f.absent("missing", "not_supplied"), f.absent("untested")],
        extra_operands={"missing": f.blank(), "untested": f.blank()})


def render(state):
    instructions = prompt.rna_comparison_results_instructions(state["execution_assignment"])
    return prompt.render_rna_comparison_results_prompt(state, instructions)


def assert_no_tracking(text):
    for hidden in ("HIDDEN_", "hidden-routing-anchor", "/hidden/", "sheet_sha256", "result_receipt_key",
            "calculation_key", "input_paths", "selected_input_digests", "rna_comparison_projection_v1",
            "bundle_artifact_ref", "handoff-WT", "source-WT", "sheet-WT"):
        assert hidden not in text


@pytest.mark.parametrize("family", ["energy_comparison", "structures", "position_changes", "pair_changes", "comparison_counts"])
def test_pair_task_and_supplied_steering_keep_exact_selected_outputs(pair_sheet, family):
    chosen = request(family)
    rows = project(pair_sheet, [chosen])
    state = decision_state(pair_sheet, [chosen], rows)
    before = deepcopy(state)
    text = render(state)
    task, steering = text.split("\n\nSTEERING\n", 1)
    assert task.startswith("TASK\n")
    assert "explicit baseline WT" in task and "pairwise comparison with V" in task
    assert "Keep the parent's baseline" in task and "20 GiB memory and 4 GiB scratch" in task
    assert "no wall-time budget" in task and "no operation order is prescribed" in task
    assert "recorded facts are populated automatically" in task
    assert steering.count(render_rna_comparison_projections(rows)) == 1
    assert "| tool/execution.results.status | 1 | 0 | unavailable | insufficient completed actions | 0 |" in steering
    assert state == before
    assert_no_tracking(text)
    if family == "structures":
        assert "original sequence (complete, preserving original case)" in task
        assert "| WT | Dot-bracket | (((...))) |" in steering
        assert "| V | Dot-bracket | ((.....)) |" in steering
        assert "energy delta" not in steering
    else:
        assert "(((...)))" not in text and "GGGAAAUCC" not in text
    if family == "energy_comparison":
        assert "native evaluated structure energy; no per-nucleotide normalization" in task
        assert "signed energy difference (variant minus baseline)" in task
        assert "include_tolerance_band" not in text
    if family == "position_changes":
        assert "2 explicit position selectors" in task
        assert "2 declared substitutions" not in task
        assert "index 6: C to U" in task
        assert "null" not in steering or "unavailable" in steering
        assert "unpaired | lost pairing | 1" in steering


def test_scan_task_summarizes_declared_population_and_does_not_dump_members(scan_sheet, tmp_path):
    choice = request("scan_energy", metrics=["baseline_rank_start", "baseline_rank_end", "baseline_tie_count",
        "lowest_energy_tie_count", "baseline_selected_energy", "minimum_selected_energy", "baseline_energy_above_minimum"])
    state = decision_state(scan_sheet, [choice], project(scan_sheet, [choice]))
    text = render(state)
    task, steering = text.split("\n\nSTEERING\n", 1)
    assert "finite scan scan" in task and "explicit baseline WT" in task
    assert "| All declared entries, including baseline and aliases | 8 |" in task
    assert "| Retained saved inputs | 4 |" in task and "| Received failures | 1 |" in task
    assert "| Not supplied | 1 |" in task and "| Not tested | 1 |" in task
    assert "| Aliases, with no additional rank weight | 1 |" in task
    assert "6 baseline-to-canonical-variant comparisons" in task
    assert "compare-A" not in task and "AliasA" not in task and "untested" not in task
    assert "baseline rank start (first occupied exact rank)" in task
    assert "baseline tie count (including the baseline)" in task
    assert "do not establish a global optimum" in task
    assert "rank population count | 4" in steering
    assert "baseline rank start | 2" in steering and "baseline rank end | 3" in steering
    assert "baseline energy above minimum | 1.0 | kcal/mol" in steering
    assert "Selected member" not in text and "(((" not in text
    assert_no_tracking(text)
    (tmp_path / "FILLED_SCAN_TASK_STEERING_SYNTHETIC.txt").write_text(text + "\n")
    (tmp_path / "FILLED_SCAN_STATE_SYNTHETIC.json").write_text(json.dumps(state, indent=2) + "\n")


@pytest.mark.parametrize("kind", ["native_mfe", "native_evaluation"])
@pytest.mark.parametrize("normalization", ["none", "per_nt"])
def test_energy_policy_uses_actual_selected_kind_normalization_and_tolerance(pair_sheet, kind, normalization):
    selected = assignment(pair_sheet, [request("energy_comparison")])
    energy = selected["selector"]["question"]["comparisons"][0]["energy"]
    energy.update(quantity=kind, normalization=normalization, baseline_absolute_tolerance=0)
    text = prompt.rna_comparison_results_instructions(selected)
    assert prompt._name(kind) + "; " in text
    assert ("no per-nucleotide normalization; kcal/mol" if normalization == "none" else "own sequence length; kcal/mol/nt") in text
    assert "absolute baseline tolerance 0 in the selected energy unit" in text
    assert "tolerance is not an uncertainty interval" in text


@pytest.mark.parametrize("correspondence,expected", [
    (None, "equal integer indices do not establish correspondence"),
    ({"kind": "identical_sequence"}, "validated against both retained sequences"),
    (f.complete([(None, 0), (0, 1)]), "2 supplied complete alignment columns"),
    (f.partial([(0, 0)]), "unlisted positions remain unknown"),
])
def test_correspondence_meanings_are_selected_not_inferred(pair_sheet, correspondence, expected):
    selected = assignment(pair_sheet, [request("position_changes")])
    selected["selector"]["question"]["comparisons"][0]["correspondence"] = correspondence
    assert expected in prompt.rna_comparison_results_instructions(selected)


def test_site_only_task_has_no_automatic_energy_or_structures(pair_sheet):
    selected = assignment(pair_sheet, [request("position_changes")])
    comparison = selected["selector"]["question"]["comparisons"][0]
    comparison["energy"] = None
    comparison["calculate_pair_changes"] = False
    comparison["site_selections"] = [f.site(positions=[6])]
    text = prompt.rna_comparison_results_instructions(selected)
    assert "one explicit position, index 6" in text
    assert "No energy comparison requested." in text
    assert "native minimum-free-energy prediction" not in text and "kcal/mol" not in text
    assert "dot-bracket structure (complete original string)" not in text
    assert "Sequence indices are zero based" in text
    assert "unpaired, supplied gap, unmapped" in text.lower()


def test_scan_sites_and_explicit_member_window_describe_the_requested_question(scan_sheet):
    selected = assignment(scan_sheet, [request("scan_members", members={"kind": "exceptions", "predicates": ["model_unknown", "received_failure"]}, limit=2)])
    text = prompt.rna_comparison_results_instructions(selected)
    assert "members matching any selected predicate: model unknown; received failure" in text
    assert "at most 2 matching selected members" in text
    assert "not native truncation" in text
    assert "complete original string" not in text
    for comparison in selected["selector"]["question"]["comparisons"]:
        comparison["site_selections"] = [f.site(positions=list(range(500)))]
        comparison["energy"] = None
    selected["selector"]["question"]["scan"].update(energy=None, topology_selection_ids=["selected"])
    selected["selector"]["projections"] = [request("scan_sites")]
    text = prompt.rna_comparison_results_instructions(selected)
    assert "500 explicit position selectors" in text
    assert "498; 499" not in text
    assert "changed variant fraction" in text and "each selected baseline site" in text
    assert "Rank the explicit baseline" not in text


def test_parent_form_keeps_field_meanings_and_interpretation_constraints_without_eight_family_schema(pair_sheet):
    state = decision_state(pair_sheet, [request("structures")])
    state["requested_form"]["properties"]["constrained"] = {"anyOf": [
        {"type": "string", "pattern": "^selected_[0-9]+$", "maxLength": 30}, {"type": "null"}]}
    before = deepcopy(state)
    text = prompt.render_rna_comparison_requested_return(state)
    assert "return.the_parent_chosen_answer | required | array" in text
    assert "WT rank and gap for the selected population." in text
    assert "Automatically supplied requested RNA comparison facts" in text
    for value in ("lowest", "not_lowest", "unresolved", "minimum", "maxItems", "uniqueItems", "^selected_[0-9]+$", "maxLength"):
        assert value in text
    assert "Measured signal in the unrelated supplied molecular assay." in text
    assert "recorded fact from other_measurement" in text
    assert "later tool outcomes are facts, not a new judgment" in text
    assert "family" not in text and "payload" not in text
    assert_no_tracking(text)
    assert state == before


@pytest.mark.parametrize("form", [None, "missing"])
def test_absent_parent_form_is_explicit_and_does_not_invent_one(form):
    state = {} if form == "missing" else {"requested_form": form}
    assert prompt.render_rna_comparison_requested_return(state) == "Parent return form\n\nAbsent: no parent return form was supplied."


def test_same_or_distinct_goal_result_schema_uses_compact_parent_meaning(pair_sheet):
    state = decision_state(pair_sheet, [request("structures")])
    state["goal"]["result_contract"] = deepcopy(state["requested_form"])
    text = render(state)
    assert text.count("return.the_parent_chosen_answer | required | array") == 1
    assert_no_tracking(text)
    state["goal"]["result_contract"]["properties"]["conclusion"]["description"] = "Distinct assignment meaning"
    text = render(state)
    assert "Distinct assignment meaning" in text
    assert_no_tracking(text)


def test_status_failure_delivery_and_own_history_are_separate(pair_sheet):
    issue = {"stage": "input", "code": "retained_sheet_missing", "member_id": "V",
        "comparison_id": None, "selection_id": None, "field": None, "index": None}
    state = decision_state(pair_sheet, [request("energy_comparison")])
    state["last_local_outcome"] = {"status": "completed", "record_refs": [], "changed_record_refs": [],
        "result": receipt([], status=True, issues=[issue]), "feedback": None}
    before = deepcopy(state)
    text = render(state)
    assert "| execution.results.status | completed | false |" in text
    assert "member V | input | retained sheet missing" in text
    assert "completed status action does not complete" in text
    assert "exact zero through the existing practical endpoint" in text
    assert "comparison delivery complete" in text
    assert_no_tracking(text)
    assert state == before


def test_missing_baseline_retains_unavailability_and_zero_gap_remains_measured(scan_sheet):
    choice = request("scan_energy", metrics=["baseline_rank_start", "baseline_energy_above_minimum"])
    question = deepcopy(scan_sheet["selected_question"])
    question["membership"][0] = f.absent("WT", "not_supplied")
    operands = {o["member_id"]: {key: deepcopy(o[key]) for key in
        ("original_sheet", "original_bundle_software", "received_failure")}
        for o in scan_sheet["operands"] if o["state"] != "alias"}
    operands["WT"] = f.blank()
    missing = f.rebuild(scan_sheet, operands=operands, question=question)
    text = render(decision_state(missing, [choice], project(missing, [choice])))
    assert "WT: not supplied." in text
    assert "baseline rank start | unavailable" in text
    assert "| rank population count | unavailable |" in text
    assert "| comparable variant count | unavailable |" in text
    tied = f.scan(energies=(-5.0, -5.0, -4.0, -3.0))
    text = render(decision_state(tied, [choice], project(tied, [choice])))
    assert "baseline energy above minimum | 0.0 | kcal/mol | present" in text
    assert "Baseline rank class: tied lowest." in text


def test_incompatible_energy_return_keeps_raw_values_and_unavailable_difference(pair_sheet):
    sheet = f.pair(f.feature(energy=-4.0), f.feature("V", "GGGAAAUCC", energy=-6.0, temperature=25.0),
        selections=[], pairs=False, correspondence=None, energy=f.energy_request())
    choice = request("energy_comparison")
    text = render(decision_state(sheet, [choice], project(sheet, [choice])))
    assert "baseline native energy | -4.0 | kcal/mol | present" in text
    assert "variant native energy | -6.0 | kcal/mol | present" in text
    assert "energy delta | unavailable | kcal/mol | incompatible" in text
    assert "model setting different" in text
    assert "compatibility: incompatible" in text


def test_full_task_recurs_with_lookup_without_duplicating_receipt_rows(pair_sheet):
    choice = request("structures")
    rows = project(pair_sheet, [choice])
    state = decision_state(pair_sheet, [choice], rows)
    state["last_local_outcome"] = {"status": "completed", "result": receipt(rows), "feedback": None,
        "record_refs": [], "changed_record_refs": []}
    instructions = prompt.rna_comparison_results_instructions(state["execution_assignment"])
    ordinary = prompt.render_rna_comparison_results_prompt(state, instructions)
    continued = prompt.render_rna_comparison_results_prompt(state, instructions,
        lookup_results=[{"view": "own_attempts", "records": [], "total": 0, "offset": 0, "returned_count": 0}])
    assert ordinary.split("\n\nSTEERING\n")[0] == continued.split("\n\nSTEERING\n")[0]
    assert ordinary.count(render_rna_comparison_projections(rows)) == 1
    assert continued.count(render_rna_comparison_projections(rows)) == 1
    assert "Requested information; continue the same decision" in continued
    assert instructions in ordinary
    assert_no_tracking(continued)


def test_rendering_needs_no_store_file_network_native_or_calculator(pair_sheet, monkeypatch):
    choice = request("structures")
    state = decision_state(pair_sheet, [choice], project(pair_sheet, [choice]))
    before = deepcopy(state)
    def forbidden(*args, **kwargs):
        raise AssertionError("Presentation crossed a side-effect/calculation boundary")
    calculations = importlib.import_module("gene_annotation_episode.rna_structure_comparison_calculations")
    inputs = importlib.import_module("gene_annotation_episode.rna_structure_comparison_inputs")
    publication = importlib.import_module("gene_annotation_episode.rna_structure_comparison_publication")
    from gene_annotation_episode.state import Store
    for target, name in [(builtins, "open"), (Path, "read_text"), (Path, "read_bytes"),
            (socket, "socket"), (subprocess, "Popen"), (Store, "get"),
            (calculations, "calculate_rna_comparison_components"), (inputs, "populate_rna_comparison_sheet"),
            (publication, "prepare_rna_comparison_grading")]:
        monkeypatch.setattr(target, name, forbidden)
    assert "Selected RNA comparison facts" in render(state)
    assert state == before


@pytest.mark.parametrize("selector,version", [({}, "execution_results_assignment_v1"),
    ({"version": "native_blast_result_selector_v1"}, "execution_results_assignment_v1"),
    ({"version": SELECTOR_VERSION}, "different_assignment_version")])
def test_other_results_instructions_unchanged(selector, version):
    namespace = {"plain": plain}
    exec((PACKET / "baseline_execution_instructions.txt").read_text(), namespace)
    context = SimpleNamespace(role="results", assignment={"version": version, "selector": selector})
    assert ExecutionEpisodes.instructions(None, context) == namespace["instructions"](None, context)


@pytest.mark.parametrize("role", ["launch", "launch_api", "launch_local", "launch_hpc"])
def test_original_nonresults_instructions_unchanged(role):
    namespace = {"plain": plain}
    exec((PACKET / "baseline_execution_instructions.txt").read_text(), namespace)
    owner = SimpleNamespace(_delegate=lambda _: SimpleNamespace(instructions=lambda _: "Original resource instructions"),
        _validate_request=lambda value: value)
    context = SimpleNamespace(role=role, assignment={"service": "selected_service"})
    assert ExecutionEpisodes.instructions(owner, context) == namespace["instructions"](owner, context)


def test_exact_execution_branch_uses_new_full_instructions_without_observation(pair_sheet):
    selected = assignment(pair_sheet, [request("structures")])
    context = SimpleNamespace(role="results", assignment=selected)
    assert ExecutionEpisodes.instructions(None, context) == prompt.rna_comparison_results_instructions(selected)
    assert "Acquire the original selected execution results" not in ExecutionEpisodes.instructions(None, context)


def test_noncomparison_context_is_not_rendered_as_comparison():
    with pytest.raises(ValueError, match="rna_comparison_results_context_required"):
        prompt.render_rna_comparison_results_prompt({"execution_assignment": {"selector": {"version": "old"}}}, "Legacy")
