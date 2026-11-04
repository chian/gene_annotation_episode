"""Numerical answers, failure components and offline saved-sheet recalculation."""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.nhmmer_inputs import build_nhmmer_sheet, parse_nhmmer_artifacts
from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores


FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_nhmmer_2026-10-24"


def sheet_for(name):
    directory = FIXTURES / name
    native = parse_nhmmer_artifacts(program="nhmmscan" if name == "nhmmscan" else "nhmmer",
        artifacts={"stdout": (directory / "stdout.txt").read_text(), "tblout": (directory / "hits.tbl").read_text()},
        artifact_refs={"stdout": name + "/stdout", "tblout": name + "/tblout"}, engine_version="3.4")
    return build_nhmmer_sheet(native, inputs=json.loads((directory / "inputs.json").read_text()))


def table_sheet(text, inputs=None, program="nhmmer"):
    native = parse_nhmmer_artifacts(program=program, artifacts={"tblout": text},
        artifact_refs={"tblout": "synthetic-table"}, engine_version="3.4")
    return build_nhmmer_sheet(native, inputs=inputs or {})


def score_table(text, inputs=None, program="nhmmer"):
    return calculate_nhmmer_scores(table_sheet(text, inputs, program))


@pytest.mark.parametrize("name", ["nhmmer_sequence", "nhmmer_profile", "nhmmer_msa", "nhmmscan"])
def test_retained_real_gapped_locus_exact_counts_and_denominators(name):
    scores = calculate_nhmmer_scores(sheet_for(name))
    row = next(row for row in scores["loci"] if "gapped" in row["identities"].values())
    assert row["model_length"] == 100
    assert row["sequence_length"] == 121
    assert row["model_span_positions"] == 100
    assert row["sequence_span_positions"] == 101
    assert row["sequence_envelope_positions"] == 101
    assert row["paired_positions"] == 98
    assert row["insert_positions"] == 3
    assert row["delete_positions"] == 2
    assert row["alignment_columns"] == 103
    assert row["model_span_coverage"] == 1
    assert row["sequence_span_coverage"] == pytest.approx(101 / 121)
    assert row["paired_sequence_coverage"] == pytest.approx(98 / 121)
    assert row["paired_model_coverage"] == 0.98
    cell = row["components"]["paired_sequence_coverage"]
    assert (cell["numerator"], cell["denominator"], cell["unit"]) == (98, 121, "fraction")
    assert row["components"]["posterior_lower_mean"]["denominator"] == 101
    assert row["components"]["posterior_upper_mean"]["bound_inclusive"] is False
    assert row["native_accuracy"] != row["posterior_lower_mean"]
    assert not any(key in row for key in ("translation", "sequence_identity_fraction", "function_confidence"))


def test_reverse_actual_alignment_keeps_native_direction_and_paired_coordinates():
    sheet = sheet_for("nhmmer_profile")
    scores = calculate_nhmmer_scores(sheet)
    row = next(row for row in scores["loci"] if row["strand"] == "-")
    native = next(row for row in sheet["loci"] if row["native"]["strand"] == "-")
    assert (native["native"]["ali_from"], native["native"]["ali_to"]) == (110, 11)
    assert row["coordinates"]["sequence_interval"] == [10, 110]
    assert row["paired_sequence_intervals"] == [[10, 110]]
    assert row["sequence_span_coverage"] == pytest.approx(100 / 120)


def test_native_zero_and_negative_measurements_are_not_missing_or_confidence():
    row = score_table("t - q - 1 5 1 5 1 5 20 + 0 -3.2 0\n")["loci"][0]
    assert row["native_evalue"] == 0.0
    assert row["native_score_bits"] == -3.2
    assert row["native_bias_bits"] == 0
    assert row["paired_positions"] is None
    assert row["posterior_lower_mean"] is None
    assert row["model_span_positions"] == 5
    assert row["model_span_coverage"] is None
    assert row["sequence_span_coverage"] == 0.25
    assert row["components"]["model_span_coverage"]["denominator"] is None


def test_missing_vs_invalid_native_statistics_preserve_other_components():
    scores = score_table("t - q - 1 5 1 5 1 5 20 + - -2 0\n"
                         "t - q - 1 5 1 5 1 5 20 + -1 3 nan\n"
                         "t - q - 1 5 1 5 1 5 20 + 1 3 0\n")
    assert [row["native_evalue"] for row in scores["loci"]] == [None, None, 1]
    assert [row["sequence_span_coverage"] for row in scores["loci"]] == [0.25] * 3
    assert scores["loci"][1]["native_bias_bits"] is None


