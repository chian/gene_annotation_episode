"""Explicit invented energy populations; no native measurement claims."""
from copy import deepcopy
import importlib
import math

import pytest

from gene_annotation_episode.rna_structure_comparison_calculations import calculate_rna_comparison_components
from gene_annotation_episode.rna_structure_scan_calculations import calculate_rna_scan_components
from gene_annotation_episode.rna_structure_comparison_contracts import validate_rna_comparison_components
from gene_annotation_episode.rna_structure_comparison_inputs import populate_rna_comparison_sheet

f = importlib.import_module("verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")


def calculated(sheet):
    result = calculate_rna_comparison_components(sheet)
    validate_rna_comparison_components(result, sheet=sheet)
    comparisons = {c["comparison_id"]: c for c in result["comparisons"]}
    assert calculate_rna_scan_components(sheet, pairwise_components=comparisons) == result["scan"]
    return result["scan"]


def test_example_5_failure_ties_aliases_and_population_qualification():
    scan = calculated(f.scan())
    values = f.values(scan["energy_components"])
    expected = {"declared_entry_count": 6, "canonical_member_count": 5, "declared_variant_count": 4,
        "alias_entry_count": 1, "comparable_variant_count": 3, "received_failure_variant_count": 1,
        "rank_population_count": 4, "lower_variant_count": 1, "equal_variant_count": 1,
        "higher_variant_count": 1, "baseline_rank_start": 2, "baseline_rank_end": 3,
        "baseline_tie_count": 2, "baseline_selected_energy": -4.0, "minimum_selected_energy": -5.0,
        "baseline_energy_above_minimum": 1.0, "lowest_energy_tie_count": 1}
    assert {key: values[key] for key in expected} == expected
    rows = {m["member_id"]: m for m in scan["members"]}
    assert (rows["WT"]["exact_rank_start"]["value"], rows["WT"]["exact_rank_end"]["value"]) == (2, 3)
    assert (rows["B"]["exact_rank_start"]["value"], rows["B"]["exact_rank_end"]["value"]) == (2, 3)
    assert rows["AliasA"]["exact_rank_start"] == rows["A"]["exact_rank_start"]
    assert rows["AliasA"]["membership_state"] == "alias"
    assert rows["D"]["energy_state"] == "received_failure"
    assert scan["baseline_rank_class"] == "not_lowest"
    assert "selected_population_only" in {i["code"] for i in scan["issues"]}


def test_example_5_tied_lowest_variant():
    scan = calculated(f.scan((-5.0, -5.0, -4.0, -3.0)))
    values = f.values(scan["energy_components"])
    assert scan["baseline_rank_class"] == "tied_lowest"
    assert (values["baseline_rank_start"], values["baseline_rank_end"], values["lowest_energy_tie_count"]) == (1, 2, 2)
    assert values["baseline_energy_above_minimum"] == 0


def test_example_8_tolerance_does_not_make_approximate_ties():
    scan = calculated(f.scan((0.0, 0.06, 0.12), failed=False, aliases=False, tolerance=0.1))
    assert [r["exact_rank_start"]["value"] for r in scan["members"]] == [1, 2, 3]
    values = f.values(scan["energy_components"])
    assert values["within_tolerance_variant_count"] == 1
    assert values["equal_variant_count"] == 0 and values["baseline_tie_count"] == 1
    assert scan["baseline_rank_class"] == "unique_lowest"


def test_baseline_only_rank_is_valid_but_zero_variant_denominator_is_not():
    scan = calculated(f.scan((-4.0,), failed=False, aliases=False))
    cells = f.cells(scan["energy_components"])
    assert cells["rank_population_count"]["value"] == cells["baseline_rank_start"]["value"] == 1
    assert cells["baseline_selected_energy"]["value"] == cells["minimum_selected_energy"]["value"] == -4
    assert cells["lowest_energy_tie_count"]["value"] == 1
    assert cells["baseline_energy_above_minimum"]["value"] == 0
    assert cells["comparable_variant_fraction"]["value"] is None
    assert cells["comparable_variant_fraction"]["denominator"] == 0


