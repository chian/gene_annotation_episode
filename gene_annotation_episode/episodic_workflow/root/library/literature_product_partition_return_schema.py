from gene_annotation_episode.domain import obj

ROLES = ("a", "b")

MEANINGS = ("subject", "organism", "construct", "preparation", "compound", "endpoint",
            "condition", "stage", "time", "denominator", "measurement_basis", "measurement_identity")
RELATIONSHIPS = ("supported", "unknown", "conflicting")
RELATIONS = ("same_preparation", "same_endpoint", "shared_denominator")
BASES = ("amount_fraction", "signal_fraction", "unknown", "conflicting")
STAGES = ("equilibrium", "timepoint", "endpoint", "unknown", "conflicting")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
EVIDENCE_ROLES = ("composition", "identity_confirmation", "competing_contribution",
                  "preparation_change", "repetition_basis", "uncertainty")

COMPONENTS = ("partition_a_fraction", "partition_b_fraction", "selected_fraction_sum",
              "selected_closure_deviation", "partition_a_over_b")
REASONS = ("source_measurement_unavailable", "source_fraction_unit_unreported",
    "unsupported_source_fraction_unit", "censored_measurement", "basis_unknown", "basis_conflicting",
    "incompatible_fraction_bases", "same_preparation_unknown", "same_preparation_conflicting",
    "same_endpoint_unknown", "same_endpoint_conflicting", "shared_denominator_unknown",
    "shared_denominator_conflicting", "reused_source_observation", "zero_denominator_fraction",
    "numerical_model_range", "qualification_unknown", "qualification_conflicting")
CONDITIONS = ("source_reported_fraction_scale", "same_selected_preparation_and_endpoint",
              "shared_selected_denominator", "dependent_transforms_not_independent_evidence")

NAMESPACE = "literature_product_partition_cells"

def binding_references(value):
    result = []
    def visit(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if key.endswith("_ref") and child is not None: result.append(child)
                else: visit(child)
        elif isinstance(node, list):
            for child in node: visit(child)
    visit(value)
    return list(dict.fromkeys(result))



def product_partition_cells_schema():
    def reference(namespace, nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    def enum(values): return {"type": "string", "enum": list(values)}
    quantity = obj({"role": enum(ROLES), **{name + "_ref": reference("reference") for name in MEANINGS},
                    "meaning_status": obj({name: enum(("selected", "not_selected", "withheld_unrequested_numbers")) for name in MEANINGS}),
                    "basis": enum(BASES), "stage": enum(STAGES), "qualification": enum(QUALIFICATIONS)})
    return {"type": "array", "x-source": NAMESPACE, "items": obj({
        "sheet_ref": reference("source", False), "evidence_source_ref": reference("source", False),
        "experiment_ref": reference("reference"), "component": enum(COMPONENTS),
        "experiment_status": enum(("selected", "not_selected", "withheld_unrequested_numbers")),
        "value": {"type": ["number", "null"]}, "unit": enum(("fraction", "dimensionless")),
        "status": enum(("populated", "unavailable")), "origin": enum(("reported", "synthetic", "derived")),
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": enum(CONDITIONS)},
        "approximate": {"type": "boolean"}, "threshold": {"type": ["number", "null"]},
        "bound": enum(("none", "lt", "le", "gt", "ge")), "outside_reported_fraction_range": {"type": "boolean"},
        "quantities": {"type": "array", "maxItems": 2, "items": quantity},
        "relationships": obj({name: enum(RELATIONSHIPS) for name in RELATIONS}),
        "evidence": {"type": "array", "items": obj({"role": enum(EVIDENCE_ROLES),
            "witness_ref": reference("reference"), "availability": enum(("recorded", "withheld_unrequested_numbers"))})},
        "evaluation_scope": {"type": "string", "const": "reported_selected_product_partition"},
        "uncertainty_calculation": {"type": "string", "const": "not_implemented"}})}

