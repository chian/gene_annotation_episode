"""Projection checks over explicitly synthetic retained comparison inputs.

Invented energies and recognized software identities are engineering fixtures,
not native observations. Calculations build fixture inputs only; the projector
must operate with calculator/native/acquisition paths unavailable.
"""
from copy import deepcopy
import importlib
import inspect
import json
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.rna_structure_comparison_contracts import (
    PAIR_METRICS, PAIR_RELATIONS, SCAN_ENERGY_METRICS, SCAN_SITE_METRICS,
    SITE_METRICS, SITE_TRANSITIONS, comparison_digest, validate_rna_comparison_components,
)
from gene_annotation_episode.rna_structure_comparison_calculations import calculate_rna_comparison_components
from gene_annotation_episode.rna_structure_comparison_inputs import populate_rna_comparison_sheet
from gene_annotation_episode.rna_structure_comparison_views import (
    PROJECTION_SOURCE, RETURNED_NUMERIC_CELL_SCHEMA, RNA_COMPARISON_PROJECTION_RESULT_SCHEMA,
    project_rna_comparison, rna_comparison_fact_sources, validate_rna_comparison_projection,
)

f = importlib.import_module("verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")
a = importlib.import_module("verification.tool_graders_rna_comparison_inputs_2026-10-26_366.fixture_helpers")
REPO = Path(__file__).resolve().parents[1]
KEYS = {"result_receipt_key": "rna_comparison_receipt:" + "1" * 64,
    "calculation_key": "rna_comparison_calculation:" + "2" * 64}


def request_for(family, **overrides):
    values = {
        "energy_comparison": {"comparison_ids": ["compare-V"], "metrics": ["energy_delta", "baseline_native_energy", "variant_native_energy"],
            "include_order": True, "include_tolerance_band": False},
        "structures": {"member_ids": ["WT", "V"], "fields": ["dot_bracket"]},
        "position_changes": {"comparison_id": "compare-V", "selection_id": "selected", "transitions": list(SITE_TRANSITIONS)},
        "pair_changes": {"comparison_ids": ["compare-V"], "relations": list(PAIR_RELATIONS)},
        "comparison_counts": {"comparison_ids": ["compare-V"], "selection_ids": ["selected"],
            "metrics": ["changed_site_fraction", "pair_symmetric_difference_count"], "include_pairing_change_state": True},
        "scan_energy": {"scan_id": "scan", "metrics": ["baseline_rank_start", "baseline_rank_end", "baseline_tie_count",
            "minimum_selected_energy", "baseline_energy_above_minimum", "lowest_energy_tie_count"], "include_rank_class": True},
        "scan_sites": {"scan_id": "scan", "selection_ids": ["selected"], "metrics": list(SCAN_SITE_METRICS)},
        "scan_members": {"scan_id": "scan", "members": {"kind": "exceptions", "predicates": ["lower_than_baseline"]},
            "fields": ["energy", "rank_start", "rank_end", "eligibility"], "order": "declared", "limit": None},
    }
    return {"projection_id": family, "family": family, **values[family], **overrides}


def calculate(sheet):
    return sheet, calculate_rna_comparison_components(sheet)


def project(data, *requests):
    return project_rna_comparison(*data, projections=list(requests), **KEYS)


def valid(result, data, selected):
    assert validate_rna_comparison_projection(result, sheet=data[0], components=data[1], selection=selected, **KEYS) == result
    assert Draft202012Validator(RNA_COMPARISON_PROJECTION_RESULT_SCHEMA).is_valid(result)


def strings(value):
    if isinstance(value, dict):
        return [string for child in value.values() for string in strings(child)]
    if isinstance(value, list):
        return [string for child in value for string in strings(child)]
    return [value] if isinstance(value, str) else []


def keys(value):
    if isinstance(value, dict):
        return [*value, *[key for child in value.values() for key in keys(child)]]
    if isinstance(value, list):
        return [key for child in value for key in keys(child)]
    return []


@pytest.fixture(scope="module")
def pair_data():
    return calculate(f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0), energy=f.energy_request()))


@pytest.fixture(scope="module")
def scan_data():
    return calculate(f.scan(extra_members=[f.absent("NS", "not_supplied"), f.absent("NT")],
        extra_operands={"NS": f.blank(), "NT": f.blank()}))


@pytest.fixture(scope="module")
def all_family_data():
    sheet = f.scan(failed=False, aliases=True)
    q = deepcopy(sheet["selected_question"])
    originals = {o["member_id"]: o["original_sheet"] for o in sheet["operands"]}
    baseline = originals["WT"]["analysis_sequence"]["analysis_sequence"]
    for comparison in q["comparisons"]:
        variant = originals[comparison["variant_member_id"]]["analysis_sequence"]["analysis_sequence"]
        comparison["correspondence"] = {"kind": "substitution_only", "substitutions": [
            {"index": i, "baseline_symbol": x, "variant_symbol": y} for i, (x, y) in enumerate(zip(baseline, variant)) if x != y]}
        comparison["site_selections"] = [f.site(positions=[0, 1, 2])]
        comparison["calculate_pair_changes"] = True
    q["scan"]["topology_selection_ids"] = ["selected"]
    return calculate(f.rebuild(sheet, question=q))


