"""Pure source-response components with explicit physical-owner dependence.

The caller supplies parsed measurements and established scientific meanings.
Known canceled owners need no chosen numerical reading; source interpretation,
reading reconciliation, custody, selected execution and annotation credit belong
to their separate consumers. This module performs no IO or episode action.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import combinations

from . import literature_controlled_response_calculations as _old
from .literature_experimental_contracts import RATE_UNITS


_INPUT_VERSION = "controlled_response_owner_inputs_v2"
_VERSION = "controlled_response_owner_sheet_v2"
_ROLES = _old.PRIMITIVE_ORDER
_COEFFICIENTS = (1, -1, -1, 1)


def _obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def _schema():
    text, number = {"type": "string", "minLength": 1}, {"type": "number"}
    def enum(values):
        return {"enum": list(values)}
    def nullable(value):
        return {"anyOf": [value, {"type": "null"}]}
    def array(value, **kwargs):
        return {"type": "array", "items": value, **kwargs}
    def reference(name):
        return {"$ref": "#/$defs/" + name}
    state = enum(("known", "unknown", "conflicting"))
    arm = _obj({"value": nullable(number), "threshold": nullable(number),
        "relation": enum(("eq", "lt", "le", "gt", "ge", "interval", "none")),
        "approximate": {"type": "boolean"}, "unit": nullable(enum(RATE_UNITS)),
        "status": enum(("point", "bound", "missing", "ambiguous", "conflicting", "unsupported")),
        **{name + "_id": nullable(text) for name in _old._MEANINGS},
        "source_observation_id": nullable(text), "origin": enum(("reported", "graph_derived", "synthetic")),
        "digitization_interval": nullable(_obj({"lower": number, "upper": number})),
        "protein_arrangement": enum(_old._ARRANGEMENTS),
        "meaning_statuses": _obj({name: state for name in _old._MEANINGS})})
    target = _obj({"status": state, "canonical_id": nullable(text)})
    relationships = _obj({"condition1_target": target, "condition0_target": target,
        "condition_levels_relation": enum(("same", "different", "unknown", "conflicting")),
        "subject_construct_across_conditions": enum(("same", "different", "unknown", "conflicting")),
        **{name: enum(_old._APPLICATIONS) for name in
           ("condition1_control_application", "condition0_control_application")},
        "control_reference_reuse": enum(_old._REUSE),
        "nonintended_conditions": enum(("matched", "different", "unknown", "conflicting")),
        "intended_factor": nullable(text)})
    role_covariance = _obj({"primitive_order": {"const": list(_ROLES)},
        "physical_observation_ids": array(text, minItems=4, maxItems=4),
        "units": array(enum(RATE_UNITS), minItems=4, maxItems=4),
        "matrix": array(array(number, minItems=4, maxItems=4), minItems=4, maxItems=4)})
    owner_covariance = _obj({"physical_observation_ids": array(text, minItems=1, maxItems=4, uniqueItems=True),
        "units": array(enum(RATE_UNITS), minItems=1, maxItems=4),
        "matrix": array(array(number, minItems=1, maxItems=4), minItems=1, maxItems=4)})
    schema = _obj({"version": {"const": _INPUT_VERSION},
        "arms": _obj({name: nullable(reference("Arm")) for name in _ROLES}),
        "relationships": reference("Relationships"),
        "covariance": nullable({"oneOf": [reference("RoleCovariance"), reference("OwnerCovariance")]}),
        "variance_status": enum(("known", "estimated", "unknown")),
        "model_kind": enum(("none", "known_joint_normal_source_means"))})
    schema["$defs"] = {"Arm": arm, "Relationships": relationships,
                       "RoleCovariance": role_covariance, "OwnerCovariance": owner_covariance}
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


def controlled_response_owner_arguments_schema():
    """Return the detached closed PARSED-input type, not a model tool schema."""
    return deepcopy(_schema())


def _context_reasons(left, right):
    """Scientific disagreement, independently of unused numerical readings."""
    reasons = set()
    for meaning in _old._MEANINGS[:-1]:
        a, b = left[meaning + "_id"], right[meaning + "_id"]
        if a is not None and b is not None and a != b:
            reasons.add("conflicting_owner_context")
    if left["protein_arrangement"] != right["protein_arrangement"]:
        reasons.add("conflicting_protein_arrangement")
    if left["unit"] and right["unit"] and RATE_UNITS[left["unit"]][0] != RATE_UNITS[right["unit"]][0]:
        reasons.add("incompatible_unit_dimension")
    return reasons


def _validate_covariance(inputs):
    raw, status = inputs["covariance"], inputs["variance_status"]
    if (raw is None) != (status == "unknown"):
        _old._fail("covariance_status_mismatch", "variance_status")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        _old._fail("closed_fields_required", "covariance")
    role_form = "primitive_order" in raw
    fields = ("physical_observation_ids", "units", "matrix")
    _old._closed(raw, (("primitive_order",) + fields) if role_form else fields, "covariance")
    owners, units, matrix = (raw[name] for name in fields)
    if not isinstance(owners, list) or not 1 <= len(owners) <= 4:
        _old._fail("covariance_owner_roster_required", "covariance.physical_observation_ids")
    size = len(owners)
    if role_form and (raw["primitive_order"] != list(_ROLES) or size != 4):
        _old._fail("covariance_order_mismatch", "covariance.primitive_order")
    if not isinstance(units, list) or len(units) != size:
        _old._fail("covariance_unit_roster_mismatch", "covariance.units")
    arms = [inputs["arms"][role] for role in _ROLES]
    for i, owner in enumerate(owners):
        _old._identity(owner, "covariance.physical_observation_ids", nullable=False)
        _old._enum(units[i], tuple(RATE_UNITS), "covariance.units")
        matches = [arm for arm in arms if arm is not None and arm["physical_observation_id"] == owner]
        if not matches or role_form and (arms[i] is None or arms[i]["physical_observation_id"] != owner):
            _old._fail("covariance_owner_mismatch", "covariance.physical_observation_ids")
        if any(arm["unit"] is not None and RATE_UNITS[arm["unit"]][0] != RATE_UNITS[units[i]][0] for arm in matches):
            _old._fail("covariance_unit_mismatch", "covariance.units")
    if not role_form and len(set(owners)) != size:
        _old._fail("unique_covariance_owners_required", "covariance.physical_observation_ids")
    if not isinstance(matrix, list) or len(matrix) != size or any(
            not isinstance(row, list) or len(row) != size for row in matrix):
        _old._fail("square_covariance_required", "covariance.matrix")
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            _old._finite(value, f"covariance.matrix[{i}][{j}]")
    exact = [[_old._q(value) for value in row] for row in matrix]
    if any(exact[i][j] != exact[j][i] for i in range(size) for j in range(size)):
        _old._fail("symmetric_covariance_required", "covariance.matrix")
    for order in range(1, size + 1):
        for indices in combinations(range(size), order):
            if _old._determinant([[exact[i][j] for j in indices] for i in indices]) < 0:
                _old._fail("positive_semidefinite_covariance_required", "covariance.matrix")
    scales = [_old._scale(unit) for unit in units]
    normalized = [[exact[i][j] * scales[i] * scales[j] for j in range(size)] for i in range(size)]
    for i in range(size):
        for j in range(i):
            if owners[i] == owners[j]:
                if RATE_UNITS[units[i]][0] != RATE_UNITS[units[j]][0]:
                    _old._fail("covariance_unit_mismatch", "covariance.units")
                if role_form and _context_reasons(arms[i], arms[j]):
                    _old._fail("shared_measurement_context_mismatch", "covariance.physical_observation_ids")
                if normalized[i] != normalized[j]:
                    _old._fail("shared_measurement_covariance_mismatch", "covariance.matrix")
    unique = list(dict.fromkeys(owners))
    positions = [owners.index(owner) for owner in unique]
    return {"owners": unique, "units": list(units),
            "matrix": [[normalized[i][j] for j in positions] for i in positions]}


def _validate(inputs):
    _old._closed(inputs, ("version", "arms", "relationships", "covariance", "variance_status", "model_kind"), "inputs")
    if inputs["version"] != _INPUT_VERSION:
        _old._fail("unsupported_input_version", "version")
    _old._enum(inputs["variance_status"], ("known", "estimated", "unknown"), "variance_status")
    # Reuse unchanged arm/relationship STRUCTURAL validation only. No number is
    # replaced and no sheet/populator is invoked. The new covariance is checked
    # separately in full rather than passed through006's strict reading aliases.
    _old._validate({**inputs, "version": _old.INPUT_VERSION,
                    "covariance": None, "variance_status": "unknown"})
    return _validate_covariance(inputs)


def validate_controlled_response_owner_inputs(inputs):
    """Validate finite parsed data/full supplied covariance; return a copy."""
    _validate(inputs)
    return deepcopy(inputs)


def _groups(arms):
    groups, keys = [], {}
    for index, arm in enumerate(arms):
        known = arm is not None and arm["physical_observation_id"] is not None
        owner = arm["physical_observation_id"] if known else None
        key = ("owner", owner) if known else ("role", index)
        if key not in keys:
            keys[key] = len(groups)
            groups.append({"physical_observation_id": owner, "roles": [], "coefficient": 0, "known_owner": known})
        group = groups[keys[key]]
        group["roles"].append(_ROLES[index])
        group["coefficient"] += _COEFFICIENTS[index]
    return groups


def _scientific_pair_reasons(inputs, indices, label):
    arms = [inputs["arms"][_ROLES[i]] for i in indices]
    reasons = {"missing_arm"} if any(arm is None for arm in arms) else set()
    for meaning in ("endpoint", "normalization"):
        reasons |= _old._identity_reasons(arms, meaning)
    for arm, allowed in zip(arms, (("protein_present",), ("protein_free_control", "empty_vector_control"))):
        if arm is not None and arm["protein_arrangement"] not in allowed:
            reasons.add({"unknown": "unknown_protein_arrangement", "conflicting": "conflicting_protein_arrangement"}.get(
                arm["protein_arrangement"], "incompatible_control_arrangement"))
    target = inputs["relationships"][label + "_target"]
    application = inputs["relationships"][label + "_control_application"]
    if target["status"] != "known":
        reasons.add(target["status"] + "_condition_correspondence")
    for i, arm in enumerate(arms):
        if arm is None:
            continue
        state = arm["meaning_statuses"]["condition"]
        if state != "known":
            reasons.add(state + "_condition_correspondence")
        elif target["status"] == "known" and (i == 0 or application == "matched_condition_control") and arm["condition_id"] != target["canonical_id"]:
            reasons.add("different_condition_correspondence")
    if application in ("unknown", "conflicting"):
        reasons.add(application + "_control_application")
    return reasons


def _scientific_reasons(inputs, arms, covariance):
    reasons = _scientific_pair_reasons(inputs, (0, 1), "condition1")
    reasons |= _scientific_pair_reasons(inputs, (2, 3), "condition0")
    relationships = inputs["relationships"]
    for meaning in ("endpoint", "normalization"):
        reasons |= _old._identity_reasons(arms, meaning)
    reasons |= _old._identity_reasons([arms[0], arms[2]], "subject_construct")
    subject = relationships["subject_construct_across_conditions"]
    if subject != "same":
        reasons.add(subject + "_subject_correspondence")
    levels = relationships["condition_levels_relation"]
    if levels in ("unknown", "conflicting"):
        reasons.add(levels + "_condition_correspondence")
    if levels == "same" or (relationships["condition1_target"]["canonical_id"] is not None and
            relationships["condition1_target"]["canonical_id"] == relationships["condition0_target"]["canonical_id"]):
        reasons.add("condition_levels_not_distinct")
    if relationships["intended_factor"] is None:
        reasons.add("missing_intended_factor")
    reuse, left, right = relationships["control_reference_reuse"], arms[1], arms[3]
    if reuse == "conflicting":
        reasons.add("conflicting_control_reuse")
    elif reuse in ("distinct_observations", "same_reference_with_stated_invariance"):
        if left is None or right is None or left["physical_observation_id"] is None or right["physical_observation_id"] is None:
            reasons.add("conflicting_control_reuse")
        elif (left["physical_observation_id"] == right["physical_observation_id"]) != (reuse == "same_reference_with_stated_invariance"):
            reasons.add("conflicting_control_reuse")
    units = [arm["unit"] for arm in arms if arm and arm["unit"]]
    units += covariance["units"] if covariance else []
    if len({RATE_UNITS[unit][0] for unit in units}) > 1:
        reasons.add("incompatible_unit_dimension")
    for i, arm in enumerate(arms):
        if arm is None:
            continue
        if arm["meaning_statuses"]["physical_observation"] == "conflicting":
            reasons.add("conflicting_owner_context")
        for other in arms[:i]:
            if other is None:
                continue
            a, b = arm["physical_observation_id"], other["physical_observation_id"]
            if a is not None and a == b:
                reasons |= _context_reasons(arm, other)
            if (arm["source_observation_id"] is not None and arm["source_observation_id"] == other["source_observation_id"]
                    and a is not None and b is not None and a != b):
                reasons.add("conflicting_source_owner_binding")
    return reasons


def _reading_signature(arm):
    if arm["unit"] is None:
        return None
    scale = _old._scale(arm["unit"])
    interval = arm["digitization_interval"]
    return (arm["status"], arm["relation"], arm["approximate"],
        RATE_UNITS[arm["unit"]][0],
        _old._q(arm["value"]) * scale if arm["value"] is not None else None,
        _old._q(arm["threshold"]) * scale if arm["threshold"] is not None else None,
        tuple(_old._q(interval[side]) * scale for side in ("lower", "upper")) if interval else None)


def _disjoint(left, right):
    a, b = _old._range(left), _old._range(right)
    for x, y in ((a, b), (b, a)):
        if x.upper is not None and y.lower is not None and (x.upper < y.lower or
                x.upper == y.lower and not (x.upper_closed and y.lower_closed)):
            return True
    return False


def _reading_dependencies(inputs, groups):
    active_reasons, canceled_qualifications, conflict_roles = set(), set(), set()
    active_roles, canceled_roles = [], []
    for group in groups:
        canceled = group["known_owner"] and group["coefficient"] == 0
        rows = [(role, inputs["arms"][role]) for role in group["roles"]]
        if canceled:
            canceled_roles.extend(group["roles"])
            canceled_qualifications.add("owner_cancellation")
            for role, arm in rows:
                if arm["unit"] is None:
                    canceled_qualifications.add("canceled_unit_unknown")
                if arm["status"] not in ("point", "bound"):
                    canceled_qualifications.add("canceled_reading_unavailable")
                if arm["origin"] == "graph_derived":
                    canceled_qualifications.add("canceled_graph_reading")
                if arm["status"] == "conflicting":
                    canceled_qualifications.add("canceled_source_reading_conflict")
                    conflict_roles.add(role)
        else:
            active_roles.extend(group["roles"])
            for role, arm in rows:
                active_reasons |= _old._operand_reasons(arm)
                if arm and arm["status"] == "conflicting":
                    conflict_roles.add(role)
        for i, (role, arm) in enumerate(rows):
            for other_role, other in rows[:i]:
                if arm is None or other is None:
                    continue
                signatures = _reading_signature(arm), _reading_signature(other)
                different = signatures[0] != signatures[1]
                if canceled and different:
                    canceled_qualifications.add("canceled_representation_difference")
                usable = all(row["unit"] is not None and row["status"] in ("point", "bound") for row in (arm, other))
                if usable and RATE_UNITS[arm["unit"]][0] == RATE_UNITS[other["unit"]][0] and _disjoint(arm, other):
                    conflict_roles.update((role, other_role))
                    if canceled:
                        canceled_qualifications.add("canceled_reading_domain_conflict")
                        if arm["relation"] == other["relation"] == "eq":
                            canceled_qualifications.add("canceled_source_reading_conflict")
                    else:
                        active_reasons.add("conflicting_source_literal")
                elif not canceled and usable and different:
                    active_reasons.add("unresolved_active_reading_model")
    return (active_reasons, canceled_qualifications, conflict_roles,
            [role for role in _ROLES if role in active_roles],
            [role for role in _ROLES if role in canceled_roles])


def _raw_local_cells(inputs, arms):
    cells = {}
    for i, arm in enumerate(arms):
        reasons = _old._operand_reasons(arm)
        cells[_old.COMPONENTS[i]] = _old._cell(_old._range(arm) if not reasons else None,
            _old._unit([arm]), _old._FORMULAS[i], [arm], reasons=reasons,
            qualifications=_old._qualifications(inputs, [arm]), raw=True)
    for index, (indices, label) in enumerate((((0, 1), "condition1"), ((2, 3), "condition0"))):
        selected = [arms[i] for i in indices]
        reasons = _old._pair_reasons(inputs, indices, label)
        qualifications = _old._qualifications(inputs, selected)
        if inputs["relationships"][label + "_control_application"] == "shared_reference_assumption":
            qualifications.add("shared_reference_assumption")
        cells[_old.COMPONENTS[4 + index]] = _old._cell(_old._linear(selected, (1, -1)) if not reasons else None,
            _old._unit(selected), _old._FORMULAS[4 + index], selected,
            reasons=reasons, qualifications=qualifications)
    return cells


def populate_controlled_response_owner(inputs):
    """Populate raw/local cells and the contrast's actual owner dependencies."""
    covariance = _validate(inputs)
    arms = [inputs["arms"][role] for role in _ROLES]
    groups = _groups(arms)
    scientific = _scientific_reasons(inputs, arms, covariance)
    numeric, canceled_qualifications, conflicts, active_roles, canceled_roles = _reading_dependencies(inputs, groups)
    active = [inputs["arms"][role] for role in active_roles]
    active_groups = [group for group in groups if not (group["known_owner"] and group["coefficient"] == 0)]
    required = list(dict.fromkeys(group["physical_observation_id"] for group in active_groups if group["known_owner"]))
    provided = covariance["owners"] if covariance else []
    incomplete = any(not group["known_owner"] for group in active_groups) or not set(required) <= set(provided)
    covariance_state = ("scientific_blocked" if scientific else "unavailable" if covariance is None else
                        "incomplete_active_coverage" if incomplete else "available")
    reasons = scientific | numeric
    effect = None
    if not reasons:
        representatives = [inputs["arms"][group["roles"][0]] for group in active_groups]
        effect = _old._linear(representatives, [group["coefficient"] for group in active_groups])
    unit = _old._unit(active)
    qualifications = _old._qualifications(inputs, active, cross=True) | canceled_qualifications
    if any(inputs["relationships"][label + "_control_application"] == "shared_reference_assumption"
           for label in ("condition1", "condition0")):
        qualifications.add("shared_reference_assumption")
    cells = _raw_local_cells(inputs, arms)
    cells[_old.COMPONENTS[6]] = _old._cell(effect, unit, _old._FORMULAS[6], active,
        reasons=reasons, qualifications=qualifications)
    variance_reasons = set(reasons)
    if effect is not None and effect.point is None:
        variance_reasons.add("unresolved_censoring_model")
    if covariance is None:
        variance_reasons.add("unknown_covariance")
    elif incomplete:
        variance_reasons.add("incomplete_active_covariance")
    variance = None
    if not variance_reasons:
        positions = [provided.index(group["physical_observation_id"]) for group in active_groups]
        variance = sum(group_i["coefficient"] * group_j["coefficient"] * covariance["matrix"][positions[i]][positions[j]]
            for i, group_i in enumerate(active_groups) for j, group_j in enumerate(active_groups))
    variance_qualifications = qualifications | _old._qualifications(inputs, active, covariance=True)
    variance_unit = "(" + unit + ")^2" if unit is not None else None
    cells[_old.COMPONENTS[7]] = _old._cell(_old._point(variance), variance_unit, _old._FORMULAS[7], active,
        reasons=variance_reasons, qualifications=variance_qualifications)
    cells[_old.COMPONENTS[8]] = _old._cell(_old._point(_old._sqrt(variance)) if variance is not None else None,
        unit, _old._FORMULAS[8], active, reasons=variance_reasons, qualifications=variance_qualifications)
    positive_reasons = variance_reasons | ({"nonpositive_variance_for_model"} if variance is not None and variance <= 0 else set())
    cells[_old.COMPONENTS[9]] = _old._cell(_old._point(1 / variance) if variance is not None and variance > 0 else None,
        "(" + unit + ")^-2" if unit is not None else None, _old._FORMULAS[9], active,
        reasons=positive_reasons, qualifications=variance_qualifications)
    model_reasons = set(positive_reasons)
    if inputs["variance_status"] == "estimated":
        model_reasons.add("estimated_covariance")
    if inputs["model_kind"] == "none":
        model_reasons.add("observation_model_unselected")
    if any(arm and arm["status"] == "bound" for arm in active):
        model_reasons.add("unresolved_censoring_model")
    if any(arm and (arm["origin"] == "graph_derived" or arm["approximate"] or arm["digitization_interval"] is not None) for arm in active):
        model_reasons.add("unresolved_reading_model")
    score = effect.point * abs(effect.point) / (2 * variance) if not model_reasons else None
    model_qualifications = variance_qualifications | _old._qualifications(inputs, active, model=True)
    cells[_old.COMPONENTS[10]] = _old._cell(_old._point(score), "dimensionless", _old._FORMULAS[10], active,
        reasons=model_reasons, qualifications=model_qualifications)
    index = _old._bounded_index(score) if score is not None else None
    cells[_old.COMPONENTS[11]] = _old._cell(_old._point(index), "dimensionless", _old._FORMULAS[11], active,
        reasons=model_reasons | ({"numeric_range_failure"} if score is not None and index is None else set()),
        qualifications=model_qualifications)
    dependencies = {"coefficient_order": list(_ROLES), "role_coefficients": list(_COEFFICIENTS),
        "groups": groups, "active_roles": active_roles, "canceled_roles": canceled_roles,
        "scientific_reasons": sorted(scientific), "active_reading_reasons": sorted(numeric),
        "canceled_reading_qualifications": sorted(canceled_qualifications),
        "reading_conflict_roles": [role for role in _ROLES if role in conflicts],
        "required_covariance_owner_ids": required, "provided_covariance_owner_ids": list(provided),
        "covariance_state": covariance_state, "model_active_roles": list(active_roles)}
    return {"version": _VERSION, "primitive_order": list(_ROLES), "inputs": deepcopy(inputs),
            "cells": cells, "contrast_dependencies": dependencies}


__all__ = ["controlled_response_owner_arguments_schema", "validate_controlled_response_owner_inputs",
           "populate_controlled_response_owner"]
