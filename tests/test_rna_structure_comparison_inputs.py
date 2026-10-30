"""Supplied-data input verification; no comparison mathematics/native execution."""
from copy import deepcopy
import json
from importlib import import_module
from pathlib import Path

import pytest

from gene_annotation_episode.rna_structure_comparison_contracts import (
    validate_rna_comparison_sheet, validate_rna_comparison_selector,
)
from gene_annotation_episode.rna_structure_comparison_inputs import (
    build_rna_correspondence, populate_rna_comparison_sheet,
)
_fixtures = import_module("verification.tool_graders_rna_comparison_inputs_2026-10-26_366.fixture_helpers")
absent, comparison, energy_request, failure, feature, member, pair_inputs, scan_request, selector, site, supplied = (
    getattr(_fixtures, name) for name in ("absent", "comparison", "energy_request", "failure", "feature", "member",
        "pair_inputs", "scan_request", "selector", "site", "supplied"))

AUTHORITY = {"kind": "parent_assignment", "source_ref": "source-alignment"}


def populate(selected, operands):
    value = populate_rna_comparison_sheet(selected, operands=operands)
    assert validate_rna_comparison_sheet(value) == value
    return value


def test_substitution_is_explicit_identity_map_and_sources_are_unchanged():
    selected, operands = pair_inputs(selections=[site(positions=[0, 6, 8])], pairs=True)
    originals = deepcopy((selected, operands))
    result = populate(selected, operands)
    correspondence = result["comparisons"][0]["correspondence"]
    assert correspondence["state"] == "valid"
    assert correspondence["baseline_to_variant"][6] == {"index": 6, "state": "matched", "counterpart_index": 6, "column": 6}
    assert result["comparisons"][0]["resolved_selections"][0]["indices"] == [0, 6, 8]
    assert (selected, operands) == originals
    assert result["operands"][0]["original_sheet"] == operands["WT"]["original_sheet"]
    result["operands"][0]["original_sheet"]["structure"]["dot_bracket"] = "changed"
    assert operands == originals[1]
    assert "all_site_rows" not in result["comparisons"][0]
    assert "energy_delta" not in result["comparisons"][0]


def test_pairwise_same_sequence_different_structures_is_allowed():
    a = feature("WT", "GGGAAAACCC", "((....))..")
    b = feature("V", "GGGAAAACCC", ".((....)).")
    selected, operands = pair_inputs(a=a, b=b, request={"kind": "identical_sequence"})
    result = populate(selected, operands)
    assert result["comparisons"][0]["correspondence"]["state"] == "valid"
    assert [r["original_sheet"]["structure"]["dot_bracket"] for r in result["operands"]] == ["((....))..", ".((....))."]


@pytest.mark.parametrize("mapping_request", [
    {"kind": "identical_sequence"},
    {"kind": "substitution_only", "substitutions": []},
    {"kind": "substitution_only", "substitutions": [{"index": 6, "baseline_symbol": "A", "variant_symbol": "U"}]},
    {"kind": "substitution_only", "substitutions": [{"index": 5, "baseline_symbol": "A", "variant_symbol": "U"}]},
    {"kind": "substitution_only", "substitutions": [{"index": 6, "baseline_symbol": "C", "variant_symbol": "U"}, {"index": 6, "baseline_symbol": "C", "variant_symbol": "U"}]},
])
def test_invalid_identity_and_substitution_manifest_retains_independent_sheets(mapping_request):
    selected, operands = pair_inputs(request=mapping_request)
    result = populate(selected, operands)
    mapping = result["comparisons"][0]["correspondence"]
    assert mapping["state"] == "invalid"
    assert mapping["request"] == mapping_request
    assert all(m["state"] == "unknown" for m in mapping["baseline_to_variant"])
    assert result["operands"][0]["original_sheet"]["topology"]["status"] == "valid"


def test_substitution_preserves_original_case_and_analysis_map():
    a = feature("WT", "gggaaaccc", normalization="uppercase_ascii")
    b = feature("V", "gggaaaucc", normalization="uppercase_ascii")
    request = {"kind": "substitution_only", "substitutions": [{"index": 6, "baseline_symbol": "c", "variant_symbol": "u"}]}
    selected, operands = pair_inputs(a=a, b=b, request=request)
    result = populate(selected, operands)
    assert result["comparisons"][0]["correspondence"]["state"] == "valid"
    assert result["operands"][0]["original_sheet"]["analysis_sequence"]["original_sequence"] == "gggaaaccc"
    assert result["operands"][0]["original_sheet"]["analysis_sequence"]["original_to_analysis_indices"] == list(range(9))