def all_requests():
    return [
        request_for("energy_comparison", comparison_ids=["compare-B", "compare-A"]),
        request_for("structures", member_ids=["B", "WT"], fields=["pairs", "original_sequence"]),
        request_for("position_changes", comparison_id="compare-A"),
        request_for("pair_changes", comparison_ids=["compare-B", "compare-A"]),
        request_for("comparison_counts", comparison_ids=["compare-A", "compare-B"]),
        request_for("scan_energy"), request_for("scan_sites"), request_for("scan_members"),
    ]


@pytest.mark.parametrize("family_index", range(8))
def test_each_exact_projection_family_alone(all_family_data, family_index):
    selected = all_requests()[family_index]
    result, = project(all_family_data, selected)
    valid(result, all_family_data, selected)
    assert result["selection"] == selected
    assert result["family"] == selected["family"]
    assert "input_paths" not in keys(result)


def test_explicit_combination_preserves_projection_request_and_field_order(all_family_data):
    requests = all_requests()[::-1]
    results = project(all_family_data, *requests)
    assert [r["projection_id"] for r in results] == [r["projection_id"] for r in requests]
    energy = next(r for r in results if r["family"] == "energy_comparison")
    assert [r["comparison_id"] for r in energy["payload"]["rows"]] == ["compare-B", "compare-A"]
    assert [c["metric"] for c in energy["payload"]["rows"][0]["measurements"]] == requests[-1]["metrics"]
    structures = next(r for r in results if r["family"] == "structures")
    assert [r["member_id"] for r in structures["payload"]["rows"]] == ["B", "WT"]
    assert [v["field"] for v in structures["payload"]["rows"][0]["values"]] == ["pairs", "original_sequence"]
    assert energy["population_id"] is None  # These are two distinct comparison populations.


def test_parent_energy_only_and_two_structures_only_do_not_expand_each_other(pair_data):
    energy, = project(pair_data, request_for("energy_comparison"))
    assert f.values(energy["payload"]["rows"][0]["measurements"])["energy_delta"] == 1.0
    assert not {"GGGAAACCC", "GGGAAAUCC", "(((...)))"} & set(strings(energy))
    structures, = project(pair_data, request_for("structures"))
    assert [row["values"] for row in structures["payload"]["rows"]] == [
        [{"field": "dot_bracket", "state": "present", "value": "(((...)))", "reason": None}]] * 2
    assert "energy_delta" not in strings(structures)
    assert structures["qualification"]["site_populations"] == structures["qualification"]["pair_populations"] == []


def test_returned_cell_keeps_every_numerical_field_and_only_omits_full_paths(pair_data):
    result, = project(pair_data, request_for("energy_comparison"))
    originals = f.cells(pair_data[1]["comparisons"][0]["energy"]["components"])
    for cell in result["payload"]["rows"][0]["measurements"]:
        original = originals[cell["metric"]]
        assert cell == {k: v for k, v in original.items() if k != "input_paths"}
        assert set(cell) == set(RETURNED_NUMERIC_CELL_SCHEMA["properties"])
        assert original["input_paths"]


def test_all_structure_fields_keep_original_case_and_selected_order():
    left = f.feature(sequence="gggaaaccc", normalization="uppercase_ascii")
    data = calculate(f.pair(left, pairs=False, selections=[]))
    chosen = request_for("structures", member_ids=["WT"], fields=["analysis_sequence", "pairs", "original_sequence", "dot_bracket"])
    result, = project(data, chosen)
    values = result["payload"]["rows"][0]["values"]
    assert [v["value"] for v in values] == ["GGGAAACCC", [[0, 8], [1, 7], [2, 6]], "gggaaaccc", "(((...)))"]
    valid(result, data, chosen)


@pytest.mark.parametrize("original,expected", [("(((...))", "(((...))"), ("([)]", "([)]"), ("", "")])
def test_invalid_original_structure_is_returned_as_invalid_text_without_pairs(original, expected):
    left = f.feature(structure=original)
    data = calculate(f.pair(left, correspondence=None, pairs=False, selections=[]))
    result, = project(data, request_for("structures", member_ids=["WT"], fields=["dot_bracket", "pairs"]))
    fields = result["payload"]["rows"][0]["values"]
    assert fields[0] == {"field": "dot_bracket", "state": "invalid_input", "value": expected, "reason": "original_topology_invalid"}
    assert fields[1] == {"field": "pairs", "state": "invalid_input", "value": None, "reason": "original_topology_invalid"}
    assert result["delivery"] == "qualified_unavailability"


@pytest.mark.parametrize("sequence,state,value", [(None, "missing_input", None), ("AC@", "invalid_input", "AC@"), ("", "invalid_input", "")])
def test_missing_and_invalid_original_sequence_are_distinct(sequence, state, value):
    data = calculate(f.pair(f.feature(sequence=sequence), correspondence=None, pairs=False, selections=[]))
    result, = project(data, request_for("structures", member_ids=["WT"], fields=["original_sequence", "analysis_sequence"]))
    fields = result["payload"]["rows"][0]["values"]
    assert fields[0]["value"] == value and fields[0]["state"] == state
    assert fields[1]["value"] is None and fields[1]["state"] == state


