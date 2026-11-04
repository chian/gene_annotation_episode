"""D3 supplied-sheet tests; the builder below is an explicitly labeled fixture.

Native bytes are retained contract-study responses. Building DataSheet objects
here tests D3 against the frozen D2 interface, not production parsing/acquisition.
"""

from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import jsonschema
import pytest

from gene_annotation_episode.bvbrc_data_fields import FIELD_REGISTRY
from gene_annotation_episode.bvbrc_data_feature_sequences import (
    FEATURE_SEQUENCE_COMPONENTS_SCHEMA,
    FEATURE_SEQUENCE_SHEET_SCHEMA,
    extract_feature_sequence_join,
)
from gene_annotation_episode.bvbrc_data_schema import validate
from gene_annotation_episode.bvbrc_data_calculators import calculate_feature_sequence_counts

EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
AA_MD5 = "7594e119ffe8456710f27d137885e84c"
NA_MD5 = "584ae482fd635ee1fb6243df48fb8508"
FEATURE_IDS = ["PATRIC.511145.12.NC_000913.CDS.822959.823720.rev",
               "RefSeq.511145.12.NC_000913.CDS.822959.823720.rev"]


def fixture_sheet(collection, native_rows, fields=None, *, raw_bytes=None, profile="json_array_with_headers_v1"):
    """TEST ONLY: construct frozen-shape supplied sheets with labeled custody.

    Native cells below copy supplied JSON values. Population/prepared/time fields
    are explicitly fixture metadata, not an actual prepared request or receipt.
    """
    registry = FIELD_REGISTRY[collection]
    fields = list(dict.fromkeys(key for row in native_rows for key in row)) if fields is None else fields
    native_body = native_rows if profile == "json_array_with_headers_v1" else {
        "responseHeader": {"status": 0}, "response": {"docs": native_rows, "start": 0, "numFound": len(native_rows)}}
    raw_bytes = json.dumps(native_body, separators=(",", ":")).encode() if raw_bytes is None else raw_bytes
    digest = hashlib.sha256(raw_bytes).hexdigest()
    rows = []
    for index, native in enumerate(native_rows):
        row_key = digest + "/row/" + str(index)
        path = ("/response/docs/" if profile == "solr_json_envelope_v1" else "/") + str(index)
        cells, numeric = [], []
        for field in fields:
            spec = registry["fields"][field]
            value = native.get(field)
            presence = "absent" if field not in native else "null" if value is None else "present"
            shape = "absent" if presence == "absent" else "null" if value is None else (
                "array" if type(value) is list else "object" if type(value) is dict else "scalar")
            complex_array = shape == "array" and any(type(item) in (dict, list) for item in value)
            values = [] if presence != "present" or shape == "object" or complex_array else value if shape == "array" else [value]
            atoms = []
            for item in values:
                kind = "null" if item is None else "boolean" if type(item) is bool else (
                    "number" if type(item) in (int, float) else "string")
                atoms.append({"kind": kind, "string_value": item if kind == "string" else None,
                              "number_value": item if kind == "number" else None,
                              "boolean_value": item if kind == "boolean" else None,
                              "number_lexeme": json.dumps(item) if kind == "number" else None})
            expected_type = "number" if spec["solr_type"] in ("int", "long", "float") else (
                "boolean" if spec["solr_type"] == "boolean" else "string")
            valid = not complex_array and shape == ("array" if spec["multi_valued"] else "scalar") and all(
                atom["kind"] == expected_type and (spec["solr_type"] not in ("int", "long")
                    or type(atom["number_value"]) is int) for atom in atoms)
            status = "missing" if presence != "present" else "valid" if valid else "invalid"
            codes = [] if status != "invalid" else ["bvbrc_invalid_native_field"]
            key = row_key + "/field/" + field
            cell = {"cell_key": key, "field": field, "native_path": path + "/" + field,
                    "presence": presence, "native_shape": shape, "atoms": atoms, "status": status,
                    "field_schema_status": "not_evaluated" if status == "missing" else "match" if valid else "mismatch",
                    "issue_codes": codes}
            cells.append(cell)
            if spec["numeric_projection"]:
                present = status == "valid" and type(value) in (int, float)
                numeric.append({"cell_key": key, "field": field, "native_path": path + "/" + field,
                                "value": value if present else None,
                                "status": "reported" if present else "missing" if status == "missing" else "invalid",
                                "reason": None if present else "native_null" if presence == "null" else (
                                    "native_field_absent" if presence == "absent" else "native_value_invalid"),
                                "quantity_kind": spec["quantity_kind"], "unit_code": spec["unit_code"],
                                "unit_basis": spec["unit_basis"], "unit_cell_keys": [],
                                "denominator_value": None, "denominator_basis": "unknown",
                                "origin": "native_reported" if present else "unavailable",
                                "uncertainty_cell_keys": [], "issue_codes": codes})
        identity = native.get(registry["unique_key"]) if registry["unique_key"] in fields else None
        identity = identity if type(identity) is str and identity else None
        rows.append({"row_key": row_key, "row_index": index, "native_path": path, "native_id": identity,
                     "status": "valid" if identity is not None and all(c["status"] != "invalid" for c in cells) else "partial",
                     "cells": cells, "numerical_cells": numeric, "issues": []})
    valid_count = sum(row["status"] == "valid" for row in rows)
    return validate("DataSheet", {
        "version": "bvbrc_data_sheet_v1", "collection": collection, "mode": "page",
        "custody": {"native_sha256": digest, "retrieved_at": "synthetic_supplied_sheet_fixture",
                    "requested_url": "https://fixture.invalid/" + collection,
                    "effective_url": "https://fixture.invalid/" + collection,
                    "media_type": "application/json" if profile == "json_array_with_headers_v1" else "application/solr+json",
                    "native_profile": profile, "prepared_sha256": "0" * 64,
                    "field_contract_version": "bvbrc_data_fields_2026_10_24_v1"},
        "transport": {"http_status": 200, "body_complete": True, "headers": [], "failure_code": None,
                      "automatic_redirects": False, "native_query_time_ms": None},
        "qualification": {"service_matches": True, "request_matches": True, "transport_complete": True,
                          "http_success": True, "format_valid": True, "population_metadata_valid": True,
                          "native_partial_results": None, "requested_fields_valid": valid_count == len(rows),
                          "status": "complete" if valid_count == len(rows) else "partial"},
        "population": {"population_key": "0" * 64, "compiled_query": None, "echoed_query": None,
                       "echoed_filter_queries": [], "reported_total": len(rows), "native_num_found_exact": None,
                       "exactness": "provider_reported", "native_location": None},
        "selected_fields": fields,
        "page": {"mode": "page", "requested_offset": 0, "requested_limit": max(1, len(rows)),
                 "response_start": 0, "native_content_range": None, "returned_row_count": len(rows),
                 "valid_row_count": valid_count, "invalid_row_count": len(rows) - valid_count,
                 "reported_total": len(rows), "count_exactness": "provider_reported", "response_complete": True,
                 "population_coverage": "unknown", "next_offset": None, "next_offset_basis": None},
        "count": {"population_key": "0" * 64, "reported_value": len(rows), "exactness": "provider_reported",
                  "availability": "available", "reason": None, "native_location": None},
        "rows": rows, "facets": [], "issues": [],
    })


