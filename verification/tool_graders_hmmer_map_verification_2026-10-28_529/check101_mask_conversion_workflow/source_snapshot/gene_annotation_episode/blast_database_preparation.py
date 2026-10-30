"""Pure makeblastdb artifact population and existing prepared-manifest projection.

This supporting operation produces no scientific score. All file facts are
supplied occurrences from the original attempt: this module never opens a path,
enumerates a directory, launches a command, or invents a native measurement.
"""
from __future__ import annotations

from pathlib import PurePosixPath
import re

from .blast_utility_contracts import (
    SCHEMAS,
    validate_blast_utility_operation,
    validate_blast_utility_record,
)
from .domain import ContractError
from .native_blast_standard_database_contracts import (
    FILE_IDENTITY_SCHEMA,
    _absolute,
    _copy,
    _schema,
    validate_standard_prepared_blast_database_manifest,
)


_DETAIL_FIELDS = (
    "input_type", "database_format_version", "parse_seqids", "hash_index",
    "taxid", "taxid_map_occurrence_id", "mask_occurrence_ids",
)
_DATABASE_ROLES = frozenset({"database_file", "database_metadata"})


def _fail(code):
    raise ContractError("blast_utility_" + code)


def _failure(code, *, stage="validation", occurrence_id=None, native_returncode=None):
    return {"stage": stage, "code": code, "occurrence_id": occurrence_id,
            "record_key": None, "line_number": None,
            "native_returncode": native_returncode}


def _check(name, status, *, subject_refs, method, reason=None, occurrences=()):
    return {"name": name, "status": status, "subject_refs": list(subject_refs),
            "method": method, "reason": reason,
            "evidence_occurrence_ids": list(occurrences)}


def _native_file_path(value, occurrence):
    """Resolve a native filename only against its own supplied source location."""
    if (not value or any(c in value for c in ("\0", "\n", "\r"))
            or ".." in value.split("/") or str(PurePosixPath(value)) != value):
        return None
    if value.startswith("/"):
        return value if not value.startswith("//") else None
    source = None if occurrence is None else occurrence["native_path"]
    if source is None:
        return None
    return str(PurePosixPath(source).parent / value)


