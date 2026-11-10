"""Subject-mismatch feedback preserves custody and supports explicit correction."""
import asyncio
from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, project_finding_progress
from gene_annotation_episode.scientific_findings import validate_finding
from gene_annotation_episode.state import Store
from test_scientific_findings import finding, quoted_observation, target_question
from test_scientific_hypervolume_runtime import assessment
from test_state import empty_payload


@pytest.mark.parametrize('wrong_kind', ['number', 'other_source_subject'])
def test_wrong_subject_remains_rejected_until_caller_selects_recorded_subject(tmp_path, wrong_kind):
    with Store(tmp_path / 'state') as store:
        target, hypothesis = target_question(store)
        scope = {'subject_refs': [target]}
        subject, observed = quoted_observation(store, accession='measured', start=0, end=17)
        if wrong_kind == 'number':
            wrong = store.put('reference', {'reference_type': 'literature_result',
                'source_ref': observed['source_ref'], 'accession': 'reported-number-10',
                'label': '10', 'sequence_ref': None, 'molecule': None, 'length': None,
                'term_refs': [], 'context_refs': []}, origin='external')['id']
        else:
            wrong, _ = quoted_observation(store, accession='other-source', start=18, end=67)
        original_observation = deepcopy(store.get(observed['id']))
        original_wrong = deepcopy(store.get(wrong))
        row = assessment(hypothesis, observed['id'], 'scope_limited', alias='source_finding')
        row.update(relation='does_not_discriminate', extent_basis='inferred_extent',
            target_footprint=[{'target_ref': target, 'start': 0, 'end': 10, 'unit': 'aa'}])
        row['investigation_finding'] = finding(wrong, qualification='different_source_subject')
        payload = empty_payload()
        payload['assessments'] = [row]
        original_payload = deepcopy(payload)

        rejected = store.commit_reasoning(payload, scope, 'wrong-source-subject')
        assert rejected['status'] == 'invalid'
        assert rejected['record_refs'] == rejected['changed_record_refs'] == []
        error, = rejected['errors']
        assert error['code'] == 'finding_source_subject_not_in_observation'
        assert error['reference'] == wrong and error['observation_ref'] == observed['id']
        assert error['field_path'] == ['investigation_finding', 'source_claim', 'subject_refs', 0]
        assert error['observation_subject_refs'] == observed['subject_refs'] == [subject]
        assert error['observation_source_subject_refs'] == observed['source_subject_refs'] == [subject]
        assert 'does not substitute' in error['repair']
        assert payload == original_payload
        assert store.get(observed['id']) == original_observation
        assert store.get(wrong) == original_wrong
        assert store.commit_reasoning(payload, scope, 'wrong-source-subject') == rejected
        assert store.current_assessments() == []
        assert project_finding_progress(store, scope, FindingProgressPolicy(1),
            known_assessment_refs=[])['credit'] == 0

        corrected = deepcopy(payload)
        corrected['assessments'][0]['investigation_finding']['source_claim']['subject_refs'] = [subject]
        accepted = store.commit_reasoning(corrected, scope, 'caller-corrected-source-subject')
        assert accepted['status'] == 'completed' and accepted['errors'] == []
        saved = store.get(accepted['aliases']['source_finding'])
        assert saved['investigation_finding']['source_claim']['subject_refs'] == [subject]
        assert saved['relation'] == 'does_not_discriminate'
        assert saved['investigation_finding']['qualification']['kind'] == 'different_source_subject'
        assert store.get(observed['id']) == original_observation
        assert store.get(wrong) == original_wrong
        assert project_finding_progress(store, scope, FindingProgressPolicy(1),
            known_assessment_refs=[saved['id']])['credit'] == 1


def test_feedback_reuses_observation_references_without_loading_their_bodies():
    class ReceivedArgumentStore:
        calls = []

        def _require(self, ref, kinds):
            self.calls.append(ref)
            assert ref == 'reference_wrong_number', 'unreceived subject body was read'
            return {'id': ref, 'record_type': 'reference'}

    store = ReceivedArgumentStore()
    observed = {'subject_refs': ['reference_observed'],
        'source_subject_refs': ['reference_source_subject']}
    request = {'observation_ref': 'observation_received',
        'investigation_finding': finding('reference_wrong_number')}
    with pytest.raises(ContractError, match='finding_source_subject_not_in_observation') as error:
        validate_finding(store, request, observed)
    assert store.calls == ['reference_wrong_number']
    assert error.value.detail['observation_subject_refs'] == ['reference_observed']
    assert error.value.detail['observation_source_subject_refs'] == ['reference_source_subject']


def test_either_existing_observation_subject_role_remains_permitted():
    class SubjectStore:
        def _require(self, ref, kinds):
            return {'id': ref, 'record_type': 'reference'}

    observed = {'subject_refs': ['reference_observed'],
        'source_subject_refs': ['reference_source_subject']}
    for subject in ('reference_observed', 'reference_source_subject'):
        validate_finding(SubjectStore(), {'observation_ref': 'observation_received',
            'investigation_finding': finding(subject)}, observed)


@pytest.mark.parametrize('through_history', [False, True])
def test_recorded_subject_operands_reach_actual_literature_wire(tmp_path, through_history):
    from gene_annotation_episode.decision_context import state_frame
    from test_component_axis_inspection_prompt import state
    from test_literature_experimental_prompt_delivery import LiteratureWire, complete

    first = state()
    first['last_local_outcome'] = {'status': 'invalid', 'record_refs': [],
        'errors': [{'code': 'finding_source_subject_not_in_observation',
            'reference': 'reference_wrong_number', 'observation_ref': 'observation_sample',
            'observation_subject_refs': ['reference_membrane_sample'],
            'observation_source_subject_refs': ['reference_membrane_sample'],
            'repair': 'Use this observation\'s actual subject; preserve unknown target correspondence.'}]}
    if through_history:
        first['last_local_outcome'] = {'status': 'completed', 'result': {
            'view': 'records', 'total_prior_decisions': 1,
            'records': [{'decision_index': 0, 'outcome': first['last_local_outcome']}]}}
    second = deepcopy(first)
    second['current_credit'] = 0
    original = deepcopy((first, second))
    wire, cold = LiteratureWire(tmp_path / 'wire'), LiteratureWire(tmp_path / 'cold')

    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(cold, state_frame(second))

    asyncio.run(exercise())
    for turn in (*wire.turns_sent(), *cold.turns_sent()):
        text = turn['input'][0]['text']
        assert 'finding_source_subject_not_in_observation' in text
        assert 'Recorded observation subjects for the rejected finding' in text
        assert 'observation_subject_refs' in text and 'observation_source_subject_refs' in text
        assert 'reference_membrane_sample' in text and 'reference_wrong_number' in text
        assert 'preserve unknown target correspondence' in text
    assert (first, second) == original


def test_source_provider_fields_are_not_promoted_to_host_rejection_feedback():
    from gene_annotation_episode.component_axis_literature_prompt import _finding_subject_rejections

    provider = {'errors': [{'code': 'finding_source_subject_not_in_observation',
        'observation_subject_refs': ['reference_untrusted'],
        'observation_source_subject_refs': ['reference_untrusted']}]}
    assert _finding_subject_rejections({'status': 'completed',
        'result': {'provider_result': provider}}) == []
