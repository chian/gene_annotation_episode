import builtins
import importlib.util
import json
import socket
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode.rna_structure_calculations import (
    calculate_rna_topology_components, calculate_rna_pair_composition, calculate_rna_energy_components,
    calculate_rna_prediction_components, calculate_rna_feature_components,
)
from gene_annotation_episode.rna_structure_contracts import (
    PAIR_TYPES, ROW_METRICS, validate_rna_components, validate_rna_sheet,
)
from gene_annotation_episode.rna_structure_native import (
    parse_rna_native_record, parse_biomni_rna_prediction_text, populate_rna_prediction_sheet,
)

PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_rna_structure_core_2026-10-26_354"
SPEC = importlib.util.spec_from_file_location("rna_calculation_fixture_helpers", PACKET / "fixture_helpers.py")
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)
CASES = json.loads((PACKET / "topology_oracles.json").read_text())


def summary(components):
    return {cell["name"]: cell for cell in components["summary"]}


@pytest.mark.parametrize("case", CASES, ids=lambda row: row["name"])
def test_literal_numerical_oracles_and_complete_full_rows(case):
    request = F.feature_input(case["structure"], case["sequence"])
    native_record = F.native_record(request)
    sheet = F.feature_sheet(request, native=F.parsed(native_record))
    components = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    actual = summary(components)
    for name, expected in case["summary"].items():
        assert actual[name]["state"] == "present", name
        assert actual[name]["value"] == expected, name
    assert set(actual) == set(ROW_METRICS["summary"])
    for family in ("pairs", "stems", "regions"):
        for row in components[family]:
            assert [cell["name"] for cell in row["cells"]] == list(ROW_METRICS[family])
    assert validate_rna_components(components, sheet=sheet) == components
    assert actual["mfe_kcal_mol"]["state"] == "not_requested"
    assert actual["evaluated_energy_kcal_mol"]["state"] == "not_requested"
    F.retain("topology_" + case["name"], original_input=request, synthetic_native_record=native_record,
        populated_sheet=sheet, components=components, numerical_oracle=case)


def test_means_and_fractions_preserve_actual_numerators_denominators_units():
    cells = summary(calculate_rna_feature_components(F.feature_sheet(), parameters=F.PARAMETERS))
    assert (cells["paired_fraction"]["numerator"], cells["paired_fraction"]["denominator"]) == (6, 9)
    assert (cells["mean_pair_span_nt"]["numerator"], cells["mean_pair_span_nt"]["denominator"]) == (18, 3)
    assert (cells["mean_stem_pairs"]["numerator"], cells["mean_stem_pairs"]["denominator"], cells["mean_stem_pairs"]["unit"]) == (3, 1, "pairs/stem")
    assert (cells["loop_mean_unpaired_nt"]["numerator"], cells["loop_mean_unpaired_nt"]["denominator"]) == (3, 1)
    assert cells["pair_count"]["numerator"] is cells["pair_count"]["denominator"] is None
    assert cells["longest_stem_pairs"]["numerator"] is cells["longest_stem_pairs"]["denominator"] is None


def test_zero_pairs_have_zero_counts_and_explicit_unavailable_ratios():
    sheet = F.feature_sheet(F.feature_input("....", "AAAA"))
    cells = summary(calculate_rna_feature_components(sheet, parameters=F.PARAMETERS))
    for name, reason in (("mean_pair_span_nt", "zero_pair_denominator"), ("mean_stem_pairs", "zero_stem_denominator"),
        ("long_stem_fraction", "zero_stem_denominator"), ("loop_mean_unpaired_nt", "zero_closed_loop_denominator"),
        ("accepted_pair_fraction", "zero_unambiguous_pair_denominator")):
        assert cells[name]["value"] is None
        assert (cells[name]["numerator"], cells[name]["denominator"]) == (0, 0)
        assert cells[name]["reason"] == reason
    assert cells["loop_max_unpaired_nt"]["value"] is None
    assert cells["loop_max_unpaired_nt"]["numerator"] is cells["loop_max_unpaired_nt"]["denominator"] is None
    assert cells["pair_count_GC"]["state"] == "present" and cells["pair_count_GC"]["value"] == 0


