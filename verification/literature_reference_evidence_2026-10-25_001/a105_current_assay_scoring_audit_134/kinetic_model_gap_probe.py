"""Synthetic arithmetic and current callable-contract probe; no paper or Store."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.literature_kinetic_calculations import (
    INPUT_VERSION, MODEL_VERSION, PARAMETER_UNITS, COMPONENTS,
    kinetic_operand_keys, populate_kinetic_contrast,
)
from gene_annotation_episode.literature_kinetic_inputs import kinetic_arguments_schema
from gene_annotation_episode.literature_kinetic_storage import (
    COMPONENTS as EXPOSED_COMPONENTS, MODEL_CAPABILITY,
)


def operand(value, role):
    return {
        "parameter_kind": "catalytic_efficiency",
        "unit": PARAMETER_UNITS["catalytic_efficiency"], "value": value,
        "status": "point", "relation": "eq", "approximate": False,
        "origin": "synthetic", "measurement_id": "synthetic-token-" + role,
        "physical_measurement_id": "synthetic-fit-" + role,
        "subject": {"organism": "synthetic organism", "genotype": None,
            "molecule": "synthetic molecule", "construct": "synthetic construct"},
        "context": {"substrate": "synthetic substrate-" + role,
            "preparation": "synthetic preparation", "experiment": "synthetic experiment",
            "experimental_system": "synthetic purified system",
            "conditions": "synthetic common conditions", "endpoint": "synthetic product rate",
            "normalization": "synthetic fitted efficiency"},
        "uncertainty": {"statistic": "unreported", "magnitude": None,
            "interval": None, "confidence_level": None, "count": None,
            "repetition_basis": "unspecified", "estimate_basis": "unknown"},
        "source": {"source_ref": "synthetic-source", "artifact_ref": "synthetic-artifact",
            "representation": "synthetic", "start": 10 if role == "numerator" else 30,
            "end": 15 if role == "numerator" else 35}, "unavailable_reason": None,
    }


inputs = {"version": INPUT_VERSION, "numerator": operand(12, "numerator"),
    "denominator": operand(3, "denominator"),
    "subject_relationship": "same_molecule_and_construct",
    "parameter_definition_relationship": "same", "substrate_arrangement": "separate_assays",
    "comparison_scope": "common_conditions", "nonintended_conditions_relationship": "matched"}
keys = kinetic_operand_keys(inputs)
model = {"version": MODEL_VERSION, "measurement_order": ["numerator", "denominator"],
    "measurement_keys": [keys["numerator"], keys["denominator"]],
    "covariance": [[0.09, 0.02], [0.02, 0.16]], "variance_status": "known",
    "observation_model": "known_normal_log_parameters",
    "log_basis": "natural_log_canonical_parameter", "origin": "synthetic",
    "source": {"source_ref": "synthetic-covariance", "artifact_ref": "synthetic-covariance-artifact",
        "representation": "synthetic", "start": 0, "end": 20}}
before = deepcopy((inputs, model))
native = populate_kinetic_contrast(inputs)
known = populate_kinetic_contrast(inputs, model)
estimated_model = deepcopy(model)
estimated_model["variance_status"] = "estimated"
estimated = populate_kinetic_contrast(inputs, estimated_model)
assert (inputs, model) == before
assert known["cells"]["parameter_difference"]["value"] == 9
assert known["cells"]["parameter_ratio"]["value"] == 4
assert abs(known["cells"]["log_contrast_variance"]["value"] - 0.21) < 1e-15
assert estimated["cells"]["log_contrast_variance"]["value"] is not None
assert estimated["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "known_log_covariance_required"
unexposed = [name for name in COMPONENTS if name not in EXPOSED_COMPONENTS]
assert len(unexposed) == 4
schema = kinetic_arguments_schema()
assert not any("model" in key or "covariance" in key for key in schema["properties"])
result = {
    "kind": "constructed engineering evidence, not published findings or an actual-model run",
    "native_callable_model_reader_capability": MODEL_CAPABILITY,
    "current_selected_argument_names": sorted(schema["properties"]),
    "current_typed_component_names": list(EXPOSED_COMPONENTS),
    "pure_calculator_components_not_exposed_by_native_path": unexposed,
    "inputs": inputs, "model": model,
    "without_model": native["cells"], "with_known_model": known["cells"],
    "with_estimated_covariance": estimated["cells"],
    "limits": ["This confirms arithmetic and the callable contract, not paper availability of covariance.",
        "The declared log-normal model and covariance are synthetic conditions, not inferred facts.",
        "No assay reliability probability or independent replication follows from this transform.",
        "Connecting these four cells does not complete A105 scientific validity or assay coverage."],
}
directory = Path(__file__).resolve().parent
(directory / "KINETIC_MODEL_GAP_PROBE_001.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"exposed": list(EXPOSED_COMPONENTS), "unexposed": unexposed,
    "known_model_cells": {name: {"value": known["cells"][name]["value"],
        "unavailable_reason": known["cells"][name]["unavailable_reason"]} for name in COMPONENTS},
    "estimated_model_evidence_reason": estimated["cells"]["source_profile_log_ratio"]["unavailable_reason"]}, indent=2))
