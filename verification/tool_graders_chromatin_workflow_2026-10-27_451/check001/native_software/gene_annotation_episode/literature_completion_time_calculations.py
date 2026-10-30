"""Exact positive-time domains and endpoint-time ratios; no activity inference."""
from fractions import Fraction
import math

from .literature_completion_time_inputs import ROLES, validate_completion_time_extraction
from .literature_rate_domains import _divide, _encode, _project, INF

VERSION = "a105_completion_time_components_v1"
COMPONENTS = ("numerator_time", "denominator_time", "completion_time_ratio", "inverse_completion_time_ratio")
REASONS = ("source_measurement_unavailable", "source_time_unit_unreported", "unsupported_source_time_unit",
    "nonpositive_physical_time", "endpoint_relation_unknown", "endpoint_relation_conflicting", "different_endpoints",
    "preparation_relation_unknown", "preparation_relation_conflicting", "pair_relationship_unknown",
    "pair_relationship_conflicting", "source_meaning_unavailable", "qualification_unknown", "qualification_conflicting",
    "reused_source_observation", "numerical_model_range")
CONDITIONS = ("strictly_positive_physical_completion_time", "source_endpoint_and_pair_interpretations",
    "reported_operand_cartesian_enclosure", "preparation_protocol_comparison_only")
LIMITS = ("inverse_endpoint_time_is_not_intrinsic_rate_or_molecular_activity_retention",
    "protocol_comparison_does_not_isolate_intended_change",
    "unknown_retained_molecule_amount_is_not_corrected",
    "no_contaminant_fraction_or_function_probability",
    "reported_limits_are_not_sampling_confidence_intervals",
    "ratio_and_inverse_are_dependent_representations")


def _operand(row):
    if row is None:
        return None, "source_measurement_unavailable"
    if row["unavailable_reason"]:
        return None, row["unavailable_reason"]
    q = Fraction(row["exact_minutes"])
    return {"none": (q, True, q, True), "lt": (Fraction(0), False, q, False),
        "le": (Fraction(0), False, q, True), "gt": (q, False, INF, False),
        "ge": (q, q > 0, INF, False)}[row["bound"]], None


def _pair_reason(extraction, reasons):
    if any(reasons.values()):
        return next(reason for reason in reasons.values() if reason)
    comparison = extraction["comparison"]
    for field in ("endpoint_relation", "preparation_relation", "pair_relationship"):
        value = comparison[field]["value"]
        if value in ("unknown", "conflicting"):
            return field + "_" + value
        if field == "endpoint_relation" and value == "different":
            return "different_endpoints"
    rows = [extraction["quantities"][role] for role in ROLES]
    for row in rows:
        if row["qualification"]["value"] in ("unknown", "conflicting"):
            return "qualification_" + row["qualification"]["value"]
        if any(row["meanings"][field] is None for field in ("preparation", "endpoint")):
            return "source_meaning_unavailable"
    n, d = rows
    if (n["measurement_key"] == d["measurement_key"] or n["physical_observation_key"] is not None
            and n["physical_observation_key"] == d["physical_observation_key"]):
        return "reused_source_observation"
    return None


def populate_completion_time_components(extraction):
    """Populate four numerical cells, including strict reported-limit images.

    Times describe their actual source preparations reaching the selected same
    endpoint. Their ratio is a descriptive comparison across protocols. Applying
    positivity is an explicit physical conditioning, not a source observation.
    Approximate reports remain approximate without invented tolerance or noise.
    """
    extraction = validate_completion_time_extraction(extraction)
    operands = {role: _operand(extraction["quantities"][role]) for role in ROLES}
    reason = _pair_reason(extraction, {role: item[1] for role, item in operands.items()})
    n, d = (operands[role][0] for role in ROLES)
    cells = {}
    for component in COMPONENTS:
        roles = (component.removesuffix("_time"),) if component in ("numerator_time", "denominator_time") else ROLES
        individual = len(roles) == 1
        failure = operands[roles[0]][1] if individual else reason
        domain = operands[roles[0]][0] if individual else None if failure else _divide(
            n if component == "completion_time_ratio" else d, d if component == "completion_time_ratio" else n)
        conditioning = list(CONDITIONS[:1] if individual else CONDITIONS)
        projected = _project(domain, basis="reported_operand_algebra" if not individual else "reported_time_operand",
            conditioning="strictly_positive_physical_completion_time", failure=failure)
        if projected["failure"] and failure is None:
            failure = projected["failure"]
        point = domain is not None and domain[0] == domain[2]
        point_value = None
        if point and failure is None:
            try:
                point_value = float(domain[0])
                if not math.isfinite(point_value) or point_value == 0 and domain[0] != 0:
                    raise OverflowError
            except (ValueError, OverflowError):
                failure = "numerical_model_range"
        row = extraction["quantities"][roles[0]] if individual else None
        cells[component] = {"value": point_value if failure is None else None,
            "unit": "min" if individual and domain is not None else None if individual else "dimensionless",
            "status": "unavailable" if failure else "point" if point else "bounded",
            "unavailable_reason": failure, "approximate": any(extraction["quantities"][role] and
                extraction["quantities"][role]["approximate"] for role in roles),
            "origin": row["origin"] if row else "derived", "conditional_on": conditioning,
            "formula": "source_" + roles[0] + "_time_in_minutes" if individual else
                "numerator_time/denominator_time" if component == "completion_time_ratio" else "denominator_time/numerator_time",
            "reported_domain": projected, "exact_domain": _encode(domain),
            "input_measurement_keys": [extraction["quantities"][role]["measurement_key"] for role in roles
                if extraction["quantities"][role] and extraction["quantities"][role]["measurement_key"]]}
    return {"version": VERSION, "axis": "A105", "evaluation_scope": "source_preparation_completion_time",
        "cells": cells, "interpretation_limits": list(LIMITS), "annotation_credit": None,
        "independent_preparation_count": None, "sampling_confidence_interval": None}
