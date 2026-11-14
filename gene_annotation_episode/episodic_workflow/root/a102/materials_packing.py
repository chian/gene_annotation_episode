"""Compact physical custody for native read members, not biological targets.

Member component digests describe their exact own bytes. Chunk artifacts have
their own independent digests; offsets never change a chunk into a read artifact.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

from .domain import ContractError

REPRESENTATION = "packed_member_components_v1"
CHUNK_BYTES = 8 * 1024 * 1024
COMPONENTS = ("header", "sequence", "quality")
MEDIA = {"header": "text/x-parser-title; charset=utf-8", "sequence": "text/x-sequence",
         "quality": "text/x-fastq-quality"}


def install_tables(store):
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS material_pack_chunks(
            parse_key TEXT NOT NULL,chunk_index INTEGER NOT NULL,artifact_ref TEXT NOT NULL,
            PRIMARY KEY(parse_key,chunk_index));
        CREATE TABLE IF NOT EXISTS material_component_spans(
            member_ref TEXT NOT NULL,component TEXT NOT NULL,part INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,
            PRIMARY KEY(member_ref,component,part));
        CREATE TABLE IF NOT EXISTS material_name_counts(
            parse_key TEXT NOT NULL,name TEXT NOT NULL,next_occurrence INTEGER NOT NULL,
            PRIMARY KEY(parse_key,name));
    """)


class Occurrences:
    """Transient parser bookkeeping on disk, removed when an attempt finalizes."""
    def __init__(self, store, key):
        self.store, self.key = store, key

    def __call__(self, name):
        row = self.store.db.execute("SELECT next_occurrence FROM material_name_counts WHERE parse_key=? AND name=?",
                                    (self.key, name)).fetchone()
        occurrence = row[0] if row else 0
        self.store.db.execute("INSERT INTO material_name_counts VALUES(?,?,?) ON CONFLICT(parse_key,name) DO UPDATE SET next_occurrence=excluded.next_occurrence",
                              (self.key, name, occurrence + 1))
        return occurrence

    def close(self):
        self.store.db.execute("DELETE FROM material_name_counts WHERE parse_key=?", (self.key,))


class Packer:
    def __init__(self, store, key):
        self.store, self.key = store, key
        self.buffer, self.chunk_index = bytearray(), 0
        self.budget = CHUNK_BYTES
        if type(self.budget) is not int or self.budget < 1:
            raise ContractError("invalid_material_chunk_budget")

    def flush(self):
        if not self.buffer:
            return
        ref = self.store.artifact(bytes(self.buffer), "application/x-packed-member-components")
        self.store.db.execute("INSERT INTO material_pack_chunks VALUES(?,?,?)", (self.key, self.chunk_index, ref))
        self.buffer.clear()
        self.chunk_index += 1

    def add(self, member_ref, values):
        metadata = {}
        for component in COMPONENTS:
            value = values[component]
            if value is None:
                metadata[component] = None
                continue
            encoded = value.encode("utf-8" if component == "header" else "ascii")
            metadata[component] = {"sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded)}
            cursor, part = 0, 0
            while cursor < len(encoded):
                if len(self.buffer) == self.budget:
                    self.flush()
                count = min(self.budget - len(self.buffer), len(encoded) - cursor)
                start = len(self.buffer)
                self.buffer.extend(memoryview(encoded)[cursor:cursor+count])
                self.store.db.execute("INSERT INTO material_component_spans VALUES(?,?,?,?,?,?)",
                    (member_ref, component, part, self.chunk_index, start, start + count))
                cursor += count
                part += 1
        return {"representation": REPRESENTATION, "parse_key": self.key, "components": metadata}


def packed(member):
    return member.get("storage", {}).get("representation") == REPRESENTATION


def component_info(store, member, component):
    if packed(member):
        return member["storage"]["components"][component]
    ref = member[component + "_ref"]
    if ref is None:
        return None
    artifact = store.get(ref)
    return {"sha256": artifact["sha256"], "bytes": artifact["size"]}


def content_ref(store, member, component):
    info = component_info(store, member, component)
    return "artifact_" + info["sha256"] if info is not None else None


def materialized_components(store, member):
    """Actual registered artifacts only, shared by reference ownership/export."""
    refs = {}
    for component in COMPONENTS:
        info = component_info(store, member, component)
        if info is None:
            refs[component] = None
            continue
        ref = "artifact_" + info["sha256"]
        row = store.db.execute("SELECT sha256,size FROM artifacts WHERE id=?", (ref,)).fetchone()
        refs[component] = ref if row is not None and row[0] == info["sha256"] and row[1] == info["bytes"] else None
    return refs


def component_chunks(store, member, component, *, offset=0, limit=None):
    """Yield only selected component bytes, verifying intersected bounded chunks."""
    from .materials import artifact_path
    info = component_info(store, member, component)
    if info is None:
        return
    end = info["bytes"] if limit is None else min(info["bytes"], offset + limit)
    if not packed(member):
        with artifact_path(store, member[component + "_ref"]).open("rb") as handle:
            handle.seek(offset)
            remaining = max(0, end-offset)
            while remaining:
                data = handle.read(min(65536, remaining))
                if not data:
                    raise ContractError("material_component_size_mismatch")
                remaining -= len(data)
                yield data
        return
    cursor = 0
    rows = store.db.execute("SELECT s.start,s.end,c.artifact_ref FROM material_component_spans s JOIN material_pack_chunks c ON c.parse_key=? AND c.chunk_index=s.chunk_index WHERE s.member_ref=? AND s.component=? ORDER BY s.part",
        (member["storage"]["parse_key"], member["id"], component))
    for start, stop, ref in rows:
        width = stop-start
        if width < 0:
            raise ContractError("material_component_span_invalid")
        overlap_start, overlap_end = max(offset, cursor), min(end, cursor+width)
        if overlap_start < overlap_end:
            artifact = store.get(ref)
            if not 0 <= start <= stop <= artifact["size"]:
                raise ContractError("material_component_span_invalid")
            with artifact_path(store, ref).open("rb") as handle:
                handle.seek(start + overlap_start-cursor)
                remaining = overlap_end-overlap_start
                while remaining:
                    data = handle.read(min(65536, remaining))
                    if not data:
                        raise ContractError("material_component_size_mismatch")
                    remaining -= len(data)
                    yield data
        cursor += width
    if cursor != info["bytes"]:
        raise ContractError("material_component_size_mismatch")


def component_window(store, member, component, offset, limit):
    if component_info(store, member, component) is None:
        return None
    return b"".join(component_chunks(store, member, component, offset=offset, limit=limit))


def materialize(store, member, components=COMPONENTS):
    """Explicitly selected real artifacts; immutable member/index rows never change."""
    from .materials import artifact_file, artifact_path
    with store.transaction():
        refs = materialized_components(store, member)
        for component in components:
            info = component_info(store, member, component)
            if info is None:
                continue
            if refs[component] is not None:
                artifact_path(store, refs[component])
                continue
            digest, size = hashlib.sha256(), 0
            fd, name = tempfile.mkstemp(prefix=".member-component-", dir=store.path)
            try:
                with os.fdopen(fd, "wb") as output:
                    for data in component_chunks(store, member, component):
                        output.write(data)
                        digest.update(data)
                        size += len(data)
                if digest.hexdigest() != info["sha256"] or size != info["bytes"]:
                    raise ContractError("material_component_digest_mismatch")
                refs[component] = artifact_file(store, Path(name), MEDIA[component])
            finally:
                Path(name).unlink(missing_ok=True)
        return refs