def test_all_sixteen_ordered_pair_counts_and_accepted_parameter_set():
    # Sixteen consecutive supplied tiny loops, one of each 5'-ordered type.
    sequence = "AAACAGAUCACCCGCUGAGCGGGUU AUCUGUU".replace(" ", "")
    assert sequence == "AA" + "AC" + "AG" + "AU" + "CA" + "CC" + "CG" + "CU" + "GA" + "GC" + "GG" + "GU" + "UA" + "UC" + "UG" + "UU"
    request = F.feature_input("()()()()()()()()()()()()()()()()", sequence)
    sheet = F.feature_sheet(request)
    components = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    cells = summary(components)
    assert {pair: cells["pair_count_" + pair]["value"] for pair in PAIR_TYPES} == {
        "AA": 1, "AC": 1, "AG": 1, "AU": 1, "CA": 1, "CC": 1, "CG": 1, "CU": 1,
        "GA": 1, "GC": 1, "GG": 1, "GU": 1, "UA": 1, "UC": 1, "UG": 1, "UU": 1}
    assert cells["unambiguous_pair_count"]["value"] == 16
    assert cells["ambiguous_pair_count"]["value"] == 0
    assert cells["accepted_pair_count"]["value"] == 6
    assert cells["accepted_pair_fraction"]["value"] == 0.375
    F.retain("all_sixteen_pair_types", original_input=request, sheet=sheet, components=components)


@pytest.mark.parametrize("sequence,state,reason", [(None, "missing_input", "no_sequence_supplied"),
    ("", "invalid_input", "rna_empty_sequence"), ("GG!AAACCC", "invalid_input", "rna_invalid_sequence_symbol"),
    ("GGGAAACC", "incompatible", "rna_sequence_structure_length_mismatch")])
def test_sequence_failure_never_erases_valid_topology_or_invents_pair_counts(sequence, state, reason):
    request = F.feature_input(sequence=sequence)
    sheet = F.feature_sheet(request)
    components = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    cells = summary(components)
    assert cells["pair_count"]["value"] == 3
    assert cells["paired_fraction"]["value"] == 0.6666666666666666
    assert cells["pair_count_GC"]["value"] is None
    assert cells["pair_count_GC"]["state"] == state
    assert cells["accepted_pair_fraction"]["reason"] == reason
    assert cells["accepted_pair_fraction"]["denominator"] is None
    assert all(row["symbol_i"] is row["symbol_j"] is row["ordered_pair"] is row["unambiguous"] is None for row in sheet["sequence_pairs"])
    F.retain("sequence_" + reason, original_input=request, sheet=sheet, components=components)


@pytest.mark.parametrize("sequence,known,ambiguous,accepted,fraction", [
    ("NNNAAANNN", 0, 3, 0, None), ("GNGAAACNC", 2, 1, 2, 1.0), ("GUGAAACAC", 3, 0, 3, 1.0)])
def test_ambiguity_is_explicit_and_never_expanded(sequence, known, ambiguous, accepted, fraction):
    request = F.feature_input(sequence=sequence)
    sheet = F.feature_sheet(request)
    components = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    cells = summary(components)
    assert cells["unambiguous_pair_count"]["value"] == known
    assert cells["ambiguous_pair_count"]["value"] == ambiguous
    assert cells["accepted_pair_count"]["value"] == accepted
    assert cells["accepted_pair_fraction"]["value"] == fraction
    assert cells["accepted_pair_fraction"]["denominator"] == known
    F.retain("ambiguity_" + sequence, original_input=request, sheet=sheet, components=components)


@pytest.mark.parametrize("structure,reason", [("", "rna_empty_structure"), ("(]", "rna_mismatched_bracket"),
    ("([)]", "rna_crossing_pairs_unsupported"), ("...&...", "rna_invalid_structure_symbol")])
def test_invalid_or_unsupported_topology_has_no_fabricated_counts(structure, reason):
    request = F.feature_input(structure, "GGGAAACCC")
    sheet = F.feature_sheet(request)
    result = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    cells = summary(result)
    assert cells["n_nt"]["value"] is cells["pair_count"]["value"] is None
    assert cells["pair_count"]["reason"] == reason
    assert result["pairs"] == result["stems"] == result["regions"] == []
    assert sheet["analysis_sequence"]["symbol_counts"]["G"] == 3
    F.retain("invalid_topology_" + reason, original_input=request, sheet=sheet, components=result)


def test_region_cells_name_immediate_branches_and_inapplicable_sides():
    sheet = F.feature_sheet(F.feature_input("(.(...)..(...)...)", None))
    regions = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)["regions"]
    multi = {cell["name"]: cell for cell in regions[0]["cells"]}
    assert (multi["branch_count"]["value"], multi["branch_count"]["unit"]) == (2, "pairs")
    assert multi["loop_unpaired_nt"]["value"] == 6
    assert multi["five_prime_unpaired_nt"]["state"] == "incompatible"
    assert multi["five_prime_unpaired_nt"]["reason"] == "rna_region_side_not_defined"
    bulge = F.feature_sheet(F.feature_input("((.((...))))", None))
    cells = {cell["name"]: cell for cell in calculate_rna_feature_components(bulge, parameters=F.PARAMETERS)["regions"][0]["cells"]}
    assert cells["five_prime_unpaired_nt"]["value"] == 1
    assert cells["three_prime_unpaired_nt"]["value"] == 0