def test_absent_member_structure_has_exact_absence_reason(scan_data):
    result, = project(scan_data, request_for("structures", member_ids=["NS", "NT", "D"], fields=["dot_bracket"]))
    assert [r["values"][0]["reason"] for r in result["payload"]["rows"]] == ["not_supplied", "not_tested", "received_failure"]
    assert all(r["structure_origin"] is None for r in result["payload"]["rows"])


def test_reassigned_selected_partner_and_no_unrequested_sites():
    data = calculate(f.pair(f.feature(sequence="GGGAAAACCC", structure="((....)).."),
        f.feature("V", "GGGAAAACCC", ".((....))."), selections=[f.site(positions=[1])]))
    selected = request_for("position_changes")
    result, = project(data, selected)
    row, = result["payload"]["rows"]
    assert row["baseline_index"] == row["variant_index"] == 1
    assert row["baseline_partner"]["local_index"] == 6
    assert row["variant_partner"]["local_index"] == 8
    assert row["transition"] == "reassigned_partner" and row["change_indicator"]["value"] == 1
    assert result["qualification"]["site_populations"][0]["requested_site_count"] == 1
    assert "((....)).." not in strings(result)
    valid(result, data, selected)


def test_insertion_uses_selected_variant_coordinates_and_partner_correspondence():
    data = calculate(f.pair(b=f.feature("V", "UGGGAAACCC", ".(((...)))"),
        correspondence=f.complete([(None, 0), *[(i, i + 1) for i in range(9)]]),
        selections=[f.site(member_id="V", positions=[1])]))
    result, = project(data, request_for("position_changes"))
    row, = result["payload"]["rows"]
    assert (row["baseline_index"], row["variant_index"], row["column"]) == (0, 1, 1)
    assert row["baseline_partner"] == {"state": "mapped", "local_index": 8, "column": 9, "counterpart_index": 9}
    assert row["variant_partner"] == {"state": "mapped", "local_index": 9, "column": 9, "counterpart_index": 8}


def test_deletion_denominator_context_and_pair_rows_are_distinct():
    mapping = [(i, None if i == 3 else i if i < 3 else i - 1) for i in range(9)]
    data = calculate(f.pair(b=f.feature("V", "GGGAACCC", "(((..)))"), correspondence=f.complete(mapping),
        selections=[f.site(positions=[2, 3, 6])]))
    result, = project(data, request_for("comparison_counts", metrics=["unchanged_site_fraction", "decidable_site_fraction"],
        include_pairing_change_state=False))
    row, = result["payload"]["rows"]
    cells = {c["metric"]: c for c in row["measurements"]}
    assert (cells["unchanged_site_fraction"]["numerator"], cells["unchanged_site_fraction"]["denominator"]) == (2, 2)
    assert (cells["decidable_site_fraction"]["numerator"], cells["decidable_site_fraction"]["denominator"]) == (2, 3)
    assert result["qualification"]["site_populations"] == [{"comparison_id": "compare-V", "selection_id": "selected",
        "requested_site_count": 3, "decidable_site_count": 2, "deleted_site_count": 1, "inserted_site_count": 0,
        "unmapped_site_count": 0, "unavailable_topology_site_count": 0, "unresolved_partner_site_count": 0}]
    assert result["qualification"]["pair_populations"] == []
    pairs, = project(data, request_for("pair_changes", relations=["preserved"]))
    assert pairs["payload"]["rows"][0]["change"]["baseline_pair"] == [0, 8]
    assert pairs["payload"]["rows"][0]["change"]["variant_pair"] == [0, 7]


def test_partial_partner_unknown_is_not_returned_as_stable():
    data = calculate(f.pair(correspondence=f.partial([(0, 0)]), selections=[f.site(positions=[0])]))
    result, = project(data, request_for("position_changes"))
    row, = result["payload"]["rows"]
    assert row["transition"] == "unresolved_partner" and row["change_indicator"]["value"] is None
    assert row["baseline_partner"]["local_index"] == 8 and row["baseline_partner"]["column"] is None
    assert result["qualification"]["site_populations"][0]["decidable_site_count"] == 0
    assert result["delivery"] == "qualified_unavailability"


@pytest.mark.parametrize("positions,expected_count,delivery", [([], 0, "empty_selected_set"), ([99], None, "qualified_unavailability")])
def test_valid_empty_vs_invalid_selection_keeps_count_knowledge(positions, expected_count, delivery):
    data = calculate(f.pair(selections=[f.site(positions=positions)]))
    selected = request_for("position_changes")
    result, = project(data, selected)
    assert result["payload"]["rows"] == [] and result["delivery"] == delivery
    assert result["qualification"]["site_populations"][0]["requested_site_count"] == expected_count
    counts, = project(data, request_for("comparison_counts", metrics=["requested_site_count", "changed_site_fraction"], include_pairing_change_state=False))
    assert counts["payload"]["rows"][0]["measurements"][0]["value"] == expected_count
    assert counts["payload"]["rows"][0]["measurements"][1]["value"] is None


def test_empty_transition_filter_is_not_an_unavailable_calculation(pair_data):
    result, = project(pair_data, request_for("position_changes", transitions=["lost_pairing"]))
    assert result["delivery"] == "empty_selected_set"
    assert result["qualification"]["site_populations"][0]["decidable_site_count"] == 9


