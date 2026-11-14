"""Explicit VDB function inputs and attributable, original-HSP measurements.

The frozen 338 contract and its validation addendum define this additive sheet.
Only population invokes the existing v1 calculator, exactly once. Validation
checks saved values and relations; it never parses or recalculates the v1 base.
No function weights, acquisition, resource decisions or annotation credit live
here. Source authentication remains the acquiring caller's responsibility.
"""
from __future__ import annotations

from copy import deepcopy as _deepcopy
import hashlib as _hashlib
import json as _json
import math as _math
import re as _re

from Bio.Data import CodonTable as _CodonTable
from Bio.Seq import Seq as _Seq

from . import blast_vdb_inputs as _v1
from . import blast_vdb_calculators as _base

__all__ = ["extract_blast_vdb_feature_function_assignments",
           "populate_blast_vdb_function_sheet", "validate_blast_vdb_function_sheet"]

_PREFIX = "blast_vdb_function_"
_SCHEMA = "blast_vdb_function_sheet_v2"
_FIELDS = "schema base_sheet base_components assignment_records dependency_records census_records entities observations link_results issues"
_REASONS = set((
    "base_source_unavailable base_source_conflict query_binding_unavailable "
    "member_origin_unavailable member_origin_ambiguous target_identity_unavailable "
    "target_identity_conflict assignment_scope_missing assignment_entity_conflict "
    "assignment_function_conflict assignment_namespace_unscored sample_assignment_not_query_function "
    "hsp_score_missing hsp_geometry_unavailable hsp_sequence_conflict hsp_not_contained_in_feature "
    "coding_witness_missing coding_witness_conflict hsp_codon_correspondence_unavailable "
    "dependency_relation_unresolved dependency_relation_conflict dependency_unknown "
    "census_missing census_partial census_unit_mismatch census_snapshot_mismatch "
    "census_filter_mismatch census_scope_mismatch census_annotation_snapshot_mismatch "
    "census_membership_unverified census_count_conflict census_function_missing census_zero_conflict "
    "native_output_partial linear_underflow kernel_arithmetic_out_of_range").split())
_CONFLICTS = {r for r in _REASONS if r.endswith(("conflict", "mismatch"))}
_CONFLICTS |= {"hsp_not_contained_in_feature"}
_ENTITY_FIELDS = ("entity_key address subject_rows member_binding_indices metadata_keys parent_sequence_identity "
                  "target_identity origin_status origin_sample_keys sample_relation_status eligible_hsp_rows assignment_keys issues")
_OBS_FIELDS = ("observation_key entity_key assignment_key function row_key source_locator native_bit_score native_evalue "
               "paired_query_units paired_reference_nt aligned_reference_nt attributable_reference_nt "
               "corresponding_feature_residues qualification reason_code base_component_pointer feature_component_pointer issues")


def _fail(code="record_fields_invalid"):
    raise ValueError(_PREFIX + code)


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and _math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _copy(v) for k, v in value.items()}
    _fail("finite_json_required")


def _keys(value, names, code="record_fields_invalid"):
    if type(value) is not dict or set(value) != set(names.split() if isinstance(names, str) else names):
        _fail(code)


def _str(value):
    if type(value) is not str or not value.strip():
        _fail()


def _int(value, minimum=0):
    if type(value) is not int or value < minimum:
        _fail()


def _num(value):
    if type(value) not in (int, float) or type(value) is float and not _math.isfinite(value):
        _fail()


def _bool(value):
    if type(value) is not bool:
        _fail()


def _enum(value, choices):
    if type(value) not in (str, int) or value not in choices:
        _fail()


def _nullable(value, check):
    if value is not None:
        check(value)


def _array(value, check):
    if type(value) is not list:
        _fail()
    for row in value:
        check(row)


def _v1_shape(check, value):
    try:
        check(value)
    except (ValueError, KeyError, TypeError, IndexError):
        _fail()


def _identity(value):
    _v1_shape(_v1._identity, value)


def _function(value):
    _v1_shape(_v1._function, value)


def _prov(value):
    _v1_shape(_v1._prov, value)


def _member(value):
    _v1_shape(_v1._member_key, value)


def _digest(value):
    _v1_shape(_v1._digest, value)


def _interval(value):
    _v1_shape(_v1._interval, value)


def _pointer(value):
    _v1_shape(_v1._pointer, value)


def _issue_shape(value):
    _v1_shape(_v1._issue_shape, value)


def _token(value):
    return _json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _key(kind, value):
    return kind + ":" + _hashlib.sha256(_token(value).encode("utf-8")).hexdigest()


def _distinct(rows):
    return list({_token(r): r for r in rows}.values())


def _unique(rows, field=None):
    values = [_token(r if field is None else r[field]) for r in rows]
    if len(values) != len(set(values)):
        _fail("record_key_duplicate")


def _get(value, pointer):
    _pointer(pointer)
    current = value
    try:
        for part in pointer.split("/")[1:] if pointer else []:
            part = part.replace("~1", "/").replace("~0", "~")
            if type(current) is list:
                if not _re.fullmatch(r"0|[1-9][0-9]*", part):
                    _fail("reference_out_of_range")
                current = current[int(part)]
            elif type(current) is dict:
                current = current[part]
            else:
                _fail("reference_out_of_range")
    except (KeyError, IndexError, ValueError) as error:
        if isinstance(error, ValueError) and str(error).startswith(_PREFIX):
            raise
        _fail("reference_out_of_range")
    return current


def _base_shape(sheet):
    try:
        _v1._validate_sheet(sheet)
    except ValueError as error:
        suffix = str(error).removeprefix("blast_vdb_")
        if suffix in {"unknown_dataset_key", "unknown_metadata_key", "binding_index_out_of_range"}:
            _fail("reference_out_of_range")
        if suffix in {"duplicate_binding", "duplicate_record_key"}:
            _fail("record_key_duplicate")
        _fail("sheet_schema_invalid")
    except (KeyError, TypeError, IndexError):
        _fail("sheet_schema_invalid")


def _address(value):
    _keys(value, "assignment_scope member_key feature_identifier")
    _enum(value["assignment_scope"], {"whole_sequence", "feature"})
    _member(value["member_key"])
    _nullable(value["feature_identifier"], _identity)
    if (value["assignment_scope"] == "feature") != (value["feature_identifier"] is not None):
        _fail()


def _assignment_shape(value):
    _keys(value, "assignment_key function assignment_scope target metadata_key function_ordinal scope_origin scope_source whole_sequence_cds_feature_identifier sources")
    _str(value["assignment_key"]); _function(value["function"])
    _enum(value["assignment_scope"], {"whole_sequence", "feature", "sample"})
    target = value["target"]
    _keys(target, "member_key feature_identifier sample_key")
    _nullable(target["member_key"], _member)
    _nullable(target["feature_identifier"], _identity)
    _nullable(target["sample_key"], _str)
    required = {"whole_sequence": {"member_key"}, "feature": {"member_key", "feature_identifier"}, "sample": {"sample_key"}}[value["assignment_scope"]]
    if {k for k, v in target.items() if v is not None} != required:
        _fail()
    _str(value["metadata_key"]); _int(value["function_ordinal"])
    _enum(value["scope_origin"], {"native_feature_record", "supplied_explicit_scope"})
    _prov(value["scope_source"])
    _nullable(value["whole_sequence_cds_feature_identifier"], _identity)
    _array(value["sources"], _prov)


def _dependency_shape(value):
    _keys(value, "dependency_key relation entities sources native_record")
    _str(value["dependency_key"])
    _enum(value["relation"], {"same_original_molecule", "same_library", "same_study", "declared_dependent"})
    _array(value["entities"], _address); _array(value["sources"], _prov)
    if type(value["native_record"]) not in (dict, str):
        _fail()


def _sequence_identity(value):
    _keys(value, "molecule sha256 length")
    if value["molecule"] != "nt":
        _fail()
    _digest(value["sha256"]); _int(value["length"], 1)


def _target_identity(value):
    _keys(value, "assignment_scope representation molecule sha256 length coding")
    _enum(value["assignment_scope"], {"whole_sequence", "feature"})
    _enum(value["representation"], {"full_member_nt_v1", "oriented_feature_nt_v1"})
    _sequence_identity({k: value[k] for k in ("molecule", "sha256", "length")})
    if (value["assignment_scope"] == "whole_sequence") != (value["representation"] == "full_member_nt_v1"):
        _fail()
    coding = value["coding"]
    if coding is not None:
        _keys(coding, "genetic_code codon_start translation_sha256 translation_length")
        _int(coding["genetic_code"], 1); _enum(coding["codon_start"], {1, 2, 3})
        _digest(coding["translation_sha256"]); _int(coding["translation_length"], 1)
        if value["assignment_scope"] != "feature":
            _fail()


def _census_shape(value):
    _keys(value, "census_key assignment_scope function_namespace scope datasets annotation_snapshot enumeration entities dependency_records annotation_bindings identity_proofs source native_record")
    _str(value["census_key"]); _str(value["function_namespace"])
    _enum(value["assignment_scope"], {"whole_sequence", "feature"})
    _enum(value["scope"], {"searched_population", "dataset_census", "supplied_subset"})
    _prov(value["source"])
    if type(value["native_record"]) is not dict:
        _fail()
    def dataset(row):
        _keys(row, "dataset_key identifier snapshot selected_input sra_mode include_filtered_reads")
        _str(row["dataset_key"]); _identity(row["identifier"])
        _v1_shape(_v1._snapshot, row["snapshot"]); _v1_shape(_v1._selected, row["selected_input"])
        _enum(row["sra_mode"], {0, 1, 2}); _bool(row["include_filtered_reads"])
    _array(value["datasets"], dataset); _unique(value["datasets"], "dataset_key")
    snapshot = value["annotation_snapshot"]
    _keys(snapshot, "identifier content_sha256 assignment_namespace source")
    _identity(snapshot["identifier"]); _digest(snapshot["content_sha256"])
    _str(snapshot["assignment_namespace"]); _prov(snapshot["source"])
    enumeration = value["enumeration"]
    _keys(enumeration, "base_count_unit reported_total complete pagination_complete source native_record")
    _enum(enumeration["base_count_unit"], {"member_instance", "feature_instance"})
    _nullable(enumeration["reported_total"], _int); _bool(enumeration["complete"])
    _nullable(enumeration["pagination_complete"], _bool); _prov(enumeration["source"])
    if type(enumeration["native_record"]) is not dict:
        _fail()
    def entity(row):
        _keys(row, "entity_key address target_identity parent_sequence_identity functions function_assignment_sources origin_sample_keys sample_relation_status source")
        _str(row["entity_key"]); _address(row["address"])
        _target_identity(row["target_identity"]); _sequence_identity(row["parent_sequence_identity"])
        _array(row["functions"], _function); _array(row["function_assignment_sources"], _prov)
        _array(row["origin_sample_keys"], _str); _enum(row["sample_relation_status"], {"available", "unavailable", "incompatible"})
        _prov(row["source"])
    _array(value["entities"], entity); _unique(value["entities"], "entity_key")
    _array(value["dependency_records"], _dependency_shape); _unique(value["dependency_records"], "dependency_key")
    def binding(row):
        _keys(row, "assignment_key census_entity_key annotation_snapshot_sha256 source")
        _str(row["assignment_key"]); _str(row["census_entity_key"])
        _digest(row["annotation_snapshot_sha256"]); _prov(row["source"])
    _array(value["annotation_bindings"], binding)
    def proof(row):
        _keys(row, "entity_key sequence_source linkage_source normalization symbols")
        _str(row["entity_key"]); _prov(row["sequence_source"]); _prov(row["linkage_source"])
        _enum(row["normalization"], {"full_member_nt_v1", "oriented_feature_nt_v1"}); _str(row["symbols"])
    _array(value["identity_proofs"], proof)


def _issue(sheet, suffix, *, row=None, pointer=None, **details):
    if suffix not in _REASONS:
        raise AssertionError(suffix)
    return {"code": _PREFIX + suffix, "search_key": _deepcopy(sheet["search"]["search_key"]),
            "hit_ordinal": row["hit_ordinal"] if row else None,
            "hsp_ordinal": row["hsp_ordinal"] if row else None,
            "source_pointer": pointer, "details": details}


