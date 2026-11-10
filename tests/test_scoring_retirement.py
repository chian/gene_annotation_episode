"""Rejected categorical scores cannot reappear through implicit entry points."""
import math

import pytest

from gene_annotation_episode.credit import (
    AXES, AnnotationScoringUnavailable, CreditPolicy, HypervolumeParameters,
    project_credit, softened_hypervolume, unavailable_annotation_score,
)
from gene_annotation_episode.scientific_credit import (
    AnnotationSupportScore, ScientificEvidenceCredit, ScientificInvestigationCredit,
)
from gene_annotation_episode.scientific_support_metadata import annotation_policy_routes


@pytest.mark.parametrize('constructor', [CreditPolicy, AnnotationSupportScore,
    ScientificEvidenceCredit, ScientificInvestigationCredit])
def test_retired_bindings_cannot_construct_a_categorical_scorer(constructor):
    with pytest.raises(AnnotationScoringUnavailable, match='categorical_annotation_scoring_retired'):
        constructor()


def test_stale_projection_never_reads_or_changes_scientific_state():
    class NoAccess:
        def __getattr__(self, name):
            pytest.fail('retired projection accessed scientific state: '+name)

    with pytest.raises(AnnotationScoringUnavailable):
        project_credit(NoAccess())
    assert AXES == ()
    assert unavailable_annotation_score() == {
        'status': 'unavailable', 'annotation_score': None,
        'reason': 'numerical_evidence_component_scorer_not_bound'}


def test_hypervolume_preserves_formula_without_default_axes_or_missing_as_zero():
    operands = {'component_one': .8, 'component_two': .4}
    parameters = HypervolumeParameters((('component_one', 1), ('component_two', 2)), .25)
    baseline = .25**3
    expected = ((.25+.75*.8)*(.25+.75*.4)**2-baseline)/(1-baseline)
    assert softened_hypervolume(operands, parameters) == pytest.approx(expected)
    assert softened_hypervolume(dict.fromkeys(operands, 0), parameters) == 0
    assert softened_hypervolume(dict.fromkeys(operands, 1), parameters) == 1
    with pytest.raises(AnnotationScoringUnavailable):
        softened_hypervolume(operands)
    for invalid in ({'component_one': .8}, {**operands, 'component_two': None},
                    {**operands, 'component_two': math.nan}, {**operands, 'component_two': True}):
        with pytest.raises(ValueError):
            softened_hypervolume(invalid, parameters)


def test_no_observation_kind_is_mapped_to_a_rejected_axis():
    for projector, reason in ((None, 'annotation_score_unbound'),
                              (lambda *_args: 0, 'unsupported_projector')):
        view = annotation_policy_routes(projector, None,
            observation_kinds=['alignment', 'assay_report', 'structure_match'])
        assert view['status'] == 'unavailable' and view['reason'] == reason
        assert view['policy'] is None
        assert all(row['axis'] is None and row['status'] == 'unavailable' for row in view['routes'])
