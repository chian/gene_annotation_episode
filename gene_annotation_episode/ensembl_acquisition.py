"""Pure, explicit acquisition contracts for the retained Ensembl 116 BioMart.

HTTP, Source custody, admission and receipts belong to the existing host.  This
module neither follows the native registry's URLs nor chooses species, aliases
or follow-up queries.  Discovery evidence is immutable input, not authority.
"""
from copy import deepcopy
import base64
import hashlib
import json
import math
import re
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator, validators

from .acquisition import SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt


TOOL = "public.ensembl.request"
VERSION = "ensembl_biomart_acquisition_result_v1"
MODEL_VIEW_VERSION = "ensembl_biomart_model_view_v1"
VALUE_VERSION = "ensembl_biomart_acquisition_value_v1"
RESOURCE = "ensembl116_biomart"
URL = "https://jun2026.archive.ensembl.org/biomart/martservice"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_GENE_IDS = 100
OPERATIONS = ("registry", "datasets", "configuration", "gene_homologies")


def _object(properties):
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}


_TEXT = {"type": "string"}
_NULL_TEXT = {"type": ["string", "null"]}
_NAME = {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,127}$"}
_DATASET = {"type": "string", "pattern": "^[a-z][a-z0-9_]*_gene_ensembl$", "maxLength": 128}
_SOURCE = {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$",
    "format": "reference", "x-reference-namespace": "source"}
_ARTIFACT = {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$",
    "format": "reference", "x-reference-namespace": "artifact"}
_CONTEXT = {"virtual_schema": _NAME, "mart": _NAME}
_OPERANDS = {
    "registry": {},
    "datasets": {**_CONTEXT, "registry_source_ref": _SOURCE},
    "configuration": {**_CONTEXT, "dataset": _DATASET, "datasets_source_ref": _SOURCE},
    "gene_homologies": {**_CONTEXT, "source_dataset": _DATASET, "target_dataset": _DATASET,
        "source_configuration_ref": _SOURCE, "target_configuration_ref": _SOURCE,
        "source_attribute_style": {"enum": ["base", "homologs"]},
        "gene_ids": {"type": "array", "minItems": 1, "maxItems": MAX_GENE_IDS,
            "items": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}$"}},
        "include_identity_percentages": {"type": "boolean"},
        "include_confidence": {"type": "boolean"}},
}
_ARGUMENTS = {"oneOf": [_object({"operation": {"const": tag}, "resource": {"const": RESOURCE},
    **deepcopy(fields), "max_bytes": {"type": "integer", "minimum": 1,
        "maximum": MAX_RESPONSE_BYTES}}) for tag, fields in _OPERANDS.items()]}
ARGUMENTS_SCHEMA = deepcopy(_ARGUMENTS)
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
        .redefine("integer", lambda _, value: type(value) is int)
        .redefine("number", lambda _, value: type(value) is int
            or type(value) is float and math.isfinite(value)))
_SOURCE_RE = re.compile(_SOURCE["pattern"], re.ASCII)
_ARTIFACT_RE = re.compile(_ARTIFACT["pattern"], re.ASCII)


def _require(condition, code="ensembl_value_invalid"):
    if not condition:
        raise ValueError(code)


def _plain(value):
    if type(value) is dict:
        for key, child in value.items():
            _require(type(key) is str)
            key.encode("utf-8")
            _plain(child)
    elif type(value) is list:
        for child in value:
            _plain(child)
    elif type(value) is str:
        value.encode("utf-8")
    else:
        _require(type(value) in (type(None), bool, int, float))
        if type(value) is float:
            _require(math.isfinite(value))


def _validated(value, schema):
    try:
        _plain(value)
        _require(_STRICT(schema).is_valid(value))
    except (TypeError, KeyError, OverflowError, RecursionError, UnicodeError) as error:
        raise ValueError("ensembl_value_invalid") from error
    return deepcopy(value)


def _same(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        right, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_ensembl_arguments(arguments):
    value = _validated(arguments, _ARGUMENTS)
    for name, child in value.items():
        if name.endswith("_ref"):
            _require(_SOURCE_RE.fullmatch(child) is not None)
        elif name in {"virtual_schema", "mart"}:
            _require(re.fullmatch(_NAME["pattern"], child, re.ASCII) is not None)
        elif name in {"dataset", "source_dataset", "target_dataset"}:
            _require(re.fullmatch(_DATASET["pattern"], child, re.ASCII) is not None)
    if value["operation"] == "gene_homologies":
        _require(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}", item, re.ASCII)
            is not None for item in value["gene_ids"]))
        _require(value["source_dataset"] != value["target_dataset"], "ensembl_distinct_datasets_required")
        _require(value["source_configuration_ref"] != value["target_configuration_ref"],
            "ensembl_distinct_configurations_required")
    return value


def _column_specs(arguments):
    if arguments["operation"] != "gene_homologies":
        return []
    prefix = "homologs_" if arguments["source_attribute_style"] == "homologs" else ""
    target = arguments["target_dataset"][:-len("_gene_ensembl")] + "_homolog_"
    rows = [("source_gene_id", prefix + "ensembl_gene_id", None),
        ("source_chromosome", prefix + "chromosome_name", None),
        ("source_start", prefix + "start_position", None),
        ("source_end", prefix + "end_position", None),
        ("source_strand", prefix + "strand", None),
        ("target_gene_id", target + "ensembl_gene", None),
        ("target_chromosome", target + "chromosome", None),
        ("target_start", target + "chrom_start", None),
        ("target_end", target + "chrom_end", None),
        ("homology_type", target + "orthology_type", None)]
    if arguments["include_identity_percentages"]:
        rows += [("target_percent_identity", target + "perc_id", "target_sequence"),
            ("query_percent_identity", target + "perc_id_r1", "query_sequence")]
    if arguments["include_confidence"]:
        rows.append(("native_orthology_confidence", target + "orthology_confidence", None))
    return [{"role": role, "attribute": attribute, "denominator": denominator}
        for role, attribute, denominator in rows]


def _query_xml(arguments):
    root = ET.Element("Query", {"virtualSchemaName": arguments["virtual_schema"],
        "formatter": "TSV", "header": "1", "uniqueRows": "0", "count": "0",
        "completionStamp": "1", "datasetConfigVersion": "0.6"})
    dataset = ET.SubElement(root, "Dataset", {"name": arguments["source_dataset"], "interface": "default"})
    ET.SubElement(dataset, "Filter", {"name": "ensembl_gene_id", "value": ",".join(arguments["gene_ids"])})
    for column in _column_specs(arguments):
        ET.SubElement(dataset, "Attribute", {"name": column["attribute"]})
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)


