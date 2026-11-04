"""Independent B1 numerical examples, edge cases and no-I/O recalculation."""
import builtins
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.hmmer_alignment_preparation_calculations import (
    CHECK_CODES, CHECK_STATES, COMPONENT_FIELDS, ISSUE_CODES, ROW_FIELDS,
    calculate_hmmer_alignment_preparation_components as calculate,
    reconstruct_alimask_model_map,
)
from gene_annotation_episode.hmmer_alignment_preparation_data import populate_hmmer_alignment_preparation_sheet
from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from test_hmmer_alignment_preparation_data import NATIVE, ROOT, build_sheet, mask_sheet, native_build, payload

AMINO_BACKGROUND = dict(zip("ACDEFGHIKLMNPQRSTVWY", [
    .0787945, .0151600, .0535222, .0668298, .0397062, .0695071, .0229198, .0590092,
    .0594422, .0963728, .0237718, .0414386, .0482904, .0395639, .0540978, .0683364,
    .0540687, .0673417, .0114135, .0304133]))


def check(result, code):
    return [item for item in result["checks"] if item["code"] == code]


def stockholm(sequence="ACDEFG", rf="xxxxxx", mm=None):
    return ("# STOCKHOLM 1.0\na " + sequence + "\n#=GC RF " + rf + "\n" +
            ("#=GC MM " + mm + "\n" if mm is not None else "") + "//\n").encode()


def test_native_protein_filled_numbers_and_full_correspondence():
    result = calculate(build_sheet(), parameters={"background": AMINO_BACKGROUND})
    row = result["rows"][0]
    values = {name: component["value"] for name, component in row["components"].items()}
    assert values["input_sequence_count"] == 3
    assert values["input_column_count"] == 14
    assert values["rf_consensus_count"] == values["model_length"] == values["resaved_column_count"] == 12
    assert values["model_alignment_fraction"] == 12 / 14
    assert values["effective_sequence_count"] == 3
    assert values["effective_input_sequence_ratio"] == 1
    assert values["native_relative_entropy"] == 4.376
    assert values["mean_match_relative_entropy"] == pytest.approx(4.376, abs=.0005)
    assert row["source_symbol_counts"][4]["counts"] == {"F": 2, "Y": 1}
    positions = row["model_components"]["positions"]
    assert len(positions) == 12
    p, q = math.exp(-.40547), math.exp(-1.09861)
    expected = -p * math.log2(p) - q * math.log2(q)
    assert positions[4]["entropy"]["value"] == pytest.approx(expected, abs=1e-14)
    assert row["coordinates"]["model_to_source_alignment"] == list(range(1, 13))
    assert row["coordinates"]["model_to_resaved_alignment"] == list(range(1, 13))
    mapping = row["coordinates"]["source_resaved"]["source_to_resaved_columns"]
    assert mapping[11]["resaved_alignment_positions"] == [12]
    assert mapping[12]["resaved_alignment_positions"] == mapping[13]["resaved_alignment_positions"] == []
    assert check(result, "source_checksum")[0]["state"] == "pass"
    assert check(result, "summary_relative_entropy")[0]["state"] == "pass"


def test_native_singlemx_matrix_kl_not_empirical_single_sequence_frequencies():
    result = calculate(build_sheet("singlemx"), parameters={"background": AMINO_BACKGROUND})
    row = result["rows"][0]
    assert row["components"]["mean_match_relative_entropy"]["value"] == pytest.approx(.6282749544993825, abs=1e-12)
    assert row["components"]["model_alignment_fraction"]["value"] == 1
    assert row["components"]["effective_input_sequence_ratio"]["value"] == 1
    assert row["coordinates"]["model_to_source_alignment"] is None
    assert row["model_components"]["positions"][0]["entropy"]["value"] > 3


@pytest.mark.parametrize("case,background", [("dna", dict.fromkeys("ACGT", .25)), ("rna", dict.fromkeys("ACGU", .25)), ("annotated", AMINO_BACKGROUND)])
def test_native_other_build_alphabets_and_annotations(case, background):
    sheet = build_sheet(case)
    result = calculate(sheet, parameters={"background": background})
    assert result["rows"][0]["components"]["mean_match_relative_entropy"]["state"] == "present"
    assert check(result, "summary_counts")[0]["state"] == "pass"
    if case == "annotated":
        source = sheet["input_records"][0]
        assert source["column_annotations"]["SS_cons"]["text"] == "HHHHHHCCCCCC.."
        assert sheet["model_extraction"]["records"][0]["positions"][1]["annotations"]["MM"]["value"] == "m"


