"""Synthetic saved-sheet calculator verification, not live service evidence.

The retained examples were independently assembled in contract review 185.
Mutations below are explicit synthetic edge cases; they make no host-custody
claim and never replace the original source-executed fixtures.
"""
from copy import deepcopy
import builtins
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
import urllib.request

import pytest

from gene_annotation_episode.bvbrc_comparative_systems_calculation_contracts import (
    validate_calculation_parameters, validate_components,
)
from gene_annotation_episode.bvbrc_comparative_systems_calculators import calculate_comparative_systems_components as calculate
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256, schema, validate_shape

_FIXTURE = Path(__file__).parent / "fixtures/bvbrc_comparative_systems_calculators/saved_examples.json"


@pytest.fixture
def examples():
    return json.loads(_FIXTURE.read_text())["examples"]


def parameters(requests):
    return {"version": "bvbrc_comparative_systems_calculation_parameters_v1", "requests": requests,
            "duplicate_policy": "preserve_native_occurrences_and_deduplicate_identical_record_ids",
            "absolute_tolerance": 1e-12, "relative_tolerance": 1e-12}


def request(examples, quantity, *, supplied=False, family_kind="plfam", category=None,
            formula=None, pair=None, reference=None, component_id=None):
    if quantity.startswith("family_") or quantity.startswith("observed_family_"):
        row = deepcopy(examples["families_components"]["parameters"]["requests"][0])
        row["entity"]["family_kind"] = family_kind
        row["entity"]["family_id"] = "PLF_TEST" if family_kind == "plfam" else "PGF_TEST"
        row["family_kind"] = family_kind
        row["view_selection"]["view_id"] = family_kind
        if pair is not None:
            row["entity"] = {key: None for key in row["entity"]}
            row["entity"].update(kind="pair", comparison_id="synthetic_pair")
    else:
        index = 2 if quantity.startswith("subsystem_") or formula and formula.startswith("subsystem_") else 0
        row = deepcopy(examples["pathway_subsystem_components"]["parameters"]["requests"][index])
    row.update(component_id=component_id or quantity + (":" + category if category else ""), quantity=quantity,
               category=category, native_formula=formula, comparison_genome_ids=pair,
               reference_membership_id=reference)
    if formula:
        row["view_selection"]["view_id"] = formula.split("_", 1)[0] + "_summary"
    if supplied:
        row["view_selection"] = {"kind": "supplied_record_set", "view_id": None, "record_set_id": "later_pathway_records"}
        row["population_id"] = "later_pathway_genomes"
    return row


def one(sheet, req):
    return calculate(sheet, parameters=parameters([req]))["components"][0]


def value(component):
    return component["value"]["value"]


def add_joined_subsystem_rows(sheet):
    for original in list(sheet["association_rows"]):
        if original["table"] != "subsystems_tsv":
            continue
        row = deepcopy(original)
        row.update(document_id="subsystems", table="genes", association_id="joined_" + row["association_id"])
        for field in row["fields"]:
            field["location"].update(document_id="subsystems", table="genes",
                                      source_ref="synthetic_source_subsystems", raw_artifact_ref="synthetic_artifact_subsystems")
        sheet["association_rows"].append(row)


def supplied_kind(sheet, kind):
    """Build an explicit synthetic supplied population from saved associations."""
    record_set = sheet["supplied_record_sets"]["record_sets"][0]
    selection = sheet["supplied_record_sets"]["selection"]["record_sets"][0]
    record_set["collection"] = selection["collection"] = kind
    record_set["annotation_filter"] = selection["annotation_filter"] = "none"
    rows = [deepcopy(row) for row in sheet["association_rows"] if row["table"] == "subsystems_tsv"] if kind == "subsystem" else [deepcopy(row["association"]) for row in record_set["rows"]]
    # Keep exact repeated source occurrences, but native unique-key metadata is
    # generated for this test's distinct supplied documents.
    template = record_set["rows"][0]
    output = []
    for index, association in enumerate(rows):
        item = deepcopy(template)
        association.update(association_id="test_supplied_" + str(index), document_id=None,
                           record_set_id=record_set["record_set_id"], table="data_rows", row_ordinal=index)
        if kind == "genome_feature":
            association["identifiers"].update(pathway_id=None, ec_number=None,
                                              plfam_id="PLF_TEST" if index < 3 else None,
                                              pgfam_id="PGF_TEST" if index == 0 else None)
        key = "synthetic_record_" + str(index)
        association["identifiers"]["record_id"] = key
        item.update(native_unique_key=key, association=association, page_row_key="test/row/" + str(index),
                    duplicate_state="unique", qualification_codes=[])
        item["native_row"].update(row_index=index, native_id=key, row_key=item["page_row_key"])
        output.append(item)
    record_set["rows"] = output
    record_set["population"]["members"] = [row["native_unique_key"] for row in output]
    for field in ("raw_occurrence_count", "distinct_valid_member_count"):
        record_set["population"][field]["value"] = len(output)
    return record_set