def ensembl_request_spec(arguments):
    """Deterministic transport only; host must validate discovery before I/O."""
    arguments = validate_ensembl_arguments(arguments)
    tag = arguments["operation"]
    params = {"type": tag}
    body, content_type = None, None
    if tag != "registry":
        params.update(virtualSchema=arguments["virtual_schema"], mart=arguments["mart"])
    if tag == "configuration":
        params.update(dataset=arguments["dataset"], interface="default")
    if tag == "gene_homologies":
        params = {}
        body = urlencode({"query": _query_xml(arguments)}).encode("ascii")
        content_type = "application/x-www-form-urlencoded; charset=UTF-8"
    return {"service": "ensembl", "url": URL, "method": "POST" if body is not None else "GET",
        "params": params, "body": body, "content_type": content_type,
        "media_type": "application/xml" if tag in {"registry", "configuration"} else "text/plain",
        "max_bytes": arguments["max_bytes"], "follow_redirects": False}


def ensembl_discovery_refs(arguments):
    """Direct selected Source operands; no admission or parent permissions."""
    arguments = validate_ensembl_arguments(arguments)
    fields = {"registry": (), "datasets": ("registry_source_ref",),
        "configuration": ("datasets_source_ref",),
        "gene_homologies": ("source_configuration_ref", "target_configuration_ref")}
    return [arguments[name] for name in fields[arguments["operation"]]]


def _address(spec):
    return spec["url"] + ("?" + urlencode(spec["params"]) if spec["params"] else "")


_COUNT = {"type": ["integer", "null"], "minimum": 0}
_RESPONSE = _object({"request_url": _TEXT, "request_method": {"enum": ["GET", "POST"]},
    "request_body_sha256": _NULL_TEXT, "media_type": _TEXT,
    "http_status": {"type": ["integer", "null"], "minimum": 100, "maximum": 599},
    "content_type": _NULL_TEXT, "body_complete": {"type": ["boolean", "null"]},
    "retained_bytes": {"type": "integer", "minimum": 0}, "reported_retained_bytes": _COUNT,
    "observed_body_bytes": _COUNT, "declared_body_bytes": _COUNT, "response_byte_limit": _COUNT,
    "capture_failure": _NULL_TEXT, "retry_after": _NULL_TEXT,
    "timeout_seconds": {"type": "number", "exclusiveMinimum": 0}, "automatic_redirects": {"const": False}})
_XML_REF = {"$ref": "#/$defs/XMLNode"}
_XML_NODE = _object({"tag": _TEXT, "attributes": {"type": "array", "items":
    _object({"name": _TEXT, "value": _TEXT})}, "text": _NULL_TEXT, "tail": _NULL_TEXT,
    "children": {"type": "array", "items": _XML_REF}})
_LINE = _object({"line_number": {"type": "integer", "minimum": 1}, "text": _TEXT,
    "ending": {"enum": ["", "\n", "\r", "\r\n"]}, "cells": {"type": "array", "items": _TEXT},
    "role": {"enum": ["blank", "header", "row", "completion", "error", "unclassified"]}})
_COLUMN = _object({"role": _TEXT, "attribute": _TEXT, "denominator": _NULL_TEXT,
    "native_display_name": _NULL_TEXT})
_DATASET_CONTEXT = _object({"dataset": _TEXT, "display_name": _NULL_TEXT,
    "dataset_version": _NULL_TEXT, "version_meaning": {"const": "native_assembly_or_genebuild_not_ensembl_release"},
    "configuration_source_ref": _SOURCE, "datasets_source_ref": _SOURCE})
_DISCOVERY = _object({"source_ref": _SOURCE, "raw_artifact_ref": _ARTIFACT,
    "operation": {"enum": list(OPERATIONS[:-1])}})
ISSUE_CODES = (
    "transport_metadata_unavailable", "transport_count_conflict", "http_not_success", "http_redirect",
    "response_incomplete", "response_byte_limit_exceeded", "response_capture_failure", "content_type_mismatch",
    "invalid_native_utf8", "invalid_native_xml", "native_xml_doctype_forbidden", "native_xml_root_invalid",
    "native_configuration_identity_conflict", "native_configuration_interface_conflict",
    "native_error_response", "native_response_empty", "native_column_arity_conflict",
    "native_header_missing", "native_header_context_missing", "native_header_context_conflict",
    "native_completion_missing", "native_completion_conflict",
    "native_data_after_completion", "native_source_id_not_requested", "native_source_id_missing",
    "native_coordinate_invalid", "native_strand_invalid", "native_homology_association_incomplete",
)
_RESULT = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"XMLNode": _XML_NODE},
    **_object({"version": {"const": VERSION}, "operation": {"const": TOOL}, "service": {"const": "ensembl"},
        "resource": {"const": RESOURCE}, "source_ref": _SOURCE, "raw_artifact_ref": _ARTIFACT,
        "requested": _ARGUMENTS, "response": _RESPONSE, "native_text": _NULL_TEXT,
        "parse_state": {"enum": ["xml", "tsv", "decode_failed"]},
        "decode_error": {"enum": [None, "invalid_native_utf8", "invalid_native_xml", "native_xml_doctype_forbidden"]},
        "xml_document": {"anyOf": [{"type": "null"}, _XML_REF]},
        "tsv_lines": {"type": "array", "items": _LINE},
        "native_response_state": {"enum": ["data", "error", "invalid", "unavailable"]},
        "representation_state": {"enum": ["complete", "partial", "invalid"]},
        "native_completion": {"enum": ["reported_complete", "missing", "conflicting", "not_applicable"]},
        "columns": {"type": "array", "items": _COLUMN},
        "dataset_contexts": {"type": "array", "items": _DATASET_CONTEXT},
        "discovery_evidence": {"type": "array", "uniqueItems": True, "items": _DISCOVERY},
        "requested_id_count": _COUNT, "retained_row_count": _COUNT,
        "matching_population_count": {"type": "null"},
        "population_coverage": {"const": "selected_response_only"},
        "native_pagination": {"const": "not_exposed"},
        "coordinate_convention": {"enum": [None, "native_one_based_inclusive"]},
        "issues": {"type": "array", "uniqueItems": True, "items":
            _object({"code": {"enum": list(ISSUE_CODES)}, "pointer": _TEXT})}})}
