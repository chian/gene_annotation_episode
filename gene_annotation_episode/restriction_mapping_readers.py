"""Read retained restriction observations without executing a native search.

This is the common supporting-data numerical authority for both wrapper names.
It preserves raw native integers, distinguishes returned emptiness from missing
work, and derives only explicit source-coordinate components. References here
are operands; callers still own Store/scope/custody validation.
"""
from collections import Counter
from copy import deepcopy
import hashlib

from jsonschema import Draft202012Validator

from .restriction_mapping_contracts import (
    restriction_canonical, restriction_digest, restriction_issue,
    restriction_schema, validate_restriction_record,
)


_NATIVE_SCHEMA = restriction_schema("NativeResult")
_REQUEST_VALIDATOR = Draft202012Validator(_NATIVE_SCHEMA["properties"]["request"])
_SOFTWARE_VALIDATOR = Draft202012Validator(_NATIVE_SCHEMA["properties"]["software"])
_DNA = frozenset("ACGTRYSWKMBDHVN")
_QUALIFICATIONS = frozenset(("association_unavailable", "cut_geometry_unknown",
                            "native_position_meaning_unknown"))


def _valid(kind, value):
    try:
        return validate_restriction_record(kind, value)
    except (ValueError, TypeError, KeyError, RecursionError):
        return None


def _same(left, right):
    try:
        return restriction_canonical(left) == restriction_canonical(right)
    except (ValueError, TypeError, RecursionError):
        return False


def _add(issues, code, phase="read", *, enzyme=None, match=None, position=None):
    issue = restriction_issue(code, phase, enzyme_ordinal=enzyme,
        match_ordinal=match, position_ordinal=position)
    if issue not in issues:
        issues.append(issue)


def _empty(selected):
    return {"version": "restriction_mapping_result_v1", "native_sha256": None,
        "selected_sequence": selected, "native_sequence": None,
        "binding_status": "unavailable", "topology": None,
        "enzyme_selection": None, "catalog_identity": None,
        "population": {"selected_enzyme_count": None, "attempted_enzyme_count": 0,
            "returned_enzyme_count": 0, "complete_empty_enzyme_count": 0,
            "recognition_match_count": None},
        "enzyme_rows": [], "unassociated_match_calls": [],
        "status": "unavailable", "issues": []}


def _result_row(catalog_row):
    return {"catalog_ordinal": catalog_row["ordinal"], "name": catalog_row["name"],
        "catalog_row": deepcopy(catalog_row), "search_state": "invalid",
        "position_meaning": catalog_row["position_meaning"],
        "native_search_positions_1based": None, "returned_position_count": None,
        "recognition_match_count": None, "recognition_events": None,
        "positions": None, "issues": []}


def _position(value, ordinal, catalog, *, topology, length, attributable):
    row = {"position_ordinal": ordinal, "native_position": value,
        "watson_boundary_0based": None, "crick_boundary_0based": None,
        "watson_canonical_boundary_0based": None,
        "crick_canonical_boundary_0based": None,
        "geometry_state": "unavailable" if not attributable else "unknown",
        "recognition_association": "not_recorded", "recognition_event_ordinal": None}
    if (not attributable or catalog["position_meaning"] != "first_base_after_cut_1based"
            or type(catalog["native_ovhg"]) is not int):
        return row
    watson, crick = value - 1, value - catalog["native_ovhg"] - 1
    row.update(watson_boundary_0based=watson, crick_boundary_0based=crick,
        geometry_state="known")
    if topology == "circular":
        row.update(watson_canonical_boundary_0based=watson % length,
            crick_canonical_boundary_0based=crick % length)
    else:
        row.update(watson_canonical_boundary_0based=watson if 0 <= watson <= length else None,
            crick_canonical_boundary_0based=crick if 0 <= crick <= length else None)
    return row