def test_reviewed_values_and_independent_arithmetic(examples):
    for name in ("pathway_subsystem", "families", "hex_256"):
        saved = examples[name + "_sheet"]
        before = deepcopy(saved)
        expected = examples[name + "_components"]
        result = calculate(saved, parameters=expected["parameters"])
        assert saved == before
        assert result["sheet_sha256"] == canonical_sha256(saved)
        assert [value(c) for c in result["components"]] == pytest.approx([value(c) for c in expected["components"]])
    results = calculate(examples["pathway_subsystem_sheet"], parameters=examples["pathway_subsystem_components"]["parameters"])["components"]
    assert results[0]["ratio"]["numerator"]["value"] == 3
    assert results[0]["ratio"]["denominator"]["value"] == 2 * 2
    assert results[1]["ratio"]["numerator"]["value"] == 4
    assert results[1]["ratio"]["denominator"]["value"] == 3 * 3
    assert value(results[0]) == 100 * 3 / (2 * 2)
    assert value(results[1]) == 100 * 4 / (3 * 3)


def test_native_and_supplied_populations_cannot_be_swapped(examples):
    sheet = examples["pathway_subsystem_sheet"]
    req = request(examples, "pathway_retained_ec_occupancy_percent")
    req["population_id"] = "discard_and_dependence_requested"
    result = one(sheet, req)
    assert result["value"]["state"] == "incompatible"
    assert "population_incompatible" in result["qualification_codes"]
    req["population_id"] = "later_pathway_genomes"
    assert one(sheet, req)["value"]["state"] == "incompatible"


def test_family_population_sd_cv_and_overflow_independence(examples):
    sheet = examples["families_sheet"]
    cv = one(sheet, request(examples, "family_length_cv"))
    mean = sum((100, 200, 300)) / 3
    population_sd = math.sqrt(sum((v - mean) ** 2 for v in (100, 200, 300)) / 3)
    assert value(cv) == pytest.approx(population_sd / mean)
    assert cv["ratio"]["numerator"]["uncertainty"] is None
    assert cv["ratio"]["numerator"]["value"] != math.sqrt(10000)
    overflow = examples["hex_256_sheet"]
    original = deepcopy(overflow)
    calculated = calculate(overflow, parameters=examples["hex_256_components"]["parameters"])
    assert value(calculated["components"][1]) == 257 / 2
    assert overflow == original
    assert overflow["family_rows"][0]["raw_hex_counts"] == "10001"
    assert all(row["reported_occurrences"]["state"] == "incompatible" for row in overflow["family_rows"][0]["genome_counts"])


@pytest.mark.parametrize("state", ["missing", "not_measured", "failed", "truncated", "invalid", "incompatible"])
def test_native_unavailable_states_are_preserved(examples, state):
    sheet = examples["families_sheet"]
    sheet["family_rows"][0]["reported_length_population_sd"].update(state=state, value=None, origin="unavailable")
    result = one(sheet, request(examples, "family_length_cv"))
    assert result["value"]["state"] == state
    assert result["ratio"]["denominator"]["value"] == 200


@pytest.mark.parametrize("quantity", ["pathway_retained_feature_density", "subsystem_retained_feature_density"])
def test_feature_density_is_unbounded_and_occurrences_deduplicate(examples, quantity):
    sheet = examples["pathway_subsystem_sheet"]
    req = request(examples, quantity)
    assert value(one(sheet, req)) == 4 / (2 * 2)
    target = next(row for row in sheet["association_rows"] if row["table"] == ("pathways_tsv" if quantity.startswith("pathway") else "subsystems_tsv"))
    for i in range(5):
        added = deepcopy(target)
        added["association_id"] += "_extra_" + str(i)
        added["identifiers"].update(record_id="extra_" + str(i), feature_id="extra_feature_" + str(i))
        sheet["association_rows"].append(added)
    result = one(sheet, req)
    assert value(result) == 9 / 4
    assert result["ratio"]["numerator"]["value"] == 9
    assert result["value"]["unit"].startswith("feature_per_")


def test_category_singleton_counts_conflict_and_no_record(examples):
    sheet = examples["pathway_subsystem_sheet"]
    counts = {}
    for category in ("active", "likely", "inactive"):
        result = one(sheet, request(examples, "subsystem_explicit_category_genome_count", category=category))
        counts[category] = value(result)
        assert "conflicting_native_categories" in result["qualification_codes"]
        assert result["ratio"] is None
    assert counts == {"active": 0, "likely": 1, "inactive": 0}
    native_sets = {}
    for row in sheet["association_rows"]:
        if row["table"] == "subsystems_tsv":
            native_sets.setdefault(row["identifiers"]["genome_id"], set()).add(row["active_category"])
    assert sum(len(categories) > 1 for categories in native_sets.values()) == 1
    assert sheet["subsystem_rows"][0]["reported_record_genome_fraction"]["value"] == 1
    population = next(p for p in sheet["populations"] if p["population_id"] == "subsystem_native_genomes")
    population["members"].append("unrepresented_test_genome")
    population["distinct_valid_member_count"]["value"] = population["raw_occurrence_count"]["value"] = 3
    result = one(sheet, request(examples, "subsystem_explicit_category_genome_count", category="inactive"))
    assert value(result) == 0
    assert "absent_record_not_measured" in result["qualification_codes"]


