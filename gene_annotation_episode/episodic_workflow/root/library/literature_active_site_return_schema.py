from copy import deepcopy
from gene_annotation_episode.domain import obj

ROLES = ("protein_mass_concentration", "assumed_molecular_weight", "active_site_concentration", "reported_active_fraction")

LITERAL_FIELDS = ("subject", "organism", "construct", "preparation", "assay", "condition", "endpoint", "measurement_identity")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
SPREAD_KINDS = ("regression_sd", "sd", "sem", "untyped", "unreported", "unknown", "conflicting")
SAMPLING = ("same_preparation_aliquots", "independent_preparations", "unknown", "conflicting")
INTERPRETATIONS = {
    "molecular_basis": ("per_monomer", "per_dimer", "unknown", "conflicting"),
    "amount_linkage": ("same_preparation_and_assay", "different", "unknown", "conflicting"),
    "active_estimate_meaning": ("titrated_active_sites", "other", "unknown", "conflicting"),
    "titrant_concentration_basis": ("nominal_reported", "independently_standardized_active", "unknown", "conflicting"),
    "titrant_to_site_stoichiometry": ("reported_one_to_one", "other", "unknown", "conflicting"),
    "site_stoichiometry": ("one_site_per_monomer", "other", "unknown", "conflicting"),
    "normalization_stage": ("none", "total_monomer", "active_sites", "unknown", "conflicting"),
}

COMPONENTS = ("protein_mass_concentration", "assumed_molecular_weight", "total_monomer_concentration",
    "active_site_concentration", "sites_per_total_monomer", "conditional_active_monomer_fraction",
    "conditional_nominal_to_active_denominator_factor", "reported_active_fraction", "derived_minus_reported_fraction")

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

NAMESPACE = "literature_active_site_cells"

def active_site_cells_schema():
    def ref(namespace):
        return {"type": "string", "format": "reference", "x-reference-namespace": namespace}
    witness = obj({"source_ref": ref("source"), "artifact_ref": ref("artifact"),
        "representation": {"type": "string", "enum": ["original", "text"]},
        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 1}})
    meaning = obj({"status": {"type": "string", "enum": ["selected", "not_selected", "withheld_amount_operand"]},
        "witness": {"anyOf": [deepcopy(witness), {"type": "null"}]}})
    def interpretation(values):
        return obj({"value": {"type": "string", "enum": list(values)}, "support": {"type": "array", "items": deepcopy(meaning)}})
    nullable_number = {"type": ["number", "null"]}
    exact_number = {"anyOf": [obj({"numerator": {"type": "string", "pattern": "^-?[0-9]+$"},
        "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}}), {"type": "null"}]}
    exact_domain = {"anyOf": [obj({"lower": deepcopy(exact_number), "upper": deepcopy(exact_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"}}), {"type": "null"}]}
    domain = obj({"kind": {"type": "string", "enum": ["point", "finite_interval", "lower_bounded", "upper_bounded", "unbounded", "unavailable"]},
        "lower": deepcopy(nullable_number), "upper": deepcopy(nullable_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"},
        "projection": {"type": "string", "enum": ["none", "exact", "outward"]},
        "basis": {"type": "string", "enum": ["reported_operand", "reported_operand_algebra"]},
        "conditioning": {"type": "string", "const": "nonnegative_amounts_positive_molecular_weight"},
        "failure": {"type": ["string", "null"], "enum": [*REASONS, None]}})
    reading = {"anyOf": [obj({"number": deepcopy(witness), "raw_unit": {"type": ["string", "null"]},
        "bound": {"type": "string", "enum": ["point", "lt", "le", "gt", "ge"]}}), {"type": "null"}]}
    operand = obj({"role": {"type": "string", "enum": list(ROLES)},
        "meanings": obj({field: deepcopy(meaning) for field in LITERAL_FIELDS}),
        "qualification": interpretation(QUALIFICATIONS), "reading": deepcopy(reading),
        "reported_uncertainty": obj({"kind": interpretation(SPREAD_KINDS), "sampling_basis": interpretation(SAMPLING),
            "statement": deepcopy(meaning), "reading": deepcopy(reading)}),
        "measurement_key": {"type": ["string", "null"]}, "physical_observation_key": {"type": ["string", "null"]}})
    uncertainty = obj({"value": {"type": "null"}, "status": {"type": "string", "const": "unavailable"},
        "reason": {"type": "string", "const": "full_joint_covariance_propagation_not_implemented"},
        "input_state": {"type": "string", "const": "joint_source_error_covariance_not_selected"},
        "source_spreads_are_not_full_joint_uncertainty": {"type": "boolean", "const": True}})
    return {"type": "array", "items": obj({"sheet_ref": ref("source"), "evidence_source_ref": ref("source"),
        "component": {"type": "string", "enum": list(COMPONENTS)}, "value": deepcopy(nullable_number),
        "unit": {"type": ["string", "null"], "enum": ["mg/mL", "kDa", "nM", "dimensionless", None]},
        "status": {"type": "string", "enum": ["point", "bounded", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "origin": {"type": "string", "enum": ["reported", "synthetic", "derived"]}, "approximate": {"type": "boolean"},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": list(CONDITIONS)}},
        "reported_domain": domain, "exact_domain": exact_domain,
        "evaluation_scope": {"type": "string", "const": "active_site_titration_amount"},
        "experiment": deepcopy(meaning), "intended_change": deepcopy(meaning), "other_changes": {"type": "array", "items": deepcopy(meaning)},
        "interpretations": obj({field: interpretation(values) for field, values in INTERPRETATIONS.items()}),
        "operands": {"type": "array", "minItems": 1, "maxItems": 4, "items": operand}, "fraction_uncertainty": uncertainty,
        "rate_application_status": {"type": "string", "enum": ["not_applied_already_active_normalized", "not_applied_requires_same_rate_context",
            "not_applied_no_rate_selected", "not_applied_normalization_unknown", "not_applied_normalization_conflicting"]}}), "x-source": NAMESPACE}