def test_scan_requires_actual_query_length_for_sequence_coverage():
    text = "model - q - 1 40 61 100 60 101 40 + 1 3 0\n"
    scores = score_table(text, program="nhmmscan")["loci"][0]
    assert scores["model_span_coverage"] == 1
    assert scores["sequence_span_coverage"] is None
    known = score_table(text, {"query": {"name": "q", "kind": "nucleotide_sequence", "length": 200}}, "nhmmscan")["loci"][0]
    assert known["sequence_span_coverage"] == 0.2
    assert known["sequence_envelope_coverage"] == 0.21


def test_one_position_locus_has_one_position_span():
    scores = score_table("t - q - 1 1 1 1 1 1 10 - 0 0 0\n")["loci"][0]
    assert scores["model_span_positions"] == 1
    assert scores["sequence_span_positions"] == 1
    assert scores["sequence_span_coverage"] == 0.1


def test_model_and_sequence_envelope_invalidity_are_independent():
    row = score_table("t - q - 5 1 1 5 2 4 20 + 1 3 0\n")["loci"][0]
    assert row["model_span_positions"] is None
    assert row["sequence_envelope_positions"] is None
    assert row["sequence_span_positions"] == 5
    assert row["native_score_bits"] == 3


def test_cutoffs_are_explicit_per_model_per_hit_and_never_domain_substituted():
    inputs = {"query": {"name": "q", "kind": "profile", "length": 10}, "model_cutoffs": [
        {"name": "q", "GA": {"sequence_bits": 5, "domain_bits": 100}, "TC": 8,
         "NC": {"domain_bits": -100}}]}
    row = score_table("t - q - 1 5 1 5 1 5 20 + 0 7 1\n", inputs)["loci"][0]
    by_name = {entry["cutoff"]: entry for entry in row["cutoff_margins"]}
    assert by_name["GA"]["margin_bits"] == 2
    assert by_name["TC"]["margin_bits"] == -1
    assert by_name["NC"]["margin_bits"] is None
    assert not by_name["GA"]["domain_bits_used"]
    assert row["native_status"]["included"] is None


def test_wrong_or_ambiguous_model_cutoff_identity_does_not_make_a_margin():
    inputs = {"model_cutoffs": [{"name": "q", "accession": "wrong", "GA": 1}]}
    assert score_table("t - q A 1 5 1 5 1 5 20 + 0 7 1\n", inputs)["loci"][0]["cutoff_margins"] == []
    inputs = {"model_cutoffs": [{"name": "q", "GA": 1}] * 2}
    margins = score_table("t - q - 1 5 1 5 1 5 20 + 0 7 1\n", inputs)["loci"][0]["cutoff_margins"]
    assert all(entry["margin_bits"] is None for entry in margins)
    assert all(entry["unavailable_reason"] == "ambiguous_model_cutoffs" for entry in margins)


def test_overlap_union_is_strand_scoped_and_never_sums_evalues():
    text = ("t - q - 1 10 1 10 1 10 100 + 1 5 0\n"
            "t - q - 6 15 6 15 6 15 100 + 2 6 0\n"
            "t - q - 1 10 10 1 10 1 100 - 3 7 0\n")
    inputs = {"query": {"name": "q", "kind": "profile", "length": 20},
              "targets": [{"name": "t", "kind": "nucleotide_sequence", "length": 100}]}
    scores = score_table(text, inputs)
    unions = scores["queries"][0]["unions"]
    assert len(unions) == 2
    plus = next(group for group in unions if group["strand"] == "+")
    minus = next(group for group in unions if group["strand"] == "-")
    assert plus["union_components"]["sequence_span"]["positions"] == 15
    assert plus["union_components"]["sequence_span"]["coverage"] == 0.15
    assert plus["union_components"]["model_span"]["coverage"] == 0.75
    assert minus["union_components"]["sequence_span"]["positions"] == 10
    assert all("evalue" not in group for group in unions)
    assert plus["union_components"]["paired_sequence"]["positions"] is None


def test_equal_display_names_alone_do_not_establish_union_population():
    scores = score_table("t - q - 1 10 1 10 1 10 100 + 1 5 0\n" * 2)
    assert scores["queries"] == []
    assert all(row["union_identity"] is None for row in scores["loci"])


