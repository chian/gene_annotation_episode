"""SOP step 8 offline: a spectro_direct leaf record goes through the page's own path (group_leaf_records, finalize_grader, page_update) for the claim
'<enzyme> catalyzes <reaction>' (partner null) and for the claim of a named substrate. The real-model version of this check is in the page's tests."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_identity import finalize_grader, group_leaf_records
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_page_update import page_update
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    LEAF_RECORD_IDENTITY, QUALITATIVE_LOG_RATIO, SUPPORT_FACTORS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spectro_direct_cases import real_record, synthetic_record


def leaf(record, target, partner=None):
    identity = {name: None for name in LEAF_RECORD_IDENTITY}
    identity.update({'experiment_type': 'spectro_direct', 'target_id': target, 'partner_id': partner})
    spans = {ref: {'locator': f'bytes {10 * index}-{10 * index + 8} of the source', 'quote': span['quote']} for index, (ref, span) in enumerate(record['spans'].items())}
    return {**record, **identity, 'spans': spans, 'span_start': 0, 'span_end': 100, 'unavailable_reasons': {}, 'identity_provenance': {}}


def run(record, claim):
    leaves = [leaf(record, 'thdf', 'fad')]
    graders = [finalize_grader(grader) for grader in group_leaf_records(leaves)]
    items = [{'grader': grader, 'member_records': leaves} for grader in graders]
    return page_update(None, items, {'hypothesis_1': claim})


def test_a_stated_turnover_bears_directly_and_supports_by_its_graded_strength():
    update = run(real_record(), {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': None})
    (state,) = update['sheet_state'].values()
    (member,) = state['member_results']
    assert member['sheet'] == 'activity_rate' and member['experiment_type'] == 'spectro_direct' and member['bearing'] == 'direct'
    assert member['direction'] == 'supports' and member['measured_effect'] == 0.21 and member['effect_unit'] == 's^-1'
    p = (-0.6777807052660807 + 2) / 4      # log10(0.21) against the turnover anchors 1e-2 .. 1e2
    assert member['log_ratio'] == pytest.approx(QUALITATIVE_LOG_RATIO['spectro_direct'] * (3 * p ** 2 - 2 * p ** 3), rel=1e-6)      # no variance: the spread kind is not stated
    assert member['effect_support'] == SUPPORT_FACTORS['direct'] and 0 < member['weight'] <= 1
    assert update['features'] and update['features'][0]['target_id'] == 'thdf' and update['features'][0]['experiments'] == 1
    assert 0 < update['credit']['hypothesis_1'] <= 1


def test_a_synthetic_record_with_every_criterion_decided_has_a_near_full_weight_and_a_variance_in_the_strength():
    update = run(synthetic_record(), {'predicate': 'catalyzes', 'subject_id': 'thdf', 'partner_id': None})
    (member,) = next(iter(update['sheet_state'].values()))['member_results']
    assert member['measured_effect'] == 5.0e5 and member['effect_unit'] == 'M^-1s^-1' and member['effect_variance'] == pytest.approx(4.0e4 ** 2)
    assert member['direction'] == 'supports' and 0 < member['log_ratio'] <= QUALITATIVE_LOG_RATIO['spectro_direct']
    assert member['weight'] == pytest.approx(0.99)      # nine criteria at degree 1 and the substrate series at 0.9 (its lowest concentration, 0.25 x Km, is just above the researched 0.2 x Km), the mean over the ten


def test_a_claim_naming_another_substrate_does_not_bear_and_a_claim_naming_the_stated_substrate_does():
    other = run(real_record(), {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': 'NADH'})
    assert not other['sheet_state']      # partner_contradicts_claim: different_subject, no row
    same = run(real_record(), {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': 'FAD'})
    assert next(iter(same['sheet_state'].values()))['member_results'][0]['bearing'] == 'direct'


def test_a_claim_about_another_enzyme_does_not_bear():
    assert not run(real_record(), {'predicate': 'catalyzes', 'subject_id': 'BorF', 'partner_id': None})['sheet_state']
