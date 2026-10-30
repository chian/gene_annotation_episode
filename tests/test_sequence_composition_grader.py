"""Hand-checkable composition/FASTQ fixtures; no biological function inference."""
from copy import deepcopy
import io
import json
import math
import sys

from Bio import SeqIO
import pytest

import gene_annotation_episode.sequence_composition_grader as grader
from gene_annotation_episode.material_parsing import records


def codes(value):
    return {issue["code"] for issue in value["issues"]}


def test_dna_filled_example_separates_native_counts_and_calculated_quantities():
    result = grader.grade_sequence_composition("acgN", molecule="dna", quality="!+5?", quality_encoding="phred33")
    sheet, scores = result["sheet"], result["scores"]
    assert sheet["sequence"] == "acgN"
    assert sheet["quality"] == "!+5?"
    assert sheet["molecule"] == "dna"
    assert sheet["length"] == scores["length"] == 4
    assert sheet["symbol_counts"] == scores["symbol_counts"] == {"A": 1, "C": 1, "G": 1, "N": 1}
    assert sheet["composition"] == {"unambiguous_nucleotide_count": 3, "ambiguous_symbol_count": 1,
                                     "gc_count": 2, "gc_denominator": 3, "invalid_symbol_count": 0}
    assert sheet["quality_measurements"]["native_score_distribution"] == [
        {"native_score": score, "count": 1} for score in (0, 10, 20, 30)]
    assert "mean_phred" not in sheet and "quality_thresholds" not in sheet
    assert scores["status"] == "complete"
    assert scores["unambiguous_nucleotide_count"] == 3
    assert scores["ambiguous_symbol_count"] == 1
    assert scores["ambiguity_fraction"] == 0.25
    assert scores["gc_count"] == 2 and scores["gc_denominator"] == 3
    assert scores["gc_fraction"] == pytest.approx(2 / 3)
    assert scores["quality_observation_count"] == 4
    assert scores["mean_phred"] == 15.0
    assert scores["expected_error_count"] == pytest.approx(1.111)
    assert scores["mean_error_probability"] == pytest.approx(0.27775)
    assert scores["mean_error_probability"] != pytest.approx(10 ** (-scores["mean_phred"] / 10))
    assert scores["quality_thresholds"] == [
        {"phred_threshold": 20, "count_at_or_above": 2, "fraction_at_or_above": 0.5, "denominator": 4},
        {"phred_threshold": 30, "count_at_or_above": 1, "fraction_at_or_above": 0.25, "denominator": 4}]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("molecule,sequence,unambiguous,ambiguous,gc,denominator", [
    ("dna", "ACGTRYSWKMBDHVN", 4, 11, 2, 4),
    ("rna", "ACGURYSWKMBDHVN", 4, 11, 2, 4),
    ("rna", "ggcuuN", 5, 1, 3, 5),
    ("protein", "ACGT", None, 0, None, None),
    ("protein", "ABXZWJOu*", None, 4, None, None),
    ("unspecified", "ACGT", None, None, None, None),
    ("dna", "NRY", 0, 3, 0, 0),
    ("dna", "AT", 2, 0, 0, 2),
])
def test_declared_molecule_controls_composition(molecule, sequence, unambiguous, ambiguous, gc, denominator):
    scores = grader.grade_sequence_composition(sequence, molecule=molecule)["scores"]
    assert scores["length"] == len(sequence)
    assert scores["unambiguous_nucleotide_count"] == unambiguous
    assert scores["ambiguous_symbol_count"] == ambiguous
    assert scores["gc_count"] == gc
    assert scores["gc_denominator"] == denominator
    assert scores["gc_fraction"] == (gc / denominator if denominator else None)
    assert scores["ambiguity_fraction"] == (ambiguous / len(sequence) if ambiguous is not None else None)
    assert scores["quality_observation_count"] is None
    assert scores["expected_error_count"] is None


