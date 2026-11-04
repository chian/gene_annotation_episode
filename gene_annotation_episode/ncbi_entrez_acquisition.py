"""Pure, one-request molecular Entrez contracts and retained native documents.

No transport, discovery chain, scoring, record admission or publication occurs
here. Unsupported fetch/database combinations are deliberately unexposed.
"""
from copy import deepcopy
import hashlib
import json
import math
import re
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator, ValidationError, validators

from .acquisition import SourceSnapshot, parse_genbank
from .ucsc_acquisition import _parse as _parse_json, _analyse, _from_plain


TOOL = "public.ncbi.entrez"
VERSION = "ncbi_molecular_entrez_result_v1"
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
MAX_BYTES = 8 * 1024 * 1024
MAX_IDS = 100
DATABASES = ("protein", "nuccore", "gene", "taxonomy", "assembly", "gds", "sra", "snp")
FETCH_FORMATS = {"protein": "genpept", "nuccore": "genbank", "gene": "gene_xml", "taxonomy": "taxonomy_xml",
    "sra": "sra_experiment_package_xml"}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _array(items):
    return {"type": "array", "items": items}


def _nullable(node):
    return {"anyOf": [node, {"type": "null"}]}


_TEXT = {"type": "string"}
_INT = {"type": "integer", "minimum": 0}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": MAX_BYTES}
_IDS = {"type": "array", "minItems": 1, "maxItems": MAX_IDS,
    "items": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}$"}}
_COMMON = {"database": {"enum": list(DATABASES)}, "max_bytes": _LIMIT}
_ARGUMENTS = {"oneOf": [
    _object({"operation": {"const": "search"}, **_COMMON, "term": {"type": "string", "minLength": 1},
        "retstart": _INT, "retmax": {"type": "integer", "minimum": 1, "maximum": MAX_IDS}, "native_format": {"const": "json"}}),
    _object({"operation": {"const": "summary"}, **_COMMON, "ids": _IDS, "native_format": {"const": "json"}}),
    *[_object({"operation": {"const": "fetch"}, "database": {"const": database}, "max_bytes": _LIMIT,
        "ids": {**_IDS, **({"uniqueItems": True} if database == "gene" else {}),
            **({"maxItems": 1, "items": {"type": "string", "pattern": "^(?:SRR|ERR|DRR)[0-9]+$"}}
                if database == "sra" else {})},
        "native_format": {"const": native_format}}) for database, native_format in FETCH_FORMATS.items()],
]}
ARGUMENTS_SCHEMA = deepcopy(_ARGUMENTS)
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _, value: type(value) is int)
    .redefine("number", lambda _, value: type(value) is int or type(value) is float and math.isfinite(value)))
_SOURCE_RE = re.compile(r"source_[a-f0-9]{24,64}\Z")
_ARTIFACT_RE = re.compile(r"artifact_[a-f0-9]{64}\Z")


def _require(condition, code):
    if not condition:
        raise ValueError("ncbi_entrez_" + code)


def _validated(value, schema):
    try:
        value = deepcopy(value)
        json.dumps(value, allow_nan=False)
        _STRICT(schema).validate(value)
    except (ValueError, TypeError, OverflowError, RecursionError, ValidationError) as error:
        raise ValueError("ncbi_entrez_contract_invalid") from error
    return value


def validate_entrez_arguments(arguments):
    value = _validated(arguments, _ARGUMENTS)
    _require(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}", item, re.ASCII)
        is not None for item in value.get("ids", [])), "identifier_invalid")
    if value["operation"] == "summary" or value["operation"] == "fetch" and value["database"] in {"gene", "taxonomy"}:
        _require(all(re.fullmatch(r"[0-9]+", item, re.ASCII) is not None for item in value["ids"]), "numeric_ids_required")
    if value["operation"] == "fetch" and value["database"] == "sra":
        _require(len(value["ids"]) == 1 and re.fullmatch(r"(?:SRR|ERR|DRR)[0-9]+", value["ids"][0], re.ASCII)
            is not None, "sra_run_accession_required")
    if value["operation"] == "search":
        _require(not any(character in value["term"] for character in "\0\r\n"), "term_invalid")
    return value


