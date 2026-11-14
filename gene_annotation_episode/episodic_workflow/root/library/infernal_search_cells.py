"""Pure shared assembly of parsed Infernal search cells and record identities.

No native text reader, acquisition, calculation or episode behavior lives here.
Native metadata/geometry rules are factored from infernal_search_inputs.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
import re

from .infernal_search_contracts import (
    SHEET_SCHEMA, finite_copy, sheet_digest, validate_infernal_search_sheet)

def _copy(value):
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("infernal_finite_json_required") from error
    return deepcopy(value)

def _issue(issues, code, *, severity="error", **detail):
    issues.append({"code": code, "severity": severity, **detail})

def _positive(value):
    return type(value) is int and value > 0

def _metadata(rows, kind, issues, *, nullable_names=False):
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError("infernal_metadata_list_required")
    result = []
    for index, raw in enumerate(_copy(rows)):
        problems = []
        if not isinstance(raw, dict):
            _issue(problems, "metadata_object_required")
            row = {}
        else:
            row = raw
        nullable = (nullable_names and kind == "sequence" and row.get("name") is None
                    and isinstance(row.get("query_occurrence_key"), str) and row["query_occurrence_key"])
        if not nullable and (not isinstance(row.get("name"), str) or not row["name"]):
            _issue(problems, "metadata_name_invalid")
        for field in ("accession", "artifact_id"):
            if row.get(field) is not None and (not isinstance(row[field], str) or not row[field]):
                _issue(problems, "metadata_identity_invalid", field=field)
        if row.get("occurrence") is not None and not _positive(row["occurrence"]):
            _issue(problems, "metadata_occurrence_invalid")
        field = "length" if kind == "sequence" else "consensus_length"
        length = row.get(field)
        if length is not None and not _positive(length):
            _issue(problems, "metadata_length_invalid", field=field)
            length = None
        if kind == "sequence" and row.get("sequence") is not None:
            sequence = row["sequence"]
            if not isinstance(sequence, str) or not re.fullmatch(r"[ACGTURYSWKMBDHVNacgturyswkmbdhvn]+", sequence):
                _issue(problems, "metadata_sequence_invalid")
            elif length is not None and len(sequence) != length:
                _issue(problems, "metadata_sequence_length_conflict", declared=length, actual=len(sequence))
        result.append({"metadata_index": index, "supplied": raw, "length": length,
                       "status": "invalid" if problems else "available", "issues": problems})
        issues.extend({**p, "metadata_kind": kind, "metadata_index": index} for p in problems)
    return result

def _join(entity, records, hit, kind):
    candidates, rejected, unresolved = [], [], []
    for record in records:
        raw = record["supplied"]
        if not isinstance(raw, dict) or raw.get("name") != entity["name"]:
            continue
        if raw.get("artifact_id") is not None and raw["artifact_id"] != hit["locator"]["artifact_id"]:
            continue
        index = record["metadata_index"]
        if raw.get("occurrence") is not None:
            unresolved.append(index)
        elif raw.get("accession") is not None and entity["accession"] is not None and raw["accession"] != entity["accession"]:
            rejected.append(index)
        else:
            candidates.append(record)
    result = {"status": "missing", "metadata_index": None,
              "candidate_indices": [r["metadata_index"] for r in candidates],
              "rejected_identity_indices": rejected, "unresolved_occurrence_indices": unresolved}
    if unresolved:
        result["status"] = "unresolved_occurrence"
        _issue(hit["issues"], "metadata_original_record_association_required", kind=kind, metadata_indices=unresolved)
    elif len(candidates) > 1:
        result["status"] = "ambiguous"
        _issue(hit["issues"], "metadata_join_ambiguous", kind=kind, metadata_indices=result["candidate_indices"])
    elif candidates:
        record = candidates[0]
        result.update(status="matched" if record["status"] == "available" else "invalid_metadata",
                      metadata_index=record["metadata_index"])
        if record["status"] == "available":
            return result, record
        _issue(hit["issues"], "matched_metadata_invalid", kind=kind, metadata_index=record["metadata_index"])
    elif rejected:
        result["status"] = "identity_conflict"
        _issue(hit["issues"], "metadata_identity_conflict", kind=kind, metadata_indices=rejected)
    return result, None

def _length(native, record, join, kind, hit):
    supplied = record["length"] if record else None
    result = {"native": native, "supplied": supplied, "value": None, "status": "missing",
              "provenance": {"native": hit["locator"] if native is not None else None,
                             "metadata_index": join["metadata_index"]}}
    if "native_"+kind+"_length" in hit["native_tokens"] and native is None:
        result["status"] = "invalid_native_length"
    elif join["status"] in {"ambiguous", "invalid_metadata", "unresolved_occurrence", "identity_conflict"}:
        result["status"] = join["status"]
    elif native is not None and supplied is not None and native != supplied:
        result["status"] = "conflict"
        _issue(hit["issues"], "native_supplied_length_conflict", kind=kind, native=native, supplied=supplied)
    elif native is not None or supplied is not None:
        result.update(value=native if native is not None else supplied, status="validated")
    else:
        _issue(hit["issues"], "length_denominator_missing", severity="warning", kind=kind)
    return result

def _geometry(hit, prefix):
    start, end = hit.get(prefix + "_from"), hit.get(prefix + "_to")
    if not _positive(start) or not _positive(end):
        return None
    if prefix == "model" and start > end:
        _issue(hit["issues"], "model_coordinates_reversed")
        return None
    if prefix == "sequence" and (hit["strand"] not in {"+", "-"}
            or hit["strand"] == "+" and start > end or hit["strand"] == "-" and start < end):
        _issue(hit["issues"], "sequence_strand_coordinate_conflict")
        return None
    native = hit.get("native_" + prefix + "_length")
    if native is not None and max(start, end) > native:
        _issue(hit["issues"], "coordinates_exceed_native_length", kind=prefix)
        return None
    length = hit["lengths"][prefix]["value"]
    if length is not None and max(start, end) > length:
        _issue(hit["issues"], "coordinates_exceed_validated_length", kind=prefix)
        return None
    return [min(start, end) - 1, max(start, end)]


_NATIVE_NULLS = ("native_target_name", "native_target_accession", "native_query_name", "native_query_accession",
    "algorithm", "model_from", "model_to", "sequence_from", "sequence_to", "strand", "truncation", "pass",
    "gc_fraction", "bias_bits", "bitscore", "evalue", "inclusion", "native_model_length", "native_sequence_length",
    "idx", "clan", "olp", "anyidx", "anyfrct1", "anyfrct2", "winidx", "winfrct1", "winfrct2", "description",
    "native_rank", "native_alignment_accuracy", "native_model_boundary", "native_sequence_boundary",
    "correspondence", "duplicate_of", "query_occurrence_key")


def _descriptor(profile):
    return {"profile": profile, "source_ref": None, "artifact_ref": None, "source_sha256": None,
            "source_byte_length": None, "byte_hash_verified": False}


def _explicit_record(entity, records, hit, kind):
    """Honor a source-validated occurrence association, never a positional join."""
    join = entity.get("metadata_join", {"status": "missing", "metadata_index": None})
    entity["metadata_join"] = join
    index = join.get("metadata_index")
    if join.get("status") != "matched":
        return join, None
    if type(index) is not int or not 0 <= index < len(records):
        raise ValueError("infernal_explicit_metadata_association_invalid")
    record = records[index]
    if record["status"] != "available":
        join["status"] = "invalid_metadata"
        _issue(hit["issues"], "matched_metadata_invalid", kind=kind, metadata_index=index)
        return join, None
    supplied = record["supplied"]
    if kind == "sequence":
        identity = entity.get("identity")
        expected = {"kind": "supplied_sequence_metadata", "metadata_index": index}
        if identity != expected:
            raise ValueError("infernal_explicit_metadata_association_invalid")
        occurrence = hit.get("query_occurrence_key")
        if occurrence is not None and supplied.get("query_occurrence_key") != occurrence:
            raise ValueError("infernal_explicit_occurrence_association_invalid")
    if (entity.get("name") is not None and supplied.get("name") is not None
            and entity["name"] != supplied["name"]):
        raise ValueError("infernal_explicit_native_name_conflict")
    return join, record


def _native_association_ambiguity(hits, artifacts):
    """Preserve native repeated-list and metadata-identity rejection exactly."""
    ids = [a.get("artifact_id") for a in artifacts]
    metadata_identities, repeated_queries = defaultdict(set), defaultdict(set)
    for hit in hits:
        for kind in ("sequence", "model"):
            join = hit[kind]["metadata_join"]
            if join["status"] == "matched":
                metadata_identities[(kind, join["metadata_index"])].add((hit[kind]["name"], hit[kind]["accession"]))
        if hit.get("table_format") == 2:
            repeated_queries[(hit["locator"]["artifact_index"], hit["native_query_name"], hit["native_query_accession"])].add(hit["query_list_locator"]["list_index"])
    for hit in hits:
        repeated = len(repeated_queries[(hit["locator"]["artifact_index"], hit["native_query_name"], hit["native_query_accession"])]) > 1
        duplicate_id = ids.count(hit["locator"]["artifact_id"]) > 1
        for kind in ("sequence", "model"):
            join = hit[kind]["metadata_join"]
            multiple = len(metadata_identities[(kind, join["metadata_index"])]) > 1
            if duplicate_id or multiple or repeated and hit[kind]["native_role"] == "query":
                if join["status"] == "matched":
                    join["status"] = "ambiguous"
                    hit["lengths"][kind].update(value=None, status="ambiguous")
                    hit["sequence_length" if kind == "sequence" else "consensus_length"] = None
                if kind == "sequence":
                    hit["sequence"]["identity"] = None
                _issue(hit["issues"], "native_record_association_ambiguous", kind=kind)


def _length_agreement(hits, populations):
    # One physical input/model must not gain a denominator by selecting the
    # first of contradictory source measurements.
    for kind in ("sequence", "model"):
        groups = defaultdict(list)
        for hit in hits:
            joined = hit[kind]["metadata_join"]
            key = ("metadata", joined["metadata_index"]) if joined["status"] == "matched" else None
            if kind == "sequence" and key is None and hit["sequence"].get("identity"):
                key = ("query_list", json.dumps(hit["sequence"]["identity"], sort_keys=True))
            if key is not None:
                groups[key].append(hit)
        for members in groups.values():
            values = {h["lengths"][kind]["native"] for h in members if h["lengths"][kind]["native"] is not None}
            if len(values) > 1:
                for hit in members:
                    hit["lengths"][kind].update(value=None, status="conflict")
                    hit["sequence_length" if kind == "sequence" else "consensus_length"] = None
                    _issue(hit["issues"], "entity_native_lengths_conflict", kind=kind, lengths=sorted(values))
    for population in populations:
        members = [h for h in hits if h["sequence"].get("identity") == population["sequence_identity"]]
        cells = [population["length"], *(h["lengths"]["sequence"] for h in members)]
        values = {c["value"] for c in cells if c.get("value") is not None}
        if len(values) > 1 or any(c.get("status") == "conflict" for c in cells):
            for cell in cells:
                cell.update(value=None, status="conflict")
            for hit in members:
                hit["sequence_length"] = None
            _issue(population["issues"], "entity_sequence_lengths_conflict", lengths=sorted(values))


def populate_infernal_search_cells(
    *, operation: dict, artifacts: list[dict], hits: list[dict],
    sequence_metadata: list[dict] | None, model_metadata: list[dict] | None,
    sequence_populations: list[dict], source_context: dict | None,
    issues: list[dict], statistical_limitations: list[str],
) -> dict:
    """Assemble parsed facts into the one common search sheet, without scoring.

    Native rows are joined with the existing strict name/accession semantics.
    Format adapters can instead supply explicit source-validated role records,
    including a nullable native name and an exact original occurrence identity.
    """
    data = finite_copy(dict(operation=operation, artifacts=artifacts, hits=hits,
        sequence_metadata=sequence_metadata, model_metadata=model_metadata,
        sequence_populations=sequence_populations, source_context=source_context,
        issues=issues, statistical_limitations=statistical_limitations))
    operation, artifacts, hits, issues = (data[k] for k in ("operation", "artifacts", "hits", "issues"))
    source_context, populations = data["source_context"], data["sequence_populations"]
    profile = (source_context or {}).get("profile", "infernal_tblout")
    native = profile == "infernal_tblout"
    if not isinstance(hits, list) or not isinstance(artifacts, list) or not isinstance(populations, list):
        raise ValueError("infernal_search_cells_lists_required")
    seqmeta = _metadata(data["sequence_metadata"], "sequence", issues, nullable_names=profile == "rfam_single_json")
    modmeta = _metadata(data["model_metadata"], "model", issues)
    for index, artifact in enumerate(artifacts):
        artifact.setdefault("artifact_index", index)
        artifact.setdefault("source_descriptor", _descriptor(profile))
    for hit in hits:
        for field in _NATIVE_NULLS:
            hit.setdefault(field, None)
        hit.setdefault("native_tokens", {})
        hit.setdefault("issues", [])
        hit.setdefault("source_details", {"profile": profile})
        artifact = artifacts[hit["locator"]["artifact_index"]]
        preassembled = all(isinstance(hit.get(k), dict) for k in ("sequence", "model"))
        old_lengths = hit.get("lengths", {})
        hit["lengths"] = {}
        for kind, records in (("sequence", seqmeta), ("model", modmeta)):
            if preassembled:
                entity = hit[kind]
                join, record = _explicit_record(entity, records, hit, kind)
            else:
                program = hit.get("program", operation.get("program"))
                role = ("target" if (kind == "sequence") == (program == "cmsearch") else "query") if program else None
                entity = {"name": hit.get("native_" + str(role) + "_name"),
                    "accession": hit.get("native_" + str(role) + "_accession"), "native_role": role,
                    "input_record_occurrence": None}
                join, record = _join(entity, records, hit, kind) if role else ({"status": "role_unknown", "metadata_index": None}, None)
                entity["metadata_join"] = join
                hit[kind] = entity
                if kind == "sequence":
                    entity["identity"] = ({"kind": "supplied_sequence_metadata", "metadata_index": record["metadata_index"]} if record else None)
            length = _length(hit["native_" + kind + "_length"], record, join, kind, hit)
            # Retained invalid/conflicting cells cannot be rehabilitated by
            # permissive defaults during a format adapter's reassembly.
            if old_lengths.get(kind, {}).get("status") not in (None, "missing", "validated"):
                length = old_lengths[kind]
            hit["lengths"][kind] = length
        hit["consensus_length"] = hit["lengths"]["model"]["value"]
        hit["sequence_length"] = hit["lengths"]["sequence"]["value"]
        hit["model_interval"] = _geometry(hit, "model")
        hit["sequence_interval"] = _geometry(hit, "sequence")
        if hit["source_details"].get("query_coordinates_valid") is False:
            hit["sequence_interval"] = None
        missing = hit["source_details"].get("missing", {})
        if any(missing.get(k) == "coordinates_invalid" for k in ("query_from", "query_to")):
            hit["sequence_interval"] = None
        if any(missing.get(k) == "coordinates_invalid" for k in ("model_from", "model_to")):
            hit["model_interval"] = None
        hit["coordinate_convention"] = {"native": "one_based_inclusive", "intervals": "zero_based_half_open"}
        if (not preassembled and hit["sequence"].get("identity") is None and hit.get("program") == "cmscan"
                and hit.get("table_format") == 2 and hit["query_list_boundary_observed"]
                and artifact.get("effective_complete") is True and hit["sequence"]["metadata_join"]["status"] == "missing"):
            hit["sequence"]["identity"] = {"kind": "native_query_list", **hit["query_list_locator"]}
        if hit["sequence"].get("identity") is None:
            _issue(hit["issues"], "sequence_aggregate_identity_unavailable", severity="warning")
    if native:
        _native_association_ambiguity(hits, artifacts)
        for index, artifact in enumerate(artifacts):
            relevant = [h for h in hits if h["locator"]["artifact_index"] == index]
            artifact["retained_population_complete"] = (artifact.get("effective_complete") is True
                and not artifact.get("omitted_overlaps", False)
                and all(row.get("status") != "invalid" for row in artifact["rows"])
                and not any(p["code"] == "native_list_index_discontinuity" for h in relevant for p in h["issues"]))
            for hit in relevant:
                hit["population_complete"] = artifact["retained_population_complete"]
                identity = hit["sequence"].get("identity")
                if not hit["population_complete"] and identity and identity["kind"] == "native_query_list":
                    hit["sequence"]["identity"] = None
                    _issue(hit["issues"], "native_query_population_incomplete", severity="warning")
    _length_agreement(hits, populations)
    for hit in hits:
        hit.setdefault("population_complete", False)
        hit.setdefault("attribution", {"sequence": "valid" if hit["sequence"].get("identity") else "unresolved",
            "model": "valid" if hit["model"].get("name") else "unresolved", "source_locators": [deepcopy(hit["locator"])]})
        hit["status"] = "partial" if hit["issues"] else "available"
        issues.extend({**p, **hit["locator"]} for p in hit["issues"])
    for artifact in artifacts:
        for row in artifact.get("rows", []):
            if row.get("hit_id") not in {h["hit_id"] for h in hits}:
                issues.extend({**p, **row.get("locator", {})} for p in row.get("issues", []))
        issues.extend({**p, "artifact_id": artifact.get("artifact_id"), "artifact_index": artifact["artifact_index"]} for p in artifact.get("issues", []))
        if artifact.get("status") != "invalid":
            artifact["status"] = ("partial" if artifact.get("issues") or any(h["issues"] for h in hits if h["locator"]["artifact_index"] == artifact["artifact_index"])
                                  or artifact.get("effective_complete") is not True else "available")
    status = ("missing" if not artifacts or not hits and not any(a.get("effective_complete") is True or a.get("rows") for a in artifacts)
              else "partial" if issues else "available")
    if not hits and any(a.get("rows") or a.get("status") == "invalid" for a in artifacts):
        status = "invalid"
    result = {**data, "schema": SHEET_SCHEMA, "metadata_validation": {"sequence": seqmeta, "model": modmeta},
        "status": status, "lineage": None,
        "no_hit_meaning": "no_reported_match_under_recorded_settings; not biological absence"}
    return validate_infernal_search_sheet(result)


def upgrade_saved_infernal_search_sheet(sheet: dict) -> dict:
    """Explicit pure v1-cell conversion; ordinary replay never invokes this.

    Existing cells, intervals, source text and observations are not recomputed.
    The new lineage identifies the unchanged legacy sheet by its original digest.
    """
    saved = finite_copy(sheet)
    if not isinstance(saved, dict) or saved.get("schema") != "infernal_search_sheet_v1":
        raise ValueError("saved_infernal_search_sheet_v1_required")
    result = deepcopy(saved)
    result.update(schema=SHEET_SCHEMA, sequence_populations=[], source_context={"profile": "infernal_tblout"},
        lineage={"source_sheet_schema": saved["schema"], "source_sheet_digest": sheet_digest(saved)})
    for artifact in result["artifacts"]:
        artifact["source_descriptor"] = _descriptor("infernal_tblout")
    for hit in result["hits"]:
        for field in _NATIVE_NULLS:
            hit.setdefault(field, None)
        hit.update(source_details={"profile": "infernal_tblout"}, attribution={
            "sequence": "valid" if hit["sequence"].get("identity") else "unresolved",
            "model": "valid" if hit["model"].get("name") else "unresolved", "source_locators": [deepcopy(hit["locator"])]})
    return validate_infernal_search_sheet(result)


__all__ = ["populate_infernal_search_cells", "upgrade_saved_infernal_search_sheet"]
