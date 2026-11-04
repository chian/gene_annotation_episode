"""Supplied VDB function metadata, using the original document/search boundary.

These standalone ports implement accepted338 and its wire addenda. They do not
register a consumer, acquire bytes or dispatch a worker. Callers retain every
validation envelope, including rejected originals. The existing342 populator
owns scientific links and original-HSP measurements; its unchanged base reader
may revalidate native source records already retained in the supplied sheet.
"""
from __future__ import annotations

from copy import deepcopy

from jsonschema import Draft202012Validator, validators

from . import blast_vdb_function_inputs as _inputs
from . import native_blast_database_metadata as _metadata

__all__ = ["validate_native_blast_vdb_function_metadata_payload",
           "populate_native_blast_vdb_function_sheets",
           "native_blast_vdb_function_metadata_schema"]

_CONSUMER = "vdb_function"
_SCHEMA_ID = "native_blast_vdb_function_metadata_v1"
_object, _array = _metadata._object, _metadata._array
_nullable, _enum = _metadata._nullable, _metadata._enum
_TOKEN, _I0, _I1 = _metadata._TOKEN, _metadata._I0, _metadata._I1
_PROV, _ID, _FUNCTION = _metadata._PROV, _metadata._IDENTIFIER, _metadata._FUNCTION
_SHA, _BOOL = _metadata._SHA, _metadata._BOOL
_MEMBER = _metadata._MEMBER_KEY
_ADDRESS = _object(assignment_scope=_enum("whole_sequence", "feature"),
    member_key=_MEMBER, feature_identifier=_nullable(_ID))
_ASSIGNMENT = _object(assignment_key=_TOKEN, function=_FUNCTION,
    assignment_scope=_enum("whole_sequence", "feature", "sample"),
    target=_object(member_key=_nullable(_MEMBER), feature_identifier=_nullable(_ID), sample_key=_nullable(_TOKEN)),
    metadata_key=_TOKEN, function_ordinal=_I0,
    scope_origin=_enum("native_feature_record", "supplied_explicit_scope"),
    scope_source=_PROV, whole_sequence_cds_feature_identifier=_nullable(_ID), sources=_array(_PROV))
_DEPENDENCY = _object(dependency_key=_TOKEN,
    relation=_enum("same_original_molecule", "same_library", "same_study", "declared_dependent"),
    entities=_array(_ADDRESS), sources=_array(_PROV), native_record={"type": ["object", "string"]})
_SEQUENCE_IDENTITY = _object(molecule=_enum("nt"), sha256=_SHA, length=_I1)
_TARGET_IDENTITY = _object(assignment_scope=_enum("whole_sequence", "feature"),
    representation=_enum("full_member_nt_v1", "oriented_feature_nt_v1"), molecule=_enum("nt"),
    sha256=_SHA, length=_I1, coding=_nullable(_object(genetic_code=_I1,
        codon_start={"type": "integer", "enum": [1, 2, 3]}, translation_sha256=_SHA, translation_length=_I1)))
_CENSUS = _object(census_key=_TOKEN, assignment_scope=_enum("whole_sequence", "feature"),
    function_namespace=_TOKEN, scope=_enum("searched_population", "dataset_census", "supplied_subset"),
    datasets=_array(_object(dataset_key=_TOKEN, identifier=_ID, snapshot=_metadata._SNAPSHOT,
        selected_input=_metadata._SELECTED, sra_mode={"type": "integer", "enum": [0, 1, 2]}, include_filtered_reads=_BOOL)),
    annotation_snapshot=_object(identifier=_ID, content_sha256=_SHA, assignment_namespace=_TOKEN, source=_PROV),
    enumeration=_object(base_count_unit=_enum("member_instance", "feature_instance"), reported_total=_nullable(_I0),
        complete=_BOOL, pagination_complete=_nullable(_BOOL), source=_PROV, native_record={"type": "object"}),
    entities=_array(_object(entity_key=_TOKEN, address=_ADDRESS, target_identity=_TARGET_IDENTITY,
        parent_sequence_identity=_SEQUENCE_IDENTITY, functions=_array(_FUNCTION),
        function_assignment_sources=_array(_PROV), origin_sample_keys=_array(_TOKEN),
        sample_relation_status=_enum("available", "unavailable", "incompatible"), source=_PROV)),
    dependency_records=_array(_DEPENDENCY),
    annotation_bindings=_array(_object(assignment_key=_TOKEN, census_entity_key=_TOKEN,
        annotation_snapshot_sha256=_SHA, source=_PROV)),
    identity_proofs=_array(_object(entity_key=_TOKEN, sequence_source=_PROV, linkage_source=_PROV,
        normalization=_enum("full_member_nt_v1", "oriented_feature_nt_v1"), symbols={"type": "string", "minLength": 1})),
    source=_PROV, native_record={"type": "object"})
