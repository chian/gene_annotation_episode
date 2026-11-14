"""Pure contracts for one explicitly advertised SRA file acquisition.

The supplied XML File is evidence, not a verified NCBI Source. These functions
validate its selected native occurrence and one captured transfer; they grant
no File, authenticate no episode and never decode an SRA/FASTQ archive.
"""
from copy import deepcopy
import hashlib
import math
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator, ValidationError, validators

from .acquisition import SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from .ncbi_entrez_acquisition import _xml
from .native_file_capture import NativeFileCaptureError, _identity


TOOL = "public.ncbi.sra.file"
SERVICE = "ncbi_sra"
MAX_BYTES = 1024 ** 3
MAX_ADVERTISEMENT_BYTES = 8 * 1024 ** 2
ADVERTISEMENT_FORMAT = "sra_experiment_package_xml"
ALLOWED_DOWNLOAD_HOSTS = (
    "sra-pub-run-odp.s3.amazonaws.com", "sra-downloadb.be-md.ncbi.nlm.nih.gov",
)
SRA_FILE_FAILURE_CODES = (
    "invalid_tool_input", "data_acquisition_failed", "data_acquisition_publication_incomplete",
    "provider_connection_failed", "provider_request_timeout", "provider_response_byte_limit",
    "provider_body_capture_failed", "sra_file_arguments_invalid", "sra_file_advertisement_identity_conflict",
    "sra_file_advertisement_format_unavailable", "sra_file_selection_unavailable",
    "sra_file_selection_conflict", "sra_file_https_resource_unsupported", "sra_file_native_claim_invalid",
    "sra_file_request_conflict", "sra_file_http_status_unknown", "sra_file_http_not_success",
    "sra_file_unrequested_range", "sra_file_capture_invalid", "sra_file_capture_incomplete",
    "sra_file_content_encoding_unsupported", "sra_file_native_size_conflict", "sra_file_native_md5_conflict",
    "sra_file_input_not_received", "sra_file_input_identity_conflict", "sra_file_input_bytes_unavailable",
    "sra_file_saved_outcome_conflict", "sra_file_value_invalid",
)
_SHA = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
_MD5 = re.compile(r"[a-fA-F0-9]{32}\Z", re.ASCII)


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _array(item):
    return dict(type="array", items=item)


def _nullable(item):
    return dict(anyOf=[item, dict(type="null")])


_TEXT = dict(type="string")
_LABEL = dict(type="string", minLength=1, pattern=r"^[^\x00-\x1f\x7f]+$")
_INDEX = dict(type="integer", minimum=0)
_FILE = _object(dict(artifact_ref=dict(type="string", pattern=r"^artifact_[a-f0-9]{64}$",
    format="reference", **{"x-reference-namespace": "artifact"}),
    sha256=dict(type="string", pattern=r"^[a-f0-9]{64}$"),
    size_bytes=dict(type="integer", minimum=0, maximum=MAX_ADVERTISEMENT_BYTES),
    format=dict(const=ADVERTISEMENT_FORMAT)))
_URL_SELECTION = dict(oneOf=[_object(dict(kind=dict(const="file_url"))),
    _object(dict(kind=dict(const="alternative_url"), alternative_ordinal_0based=_INDEX))])
_ARGUMENTS = _object(dict(advertisement_file=_FILE,
    experiment_package_ordinal_0based=_INDEX, run_ordinal_0based=_INDEX, file_ordinal_0based=_INDEX,
    url_selection=_URL_SELECTION, run_accession=_LABEL,
    semantic_name=dict(enum=["fastq", "SRA Normalized", "SRA Lite"]),
    supertype=dict(enum=["Original", "Primary ETL"]), file_name=_LABEL, url=_LABEL,
    max_bytes=dict(type="integer", minimum=1, maximum=MAX_BYTES)))
ARGUMENTS_SCHEMA = deepcopy(_ARGUMENTS)
_ATTRIBUTE = _object(dict(name=_TEXT, value=_TEXT))
_ATTRIBUTES = _array(_ATTRIBUTE)
_LOCATION = _object(dict(experiment_package_ordinal_0based=_INDEX, run_ordinal_0based=_INDEX,
    file_ordinal_0based=_INDEX, url_selection=_URL_SELECTION))
