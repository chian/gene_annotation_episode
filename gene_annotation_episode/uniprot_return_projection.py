"""Project explicitly selected facts from one authenticated UniProt publication.

The caller owns receipt authentication and material access. This module neither
acquires nor grants anything: grants below are only requested descriptors. The
native parser/publication remains the authority for its measurements. Retained
JSON is decoded to address selected leaves and original collection positions,
including positions that the parser could not publish.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from jsonschema import Draft202012Validator

from .uniprot_return_contracts import (
    uniprot_selected_return_schema, validate_uniprot_return_selection,
)


_MISSING = object()
_INVALID = object()
_TOKEN = re.compile(r"[^\s\x00-\x1f\x7f]+\Z")
_ECO = re.compile(r"ECO:[0-9]{7}\Z")
_EC = re.compile(r"(?:[0-9]+|n[0-9]+|-)(?:\.(?:[0-9]+|n[0-9]+|-)){3}\Z")
_ISSUE_KEYS = ("code", "record_ordinal", "pointer", "field", "effect")


def _require(condition, code="selected_value_conflict"):
    if not condition:
        raise ValueError("uniprot_" + code)


def _pointer(parent, token):
    return parent + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _lookup(value, pointer):
    """Address a selected leaf; never search or coerce a native container."""
    if not pointer:
        return value
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if token not in value:
                return _MISSING
            value = value[token]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                return _MISSING
            ordinal = int(token)
            if ordinal >= len(value):
                return _MISSING
            value = value[ordinal]
        else:
            return _INVALID
    return value


def _state(value, expected):
    return ("absent" if value is _MISSING else "null" if value is None else
            "present" if type(value) is expected else "invalid")


def _native_field(value, pointer, expected=str):
    state = _state(value, expected)
    return {"state": state, "value": value if state == "present" else None,
            "pointer": pointer}


def _invalid_json_constant(value):
    raise ValueError("non_json_number")


def _collection(state, count):
    return {"native_state": state, "native_member_count": count,
            "matching_member_count": 0, "indeterminate_member_count": 0,
            "unavailable_member_count": 0, "excluded_member_count": 0, "members": []}


def _add_member(collection, ordinal, pointer, state, value, failures):
    count = {"matched": "matching_member_count", "indeterminate": "indeterminate_member_count",
             "unavailable": "unavailable_member_count", "excluded": "excluded_member_count"}[state]
    collection[count] += 1
    if state != "excluded":
        collection["members"].append({"ordinal": ordinal, "pointer": pointer,
            "selection_state": state, "value": value, "failures": failures})


def _issue(issue, origin, index):
    return {"origin": origin, "original_issue_index": index,
            **{key: deepcopy(issue[key]) for key in _ISSUE_KEYS}}


class _Cells:
    """Build selected cells with their original request-array locations."""

    def __init__(self, page_index, record_index=None, field_index=None):
        self.page_index = page_index
        self.record_index = record_index
        self.field_index = field_index

    def failure(self, code, pointer=None):
        return {"code": code, "page_selection_index": self.page_index,
                "record_selection_index": self.record_index,
                "field_selection_index": self.field_index, "native_pointer": pointer}

    def state_failures(self, state, pointer, *, invalid="field_invalid"):
        return ([] if state == "present" else
                [self.failure(invalid if state == "invalid" else "field_" + state, pointer)])

    def token(self, field, pattern=_TOKEN):
        state, value, pointer = field["state"], field["value"], field["pointer"]
        failures = self.state_failures(state, pointer)
        exact = state == "present" and isinstance(value, str) and pattern.fullmatch(value) is not None
        if state == "present" and not exact:
            failures.append(self.failure("token_not_representable", pointer))
        return {"native_state": state, "representation": "exact" if exact else "unavailable",
                "value": value if exact else None, "pointer": pointer}, failures

    def integer(self, field, unit, origin="native"):
        return {"native_state": field["state"], "value": field["value"],
                "pointer": field["pointer"], "origin": origin, "unit": unit}, self.state_failures(
                    field["state"], field["pointer"])

    def text(self, field, window):
        state, value, pointer = field["state"], field["value"], field["pointer"]
        offset, limit = window["offset"], window["limit"]
        out = {"native_state": state, "pointer": pointer,
               "owner_pointer": pointer.rsplit("/", 1)[0], "offset": offset, "limit": limit,
               "native_length": None, "start": None, "end": None, "text": None,
               "omitted_prefix": None, "omitted_suffix": None, "extent": "unavailable",
               "unit": "unicode_code_points"}
        if state == "present":
            length = len(value)
            start, end = min(offset, length), min(offset + limit, length)
            extent = ("offset_past_end" if offset > length else
                      "empty_value" if length == 0 else
                      "whole_value" if start == 0 and end == length else "window")
            out.update(native_length=length, start=start, end=end, text=value[start:end],
                       omitted_prefix=start, omitted_suffix=length - end, extent=extent)
        return out, self.state_failures(state, pointer, invalid="text_pointer_not_string")

    def reply(self, request, value, failures, *, partial=False):
        return {"request_index": self.field_index, "request": deepcopy(request),
                "status": "unavailable" if value is None else
                          "partial" if partial or failures else "available",
                "value": value, "failures": failures}


class _RecordCells(_Cells):
    def __init__(self, projector, bound, raw, record_index, field_index=None):
        super().__init__(projector.index, record_index, field_index)
        self.projector, self.bound, self.raw = projector, bound, raw
        self.record = bound["record"]
        self.root = self.record["identity"]["record_pointer"]

    def native(self, relative):
        return _native_field(_lookup(self.raw, relative), self.root + relative)

    def checked_field(self, field, pointer):
        """Verify a selected pointer/value association without rerunning P."""
        _require(field["pointer"] == pointer, "selected_owner_conflict")
        raw = _lookup(self.raw, pointer[len(self.root):])
        expected = _native_field(raw, pointer)
        _require(field == expected)
        return field

    def indexed(self, group, pointer):
        items = group["items"]
        result = {item["pointer"]: item for item in items}
        _require(len(result) == len(items), "selected_owner_conflict")
        for item in items:
            _require(item["pointer"] == _pointer(pointer, item["ordinal"]), "selected_owner_conflict")
        return result

    def integer_request(self, request):
        name = request["field"]
        if name == "taxon_id":
            field, unit, origin = self.record["taxon"]["taxon_id"], "taxon_id", "native"
        elif name in {"entry_version", "sequence_version"}:
            field, unit, origin = self.record["metadata"][name], "version", "native"
        elif name == "reported_sequence_length":
            field, unit, origin = self.record["sequence"]["reported_length_aa"], "aa", "native"
        else:
            sequence = self.record["sequence"]
            field = {**sequence["value"], "value": sequence["observed_length_aa"]}
            unit, origin = "aa", "derived"
        value, failures = self.integer(field, unit, origin)
        return self.reply(request, value, failures)

    def token_request(self, request):
        name = request["field"]
        if name == "primary_accession":
            field = {"state": "present", "value": self.record["identity"]["primary_accession"],
                     "pointer": self.root + "/primaryAccession"}
        elif name == "secondary_accession":
            field = self.native("/secondaryAccessions/" + str(request["array_ordinal"]))
        elif name == "uniprot_id":
            field = self.record["metadata"][name]
        else:
            field = self.record["sequence"][{"sequence_md5": "md5", "sequence_crc64": "crc64"}[name]]
        value, failures = self.token(field)
        return self.reply(request, value, failures)

    def ec_request(self, request):
        relative = request["pointer"]
        pointer = self.root + relative
        ec, failures = self.token(self.native(relative), _EC)
        component = re.match(r"/proteinDescription/(?:contains|includes)/[0-9]+", relative)
        value = {"pointer": pointer, "owner_pointer": pointer.rsplit("/", 1)[0],
                 "name_group_pointer": pointer.rsplit("/ecNumbers/", 1)[0],
                 "component_pointer": self.root + component[0] if component else None,
                 "scope": "component" if component else "entry", "ec": ec,
                 "interpretation": "external_annotation_not_target_experiment"}
        return self.reply(request, value, failures)

    def sequence_bytes(self):
        sequence = self.record["sequence"]
        if sequence["value"]["state"] != "present":
            return None
        reference = self.bound["sequence_ref"]
        expected = sequence["value"]["value"].encode("ascii")
        digest = hashlib.sha256(expected).hexdigest()
        _require(reference == "artifact_" + digest, "binding_conflict")
        supplied = self.projector.sequence_contents.get(reference)
        if supplied is None:
            return None
        _require(isinstance(supplied, bytes) and supplied == expected,
                 "artifact_content_conflict")
        _require(len(supplied) == sequence["observed_length_aa"])
        return supplied

    def sequence_request(self, request):
        sequence = self.record["sequence"]
        pointer = sequence["value"]["pointer"]
        length = sequence["observed_length_aa"]
        if length is None:
            return self.reply(request, None, [self.failure("sequence_unavailable", pointer)])
        if request["end"] > length:
            return self.reply(request, None, [self.failure("sequence_window_out_of_range", pointer)])
        content = self.sequence_bytes()
        if content is None:
            return self.reply(request, None, [self.failure("sequence_unavailable", pointer)])
        reported = sequence["reported_length_aa"]
        value = {"start": request["start"], "end": request["end"], "sequence_length": length,
                 "sequence_sha256": hashlib.sha256(content).hexdigest(),
                 "value": content[request["start"]:request["end"]].decode("ascii"),
                 "coordinates": "zero_based_half_open", "unit": "aa",
                 "reported_length_state": reported["state"], "reported_length": reported["value"],
                 "length_relation": sequence["length_relation"]}
        return self.reply(request, value, self.state_failures(reported["state"], reported["pointer"]))

    def evidence(self, selection=None, *, subtree=None):
        """Join original local ordinals to P's exact evidence owner pointers."""
        containers = []
        if subtree is not None or selection["mode"] == "all_record":
            relative = subtree[len(self.root):] if subtree is not None else ""
            stack = [(_lookup(self.raw, relative), self.root + relative)]
            while stack:
                value, pointer = stack.pop()
                if isinstance(value, dict):
                    if "evidences" in value:
                        containers.append((pointer, value["evidences"]))
                    stack.extend((child, _pointer(pointer, key))
                                 for key, child in reversed(list(value.items())))
                elif isinstance(value, list):
                    stack.extend((child, _pointer(pointer, ordinal))
                                 for ordinal, child in reversed(list(enumerate(value))))
        else:
            owner = self.root + selection["owner_pointer"]
            containers = [(owner, _lookup(self.raw, selection["owner_pointer"] + "/evidences"))]
        states = [_state(raw, list) for _, raw in containers]
        state = ("present" if "present" in states else "invalid" if "invalid" in states else
                 "null" if "null" in states else "absent")
        count = (None if any(s in {"null", "invalid"} for s in states) else
                 sum(len(raw) for (_, raw), s in zip(containers, states) if s == "present"))
        collection = _collection(state, count)
        failures = []
        partial = state != "present" or count is None
        published = self.record["evidence"]["items"]
        by_pointer = {item["pointer"]: item for item in published}
        _require(len(published) == len(by_pointer), "selected_owner_conflict")
        if not containers:
            failures.append(self.failure("field_absent", (subtree or self.root) + "/evidences"))
        for (owner, raw), container_state in zip(containers, states):
            pointer = owner + "/evidences"
            failures.extend(self.state_failures(container_state, pointer))
            if container_state != "present":
                continue
            ordinal_filter = (selection["ordinal"] if selection is not None and
                              selection["mode"] == "owner_ordinal" else None)
            if ordinal_filter is not None and ordinal_filter >= len(raw):
                failures.append(self.failure("selected_ordinal_unavailable", _pointer(pointer, ordinal_filter)))
                partial = True
            for ordinal, item in enumerate(raw):
                member_pointer = _pointer(pointer, ordinal)
                if ordinal_filter is not None and ordinal != ordinal_filter:
                    _add_member(collection, ordinal, member_pointer, "excluded", None, [])
                    continue
                if not isinstance(item, dict):
                    _add_member(collection, ordinal, member_pointer, "unavailable", None,
                                [self.failure("field_invalid", member_pointer)])
                    partial = True
                    continue
                native = by_pointer.get(member_pointer)
                _require(native is not None and native["owner_pointer"] == owner and
                         native["ordinal"] == ordinal, "selected_owner_conflict")
                value = {"ordinal": ordinal, "pointer": member_pointer, "owner_pointer": owner}
                member_failures = []
                for target, key, native_key, pattern in (
                        ("eco", "evidence_code", "evidenceCode", _ECO),
                        ("source", "source", "source", _TOKEN),
                        ("source_identifier", "source_id", "id", _TOKEN)):
                    field = self.checked_field(native[key], _pointer(member_pointer, native_key))
                    value[target], errors = self.token(field, pattern)
                    member_failures.extend(errors)
                _add_member(collection, ordinal, member_pointer, "matched", value, member_failures)
                partial |= bool(member_failures)
        return collection, failures, partial

    def position(self, native, pointer):
        _require(native["value"]["pointer"] == pointer + "/value" and
                 native["modifier"]["pointer"] == pointer + "/modifier", "selected_owner_conflict")
        modifier, failures = self.token(native["modifier"])
        failures.extend(self.state_failures(native["state"], pointer))
        failures.extend(self.state_failures(native["value"]["state"], pointer + "/value"))
        return {"native_state": native["state"], "value": native["value"]["value"],
                "value_pointer": native["value"]["pointer"], "value_state": native["value"]["state"],
                "modifier": modifier}, failures

    def feature_value(self, native, request):
        pointer = native["pointer"]
        start, failures = self.position(native["start"], pointer + "/location/start")
        end, errors = self.position(native["end"], pointer + "/location/end")
        failures.extend(errors)
        sequence_id, errors = self.token(native["native_sequence_id"])
        # Native omission explicitly binds to the entry sequence in P. It is
        # not a missing requested position or an unresolved sequence identity.
        if native["native_sequence_id"]["state"] != "absent":
            failures.extend(errors)
        value = {"ordinal": native["ordinal"], "pointer": pointer, "start": start, "end": end,
                 "native_sequence_id": sequence_id, "sequence_binding": native["sequence_binding"],
                 "native_coordinates": "one_based_inclusive",
                 "exact_interval": deepcopy(native["exact_interval_0based_half_open"]),
                 "derived_coordinates": "zero_based_half_open", "unit": "aa",
                 "type_window": None, "description_window": None, "evidence": None}
        partial = False
        for key, leaf in (("type_window", "type"), ("description_window", "description")):
            if request[key] is not None:
                field = (native["type"] if leaf == "type" else
                         self.native(pointer[len(self.root):] + "/description"))
                value[key], errors = self.text(field, request[key])
                failures.extend(errors)
        if request["include_evidence"]:
            value["evidence"], errors, partial = self.evidence(subtree=pointer)
            failures.extend(errors)
        return value, failures, partial or bool(failures)

    def properties(self, native, raw, requests):
        pointer = native["pointer"] + "/properties"
        state = native["properties_state"]
        properties = raw.get("properties", _MISSING)
        _require(state == _state(properties, list))
        published = self.indexed({"items": native["properties"]}, pointer)
        replies = []
        partial = False
        for index, request in enumerate(requests):
            failures = self.state_failures(state, pointer)
            reply = {"request_index": index, "request": deepcopy(request), "native_state": state,
                     "matches": [], "indeterminate_property_count": 0, "failures": failures}
            if state == "present":
                for ordinal, raw_property in enumerate(properties):
                    member_pointer = _pointer(pointer, ordinal)
                    if not isinstance(raw_property, dict):
                        reply["indeterminate_property_count"] += 1
                        failures.append(self.failure("field_invalid", member_pointer))
                        continue
                    prop = published.get(member_pointer)
                    _require(prop is not None and prop["ordinal"] == ordinal, "selected_owner_conflict")
                    key = self.checked_field(prop["key"], member_pointer + "/key")
                    if key["state"] != "present":
                        reply["indeterminate_property_count"] += 1
                        failures.extend(self.state_failures(key["state"], key["pointer"]))
                    elif key["value"] == request["key"]:
                        field = self.checked_field(prop["value"], member_pointer + "/value")
                        value, errors = self.text(field, request["window"])
                        reply["matches"].append({"ordinal": ordinal, "pointer": member_pointer,
                                                 "value": value})
                        failures.extend(errors)
                if not reply["matches"] and not reply["indeterminate_property_count"]:
                    failures.append(self.failure("property_not_found", pointer))
            partial |= bool(failures)
            replies.append(reply)
        return replies, partial

    def xref_value(self, native, raw, request):
        pointer = native["pointer"]
        database, failures = self.token(self.checked_field(native["database"], pointer + "/database"))
        identifier, errors = self.token(self.checked_field(native["identifier"], pointer + "/id"))
        failures.extend(errors)
        properties, partial = self.properties(native, raw, request["properties"])
        value = {"ordinal": native["ordinal"], "pointer": pointer,
                 "database": database, "identifier": identifier,
                 "properties_state": native["properties_state"], "properties": properties,
                 "evidence": None}
        if request["include_evidence"]:
            value["evidence"], errors, evidence_partial = self.evidence(subtree=pointer)
            failures.extend(errors)
            partial |= evidence_partial
        return value, failures, partial or bool(failures)

    def member_request(self, request):
        feature = request["kind"] == "feature_location"
        group = self.record["features" if feature else "cross_references"]
        name = "features" if feature else "uniProtKBCrossReferences"
        pointer = self.root + "/" + name
        raw = self.raw.get(name, _MISSING)
        state = group["state"]
        _require(state == _state(raw, list))
        selector = request["selection"]
        overlap = selector["mode"] == "entry_interval_overlap"
        if overlap:
            length = self.record["sequence"]["observed_length_aa"]
            if length is None:
                return self.reply(request, None, [self.failure("sequence_unavailable", pointer)])
            if selector["end"] > length:
                return self.reply(request, None, [self.failure("sequence_window_out_of_range", pointer)])
        count = len(raw) if state == "present" else 0 if state == "absent" else None
        collection = _collection(state, count)
        failures = self.state_failures(state, pointer)
        partial = state != "present"
        if state != "present":
            return self.reply(request, collection, failures, partial=partial)
        published = self.indexed(group, pointer)
        ordinal_filter = selector["ordinal"] if selector["mode"] == "ordinal" else None
        if ordinal_filter is not None and ordinal_filter >= len(raw):
            failures.append(self.failure("selected_ordinal_unavailable", _pointer(pointer, ordinal_filter)))
            partial = True
        for ordinal, member in enumerate(raw):
            member_pointer = _pointer(pointer, ordinal)
            if ordinal_filter is not None and ordinal_filter != ordinal:
                _add_member(collection, ordinal, member_pointer, "excluded", None, [])
                continue
            if not isinstance(member, dict):
                membership = "indeterminate" if overlap or selector["mode"] == "database" else "unavailable"
                _add_member(collection, ordinal, member_pointer, membership, None,
                            [self.failure("field_invalid", member_pointer)])
                partial = True
                continue
            native = published.get(member_pointer)
            _require(native is not None and native["ordinal"] == ordinal, "selected_owner_conflict")
            membership = "matched"
            if overlap:
                interval = native["exact_interval_0based_half_open"]
                if native["sequence_binding"] == "explicit_other_sequence":
                    membership = "excluded"
                elif interval is None:
                    membership = "indeterminate"
                else:
                    _require(native["sequence_binding"] == "entry_sequence", "selected_owner_conflict")
                    if not (interval[0] < selector["end"] and interval[1] > selector["start"]):
                        membership = "excluded"
            elif selector["mode"] == "database":
                database = self.checked_field(native["database"], member_pointer + "/database")
                membership = ("indeterminate" if database["state"] != "present" else
                              "matched" if database["value"] == selector["database"] else "excluded")
            if membership == "excluded":
                _add_member(collection, ordinal, member_pointer, membership, None, [])
                continue
            value, errors, member_partial = (self.feature_value(native, request) if feature else
                                             self.xref_value(native, member, request))
            _add_member(collection, ordinal, member_pointer, membership, value, errors)
            partial |= member_partial or membership == "indeterminate"
        return self.reply(request, collection, failures, partial=partial)

    def field(self, request):
        kind = request["kind"]
        if kind == "integer":
            return self.integer_request(request)
        if kind == "token":
            return self.token_request(request)
        if kind == "text":
            value, failures = self.text(self.native(request["pointer"]), request)
            return self.reply(request, value, failures)
        if kind == "ec_assignment":
            return self.ec_request(request)
        if kind == "sequence_window":
            return self.sequence_request(request)
        if kind == "evidence":
            value, failures, partial = self.evidence(request["selection"])
            return self.reply(request, value, failures, partial=partial)
        return self.member_request(request)


