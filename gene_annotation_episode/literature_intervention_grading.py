"""A106 intervention assessment using the existing evidence-ratio calculation."""
from copy import deepcopy

from .domain import obj
from .literature_assay_grading import (
    COMPONENTS, ROLES, REQUIRED_ROLES, COMMON_CRITERIA, operand_schema,
    interpretation_schema, prediction_model_schema, assay_grading_cell_schema,
    grade_experimental_measurement,
)

INPUT_VERSION = "a106_intervention_grading_inputs_v1"
VERSION = "a106_intervention_grading_sheet_v1"
EVALUATION_SCOPE = "intervention_experimental_evidence"
QUANTITY_KINDS = ("native_endpoint", "endpoint_difference", "endpoint_ratio",
                  "log2_fold_change", "fitness_difference")
CRITERIA = (*COMMON_CRITERIA, "intervention_identity", "subject_correspondence",
            "contrast_definition", "prediction_independence")
CRITERION_QUESTIONS = {
    "measurement_identity": "Which actual molecule, strain, construct, endpoint, time, unit and measurement scale define the estimate?",
    "calibration_applicability": "Do measurement range, calibration, detection limits and normalization support this quantity?",
    "matrix_interference": "Do processing, library composition, mapping ambiguity, batch and measurement interference permit this comparison?",
    "background_alternatives": "Do the controls address background, polar effects, unintended changes and alternatives relevant to this assertion?",
    "attribution_supported": "Does changing the actual studied component support the claimed contribution at the measured endpoint's resolution?",
    "assertion_relevance": "Does the contrast distinguish the stated contribution from the explicit alternative, without assuming an untested mechanism?",
    "condition_scope": "Are conditions, timing, backgrounds and intended versus nuisance changes appropriate to the assertion?",
    "variance_correspondence": "Does the selected variance describe this exact estimate, scale, normalization and shared inputs?",
    "sampling_basis": "Are biological units, technical repeats, pairing and dependence represented correctly?",
    "intervention_identity": "Are the actual intervention, measured extent, reference and restoration arms, when present, established?",
    "subject_correspondence": "What source-supported correspondence connects the tested molecule and intervention to the supplied sequence?",
    "contrast_definition": "Are comparison direction, samples, reference, endpoint and normalization established from the experiment and analysis?",
    "prediction_independence": "Were the assertion and alternative predictions specified independently of the selected observed result?",
}


def intervention_grading_input_schema():
    interpretation = interpretation_schema()
    interpretation["properties"]["status"] = {"enum": ["supported", "unknown", "conflicting"]}
    interpretation["properties"]["support_refs"]["description"] = (
        "Received reference records with exact source anchors, such as experiment_ref. "
        "A document source_ref alone does not provide an anchored interpretation witness.")
    return obj({"version": {"const": INPUT_VERSION}, "assay_type": {"const": "intervention_response"},
        "assertion_ref": {"type": "string", "minLength": 1}, "quantity_kind": {"enum": list(QUANTITY_KINDS)},
        "quantities": obj({role: {"anyOf": [operand_schema(), {"type": "null"}]} for role in ROLES},
                          required=list(REQUIRED_ROLES)),
        "interpretations": obj({key: deepcopy(interpretation) for key in CRITERIA}, required=[]),
        "prediction_model": {"anyOf": [prediction_model_schema(), {"type": "null"}]}})


def intervention_grading_sheet_schema():
    inputs = intervention_grading_input_schema()["properties"]
    return obj({"version": {"const": VERSION}, "axis": {"const": "A106"},
        "evaluation_scope": {"const": EVALUATION_SCOPE},
        **{key: deepcopy(inputs[key]) for key in ("assay_type", "assertion_ref", "quantity_kind",
                                                 "interpretations", "prediction_model")},
        "cells": obj({name: assay_grading_cell_schema() for name in COMPONENTS}),
        "annotation_credit": {"type": "null"}})


def _units(kind, unit):
    if kind == "log2_fold_change":
        return unit == "log2_ratio"
    if kind == "endpoint_ratio":
        return unit in {"dimensionless", "fraction"}
    # Native units are authenticated by the readers. The grader requires the
    # predictions and variance to use that exact scale and explicit criteria.
    return kind in QUANTITY_KINDS and bool(unit.strip()) and unit not in {"unknown", "unreported", "probability"}


def grade_intervention(extraction):
    return grade_experimental_measurement(extraction,
        input_schema=intervention_grading_input_schema(), sheet_schema=intervention_grading_sheet_schema(),
        required_criteria=lambda *_: (list(CRITERIA), set()), quantity_unit_supported=_units,
        version=VERSION, axis="A106", evaluation_scope=EVALUATION_SCOPE)
