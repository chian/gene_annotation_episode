"""Closed, data-only legacy BLASTP report contracts.

These projections describe supplied bytes, not successful process execution or
input occurrence custody. Native inconsistencies remain observed values with
required issues. Schema loading happens at import; validation performs no IO.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, validators

from .bvbrc_proteome_native_contracts import native_schema


FORMAT = "ncbi_blastall_blastp_pairwise_text_v1"
RELEASES = frozenset({"2.0.11", "2.2.2", "2.2.21"})
_INTEGER = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)\Z")
_DECIMAL = re.compile(
    r"[+-]?(?:(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]*)?|\.[0-9]+)"
    r"(?:[eE][+-]?[0-9]+)?\Z"
)
_DOCUMENT = json.loads(Path(__file__).with_name(
    "bvbrc_proteome_directional_schemas.json").read_text(encoding="utf-8"))
_DEFS = _DOCUMENT["$defs"]
_SOURCE_SCHEMA = native_schema("NativeSource")
for _name, _definition in _SOURCE_SCHEMA["$defs"].items():
    if _DEFS[_name] != _definition:
        raise RuntimeError("directional_native_source_schema_drift")


class ProteomeDirectionalError(ValueError):
    """Stable machine-readable error; the message never echoes native content."""

    def __init__(self, code: str, path: str = ""):
        self.code, self.path = code, path
        super().__init__(code)


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _require(condition, path=""):
    if not condition:
        raise ProteomeDirectionalError("directional_contract_invalid", path)


def _plain_json(value, path="", ancestors=None):
    if value is None or type(value) in (str, int, bool):
        return
    _require(type(value) in (dict, list), path)
    ancestors = set() if ancestors is None else ancestors
    _require(id(value) not in ancestors, path)
    ancestors.add(id(value))
    for key, child in (value.items() if type(value) is dict else enumerate(value)):
        _require(type(value) is not dict or type(key) is str, path)
        _plain_json(child, _pointer(path, key), ancestors)
    ancestors.remove(id(value))


_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) in (int, float),
})
_Validator = validators.extend(Draft202012Validator, type_checker=_TYPES)


def directional_schema(name: str) -> dict:
    """Return a detached schema with only locally reachable definitions."""
    if type(name) is not str or name not in _DEFS:
        raise ProteomeDirectionalError("directional_argument_invalid", "/name")
    reached = set()

    def visit(node):
        if type(node) is dict:
            if "$ref" in node:
                key = node["$ref"].removeprefix("#/$defs/")
                if key not in _DEFS:
                    raise RuntimeError("directional_packaged_schema_reference_invalid")
                if key not in reached:
                    reached.add(key)
                    visit(_DEFS[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)

    root = {"$schema": _DOCUMENT["$schema"], "$ref": "#/$defs/" + name}
    visit(root)
    root["$defs"] = {k: deepcopy(v) for k, v in _DEFS.items() if k in reached}
    return root


_RESULT_VALIDATOR = _Validator(directional_schema("DirectionalReportResult"))
_SOURCE_VALIDATOR = _Validator(_SOURCE_SCHEMA)
_DECIMAL_FIELDS = frozenset({"bit_score", "expect", "evalue", "threshold", "bits", "lambda", "k", "h", "decimal_value",
                           "identity_printed_percent", "positive_printed_percent", "gap_printed_percent"})
_INTEGER_FIELDS = frozenset({"length", "sequence_count", "letter_count", "raw_score", "expect_group_count", "integer_value",
                           "identity_count", "identity_denominator", "positive_count", "positive_denominator", "gap_count", "gap_denominator",
                           "query_start", "query_end", "subject_start", "subject_end"})
_STATISTIC_CELLS = frozenset({"integer_value", "decimal_value", "text_value", "threshold", "bits", "lambda", "k", "h"})


def _statistic_cells(kind):
    if kind in {"database_name", "database_posted_date", "matrix"}:
        return {"text_value"}
    if kind in {"ka_ungapped", "ka_gapped"}:
        return {"lambda", "k", "h"}
    if kind in {"sequences_better_than", "hsps_better_than_without_gapping"}:
        return {"integer_value", "threshold"}
    if kind in {"x1", "x2", "x3", "s1", "s2"}:
        return {"integer_value", "bits"}
    return {"integer_value"}


def _check_shape(validator, value):
    _plain_json(value)
    error = next(validator.iter_errors(value), None)
    if error:
        path = ""
        for token in error.absolute_path:
            path = _pointer(path, token)
        raise ProteomeDirectionalError("directional_contract_invalid", path)


def _validate_source(value):
    try:
        _check_shape(_SOURCE_VALIDATOR, value)
    except ProteomeDirectionalError as error:
        raise ProteomeDirectionalError("directional_source_invalid", "/source" + error.path) from None


def _native_integer(text):
    if not _INTEGER.fullmatch(text):
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return None


def _native_decimal(text):
    normalized = "1" + text if re.fullmatch(r"[eE][+-]?[0-9]+", text) else text
    return normalized.replace(",", "") if _DECIMAL.fullmatch(normalized) else None


def _value(cell):
    return cell["value"] if cell["state"] == "present" else None


def _issue(code, scope, q=None, s=None, h=None, locations=()):
    return {"code": code, "scope": scope, "query_ordinal": q,
            "subject_ordinal": s, "hsp_ordinal": h, "locations": list(locations)}


def _locations(*cells):
    result = []
    for cell in cells:
        for loc in cell["locations"]:
            if loc not in result:
                result.append(loc)
    return result


def _required_issues(result):
    """Yield (owning issue list, issue) for observable consistency requirements.

    The parser adds these records. A saved-data validator requires them without
    erasing contradictory native values or claiming to possess the raw bytes.
    """
    source = result["source"]
    for condition, code in (
        (not source["body_complete"], "source_body_incomplete"),
        (source["object_complete"] == "no", "source_object_incomplete"),
        (source["object_complete"] == "unknown", "source_object_completeness_unknown"),
        (result["declared_format"] != FORMAT, "unsupported_format"),
    ):
        if condition:
            yield result["issues"], _issue(code, "report")
    for banner in result["banners"]:
        if _value(banner["program"]) != "BLASTP":
            yield result["issues"], _issue("unsupported_program", "report", locations=_locations(banner["program"]))
        elif _value(banner["release"]) not in RELEASES:
            yield result["issues"], _issue("unsupported_banner_version", "report", locations=_locations(banner["release"]))
    if (result["declared_format"] == FORMAT and not result["banners"] and
            not any(i["code"] == "unsupported_encoding" for i in result["issues"])):
        yield result["issues"], _issue("missing_banner", "report")

    def cells(owner, scope, q=None, s=None, h=None):
        for cell in owner.values():
            if type(cell) is dict and cell.get("state") == "invalid":
                # All invalid numeric spellings are retained, even when a larger
                # malformed block also has its own structural issue.
                yield owner["issues"], _issue("invalid_native_number", scope, q, s, h, cell["locations"])

    for query in result["queries"]:
        q = query["ordinal"]
        yield from cells(query, "query", q)
        for field, code in (("header_text", "missing_query_header"), ("length", "missing_query_length")):
            if query[field]["state"] == "missing" or (field == "header_text" and not _value(query[field])):
                yield query["issues"], _issue(code, "query", q)
        if query["banner_ordinal"] is None:
            yield query["issues"], _issue("missing_banner", "query", q)
        if _value(query["length"]) == 0:
            yield query["issues"], _issue("count_out_of_bounds", "query", q, locations=_locations(query["length"]))
        if query["boundary"] == "eof_unconfirmed":
            yield query["issues"], _issue("unterminated_native_block", "query", q)
        if query["no_hits_marker"]["state"] == "present" and query["subjects"]:
            yield query["issues"], _issue("no_hits_with_alignments", "query", q, locations=_locations(query["no_hits_marker"]))
        for header in query["database_headers"]:
            for cell in header.values():
                if type(cell) is dict and cell.get("state") == "invalid":
                    yield query["issues"], _issue("invalid_native_number", "query", q, locations=cell["locations"])
        for desc in query["descriptions"]:
            yield from cells(desc, "description", q)
        for stat in query["statistics"]:
            yield from cells(stat, "statistic", q)
            if any(stat[k]["state"] == "missing" for k in _statistic_cells(stat["kind"])):
                # Missing statistic syntax must be qualified, but exact observed
                # locations may differ between a wholly missing and partial row.
                if not any(i["code"] == "unparsed_scientific_record" for i in stat["issues"]):
                    yield stat["issues"], _issue("unparsed_scientific_record", "statistic", q)
        for subject in query["subjects"]:
            s = subject["ordinal"]
            yield from cells(subject, "subject", q, s)
            if subject["length"]["state"] == "missing":
                yield subject["issues"], _issue("missing_subject_length", "subject", q, s)
            if _value(subject["length"]) == 0:
                yield subject["issues"], _issue("count_out_of_bounds", "subject", q, s, locations=_locations(subject["length"]))
            for hsp in subject["hsps"]:
                h = hsp["ordinal"]
                yield from cells(hsp, "hsp", q, s, h)
                if any(hsp[k]["state"] == "missing" for k in ("bit_score", "raw_score", "expect")):
                    yield hsp["issues"], _issue("missing_hsp_score", "hsp", q, s, h)
                if any(hsp[k]["state"] == "missing" for k in ("identity_count", "identity_denominator")):
                    yield hsp["issues"], _issue("missing_identity_counts", "hsp", q, s, h)
                if not hsp["traceback_blocks"]:
                    yield hsp["issues"], _issue("missing_traceback", "hsp", q, s, h)
                denominators = []
                for prefix in ("identity", "positive", "gap"):
                    count, denom = (hsp[prefix + suffix] for suffix in ("_count", "_denominator"))
                    n, d = _value(count), _value(denom)
                    if d is not None:
                        denominators.append(denom)
                    if d == 0 or (n is not None and d is not None and n > d):
                        yield hsp["issues"], _issue("count_out_of_bounds", "hsp", q, s, h, _locations(count, denom))
                if len({_value(d) for d in denominators}) > 1:
                    yield hsp["issues"], _issue("alignment_denominator_mismatch", "hsp", q, s, h, _locations(*denominators))
                complete_widths = []
                for block in hsp["traceback_blocks"]:
                    yield from cells(block, "hsp", q, s, h)
                    required = ("query_start", "query_symbols", "query_end", "subject_start", "subject_symbols", "subject_end")
                    if any(block[k]["state"] != "present" for k in required):
                        yield block["issues"], _issue("incomplete_traceback_block", "hsp", q, s, h)
                    widths = [len(_value(block[k])) for k in ("query_symbols", "subject_symbols", "midline") if _value(block[k]) is not None]
                    if len(set(widths)) > 1:
                        yield block["issues"], _issue("traceback_width_mismatch", "hsp", q, s, h, _locations(block["query_symbols"], block["subject_symbols"], block["midline"]))
                    if all(block[k]["state"] == "present" for k in ("query_symbols", "subject_symbols")):
                        complete_widths.append(len(block["query_symbols"]["value"]))
                    for side, full in (("query", query["length"]), ("subject", subject["length"])):
                        start, end, symbols = (block[side + suffix] for suffix in ("_start", "_end", "_symbols"))
                        a, b, seq, length = _value(start), _value(end), _value(symbols), _value(full)
                        if a is not None and b is not None:
                            if b < a:
                                yield block["issues"], _issue("nonprotein_coordinate_order", "hsp", q, s, h, _locations(start, end))
                            if seq is not None and sum(c != "-" for c in seq) != abs(b - a) + 1:
                                yield block["issues"], _issue("coordinate_symbol_count_mismatch", "hsp", q, s, h, _locations(start, end, symbols))
                        if any(x is not None and (x < 1 or (length is not None and x > length)) for x in (a, b)):
                            yield block["issues"], _issue("coordinate_out_of_bounds", "hsp", q, s, h, _locations(start, end, full))
                if (hsp["traceback_blocks"] and len(complete_widths) == len(hsp["traceback_blocks"]) and
                        any(_value(d) != sum(complete_widths) for d in denominators)):
                    yield hsp["issues"], _issue("alignment_denominator_mismatch", "hsp", q, s, h, _locations(*denominators))


def _all_issue_lists(result):
    yield result["issues"]
    for q in result["queries"]:
        yield q["issues"]
        for name in ("descriptions", "statistics", "subjects"):
            for owner in q[name]:
                yield owner["issues"]
                if name == "subjects":
                    for hsp in owner["hsps"]:
                        yield hsp["issues"]
                        for block in hsp["traceback_blocks"]:
                            yield block["issues"]


def _expected_state(result):
    supported = result["declared_format"] == FORMAT and any(
        q["banner_ordinal"] is not None and
        _value(result["banners"][q["banner_ordinal"]]["program"]) == "BLASTP" and
        _value(result["banners"][q["banner_ordinal"]]["release"]) in RELEASES
        for q in result["queries"]
    )
    if not supported:
        return "failure"
    return "partial" if any(_all_issue_lists(result)) else "ok"


def validate_directional_report(value: dict) -> dict:
    """Validate supplied projection data and return a fully detached copy.

    This checks locations and declared byte binding, not the underlying artifact
    bytes. The parser separately checks the digest, length, and source slices.
    """
    _check_shape(_RESULT_VALIDATOR, value)
    binding = value["source"]["content"]
    size = binding["byte_count"]

    def span(item, path, parent=None):
        a, b = item["byte_start"], item["byte_end"]
        _require(0 <= a <= b <= size, path)
        if parent is not None:
            _require(parent["byte_start"] <= a <= b <= parent["byte_end"], path)

    def located(loc, path, parent=None):
        _require(loc["source_ref"] == binding["source_ref"] and loc["sha256"] == binding["sha256"], path)
        span(loc["span"], path + "/span", parent)

    def record(owner, path, parent=None):
        span(owner["span"], path + "/span", parent)
        for key, cell in owner.items():
            if type(cell) is not dict or "state" not in cell:
                continue
            p = _pointer(path, key)
            for index, loc in enumerate(cell["locations"]):
                located(loc, f"{p}/locations/{index}", owner["span"])
            if cell["state"] == "present":
                if key in _INTEGER_FIELDS:
                    _require(_native_integer(cell["native_text"]) == cell["value"], p)
                elif key in _DECIMAL_FIELDS:
                    _require(_native_decimal(cell["native_text"]) == cell["value"], p)
                else:
                    _require(cell["value"] == cell["native_text"] or cell["value"] == " ".join(x.strip() for x in cell["native_text"].splitlines()), p)
            elif cell["state"] == "invalid" and key in _INTEGER_FIELDS | _DECIMAL_FIELDS:
                decoder = _native_integer if key in _INTEGER_FIELDS else _native_decimal
                _require(decoder(cell["native_text"]) is None, p)

    def sequence(records, path, parent=None, overlap=False):
        previous = None
        for index, owner in enumerate(records):
            p = f"{path}/{index}"
            _require(owner["ordinal"] == index, p + "/ordinal")
            record(owner, p, parent)
            if previous is not None:
                _require(owner["span"]["byte_start"] >= previous["byte_start" if overlap else "byte_end"], p + "/span")
            previous = owner["span"]

    def issues(items, path, scope=None, q=None, s=None, h=None):
        for index, issue in enumerate(items):
            p = f"{path}/{index}"
            if scope is not None:
                _require((issue["scope"], issue["query_ordinal"], issue["subject_ordinal"], issue["hsp_ordinal"]) == (scope, q, s, h), p)
            for loc_i, loc in enumerate(issue["locations"]):
                located(loc, f"{p}/locations/{loc_i}")

    sequence(value["banners"], "/banners")
    sequence(value["queries"], "/queries")
    issues(value["issues"], "/issues", "report")
    for qi, query in enumerate(value["queries"]):
        p = f"/queries/{qi}"
        bi = query["banner_ordinal"]
        if bi is not None:
            _require(bi < len(value["banners"]) and value["banners"][bi]["span"]["byte_end"] <= query["span"]["byte_start"], p + "/banner_ordinal")
            _require(not any(b["span"]["byte_start"] < query["span"]["byte_start"] for b in value["banners"][bi + 1:]), p + "/banner_ordinal")
        boundary = query["boundary"]
        endpoint = query["span"]["byte_end"]
        if boundary == "next_banner":
            _require(any(b["span"]["byte_start"] == endpoint for b in value["banners"]), p + "/boundary")
        elif boundary == "next_query":
            _require(any(q["span"]["byte_start"] == endpoint for q in value["queries"][qi + 1:]), p + "/boundary")
        else:
            _require(endpoint == size, p + "/boundary")
            if boundary == "eof_complete":
                _require(value["source"]["body_complete"] and value["source"]["object_complete"] == "yes", p + "/boundary")
        header = _value(query["header_text"])
        _require(_value(query["identifier_token"]) == (header.split()[0] if header and header.split() else None), p + "/identifier_token")
        marker = _value(query["no_hits_marker"])
        if marker is not None:
            _require(re.fullmatch(r"\s*(?:\*+\s*)?No hits found(?:\s*\*+)?\s*", marker) is not None, p + "/no_hits_marker")
        issues(query["issues"], p + "/issues", "query", qi)
        for name in ("database_headers", "descriptions", "statistics", "subjects"):
            sequence(query[name], p + "/" + name, query["span"], overlap=name == "statistics")
        for name, scope in (("descriptions", "description"), ("statistics", "statistic")):
            for oi, owner in enumerate(query[name]):
                issues(owner["issues"], f"{p}/{name}/{oi}/issues", scope, qi)
                if name == "descriptions":
                    _require(owner["ellipsis_suffix"] == bool(_value(owner["label"]) and _value(owner["label"]).endswith("...")), f"{p}/{name}/{oi}/ellipsis_suffix")
                else:
                    _require(all(owner[k]["state"] == "missing" for k in _STATISTIC_CELLS - _statistic_cells(owner["kind"])), f"{p}/{name}/{oi}")
        for si, subject in enumerate(query["subjects"]):
            sp = f"{p}/subjects/{si}"
            issues(subject["issues"], sp + "/issues", "subject", qi, si)
            header = _value(subject["defline_text"])
            _require(_value(subject["identifier_token"]) == (header.split()[0] if header and header.split() else None), sp + "/identifier_token")
            sequence(subject["hsps"], sp + "/hsps", subject["span"])
            for hi, hsp in enumerate(subject["hsps"]):
                hp = f"{sp}/hsps/{hi}"
                issues(hsp["issues"], hp + "/issues", "hsp", qi, si, hi)
                sequence(hsp["traceback_blocks"], hp + "/traceback_blocks", hsp["span"])
                for ti, block in enumerate(hsp["traceback_blocks"]):
                    issues(block["issues"], f"{hp}/traceback_blocks/{ti}/issues", "hsp", qi, si, hi)
    for ri, raw in enumerate(value["raw_records"]):
        for li, loc in enumerate(raw["locations"]):
            located(loc, f"/raw_records/{ri}/locations/{li}")
        if raw["kind"] in {"unknown_header", "unknown_footer"}:
            all_issues = [i for owner in _all_issue_lists(value) for i in owner]
            _require(any(i["code"] == "unparsed_scientific_record" and
                         all(loc in i["locations"] for loc in raw["locations"]) for i in all_issues), f"/raw_records/{ri}")
    for owner, required in _required_issues(value):
        _require(required in owner, "/issues")
    _require(value["parse_state"] == _expected_state(value), "/parse_state")
    return deepcopy(value)


__all__ = ["ProteomeDirectionalError", "directional_schema", "validate_directional_report"]
