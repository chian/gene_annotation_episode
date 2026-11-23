"""Private received sequence extraction for A107."""
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sequence_views import view_sequence


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


REPRESENTATION = "packed_member_components"


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
    """Yield only the selected component bytes, in bounded windows read through the store."""
    info = component_info(store, member, component)
    if info is None:
        return
    end = info["bytes"] if limit is None else min(info["bytes"], offset + limit)
    if not packed(member):
        with store.open_artifact(member[component + "_ref"]) as handle:
            handle.seek(offset)
            remaining = max(0, end-offset)
            while remaining:
                data = handle.read(min(65536, remaining))
                if not data:
                    raise ContractError("material_component_size_mismatch")
                remaining -= len(data)
                yield data
        return
    cursor = offset
    while cursor < end:
        window = store.material_member(member["id"], offset=cursor, limit=min(65536, end-cursor))
        data = window[component].encode("ascii")
        if not data:
            raise ContractError("material_component_size_mismatch")
        cursor += len(data)
        yield data


def component_window(store, member, component, offset, limit):
    if component_info(store, member, component) is None:
        return None
    return b"".join(component_chunks(store, member, component, offset=offset, limit=limit))

