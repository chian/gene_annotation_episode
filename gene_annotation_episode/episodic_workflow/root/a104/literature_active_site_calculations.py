"""Active-site amount components with exact reported-operand arithmetic.

These cells evaluate physical denominator adequacy, not universal reliability.
No source acquisition, rate mutation, score aggregation or observation occurs.
"""
from fractions import Fraction
import math

from .literature_active_site_inputs import ROLES, validate_active_site_extraction
from .literature_rate_domains import _contains_zero, _divide, _multiply, _subtract, _point, _encode, _project, INF

VERSION = "a105_active_site_components_v1"
COMPONENTS = ("protein_mass_concentration", "assumed_molecular_weight", "total_monomer_concentration",
    "active_site_concentration", "sites_per_total_monomer", "conditional_active_monomer_fraction",
    "conditional_nominal_to_active_denominator_factor", "reported_active_fraction", "derived_minus_reported_fraction")
COMPONENT_ROLES = {name: (name,) for name in ROLES}
COMPONENT_ROLES.update(total_monomer_concentration=ROLES[:2], sites_per_total_monomer=ROLES[:3],
    conditional_active_monomer_fraction=ROLES[:3], conditional_nominal_to_active_denominator_factor=ROLES[:3],
    derived_minus_reported_fraction=ROLES)
REASONS = ("source_measurement_unavailable", "source_unit_unreported", "source_unit_conflicting", "unsupported_source_unit",
    "negative_physical_amount", "nonpositive_molecular_weight", "empty_nonnegative_amount_domain",
    "zero_total_monomer_concentration", "zero_active_site_concentration", "active_fraction_exceeds_one", "molecular_basis_per_dimer_coefficient_unimplemented", "molecular_basis_unknown",
    "molecular_basis_conflicting", "amount_linkage_different", "amount_linkage_unknown", "amount_linkage_conflicting",
    "active_estimate_meaning_other", "active_estimate_meaning_unknown", "active_estimate_meaning_conflicting",
    "titrant_to_site_stoichiometry_other", "titrant_to_site_stoichiometry_unknown", "titrant_to_site_stoichiometry_conflicting",
    "titrant_concentration_basis_unknown", "titrant_concentration_basis_conflicting", "site_stoichiometry_other",
    "site_stoichiometry_unknown", "site_stoichiometry_conflicting", "source_meaning_unavailable", "qualification_unknown",
    "qualification_conflicting", "reused_source_observation", "numerical_model_range")
CONDITIONS = ("nonnegative_amounts_positive_molecular_weight", "reported_operand_cartesian_enclosure", "source_monomer_molecular_weight_basis",
    "same_source_preparation_and_assay", "source_titrated_active_site_estimate", "source_reported_one_to_one_titrant_to_site",
    "reported_nominal_titrant_concentration", "independently_standardized_active_titrant_concentration",
    "source_one_site_per_monomer_interpretation", "same_rate_with_total_monomer_denominator_required_before_application", "physical_one_site_fraction_in_unit_interval")
LIMITS = ("reported_points_are_not_exact_physical_values", "reported_bounds_are_not_sampling_confidence_intervals",
    "nominal_titrant_concentration_is_not_independently_standardized_active_concentration",
    "chemical_purity_is_not_active_titrant_molar_fraction", "titrated_active_site_estimate_not_divided_again_by_titrant_stoichiometry",
    "density_is_not_active_fraction_without_one_site_per_monomer", "dimer_molecular_weight_does_not_supply_monomer_coefficient",
    "factor_requires_same_rate_preparation_assay_and_total_monomer_denominator", "active_normalized_rates_must_not_be_corrected_again",
    "tag_or_preparation_comparison_does_not_isolate_causal_tag_effect", "aliquots_are_not_independent_preparations",
    "source_regression_sd_is_not_sem_preparation_cv_or_known_variance", "aliases_and_repeated_representations_are_not_independent_evidence",
    "active_fraction_is_not_optical_inner_filter_or_instrument_recovery", "no_universal_reliability_function_probability_or_annotation_credit")