def test_no_implicit_pair_or_site_count_rows(pair_data):
    pair, = project(pair_data, request_for("comparison_counts", selection_ids=[], metrics=["preserved_pair_count"], include_pairing_change_state=False))
    site, = project(pair_data, request_for("comparison_counts", metrics=["changed_site_count"], include_pairing_change_state=False))
    assert [r["selection_id"] for r in pair["payload"]["rows"]] == [None]
    assert [r["selection_id"] for r in site["payload"]["rows"]] == ["selected"]
    assert pair["qualification"]["site_populations"] == site["qualification"]["pair_populations"] == []


def test_scan_ranking_has_required_actual_population_without_member_dump(scan_data):
    result, = project(scan_data, request_for("scan_energy"))
    values = f.values(result["payload"]["measurements"])
    assert values == {"baseline_rank_start": 2, "baseline_rank_end": 3, "baseline_tie_count": 2,
        "minimum_selected_energy": -5.0, "baseline_energy_above_minimum": 1.0, "lowest_energy_tie_count": 1}
    assert result["payload"]["rank_class"] == "not_lowest"
    assert result["qualification"]["population"] == {"declared_variant_count": 6, "alias_entry_count": 1,
        "native_energy_available_variant_count": 3, "comparable_variant_count": 3, "received_failure_variant_count": 1,
        "not_supplied_variant_count": 1, "not_tested_variant_count": 1, "sheet_energy_unavailable_variant_count": 0,
        "model_incompatible_variant_count": 0, "model_unknown_variant_count": 0, "rank_population_count": 4}
    assert result["qualification"]["member_ids"] == ["WT"]
    assert not {"A", "B", "C", "D", "NS", "NT", "AliasA", "GGGAAACCC", "(((...)))"} & set(strings(result))
    assert result["delivery"] == "values"


def test_rank_class_only_uses_retained_population_without_extra_measurement(scan_data):
    result, = project(scan_data, request_for("scan_energy", metrics=[]))
    assert result["payload"]["measurements"] == []
    assert result["population_id"] == scan_data[1]["scan"]["energy_components"][0]["population_id"]


def test_exact_member_predicates_use_or_and_explicit_window(scan_data):
    selected = request_for("scan_members", members={"kind": "exceptions", "predicates": ["lower_than_baseline", "received_failure", "not_tested"]}, limit=2)
    result, = project(scan_data, selected)
    assert (result["payload"]["matched_count"], result["payload"]["returned_count"], result["payload"]["omitted_count"]) == (3, 2, 1)
    assert [r["member_id"] for r in result["payload"]["rows"]] == ["A", "D"]
    assert "selected_window_omits_members" in result["qualification"]["codes"]
    assert result["qualification"]["member_ids"] == ["WT", "A", "D"]
    assert "NT" not in [issue["member_id"] for issue in result["qualification"]["issues"]]
    assert result["delivery"] == "qualified_unavailability"
    valid(result, scan_data, selected)


def test_alias_requires_explicit_selection_and_retains_declared_order(scan_data):
    selected = request_for("scan_members", members={"kind": "explicit", "member_ids": ["AliasA", "B", "WT"]},
        fields=["rank_end", "rank_start", "eligibility"])
    result, = project(scan_data, selected)
    assert [r["member_id"] for r in result["payload"]["rows"]] == ["WT", "B", "AliasA"]
    alias = result["payload"]["rows"][-1]
    assert alias["canonical_member_id"] == "A"
    assert [v["field"] for v in alias["values"]] == selected["fields"]
    assert [v["cell"]["value"] for v in alias["values"][:2]] == [1, 1]
    assert result["qualification"]["population"]["rank_population_count"] == 4


@pytest.mark.parametrize("predicates,expected", [(["lower_than_baseline"], ["A"]), (["equal_to_baseline"], ["B"]),
    (["higher_than_baseline"], ["C"]), (["received_failure"], ["D"]), (["not_supplied"], ["NS"]), (["not_tested"], ["NT"])])
def test_each_scan_predicate_is_exact_selected_class(scan_data, predicates, expected):
    result, = project(scan_data, request_for("scan_members", members={"kind": "exceptions", "predicates": predicates}, fields=["eligibility"]))
    assert [r["member_id"] for r in result["payload"]["rows"]] == expected


def test_tolerance_selects_stored_band_but_never_rewrites_ranks():
    data = calculate(f.scan((0.0, 0.06, 0.12), failed=False, aliases=False, tolerance=0.1))
    selected = request_for("scan_members", members={"kind": "exceptions", "predicates": ["within_baseline_tolerance"]}, fields=["rank_start", "rank_end"])
    result, = project(data, selected)
    assert [r["member_id"] for r in result["payload"]["rows"]] == ["A"]
    assert [v["cell"]["value"] for v in result["payload"]["rows"][0]["values"]] == [2, 2]