def _preparation_observations(record):
    """Derive only custody/execution/family facts, never native integrity."""
    checks, failures = [], []
    outcome, key = record["original_outcome"], record["database_key"]
    occurrences = {r["occurrence_id"]: r for r in record["inputs"] + record["outputs"]}
    database_outputs = [r for r in record["outputs"] if r["role"] in _DATABASE_ROLES]
    evidence = [r["occurrence_id"] for r in database_outputs]
    streams = [r["occurrence_id"] for r in record["outputs"]
               if r["role"] in {"stdout", "stderr", "diagnostics"}]

    if outcome["state"] == "succeeded":
        checks.append(_check("native_execution", "pass", subject_refs=[key],
                             method="native_execution_outcome", occurrences=streams))
    else:
        code = ("native_start_failed" if not outcome["started"] and outcome["state"] == "failed" else
                "native_nonzero_exit" if outcome["returncode"] not in (None, 0) else
                "preparation_not_successful")
        failures.append(_failure(code, stage="native", native_returncode=outcome["returncode"]))
        checks.append(_check("native_execution", "fail" if outcome["state"] == "failed" else "unknown",
                             subject_refs=[key], method="native_execution_outcome",
                             reason=code, occurrences=streams))

    inventory_reasons = []
    if not record["inventory_complete"]:
        inventory_reasons.append("output_inventory_incomplete")
    if not database_outputs:
        inventory_reasons.append("output_missing")
    if any(r["completeness"] != "complete" for r in database_outputs):
        inventory_reasons.append("output_family_incomplete")
    paths = {r["native_path"]: r for r in database_outputs if r["native_path"] is not None}
    if any(r["native_path"] is None for r in database_outputs):
        inventory_reasons.append("record_association_unresolved")

    # These are necessary native family members, never proof of complete capture.
    # Completeness above comes only from the original producer's closed inventory.
    letter = "n" if record["operation"]["molecule"] == "dna" else "p"
    opposite = "p" if letter == "n" else "n"
    for prefix in record["native_paths"]:
        family = [path for path in paths if path.startswith(prefix + ".")]
        if not family:
            inventory_reasons.append("output_family_incomplete")
            continue
        if any(re.fullmatch(re.escape(prefix) + r"(?:\.\d+)?\." + opposite + r"(?:hr|in|sq)", path)
               for path in family):
            inventory_reasons.append("database_kind_conflict")
        stems = set()
        for path in family:
            match = re.fullmatch("(" + re.escape(prefix) + r"(?:\.\d+)?)\." + letter + r"(?:hr|in|sq)", path)
            if match:
                stems.add(match[1])
        if not stems or any(not all(stem + "." + letter + ext in paths for ext in ("hr", "in", "sq"))
                            for stem in stems):
            inventory_reasons.append("output_family_incomplete")
        if record["detail"]["database_format_version"] == 5 and prefix + "." + letter + "db" not in paths:
            inventory_reasons.append("output_family_incomplete")

    # Native metadata lists are assertions from their particular retained source,
    # not a glob or an independently sorted join. Every listed file must exist in
    # the supplied family; additional captured files are always retained.
    metadata_reasons = []
    known = {}
    metadata_evidence = []
    for field in record["native_metadata"]:
        if field["occurrence_id"] not in metadata_evidence:
            metadata_evidence.append(field["occurrence_id"])
        if field["value"] is None:
            if field["missing_reason"] == "native_field_invalid":
                metadata_reasons.append("native_document_invalid")
            continue
        name, value = field["field_name"], field["value"]
        if field["value_basis"] != "native_reported_approximate":
            identity = name, field["unit"]
            if identity in known and known[identity] != value:
                metadata_reasons.append("database_metadata_conflict")
            known[identity] = value
        if name == "database_format_version" and value != record["detail"]["database_format_version"]:
            metadata_reasons.append("database_metadata_conflict")
        if name == "database_title" and value != record["operation"]["parameters"]["title"]:
            metadata_reasons.append("database_metadata_conflict")
        if name == "database_residue_count" and field["unit"] not in {
                "symbols", "nt" if record["operation"]["molecule"] == "dna" else "aa"}:
            metadata_reasons.append("database_kind_conflict")
        if name in {"database_file_names", "database_volume_names"}:
            if len(set(value)) != len(value):
                metadata_reasons.append("duplicate_native_identity")
            for native_name in value:
                path = _native_file_path(native_name, occurrences.get(field["occurrence_id"]))
                if path is None:
                    metadata_reasons.append("record_association_unresolved")
                elif name == "database_file_names" and path not in paths:
                    inventory_reasons.append("output_family_incomplete")
                elif name == "database_volume_names" and not any(p.startswith(path + ".") for p in paths):
                    inventory_reasons.append("output_family_incomplete")

    for code in dict.fromkeys(inventory_reasons):
        failures.append(_failure(code, stage="capture" if code == "output_inventory_incomplete" else "validation"))
    checks.append(_check("database_inventory", "fail" if inventory_reasons else "pass",
                         subject_refs=[key], method="family_inventory",
                         reason=inventory_reasons[0] if inventory_reasons else None, occurrences=evidence))
    if record["native_metadata"]:
        for code in dict.fromkeys(metadata_reasons):
            failures.append(_failure(code))
        known_metadata = any(f["value"] is not None for f in record["native_metadata"])
        checks.append(_check("database_metadata", "fail" if metadata_reasons else "pass" if known_metadata else "unknown",
                             subject_refs=[key], method="explicit_reference_join",
                             reason=metadata_reasons[0] if metadata_reasons else None if known_metadata else "semantic_validation_unavailable",
                             occurrences=metadata_evidence))
    return checks, failures


