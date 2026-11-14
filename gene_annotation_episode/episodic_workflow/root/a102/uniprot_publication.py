"""Pure binding of a native UniProt page to existing acquisition references.

This descriptor retains source metadata. It supplies no acquisition score or
parent-return schema, and neither reads artifacts nor executes a request.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from jsonschema import Draft202012Validator

from .domain import identity
from .uniprot_native import validate_uniprot_projection
from .uniprot_native_contracts import PUBLICATION_SCHEMA


def bind_uniprot_publication(parsed: dict, *, source_ref: str,
                            native_artifact_ref: str,
                            references_by_ordinal: dict[int, dict]) -> dict:
    """Bind each original row ordinal to its actual stored reference record.

    The caller verifies artifact bytes first and reports a binding failure for
    every omitted parsed ordinal. The unchanged page counts parser-eligible
    rows; records contains the actual bound subset. Ordinals live in anchors,
    preserving the existing deduplication of identical references.
    """
    validate_uniprot_projection(parsed)
    if (not isinstance(source_ref, str) or not source_ref.startswith("source_") or
            native_artifact_ref != "artifact_" + parsed["content_sha256"]):
        raise ValueError("uniprot_publication_source_identity_conflict")
    if (parsed["page"]["request_verification"] != "caller_supplied" or
            parsed["page"]["effective_request"] is None):
        raise ValueError("uniprot_publication_request_unverified")
    ordinals = {row["identity"]["record_ordinal"] for row in parsed["records"]}
    if (not isinstance(references_by_ordinal, dict) or
            any(type(ordinal) is not int for ordinal in references_by_ordinal) or
            not set(references_by_ordinal) <= ordinals):
        raise ValueError("uniprot_publication_ordinal_binding_conflict")
    rows = []
    for native in parsed["records"]:
        anchor = native["identity"]
        if anchor["record_ordinal"] not in references_by_ordinal:
            continue
        stored = references_by_ordinal[anchor["record_ordinal"]]
        if (not isinstance(stored, dict) or stored.get("record_type") != "reference" or
                stored.get("origin") != "external" or stored.get("reference_type") != "protein" or
                stored.get("molecule") != "protein" or stored.get("source_ref") != source_ref or
                stored.get("accession") != anchor["primary_accession"]):
            raise ValueError("uniprot_publication_reference_binding_conflict")
        record = {key: value for key, value in stored.items()
                  if key not in {"id", "record_type", "origin"}}
        if stored.get("id") != identity("reference", {"origin": stored["origin"], "record": record}):
            raise ValueError("uniprot_publication_reference_identity_conflict")
        sequence = native["sequence"]
        expected_ref = ("artifact_" + hashlib.sha256(sequence["value"]["value"].encode("ascii")).hexdigest()
                        if sequence["value"]["state"] == "present" else None)
        if (stored.get("sequence_ref") != expected_ref or
                stored.get("length") != sequence["observed_length_aa"]):
            raise ValueError("uniprot_publication_sequence_binding_conflict")
        rows.append({"anchor": {"source_ref": source_ref, "reference_ref": stored["id"],
            "record_ordinal": anchor["record_ordinal"], "record_pointer": anchor["record_pointer"],
            "primary_accession": anchor["primary_accession"]},
            "sequence_ref": stored["sequence_ref"], "record": deepcopy(native)})
    publication = {"version": "uniprot_publication_v1", "source_ref": source_ref,
        "native_artifact_ref": native_artifact_ref, "content_sha256": parsed["content_sha256"],
        "page": deepcopy(parsed["page"]), "records": rows, "issues": deepcopy(parsed["issues"])}
    Draft202012Validator(PUBLICATION_SCHEMA).validate(publication)
    return publication


__all__ = ["bind_uniprot_publication"]