_RESULT["$id"] = "urn:gene-annotation:ensembl-acquisition:" + hashlib.sha256(json.dumps(
    _RESULT, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

# Private retained data, not a Source or a receiver permission. The original
# rich public schema stays literal for existing records and cached actions.
_VALUE = deepcopy(_RESULT)
_VALUE.pop("$id")
_VALUE["properties"]["version"] = {"const": VALUE_VERSION}
_VALUE["properties"].pop("source_ref")
_VALUE["required"].remove("source_ref")
_VALUE["properties"]["observed_transfer"] = _object({
    "declared_body_bytes": {}, "body_capture_failure": {}})
_VALUE["required"].append("observed_transfer")

ENSEMBL_FAILURE_CODES = tuple(dict.fromkeys([
    *("ensembl_" + code for code in ISSUE_CODES),
    "data_acquisition_failed",
    "data_acquisition_publication_incomplete",
    "ensembl_artifact_identity_conflict",
    "ensembl_artifact_reference_invalid",
    "ensembl_attribute_not_uniquely_advertised",
    "ensembl_control_invalid",
    "ensembl_dataset_interface_not_advertised",
    "ensembl_dataset_not_uniquely_advertised",
    "ensembl_discovery_context_conflict",
    "ensembl_discovery_custody_conflict",
    "ensembl_discovery_evidence_invalid",
    "ensembl_discovery_operation_conflict",
    "ensembl_discovery_producer_invalid",
    "ensembl_discovery_response_not_complete",
    "ensembl_discovery_saved_result_conflict",
    "ensembl_discovery_snapshot_invalid",
    "ensembl_discovery_source_invalid",
    "ensembl_discovery_source_unavailable",
    "ensembl_distinct_configurations_required",
    "ensembl_distinct_datasets_required",
    "ensembl_failure_witness_invalid",
    "ensembl_filter_not_uniquely_advertised",
    "ensembl_mart_not_uniquely_advertised",
    "ensembl_native_qualification_conflict",
    "ensembl_native_representation_conflict",
    "ensembl_original_action_conflict",
    "ensembl_original_action_incomplete",
    "ensembl_original_action_required",
    "ensembl_original_operation_conflict",
    "ensembl_prepared_request_conflict",
    "ensembl_received_input_authority_required",
    "ensembl_result_request_conflict",
    "ensembl_retained_discovery_conflict",
    "ensembl_saved_outcome_conflict",
    "ensembl_saved_receipt_conflict",
    "ensembl_saved_response_conflict",
    "ensembl_saved_result_conflict",
    "ensembl_saved_source_conflict",
    "ensembl_selection_conflict",
    "ensembl_snapshot_body_conflict",
    "ensembl_snapshot_byte_limit_conflict",
    "ensembl_snapshot_effective_url_conflict",
    "ensembl_snapshot_headers_conflict",
    "ensembl_snapshot_headers_invalid",
    "ensembl_snapshot_invalid",
    "ensembl_snapshot_request_conflict",
    "ensembl_snapshot_selected_request_conflict",
    "ensembl_snapshot_transport_invalid",
    "ensembl_snapshot_transport_policy_conflict",
    "ensembl_source_identity_conflict",
    "ensembl_source_invalid",
    "ensembl_source_lineage_cycle",
    "ensembl_source_lineage_selection_conflict",
    "ensembl_source_not_received",
    "ensembl_source_reference_invalid",
    "ensembl_source_request_conflict",
    "ensembl_transfer_metadata_conflict",
    "ensembl_value_invalid",
    "invalid_tool_input",
]))


def ensembl_result_schema():
    return deepcopy(_RESULT)


def _issue(code, pointer):
    return {"code": code, "pointer": pointer}


def _unique_issues(issues):
    seen, result = set(), []
    for row in issues:
        key = row["code"], row["pointer"]
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


class _XMLBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("native_xml_doctype_forbidden")


def _xml_node(node):
    return {"tag": "#comment" if node.tag is ET.Comment else "#processing_instruction"
        if node.tag is ET.ProcessingInstruction else node.tag,
        "attributes": [{"name": name, "value": value} for name, value in node.attrib.items()],
        "text": node.text, "tail": node.tail, "children": [_xml_node(child) for child in node]}


def _tag(node):
    return node["tag"]


def _attributes(node):
    return {row["name"]: row["value"] for row in node["attributes"]}


def _walk(node):
    yield node
    for child in node["children"]:
        yield from _walk(child)


def _lines(text):
    result = []
    for match in re.finditer(r"([^\r\n]*)(\r\n|\r|\n|$)", text):
        if match.start() == match.end():
            continue
        value, ending = match.groups()
        result.append({"line_number": len(result) + 1, "text": value, "ending": ending,
            "cells": value.split("\t"), "role": "row"})
    return result


def _native_error(text):
    return any(line.startswith(("Query ERROR:", "ERROR:", "BioMart::Exception"))
        for line in re.split(r"\r\n|\r|\n", text))


def _parse(raw, arguments):
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return None, "decode_failed", "invalid_native_utf8", None, []
    if arguments["operation"] in {"registry", "configuration"}:
        try:
            parser = ET.XMLParser(target=_XMLBuilder(insert_comments=True, insert_pis=True))
            document = _xml_node(ET.fromstring(text, parser=parser))
        except (ET.ParseError, ValueError, RecursionError) as error:
            code = "native_xml_doctype_forbidden" if str(error) == "native_xml_doctype_forbidden" else "invalid_native_xml"
            return text, "decode_failed", code, None, []
        return text, "xml", None, document, []
    return text, "tsv", None, None, _lines(text)


def _snapshot_response(snapshot, arguments, artifact_ref):
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "ensembl_snapshot_invalid")
    _plain(snapshot.request)
    _require(_same(snapshot.request, arguments), "ensembl_snapshot_selected_request_conflict")
    transport = snapshot.transport
    _require(type(transport) is dict, "ensembl_snapshot_transport_invalid")
    spec = ensembl_request_spec(arguments)
    address, request = _address(spec), transport.get("request")
    _require(type(request) is dict and request.get("method") == spec["method"]
        and request.get("url") == address, "ensembl_snapshot_request_conflict")
    expected_body = spec["body"]
    if expected_body is None:
        _require(not {"body_base64", "body_sha256"}.intersection(request), "ensembl_snapshot_body_conflict")
    else:
        _require(request.get("body_base64") == base64.b64encode(expected_body).decode("ascii")
            and request.get("body_sha256") == hashlib.sha256(expected_body).hexdigest(),
            "ensembl_snapshot_body_conflict")
    headers = request.get("headers")
    _require(type(headers) is dict and all(type(k) is str and type(v) is str for k, v in headers.items()),
        "ensembl_snapshot_headers_invalid")
    def request_header(name):
        values = [value for key, value in headers.items() if key.lower() == name]
        return values[0] if len(values) == 1 else None
    _require(request_header("accept") == spec["media_type"]
        and (expected_body is None or request_header("content-type") == spec["content_type"]),
        "ensembl_snapshot_headers_conflict")
    _require(snapshot.service == "ensembl" and snapshot.url in (URL, address)
        and snapshot.media_type == spec["media_type"], "ensembl_snapshot_request_conflict")
    _require(transport.get("effective_url", address) == address, "ensembl_snapshot_effective_url_conflict")
    policy = transport.get("request_policy")
    timeout = policy.get("timeout_seconds") if type(policy) is dict else None
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    _require(type(policy) is dict and policy.get("automatic_redirects") is False and valid_timeout,
        "ensembl_snapshot_transport_policy_conflict")
    _require(len(snapshot.content) <= arguments["max_bytes"], "ensembl_snapshot_byte_limit_conflict")
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(), "ensembl_artifact_identity_conflict")
    def observed(key, kind, minimum=None, maximum=None):
        value = transport.get(key)
        return value if type(value) is kind and (minimum is None or value >= minimum) and (
            maximum is None or value <= maximum) else None
    native_headers = transport.get("headers")
    def header(name):
        value = native_headers.get(name) if type(native_headers) is dict else None
        return value if type(value) is str else None
    return {"request_url": address, "request_method": spec["method"],
        "request_body_sha256": hashlib.sha256(expected_body).hexdigest() if expected_body is not None else None,
        "media_type": snapshot.media_type, "http_status": observed("status", int, 100, 599),
        "content_type": header("content-type"), "body_complete": observed("body_complete", bool),
        "retained_bytes": len(snapshot.content), "reported_retained_bytes": observed("retained_body_bytes", int, 0),
        "observed_body_bytes": observed("observed_body_bytes", int, 0),
        "declared_body_bytes": observed("declared_body_bytes", int, 0),
        "response_byte_limit": observed("response_byte_limit", int, 0),
        "capture_failure": observed("body_capture_failure", str), "retry_after": header("retry-after"),
        "timeout_seconds": timeout, "automatic_redirects": False}