def test_exception_predicate_uses_exact_classification_when_numbers_round_equal():
    tiny = float.fromhex("0x0.0000000000001p-1022")
    wt = f.feature(sequence="AAA", structure="...", energy=tiny)
    variant = f.feature("A", "CCCCCC", "......", energy=tiny)
    energy = f.energy_request(normalization="per_nt")
    selected = f.selector([f.member(wt), f.member(variant)], [f.comparison("A", energy=energy)], scan=f.scan_request(energy))
    data = calculate(populate_rna_comparison_sheet(selected, operands={"WT": f.supplied(wt), "A": f.supplied(variant)}))
    assert [row["energy"]["value"] for row in data[1]["scan"]["members"]] == [0.0, 0.0]
    result, = project(data, request_for("scan_members", fields=["energy", "rank_start"]))
    assert [row["member_id"] for row in result["payload"]["rows"]] == ["A"]
    assert result["payload"]["rows"][0]["values"][1]["cell"]["value"] == 1


@pytest.mark.parametrize("kind,predicate", [("incompatible", "model_incompatible"),
    ("unknown", "model_unknown"), ("unavailable", "energy_unavailable")])
def test_exclusion_predicates_preserve_original_eligibility(kind, predicate):
    sheet = f.scan(failed=False, aliases=False)
    operands = {o["member_id"]: {k: deepcopy(o[k]) for k in f.blank()} for o in sheet["operands"]}
    if kind == "incompatible":
        operands["A"] = f.supplied(f.feature("A", "GGGAAAUCC", energy=-5.0, temperature=25.0))
    elif kind == "unknown":
        operands["A"]["original_bundle_software"] = None
    else:
        operands["A"] = f.supplied(f.feature("A", "GGGAAAUCC"))
    data = calculate(f.rebuild(sheet, operands=operands))
    result, = project(data, request_for("scan_members", members={"kind": "exceptions", "predicates": [predicate]}, fields=["eligibility"]))
    assert [row["member_id"] for row in result["payload"]["rows"]] == ["A"]
    expected = "native_energy_unavailable" if kind == "unavailable" else "model_" + kind
    assert result["payload"]["rows"][0]["values"] == [{"field": "eligibility", "state": expected}]


def test_baseline_only_scan_is_ranked_without_invented_variants():
    data = calculate(f.scan((-4.0,), failed=False, aliases=False))
    result, = project(data, request_for("scan_energy"))
    assert result["qualification"]["population"]["declared_variant_count"] == 0
    assert result["qualification"]["population"]["rank_population_count"] == 1
    assert result["payload"]["rank_class"] == "unique_lowest"
    assert f.values(result["payload"]["measurements"])["baseline_energy_above_minimum"] == 0.0


def test_valid_all_unpaired_topology_has_empty_pairs_and_zero_denominator():
    data = calculate(f.pair(f.feature(structure="........."), f.feature("V", "GGGAAAUCC", ".........")))
    result, = project(data, request_for("pair_changes"))
    assert result["payload"]["rows"] == [] and result["delivery"] == "empty_selected_set"
    assert result["qualification"]["pair_populations"][0]["baseline_pair_count"] == 0
    counts, = project(data, request_for("comparison_counts", selection_ids=[],
        metrics=["preserved_baseline_pair_fraction"], include_pairing_change_state=False))
    cell = counts["payload"]["rows"][0]["measurements"][0]
    assert cell["denominator"] == 0 and cell["reason"] == "zero_denominator"


def test_unavailable_topology_does_not_claim_empty_change_filter():
    data = calculate(f.pair(f.feature(structure="(((...))("), correspondence=f.complete([(i, i) for i in range(9)]),
        selections=[f.site(positions=[0, 1])]))
    result, = project(data, request_for("position_changes", transitions=["lost_pairing"]))
    assert result["payload"]["rows"] == [] and result["delivery"] == "qualified_unavailability"
    assert result["qualification"]["site_populations"][0]["unavailable_topology_site_count"] == 2


def test_overlap_union_does_not_duplicate_position_returns():
    data = calculate(f.pair(selections=[f.site(positions=[3, 4, 3], intervals=[(3, 6)], regions=["region:2:6"])]))
    result, = project(data, request_for("position_changes"))
    assert [r["baseline_index"] for r in result["payload"]["rows"]] == [3, 4, 5]


def test_incompatible_raw_energy_remains_present_while_delta_unavailable():
    data = calculate(f.pair(f.feature(energy=-4.0), f.feature("V", "GGGAAAUCC", energy=-6.0, temperature=25.0), energy=f.energy_request()))
    result, = project(data, request_for("energy_comparison"))
    row, = result["payload"]["rows"]
    assert row["compatibility_state"] == "incompatible"
    assert f.values(row["measurements"]) == {"energy_delta": None, "baseline_native_energy": -4.0, "variant_native_energy": -6.0}
    assert "model_setting_different" in result["qualification"]["codes"]
    assert result["delivery"] == "qualified_unavailability"


def test_missing_baseline_rank_unavailable_not_empty_population():
    sheet = f.scan()
    q = deepcopy(sheet["selected_question"])
    q["membership"][0] = f.absent("WT", "not_supplied")
    operands = {o["member_id"]: {k: deepcopy(o[k]) for k in f.blank()} for o in sheet["operands"] if o["state"] != "alias"}
    operands["WT"] = f.blank()
    data = calculate(f.rebuild(sheet, question=q, operands=operands))
    result, = project(data, request_for("scan_energy"))
    assert result["qualification"]["population"]["rank_population_count"] is None
    assert result["qualification"]["population"]["native_energy_available_variant_count"] == 3
    assert result["delivery"] == "qualified_unavailability"
    assert result["payload"]["rank_class"] == "unavailable"


