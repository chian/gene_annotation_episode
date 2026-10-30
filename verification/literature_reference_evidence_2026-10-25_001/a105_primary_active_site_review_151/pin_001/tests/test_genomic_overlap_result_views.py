"""Selection tests use the supplied hand-worked packet, not a live result claim."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.genomic_overlap_contracts import canonical_genomic_overlap_sheet_sha256
from gene_annotation_episode.genomic_overlap_result_views import project_genomic_overlap_result


PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_genomic_overlap_contract_2026-10-27_418"


@pytest.fixture
def worked():
    return json.loads((PACKET / "WORKED_EXAMPLE.json").read_text())


def _project(worked):
    return project_genomic_overlap_result(worked["sheet"], worked["components"], selector=worked["selector"])


def _select(worked, kind, fields, *, offset=0, limit=100, occurrences=()):
    worked["selector"]["projection"] = {"kind": kind, "measurement_fields": fields,
        "offset": offset, "limit": limit, "occurrence_keys": list(occurrences)}


def _rehash(worked):
    worked["components"]["source_sheet_sha256"] = canonical_genomic_overlap_sheet_sha256(worked["sheet"])


def _failure(*, code="native_output_partial", stage="parse", pair="comparison_0",
             set_key=None, path="/parsed_byte_count", artifact=None, expected=68, observed=34):
    return {"code": code, "stage": stage, "set_key": set_key, "comparison_key": pair,
        "artifact_ref": artifact, "locator": None, "field_path": path,
        "expected_value": expected, "observed_value": observed,
        "partial_artifact_refs": [] if artifact is None else [artifact],
        "requirement": "complete_native_output"}


def _missing_ratio(reason, denominator=None):
    return {"numerator": None, "denominator": denominator, "value": None, "missing_reason": reason}


def _make_unavailable_metrics(pair, *, reason="unavailable_input"):
    for population in ("unfiltered", "selected"):
        for key, value in pair[population].items():
            pair[population][key] = _missing_ratio(reason) if isinstance(value, dict) else None
    pair["observed"] = {"observed_pair_count": None, "observed_pairwise_bp_sum": None,
        "observed_intersection_union_bp": None, "interpretation": "unavailable"}
    pair["intersection_union_segments"] = pair["selected_intersection_union_segments"] = None


def _partial(worked):
    """Hand-supplied first valid row only; missing second row is not a zero."""
    native = worked["sheet"]["comparisons"][0]
    native["result_extent"] = "partial"
    native["parsed_byte_count"] = 34
    native["receipt"]["capture_extent"] = "partial"
    native["receipt"]["native_result_extent"] = "partial"
    native["receipt"]["completeness_basis"] = "partial_native_result"
    native["valid_pairs"] = native["valid_pairs"][:1]
    issue = _failure(artifact=native["receipt"]["stdout"]["artifact_ref"])
    native["issues"] = [issue]
    worked["sheet"]["issues"] = [deepcopy(issue)]
    pair = worked["components"]["pairs"][0]
    pair["result_extent"] = "partial"
    _make_unavailable_metrics(pair, reason="incomplete_native_result")
    pair["observed"] = {"observed_pair_count": 1, "observed_pairwise_bp_sum": 3,
        "observed_intersection_union_bp": 3, "interpretation": "lower_bound_subset"}
    pair["unfiltered"]["a_union_coverage_fraction"]["denominator"] = 15
    pair["unfiltered"]["b_union_coverage_fraction"]["denominator"] = 5
    pair["unfiltered"]["a_region_overlap_fraction"]["denominator"] = 2
    pair["unfiltered"]["b_region_overlap_fraction"]["denominator"] = 1
    pair["edges"] = pair["edges"][:1]
    pair["issues"] = [deepcopy(issue)]
    for row in pair["occurrences"]:
        row.update(result_extent="partial", partner_count=None, covered_bp=None,
                   coverage_fraction=_missing_ratio("incomplete_native_result", row["span_bp"]))
        row["pair_keys"] = [key for key in row["pair_keys"] if key == "p0:a0:b0"]
    _rehash(worked)
    return issue


def _three_sets(worked):
    """Add unavailable C; A/B stays the valid supplied two-edge result."""
    sheet, components = worked["sheet"], worked["components"]
    c_spec = deepcopy(sheet["request"]["region_sets"][1])
    c_spec.update(set_key="C", display_label="unavailable C")
    c_spec["source"]["source_ref"] = "synthetic:missing:C"
    c_spec["source"]["file"]["artifact_ref"] = "synthetic:missing:C"
    sheet["request"]["region_sets"].append(c_spec)
    issue = _failure(code="input_unavailable", stage="input", pair=None, set_key="C",
        path="/source/file", artifact="synthetic:missing:C", expected=None, observed=None)
    issue["requirement"] = "complete_input"
    c_parsed = deepcopy(sheet["sets"][1])
    c_parsed.update(set_key="C", source_file=c_spec["source"]["file"], result_extent="unavailable",
        parsed_byte_count=0, input_data_row_count=None, regions=[], ignored_records=[], invalid_records=[],
        canonical_order=[], coordinate_groups=[], full_record_groups=[], issues=[issue])
    sheet["sets"].append(c_parsed)
    c_component = deepcopy(components["sets"][1])
    c_component.update(set_key="C", result_extent="unavailable", input_data_row_count=None,
        valid_region_count=0, region_count=None, summed_region_bp=None, union_bp=None,
        coordinate_locus_count=None, duplicate_coordinate_excess=None, union_segments=None,
        region_geometry=[], issues=[deepcopy(issue)])
    components["sets"].append(c_component)
    sheet["issues"].append(deepcopy(issue))
    for ordinal, a in ((1, "A"), (2, "B")):
        key = f"comparison_{ordinal}"
        sheet["request"]["comparisons"].append({"comparison_key": key, "ordinal": ordinal,
            "a_set_key": a, "b_set_key": "C"})
        source = sheet["sets"][0 if a == "A" else 1]["source_file"]
        native = deepcopy(sheet["comparisons"][0])
        receipt = native["receipt"]
        receipt.update(comparison_key=key, identity=None, derivation="not_executed_invalid_input",
            outcome="not_executed", software=None, realized_argv=[], environment={}, returncode=None,
            started_at=None, finished_at=None, stdout=None, stderr=None, writer_closed=None,
            capture_extent="unavailable", native_result_extent="unavailable",
            completeness_basis="unavailable", completeness_source_refs=[], issues=[])
        receipt["a"] = {"set_key": a, "original_file": source, "canonical_file": None}
        receipt["b"] = {"set_key": "C", "original_file": c_spec["source"]["file"], "canonical_file": None}
        pair_issue = _failure(code="native_output_unavailable", pair=key, path="/receipt/stdout",
                              expected=None, observed=None)
        native.update(comparison_key=key, result_extent="unavailable", parsed_byte_count=0,
                      valid_pairs=[], rejected_rows=[], issues=[pair_issue])
        sheet["comparisons"].append(native)
        relation = deepcopy(sheet["reference_relations"][0])
        relation.update(comparison_key=key, a_set_key=a, b_set_key="C")
        sheet["reference_relations"].append(relation)
        pair = deepcopy(components["pairs"][0])
        pair.update(comparison_key=key, a_set_key=a, b_set_key="C", result_extent="unavailable",
                    edges=[], issues=[deepcopy(pair_issue)])
        _make_unavailable_metrics(pair)
        pair["occurrences"] = [row for row in pair["occurrences"] if row["set_key"] == a]
        for row in pair["occurrences"]:
            row.update(comparison_key=key, result_extent="unavailable", partner_count=None,
                covered_bp=None, pair_keys=[], coverage_fraction=_missing_ratio("unavailable_input", row["span_bp"]))
        components["pairs"].append(pair)
        sheet["issues"].append(deepcopy(pair_issue))
        components["issues"].append(deepcopy(pair_issue))
    _rehash(worked)


def _empty(worked):
    """Two validated empty inputs: analytic empty, without native stdout."""
    for spec, parsed, calculated in zip(worked["sheet"]["request"]["region_sets"],
                                       worked["sheet"]["sets"], worked["components"]["sets"]):
        identity = {"artifact_ref": "supplied:empty:" + spec["set_key"],
            "sha256": hashlib.sha256(b"").hexdigest(), "size_bytes": 0, "format": spec["format"]}
        spec["source"]["file"] = identity
        parsed.update(source_file=identity, parsed_byte_count=0, input_data_row_count=0,
            regions=[], ignored_records=[], invalid_records=[], canonical_order=[],
            coordinate_groups=[], full_record_groups=[], issues=[])
        calculated.update(input_data_row_count=0, valid_region_count=0, region_count=0,
            summed_region_bp=0, union_bp=0, coordinate_locus_count=0, duplicate_coordinate_excess=0,
            union_segments=[], region_geometry=[])
    native = worked["sheet"]["comparisons"][0]
    native.update(parsed_byte_count=0, valid_pairs=[], rejected_rows=[])
    native["receipt"].update(identity=None, derivation="validated_empty_input", outcome="not_executed",
        software=None, realized_argv=[], environment={}, returncode=None, started_at=None, finished_at=None,
        stdout=None, stderr=None, writer_closed=None, completeness_basis="validated_empty_input",
        completeness_source_refs=[])
    for side, parsed in zip(("a", "b"), worked["sheet"]["sets"]):
        native["receipt"][side] = {"set_key": parsed["set_key"], "original_file": parsed["source_file"], "canonical_file": None}
    pair = worked["components"]["pairs"][0]
    for population in ("unfiltered", "selected"):
        for key, value in pair[population].items():
            pair[population][key] = {"numerator": 0, "denominator": 0, "value": None,
                "missing_reason": "zero_denominator"} if isinstance(value, dict) else 0
    pair.update(observed={"observed_pair_count": 0, "observed_pairwise_bp_sum": 0,
                          "observed_intersection_union_bp": 0, "interpretation": "exact_complete_result"},
        intersection_union_segments=[], selected_intersection_union_segments=[], edges=[], occurrences=[])
    _rehash(worked)


def test_exact_hand_worked_jaccard_only_return(worked):
    result = _project(worked)
    assert result == worked["requested_return"]["overlap"]
    assert result["pair_rows"][0]["measurements"] == {"unfiltered.jaccard_bp": {
        "numerator": 5, "denominator": 15, "value": 1 / 3, "missing_reason": None}}
    assert "edges" not in json.dumps(result)
    assert "pairwise_overlap_bp_sum" not in json.dumps(result)


def test_set_selection_and_paging_keep_only_requested_measurements(worked):
    _select(worked, "set_metrics", ["union_bp", "duplicate_coordinate_excess"], offset=1, limit=1)
    result = _project(worked)
    assert result["set_rows"] == [{"set_key": "B", "result_extent": "complete",
        "measurements": {"union_bp": 5, "duplicate_coordinate_excess": 0}, "issues": []}]
    assert result["page"] == {"offset": 1, "limit": 1, "total_rows": 2, "returned_rows": 1}
    assert result["pair_rows"] == result["occurrence_rows"] == []


def test_occurrence_filter_precedes_page_and_uses_population_endpoint_order(worked):
    _select(worked, "occurrence_rows", ["coverage_fraction", "pair_keys"], offset=1, limit=2,
        occurrences=[{"set_key": "B", "occurrence_key": "r0"}, {"set_key": "A", "occurrence_key": "r1"}])
    result = _project(worked)
    assert [(row["population"], row["set_key"], row["occurrence_key"]) for row in result["occurrence_rows"]] == [
        ("unfiltered", "B", "r0"), ("selected", "A", "r1")]
    assert [row["measurements"] for row in result["occurrence_rows"]] == [
        {"coverage_fraction": {"numerator": 5, "denominator": 5, "value": 1, "missing_reason": None},
         "pair_keys": ["p0:a0:b0", "p0:a1:b0"]},
        {"coverage_fraction": {"numerator": 5, "denominator": 10, "value": .5, "missing_reason": None},
         "pair_keys": ["p0:a1:b0"]}]
    assert result["page"] == {"offset": 1, "limit": 2, "total_rows": 4, "returned_rows": 2}


def test_missing_ratio_and_observed_lower_bound_remain_distinct(worked):
    original_issue = _partial(worked)
    _select(worked, "pair_metrics", ["unfiltered.jaccard_bp", "observed.observed_pairwise_bp_sum"])
    result = _project(worked)
    row = result["pair_rows"][0]
    assert row["measurements"] == {"unfiltered.jaccard_bp": _missing_ratio("incomplete_native_result"),
                                    "observed.observed_pairwise_bp_sum": 3}
    assert row["observed_interpretation"] == "lower_bound_subset"
    assert result["result_extent"] == row["result_extent"] == "partial"
    assert original_issue in result["failures"]
    assert sum(issue == original_issue for issue in result["failures"]) == 1
    missing = [issue for issue in result["failures"] if issue["code"] == "requested_field_unavailable"]
    assert len(missing) == 1 and missing[0]["field_path"] == "/pairs/0/unfiltered/jaccard_bp"


def test_unrequested_calculation_failure_is_not_returned(worked):
    irrelevant = _failure(code="zero_denominator", stage="calculate",
                         path="/pairs/0/selected/b_region_overlap_fraction", expected=None, observed=0)
    worked["components"]["pairs"][0]["issues"] = [irrelevant]
    worked["components"]["issues"] = [deepcopy(irrelevant)]
    assert _project(worked)["failures"] == []
    assert _project(worked)["pair_rows"][0]["issues"] == []


def test_unrelated_comparison_and_set_failures_are_not_returned(worked):
    _three_sets(worked)
    result = _project(worked)
    assert result["result_extent"] == "complete"
    assert result["failures"] == []
    assert len(result["reference_relations"]) == 1


def test_pair_page_retains_population_extent_without_off_page_failure_dump(worked):
    _three_sets(worked)
    worked["selector"]["comparison_keys"] = ["comparison_0", "comparison_1", "comparison_2"]
    result = _project(worked)
    assert result["page"]["total_rows"] == 3 and result["page"]["returned_rows"] == 1
    assert result["result_extent"] == "partial"
    assert result["pair_rows"][0]["result_extent"] == "complete"
    assert result["failures"] == []
    worked["selector"]["projection"]["offset"] = 20
    result = _project(worked)
    assert result["pair_rows"] == [] and result["result_extent"] == "partial"
    assert result["failures"] == []


def test_set_extent_uses_inputs_independently_of_native_failure(worked):
    _partial(worked)
    _select(worked, "set_metrics", ["union_bp"])
    result = _project(worked)
    assert result["result_extent"] == "complete"
    assert [row["measurements"]["union_bp"] for row in result["set_rows"]] == [15, 5]
    assert result["failures"] == []


def test_occurrence_population_keeps_missing_input_failure_even_on_empty_page(worked):
    _three_sets(worked)
    worked["selector"]["comparison_keys"] = ["comparison_1"]
    _select(worked, "occurrence_rows", ["span_bp"], offset=100)
    result = _project(worked)
    assert result["occurrence_rows"] == [] and result["result_extent"] == "unavailable"
    assert result["page"]["total_rows"] == 4
    assert [failure["code"] for failure in result["failures"]] == ["input_unavailable"]
    assert result["failures"][0]["set_key"] == "C"


def test_known_empty_page_is_not_a_failure(worked):
    _select(worked, "occurrence_rows", ["span_bp"], offset=100)
    result = _project(worked)
    assert result["page"]["total_rows"] == 6
    assert result["page"]["returned_rows"] == 0
    assert result["result_extent"] == "complete" and result["failures"] == []


def test_analytic_empty_zero_denominator_is_not_a_measured_zero_ratio(worked):
    _empty(worked)
    result = _project(worked)
    assert result["pair_rows"][0]["measurements"] == {"unfiltered.jaccard_bp": {
        "numerator": 0, "denominator": 0, "value": None, "missing_reason": "zero_denominator"}}
    assert result["result_extent"] == "complete"
    assert [issue["code"] for issue in result["failures"]] == ["zero_denominator"]
    _select(worked, "occurrence_rows", ["span_bp"])
    result = _project(worked)
    assert result["page"]["total_rows"] == result["page"]["returned_rows"] == 0
    assert result["result_extent"] == "complete" and result["failures"] == []


def test_explicit_known_occurrence_filter_does_not_inherit_off_page_missing_set(worked):
    _three_sets(worked)
    worked["selector"]["comparison_keys"] = ["comparison_1"]
    _select(worked, "occurrence_rows", ["span_bp"], offset=100,
            occurrences=[{"set_key": "A", "occurrence_key": "r0"}])
    result = _project(worked)
    assert result["page"]["total_rows"] == 2 and result["page"]["returned_rows"] == 0
    assert result["result_extent"] == "unavailable"
    assert result["failures"] == []


def test_explicit_span_only_needs_own_input_but_coverage_needs_both(worked):
    _three_sets(worked)
    worked["selector"]["comparison_keys"] = ["comparison_1"]
    chosen = [{"set_key": "A", "occurrence_key": "r0"}]
    _select(worked, "occurrence_rows", ["span_bp"], occurrences=chosen, limit=1)
    result = _project(worked)
    assert result["occurrence_rows"][0]["measurements"] == {"span_bp": 10}
    assert result["failures"] == []
    assert result["result_extent"] == "unavailable" and result["page"]["total_rows"] == 2
    _select(worked, "occurrence_rows", ["coverage_fraction"], occurrences=chosen, limit=1)
    result = _project(worked)
    assert result["occurrence_rows"][0]["measurements"] == {
        "coverage_fraction": _missing_ratio("unavailable_input", 10)}
    assert any(issue["code"] == "input_unavailable" and issue["set_key"] == "C" for issue in result["failures"])
    assert any(issue["code"] == "native_output_unavailable" for issue in result["failures"])
    _select(worked, "occurrence_rows", ["span_bp"], limit=1)
    result = _project(worked)
    assert result["occurrence_rows"][0]["measurements"] == {"span_bp": 10}
    assert result["page"]["total_rows"] == 4
    assert [issue["code"] for issue in result["failures"]] == ["input_unavailable"]


def test_no_available_occurrences_preserves_unavailable_input_qualification(worked):
    _empty(worked)
    issues = []
    for parsed, component in zip(worked["sheet"]["sets"], worked["components"]["sets"]):
        issue = _failure(code="input_unavailable", stage="input", pair=None, set_key=parsed["set_key"],
                         path="/source_file", artifact=parsed["source_file"]["artifact_ref"], expected=None, observed=None)
        issue["requirement"] = "complete_input"
        issues.append(issue)
        parsed.update(result_extent="unavailable", input_data_row_count=None, issues=[issue])
        component.update(result_extent="unavailable", input_data_row_count=None, region_count=None,
            summed_region_bp=None, union_bp=None, coordinate_locus_count=None, duplicate_coordinate_excess=None,
            union_segments=None, issues=[deepcopy(issue)])
    native = worked["sheet"]["comparisons"][0]
    native["result_extent"] = "unavailable"
    native["receipt"].update(derivation="not_executed_invalid_input", native_result_extent="unavailable",
                             capture_extent="unavailable", completeness_basis="unavailable")
    worked["sheet"]["issues"] = deepcopy(issues)
    pair = worked["components"]["pairs"][0]
    pair["result_extent"] = "unavailable"
    _make_unavailable_metrics(pair)
    _rehash(worked)
    _select(worked, "occurrence_rows", ["coverage_fraction"])
    result = _project(worked)
    assert result["occurrence_rows"] == []
    assert result["page"]["total_rows"] == result["page"]["returned_rows"] == 0
    assert result["result_extent"] == "unavailable"
    assert result["failures"] == issues  # Original A then B order, despite no returned row.


@pytest.mark.parametrize("mutation", [
    lambda w: w["components"].update(source_sheet_sha256="0" * 64),
    lambda w: w["selector"]["parameters"].update(minimum_overlap_bp=5),
    lambda w: w["selector"]["parameters"]["minimum_a_fraction"].update(denominator=2),
    lambda w: w["selector"].update(comparison_keys=["foreign"]),
    lambda w: w["selector"].update(comparison_keys=["comparison_0", "comparison_0"]),
    lambda w: w["selector"]["projection"].update(measurement_fields=["unfiltered.jaccard_bp"] * 2),
    lambda w: w["selector"]["projection"].update(measurement_fields=["unfiltered.unlisted_measure"]),
    lambda w: w["selector"]["projection"].update(offset=True),
    lambda w: w["selector"]["projection"].update(extra="not allowed"),
    lambda w: w["components"]["pairs"][0]["unfiltered"]["jaccard_bp"].update(value=float("nan")),
    lambda w: w["components"]["pairs"][0]["unfiltered"].update(native_pair_count=True),
    lambda w: w["components"]["sets"].reverse(),
    lambda w: w["components"]["pairs"][0].update(a_set_key="B"),
    lambda w: w["components"]["pairs"][0].update(reference_relation="same_supplied_reference"),
    lambda w: w["components"]["pairs"][0]["occurrences"].reverse(),
    lambda w: w["components"]["pairs"][0]["occurrences"][0].update(pair_keys=["foreign"]),
    lambda w: w["components"]["pairs"][0]["occurrences"][0].update(pair_keys=[]),
    lambda w: w["components"]["pairs"][0]["occurrences"][0].update(span_bp=12),
    lambda w: w["components"]["pairs"][0]["edges"][0].update(a_occurrence_key="r1"),
    lambda w: w["components"]["pairs"][0]["edges"][0].update(overlap_bp=4),
])
def test_invalid_api_contract_or_join_raises(worked, mutation):
    mutation(worked)
    with pytest.raises(ValueError):
        _project(worked)


@pytest.mark.parametrize("occurrences", [
    [{"set_key": "A", "occurrence_key": "r0"}] * 2,
    [{"set_key": "A", "occurrence_key": "foreign"}],
    [{"set_key": "C", "occurrence_key": "r0"}],
])
def test_occurrence_selection_requires_unique_declared_keys(worked, occurrences):
    _select(worked, "occurrence_rows", ["coverage_fraction"], occurrences=occurrences)
    with pytest.raises(ValueError):
        _project(worked)


def test_selector_comparisons_require_request_order(worked):
    _three_sets(worked)
    worked["selector"]["comparison_keys"] = ["comparison_2", "comparison_0"]
    with pytest.raises(ValueError, match="comparison_selection_order"):
        _project(worked)


def test_saved_sheet_selector_is_validated_without_accessing_artifacts(worked):
    canonical = json.dumps(worked["sheet"], sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode()
    worked["selector"].update(mode="saved_sheet_recalculation", saved_sheet_file={
        "artifact_ref": "supplied:qualified:sheet", "sha256": worked["components"]["source_sheet_sha256"],
        "size_bytes": len(canonical), "format": worked["sheet"]["version"]})
    assert _project(worked)["pair_rows"][0]["measurements"] == worked["requested_return"]["overlap"]["pair_rows"][0]["measurements"]
    worked["selector"]["saved_sheet_file"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="saved_selector_sheet_hash"):
        _project(worked)


def test_projector_is_detached_and_performs_no_io_or_execution(worked, monkeypatch):
    before = deepcopy(worked)
    def forbidden(*args, **kwargs):
        raise AssertionError("projection attempted I/O or execution")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    result = _project(worked)
    assert worked == before
    result["pair_rows"][0]["measurements"]["unfiltered.jaccard_bp"]["numerator"] = 999
    result["parameters"]["minimum_overlap_bp"] = 999
    result["reference_relations"][0]["issues"].append({"changed": True})
    assert worked == before
    assert _project(worked) == before["requested_return"]["overlap"]


def test_joined_supplied_readers_calculator_to_projection(worked):
    """One actual pure chain; still supplied synthetic bytes, no native execution."""
    from gene_annotation_episode.genomic_overlap_inputs import (
        build_genomic_overlap_sheet, extract_overlap_reference_metadata,
        parse_bedtools_intersect_wo, parse_region_set,
    )
    from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
    raw = {row["key"]: row["utf8_text"].encode() for row in worked["raw_artifacts"]}
    request = worked["request"]
    parsed = [parse_region_set(raw["input_a" if index == 0 else "input_b"],
              specification=spec, set_position=index) for index, spec in enumerate(request["region_sets"])]
    by_key = {row["set_key"]: row for row in parsed}
    pairs = [parse_bedtools_intersect_wo(raw["native"], pair=request["comparisons"][0], sets=by_key,
             native=worked["supplied_output_metadata_example"])]
    references = extract_overlap_reference_metadata(specifications=request["region_sets"],
                 sets=by_key, comparisons=request["comparisons"])
    sheet = build_genomic_overlap_sheet(request=request, sets=parsed, native_pairs=pairs,
                                       reference_relations=references)
    components = calculate_genomic_overlap_components(sheet, parameters=worked["selector"]["parameters"])
    result = project_genomic_overlap_result(sheet, components, selector=worked["selector"])
    assert result["pair_rows"][0]["measurements"] == {"unfiltered.jaccard_bp": {
        "numerator": 5, "denominator": 15, "value": 1 / 3, "missing_reason": None}}
    assert components["pairs"][0]["unfiltered"]["pairwise_overlap_bp_sum"] == 8
    assert components["pairs"][0]["selected"]["selected_pair_count"] == 1
    assert result["failures"] == []
    assert sheet["comparisons"][0]["receipt"]["identity"] is None
