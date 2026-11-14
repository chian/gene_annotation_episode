"""Pure, unweighted CA superposition and independently selected evaluation.

The retained sheet is sufficient for every calculation here. Parameters choose
membership and tolerances explicitly. Native uncertainty is preserved input, not
a fit weight or a probability of function. All transforms use moving y @ R + t
in the fixed frame. No function performs I/O or executes an alignment.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Literal

import numpy as np
from jsonschema import Draft202012Validator, validators

from .execution_contracts import canonical, digest
from .protein_structure_contracts import (
    Correspondence, CoordinatePair, PairSelection, ResolvedPairSelection,
    NumericalParameters, FitResult, DeclaredTransform, TransformResult,
    ProteinStructureSheet, CalculationParameters, ProteinStructureComponents,
    NumberCell, VectorCell, MatrixCell, SiteMeasurement, CoordinateSet,
    CountComponents, CoverageComponents, AlignmentComponents, EvaluationComponents,
    protein_structure_schema_definitions, protein_structure_schema_ref,
    validate_correspondence, validate_declared_transform_record,
    validate_calculation_parameters, validate_protein_structure_sheet,
    validate_protein_structure_components, same, issue,
)
from .protein_structure_sequences import residue_position_key
from .protein_structure_sheet import _numerical_digest, _validate_input_relationships


_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, v: type(v) is int)
    .redefine("number", lambda _, v: type(v) in (int, float) and _finite_number(v)))
_SCHEMAS = protein_structure_schema_definitions()
_VALIDATORS = {name: _STRICT({"$defs": _SCHEMAS, **protein_structure_schema_ref(name)})
    for name in ("CoordinatePair", "PairSelection", "ResolvedPairSelection", "NumericalParameters", "FitResult", "TransformResult")}


def _finite_number(value):
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError):
        return False


def _shape(name, value):
    """Reuse A's exact subrecord schemas; the numerical lane adds relationships."""
    try:
        if not _VALIDATORS[name].is_valid(value):
            raise ValueError("invalid_schema")
        _cells(value)
    except (KeyError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error
    return deepcopy(value)


def _cells(value):
    if isinstance(value, list):
        for item in value:
            _cells(item)
    elif isinstance(value, dict):
        if set(value) == {"value", "state", "reason", "unit", "origin"}:
            if ((value["state"] == "present") != (value["value"] is not None)
                    or (value["state"] == "present") != (value["reason"] is None)):
                raise ValueError("invalid_schema")
        for item in value.values():
            _cells(item)


def _cell(value=None, *, unit="angstrom", origin="derived", state="unavailable", reason="calculation_not_performed"):
    return {"value": deepcopy(value), "state": "present" if value is not None else state,
            "reason": None if value is not None else reason, "unit": unit, "origin": origin}


def _unique(values, code="duplicate_selection"):
    if len({canonical(value) for value in values}) != len(values):
        raise ValueError(code)


def _qualifications(values):
    return list(dict.fromkeys(values))


def _numerical(value):
    result = _shape("NumericalParameters", value)
    if any(number < 0 for number in result.values()):
        raise ValueError("invalid_schema")
    return result


_PRECEDENCE = {code: index for index, code in enumerate((
    "unmapped_site", "invalid_coordinate_identity", "ambiguous_residue_variant",
    "ambiguous_ca", "ca_missing", "nonfinite_coordinate", "invalid_occupancy", "zero_occupancy_excluded"))}


def _pair_reason(pair):
    reasons = [pair[side + "_ca_state"]["primary_reason"] for side in ("fixed", "moving")
               if pair[side + "_ca_state"]["state"] != "available"]
    return min(reasons, key=lambda reason: _PRECEDENCE.get(reason, len(_PRECEDENCE))) if reasons else None


def _pairs(values):
    if type(values) is not list:
        raise ValueError("invalid_schema")
    result = [_shape("CoordinatePair", value) for value in values]
    _unique([p["correspondence_id"] for p in result])
    for side in ("fixed", "moving"):
        _unique([p[side + "_position_0based"] for p in result])
    for pair in result:
        for side in ("fixed", "moving"):
            ca, xyz, key = (pair[side + "_ca_state"], pair[side + "_xyz_A"], pair[side + "_atom_row_key"])
            _unique(ca["candidate_atom_row_keys"], "invalid_coordinate_identity")
            if key != ca["selected_atom_row_key"] or key is not None and key not in ca["candidate_atom_row_keys"]:
                raise ValueError("invalid_coordinate_identity")
            if ((ca["state"] == "available") != (xyz["state"] == "present")
                    or (ca["state"] == "available") != (ca["primary_reason"] is None)
                    or ca["state"] == "available" and key is None
                    or xyz["unit"] != "angstrom" or xyz["origin"] != "observed"):
                raise ValueError("invalid_coordinate_identity")
            if ca["state"] != "available" and (xyz["reason"] != ca["primary_reason"]
                    or xyz["state"] != ("invalid" if ca["state"] == "invalid" else "unavailable")):
                raise ValueError("invalid_coordinate_identity")
    return result


def _selection(value):
    result = _shape("PairSelection", value)
    if result["kind"] == "explicit":
        if not result["members"]:
            raise ValueError("invalid_schema")
        _unique(result["members"])
    return result


def resolve_pair_selection(correspondence: Correspondence, coordinate_pairs: list[CoordinatePair], *,
                           selection: PairSelection) -> ResolvedPairSelection:
    corr, pairs, selected = validate_correspondence(correspondence), _pairs(coordinate_pairs), _selection(selection)
    mapped = [row for row in corr["rows"] if row["fixed_position_0based"] is not None and row["moving_position_0based"] is not None]
    if [p["correspondence_id"] for p in pairs] != [r["correspondence_id"] for r in mapped]:
        raise ValueError("conflicting_identity")
    for row, pair in zip(mapped, pairs):
        for side in ("fixed", "moving"):
            if (pair[side + "_position_0based"] != row[side + "_position_0based"]
                    or not same(pair[side + "_ca_state"], row[side + "_ca"])):
                raise ValueError("conflicting_identity")
    pair_by_id = {p["correspondence_id"]: p for p in pairs}
    rows_by_id = {row["correspondence_id"]: row for row in corr["rows"]}
    members = ([{"kind": "correspondence_id", "correspondence_id": row["correspondence_id"]} for row in mapped]
               if selected["kind"] == "all_mapped_pairs" and corr["population_available"]
               else selected.get("members", []))
    result = {"selection": selected, "rows": [], "requested_count": None,
              "resolved_pair_count": None, "available_candidate_count": None}
    resolved_ids = []
    population = corr["population_available"]
    unknown_reason = next((i["code"] for i in corr["issues"]), "polymer_mapping_unavailable")
    for index, member in enumerate(members):
        row = None
        if population:
            if member["kind"] == "correspondence_id":
                row = rows_by_id.get(member["correspondence_id"])
                if row is None:
                    raise ValueError("map_endpoint_missing")
            else:
                side, position = member["structure_role"], member["position_0based"]
                row = next((r for r in corr["rows"] if r[side + "_position_0based"] == position), None)
                if row is None and not any(r["sequence_position_0based"] == position for r in corr["unmapped_" + side]):
                    raise ValueError("map_endpoint_missing")
        pair = pair_by_id.get(row["correspondence_id"]) if row is not None else None
        reason = unknown_reason if not population else "unmapped_site" if pair is None else _pair_reason(pair)
        cid = row["correspondence_id"] if row else None
        if cid is not None:
            resolved_ids.append(cid)
        positions = {s + "_position_0based": row[s + "_position_0based"] if row else
                     member["position_0based"] if population and member["kind"] == "sequence_position" and member["structure_role"] == s else None
                     for s in ("fixed", "moving")}
        result["rows"].append({"request_index_0based": index, "selector": deepcopy(member),
            "correspondence_id": cid, **positions, "available": reason is None,
            "primary_reason": reason, "qualifications": _qualifications([
                q for s in ("fixed", "moving") for q in (pair[s + "_ca_state"]["qualifications"] if pair else [])])})
    _unique(resolved_ids)
    if population or selected["kind"] == "explicit":
        result["requested_count"] = len(members)
    if population:
        result["resolved_pair_count"] = sum(r["correspondence_id"] in pair_by_id for r in result["rows"])
        result["available_candidate_count"] = sum(r["available"] for r in result["rows"])
    return _shape("ResolvedPairSelection", result)


def _resolved(value, pairs):
    result = _shape("ResolvedPairSelection", value)
    selection = _selection(result["selection"])
    rows = result["rows"]
    if [r["request_index_0based"] for r in rows] != list(range(len(rows))):
        raise ValueError("conflicting_identity")
    if selection["kind"] == "explicit" and not same(selection["members"], [r["selector"] for r in rows]):
        raise ValueError("conflicting_identity")
    if selection["kind"] == "explicit" and result["requested_count"] != len(selection["members"]):
        raise ValueError("conflicting_identity")
    if result["requested_count"] is not None and result["requested_count"] != len(rows):
        raise ValueError("conflicting_identity")
    _unique([r["selector"] for r in rows])
    _unique([r["correspondence_id"] for r in rows if r["correspondence_id"] is not None])
    by_id = {p["correspondence_id"]: p for p in pairs}
    known = result["resolved_pair_count"] is not None
    if known != (result["available_candidate_count"] is not None) or known and result["requested_count"] is None:
        raise ValueError("conflicting_identity")
    if known and (result["resolved_pair_count"] != sum(r["correspondence_id"] in by_id for r in rows)
                  or result["available_candidate_count"] != sum(r["available"] for r in rows)):
        raise ValueError("conflicting_identity")
    for row in rows:
        pair = by_id.get(row["correspondence_id"])
        selector = row["selector"]
        if selector["kind"] == "correspondence_id" and row["correspondence_id"] is not None and selector["correspondence_id"] != row["correspondence_id"]:
            raise ValueError("conflicting_identity")
        if selector["kind"] == "sequence_position" and known and selector["position_0based"] != row[selector["structure_role"] + "_position_0based"]:
            raise ValueError("conflicting_identity")
        if selection["kind"] == "all_mapped_pairs" and selector["kind"] != "correspondence_id":
            raise ValueError("conflicting_identity")
        if row["available"] != (row["primary_reason"] is None) or row["available"] and (not known or pair is None):
            raise ValueError("conflicting_identity")
        if known and pair is not None:
            if any(row[s + "_position_0based"] != pair[s + "_position_0based"] for s in ("fixed", "moving")) or row["primary_reason"] != _pair_reason(pair):
                raise ValueError("conflicting_identity")
    return result


def _transform_empty(reason, *, state="unavailable", origin="fitted", issues=None):
    cell_state = "invalid" if state == "invalid" else "unavailable"
    return {"state": state, "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": _cell(unit="dimensionless", origin=origin, state=cell_state, reason=reason),
        "translation": _cell(unit="angstrom", origin=origin, state=cell_state, reason=reason),
        "issues": deepcopy(issues or []), "qualifications": ["minimum_only"] if state == "nonunique_fit" else []}


_FIT_UNITS = {
    "fixed_centroid": "angstrom", "moving_centroid": "angstrom", "cross_covariance": "angstrom_squared",
    "singular_values": "angstrom_squared", "fixed_geometry_singular_values": "angstrom",
    "moving_geometry_singular_values": "angstrom", "fixed_geometry_rank": "count", "moving_geometry_rank": "count",
    "cross_covariance_rank": "count", "uncorrected_rotation_determinant": "dimensionless",
    "reflection_correction_sign": "dimensionless", "fit_sse_raw_formula": "angstrom_squared",
    "fit_sse_roundoff_limit": "angstrom_squared", "fit_sse": "angstrom_squared",
    "fit_residual_sse": "angstrom_squared", "fit_rmsd": "angstrom"}


def _fit_empty(selection, reason, *, state="unavailable", transform=None):
    cell_state = "not_applicable" if state == "not_applicable" else "invalid" if state == "invalid" else "unavailable"
    return {"state": state, "selection": deepcopy(selection), "used_correspondence_ids": [], "excluded": [],
        **{field: _cell(unit=unit, origin="fitted", state=cell_state, reason=reason) for field, unit in _FIT_UNITS.items()},
        "transform": transform or _transform_empty(reason, state="invalid" if state == "invalid" else "unavailable"),
        "issues": [], "qualifications": []}


def _partition(request, policy, *, transform_available=True):
    if policy not in ("require_all", "use_available"):
        raise ValueError("invalid_schema")
    unknown = request["available_candidate_count"] is None
    all_failed = policy == "require_all" and any(not r["available"] for r in request["rows"])
    used, excluded = [], []
    for row in request["rows"]:
        reason = (row["primary_reason"] if not row["available"] else
                  "policy_requires_all" if all_failed or unknown else
                  "transform_unavailable" if not transform_available else None)
        if reason is None:
            used.append(row["correspondence_id"])
        else:
            excluded.append({"request_index_0based": row["request_index_0based"], "reason": reason})
    return used, excluded, unknown or all_failed


def _finite_array(value):
    array = np.asarray(value, dtype=np.float64)
    if not np.isfinite(array).all():
        raise FloatingPointError("nonfinite numerical result")
    return array


def _rank(singular, absolute, relative):
    limit = max(absolute, relative * float(singular[0]))
    if not math.isfinite(limit):
        raise FloatingPointError("nonfinite tolerance")
    return sum(float(s) > limit for s in singular)


def _sse_values(sx, sy, singular, sign, numerical):
    raw = math.fsum((sx, sy, -2 * float(singular[0]), -2 * float(singular[1]), -2 * sign * float(singular[2])))
    limit = max(numerical["sse_roundoff_absolute_tolerance_A2"],
        numerical["sse_roundoff_relative_tolerance"] * math.fsum((sx, sy, 2 * float(singular[0]), 2 * float(singular[1]), 2 * float(singular[2]))))
    if not all(math.isfinite(x) for x in (raw, limit)):
        raise FloatingPointError("nonfinite SSE")
    return raw, limit


def fit_ca_transform(pairs: list[CoordinatePair], *, fit_request: ResolvedPairSelection,
    missing_coordinate_policy: Literal["require_all", "use_available"],
    numerical_parameters: NumericalParameters) -> FitResult:
    pairs, numerical = _pairs(pairs), _numerical(numerical_parameters)
    request = _resolved(fit_request, pairs)
    used, excluded, failed = _partition(request, missing_coordinate_policy)
    reason = "incomplete_fit" if failed else "empty_fit"
    result = _fit_empty(request, reason)
    result["excluded"] = excluded
    if failed or not used:
        result["issues"] = [issue(reason, stage="fit", field="fit_selection")]
        if request["requested_count"] == 0:
            result["fit_rmsd"]["reason"] = "zero_denominator"
        return _shape("FitResult", result)
    by_id = {p["correspondence_id"]: p for p in pairs}
    result["used_correspondence_ids"] = used
    if excluded:
        result["qualifications"].append("available_subset_used")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            x = _finite_array([by_id[key]["fixed_xyz_A"]["value"] for key in used])
            y = _finite_array([by_id[key]["moving_xyz_A"]["value"] for key in used])
            xb, yb = _finite_array(x.mean(axis=0)), _finite_array(y.mean(axis=0))
            xc, yc = _finite_array(x - xb), _finite_array(y - yb)
            h = _finite_array(yc.T @ xc)
            u, singular, vt = np.linalg.svd(h, full_matrices=True)
            singular = _finite_array(singular)
            gsx = _finite_array(np.pad(np.linalg.svd(xc, compute_uv=False), (0, max(0, 3 - min(xc.shape)))))
            gsy = _finite_array(np.pad(np.linalg.svd(yc, compute_uv=False), (0, max(0, 3 - min(yc.shape)))))
            det = float(np.linalg.det(u @ vt))
            sign = 1 if det >= 0 else -1
            rh = _rank(singular, numerical["svd_absolute_tolerance_A2"], numerical["svd_relative_tolerance"])
            rx = _rank(gsx, numerical["geometry_absolute_tolerance_A"], numerical["svd_relative_tolerance"])
            ry = _rank(gsy, numerical["geometry_absolute_tolerance_A"], numerical["svd_relative_tolerance"])
            sx, sy = float(np.sum(xc * xc)), float(np.sum(yc * yc))
            raw, limit = _sse_values(sx, sy, singular, sign, numerical)
            values = {"fixed_centroid": xb.tolist(), "moving_centroid": yb.tolist(), "cross_covariance": h.tolist(),
                "singular_values": singular.tolist(), "fixed_geometry_singular_values": gsx.tolist(),
                "moving_geometry_singular_values": gsy.tolist(), "fixed_geometry_rank": rx, "moving_geometry_rank": ry,
                "cross_covariance_rank": rh, "uncorrected_rotation_determinant": det, "reflection_correction_sign": sign,
                "fit_sse_raw_formula": raw, "fit_sse_roundoff_limit": limit}
            for field, value in values.items():
                result[field] = _cell(value, unit=_FIT_UNITS[field], origin="fitted")
            if raw < -limit:
                raise FloatingPointError("negative SSE outside retained roundoff limit")
            sse = max(0.0, raw)
            result["fit_sse"] = _cell(sse, unit="angstrom_squared", origin="fitted")
            result["fit_rmsd"] = _cell(math.sqrt(sse / len(used)), unit="angstrom", origin="fitted")
            if raw < 0:
                result["qualifications"].append("numerical_roundoff_clamp")
            tie = sign < 0 and abs(float(singular[1] - singular[2])) <= max(
                numerical["svd_absolute_tolerance_A2"], numerical["svd_relative_tolerance"] * float(singular[0]))
            if len(used) < 3 or rh < 2 or tie:
                problem = issue("nonunique_fit", stage="fit", field="rotation")
                result.update(state="minimum_only", transform=_transform_empty("nonunique_fit", state="nonunique_fit", issues=[problem]), issues=[problem])
                result["fit_residual_sse"] = _cell(unit="angstrom_squared", origin="fitted", reason="nonunique_fit")
                result["qualifications"].append("minimum_only")
            else:
                rotation = _finite_array(u @ np.diag([1.0, 1.0, float(sign)]) @ vt)
                translation = _finite_array(xb - yb @ rotation)
                if (float(np.max(np.abs(rotation.T @ rotation - np.eye(3)))) > numerical["rotation_orthogonality_tolerance"]
                        or abs(float(np.linalg.det(rotation)) - 1) > numerical["rotation_determinant_tolerance"]):
                    raise FloatingPointError("fitted rotation outside retained numerical tolerances")
                residual = _finite_array(y @ rotation + translation - x)
                residual_sse = float(np.sum(residual * residual))
                if not math.isfinite(residual_sse) or abs(residual_sse - sse) > limit:
                    raise FloatingPointError("inconsistent residual and formula SSE")
                result.update(state="performed", transform={"state": "identifiable_fit", "direction": "moving_to_fixed",
                    "convention": "row_vector_y_R_plus_t", "rotation": _cell(rotation.tolist(), unit="dimensionless", origin="fitted"),
                    "translation": _cell(translation.tolist(), unit="angstrom", origin="fitted"), "issues": [], "qualifications": []})
                result["fit_residual_sse"] = _cell(residual_sse, unit="angstrom_squared", origin="fitted")
    except (FloatingPointError, OverflowError, np.linalg.LinAlgError, ValueError):
        problem = issue("numeric_inconsistency", stage="fit", field="fit_sse")
        result.update(state="invalid", transform=_transform_empty("numeric_inconsistency", state="invalid", issues=[problem]), issues=[problem])
        for field in _FIT_UNITS:
            if result[field]["value"] is None or field in ("fit_sse", "fit_residual_sse", "fit_rmsd"):
                result[field] = _cell(unit=_FIT_UNITS[field], origin="fitted", state="invalid", reason="numeric_inconsistency")
    return _shape("FitResult", result)


def validate_declared_transform(transform: DeclaredTransform, *,
                                numerical_parameters: NumericalParameters) -> TransformResult:
    declared, numerical = validate_declared_transform_record(transform), _numerical(numerical_parameters)
    origin = "supplied" if declared["origin"] == "supplied" else "fitted"
    valid = False
    try:
        with np.errstate(over="raise", invalid="raise"):
            rotation = _finite_array(declared["rotation"])
            orthogonality = float(np.max(np.abs(rotation.T @ rotation - np.eye(3))))
            determinant = float(np.linalg.det(rotation))
            valid = (math.isfinite(orthogonality) and math.isfinite(determinant)
                     and orthogonality <= numerical["rotation_orthogonality_tolerance"]
                     and abs(determinant - 1) <= numerical["rotation_determinant_tolerance"])
    except (FloatingPointError, OverflowError, np.linalg.LinAlgError):
        pass
    if not valid:
        return _transform_empty("invalid_transform", state="invalid", origin=origin,
            issues=[issue("invalid_transform", stage="input", field="rotation")])
    return {"state": "supplied", "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": _cell(declared["rotation"], unit="dimensionless", origin=origin),
        "translation": _cell(declared["translation_A"], origin=origin), "issues": [], "qualifications": []}


def _evaluate(pairs, request, fit, transform, parameters):
    available_transform = transform["state"] in ("identifiable_fit", "supplied")
    selected, excluded, failed = _partition(request, parameters["missing_coordinate_policy"],
                                           transform_available=available_transform)
    reason = ("incomplete_evaluation" if failed else "transform_unavailable" if not available_transform
              else "empty_evaluation")
    result = {"state": "unavailable", "selection": deepcopy(request), "used_correspondence_ids": [],
        "excluded": excluded, **{name: _cell(unit=unit, reason=reason) for name, unit in (
            ("evaluation_sse", "angstrom_squared"), ("evaluation_rmsd", "angstrom"),
            ("evaluation_mean_distance", "angstrom"), ("evaluation_min_distance", "angstrom"),
            ("evaluation_max_distance", "angstrom"), ("above_threshold_count", "count"),
            ("above_threshold_fraction", "fraction"))},
        "distance_threshold_A": _cell(parameters["distance_threshold_A"], origin="supplied",
            state="not_applicable", reason="not_requested"), "issues": []}
    threshold = parameters["distance_threshold_A"]
    if threshold is None:
        for name, unit in (("above_threshold_count", "count"), ("above_threshold_fraction", "fraction")):
            result[name] = _cell(unit=unit, state="not_applicable", reason="not_requested")
    elif request["requested_count"] == 0:
        result["above_threshold_fraction"]["reason"] = "zero_denominator"
    if request["requested_count"] == 0:
        for name in ("evaluation_rmsd", "evaluation_mean_distance"):
            result[name]["reason"] = "zero_denominator"
    by_id = {p["correspondence_id"]: p for p in pairs}
    excluded_by_index = {r["request_index_0based"]: r["reason"] for r in excluded}
    in_fit, selected = set(fit["used_correspondence_ids"]), set(selected)
    sites = []
    for row in request["rows"]:
        index, cid = row["request_index_0based"], row["correspondence_id"]
        unavailable = excluded_by_index.get(index, reason)
        site = {"request_index_0based": index, "selector": deepcopy(row["selector"]),
            "correspondence_id": cid, "fixed_position_0based": row["fixed_position_0based"],
            "moving_position_0based": row["moving_position_0based"], "in_fit": cid in in_fit,
            "in_evaluation": True, "evaluated": False, "primary_reason": unavailable,
            "moving_transformed_xyz": _cell(reason=unavailable), "residual_xyz": _cell(reason=unavailable),
            "distance_squared": _cell(unit="angstrom_squared", reason=unavailable),
            "distance": _cell(reason=unavailable), "above_threshold": None,
            "qualifications": deepcopy(row["qualifications"])}
        if cid in selected:
            pair = by_id[cid]
            try:
                with np.errstate(over="raise", invalid="raise", divide="raise"):
                    xyz = _finite_array(_finite_array(pair["moving_xyz_A"]["value"]) @
                        _finite_array(transform["rotation"]["value"]) + _finite_array(transform["translation"]["value"]))
                    residual = _finite_array(xyz - _finite_array(pair["fixed_xyz_A"]["value"]))
                    d2 = float(np.sum(residual * residual))
                    if not math.isfinite(d2):
                        raise FloatingPointError("nonfinite distance")
                    distance = math.sqrt(d2)
                site.update(evaluated=True, primary_reason=None,
                    moving_transformed_xyz=_cell(xyz.tolist()), residual_xyz=_cell(residual.tolist()),
                    distance_squared=_cell(d2, unit="angstrom_squared"), distance=_cell(distance),
                    above_threshold=None if threshold is None else distance > threshold)
                result["used_correspondence_ids"].append(cid)
            except (FloatingPointError, OverflowError, ValueError):
                site["primary_reason"] = "numeric_inconsistency"
                for name in ("moving_transformed_xyz", "residual_xyz", "distance_squared", "distance"):
                    site[name].update(state="invalid", reason="numeric_inconsistency")
                result["excluded"].append({"request_index_0based": index, "reason": "numeric_inconsistency"})
                result["issues"].append(issue("numeric_inconsistency", stage="evaluation", correspondence=cid, field="distance"))
        sites.append(site)
    result["excluded"].sort(key=lambda row: row["request_index_0based"])
    evaluated = [row for row in sites if row["evaluated"]]
    if result["issues"]:
        result["state"] = "invalid"
        for name in ("evaluation_sse", "evaluation_rmsd", "evaluation_mean_distance", "evaluation_min_distance", "evaluation_max_distance"):
            result[name].update(state="invalid", reason="numeric_inconsistency")
        if threshold is not None:
            for name in ("above_threshold_count", "above_threshold_fraction"):
                result[name].update(state="invalid", reason="numeric_inconsistency")
    elif evaluated:
        try:
            sse = math.fsum(row["distance_squared"]["value"] for row in evaluated)
            total = math.fsum(row["distance"]["value"] for row in evaluated)
            if not math.isfinite(sse) or not math.isfinite(total):
                raise OverflowError("nonfinite evaluation aggregate")
            distances = [row["distance"]["value"] for row in evaluated]
            result.update(state="performed", evaluation_sse=_cell(sse, unit="angstrom_squared"),
                evaluation_rmsd=_cell(math.sqrt(sse / len(evaluated))),
                evaluation_mean_distance=_cell(total / len(evaluated)),
                evaluation_min_distance=_cell(min(distances)), evaluation_max_distance=_cell(max(distances)))
            if threshold is not None:
                count = sum(row["above_threshold"] for row in evaluated)
                result.update(above_threshold_count=_cell(count, unit="count"),
                              above_threshold_fraction=_cell(count / len(evaluated), unit="fraction"))
        except (OverflowError, ValueError):
            result["state"] = "invalid"
            result["issues"] = [issue("numeric_inconsistency", stage="evaluation", field="distance")]
            for name in ("evaluation_sse", "evaluation_rmsd", "evaluation_mean_distance", "evaluation_min_distance", "evaluation_max_distance"):
                result[name] = _cell(unit="angstrom_squared" if name == "evaluation_sse" else "angstrom",
                    state="invalid", reason="numeric_inconsistency")
    else:
        result["issues"] = [issue("incomplete_evaluation" if failed or not available_transform else "empty_evaluation",
                                  stage="evaluation", field="evaluation_selection")]
    return result, sites


def _ratio(numerator, denominator, *, performed=True, reason="calculation_not_performed") -> NumberCell:
    if denominator == 0:
        return _cell(unit="fraction", reason="zero_denominator")
    if numerator is None or denominator is None or not performed:
        return _cell(unit="fraction", reason=reason)
    return _cell(numerator / denominator, unit="fraction")


def _summaries(sheet, parameters, fit, evaluation):
    corr, sequences = sheet["correspondence"], sheet["sequences"]
    reason = next((i["code"] for i in corr["issues"]), "polymer_mapping_unavailable")
    p = len(sheet["coordinate_pairs"]) if corr["population_available"] else None
    m = sum(_pair_reason(pair) is None for pair in sheet["coordinate_pairs"]) if p is not None else None
    counts = {"mapped_pair_count": _cell(p, unit="pair", reason=reason),
              "available_pair_count": _cell(m, unit="pair", reason=reason)}
    coverage = {}
    for side in ("fixed", "moving"):
        sequence = sequences[side]
        length = sequence["sequence_length"]
        coordinates = sum(row["ca"]["state"] == "available" for row in sequence["residues"]) if length is not None else None
        unmapped = length - p if length is not None and p is not None else None
        if unmapped is not None and unmapped < 0:
            raise ValueError("conflicting_identity")
        for name, value in (("sequence_length", length), ("coordinate_count", coordinates), ("unmapped_count", unmapped)):
            counts[side + "_" + name] = _cell(value, unit="residue", reason=reason)
        counts[side + "_declared_polymer_length"] = _cell(sequence["declared_polymer_length"], unit="residue", reason="not_supplied")
        coverage.update({side + "_correspondence_coverage": _ratio(p, length, reason=reason),
            side + "_coordinate_coverage": _ratio(coordinates, length, reason=reason),
            side + "_paired_coordinate_coverage": _ratio(m, length, reason=reason)})
    coverage["mapped_pair_coordinate_coverage"] = _ratio(m, p, reason=reason)
    for name, group in (("fit", fit), ("evaluation", evaluation)):
        if name == "fit" and parameters["mode"] == "evaluate_declared_transform_ca":
            for field in ("requested_count", "resolved_pair_count", "available_candidate_count", "used_count", "excluded_count"):
                unit = "count" if field in ("requested_count", "excluded_count") else "pair"
                counts[name + "_" + field] = _cell(unit=unit, state="not_applicable", reason="mode_not_applicable")
            coverage["fit_coverage"] = _cell(unit="fraction", state="not_applicable", reason="mode_not_applicable")
            continue
        request, used = group["selection"], len(group["used_correspondence_ids"])
        requested = request["requested_count"]
        for field in ("requested_count", "resolved_pair_count", "available_candidate_count"):
            counts[name + "_" + field] = _cell(request[field], unit="count" if field == "requested_count" else "pair", reason=reason)
        counts[name + "_used_count"] = _cell(used, unit="pair")
        counts[name + "_excluded_count"] = _cell(requested - used if requested is not None else None, unit="count", reason=reason)
        coverage[name + "_coverage"] = _ratio(used, requested,
            performed=group["state"] in ("performed", "minimum_only"), reason="calculation_not_performed")
    fields = ("alignment_score", "alignment_identity_count", "alignment_substitution_count", "alignment_column_count",
              "alignment_fixed_gap_count", "alignment_moving_gap_count")
    alignment = {field: _cell(unit="native_alignment_score" if field == "alignment_score" else "count",
        origin="observed" if field == "alignment_score" else "derived",
        state="not_applicable" if corr["origin"] == "explicit_map" else "unavailable",
        reason="mode_not_applicable" if corr["origin"] == "explicit_map" else reason) for field in fields}
    if corr["origin"] == "retained_alignment" and corr["alignment_native"] is not None:
        original = corr["alignment_native"]["pairwise_sheet"]
        original_counts = original["measured_column_counts"]
        query_fixed = sheet["input_identities"]["correspondence"]["orientation"] == "fixed_is_query"
        values = dict(zip(fields, (original["native_score"], original_counts["identical_positions"],
            original_counts["substituted_positions"], original_counts["alignment_columns"],
            original_counts["query_gap_columns" if query_fixed else "reference_gap_columns"],
            original_counts["reference_gap_columns" if query_fixed else "query_gap_columns"])))
        for field, value in values.items():
            alignment[field] = _cell(value, unit=alignment[field]["unit"], origin=alignment[field]["origin"], reason="no_alignment")
    return counts, coverage, alignment


def _raw_xyz(atom):
    if atom is None:
        return _cell(reason="no_coordinate_residue", origin="observed")
    if any(number["state"] != "present" for number in atom["xyz_A"]):
        return _cell(state="invalid", reason="nonfinite_coordinate", origin="observed")
    return _cell([number["value"] for number in atom["xyz_A"]], origin="observed")


def _coordinate_sets(sheet, parameters, transform) -> list[CoordinateSet]:
    outputs = []
    for selected in parameters["coordinate_sets"]:
        side = selected["structure_role"]
        sequence, parsed = sheet["sequences"][side], sheet["structures"][side]
        selection = sequence["selection"]
        length, residues = sequence["sequence_length"], sequence["residues"]
        members = selected["members"]
        positions = (list(range(len(residues))) if members["kind"] == "all_selected_chain" else members["positions"])
        if members["kind"] == "sequence_positions" and length is not None and any(p >= length for p in positions):
            raise ValueError("map_endpoint_missing")
        position_set = set(positions)
        atoms = {atom["identity"]["atom_row_key"]: atom for atom in parsed["atoms"]}
        output = {"selection": deepcopy(selected), "state": "complete", "rows": [],
            "requested_position_count": length if members["kind"] == "all_selected_chain" else len(positions),
            "atom_row_count": 0, "issues": []}

        def append(atom, residue, position, *, ca=False):
            cell = _raw_xyz(atom)
            if ca and residue is not None and residue["ca"]["state"] != "available":
                cell = _cell(state="invalid" if residue["ca"]["state"] == "invalid" else "unavailable",
                    reason=residue["ca"]["primary_reason"], origin="observed")
            if residue is None and atom is None:
                cell = _cell(reason="polymer_mapping_unavailable", origin="observed")
            problems = []
            key = atom["identity"]["atom_row_key"] if atom else None
            if selected["frame"] == "moving_in_fixed_frame":
                if cell["state"] == "present" and transform["state"] not in ("identifiable_fit", "supplied"):
                    cell = _cell(reason="transform_unavailable")
                elif cell["state"] == "present":
                    try:
                        with np.errstate(over="raise", invalid="raise"):
                            cell = _cell(_finite_array(_finite_array(cell["value"]) @
                                _finite_array(transform["rotation"]["value"]) + _finite_array(transform["translation"]["value"])).tolist())
                    except (FloatingPointError, OverflowError, ValueError):
                        cell = _cell(state="invalid", reason="numeric_inconsistency")
                        problems.append(issue("numeric_inconsistency", stage="evaluation", role=side,
                            atom=key, position=residue["position_key"] if residue else None, field="coordinate_set"))
                else:
                    cell["origin"] = "derived"
            if cell["state"] != "present" and cell["reason"] in _PRECEDENCE:
                problems.append(issue(cell["reason"], stage="selection", role=side, atom=key,
                    position=residue["position_key"] if residue else None, field="xyz"))
            output["rows"].append({"row_index_0based": len(output["rows"]), "atom_row_key": key,
                "sequence_position_0based": position,
                "residue_identity": deepcopy(atom["identity"]["residue"] if atom else residue["selected_residue_identity"] if residue else None),
                "declared_residue_identity": deepcopy(residue["no_coordinate_identity"] if residue else None),
                "atom_identity": deepcopy(atom["identity"] if atom else None), "xyz": cell, "issues": problems})
            output["issues"].extend(deepcopy(problems))

        if selected["atom_scope"] == "selected_ca":
            for position in positions:
                residue = residues[position] if position < len(residues) else None
                atom = atoms.get(residue["ca"]["selected_atom_row_key"]) if residue else None
                append(atom, residue, position, ca=True)
        else:
            block = selection["data_block"]["ordinal_0based"] if selection["data_block"] else None
            chain = next((row for row in parsed["chains"] if row["block_ordinal_0based"] == block
                and same(row["model_key"], selection["model_key"]) and same(row["chain_key"], selection["chain_key"])), None)
            keys = set(chain["atom_row_keys"]) if chain else set()
            by_position = {canonical(row["position_key"]): row for row in residues}
            seen_positions = set()
            for atom in parsed["atoms"]:
                if atom["identity"]["atom_row_key"] not in keys:
                    continue
                native_residue = atom["identity"]["residue"]
                key = residue_position_key(native_residue) if native_residue is not None else None
                residue = by_position.get(canonical(key)) if key is not None else None
                position = residue["sequence_position_0based"] if residue else None
                if members["kind"] == "sequence_positions" and position not in position_set:
                    continue
                append(atom, residue, position)
                if position is not None:
                    seen_positions.add(position)
            # No invented atoms: placeholder rows explicitly preserve declared
            # positions absent from the raw native atom population.
            for position in positions:
                if position not in seen_positions:
                    append(None, residues[position] if position < len(residues) else None, position)
        output["atom_row_count"] = sum(row["atom_row_key"] is not None for row in output["rows"])
        if any(problem["code"] == "numeric_inconsistency" for problem in output["issues"]):
            output["state"] = "invalid"
        elif length is None or any(row["xyz"]["state"] != "present" for row in output["rows"]):
            output["state"] = "partial" if output["rows"] else "unavailable"
        outputs.append(output)
    return outputs


def _overall(fit, evaluation, coordinates, counts, sites):
    if fit["state"] == "invalid" or fit["transform"]["state"] == "invalid" or evaluation["state"] == "invalid" or any(c["state"] == "invalid" for c in coordinates):
        return "invalid"
    if (fit["state"] in ("performed", "not_applicable") and evaluation["state"] == "performed"
            and not fit["excluded"] and not evaluation["excluded"] and all(c["state"] == "complete" for c in coordinates)):
        return "complete"
    if any(cell["state"] == "present" for cell in counts.values()) or any(row["evaluated"] for row in sites):
        return "partial"
    return "unavailable"


def calculate_protein_structure_components(sheet: ProteinStructureSheet, *,
    parameters: CalculationParameters) -> ProteinStructureComponents:
    sheet, parameters = validate_protein_structure_sheet(sheet), validate_calculation_parameters(parameters)
    _validate_input_relationships(sheet)
    # A saved calculation can change mode and selections explicitly. Its source
    # map, file identities and original native request are never rewritten.
    declared = parameters["declared_transform"]
    if declared is not None:
        for side in ("fixed", "moving"):
            if not same(declared[side + "_selection"], sheet["sequences"][side]["selection"]):
                raise ValueError("invalid_transform")
        transform = validate_declared_transform(declared, numerical_parameters=parameters["numerical"])
        fit = _fit_empty(None, "mode_not_applicable", state="not_applicable", transform=transform)
    else:
        selection = resolve_pair_selection(sheet["correspondence"], sheet["coordinate_pairs"], selection=parameters["fit_selection"])
        fit = fit_ca_transform(sheet["coordinate_pairs"], fit_request=selection,
            missing_coordinate_policy=parameters["missing_coordinate_policy"], numerical_parameters=parameters["numerical"])
        transform = fit["transform"]
    evaluation_request = resolve_pair_selection(sheet["correspondence"], sheet["coordinate_pairs"], selection=parameters["evaluation_selection"])
    evaluation, sites = _evaluate(sheet["coordinate_pairs"], evaluation_request, fit, transform, parameters)
    coordinates = _coordinate_sets(sheet, parameters, transform)
    counts, coverage, alignment = _summaries(sheet, parameters, fit, evaluation)
    numerical_hash = _numerical_digest(sheet)
    qualifications = _qualifications(sheet["source_qualifications"] + fit["qualifications"]
        + (["available_subset_used"] if evaluation["state"] == "performed" and evaluation["excluded"] else [])
        + (["threshold_is_descriptive"] if parameters["distance_threshold_A"] is not None else []))
    result = {"version": "protein_structure_components_v1",
        "calculation_id": "protein_structure_calculation_" + digest({"input_numerical_sha256": numerical_hash, "parameters": parameters}),
        "input_numerical_sha256": numerical_hash, "parameters": parameters,
        "state": _overall(fit, evaluation, coordinates, counts, sites), "counts": counts, "coverage": coverage,
        "alignment": alignment, "fit": fit, "transform": deepcopy(transform), "evaluation": evaluation,
        "site_measurements": sites, "coordinate_sets": coordinates,
        "issues": deepcopy(sheet["parse_issues"] + sheet["correspondence_issues"] + fit["issues"] +
            transform["issues"] + evaluation["issues"] + [i for c in coordinates for i in c["issues"]]),
        "qualifications": qualifications}
    return validate_protein_structure_components(result)


def _require(condition, code="numeric_inconsistency"):
    if not condition:
        raise ValueError(code)


def _near(actual, expected, *, absolute, relative):
    """Arithmetic validation tolerance, never an experimental uncertainty."""
    a, b = _finite_array(actual), _finite_array(expected)
    _require(a.shape == b.shape)
    with np.errstate(over="raise", invalid="raise"):
        bound = absolute + relative * np.maximum(np.abs(a), np.abs(b))
        _require(bool(np.all(np.abs(a - b) <= bound)))


def _recorded_cell(cell, expected, *, unit, numerical, origin="fitted", absolute=None):
    _require(cell["state"] == "present" and cell["reason"] is None and cell["unit"] == unit
             and cell["origin"] == origin)
    if unit in ("count", "pair", "residue"):
        _require(type(cell["value"]) is int and cell["value"] == expected)
        return
    if absolute is None:
        absolute = (numerical["geometry_absolute_tolerance_A"] if unit == "angstrom" else
                    numerical["sse_roundoff_absolute_tolerance_A2"] if unit == "angstrom_squared" else
                    numerical["rotation_orthogonality_tolerance"])
    _near(cell["value"], expected, absolute=absolute, relative=numerical["svd_relative_tolerance"])


def _check_spectrum(matrix, singular, *, absolute, relative):
    """Validate retained singular values by Gram invariants, without an SVD.

    For a matrix with three columns the three nonnegative singular values are
    determined by the elementary symmetric polynomials of Gram eigenvalues.
    Scaling keeps the check from needlessly overflowing those polynomials.
    """
    matrix, singular = _finite_array(matrix), _finite_array(singular)
    _require(singular.shape == (3,) and bool(np.all(singular >= 0)) and bool(np.all(singular[:-1] >= singular[1:])))
    scale = max(float(np.max(np.abs(matrix))), float(singular[0]))
    if scale == 0:
        _require(bool(np.all(singular == 0)))
        return
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        normalized = matrix / scale
        gram = normalized.T @ normalized
        eigenvalues = (singular / scale) ** 2
        retained = [float(np.sum(eigenvalues)),
            math.fsum(float(eigenvalues[i] * eigenvalues[j]) for i in range(3) for j in range(i + 1, 3)),
            float(np.prod(eigenvalues))]
        actual = [float(np.trace(gram)),
            math.fsum(float(gram[i, i] * gram[j, j] - gram[i, j] * gram[j, i]) for i in range(3) for j in range(i + 1, 3)),
            float(np.linalg.det(gram))]
        # The scalar tolerance is the explicitly retained singular-value
        # tolerance expressed in these dimensionless polynomial coordinates.
        scaled_tolerance = absolute / scale
        for degree, (left, right) in enumerate(zip(retained, actual), start=1):
            factor = 2 * degree * max(1.0, float(np.sum(eigenvalues))) ** (degree - 1)
            _near(left, right, absolute=factor * scaled_tolerance, relative=factor * relative)


def _validate_recorded_fit(sheet, components):
    parameters, fit = components["parameters"], components["fit"]
    numerical = parameters["numerical"]
    if parameters["mode"] == "evaluate_declared_transform_ca":
        declared = parameters["declared_transform"]
        for side in ("fixed", "moving"):
            _require(same(declared[side + "_selection"], sheet["sequences"][side]["selection"]), "invalid_transform")
        expected_transform = validate_declared_transform(declared, numerical_parameters=numerical)
        _require(same(fit, _fit_empty(None, "mode_not_applicable", state="not_applicable", transform=expected_transform)))
        return
    request = resolve_pair_selection(sheet["correspondence"], sheet["coordinate_pairs"], selection=parameters["fit_selection"])
    _require(same(request, fit["selection"]), "conflicting_identity")
    used, excluded, failed = _partition(request, parameters["missing_coordinate_policy"])
    _require(same(excluded, fit["excluded"]) and same(used, fit["used_correspondence_ids"]))
    if failed or not used:
        reason = "incomplete_fit" if failed else "empty_fit"
        expected = _fit_empty(request, reason)
        expected["excluded"] = excluded
        expected["issues"] = [issue(reason, stage="fit", field="fit_selection")]
        if request["requested_count"] == 0:
            expected["fit_rmsd"]["reason"] = "zero_denominator"
        _require(same(expected, fit))
        return
    if fit["state"] == "invalid":
        # A retained numerical failure is not rerun to try to turn it into a
        # successful native result. It may retain finite earlier diagnostics.
        _require(any(i["code"] == "numeric_inconsistency" for i in fit["issues"]))
        _require(fit["transform"]["state"] == "invalid")
        for field in ("fit_sse", "fit_residual_sse", "fit_rmsd"):
            _require(fit[field]["state"] == "invalid" and fit[field]["reason"] == "numeric_inconsistency")
        return
    by_id = {pair["correspondence_id"]: pair for pair in sheet["coordinate_pairs"]}
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        x = _finite_array([by_id[key]["fixed_xyz_A"]["value"] for key in used])
        y = _finite_array([by_id[key]["moving_xyz_A"]["value"] for key in used])
        xb, yb = x.mean(axis=0), y.mean(axis=0)
        xc, yc = x - xb, y - yb
        h = yc.T @ xc
        for field, value in (("fixed_centroid", xb), ("moving_centroid", yb), ("cross_covariance", h)):
            _recorded_cell(fit[field], value, unit=_FIT_UNITS[field], numerical=numerical)
        for field, matrix, tolerance in (("singular_values", h, "svd_absolute_tolerance_A2"),
                ("fixed_geometry_singular_values", xc, "geometry_absolute_tolerance_A"),
                ("moving_geometry_singular_values", yc, "geometry_absolute_tolerance_A")):
            cell = fit[field]
            _require(cell["state"] == "present" and cell["unit"] == _FIT_UNITS[field] and cell["origin"] == "fitted")
            _check_spectrum(matrix, cell["value"], absolute=numerical[tolerance], relative=numerical["svd_relative_tolerance"])
        singular = fit["singular_values"]["value"]
        for field, array, tolerance in (("cross_covariance_rank", singular, "svd_absolute_tolerance_A2"),
                ("fixed_geometry_rank", fit["fixed_geometry_singular_values"]["value"], "geometry_absolute_tolerance_A"),
                ("moving_geometry_rank", fit["moving_geometry_singular_values"]["value"], "geometry_absolute_tolerance_A")):
            _recorded_cell(fit[field], _rank(array, numerical[tolerance], numerical["svd_relative_tolerance"]),
                unit="count", numerical=numerical)
        det, sign = fit["uncorrected_rotation_determinant"]["value"], fit["reflection_correction_sign"]["value"]
        _require(det is not None and sign in (-1, 1) and sign == (1 if det >= 0 else -1))
        _near(abs(det), 1, absolute=numerical["rotation_determinant_tolerance"], relative=0)
        if fit["cross_covariance_rank"]["value"] == 3:
            _require(sign == (1 if np.linalg.det(h) >= 0 else -1))
        sx, sy = float(np.sum(xc * xc)), float(np.sum(yc * yc))
        raw, limit = _sse_values(sx, sy, singular, sign, numerical)
        _require(raw >= -limit)
        for field, value in (("fit_sse_raw_formula", raw), ("fit_sse_roundoff_limit", limit), ("fit_sse", max(0.0, raw))):
            _recorded_cell(fit[field], value, unit="angstrom_squared", numerical=numerical)
        _recorded_cell(fit["fit_rmsd"], math.sqrt(max(0.0, raw) / len(used)), unit="angstrom", numerical=numerical)
        tie = sign < 0 and abs(singular[1] - singular[2]) <= max(numerical["svd_absolute_tolerance_A2"], numerical["svd_relative_tolerance"] * singular[0])
        nonunique = len(used) < 3 or fit["cross_covariance_rank"]["value"] < 2 or tie
        _require((fit["state"] == "minimum_only") == nonunique)
        _require(("numerical_roundoff_clamp" in fit["qualifications"]) == (fit["fit_sse_raw_formula"]["value"] < 0))
        _require(("available_subset_used" in fit["qualifications"]) == bool(excluded))
        expected_qualifications = (["available_subset_used"] if excluded else []) + (
            ["numerical_roundoff_clamp"] if fit["fit_sse_raw_formula"]["value"] < 0 else []) + (["minimum_only"] if nonunique else [])
        _require(same(fit["qualifications"], expected_qualifications))
        if nonunique:
            _require(fit["transform"]["state"] == "nonunique_fit" and fit["fit_residual_sse"]["value"] is None
                and fit["fit_residual_sse"]["reason"] == "nonunique_fit" and "minimum_only" in fit["qualifications"])
            return
        _require(fit["state"] == "performed" and fit["transform"]["state"] == "identifiable_fit")
        _require(fit["issues"] == [] and fit["transform"]["issues"] == [] and fit["transform"]["qualifications"] == [])
        _require(fit["transform"]["rotation"]["origin"] == "fitted" and fit["transform"]["rotation"]["unit"] == "dimensionless")
        rotation, translation = fit["transform"]["rotation"]["value"], fit["transform"]["translation"]["value"]
        rotation, translation = _finite_array(rotation), _finite_array(translation)
        _near(rotation.T @ rotation, np.eye(3), absolute=numerical["rotation_orthogonality_tolerance"], relative=0)
        _near(np.linalg.det(rotation), 1, absolute=numerical["rotation_determinant_tolerance"], relative=0)
        _recorded_cell(fit["transform"]["translation"], xb - yb @ rotation, unit="angstrom", numerical=numerical)
        residual = y @ rotation + translation - x
        residual_sse = float(np.sum(residual * residual))
        _recorded_cell(fit["fit_residual_sse"], residual_sse, unit="angstrom_squared", numerical=numerical)
        _require(abs(residual_sse - fit["fit_sse"]["value"]) <= fit["fit_sse_roundoff_limit"]["value"])


def _validate_recorded_components(sheet: ProteinStructureSheet, value: ProteinStructureComponents, *, original=False):
    """Validate retained arithmetic and associations without refitting.

    No SVD or calculator is invoked. In particular, this function never returns
    replacement components. The parser returns the original validated record.
    Actual producer/receipt authority remains the host's separate responsibility.
    """
    sheet = validate_protein_structure_sheet(sheet)
    _validate_input_relationships(sheet)
    value = validate_protein_structure_components(value)
    parameters = value["parameters"]
    _require(value["input_numerical_sha256"] == _numerical_digest(sheet), "input_digest_mismatch")
    if original:
        _require(same(parameters, sheet["native_request"]), "original_commission_mismatch")
    try:
        _validate_recorded_fit(sheet, value)
        evaluation, sites, transform = value["evaluation"], value["site_measurements"], value["transform"]
        request = resolve_pair_selection(sheet["correspondence"], sheet["coordinate_pairs"], selection=parameters["evaluation_selection"])
        _require(same(request, evaluation["selection"]), "conflicting_identity")
        _require(len(sites) == len(request["rows"]), "conflicting_identity")
        expected_used, expected_excluded, failed = _partition(request, parameters["missing_coordinate_policy"],
            transform_available=transform["state"] in ("identifiable_fit", "supplied"))
        unavailable = {r["request_index_0based"]: r["reason"] for r in expected_excluded}
        pairs = {p["correspondence_id"]: p for p in sheet["coordinate_pairs"]}
        used, excluded, distances, squared = [], [], [], []
        threshold = parameters["distance_threshold_A"]
        for row, site in zip(request["rows"], sites):
            index, cid = row["request_index_0based"], row["correspondence_id"]
            for field in ("request_index_0based", "selector", "correspondence_id", "fixed_position_0based", "moving_position_0based", "qualifications"):
                _require(same(site[field], row[field]), "conflicting_identity")
            _require(site["in_evaluation"] and site["in_fit"] == (cid in value["fit"]["used_correspondence_ids"]))
            if not site["evaluated"]:
                _require(site["primary_reason"] == unavailable.get(index, "numeric_inconsistency"))
                _require(site["above_threshold"] is None and all(site[field]["value"] is None for field in
                    ("moving_transformed_xyz", "residual_xyz", "distance_squared", "distance")))
                if index not in unavailable:
                    _require(evaluation["state"] == "invalid")
                for field in ("moving_transformed_xyz", "residual_xyz", "distance_squared", "distance"):
                    expected = _cell(unit="angstrom_squared" if field == "distance_squared" else "angstrom",
                        state="invalid" if index not in unavailable else "unavailable", reason=site["primary_reason"])
                    _require(same(site[field], expected))
                excluded.append({"request_index_0based": index, "reason": site["primary_reason"]})
                continue
            _require(cid in expected_used and site["primary_reason"] is None)
            pair = pairs[cid]
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                xyz = _finite_array(pair["moving_xyz_A"]["value"]) @ _finite_array(transform["rotation"]["value"]) + _finite_array(transform["translation"]["value"])
                residual = xyz - _finite_array(pair["fixed_xyz_A"]["value"])
                d2 = float(np.sum(residual * residual))
                distance = math.sqrt(d2)
            for field, expected, unit in (("moving_transformed_xyz", xyz, "angstrom"), ("residual_xyz", residual, "angstrom"),
                    ("distance_squared", d2, "angstrom_squared"), ("distance", distance, "angstrom")):
                _recorded_cell(site[field], expected, unit=unit, numerical=parameters["numerical"], origin="derived")
            _require(site["above_threshold"] is (None if threshold is None else site["distance"]["value"] > threshold))
            used.append(cid)
            distances.append(site["distance"]["value"])
            squared.append(site["distance_squared"]["value"])
        _require(same(used, evaluation["used_correspondence_ids"]) and same(excluded, evaluation["excluded"]))
        _require(same(evaluation["distance_threshold_A"], _cell(threshold, origin="supplied", state="not_applicable", reason="not_requested")))
        if evaluation["state"] == "performed":
            _require(bool(used) and used == expected_used and not failed)
            n, sse = len(used), math.fsum(squared)
            for field, expected, unit in (("evaluation_sse", sse, "angstrom_squared"),
                    ("evaluation_rmsd", math.sqrt(sse / n), "angstrom"),
                    ("evaluation_mean_distance", math.fsum(distances) / n, "angstrom"),
                    ("evaluation_min_distance", min(distances), "angstrom"),
                    ("evaluation_max_distance", max(distances), "angstrom")):
                _recorded_cell(evaluation[field], expected, unit=unit, numerical=parameters["numerical"], origin="derived")
            if threshold is not None:
                above = sum(d > threshold for d in distances)
                _recorded_cell(evaluation["above_threshold_count"], above, unit="count", numerical=parameters["numerical"], origin="derived")
                _recorded_cell(evaluation["above_threshold_fraction"], above / n, unit="fraction", numerical=parameters["numerical"], origin="derived")
        else:
            _require(evaluation["state"] == "invalid" or not used)
            reason = ("numeric_inconsistency" if evaluation["state"] == "invalid" else "incomplete_evaluation" if failed
                else "transform_unavailable" if transform["state"] not in ("identifiable_fit", "supplied") else "empty_evaluation")
            for field in ("evaluation_sse", "evaluation_rmsd", "evaluation_mean_distance", "evaluation_min_distance", "evaluation_max_distance"):
                why = ("zero_denominator" if evaluation["state"] != "invalid" and request["requested_count"] == 0
                    and field in ("evaluation_rmsd", "evaluation_mean_distance") else reason)
                _require(same(evaluation[field], _cell(unit="angstrom_squared" if field == "evaluation_sse" else "angstrom",
                    state="invalid" if evaluation["state"] == "invalid" else "unavailable", reason=why)))
        if threshold is None:
            for field, unit in (("above_threshold_count", "count"), ("above_threshold_fraction", "fraction")):
                _require(same(evaluation[field], _cell(unit=unit, state="not_applicable", reason="not_requested")))
        counts, coverage, alignment = _summaries(sheet, parameters, value["fit"], evaluation)
        _require(same(value["counts"], counts) and same(value["coverage"], coverage) and same(value["alignment"], alignment))
        _require(same(value["coordinate_sets"], _coordinate_sets(sheet, parameters, transform)))
        _require(value["state"] == _overall(value["fit"], evaluation, value["coordinate_sets"], counts, sites))
        expected_qualifications = _qualifications(sheet["source_qualifications"] + value["fit"]["qualifications"]
            + (["available_subset_used"] if evaluation["state"] == "performed" and evaluation["excluded"] else [])
            + (["threshold_is_descriptive"] if threshold is not None else []))
        _require(same(value["qualifications"], expected_qualifications))
        _require(same(value["issues"], sheet["parse_issues"] + sheet["correspondence_issues"] + value["fit"]["issues"]
            + transform["issues"] + evaluation["issues"] + [i for c in value["coordinate_sets"] for i in c["issues"]]))
    except (FloatingPointError, OverflowError, np.linalg.LinAlgError) as error:
        raise ValueError("numeric_inconsistency") from error


def validate_recorded_protein_structure_components(sheet: ProteinStructureSheet, *,
    components: ProteinStructureComponents) -> ProteinStructureComponents:
    """Return the detached original after validation, without fitting or I/O.

    This 380/004 port admits a recorded later calculation as well as an original
    native baseline. It proves arithmetic consistency, not receipt authority.
    """
    _validate_recorded_components(sheet, components, original=False)
    return deepcopy(components)


__all__ = ["resolve_pair_selection", "fit_ca_transform", "validate_declared_transform", "calculate_protein_structure_components",
           "validate_recorded_protein_structure_components"]