def test_topology_only_scan_eligibility_has_no_fabricated_energy_population(all_family_data):
    q = deepcopy(all_family_data[0]["selected_question"])
    q["scan"]["energy"] = None
    for c in q["comparisons"]:
        c["energy"] = None
    data = calculate(f.rebuild(all_family_data[0], question=q))
    selected = request_for("scan_members", members={"kind": "explicit", "member_ids": ["WT", "A"]}, fields=["eligibility"])
    result, = project(data, selected)
    assert result["qualification"]["population"] is None and result["population_id"] is None
    assert [r["values"] for r in result["payload"]["rows"]] == [[{"field": "eligibility", "state": "not_requested"}]] * 2
    with pytest.raises(ValueError):
        project(data, {**selected, "fields": ["energy"]})


def test_scan_sites_has_per_site_variant_denominator_without_individual_members(all_family_data):
    result, = project(all_family_data, request_for("scan_sites", metrics=["changed_variant_fraction", "decidable_variant_count"]))
    assert [r["baseline_index"] for r in result["payload"]["rows"]] == [0, 1, 2]
    assert all(r["measurements"][0]["denominator"] == 3 for r in result["payload"]["rows"])
    assert result["qualification"]["member_ids"] == ["WT"]
    assert not {"A", "B", "C", "AliasA"} & set(strings(result))


def test_unrequested_topology_selection_issues_do_not_cross_scan_projection(all_family_data):
    q = deepcopy(all_family_data[0]["selected_question"])
    q["comparisons"][0]["site_selections"].append(f.site(key="unrequested-invalid-sites", positions=[99]))
    data = calculate(f.rebuild(all_family_data[0], question=q))
    for selected in (request_for("scan_energy"), request_for("scan_sites"), request_for("scan_members")):
        result, = project(data, selected)
        assert "unrequested-invalid-sites" not in strings(result)
        assert "invalid_site_selection" not in result["qualification"]["codes"]
    explicitly_invalid, = project(data, request_for("position_changes", comparison_id="compare-A", selection_id="unrequested-invalid-sites"))
    assert explicitly_invalid["delivery"] == "qualified_unavailability"
    assert "invalid_site_selection" in explicitly_invalid["qualification"]["codes"]


@pytest.mark.parametrize("limit,returned", [(0, 0), (1, 1), (None, 2)])
def test_explicit_limit_never_means_native_truncation(scan_data, limit, returned):
    result, = project(scan_data, request_for("scan_members", members={"kind": "explicit", "member_ids": ["A", "B"]}, limit=limit))
    assert result["payload"]["matched_count"] == 2 and result["payload"]["returned_count"] == returned
    assert result["payload"]["omitted_count"] == 2 - returned
    assert "truncated" not in strings(result)
    if limit == 0:
        assert result["delivery"] == "empty_selected_set"


@pytest.mark.parametrize("key,value", [("result_receipt_key", "rna_comparison_receipt:" + "A" * 64),
    ("calculation_key", "rna_comparison_calculation:" + "3" * 63), ("result_receipt_key", "rna_result_receipt:" + "1" * 64),
    ("calculation_key", True)])
def test_publication_keys_have_strict_prefix_digest_types(pair_data, key, value):
    with pytest.raises(ValueError, match="projection_mismatch"):
        project_rna_comparison(*pair_data, projections=[request_for("structures")], **{**KEYS, key: value})


@pytest.mark.parametrize("key", KEYS)
def test_well_formed_but_wrong_publication_key_is_rejected(pair_data, key):
    selected = request_for("structures")
    result, = project(pair_data, selected)
    result[key] = result[key][:-1] + "a"
    with pytest.raises(ValueError, match="projection_mismatch"):
        valid(result, pair_data, selected)


@pytest.mark.parametrize("family,mutation", [
    ("energy_comparison", lambda r: r["payload"]["rows"][0]["measurements"][0].update(value=999.0)),
    ("energy_comparison", lambda r: r["payload"]["rows"][0].update(order="equal")),
    ("structures", lambda r: r["payload"]["rows"][0]["values"][0].update(value=".........")),
    ("structures", lambda r: r["payload"]["rows"].reverse()),
    ("position_changes", lambda r: r["payload"]["rows"][0].update(baseline_index=8)),
    ("position_changes", lambda r: r["payload"]["rows"][0]["baseline_partner"].update(local_index=7)),
    ("position_changes", lambda r: r["payload"]["rows"].pop()),
    ("pair_changes", lambda r: r["payload"]["rows"][0]["change"].update(variant_pair=[0, 7])),
    ("comparison_counts", lambda r: r["qualification"]["site_populations"][0].update(decidable_site_count=99)),
    ("comparison_counts", lambda r: r["payload"]["rows"][0]["measurements"][0].update(metric="lost_pair_count")),
])
def test_forged_projected_values_rows_positions_partners_and_strings_rejected(pair_data, family, mutation):
    selected = request_for(family)
    result, = project(pair_data, selected)
    mutation(result)
    with pytest.raises(ValueError):
        valid(result, pair_data, selected)


