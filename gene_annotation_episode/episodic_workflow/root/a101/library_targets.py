"""Fixed original read membership and lazy read-local scientific subjects.

The library is a data target, never a biological sequence or organism. Its
position measure is disjoint original member-local symbols, not joined bases,
unique genes, independent molecules or recovered genome completeness.
"""
from __future__ import annotations

import hashlib
import json

from .domain import ContractError, canonical, identity
from . import materials_packing as packing

VERSION = "fixed_original_read_position_measure_v1"


def install_tables(store):
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS library_selection_members(
            selection_ref TEXT NOT NULL,read_ref TEXT NOT NULL,
            PRIMARY KEY(selection_ref,read_ref));
    """)


def is_library(row):
    return row.get("record_type") == "input" and row.get("target_kind") == "read_library"


def bind(store, collection_refs):
    """Initialization only: freeze actual parsed membership without loading it.

    A shared caller library declaration may group files, but supplies no pairing,
    organism or common-sample inference. The same collection occurs only once.
    Valid parsed members of a partial input form an explicitly partial binding.
    """
    collections = [store._require(ref, {"collection"}) for ref in dict.fromkeys(collection_refs)]
    if not collections:
        raise ContractError("library_requires_original_collection")
    declared = {row["library_ref"] for row in collections}
    if len(collections) > 1 and (None in declared or len(declared) != 1):
        raise ContractError("library_group_requires_same_caller_declaration")
    materials = [store.get(row["material_ref"]) for row in collections]
    if any(row["use"] != "target" or row["origin"] != "caller" for row in materials):
        raise ContractError("library_binding_requires_caller_target_material")
    digest, count, mass = hashlib.sha256(), 0, 0
    for collection in collections:
        for (raw,) in store.db.execute("SELECT data FROM material_members WHERE collection_ref=? ORDER BY ordinal", (collection["id"],)):
            member = json.loads(raw)
            unit = store._unit(member["molecule"])
            digest.update((canonical({"member_ref": member["id"], "length": member["length"], "unit": unit}) + "\n").encode())
            count += 1
            mass += member["length"]
    if not count:
        raise ContractError("library_has_no_indexed_original_members")
    molecules = {row["molecule"] for row in collections}
    record = {"target_kind": "read_library", "binding_version": VERSION,
        "name": store.get(next(iter(declared)))["name"] if next(iter(declared)) is not None else materials[0]["name"],
        "molecule": next(iter(molecules)) if len(molecules) == 1 else "unspecified", "role": "read",
        "collection_refs": [row["id"] for row in collections],
        "material_refs": [row["id"] for row in materials],
        "source_refs": sorted({row["source_ref"] for row in collections}),
        "declared_library_ref": next(iter(declared)),
        "sample_refs": sorted({row["sample_ref"] for row in collections if row["sample_ref"]}),
        "context_source_refs": sorted({ref for row in materials for ref in row["context_source_refs"]}),
        "member_count": count, "position_mass": mass, "membership_sha256": digest.hexdigest(),
        "complete_file_membership": all(row["complete"] for row in collections),
        "measure": "original_member_local_position_mass_not_unique_genes_or_genome_completeness",
        "coordinate_system": "library_original_member_local_zero_based_half_open",
        "sequence_ref": None}
    ref = identity("input", record)
    record.update(id=ref, record_type="input", origin="caller")
    with store.transaction():
        store.db.execute("INSERT OR IGNORE INTO inputs VALUES(?,?)", (ref, canonical(record)))
    return record


def read_ref(library_ref, member_ref):
    # Existing content identities are 24 hex digits. Their pair fits the closed
    # persistent-ref syntax without a second row/file for each original read.
    if not library_ref.startswith("input_") or not member_ref.startswith("member_"):
        raise ContractError("invalid_original_read_identity")
    return "read_subject_" + library_ref[6:] + member_ref[7:]


def resolve(store, reference):
    if not reference.startswith("read_subject_") or len(reference) != 61:
        return None
    suffix = reference[len("read_subject_"):]
    if any(char not in "0123456789abcdef" for char in suffix):
        return None
    library_ref, member_ref = "input_" + suffix[:24], "member_" + suffix[24:]
    try:
        target, member = store.get_input(library_ref), store.get(member_ref)
    except ContractError:
        return None
    if not is_library(target) or member.get("collection_ref") not in target["collection_refs"]:
        return None
    before = target["collection_refs"][:target["collection_refs"].index(member["collection_ref"])]
    ordinal = sum(store.get(ref)["member_count"] for ref in before)
    ordinal += store.db.execute("SELECT count(*) FROM material_members WHERE collection_ref=? AND ordinal<?",
        (member["collection_ref"], member["ordinal"])).fetchone()[0]
    return {"id": reference, "record_type": "read_subject", "origin": "caller",
        "library_ref": library_ref, "member_ref": member_ref,
        "ordinal": ordinal, "source_ordinal": member["ordinal"],
        "name": member["name"], "description": member["description"],
        "molecule": member["molecule"], "role": "read", "length": member["length"], "unit": store._unit(member["molecule"]),
        "source_ref": member["source_ref"], "collection_ref": member["collection_ref"],
        "material_ref": member["material_ref"],
        "sequence_ref": None, "quality_encoding": member["quality_encoding"],
        "quality_present": packing.component_info(store, member, "quality") is not None,
        "binding_version": VERSION}


def _rows(store, library_ref):
    target = store.get_input(library_ref)
    for collection_ref in target["collection_refs"]:
        for (data,) in store.db.execute("SELECT data FROM material_members WHERE collection_ref=? ORDER BY ordinal", (collection_ref,)):
            yield json.loads(data)


def _query(target):
    # The native member index remains the membership authority. This relational
    # view adds no original-read registry. SQL may scan/sort on disk for an
    # explicitly selected range; that is not a memory/throughput claim.
    return """WITH native AS (
        SELECT m.id AS member_ref,json_extract(m.data,'$.length') AS length,
        CASE json_extract(m.data,'$.molecule') WHEN 'protein' THEN 'aa'
          WHEN 'dna' THEN 'nt' WHEN 'rna' THEN 'nt' ELSE 'symbol' END AS unit,
        row_number() OVER (ORDER BY cast(c.key AS integer),m.ordinal)-1 AS ordinal
        FROM material_members m JOIN json_each(?) c ON m.collection_ref=c.value)
        SELECT *, 'read_subject_' || ? || substr(member_ref,8) AS read_ref FROM native""", [canonical(target["collection_refs"]), target["id"][6:]]


def span(store, value):
    """Validate one physical original-position span without implicit expansion."""
    if not isinstance(value, dict) or not {"target_ref", "start", "end", "unit"} <= set(value) <= {"target_ref", "member_ref", "start", "end", "unit"}:
        raise ContractError("invalid_original_span")
    target = store.get_input(value["target_ref"])
    if is_library(target):
        if "member_ref" not in value:
            raise ContractError("library_span_requires_original_member")
        native = store._require(value["member_ref"], {"collection_member"})
        if native["collection_ref"] not in target["collection_refs"]:
            raise ContractError("member_not_in_fixed_library")
        length, unit = native["length"], store._unit(native["molecule"])
    else:
        if "member_ref" in value:
            raise ContractError("scalar_input_span_has_no_member_dimension")
        length, unit = target["length"], target["unit"]
    if (type(value["start"]) is not int or type(value["end"]) is not int
            or not 0 <= value["start"] < value["end"] <= length or value["unit"] != unit):
        raise ContractError("span_outside_original_member_or_input")
    return target


def key(value):
    return value["target_ref"], value.get("member_ref"), value["unit"]


def selection_for(store, scope, library_ref):
    for ref in scope.get("read_selection_refs", ()):
        row = store.get(ref)
        if row["library_ref"] == library_ref:
            return row
    return None


def contains(store, scope, value):
    if value["target_ref"] not in scope["subject_refs"]:
        return False
    if "segments" in scope:
        return store._covered_by([value], scope["segments"])
    selected = selection_for(store, scope, value["target_ref"])
    if selected is None:
        return True
    return store.db.execute("SELECT 1 FROM library_selection_members WHERE selection_ref=? AND read_ref=?",
        (selected["id"], read_ref(value["target_ref"], value["member_ref"]))).fetchone() is not None


def member_page(store, library_ref, *, selection_ref=None, offset=0, limit=50, scope=None):
    target = store.get_input(library_ref)
    if not is_library(target):
        raise ContractError("read_library_target_required")
    normalized = store.validate_scope(scope)
    if library_ref not in normalized["subject_refs"]:
        raise ContractError("library_outside_assigned_scope")
    if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 1:
        raise ContractError("invalid_page")
    selected = store._require(selection_ref, {"read_selection"}) if selection_ref else selection_for(store, normalized, library_ref)
    if selected and selected["library_ref"] != library_ref:
        raise ContractError("selection_library_mismatch")
    base_query, parameters = _query(target)
    clauses = ["1"]
    for chosen in {row["id"] for row in (selected, selection_for(store, normalized, library_ref)) if row}:
        clauses.append("EXISTS (SELECT 1 FROM library_selection_members s WHERE s.selection_ref=? AND s.read_ref=n.read_ref)")
        parameters.append(chosen)
    if "segments" in normalized:
        members = sorted({row["member_ref"] for row in normalized["segments"] if row["target_ref"] == library_ref})
        clauses.append("n.member_ref IN (SELECT value FROM json_each(?))")
        parameters.append(canonical(members))
    where = " AND ".join(clauses)
    query = "SELECT * FROM (" + base_query + ") n WHERE " + where
    total = store.db.execute("SELECT count(*) FROM (" + query + ")", parameters).fetchone()[0]
    refs = store.db.execute("SELECT read_ref FROM (" + query + ") ORDER BY ordinal LIMIT ? OFFSET ?", (*parameters, limit, offset))
    rows = [resolve(store, row[0]) for row in refs]
    # Native labels are not automatically unbounded model context.
    from .materials import model_record_view
    next_offset = offset + len(rows) if offset + len(rows) < total else None
    return {"library_ref": library_ref, "selection_ref": selected["id"] if selected else None,
        "members": [model_record_view(store, row) for row in rows], "total": total,
        "offset": offset, "limit": limit, "next_offset": next_offset,
        "next_query": {"library_ref": library_ref, **({"selection_ref": selected["id"]} if selected else {}),
            "offset": next_offset, "limit": limit} if next_offset is not None else None}


def select(store, library_ref, *, member_refs=None, ordinal_ranges=None, scope=None):
    """Freeze an owner's explicit original-member selection, without discovery."""
    target = store.get_input(library_ref)
    if not is_library(target):
        raise ContractError("read_library_target_required")
    normalized = store.validate_scope(scope)
    if library_ref not in normalized["subject_refs"]:
        raise ContractError("library_outside_assigned_scope")
    if (member_refs is None) == (ordinal_ranges is None):
        raise ContractError("choose_original_members_or_ordinal_ranges")
    base_query, parameters = _query(target)
    if member_refs is not None:
        if not isinstance(member_refs, list) or not member_refs or not all(isinstance(ref, str) for ref in member_refs):
            raise ContractError("invalid_member_selection")
        requested = sorted(set(member_refs))
        condition = "member_ref IN (SELECT value FROM json_each(?))"
        parameters.append(canonical(requested))
    else:
        if not isinstance(ordinal_ranges, list) or not ordinal_ranges or any(not isinstance(row, dict)
            or set(row) != {"start", "end"} or type(row["start"]) is not int or type(row["end"]) is not int
            or not 0 <= row["start"] < row["end"] <= target["member_count"] for row in ordinal_ranges):
            raise ContractError("invalid_library_ordinal_range")
        condition = "EXISTS (SELECT 1 FROM json_each(?) x WHERE n.ordinal>=json_extract(x.value,'$.start') AND n.ordinal<json_extract(x.value,'$.end'))"
        parameters.append(canonical(ordinal_ranges))
        requested = None
    query = "SELECT n.* FROM (" + base_query + ") n WHERE (" + condition + ") ORDER BY ordinal"
    digest, count, mass = hashlib.sha256(), 0, 0
    for row in store.db.execute(query, parameters):
        value = {"target_ref": library_ref, "member_ref": row["member_ref"], "start": 0, "end": row["length"], "unit": row["unit"]}
        if not contains(store, normalized, value):
            raise ContractError("selected_member_outside_assigned_scope")
        digest.update((row["read_ref"] + "\n").encode())
        count += 1
        mass += row["length"]
    if not count or requested is not None and count != len(requested):
        raise ContractError("selected_member_not_in_fixed_library")
    record = {"library_ref": library_ref, "binding_version": VERSION,
        "member_count": count, "position_mass": mass, "membership_sha256": digest.hexdigest()}
    with store.transaction():
        selected = store.put("read_selection", record, origin="tool", scope=normalized)
        store.db.executemany("INSERT OR IGNORE INTO library_selection_members VALUES(?,?)",
            ((selected["id"], row["read_ref"]) for row in store.db.execute(query, parameters)))
    return selected