def _response_issues(response, arguments):
    issues = []
    for key in ("http_status", "body_complete", "reported_retained_bytes", "response_byte_limit"):
        if response[key] is None:
            issues.append(_issue("transport_metadata_unavailable", "/response/" + key))
    status = response["http_status"]
    if status is not None and not 200 <= status < 300:
        issues.append(_issue("http_not_success", "/response/http_status"))
        if 300 <= status < 400:
            issues.append(_issue("http_redirect", "/response/http_status"))
    if response["body_complete"] is False:
        issues.append(_issue("response_incomplete", "/response/body_complete"))
    if response["capture_failure"] is not None:
        issues.append(_issue("response_capture_failure", "/response/capture_failure"))
    limit, retained = arguments["max_bytes"], response["retained_bytes"]
    if response["capture_failure"] == "provider_response_byte_limit" or (
            response["observed_body_bytes"] is not None and response["observed_body_bytes"] > limit):
        issues.append(_issue("response_byte_limit_exceeded", "/response/observed_body_bytes"))
    if (response["reported_retained_bytes"] not in (None, retained)
            or response["response_byte_limit"] not in (None, limit)
            or response["observed_body_bytes"] is not None and response["observed_body_bytes"] < retained
            or response["body_complete"] is True and any(response[key] not in (None, retained)
                for key in ("observed_body_bytes", "declared_body_bytes"))):
        issues.append(_issue("transport_count_conflict", "/response"))
    content_type = response["content_type"]
    if content_type is not None:
        allowed = {"application/xml", "text/xml", "text/plain"} if arguments["operation"] in {
            "registry", "configuration"} else {"text/plain", "text/tab-separated-values"}
        if content_type.split(";", 1)[0].strip().lower() not in allowed:
            issues.append(_issue("content_type_mismatch", "/response/content_type"))
    return issues


def _qualify(text, state, error, xml, lines, arguments, columns):
    issues, invalid = [], False
    native_error = text is not None and _native_error(text)
    if native_error:
        issues.append(_issue("native_error_response", "/native_text"))
    if error is not None:
        issues.append(_issue(error, "/raw_artifact_ref"))
        return "error" if native_error else "unavailable", "invalid", "not_applicable", None, issues
    if text is None or not text.strip():
        issues.append(_issue("native_response_empty", "/native_text"))
        invalid = True
    tag = arguments["operation"]
    completion, rows = "not_applicable", None
    if state == "xml":
        root = "MartRegistry" if tag == "registry" else "DatasetConfig"
        if _tag(xml) != root:
            issues.append(_issue("native_xml_root_invalid", "/xml_document/tag"))
            invalid = True
        elif tag == "configuration":
            attrs = _attributes(xml)
            if attrs.get("internalName") != arguments["dataset"]:
                issues.append(_issue("native_configuration_identity_conflict", "/xml_document/attributes"))
            if "default" not in attrs.get("interfaces", "").split(","):
                issues.append(_issue("native_configuration_interface_conflict", "/xml_document/attributes"))
    else:
        header_seen, stamps, after_stamp, rows = False, [], False, 0
        width = len(columns) if tag == "gene_homologies" else 9
        for index, line in enumerate(lines):
            location, value = "/tsv_lines/" + str(index), line["text"]
            if value == "" or tag == "datasets" and not value.strip():
                line["role"] = "blank"
                continue
            if value.startswith(("Query ERROR:", "ERROR:", "BioMart::Exception")):
                line["role"] = "error"
                continue
            if tag == "gene_homologies" and value == "[success]":
                line["role"] = "completion"
                stamps.append(index)
                after_stamp = True
                continue
            if after_stamp:
                issues.append(_issue("native_data_after_completion", location))
            if tag == "gene_homologies" and not header_seen:
                line["role"] = "header"
                header_seen = True
                known = [(index, column["native_display_name"]) for index, column in enumerate(columns)
                    if column["native_display_name"] is not None]
                if len(line["cells"]) != width:
                    line["role"] = "unclassified"
                else:
                    for column_index, column in enumerate(columns):
                        if column["native_display_name"] is None:
                            issues.append(_issue("native_header_context_missing",
                                location + "/cells/" + str(column_index)))
                    if not known:
                        line["role"] = "unclassified"
                    elif any(line["cells"][index] != name for index, name in known):
                        line["role"] = "unclassified"
                        issues.append(_issue("native_header_context_conflict", location))
            else:
                line["role"] = "row"
                rows += 1
            if len(line["cells"]) != width:
                issues.append(_issue("native_column_arity_conflict", location + "/cells"))
                continue
            if tag == "gene_homologies" and line["role"] == "row":
                issues.extend(_row_issues(line["cells"], arguments, location))
        if tag == "gene_homologies":
            if not header_seen:
                issues.append(_issue("native_header_missing", "/tsv_lines"))
                invalid = True
            completion = "reported_complete" if len(stamps) == 1 and not any(
                row["code"] == "native_data_after_completion" for row in issues) and not native_error else "missing"
            if not stamps:
                issues.append(_issue("native_completion_missing", "/tsv_lines"))
            elif completion != "reported_complete":
                completion = "conflicting"
                issues.append(_issue("native_completion_conflict", "/tsv_lines"))
    substantive = [row for row in issues if row["code"] != "native_error_response"]
    return ("error" if native_error else "invalid" if invalid else "data",
        "invalid" if invalid else "partial" if substantive else "complete", completion, rows, issues)


