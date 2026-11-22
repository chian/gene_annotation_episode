"""SOP step 8 offline: a spectro_direct leaf record goes through the page's own path (group_leaf_records, finalize_grader, page_update) for the claim
'<enzyme> catalyzes <reaction>' (partner null) and for the claim of a named substrate. The real-model version of this check is in the page's tests."""
import asyncio

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_target import (
    SUBJECT_UNIDENTIFIED_STANDING, identified_closeness)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_identity import finalize_grader, group_leaf_records
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_page_update import page_update
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    LEAF_RECORD_IDENTITY, QUALITATIVE_LOG_RATIO, SUPPORT_FACTORS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spectro_direct_cases import real_record, sparse_record, synthetic_record


def leaf(record, target, partner=None):
    identity = {name: None for name in LEAF_RECORD_IDENTITY}
    identity.update({'experiment_type': 'spectro_direct', 'target_id': target, 'partner_id': partner})
    spans = {ref: {'locator': f'bytes {10 * index}-{10 * index + 8} of the source', 'quote': span['quote']} for index, (ref, span) in enumerate(record['spans'].items())}
    return {**record, **identity, 'spans': spans, 'span_start': 0, 'span_end': 100, 'unavailable_reasons': {}, 'identity_provenance': {}}


def resolver(resolution='database_id', match_count=1):
    """A stand-in for literature_subject_resolution.resolve_subject, passed as the argument page_update takes. A name with several
    matches lists every candidate (the first is the record the resolver itself names)."""
    def resolve_subject(*, name, database_id, database, organism):
        if resolution == 'unresolved':
            return {'record_ref': None, 'sequence_ref': None, 'resolution': 'unresolved', 'match_count': 0, 'provider': None}
        candidates = [{'record_ref': f'record_{index}_of_{name}', 'sequence_ref': f'sequence_{index}_of_{name}', 'provider': 'uniprot'} for index in range(match_count)]
        if match_count == 1:
            candidates = [{'record_ref': 'record_of_' + name, 'sequence_ref': 'sequence_of_' + name, 'provider': 'uniprot'}]
        return {**candidates[0], 'resolution': resolution, 'match_count': match_count, 'provider': 'uniprot', 'candidates': candidates}
    return resolve_subject


def closeness_of(value):
    """A stand-in for literature_subject_closeness.subject_closeness (a coroutine function): the closeness is ``value``, or
    ``value[subject_record_ref]`` when a mapping gives one closeness for each candidate record."""
    async def subject_closeness(*, subject_record_ref, target_record_ref):
        assert target_record_ref == 'target_record'
        held = value[subject_record_ref] if isinstance(value, dict) else value
        return {'closeness': held, 'identity': held, 'query_coverage': 1.0, 'target_coverage': 1.0, 'comparison_ref': 'comparison_of_' + subject_record_ref}
    return subject_closeness


def run(record, claim, resolve=None, closeness=1.0, name='thdf', partner='fad'):
    leaves = [leaf(record, name, partner)]
    graders = [finalize_grader(grader) for grader in group_leaf_records(leaves)]
    items = [{'grader': grader, 'member_records': leaves} for grader in graders]
    return asyncio.run(page_update(None, items, {'hypothesis_1': claim}, {'hypothesis_1': 'target_record'}, resolve or resolver(), closeness_of(closeness)))


