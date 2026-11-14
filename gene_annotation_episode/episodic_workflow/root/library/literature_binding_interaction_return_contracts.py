"""Original binding-family return contracts; no numerical or repository activation."""
from copy import deepcopy
from gene_annotation_episode.domain import obj

ROLES = ("reference_subject_reference_ligand", "reference_subject_test_ligand",
         "test_subject_reference_ligand", "test_subject_test_ligand")
CONTEXT_FIELDS = ("subject", "construct", "state", "preparation", "experiment",
                  "ligand", "tracer", "readout", "normalization", "conditions")
ID_FIELDS = CONTEXT_FIELDS + ("parameter_definition",)
RELATIONS = ("within_reference_subject", "within_test_subject",
             "ligand_correspondence", "parameter_definition", "separate_assays",
             "common_conditions")
UNCERTAINTY_PARTIAL_CODES = (
    "uncertainty_metadata_unresolved", "reported_uncertainty_magnitude_unknown",
    "confidence_interval_endpoints_incomplete", "confidence_level_unknown",
)
KINDS = ("ic50", "reported_hill_kd", "unknown", "conflicting")
STATISTICS = ("sd", "sem", "confidence_interval", "unspecified", "unreported", "unknown", "conflicting")
BASES = ("fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown", "conflicting")
REPETITIONS = ("biological_preparations", "technical_measurements", "assay_occasions", "unspecified", "unknown", "conflicting")
MEASUREMENT_STATUSES = ("not_selected", "parsed", "reported_unavailable", "ambiguous", "unreadable", "conflicting",
    "source_unavailable", "unsupported_expression", "unsupported_unit", "numerical_range", "unit_not_selected",
    "unit_ambiguous", "unit_unreadable", "unit_conflicting", "unit_source_unavailable")
SCALAR_STATUSES = ("not_selected", "parsed", "qualified", "ambiguous", "unreadable", "conflicting",
    "source_unavailable", "unsupported_literal", "unsupported_count_literal", "source_token_incomplete",
    "conflicting_qualification", "numerical_range")
UNCERTAINTY_REASONS = ("uncertainty_description_not_selected", "uncertainty_interval_unit_unavailable",
    "conflicting_interval_order", "uncertainty_interval_numeric_range", "confidence_level_out_of_range", "confidence_level_numeric_range",
    "conflicting_exact_minimum_count", "uncertainty_meaning_source_unavailable", "uncertainty_statistic_unknown",
    "uncertainty_statistic_conflicting", "uncertainty_basis_conflicting", "reported_spread_uncertainty_meaning_conflict",
    "interval_uncertainty_meaning_conflict", "uncertainty_on_unreported_parameter")
ROLE_UNAVAILABLE_REASONS = ("role_not_selected", "parameter_kind_source_unavailable", "parameter_kind_unknown",
    "parameter_kind_conflicting", "parameter_kind_mismatch", "conflicting_source_cell", "unresolved_source_cell_rereading",
    *("measurement_" + status for status in MEASUREMENT_STATUSES))
CALCULATION_INPUT_STATUSES = ("ready", "common_parameter_kind_unknown", "common_parameter_kind_conflicting",
    "common_parameter_kind_source_unavailable")
RAW_COMPONENTS = ("parameter_rr", "parameter_rt", "parameter_tr", "parameter_tt")
COMPONENTS = (*RAW_COMPONENTS, "reference_subject_ratio", "test_subject_ratio", "interaction_ratio", "log_interaction")
FORMULA_CODES = {name: "binding_interaction_" + name for name in COMPONENTS}
CALCULATION_REASONS = (
    *("missing_operand:" + r for r in ROLES), *("unreported_operand:" + r for r in ROLES),
    "reused_source_token", "reused_physical_fit", "ligand_roles_not_distinct", "subject_roles_not_distinct",
    "opposing_reported_limits", "numerical_representation_range", "common_conditions_claim_conflicts_with_canonical_ids",
    *(name + "_" + status for name in ("within_reference_subject", "within_test_subject", "ligand_correspondence",
        "parameter_definition", "separate_assays") for status in ("unknown", "conflicting")),
    *("canonical_" + name + "_" + status for name in ("subject", "construct", "state", "parameter_definition", "readout",
        "normalization", "ligand") for status in ("unknown", "conflicting")),
    *("common_conditions_" + status for status in ("unknown", "not_matched", "conflicting")),
)
UNAVAILABLE_REASONS = (*CALCULATION_REASONS, *CALCULATION_INPUT_STATUSES[1:],
    *("source_" + status for status in MEASUREMENT_STATUSES))