def _row_issues(cells, arguments, location):
    issues = []
    def issue(code, index):
        issues.append(_issue(code, location + "/cells/" + str(index)))
    if not cells[0]:
        issue("native_source_id_missing", 0)
    elif cells[0] not in arguments["gene_ids"]:
        issue("native_source_id_not_requested", 0)
    for gene, start, end in ((0, 2, 3), (5, 7, 8)):
        if cells[gene]:
            valid = []
            for index in (start, end):
                valid.append(re.fullmatch(r"[1-9][0-9]*", cells[index], re.ASCII) is not None)
                if not valid[-1]:
                    issue("native_coordinate_invalid", index)
            # Native gene coordinates are positive decimal strings. Compare
            # their exact magnitude without Python's integer digit limit.
            if all(valid) and (len(cells[start]) > len(cells[end]) or
                    len(cells[start]) == len(cells[end]) and cells[start] > cells[end]):
                issue("native_coordinate_invalid", end)
    if cells[0] and cells[4] not in {"-1", "1"}:
        issue("native_strand_invalid", 4)
    if not cells[5] and any(cells[index] for index in range(6, len(cells))):
        issue("native_homology_association_incomplete", 5)
    if cells[5] and not cells[9]:
        issue("native_homology_association_incomplete", 9)
    return issues


def _registry_marts(xml):
    result = []
    def visit(node, schema="default"):
        attrs = _attributes(node)
        if _tag(node) == "virtualSchema":
            schema = attrs.get("name")
        if _tag(node) in {"MartURLLocation", "MartDBLocation"}:
            result.append((attrs.get("serverVirtualSchema", schema), attrs.get("name"), attrs))
        for child in node["children"]:
            visit(child, schema)
    visit(xml)
    return result


def _one(values, code):
    _require(len(values) == 1, code)
    return values[0]


def _configuration_attribute(xml, name):
    return _one([node for node in _walk(xml) if _tag(node) == "AttributeDescription"
        and _attributes(node).get("internalName") == name], "ensembl_attribute_not_uniquely_advertised")


def validate_ensembl_discovery(arguments, *, evidence=None):
    """Bind only selected retained lineage; host authenticates Source admission.

    ``evidence`` maps Source IDs to ``{snapshot, artifact_ref}``.  No advertised
    URL is opened.  Each prior snapshot must have its own exact selected native
    request, no redirects, original byte hash, complete capture and valid shape.
    """
    arguments = validate_ensembl_arguments(arguments)
    _require(evidence is None or type(evidence) is dict, "ensembl_discovery_evidence_invalid")
    evidence = {} if evidence is None else evidence
    cache, refs = {}, []
    def retained(source_ref, operation):
        _require(type(source_ref) is str and _SOURCE_RE.fullmatch(source_ref) is not None,
            "ensembl_discovery_source_invalid")
        if source_ref not in cache:
            item = evidence.get(source_ref)
            _require(type(item) is dict and set(item) == {"snapshot", "artifact_ref"},
                "ensembl_discovery_source_unavailable")
            snapshot = item["snapshot"]
            _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.request) is dict,
                "ensembl_discovery_snapshot_invalid")
            selected = validate_ensembl_arguments(snapshot.request)
            _require(selected["operation"] == operation, "ensembl_discovery_operation_conflict")
            value = ensembl_result(snapshot, arguments=selected, source_ref=source_ref,
                artifact_ref=item["artifact_ref"], evidence=evidence)
            _require(value["native_response_state"] == "data" and value["representation_state"] == "complete"
                and not value["issues"] and value["response"]["body_complete"] is True,
                "ensembl_discovery_response_not_complete")
            for row in value["discovery_evidence"]:
                if row not in refs:
                    refs.append(row)
            own = {"source_ref": source_ref, "raw_artifact_ref": item["artifact_ref"], "operation": operation}
            if own not in refs:
                refs.append(own)
            cache[source_ref] = value
        value = cache[source_ref]
        _require(value["requested"]["operation"] == operation, "ensembl_discovery_operation_conflict")
        return value
    tag = arguments["operation"]
    contexts, columns = [], []
    if tag == "datasets":
        value = retained(arguments["registry_source_ref"], "registry")
        _one([attrs for schema, mart, attrs in _registry_marts(value["xml_document"])
            if schema == arguments["virtual_schema"] and mart == arguments["mart"]],
            "ensembl_mart_not_uniquely_advertised")
    elif tag == "configuration":
        value = retained(arguments["datasets_source_ref"], "datasets")
        _require(all(value["requested"][key] == arguments[key] for key in _CONTEXT),
            "ensembl_discovery_context_conflict")
        row = _one([line["cells"] for line in value["tsv_lines"] if line["role"] == "row"
            and len(line["cells"]) == 9 and line["cells"][1] == arguments["dataset"]],
            "ensembl_dataset_not_uniquely_advertised")
        _require("default" in row[7].split(","), "ensembl_dataset_interface_not_advertised")
    elif tag == "gene_homologies":
        configs = []
        for side in ("source", "target"):
            source_ref = arguments[side + "_configuration_ref"]
            config = retained(source_ref, "configuration")
            _require(all(config["requested"][key] == arguments[key] for key in _CONTEXT)
                and config["requested"]["dataset"] == arguments[side + "_dataset"],
                "ensembl_discovery_context_conflict")
            dataset_ref = config["requested"]["datasets_source_ref"]
            dataset = retained(dataset_ref, "datasets")
            row = _one([line["cells"] for line in dataset["tsv_lines"] if line["role"] == "row"
                and line["cells"][1] == arguments[side + "_dataset"]],
                "ensembl_dataset_not_uniquely_advertised")
            contexts.append({"dataset": row[1], "display_name": row[2], "dataset_version": row[4],
                "version_meaning": "native_assembly_or_genebuild_not_ensembl_release",
                "configuration_source_ref": source_ref, "datasets_source_ref": dataset_ref})
            configs.append(config)
        xml = configs[0]["xml_document"]
        _one([node for node in _walk(xml) if _tag(node) in {"FilterDescription", "Option"}
            and _attributes(node).get("internalName") == "ensembl_gene_id"],
            "ensembl_filter_not_uniquely_advertised")
        for column in _column_specs(arguments):
            attrs = _attributes(_configuration_attribute(xml, column["attribute"]))
            display_name = attrs.get("displayName")
            # A native pointer can explain the header label without replacing
            # the caller's requested alias, dataset, interface or attribute.
            if (display_name is None and attrs.get("pointerDataset") == arguments["source_dataset"]
                    and attrs.get("pointerInterface") == "default" and attrs.get("pointerAttribute")):
                display_name = _attributes(_configuration_attribute(xml, attrs["pointerAttribute"])).get("displayName")
            columns.append({**column, "native_display_name": display_name})
    return {"discovery_evidence": refs, "dataset_contexts": contexts, "columns": columns}


