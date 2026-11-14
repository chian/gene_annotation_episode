"""Private received sequence extraction for A107."""
from .domain import ContractError
import hashlib
from .sequence_views import view_sequence


def is_library(row):
    return row.get("record_type") == "input" and row.get("target_kind") == "read_library"


def sequence(store, reference: str, *, molecule_model: str | None = None) -> str:
    row = store.get(reference)
    if row.get("record_type") == "read_subject":
        member = store.get(row["member_ref"])
        return component_window(store, member, "sequence", 0, row["length"]).decode("ascii")
    if is_library(row):
        raise ContractError("library_is_not_a_sequence_operand")
    if row.get("sequence_ref"):
        return store.get_artifact(row["sequence_ref"]).decode("ascii")
    if row.get("record_type") == "feature":
        parent = sequence(store, row["subject_ref"], molecule_model=molecule_model)
        selected_sequence = "".join(parent[item["start"]:item["end"]] for item in row["segments"])
        if row["strand"] == "-":
            known_model = store.subject_molecule(row["subject_ref"])
            model = known_model if known_model != "unspecified" else molecule_model
            try:
                return view_sequence(selected_sequence, molecule=model, orientation="reverse_complement")["sequence"]
            except ValueError as error:
                raise ContractError(str(error)) from error
        return selected_sequence
    raise ContractError("referenced_record_has_no_sequence")


REPRESENTATION = "packed_member_components_v1"


def _verified_artifact_path(store, ref):
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


def component_chunks(store, member, component, *, offset=0, limit=None):
    """Yield only selected component bytes, verifying intersected bounded chunks."""
    info = component_info(store, member, component)
    if info is None:
        return
    end = info["bytes"] if limit is None else min(info["bytes"], offset + limit)
    if not packed(member):
        with _verified_artifact_path(store, member[component + "_ref"]).open("rb") as handle:
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
            with _verified_artifact_path(store, ref).open("rb") as handle:
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

