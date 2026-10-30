"""Supplied-record capture-loss cases; no filesystem recovery or live execution."""
from copy import deepcopy
import builtins
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
from gene_annotation_episode.genomic_overlap_contracts import canonical_genomic_overlap_sheet_sha256
from gene_annotation_episode.genomic_overlap_inputs import (
    _native_complete, build_genomic_overlap_sheet, parse_bedtools_intersect_wo, parse_region_set,
)
from gene_annotation_episode.genomic_overlap_result_views import project_genomic_overlap_result
from test_genomic_overlap_inputs import (
    PARAMETERS, ROW, identity, inputs, parsed_pairs, receipt, sheet_from,
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def loss_case(missing=(1,)):
    request, original = inputs([b"chr1\t0\t10\n", b""])
    pair = request["comparisons"][0]
    native = receipt(pair, original, None, derivation="validated_empty_input")
    native.update(writer_closed=True, completeness_source_refs=["synthetic:original-analytic-seal"])
    current = deepcopy(original)
    for index in missing:
        current[index] = parse_region_set(None, specification=request["region_sets"][index], set_position=index)
    native["capture_extent"] = "unavailable"
    return request, current, native


def parse_loss(request, sets, native, content=None):
    return parse_bedtools_intersect_wo(content, pair=request["comparisons"][0],
        sets={row["set_key"]: row for row in sets}, native=native)


def mixed_example():
    """Original A=[0,10),[5,15), B=[7,12), C empty, then supplied C loss."""
    request, original_sets = inputs([b"chr1\t0\t10\nchr1\t5\t15\n", b"chr1\t7\t12\n", b""])
    raw = ROW + b"chr1\t5\t15\ts0_r1\tchr1\t7\t12\ts1_r0\t5\n"
    original_pairs = [parsed_pairs(request, original_sets, raw)]
    for index in (1, 2):
        original_pairs.append(parsed_pairs(request, original_sets, None,
            derivation="validated_empty_input", pair_index=index))
    original = sheet_from(request, original_sets, original_pairs)
    current_sets = deepcopy(original_sets)
    current_sets[2] = parse_region_set(None, specification=request["region_sets"][2], set_position=2)
    current_pairs = [deepcopy(original_pairs[0])]
    by_key = {row["set_key"]: row for row in current_sets}
    for index in (1, 2):
        native = deepcopy(original_pairs[index]["receipt"])
        native["capture_extent"] = "unavailable"
        current_pairs.append(parse_bedtools_intersect_wo(None, pair=request["comparisons"][index],
            sets=by_key, native=native))
    return original, sheet_from(request, current_sets, current_pairs)


def selector(sheet, parameters=PARAMETERS, keys=("comparison_0",)):
    return {"version": "genomic_overlap_result_selector_v1", "mode": "native_result",
        "comparison_keys": list(keys), "saved_sheet_file": None, "parameters": deepcopy(parameters),
        "projection": {"kind": "pair_metrics", "offset": 0, "limit": 10,
            "measurement_fields": ["unfiltered.jaccard_bp"], "occurrence_keys": []}}


@pytest.mark.parametrize("missing", [(0,), (1,), (0, 1)])
def test_current_loss_keeps_original_analytic_facts_and_never_infers_zero(missing):
    request, sets, native = loss_case(missing)
    before = canonical(native)
    parsed = parse_loss(request, sets, native)
    assert parsed["receipt"] == native and canonical(native) == before
    assert parsed["result_extent"] == "unavailable"
    assert parsed["parsed_byte_count"] == 0
    assert parsed["valid_pairs"] == parsed["rejected_rows"] == parsed["issues"] == []
    assert native["issues"] == []  # Located ParsedRegionSet failures suffice.
    assert not _native_complete(parsed["receipt"])
    sheet = sheet_from(request, sets, [parsed])
    components = calculate_genomic_overlap_components(sheet, parameters=PARAMETERS)
    pair = components["pairs"][0]
    assert pair["unfiltered"]["jaccard_bp"] == {
        "numerator": None, "denominator": None, "value": None, "missing_reason": "unavailable_input"}
    assert pair["unfiltered"]["native_pair_count"] is None
    assert pair["observed"] == {"observed_pair_count": None, "observed_pairwise_bp_sum": None,
        "observed_intersection_union_bp": None, "interpretation": "unavailable"}
    for index in missing:
        assert components["sets"][index]["input_data_row_count"] is None
        assert components["sets"][index]["region_count"] is None
        assert components["sets"][index]["union_bp"] is None
    parsed["receipt"]["completeness_source_refs"].clear()
    assert canonical(native) == before  # Detached output, original receipt unchanged.


@pytest.mark.parametrize("code,stage,requirement", [
    ("input_unavailable", "input", "complete_input"),
    ("input_unavailable", "capture", "complete_input"),
    ("input_digest_mismatch", "capture", "matching_file_identity"),
    ("artifact_digest_mismatch", "capture", "matching_file_identity"),
    ("native_output_unavailable", "capture", "complete_input"),
])
def test_located_receipt_failure_can_supply_current_unavailability(code, stage, requirement):
    request, sets, native = loss_case()
    failure = sets[1]["issues"].pop()
    failure.update(code=code, stage=stage, requirement=requirement,
        comparison_key=request["comparisons"][0]["comparison_key"])
    native["issues"] = [failure]
    parsed = parse_loss(request, sets, native)
    sheet = sheet_from(request, sets, [parsed])
    assert parsed["result_extent"] == "unavailable"
    assert sheet["issues"] == [failure]
    assert native["issues"] == [failure]


@pytest.mark.parametrize("change", [
    {"set_key": None}, {"set_key": "A"}, {"set_key": "foreign"},
    {"comparison_key": "foreign"}, {"stage": "native"}, {"stage": "calculate"},
    {"code": "zero_denominator"}, {"requirement": "original_native_output"},
])
def test_unlocated_unrelated_or_noninput_failure_cannot_authorize_loss(change):
    request, sets, native = loss_case()
    failure = sets[1]["issues"].pop()
    failure.update(change)
    native["issues"] = [failure]
    with pytest.raises(ValueError, match="analytic_input_failure"):
        parse_loss(request, sets, native)


@pytest.mark.parametrize("unlocated_index", [0, 1])
def test_every_unavailable_operand_requires_its_own_location(unlocated_index):
    request, sets, native = loss_case((0, 1))
    sets[unlocated_index]["issues"].clear()
    with pytest.raises(ValueError, match="analytic_input_failure"):
        parse_loss(request, sets, native)


@pytest.mark.parametrize("change", [
    {"capture_extent": "complete"}, {"capture_extent": "partial"},
    {"native_result_extent": "partial"}, {"native_result_extent": "unavailable"},
    {"completeness_basis": "unavailable"}, {"completeness_basis": "partial_native_result"},
    {"outcome": "succeeded"}, {"returncode": 0},
    {"started_at": "2026-10-27T00:00:00Z"}, {"finished_at": "2026-10-27T00:00:01Z"},
    {"realized_argv": ["bedtools", "intersect"]}, {"environment": {"LC_ALL": "C"}},
    {"software": {"executable": "bedtools", "declared_version": None,
                  "observed_version": None, "executable_sha256": None}},
    {"stdout": identity(b"", "bedtools_intersect_wo_bed4_v1")},
    {"stderr": identity(b"", "native_stderr_text_v1")},
])
def test_current_loss_requires_exact_extent_basis_and_uninvoked_facts(change):
    request, sets, native = loss_case()
    native.update(deepcopy(change))
    with pytest.raises(ValueError):
        parse_loss(request, sets, native)


@pytest.mark.parametrize("raw", [b"", b"unexpected\n"])
@pytest.mark.parametrize("stream", [False, True])
def test_current_analytic_loss_requires_content_none_even_for_empty_stream(raw, stream):
    request, sets, native = loss_case()
    with pytest.raises(ValueError, match="analytic_native_bytes"):
        parse_loss(request, sets, native, io.BytesIO(raw) if stream else raw)


@pytest.mark.parametrize("other_unavailable", [False, True])
@pytest.mark.parametrize("raw", [b"chr1\t3\t3\n", b"bad\n", b"chr1\t0\t10\nbad\n"])
def test_available_invalid_input_cannot_be_relabelled_as_capture_loss(raw, other_unavailable):
    request, sets = inputs([raw, b""])
    native = receipt(request["comparisons"][0], sets, None, derivation="validated_empty_input")
    native["capture_extent"] = "unavailable"
    if other_unavailable:
        sets[1] = parse_region_set(None, specification=request["region_sets"][1], set_position=1)
    assert sets[0]["result_extent"] == "partial"
    with pytest.raises(ValueError, match="invalid_analytic_empty"):
        parse_loss(request, sets, native)


def test_available_partial_prefix_is_not_current_capture_loss():
    request, sets = inputs([b"chr1\t0\t10\nchr1\t5\t15\n", b""])
    native = receipt(request["comparisons"][0], sets, None, derivation="validated_empty_input")
    native["capture_extent"] = "unavailable"
    sets[0] = parse_region_set(b"chr1\t0\t10\n", specification=request["region_sets"][0], set_position=0)
    assert sets[0]["result_extent"] == "partial"
    with pytest.raises(ValueError, match="invalid_analytic_empty"):
        parse_loss(request, sets, native)


@pytest.mark.parametrize("capture", ["complete", "unavailable"])
def test_available_nonempty_operands_reject_analytic_assertion_despite_failure(capture):
    request, sets = inputs([b"chr1\t0\t10\n", b"chr1\t7\t12\n"])
    native = receipt(request["comparisons"][0], sets, None, derivation="validated_empty_input")
    native["capture_extent"] = capture
    native["issues"] = parse_region_set(None, specification=request["region_sets"][1], set_position=1)["issues"]
    with pytest.raises(ValueError, match="invalid_analytic_empty"):
        parse_loss(request, sets, native)


@pytest.mark.parametrize("extent", ["complete", "partial"])
def test_builder_and_saved_recalculation_reject_forged_current_pair_extent(extent):
    _, sheet = mixed_example()
    sheet["comparisons"][1]["result_extent"] = extent
    with pytest.raises(ValueError):
        build_genomic_overlap_sheet(request=sheet["request"], sets=sheet["sets"],
            native_pairs=sheet["comparisons"], reference_relations=sheet["reference_relations"])
    with pytest.raises(ValueError):
        calculate_genomic_overlap_components(sheet, parameters=PARAMETERS)


@pytest.mark.parametrize("change", ["capture", "failure", "bytes", "rows"])
def test_builder_rechecks_current_loss_in_supplied_saved_records(change):
    _, sheet = mixed_example()
    pair = sheet["comparisons"][1]
    if change == "capture":
        pair["receipt"]["capture_extent"] = "complete"
    elif change == "failure":
        sheet["sets"][2]["issues"].clear()
    elif change == "bytes":
        pair["parsed_byte_count"] = 1
    else:
        pair["valid_pairs"] = deepcopy(sheet["comparisons"][0]["valid_pairs"])
    with pytest.raises(ValueError):
        calculate_genomic_overlap_components(sheet, parameters=PARAMETERS)


def test_original_invalid_input_remains_original_invalid_input_after_map_loss():
    request, sets = inputs([b"chr1\t3\t3\n", b"chr1\t7\t12\n"])
    native = receipt(request["comparisons"][0], sets, None, derivation="not_executed_invalid_input")
    before = canonical(native)
    original = parse_loss(request, sets, native)
    sets[0] = parse_region_set(None, specification=request["region_sets"][0], set_position=0)
    current = parse_loss(request, sets, native)
    assert original["result_extent"] == current["result_extent"] == "unavailable"
    assert canonical(current["receipt"]) == before
    assert current["receipt"]["derivation"] == "not_executed_invalid_input"
    assert current["receipt"]["native_result_extent"] == "unavailable"
    sheet_from(request, sets, [current])


def test_three_set_loss_preserves_exact_ab_order_null_c_and_scoped_projection():
    original, current = mixed_example()
    original_before, current_before = canonical(original), canonical(current)
    components = calculate_genomic_overlap_components(current, parameters=PARAMETERS)
    assert current["request"] == original["request"]
    assert current["sets"][:2] == original["sets"][:2]
    assert current["comparisons"][0] == original["comparisons"][0]
    assert [pair["comparison_key"] for pair in components["pairs"]] == [
        "comparison_0", "comparison_1", "comparison_2"]
    assert [pair["result_extent"] for pair in components["pairs"]] == ["complete", "unavailable", "unavailable"]
    ab = components["pairs"][0]["unfiltered"]
    assert (ab["native_pair_count"], ab["pairwise_overlap_bp_sum"],
            ab["intersection_union_bp"], ab["combined_union_bp"]) == (2, 8, 5, 15)
    assert ab["jaccard_bp"] == {"numerator": 5, "denominator": 15, "value": 1 / 3, "missing_reason": None}
    for index in (1, 2):
        native = current["comparisons"][index]["receipt"]
        assert {**native, "capture_extent": "complete"} == original["comparisons"][index]["receipt"]
        pair = components["pairs"][index]
        assert pair["unfiltered"]["jaccard_bp"] == {
            "numerator": None, "denominator": None, "value": None, "missing_reason": "unavailable_input"}
        assert pair["observed"]["interpretation"] == "unavailable"
    c = components["sets"][2]
    assert c["valid_region_count"] == 0
    assert c["input_data_row_count"] is c["region_count"] is c["union_bp"] is None
    projection = project_genomic_overlap_result(current, components, selector=selector(current))
    assert projection["result_extent"] == "complete" and projection["failures"] == []
    assert projection["pair_rows"][0]["issues"] == []
    assert projection["pair_rows"][0]["measurements"] == {"unfiltered.jaccard_bp": ab["jaccard_bp"]}
    assert canonical(original) == original_before and canonical(current) == current_before


def test_saved_loss_sheet_recalculates_without_files_and_preserves_history(monkeypatch, tmp_path):
    original, current = mixed_example()
    original_raw, current_raw = canonical(original), canonical(current)
    original_file, current_file = tmp_path / "original-sheet.json", tmp_path / "current-sheet.json"
    original_file.write_bytes(original_raw)
    current_file.write_bytes(current_raw)
    old = calculate_genomic_overlap_components(current, parameters=PARAMETERS)
    old_raw = canonical(old)
    receipt_raw = [canonical(pair["receipt"]) for pair in current["comparisons"]]
    saved = json.loads(current_file.read_bytes())
    parameters = {**deepcopy(PARAMETERS), "minimum_overlap_bp": 4}
    selected = selector(saved, parameters)
    selected.update(mode="saved_sheet_recalculation",
                    saved_sheet_file=identity(current_raw, current["version"]))
    def forbidden(*args, **kwargs):
        raise AssertionError("saved analytic-loss calculation attempted acquisition or execution")
    with monkeypatch.context() as guard:
        for owner, name in ((builtins, "open"), (Path, "open"), (socket, "socket"), (subprocess, "Popen")):
            guard.setattr(owner, name, forbidden)
        changed = calculate_genomic_overlap_components(saved, parameters=parameters)
        projected = project_genomic_overlap_result(saved, changed, selector=selected)
    assert changed["pairs"][0]["selected"]["selected_pair_count"] == 1
    assert changed["pairs"][0]["selected"]["selected_pairwise_bp_sum"] == 5
    assert changed["pairs"][0]["selected"]["a_region_overlap_fraction"]["value"] == .5
    assert changed["pairs"][0]["unfiltered"] == old["pairs"][0]["unfiltered"]
    assert all(pair["selected"]["selected_pair_count"] is None for pair in changed["pairs"][1:])
    assert projected["pair_rows"][0]["measurements"]["unfiltered.jaccard_bp"]["value"] == 1 / 3
    assert projected["failures"] == []
    assert canonical(saved) == current_raw and canonical(old) == old_raw
    assert [canonical(pair["receipt"]) for pair in saved["comparisons"]] == receipt_raw
    assert original_file.read_bytes() == original_raw and current_file.read_bytes() == current_raw
    assert canonical(original) == original_raw and canonical(current) == current_raw
    assert changed["source_sheet_sha256"] == old["source_sheet_sha256"] == canonical_genomic_overlap_sheet_sha256(saved)