def entrez_request_spec(arguments):
    arguments = validate_entrez_arguments(arguments)
    operation = arguments["operation"]
    endpoint = {"search": "esearch", "summary": "esummary", "fetch": "efetch"}[operation]
    params = {"db": arguments["database"], "tool": "gene-annotation-episode"}
    if operation == "search":
        params.update(term=arguments["term"], retstart=arguments["retstart"], retmax=arguments["retmax"], retmode="json")
    else:
        params["id"] = ",".join(arguments["ids"])
        params["retmode"] = "json" if operation == "summary" else "xml"
    if operation == "fetch" and arguments["database"] in {"protein", "nuccore"}:
        params.update(retmode="text", rettype="gp" if arguments["database"] == "protein" else "gbwithparts")
    if operation == "fetch" and arguments["database"] == "sra":
        params["rettype"] = "docset"
    media = "application/json" if operation != "fetch" else "text/x-genbank" if arguments["database"] in {"protein", "nuccore"} else "application/xml"
    return {"service": "ncbi_entrez", "url": BASE_URL + endpoint + ".fcgi", "method": "GET",
        "params": params, "media_type": media, "max_bytes": arguments["max_bytes"], "follow_redirects": False}


_JSON_REF = {"$ref": "#/$defs/JsonNode"}
_XML_REF = {"$ref": "#/$defs/XmlNode"}
_JSON_NODE = {"oneOf": [_object({"kind": {"const": "object"}, "members": _array(_object({"name": _TEXT, "value": _JSON_REF}))}),
    _object({"kind": {"const": "array"}, "items": _array(_JSON_REF)}),
    _object({"kind": {"const": "number"}, "token": _TEXT}),
    *[_object({"kind": {"const": kind}, "value": {"type": kind}}) for kind in ("string", "boolean", "null")]]}
_XML_NODE = _object({"tag": _TEXT, "attributes": _array(_object({"name": _TEXT, "value": _TEXT})),
    "text": _nullable(_TEXT), "tail": _nullable(_TEXT), "children": _array(_XML_REF)})
_XML_DOCUMENT = _object({"root": _XML_REF, "fragment_wrapper": {"type": "boolean"}, "doctype": _nullable(_object({"name": _TEXT,
    "public_id": _nullable(_TEXT), "system_id": _nullable(_TEXT)}))})
_DOCUMENT = {"oneOf": [_object({"kind": {"const": "json"}, "value": _JSON_REF}),
    _object({"kind": {"const": "xml"}, "value": _XML_DOCUMENT}),
    _object({"kind": {"const": "genbank"}, "value": _JSON_REF})]}
_ISSUE = _object({"code": _TEXT, "native_locator": _nullable(_TEXT)})
_RECORD = _object({"identifier": _nullable(_TEXT), "reported_uid": _nullable(_TEXT),
    "native_locator": _TEXT, "exact_requested_identifier": {"type": "boolean"}})
_ASSOCIATION = _object({"subject_locator": _TEXT, "native_relation": _TEXT,
    "namespace": _TEXT, "identifier": _TEXT, "native_locator": _TEXT})
_RESPONSE = _object({"request_url": _TEXT, "request_method": {"const": "GET"},
    "http_status": _nullable({"type": "integer", "minimum": 100, "maximum": 599}),
    "content_type": _nullable(_TEXT), "body_complete": _nullable({"type": "boolean"}),
    "retained_bytes": _INT, "reported_retained_bytes": _nullable(_INT), "observed_bytes": _nullable(_INT),
    "declared_bytes": _nullable(_INT), "byte_limit": _INT, "capture_failure": _nullable(_TEXT),
    "header_items": _array(_array(_TEXT))})
_POPULATION = _object({"database": {"enum": list(DATABASES)}, "unit": {"const": "native_record_occurrences"},
    "coverage": {"const": "selected_response_only"}, "matching_count_native": _nullable(_TEXT),
    "retstart_native": _nullable(_TEXT), "retmax_native": _nullable(_TEXT),
    "requested_id_count": _nullable(_INT), "returned_record_count": _nullable(_INT),
    "returned_id_order_native": _nullable(_array(_TEXT)), "records_order": {"const": "native_representation_order"}})