def populate_database_artifact_set(*, operation: dict, inputs: list[dict], outputs: list[dict],
                                   database_key: str, identity: dict, software: dict,
                                   argv: list[str], native_paths: list[str],
                                   dependency_bindings: list[dict], native_metadata: list[dict],
                                   outcome: dict) -> dict:
    """Retain original preparation facts; completeness is not inferred from names.

    ``detail`` contains requested settings. ``native_metadata`` contains separate
    source-located native observations and is never replaced by those requests.
    Missing counts remain missing. The caller supplies the closed inventory and
    software/command identities established by the actual execution boundary.
    """
    operation = validate_blast_utility_operation(operation)
    outcome = validate_blast_utility_record("NativeOutcome", outcome)
    if operation["program"] != "makeblastdb" or operation["mode"] != "create_sequence_database":
        _fail("preparation_operation_required")
    if type(inputs) is not list or type(outputs) is not list:
        _fail("preparation_occurrence_lists_required")
    inputs = [validate_blast_utility_record("ArtifactOccurrence", row) for row in inputs]
    outputs = [validate_blast_utility_record("ArtifactOccurrence", row) for row in outputs]
    record = {
        "version": "blast_database_artifact_set_v1", "kind": "sequence_database",
        "operation": operation, "original_outcome": outcome, "database_key": database_key,
        "identity": identity, "software": software, "argv": argv, "native_paths": native_paths,
        "inputs": inputs, "outputs": outputs, "dependencies": dependency_bindings,
        "inventory_complete": outcome["writer_closed"] and outcome["inventory_complete"] and all(
            row["completeness"] == "complete" and row["native_path"] is not None for row in outputs),
        "native_metadata": native_metadata,
        "detail": {name: operation["parameters"][name] for name in _DETAIL_FIELDS},
        "compatibility": "unverified", "checks": [], "failures": [],
    }
    # Native contradictions need qualification before full relationship
    # validation. Validate finite shape first so native failures remain records;
    # the common validator below still owns all structural joins and meanings.
    try:
        record = _copy(record)
        _schema(record, SCHEMAS["DatabaseArtifactSet"])
    except (ValueError, RecursionError) as exc:
        raise ContractError("blast_utility_schema_invalid") from exc
    record["checks"], record["failures"] = _preparation_observations(record)
    return validate_database_artifact_relationships(record)


def validate_database_artifact_relationships(record: dict) -> dict:
    """Validate a saved artifact set without acquiring or inspecting its files."""
    record = validate_blast_utility_record("DatabaseArtifactSet", record)
    by_path, by_ref = {}, {}
    for occurrence in record["inputs"] + record["outputs"]:
        path = occurrence["native_path"]
        identity = occurrence["sha256"], occurrence["size_bytes"]
        if path is not None and path in by_path and by_path[path] != identity:
            _fail("artifact_path_identity_conflict")
        if occurrence["artifact_ref"] in by_ref and by_ref[occurrence["artifact_ref"]] != identity:
            _fail("artifact_reference_identity_conflict")
        if path is not None:
            by_path[path] = identity
        by_ref[occurrence["artifact_ref"]] = identity
    checks, failures = _preparation_observations(record)
    if any(check not in record["checks"] for check in checks):
        _fail("preparation_observation_conflict")
    if any(failure not in record["failures"] for failure in failures):
        _fail("preparation_failure_missing")
    return record


def _supplied_file_identity(value):
    try:
        value = _copy(value)
        _schema(value, FILE_IDENTITY_SCHEMA)
        _absolute(value["path"])
        return value
    except ValueError as exc:
        raise ContractError("blast_utility_projection_file_identity_invalid") from exc