def test_missing_background_and_explicit_recalculation_parameters():
    sheet = build_sheet()
    missing = calculate(sheet)
    assert missing["rows"][0]["components"]["mean_match_relative_entropy"]["state"] == "missing"
    assert missing["rows"][0]["components"]["native_relative_entropy"]["value"] == 4.376
    old = deepcopy(sheet)
    uniform = dict.fromkeys("ACDEFGHIKLMNPQRSTVWY", .05)
    recalculated = calculate(sheet, parameters={"background": uniform, "probability_tolerance": 0})
    assert recalculated["rows"][0]["components"]["mean_match_relative_entropy"]["state"] == "present"
    assert check(recalculated, "summary_relative_entropy")[0]["state"] == "fail"
    assert any(item["state"] == "fail" for item in check(recalculated, "model_components"))
    assert sheet == old


def test_saved_recalculation_has_no_io_network_native_or_input_mutation(monkeypatch):
    sheet = json.loads(json.dumps(build_sheet()))
    expected = calculate(sheet, parameters={"background": AMINO_BACKGROUND})
    original = deepcopy(sheet)
    mask = mask_sheet(stockholm(), stockholm(mm=".mmm.."), **{"--alirange": "2-4"})
    expected_mask = calculate(mask)
    def forbidden(*args, **kwargs):
        raise AssertionError("pure recalculation attempted I/O or a native process")
    with monkeypatch.context() as context:
        for target, name in ((builtins, "open"), (Path, "open"), (Path, "read_bytes"), (socket, "socket"),
                             (subprocess, "run"), (subprocess, "Popen")):
            context.setattr(target, name, forbidden)
        actual = calculate(sheet, parameters={"background": AMINO_BACKGROUND})
        actual_mask = calculate(mask)
    assert actual == expected and sheet == original
    assert actual_mask == expected_mask


def test_partial_later_model_retains_complete_first_calculation():
    selected, inputs, outputs, extraction = native_build()
    source = inputs["alignment"][0]["content"]
    inputs["alignment"] = [payload("alignment", source + source)]
    model = outputs["models"][0]["content"]
    outputs["models"] = [payload("models", model + model[:model.index(b"      5")], "output")]
    extraction = extract_hmmer_models(outputs["models"][0]["content"], occurrence=outputs["models"][0]["occurrence"], format="hmmer3_ascii")
    sheet = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    result = calculate(sheet, parameters={"background": AMINO_BACKGROUND})
    assert result["rows"][0]["components"]["mean_match_entropy"]["state"] == "present"
    assert result["rows"][1]["components"]["mean_match_entropy"]["state"] == "incomplete"


def test_mask_overlap_union_five_columns_of_fourteen():
    source = (NATIVE / "inputs/protein.sto").read_bytes()
    output = (NATIVE / "native/alimask_alignment/masked.sto").read_bytes()
    result = calculate(mask_sheet(source, output, **{"--alirange": "2-4,4-6", "--amino": True}))
    row = result["rows"][0]
    expected = {"requested_interval_count": 2, "requested_union_count": 5, "actual_masked_count": 5,
        "newly_masked_count": 5, "removed_masked_count": 0, "retained_masked_count": 0, "masked_fraction": 5 / 14}
    assert {name: row["components"][name]["value"] for name in expected} == expected
    assert row["output_mm"] == ".mmmmm........"
    assert check(result, "mask_annotation")[0]["state"] == "pass"


@pytest.mark.parametrize("append,expected_mask,expected_counts", [(False, ".mmm..", (2, 1, 1)), (True, "mmmm..", (2, 0, 2))])
def test_replace_and_appendmask_preserve_old_mask(append, expected_mask, expected_counts):
    result = calculate(mask_sheet(stockholm(mm="m.m..."), stockholm(mm=expected_mask),
        **{"--alirange": "2-4", "--appendmask": append, "--amino": True}))
    row = result["rows"][0]
    assert tuple(row["components"][name]["value"] for name in ("newly_masked_count", "removed_masked_count", "retained_masked_count")) == expected_counts
    assert check(result, "mask_annotation")[0]["state"] == "pass"


def test_hand_model_span_includes_insert_columns_and_rf_missing_is_unknown():
    source = stockholm(sequence="ACD-EF", rf="xx..xx")
    output = stockholm(sequence="ACD-EF", rf="xx..xx", mm=".mmmm.")
    result = calculate(mask_sheet(source, output, mode="mask_model", **{"--hand": True, "--modelrange": "2-3", "--amino": True}))
    row = result["rows"][0]
    assert row["reconstruction"]["map"] == [1, 2, 5, 6]
    assert row["components"]["requested_union_count"]["value"] == 4
    assert row["intervals"][0]["alignment_start"] == 2 and row["intervals"][0]["alignment_end"] == 5
    missing = source.replace(b"#=GC RF xx..xx\n", b"")
    unknown = calculate(mask_sheet(missing, output, mode="mask_model", **{"--hand": True, "--modelrange": "2-3"}))
    assert unknown["rows"][0]["components"]["requested_union_count"]["state"] == "missing"
    assert check(unknown, "mask_annotation")[0]["state"] == "unknown"