def native_fixture():
    features_bytes = (EVIDENCE / "feature_page.body").read_bytes()
    sequence_bytes = (EVIDENCE / "feature_sequences.body").read_bytes()
    features, sequences = json.loads(features_bytes), json.loads(sequence_bytes)
    fields = ["feature_id", "genome_id", "sequence_id", "patric_id", "gene", "aa_sequence_md5",
              "na_sequence_md5", "aa_length", "na_length", "start", "end", "strand", "annotation"]
    return (fixture_sheet("genome_feature", features, fields, raw_bytes=features_bytes),
            fixture_sheet("feature_sequence", sequences, ["md5", "sequence_type", "sequence"], raw_bytes=sequence_bytes))


def small_fixture(*, feature_changes=None, sequence_rows=None, feature_rows=None, sequence="MAb "):
    digest = hashlib.md5(sequence.encode("ascii")).hexdigest()
    feature = {"feature_id": "F", "aa_sequence_md5": digest, "aa_length": len(sequence),
               "start": 10, "end": 999, "strand": "-", "segments": ["10..11", "998..999"]}
    feature.update(feature_changes or {})
    features = [feature] if feature_rows is None else feature_rows
    sequences = [{"md5": digest, "sequence_type": "AA", "sequence": sequence}] if sequence_rows is None else sequence_rows
    return fixture_sheet("genome_feature", features), fixture_sheet("feature_sequence", sequences)


def join(features, sequences, **kwargs):
    return extract_feature_sequence_join([features], [sequences], feature_ids=kwargs.get("feature_ids", ["F"]),
                                         sequence_kind=kwargs.get("sequence_kind", "AA"))