def _native_payload(raw, arguments, discovery):
    text, state, error, xml, lines = _parse(raw, arguments)
    native, representation, completion, rows, issues = _qualify(text, state, error, xml, lines,
        arguments, discovery["columns"])
    return {"native_text": text, "parse_state": state, "decode_error": error,
        "xml_document": xml, "tsv_lines": lines, "native_response_state": native,
        "representation_state": representation, "native_completion": completion,
        **discovery, "requested_id_count": len(arguments["gene_ids"]) if "gene_ids" in arguments else None,
        "retained_row_count": rows, "matching_population_count": None,
        "population_coverage": "selected_response_only", "native_pagination": "not_exposed",
        "coordinate_convention": "native_one_based_inclusive" if arguments["operation"] == "gene_homologies" else None}, issues


def _ensembl_content(snapshot, *, arguments, artifact_ref, evidence=None):
    response = _snapshot_response(snapshot, arguments, artifact_ref)
    discovery = validate_ensembl_discovery(arguments, evidence=evidence)
    payload, issues = _native_payload(snapshot.content, arguments, discovery)
    return {"operation": TOOL, "service": "ensembl", "resource": RESOURCE,
        "raw_artifact_ref": artifact_ref, "requested": arguments,
        "response": response, **payload,
        "issues": _unique_issues(_response_issues(response, arguments) + issues)}


def ensembl_result(snapshot, *, arguments, source_ref, artifact_ref, evidence=None):
    arguments = validate_ensembl_arguments(arguments)
    _require(type(source_ref) is str and _SOURCE_RE.fullmatch(source_ref) is not None,
        "ensembl_source_reference_invalid")
    return _validated({"version": VERSION, "source_ref": source_ref,
        **_ensembl_content(snapshot, arguments=arguments, artifact_ref=artifact_ref,
            evidence=evidence)}, _RESULT)


def validate_ensembl_result(value, *, evidence=None):
    value = _validated(value, _RESULT)
    _require(_SOURCE_RE.fullmatch(value["source_ref"]) is not None, "ensembl_source_reference_invalid")
    return _validate_ensembl_content(value, evidence=evidence)


def _validate_ensembl_content(value, *, evidence=None, retained_discovery=False):
    sources = [row["source_ref"] for row in value["discovery_evidence"]]
    for context in value["dataset_contexts"]:
        sources.extend(context[key] for key in ("configuration_source_ref", "datasets_source_ref"))
    artifacts = [value["raw_artifact_ref"], *(row["raw_artifact_ref"] for row in value["discovery_evidence"])]
    _require(all(_SOURCE_RE.fullmatch(reference) is not None for reference in sources),
        "ensembl_source_reference_invalid")
    _require(all(_ARTIFACT_RE.fullmatch(reference) is not None for reference in artifacts),
        "ensembl_artifact_reference_invalid")
    arguments = validate_ensembl_arguments(value["requested"])
    response, spec = value["response"], ensembl_request_spec(arguments)
    try:
        valid_timeout = type(response["timeout_seconds"]) in (int, float) and math.isfinite(
            response["timeout_seconds"]) and response["timeout_seconds"] > 0
    except OverflowError:
        valid_timeout = False
    _require(valid_timeout, "ensembl_snapshot_transport_policy_conflict")
    expected_body = spec["body"]
    _require(response["request_url"] == _address(spec) and response["request_method"] == spec["method"]
        and response["media_type"] == spec["media_type"]
        and response["request_body_sha256"] == (hashlib.sha256(expected_body).hexdigest()
            if expected_body is not None else None), "ensembl_result_request_conflict")
    _require(response["retained_bytes"] <= arguments["max_bytes"], "ensembl_snapshot_byte_limit_conflict")
    discovery = (_retained_discovery(value) if retained_discovery else
        validate_ensembl_discovery(arguments, evidence=evidence))
    if value["native_text"] is None:
        _require(value["decode_error"] == "invalid_native_utf8", "ensembl_native_representation_conflict")
        payload, issues = _native_payload(b"\xff", arguments, discovery)
    else:
        raw = value["native_text"].encode("utf-8")
        _require(value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
            and len(raw) == response["retained_bytes"], "ensembl_artifact_identity_conflict")
        payload, issues = _native_payload(raw, arguments, discovery)
    _require(all(_same(value[key], expected) for key, expected in payload.items()),
        "ensembl_native_representation_conflict")
    _require(_same(value["issues"], _unique_issues(_response_issues(response, arguments) + issues)),
        "ensembl_native_qualification_conflict")
    return value