@pytest.mark.parametrize("quantity,expected", [("observed_family_set_intersection_count", 1),
                                              ("observed_family_set_union_count", 1),
                                              ("observed_family_set_jaccard", 1)])
def test_native_family_sets_keep_pl_and_pg_distinct(examples, quantity, expected):
    sheet = examples["families_sheet"]
    assert value(one(sheet, request(examples, quantity, pair=["1.1", "2.1"]))) == expected
    pg = sheet["family_rows"][1]
    pg["positive_genome_ids"] = ["1.1"]
    pg["positive_genome_count_from_list"]["value"] = 1
    result = one(sheet, request(examples, quantity, family_kind="pgfam", pair=["1.1", "2.1"]))
    assert value(result) == (1 if quantity.endswith("union_count") else 0)
    if quantity.endswith("jaccard"):
        assert result["ratio"]["numerator"]["value"] == 0
        assert result["ratio"]["denominator"]["value"] == 1


def test_empty_union_and_unknown_genome_are_not_perfect_similarity(examples):
    sheet = examples["families_sheet"]
    row = sheet["family_rows"][0]
    row["positive_genome_ids"] = []
    row["positive_genome_count_from_list"]["value"] = 0
    result = one(sheet, request(examples, "observed_family_set_jaccard", pair=["1.1", "2.1"]))
    assert value(result) is None
    assert result["ratio"]["denominator"]["value"] == 0
    assert "empty_denominator" in result["qualification_codes"]
    result = one(sheet, request(examples, "observed_family_set_jaccard", pair=["1.1", "unknown_genome"]))
    assert result["value"]["state"] == "incompatible"


def test_partial_identity_keeps_valid_operands_and_unrelated_quantity(examples):
    sheet = examples["pathway_subsystem_sheet"]
    sheet["association_rows"][0]["identifiers"]["feature_id"] = None
    sheet["association_rows"][0]["identity_status"] = "partial"
    occupancy = one(sheet, request(examples, "pathway_retained_ec_occupancy_percent"))
    density = one(sheet, request(examples, "pathway_retained_feature_density"))
    assert value(occupancy) == 75
    assert density["value"]["state"] == "missing"
    assert density["ratio"]["numerator"]["value"] == 3
    assert density["ratio"]["denominator"]["value"] == 4


def test_conflicting_duplicates_only_affect_selected_dependencies(examples):
    sheet = examples["pathway_subsystem_sheet"]
    conflict = deepcopy(sheet["association_rows"][0])
    conflict["association_id"] += "_conflict"
    conflict["identifiers"]["feature_id"] = "conflicting_feature"
    sheet["association_rows"].append(conflict)
    reqs = [request(examples, "pathway_retained_feature_density"), request(examples, "pathway_record_feature_density", supplied=True)]
    results = calculate(sheet, parameters=parameters(reqs))["components"]
    assert results[0]["value"]["state"] == "incompatible"
    assert "duplicate_record_conflict" in results[0]["qualification_codes"]
    assert value(results[1]) == 5 / 9


def test_incomplete_supplied_population_keeps_native_result(examples):
    sheet = examples["pathway_subsystem_sheet"]
    sheet["supplied_record_sets"]["record_sets"][0]["population"]["completeness"] = "partial"
    sheet["supplied_record_sets"]["record_sets"][0]["page_coverage"] = "partial"
    native = one(sheet, request(examples, "pathway_retained_ec_occupancy_percent"))
    later = one(sheet, request(examples, "pathway_record_ec_occupancy_percent", supplied=True))
    assert value(native) == 75
    assert later["value"]["state"] == "missing"
    assert later["ratio"]["numerator"]["value"] == 4
    assert later["ratio"]["denominator"]["value"] == 9


def test_supplied_subsystem_and_family_quantities(examples):
    sheet = examples["pathway_subsystem_sheet"]
    supplied_kind(sheet, "subsystem")
    occupancy = one(sheet, request(examples, "subsystem_record_role_occupancy_percent", supplied=True))
    density = one(sheet, request(examples, "subsystem_record_feature_density", supplied=True))
    assert value(occupancy) == 100 * 3 / 6
    assert value(density) == 4 / 6
    family_sheet = deepcopy(examples["pathway_subsystem_sheet"])
    supplied_kind(family_sheet, "genome_feature")
    family = one(family_sheet, request(examples, "family_record_genome_occupancy", supplied=True))
    assert value(family) == 2 / 3
    for quantity, expected in (("observed_family_set_intersection_count", 1), ("observed_family_set_union_count", 1),
                               ("observed_family_set_jaccard", 1)):
        result = one(family_sheet, request(examples, quantity, supplied=True, pair=["1.1", "2.1"]))
        assert value(result) == expected


