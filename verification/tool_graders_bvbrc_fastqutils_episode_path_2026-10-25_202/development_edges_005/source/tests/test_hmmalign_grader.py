from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess

import pytest

import gene_annotation_episode.hmmalign_inputs as readers
from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores


FIXTURES = Path(__file__).resolve().parents[1]/"verification/tool_graders_hmmalign_2026-10-24/native"


def sheet(text, inputs=None):
    return readers.build_hmmalign_sheet(readers.parse_hmmalign_stockholm(text, artifact_ref="actual", engine_version="3.4"), inputs=inputs or {})


def native_sheet(mode):
    sequences = []
    for record in (FIXTURES/"sequences.fa").read_text().split(">")[1:]:
        name, *lines = record.splitlines()
        sequence = "".join(lines)
        sequences.append({"name": name, "occurrence": 0, "sequence": sequence, "length": len(sequence), "origin": "new"})
    inputs = {"profile": {"name": "test", "length": 20, "alphabet": "amino", "map": list(range(1, 21)), "checksum": 1166427327},
              "trim": mode == "trim", "sequences": sequences, "acquisition": {"output_complete": True}}
    if mode == "mapali":
        inputs["mapali"] = {"artifact_ref": "seed", "stockholm": (FIXTURES/"seed.sto").read_text()}
    return sheet((FIXTURES/mode/"stdout.txt").read_text(), inputs)


def test_synthetic_counts_rf_inserts_deletions_fragments_occupancy_and_pp_bounds():
    text = ("# STOCKHOLM 1.0\nq aaACdE-ff\n#=GR q PP 01*95*.9*\n"
            "fragment ~~A-.EF~~\n#=GR fragment PP ..*..**..\n"
            "#=GC RF ..xx.xx..\n#=GC PP_cons ..*9.*9..\n//\n")
    populated = sheet(text, {"trim": False, "profile": {"length": 4, "alphabet": "protein"},
        "sequences": [{"name": "q", "occurrence": 0, "sequence": "aaACdEff", "length": 8},
                      {"name": "fragment", "occurrence": 0, "sequence": "AEF", "length": 3}]})
    result = calculate_hmmalign_scores(populated)
    q, fragment = result["sequences"]
    assert q["model_length"] == 4 and q["original_length"] == 8
    assert q["match_state_residues"] == 3 and q["deleted_model_positions"] == 1
    assert q["insert_state_residues"] == 1 and q["terminal_unaligned_residues"] == 4
    assert q["retained_residues"] == 8 and q["trimmed_residues"] == 0
    assert q["model_occupancy"] == 3/4 and q["sequence_match_coverage"] == 3/8
    assert q["posterior_lower_mean"] == pytest.approx(5.05/8)
    assert q["posterior_upper_mean"] == pytest.approx(5.65/8)
    assert q["posterior_bounded_residue_count"] == 8
    assert q["posterior_mean_upper_inclusive"] is False
    assert fragment["fragment"] == "native_missing_data"
    assert fragment["deleted_model_positions"] == 1
    assert result["columns"][0]["populations"]["all"] == {
        "occupancy_numerator": 1, "occupancy_denominator": 1, "missing_rows": 1,
        "row_count": 2, "record_keys": [q["record_key"], fragment["record_key"]],
        "occupancy": 1.0, "unavailable_reason": None}
    assert result["columns"][4]["homologous_model_column"] is False
    assert result["columns"][4]["model_position"] is None
    assert result["columns"][4]["occupancy"] == 1/2
    assert not any(key in result for key in ("confidence", "function_confidence", "combined_score"))


def test_missing_fragment_positions_are_not_deletions_or_occupancy_denominator():
    result = calculate_hmmalign_scores(sheet("# STOCKHOLM 1.0\nf ~AC~\nq -AC-\n#=GC RF xxxx\n//\n"))
    fragment, full = result["sequences"]
    assert fragment["missing_model_positions"] == 2 and fragment["deleted_model_positions"] == 0
    assert full["missing_model_positions"] == 0 and full["deleted_model_positions"] == 2
    assert fragment["model_occupancy"] == full["model_occupancy"] == .5
    assert result["columns"][0]["occupancy_denominator"] == 1
    assert result["columns"][0]["populations"]["fragment"]["occupancy"] is None
    assert result["columns"][0]["populations"]["fragment"]["missing_rows"] == 1


