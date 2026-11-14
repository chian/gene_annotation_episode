"""Synthetic statements in real Store records; no science or credit validation.

The host validates identity, source-subject links, and correction ownership.
These fixtures supply no measurements, grader results, or functional support.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.scientific_findings import (
    FindingIdentity, finding_target_roots, validate_finding, validate_replacement_scope)
from gene_annotation_episode.state import Store


def finding(target):
    return {'source_claim': {'subject_refs': [target], 'predicate': 'growth_capability',
                'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []},
        'qualification': {'kind': 'measurement_does_not_establish_claim',
                          'context_refs': [], 'assumption_refs': []},
        'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
        'same_source_claim_as_ref': None, 'replaces_refs': []}


def source(store, name, identifiers=()):
    artifact = store.artifact('Synthetic contract fixture, not empirical evidence: ' + name)
    return store.put('source', {'provider': 'synthetic_fixture', 'accession': name,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None,
        'publication_identifiers': list(identifiers)}, origin='external')


def operands(store):
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'biological_role',
        'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}, origin='reasoning')
    received = source(store, 'source')
    observation = store.put('observation', {'subject_refs': [target], 'source_subject_refs': [target],
        'kind': 'source_content', 'source_ref': received['id'], 'measurements': [],
        'dependencies': [], 'anchor': None}, origin='external')
    assessment = {'hypothesis_ref': hypothesis['id'], 'observation_ref': observation['id'],
        'relation': 'does_not_discriminate', 'applicability': 'incomparable',
        'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
        'expected_revision': 0, 'investigation_finding': finding(target)}
    return target, observation, assessment


def test_actual_saved_finding_identity_survives_reopen_and_declared_equivalence(tmp_path):
    with Store(tmp_path / 'store') as store:
        target, observation, payload = operands(store)
        first = store.put('assessment', payload, origin='reasoning')
        original = deepcopy(first)
        key = FindingIdentity(store).finding(first)
        assert finding_target_roots(store, first) == {target}
        corrected = deepcopy(payload)
        corrected['expected_revision'] = first['revision']
        corrected['investigation_finding']['same_source_claim_as_ref'] = first['id']
        corrected['investigation_finding']['replaces_refs'] = [first['id']]
        second = store.put('assessment', corrected, origin='reasoning', scope={'subject_refs': [target]})
        assert FindingIdentity(store).finding(second) == key
        assert store.get(first['id']) == original
        assert store.get(observation['id']) == observation
    with Store(tmp_path / 'store') as store:
        assert FindingIdentity(store).finding(store.get(second['id'])) == key
        assert store.get(first['id']) == original
        changed = deepcopy(corrected)
        changed['expected_revision'] = second['revision']
        changed['investigation_finding']['qualification']['kind'] = 'different_source_subject'
        third = store.put('assessment', changed, origin='reasoning', scope={'subject_refs': [target]})
        assert FindingIdentity(store).finding(third)['finding_key'] != key['finding_key']


@pytest.mark.parametrize('defect,code', [
    ('subject', 'finding_source_subject_not_in_observation'),
    ('status', 'finding_status_reason_mismatch'),
    ('untyped', 'finding_reference_has_no_typed_finding'),
])
def test_real_reference_validation_preserves_received_operands(tmp_path, defect, code):
    with Store(tmp_path / 'store') as store:
        target, observation, payload = operands(store)
        if defect == 'subject':
            unrelated_source = source(store, 'different-source')
            other = store.put('reference', {'reference_type': 'literature_result',
                'source_ref': unrelated_source['id'], 'accession': 'synthetic-other-subject',
                'label': 'Explicit negative reference fixture', 'sequence_ref': None,
                'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}, origin='external')
            payload['investigation_finding']['source_claim']['subject_refs'] = [other['id']]
        elif defect == 'status':
            payload['investigation_finding']['withdrawal_reason'] = 'source_misread'
        else:
            untyped = deepcopy(payload)
            del untyped['investigation_finding']
            previous = store.put('assessment', untyped, origin='reasoning')
            payload['investigation_finding']['same_source_claim_as_ref'] = previous['id']
        before = deepcopy(payload)
        with pytest.raises(ContractError, match='^' + code + '$') as caught:
            validate_finding(store, payload, observation)
        assert type(caught.value) is ContractError
        assert payload == before and store.get(observation['id']) == observation
        if defect == 'subject':
            assert caught.value.detail['observation_subject_refs'] == [target]
            assert caught.value.detail['observation_source_subject_refs'] == [target]
            assert store.get(other['id']) == other


@pytest.mark.parametrize('narrow', [False, True], ids=['owned-full-extent', 'outside-narrow-scope'])
def test_replacement_scope_uses_real_original_record_extent(tmp_path, narrow):
    with Store(tmp_path / 'store') as store:
        target, observation, payload = operands(store)
        previous = store.put('assessment', payload, origin='reasoning')
        replacement = deepcopy(payload)
        replacement['investigation_finding']['replaces_refs'] = [previous['id']]
        scope = {'subject_refs': [target]}
        if narrow:
            scope['segments'] = [{'target_ref': target, 'start': 0, 'end': 1, 'unit': 'aa'}]
            with pytest.raises(ContractError, match='^finding_replacement_outside_scope$'):
                validate_replacement_scope(store, replacement, scope)
        else:
            assert validate_replacement_scope(store, replacement, scope) is None
        assert store.get(previous['id']) == previous
        assert store.get(observation['id']) == observation


@pytest.mark.parametrize('conflicting', [False, True], ids=['declared-doi', 'conflicting-doi'])
def test_source_identity_retains_actual_metadata_conflicts(tmp_path, conflicting):
    with Store(tmp_path / 'store') as store:
        ids = [{'namespace': 'doi', 'value': '10.1234/synthetic'}]
        if conflicting:
            ids.append({'namespace': 'doi', 'value': '10.1234/other-synthetic'})
        first, second = (source(store, name, ids) for name in ('first', 'second'))
        canonicalizer = FindingIdentity(store)
        a, b = canonicalizer.source(first['id']), canonicalizer.source(second['id'])
        if conflicting:
            assert a['conflicting_publication_metadata']['doi'] == sorted(item['value'] for item in ids)
            assert a != b
        else:
            assert a == b == {'publication': {'doi': '10.1234/synthetic'}}
        assert store.get(first['id']) == first and store.get(second['id']) == second


def test_semantic_normalization_preserves_order_without_claiming_new_identity(tmp_path):
    with Store(tmp_path / 'store') as store:
        target, _, _ = operands(store)
        normalizer = FindingIdentity(store)
        assert normalizer.entity(target) == {'record_type': 'input', 'original_identity': target}
        assert normalizer.value([1.0, 2.0]) == [1, 2]
        assert normalizer.value([2.0, 1.0]) != normalizer.value([1.0, 2.0])
        assert normalizer.value({'roles': ['b', 'a', 'b']}) == {'roles': ['a', 'b']}
