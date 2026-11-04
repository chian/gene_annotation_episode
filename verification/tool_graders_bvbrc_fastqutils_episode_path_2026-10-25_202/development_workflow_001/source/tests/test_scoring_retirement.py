"""Rejected categorical scores cannot reappear through implicit entry points."""
import json
import math

import pytest

from gene_annotation_episode.credit import (
    AXES, AnnotationScoringUnavailable, CreditPolicy, HypervolumeParameters,
    project_credit, softened_hypervolume, unavailable_annotation_score,
)
from gene_annotation_episode.default_scientific_binding import bind_default_science
from gene_annotation_episode.investigation_policy import create_policy
from gene_annotation_episode.investigation_progress import ScientificFindingProgress
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


def default_binding(tmp_path, **overrides):
    values = dict(run_dir=tmp_path/'run', resume=False, provider_config=None,
        credit_policy=None, initial_known_record_refs=None, project_child_credit=None,
        project_annotation_score=None, binding_definitions=None)
    values.update(overrides)
    return bind_default_science(None, **values)


def test_default_does_not_bind_absence_as_zero_or_change_progress(tmp_path):
    binding = default_binding(tmp_path)
    assert type(binding['project_credit']) is ScientificFindingProgress
    assert binding['project_child_credit'] is binding['project_credit']
    assert binding['project_annotation_score'] is None
    assert 'annotation_score' not in binding['binding_definitions']
    assert not (tmp_path/'run').exists()


@pytest.mark.parametrize('overrides', [
    {'credit_policy': {}}, {'provider_config': {'credit': {'scale': 100}}},
    {'provider_config': {'credit': {'applicability_weights': {'transfer': .6}}}},
])
def test_old_policy_is_rejected_before_starting_or_recording_new_work(tmp_path, overrides):
    with pytest.raises(ValueError, match='categorical_annotation_policy_retired'):
        default_binding(tmp_path, **overrides)
    assert not (tmp_path/'run').exists()


def test_custom_numeric_annotation_channel_is_not_replaced(tmp_path):
    def explicit_scorer(*args, **kwargs):
        raise AssertionError('binding must not execute a supplied scorer')
    definition = {'annotation_score': {'kind': 'synthetic_test_numerical_component'}}
    binding = default_binding(tmp_path, project_annotation_score=explicit_scorer,
        binding_definitions=definition)
    assert binding['project_annotation_score'] is explicit_scorer
    assert binding['binding_definitions']['annotation_score'] == definition['annotation_score']


def test_case_policy_requires_progress_and_has_no_implicit_annotation_policy():
    parameters = {'scientific_child': 'received_findings',
        'scientific_progress': {'finding_unit': 7, 'initial_known_record_refs': [], 'loss_preview_size': 5},
        'operational': {'registry_ref': 'fixture', 'handoff_unit': 1, 'acquired_record_unit': 1},
        'monitoring': {'information_unit': 1},
        'controller': {'cost': .001, 'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}}
    policy = create_policy(parameters)
    assert policy.project_annotation_score is None and policy.annotation_score_definition is None
    assert type(policy.project_task_credit) is ScientificFindingProgress
    assert policy.project_task_credit is policy.project_scientific_child_credit
    assert policy.task_credit_definition['policy']['finding_unit'] == 7
    with pytest.raises(ValueError, match='categorical_annotation_policy_retired'):
        create_policy({**parameters, 'scientific': {}})


def test_no_observation_kind_is_mapped_to_a_rejected_axis():
    for projector, reason in ((None, 'annotation_score_unbound'),
                              (lambda *_args: 0, 'unsupported_projector')):
        view = annotation_policy_routes(projector, None,
            observation_kinds=['alignment', 'assay_report', 'structure_match'])
        assert view['status'] == 'unavailable' and view['reason'] == reason
        assert view['policy'] is None
        assert all(row['axis'] is None and row['status'] == 'unavailable' for row in view['routes'])