_RESULT = {**_object({"version": {"const": VERSION}, "tool": {"const": TOOL}, "requested": _ARGUMENTS,
    "source_ref": {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$", "format": "reference", "x-reference-namespace": "source"},
    "raw_artifact_ref": {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$", "format": "reference", "x-reference-namespace": "artifact"},
    "response": _RESPONSE, "native_text": _nullable(_TEXT), "native_document": _nullable(_DOCUMENT),
    "native_locator_kind": {"const": "json_pointer_in_result"},
    "parse_state": {"enum": ["json", "xml", "genbank", "unavailable"]},
    "native_response_state": {"enum": ["data", "error", "unknown"]},
    "representation_state": {"enum": ["complete", "partial", "unavailable"]},
    "records": _array(_RECORD), "embedded_xml": _array(_object({"native_locator": _TEXT,
        "document": _nullable(_XML_DOCUMENT), "parse_error": _nullable(_TEXT)})),
    "population": _POPULATION, "associations": _array(_ASSOCIATION), "issues": _array(_ISSUE)}),
    "$defs": {"JsonNode": _JSON_NODE, "XmlNode": _XML_NODE}}


def entrez_result_schema():
    return deepcopy(_RESULT)


def _issue(code, locator=None):
    return {"code": code, "native_locator": locator}


def _members(node, name):
    return [(index, row["value"]) for index, row in enumerate(node.get("members", []))
        if row["name"] == name] if node.get("kind") == "object" else []


def _one(node, name):
    rows = _members(node, name)
    return rows[0][1] if len(rows) == 1 else {}


def _text(node):
    return node.get("value") if node.get("kind") == "string" else None


def _number_text(node):
    token = _text(node) if node.get("kind") == "string" else node.get("token") if node.get("kind") == "number" else None
    return token if type(token) is str and re.fullmatch(r"[0-9]+", token, re.ASCII) is not None else None


def _content(node):
    return bool(node.get("members")) if node.get("kind") == "object" else bool(node.get("items")) if node.get("kind") == "array" else bool(node.get("value"))


class _XMLBuilder(ET.TreeBuilder):
    def __init__(self):
        super().__init__(insert_comments=True, insert_pis=True)
        self.declaration = None

    def doctype(self, name, public_id, system_id):
        self.declaration = dict(name=name, public_id=public_id, system_id=system_id)


def _xml_node(node):
    return {"tag": "#comment" if node.tag is ET.Comment else "#processing_instruction" if node.tag is ET.ProcessingInstruction else node.tag,
        "attributes": [dict(name=name, value=value) for name, value in node.attrib.items()],
        "text": node.text, "tail": node.tail, "children": [_xml_node(child) for child in node]}


def _xml(text, *, fragment=False):
    builder = _XMLBuilder()
    parser = ET.XMLParser(target=builder)
    root = ET.fromstring("<native_fragment>" + text + "</native_fragment>" if fragment else text, parser=parser)
    document = _xml_node(root)
    if fragment:
        document["tag"] = "#fragment"
    return {"root": document, "fragment_wrapper": fragment, "doctype": builder.declaration}


def _walk_json(node, locator):
    yield node, locator
    if node.get("kind") == "object":
        for index, row in enumerate(node["members"]):
            yield from _walk_json(row["value"], locator + "/members/" + str(index) + "/value")
    elif node.get("kind") == "array":
        for index, child in enumerate(node["items"]):
            yield from _walk_json(child, locator + "/items/" + str(index))


def _walk_xml(node, locator):
    yield node, locator
    for index, child in enumerate(node["children"]):
        yield from _walk_xml(child, locator + "/children/" + str(index))


def _sra_xml(document, locator):
    associations = []
    tags = {"STUDY": "sra_study", "STUDY_REF": "sra_study", "SAMPLE": "sra_sample",
        "SAMPLE_REF": "sra_sample", "EXPERIMENT": "sra_experiment", "EXPERIMENT_REF": "sra_experiment",
        "RUN": "sra_run"}
    for node, path in _walk_xml(document["root"], locator + "/root"):
        tag = node["tag"].rsplit("}", 1)[-1].upper()
        if tag not in tags:
            continue
        for index, attribute in enumerate(node["attributes"]):
            if attribute["name"].lower() in {"accession", "acc"}:
                associations.append(dict(subject_locator=path, native_relation=node["tag"] + "/@" + attribute["name"],
                    namespace=tags[tag], identifier=attribute["value"], native_locator=path + "/attributes/" + str(index)))
    return associations


def _sra_fetch_records(document, requested):
    """Keep actual RUN occurrences, without treating packages or reads as runs."""
    records, issues, inventory_known = [], [], True
    for package_index, package in enumerate(document["root"]["children"]):
        if package["tag"] != "EXPERIMENT_PACKAGE":
            continue
        run_sets = [(index, child) for index, child in enumerate(package["children"]) if child["tag"] == "RUN_SET"]
        package_path = "/native_document/value/root/children/" + str(package_index)
        if not run_sets:
            inventory_known = False
            issues.append(_issue("native_sra_run_inventory_missing", package_path))
        for set_index, run_set in run_sets:
            for run_index, run in enumerate(run_set["children"]):
                if run["tag"] != "RUN":
                    continue
                path = package_path + "/children/" + str(set_index) + "/children/" + str(run_index)
                accessions = [item["value"] for item in run["attributes"] if item["name"] == "accession"]
                identifier = accessions[0] if len(accessions) == 1 and accessions[0] else None
                if identifier is None:
                    issues.append(_issue("native_sra_run_identity_missing", path))
                records.append(dict(identifier=identifier, reported_uid=None, native_locator=path,
                    exact_requested_identifier=identifier in requested))
    return records, issues, inventory_known


def _sra_fetch_identity_state(value):
    """Confirm only the requested literal RUN role; sibling runs are retained."""
    requested = value["requested"]["ids"][0]
    matched = [record for record in value["records"] if record["identifier"] == requested]
    if not matched:
        if not value["records"]:
            return "empty" if value["population"]["returned_record_count"] == 0 else "unavailable"
        return "mismatch" if all(record["identifier"] is not None for record in value["records"]) else "unavailable"
    for record in matched:
        node = _record_node(value, record)
        primary_ids = [item["text"] for identifiers in node["children"] if identifiers["tag"] == "IDENTIFIERS"
            for item in identifiers["children"] if item["tag"] == "PRIMARY_ID"]
        if any(item is not None and item != requested for item in primary_ids):
            return "mismatch"
    return "matched"


def _snapshot(snapshot, arguments):
    spec = entrez_request_spec(arguments)
    address = spec["url"] + "?" + urlencode(spec["params"])
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes
        and snapshot.service == spec["service"] and snapshot.url in {spec["url"], address}
        and type(snapshot.request) is dict and type(snapshot.transport) is dict
        and snapshot.media_type == spec["media_type"], "snapshot_conflict")
    _require(json.dumps(snapshot.request, sort_keys=True, allow_nan=False) == json.dumps(arguments, sort_keys=True, allow_nan=False), "selected_request_conflict")
    request, policy = snapshot.transport.get("request"), snapshot.transport.get("request_policy")
    _require(type(request) is dict and set(request) == {"url", "method", "headers"}
        and request.get("url") == address and request.get("method") == "GET", "transport_request_conflict")
    timeout = policy.get("timeout_seconds") if type(policy) is dict else None
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    _require(type(policy) is dict and set(policy) == {"timeout_seconds", "automatic_redirects"}
        and policy.get("automatic_redirects") is False and valid_timeout, "transport_policy_conflict")
    headers = request.get("headers")
    _require(type(headers) is dict and all(type(key) is str and type(value) is str for key, value in headers.items())
        and [value for key, value in headers.items() if key.lower() == "accept"] == [spec["media_type"]], "transport_media_conflict")
    _require(snapshot.transport.get("response_byte_limit") == arguments["max_bytes"]
        and type(snapshot.transport.get("response_byte_limit")) is int
        and len(snapshot.content) <= arguments["max_bytes"], "transport_limit_conflict")
    def observed(name, kind):
        value = snapshot.transport.get(name)
        return value if type(value) is kind and (kind is not int or value >= 0) else None
    status = observed("status", int)
    status = status if status is not None and 100 <= status <= 599 else None
    response_headers = snapshot.transport.get("headers")
    content_type = response_headers.get("content-type") if type(response_headers) is dict else None
    items = snapshot.transport.get("header_items")
    items = [list(pair) for pair in items] if type(items) is list and all(type(pair) in (list, tuple)
        and len(pair) == 2 and all(type(item) is str for item in pair) for pair in items) else []
    return dict(request_url=address, request_method="GET", http_status=status,
        content_type=content_type if type(content_type) is str else None,
        body_complete=observed("body_complete", bool), retained_bytes=len(snapshot.content),
        reported_retained_bytes=observed("retained_body_bytes", int), observed_bytes=observed("observed_body_bytes", int),
        declared_bytes=observed("declared_body_bytes", int), byte_limit=arguments["max_bytes"],
        capture_failure=observed("body_capture_failure", str), header_items=items)


def _capture_issues(response):
    issues = []
    if response["http_status"] is None: issues.append(_issue("http_status_unknown"))
    elif not 200 <= response["http_status"] < 300: issues.append(_issue("http_not_success"))
    if response["body_complete"] is not True: issues.append(_issue("capture_not_complete"))
    if response["capture_failure"] is not None: issues.append(_issue(response["capture_failure"]))
    if response["reported_retained_bytes"] != response["retained_bytes"]: issues.append(_issue("capture_size_unknown_or_conflicting"))
    if response["body_complete"] is True and response["observed_bytes"] != response["retained_bytes"]: issues.append(_issue("capture_observed_size_unknown_or_conflicting"))
    return issues


def _native_entrez_result(raw, arguments, response, source_ref, artifact_ref):
    """Parse retained bytes using the one native authority; never acquire data."""
    issues, records, embedded, associations = _capture_issues(response), [], [], []
    text, document, parse_state, native_state = None, None, "unavailable", "unknown"
    population = dict(database=arguments["database"], unit="native_record_occurrences", coverage="selected_response_only",
        matching_count_native=None, retstart_native=None, retmax_native=None,
        requested_id_count=len(arguments["ids"]) if "ids" in arguments else None, returned_record_count=None,
        returned_id_order_native=None, records_order="native_representation_order")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        issues.append(_issue("invalid_native_utf8"))
    if text is not None:
        try:
            if arguments["native_format"] == "json":
                node, kind, error, plain, tree, json_issues = _parse_json(raw)
                if error is not None: raise ValueError(error)
                if tree is None: _, tree, _, _ = _analyse(_from_plain(plain))
                issues += [_issue(row["code"], "/native_document/value" + row["pointer"][len("/native_document"):]) for row in json_issues]
                document, parse_state, native_state = dict(kind="json", value=tree), "json", "data"
                if any(_content(child) for name in ("error", "ERROR") for _, child in _members(tree, name)):
                    native_state = "error"; issues.append(_issue("native_error", "/native_document/value"))
                if arguments["operation"] == "search":
                    result = _one(tree, "esearchresult")
                    contexts = _members(tree, "esearchresult")
                    result_locator = "/native_document/value/members/" + str(contexts[0][0]) + "/value" if len(contexts) == 1 else "/native_document/value"
                    ids = _one(result, "idlist")
                    for name, target in (("count", "matching_count_native"), ("retstart", "retstart_native"), ("retmax", "retmax_native")):
                        population[target] = _number_text(_one(result, name))
                        if population[target] is None: issues.append(_issue("native_" + name + "_missing_or_ambiguous", result_locator))
                    if ids.get("kind") == "array" and all(_text(item) is not None for item in ids["items"]):
                        locator = "/native_document/value/members/" + str(_members(tree, "esearchresult")[0][0]) + "/value/members/" + str(_members(result, "idlist")[0][0]) + "/value/items/"
                        records = [dict(identifier=_text(item), reported_uid=None, native_locator=locator + str(index), exact_requested_identifier=False)
                            for index, item in enumerate(ids["items"])]
                        population["returned_record_count"] = len(records)
                        population["returned_id_order_native"] = [_text(item) for item in ids["items"]]
                    else: issues.append(_issue("native_id_list_missing_or_ambiguous"))
                    if any(_content(child) for _, child in _members(result, "errorlist")):
                        native_state = "error"; issues.append(_issue("native_error", result_locator))
                    if any(_content(child) for _, child in _members(result, "warninglist")): issues.append(_issue("native_warning", result_locator))
                else:
                    result = _one(tree, "result")
                    if result.get("kind") == "object":
                        root_index = _members(tree, "result")[0][0]
                        uids = _one(result, "uids")
                        valid_uids = uids.get("kind") == "array" and all(_text(item) is not None for item in uids.get("items", []))
                        returned_ids = [_text(item) for item in uids["items"]] if valid_uids else []
                        for index, row in enumerate(result["members"]):
                            if (row["name"] in returned_ids or re.fullmatch(r"[0-9]+", row["name"], re.ASCII) is not None) and row["value"].get("kind") == "object":
                                records.append(dict(identifier=row["name"], reported_uid=_number_text(_one(row["value"], "uid")),
                                    native_locator=f"/native_document/value/members/{root_index}/value/members/{index}/value",
                                    exact_requested_identifier=row["name"] in arguments["ids"]))
                                if records[-1]["reported_uid"] is None:
                                    issues.append(_issue("native_record_uid_missing_or_ambiguous", records[-1]["native_locator"]))
                                elif records[-1]["reported_uid"] != row["name"]:
                                    issues.append(_issue("native_record_uid_conflict", records[-1]["native_locator"]))
                                if any(_content(child) for _, child in _members(row["value"], "error")):
                                    native_state = "error"; issues.append(_issue("native_record_error", records[-1]["native_locator"]))
                        population["returned_record_count"] = len(records) if records or valid_uids else None
                        if not valid_uids:
                            issues.append(_issue("native_uid_order_missing_or_ambiguous"))
                        else:
                            population["returned_id_order_native"] = returned_ids
                            if sorted(population["returned_id_order_native"]) != sorted(row["identifier"] for row in records):
                                issues.append(_issue("native_uid_membership_conflict"))
                    else: issues.append(_issue("native_summary_missing_or_ambiguous"))
                if arguments["database"] == "sra":
                    names = {"run_id": "sra_run", "exp_id": "sra_experiment", "study_id": "sra_study", "sample_id": "sra_sample"}
                    for item, path in _walk_json(tree, "/native_document/value"):
                        if item.get("kind") != "object": continue
                        for index, member in enumerate(item["members"]):
                            field, value = member["name"], _text(member["value"])
                            location = path + "/members/" + str(index) + "/value"
                            if value is not None and field in names:
                                associations.append(dict(subject_locator=path, native_relation=field, namespace=names[field], identifier=value, native_locator=location))
                            if value is not None and field.lower() in {"expxml", "runs"}:
                                try:
                                    xml = _xml(value, fragment=True)
                                    embedded.append(dict(native_locator=location, document=xml, parse_error=None))
                                    associations += _sra_xml(xml, "/embedded_xml/" + str(len(embedded)-1) + "/document")
                                except (ET.ParseError, ValueError, RecursionError):
                                    embedded.append(dict(native_locator=location, document=None, parse_error="invalid_native_xml_fragment"))
                                    issues.append(_issue("invalid_native_xml_fragment", location))
            elif arguments["native_format"] == "sra_experiment_package_xml":
                xml = _xml(text)
                document, parse_state, native_state = dict(kind="xml", value=xml), "xml", "data"
                root = xml["root"]
                if root["tag"] != "EXPERIMENT_PACKAGE_SET":
                    issues.append(_issue("native_root_unexpected", "/native_document/value/root"))
                else:
                    records, native_issues, inventory_known = _sra_fetch_records(xml, arguments["ids"])
                    issues.extend(native_issues)
                    population["returned_record_count"] = len(records) if inventory_known else None
                    population["returned_id_order_native"] = ([record["identifier"] for record in records]
                        if inventory_known and all(record["identifier"] is not None for record in records) else None)
                    associations.extend(_sra_xml(xml, "/native_document/value"))
                if any(item["tag"] in {"ERROR", "Error"} for item, _ in _walk_xml(root, "")):
                    native_state = "error"; issues.append(_issue("native_error"))
            elif arguments["native_format"] in {"gene_xml", "taxonomy_xml"}:
                xml = _xml(text)
                document, parse_state, native_state = dict(kind="xml", value=xml), "xml", "data"
                expected = "Entrezgene-Set" if arguments["database"] == "gene" else "TaxaSet"
                record_tag = "Entrezgene" if arguments["database"] == "gene" else "Taxon"
                root = xml["root"]
                if root["tag"] != expected: issues.append(_issue("native_root_unexpected", "/native_document/value/root"))
                else:
                    for index, child in enumerate(root["children"]):
                        if child["tag"] == record_tag:
                            identifier = None
                            target = "Gene-track_geneid" if arguments["database"] == "gene" else "TaxId"
                            candidates = (child["children"] if arguments["database"] == "taxonomy"
                                else [item for item, _ in _walk_xml(child, "")])
                            matches = [item["text"] for item in candidates if item["tag"] == target]
                            if len(matches) == 1: identifier = matches[0]
                            else: issues.append(_issue("native_record_identity_missing_or_ambiguous", "/native_document/value/root/children/"+str(index)))
                            records.append(dict(identifier=identifier, reported_uid=identifier,
                                native_locator="/native_document/value/root/children/"+str(index), exact_requested_identifier=identifier in arguments["ids"]))
                    population["returned_record_count"] = len(records)
                if any(item["tag"] in {"ERROR", "Error"} for item, _ in _walk_xml(root, "")):
                    native_state = "error"; issues.append(_issue("native_error"))
            else:
                parsed = parse_genbank(raw)
                _require(bool(parsed), "genbank_records_missing")
                _, tree, _, _ = _analyse(_from_plain(parsed))
                document, parse_state, native_state = dict(kind="genbank", value=tree), "genbank", "data"
                records = [dict(identifier=row["accession"], reported_uid=None,
                    native_locator="/native_document/value/items/"+str(index), exact_requested_identifier=row["accession"] in arguments["ids"])
                    for index, row in enumerate(parsed)]
                population["returned_record_count"] = len(records)
        except (ValueError, ET.ParseError, UnicodeError, RecursionError, TypeError, OverflowError) as error:
            document, parse_state, native_state = None, "unavailable", "unknown"
            issues.append(_issue(str(error) if str(error) in {"invalid_native_json", "invalid_native_unicode"} else "native_parse_failed"))
    result = dict(version=VERSION, tool=TOOL, requested=arguments, source_ref=source_ref, raw_artifact_ref=artifact_ref,
        response=response, native_text=text, native_document=document, parse_state=parse_state,
        native_locator_kind="json_pointer_in_result",
        native_response_state=native_state, representation_state="unavailable" if document is None else "partial" if issues else "complete",
        records=records, embedded_xml=embedded, population=population, associations=associations, issues=issues)
    return result


def entrez_result(snapshot, *, arguments, source_ref, artifact_ref):
    arguments = validate_entrez_arguments(arguments)
    _require(type(source_ref) is str and _SOURCE_RE.fullmatch(source_ref) is not None
        and type(artifact_ref) is str and _ARTIFACT_RE.fullmatch(artifact_ref) is not None, "references_invalid")
    response = _snapshot(snapshot, arguments)
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(), "artifact_identity_conflict")
    return validate_entrez_result(_native_entrez_result(snapshot.content, arguments, response, source_ref, artifact_ref))