def _link(kind, key, pointers, issues):
    conflicts = [i for i in issues if (i["code"].removeprefix(_PREFIX) in _CONFLICTS and not
        (i["code"].removeprefix(_PREFIX) in {"census_filter_mismatch", "census_snapshot_mismatch"} and i["details"].get("missing_input") is True))
        or i["code"] == _PREFIX + "census_membership_unverified" and any(i["details"].get(k) is True
            for k in ("identity_proof_conflict", "coding_proof_conflict", "parent_identity_conflict", "membership_conflict"))]
    status = "incompatible" if conflicts else "unavailable" if issues else "available"
    reason = conflicts[0]["code"] if conflicts else issues[0]["code"] if issues else None
    return dict(record_kind=kind, record_key=key, status=status, reason_code=reason,
                input_pointers=pointers, issues=issues)


def _mkey(member):
    return {k: _deepcopy(member[k]) for k in ("dataset_key", "member_kind", "member_identifier")}


def _addr(member, feature=None):
    return dict(assignment_scope="feature" if feature is not None else "whole_sequence",
                member_key=_deepcopy(member), feature_identifier=_deepcopy(feature))


def _assignment_address(row):
    return None if row["assignment_scope"] == "sample" else _addr(row["target"]["member_key"], row["target"]["feature_identifier"])


def _meta_matches(meta, address, kind=None):
    entity, member = meta["entity"], address["member_key"]
    expected = kind or ("feature" if address["assignment_scope"] == "feature" else "member")
    return (entity["kind"] == expected and entity["dataset_key"] == member["dataset_key"]
            and entity["member_identifier"] == member["member_identifier"]
            and (expected != "feature" or entity["feature_identifier"] == address["feature_identifier"]))


def _matching_features(sheet, address):
    return [(i, row) for i, row in enumerate(sheet["feature_bindings"])
            if row["feature_identifier"] == address["feature_identifier"]
            and _mkey(sheet["member_bindings"][row["member_binding_index"]]) == address["member_key"]]


def _extract(sheet):
    records, issues = [], []
    for meta in sheet["reference_metadata"]:
        if meta["entity"]["kind"] != "feature" or not meta["functions"]:
            continue
        matches = [(i, f) for i, f in enumerate(sheet["feature_bindings"])
                   if f["feature_identifier"] == meta["entity"]["feature_identifier"]
                   and _meta_matches(meta, _addr(_mkey(sheet["member_bindings"][f["member_binding_index"]]), f["feature_identifier"]))]
        addresses = _distinct([_addr(_mkey(sheet["member_bindings"][f["member_binding_index"]]), f["feature_identifier"]) for _, f in matches])
        if len(addresses) != 1 or meta["feature"] is None:
            issues.append(_issue(sheet, "assignment_entity_conflict", metadata_key=meta["metadata_key"], feature_binding_indices=[i for i, _ in matches]))
            continue
        address = addresses[0]
        for ordinal, assignment in enumerate(meta["functions"]):
            sources = [assignment["source"], meta["source"]]
            if meta["linkage_source"] is not None:
                sources.append(meta["linkage_source"])
            sources += [f["provenance"] for _, f in matches]
            records.append(dict(assignment_key=_key("feature-assignment", [address, meta["metadata_key"], ordinal]),
                function=_deepcopy(assignment["function"]), assignment_scope="feature",
                target=dict(member_key=_deepcopy(address["member_key"]), feature_identifier=_deepcopy(address["feature_identifier"]), sample_key=None),
                metadata_key=meta["metadata_key"], function_ordinal=ordinal,
                scope_origin="native_feature_record" if meta["extraction_method"] == "native_parser" else "supplied_explicit_scope",
                scope_source=_deepcopy(meta["source"]), whole_sequence_cds_feature_identifier=None,
                sources=_deepcopy(_distinct(sources))))
    return dict(schema="blast_vdb_feature_function_assignments_v1", records=records, issues=issues)


def extract_blast_vdb_feature_function_assignments(vdb_sheet: dict) -> dict:
    """Extract literal, feature-scoped assignments; never infer member function."""
    sheet = _copy(vdb_sheet); _base_shape(sheet)
    return _extract(sheet)


def _coalesce_assignments(rows):
    result = []
    for row in rows:
        content = {k: v for k, v in row.items() if k != "sources"}
        same = next((r for r in result if {k: v for k, v in r.items() if k != "sources"} == content), None)
        if same is None:
            result.append(_deepcopy(row))
        else:
            same["sources"] = _deepcopy(_distinct(same["sources"] + row["sources"]))
    return result


def _metadata_unqualified(base, key):
    return any(i["code"] in {"blast_vdb_metadata_native_extraction_unverified", "blast_vdb_metadata_entity_conflict",
        "blast_vdb_sequence_identity_conflict"} and i["details"].get("metadata_key") == key for i in base["issues"])


def _assignment_issues(sheet, base, row, conflicting=False):
    issues = []
    def add(code, **details):
        issues.append(_issue(sheet, code, assignment_key=row["assignment_key"], metadata_key=row["metadata_key"], **details))
    if conflicting:
        add("assignment_function_conflict")
    metas = [m for m in sheet["reference_metadata"] if m["metadata_key"] == row["metadata_key"]]
    if len(metas) != 1:
        add("assignment_entity_conflict"); return issues
    meta = metas[0]; scope = row["assignment_scope"]; address = _assignment_address(row)
    if (scope == "sample" and (meta["entity"]["kind"] != "sample" or meta["entity"]["sample_key"] != row["target"]["sample_key"])
            or scope != "sample" and not _meta_matches(meta, address)):
        add("assignment_entity_conflict")
    ordinal = row["function_ordinal"]
    if ordinal >= len(meta["functions"]) or meta["functions"][ordinal]["function"] != row["function"]:
        add("assignment_function_conflict", function_ordinal=ordinal)
    if _metadata_unqualified(base, meta["metadata_key"]) or meta["linkage_source"] is None:
        add("assignment_entity_conflict")
    if row["scope_origin"] == "native_feature_record" and (scope != "feature" or meta["extraction_method"] != "native_parser" or row["scope_source"] != meta["source"]):
        add("assignment_scope_missing")
    if scope == "feature" and not _matching_features(sheet, address):
        add("assignment_entity_conflict")
    witness = row["whole_sequence_cds_feature_identifier"]
    translated = sheet["search"]["program_context"]["execution_program"] == "tblastn_vdb"
    if witness is not None and (scope != "whole_sequence" or not translated):
        add("coding_witness_conflict")
    if scope == "whole_sequence" and translated and witness is None:
        add("coding_witness_missing")
    if scope == "sample":
        add("sample_assignment_not_query_function")
    return _distinct(issues)


def _parent_sequence(sheet, base, address):
    rows = [m for m in sheet["reference_metadata"] if _meta_matches(m, address, "member") and m["sequence"] is not None]
    if not rows:
        return None, "target_identity_unavailable"
    identities = []
    for m in rows:
        sequence = m["sequence"]
        if (m["linkage_source"] is None or _metadata_unqualified(base, m["metadata_key"])
                or sequence["molecule"] != "nt" or _v1._symbols(sequence["symbols"], sequence["length"]) != sequence):
            return None, "target_identity_conflict"
        identities.append(sequence)
    if len(_distinct(identities)) != 1:
        return None, "target_identity_conflict"
    sequence = identities[0]
    for member in sheet["member_bindings"]:
        if _mkey(member) == address["member_key"] and member["reference_identity"] is not None:
            ref = member["reference_identity"]
            if ((ref["full_length"] is not None and ref["full_length"] != sequence["length"])
                    or (ref["sequence_sha256"] is not None and ref["sequence_sha256"] != sequence["sha256"])):
                return None, "target_identity_conflict"
    subjects = [s for s in base["subjects"] if any(_mkey(sheet["member_bindings"][i]) == address["member_key"] for i in s["member_binding_indices"])]
    for subject in subjects:
        length = subject["coordinate_context"]["reference"]["reported_length"]
        if length is not None and length != sequence["length"]:
            return None, "target_identity_conflict"
        offered = [b for b in sheet["sequence_identity_bindings"] if b["binding"]["hit_index"] == subject["row_key"]["hit_ordinal"]]
        if offered and subject["sequence_group_key"] != "sha256:" + sequence["sha256"]:
            return None, "target_identity_conflict"
    return sequence, None


def _feature_state(sheet, base, address, sequence):
    """Qualify an exact feature independently of aggregate HSP relation_status."""
    matches = _matching_features(sheet, address)
    if not matches or sequence is None:
        return None, None, None, "target_identity_unavailable"
    skip = {"function", "provenance", "member_binding_index", "hit_ordinal"}
    shapes = _distinct([{k: v for k, v in f.items() if k not in skip} for _, f in matches])
    if len(shapes) != 1:
        return None, None, None, "target_identity_conflict"
    feature = matches[0][1]
    for _, f in matches:
        member = sheet["member_bindings"][f["member_binding_index"]]
        if (f["search_key"] != sheet["search"]["search_key"] or f["search_key"] != member["search_key"]
                or f["hit_ordinal"] != member["hit_ordinal"] or f["member_identifier"] != member["member_identifier"]):
            return None, None, None, "assignment_entity_conflict"
    segments, strand = feature["segments"], feature["strand"]
    if (feature["location_status"] != "exact" or not segments or strand not in (-1, 1)
            or segments != sorted(segments, reverse=strand == -1)
            or any(b > sequence["length"] for a, b in segments)
            or any(a2 < b1 for (_, b1), (a2, _) in zip(sorted(segments), sorted(segments)[1:]))
            or [min(a for a, b in segments), max(b for a, b in segments)] != feature["member_interval"]):
        return feature, None, None, "target_identity_unavailable"
    metadata = [m for m in sheet["reference_metadata"] if _meta_matches(m, address) and m["feature"] is not None]
    if not metadata or any(m["linkage_source"] is None or _metadata_unqualified(base, m["metadata_key"]) for m in metadata):
        return feature, None, None, "target_identity_unavailable"
    for meta in metadata:
        raw = meta["feature"]
        if any(raw[k] != feature[k] for k in ("segments", "strand", "genetic_code", "codon_start")) or raw["key"] != feature["feature_kind"]:
            return feature, None, None, "target_identity_conflict"
    symbols = "".join(sequence["symbols"][a:b] if strand == 1 else str(_Seq(sequence["symbols"][a:b]).reverse_complement()) for a, b in segments)
    digest = _hashlib.sha256(symbols.encode("ascii")).hexdigest()
    if feature["feature_sequence_sha256"] is not None and feature["feature_sequence_sha256"] != digest:
        return feature, None, None, "target_identity_conflict"
    components = [(i, f) for i, f in enumerate(base["feature_components"])
                  if f["member_key"] == address["member_key"] and f["feature_identifier"] == address["feature_identifier"]]
    if len(components) != 1:
        return feature, None, None, "assignment_entity_conflict"
    index, component = components[0]
    target = dict(assignment_scope="feature", representation="oriented_feature_nt_v1", molecule="nt",
                  sha256=digest, length=len(symbols), coding=None)
    if sheet["search"]["program_context"]["execution_program"] == "tblastn_vdb":
        mapping = component["translation_map"]
        if mapping is None or mapping["status"] != "available":
            conflict = mapping is not None and mapping["status"] == "incompatible"
            return feature, component, None, "coding_witness_conflict" if conflict else "coding_witness_missing"
        translations = [m["feature"]["translation"] for m in metadata if m["metadata_key"] == feature["translation_metadata_key"]]
        if len(translations) != 1 or not translations[0]:
            return feature, component, None, "coding_witness_missing"
        translation = "".join(translations[0].split()).upper()
        target["coding"] = dict(genetic_code=mapping["genetic_code"], codon_start=mapping["codon_start"],
                                translation_sha256=_hashlib.sha256(translation.encode("ascii")).hexdigest(), translation_length=len(translation))
    return feature, component, target, None


