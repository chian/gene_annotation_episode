"""Question-specific text from synthetic selected RNA returns; no new RNA run."""
from copy import deepcopy
import builtins
import importlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.rna_structure_comparison_calculations import calculate_rna_comparison_components
from gene_annotation_episode.rna_structure_comparison_contracts import PAIR_RELATIONS, SITE_TRANSITIONS, SELECTOR_VERSION
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE, project_rna_comparison
from gene_annotation_episode.rna_structure_comparison_presentation import (
    has_received_rna_comparison_context, is_rna_comparison_results_context,
    render_rna_comparison_lookup, render_rna_comparison_own_outcome,
    render_rna_comparison_projections, select_rna_comparison_presentation,
)

f = importlib.import_module("verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")
KEYS = {"result_receipt_key": "rna_comparison_receipt:" + "1" * 64,
    "calculation_key": "rna_comparison_calculation:" + "2" * 64}


def request(family, **changes):
    options = {
        "energy_comparison": dict(comparison_ids=["compare-V"], metrics=["energy_delta", "baseline_native_energy", "variant_native_energy"],
            include_order=True, include_tolerance_band=False),
        "structures": dict(member_ids=["WT", "V"], fields=["original_sequence", "dot_bracket"]),
        "position_changes": dict(comparison_id="compare-V", selection_id="selected", transitions=list(SITE_TRANSITIONS)),
        "pair_changes": dict(comparison_ids=["compare-V"], relations=list(PAIR_RELATIONS)),
        "comparison_counts": dict(comparison_ids=["compare-V"], selection_ids=["selected"],
            metrics=["changed_site_fraction"], include_pairing_change_state=False),
        "scan_energy": dict(scan_id="scan", metrics=["baseline_rank_start", "baseline_rank_end", "baseline_energy_above_minimum"],
            include_rank_class=True),
        "scan_sites": dict(scan_id="scan", selection_ids=["selected"], metrics=["changed_variant_fraction"]),
        "scan_members": dict(scan_id="scan", members={"kind": "explicit", "member_ids": ["A", "AliasA"]},
            fields=["energy", "rank_start", "eligibility"], order="declared", limit=None),
    }
    return dict(projection_id=family, family=family, **{**options[family], **changes})


def project(sheet, choices):
    return project_rna_comparison(sheet, calculate_rna_comparison_components(sheet), projections=choices, **KEYS)


@pytest.fixture(scope="module")
def pair():
    sheet = f.pair(f.feature(energy=-4.0), f.feature("V", "GGGAAAUCC", "((.....))", energy=-5.0),
        selections=[f.site(positions=[0, 6])], energy=f.energy_request())
    return project(sheet, [request(family) for family in
        ("energy_comparison", "structures", "position_changes", "pair_changes", "comparison_counts")])


@pytest.fixture(scope="module")
def scan():
    sheet = f.scan(failed=False, aliases=True)
    question = deepcopy(sheet["selected_question"])
    originals = {row["member_id"]: row["original_sheet"] for row in sheet["operands"]}
    baseline = originals["WT"]["analysis_sequence"]["analysis_sequence"]
    for comparison in question["comparisons"]:
        sequence = originals[comparison["variant_member_id"]]["analysis_sequence"]["analysis_sequence"]
        comparison["correspondence"] = dict(kind="substitution_only", substitutions=[
            dict(index=i, baseline_symbol=a, variant_symbol=b) for i, (a, b) in enumerate(zip(baseline, sequence)) if a != b])
        comparison["site_selections"] = [f.site(positions=[0, 6])]
    question["scan"]["topology_selection_ids"] = ["selected"]
    return project(f.rebuild(sheet, question=question), [request(name) for name in ("scan_energy", "scan_sites", "scan_members")])


def receiver(rows):
    return {"goal": {"objective": "Annotate the supplied sequence"},
        "received_rna_comparison_values": [{"fact_source": PROJECTION_SOURCE, "facts": deepcopy(rows)}]}