def test_retained_native_example_has_four_relations_exact_hashes_and_source_values():
    features, sequences = native_fixture()
    result = join(features, sequences, feature_ids=FEATURE_IDS, sequence_kind="both")
    expected = json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())["feature_sequence_expected_sheet"]
    assert result["input_page_counts"] == expected["input_page_counts"]
    assert result["input_native_sha256s"] == expected["input_native_sha256s"]
    assert len(result["edges"]) == 4
    for actual, frozen in zip(result["edges"], expected["edges"]):
        assert {k: v for k, v in actual.items() if k != "feature_metadata_cells"} == {
            k: v for k, v in frozen.items() if k != "feature_metadata_cells"}
        assert all(cell in actual["feature_metadata_cells"] for cell in frozen["feature_metadata_cells"])
        assert "gene" in {cell["field"] for cell in actual["feature_metadata_cells"]}
    assert [edge["sequence_length"] for edge in result["edges"]] == [253, 762, 253, 762]
    assert [edge["native_md5"] for edge in result["edges"]] == [AA_MD5, NA_MD5, AA_MD5, NA_MD5]
    sequence = sequences["rows"][0]["cells"][2]["atoms"][0]["string_value"]
    assert sequence == sequence.lower()
    assert hashlib.md5(sequence.encode("ascii")).hexdigest() == NA_MD5
    assert hashlib.md5(sequence.upper().encode("ascii")).hexdigest() != NA_MD5
    assert not result["requirements"] and not result["issues"]
    components = calculate_feature_sequence_counts(result)
    assert components == json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())["feature_sequence_expected_components"]
    assert_source_locators(result, [features, sequences])
    frozen_defs = json.loads((EVIDENCE / "CONTRACT_SHAPES.json").read_text())["schemas"]["$defs"]
    jsonschema.Draft202012Validator({"$ref": "#/$defs/FeatureSequenceSheet", "$defs": frozen_defs}).validate(result)
    # Explicit additive correction002 narrows native CellLocation to native
    # source levels; supplied provenance has its own separate location shape.
    frozen_defs["CellLocation"]["properties"]["source_level"]["enum"].remove("supplied")
    def expand(value, definitions):
        if type(value) is dict:
            if "$ref" in value:
                return expand(definitions[value["$ref"].split("/")[-1]], definitions)
            return {key: expand(child, definitions) for key, child in value.items()}
        if type(value) is list:
            return [expand(child, definitions) for child in value]
        return value
    for exported, name in ((FEATURE_SEQUENCE_SHEET_SCHEMA, "FeatureSequenceSheet"),
                           (FEATURE_SEQUENCE_COMPONENTS_SCHEMA, "FeatureSequenceComponents")):
        assert expand(exported["$defs"][name], exported["$defs"]) == expand(frozen_defs[name], frozen_defs)


def assert_source_locators(result, pages):
    rows = {(p["custody"]["native_sha256"], p["collection"], r["row_key"]): r for p in pages for r in p["rows"]}
    for edge in result["edges"]:
        for location in edge["feature_rows"] + edge["sequence_rows"]:
            assert (location["native_sha256"], location["collection"], location["row_key"]) in rows
        for location in edge["sequence_cells"] + edge["feature_metadata_cells"]:
            row = rows[location["native_sha256"], location["collection"], location["row_key"]]
            assert any(c["cell_key"] == location["cell_key"] and c["field"] == location["field"] for c in row["cells"])


@pytest.mark.parametrize("kind,expected", [("AA", [253, 253]), ("NA", [762, 762])])
def test_modes_order_and_exact_feature_ids(kind, expected):
    features, sequences = native_fixture()
    result = join(features, sequences, feature_ids=list(reversed(FEATURE_IDS)), sequence_kind=kind)
    assert [e["feature_id"] for e in result["edges"]] == list(reversed(FEATURE_IDS))
    assert [e["sequence_length"] for e in result["edges"]] == expected
    alias = join(features, sequences, feature_ids=["fig|511145.12.peg.816"])
    assert alias["edges"][0]["join_status"] == "missing_feature"


def test_same_page_repeated_delivery_does_not_add_relations_or_counts():
    features, sequences = native_fixture()
    expected = join(features, sequences, feature_ids=FEATURE_IDS, sequence_kind="both")
    actual = extract_feature_sequence_join([features, deepcopy(features)], [sequences, deepcopy(sequences)],
                                           feature_ids=FEATURE_IDS, sequence_kind="both")
    assert actual == expected


def test_duplicate_native_sequence_rows_remain_distinguishable():
    sequence = "MAb "
    native = {"md5": hashlib.md5(sequence.encode()).hexdigest(), "sequence_type": "AA", "sequence": sequence}
    features, sequences = small_fixture(sequence_rows=[native, deepcopy(native), {"md5": "f" * 32,
                                        "sequence_type": "AA", "sequence": "UNJOINED"}])
    result = join(features, sequences)
    edge = result["edges"][0]
    assert edge["join_status"] == "repeated_identical"
    assert len(edge["sequence_rows"]) == 2
    assert edge["sequence_rows"][0] != edge["sequence_rows"][1]
    assert result["input_page_counts"][1]["retained_row_count"] == 3
    assert edge["sequence_length"] == 4 and edge["raw_md5_match"] is True