def _retained_discovery(value):
    """Check retained descriptor relationships, without inventing custody.

    Actual external discovery authentication remains in the host. No snapshot,
    Source identity or absent ancestor is reconstructed by this pure path.
    """
    arguments, rows = value["requested"], value["discovery_evidence"]
    contexts, columns = value["dataset_contexts"], value["columns"]
    by_ref = {row["source_ref"]: row for row in rows}
    _require(len(by_ref) == len(rows), "ensembl_retained_discovery_conflict")
    tag = arguments["operation"]
    if tag == "registry":
        _require(not rows and not contexts and not columns, "ensembl_retained_discovery_conflict")
    elif tag == "datasets":
        _require(len(rows) == 1 and rows[0]["source_ref"] == arguments["registry_source_ref"]
            and rows[0]["operation"] == "registry" and not contexts and not columns,
            "ensembl_retained_discovery_conflict")
    elif tag == "configuration":
        _require(len(rows) == 2 and [row["operation"] for row in rows] == ["registry", "datasets"]
            and rows[1]["source_ref"] == arguments["datasets_source_ref"] and not contexts and not columns,
            "ensembl_retained_discovery_conflict")
    else:
        expected = _column_specs(arguments)
        _require(len(columns) == len(expected) and all(_same(
            {key: column[key] for key in ("role", "attribute", "denominator")}, wanted)
            for column, wanted in zip(columns, expected)), "ensembl_retained_discovery_conflict")
        _require(len(contexts) == 2 and all(context["dataset"] == arguments[side + "_dataset"]
            and context["configuration_source_ref"] == arguments[side + "_configuration_ref"]
            for side, context in zip(("source", "target"), contexts)), "ensembl_retained_discovery_conflict")
        wanted_configs = {arguments[side + "_configuration_ref"] for side in ("source", "target")}
        wanted_datasets = {context["datasets_source_ref"] for context in contexts}
        _require({row["source_ref"] for row in rows if row["operation"] == "configuration"} == wanted_configs
            and {row["source_ref"] for row in rows if row["operation"] == "datasets"} == wanted_datasets
            and 1 <= sum(row["operation"] == "registry" for row in rows) <= len(wanted_datasets),
            "ensembl_retained_discovery_conflict")
        positions = {row["source_ref"]: index for index, row in enumerate(rows)}
        _require(all(positions[context["datasets_source_ref"]] < positions[context["configuration_source_ref"]]
            for context in contexts) and positions[arguments["source_configuration_ref"]] <
            positions[arguments["target_configuration_ref"]] and all(any(
                earlier["operation"] == "registry" for earlier in rows[:index])
                for index, row in enumerate(rows) if row["operation"] == "datasets"),
            "ensembl_retained_discovery_conflict")
    return {"discovery_evidence": rows, "dataset_contexts": contexts, "columns": columns}


def ensembl_value_schema():
    return deepcopy(_VALUE)


def ensembl_value(snapshot, *, arguments, artifact_ref, evidence=None):
    arguments = validate_ensembl_arguments(arguments)
    content = _ensembl_content(snapshot, arguments=arguments, artifact_ref=artifact_ref, evidence=evidence)
    return validate_ensembl_value({"version": VALUE_VERSION, **content,
        "observed_transfer": {key: deepcopy(snapshot.transport.get(key)) for key in
            ("declared_body_bytes", "body_capture_failure")}}, evidence=evidence)


def validate_ensembl_value(value, *, evidence=None):
    value = _validate_ensembl_content(_validated(value, _VALUE), evidence=evidence,
        retained_discovery=evidence is None)
    for raw_key, response_key, kind in (("declared_body_bytes", "declared_body_bytes", int),
            ("body_capture_failure", "capture_failure", str)):
        raw = value["observed_transfer"][raw_key]
        expected = raw if type(raw) is kind and (kind is not int or raw >= 0) else None
        _require(_same(value["response"][response_key], expected), "ensembl_transfer_metadata_conflict")
    return value


def ensembl_result_from_value(value, *, source_ref, evidence=None):
    value = validate_ensembl_value(value, evidence=evidence)
    _require(type(source_ref) is str and _SOURCE_RE.fullmatch(source_ref) is not None,
        "ensembl_source_reference_invalid")
    value.pop("observed_transfer")
    value.update(version=VERSION, source_ref=source_ref)
    return _validated(value, _RESULT)


def ensembl_receipt_schema():
    return acquisition_receipt_schema(failure_codes=ENSEMBL_FAILURE_CODES)


def validate_ensembl_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=ENSEMBL_FAILURE_CODES,
        invalid_code="ensembl_receipt_invalid")


def failed_ensembl_receipt(code, *, source_ref=None):
    return validate_ensembl_receipt(dict(acquired=False, source_ref=source_ref,
        data_ref=None, failure_code=code))


def _receipt_transfer_failure(value):
    response, arguments = value["response"], value["requested"]
    status = response["http_status"]
    if status is None:
        return "transport_metadata_unavailable"
    if not 200 <= status < 300:
        return "http_redirect" if 300 <= status < 400 else "http_not_success"
    if response["body_complete"] is not True:
        return "response_incomplete"
    declared, failure = (value["observed_transfer"][key] for key in
        ("declared_body_bytes", "body_capture_failure"))
    if (declared is not None and (type(declared) is not int or declared < 0)
            or failure is not None and type(failure) is not str):
        return "transport_metadata_unavailable"
    if any(response[key] is None for key in (
            "reported_retained_bytes", "observed_body_bytes", "response_byte_limit")):
        return "transport_metadata_unavailable"
    if response["capture_failure"] is not None:
        return ("response_byte_limit_exceeded" if response["capture_failure"] == "provider_response_byte_limit"
            else "response_capture_failure")
    retained = response["retained_bytes"]
    if (response["reported_retained_bytes"] != retained or response["observed_body_bytes"] != retained
            or response["declared_body_bytes"] not in (None, retained)
            or response["response_byte_limit"] != arguments["max_bytes"]):
        return "transport_count_conflict"
    return None


def ensembl_receipt(value, *, source_ref):
    value = validate_ensembl_value(value)
    failure = _receipt_transfer_failure(value)
    if failure is None:
        failure = next((row["code"] for row in value["issues"]
            if row["code"] != "content_type_mismatch"), None)
    if failure is not None:
        return failed_ensembl_receipt("ensembl_" + failure, source_ref=source_ref)
    return validate_ensembl_receipt(dict(acquired=True, source_ref=source_ref,
        data_ref=value["raw_artifact_ref"], failure_code=None))


