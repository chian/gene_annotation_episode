"""Pure received-file contracts; shape validation establishes no custody.

Only the host input binding authenticates records, receipts and permissions.
Decoded documents retain supplied assertions; they are not producer proof.
These private contracts are not registered model-facing return schemas.
"""
from copy import deepcopy
import hashlib
import json
import math
import re
import unicodedata


RECEIVED_INPUT_VERSION = "molecular_sequence_received_input_result_v1"
RECEIVED_FILE_VERSION = "molecular_sequence_received_file_result_v1"
RECEIVED_SOURCE_VERSION = "molecular_sequence_received_source_result_v1"
RECEIVED_SUBJECT_VERSION = "molecular_sequence_received_subject_result_v1"
NAMESPACES = ("artifact", "source")
SUBJECT_NAMESPACES = ("input", "reference", "feature", "product", "read_subject")
TAG_KEYS = ("schema", "version")
_FAILURE_STAGES = {
    "invalid_context": "authority", "invalid_commission": "authority",
    "invalid_inheritance": "authority", "reference_not_received": "authority",
    "reference_denied": "authority", "reference_unavailable": "authority",
    "reference_type_conflict": "authority", "scope_denied": "authority",
    "source_identity_conflict": "authority", "artifact_not_received": "authority",
    "artifact_denied": "authority", "artifact_unavailable": "artifact",
    "artifact_identity_conflict": "artifact", "artifact_bytes_unavailable": "artifact",
    "invalid_utf8": "decode", "invalid_json": "decode",
    "duplicate_json_key": "decode", "nonfinite_json": "decode",
    "unrepresentable_json_number": "decode",
}
FAILURE_CODES = tuple(_FAILURE_STAGES)
FAILURE_STAGES = tuple(dict.fromkeys(_FAILURE_STAGES.values()))
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _require(condition):
    if not condition:
        raise ValueError("molecular_sequence_received_input_invalid")


def _copy(value):
    def check(item):
        kind = type(item)
        if kind is str:
            item.encode("utf-8"); return
        if item is None or kind in (int, bool): return
        if kind is float:
            _require(math.isfinite(item)); return
        if kind is list:
            for child in item: check(child)
            return
        if kind is dict:
            for key, child in item.items():
                _require(type(key) is str); check(key); check(child)
            return
        _require(False)
    try:
        check(value)
        return deepcopy(value)
    except (UnicodeError, RecursionError) as error:
        raise ValueError("molecular_sequence_received_input_invalid") from error


def input_record_digest(value):
    value = _copy(value)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()))


def _text(value):
    return type(value) is str and bool(value) and not any(c in value for c in "\0\r\n")


def _file_format(value):
    return type(value) is str and bool(value) and not any(
        unicodedata.category(char) == "Cc" for char in value)


def _same(left, right):
    return input_record_digest(left) == input_record_digest(right)


def molecular_sequence_input_failure(code):
    _require(type(code) is str and code in _FAILURE_STAGES)
    return dict(stage=_FAILURE_STAGES[code], code=code)


def _failure(value):
    _closed(value, "stage code")
    _require(type(value["code"]) is str and value["code"] in _FAILURE_STAGES
        and value["stage"] == _FAILURE_STAGES[value["code"]])


def unread_molecular_sequence_input_content(issue):
    _failure(issue)
    return dict(state="not_read", document_tag_key=None, document_version=None, value=None, failure=deepcopy(issue))


class _DecodeFailure(ValueError):
    def __init__(self, code): self.code = code