_UNIT_FIELDS = dict(supplied_assignments=_array(_ASSIGNMENT), dependency_records=_array(_DEPENDENCY),
                    census_records=_array(_CENSUS))
_UNIT = _object(search_key=_metadata._SEARCH, **_UNIT_FIELDS)
_SCHEMA = _object(schema=_enum(_SCHEMA_ID), documents=_array(_metadata._DOCUMENT), searches=_array(_UNIT))
_SEARCH_KEY = _object(artifact_key=_TOKEN, member_ordinal=_nullable(_I0), report_index=_I0,
                      search_pointer=_metadata._POINTER)
_NORMALIZED_UNIT = _object(search_key=_SEARCH_KEY, **_UNIT_FIELDS)
_Validator = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda checker, value: type(value) is int))


def native_blast_vdb_function_metadata_schema() -> dict:
    """Return the single closed wire schema, detached from validator state."""
    return deepcopy(_SCHEMA)


def _shape(value, schema, pointer=""):
    error = next(_Validator(schema).iter_errors(value), None)
    if error is not None:
        path = pointer + "".join("/" + _metadata._escape(p) for p in error.absolute_path)
        raise _metadata._Invalid(path, "closed_payload_shape_invalid")


def _record_relationships(value, schema, pointer=""):
    """Closed field relationships only; scientific compatibility belongs to342."""
    if schema is _ASSIGNMENT:
        required = {"whole_sequence": {"member_key"}, "feature": {"member_key", "feature_identifier"},
                    "sample": {"sample_key"}}[value["assignment_scope"]]
        if {k for k, v in value["target"].items() if v is not None} != required:
            raise _metadata._Invalid(pointer + "/target", "entity_slots_invalid")
    elif schema is _ADDRESS:
        if (value["assignment_scope"] == "feature") != (value["feature_identifier"] is not None):
            raise _metadata._Invalid(pointer, "entity_slots_invalid")
    elif schema is _TARGET_IDENTITY:
        whole = value["assignment_scope"] == "whole_sequence"
        if whole != (value["representation"] == "full_member_nt_v1") or whole and value["coding"] is not None:
            raise _metadata._Invalid(pointer, "entity_slots_invalid")
    if type(value) is list:
        for i, row in enumerate(value):
            _record_relationships(row, schema.get("items", {}), pointer + "/" + str(i))
    elif type(value) is dict:
        for name, row in value.items():
            _record_relationships(row, schema.get("properties", {}).get(name, {}), pointer + "/" + _metadata._escape(name))


def _provenances(value, schema, pointer=""):
    if schema.get("x-wire") == "provenance":
        yield pointer, value
    elif type(value) is list:
        for i, row in enumerate(value):
            yield from _provenances(row, schema.get("items", {}), pointer + "/" + str(i))
    elif type(value) is dict:
        for name, row in value.items():
            yield from _provenances(row, schema.get("properties", {}).get(name, {}), pointer + "/" + _metadata._escape(name))


def _source_identities(documents):
    sources, artifacts = {}, {}
    for row in documents:
        sources.setdefault(row["source_ref"], set()).add((row["artifact_ref"], row["sha256"], row["size_bytes"]))
        artifacts.setdefault(row["artifact_ref"], set()).add((row["sha256"], row["size_bytes"]))
    return sources, artifacts


