"""Freeze actual selected Store sequence material for restriction operations.

This adapter reads supplied records and artifacts only. Existing resolvers own
sequence traversal and scope; no restriction search or resource choice occurs.
A witness and a content hash do not by themselves establish episode authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from .alignment_site_native import immutable_record
from .domain import ContractError, identity
from . import library_targets as libraries
from . import materials_packing as packing
from .materials import artifact_path
from .restriction_mapping_contracts import restriction_canonical, validate_restriction_record
from .sequence_mapping import validate_mapping


_VERSION = "restriction_sequence_witness_v1"
_DNA = frozenset("ACGTRYSWKMBDHVN")
_SEQUENCES = frozenset(("input", "feature", "product", "reference", "read_subject"))
_FIELDS = frozenset(("version", "namespace", "sequence_ref", "sequence", "content_sha256",
    "length_nt", "sequence_version", "molecule", "scope", "records", "artifacts", "mapping",
    "mapping_state", "mapping_issue", "packed_components"))
_INDEX_FIELDS = frozenset(("member_ref", "parse_key", "component", "part", "chunk_index",
    "start", "end", "artifact_ref"))
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _require(condition, code, **detail):
    if not condition:
        raise ContractError("restriction_" + code, detail=detail or None)


def _text(value):
    return type(value) is str and bool(value)


def _uint(value):
    return type(value) is int and value >= 0


def _same(left, right):
    return restriction_canonical(left) == restriction_canonical(right)


def _edges(record):
    """Relevant custody edges only, never arbitrary references in requests."""
    kind = record["record_type"]
    edges = []
    def add(ref, kinds):
        if ref is not None:
            _require(_text(ref), "ancestry_invalid")
            edges.append((ref, frozenset(kinds)))
    if kind == "feature":
        add(record.get("subject_ref"), _SEQUENCES)
        _require(bool(edges), "ancestry_invalid")
    elif kind == "product":
        parents = record.get("parent_refs")
        _require(type(parents) is list and bool(parents), "ancestry_invalid")
        for ref in parents:
            add(ref, _SEQUENCES)
    elif kind == "read_subject":
        for field, types in (("library_ref", ("input",)), ("member_ref", ("collection_member",)),
                ("collection_ref", ("collection",)), ("material_ref", ("material",))):
            _require(record.get(field) is not None, "ancestry_invalid")
            add(record[field], types)
    elif kind == "input" and not libraries.is_library(record):
        native = record.get("source_record", {})
        _require(type(native) is dict, "ancestry_invalid")
        for field, types in (("material_ref", ("material",)), ("member_ref", ("collection_member",))):
            add(native.get(field), types)
    elif kind in {"collection_member", "collection"}:
        add(record.get("material_ref"), ("material",))
        if kind == "collection_member":
            add(record.get("collection_ref"), ("collection",))
    elif kind == "reference":
        add(record.get("member_ref"), ("collection_member",))
    if kind == "source":
        parents = record.get("parent_source_refs", [])
        _require(type(parents) is list, "ancestry_invalid")
        for ref in parents:
            add(ref, ("source",))
    for field in ("source_ref", "mapping_source_ref"):
        add(record.get(field), ("source",))
    return edges


def _record_identity(record):
    _require(type(record) is dict and _text(record.get("id"))
        and _text(record.get("record_type")), "record_identity_conflict")
    if record["record_type"] == "collection_member":
        _require(record.get("origin") == "tool" and _uint(record.get("ordinal"))
            and _uint(record.get("length")), "member_identity_conflict")
        storage = record.get("storage")
        if packing.packed(record):
            _require(type(storage) is dict and _text(storage.get("parse_key"))
                and type(storage.get("components")) is dict
                and set(storage["components"]) == set(packing.COMPONENTS), "member_identity_conflict")
            def component_ref(component):
                info = storage["components"][component]
                if info is None:
                    return None
                _require(type(info) is dict and set(info) == {"sha256", "bytes"}
                    and type(info["sha256"]) is str and _DIGEST.fullmatch(info["sha256"]) is not None
                    and _uint(info["bytes"]), "member_identity_conflict")
                return "artifact_" + info["sha256"]
            key = storage["parse_key"]
            sequence_ref, quality_ref = component_ref("sequence"), component_ref("quality")
            component_ref("header")
        else:
            # The immutable parse key is retained on the actual collection row.
            return
        _require(_uint(record.get("ordinal")) and record["id"] == identity("member", {
            "parse_key": key, "ordinal": record["ordinal"], "sequence_ref": sequence_ref,
            "quality_ref": quality_ref}), "member_identity_conflict")
    else:
        try:
            immutable_record(record)
        except (ContractError, KeyError, TypeError, ValueError) as error:
            raise ContractError("restriction_record_identity_conflict") from error


def _scope(value):
    _require(type(value) is dict and {"subject_refs"} <= set(value)
        <= {"subject_refs", "segments", "read_selection_refs"}, "witness_invalid")
    for field in ("subject_refs", "read_selection_refs"):
        if field in value:
            refs = value[field]
            _require(type(refs) is list and all(_text(ref) for ref in refs)
                and refs == sorted(set(refs)) and (field != "read_selection_refs" or refs), "witness_invalid")
    if "segments" in value:
        _require(type(value["segments"]) is list and bool(value["segments"]), "witness_invalid")
        for row in value["segments"]:
            _require(type(row) is dict and {"target_ref", "start", "end", "unit"} <= set(row)
                <= {"target_ref", "member_ref", "start", "end", "unit"}
                and row["target_ref"] in value["subject_refs"]
                and _uint(row["start"]) and type(row["end"]) is int and row["start"] < row["end"]
                and row["unit"] in {"nt", "aa", "symbol"}
                and ("member_ref" not in row or _text(row["member_ref"])), "witness_invalid")


def _validated_witness(value):
    """Validate a detached supplied witness; this performs no Store or file I/O."""
    try:
        restriction_canonical(value)
    except (ValueError, TypeError, RecursionError) as error:
        raise ContractError("restriction_witness_invalid") from error
    _require(type(value) is dict and set(value) == _FIELDS and value["version"] == _VERSION,
        "witness_invalid")
    sequence = value["sequence"]
    _require(type(sequence) is str and bool(sequence) and sequence.isascii()
        and set(sequence.upper()) <= _DNA and type(value["length_nt"]) is int
        and value["length_nt"] == len(sequence)
        and value["content_sha256"] == hashlib.sha256(sequence.encode("utf-8")).hexdigest(),
        "sequence_content_conflict")
    _require(value["namespace"] in {"subject", "reference"} and _text(value["sequence_ref"])
        and value["molecule"] in {"dna", "unspecified"}
        and (value["sequence_version"] is None or _uint(value["sequence_version"])), "witness_invalid")
    _scope(value["scope"])
    _require(type(value["records"]) is list and type(value["artifacts"]) is list
        and type(value["packed_components"]) is list, "witness_invalid")
    records = {}
    for row in value["records"]:
        _require(type(row) is dict and set(row) == {"record_ref", "record_type", "record"}
            and _text(row["record_ref"]) and _text(row["record_type"]), "witness_invalid")
        record = row["record"]
        _record_identity(record)
        _require(record["id"] == row["record_ref"] and record["record_type"] == row["record_type"],
            "record_identity_conflict")
        records[row["record_ref"]] = record
    _require([r["record_ref"] for r in value["records"]] == sorted(records)
        and value["sequence_ref"] in records, "witness_invalid")
    selected = records[value["sequence_ref"]]
    _require(selected["record_type"] in _SEQUENCES and not libraries.is_library(selected)
        and value["namespace"] == ("reference" if selected["record_type"] == "reference" else "subject")
        and selected.get("revision") == value["sequence_version"], "selected_record_conflict")
    seen, active = set(), set()
    def visit(ref):
        _require(ref not in active, "ancestry_cycle")
        if ref in seen:
            return
        _require(ref in records, "ancestry_incomplete")
        active.add(ref)
        for child, kinds in _edges(records[ref]):
            _require(child in records and records[child]["record_type"] in kinds, "ancestry_invalid")
            visit(child)
        active.remove(ref);seen.add(ref)
    visit(value["sequence_ref"])
    _require(seen == set(records), "ancestry_unrelated")
    molecule = selected.get("molecule") or "unspecified"
    if selected["record_type"] == "feature":
        ancestor = selected
        while ancestor["record_type"] == "feature":
            ancestor = records[ancestor["subject_ref"]]
        molecule = ancestor.get("molecule") or "unspecified"
    _require(molecule == value["molecule"], "selected_record_conflict")
    artifacts = {}
    for pin in value["artifacts"]:
        _require(type(pin) is dict and set(pin) == {"artifact_ref", "sha256", "size_bytes"}
            and type(pin["sha256"]) is str and _DIGEST.fullmatch(pin["sha256"]) is not None
            and pin["artifact_ref"] == "artifact_" + pin["sha256"] and _uint(pin["size_bytes"]),
            "artifact_identity_conflict")
        artifacts[pin["artifact_ref"]] = pin
    _require([p["artifact_ref"] for p in value["artifacts"]] == sorted(artifacts), "witness_invalid")
    for record in records.values():
        if record["record_type"] == "collection_member":
            collection = records.get(record.get("collection_ref"))
            _require(collection is not None and collection["record_type"] == "collection"
                and collection["source_ref"] == record["source_ref"]
                and collection["material_ref"] == record["material_ref"], "member_identity_conflict")
            key = collection["parse_key"]
            if packing.packed(record):
                component = record["storage"]["components"]["sequence"]
                _require(component is not None and component["bytes"] == record["length"], "member_identity_conflict")
                seq = "artifact_" + component["sha256"]
                quality = record["storage"]["components"]["quality"]
                quality_ref = "artifact_" + quality["sha256"] if quality is not None else None
            else:
                seq, quality_ref = record["sequence_ref"], record["quality_ref"]
                _require(seq in artifacts and artifacts[seq]["size_bytes"] == record["length"], "member_identity_conflict")
            _require(record["id"] == identity("member", {"parse_key": key, "ordinal": record["ordinal"],
                "sequence_ref": seq, "quality_ref": quality_ref}) and (not packing.packed(record)
                or key == record["storage"]["parse_key"]), "member_identity_conflict")
        for field in (("artifact_ref", "text_ref", "request_ref") if record["record_type"] == "source"
                else ("sequence_ref", "header_ref", "quality_ref") if record["record_type"] != "read_subject" else ()):
            if record.get(field) is not None:
                _require(record[field] in artifacts, "artifact_identity_conflict")
    groups, chunk_owners = {}, {}
    index_order = []
    for row in value["packed_components"]:
        _require(type(row) is dict and set(row) == _INDEX_FIELDS and _text(row["member_ref"])
            and _text(row["parse_key"]) and row["component"] in packing.COMPONENTS
            and all(_uint(row[f]) for f in ("part", "chunk_index", "start", "end"))
            and row["start"] < row["end"] and row["artifact_ref"] in artifacts,
            "packed_index_conflict")
        member = records.get(row["member_ref"])
        _require(member is not None and member["record_type"] == "collection_member" and packing.packed(member)
            and member["storage"]["parse_key"] == row["parse_key"]
            and row["end"] <= artifacts[row["artifact_ref"]]["size_bytes"], "packed_index_conflict")
        owner = (row["parse_key"], row["chunk_index"])
        _require(owner not in chunk_owners or chunk_owners[owner] == row["artifact_ref"], "packed_index_conflict")
        chunk_owners[owner] = row["artifact_ref"]
        key = (row["member_ref"], row["component"])
        groups.setdefault(key, []).append(row)
        index_order.append((*key, row["part"]))
    _require(index_order == sorted(set(index_order)), "packed_index_conflict")
    for member in records.values():
        if member["record_type"] != "collection_member" or not packing.packed(member):
            continue
        for component in packing.COMPONENTS:
            rows = groups.get((member["id"], component), [])
            info = member["storage"]["components"][component]
            _require([r["part"] for r in rows] == list(range(len(rows)))
                and sum(r["end"] - r["start"] for r in rows) == (info["bytes"] if info else 0),
                "packed_index_conflict")
    if value["mapping_state"] == "available":
        _require(value["mapping_issue"] is None, "mapping_conflict")
        try:
            validate_mapping(value["mapping"])
        except (ValueError, TypeError, KeyError) as error:
            raise ContractError("restriction_mapping_conflict") from error
        _require(value["mapping"]["units_per_symbol"] == 1
            and value["mapping"]["symbol_length"] == len(sequence)
            and all(r["unit"] != "aa" for r in value["mapping"]["path"]), "mapping_conflict")
    else:
        _require(value["mapping_state"] == "unavailable" and value["mapping"] is None
            and value["mapping_issue"] == "subregion_mapping_unavailable", "mapping_conflict")
    if selected.get("length") is not None:
        _require(type(selected["length"]) is int and selected["length"] == len(sequence), "selected_record_conflict")
    if selected["record_type"] == "read_subject":
        member, library = records[selected["member_ref"]], records[selected["library_ref"]]
        _require(libraries.is_library(library) and member["collection_ref"] in library["collection_refs"]
            and all(selected[field] == member[field] for field in
                ("source_ref", "collection_ref", "material_ref", "length", "molecule")), "selected_record_conflict")
        expected = (member["storage"]["components"]["sequence"]["sha256"] if packing.packed(member)
            else artifacts[member["sequence_ref"]]["sha256"])
        _require(value["content_sha256"] == expected, "sequence_content_conflict")
    if selected.get("sequence_ref"):
        pin = artifacts.get(selected["sequence_ref"])
        _require(pin is not None and pin["sha256"] == value["content_sha256"]
            and pin["size_bytes"] == len(sequence), "sequence_content_conflict")
    return deepcopy(value)


def validate_restriction_sequence_witness(value):
    """Validate supplied data only; a valid witness grants no Store authority."""
    try:
        return _validated_witness(value)
    except (ContractError, ValueError, KeyError, TypeError, RecursionError) as error:
        if isinstance(error, ContractError) and str(error).startswith("restriction_"):
            raise
        raise ContractError("restriction_witness_invalid") from error


def restriction_sequence_witness(store, sequence_ref, *, namespace, scope,
        permitted_record_refs, sequence_reader, check_operand):
    """Read the actual selected operand without writing or selecting more work."""
    _require(type(permitted_record_refs) in {list, tuple} and all(_text(r) for r in permitted_record_refs)
        and _text(sequence_ref) and sequence_ref in permitted_record_refs, "operand_not_received")
    try:
        normalized = store.validate_scope(scope)
        selected = store.get(sequence_ref)
        _require(selected["record_type"] in _SEQUENCES and not libraries.is_library(selected), "sequence_operand_required")
        _require(namespace == ("reference" if selected["record_type"] == "reference" else "subject"), "namespace_conflict")
        check_operand(sequence_ref, normalized)
        molecule = store.subject_molecule(sequence_ref)
        _require(molecule in {"dna", "unspecified"}, "dna_processing_model_required")
        sequence = sequence_reader(sequence_ref, molecule_model="dna")
        _require(type(sequence) is str and bool(sequence) and sequence.isascii()
            and set(sequence.upper()) <= _DNA, "dna_sequence_invalid")
        _require(store.subject_length(sequence_ref) == len(sequence), "sequence_content_conflict")
        mapping = store.sequence_mapping(sequence_ref) if store.has_exact_mapping(sequence_ref) else None
        records, artifacts, indexes, active = {}, {}, [], set()
        def capture_artifact(ref):
            if ref in artifacts:
                return
            artifact = store.get(ref)
            _require(artifact["record_type"] == "artifact", "artifact_identity_conflict")
            path = artifact_path(store, ref)
            _require(path.stat().st_size == artifact["size"] and ref == "artifact_" + artifact["sha256"],
                "artifact_identity_conflict")
            artifacts[ref] = {"artifact_ref": ref, "sha256": artifact["sha256"], "size_bytes": artifact["size"]}
        def visit(ref, kinds=None):
            _require(ref not in active, "ancestry_cycle")
            if ref in records:
                _require(kinds is None or records[ref]["record_type"] in kinds, "ancestry_invalid")
                return
            record = store.get(ref)
            _require(kinds is None or record["record_type"] in kinds, "ancestry_invalid")
            _record_identity(record)
            active.add(ref)
            if record["record_type"] == "collection_member":
                index = store.db.execute("SELECT parse_key,ordinal,collection_ref FROM material_members WHERE id=?", (ref,)).fetchone()
                _require(index is not None and index["ordinal"] == record["ordinal"]
                    and index["collection_ref"] == record["collection_ref"], "member_identity_conflict")
                if packing.packed(record):
                    _require(index["parse_key"] == record["storage"]["parse_key"], "member_identity_conflict")
                    for component in packing.COMPONENTS:
                        info = packing.component_info(store, record, component)
                        rows = list(store.db.execute("SELECT s.part,s.chunk_index,s.start,s.end,c.artifact_ref "
                            "FROM material_component_spans s LEFT JOIN material_pack_chunks c "
                            "ON c.parse_key=? AND c.chunk_index=s.chunk_index "
                            "WHERE s.member_ref=? AND s.component=? ORDER BY s.part",
                            (index["parse_key"], ref, component)))
                        for row in rows:
                            _require(row["artifact_ref"] is not None, "packed_index_conflict")
                            capture_artifact(row["artifact_ref"])
                            indexes.append({"member_ref": ref, "parse_key": index["parse_key"],
                                "component": component, **dict(row)})
                        if info is not None:
                            digest, size = hashlib.sha256(), 0
                            for chunk in packing.component_chunks(store, record, component):
                                digest.update(chunk);size += len(chunk)
                            _require(digest.hexdigest() == info["sha256"] and size == info["bytes"],
                                "member_component_conflict")
            for child, types in _edges(record):
                visit(child, types)
            for field in (("artifact_ref", "text_ref", "request_ref") if record["record_type"] == "source"
                    else ("sequence_ref", "header_ref", "quality_ref") if record["record_type"] != "read_subject" else ()):
                if record.get(field) is not None:
                    capture_artifact(record[field])
            active.remove(ref);records[ref] = record
        visit(sequence_ref, _SEQUENCES)
        value = {"version": _VERSION, "namespace": namespace, "sequence_ref": sequence_ref,
            "sequence": sequence, "content_sha256": hashlib.sha256(sequence.encode("utf-8")).hexdigest(),
            "length_nt": len(sequence), "sequence_version": selected.get("revision"), "molecule": molecule,
            "scope": normalized, "records": [{"record_ref": ref, "record_type": records[ref]["record_type"],
                "record": records[ref]} for ref in sorted(records)],
            "artifacts": [artifacts[ref] for ref in sorted(artifacts)], "mapping": mapping,
            "mapping_state": "available" if mapping is not None else "unavailable",
            "mapping_issue": None if mapping is not None else "subregion_mapping_unavailable",
            "packed_components": sorted(indexes, key=lambda r: (r["member_ref"], r["component"], r["part"]))}
        return validate_restriction_sequence_witness(value)
    except (ContractError, ValueError, KeyError, TypeError, OSError, RecursionError) as error:
        if isinstance(error, ContractError) and str(error).startswith("restriction_"):
            raise
        raise ContractError("restriction_operand_resolution_failed", detail={"cause_code": str(error)}) from error


def revalidate_restriction_sequence_witness(store, witness, *, scope,
        permitted_record_refs, sequence_reader, check_operand):
    original = validate_restriction_sequence_witness(witness)
    current = restriction_sequence_witness(store, original["sequence_ref"], namespace=original["namespace"],
        scope=scope, permitted_record_refs=permitted_record_refs,
        sequence_reader=sequence_reader, check_operand=check_operand)
    _require(_same(original, current), "witness_changed")
    return original


def restriction_sequence_binding(witness, *, source_ref):
    """Project narrow operands; the caller authenticates its retained source ID."""
    witness = validate_restriction_sequence_witness(witness)
    _require(_text(source_ref), "input_source_required")
    return validate_restriction_record("SequenceBinding", {
        "version": "restriction_selected_sequence_v1", "namespace": witness["namespace"],
        "sequence_ref": witness["sequence_ref"], "source_ref": source_ref,
        "sequence_version": witness["sequence_version"], "content_sha256": witness["content_sha256"],
        "length_nt": witness["length_nt"], "origin_mapping_ref": None})


__all__ = ["restriction_sequence_witness", "validate_restriction_sequence_witness",
    "revalidate_restriction_sequence_witness", "restriction_sequence_binding"]
