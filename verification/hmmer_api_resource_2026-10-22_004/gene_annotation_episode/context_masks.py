"""Semantic sets of fixed original material positions, never sequence mappings.

Episode scopes keep their separate nonempty/one-selection contract. Context masks
may union frozen selection handles and explicitly allocate nothing. The native
member index is authoritative; no eager read subject inventory is constructed.
"""
from __future__ import annotations
import hashlib
from .domain import ContractError, canonical
from . import library_targets as libraries

VERSION = "fixed_original_position_set_v1"
FIELDS = {"subject_refs", "read_selection_refs", "segments"}


def normalize(store, mask):
    if (not isinstance(mask, dict) or not {"subject_refs"} <= set(mask) <= FIELDS
            or not isinstance(mask["subject_refs"], list)
            or any(not isinstance(ref, str) for ref in mask["subject_refs"])):
        raise ContractError("invalid_context_mask")
    targets = sorted(set(mask["subject_refs"]))
    if not set(targets) <= set(store.problem()["subject_refs"]):
        raise ContractError("context_mask_unknown_original_target")
    if not targets:
        if set(mask) != {"subject_refs"}:
            raise ContractError("empty_context_mask_has_no_selection_or_segments")
        return {"subject_refs": []}
    result = {"subject_refs": targets}
    if "read_selection_refs" in mask:
        refs = mask["read_selection_refs"]
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
            raise ContractError("invalid_context_selection_union")
        for ref in refs:
            choice = store._require(ref, {"read_selection"})
            if choice["library_ref"] not in targets:
                raise ContractError("context_selection_outside_target")
        result["read_selection_refs"] = sorted(set(refs))
    if "segments" in mask:
        if not isinstance(mask["segments"], list) or not mask["segments"]:
            raise ContractError("invalid_context_mask_segments")
        for value in mask["segments"]:
            libraries.span(store, value)
            if value["target_ref"] not in targets:
                raise ContractError("context_segment_outside_target")
            selected = _selections(store, result, value["target_ref"])
            if selected and not store.db.execute("SELECT 1 FROM library_selection_members WHERE selection_ref IN (SELECT value FROM json_each(?)) AND read_ref=? LIMIT 1",
                    (canonical(selected), libraries.read_ref(value["target_ref"], value["member_ref"]))).fetchone():
                raise ContractError("context_segment_outside_selection_union")
        if {row["target_ref"] for row in mask["segments"]} != set(targets):
            raise ContractError("context_target_without_segment")
        result["segments"] = store._merge_segments(mask["segments"])
    return result


def _selections(store, mask, target_ref):
    return [ref for ref in mask.get("read_selection_refs", ()) if store.get(ref)["library_ref"] == target_ref]


def target_query(store, mask, target_ref):
    """Lazy relational disjoint intervals; caller controls streaming/paging.

    Columns: target_ref,member_ref,dimension_ref,read_ref,length,unit,start,end.
    No query is executed here and no lazy scientific subject is materialized.
    """
    mask = normalize(store, mask)
    if target_ref not in mask["subject_refs"]:
        return "SELECT NULL target_ref,NULL member_ref,NULL dimension_ref,NULL read_ref,0 length,NULL unit,0 start,0 end WHERE 0", []
    target = store.get_input(target_ref)
    spans = [row for row in mask.get("segments", ()) if row["target_ref"] == target_ref]
    if not libraries.is_library(target):
        rows = spans or [{"start": 0, "end": target["length"]}]
        return "SELECT ? target_ref,NULL member_ref,? dimension_ref,? read_ref,? length,? unit,json_extract(j.value,'$.start') start,json_extract(j.value,'$.end') end FROM json_each(?) j", [target_ref,target_ref,target_ref,target["length"],target["unit"],canonical(rows)]
    native = "SELECT ? target_ref,m.id member_ref,'read_subject_' || ? || substr(m.id,8) dimension_ref,'read_subject_' || ? || substr(m.id,8) read_ref,json_extract(m.data,'$.length') length,CASE json_extract(m.data,'$.molecule') WHEN 'protein' THEN 'aa' WHEN 'dna' THEN 'nt' WHEN 'rna' THEN 'nt' ELSE 'symbol' END unit FROM material_members m WHERE m.collection_ref IN (SELECT value FROM json_each(?))"
    params = [target_ref,target_ref[6:],target_ref[6:],canonical(target["collection_refs"])]
    if spans:
        return "SELECT n.*,json_extract(j.value,'$.start') start,json_extract(j.value,'$.end') end FROM ("+native+") n JOIN json_each(?) j ON n.member_ref=json_extract(j.value,'$.member_ref')", params+[canonical(spans)]
    choices = _selections(store, mask, target_ref)
    sql = "SELECT n.*,0 start,length end FROM ("+native+") n"
    if choices:
        sql += " WHERE EXISTS (SELECT 1 FROM library_selection_members s WHERE s.selection_ref IN (SELECT value FROM json_each(?)) AND s.read_ref=n.read_ref)"
        params.append(canonical(choices))
    return sql, params


