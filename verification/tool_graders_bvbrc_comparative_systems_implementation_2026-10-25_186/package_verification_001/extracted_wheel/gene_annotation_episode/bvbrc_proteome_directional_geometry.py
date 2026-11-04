"""Pure protein-column geometry for retained directional BLASTP reports.

Native coordinates are one-based and inclusive. Returned positions and unions
are zero-based and half-open. No native cell is rewritten; no operation here
acquires data, executes a program, selects an HSP, or assigns annotation credit.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import re

from .blast_pairwise_grader import (
    _axis_positions, _mapping_conflicts, _union_size, alignment_components,
)


_KEY_FIELDS = ("report_ordinal", "query_ordinal", "subject_ordinal",
               "hsp_ordinal", "block_ordinal", "column_ordinal")
_ALPHABETS = {"standard20": frozenset("ACDEFGHIKLMNPQRSTVWY"),
              "standard20_plus_uo": frozenset("ACDEFGHIKLMNPQRSTVWYUO")}
_SYMBOLS = re.compile(r"[A-Za-z*\-]+\Z")
_INT_TEXT = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)\Z")
_COUNT_UNITS = {
    "alignment_columns": "alignment_column", "paired_columns": "paired_column",
    "displayed_symbol_identical_pairs": "paired_column",
    "displayed_symbol_nonidentical_pairs": "paired_column",
    "resolved_amino_acid_pairs": "paired_column",
    "resolved_amino_acid_identical_pairs": "paired_column",
    "resolved_amino_acid_substituted_pairs": "paired_column",
    "unresolved_symbol_pairs": "paired_column", "stop_containing_pairs": "paired_column",
    "query_gap_columns": "alignment_column", "subject_gap_columns": "alignment_column",
    "query_gap_runs": "gap_run", "subject_gap_runs": "gap_run",
    "query_non_gap_symbols": "displayed_position", "subject_non_gap_symbols": "displayed_position",
}


class DirectionalNumericalContractError(ValueError):
    """A caller error located in the arguments, never echoed scientific prose."""

    def __init__(self, code: str, pointer: str = ""):
        self.code, self.pointer = code, pointer
        super().__init__(code)


def _require(condition, pointer, code="invalid_input_contract"):
    if not condition:
        raise DirectionalNumericalContractError(code, pointer)


def _key(value, width, pointer):
    _require(type(value) is dict and set(value) == set(_KEY_FIELDS[:width]), pointer)
    for field in _KEY_FIELDS[:width]:
        _require(type(value[field]) is int and value[field] >= 0, pointer + "/" + field)
    return tuple(value[field] for field in _KEY_FIELDS[:width])


def _span(value, pointer):
    _require(type(value) is dict and set(value) == {"byte_start", "byte_end"}, pointer)
    _require(all(type(value[k]) is int for k in value)
             and 0 <= value["byte_start"] <= value["byte_end"], pointer)


def _native_cell(cell, kind, pointer):
    _require(type(cell) is dict and set(cell) == {"state", "value", "native_text", "locations"}, pointer)
    _require(cell["state"] in ("present", "missing", "invalid"), pointer + "/state")
    _require(type(cell["locations"]) is list, pointer + "/locations")
    for i, loc in enumerate(cell["locations"]):
        p = f"{pointer}/locations/{i}"
        _require(type(loc) is dict and set(loc) == {"source_ref", "sha256", "span"}, p)
        _require(type(loc["source_ref"]) is str and bool(loc["source_ref"]), p + "/source_ref")
        _require(type(loc["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", loc["sha256"]) is not None, p + "/sha256")
        _span(loc["span"], p + "/span")
    if cell["state"] == "missing":
        _require(cell["value"] is None and cell["native_text"] is None and not cell["locations"], pointer)
        return
    _require(type(cell["native_text"]) is str and bool(cell["locations"]), pointer)
    value = cell["value"]
    parsed_integer = None
    if kind == "integer" and _INT_TEXT.fullmatch(cell["native_text"]):
        try:
            parsed_integer = int(cell["native_text"].replace(",", ""))
        except ValueError:
            # The reader preserves an unconvertible native integer as invalid,
            # including a spelling exceeding the interpreter's integer limit.
            pass
    if cell["state"] == "invalid":
        _require(value is None, pointer + "/value")
        if kind == "integer":
            _require(parsed_integer is None, pointer + "/native_text")
    elif kind == "integer":
        _require(type(value) is int and value >= 0, pointer + "/value")
        _require(_INT_TEXT.fullmatch(cell["native_text"]) is not None, pointer + "/native_text")
        _require(parsed_integer == value, pointer + "/value")
    else:
        _require(type(value) is str and value == cell["native_text"], pointer + "/value")


def _unique(values):
    result = []
    seen = set()
    for value in values:
        key = tuple(sorted(value.items())) if type(value) is dict else value
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(value))
    return result


def _ref(key, suffix):
    base = f"/queries/{key['query_ordinal']}"
    if suffix == "query_length":
        pointer = base + "/length"
    else:
        base += f"/subjects/{key['subject_ordinal']}"
        if suffix == "subject_length":
            pointer = base + "/length"
        else:
            pointer = (base + f"/hsps/{key['hsp_ordinal']}/traceback_blocks/"
                       f"{key['block_ordinal']}/{suffix}")
    return {"report_ordinal": key["report_ordinal"], "pointer": pointer}


def _issue(code, fields=(), columns=(), hsps=()):
    return {"code": code, "fields": _unique(fields), "columns": _unique(columns),
            "hsps": _unique(hsps), "argument_pointer": None}


def _cell(value, unit, inputs, *, state="value", reasons=()):
    return {"state": state, "value": value, "unit": unit, "inputs": _unique(inputs),
            "reasons": list(dict.fromkeys(reasons)), "uncertainty": None}


def _fraction(numerator, denominator, inputs, places, *, state="value", reasons=(), zero_reason="zero_paired_population"):
    if state != "value":
        return _cell(None, "fraction", inputs, state=state, reasons=reasons)
    if denominator == 0:
        return _cell(None, "fraction", inputs, state="undefined", reasons=[zero_reason])
    # Integer long division gives exact HALF_EVEN rendering without binary float
    # or a Decimal context whose precision could silently round an operand.
    quotient, remainder = divmod(numerator * 10 ** places, denominator)
    if 2 * remainder > denominator or (2 * remainder == denominator and quotient % 2):
        quotient += 1
    digits = str(quotient)
    decimal = digits if places == 0 else digits.zfill(places + 1)[:-places] + "." + digits.zfill(places + 1)[-places:]
    return _cell({"numerator": numerator, "denominator": denominator, "decimal": decimal}, "fraction", inputs)


def _support(key, included):
    return {"included_blocks": [deepcopy(key)] if included else [],
            "excluded_blocks": [] if included else [deepcopy(key)],
            "hsps_without_traceback": [], "complete_for_displayed_blocks": included}


def union_position_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Return the exact sorted maximal union of supplied half-open intervals."""
    _require(type(intervals) is list, "/intervals")
    for i, interval in enumerate(intervals):
        _require(type(interval) is list and len(interval) == 2
                 and all(type(n) is int for n in interval)
                 and 0 <= interval[0] < interval[1], f"/intervals/{i}")
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def _position_union(intervals, *, key, inputs, length, length_ref, places, state="value", reasons=()):
    merged = union_position_intervals(intervals)
    count = _union_size(tuple(row) for row in merged) if state == "value" else None
    denominator = length["value"] if length["state"] == "present" and length["value"] > 0 else None
    length_state = "value" if denominator is not None else "missing" if length["state"] == "missing" else "invalid"
    length_reasons = [] if denominator is not None else ["missing_reported_length" if length_state == "missing" else "invalid_reported_length"]
    precedence = {"value": 0, "undefined": 1, "missing": 2, "invalid": 3, "conflict": 4}
    ratio_state = max((state, length_state), key=precedence.__getitem__)
    return {"intervals": merged, "count": _cell(count, "displayed_position", inputs, state=state, reasons=reasons),
            "reported_length": deepcopy(length),
            "coverage": _fraction(count, denominator, [*inputs, length_ref], places,
                                  state=ratio_state, reasons=[*reasons, *length_reasons]),
            "support": _support(key, state == "value")}


