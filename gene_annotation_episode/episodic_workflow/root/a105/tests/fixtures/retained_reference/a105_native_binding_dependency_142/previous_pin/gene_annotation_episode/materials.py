"""Caller asset custody and source-bound indexes in the existing Store authority.

Members are source records, never annotation targets by registration or parsing.
Only initialization binds explicitly selected sequence targets. The SQLite
member index is authoritative for parsed members; counts describe its immutable
snapshot and are published in the same transaction.
"""
from __future__ import annotations

import base64
import codecs
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse, unquote

from .domain import ContractError, MOLECULES, ROLES, canonical, identity
from .material_parsing import FORMATS, VERSION, recognize, records
from . import materials_packing as packing
from . import library_targets as libraries

METADATA_PREVIEW_CHARACTERS = 256


def text_preview(text):
    """A display projection, never a replacement for a native identifier."""
    return {"text": text[:METADATA_PREVIEW_CHARACTERS], "characters": len(text),
            "utf8_bytes": len(text.encode("utf-8")),
            "complete": len(text) <= METADATA_PREVIEW_CHARACTERS}


def member_preview(store, member):
    body = {key: value for key, value in member.items()
            if key not in {"name", "description", "sequence_ref", "quality_ref"}}
    body.update(name_preview=text_preview(member["name"]),
        description_preview=text_preview(member["description"]),
        quality_present=packing.component_info(store, member, "quality") is not None,
        metadata_preview_characters=METADATA_PREVIEW_CHARACTERS,
        header={"representation": member["header_representation"],
                "utf8_bytes": packing.component_info(store, member, "header")["bytes"],
                "read_with": {"member_ref": member["id"], "offset": 0, "limit": 12000}})
    return body


def model_record_view(store, row):
    """Bound automatic native-label context without altering stored records."""
    if row.get("record_type") == "read_subject":
        member = store.get(row["member_ref"])
        return {**{key: value for key, value in row.items() if key not in {"name", "description"}},
            "name_preview": text_preview(row["name"]), "description_preview": text_preview(row["description"]),
            "metadata_preview_characters": METADATA_PREVIEW_CHARACTERS,
            "header": {"representation": member["header_representation"],
                "utf8_bytes": packing.component_info(store, member, "header")["bytes"],
                "read_with": {"member_ref": member["id"], "offset": 0, "limit": 12000}}}
    if row.get("record_type") == "input" and row.get("source_record", {}).get("member_ref"):
        body = {key: value for key, value in row.items() if key not in {"name", "description"}}
        body["source_record"] = {key: value for key, value in row["source_record"].items()
                                 if key != "identifier"}
        body["source_record"]["identifier_preview"] = text_preview(row["source_record"]["identifier"])
        member = store.get(row["source_record"]["member_ref"])
        body.update(name_preview=text_preview(row["name"]),
                    description_preview=text_preview(row["description"]),
                    metadata_preview_characters=METADATA_PREVIEW_CHARACTERS,
                    header={"representation": member["header_representation"],
                            "utf8_bytes": packing.component_info(store, member, "header")["bytes"],
                            "read_with": {"member_ref": member["id"], "offset": 0, "limit": 12000}})
        return body
    if row.get("record_type") == "reference" and row.get("member_ref"):
        body = {key: value for key, value in row.items() if key != "label"}
        member = store.get(row["member_ref"])
        body.update(label_preview=text_preview(member["name"]),
                    metadata_preview_characters=METADATA_PREVIEW_CHARACTERS,
                    header={"representation": member["header_representation"],
                            "utf8_bytes": packing.component_info(store, member, "header")["bytes"],
                            "read_with": {"member_ref": member["id"], "offset": 0, "limit": 12000}})
        return body
    return row