_CLAIMS = _object(dict(size_token=_nullable(_TEXT), size_bytes=_nullable(_INDEX), md5_token=_nullable(_TEXT)))
_SELECTION = _object(dict(version=dict(const="ncbi_sra_file_selection_v1"), advertisement_file=_FILE,
    locator_kind=dict(const="direct_element_ordinals"), location=_LOCATION,
    run_attributes=_ATTRIBUTES, file_attributes=_ATTRIBUTES,
    alternative_attributes=_nullable(_ATTRIBUTES), selected_url=_TEXT, claims=_CLAIMS))
_JSON = dict(oneOf=[dict(type="null"), dict(type="boolean"), dict(type="number"), dict(type="string"),
    dict(type="array", items={"$ref": "#/$defs/Json"}),
    dict(type="object", additionalProperties={"$ref": "#/$defs/Json"})])
_OBSERVED = _object(dict(service=_TEXT, url=_TEXT, request={"$ref": "#/$defs/Json"},
    media_type=_TEXT, transport={"$ref": "#/$defs/Json"}))
_RAW_FILE = _object(dict(artifact_ref=dict(type="string", pattern=r"^artifact_[a-f0-9]{64}$"),
    sha256=dict(type="string", pattern=r"^[a-f0-9]{64}$"), size_bytes=_INDEX,
    md5=dict(type="string", pattern=r"^[a-f0-9]{32}$")))
_CHECKS = _object(dict(request=dict(enum=["matched", "conflicting"]),
    body_capture=dict(enum=["complete", "incomplete", "unknown"]),
    native_size=dict(enum=["absent", "not_verified", "verified", "conflicting"]),
    native_md5=dict(enum=["absent", "not_verified", "verified", "conflicting"]),
    archive_identity=dict(const="not_parsed")))
_VALUE = {**_object(dict(version=dict(const="ncbi_sra_file_value_v1"), requested=_ARGUMENTS,
    selection=_SELECTION, observed=_OBSERVED, raw_file=_RAW_FILE, checks=_CHECKS,
    failure_code=dict(enum=[None, *SRA_FILE_FAILURE_CODES]))), "$defs": dict(Json=_JSON)}
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _, value: type(value) is int)
    .redefine("number", lambda _, value: type(value) is int or type(value) is float and math.isfinite(value)))


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _plain(value):
    if type(value) is dict:
        _require(all(type(key) is str for key in value), "sra_file_value_invalid")
        for child in value.values():
            _plain(child)
    elif type(value) is list:
        for child in value:
            _plain(child)
    elif type(value) is float:
        _require(math.isfinite(value), "sra_file_value_invalid")
    else:
        _require(type(value) in (str, int, bool, type(None)), "sra_file_value_invalid")
    if type(value) is str:
        value.encode("utf-8")


def _validated(value, schema, code):
    try:
        _plain(value)
        _STRICT(schema).validate(value)
        return deepcopy(value)
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeError, ValidationError) as error:
        raise ValueError(code) from error


def _https_url(value):
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname in ALLOWED_DOWNLOAD_HOSTS
            and parts.username is None and parts.password is None and parts.port in (None, 443)
            and not parts.fragment and not parts.query and parts.path.startswith("/")
            and not any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value))
    except (ValueError, TypeError):
        valid = False
    _require(valid, "sra_file_https_resource_unsupported")


def sra_file_argument_schema():
    return deepcopy(_ARGUMENTS)


def validate_sra_file_arguments(arguments):
    value = _validated(arguments, _ARGUMENTS, "sra_file_arguments_invalid")
    try:
        _identity(value["advertisement_file"])
    except NativeFileCaptureError as error:
        raise ValueError("sra_file_arguments_invalid") from error
    _require(all(not (ord(character) < 32 or 127 <= ord(character) <= 159)
        for name in ("run_accession", "file_name") for character in value[name]), "sra_file_arguments_invalid")
    _require((value["semantic_name"] == "fastq") == (value["supertype"] == "Original"),
        "sra_file_arguments_invalid")
    _https_url(value["url"])
    return value


def sra_file_selection_schema():
    return deepcopy(_SELECTION)


def _attributes(rows):
    result = {}
    for row in rows:
        _require(row["name"] not in result, "sra_file_selection_conflict")
        result[row["name"]] = row["value"]
    return result


