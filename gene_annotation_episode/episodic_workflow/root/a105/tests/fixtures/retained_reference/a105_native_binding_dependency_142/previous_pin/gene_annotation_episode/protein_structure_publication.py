"""Ordinary source and sequence publication for retained protein results.

Payload construction is pure; publication validates retained original bytes.
The result host separately authenticates capture and worker custody. A source's
auxiliary list preserves original files and grants no receiving episode access.
"""
from __future__ import annotations

from .domain import ContractError, RECORD_SCHEMAS, identity, validate_schema
from .execution_contracts import canonical, digest
from .native_protein_structure_acquisition import (
    ProteinStructureCapture, retained_protein_structure_file,
)
from .native_protein_structure_contracts import NativeProteinBundle, validate_protein_structure_bundle
from .protein_structure_contracts import (
    FileIdentity, ReferenceRef, SourceRef, StructureSequence,
    validate_file_identity, validate_structure_sequence,
)
from .protein_structure_result_worker import (
    ProteinResultWorkerResult, validate_protein_structure_result_worker_result,
)


def protein_structure_source_payload(*, bundle: NativeProteinBundle,
        capture: ProteinStructureCapture,
        worker_result: ProteinResultWorkerResult | None) -> dict:
    """Build the single approved immutable payload from qualified actual files.

This checks the supplied metadata relationship. It does not acquire bytes or
establish original episode authority. Saved recalculation must use the original
source, rather than pass its later worker output to this function.
    """
    if capture["bundle_validated"] is not True or capture["original_plan"] is None or capture["bundle_file"] is None:
        raise ValueError("capture_incomplete")
    original = validate_protein_structure_bundle(bundle, plan=capture["original_plan"])
    bundle_file = validate_file_identity(capture["bundle_file"])
    if (bundle_file["format"] != "native_protein_structure_bundle_v1"
            or bundle_file["sha256"] != digest(original)
            or bundle_file["byte_length"] != len(canonical(original).encode("utf-8"))):
        raise ValueError("input_digest_mismatch")
    references = []
    for row in capture["files"]:
        if row["observed"] is not None:
            references.append(validate_file_identity(row["observed"])["artifact_ref"])
    if worker_result is not None:
        result = validate_protein_structure_result_worker_result(worker_result)
        operation = original["requested_job"]["native_protein_structure"]["request"]["operation"]
        if result["mode"] != "original_native_result" or result["operation"] != operation:
            raise ValueError("original_commission_mismatch")
        for name in ("native_result_file", "sheet_file", "components_file"):
            if result[name] is not None:
                references.append(result[name]["file_identity"]["artifact_ref"])
    return {"provider": "episode.execution_result",
        "accession": "native_protein_structure_" + digest(original["identity"]),
        "uri": None, "artifact_ref": bundle_file["artifact_ref"], "text_ref": None,
        "request_ref": None, "version": "native_protein_structure_bundle_v1",
        "retrieved_at": original["finished_at"],
        "auxiliary_artifact_refs": list(dict.fromkeys(references))}


def _ordinary_record(store, reference, kind):
    """Validate the existing domain identity without creating a new namespace."""
    if type(reference) is not str:
        raise ValueError("invalid_schema")
    try:
        record = store.get(reference)
    except ContractError as error:
        raise ValueError("conflicting_identity") from error
    except (ValueError, TypeError) as error:
        raise ValueError("invalid_schema") from error
    if (type(record) is not dict or record.get("id") != reference
            or record.get("record_type") != kind or record.get("origin") != "tool"):
        raise ValueError("conflicting_identity")
    payload = {key: value for key, value in record.items()
        if key not in {"id", "record_type", "origin"}}
    try:
        expected = identity(kind, {"origin": record["origin"], "record": payload})
    except (ValueError, TypeError) as error:
        raise ValueError("invalid_schema") from error
    if reference != expected:
        raise ValueError("conflicting_identity")
    try:
        validate_schema(payload, RECORD_SCHEMAS[kind])
    except ContractError as error:
        raise ValueError("invalid_schema") from error
    return record


def _put_original(store, kind, payload):
    """Store.put remains the publisher; check its INSERT OR IGNORE replay too."""
    expected_ref = identity(kind, {"origin": "tool", "record": payload})
    expected = {**payload, "id": expected_ref, "record_type": kind, "origin": "tool"}
    with store.transaction():
        try:
            store.get(expected_ref)
        except ContractError as error:
            if str(error) != "unknown_reference":
                raise ValueError("conflicting_identity") from error
        else:
            if canonical(_ordinary_record(store, expected_ref, kind)) != canonical(expected):
                raise ValueError("conflicting_identity")
        try:
            published = store.put(kind, payload, origin="tool")
        except ContractError as error:
            raise ValueError("invalid_schema") from error
        actual = _ordinary_record(store, expected_ref, kind)
        if canonical(published) != canonical(expected) or canonical(actual) != canonical(expected):
            raise ValueError("conflicting_identity")
        return actual["id"]