@pytest.mark.parametrize("mutation", [lambda r: r.update(extra="unrequested"),
    lambda r: r["selection"]["metrics"].reverse(),
    lambda r: r["payload"]["rows"][0]["measurements"].pop(),
    lambda r: r["qualification"]["codes"].append("free prose"),
    lambda r: r.update(population_id="unrelated"),
    lambda r: r["payload"]["rows"][0]["measurements"][0].update(value=True),
    lambda r: r["payload"]["rows"][0]["measurements"][0].update(value=float("nan")),
    lambda r: r["payload"]["rows"][0]["measurements"][0].update(unit="kcal/mol/nt"),
    lambda r: r["payload"]["rows"][0]["measurements"][0].update(denominator=9),
    lambda r: r["payload"]["rows"][0]["measurements"][0].update(input_paths=["/operands"]),
])
def test_closed_exact_projection_rejects_extra_missing_changed_and_nonfinite(pair_data, mutation):
    selected = request_for("energy_comparison")
    result, = project(pair_data, selected)
    mutation(result)
    with pytest.raises(ValueError):
        valid(result, pair_data, selected)


@pytest.mark.parametrize("selected", [request_for("scan_energy", metrics=["member_rank_start"]),
    request_for("scan_members", members={"kind": "explicit", "member_ids": ["unselected"]}),
    request_for("scan_members", members={"kind": "exceptions", "predicates": ["almost_equal"]})])
def test_invalid_projection_relationships_do_not_widen_selection(scan_data, selected):
    with pytest.raises(ValueError):
        project(scan_data, selected)


@pytest.mark.parametrize("mutation", [lambda r: r["payload"].update(matched_count=999),
    lambda r: r["payload"]["rows"][0].update(canonical_member_id="B"),
    lambda r: r["payload"]["rows"][0]["values"][0]["cell"].update(value=-8.0),
    lambda r: r["qualification"]["population"].update(rank_population_count=5),
    lambda r: r["qualification"]["member_ids"].append("AliasA")])
def test_forged_scan_members_ranks_population_and_exclusions_rejected(scan_data, mutation):
    selected = request_for("scan_members")
    result, = project(scan_data, selected)
    mutation(result)
    with pytest.raises(ValueError):
        valid(result, scan_data, selected)


def test_unexpected_null_selected_member_cell_cannot_be_synthesized(scan_data):
    data = deepcopy(scan_data)
    data[1]["scan"]["members"][1]["energy"] = None
    with pytest.raises(ValueError, match="projection_mismatch"):
        project(data, request_for("scan_members"))


def test_empty_or_duplicate_projection_list_is_rejected(pair_data):
    with pytest.raises(ValueError):
        project(pair_data)
    selected = request_for("structures")
    with pytest.raises(ValueError):
        project(pair_data, selected, selected)


def test_projection_is_pure_detached_and_reselectable_without_calculators(pair_data, monkeypatch):
    sheet, components = pair_data
    before = deepcopy(pair_data)
    def forbidden(*args, **kwargs):
        raise AssertionError("Projector attempted calculation or acquisition")
    calculation = importlib.import_module("gene_annotation_episode.rna_structure_comparison_calculations")
    scan_calculation = importlib.import_module("gene_annotation_episode.rna_structure_scan_calculations")
    monkeypatch.setattr(calculation, "calculate_rna_comparison_components", forbidden)
    monkeypatch.setattr(scan_calculation, "calculate_rna_scan_components", forbidden)
    monkeypatch.setitem(sys.modules, "RNA", None)
    selected = request_for("structures", member_ids=["V"], fields=["original_sequence"])
    result, = project(pair_data, selected)
    valid(result, pair_data, selected)
    result["payload"]["rows"][0]["values"][0]["value"] = "changed copy"
    assert pair_data == before
    assert any(c["input_paths"] for c in components["comparisons"][0]["energy"]["components"])
    next_result, = project(pair_data, request_for("energy_comparison", metrics=["energy_absolute_delta"], include_order=False))
    assert next_result["payload"]["rows"][0]["measurements"][0]["value"] == 1.0
    assert next_result["payload"]["rows"][0]["order"] is None
    source = inspect.getsource(importlib.import_module("gene_annotation_episode.rna_structure_comparison_views"))
    assert "from .rna_structure_comparison_calculations import" not in source
    assert "import subprocess" not in source and "open(" not in source


def test_shape_validation_does_not_claim_independent_numerical_proof(pair_data):
    sheet, components = deepcopy(pair_data)
    components["comparisons"][0]["energy"]["components"][4]["value"] = 123.0
    # Source arithmetic checking is workload D's job; C copies supplied cells.
    validate_rna_comparison_components(components, sheet=sheet)
    result, = project((sheet, components), request_for("energy_comparison", metrics=["energy_delta"], include_order=False))
    assert result["payload"]["rows"][0]["measurements"][0]["value"] == 123.0


def test_schema_source_is_closed_and_detached():
    source = rna_comparison_fact_sources()
    assert list(source) == [PROJECTION_SOURCE]
    schema = source[PROJECTION_SOURCE]["report_schema"]
    Draft202012Validator.check_schema(schema)
    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for child in node.values():
                check(child)
        elif isinstance(node, list):
            for child in node:
                check(child)
    check(schema)
    schema["items"]["oneOf"].clear()
    assert len(rna_comparison_fact_sources()[PROJECTION_SOURCE]["report_schema"]["items"]["oneOf"]) == 8


