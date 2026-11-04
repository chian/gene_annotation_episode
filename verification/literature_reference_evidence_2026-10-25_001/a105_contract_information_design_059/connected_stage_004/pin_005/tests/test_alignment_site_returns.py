"""Synthetic saved-sheet and actual closed-form boundary tests; no native execution."""
from copy import deepcopy
import builtins
import json
import socket
import subprocess

import pytest

from gene_annotation_episode.alignment_site_returns import (
    alignment_site_fact_sources, requested_site_projections,
    project_reference_site_return, project_blast_column_return,
    project_site_action_return, validate_frozen_site_return,
)
from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, validate_closed_schema, validate_form,
)


REFERENCE = "reference_site_rows"
BLAST = "blast_hsp_column_rows"
ALIGNMENT = "observation_" + "a" * 24
OTHER = "observation_" + "b" * 24
QUERY = "input_" + "c" * 24
TARGET = "reference_" + "d" * 24
SOURCE = "source_" + "e" * 24
ARTIFACT = "artifact_" + "f" * 24
MINIMUM = ("selection_policy", "alignment_ref", "selection", "data_status")


def form_schema(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def subset(node, names):
    node["properties"] = {name: node["properties"][name] for name in names}
    node["required"] = list(names)
    return node


def request(source=REFERENCE, policy="all_own_completed_results", *, groups=None, rows=None,
            components=None, insertions=None, positions=(3, 4, 5, 6, 7, 8, 0), window=None):
    fields = alignment_site_fact_sources()[source]["report_schema"]
    group = fields["items"]
    props = group["properties"]
    props["selection_policy"] = {"type": "string", "const": policy}
    if policy != "all_own_completed_results":
        props["alignment_ref"]["const"] = ALIGNMENT
    selection = props["selection"]["properties"]
    if policy == "matching_alignment_window":
        if source == REFERENCE:
            selection["kind"] = {"type": "string", "const": "reference_window"}
            window = window or {"start": 3, "end": 9}
        else:
            window = window or {"column_offset": 2, "column_limit": 4}
        for key, value in window.items():
            selection[key]["const"] = value
    elif policy == "matching_alignment_position_set":
        selection["kind"] = {"type": "string", "const": "reference_positions"}
        selection["positions"]["items"]["enum"] = list(positions)
    if rows is not None:
        subset(props["rows"]["items"], rows)
    if components is not None:
        subset(props["components"], components)
    if insertions is not None:
        subset(props["insertions"]["items"], insertions)
    if groups is not None:
        subset(group, groups)
    return fields


def _mapping(interval):
    return {"original_intervals": None if interval is not None else [],
        "mapping_status": "unavailable" if interval is not None else "not_applicable",
        "mapping_reason": "site_original_mapping_unavailable" if interval is not None else None}


def reference_fixture():
    positions = [3, 4, 5, 6, 7, 8, 0, 5]
    native = {"aligned": True, "aligned_query": "ACD-EFG", "aligned_reference": "ACTVE-G",
        "query_length": 10, "reference_length": 12, "native_score": 42.0,
        "mode": "local", "matrix": "BLOSUM62", "gap_open": -2, "gap_extend": -0.5,
        "biopython_version": "synthetic", "query_interval": [1, 7], "reference_interval": [3, 9],
        "coordinates": [[1, 4, 4, 5, 6, 7], [3, 6, 7, 8, 8, 9]],
        "paired_positions": 5, "identical_positions": 4, "identity_fraction": 0.8,
        "query_coverage": 0.6, "reference_coverage": 0.5}
    lookup = {3: (1, "A", "A", "identical", 0), 4: (2, "C", "C", "identical", 1),
        5: (3, "D", "T", "substituted", 2), 6: (None, "-", "V", "query_gap", 3),
        7: (4, "E", "E", "identical", 4), 8: (6, "G", "G", "identical", 6),
        0: (None, None, None, "outside_alignment", None)}
    rows = []
    for ordinal, position in enumerate(positions):
        qpos, qsym, rsym, relationship, column = lookup[position]
        qinterval = None if qpos is None else [qpos, qpos + 1]
        rinterval = [position, position + 1]
        rows.append({"request_ordinal": ordinal, "reference_position": position,
            "reference_interval": rinterval, "query_interval": qinterval, "query_position": qpos,
            "reference_symbol": rsym, "query_symbol": qsym, "query_original_symbol": None,
            "relationship": relationship, "alignment_column": column, "native_operation": None,
            "query_strand": "+", "query_quality_character": None, "query_quality_score": None,
            "quality_encoding": "unspecified", "quality_scale": None,
            **{"query_" + key: value for key, value in _mapping(qinterval).items()},
            **{"reference_" + key: value for key, value in _mapping(rinterval).items()},
            "unavailable_reason": None})
    insertions = [{"event_ordinal": 0, "reference_boundary": 8, "query_interval": [5, 6],
        "query_strand": "+", "query_sequence": "F", "query_quality_characters": None,
        "alignment_column_interval": [5, 6],
        **{"query_" + key: value for key, value in _mapping([5, 6]).items()}}]
    summary = dict(zip(("requested_position_count", "unique_requested_position_count",
        "duplicate_requested_position_count", "identical_positions", "substituted_positions",
        "paired_positions", "query_gap_positions", "reference_skip_positions",
        "outside_alignment_positions", "unavailable_positions", "aligned_reference_positions",
        "selected_insertion_events", "inserted_query_positions", "selected_query_paired_units",
        "selected_reference_paired_units"), (8, 7, 1, 4, 1, 5, 1, 0, 1, 0, 6, 1, 1, 5, 5)))
    ratios = {name: {"numerator": n, "denominator": d, "value": v} for name, n, d, v in (
        ("selected_paired_identity", 4, 5, 0.8), ("selected_alignment_identity", 4, 7, 4 / 7),
        ("selected_reference_aligned_fraction", 6, 7, 6 / 7),
        ("selected_reference_paired_fraction", 5, 7, 5 / 7),
        ("selected_query_paired_coverage", 5, 10, 0.5),
        ("selected_reference_paired_coverage", 5, 12, 5 / 12))}
    counts = deepcopy(summary)
    summary.update({name: ratio["value"] for name, ratio in ratios.items()})
    sheet = {"schema": "reference_site_comparison_sheet_v1", "mode": "biopython_pairwise",
        "status": "partial", "source": {"alignment_ref": ALIGNMENT, "source_ref": SOURCE,
            "native_artifact_ref": ARTIFACT, "provider": "biopython.alignment",
            "format": "biopython_pairwise_json", "native_version": "synthetic", "native_locator": {}},
        "operands": {"query": {"subject_ref": QUERY, "length": 10, "unit": "aa",
            "alignment_unit": "aa", "molecule": "protein"}, "reference": {"subject_ref": TARGET,
            "length": 12, "unit": "aa", "alignment_unit": "aa", "molecule": "protein"}},
        "selection": {"kind": "reference_positions", "positions": positions},
        "requested_positions": positions.copy(), "unique_requested_positions": [3, 4, 5, 6, 7, 8, 0],
        "native_input": native, "native_parameters": {"mode": "local"},
        "inherited_native_measurements": {"native_score": 42.0},
        "symbol_interpretation": {"basis": "native_symbols"}, "original_mapping_inputs": None,
        "sites": rows, "insertions": insertions, "measured_counts": deepcopy(counts),
        "availability": {"local_correspondence": True, "insertion_correspondence": True, "quality": "unavailable"},
        "issues": [{"code": "site_original_mapping_unavailable", "role": "reference"}]}
    scores = {"schema": "reference_site_components_v1", "status": "partial", "summary": summary,
        "ratios": ratios, "observed_subset_counts": counts,
        "component_status": {name: "available" for name in summary}, "issues": [],
        "definitions": {"population": "synthetic_explicit_selected_reference_positions"}}
    return sheet, scores


def blast_fixture():
    columns = []
    for column, qsym, rsym, qinterval, rinterval, relationship in (
        (2, "G", "G", [4, 5], [8, 9], "identical"),
        (3, "-", "T", None, [7, 8], "query_gap"),
        (4, "T", "-", [5, 6], None, "reference_gap"),
        (5, "A", "A", [6, 7], [6, 7], "identical")):
        columns.append({"column": column, "query_symbol": qsym, "reference_symbol": rsym,
            "query_interval": qinterval, "reference_interval": rinterval,
            "query_unit": "nt", "reference_unit": "nt", "alignment_unit": "nt",
            "query_direction": 1, "reference_direction": -1,
            "query_frame": None, "reference_frame": None,
            "query_strand": "Plus", "reference_strand": "Minus", "relationship": relationship,
            **{"query_" + key: value for key, value in _mapping(qinterval).items()},
            **{"reference_" + key: value for key, value in _mapping(rinterval).items()}})
    summary = {"window_alignment_columns": 4, "paired_columns": 2, "identical_pairs": 2,
        "substituted_pairs": 0, "query_gap_columns": 1, "reference_gap_columns": 1,
        "query_paired_units": 2, "reference_paired_units": 2}
    ratios = {name: {"numerator": n, "denominator": d, "value": v} for name, n, d, v in (
        ("paired_identity", 2, 2, 1.0), ("alignment_identity", 2, 4, 0.5),
        ("query_paired_coverage", 2, 12, 2 / 12), ("reference_paired_coverage", 2, 18, 2 / 18))}
    counts = deepcopy(summary)
    summary.update({name: ratio["value"] for name, ratio in ratios.items()})
    sheet = {"schema": "blast_hsp_column_sheet_v1", "status": "complete", "program": "blastn",
        "native_version": "synthetic", "source": {"alignment_ref": ALIGNMENT, "source_ref": SOURCE,
            "native_artifact_ref": ARTIFACT, "provider": "ncbi.blast", "format": "ncbi_blast_json_hsp",
            "native_version": "synthetic", "native_locator": {"report_ordinal": 0, "hit_ordinal": 2, "hsp_ordinal": 3}},
        "operands": {"query": {"subject_ref": QUERY, "length": 12, "unit": "nt",
            "alignment_unit": "nt", "molecule": "dna"}, "reference": {"subject_ref": TARGET,
            "length": 18, "unit": "nt", "alignment_unit": "nt", "molecule": "dna"}},
        "native_input": {"qseq": "ACG-TAGG", "hseq": "ACGT-AGG", "query_from": 3,
            "query_to": 9, "hit_from": 11, "hit_to": 5, "bit_score": 0, "evalue": 0},
        "inherited_native_measurements": {"bit_score": 0, "evalue": 0},
        "requested_window": {"column_offset": 2, "column_limit": 4},
        "realized_window": {"column_offset": 2, "column_end": 6},
        "total_columns": 8, "next_column_offset": 6, "columns": columns,
        "original_mapping_inputs": None, "measured_counts": counts,
        "availability": {"traceback": "available", "geometry": "available"}, "issues": []}
    scores = {"schema": "blast_hsp_column_components_v1", "status": "complete", "summary": summary,
        "ratios": ratios, "component_status": {name: "available" for name in summary},
        "issues": [], "definitions": {"population": "synthetic_explicit_alignment_window"}}
    return sheet, scores


def action_fixture(source=REFERENCE):
    sheet, scores = reference_fixture() if source == REFERENCE else blast_fixture()
    return {"decision_index": 7, "operation_ref": "operation_" + "1" * 24,
        "tool_name": "sequence.sites" if source == REFERENCE else "result.blast.hsp",
        "operation_status": "completed", "arguments": {"alignment_ref": ALIGNMENT,
            "positions": sheet["selection"]["positions"].copy()} if source == REFERENCE else
            {"observation_ref": ALIGNMENT, **sheet["requested_window"]},
        "binding": {"alignment_ref": ALIGNMENT, "native_source_ref": SOURCE,
            "native_artifact_ref": ARTIFACT, "result_source_ref": "source_" + "2" * 24 if source == REFERENCE else None,
            "result_observation_ref": "observation_" + "3" * 24 if source == REFERENCE else None,
            "native_locator": None if source == REFERENCE else sheet["source"]["native_locator"]},
        "grading_artifact_ref": "artifact_" + "4" * 24,
        "grading": {"sheet": sheet, "scores": scores, "failure": None},
        "availability": "bound", "feedback_code": None}


def assert_error(code, callback):
    with pytest.raises(ReportBoundaryError) as caught:
        callback()
    assert caught.value.diagnostic["code"] == code


def test_catalog_uses_actual_closed_communication_grammar_and_is_detached():
    catalog = alignment_site_fact_sources()
    assert set(catalog) == {REFERENCE, BLAST}
    validate_closed_schema(form_schema(**{name: entry["report_schema"] for name, entry in catalog.items()}))
    catalog[REFERENCE]["report_schema"]["items"]["properties"].clear()
    assert alignment_site_fact_sources()[REFERENCE]["report_schema"]["items"]["properties"]


@pytest.mark.parametrize("source,policy", [(REFERENCE, policy) for policy in (
    "all_own_completed_results", "matching_alignment", "matching_alignment_window", "matching_alignment_position_set")]
    + [(BLAST, policy) for policy in ("all_own_completed_results", "matching_alignment", "matching_alignment_window")])
def test_all_explicit_selectors_have_exact_canonical_shape(source, policy):
    fields = request(source, policy)
    result = requested_site_projections(form_schema(result=fields))[source]
    assert set(result) == {"selection", "fields"}
    assert set(result["selection"]) == {"policy", "alignment_refs", "positions", "window"}
    assert result["selection"]["policy"] == policy
    assert result["selection"]["alignment_refs"] == (None if policy == "all_own_completed_results" else [ALIGNMENT])
    assert result["fields"] == fields
    result["fields"]["items"]["properties"].clear()
    assert fields["items"]["properties"]


@pytest.mark.parametrize("policy", [None, "latest", "all_history", "matching_alignment_position_set"])
def test_absent_unknown_or_source_incompatible_policy_is_rejected(policy):
    fields = request(BLAST)
    if policy is None:
        fields["items"]["properties"]["selection_policy"] = {"type": "string", "enum": ["matching_alignment"]}
    else:
        fields["items"]["properties"]["selection_policy"]["const"] = policy
    assert_error("alignment_site_explicit_selection_required", lambda: requested_site_projections(form_schema(x=fields)))


def test_reference_enum_uses_first_occurrence_order_and_exact_refs():
    fields = request(policy="matching_alignment")
    ref = fields["items"]["properties"]["alignment_ref"]
    del ref["const"]
    ref["enum"] = [OTHER, ALIGNMENT]
    assert requested_site_projections(form_schema(x=fields))[REFERENCE]["selection"]["alignment_refs"] == [OTHER, ALIGNMENT]
    ref["enum"] = ["source_" + "a" * 24]
    assert_error("alignment_site_selection_reference_required", lambda: requested_site_projections(form_schema(x=fields)))


@pytest.mark.parametrize("change", ["positions_null", "policy_enum_conflict", "window_bound_conflict", "implicit_kind_filter"])
def test_incompatible_policy_and_selector_constraints_fail_before_execution(change):
    fields = request(policy="matching_alignment_position_set")
    props = fields["items"]["properties"]
    if change == "positions_null":
        props["selection"]["properties"]["positions"]["const"] = None
    elif change == "policy_enum_conflict":
        props["selection_policy"]["enum"] = ["all_own_completed_results"]
    elif change == "window_bound_conflict":
        fields = request(policy="matching_alignment_window")
        fields["items"]["properties"]["selection"]["properties"]["start"]["minimum"] = 5
    else:
        fields = request()
        fields["items"]["properties"]["selection"]["properties"]["kind"]["enum"] = ["reference_positions"]
    with pytest.raises(ReportBoundaryError):
        requested_site_projections(form_schema(x=fields))


@pytest.mark.parametrize("bad_positions", [[3, 3], [True], [-1], [], [3.0]])
def test_position_set_rejects_duplicates_booleans_negative_empty_and_float(bad_positions):
    fields = request(policy="matching_alignment_position_set", positions=bad_positions)
    with pytest.raises(ReportBoundaryError):
        requested_site_projections(form_schema(x=fields))


def test_position_set_is_exact_and_returns_original_order_and_duplicates():
    fields = request(policy="matching_alignment_position_set")
    sheet, scores = reference_fixture()
    result = project_reference_site_return(sheet, scores, fields)
    assert result["selection"]["positions"] == [3, 4, 5, 6, 7, 8, 0, 5]
    assert [row["reference_position"] for row in result["rows"]] == [3, 4, 5, 6, 7, 8, 0, 5]
    wrong = request(policy="matching_alignment_position_set", positions=[3, 4])
    assert_error("alignment_site_selection_mismatch", lambda: project_reference_site_return(sheet, scores, wrong))


def test_window_selection_compares_original_request_including_limit():
    fields = request(BLAST, "matching_alignment_window")
    sheet, scores = blast_fixture()
    assert project_blast_column_return(sheet, scores, fields)["selection"]["column_limit"] == 4
    sheet["requested_window"]["column_limit"] = 3
    assert_error("alignment_site_selection_mismatch", lambda: project_blast_column_return(sheet, scores, fields))


def test_reference_window_retains_its_original_kind_and_range():
    sheet, scores = reference_fixture()
    sheet["selection"] = {"kind": "reference_window", "start": 3, "end": 9}
    fields = request(policy="matching_alignment_window", groups=MINIMUM)
    assert project_reference_site_return(sheet, scores, fields)["selection"] == {
        "kind": "reference_window", "positions": None, "start": 3, "end": 9}


@pytest.mark.parametrize("change", ["selector", "projection", "bounds"])
def test_same_source_aliases_must_have_identical_selection_and_projection(change):
    first = request(groups=(*MINIMUM, "rows"), rows=("request_ordinal", "reference_position", "reference_unit", "relationship"))
    second = deepcopy(first)
    assert list(requested_site_projections(form_schema(first=first, second=second))) == [REFERENCE]
    if change == "selector":
        second["items"]["properties"]["selection_policy"]["const"] = "matching_alignment"
        second["items"]["properties"]["alignment_ref"]["const"] = ALIGNMENT
    elif change == "projection":
        subset(second["items"], MINIMUM)
    else:
        second["maxItems"] = 1
    assert_error("alignment_site_projection_conflict", lambda: requested_site_projections(form_schema(first=first, second=second)))


@pytest.mark.parametrize("field", MINIMUM)
def test_minimum_group_identity_and_status_cannot_be_omitted(field):
    fields = request(groups=[name for name in MINIMUM if name != field])
    with pytest.raises(ReportBoundaryError):
        requested_site_projections(form_schema(x=fields))


@pytest.mark.parametrize("change", ["row_identity", "row_unit", "ratio_denominator", "paired_unit",
    "unknown_field", "wrong_scalar_type", "lost_null", "native_namespace", "coordinate_description", "segments"])
def test_projection_rejects_missing_meaning_or_changed_types(change):
    fields = request()
    props = fields["items"]["properties"]
    row = props["rows"]["items"]
    if change == "row_identity":
        subset(row, [key for key in row["properties"] if key != "request_ordinal"])
    elif change == "row_unit":
        subset(row, [key for key in row["properties"] if key != "query_unit"])
    elif change == "ratio_denominator":
        subset(props["components"]["properties"]["selected_paired_identity"], ("value", "numerator", "unit"))
    elif change == "paired_unit":
        subset(fields["items"], [key for key in props if key != "query_unit"])
    elif change == "unknown_field":
        props["raw_native"] = {"type": "string", "format": "protein_sequence"}
        fields["items"]["required"].append("raw_native")
    elif change == "wrong_scalar_type":
        row["properties"]["reference_position"]["type"] = "number"
    elif change == "lost_null":
        row["properties"]["query_position"]["type"] = "integer"
    elif change == "native_namespace":
        props["alignment_ref"]["x-reference-namespace"] = "source"
    elif change == "coordinate_description":
        row["properties"]["reference_position"]["description"] = "One based coordinate."
    else:
        subset(row["properties"]["query_original_intervals"]["items"], ("subject_ref", "start", "end", "strand"))
    with pytest.raises(ReportBoundaryError):
        requested_site_projections(form_schema(x=fields))


def test_projection_copies_requested_numbers_with_explicit_denominators_and_no_whole_scores():
    sheet, scores = reference_fixture()
    fields = request(groups=(*MINIMUM, "components"), components=("paired_positions", "selected_paired_identity"))
    original = deepcopy((sheet, scores, fields))
    result = project_reference_site_return(sheet, scores, fields)
    assert set(result) == {*MINIMUM, "components"}
    assert result["components"] == {"paired_positions": 5,
        "selected_paired_identity": {"value": 0.8, "numerator": 4, "denominator": 5, "unit": "fraction"}}
    assert (sheet, scores, fields) == original
    assert "native_score" not in json.dumps(result)
    assert "operation_" not in json.dumps(result)


def test_ratios_are_copied_without_recalculation_or_rounding():
    sheet, scores = reference_fixture()
    scores["ratios"]["selected_paired_identity"] = {"value": 0.8123456789012345, "numerator": 4, "denominator": 5}
    fields = request(groups=(*MINIMUM, "components"), components=("selected_paired_identity",))
    result = project_reference_site_return(sheet, scores, fields)
    assert result["components"]["selected_paired_identity"]["value"] == 0.8123456789012345


def test_all_reference_row_fields_insertions_and_split_original_segments_cross_real_boundary():
    sheet, scores = reference_fixture()
    sheet["sites"][0]["native_operation"] = "="
    segments = [{"subject_ref": QUERY, "start": 3, "end": 4, "unit": "nt", "strand": "+"},
        {"subject_ref": QUERY, "start": 8, "end": 10, "unit": "nt", "strand": "+"}]
    sheet["sites"][0].update(query_original_intervals=segments, query_mapping_status="available", query_mapping_reason=None)
    sheet["insertions"][0].update(query_sequence="F*", query_quality_characters="!I", query_interval=[5, 7])
    fields = request()
    result = project_reference_site_return(sheet, scores, fields)
    assert result["rows"][0]["query_original_intervals"] == segments
    assert result["insertions"][0]["query_sequence"] == ["F", "*"]
    assert result["insertions"][0]["query_quality_characters"] == ["!", "I"]
    schema = form_schema(selected=fields)
    form = form_with_facts({}, schema, {REFERENCE: [result]})
    assert validate_form(form, schema, lambda *_: True) == form
    validate_frozen_site_return(form, schema, {REFERENCE: [result]})


def test_partial_unknown_components_remain_null_and_valid_native_cells_survive():
    sheet, scores = blast_fixture()
    sheet["status"] = "partial"
    sheet["issues"] = [{"code": "site_native_geometry_conflict"}, {"code": "provider_specific_diagnostic"}]
    scores["summary"]["query_paired_units"] = None
    scores["ratios"]["query_paired_coverage"] = {"numerator": None, "denominator": 12, "value": None}
    result = project_blast_column_return(sheet, scores, request(BLAST))
    assert result["components"]["query_paired_units"] is None
    assert result["components"]["query_paired_coverage"] == {
        "value": None, "numerator": None, "denominator": 12, "unit": "fraction"}
    assert result["components"]["identical_pairs"] == 2
    assert result["issue_codes"] == ["site_native_geometry_conflict", "site_component_unavailable"]


def test_known_no_alignment_preserves_zero_coverage_and_null_identity():
    sheet, scores = reference_fixture()
    sheet["status"] = "no_alignment"
    sheet["native_input"].update(aligned=False, aligned_query="", aligned_reference="", coordinates=[],
        query_interval=None, reference_interval=None, paired_positions=0, identical_positions=0,
        identity_fraction=None, query_coverage=0.0, reference_coverage=0.0)
    for row in sheet["sites"]:
        row.update(relationship="outside_alignment", query_position=None, query_interval=None,
            query_symbol=None, reference_symbol=None, alignment_column=None, query_original_intervals=[],
            query_mapping_status="not_applicable", query_mapping_reason=None)
    sheet["insertions"] = []
    sheet["measured_counts"] = {key: 0 for key in sheet["measured_counts"]}
    sheet["measured_counts"].update(requested_position_count=8, unique_requested_position_count=7,
        duplicate_requested_position_count=1, outside_alignment_positions=7)
    scores["status"] = "no_alignment"
    scores["summary"] = deepcopy(sheet["measured_counts"])
    scores["observed_subset_counts"] = deepcopy(sheet["measured_counts"])
    for name, ratio in scores["ratios"].items():
        ratio.update(numerator=0, value=None if name.endswith("identity") else 0.0)
        if name.endswith("identity"):
            ratio["denominator"] = 0
        scores["summary"][name] = ratio["value"]
    fields = request(groups=(*MINIMUM, "components"), components=("paired_positions",
        "selected_paired_identity", "selected_query_paired_coverage"))
    result = project_reference_site_return(sheet, scores, fields)
    assert result["data_status"] == "no_alignment"
    assert result["components"]["paired_positions"] == 0
    assert result["components"]["selected_paired_identity"] == {
        "value": None, "numerator": 0, "denominator": 0, "unit": "fraction"}
    assert result["components"]["selected_query_paired_coverage"]["value"] == 0.0


@pytest.mark.parametrize("source", [REFERENCE, BLAST])
def test_action_projection_uses_exact_selection_binding_and_actual_operational_status(source):
    record = action_fixture(source)
    record["operation_status"] = "partial"
    fields = request(source)
    original = deepcopy(record)
    result = project_site_action_return(record, fields)
    assert result["data_status"] == record["grading"]["sheet"]["status"]
    assert result["operation_status"] == "partial"
    assert record == original
    assert not {"decision_index", "operation_ref", "grading_artifact_ref", "native_artifact_ref", "grading"} & set(result)


@pytest.mark.parametrize("source", [REFERENCE, BLAST])
@pytest.mark.parametrize("availability,code", [("legacy_result_ungraded", "site_legacy_result_ungraded"),
    ("grading_unavailable", "site_grading_unavailable")])
def test_legacy_and_failed_grading_return_unavailable_groups_not_successful_empty_rows(source, availability, code):
    record = action_fixture(source)
    record.update(availability=availability, grading=None, grading_artifact_ref=None)
    result = project_site_action_return(record, request(source))
    assert result["data_status"] == "unavailable"
    assert result["rows"] is None and result["components"] is None
    assert result["query_unit"] is None and result["query_ref"] is None
    assert result["operation_status"] == "completed"
    assert result["issue_codes"] == [code]
    assert result["selection"]["positions" if source == REFERENCE else "column_offset"] == (
        [3, 4, 5, 6, 7, 8, 0, 5] if source == REFERENCE else 2)


def test_failed_grading_preserves_allowed_code_and_maps_internal_only_code():
    record = action_fixture()
    record.update(availability="grading_unavailable", feedback_code="site_native_geometry_conflict",
        grading={"sheet": None, "scores": None, "failure": {"code": "site_native_geometry_conflict"}})
    result = project_site_action_return(record, request())
    assert result["issue_codes"] == ["site_grading_unavailable", "site_native_geometry_conflict"]
    record["feedback_code"] = "provider_specific_error"
    assert project_site_action_return(record, request())["issue_codes"] == ["site_grading_unavailable",
        "site_native_geometry_conflict", "site_component_unavailable"]


def test_specific_saved_failure_code_survives_generic_operational_feedback():
    record = action_fixture(BLAST)
    record.update(availability="grading_unavailable", feedback_code="tool_grading_input_rejected",
        grading={"sheet": None, "scores": None, "failure": {"code": "site_native_geometry_conflict",
            "category": "grading_input", "detail": "Internal diagnostic remains in its artifact."}})
    result = project_site_action_return(record, request(BLAST))
    assert result["issue_codes"] == ["site_grading_unavailable", "site_native_geometry_conflict", "site_component_unavailable"]
    assert "Internal diagnostic" not in json.dumps(result)


@pytest.mark.parametrize("change", ["binding_alignment", "source", "artifact", "locator", "arguments", "tool", "status", "boolean_index"])
def test_action_binding_or_selection_conflicts_are_never_repaired(change):
    record = action_fixture(BLAST)
    if change == "binding_alignment":
        record["binding"]["alignment_ref"] = OTHER
    elif change == "source":
        record["binding"]["native_source_ref"] = "source_" + "9" * 24
    elif change == "artifact":
        record["binding"]["native_artifact_ref"] = "artifact_" + "9" * 24
    elif change == "locator":
        record["binding"]["native_locator"] = {"report_ordinal": 0, "hit_ordinal": 2, "hsp_ordinal": 4}
    elif change == "arguments":
        record["arguments"]["column_limit"] = 3
    elif change == "tool":
        record["tool_name"] = "sequence.sites"
    elif change == "status":
        record["operation_status"] = "failed"
    else:
        record["decision_index"] = True
    with pytest.raises(ReportBoundaryError):
        project_site_action_return(record, request(BLAST))


def test_same_position_set_cannot_replace_actual_request_order_or_duplicates_in_action():
    record = action_fixture()
    record["arguments"]["positions"] = [0, 3, 4, 5, 6, 7, 8]
    assert_error("alignment_site_action_selection_conflict", lambda: project_site_action_return(record, request()))


def test_missing_traceback_and_real_empty_terminal_page_remain_distinct():
    sheet, scores = blast_fixture()
    sheet.update(status="unavailable", realized_window=None, total_columns=None, next_column_offset=None, columns=[])
    scores["summary"] = {key: None for key in scores["summary"]}
    scores["ratios"] = {key: {"value": None, "numerator": None,
        "denominator": 12 if key == "query_paired_coverage" else 18 if key == "reference_paired_coverage" else None}
        for key in scores["ratios"]}
    missing = project_blast_column_return(sheet, scores, request(BLAST))
    assert missing["rows"] is None
    assert missing["selection"] == {"column_offset": 2, "column_limit": 4,
        "column_end": None, "total_columns": None, "next_column_offset": None}
    assert missing["components"]["window_alignment_columns"] is None
    assert missing["components"]["query_paired_coverage"]["denominator"] == 12
    assert missing["components"]["reference_paired_coverage"]["denominator"] == 18
    sheet.update(status="complete", requested_window={"column_offset": 8, "column_limit": 4},
        realized_window={"column_offset": 8, "column_end": 8}, total_columns=8, next_column_offset=None)
    scores["summary"] = {key: None if key in scores["ratios"] else 0 for key in scores["summary"]}
    scores["ratios"] = {key: {"value": 0.0 if key.endswith("coverage") else None,
        "numerator": 0, "denominator": 12 if key == "query_paired_coverage" else
            18 if key == "reference_paired_coverage" else 0} for key in scores["ratios"]}
    empty = project_blast_column_return(sheet, scores, request(BLAST))
    assert empty["rows"] == []
    assert empty["components"]["window_alignment_columns"] == 0
    assert empty["components"]["paired_identity"]["value"] is None
    assert empty["selection"]["column_end"] == 8


@pytest.mark.parametrize("program,query_unit,reference_unit", [("blastn", "nt", "nt"),
    ("blastp", "aa", "aa"), ("blastx", "nt", "aa"), ("tblastn", "aa", "nt"), ("tblastx", "nt", "nt")])
def test_native_blast_group_units_survive_unknown_declared_material(program, query_unit, reference_unit):
    sheet, scores = blast_fixture()
    sheet["program"] = program
    for role in ("query", "reference"):
        sheet["operands"][role]["unit"] = "symbol"
        sheet["operands"][role]["molecule"] = "unknown"
    for row in sheet["columns"]:
        row.update(query_unit=query_unit, reference_unit=reference_unit)
    result = project_blast_column_return(sheet, scores, request(BLAST))
    assert (result["query_unit"], result["reference_unit"]) == (query_unit, reference_unit)


def test_explicit_native_unit_conflict_and_boolean_direction_are_rejected():
    sheet, scores = blast_fixture()
    sheet["operands"]["query"]["unit"] = "aa"
    assert_error("alignment_site_saved_unit_conflict", lambda: project_blast_column_return(sheet, scores, request(BLAST)))
    sheet["operands"]["query"]["unit"] = "nt"
    sheet["columns"][0]["query_direction"] = True
    with pytest.raises(ReportBoundaryError):
        project_blast_column_return(sheet, scores, request(BLAST))


@pytest.mark.parametrize("change", ["empty_identity", "operation", "strand", "integer_float", "symbol_prose"])
def test_malformed_requested_values_cannot_cross_as_closed_facts(change):
    sheet, scores = reference_fixture()
    if change == "empty_identity":
        sheet["operands"]["query"]["subject_ref"] = ""
    elif change == "operation":
        sheet["sites"][0]["native_operation"] = "I"
    elif change == "strand":
        sheet["sites"][0]["query_strand"] = "unknown"
    elif change == "integer_float":
        scores["summary"]["paired_positions"] = 5.0
    else:
        sheet["sites"][0]["query_symbol"] = "a residue"
    with pytest.raises(ReportBoundaryError):
        project_reference_site_return(sheet, scores, request())


@pytest.mark.parametrize("field,value", [("native_operation", "I"), ("query_strand", "unknown")])
def test_finite_native_symbol_and_strand_meanings_also_constrain_schema_literals(field, value):
    fields = request()
    fields["items"]["properties"]["rows"]["items"]["properties"][field]["const"] = value
    assert_error("alignment_site_projection_meaning_conflict", lambda: requested_site_projections(form_schema(x=fields)))


def test_return_values_are_detached_at_every_nested_level():
    sheet, scores = reference_fixture()
    result = project_reference_site_return(sheet, scores, request())
    original = deepcopy((sheet, scores))
    result["rows"][0]["reference_interval"][0] = 99
    result["selection"]["positions"].clear()
    result["components"]["selected_paired_identity"]["numerator"] = 99
    assert (sheet, scores) == original


def test_row_bounds_fail_without_truncation_and_group_minimum_is_checked_after_assembly():
    sheet, scores = reference_fixture()
    fields = request()
    fields["items"]["properties"]["rows"]["maxItems"] = 1
    assert_error("maxItems", lambda: project_reference_site_return(sheet, scores, fields))
    fields = request()
    fields["minItems"] = 2
    group = project_reference_site_return(sheet, scores, fields)
    schema = form_schema(results=fields)
    facts = {REFERENCE: [group, deepcopy(group)]}
    form = form_with_facts({}, schema, facts)
    validate_form(form, schema, lambda *_: True)
    validate_frozen_site_return(form, schema, facts)


@pytest.mark.parametrize("change", ["null_zero", "int_bool", "int_float", "order", "duplicate", "value", "unknown_code"])
def test_frozen_values_reject_changes_in_type_null_order_duplicates_or_codes(change):
    fields = request()
    facts = {REFERENCE: [project_reference_site_return(*reference_fixture(), fields)]}
    schema = form_schema(selected=fields)
    form = form_with_facts({}, schema, facts)
    group = form["selected"][0]
    if change == "null_zero":
        group["rows"][0]["query_quality_score"] = 0
    elif change == "int_bool":
        group["components"]["paired_positions"] = True
    elif change == "int_float":
        group["components"]["paired_positions"] = 5.0
    elif change == "order":
        group["rows"].reverse()
    elif change == "duplicate":
        group["rows"].append(deepcopy(group["rows"][0]))
    elif change == "value":
        group["components"]["selected_paired_identity"]["value"] = 0.9
    else:
        group["issue_codes"].append("invented_scientific_conclusion")
    with pytest.raises(ReportBoundaryError):
        validate_frozen_site_return(form, schema, facts)


def test_frozen_comparison_distinguishes_integer_and_float_ratio_values_even_when_schema_accepts_both():
    fields = request(BLAST)
    facts = {BLAST: [project_blast_column_return(*blast_fixture(), fields)]}
    schema = form_schema(selected=fields)
    form = form_with_facts({}, schema, facts)
    form["selected"][0]["components"]["paired_identity"]["value"] = 1
    validate_form(form, schema, lambda *_: True)
    assert_error("alignment_site_frozen_source_mismatch", lambda: validate_frozen_site_return(form, schema, facts))


def test_frozen_missing_closure_missing_source_and_empty_source_are_distinct():
    schema = form_schema(selected=request(groups=MINIMUM))
    form = {"selected": []}
    assert_error("alignment_site_frozen_facts_unavailable", lambda: validate_frozen_site_return(form, schema, None))
    assert_error("alignment_site_frozen_source_missing", lambda: validate_frozen_site_return(form, schema, {}))
    validate_frozen_site_return(form, schema, {REFERENCE: []})
    assert_error("alignment_site_frozen_source_invalid", lambda: validate_frozen_site_return(form, schema, {REFERENCE: None}))


def test_mixed_sources_and_equal_aliases_use_real_form_with_facts_and_reference_validation():
    ref, blast = request(), request(BLAST)
    schema = form_schema(first=ref, alias=deepcopy(ref), blast=blast,
        interpretation={"type": "string", "enum": ["unresolved"]})
    facts = {REFERENCE: [project_site_action_return(action_fixture(), ref)],
        BLAST: [project_site_action_return(action_fixture(BLAST), blast)]}
    form = form_with_facts({"interpretation": "unresolved"}, schema, facts)
    namespaces = []
    def resolver(value, namespace):
        namespaces.append((value, namespace))
        return value in {ALIGNMENT, QUERY, TARGET, SOURCE}
    validate_form(form, schema, resolver)
    assert (ALIGNMENT, "observation") in namespaces
    assert (SOURCE, "source") in namespaces
    assert (TARGET, None) in namespaces
    validate_frozen_site_return(form, schema, facts)
    assert_error("unknown_reference", lambda: validate_form(form, schema, lambda *_: False))


def test_non_site_schemas_are_noops_and_do_not_require_closure():
    schema = form_schema(ref={"type": "string", "format": "reference", "x-source": "other_fact"})
    assert requested_site_projections(schema) == {}
    validate_frozen_site_return({"ref": QUERY}, schema, None)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), object()])