def receipt(rows, *, status=False, issues=(), failure=None):
    return {"version": "rna_structure_comparison_result_receipt_v1", "tool_name":
        "execution.results.status" if status else "execution.results.collect", "projection_rows": deepcopy(rows),
        "delivery_complete": not status and not failure and not issues, "issues": list(issues),
        "preparation_failure": failure, "assignment_digest": "secret-digest", "source_ref": "secret-source",
        "selected_input_digests": [{"path": "/hidden/retained/sheet"}]}


def results_context(rows, **changes):
    return {"execution_assignment": {"version": "execution_results_assignment_v1", "handoff_ref": "hidden-anchor",
                "selector": {"version": SELECTOR_VERSION}},
        "execution_progress": {PROJECTION_SOURCE: deepcopy(rows), "execution_completed": False},
        "last_local_outcome": {"status": "completed", "result": receipt(rows, **changes),
            "record_refs": [], "changed_record_refs": [], "feedback": None}}


@pytest.mark.parametrize("index", range(8))
def test_each_family_renders_without_unrequested_families(pair, scan, index):
    row = (pair + scan)[index]
    before = deepcopy(row)
    text = render_rna_comparison_projections([row])
    assert "Requested RNA " in text
    assert row == before
    for hidden in ("result_receipt_key", "calculation_key", "input_paths", KEYS["result_receipt_key"], KEYS["calculation_key"]):
        assert hidden not in text
    if row["family"] != "structures":
        assert "(((...)))" not in text and "GGGAAACCC" not in text


def test_energy_only_has_signed_difference_and_no_structure(pair):
    text = render_rna_comparison_projections([pair[0]])
    assert "energy delta | -1.0 | kcal/mol" in text
    assert "variant lower" in text and "native evaluated structure energy" in text
    assert "Dot-bracket" not in text and "Base pairs" not in text


def test_two_requested_structures_remain_complete_and_different(pair):
    text = render_rna_comparison_projections([pair[1]])
    assert "| WT | Original sequence | GGGAAACCC |" in text
    assert "| V | Original sequence | GGGAAAUCC |" in text
    assert "| WT | Dot-bracket | (((...))) |" in text
    assert "| V | Dot-bracket | ((.....)) |" in text
    assert "energy delta" not in text and "kcal/mol" not in text


def test_selected_positions_preserve_partner_relationship_and_coordinates(pair):
    text = render_rna_comparison_projections([pair[2]])
    assert "Sequence indices and alignment columns are separate" in text
    assert "| C | 6 | U | 6 | 6 | mapped; local index 2; counterpart index 2; alignment column 2 | unpaired | lost pairing | 1" in text
    assert "| G | 0 | G | 0 | 0 | mapped; local index 8; counterpart index 8; alignment column 8" in text
    assert "| requested site count | 2 |" in text
    assert "biological importance" not in text


def test_scan_rank_is_aggregate_and_does_not_guess_energy_kind(scan):
    text = render_rna_comparison_projections([scan[0]])
    assert "baseline rank start | 2" in text and "baseline rank end | 3" in text
    assert "baseline energy above minimum | 1.0 | kcal/mol" in text
    assert "| rank population count | 4 |" in text
    assert "native minimum free energy" not in text
    assert "Selected member" not in text and "AliasA" not in text
    assert "| alias entry count | 1 |" in text
    assert "Numerator" not in text and "Denominator" not in text


def test_scan_sites_and_explicit_members_retain_different_populations(scan):
    sites = render_rna_comparison_projections([scan[1]])
    members = render_rna_comparison_projections([scan[2]])
    assert "Baseline index 6" in sites and "Denominator" in sites
    assert "changed variant fraction | 0.0 | fraction | 0 | 3 |" in sites
    assert "Selected member" not in sites and "GGG" not in sites
    assert "Selected member AliasA; alias of A" in members
    assert "| 2 | 2 | 0 |" in members


def test_unknown_population_count_stays_unavailable_without_inventing_coordinates(pair, scan):
    row = deepcopy(scan[0]); row["qualification"]["population"]["model_unknown_variant_count"] = None
    text = render_rna_comparison_projections([row])
    assert "| model unknown variant count | unavailable |" in text
    counts = render_rna_comparison_projections([pair[4]])
    assert "Baseline index" not in counts and "unchanged" not in counts
    assert "changed site fraction | 0.5 | fraction | 1 | 2 |" in counts


