"""Numerical correspondence sheets for supplied ``sequence_ops.align_pair`` results.

Reading a native result and calculating from its saved sheet are separate pure
operations. Neither operation imports Biopython, executes an alignment, chooses
a resource, assigns annotation credit, or estimates functional confidence.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .alignment_correspondence import (
    ARTIFACT_SCHEMA, BASE_COUNT_NAMES, count_literal_alignment_columns,
    populate_correspondence_sheet, calculate_correspondence_components,
    _ratio as _fraction,
)

SHEET_SCHEMA = "biopython_pairwise_sheet_v1"
_COUNT_FIELDS = (
    "alignment_columns", "paired_positions", "identical_positions",
    "substituted_positions", "query_gap_columns", "reference_gap_columns",
    "query_aligned_positions", "reference_aligned_positions",
)
_REPORTED_FIELDS = (
    "paired_positions", "identical_positions", "identity_fraction",
    "query_coverage", "reference_coverage",
)


def _require_json(value, code):
    """Reject nonfinite/non-JSON inputs without dropping or rewriting native data."""
    def check(item):
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise TypeError
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif item is not None and type(item) not in (bool, int, float, str):
            raise TypeError

    try:
        check(value)
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(code) from error


def _number(value, field, issues, *, integer=False, minimum=None, maximum=None,
            required=False):
    if value is None:
        if required:
            issues.append({"code": "measurement_missing", "field": field})
        return None
    if (type(value) not in ((int,) if integer else (int, float))
            or minimum is not None and value < minimum
            or maximum is not None and value > maximum):
        issues.append({"code": "measurement_invalid", "field": field})
        return None
    return value


def _count_columns(query, reference):
    return count_literal_alignment_columns(query, reference)


def _traceback(native, issues):
    query, reference = native.get("aligned_query"), native.get("aligned_reference")
    if query is None and reference is None:
        issues.append({"code": "traceback_missing"})
        return {"status": "unavailable", "query": None, "reference": None}, None
    if (type(query) is not str or type(reference) is not str or not query
            or len(query) != len(reference)
            or re.fullmatch(r"[A-Za-z*\-]+", query) is None
            or re.fullmatch(r"[A-Za-z*\-]+", reference) is None):
        issues.append({"code": "traceback_strings_invalid"})
        return {"status": "invalid", "query": None, "reference": None}, None
    query, reference = query.upper(), reference.upper()
    if any(a == b == "-" for a, b in zip(query, reference)):
        issues.append({"code": "double_gap_alignment_column"})
        return {"status": "invalid", "query": query, "reference": reference}, None
    return ({"status": "valid", "query": query, "reference": reference},
            _count_columns(query, reference))


def _empty_geometry():
    return {"available": False, "coordinate_system": "zero_based_half_open",
            "coordinates": None, "query_interval": None, "reference_interval": None,
            "operand_bounds_checked": {"query": False, "reference": False}}


def _geometry(native, traceback, counts, lengths, mode, issues):
    """Check the entire path, including placement of gaps, before mapping positions."""
    empty = _empty_geometry()
    coordinates = native.get("coordinates")
    if coordinates is None:
        issues.append({"code": "coordinate_path_missing"})
        return empty, []
    if (type(coordinates) is not list or len(coordinates) != 2
            or any(type(axis) is not list for axis in coordinates)
            or len(coordinates[0]) < 2 or len(coordinates[0]) != len(coordinates[1])
            or any(type(p) is not int or p < 0 for axis in coordinates for p in axis)):
        issues.append({"code": "coordinate_path_invalid"})
        return empty, []
    deltas = [(coordinates[0][i+1] - coordinates[0][i],
               coordinates[1][i+1] - coordinates[1][i])
              for i in range(len(coordinates[0])-1)]
    if any(dq < 0 or dr < 0 or dq == dr == 0 or dq and dr and dq != dr
           for dq, dr in deltas):
        issues.append({"code": "coordinate_step_invalid"})
        return empty, []
    if sum(max(dq, dr) for dq, dr in deltas) != counts["alignment_columns"]:
        issues.append({"code": "coordinate_traceback_length_conflict"})
        return empty, []
    invalid = False
    intervals = {}
    for index, axis in enumerate(("query", "reference")):
        start, end = coordinates[index][0], coordinates[index][-1]
        interval = native.get(axis + "_interval")
        consumed = counts[axis + "_aligned_positions"]
        if consumed == 0 and interval is None:
            intervals[axis] = None
        elif (type(interval) is not list or len(interval) != 2
                or any(type(p) is not int or p < 0 for p in interval)
                or interval[0] >= interval[1]):
            issues.append({"code": "alignment_interval_invalid", "operand": axis})
            invalid = True
        elif interval != [start, end]:
            issues.append({"code": "coordinate_interval_conflict", "operand": axis})
            invalid = True
        else:
            intervals[axis] = interval
        if end - start != consumed:
            issues.append({"code": "coordinate_traceback_span_conflict", "operand": axis})
            invalid = True
        if lengths[axis] is not None and end > lengths[axis]:
            issues.append({"code": "coordinates_outside_operand", "operand": axis})
            invalid = True
        if mode == "global" and (start != 0 or lengths[axis] is not None and end != lengths[axis]):
            issues.append({"code": "global_alignment_operand_span_conflict", "operand": axis})
            invalid = True
    if invalid:
        return empty, []
    rows, column = [], 0
    for segment, (dq, dr) in enumerate(deltas):
        for offset in range(max(dq, dr)):
            a, b = traceback["query"][column], traceback["reference"][column]
            if (a != "-") != bool(dq) or (b != "-") != bool(dr):
                issues.append({"code": "coordinate_traceback_gap_conflict", "column": column})
                return empty, []
            rows.append({"column": column,
                "query_position": coordinates[0][segment] + offset if dq else None,
                "reference_position": coordinates[1][segment] + offset if dr else None,
                "query_symbol": a if dq else None, "reference_symbol": b if dr else None,
                "relationship": ("query_gap" if not dq else "reference_gap" if not dr
                                 else "identical" if a == b else "substituted")})
            column += 1
    return {"available": True, "coordinate_system": "zero_based_half_open",
            "coordinates": deepcopy(coordinates),
            "query_interval": deepcopy(intervals["query"]),
            "reference_interval": deepcopy(intervals["reference"]),
            "operand_bounds_checked": {axis: lengths[axis] is not None for axis in lengths}}, rows


def _no_alignment_conflict(native):
    detail_fields = ("aligned_query", "aligned_reference", "coordinates",
                     "query_interval", "reference_interval")
    return (any(native.get(field) not in (None, "", []) for field in detail_fields)
            or any(native.get(field) not in (None, 0) for field in _REPORTED_FIELDS))


def _common_sheet(*, counts, lengths, geometry, correspondence, alignment_state, molecule):
    """Adapt measured cells; never manufacture another producer's traceback."""
    if alignment_state == "no_alignment":
        measurement = {"kind": "explicit_no_alignment"}
    elif counts is None or all(value is None for value in counts.values()):
        measurement = {"kind": "unavailable"}
    else:
        measurement = {"kind": "validated_saved_counts", "basis": "traceback",
            "counts": {name: counts[name] for name in BASE_COUNT_NAMES}}
    available = geometry["available"]
    pairs = [{"query_start": row["query_position"], "query_end": row["query_position"] + 1,
        "reference_start": row["reference_position"], "reference_end": row["reference_position"] + 1,
        "identical": row["relationship"] == "identical"}
        for row in correspondence if row["query_position"] is not None and row["reference_position"] is not None]
    unit = "aa" if molecule == "protein" else "nt"
    return populate_correspondence_sheet(
        operands={"query": {"length": lengths["query"], "unit": unit},
            "reference": {"length": lengths["reference"], "unit": unit}, "alignment_unit": unit},
        rows=[{"source_key": "", "measurement_input": measurement,
            "paired_lengths": dict(lengths),
            "span_inputs": {axis: {"interval": deepcopy(geometry[axis + "_interval"]) if available else None,
                "length": lengths[axis]} for axis in ("query", "reference")},
            "geometry_available": available, "pairs": pairs,
            "symbol_widths": {"query": 1, "reference": 1},
            "reported_alignment_identity_fallback": None}],
        population={"original_rows_complete": True, "execution_state": "unknown",
            "producer_state": "unknown", "explicit_zero_result": alignment_state == "no_alignment"},
        selected_intervals={"query": None, "reference": None})