def _recognition_event(match, call, catalog, *, topology, sequence):
    """Interpret observed native groups; this performs no pattern matching."""
    groups = {row["name"]: row["text"] for row in match["groups"]}
    orientation = "unknown"
    group_text = None
    if catalog["symmetry"] == "palindromic":
        orientation = "palindromic"
        group_text = groups.get(catalog["name"])
    elif catalog["symmetry"] == "nonpalindromic" and catalog["name"] in groups:
        orientation = "forward" if groups[catalog["name"]] else "reverse"
        if orientation == "forward":
            group_text = groups[catalog["name"]]
        else:
            nonempty = [text for name, text in groups.items()
                        if name != catalog["name"] and text is not None]
            if len(nonempty) == 1:
                group_text = nonempty[0]
    start, size, length = match["native_start_1based"] - 1, catalog["size_nt"], len(sequence)
    end = start + size
    extension = 0 if topology == "linear" else min(size - 1, length)
    available = sequence if topology == "linear" else sequence + sequence[:max(extension, 0)]
    span_ok = (size > 0 and 0 <= start < length and end <= len(available)
               and type(group_text) is str and len(group_text) == size
               and group_text == available[start:end])
    event = {"match_call_ordinal": call["call_ordinal"], "match_ordinal": match["match_ordinal"],
        "native_start_1based": match["native_start_1based"], "orientation": orientation,
        "unwrapped_span_0based": [start, end] if span_ok else None,
        "segments": None, "crosses_origin": None, "native_groups": deepcopy(match["groups"])}
    if span_ok:
        event["segments"] = [{"start": start, "end": min(end, length)}]
        if end > length:
            event["segments"].append({"start": 0, "end": end - length})
        event["crosses_origin"] = end > length
    return event


def _match_events(native, catalog_rows, *, topology, sequence, context_ok):
    events = {ordinal: None for ordinal in catalog_rows}
    issues = {ordinal: [] for ordinal in catalog_rows}
    unassociated, candidates = [], {ordinal: [] for ordinal in catalog_rows}
    calls = native.get("match_observations")
    if type(calls) is not list:
        return events, issues, unassociated
    declared = Counter(c.get("call_ordinal") for c in calls if type(c) is dict
                       and type(c.get("call_ordinal")) is int)
    for input_ordinal, raw in enumerate(calls):
        # Input index is the original trace ordinal even for a corrupt declared ID.
        if type(raw) is not dict:
            unassociated.append(input_ordinal)
            continue
        header = deepcopy(raw)
        if header.get("state") == "returned":
            header["matches"] = []
        call = _valid("MatchCall", header)
        if (call is None or call["call_ordinal"] != input_ordinal
                or declared[call["call_ordinal"]] != 1):
            unassociated.append(input_ordinal)
            continue
        owners = call["owner_ordinals"]
        expected = [ordinal for ordinal, row in catalog_rows.items()
                    if row is not None and _same(row["native_pattern"], call["native_pattern"])
                    and row["size_nt"] == call["site_size_nt"]]
        if (not context_ok or owners != expected or len(owners) != 1
                or call["linear"] != (topology == "linear")):
            unassociated.append(input_ordinal)
            for ordinal in owners:
                if ordinal in issues:
                    _add(issues[ordinal], "match_owner_ambiguous", "association", enzyme=ordinal)
            continue
        call["matches"] = deepcopy(raw.get("matches"))
        candidates[owners[0]].append(call)
    for ordinal, row in catalog_rows.items():
        if row is None:
            continue
        available = candidates[ordinal]
        if len(available) != 1 or available[0]["state"] != "returned":
            _add(issues[ordinal], "match_capture_unavailable", "capture", enzyme=ordinal)
            continue
        call = available[0]
        matches = call["matches"]
        if type(matches) is not list:
            _add(issues[ordinal], "match_capture_unavailable", "capture", enzyme=ordinal)
            continue
        valid, complete = [], True
        for match_index, raw_match in enumerate(matches):
            match = _valid("Match", raw_match)
            if (match is None or match["match_ordinal"] != match_index
                    or len({g["name"] for g in match["groups"]}) != len(match["groups"])):
                _add(issues[ordinal], "retained_record_conflict", "capture", enzyme=ordinal,
                     match=match_index)
                complete = False
                continue
            event = _recognition_event(match, call, row, topology=topology, sequence=sequence)
            if event["orientation"] == "unknown" or event["segments"] is None:
                _add(issues[ordinal], "retained_record_conflict", "capture", enzyme=ordinal,
                     match=match_index)
                complete = False
            valid.append(event)
        events[ordinal] = (valid, complete)
    return events, issues, sorted(set(unassociated))