def _qualify_catalog_sources(value, result, catalog):
    """Reject contradictory source aliases without inventing a new locator."""
    normalized = result["normalized"]
    sources, artifacts = _source_identities(normalized["documents"])
    for i, doc in enumerate(normalized["documents"]):
        if len(sources[doc["source_ref"]]) != 1 or len(artifacts[doc["artifact_ref"]]) != 1:
            raise _metadata._Invalid(_metadata._original_pointer(result, f"/documents/{i}"),
                "document_source_identity_conflict", "relation_conflict", document=doc["document_key"])
    # Every provenance slot refers to the same retained document bytes, even if
    # the received document has a different key, artifact handle or source alias.
    docs = {d["document_key"]: d for d in normalized["documents"]}
    supplied = {d["document_key"]: d for d in catalog["documents"]}
    for i, unit in enumerate(normalized["searches"]):
        original = _metadata._original_pointer(result, f"/searches/{i}")
        wire = _metadata._pointer_get(value, original)
        for j, census in enumerate(wire["census_records"]):
            for suffix, provenance in _provenances(census, _CENSUS):
                doc = docs[provenance["source_ref"]]
                if any(doc["artifact_ref"] == r["artifact_ref"] or doc["source_ref"] == r["source_ref"]
                       or (doc["sha256"], doc["size_bytes"]) == (r["sha256"], r["size_bytes"])
                       for r in catalog["primary_reports"]):
                    result["issues"].append(_metadata._issue(result, "relation_conflict",
                        f"{original}/census_records/{j}" + suffix,
                        "vdb_function_input_records_conflict", document=doc["document_key"], search=wire["search_key"]))
            snapshot = census["annotation_snapshot"]
            source = snapshot["source"]
            doc = supplied[source["source_ref"]]
            if doc["format"] == "json":
                assertion = _metadata._pointer_get(_metadata._decode(doc["contents"]), source["pointer"])
                # A directly named digest assertion can contradict the claim.
                # A source document's own hash is a different identity (006).
                asserted_digest = assertion.get("content_sha256") if type(assertion) is dict else None
                if asserted_digest is not None and asserted_digest != snapshot["content_sha256"]:
                    result["issues"].append(_metadata._issue(result, "relation_conflict",
                        f"{original}/census_records/{j}/annotation_snapshot/source",
                        "vdb_function_input_records_conflict", document=doc["document_key"], search=wire["search_key"]))


def validate_native_blast_vdb_function_metadata_payload(payload, *, descriptor, document_catalog, job) -> dict:
    """Validate/lower supplied bytes; the acquiring caller authenticates custody.

The exact legacy envelope and normalization map retain rejected original inputs.
No filename, title, accession spelling or native report supplies function scope.
"""
    value = _metadata._copy(payload)
    result = {k: descriptor[k] for k in ("consumer", "schema_id", "input_key", "artifact_ref", "sha256")}
    result.update(status="valid", payload=value, normalized=None, normalization_map=[], issues=[])
    if (descriptor["consumer"], descriptor["schema_id"]) != (_CONSUMER, _SCHEMA_ID):
        result["status"] = "unsupported"
        result["issues"].append(_metadata._issue(descriptor, "schema_unsupported", "", "metadata_tuple_unregistered"))
        return result
    try:
        _metadata._validate_catalog(document_catalog, consumers=(_CONSUMER,))
        if document_catalog["descriptor"] != descriptor:
            raise _metadata._Invalid("", "descriptor_catalog_conflict")
        _shape(value, _SCHEMA)
        _record_relationships(value, _SCHEMA)
        result["normalized"] = _metadata._lower_payload(value, descriptor, document_catalog, job,
            result["issues"], result["normalization_map"], payload_schema=_SCHEMA)
        _qualify_catalog_sources(value, result, document_catalog)
    except _metadata._Invalid as error:
        result["status"] = "valid" if isinstance(error, _metadata._Unresolved) else "invalid"
        result["normalized"] = None
        result["normalization_map"] = []
        result["issues"].append(_metadata._issue(descriptor, error.code, error.pointer, error.detail,
            document=error.document, search=error.search))
    return result


def _population_issue(validation, pointer, detail, *, conflict, search=None):
    return _metadata._issue(validation, "relation_conflict" if conflict else "relation_unresolved",
        _metadata._original_pointer(validation, pointer), detail, search=search)


def _unit_source_error(validation, unit, catalog):
    used = {p["source_ref"] for _, p in _provenances(unit, _NORMALIZED_UNIT)}
    documents = [d for d in validation["normalized"]["documents"] if d["source_ref"] in used]
    if used != {d["source_ref"] for d in documents}:
        return "vdb_function_input_records_conflict", True
    for doc in documents:
        matches = [r for r in catalog["entries"] + catalog["retained_sources"]
                   if r["artifact_ref"] == doc["artifact_ref"]]
        if not matches:
            return "vdb_function_artifact_catalog_conflict", False
        if any(any(r[k] != doc[k] for k in ("source_ref", "sha256", "size_bytes")) for r in matches):
            return "vdb_function_artifact_catalog_conflict", True
    return None