def correspondence_sheet_from_biopython(sheet, *, validate=True):
    """Project an existing legacy envelope into the common numerical sheet.

    Production/saved calculations validate the complete legacy sheet first.
    Retained-artifact readers can compare its already authenticated saved cells
    without invoking a whole-alignment calculator again.
    """
    if validate:
        _validate_sheet(sheet)
    return _common_sheet(counts=sheet["measured_column_counts"], lengths=sheet["lengths"],
        geometry=sheet["geometry"], correspondence=sheet["residue_correspondence"],
        alignment_state=sheet["alignment_state"], molecule=sheet["molecule"])


def build_biopython_pairwise_sheet(native: dict, *, molecule: str) -> dict:
    """Extract finite native facts and validated correspondence without scoring.

    Strings supply column counts even if coordinates are invalid. Positional
    coverage requires the full path to agree with strings, intervals, available
    operand lengths, and local/global mode. The supplied result does not contain
    original unaligned sequence symbols, so those cannot be reconstructed.

    Nonfinite/non-JSON inputs fail at the boundary. Finite malformed individual
    measurements are retained verbatim in ``native_result`` and have issues and
    null validated components. ``aligned=False`` is an explicit zero result;
    missing traceback for ``aligned=True`` supplies no zero measurements.

    ``biopython_pairwise_native_v2`` deliberately omits derived convenience
    measurements. Markerless legacy results retain their original required
    reported-field checks; any supplied reported values still retain conflicts.
    Both formats populate this same sheet and use the same calculator.
    """
    if type(native) is not dict:
        raise ValueError("biopython_pairwise_native_object_required")
    _require_json(native, "finite_json_biopython_pairwise_native_required")
    if type(molecule) is not str or molecule not in {"protein", "dna", "rna"}:
        raise ValueError("biopython_pairwise_molecule_required")
    if type(native.get("aligned")) is not bool:
        raise ValueError("biopython_pairwise_aligned_boolean_required")
    if type(native.get("mode")) is not str or native["mode"] not in {"local", "global"}:
        raise ValueError("biopython_pairwise_mode_required")
    native_format = native.get("native_format")
    if native_format is not None and native_format != "biopython_pairwise_native_v2":
        raise ValueError("biopython_pairwise_native_format_unknown")
    issues = []
    aligned = native["aligned"]
    lengths = {axis: _number(native.get(axis + "_length"), axis + "_length", issues,
                            integer=True, minimum=0, required=True)
               for axis in ("query", "reference")}
    matrix = native.get("matrix")
    if type(matrix) is not str or not matrix:
        issues.append({"code": "native_matrix_missing_or_invalid"})
        matrix = None
    parameters = {"matrix": matrix,
        **{field: _number(native.get(field), field, issues, required=aligned)
           for field in ("gap_open", "gap_extend")}}
    score = _number(native.get("native_score"), "native_score", issues, required=aligned)
    reported = {field: _number(native.get(field), field, issues,
        integer=field.endswith("positions"), minimum=0,
        maximum=None if field.endswith("positions") else 1,
        required=aligned and native_format is None)
        for field in _REPORTED_FIELDS}
    counts = None
    geometry, correspondence = _empty_geometry(), []
    if aligned:
        traceback, counts = _traceback(native, issues)
        if counts is not None:
            geometry, correspondence = _geometry(native, traceback, counts, lengths, native["mode"], issues)
        alignment_state = "alignment"
    elif _no_alignment_conflict(native):
        issues.append({"code": "no_alignment_has_alignment_data"})
        traceback = {"status": "conflicting", "query": None, "reference": None}
        alignment_state = "conflicting"
    else:
        traceback = {"status": "no_alignment", "query": None, "reference": None}
        counts = dict.fromkeys(_COUNT_FIELDS, 0)
        alignment_state = "no_alignment"
    if counts is not None:
        for field in ("paired_positions", "identical_positions"):
            if reported[field] is not None and reported[field] != counts[field]:
                issues.append({"code": "reported_count_traceback_conflict", "field": field,
                               "reported": reported[field], "measured": counts[field]})
        common = calculate_correspondence_components(_common_sheet(counts=counts, lengths=lengths,
            geometry=geometry, correspondence=correspondence, alignment_state=alignment_state,
            molecule=molecule))["rows"][0]
        fractions = {"identity_fraction": common["fractions"]["paired_identity"]}
        if geometry["available"] or alignment_state == "no_alignment":
            fractions.update({axis + "_coverage": common["fractions"][axis + "_aligned_coverage"]
                              for axis in ("query", "reference")})
        for field, measured in fractions.items():
            if (reported[field] is not None and measured is not None
                    and not math.isclose(reported[field], measured, rel_tol=1e-12, abs_tol=1e-15)):
                issues.append({"code": "reported_fraction_traceback_conflict", "field": field,
                               "reported": reported[field], "measured": measured})
    if reported["identical_positions"] is not None and reported["paired_positions"] is not None:
        if reported["identical_positions"] > reported["paired_positions"]:
            issues.append({"code": "reported_identity_exceeds_paired_positions"})
    status = ("partial" if issues else "no_alignment" if alignment_state == "no_alignment" else "complete")
    if aligned and counts is None:
        status = "alignment_data_unavailable"
    return {
        "schema": SHEET_SCHEMA, "status": status, "native_result": deepcopy(native),
        "molecule": molecule, "mode": native["mode"], "aligned": aligned,
        "alignment_state": alignment_state, "native_parameters": parameters,
        "native_score": score, "lengths": lengths, "reported_measurements": reported,
        "traceback": traceback,
        "measured_column_counts": counts if counts is not None else dict.fromkeys(_COUNT_FIELDS),
        "geometry": geometry, "residue_correspondence": correspondence, "issues": issues,
        "symbol_interpretation": {
            "reader_normalization": "uppercase_of_native_traceback_symbols",
            "native_nucleotide_normalization": "U_to_T_before_alignment" if molecule != "protein" else None,
            "identity": "literal_normalized_symbol_equality_without_ambiguity_resolution",
        },
        "limitations": ["only_the_supplied_native_alignment_is_available_not_all_optimal_alternatives",
                        "original_unaligned_sequence_symbols_are_not_present_in_this_native_result",
                        "native_score_is_not_database_significance_or_function_confidence"],
    }