def test_distinct_raw_sequence_pages_and_duplicate_feature_occurrences_are_retained():
    features, sequences = small_fixture()
    duplicate_native = {"feature_id": "F", "aa_sequence_md5": hashlib.md5(b"MAb ").hexdigest(), "aa_length": 4}
    features = fixture_sheet("genome_feature", [duplicate_native, deepcopy(duplicate_native)])
    other_rows = [{"md5": duplicate_native["aa_sequence_md5"], "sequence_type": "AA", "sequence": "MAb "}]
    other = fixture_sheet("feature_sequence", other_rows, raw_bytes=json.dumps(other_rows, indent=1).encode())
    result = extract_feature_sequence_join([features], [sequences, other], feature_ids=["F"], sequence_kind="AA")
    assert len(result["edges"]) == 2
    assert all(e["join_status"] == "repeated_identical" and len(e["sequence_rows"]) == 2 for e in result["edges"])
    assert len(result["input_page_counts"]) == 3


@pytest.mark.parametrize("changed", [{"sequence": "XXXX"}, {"sequence": "XXXXX"}, {"sequence_type": "NA"}])
def test_conflicting_sequence_candidates_never_choose_first(changed):
    native = {"md5": hashlib.md5(b"MAb ").hexdigest(), "sequence_type": "AA", "sequence": "MAb "}
    features, sequences = small_fixture(sequence_rows=[native, {**native, **changed}])
    result = join(features, sequences)
    edge = result["edges"][0]
    assert edge["join_status"] == "conflict" and edge["reason"] == "ambiguous_join"
    assert len(edge["sequence_rows"]) == len(edge["sequence_cells"]) == 2
    assert edge["sequence_length"] == (None if changed.get("sequence") == "XXXXX" else 4)
    reversed_sequences = fixture_sheet("feature_sequence", [{**native, **changed}, native])
    reversed_edge = join(features, reversed_sequences)["edges"][0]
    for key in ("join_status", "reason", "sequence_length", "raw_md5_match", "length_match"):
        assert edge[key] == reversed_edge[key]


@pytest.mark.parametrize("change,flag", [({"aa_length": 5}, False), ({"aa_length": -1}, None),
                                         ({"aa_length": 4.0}, None), ({"aa_length": True}, None)])
def test_mismatched_or_invalid_feature_length(change, flag):
    features, sequences = small_fixture(feature_changes=change)
    result = join(features, sequences)
    edge = result["edges"][0]
    assert edge["join_status"] == "conflict"
    assert edge["length_match"] is flag
    assert edge["feature_length"] == (5 if flag is False else None)
    assert edge["sequence_length"] == 4
    assert {r["collection"] for r in result["requirements"]} == {"genome_feature"}


def test_conflicting_feature_copies_both_survive():
    native = {"feature_id": "F", "aa_sequence_md5": hashlib.md5(b"MAb ").hexdigest(), "aa_length": 4}
    features, sequences = small_fixture(feature_rows=[native, {**native, "aa_length": 5}])
    result = join(features, sequences)
    assert len(result["edges"]) == 2
    assert [e["feature_length"] for e in result["edges"]] == [4, 5]
    assert all(e["join_status"] == "conflict" and e["reason"] == "conflicting_metadata" for e in result["edges"])


def test_empty_pages_absent_pages_and_unselected_feature_are_distinct():
    empty_features = fixture_sheet("genome_feature", [], ["feature_id"])
    empty_sequences = fixture_sheet("feature_sequence", [], ["md5", "sequence_type", "sequence"])
    absent = extract_feature_sequence_join([], [], feature_ids=["F"], sequence_kind="both")
    empty = join(empty_features, empty_sequences, sequence_kind="both")
    assert [e["reason"] for e in absent["edges"]] == ["missing_input_page"] * 2
    assert [e["reason"] for e in empty["edges"]] == ["missing_feature_record"] * 2
    assert absent["input_page_counts"] == []
    assert [p["retained_row_count"] for p in empty["input_page_counts"]] == [0, 0]
    assert empty["input_native_sha256s"] == [hashlib.sha256(b"[]").hexdigest()]
    assert len(empty["input_page_counts"]) == 2  # Same bytes, distinct collections.
    assert len(empty["requirements"]) == 1


