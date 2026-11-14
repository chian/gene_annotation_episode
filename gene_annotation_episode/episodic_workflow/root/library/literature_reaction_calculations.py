"""Pure reported-ratio comparisons and simple resource constraints for A110.

These operations use the caller's explicit physical/design meanings. They do
not read a paper, correct a measurement, infer independence, establish a native
resource inventory, transfer a reference annotation, or compile annotation
credit. Signed comparisons are proposed conventions, not probabilities.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a110_reaction_constraints_v1"
COMPONENTS = (
    "ratio_mean", "claim_nominal_squared_error", "claim_mean_squared_error",
    "reaction_comparison", "reaction_comparison_lower", "reaction_comparison_upper",
    "resource_capacity", "resource_capacity_lower", "resource_capacity_upper",
    "resource_coverage", "resource_coverage_lower", "resource_coverage_upper",
    "resource_comparison", "resource_comparison_lower", "resource_comparison_upper",
)
FORMULAS = {
    "ratio_mean": "reported_mean_or_mean_independent_units",
    "claim_nominal_squared_error": "(mean-claim)^2",
    "claim_mean_squared_error": "mean((y-claim)^2)_or_(mean-claim)^2+(n-1)*SD^2/n",
    "reaction_comparison": "min_alternatives((e_alt-e_claim)/(e_alt+e_claim));both_zero=0",
    "reaction_comparison_lower": "min_alternatives(logical_contrast_lower)",
    "reaction_comparison_upper": "min_alternatives(logical_contrast_upper)",
    "resource_capacity": "min_resources(U/a)",
    "resource_capacity_lower": "min_resources(U_lower/a);missing_resource_lower=0",
    "resource_capacity_upper": "min_resources(U_upper/a);missing_resource_upper=unbounded",
    "resource_coverage": "min(1,capacity/demand)",
    "resource_coverage_lower": "min(1,capacity_lower/demand)",
    "resource_coverage_upper": "min(1,capacity_upper/demand)",
    "resource_comparison": "2*coverage-1",
    "resource_comparison_lower": "2*coverage_lower-1",
    "resource_comparison_upper": "2*coverage_upper-1",
}
DETAIL_FORMULAS = (
    "reported_prediction", "y-prediction", "(mean-prediction)^2",
    "mean((y-prediction)^2)_or_(mean-prediction)^2+(n-1)*SD^2/n",
    "(e_alt-e_claim)/(e_alt+e_claim);both_zero=0", "sample_SD_independent_units",
)
REASONS = (
    "ratio_unreported", "mean_unreported", "claim_unreported",
    "prediction_unreported", "sampling_moments_unreported", "alternatives_unreported",
    "alternative_comparison_unreported", "budget_unreported",
    "resources_incomplete", "resource_value_unreported", "demand_unreported",
    "capacity_upper_unbounded", "numerical_model_range",
)
CONDITIONAL_CODES = (
    "reported_ratio_scale", "declared_independent_units", "constant_prediction",
    "summary_sample_SD_and_exact_n", "explicit_single_unit_summary",
    "fixed_named_alternatives", "logical_enclosure_not_confidence_interval",
    "simple_fixed_consumption_model", "same_period_and_compartment",
    "supplied_reagents_only", "usable_resources_as_declared", "declared_resource_completeness",
    "explicit_resource_domain", "positive_point_demand", "source_comparison_convention",
)
RATIO_MODES = ("independent_units", "source_summary")
RATIO_KINDS = ("product_pair", "formed_per_consumed", "formed_per_supplied", "signal_ratio")
RATIO_UNITS = ("mol_per_mol", "signal_per_signal")
ORIGINS = ("reported", "graph_derived", "synthetic")
BUDGET_BASES = ("supplied_reagent_batch", "usable_batch", "usable_rate")
BUDGET_UNITS = ("umol", "uM", "umol_per_min", "uM_per_min")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _fields(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _number(value, field, *, nullable=False, nonnegative=False, positive=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)
    if positive and value <= 0:
        _fail("positive_value_required", field)
    if nonnegative and value < 0:
        _fail("nonnegative_value_required", field)


def _identity(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_identity_required", field)


def _enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail("unsupported_" + field.rsplit(".", 1)[-1], field)


def _array(value, field):
    if not isinstance(value, list):
        _fail("array_required", field)


def _validate(inputs):
    _fields(inputs, ("ratio", "budget"), "inputs")
    ratio = inputs["ratio"]
    if ratio is not None:
        _fields(ratio, ("mode", "ratio_kind", "unit", "origin", "observations", "mean",
                        "sample_sd", "independent_n", "claim", "alternatives"), "ratio")
        for name, allowed in (("mode", RATIO_MODES), ("ratio_kind", RATIO_KINDS),
                              ("unit", RATIO_UNITS), ("origin", ORIGINS)):
            _enum(ratio[name], allowed, "ratio." + name)
        if (ratio["ratio_kind"] == "signal_ratio") != (ratio["unit"] == "signal_per_signal"):
            _fail("ratio_kind_unit_mismatch", "ratio.unit")
        for name in ("mean", "sample_sd", "claim"):
            _number(ratio[name], "ratio." + name, nullable=True, nonnegative=name == "sample_sd")
        n = ratio["independent_n"]
        if n is not None and (type(n) is not int or n < 1):
            _fail("positive_integer_required", "ratio.independent_n")
        if n == 1 and ratio["sample_sd"] is not None:
            _fail("single_unit_has_no_sample_sd", "ratio.sample_sd")
        _array(ratio["observations"], "ratio.observations")
        seen = set()
        for index, observation in enumerate(ratio["observations"]):
            field = "ratio.observations." + str(index)
            _fields(observation, ("measurement_key", "value"), field)
            _identity(observation["measurement_key"], field + ".measurement_key")
            _number(observation["value"], field + ".value")
            if observation["measurement_key"] in seen:
                _fail("duplicate_measurement_key", field + ".measurement_key")
            seen.add(observation["measurement_key"])
        if ratio["mode"] == "independent_units":
            if not ratio["observations"]:
                _fail("independent_observations_required", "ratio.observations")
            if any(ratio[field] is not None for field in ("mean", "sample_sd", "independent_n")):
                _fail("independent_summary_fields_must_be_null", "ratio")
        elif ratio["observations"]:
            _fail("summary_observations_must_be_empty", "ratio.observations")
        _array(ratio["alternatives"], "ratio.alternatives")
        seen = set()
        for index, alternative in enumerate(ratio["alternatives"]):
            field = "ratio.alternatives." + str(index)
            _fields(alternative, ("key", "prediction"), field)
            _identity(alternative["key"], field + ".key")
            _number(alternative["prediction"], field + ".prediction", nullable=True)
            if alternative["key"] in seen:
                _fail("duplicate_alternative_key", field + ".key")
            seen.add(alternative["key"])

    budget = inputs["budget"]
    if budget is not None:
        _fields(budget, ("basis", "unit", "origin", "resources_complete", "resources", "demand"), "budget")
        for name, allowed in (("basis", BUDGET_BASES), ("unit", BUDGET_UNITS), ("origin", ORIGINS)):
            _enum(budget[name], allowed, "budget." + name)
        if (budget["basis"] == "usable_rate") != budget["unit"].endswith("_per_min"):
            _fail("budget_basis_unit_mismatch", "budget.unit")
        if type(budget["resources_complete"]) is not bool:
            _fail("boolean_required", "budget.resources_complete")
        _number(budget["demand"], "budget.demand", nullable=True, positive=True)
        _array(budget["resources"], "budget.resources")
        if not budget["resources"]:
            _fail("resources_required", "budget.resources")
        seen = set()
        for index, resource in enumerate(budget["resources"]):
            field = "budget.resources." + str(index)
            _fields(resource, ("resource_key", "value", "lower", "upper", "coefficient"), field)
            _identity(resource["resource_key"], field + ".resource_key")
            if resource["resource_key"] in seen:
                _fail("duplicate_resource_key", field + ".resource_key")
            seen.add(resource["resource_key"])
            for name in ("value", "lower", "upper"):
                _number(resource[name], field + "." + name, nullable=True, nonnegative=True)
            _number(resource["coefficient"], field + ".coefficient", positive=True)
            low, value, high = resource["lower"], resource["value"], resource["upper"]
            if low is not None and high is not None and low > high:
                _fail("ordered_resource_bounds_required", field)
            if value is not None and ((low is not None and value < low) or (high is not None and value > high)):
                _fail("nominal_outside_resource_bounds", field + ".value")


def _fraction(value):
    return None if value is None else Fraction(value)


def _cell(value, unit, formula, *, reason=None, origin="derived", conditional=(), bound=None):
    if value is not None and reason is None:
        try:
            converted = float(value)
        except (OverflowError, ValueError):
            converted = None
        if converted is not None and math.isfinite(converted):
            if bound is not None:
                exact = Fraction(converted)
                if bound == "lower" and exact > value:
                    converted = math.nextafter(converted, -math.inf)
                if bound == "upper" and exact < value:
                    converted = math.nextafter(converted, math.inf)
            elif converted == 0 and value != 0:
                converted = None
        if converted is None or not math.isfinite(converted):
            value, reason = None, "numerical_model_range"
        else:
            value = converted
    return {"value": value, "unit": unit,
            "status": "unavailable" if value is None else "populated",
            "formula": formula, "origin": origin,
            "unavailable_reason": reason, "conditional_on": list(conditional)}


def _sqrt(value):
    """Scale exact variance before sqrt, avoiding premature float overflow."""
    if value == 0:
        return 0.0
    exponent = (value.numerator.bit_length() - value.denominator.bit_length()) // 2
    scaled = value / (Fraction(2) ** (2 * exponent))
    try:
        result = math.ldexp(math.sqrt(float(scaled)), exponent)
    except OverflowError:
        return None
    return result if math.isfinite(result) and result != 0 else None


def _ratio_parts(ratio):
    if ratio is None:
        return None, None, None, (), "ratio_unreported", [], None
    if ratio["mode"] == "independent_units":
        values = [Fraction(row["value"]) for row in ratio["observations"]]
        n = len(values)
        mean = sum(values, Fraction(0)) / n
        variance = sum(((value - mean) ** 2 for value in values), Fraction(0)) / n
        sample_variance = variance * n / (n - 1) if n > 1 else None
        return mean, variance, n, ("reported_ratio_scale", "declared_independent_units", "constant_prediction"), None, values, sample_variance
    mean, sd, n = _fraction(ratio["mean"]), _fraction(ratio["sample_sd"]), ratio["independent_n"]
    conditions = ("reported_ratio_scale", "constant_prediction")
    if mean is None:
        return mean, None, n, conditions, "mean_unreported", [], None
    if n == 1:
        return mean, Fraction(0), n, (*conditions, "explicit_single_unit_summary"), None, [], None
    if sd is None or n is None:
        return mean, None, n, conditions, "sampling_moments_unreported", [], None
    return mean, Fraction(n - 1, n) * sd ** 2, n, (*conditions, "summary_sample_SD_and_exact_n"), None, [], None


def populate_reaction_constraints(inputs):
    """Populate defined A110 reference-scale components without source I/O.

    Exact-rational intermediate calculations preserve representable signed
    contrasts even when squared errors exceed or underflow float range. Every
    final point cell independently reports range failure. Logical bound cells
    round outward. Missing sampling moments are not zero variation; missing
    resource constraints are not unlimited measured capacity.
    """
    _validate(inputs)
    ratio, budget = inputs["ratio"], inputs["budget"]
    mean, variation, n, conditions, ratio_reason, values, sample_variance = _ratio_parts(ratio)
    cells, comparisons = {}, []
    ratio_unit = ratio["unit"] if ratio else "unreported"
    ratio_origin = ratio["origin"] if ratio and ratio["mode"] == "source_summary" else "derived"
    cells["ratio_mean"] = _cell(mean, ratio_unit, FORMULAS["ratio_mean"],
        reason="ratio_unreported" if ratio is None else "mean_unreported" if mean is None else None,
        origin=ratio_origin, conditional=("reported_ratio_scale",))
    claim = _fraction(ratio["claim"]) if ratio else None
    nominal_claim = (mean - claim) ** 2 if mean is not None and claim is not None else None
    claim_reason = "ratio_unreported" if ratio is None else "claim_unreported" if claim is None else ratio_reason
    nominal_reason = "ratio_unreported" if ratio is None else "claim_unreported" if claim is None else "mean_unreported" if mean is None else None
    e_claim = nominal_claim + variation if nominal_claim is not None and variation is not None else None
    cells["claim_nominal_squared_error"] = _cell(nominal_claim, "squared_ratio", FORMULAS["claim_nominal_squared_error"],
        reason=nominal_reason, conditional=("reported_ratio_scale", "constant_prediction"))
    cells["claim_mean_squared_error"] = _cell(e_claim, "squared_ratio", FORMULAS["claim_mean_squared_error"],
        reason=claim_reason, conditional=conditions)
    residuals = []
    if ratio:
        models = [("claim", claim), *[(alternative["key"], _fraction(alternative["prediction"])) for alternative in ratio["alternatives"]]]
        for model_index, (key, prediction) in enumerate(models):
            selected = values if ratio["mode"] == "independent_units" else ([] if mean is None else [mean])
            residuals.append({"model_key": key, "model_role": "claim" if model_index == 0 else "alternative", "basis": "independent_units" if values else "source_mean_only",
                "residuals": [_cell(value - prediction if prediction is not None else None, ratio_unit,
                    "y-prediction", reason="prediction_unreported" if prediction is None else None,
                    conditional=("reported_ratio_scale", "constant_prediction")) for value in selected]})
    scores, lower_scores, upper_scores = [], [], []
    for alternative in ratio["alternatives"] if ratio else []:
        prediction = _fraction(alternative["prediction"])
        nominal = (mean - prediction) ** 2 if mean is not None and prediction is not None else None
        e_alt = nominal + variation if nominal is not None and variation is not None else None
        error_reason = "prediction_unreported" if prediction is None else ratio_reason
        nominal_alt_reason = "prediction_unreported" if prediction is None else "mean_unreported" if mean is None else None
        score = None
        if e_claim is not None and e_alt is not None:
            score = (e_alt - e_claim) / (e_alt + e_claim) if e_alt + e_claim else Fraction(0)
        score_reason = claim_reason or error_reason
        scores.append(score)
        lower_scores.append(score if score is not None else Fraction(-1))
        upper_scores.append(score if score is not None else Fraction(1))
        comparisons.append({"key": alternative["key"],
            "prediction": _cell(prediction, ratio_unit, "reported_prediction", reason="prediction_unreported" if prediction is None else None, origin="proposed"),
            "nominal_squared_error": _cell(nominal, "squared_ratio", "(mean-prediction)^2", reason=nominal_alt_reason, conditional=conditions),
            "mean_squared_error": _cell(e_alt, "squared_ratio", "mean((y-prediction)^2)_or_(mean-prediction)^2+(n-1)*SD^2/n", reason=error_reason, conditional=conditions),
            "signed_contrast": _cell(score, "dimensionless", "(e_alt-e_claim)/(e_alt+e_claim);both_zero=0", reason=score_reason, origin="proposed", conditional=(*conditions, "source_comparison_convention"))})
    comparison = min(scores) if scores and all(score is not None for score in scores) else None
    comparison_reason = None if comparison is not None else "ratio_unreported" if ratio is None else "alternatives_unreported" if not scores else "alternative_comparison_unreported"
    cells["reaction_comparison"] = _cell(comparison, "dimensionless", FORMULAS["reaction_comparison"], reason=comparison_reason,
        origin="proposed", conditional=(*conditions, "fixed_named_alternatives", "source_comparison_convention"))
    for suffix, value in (("lower", min(lower_scores) if lower_scores else Fraction(-1)),
                          ("upper", min(upper_scores) if upper_scores else Fraction(1))):
        component = "reaction_comparison_" + suffix
        cells[component] = _cell(value, "dimensionless", FORMULAS[component], origin="proposed",
            conditional=("fixed_named_alternatives", "logical_enclosure_not_confidence_interval"), bound=suffix)

    capacity = None
    capacity_reason = "budget_unreported" if budget is None else None
    lower, upper = Fraction(0), None
    limiting, lower_limiting, upper_limiting = [], [], []
    if budget:
        resource_values = [(resource["resource_key"], _fraction(resource["value"]), Fraction(resource["coefficient"])) for resource in budget["resources"]]
        if budget["resources_complete"] and all(value is not None for _, value, _ in resource_values):
            capacity = min(value / coefficient for _, value, coefficient in resource_values)
            limiting = [key for key, value, coefficient in resource_values if value / coefficient == capacity]
        else:
            capacity_reason = "resources_incomplete" if not budget["resources_complete"] else "resource_value_unreported"
        lows = [(resource["resource_key"], Fraction(resource["lower"] or 0) / Fraction(resource["coefficient"])) for resource in budget["resources"]]
        lower = min(value for _, value in lows) if budget["resources_complete"] else Fraction(0)
        lower_limiting = [key for key, value in lows if value == lower]
        highs = [(resource["resource_key"], Fraction(resource["upper"]) / Fraction(resource["coefficient"])) for resource in budget["resources"] if resource["upper"] is not None]
        if highs:
            upper = min(value for _, value in highs)
            upper_limiting = [key for key, value in highs if value == upper]
        if upper == 0:
            capacity, capacity_reason = Fraction(0), None
            limiting = list(upper_limiting)
    budget_unit = budget["unit"] if budget else "unreported"
    budget_conditions = ("simple_fixed_consumption_model", "same_period_and_compartment", "declared_resource_completeness")
    if budget:
        budget_conditions += ("supplied_reagents_only" if budget["basis"] == "supplied_reagent_batch" else "usable_resources_as_declared",)
    cells["resource_capacity"] = _cell(capacity, budget_unit, FORMULAS["resource_capacity"], reason=capacity_reason, conditional=budget_conditions)
    cells["resource_capacity_lower"] = _cell(lower, budget_unit, FORMULAS["resource_capacity_lower"], conditional=(*budget_conditions, "explicit_resource_domain", "logical_enclosure_not_confidence_interval"), bound="lower")
    cells["resource_capacity_upper"] = _cell(upper, budget_unit, FORMULAS["resource_capacity_upper"], reason="capacity_upper_unbounded" if upper is None else None, conditional=(*budget_conditions, "explicit_resource_domain", "logical_enclosure_not_confidence_interval"), bound="upper")
    demand = _fraction(budget["demand"]) if budget else None
    coverage = min(Fraction(1), capacity / demand) if demand is not None and capacity is not None else None
    coverage_reason = "budget_unreported" if budget is None else "demand_unreported" if demand is None else capacity_reason
    coverage_lower = min(Fraction(1), lower / demand) if demand is not None else Fraction(0)
    coverage_upper = min(Fraction(1), upper / demand) if demand is not None and upper is not None else Fraction(1)
    for component, value, reason, bound in (
        ("resource_coverage", coverage, coverage_reason, None),
        ("resource_coverage_lower", coverage_lower, None, "lower"),
        ("resource_coverage_upper", coverage_upper, None, "upper"),
        ("resource_comparison", 2 * coverage - 1 if coverage is not None else None, coverage_reason, None),
        ("resource_comparison_lower", 2 * coverage_lower - 1, None, "lower"),
        ("resource_comparison_upper", 2 * coverage_upper - 1, None, "upper"),
    ):
        cells[component] = _cell(value, "dimensionless", FORMULAS[component], reason=reason,
            origin="proposed" if component.startswith("resource_comparison") else "derived",
            conditional=(*budget_conditions, *( ("positive_point_demand",) if demand is not None else ()),
                         *(("explicit_resource_domain", "logical_enclosure_not_confidence_interval") if bound else ())), bound=bound)
    derived_sd = _sqrt(sample_variance) if sample_variance is not None else None
    return {"version": VERSION, "inputs": deepcopy(inputs),
        "cells": {component: cells[component] for component in COMPONENTS},
        "comparisons": comparisons,
        "ratio_details": {"mode": ratio["mode"] if ratio else None,
            "ratio_kind": ratio["ratio_kind"] if ratio else None,
            "independent_n": n, "reported_sample_sd": ratio["sample_sd"] if ratio else None,
            "derived_sample_sd": _cell(derived_sd, ratio_unit, "sample_SD_independent_units",
                reason="numerical_model_range" if sample_variance is not None and derived_sd is None else "sampling_moments_unreported" if derived_sd is None else None,
                conditional=("declared_independent_units",)),
            "residuals_by_model": residuals,
            "conditions": list(conditions),
            "bounds_meaning": "logical_enclosure_not_confidence_interval"},
        "budget_details": {"basis": budget["basis"] if budget else None,
            "unit": budget["unit"] if budget else None,
            "resources_complete": budget["resources_complete"] if budget else None,
            "incomplete_resource_lower_bound": not budget["resources_complete"] if budget else None,
            "limiting_resource_keys": limiting,
            "lower_limiting_resource_keys": lower_limiting,
            "upper_limiting_resource_keys": upper_limiting,
            "bounds_meaning": "logical_enclosure_not_confidence_interval"}}


__all__ = ["VERSION", "COMPONENTS", "FORMULAS", "DETAIL_FORMULAS", "REASONS",
    "CONDITIONAL_CODES", "RATIO_MODES", "RATIO_KINDS", "RATIO_UNITS", "ORIGINS",
    "BUDGET_BASES", "BUDGET_UNITS", "populate_reaction_constraints"]
