"""Original structure return schema and pure saved-extraction projections."""
from copy import deepcopy
from gene_annotation_episode.domain import obj
from .literature_structure_calculations import COMPONENTS, CONDITIONAL_CODES, REASONS
from .literature_structure_input_contracts import structure_population_schema

PROVIDER = "literature.experimental.structure"
FORMULA_CODES = {name: "structure_" + name + "_v1" for name in COMPONENTS}
BINDINGS = {
    "assayed_subject_ref": ("molecule", "reference"),
    "construct_ref": ("construct", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "partner_ref": ("partner", "reference"),
    "experimental_system_ref": ("experimental_system", "context"),
    "condition_ref": ("condition", "context"),
}
SOURCE_KINDS = ("primary_source", "retained_extraction", "graph_extraction", "synthetic_fixture")
VALIDATION_BINDINGS = ("matching_entry_revision", "entry_mismatch", "revision_mismatch",
                       "binding_unreported", "not_supplied")
_FIXED_METADATA = {
    "evaluation_scope": "conditional_deposited_model_geometry",
    "bound_kind": "conditional_arithmetic_outer",
    "unconditional_uncertainty": "unreported",
    "occupancy_basis": "conditioned_selected_model",
    "comparability_basis": "single_state_no_causal_comparison",
    "isolation_basis": "conditioned_atom_assignments",
    "local_validation_granularity": "residue",
    "transform_basis": "identity_coordinates_only",
}


def _metadata(extraction):
    return {**_FIXED_METADATA,
        "validation_binding": extraction["calculation_inputs"]["validation_binding"],
        "operand_source_kind": extraction["source_kind"],
        "model_number": extraction["model_number"],
        "geometry_definition": [{
            "endpoint_a": deepcopy(member["endpoint_a"]["selector"]),
            "endpoint_b": deepcopy(member["endpoint_b"]["selector"]),
            "positive_max_A": member["positive_max_A"],
            "incompatible_min_A": member["incompatible_min_A"],
        } for member in extraction["native_geometry"]],
        "local_validation_definition": [deepcopy(member["selector"])
            for member in extraction["native_local"]]}


def _direct_references(args):
    return list(dict.fromkeys([args["source_ref"], args["coordinate_source_ref"],
        *([args["validation_source_ref"]] if args["validation_source_ref"] else []),
        *(args["literals"][literal]["source_ref"] for literal, _ in BINDINGS.values()
          if args["literals"][literal] is not None)]))


def structure_cells_schema():
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    inputs = structure_population_schema()["properties"]
    properties = {"sheet_ref": dict(source), "evidence_source_ref": dict(source),
        **{field: {**source, "type": ["string", "null"]} for field in (
            "coordinate_source_ref", "validation_source_ref")},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        **{field: {"type": ["number", "null"], "minimum": -1, "maximum": 1}
            for field in ("value", "lower", "upper")},
        "unit": {"type": "string", "enum": ["dimensionless"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "origin": {"type": "string", "enum": ["proposed"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONAL_CODES)}},
        "validation_binding": {"type": "string", "enum": list(VALIDATION_BINDINGS)},
        "operand_source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "model_number": deepcopy(inputs["model_number"]),
        "geometry_definition": deepcopy(inputs["geometry_panel"]),
        "local_validation_definition": deepcopy(inputs["local_panel"]),
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_structure_cells"}