def test_complete_insertion_has_explicit_gap_and_offset_maps():
    a, b = feature(), feature("V", "UGGGAAACCC", ".(((...)))")
    columns = [{"column": 0, "baseline_index": None, "variant_index": 0}] + [
        {"column": i + 1, "baseline_index": i, "variant_index": i + 1} for i in range(9)]
    selected, operands = pair_inputs(a=a, b=b, request={"kind": "supplied_complete_alignment", "authority": AUTHORITY, "columns": columns})
    result = populate(selected, operands)
    mapping = result["comparisons"][0]["correspondence"]
    assert mapping["columns"] == columns
    assert mapping["baseline_to_variant"][0] == {"index": 0, "state": "matched", "counterpart_index": 1, "column": 1}
    assert mapping["variant_to_baseline"][0] == {"index": 0, "state": "gap", "counterpart_index": None, "column": 0}
    assert mapping["baseline_to_variant"][8]["counterpart_index"] == 9
    assert "supplied_alignment_gap" in {i["code"] for i in mapping["issues"]}


def test_complete_deletion_and_union_resolve_original_coordinates():
    a, b = feature(), feature("V", "GGGAACCC", "(((..)))")
    columns = [{"column": i, "baseline_index": i, "variant_index": None if i == 3 else i if i < 3 else i - 1} for i in range(9)]
    selected, operands = pair_inputs(a=a, b=b, request={"kind": "supplied_complete_alignment", "authority": AUTHORITY, "columns": columns}, selections=[site(positions=[2, 3, 6])])
    result = populate(selected, operands)
    inputs = result["comparisons"][0]
    assert inputs["resolved_selections"][0]["indices"] == [2, 3, 6]
    assert inputs["correspondence"]["baseline_to_variant"][3]["state"] == "gap"
    assert inputs["correspondence"]["baseline_to_variant"][6]["counterpart_index"] == 5


@pytest.mark.parametrize("mutate", [
    lambda c: c.pop(), lambda c: c.append(deepcopy(c[-1])),
    lambda c: c[0].update(column=1),
    lambda c: c[0].update(baseline_index=None, variant_index=None),
    lambda c: c[1].update(baseline_index=0), lambda c: c[1].update(variant_index=9),
])
def test_complete_alignment_coverage_order_and_double_gaps_invalid(mutate):
    columns = [{"column": i, "baseline_index": i, "variant_index": i} for i in range(9)]
    mutate(columns)
    result = build_rna_correspondence(feature(), feature("V"), request={"kind": "supplied_complete_alignment", "authority": AUTHORITY, "columns": columns})
    assert result["state"] == "invalid"
    assert result["columns"] == columns
    assert all(m["state"] == "unknown" for m in result["baseline_to_variant"])


def test_partial_map_omitted_partner_is_unknown_never_a_gap():
    request = {"kind": "supplied_partial_correspondence", "authority": AUTHORITY,
        "matches": [{"baseline_index": 0, "variant_index": 0}]}
    selected, operands = pair_inputs(request=request, selections=[site(positions=[0])])
    result = populate(selected, operands)
    mapping = result["comparisons"][0]["correspondence"]
    assert mapping["columns"] == []
    assert mapping["matches"] == request["matches"]
    assert mapping["baseline_to_variant"][8] == {"index": 8, "state": "unknown", "counterpart_index": None, "column": None}
    assert not any(m["state"] == "gap" for m in mapping["baseline_to_variant"])


@pytest.mark.parametrize("matches", [
    [{"baseline_index": 0, "variant_index": 0}, {"baseline_index": 0, "variant_index": 1}],
    [{"baseline_index": 1, "variant_index": 0}, {"baseline_index": 0, "variant_index": 1}],
    [{"baseline_index": 0, "variant_index": 9}],
])
def test_partial_map_rejects_duplicate_out_of_range_or_unordered_assertions(matches):
    result = build_rna_correspondence(feature(), feature("V"), request={"kind": "supplied_partial_correspondence", "authority": AUTHORITY, "matches": matches})
    assert result["state"] == "invalid"