@pytest.mark.parametrize("molecule,sequence", [("dna", "ACGTU N-?ß"), ("rna", "ACGUT N-?ß")])
def test_invalid_symbols_preserve_known_counts_and_actual_denominators(molecule, sequence):
    result = grader.grade_sequence_composition(sequence, molecule=molecule)
    sheet, scores = result["sheet"], result["scores"]
    assert sheet["sequence"] == sequence
    assert sheet["length"] == 10
    assert sheet["symbol_counts"]["ß"] == 1  # Unicode uppercase would invent two S symbols.
    assert sheet["composition"]["invalid_symbol_count"] == 5
    assert scores["unambiguous_nucleotide_count"] == 4
    assert scores["ambiguous_symbol_count"] == 1
    assert scores["ambiguity_fraction"] == 0.1
    assert scores["denominators"]["ambiguity_fraction"] == 10
    assert scores["gc_fraction"] == 0.5
    assert "unexpected_symbol_for_declared_molecule" in codes(sheet)


@pytest.mark.parametrize("molecule", ["dna", "rna", "protein", "unspecified"])
def test_empty_sequence_has_zero_counts_and_unknown_ratios(molecule):
    absent = grader.grade_sequence_composition("", molecule=molecule)["scores"]
    assert absent["length"] == 0 and absent["symbol_counts"] == {}
    assert absent["ambiguity_fraction"] is None and absent["gc_fraction"] is None
    assert absent["quality_observation_count"] is None and absent["expected_error_count"] is None
    present = grader.grade_sequence_composition("", molecule=molecule, quality="", quality_encoding="phred33")["scores"]
    assert present["quality_observation_count"] == 0
    assert present["expected_error_count"] == 0.0
    assert present["mean_phred"] is None and present["mean_error_probability"] is None
    assert all(row["count_at_or_above"] == 0 and row["fraction_at_or_above"] is None
               and row["denominator"] == 0 for row in present["quality_thresholds"])


@pytest.mark.parametrize("encoding", [None, "unspecified", "phred33", "phred64", "solexa64", "fastq"])
def test_missing_quality_is_not_zero_error_or_perfect_quality(encoding):
    result = grader.grade_sequence_composition("ACGT", molecule="dna", quality_encoding=encoding)
    assert result["sheet"]["quality"] is None
    assert result["sheet"]["quality_encoding"] == encoding
    assert result["sheet"]["quality_measurements"]["status"] == "not_supplied"
    for key in ("quality_observation_count", "mean_phred", "mean_error_probability", "expected_error_count"):
        assert result["scores"][key] is None
    assert result["scores"]["gc_fraction"] == 0.5


@pytest.mark.parametrize("encoding,status,code", [
    (None, "encoding_unknown", "quality_encoding_not_declared"),
    ("unspecified", "encoding_unknown", "quality_encoding_not_declared"),
    ("fastq", "encoding_unsupported", "quality_encoding_unsupported"),
    ("phred+33", "encoding_unsupported", "quality_encoding_unsupported"),
    ("PHRED33", "encoding_unsupported", "quality_encoding_unsupported"),
])
def test_encoding_is_never_guessed_or_aliased(encoding, status, code):
    result = grader.grade_sequence_composition("ACGT", molecule="unspecified", quality="IIII", quality_encoding=encoding)
    assert result["sheet"]["quality"] == "IIII"
    assert result["sheet"]["quality_measurements"]["status"] == status
    assert code in codes(result["sheet"])
    assert result["scores"]["quality_observation_count"] is None
    assert result["scores"]["mean_phred"] is None
    assert result["scores"]["gc_fraction"] is None
    assert all(row["count_at_or_above"] is None and row["denominator"] is None
               for row in result["scores"]["quality_thresholds"])


