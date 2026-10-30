"""One numerical sheet and calculator for supplied residue correspondence.

Native formats, program scores, coordinate decoding and source custody belong
to their adapters.  This module only evaluates explicit measured columns,
validated intervals and population qualifications.  It never executes an
aligner, chooses an action, opens a file or assigns annotation credit.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re


SHEET_SCHEMA = "alignment_correspondence_sheet_v1"
COMPONENT_SCHEMA = "alignment_correspondence_components_v1"
ARTIFACT_SCHEMA = "alignment_correspondence_artifacts_v1"
BASE_COUNT_NAMES = (
    "alignment_columns", "paired_positions", "identical_positions",
    "query_gap_columns", "reference_gap_columns",
    "query_aligned_positions", "reference_aligned_positions",
)
COUNT_NAMES = BASE_COUNT_NAMES + ("substituted_positions",)
_AXES = ("query", "reference")
_ROW_FIELDS = {"source_key", "measurement_input", "paired_lengths", "span_inputs",
    "geometry_available", "pairs", "symbol_widths",
    "reported_alignment_identity_fallback"}
_PAIR_FIELDS = {"query_start", "query_end", "reference_start", "reference_end", "identical"}


def _fail(code, path=""):
    raise ValueError("alignment_correspondence_" + code + (":" + path if path else ""))


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(child) for child in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _copy(child) for key, child in value.items()}
    _fail("finite_json_required")


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False)


def _closed(value, fields, path):
    if type(value) is not dict or set(value) != set(fields):
        _fail("closed_fields_required", path)


def _length(value, path):
    if value is not None and (type(value) is not int or value < 0):
        _fail("nonnegative_integer_required", path)


def _interval(value, path, length=None):
    if value is None:
        return
    if (type(value) is not list or len(value) != 2
            or any(type(item) is not int for item in value)
            or not 0 <= value[0] < value[1]
            or length is not None and value[1] > length):
        _fail("interval_invalid", path)


def _ratio(numerator, denominator):
    return numerator / denominator if numerator is not None and denominator else None


def _substituted(paired, identical):
    return paired - identical if paired is not None and identical is not None else None


def _nongap(columns, gaps):
    return columns - gaps if columns is not None and gaps is not None else None


def total_gap_columns(counts):
    query, reference = counts.get("query_gap_columns"), counts.get("reference_gap_columns")
    return query + reference if query is not None and reference is not None else None


def reported_column_measurements(*, alignment_columns, identical_positions,
        positive_positions, gap_columns):
    """Qualify explicit native counts without pretending they are a traceback."""
    values = {"alignment_columns": alignment_columns, "identical_positions": identical_positions,
        "positive_positions": positive_positions, "gap_columns": gap_columns}
    for name, value in values.items():
        _length(value, "/reported_counts/" + name)
    issues, usable_identity = [], identical_positions
    for field in ("identical_positions", "positive_positions", "gap_columns"):
        value = values[field]
        if alignment_columns is not None and value is not None and value > alignment_columns:
            issues.append({"code": "reported_count_exceeds_alignment_length", "field": field})
            if field == "identical_positions":
                usable_identity = None
    paired = (_nongap(alignment_columns, gap_columns)
        if alignment_columns is not None and gap_columns is not None and gap_columns <= alignment_columns else None)
    if paired is not None and usable_identity is not None and usable_identity > paired:
        issues.append({"code": "reported_identity_exceeds_paired_columns"})
        usable_identity = None
    if paired is not None and positive_positions is not None and positive_positions > paired:
        issues.append({"code": "reported_positive_exceeds_paired_columns"})
    if positive_positions is not None and identical_positions is not None and positive_positions < identical_positions:
        issues.append({"code": "reported_positive_below_identity"})
    return {"alignment_columns": alignment_columns, "paired_positions": paired,
        "identical_positions": usable_identity, "query_gap_columns": None,
        "reference_gap_columns": None, "query_aligned_positions": None,
        "reference_aligned_positions": None}, issues


def count_literal_alignment_columns(query, reference):
    """Count the caller-validated equal-width literal columns, without coercion.

    Callers own alphabet/case normalization and rejection of double gaps.  The
    unchanged primitive is also used by the distinct all-placement scanner.
    """
    query_gaps, reference_gaps = query.count("-"), reference.count("-")
    paired = _nongap(len(query), query_gaps + reference_gaps)
    identical = sum(a == b and a != "-" for a, b in zip(query, reference))
    return {"alignment_columns": len(query), "paired_positions": paired,
        "identical_positions": identical,
        "substituted_positions": _substituted(paired, identical),
        "query_gap_columns": query_gaps, "reference_gap_columns": reference_gaps,
        "query_aligned_positions": _nongap(len(query), query_gaps),
        "reference_aligned_positions": _nongap(len(reference), reference_gaps)}


def interval_union_length(intervals):
    """Length of validated half-open intervals in one original-operand unit.

    Inputs may be lists or tuples, in either order, with overlap, adjacency or
    repetition.  Callers validate the nonnegative coordinate domain first.
    """
    boundary, total = None, 0
    for start, end in sorted((row[0], row[1]) for row in intervals):
        total += end - start if boundary is None else max(0, end - max(start, boundary))
        boundary = end if boundary is None else max(boundary, end)
    return total


def interval_length(interval):
    """Width of an explicit validated interval; absent input remains absent."""
    _interval(interval, "/interval")
    return interval[1] - interval[0] if interval is not None else None


def _counts(measurement, path):
    if type(measurement) is not dict:
        _fail("measurement_input_required", path)
    kind = measurement.get("kind")
    if kind == "literal_columns":
        _closed(measurement, {"kind", "query", "reference"}, path)
        query, reference = measurement["query"], measurement["reference"]
        if (type(query) is not str or type(reference) is not str or not query
                or len(query) != len(reference)
                or re.fullmatch(r"[A-Za-z*\-]+", query) is None
                or re.fullmatch(r"[A-Za-z*\-]+", reference) is None
                or any(a == b == "-" for a, b in zip(query, reference))):
            _fail("literal_columns_invalid", path)
        values = count_literal_alignment_columns(query, reference)
    elif kind == "validated_saved_counts":
        _closed(measurement, {"kind", "basis", "counts"}, path)
        if measurement["basis"] not in ("traceback", "native_reported", "validated_saved"):
            _fail("saved_count_basis_invalid", path + "/basis")
        _closed(measurement["counts"], BASE_COUNT_NAMES, path + "/counts")
        values = measurement["counts"]
    elif kind in ("explicit_no_alignment", "unavailable"):
        _closed(measurement, {"kind"}, path)
        values = dict.fromkeys(BASE_COUNT_NAMES, 0 if kind == "explicit_no_alignment" else None)
    else:
        _fail("measurement_kind_invalid", path)
    values = {name: values[name] for name in BASE_COUNT_NAMES}
    for name, value in values.items():
        _length(value, path + "/" + name)
    columns, paired, identical = (values[name] for name in (
        "alignment_columns", "paired_positions", "identical_positions"))
    if (columns is not None and paired is not None and paired > columns
            or columns is not None and identical is not None and identical > columns
            or paired is not None and identical is not None and identical > paired):
        _fail("count_relationship_invalid", path)
    for axis in _AXES:
        gap, aligned = values[axis + "_gap_columns"], values[axis + "_aligned_positions"]
        if columns is not None and (gap is not None and gap > columns
                or aligned is not None and aligned > columns
                or gap is not None and aligned is not None and aligned != columns - gap):
            _fail("count_relationship_invalid", path + "/" + axis)
    if all(values[name] is not None for name in (
            "alignment_columns", "paired_positions", "query_gap_columns", "reference_gap_columns")):
        if paired != columns - values["query_gap_columns"] - values["reference_gap_columns"]:
            _fail("count_relationship_invalid", path + "/paired_positions")
    return values


def _row(value, index, operands):
    path = "/rows/" + str(index)
    _closed(value, _ROW_FIELDS, path)
    if type(value["source_key"]) is not str:
        _fail("source_key_required", path)
    counts = _counts(value["measurement_input"], path + "/measurement_input")
    _closed(value["paired_lengths"], _AXES, path + "/paired_lengths")
    _closed(value["span_inputs"], _AXES, path + "/span_inputs")
    _closed(value["symbol_widths"], _AXES, path + "/symbol_widths")
    for axis in _AXES:
        length = value["paired_lengths"][axis]
        _length(length, path + "/paired_lengths/" + axis)
        if length != operands[axis]["length"]:
            _fail("operand_length_conflict", path + "/paired_lengths/" + axis)
        span = value["span_inputs"][axis]
        _closed(span, {"interval", "length"}, path + "/span_inputs/" + axis)
        _length(span["length"], path + "/span_inputs/" + axis + "/length")
        _interval(span["interval"], path + "/span_inputs/" + axis + "/interval", span["length"])
        width = value["symbol_widths"][axis]
        if width is not None and (type(width) is not int or width not in (1, 3)):
            _fail("symbol_width_invalid", path + "/symbol_widths/" + axis)
    if type(value["geometry_available"]) is not bool or type(value["pairs"]) is not list:
        _fail("geometry_required", path)
    if value["pairs"] and not value["geometry_available"]:
        _fail("unavailable_geometry_has_pairs", path)
    for ordinal, pair in enumerate(value["pairs"]):
        _closed(pair, _PAIR_FIELDS, path + "/pairs/" + str(ordinal))
        if type(pair["identical"]) is not bool:
            _fail("pair_identity_invalid", path + "/pairs/" + str(ordinal))
        for axis in _AXES:
            interval = [pair[axis + "_start"], pair[axis + "_end"]]
            _interval(interval, path + "/pairs/" + str(ordinal) + "/" + axis,
                value["paired_lengths"][axis])
            width = value["symbol_widths"][axis]
            if width is not None and interval[1] - interval[0] != width:
                _fail("pair_width_conflict", path + "/pairs/" + str(ordinal) + "/" + axis)
    if value["geometry_available"]:
        if (counts["paired_positions"] is not None and len(value["pairs"]) != counts["paired_positions"]
                or counts["identical_positions"] is not None and sum(
                    pair["identical"] for pair in value["pairs"]) != counts["identical_positions"]):
            _fail("pair_count_conflict", path)
    fallback = value["reported_alignment_identity_fallback"]
    if fallback is not None and (type(fallback) not in (int, float) or not 0 <= fallback <= 1):
        _fail("reported_identity_invalid", path)
    return {**deepcopy(value), "measured_counts": counts}


def populate_correspondence_sheet(*, operands, rows, population, selected_intervals):
    """Populate one closed common sheet from explicit source-qualified facts."""
    operands, rows, population, selected_intervals = _copy([
        operands, rows, population, selected_intervals])
    _closed(operands, {"query", "reference", "alignment_unit"}, "/operands")
    for axis in _AXES:
        _closed(operands[axis], {"length", "unit"}, "/operands/" + axis)
        _length(operands[axis]["length"], "/operands/" + axis + "/length")
        if operands[axis]["unit"] not in (None, "nt", "aa"):
            _fail("unit_invalid", "/operands/" + axis)
    if operands["alignment_unit"] not in (None, "nt", "aa") or type(rows) is not list:
        _fail("operands_or_rows_invalid")
    _closed(population, {"original_rows_complete", "execution_state", "producer_state",
        "explicit_zero_result"}, "/population")
    if (population["original_rows_complete"] is not None and type(population["original_rows_complete"]) is not bool
            or population["execution_state"] not in ("completed", "failed", "unknown")
            or population["producer_state"] not in ("complete", "incomplete", "unknown")
            or type(population["explicit_zero_result"]) is not bool):
        _fail("population_invalid")
    _closed(selected_intervals, _AXES, "/selected_intervals")
    for axis in _AXES:
        _interval(selected_intervals[axis], "/selected_intervals/" + axis, operands[axis]["length"])
    measured_rows = [_row(row, i, operands) for i, row in enumerate(rows)]
    if population["explicit_zero_result"] and (
            population["execution_state"] == "failed" or population["producer_state"] == "incomplete"
            or any(row["pairs"] or any(value is not None and value > 0
                for value in row["measured_counts"].values()) for row in measured_rows)):
        _fail("explicit_zero_population_conflict", "/population/explicit_zero_result")
    return {"schema": SHEET_SCHEMA, "operands": operands,
        "rows": measured_rows,
        "population": population, "selected_intervals": selected_intervals}


def _validate_sheet(sheet):
    _closed(sheet, {"schema", "operands", "rows", "population", "selected_intervals"}, "")
    if sheet["schema"] != SHEET_SCHEMA or type(sheet["rows"]) is not list:
        _fail("sheet_required")
    rows = []
    for i, row in enumerate(sheet["rows"]):
        _closed(row, _ROW_FIELDS | {"measured_counts"}, "/rows/" + str(i))
        rows.append({key: row[key] for key in _ROW_FIELDS})
    rebuilt = populate_correspondence_sheet(operands=sheet["operands"], rows=rows,
        population=sheet["population"], selected_intervals=sheet["selected_intervals"])
    if not _same(sheet, rebuilt):
        _fail("saved_sheet_conflict")


def _row_components(row):
    counts = deepcopy(row["measured_counts"])
    derived = []
    for axis in _AXES:
        name = axis + "_aligned_positions"
        if counts[name] is None:
            value = _nongap(counts["alignment_columns"], counts[axis + "_gap_columns"])
            if value is not None:
                counts[name] = value
                derived.append(name)
    counts["substituted_positions"] = _substituted(
        counts["paired_positions"], counts["identical_positions"])
    geometry = row["geometry_available"]
    zero = row["measurement_input"]["kind"] == "explicit_no_alignment"
    paired_units, aligned_units, spans = {}, {}, {}
    for axis in _AXES:
        paired_units[axis] = (interval_union_length(
            (pair[axis + "_start"], pair[axis + "_end"]) for pair in row["pairs"])
            if geometry else 0 if zero else None)
        symbols, width = counts[axis + "_aligned_positions"], row["symbol_widths"][axis]
        aligned_units[axis] = symbols * width if (geometry or zero) and symbols is not None and width is not None else None
        interval = row["span_inputs"][axis]["interval"]
        spans[axis] = interval_length(interval)
    fractions = {"paired_identity": _ratio(counts["identical_positions"], counts["paired_positions"]),
        "alignment_identity": (_ratio(counts["identical_positions"], counts["alignment_columns"])
            if counts["identical_positions"] is not None and counts["alignment_columns"]
            else row["reported_alignment_identity_fallback"])}
    for axis in _AXES:
        fractions[axis + "_paired_coverage"] = _ratio(paired_units[axis], row["paired_lengths"][axis])
        fractions[axis + "_aligned_coverage"] = _ratio(aligned_units[axis], row["paired_lengths"][axis])
        fractions[axis + "_span_coverage"] = _ratio(spans[axis], row["span_inputs"][axis]["length"])
    return {"counts": counts, "derived_count_fields": derived + ["substituted_positions"],
        "paired_units": paired_units, "aligned_units": aligned_units,
        "span_positions": spans, "fractions": fractions,
        "paired_lengths": deepcopy(row["paired_lengths"]),
        "span_lengths": {axis: row["span_inputs"][axis]["length"] for axis in _AXES},
        "geometry_available": geometry}


def _mapping_conflicts(pairs, axis):
    other = "reference" if axis == "query" else "query"
    active, conflicts = [], []
    for index, row in sorted(enumerate(pairs), key=lambda item: (
            item[1][axis + "_start"], item[1][axis + "_end"], item[0])):
        active = [(i, old) for i, old in active if old[axis + "_end"] > row[axis + "_start"]]
        for i, old in active:
            fields = (axis + "_start", axis + "_end", other + "_start", other + "_end")
            if tuple(old[field] for field in fields) != tuple(row[field] for field in fields):
                conflicts.append({"code": "alternative_residue_mapping", "operand": axis,
                    "pair_indices": [i, index]})
        active.append((index, row))
    return conflicts


def _union(sheet):
    by_pair, signatures, representations = {}, {}, []
    rows = sheet["rows"]
    for index, row in enumerate(rows):
        keys = []
        for pair in row["pairs"]:
            key = tuple(pair[name] for name in ("query_start", "query_end", "reference_start", "reference_end"))
            keys.append(key)
            item = by_pair.setdefault(key, {"identity_values": set(), "row_indices": []})
            item["identity_values"].add(pair["identical"])
            if index not in item["row_indices"]:
                item["row_indices"].append(index)
            representations.append((*key, pair["identical"]))
        if row["geometry_available"]:
            signatures.setdefault(tuple(sorted(keys)), []).append(index)
    pairs, identity_conflicts = [], []
    for key, value in sorted(by_pair.items()):
        identity = next(iter(value["identity_values"])) if len(value["identity_values"]) == 1 else None
        if identity is None:
            identity_conflicts.append({"code": "identity_at_correspondence_conflicts",
                "pair_index": len(pairs), "row_indices": value["row_indices"]})
        pairs.append({**dict(zip(("query_start", "query_end", "reference_start", "reference_end"), key)),
            "identical": identity, "row_indices": value["row_indices"]})
    conflicts = identity_conflicts + _mapping_conflicts(pairs, "query") + _mapping_conflicts(pairs, "reference")
    mapped = sum(row["geometry_available"] for row in rows)
    complete = bool(rows) and mapped == len(rows)
    covered = {axis: interval_union_length((p[axis + "_start"], p[axis + "_end"]) for p in pairs)
        for axis in _AXES}
    unique_representations = set(representations)
    groups = [indices for indices in signatures.values() if len(indices) > 1]
    counts = {"supplied_rows": len(rows), "distinct_residue_pairs": len(pairs),
        "identical_residue_pairs": sum(p["identical"] is True for p in pairs) if pairs and not identity_conflicts else None,
        "rows_with_geometry": mapped, "rows_without_geometry": len(rows) - mapped,
        "distinct_position_identity_pairs": len(unique_representations),
        "identical_position_identity_pairs": sum(pair[-1] for pair in unique_representations),
        "overlap_pair_representations": len(representations) - len(unique_representations),
        "conflicting_mapping_count": len(conflicts), "identical_mapping_group_count": len(groups),
        **{axis + "_paired_positions": covered[axis] for axis in _AXES}}
    fractions = {"paired_identity": _ratio(sum(p["identical"] is True for p in pairs), len(pairs))
        if pairs and not conflicts else None}
    for axis in _AXES:
        fraction = _ratio(covered[axis], sheet["operands"][axis]["length"])
        fractions[axis + "_observed_coverage"] = fraction if mapped else None
        fractions[axis + "_supplied_complete_coverage"] = fraction if complete else None
        fractions[axis + "_original_complete_coverage"] = fraction if complete and sheet["population"]["original_rows_complete"] is True else None
    return {"pairs": pairs, "counts": counts, "fractions": fractions,
        "complete_for_supplied_rows": complete, "position_counts_available": bool(pairs) or complete,
        "identical_mapping_row_groups": groups,
        "conflicts": conflicts}


def _selected(sheet, union):
    population = sheet["population"]
    complete = union["complete_for_supplied_rows"] and population["original_rows_complete"] is True
    execution_qualified = complete and population["execution_state"] != "failed" and population["producer_state"] != "incomplete"
    successful = population["execution_state"] == "completed" and population["producer_state"] == "complete"
    result = {}
    for axis in _AXES:
        interval = sheet["selected_intervals"][axis]
        denominator = interval_length(interval)
        observed = None
        if interval is not None:
            pieces = [(max(pair[axis + "_start"], interval[0]), min(pair[axis + "_end"], interval[1]))
                for pair in union["pairs"] if pair[axis + "_start"] < interval[1] and pair[axis + "_end"] > interval[0]]
            observed = interval_union_length(pieces) if pieces or complete else None
        qualified = observed if execution_qualified else 0 if population["explicit_zero_result"] and interval is not None else None
        success_numerator = (observed if complete else 0 if population["explicit_zero_result"]
            and interval is not None else None) if successful else None
        result[axis] = {"observed_numerator": observed, "denominator": denominator,
            "complete_numerator": observed if complete else None,
            "complete_value": _ratio(observed, denominator) if complete else None,
            "execution_qualified_numerator": qualified,
            "execution_qualified_value": _ratio(qualified, denominator),
            "execution_success_numerator": success_numerator,
            "execution_success_value": _ratio(success_numerator, denominator),
            "complete_for_original_rows": complete}
    return result


def _definitions(operands):
    """The canonical meanings, independent of legacy field names or sources."""
    def field(formula, inputs, unit, population, denominator=None, missing=None):
        return {"formula": formula, "input_fields": inputs, "unit": unit,
            "population": population, "denominator": denominator,
            "missing_behavior": missing or "null when a required source measurement is unavailable",
            "uncertainty": None}
    unit = operands["alignment_unit"]
    rows = {
        "alignment_columns": field("number of supplied literal columns, or explicit validated count",
            ["rows.measurement_input"], "alignment_columns", "one supplied alignment"),
        "paired_positions": field("columns having two nongap symbols, or explicit validated count",
            ["rows.measurement_input"], "symbol_pairs", "one supplied alignment"),
        "identical_positions": field("paired columns with literal equal normalized symbols, or explicit validated count",
            ["rows.measurement_input"], "symbol_pairs", "one supplied alignment"),
        "substituted_positions": field("paired_positions - identical_positions",
            ["rows.measured_counts.paired_positions", "rows.measured_counts.identical_positions"],
            "symbol_pairs", "one supplied alignment"),
        "paired_identity": field("identical_positions / paired_positions",
            ["rows.measured_counts.identical_positions", "rows.measured_counts.paired_positions"],
            "fraction", "paired columns of one supplied alignment", "rows.measured_counts.paired_positions",
            "null for missing numerator or missing/zero denominator"),
        "alignment_identity": field("identical_positions / alignment_columns; otherwise the explicit native fraction fallback",
            ["rows.measured_counts.identical_positions", "rows.measured_counts.alignment_columns",
             "rows.reported_alignment_identity_fallback"], "fraction", "all columns of one supplied alignment",
            "rows.measured_counts.alignment_columns", "null when both derived fraction and explicit native fallback are unavailable"),
    }
    union = {
        "supplied_rows": field("count supplied correspondence rows", ["rows"], "rows", "supplied rows"),
        "distinct_residue_pairs": field("count distinct (query interval, reference interval) pairs",
            ["rows.pairs"], "position_pairs", "union of supplied checked correspondence rows"),
        "identical_residue_pairs": field("count identical distinct pairs when their identity agrees",
            ["rows.pairs"], "position_pairs", "union of supplied checked correspondence rows",
            missing="null for empty correspondence or conflicting identity at the same coordinate pair"),
        "paired_identity": field("identical distinct pairs / distinct pairs",
            ["rows.pairs"], "fraction", "union of supplied checked correspondence rows",
            "union.counts.distinct_residue_pairs", "null for empty correspondence or any alternative mapping/identity conflict"),
        "rows_with_geometry": field("count rows with geometry_available true",
            ["rows.geometry_available"], "rows", "all supplied rows"),
        "rows_without_geometry": field("count rows with geometry_available false",
            ["rows.geometry_available"], "rows", "all supplied rows"),
        "distinct_position_identity_pairs": field("count distinct (query interval, reference interval, identity flag) tuples",
            ["rows.pairs"], "position_identity_pairs", "all observed supplied pair representations"),
        "identical_position_identity_pairs": field("count true identity flags among distinct position/identity tuples",
            ["rows.pairs"], "position_identity_pairs", "all observed supplied pair representations"),
        "overlap_pair_representations": field("supplied pair representations - distinct position/identity tuples",
            ["rows.pairs"], "representations", "all observed supplied pair representations"),
        "conflicting_mapping_count": field("count identity conflicts and overlapping alternative axis mappings",
            ["rows.pairs"], "conflicts", "observed correspondence union"),
        "identical_mapping_group_count": field("count groups of multiple geometry rows with identical coordinate-pair signatures",
            ["rows.pairs", "rows.geometry_available"], "groups", "supplied correspondence rows"),
    }
    selected = {}
    for axis in _AXES:
        axis_unit = operands[axis]["unit"]
        rows[axis + "_gap_columns"] = field("count columns having a gap on this axis, or explicit validated count",
            ["rows.measurement_input"], "alignment_columns", "one supplied alignment")
        rows[axis + "_aligned_positions"] = field("nongap symbols on this axis, or explicit validated count",
            ["rows.measurement_input"], unit, "one supplied alignment")
        rows[axis + "_paired_units"] = field("length of the union of checked paired intervals on this axis",
            ["rows.pairs", "rows.geometry_available"], axis_unit, "one supplied alignment",
            missing="null without geometry; zero for explicit no alignment")
        rows[axis + "_aligned_units"] = field("nongap symbols * units per symbol",
            ["rows.measured_counts." + axis + "_aligned_positions", "rows.symbol_widths." + axis,
             "rows.geometry_available"], axis_unit, "one supplied alignment",
            missing="null without geometry/width/counts; zero for explicit no alignment")
        rows[axis + "_span_positions"] = field("end - start of the independently checked endpoint interval",
            ["rows.span_inputs." + axis + ".interval"], axis_unit, "one supplied native endpoint span")
        for coverage, numerator, denominator in (
                ("paired", "paired_units", "paired_lengths"),
                ("aligned", "aligned_units", "paired_lengths"),
                ("span", "span_positions", "span_lengths")):
            rows[axis + "_" + coverage + "_coverage"] = field(
                numerator + " / " + denominator,
                ["rows." + numerator + "." + axis, "rows." + denominator + "." + axis],
                "fraction", "explicitly qualified " + coverage + " axis of one supplied alignment",
                "rows." + denominator + "." + axis,
                "null for missing numerator or missing/zero denominator; paired/aligned quantities require checked geometry or explicit no alignment")
        union[axis + "_paired_positions"] = field("length(union(all checked paired intervals on this axis))",
            ["rows.pairs"], axis_unit, "observed correspondence union")
        for qualifier in ("observed", "supplied_complete", "original_complete"):
            union[axis + "_" + qualifier + "_coverage"] = field(
                "union paired positions / explicit operand length",
                ["rows.pairs", "rows.geometry_available", "population.original_rows_complete",
                 "operands." + axis + ".length"], "fraction", qualifier + " correspondence union",
                "operands." + axis + ".length",
                "null without mapped rows or positive length; supplied_complete additionally requires every supplied row geometry; original_complete also requires original_rows_complete true")
        selected[axis] = field("length(union(paired intervals clipped to the supplied selection)) / selection width",
            ["rows.pairs", "selected_intervals." + axis, "population"], "fraction",
            "explicitly supplied numerical interval; observed, original-complete, legacy non-disqualification and known-success populations remain separate",
            "selected_intervals." + axis + "[1] - selected_intervals." + axis + "[0]",
            "absent selection stays null; incomplete observations may retain a lower-bound numerator; execution_qualified_* retains legacy non-disqualification (not failed/incomplete), where unknown is not successful execution; execution_success_* additionally requires explicit completed execution AND complete producer, plus original/geometry completeness or an established explicit-zero result")
    return {"rows": rows, "union": union, "selected": selected,
        "coordinate_system": "zero_based_half_open_original_operand",
        "native_scores": "Native algorithm scores and significance remain in source envelopes; none are combined or converted to confidence here."}


def calculate_correspondence_components(sheet):
    """Evaluate this same saved sheet for every native correspondence adapter."""
    sheet = _copy(sheet)
    _validate_sheet(sheet)
    rows = [_row_components(row) for row in sheet["rows"]]
    union = _union(sheet)
    return {"schema": COMPONENT_SCHEMA, "rows": rows, "union": union,
        "selected": _selected(sheet, union), "definitions": _definitions(sheet["operands"])}


def validate_correspondence_artifacts(value, *, admission=False):
    """Validate custody shape; admission alone evaluates the saved numerical sheet.

    Frozen readers compare stored facts and legacy projections in their source
    adapters. They never call the numerical calculator through this function.
    """
    value = _copy(value)
    _closed(value, {"version", "instances"}, "/correspondence")
    if value["version"] != ARTIFACT_SCHEMA or type(value["instances"]) is not list:
        _fail("artifacts_required")
    seen = set()
    for index, instance in enumerate(value["instances"]):
        path = "/instances/" + str(index)
        _closed(instance, {"legacy_pointer", "axis_basis", "sheet", "components"}, path)
        pointer, basis = instance["legacy_pointer"], instance["axis_basis"]
        if (type(pointer) is not str or pointer and not pointer.startswith("/")
                or re.search(r"~(?![01])", pointer) is not None
                or basis not in ("direct", "reported", "qualified")
                or (pointer, basis) in seen):
            _fail("artifact_address_invalid", path)
        seen.add((pointer, basis))
        sheet, components = instance["sheet"], instance["components"]
        _closed(sheet, {"schema", "operands", "rows", "population", "selected_intervals"}, path + "/sheet")
        _closed(components, {"schema", "rows", "union", "selected", "definitions"}, path + "/components")
        if (sheet["schema"] != SHEET_SCHEMA or components["schema"] != COMPONENT_SCHEMA
                or type(sheet["rows"]) is not list or type(components["rows"]) is not list
                or len(sheet["rows"]) != len(components["rows"])):
            _fail("artifact_schemas_invalid", path)
        if admission and not _same(calculate_correspondence_components(sheet), components):
            _fail("saved_components_conflict", path)
    return value


__all__ = ["SHEET_SCHEMA", "COMPONENT_SCHEMA", "ARTIFACT_SCHEMA", "BASE_COUNT_NAMES",
    "COUNT_NAMES", "count_literal_alignment_columns", "interval_union_length", "interval_length",
    "reported_column_measurements", "total_gap_columns",
    "populate_correspondence_sheet", "calculate_correspondence_components", "validate_correspondence_artifacts"]