def test_duplicate_rows_do_not_increase_union_length():
    inputs = {"query": {"name": "q", "kind": "profile", "length": 20},
              "targets": [{"name": "t", "kind": "nucleotide_sequence", "length": 100}]}
    scores = score_table("t - q - 1 10 1 10 1 10 100 + 1 5 0\n" * 2, inputs)
    component = scores["queries"][0]["unions"][0]["union_components"]["sequence_span"]
    assert component["positions"] == 10
    assert component["included_record_count"] == 2


def test_pp_bins_are_bounds_over_residues_excluding_delete_gaps():
    sheet = table_sheet("t - q - 1 4 1 4 1 4 10 + 1 3 0\n", {"query": {"name": "q", "kind": "profile", "length": 10}})
    sheet["loci"][0]["alignment"] = {"valid": True, "posterior_valid": True,
        "model_aligned": "ac.gt", "sequence_aligned": "ACG-T", "posterior": "09*.*"}
    row = calculate_nhmmer_scores(sheet)["loci"][0]
    assert (row["paired_positions"], row["insert_positions"], row["delete_positions"]) == (3, 1, 1)
    assert row["posterior_lower_mean"] == pytest.approx((0 + .85 + .95 + .95) / 4)
    assert row["posterior_upper_mean"] == pytest.approx((.05 + .95 + 1 + 1) / 4)
    assert row["components"]["posterior_upper_mean"]["denominator"] == 4
    assert row["components"]["posterior_upper_mean"]["bound_inclusive"] is False
    assert row["paired_model_intervals"] == [[0, 2], [3, 4]]
    assert row["paired_sequence_intervals"] == [[0, 2], [3, 4]]


def test_missing_pp_residue_is_reported_and_not_zero():
    sheet = table_sheet("t - q - 1 4 1 4 1 4 10 + 1 3 0\n")
    sheet["loci"][0]["alignment"] = {"valid": True, "posterior_valid": True,
        "model_aligned": "acgt", "sequence_aligned": "ACGT", "posterior": "***."}
    row = calculate_nhmmer_scores(sheet)["loci"][0]
    assert row["posterior_lower_mean"] == pytest.approx(.95)
    assert row["posterior_upper_mean"] == 1
    assert row["components"]["posterior_upper_mean"]["denominator"] == 3
    assert row["components"]["posterior_upper_mean"]["missing_residue_count"] == 1
    assert row["components"]["posterior_upper_mean"]["bound_inclusive"] is True


@pytest.mark.parametrize("posterior,reason", [("**X*", "posterior_symbol_invalid"), ("***", "posterior_unavailable_or_invalid")])
def test_bad_pp_retains_valid_alignment_counts(posterior, reason):
    sheet = table_sheet("t - q - 1 4 1 4 1 4 10 + 1 3 0\n")
    sheet["loci"][0]["alignment"] = {"valid": True, "posterior_valid": True,
        "model_aligned": "acgt", "sequence_aligned": "ACGT", "posterior": posterior}
    row = calculate_nhmmer_scores(sheet)["loci"][0]
    assert row["paired_positions"] == 4
    assert row["posterior_lower_mean"] is None
    assert row["availability"]["posterior_lower_mean"] == reason


def test_native_searched_space_is_actual_not_number_of_hits():
    scores = calculate_nhmmer_scores(sheet_for("nhmmer_profile"))
    stats = {entry["name"]: entry for entry in scores["queries"][0]["searched_space"]}
    assert stats["Target sequences"]["count"] == 3
    assert stats["Target sequences"]["positions"] == 722
    assert stats["Target sequences"]["positions_unit"] == "nucleotides_searched"
    assert stats["Query model(s)"]["positions"] == 100
    # The count printed next to this native fraction is NOT its numerator.
    assert stats["Total number of hits"]["count"] == 3
    assert stats["Total number of hits"]["fraction_numerator"] is None
    assert stats["Total number of hits"]["fraction_denominator"] == 722
    assert stats["Residues passing SSV filter"]["fraction_numerator"] == stats["Residues passing SSV filter"]["count"]
    # nhmmscan has a query sequence and a target model population instead.
    scan = calculate_nhmmer_scores(sheet_for("nhmmscan"))
    stats = {entry["name"]: entry for entry in scan["queries"][0]["searched_space"]}
    assert stats["Target model(s)"]["count"] == 1
    assert stats["Query sequence(s)"]["positions"] == 240
    assert stats["Total number of hits"]["fraction_denominator"] == 240