def test_tied_normalized_minimum_carries_original_ratio_without_member_return():
    wt = f.feature(sequence="AAAAAAAAA", structure=".........", energy=-4.0)
    variant = f.feature("A", "C" * 18, "." * 18, energy=-8.0)
    energy = f.energy_request(normalization="per_nt")
    selected = f.selector([f.member(wt), f.member(variant)], [f.comparison("A", energy=energy)], scan=f.scan_request(energy))
    data = calculate(populate_rna_comparison_sheet(selected, operands={"WT": f.supplied(wt), "A": f.supplied(variant)}))
    result, = project(data, request_for("scan_energy", metrics=["minimum_selected_energy", "lowest_energy_tie_count", "baseline_energy_above_minimum"]))
    cell = result["payload"]["measurements"][0]
    assert (cell["numerator"], cell["denominator"]) == (-4.0, 9)
    assert f.values(result["payload"]["measurements"])["lowest_energy_tie_count"] == 2
    assert f.values(result["payload"]["measurements"])["baseline_energy_above_minimum"] == 0.0
    assert "input_paths" not in cell and result["payload"]["rank_class"] == "tied_lowest"
    original_minimum = f.cells(data[1]["scan"]["energy_components"])["minimum_selected_energy"]
    assert len(original_minimum["input_paths"]) == 4
    assert "A" not in strings(result) and "AAAAAAAAA" not in strings(result)
    q = deepcopy(data[0]["selected_question"])
    q["membership"].reverse()
    reordered = calculate(f.rebuild(data[0], question=q))
    second, = project(reordered, result["selection"])
    minimum = second["payload"]["measurements"][0]
    assert (minimum["numerator"], minimum["denominator"]) == (-8.0, 18)
    assert [c["value"] for c in second["payload"]["measurements"]] == [c["value"] for c in result["payload"]["measurements"]]


def test_saved_parameter_change_recalculation_and_reprojection_preserve_old_data(pair_data):
    original = deepcopy(pair_data)
    q = deepcopy(pair_data[0]["selected_question"])
    q["comparisons"][0]["energy"]["normalization"] = "per_nt"
    changed = calculate(f.rebuild(pair_data[0], question=q))
    result, = project(changed, request_for("energy_comparison"))
    assert result["payload"]["rows"][0]["measurements"][0]["unit"] == "kcal/mol/nt"
    assert result["payload"]["rows"][0]["measurements"][0]["value"] == 1 / 9
    assert pair_data == original


def test_large_scan_retains_all_members_but_selected_output_is_bounded(tmp_path):
    # 256 unique synthetic variants; these are supplied model-energy fixtures.
    sequences = ["AAAA" + "".join("ACGU"[(n // (4 ** i)) % 4] for i in range(5)) for n in range(257)]
    sheets = [f.feature("WT" if i == 0 else f"V{i:03d}", seq, "." * 9, energy=-10.0 if i == 0 else -9.0 + (i % 4))
        for i, seq in enumerate(sequences)]
    energy = f.energy_request()
    members = [f.member(s) for s in sheets]
    selected = f.selector(members, [f.comparison(s["record_key"], energy=energy) for s in sheets[1:]], scan=f.scan_request(energy))
    sheet = populate_rna_comparison_sheet(selected, operands={s["record_key"]: f.supplied(s) for s in sheets})
    data = calculate(sheet)
    choice = request_for("scan_energy", metrics=["baseline_rank_start", "baseline_rank_end", "lowest_energy_tie_count", "baseline_energy_above_minimum"])
    result, = project(data, choice)
    assert len(data[1]["scan"]["members"]) == 257
    assert result["qualification"]["population"]["rank_population_count"] == 257
    assert result["payload"]["rank_class"] == "unique_lowest"
    assert len(json.dumps(result)) < 12000
    assert "input_paths" not in keys(result)
    assert len(f.cells(data[1]["scan"]["energy_components"])["baseline_rank_start"]["input_paths"]) > 1500
    assert not any(text.startswith("V0") or text.startswith("V1") or text.startswith("V2") for text in strings(result))
    assert not set(sequences) & set(strings(result))
    (tmp_path / "large_scan_selected_projection.json").write_text(json.dumps({"provenance": "synthetic fixture, no native execution",
        "retained_member_count": len(data[1]["scan"]["members"]), "projection": result}, indent=2) + "\n")


def test_filled_examples_retained_with_exact_selected_outputs(pair_data, scan_data, tmp_path):
    example = {"provenance": "Invented arithmetic fixture energies, not native measurements or execution",
        "pair": {"sheet": pair_data[0], "components": pair_data[1], "projections": project(pair_data,
            request_for("energy_comparison"), request_for("structures", fields=["original_sequence", "dot_bracket", "pairs"]))},
        "scan": {"sheet": scan_data[0], "components": scan_data[1], "projections": project(scan_data,
            request_for("scan_energy"), request_for("scan_members", limit=1))}}
    (tmp_path / "filled_examples.json").write_text(json.dumps(example, indent=2) + "\n")
    assert f.values(example["pair"]["projections"][0]["payload"]["rows"][0]["measurements"])["energy_delta"] == 1.0
    assert example["scan"]["projections"][0]["qualification"]["population"]["rank_population_count"] == 4