def _entity_context(sheet, base, address):
    indices = [i for i, m in enumerate(sheet["member_bindings"]) if _mkey(m) == address["member_key"]]
    subjects = [s for s in base["subjects"] if any(i in indices for i in s["member_binding_indices"])]
    if address["assignment_scope"] == "feature":
        bound = {f["hit_ordinal"] for _, f in _matching_features(sheet, address)}
        subjects = [s for s in subjects if s["row_key"]["hit_ordinal"] in bound]
    origins = [o for o in base["membership"]["origins"] if any(o["row_key"] == s["row_key"] for s in subjects)]
    statuses = [o["status"] if address["member_key"] in o["member_keys"] else "ambiguous" if o["status"] == "ambiguous" else "unavailable" for o in origins]
    origin = "available" if "available" in statuses else "ambiguous" if "ambiguous" in statuses else "unavailable"
    sequence, reason = _parent_sequence(sheet, base, address)
    target = None if sequence is None else dict(assignment_scope="whole_sequence", representation="full_member_nt_v1",
        molecule="nt", sha256=sequence["sha256"], length=sequence["length"], coding=None)
    feature = component = None
    if address["assignment_scope"] == "feature":
        feature, component, target, feature_reason = _feature_state(sheet, base, address, sequence)
        reason = reason or feature_reason
    groups = [s for s in base["sample_groups"]["groups"] if address["member_key"] in s["origin_member_keys"]]
    samples = _distinct([s["sample_key"] for s in groups])
    sample_status = "available" if samples else "unavailable"
    if any(i["code"] == "blast_vdb_sample_link_conflict" and (i["details"].get("member_key") == address["member_key"]
            or i["details"].get("sample_key") in [sheet["member_bindings"][j]["sample_key"] for j in indices]) for i in base["issues"]):
        sample_status = "incompatible"; samples = []
    return dict(indices=indices, subjects=subjects, origin=origin, sequence=sequence, target=target,
                reason=reason, feature=feature, feature_component=component, samples=samples, sample_status=sample_status)


def _measure(value, unit, reason=None):
    return dict(value=value, unit=unit, status="available" if value is not None else "incompatible" if reason == "incompatible_input" else "unavailable",
                unavailable_reason=None if value is not None else reason or "missing_input")


def _count_positions(columns, axis, paired=False):
    return len({p for c in columns if c[axis + "_interval"] is not None
                and (not paired or c["query_interval"] is not None and c["reference_interval"] is not None)
                for p in range(*c[axis + "_interval"])})


def _whole_witness(sheet, base, address, sequence, assignment):
    fid = assignment["whole_sequence_cds_feature_identifier"] if assignment else None
    if fid is None:
        return None, None, "coding_witness_missing"
    feature, component, target, reason = _feature_state(sheet, base, _addr(address["member_key"], fid), sequence)
    if reason:
        return feature, component, "coding_witness_conflict" if reason in _CONFLICTS else "coding_witness_missing"
    if feature["segments"] != [[0, sequence["length"]]] or feature["feature_kind"] != "CDS":
        return feature, component, "coding_witness_conflict"
    return feature, component, None


def _hsp_facts(sheet, base, address, context, hsp, assignment=None):
    """Inspect stored original columns; never clip or lend a native score."""
    issues = []
    def add(code, **details):
        issues.append(_issue(sheet, code, row=hsp["row_key"], pointer=hsp["source_locator"]["pointer"],
                             entity_key=_key("entity", address), assignment_key=assignment["assignment_key"] if assignment else None, **details))
    translated = sheet["search"]["program_context"]["execution_program"] == "tblastn_vdb"
    score = hsp["native_components"]["native_scores"]
    columns = hsp["correspondence"]["columns"]
    geometry = (hsp["correspondence"]["geometry_status"] == "available" and hsp["native_components"]["geometry_available"])
    values = dict(native_bit_score=_measure(score["bit_score"], "bits"), native_evalue=_measure(score["evalue"], "expected_chance_match"),
        paired_query_units=_measure(_count_positions(columns, "query", True) if geometry else None, "aa" if translated else "nt"),
        paired_reference_nt=_measure(_count_positions(columns, "reference", True) if geometry else None, "nt"),
        aligned_reference_nt=_measure(_count_positions(columns, "reference") if geometry else None, "nt"),
        attributable_reference_nt=_measure(None, "nt"), corresponding_feature_residues=_measure(None, "aa", "missing_input" if translated else "not_measured"))
    origin = next((o for o in base["membership"]["origins"] if o["row_key"]["hit_ordinal"] == hsp["row_key"]["hit_ordinal"]), None)
    if base["status"] in {"incompatible", "unavailable"}:
        add("base_source_conflict" if base["status"] == "incompatible" else "base_source_unavailable")
    if origin is None or origin["status"] != "available" or address["member_key"] not in origin["member_keys"]:
        add("member_origin_ambiguous" if origin and origin["status"] == "ambiguous" else "member_origin_unavailable")
    subject = next((s for s in base["subjects"] if s["row_key"]["hit_ordinal"] == hsp["row_key"]["hit_ordinal"]), None)
    query = subject["coordinate_context"]["query"] if subject else None
    if query is None or query["full_length"] is None or query["effective_query_interval"] is None:
        add("query_binding_unavailable")
    elif geometry and any(c["query_interval"] is not None and (c["query_interval"][0] < query["effective_query_interval"][0]
            or c["query_interval"][1] > query["effective_query_interval"][1]) for c in columns):
        add("query_binding_unavailable")
    if context["reason"]:
        add(context["reason"])
    if score["bit_score"] is None:
        add("hsp_score_missing")
    if not geometry or not values["paired_query_units"]["value"]:
        add("hsp_geometry_unavailable")
    sequence = context["sequence"]
    feature, component = context["feature"], context["feature_component"]
    if translated and address["assignment_scope"] == "whole_sequence":
        feature, component, reason = _whole_witness(sheet, base, address, sequence, assignment)
        if reason:
            add(reason)
    pointer = ("/base_components/feature_components/" + str(base["feature_components"].index(component))) if component is not None else None
    if geometry and sequence is not None:
        refs = [c for c in columns if c["reference_interval"] is not None]
        if any(c["reference_interval"][0] < 0 or c["reference_interval"][1] > sequence["length"] for c in refs):
            add("hsp_geometry_unavailable")
        elif not translated:
            for c in refs:
                a, b = c["reference_interval"]
                actual = sequence["symbols"][a:b]
                direction = c["reference_direction"]
                if direction not in (-1, 1):
                    add("hsp_geometry_unavailable", column=c["column"]); continue
                if direction == -1:
                    actual = str(_Seq(actual).reverse_complement())
                if c["reference_symbol"].upper() != actual:
                    add("hsp_sequence_conflict", column=c["column"], actual_symbols=actual, reported_symbol=c["reference_symbol"])
        if feature is not None and any(not any(a <= c["reference_interval"][0] and c["reference_interval"][1] <= b for a, b in feature["segments"]) for c in refs):
            add("hsp_not_contained_in_feature")
        if translated:
            mapping = component["translation_map"] if component else None
            if mapping is None or mapping["status"] != "available":
                add("hsp_codon_correspondence_unavailable")
            else:
                residues = set(); codons = {tuple(c["member_positions"]): c for c in mapping["codons"]}
                for c in refs:
                    a, b = c["reference_interval"]; direction = c["reference_direction"]
                    positions = tuple(range(a, b)) if direction == 1 else tuple(range(b - 1, a - 1, -1))
                    codon = codons.get(positions)
                    if (direction != mapping["strand"] or codon is None or len(positions) != 3
                            or c["reference_symbol"].upper() != codon["translated_symbol"]
                            or codon["terminal_stop"] or codon["feature_residue_index"] is None):
                        add("hsp_codon_correspondence_unavailable", column=c["column"], member_positions=list(positions))
                    elif c["query_interval"] is not None:
                        residues.add(codon["feature_residue_index"])
                if not any(i["code"] == _PREFIX + "hsp_codon_correspondence_unavailable" for i in issues):
                    values["corresponding_feature_residues"] = _measure(len(residues), "aa")
    if not issues:
        values["attributable_reference_nt"] = _deepcopy(values["aligned_reference_nt"])
    return values, pointer, _distinct(issues)


def _dependency_issues(sheet, record, addresses):
    issues = []
    tokens = [_token(a) for a in record["entities"]]
    if len(tokens) < 2 or len(tokens) != len(set(tokens)):
        issues.append(_issue(sheet, "dependency_relation_conflict", dependency_key=record["dependency_key"]))
    if (any(t not in addresses for t in tokens) or not record["sources"] or not record["native_record"]):
        issues.append(_issue(sheet, "dependency_relation_unresolved", dependency_key=record["dependency_key"],
                             unresolved_entities=[a for a in record["entities"] if _token(a) not in addresses]))
    return issues


def _proof_matches(proof, identity):
    sequence = _v1._symbols(proof["symbols"])
    return sequence is not None and all(sequence[k] == identity[k] for k in ("molecule", "sha256", "length"))


def _coding_proof_matches(symbols, coding):
    if coding is None:
        return True
    sequence = _v1._symbols(symbols)
    if sequence is None:
        return False
    bases = sequence["symbols"][coding["codon_start"] - 1:]
    bases = bases[:len(bases) - len(bases) % 3]
    try:
        translation = str(_Seq(bases).translate(table=coding["genetic_code"], cds=False))
        table = _CodonTable.unambiguous_dna_by_id[coding["genetic_code"]]
    except (ValueError, KeyError):
        return False
    if translation.endswith("*"):
        translation = translation[:-1]
    possibilities = [translation]
    if translation and bases[:3].replace("U", "T") in table.start_codons:
        possibilities.append("M" + translation[1:])
    return any("*" not in t and len(t) == coding["translation_length"]
               and _hashlib.sha256(t.encode("ascii")).hexdigest() == coding["translation_sha256"] for t in possibilities)