def decode_molecular_sequence_input(raw, *, tag_key):
    """Decode supplied bytes only; the caller separately verifies their identity."""
    _require(type(raw) is bytes and tag_key in TAG_KEYS)
    def fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise _DecodeFailure("duplicate_json_key")
            result[key] = value
        return result
    def constant(_): raise _DecodeFailure("nonfinite_json")
    def number(token):
        value = float(token)
        if not math.isfinite(value): raise _DecodeFailure("nonfinite_json")
        if value == 0 and any(c in "123456789" for c in token.lower().split("e", 1)[0]):
            raise _DecodeFailure("unrepresentable_json_number")
        return value
    def integer(token):
        try: return int(token)
        except ValueError as error: raise _DecodeFailure("unrepresentable_json_number") from error
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        code = "invalid_utf8"
    else:
        try:
            value = _copy(json.loads(text, object_pairs_hook=fields, parse_float=number,
                parse_int=integer, parse_constant=constant))
        except _DecodeFailure as error:
            code = error.code
        except (ValueError, TypeError, RecursionError, OverflowError):
            code = "invalid_json"
        else:
            present = type(value) is dict and tag_key in value
            version = value[tag_key] if present and type(value[tag_key]) is str else None
            return dict(state="decoded", document_tag_key=tag_key if present else None,
                document_version=version, value=value, failure=None)
    return dict(state="decode_failed", document_tag_key=None, document_version=None,
        value=None, failure=molecular_sequence_input_failure(code))


def _received_record_metadata(value, *, version, input_fields, namespaces=NAMESPACES):
    """Validate common record metadata, without reading or authorizing it."""
    value = _copy(value)
    _closed(value, "version selection input failure")
    _require(value["version"] == version)
    selected = value["selection"]; _closed(selected, "reference namespace")
    _require(_text(selected["reference"]) and selected["namespace"] in namespaces)
    issue = value["failure"]
    if issue is not None: _failure(issue)
    item = value["input"]
    if item is None:
        _require(issue is not None and issue["stage"] != "decode")
        return value
    _closed(item, input_fields)
    receiver = item["receiver"]; _closed(receiver, "run_id episode_id request_sha256 assignment_sha256")
    _require(all(_text(receiver[k]) for k in ("run_id", "episode_id"))
        and all(type(receiver[k]) is str and _SHA.fullmatch(receiver[k]) for k in ("request_sha256", "assignment_sha256")))
    _require(type(item["scope"]) is dict and type(item["inheritance_manifest"]) is dict)
    witness = item["witness"]; _closed(witness, "reference namespace record record_sha256 record_revision source_version")
    record = witness["record"]
    _require(type(record) is dict and witness["reference"] == selected["reference"] == record.get("id")
        and witness["namespace"] == selected["namespace"] == record.get("record_type")
        and witness["record_sha256"] == input_record_digest(record)
        and _same(witness["record_revision"], record.get("revision"))
        and _same(witness["source_version"], record.get("version") if selected["namespace"] == "source" else None))
    return value


def _received_metadata(value, *, version, input_fields, json_format):
    """Validate admitted File metadata; Source-only shape cannot select this path."""
    value = _received_record_metadata(value, version=version, input_fields=input_fields)
    item = value["input"]
    if item is None:
        return value
    record = item["witness"]["record"]
    selected = value["selection"]
    file = item["file"]; _closed(file, "artifact_ref sha256 size_bytes format")
    _require(type(file["sha256"]) is str and _SHA.fullmatch(file["sha256"])
        and file["artifact_ref"] == "artifact_" + file["sha256"]
        and type(file["size_bytes"]) is int and file["size_bytes"] >= 0
        and (file["format"] == "json" if json_format else _file_format(file["format"])))
    artifact = item["artifact_record"]; _closed(artifact, "id record_type sha256 size media_type")
    _require(artifact["record_type"] == "artifact" and artifact["id"] == file["artifact_ref"]
        and artifact["sha256"] == file["sha256"] and type(artifact["size"]) is int
        and artifact["size"] == file["size_bytes"] and _text(artifact["media_type"]))
    _require(_same(record, artifact) if selected["namespace"] == "artifact" else record.get("artifact_ref") == file["artifact_ref"])
    _require(item["byte_verification"] in ("verified", "unavailable", "identity_conflict"))
    return value


