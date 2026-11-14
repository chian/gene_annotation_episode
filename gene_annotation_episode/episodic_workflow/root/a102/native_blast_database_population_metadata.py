"""Supplied, authenticated BLAST population records; no acquisition or scoring.

The v3 wire extension preserves source assertions rather than deriving equality
from a database path/name.  Source records are extracted once from authenticated
JSON bytes by preparation.  Saved validation compares those frozen records and
original declarations without re-running extraction, native parsing or grading.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re


SEQUENCE_POPULATION_METADATA_SCHEMA = "native_blast_database_sequence_metadata_v3"
_PREFIX = "blast_database_population_"
_RECORD_FIELDS = {"source_ref", "artifact_ref", "sha256", "size_bytes", "pointer", "value"}


def _fail(suffix):
    raise ValueError(_PREFIX + suffix)


def _copy(value, active=None):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or type(value) is dict and all(type(k) is str for k in value):
        active = set() if active is None else active
        if id(value) in active:
            _fail("finite_json_required")
        active.add(id(value))
        try:
            return [_copy(v, active) for v in value] if type(value) is list else {k: _copy(v, active) for k, v in value.items()}
        finally:
            active.remove(id(value))
    _fail("finite_json_required")


def _token(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _pointer(value):
    return type(value) is str and (not value or value.startswith("/")) and re.search(r"~(?![01])", value) is None


def _at(value, pointer):
    if not _pointer(pointer):
        raise ValueError("pointer_invalid")
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            if re.fullmatch(r"0|[1-9][0-9]*", part) is None:
                raise ValueError("pointer_index_invalid")
            value = value[int(part)]
        else:
            value = value[part]
    return value


def _records(value):
    value = _copy(value)
    if type(value) is not list:
        _fail("context_fields_invalid")
    for row in value:
        if (type(row) is not dict or set(row) != _RECORD_FIELDS
                or any(type(row[k]) is not str or not row[k] or "\0" in row[k] for k in ("source_ref", "artifact_ref"))
                or type(row["sha256"]) is not str or re.fullmatch(r"[a-f0-9]{64}", row["sha256"]) is None
                or type(row["size_bytes"]) is not int or row["size_bytes"] < 0 or not _pointer(row["pointer"])):
            _fail("context_fields_invalid")
    return value


def native_blast_database_sequence_population_metadata_schema() -> dict:
    """The exact v2 record-locator fields plus required per-search assertions."""
    from .native_blast_database_metadata import _SEQUENCE_SCHEMA_V2, _TOKEN, _PROV, _object, _array
    schema = deepcopy(_SEQUENCE_SCHEMA_V2)
    schema["properties"]["schema"] = {"enum": [SEQUENCE_POPULATION_METADATA_SCHEMA]}
    unit = schema["properties"]["searches"]["items"]
    association = _object(association_key=_TOKEN, database_key=_TOKEN,
                          assertion_source=_PROV, census_source=_PROV)
    association["x-wire"] = "population_association"
    unit["properties"]["database_population_associations"] = _array(association)
    unit["required"].append("database_population_associations")
    profile = unit["properties"]["database_profile"]["anyOf"][0]
    profile["properties"]["source"] = {**_TOKEN, "x-wire": "population_source"}
    return schema


def _json_record(document, value, pointer=""):
    return {**{k: document[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")},
            "pointer": pointer, "value": deepcopy(value)}


def _retain_document_records(payload, documents):
    """Extract only supplied JSON; malformed/missing pointers retain no record."""
    from .native_blast_database_metadata import _decode
    records = []
    requested = {}
    for unit in payload.get("searches", []) if type(payload) is dict else []:
        for row in unit.get("database_population_associations", []):
            for field in ("assertion_source", "census_source"):
                prov = row[field]
                requested.setdefault(prov["source_ref"], set()).add(prov["pointer"])
    for doc in documents:
        if doc["document_key"] not in requested or doc["format"] != "json":
            continue
        raw = doc["contents"]
        if (type(raw) is not bytes or len(raw) != doc["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != doc["sha256"]):
            continue
        try:
            value = _decode(raw)
        except (ValueError, UnicodeError):
            continue
        records.append(_json_record(doc, value))
        for pointer in sorted(requested[doc["document_key"]] - {""}):
            try:
                pointed = _at(value, pointer)
            except (ValueError, KeyError, IndexError, TypeError):
                continue
            records.append(_json_record(doc, pointed, pointer))
    return list({_token(r): r for r in records}.values())


def _retain_preparation_records(validation, *, metadata_entries, bundle, catalog, manifest_documents):
    """Add original metadata, bundle and captured manifest facts to a v3 envelope.

    The caller has authenticated these objects and bytes. Bundle length is an
    explicit original capture fact; it is never reconstructed by serialization.
    """
    if validation["schema_id"] != SEQUENCE_POPULATION_METADATA_SCHEMA:
        return
    records = validation.setdefault("population_source_records", [])
    if validation["status"] == "valid":
        for entry in metadata_entries:
            records.append(_json_record(entry, validation["payload"]))
    size = catalog.get("bundle_size_bytes")
    if type(size) is int and size >= 0:
        records.append(_json_record(dict(source_ref=catalog["bundle_source_ref"], artifact_ref=catalog["bundle_artifact_ref"],
            sha256=catalog["bundle_sha256"], size_bytes=size), bundle))
    from .native_blast_database_metadata import _decode
    for doc in manifest_documents:
        try:
            value = _decode(doc["contents"])
        except (ValueError, UnicodeError):
            continue
        records.append(_json_record(doc, value))
    validation["population_source_records"] = list({_token(r): r for r in records}.values())


def _job(prepared):
    request = prepared["invocation"]["request"]
    keys = [k for k in ("native_blast_standard_database", "native_blast_database") if k in request]
    if len(keys) != 1:
        _fail("context_fields_invalid")
    return keys[0], request[keys[0]]


def _bundle(prepared, records):
    key, _ = _job(prepared)
    version = key + "_bundle_v1"
    rows = [r for r in records if r["pointer"] == "" and type(r["value"]) is dict
            and r["value"].get("version") == version
            and r["value"].get("requested_job") == prepared["invocation"]["request"]]
    rows = list({_token(r): r for r in rows}.values())
    return rows[0] if len(rows) == 1 else None


def _selected(prepared, records, database_key):
    job_key, job = _job(prepared)
    bundle_record = _bundle(prepared, records)
    selected = [d for d in job["databases"] if d["database_key"] == database_key]
    if bundle_record is None or len(selected) != 1:
        return None
    db, bundle = selected[0], bundle_record["value"]
    if db["role"] != "target" or db["identity"]["preparation_type"] != "sequence_database":
        return None
    index = job["databases"].index(db)
    pointer = f"/requested_job/{job_key}/databases/{index}"
    custody = [r for r in prepared["source_relations"] if r["pointer"] == pointer
               and (job_key != "native_blast_standard_database" or r.get("kind") == "database")]
    captures = [r for r in bundle.get("database_manifest", []) if r["database_key"] == database_key]
    if len(custody) != 1 or custody[0]["status"] != "available" or len(captures) != 1:
        return None
    capture = captures[0]
    artifacts = [r for r in bundle["artifacts"] if r["artifact_key"] == capture["manifest_artifact_key"]]
    if (len(artifacts) != 1 or artifacts[0]["role"] != "database_manifest"
            or artifacts[0]["database_key"] != database_key or capture["native_paths"] != db["native_paths"]
            or any(artifacts[0][k] != db["manifest_file"][k] for k in ("sha256", "size_bytes"))
            or len(capture["checks"]) != len(db["manifest"]["files"])
            or any(r["status"] != "verified" or r["observed_sha256"] != r["expected_sha256"] for r in capture["checks"])
            or sorted((r["path"], r["expected_sha256"], r["size_bytes"]) for r in capture["checks"])
                != sorted((r["path"], r["sha256"], r["size_bytes"]) for r in db["manifest"]["files"])):
        return None
    manifests = [r for r in records if r["pointer"] == "" and r["value"] == db["manifest"]
                 and all(r[k] == db["manifest_file"][k] for k in ("sha256", "size_bytes"))]
    manifests = list({_token(r): r for r in manifests}.values())
    if len(manifests) != 1:
        return None
    argv, requested = bundle.get("realized_argv", []), prepared["invocation"]["request"].get("argv", [])
    if argv.count("-db") != 1 or requested.count("-db") != 1:
        return None
    try:
        operand = argv[argv.index("-db") + 1]
        original = requested[requested.index("-db") + 1]
    except IndexError:
        return None
    if operand != original or operand != " ".join(db["native_paths"]):
        return None
    return dict(native_database_operand=operand, native_paths=deepcopy(db["native_paths"]),
        identity=deepcopy(db["identity"]), manifest_sha256=manifests[0]["sha256"], manifest_size_bytes=manifests[0]["size_bytes"],
        invocation_source=dict(source_ref=bundle_record["source_ref"], pointer=f"/requested_job/{job_key}"),
        manifest_source=dict(source_ref=manifests[0]["source_ref"], pointer="/identity"))


def _provenance(original, declaration, document):
    # An unresolved literal remains a supplied token, never a new Store source.
    source = document["source_ref"] if document is not None else (
        declaration["artifact"]["source_ref"] if declaration is not None and declaration["artifact"]["kind"] == "received"
        else original["source_ref"])
    return dict(source_ref=source, pointer=original["pointer"])


def _record(records, document, provenance):
    if document is None or document["format"] != "json":
        return None
    rows = [r for r in records if all(r[k] == document[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes"))
            and r["pointer"] == provenance["pointer"]]
    rows = list({_token(r): r for r in rows}.values())
    return rows[0] if len(rows) == 1 else None


def _validate_retained_records(validation):
    """Check the saved record envelope internally, without decoding any bytes."""
    records = _records(validation["population_source_records"])
    for record in records:
        roots = [r for r in records if r["pointer"] == "" and all(r[k] == record[k]
            for k in ("source_ref", "artifact_ref", "sha256", "size_bytes"))]
        if not roots or any(_token(r["value"]) != _token(roots[0]["value"]) for r in roots):
            _fail("saved_relation_conflict")
        try:
            value = _at(roots[0]["value"], record["pointer"])
        except (KeyError, IndexError, TypeError, ValueError):
            _fail("saved_relation_conflict")
        if _token(value) != _token(record["value"]):
            _fail("saved_relation_conflict")
    if validation["status"] != "valid":
        return records
    payload = validation["payload"]
    owners = [r for r in records if r["artifact_ref"] == validation["artifact_ref"] and r["pointer"] == ""]
    if not owners or any(r["sha256"] != validation["sha256"] or r["value"] != payload for r in owners):
        _fail("saved_relation_conflict")
    documents = {d["document_key"]: d for d in validation["normalized"]["documents"]}
    for ui, unit in enumerate(payload["searches"]):
        for ai, row in enumerate(unit["database_population_associations"]):
            for field in ("assertion_source", "census_source"):
                prov = row[field]
                doc = documents.get(prov["source_ref"])
                if doc is None or doc["format"] != "json":
                    continue
                root = _record(records, doc, dict(source_ref=doc["source_ref"], pointer=""))
                if root is None:
                    # A saved envelope cannot erase an available original JSON
                    # document. Only an original decode failure has no JSON root.
                    address = f"/searches/{ui}/database_population_associations/{ai}/{field}"
                    if not any(i["pointer"] == address and i["document_key"] == doc["document_key"]
                            and i["detail_code"] == _PREFIX + "source_record_invalid" for i in validation["issues"]):
                        _fail("saved_relation_conflict")
                    continue
                try:
                    original = _at(root["value"], prov["pointer"])
                except (KeyError, IndexError, TypeError, ValueError):
                    continue
                actual = _record(records, doc, dict(source_ref=doc["source_ref"], pointer=prov["pointer"]))
                if actual is None or _token(actual["value"]) != _token(original):
                    _fail("saved_relation_conflict")
    return records


def _checked_records(prepared, source_records):
    supplied = _records(source_records)
    retained = []
    for validation in prepared["metadata"]:
        if validation["schema_id"] == SEQUENCE_POPULATION_METADATA_SCHEMA:
            retained.extend(_validate_retained_records(validation))
        elif "population_source_records" in validation:
            _fail("context_fields_invalid")
    if {_token(r) for r in retained} != {_token(r) for r in supplied}:
        _fail("saved_relation_conflict")
    _validate_population_documents(prepared, supplied)
    return supplied


def _validate_population_documents(prepared, records):
    """Check resolved source addresses against the original wire selections."""
    _, job = _job(prepared)
    bundle_record = _bundle(prepared, records)
    bundle = None if bundle_record is None else bundle_record["value"]
    for validation in prepared["metadata"]:
        if validation["schema_id"] != SEQUENCE_POPULATION_METADATA_SCHEMA or validation["status"] != "valid":
            continue
        declarations = {d["document_key"]: d for d in validation["payload"]["documents"]}
        documents = {d["document_key"]: d for d in validation["normalized"]["documents"]}
        if len(documents) != len(validation["normalized"]["documents"]):
            _fail("saved_relation_conflict")
        selected_keys = {row[field]["source_ref"] for unit in validation["payload"]["searches"]
            for row in unit["database_population_associations"] for field in ("assertion_source", "census_source")}
        for key in selected_keys:
            original, document = declarations.get(key), documents.get(key)
            if document is None:
                if original is not None and original["artifact"]["kind"] == "received" and any(
                        r["pointer"] == "" and all(r[k] == original["artifact"][k]
                            for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")) for r in records):
                    _fail("saved_relation_conflict")
                continue
            if (original is None or any(document[k] != original[k] for k in ("document_key", "artifact", "format"))
                    or set(document) != {"document_key", "artifact", "format", "artifact_key", "source_ref", "artifact_ref", "sha256", "size_bytes"}):
                _fail("saved_relation_conflict")
            address, expected, captured_key = original["artifact"], None, None
            kind = address["kind"]
            if kind == "received":
                if document["artifact_key"] is not None or any(document[k] != address[k]
                        for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")):
                    _fail("saved_relation_conflict")
                continue
            if bundle is None:
                continue  # No independently retained original bundle: selection stays unavailable.
            try:
                def one(rows):
                    if len(rows) != 1:
                        _fail("saved_relation_conflict")
                    return rows[0]
                if kind == "input":
                    expected = one([d for d in job["inputs"] if d["input_key"] == address["input_key"]])
                    capture = one([d for d in bundle["input_manifest"] if d["input_key"] == address["input_key"]])
                    if capture["original_path"] != expected["path"]:
                        _fail("saved_relation_conflict")
                    captured_key = capture["artifact_key"]
                elif kind == "output":
                    capture = one([d for d in bundle["output_manifest"] if d["output_key"] == address["output_key"]])
                    artifact = one([d for d in bundle["artifacts"] if d["artifact_key"] in capture["artifact_keys"]
                        and d["relative_path"] == address["relative_path"]])
                    expected, captured_key = artifact, artifact["artifact_key"]
                else:
                    database = one([d for d in job["databases"] if d["database_key"] == address["database_key"]])
                    capture = one([d for d in bundle["database_manifest"] if d["database_key"] == address["database_key"]])
                    if kind == "database_manifest":
                        expected, captured_key = database["manifest_file"], capture["manifest_artifact_key"]
                    elif kind == "database_metadata_manifest":
                        expected = database["manifest"]["metadata_manifests"][address["manifest_index"]]
                        slot = capture["metadata_manifest_artifacts"][address["manifest_index"]]
                        if slot["identity"] != expected:
                            _fail("saved_relation_conflict")
                        captured_key = slot["artifact_key"]
                    else:
                        expected = (database["manifest"]["preparation"]["input_manifest"]
                            if address["role"] == "preparation_input_manifest" else database["manifest"]["access"]["offline_configuration"])
                        slot = one([d for d in capture["sidecar_artifacts"] if d["role"] == address["role"]])
                        if slot["identity"] != expected:
                            _fail("saved_relation_conflict")
                        captured_key = slot["artifact_key"]
                if (document["artifact_key"] != captured_key or expected is None
                        or any(document[k] != expected[k] for k in ("sha256", "size_bytes"))):
                    _fail("saved_relation_conflict")
            except (KeyError, IndexError, TypeError):
                _fail("saved_relation_conflict")


def _population_search_units(search, prepared, records):
    """Find original selected v3 units even if another field could not lower."""
    bundle = _bundle(prepared, records)
    report_keys = {} if bundle is None else {r["output_key"]: r["artifact_keys"]
        for r in bundle["value"]["output_manifest"]}
    key = search["search_key"]
    for validation in prepared["metadata"]:
        if (validation["schema_id"] != SEQUENCE_POPULATION_METADATA_SCHEMA or validation["status"] != "valid"
                or validation["normalized"] is None):
            continue
        payload, normalized = validation["payload"], validation["normalized"]
        for ui, unit in enumerate(payload["searches"]):
            original_pointer = f"/searches/{ui}"
            mappings = [r for r in validation["normalization_map"] if r["payload_pointer"] == original_pointer]
            wire = unit["search_key"]
            same_slots = all(wire[k] == key[k] for k in ("member_ordinal", "report_index", "search_pointer"))
            matches = same_slots and (report_keys.get(wire["output_key"]) == [key["artifact_key"]] if bundle is not None
                else bool(mappings and _at(normalized, mappings[0]["normalized_pointer"])["search_key"] == key))
            if not matches:
                continue
            yield validation, original_pointer, unit


def _declarations(search, prepared, records):
    """Yield original metadata row addresses, preserving order and duplicates."""
    for validation, original_pointer, unit in _population_search_units(search, prepared, records):
        payload, normalized = validation["payload"], validation["normalized"]
        documents = {r["document_key"]: r for r in normalized["documents"]}
        declared = {r["document_key"]: r for r in payload["documents"]}
        owners = [r for r in records if r["pointer"] == "" and r["artifact_ref"] == validation["artifact_ref"]
                  and r["sha256"] == validation["sha256"] and r["value"] == payload]
        owners = list({_token(r): r for r in owners}.values())
        if not owners:
            _fail("source_record_unavailable")
        for ai, assertion in enumerate(unit["database_population_associations"]):
            pointer = original_pointer + f"/database_population_associations/{ai}"
            for owner in owners:
                yield validation, pointer, assertion, dict(source_ref=owner["source_ref"], pointer=pointer), declared, documents


def _issue(validation, pointer, search, detail, *, incompatible=False):
    return dict(code="native_blast_metadata_relation_conflict" if incompatible else "native_blast_metadata_relation_unresolved",
        input_key=validation["input_key"], consumer=validation["consumer"], schema_id=validation["schema_id"],
        pointer=pointer, document_key=None, search_address=deepcopy(search["search_key"]), detail_code=detail)


def _row_details(row, profile):
    """Source qualification only; these codes carry no numerical confidence."""
    details = []
    selected, assertion, census = row["selected_database"], row["assertion_record"], row["census_record"]
    if selected is None:
        details.append(("selected_database_unavailable", False))
    for value in (assertion, census):
        if value is None:
            details.append(("source_record_unavailable", False))
    if assertion is not None:
        value = assertion["value"]
        fields = {"schema", "relation", "native_database_operand", "database_manifest_sha256", "population_identity", "census_artifact"}
        if (type(value) is not dict or set(value) != fields or value.get("schema") != "blast_database_population_assertion_v1"
                or value.get("relation") != "same_population"):
            details.append(("source_record_invalid", True))
        else:
            if selected is not None:
                if value["native_database_operand"] != selected["native_database_operand"]:
                    details.append(("native_operand_conflict", True))
                if value["database_manifest_sha256"] != selected["manifest_sha256"]:
                    details.append(("manifest_identity_conflict", True))
                original_identity = value["population_identity"]
                selected_identity = {k: v for k, v in selected["identity"].items() if k != "source"}
                if type(original_identity) is not dict or set(original_identity) != set(selected_identity):
                    details.append(("population_identity_conflict", True))
                else:
                    for field, expected in selected_identity.items():
                        # An unknown required release/scope establishes neither
                        # equality nor a contradiction with the other record.
                        if field in {"release", "scope"} and (original_identity[field] is None or expected is None):
                            details.append(("population_" + field + "_unavailable", False))
                        elif original_identity[field] != expected:
                            details.append(("population_identity_conflict", True))
            if census is not None and value["census_artifact"] != {k: census[k] for k in ("sha256", "size_bytes", "pointer")}:
                details.append(("census_record_conflict", True))
    if selected is not None:
        for field in ("release", "scope"):
            if selected["identity"][field] is None:
                details.append(("population_" + field + "_unavailable", False))
    if census is not None:
        if profile is None:
            details.append(("source_record_unavailable", False))
        elif (profile["source"] != row["census_source"]["source_ref"]
              or census["value"] != {k: v for k, v in profile.items() if k != "source"}):
            details.append(("census_record_conflict", True))
    return sorted(set(details))


def extract_native_blast_database_population_associations(*, search, prepared_inputs, source_records, database_profile) -> dict:
    """Associate existing retained records; never infer a population or counts."""
    prepared, search = _copy(prepared_inputs), _copy(search)
    records = _checked_records(prepared, source_records)
    associations, issues = [], []
    for validation, pointer, declaration, owner, declared, documents in _declarations(search, prepared, records):
        row = dict(schema="blast_database_population_association_input_v1", association_key=declaration["association_key"],
            search_key=deepcopy(search["search_key"]), database_key=declaration["database_key"], metadata_source=owner,
            selected_database=_selected(prepared, records, declaration["database_key"]))
        for name in ("assertion", "census"):
            original = declaration[name + "_source"]
            document = documents.get(original["source_ref"])
            row[name + "_source"] = _provenance(original, declared.get(original["source_ref"]), document)
            row[name + "_record"] = _record(records, document, row[name + "_source"])
        associations.append(row)
        for detail, incompatible in _row_details(row, database_profile):
            issues.append(_issue(validation, pointer, search, _PREFIX + detail, incompatible=incompatible))
    from .blast_database_population_associations import validate_blast_database_population_context
    validate_blast_database_population_context(dict(schema="blast_database_population_context_v1",
        search_key=search["search_key"], associations=associations))
    return dict(schema="native_blast_database_population_associations_v1", associations=associations, issues=issues)


def validate_native_blast_database_population_associations(association_inputs, *, search, prepared_inputs, source_records,
                                                          database_profile) -> list[dict]:
    """Compare saved association fields to original declarations and records."""
    from .blast_database_population_associations import validate_blast_database_population_context
    prepared, search = _copy(prepared_inputs), _copy(search)
    records = _checked_records(prepared, source_records)
    profiles = [u["database_profile"] for v in prepared["metadata"]
        if v["consumer"] == "sequence_database" and v["status"] == "valid" and v["normalized"] is not None
        for u in v["normalized"]["searches"] if u["search_key"] == search["search_key"] and u["database_profile"] is not None]
    if _job(prepared)[0] == "native_blast_standard_database":
        from .native_blast_standard_database_metadata import _search_status
        if _search_status(search, prepared)[0] != "available":
            profiles = []
    unique_profiles = {_token(p): p for p in profiles}
    if database_profile != (next(iter(unique_profiles.values())) if len(unique_profiles) == 1 else None):
        _fail("saved_relation_conflict")
    context = validate_blast_database_population_context(dict(schema="blast_database_population_context_v1",
        search_key=search["search_key"], associations=association_inputs))
    rows = context["associations"]
    declarations = list(_declarations(search, prepared, records))
    if len(rows) != len(declarations):
        _fail("saved_relation_conflict")
    for row, (_, _, declaration, owner, declared, documents) in zip(rows, declarations):
        if (row["metadata_source"] != owner or row["association_key"] != declaration["association_key"]
                or row["database_key"] != declaration["database_key"] or row["search_key"] != search["search_key"]
                or row["selected_database"] != _selected(prepared, records, declaration["database_key"])):
            _fail("saved_relation_conflict")
        for name in ("assertion", "census"):
            original = declaration[name + "_source"]
            document = documents.get(original["source_ref"])
            provenance = _provenance(original, declared.get(original["source_ref"]), document)
            if row[name + "_source"] != provenance or row[name + "_record"] != _record(records, document, provenance):
                _fail("saved_relation_conflict")
    return rows


__all__ = ["native_blast_database_sequence_population_metadata_schema",
    "extract_native_blast_database_population_associations", "validate_native_blast_database_population_associations"]
