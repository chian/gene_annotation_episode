"""Independent B1 numerical examples, edge cases and no-I/O recalculation."""

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_alignment_preparation_calculations import calculate_hmmer_alignment_preparation_components as calculate, reconstruct_alimask_model_map
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_alignment_preparation_data import _alignment_records
from test_hmmer_alignment_preparation_data import NATIVE, mask_sheet, payload


def check(result, code):
    return [item for item in result["checks"] if item["code"] == code]


def stockholm(sequence="ACDEFG", rf="xxxxxx", mm=None):
    return ("# STOCKHOLM 1.0\na " + sequence + "\n#=GC RF " + rf + "\n" +
            ("#=GC MM " + mm + "\n" if mm is not None else "") + "//\n").encode()


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
    unknown = calculate(mask_sheet(missing, output, mode="mask_model", **{"--hand": True, "--modelrange": "2-3", "--amino": True}))
    assert unknown["rows"][0]["components"]["requested_union_count"]["state"] == "missing"
    assert check(unknown, "mask_annotation")[0]["state"] == "unknown"


def test_mapping_adjusted_coordinates_no_map_and_unsafe_suffix():
    source = stockholm(sequence="ACDEFG", rf=".x..x.")
    stdout = b"alignment coordinates     model coordinates\n 2..5 -> 1..2\n 3..4 -> -..-  (no map)\n"
    result = calculate(mask_sheet(source, mode="alignment_to_model", stdout=stdout, **{"--ali2model": "1-6,3-4", "--hand": True, "--amino": True}))
    assert check(result, "native_mapping")[0]["state"] == "pass"
    interval = result["rows"][0]["intervals"][0]
    assert interval["inclusive_span"]["value"] == 6
    assert interval["returned_source_span"]["value"] == 4
    assert interval["returned_target_span"]["value"] == 2
    assert result["rows"][0]["intervals"][1]["returned_target_span"]["state"] == "missing"
    unsafe = calculate(mask_sheet(source, mode="alignment_to_model", stdout=b"alignment coordinates model coordinates\n6..6 -> -..- (no map)\n", **{"--ali2model": "6-6", "--hand": True, "--amino": True}))
    assert "unsafe_native_range" in {i["code"] for i in unsafe["issues"]}
    assert check(unsafe, "native_mapping")[0]["state"] == "fail"


def test_fast_weighting_changes_map_and_gap_half_boundary_is_exact():
    source = b"# STOCKHOLM 1.0\n#=GS a WT 0.1\n#=GS b WT 3.0\na ACGT\nb A--T\n//\n"
    sheet = mask_sheet(source, **{"--alirange": "1-1", "--dna": True})
    record = sheet["input_records"][0]
    unweighted = reconstruct_alimask_model_map(record, settings={"--dna": True, "--wnone": True, "--fragthresh": 0, "--symfrac": .5})
    given = reconstruct_alimask_model_map(record, settings={"--dna": True, "--wgiven": True, "--fragthresh": 0, "--symfrac": .5})
    assert unweighted["map"] == [1, 2, 3, 4]
    assert given["map"] == [1, 4]
    pb = reconstruct_alimask_model_map(record, settings={"--dna": True, "--wpb": True, "--fragthresh": 0})
    assert pb["pb_consensus_columns"] == [1, 4]  # PB strict gap fraction < .5.


@pytest.mark.parametrize("settings,reason", [({"--wpb": True}, "alphabet_missing")])
def test_unknown_fast_branches_are_explicit(settings, reason):
    # This checks legacy saved-record absence, using the unchanged structural
    # reader. A fresh unflagged short source now refuses native alphabet inference.
    source = _alignment_records(payload("alignment", stockholm(sequence="ACGT", rf="xxxx")),
        "stockholm", {"engine_version": "3.4"}, {"issues": [], "native_rows": []})[0]
    assert "input_decoding" not in source
    result = reconstruct_alimask_model_map(source, settings=settings)
    assert result["map"] is None and result["state"] == "missing"
    assert result["issues"][0]["code"] == reason


def test_pb_sampling_is_not_implicitly_replaced_by_full_population_weights():
    source = mask_sheet(stockholm(sequence="A", rf="x"), **{"--alirange": "1-1", "--amino": True})["input_records"][0]
    source["rows"] *= 50001
    result = reconstruct_alimask_model_map(source, settings={"--amino": True, "--wpb": True})
    assert result["map"] is None and result["issues"][0]["code"] == "map_context_unavailable"


def test_wrong_source_bytes_width_mm_bounds_and_capacity():
    result = calculate(mask_sheet(stockholm(), stockholm(mm="mmmmmm"), **{"--alirange": "5-8", "--amino": True}))
    assert "range_out_of_bounds" in {i["code"] for i in result["issues"]}
    assert result["rows"][0]["components"]["requested_union_count"]["state"] == "incompatible"
    capacity = calculate(mask_sheet(stockholm(), stockholm(mm="m....."), **{"--alirange": ",".join(["1-1"] * 101), "--amino": True}))
    assert check(capacity, "range_capacity")[0]["state"] == "fail"
    invalid = calculate(mask_sheet(stockholm(), stockholm(mm="mX...."), **{"--alirange": "1-1", "--amino": True}))
    assert invalid["rows"][0]["components"]["actual_masked_count"]["state"] == "incompatible"


def test_multi_alignment_population_is_first_only_and_unsupported_not_zero():
    source = stockholm()
    result = calculate(mask_sheet(source + source, stockholm(mm="m....."), **{"--alirange": "1-1", "--amino": True}))
    values = result["rows"][0]["components"]
    assert values["input_alignment_count"]["value"] == 2
    assert values["processed_alignment_count"]["value"] == values["unprocessed_alignment_count"]["value"] == 1
    unknown = calculate(mask_sheet(b">a\nACGT\n", **{"--informat": "afa", "--alirange": "1-1"}))
    assert unknown["rows"][0]["components"]["input_alignment_count"]["value"] is None


def test_missing_stdout_and_mask_are_missing_not_zero():
    source = stockholm()
    result = calculate(mask_sheet(source, mode="model_to_alignment", **{"--hand": True, "--model2ali": "1-1", "--amino": True}))
    count = result["rows"][0]["components"]["native_mapping_row_count"]
    assert count["value"] is None and count["state"] == "missing"
    result = calculate(mask_sheet(source, **{"--alirange": "1-1", "--amino": True}))
    count = result["rows"][0]["components"]["actual_masked_count"]
    assert count["value"] is None and count["state"] == "missing"