class _PageProjection(_Cells):
    def __init__(self, publication, content, outer_status, bound_count, errors, qualifications,
                 selection, index, sequence_contents):
        super().__init__(index)
        self.publication, self.page, self.selection = publication, publication["page"], selection
        self.index, self.sequence_contents = index, sequence_contents
        self.errors, self.qualifications = errors, qualifications
        self.outer_status, self.bound_count = outer_status, bound_count
        _require(type(bound_count) is int and bound_count == len(publication["records"]), "binding_conflict")
        _require(outer_status in {"completed", "partial"}, "original_context_conflict")
        _require(isinstance(content, bytes) and hashlib.sha256(content).hexdigest() ==
                 publication["content_sha256"], "artifact_content_conflict")
        _require(publication["native_artifact_ref"] == "artifact_" + publication["content_sha256"],
                 "source_snapshot_conflict")
        self.rows = None
        try:
            body = json.loads(content, parse_constant=_invalid_json_constant)
        except (ValueError, UnicodeError, RecursionError):
            _require(self.page["response_body_state"] == "invalid_json")
        else:
            if isinstance(body, dict) and isinstance(body.get("results"), list):
                self.rows = body["results"]
            elif (isinstance(body, dict) and "results" not in body and
                  (self.page["operation"] == "record" or "primaryAccession" in body)):
                self.rows = [body]
            else:
                _require(self.page["response_body_state"] == "invalid_envelope")
        _require(self.page["native_record_count"] == (len(self.rows) if self.rows is not None else None))
        self.by_ordinal = {}
        for bound in publication["records"]:
            anchor, identity = bound["anchor"], bound["record"]["identity"]
            ordinal = anchor["record_ordinal"]
            _require(type(ordinal) is int and self.rows is not None and 0 <= ordinal < len(self.rows) and
                     ordinal not in self.by_ordinal, "binding_conflict")
            pointer = "" if self.page["operation"] == "record" else "/results/" + str(ordinal)
            raw = self.rows[ordinal]
            _require(isinstance(raw, dict) and anchor["source_ref"] == publication["source_ref"] and
                     anchor["record_pointer"] == identity["record_pointer"] == pointer and
                     ordinal == identity["record_ordinal"] and anchor["primary_accession"] ==
                     identity["primary_accession"] == raw.get("primaryAccession"), "binding_conflict")
            self.by_ordinal[ordinal] = bound

    def pointer(self, ordinal):
        return "" if self.page["operation"] == "record" and ordinal == 0 else "/results/" + str(ordinal)

    def page_field(self, request, index):
        cells = _Cells(self.index, field_index=index)
        name = request["field"]
        if name in {"next_cursor", "next_url"}:
            state = self.page["next_state"]
            if state not in {"present", "absent"}:
                return cells.reply(request, None, [cells.failure("page_field_unavailable", "/headers/link")])
            field = {"state": state, "value": self.page[name] if state == "present" else None,
                     "pointer": "/headers/link"}
        elif name == "effective_query":
            query = (self.page["effective_request"] or {}).get("query", _MISSING)
            field = _native_field(query, "/effective_request/query")
        else:
            field = self.page[name]
        if request["kind"] == "page_integer":
            value, failures = cells.integer(field, "count")
        elif request["kind"] == "page_token":
            value, failures = cells.token(field)
        else:
            value, failures = cells.text(field, request)
        return cells.reply(request, value, failures)

    def issues(self, ordinal, bound=None):
        if ordinal is None:
            native, origin = self.page["issues"], "native_page"
        elif bound is not None:
            native, origin = bound["record"]["issues"], "native_record"
        else:
            native, origin = self.publication["issues"], "native_projection"
        result = [_issue(row, origin, index) for index, row in enumerate(native)
                  if row["record_ordinal"] == ordinal]
        for rows, origin in ((self.errors, "publication_projection"),
                             (self.qualifications, "publication_qualification")):
            result.extend(_issue(row, origin, index) for index, row in enumerate(rows)
                          if row["record_ordinal"] == ordinal)
        return result

    def record_reply(self, request, index, ordinal, *, indeterminate=False):
        cells = _Cells(self.index, index)
        pointer = self.pointer(ordinal)
        bound = self.by_ordinal.get(ordinal)
        if indeterminate:
            state, code = "unavailable", "record_selection_indeterminate"
        elif self.rows is None or self.page["projection_state"] == "invalid":
            state, code = "unavailable", "publication_unavailable"
            pointer = None
        elif ordinal >= len(self.rows):
            state, code = "not_in_response", "record_not_in_response"
            pointer = None
        elif bound is not None:
            state, code = "bound", None
        elif any(issue["record_ordinal"] == ordinal and issue["effect"] == "record_unpublishable"
                 for issue in self.publication["issues"]):
            state, code = "parser_unpublishable", "record_parser_unpublishable"
        else:
            state, code = "binding_omitted", "record_binding_omitted"
        reply = {"record_selection_index": index, "requested_record_ordinal": ordinal,
                 "state": state, "witness": None, "fields": [], "issues": self.issues(ordinal, bound),
                 "sequence_grant_status": "not_requested", "sequence_grant": None,
                 "failures": [cells.failure(code, pointer)] if code else []}
        if state == "bound":
            identity = bound["record"]["identity"]
            reply["witness"] = {"record_id": bound["anchor"]["reference_ref"],
                "record_ordinal": ordinal, "record_pointer": pointer,
                "accession_relation": identity["accession_relation"],
                "sequence_artifact_id": bound["sequence_ref"]}
        for field_index, field_request in enumerate(request["fields"]):
            if state == "bound":
                projector = _RecordCells(self, bound, self.rows[ordinal], index, field_index)
                reply["fields"].append(projector.field(field_request))
            else:
                field_cells = _Cells(self.index, index, field_index)
                reply["fields"].append(field_cells.reply(field_request, None,
                    [field_cells.failure(code, pointer)]))
        if request["grant_sequence_artifact"]:
            reply["sequence_grant_status"] = "unavailable"
            if state == "bound":
                projector = _RecordCells(self, bound, self.rows[ordinal], index)
                content = projector.sequence_bytes()
                if content is None:
                    reply["failures"].append(cells.failure("sequence_unavailable", pointer + "/sequence/value"))
                else:
                    reply["sequence_grant_status"] = "available"
                    reply["sequence_grant"] = {"artifact_ref": bound["sequence_ref"],
                        "record_id": bound["anchor"]["reference_ref"], "record_ordinal": ordinal,
                        "sequence_sha256": hashlib.sha256(content).hexdigest(),
                        "length": bound["record"]["sequence"]["observed_length_aa"],
                        "unit": "aa", "molecule": "protein", "meaning": "explicit_full_sequence_artifact"}
        return reply

    def project(self):
        records, failures, selected, indeterminate = [], [], set(), set()
        for index, request in enumerate(self.selection["records"]):
            selector = request["record"]
            cells = _Cells(self.index, index)
            ordinals, unknown = [], set()
            if selector["mode"] == "ordinal":
                ordinals = [selector["ordinal"]]
            elif self.rows is None:
                failures.append(cells.failure("publication_unavailable"))
            elif selector["mode"] == "all_native_records":
                ordinals = list(range(len(self.rows)))
            elif self.page["projection_state"] == "invalid":
                failures.append(cells.failure("publication_unavailable"))
            else:
                for ordinal, raw in enumerate(self.rows):
                    primary = raw.get("primaryAccession") if isinstance(raw, dict) else None
                    if not isinstance(primary, str) or not primary.strip():
                        ordinals.append(ordinal)
                        unknown.add(ordinal)
                    elif primary == selector["accession"]:
                        ordinals.append(ordinal)
                if not ordinals:
                    failures.append(cells.failure("record_selection_no_match"))
            for ordinal in ordinals:
                records.append(self.record_reply(request, index, ordinal, indeterminate=ordinal in unknown))
            selected.update(ordinals)
            indeterminate.update(unknown)
        native = self.publication
        witness = {"source_id": native["source_ref"], "native_artifact_id": native["native_artifact_ref"],
                   "content_sha256": native["content_sha256"], "publication_sha256": hashlib.sha256(
                       json.dumps(native, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                  allow_nan=False).encode("utf-8")).hexdigest()}
        page = self.page
        status = {key: deepcopy(page[key]) for key in (
            "operation", "selection_extent", "response_body_state", "native_record_count",
            "pagination_metadata_available", "next_state", "whole_query_complete", "request_verification")}
        status.update(parser_projection_state=page["projection_state"],
            outer_acquisition_status=self.outer_status, parser_eligible_record_count=page["publishable_record_count"],
            bound_record_count=self.bound_count, record_selection_count=len(self.selection["records"]),
            requested_record_count=len(selected), indeterminate_record_count=len(indeterminate),
            returned_bound_record_count=len({r["requested_record_ordinal"] for r in records if r["state"] == "bound"}),
            unselected_issue_count=sum(row["record_ordinal"] is not None and row["record_ordinal"] not in selected
                for rows in (native["issues"], self.errors, self.qualifications) for row in rows))
        grant = ({"source_ref": native["source_ref"], "native_artifact_id": native["native_artifact_ref"],
                  "content_sha256": native["content_sha256"], "meaning": "explicit_whole_native_source"}
                 if self.selection["grant_source"] else None)
        return {"page_selection_index": self.index, "witness": witness, "status": status,
                "page_fields": [self.page_field(request, index)
                                for index, request in enumerate(self.selection["page_fields"])],
                "records": records, "issues": self.issues(None), "source_grant_status":
                    "available" if grant is not None else "not_requested",
                "source_grant": grant, "failures": failures}


