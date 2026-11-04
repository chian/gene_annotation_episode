"""D4 supplied-sheet associations, native observations and labeled edge cases.

Fixture construction here is independent of the D2 parser. Native bytes are
historical; fixture-only prepared/population identities do not claim a new v2
request or host admission. Populated counts/FPKM/TPM/p-values below are synthetic.
"""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import urllib.request

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.bvbrc_data_molecular import (
    MOLECULAR_SHEET_SCHEMA, SUPPLIED_METADATA_SCHEMA,
    extract_molecular_experiment_rows,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
FROZEN = json.loads((EVIDENCE / "CONTRACT_SHAPES.json").read_text())
EXPECTED = json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())["molecular_expected_sheet"]
FIELDS = ["counts", "fpkm", "tpm", "log2_fc", "p_value", "z_score", "other_value"]
SUPPLIED_FIELDS = ["sample_ids", "biological_replicate_ids", "technical_replicate_ids",
                   "measurement_units", "normalization_method", "pvalue_correction_method", "contrast"]


def _corrected_schema(name):
    """Independent literal application of the additive correction002."""
    definitions = deepcopy(FROZEN["schemas"]["$defs"])
    definitions["CellLocation"]["properties"]["source_level"]["enum"].remove("supplied")
    definitions["SuppliedCellLocation"] = {
        "type": "object", "properties": {
            "cell_key": {"type": "string"},
            "field": {"type": "string", "enum": SUPPLIED_FIELDS},
            "source_level": {"const": "supplied"},
            "source_ref": {"type": "string", "minLength": 1},
            "record_path": {"type": "string", "pattern": r"^(?:/(?:[^~/]|~[01])*)*(?![\s\S])"}},
        "required": ["cell_key", "field", "source_level", "source_ref", "record_path"],
        "additionalProperties": False,
    }
    definitions["MolecularMetadata"]["properties"]["cells"]["items"] = {
        "oneOf": [{"$ref": "#/$defs/CellLocation"}, {"$ref": "#/$defs/SuppliedCellLocation"}]}
    return {"$ref": "#/$defs/" + name, "$defs": definitions}


def _atom(value):
    kind = ("null" if value is None else "boolean" if type(value) is bool else
            "number" if type(value) in (int, float) else "string")
    return {"kind": kind, "string_value": value if kind == "string" else None,
            "number_value": value if kind == "number" else None,
            "boolean_value": value if kind == "boolean" else None,
            "number_lexeme": json.dumps(value) if kind == "number" else None}