@pytest.mark.parametrize("mode,reason", [("absent", "native_field_absent"), ("null", "native_null"), ("unselected", "not_selected")])
def test_missing_hash_states_and_requirements(mode, reason):
    row = {"feature_id": "F", "aa_length": 4}
    if mode == "null":
        row["aa_sequence_md5"] = None
    fields = ["feature_id", "aa_length"] + ([] if mode == "unselected" else ["aa_sequence_md5"])
    features = fixture_sheet("genome_feature", [row], fields)
    _, sequences = small_fixture()
    result = join(features, sequences)
    assert result["edges"][0]["join_status"] == "missing_key"
    assert result["edges"][0]["reason"] == reason
    assert result["requirements"] == [{"collection": "genome_feature", "field": "feature_id", "values": ["F"],
                                       "sequence_kind": "AA", "reason": reason}]


def test_missing_sequence_page_record_and_unselected_text_are_distinct():
    features, sequences = small_fixture()
    no_pages = extract_feature_sequence_join([features], [], feature_ids=["F"], sequence_kind="AA")
    no_records = join(features, fixture_sheet("feature_sequence", [], ["md5"]))
    text_not_selected = fixture_sheet("feature_sequence", [{"md5": hashlib.md5(b"MAb ").hexdigest(), "sequence_type": "AA"}])
    no_text = join(features, text_not_selected)
    assert [r["edges"][0]["reason"] for r in (no_pages, no_records, no_text)] == [
        "missing_input_page", "missing_sequence_record", "sequence_text_unavailable"]
    assert no_text["edges"][0]["join_status"] == "missing_sequence"
    assert no_text["requirements"][0]["reason"] == "not_selected"
    assert no_text["edges"][0]["sequence_cells"] == []
    assert no_pages["requirements"][0]["values"] == [hashlib.md5(b"MAb ").hexdigest()]


@pytest.mark.parametrize("value", [None, "", 7])
def test_null_empty_and_invalid_sequence_values(value):
    features, sequences = small_fixture(sequence_rows=[{"md5": hashlib.md5(b"MAb ").hexdigest(),
                                                       "sequence_type": "AA", "sequence": value}])
    edge = join(features, sequences)["edges"][0]
    assert edge["sequence_length"] == (0 if value == "" else None)
    assert edge["join_status"] == ("conflict" if value == "" else "missing_sequence")
    assert len(edge["sequence_cells"]) == 1


def test_true_zero_length_and_no_span_or_translation_inference():
    features, sequences = small_fixture(sequence="")
    result = join(features, sequences)
    edge = result["edges"][0]
    assert edge["sequence_length"] == edge["feature_length"] == 0
    assert edge["length_match"] is True and edge["join_status"] == "joined"
    assert {"start", "end", "strand", "segments"} <= {c["field"] for c in edge["feature_metadata_cells"]}
    missing_length = fixture_sheet("genome_feature", [{"feature_id": "F", "aa_sequence_md5": hashlib.md5(b"").hexdigest(),
                                                       "start": 1, "end": 99}])
    edge = join(missing_length, sequences)["edges"][0]
    assert edge["feature_length"] is None and edge["length_match"] is None
    assert edge["join_status"] == "joined"


def test_exact_bytes_no_uppercase_strip_or_unicode_substitution():
    features, sequences = small_fixture()
    assert join(features, sequences)["edges"][0]["raw_md5_match"] is True
    wrong = fixture_sheet("feature_sequence", [{"md5": hashlib.md5(b"MAb ").hexdigest(), "sequence_type": "AA", "sequence": "MAB"}])
    edge = join(features, wrong)["edges"][0]
    assert edge["raw_md5_match"] is False and edge["length_match"] is False
    unicode = fixture_sheet("feature_sequence", [{"md5": hashlib.md5(b"MAb ").hexdigest(), "sequence_type": "AA", "sequence": "M\u00e9b "}])
    edge = join(features, unicode)["edges"][0]
    assert edge["raw_md5_match"] is None and edge["sequence_length"] == 4
    assert edge["join_status"] == "conflict" and edge["reason"] == "native_value_invalid"


@pytest.mark.parametrize("hash_value", ["bad", "g" * 32, "", " 0" * 16, 4])
def test_invalid_hashes_are_not_silently_normalized(hash_value):
    features, sequences = small_fixture(feature_changes={"aa_sequence_md5": hash_value})
    edge = join(features, sequences)["edges"][0]
    assert edge["join_status"] == "conflict" and edge["reason"] == "native_value_invalid"
    assert edge["native_md5"] == (hash_value if type(hash_value) is str else None)


@pytest.mark.parametrize("kind", ["NA", "aa", "DNA", ""])
def test_sequence_types_are_exact(kind):
    features, sequences = small_fixture(sequence_rows=[{"md5": hashlib.md5(b"MAb ").hexdigest(), "sequence_type": kind, "sequence": "MAb "}])
    edge = join(features, sequences)["edges"][0]
    assert edge["join_status"] == "type_mismatch" and edge["reason"] == "sequence_type_mismatch"
    assert edge["raw_md5_match"] is True