def test_reference_membership_missing_partial_empty_and_context(examples):
    original = examples["pathway_subsystem_sheet"]
    req = request(examples, "reference_component_representation", reference="synthetic_four_ECs")
    assert value(one(original, req)) == 2 / 4
    for mode in ("missing", "partial", "empty", "incompatible"):
        sheet = deepcopy(original)
        if mode == "missing":
            sheet["reference_memberships"] = []
        elif mode == "partial":
            sheet["reference_memberships"][0]["completeness"] = "partial"
        elif mode == "empty":
            sheet["reference_memberships"][0]["members"] = []
        else:
            sheet["reference_memberships"][0]["entity"]["pathway_id"] = "WRONG_PATHWAY"
        result = one(sheet, req)
        assert result["value"]["state"] != "available"
        if mode == "empty":
            assert result["ratio"]["denominator"]["value"] == 0
        if mode == "partial":
            assert result["ratio"]["numerator"]["value"] == 2
            assert result["ratio"]["denominator"]["value"] == 4


@pytest.mark.parametrize("formula", ["pathway_ec_conservation", "pathway_gene_conservation",
                                     "subsystem_role_conservation", "subsystem_gene_conservation", "subsystem_prop_active"])
def test_all_native_formula_discrepancies_and_tolerances(examples, formula):
    sheet = examples["pathway_subsystem_sheet"]
    add_joined_subsystem_rows(sheet)
    req = request(examples, "reported_formula_check", formula=formula)
    result = one(sheet, req)
    assert value(result) == 0
    assert result["ratio"] is None
    fields = {"pathway_ec_conservation": "reported_ec_conservation_percent", "pathway_gene_conservation": "reported_gene_conservation",
              "subsystem_role_conservation": "reported_role_conservation_percent", "subsystem_gene_conservation": "reported_gene_conservation",
              "subsystem_prop_active": "reported_record_genome_fraction"}
    row = sheet["pathway_rows" if formula.startswith("pathway_") else "subsystem_rows"][0]
    row[fields[formula]]["value"] += -0.125 if formula == "subsystem_prop_active" else 0.125
    params = parameters([req])
    mismatch = calculate(sheet, parameters=params)
    assert value(mismatch["components"][0]) == 0.125
    assert "native_formula_mismatch" in mismatch["components"][0]["qualification_codes"]
    previous = deepcopy(mismatch)
    params["absolute_tolerance"] = 0.125
    tolerated = calculate(sheet, parameters=params)
    assert value(tolerated["components"][0]) == 0.125
    assert "native_formula_mismatch" not in tolerated["components"][0]["qualification_codes"]
    assert mismatch == previous


def test_native_role_formula_requires_joined_rows_and_preserves_join_loss(examples):
    sheet = examples["pathway_subsystem_sheet"]
    req = request(examples, "reported_formula_check", formula="subsystem_role_conservation")
    assert one(sheet, req)["value"]["state"] == "missing"
    assert value(one(sheet, request(examples, "subsystem_retained_role_occupancy_percent"))) == 75
    add_joined_subsystem_rows(sheet)
    sheet["association_rows"] = [row for row in sheet["association_rows"] if not (
        row["document_id"] == "subsystems" and row["table"] == "genes" and row["identifiers"]["role_id"] == "r2")]
    discrepancy = one(sheet, req)
    assert value(discrepancy) == 75 - (2 / (2 * 2) * 100)
    assert "native_formula_mismatch" in discrepancy["qualification_codes"]


def test_native_zero_sentinel_and_new_empty_ratio(examples):
    sheet = examples["pathway_subsystem_sheet"]
    row = sheet["pathway_rows"][0]
    for field in ("reported_ec_token_count", "reported_genome_ec_count", "reported_ec_conservation_percent"):
        row[field]["value"] = 0
    discrepancy = one(sheet, request(examples, "reported_formula_check", formula="pathway_ec_conservation"))
    assert value(discrepancy) == 0
    sheet["association_rows"] = [r for r in sheet["association_rows"] if r["table"] != "pathways_tsv"]
    raw = next(d for d in sheet["native_documents"] if d["document"]["document_id"] == "pathway_raw")
    raw["tables"][0]["rows"] = []
    population = next(p for p in sheet["populations"] if p["population_id"] == "pathway_native_ecs")
    population["members"] = []
    population["distinct_valid_member_count"]["value"] = population["raw_occurrence_count"]["value"] = 0
    empty = one(sheet, request(examples, "pathway_retained_ec_occupancy_percent"))
    assert empty["value"]["state"] == "missing"
    assert empty["ratio"]["numerator"]["value"] == empty["ratio"]["denominator"]["value"] == 0
    assert row["reported_ec_conservation_percent"]["value"] == 0


