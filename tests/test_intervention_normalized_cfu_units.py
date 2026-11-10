"""Preserve initial-OD normalization through A106 measurement and score custody.

The calculations use engineered inputs. They are not predictions or a numerical
positive result for the carbon-starvation study that motivated this unit.
"""
import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from test_literature_perturbation_source import (
    covariance_arguments, extract, summary_grading_parent_return,
)


NORMALIZED = "CFU_per_initial_OD_per_mL"


@pytest.mark.parametrize("endpoint,covariance,prediction,canonical,expected", [
    (NORMALIZED, NORMALIZED + "_squared", NORMALIZED, NORMALIZED, 40),
    ("CFU/iOD/mL", "(CFU/iOD/mL)^2", "CFU/iOD/ml", NORMALIZED, 40),
    ("c.f.u./iOD/mL", "(c.f.u./iOD/mL)^2", "c.f.u./iOD/ml", NORMALIZED, 40),
    ("CFU/iOD/mL", "CFU^2/iOD^2/mL^2", "CFU/mL", NORMALIZED, None),
    ("CFU/mL", "(CFU/mL)^2", "CFU/iOD/mL", "CFU_per_mL", None),
])
def test_initial_od_normalization_survives_summary_grading_and_parent_return(
        tmp_path, endpoint, covariance, prediction, canonical, expected):
    summary_grading_parent_return(tmp_path, endpoint, covariance, prediction,
        canonical_unit=canonical, expected=expected)


@pytest.mark.parametrize("unit,error", [
    ("CFU/iOD/mL^2", "unsupported_perturbation_source_unit"),
    ("c.f.u./iOD/mL^2", "unsupported_perturbation_source_unit"),
    ("(CFU/mL)^2", "covariance_endpoint_unit_mismatch"),
])
def test_normalized_covariance_retains_the_whole_endpoint_unit(unit, error):
    args, raw = covariance_arguments(endpoint_unit="CFU/iOD/mL", unit=unit)
    with pytest.raises(ExperimentalContractError, match=error):
        extract(args, raw)


@pytest.mark.parametrize("unit", ["CFU/OD/mL", "c.f.u./OD/mL"])
def test_unspecified_od_does_not_become_initial_od_normalization(unit):
    args, raw = covariance_arguments(endpoint_unit=unit, unit=f"({unit})^2")
    with pytest.raises(ExperimentalContractError, match="unsupported_perturbation_source_unit"):
        extract(args, raw)
