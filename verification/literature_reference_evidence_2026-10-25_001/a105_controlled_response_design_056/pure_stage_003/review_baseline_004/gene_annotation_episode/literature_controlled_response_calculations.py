"""Pure four-arm source-response arithmetic within A105.

This accepts already parsed, explicitly interpreted inputs, never model-selected
scientific numbers or source documents. Source custody, condition/normalization
interpretation, reader partials, selected execution and annotation credit belong
elsewhere. The controlled effect is conditional on actual control applicability;
it does not establish isolated causal protein action or proton coupling.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import combinations, permutations
import math

from .literature_experimental_contracts import ExperimentalContractError, RATE_UNITS


INPUT_VERSION = "controlled_response_inputs_v1"
VERSION = "controlled_response_sheet_v1"
PRIMITIVE_ORDER = ("protein_condition1", "empty_condition1",
                   "protein_condition0", "empty_condition0")
COMPONENTS = tuple(name + "_response" for name in PRIMITIVE_ORDER) + (
    "condition1_controlled_response", "condition0_controlled_response",
    "controlled_response_difference", "contrast_variance",
    "contrast_standard_uncertainty", "contrast_precision",
    "source_profile_log_ratio", "source_signed_index")
CELL_FIELDS = ("value", "lower", "upper", "relation", "approximate", "unit",
               "status", "origin", "unavailable_reason", "formula_code",
               "conditional_on", "bound_kind", "bound_state")
ARM_FIELDS = ("value", "threshold", "relation", "approximate", "unit", "status",
              "endpoint_id", "normalization_id", "subject_construct_id",
              "condition_id", "physical_observation_id", "source_observation_id",
              "origin", "digitization_interval", "protein_arrangement",
              "meaning_statuses")
RELATIONSHIP_FIELDS = ("condition1_target", "condition0_target",
    "condition_levels_relation", "condition1_control_application",
    "condition0_control_application", "subject_construct_across_conditions",
    "control_reference_reuse", "nonintended_conditions", "intended_factor")
_MEANINGS = ("endpoint", "normalization", "subject_construct", "condition",
             "physical_observation")
_STATES = ("known", "unknown", "conflicting")
_ARRANGEMENTS = ("protein_present", "protein_free_control", "empty_vector_control",
                 "other_specified", "unknown", "conflicting")
_APPLICATIONS = ("matched_condition_control", "shared_reference_assumption",
                 "unknown", "conflicting")
_REUSE = ("distinct_observations", "same_reference_with_stated_invariance",
          "unknown", "conflicting")
_BASE_UNITS = {"amount_rate": "umol/min", "concentration_rate": "uM/min",
               "turnover_rate": "per_min", "specific_amount_rate": "umol/min/mg"}
_FORMULAS = ("source_response",) * 4 + ("condition_control_difference",) * 2 + (
    "four_arm_condition_difference", "linear_joint_covariance",
    "square_root_variance", "inverse_variance", "signed_known_normal_profile",
    "tanh_half_signed_profile")
REASONS = (
    "missing_arm", "unknown_unit", "incompatible_unit_dimension",
    "unknown_endpoint", "different_endpoint", "conflicting_endpoint",
    "unknown_normalization", "different_normalization", "conflicting_normalization",
    "unknown_subject_correspondence", "different_subject_correspondence",
    "conflicting_subject_correspondence", "unknown_control_application",
    "conflicting_control_application", "unknown_protein_arrangement",
    "conflicting_protein_arrangement", "incompatible_control_arrangement",
    "unknown_condition_correspondence", "different_condition_correspondence",
    "conflicting_condition_correspondence", "condition_levels_not_distinct",
    "missing_intended_factor", "conflicting_control_reuse",
    "unsupported_source_expression", "ambiguous_source_literal",
    "conflicting_source_literal", "unavailable_source_dependency",
    "unknown_covariance", "estimated_covariance", "nonpositive_variance_for_model",
    "observation_model_unselected", "unresolved_censoring_model",
    "unresolved_reading_model", "numeric_range_failure", "uninformative_bounds")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _closed(value, fields, field):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail("closed_fields_required", field)


def _enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail("unsupported_value", field)


def _identity(value, field, *, nullable=True):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_identity_required", field)


def _finite(value, field, *, nullable=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def _q(value):
    # The pure interface is finite JSON numbers. Interpret their stable decimal
    # spelling exactly, not successive floating products/subtractions.
    return Fraction(str(value))


def _scale(unit):
    return _q(RATE_UNITS[unit][1])


def _validate_arm(arm, field):
    if arm is None:
        return
    _closed(arm, ARM_FIELDS, field)
    _enum(arm["status"], ("point", "bound", "missing", "ambiguous", "conflicting",
                           "unsupported"), field + ".status")
    _enum(arm["relation"], ("eq", "lt", "le", "gt", "ge", "interval", "none"),
          field + ".relation")
    _enum(arm["origin"], ("reported", "graph_derived", "synthetic"), field + ".origin")
    _enum(arm["protein_arrangement"], _ARRANGEMENTS, field + ".protein_arrangement")
    if type(arm["approximate"]) is not bool:
        _fail("boolean_required", field + ".approximate")
    if arm["unit"] is not None:
        _enum(arm["unit"], tuple(RATE_UNITS), field + ".unit")
    _finite(arm["value"], field + ".value", nullable=True)
    _finite(arm["threshold"], field + ".threshold", nullable=True)
    status, relation = arm["status"], arm["relation"]
    if status == "point":
        if arm["value"] is None or arm["threshold"] is not None or relation not in ("eq", "interval"):
            _fail("point_contract_mismatch", field)
    elif status == "bound":
        if arm["value"] is not None or arm["threshold"] is None or relation not in ("lt", "le", "gt", "ge"):
            _fail("bound_contract_mismatch", field)
    elif arm["value"] is not None or arm["threshold"] is not None or relation != "none":
        _fail("unavailable_measurement_must_be_null", field)
    interval = arm["digitization_interval"]
    if interval is not None:
        _closed(interval, ("lower", "upper"), field + ".digitization_interval")
        for side in ("lower", "upper"):
            _finite(interval[side], field + ".digitization_interval." + side)
        if (status != "point" or relation != "interval" or arm["origin"] != "graph_derived"
                or not interval["lower"] <= arm["value"] <= interval["upper"]):
            _fail("digitization_interval_mismatch", field)
    elif relation == "interval":
        _fail("digitization_interval_required", field)
    _closed(arm["meaning_statuses"], _MEANINGS, field + ".meaning_statuses")
    for meaning in _MEANINGS:
        state = arm["meaning_statuses"][meaning]
        _enum(state, _STATES, field + ".meaning_statuses." + meaning)
        identity = arm[meaning + "_id"]
        _identity(identity, field + "." + meaning + "_id")
        if (state == "known") != (identity is not None):
            _fail("meaning_identity_mismatch", field + "." + meaning + "_id")
    _identity(arm["source_observation_id"], field + ".source_observation_id",
              nullable=status == "missing")
    if status == "missing" and arm["source_observation_id"] is not None:
        _fail("missing_source_identity_must_be_null", field)


def _determinant(matrix):
    size = len(matrix)
    total = Fraction(0)
    for perm in permutations(range(size)):
        inversions = sum(perm[i] > perm[j] for i in range(size) for j in range(i + 1, size))
        product = Fraction((-1) ** inversions)
        for i in range(size):
            product *= matrix[i][perm[i]]
        total += product
    return total


def _validate_covariance(inputs):
    raw, status = inputs["covariance"], inputs["variance_status"]
    if (raw is None) != (status == "unknown"):
        _fail("covariance_status_mismatch", "variance_status")
    if raw is None:
        return None
    _closed(raw, ("primitive_order", "physical_observation_ids", "units", "matrix"), "covariance")
    if raw["primitive_order"] != list(PRIMITIVE_ORDER):
        _fail("covariance_order_mismatch", "covariance.primitive_order")
    for field in ("physical_observation_ids", "units"):
        if not isinstance(raw[field], list) or len(raw[field]) != 4:
            _fail("four_operands_required", "covariance." + field)
    for i, name in enumerate(PRIMITIVE_ORDER):
        arm = inputs["arms"][name]
        owner = raw["physical_observation_ids"][i]
        _identity(owner, "covariance.physical_observation_ids", nullable=False)
        _enum(raw["units"][i], tuple(RATE_UNITS), "covariance.units")
        if arm is None or owner != arm["physical_observation_id"]:
            _fail("covariance_owner_mismatch", "covariance.physical_observation_ids")
        if arm["unit"] is None or RATE_UNITS[raw["units"][i]][0] != RATE_UNITS[arm["unit"]][0]:
            _fail("covariance_unit_mismatch", "covariance.units")
    matrix = raw["matrix"]
    if not isinstance(matrix, list) or len(matrix) != 4 or any(
            not isinstance(row, list) or len(row) != 4 for row in matrix):
        _fail("four_by_four_covariance_required", "covariance.matrix")
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            _finite(value, f"covariance.matrix[{i}][{j}]")
    matrix = [[_q(value) for value in row] for row in matrix]
    if any(matrix[i][j] != matrix[j][i] for i in range(4) for j in range(4)):
        _fail("symmetric_covariance_required", "covariance.matrix")
    for size in range(1, 5):
        for indices in combinations(range(4), size):
            if _determinant([[matrix[i][j] for j in indices] for i in indices]) < 0:
                _fail("positive_semidefinite_covariance_required", "covariance.matrix")
    scales = [_scale(unit) for unit in raw["units"]]
    matrix = [[matrix[i][j] * scales[i] * scales[j] for j in range(4)] for i in range(4)]
    for i, name in enumerate(PRIMITIVE_ORDER):
        for j in range(i):
            if raw["physical_observation_ids"][i] != raw["physical_observation_ids"][j]:
                continue
            if _alias_reasons(inputs["arms"][name], inputs["arms"][PRIMITIVE_ORDER[j]]):
                _fail("shared_measurement_context_mismatch", "covariance.physical_observation_ids")
            if matrix[i] != matrix[j] or any(matrix[k][i] != matrix[k][j] for k in range(4)):
                _fail("shared_measurement_covariance_mismatch", "covariance.matrix")
    return matrix


def _validate(inputs):
    _closed(inputs, ("version", "arms", "relationships", "covariance", "variance_status", "model_kind"), "inputs")
    if inputs["version"] != INPUT_VERSION:
        _fail("unsupported_input_version", "version")
    _closed(inputs["arms"], PRIMITIVE_ORDER, "arms")
    for name, arm in inputs["arms"].items():
        _validate_arm(arm, "arms." + name)
    relationships = inputs["relationships"]
    _closed(relationships, RELATIONSHIP_FIELDS, "relationships")
    for name in ("condition1_target", "condition0_target"):
        target = relationships[name]
        _closed(target, ("status", "canonical_id"), "relationships." + name)
        _enum(target["status"], _STATES, "relationships." + name + ".status")
        _identity(target["canonical_id"], "relationships." + name + ".canonical_id")
        if (target["status"] == "known") != (target["canonical_id"] is not None):
            _fail("meaning_identity_mismatch", "relationships." + name)
    for name in ("condition_levels_relation", "subject_construct_across_conditions"):
        _enum(relationships[name], ("same", "different", "unknown", "conflicting"), "relationships." + name)
    for name in ("condition1_control_application", "condition0_control_application"):
        _enum(relationships[name], _APPLICATIONS, "relationships." + name)
    _enum(relationships["control_reference_reuse"], _REUSE, "relationships.control_reference_reuse")
    _enum(relationships["nonintended_conditions"], ("matched", "different", "unknown", "conflicting"),
          "relationships.nonintended_conditions")
    _identity(relationships["intended_factor"], "relationships.intended_factor")
    _enum(inputs["variance_status"], ("known", "estimated", "unknown"), "variance_status")
    _enum(inputs["model_kind"], ("none", "known_joint_normal_source_means"), "model_kind")
    return _validate_covariance(inputs)


def validate_controlled_response_inputs(inputs):
    """Validate the closed parsed-input contract and return a detached copy.

    Invalid direct covariance is an actionable contract error. A future source
    reader must retain authentic bad covariance as a source partial before
    calling this function with covariance explicitly unavailable.
    """
    _validate(inputs)
    return deepcopy(inputs)


def _operand_reasons(arm):
    if arm is None:
        return {"missing_arm"}
    reasons = set()
    if arm["unit"] is None:
        reasons.add("unknown_unit")
    status_reason = {"missing": "missing_arm", "ambiguous": "ambiguous_source_literal",
        "conflicting": "conflicting_source_literal", "unsupported": "unsupported_source_expression"}
    if arm["status"] in status_reason:
        reasons.add(status_reason[arm["status"]])
    return reasons


def _identity_reasons(arms, meaning):
    states = [arm["meaning_statuses"][meaning] for arm in arms if arm is not None]
    if "conflicting" in states:
        return {"conflicting_" + meaning if meaning in ("endpoint", "normalization") else
                "conflicting_" + ("subject_correspondence" if meaning == "subject_construct" else "condition_correspondence")}
    if len(states) != len(arms) or "unknown" in states:
        return {"unknown_" + meaning if meaning in ("endpoint", "normalization") else
                "unknown_" + ("subject_correspondence" if meaning == "subject_construct" else "condition_correspondence")}
    if len({arm[meaning + "_id"] for arm in arms}) != 1:
        return {"different_" + meaning if meaning in ("endpoint", "normalization") else
                "different_" + ("subject_correspondence" if meaning == "subject_construct" else "condition_correspondence")}
    return set()


def _alias_reasons(left, right):
    """Test consistency of an asserted common physical/source observation."""
    reasons = set()
    for meaning in _MEANINGS[:-1]:
        a, b = left[meaning + "_id"], right[meaning + "_id"]
        if a is not None and b is not None and a != b:
            reasons |= {"conflicting_" + meaning if meaning in ("endpoint", "normalization") else
                "conflicting_" + ("subject_correspondence" if meaning == "subject_construct" else "condition_correspondence")}
    if left["protein_arrangement"] != right["protein_arrangement"]:
        reasons.add("conflicting_protein_arrangement")
    if left["unit"] is None or right["unit"] is None:
        return reasons | {"unknown_unit"}
    if RATE_UNITS[left["unit"]][0] != RATE_UNITS[right["unit"]][0]:
        return reasons | {"incompatible_unit_dimension"}
    for field in ("status", "relation", "approximate"):
        if left[field] != right[field]:
            reasons.add("conflicting_source_literal")
    for field in ("value", "threshold"):
        a, b = left[field], right[field]
        if ((a is None) != (b is None) or a is not None and
                _q(a) * _scale(left["unit"]) != _q(b) * _scale(right["unit"])):
            reasons.add("conflicting_source_literal")
    a, b = left["digitization_interval"], right["digitization_interval"]
    if (a is None) != (b is None) or a is not None and any(
            _q(a[side]) * _scale(left["unit"]) != _q(b[side]) * _scale(right["unit"])
            for side in ("lower", "upper")):
        reasons.add("conflicting_source_literal")
    return reasons


def _common_alias_reasons(arms):
    reasons = set()
    for i, left in enumerate(arms):
        if left is None:
            continue
        for right in arms[:i]:
            if right is None:
                continue
            same_owner = left["physical_observation_id"] is not None and left["physical_observation_id"] == right["physical_observation_id"]
            same_source = left["source_observation_id"] is not None and left["source_observation_id"] == right["source_observation_id"]
            if same_owner or same_source:
                reasons |= _alias_reasons(left, right)
                if same_source and left["physical_observation_id"] is not None and right["physical_observation_id"] is not None and not same_owner:
                    reasons.add("conflicting_source_literal")
    return reasons


def _unit(arms):
    units = [arm["unit"] for arm in arms if arm is not None and arm["unit"] is not None]
    dimensions = {RATE_UNITS[unit][0] for unit in units}
    return _BASE_UNITS[next(iter(dimensions))] if len(dimensions) == 1 else None


def _pair_reasons(inputs, indices, label):
    arms = [inputs["arms"][PRIMITIVE_ORDER[i]] for i in indices]
    reasons = set().union(*(_operand_reasons(arm) for arm in arms))
    for meaning in ("endpoint", "normalization"):
        reasons |= _identity_reasons(arms, meaning)
    if len({RATE_UNITS[arm["unit"]][0] for arm in arms if arm and arm["unit"]}) > 1:
        reasons.add("incompatible_unit_dimension")
    for arm, allowed in zip(arms, (("protein_present",), ("protein_free_control", "empty_vector_control"))):
        if arm is None:
            continue
        arrangement = arm["protein_arrangement"]
        if arrangement not in allowed:
            reasons.add({"unknown": "unknown_protein_arrangement", "conflicting": "conflicting_protein_arrangement"}.get(
                arrangement, "incompatible_control_arrangement"))
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
    reasons |= _common_alias_reasons(arms)
    return reasons


def _effect_reasons(inputs, pair_reasons):
    arms = [inputs["arms"][name] for name in PRIMITIVE_ORDER]
    relationships = inputs["relationships"]
    reasons = set().union(*pair_reasons)
    for meaning in ("endpoint", "normalization"):
        reasons |= _identity_reasons(arms, meaning)
    reasons |= _identity_reasons([arms[0], arms[2]], "subject_construct")
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
    reuse = relationships["control_reference_reuse"]
    left, right = arms[1], arms[3]
    if reuse == "conflicting":
        reasons.add("conflicting_control_reuse")
    elif reuse in ("same_reference_with_stated_invariance", "distinct_observations"):
        if left is None or right is None or left["physical_observation_id"] is None or right["physical_observation_id"] is None:
            reasons.add("conflicting_control_reuse")
        else:
            same = left["physical_observation_id"] == right["physical_observation_id"]
            if same != (reuse == "same_reference_with_stated_invariance"):
                reasons.add("conflicting_control_reuse")
    reasons |= _common_alias_reasons(arms)
    return reasons


@dataclass(frozen=True)
class _Range:
    point: Fraction | None
    lower: Fraction | None
    upper: Fraction | None
    lower_closed: bool = True
    upper_closed: bool = True
    kinds: frozenset = frozenset()


def _range(arm):
    scale = _scale(arm["unit"])
    if arm["status"] == "point":
        point = _q(arm["value"]) * scale
        interval = arm["digitization_interval"]
        return (_Range(point, _q(interval["lower"]) * scale, _q(interval["upper"]) * scale,
                       kinds=frozenset(("conditional_digitization",))) if interval else
                _Range(point, point, point))
    threshold = _q(arm["threshold"]) * scale
    return (_Range(None, None, threshold, upper_closed=arm["relation"] == "le",
                   kinds=frozenset(("reported_limit",))) if arm["relation"] in ("lt", "le") else
            _Range(None, threshold, None, lower_closed=arm["relation"] == "ge",
                   kinds=frozenset(("reported_limit",))))


def _linear(arms, coefficients):
    # Merge only explicit, consistent physical owners. Source labels or equal
    # scalar values never assert identity. Missing roles are rejected earlier.
    groups = {}
    for i, (arm, coefficient) in enumerate(zip(arms, coefficients)):
        key = ("owner", arm["physical_observation_id"]) if arm["physical_observation_id"] is not None else ("role", i)
        if key in groups:
            old, count = groups[key]
            groups[key] = old, count + coefficient
        else:
            groups[key] = arm, coefficient
    point = lower = upper = Fraction(0)
    lower_closed = upper_closed = True
    kinds = set()
    for arm, coefficient in groups.values():
        if coefficient == 0:
            continue
        value = _range(arm)
        kinds |= value.kinds
        point = None if point is None or value.point is None else point + coefficient * value.point
        lo, hi = (value.lower, value.upper) if coefficient > 0 else (value.upper, value.lower)
        lc, uc = (value.lower_closed, value.upper_closed) if coefficient > 0 else (value.upper_closed, value.lower_closed)
        lower = None if lower is None or lo is None else lower + coefficient * lo
        upper = None if upper is None or hi is None else upper + coefficient * hi
        lower_closed &= lc
        upper_closed &= uc
    return _Range(point, lower, upper, lower_closed, upper_closed, frozenset(kinds))


def _number(value):
    if value is None:
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) and (result != 0 or value == 0) else None


def _origin(arms, *, raw=False):
    origins = {arm["origin"] for arm in arms if arm is not None}
    return ("synthetic" if "synthetic" in origins else "graph_derived" if "graph_derived" in origins
            else next(iter(origins)) if raw and origins else "calculated")


def _qualifications(inputs, arms, *, cross=False, covariance=False, model=False):
    result = set()
    if any(arm is not None and arm["origin"] == "synthetic" for arm in arms):
        result.add("synthetic_fixture")
    if any(arm is not None and arm["approximate"] for arm in arms):
        result.add("approximate_source_reading")
    if any(arm is not None and arm["digitization_interval"] is not None for arm in arms):
        result.add("conditional_digitization")
    if cross:
        relationships = inputs["relationships"]
        state = relationships["nonintended_conditions"]
        if state != "matched":
            result.add("nonintended_conditions_" + state)
        if relationships["control_reference_reuse"] == "unknown":
            result.add("unknown_control_reuse")
    if covariance and inputs["variance_status"] == "estimated":
        result.add("estimated_covariance")
    if model and inputs["model_kind"] == "known_joint_normal_source_means":
        result.add("known_normal_source_means")
    return result


def _cell(value, unit, formula, arms, *, reasons=(), qualifications=(), raw=False):
    reasons, qualifications = set(reasons), set(qualifications)
    result = {"value": None, "lower": None, "upper": None, "relation": "none",
        "approximate": any(arm is not None and arm["approximate"] for arm in arms),
        "unit": unit, "status": "unavailable", "origin": _origin(arms, raw=raw),
        "unavailable_reason": None, "formula_code": formula,
        "conditional_on": sorted(qualifications), "bound_kind": "none",
        "bound_state": {"lower": "unknown", "upper": "unknown"}}
    if reasons:
        result["status"] = ("conflicting" if any(reason.startswith("conflicting_") for reason in reasons)
            else "unsupported" if "unsupported_source_expression" in reasons else
            "partial" if raw and reasons == {"unknown_unit"} and arms[0]["status"] in ("point", "bound") else "unavailable")
    elif value is not None:
        bounded = bool(value.kinds)
        result["bound_kind"] = "mixed" if len(value.kinds) > 1 else next(iter(value.kinds)) if value.kinds else "none"
        result["value"] = _number(value.point)
        if value.point is not None and result["value"] is None:
            reasons.add("numeric_range_failure")
        if bounded:
            for side in ("lower", "upper"):
                exact = getattr(value, side)
                converted = _number(exact)
                result[side] = converted
                result["bound_state"][side] = "unbounded" if exact is None else "available" if converted is not None else "numeric_range_failure"
                if exact is not None and converted is None:
                    reasons.add("numeric_range_failure")
        else:
            result["bound_state"] = dict.fromkeys(("lower", "upper"), "not_applicable")
        lower, upper = result["lower"], result["upper"]
        if lower is not None and upper is not None:
            result["relation"] = "interval"
        elif lower is not None:
            result["relation"] = "ge" if value.lower_closed else "gt"
        elif upper is not None:
            result["relation"] = "le" if value.upper_closed else "lt"
        elif result["value"] is not None:
            result["relation"] = "eq"
        available = any(result[name] is not None for name in ("value", "lower", "upper"))
        result["status"] = ("partial" if reasons and available else "available" if result["value"] is not None
                             else "bounded" if available else "unavailable")
        if not available and not reasons:
            reasons.add("uninformative_bounds")
    result["unavailable_reason"] = sorted(reasons) or None
    return result


def _point(value):
    return None if value is None else _Range(value, value, value)


def _sqrt(value):
    with localcontext() as context:
        context.prec = 80
        return (Decimal(value.numerator) / Decimal(value.denominator)).sqrt()


def _bounded_index(score):
    # tanh saturates to a finite endpoint even when the exact S exceeds float
    # range. A nonzero tiny result must never silently become exact zero.
    if score == 0:
        return Fraction(0)
    if abs(score) > 100:
        return Fraction(1 if score > 0 else -1)
    half = _number(score / 2)
    if half is None:
        return None
    result = math.tanh(half)
    return result if result != 0 else None


def populate_controlled_response(inputs):
    """Populate four raw responses, two controlled pairs and their joint effect.

    e = x0-x1-x2+x3; V = [1,-1,-1,1] C [1,-1,-1,1]^T. Units
    and the biological normalization identity must both be compatible. Every
    linear operation uses exact rationals and explicit physical aliases, not
    independent intermediate pair intervals. Each final numerical dependency
    has its own finite-range check. Invalid direct covariance raises; missing
    covariance leaves valid magnitudes intact. No count implies independence.
    """
    covariance = _validate(inputs)
    arms = [inputs["arms"][name] for name in PRIMITIVE_ORDER]
    cells = {}
    for i, arm in enumerate(arms):
        reasons = _operand_reasons(arm)
        value = _range(arm) if not reasons else None
        cells[COMPONENTS[i]] = _cell(value, _unit([arm]), _FORMULAS[i], [arm], reasons=reasons,
            qualifications=_qualifications(inputs, [arm]), raw=True)
    pair_reasons = []
    for index, (indices, label) in enumerate((((0, 1), "condition1"), ((2, 3), "condition0"))):
        selected = [arms[i] for i in indices]
        reasons = _pair_reasons(inputs, indices, label)
        pair_reasons.append(reasons)
        qualifications = _qualifications(inputs, selected)
        if inputs["relationships"][label + "_control_application"] == "shared_reference_assumption":
            qualifications.add("shared_reference_assumption")
        cells[COMPONENTS[4 + index]] = _cell(_linear(selected, (1, -1)) if not reasons else None,
            _unit(selected), _FORMULAS[4 + index], selected, reasons=reasons, qualifications=qualifications)
    reasons = _effect_reasons(inputs, pair_reasons)
    qualifications = _qualifications(inputs, arms, cross=True)
    if any(inputs["relationships"][label + "_control_application"] == "shared_reference_assumption"
           for label in ("condition1", "condition0")):
        qualifications.add("shared_reference_assumption")
    effect = _linear(arms, (1, -1, -1, 1)) if not reasons else None
    unit = _unit(arms)
    cells[COMPONENTS[6]] = _cell(effect, unit, _FORMULAS[6], arms, reasons=reasons, qualifications=qualifications)
    variance_reasons = set(reasons)
    if effect is not None and effect.point is None:
        variance_reasons.add("unresolved_censoring_model")
    if covariance is None:
        variance_reasons.add("unknown_covariance")
    coefficients = (1, -1, -1, 1)
    variance = (sum(coefficients[i] * covariance[i][j] * coefficients[j] for i in range(4) for j in range(4))
                if not variance_reasons else None)
    variance_qualifications = qualifications | _qualifications(inputs, arms, covariance=True)
    variance_unit = "(" + unit + ")^2" if unit is not None else None
    cells[COMPONENTS[7]] = _cell(_point(variance), variance_unit, _FORMULAS[7], arms,
        reasons=variance_reasons, qualifications=variance_qualifications)
    cells[COMPONENTS[8]] = _cell(_point(_sqrt(variance)) if variance is not None else None, unit,
        _FORMULAS[8], arms, reasons=variance_reasons, qualifications=variance_qualifications)
    positive_reasons = variance_reasons | ({"nonpositive_variance_for_model"} if variance is not None and variance <= 0 else set())
    cells[COMPONENTS[9]] = _cell(_point(1 / variance) if variance is not None and variance > 0 else None,
        "(" + unit + ")^-2" if unit is not None else None, _FORMULAS[9], arms,
        reasons=positive_reasons, qualifications=variance_qualifications)
    model_reasons = set(positive_reasons)
    if inputs["variance_status"] == "estimated":
        model_reasons.add("estimated_covariance")
    if inputs["model_kind"] == "none":
        model_reasons.add("observation_model_unselected")
    if any(arm is not None and arm["status"] == "bound" for arm in arms):
        model_reasons.add("unresolved_censoring_model")
    if any(arm is not None and (arm["approximate"] or arm["origin"] == "graph_derived"
                                or arm["digitization_interval"] is not None) for arm in arms):
        model_reasons.add("unresolved_reading_model")
    score = effect.point * abs(effect.point) / (2 * variance) if not model_reasons else None
    model_qualifications = variance_qualifications | _qualifications(inputs, arms, model=True)
    cells[COMPONENTS[10]] = _cell(_point(score), "dimensionless", _FORMULAS[10], arms,
        reasons=model_reasons, qualifications=model_qualifications)
    index = _bounded_index(score) if score is not None else None
    cells[COMPONENTS[11]] = _cell(_point(index), "dimensionless", _FORMULAS[11], arms,
        reasons=model_reasons | ({"numeric_range_failure"} if score is not None and index is None else set()),
        qualifications=model_qualifications)
    return {"version": VERSION, "primitive_order": list(PRIMITIVE_ORDER),
            "inputs": deepcopy(inputs), "cells": cells}


__all__ = ["INPUT_VERSION", "VERSION", "PRIMITIVE_ORDER", "COMPONENTS", "CELL_FIELDS",
           "ARM_FIELDS", "RELATIONSHIP_FIELDS", "REASONS",
           "validate_controlled_response_inputs", "populate_controlled_response"]