@pytest.mark.parametrize("pp,lower,upper,n", [(None, None, None, 0), ("..", None, None, 0),
    ("00", 0.0, .05, 2), ("**", .95, 1.0, 2), ("*.", .95, 1.0, 1), ("19", .45, .55, 2)])
def test_pp_missing_and_zero_are_distinct_and_denominator_is_explicit(pp, lower, upper, n):
    text = "# STOCKHOLM 1.0\nq AC\n" + (f"#=GR q PP {pp}\n" if pp is not None else "") + "#=GC RF xx\n//\n"
    row = calculate_hmmalign_scores(sheet(text))["sequences"][0]
    assert row["posterior_lower_mean"] == lower
    assert row["posterior_upper_mean"] == upper
    assert row["denominators"]["posterior_lower_mean"] == n
    assert row["posterior_unavailable_residue_count"] == 2-n
    if n == 0:
        assert row["unavailable"]["posterior_lower_mean"] == "no_usable_native_PP_residues"


def test_invalid_pp_components_preserve_valid_residue_bounds():
    result = calculate_hmmalign_scores(sheet("# STOCKHOLM 1.0\nq A-C\n#=GR q PP *9?\n#=GC RF xxx\n//\n"))
    row = result["sequences"][0]
    assert row["posterior_lower_mean"] == .95 and row["posterior_upper_mean"] == 1
    assert row["posterior_bounded_residue_count"] == 1 and row["posterior_unavailable_residue_count"] == 1
    assert {i["code"] for i in row["issues"]} == {"hmmalign_pp_on_nonresidue", "hmmalign_pp_symbol_invalid"}


def test_bad_pp_geometry_does_not_join_prefix_as_a_full_posterior_row():
    result = calculate_hmmalign_scores(sheet("# STOCKHOLM 1.0\nq ACE\n#=GR q PP **\n#=GC RF xxx\n//\n"))
    row = result["sequences"][0]
    assert row["match_state_residues"] == 3
    assert row["posterior_lower_mean"] is None
    assert "hmmalign_annotation_geometry_invalid" in {i["code"] for i in row["issues"]}


def test_invalid_pp_cons_component_preserves_valid_native_column_bounds():
    result = calculate_hmmalign_scores(sheet("# STOCKHOLM 1.0\nq AC\n#=GC RF xx\n#=GC PP_cons ?9\n//\n"))
    assert result["columns"][0]["posterior_cons_lower"] is None
    assert result["columns"][1]["posterior_cons_lower"] == .85
    assert any(i["code"] == "hmmalign_pp_cons_symbol_invalid" for i in result["issues"])


def test_actual_ordinary_numerical_example():
    result = calculate_hmmalign_scores(native_sheet("ordinary"))
    assert result["issues"] == []
    row = result["sequences"][1]
    assert row["original_length"] == 25 and row["model_length"] == 20
    assert (row["match_state_residues"], row["deleted_model_positions"], row["insert_state_residues"], row["terminal_unaligned_residues"]) == (18, 2, 3, 4)
    assert row["retained_residues"] == 25 and row["trimmed_residues"] == 0
    assert row["model_occupancy"] == 18/20
    assert row["sequence_match_coverage"] == 18/25
    assert row["posterior_lower_mean"] == 22.55/25
    assert row["posterior_upper_mean"] == 24.15/25
    assert row["mapping"]["original_interval"] == [0, 25]
    assert result["summary"]["column_count"] == 33


def test_actual_trim_numerical_example_uses_original_sequence_denominator():
    populated = native_sheet("trim")
    result = calculate_hmmalign_scores(populated)
    assert result["issues"] == []
    row = result["sequences"][1]
    assert (row["original_length"], row["retained_residues"], row["trimmed_residues"], row["terminal_unaligned_residues"]) == (25, 21, 4, 0)
    assert row["model_occupancy"] == .9 and row["sequence_match_coverage"] == .72
    assert row["mapping"]["original_interval"] == [4, 25]
    assert row["posterior_lower_mean"] == pytest.approx(18.75/21)
    assert row["posterior_upper_mean"] == pytest.approx(20.15/21)
    assert row["denominators"]["posterior_lower_mean"] == 21
    assert populated["sequences"][1]["correspondence"][0]["original_sequence_position"] == 4
    assert result["summary"]["column_count"] == 25