def test_aggregate_model_issue_is_not_applied_to_every_ranked_member(scan):
    row = deepcopy(scan[0]); row["qualification"]["codes"].append("native_model_missing")
    text = render_rna_comparison_projections([row])
    assert "| model unknown variant count | 0 |" in text and "baseline rank start | 2" in text
    assert "Additional input qualifications (member scope not supplied):" in text
    assert "native model missing" in text
    assert "Baseline rank class: unavailable" not in text


def test_invalid_original_structure_retains_original_text_and_invalid_state():
    sheet = f.pair(f.feature(structure="(((...))"), correspondence=None, pairs=False, selections=[])
    rows = project(sheet, [request("structures", member_ids=["WT"], fields=["dot_bracket", "pairs"])])
    text = render_rna_comparison_projections(rows)
    assert "(((...))" in text and "invalid input: original topology invalid" in text
    assert "Base pairs | unavailable" in text


def test_receiver_removes_only_exact_direct_duplicates_and_keeps_interpretation(pair):
    state = receiver([pair[0]])
    different = deepcopy(pair[0]); different["calculation_key"] = "rna_comparison_calculation:" + "3" * 64
    state["child_reports"] = [{"arbitrary_name": [deepcopy(pair[0]), {"unrelated": 42}], "other": False},
        {"another_name": [deepcopy(pair[0])]}, {"different_calculation": [different]},
        {"nested": {"keep": [deepcopy(pair[0])]}}]
    state["current_report_update"] = {"interpretation": "retain literally", "nested": deepcopy(pair[0])}
    before = deepcopy(state)
    selected = select_rna_comparison_presentation(state)
    assert state == before and selected["projections"] == [pair[0]]
    assert selected["context"]["child_reports"] == [
        {"arbitrary_name": [{"unrelated": 42}], "other": False},
        {"different_calculation": [different]}, {"nested": {"keep": [pair[0]]}}]
    assert selected["context"]["current_report_update"] == state["current_report_update"]
    assert "received_rna_comparison_values" not in selected["context"]


def test_different_calculation_identities_are_not_deduplicated_by_equal_numbers(pair):
    other = deepcopy(pair[0]); other["calculation_key"] = "rna_comparison_calculation:" + "3" * 64
    selected = select_rna_comparison_presentation(receiver([pair[0], pair[0], other]))
    assert selected["projections"] == [pair[0], other]
    assert render_rna_comparison_projections(selected["projections"]).count("Requested RNA energy comparison") == 2


def test_results_progress_and_own_receipt_display_once_without_tracking(pair):
    state = results_context([pair[0]])
    state["last_local_outcome"]["feedback"] = {"keep": "supplied feedback"}
    before = deepcopy(state)
    selected = select_rna_comparison_presentation(state)
    assert state == before and selected["projections"] == [pair[0]]
    assert selected["context"]["last_local_outcome"] == {"feedback": {"keep": "supplied feedback"}}
    assert PROJECTION_SOURCE not in selected["context"]["execution_progress"]
    text = render_rna_comparison_own_outcome(selected["own_outcome"])
    assert "| execution.results.collect | completed | true |" in text
    assert "secret" not in text and "hidden" not in text


def test_successful_status_is_not_comparison_completion():
    issue = dict(stage="input", code="retained_sheet_missing", member_id="V", comparison_id=None,
        selection_id=None, field="/operands/1", index=None)
    selected = select_rna_comparison_presentation(results_context([], status=True, issues=[issue]))
    text = render_rna_comparison_own_outcome(selected["own_outcome"])
    assert "| execution.results.status | completed | false |" in text
    assert "member V | input | retained sheet missing" in text
    assert "/operands/1" not in text and selected["projections"] == []