def _record_node(value, record):
    node = value
    for part in record['native_locator'].split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def _uid(value):
    return (value.lstrip('0') or '0') if type(value) is str and re.fullmatch(r'[0-9]+', value, re.ASCII) else None


def _uid_identity(requested, aliases):
    selected = {_uid(item) for item in requested}
    observed = {_uid(item) for item in aliases}
    if None in selected or None in observed or not observed:
        return 'unavailable'
    return 'matched' if selected & observed else 'mismatch'


def _genbank_identity(node, requested):
    primary = _text(_one(node, 'accession'))
    annotations = _one(node, 'annotations')
    gi = _text(_one(annotations, 'gi'))
    accessions = _one(node, 'accessions')
    aliases = [_text(item) for item in accessions.get('items', [])] if accessions.get('kind') == 'array' else []
    aliases = [item for item in aliases if item is not None]
    if primary is not None:
        aliases.append(primary)
    states = []
    for identifier in requested:
        if identifier in aliases or gi is not None and _uid(identifier) == _uid(gi) and _uid(identifier) is not None:
            return 'matched'
        if any(identifier.casefold() == alias.casefold() for alias in aliases):
            states.append('unavailable')  # Do not reject a possible native case alias.
            continue
        if _uid(identifier) is not None:
            states.append('mismatch' if _uid(gi) is not None else 'unavailable')
            continue
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[0-9]+)?', identifier, re.ASCII) or not aliases:
            states.append('unavailable')
            continue
        version = re.fullmatch(r'(.+)\.([0-9]+)', identifier, re.ASCII)
        if version and version[1] in aliases and (primary is None or not re.fullmatch(
                re.escape(version[1]) + r'\.[0-9]+', primary, re.ASCII)):
            # A secondary/base accession does not declare its historical version.
            states.append('unavailable')
        else:
            states.append('mismatch')
    return 'mismatch' if states and all(state == 'mismatch' for state in states) else 'unavailable'