@pytest.mark.parametrize("missing", ["received_failure", "not_supplied", "not_tested", "model_unknown", "missing_energy"])
def test_unqualified_baseline_keeps_independent_counts_and_no_rank_population(missing):
    sheet = f.scan()
    question = deepcopy(sheet["selected_question"])
    operands = {o["member_id"]: {k: deepcopy(o[k]) for k in ("original_sheet", "original_bundle_software", "received_failure")}
        for o in sheet["operands"] if o["state"] != "alias"}
    if missing == "received_failure":
        failure = f.failure("WT")
        question["membership"][0] = {"member_id": "WT", "kind": "received_failure", "failure": failure}
        operands["WT"] = {**f.blank(), "received_failure": failure}
    elif missing in ("not_supplied", "not_tested"):
        question["membership"][0] = f.absent("WT", missing)
        operands["WT"] = f.blank()
    elif missing == "model_unknown":
        operands["WT"]["original_bundle_software"] = None
    else:
        operands["WT"] = f.supplied(f.feature())
    sheet = f.rebuild(sheet, operands=operands, question=question)
    scan = calculated(sheet)
    cells = f.cells(scan["energy_components"])
    assert cells["declared_variant_count"]["value"] == 4
    assert cells["native_energy_available_variant_count"]["value"] == 3
    assert cells["received_failure_variant_count"]["value"] == 1
    for metric in ("comparable_variant_count", "model_incompatible_variant_count", "model_unknown_variant_count",
            "rank_population_count", "baseline_rank_start", "baseline_rank_end", "baseline_tie_count",
            "baseline_selected_energy", "minimum_selected_energy", "lowest_energy_tie_count", "baseline_energy_above_minimum"):
        assert cells[metric]["value"] is None
    assert all(row["exact_rank_start"]["value"] is None for row in scan["members"])
    assert scan["baseline_rank_class"] == "unavailable"


def test_scan_exclusion_partition_and_overlapping_native_availability_count():
    extra = [f.absent("N", "not_supplied"), f.absent("T", "not_tested")]
    missing = f.feature("M", "GGGACACCC")
    extra.append(f.member(missing))
    sheet = f.scan(extra_members=extra, extra_operands={"N": f.blank(), "T": f.blank(), "M": f.supplied(missing)})
    operands = {o["member_id"]: {k: deepcopy(o[k]) for k in ("original_sheet", "original_bundle_software", "received_failure")}
        for o in sheet["operands"] if o["state"] != "alias"}
    operands["A"]["original_sheet"]["model"]["selected"]["temperature_c"] = 25.0
    operands["A"]["original_sheet"]["model"]["effective_settings"]["temperature_c"] = 25.0
    operands["B"]["original_bundle_software"] = None
    scan = calculated(f.rebuild(sheet, operands=operands))
    values = f.values(scan["energy_components"])
    categories = ["received_failure_variant_count", "not_supplied_variant_count", "not_tested_variant_count",
        "sheet_energy_unavailable_variant_count", "model_incompatible_variant_count", "model_unknown_variant_count", "comparable_variant_count"]
    assert [values[c] for c in categories] == [1] * 7
    assert sum(values[c] for c in categories) == values["declared_variant_count"] == 7
    assert values["native_energy_available_variant_count"] == 3
    assert values["rank_population_count"] == 2
    assert scan["baseline_rank_class"] == "unique_lowest"


def test_known_member_mismatch_survives_unknown_baseline_proof_without_a_rank_population():
    sheet = f.scan()
    operands = {o["member_id"]: {k: deepcopy(o[k]) for k in ("original_sheet", "original_bundle_software", "received_failure")}
        for o in sheet["operands"] if o["state"] != "alias"}
    operands["WT"]["original_bundle_software"] = None
    operands["A"]["original_sheet"]["model"]["selected"]["temperature_c"] = 25.0
    operands["A"]["original_sheet"]["model"]["effective_settings"]["temperature_c"] = 25.0
    scan = calculated(f.rebuild(sheet, operands=operands))
    rows = {r["member_id"]: r for r in scan["members"]}
    assert rows["A"]["energy_state"] == "model_incompatible"
    assert rows["B"]["energy_state"] == "model_unknown"
    assert f.cells(scan["energy_components"])["rank_population_count"]["value"] is None


