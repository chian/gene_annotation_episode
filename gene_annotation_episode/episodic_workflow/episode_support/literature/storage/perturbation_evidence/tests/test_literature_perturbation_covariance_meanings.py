"""Constructed covariance meaning custody, without new statistical arithmetic, through the real runner."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.perturbation_evidence.tests.test_literature_perturbation_summary import extract, calculate
from .library_data import data_for
from .library_world import run_scenarios, world  # noqa: F401 - ``world`` is the fixture


@pytest.mark.parametrize('basis', [None, True, 1, 'probably_reported'])
def test_covariance_interpretation_basis_is_closed_and_never_inferred(basis):
    data = data_for(); data['covariances'][0]['interpretation_basis'] = basis
    with pytest.raises(ExperimentalContractError, match='unsupported_summary_meaning'):
        extract(data)


def test_optional_capture_does_not_change_any_numerical_cell_or_old_payload_shape():
    old = calculate(data_for(qualify=False))
    new = calculate(data_for())
    assert old['cells'] == new['cells']
    assert 'covariance_descriptors' not in old
    assert new['covariance_descriptors'][0]['interpretation_basis'] == 'source_reported'
    assert new['covariance_descriptors'][1]['interpretation_basis'] is None
    assert new['covariance_descriptors'][1]['selection'] == 'unreported'


@pytest.mark.parametrize('kind,basis', [('mean_covariance', 'source_reported'),
                                        ('uncorrelated', 'conditional_assumption'),
                                        ('paired_units', 'source_supported_inference')])
def test_same_numbers_keep_distinct_meanings_through_parent_receipt(world, kind, basis):
    outcome, = run_scenarios(world, 'meaning-' + kind, ('covariance_receipt', {'kind': kind, 'basis_name': basis}))
    assert outcome == {'kind': kind}


def test_only_component_relevant_pairs_cross_the_exact_original_form(world):
    outcome, = run_scenarios(world, 'pairs', ('covariance_pairs', {}))
    assert outcome == {'pairs': 3}


@pytest.mark.parametrize('unavailable', ['unknown_covariance', 'incompatible_estimator'])
def test_unknown_or_unavailable_estimator_is_not_presented_as_applied_covariance(world, unavailable):
    outcome, = run_scenarios(world, 'unavailable-' + unavailable, ('covariance_unavailable', {'unavailable': unavailable}))
    assert outcome == {'unavailable': unavailable}