def test_actual_mapali_inherited_population_is_separate_and_pp_cons_excludes_inherited():
    populated = native_sheet("mapali")
    result = calculate_hmmalign_scores(populated)
    assert result["issues"] == []
    assert result["summary"]["sequence_counts_by_origin"] == {"inherited": 10, "newly_aligned": 4, "unknown": 0}
    inherited = result["sequences"][0]
    assert inherited["original_length"] == 20 and inherited["match_state_residues"] == 20
    assert inherited["model_occupancy"] == 1 and inherited["sequence_match_coverage"] == 1
    assert inherited["posterior_lower_mean"] is None and inherited["posterior_upper_mean"] is None
    model_column = result["columns"][4]
    assert model_column["occupancy_numerator"] == model_column["occupancy_denominator"] == 14
    assert model_column["populations"]["inherited"]["occupancy_denominator"] == 10
    assert model_column["populations"]["newly_aligned"]["occupancy_denominator"] == 4
    assert model_column["pp_cons_observed_denominator"] == 4
    assert model_column["posterior_cons_lower"] == .85
    assert model_column["posterior_cons_upper"] == .95
    assert model_column["model_position"] == 1


@pytest.mark.parametrize("trim", [False, True])
def test_actual_fragment_mapali_retains_missing_populations_and_trimmed_inherited_insertions(trim):
    mode = "fragment_mapali_trim" if trim else "fragment_mapali"
    inputs = {"profile": {"name": "fragment_profile", "length": 20, "alphabet": "amino",
                          "map": [*range(3, 9), *range(11, 25)], "checksum": 1589892361},
              "mapali": {"artifact_ref": "fragment_seed", "stockholm": (FIXTURES/"fragment_seed.sto").read_text()},
              "trim": trim, "sequences": [{"name": "new", "occurrence": 0, "sequence": "ACDEFGHIKLMNPQRSTVWY", "origin": "new"}]}
    populated = sheet((FIXTURES/mode/"stdout.txt").read_text(), inputs)
    result = calculate_hmmalign_scores(populated)
    assert result["issues"] == []
    assert populated["mapali"]["computed_checksum"] == 1589892361
    inherited, _, fragment, new = result["sequences"]
    assert inherited["original_length"] == 26
    assert inherited["retained_residues"] == (22 if trim else 26)
    assert inherited["trimmed_residues"] == (4 if trim else 0)
    assert inherited["terminal_unaligned_residues"] == (0 if trim else 4)
    assert inherited["insert_state_residues"] == 2
    assert inherited["match_state_residues"] == 20
    assert inherited["posterior_lower_mean"] is None
    assert inherited["mapping"]["original_interval"] == ([2, 24] if trim else [0, 26])
    assert fragment["missing_model_positions"] == 6
    assert fragment["deleted_model_positions"] == 0
    assert fragment["match_state_residues"] == 14
    assert fragment["model_occupancy"] == 14/20
    assert fragment["sequence_match_coverage"] == 1
    first_model = result["columns"][0 if trim else 2]
    assert first_model["populations"]["inherited"]["occupancy_denominator"] == 2
    assert first_model["populations"]["inherited"]["missing_rows"] == 1
    assert first_model["pp_cons_observed_denominator"] == 1
    assert new["posterior_lower_mean"] == .945
    assert populated["sequences"][0]["native"]["sequence_annotations"][0]["value"] == "preserved description"


@pytest.mark.parametrize("mode", ["ordinary", "trim", "mapali"])
def test_saved_sheet_offline_recalculation_never_reads_parses_executes_or_networks(mode, monkeypatch):
    populated = native_sheet(mode)
    saved = json.loads(json.dumps(populated, allow_nan=False))
    expected = calculate_hmmalign_scores(saved)
    original = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("calculator attempted acquisition, native execution, I/O or reparsing")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(readers, "parse_hmmalign_stockholm", forbidden)
    monkeypatch.setattr(readers, "build_hmmalign_sheet", forbidden)
    assert calculate_hmmalign_scores(saved, parameters={}) == expected
    assert saved == original