@pytest.mark.parametrize("encoding,quality", [("phred33", "!+5?"), ("phred64", "@JT^")])
def test_phred_encodings_have_same_unrounded_numerical_meaning(encoding, quality):
    result = grader.grade_sequence_composition("ACGT", molecule="dna", quality=quality, quality_encoding=encoding)
    assert result["scores"]["mean_phred"] == 15
    assert result["scores"]["expected_error_count"] == pytest.approx(1.111)
    assert [row["phred"] for row in result["scores"]["quality_components"]] == [0, 10, 20, 30]


def test_solexa_preserves_negative_native_score_and_uses_odds_conversion():
    result = grader.grade_sequence_composition("ACG", molecule="dna", quality=";@J", quality_encoding="solexa64",
                                               quality_thresholds=(0, 1, 2, 3, 10, 11))
    assert [row["native_score"] for row in result["sheet"]["quality_measurements"]["native_score_distribution"]] == [-5, 0, 10]
    scores = result["scores"]
    probabilities = [1 / (1 + 10 ** -0.5), 0.5, 1 / 11]
    phred = [10 * math.log10(1 + 10 ** -0.5), 10 * math.log10(2), 10 * math.log10(11)]
    assert [row["error_probability"] for row in scores["quality_components"]] == pytest.approx(probabilities)
    assert [row["phred"] for row in scores["quality_components"]] == pytest.approx(phred)
    assert scores["mean_phred"] == pytest.approx(sum(phred) / 3)
    assert scores["expected_error_count"] == pytest.approx(sum(probabilities))
    assert scores["mean_error_probability"] == pytest.approx(sum(probabilities) / 3)
    assert [row["count_at_or_above"] for row in scores["quality_thresholds"]] == [3, 3, 2, 2, 1, 0]


@pytest.mark.parametrize("encoding,native_format,first,last,native_key", [
    ("phred33", "fastq-sanger", 33, 126, "phred_quality"),
    ("phred64", "fastq-illumina", 64, 126, "phred_quality"),
    ("solexa64", "fastq-solexa", 59, 126, "solexa_quality"),
])
def test_all_supported_native_quality_characters_match_biopython(encoding, native_format, first, last, native_key):
    quality = "".join(chr(value) for value in range(first, last + 1))
    sequence = "A" * len(quality)
    native = SeqIO.read(io.StringIO(f"@read\n{sequence}\n+\n{quality}\n"), native_format)
    result = grader.grade_sequence_composition(sequence, molecule="dna", quality=quality, quality_encoding=encoding)
    distribution = result["sheet"]["quality_measurements"]["native_score_distribution"]
    assert [row["native_score"] for row in distribution] == native.letter_annotations[native_key]
    assert all(row["count"] == 1 for row in distribution)
    assert result["scores"]["quality_observation_count"] == len(sequence)
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("encoding,invalid", [
    ("phred33", " "), ("phred33", "\x7f"), ("phred33", "é"),
    ("phred64", "?"), ("phred64", "\x7f"),
    ("solexa64", ":"), ("solexa64", "\x7f"),
])
def test_invalid_quality_retains_valid_native_counts_without_whole_read_aggregate(encoding, invalid):
    result = grader.grade_sequence_composition("ACG", molecule="dna", quality="II" + invalid, quality_encoding=encoding)
    quality = result["sheet"]["quality_measurements"]
    assert quality["status"] == "invalid"
    assert quality["decoded_character_count"] == 2 and quality["invalid_character_count"] == 1
    assert quality["invalid_characters"] == [{"position": 2, "codepoint": ord(invalid)}]
    assert result["scores"]["quality_observation_count"] is None
    assert result["scores"]["mean_phred"] is None
    assert result["scores"]["expected_error_count"] is None
    assert result["scores"]["gc_fraction"] == pytest.approx(2 / 3)