def ratio_scan(*, reorder=False, energy_a=-2.0, energy_b=-1.0):
    baseline = f.feature("WT", "AAA", "...", energy=energy_b)
    variant = f.feature("A", "AAAAAA", "......", energy=energy_a)
    request = f.energy_request(0.1, "per_nt")
    members = [f.member(variant), f.member(baseline)] if reorder else [f.member(baseline), f.member(variant)]
    return populate_rna_comparison_sheet(f.selector(members, [f.comparison("A", energy=request)],
        scan=f.scan_request(request)), operands={"WT": f.supplied(baseline), "A": f.supplied(variant)})


def test_exact_normalized_ties_retain_all_minimum_paths_and_original_carrier():
    first, second = calculated(ratio_scan()), calculated(ratio_scan(reorder=True))
    names = ("minimum_selected_energy", "baseline_energy_above_minimum", "lowest_energy_tie_count", "baseline_rank_start", "baseline_rank_end")
    ac, bc = f.cells(first["energy_components"]), f.cells(second["energy_components"])
    assert {n: ac[n]["value"] for n in names} == {n: bc[n]["value"] for n in names}
    assert (ac["minimum_selected_energy"]["numerator"], ac["minimum_selected_energy"]["denominator"]) == (-1.0, 3)
    assert (bc["minimum_selected_energy"]["numerator"], bc["minimum_selected_energy"]["denominator"]) == (-2.0, 6)
    assert ac["lowest_energy_tie_count"]["value"] == 2
    assert all(f"/operands/{i}/original_sheet/native_evaluation" in ac["minimum_selected_energy"]["input_paths"] for i in (0, 1))


def test_subnormal_ratios_order_exactly_even_when_returned_values_round_equal():
    # Both per_nt outputs round to zero, but their exact stored-value ratios differ.
    tiny = math.ulp(0.0)
    scan = calculated(ratio_scan(energy_b=tiny, energy_a=tiny))
    rows = {r["member_id"]: r for r in scan["members"]}
    assert rows["WT"]["energy"]["value"] == rows["A"]["energy"]["value"] == 0.0
    assert rows["A"]["exact_rank_start"]["value"] == 1
    assert rows["WT"]["exact_rank_start"]["value"] == 2
    assert scan["baseline_rank_class"] == "not_lowest"


def test_adjacent_binary64_values_never_merge_into_ties():
    scan = calculated(f.scan((1.0, math.nextafter(1.0, math.inf)), failed=False, aliases=False, tolerance=1.0))
    values = f.values(scan["energy_components"])
    assert values["equal_variant_count"] == 0 and values["within_tolerance_variant_count"] == 1
    assert [r["exact_rank_start"]["value"] for r in scan["members"]] == [1, 2]


def test_overflow_gap_is_unavailable_but_exact_ranks_survive():
    scan = calculated(f.scan((1e308, -1e308), failed=False, aliases=False))
    cells = f.cells(scan["energy_components"])
    assert cells["baseline_rank_start"]["value"] == 2
    assert cells["minimum_selected_energy"]["value"] == -1e308
    assert cells["baseline_energy_above_minimum"]["reason"] == "nonfinite_derived_value"


def test_scan_sites_have_per_site_decidable_variant_denominators_and_no_alias_weight():
    a = f.feature("WT", "G" * 10, "((....))..")
    b = f.feature("A", "A" * 10, ".((....)).")
    c = f.feature("B", "C" * 10, "((....))..")
    membership = [f.member(s) for s in (a, b, c)] + [f.absent("D"), {"member_id": "AliasA", "kind": "alias", "canonical_member_id": "A"}]
    selection = f.site(positions=[0, 1, 6])
    comparisons = [f.comparison("A", correspondence=f.complete([(i, i) for i in range(10)]), selections=[selection]),
        f.comparison("B", correspondence=f.partial([(0, 0), (1, 1)]), selections=[selection]),
        f.comparison("D", correspondence=f.complete([(i, i) for i in range(10)]), selections=[selection])]
    selected = f.selector(membership, comparisons, scan=f.scan_request(selections=["selected"]))
    sheet = populate_rna_comparison_sheet(selected, operands={"WT": f.supplied(a), "A": f.supplied(b), "B": f.supplied(c), "D": f.blank()})
    scan = calculated(sheet)
    rows = {r["baseline_index"]: f.values(r["components"], "selected") for r in scan["site_components"]}
    assert rows[0]["changed_variant_count"] == 1
    assert rows[0]["unresolved_partner_variant_count"] == rows[0]["unavailable_topology_variant_count"] == 1
    assert rows[0]["decidable_variant_count"] == 1 and rows[0]["changed_variant_fraction"] == 1
    assert rows[6]["unmapped_variant_count"] == 1
    assert scan["energy_components"] == [] and scan["baseline_rank_class"] == "not_requested"
    assert all(r["energy"] is None and r["energy_state"] == "not_requested" for r in scan["members"])