def validate_molecular_sequence_received_source(value):
    """Validate closed Source-only metadata, never File or producer authority."""
    value = _received_record_metadata(value, version=RECEIVED_SOURCE_VERSION,
        input_fields="receiver scope inheritance_manifest witness", namespaces=("source",))
    issue = value["failure"]
    _require(issue is None or issue["stage"] == "authority")
    _require((value["input"] is None) == (issue is not None))
    return value


def validate_molecular_sequence_received_subject(value):
    """Validate sequence-subject metadata in its actual record namespace."""
    value = _received_record_metadata(value, version=RECEIVED_SUBJECT_VERSION,
        input_fields="receiver scope inheritance_manifest witness", namespaces=SUBJECT_NAMESPACES)
    issue = value["failure"]
    _require(issue is None or issue["stage"] == "authority")
    _require((value["input"] is None) == (issue is not None))
    return value


def validate_molecular_sequence_received_input(value):
    """Validate closed data relationships, never a caller's claim of authority."""
    value = _received_metadata(value, version=RECEIVED_INPUT_VERSION,
        input_fields="receiver scope inheritance_manifest witness file artifact_record tag_key byte_verification content",
        json_format=True)
    item, issue = value["input"], value["failure"]
    if item is None:
        return value
    _require(item["tag_key"] in TAG_KEYS)
    content = item["content"]; _closed(content, "state document_tag_key document_version value failure")
    _require(content["state"] in ("not_read", "decoded", "decode_failed"))
    state = item["byte_verification"]
    _require(state in ("verified", "unavailable", "identity_conflict"))
    if state != "verified":
        expected = "artifact_bytes_unavailable" if state == "unavailable" else "artifact_identity_conflict"
        _require(content == unread_molecular_sequence_input_content(molecular_sequence_input_failure(expected))
            and issue == molecular_sequence_input_failure(expected))
    elif content["state"] == "decode_failed":
        _require(issue is not None and issue["stage"] == "decode" and content["failure"] == issue
            and content["value"] is None and content["document_tag_key"] is None and content["document_version"] is None)
    else:
        _require(content["state"] == "decoded" and issue is None and content["failure"] is None)
        document = content["value"]; tag = item["tag_key"]
        present = type(document) is dict and tag in document
        _require(content["document_tag_key"] == (tag if present else None)
            and content["document_version"] == (document[tag] if present and type(document[tag]) is str else None))
    return value


def validate_molecular_sequence_received_file(value):
    """Check raw-file metadata only; its format is selected, not detected."""
    value = _received_metadata(value, version=RECEIVED_FILE_VERSION,
        input_fields="receiver scope inheritance_manifest witness file artifact_record byte_verification",
        json_format=False)
    item, issue = value["input"], value["failure"]
    _require(issue is None or issue["stage"] != "decode")
    if item is not None:
        state = item["byte_verification"]
        expected = (None if state == "verified" else molecular_sequence_input_failure(
            "artifact_bytes_unavailable" if state == "unavailable" else "artifact_identity_conflict"))
        _require(issue == expected)
    return value


def molecular_sequence_received_input_schema():
    """Private host schema; opaque source/JSON content is never a model form."""
    def obj(properties):
        return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)
    def nullable(node): return {"anyOf": [node, {"type": "null"}]}
    text = {"type": "string", "minLength": 1}
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    issue = obj(dict(stage={"enum": list(FAILURE_STAGES)}, code={"enum": list(FAILURE_CODES)}))
    artifact = obj(dict(id=text, record_type={"const": "artifact"}, sha256=sha,
        size={"type": "integer", "minimum": 0}, media_type=text))
    file = obj(dict(artifact_ref=text, sha256=sha, size_bytes={"type": "integer", "minimum": 0}, format={"const": "json"}))
    content = obj(dict(state={"enum": ["not_read", "decoded", "decode_failed"]},
        document_tag_key={"enum": [None, *TAG_KEYS]}, document_version=nullable({"type": "string"}), value={}, failure=nullable(issue)))
    item = obj(dict(receiver=obj(dict(run_id=text, episode_id=text, request_sha256=sha, assignment_sha256=sha)),
        scope={"type": "object"}, inheritance_manifest={"type": "object"},
        witness=obj(dict(reference=text, namespace={"enum": list(NAMESPACES)}, record={"type": "object"},
            record_sha256=sha, record_revision={}, source_version={})),
        file=file, artifact_record=artifact, tag_key={"enum": list(TAG_KEYS)},
        byte_verification={"enum": ["verified", "unavailable", "identity_conflict"]}, content=content))
    return obj(dict(version={"const": RECEIVED_INPUT_VERSION},
        selection=obj(dict(reference=text, namespace={"enum": list(NAMESPACES)})), input=nullable(item), failure=nullable(issue)))