def test_recalculation_and_saved_validation_forbid_acquisition_parsing_processes_and_io(examples, monkeypatch):
    sheet = examples["pathway_subsystem_sheet"]
    alternative = deepcopy(sheet["reference_memberships"][0])
    alternative.update(membership_id="other_saved_map", map_id="different_explicit_map", members=["1.1.1.1", "4.4.4.4"])
    sheet["reference_memberships"].append(alternative)
    original = deepcopy(sheet)
    earlier = calculate(sheet, parameters=examples["pathway_subsystem_components"]["parameters"])
    earlier_copy = deepcopy(earlier)
    def forbidden(*args, **kwargs):
        raise AssertionError("calculation attempted prohibited acquisition, parsing, model, process or IO")
    for owner, name in ((builtins, "open"), (Path, "read_bytes"), (Path, "read_text"),
                        (socket, "create_connection"), (socket, "socket"), (subprocess, "Popen"),
                        (subprocess, "run"), (os, "system"), (urllib.request, "urlopen")):
        monkeypatch.setattr(owner, name, forbidden)
    for name in ("bvbrc_comparative_systems_native", "bvbrc_comparative_systems_sheet", "bvbrc_comparative_systems_data_inputs",
                 "api_bvbrc_appservice", "api_bvbrc_data"):
        monkeypatch.setitem(sys.modules, "gene_annotation_episode." + name, SimpleNamespace(__getattr__=forbidden))
    later = calculate(sheet, parameters=examples["saved_sheet_recalculation"]["parameters"])
    assert value(later["components"][0]) == 3 / 4
    alternate = one(sheet, request(examples, "reference_component_representation", reference="other_saved_map"))
    assert value(alternate) == 1 / 2
    import gene_annotation_episode.bvbrc_comparative_systems_calculators as calculator_module
    monkeypatch.setattr(calculator_module, "calculate_comparative_systems_components", forbidden)
    assert validate_components(earlier, sheet=sheet) == earlier
    assert sheet == original
    assert earlier == earlier_copy


@pytest.mark.parametrize("mutation", ["duplicate_id", "irrelevant_selector", "wrong_view", "family_kind", "negative_tolerance", "bool_tolerance", "nan", "pair_repeated"])
def test_parameters_are_closed_explicit_and_quantity_specific(examples, mutation):
    req = request(examples, "family_returned_genome_occupancy")
    params = parameters([req])
    if mutation == "duplicate_id":
        params["requests"].append(deepcopy(req))
    elif mutation == "irrelevant_selector":
        req["category"] = "active"
    elif mutation == "wrong_view":
        req["view_selection"]["record_set_id"] = "other"
    elif mutation == "family_kind":
        req["family_kind"] = "pgfam"
    elif mutation == "negative_tolerance":
        params["absolute_tolerance"] = -1
    elif mutation == "bool_tolerance":
        params["absolute_tolerance"] = True
    elif mutation == "nan":
        params["relative_tolerance"] = float("nan")
    else:
        params["requests"] = [request(examples, "observed_family_set_jaccard", pair=["1.1", "1.1"])]
    with pytest.raises(ValueError):
        validate_calculation_parameters(params)


@pytest.mark.parametrize("mutation", ["hash", "analysis", "unit", "operand_unit", "operand_population", "pointer", "owner", "component_id", "ratio_output"])
def test_saved_component_relationship_tampering_rejected(examples, mutation):
    sheet = examples["families_sheet"]
    result = calculate(sheet, parameters=examples["families_components"]["parameters"])
    component = result["components"][0]
    if mutation == "hash":
        result["sheet_sha256"] = "0" * 64
    elif mutation == "analysis":
        result["analysis_id"] = "other_analysis"
    elif mutation == "unit":
        component["value"]["unit"] = "percent"
    elif mutation == "operand_unit":
        component["ratio"]["denominator"]["unit"] = "feature"
    elif mutation == "operand_population":
        component["ratio"]["numerator"]["population_id"] = "unrelated_population"
    elif mutation == "pointer":
        component["input_refs"][0]["pointer"] = "/missing"
    elif mutation == "owner":
        component["input_refs"][0]["owner_id"] = "other_analysis"
    elif mutation == "component_id":
        component["component_id"] = "unrequested_component"
    else:
        component["ratio"]["output"]["value"] = 0.2
    with pytest.raises(ValueError):
        validate_components(result, sheet=sheet)


def test_available_dependency_identity_cannot_change_to_another_saved_view(examples):
    sheet = examples["families_sheet"]
    result = calculate(sheet, parameters=examples["families_components"]["parameters"])
    result["parameters"]["requests"][0]["view_selection"]["view_id"] = "pgfam"
    with pytest.raises(ValueError, match="dependency_view_mismatch"):
        validate_components(result, sheet=sheet)
    result = calculate(sheet, parameters=examples["families_components"]["parameters"])
    component = result["components"][2]
    for refs in (component["input_refs"], component["ratio"]["numerator"]["input_refs"],
                 component["value"]["input_refs"], component["ratio"]["output"]["input_refs"]):
        for ref in refs:
            ref["pointer"] = ref["pointer"].replace("/reported_length_population_sd", "/reported_length_max")
    with pytest.raises(ValueError, match="native_field_mismatch"):
        validate_components(result, sheet=sheet)


def test_missing_unrelated_population_counts_do_not_remove_native_length_statistics(examples):
    sheet = examples["families_sheet"]
    population = next(p for p in sheet["populations"] if p["population_id"] == "families_native_genomes")
    population["distinct_valid_member_count"].update(state="missing", value=None, origin="unavailable")
    assert one(sheet, request(examples, "family_returned_genome_occupancy"))["value"]["state"] == "missing"
    assert value(one(sheet, request(examples, "family_length_cv"))) == pytest.approx(math.sqrt(20000 / 3) / 200)
    assert value(one(sheet, request(examples, "family_occurrences_per_positive_genome"))) == 1.5