def entrez_selected_identity_state(value):
    """Compare only explicit native identity roles in an already validated result.

    Unknown aliases and qualified historical mappings are unavailable identity,
    not disagreement. No missing record is manufactured and no request is made.
    """
    requested = value['requested']
    if requested['operation'] == 'search':
        return 'empty' if value['population']['returned_record_count'] == 0 else 'unavailable'
    if requested['operation'] == 'fetch' and requested['database'] == 'sra':
        return _sra_fetch_identity_state(value)
    if not value['records']:
        return 'empty' if value['population']['returned_record_count'] == 0 else 'unavailable'
    states = []
    for record in value['records']:
        node = _record_node(value, record)
        if record['exact_requested_identifier'] and requested['operation'] != 'summary':
            states.append('matched')
            continue
        if requested['operation'] == 'summary':
            if (record['identifier'] is None or record['reported_uid'] is None
                    or _uid(record['identifier']) != _uid(record['reported_uid'])):
                states.append('unavailable')
            elif record['exact_requested_identifier']:
                states.append('matched')
            elif requested['database'] == 'gene' and any(_members(node, name) for name in ('status', 'currentid')):
                # These native fields can qualify discontinued/secondary IDs.
                # No undocumented status number or historical replacement is inferred.
                states.append('unavailable')
            else:
                states.append(_uid_identity(requested['ids'], [record['identifier']]))
        elif requested['database'] in {'protein', 'nuccore'}:
            states.append(_genbank_identity(node, requested['ids']))
        elif requested['database'] == 'gene':
            history = False
            for item, _ in _walk_xml(node, ''):
                if item['tag'] in {'Gene-track_current-id', 'Gene-track_discontinue-date'}:
                    history = True
                if item['tag'] == 'Gene-track_status' and not any(attribute == dict(name='value', value='live')
                        for attribute in item['attributes']):
                    history = True
            states.append('unavailable' if history or record['identifier'] is None else
                _uid_identity(requested['ids'], [record['identifier']]))
        else:
            aliases, ambiguous = [], record['identifier'] is None
            if record['identifier'] is not None:
                aliases.append(record['identifier'])
            for child in node['children']:
                if child['tag'] == 'AkaTaxIds':
                    for item in child['children']:
                        if item['tag'] == 'TaxId' and type(item['text']) is str:
                            aliases.append(item['text'])
                        else:
                            ambiguous = True
            states.append('unavailable' if ambiguous else _uid_identity(requested['ids'], aliases))
    if 'mismatch' in states:
        return 'mismatch'
    return 'matched' if all(state == 'matched' for state in states) else 'unavailable'