def test_a_stated_turnover_bears_directly_and_supports_by_its_graded_strength():
    update = run(real_record(), {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': None})
    (state,) = update['sheet_state'].values()
    (member,) = state['member_results']
    assert member['sheet'] == 'activity_rate' and member['experiment_type'] == 'spectro_direct' and member['target_match'] == 'same' and member['relevance'] == 'relevant'
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
    assert not other['sheet_state']      # relevance irrelevant (other_partner): no row
    same = run(real_record(), {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': 'FAD'})
    member = next(iter(same['sheet_state'].values()))['member_results'][0]
    assert member['target_match'] == 'same' and member['relevance'] == 'relevant'


def test_an_experiment_that_names_no_partner_and_measured_nothing_is_irrelevant_to_a_claim_that_names_one_and_stays_off_every_row():
    # sparse_record states no effect and no statement: like the ultracentrifugation of PopZ alone against 'PopZ binds ParB'
    claim = {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': 'FAD'}
    update = run(sparse_record(), claim, partner=None)
    assert not update['sheet_state']


def test_an_experiment_that_measured_an_effect_but_names_no_partner_is_unresolved_and_enters_the_row():
    claim = {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': 'FAD'}
    member = only_result(run(real_record(), claim, partner=None))[1]
    assert member['target_match'] == 'same' and member['relevance'] == 'unresolved' and member['direction'] == 'supports'


def test_a_claim_about_another_enzyme_does_not_bear_when_the_assayed_protein_is_not_identified():
    assert not run(real_record(), {'predicate': 'catalyzes', 'subject_id': 'BorF', 'partner_id': None}, resolve=resolver('unresolved'))['sheet_state']


CLAIM = {'predicate': 'catalyzes', 'subject_id': 'ThdF', 'partner_id': None}


def only_result(update):
    (state,) = update['sheet_state'].values()
    (member,) = state['member_results']
    return state['row'], member


def test_the_exact_sequence_is_direct_at_full_standing_and_carries_its_identification():
    row, member = only_result(run(real_record(), CLAIM))
    assert member['target_match'] == 'same' and member['relevance'] == 'relevant' and member['subject_resolution'] == 'database_id' and member['subject_match_count'] == 1
    assert member['subject_record_ref'] == 'record_of_thdf' and member['subject_sequence_ref'] == 'sequence_of_thdf'
    assert member['subject_closeness'] == 1.0 and member['comparison_ref'] == 'comparison_of_record_of_thdf'
    assert identified_closeness(member) == 1.0 and row['identified_closeness'] == 1.0 and row['comparison_ref'] == 'comparison_of_record_of_thdf'


def test_a_protein_of_another_name_whose_sequence_is_the_targets_bears_directly():
    update = run(real_record(), {**CLAIM, 'subject_id': 'BorF'}, name='thdf')
    _, member = only_result(update)
    assert member['target_match'] == 'same' and member['relevance'] == 'relevant' and member['target_id'] == 'borf'


def test_the_score_and_the_credit_scale_smoothly_with_the_closeness():
    full = run(real_record(), CLAIM, closeness=1.0)
    scores, credits = [], []
    for closeness in (0.0, 0.25, 0.5, 0.75, 0.9):
        update = run(real_record(), CLAIM, closeness=closeness)
        row, member = only_result(update)
        assert member['target_match'] == 'related' and member['relevance'] == 'relevant' and member['direction'] == 'supports'
        scores.append(row['support'])
        credits.append(update['credit']['hypothesis_1'])
        standing = SUBJECT_UNIDENTIFIED_STANDING + (1 - SUBJECT_UNIDENTIFIED_STANDING) * closeness
        assert row['support'] == pytest.approx(only_result(full)[0]['support'] * standing)
        assert credits[-1] == pytest.approx(full['credit']['hypothesis_1'] * standing)
    assert scores == sorted(scores) and len(set(scores)) == len(scores) and credits == sorted(credits)
    assert scores[-1] < only_result(full)[0]['support']


def test_the_closest_of_several_matches_carries_the_result_and_their_number_lowers_nothing():
    # Four candidates of closeness 0.2, 0.7, 0.4, 0.1: the closest (0.7) is kept, so the standing is that of 0.7 alone,
    # S + (1 - S) * 0.7, exactly as for a name with one match of closeness 0.7; the count of 4 divides nothing.
    closeness = {f'record_{index}_of_thdf': value for index, value in enumerate((0.2, 0.7, 0.4, 0.1))}
    four = only_result(run(real_record(), CLAIM, resolve=resolver('name_ambiguous', 4), closeness=closeness))
    one = only_result(run(real_record(), CLAIM, resolve=resolver('name_ambiguous', 1), closeness=0.7))
    assert four[1]['subject_match_count'] == 4 and four[1]['subject_closeness'] == 0.7
    assert four[0]['identified_closeness'] == pytest.approx(SUBJECT_UNIDENTIFIED_STANDING + (1 - SUBJECT_UNIDENTIFIED_STANDING) * 0.7)
    assert four[0]['identified_closeness'] == pytest.approx(one[0]['identified_closeness'])
    assert four[0]['support'] == pytest.approx(one[0]['support'])


def test_an_unresolved_subject_stands_at_the_bottom_of_the_scale_and_still_counts():
    update = run(real_record(), CLAIM, resolve=resolver('unresolved'))
    row, member = only_result(update)
    assert member['target_match'] == 'same' and member['relevance'] == 'relevant' and member['subject_resolution'] == 'unresolved' and member['subject_closeness'] is None
    assert member['subject_record_ref'] is None and member['comparison_ref'] is None
    assert row['identified_closeness'] == SUBJECT_UNIDENTIFIED_STANDING
    full = run(real_record(), CLAIM)
    assert update['credit']['hypothesis_1'] == pytest.approx(full['credit']['hypothesis_1'] * SUBJECT_UNIDENTIFIED_STANDING)
    assert 0 < row['support'] == pytest.approx(only_result(full)[0]['support'] * SUBJECT_UNIDENTIFIED_STANDING)


def test_an_ambiguous_name_keeps_the_closest_candidate_and_its_comparison():
    closeness = {f'record_{index}_of_thdf': value for index, value in enumerate((0.2, 0.7, 0.4, 0.1))}
    _, member = only_result(run(real_record(), CLAIM, resolve=resolver('name_ambiguous', 4), closeness=closeness))
    assert member['subject_closeness'] == 0.7 and member['subject_match_count'] == 4
    assert member['subject_record_ref'] == 'record_1_of_thdf' and member['subject_sequence_ref'] == 'sequence_1_of_thdf'
    assert member['comparison_ref'] == 'comparison_of_record_1_of_thdf'


def test_a_resolved_subject_of_closeness_zero_stands_where_an_unresolved_one_does():
    assert only_result(run(real_record(), CLAIM, closeness=0.0))[0]['identified_closeness'] == SUBJECT_UNIDENTIFIED_STANDING
