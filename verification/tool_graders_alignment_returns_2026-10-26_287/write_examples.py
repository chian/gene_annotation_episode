"""Retain explicit synthetic inputs, original forms and actual pure projections."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_alignment_site_returns import (REFERENCE, BLAST, MINIMUM, request,
    reference_fixture, blast_fixture, action_fixture, form_schema)
from gene_annotation_episode.alignment_site_returns import (
    project_reference_site_return, project_blast_column_return,
    project_site_action_return, validate_frozen_site_return)
from gene_annotation_episode.communication import form_with_facts, validate_form

examples = []

def retain(name, source, inputs, fields, group):
    schema = form_schema(selected=fields)
    facts = {source: [group]}
    form = form_with_facts({}, schema, facts)
    validate_form(form, schema, lambda *_: True)
    validate_frozen_site_return(form, schema, facts)
    examples.append({"name": name, "evidence_class": "explicit_synthetic_saved_sheet_fixture",
        "inputs": inputs, "original_schema": schema, "frozen_facts": facts, "validated_form": form})

sheet, scores = reference_fixture()
fields = request(groups=(*MINIMUM, "rows", "components"),
    rows=("request_ordinal", "reference_position", "reference_unit", "relationship", "query_position", "query_unit"),
    components=("requested_position_count", "unique_requested_position_count", "duplicate_requested_position_count",
        "paired_positions", "identical_positions", "selected_paired_identity", "selected_alignment_identity"))
retain("duplicate_reference_request", REFERENCE, {"sheet": sheet, "scores": scores}, fields,
    project_reference_site_return(sheet, scores, fields))

sheet, scores = blast_fixture()
fields = request(BLAST, "matching_alignment_window", groups=(*MINIMUM, "rows", "components"),
    rows=("column", "relationship", "query_interval", "query_unit", "reference_interval", "reference_unit",
        "query_direction", "reference_direction"),
    components=("window_alignment_columns", "paired_columns", "paired_identity", "alignment_identity",
        "query_paired_coverage", "reference_paired_coverage"))
retain("reverse_blast_window", BLAST, {"sheet": sheet, "scores": scores}, fields,
    project_blast_column_return(sheet, scores, fields))

sheet, scores = deepcopy(sheet), deepcopy(scores)
sheet.update(status="unavailable", realized_window=None, total_columns=None, next_column_offset=None, columns=[])
sheet["measured_counts"] = {key: None for key in sheet["measured_counts"]}
sheet["availability"] = {"traceback": "unavailable", "geometry": "unavailable"}
sheet["native_input"].pop("qseq")
sheet["native_input"].pop("hseq")
scores["status"] = "unavailable"
scores["summary"] = {key: None for key in scores["summary"]}
scores["ratios"] = {key: {"value": None, "numerator": None,
    "denominator": 12 if key == "query_paired_coverage" else 18 if key == "reference_paired_coverage" else None}
    for key in scores["ratios"]}
scores["component_status"] = {key: "unavailable" for key in scores["component_status"]}
retain("unavailable_traceback", BLAST, {"sheet": sheet, "scores": scores}, fields,
    project_blast_column_return(sheet, scores, fields))

sheet, scores = blast_fixture()
sheet.update(requested_window={"column_offset": 8, "column_limit": 4},
    realized_window={"column_offset": 8, "column_end": 8}, total_columns=8, next_column_offset=None, columns=[])
sheet["measured_counts"] = {key: 0 for key in sheet["measured_counts"]}
scores["summary"] = {key: None if key in scores["ratios"] else 0 for key in scores["summary"]}
scores["ratios"] = {key: {"value": 0.0 if key.endswith("coverage") else None,
    "numerator": 0, "denominator": 12 if key == "query_paired_coverage" else
        18 if key == "reference_paired_coverage" else 0} for key in scores["ratios"]}
scores["summary"].update({key: value["value"] for key, value in scores["ratios"].items()})
scores["component_status"].update(paired_identity="not_applicable", alignment_identity="not_applicable")
fields = request(BLAST, groups=(*MINIMUM, "rows", "components"), rows=("column", "relationship"),
    components=("window_alignment_columns", "paired_columns", "paired_identity", "query_paired_coverage"))
retain("empty_terminal_window", BLAST, {"sheet": sheet, "scores": scores}, fields,
    project_blast_column_return(sheet, scores, fields))

record = action_fixture()
record.update(availability="legacy_result_ungraded", grading=None, grading_artifact_ref=None)
fields = request(groups=(*MINIMUM, "rows", "components", "issue_codes", "operation_status"),
    rows=("request_ordinal", "reference_position", "reference_unit", "relationship"), components=("paired_positions",))
retain("older_ungraded_action", REFERENCE, {"record": record}, fields,
    project_site_action_return(record, fields))

Path(sys.argv[1]).write_text(json.dumps({"version": "alignment_site_return_examples_v1", "examples": examples},
    indent=2, allow_nan=False) + "\n")
print(json.dumps({"examples": [example["name"] for example in examples], "output": sys.argv[1],
    "reference": {"requests": 8, "unique_positions": 7, "paired_positions": 5, "paired_identity": {"value": 0.8,
        "numerator": 4, "denominator": 5}},
    "blast_window": {"columns": 4, "paired_columns": 2, "alignment_identity": {"value": 0.5,
        "numerator": 2, "denominator": 4}},
    "missing_rows": None, "terminal_rows": [], "legacy_issue": "site_legacy_result_ungraded"}))