EVALUATION_SCOPE = "source_binding_discrimination_interaction"
MODEL_INPUT_STATUS = "not_supplied_by_native_operation"
MODEL_CAPABILITY = "unimplemented"
def binding_interaction_cells_schema():
    """Closed C4 parent return: finite meanings, actual refs, selected numbers."""
    def enum(values, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "enum": [*values, None] if nullable else list(values)}
    def ref(namespace="reference", nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    def array(value, unique=False):
        return {"type": "array", "items": value, **({"uniqueItems": True} if unique else {})}
    refs = array(ref(nullable=False), True)
    number, integer = {"type": ["number", "null"]}, {"type": ["integer", "null"]}
    literal_status = ("not_selected", "exact", "ambiguous", "unreadable", "conflicting", "source_unavailable")
    literal = obj({"status": enum(literal_status), "declared_status": enum(literal_status[1:-1], True), "candidate_refs": refs, "fragment_refs": refs})
    def interpreted(values):
        return obj({"value": enum(values), "status": enum(("interpreted", "source_unavailable", "not_selected")), "witness_refs": refs})
    region = {"type": ["array", "null"], "minItems": 4, "maxItems": 4, "items": {"type": "integer", "minimum": 0}}
    location = obj({"ref": ref(nullable=False), "source_ref": ref("source", False),
        "kind": enum(("utf8_span", "image_region", "unresolved")), "start": integer, "end": integer, "region": region})
    location_nullable = deepcopy(location)
    location_nullable["type"] = ["object", "null"]
    definition = obj({"status": enum(("known", "unknown", "conflicting", "source_unavailable", "not_selected")),
        "canonical_witness_ref": ref(), "witness_refs": refs, "canonical_witness_location": location_nullable})
    scalar = obj({"literal": literal, "status": enum(SCALAR_STATUSES), "relation": enum(("eq", "lt", "le", "gt", "ge"), True),
        "approximate": {"type": "boolean"}, "percent": {"type": "boolean"},
        "qualification_origin": enum(("selected_literal", "retained_text_context"), True)})
    measurement = obj({"value": number, "relation": enum(("eq", "lt", "le", "gt", "ge", "unreported")), "reported_spread": number})
    def nullable_object(schema):
        schema = deepcopy(schema)
        schema["type"] = ["object", "null"]
        return schema
    interval_values = {"type": ["array", "null"], "minItems": 2, "maxItems": 2, "items": number}
    canonical_uncertainty = nullable_object(obj({"statistic": enum(("sd", "sem", "confidence_interval", "unspecified", "unreported")),
        "basis": enum(("fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown")),
        "exact_count": integer, "minimum_count": integer, "repetition_basis": enum(("biological_preparations", "technical_measurements", "assay_occasions", "unspecified")),
        "interval": interval_values, "confidence_level": number}))
    values = obj({"delivery_status": enum(("requested", "not_requested")), "native": nullable_object(measurement), "canonical": nullable_object(measurement),
        "candidates": {"type": ["array", "null"], "items": obj({"witness_ref": ref(nullable=False), "native": nullable_object(measurement),
            "canonical": nullable_object(measurement), "canonical_unit": enum(("nM",), True)})}, "uncertainty": canonical_uncertainty,
        "interval_native": interval_values, "scalar_native": nullable_object(obj({k: number for k in ("confidence_level", "exact_count", "minimum_count")}))})
    interval = nullable_object(obj({"lower": scalar, "upper": scalar, "unit_relationship": interpreted(("same_as_parameter", "explicit_unit", "unknown", "conflicting")),
        "unit": literal, "canonical_status": enum(("parsed", "partial", "unit_unavailable", "conflicting", "numerical_range")), "canonical_unit": enum(("nM",), True)}))
    metadata = obj({"selection_status": enum(("selected", "not_selected")), "parameter_kind": interpreted(KINDS),
        "definitions": obj({k: definition for k in ID_FIELDS}), "physical_fit": definition, "source_cell_ref": ref(),
        "parse_status": enum(MEASUREMENT_STATUSES), "expression": literal, "unit": literal,
        "unavailable_reasons": array(enum(ROLE_UNAVAILABLE_REASONS), True), "numeric_locations": array(location), "values": values,
        "uncertainty": obj({"selection_status": enum(("selected", "not_selected")), "reported_spread_status": enum(("reported", "native_reported_unit_unavailable", "not_in_selected_expression", "unresolved")),
            "meanings": obj({"statistic": interpreted(STATISTICS), "basis": interpreted(BASES), "repetition_basis": interpreted(REPETITIONS)}),
            "interval": interval, "confidence_level": scalar, "exact_count": scalar, "minimum_count": scalar,
            "unavailable_reasons": array(enum(UNCERTAINTY_REASONS), True)})})
    return {"type": "array", "x-source": "literature_binding_interaction_cells", "items": obj({
        "sheet_ref": ref("source", False), "evidence_source_ref": ref("source", False), "component": enum(COMPONENTS),
        "value": number, "threshold": number, "relation": enum(("eq", "lt", "le", "gt", "ge", "unreported", "none")),
        "unit": enum(("nM", "dimensionless"), True), "status": enum(("populated", "reported_limit", "conflicting", "unavailable")),
        "origin": enum(("synthetic", "visual_transcription", "derived")), "unavailable_reason": enum(UNAVAILABLE_REASONS, True),
        "calculation_unavailable_reason": enum(CALCULATION_REASONS, True), "bound_kind": enum(("printed_limit", "reported_limit_arithmetic"), True),
        "formula_code": enum(FORMULA_CODES.values()), "evaluation_scope": enum((EVALUATION_SCOPE,)),
        "comparison_scope": enum(("reported_protocols", "common_conditions")), "common_parameter_kind": interpreted(KINDS),
        "calculation_input_status": enum(CALCULATION_INPUT_STATUSES), "model_input_status": enum((MODEL_INPUT_STATUS,)),
        "model_reader_capability": enum((MODEL_CAPABILITY,)), "relationships": obj({k: interpreted(("supported", "unknown", "conflicting") if k != "common_conditions"
            else ("matched", "not_matched", "unknown", "conflicting")) for k in RELATIONS}), "roles": obj({k: metadata for k in ROLES})})}