def _census_issues(sheet, census, entities, assignments, observations):
    """Qualify a supplied enumeration, without computing target groups or weights."""
    issues = []
    def add(code, **details):
        issue = _issue(sheet, code, census_key=census["census_key"], **details)
        if issue not in issues:
            issues.append(issue)
    enumeration = census["enumeration"]
    if not enumeration["complete"] or enumeration["pagination_complete"] is not True:
        add("census_partial")
    addresses = [_token(e["address"]) for e in census["entities"]]
    if enumeration["reported_total"] is None:
        add("census_partial")
    elif len(set(addresses)) != len(addresses) or enumeration["reported_total"] != len(set(addresses)):
        add("census_count_conflict")
    expected_unit = "member_instance" if census["assignment_scope"] == "whole_sequence" else "feature_instance"
    if enumeration["base_count_unit"] != expected_unit:
        add("census_unit_mismatch")
    if census["scope"] != "searched_population":
        add("census_scope_mismatch")
    original = {d["dataset_key"]: d for d in sheet["dataset_records"]}
    supplied = {d["dataset_key"]: d for d in census["datasets"]}
    if set(original) != set(supplied) or not original:
        add("census_scope_mismatch")
    for key in original.keys() & supplied.keys():
        actual, value = original[key], supplied[key]
        if actual["identifier"] != value["identifier"] or actual["selected_input"] != value["selected_input"]:
            add("census_scope_mismatch", dataset_key=key)
        if not any(v is not None for v in actual["snapshot"].values()) or not any(v is not None for v in value["snapshot"].values()):
            add("census_snapshot_mismatch", dataset_key=key, missing_input=True)
        elif actual["snapshot"] != value["snapshot"]:
            add("census_snapshot_mismatch", dataset_key=key)
        context = actual["search_context"]
        if context["search_key"] != sheet["search"]["search_key"]:
            add("census_scope_mismatch", dataset_key=key)
        if any(context[f] is None for f in ("sra_mode", "include_filtered_reads")):
            add("census_filter_mismatch", dataset_key=key, missing_input=True)
        if any(context[f] is not None and context[f] != value[f] for f in ("sra_mode", "include_filtered_reads")):
            add("census_filter_mismatch", dataset_key=key)
        params = sheet["search"]["normalized"]["search"]["parameters"]
        if any(f in params and params[f] != value[f] for f in ("sra_mode", "include_filtered_reads")):
            add("census_filter_mismatch", dataset_key=key)
    snapshot = census["annotation_snapshot"]
    if snapshot["assignment_namespace"] != census["function_namespace"]:
        add("census_annotation_snapshot_mismatch")
    report_sources = {sheet["report_source"]["artifact_ref"], sheet["search"]["search_key"]["artifact_key"]}
    # A literal source relation is not a claim that this pure port authenticated
    # external bytes. It can, however, reject use of this report as its own census.
    if census["source"]["source_ref"] in report_sources or enumeration["source"]["source_ref"] in report_sources:
        add("census_membership_unverified", report_used_as_census=True)
    census_entities = {e["entity_key"]: e for e in census["entities"]}
    for proof in census["identity_proofs"]:
        if proof["entity_key"] not in census_entities:
            add("census_membership_unverified", census_entity_key=proof["entity_key"])
    for entity in census["entities"]:
        key = entity["entity_key"]; target = entity["target_identity"]; address = entity["address"]
        if (address["assignment_scope"] != census["assignment_scope"] or target["assignment_scope"] != census["assignment_scope"]
                or address["member_key"]["dataset_key"] not in supplied):
            add("census_scope_mismatch", census_entity_key=key)
        if any(f["namespace"] != census["function_namespace"] for f in entity["functions"]):
            add("census_annotation_snapshot_mismatch", census_entity_key=key)
        if entity["functions"] and not entity["function_assignment_sources"]:
            add("census_membership_unverified", census_entity_key=key)
        if entity["sample_relation_status"] == "available" and not entity["origin_sample_keys"]:
            add("census_membership_unverified", census_entity_key=key)
        expected = [(target["representation"], target)]
        if address["assignment_scope"] == "feature":
            expected.append(("full_member_nt_v1", entity["parent_sequence_identity"]))
        elif {k: target[k] for k in ("molecule", "sha256", "length")} != entity["parent_sequence_identity"]:
            add("census_membership_unverified", census_entity_key=key, parent_identity_conflict=True)
        for normalization, identity in expected:
            proofs = [p for p in census["identity_proofs"] if p["entity_key"] == key and p["normalization"] == normalization]
            if not proofs:
                add("census_membership_unverified", census_entity_key=key, normalization=normalization)
            for proof in proofs:
                if (not _proof_matches(proof, identity) or proof["sequence_source"]["source_ref"] in report_sources
                        or proof["linkage_source"]["source_ref"] in report_sources):
                    add("census_membership_unverified", census_entity_key=key, normalization=normalization, identity_proof_conflict=True)
                if normalization == "oriented_feature_nt_v1" and not _coding_proof_matches(proof["symbols"], target["coding"]):
                    add("census_membership_unverified", census_entity_key=key, coding_proof_conflict=True)
            normalized = [_v1._symbols(p["symbols"]) for p in proofs]
            if len(_distinct(normalized)) > 1:
                add("census_count_conflict", census_entity_key=key, conflicting_identity_proofs=True)
    by_address = {}
    for entity in census["entities"]:
        by_address.setdefault(_token(entity["address"]), []).append(entity)
    for dep in census["dependency_records"]:
        if _dependency_issues(sheet, dep, set(by_address)):
            add("census_membership_unverified", dependency_key=dep["dependency_key"])
    actual_assignments = {}
    for assignment in assignments:
        actual_assignments.setdefault(assignment["assignment_key"], []).append(assignment)
    for binding in census["annotation_bindings"]:
        key = binding["assignment_key"]
        matches = actual_assignments.get(key, [])
        entity = census_entities.get(binding["census_entity_key"])
        if binding["annotation_snapshot_sha256"] != snapshot["content_sha256"]:
            add("census_annotation_snapshot_mismatch", assignment_key=key)
        if len(matches) != 1 or entity is None or (matches and _assignment_address(matches[0]) != entity["address"]):
            add("census_membership_unverified", assignment_key=key, census_entity_key=binding["census_entity_key"],
                membership_conflict=bool(matches) and entity is not None)
    selected_observations = [o for o in observations if o["qualification"] == "available"
        and o["function"] is not None and o["function"]["namespace"] == census["function_namespace"]]
    observed = {e["entity_key"]: e for e in entities if e["address"]["assignment_scope"] == census["assignment_scope"]}
    # Eligible unknown targets also belong to the census partition; they cannot
    # disappear merely because no assignment is available in this namespace.
    for entity in observed.values():
        if not entity["eligible_hsp_rows"]:
            continue
        matches = by_address.get(_token(entity["address"]), [])
        if (len(matches) != 1 or matches[0]["target_identity"] != entity["target_identity"]
                or matches[0]["parent_sequence_identity"] != entity["parent_sequence_identity"]):
            add("census_membership_unverified", entity_key=entity["entity_key"], membership_conflict=bool(matches))
    for observation in selected_observations:
        entity = observed.get(observation["entity_key"])
        if entity is None:
            continue
        candidates = by_address.get(_token(entity["address"]), [])
        if len(candidates) != 1:
            add("census_membership_unverified", entity_key=entity["entity_key"]); continue
        target = candidates[0]
        function = observation["function"]
        if function not in target["functions"]:
            code = "census_zero_conflict" if not any(function in e["functions"] for e in census["entities"]) else "census_function_missing"
            add(code, function=function, entity_key=entity["entity_key"])
        bindings = [b for b in census["annotation_bindings"] if b["assignment_key"] == observation["assignment_key"]
                    and b["census_entity_key"] == target["entity_key"]]
        if not bindings:
            add("census_membership_unverified", assignment_key=observation["assignment_key"])
    return issues


def _new_observation(sheet, base, entity, context, hsp, assignment, assignment_issues=()):
    values, pointer, issues = _hsp_facts(sheet, base, entity["address"], context, hsp, assignment)
    issues = _distinct([*assignment_issues, *issues])
    link = _link("assignment", "unused", [], issues)
    qualification = link["status"]
    if assignment and assignment["assignment_scope"] == "sample":
        qualification = "not_applicable"
    identity = [entity["entity_key"], assignment["assignment_key"] if assignment else None, hsp["row_key"]]
    return dict(observation_key=_key("observation", identity), entity_key=entity["entity_key"],
        assignment_key=assignment["assignment_key"] if assignment else None,
        function=_deepcopy(assignment["function"]) if assignment else None, row_key=_deepcopy(hsp["row_key"]),
        source_locator=_deepcopy(hsp["source_locator"]), **values, qualification=qualification,
        reason_code=link["reason_code"], base_component_pointer="/base_components/hsps/" + str(base["hsps"].index(hsp)),
        feature_component_pointer=pointer, issues=issues)


def _entity_issues(sheet, address, context):
    reasons = [context["reason"], None if context["origin"] == "available" else
        "member_origin_ambiguous" if context["origin"] == "ambiguous" else "member_origin_unavailable"]
    return [_issue(sheet, reason, entity_key=_key("entity", address)) for reason in reasons if reason]


def populate_blast_vdb_function_sheet(vdb_sheet: dict, *, supplied_assignments: list[dict],
                                      dependency_records: list[dict], census_records: list[dict]) -> dict:
    """Populate the complete additive sheet from explicit, already supplied data."""
    sheet, supplied, dependencies, censuses = _copy([vdb_sheet, supplied_assignments, dependency_records, census_records])
    _base_shape(sheet)
    _array(supplied, _assignment_shape); _array(dependencies, _dependency_shape); _array(censuses, _census_shape)
    _unique(dependencies, "dependency_key"); _unique(censuses, "census_key")
    base = _base.calculate_blast_vdb_components(sheet)
    extraction = _extract(sheet)
    assignments = _coalesce_assignments([*extraction["records"], *supplied])
    by_assignment = {}
    for i, row in enumerate(assignments):
        by_assignment.setdefault(row["assignment_key"], []).append(i)
    addresses = [_addr(_mkey(m)) for m in sheet["member_bindings"]]
    addresses += [_addr(_mkey(sheet["member_bindings"][f["member_binding_index"]]), f["feature_identifier"]) for f in sheet["feature_bindings"]]
    addresses = _distinct(addresses)
    contexts = {_token(a): _entity_context(sheet, base, a) for a in addresses}
    links, issues = [], [*base["issues"], *extraction["issues"]]
    assignment_issues = {}
    for key, indices in by_assignment.items():
        own = []
        for i in indices:
            row = assignments[i]
            own += _assignment_issues(sheet, base, row, len(indices) > 1)
            address = _assignment_address(row)
            if address is not None and _token(address) not in contexts:
                own.append(_issue(sheet, "assignment_entity_conflict", assignment_key=key, target=row["target"]))
        own = _distinct(own)
        assignment_issues[key] = own
        links.append(_link("assignment", key, [f"/assignment_records/{i}" for i in indices], own))
    entities, observations = [], []
    for address in addresses:
        context = contexts[_token(address)]
        own_assignments = [a for a in assignments if _assignment_address(a) == address]
        own_issues = _entity_issues(sheet, address, context)
        sequence = context["sequence"]
        entity = dict(entity_key=_key("entity", address), address=_deepcopy(address),
            subject_rows=[_deepcopy(s["row_key"]) for s in context["subjects"]],
            member_binding_indices=context["indices"],
            metadata_keys=[m["metadata_key"] for m in sheet["reference_metadata"] if _meta_matches(m, address) or _meta_matches(m, address, "member")],
            parent_sequence_identity={k: sequence[k] for k in ("molecule", "sha256", "length")} if sequence else None,
            target_identity=context["target"], origin_status=context["origin"],
            origin_sample_keys=context["samples"], sample_relation_status=context["sample_status"],
            eligible_hsp_rows=[], assignment_keys=_distinct([a["assignment_key"] for a in own_assignments]), issues=own_issues)
        eligible = []
        hrows = [h for h in base["hsps"] if any(h["row_key"] in s["hsp_row_keys"] for s in context["subjects"])]
        for hsp in hrows:
            for key in entity["assignment_keys"]:
                candidates = [a for a in own_assignments if a["assignment_key"] == key]
                # Conflicting records remain in assignment_records and the link
                # points at every variant. They cannot produce an order winner.
                if len(candidates) != 1:
                    continue
                observations.append(_new_observation(sheet, base, entity, context, hsp, candidates[0], assignment_issues[key]))
            translated_whole = address["assignment_scope"] == "whole_sequence" and sheet["search"]["program_context"]["execution_program"] == "tblastn_vdb"
            if translated_whole:
                witnesses = [a for a in own_assignments if not assignment_issues[a["assignment_key"]]]
                alternatives = [_new_observation(sheet, base, entity, context, hsp, a) for a in witnesses]
                alternatives = [o for o in alternatives if o["qualification"] == "available"]
                unknown = min(alternatives, key=lambda o: _token(o["feature_component_pointer"])) if alternatives else None
                if unknown is not None:
                    unknown.update(assignment_key=None, function=None,
                        observation_key=_key("observation", [entity["entity_key"], None, hsp["row_key"]]))
            else:
                unknown = _new_observation(sheet, base, entity, context, hsp, None)
                if unknown["qualification"] != "available":
                    unknown = None
            if unknown is not None:
                observations.append(unknown); eligible.append(_deepcopy(hsp["row_key"]))
        entity["eligible_hsp_rows"] = _distinct(eligible)
        entities.append(entity)
    for i, record in enumerate(dependencies):
        own = _dependency_issues(sheet, record, set(contexts))
        links.append(_link("dependency", record["dependency_key"], [f"/dependency_records/{i}"], own))
    for i, record in enumerate(censuses):
        own = _census_issues(sheet, record, entities, assignments, observations)
        links.append(_link("census", record["census_key"], [f"/census_records/{i}"], own))
    issues += [i for row in links + entities + observations for i in row["issues"]]
    if base["status"] in {"unavailable", "incompatible"}:
        issues.append(_issue(sheet, "base_source_conflict" if base["status"] == "incompatible" else "base_source_unavailable"))
    result = dict(schema=_SCHEMA, base_sheet=sheet, base_components=base, assignment_records=assignments,
                  dependency_records=dependencies, census_records=censuses, entities=entities, observations=observations,
                  link_results=links, issues=_deepcopy(_distinct(issues)))
    return validate_blast_vdb_function_sheet(result)