def test_scan_requires_all_and_only_exact_comparison_bindings():
    sheet = f.scan()
    full = calculate_rna_comparison_components(sheet)
    comparisons = {c["comparison_id"]: c for c in full["comparisons"]}
    for broken in ({}, {**comparisons, "extra": comparisons["compare-A"]},
            {**comparisons, "compare-A": comparisons["compare-B"]}):
        with pytest.raises(ValueError):
            calculate_rna_scan_components(sheet, pairwise_components=broken)
    forged = deepcopy(comparisons)
    forged["compare-A"]["variant_member_id"] = "B"
    with pytest.raises(ValueError):
        calculate_rna_scan_components(sheet, pairwise_components=forged)


@pytest.mark.parametrize("mutation", ["null_value", "zero_denominator", "null_numerator"])
def test_malformed_pairwise_numeric_cell_is_a_closed_input_failure(mutation):
    sheet = f.scan(normalization="per_nt")
    result = calculate_rna_comparison_components(sheet)
    supplied = {c["comparison_id"]: c for c in result["comparisons"]}
    cell = next(c for c in supplied["compare-A"]["energy"]["components"] if c["metric"] == "variant_selected_energy")
    if mutation == "null_value":
        cell["value"] = None
    elif mutation == "zero_denominator":
        cell["denominator"] = 0
    else:
        cell["numerator"] = None
    with pytest.raises(ValueError):
        calculate_rna_scan_components(sheet, pairwise_components=supplied)


def test_pairwise_question_returns_no_scan():
    sheet = f.pair()
    result = calculate_rna_comparison_components(sheet)
    assert calculate_rna_scan_components(sheet, pairwise_components={c["comparison_id"]: c for c in result["comparisons"]}) is None


@pytest.mark.parametrize("kind", ["alias_chain", "alias_cycle", "duplicate_descriptor", "duplicate_sequence"])
def test_malformed_population_cannot_reach_rank_arithmetic(kind):
    sheet = f.scan()
    q = deepcopy(sheet["selected_question"])
    if kind == "alias_chain":
        q["membership"].append({"member_id": "Alias2", "kind": "alias", "canonical_member_id": "AliasA"})
    elif kind == "alias_cycle":
        q["membership"][-1]["canonical_member_id"] = "AliasA"
    elif kind == "duplicate_descriptor":
        q["membership"][1]["saved_input"] = deepcopy(q["membership"][0]["saved_input"])
        selected = {"version": "native_rna_structure_comparison_selector_v1", "acquisition": "retained_inputs_only",
            "question": q, "parameters": sheet["parameters"], "projections": [{"projection_id": "rank", "family": "scan_energy",
                "scan_id": "scan", "metrics": ["baseline_rank_start"], "include_rank_class": True}]}
        with pytest.raises(ValueError):
            populate_rna_comparison_sheet(selected, operands={})
        return
    else:
        operands = {o["member_id"]: {k: deepcopy(o[k]) for k in ("original_sheet", "original_bundle_software", "received_failure")}
            for o in sheet["operands"] if o["state"] != "alias"}
        operands["A"] = f.supplied(f.feature("A", energy=-5.0))
        with pytest.raises(ValueError):
            f.rebuild(sheet, operands=operands)
        return
    with pytest.raises(ValueError):
        f.rebuild(sheet, question=q)
