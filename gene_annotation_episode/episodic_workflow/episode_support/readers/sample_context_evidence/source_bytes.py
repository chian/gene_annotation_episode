"""Private A108 source-byte capture, digest verification and literal windows."""
import hashlib
import os
from pathlib import Path
import tempfile
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import ContractError


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
    """Verify retained byte identity only; callers own access authority."""
    artifact = store._require(ref, {"artifact"})
    path = store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != artifact["sha256"]:
        raise ContractError("artifact_digest_mismatch")
    return path


def source_window_selection(source, representation):
    """Select the existing representation using metadata, without opening bytes."""
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
    return selected_ref, representation, available


def _source_character_span(handle, offset):
    """Find the complete UTF-8 character containing an interior byte offset."""
    left = max(0, offset - 3)
    handle.seek(left)
    nearby = handle.read(7)
    position = offset - left
    start = position
    while start > 0 and nearby[start] & 0xC0 == 0x80:
        start -= 1
    first = nearby[start]
    width = (2 if 0xC2 <= first <= 0xDF else 3 if 0xE0 <= first <= 0xEF
             else 4 if 0xF0 <= first <= 0xF4 else 0)
    if not width or not start < position < start + width:
        return None
    try:
        nearby[start:start + width].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return left + start, left + start + width


def source_window(store, source_ref, *, offset=0, limit=12000, representation="text"):
    source = store._require(source_ref, {"source"})
    requested_representation = representation
    selected_ref, representation, available = source_window_selection(source, representation)
    artifact = store.get(selected_ref)
    if type(offset) is not int or not 0 <= offset <= artifact["size"] or type(limit) is not int or limit < 1:
        raise ContractError("source_offset_out_of_bounds")
    with artifact_path(store, artifact["id"]).open("rb") as handle:
        handle.seek(offset)
        content = handle.read(limit)
        if content and content[0] & 0xC0 == 0x80:
            span = _source_character_span(handle, offset)
            detail = {}
            if span is not None:
                start, end = span
                detail = {"source_ref": source_ref, "artifact_ref": artifact["id"],
                    "representation": representation, "requested_offset": offset,
                    "character_start": start, "character_end": end,
                    "retry_query": {"source_ref": source_ref, "representation": representation,
                        "offset": start, "limit": max(limit, end - start)}}
            # The selected read still fails; the caller chooses whether to
            # request the suggested window. No source text is returned here.
            raise ContractError("source_offset_not_utf8_boundary", detail=detail)
    while content:
        try:
            text = content.decode("utf-8")
            break
        except UnicodeDecodeError as error:
            if error.reason != "unexpected end of data":
                raise ContractError("source_not_utf8_text", detail={
                    "source_ref": source_ref, "artifact_ref": artifact["id"],
                    "requested_representation": requested_representation,
                    "representation": representation,
                    "available_representations": available,
                    "requested_offset": offset,
                    "invalid_byte_offset": offset + error.start,
                    "required_encoding": "utf-8"}) from error
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