def _operand(row):
    if row is None:
        return None, "source_measurement_unavailable"
    if row["unavailable_reason"]:
        return None, row["unavailable_reason"]
    q = Fraction(row["exact_value"])
    return {"none": _point(q), "lt": (Fraction(0), row["unit"]["canonical_unit"] != "kDa", q, False), "le": (Fraction(0), row["unit"]["canonical_unit"] != "kDa", q, True),
        "gt": (q, False, INF, False), "ge": (q, q > 0 or row["unit"]["canonical_unit"] != "kDa", INF, False)}[row["bound"]], None


def _relation(extraction, field, wanted):
    actual = extraction["interpretations"][field]["value"]
    return None if actual in wanted else ("molecular_basis_per_dimer_coefficient_unimplemented" if field == "molecular_basis" and actual == "per_dimer" else field + "_" + actual)


def _reason(extraction, operands, roles, fields):
    for role in roles:
        row = extraction["quantities"][role]
        if operands[role][1]:
            return operands[role][1]
        if row["qualification"]["value"] in ("unknown", "conflicting"):
            return "qualification_" + row["qualification"]["value"]
        if any(row["meanings"][field] is None for field in ("subject", "preparation", "assay")):
            return "source_meaning_unavailable"
    for field, wanted in fields:
        reason = _relation(extraction, field, wanted)
        if reason:
            return reason
    # Distinct measurands can share a preparation, but cannot reuse the same
    # physical measurement or numeric token as separate density operands.
    seen, physical = set(), set()
    for role in roles:
        row = extraction["quantities"][role]
        key, pk = row["measurement_key"], row["physical_observation_key"]
        if key in seen or pk is not None and pk in physical:
            return "reused_source_observation"
        seen.add(key)
        if pk is not None:
            physical.add(pk)
    return None