def test_documented_native_value_represented_in_legacy_format_is_not_a_live_run():
    sequence = "CUACGGCGCGGCGCCCUUGGCGA"
    structure = "...........((((...))))."
    raw = f"Sequence: {sequence}\nStructure: {structure}\nMinimum Free Energy: -5.00 kcal/mol\n".encode()
    native = parse_biomni_rna_prediction_text(raw, record_key="documented-value", expected_sequence=sequence)
    request = F.prediction_input(sequence, record_key="documented-value")
    sheet = populate_rna_prediction_sheet(native, record_key="documented-value", original_input=request,
        model_metadata=None, subject_binding=None)
    result = calculate_rna_prediction_components(sheet, parameters=F.PARAMETERS)
    cells = summary(result)
    assert cells["n_nt"]["value"] == 23
    assert cells["pair_count"]["value"] == 4
    assert cells["pair_count_CG"]["value"] == 3
    assert cells["pair_count_GC"]["value"] == 1
    assert cells["paired_fraction"]["value"] == 0.34782608695652173
    assert cells["external_unpaired_nt"]["value"] == 12
    assert cells["mfe_kcal_mol"]["value"] == -5.0
    assert cells["mfe_kcal_mol"]["origin"] == "native_prediction"
    assert cells["mfe_per_nt"]["value"] == -0.21739130434782608
    assert (cells["mfe_per_nt"]["numerator"], cells["mfe_per_nt"]["denominator"]) == (-5.0, 23)
    assert sheet["native_mfe"]["numeric_text"] == "-5.00"
    assert sheet["model"] is None
    assert all(cell["uncertainty"]["value"] is None for cell in result["summary"])
    F.retain("documented_numeric_prediction", qualification="Published native value; synthetic wrapper-format serialization; no live native run",
        original_input=request, raw_legacy_text=raw.decode(), native=native, sheet=sheet, components=result)


def test_evaluation_stays_separate_and_can_be_positive_or_measured_zero():
    for energy, expected_per_nt in ((2.25, 0.25), (0.0, 0.0), (-4.5, -0.5)):
        request = F.feature_input(energy_mode="viennarna_evaluate")
        record = F.native_record(request, energy=energy)
        sheet = F.feature_sheet(request, native=F.parsed(record))
        result = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
        cells = summary(result)
        assert cells["mfe_kcal_mol"]["value"] is None
        assert cells["evaluated_energy_kcal_mol"]["value"] == energy
        assert cells["evaluated_energy_kcal_mol"]["formula_id"] == "native:eval_structure"
        assert cells["evaluated_energy_per_nt"]["value"] == expected_per_nt
        assert cells["evaluated_energy_kcal_mol"]["state"] == "present"
        F.retain("synthetic_evaluation_" + str(energy), original_input=request, synthetic_native_record=record, sheet=sheet, components=result)