def validate_entrez_result(value):
    """Validate native meanings; record admission and original custody are host work."""
    value = _validated(value, _RESULT)
    selected = validate_entrez_arguments(value["requested"])
    _require(_SOURCE_RE.fullmatch(value["source_ref"]) is not None and _ARTIFACT_RE.fullmatch(value["raw_artifact_ref"]) is not None, "references_invalid")
    spec = entrez_request_spec(selected)
    _require(value["response"]["request_url"] == spec["url"] + "?" + urlencode(spec["params"])
        and value["response"]["byte_limit"] == selected["max_bytes"]
        and value["response"]["retained_bytes"] <= selected["max_bytes"], "response_request_conflict")
    if value["native_text"] is not None:
        try:
            raw = value["native_text"].encode("utf-8")
        except UnicodeError as error:
            raise ValueError("ncbi_entrez_native_text_identity_conflict") from error
        _require(len(raw) == value["response"]["retained_bytes"]
            and hashlib.sha256(raw).hexdigest() == value["raw_artifact_ref"][9:], "native_text_identity_conflict")
        expected = _native_entrez_result(raw, selected, value["response"], value["source_ref"], value["raw_artifact_ref"])
        _require(value == expected, "native_result_conflict")
    else:
        # Invalid UTF8 cannot be reconstructed from this DTO. Authenticate only
        # its unavailable representation, without inventing another entity read.
        _require(value["native_document"] is None and value["parse_state"] == "unavailable"
            and value["native_response_state"] == "unknown" and value["representation_state"] == "unavailable"
            and value["records"] == value["embedded_xml"] == value["associations"] == []
            and value["issues"] == _capture_issues(value["response"]) + [_issue("invalid_native_utf8")], "representation_conflict")
        population = value["population"]
        _require(population["database"] == selected["database"]
            and population["requested_id_count"] == (len(selected["ids"]) if "ids" in selected else None)
            and all(population[key] is None for key in ("matching_count_native", "retstart_native", "retmax_native",
                "returned_record_count", "returned_id_order_native")), "population_conflict")
    return value


__all__ = ["TOOL", "VERSION", "ARGUMENTS_SCHEMA", "validate_entrez_arguments", "entrez_request_spec",
    "entrez_result", "validate_entrez_result", "entrez_result_schema", "entrez_selected_identity_state"]