def _configuration_model_view(document):
    root = _attributes(document)
    attributes, filters = {}, []
    for node in _walk(document):
        fields = _attributes(node)
        name = fields.get("internalName")
        if _tag(node) == "AttributeDescription" and type(name) is str:
            attributes.setdefault(name, []).append(fields)
        elif _tag(node) in {"FilterDescription", "Option"} and name == "ensembl_gene_id":
            filters.append(fields)
    def state(count):
        return "unique" if count == 1 else "missing" if count == 0 else "ambiguous"
    def label(name):
        found = attributes.get(name, [])
        if len(found) != 1:
            return None
        fields = found[0]
        value = fields.get("displayName")
        if (value is None and fields.get("pointerDataset") == root.get("internalName")
                and fields.get("pointerInterface") == "default"):
            target = attributes.get(fields.get("pointerAttribute"), [])
            if len(target) == 1:
                value = target[0].get("displayName")
        return value
    def group(names):
        missing = [name for name in names if not attributes.get(name)]
        ambiguous = [name for name in names if len(attributes.get(name, [])) > 1]
        unknown_headers = [name for name in names if len(attributes.get(name, [])) == 1 and label(name) is None]
        return {"advertisement": "all_unique" if not missing and not ambiguous else "missing_or_ambiguous",
            "missing_attributes": missing, "ambiguous_attributes": ambiguous,
            "unknown_header_labels": unknown_headers}
    source_fields = ("ensembl_gene_id", "chromosome_name", "start_position", "end_position", "strand")
    suffixes = ("ensembl_gene", "chromosome", "chrom_start", "chrom_end", "orthology_type",
        "perc_id", "perc_id_r1", "orthology_confidence")
    namespaces = []
    for name in attributes:
        for suffix in suffixes:
            ending = "_homolog_" + suffix
            if name.endswith(ending) and len(name) > len(ending):
                namespace = name[:-len(suffix)]
                if namespace not in namespaces:
                    namespaces.append(namespace)
                break
    return {"reported_dataset": root.get("internalName"), "display_name": root.get("displayName"),
        "interfaces": root.get("interfaces"), "native_dataset_version": root.get("version"),
        "native_version_meaning": "native_assembly_or_genebuild_not_ensembl_release",
        "native_software_version": root.get("softwareVersion"),
        "gene_id_filter": {"name": "ensembl_gene_id", "advertisement": state(len(filters))},
        "source_attribute_styles": [{"style": style, "attributes": [prefix + name for name in source_fields],
            **group([prefix + name for name in source_fields])}
            for style, prefix in (("base", ""), ("homologs", "homologs_"))],
        # These are native attribute namespaces, not inferred species or
        # substituted datasets. The separate dataset inventory owns identities.
        "native_homology_namespaces": [{"attribute_namespace": namespace,
            "gene_context": group([namespace + suffix for suffix in suffixes[:5]]),
            "identity_percentages": group([namespace + suffix for suffix in suffixes[5:7]]),
            "native_confidence": group([namespace + suffixes[7]])} for namespace in namespaces],
        "availability_scope": "finite_public_ensembl_request_operands_only"}


def ensembl_outcome_view(outcome):
    """Detach a finite model view without changing retained outcomes or facts.

    Every scientific TSV cell remains ordered and lexical. Discovery XML is
    represented by identities and availability for this binding's finite
    operands; its full unknown native content remains in the original Source
    and controlled DTO. This projection confers no receipt or File authority.
    """
    if type(outcome) is not dict or type(outcome.get("result")) is not dict:
        return None
    supplied = outcome["result"]
    if (supplied.get("version") != VERSION or supplied.get("operation") != TOOL
            or supplied.get("service") != "ensembl" or supplied.get("resource") != RESOURCE):
        return None
    try:
        value = _validated(supplied, _RESULT)
        arguments = validate_ensembl_arguments(value["requested"])
        sources = [value["source_ref"], *(row["source_ref"] for row in value["discovery_evidence"])]
        for context in value["dataset_contexts"]:
            sources.extend(context[key] for key in ("configuration_source_ref", "datasets_source_ref"))
        artifacts = [value["raw_artifact_ref"], *(row["raw_artifact_ref"] for row in value["discovery_evidence"])]
        _require(all(_SOURCE_RE.fullmatch(reference) is not None for reference in sources)
            and all(_ARTIFACT_RE.fullmatch(reference) is not None for reference in artifacts))
        text = value["native_text"]
        if text is not None:
            raw = text.encode("utf-8")
            _require(value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
                and len(raw) == value["response"]["retained_bytes"])
            parsed_text, state, error, document, lines = _parse(raw, arguments)
            _require(state == value["parse_state"] and error == value["decode_error"]
                and _same(document, value["xml_document"]))
        else:
            _require(value["parse_state"] == "decode_failed" and value["decode_error"] == "invalid_native_utf8"
                and value["xml_document"] is None and value["tsv_lines"] == [])
            parsed_text, state, error, document, lines = None, "decode_failed", "invalid_native_utf8", None, []
        native, representation, completion, rows, issues = _qualify(parsed_text, state, error, document,
            lines, arguments, value["columns"])
        _require(_same(lines, value["tsv_lines"]) and value["native_response_state"] == native
            and value["representation_state"] == representation and value["native_completion"] == completion
            and value["retained_row_count"] == rows and _same(value["issues"],
                _unique_issues(_response_issues(value["response"], arguments) + issues)))
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        return None
    view = {key: child for key, child in value.items() if key not in {"native_text", "xml_document", "tsv_lines"}}
    view["version"] = MODEL_VIEW_VERSION
    view["native_body"] = {"source_ref": value["source_ref"], "representation": "original",
        "retained_body_available": True,
        "xml_view_scope": "finite_binding_identities_and_availability" if value["parse_state"] == "xml" else None}
    tag, document = arguments["operation"], value["xml_document"]
    if value["parse_state"] == "xml":
        view["native_root_tag"] = _tag(document)
        if tag == "registry" and _tag(document) == "MartRegistry":
            view["registry_marts"] = [{"virtual_schema": schema, "mart": mart,
                "display_name": fields.get("displayName"), "visible": fields.get("visible")}
                for schema, mart, fields in _registry_marts(document)]
        elif tag == "configuration" and _tag(document) == "DatasetConfig":
            view["configuration"] = _configuration_model_view(document)
    elif value["parse_state"] == "tsv":
        if tag == "datasets":
            view["native_columns"] = ["dataset_type", "dataset", "display_name", "visible", "native_dataset_version",
                "initial_batch_size", "max_batch_size", "interfaces", "modified"]
            view["native_batch_size_meaning"] = "execution_batch_controls_not_output_pagination_or_matching_population"
            view["native_dataset_version_meaning"] = "native_assembly_or_genebuild_not_ensembl_release"
        # cells plus ending reversibly represent every original TSV line,
        # including blanks, malformed rows, errors and completion stamps once.
        view["native_lines"] = [{key: row[key] for key in ("line_number", "role", "cells", "ending")}
            for row in value["tsv_lines"]]
    elif text is not None:
        view["native_diagnostic_text"] = text
    return {**deepcopy(outcome), "result": view,
        "automatic_preview": {"kind": MODEL_VIEW_VERSION, "complete_result_preserved": True}}


__all__ = ["TOOL", "VERSION", "MODEL_VIEW_VERSION", "VALUE_VERSION", "RESOURCE", "URL", "MAX_RESPONSE_BYTES", "MAX_GENE_IDS", "OPERATIONS",
    "ARGUMENTS_SCHEMA", "ISSUE_CODES", "validate_ensembl_arguments", "ensembl_request_spec", "ensembl_discovery_refs",
    "validate_ensembl_discovery", "ensembl_result_schema", "ensembl_result", "validate_ensembl_result",
    "ensembl_outcome_view", "ensembl_value", "validate_ensembl_value", "ensembl_value_schema",
    "ensembl_result_from_value", "ensembl_receipt", "validate_ensembl_receipt",
    "failed_ensembl_receipt", "ensembl_receipt_schema", "ENSEMBL_FAILURE_CODES"]
