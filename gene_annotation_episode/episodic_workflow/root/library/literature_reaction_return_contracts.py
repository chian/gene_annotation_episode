"""Original reaction return contracts and pure saved-value helpers."""
from copy import deepcopy
from gene_annotation_episode.domain import identity, obj
from .literature_reaction_calculations import COMPONENTS, CONDITIONAL_CODES, REASONS
from .literature_reaction_inputs import LITERAL_FIELDS
from .literature_reaction_meanings import (
    RECORD_VERSION as MEANINGS_RECORD_VERSION, NAMESPACE as MEANINGS_NAMESPACE,
    BASES, MODEL_FIELDS, RESOURCE_FIELDS, DEMAND_FIELDS,
    direct_references as meaning_direct_references,
)

PROVIDER = "literature.experimental.reaction"
FORMULA_CODES = {name: "reaction_" + name + "_v1" for name in COMPONENTS}
BINDINGS = {
    "assayed_subject_ref": ("molecule", "reference"),
    "construct_ref": ("construct", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "numerator_ref": ("numerator", "term"),
    "denominator_ref": ("denominator", "term"),
    "endpoint_ref": ("endpoint", "term"),
    "condition_ref": ("condition", "context"),
    "resource_context_ref": ("resource_context", "context"),
}
SOURCE_KINDS = ("primary_source", "retained_extraction", "graph_extraction", "synthetic_fixture")
LITERAL_REFERENCE_TYPES = {
    "molecule": "literature_result",  # An unsequenced source role, not an inferred protein or assay.
    "construct": "construct",
    "experiment": "assay",
}
_FIXED_METADATA = {
    "evaluation_scope": "reported_reference_reaction_constraints",
    "bound_kind": "logical_model_domain_not_confidence_interval",
    "measurement_corrections": "not_applied",
    "target_correspondence": "not_evaluated",
    "uncertainty_interpretation": "descriptive_not_confidence_interval",
}


def literal_reference_role(record):
    """Recover the producer's original role, including historical assay-typed subjects.

    The accession binds the selected literal field and its exact saved anchor.
    No label interpretation, source rereading or biological identity inference
    is involved. Caller-declared assays keep their existing authority.
    """
    if record.get("record_type") != "reference" or record.get("origin") != "tool":
        return None
    anchor = record.get("anchor")
    if not isinstance(anchor, dict):
        return None
    for role in LITERAL_REFERENCE_TYPES:
        if record.get("accession") == identity("reaction_literal", {"field": role, **anchor}):
            return role
    return None


def reaction_return_view_requirements():
    """Static contract metadata; no source lookup or scientific interpretation."""
    return {
        "required_sheet_versions": {
            "literature_reaction_cells": "literature_reaction_record_v2",
            "literature_reaction_semantic_cells": MEANINGS_RECORD_VERSION,
        },
        "detail": (
            "The numerical and semantic return views require different saved sheet versions. "
            "A legacy numerical sheet has no saved semantic bindings. Inspect the actual "
            "sheet's Source version and select its matching recorded-fact view. A valid "
            "numerical return may include an empty semantic companion; a lone empty wrong "
            "view is rejected. Redelivery changes the representation of existing saved "
            "facts and cannot create semantic bindings. Source-supported meanings require "
            "an a110_source_reaction_measurements_v2 dataset or an "
            "a110_source_reaction_selection_v1 calculation, rather than another population "
            "of the same a110_source_reaction_measurements_v1 dataset."
        ),
    }


def _metadata(extraction, sheet):
    ratio = extraction["calculation_inputs"]["ratio"]
    budget = extraction["calculation_inputs"]["budget"]
    details = sheet["ratio_details"]
    reported_sd = details["reported_sample_sd"]
    derived_sd = details["derived_sample_sd"]["value"]
    return {**_FIXED_METADATA,
        "operand_source_kind": extraction["arguments"]["source_kind"],
        "ratio_origin": ratio["origin"] if ratio is not None else None,
        "budget_origin": budget["origin"] if budget is not None else None,
        "independent_n": details["independent_n"],
        "reported_sample_sd": reported_sd,
        "derived_sample_sd": derived_sd,
        "ratio_uncertainty": "reported_sample_sd" if reported_sd is not None else
            "descriptive_sample_sd" if derived_sd is not None else "unreported",
        "ratio_mode": ratio["mode"] if ratio is not None else None,
        "ratio_kind": ratio["ratio_kind"] if ratio is not None else None,
        "ratio_unit": ratio["unit"] if ratio is not None else None,
        "claim_prediction": ratio["claim"] if ratio is not None else None,
        "alternative_predictions": [entry["prediction"] for entry in ratio["alternatives"]]
            if ratio is not None else [],
        "budget_basis": budget["basis"] if budget is not None else None,
        "budget_unit": budget["unit"] if budget is not None else None,
        "resources_complete": budget["resources_complete"] if budget is not None else None,
        "demand": budget["demand"] if budget is not None else None}


def _direct_references(args):
    """Fixed semantic order survives canonical JSON object-key reordering."""
    return list(dict.fromkeys([args["source_ref"],
        *([args["data_source_ref"]] if args["data_source_ref"] is not None else []),
        *(args["literals"][field]["source_ref"] for field in LITERAL_FIELDS
          if args["literals"][field] is not None),
        *(entry["source_ref"] for entry in args["interpretation_witnesses"])]))


def reaction_direct_references(extraction, direct):
    refs = meaning_direct_references(extraction, direct)
    if "native_evidence" in extraction:
        from .literature_reaction_native_inputs import native_direct_references
        refs.extend(native_direct_references(extraction["native_evidence"]))
    return list(dict.fromkeys(refs))


def reaction_cells_schema():
    """Closed scientific return: selected cells and their numeric model panel."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    nullable_number = {"type": ["number", "null"]}
    def nullable_enum(values):
        return {"type": ["string", "null"], "enum": [None, *values]}
    properties = {"sheet_ref": dict(source), "evidence_source_ref": dict(source),
        "data_source_ref": {**source, "type": ["string", "null"]},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": dict(nullable_number),
        "unit": {"type": "string", "enum": ["mol_per_mol", "signal_per_signal", "squared_ratio",
            "dimensionless", "umol", "uM", "umol_per_min", "uM_per_min", "unreported"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["reported", "graph_derived", "synthetic", "derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONAL_CODES)}},
        "ratio_mode": nullable_enum(["independent_units", "source_summary"]),
        "ratio_kind": nullable_enum(["product_pair", "formed_per_consumed", "formed_per_supplied", "signal_ratio"]),
        "ratio_unit": nullable_enum(["mol_per_mol", "signal_per_signal"]),
        "ratio_origin": nullable_enum(["reported", "graph_derived", "synthetic"]),
        "budget_origin": nullable_enum(["reported", "graph_derived", "synthetic"]),
        "independent_n": {"type": ["integer", "null"], "minimum": 1},
        "reported_sample_sd": {**nullable_number, "minimum": 0},
        "derived_sample_sd": {**nullable_number, "minimum": 0},
        "ratio_uncertainty": {"type": "string", "enum": ["reported_sample_sd",
            "descriptive_sample_sd", "unreported"]},
        "claim_prediction": dict(nullable_number),
        "alternative_predictions": {"type": "array", "items": dict(nullable_number)},
        "budget_basis": nullable_enum(["supplied_reagent_batch", "usable_batch", "usable_rate"]),
        "budget_unit": nullable_enum(["umol", "uM", "umol_per_min", "uM_per_min"]),
        "resources_complete": {"type": ["boolean", "null"]},
        "demand": {**nullable_number, "exclusiveMinimum": 0},
        "operand_source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_reaction_cells",
        "description": (
            "Numerical cells from literature_reaction_record_v2, including supported v1 "
            "measurement datasets. A literature_reaction_record_v3 sheet returns its "
            "numerical cells together with source-bound meanings through "
            "literature_reaction_semantic_cells instead. "
            + reaction_return_view_requirements()["detail"])}


def reaction_semantic_cells_schema():
    """Closed named scientific view of the same15 existing numerical cells."""
    schema = deepcopy(reaction_cells_schema())
    schema["x-source"] = MEANINGS_NAMESPACE
    schema["description"] = (
        "Numerical cells and saved source-bound meanings from literature_reaction_record_v3. "
        "A literature_reaction_record_v2 sheet does not provide this view. "
        + reaction_return_view_requirements()["detail"])
    properties = schema["items"]["properties"]
    def ref(kind, nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference",
                "x-reference-namespace": kind}
    def meaning(kind, fields, bases):
        return {kind + "_ref": ref("reference", False), "definition_reported": {"type": "boolean"},
            **{field + "_ref": ref(namespace) for field, namespace in fields.items() if field != "definition"},
            **{basis: {"type": "string", "enum": list(BASES)} for basis in bases}}
    model = obj({**meaning("model", MODEL_FIELDS, ("prediction_basis",)),
        "role": {"type": "string", "enum": ["claim", "alternative"]},
        "prediction": {"type": ["number", "null"]},
        "unit": {"type": "string", "enum": ["mol_per_mol", "signal_per_signal"]}})
    resource = obj({**meaning("resource", RESOURCE_FIELDS, ("supply_basis", "coefficient_basis")),
        "coefficient": {"type": "number", "exclusiveMinimum": 0},
        "coefficient_role": {"type": "string", "enum": ["resource_unit_per_demand_unit"]},
        "coefficient_demand_ref": ref("reference", False)})
    demand = obj({**meaning("demand", DEMAND_FIELDS, ("demand_basis",)),
        "value": {"type": ["number", "null"], "exclusiveMinimum": 0},
        "unit": {"type": "string", "enum": ["umol", "uM", "umol_per_min", "uM_per_min"]}})
    fields = {"model_definitions": {"type": "array", "items": model},
        "comparison_member_refs": {"type": "array", "uniqueItems": True, "items": ref("reference", False)},
        "comparison_reduction": {"type": "string", "enum": ["minimum_over_declared_alternatives"]},
        "resource_definitions": {"type": "array", "items": resource},
        "demand_definition": {**demand, "type": ["object", "null"]},
        "nominal_limiting_resource_refs": {"type": "array", "uniqueItems": True, "items": ref("reference", False)}}
    properties.update(fields)
    schema["items"]["required"].extend(fields)
    return schema