def test_nonfinite_or_nonjson_saved_input_is_rejected(bad):
    sheet, scores = reference_fixture()
    sheet["native_input"]["bad"] = bad
    with pytest.raises(ReportBoundaryError):
        project_reference_site_return(sheet, scores, request())


def test_cyclic_nonjson_input_returns_structured_failure():
    sheet, scores = reference_fixture()
    sheet["native_input"]["cycle"] = sheet
    assert_error("alignment_site_finite_json_required", lambda: project_reference_site_return(sheet, scores, request()))


def test_pure_projection_and_frozen_validation_do_no_io_model_or_calculation(monkeypatch):
    fields, record = request(), action_fixture()
    schema = form_schema(selected=fields)
    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected acquisition or execution")
    monkeypatch.setattr(builtins, "open", blocked)
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(subprocess, "Popen", blocked)
    group = project_site_action_return(record, fields)
    facts = {REFERENCE: [group]}
    form = form_with_facts({}, schema, facts)
    validate_frozen_site_return(form, schema, facts)
    result = project_reference_site_return(record["grading"]["sheet"], record["grading"]["scores"], fields)
    assert result["operation_status"] is None


def test_only_the_six_frozen_public_interfaces_are_exported():
    import gene_annotation_episode.alignment_site_returns as module
    assert set(module.__all__) == {"alignment_site_fact_sources", "requested_site_projections",
        "project_reference_site_return", "project_blast_column_return", "project_site_action_return",
        "validate_frozen_site_return"}