def molecular_sequence_received_file_schema():
    """Private raw-file metadata, without decoded content or a host path."""
    schema = molecular_sequence_received_input_schema()
    schema["properties"]["version"] = {"const": RECEIVED_FILE_VERSION}
    item = schema["properties"]["input"]["anyOf"][0]
    for name in ("tag_key", "content"):
        del item["properties"][name]
        item["required"].remove(name)
    item["properties"]["file"]["properties"]["format"] = {
        "type": "string", "minLength": 1, "not": {"pattern": "[\\u0000-\\u001f\\u007f-\\u009f]"}}
    issue = schema["properties"]["failure"]["anyOf"][0]
    issue["properties"]["stage"]["enum"] = [stage for stage in FAILURE_STAGES if stage != "decode"]
    issue["properties"]["code"]["enum"] = [code for code in FAILURE_CODES if _FAILURE_STAGES[code] != "decode"]
    return schema


def molecular_sequence_received_source_schema():
    """Private Source-only metadata; no artifact, path, bytes or decoded content."""
    schema = molecular_sequence_received_input_schema()
    schema["properties"]["version"] = {"const": RECEIVED_SOURCE_VERSION}
    schema["properties"]["selection"]["properties"]["namespace"] = {"const": "source"}
    item = schema["properties"]["input"]["anyOf"][0]
    for name in ("file", "artifact_record", "tag_key", "byte_verification", "content"):
        del item["properties"][name]
        item["required"].remove(name)
    item["properties"]["witness"]["properties"]["namespace"] = {"const": "source"}
    issue = schema["properties"]["failure"]["anyOf"][0]
    issue["properties"]["stage"]["enum"] = ["authority"]
    issue["properties"]["code"]["enum"] = [code for code in FAILURE_CODES if _FAILURE_STAGES[code] == "authority"]
    return schema


def molecular_sequence_received_subject_schema():
    """Private record metadata; sequence bytes and File access are separate."""
    schema = molecular_sequence_received_source_schema()
    schema["properties"]["version"] = {"const": RECEIVED_SUBJECT_VERSION}
    namespace = {"enum": list(SUBJECT_NAMESPACES)}
    schema["properties"]["selection"]["properties"]["namespace"] = deepcopy(namespace)
    item = schema["properties"]["input"]["anyOf"][0]
    item["properties"]["witness"]["properties"]["namespace"] = namespace
    return schema


__all__ = ["RECEIVED_INPUT_VERSION", "RECEIVED_FILE_VERSION", "RECEIVED_SOURCE_VERSION", "NAMESPACES", "TAG_KEYS", "FAILURE_CODES", "FAILURE_STAGES",
    "RECEIVED_SUBJECT_VERSION", "SUBJECT_NAMESPACES",
    "validate_molecular_sequence_received_input", "decode_molecular_sequence_input",
    "validate_molecular_sequence_received_file", "molecular_sequence_received_file_schema",
    "validate_molecular_sequence_received_source", "molecular_sequence_received_source_schema",
    "validate_molecular_sequence_received_subject", "molecular_sequence_received_subject_schema",
    "molecular_sequence_received_input_schema", "molecular_sequence_input_failure",
    "unread_molecular_sequence_input_content", "input_record_digest"]