def _validate_sheet(sheet):
    if type(sheet) is not dict or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("biopython_pairwise_sheet_required")
    _require_json(sheet, "finite_json_biopython_pairwise_sheet_required")
    error = "biopython_pairwise_sheet_components_invalid"
    try:
        if (sheet["molecule"] not in ("dna", "rna", "protein")
                or sheet["mode"] not in ("local", "global") or type(sheet["aligned"]) is not bool
                or sheet["alignment_state"] not in ("alignment", "no_alignment", "conflicting")
                or type(sheet["issues"]) is not list or type(sheet["status"]) is not str):
            raise ValueError(error)
        counts, lengths = sheet["measured_column_counts"], sheet["lengths"]
        geometry, traceback = sheet["geometry"], sheet["traceback"]
        if (type(counts) is not dict or set(counts) != set(_COUNT_FIELDS)
                or type(lengths) is not dict or set(lengths) != {"query", "reference"}
                or type(geometry) is not dict or type(geometry["available"]) is not bool
                or type(traceback) is not dict or type(sheet["residue_correspondence"]) is not list
                or any(v is not None and (type(v) is not int or v < 0)
                       for v in (*counts.values(), *lengths.values()))
                or sheet["native_score"] is not None and type(sheet["native_score"]) not in (int, float)):
            raise ValueError(error)
        no_alignment = sheet["alignment_state"] == "no_alignment"
        if no_alignment:
            if sheet["aligned"] or traceback["status"] != "no_alignment" or any(v != 0 for v in counts.values()):
                raise ValueError(error)
        elif traceback["status"] == "valid":
            validation_issues = []
            checked, measured = _traceback({"aligned_query": traceback["query"],
                "aligned_reference": traceback["reference"]}, validation_issues)
            if not sheet["aligned"] or validation_issues or measured != counts or checked != traceback:
                raise ValueError(error)
        elif any(v is not None for v in counts.values()):
            raise ValueError(error)
        if geometry["available"]:
            validation_issues = []
            checked, correspondence = _geometry(geometry, traceback, counts, lengths, sheet["mode"], validation_issues)
            if (no_alignment or validation_issues or checked != geometry
                    or correspondence != sheet["residue_correspondence"]):
                raise ValueError(error)
        elif sheet["residue_correspondence"]:
            raise ValueError(error)
    except (KeyError, TypeError, AttributeError, IndexError) as exception:
        raise ValueError(error) from exception