def test_invalid_saved_row_does_not_destroy_valid_sibling():
    populated = native_sheet("ordinary")
    populated["sequences"][0]["measurements"]["match_state_residues"] = -1
    result = calculate_hmmalign_scores(populated)
    assert result["sequences"][0]["status"] == "invalid"
    assert result["sequences"][1]["model_occupancy"] == .9
    assert result["summary"]["invalid_sequence_count"] == 1
    assert any(i["code"] == "hmmalign_sequence_sheet_invalid" for i in result["issues"])


@pytest.mark.parametrize("field", ["name", "native", "availability", "posterior", "native_rf", "inherited_join"])
def test_incomplete_saved_row_preserves_valid_sibling(field):
    populated = native_sheet("ordinary")
    del populated["sequences"][0][field]
    result = calculate_hmmalign_scores(populated)
    assert result["sequences"][0]["status"] == "invalid"
    assert result["sequences"][1]["model_occupancy"] == .9


def test_inconsistent_saved_posterior_component_is_not_silently_accepted():
    populated = native_sheet("ordinary")
    populated["sequences"][0]["posterior"]["lower_sum_hundredths"] = 1
    result = calculate_hmmalign_scores(populated)
    assert result["sequences"][0]["status"] == "invalid"
    assert result["sequences"][1]["posterior_lower_mean"] == .902


def test_invalid_saved_column_population_preserves_other_columns():
    populated = native_sheet("ordinary")
    populated["columns"][0]["populations"]["all"]["occupancy_numerator"] = 100
    result = calculate_hmmalign_scores(populated)
    assert result["columns"][0]["status"] == "invalid"
    assert result["columns"][4]["occupancy"] == 1


@pytest.mark.parametrize("parameters,code", [(4, "hmmalign_parameters_object_required"),
    ({"scale": 1}, "hmmalign_unsupported_parameters:scale"),
    ({"bad": float("inf")}, "hmmalign_parameters_finite_json_required")])
def test_unsupported_and_nonfinite_parameters_are_errors(parameters, code):
    with pytest.raises(ValueError, match=code):
        calculate_hmmalign_scores(native_sheet("ordinary"), parameters=parameters)


def test_nonfinite_sheet_and_wrong_schema_are_errors():
    populated = native_sheet("ordinary")
    populated["inputs"]["unused"] = float("nan")
    with pytest.raises(ValueError, match="hmmalign_sheet_finite_json_required"):
        calculate_hmmalign_scores(populated)
    with pytest.raises(ValueError, match="hmmalign_sheet_schema_invalid"):
        calculate_hmmalign_scores({})


def test_empty_completed_and_missing_native_output_do_not_conflate():
    empty = calculate_hmmalign_scores(sheet("# STOCKHOLM 1.0\n//\n"))
    missing = calculate_hmmalign_scores(sheet(""))
    assert empty["summary"]["native_status"] == "completed_empty"
    assert missing["summary"]["native_status"] == "missing"
    assert empty["summary"]["sequence_count"] == missing["summary"]["sequence_count"] == 0
    assert empty["summary"]["terminated_alignment_count"] == 1
    assert missing["summary"]["terminated_alignment_count"] == 0


def test_no_original_length_no_trim_flag_or_no_rf_remain_scoped_unknowns():
    result = calculate_hmmalign_scores(sheet("# STOCKHOLM 1.0\nq AC\n#=GR q PP **\n//\n"))
    row = result["sequences"][0]
    assert row["original_length"] is row["trimmed_residues"] is row["model_length"] is None
    assert row["model_occupancy"] is row["match_state_residues"] is None
    assert row["retained_residues"] == 2 and row["posterior_lower_mean"] == .95
    assert row["sequence_match_coverage"] is None


def test_stop_nonresidue_is_preserved_and_not_counted_as_an_amino_acid():
    row = calculate_hmmalign_scores(sheet("# STOCKHOLM 1.0\nq A*C\n#=GC RF xxx\n//\n"))["sequences"][0]
    assert row["retained_residues"] == row["match_state_residues"] == 2
    assert row["nonresidue_model_positions"] == 1
    assert row["deleted_model_positions"] == 0
    assert row["model_occupancy"] == 2/3