def project_uniprot_page(publication: dict, *, native_content: bytes,
                        outer_status: str, bound_record_count: int,
                        projection_errors: list[dict],
                        projection_qualifications: list[dict],
                        page_selection: dict, page_selection_index: int,
                        sequence_contents: dict[str, bytes]) -> dict:
    """Return the exact PageReply for one already authenticated saved page.

    ``sequence_contents`` contains only the selected sequence artifacts whose
    bytes the host could read. Missing bytes yield explicit unavailability;
    present conflicting bytes are integrity errors. No native parser is called.
    """
    selection = validate_uniprot_return_selection(
        {"version": "uniprot_return_selection_v1", "pages": [page_selection]})
    page_selection = selection["pages"][0]
    _require(page_selection["publication"]["mode"] == "assigned_page", "selection_mode_conflict")
    _require(type(page_selection_index) is int and page_selection_index >= 0, "selection_invalid")
    projector = _PageProjection(publication, native_content, outer_status, bound_record_count,
        projection_errors, projection_qualifications, page_selection, page_selection_index, sequence_contents)
    result = projector.project()
    # The full aggregate's request-array correspondence is checked by C at the
    # host boundary; a pure single-page projection may have any original index.
    schema = uniprot_selected_return_schema(selection)["properties"]["pages"]["items"]
    if next(Draft202012Validator(schema).iter_errors(result), None) is not None:
        raise ValueError("uniprot_selected_value_conflict")
    return result


__all__ = ["project_uniprot_page"]