def _page(collection, records, *, selected=None, raw=None, receipt=None):
    """Labeled input fixture builder; supports the known scalar/list fixtures."""
    registry = FROZEN["field_registry"][collection]
    fields = list(registry["selectable_fields"] if selected is None else selected)
    raw = json.dumps(records, separators=(",", ":")).encode() if raw is None else raw
    digest = hashlib.sha256(raw).hexdigest()
    rows = []
    for index, record in enumerate(records):
        row_key = digest + "/row/" + str(index)
        path = "/" + str(index)
        cells, numerical = [], []
        for field in fields:
            definition = registry["fields"][field]
            value = record.get(field)
            present = field in record
            cell = {"cell_key": row_key + "/field/" + field, "field": field,
                    "native_path": path + "/" + field,
                    "presence": "absent" if not present else "null" if value is None else "present",
                    "native_shape": "absent" if not present else "null" if value is None else
                                    "array" if type(value) is list else "scalar",
                    "atoms": [] if value is None else [_atom(v) for v in value] if type(value) is list else [_atom(value)],
                    "status": "missing" if value is None else "valid",
                    "field_schema_status": "not_evaluated" if value is None else "match",
                    "issue_codes": []}
            cells.append(cell)
            if definition["numeric_projection"]:
                text = value is not None and definition["numeric_text_grammar"] is not None
                numerical.append({"cell_key": cell["cell_key"], "field": field,
                    "native_path": cell["native_path"], "value": int(value) if text else value,
                    "status": "missing" if value is None else "parsed_numeric_text" if text else "reported",
                    "reason": "native_field_absent" if not present else "native_null" if value is None else None,
                    "quantity_kind": definition["quantity_kind"], "unit_code": definition["unit_code"],
                    "unit_basis": definition["unit_basis"], "unit_cell_keys": [],
                    "denominator_value": None, "denominator_basis": "unknown",
                    "origin": "unavailable" if value is None else "derived_from_native_text" if text else "native_reported",
                    "uncertainty_cell_keys": [], "issue_codes": []})
        rows.append({"row_key": row_key, "row_index": index, "native_path": path,
                     "native_id": record.get(registry["unique_key"]), "status": "valid",
                     "cells": cells, "numerical_cells": numerical, "issues": []})
    url = receipt["url"] if receipt else "https://fixture.invalid/api/" + collection
    total = int(next(v for k, v in receipt["headers"] if k.lower() == "content-range").split("/")[1]) if receipt else len(rows)
    population = hashlib.sha256(("fixture-only-population:" + url).encode()).hexdigest()
    headers = [{"name": k, "value": v} for k, v in receipt["headers"]] if receipt else []
    result = {
        "version": "bvbrc_data_sheet_v1", "collection": collection, "mode": "page",
        "custody": {"native_sha256": digest, "retrieved_at": receipt["retrieved_at"] if receipt else "synthetic",
                    "requested_url": url, "effective_url": url, "media_type": "application/json",
                    "native_profile": "json_array_with_headers_v1", "prepared_sha256": "0" * 64,
                    "field_contract_version": "bvbrc_data_fields_2026_10_24_v1"},
        "transport": {"http_status": 200, "body_complete": True, "headers": headers,
                      "failure_code": None, "automatic_redirects": False, "native_query_time_ms": None},
        "qualification": {"service_matches": True, "request_matches": True, "transport_complete": True,
                          "http_success": True, "format_valid": True, "population_metadata_valid": True,
                          "native_partial_results": None, "requested_fields_valid": True, "status": "complete"},
        "population": {"population_key": population, "compiled_query": None, "echoed_query": None,
                       "echoed_filter_queries": [], "reported_total": total, "native_num_found_exact": None,
                       "exactness": "provider_reported", "native_location": "header:Content-Range"},
        "selected_fields": fields,
        "page": {"mode": "page", "requested_offset": 0, "requested_limit": max(1, len(rows)),
                 "response_start": 0, "native_content_range": "items 0-" + str(len(rows)) + "/" + str(total),
                 "returned_row_count": len(rows), "valid_row_count": len(rows), "invalid_row_count": 0,
                 "reported_total": total, "count_exactness": "provider_reported", "response_complete": True,
                 "population_coverage": "subset" if total > len(rows) else "unknown",
                 "next_offset": len(rows) if total > len(rows) else None,
                 "next_offset_basis": "reported_more" if total > len(rows) else None},
        "count": {"population_key": population, "reported_value": total, "exactness": "provider_reported",
                  "availability": "available", "reason": None, "native_location": "header:Content-Range"},
        "rows": rows, "facets": [], "issues": [],
    }
    Draft202012Validator({**FROZEN["schemas"], "$ref": "#/$defs/DataSheet"}).validate(result)
    return result


def native_inputs():
    pages = []
    for name, collection in (("expression_page", "bioset_result"), ("bioset_page", "bioset"),
                             ("experiment_page", "experiment")):
        raw = (EVIDENCE / (name + ".body")).read_bytes()
        receipt = json.loads((EVIDENCE / (name + ".meta.json")).read_text())
        assert hashlib.sha256(raw).hexdigest() == receipt["sha256"]
        fields = re.search(r"select\(([^)]+)\)", receipt["url"]).group(1).split(",")
        pages.append(_page(collection, json.loads(raw), selected=fields, raw=raw, receipt=receipt))
    return {"result_pages": [pages[0]], "bioset_pages": [pages[1]], "experiment_pages": [pages[2]],
            "feature_pages": [], "result_ids": EXPECTED["selected_result_ids"][:], "supplied_metadata": []}


def synthetic_inputs(*, results=None, biosets=None, experiments=None, features=None, supplied=None):
    return {"result_pages": [_page("bioset_result", results if results is not None else [
                {"id": "r", "exp_id": "e", "bioset_id": "b", "feature_id": "f", "log2_fc": -2.5}])],
            "bioset_pages": [_page("bioset", biosets if biosets is not None else [{"bioset_id": "b", "exp_id": "e"}])],
            "experiment_pages": [_page("experiment", experiments if experiments is not None else [{"exp_id": "e"}])],
            "feature_pages": [_page("genome_feature", features if features is not None else [{"feature_id": "f"}])],
            "result_ids": ["r"], "supplied_metadata": [] if supplied is None else supplied}


