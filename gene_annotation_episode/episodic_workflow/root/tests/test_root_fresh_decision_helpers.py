"""Actual root connections and original presentation contracts, not science."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.task import AnnotationTask
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
from gene_annotation_episode.episodic_workflow.root.shared_information import SharedInformation
from gene_annotation_episode.episodic_workflow.root.shared_information_results import publication_view, outcome_view
from gene_annotation_episode.episodic_workflow.root.component_source_access import decision_context
from gene_annotation_episode.episodic_workflow.root.component_source_inspection import inspection_index
from gene_annotation_episode.episodic_workflow.root.execution_operand_presentation import plan_outcome_view, is_hpc_context
from gene_annotation_episode.episodic_workflow.root.literature_context_marker import is_literature_experimental_context
from gene_annotation_episode.episodic_workflow.root.evidence_axis_instructions import instruction_view
from gene_annotation_episode.episodic_workflow.root.evidence_axis_instruction_view import evidence_axis_instruction_view
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import actual_root, initial_view, action_rows, ProviderUnavailable


def test_real_root_build_and_reopen_preserve_request_received_input_and_credit(tmp_path):
    with actual_root(tmp_path) as root:
        assert type(root.source) is AnnotationTask
        before = dict(root.workflow.journal.row('runtime_episodes', root.source.episode_id))
        request = root.episode.request.as_record()
        known = tuple(root.workflow.receipts.known(root.source.episode_id))
        credit = root.workflow.source_credit_view(root.source)
        assert set(root.scope['subject_refs']) <= set(known)
        assert json.loads(before['request']) == request
        assert not any(action_rows(root).values())
    with actual_root(tmp_path, initialize=False) as root:
        assert dict(root.workflow.journal.row('runtime_episodes', root.source.episode_id)) == before
        assert root.episode.request.as_record() == request
        assert tuple(root.workflow.receipts.known(root.source.episode_id)) == known
        assert root.workflow.source_credit_view(root.source) == credit
        with pytest.raises(WorkflowError, match='reconstructed immutable assignment differs'):
            root.workflow.build('annotation', 'root', 'A different immutable request', root.scope)
        assert dict(root.workflow.journal.row('runtime_episodes', root.source.episode_id)) == before
        assert not any(action_rows(root).values())


def test_genuine_root_shared_repository_denies_nonexistent_parent_before_publication(tmp_path):
    with actual_root(tmp_path) as root:
        context = root.workflow.binding_context(root.source)
        repository = root.workflow.shared_information_repository()
        assert type(repository) is SharedInformation
        assert repository.parent(context) is None and repository.catalog(context) == []
        view = repository.context_view(context)
        assert view['upward_recipient'] is None
        assert all(view[key] == [] for key in ('needs', 'information_available', 'dispositions'))
        arguments = {'target_ref': root.scope['subject_refs'][0], 'question': 'Missing engineering operand',
            'required_information': 'An actual parent-owned operand', 'reason': 'Exercise original denial',
            'blocking': False, 'available_record_refs': []}
        with pytest.raises(ContractError, match='shared_information_parent_recipient_unavailable'):
            repository.execute(context, 'shared.request_information', arguments,
                known_record_refs=context.received_record_refs, operation_key='engineering-denied-root-request')
        assert root.store.db.execute('SELECT count(*) FROM shared_investigation_publications').fetchone()[0] == 0
        assert root.store.db.execute('SELECT count(*) FROM shared_investigation_operations').fetchone()[0] == 0
        assert not any(action_rows(root).values())


def test_shared_repository_rejects_changed_original_context_without_creating_evidence(tmp_path):
    with actual_root(tmp_path) as root:
        context = root.workflow.binding_context(root.source)
        repository = root.workflow.shared_information_repository()
        with pytest.raises(ValueError, match='shared_information_context_conflict'):
            repository.context_view(replace(context, episode_id='different_original_episode'))
        assert not any(action_rows(root).values())


def test_source_access_views_of_actual_empty_root_history_invent_no_notice(tmp_path):
    with actual_root(tmp_path) as root:
        context = root.workflow.binding_context(root.source)
        assert decision_context(root.workflow, context) is None
        assert inspection_index(root.store, run_id=root.workflow.run_id,
            episode_id=root.source.episode_id, known_source_refs=context.received_record_refs) is None
        assert not any(action_rows(root).values())


def test_actual_fresh_decision_inputs_use_real_controller_and_scoped_store(tmp_path):
    with actual_root(tmp_path) as root, initial_view(root) as view:
        context, schema = root.source._decision_inputs(view)
        assert context['goal'] == root.episode.request.goal.as_record()
        assert context['scope'] == root.scope
        assert context['current_credit']['mode'] == 'annotation_axis_credit'
        assert context['current_credit']['root_score'] == root.workflow.source_credit_view(root.source)['credit']['root_score']
        assert context['requested_form'] is None
        assert isinstance(schema['properties']['selection']['anyOf'], list)
        assert root.provider.requests == [] and root.tools.execution_calls == []
        assert not any(action_rows(root).values())


def test_unavailable_provider_retains_original_pending_request_across_real_reopen(tmp_path):
    with actual_root(tmp_path) as root, initial_view(root) as view:
        with pytest.raises(ProviderUnavailable):
            asyncio.run(root.source.next(view))
        rows = action_rows(root)
        assert rows['runtime_actions'] == rows['runtime_observations'] == []
        assert len(rows['runtime_model_calls']) == 1
        pending = rows['runtime_model_calls'][0]
        assert pending['response'] is None and pending['purpose'] == 'decision'
        request = json.loads(pending['request'])
        assert len(root.provider.requests) == 1
        assert root.provider.requests[0]['context'] == request['context']
        assert root.tools.execution_calls == []
    with actual_root(tmp_path, initialize=False) as root, initial_view(root) as view:
        assert action_rows(root)['runtime_model_calls'] == [pending]
        with pytest.raises(ProviderUnavailable):
            asyncio.run(root.source.next(view))
        after = action_rows(root)
        assert after['runtime_actions'] == after['runtime_observations'] == []
        assert len(after['runtime_model_calls']) == 1
        assert after['runtime_model_calls'][0]['request'] == pending['request']
        assert after['runtime_model_calls'][0]['response'] is None
        assert root.provider.requests[0]['context'] == request['context']


def test_shared_metadata_views_do_not_mutate_saved_publication_or_outcome():
    body = {'version': 'shared_investigation_information_v4', 'kind': 'information',
        'evidence_refs': ['engineering_reference'], 'qualification': 'Retained historical prose'}
    original = deepcopy(body)
    viewed = publication_view(body)
    assert viewed['evidence_refs'] == body['evidence_refs'] and 'qualification' not in viewed
    outcome = {'status': 'completed', 'result': body, 'record_refs': ['engineering_reference']}
    assert outcome_view(outcome)['result'] == viewed
    assert body == original and outcome['result'] == original


def test_execution_file_presentation_keeps_exact_original_bytes_and_native_operands():
    text = 'engineering input\nλ\n'
    plan = {'plan_id': 'engineering-plan', 'original_prediction': {'seconds': 2.5},
        'practical_assignment': {'nodes': 1}, 'prediction_episode_id': 'retained-host-id',
        'supplied_files': [{'path': 'input.txt', 'text': text}]}
    original = deepcopy(plan)
    viewed = plan_outcome_view({'result': plan})['result']
    assert plan == original and 'prediction_episode_id' not in viewed
    assert viewed['original_prediction'] == original['original_prediction']
    assert viewed['practical_assignment'] == original['practical_assignment']
    assert viewed['supplied_files'][0]['text_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert viewed['supplied_files'][0]['text_size_bytes'] == len(text.encode())
    assert 'text' not in viewed['supplied_files'][0]
    assert is_hpc_context({'hpc_commission': {}}) and not is_hpc_context({})


def test_original_instruction_record_validator_retains_text_and_rejects_missing_provenance():
    entry = {'entry_version': 'evidence_axis_instruction_v1', 'id': 'A107', 'slot': 'evidence_axis',
        'name': 'Engineering instruction fixture', 'description': 'Contract validation only',
        'investigation_instructions': 'Preserve the supplied engineering operand.',
        'evidence': [{'case_group': 'engineering', 'case_id': 'fixture', 'source_url': 'urn:engineering:fixture',
            'source_locator': 'fixture', 'observation': 'Contract shape', 'limit': 'No scientific evidence'}]}
    original = deepcopy(entry)
    assert instruction_view(entry)['investigation_instructions'] == entry['investigation_instructions']
    assert entry == original
    with pytest.raises(ValueError, match='evidence_axis_instruction_invalid'):
        instruction_view({**entry, 'evidence': []})
    guidance = evidence_axis_instruction_view({'id': 'A107', 'name': 'Engineering fixture',
        'description': 'Score an engineering operand.', 'native_measurements': []})
    assert guidance['instruction_status'] == 'limited_existing_measurement_guidance'
    assert 'Investigate an engineering operand.' in guidance['investigation_instructions']
    assert is_literature_experimental_context({'literature_experimental_work': {'version': 'literature_experimental_task_v1'}})
    assert not is_literature_experimental_context({'literature_experimental_work': {'version': 'other'}})