def _claims(attributes):
    token, md5 = attributes.get("size"), attributes.get("md5")
    _require(token is None or re.fullmatch(r"[0-9]+", token, re.ASCII) is not None,
        "sra_file_native_claim_invalid")
    _require(md5 is None or _MD5.fullmatch(md5) is not None, "sra_file_native_claim_invalid")
    try:
        size = None if token is None else int(token)
    except ValueError as error:
        raise ValueError("sra_file_native_claim_invalid") from error
    return dict(size_token=token, size_bytes=size, md5_token=md5)


def validate_sra_file_selection(selection, *, arguments):
    arguments = validate_sra_file_arguments(arguments)
    value = _validated(selection, _SELECTION, "sra_file_selection_conflict")
    _require(value["advertisement_file"] == arguments["advertisement_file"], "sra_file_selection_conflict")
    _require(value["location"] == {name: arguments[name] for name in _LOCATION["properties"]},
        "sra_file_selection_conflict")
    run, file = _attributes(value["run_attributes"]), _attributes(value["file_attributes"])
    _require(run.get("accession") == arguments["run_accession"] and all(file.get(native) == arguments[public]
        for native, public in (("filename", "file_name"), ("semantic_name", "semantic_name"),
            ("supertype", "supertype"))), "sra_file_selection_conflict")
    if arguments["url_selection"]["kind"] == "file_url":
        _require(value["alternative_attributes"] is None, "sra_file_selection_conflict")
        url = file.get("url")
    else:
        _require(value["alternative_attributes"] is not None, "sra_file_selection_conflict")
        url = _attributes(value["alternative_attributes"]).get("url")
    _require(url == value["selected_url"] == arguments["url"], "sra_file_selection_conflict")
    _require(value["claims"] == _claims(file), "sra_file_selection_conflict")
    return value


def _children(node, tag):
    return [child for child in node["children"] if child["tag"] == tag]


def _occurrence(rows, index):
    _require(index < len(rows), "sra_file_selection_unavailable")
    return rows[index]


def _single_child(node, tag):
    rows = _children(node, tag)
    _require(len(rows) == 1, "sra_file_selection_unavailable")
    return rows[0]


def resolve_sra_file_selection(raw_xml, *, arguments):
    """Select exact native XML occurrences; File shape/digest is not admission."""
    arguments = validate_sra_file_arguments(arguments)
    file = arguments["advertisement_file"]
    _require(type(raw_xml) is bytes and len(raw_xml) == file["size_bytes"]
        and hashlib.sha256(raw_xml).hexdigest() == file["sha256"], "sra_file_advertisement_identity_conflict")
    try:
        document = _xml(raw_xml.decode("utf-8"))
        _require(document["doctype"] is None and document["root"]["tag"] == "EXPERIMENT_PACKAGE_SET",
            "sra_file_advertisement_format_unavailable")
    except (UnicodeError, ET.ParseError, ValueError, RecursionError) as error:
        raise ValueError("sra_file_advertisement_format_unavailable") from error
    package = _occurrence(_children(document["root"], "EXPERIMENT_PACKAGE"),
        arguments["experiment_package_ordinal_0based"])
    run = _occurrence(_children(_single_child(package, "RUN_SET"), "RUN"), arguments["run_ordinal_0based"])
    native = _occurrence(_children(_single_child(run, "SRAFiles"), "SRAFile"), arguments["file_ordinal_0based"])
    alternative = None
    if arguments["url_selection"]["kind"] == "alternative_url":
        alternative = _occurrence(_children(native, "Alternatives"),
            arguments["url_selection"]["alternative_ordinal_0based"])["attributes"]
    attributes = _attributes(native["attributes"])
    url = attributes.get("url") if alternative is None else _attributes(alternative).get("url")
    _require(type(url) is str and bool(url), "sra_file_selection_unavailable")
    return validate_sra_file_selection(dict(version="ncbi_sra_file_selection_v1",
        advertisement_file=file, locator_kind="direct_element_ordinals",
        location={name: arguments[name] for name in _LOCATION["properties"]},
        run_attributes=run["attributes"], file_attributes=native["attributes"],
        alternative_attributes=alternative, selected_url=url, claims=_claims(attributes)), arguments=arguments)


def sra_file_request_spec(arguments, *, selection):
    arguments = validate_sra_file_arguments(arguments)
    validate_sra_file_selection(selection, arguments=arguments)
    return dict(service=SERVICE, url=arguments["url"], params={}, media_type="application/octet-stream",
        max_bytes=arguments["max_bytes"], follow_redirects=False)