def _definitions(molecule):
    unit = "amino_acid_positions" if molecule == "protein" else "nucleotide_positions"
    formulas = {
        "alignment_columns": "len(traceback.query)",
        "paired_positions": "count(columns where query and reference are both nongap)",
        "identical_positions": "count(paired columns with literal equal uppercase symbols)",
        "substituted_positions": "paired_positions - identical_positions",
        "query_gap_columns": "count(traceback.query symbols equal to '-')",
        "reference_gap_columns": "count(traceback.reference symbols equal to '-')",
        "query_aligned_positions": "alignment_columns - query_gap_columns",
        "reference_aligned_positions": "alignment_columns - reference_gap_columns",
        "paired_identity": "identical_positions / paired_positions",
        "alignment_identity": "identical_positions / alignment_columns",
        "query_paired_coverage": "paired_positions / lengths.query, with validated geometry",
        "reference_paired_coverage": "paired_positions / lengths.reference, with validated geometry",
        "query_aligned_coverage": "query_aligned_positions / lengths.query, with validated geometry",
        "reference_aligned_coverage": "reference_aligned_positions / lengths.reference, with validated geometry",
        "native_score": "native_result.native_score, unchanged",
    }
    ratio_inputs = {
        "paired_identity": ("measured_column_counts.identical_positions", "measured_column_counts.paired_positions"),
        "alignment_identity": ("measured_column_counts.identical_positions", "measured_column_counts.alignment_columns"),
        "query_paired_coverage": ("measured_column_counts.paired_positions", "lengths.query"),
        "reference_paired_coverage": ("measured_column_counts.paired_positions", "lengths.reference"),
        "query_aligned_coverage": ("measured_column_counts.query_aligned_positions", "lengths.query"),
        "reference_aligned_coverage": ("measured_column_counts.reference_aligned_positions", "lengths.reference"),
    }
    definitions = {}
    for name, formula in formulas.items():
        fraction = name.endswith(("identity", "coverage"))
        inputs = (["native_score"] if name == "native_score" else
                  list(ratio_inputs[name]) if fraction else ["measured_column_counts." + name])
        if name.endswith("coverage"):
            inputs += ["geometry.available", "alignment_state"]
        definitions[name] = {
            "formula": formula,
            "inputs": inputs,
            "measurement_source": ("native_result.native_score" if name == "native_score"
                                   else ["native_result.aligned_query", "native_result.aligned_reference"]),
            "denominator": "denominators." + name if fraction else None,
            "units": "fraction" if fraction else "native_alignment_score" if name == "native_score"
                     else "alignment_columns" if name.endswith("columns") else unit,
            "population": ("full_query_operand" if name.startswith("query_") and name.endswith("coverage") else
                           "full_reference_operand" if name.startswith("reference_") and name.endswith("coverage") else
                           "paired_alignment_columns" if name == "paired_identity" else "supplied_native_alignment"),
            "kind": "native_algorithm_score" if name == "native_score" else "derived_from_native_alignment",
            "missing": ("null_when_native_score_missing_or_invalid" if name == "native_score" else
                        "null_when_geometry_invalid_or_length_missing_or_zero; explicit_no_alignment_uses_zero_positions"
                        if name.endswith("coverage") else
                        "null_when_count_missing_or_denominator_zero" if fraction else
                        "null_when_traceback_unavailable_or_invalid; zero_for_explicit_no_alignment"),
            "coordinate_system": "zero_based_half_open" if name.endswith("coverage") else None,
            "uncertainty": None,
        }
    return definitions


