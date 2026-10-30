"""Pure, source-preserving UniProtKB JSON record/selected-page projection.

This module acquires nothing, creates no artifacts and assigns no scientific
score. Pointers address the retained native JSON; /headers pointers address the
separately retained response-header mapping. Invalid fields remain in those
original bytes. Row filtering never renumbers native ordinals.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import parse_qsl, unquote, urlsplit

from jsonschema import Draft202012Validator

from .uniprot_native_contracts import PARSED_PAGE_SCHEMA


_MISSING = object()
_PROTEIN = re.compile(r"[A-Z]+\Z", re.ASCII)
_SECTIONS = {"proteinDescription": dict, "genes": list, "comments": list,
             "references": list, "keywords": list, "extraAttributes": dict}
_PAGE_VALIDATOR = Draft202012Validator(PARSED_PAGE_SCHEMA)
_REQUEST_VALIDATOR = Draft202012Validator({
    "$ref": "#/$defs/CanonicalRequest", "$defs": PARSED_PAGE_SCHEMA["$defs"]})


def _ptr(parent, key):
    return parent + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _size(value):
    if type(value) is not int or not 1 <= value <= 500:
        raise ValueError("uniprot_page_size_invalid")
    return value


def normalize_query_uniprot(endpoint: str, *, max_results: int | None = None) -> dict:
    """Normalize one explicit supported URL without choosing or fetching work.

    None is omission. Search defaults to the existing client size 10; selected
    sizes describe a page request, never post-response truncation.
    """
    if not isinstance(endpoint, str) or not endpoint or endpoint != endpoint.strip():
        raise ValueError("uniprot_endpoint_invalid")
    if any(ord(char) < 32 or ord(char) == 127 for char in endpoint):
        raise ValueError("uniprot_endpoint_invalid")
    if max_results is not None:
        _size(max_results)
    try:
        url = urlsplit(endpoint)
    except ValueError as error:
        raise ValueError("uniprot_endpoint_invalid") from error
    if "#" in endpoint or url.fragment:
        raise ValueError("uniprot_endpoint_fragment_not_supported")
    if url.scheme or url.netloc:
        if url.scheme != "https" or url.netloc != "rest.uniprot.org":
            raise ValueError("uniprot_endpoint_origin_not_supported")
    elif endpoint.startswith("//"):
        raise ValueError("uniprot_endpoint_origin_not_supported")
    if re.search(r"%(?![0-9A-Fa-f]{2})", url.path + url.query):
        raise ValueError("uniprot_endpoint_encoding_invalid")
    try:
        path = unquote(url.path, errors="strict")
        pairs = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True,
                          errors="strict")
    except (UnicodeError, ValueError) as error:
        raise ValueError("uniprot_endpoint_encoding_invalid") from error
    if not path.startswith("/"):
        path = "/" + path
    params = dict(pairs)
    if len(params) != len(pairs):
        raise ValueError("uniprot_endpoint_duplicate_parameter")
    if "format" in params and params["format"] != "json":
        raise ValueError("uniprot_endpoint_format_not_supported")
    if path == "/uniprotkb/search":
        if set(params) - {"query", "size", "cursor", "format"}:
            raise ValueError("uniprot_endpoint_parameter_not_supported")
        if not params.get("query", "").strip():
            raise ValueError("uniprot_query_required")
        if "cursor" in params and not params["cursor"].strip():
            raise ValueError("uniprot_cursor_invalid")
        selected_size = None
        if "size" in params:
            if not re.fullmatch(r"[0-9]+", params["size"], re.ASCII):
                raise ValueError("uniprot_page_size_invalid")
            selected_size = _size(int(params["size"]))
        if max_results is not None and selected_size not in (None, max_results):
            raise ValueError("uniprot_page_size_conflict")
        return {"operation": "search", "query": params["query"],
                "size": selected_size if selected_size is not None else
                        max_results if max_results is not None else 10,
                **({"cursor": params["cursor"]} if "cursor" in params else {})}
    if set(params) - {"format"}:
        raise ValueError("uniprot_endpoint_parameter_not_supported")
    if max_results is not None:
        raise ValueError("uniprot_record_max_results_not_supported")
    match = re.fullmatch(r"/uniprotkb/([A-Za-z0-9]+)(?:\.json)?", path)
    if not match or match[1] in {"search", "stream", "accessions"}:
        raise ValueError("uniprot_endpoint_path_not_supported")
    return {"operation": "record", "accession": match[1]}


def _canonical_request(request):
    if request is None:
        return None
    if list(_REQUEST_VALIDATOR.iter_errors(request)):
        raise ValueError("uniprot_canonical_request_invalid")
    for key in ("accession", "query", "cursor"):
        if key in request and not request[key].strip():
            raise ValueError("uniprot_canonical_request_invalid")
    return deepcopy(request)


class _Reader:
    def __init__(self, ordinal=None):
        self.ordinal = ordinal
        self.issues = []

    def issue(self, code, pointer, field, effect="field_partial"):
        issue = {"code": code, "record_ordinal": self.ordinal, "pointer": pointer,
                 "field": field, "effect": effect}
        if issue not in self.issues:
            self.issues.append(issue)

    def state(self, value, expected, pointer, field):
        if value is _MISSING:
            return "absent"
        if value is None:
            return "null"
        if not isinstance(value, expected):
            self.issue("field_type_invalid", pointer, field)
            return "invalid"
        return "present"

    def container(self, parent, key, expected, pointer, field):
        value = parent.get(key, _MISSING)
        state = self.state(value, expected, pointer, field)
        return state, value if state == "present" else expected()

    def field(self, parent, key, pointer, group, kind=str, *, minimum=0):
        value = parent.get(key, _MISSING)
        state = self.state(value, kind, pointer, group)
        if state == "present":
            invalid = ((kind is int and (type(value) is not int or value < minimum)) or
                       (kind is list and any(not isinstance(x, str) for x in value)))
            if invalid:
                state = "invalid"
                self.issue("field_type_invalid", pointer, group)
        return {"state": state, "value": value if state == "present" else None,
                "pointer": pointer}


def _metadata(row, pointer, reader):
    out = {name: reader.field(row, key, _ptr(pointer, key), "metadata")
           for name, key in (("uniprot_id", "uniProtkbId"), ("entry_type", "entryType"),
                             ("protein_existence", "proteinExistence"))}
    audit_pointer = _ptr(pointer, "entryAudit")
    _, audit = reader.container(row, "entryAudit", dict, audit_pointer, "metadata")
    for name, key in (("first_public_date", "firstPublicDate"),
                      ("last_annotation_update_date", "lastAnnotationUpdateDate"),
                      ("last_sequence_update_date", "lastSequenceUpdateDate")):
        out[name] = reader.field(audit, key, _ptr(audit_pointer, key), "metadata")
    for name, key in (("entry_version", "entryVersion"), ("sequence_version", "sequenceVersion")):
        out[name] = reader.field(audit, key, _ptr(audit_pointer, key), "metadata", int, minimum=1)
    out["native_sections"] = [{"name": key,
        "state": reader.state(row.get(key, _MISSING), kind, _ptr(pointer, key), "metadata"),
        "pointer": _ptr(pointer, key)} for key, kind in _SECTIONS.items()]
    return out


def _sequence(row, pointer, reader):
    pointer = _ptr(pointer, "sequence")
    state, raw = reader.container(row, "sequence", dict, pointer, "sequence")
    value = reader.field(raw, "value", _ptr(pointer, "value"), "sequence")
    if value["state"] == "present" and not _PROTEIN.fullmatch(value["value"]):
        value = {**value, "state": "invalid", "value": None}
        reader.issue("sequence_invalid", value["pointer"], "sequence")
    observed = len(value["value"]) if value["state"] == "present" else None
    reported = reader.field(raw, "length", _ptr(pointer, "length"), "sequence", int)
    relation = "unavailable"
    if observed is not None and reported["state"] == "present":
        relation = "agree" if observed == reported["value"] else "conflict"
        if relation == "conflict":
            reader.issue("sequence_length_conflict", reported["pointer"], "sequence")
    return {"state": state, "value": value, "reported_length_aa": reported,
            "observed_length_aa": observed, "length_relation": relation,
            "md5": reader.field(raw, "md5", _ptr(pointer, "md5"), "sequence"),
            "crc64": reader.field(raw, "crc64", _ptr(pointer, "crc64"), "sequence"),
            "unit": "aa"}


def _taxon(row, pointer, reader):
    pointer = _ptr(pointer, "organism")
    state, raw = reader.container(row, "organism", dict, pointer, "taxon")
    return {"state": state,
        "taxon_id": reader.field(raw, "taxonId", _ptr(pointer, "taxonId"), "taxon", int, minimum=1),
        "scientific_name": reader.field(raw, "scientificName", _ptr(pointer, "scientificName"), "taxon"),
        "common_name": reader.field(raw, "commonName", _ptr(pointer, "commonName"), "taxon"),
        "synonyms": reader.field(raw, "synonyms", _ptr(pointer, "synonyms"), "taxon", list),
        "lineage_names": reader.field(raw, "lineage", _ptr(pointer, "lineage"), "taxon", list)}


def _evidence(row, pointer, reader):
    """Index every evidences array, retaining its own local ordinal/owner."""
    states, items = [], []
    stack = [(row, pointer)]
    while stack:
        value, location = stack.pop()
        if isinstance(value, dict):
            if "evidences" in value:
                evidence_pointer = _ptr(location, "evidences")
                state, rows = reader.container(value, "evidences", list, evidence_pointer, "evidence")
                states.append(state)
                for ordinal, item in enumerate(rows):
                    item_pointer = _ptr(evidence_pointer, ordinal)
                    if not isinstance(item, dict):
                        reader.issue("evidence_row_invalid", item_pointer, "evidence")
                        continue
                    fields = {name: reader.field(item, key, _ptr(item_pointer, key), "evidence")
                              for name, key in (("evidence_code", "evidenceCode"),
                                                ("source", "source"), ("source_id", "id"))}
                    if fields["evidence_code"]["state"] != "present":
                        reader.issue("evidence_row_invalid", item_pointer, "evidence")
                    items.append({"ordinal": ordinal, "pointer": item_pointer,
                                  "owner_pointer": location, **fields})
            stack.extend((child, _ptr(location, key)) for key, child in reversed(list(value.items())))
        elif isinstance(value, list):
            stack.extend((child, _ptr(location, ordinal)) for ordinal, child in
                         reversed(list(enumerate(value))))
    # Presence of a valid array is independent of malformed arrays elsewhere.
    state = ("present" if "present" in states else "invalid" if "invalid" in states
             else "null" if "null" in states else "absent")
    return {"state": state, "items": items}


def _position(raw, name, pointer, reader):
    state, raw = reader.container(raw, name, dict, pointer, "features")
    return {"state": state,
        "value": reader.field(raw, "value", _ptr(pointer, "value"), "features", int, minimum=1),
        "modifier": reader.field(raw, "modifier", _ptr(pointer, "modifier"), "features")}


def _features(row, pointer, reader, identity, sequence, evidence):
    pointer = _ptr(pointer, "features")
    state, rows = reader.container(row, "features", list, pointer, "features")
    items = []
    for ordinal, item in enumerate(rows):
        item_pointer = _ptr(pointer, ordinal)
        if not isinstance(item, dict):
            reader.issue("field_type_invalid", item_pointer, "features")
            continue
        location_pointer = _ptr(item_pointer, "location")
        location_state, location = reader.container(item, "location", dict, location_pointer, "features")
        start = _position(location, "start", _ptr(location_pointer, "start"), reader)
        end = _position(location, "end", _ptr(location_pointer, "end"), reader)
        sequence_id = reader.field(location, "sequence", _ptr(location_pointer, "sequence"), "features")
        if sequence_id["state"] == "present" and sequence_id["value"] != identity["primary_accession"]:
            binding = "explicit_other_sequence"
        elif (sequence["value"]["state"] == "present" and
              (sequence_id["state"] == "absent" or
               sequence_id["state"] == "present" and sequence_id["value"] == identity["primary_accession"])):
            binding = "entry_sequence"
        else:
            binding = "unresolved"
        if binding != "entry_sequence":
            reader.issue("feature_sequence_unresolved", location_pointer, "features", "qualification")
        a, b = start["value"]["value"], end["value"]["value"]
        exact = start["modifier"]["value"] == end["modifier"]["value"] == "EXACT"
        valid_order = a is not None and b is not None and a <= b
        compatible = binding == "entry_sequence" and valid_order and b <= sequence["observed_length_aa"]
        interval = [a - 1, b] if exact and compatible else None
        if location_state != "present" or not valid_order or (binding == "entry_sequence" and
                                                                b > sequence["observed_length_aa"]):
            reader.issue("feature_location_invalid", location_pointer, "features")
        elif not exact:
            reader.issue("feature_location_invalid", location_pointer, "features", "qualification")
        items.append({"ordinal": ordinal, "pointer": item_pointer,
            "type": reader.field(item, "type", _ptr(item_pointer, "type"), "features"),
            "feature_id": reader.field(item, "featureId", _ptr(item_pointer, "featureId"), "features"),
            "start": start, "end": end, "native_sequence_id": sequence_id,
            "sequence_binding": binding, "exact_interval_0based_half_open": interval,
            "coordinate_unit": "aa", "evidence_pointers": [e["pointer"] for e in evidence["items"]
                                                            if e["owner_pointer"] == item_pointer]})
    return {"state": state, "items": items}


def _cross_references(row, pointer, reader, evidence):
    pointer = _ptr(pointer, "uniProtKBCrossReferences")
    state, rows = reader.container(row, "uniProtKBCrossReferences", list, pointer, "cross_references")
    items = []
    for ordinal, raw in enumerate(rows):
        item_pointer = _ptr(pointer, ordinal)
        if not isinstance(raw, dict):
            reader.issue("cross_reference_invalid", item_pointer, "cross_references")
            continue
        database = reader.field(raw, "database", _ptr(item_pointer, "database"), "cross_references")
        identifier = reader.field(raw, "id", _ptr(item_pointer, "id"), "cross_references")
        if database["state"] != "present" or identifier["state"] != "present":
            reader.issue("cross_reference_invalid", item_pointer, "cross_references")
        properties_pointer = _ptr(item_pointer, "properties")
        properties_state, properties = reader.container(raw, "properties", list, properties_pointer,
                                                        "cross_references")
        projected = []
        for prop_ordinal, prop in enumerate(properties):
            prop_pointer = _ptr(properties_pointer, prop_ordinal)
            if not isinstance(prop, dict):
                reader.issue("cross_reference_invalid", prop_pointer, "cross_references")
                continue
            projected.append({"ordinal": prop_ordinal, "pointer": prop_pointer,
                "key": reader.field(prop, "key", _ptr(prop_pointer, "key"), "cross_references"),
                "value": reader.field(prop, "value", _ptr(prop_pointer, "value"), "cross_references")})
        items.append({"ordinal": ordinal, "pointer": item_pointer, "database": database,
            "identifier": identifier, "properties_state": properties_state, "properties": projected,
            "evidence_pointers": [e["pointer"] for e in evidence["items"] if e["owner_pointer"] == item_pointer]})
    return {"state": state, "items": items}


def _legacy_publication(row, pointer, reader):
    description_pointer = _ptr(pointer, "proteinDescription")
    _, description = reader.container(row, "proteinDescription", dict, description_pointer, "metadata")
    candidates = []
    recommended_pointer = _ptr(description_pointer, "recommendedName")
    state, recommended = reader.container(description, "recommendedName", dict, recommended_pointer, "metadata")
    if state == "present" and recommended:
        candidates.append((recommended, recommended_pointer))
    submissions_pointer = _ptr(description_pointer, "submissionNames")
    _, submissions = reader.container(description, "submissionNames", list, submissions_pointer, "metadata")
    candidates.extend((raw, _ptr(submissions_pointer, ordinal)) for ordinal, raw in enumerate(submissions))
    source_name, name_pointer, ecs, ec_pointers = None, None, [], []
    for ordinal, (raw, candidate_pointer) in enumerate(candidates):
        if not isinstance(raw, dict):
            reader.issue("field_type_invalid", candidate_pointer, "metadata")
            continue
        full_pointer = _ptr(candidate_pointer, "fullName")
        _, full_name = reader.container(raw, "fullName", dict, full_pointer, "metadata")
        name = reader.field(full_name, "value", _ptr(full_pointer, "value"), "metadata")
        if ordinal == 0:
            source_name, name_pointer = name["value"], name["pointer"]
        numbers_pointer = _ptr(candidate_pointer, "ecNumbers")
        _, numbers = reader.container(raw, "ecNumbers", list, numbers_pointer, "metadata")
        for ec_ordinal, number in enumerate(numbers):
            number_pointer = _ptr(numbers_pointer, ec_ordinal)
            if not isinstance(number, dict):
                reader.issue("field_type_invalid", number_pointer, "metadata")
                continue
            ec = reader.field(number, "value", _ptr(number_pointer, "value"), "metadata")
            if ec["state"] == "present":
                ecs.append(ec["value"])
                ec_pointers.append(ec["pointer"])
    return {"source_name": source_name, "source_name_pointer": name_pointer,
            "source_ec_numbers": ecs, "source_ec_number_pointers": ec_pointers,
            "interpretation": "external_annotation_not_target_experiment"}


def _header_fields(response_headers, reader):
    if response_headers is not None and not isinstance(response_headers, dict):
        raise ValueError("uniprot_response_headers_invalid")
    headers = {}
    conflicts = set()
    for key, value in (response_headers or {}).items():
        if not isinstance(key, str):
            raise ValueError("uniprot_response_headers_invalid")
        name = key.lower()
        if name in headers and headers[name] != value:
            conflicts.add(name)
        headers[name] = value
    fields = {}
    for name, native in (("total_results", "x-total-results"),
                         ("release", "x-uniprot-release"),
                         ("release_date", "x-uniprot-release-date")):
        pointer = "/headers/" + native
        raw = headers.get(native, _MISSING)
        state = ("absent" if raw is _MISSING else "null" if raw is None
                 else "present" if isinstance(raw, str) else "invalid")
        if native in conflicts:
            state = "invalid"
        if name == "total_results" and state == "present":
            if re.fullmatch(r"[0-9]+", raw, re.ASCII):
                try:
                    raw = int(raw)
                except ValueError:
                    state = "invalid"
            else:
                state = "invalid"
        if state == "invalid":
            code = ("total_results_invalid" if name == "total_results" else
                    "release_conflict" if native in conflicts else "field_type_invalid")
            reader.issue(code, pointer, "pagination")
        fields[name] = {"state": state, "value": raw if state == "present" else None,
                        "pointer": pointer}
    return headers, conflicts, fields


def _link_parts(link):
    # Link URLs and quoted parameter values may contain commas. A string split
    # would silently turn a single native URL into unrelated continuation data.
    parts, start, angle, quote, escaped = [], 0, False, False, False
    for index, char in enumerate(link):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
        elif angle:
            if char == ">":
                angle = False
            elif char == "<":
                raise ValueError("invalid_link")
        elif char == "<":
            angle = True
        elif char == '"':
            quote = True
        elif char == ",":
            parts.append(link[start:index])
            start = index + 1
    if angle or quote:
        raise ValueError("invalid_link")
    parts.append(link[start:])
    return parts


def _link_selection(address):
    """Read only parameters actually supplied by a native continuation URL.

    A Link may supply just the opaque cursor. The selected operation still owns
    its original query/size; omitted Link parameters neither replace those nor
    establish new parameter values.
    """
    url = urlsplit(address)
    if (address != address.strip() or url.scheme != "https" or url.netloc != "rest.uniprot.org" or
            url.path != "/uniprotkb/search" or "#" in address or
            any(ord(char) < 32 or ord(char) == 127 for char in address) or
            re.search(r"%(?![0-9A-Fa-f]{2})", url.query)):
        raise ValueError("invalid_link")
    pairs = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True, errors="strict")
    selected = dict(pairs)
    if (len(pairs) != len(selected) or set(selected) - {"query", "size", "cursor", "format"} or
            not selected.get("cursor", "").strip() or
            "query" in selected and not selected["query"].strip() or
            "format" in selected and selected["format"] != "json"):
        raise ValueError("invalid_link")
    if "size" in selected:
        if not re.fullmatch(r"[0-9]+", selected["size"], re.ASCII):
            raise ValueError("invalid_link")
        selected["size"] = _size(int(selected["size"]))
    return selected


def _link_relations(attributes):
    # Malformed rel syntax is unknown/invalid continuation metadata, never
    # proof of an absent next page. Parse every parameter before using rel.
    parameter = re.compile(r'''\s*;\s*([!#$%&'*+.^_`|~0-9A-Za-z-]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([!#$%&'*+.^_`|~0-9A-Za-z:/?-]+))\s*''')
    offset, relations = 0, []
    while offset < len(attributes):
        match = parameter.match(attributes, offset)
        if not match:
            raise ValueError("invalid_link")
        if match[1].lower() == "rel":
            value = re.sub(r"\\(.)", r"\1", match[2]) if match[2] is not None else match[3]
            if not value.strip():
                raise ValueError("invalid_link")
            relations.append(value)
        offset = match.end()
    if len(relations) > 1:
        raise ValueError("invalid_link")
    return relations[0].split() if relations else []


def _next_page(headers, conflicts, request, operation, available, reader):
    if operation == "record":
        return {"next_state": "not_applicable", "next_cursor": None, "next_url": None}
    out = {"next_state": "unknown" if not available else "absent",
           "next_cursor": None, "next_url": None}
    if not available or "link" not in headers:
        return out
    link = headers["link"]
    try:
        if not isinstance(link, str) or not link.strip() or "link" in conflicts:
            raise ValueError("invalid_link")
        next_urls = []
        for part in _link_parts(link):
            match = re.fullmatch(r"\s*<([^<>]+)>\s*((?:;.*)?)", part)
            if not match:
                raise ValueError("invalid_link")
            if "next" in _link_relations(match[2]):
                next_urls.append(match[1])
        if not next_urls:
            return out
        if len(next_urls) != 1:
            raise ValueError("invalid_link")
        out["next_url"] = next_urls[0]
        selected = _link_selection(out["next_url"])
        if request is not None:
            if (request["operation"] != "search" or
                    "query" in selected and selected["query"] != request["query"] or
                    "size" in selected and "size" in request and selected["size"] != request["size"]):
                reader.issue("link_query_conflict", "/headers/link", "pagination")
                out["next_state"] = "invalid"
                return out
        out.update(next_state="present", next_cursor=selected["cursor"])
    except ValueError:
        out["next_state"] = "invalid"
        reader.issue("link_invalid", "/headers/link", "pagination")
    return out


def _whole_query_complete(page):
    if page["operation"] != "search":
        return None
    request = page["effective_request"]
    if request is None:
        return None
    if "cursor" in request or page["next_state"] == "present":
        return False
    if (page["response_body_state"] == "complete_json" and
            page["next_state"] == "absent" and page["pagination_metadata_available"] and
            page["total_results"]["state"] == "present" and
            not any(issue["effect"] != "qualification" for issue in page["issues"])):
        total, count = page["total_results"]["value"], page["native_record_count"]
        if total == count:
            return True
        if count is not None and total > count:
            return False
    return None


def _projection_state(issues):
    if any(issue["effect"] == "page_unusable" for issue in issues):
        return "invalid"
    if any(issue["effect"] in {"record_unpublishable", "field_partial"} for issue in issues):
        return "partial"
    return "complete"


def parse_uniprot_native(content: bytes, *, request: dict | None,
                         response_headers: dict | None) -> dict:
    """Project one retained JSON body and observed headers without acquisition.

    request=None is unavailable request evidence. The envelope may identify its
    shape but can never supply an invented requested accession/query/cursor.
    """
    if not isinstance(content, bytes):
        raise ValueError("uniprot_native_bytes_required")
    request = _canonical_request(request)
    reader = _Reader()
    operation = request["operation"] if request is not None else "unknown"
    body_state, native_count, rows = "complete_json", None, []
    try:
        def invalid_constant(value):
            raise ValueError("non_json_number")
        body = json.loads(content, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        body_state = "invalid_json"
        reader.issue("invalid_json", "", "envelope", "page_unusable")
    else:
        if isinstance(body, dict) and isinstance(body.get("results"), list):
            envelope_operation, native_count = "search", len(body["results"])
            rows = [(ordinal, "/results/" + str(ordinal), raw)
                    for ordinal, raw in enumerate(body["results"])]
        elif (isinstance(body, dict) and "results" not in body and
              (operation == "record" or "primaryAccession" in body)):
            envelope_operation, native_count, rows = "record", 1, [(0, "", body)]
        else:
            envelope_operation = "unknown"
            body_state = "invalid_envelope"
            reader.issue("invalid_envelope", "", "envelope", "page_unusable")
        if operation == "unknown":
            operation = envelope_operation
        elif envelope_operation != "unknown" and envelope_operation != operation:
            reader.issue("request_mismatch", "", "request", "page_unusable")
            rows = []
    if request is None:
        reader.issue("native_request_unverified", "", "request", "qualification")
    headers, conflicts, header_fields = _header_fields(response_headers, reader)
    next_page = _next_page(headers, conflicts, request, operation, response_headers is not None, reader)
    page = {"operation": operation, "effective_request": request,
        "response_body_state": body_state, "native_record_count": native_count,
        "publishable_record_count": 0, "projection_state": "complete",
        "pagination_metadata_available": response_headers is not None,
        **next_page, **header_fields,
        "selection_extent": {"record": "one_record", "search": "one_selected_page",
                             "unknown": "not_established"}[operation],
        "whole_query_complete": None, "issues": reader.issues,
        "request_verification": "caller_supplied" if request is not None else "unknown"}
    records, all_issues = [], list(reader.issues)
    for ordinal, pointer, raw in rows:
        record_reader = _Reader(ordinal)
        if not isinstance(raw, dict):
            record_reader.issue("record_not_object", pointer, "identity", "record_unpublishable")
            all_issues.extend(record_reader.issues)
            continue
        primary = raw.get("primaryAccession")
        if not isinstance(primary, str) or not primary.strip():
            record_reader.issue("primary_accession_missing", _ptr(pointer, "primaryAccession"),
                                "identity", "record_unpublishable")
            all_issues.extend(record_reader.issues)
            continue
        secondary = record_reader.field(raw, "secondaryAccessions", _ptr(pointer, "secondaryAccessions"),
                                        "identity", list)
        requested = request["accession"] if request is not None and operation == "record" else None
        relation = "unverified" if request is None else "search_member"
        if requested is not None:
            if requested == primary:
                relation = "primary"
            elif requested in (secondary["value"] or []):
                relation = "secondary"
            else:
                record_reader.issue("accession_unmatched", _ptr(pointer, "primaryAccession"),
                                    "identity", "record_unpublishable")
                all_issues.extend(record_reader.issues)
                continue
        identity = {"record_ordinal": ordinal, "record_pointer": pointer, "primary_accession": primary,
                    "requested_accession": requested, "accession_relation": relation,
                    "secondary_accessions": secondary}
        metadata = _metadata(raw, pointer, record_reader)
        sequence = _sequence(raw, pointer, record_reader)
        taxon = _taxon(raw, pointer, record_reader)
        evidence = _evidence(raw, pointer, record_reader)
        features = _features(raw, pointer, record_reader, identity, sequence, evidence)
        cross_references = _cross_references(raw, pointer, record_reader, evidence)
        legacy = _legacy_publication(raw, pointer, record_reader)
        records.append({"identity": identity, "metadata": metadata, "sequence": sequence,
                        "taxon": taxon, "features": features, "evidence": evidence,
                        "cross_references": cross_references, "issues": record_reader.issues,
                        "legacy_publication": legacy})
        all_issues.extend(record_reader.issues)
    page["publishable_record_count"] = len(records)
    page["projection_state"] = _projection_state(all_issues)
    page["whole_query_complete"] = _whole_query_complete(page)
    result = {"version": "uniprot_native_page_v1", "content_sha256": hashlib.sha256(content).hexdigest(),
              "page": page, "records": records, "issues": all_issues}
    validate_uniprot_projection(result)
    return result


def _require(condition, reason):
    if not condition:
        raise ValueError("uniprot_projection_" + reason)


def _field_pointer(field, pointer):
    _require(field["pointer"] == pointer, "field_pointer_conflict")


def _validate_fields(value):
    if isinstance(value, dict):
        if set(value) == {"state", "value", "pointer"}:
            _require((value["value"] is not None) == (value["state"] == "present"), "field_state_conflict")
        for child in value.values():
            _validate_fields(child)
    elif isinstance(value, list):
        for child in value:
            _validate_fields(child)


def _validate_order(items, prefix):
    ordinals = [item["ordinal"] for item in items]
    _require(ordinals == sorted(set(ordinals)), "native_ordinal_conflict")
    for item in items:
        _require(item["pointer"] == _ptr(prefix, item["ordinal"]), "native_pointer_conflict")


def _validate_record(record, page):
    identity = record["identity"]
    ordinal, pointer = identity["record_ordinal"], identity["record_pointer"]
    _require(bool(identity["primary_accession"].strip()), "primary_accession_invalid")
    _require(ordinal < page["native_record_count"], "record_ordinal_conflict")
    _require(pointer == ("" if page["operation"] == "record" else "/results/" + str(ordinal)),
             "record_pointer_conflict")
    if page["operation"] == "record":
        _require(ordinal == 0, "record_ordinal_conflict")
    secondary = identity["secondary_accessions"]
    _field_pointer(secondary, _ptr(pointer, "secondaryAccessions"))
    request = page["effective_request"]
    requested = request["accession"] if request is not None and page["operation"] == "record" else None
    _require(identity["requested_accession"] == requested, "requested_accession_conflict")
    expected_relation = "unverified" if request is None else "search_member"
    if requested is not None:
        expected_relation = ("primary" if identity["primary_accession"] == requested else
                             "secondary" if requested in (secondary["value"] or []) else None)
    _require(identity["accession_relation"] == expected_relation, "accession_relation_conflict")
    metadata = record["metadata"]
    for name, native in (("uniprot_id", "uniProtkbId"), ("entry_type", "entryType"),
                         ("protein_existence", "proteinExistence"),
                         ("first_public_date", "entryAudit/firstPublicDate"),
                         ("last_annotation_update_date", "entryAudit/lastAnnotationUpdateDate"),
                         ("last_sequence_update_date", "entryAudit/lastSequenceUpdateDate"),
                         ("entry_version", "entryAudit/entryVersion"),
                         ("sequence_version", "entryAudit/sequenceVersion")):
        _field_pointer(metadata[name], pointer + "/" + native)
    for name in ("entry_version", "sequence_version"):
        _require(metadata[name]["value"] is None or metadata[name]["value"] > 0, "version_invalid")
    _require([s["name"] for s in metadata["native_sections"]] == list(_SECTIONS), "native_sections_conflict")
    for section in metadata["native_sections"]:
        _require(section["pointer"] == _ptr(pointer, section["name"]), "native_section_pointer_conflict")
    sequence = record["sequence"]
    for name, native in (("value", "value"), ("reported_length_aa", "length"),
                         ("md5", "md5"), ("crc64", "crc64")):
        _field_pointer(sequence[name], pointer + "/sequence/" + native)
    value = sequence["value"]["value"]
    _require(value is None or _PROTEIN.fullmatch(value) is not None, "sequence_invalid")
    observed = len(value) if value is not None else None
    _require(sequence["observed_length_aa"] == observed, "observed_length_conflict")
    reported = sequence["reported_length_aa"]["value"]
    relation = "unavailable" if observed is None or reported is None else "agree" if observed == reported else "conflict"
    _require(sequence["length_relation"] == relation, "length_relation_conflict")
    if sequence["state"] != "present":
        _require(all(sequence[name]["state"] == "absent" for name in
                     ("value", "reported_length_aa", "md5", "crc64")), "sequence_container_conflict")
    taxon = record["taxon"]
    for name, native in (("taxon_id", "taxonId"), ("scientific_name", "scientificName"),
                         ("common_name", "commonName"), ("synonyms", "synonyms"), ("lineage_names", "lineage")):
        _field_pointer(taxon[name], pointer + "/organism/" + native)
        if taxon["state"] != "present":
            _require(taxon[name]["state"] == "absent", "taxon_container_conflict")
    _require(taxon["taxon_id"]["value"] is None or taxon["taxon_id"]["value"] > 0, "taxon_id_invalid")
    evidence = record["evidence"]["items"]
    by_pointer = {item["pointer"]: item for item in evidence}
    _require(len(by_pointer) == len(evidence), "evidence_pointer_conflict")
    owners = {}
    for item in evidence:
        owner = item["owner_pointer"]
        _require(owner == pointer or owner.startswith(pointer + "/"), "evidence_owner_conflict")
        _require(item["pointer"] == _ptr(_ptr(owner, "evidences"), item["ordinal"]), "evidence_pointer_conflict")
        owners.setdefault(owner, []).append(item)
        for name, native in (("evidence_code", "evidenceCode"), ("source", "source"), ("source_id", "id")):
            _field_pointer(item[name], _ptr(item["pointer"], native))
    for owner, items in owners.items():
        _validate_order(items, _ptr(owner, "evidences"))
    for group in ("evidence", "features", "cross_references"):
        if record[group]["state"] != "present":
            _require(not record[group]["items"], "container_state_conflict")
    _validate_order(record["features"]["items"], _ptr(pointer, "features"))
    for feature in record["features"]["items"]:
        fp = feature["pointer"]
        _field_pointer(feature["type"], _ptr(fp, "type"))
        _field_pointer(feature["feature_id"], _ptr(fp, "featureId"))
        for name in ("start", "end"):
            position = feature[name]
            for field in ("value", "modifier"):
                _field_pointer(position[field], fp + "/location/" + name + "/" + field)
                if position["state"] != "present":
                    _require(position[field]["state"] == "absent", "position_state_conflict")
            _require(position["value"]["value"] is None or position["value"]["value"] > 0,
                     "position_value_invalid")
        native_id = feature["native_sequence_id"]
        _field_pointer(native_id, fp + "/location/sequence")
        if native_id["state"] == "present" and native_id["value"] != identity["primary_accession"]:
            binding = "explicit_other_sequence"
        elif value is not None and (native_id["state"] == "absent" or
                                    native_id["state"] == "present" and native_id["value"] == identity["primary_accession"]):
            binding = "entry_sequence"
        else:
            binding = "unresolved"
        _require(feature["sequence_binding"] == binding, "feature_sequence_conflict")
        start, end = feature["start"]["value"]["value"], feature["end"]["value"]["value"]
        exact = feature["start"]["modifier"]["value"] == feature["end"]["modifier"]["value"] == "EXACT"
        interval = ([start - 1, end] if binding == "entry_sequence" and exact and
                    start is not None and end is not None and start <= end <= observed else None)
        _require(feature["exact_interval_0based_half_open"] == interval, "feature_interval_conflict")
        _require(feature["evidence_pointers"] == [e["pointer"] for e in evidence if e["owner_pointer"] == fp],
                 "feature_evidence_conflict")
    _validate_order(record["cross_references"]["items"], _ptr(pointer, "uniProtKBCrossReferences"))
    for xref in record["cross_references"]["items"]:
        xp = xref["pointer"]
        _field_pointer(xref["database"], _ptr(xp, "database"))
        _field_pointer(xref["identifier"], _ptr(xp, "id"))
        _validate_order(xref["properties"], _ptr(xp, "properties"))
        if xref["properties_state"] != "present":
            _require(not xref["properties"], "property_state_conflict")
        for prop in xref["properties"]:
            for field in ("key", "value"):
                _field_pointer(prop[field], _ptr(prop["pointer"], field))
        _require(xref["evidence_pointers"] == [e["pointer"] for e in evidence if e["owner_pointer"] == xp],
                 "xref_evidence_conflict")
    legacy = record["legacy_publication"]
    _require(legacy["source_name"] is None or legacy["source_name_pointer"] is not None,
             "legacy_name_pointer_missing")
    _require(len(legacy["source_ec_numbers"]) == len(legacy["source_ec_number_pointers"]),
             "legacy_ec_pointer_count_conflict")
    prefix = re.escape(pointer + "/proteinDescription/") + r"(?:recommendedName|submissionNames/[0-9]+)"
    if legacy["source_name_pointer"] is not None:
        _require(re.fullmatch(prefix + r"/fullName/value", legacy["source_name_pointer"]) is not None,
                 "legacy_name_pointer_conflict")
    for ec_pointer in legacy["source_ec_number_pointers"]:
        _require(re.fullmatch(prefix + r"/ecNumbers/[0-9]+/value", ec_pointer) is not None,
                 "legacy_ec_pointer_conflict")
    for issue in record["issues"]:
        _require(issue["record_ordinal"] == ordinal and issue["effect"] in {"field_partial", "qualification"},
                 "record_issue_conflict")


def validate_uniprot_projection(parsed: dict) -> None:
    """Validate the closed shape and relational consistency, without acquisition.

    Native bytes remain a separate operand: this validator cannot authenticate a
    response or prove a projection's values against bytes that it was not given.
    The legacy compatibility helper additionally checks the retained digest.
    """
    error = next(_PAGE_VALIDATOR.iter_errors(parsed), None)
    if error is not None:
        raise ValueError("uniprot_projection_schema_invalid") from error
    _validate_fields(parsed)
    page = parsed["page"]
    request = _canonical_request(page["effective_request"])
    _require(page["request_verification"] == ("unknown" if request is None else "caller_supplied"),
             "request_verification_conflict")
    if request is not None:
        _require(request["operation"] == page["operation"], "operation_conflict")
    _require(page["selection_extent"] == {"record": "one_record", "search": "one_selected_page",
             "unknown": "not_established"}[page["operation"]], "selection_extent_conflict")
    if page["response_body_state"] != "complete_json":
        _require(page["native_record_count"] is None and not parsed["records"], "invalid_envelope_count_conflict")
    if parsed["records"]:
        _require(page["native_record_count"] is not None and page["operation"] != "unknown", "record_count_unknown")
    _require(page["publishable_record_count"] == len(parsed["records"]), "publishable_count_conflict")
    ordinals = [record["identity"]["record_ordinal"] for record in parsed["records"]]
    _require(ordinals == sorted(set(ordinals)), "record_ordinal_conflict")
    for field, native in (("total_results", "x-total-results"), ("release", "x-uniprot-release"),
                           ("release_date", "x-uniprot-release-date")):
        _field_pointer(page[field], "/headers/" + native)
        if not page["pagination_metadata_available"]:
            _require(page[field]["state"] == "absent", "unobserved_header_conflict")
    if page["next_state"] == "present":
        _require(page["pagination_metadata_available"] and page["next_url"] is not None and
                 page["next_cursor"] is not None and page["operation"] != "record", "next_page_conflict")
        selected = _link_selection(page["next_url"])
        _require(selected["cursor"] == page["next_cursor"], "next_cursor_conflict")
        if request is not None:
            _require(("query" not in selected or selected["query"] == request["query"]) and
                     ("size" not in selected or "size" not in request or selected["size"] == request["size"]),
                     "next_request_conflict")
    else:
        _require(page["next_cursor"] is None, "next_cursor_conflict")
    _require(page["projection_state"] == _projection_state(parsed["issues"]), "projection_state_conflict")
    _require(page["whole_query_complete"] == _whole_query_complete(page), "whole_query_complete_conflict")
    for issue in page["issues"]:
        _require(issue["record_ordinal"] is None and issue in parsed["issues"], "page_issue_conflict")
    for issue in parsed["issues"]:
        ordinal = issue["record_ordinal"]
        if ordinal is None:
            _require(issue in page["issues"], "page_issue_conflict")
        else:
            _require(page["native_record_count"] is not None and ordinal < page["native_record_count"],
                     "issue_ordinal_conflict")
            prefix = "" if page["operation"] == "record" else "/results/" + str(ordinal)
            _require(issue["pointer"] == prefix or issue["pointer"].startswith(prefix + "/"),
                     "issue_pointer_conflict")
    for record in parsed["records"]:
        _validate_record(record, page)
        expected_issues = [issue for issue in parsed["issues"]
                           if issue["record_ordinal"] == record["identity"]["record_ordinal"]]
        _require(record["issues"] == expected_issues, "record_issue_conflict")


def _resolve_native(body, pointer):
    value = body
    if pointer:
        for token in pointer[1:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def legacy_uniprot_records(parsed: dict, content: bytes) -> list[dict]:
    """Project old parser keys using the single native parser's decisions.

    Raw sections are copied verbatim from matching retained bytes. This helper
    does not independently reinterpret accession, sequence, names or EC values.
    """
    validate_uniprot_projection(parsed)
    if not isinstance(content, bytes) or hashlib.sha256(content).hexdigest() != parsed["content_sha256"]:
        raise ValueError("uniprot_native_content_digest_conflict")
    if not parsed["records"]:
        return []
    body = json.loads(content)
    records = []
    for record in parsed["records"]:
        raw = _resolve_native(body, record["identity"]["record_pointer"])
        legacy = record["legacy_publication"]
        records.append({"accession": record["identity"]["primary_accession"],
            "entry_type": record["metadata"]["entry_type"]["value"],
            "sequence": record["sequence"]["value"]["value"],
            "taxon_id": record["taxon"]["taxon_id"]["value"],
            "organism": record["taxon"]["scientific_name"]["value"],
            "source_name": legacy["source_name"], "source_ec_numbers": list(legacy["source_ec_numbers"]),
            "source_features": raw.get("features", []), "source_comments": raw.get("comments", []),
            "source_references": raw.get("references", []),
            "source_cross_references": raw.get("uniProtKBCrossReferences", []),
            "entry_audit": raw.get("entryAudit", {}), "interpretation": legacy["interpretation"]})
    return records