def _rowkey(row):
    _keys(row, "search_key hit_ordinal hsp_ordinal description_ordinal")
    _v1_shape(_v1._search_key, row["search_key"])
    for name in ("hit_ordinal", "hsp_ordinal", "description_ordinal"):
        _nullable(row[name], _int)


def _locator(row):
    _keys(row, "artifact_ref report_index pointer search_key member_ordinal member_sha256 native_format hit_index description_index hsp_index line_numbers data_row_ordinals")
    _str(row["artifact_ref"]); _int(row["report_index"]); _pointer(row["pointer"])
    _v1_shape(_v1._search_key, row["search_key"])
    _nullable(row["member_sha256"], _digest)
    _enum(row["native_format"], {"json2", "tabular"})
    for name in ("member_ordinal", "hit_index", "description_index", "hsp_index"):
        _nullable(row[name], _int)
    for name in ("line_numbers", "data_row_ordinals"):
        _nullable(row[name], lambda values: _array(values, _int))


def _measure_shape(value, unit=None, integer=False):
    _keys(value, "value unit status unavailable_reason")
    _str(value["unit"]); _enum(value["status"], {"available", "unavailable", "incompatible"})
    _nullable(value["value"], _int if integer else _num)
    _nullable(value["unavailable_reason"], _str)
    if (value["status"] == "available") != (value["value"] is not None) or (value["value"] is not None) != (value["unavailable_reason"] is None):
        _fail()
    if unit is not None and value["unit"] != unit:
        _fail()


def _saved_measure_shapes(value):
    """Check legacy numerical-cell types without recomputing legacy science."""
    if type(value) is list:
        for row in value:
            _saved_measure_shapes(row)
    elif type(value) is dict:
        if set(value) == {"value", "unit", "status", "unavailable_reason"}:
            _measure_shape(value)
        elif set(value) == {"numerator", "denominator", "value", "unit", "complete_for_reported_hsps", "unavailable_reason"}:
            _ratio_shape(value)
        else:
            # Raw source records have their own native, deliberately open shape.
            for name, item in value.items():
                if name not in {"native_hsp", "native_record", "details"}:
                    _saved_measure_shapes(item)


def _ratio_shape(value):
    _keys(value, "numerator denominator value unit complete_for_reported_hsps unavailable_reason")
    for key in ("numerator", "denominator", "value"):
        _nullable(value[key], _num)
    _bool(value["complete_for_reported_hsps"]); _nullable(value["unavailable_reason"], _str)
    if value["unit"] != "fraction" or (value["value"] is None) != (value["unavailable_reason"] is not None):
        _fail()
    if value["value"] is not None and (value["denominator"] is None or value["denominator"] <= 0
            or value["numerator"] is None or value["value"] != value["numerator"] / value["denominator"]
            or not value["complete_for_reported_hsps"]):
        _fail()


def _cells(row, measures="", ratios="", *, integer=True):
    for name in measures.split():
        _measure_shape(row[name], integer=integer)
    for name in ratios.split():
        _ratio_shape(row[name])


def _stored_source(sheet, rowkey, source):
    _rowkey(rowkey); _locator(source)
    key = sheet["search"]["search_key"]; actual = sheet["report_source"]
    if rowkey["search_key"] != key or source["search_key"] != key:
        _fail("reference_out_of_range")
    for source_field, actual_field in (("artifact_ref", "artifact_ref"), ("member_ordinal", "member_ordinal"), ("member_sha256", "member_sha256")):
        if source[source_field] != actual[actual_field]:
            _fail("reference_out_of_range")
    if source["report_index"] != key["report_index"]:
        _fail("reference_out_of_range")
    for a, b in (("hit_index", "hit_ordinal"), ("hsp_index", "hsp_ordinal"), ("description_index", "description_ordinal")):
        if source[a] != rowkey[b]:
            _fail("reference_out_of_range")
    if source["native_format"] != sheet["search"]["normalized"]["format"]:
        _fail()
    pointer = key["search_pointer"]
    if source["native_format"] == "json2":
        if rowkey["hit_ordinal"] is not None:
            pointer += "/hits/" + str(rowkey["hit_ordinal"])
        if rowkey["hsp_ordinal"] is not None:
            pointer += "/hsps/" + str(rowkey["hsp_ordinal"])
        if rowkey["description_ordinal"] is not None:
            pointer += "/description/" + str(rowkey["description_ordinal"])
    if source["pointer"] != pointer:
        _fail("reference_out_of_range")
    if source["native_format"] == "json2":
        if source["line_numbers"] is not None or source["data_row_ordinals"] is not None:
            _fail()
    else:
        rows = source["data_row_ordinals"]
        if rowkey["hsp_ordinal"] is not None and rows != [rowkey["hsp_ordinal"]]:
            _fail("reference_out_of_range")
        if rows is not None:
            lines = sheet["search"]["native"]["line_numbers"]
            if any(i >= len(lines) for i in rows) or source["line_numbers"] != [lines[i] for i in rows]:
                _fail("reference_out_of_range")


def _saved_query_axis(sheet, base, axis):
    """Check a saved denominator against the original explicit operand/extent."""
    search = sheet["search"]; binding = sheet["query_binding"]
    kind = "pssm_master" if search["program_context"]["query_kind"] == "pssm" else "sequence"
    unit = "nt" if search["program_context"]["execution_program"] == "blastn_vdb" else "aa"
    if axis["axis_kind"] != kind or axis["coordinate_unit"] != unit or axis["reported_length"] != search["normalized"]["query"]["length"]:
        _fail()
    _nullable(axis["full_length"], lambda n: _int(n, 1))
    _nullable(axis["selected_interval"], _interval); _nullable(axis["effective_query_interval"], _interval)
    if axis["full_length"] is None:
        if axis["selected_interval"] is not None or axis["effective_query_interval"] is not None or not any(
                i["code"] in {"blast_vdb_query_axis_unbound", "blast_vdb_query_axis_conflict"} for i in base["issues"]):
            _fail()
        return
    if binding is None or binding["operand"] != search["operand_binding"]:
        _fail()
    operand = binding["operand"]
    if (operand["role"] != "query" or binding["axis_kind"] != kind or binding["coordinate_unit"] != unit
            or operand["molecule"] not in ({"dna", "rna"} if unit == "nt" else {"protein"})
            or binding["full_length"] != operand["length"] or axis["full_length"] != binding["full_length"]
            or axis["selected_interval"] != operand["selected_interval"]):
        _fail()
    selected, reported = axis["selected_interval"], axis["reported_length"]
    if reported is not None and reported != axis["full_length"] and (selected is None or reported != selected[1] - selected[0]):
        _fail()
    datasets = [d for d in sheet["dataset_records"] if d["search_context"]["search_key"] == search["search_key"]]
    if kind == "pssm_master":
        maps = [m["master_mapping"] for m in sheet["reference_metadata"] if m["entity"]["kind"] == "query_master"
            and m["entity"]["pssm_key"] == binding["pssm_key"] and m["source"] == binding["master_mapping_ref"]
            and m["master_mapping"] is not None and not _metadata_unqualified(base, m["metadata_key"])]
        if len(maps) != 1 or binding["pssm_key"] is None or {d["search_context"]["input_pssm_key"] for d in datasets} != {binding["pssm_key"]}:
            _fail()
        master = maps[0]
        if (master["pssm_key"] != binding["pssm_key"] or master["num_columns"] != axis["full_length"]
                or [c["column"] for c in master["columns"]] != list(range(master["num_columns"]))
                or any(c["master_position"] is not None and c["master_position"] >= axis["full_length"] for c in master["columns"])):
            _fail()
    extents = [d["search_context"]["query_extent"] for d in datasets]
    expected = None
    if extents and len({(e["mode"], _token(e["interval"])) for e in extents}) == 1:
        extent = extents[0]
        if extent["mode"] == "full" and selected is None:
            expected = [0, axis["full_length"]]
        elif extent["mode"] == "interval" and extent["interval"] == selected:
            expected = selected
    if axis["effective_query_interval"] != expected:
        _fail()


def _saved_columns(hsp, subject):
    native, correspondence, components = hsp["native_hsp"], hsp["correspondence"], hsp["native_components"]
    _keys(correspondence, "traceback_status geometry_status native_scores reported_counts reported_percentages columns issues")
    for field in ("traceback_status", "geometry_status"):
        _enum(correspondence[field], {"available", "unavailable", "incompatible"})
    _keys(components, "native_scores reported_counts reported_percentages counts fractions denominators coordinate_units traceback_available geometry_available pairs issues")
    for name in ("native_scores", "reported_counts", "reported_percentages"):
        if components[name] != correspondence[name]:
            _fail()
    _keys(components["native_scores"], "bit_score score evalue")
    for name, value in components["native_scores"].items():
        _nullable(value, _num)
        original = native.get(name)
        expected = original if type(original) in (int, float) and (name != "evalue" or original >= 0) else None
        if value != expected:
            _fail()
    _keys(components["reported_counts"], "align_len identity positive gaps")
    _keys(components["reported_percentages"], "identity_percent query_coverage_percent query_subject_coverage_percent query_unique_subject_coverage_percent")
    for count in components["reported_counts"].values():
        _nullable(count, _int)
    for value in components["reported_percentages"].values():
        _nullable(value, _num)
    _bool(components["traceback_available"]); _bool(components["geometry_available"])
    _keys(components["coordinate_units"], "query reference alignment")
    _keys(components["fractions"], "query_paired_coverage reference_paired_coverage paired_identity alignment_identity")
    _keys(components["denominators"], "query_length reference_length paired_columns alignment_columns")
    axis = subject["coordinate_context"]
    if (components["denominators"]["query_length"] != (axis["query"]["full_length"] or axis["query"]["reported_length"])
            or components["denominators"]["reference_length"] != (axis["reference"]["reported_length"] or axis["reference"]["full_length"])):
        _fail()
    count_fields = "alignment_columns paired_columns identical_pairs query_gap_columns reference_gap_columns"
    if components["geometry_available"]:
        count_fields += " paired_query_positions paired_reference_positions"
    _keys(components["counts"], count_fields)
    for value in [*components["counts"].values(), *components["denominators"].values()]:
        _nullable(value, _int)
    for value in components["fractions"].values():
        _nullable(value, _num)
    _array(components["pairs"], lambda p: _keys(p, "query_start query_end reference_start reference_end identical"))
    def column(c):
        _keys(c, "column query_symbol reference_symbol query_interval reference_interval query_unit reference_unit alignment_unit relationship query_direction query_frame query_strand reference_direction reference_frame reference_strand")
        _int(c["column"]); _str(c["query_symbol"]); _str(c["reference_symbol"])
        for axis in ("query", "reference"):
            _nullable(c[axis + "_interval"], _interval)
            _nullable(c[axis + "_direction"], lambda n: _enum(n, {-1, 1}))
            if c[axis + "_frame"] is not None and type(c[axis + "_frame"]) is not int:
                _fail()
            _nullable(c[axis + "_strand"], lambda v: _enum(v, {"Plus", "Minus"}))
            _enum(c[axis + "_unit"], {"nt", "aa"})
        _enum(c["alignment_unit"], {"nt", "aa"})
        _enum(c["relationship"], {"identical", "substituted", "query_gap", "reference_gap"})
    _array(correspondence["columns"], column)
    columns = correspondence["columns"]
    if not components["traceback_available"]:
        if columns:
            _fail()
        return
    query, reference = native.get("qseq"), native.get("hseq")
    if (not isinstance(query, str) or not isinstance(reference, str) or len(query) != len(reference)
            or len(columns) != len(query)):
        _fail()
    for i, c in enumerate(columns):
        a, b = query[i], reference[i]
        relationship = "query_gap" if a == "-" else "reference_gap" if b == "-" else "identical" if a.upper() == b.upper() else "substituted"
        if c["column"] != i or c["query_symbol"] != a or c["reference_symbol"] != b or c["relationship"] != relationship:
            _fail()
        if any(c[k + "_unit"] != components["coordinate_units"][k] for k in ("query", "reference", "alignment")):
            _fail()
    if correspondence["geometry_status"] != "available":
        if any(c["query_interval"] is not None or c["reference_interval"] is not None for c in columns):
            _fail()
        return
    if not components["geometry_available"]:
        _fail()
    for axis, prefix, symbols in (("query", "query", query), ("reference", "hit", reference)):
        first, last = native.get(prefix + "_from"), native.get(prefix + "_to")
        _int(first, 1); _int(last, 1)
        unit = components["coordinate_units"][axis]
        width = 3 if unit == "nt" and components["coordinate_units"]["alignment"] == "aa" else 1
        direction = 1 if last >= first else -1
        frame = native.get(prefix + "_frame")
        if hsp["source_locator"]["native_format"] == "json2" and width == 3 and type(frame) is int and frame < 0 and first < last:
            first, last, direction = last, first, -1
        length = components["denominators"][axis + "_length"]
        if abs(last - first) + 1 != sum(s != "-" for s in symbols) * width or length is not None and max(first, last) > length:
            _fail()
        if width == 3 and frame is not None:
            if type(frame) is not int or frame not in (-3, -2, -1, 1, 2, 3) or (frame > 0) != (direction > 0):
                _fail()
            phase = (first - 1) % 3 + 1 if direction == 1 else (length - first) % 3 + 1 if length is not None else None
            if phase is not None and phase != abs(frame):
                _fail()
        cursor = first - 1 if direction == 1 else first
        for c, symbol in zip(columns, symbols):
            interval = None if symbol == "-" else [cursor, cursor + width] if direction == 1 else [cursor - width, cursor]
            if c[axis + "_interval"] != interval:
                _fail()
            if symbol != "-":
                cursor += direction * width
            expected_direction = direction if first != last else 1 if unit == "aa" or native.get(prefix + "_strand") == "Plus" else -1 if native.get(prefix + "_strand") == "Minus" else None
            if c[axis + "_direction"] != expected_direction or c[axis + "_frame"] != (frame if type(frame) is int else None):
                _fail()
    pairs = [dict(query_start=c["query_interval"][0], query_end=c["query_interval"][1],
                  reference_start=c["reference_interval"][0], reference_end=c["reference_interval"][1],
                  identical=c["relationship"] == "identical") for c in columns if c["query_interval"] is not None and c["reference_interval"] is not None]
    if components["pairs"] != pairs or components["counts"]["paired_columns"] != len(pairs):
        _fail()


