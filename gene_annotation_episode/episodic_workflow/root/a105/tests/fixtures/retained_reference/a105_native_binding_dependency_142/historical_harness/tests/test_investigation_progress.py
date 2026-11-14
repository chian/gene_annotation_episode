"""Explicit synthetic finding units; no production policy selected here."""
from copy import deepcopy

import pytest

from gene_annotation_episode.investigation_progress import FindingProgressPolicy, project_finding_progress
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.credit import CreditPolicy
from test_scientific_findings import finding, quoted_observation, target_question
from test_scientific_hypervolume_runtime import assessment, annotation, evidence
from test_context_credit import source_fixture


def put_finding(store, hypothesis, observed, subject, *, value='positive', qualification='none',
                replaces=(), revision=0, withdraw=False):
    payload = assessment(hypothesis, observed['id'], 'incomparable', revision=revision)
    payload['relation'] = 'does_not_discriminate'
    payload['investigation_finding'] = finding(subject, value=value, qualification=qualification,
                                                replaces=replaces)
    if withdraw:
        payload['investigation_finding'].update(status='withdrawn', withdrawal_reason='source_misread')
    return store.put('assessment', payload, origin='reasoning')


def test_actual_findings_deduplicate_correct_and_withdraw_without_opinion_weight(tmp_path):
    # Seven is an explicit fixture unit, not an approved production weight.
    policy = FindingProgressPolicy(finding_unit=7)
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        scope = {'subject_refs': [target]}
        subject_a, obs_a = quoted_observation(store, accession='first', start=0, end=17)
        subject_b, obs_b = quoted_observation(store, accession='again', start=18, end=67)
        a = put_finding(store, hypothesis, obs_a, subject_a)
        b = put_finding(store, hypothesis, obs_b, subject_b)
        options = {'known_assessment_refs': [a['id'], b['id']], 'details_limit': 20}
        shared_but_not_received = project_finding_progress(store, scope, policy, known_assessment_refs=[])
        assert shared_but_not_received['credit'] == 0
        first = project_finding_progress(store, scope, policy, **options)
        assert first['credit'] == 7 and first['retained_finding_count'] == 1
        assert {item['known_assessment_ref'] for item in first['source_contributions']} == {a['id'], b['id']}
        assert a['applicability'] == b['applicability'] == 'incomparable'

        corrected = put_finding(store, hypothesis, obs_b, subject_b, value='negative',
            replaces=[a['id']], revision=b['revision'])
        loss_before_receipt = project_finding_progress(store, scope, policy,
            known_assessment_refs=[a['id']], details_limit=20)
        assert loss_before_receipt['credit'] == 0
        assert loss_before_receipt['inactive_dependencies'][0] == {
            'assessment_ref': a['id'], 'reason': 'finding_replaced',
            'replacement_refs': [corrected['id']],
            'replacement_provenance': 'one_current_correction_witness'}
        options['known_assessment_refs'].append(corrected['id'])
        second = project_finding_progress(store, scope, policy, **options)
        assert second['credit'] == 7 and second['retained_finding_count'] == 1
        reasons = {item['assessment_ref']: item['reason'] for item in second['inactive_dependencies']}
        assert reasons == {a['id']: 'finding_replaced', b['id']: 'not_current_assessment_revision'}
        assert second['source_contributions'][0]['known_assessment_ref'] == corrected['id']
        assert store.get(a['id']) == a

        withdrawn = put_finding(store, hypothesis, obs_b, subject_b, value='negative',
            replaces=[a['id']], revision=corrected['revision'], withdraw=True)
        options['known_assessment_refs'].append(withdrawn['id'])
        last = project_finding_progress(store, scope, policy, **options)
        assert last['credit'] == 0 and last['credit']-second['credit'] == -7
        assert next(item for item in last['inactive_dependencies'] if item['assessment_ref'] == withdrawn['id'])[
            'withdrawal_reason'] == 'source_misread'
        assert last['policy'] == policy.as_record()