def _extract(inputs):
    before = deepcopy(inputs)
    result = extract_molecular_experiment_rows(**inputs)
    assert inputs == before
    Draft202012Validator(_corrected_schema("MolecularSheet")).validate(result)
    # An independent plain JSON round trip also excludes accidental live objects.
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    return result


def measurement(row, field):
    return next(cell for cell in row["measurements"] if cell["field"] == field)


def metadata(row, field, level):
    return next(cell for cell in row["metadata"] if cell["field"] == field and cell["source_level"] == level)


def supplied_record(**overrides):
    return {"result_id": "r", "bioset_id": "b", "provenance": {"source_ref": "source/a~b", "record_path": "/design/0"},
            "sample_ids": None, "biological_replicate_ids": None, "technical_replicate_ids": None,
            "measurement_units": [], "normalization_method": None, "pvalue_correction_method": None,
            "contrast": None, **overrides}


def test_exported_shapes_match_frozen_contract_with_exact_additive_locations():
    def expanded(value, definitions):
        if type(value) is dict:
            if "$ref" in value:
                return expanded(definitions[value["$ref"].rsplit("/", 1)[1]], definitions)
            return {key: expanded(child, definitions) for key, child in value.items()}
        if type(value) is list:
            return [expanded(child, definitions) for child in value]
        return value

    assert MOLECULAR_SHEET_SCHEMA["$defs"]["MolecularSheet"] == FROZEN["schemas"]["$defs"]["MolecularSheet"]
    expected = _corrected_schema("MolecularSheet")["$defs"]
    for name in ("SuppliedMetadata", "SuppliedCellLocation", "MolecularMetadata"):
        actual = MOLECULAR_SHEET_SCHEMA["$defs"]
        assert expanded(actual[name], actual) == expanded(expected[name], expected)


def test_retained_native_values_and_exact_independent_expected_relationships():
    inputs = native_inputs()
    actual = _extract(inputs)
    for key in ("version", "selected_result_ids", "input_native_sha256s", "supplied_metadata",
                "missing_result_ids", "requirements", "issues"):
        assert actual[key] == EXPECTED[key]
    assert len(actual["rows"]) == 2
    for row, expected in zip(actual["rows"], EXPECTED["rows"]):
        for key in expected.keys() - {"metadata"}:
            assert row[key] == expected[key]
        for field in expected["metadata"]:
            assert metadata(row, field["field"], field["source_level"]) == field
        assert [cell["field"] for cell in row["measurements"]] == FIELDS
        for field in ("counts", "fpkm", "tpm", "p_value", "other_value"):
            assert measurement(row, field)["value"] is None
            assert measurement(row, field)["reason"] == "native_field_absent"
    assert [measurement(row, "log2_fc")["value"] for row in actual["rows"]] == [-0.132, -0.129]
    assert [measurement(row, "z_score")["value"] for row in actual["rows"]] == [-0.544, -0.556]
    assert actual["rows"][0]["experiment"]["rows"][0]["row_key"].endswith("/row/1")
    assert actual["rows"][1]["experiment"]["rows"][0]["row_key"].endswith("/row/0")


def test_empty_native_duration_and_aggregate_arrays_are_retained_without_zipping():
    inputs = native_inputs()
    actual = _extract(inputs)
    row = actual["rows"][1]
    duration = metadata(row, "treatment_duration", "bioset")
    assert duration["status"] == "reported"
    source = inputs["bioset_pages"][0]["rows"][1]
    cell = next(cell for cell in source["cells"] if cell["cell_key"] == duration["cells"][0]["cell_key"])
    assert cell["atoms"][0]["string_value"] == ""
    treatment = metadata(actual["rows"][0], "treatment_name", "experiment")
    assert len(treatment["cells"]) == 1
    assert treatment["cells"][0]["row_key"].endswith("/row/1")
    assert metadata(row, "samples", "experiment")["reason"] == "native_field_absent"
    assert metadata(row, "sample_ids", "supplied")["status"] == "missing"