@pytest.mark.parametrize("quality", ["", "III", "IIIII"])
def test_mismatched_quality_keeps_actual_lengths_and_suppresses_sequence_quality_summary(quality):
    result = grader.grade_sequence_composition("ACGT", molecule="dna", quality=quality, quality_encoding="phred33")
    assert result["sheet"]["quality"] == quality
    assert result["sheet"]["quality_measurements"]["character_count"] == len(quality)
    assert result["sheet"]["quality_measurements"]["decoded_character_count"] == len(quality)
    assert "quality_sequence_length_mismatch" in codes(result["sheet"])
    assert result["scores"]["quality_observation_count"] is None
    assert result["scores"]["expected_error_count"] is None


def test_reopened_sheet_can_recalculate_thresholds_without_builder_or_mutation(tmp_path, monkeypatch):
    sheet = grader.build_sequence_composition_sheet("ACGT", molecule="dna", quality="!+5?", quality_encoding="phred33")
    path = tmp_path / "sheet.json"
    path.write_text(json.dumps(sheet, allow_nan=False))
    saved = json.loads(path.read_text())
    before = deepcopy(saved)
    def rerun_forbidden(*args, **kwargs):
        raise AssertionError("recalculation must not run builder or acquisition")
    monkeypatch.setattr(grader, "build_sequence_composition_sheet", rerun_forbidden)
    first = grader.calculate_sequence_composition_scores(saved)
    second = grader.calculate_sequence_composition_scores(saved, quality_thresholds=(-1, 10, 21, 30, 31, 10))
    assert [row["count_at_or_above"] for row in first["quality_thresholds"]] == [2, 1]
    assert [row["count_at_or_above"] for row in second["quality_thresholds"]] == [4, 3, 1, 1, 0, 3]
    assert first["mean_phred"] == second["mean_phred"] == 15
    assert saved == before
    second["symbol_counts"]["A"] = 100
    second["issues"].append({"code": "test_only"})
    assert saved == before


def test_wrapped_existing_material_fixture_reaches_grader_as_complete_native_strings():
    # Exact first record in tests/test_packed_materials.py WRAPPED_FASTQ; synthetic.
    native = "@dup αβ exact 🧬\r\nACGT\r\nTGCA\r\n+\r\n!@+~\r\n@@##\r\n".encode("utf-8")
    parsed = list(records(io.BytesIO(native), "fastq", molecule="unspecified", name="reads"))
    assert len(parsed) == 1 and "record" in parsed[0]
    record = parsed[0]["record"]
    assert record["sequence"] == "ACGTTGCA" and record["quality"] == "!@+~@@##"
    declared = grader.grade_sequence_composition(record["sequence"], molecule="unspecified",
                                                 quality=record["quality"], quality_encoding="phred33")
    unknown = grader.grade_sequence_composition(record["sequence"], molecule="unspecified",
                                                quality=record["quality"], quality_encoding="unspecified")
    assert declared["scores"]["quality_observation_count"] == 8
    assert declared["scores"]["mean_phred"] == 25
    assert declared["scores"]["gc_fraction"] is None
    assert unknown["scores"]["quality_observation_count"] is None
    assert unknown["sheet"]["quality"] == "!@+~@@##"


@pytest.mark.parametrize("changes,code", [
    ({"sequence": None}, "sequence_composition_sequence_string_required"),
    ({"sequence": b"ACGT"}, "sequence_composition_sequence_string_required"),
    ({"molecule": None}, "sequence_composition_declared_molecule_required"),
    ({"molecule": "DNA"}, "sequence_composition_declared_molecule_required"),
    ({"molecule": "unknown"}, "sequence_composition_declared_molecule_required"),
    ({"quality": [1, 2]}, "sequence_composition_quality_string_or_null_required"),
    ({"quality_encoding": 33}, "sequence_composition_encoding_string_or_null_required"),
])
def test_malformed_top_level_arguments_have_specific_errors(changes, code):
    arguments = {"sequence": "ACGT", "molecule": "dna", **changes}
    before = deepcopy(arguments)
    with pytest.raises(ValueError, match="^" + code + "$"):
        grader.build_sequence_composition_sheet(**arguments)
    assert arguments == before