def _saved_translation(sheet, feature):
    mapping = feature["translation_map"]
    if mapping is None:
        return
    _keys(mapping, "status unavailable_reason member_sequence_metadata_key translation_metadata_key genetic_code codon_start strand leading_untranslated_member_positions trailing_untranslated_member_positions codons issues")
    _enum(mapping["status"], {"available", "unavailable", "incompatible"})
    _nullable(mapping["unavailable_reason"], _str)
    if (mapping["status"] == "available") != (mapping["unavailable_reason"] is None):
        _fail()
    for field in ("member_sequence_metadata_key", "translation_metadata_key"):
        _nullable(mapping[field], _str)
    _nullable(mapping["genetic_code"], lambda x: _int(x, 1))
    _nullable(mapping["codon_start"], lambda x: _enum(x, {1, 2, 3}))
    _nullable(mapping["strand"], lambda x: _enum(x, {-1, 1}))
    for name in ("leading_untranslated_member_positions", "trailing_untranslated_member_positions"):
        _nullable(mapping[name], lambda v: _array(v, _int))
    def codon(c):
        _keys(c, "ordinal member_positions oriented_triplet translated_symbol feature_residue_index feature_symbol terminal_stop")
        _int(c["ordinal"]); _array(c["member_positions"], _int)
        _str(c["oriented_triplet"]); _str(c["translated_symbol"])
        _nullable(c["feature_residue_index"], _int); _nullable(c["feature_symbol"], _str); _bool(c["terminal_stop"])
        if len(c["member_positions"]) != 3 or len(c["oriented_triplet"]) != 3 or len(c["translated_symbol"]) != 1:
            _fail()
    _array(mapping["codons"], codon); _array(mapping["issues"], _issue_shape)
    if mapping["status"] != "available":
        return
    metadata = {m["metadata_key"]: m for m in sheet["reference_metadata"]}
    if mapping["translation_metadata_key"] not in metadata or mapping["member_sequence_metadata_key"] not in metadata:
        _fail("reference_out_of_range")
    raw = metadata[mapping["translation_metadata_key"]]["feature"]
    sequence = metadata[mapping["member_sequence_metadata_key"]]["sequence"]
    if raw is None or sequence is None or not raw["translation"] or len(raw["segments"]) != 1:
        _fail()
    if any(raw[k] != mapping[k] for k in ("genetic_code", "codon_start", "strand")):
        _fail()
    dataset = next(d for d in sheet["dataset_records"] if d["dataset_key"] == feature["member_key"]["dataset_key"])
    if dataset["search_context"]["subject_genetic_code"] != mapping["genetic_code"]:
        _fail()
    a, b = raw["segments"][0]
    positions = list(range(a, b)) if mapping["strand"] == 1 else list(range(b - 1, a - 1, -1))
    bases = sequence["symbols"][a:b]
    if mapping["strand"] == -1:
        bases = str(_Seq(bases).reverse_complement())
    offset = mapping["codon_start"] - 1
    coding = bases[offset:]; coding_positions = positions[offset:]
    usable = len(coding) - len(coding) % 3
    if (mapping["leading_untranslated_member_positions"] != positions[:offset]
            or mapping["trailing_untranslated_member_positions"] != coding_positions[usable:]):
        _fail()
    try:
        translated = str(_Seq(coding[:usable]).translate(table=mapping["genetic_code"], cds=False))
    except (ValueError, KeyError):
        _fail()
    supplied = "".join(raw["translation"].split()).upper()
    if len(mapping["codons"]) != len(translated):
        _fail()
    for i, c in enumerate(mapping["codons"]):
        expected = dict(ordinal=i, member_positions=coding_positions[3*i:3*i+3], oriented_triplet=coding[3*i:3*i+3],
            translated_symbol=translated[i], feature_residue_index=i if i < len(supplied) else None,
            feature_symbol=supplied[i] if i < len(supplied) else None, terminal_stop=translated[i] == "*" and i == len(translated)-1)
        if c != expected:
            _fail()