def test_synthetic_fractional_counts_zero_and_pvalue_are_separate_native_fields():
    inputs = synthetic_inputs(results=[{"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f",
        "counts": 2.75, "fpkm": 0, "tpm": 5.25, "log2_fc": -3, "p_value": 0,
        "z_score": -0.25, "other_value": -19.5}])
    row = _extract(inputs)["rows"][0]
    assert [cell["value"] for cell in row["measurements"]] == [2.75, 0, 5.25, -3, 0, -0.25, -19.5]
    assert all(cell["origin"] == "native_reported" for cell in row["measurements"])
    assert all(cell["unit_code"] is None and cell["unit_basis"] == "unknown" for cell in row["measurements"])
    assert row["relationship_status"] == "matched"


def test_unselected_null_absent_and_invalid_measurements_stay_distinct():
    page = _page("bioset_result", [{"id": "r", "counts": None, "log2_fc": -1}],
                 selected=["id", "counts", "p_value", "log2_fc"])
    inputs = synthetic_inputs()
    inputs["result_pages"] = [page]
    row = _extract(inputs)["rows"][0]
    assert measurement(row, "counts")["reason"] == "native_null"
    assert measurement(row, "p_value")["reason"] == "native_field_absent"
    assert measurement(row, "tpm")["reason"] == "not_selected"
    assert measurement(row, "log2_fc")["value"] == -1
    assert row["bioset"]["status"] == "missing_key"


def test_bad_parent_links_do_not_erase_valid_measurements_or_choose_another_experiment():
    inputs = synthetic_inputs(biosets=[{"bioset_id": "b", "exp_id": "other"}],
                              experiments=[{"exp_id": "other"}, {"exp_id": "e"}])
    row = _extract(inputs)["rows"][0]
    assert row["bioset"]["status"] == "conflict"
    assert row["experiment"]["expected_id"] == "e"
    assert row["experiment"]["rows"][0]["row_key"].endswith("/row/1")
    assert row["relationship_status"] == "conflict"
    assert measurement(row, "log2_fc")["value"] == -2.5
    assert any(issue["field"] == "exp_id" for issue in row["issues"])


def test_matching_gene_taxon_entity_and_row_order_do_not_join_different_feature_id():
    inputs = synthetic_inputs(results=[{"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f",
                                         "entity_id": "alias", "entity_name": "same", "taxon_id": 123}],
                              features=[{"feature_id": "different", "patric_id": "alias", "gene": "same", "taxon_id": 123}])
    result = _extract(inputs)
    assert result["rows"][0]["feature"]["status"] == "missing_record"
    assert result["rows"][0]["feature"]["rows"] == []
    assert result["requirements"] == [{"collection": "genome_feature", "field": "feature_id", "values": ["f"],
                                        "sequence_kind": None, "reason": "missing_feature_record"}]


def test_explicit_feature_alias_disagreement_is_retained_as_conflict():
    inputs = synthetic_inputs(results=[{"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f", "patric_id": "left"}],
                              features=[{"feature_id": "f", "patric_id": "right"}])
    row = _extract(inputs)["rows"][0]
    assert row["feature"]["status"] == "conflict"
    assert len(row["feature"]["rows"]) == 1
    assert metadata(row, "patric_id", "result")["status"] == "reported"


@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_result_ids_all_survive_and_conflicting_measurements_are_qualified(conflicting):
    second = -7 if conflicting else -2.5
    inputs = synthetic_inputs(results=[
        {"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f", "log2_fc": -2.5},
        {"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f", "log2_fc": second}])
    result = _extract(inputs)
    assert len(result["rows"]) == 2
    assert [measurement(row, "log2_fc")["value"] for row in result["rows"]] == [-2.5, second]
    assert len({row["row_key"] for row in result["rows"]}) == 2
    assert all(row["relationship_status"] == ("conflict" if conflicting else "matched") for row in result["rows"])