def test_unsupported_parameters_and_nonfinite_json_are_rejected():
    sheet = table_sheet("# [ok]\n")
    with pytest.raises(ValueError, match="nhmmer_unsupported_parameters:weight"):
        calculate_nhmmer_scores(sheet, parameters={"weight": 1})
    with pytest.raises(ValueError, match="nhmmer_invalid_parameters_type"):
        calculate_nhmmer_scores(sheet, parameters=[])
    with pytest.raises(ValueError, match="nhmmer_nonfinite_json"):
        calculate_nhmmer_scores(sheet, parameters={"x": float("inf")})


def test_saved_sheet_recalculates_with_no_files_network_programs_or_parser(monkeypatch):
    import gene_annotation_episode.nhmmer_inputs as readers
    sheet = sheet_for("nhmmscan")
    expected = calculate_nhmmer_scores(sheet)
    saved = json.loads(json.dumps(sheet, allow_nan=False))
    saved.pop("native")  # No raw outputs are needed by calculations.
    before = deepcopy(saved)

    def forbidden(*args, **kwargs):
        raise AssertionError("offline calculator attempted external work or reparsing")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(readers, "parse_nhmmer_artifacts", forbidden)
    monkeypatch.setattr(readers, "iter_nhmmer_tblout_rows", forbidden)
    assert calculate_nhmmer_scores(saved, parameters={}) == expected
    assert saved == before
    json.dumps(expected, allow_nan=False)


def test_recalculation_changes_declared_cutoff_without_touching_native_data():
    sheet = table_sheet("t - q - 1 4 1 4 1 4 10 + 1 8 0\n", {"model_cutoffs": [{"name": "q", "GA": 5}]})
    first = calculate_nhmmer_scores(sheet)["loci"][0]
    changed = deepcopy(sheet)
    changed["inputs"]["model_cutoffs"][0]["GA"] = 6
    second = calculate_nhmmer_scores(changed)["loci"][0]
    assert first["cutoff_margins"][0]["margin_bits"] == 3
    assert second["cutoff_margins"][0]["margin_bits"] == 2
    assert first["native"] == second["native"]


def test_invalid_saved_locus_preserves_other_siblings():
    sheet = table_sheet("t - q - 1 4 1 4 1 4 10 + 1 8 0\n")
    sheet["loci"].insert(0, "malformed")
    scores = calculate_nhmmer_scores(sheet)
    assert len(scores["loci"]) == 1
    assert scores["loci"][0]["native_score_bits"] == 8
    assert any(issue["code"] == "nhmmer_invalid_sheet_locus" for issue in scores["issues"])


def test_finite_extreme_cutoff_cannot_create_nonfinite_output():
    sheet = table_sheet("t - q - 1 4 1 4 1 4 10 + 1 -1e308 0\n", {"model_cutoffs": [{"name": "q", "GA": 1e308}]})
    scores = calculate_nhmmer_scores(sheet)
    margin = scores["loci"][0]["cutoff_margins"][0]
    assert margin["margin_bits"] is None
    assert margin["unavailable_reason"] == "cutoff_margin_overflow"
    json.dumps(scores, allow_nan=False)


def test_native_inclusion_flags_stay_native_when_thresholds_disagree():
    sheet = sheet_for("nhmmer_profile")
    sheet["inputs"]["model_cutoffs"] = [{"name": "model", "GA": 10000}]
    row = calculate_nhmmer_scores(sheet)["loci"][0]
    assert row["native_status"]["included"] is True
    assert row["cutoff_margins"][0]["margin_bits"] < 0


def test_bad_saved_alignment_span_does_not_turn_into_paired_coverage():
    sheet = table_sheet("t - q - 1 4 1 4 1 4 10 + 1 3 0\n")
    sheet["loci"][0]["alignment"] = {"valid": True, "posterior_valid": True,
        "model_aligned": "acgt", "sequence_aligned": "ACG-", "posterior": "***."}
    row = calculate_nhmmer_scores(sheet)["loci"][0]
    assert row["paired_positions"] is None
    assert row["availability"]["paired_positions"] == "alignment_spans_disagree"
    assert row["sequence_span_positions"] == 4