def _saved_base(sheet, base):
    _keys(base, "schema search_key status hsps subjects membership sequence_groups sample_groups feature_components taxonomy source_quality population_components issues", "sheet_schema_invalid")
    if base["schema"] != "blast_vdb_components_v1" or base["search_key"] != sheet["search"]["search_key"]:
        _fail("sheet_schema_invalid")
    _enum(base["status"], {"complete", "partial", "no_reported_hits", "unavailable", "incompatible"})
    _array(base["issues"], _issue_shape)
    for key in ("hsps", "subjects", "feature_components"):
        if type(base[key]) is not list:
            _fail()
    _keys(base["membership"], "row_keys native_search_statistics selected_dataset_keys reported_subject_count reported_hsp_count origin_bound_subject_count origin_unbound_subject_count origin_ambiguous_subject_count origins catalogue_members origin_members counts_by_kind complete_for_reported_subjects")
    _keys(base["sequence_groups"], "groups demonstrated_group_count grouped_subject_count ungrouped_subject_count duplicate_subject_representations complete_for_reported_subjects")
    _keys(base["sample_groups"], "groups observed_origin_sample_count catalog_sample_count unresolved_origin_member_count complete_for_origin_members")
    _keys(base["taxonomy"], "subject_taxa sample_context sequence_group_ranks target_status target_independent_of_search issues")
    _keys(base["source_quality"], "records missing_member_keys issues")
    _keys(base["population_components"], "records function_weight_model issues")
    for section in ("taxonomy", "source_quality", "population_components"):
        _array(base[section]["issues"], _issue_shape)
    _enum(base["taxonomy"]["target_status"], {"available", "unavailable", "incompatible"})
    _nullable(base["taxonomy"]["target_independent_of_search"], _bool)
    _array(base["source_quality"]["missing_member_keys"], _member)
    if base["population_components"]["function_weight_model"] != dict(status="unavailable", components=None, reason="vdb_function_weight_model_not_defined"):
        _fail()
    _saved_measure_shapes(base)
    for obj, field in ((base["membership"], "complete_for_reported_subjects"), (base["sequence_groups"], "complete_for_reported_subjects"), (base["sample_groups"], "complete_for_origin_members")):
        _bool(obj[field])
    membership = base["membership"]
    _cells(membership, "reported_subject_count reported_hsp_count origin_bound_subject_count origin_unbound_subject_count origin_ambiguous_subject_count")
    _array(membership["selected_dataset_keys"], _str)
    if type(membership["native_search_statistics"]) is not dict:
        _fail()
    _cells(base["sequence_groups"], "demonstrated_group_count grouped_subject_count ungrouped_subject_count duplicate_subject_representations")
    _cells(base["sample_groups"], "observed_origin_sample_count catalog_sample_count unresolved_origin_member_count")
    _keys(membership["row_keys"], "search hits")
    _rowkey(membership["row_keys"]["search"])
    if membership["row_keys"]["search"] != dict(search_key=base["search_key"], hit_ordinal=None, hsp_ordinal=None, description_ordinal=None):
        _fail("reference_out_of_range")
    row_index = {}
    for hit in membership["row_keys"]["hits"]:
        _keys(hit, "component_index row_key source_locator hsps descriptions")
        _int(hit["component_index"]); _stored_source(sheet, hit["row_key"], hit["source_locator"])
        row_index[_token(hit["row_key"])] = hit
        for group in ("hsps", "descriptions"):
            for row in hit[group]:
                _keys(row, "component_index row_key source_locator")
                _int(row["component_index"]); _stored_source(sheet, row["row_key"], row["source_locator"])
                token = _token(row["row_key"])
                if token in row_index:
                    _fail("record_key_duplicate")
                row_index[token] = row
    _unique(membership["row_keys"]["hits"], "row_key")
    if base["status"] in {"complete", "partial", "no_reported_hits"}:
        original_hits = sheet["search"]["normalized"]["hits"]
        if len(membership["row_keys"]["hits"]) != len(original_hits):
            _fail("reference_out_of_range")
        for ordinal, hit in enumerate(membership["row_keys"]["hits"]):
            original = original_hits[ordinal]
            mapping = sheet["search"]["row_map"][ordinal]
            if hit["component_index"] != ordinal or hit["row_key"]["hit_ordinal"] != original["hit_index"]:
                _fail("reference_out_of_range")
            for field, key in (("hsps", "hsp_ordinal"), ("descriptions", "description_ordinal")):
                if [r["component_index"] for r in hit[field]] != list(range(len(original[field]))):
                    _fail("reference_out_of_range")
                if [r["row_key"][key] for r in hit[field]] != mapping["hsp_ordinals" if field == "hsps" else "description_ordinals"]:
                    _fail("reference_out_of_range")
    _unique(base["subjects"], "row_key"); _unique(base["hsps"], "row_key")
    if {_token(s["row_key"]) for s in base["subjects"]} != {_token(h["row_key"]) for h in membership["row_keys"]["hits"]}:
        _fail("reference_out_of_range")
    if {_token(h["row_key"]) for h in base["hsps"]} != {_token(h["row_key"]) for hit in membership["row_keys"]["hits"] for h in hit["hsps"]}:
        _fail("reference_out_of_range")
    for subject in base["subjects"]:
        _keys(subject, "row_key source_locator hsp_row_keys descriptions coordinate_context geometry_complete observed_paired_query_intervals observed_paired_reference_intervals observed_paired_query_units observed_paired_reference_nt full_query_coverage selected_query_coverage reported_reference_coverage full_member_coverage maximum_bit_score minimum_evalue hsp_count member_binding_indices sequence_group_key issues")
        _stored_source(sheet, subject["row_key"], subject["source_locator"])
        _array(subject["hsp_row_keys"], _rowkey); _array(subject["member_binding_indices"], _int)
        _bool(subject["geometry_complete"]); _array(subject["issues"], _issue_shape)
        _cells(subject, "observed_paired_query_units observed_paired_reference_nt hsp_count",
            "full_query_coverage selected_query_coverage reported_reference_coverage full_member_coverage")
        _cells(subject, "maximum_bit_score minimum_evalue", integer=False)
        for field in ("observed_paired_query_intervals", "observed_paired_reference_intervals"):
            _array(subject[field], _interval)
        _nullable(subject["sequence_group_key"], _str)
        for description in subject["descriptions"]:
            _keys(description, "row_key source_locator native_description")
            _stored_source(sheet, description["row_key"], description["source_locator"])
            if _token(description["row_key"]) not in row_index or type(description["native_description"]) is not dict:
                _fail("reference_out_of_range")
        if _token(subject["row_key"]) not in row_index:
            _fail("reference_out_of_range")
        if subject["hsp_row_keys"] != [r["row_key"] for r in row_index[_token(subject["row_key"])]["hsps"]]:
            _fail("reference_out_of_range")
        if any(i >= len(sheet["member_bindings"]) or sheet["member_bindings"][i]["hit_ordinal"] != subject["row_key"]["hit_ordinal"] for i in subject["member_binding_indices"]):
            _fail("reference_out_of_range")
        _keys(subject["coordinate_context"], "query reference")
        _keys(subject["coordinate_context"]["query"], "axis_kind reported_length full_length selected_interval effective_query_interval coordinate_unit")
        _keys(subject["coordinate_context"]["reference"], "reported_length full_length coordinate_unit")
        _saved_query_axis(sheet, base, subject["coordinate_context"]["query"])
        reference = subject["coordinate_context"]["reference"]
        original_hit = sheet["search"]["normalized"]["hits"][row_index[_token(subject["row_key"])]["component_index"]]
        if reference["coordinate_unit"] != "nt" or reference["reported_length"] != original_hit["length"]:
            _fail()
        _nullable(reference["full_length"], lambda n: _int(n, 1))
    for hsp in base["hsps"]:
        _keys(hsp, "row_key source_locator native_hsp geometry_program query_axis_kind reference_axis_kind native_components correspondence query_span reference_span substitutions full_query_coverage selected_query_coverage reported_reference_coverage full_member_coverage member_binding_indices issues")
        _stored_source(sheet, hsp["row_key"], hsp["source_locator"])
        _array(hsp["member_binding_indices"], _int); _array(hsp["issues"], _issue_shape)
        _cells(hsp, "query_span reference_span substitutions",
            "full_query_coverage selected_query_coverage reported_reference_coverage full_member_coverage")
        row = row_index.get(_token(hsp["row_key"]))
        if row is None or row["source_locator"] != hsp["source_locator"]:
            _fail("reference_out_of_range")
        subjects = [s for s in base["subjects"] if hsp["row_key"] in s["hsp_row_keys"]]
        if len(subjects) != 1:
            _fail("reference_out_of_range")
        subject = subjects[0]
        if hsp["member_binding_indices"] != subject["member_binding_indices"]:
            _fail()
        if hsp["geometry_program"] != sheet["search"]["program_context"]["geometry_program"]:
            _fail()
        if hsp["source_locator"]["native_format"] == "json2":
            try:
                native = sheet["search"]["native"]["search"]["hits"][hsp["row_key"]["hit_ordinal"]]["hsps"][hsp["row_key"]["hsp_ordinal"]]
            except (KeyError, IndexError, TypeError):
                _fail("reference_out_of_range")
        else:
            hits = [h for h in sheet["search"]["normalized"]["hits"] if h["hit_index"] == hsp["row_key"]["hit_ordinal"]]
            if len(hits) != 1 or row["component_index"] >= len(hits[0]["hsps"]):
                _fail("reference_out_of_range")
            native = {k: v for k, v in hits[0]["hsps"][row["component_index"]].items() if k != "source_locator"}
        if hsp["native_hsp"] != native:
            _fail()
        _saved_columns(hsp, subject)
    for origin in membership["origins"]:
        _keys(origin, "row_key status member_keys binding_indices")
        _rowkey(origin["row_key"]); _enum(origin["status"], {"available", "unavailable", "ambiguous", "incompatible"})
        _array(origin["member_keys"], _member); _array(origin["binding_indices"], _int)
        if _token(origin["row_key"]) not in row_index:
            _fail("reference_out_of_range")
        if origin["status"] == "available":
            if not origin["binding_indices"] or len(origin["member_keys"]) != 1:
                _fail()
            for i in origin["binding_indices"]:
                if i >= len(sheet["member_bindings"]):
                    _fail("reference_out_of_range")
                member = sheet["member_bindings"][i]
                if (member["relationship"] != "reported_origin" or _mkey(member) != origin["member_keys"][0]
                        or member["search_key"] != base["search_key"] or member["hit_ordinal"] != origin["row_key"]["hit_ordinal"]):
                    _fail()
        elif origin["member_keys"] or origin["binding_indices"]:
            _fail()
    for field in ("catalogue_members", "origin_members"):
        for row in membership[field]:
            _keys(row, "member_key binding_indices row_keys")
            _member(row["member_key"]); _array(row["binding_indices"], _int); _array(row["row_keys"], _rowkey)
            if any(i >= len(sheet["member_bindings"]) or _mkey(sheet["member_bindings"][i]) != row["member_key"] for i in row["binding_indices"]):
                _fail("reference_out_of_range")
    for row in membership["counts_by_kind"]:
        _keys(row, "kind catalog_member_count origin_member_count")
        _str(row["kind"]); _cells(row, "catalog_member_count origin_member_count")
    for group in base["sequence_groups"]["groups"]:
        _keys(group, "sequence_group_key digest molecule length subject_row_keys member_keys binding_indices subject_count member_count")
        _digest(group["digest"]); _int(group["length"], 1)
        if group["molecule"] != "nt" or group["sequence_group_key"] != "sha256:" + group["digest"]:
            _fail()
        _array(group["subject_row_keys"], _rowkey); _array(group["member_keys"], _member); _array(group["binding_indices"], _int)
        _cells(group, "subject_count member_count")
    for group in base["sample_groups"]["groups"]:
        _keys(group, "sample_key sample_identifier biosample_identifiers dataset_keys origin_member_keys catalog_member_keys origin_subject_row_keys metadata_keys")
        _str(group["sample_key"]); _identity(group["sample_identifier"])
        _array(group["biosample_identifiers"], _identity); _array(group["dataset_keys"], _str)
        _array(group["origin_member_keys"], _member); _array(group["catalog_member_keys"], _member)
        _array(group["origin_subject_row_keys"], _rowkey); _array(group["metadata_keys"], _str)
    for feature in base["feature_components"]:
        _keys(feature, "feature_binding_indices member_key feature_identifier functions relation_status hsp_rows translation_map paired_reference_overlap_nt feature_length_nt feature_paired_nt_coverage paired_subject_fraction_in_feature corresponding_feature_residue_union feature_translation_length feature_paired_residue_coverage issues")
        _array(feature["feature_binding_indices"], _int); _member(feature["member_key"]); _identity(feature["feature_identifier"])
        if not feature["feature_binding_indices"]:
            _fail("reference_out_of_range")
        _unique(feature["feature_binding_indices"])
        _array(feature["functions"], _function); _array(feature["issues"], _issue_shape)
        _enum(feature["relation_status"], {"incompatible", "unavailable", "nonoverlap", "translated_correspondence", "overlap_only"})
        _cells(feature, "paired_reference_overlap_nt feature_length_nt feature_translation_length",
            "feature_paired_nt_coverage paired_subject_fraction_in_feature feature_paired_residue_coverage")
        _nullable(feature["corresponding_feature_residue_union"], lambda rows: _array(rows, _int))
        for i in feature["feature_binding_indices"]:
            if i >= len(sheet["feature_bindings"]):
                _fail("reference_out_of_range")
            binding = sheet["feature_bindings"][i]
            if _mkey(sheet["member_bindings"][binding["member_binding_index"]]) != feature["member_key"] or binding["feature_identifier"] != feature["feature_identifier"]:
                _fail()
        for row in feature["hsp_rows"]:
            _keys(row, "row_key paired_reference_overlap_nt aligned_reference_overlap_nt paired_query_overlap_units complete_paired_codons partial_codon_overlap_nt corresponding_feature_residues identical_query_feature_residues substitutions_query_feature issues")
            _rowkey(row["row_key"]); _array(row["issues"], _issue_shape)
            _cells(row, "paired_reference_overlap_nt aligned_reference_overlap_nt paired_query_overlap_units complete_paired_codons partial_codon_overlap_nt corresponding_feature_residues identical_query_feature_residues substitutions_query_feature")
            if _token(row["row_key"]) not in row_index:
                _fail("reference_out_of_range")
        _saved_translation(sheet, feature)
    for row in base["taxonomy"]["subject_taxa"]:
        _keys(row, "row_key taxids metadata_keys status")
        _rowkey(row["row_key"]); _array(row["taxids"], lambda n: _int(n, 1)); _array(row["metadata_keys"], _str)
        _enum(row["status"], {"available", "ambiguous", "unavailable"})
    for row in base["taxonomy"]["sample_context"]:
        _keys(row, "sample_key taxids metadata_keys")
        _str(row["sample_key"]); _array(row["taxids"], lambda n: _int(n, 1)); _array(row["metadata_keys"], _str)
    for row in base["taxonomy"]["sequence_group_ranks"]:
        _keys(row, "rank taxon_group_counts unambiguous_group_count ambiguous_group_count unknown_group_count same_taxon_pair_count comparable_pair_count same_taxon_pair_fraction different_taxon_pair_fraction target_taxid target_matching_groups target_conflicting_groups target_ambiguous_groups target_matching_fraction")
        _str(row["rank"])
        for count in row["taxon_group_counts"]:
            _keys(count, "taxid count"); _int(count["taxid"], 1); _int(count["count"])
        for field in ("unambiguous_group_count", "ambiguous_group_count", "unknown_group_count", "same_taxon_pair_count", "comparable_pair_count"):
            _int(row[field])
        _nullable(row["target_taxid"], lambda n: _int(n, 1))
        for field in ("target_matching_groups", "target_conflicting_groups", "target_ambiguous_groups"):
            _nullable(row[field], _int)
        _cells(row, ratios="same_taxon_pair_fraction different_taxon_pair_fraction target_matching_fraction")
    for row in base["source_quality"]["records"]:
        _keys(row, "metadata_key dataset_key member_keys assembly_identifier method method_version completeness_fraction contamination_fraction contig_count contig_n50 total_sequence_length source linkage_source")
        _str(row["metadata_key"]); _nullable(row["dataset_key"], _str); _array(row["member_keys"], _member)
        _nullable(row["assembly_identifier"], _identity); _nullable(row["method"], _str); _nullable(row["method_version"], _str)
        _prov(row["source"]); _nullable(row["linkage_source"], _prov)
        _cells(row, "completeness_fraction contamination_fraction", integer=False)
        _cells(row, "contig_count contig_n50 total_sequence_length")
    for row in base["population_components"]["records"]:
        _keys(row, "population_key count_unit status matched_dataset_keys total_count observed_entity_count observed_fraction_of_supplied_population function_components issues")
        _str(row["population_key"]); _str(row["count_unit"]); _enum(row["status"], {"available", "unavailable", "incompatible"})
        _array(row["matched_dataset_keys"], _str); _array(row["issues"], _issue_shape)
        _cells(row, "total_count observed_entity_count", "observed_fraction_of_supplied_population")
        for function in row["function_components"]:
            _keys(function, "function assignment_scope population_function_count population_function_fraction observed_function_entity_count observed_fraction_of_function_population")
            _function(function["function"]); _enum(function["assignment_scope"], {"whole_sequence", "feature", "sample"})
            _cells(function, "population_function_count observed_function_entity_count", "population_function_fraction observed_fraction_of_function_population")