def project_biopython_scores(sheet, common):
    """Select the legacy score cells from stored common calculated cells."""
    counts = {name: common["counts"][name] for name in _COUNT_FIELDS}
    lengths = common["paired_lengths"]
    denominators = {"paired_identity": counts["paired_positions"],
        "alignment_identity": counts["alignment_columns"],
        "query_paired_coverage": lengths["query"], "reference_paired_coverage": lengths["reference"],
        "query_aligned_coverage": lengths["query"], "reference_aligned_coverage": lengths["reference"]}
    return {"schema": "biopython_pairwise_scores_v1", "status": sheet["status"], **counts,
        **{field: common["fractions"][field] for field in denominators},
        "native_score": sheet["native_score"], "denominators": denominators,
        "definitions": _definitions(sheet["molecule"]), "issues": deepcopy(sheet["issues"])}


def _calculate_biopython_artifacts(sheet):
    """Calculate inspectable components from saved counts and validated geometry.

    A no-alignment result contributes zero positions, with null identity (zero
    denominator). Missing or inconsistent geometry never produces positional
    coverage, even when the native producer reported a coverage fraction.
    """
    _validate_sheet(sheet)
    common_sheet = correspondence_sheet_from_biopython(sheet, validate=False)
    common_components = calculate_correspondence_components(common_sheet)
    scores = project_biopython_scores(sheet, common_components["rows"][0])
    return scores, common_sheet, common_components