def iter_eligible(store, scope, target_ref=None):
    """Stream exact fixed geometry, preserving original member coordinates."""
    normalized = store.validate_scope(scope)
    if "segments" in normalized:
        yield from (dict(row) for row in normalized["segments"] if target_ref is None or row["target_ref"] == target_ref)
        return
    for ref in normalized["subject_refs"]:
        if target_ref is not None and ref != target_ref:
            continue
        target = store.get_input(ref)
        if not is_library(target):
            yield {"target_ref": ref, "start": 0, "end": target["length"], "unit": target["unit"]}
            continue
        selection = selection_for(store, normalized, ref)
        for member in _rows(store, ref):
            if selection and store.db.execute("SELECT 1 FROM library_selection_members WHERE selection_ref=? AND read_ref=?",
                    (selection["id"], read_ref(ref, member["id"]))).fetchone() is None:
                continue
            yield {"target_ref": ref, "member_ref": member["id"], "start": 0, "end": member["length"], "unit": store._unit(member["molecule"])}


def measure(store, scope, target_ref):
    normalized = store.validate_scope(scope)
    if target_ref not in normalized["subject_refs"]:
        raise ContractError("target_outside_scope")
    if "segments" in normalized:
        return sum(row["end"]-row["start"] for row in normalized["segments"] if row["target_ref"] == target_ref)
    target = store.get_input(target_ref)
    if not is_library(target):
        return target["length"]
    selection = selection_for(store, normalized, target_ref)
    return (selection or target)["position_mass"]