def _entity_shape(row):
    _keys(row, _ENTITY_FIELDS)
    _str(row["entity_key"]); _address(row["address"])
    _array(row["subject_rows"], _rowkey); _array(row["member_binding_indices"], _int)
    _array(row["metadata_keys"], _str); _nullable(row["parent_sequence_identity"], _sequence_identity)
    _nullable(row["target_identity"], _target_identity)
    _enum(row["origin_status"], {"available", "unavailable", "ambiguous", "incompatible"})
    _enum(row["sample_relation_status"], {"available", "unavailable", "incompatible"})
    _array(row["origin_sample_keys"], _str); _array(row["eligible_hsp_rows"], _rowkey)
    _array(row["assignment_keys"], _str); _array(row["issues"], _issue_shape)
    for name in ("subject_rows", "member_binding_indices", "metadata_keys", "origin_sample_keys", "eligible_hsp_rows", "assignment_keys"):
        _unique(row[name])


def _reason(value):
    if value is not None and value not in {_PREFIX + r for r in _REASONS}:
        _fail()


def _observation_shape(row):
    _keys(row, _OBS_FIELDS)
    _str(row["observation_key"]); _str(row["entity_key"])
    _nullable(row["assignment_key"], _str); _nullable(row["function"], _function)
    _rowkey(row["row_key"]); _locator(row["source_locator"])
    _enum(row["qualification"], {"available", "unavailable", "incompatible", "not_applicable"})
    _reason(row["reason_code"]); _pointer(row["base_component_pointer"])
    _nullable(row["feature_component_pointer"], _pointer); _array(row["issues"], _issue_shape)
    for name in ("native_bit_score", "native_evalue", "paired_query_units", "paired_reference_nt", "aligned_reference_nt", "attributable_reference_nt", "corresponding_feature_residues"):
        _measure_shape(row[name], integer=name not in {"native_bit_score", "native_evalue"})
    if (row["assignment_key"] is None) != (row["function"] is None):
        _fail()
    if (row["qualification"] == "available") != (row["reason_code"] is None):
        _fail()


def _link_shape(row):
    _keys(row, "record_kind record_key status reason_code input_pointers issues")
    _enum(row["record_kind"], {"assignment", "dependency", "census"})
    _str(row["record_key"]); _enum(row["status"], {"available", "unavailable", "incompatible"})
    _reason(row["reason_code"]); _array(row["input_pointers"], _pointer); _array(row["issues"], _issue_shape)
    if not row["input_pointers"] or (row["status"] == "available") != (row["reason_code"] is None):
        _fail()


def validate_blast_vdb_function_sheet(sheet: dict) -> dict:
    """Return a detached, value-identical sheet after saved-relation validation.

    Checks use only fields already saved, including original rows and complete
    source proofs. They perform no native parser, base calculator or population
    call and do not change a stored number, qualification, order or pointer.
    """
    result = _copy(sheet)
    _keys(result, _FIELDS, "sheet_schema_invalid")
    if result["schema"] != _SCHEMA:
        _fail("sheet_schema_invalid")
    source, base = result["base_sheet"], result["base_components"]
    _base_shape(source)
    try:
        _saved_base(source, base)
    except (KeyError, TypeError, IndexError):
        _fail("sheet_schema_invalid")
    for field, check in (("assignment_records", _assignment_shape), ("dependency_records", _dependency_shape), ("census_records", _census_shape),
            ("entities", _entity_shape), ("observations", _observation_shape), ("link_results", _link_shape), ("issues", _issue_shape)):
        _array(result[field], check)
    for field, key in (("dependency_records", "dependency_key"), ("census_records", "census_key"), ("entities", "entity_key"), ("observations", "observation_key")):
        _unique(result[field], key)
    _unique([e["address"] for e in result["entities"]])
    _unique([[r["record_kind"], r["record_key"]] for r in result["link_results"]])
    entities = {e["entity_key"]: e for e in result["entities"]}
    assignments = {}
    for i, row in enumerate(result["assignment_records"]):
        assignments.setdefault(row["assignment_key"], []).append((i, row))
    # Literal metadata records are mandatory saved inputs. Check their source
    # relations without reparsing native bytes or invoking a population port.
    extraction = _extract(source)
    for original in extraction["records"]:
        candidates = [r for _, r in assignments.get(original["assignment_key"], [])
            if all(r[k] == v for k, v in original.items() if k != "sources")]
        if len(candidates) != 1 or any(p not in candidates[0]["sources"] for p in original["sources"]):
            _fail("reference_out_of_range")
    contexts = {}
    actual_addresses = _distinct([_addr(_mkey(m)) for m in source["member_bindings"]]
        + [_addr(_mkey(source["member_bindings"][f["member_binding_index"]]), f["feature_identifier"]) for f in source["feature_bindings"]])
    if {_token(e["address"]) for e in entities.values()} != {_token(a) for a in actual_addresses}:
        _fail("reference_out_of_range")
    for entity in entities.values():
        address = entity["address"]
        if entity["entity_key"] != _key("entity", address):
            _fail()
        context = _entity_context(source, base, address); contexts[entity["entity_key"]] = context
        sequence = context["sequence"]
        expected = dict(subject_rows=[s["row_key"] for s in context["subjects"]], member_binding_indices=context["indices"],
            metadata_keys=[m["metadata_key"] for m in source["reference_metadata"] if _meta_matches(m, address) or _meta_matches(m, address, "member")],
            parent_sequence_identity={k: sequence[k] for k in ("molecule", "sha256", "length")} if sequence else None,
            target_identity=context["target"], origin_status=context["origin"], origin_sample_keys=context["samples"], sample_relation_status=context["sample_status"],
            issues=_entity_issues(source, address, context))
        if any(entity[k] != v for k, v in expected.items()):
            _fail()
        expected_keys = {a["assignment_key"] for a in result["assignment_records"] if _assignment_address(a) == address}
        if set(entity["assignment_keys"]) != expected_keys:
            _fail("reference_out_of_range")
    link_map = {(r["record_kind"], r["record_key"]): r for r in result["link_results"]}
    expected_links = {("assignment", key) for key in assignments}
    expected_links |= {("dependency", r["dependency_key"]) for r in result["dependency_records"]}
    expected_links |= {("census", r["census_key"]) for r in result["census_records"]}
    if set(link_map) != expected_links:
        _fail("reference_out_of_range")
    for key, rows in assignments.items():
        link = link_map[("assignment", key)]
        if set(link["input_pointers"]) != {f"/assignment_records/{i}" for i, _ in rows}:
            _fail("reference_out_of_range")
        own = []
        for _, row in rows:
            own += _assignment_issues(source, base, row, len(rows) > 1)
            address = _assignment_address(row)
            if address is not None and address not in actual_addresses:
                own.append(_issue(source, "assignment_entity_conflict", assignment_key=key, target=row["target"]))
        if link != _link("assignment", key, link["input_pointers"], _distinct(own)):
            _fail()
        if len(rows) > 1 and len({_token({k: v for k, v in row.items() if k != "sources"}) for _, row in rows}) != len(rows):
            _fail("record_key_duplicate")
    for field, kind, keyfield in (("dependency_records", "dependency", "dependency_key"), ("census_records", "census", "census_key")):
        for i, row in enumerate(result[field]):
            link = link_map[(kind, row[keyfield])]
            expected_pointers = [f"/{field}/{i}"]
            if link["input_pointers"] != expected_pointers:
                _fail("reference_out_of_range")
            own = (_dependency_issues(source, row, {_token(a) for a in actual_addresses}) if kind == "dependency" else
                   _census_issues(source, row, result["entities"], result["assignment_records"], result["observations"]))
            if link != _link(kind, row[keyfield], expected_pointers, own):
                _fail()
    eligible = {key: [] for key in entities}
    assigned_observations = set()
    for observation in result["observations"]:
        entity = entities.get(observation["entity_key"])
        if entity is None:
            _fail("reference_out_of_range")
        pointer = observation["base_component_pointer"]
        if not _re.fullmatch(r"/base_components/hsps/(0|[1-9][0-9]*)", pointer):
            _fail("reference_out_of_range")
        hsp = _get(result, pointer)
        if hsp["row_key"] != observation["row_key"] or hsp["source_locator"] != observation["source_locator"]:
            _fail("reference_out_of_range")
        context = contexts[entity["entity_key"]]
        if not any(hsp["row_key"] in s["hsp_row_keys"] for s in context["subjects"]):
            _fail("reference_out_of_range")
        key = observation["assignment_key"]
        candidates = []
        if key is not None:
            if key not in assignments or len(assignments[key]) != 1 or key not in entity["assignment_keys"]:
                _fail("reference_out_of_range")
            assignment = assignments[key][0][1]
            if assignment["function"] != observation["function"]:
                _fail()
            candidates = [assignment]
            assigned_observations.add((entity["entity_key"], key, _token(hsp["row_key"])))
        elif entity["address"]["assignment_scope"] == "whole_sequence" and source["search"]["program_context"]["execution_program"] == "tblastn_vdb":
            candidates = [a for name in entity["assignment_keys"] if link_map[("assignment", name)]["status"] == "available" for _, a in assignments[name]]
        else:
            candidates = [None]
        valid = False
        for assignment in candidates:
            values, feature_pointer, issues = _hsp_facts(source, base, entity["address"], context, hsp, assignment)
            if key is not None:
                issues = _distinct([*link_map[("assignment", key)]["issues"], *issues])
            elif issues:
                continue
            relation = _link("assignment", "unused", [], issues)
            expected_key = _key("observation", [entity["entity_key"], key, hsp["row_key"]])
            if (observation["observation_key"] == expected_key and observation["feature_component_pointer"] == feature_pointer
                    and observation["qualification"] == relation["status"] and observation["reason_code"] == relation["reason_code"]
                    and observation["issues"] == issues and all(observation[k] == v for k, v in values.items())):
                valid = True; break
        if not valid:
            _fail()
        if key is None:
            if observation["qualification"] != "available":
                _fail()
            eligible[entity["entity_key"]].append(observation["row_key"])
    for entity in entities.values():
        if {_token(r) for r in entity["eligible_hsp_rows"]} != {_token(r) for r in eligible[entity["entity_key"]]}:
            _fail("reference_out_of_range")
        context = contexts[entity["entity_key"]]
        independent = [None]
        if entity["address"]["assignment_scope"] == "whole_sequence" and source["search"]["program_context"]["execution_program"] == "tblastn_vdb":
            independent = [a for name in entity["assignment_keys"] if link_map[("assignment", name)]["status"] == "available" for _, a in assignments[name]]
        expected_eligible = []
        for hsp in base["hsps"]:
            if any(hsp["row_key"] in s["hsp_row_keys"] for s in context["subjects"]) and any(
                    not _hsp_facts(source, base, entity["address"], context, hsp, a)[2] for a in independent):
                expected_eligible.append(hsp["row_key"])
        if {_token(r) for r in eligible[entity["entity_key"]]} != {_token(r) for r in expected_eligible}:
            _fail("reference_out_of_range")
        for key in entity["assignment_keys"]:
            if len(assignments[key]) != 1:
                continue
            for subject in context["subjects"]:
                for row in subject["hsp_row_keys"]:
                    if (entity["entity_key"], key, _token(row)) not in assigned_observations:
                        _fail("reference_out_of_range")
    # All original upstream qualifications and every local dependent issue stay
    # visible. Additional saved issue rows are allowed only from their sources.
    expected_issues = [*base["issues"], *extraction["issues"]]
    expected_issues += [i for r in result["link_results"] + result["entities"] + result["observations"] for i in r["issues"]]
    if base["status"] in {"unavailable", "incompatible"}:
        expected_issues.append(_issue(source, "base_source_conflict" if base["status"] == "incompatible" else "base_source_unavailable"))
    if result["issues"] != _distinct(expected_issues):
        _fail()
    return result