def test_saved_sheet_recalculation_works_with_acquisition_and_native_ports_unavailable(monkeypatch):
    original = F.feature_sheet(F.feature_input(sequence="GUGAAACAC"))
    serialized = json.dumps(original, sort_keys=True)
    saved = json.loads(serialized)
    first = deepcopy(F.PARAMETERS)
    first["pair_composition"]["accepted_ordered_pair_types"] = ["GC", "CG"]
    changed = deepcopy(first)
    changed["topology"]["long_stem_min_pairs"] = 4
    changed["pair_composition"]["accepted_ordered_pair_types"] = ["GC", "CG", "AU", "UA"]
    changed["energy"]["normalization"] = "none"

    def unavailable(*args, **kwargs):
        raise AssertionError("Acquisition/native execution is unavailable in saved-sheet recalculation")

    original_import = builtins.__import__
    def bounded_import(name, *args, **kwargs):
        if name == "RNA" or name.split(".")[-1] in ("state", "materials", "acquisition", "local_jobs", "native_lifecycle"):
            return unavailable()
        return original_import(name, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", unavailable)
        guard.setattr(builtins, "__import__", bounded_import)
        guard.setattr(socket, "create_connection", unavailable)
        guard.setattr(subprocess, "Popen", unavailable)
        guard.setattr(subprocess, "run", unavailable)
        guard.setitem(sys.modules, "RNA", None)
        before = calculate_rna_feature_components(saved, parameters=first)
        after = calculate_rna_feature_components(saved, parameters=changed)
        assert validate_rna_components(after, sheet=saved) == after
    before_cells, after_cells = summary(before), summary(after)
    assert (before_cells["long_stem_count"]["value"], after_cells["long_stem_count"]["value"]) == (1, 0)
    assert (before_cells["long_stem_fraction"]["value"], after_cells["long_stem_fraction"]["value"]) == (1.0, 0.0)
    assert before_cells["accepted_pair_fraction"]["value"] == 0.6666666666666666
    assert after_cells["accepted_pair_fraction"]["value"] == 1.0
    assert after_cells["mfe_per_nt"]["reason"] == "normalization_not_requested"
    assert json.dumps(saved, sort_keys=True) == serialized
    F.retain("offline_recalculation", saved_sheet=saved, before=before, after=after,
        disabled_ports=["file open", "RNA import", "Store/acquisition module imports", "network", "subprocess"])


def test_specialized_calculators_agree_with_named_assembled_components():
    sheet = F.feature_sheet()
    assembled = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    topology = calculate_rna_topology_components(sheet, parameters=F.PARAMETERS["topology"])
    composition = calculate_rna_pair_composition(sheet, parameters=F.PARAMETERS["pair_composition"])
    energy = calculate_rna_energy_components(sheet, parameters=F.PARAMETERS["energy"])
    assert assembled["summary"] == topology["summary"] + composition["summary"] + energy["summary"]
    assert assembled["pairs"] == topology["pairs"]


def test_saved_prediction_recalculates_without_native_or_acquisition(monkeypatch):
    request = F.prediction_input()
    record = F.native_record(request, prediction_structure="(((...)))", energy=-4.5)
    sheet = populate_rna_prediction_sheet(F.parsed(record), record_key=request["record_key"], original_input=request,
        model_metadata=None, subject_binding=None)
    saved = json.loads(json.dumps(sheet))
    changed = deepcopy(F.PARAMETERS)
    changed["topology"]["long_stem_min_pairs"] = 4
    changed["energy"]["normalization"] = "none"

    def unavailable(*args, **kwargs):
        raise AssertionError("No acquisition/native execution is allowed")
    original_import = builtins.__import__
    def bounded_import(name, *args, **kwargs):
        if name == "RNA" or name.split(".")[-1] in ("state", "materials", "acquisition", "local_jobs", "native_lifecycle"):
            return unavailable()
        return original_import(name, *args, **kwargs)
    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", unavailable)
        guard.setattr(builtins, "__import__", bounded_import)
        guard.setattr(socket, "create_connection", unavailable)
        guard.setattr(subprocess, "Popen", unavailable)
        guard.setattr(subprocess, "run", unavailable)
        guard.setitem(sys.modules, "RNA", None)
        before = calculate_rna_prediction_components(saved, parameters=F.PARAMETERS)
        after = calculate_rna_prediction_components(saved, parameters=changed)
        assert validate_rna_components(after, sheet=saved) == after
    assert summary(before)["mfe_per_nt"]["value"] == -0.5
    assert summary(after)["mfe_kcal_mol"]["value"] == -4.5
    assert summary(after)["mfe_per_nt"]["value"] is None
    assert summary(after)["mfe_per_nt"]["reason"] == "normalization_not_requested"
    assert summary(before)["long_stem_count"]["value"] == 1
    assert summary(after)["long_stem_count"]["value"] == 0
    assert saved == sheet
    F.retain("offline_prediction_recalculation", qualification="Synthetic recorded prediction; no native call",
        original_input=request, original_record=record, saved_sheet=saved, before=before, after=after)


@pytest.mark.parametrize("mutation", [
    lambda value: value["summary"][1].update(value=99),
    lambda value: value["summary"][4].update(denominator=10),
    lambda value: value["summary"][1].update(value=True),
    lambda value: value["summary"][1].update(unit="dimensionless"),
    lambda value: value["summary"].pop(),
    lambda value: value.update(calculator_version="unrecorded_formula"),
])
def test_saved_component_facts_are_revalidated_against_sheet_and_parameters(mutation):
    sheet = F.feature_sheet()
    result = calculate_rna_feature_components(sheet, parameters=F.PARAMETERS)
    mutation(result)
    with pytest.raises(ValueError, match="rna_invalid_component_schema"):
        validate_rna_components(result, sheet=sheet)