def test_absent_sequence_does_not_erase_supplied_topology_correspondence():
    a, b = feature(sequence=None), feature("V", sequence=None)
    columns = [{"column": i, "baseline_index": i, "variant_index": i} for i in range(9)]
    result = build_rna_correspondence(a, b, request={"kind": "supplied_complete_alignment", "authority": AUTHORITY, "columns": columns})
    assert result["state"] == "valid"
    assert {i["code"] for i in result["issues"]} == {"original_sequence_unavailable"}
    missing = build_rna_correspondence(a, b, request={"kind": "identical_sequence"})
    assert missing["state"] == "missing_input"


def test_invalid_original_structure_retained_with_no_pairing_array():
    a, b = feature(), feature("V", structure="(((...)).")
    selected, operands = pair_inputs(a=a, b=b, request={"kind": "identical_sequence"})
    result = populate(selected, operands)
    original = result["operands"][1]["original_sheet"]
    assert original["structure"]["dot_bracket"] == "(((...))."
    assert original["topology"]["pairs"] is None
    assert "original_topology_invalid" in {i["code"] for i in result["operands"][1]["issues"]}


def test_site_interval_region_union_preserves_request_and_excludes_closing_pair():
    selection = site(positions=[3, 3, 8], intervals=[(3, 5), (4, 6)], regions=["region:2:6", "region:2:6"])
    selected, operands = pair_inputs(selections=[selection])
    result = populate(selected, operands)
    resolved = result["comparisons"][0]["resolved_selections"][0]
    assert resolved == {"selection": selection, "indices": [3, 4, 5, 8]}
    assert 2 not in resolved["indices"] and 6 not in resolved["indices"]


@pytest.mark.parametrize("selection", [site(positions=[9]), site(intervals=[(0, 10)]),
    site(intervals=[(5, 5)]), site(intervals=[(6, 4)]), site(regions=["region:missing"])])
def test_invalid_site_selection_is_qualified_whole_not_clipped(selection):
    selected, operands = pair_inputs(selections=[selection])
    result = populate(selected, operands)
    inputs = result["comparisons"][0]
    assert inputs["resolved_selections"] == [{"selection": selection, "indices": []}]
    assert any(i["code"] == "invalid_site_selection" and i["selection_id"] == "selected" for i in inputs["issues"])
    corrupt = deepcopy(result)
    corrupt["comparisons"][0]["issues"] = []
    with pytest.raises(ValueError):
        validate_rna_comparison_sheet(corrupt)


def test_valid_empty_selection_is_distinct_from_invalid():
    selected, operands = pair_inputs(selections=[site()])
    result = populate(selected, operands)
    assert result["comparisons"][0]["resolved_selections"][0]["indices"] == []
    assert not any(i["code"] == "invalid_site_selection" for i in result["comparisons"][0]["issues"])


def test_energy_only_retains_original_values_without_correspondence():
    a, b = feature(energy=-4.0), feature("V", "GGGAAAUCC", energy=-6.0, temperature=25.0)
    selected, operands = pair_inputs(a=a, b=b, energy=energy_request())
    selected["question"]["comparisons"][0]["correspondence"] = None
    selected["projections"] = [{"projection_id": "energy", "family": "energy_comparison",
        "comparison_ids": ["compare-V"], "metrics": ["energy_delta"], "include_order": True, "include_tolerance_band": False}]
    result = populate(selected, operands)
    assert result["comparisons"][0]["correspondence"] is None
    assert result["comparisons"][0]["issues"] == []
    assert [r["original_sheet"]["native_evaluation"]["value"] for r in result["operands"]] == [-4.0, -6.0]
    assert [r["original_sheet"]["model"]["effective_settings"]["temperature_c"] for r in result["operands"]] == [37.0, 25.0]
    assert result["operands"][0]["original_sheet"]["native_evaluation"]["numeric_text"] == "-4.0"