def _usable_records(validation, pointer, unit):
    result = deepcopy(unit)
    for field in _UNIT_FIELDS:
        result[field] = []
        for i, row in enumerate(unit[field]):
            original = _metadata._original_pointer(validation, f"{pointer}/{field}/{i}")
            if not any(issue["pointer"] == original or issue["pointer"].startswith(original + "/")
                       for issue in validation["issues"]):
                result[field].append(deepcopy(row))
    return result


def populate_native_blast_vdb_function_sheets(base_sheet_set, *, prepared_inputs, artifact_catalog) -> dict:
    """Populate actual342 sheets after the VDB merge, preserving local failures.

This consumes validation envelopes and catalog facts already supplied by the
caller. It does not read catalog paths or populate/reparse the base VDB sheet.
Each scientific sheet retains its complete base and342's exact LinkResults.
"""
    base, prepared = _metadata._copy([base_sheet_set, prepared_inputs])
    if (type(base) is not dict or base.get("schema") != "native_blast_database_sheet_set_v1"
            or type(base.get("vdb")) is not list or type(prepared) is not dict
            or prepared.get("schema") != "native_blast_database_prepared_inputs_v1"
            or type(prepared.get("metadata")) is not list or type(artifact_catalog) is not dict
            or type(artifact_catalog.get("entries")) is not list or type(artifact_catalog.get("retained_sources")) is not list):
        raise ValueError("blast_vdb_function_sheet_schema_invalid")
    if any(type(row) is not dict or set(row) != {"search_key", "sheet"}
           or type(row["search_key"]) is not dict or type(row["sheet"]) is not dict for row in base["vdb"]):
        raise ValueError("blast_vdb_function_sheet_schema_invalid")
    for row in base["vdb"]:
        try:
            _shape(row["search_key"], _SEARCH_KEY)
        except _metadata._Invalid:
            raise ValueError("blast_vdb_function_sheet_schema_invalid") from None
    if any(type(row) is not dict or not {"artifact_ref", "source_ref", "sha256", "size_bytes"} <= row.keys()
           for row in artifact_catalog["entries"] + artifact_catalog["retained_sources"]):
        raise ValueError("blast_vdb_function_sheet_schema_invalid")
    if any(type(row) is not dict for row in prepared["metadata"]):
        raise ValueError("blast_vdb_function_sheet_schema_invalid")
    result = dict(schema="native_blast_vdb_function_population_v1", sheets=[], issues=[])
    units = []
    for validation in prepared["metadata"]:
        if validation.get("consumer") != _CONSUMER:
            continue
        result["issues"].extend(deepcopy(validation["issues"]))
        if validation["schema_id"] != _SCHEMA_ID or validation["status"] != "valid" or validation["normalized"] is None:
            continue
        for index, unit in enumerate(validation["normalized"]["searches"]):
            pointer = f"/searches/{index}"
            original = _metadata._original_pointer(validation, pointer)
            wire = _metadata._pointer_get(validation["payload"], original)
            search = wire["search_key"]
            try:
                _shape(unit, _NORMALIZED_UNIT)
                _record_relationships(unit, _NORMALIZED_UNIT)
            except _metadata._Invalid:
                result["issues"].append(_population_issue(validation, pointer,
                    "vdb_function_input_records_conflict", conflict=True, search=search))
                continue
            source_error = _unit_source_error(validation, unit, artifact_catalog)
            if source_error is not None:
                result["issues"].append(_population_issue(validation, pointer,
                    source_error[0], conflict=source_error[1], search=search))
                continue
            candidates = [r for r in base["vdb"] if r["search_key"] == unit["search_key"]]
            if len(candidates) != 1:
                result["issues"].append(_population_issue(validation, pointer,
                    "vdb_function_base_search_ambiguous" if candidates else "vdb_function_base_search_unavailable",
                    conflict=bool(candidates), search=search))
                continue
            sheet = candidates[0]["sheet"]
            reports = [r for r in artifact_catalog["entries"] if r.get("artifact_key") == unit["search_key"]["artifact_key"]
                       and r.get("role") == "primary_report"]
            if (len(reports) != 1 or reports[0]["artifact_ref"] != sheet.get("report_source", {}).get("artifact_ref")
                    or reports[0].get("output_key") != search["output_key"]):
                result["issues"].append(_population_issue(validation, pointer,
                    "vdb_function_artifact_catalog_conflict", conflict=bool(reports), search=search))
                continue
            if sheet.get("search", {}).get("search_key") != unit["search_key"]:
                result["issues"].append(_population_issue(validation, pointer,
                    "vdb_function_base_sheet_invalid", conflict=True, search=search))
                continue
            units.append((validation, pointer, search, _usable_records(validation, pointer, unit), sheet))

    # Dependency/census keys are strict342 record identities. Cross-envelope
    # collisions reject every conflicting record, never an earlier source.
    owners = {}
    for index, (_, _, _, unit, _) in enumerate(units):
        for field, key in (("dependency_records", "dependency_key"), ("census_records", "census_key")):
            for row in unit[field]:
                identity = (_metadata._token(unit["search_key"]), field, row[key])
                owners.setdefault(identity, []).append(index)
    conflicts = {identity for identity, indices in owners.items() if len(indices) > 1}
    groups = {}
    for index, item in enumerate(units):
        validation, pointer, search, unit, _ = item
        for field, keyfield in (("dependency_records", "dependency_key"), ("census_records", "census_key")):
            rejected = [r for r in unit[field] if (_metadata._token(unit["search_key"]), field, r[keyfield]) in conflicts]
            if rejected:
                # Point into the original normalized unit before filtering;
                # repeated identities must retain every original input address.
                original_rows = _metadata._pointer_get(validation["normalized"], pointer)[field]
                for ri, row in enumerate(original_rows):
                    if any(row[keyfield] == r[keyfield] for r in rejected):
                        result["issues"].append(_population_issue(validation, f"{pointer}/{field}/{ri}",
                            "vdb_function_input_records_conflict", conflict=True, search=search))
                unit[field] = [r for r in unit[field] if r not in rejected]
        groups.setdefault(_metadata._token(unit["search_key"]), []).append(item)
    # Native feature metadata needs no additional supplied assignment payload.
    # Populate every unique retained base search, even when all supplied units
    # for it were rejected. Originals and those rejections remain in the caller's
    # prepared inputs and this envelope; no rejected labels enter the sheet.
    base_groups = {}
    for row in base["vdb"]:
        if type(row) is not dict or set(row) != {"search_key", "sheet"}:
            raise ValueError("blast_vdb_function_sheet_schema_invalid")
        base_groups.setdefault(_metadata._token(row["search_key"]), []).append(row)
    for key, base_rows in base_groups.items():
        items = groups.get(key, [])
        if items:
            owners = [(v, p, s) for v, p, s, _, _ in items]
        else:
            try:
                owner = _metadata._input_issue_descriptor(prepared["invocation"]["request"]["native_blast_database"])
            except (KeyError, TypeError):
                raise ValueError("blast_vdb_function_sheet_schema_invalid") from None
            owner["normalization_map"] = []
            owners = [(owner, "/vdb", None)]
        if len(base_rows) != 1:
            for v, p, s in owners:
                issue = _population_issue(v, p, "vdb_function_base_search_ambiguous", conflict=True, search=s)
                if issue not in result["issues"]:
                    result["issues"].append(issue)
            continue
        base_sheet = base_rows[0]["sheet"]
        reports = [r for r in artifact_catalog["entries"] if r.get("artifact_key") == base_rows[0]["search_key"]["artifact_key"]
                   and r.get("role") == "primary_report"]
        if len(reports) != 1 or reports[0]["artifact_ref"] != base_sheet.get("report_source", {}).get("artifact_ref"):
            for v, p, s in owners:
                result["issues"].append(_population_issue(v, p, "vdb_function_artifact_catalog_conflict", conflict=bool(reports), search=s))
            continue
        if base_sheet.get("search", {}).get("search_key") != base_rows[0]["search_key"]:
            for v, p, s in owners:
                result["issues"].append(_population_issue(v, p, "vdb_function_base_sheet_invalid", conflict=True, search=s))
            continue
        fields = {name: [deepcopy(row) for item in items for row in item[3][name]] for name in _UNIT_FIELDS}
        try:
            sheet = _inputs.populate_blast_vdb_function_sheet(base_sheet, **fields)
            sheet = _inputs.validate_blast_vdb_function_sheet(sheet)
        except ValueError as error:
            detail = ("vdb_function_input_records_conflict" if str(error) in {
                "blast_vdb_function_record_key_duplicate", "blast_vdb_function_record_fields_invalid"}
                else "vdb_function_base_sheet_invalid")
            for validation, pointer, search in owners:
                result["issues"].append(_population_issue(validation, pointer, detail, conflict=True, search=search))
        else:
            result["sheets"].append(dict(search_key=deepcopy(base_rows[0]["search_key"]), sheet=sheet))
    return result
