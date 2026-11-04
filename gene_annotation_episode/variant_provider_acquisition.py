"""Bounded, explicit EVA/gnomAD acquisition; no analysis or transport here.

Protocol authorities are EVA's VariantWSServer/RegionWSServer and QueryUtils,
and gnomad-browser's query/variant/gene GraphQL types and resolvers. RS/SS
accessioning, unverified species-list envelopes, arbitrary GraphQL, automatic
selection and pagination are not exposed. Upstream source is not live proof.
"""
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import re
from urllib.parse import quote, urlencode

from .acquisition import SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from .domain import ContractError, canonical
from .ucsc_acquisition import _parse, _analyse


OPERATIONS = ("public.eva.request", "public.gnomad.request")
MAX_BYTES = 8 * 1024 ** 2
VALUE_VERSION = "variant_provider_value_v1"
EVA_ROOT = "https://www.ebi.ac.uk/eva/webservices/rest/v1"
GNOMAD_ROOT = "https://gnomad.broadinstitute.org/api"
DATASET_REFERENCES = {
    **{key: "GRCh38" for key in ("gnomad_r4", "gnomad_r4_non_ukb", "gnomad_r3",
        "gnomad_r3_controls_and_biobanks", "gnomad_r3_non_cancer", "gnomad_r3_non_neuro",
        "gnomad_r3_non_topmed", "gnomad_r3_non_v2")},
    **{key: "GRCh37" for key in ("gnomad_r2_1", "gnomad_r2_1_controls", "gnomad_r2_1_non_neuro",
        "gnomad_r2_1_non_cancer", "gnomad_r2_1_non_topmed", "exac")},
}
VARIANT_FIELDS = ("rsids", "exome", "genome", "joint", "flags")
GENE_FIELDS = ("symbol", "gencode_symbol", "name", "chrom", "start", "stop", "strand", "variants")
PROVIDER_FAILURE_CODES = tuple("variant_provider_" + code for code in (
    "operation_unknown", "arguments_invalid", "snapshot_invalid", "artifact_identity_conflict",
    "selected_request_conflict", "transport_invalid", "transfer_policy_conflict",
    "http_status_unavailable", "http_not_successful", "partial_response", "capture_incomplete",
    "capture_identity_conflict", "content_encoding_unsupported", "native_representation_invalid",
    "native_error", "native_identity_conflict", "native_result_unavailable", "value_invalid",
    "receipt_invalid")) + ("provider_connection_failed", "provider_request_timeout",
    "provider_response_byte_limit", "provider_body_capture_failed", "data_acquisition_failed",
    "data_acquisition_publication_incomplete", "invalid_tool_input", "adapter_execution_failed")


def _require(condition, code="value_invalid"):
    if not condition:
        raise ContractError("variant_provider_" + code)


def _json(value):
    if type(value) is dict:
        for key, child in value.items():
            _require(type(key) is str); key.encode("utf-8"); _json(child)
    elif type(value) is list:
        for child in value: _json(child)
    elif type(value) is str:
        value.encode("utf-8")
    else:
        _require(type(value) in (type(None), bool, int, float)
            and (type(value) is not float or math.isfinite(value)))


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


_TEXT = {"type": "string", "minLength": 1, "maxLength": 4096}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": MAX_BYTES}
_DATASET = {"enum": list(DATASET_REFERENCES)}
_REFERENCE = {"enum": ["GRCh37", "GRCh38"]}
_PAGE = {"limit": {"type": "integer", "minimum": 1, "maximum": 10000},
    "skip": {"type": "integer", "minimum": 0}, "max_bytes": _LIMIT}
