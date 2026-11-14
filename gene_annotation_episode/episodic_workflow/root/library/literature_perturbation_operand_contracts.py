"""Original typed perturbation operand return declarations."""
from gene_annotation_episode.domain import REF, obj
from .literature_assay_grading import operand_schema

VERSION = "perturbation_operand_return_v1"
NAMESPACE = "literature_perturbation_operand_cells"
REQUESTED = "requested_perturbation_operand_components"
ENDPOINTS = {"reference_endpoint": "W", "perturbed_endpoint": "K", "restored_endpoint": "R"}
EFFECTS = {**{name: "native_endpoint" for name in ENDPOINTS},
    "perturbation_difference": "endpoint_difference", "restoration_difference": "endpoint_difference"}
VARIANCES = {**{role + "_mean_variance": name for name, role in ENDPOINTS.items()},
    "perturbation_mean_variance": "perturbation_difference",
    "restoration_mean_variance": "restoration_difference"}
COMPONENTS = (*EFFECTS, *VARIANCES)


def cells_schema():
    from .literature_perturbation_return_contracts import perturbation_cells_schema
    from .literature_perturbation_summary_return_contracts import perturbation_summary_cells_schema
    source = {**REF, "x-reference-namespace": "source"}
    return {"type": "array", "x-source": NAMESPACE, "items": obj({
        "row_version": {"const": VERSION}, "sheet_ref": source,
        "component": {"enum": list(COMPONENTS)},
        "quantity_kind": {"enum": ["native_endpoint", "endpoint_difference"]},
        "variance_for": {"type": ["string", "null"], "enum": [None, *EFFECTS]},
        "cell": operand_schema(),
        "source_cell": {"anyOf": [perturbation_cells_schema()["items"],
                                    perturbation_summary_cells_schema()["items"]]},
    })}