def project_prepared_blast_database(record: dict, *, contract: str,
                                    preparation_receipt: dict, input_manifest: dict | None,
                                    metadata_manifests: list[dict]) -> dict:
    """Project the existing standard manifest or a specific unavailable result.

    Availability means the retained preparation facts meet that manifest's
    contract. It never upgrades ``compatibility`` or implies a native integrity
    check or a search. The supplied receipt has its own real identity; no file
    identity is fabricated for this not-yet-saved returned manifest.
    """
    record = validate_database_artifact_relationships(record)
    if type(contract) is not str or contract != "standard":
        _fail("projection_contract_unsupported")
    receipt = _supplied_file_identity(preparation_receipt)
    source_input = None if input_manifest is None else _supplied_file_identity(input_manifest)
    if type(metadata_manifests) is not list:
        _fail("projection_metadata_manifests_invalid")
    metadata = [_supplied_file_identity(value) for value in metadata_manifests]
    failures = list(record["failures"])
    if record["original_outcome"]["state"] != "succeeded":
        failures.append(_failure("preparation_not_successful", stage="projection"))
    if record["compatibility"] == "incompatible":
        failures.append(_failure("incompatible_database_format", stage="projection"))
    identities = [receipt, *metadata, *([] if source_input is None else [source_input])]
    by_path, by_ref = {}, {}
    for occurrence in record["inputs"] + record["outputs"]:
        identity = occurrence["sha256"], occurrence["size_bytes"]
        if occurrence["native_path"] is not None:
            by_path[occurrence["native_path"]] = identity
        by_ref[occurrence["artifact_ref"]] = identity
    for value in identities:
        identity = value["sha256"], value["size_bytes"]
        if ((value["path"] in by_path and by_path[value["path"]] != identity)
                or (value["artifact_ref"] in by_ref and by_ref[value["artifact_ref"]] != identity)):
            failures.append(_failure("supplied_binding_conflict", stage="projection"))
        by_path[value["path"]] = identity
        if value["artifact_ref"] is not None:
            by_ref[value["artifact_ref"]] = identity
    if failures:
        return validate_blast_utility_record("PreparedDatabaseProjection", {
            "status": "unavailable", "manifest": None, "failures": failures})

    # Preserve every supplied database component, including v5 sidecars and
    # unknown extensions. Streams remain in the complete artifact set above.
    files = []
    seen_paths = set()
    for occurrence in record["outputs"]:
        if occurrence["role"] in _DATABASE_ROLES and occurrence["native_path"] not in seen_paths:
            files.append({"path": occurrence["native_path"], "sha256": occurrence["sha256"],
                          "size_bytes": occurrence["size_bytes"]})
            seen_paths.add(occurrence["native_path"])
    manifest = {
        "version": "native_blast_standard_prepared_database_manifest_v1",
        "database_key": record["database_key"],
        "kind": "blast_nucleotide_sequence" if record["operation"]["molecule"] == "dna" else "blast_protein_sequence",
        "identity": record["identity"], "native_paths": record["native_paths"], "files": files,
        "preparation": {
            "method": "makeblastdb", "preparation_type": "sequence_database",
            "software": record["software"], "argv": record["argv"],
            "source": {"source_ref": receipt["artifact_ref"] or receipt["path"], "pointer": ""},
            "input_manifest": source_input, "receipt": receipt,
        },
        "metadata_manifests": metadata,
        "access": {"mode": "prepared_local", "offline_configuration": None},
        "inventory_complete": record["inventory_complete"],
    }
    try:
        manifest = validate_standard_prepared_blast_database_manifest(manifest)
    except ValueError:
        return validate_blast_utility_record("PreparedDatabaseProjection", {
            "status": "unavailable", "manifest": None,
            "failures": [_failure("supplied_binding_conflict", stage="projection")]})
    return validate_blast_utility_record("PreparedDatabaseProjection", {
        "status": "available", "manifest": manifest, "failures": []})


__all__ = ["populate_database_artifact_set", "validate_database_artifact_relationships",
           "project_prepared_blast_database"]