def populate_active_site_components(extraction):
    """Compile rho/MW, A/C and C/A; never apply any factor to a rate.

    Canonical rho is mg/mL (= g/L), MW is kDa, so C in nM is
    rho/MW*10^6. A/C describes sites per total monomer; only an explicit
    one-site-per-monomer interpretation labels that number an active fraction.
    A is already a titrated active-site estimate, never titrant amount to be
    divided again. Nominal titrant calibration remains explicit conditioning.
    """
    extraction = validate_active_site_extraction(extraction)
    operands = {role: _operand(extraction["quantities"][role]) for role in ROLES}
    monomer_fields = (("molecular_basis", ("per_monomer",)), ("amount_linkage", ("same_preparation_and_assay",)))
    active_fields = (*monomer_fields, ("active_estimate_meaning", ("titrated_active_sites",)),
        ("titrant_to_site_stoichiometry", ("reported_one_to_one",)),
        ("titrant_concentration_basis", ("nominal_reported", "independently_standardized_active")))
    c_reason = _reason(extraction, operands, ROLES[:2], monomer_fields)
    active_reason = _reason(extraction, operands, ROLES[:3], active_fields)
    alpha_reason = active_reason or _relation(extraction, "site_stoichiometry", ("one_site_per_monomer",))
    diff_reason = alpha_reason or _reason(extraction, operands, ROLES, active_fields)
    rho, mw, active, reported = (operands[role][0] for role in ROLES)
    c = _multiply(_divide(rho, mw), _point(Fraction(1000000))) if not c_reason else None
    active_reason = active_reason or ("zero_total_monomer_concentration" if c is not None and _contains_zero(c) else None)
    alpha_reason = active_reason or _relation(extraction, "site_stoichiometry", ("one_site_per_monomer",))
    density = _divide(active, c) if not active_reason else None
    alpha = density if not alpha_reason else None
    if alpha is not None:
        # Intersect only the biological fraction, with explicit conditioning.
        # The source density remains unchanged; an impossible point is unavailable.
        lower, lc, upper, uc = alpha
        if lower > 1 or lower == 1 and not lc:
            alpha, alpha_reason = None, "active_fraction_exceeds_one"
        else:
            alpha = (lower, lc, min(upper, Fraction(1)), uc if upper <= 1 else True)
    diff_reason = alpha_reason or _reason(extraction, operands, ROLES, active_fields)
    factor_reason = active_reason or ("zero_active_site_concentration" if active is not None and _contains_zero(active) else None)
    factor = _divide(c, active) if not factor_reason else None
    domains = {**{role: operands[role] for role in ROLES}, "total_monomer_concentration": (c, c_reason),
        "sites_per_total_monomer": (density, active_reason), "conditional_active_monomer_fraction": (alpha, alpha_reason),
        "conditional_nominal_to_active_denominator_factor": (factor, factor_reason),
        "derived_minus_reported_fraction": (_subtract(alpha, reported) if not diff_reason else None, diff_reason)}
    formulas = {role: "source_" + role + "_in_canonical_units" for role in ROLES}
    formulas.update(total_monomer_concentration="protein_mass_concentration/assumed_molecular_weight*10^6",
        sites_per_total_monomer="active_site_concentration/total_monomer_concentration",
        conditional_active_monomer_fraction="intersection(sites_per_total_monomer,[0,1])_given_one_site_per_monomer",
        conditional_nominal_to_active_denominator_factor="total_monomer_concentration/active_site_concentration",
        derived_minus_reported_fraction="conditional_active_monomer_fraction-reported_active_fraction")
    units = {"protein_mass_concentration": "mg/mL", "assumed_molecular_weight": "kDa",
        "total_monomer_concentration": "nM", "active_site_concentration": "nM"}
    cells = {}
    for name in COMPONENTS:
        domain, reason = domains[name]
        roles = COMPONENT_ROLES[name]
        conditions = list(CONDITIONS[:2])
        if name not in ROLES:
            conditions.extend(CONDITIONS[2:4])
        if name in ("sites_per_total_monomer", "conditional_active_monomer_fraction", "conditional_nominal_to_active_denominator_factor", "derived_minus_reported_fraction"):
            conditions.extend(CONDITIONS[4:6])
            basis = extraction["interpretations"]["titrant_concentration_basis"]["value"]
            if basis in ("nominal_reported", "independently_standardized_active"):
                conditions.append(CONDITIONS[6 if basis == "nominal_reported" else 7])
        if name in ("conditional_active_monomer_fraction", "derived_minus_reported_fraction"):
            conditions.extend((CONDITIONS[8], CONDITIONS[10]))
        if name == "conditional_nominal_to_active_denominator_factor":
            conditions.append(CONDITIONS[9])
        projected = _project(domain, basis="reported_operand" if name in ROLES else "reported_operand_algebra",
            conditioning="nonnegative_amounts_positive_molecular_weight", failure=reason)
        reason = reason or projected["failure"]
        point = domain is not None and domain[0] == domain[2]
        value = None
        if point and not reason:
            try:
                value = float(domain[0])
                if not math.isfinite(value) or value == 0 and domain[0] != 0:
                    raise OverflowError
            except (ValueError, OverflowError):
                reason = "numerical_model_range"
        cells[name] = {"value": value if not reason else None, "unit": units.get(name, "dimensionless"),
            "status": "unavailable" if reason else "point" if point else "bounded", "unavailable_reason": reason,
            "approximate": any(extraction["quantities"][role] and extraction["quantities"][role]["approximate"] for role in roles),
            "origin": extraction["quantities"][name]["origin"] if name in ROLES and extraction["quantities"][name] else "derived",
            "conditional_on": conditions, "formula": formulas[name], "reported_domain": projected, "exact_domain": _encode(domain),
            "input_measurement_keys": [extraction["quantities"][role]["measurement_key"] for role in roles
                if extraction["quantities"][role] and extraction["quantities"][role]["measurement_key"]]}
    return {"version": VERSION, "axis": "A105", "evaluation_scope": "active_site_titration_amount", "cells": cells,
        "interpretation_limits": list(LIMITS), "annotation_credit": None, "rate_factor_applied": False,
        "fraction_uncertainty": {"value": None, "status": "unavailable", "reason": "full_joint_covariance_propagation_not_implemented",
            "input_state": "joint_source_error_covariance_not_selected", "source_spreads_are_not_full_joint_uncertainty": True},
        "independent_preparation_count": None}
