"""Frozen schema compatibility and adversarial JSON/type validation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.bvbrc_data_schema import schema, validate, fact_schemas, json_digest
from gene_annotation_episode.communication import validate_closed_schema, validate_form

EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
FROZEN = json.loads((EVIDENCE / "CONTRACT_SHAPES.json").read_text())
EXAMPLES = json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())


def apply_unavailable_return_correction(source, row):
    """Apply contract 003 to a detached original oracle, never its artifacts."""
    if source == "execution_bvbrc_pages":
        for field in ("returned_row_count", "valid_row_count", "invalid_row_count"):
            row["properties"][field]["type"] = ["integer", "null"]
        row["properties"]["unavailable_reason"] = deepcopy(
            FROZEN["fact_schemas"]["execution_bvbrc_counts"]["items"]["properties"]["reason"])
        row["required"].append("unavailable_reason")
    elif source == "execution_bvbrc_facets":
        row["properties"]["bucket_ref"]["type"] = ["string", "null"]


def expected_fact_schemas():
    result = deepcopy(FROZEN["fact_schemas"])
    for source, definition in result.items():
        apply_unavailable_return_correction(source, definition["items"])
    return result


def unfactor(value, definitions):
    if isinstance(value, dict):
        if "$ref" in value and value["$ref"].split("/")[-1] not in FROZEN["schemas"]["$defs"]:
            return unfactor(definitions[value["$ref"].split("/")[-1]], definitions)
        return {key: unfactor(child, definitions) for key, child in value.items()}
    if isinstance(value, list):
        return [unfactor(child, definitions) for child in value]
    return value


@pytest.mark.parametrize("name", tuple(FROZEN["schemas"]["$defs"]))
def test_all_original_definitions_preserve_contract_except_additive_corrections(name):
    value = schema(name)
    Draft202012Validator.check_schema(value)
    actual = unfactor(value["$defs"][name], value["$defs"])
    expected = deepcopy(FROZEN["schemas"]["$defs"][name])
    if name == "CellLocation":
        expected["properties"]["source_level"]["enum"].remove("supplied")
    if name == "MolecularMetadata":
        # The added locator's full definition is expanded by unfactor.
        expected["properties"]["cells"]["items"] = {"oneOf": [
            {"$ref": "#/$defs/CellLocation"}, schema("SuppliedCellLocation")["$defs"]["SuppliedCellLocation"]]}
    if name == "ReceiverMaterialization":
        for row in expected["properties"]["facts"]["items"]["oneOf"]:
            if "returned_row_count" in row["properties"]:
                apply_unavailable_return_correction("execution_bvbrc_pages", row)
            elif "bucket_ref" in row["properties"]:
                apply_unavailable_return_correction("execution_bvbrc_facets", row)
    assert actual == expected


def test_fact_schemas_preserve_frozen_contract_with_explicit_unavailable_correction():
    assert fact_schemas() == expected_fact_schemas()
    copy = fact_schemas()
    copy.clear()
    assert fact_schemas() == expected_fact_schemas()


def test_embedded_fact_union_matches_all_six_corrected_fact_shapes():
    definition = schema("ReceiverMaterialization")
    rows = definition["$defs"]["ReceiverMaterialization"]["properties"]["facts"]["items"]["oneOf"]
    assert unfactor(rows, definition["$defs"]) == [
        value["items"] for value in expected_fact_schemas().values()]


@pytest.mark.parametrize("source", tuple(FROZEN["fact_schemas"]))
def test_corrected_facts_remain_accepted_by_existing_closed_schema_guard(source):
    form = {"type": "object", "properties": {"facts": fact_schemas()[source]},
            "required": ["facts"], "additionalProperties": False}
    assert validate_closed_schema(form) == form


def synthetic_page_fact(**changes):
    """A synthetic populated page, with changes for explicit unavailable cases."""
    row = {"source_ref": "fixture:result", "collection": "genome_feature",
           "input_source_refs": [], "metadata_source_refs": [], "status": "complete",
           "mode": "page", "requested_offset": 0, "requested_limit": 2,
           "returned_row_count": 2, "valid_row_count": 2, "invalid_row_count": 0,
           "reported_total": 2, "count_exactness": "exact", "response_complete": True,
           "population_coverage": "complete", "next_offset": None,
           "population_ref": "fixture:result#population", "unavailable_reason": None}
    row.update(changes)
    return row


def synthetic_facet_fact(**changes):
    """A synthetic acquired native null-term bucket, distinct from no bucket."""
    row = {"source_ref": "fixture:result", "collection": "genome_feature",
           "input_source_refs": [], "metadata_source_refs": [], "status": "complete",
           "population_ref": "fixture:result#population", "field": "annotation",
           "bucket_ref": "fixture:result#bucket/2", "is_missing_bucket": True,
           "term_ref": "fixture:result#term/2", "count": 0, "denominator": 2,
           "fraction": 0.0, "fraction_unavailable_reason": None,
           "requested_offset": 0, "requested_limit": 10, "requested_min_count": 0,
           "bucket_window_status": "exhausted_window"}
    row.update(changes)
    return row


def synthetic_materialization(source, rows):
    # This tests schema shape only; host custody and projection consistency
    # remain the responsibilities of the D5/D6 consumers.
    return {"version": "bvbrc_received_values_v1", "admission_key": "fixture:admission",
            "form_field": "facts", "fact_source": source, "facts": rows,
            "cells": [], "unavailable": []}


def validate_fact_form(source, rows):
    form_schema = {"type": "object", "properties": {"facts": fact_schemas()[source]},
                   "required": ["facts"], "additionalProperties": False}
    references = {("fixture:result", "execution_result"),
                  ("fixture:result#population", "bvbrc_data_population"),
                  ("fixture:result#bucket/2", "bvbrc_data_bucket"),
                  ("fixture:result#term/2", "bvbrc_data_cell")}
    return validate_form({"facts": rows}, form_schema,
                         reference_resolver=lambda value, namespace: (value, namespace) in references)


def assert_fact_and_materialization(source, rows):
    assert validate_fact_form(source, rows) == {"facts": rows}
    materialized = synthetic_materialization(source, rows)
    assert validate("ReceiverMaterialization", materialized) == materialized


def assert_invalid_fact_and_materialization(source, rows):
    with pytest.raises(ValueError):
        validate_fact_form(source, rows)
    with pytest.raises(ValueError):
        validate("ReceiverMaterialization", synthetic_materialization(source, rows))


@pytest.mark.parametrize("changes", [
    {},
    {"returned_row_count": 0, "valid_row_count": 0, "reported_total": 0},
    {"requested_offset": 7, "returned_row_count": 0, "valid_row_count": 0,
     "population_coverage": "subset"},
    {"status": "partial", "valid_row_count": 1, "invalid_row_count": 1,
     "response_complete": False, "population_coverage": "unknown",
     "unavailable_reason": "native_partial_results"},
], ids=["populated", "successful_zero", "empty_beyond_total", "valid_partial"])
def test_page_facts_preserve_observed_integer_counts(changes):
    row = synthetic_page_fact(**changes)
    assert_fact_and_materialization("execution_bvbrc_pages", [row])
    assert all(type(row[field]) is int for field in (
        "returned_row_count", "valid_row_count", "invalid_row_count"))


@pytest.mark.parametrize("mode", ["page", "count", "facet"])
@pytest.mark.parametrize("reason", ["transport_incomplete", "native_partial_results",
                                   "native_format_unverified", "native_value_invalid",
                                   "incompatible_input"])
def test_failed_no_sheet_page_facts_have_unknown_counts_and_explicit_reason(mode, reason):
    row = synthetic_page_fact(status="unavailable", mode=mode,
        requested_offset=7 if mode == "page" else None,
        requested_limit=2 if mode == "page" else None,
        returned_row_count=None, valid_row_count=None, invalid_row_count=None,
        reported_total=None, count_exactness="unknown", response_complete=False,
        population_coverage="unknown", unavailable_reason=reason)
    assert_fact_and_materialization("execution_bvbrc_pages", [row])
    assert row["returned_row_count"] is None and row["reported_total"] is None
    assert row["unavailable_reason"] == reason


@pytest.mark.parametrize("field", ["returned_row_count", "valid_row_count", "invalid_row_count"])
@pytest.mark.parametrize("invalid", [-1, True, 1.5, "0"])
def test_nullable_page_counts_still_reject_invalid_values(field, invalid):
    assert_invalid_fact_and_materialization("execution_bvbrc_pages", [synthetic_page_fact(**{field: invalid})])


@pytest.mark.parametrize("field", ["returned_row_count", "valid_row_count", "invalid_row_count"])
def test_embedded_page_counts_keep_strict_integer_validation(field):
    value = synthetic_materialization("execution_bvbrc_pages", [synthetic_page_fact(**{field: 1.0})])
    with pytest.raises(ValueError):
        validate("ReceiverMaterialization", value)


@pytest.mark.parametrize("invalid", ["missing", "undeclared_reason", "", 0])
def test_page_unavailable_reason_is_required_and_closed(invalid):
    row = synthetic_page_fact(unavailable_reason=invalid)
    if invalid == "missing":
        del row["unavailable_reason"]
    assert_invalid_fact_and_materialization("execution_bvbrc_pages", [row])


@pytest.mark.parametrize("reason", ["transport_incomplete", "native_partial_results",
                                   "native_format_unverified", "native_value_invalid",
                                   "incompatible_input"])
def test_query_unavailable_facet_is_distinct_from_native_missing_term_bucket(reason):
    missing_bucket = synthetic_facet_fact()
    unavailable = synthetic_facet_fact(status="unavailable", bucket_ref=None,
        is_missing_bucket=None, term_ref=None, count=None, denominator=None, fraction=None,
        fraction_unavailable_reason=reason, bucket_window_status="invalid")
    assert_fact_and_materialization("execution_bvbrc_facets", [missing_bucket])
    assert_fact_and_materialization("execution_bvbrc_facets", [unavailable])
    assert missing_bucket["bucket_ref"] is not None and missing_bucket["is_missing_bucket"] is True
    assert missing_bucket["count"] == 0 and unavailable["count"] is None
    assert unavailable["bucket_ref"] is None and unavailable["is_missing_bucket"] is None
    assert unavailable["fraction_unavailable_reason"] == reason


def test_successful_empty_facet_array_remains_empty():
    assert_fact_and_materialization("execution_bvbrc_facets", [])


def test_acquired_invalid_facet_bucket_keeps_native_position_reference():
    row = synthetic_facet_fact(status="partial", is_missing_bucket=None, term_ref=None,
        count=None, fraction=None, fraction_unavailable_reason="native_value_invalid",
        bucket_window_status="invalid")
    assert_fact_and_materialization("execution_bvbrc_facets", [row])
    assert row["bucket_ref"] == "fixture:result#bucket/2"


@pytest.mark.parametrize("invalid", [True, 0, [], {}])
def test_nullable_facet_bucket_reference_retains_identifier_type(invalid):
    assert_invalid_fact_and_materialization("execution_bvbrc_facets", [synthetic_facet_fact(bucket_ref=invalid)])


@pytest.mark.parametrize("source, row", [
    ("execution_bvbrc_pages", synthetic_page_fact(extra=None)),
    ("execution_bvbrc_facets", synthetic_facet_fact(extra=None)),
])
def test_corrected_fact_objects_remain_closed(source, row):
    assert_invalid_fact_and_materialization(source, [row])


def test_schemas_and_validated_objects_are_detached():
    first = schema("DataSheet")
    first["$defs"]["DataSheet"].clear()
    assert schema("DataSheet")["$defs"]["DataSheet"]["type"] == "object"
    result = validate("DataSheet", EXAMPLES["facet_expected_sheet"])
    result["facets"][0]["buckets"].clear()
    assert len(EXAMPLES["facet_expected_sheet"]["facets"][0]["buckets"]) == 3


@pytest.mark.parametrize("value", [True, 1.0, float("nan"), float("inf"), float("-inf"), "1"])
def test_native_integer_type_is_strict(value):
    example = deepcopy(EXAMPLES["feature_sequence_expected_components"])
    example["relation_count"] = value
    with pytest.raises(ValueError):
        validate("FeatureSequenceComponents", example)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_finite_numeric_atoms(value):
    with pytest.raises(ValueError):
        validate("NativeAtom", dict(kind="number", string_value=None, boolean_value=None,
                                   number_value=value, number_lexeme="1"))


@pytest.mark.parametrize("mutation", ["extra", "missing", "tuple", "nonstring_key", "cycle"])
def test_closed_plain_json_shapes(mutation):
    value = deepcopy(EXAMPLES["facet_expected_components"])
    if mutation == "extra":
        value["unspecified"] = None
    elif mutation == "missing":
        del value["version"]
    elif mutation == "tuple":
        value["fractions"] = tuple(value["fractions"])
    elif mutation == "nonstring_key":
        value[0] = 1
    else:
        value["fractions"].append(value)
    with pytest.raises(ValueError):
        validate("FacetComponents", value)


@pytest.mark.parametrize("pointer", ["/a~2b", "not/a/pointer", "/dangling~", "/a~10~", "\n"])
def test_additive_supplied_locations_reject_invalid_pointers(pointer):
    with pytest.raises(ValueError):
        validate("SuppliedCellLocation", dict(cell_key="supplied/a", field="sample_ids",
            source_level="supplied", source_ref="source:a", record_path=pointer))


@pytest.mark.parametrize("pointer", ["", "/", "/design/0/sample_ids/0", "/a~1b/~0"])
def test_additive_supplied_locations_have_actual_source_provenance(pointer):
    value = dict(cell_key="supplied/source:a" + pointer, field="sample_ids",
                 source_level="supplied", source_ref="source:a", record_path=pointer)
    assert validate("SuppliedCellLocation", value) == value
    value["source_ref"] = ""
    with pytest.raises(ValueError):
        validate("SuppliedCellLocation", value)


def test_invalid_names_raise_value_error():
    for value in ("NotASchema", [], None):
        with pytest.raises(ValueError):
            schema(value)
        with pytest.raises(ValueError):
            validate(value, {})


def test_unicode_digest_uses_actual_utf8_and_is_independent_of_key_order():
    value = {"z": "β-lactamase", "a": ["café", 0, None]}
    expected_bytes = '{"a":["café",0,null],"z":"β-lactamase"}'.encode("utf-8")
    expected = hashlib.sha256(expected_bytes).hexdigest()
    assert json_digest(value) == expected
    assert json_digest({"a": value["a"], "z": value["z"]}) == expected
    assert json_digest(value) != hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), (1, 2), {1: "not a string key"}])
def test_digest_does_not_coerce_non_json_values(bad):
    with pytest.raises(ValueError):
        json_digest(bad)