def test_missing_family_rows_are_not_an_observed_empty_set(examples):
    sheet = examples["families_sheet"]
    sheet["family_rows"] = []
    result = one(sheet, request(examples, "observed_family_set_jaccard", pair=["1.1", "2.1"]))
    assert result["value"]["state"] == "missing"
    assert "missing_required_field" in result["qualification_codes"]


def test_wrong_original_formula_population_and_subsystem_context_are_unavailable(examples):
    sheet = examples["pathway_subsystem_sheet"]
    population = next(p for p in sheet["populations"] if p["population_id"] == "pathway_native_genomes")
    population["members"] = ["1.1"]
    population["distinct_valid_member_count"]["value"] = 1
    result = one(sheet, request(examples, "reported_formula_check", formula="pathway_ec_conservation"))
    assert result["value"]["state"] == "incompatible"
    conflict = deepcopy(sheet["subsystem_rows"][0])
    conflict["entity"]["subclass"] = "Different context"
    sheet["subsystem_rows"].append(conflict)
    result = one(sheet, request(examples, "reported_formula_check", formula="subsystem_prop_active"))
    assert result["value"]["state"] == "incompatible"


def test_relative_tolerance_and_detached_values(examples):
    sheet = examples["pathway_subsystem_sheet"]
    sheet["pathway_rows"][0]["reported_ec_conservation_percent"]["value"] = 75.75
    req = request(examples, "reported_formula_check", formula="pathway_ec_conservation")
    params = parameters([req])
    params.update(absolute_tolerance=0, relative_tolerance=0.01)
    result = calculate(sheet, parameters=params)
    assert value(result["components"][0]) == 0.75
    assert "native_formula_mismatch" not in result["components"][0]["qualification_codes"]
    result["parameters"]["relative_tolerance"] = 1
    assert params["relative_tolerance"] == 0.01
    params["relative_tolerance"] = 0.009
    assert "native_formula_mismatch" in calculate(sheet, parameters=params)["components"][0]["qualification_codes"]


def test_finite_inputs_with_unrepresentable_ratio_return_typed_invalid(examples):
    sheet = examples["families_sheet"]
    sheet["family_rows"][0]["reported_length_population_sd"]["value"] = 1e308
    sheet["family_rows"][0]["reported_length_mean"]["value"] = 1e-308
    result = one(sheet, request(examples, "family_length_cv"))
    assert result["value"]["state"] == "invalid"
    assert "nonfinite_number" in result["qualification_codes"]
    assert result["ratio"]["numerator"]["value"] == 1e308
    assert result["ratio"]["denominator"]["value"] == 1e-308


def test_every_frozen_quantity_has_an_exercised_request(examples):
    # This guards against silently implementing ratios while omitting scalar
    # counts or a separately named supplied-record measurement.
    all_quantities = set(schema("QuantityV1")["$defs"]["QuantityV1"]["enum"])
    tested = {"family_returned_genome_occupancy", "family_record_genome_occupancy", "family_occurrences_per_positive_genome", "family_length_cv",
              "pathway_retained_ec_occupancy_percent", "pathway_retained_feature_density", "pathway_record_ec_occupancy_percent", "pathway_record_feature_density",
              "subsystem_retained_role_occupancy_percent", "subsystem_retained_feature_density", "subsystem_record_role_occupancy_percent", "subsystem_record_feature_density",
              "subsystem_explicit_category_genome_count", "observed_family_set_intersection_count", "observed_family_set_union_count", "observed_family_set_jaccard",
              "reference_component_representation", "reported_formula_check"}
    assert all_quantities == tested


# These cases use the actual N parser/builder. The new joined fixture is output
# of the unchanged pinned producer on synthetic inputs (see evidence_c_review).
# Other edits below are explicitly synthetic malformed/contradictory artifacts.
_N_FIXTURES = Path(__file__).parent / "fixtures/bvbrc_comparative_systems_native"
_JOIN_WITNESS = _FIXTURE.parent / "dependency_precision/joined_metadata_subsystems_tables.json"
_FORMULAS = ("pathway_ec_conservation", "pathway_gene_conservation",
             "subsystem_role_conservation", "subsystem_gene_conservation", "subsystem_prop_active")


def dependency_sheet(*, name="pathway_subsystem_sheet", edits=None, joined_witness=False, incomplete=None):
    from gene_annotation_episode.bvbrc_comparative_systems_native import parse_comparative_systems_document
    from gene_annotation_episode.bvbrc_comparative_systems_sheet import build_comparative_systems_sheet

    options = json.loads((_N_FIXTURES / "build_inputs.json").read_text())[name]
    sources = options.pop("source_documents")
    assert set(edits or {}) <= {source["document_id"] for source in sources}
    contents = {hashlib.sha256(p.read_bytes()).hexdigest(): p.read_bytes()
                for p in (_N_FIXTURES / "source_executed_synthetic").rglob("*") if p.is_file()}
    documents = []
    for source in sources:
        content = contents[source["sha256"]]
        identifier = source["document_id"]
        if joined_witness and identifier == "subsystems":
            content = _JOIN_WITNESS.read_bytes()
        if identifier in (edits or {}):
            content = edits[identifier](content)
            source.update(basis="synthetic_fixture", producer_evidence_id=None)
            selected = next(d for d in options["document_selection"]["documents"] if d["document_id"] == identifier)
            selected["producer_evidence_id"] = None
        source.update(byte_count=len(content), sha256=hashlib.sha256(content).hexdigest())
        if identifier == incomplete:
            source["object_complete"] = "partial"
        documents.append(parse_comparative_systems_document(content, document=source,
            format_profile=source["format_profile"], producer_evidence=tuple(options["producer_evidence"])))
    return build_comparative_systems_sheet(tuple(documents), **options)