def test_native_type_unavailable_does_not_become_an_assumed_aa_type():
    features, sequences = small_fixture(sequence_rows=[{"md5": hashlib.md5(b"MAb ").hexdigest(), "sequence": "MAb "}])
    result = join(features, sequences)
    assert result["edges"][0]["join_status"] == "conflict"
    assert result["edges"][0]["reason"] == "not_selected"


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(collection="genome"),
    lambda p: p.update(mode="count"),
    lambda p: p["page"].update(returned_row_count=0),
    lambda p: p["page"].update(valid_row_count=True),
    lambda p: p["page"].update(returned_row_count=1.0),
    lambda p: p["rows"][0].update(row_index=1),
    lambda p: p["rows"][0].update(row_key="forged"),
    lambda p: p["rows"][0].update(native_path="/99"),
    lambda p: p["rows"][0].update(native_id="other"),
    lambda p: p["rows"][0]["cells"][0].update(cell_key="forged"),
    lambda p: p["rows"][0]["cells"][0].update(native_path="/99/feature_id"),
    lambda p: p["rows"][0]["cells"][0]["atoms"][0].update(number_value=2),
    lambda p: p["rows"][0]["cells"][0]["atoms"].clear(),
    lambda p: p["rows"][0]["numerical_cells"][0].update(value=True),
    lambda p: p["rows"][0]["numerical_cells"][0].update(value=44),
    lambda p: p["rows"][0]["numerical_cells"][0].update(cell_key="forged"),
    lambda p: p["transport"].update(native_query_time_ms=float("nan")),
    lambda p: p["transport"].update(native_query_time_ms=float("inf")),
    lambda p: p.update(unexpected=True),
])
def test_invalid_supplied_sheet_structure_is_rejected(mutation):
    features, sequences = small_fixture()
    mutation(features)
    with pytest.raises(ValueError):
        join(features, sequences)


def test_numeric_lexeme_validation_and_unrepresentable_not_zero():
    features, sequences = small_fixture()
    cell = next(c for c in features["rows"][0]["cells"] if c["field"] == "aa_length")
    cell["atoms"][0]["number_lexeme"] = "4e-999"
    with pytest.raises(ValueError):
        join(features, sequences)
    cell["status"] = "unrepresentable"
    cell["issue_codes"] = ["bvbrc_unrepresentable_numeric_value"]
    cell["atoms"][0]["number_value"] = None
    features["rows"][0]["numerical_cells"][0].update(value=None, status="invalid", reason="unrepresentable_numeric_value")
    features["rows"][0]["status"] = "partial"
    features["page"].update(valid_row_count=0, invalid_row_count=1)
    edge = join(features, sequences)["edges"][0]
    assert edge["feature_length"] is None and edge["length_match"] is None


@pytest.mark.parametrize("ids,kind", [([], "AA"), (["F", "F"], "AA"), (("F",), "AA"), ([1], "AA"), (["F"], "dna"), (["F"], None)])
def test_selection_is_closed_and_typed(ids, kind):
    with pytest.raises(ValueError):
        extract_feature_sequence_join([], [], feature_ids=ids, sequence_kind=kind)


def test_reprojection_same_bytes_merges_only_compatible_cells():
    rows = [{"feature_id": "F", "aa_sequence_md5": hashlib.md5(b"MAb ").hexdigest(), "aa_length": 4,
             "gene": "g", "product": "source product"}]
    raw = json.dumps(rows).encode()
    a = fixture_sheet("genome_feature", rows, ["feature_id", "aa_sequence_md5", "aa_length", "gene"], raw_bytes=raw)
    b = fixture_sheet("genome_feature", rows, ["feature_id", "aa_sequence_md5", "aa_length", "product"], raw_bytes=raw)
    _, sequences = small_fixture()
    result = extract_feature_sequence_join([a, b], [sequences], feature_ids=["F"], sequence_kind="AA")
    assert len(result["edges"]) == 1 and len(result["input_page_counts"]) == 2
    assert {"gene", "product"} <= {c["field"] for c in result["edges"][0]["feature_metadata_cells"]}
    conflicting = deepcopy(a)
    conflicting["rows"][0]["cells"][-1]["atoms"][0]["string_value"] = "different"
    with pytest.raises(ValueError, match="conflicting_repeated_cell"):
        extract_feature_sequence_join([a, conflicting], [sequences], feature_ids=["F"], sequence_kind="AA")