def test_mapping_adjusted_coordinates_no_map_and_unsafe_suffix():
    source = stockholm(sequence="ACDEFG", rf=".x..x.")
    stdout = b"alignment coordinates     model coordinates\n 2..5 -> 1..2\n 3..4 -> -..-  (no map)\n"
    result = calculate(mask_sheet(source, mode="alignment_to_model", stdout=stdout, **{"--ali2model": "1-6,3-4", "--hand": True}))
    assert check(result, "native_mapping")[0]["state"] == "pass"
    interval = result["rows"][0]["intervals"][0]
    assert interval["inclusive_span"]["value"] == 6
    assert interval["returned_source_span"]["value"] == 4
    assert interval["returned_target_span"]["value"] == 2
    assert result["rows"][0]["intervals"][1]["returned_target_span"]["state"] == "missing"
    unsafe = calculate(mask_sheet(source, mode="alignment_to_model", stdout=b"alignment coordinates model coordinates\n6..6 -> -..- (no map)\n", **{"--ali2model": "6-6", "--hand": True}))
    assert "unsafe_native_range" in {i["code"] for i in unsafe["issues"]}
    assert check(unsafe, "native_mapping")[0]["state"] == "fail"


@pytest.mark.parametrize("number,weight", [(0, "--wnone"), (1, "--wgiven"), (2, "--wpb")])
def test_fast_maps_against_retained_actual_producer_native_output(number, weight):
    directory = ROOT / "verification/tool_graders_hmmer_preparation_producer_2026-10-26_267/check004/temporary" / ("test_actual_gappy_fragment_map" + str(number))
    source = (directory / "gappy.sto").read_bytes()
    bundle = json.loads((directory / "hmmer-preparation-attempt/bundle.json").read_text())
    stdout = (directory / "hmmer-preparation-attempt/outputs/stdout").read_bytes()
    settings = bundle["operation"]["settings"]
    assert settings[weight] is True
    sheet = mask_sheet(source, mode="model_to_alignment", stdout=stdout, **settings)
    result = calculate(sheet)
    assert check(result, "native_mapping")[0]["state"] == "pass"
    reconstruction = result["rows"][0]["reconstruction"]
    assert reconstruction["marked_sequences"][0]["sequence"] == "~~ACGT-A~~"
    assert len(reconstruction["column_occupancy"]) == 10
    assert len(reconstruction["weights"]) == 3
    assert reconstruction["map"]


def test_fast_weighting_changes_map_and_gap_half_boundary_is_exact():
    source = b"# STOCKHOLM 1.0\n#=GS a WT 0.1\n#=GS b WT 3.0\na ACGT\nb A--T\n//\n"
    sheet = mask_sheet(source, **{"--alirange": "1-1"})
    record = sheet["input_records"][0]
    unweighted = reconstruct_alimask_model_map(record, settings={"--dna": True, "--wnone": True, "--fragthresh": 0, "--symfrac": .5})
    given = reconstruct_alimask_model_map(record, settings={"--dna": True, "--wgiven": True, "--fragthresh": 0, "--symfrac": .5})
    assert unweighted["map"] == [1, 2, 3, 4]
    assert given["map"] == [1, 4]
    pb = reconstruct_alimask_model_map(record, settings={"--dna": True, "--wpb": True, "--fragthresh": 0})
    assert pb["pb_consensus_columns"] == [1, 4]  # PB strict gap fraction < .5.


@pytest.mark.parametrize("settings,reason", [({"--dna": True, "--wgsc": True}, "weighting_unsupported"),
                                           ({"--wpb": True}, "alphabet_missing")])
def test_unknown_fast_branches_are_explicit(settings, reason):
    source = mask_sheet(stockholm(sequence="ACGT", rf="xxxx"), **{"--alirange": "1-1"})["input_records"][0]
    result = reconstruct_alimask_model_map(source, settings=settings)
    assert result["map"] is None and result["state"] == "missing"
    assert result["issues"][0]["code"] == reason


def test_pb_sampling_is_not_implicitly_replaced_by_full_population_weights():
    source = mask_sheet(stockholm(sequence="A", rf="x"), **{"--alirange": "1-1"})["input_records"][0]
    source["rows"] *= 50001
    result = reconstruct_alimask_model_map(source, settings={"--amino": True, "--wpb": True})
    assert result["map"] is None and result["issues"][0]["code"] == "pb_sampling_unsupported"