def calculate_biopython_pairwise_scores(sheet: dict) -> dict:
    """Calculate the legacy view through the same common numerical authority."""
    return _calculate_biopython_artifacts(sheet)[0]


def grade_biopython_pairwise(native: dict, *, molecule: str,
                             _retain_correspondence: bool = False) -> dict:
    """Read once and calculate once; the caller owns retention and publication."""
    if type(_retain_correspondence) is not bool:
        raise ValueError("biopython_correspondence_retention_boolean_required")
    sheet = build_biopython_pairwise_sheet(native, molecule=molecule)
    scores, common, calculated = _calculate_biopython_artifacts(sheet)
    result = {"sheet": sheet, "scores": scores}
    if _retain_correspondence:
        result["correspondence"] = {"version": ARTIFACT_SCHEMA,
            "instances": [{"legacy_pointer": "", "axis_basis": "direct", "sheet": common,
                "components": calculated}]}
    return result


def validate_biopython_correspondence(grading, instance):
    """Compare retained facts/projections without regrading a frozen source."""
    from .alignment_correspondence import _same
    expected = correspondence_sheet_from_biopython(grading["sheet"], validate=False)
    if (instance["legacy_pointer"] != "" or instance["axis_basis"] != "direct"
            or not _same(expected, instance["sheet"])
            or not _same(project_biopython_scores(grading["sheet"], instance["components"]["rows"][0]), grading["scores"])):
        raise ValueError("biopython_saved_correspondence_conflict")


__all__ = ["build_biopython_pairwise_sheet", "calculate_biopython_pairwise_scores",
           "grade_biopython_pairwise", "count_literal_alignment_columns"]