def _headers(transport):
    values = []
    headers, items = transport.get("headers"), transport.get("header_items")
    if type(headers) is not dict or not all(type(k) is str and type(v) is str for k, v in headers.items()):
        return None
    values.extend(headers.items())
    if type(items) is not list or not all(type(row) is list and len(row) == 2
            and all(type(item) is str for item in row) for row in items):
        return None
    values.extend(items)
    return [(key.lower(), value) for key, value in values]


def _verification(arguments, selection, observed, file):
    claims = selection["claims"]
    checks = dict(request="conflicting", body_capture="unknown",
        native_size="absent" if claims["size_bytes"] is None else "not_verified",
        native_md5="absent" if claims["md5_token"] is None else "not_verified", archive_identity="not_parsed")
    spec = sra_file_request_spec(arguments, selection=selection)
    transport = observed["transport"]
    if type(transport) is not dict:
        return checks, "sra_file_request_conflict"
    request, policy = transport.get("request"), transport.get("request_policy")
    timeout = policy.get("timeout_seconds") if type(policy) is dict else None
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    if (observed["service"] != SERVICE or observed["url"] != spec["url"] or observed["request"] != {}
            or type(request) is not dict or set(request) != {"url", "method", "headers"}
            or request.get("url") != spec["url"] or request.get("method") != "GET"
            or type(policy) is not dict or set(policy) != {"timeout_seconds", "automatic_redirects"}
            or policy.get("automatic_redirects") is not False or not valid_timeout
            or type(transport.get("response_byte_limit")) is not int
            or transport["response_byte_limit"] != arguments["max_bytes"]
            or file["size_bytes"] > arguments["max_bytes"]):
        return checks, "sra_file_request_conflict"
    headers = request.get("headers")
    if (type(headers) is not dict or not all(type(k) is str and type(v) is str for k, v in headers.items())
            or [v for k, v in headers.items() if k.lower() == "accept"] != [spec["media_type"]]
            or any(k.lower() in {"range", "authorization", "cookie"} for k in headers)):
        return checks, "sra_file_request_conflict"
    hosts = [value for key, value in headers.items() if key.lower() == "host"]
    if hosts and (len(hosts) != 1 or hosts[0].casefold() != urlsplit(spec["url"]).netloc.casefold()):
        return checks, "sra_file_request_conflict"
    status = transport.get("status")
    effective = transport.get("effective_url")
    # The existing HTTPError capture has no effective_url field. Its exact
    # selected request and error entity remain usable failed-response evidence.
    if (effective is not None and effective != spec["url"]
            or effective is None and type(status) is int and 200 <= status < 300):
        return checks, "sra_file_request_conflict"
    checks["request"] = "matched"
    response_headers = _headers(transport)
    if response_headers is None:
        return checks, "sra_file_capture_invalid"
    complete = transport.get("body_complete")
    counts = [transport.get(key) for key in ("retained_body_bytes", "observed_body_bytes")]
    declared, capture_failure = transport.get("declared_body_bytes"), transport.get("body_capture_failure")
    if (type(complete) is not bool or any(type(count) is not int or count < 0 for count in counts)
            or declared is not None and (type(declared) is not int or declared < 0)
            or capture_failure is not None and (type(capture_failure) is not str
                or capture_failure not in {"provider_response_byte_limit", "provider_body_capture_failed"})):
        return checks, "sra_file_capture_invalid"
    exact = counts == [file["size_bytes"], file["size_bytes"]] and (declared is None or declared == file["size_bytes"])
    checks["body_capture"] = "complete" if complete and capture_failure is None and exact else "incomplete"
    if type(status) is not int or not 100 <= status <= 599:
        return checks, "sra_file_http_status_unknown"
    if not 200 <= status < 300:
        return checks, "sra_file_http_not_success"
    if status == 206 or any(key == "content-range" for key, _ in response_headers):
        return checks, "sra_file_unrequested_range"
    if capture_failure is not None:
        return checks, capture_failure
    if checks["body_capture"] != "complete":
        return checks, "sra_file_capture_incomplete"
    if observed["media_type"] != spec["media_type"]:
        checks["request"] = "conflicting"
        return checks, "sra_file_request_conflict"
    if any(key == "content-encoding" and value.lower().strip() not in ("", "identity")
            for key, value in response_headers):
        return checks, "sra_file_content_encoding_unsupported"
    if claims["size_bytes"] is not None:
        checks["native_size"] = "verified" if claims["size_bytes"] == file["size_bytes"] else "conflicting"
    if claims["md5_token"] is not None:
        checks["native_md5"] = "verified" if claims["md5_token"].lower() == file["md5"] else "conflicting"
    failure = ("sra_file_native_size_conflict" if checks["native_size"] == "conflicting" else
        "sra_file_native_md5_conflict" if checks["native_md5"] == "conflicting" else None)
    return checks, failure


