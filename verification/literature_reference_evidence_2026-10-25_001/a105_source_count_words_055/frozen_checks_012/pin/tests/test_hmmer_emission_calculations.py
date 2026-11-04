"""Independently checkable numerical answers, partial data and pure replay."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_emission_calculations import calculate_hmmemit_components
from gene_annotation_episode.hmmer_emission_data import populate_hmmemit_sheet
from test_hmmer_emission_data import NATIVE, arguments, make_sheet


def rows(result, kind):
    return [r for r in result["rows"] if r["kind"] == kind]


def value(row, field):
    return row[field]["value"]


def check(result, code):
    return next(c["state"] for c in result["checks"] if c["code"] == code)


@pytest.mark.parametrize("style,expected", [("core", [12, 12, 12]), ("profile_local", [15, 72, 39]), ("profile_unilocal", [85, 31, 21]), ("profile_glocal", [92, 37, 30]), ("profile_uniglocal", [100, 31, 17])])
def test_retained_native_length_populations(style, expected):
    result = calculate_hmmemit_components(make_sheet(style))
    assert not result["issues"]
    generated = rows(result, "generated_record")
    assert [value(r, "length") for r in generated] == expected
    model, = rows(result, "model")
    assert value(model, "captured_sample_count") == 3
    assert value(model, "total_length") == sum(expected)
    assert value(model, "minimum_length") == min(expected)
    assert value(model, "maximum_length") == max(expected)
    assert value(model, "mean_length") == sum(expected)/3
    assert value(model, "selected_N") == 3
    assert value(model, "input_model_length") == 12
    assert value(model, "count_difference") == 0
    assert check(result, "sample_population_count") == "pass"
    if style.startswith("profile"):
        assert value(model, "configured_expected_length") == 20
        assert all(value(r, "length") != 20 for r in generated)
    assert all(r["model_alignment"]["state"] == "missing" for r in generated)


def test_native_alignment_width_occupancy_and_coordinates():
    result = calculate_hmmemit_components(make_sheet("alignment"))
    assert not result["issues"]
    alignment, = rows(result, "alignment")
    assert value(alignment, "alignment_width") == 12
    assert value(alignment, "rf_match_column_count") == 12
    assert value(alignment, "captured_row_count") == 3
    assert [value(c, "occupancy") for c in alignment["match_columns"]] == [3]*12
    assert [value(c, "occupancy_fraction") for c in alignment["match_columns"]] == [1]*12
    assert [value(c, "model_position") for c in alignment["match_columns"]] == list(range(1, 13))
    assert [value(c, "residue_position") for c in alignment["row_coordinates"][0]["columns"]] == list(range(1, 13))
    assert check(result, "rf_matches_model_length") == "pass"


def test_alignment_gaps_use_ungapped_lengths_and_rf_sample_denominator():
    text = b"# STOCKHOLM 1.0\ntiny_protein-sample1 AC-DEF\ntiny_protein-sample2 A.-D-F\n#=GC RF xx.xxx\n//\n"
    result = calculate_hmmemit_components(make_sheet("alignment", output=text, settings={"-N": 2}))
    generated = rows(result, "generated_record")
    assert [value(r, "length") for r in generated] == [5, 3]
    assert [value(r, "gap_count") for r in generated] == [1, 3]
    alignment, = rows(result, "alignment")
    assert value(alignment, "alignment_width") == 6
    assert [value(c, "occupancy") for c in alignment["match_columns"]] == [2, 1, 2, 1, 2]
    assert [value(c, "occupancy_fraction") for c in alignment["match_columns"]] == [1, 0.5, 1, 0.5, 1]
    assert check(result, "rf_matches_model_length") == "fail"
    assert all(c["model_position"]["state"] == "incompatible" for c in alignment["match_columns"])
    assert [value(c, "residue_position") for c in alignment["row_coordinates"][1]["columns"]] == [1, None, None, 2, None, 3]


@pytest.mark.parametrize("style,expected", [("consensus", "ACDEFGHIKLMN"), ("fancy", "ACDExGHIKLMN")])
def test_native_consensus_full_positions_and_exact_mismatch(style, expected):
    result = calculate_hmmemit_components(make_sheet(style))
    consensus, = rows(result, "consensus")
    assert consensus["expected_sequence"] == expected
    assert consensus["actual_sequence"] == expected
    assert value(consensus, "mismatch_count") == 0
    assert value(consensus, "certain_mismatch_count") == 0
    assert value(consensus, "ambiguous_position_count") == 0
    assert check(result, "consensus_agreement") == "pass"
    assert len(consensus["positions"]) == 12
    assert value(consensus["positions"][4], "maximum_probability") == pytest.approx(0.6666634054134197)
    assert len(consensus["positions"][4]["probabilities"]) == 20


def test_saved_sheet_changed_thresholds_recalculate_without_external_effects(monkeypatch):
    import builtins
    import socket
    import subprocess
    original = make_sheet("fancy")
    saved = json.loads(json.dumps(original, allow_nan=False))
    def forbidden(*args, **kwargs):
        raise AssertionError("saved sheet replay attempted I/O/native/network")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    changed = calculate_hmmemit_components(saved, parameters={"consensus_thresholds": {"minl": 0.6, "minu": 0.9}, "probability_rounding_tolerance": 1e-5})
    consensus, = rows(changed, "consensus")
    assert consensus["expected_sequence"] == "ACDEfGHIKLMN"
    assert consensus["actual_sequence"] == "ACDExGHIKLMN"
    assert value(consensus, "mismatch_count") == 1
    assert value(consensus, "certain_mismatch_count") == 1
    assert check(changed, "consensus_agreement") == "fail"
    assert saved == original


def test_near_threshold_does_not_falsely_prove_exact_consensus():
    result = calculate_hmmemit_components(make_sheet("fancy"), parameters={"consensus_thresholds": {"minl": 2/3, "minu": 0.9}, "probability_rounding_tolerance": 1e-5})
    consensus, = rows(result, "consensus")
    assert value(consensus, "mismatch_count") == 0
    assert value(consensus, "ambiguous_position_count") == 1
    assert consensus["positions"][4]["near_threshold"]
    assert consensus["positions"][4]["possible_symbols"] == ["f", "x"]
    assert check(result, "consensus_agreement") == "unknown"


def test_synthetic_tie_uses_first_native_alphabet_symbol_and_flags_uncertainty():
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes().replace(b"0.40547", b"0.69315").replace(b"1.09861", b"0.69315")
    result = calculate_hmmemit_components(make_sheet("consensus", model=model))
    consensus, = rows(result, "consensus")
    assert consensus["expected_sequence"] == "ACDEFGHIKLMN"
    assert consensus["positions"][4]["maximum_symbols"] == ["F", "Y"]
    assert consensus["positions"][4]["near_tie"]
    assert check(result, "consensus_agreement") == "unknown"


@pytest.mark.parametrize("style,symbol", [("consensus", "X"), ("fancy", "x")])
def test_masked_state_has_native_unknown_symbol(style, symbol):
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes().replace(b"MM    no", b"MM    yes").replace(b"5 F x - -", b"5 F x m -")
    output = f">tiny_protein-consensus\nACDE{symbol}GHIKLMN\n".encode()
    result = calculate_hmmemit_components(make_sheet(style, model=model, output=output))
    consensus, = rows(result, "consensus")
    assert consensus["expected_sequence"] == "ACDE"+symbol+"GHIKLMN"
    assert consensus["positions"][4]["masked"]
    assert check(result, "consensus_agreement") == "pass"


@pytest.mark.parametrize("alphabet,sequence,ambiguous", [("amino", "ACxbJOu", 3), ("dna", "AcgTNry", 3), ("rna", "AcgUNry", 3)])
def test_alphabet_symbol_counts_case_and_ambiguity_denominator(alphabet, sequence, ambiguous):
    model = (NATIVE / f'hmmbuild_{"protein" if alphabet == "amino" else alphabet}/profile.hmm').read_bytes()
    name = next(line.split()[1] for line in model.decode().splitlines() if line.startswith("NAME"))
    sheet = make_sheet(model=model, output=f">{name}-sample1\n{sequence}\n".encode(), settings={"-N": 1})
    result = calculate_hmmemit_components(sheet)
    generated, = rows(result, "generated_record")
    assert value(generated, "length") == 7
    assert value(generated, "ambiguous_residue_count") == ambiguous
    assert value(generated, "ambiguous_fraction") == ambiguous/7
    assert sum(c["value"] for c in generated["symbol_counts"].values()) == 7


def test_missing_selected_n_is_not_default_one():
    result = calculate_hmmemit_components(make_sheet(settings={}))
    model, = rows(result, "model")
    assert value(model, "captured_sample_count") == 3
    assert model["selected_N"]["state"] == "missing"
    assert model["count_difference"]["state"] == "missing"
    assert check(result, "sample_population_count") == "unknown"


def test_missing_thresholds_remain_unknown_and_explicit_null_overrides_settings():
    for sheet, parameters in [(make_sheet("fancy", settings={}), None), (make_sheet("fancy"), {"consensus_thresholds": None})]:
        result = calculate_hmmemit_components(sheet, parameters=parameters)
        consensus, = rows(result, "consensus")
        assert consensus["expected_sequence"] is None
        assert consensus["mismatch_count"]["state"] == "missing"
        assert check(result, "consensus_agreement") == "unknown"


def test_complete_empty_population_zero_diff_vs_missing_unknown():
    empty = calculate_hmmemit_components(make_sheet(output=b""))
    model, = rows(empty, "model")
    assert value(model, "captured_sample_count") == 0
    assert value(model, "total_length") == 0
    assert value(model, "count_difference") == -3
    assert model["mean_length"]["state"] == "missing"
    assert check(empty, "sample_population_count") == "fail"
    args = arguments()
    args["outputs"] = {}
    missing = calculate_hmmemit_components(populate_hmmemit_sheet(**args))
    model, = rows(missing, "model")
    assert model["captured_sample_count"]["state"] == "missing"
    assert value(model, "captured_sample_count") is None


def test_partial_capture_count_is_observed_and_completeness_unknown():
    result = calculate_hmmemit_components(make_sheet(output=b">tiny_protein-sample1\nAC\n", completeness="partial"))
    model, = rows(result, "model")
    assert value(model, "captured_sample_count") == 1
    assert value(model, "count_difference") == -2
    assert check(result, "sample_population_count") == "unknown"
    assert model["total_length"]["state"] == "incomplete"


def test_duplicate_records_cannot_manufacture_model_sample_count():
    result = calculate_hmmemit_components(make_sheet(output=b">tiny_protein-sample1\nAC\n>tiny_protein-sample1\nAD\n", settings={"-N": 2}))
    assert len(rows(result, "generated_record")) == 2
    model, = rows(result, "model")
    assert model["captured_sample_count"]["state"] == "incompatible"
    assert value(model, "captured_sample_count") is None


@pytest.mark.parametrize("mutation", ["key", "sequence", "locator", "digest", "association", "model_key"])
def test_saved_identity_coordinate_sequence_mutation_rejected(mutation):
    sheet = make_sheet()
    row = sheet["output_records"][0]
    if mutation == "key":
        row["record_key"] = "forged"
    elif mutation == "sequence":
        row["sequence"] = "AAAA"
    elif mutation == "locator":
        row["locator"]["byte_end"] = 1000000
    elif mutation == "digest":
        sheet["artifact_occurrences"][1]["sha256"] = "0"*64
    elif mutation == "association":
        sheet["associations"][0]["model_record_key"] = "wrong"
    elif mutation == "model_key":
        sheet["model_extraction"]["records"][0]["record_key"] = "wrong"
    result = calculate_hmmemit_components(sheet)
    assert result["issues"]
    assert not any(c["code"] == "sample_population_count" and c["state"] == "pass" for c in result["checks"])


@pytest.mark.parametrize("parameters", [{"probability_rounding_tolerance": -1}, {"probability_rounding_tolerance": float("nan")}, {"consensus_thresholds": {"minl": 0.9}}, {"consensus_thresholds": {"minl": 0.1, "minu": 2}}, {"extra": 1}])
def test_invalid_parameters_are_structured(parameters):
    result = calculate_hmmemit_components(make_sheet(), parameters=parameters)
    assert result["issues"][0]["code"] == "parameters_invalid"
    assert not result["rows"]


@pytest.mark.parametrize("alphabet,sequence", [("dna", "ACGTACGTACGT"), ("rna", "ACGUACGUACGU")])
def test_nucleotide_consensus_from_retained_full_model(alphabet, sequence):
    model = (NATIVE / f"hmmbuild_{alphabet}/profile.hmm").read_bytes()
    result = calculate_hmmemit_components(make_sheet("consensus", model=model,
        output=f">tiny_{alphabet}-consensus\n{sequence}\n".encode()))
    consensus, = rows(result, "consensus")
    assert consensus["expected_sequence"] == sequence
    assert check(result, "consensus_agreement") == "pass"
    assert all(len(p["probabilities"]) == 4 for p in consensus["positions"])


def test_partial_model_positions_do_not_create_a_padded_full_consensus():
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes().split(b"      5 ")[0]
    result = calculate_hmmemit_components(make_sheet("consensus", model=model))
    consensus, = rows(result, "consensus")
    assert len(consensus["positions"]) == 4
    assert consensus["expected_sequence"] is None
    assert consensus["mismatch_count"]["state"] == "incomplete"
    assert check(result, "consensus_agreement") == "unknown"


def test_underflow_is_not_zero_and_does_not_prove_consensus():
    model = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes().replace(b"0.40547", b"1000.00")
    result = calculate_hmmemit_components(make_sheet("consensus", model=model))
    consensus, = rows(result, "consensus")
    assert consensus["positions"][4]["probabilities"][4]["probability"]["state"] == "nonfinite"
    assert consensus["positions"][4]["probabilities"][4]["probability"]["value"] is None
    assert consensus["expected_sequence"] is None
    assert check(result, "consensus_agreement") == "unknown"


@pytest.mark.parametrize("change", ["rf", "fragment", "raw_value"])
def test_saved_native_annotation_and_sequence_relationships_checked(change):
    sheet = make_sheet("alignment")
    if change == "rf":
        sheet["output_records"][0]["native"]["column_annotations"]["RF"]["text"] = "............"
    elif change == "fragment":
        row = sheet["output_records"][1]
        row["fragments"][0]["value"] = "AAAAAAAAAAAA"
        row["sequence"] = "AAAAAAAAAAAA"
    else:
        native = next(r for r in sheet["native_rows"] if r["kind"] == "sequence")
        native["value"] = "AAAAAAAAAAAA"
        row = sheet["output_records"][1]
        row["fragments"][0]["value"] = "AAAAAAAAAAAA"
        row["sequence"] = "AAAAAAAAAAAA"
    result = calculate_hmmemit_components(sheet)
    assert result["issues"]
    assert check(result, "alignment_geometry") == "fail"


def test_fasta_gap_does_not_become_native_model_alignment():
    result = calculate_hmmemit_components(make_sheet(output=b">tiny_protein-sample1\nAC-D\n", settings={"-N": 1}))
    generated, = rows(result, "generated_record")
    assert value(generated, "length") == 3
    assert value(generated, "gap_count") == 1
    assert generated["length"]["state"] == "incomplete"
    assert generated["model_alignment"]["state"] == "missing"


def test_partial_capture_cannot_prove_full_consensus_agreement():
    result = calculate_hmmemit_components(make_sheet("consensus", completeness="partial"))
    consensus, = rows(result, "consensus")
    assert consensus["actual_sequence"] == "ACDEFGHIKLMN"
    assert value(consensus, "mismatch_count") == 0
    assert consensus["mismatch_count"]["state"] == "incomplete"
    assert value(consensus, "certain_mismatch_count") is None
    assert check(result, "consensus_agreement") == "unknown"
    assert check(result, "consensus_length") == "unknown"


def test_one_native_path_retained_as_stdout_and_generated_alignment_uses_occurrences():
    args = arguments("alignment")
    args["outputs"]["stdout"][0]["occurrence"]["artifact_ref"] = args["outputs"]["generated_alignment"][0]["occurrence"]["artifact_ref"]
    result = calculate_hmmemit_components(populate_hmmemit_sheet(**args))
    assert not result["issues"]
    assert check(result, "alignment_geometry") == "pass"