def _retained_bytes(store, file):
    path = retained_protein_structure_file(store, file)
    try:
        return path.read_bytes()
    except OSError as error:
        raise ValueError("retained_artifact_missing") from error


def publish_protein_structure_source(store, *, bundle: NativeProteinBundle,
        capture: ProteinStructureCapture,
        worker_result: ProteinResultWorkerResult | None) -> SourceRef:
    """Publish original retained provenance after host custody authentication.

    Diagnostic capture identities stay diagnostic. Publication grants no use of
    their bytes and cannot replace the original source with saved recalculation.
    """
    try:
        payload = protein_structure_source_payload(
            bundle=bundle, capture=capture, worker_result=worker_result)
        if _retained_bytes(store, capture["bundle_file"]) != canonical(bundle).encode("utf-8"):
            raise ValueError("input_digest_mismatch")
        if len(capture["files"]) != len(bundle["files"]):
            raise ValueError("original_commission_mismatch")
        for index, row in enumerate(capture["files"]):
            if (type(row["manifest_index_0based"]) is not int
                    or row["manifest_index_0based"] != index
                    or canonical(row["declared"]) != canonical(bundle["files"][index])):
                raise ValueError("original_commission_mismatch")
            if row["observed"] is not None:
                if row["observed"]["format"] != row["declared"]["format"]:
                    raise ValueError("unsupported_format")
                retained_protein_structure_file(store, row["observed"])
        if worker_result is not None:
            for name in ("native_result_file", "sheet_file", "components_file"):
                if worker_result[name] is not None:
                    retained_protein_structure_file(store, worker_result[name]["file_identity"])
    except (KeyError, TypeError, IndexError, UnicodeError) as error:
        raise ValueError("invalid_schema") from error
    except ValueError as error:
        if str(error) == "capture_incomplete":
            raise ValueError("original_commission_mismatch") from error
        raise
    return _put_original(store, "source", payload)


def publish_structure_sequence_reference(store, *, source_ref: SourceRef,
        sequence: StructureSequence, sequence_file: FileIdentity,
        residue_map_file: FileIdentity) -> ReferenceRef:
    """Publish one supplied original sequence and its complete retained map.

    The caller authenticates the original extraction. This checks publication
    relationships and exact bytes without parsing or reconstructing a structure.
    """
    sequence = validate_structure_sequence(sequence)
    sequence_file = validate_file_identity(sequence_file)
    residue_map_file = validate_file_identity(residue_map_file)
    if (sequence_file["format"] != "ascii_protein_sequence_v1"
            or residue_map_file["format"] != "protein_structure_sequence_v1"):
        raise ValueError("unsupported_format")
    if not sequence["sequence_available"] or not sequence["alignment_sequence"]:
        raise ValueError("sequence_artifact_mismatch")
    try:
        sequence_bytes = sequence["alignment_sequence"].encode("ascii")
    except UnicodeError as error:
        raise ValueError("sequence_artifact_mismatch") from error
    if sequence_bytes != sequence_bytes.upper():
        raise ValueError("sequence_artifact_mismatch")
    if (_retained_bytes(store, sequence_file) != sequence_bytes
            or _retained_bytes(store, residue_map_file) != canonical(sequence).encode("utf-8")):
        raise ValueError("sequence_artifact_mismatch")
    with store.transaction():
        source = _ordinary_record(store, source_ref, "source")
        if (source["provider"] != "episode.execution_result"
                or source["version"] != "native_protein_structure_bundle_v1"):
            raise ValueError("original_commission_mismatch")
        if any(file["artifact_ref"] not in source.get("auxiliary_artifact_refs", [])
                for file in (sequence_file, residue_map_file)):
            raise ValueError("original_commission_mismatch")
        return _put_original(store, "reference", {
            "reference_type": "protein", "source_ref": source_ref,
            "accession": "structure_sequence_" + digest(sequence),
            "label": "Structure-derived protein sequence",
            "sequence_ref": sequence_file["artifact_ref"], "molecule": "protein",
            "length": sequence["sequence_length"], "term_refs": [],
            "context_refs": [], "anchor": None,
        })