def test_no_input_mutation_or_io_and_output_is_detached(monkeypatch):
    features, sequences = native_fixture()
    original = deepcopy([features, sequences])

    def forbidden(*args, **kwargs):
        raise AssertionError("D3 attempted I/O")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = join(features, sequences, feature_ids=FEATURE_IDS, sequence_kind="both")
    assert [features, sequences] == original
    result["selection"]["feature_ids"][0] = "changed"
    result["edges"][0]["feature_rows"][0]["row_key"] = "changed"
    assert [features, sequences] == original
    assert FEATURE_IDS[0].startswith("PATRIC.")


def test_solr_paths_resolve_and_partial_rows_keep_usable_values():
    features, sequences = small_fixture()
    raw = [{"feature_id": "F", "aa_sequence_md5": hashlib.md5(b"MAb ").hexdigest(), "aa_length": 4,
            "start": "bad coordinate"}]
    features = fixture_sheet("genome_feature", raw, profile="solr_json_envelope_v1")
    features["qualification"]["native_partial_results"] = True
    issue = {"code": "bvbrc_native_partial_results", "phase": "format", "row_index": None,
             "field": None, "native_path": "/responseHeader/partialResults", "http_status": None}
    features["issues"] = [issue]
    result = join(features, sequences)
    assert result["edges"][0]["join_status"] == "joined"
    assert result["issues"] == [issue]
    assert result["input_page_counts"][0]["valid_row_count"] == 0
    assert_source_locators(result, [features, sequences])


def test_saved_sheet_calculator_counts_unjoined_rows_and_repeated_representations(monkeypatch):
    native = {"md5": hashlib.md5(b"MAb ").hexdigest(), "sequence_type": "AA", "sequence": "MAb "}
    features, sequences = small_fixture(sequence_rows=[native, deepcopy(native),
        {"md5": hashlib.md5(b"OTHER").hexdigest(), "sequence_type": "AA", "sequence": "OTHER"}])
    result = join(features, sequences)
    saved = json.loads(json.dumps(result))

    def forbidden(*args, **kwargs):
        raise AssertionError("saved-sheet calculation attempted I/O")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    components = calculate_feature_sequence_counts(saved)
    assert components == {"version": "bvbrc_feature_sequence_components_v1", "selected_feature_count": 1,
        "retained_feature_row_count": 1, "native_sequence_record_count": 3, "distinct_joined_aa_sequence_count": 1,
        "distinct_joined_na_sequence_count": 0, "relation_count": 1, "missing_key_count": 0,
        "missing_record_count": 0, "conflicting_relation_count": 0, "length_agreement_count": 1}
    assert saved == result


def test_differing_candidate_lengths_leave_scalar_length_and_agreement_unknown():
    md5 = hashlib.md5(b"MAb ").hexdigest()
    features, sequences = small_fixture(sequence_rows=[
        {"md5": md5, "sequence_type": "AA", "sequence": "XX"},
        {"md5": md5, "sequence_type": "AA", "sequence": "YYY"}])
    result = join(features, sequences)
    assert result["edges"][0]["sequence_length"] is None
    assert result["edges"][0]["length_match"] is None
    components = calculate_feature_sequence_counts(result)
    assert components["conflicting_relation_count"] == 1 and components["relation_count"] == 0


def test_hash_join_is_case_sensitive_and_raw_digest_is_not_normalized():
    features, sequences = small_fixture()
    native_hash = hashlib.md5(b"MAb ").hexdigest()
    upper_row = {"md5": native_hash.upper(), "sequence_type": "AA", "sequence": "MAb "}
    sequences = fixture_sheet("feature_sequence", [upper_row])
    assert join(features, sequences)["edges"][0]["join_status"] == "missing_record"
    features = fixture_sheet("genome_feature", [{"feature_id": "F", "aa_sequence_md5": native_hash.upper(), "aa_length": 4}])
    edge = join(features, sequences)["edges"][0]
    assert edge["native_md5"] == native_hash.upper() and edge["raw_md5_match"] is False
    assert edge["join_status"] == "conflict"


@pytest.mark.parametrize("mutation", [
    lambda p: p["rows"][0]["cells"][0].update(presence="absent", native_shape="absent", atoms=[]),
    lambda p: p["rows"][0]["numerical_cells"].clear(),
    lambda p: p["rows"][0]["cells"][2].update(status="invalid"),
])
def test_cross_field_status_and_numeric_slot_mismatches_are_rejected(mutation):
    features, sequences = small_fixture()
    mutation(features)
    with pytest.raises(ValueError):
        join(features, sequences)


def test_invalid_sequence_collection_and_nonlist_pages_are_rejected():
    features, sequences = small_fixture()
    with pytest.raises(ValueError):
        extract_feature_sequence_join([features], [features], feature_ids=["F"], sequence_kind="AA")
    with pytest.raises(ValueError):
        extract_feature_sequence_join((features,), [sequences], feature_ids=["F"], sequence_kind="AA")


