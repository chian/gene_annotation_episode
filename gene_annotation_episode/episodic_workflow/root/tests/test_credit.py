"""The root hypervolume credit over unbounded axis credits."""
import math

import pytest

from gene_annotation_episode.episodic_workflow.root.axes import AXIS_ROLES
from gene_annotation_episode.episodic_workflow.root.credit import (HYPERVOLUME_OFFSET, annotation_hypervolume)


def _weights(value=1.0):
    return {role: value for role in AXIS_ROLES}


def _credits(**changes):
    return {**{role: 0.0 for role in AXIS_ROLES}, **changes}


def test_offset_is_one_for_epsilon_one_half():
    assert HYPERVOLUME_OFFSET == 1.0


def test_no_credit_is_zero():
    assert annotation_hypervolume(_credits(), _weights()) == 0.0


def test_single_axis_gain_is_linear_with_unit_weight():
    assert annotation_hypervolume(_credits(gene_context_evidence=3.5), _weights()) == 3.5


def test_credits_above_one_are_neither_clamped_nor_rescaled():
    credits = _credits(sequence_homology_evidence=40.0, perturbation_evidence=1e6)
    weights = {**_weights(), 'perturbation_evidence': 0.5}
    expected = (1 + 40.0) * (1 + 1e6) ** 0.5 - 1
    assert math.isclose(annotation_hypervolume(credits, weights), expected, rel_tol=1e-12)


def test_weighted_product_over_all_nine_axes():
    credits = {role: float(index) for index, role in enumerate(AXIS_ROLES)}
    weights = {role: 0.1 * (index + 1) for index, role in enumerate(AXIS_ROLES)}
    expected = math.prod((1 + credits[role]) ** weights[role] for role in AXIS_ROLES) - 1
    assert math.isclose(annotation_hypervolume(credits, weights), expected, rel_tol=1e-12)


def test_missing_or_unknown_axis_raises():
    credits = _credits()
    del credits['sample_context_evidence']
    with pytest.raises(KeyError, match='missing=sample_context_evidence'):
        annotation_hypervolume(credits, _weights())
    with pytest.raises(KeyError, match='unknown=other_evidence'):
        annotation_hypervolume(_credits(other_evidence=1.0), _weights())


@pytest.mark.parametrize('credit', [-0.1, math.inf, math.nan, True, '1'])
def test_inadmissible_credit_raises(credit):
    with pytest.raises(ValueError):
        annotation_hypervolume(_credits(gene_context_evidence=credit), _weights())


@pytest.mark.parametrize('weight', [0.0, -1.0])
def test_non_positive_weight_raises(weight):
    with pytest.raises(ValueError, match='axis_weight_must_be_positive'):
        annotation_hypervolume(_credits(), {**_weights(), 'gene_context_evidence': weight})
