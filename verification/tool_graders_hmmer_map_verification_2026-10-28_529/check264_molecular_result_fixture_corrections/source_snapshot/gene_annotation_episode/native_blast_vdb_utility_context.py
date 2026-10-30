"""Authenticate selected VDB request claims against original retained bytes.

The qualifier is pure and supplies claims, not authentication. Only the original
bounded worker reads selected documents. Saved consumers validate its frozen
proof without reopening metadata, acquiring data or constructing a search job.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from jsonschema import Draft202012Validator

from .blast_utility_contracts import SCHEMAS, validate_blast_utility_record as core
from .blast_preparation_contracts import DATABASE_DEPENDENCY_SCHEMA
from .blast_vdb_utility_contracts import validate_vdb_utility_context
from .domain import ContractError
from .native_blast_contracts import finite_json_copy, native_blast_digest
from .native_blast_database_contracts import (
    DATABASE_OPERAND_SCHEMA as ADDITIONAL_DATABASE_SCHEMA,
    validate_native_blast_database_operand,
)
from .native_blast_standard_database_contracts import DATABASE_OPERAND_SCHEMA, _database

REQUEST_VERSION = "native_blast_vdb_utility_context_request_v1"
AUTHENTICATION_VERSION = "native_blast_vdb_context_authentication_v1"
_PREFIX = "/requested_job/native_blast_utility/vdb_context_request"
_STR = {"type": "string", "minLength": 1, "pattern": r"^[^\s\x00]+$"}
_INT = {"type": "integer", "minimum": 0}
_SHA = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}
_POINTER = {"type": "string", "pattern": r"^(?:/(?:[^~]|~[01])*)?$"}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def _array(items):
    return {"type": "array", "items": items}


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


ORIGIN_SCHEMA = {"anyOf": [
    _object({"kind": {"const": "request"}}),
    _object({"kind": {"const": "selected_json"}, "document_key": _STR, "pointer": _POINTER}),
]}
SAMPLE_ORIGIN_SCHEMA = {"anyOf": [*deepcopy(ORIGIN_SCHEMA["anyOf"]),
    _object({"kind": {"const": "dataset_sample"}, "document_key": _STR,
             "dataset_pointer": _POINTER, "sample_index": _INT})]}
JSON_ADDRESS_SCHEMA = {"anyOf": [
    _object({"kind": {"const": "database_manifest"}, "database_key": _STR}),
    _object({"kind": {"const": "database_metadata_manifest"}, "database_key": _STR, "manifest_index": _INT}),
    _object({"kind": {"const": "database_sidecar"}, "database_key": _STR,
             "role": {"enum": ["preparation_input_manifest", "preparation_receipt"]}}),
]}
DATABASE_FILE_ADDRESS_SCHEMA = _object({"kind": {"const": "database_file"},
    "database_key": _STR, "file_index": _INT})
DEPENDENCY_DECLARATION_SCHEMA = {"anyOf": [*deepcopy(ORIGIN_SCHEMA["anyOf"]),
    _object({"kind": {"const": "alias_directive"}, "database_key": _STR, "file_index": _INT,
             "directive": {"enum": ["DBLIST", "VDBLIST"]}, "directive_row_ordinal": _INT,
             "token_ordinal": _INT})]}
LIST_REFERENCE_SCHEMA = {"anyOf": [
    _object({"kind": {"const": "input"}, "input_key": _STR}),
    _object({"kind": {"const": "database_list"}, "list_key": _STR}),
]}


def _request_schema():
    props = deepcopy(SCHEMAS["VDBUtilityContext"]["properties"])
    props["source_inputs"]["items"]["properties"]["source"] = deepcopy(ORIGIN_SCHEMA)
    props["entry_identifier_bindings"]["items"]["properties"]["source"] = deepcopy(ORIGIN_SCHEMA)
    member = props["member_bindings"]["items"]["properties"]
    member["provenance"] = deepcopy(ORIGIN_SCHEMA)
    for key in ("read_identity", "reference_identity"):
        member[key]["anyOf"][0]["properties"]["source"] = deepcopy(ORIGIN_SCHEMA)
    props["sample_links"]["items"]["properties"]["link"]["properties"]["source"] = deepcopy(SAMPLE_ORIGIN_SCHEMA)
    dep = deepcopy(DATABASE_DEPENDENCY_SCHEMA["properties"])
    del dep["list_occurrence_id"]
    dep.update(list_ref=_nullable(LIST_REFERENCE_SCHEMA), declaration=DEPENDENCY_DECLARATION_SCHEMA)
    return _object({"version": {"const": REQUEST_VERSION},
        "documents": _array(_object({"document_key": _STR, "selection": JSON_ADDRESS_SCHEMA})),
        **{k: props[k] for k in ("source_inputs", "entry_identifier_bindings", "member_bindings", "sample_links")},
        "dependency_databases": _array({"anyOf": [DATABASE_OPERAND_SCHEMA, ADDITIONAL_DATABASE_SCHEMA]}),
        "database_lists": _array(_object({"list_key": _STR, "selection": DATABASE_FILE_ADDRESS_SCHEMA,
            "grammar": {"enum": ["vdb_whitespace_tokens", "blast_database_lines"]}})),
        "declared_dependencies": _array(_object(dep))})


REQUEST_SCHEMA = _request_schema()


def _error(code):
    raise ContractError("native_blast_utility_" + code)


def _require(condition, code="supplied_binding_conflict"):
    if not condition:
        _error(code)


def _schema(value, schema):
    _require(next(Draft202012Validator(schema).iter_errors(value), None) is None,
             "vdb_context_schema_mismatch")


def vdb_utility_context_request_schema() -> dict:
    return deepcopy(REQUEST_SCHEMA)


def vdb_utility_database_operands(job: dict) -> list[dict]:
    return deepcopy([*job["databases"], *job["vdb_context_request"]["dependency_databases"]])


def _address(job, address):
    databases = {r["database_key"]: r for r in vdb_utility_database_operands(job)}
    _require(address["database_key"] in databases)
    db = databases[address["database_key"]]
    kind, manifest = address["kind"], db["manifest"]
    if kind == "database_manifest":
        role, descriptor = "manifest", db["manifest_file"]
    elif kind == "database_metadata_manifest":
        index = address["manifest_index"]
        _require(index < len(manifest["metadata_manifests"]))
        role, descriptor = "metadata_manifest", manifest["metadata_manifests"][index]
    elif kind == "database_file":
        index = address["file_index"]
        _require(index < len(manifest["files"]))
        role, descriptor = "database_file", manifest["files"][index]
    else:
        key = {"preparation_input_manifest": "input_manifest", "preparation_receipt": "receipt"}[address["role"]]
        descriptor = manifest["preparation"][key]
        _require(descriptor is not None)
        role = "input_manifest" if key == "input_manifest" else "preparation_receipt"
    return {"database_key": db["database_key"], "role": role,
            "original_path": descriptor["path"], "identity": deepcopy(descriptor)}


def vdb_utility_document_selections(job: dict) -> list[dict]:
    return [{**deepcopy(row), **_address(job, row["selection"])}
            for row in job["vdb_context_request"]["documents"]]


def _pointer(document, pointer):
    _require(type(pointer) is str and (not pointer or pointer.startswith("/"))
             and re.search(r"~(?![01])", pointer) is None)
    current = document
    for raw in pointer.split("/")[1:] if pointer else []:
        token = raw.replace("~1", "/").replace("~0", "~")
        if type(current) is list:
            _require(re.fullmatch(r"0|[1-9][0-9]*", token) is not None)
            _require(int(token) < len(current))
            current = current[int(token)]
        else:
            _require(type(current) is dict and token in current)
            current = current[token]
    return current


def _fields(record, keys):
    _require(type(record) is dict and set(keys) <= record.keys())
    return deepcopy({key: record[key] for key in keys})


def _same_json(left, right):
    # Python equality conflates true with 1 and false with 0. Original typed
    # metadata claims must retain those JSON distinctions.
    return native_blast_digest(left) == native_blast_digest(right)


def extract_vdb_dataset_claim(record: dict) -> dict:
    return _fields(record, ("dataset_key", "dataset_type", "selected_input", "snapshot", "run_identifiers"))


def extract_vdb_identity_claim(record: dict) -> dict:
    return _fields(record, ("namespace", "value", "version"))


def extract_vdb_read_identity_claim(record: dict) -> dict:
    return _fields(record, ("native_read_name", "spot_id", "read_index"))


def extract_vdb_reference_identity_claim(record: dict) -> dict:
    return _fields(record, ("identifier", "full_length", "sequence_sha256"))


def extract_vdb_member_claim(record: dict) -> dict:
    result = _fields(record, ("dataset_key", "member_kind", "member_identifier", "relationship",
                              "read_identity", "reference_identity", "sample_key"))
    identifier = record.get("native_identifier")
    described = record.get("native_description")
    if described is not None:
        _require(type(described) is dict and "id" in described)
        _require(identifier is None or identifier == described["id"])
        identifier = described["id"]
    _require(type(identifier) is str and bool(identifier))
    result["native_identifier"] = identifier
    for key, extract in (("read_identity", extract_vdb_read_identity_claim),
                         ("reference_identity", extract_vdb_reference_identity_claim)):
        if result[key] is not None:
            result[key] = extract(result[key])
    return result


def extract_vdb_sample_claim(record: dict) -> dict:
    result = _fields(record, ("dataset_key", "link"))
    result["link"] = _fields(result["link"], ("sample_key", "sample_identifier", "biosample_identifier"))
    return result


def extract_vdb_dataset_sample_claim(record: dict, *, sample_index: int) -> dict:
    _require(type(record) is dict and "dataset_key" in record and type(record.get("sample_links")) is list
             and type(sample_index) is int and 0 <= sample_index < len(record["sample_links"]))
    return extract_vdb_sample_claim({"dataset_key": record["dataset_key"], "link": record["sample_links"][sample_index]})


def _claims(request):
    # (qualified source pointer, request record pointer, original locator,
    #  exact supplied biological values, fixed extractor)
    for i, row in enumerate(request["source_inputs"]):
        path = f"/source_inputs/{i}"
        yield path + "/source", path, row["source"], extract_vdb_dataset_claim(row), extract_vdb_dataset_claim
    for i, row in enumerate(request["entry_identifier_bindings"]):
        path = f"/entry_identifier_bindings/{i}"
        yield path + "/source", path, row["source"], row["identifier"], extract_vdb_identity_claim
    for i, row in enumerate(request["member_bindings"]):
        path = f"/member_bindings/{i}"
        yield path + "/provenance", path, row["provenance"], extract_vdb_member_claim(row), extract_vdb_member_claim
        for name, extract in (("read_identity", extract_vdb_read_identity_claim),
                              ("reference_identity", extract_vdb_reference_identity_claim)):
            if row[name] is not None:
                nested = path + "/" + name
                yield nested + "/source", nested, row[name]["source"], extract(row[name]), extract
    for i, row in enumerate(request["sample_links"]):
        path = f"/sample_links/{i}"
        yield path + "/link/source", path, row["link"]["source"], extract_vdb_sample_claim(row), extract_vdb_sample_claim


def validate_vdb_utility_context_request(value: dict, *, job: dict) -> dict:
    request = finite_json_copy(value)
    _schema(request, REQUEST_SCHEMA)
    job = {**job, "vdb_context_request": request}
    op = core("Operation", job["operation"])
    _require(op["version"] == "blast_utility_operation_v3")
    databases = vdb_utility_database_operands(job)
    _require(len({d["database_key"] for d in databases}) == len(databases))
    for db in databases:
        if db["manifest"]["version"] == "native_blast_prepared_database_manifest_v1":
            validate_native_blast_database_operand(db)
        else:
            _database(db)
    documents = {r["document_key"]: r for r in request["documents"]}
    _require(len(documents) == len(request["documents"]))
    vdb_utility_document_selections(job)
    lists = {r["list_key"]: r for r in request["database_lists"]}
    _require(len(lists) == len(request["database_lists"]))
    addresses = []
    for row in lists.values():
        address = _address(job, row["selection"])
        key = address["database_key"], address["role"], address["original_path"]
        _require(key not in addresses)
        addresses.append(key)
    for _, _, origin, _, _ in _claims(request):
        if origin["kind"] != "request":
            _require(origin["document_key"] in documents)
    p = op["parameters"]
    original = p["database_selection"]["inputs"]
    _require(len(request["source_inputs"]) == len(original))
    for row, selected in zip(request["source_inputs"], original):
        _require(row["ordinal"] == selected["ordinal"] and row["selected_input"] == {
            "kind": selected["kind"], "value": selected["value"]}
            and row["binding_native_path"] == selected["binding_native_path"])
    selection = p["selection"]
    selectors = selection["selectors"] if selection is not None and selection["kind"] == "entries" else []
    _require([r["selector_ordinal"] for r in request["entry_identifier_bindings"]] == [r["ordinal"] for r in selectors])
    for row, selected in zip(request["entry_identifier_bindings"], selectors):
        _require(row["identifier"]["value"] == selected["value"])
    if selection is not None and selection["kind"] == "all_references":
        _require(any(r["dataset_type"] == "csra" for r in request["source_inputs"]))
    datasets = {r["dataset_key"] for r in request["source_inputs"] if r["dataset_key"] is not None}
    _require(len({r["binding_key"] for r in request["member_bindings"]}) == len(request["member_bindings"]))
    _require(all(r["dataset_key"] in datasets for r in request["sample_links"]))
    for member in request["member_bindings"]:
        _require(member["dataset_key"] in datasets)
        _require(member["read_identity"] is None or member["member_kind"] == "read")
        _require(member["reference_identity"] is None or member["member_kind"] in {"reference", "wgs_sequence"})
        if member["sample_key"] is not None:
            links = [extract_vdb_sample_claim(r)["link"] for r in request["sample_links"]
                     if r["dataset_key"] == member["dataset_key"] and r["link"]["sample_key"] == member["sample_key"]]
            _require(bool(links) and all(r == links[0] for r in links))
    by_database = {d["database_key"]: d for d in databases}
    inputs = {r["input_key"]: r for r in job["inputs"]}
    _require(len({d["ordinal"] for d in request["declared_dependencies"]}) == len(request["declared_dependencies"]))
    for dep in request["declared_dependencies"]:
        _require(dep["database_key"] in by_database)
        db = by_database[dep["database_key"]]
        _require(dep["native_path_index"] < len(db["native_paths"]))
        file_source = dep["source"] in {"dblist_file", "vdblist_file"}
        _require((dep["list_ref"] is not None) == file_source and (dep["list_entry_ordinal"] is not None) == file_source)
        if file_source:
            ref = dep["list_ref"]
            _require(ref["input_key"] in inputs and inputs[ref["input_key"]]["role"] == "database_list"
                     if ref["kind"] == "input" else ref["list_key"] in lists)
        origin = dep["declaration"]
        if origin["kind"] == "selected_json":
            _require(origin["document_key"] in documents)
        elif origin["kind"] == "alias_directive":
            _address(job, {"kind": "database_file", "database_key": origin["database_key"], "file_index": origin["file_index"]})
            _require(dep["source"] == origin["directive"].lower())
        else:
            _require(file_source or dep["source"] == "db")
        if dep["source"] == "db":
            _require(origin["kind"] == "request" and any(r["value"] == dep["native_reference"]
                and r["binding_native_path"] == db["native_paths"][dep["native_path_index"]] for r in original))
    return request


def vdb_utility_occurrence_id(capture, row):
    if row["direction"] == "input":
        return row["input_key"]
    return "native_blast_utility_occurrence_" + native_blast_digest({
        "identity": capture["original_bundle"]["identity"], **{key: row.get(key) for key in
        ("direction", "input_key", "database_key", "role", "ordinal", "original_path")}})


def vdb_utility_occurrence_role(job, row):
    if row["direction"] == "database" and row["role"] == "database_file":
        for selected in job["vdb_context_request"]["database_lists"]:
            address = _address(job, selected["selection"])
            if all(row[k] == address[k] for k in ("database_key", "role", "original_path")):
                return "database_list"
    return {"manifest": "database_manifest", "metadata_manifest": "database_metadata"}.get(row["role"], row["role"])


def _captured(capture, address):
    rows = [r for r in capture["artifacts"] if r["direction"] == "database"
            and all(r[k] == address[k] for k in ("database_key", "role", "original_path"))]
    _require(len(rows) == 1, "input_population_unavailable")
    return rows[0]


def _document_rows(capture):
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    return [{"document_key": selected["document_key"], "selection": selected["selection"],
             "occurrence_id": vdb_utility_occurrence_id(capture, row),
             **{key: row[key] for key in ("artifact_ref", "sha256", "size_bytes")}}
            for selected in vdb_utility_document_selections(job)
            for row in [_captured(capture, selected)]]


def _provenance_rows(capture):
    request = capture["plan"]["requested_job"]["native_blast_utility"]["vdb_context_request"]
    documents = {r["document_key"]: r for r in _document_rows(capture)}
    rows = []
    for pointer, request_pointer, origin, _, _ in _claims(request):
        if origin["kind"] == "request":
            reference, namespace, location = capture["source_ref"], "source", _PREFIX + request_pointer
        else:
            reference, namespace = documents[origin["document_key"]]["artifact_ref"], "artifact"
            location = (origin["pointer"] if origin["kind"] == "selected_json" else
                        origin["dataset_pointer"] + "/sample_links/" + str(origin["sample_index"]))
        rows.append({"context_pointer": "/vdb_context" + pointer, "origin": deepcopy(origin),
                     "source_ref": reference, "source_namespace": namespace, "pointer": location})
    return rows


def _list_selections(capture):
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    rows, seen = [], set()
    for role, grammar in (("database_list", "vdb_whitespace_tokens"), ("entry_batch", "vdb_entry_lines")):
        for item in job["inputs"]:
            if item["role"] == role:
                matches = [r for r in capture["artifacts"] if r["direction"] == "input" and r["input_key"] == item["input_key"]]
                _require(len(matches) == 1, "input_population_unavailable")
                row = matches[0]
                rows.append((row, grammar)); seen.add(vdb_utility_occurrence_id(capture, row))
    for selected in job["vdb_context_request"]["database_lists"]:
        row = _captured(capture, _address(job, selected["selection"]))
        oid = vdb_utility_occurrence_id(capture, row)
        if oid not in seen:
            rows.append((row, selected["grammar"])); seen.add(oid)
    return rows


def _list_occurrence(capture, reference):
    if reference is None:
        return None
    if reference["kind"] == "input":
        return reference["input_key"]
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    selected = next(r for r in job["vdb_context_request"]["database_lists"] if r["list_key"] == reference["list_key"])
    return vdb_utility_occurrence_id(capture, _captured(capture, _address(job, selected["selection"])))


def qualify_vdb_utility_context(capture: dict, *, base_context: dict) -> dict:
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    request = validate_vdb_utility_context_request(job["vdb_context_request"], job=job)
    context = deepcopy(base_context)
    bindings = []
    for db in vdb_utility_database_operands(job):
        captured = [r for r in capture["artifacts"] if r["direction"] == "database" and r["database_key"] == db["database_key"]]
        from .native_blast_utility_contracts import database_file_selections
        expected = [r for r in database_file_selections(job) if r["database_key"] == db["database_key"]]
        bindings.append(core("DatabaseBinding", {"database_key": db["database_key"], "kind": db["kind"],
            "molecule": {"blast_protein_sequence": "protein", "blast_nucleotide_sequence": "dna"}.get(db["kind"], "dna" if db["kind"] == "vdb" else "unknown"),
            "identity": {k: db["identity"][k] for k in ("namespace", "value", "version", "release")},
            "source_ref": capture["source_ref"], "native_paths": db["native_paths"],
            "occurrence_ids": [vdb_utility_occurrence_id(capture, r) for r in captured],
            "inventory_complete": db["manifest"]["inventory_complete"] and len(captured) == len(expected)}))
    context["database_binding"] = bindings[0]
    by_id = {r["occurrence_id"]: r for r in context["occurrences"]}
    _require(set(job["operation"]["input_occurrence_ids"]) <= by_id.keys(), "input_population_unavailable")
    context["operation_input_occurrences"] = [by_id[k] for k in job["operation"]["input_occurrence_ids"]]
    p = job["operation"]["parameters"]
    context["vdb_context"] = {"version": "blast_vdb_utility_context_v1",
        **{k: deepcopy(request[k]) for k in ("source_inputs", "entry_identifier_bindings", "member_bindings", "sample_links")},
        "selection_kind": None if p["selection"] is None else p["selection"]["kind"],
        "include_filtered_reads": p["include_filtered_reads"], "dependency_database_bindings": bindings[1:],
        "declared_dependencies": [{**{k: v for k, v in d.items() if k not in {"list_ref", "declaration"}},
                                   "list_occurrence_id": _list_occurrence(capture, d["list_ref"])}
                                  for d in request["declared_dependencies"]]}
    for row in _provenance_rows(capture):
        parent, _, key = row["context_pointer"].rpartition("/")
        _pointer(context, parent)[key] = {k: row[k] for k in ("source_ref", "pointer")}
    validate_vdb_utility_context(context["vdb_context"], operation=context["operation"],
        database_binding=context["database_binding"], operation_input_occurrences=context["operation_input_occurrences"])
    return context


def _lexical_list(raw, grammar, occurrence):
    _require(type(raw) is bytes, "input_population_unavailable")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _error("supplied_binding_conflict")
    _require("\x00" not in text)
    entries, offset = [], 0
    # Native C++ line processing permits LF and CRLF; bare CR is ambiguous.
    _require(re.search(rb"\r(?!\n)", raw) is None)
    if grammar == "blast_database_lines":
        from .blast_preparation_inputs import parse_blast_preparation_list
        parsed = parse_blast_preparation_list(raw, grammar=grammar, occurrence=occurrence)
        _require(not parsed["failures"])
        declared = [r["original_token"] for r in parsed["rows"]]
    else:
        declared = None
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        body = line[:-2] if line.endswith(b"\r\n") else line[:-1] if line.endswith(b"\n") else line
        if grammar == "vdb_whitespace_tokens":
            matches = [(m.start(), m.end(), m.group()) for m in re.finditer(rb"[^ \t\r\n\v\f]+", body)]
        elif grammar == "vdb_entry_lines":
            matches = [(0, len(body), body)] if body else []
            _require(not body or not any(c in body for c in (b"\t", b"\v", b"\f")) and body.strip() == body)
        else:
            stripped = body.strip(b" \t")
            start = len(body) - len(body.lstrip(b" \t"))
            matches = [(start, start + len(stripped), stripped)] if stripped else []
        for token_ordinal, (start, end, value) in enumerate(matches):
            entries.append({"ordinal": len(entries), "line_number": number, "token_ordinal": token_ordinal,
                "byte_start": offset + start, "byte_end": offset + end, "value": value.decode("utf-8")})
        offset += len(line)
    if declared is not None:
        _require(declared == [r["value"] for r in entries])
    return entries


def validate_vdb_selected_input_bytes(job, contents_by_input):
    """Preflight exact native list interpretation; no file access or discovery."""
    p = job["operation"]["parameters"]
    for item in job["inputs"]:
        raw = contents_by_input.get(item["input_key"])
        _require(type(raw) is bytes, "input_population_unavailable")
        _require((len(raw), hashlib.sha256(raw).hexdigest()) == (item["size_bytes"], item["sha256"]), "input_identity_mismatch")
        grammar = "vdb_entry_lines" if item["role"] == "entry_batch" else "vdb_whitespace_tokens"
        entries = _lexical_list(raw, grammar, None)
        expected = ([r["value"] for r in p["selection"]["selectors"]] if item["role"] == "entry_batch" else
                    [r["value"] for r in p["database_selection"]["inputs"]])
        _require([r["value"] for r in entries] == expected)


_LIST_ENTRY_SCHEMA = _object({"ordinal": _INT, "line_number": {"type": "integer", "minimum": 1},
    "token_ordinal": _INT, "byte_start": _INT, "byte_end": _INT, "value": {"type": "string", "minLength": 1}})
AUTHENTICATION_SCHEMA = _object({"version": {"const": AUTHENTICATION_VERSION}, "passed": {"const": True},
    "bundle_artifact_ref": {"type": "string", "pattern": r"^artifact_[0-9a-f]{64}$"},
    "request_sha256": _SHA, "context_sha256": _SHA,
    "documents": _array(_object({"document_key": _STR, "selection": JSON_ADDRESS_SCHEMA,
        "occurrence_id": _STR, "artifact_ref": {"type": "string", "pattern": r"^artifact_[0-9a-f]{64}$"},
        "sha256": _SHA, "size_bytes": _INT})),
    "provenance": _array(_object({"context_pointer": _POINTER, "origin": SAMPLE_ORIGIN_SCHEMA,
        "source_ref": _STR, "source_namespace": {"enum": ["source", "artifact"]}, "pointer": _POINTER})),
    "lists": _array(_object({"occurrence_id": _STR,
        "grammar": {"enum": ["vdb_whitespace_tokens", "vdb_entry_lines", "blast_database_lines"]},
        "sha256": _SHA, "size_bytes": _INT, "entries": _array(_LIST_ENTRY_SCHEMA)})),
    "dependencies": _array(_object({"ordinal": _INT, "declaration": DEPENDENCY_DECLARATION_SCHEMA,
        "list_occurrence_id": _nullable(_STR)}))})


def validate_vdb_context_authentication_shape(value: dict, *, context: dict) -> dict:
    """Saved worker boundary; host has already authenticated the original receipt."""
    value = finite_json_copy(value)
    _schema(value, AUTHENTICATION_SCHEMA)
    _require(value["context_sha256"] == native_blast_digest(context))
    by_id = {r["occurrence_id"]: r for r in context["occurrences"]}
    for row in value["documents"]:
        _require(row["occurrence_id"] in by_id)
        _require(all(row[k] == by_id[row["occurrence_id"]][k] for k in ("artifact_ref", "sha256", "size_bytes")))
    for row in value["provenance"]:
        _require(_pointer(context, row["context_pointer"]) == {k: row[k] for k in ("source_ref", "pointer")})
        _require(row["source_ref"].startswith("artifact_") if row["source_namespace"] == "artifact" else row["source_ref"].startswith("source_"))
    for row in value["lists"]:
        _require(row["occurrence_id"] in by_id)
        original = by_id[row["occurrence_id"]]
        _require(all(row[k] == original[k] for k in ("sha256", "size_bytes")))
        previous_end, previous_line, previous_token = 0, 0, -1
        for i, entry in enumerate(row["entries"]):
            _require(entry["ordinal"] == i and previous_end <= entry["byte_start"] < entry["byte_end"] <= row["size_bytes"]
                and entry["byte_end"] - entry["byte_start"] == len(entry["value"].encode("utf-8"))
                and entry["line_number"] >= previous_line)
            _require(entry["token_ordinal"] == (previous_token + 1 if entry["line_number"] == previous_line else 0))
            if row["grammar"] != "vdb_whitespace_tokens":
                _require(entry["token_ordinal"] == 0)
            previous_end, previous_line, previous_token = entry["byte_end"], entry["line_number"], entry["token_ordinal"]
    return value


def _validate_list_values(value, capture):
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    p = job["operation"]["parameters"]
    by_id = {r["occurrence_id"]: r for r in value["lists"]}
    for oid, expected in [(p["database_selection"]["list_occurrence_id"],
                           [r["value"] for r in p["database_selection"]["inputs"]])]:
        if oid is not None:
            _require([r["value"] for r in by_id[oid]["entries"]] == expected)
    selection = p["selection"]
    if selection is not None and selection["kind"] == "entries" and selection["batch_occurrence_id"] is not None:
        _require([r["value"] for r in by_id[selection["batch_occurrence_id"]]["entries"]] == [r["value"] for r in selection["selectors"]])
    for dep in job["vdb_context_request"]["declared_dependencies"]:
        oid = _list_occurrence(capture, dep["list_ref"])
        if oid is not None:
            entries = by_id[oid]["entries"]
            _require(dep["list_entry_ordinal"] < len(entries) and entries[dep["list_entry_ordinal"]]["value"] == dep["native_reference"])


def validate_vdb_context_authentication(value: dict, *, capture: dict, context: dict) -> dict:
    value = validate_vdb_context_authentication_shape(value, context=context)
    _require(context["operation"] == capture["plan"]["requested_job"]["native_blast_utility"]["operation"])
    # Authenticate the whole original qualified population and outcome. The
    # supplied context is not itself a source for those original facts.
    from .native_blast_utility_result_worker import qualified_utility_context
    expected_context = qualified_utility_context(capture)
    _require(context == expected_context)
    _require(value["bundle_artifact_ref"] == capture["bundle_artifact_ref"]
             and value["request_sha256"] == native_blast_digest(capture["plan"]["requested_job"]))
    _require(value["documents"] == _document_rows(capture) and value["provenance"] == _provenance_rows(capture))
    selected = _list_selections(capture)
    _require(len(selected) == len(value["lists"]))
    for row, (original, grammar) in zip(value["lists"], selected):
        _require({k: v for k, v in row.items() if k != "entries"} == {
            "occurrence_id": vdb_utility_occurrence_id(capture, original), "grammar": grammar,
            **{k: original[k] for k in ("sha256", "size_bytes")}})
    deps = capture["plan"]["requested_job"]["native_blast_utility"]["vdb_context_request"]["declared_dependencies"]
    _require(value["dependencies"] == [{"ordinal": r["ordinal"], "declaration": r["declaration"],
        "list_occurrence_id": _list_occurrence(capture, r["list_ref"])} for r in deps])
    _validate_list_values(value, capture)
    return value


def authenticate_vdb_utility_context(capture: dict, *, context: dict,
                                     contents_by_occurrence: dict[str, bytes]) -> dict:
    from .native_hmmer_preparation_acquisition import _decode
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    request = validate_vdb_utility_context_request(job["vdb_context_request"], job=job)
    rows = {r["occurrence_id"]: r for r in context["occurrences"]}
    def content(oid):
        _require(oid in rows and oid in contents_by_occurrence, "input_population_unavailable")
        raw, row = contents_by_occurrence[oid], rows[oid]
        _require(type(raw) is bytes and (len(raw), hashlib.sha256(raw).hexdigest()) ==
                 (row["size_bytes"], row["sha256"]), "input_identity_mismatch")
        return raw
    for db in vdb_utility_database_operands(job):
        row = _captured(capture, _address(job, {"kind": "database_manifest", "database_key": db["database_key"]}))
        _require(_same_json(_decode(content(vdb_utility_occurrence_id(capture, row))), db["manifest"]), "input_identity_mismatch")
    documents = _document_rows(capture)
    parsed = {r["document_key"]: _decode(content(r["occurrence_id"])) for r in documents}
    for _, _, origin, expected, extract in _claims(request):
        if origin["kind"] == "request":
            continue
        document = parsed[origin["document_key"]]
        if origin["kind"] == "dataset_sample":
            actual = extract_vdb_dataset_sample_claim(_pointer(document, origin["dataset_pointer"]), sample_index=origin["sample_index"])
        else:
            actual = extract(_pointer(document, origin["pointer"]))
        _require(_same_json(actual, expected))
    lists = []
    for original, grammar in _list_selections(capture):
        oid = vdb_utility_occurrence_id(capture, original)
        lists.append({"occurrence_id": oid, "grammar": grammar,
            **{k: original[k] for k in ("sha256", "size_bytes")},
            "entries": _lexical_list(content(oid), grammar, rows[oid])})
    dependencies = []
    for dep in request["declared_dependencies"]:
        origin = dep["declaration"]
        if origin["kind"] == "selected_json":
            actual = _pointer(parsed[origin["document_key"]], origin["pointer"])
            fields = ("role", "ordinal", "database_key", "native_path_index", "native_reference", "source", "list_entry_ordinal")
            _require(_same_json(_fields(actual, fields), _fields(dep, fields)))
        elif origin["kind"] == "alias_directive":
            from .blast_preparation_inputs import parse_blast_alias_document
            address = _address(job, {"kind": "database_file", "database_key": origin["database_key"], "file_index": origin["file_index"]})
            oid = vdb_utility_occurrence_id(capture, _captured(capture, address))
            occurrence = {**rows[oid], "role": "alias_file", "native_format": "blast_alias_text"}
            document = parse_blast_alias_document(content(oid), occurrence=occurrence)
            _require(not document["failures"])
            matches = [r for r in document["rows"] if r["row_ordinal"] == origin["directive_row_ordinal"]]
            _require(len(matches) == 1 and matches[0]["native_key"] == origin["directive"])
            tokens = matches[0]["tokens"]
            _require(origin["token_ordinal"] < len(tokens) and tokens[origin["token_ordinal"]]["value"] == dep["native_reference"])
        dependencies.append({"ordinal": dep["ordinal"], "declaration": deepcopy(origin),
                             "list_occurrence_id": _list_occurrence(capture, dep["list_ref"])})
    proof = {"version": AUTHENTICATION_VERSION, "passed": True,
        "bundle_artifact_ref": capture["bundle_artifact_ref"],
        "request_sha256": native_blast_digest(capture["plan"]["requested_job"]),
        "context_sha256": native_blast_digest(context), "documents": documents,
        "provenance": _provenance_rows(capture), "lists": lists, "dependencies": dependencies}
    return validate_vdb_context_authentication(proof, capture=capture, context=context)


def vdb_utility_authentication_occurrence_ids(capture):
    """Selected document/list/alias byte operands; binary data stays hash-only."""
    job = capture["plan"]["requested_job"]["native_blast_utility"]
    ids = {r["occurrence_id"] for r in _document_rows(capture)}
    for db in vdb_utility_database_operands(job):
        ids.add(vdb_utility_occurrence_id(capture, _captured(capture,
            _address(job, {"kind": "database_manifest", "database_key": db["database_key"]}))))
    ids.update(vdb_utility_occurrence_id(capture, r) for r, _ in _list_selections(capture))
    for dep in job["vdb_context_request"]["declared_dependencies"]:
        origin = dep["declaration"]
        if origin["kind"] == "alias_directive":
            ids.add(vdb_utility_occurrence_id(capture, _captured(capture, _address(job,
                {"kind": "database_file", "database_key": origin["database_key"], "file_index": origin["file_index"]}))))
    return ids
