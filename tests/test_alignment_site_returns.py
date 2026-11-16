"""Synthetic saved-sheet and actual closed-form boundary tests; no native execution."""
from copy import deepcopy
import builtins
import socket
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.root.library.alignment_site_projection_requests import alignment_site_fact_sources
from gene_annotation_episode.episodic_workflow.root.library.alignment_site_returns import (
    requested_site_projections,
    project_reference_site_return, project_blast_column_return,
    project_site_action_return, validate_frozen_site_return,
)
from gene_annotation_episode.episodic_workflow.root.communication import (
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


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), object()])
def test_nonfinite_or_nonjson_saved_input_is_rejected(bad):
    sheet, scores = reference_fixture()
    sheet["native_input"]["bad"] = bad
    with pytest.raises(ReportBoundaryError):
        project_reference_site_return(sheet, scores, request())


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