def edit_embedded_table(table, operation):
    def edit(content):
        native = json.loads(content)
        rows = list(csv.reader(io.StringIO(native[table]), delimiter="\t"))
        operation(rows)
        output = io.StringIO()
        csv.writer(output, delimiter="\t", lineterminator="\n").writerows(rows)
        native[table] = output.getvalue()
        return json.dumps(native).encode()
    return edit


def test_joined_role_formula_uses_exact_operands_despite_feature_metadata(examples):
    sheet = dependency_sheet(joined_witness=True)
    before = deepcopy(sheet)
    rows = [r for r in sheet["association_rows"] if r["document_id"] == "subsystems"
            and r["table"] == "genes" and r["identifiers"]["record_id"] == "ss_f1"]
    assert len(rows) == 2
    assert {r["identity_status"] for r in rows} == {"valid"}
    assert all("inner_join_many_to_many" in r["qualification_codes"] for r in rows)
    assert len({(r["identifiers"]["genome_id"], r["identifiers"]["role_id"]) for r in rows}) == 1
    assert len({r["identifiers"]["patric_id"] for r in rows}) == 2
    result = one(sheet, request(examples, "reported_formula_check", formula="subsystem_role_conservation"))
    assert result["value"]["state"] == "available"
    assert value(result) == abs(75 - 100 * 3 / (2 * 2)) == 0
    assert "inner_join_many_to_many" in result["qualification_codes"]
    assert "duplicate_record_conflict" not in result["qualification_codes"]
    assert sheet == before


@pytest.mark.parametrize("formula", _FORMULAS)
@pytest.mark.parametrize("defect", ["unidentified_width", "unrelated_number"])
def test_formula_ignores_only_unrelated_summary_defects(examples, formula, defect):
    subsystem = formula.startswith("subsystem")
    document, table = ("subsystems", "subsystems") if subsystem else ("pathways", "pathway")
    def malformed_other(rows):
        if defect == "unidentified_width":
            rows.append(["synthetic_unidentified_malformed_summary"])
        else:
            other = list(rows[1])
            other[rows[0].index("subsystem_id" if subsystem else "pathway_id")] = "UNRELATED_SYNTHETIC_ID"
            if subsystem:
                other[rows[0].index("subsystem_name")] = "Other synthetic subsystem"
            other[rows[0].index("genome_count")] = "not_a_number"
            rows.append(other)
    sheet = dependency_sheet(edits={document: edit_embedded_table(table, malformed_other)})
    native = next(d for d in sheet["native_documents"] if d["document"]["document_id"] == document)
    assert next(t for t in native["tables"] if t["table"] == table)["rows"][-1]["status"] != "ok"
    result = one(sheet, request(examples, "reported_formula_check", formula=formula))
    assert result["value"]["state"] == "available"
    assert value(result) == 0


@pytest.mark.parametrize("field,replacement,state", [
    ("genome_id", "2.1", "incompatible"), ("role_id", "r2", "incompatible"),
    ("feature_id", "other_feature_join_key", "incompatible"),
    ("role_id", "", "missing"), ("subsystem_id", "OTHER_SYSTEM", "incompatible"),
    ("subclass", "Other hierarchy", "incompatible"),
])
def test_joined_role_formula_rejects_required_identity_changes(examples, field, replacement, state):
    def contradict(rows):
        matches = [row for row in rows[1:] if row[rows[0].index("id")] == "ss_f1"]
        matches[-1][rows[0].index(field)] = replacement
    sheet = dependency_sheet(joined_witness=True, edits={"subsystems": edit_embedded_table("genes", contradict)})
    result = one(sheet, request(examples, "reported_formula_check", formula="subsystem_role_conservation"))
    assert result["value"]["state"] == state
    assert value(result) is None


@pytest.mark.parametrize("flag", ["identity_status", "duplicate_record_conflict"])
def test_joined_role_formula_does_not_erase_explicit_identity_failures(examples, flag):
    sheet = dependency_sheet(joined_witness=True)
    row = next(r for r in sheet["association_rows"] if r["document_id"] == "subsystems" and r["table"] == "genes")
    # An explicitly synthetic saved-sheet conflict; no assertion of native bytes.
    if flag == "identity_status":
        row["identity_status"] = "conflicting"
    else:
        row["qualification_codes"].append(flag)
    result = one(sheet, request(examples, "reported_formula_check", formula="subsystem_role_conservation"))
    assert result["value"]["state"] == "incompatible"