def calculate_protein_block(
    block: dict, *, key: dict, query_length: dict, subject_length: dict,
    amino_acid_alphabet: str, ratio_decimal_places: int, rounding: str,
) -> dict:
    """Calculate a native block with explicit alphabet and fraction rendering.

    Every string count uses both native symbol cells because usable paired
    strings are the population prerequisite. Coordinate counts also name the
    axis endpoints and its same-occurrence length (the optional bounds check).
    A reported interval does not consume symbols; trace geometry does. Coverage
    adds the same native length as its explicit denominator.
    """
    _key(key, 5, "/key")
    _require(type(amino_acid_alphabet) is str and amino_acid_alphabet in _ALPHABETS,
             "/amino_acid_alphabet", "invalid_parameters")
    _require(type(ratio_decimal_places) is int and 0 <= ratio_decimal_places <= 30,
             "/ratio_decimal_places", "invalid_parameters")
    _require(rounding == "half_even" and type(rounding) is str, "/rounding", "invalid_parameters")
    _native_cell(query_length, "integer", "/query_length")
    _native_cell(subject_length, "integer", "/subject_length")
    fields = ("query_start", "query_symbols", "query_end", "midline", "subject_start", "subject_symbols", "subject_end")
    _require(type(block) is dict and set(block) == {"ordinal", "span", "issues", *fields}, "/block")
    _require(type(block["ordinal"]) is int and block["ordinal"] == key["block_ordinal"], "/block/ordinal")
    _span(block["span"], "/block/span")
    _require(type(block["issues"]) is list, "/block/issues")
    for field in fields:
        _native_cell(block[field], "integer" if field.endswith(("_start", "_end")) else "string", "/block/" + field)
    inputs = [_ref(key, "query_symbols"), _ref(key, "subject_symbols")]
    symbols = [block[name] for name in ("query_symbols", "subject_symbols")]
    string_reasons = []
    if any(c["state"] == "missing" for c in symbols):
        string_reasons.append("missing_traceback_symbols")
    if any(c["state"] == "invalid" or c["state"] == "present" and not _SYMBOLS.fullmatch(c["value"]) for c in symbols):
        string_reasons.append("invalid_traceback_symbols")
    if all(c["state"] == "present" for c in symbols):
        if len(symbols[0]["value"]) != len(symbols[1]["value"]):
            string_reasons.append("traceback_width_conflict")
        if any(a == b == "-" for a, b in zip(symbols[0]["value"], symbols[1]["value"])):
            string_reasons.append("double_gap_column")
    string_state = ("invalid" if any(r != "missing_traceback_symbols" for r in string_reasons)
                    else "missing" if string_reasons else "value")
    diagnostics = [_issue(code, inputs) for code in string_reasons]
    usable = string_state == "value"
    q, s = (c["value"] for c in symbols) if usable else (None, None)
    normalized = {"qseq": q, "hseq": s}
    for side, prefix in (("query", "query"), ("subject", "hit")):
        for suffix, target in (("start", "from"), ("end", "to")):
            cell = block[side + "_" + suffix]
            if cell["state"] == "present":
                normalized[prefix + "_" + target] = cell["value"]
    coverage, mapped = {}, {}
    for side, length, prefix in (("query", query_length, "query"), ("subject", subject_length, "hit")):
        length_ref = _ref(key, side + "_length")
        coordinate_inputs = [_ref(key, side + "_start"), _ref(key, side + "_end"), length_ref]
        start, end = (block[side + suffix] for suffix in ("_start", "_end"))
        reasons = []
        if any(c["state"] == "missing" for c in (start, end)):
            reasons.append("missing_coordinate")
        if any(c["state"] == "invalid" or c["state"] == "present" and c["value"] < 1 for c in (start, end)):
            reasons.append("invalid_coordinate")
        if all(c["state"] == "present" and c["value"] >= 1 for c in (start, end)):
            if end["value"] < start["value"]:
                reasons.append("reverse_protein_coordinates")
            if length["state"] == "present" and length["value"] > 0 and max(start["value"], end["value"]) > length["value"]:
                reasons.append("coordinate_outside_reported_length")
        state = "invalid" if any(r != "missing_coordinate" for r in reasons) else "missing" if reasons else "value"
        diagnostics.extend(_issue(code, coordinate_inputs) for code in reasons)
        if length["state"] != "present" or length["value"] == 0:
            diagnostics.append(_issue("missing_reported_length" if length["state"] == "missing" else "invalid_reported_length", [length_ref]))
        intervals = [[start["value"] - 1, end["value"]]] if state == "value" else []
        coverage[side + "_reported_interval_union"] = _position_union(intervals, key=key, inputs=coordinate_inputs,
            length=length, length_ref=length_ref, places=ratio_decimal_places, state=state, reasons=reasons)
        trace_inputs = [*inputs, *coordinate_inputs]
        trace_reasons = [*string_reasons, *reasons]
        precedence = {"value": 0, "missing": 1, "invalid": 2, "conflict": 3}
        trace_state = max((state, string_state), key=precedence.__getitem__)
        positions = None
        if usable and state == "value":
            seq = q if side == "query" else s
            if end["value"] - start["value"] + 1 != len(seq.replace("-", "")):
                trace_reasons.append("coordinate_span_conflict")
                trace_state = "conflict"
                diagnostics.append(_issue("coordinate_span_conflict", trace_inputs))
            else:
                existing_issues = []
                positions = _axis_positions(normalized, prefix=prefix, symbols=seq,
                    length=length["value"] if length["state"] == "present" and length["value"] > 0 else None,
                    coordinate_unit="aa", alignment_unit="aa", issues=existing_issues)
                if positions is None or existing_issues:
                    raise RuntimeError("validated_protein_axis_disagrees_with_blast_geometry")
        mapped[side] = positions
        occupied = [list(pos) for pos in positions if pos is not None] if positions is not None else []
        paired = [list(pos) for pos, other in zip(positions, s if side == "query" else q)
                  if pos is not None and other != "-"] if positions is not None else []
        for basis, intervals in (("occupied", occupied), ("paired", paired)):
            coverage[side + "_trace_" + basis + "_union"] = _position_union(intervals, key=key,
                inputs=trace_inputs, length=length, length_ref=length_ref, places=ratio_decimal_places,
                state=trace_state, reasons=trace_reasons)
    columns, counts = [], {}
    if usable:
        native_math = alignment_components(normalized, program="blastp", query_length=None, reference_length=None)["counts"]
        alphabet = _ALPHABETS[amino_acid_alphabet]
        kinds = defaultdict(int)
        for i, (a, b) in enumerate(zip(q, s)):
            au, bu = a.upper(), b.upper()
            kind = ("query_gap" if a == "-" else "subject_gap" if b == "-" else
                    "stop_containing_pair" if "*" in (a, b) else
                    "unresolved_pair" if au not in alphabet or bu not in alphabet else
                    "resolved_identical" if au == bu else "resolved_substituted")
            kinds[kind] += 1
            column = {"key": {**key, "column_ordinal": i}, "query_symbol": a, "subject_symbol": b,
                      "kind": kind, "displayed_symbol_equal": a != "-" and b != "-" and au == bu}
            for side, symbol in (("query", a), ("subject", b)):
                pos = mapped[side][i] if mapped[side] is not None else None
                column[side + "_position"] = {"state": "gap" if symbol == "-" else "position" if pos is not None else "unavailable_coordinate",
                                               "value": pos[0] if pos is not None else None}
            columns.append(column)
        paired = native_math["paired_columns"]
        values = {"alignment_columns": native_math["alignment_columns"], "paired_columns": paired,
                  "displayed_symbol_identical_pairs": native_math["identical_pairs"],
                  "displayed_symbol_nonidentical_pairs": paired - native_math["identical_pairs"],
                  "resolved_amino_acid_pairs": kinds["resolved_identical"] + kinds["resolved_substituted"],
                  "resolved_amino_acid_identical_pairs": kinds["resolved_identical"],
                  "resolved_amino_acid_substituted_pairs": kinds["resolved_substituted"],
                  "unresolved_symbol_pairs": kinds["unresolved_pair"], "stop_containing_pairs": kinds["stop_containing_pair"],
                  "query_gap_columns": native_math["query_gap_columns"], "subject_gap_columns": native_math["reference_gap_columns"],
                  "query_gap_runs": len(re.findall("-+", q)), "subject_gap_runs": len(re.findall("-+", s)),
                  "query_non_gap_symbols": len(q.replace("-", "")), "subject_non_gap_symbols": len(s.replace("-", ""))}
        counts = {name: _cell(values[name], unit, inputs) for name, unit in _COUNT_UNITS.items()}
    else:
        counts = {name: _cell(None, unit, inputs, state=string_state, reasons=string_reasons) for name, unit in _COUNT_UNITS.items()}
    operands = {
        "trace_symbol_identity_over_columns": ("displayed_symbol_identical_pairs", "alignment_columns"),
        "trace_symbol_identity_over_pairs": ("displayed_symbol_identical_pairs", "paired_columns"),
        "trace_resolved_amino_acid_identity": ("resolved_amino_acid_identical_pairs", "resolved_amino_acid_pairs"),
        "trace_resolved_pair_fraction": ("resolved_amino_acid_pairs", "paired_columns"),
        "trace_unresolved_pair_fraction": ("unresolved_symbol_pairs", "paired_columns"),
        "trace_gap_fraction": (None, "alignment_columns"),
    }
    fractions = {}
    for name, (n, d) in operands.items():
        numerator = (counts[n]["value"] if n else counts["query_gap_columns"]["value"] + counts["subject_gap_columns"]["value"]) if usable else None
        fractions[name] = _fraction(numerator, counts[d]["value"], inputs, ratio_decimal_places,
            state=string_state, reasons=string_reasons,
            zero_reason="zero_resolved_population" if d == "resolved_amino_acid_pairs" else "zero_paired_population")
    return {"key": deepcopy(key), "counts": counts, "fractions": fractions,
            "columns": columns, "coverage": coverage, "diagnostics": diagnostics}


