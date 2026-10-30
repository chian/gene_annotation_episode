"""Closed host custody records, without execution or scientific calculations."""
from copy import deepcopy
import hashlib
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator

from .domain import ContractError, identity
from .restriction_mapping_contracts import (
    restriction_canonical, restriction_digest, restriction_schema,
    validate_restriction_record,
)
from .restriction_mapping_inputs import validate_restriction_sequence_witness


def _obj(**properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _arr(items, unique=False):
    return dict(type="array", items=items, **({"uniqueItems": True} if unique else {}))


def _enum(*values):
    return {"enum": list(values)}


def _null(schema):
    return {"anyOf": [schema, {"type": "null"}]}


TEXT = {"type": "string", "minLength": 1}
INT = {"type": "integer"}
UINT = {"type": "integer", "minimum": 0}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
PIN = restriction_schema("FilePin")
BINDING = restriction_schema("SequenceBinding")
NAMES = ("find_restriction_sites", "find_restriction_enzymes")
ISSUE_CODES = ("input_conflict", "software_conflict", "worker_failed", "writer_not_closed",
    "file_missing", "file_invalid", "file_digest_conflict", "manifest_invalid",
    "native_binding_conflict", "catalog_conflict", "mapping_conflict")
LOCAL_FAILURES = ("local_job_boundary_unavailable", "local_job_resource_limit", "local_job_cancelled",
    "local_job_not_collectable", "local_job_execution_error", "local_job_stop_unconfirmed",
    "local_job_cleanup_requires_quiescent_unit", "local_job_execution_unknown")
SCOPE = {"type": "object", "properties": {"subject_refs": _arr(TEXT, True),
    "read_selection_refs": {**_arr(TEXT, True), "minItems": 1},
    "segments": {**_arr({"type": "object", "properties": {"target_ref": TEXT, "member_ref": TEXT,
        "start": UINT, "end": UINT, "unit": _enum("nt", "aa", "symbol")},
        "required": ["target_ref", "start", "end", "unit"], "additionalProperties": False}), "minItems": 1}},
    "required": ["subject_refs"], "additionalProperties": False}
WITNESS = _obj(version=_enum("restriction_sequence_witness_v1"), namespace=_enum("subject", "reference"),
    sequence_ref=TEXT, sequence=TEXT, content_sha256=SHA, length_nt={"type": "integer", "minimum": 1},
    sequence_version=_null(UINT), molecule=_enum("dna", "unspecified"), scope=SCOPE,
    records=_arr(_obj(record_ref=TEXT, record_type=TEXT, record={"type": "object"})),
    artifacts=_arr(_obj(artifact_ref=TEXT, sha256=SHA, size_bytes=UINT)),
    mapping=_null({"type": "object"}), mapping_state=_enum("available", "unavailable"),
    mapping_issue=_enum(None, "subregion_mapping_unavailable"),
    packed_components=_arr(_obj(member_ref=TEXT, parse_key=TEXT, component=_enum("header", "sequence", "quality"),
        part=UINT, chunk_index=UINT, start=UINT, end=UINT, artifact_ref=TEXT)))
NATIVE_REQUEST = _obj(version=_enum("restriction_worker_request_v1"), mode=_enum("native"),
    sequence=TEXT, selected_sequence=BINDING, enzyme_selection=restriction_schema("EnzymeSelection"),
    topology=_enum("linear", "circular"))
SAVED_REQUEST = _obj(version=_enum("restriction_worker_request_v1"), mode=_enum("saved"),
    native_file=PIN, catalog_file=_null(PIN), selected_sequence=BINDING)
FILE_IDENTITY = _obj(artifact_ref=TEXT, sha256=SHA, size_bytes=UINT, format=TEXT)
_COMMON = dict(operation_key=TEXT, operation_ref=TEXT, tool_name=_enum(*NAMES),
    arguments={"type": "object"}, scope=SCOPE)
_VIEW = _obj(version=_enum("durable_systemd_native_job_v2"),
    state=_enum("prepared", "returned", "running", "starting", "execution_unknown"),
    terminal={"type": "boolean"}, quiescent={"type": "boolean"}, metadata={"type": "object"},
    native_receipt=_null({"type": "object"}), files=_obj(**{name: _obj(available={"type": "boolean"},
        bytes=_null(UINT)) for name in ("stdout", "stderr")}))
SCHEMAS = {
    "InputBody": _obj(version=_enum("restriction_input_source_v1"), **_COMMON, witness=WITNESS),
    "Software": _obj(python=PIN, implementation_files=_arr(PIN), biopython_version=_enum("1.88"),
        native_source_file=PIN, dictionary_file=PIN,
        environment={"type": "object", "additionalProperties": {"type": "string"}}),
    "BoundIssue": _obj(phase=_enum("input", "worker", "capture", "publication", "authority"),
        code=_enum(*ISSUE_CODES), role=_enum(None, "input", "native", "catalog", "mapping", "manifest",
            "stdout", "stderr", "closure")),
}
SCHEMAS["Reservation"] = _obj(version=_enum("restriction_operation_reservation_v1"), **_COMMON,
    work_mode=_enum("native", "saved"), input_source_ref=TEXT, prior_result_source_ref=_null(TEXT),
    sequence_binding=BINDING, worker_request={"anyOf": [NATIVE_REQUEST, SAVED_REQUEST]},
    software=SCHEMAS["Software"], policy=_obj(memory_bytes={"type": "integer", "minimum": 1},
        scratch_bytes={"type": "integer", "minimum": 1},
        wall_seconds=_null({"type": "number", "exclusiveMinimum": 0})),
    directory=TEXT, request_file=PIN, output_directory=TEXT, handle_path=TEXT, stdout_path=TEXT, stderr_path=TEXT)
SCHEMAS["ExecutionProof"] = _obj(version=_enum("restriction_operation_execution_proof_v1"),
    reservation_sha256=SHA, handle_artifact_ref=TEXT, control_request_artifact_ref=TEXT,
    status_artifact_ref=TEXT, native_receipt_artifact_ref=_null(TEXT), original_view=_VIEW,
    returncode=_null(INT), failure_code=_enum(None, *LOCAL_FAILURES))
SCHEMAS["PublishedBody"] = _obj(version=_enum("restriction_published_result_v1"), **_COMMON,
    work_mode=_enum("native", "saved"), input_source_ref=TEXT, prior_result_source_ref=_null(TEXT),
    reservation_artifact_ref=TEXT, execution_proof_artifact_ref=TEXT,
    files=_obj(**{role: _null(FILE_IDENTITY) for role in ("native", "catalog", "mapping", "manifest", "stdout", "stderr")}),
    validation=_obj(**{role: _enum("validated", "invalid", "missing") for role in ("native", "catalog", "mapping")}),
    status=_enum("completed", "partial", "failed", "invalid"),
    failure_code=_enum(None, "native_unavailable", "reader_unavailable", "mapping_invalid"),
    issues=_arr(SCHEMAS["BoundIssue"]))


def _require(condition, code="bound_record_invalid"):
    if not condition:
        raise ContractError("restriction_" + code)


def _same(left, right):
    return restriction_canonical(left) == restriction_canonical(right)


def _strict(value, schema):
    if "anyOf" in schema:
        return any(Draft202012Validator(branch).is_valid(value) and _strict(value, branch)
                   for branch in schema["anyOf"])
    if schema.get("type") == "integer" and type(value) is not int:
        return False
    if type(value) is dict:
        return all(_strict(child, schema.get("properties", {}).get(key,
            schema.get("additionalProperties", {}) if type(schema.get("additionalProperties")) is dict else {}))
            for key, child in value.items())
    if type(value) is list:
        return all(_strict(child, schema.get("items", {})) for child in value)
    return True


def validate_restriction_alias_arguments(tool_name, value):
    """Keep exact raw selections; defaults belong only in the core request."""
    restriction_canonical(value)
    _require(tool_name in NAMES and type(value) is dict, "arguments_invalid")
    mode = value.get("mode")
    if mode == "saved":
        _require(set(value) == {"mode", "result_source_ref"} and type(value["result_source_ref"]) is str
            and bool(value["result_source_ref"]), "arguments_invalid")
    else:
        required = {"mode", "sequence_ref"} | ({"enzyme_names"} if tool_name == NAMES[0] else set())
        _require(mode == "native" and required <= set(value) <= required | {"topology"}
            and type(value["sequence_ref"]) is str and bool(value["sequence_ref"])
            and ("topology" not in value or value["topology"] in ("linear", "circular")), "arguments_invalid")
        if tool_name == NAMES[0]:
            validate_restriction_record("EnzymeSelection", {"kind": "explicit", "names": value["enzyme_names"]})
    return deepcopy(value)


def restriction_native_request(tool_name, arguments, *, sequence, sequence_binding):
    arguments = validate_restriction_alias_arguments(tool_name, arguments)
    binding = validate_restriction_record("SequenceBinding", sequence_binding)
    _require(arguments["mode"] == "native" and arguments["sequence_ref"] == binding["sequence_ref"]
        and type(sequence) is str and bool(sequence) and sequence.isascii()
        and set(sequence.upper()) <= set("ACGTRYSWKMBDHVN")
        and binding["length_nt"] == len(sequence)
        and binding["content_sha256"] == hashlib.sha256(sequence.encode()).hexdigest(), "input_conflict")
    return {"version": "restriction_worker_request_v1", "mode": "native", "sequence": sequence,
        "selected_sequence": binding, "enzyme_selection": ({"kind": "explicit", "names": arguments["enzyme_names"]}
            if tool_name == NAMES[0] else {"kind": "commercial_native_batch", "names": None}),
        "topology": arguments.get("topology", "circular" if tool_name == NAMES[0] else "linear")}


def restriction_bound_schema(kind):
    _require(kind in SCHEMAS, "bound_record_kind_unknown")
    return deepcopy(SCHEMAS[kind])


def validate_restriction_bound_record(kind, value):
    schema = restriction_bound_schema(kind)
    restriction_canonical(value)
    _require(Draft202012Validator(schema).is_valid(value) and _strict(value, schema))
    value = deepcopy(value)
    if kind in ("InputBody", "Reservation", "PublishedBody"):
        args = validate_restriction_alias_arguments(value["tool_name"], value["arguments"])
        _require(value["operation_ref"] == identity("operation", {"key": value["operation_key"],
            "name": value["tool_name"], "arguments": args}), "operation_conflict")
        scope = value["scope"]
        for field in ("subject_refs", "read_selection_refs"):
            if field in scope:
                _require(scope[field] == sorted(set(scope[field])), "scope_conflict")
        for row in scope.get("segments", []):
            _require(row["target_ref"] in scope["subject_refs"] and row["start"] < row["end"], "scope_conflict")
    if kind == "InputBody":
        witness = validate_restriction_sequence_witness(value["witness"])
        _require(args["mode"] == "native" and args["sequence_ref"] == witness["sequence_ref"]
            and _same(witness["scope"], value["scope"]), "input_conflict")
    elif kind == "Software":
        for pin in [value["python"], value["native_source_file"], value["dictionary_file"], *value["implementation_files"]]:
            validate_restriction_record("FilePin", pin)
        _require(len({p["path"] for p in value["implementation_files"]}) == len(value["implementation_files"]), "software_conflict")
    elif kind == "Reservation":
        validate_restriction_bound_record("Software", value["software"])
        validate_restriction_record("SequenceBinding", value["sequence_binding"])
        _require(value["work_mode"] == args["mode"] == value["worker_request"]["mode"]
            and value["input_source_ref"] == value["sequence_binding"]["source_ref"]
            and _same(value["worker_request"]["selected_sequence"], value["sequence_binding"]), "input_conflict")
        if value["work_mode"] == "native":
            _require(value["prior_result_source_ref"] is None and _same(value["worker_request"],
                restriction_native_request(value["tool_name"], args, sequence=value["worker_request"]["sequence"],
                    sequence_binding=value["sequence_binding"])), "input_conflict")
        else:
            _require(value["prior_result_source_ref"] == args["result_source_ref"], "input_conflict")
            for pin in (value["worker_request"]["native_file"], value["worker_request"]["catalog_file"]):
                if pin is not None:
                    validate_restriction_record("FilePin", pin)
        root = PurePosixPath(value["directory"])
        validate_restriction_record("FilePin", {"path": str(root), "sha256": "0" * 64, "size_bytes": 0})
        _require(root.name == hashlib.sha256(value["operation_key"].encode()).hexdigest()
            and root.parent.name == "native-restriction", "path_conflict")
        for field, name in (("output_directory", "output"), ("handle_path", "handle.json"),
                ("stdout_path", "stdout.txt"), ("stderr_path", "stderr.txt")):
            _require(value[field] == str(root / name), "path_conflict")
        validate_restriction_record("FilePin", value["request_file"])
        _require(value["request_file"]["path"] == str(root / "request.json"), "path_conflict")
    elif kind == "ExecutionProof":
        view = value["original_view"]
        _require(view["metadata"].get("native_lifecycle_version") == view["version"], "proof_conflict")
        _require(view["terminal"] and view["quiescent"] and view["state"] == "returned", "proof_conflict")
        metadata = view["metadata"]
        _require(_same(value["returncode"], metadata.get("native_returncode")), "proof_conflict")
        for field in ("native_returncode", "observed_scratch_bytes"):
            measured = metadata.get(field)
            _require(measured is None or type(measured) is int, "proof_conflict")
            if field == "observed_scratch_bytes" and measured is not None:
                _require(measured >= 0, "proof_conflict")
        elapsed = metadata.get("elapsed_seconds")
        _require(elapsed is None or type(elapsed) in (int, float), "proof_conflict")
        for field in ("handle_artifact_ref", "control_request_artifact_ref", "status_artifact_ref", "native_receipt_artifact_ref"):
            _require(value[field] is None or re.fullmatch(r"artifact_[0-9a-f]{64}", value[field]) is not None, "proof_conflict")
        receipt = view["native_receipt"]
        _require((receipt is None) == (value["native_receipt_artifact_ref"] is None), "proof_conflict")
        if receipt is not None:
            _require(_same(receipt.get("native_returncode"), value["returncode"]), "proof_conflict")
        for info in view["files"].values():
            _require(info["available"] == (info["bytes"] is not None), "proof_conflict")
    elif kind == "PublishedBody":
        _require(value["work_mode"] == args["mode"] and value["prior_result_source_ref"] ==
            (None if args["mode"] == "native" else args["result_source_ref"]), "input_conflict")
        for role, file in value["files"].items():
            if file is not None:
                _require(file["artifact_ref"] == "artifact_" + file["sha256"], "file_identity_conflict")
            if role in value["validation"]:
                _require((file is None) == (value["validation"][role] == "missing"), "validation_conflict")
        if value["status"] == "completed":
            _require(all(v == "validated" for v in value["validation"].values())
                and value["failure_code"] is None and not value["issues"], "validation_conflict")
        if value["failure_code"] is None:
            _require(value["validation"]["mapping"] == "validated", "validation_conflict")
        if value["validation"]["mapping"] == "validated":
            _require(value["failure_code"] is None and value["validation"]["native"] == "validated", "validation_conflict")
        if value["status"] == "partial":
            _require(value["validation"]["native"] == "validated", "validation_conflict")
        if value["status"] == "failed":
            _require(value["validation"]["native"] != "validated" and value["failure_code"] == "native_unavailable", "validation_conflict")
        if value["failure_code"] == "reader_unavailable":
            _require(value["status"] == "partial" and value["validation"]["native"] == "validated", "validation_conflict")
        if value["failure_code"] == "mapping_invalid":
            _require(value["status"] == "invalid", "validation_conflict")
    return value


__all__ = ["restriction_bound_schema", "validate_restriction_bound_record",
    "validate_restriction_alias_arguments", "restriction_native_request"]