def validate_scope(store, scope=None, parent_scope=None):
    available = set(store.problem()["subject_refs"])
    if scope is None:
        scope = {"subject_refs": sorted(available)}
    if (not isinstance(scope, dict) or not {"subject_refs"} <= set(scope) <= {"subject_refs", "segments", "read_selection_refs"}
            or not isinstance(scope["subject_refs"], list) or not all(isinstance(ref, str) for ref in scope["subject_refs"])):
        raise ContractError("invalid_scope")
    selected = set(scope["subject_refs"])
    if (not selected and available) or len(selected) != len(scope["subject_refs"]) or not selected <= available:
        raise ContractError("unknown_or_empty_scope")
    result = {"subject_refs": sorted(selected)}
    if "read_selection_refs" in scope:
        refs = scope["read_selection_refs"]
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs) or len(set(refs)) != len(refs):
            raise ContractError("invalid_read_selection_scope")
        libraries = set()
        for ref in refs:
            choice = store._require(ref, {"read_selection"})
            if choice["library_ref"] not in selected or choice["library_ref"] in libraries:
                raise ContractError("selection_library_outside_scope_or_repeated")
            libraries.add(choice["library_ref"])
        result["read_selection_refs"] = sorted(refs)
    if "segments" in scope:
        segments = scope["segments"]
        if not isinstance(segments, list) or not segments:
            raise ContractError("invalid_scope_segments")
        for value in segments:
            try:
                span(store, value)
            except ContractError as exc:
                raise ContractError("scope_segment_outside_input", detail={"cause_code": str(exc)}) from exc
            if not contains(store, result, value):
                raise ContractError("scope_segment_outside_selected_members")
        if {row["target_ref"] for row in segments} != selected:
            raise ContractError("scope_subject_without_segment")
        result["segments"] = store._merge_segments(segments)
    if parent_scope is not None:
        parent = validate_scope(store, parent_scope)
        if not selected <= set(parent["subject_refs"]):
            raise ContractError("scope_outside_parent")
        if "segments" in parent:
            for value in iter_eligible(store, result):
                if not contains(store, parent, value):
                    raise ContractError("scope_segments_outside_parent")
        else:
            # Explicit intervals can be tested directly. Full selected-member
            # scopes compare the immutable selection index in SQL, not Python.
            if "segments" in result:
                if not all(contains(store, parent, value) for value in result["segments"]):
                    raise ContractError("scope_segments_outside_parent")
            else:
                for ref in selected:
                    parent_selection = selection_for(store, parent, ref)
                    if parent_selection is None:
                        continue
                    child_selection = selection_for(store, result, ref)
                    if child_selection is None:
                        if parent_selection["member_count"] != store.get_input(ref)["member_count"]:
                            raise ContractError("scope_members_outside_parent")
                    elif store.db.execute("SELECT read_ref FROM library_selection_members WHERE selection_ref=? EXCEPT SELECT read_ref FROM library_selection_members WHERE selection_ref=? LIMIT 1",
                            (child_selection["id"], parent_selection["id"])).fetchone():
                        raise ContractError("scope_members_outside_parent")
    return result


def footprint_dimension(store, value):
    target = span(store, value)
    if is_library(target):
        ref = read_ref(target["id"], value["member_ref"])
        row = resolve(store, ref)
        return {"id": ref, "target_ref": target["id"], "member_ref": row["member_ref"],
            "length": row["length"], "unit": row["unit"]}
    return {"id": target["id"], "target_ref": target["id"], "length": target["length"], "unit": target["unit"]}


def dimension_segments(store, scope, dimension_ref):
    normalized = store.validate_scope(scope)
    row = store.get(dimension_ref)
    if row["record_type"] == "read_subject":
        value = {"target_ref": row["library_ref"], "member_ref": row["member_ref"],
            "start": 0, "end": row["length"], "unit": row["unit"]}
    elif row["record_type"] == "input" and not is_library(row):
        value = {"target_ref": row["id"], "start": 0, "end": row["length"], "unit": row["unit"]}
    else:
        raise ContractError("original_scalar_or_read_dimension_required")
    if value["target_ref"] not in normalized["subject_refs"]:
        return []
    if "segments" in normalized:
        return [{"start": part["start"], "end": part["end"]} for part in normalized["segments"] if key(part) == key(value)]
    return [{"start": 0, "end": row["length"]}] if contains(store, normalized, value) else []