def test_scan_failure_absent_and_alias_keep_explicit_population_and_no_invented_records():
    a, b, failed = feature(), feature("A", "GGGAAAUCC"), failure()
    members = [member(a), member(b), {"member_id": "D", "kind": "received_failure", "failure": failed},
        absent("missing", "not_supplied"), absent("untested"), {"member_id": "AliasA", "kind": "alias", "canonical_member_id": "A"}]
    selected = selector(members, [comparison(k) for k in ("A", "D", "missing", "untested")], scan=scan_request())
    operands = {"WT": supplied(a), "A": supplied(b), "D": {"original_sheet": None,
        "original_bundle_software": None, "received_failure": failed},
        "missing": supplied(None), "untested": supplied(None)}
    result = populate(selected, operands)
    assert [r["member_id"] for r in result["operands"]] == ["WT", "A", "D", "missing", "untested", "AliasA"]
    assert result["operands"][2]["received_failure"] == failed
    assert result["operands"][3]["state"] == "not_supplied"
    assert result["operands"][4]["state"] == "not_tested"
    assert result["operands"][5]["canonical_member_id"] == "A"
    assert all(r["original_sheet"] is None for r in result["operands"][2:])
    assert all(r["variant_identity"] == "unverified" for r in result["operands"][2:5])
    assert result["operands"][5]["variant_identity"] == "not_applicable"


@pytest.mark.parametrize("baseline_kind", ["not_supplied", "not_tested", "received_failure"])
def test_missing_or_failed_baseline_stays_explicit(baseline_kind):
    failed, b = failure("WT"), feature("V")
    first = {"member_id": "WT", "kind": "received_failure", "failure": failed} if baseline_kind == "received_failure" else absent("WT", baseline_kind)
    selected = selector([first, member(b)], [comparison(correspondence={"kind": "identical_sequence"})])
    operands = {"WT": {**supplied(None), "received_failure": failed if baseline_kind == "received_failure" else None}, "V": supplied(b)}
    result = populate(selected, operands)
    mapping = result["comparisons"][0]["correspondence"]
    assert mapping["baseline_length_nt"] is None and mapping["variant_length_nt"] == 9
    assert mapping["state"] == "missing_input"
    assert result["operands"][0]["original_sheet"] is None


def test_scan_repeated_sequence_requires_parent_selected_representative():
    a, b = feature(), feature("V", energy=-10.0)
    selected = selector([member(a), member(b)], [comparison()], scan=scan_request())
    with pytest.raises(ValueError, match="duplicate_sequence_variant_requires_representative"):
        populate_rna_comparison_sheet(selected, operands={"WT": supplied(a), "V": supplied(b)})
    selected = selector([member(a), {"member_id": "V", "kind": "alias", "canonical_member_id": "WT"}], [], scan=scan_request())
    result = populate(selected, {"WT": supplied(a)})
    assert len(result["comparisons"]) == 0


def test_duplicate_descriptor_requires_alias_even_in_pairwise():
    a = feature()
    selected = selector([member(a), member(a, key="V")], [comparison()])
    with pytest.raises(ValueError, match="duplicate_operand_requires_alias"):
        validate_rna_comparison_selector(selected)


@pytest.mark.parametrize("aliases", [
    [{"member_id": "x", "kind": "alias", "canonical_member_id": "x"}],
    [{"member_id": "x", "kind": "alias", "canonical_member_id": "missing"}],
    [{"member_id": "x", "kind": "alias", "canonical_member_id": "y"}, {"member_id": "y", "kind": "alias", "canonical_member_id": "x"}],
    [{"member_id": "x", "kind": "alias", "canonical_member_id": "WT"}, {"member_id": "y", "kind": "alias", "canonical_member_id": "x"}],
])
def test_invalid_aliases_do_not_silently_resolve(aliases):
    selected, _ = pair_inputs()
    selected["question"]["membership"].extend(aliases)
    with pytest.raises(ValueError, match="invalid_alias"):
        validate_rna_comparison_selector(selected)


def test_alias_may_not_supply_extra_operand():
    selected, operands = pair_inputs()
    selected["question"]["membership"].append({"member_id": "alias", "kind": "alias", "canonical_member_id": "V"})
    operands["alias"] = deepcopy(operands["V"])
    with pytest.raises(ValueError):
        populate_rna_comparison_sheet(selected, operands=operands)


@pytest.mark.parametrize("field,value", [("record_key", "other"), ("operation", "predict_rna_secondary_structure"), ("mode", "mfe_prediction")])
def test_original_descriptor_associations_must_match(field, value):
    selected, operands = pair_inputs()
    selected["question"]["membership"][0]["saved_input"][field] = value
    with pytest.raises(ValueError):
        populate_rna_comparison_sheet(selected, operands=operands)