@pytest.mark.parametrize("thresholds", [[20, 30], (True,), (20.0,), (math.nan,), (math.inf,), None])
def test_thresholds_require_explicit_integer_tuple(thresholds):
    sheet = grader.build_sequence_composition_sheet("A", molecule="dna")
    with pytest.raises(ValueError, match="sequence_composition_integer_quality_thresholds_tuple_required"):
        grader.calculate_sequence_composition_scores(sheet, quality_thresholds=thresholds)


def test_threshold_report_remains_json_serializable_at_interpreter_integer_limit():
    limit = sys.get_int_max_str_digits()
    if not limit:
        pytest.skip("interpreter has no integer serialization limit")
    sheet = grader.build_sequence_composition_sheet("A", molecule="dna")
    with pytest.raises(ValueError, match="sequence_composition_json_quality_thresholds_required"):
        grader.calculate_sequence_composition_scores(sheet, quality_thresholds=(10 ** limit,))


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, object(), (1, 2), {1: "integer key"}])
def test_saved_sheets_must_be_finite_json_including_unknown_fields(bad):
    sheet = grader.build_sequence_composition_sheet("A", molecule="dna")
    sheet["extra_native_field"] = bad
    with pytest.raises(ValueError, match="sequence_composition_finite_json_sheet_required"):
        grader.calculate_sequence_composition_scores(sheet)


@pytest.mark.parametrize("sheet,code", [
    (None, "sequence_composition_sheet_required"),
    ({"schema": "other"}, "sequence_composition_sheet_required"),
    ({"schema": grader.SHEET_SCHEMA}, "sequence_composition_saved_inputs_required"),
])
def test_malformed_saved_top_level_contract_is_not_a_zero_result(sheet, code):
    with pytest.raises(ValueError, match="^" + code + "$"):
        grader.calculate_sequence_composition_scores(sheet)


def test_invalid_saved_individual_count_preserves_independent_quality():
    sheet = grader.build_sequence_composition_sheet("ACGN", molecule="dna", quality="!+5?", quality_encoding="phred33")
    sheet["composition"]["gc_count"] = -1
    before = deepcopy(sheet)
    scores = grader.calculate_sequence_composition_scores(sheet)
    assert scores["gc_count"] is None and scores["gc_fraction"] is None
    assert scores["gc_denominator"] == 3 and scores["ambiguity_fraction"] == 0.25
    assert scores["mean_phred"] == 15
    assert "invalid_or_missing_count" in codes(scores)
    assert sheet == before


@pytest.mark.parametrize("replacement", [True, 1.0, -1, 2, "1"])
def test_saved_quality_distribution_cannot_silently_change_its_population(replacement):
    sheet = grader.build_sequence_composition_sheet("A", molecule="dna", quality="I", quality_encoding="phred33")
    sheet["quality_measurements"]["native_score_distribution"][0]["count"] = replacement
    scores = grader.calculate_sequence_composition_scores(sheet)
    assert scores["expected_error_count"] is None
    assert scores["quality_observation_count"] is None
    assert scores["gc_count"] == 0 and scores["gc_fraction"] == 0.0
    assert "quality_measurement_conflicts_with_retained_input" in codes(scores)


def test_known_zero_expected_counts_do_not_become_missing():
    scores = grader.grade_sequence_composition("A", molecule="dna", quality="!", quality_encoding="phred33")["scores"]
    assert scores["gc_count"] == scores["ambiguous_symbol_count"] == 0
    assert scores["gc_fraction"] == scores["ambiguity_fraction"] == 0
    assert scores["mean_phred"] == 0
    assert scores["mean_error_probability"] == scores["expected_error_count"] == 1
    assert scores["quality_thresholds"][0]["count_at_or_above"] == 0
    assert scores["quality_thresholds"][0]["fraction_at_or_above"] == 0