def test_duplicate_parent_ids_retain_all_conflicting_candidates():
    inputs = synthetic_inputs(biosets=[{"bioset_id": "b", "exp_id": "e", "treatment_name": "left"},
                                      {"bioset_id": "b", "exp_id": "e", "treatment_name": "right"}])
    row = _extract(inputs)["rows"][0]
    assert len(row["bioset"]["rows"]) == 2
    assert row["bioset"]["status"] == "conflict"
    assert len(metadata(row, "treatment_name", "bioset")["cells"]) == 2
    assert metadata(row, "treatment_name", "bioset")["status"] == "conflict"


def test_exact_repeated_page_is_retained_without_inventing_a_distinct_source():
    inputs = synthetic_inputs()
    inputs["result_pages"].append(deepcopy(inputs["result_pages"][0]))
    result = _extract(inputs)
    assert len(result["rows"]) == 2
    assert result["rows"][0] == result["rows"][1]
    assert len(result["input_native_sha256s"]) == 4


def test_missing_result_and_parent_acquisitions_are_typed_and_no_result_is_fabricated():
    inputs = synthetic_inputs()
    inputs.update(bioset_pages=[], experiment_pages=[], feature_pages=[], result_ids=["r", "absent"])
    result = _extract(inputs)
    assert len(result["rows"]) == 1
    assert result["missing_result_ids"] == ["absent"]
    assert {(r["collection"], tuple(r["values"]), r["reason"]) for r in result["requirements"]} == {
        ("bioset", ("b",), "missing_input_page"), ("experiment", ("e",), "missing_input_page"),
        ("genome_feature", ("f",), "missing_input_page"), ("bioset_result", ("absent",), "requested_row_absent")}
    inputs["result_pages"] = []
    result = _extract(inputs)
    assert result["rows"] == []
    assert result["missing_result_ids"] == ["r", "absent"]
    assert result["requirements"][0]["values"] == ["r", "absent"]


def test_supplied_units_design_and_source_pointer_are_exact_without_a_fake_native_hash():
    supplied = supplied_record(sample_ids=["s/1", "s2"], biological_replicate_ids=["b1", "b2"],
        measurement_units=[{"field": "log2_fc", "unit": "exact arbitrary units"}],
        pvalue_correction_method="BH (supplied)", normalization_method="recorded method",
        contrast={"numerator_condition": "treated", "denominator_condition": "control"})
    result = _extract(synthetic_inputs(supplied=[supplied]))
    row = result["rows"][0]
    unit = measurement(row, "log2_fc")
    assert unit["value"] == -2.5 and unit["unit_code"] is None and unit["unit_basis"] == "supplied"
    assert unit["unit_cell_keys"] == ["supplied/source~1a~0b/design/0/measurement_units/0/unit"]
    cells = metadata(row, "measurement_units", "supplied")["cells"]
    assert {cell["record_path"] for cell in cells} == {
        "/design/0/measurement_units/0/field", "/design/0/measurement_units/0/unit"}
    assert all("native_sha256" not in cell and "collection" not in cell for cell in cells)
    assert result["supplied_metadata"] == [supplied]
    assert [c["record_path"] for c in metadata(row, "sample_ids", "supplied")["cells"]] == [
        "/design/0/sample_ids/0", "/design/0/sample_ids/1"]


def test_supplied_null_empty_arrays_and_empty_strings_have_resolvable_distinct_states():
    record = supplied_record(sample_ids=[], biological_replicate_ids=None, normalization_method="")
    row = _extract(synthetic_inputs(supplied=[record]))["rows"][0]
    samples = metadata(row, "sample_ids", "supplied")
    assert samples["status"] == "supplied" and samples["cells"][0]["record_path"] == "/design/0/sample_ids"
    missing = metadata(row, "biological_replicate_ids", "supplied")
    assert missing["status"] == "missing" and missing["reason"] == "native_null" and len(missing["cells"]) == 1
    units = metadata(row, "measurement_units", "supplied")
    assert units["reason"] == "unknown_units" and len(units["cells"]) == 1
    assert metadata(row, "normalization_method", "supplied")["status"] == "supplied"
    assert measurement(row, "log2_fc")["unit_cell_keys"] == []


