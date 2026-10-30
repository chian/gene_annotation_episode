"""Partial-role controls plus actual Store/EPR input-boundary engineering cases.

The labelled format records establish no custody. The shared real input-owner
fixture authenticates current receipts/bytes under engineered commissions; no
configured scientific service, frozen historical alias or native work is claimed.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.calibrated_signal_contracts import CalibratedSignalContractError
from gene_annotation_episode.calibrated_signal_sheet import (populate_calibrated_signal_sheet,
    read_calibrated_signal_inputs, validate_calibrated_signal_input_read)
from gene_annotation_episode.molecular_sequence_input_contracts import (RECEIVED_INPUT_VERSION,
    decode_molecular_sequence_input, input_record_digest, molecular_sequence_input_failure,
    unread_molecular_sequence_input_content, validate_molecular_sequence_received_input)
from test_calibrated_signal_measurements import supplied_inputs
from test_molecular_sequence_input_bindings import actual_received_input_owner


def sheet():
    return populate_calibrated_signal_sheet(**supplied_inputs())


def engineering_received(*, document=None, raw=None, namespace="artifact", byte_state="verified"):
    """A pure format fixture, intentionally not an authenticated host callback."""
    if raw is None:
        raw = json.dumps(sheet() if document is None else document, allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
    artifact = {"id": "artifact_" + digest, "record_type": "artifact", "sha256": digest,
        "size": len(raw), "media_type": "application/json"}
    record = artifact if namespace == "artifact" else {
        "id": "source_engineering_format_only", "record_type": "source", "artifact_ref": artifact["id"],
        "revision": 1, "version": "supplied-format-example", "origin": "tool"}
    issue = None
    if byte_state != "verified":
        issue = molecular_sequence_input_failure("artifact_bytes_unavailable" if byte_state == "unavailable" else "artifact_identity_conflict")
        content = unread_molecular_sequence_input_content(issue)
    else:
        content = decode_molecular_sequence_input(raw, tag_key="version")
        issue = content["failure"]
    value = {"version": RECEIVED_INPUT_VERSION, "selection": {"reference": record["id"], "namespace": namespace},
        "input": {"receiver": {"run_id": "engineering-format-only", "episode_id": "engineering-format-only",
            "request_sha256": "1" * 64, "assignment_sha256": "2" * 64},
            "scope": {}, "inheritance_manifest": {}, "witness": {"reference": record["id"], "namespace": namespace,
                "record": deepcopy(record), "record_sha256": input_record_digest(record),
                "record_revision": record.get("revision"), "source_version": record.get("version")},
            "file": {"artifact_ref": artifact["id"], "sha256": digest, "size_bytes": len(raw), "format": "json"},
            "artifact_record": artifact, "tag_key": "version", "byte_verification": byte_state, "content": content},
        "failure": issue}
    return validate_molecular_sequence_received_input(value)


def read_format(value):
    selected = value["selection"]
    return read_calibrated_signal_inputs(selected["reference"], namespace=selected["namespace"],
        read_input=lambda reference, namespace: deepcopy(value))


def test_whole_supplied_sheet_keeps_all_values_and_original_file_evidence():
    received = engineering_received()
    before = deepcopy(received)
    result = read_format(received)
    assert result["state"] == "complete" and result["failures"] == []
    assert result["sheet"] == sheet()
    assert result["received_input"] == before == received
    assert {name: role["value"] for name, role in result["roles"].items()} == {
        name: before["input"]["content"]["value"][name] for name in result["roles"]}
    assert all(role["state"] == "present" for role in result["roles"].values())
    assert validate_calibrated_signal_input_read(result) == result


@pytest.mark.parametrize("kind", ["missing", "null", "wrong", "numeric"])
def test_wrong_tag_preserves_valid_role_evidence_without_manufacturing_sheet(kind):
    document = sheet()
    if kind == "missing": del document["version"]
    elif kind == "null": document["version"] = None
    elif kind == "wrong": document["version"] = "different-scientific-document"
    else: document["version"] = 1
    received = engineering_received(document=document)
    result = read_format(received)
    assert result["state"] == "partial" and result["sheet"] is None
    assert all(role["state"] == "present" for role in result["roles"].values())
    assert result["roles"]["calibrations"]["value"] == document["calibrations"]
    assert "document_tag_conflict" in {issue["code"] for issue in result["failures"]}
    assert result["received_input"]["input"]["file"] == received["input"]["file"]


@pytest.mark.parametrize("role", ["samples", "species", "calibrations", "association"])
@pytest.mark.parametrize("kind,state", [("missing", "missing"), ("null", "invalid"), ("invalid", "invalid")])
def test_one_invalid_role_keeps_the_other_decoded_roles_and_admitted_source(role, kind, state):
    document = sheet()
    if kind == "missing": del document[role]
    elif kind == "null": document[role] = None
    else: document[role] = {"not": "the selected role shape"} if role != "association" else {}
    received = engineering_received(document=document)
    result = read_format(received)
    assert result["state"] == "partial" and result["sheet"] is None
    assert result["roles"][role]["state"] == state and result["roles"][role]["value"] is None
    assert result["roles"][role]["source_pointer"] == "/" + role
    for name, item in result["roles"].items():
        if name != role:
            assert item["state"] == "present" and item["value"] == document[name]
    assert result["received_input"] == received


@pytest.mark.parametrize("role", ["samples", "species", "calibrations"])
def test_explicit_empty_population_is_kept_separately_from_missing_or_invalid(role):
    document = sheet()
    document[role] = []
    result = read_format(engineering_received(document=document))
    assert result["roles"][role]["state"] == "empty"
    assert result["roles"][role]["value"] == []
    if role in {"samples", "calibrations"}:
        assert result["state"] == "complete" and result["sheet"][role] == []
    else:
        assert result["state"] == "partial" and result["sheet"] is None


@pytest.mark.parametrize("mutation,code", [("sample", "duplicate_identity"), ("point", "duplicate_identity"),
    ("reference", "unknown_analysis_species_identity"), ("calibration", "unknown_species_identity"),
    ("representation", "representation_signal_kind_conflict")])
def test_cross_identity_errors_keep_closed_role_values_and_original_bytes(mutation, code):
    document = sheet()
    if mutation == "sample": document["samples"].append(deepcopy(document["samples"][0]))
    elif mutation == "point": document["samples"][0]["measurements"] *= 2
    elif mutation == "reference": document["association"]["analysis_species_ids"] = ["not-supplied"]
    elif mutation == "calibration": document["calibrations"][0]["species_id"] = "not-supplied"
    else: document["samples"][0]["signal_kind"] = "peak_height"
    received = engineering_received(document=document)
    result = read_format(received)
    assert result["state"] == "partial" and result["sheet"] is None
    assert all(role["state"] == "present" for role in result["roles"].values())
    assert result["roles"]["samples"]["value"] == document["samples"]
    assert result["received_input"] == received
    assert any(issue["code"] == "cross_role_conflict" and issue["contract_code"] == code for issue in result["failures"])


@pytest.mark.parametrize("raw", [b"null", b"[]", b'"not-a-sheet"'])
def test_decoded_nonobject_is_not_confused_with_missing_bytes_or_fake_empty_roles(raw):
    received = engineering_received(raw=raw)
    assert received["input"]["content"]["state"] == "decoded"
    result = read_format(received)
    assert result["state"] == "unavailable" and result["sheet"] is None
    assert result["received_input"] == received
    assert all(role["state"] == "unavailable" and role["value"] is None for role in result["roles"].values())


@pytest.mark.parametrize("raw,code", [(b"\xff", "invalid_utf8"), (b'{"x":1,"x":2}', "duplicate_json_key"),
    (b'{"x":NaN}', "nonfinite_json"), (b'{"x":1e999}', "nonfinite_json"),
    (b'{"x":1e-999}', "unrepresentable_json_number"), (b"{", "invalid_json")])
def test_decode_failure_retains_verified_file_evidence_without_inventing_role_values(raw, code):
    received = engineering_received(raw=raw)
    result = read_format(received)
    assert result["state"] == "unavailable" and result["sheet"] is None
    assert result["received_input"]["input"]["byte_verification"] == "verified"
    assert result["received_input"]["input"]["file"] == received["input"]["file"]
    assert result["failures"] == [{"code": "decode_failed", "role": None, "source_pointer": "",
        "contract_code": None, "common_failure": {"stage": "decode", "code": code}}]
    assert all(role["value"] is None for role in result["roles"].values())


@pytest.mark.parametrize("byte_state", ["unavailable", "identity_conflict"])
def test_unverified_bytes_keep_only_the_admitted_metadata_and_are_not_decoded(byte_state):
    received = engineering_received(byte_state=byte_state)
    result = read_format(received)
    assert result["received_input"] == received
    assert result["received_input"]["input"]["content"]["state"] == "not_read"
    assert result["state"] == "unavailable" and result["sheet"] is None
    assert result["failures"][0]["code"] == "input_unavailable"


@pytest.mark.parametrize("code", ["reference_not_received", "reference_denied", "invalid_commission"])
def test_common_denial_has_no_private_witness_or_file_metadata_to_promote(code):
    received = {"version": RECEIVED_INPUT_VERSION, "selection": {"reference": "requested-reference", "namespace": "artifact"},
        "input": None, "failure": molecular_sequence_input_failure(code)}
    result = read_format(received)
    assert result["received_input"]["input"] is None
    assert result["state"] == "unavailable" and result["sheet"] is None
    assert all(role["value"] is None for role in result["roles"].values())
    assert result["failures"][0]["common_failure"] == received["failure"]


def test_supplied_provenance_assertions_are_copied_and_never_resolved_as_grants():
    document = sheet()
    document["samples"][0]["source"] = {"source_ref": "unreceived-citation-assertion", "pointer": "/claimed"}
    received = engineering_received(document=document, namespace="source")
    calls = []
    def callback(reference, namespace):
        calls.append((reference, namespace))
        return deepcopy(received)
    result = read_calibrated_signal_inputs(received["selection"]["reference"], namespace="source", read_input=callback)
    assert calls == [(received["selection"]["reference"], "source")]
    assert result["sheet"]["samples"][0]["source"] == document["samples"][0]["source"]
    assert result["received_input"]["input"]["witness"] == received["input"]["witness"]


def test_callback_cannot_substitute_a_different_selected_input():
    original = engineering_received()
    changed = sheet(); changed["samples"][0]["sample_id"] = "different-supplied-sample"
    other = engineering_received(document=changed)
    with pytest.raises(CalibratedSignalContractError, match="calibrated_signal_input_selection_conflict"):
        read_calibrated_signal_inputs(original["selection"]["reference"], namespace="artifact",
            read_input=lambda *_: other)


@pytest.mark.parametrize("reference,namespace", [("", "artifact"), (False, "artifact"), ("ref", "subject")])
def test_invalid_selection_does_not_call_the_input_owner(reference, namespace):
    def forbidden(*args): raise AssertionError("invalid selection reached input owner")
    with pytest.raises(CalibratedSignalContractError, match="calibrated_signal_input_selection_invalid"):
        read_calibrated_signal_inputs(reference, namespace=namespace, read_input=forbidden)


def test_saved_format_interpretation_needs_no_store_native_file_or_network_access(monkeypatch):
    received = engineering_received()
    expected = read_format(received)
    def forbidden(*args, **kwargs): raise AssertionError("format interpretation attempted external work")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert read_format(received) == expected
    assert validate_calibrated_signal_input_read(expected) == expected


@pytest.mark.parametrize("mutation", ["role", "sheet", "failure"])
def test_interpretation_validator_rejects_changed_derived_state(mutation):
    result = read_format(engineering_received())
    if mutation == "role": result["roles"]["samples"]["state"] = "empty"
    elif mutation == "sheet": result["sheet"]["samples"][0]["sample_id"] = "forged"
    else: result["failures"] = [{"code": "document_shape_invalid", "role": None, "source_pointer": "",
        "contract_code": None, "common_failure": None}]
    with pytest.raises(CalibratedSignalContractError, match="calibrated_signal_input_interpretation_conflict"):
        validate_calibrated_signal_input_read(result)


def actual_read(value, *, context=None):
    receiving = value.context if context is None else context
    return read_calibrated_signal_inputs(value.reference, namespace=value.namespace,
        read_input=lambda reference, namespace: value.binding.read_received(
            receiving, reference, namespace, tag_key="version"))


def database_rows(store):
    tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple(row) for row in store.db.execute(
        'SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in tables}


@pytest.mark.parametrize("namespace", ["artifact", "source"])
def test_actual_receiving_callback_preserves_file_current_source_version_and_all_database_rows(tmp_path, namespace):
    document = sheet()
    document["samples"][0]["source"] = {"source_ref": "unreceived-source-assertion", "pointer": "/reported"}
    raw = json.dumps(document, allow_nan=False).encode()
    with actual_received_input_owner(tmp_path, raw=raw, namespace=namespace) as value:
        before = database_rows(value.store)
        known = set(value.receipts.known(value.context.episode_id))
        changes = value.store.db.total_changes
        result = actual_read(value)
        item = result["received_input"]["input"]
        assert result["state"] == "complete" and result["sheet"] == document
        assert item["receiver"]["episode_id"] == value.context.episode_id
        assert item["file"]["artifact_ref"] == value.artifact_ref
        assert item["file"]["sha256"] == hashlib.sha256(raw).hexdigest() and item["file"]["size_bytes"] == len(raw)
        assert item["witness"]["record"] == value.store.get(value.reference)
        assert item["witness"]["source_version"] == ("declared_source_version" if namespace == "source" else None)
        assert item["content"]["document_version"] == document["version"]
        assert item["content"]["value"] == document
        assert value.store.get_artifact(item["file"]["artifact_ref"]) == raw
        assert value.text_ref != item["file"]["artifact_ref"]
        assert all(ref != "unreceived-source-assertion" for ref, _ in value.verdicts)
        assert known == set(value.receipts.known(value.context.episode_id))
        assert changes == value.store.db.total_changes and before == database_rows(value.store)


def test_actual_admitted_file_keeps_valid_roles_when_supplied_calibration_is_null(tmp_path):
    document = sheet(); document["calibrations"] = None
    raw = json.dumps(document, allow_nan=False).encode()
    with actual_received_input_owner(tmp_path, raw=raw, namespace="source") as value:
        result = actual_read(value)
        assert result["state"] == "partial" and result["sheet"] is None
        assert result["roles"]["calibrations"]["state"] == "invalid"
        assert result["roles"]["calibrations"]["value"] is None
        for name in ("samples", "species", "association"):
            assert result["roles"][name]["state"] == "present" and result["roles"][name]["value"] == document[name]
        assert result["received_input"]["input"]["file"]["artifact_ref"] == value.artifact_ref
        assert value.store.get_artifact(value.artifact_ref) == raw


@pytest.mark.parametrize("kind,code", [("unreceived", "reference_not_received"),
    ("protected_dependency", "artifact_not_received"), ("protected_owner", "artifact_denied")])
def test_actual_owner_and_dependency_denials_never_become_input_or_source_grants(tmp_path, kind, code):
    with actual_received_input_owner(tmp_path, raw=json.dumps(sheet()).encode(), namespace="source",
            deliver=kind != "unreceived", protected=kind != "unreceived", grant_artifact=kind == "protected_owner") as value:
        if kind == "protected_owner": value.denied.add((value.artifact_ref, "artifact"))
        before = database_rows(value.store)
        known = set(value.receipts.known(value.context.episode_id))
        result = actual_read(value)
        assert result["state"] == "unavailable" and result["sheet"] is None
        assert result["received_input"]["input"] is None
        assert result["failures"][0]["common_failure"]["code"] == code
        assert all(role["state"] == "unavailable" and role["value"] is None for role in result["roles"].values())
        assert before == database_rows(value.store) and known == set(value.receipts.known(value.context.episode_id))


def test_actual_receipt_prefix_stays_fixed_when_parent_later_receives_input(tmp_path):
    with actual_received_input_owner(tmp_path, raw=json.dumps(sheet()).encode(), deliver=False) as value:
        value.receipts.receive(value.parent.episode_id, [value.reference], kind="initial")
        original = actual_read(value)
        assert original["state"] == "unavailable" and original["received_input"]["input"] is None
        assert original["failures"][0]["common_failure"]["code"] == "reference_not_received"
        later_context = value.child(1)
        later = actual_read(value, context=later_context)
        assert later["state"] == "complete" and later["received_input"]["input"]["receiver"]["episode_id"] == later_context.episode_id
        assert actual_read(value) == original


@pytest.mark.parametrize("kind,code", [("missing", "artifact_bytes_unavailable"), ("changed", "artifact_identity_conflict")])
def test_actual_artifact_read_failure_preserves_admitted_metadata_and_no_decoded_roles(tmp_path, kind, code):
    with actual_received_input_owner(tmp_path, raw=json.dumps(sheet()).encode(), namespace="source") as value:
        metadata = value.store.get(value.artifact_ref)
        artifact = value.store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
        if kind == "missing": artifact.unlink()
        else: artifact.write_bytes(b'{"unselected_replacement":true}')
        result = actual_read(value)
        item = result["received_input"]["input"]
        assert result["state"] == "unavailable" and result["sheet"] is None
        assert item["artifact_record"] == metadata and item["witness"]["reference"] == value.source_ref
        assert item["content"]["state"] == "not_read" and item["content"]["value"] is None
        assert result["failures"][0]["common_failure"]["code"] == code
        assert all(role["value"] is None for role in result["roles"].values())


def test_actual_verified_lone_surrogate_input_is_a_typed_decode_failure_with_file_evidence(tmp_path):
    raw = b'{"version":"calibrated_signal_sheet_v1","calibrations":["\\ud800"]}'
    with actual_received_input_owner(tmp_path, raw=raw) as value:
        result = actual_read(value)
        item = result["received_input"]["input"]
        assert result["state"] == "unavailable" and result["sheet"] is None
        assert item["byte_verification"] == "verified" and item["content"]["state"] == "decode_failed"
        assert item["file"]["artifact_ref"] == value.artifact_ref
        assert result["failures"][0]["common_failure"] == {"stage": "decode", "code": "invalid_json"}
