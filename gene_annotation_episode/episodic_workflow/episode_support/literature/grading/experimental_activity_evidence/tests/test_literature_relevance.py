"""Relevance (what was asked) and target match (who was measured), one branch each. The real case: an ultracentrifugation
(auc) experiment on PopZ alone, no partner, no interaction stated, no measured effect, against the claim 'PopZ binds ParB'
(owner, 2026-11-21: "Use target and relevance. It does make sense you need both")."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_relevance import relevance
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import on_row
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_target import target_match

CLAIM = {'predicate': 'binds', 'subject_id': 'popz', 'partner_id': 'parb'}


def record(target='popz', partner=None, statement=None, effect_measured=False, experiment_type='auc'):
    return {'experiment_type': experiment_type, 'target_id': target, 'partner_id': partner, 'statement': statement, 'effect_measured': effect_measured}


def test_popz_alone_with_nothing_measured_is_irrelevant_to_popz_binds_parb():
    for statement in ('interaction_not_stated', None):
        assert relevance(record(statement=statement), CLAIM) == {'relevance': 'irrelevant', 'reasons': ['no_partner_in_experiment']}
    assert target_match(record(), CLAIM, None)['target_match'] == 'same'      # the right protein: only the question was not asked


def test_the_same_record_with_a_measured_effect_or_a_detected_interaction_is_unresolved():
    assert relevance(record(effect_measured=True), CLAIM) == {'relevance': 'unresolved', 'reasons': ['partner_not_stated']}
    assert relevance(record(statement='interaction_detected'), CLAIM) == {'relevance': 'unresolved', 'reasons': ['partner_not_stated']}
    assert relevance(record(statement='interaction_not_detected'), CLAIM) == {'relevance': 'unresolved', 'reasons': ['partner_not_stated']}


def test_the_partner_decides_when_the_record_names_one():
    assert relevance(record(partner='chpt'), CLAIM) == {'relevance': 'irrelevant', 'reasons': ['other_partner']}
    assert relevance(record(partner='ParB'), CLAIM) == {'relevance': 'relevant', 'reasons': ['partner_agrees']}


def test_the_symmetric_partner_route_is_relevant_and_the_same_target():
    swapped = record(target='parb', partner='popz')
    assert relevance(swapped, CLAIM) == {'relevance': 'relevant', 'reasons': ['partner_route']}
    assert target_match(swapped, CLAIM, None) == {'target_match': 'same', 'reasons': ['partner_route']}


def test_a_claim_that_names_no_partner_makes_any_experiment_of_a_fitting_type_relevant():
    assert relevance(record(), {**CLAIM, 'partner_id': None}) == {'relevance': 'relevant', 'reasons': ['claim_names_no_partner']}


def test_a_type_whose_class_cannot_test_the_predicate_is_irrelevant():
    claim = {'predicate': 'catalyzes', 'subject_id': 'popz', 'partner_id': None}
    assert relevance(record(partner='parb'), claim) == {'relevance': 'irrelevant', 'reasons': ['experiment_type_cannot_test_predicate']}


def test_the_target_match_branches():
    assert target_match(record(target=None), CLAIM, None) == {'target_match': 'not_stated', 'reasons': ['target_not_stated']}
    assert target_match(record(target='chpt'), CLAIM, None) == {'target_match': 'different', 'reasons': ['target_differs_from_subject']}
    assert target_match(record(), CLAIM, None) == {'target_match': 'same', 'reasons': ['target_names_agree']}
    assert target_match(record(target='chpt'), CLAIM, 1.0) == {'target_match': 'same', 'reasons': ['target_sequence_identical']}
    assert target_match(record(), CLAIM, 0.5) == {'target_match': 'related', 'reasons': ['target_sequence_related']}


def test_a_partner_that_conflicts_no_longer_changes_the_target_match():
    assert target_match(record(partner='chpt'), CLAIM, None)['target_match'] == 'same'


def test_the_record_must_stay_inside_its_vocabulary():
    with pytest.raises(ValueError):
        relevance(record(statement='maybe'), CLAIM)
    with pytest.raises(ValueError):
        relevance(record(effect_measured=1), CLAIM)
    with pytest.raises(ValueError):
        relevance(record(experiment_type='not_a_type'), CLAIM)


def test_on_row_needs_both():
    assert on_row({'target_match': 'same', 'relevance': 'relevant'}) and on_row({'target_match': 'related', 'relevance': 'unresolved'})
    assert not on_row({'target_match': 'same', 'relevance': 'irrelevant'})
    assert not on_row({'target_match': 'different', 'relevance': 'relevant'})
    assert not on_row({'target_match': 'not_stated', 'relevance': 'relevant'})