def test_conflicting_supplied_units_and_design_keep_every_source_without_precedence():
    left = supplied_record(measurement_units=[{"field": "log2_fc", "unit": "left"}], sample_ids=["left"])
    right = supplied_record(provenance={"source_ref": "other", "record_path": ""},
                            measurement_units=[{"field": "log2_fc", "unit": "right"}], sample_ids=["right"])
    row = _extract(synthetic_inputs(supplied=[left, right]))["rows"][0]
    assert row["relationship_status"] == "conflict"
    assert measurement(row, "log2_fc")["value"] == -2.5
    assert len(measurement(row, "log2_fc")["unit_cell_keys"]) == 2
    assert measurement(row, "log2_fc")["issue_codes"] == ["bvbrc_join_conflict"]
    assert metadata(row, "sample_ids", "supplied")["status"] == "conflict"
    assert len(metadata(row, "sample_ids", "supplied")["cells"]) == 2


def test_supplied_metadata_requires_both_result_and_bioset_link_for_units():
    bad = supplied_record(bioset_id="wrong", measurement_units=[{"field": "log2_fc", "unit": "bad link"}])
    row = _extract(synthetic_inputs(supplied=[bad]))["rows"][0]
    assert row["relationship_status"] == "conflict"
    assert metadata(row, "measurement_units", "supplied")["status"] == "conflict"
    assert measurement(row, "log2_fc")["unit_cell_keys"] == []
    shared = supplied_record(result_id=None, measurement_units=[{"field": "log2_fc", "unit": "bioset scoped"}])
    row = _extract(synthetic_inputs(supplied=[shared]))["rows"][0]
    assert measurement(row, "log2_fc")["unit_basis"] == "supplied"
    unrelated = supplied_record(result_id="different", measurement_units=[{"field": "log2_fc", "unit": "not this result"}])
    row = _extract(synthetic_inputs(supplied=[unrelated]))["rows"][0]
    assert measurement(row, "log2_fc")["unit_basis"] == "unknown"


def test_conflicting_assertions_for_one_source_path_are_invalid_input():
    left, right = supplied_record(sample_ids=["a"]), supplied_record(sample_ids=["b"])
    with pytest.raises(ValueError, match="conflicting_source_path"):
        _extract(synthetic_inputs(supplied=[left, right]))


@pytest.mark.parametrize("path", ["not/a/pointer", "/bad~2escape", "/bad~"])
def test_invalid_supplied_pointer_is_not_repaired(path):
    with pytest.raises(ValueError, match="metadata_json_pointer"):
        _extract(synthetic_inputs(supplied=[supplied_record(provenance={"source_ref": "s", "record_path": path})]))


def test_valid_escaped_source_pointers_are_not_decoded_or_renormalized():
    record = supplied_record(provenance={"source_ref": "a/b~c", "record_path": "/a~1b/~0c"}, sample_ids=["s"])
    row = _extract(synthetic_inputs(supplied=[record]))["rows"][0]
    cell = metadata(row, "sample_ids", "supplied")["cells"][0]
    assert cell["record_path"] == "/a~1b/~0c/sample_ids/0"
    assert cell["cell_key"] == "supplied/a~1b~0c/a~1b/~0c/sample_ids/0"


@pytest.mark.parametrize("slot,wrong", [("result_pages", "bioset"), ("bioset_pages", "experiment"),
                                        ("experiment_pages", "genome_feature"), ("feature_pages", "bioset_result")])
def test_wrong_collection_is_incompatible_not_zero_results(slot, wrong):
    inputs = synthetic_inputs()
    inputs[slot].append(_page(wrong, []))
    with pytest.raises(ValueError, match="collection"):
        _extract(inputs)


@pytest.mark.parametrize("change", ["version", "mode", "extra", "boolean", "integral_float", "nan",
                                    "infinity", "numeric_reference", "native_identity", "numeric_value", "row_key"])
def test_wrong_shape_types_and_forged_cell_relationships_fail(change):
    inputs = synthetic_inputs()
    page = inputs["result_pages"][0]
    row = page["rows"][0]
    number = next(cell for cell in row["numerical_cells"] if cell["field"] == "log2_fc")
    if change == "version": page["version"] = "wrong"
    elif change == "mode": page["mode"] = "count"
    elif change == "extra": page["unexpected"] = True
    elif change == "boolean": number["value"] = True
    elif change == "integral_float": row["row_index"] = 0.0
    elif change == "nan": number["value"] = float("nan")
    elif change == "infinity": number["value"] = float("inf")
    elif change == "numeric_reference": number["cell_key"] = "different"
    elif change == "native_identity": row["native_id"] = "different"
    elif change == "numeric_value": number["value"] = 9
    else: row["row_key"] = "different"
    with pytest.raises(ValueError):
        extract_molecular_experiment_rows(**inputs)


