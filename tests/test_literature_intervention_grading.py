"""Synthetic A106 cases verify shared likelihood semantics, not live scoring."""
from copy import deepcopy
import math

import pytest

from gene_annotation_episode.literature_assay_grading import ROLES, grade_assay
from gene_annotation_episode.literature_intervention_grading import CRITERIA, INPUT_VERSION, grade_intervention
from test_literature_assay_grading import fixture, operand


def intervention():
    data = dict(version=INPUT_VERSION, assay_type="intervention_response", assertion_ref="hypothesis_synthetic",
        quantity_kind="log2_fold_change", quantities=dict.fromkeys(ROLES),
        interpretations={name: dict(status="supported", support_refs=["reference_synthetic_" + name]) for name in CRITERIA},
        prediction_model=dict(kind="fixed_predictions_estimated_normal", variance_interpretation="estimated",
                              support_refs=["reference_synthetic_model"]))
    for name, value, unit in (("effect", -2., "log2_ratio"), ("effect_variance", .25, "log2_ratio_squared"),
            ("assertion_prediction", -2., "log2_ratio"), ("alternative_prediction", 0., "log2_ratio")):
        data["quantities"][name] = operand(value, unit, name)
    return data


def test_signed_screen_scale_can_supply_supported_comparison_without_restoration():
    data = intervention()
    original = deepcopy(data)
    sheet = grade_intervention(data)
    score = sheet["cells"]["source_log_evidence_ratio"]
    assert score["value"] == 8 and score["status"] == "conditional"
    assert sheet["axis"] == "A106" and sheet["annotation_credit"] is None
    assert data == original
    assert sheet["cells"]["recovery_deviation"]["value"] is None


@pytest.mark.parametrize("missing", ["effect_variance", "assertion_prediction", "alternative_prediction"])
def test_native_effect_survives_missing_required_score_operand(missing):
    data = intervention()
    data["quantities"][missing] = None
    sheet = grade_intervention(data)
    assert sheet["cells"]["measured_effect"]["value"] == -2
    assert sheet["cells"]["source_log_evidence_ratio"]["value"] is None


@pytest.mark.parametrize("criterion", ["subject_correspondence", "intervention_identity", "contrast_definition", "prediction_independence"])
def test_missing_intervention_support_prevents_functional_evidence(criterion):
    data = intervention()
    data["interpretations"][criterion] = dict(status="unknown", support_refs=[])
    cell = grade_intervention(data)["cells"]["source_log_evidence_ratio"]
    assert cell["value"] is None and criterion + "_unknown" in cell["reasons"]


def test_conflicting_effect_produces_negative_evidence_without_clipping():
    data = intervention()
    data["quantities"]["effect"]["value"] = 1.
    assert grade_intervention(data)["cells"]["source_log_evidence_ratio"]["value"] == -16


def test_same_calculation_and_censoring_model_as_existing_a105():
    a105 = fixture("protein_signal")
    a106 = intervention()
    a106["quantities"] = deepcopy(a105["quantities"])
    a106["quantity_kind"] = "endpoint_ratio"
    a106["prediction_model"] = deepcopy(a105["prediction_model"])
    for data in (a105, a106):
        data["quantities"]["effect"].update(value=None, status="bounded",
            bound=dict(relation="lt", lower=None, upper=.7))
    first = grade_assay(a105)["cells"]["source_log_evidence_ratio"]
    second = grade_intervention(a106)["cells"]["source_log_evidence_ratio"]
    assert math.isfinite(first["value"]) and first["value"] == second["value"]
    assert first["formula"] == second["formula"]


def test_prediction_cannot_reuse_the_observed_effect_identity():
    data = intervention()
    data["quantities"]["assertion_prediction"]["measurement_keys"] = data["quantities"]["effect"]["measurement_keys"]
    cell = grade_intervention(data)["cells"]["source_log_evidence_ratio"]
    assert cell["value"] is None and "prediction_reuses_observed_measurement" in cell["reasons"]