def test_missing_selected_saved_sheet_is_host_failure_not_empty_scientific_sheet():
    selected, operands = pair_inputs()
    operands["WT"]["original_sheet"] = None
    with pytest.raises(ValueError, match="retained_sheet_missing"):
        populate_rna_comparison_sheet(selected, operands=operands)


@pytest.mark.parametrize("mutation", [
    lambda s: s["comparisons"][0]["resolved_selections"][0]["indices"].append(8),
    lambda s: s["comparisons"][0]["correspondence"]["baseline_to_variant"][0].update(counterpart_index=1),
    lambda s: s["operands"][0].update(canonical_member_id="V"),
    lambda s: s["operands"].reverse(),
    lambda s: s["scan_request"].update(scan_id="forged") if s["scan_request"] else s.update(scan_request={}),
])
def test_saved_input_relationships_reject_forged_maps_and_selections(mutation):
    selected, operands = pair_inputs(selections=[site(positions=[0])])
    result = populate(selected, operands)
    mutation(result)
    with pytest.raises(ValueError):
        validate_rna_comparison_sheet(result)


def test_all_eight_plan_hand_examples_are_input_cases_only(tmp_path):
    cases = json.loads((Path(__file__).parent / "fixtures/rna_structure_comparison_inputs_366/hand_examples.json").read_text())["examples"]
    retained = []
    for case in cases:
        number = case["number"]
        energy = energy_request(case.get("tolerance")) if "energies" in case else None
        if number in (5, 8):
            names = case["members"][:len(case["energies"])]
            sequences = ["GGGAAACCC", "GGGAAAUCC", "GGGUAACCC", "GGGAAACCU"]
            sheets = [feature(k, sequences[i], energy=case["energies"][i]) for i, k in enumerate(names)]
            members = [member(s) for s in sheets]
            operands = {s["record_key"]: supplied(s) for s in sheets}
            if number == 5:
                failed = failure("D")
                members.extend([{"member_id": "D", "kind": "received_failure", "failure": failed}, {"kind": "alias", **case["alias"]}])
                operands["D"] = {**supplied(None), "received_failure": failed}
            selected = selector(members, [comparison(m["member_id"], energy=energy) for m in members if m["kind"] != "alias" and m["member_id"] != "WT"], scan=scan_request(energy))
        else:
            energies = case.get("energies", [None, None])
            temperatures = case.get("temperatures", [37.0, 37.0])
            a = feature("WT", case["baseline_sequence"], case["baseline_structure"], energy=energies[0], temperature=temperatures[0])
            b = feature("V", case["variant_sequence"], case["variant_structure"], energy=energies[1], temperature=temperatures[1])
            request = {"kind": "substitution_only", "substitutions": [{"index": i, "baseline_symbol": x, "variant_symbol": y} for i, (x, y) in enumerate(zip(case["baseline_sequence"], case["variant_sequence"])) if x != y]}
            if number == 3:
                request = {"kind": "supplied_complete_alignment", "authority": AUTHORITY, "columns": [{"column": 0, "baseline_index": None, "variant_index": 0}] + [{"column": i + 1, "baseline_index": i, "variant_index": i + 1} for i in range(9)]}
            if number == 4:
                request = {"kind": "supplied_complete_alignment", "authority": AUTHORITY, "columns": [{"column": i, "baseline_index": i, "variant_index": None if i == 3 else i if i < 3 else i - 1} for i in range(9)]}
            if number == 7:
                request = {"kind": "supplied_partial_correspondence", "authority": AUTHORITY, "matches": case["matches"]}
            selected, operands = pair_inputs(a=a, b=b, request=request,
                selections=[site(positions=case.get("selected_positions", range(len(case["baseline_sequence"]))))], energy=energy, pairs=True)
        result = populate(selected, operands)
        assert all("all_pair_rows" not in c and "all_site_rows" not in c for c in result["comparisons"])
        retained.append({"example": number, "selector": selected, "sheet": result})
    (tmp_path / "all_eight_input_examples.json").write_text(json.dumps(retained, indent=2))
    assert [row["example"] for row in retained] == list(range(1, 9))