def test_native_invalid_cell_keeps_valid_measurements_and_invalid_number_reason():
    inputs = synthetic_inputs()
    page = inputs["result_pages"][0]
    row = page["rows"][0]
    cell = next(cell for cell in row["cells"] if cell["field"] == "counts")
    cell.update(presence="present", native_shape="scalar", atoms=[_atom(True)], status="invalid",
                field_schema_status="mismatch", issue_codes=["bvbrc_invalid_native_field"])
    number = next(cell for cell in row["numerical_cells"] if cell["field"] == "counts")
    number.update(status="invalid", reason="native_value_invalid", issue_codes=["bvbrc_invalid_native_field"])
    row["status"] = "partial"
    page["page"].update(valid_row_count=0, invalid_row_count=1)
    actual = _extract(inputs)["rows"][0]
    assert measurement(actual, "counts")["reason"] == "native_value_invalid"
    assert measurement(actual, "log2_fc")["value"] == -2.5


def test_no_io_no_mutation_and_detached_saved_sheet_reextraction(monkeypatch):
    inputs = native_inputs()
    expected = _extract(inputs)
    original = deepcopy(inputs)

    def forbidden(*args, **kwargs):
        raise AssertionError("pure extractor attempted I/O")

    with monkeypatch.context() as patch:
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(urllib.request, "urlopen", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        actual = extract_molecular_experiment_rows(**json.loads(json.dumps(inputs)))
    assert actual == expected and inputs == original
    actual["rows"][0]["measurements"][0]["value"] = 111
    actual["selected_result_ids"].append("detached")
    assert inputs == original
    assert _extract(inputs) == expected


@pytest.mark.parametrize("result_ids", [[], ["r", "r"], [1], "r", ("r",)])
def test_explicit_nonempty_unique_result_selection_is_required(result_ids):
    inputs = synthetic_inputs()
    inputs["result_ids"] = result_ids
    with pytest.raises(ValueError, match="result_ids"):
        extract_molecular_experiment_rows(**inputs)


def test_partial_supplied_page_qualifications_survive_with_valid_values():
    inputs = synthetic_inputs()
    page = inputs["result_pages"][0]
    issue = {"code": "bvbrc_native_partial_results", "phase": "population",
             "row_index": None, "field": None, "native_path": "/responseHeader/partialResults", "http_status": 200}
    page["qualification"].update(status="partial", native_partial_results=True)
    page["page"].update(response_complete=False, population_coverage="unknown")
    page["issues"].append(issue)
    result = _extract(inputs)
    assert result["issues"] == [issue]
    assert measurement(result["rows"][0], "log2_fc")["value"] == -2.5


@pytest.mark.parametrize("field", ["service_matches", "request_matches"])
def test_known_incompatible_page_qualification_is_rejected(field):
    inputs = synthetic_inputs()
    inputs["result_pages"][0]["qualification"][field] = False
    with pytest.raises(ValueError, match="known_source_mismatch"):
        _extract(inputs)


def test_unrepresentable_number_token_never_becomes_zero():
    inputs = synthetic_inputs()
    page = inputs["result_pages"][0]
    row = page["rows"][0]
    raw = next(cell for cell in row["cells"] if cell["field"] == "p_value")
    raw.update(presence="present", native_shape="scalar", status="unrepresentable", field_schema_status="match",
               atoms=[{"kind": "number", "string_value": None, "number_value": None,
                       "boolean_value": None, "number_lexeme": "1e-9999"}],
               issue_codes=["bvbrc_unrepresentable_numeric_value"])
    number = next(cell for cell in row["numerical_cells"] if cell["field"] == "p_value")
    number.update(status="invalid", reason="unrepresentable_numeric_value",
                  issue_codes=["bvbrc_unrepresentable_numeric_value"])
    row["status"] = "partial"
    page["page"].update(valid_row_count=0, invalid_row_count=1)
    result = _extract(inputs)
    assert measurement(result["rows"][0], "p_value")["value"] is None
    assert measurement(result["rows"][0], "p_value")["reason"] == "unrepresentable_numeric_value"
    assert measurement(result["rows"][0], "log2_fc")["value"] == -2.5
    raw["atoms"][0]["number_value"] = 0.0
    with pytest.raises(ValueError, match="number_lexeme_value"):
        _extract(inputs)


def test_empty_native_arrays_are_reported_and_invalid_nested_arrays_are_unavailable():
    inputs = synthetic_inputs(experiments=[{"exp_id": "e", "treatment_name": [], "treatment_duration": []}])
    row = _extract(inputs)["rows"][0]
    assert metadata(row, "treatment_name", "experiment")["status"] == "reported"
    page = inputs["experiment_pages"][0]
    raw = next(cell for cell in page["rows"][0]["cells"] if cell["field"] == "treatment_duration")
    raw.update(status="invalid", field_schema_status="mismatch", issue_codes=["bvbrc_invalid_native_field"])
    page["rows"][0]["status"] = "partial"
    page["page"].update(valid_row_count=0, invalid_row_count=1)
    row = _extract(inputs)["rows"][0]
    assert metadata(row, "treatment_duration", "experiment")["status"] == "missing"
    assert metadata(row, "treatment_duration", "experiment")["reason"] == "native_value_invalid"
    assert metadata(row, "treatment_name", "experiment")["status"] == "reported"


def test_native_result_and_bioset_conditions_are_preserved_at_separate_levels():
    inputs = synthetic_inputs(results=[{"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f",
                                        "treatment_name": "result condition"}],
                              biosets=[{"bioset_id": "b", "exp_id": "e", "treatment_name": "bioset condition"}],
                              experiments=[{"exp_id": "e", "treatment_name": ["aggregate one", "aggregate two"]}])
    row = _extract(inputs)["rows"][0]
    locations = [metadata(row, "treatment_name", level)["cells"][0] for level in ("result", "bioset", "experiment")]
    assert [cell["source_level"] for cell in locations] == ["result", "bioset", "experiment"]
    assert [cell["collection"] for cell in locations] == ["bioset_result", "bioset", "experiment"]
    assert len({cell["cell_key"] for cell in locations}) == 3


def test_missing_bioset_experiment_link_is_partial_without_inferring_it_from_result():
    row = _extract(synthetic_inputs(biosets=[{"bioset_id": "b"}]))["rows"][0]
    assert row["bioset"]["expected_id"] == "b" and len(row["bioset"]["rows"]) == 1
    assert row["bioset"]["status"] == "missing_key"
    assert row["relationship_status"] == "partial"
    assert measurement(row, "log2_fc")["value"] == -2.5


def test_integer_and_float_spellings_of_same_measurement_are_not_conflicting():
    inputs = synthetic_inputs(results=[{"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f", "counts": 1},
                                       {"id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f", "counts": 1.0}])
    result = _extract(inputs)
    assert len(result["rows"]) == 2
    assert all(row["relationship_status"] == "matched" for row in result["rows"])


def test_valid_native_measurement_cannot_be_discarded_by_forged_unavailable_cell():
    inputs = synthetic_inputs()
    number = next(cell for cell in inputs["result_pages"][0]["rows"][0]["numerical_cells"] if cell["field"] == "log2_fc")
    number.update(value=None, status="missing", reason="native_field_absent", origin="unavailable")
    with pytest.raises(ValueError, match="available_native_number_discarded"):
        _extract(inputs)


def test_complementary_supplied_unit_fields_do_not_conflict_or_fill_missing_measurement():
    left = supplied_record(measurement_units=[{"field": "log2_fc", "unit": "fold unit"}])
    right = supplied_record(provenance={"source_ref": "second", "record_path": ""},
                            measurement_units=[{"field": "counts", "unit": "fractional count unit"}])
    row = _extract(synthetic_inputs(supplied=[left, right]))["rows"][0]
    assert metadata(row, "measurement_units", "supplied")["status"] == "supplied"
    assert row["relationship_status"] == "matched"
    assert measurement(row, "counts")["value"] is None
    assert measurement(row, "counts")["reason"] == "native_field_absent"
    assert measurement(row, "counts")["unit_basis"] == "supplied"