def read_restriction_mapping(native, *, selected_sequence, enzyme_catalog):
    """Validate retained input/population joins and return shared typed components.

    Empty native lists are results only for completed valid rows. Malformed rows
    do not erase independently valid rows. Global identity conflicts preserve
    native literals while suppressing attributed geometry and recognition spans.
    """
    selected = validate_restriction_record("SequenceBinding", selected_sequence)
    result = _empty(selected)
    if native is None:
        _add(result["issues"], "native_failure")
        return validate_restriction_record("MappingResult", result)
    try:
        result["native_sha256"] = restriction_digest(native)
    except (ValueError, TypeError, RecursionError):
        _add(result["issues"], "retained_record_conflict")
    if type(native) is not dict or native.get("version") != "restriction_mapping_native_v1":
        result["status"] = "invalid"
        _add(result["issues"], "unsupported_native_version")
        return validate_restriction_record("MappingResult", result)
    issues = result["issues"]
    # The complete validator supplies global structural/relationship checks.
    # Its failure qualifies this record; independently valid rows are still read.
    if _valid("NativeResult", native) is None:
        _add(issues, "retained_record_conflict")
    source_issues = native.get("issues")
    if type(source_issues) is list:
        for raw_issue in source_issues:
            issue = _valid("Issue", raw_issue)
            if issue is None:
                _add(issues, "retained_record_conflict")
            elif issue not in issues:
                issues.append(issue)
    else:
        _add(issues, "retained_record_conflict")
    malformed_top = set(native) != set(_NATIVE_SCHEMA["properties"])
    if malformed_top:
        _add(issues, "retained_record_conflict")
    request = native.get("request")
    request_ok = type(request) is dict and _REQUEST_VALIDATOR.is_valid(request)
    binding = _valid("SequenceBinding", request.get("sequence_binding")) if type(request) is dict else None
    selection = _valid("EnzymeSelection", request.get("enzyme_selection")) if type(request) is dict else None
    if binding is not None:
        result["native_sequence"] = binding
        result["binding_status"] = "matched" if _same(binding, selected) else "conflicting"
    sequence = request.get("sequence") if type(request) is dict else None
    normalized = request.get("normalized_sequence") if type(request) is dict else None
    topology = request.get("topology") if type(request) is dict else None
    sequence_ok = (type(sequence) is str and bool(sequence) and sequence.isascii()
        and set(sequence.upper()) <= _DNA and binding is not None
        and len(sequence) == binding["length_nt"]
        and hashlib.sha256(sequence.encode("utf-8")).hexdigest() == binding["content_sha256"]
        and normalized == sequence.upper())
    if not sequence_ok and binding is not None:
        result["binding_status"] = "conflicting"
    if result["binding_status"] != "matched" or not request_ok or not sequence_ok:
        _add(issues, "sequence_binding_conflict", "input")
    result["topology"] = topology if topology in ("linear", "circular") else None
    result["enzyme_selection"] = selection
    expected = _valid("Catalog", enzyme_catalog)
    actual = native.get("catalog")
    header_ok = (expected is not None and type(actual) is dict
        and set(actual) == set(restriction_schema("Catalog")["properties"])
        and _same({k: v for k, v in actual.items() if k != "enzymes"},
                  {k: v for k, v in expected.items() if k != "enzymes"}))
    if expected is None:
        _add(issues, "catalog_unavailable" if enzyme_catalog is None else "catalog_incompatible", "catalog")
    elif not header_ok:
        _add(issues, "catalog_incompatible", "catalog")
    software = native.get("software")
    software_ok = (type(software) is dict and _SOFTWARE_VALIDATOR.is_valid(software)
        and software["biopython_version"] == "1.88"
        and _valid("FilePin", software["dictionary_file"]) is not None
        and _valid("FilePin", software["native_source_file"]) is not None
        and expected is not None and _same(software["dictionary_file"], expected["dictionary_file"])
        and software["biopython_version"] == expected["biopython_version"])
    if not software_ok:
        _add(issues, "unsupported_native_version" if type(software) is dict
             and software.get("biopython_version") not in (None, "1.88") else "catalog_incompatible", "catalog")
    if expected is None:
        invalid_codes = {"input_invalid", "enzyme_unknown", "unsupported_native_version", "request_conflict"}
        result["status"] = "invalid" if (enzyme_catalog is not None
            or result["binding_status"] == "conflicting"
            or any(issue["code"] in invalid_codes for issue in issues)) else "unavailable"
        return validate_restriction_record("MappingResult", result)
    if header_ok and software_ok:
        result["catalog_identity"] = {"biopython_version": actual["biopython_version"],
            "dictionary_file": deepcopy(actual["dictionary_file"])}
    names, original_catalog_rows = expected["resolved_names"], expected["enzymes"]
    catalog_rows = {}
    actual_rows = actual.get("enzymes") if type(actual) is dict else None
    actual_rows = actual_rows if type(actual_rows) is list else []
    for ordinal, row in enumerate(original_catalog_rows):
        current = _valid("CatalogRow", actual_rows[ordinal]) if ordinal < len(actual_rows) else None
        catalog_rows[ordinal] = current if header_ok and _same(current, row) else None
        if catalog_rows[ordinal] is None:
            _add(issues, "catalog_incompatible", "catalog", enzyme=ordinal)
    catalog_complete = header_ok and len(actual_rows) == len(original_catalog_rows) and all(
        row is not None for row in catalog_rows.values())
    if catalog_complete:
        result["population"]["selected_enzyme_count"] = len(names)
    if not _same(selection, expected["selection"]):
        _add(issues, "request_conflict", "input")
        header_ok = False
    context_ok = (result["binding_status"] == "matched" and request_ok and sequence_ok
                  and header_ok and software_ok and topology in ("linear", "circular"))
    batch_order = native.get("native_batch_member_order")
    order_ok = (type(batch_order) is list and all(type(n) is str for n in batch_order)
        and len(batch_order) == len(set(batch_order)) == len(names) and set(batch_order) == set(names))
    if not order_ok:
        _add(issues, "native_mapping_incomplete", "association")
    batch_state = native.get("batch_state")
    if batch_state not in ("not_started", "returned", "failed"):
        _add(issues, "retained_record_conflict")
    if batch_state == "returned" and not _same(native.get("native_mapping_order"), batch_order):
        _add(issues, "retained_record_conflict", "association")
    elif batch_state != "returned" and native.get("native_mapping_order") is not None:
        _add(issues, "retained_record_conflict", "association")
    if batch_state != "not_started" and native.get("formatted_sequence") != " " + str(normalized):
        _add(issues, "retained_record_conflict", "capture")
        context_ok = False
    raw_searches = native.get("enzyme_searches")
    raw_searches = raw_searches if type(raw_searches) is list else []
    by_ordinal, bad = {i: [] for i in range(len(names))}, set()
    attempted_ordinals = Counter()
    for raw in raw_searches:
        if type(raw) is not dict:
            _add(issues, "native_mapping_incomplete", "association")
            continue
        ordinal = raw.get("catalog_ordinal")
        if type(ordinal) is not int or ordinal not in by_ordinal:
            _add(issues, "native_mapping_incomplete", "association")
            continue
        by_ordinal[ordinal].append(raw)
        if type(raw.get("search_ordinal")) is int:
            attempted_ordinals[raw["search_ordinal"]] += 1
        if raw.get("name") != names[ordinal]:
            bad.add(ordinal)
            if raw.get("name") in names:
                bad.add(names.index(raw["name"]))
    match_events, match_issues, unassociated = _match_events(native, catalog_rows,
        topology=topology, sequence=normalized if type(normalized) is str else "", context_ok=context_ok)
    result["unassociated_match_calls"] = unassociated
    if unassociated:
        _add(issues, "match_owner_ambiguous", "association")
    for ordinal, original in enumerate(original_catalog_rows):
        row = _result_row(original)
        catalog = catalog_rows[ordinal]
        row["catalog_row"] = deepcopy(catalog)
        if catalog is None:
            row["position_meaning"] = "unknown"
            _add(row["issues"], "catalog_incompatible", "catalog", enzyme=ordinal)
        candidates = by_ordinal[ordinal]
        search = _valid("SearchRow", candidates[0]) if len(candidates) == 1 else None
        if (search is not None and search["search_ordinal"] is not None and
                (attempted_ordinals[search["search_ordinal"]] != 1 or not order_ok
                 or search["search_ordinal"] >= len(batch_order)
                 or batch_order[search["search_ordinal"]] != search["name"])):
            bad.add(ordinal)
        if search is None or ordinal in bad:
            _add(row["issues"], "native_mapping_incomplete", "association", enzyme=ordinal)
        else:
            row["search_state"] = search["state"]
            if search["state"] != "not_started":
                result["population"]["attempted_enzyme_count"] += 1
            if search["state"] == "returned":
                positions = deepcopy(search["native_search_positions_1based"])
                row["native_search_positions_1based"] = positions
                row["returned_position_count"] = len(positions)
                result["population"]["returned_enzyme_count"] += 1
                result["population"]["complete_empty_enzyme_count"] += not positions
                row["positions"] = [_position(p, i, catalog or original, topology=topology,
                    length=selected["length_nt"], attributable=context_ok and catalog is not None)
                    for i, p in enumerate(positions)]
                if positions:
                    _add(row["issues"], "association_unavailable", "association", enzyme=ordinal)
                    if not any(p["geometry_state"] == "known" for p in row["positions"]):
                        _add(row["issues"], "cut_geometry_unknown", "read", enzyme=ordinal)
            elif search["state"] == "failed":
                _add(row["issues"], "native_search_failed", "search", enzyme=ordinal)
            else:
                _add(row["issues"], "native_mapping_incomplete", "search", enzyme=ordinal)
        captured = match_events.get(ordinal)
        if captured is not None:
            events, complete = captured
            row["recognition_events"] = events
            row["recognition_match_count"] = len(events) if complete else None
            if (complete and row["returned_position_count"] is not None and catalog is not None):
                factor = 2 if catalog["cut_kind"] == "two_cuts" else 1
                upper = len(events) * factor
                exact = topology == "circular" or catalog["cut_kind"] == "no_cut"
                if row["returned_position_count"] > upper or (exact and row["returned_position_count"] != upper):
                    row["recognition_match_count"] = None
                    _add(row["issues"], "retained_record_conflict", "association", enzyme=ordinal)
        row["issues"].extend(i for i in match_issues.get(ordinal, []) if i not in row["issues"])
        for issue in row["issues"]:
            if issue not in issues:
                issues.append(deepcopy(issue))
        result["enzyme_rows"].append(row)
    counts = [row["recognition_match_count"] for row in result["enzyme_rows"]]
    if context_ok and all(count is not None for count in counts):
        result["population"]["recognition_match_count"] = sum(counts)
    invalid_identity = not context_ok
    complete = (not malformed_top and batch_state == "returned" and order_ok
        and catalog_complete and len(raw_searches) == len(names)
        and all(row["search_state"] == "returned" for row in result["enzyme_rows"])
        and not any(issue["code"] not in _QUALIFICATIONS for issue in issues))
    result["status"] = ("invalid" if invalid_identity else "complete" if complete else
        "unavailable" if batch_state == "not_started"
        and result["population"]["attempted_enzyme_count"] == 0 else "partial")
    return validate_restriction_record("MappingResult", result)


__all__ = ["read_restriction_mapping"]