def test_typed_qualification_adds_information_and_page_reads_do_not_change_score(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        scope = {'subject_refs': [target]}
        subject_a, obs_a = quoted_observation(store, accession='first', start=0, end=17)
        subject_b, obs_b = quoted_observation(store, accession='again', start=18, end=67)
        original = put_finding(store, hypothesis, obs_a, subject_a)
        qualification = put_finding(store, hypothesis, obs_b, subject_b,
            qualification='measurement_does_not_establish_claim')
        known = [original['id'], qualification['id']]
        policy = FindingProgressPolicy(3)
        summary = project_finding_progress(store, scope, policy, known_assessment_refs=known)
        assert summary['credit'] == 6 and summary['retained_finding_count'] == 2
        for offset in (0, 1, 2):
            page = project_finding_progress(store, scope, policy, known_assessment_refs=known,
                details_limit=1, details_offset=offset)
            assert page['credit'] == 6
            assert len(page['source_contributions']) == (1 if offset < 2 else 0)
        assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='runtime_observations'").fetchone()[0] == 0


def test_rootless_source_questions_are_not_additional_annotation_targets(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, _ = target_question(store)
        subject, observed = quoted_observation(store, accession='source', start=0, end=17)
        source_question = store.put('hypothesis', {'subject_refs': [subject],
            'predicate': 'growth_capability', 'value': {'type': 'enum', 'value': 'positive'},
            'context_refs': []}, origin='reasoning')['id']
        saved = put_finding(store, source_question, observed, subject)
        result = project_finding_progress(store, {'subject_refs': [target]}, FindingProgressPolicy(2),
            known_assessment_refs=[saved['id']], details_limit=10)
        assert result['credit'] == 0
        assert result['inactive_dependencies'][0]['reason'] == 'finding_target_outside_scope'
        assert len(store.targets()) == 1


def test_correction_link_cannot_retire_a_finding_outside_assigned_region(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        whole = evidence(store, target, 'alignment')
        previous = put_finding(store, hypothesis, whole, target)
        local = evidence(store, target, 'mechanism')
        proposed = assessment(hypothesis, local['id'], 'scope_limited')
        proposed['target_footprint'] = [{'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}]
        proposed['investigation_finding'] = finding(target, replaces=[previous['id']])
        scope = {'subject_refs': [target], 'segments': proposed['target_footprint']}
        with pytest.raises(ContractError, match='finding_replacement_outside_scope'):
            store.put('assessment', proposed, origin='reasoning', scope=scope)
        assert store.current_assessments()[0] == previous


def test_correction_chain_cannot_restore_an_unauthorized_historical_retirement(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        full_scope = {'subject_refs': [target]}
        whole = evidence(store, target, 'alignment')
        a = put_finding(store, hypothesis, whole, target)
        local = evidence(store, target, 'mechanism')
        footprint = [{'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}]
        b_payload = assessment(hypothesis, local['id'], 'scope_limited')
        b_payload['target_footprint'] = footprint
        b_payload['investigation_finding'] = finding(target, replaces=[a['id']])
        b1 = store.put('assessment', b_payload, origin='reasoning', scope=full_scope)
        # The current revision explicitly no longer declares that retirement.
        b_payload['expected_revision'] = b1['revision']
        b_payload['investigation_finding']['replaces_refs'] = []
        b2 = store.put('assessment', b_payload, origin='reasoning', scope=full_scope)
        c_observation = evidence(store, target, 'comparison')
        c_payload = assessment(hypothesis, c_observation['id'], 'scope_limited')
        c_payload['target_footprint'] = footprint
        c_payload['investigation_finding'] = finding(target, replaces=[b1['id']])
        with pytest.raises(ContractError, match='finding_replacement_outside_scope') as error:
            store.put('assessment', c_payload, origin='reasoning',
                scope={'subject_refs': [target], 'segments': footprint})
        assert error.value.detail['reference'] == a['id']
        assert set(store.current_assessment_subset([a['id'], b1['id'], b2['id']])) == {a['id'], b2['id']}


def test_opinion_only_revision_keeps_known_canonical_information_without_new_receipt(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        previous = put_finding(store, hypothesis, observed, target)
        scope, policy = {'subject_refs': [target]}, FindingProgressPolicy(4)
        first = project_finding_progress(store, scope, policy, known_assessment_refs=[previous['id']])
        changed = assessment(hypothesis, observed['id'], 'scope_limited', revision=previous['revision'])
        changed['relation'] = 'mixed'
        changed['investigation_finding'] = deepcopy(previous['investigation_finding'])
        current = store.put('assessment', changed, origin='reasoning')
        later = project_finding_progress(store, scope, policy,
            known_assessment_refs=[previous['id']], details_limit=1)
        assert first['credit'] == later['credit'] == 4
        assert later['source_contributions'][0]['known_assessment_ref'] == previous['id']
        assert later['source_contributions'][0]['current_assessment_ref'] == current['id']
        received = project_finding_progress(store, scope, policy,
            known_assessment_refs=[previous['id'], current['id']])
        assert received['credit']-later['credit'] == 0


def test_observed_local_extent_does_not_require_redundant_target_footprint(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        data = {key: observed[key] for key in ('subject_refs', 'source_subject_refs', 'kind',
            'source_ref', 'measurements', 'dependencies', 'anchor')}
        data['measurements'] = [{'name': name,
            'value': {'type': 'number', 'value': value, 'unit_ref': None}}
            for name, value in [('query_start', 0), ('query_end', 5)]]
        native = store.put('observation', data, origin='tool')
        scope = {'subject_refs': [target], 'segments': [
            {'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}]}
        payload = assessment(hypothesis, native['id'], 'direct')
        payload['investigation_finding'] = finding(target)
        saved = store.put('assessment', payload, origin='reasoning', scope=scope)
        result = project_finding_progress(store, scope, FindingProgressPolicy(2),
            known_assessment_refs=[saved['id']])
        assert result['credit'] == 2


def test_owned_context_withdrawal_preserves_authoritative_correction_links(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, _ = target_question(store)
        scope = {'subject_refs': [target]}
        source = source_fixture(store, 'synthetic-context-correction')
        sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic sample',
            'source_ref': source['id'], 'attributes': [], 'related_refs': [], 'anchor': None}, origin='external')['id']
        hypothesis = store.put('hypothesis', {'subject_refs': [sample], 'predicate': 'growth_capability',
            'value': {'type': 'enum', 'value': 'positive'}, 'context_refs': []}, origin='reasoning')['id']
        def observation(kind):
            return store.put('observation', {'subject_refs': [sample], 'source_subject_refs': [sample],
                'kind': kind, 'source_ref': source['id'], 'measurements': [], 'dependencies': [],
                'anchor': None}, origin='external')['id']
        def payload(observed, revision=0, replaces=()):
            value = assessment(hypothesis, observed, 'direct', revision=revision)
            value.update(extent_basis='context_allocation', context_account_scope=scope, context_scope=scope)
            value['investigation_finding'] = finding(sample, replaces=replaces)
            return value
        b = store.put('assessment', payload(observation('growth_assay')), origin='reasoning', scope=scope)
        a_payload = payload(observation('assay_report'), replaces=[b['id']])
        a = store.put('assessment', a_payload, origin='reasoning', scope=scope)
        a_payload['expected_revision'] = a['revision']
        a_payload['context_scope'] = {'subject_refs': []}
        a_payload['investigation_finding'].update(status='withdrawn', withdrawal_reason='source_misread')
        withdrawn = store.put('assessment', a_payload, origin='reasoning', scope=scope)
        result = project_finding_progress(store, scope, FindingProgressPolicy(2),
            known_assessment_refs=[b['id'], withdrawn['id']], details_limit=10)
        assert result['credit'] == 0
        assert next(row for row in result['inactive_dependencies'] if row['assessment_ref'] == b['id'])[
            'reason'] == 'finding_replaced'


def test_context_account_domain_does_not_expand_or_block_actual_local_allocation(tmp_path):
    # Two tiny artificial inputs exercise only scope mechanics, not a second
    # gene investigation or a model-selected multi-gene annotation workload.
    path = tmp_path/'synthetic-scope.faa'
    path.write_text('>A\nMARGKKIGYS\n>B\nMARGKKIGYT\n')
    with Store(tmp_path/'workspace') as store:
        a, b = store.create_problem(path, molecule='protein')['subject_refs']
        domain, local_scope = {'subject_refs': [a, b]}, {'subject_refs': [a]}
        source = source_fixture(store, 'synthetic-broad-domain')
        sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic sample',
            'source_ref': source['id'], 'attributes': [], 'related_refs': [], 'anchor': None}, origin='external')['id']
        observed = store.put('observation', {'subject_refs': [sample], 'source_subject_refs': [sample],
            'kind': 'growth_assay', 'source_ref': source['id'], 'measurements': [],
            'dependencies': [], 'anchor': None}, origin='external')['id']
        hypothesis = store.put('hypothesis', {'subject_refs': [sample], 'predicate': 'growth_capability',
            'value': {'type': 'enum', 'value': 'positive'}, 'context_refs': []}, origin='reasoning')['id']
        payload = assessment(hypothesis, observed, 'direct')
        payload.update(extent_basis='context_allocation', context_account_scope=domain, context_scope=local_scope)
        payload['investigation_finding'] = finding(sample)
        saved = store.put('assessment', payload, origin='reasoning', scope=local_scope)
        assert project_finding_progress(store, local_scope, FindingProgressPolicy(3),
            known_assessment_refs=[saved['id']])['credit'] == 3
        assert project_finding_progress(store, {'subject_refs': [b]}, FindingProgressPolicy(3),
            known_assessment_refs=[saved['id']])['credit'] == 0


def test_attribution_narrowing_is_not_new_information_in_an_overlapping_child_scope(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        previous = put_finding(store, hypothesis, observed, target)
        footprint = [{'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}]
        scope, policy = {'subject_refs': [target], 'segments': footprint}, FindingProgressPolicy(5)
        before = project_finding_progress(store, scope, policy, known_assessment_refs=[previous['id']])
        payload = assessment(hypothesis, observed['id'], 'incomparable', revision=previous['revision'])
        payload['target_footprint'] = footprint
        payload['investigation_finding'] = deepcopy(previous['investigation_finding'])
        current = store.put('assessment', payload, origin='reasoning')
        after = project_finding_progress(store, scope, policy,
            known_assessment_refs=[previous['id'], current['id']])
        assert before['credit'] == after['credit'] == 5


def test_unreceived_same_lineage_withdrawal_has_exact_current_loss_provenance(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        observed = evidence(store, target, 'alignment')
        previous = put_finding(store, hypothesis, observed, target)
        withdrawn = put_finding(store, hypothesis, observed, target,
            revision=previous['revision'], withdraw=True)
        result = project_finding_progress(store, {'subject_refs': [target]}, FindingProgressPolicy(2),
            known_assessment_refs=[previous['id']], details_limit=10)
        assert result['credit'] == 0
        assert result['inactive_dependencies'] == [{'assessment_ref': previous['id'],
            'reason': 'scientific_finding_withdrawn', 'current_assessment_ref': withdrawn['id'],
            'withdrawal_reason': 'source_misread'}]


def test_annotation_and_information_progress_share_replacement_validity(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, hypothesis = target_question(store)
        scope = {'subject_refs': [target]}
        observed = evidence(store, target, 'alignment')
        payload = assessment(hypothesis, observed['id'], 'direct')
        payload['investigation_finding'] = finding(target)
        a = store.put('assessment', payload, origin='reasoning', scope=scope)
        store.put('annotation', annotation(target, hypothesis, [a['id']], 0), origin='reasoning')
        support = AnnotationSupportScore(CreditPolicy())
        before = support.read_details(store, scope, details_limit=10, details_offset=0)
        assert before['credit'] > 0
        b = put_finding(store, hypothesis, evidence(store, target, 'comparison'), target,
            value='negative', replaces=[a['id']])
        # Annotation still names A. Its now-retired operand cannot remain live
        # merely because its raw observation lineage has a current revision.
        after = support.read_details(store, scope, details_limit=10, details_offset=0)
        assert after['credit'] == 0
        assert after['detail_pages']['state_basis_sha256'] != before['detail_pages']['state_basis_sha256']
        assert after['inactive_dependencies'][0]['reason'] == 'scientific_finding_replaced'
        assert after['inactive_dependencies'][0]['replacement_refs'] == [b['id']]
        progress = project_finding_progress(store, scope, FindingProgressPolicy(2),
            known_assessment_refs=[a['id']], details_limit=10)
        assert progress['credit'] == 0
        assert progress['inactive_dependencies'][0]['replacement_refs'] == [b['id']]
        assert project_finding_progress(store, scope, FindingProgressPolicy(2),
            known_assessment_refs=[a['id'], b['id']])['credit'] == 2
        assert store.get(a['id']) == a


@pytest.mark.parametrize('unit', [0, -1, True, float('nan'), float('inf')])
def test_finding_units_are_explicit_and_finite(unit):
    with pytest.raises(ValueError, match='explicit_positive_finding_unit_required'):
        FindingProgressPolicy(unit)