def _column_order(column):
    return tuple(column[field] for field in _KEY_FIELDS)


def inspect_protein_correspondence(hsp_components: list[dict], *, key: dict) -> dict:
    """Inspect one explicit subject occurrence, including an empty occurrence.

    Graph relationships use literal symbols and coordinate positions only; the
    resolved alphabet and ratio rendering cannot change the graph. Exact edges
    are deduplicated, but every supporting native column occurrence survives.
    """
    parent = _key(key, 3, "/key")
    _require(type(hsp_components) is list, "/hsp_components")
    all_columns, by_pair, axis_columns = [], defaultdict(list), {"query": defaultdict(list), "subject": defaultdict(list)}
    included, excluded, absent, inputs, unavailable = [], [], [], [], []
    continuity = []
    for hi, hsp in enumerate(hsp_components):
        hp = f"/hsp_components/{hi}"
        _require(type(hsp) is dict, hp)
        identity = _key(hsp.get("key"), 4, hp + "/key")
        _require(identity[:3] == parent and identity[3] == hi, hp + "/key")
        _require(type(hsp.get("blocks")) is list, hp + "/blocks")
        _require(hsp.get("contiguous_blocks") in ("yes", "no", "unknown"), hp + "/contiguous_blocks")
        if not hsp["blocks"]:
            absent.append(deepcopy(hsp["key"]))
        previous = None
        for bi, block in enumerate(hsp["blocks"]):
            bp = hp + f"/blocks/{bi}"
            _require(type(block) is dict, bp)
            block_id = _key(block.get("key"), 5, bp + "/key")
            _require(block_id[:4] == identity and block_id[4] == bi, bp + "/key")
            _require(type(block.get("columns")) is list and type(block.get("coverage")) is dict, bp)
            good = True
            for side in ("query", "subject"):
                union = block["coverage"].get(side + "_trace_paired_union")
                _require(type(union) is dict and type(union.get("count")) is dict, bp + "/coverage")
                cell = union["count"]
                _require(type(cell.get("inputs")) is list and type(cell.get("reasons")) is list
                         and cell.get("state") in ("value", "missing", "invalid", "conflict", "undefined"), bp + "/coverage")
                inputs.extend(cell["inputs"])
                if cell["state"] != "value":
                    good = False
                    unavailable.append(cell)
            (included if good else excluded).append(deepcopy(block["key"]))
            for ci, column in enumerate(block["columns"]):
                cp = bp + f"/columns/{ci}"
                _require(type(column) is dict, cp)
                _require(_key(column.get("key"), 6, cp + "/key") == (*block_id, ci), cp + "/key")
                for side in ("query", "subject"):
                    symbol, pos = column.get(side + "_symbol"), column.get(side + "_position")
                    _require(type(symbol) is str and len(symbol) == 1 and _SYMBOLS.fullmatch(symbol), cp + "/" + side + "_symbol")
                    _require(type(pos) is dict and set(pos) == {"state", "value"}, cp + "/" + side + "_position")
                    _require((pos["state"] == "position" and type(pos["value"]) is int and pos["value"] >= 0 and symbol != "-")
                             or (pos["state"] == "gap" and pos["value"] is None and symbol == "-")
                             or (pos["state"] == "unavailable_coordinate" and pos["value"] is None and symbol != "-"), cp)
                    if pos["state"] == "position":
                        axis_columns[side][pos["value"]].append(column)
                _require((column["query_symbol"], column["subject_symbol"]) != ("-", "-"), cp)
                all_columns.append(column)
                if all(column[side + "_position"]["state"] == "position" for side in ("query", "subject")):
                    by_pair[(column["query_position"]["value"], column["subject_position"]["value"])].append(column)
            if previous is not None:
                violated = []
                for side in ("query", "subject"):
                    before = previous["coverage"][side + "_reported_interval_union"]
                    after = block["coverage"][side + "_reported_interval_union"]
                    if before["count"]["state"] == after["count"]["state"] == "value" and before["intervals"][0][1] != after["intervals"][0][0]:
                        violated.append(side)
                if violated:
                    boundary_columns = []
                    for side in violated:
                        left = [c for c in previous["columns"] if c[side + "_position"]["state"] == "position"]
                        right = [c for c in block["columns"] if c[side + "_position"]["state"] == "position"]
                        # Endpoint claims with unavailable strings/coordinates
                        # are HSP diagnostics, not invented graph witnesses.
                        if left and right:
                            boundary_columns.extend(left[-1:] + right[:1])
                    continuity.extend(boundary_columns)
            previous = block
    support = {"included_blocks": included, "excluded_blocks": excluded, "hsps_without_traceback": absent,
               "complete_for_displayed_blocks": not excluded and not absent}
    for hi, hsp in enumerate(hsp_components):
        actual = {"included_blocks": [b for b in included if b["hsp_ordinal"] == hi],
                  "excluded_blocks": [b for b in excluded if b["hsp_ordinal"] == hi],
                  "hsps_without_traceback": [h for h in absent if h["hsp_ordinal"] == hi]}
        actual["complete_for_displayed_blocks"] = not actual["excluded_blocks"] and not actual["hsps_without_traceback"]
        _require(hsp.get("pair_geometry_support") == actual, f"/hsp_components/{hi}/pair_geometry_support")
    conflicts = []

    def add_conflict(code, columns):
        seen = {_column_order(c["key"]): c for c in columns}
        rows = [seen[k] for k in sorted(seen)]
        conflicts.append({"code": code, "columns": [deepcopy(c["key"]) for c in rows],
            "query_intervals": union_position_intervals([[c["query_position"]["value"], c["query_position"]["value"] + 1] for c in rows if c["query_position"]["state"] == "position"]),
            "subject_intervals": union_position_intervals([[c["subject_position"]["value"], c["subject_position"]["value"] + 1] for c in rows if c["subject_position"]["state"] == "position"])})

    pair_keys = sorted(by_pair)
    pair_rows = [{"query_start": q, "query_end": q + 1, "reference_start": s, "reference_end": s + 1} for q, s in pair_keys]
    for side, legacy in (("query", "query"), ("subject", "reference")):
        witnesses = _mapping_conflicts(pair_rows, legacy)
        if witnesses:
            indices = {i for witness in witnesses for i in witness["pair_indices"]}
            add_conflict("alternative_" + side + "_mapping", [c for i in sorted(indices) for c in by_pair[pair_keys[i]]])
    for side, other in (("query", "subject"), ("subject", "query")):
        symbols, gaps = [], []
        for rows in axis_columns[side].values():
            if len({c[side + "_symbol"].upper() for c in rows}) > 1:
                symbols.extend(rows)
            if {c[other + "_symbol"] == "-" for c in rows} == {False, True}:
                gaps.extend(rows)
        if symbols:
            add_conflict(side + "_symbol_conflict", symbols)
        if gaps:
            add_conflict(side + "_gap_versus_pair_conflict", gaps)
    # Mark each endpoint participating in an inversion. Equal query positions
    # and equal subject positions are already the distinct alternative-map cases.
    grouped = defaultdict(list)
    for pair in pair_keys:
        grouped[pair[0]].append(pair)
    crossing, maximum = set(), None
    for q in sorted(grouped):
        for pair in grouped[q]:
            if maximum is not None and pair[1] < maximum:
                crossing.add(pair)
        maximum = max([p[1] for p in grouped[q]] + ([] if maximum is None else [maximum]))
    minimum = None
    for q in sorted(grouped, reverse=True):
        for pair in grouped[q]:
            if minimum is not None and pair[1] > minimum:
                crossing.add(pair)
        minimum = min([p[1] for p in grouped[q]] + ([] if minimum is None else [minimum]))
    if crossing:
        add_conflict("noncollinear_pair_order", [c for pair in sorted(crossing) for c in by_pair[pair]])
    if continuity:
        add_conflict("block_continuity_conflict", continuity)
    edges = [{"query_position": q, "subject_position": s,
              "supports": [deepcopy(c["key"]) for c in sorted(by_pair[(q, s)], key=lambda c: _column_order(c["key"]))],
              "symbol_state": "consistent" if len({(c["query_symbol"].upper(), c["subject_symbol"].upper()) for c in by_pair[(q, s)]}) == 1 else "conflicting"}
             for q, s in pair_keys]
    known_geometry = bool(included)
    state = "value"
    reasons = []
    if not known_geometry:
        reasons = list(dict.fromkeys(r for c in unavailable for r in c["reasons"]))
        if absent or not hsp_components:
            reasons.append("missing_traceback")
        state = ("conflict" if any(c["state"] == "conflict" for c in unavailable) else
                 "invalid" if any(c["state"] == "invalid" for c in unavailable) else "missing")
    mapping_state = ("observed_conflict" if conflicts else "incomplete_geometry"
                     if not known_geometry or not support["complete_for_displayed_blocks"] else "compatible_displayed_partial_map")
    return {"key": deepcopy(key), "edges": edges,
            "distinct_pair_count": _cell(len(edges) if known_geometry else None, "coordinate_pair", inputs, state=state, reasons=reasons),
            "repeated_pair_occurrence_count": _cell(sum(map(len, by_pair.values())) - len(edges) if known_geometry else None,
                "pair_representation", inputs, state=state, reasons=reasons),
            "pair_geometry_support": support, "conflicts": conflicts, "mapping_state": mapping_state}


__all__ = ["DirectionalNumericalContractError", "calculate_protein_block",
           "union_position_intervals", "inspect_protein_correspondence"]