def test_native_empty_identity_and_invalid_array_metadata_keep_useful_partial_data():
    features, sequences = small_fixture(feature_changes={"feature_id": ""})
    assert join(features, sequences, feature_ids=[""])["edges"][0]["join_status"] == "missing_feature"
    features, sequences = small_fixture(feature_changes={"segments": [{"position": 1}, [2, 3]]})
    result = join(features, sequences)
    assert result["edges"][0]["join_status"] == "joined"
    assert result["input_page_counts"][0]["valid_row_count"] == 0
    segments = next(c for c in features["rows"][0]["cells"] if c["field"] == "segments")
    assert segments["atoms"] == [] and segments["native_shape"] == "array" and segments["status"] == "invalid"
    assert_source_locators(result, [features, sequences])


def retained_decoder_fixture():
    """Actual D2 payload decoding, deliberately unqualified as a v2 request."""
    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.bvbrc_data_query import encode_native_query
    from gene_annotation_episode.bvbrc_data_readers import _decode_native_payload

    fixture_features, fixture_sequences = native_fixture()
    result = []
    for name, fixture in (("feature_page", fixture_features), ("feature_sequences", fixture_sequences)):
        metadata = json.loads((EVIDENCE / (name + ".meta.json")).read_text())
        content = (EVIDENCE / (name + ".body")).read_bytes()
        assert hashlib.sha256(content).hexdigest() == metadata["sha256"]
        assert len(content) == metadata["byte_count"]
        media = next(value for key, value in metadata["headers"] if key.lower() == "content-type")
        snapshot = SourceSnapshot("bvbrc_data", metadata["url"], {}, metadata["retrieved_at"], content, media,
            {"status": metadata["status"], "body_complete": metadata["body_complete"],
             "header_items": metadata["headers"], "effective_url": metadata["effective_url"],
             "automatic_redirects": False})
        prepared = encode_native_query({"version": "bvbrc_data_request_v2", "collection": fixture["collection"],
                                        "mode": "page", "filters": [], "fields": fixture["selected_fields"]},
                                       base_url="https://www.bv-brc.org/api")
        decoded = _decode_native_payload(snapshot, prepared=prepared)
        assert decoded["sheet"] is not None
        assert decoded["sheet"]["qualification"]["request_matches"] is False
        result.append(decoded["sheet"])
    return result


def test_actual_native_decoder_to_join_to_separate_calculator():
    features, sequences = retained_decoder_fixture()
    result = join(features, sequences, feature_ids=FEATURE_IDS, sequence_kind="both")
    assert result["edges"] == join(*native_fixture(), feature_ids=FEATURE_IDS, sequence_kind="both")["edges"]
    expected = json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())["feature_sequence_expected_components"]
    assert calculate_feature_sequence_counts(result) == expected
    assert {issue["code"] for issue in result["issues"]} == {"bvbrc_response_request_mismatch"}
    assert_source_locators(result, [features, sequences])


def test_public_v2_parser_to_join_with_explicitly_synthetic_solr_transport():
    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.bvbrc_data_query import encode_native_query
    from gene_annotation_episode.bvbrc_data_readers import parse_data_snapshot

    pages = []
    for name, fixture in zip(("feature_page", "feature_sequences"), native_fixture()):
        native_rows = json.loads((EVIDENCE / (name + ".body")).read_text())
        prepared = encode_native_query({"version": "bvbrc_data_request_v2", "collection": fixture["collection"],
                                        "mode": "page", "filters": [], "fields": fixture["selected_fields"]},
                                       base_url="https://fixture.invalid/api")
        body = json.dumps({"responseHeader": {"status": 0}, "response": {
            "docs": native_rows, "start": 0, "numFound": 2, "numFoundExact": True}}).encode()
        native_request = prepared["native_request"]
        source = SourceSnapshot("bvbrc_data", native_request["url"], prepared["effective_request"],
            "synthetic_transport_fixture", body, "application/solr+json", {
                "status": 200, "body_complete": True, "automatic_redirects": False,
                "request": deepcopy(native_request), "effective_url": native_request["url"], "headers": []})
        parsed = parse_data_snapshot(source, prepared=prepared)
        assert parsed["status"] == "complete"
        pages.append(parsed["sheet"])
    joined = join(*pages, feature_ids=FEATURE_IDS, sequence_kind="both")
    assert len(joined["edges"]) == 4 and not joined["issues"]
    assert calculate_feature_sequence_counts(joined)["length_agreement_count"] == 4
    assert_source_locators(joined, pages)