def target_full(store, mask, target_ref):
    mask = normalize(store, mask)
    if target_ref not in mask["subject_refs"]:
        return False
    if "segments" not in mask and not _selections(store, mask, target_ref):
        return True
    target = store.get_input(target_ref)
    sql, params = target_query(store, mask, target_ref)
    measured = store.db.execute("SELECT coalesce(sum(end-start),0) FROM ("+sql+")",params).fetchone()[0]
    return measured == (target["position_mass"] if libraries.is_library(target) else target["length"])


def measure(store, mask, target_ref):
    mask = normalize(store, mask)
    if target_ref not in mask["subject_refs"]:
        return 0
    target = store.get_input(target_ref)
    if "segments" not in mask and not _selections(store, mask, target_ref):
        return target["position_mass"] if libraries.is_library(target) else target["length"]
    sql, params = target_query(store, mask, target_ref)
    return store.db.execute("SELECT coalesce(sum(end-start),0) FROM ("+sql+")", params).fetchone()[0]


def identity_digest(store, mask):
    mask = normalize(store, mask)
    digest = hashlib.sha256((VERSION+"\n").encode())
    for ref in mask["subject_refs"]:
        if target_full(store, mask, ref):
            digest.update((canonical({"target_ref":ref,"kind":"full_target"})+"\n").encode())
            continue
        digest.update((canonical({"target_ref":ref,"kind":"position_set"})+"\n").encode())
        sql, params = target_query(store, mask, ref)
        for row in store.db.execute("SELECT member_ref,unit,start,end FROM ("+sql+") ORDER BY coalesce(member_ref,''),unit,start,end",params):
            digest.update((canonical(dict(row))+"\n").encode())
    return digest.hexdigest()


def subset(store, left, right):
    left, right = normalize(store,left), normalize(store,right)
    for ref in left["subject_refs"]:
        if ref not in right["subject_refs"]:
            return False
        if target_full(store,right,ref):
            continue
        if target_full(store,left,ref):
            return False
        ls, lp = target_query(store,left,ref); rs,rp = target_query(store,right,ref)
        if store.db.execute("SELECT 1 FROM ("+ls+") l WHERE NOT EXISTS (SELECT 1 FROM ("+rs+") r WHERE r.member_ref IS l.member_ref AND r.unit=l.unit AND r.start<=l.start AND l.end<=r.end) LIMIT 1",lp+rp).fetchone():
            return False
    return True


def overlap(store, left, right):
    left,right=normalize(store,left),normalize(store,right)
    for ref in set(left["subject_refs"]) & set(right["subject_refs"]):
        if target_full(store,left,ref) or target_full(store,right,ref):
            return True
        ls,lp=target_query(store,left,ref); rs,rp=target_query(store,right,ref)
        if store.db.execute("SELECT 1 FROM ("+ls+") l JOIN ("+rs+") r ON r.member_ref IS l.member_ref AND r.unit=l.unit AND max(l.start,r.start)<min(l.end,r.end) LIMIT 1",lp+rp).fetchone():
            return True
    return False


def dimension_segments(store, mask, dimension_ref):
    mask=normalize(store,mask)
    row=store.get(dimension_ref)
    if row["record_type"] == "read_subject":
        target_ref,member_ref=row["library_ref"],row["member_ref"]
    elif row["record_type"] == "input" and not libraries.is_library(row):
        target_ref,member_ref=row["id"],None
    else:
        raise ContractError("original_scalar_or_read_dimension_required")
    if target_ref not in mask["subject_refs"]:
        return []
    if "segments" in mask:
        return [{"start":part["start"],"end":part["end"]} for part in mask["segments"] if part["target_ref"]==target_ref and part.get("member_ref")==member_ref]
    selected=_selections(store,mask,target_ref)
    if selected and not store.db.execute("SELECT 1 FROM library_selection_members WHERE selection_ref IN (SELECT value FROM json_each(?)) AND read_ref=? LIMIT 1",(canonical(selected),dimension_ref)).fetchone():
        return []
    return [{"start":0,"end":row["length"]}]