def test_wrong_source_bytes_width_mm_bounds_and_capacity():
    result = calculate(mask_sheet(stockholm(), stockholm(mm="mmmmmm"), **{"--alirange": "5-8"}))
    assert "range_out_of_bounds" in {i["code"] for i in result["issues"]}
    assert result["rows"][0]["components"]["requested_union_count"]["state"] == "incompatible"
    capacity = calculate(mask_sheet(stockholm(), stockholm(mm="m....."), **{"--alirange": ",".join(["1-1"] * 101)}))
    assert check(capacity, "range_capacity")[0]["state"] == "fail"
    invalid = calculate(mask_sheet(stockholm(), stockholm(mm="mX...."), **{"--alirange": "1-1"}))
    assert invalid["rows"][0]["components"]["actual_masked_count"]["state"] == "incompatible"


def test_multi_alignment_population_is_first_only_and_unsupported_not_zero():
    source = stockholm()
    result = calculate(mask_sheet(source + source, stockholm(mm="m....."), **{"--alirange": "1-1"}))
    values = result["rows"][0]["components"]
    assert values["input_alignment_count"]["value"] == 2
    assert values["processed_alignment_count"]["value"] == values["unprocessed_alignment_count"]["value"] == 1
    unknown = calculate(mask_sheet(b">a\nACGT\n", **{"--informat": "afa", "--alirange": "1-1"}))
    assert unknown["rows"][0]["components"]["input_alignment_count"]["value"] is None


def test_closed_shapes_finite_json_and_bad_parameters():
    result = calculate(build_sheet(), parameters={"background": AMINO_BACKGROUND})
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert all(set(row) == ROW_FIELDS for row in result["rows"])
    assert all(set(row["components"]) <= COMPONENT_FIELDS for row in result["rows"])
    assert all(item["code"] in CHECK_CODES and item["state"] in CHECK_STATES for item in result["checks"])
    assert all(item["code"] in ISSUE_CODES for item in result["issues"])
    invalid = calculate(build_sheet(), parameters={"summary_rounding_tolerance": None})
    assert invalid["issues"][0]["code"] == "parameter_invalid"


def test_missing_stdout_and_mask_are_missing_not_zero():
    source = stockholm()
    result = calculate(mask_sheet(source, mode="model_to_alignment", **{"--hand": True, "--model2ali": "1-1"}))
    count = result["rows"][0]["components"]["native_mapping_row_count"]
    assert count["value"] is None and count["state"] == "missing"
    result = calculate(mask_sheet(source, **{"--alirange": "1-1"}))
    count = result["rows"][0]["components"]["actual_masked_count"]
    assert count["value"] is None and count["state"] == "missing"


@pytest.mark.parametrize("change", ["record_key", "row_geometry", "association", "extraction_occurrence"])
def test_saved_sheet_rejects_conflicting_references_and_geometry(change):
    sheet = build_sheet()
    if change == "record_key":
        sheet["input_records"][0]["record_key"] = "different#alignment/0"
    elif change == "row_geometry":
        sheet["input_records"][0]["rows"][0]["aligned_sequence"] += "A"
    elif change == "association":
        sheet["associations"][0]["source_record_key"] = "absent"
    else:
        sheet["model_extraction"]["occurrence"]["sha256"] = "f" * 64
    result = calculate(sheet)
    assert not result["rows"]
    assert result["issues"][0]["code"] == "sheet_invalid"


def test_nonfinite_kl_and_probability_mass_are_not_renormalized():
    background = dict.fromkeys("ACDEFGHIKLMNPQRSTVWY", 1 / 19)
    background["F"] = 0
    result = calculate(build_sheet(), parameters={"background": background})
    assert result["rows"][0]["components"]["mean_match_relative_entropy"]["state"] == "nonfinite"
    position = result["rows"][0]["model_components"]["positions"][4]
    assert position["match"]["mass"]["value"] == math.exp(-.40547) + math.exp(-1.09861)
    assert position["match"]["mass_residual"]["value"] != 0


def test_full_duplicate_models_use_ordered_occurrences_not_names():
    selected, inputs, outputs, extraction = native_build()
    inputs["alignment"] = [payload("alignment", inputs["alignment"][0]["content"] * 2)]
    outputs["models"] = [payload("models", outputs["models"][0]["content"] * 2, "output")]
    text = outputs["stdout"][0]["content"]
    row = next(line for line in text.splitlines(keepends=True) if line.startswith(b"1    "))
    outputs["stdout"] = [payload("stdout", text + row.replace(b"1    ", b"2    ", 1), "output")]
    extraction = extract_hmmer_models(outputs["models"][0]["content"], occurrence=outputs["models"][0]["occurrence"], format="hmmer3_ascii")
    sheet = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    result = calculate(sheet)
    assert len(result["rows"]) == 2
    assert [row["model_record_key"] for row in result["rows"]] == ["output:models:0#model/0", "output:models:0#model/1"]
    assert all(row["components"]["model_alignment_fraction"]["value"] == 12 / 14 for row in result["rows"])