@pytest.mark.parametrize("quantity,document", [
    ("pathway_retained_ec_occupancy_percent", "pathway_raw"),
    ("subsystem_retained_role_occupancy_percent", "subsystem_raw"),
    ("reported_formula_check", "subsystems"),
    ("observed_family_set_jaccard", "families"),
])
def test_population_quantities_keep_unidentified_malformed_rows_unavailable(examples, quantity, document):
    name = "families_sheet" if document == "families" else "pathway_subsystem_sheet"
    edit = (edit_embedded_table("genes" if document == "subsystems" else "plfam",
                              lambda rows: rows.append(["synthetic_unidentified_row"]))
            if document in ("subsystems", "families") else lambda content: content + b"\nsynthetic_unidentified_row\n")
    if document == "families":
        # Keep the native column present while making the family unidentified.
        # N separately rejects a short family's absent hex column before C.
        def unidentified_family(rows):
            other = list(rows[1])
            other[rows[0].index("family_id")] = ""
            other[rows[0].index("genomes")] = ""
            rows.append(other)
        edit = edit_embedded_table("plfam", unidentified_family)
    sheet = dependency_sheet(name=name, edits={"families_document" if document == "families" else document: edit})
    req = request(examples, quantity, formula="subsystem_role_conservation" if document == "subsystems" else None,
                  pair=["1.1", "2.1"] if document == "families" else None)
    result = one(sheet, req)
    assert result["value"]["state"] != "available"
    assert value(result) is None


@pytest.mark.parametrize("defect", ["selected_bad_number", "duplicate_selected", "wrong_genomes", "partial_object"])
def test_formula_preserves_selected_operand_ambiguity_and_custody_failures(examples, defect):
    def change(rows):
        if defect == "selected_bad_number":
            rows[1][rows[0].index("genome_ec")] = "invalid"
        elif defect == "duplicate_selected":
            rows.append(list(rows[1]))
    edits = {"pathways": edit_embedded_table("pathway", change)}
    if defect == "wrong_genomes":
        def wrong_genomes(content):
            native = json.loads(content)
            native["genome_ids"] = None
            return json.dumps(native).encode()
        edits = {"pathways": wrong_genomes}
    sheet = dependency_sheet(edits=edits, incomplete="pathways" if defect == "partial_object" else None)
    result = one(sheet, request(examples, "reported_formula_check", formula="pathway_ec_conservation"))
    assert result["value"]["state"] != "available"
    assert value(result) is None


def test_joined_record_id_cannot_change_entity_before_selection(examples):
    def changed_entity(rows):
        row = next(r for r in reversed(rows[1:]) if r[rows[0].index("id")] == "ss_f1")
        for field, value in (("subsystem_id", "OTHER_SYSTEM"), ("subsystem_name", "Other subsystem"),
                             ("subclass", "Other subclass")):
            row[rows[0].index(field)] = value
    sheet = dependency_sheet(joined_witness=True, edits={"subsystems": edit_embedded_table("genes", changed_entity)})
    assert "identity_conflict" not in sheet["subsystem_rows"][0]["qualification_codes"]
    result = one(sheet, request(examples, "reported_formula_check", formula="subsystem_role_conservation"))
    assert result["value"]["state"] == "incompatible"
    assert "duplicate_record_conflict" in result["qualification_codes"]


def test_corrected_dependencies_recalculate_immutably_and_validate_without_calculator(examples, monkeypatch):
    def add_unrelated_and_change_report(rows):
        rows[1][rows[0].index("role_conservation")] = "75.125"
        rows.append(["synthetic_unidentified_malformed_summary"])
    sheet = dependency_sheet(joined_witness=True,
        edits={"subsystems": edit_embedded_table("subsystems", add_unrelated_and_change_report)})
    before = deepcopy(sheet)
    req = request(examples, "reported_formula_check", formula="subsystem_role_conservation")
    params = parameters([req])
    old = calculate(sheet, parameters=params)
    old_before = deepcopy(old)
    assert value(old["components"][0]) == 0.125
    assert "native_formula_mismatch" in old["components"][0]["qualification_codes"]
    changed = deepcopy(params)
    changed["absolute_tolerance"] = 0.125
    def forbidden(*args, **kwargs):
        raise AssertionError("saved recalculation or validation attempted new work")
    import gene_annotation_episode.bvbrc_comparative_systems_native as native_module
    import gene_annotation_episode.bvbrc_comparative_systems_sheet as sheet_module
    import gene_annotation_episode.bvbrc_comparative_systems_calculators as calculators
    for owner, name in ((native_module, "parse_comparative_systems_document"),
                        (sheet_module, "build_comparative_systems_sheet"),
                        (builtins, "open"), (Path, "read_bytes"), (Path, "read_text"),
                        (socket, "socket"), (socket, "create_connection"),
                        (subprocess, "run"), (subprocess, "Popen"), (urllib.request, "urlopen")):
        monkeypatch.setattr(owner, name, forbidden)
    revised = calculate(sheet, parameters=changed)
    assert value(revised["components"][0]) == 0.125
    assert "native_formula_mismatch" not in revised["components"][0]["qualification_codes"]
    monkeypatch.setattr(calculators, "calculate_comparative_systems_components", forbidden)
    monkeypatch.setattr(calculators, "_reported_formula", forbidden)
    assert validate_components(old, sheet=sheet) == old
    assert validate_components(revised, sheet=sheet) == revised
    assert sheet == before and old == old_before