_ARGUMENTS = {
    OPERATIONS[0]: {"oneOf": [
        _object({"request_type": {"const": "variant"}, "species": _TEXT, "variant_id": _TEXT, **_PAGE}),
        _object({"request_type": {"const": "region"}, "species": _TEXT, "chromosome": _TEXT,
            "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 0}, **_PAGE})]},
    OPERATIONS[1]: {"oneOf": [
        _object({"request_type": {"const": "variant"}, "dataset": _DATASET,
            "reference_genome": _REFERENCE, "variant_id": _TEXT,
            "fields": {"type": "array", "items": {"enum": list(VARIANT_FIELDS)}, "uniqueItems": True}, "max_bytes": _LIMIT}),
        _object({"request_type": {"const": "gene_search"}, "query": _TEXT,
            "reference_genome": _REFERENCE, "max_bytes": _LIMIT}),
        _object({"request_type": {"const": "gene"}, "gene_id": _TEXT, "reference_genome": _REFERENCE,
            "dataset": {"anyOf": [_DATASET, {"type": "null"}]},
            "fields": {"type": "array", "items": {"enum": list(GENE_FIELDS)}, "uniqueItems": True}, "max_bytes": _LIMIT})]},
}


def _text(value):
    return (type(value) is str and 1 <= len(value) <= 4096
        and not any(ord(char) < 32 or ord(char) == 127 for char in value))


def provider_argument_schema(operation):
    _require(type(operation) is str and operation in OPERATIONS, "operation_unknown")
    return deepcopy(_ARGUMENTS[operation])


def validate_provider_arguments(operation, args):
    _require(type(operation) is str and operation in OPERATIONS, "operation_unknown")
    try:
        _json(args)
        _require(type(args) is dict and type(args.get("request_type")) is str, "arguments_invalid")
        kind = args["request_type"]
        branches = _ARGUMENTS[operation]["oneOf"]
        branch = next((row for row in branches if row["properties"]["request_type"]["const"] == kind), None)
        _require(branch is not None and set(args) == set(branch["properties"]), "arguments_invalid")
        _require(type(args["max_bytes"]) is int and 1 <= args["max_bytes"] <= MAX_BYTES, "arguments_invalid")
        if operation == OPERATIONS[0]:
            _require(_text(args["species"]) and re.fullmatch(r"[A-Za-z0-9.-]+_[A-Za-z0-9_.-]+", args["species"], re.ASCII), "arguments_invalid")
            _require(type(args["limit"]) is int and 1 <= args["limit"] <= 10000
                and type(args["skip"]) is int and args["skip"] >= 0, "arguments_invalid")
            if kind == "variant":
                _require(_text(args["variant_id"]), "arguments_invalid")
            else:
                _require(_text(args["chromosome"]) and not any(c in args["chromosome"] for c in ":,-")
                    and type(args["start"]) is int and type(args["end"]) is int
                    and 0 <= args["start"] <= args["end"], "arguments_invalid")
        else:
            _require(type(args["reference_genome"]) is str and args["reference_genome"] in ("GRCh37", "GRCh38"), "arguments_invalid")
            if kind == "gene_search":
                _require(_text(args["query"]), "arguments_invalid")
            else:
                allowed = VARIANT_FIELDS if kind == "variant" else GENE_FIELDS
                fields = args["fields"]
                _require(type(fields) is list and all(type(field) is str and field in allowed for field in fields)
                    and len(fields) == len(set(fields)), "arguments_invalid")
                if kind == "variant":
                    parts = args["variant_id"].split("-") if _text(args["variant_id"]) else []
                    _require(len(parts) == 4 and all(parts) and re.fullmatch(r"[0-9]+", parts[1], re.ASCII)
                        and int(parts[1]) > 0, "arguments_invalid")
                else:
                    _require(_text(args["gene_id"]) and re.fullmatch(r"ENSG[0-9]{11}", args["gene_id"], re.ASCII), "arguments_invalid")
                dataset = args["dataset"]
                if kind == "gene" and "variants" not in fields:
                    _require(dataset is None, "arguments_invalid")
                else:
                    _require(type(dataset) is str and dataset in DATASET_REFERENCES
                        and DATASET_REFERENCES[dataset] == args["reference_genome"], "arguments_invalid")
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError) as error:
        raise ContractError("variant_provider_arguments_invalid") from error
    return deepcopy(args)


def _sequencing_query(*, joint=False):
    return ("{ ac an homozygote_count hemizygote_count " + ("" if joint else "af ")
        + "filters populations { id ac an homozygote_count hemizygote_count } }")


def _variant_query(fields):
    identity = "variant_id reference_genome chrom pos ref alt"
    return identity + " " + " ".join(field + " " + _sequencing_query(joint=field == "joint")
        if field in {"exome", "genome", "joint"} else field for field in fields)


def provider_request_spec(operation, args):
    """Keywords for the existing PublicClients._http; body selects POST."""
    args = validate_provider_arguments(operation, args)
    if operation == OPERATIONS[0]:
        resource = ("variants/" + quote(args["variant_id"], safe="") + "/info" if args["request_type"] == "variant"
            else "segments/" + quote(args["chromosome"] + ":" + str(args["start"]) + "-" + str(args["end"]), safe="") + "/variants")
        url, service = EVA_ROOT + "/" + resource, "eva"
        params = {"species": args["species"], "limit": args["limit"], "skip": args["skip"]}
        body = None
    else:
        service, url, params = "gnomad", GNOMAD_ROOT, {}
        kind = args["request_type"]
        variables = {"reference": args["reference_genome"]}
        if kind == "variant":
            variables = {"id": args["variant_id"], "dataset": args["dataset"]}
            query = ("query VariantReference($id: String!, $dataset: DatasetId!) { variant(variantId: $id, dataset: $dataset) { "
                + _variant_query(args["fields"]) + " } }")
        elif kind == "gene_search":
            variables["query"] = args["query"]
            query = ("query GeneSearch($query: String!, $reference: ReferenceGenomeId!) { "
                "gene_search(query: $query, reference_genome: $reference) { ensembl_id ensembl_version symbol } }")
        else:
            variables["id"] = args["gene_id"]
            fields = [field if field != "variants" else "variants(dataset: $dataset) { "
                + _variant_query(("rsids", "exome", "genome", "joint", "flags")) + " }" for field in args["fields"]]
            use_dataset = "variants" in args["fields"]
            if use_dataset: variables["dataset"] = args["dataset"]
            query = ("query GeneReference($id: String!, $reference: ReferenceGenomeId!"
                + (", $dataset: DatasetId!" if use_dataset else "") + ") { gene(gene_id: $id, reference_genome: $reference) { "
                + "gene_id gene_version reference_genome " + " ".join(fields) + " } }")
        body = json.dumps({"query": query, "variables": variables}, ensure_ascii=True,
            allow_nan=False, separators=(",", ":")).encode("ascii")
    return {"service": service, "url": url, "params": params, "media_type": "application/json",
        "body": body, "content_type": "application/json" if body is not None else None,
        "accept": "application/json", "max_bytes": args["max_bytes"], "follow_redirects": False}


def _association(observed, operation, args):
    spec = provider_request_spec(operation, args)
    address = spec["url"] + ("?" + urlencode(spec["params"], doseq=True) if spec["params"] else "")
    _require(observed["service"] == spec["service"] and observed["url"] in (spec["url"], address)
        and canonical(observed["request"]) == canonical(spec["params"])
        and observed["media_type"] == spec["media_type"], "selected_request_conflict")
    transport = observed["transport"]
    _require(type(transport) is dict, "transport_invalid")
    request = transport.get("request")
    body = spec["body"]
    keys = {"url", "method", "headers"} | ({"body_base64", "body_sha256"} if body is not None else set())
    _require(type(request) is dict and set(request) == keys and request["url"] == address
        and request["method"] == ("POST" if body is not None else "GET")
        and transport.get("effective_url", address) == address, "selected_request_conflict")
    headers = request["headers"]
    _require(type(headers) is dict and all(type(k) is str and type(v) is str for k, v in headers.items()), "transport_invalid")
    lowered = [key.lower() for key in headers]
    _require(len(lowered) == len(set(lowered)) and set(lowered) <= {"accept", "content-type", "user-agent"}
        and {k.lower(): v for k, v in headers.items()}.get("accept") == "application/json", "selected_request_conflict")
    _require({k.lower(): v for k, v in headers.items()}.get("content-type") == spec["content_type"], "selected_request_conflict")
    if body is not None:
        _require(request["body_base64"] == base64.b64encode(body).decode("ascii")
            and request["body_sha256"] == hashlib.sha256(body).hexdigest(), "selected_request_conflict")
    policy = transport.get("request_policy")
    timeout = policy.get("timeout_seconds") if type(policy) is dict else None
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    _require(type(policy) is dict and set(policy) == {"timeout_seconds", "automatic_redirects"}
        and policy["automatic_redirects"] is False and valid_timeout
        and type(transport.get("response_byte_limit")) is int
        and transport["response_byte_limit"] == args["max_bytes"], "transfer_policy_conflict")


def _capture_failure(transport, size):
    status = transport.get("status")
    if type(status) is not int or not 100 <= status <= 599: return "http_status_unavailable"
    if not 200 <= status < 300: return "http_not_successful"
    pairs = transport.get("header_items")
    if type(pairs) is not list or any(type(pair) not in (list, tuple) or len(pair) != 2
            or any(type(item) is not str for item in pair) for pair in pairs): return "transport_invalid"
    if status == 206 or any(key.lower() == "content-range" for key, _ in pairs): return "partial_response"
    if any(key.lower() == "content-encoding" and value.strip().lower() != "identity" for key, value in pairs):
        return "content_encoding_unsupported"
    if (transport.get("body_complete") is not True or transport.get("body_capture_failure") is not None
            or transport.get("body_capture_error") is not None): return "capture_incomplete"
    if any(type(transport.get(key)) is not int or transport[key] != size
            for key in ("retained_body_bytes", "observed_body_bytes")): return "capture_identity_conflict"
    declared = transport.get("declared_body_bytes")
    if declared is not None and (type(declared) is not int or declared != size): return "capture_identity_conflict"
    return None


def _members(node, name):
    return [row["value"] for row in node.get("members", []) if row["name"] == name] if type(node) is dict and node.get("kind") == "object" else []


def _one(node, name):
    values = _members(node, name)
    return values[0] if len(values) == 1 else None


def _string(node):
    return node["value"] if type(node) is dict and node.get("kind") == "string" else None


def _integer(node):
    return type(node) is dict and node.get("kind") == "number" and re.fullmatch(r"-?(0|[1-9][0-9]*)", node["token"], re.ASCII) is not None


def _null(node):
    return type(node) is dict and node.get("kind") == "null"


def _list(node, check):
    return type(node) is dict and node.get("kind") == "array" and all(check(item) for item in node["items"])


def _nonempty_error(node):
    return node is not None and not _null(node) and not (node.get("kind") == "string" and node["value"] == "")


def _sequencing_shape(node, *, joint=False):
    if _null(node): return True
    if node is None or node.get("kind") != "object": return False
    for key in ("ac", "an", "homozygote_count", "hemizygote_count"):
        field = _one(node, key)
        if not (_null(field) or _integer(field)): return False
    if not joint:
        field = _one(node, "af")
        if not (_null(field) or type(field) is dict and field.get("kind") == "number"): return False
    filters = _one(node, "filters")
    if not (_null(filters) or _list(filters, lambda item: _string(item) is not None)): return False
    populations = _one(node, "populations")
    if _null(populations): return True
    def population(item):
        return _null(item) or (item.get("kind") == "object" and _string(_one(item, "id")) is not None
            and all(_integer(_one(item, key)) for key in ("ac", "an", "homozygote_count"))
            and (_null(_one(item, "hemizygote_count")) or _integer(_one(item, "hemizygote_count"))))
    return _list(populations, population)


def _variant_shape(node, fields, reference):
    if node is None or node.get("kind") != "object": return False
    if any(_string(_one(node, key)) is None for key in ("variant_id", "reference_genome", "chrom", "ref", "alt")):
        return False
    if _string(_one(node, "reference_genome")) != reference or not _integer(_one(node, "pos")): return False
    if _string(_one(node, "variant_id")) != "-".join((_string(_one(node, "chrom")),
            _one(node, "pos")["token"], _string(_one(node, "ref")), _string(_one(node, "alt")))):
        return False
    for field in fields:
        child = _one(node, field)
        if field in {"exome", "genome", "joint"}:
            if not _sequencing_shape(child, joint=field == "joint"): return False
        elif not (_null(child) or _list(child, lambda item: _string(item) is not None)): return False
    return True


def _gnomad_native(document, args):
    errors = _members(document, "errors")
    if len(errors) > 1 or errors and not _list(errors[0], lambda _: True): return "native_representation_invalid", "unavailable"
    if errors and errors[0]["items"]: return "native_error", "unavailable"
    root = _one(document, "data")
    kind = args["request_type"]
    result = _one(root, "gene_search" if kind == "gene_search" else kind)
    if result is None or _null(result): return "native_result_unavailable", "unavailable"
    if kind == "gene_search":
        valid = _list(result, lambda row: row.get("kind") == "object"
            and _string(_one(row, "ensembl_id")) is not None and _string(_one(row, "ensembl_version")) is not None
            and (_null(_one(row, "symbol")) or _string(_one(row, "symbol")) is not None))
        return (None, "empty" if not result["items"] else "confirmed") if valid else ("native_representation_invalid", "unavailable")
    if kind == "variant":
        if not _variant_shape(result, args["fields"], args["reference_genome"]): return "native_representation_invalid", "unavailable"
        return (None, "confirmed") if _string(_one(result, "variant_id")) == args["variant_id"] else ("native_identity_conflict", "conflict")
    if result.get("kind") != "object": return "native_representation_invalid", "unavailable"
    if (_string(_one(result, "gene_id")) != args["gene_id"]
            or _string(_one(result, "reference_genome")) != args["reference_genome"]):
        return "native_identity_conflict", "conflict"
    if _string(_one(result, "gene_version")) is None: return "native_representation_invalid", "unavailable"
    for field in args["fields"]:
        child = _one(result, field)
        if field == "variants":
            if not _list(child, lambda row: _variant_shape(row, VARIANT_FIELDS, args["reference_genome"])):
                return "native_representation_invalid", "unavailable"
        elif field in {"start", "stop"}:
            if not _integer(child): return "native_representation_invalid", "unavailable"
        elif not (_string(child) is not None or field == "name" and _null(child)):
            return "native_representation_invalid", "unavailable"
    return None, "confirmed"


def _eva_native(document, args):
    if document.get("kind") != "object": return "native_representation_invalid", "unavailable"
    version = _string(_one(document, "apiVersion"))
    if version is None: return "native_representation_invalid", "unavailable"
    if version != "v1": return "native_identity_conflict", "conflict"
    errors = _members(document, "error")
    if len(errors) != 1: return "native_representation_invalid", "unavailable"
    if _nonempty_error(errors[0]): return "native_error", "unavailable"
    page = _one(document, "queryOptions")
    if any(not _integer(_one(page, key)) for key in ("limit", "skip")):
        return "native_representation_invalid", "unavailable"
    # QueryUtils explicitly serializes a requested zero skip as -1. This is
    # native page custody, not a statement about the biological population.
    if (_one(page, "limit")["token"] != str(args["limit"])
            or _one(page, "skip")["token"] != str(args["skip"] if args["skip"] > 0 else -1)):
        return "native_identity_conflict", "conflict"
    responses = _one(document, "response")
    if not _list(responses, lambda row: row.get("kind") == "object") or len(responses["items"]) != 1:
        return "native_result_unavailable", "unavailable"
    response = responses["items"][0]
    if (len(_members(response, "errorMsg")) != 1
            or any(not _integer(_one(response, key)) for key in ("numResults", "numTotalResults"))):
        return "native_representation_invalid", "unavailable"
    if _nonempty_error(_one(response, "errorMsg")): return "native_error", "unavailable"
    # QueryUtils.buildQueryResult never sets id: QueryResult() supplies "".
    # It is not an echoed selected query. Missing/ambiguous/unestablished IDs
    # cannot authenticate a different native response under a matched URI.
    if _string(_one(response, "id")) != "": return "native_result_unavailable", "unavailable"
    rows = _one(response, "result")
    if not _list(rows, lambda row: row.get("kind") == "object"):
        return "native_result_unavailable", "unavailable"
    for row in rows["items"]:
        if (any(_string(_one(row, key)) is None for key in ("chromosome", "reference", "alternate"))
                or any(not _integer(_one(row, key)) for key in ("start", "end"))):
            return "native_representation_invalid", "unavailable"
        start, end = (_one(row, key)["token"] for key in ("start", "end"))
        if start.startswith("-") or end.startswith("-") or (len(end), end) < (len(start), start):
            return "native_representation_invalid", "unavailable"
        if args["request_type"] == "variant":
            identifiers = _one(row, "ids")
            native_ids = [_string(item) for item in identifiers["items"]] if _list(identifiers, lambda item: _string(item) is not None) else []
            main = _string(_one(row, "mainId"))
            # Coordinate/allele aliases require more native matching authority.
            # Do not infer them from URLs or rewrite normalized EVA alleles.
            if args["variant_id"] not in [main, *native_ids]: return "native_result_unavailable", "unavailable"
        else:
            # The official repository uses inclusive overlap, not containment.
            # Boundary-spanning rows can retain INSDC contigs; no alias proof
            # is present in this response, so unmatched literals stay unknown.
            if _string(_one(row, "chromosome")) != args["chromosome"]:
                return "native_result_unavailable", "unavailable"
            low, high = str(args["start"]), str(args["end"])
            if (len(start), start) > (len(high), high) or (len(end), end) < (len(low), low):
                return "native_identity_conflict", "conflict"
    return None, "empty" if not rows["items"] else "confirmed"


def _built_value(operation, args, raw, observed):
    _association(observed, operation, args)
    _require(len(raw) <= args["max_bytes"], "capture_identity_conflict")
    node, _, error, _, document, issues = _parse(raw)
    if error is None:
        # Always use the same reversible native-token authority, even when a
        # plain JSON number would also happen to be representable.
        _, document, issues, _ = _analyse(node)
    failure = _capture_failure(observed["transport"], len(raw))
    native_failure, identity = ("native_representation_invalid", "unavailable") if error else (
        _eva_native(document, args) if operation == OPERATIONS[0] else _gnomad_native(document, args))
    failure = failure or native_failure
    qualifications = deepcopy(issues)
    if error: qualifications.append({"code": error, "pointer": "/native_document"})
    pairs = observed["transport"].get("header_items")
    if type(pairs) is list and all(type(pair) is list and len(pair) == 2
            and all(type(item) is str for item in pair) for pair in pairs):
        if any(key.lower() == "content-type" and not (mime := item.split(";", 1)[0].strip().lower())
                in ("application/json",) and not mime.endswith("+json") for key, item in pairs):
            qualifications.append({"code": "native_content_type_qualification", "pointer": "/observed/transport/header_items"})
    if operation == OPERATIONS[0]:
        qualifications.append({"code": "requested_species_assembly_not_independent_native_confirmation", "pointer": "/requested/species"})
        qualifications.append({"code": "native_coordinates_not_converted", "pointer": "/native_document"})
        qualifications.append({"code": "native_query_id_is_not_a_selected_query_echo", "pointer": "/native_document"})
        if args["request_type"] == "region":
            qualifications.append({"code": "native_region_contig_alias_not_inferred", "pointer": "/native_document"})
    else:
        if args["request_type"] == "gene_search":
            qualifications.append({"code": "native_gene_search_is_capped_not_complete_population", "pointer": "/native_document"})
        if args["request_type"] == "gene" and "variants" in args["fields"]:
            qualifications.append({"code": "native_gene_variant_selection_not_all_genomic_variants", "pointer": "/native_document"})
        if "dataset" in args and args["dataset"] is not None:
            qualifications.append({"code": "dataset_bound_by_request_not_independent_native_echo", "pointer": "/requested/dataset"})
    return {"version": VALUE_VERSION, "operation": operation, "requested": deepcopy(args),
        "raw": {"encoding": "base64", "data": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
        "observed": deepcopy(observed), "native_document": document,
        "parsing_state": "available" if error is None else "unavailable", "identity_state": identity,
        "population_scope": "returned_response_only", "qualifications": qualifications,
        "failure_code": "variant_provider_" + failure if failure is not None else None}


def provider_value(snapshot, *, operation, arguments, artifact_ref):
    args = validate_provider_arguments(operation, arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "snapshot_invalid")
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(), "artifact_identity_conflict")
    transport = deepcopy(snapshot.transport)
    # The actual HTTP engine produces tuple header pairs. Their JSON control
    # representation is an array; native response bytes are never normalized.
    if type(transport) is dict and type(transport.get("header_items")) is list:
        transport["header_items"] = [list(pair) if type(pair) is tuple else pair for pair in transport["header_items"]]
    observed = {"service": snapshot.service, "url": snapshot.url, "request": deepcopy(snapshot.request),
        "media_type": snapshot.media_type, "transport": transport}
    _json(observed)
    _require(all(type(observed[key]) is str for key in ("service", "url", "media_type")), "snapshot_invalid")
    return _built_value(operation, args, snapshot.content, observed)


def validate_provider_value(value):
    try:
        _json(value)
        _require(type(value) is dict and set(value) == {"version", "operation", "requested", "raw", "observed",
            "native_document", "parsing_state", "identity_state", "population_scope", "qualifications", "failure_code"})
        args = validate_provider_arguments(value["operation"], value["requested"])
        raw = value["raw"]
        _require(type(raw) is dict and set(raw) == {"encoding", "data", "sha256", "size_bytes"}
            and raw["encoding"] == "base64" and type(raw["data"]) is str)
        content = base64.b64decode(raw["data"], validate=True)
        _require(base64.b64encode(content).decode("ascii") == raw["data"]
            and type(raw["size_bytes"]) is int and raw["size_bytes"] == len(content)
            and raw["sha256"] == hashlib.sha256(content).hexdigest())
        observed = value["observed"]
        _require(type(observed) is dict and set(observed) == {"service", "url", "request", "media_type", "transport"}
            and all(type(observed[key]) is str for key in ("service", "url", "media_type")))
        expected = _built_value(value["operation"], args, content, observed)
        _require(canonical(value) == canonical(expected))
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError) as error:
        raise ContractError("variant_provider_value_invalid") from error
    return deepcopy(value)


def provider_value_schema():
    node = {"$ref": "#/$defs/NativeJSON"}
    native = {"oneOf": [_object({"kind": {"const": "object"}, "members": {"type": "array", "items": _object({"name": {"type": "string"}, "value": node})}}),
        _object({"kind": {"const": "array"}, "items": {"type": "array", "items": node}}),
        _object({"kind": {"const": "number"}, "token": {"type": "string"}}),
        *[_object({"kind": {"const": kind}, "value": {"type": kind}}) for kind in ("string", "boolean", "null")]]}
    json_value = {"anyOf": [{"type": ["string", "number", "boolean", "null"]},
        {"type": "array", "items": {"$ref": "#/$defs/JSON"}},
        {"type": "object", "additionalProperties": {"$ref": "#/$defs/JSON"}}]}
    schema = _object({"version": {"const": VALUE_VERSION}, "operation": {"enum": list(OPERATIONS)},
        "requested": {"anyOf": [deepcopy(_ARGUMENTS[operation]) for operation in OPERATIONS]},
        "raw": _object({"encoding": {"const": "base64"}, "data": {"type": "string"},
            "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "size_bytes": {"type": "integer", "minimum": 0}}),
        "observed": _object({"service": {"type": "string"}, "url": {"type": "string"}, "request": {"$ref": "#/$defs/JSON"},
            "media_type": {"type": "string"}, "transport": {"type": "object", "additionalProperties": {"$ref": "#/$defs/JSON"}}}),
        "native_document": {"anyOf": [node, {"type": "null"}]}, "parsing_state": {"enum": ["available", "unavailable"]},
        "identity_state": {"enum": ["confirmed", "empty", "conflict", "unavailable"]},
        "population_scope": {"const": "returned_response_only"},
        "qualifications": {"type": "array", "items": _object({"code": {"type": "string"}, "pointer": {"type": "string"}})},
        "failure_code": {"enum": [None, *PROVIDER_FAILURE_CODES]}})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"NativeJSON": native, "JSON": json_value}, **schema}


def provider_receipt_schema():
    return acquisition_receipt_schema(failure_codes=PROVIDER_FAILURE_CODES)


def validate_provider_receipt(receipt):
    return validate_acquisition_receipt(receipt, failure_codes=PROVIDER_FAILURE_CODES, invalid_code="variant_provider_receipt_invalid")


def failed_provider_receipt(code, *, source_ref=None):
    return validate_provider_receipt({"acquired": False, "source_ref": source_ref, "data_ref": None, "failure_code": code})


def provider_receipt(value, *, source_ref):
    value = validate_provider_value(value)
    return (failed_provider_receipt(value["failure_code"], source_ref=source_ref) if value["failure_code"] else
        validate_provider_receipt({"acquired": True, "source_ref": source_ref,
            "data_ref": "artifact_" + value["raw"]["sha256"], "failure_code": None}))


def publish_provider_request(registry, operation, args, snapshot):
    """One private Value/witness; actual native Source; explicit data receipt."""
    args = validate_provider_arguments(operation, args)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "snapshot_invalid")
    artifact_ref = "artifact_" + hashlib.sha256(snapshot.content).hexdigest()
    try:
        value = provider_value(snapshot, operation=operation, arguments=args, artifact_ref=artifact_ref)
    except (ValueError, ContractError, TypeError, UnicodeError, OverflowError, RecursionError) as error:
        code = str(error) if str(error) in PROVIDER_FAILURE_CODES else "variant_provider_snapshot_invalid"
        value, private = None, {"version": "variant_provider_failure_witness_v1",
            "observed_snapshot_service": snapshot.service, "observed_snapshot_url": snapshot.url, "failure_code": code}
        _json(private)
    else:
        private = value
    auxiliary = registry.store.artifact(canonical(private), "application/json")
    captured = replace(snapshot, url=value["observed"]["transport"]["request"]["url"]) if value is not None else snapshot
    source = registry._source("eva" if operation == OPERATIONS[0] else "gnomad", None,
        snapshot=captured, accession=None, software_version=None, auxiliary_artifact_refs=[auxiliary])
    _require(source["artifact_ref"] == artifact_ref, "artifact_identity_conflict")
    receipt = provider_receipt(value, source_ref=source["id"]) if value is not None else failed_provider_receipt(code, source_ref=source["id"])
    return receipt, [source["id"], *([artifact_ref] if receipt["acquired"] else [])]


__all__ = ["OPERATIONS", "provider_argument_schema", "validate_provider_arguments", "provider_request_spec",
    "provider_value", "validate_provider_value", "provider_value_schema", "provider_receipt", "validate_provider_receipt",
    "provider_receipt_schema", "failed_provider_receipt", "PROVIDER_FAILURE_CODES", "publish_provider_request"]
