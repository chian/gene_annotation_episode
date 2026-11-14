"""Literal UTF8 positions in explicitly received source representations.

This primitive selects no experimental meaning and publishes no evidence. Memory
is bounded by the requested needle/results/context and one internal byte chunk.
The content-addressed store supplies artifact custody; only examined bytes are
validated as text. A complete scan from zero also verifies the artifact digest.
"""
from __future__ import annotations

import codecs
import hashlib

from .domain import ContractError, REF, identity, obj

CHUNK_BYTES = 65536


def locate_schema():
    return obj({"source_ref": REF, "representation": {"enum": ["original", "text"]},
        "needle": {"type": "string", "minLength": 1},
        "offset": {"type": "integer", "minimum": 0},
        "limit": {"type": "integer", "minimum": 1},
        "context_bytes": {"type": "integer", "minimum": 0}},
        ["source_ref", "representation", "needle"])


def _immutable(source):
    body = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    if source["id"] != identity("source", {"origin": source["origin"], "record": body}):
        raise ContractError("source_location_identity_conflict")


def received_source(store, source_ref, representation, *, permitted_inputs, scope):
    """Recheck custody/metadata without opening bytes, including on replay."""
    if not isinstance(permitted_inputs, (tuple, list)):
        raise ContractError("source_location_inputs_not_bound")
    if source_ref not in permitted_inputs:
        raise ContractError("source_location_source_not_received")
    if representation not in ("original", "text"):
        raise ContractError("invalid_source_representation")
    scope = store.validate_scope(scope)
    pending, seen = [source_ref], set()
    while pending:
        reference = pending.pop()
        if reference in seen:
            continue
        seen.add(reference)
        row = store._require(reference, {"source"})
        _immutable(row)
        if reference not in store.reference_subset([reference], scope):
            raise ContractError("source_location_outside_scope")
        pending.extend(row.get("parent_source_refs", ()))
    source = store._require(source_ref, {"source"})
    artifact_ref = source["artifact_ref"] if representation == "original" else source.get("text_ref")
    if artifact_ref is None:
        raise ContractError("source_representation_unavailable", detail={"representation": representation})
    artifact = store._require(artifact_ref, {"artifact"})
    if (artifact["id"] != "artifact_" + artifact["sha256"]
            or type(artifact["size"]) is not int or artifact["size"] < 0):
        raise ContractError("source_location_artifact_identity_conflict")
    return artifact


def _text(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError("source_not_utf8_text") from error
    if "\x00" in text:
        raise ContractError("source_binary_text")
    return text


def _context(handle, start, end, width, total, artifact_ref):
    left, right = max(0, start - width), min(total, end + width)
    handle.seek(left)
    raw = handle.read(right - left)
    if len(raw) != right - left:
        raise ContractError("source_location_artifact_size_conflict")
    # Clip only the outer partial characters, never the match or invalid bytes.
    while 0 < left < start and raw and raw[0] & 0xC0 == 0x80:
        left += 1
        raw = raw[1:]
    while True:
        try:
            text = _text(raw)
            break
        except ContractError as error:
            cause = error.__cause__
            if (right == total or not isinstance(cause, UnicodeDecodeError) or cause.reason != "unexpected end of data"
                    or left + cause.start < end):
                raise
            raw = raw[:cause.start]
    if not left <= start < end <= left + len(raw):
        raise ContractError("source_location_context_span_conflict")
    return {"artifact_ref": artifact_ref, "start": left, "end": left + len(raw), "text": text}


def locate(store, source_ref, representation, needle, *, offset=0, limit=8, context_bytes=120,
           permitted_inputs, scope):
    if not isinstance(needle, str) or not needle:
        raise ContractError("nonempty_literal_needle_required")
    try:
        token = needle.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ContractError("utf8_literal_needle_required") from error
    if (type(offset) is not int or offset < 0 or type(limit) is not int or limit < 1
            or type(context_bytes) is not int or context_bytes < 0):
        raise ContractError("source_location_indices_invalid")
    artifact = received_source(store, source_ref, representation, permitted_inputs=permitted_inputs, scope=scope)
    total = artifact["size"]
    if offset > total:
        raise ContractError("source_offset_out_of_bounds")
    path = store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
    positions, tail, scanned_end, search_start = [], b"", offset, offset
    decoder = codecs.getincrementaldecoder("utf-8")()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        if handle.seek(0, 2) != total:
            raise ContractError("source_location_artifact_size_conflict")
        handle.seek(offset)
        first = handle.read(1)
        if first and first[0] & 0xC0 == 0x80:
            raise ContractError("source_offset_not_utf8_boundary")
        handle.seek(offset)
        eof = False
        while len(positions) <= limit:
            requested = min(CHUNK_BYTES, total - handle.tell())
            chunk = handle.read(requested)
            if len(chunk) != requested:
                raise ContractError("source_location_artifact_size_conflict")
            eof = handle.tell() == total
            digest.update(chunk)
            try:
                decoded = decoder.decode(chunk, final=eof)
            except UnicodeDecodeError as error:
                raise ContractError("source_not_utf8_text") from error
            if "\x00" in decoded:
                raise ContractError("source_binary_text")
            valid = decoded.encode("utf-8")
            base = scanned_end - len(tail)
            data = tail + valid
            scanned_end += len(valid)
            cursor = max(0, search_start - base)
            while len(positions) <= limit:
                found = data.find(token, cursor)
                if found < 0:
                    break
                positions.append(base + found)
                search_start = base + found + 1
                cursor = found + 1
            tail = data[-(len(token) - 1):] if len(token) > 1 else b""
            if eof or len(positions) > limit:
                break
        if eof and offset == 0 and digest.hexdigest() != artifact["sha256"]:
            raise ContractError("artifact_digest_mismatch")
        matches = [{"artifact_ref": artifact["id"],
            "witness": {"source_ref": source_ref, "representation": representation,
                "start": start, "end": start + len(token), "quote": needle},
            "context": _context(handle, start, start + len(token), context_bytes, total, artifact["id"])}
            for start in positions[:limit]]
        if handle.seek(0, 2) != total:
            raise ContractError("source_location_artifact_size_conflict")
    more = len(positions) > limit
    return {"source_ref": source_ref, "representation": representation, "artifact_ref": artifact["id"],
        "offset": offset, "scanned_range": {"start": offset, "end": scanned_end},
        "total_bytes": total, "matches": matches, "has_more": more,
        "next_query": {"source_ref": source_ref, "representation": representation, "needle": needle,
            "offset": positions[limit], "limit": limit, "context_bytes": context_bytes} if more else None}