def test_lookup_recognizes_exact_boundaries_but_does_not_search_nested_content(pair):
    assert "energy delta | -1.0" in render_rna_comparison_lookup({"result": [pair[0]]})
    assert "energy delta | -1.0" in render_rna_comparison_lookup(pair[0])
    text = render_rna_comparison_lookup({"status": "completed", "result": receipt([pair[0]])})
    assert "execution.results.collect" in text and "secret" not in text
    assert render_rna_comparison_lookup({"view": "own_attempt_detail", "values": [pair[0]]}) is None
    assert render_rna_comparison_lookup({"something": {"result": [pair[0]]}}) is None


def test_empty_or_unrelated_context_does_not_claim_prompt_ownership():
    for state in (None, {}, receiver([]), {"received_rna_comparison_values": [{"fact_source": "other", "facts": [1]}]}):
        assert not has_received_rna_comparison_context(state)
        assert not is_rna_comparison_results_context(state)
    unrelated = {"current_report_update": {"keep": 1}, "last_local_outcome": {"result": {"other": 2}}}
    assert select_rna_comparison_presentation(unrelated)["context"] == unrelated
    assert is_rna_comparison_results_context(results_context([]))


@pytest.mark.parametrize("change", [lambda r: r.update(unrequested="wrong"),
    lambda r: r["payload"]["rows"][0]["measurements"][0].update(value=float("nan")),
    lambda r: r["payload"]["rows"][0]["measurements"][0].update(value=True)])
def test_malformed_projection_is_not_silently_rendered(pair, change):
    row = deepcopy(pair[0]); change(row)
    with pytest.raises(ValueError, match="rna_comparison_projection_shape_invalid"):
        render_rna_comparison_projections([row])


def test_rendering_requires_no_hidden_io_calculation_or_mutation(pair, scan, monkeypatch):
    state = receiver(pair + scan)
    before = json.dumps(state, sort_keys=True)
    def forbidden(*args, **kwargs):
        raise AssertionError("presentation cannot acquire or calculate")
    for owner, name in ((builtins, "open"), (Path, "read_text"), (Path, "read_bytes"),
            (socket, "create_connection"), (subprocess, "run"), (subprocess, "Popen")):
        monkeypatch.setattr(owner, name, forbidden)
    module = importlib.import_module("gene_annotation_episode.rna_structure_comparison_calculations")
    monkeypatch.setattr(module, "calculate_rna_comparison_components", forbidden)
    selected = select_rna_comparison_presentation(state)
    text = render_rna_comparison_projections(selected["projections"])
    assert len(text) > 100 and json.dumps(state, sort_keys=True) == before


def test_retained_workflow_scan_return_renders_without_expanding_inputs(tmp_path):
    path = Path(__file__).resolve().parents[1] / (
        "verification/tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_SCAN_001.json")
    example = json.loads(path.read_text())
    case = example["workflow_case"]
    rows = case["returned"]["comparison"]
    assert rows == case["body"]["projection_rows"]
    state = receiver(rows)
    state["child_reports"] = [deepcopy(case["returned"])]
    selected = select_rna_comparison_presentation(state)
    text = render_rna_comparison_projections(selected["projections"])
    assert selected["context"]["child_reports"] == [{"completed": True}]
    assert text.count("Requested RNA scan energy") == 1
    assert "baseline rank start | 2" in text and "baseline rank end | 3" in text
    assert "baseline energy above minimum | 1.0 | kcal/mol" in text
    assert "| received failure variant count | 1 |" in text
    assert "| not supplied variant count | 1 |" in text and "| not tested variant count | 1 |" in text
    assert "| rank population count | 4 |" in text
    for absent in ("Dot-bracket", "Selected member", "GGGAAACCC", "input_paths", "rna_comparison_receipt:"):
        assert absent not in text
    (tmp_path / "RETAINED_WORKFLOW_SCAN_TEXT_001.txt").write_text(text + "\n")
    (tmp_path / "RETAINED_WORKFLOW_SCAN_SOURCE_001.json").write_text(json.dumps({
        "fixture_provenance": example["fixture_provenance"],
        "original_path": str(path), "requested_return": case["returned"],
        "presentation_changes_numeric_values": False}, indent=2) + "\n")
