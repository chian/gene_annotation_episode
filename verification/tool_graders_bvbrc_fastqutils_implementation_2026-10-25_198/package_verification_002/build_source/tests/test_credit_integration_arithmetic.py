"""Synthetic Store regressions for integration, not new scientific weights."""
from copy import deepcopy

import pytest

from gene_annotation_episode.credit import (
    CreditPolicy, LEGACY_INTEGRATION, STABLE_INTEGRATION, project_credit,
)
from gene_annotation_episode.scientific_credit import (
    AnnotationSupportScore, ScientificEvidenceCredit, ScientificInvestigationCredit,
)
from gene_annotation_episode.state import Store
from gene_annotation_episode.domain import ContractError
from test_scientific_hypervolume_runtime import assessment, annotation, evidence
from test_context_credit import context_account, library_fixture, select_mask


def test_losing_local_accounts_cannot_change_unchanged_winning_values(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target, = store.create_problem(raw_sequence='ACG'*254, molecule='dna')['subject_refs']
        scope = {'subject_refs': [target]}
        hypothesis = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']
        saved = []
        for kind, applicability in [('alignment', 'direct'), ('assay_report', 'transfer')]:
            observation = evidence(store, target, kind)
            saved.append(store.put('assessment', assessment(hypothesis, observation['id'], applicability),
                                   origin='reasoning')['id'])
        winner = store.put('annotation', annotation(target, hypothesis, saved, 0), origin='reasoning')
        policy = CreditPolicy()
        options = {'include_interpretation_accounts': True,
                   'integration_arithmetic': STABLE_INTEGRATION}
        before = project_credit(store, scope, policy, **options)
        legacy = ScientificInvestigationCredit(policy)
        legacy_definition = deepcopy(legacy.as_record())
        assert 'integration_arithmetic' not in legacy_definition
        legacy_before = legacy(store, scope)
        # Positive but weaker local accounts insert many integration boundaries.
        # They never replace the existing winning account on any position.
        for index, (start, end) in enumerate([(1, 4), (17, 23), (111, 114),
                                             (419, 422), (701, 704)]):
            observed = evidence(store, target, 'comparison')
            observed_payload = {key: observed[key] for key in ('subject_refs', 'source_subject_refs',
                'kind', 'source_ref', 'measurements', 'dependencies', 'anchor')}
            observed_payload['measurements'] = [{'name': 'replicate',
                'value': {'type': 'number', 'value': index, 'unit_ref': None}}]
            observed = store.put('observation', observed_payload, origin='external')
            proposal = assessment(hypothesis, observed['id'], 'scope_limited')
            proposal['target_footprint'] = [
                {'target_ref': target, 'unit': 'nt', 'start': start, 'end': end}]
            narrowed = store.put('assessment', proposal, origin='reasoning')
            store.put('interpretation_account', annotation(target, hypothesis, [narrowed['id']], 0),
                origin='reasoning', scope=scope, account_owner=('synthetic_run', 'local_'+str(index)))
            after = project_credit(store, scope, policy, **options)
            assert after.credit == before.credit
            assert after.axis_components == before.axis_components
            assert after.targets == before.targets
            assert after.source_contributions == before.source_contributions
            assert {row['annotation_ref'] for row in after.source_contributions} == {winner['id']}
            summary = project_credit(store, scope, policy, details_limit=0, **options)
            page = project_credit(store, scope, policy, details_limit=1, **options)
            assert summary.credit == page.credit == before.credit
            assert summary.axis_components == page.axis_components == before.axis_components
            assert summary.as_record()['integration_arithmetic'] == STABLE_INTEGRATION
        # Existing adapters remain exactly the old arithmetic for saved runs.
        assert legacy.as_record() == legacy_definition
        explicit_legacy = project_credit(store, scope, policy, details_limit=0,
            include_interpretation_accounts=True, integration_arithmetic=LEGACY_INTEGRATION)
        assert legacy(store, scope).as_record() == explicit_legacy.as_record()
        assert legacy_before.credit > 0


def test_support_adapter_has_explicit_arithmetic_and_preserves_true_corrections(tmp_path):
    scorer = AnnotationSupportScore(CreditPolicy(epsilon=.37, scale=7))
    with Store(tmp_path/'workspace') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        observation = evidence(store, target, 'alignment')
        hypothesis = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']
        original = store.put('assessment', assessment(hypothesis, observation['id'], 'direct'), origin='reasoning')
        store.put('annotation', annotation(target, hypothesis, [original['id']], 0), origin='reasoning')
        before = scorer(store, scope)
        assert before.credit > 0
        assert before.as_record()['interpretation'] == scorer.as_record()['interpretation']
        details = scorer.read_details(store, scope, details_limit=10, details_offset=0)
        assert details['credit'] == before.credit
        assert details['axis_components'] == before.axis_components
        assert details['policy'] == scorer.as_record()['policy']
        assert details['integration_arithmetic'] == scorer.as_record()['integration_arithmetic'] == STABLE_INTEGRATION
        assert details['interpretation'] == 'annotation_support_not_investigation_progress'
        store.put('assessment', assessment(hypothesis, observation['id'], 'incomparable',
            revision=original['revision']), origin='reasoning')
        after = scorer(store, scope)
        assert after.credit == 0 and after.credit-before.credit < 0
        with pytest.raises(ContractError, match='unknown_or_empty_scope'):
            scorer(store, {'subject_refs': []})
        with pytest.raises(ValueError, match='differs_from_original_commission'):
            scorer(store, scope, assignment={'scope': {'subject_refs': [target], 'segments': [
                {'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}]}})
        # Legacy records retain their original shape and meaning.
        assert 'integration_arithmetic' not in ScientificEvidenceCredit(scorer.policy).as_record()
        assert 'integration_arithmetic' not in ScientificEvidenceCredit(scorer.policy)(store, scope).as_record()


def test_unchanged_context_winner_survives_library_group_and_interval_splits(tmp_path):
    store, target, members, source, sample = library_fixture(tmp_path)
    with store:
        full = {'subject_refs': [target['id']]}
        winner, _ = context_account(store, target, source, sample, 'baseline', [
            ('growth_assay', 'transfer', full)])
        kwargs = {'integration_arithmetic': STABLE_INTEGRATION, 'details_limit': 100}
        before = project_credit(store, **kwargs)
        # A full default cell, an exceptional whole member and a sensitive
        # member interval now all project the same original winning values.
        masks = [select_mask(store, target, members[:1]), {'subject_refs': [target['id']],
            'segments': [{'target_ref': target['id'], 'member_ref': members[1]['member_ref'],
                          'start': 1, 'end': 3, 'unit': 'nt'}]}]
        for index, mask in enumerate(masks):
            other = store.put('context', {'context_type': 'sample',
                'name': 'Synthetic losing account '+str(index), 'source_ref': source['id'],
                'attributes': [], 'related_refs': [], 'anchor': None}, origin='external')
            context_account(store, target, source, other, 'losing', [
                ('growth_assay', 'scope_limited', mask)], allocation=mask)
            after = project_credit(store, **kwargs)
            assert after.credit == before.credit
            assert after.axis_components == before.axis_components
            assert after.targets == before.targets
            assert {row['annotation_ref'] for row in after.source_contributions} == {winner['id']}
            assert after.detail_pages['source_contributions']['total'] == len(members)
            assert all(row['axis_value'] == .6 for row in after.source_contributions)
            assert AnnotationSupportScore(CreditPolicy())(store, full).credit == before.credit
