"""Frozen AppService support contracts and network-free relationship checks.

Schemas are packaged runtime assets. Validation proves shape and relationships
within the supplied value; the custody host must authenticate every referenced
record, byte artifact, selected action and receiving episode separately.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from threading import Lock

from jsonschema import Draft202012Validator, ValidationError, validators


_DOCUMENT = json.loads(Path(__file__).with_name("bvbrc_appservice_schemas.json").read_text())
_DEFINITIONS = _DOCUMENT["$defs"]

# This remembers only successful pure shape/relationship checks, never source
# contents, possession, selected actions, file integrity or episode authority.
# Digests rather than values keep closed episode data out of this small cache.
_VALIDATION_CACHE_SIZE = 512
_VALIDATED_CONTRACTS = OrderedDict()
_VALIDATION_CACHE_LOCK = Lock()


def _validation_key(schema, value):
    try:
        encoded = json.dumps((schema, value), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).digest()
    except (TypeError, ValueError, OverflowError, RecursionError):
        # A cache is optional. In particular, JSON's integer serialization limit
        # must not change which values the original validator accepts.
        return None


def _already_validated(key):
    if key is None:
        return False
    with _VALIDATION_CACHE_LOCK:
        if key not in _VALIDATED_CONTRACTS:
            return False
        _VALIDATED_CONTRACTS.move_to_end(key)
        return True


def _remember_validated(key):
    if key is not None:
        with _VALIDATION_CACHE_LOCK:
            _VALIDATED_CONTRACTS[key] = None
            _VALIDATED_CONTRACTS.move_to_end(key)
            if len(_VALIDATED_CONTRACTS) > _VALIDATION_CACHE_SIZE:
                _VALIDATED_CONTRACTS.popitem(last=False)


class ContractValidationError(ValueError):
    """A stable code and JSON pointers, without echoing potentially secret data."""

    def __init__(self, code, path="", *, contract=None):
        self.code = code
        self.diagnostics = [{"code": code, "path": path}]
        if contract is not None:
            self.diagnostics[0]["contract"] = contract
        super().__init__(code)


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _finite_json(value, path="", ancestors=None):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ContractValidationError("nonfinite_number", path)
        return
    if type(value) not in (dict, list):
        raise ContractValidationError("not_plain_json", path)
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise ContractValidationError("recursive_json", path)
    ancestors.add(id(value))
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ContractValidationError("nonstring_json_key", path)
            _finite_json(child, _pointer(path, key), ancestors)
    else:
        for index, child in enumerate(value):
            _finite_json(child, _pointer(path, index), ancestors)
    ancestors.remove(id(value))


def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _enum(validator, options, instance, schema):
    if not any(_same(instance, option) for option in options):
        yield ValidationError("value does not match a declared enum member")


def _const(validator, expected, instance, schema):
    if not _same(instance, expected):
        yield ValidationError("value does not match the declared constant")


_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) in (int, float),
})
_Validator = validators.extend(Draft202012Validator, {"enum": _enum, "const": _const},
                               type_checker=_TYPES)


def contract_schema(name: str) -> dict:
    """Return a detached schema with exactly its transitively reachable defs."""
    if type(name) is not str or name not in _DEFINITIONS:
        raise ContractValidationError("unknown_appservice_contract")
    reachable = set()

    def visit(node):
        if type(node) is dict:
            if "$ref" in node:
                ref = node["$ref"]
                if not ref.startswith("#/$defs/") or ref[8:] not in _DEFINITIONS:
                    raise RuntimeError("invalid_packaged_appservice_schema_reference")
                key = ref[8:]
                if key not in reachable:
                    reachable.add(key)
                    visit(_DEFINITIONS[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)

    root = {"$schema": _DOCUMENT["$schema"], "$ref": "#/$defs/" + name}
    visit(root)
    root["$defs"] = {key: deepcopy(value) for key, value in _DEFINITIONS.items() if key in reachable}
    return root


def _require(condition, code, path):
    if not condition:
        raise ContractValidationError(code, path)


def _unique(rows, field, path):
    values = [row[field] for row in rows]
    _require(len(values) == len(set(values)), "duplicate_" + field, path)


def _at(value, pointer):
    """Resolve an exact RFC 6901 pointer; never guess or normalize an operand."""
    if pointer == "":
        return value
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ContractValidationError("invalid_json_pointer", pointer)
    current = value
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if type(current) is dict and token in current:
            current = current[token]
        elif type(current) is list and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(current):
            current = current[int(token)]
        else:
            raise ContractValidationError("parameter_pointer_missing", pointer)
    return current


def _generation(generation, predecessor, path):
    _require((generation == 0 and predecessor is None) or
             (generation > 0 and predecessor is not None), "capability_predecessor_conflict", path)


def _object_association(obj, association, path):
    if association["output_path"] is not None:
        _require(obj["path"] == association["output_path"], "output_association_path_conflict", path)
    if association["output_uuid"] is not None:
        _require(obj["uuid"] == association["output_uuid"], "output_association_uuid_conflict", path)


def _relations(name, value, path):
    if name in {"ResultSelector", "ArtifactBundle"}:
        contents = {}
        for index, row in enumerate(value.get("supplied_contents", [])):
            key = row["source_ref"], row["artifact_field"]
            _require(key not in contents or _same(contents[key], row),
                     "supplied_content_binding_conflict", _pointer(_pointer(path, "supplied_contents"), index))
            contents[key] = row
    if name == "Range":
        _require(value[1] is None or value[1] >= value[0], "range_conflict", path)
    elif name == "ObservedRange":
        _require(value["end_inclusive"] >= value["start"], "range_conflict", path)
        _require(value["total_size"] is None or value["end_inclusive"] < value["total_size"],
                 "object_size_conflict", path)
    elif name == "InputBinding":
        populated = {key for key in ("content", "workspace_path", "inline_value", "link_evidence")
                     if value[key] is not None}
        expected = {"retained_bytes": {"content", "workspace_path"},
                    "workspace_object": {"workspace_path"},
                    "inline_parameter": ({"inline_value"} if value["inline_value"] is not None else set()),
                    "supplied_link": {"inline_value", "link_evidence"}}[value["kind"]]
        _require(populated == expected, "input_kind_content_conflict", path)
        if value["kind"] == "supplied_link":
            _require(type(value["inline_value"]) is str and bool(value["inline_value"]),
                     "supplied_link_value_invalid", path)
        _unique(value["members"], "member_id", _pointer(path, "members"))
    elif name == "AppServiceRequest":
        for field, key in (("input_bindings", "binding_id"), ("definition_inputs", "binding_id"),
                           ("workspace_targets", "target_id")):
            _unique(value[field], key, _pointer(path, field))
        inputs = {row["binding_id"]: row for row in value["input_bindings"]}
        for index, binding in enumerate(value["input_bindings"]):
            operand = _at(value["parameters"], binding["parameter_pointer"])
            expected = binding["workspace_path"] if binding["kind"] in ("workspace_object", "retained_bytes") else binding["inline_value"]
            _require(_same(operand, expected), "input_parameter_value_conflict",
                     _pointer(_pointer(path, "input_bindings"), index))
        for index, target in enumerate(value["workspace_targets"]):
            binding_id = target["input_binding_id"]
            if binding_id is not None:
                _require(binding_id in inputs, "unknown_input_binding", _pointer(path, "workspace_targets"))
                binding = inputs[binding_id]
                if binding["workspace_path"] is not None:
                    _require(binding["workspace_path"] == target["path"], "input_target_path_conflict",
                             _pointer(_pointer(path, "workspace_targets"), index))
    elif name == "ResultSelector":
        _unique(value["requirements"], "requirement_id", _pointer(path, "requirements"))
        _unique(value["supplied_capabilities"], "binding_id", _pointer(path, "supplied_capabilities"))
        _require(value["endpoint"] != "requested_projection" or value["adapter"] is not None,
                 "scientific_adapter_unbound", path)
        schema = value["requested_schema"]
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as error:
            raise ContractValidationError("requested_schema_invalid", _pointer(path, "requested_schema")) from error
        _require(schema.get("type") == "object" and schema.get("additionalProperties") is False,
                 "requested_schema_not_closed", _pointer(path, "requested_schema"))
    elif name in ("Arguments_download_capability", "CapabilityReceipt"):
        _generation(value["generation"], value["predecessor_receipt_ref"], path)
        if name == "CapabilityReceipt":
            _unique(value["entries"], "input_index", _pointer(path, "entries"))
            for entry in value["entries"]:
                _object_association(entry["object"], entry["task_association"], path)
                _require((entry["expires_at"] is None) == (entry["expiry_evidence"] is None),
                         "capability_expiry_evidence_conflict", path)
    elif name == "OperationSelection":
        _relations("Arguments_" + value["name"].rsplit(".", 1)[1], value["arguments"], _pointer(path, "arguments"))
    elif name == "Arguments_workspace_create":
        _unique(value["objects"], "target_id", _pointer(path, "objects"))
    elif name == "EffectDescriptor":
        _require(value["kind"] == value["slot"]["kind"], "effect_slot_kind_conflict", path)
        if value["kind"] == "download_capability":
            predecessors = value["predecessor_evidence_refs"]
            _require(not predecessors if value["slot"]["generation"] == 0 else bool(predecessors),
                     "capability_predecessor_conflict", path)
    elif name == "EffectReceipt":
        state = value["state"]
        _require(state != "prepared_not_issued" or value["issued_at"] is None,
                 "effect_issue_time_conflict", path)
        _require(state not in ("issued_unknown", "confirmed") or value["issued_at"] is not None,
                 "effect_issue_time_missing", path)
        _require((state == "confirmed") == (value["confirmation_source_ref"] is not None),
                 "effect_confirmation_conflict", path)
        if value["failure"] is not None and value["failure"]["effect_outcome"] is not None:
            expected = {"prepared_not_issued": "not_sent", "not_sent": "not_sent",
                        "issued_unknown": "unknown", "confirmed": "confirmed"}[state]
            _require(value["failure"]["effect_outcome"] == expected, "effect_failure_outcome_conflict", path)
    elif name == "SnapshotBinding":
        _require(value["source_ref"] == value["content"]["source_ref"], "snapshot_source_conflict", path)
    elif name == "TaskAssociation":
        if value["kind"] != "unverified_original_path":
            _require(value["evidence_ref"] is not None and value["pointer"] is not None,
                     "output_association_missing", path)
        if value["kind"] in ("task_result_manifest", "task_info_object"):
            _require(value["output_uuid"] is not None, "output_association_missing", path)
        _require(value["byte_version_status"] != "producer_bytes_bound" or bool(value["version_evidence"]),
                 "output_version_unproven", path)
    elif name == "TaskInfoReceipt":
        _require(value["file"] not in ("stdout", "stderr") or value["reported_object_uuid"] is None,
                 "task_info_object_invalid", path)
        _require(value["reported_object_uuid"] is None or value["body_complete"],
                 "task_info_object_incomplete", path)
        if value["local_window"] is not None:
            window = value["local_window"]
            _require(window["end_exclusive"] >= window["start"], "range_conflict", path)
            _require(value["file"] in ("stdout", "stderr"), "task_info_window_invalid", path)
            snapshot = value["receipt"]["snapshot"]
            if snapshot is not None:
                _require(window["end_exclusive"] <= snapshot["content"]["byte_count"],
                         "task_info_window_outside_body", path)
    elif name == "OriginalTask":
        allowed = {value["required_application_id"]}
        if value["required_application_id"] == "InfluenzaHASubtypeConversion":
            allowed.add("HASubtypeNumberingConversion")
        _require(value["native_application_id"] in allowed, "original_application_mismatch", path)
    elif name == "ArtifactMember":
        _object_association(value["workspace_object"], value["task_association"], path)
        transfer = value["transfer"]
        observed = transfer["observed_range"]
        if observed is not None:
            width = observed["end_inclusive"] - observed["start"] + 1
            _require(value["byte_count"] == width if transfer["body_complete"] else value["byte_count"] <= width,
                     "range_byte_count_conflict", path)
        if transfer["object_complete"] == "yes" and transfer["total_size"] is not None:
            _require(value["byte_count"] == transfer["total_size"], "object_size_conflict", path)
    elif name == "Transfer":
        observed = value["observed_range"]
        if observed is not None and observed["total_size"] is not None:
            _require(value["total_size"] == observed["total_size"], "object_size_conflict", path)
        if value["object_complete"] == "yes":
            _require(value["body_complete"], "incomplete_body_marked_complete", path)
            if observed is not None:
                _require(observed["start"] == 0 and value["total_size"] is not None
                         and observed["end_inclusive"] + 1 == value["total_size"], "range_conflict", path)
    elif name == "ArtifactBundle":
        _unique(value["input_bindings"], "binding_id", _pointer(path, "input_bindings"))
        _unique(value["missing_requirements"], "requirement_id", _pointer(path, "missing_requirements"))
        inputs = {row["binding_id"]: row for row in value["input_bindings"]}
        for artifact in value["artifacts"]:
            _require(artifact["task_association"]["task_id"] == value["original_task"]["task_id"],
                     "original_task_mismatch", path)
            _require(artifact["transfer"]["receipt_ref"] in value["acquisition_receipt_refs"],
                     "acquisition_receipt_missing", path)
        raw_sources = {row["source_ref"] for row in value["artifacts"]}
        query_keys = set()
        for query in value["query_bindings"]:
            _require(query["input_binding_id"] in inputs, "unknown_input_binding", path)
            binding = inputs[query["input_binding_id"]]
            members = [m for m in binding["members"] if m["member_id"] == query["input_member_id"]]
            _require(len(members) == 1, "query_member_missing", path)
            member = members[0]
            _require(member["member_pointer"] == query["input_member_pointer"], "query_member_pointer_conflict", path)
            for key in ("length", "molecule", "sequence_sha256"):
                _require(_same(member[key], query[key]), "query_member_fact_conflict", path)
            if binding["content"] is not None:
                _require(binding["content"]["source_ref"] == query["input_source_ref"], "query_source_conflict", path)
            _require(query["raw_source_ref"] in raw_sources, "query_raw_source_missing", path)
            key = (query["raw_source_ref"], query["raw_report_ordinal"])
            _require(key not in query_keys, "duplicate_query_report_binding", path)
            query_keys.add(key)
        _require(value["status"] != "ok" or not value["missing_requirements"], "bundle_status_conflict", path)
    elif name == "PublicationInputs":
        _require(value["current_operation"]["name"] == "api.bvbrc_appservice.download", "publication_operation_conflict", path)
        _require(_same(value["selector"]["adapter"], value["adapter"]), "publication_adapter_conflict", path)
        # An unavailable selected adapter has no implementation digest. Its
        # explicit selection survives acquisition without a fabricated hash.
        _require(value["adapter"] is not None or value["adapter_implementation_sha256"] is None,
                 "publication_adapter_binding_conflict", path)
    elif name == "PreparedOperation":
        _require(value["mutates_remote"] == bool(value["effects"]), "prepared_effects_conflict", path)
        _require(value["request_sha256"] == value["bound_inputs"]["request_sha256"] and
                 value["arguments_sha256"] == value["bound_inputs"]["selected_argument_sha256"],
                 "prepared_binding_conflict", path)
        for effect in value["effects"]:
            _require(_same(effect["original_job_owner"], value["bound_inputs"]["original_job_owner"]),
                     "prepared_effect_owner_conflict", path)
            _require(effect["resource_id"] == value["bound_inputs"]["resource_id"],
                     "prepared_effect_resource_conflict", path)
        _require(value["operation"] == value["bound_inputs"]["resolved"]["operation"],
                 "prepared_resolved_operation_conflict", path)
    elif name == "ResolvedObject":
        if value["task_association"] is not None:
            _object_association(value["object"], value["task_association"], path)
        if value["metadata"] is not None:
            for key in ("path", "uuid", "type"):
                _require(value["metadata"][key] == value["object"][key],
                         "resolved_metadata_object_conflict", path)
    elif name == "ResolvedUpload":
        _require(value["input"]["content"] is not None, "upload_content_missing", path)
    elif name == "ResolvedCapability":
        entry = value["entry"]
        _object_association(entry["object"], entry["task_association"], path)
        _require((entry["expires_at"] is None) == (entry["expiry_evidence"] is None),
                 "capability_expiry_evidence_conflict", path)
    elif name == "ResolvedInputs":
        if value["operation"] == "api.bvbrc_appservice.workspace_create":
            _unique(value["data_bindings"], "binding_id", _pointer(path, "data_bindings"))
    elif name == "BoundInputs":
        task = value["resolved"].get("original_task")
        if task is not None:
            _require(task["resource_id"] == value["resource_id"], "resolved_task_resource_conflict", path)
    elif name in ("Failure", "AdapterResult", "BundlePublication"):
        key = "requirements" if name == "Failure" else "missing_requirements"
        _unique(value[key], "requirement_id", _pointer(path, key))


def _walk(schema, value, validator, path=""):
    if "$ref" in schema:
        name = schema["$ref"][8:]
        _relations(name, value, path)
        _walk(_DEFINITIONS[name], value, validator, path)
        return
    if schema.get("pattern") == "^(|/.*)$":
        _require(re.search(r"~(?![01])", value) is None, "invalid_json_pointer", path)
    for keyword in ("oneOf", "anyOf", "allOf"):
        for branch in schema.get(keyword, []):
            if validator.evolve(schema=branch).is_valid(value):
                _walk(branch, value, validator, path)
    if type(value) is dict:
        for key, child in value.items():
            child_schema = schema.get("properties", {}).get(key, schema.get("additionalProperties"))
            if type(child_schema) is dict:
                _walk(child_schema, child, validator, _pointer(path, key))
    elif type(value) is list:
        prefix = schema.get("prefixItems", [])
        for index, child in enumerate(value):
            child_schema = prefix[index] if index < len(prefix) else schema.get("items")
            if type(child_schema) is dict:
                _walk(child_schema, child, validator, _pointer(path, index))


def validate_contract(name: str, value: object):
    """Validate plain finite JSON plus pure relationships; return a fresh copy."""
    schema = contract_schema(name)
    try:
        _finite_json(value)
        key = _validation_key(schema, value)
        if _already_validated(key):
            return deepcopy(value)
        validator = _Validator(schema)
        error = next(validator.iter_errors(value), None)
        if error is not None:
            path = ""
            for token in error.absolute_path:
                path = _pointer(path, token)
            raise ContractValidationError("contract_shape_invalid", path, contract=name)
        _walk(schema, value, validator)
        _remember_validated(key)
        return deepcopy(value)
    except RecursionError as error:
        raise ContractValidationError("json_nesting_too_deep") from error


def validate_request(value: dict) -> dict:
    """Validate assignment structure without defaults, preparation or I/O."""
    return validate_contract("AppServiceRequest", value)


def download_request(call, *, arguments=None):
    """Exact retained legacy or capped download identity, without normalization.

    A legacy identity is readable evidence only. The transport and fresh host
    admission separately require an explicit cap before a new GET.
    """
    _require(type(call) is dict and set(call) in (
        {"url", "byte_range"}, {"url", "byte_range", "max_bytes"}),
        "download_call_invalid", "/call")
    _require(type(call["url"]) is str and bool(call["url"]), "download_call_invalid", "/call/url")
    selected_range = call["byte_range"]
    if selected_range is not None:
        validate_contract("Range", selected_range)
    bounded = "max_bytes" in call
    if bounded:
        _require(type(call["max_bytes"]) is int and call["max_bytes"] > 0,
            "download_byte_limit_invalid", "/call/max_bytes")
    if arguments is not None:
        _require(type(arguments) is dict and "byte_range" in arguments
            and _same(selected_range, arguments["byte_range"])
            and bounded == ("max_bytes" in arguments)
            and (not bounded or _same(call["max_bytes"], arguments["max_bytes"])),
            "download_selected_limit_conflict", "/arguments")
    result = {"kind": "download", "url": call["url"],
        "requested_byte_range": deepcopy(selected_range)}
    if bounded:
        result["max_bytes"] = call["max_bytes"]
    return result


__all__ = ["ContractValidationError", "contract_schema", "validate_contract", "validate_request", "download_request"]