def sra_file_value_schema():
    return deepcopy(_VALUE)


def validate_sra_file_value(value):
    value = _validated(value, _VALUE, "sra_file_value_invalid")
    arguments = validate_sra_file_arguments(value["requested"])
    selection = validate_sra_file_selection(value["selection"], arguments=arguments)
    file = value["raw_file"]
    _require(_SHA.fullmatch(file["sha256"]) is not None
        and re.fullmatch(r"[a-f0-9]{32}", file["md5"], re.ASCII) is not None
        and file["artifact_ref"] == "artifact_" + file["sha256"], "sra_file_value_invalid")
    checks, failure = _verification(arguments, selection, value["observed"], file)
    _require(value["checks"] == checks and value["failure_code"] == failure, "sra_file_value_invalid")
    return value


def sra_file_value(snapshot, *, arguments, selection, artifact_ref):
    """Retain operational checks; archive identity and biology remain unparsed."""
    arguments = validate_sra_file_arguments(arguments)
    selection = validate_sra_file_selection(selection, arguments=arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "sra_file_value_invalid")
    sha = hashlib.sha256(snapshot.content).hexdigest()
    _require(artifact_ref == "artifact_" + sha, "sra_file_value_invalid")
    observed = dict(service=snapshot.service, url=snapshot.url, request=deepcopy(snapshot.request),
        media_type=snapshot.media_type, transport=deepcopy(snapshot.transport))
    # The HTTP owner uses tuples for header occurrences. Its retained JSON
    # control uses arrays; this changes no header value or native entity byte.
    transport = observed["transport"]
    if type(transport) is dict and type(transport.get("header_items")) is list:
        transport["header_items"] = [list(row) if type(row) is tuple else row for row in transport["header_items"]]
    file = dict(artifact_ref=artifact_ref, sha256=sha, size_bytes=len(snapshot.content),
        md5=hashlib.md5(snapshot.content, usedforsecurity=False).hexdigest())
    _validated(observed, {**_OBSERVED, "$defs": dict(Json=_JSON)}, "sra_file_value_invalid")
    checks, failure = _verification(arguments, selection, observed, file)
    return validate_sra_file_value(dict(version="ncbi_sra_file_value_v1", requested=arguments,
        selection=selection, observed=observed, raw_file=file, checks=checks, failure_code=failure))


def sra_file_receipt_schema():
    return acquisition_receipt_schema(failure_codes=SRA_FILE_FAILURE_CODES)


def validate_sra_file_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=SRA_FILE_FAILURE_CODES,
        invalid_code="sra_file_receipt_invalid")


def failed_sra_file_receipt(code, *, source_ref=None):
    return validate_sra_file_receipt(dict(acquired=False, source_ref=source_ref, data_ref=None, failure_code=code))


def sra_file_receipt(value, *, source_ref):
    value = validate_sra_file_value(value)
    if value["failure_code"] is not None:
        return failed_sra_file_receipt(value["failure_code"], source_ref=source_ref)
    return validate_sra_file_receipt(dict(acquired=True, source_ref=source_ref,
        data_ref=value["raw_file"]["artifact_ref"], failure_code=None))


__all__ = ["TOOL", "SERVICE", "MAX_BYTES", "MAX_ADVERTISEMENT_BYTES", "ADVERTISEMENT_FORMAT",
    "ALLOWED_DOWNLOAD_HOSTS", "ARGUMENTS_SCHEMA", "SRA_FILE_FAILURE_CODES", "sra_file_argument_schema",
    "validate_sra_file_arguments", "sra_file_selection_schema", "validate_sra_file_selection",
    "resolve_sra_file_selection", "sra_file_request_spec", "sra_file_value_schema", "sra_file_value",
    "validate_sra_file_value", "sra_file_receipt_schema", "validate_sra_file_receipt",
    "failed_sra_file_receipt", "sra_file_receipt"]