def install_tables(store):
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS material_members(
            id TEXT PRIMARY KEY,parse_key TEXT NOT NULL,ordinal INTEGER NOT NULL,
            collection_ref TEXT,data TEXT NOT NULL,UNIQUE(parse_key,ordinal));
        CREATE INDEX IF NOT EXISTS member_collection_index ON material_members(collection_ref,ordinal);
        CREATE TABLE IF NOT EXISTS material_errors(
            parse_key TEXT NOT NULL,error_index INTEGER NOT NULL,data TEXT NOT NULL,
            PRIMARY KEY(parse_key,error_index));
        CREATE TABLE IF NOT EXISTS material_annotations(
            parse_key TEXT NOT NULL,record_ordinal INTEGER NOT NULL,entry_kind TEXT NOT NULL,
            entry_ordinal INTEGER NOT NULL,byte_start INTEGER NOT NULL,byte_end INTEGER NOT NULL,
            preview TEXT NOT NULL,PRIMARY KEY(parse_key,record_ordinal,entry_kind,entry_ordinal));
    """)
    packing.install_tables(store)


def artifact_file(store, path, media_type="application/octet-stream"):
    """Capture a file with bounded memory before attempting its representation."""
    digest, size = hashlib.sha256(), 0
    fd, temporary = tempfile.mkstemp(dir=store.path / "artifacts", prefix=".capture-")
    try:
        with os.fdopen(fd, "wb") as output, Path(path).open("rb") as original:
            for chunk in iter(lambda: original.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        checksum = digest.hexdigest()
        directory = store.path / "artifacts" / checksum[:2]
        directory.mkdir(exist_ok=True)
        destination = directory / checksum
        if not destination.exists():
            os.replace(temporary, destination)
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        ref = "artifact_" + checksum
        store.db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?)", (ref, checksum, media_type, size))
        return ref
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def artifact_path(store, ref):
    artifact = store._require(ref, {"artifact"})
    path = store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != artifact["sha256"]:
        raise ContractError("artifact_digest_mismatch")
    return path


def is_text(path):
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                decoder.decode(chunk)
        decoder.decode(b"", final=True)
        return True
    except UnicodeError:
        return False


def source_for_artifact(store, artifact, *, provider="caller", uri=None, request=None,
                        parent_source_refs=None):
    path = artifact_path(store, artifact)
    return store.put("source", {"provider": provider, "accession": None, "uri": uri,
        "artifact_ref": artifact, "text_ref": artifact if is_text(path) else None,
        "request_ref": store.artifact(canonical(request), "application/json") if request else None,
        "version": VERSION if provider != "caller" else None, "retrieved_at": None,
        **({"parent_source_refs": parent_source_refs} if parent_source_refs is not None else {})},
        origin="caller" if provider == "caller" else "tool")


def _native_entry(store, key, event, handle):
    data = event["native_entry"]
    encoded = (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    start = handle.tell()
    handle.write(encoded)
    if event["entry_kind"] == "record":
        record = data.get("record")
        preview = {"native_parser_returned_record": data["native_parser_returned_record"],
            "metadata_available": record is not None, "warning_count": len(data["parser_warnings"]),
            "record_id_preview": text_preview(record["id"]) if record else None,
            "description_preview": text_preview(record["description"]) if record else None,
            "feature_count": record["feature_count"] if record else None,
            "sequence_available": record["sequence"]["defined"] if record else None}
    else:
        feature = data["feature"]
        preview = {"metadata_available": feature is not None,
            "feature_type_preview": text_preview(feature["type"]) if feature else None,
            "location_preview": text_preview(feature["location"]["text"]) if feature and feature["location"] is not None else None,
            "qualifier_count": len(feature["qualifiers"]) if feature else None}
    store.db.execute("INSERT INTO material_annotations VALUES(?,?,?,?,?,?,?)",
        (key, event["ordinal"], event["entry_kind"], event["entry_ordinal"], start, handle.tell(), canonical(preview)))


def register_material(store, input_path=None, *, data=None, source_ref=None, name=None, use="evidence",
        format="auto", molecule="unspecified", role="unspecified", sample=None,
        library=None, context=None, quality_encoding="unspecified"):
    if sum(value is not None for value in (input_path, data, source_ref)) != 1:
        raise ContractError("choose_one_material_source")
    if molecule not in MOLECULES or role not in ROLES:
        raise ContractError("unsupported_input_declaration")
    with store.transaction():
        if source_ref is not None:
            source = store._require(source_ref, {"source"})
            # Reusing acquired material preserves its actual custody. The new
            # wrapper is an operational interpretation, not a caller source.
            actual_name = source["accession"] or (Path(unquote(urlparse(source["uri"]).path)).name if source["uri"] else None)
            name = name or actual_name or source["provider"]
        elif input_path is not None:
            path = Path(input_path).resolve()
            artifact = artifact_file(store, path)
            uri, name = path.as_uri(), name or path.stem
        else:
            artifact = store.artifact(data)
            uri, name = None, name or "input"
        if source_ref is None:
            source = source_for_artifact(store, artifact, uri=uri)
        contexts = []
        if context is not None:
            contexts.append(store._caller_source(context, "caller_entry_context")["id"])
        declared = {}
        for kind, label in (("sample", sample), ("library", library)):
            if label is not None:
                if not isinstance(label, str) or not label:
                    raise ContractError("invalid_caller_" + kind + "_identifier")
                supplied = store._caller_source({kind: label}, "caller_" + kind)
                declared[kind] = store.put("context", {"context_type": "sample" if kind == "sample" else "collection",
                    "name": label, "source_ref": supplied["id"], "attributes": [], "related_refs": []}, origin="caller")["id"]
        return store.put("material", {"source_ref": source["id"], "name": name, "use": use,
            "requested_format": format, "molecule": molecule, "role": role,
            "sample_ref": declared.get("sample"), "library_ref": declared.get("library"),
            "context_source_refs": contexts, "quality_encoding": quality_encoding}, origin="tool" if source_ref else "caller")


def parse_material(store, material_ref, *, format=None):
    material = store._require(material_ref, {"material"})
    requested = material["requested_format"] if format is None else format
    if not isinstance(requested, str):
        raise ContractError("invalid_parser_format")
    key = identity("parse", {"material_ref": material_ref, "format": requested, "parser_version": VERSION})
    cached = store.db.execute("SELECT data FROM records WHERE record_type='parse_attempt' AND json_extract(data,'$.parse_key')=?", (key,)).fetchone()
    if cached:
        return json.loads(cached[0])
    original = store.get(material["source_ref"])
    source = original
    path = artifact_path(store, source["artifact_ref"])
    compression, representation, code = "none", requested, "parsed"
    valid, failures, symbols = 0, 0, 0
    collection = None
    native_source, native_path, native_parsed = None, None, 0
    packer = None
    gzip_without_prefix = False
    with store.transaction():
        def error(value):
            nonlocal failures
            store.db.execute("INSERT INTO material_errors VALUES(?,?,?)", (key, failures, canonical(value)))
            failures += 1

        try:
            with path.open("rb") as handle:
                prefix = handle.read(4096)
            if prefix.startswith(b"\x1f\x8b"):
                from .material_gzip import decode_prefix
                compression = "gzip"
                with tempfile.TemporaryDirectory(prefix="material-decode-", dir=store.path) as temporary:
                    decoded = Path(temporary) / "content"
                    decoding, failure = decode_prefix(path, decoded)
                    artifact = artifact_file(store, decoded)
                if failure is not None:
                    # Exact native exception text is source provenance, not an
                    # investigator-authored scientific interpretation.
                    decoding["exception_message"] = str(failure)
                    error({"ordinal": None, "byte_offset": None,
                        "code": "gzip_decode_incomplete", "decoded_prefix_bytes": decoding["decoded_bytes"],
                        "exception_type": decoding["exception_type"],
                        "unparsed_remainder": "unknown", "wrapper_integrity": "not_established"})
                    gzip_without_prefix = decoding["decoded_bytes"] == 0
                source = source_for_artifact(store, artifact, provider="material.gzip",
                    parent_source_refs=[original["id"]],
                    request={"material_ref": material_ref, "source_ref": original["id"], **decoding})
                path = artifact_path(store, artifact)
                with path.open("rb") as handle:
                    prefix = handle.read(4096)
            if requested == "auto":
                representation = recognize(prefix)
            if representation in {"raw", "fasta", "fastq", "genbank"} and not gzip_without_prefix:
                if representation == "fastq" or (representation == "fasta" and material["role"] == "read"):
                    packer = packing.Packer(store, key)
                if representation == "genbank":
                    fd, temporary = tempfile.mkstemp(prefix=".native-genbank-", dir=store.path)
                    os.close(fd)
                    native_path = Path(temporary)
                with path.open("rb") as handle, (native_path.open("wb") if native_path else open(os.devnull, "wb")) as native_handle:
                    for result in records(handle, representation, molecule=material["molecule"], name=material["name"],
                                          occurrences=packing.Occurrences(store, key)):
                        if "error" in result:
                            error(result["error"])
                            continue
                        if "native_entry" in result:
                            _native_entry(store, key, result, native_handle)
                            if result["entry_kind"] == "record" and result["native_entry"]["native_parser_returned_record"]:
                                native_parsed += 1
                            continue
                        record = result["record"]
                        title, sequence = record.pop("native_title"), record.pop("sequence")
                        quality = record.pop("quality")
                        length = len(sequence)
                        # Identity binds exact own-component content, never a
                        # chunk digest or later materialization/cache state.
                        sequence_identity = "artifact_" + hashlib.sha256(sequence.encode("ascii")).hexdigest()
                        quality_identity = "artifact_" + hashlib.sha256(quality.encode("ascii")).hexdigest() if quality is not None else None
                        member_id = identity("member", {"parse_key": key, "ordinal": record["ordinal"],
                            "sequence_ref": sequence_identity, "quality_ref": quality_identity})
                        storage = packer.add(member_id, {"header": title, "sequence": sequence, "quality": quality}) if packer else None
                        header_ref = None if packer else store.artifact(title, "text/x-parser-title; charset=utf-8")
                        sequence_ref = None if packer else store.artifact(sequence, "text/x-sequence")
                        quality_ref = None if packer or quality is None else store.artifact(quality, "text/x-fastq-quality")
                        data = {**record, "id": member_id, "record_type": "collection_member", "origin": "tool",
                            "material_ref": material_ref, "source_ref": source["id"], "sequence_ref": sequence_ref,
                            "header_ref": header_ref, "parser_version": VERSION,
                            "quality_ref": quality_ref, "quality_encoding": material["quality_encoding"],
                            "length": length, "molecule": material["molecule"], "role": material["role"],
                            **({"storage": storage} if storage else {})}
                        store.db.execute("INSERT INTO material_members VALUES(?,?,?,?,?)", (member_id, key, record["ordinal"], None, canonical(data)))
                        valid += 1
                        symbols += length
                if not valid and not failures:
                    error({"ordinal": 0, "byte_offset": 0, "code": "empty_input"})
            elif representation in {"text", "opaque"}:
                code = "retained_without_sequence_projection"
            else:
                code = "representation_unrecognized" if representation == "unknown" else "parser_not_implemented"
        except Exception as exc:
            code = "parser_execution_failed"
            error({"ordinal": valid, "byte_offset": None,
                "code": "gzip_decode_failed" if compression == "gzip" and source is original else "parser_execution_failed"})
            # Diagnostic text remains private audit; scientific feedback is typed.
            store.artifact(type(exc).__name__ + ": " + str(exc), "text/plain")
        if packer is not None:
            packer.flush()
        packing.Occurrences(store, key).close()
        if native_path is not None:
            from .genbank_intake import REPRESENTATION
            try:
                native_artifact = artifact_file(store, native_path, "application/x-ndjson; charset=utf-8")
                native_source = source_for_artifact(store, native_artifact, provider="material.genbank",
                    parent_source_refs=[source["id"]], request={"representation": REPRESENTATION,
                        "material_ref": material_ref, "parse_key": key, "parser_version": VERSION,
                        "input_source_ref": source["id"], "input_artifact_ref": source["artifact_ref"],
                        "original_material_source_ref": original["id"],
                        "meaning": "native_supplied_source_assertions_not_current_target_annotations"})
            finally:
                native_path.unlink(missing_ok=True)
        if failures:
            status = "partial" if valid or native_parsed else "failed"
            code = "partial_sequence_projection" if valid else "native_metadata_without_sequence_projection" if native_parsed else "sequence_projection_failed"
        elif representation in {"raw", "fasta", "fastq", "genbank", "text", "opaque"}:
            status = "completed"
        else:
            status = "unavailable"
        if representation in {"raw", "fasta", "fastq", "genbank"}:
            collection = store.put("collection", {"material_ref": material_ref, "source_ref": source["id"],
                "parse_key": key, "representation": representation, "parser_version": VERSION,
                "member_count": valid, "sequence_symbols": symbols, "complete": not failures,
                "molecule": material["molecule"], "role": material["role"],
                "sample_ref": material["sample_ref"], "library_ref": material["library_ref"],
                "context_source_refs": material["context_source_refs"], "quality_encoding": material["quality_encoding"],
                **({"storage_representation": packing.REPRESENTATION} if packer else {})}, origin="tool")
            store.db.execute("UPDATE material_members SET collection_ref=?,data=json_set(data,'$.collection_ref',?) WHERE parse_key=?",
                (collection["id"], collection["id"], key))
        return store.put("parse_attempt", {"material_ref": material_ref, "source_ref": source["id"],
            "requested_format": requested, "representation": representation, "compression": compression,
            "parser_version": VERSION, "parse_key": key, "status": status, "code": code,
            "collection_ref": collection["id"] if collection else None, "valid_records": valid,
            "error_count": failures,
            **({"native_source_ref": native_source["id"]} if native_source else {})}, origin="tool")


def annotation_page(store, parse_ref, *, record_ordinal=None, kind="record", offset=0, limit=50):
    """Page native supplied assertions; never Store.current_annotations()."""
    attempt = store._require(parse_ref, {"parse_attempt"})
    if (kind not in {"record", "feature"} or type(offset) is not int or offset < 0
            or type(limit) is not int or limit < 1 or
            (record_ordinal is not None and (type(record_ordinal) is not int or record_ordinal < 0))):
        raise ContractError("invalid_native_annotation_page")
    source_ref = attempt.get("native_source_ref")
    common = {"parse_ref": parse_ref, "parser_version": attempt["parser_version"],
        "original_source_ref": store.get(attempt["material_ref"])["source_ref"],
        "parsed_input_source_ref": attempt["source_ref"], "kind": kind, "record_ordinal": record_ordinal,
        "offset": offset, "limit": limit, "meaning": "native_supplied_source_assertions_not_current_target_annotations"}
    if source_ref is None:
        return {**common, "availability": "unavailable", "code": "native_annotations_not_available",
                "entries": [], "total": None, "next_offset": None, "next_query": None}
    source = store.get(source_ref)
    parameters = [attempt["parse_key"], kind]
    where = "parse_key=? AND entry_kind=?"
    if record_ordinal is not None:
        where += " AND record_ordinal=?"
        parameters.append(record_ordinal)
    total = store.db.execute("SELECT count(*) FROM material_annotations WHERE " + where, parameters).fetchone()[0]
    rows = store.db.execute("SELECT * FROM material_annotations WHERE " + where +
        " ORDER BY record_ordinal,entry_ordinal LIMIT ? OFFSET ?", (*parameters, limit, offset))
    entries = [{"record_ordinal": row["record_ordinal"], "entry_kind": row["entry_kind"],
        "entry_ordinal": row["entry_ordinal"], "source_ref": source_ref, "artifact_ref": source["artifact_ref"],
        "start": row["byte_start"], "end": row["byte_end"],
        "coordinate_system": "normalized_native_jsonl_byte_offsets_not_original_genbank",
        "preview": json.loads(row["preview"]),
        "read_with": {"source_ref": source_ref, "representation": "original", "offset": row["byte_start"],
                      "limit": min(12000, row["byte_end"] - row["byte_start"])}} for row in rows]
    next_offset = offset + len(entries) if offset + len(entries) < total else None
    next_query = {"parse_ref": parse_ref, "kind": kind, "offset": next_offset, "limit": limit}
    if record_ordinal is not None:
        next_query["record_ordinal"] = record_ordinal
    return {**common, "availability": "available", "source_ref": source_ref,
        "artifact_ref": source["artifact_ref"], "entries": entries, "total": total,
        "next_offset": next_offset, "next_query": next_query if next_offset is not None else None}


def member_page(store, collection_ref, *, offset=0, limit=50):
    collection = store._require(collection_ref, {"collection"})
    if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 1:
        raise ContractError("invalid_page")
    rows = store.db.execute("SELECT data FROM material_members WHERE collection_ref=? ORDER BY ordinal LIMIT ? OFFSET ?",
        (collection_ref, limit, offset))
    data = []
    for row in rows:
        member = json.loads(row[0])
        # The index handle is resolved by material.member. Sequence and quality
        # artifacts enter ordinary scientific reference forms when that selected
        # member is exposed as a reusable reference, not by enumerating a library.
        data.append(member_preview(store, member))
    total = collection["member_count"]
    next_offset = offset + len(data) if offset + len(data) < total else None
    return {"collection_ref": collection_ref, "members": data, "offset": offset, "limit": limit,
        "total": total, "next_offset": next_offset,
        "next_query": {"collection_ref": collection_ref, "offset": next_offset, "limit": limit} if next_offset is not None else None}


def error_page(store, parse_ref, *, offset=0, limit=50):
    attempt = store._require(parse_ref, {"parse_attempt"})
    if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 1:
        raise ContractError("invalid_page")
    rows = store.db.execute("SELECT data FROM material_errors WHERE parse_key=? ORDER BY error_index LIMIT ? OFFSET ?",
        (attempt["parse_key"], limit, offset))
    errors = [json.loads(row[0]) for row in rows]
    next_offset = offset + len(errors) if offset + len(errors) < attempt["error_count"] else None
    return {"parse_ref": parse_ref, "errors": errors, "offset": offset, "limit": limit,
        "total": attempt["error_count"], "next_offset": next_offset,
        "next_query": {"parse_ref": parse_ref, "offset": next_offset, "limit": limit} if next_offset is not None else None}


def read_material(store, material_ref, *, offset=0, limit=12000):
    material = store._require(material_ref, {"material"})
    source = store.get(material["source_ref"])
    artifact = store.get(source["artifact_ref"])
    if type(offset) is not int or not 0 <= offset <= artifact["size"] or type(limit) is not int or limit < 1:
        raise ContractError("invalid_material_window")
    with artifact_path(store, artifact["id"]).open("rb") as handle:
        handle.seek(offset)
        content = handle.read(limit)
    return {"material_ref": material_ref, "source_ref": source["id"], "artifact_ref": artifact["id"],
        "offset": offset, "end": offset + len(content), "total_bytes": artifact["size"],
        "encoding": "base64", "content": base64.b64encode(content).decode("ascii"),
        "next_offset": offset + len(content) if offset + len(content) < artifact["size"] else None}


def source_window(store, source_ref, *, offset=0, limit=12000, representation="text"):
    source = store._require(source_ref, {"source"})
    if representation not in {"text", "original", "stdout", "stderr"}:
        raise ContractError("invalid_source_representation")
    available = ["original"] + [name for name in ("text", "stdout", "stderr") if source.get(name + "_ref")]
    if representation in {"stdout", "stderr"}:
        if representation not in available:
            raise ContractError("source_representation_unavailable", detail={
                "representation": representation, "available_representations": available})
        selected_ref = source[representation + "_ref"]
    else:
        representation = "text" if representation == "text" and source.get("text_ref") else "original"
        selected_ref = source["text_ref"] if representation == "text" else source["artifact_ref"]
    artifact = store.get(selected_ref)
    if type(offset) is not int or not 0 <= offset <= artifact["size"] or type(limit) is not int or limit < 1:
        raise ContractError("source_offset_out_of_bounds")
    with artifact_path(store, artifact["id"]).open("rb") as handle:
        handle.seek(offset)
        content = handle.read(limit)
    if content and content[0] & 0xC0 == 0x80:
        raise ContractError("source_offset_not_utf8_boundary")
    while content:
        try:
            text = content.decode("utf-8")
            break
        except UnicodeDecodeError as error:
            if error.reason != "unexpected end of data":
                raise ContractError("source_not_utf8_text") from error
            if error.start == 0:
                raise ContractError("source_window_too_small_for_character") from error
            content = content[:error.start]
    else:
        text = ""
    end = offset + len(content)
    next_offset = end if end < artifact["size"] else None
    return {"source_ref": source_ref, "artifact_ref": artifact["id"], "start": offset,
        "end": end, "text": text, "total_bytes": artifact["size"],
        "representation": representation,
        "available_representations": available,
        "next_offset": next_offset,
        "next_query": {"source_ref": source_ref, "representation": representation,
                       "offset": next_offset, "limit": limit} if next_offset is not None else None}


def read_member(store, member_ref, *, offset=0, limit=12000):
    member = store._require(member_ref, {"collection_member"})
    if type(offset) is not int or not 0 <= offset <= member["length"] or type(limit) is not int or limit < 1:
        raise ContractError("invalid_member_window")
    end = min(offset + limit, member["length"])
    def window(component):
        data = packing.component_window(store, member, component, offset, end-offset)
        return data.decode("ascii") if data is not None else None
    return {"member": member_preview(store, member), "start": offset, "end": end, "sequence": window("sequence"),
        "quality": window("quality"), "next_offset": end if end < member["length"] else None}


def read_header(store, member_ref, *, offset=0, limit=12000):
    """Read the exact parser-returned title; never assert original byte offsets."""
    member = store._require(member_ref, {"collection_member"})
    size = packing.component_info(store, member, "header")["bytes"]
    if type(offset) is not int or not 0 <= offset <= size or type(limit) is not int or limit < 1:
        raise ContractError("invalid_header_window")
    content = packing.component_window(store, member, "header", offset, limit)
    if content and content[0] & 0xC0 == 0x80:
        raise ContractError("header_offset_not_utf8_boundary")
    while content:
        try:
            text = content.decode("utf-8")
            break
        except UnicodeDecodeError as error:
            if error.reason != "unexpected end of data":
                raise ContractError("header_not_utf8_text") from error
            if error.start == 0:
                raise ContractError("header_window_too_small_for_character") from error
            content = content[:error.start]
    else:
        text = ""
    end = offset + len(content)
    next_offset = end if end < size else None
    header_ref = packing.materialize(store, member, ("header",))["header"]
    return {"member_ref": member_ref, "material_ref": member["material_ref"],
        "collection_ref": member["collection_ref"], "source_ref": member["source_ref"],
        "artifact_ref": header_ref, "parser_version": member["parser_version"],
        "representation": member["header_representation"], "original_header_bytes": False,
        "ordinal": member["ordinal"], "start": offset, "end": end, "text": text,
        "total_bytes": size, "next_offset": next_offset,
        "next_query": {"member_ref": member_ref, "offset": next_offset, "limit": limit}
                      if next_offset is not None else None}


def member_reference(store, member_ref):
    member = store._require(member_ref, {"collection_member"})
    refs = packing.materialize(store, member)
    collection = store.get(member["collection_ref"])
    context = store.put("context", {"context_type": "collection", "name": store.get(member["material_ref"])["name"],
        "source_ref": member["source_ref"], "attributes": [], "related_refs": [collection["id"]]}, origin="tool")
    return store.put("reference", {"reference_type": member["molecule"] if member["molecule"] != "unspecified" else "sequence",
        "source_ref": member["source_ref"], "accession": member["id"], "label": member["name"][:512],
        "label_is_preview": len(member["name"]) > 512,
        "label_full_characters": len(member["name"]), "label_full_utf8_bytes": len(member["name"].encode("utf-8")),
        "sequence_ref": refs["sequence"], "molecule": member["molecule"], "length": member["length"],
        "term_refs": [], "context_refs": [context["id"], *[ref for ref in (collection["sample_ref"], collection["library_ref"]) if ref]],
        "member_ref": member_ref}, origin="tool")


def create_problem(store, input_path=None, *, raw_sequence=None, molecule="unspecified", role="unspecified",
        manifest_path=None, caller_context=None, format="auto"):
    if store.db.execute("SELECT 1 FROM problem").fetchone():
        raise ContractError("problem_already_exists")
    if sum(value is not None for value in (input_path, raw_sequence, manifest_path)) != 1:
        raise ContractError("choose_one_input_source")
    entries, feedback = [], []
    manifest_ref, manifest_source = None, None
    base = Path.cwd()
    if manifest_path is not None:
        path = Path(manifest_path).resolve()
        # Custody is committed before JSON or sequence interpretation.
        with store.transaction():
            manifest_ref = artifact_file(store, path, "application/json")
            manifest_source = source_for_artifact(store, manifest_ref, uri=path.as_uri())
        base = path.parent
        try:
            manifest = json.loads(store.get_artifact(manifest_ref))
            if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "entries"}
                    or manifest["schema_version"] not in {1, 2} or not isinstance(manifest["entries"], list)):
                raise ValueError()
            entries = manifest["entries"]
        except (ValueError, UnicodeError):
            feedback.append({"entry_index": None, "code": "invalid_manifest_structure"})
    else:
        entry = {"path": str(Path(input_path).resolve())} if input_path is not None else {"sequence": raw_sequence}
        entry.update(molecule=molecule, role=role, format="raw" if raw_sequence is not None else format, name="input")
        entries = [entry]
    materials, attempts, collections, subjects = [], [], [], []
    by_name, pending_links, library_groups = {}, [], {}
    for entry_index, entry in enumerate(entries):
        allowed = {"path", "sequence", "molecule", "role", "format", "name", "sample", "context", "use",
                   "library", "links", "quality_encoding", "target_records"}
        if not isinstance(entry, dict) or set(entry)-allowed or ("path" in entry) == ("sequence" in entry):
            feedback.append({"entry_index": entry_index, "code": "invalid_manifest_entry"})
            continue
        arguments = {key: entry[key] for key in ("name", "use", "molecule", "role", "sample", "library", "context", "quality_encoding") if key in entry}
        arguments.setdefault("use", "target")
        arguments["format"] = entry.get("format", "raw" if "sequence" in entry else "auto")
        try:
            if "path" in entry:
                path = Path(entry["path"])
                material = register_material(store, path if path.is_absolute() else base/path, **arguments)
            else:
                material = register_material(store, data=entry["sequence"], **arguments)
        except (ContractError, OSError, TypeError) as exc:
            feedback.append({"entry_index": entry_index, "code": str(exc) if isinstance(exc, ContractError) else "material_source_unavailable"})
            continue
        materials.append(material["id"])
        by_name.setdefault(material["name"], []).append(material["id"])
        pending_links.append((material, entry.get("links", []), entry_index))
        attempt = parse_material(store, material["id"])
        attempts.append(attempt["id"])
        if attempt["status"] != "completed":
            feedback.append({"entry_index": entry_index, "code": attempt["code"], "parse_ref": attempt["id"]})
        if attempt["collection_ref"] is None:
            continue
        collections.append(attempt["collection_ref"])
        if material["use"] != "target":
            continue
        selected = entry.get("target_records")
        if selected is not None and (not isinstance(selected, list) or not selected
                or any(type(n) is not int or n < 0 for n in selected)):
            feedback.append({"entry_index": entry_index, "code": "invalid_target_record_selection"})
            continue
        collection = store.get(attempt["collection_ref"])
        if selected is None and (collection["representation"] == "fastq" or (material["role"] == "read" and collection["representation"] != "raw")):
            grouping = material["library_ref"] or collection["id"]
            library_groups.setdefault(grouping, []).append(collection["id"])
            continue
        parameters = [collection["id"]]
        where = "collection_ref=?"
        if selected is not None:
            selected = list(dict.fromkeys(selected))
            where += " AND ordinal IN (" + ",".join("?" for _ in selected) + ")"
            parameters.extend(selected)
        found = set()
        with store.transaction():
            for row in store.db.execute("SELECT data FROM material_members WHERE " + where + " ORDER BY ordinal", parameters):
                member = json.loads(row[0])
                selected_components = packing.materialize(store, member)
                found.add(member["ordinal"])
                record = {"name": member["name"], "description": member["description"], "molecule": material["molecule"],
                    "role": material["role"], "length": member["length"], "unit": store._unit(material["molecule"]),
                    "sequence_ref": selected_components["sequence"], "source_ref": member["source_ref"],
                    "source_record": {"material_ref": material["id"], "member_ref": member["id"],
                        "identifier": member["name"], "occurrence": member["occurrence"], "ordinal": member["ordinal"]},
                    "input_issues": member["issues"], "sample_ref": material["sample_ref"],
                    "context_source_refs": material["context_source_refs"]}
                ref = identity("input", record)
                record.update(id=ref, record_type="input", origin="caller")
                store.db.execute("INSERT OR IGNORE INTO inputs VALUES(?,?)", (ref, canonical(record)))
                subjects.append(ref)
        if selected is not None and set(selected)-found:
            feedback.append({"entry_index": entry_index, "code": "selected_target_record_unavailable"})
    for group in library_groups.values():
        library = libraries.bind(store, group)
        subjects.append(library["id"])
    for material, links, entry_index in pending_links:
        for link in links if isinstance(links, list) else [None]:
            if (not isinstance(link, dict) or set(link) != {"relation", "name"}
                    or not isinstance(link.get("name"), str)
                    or len(by_name.get(link.get("name"), [])) != 1):
                feedback.append({"entry_index": entry_index, "code": "unresolved_declared_material_link"})
                continue
            try:
                store.put("material_link", {"source_ref": manifest_source["id"] if manifest_source else material["source_ref"],
                    "left_ref": material["id"], "right_ref": by_name[link["name"]][0], "relation": link["relation"]}, origin="caller")
            except ContractError:
                feedback.append({"entry_index": entry_index, "code": "invalid_declared_material_link"})
    context = store._caller_source(caller_context, "caller_context") if caller_context is not None else None
    # Repeated requests for the same semantic input reuse its durable row.
    # Preserve every supplied manifest occurrence while listing each fixed
    # annotation subject once; different source/declaration contexts have
    # different input identities and therefore remain distinct.
    subjects = list(dict.fromkeys(subjects))
    data = {"subject_refs": subjects, "material_refs": materials, "initial_parse_refs": attempts,
        "initial_collection_refs": collections, "manifest_ref": manifest_ref,
        "manifest_source_ref": manifest_source["id"] if manifest_source else None,
        "caller_context_ref": context["artifact_ref"] if context else None,
        "caller_context_source_ref": context["id"] if context else None,
        "target_binding": ("fixed_original_read_libraries_and_sequences" if library_groups else "sequence_targets") if subjects else "unresolved",
        "target_binding_versions": {"read_libraries": libraries.VERSION} if library_groups else {},
        "intake_status": "partial" if feedback else "completed", "intake_feedback": feedback}
    data["id"] = identity("problem", data)
    with store.transaction():
        store.db.execute("INSERT INTO problem VALUES(1,?)", (canonical(data),))
    return data
