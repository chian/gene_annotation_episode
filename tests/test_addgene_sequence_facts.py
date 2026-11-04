"""Literal metadata contracts using retained HTML and engineered publications.

The retained public page supplies no sequence bases. Engineering inline HTML
tests the existing parser's available/invalid/download states. No actual API
commission, authenticated download or Source custody is claimed by these tests.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import addgene_sequence_facts as facts
from gene_annotation_episode import addgene_sequence_native as native
from gene_annotation_episode import sequence_support_publication as publication
from gene_annotation_episode.acquisition import PublicClients


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
SOURCE = "source_" + "a" * 24
OTHER_SOURCE = "source_" + "b" * 24
FIXTURES = Path(__file__).parent / "fixtures/addgene_sequence_page"
ENTITY_SHA = "deb0393a4b1c71ae21e438a7dd2a6f410defbc83c3e939c2ce10faf0b4b30c4d"
METADATA_SHA = "ae1e05538cb541d5e1ad6a6610e690204e8d426066ba6432494c72ef62aa0e06"


def _literal(text, sequence_id, section="addgene-full"):
    return (f'<section id="{section}"><div data-sequence-id="{sequence_id}">'
        f'<textarea class="copy-from">{text}</textarea></div></section>')


def _inline():
    return (_literal("&gt; original header  \r\nAaCGTN", "17", "depositor-full")
        + _literal("&gt; invalid\nAC-GT", "18", "addgene-partial")
        + '<section id="other"><a href="/browse/sequence/19/">Download</a></section>').encode()


def _body(raw=None, choices=(2, 0, 99), *, complete=True):
    raw = (FIXTURES / "addgene50005.entity").read_bytes() if raw is None else raw
    page = native.read_addgene_sequences(raw, source_ref=SOURCE, requested_id="50005", response_complete=complete)
    records = {row["record_ordinal"]: row for row in page["records"]}
    bindings, missing = [], []
    for ordinal, index in enumerate(choices):
        row = records.get(index)
        sequence = row["sequence"] if row is not None else None
        bindings.append(publication._sequence_row(ordinal, index, None, None,
            publication._artifact_id(sequence) if sequence is not None else None, None,
            row["sequence_status"] if row is not None else "unavailable",
            row["issue_codes"] if row is not None else ["selected_record_unavailable"]))
        if row is None:
            missing.append(publication._error("selected_record_unavailable", index))
    return dict(version="sequence_support_publication_v1",
        request=dict(operation="get_plasmid_sequence", provider="addgene", plasmid_id="50005", max_bytes=4194304),
        selector=dict(view="sequences", record_ordinals=list(choices)), native_source_ref=SOURCE,
        native_artifact_ref=publication._artifact_id(raw), representation="addgene_html", parsed=page,
        reference_bindings=[], extractions=None, sequence_bindings=bindings,
        projection_errors=publication._unique_errors([
            *[publication._error(row["code"], row["record_ordinal"]) for row in page["issues"]], *missing]))


def _forbidden(*args, **kwargs):
    raise AssertionError("frozen Addgene metadata attempted parsing, acquisition, hashing or I/O")


def test_retained_page_and_selected_original_ordinals_keep_authentication_and_null_counts():
    entity = (FIXTURES / "addgene50005.entity").read_bytes()
    metadata = (FIXTURES / "addgene50005.json").read_bytes()
    assert len(entity) == 211547 and hashlib.sha256(entity).hexdigest() == ENTITY_SHA
    assert len(metadata) == 1661 and hashlib.sha256(metadata).hexdigest() == METADATA_SHA
    provenance = json.loads(metadata)
    assert provenance["sha256"] == ENTITY_SHA and provenance["body_complete"] is True
    body = _body(); original = deepcopy(body)
    value = facts.build_addgene_sequence_fact(body)
    assert body == original
    assert value["source_ref"] == SOURCE and value["requested_id"] == "50005"
    assert value["response_complete"] is True and value["parse_status"] == "partial"
    assert value["authentication_required"] is True and value["issues"] == body["parsed"]["issues"]
    rows = value["selected_rows"]
    assert [row["selection_ordinal"] for row in rows] == [0, 1, 2]
    assert [row["record_ordinal"] for row in rows] == [2, 0, 99]
    assert [row["status"] for row in rows] == ["authentication_required", "authentication_required", "unavailable"]
    assert [row["native_record"]["sequence_id"] for row in rows[:2]] == ["91449", "513490"]
    assert [row["native_record"]["source_completeness"] for row in rows[:2]] == ["partial", "full"]
    assert all(row["native_record"]["source_verification"] == "addgene_verified" for row in rows[:2])
    assert rows[2]["native_record"] is None and rows[2]["issue_codes"] == ["selected_record_unavailable"]
    assert all(row["sequence_file_ref"] is row["symbol_count"] is None for row in rows)
    assert all(row["native_record"]["sequence"] is None for row in rows[:2])
    assert "topology" not in value and "score" not in value
    value["selected_rows"][0]["native_record"]["locators"].clear()
    assert len(body["parsed"]["records"][2]["locators"]) == 2


def test_existing_native_row_schema_is_shared_without_altering_the_native_definition():
    before = deepcopy(native.ADDGENE_SEQUENCE_PAGE_SCHEMA)
    node = facts.ADDGENE_SEQUENCE_FACT_SCHEMA["properties"]["selected_rows"]["items"]["properties"]["native_record"]
    expected = deepcopy(native.ADDGENE_SEQUENCE_PAGE_SCHEMA["properties"]["records"]["items"])
    expected["type"] = ["object", "null"]
    assert node == expected and node is not native.ADDGENE_SEQUENCE_PAGE_SCHEMA["properties"]["records"]["items"]
    assert facts.ADDGENE_SEQUENCE_FACTS_SCHEMA["items"] == facts.ADDGENE_SEQUENCE_FACT_SCHEMA
    assert facts.ADDGENE_SEQUENCE_FACTS_SCHEMA["x-source"] == facts.FACT_SOURCE
    assert native.ADDGENE_SEQUENCE_PAGE_SCHEMA == before


def test_inline_native_available_invalid_and_download_required_records_remain_distinct():
    body = _body(_inline(), choices=(2, 0, 1, 99))
    value = facts.build_addgene_sequence_fact(body)
    rows = value["selected_rows"]
    assert [row["status"] for row in rows] == ["download_required", "available", "invalid", "unavailable"]
    assert value["authentication_required"] is False
    assert rows[1]["native_record"]["sequence"] == "AaCGTN"
    assert rows[1]["native_record"]["native_header"] == "> original header  "
    assert rows[1]["native_record"]["native_sequence_text"] == "> original header  \r\nAaCGTN"
    assert rows[1]["native_record"]["source_verification"] == "depositor"
    assert rows[1]["sequence_file_ref"] == "artifact_" + hashlib.sha256(b"AaCGTN").hexdigest()
    assert all(row["symbol_count"] is None for row in rows), "available sequence length was not reported by this publisher"
    assert rows[2]["native_record"]["native_sequence_text"] == "> invalid\nAC-GT"
    assert rows[2]["native_record"]["sequence"] is None and rows[2]["issue_codes"] == ["invalid_literal"]
    assert rows[0]["native_record"]["source_completeness"] == rows[0]["native_record"]["source_verification"] == "unknown"


@pytest.mark.parametrize("raw,complete,status", [(b"\xff", True, "invalid"), (_inline(), False, "partial")])
def test_invalid_representation_and_incomplete_response_keep_specific_metadata(raw, complete, status):
    value = facts.build_addgene_sequence_fact(_body(raw, choices=(0, 99), complete=complete))
    assert value["parse_status"] == status and value["response_complete"] is complete
    if not complete:
        assert dict(code="response_incomplete", record_ordinal=None) in value["issues"]
        assert value["selected_rows"][0]["status"] == "available"
    else:
        assert dict(code="invalid_encoding", record_ordinal=None) in value["issues"]
        assert all(row["native_record"] is None for row in value["selected_rows"])


def test_authentication_banner_does_not_erase_an_actually_supplied_valid_literal():
    raw = ('<div class="anonymous-user-sequence-alert">Log in</div>' + _literal("&gt; literal\nACGT", "17")).encode()
    value = facts.build_addgene_sequence_fact(_body(raw, choices=(0,)))
    assert value["authentication_required"] is True
    assert value["selected_rows"][0]["status"] == "available"
    assert value["selected_rows"][0]["native_record"]["sequence"] == "ACGT"


@pytest.mark.parametrize("fault", ["version", "representation", "provider", "operation", "extra", "source", "parsed_source",
    "requested_id", "artifact", "selection_order", "selection_bool", "selection_float", "selection_duplicate", "binding_count",
    "binding_ordinal", "binding_record", "binding_feature", "binding_reference", "binding_sequence", "binding_status",
    "binding_issues", "symbol_count", "projection_issues", "reference_bindings", "extractions"])
def test_builder_rejects_wrong_publication_and_selected_binding_relationships(fault):
    body = _body()
    if fault == "version": body["version"] = "another_publication"
    elif fault == "representation": body["representation"] = "genbank"
    elif fault == "provider": body["request"]["provider"] = "ncbi"
    elif fault == "operation": body["request"]["operation"] = "ncbi_gene"
    elif fault == "extra": body["findings"] = "not allowed"
    elif fault == "source": body["native_source_ref"] = "source_invalid"
    elif fault == "parsed_source": body["parsed"]["source_ref"] = OTHER_SOURCE
    elif fault == "requested_id": body["parsed"]["requested_id"] = "50006"
    elif fault == "artifact": body["native_artifact_ref"] = "artifact_invalid"
    elif fault == "selection_order": body["selector"]["record_ordinals"].reverse()
    elif fault == "selection_bool": body["selector"]["record_ordinals"][0] = True
    elif fault == "selection_float": body["selector"]["record_ordinals"][0] = 2.0
    elif fault == "selection_duplicate": body["selector"]["record_ordinals"][1] = 2
    elif fault == "binding_count": body["sequence_bindings"].pop()
    elif fault == "binding_ordinal": body["sequence_bindings"][0]["selection_ordinal"] = 1
    elif fault == "binding_record": body["sequence_bindings"][0]["record_ordinal"] = 1
    elif fault == "binding_feature": body["sequence_bindings"][0]["feature_ordinal"] = 0
    elif fault == "binding_reference": body["sequence_bindings"][0]["reference_ref"] = "reference_" + "1" * 24
    elif fault == "binding_sequence": body["sequence_bindings"][0]["sequence_ref"] = "artifact_" + "1" * 64
    elif fault == "binding_status": body["sequence_bindings"][0]["status"] = "available"
    elif fault == "binding_issues": body["sequence_bindings"][0]["issue_codes"] = []
    elif fault == "symbol_count": body["sequence_bindings"][0]["symbol_count"] = 0
    elif fault == "projection_issues": body["projection_errors"] = []
    elif fault == "reference_bindings": body["reference_bindings"] = [dict(record_ordinal=0, reference_ref=OTHER_SOURCE, sequence_ref=None)]
    else: body["extractions"] = {}
    with pytest.raises(ValueError):
        facts.build_addgene_sequence_fact(body)


@pytest.mark.parametrize("fault", ["extra", "row_extra", "native_extra", "version", "source", "requested_id", "complete", "authentication",
    "response", "selection_bool", "selection_float", "selection_gap", "reordered", "record_duplicate", "record_identity", "native_ordinal_bool",
    "sequence_identity", "category", "status", "native_status", "issue_code", "row_issues", "symbol_zero", "file_bool", "file_invented",
    "sequence_invented", "header_invented", "locator_bool", "locator_order", "locator_duplicate", "locator_tag", "missing_with_issue", "issue_bool",
    "unicode", "cycle", "tuple"])
def test_frozen_validator_rejects_forged_types_identities_status_and_nullability(fault):
    value = facts.build_addgene_sequence_fact(_body()); row = value["selected_rows"][0]; record = row["native_record"]
    if fault == "extra": value["confidence"] = 1
    elif fault == "row_extra": row["unit"] = "nucleotide"
    elif fault == "native_extra": record["topology"] = "circular"
    elif fault == "version": value["version"] = "another_fact"
    elif fault == "source": value["source_ref"] = "source_invalid"
    elif fault == "requested_id": value["requested_id"] = 50005
    elif fault == "complete": value["parse_status"] = "complete"
    elif fault == "authentication": value["authentication_required"] = False
    elif fault == "response": value["response_complete"] = False
    elif fault == "selection_bool": row["selection_ordinal"] = False
    elif fault == "selection_float": row["selection_ordinal"] = 0.0
    elif fault == "selection_gap": row["selection_ordinal"] = 1
    elif fault == "reordered": value["selected_rows"].reverse()
    elif fault == "record_duplicate": value["selected_rows"][1]["record_ordinal"] = 2
    elif fault == "record_identity": row["record_ordinal"] = 1
    elif fault == "native_ordinal_bool": record["record_ordinal"] = True
    elif fault == "sequence_identity": record["sequence_id"] = "999"
    elif fault == "category": record["source_completeness"] = "full"
    elif fault == "status": row["status"] = "available"
    elif fault == "native_status": row["status"] = record["sequence_status"] = "download_required"
    elif fault == "issue_code": row["issue_codes"] = ["invented"]
    elif fault == "row_issues": row["issue_codes"] = []
    elif fault == "symbol_zero": row["symbol_count"] = 0
    elif fault == "file_bool": row["sequence_file_ref"] = False
    elif fault == "file_invented": row["sequence_file_ref"] = "artifact_" + "1" * 64
    elif fault == "sequence_invented": record["sequence"] = "ACGT"
    elif fault == "header_invented": record["native_header"] = "> invented"
    elif fault == "locator_bool": record["locators"][0]["source_element_ordinal"] = True
    elif fault == "locator_order": record["locators"].reverse()
    elif fault == "locator_duplicate": record["locators"][1] = deepcopy(record["locators"][0])
    elif fault == "locator_tag": record["locators"][0]["tag"] = "textarea"
    elif fault == "missing_with_issue": value["issues"].append(dict(code="authentication_required", record_ordinal=99))
    elif fault == "issue_bool": value["issues"][1]["record_ordinal"] = True
    elif fault == "unicode": record["section_id"] = "\ud800"
    elif fault == "cycle": row["native_record"] = value
    else: row["issue_codes"] = tuple(row["issue_codes"])
    with pytest.raises(ValueError):
        facts.validate_addgene_sequence_fact(value)


def test_frozen_validation_uses_no_files_parsers_hashes_models_or_publication(monkeypatch):
    values = [facts.build_addgene_sequence_fact(_body()), facts.build_addgene_sequence_fact(_body(_inline(), choices=(2, 0, 1, 99)))]
    for name in ("read_addgene_sequences", "validate_addgene_sequence_page", "_literal"):
        monkeypatch.setattr(native, name, _forbidden)
    for name in ("read_sequence_support_publication", "_shape", "_artifact_id"):
        monkeypatch.setattr(publication, name, _forbidden)
    for owner, name in ((builtins, "open"), (Path, "open"), (socket, "socket"), (socket, "create_connection"),
            (subprocess, "run"), (subprocess, "Popen"), (PublicClients, "_http"), (json, "load"), (json, "loads"), (hashlib, "sha256")):
        monkeypatch.setattr(owner, name, _forbidden)
    for value in values:
        result = facts.validate_addgene_sequence_fact(value)
        assert result == value and result is not value
        assert result["selected_rows"] is not value["selected_rows"]


def test_pure_shape_does_not_claim_to_authenticate_a_different_valid_source_identity():
    value = facts.build_addgene_sequence_fact(_body())
    value["source_ref"] = OTHER_SOURCE
    assert facts.validate_addgene_sequence_fact(value)["source_ref"] == OTHER_SOURCE
    # The host must compare the original authenticated/frozen facts separately.


def test_inline_binding_file_identity_is_checked_without_inventing_a_count():
    body = _body(_inline(), choices=(0,))
    body["sequence_bindings"][0]["sequence_ref"] = "artifact_" + "0" * 64
    with pytest.raises(ValueError, match="publication_binding"):
        facts.build_addgene_sequence_fact(body)


def _communication_schema():
    return dict(type="object", properties={"facts": deepcopy(facts.ADDGENE_SEQUENCE_FACTS_SCHEMA)},
        required=["facts"], additionalProperties=False)


@pytest.mark.parametrize("inline", [False, True])
def test_registered_addgene_array_has_exact_closed_form_and_semantic_references(inline):
    """Controlled format/reference checks; no episode custody is asserted."""
    from gene_annotation_episode.communication import validate_closed_schema, validate_form

    body = _body(_inline(), choices=(2, 0, 1, 99)) if inline else _body()
    value = facts.build_addgene_sequence_fact(body)
    schema, calls = _communication_schema(), []
    known = {(SOURCE, "source"), *((row["sequence_file_ref"], "artifact")
        for row in value["selected_rows"] if row["sequence_file_ref"] is not None)}

    def resolve(reference, namespace):
        calls.append((reference, namespace))
        return (reference, namespace) in known

    assert validate_closed_schema(schema) == schema
    assert validate_form({"facts": [value]}, schema, resolve) == {"facts": [value]}
    assert set(calls) == known
    calls.clear()
    assert validate_form({"facts": []}, schema, resolve) == {"facts": []}
    assert calls == []


@pytest.mark.parametrize("defect", ["native_optional", "ordinal_float", "free_extra", "nested"])
def test_registered_addgene_array_schema_cannot_be_redefined_or_nested(defect):
    from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema

    schema = _communication_schema()
    selected = schema["properties"]["facts"]["items"]["properties"]["selected_rows"]["items"]
    if defect == "native_optional":
        selected["properties"]["native_record"]["required"].remove("sequence_id")
    elif defect == "ordinal_float":
        selected["properties"]["selection_ordinal"]["minimum"] = 0.0
    elif defect == "free_extra":
        selected["properties"]["instructions"] = {"type": "string"}
    else:
        schema = dict(type="object", properties={"nested": schema}, required=["nested"], additionalProperties=False)
    with pytest.raises(ReportBoundaryError) as rejected:
        validate_closed_schema(schema)
    assert rejected.value.diagnostic["code"] == "invalid_schema"


@pytest.mark.parametrize("defect,code", [
    ("boolean_ordinal", "addgene_sequence_fact_schema_invalid"),
    ("float_ordinal", "addgene_sequence_fact_schema_invalid"),
    ("invented_bases", "addgene_sequence_fact_sequence_relationship"),
    ("invented_count", "addgene_sequence_fact_schema_invalid"),
])
def test_registered_addgene_array_rejects_bad_dto_before_reference_checks(defect, code):
    from gene_annotation_episode.communication import ReportBoundaryError, validate_form

    value, calls = facts.build_addgene_sequence_fact(_body()), []
    row = value["selected_rows"][0]
    if defect == "boolean_ordinal": row["selection_ordinal"] = False
    elif defect == "float_ordinal": row["selection_ordinal"] = 0.0
    elif defect == "invented_bases": row["native_record"]["sequence"] = "ACGT"
    else: row["symbol_count"] = 0

    def resolve(reference, namespace):
        calls.append((reference, namespace))
        return True

    with pytest.raises(ReportBoundaryError) as rejected:
        validate_form({"facts": [value]}, _communication_schema(), resolve)
    assert rejected.value.diagnostic["code"] == code
    assert rejected.value.diagnostic["field"] == "facts"
    assert calls == []


@pytest.mark.parametrize("denied_namespace", ["source", "artifact"])
def test_registered_addgene_array_checks_source_and_selected_sequence_file_permissions(denied_namespace):
    from gene_annotation_episode.communication import ReportBoundaryError, validate_form

    value = facts.build_addgene_sequence_fact(_body(_inline(), choices=(0,)))
    denied = (SOURCE, "source") if denied_namespace == "source" else (
        value["selected_rows"][0]["sequence_file_ref"], "artifact")
    calls = []

    def resolve(reference, namespace):
        calls.append((reference, namespace))
        return (reference, namespace) != denied

    with pytest.raises(ReportBoundaryError) as rejected:
        validate_form({"facts": [value]}, _communication_schema(), resolve)
    assert rejected.value.diagnostic["code"] == "unknown_reference"
    assert denied in calls
