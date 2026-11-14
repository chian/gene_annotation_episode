"""Root host-port ownership and real Store/Journal boundaries.

Captured scientific requests below are receipt-context fixtures, not private
child commissioning, scientific completion or publication producer coverage.
No factory, classifier, permission result, module or service method is patched.
"""
from dataclasses import replace
from importlib import import_module
import asyncio
import inspect
from pathlib import Path
import typing

import pytest

from gene_annotation_episode.episodic_workflow.root import episode_services
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeServices
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.method_loop.episode import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import actual_root, action_rows


OWNER_SPECS = (
    ('workflow_tool_services', 'WorkflowToolServices', ('tool_catalog', 'tool_information_catalog', 'execute_tool')),
    ('workflow_reference_access', 'WorkflowReferenceAccess', ('reference_in_scope', 'reference_in_context')),
    ('workflow_credit_services', 'WorkflowCreditServices', ('proposed_annotation_for', 'scientific_support_routes',
        'scientific_credit', 'bound_role_credit', 'annotation_task_required')),
    ('workflow_progress_services', 'WorkflowProgressServices', ('capabilities', 'received_progress_refs',
        'observe_progress', 'describe_progress_target', 'dependencies', 'read_progress', 'progress_selection')),
    ('workflow_scientific_provenance', 'WorkflowScientificProvenance',
        ('_scientific_provenance', 'scientific_closed_request', 'scientific_parent_invocation', 'scientific_reference',
         'scientific_preparation', 'scientific_received_results', 'scientific_frozen_results')),
    ('workflow_molecular_operands', 'WorkflowMolecularOperands',
        ('read_received_molecular_input', '_molecular_input_binding', 'read_received_molecular_file_metadata',
         'molecular_commission_assignment_matches', '_molecular_reference_access', 'authenticate_source_byte_operands')),
    ('workflow_protein_structure', 'WorkflowProteinStructure',
        ('protein_structure_input_authority', 'protein_structure_reference_access', 'authenticate_structure_alignment_operands')),
    ('workflow_result_receipts', 'WorkflowResultReceipts', ('read_received_hpc_result',)),
    ('workflow_record_access', 'WorkflowRecordAccess', ('read_record', 'record_selection', 'own_outcomes')),
    ('workflow_alignment_results', 'WorkflowAlignmentResults',
        ('_alignment_site_records', 'alignment_site_own_action_results', 'alignment_site_frozen_facts')),
)


def defining_owners():
    """Only ownership tests require the new modules; behavior runs on baseline."""
    return tuple((import_module('gene_annotation_episode.episodic_workflow.root.' + module),
                  name, methods) for module, name, methods in OWNER_SPECS)


def context(root):
    return root.workflow.binding_context(root.source)


def captured_scientific_context(root):
    """Save an authentic typed request through the original Journal/receipt APIs."""
    parent = context(root)
    path = (*parent.path, ('scientific_process', 'child_0'))
    identity = EpisodeRef(parent.run_id, path)
    goal = EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']),
        objective='Engineering saved-request identity boundary',
        result_contract={'role': 'scientific_process'})
    manifest = root.workflow.receipts.bind(identity.episode_id, parent.episode_id)
    request = EpisodeRequest(goal, Record({'scope': plain(parent.scope), 'initial_report': {},
        'episode_assignment': {}, 'knowledge_inheritance': manifest})).as_record()
    with root.store.transaction():
        root.workflow.journal.save('runtime_episodes', {'episode_id': identity.episode_id,
            'path': canonical(path), 'request': canonical(request), 'initial_credit': 0,
            'state': 'active', 'completion': None, 'archive': None})
    reader = EpisodeReturnRecords(root.store, parent.run_id, failure_prefix='service_owner_test_')
    captured = reader.context(identity.episode_id)
    assert type(captured) is BindingContext and reader.authenticate(captured) is captured
    return captured


def unchanged(root, before_changes, before_rows):
    assert root.store.db.total_changes == before_changes
    assert action_rows(root) == before_rows
    assert root.tools.execution_calls == [] and root.provider.requests == []






def test_actual_constructor_catalog_capabilities_and_absent_progress_are_read_only(tmp_path):
    with actual_root(tmp_path) as root:
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        services = root.workflow.services
        assert isinstance(services, EpisodeServices)
        assert services.tool_catalog(root.scope) == []
        assert services.capabilities() == ()
        assert root.workflow.progress_provider is None
        assert services.received_progress_refs(root.source.episode_id) == []
        unchanged(root, before_changes, before_rows)


def test_scope_reader_keeps_real_record_kinds_and_rejects_unattached_bytes(tmp_path):
    with actual_root(tmp_path) as root:
        reference = root.scope['subject_refs'][0]
        unattached = root.store.artifact(b'engineering unattached bytes', 'text/plain')
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        services = root.workflow.services
        assert services.reference_in_scope(reference, root.scope, 'subject') is True
        assert services.reference_in_scope(reference, root.scope, 'artifact') is False
        assert services.reference_in_scope(unattached, root.scope, 'artifact') is False
        unchanged(root, before_changes, before_rows)


def test_actual_immutable_receiving_context_and_ancestor_reads_do_not_infer_annotation(tmp_path):
    with actual_root(tmp_path) as root:
        parent, child = context(root), captured_scientific_context(root)
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        assert type(parent) is BindingContext
        assert root.workflow.services.proposed_annotation_for(parent) is None
        assert root.workflow.services.proposed_annotation_for(child) is None
        with pytest.raises(TypeError):
            child.assignment['proposed_annotation_ref'] = 'unrecorded'
        unchanged(root, before_changes, before_rows)


def test_active_saved_scientific_request_does_not_become_a_closed_result(tmp_path):
    with actual_root(tmp_path) as root:
        child = captured_scientific_context(root)
        row = dict(root.workflow.journal.row('runtime_episodes', child.episode_id))
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        assert root.workflow.services.scientific_closed_request(child) is None
        assert dict(root.workflow.journal.row('runtime_episodes', child.episode_id)) == row
        assert root.workflow.journal.row('runtime_forms', child.episode_id) is None
        unchanged(root, before_changes, before_rows)


@pytest.mark.parametrize('identity_field', ['run_id', 'episode_id', 'path'], ids=['run', 'episode', 'path'])
def test_saved_scientific_request_rejects_foreign_identity_before_reading_other_work(tmp_path, identity_field):
    with actual_root(tmp_path) as root:
        child = captured_scientific_context(root)
        alternatives = {'run_id': 'other-run', 'episode_id': 'other-episode',
                        'path': (*child.path[:-1], ('scientific_process', 'other-child'))}
        invalid = replace(child, **{identity_field: alternatives[identity_field]})
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        with pytest.raises(ValueError, match='^scientific_closed_request_identity_mismatch$'):
            root.workflow.services.scientific_closed_request(invalid)
        unchanged(root, before_changes, before_rows)


def test_unconfigured_scientific_provenance_remains_unavailable_without_science(tmp_path):
    with actual_root(tmp_path) as root:
        actual = context(root)
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        assert root.workflow.scientific_provenance is None
        for method in ('scientific_parent_invocation', 'scientific_received_results', 'scientific_frozen_results'):
            with pytest.raises(ValueError, match='^scientific_process_provenance_unavailable$'):
                getattr(root.workflow.services, method)(actual)
        with pytest.raises(ValueError, match='^scientific_process_provenance_unavailable$'):
            root.workflow.services.scientific_preparation(actual, 'unavailable-preparation')
        with pytest.raises(ValueError, match='^scientific_provenance_receiver_identity_mismatch$'):
            root.workflow.services.scientific_parent_invocation(replace(actual, run_id='other-run'))
        unchanged(root, before_changes, before_rows)


@pytest.mark.parametrize('port,code', [
    ('reference_in_context', 'context_reference_receiver_identity_mismatch'),
    ('scientific_support_routes', 'scientific_support_routes_receiver_identity_mismatch'),
], ids=['reference', 'scientific-support'])
def test_foreign_receiver_checks_precede_selected_private_owner_imports(tmp_path, port, code):
    with actual_root(tmp_path) as root:
        invalid = replace(context(root), run_id='other-run')
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        with pytest.raises(ValueError, match='^' + code + '$'):
            if port == 'reference_in_context':
                root.workflow.services.reference_in_context(invalid, root.scope['subject_refs'][0], 'subject')
            else:
                root.workflow.services.scientific_support_routes(invalid, observation_kinds=())
        unchanged(root, before_changes, before_rows)


@pytest.mark.parametrize('selection', [{}, {'tag_key': 'x', 'file_format': 'fasta'},
    {'source_metadata_only': 1}, {'source_metadata_only': True}],
    ids=['none', 'multiple', 'nonboolean', 'source-wrong-namespace'])
def test_invalid_molecular_selection_is_rejected_before_missing_owner_construction(tmp_path, selection):
    with actual_root(tmp_path) as root:
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        with pytest.raises(ValueError, match='^molecular_sequence_input_invalid_selection$'):
            root.workflow.services.read_received_molecular_input(context(root),
                root.scope['subject_refs'][0], 'input', **selection)
        unchanged(root, before_changes, before_rows)


def test_absent_optional_molecular_tool_authority_preserves_tri_state(tmp_path):
    with actual_root(tmp_path) as root:
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        assert root.workflow.services._molecular_reference_access(
            context(root), root.scope['subject_refs'][0], 'subject') is None
        unchanged(root, before_changes, before_rows)


@pytest.mark.parametrize('decision_index', [-1, True], ids=['negative', 'boolean'])
def test_original_commission_index_guard_does_not_authenticate_unperformed_work(tmp_path, decision_index):
    with actual_root(tmp_path) as root:
        child = captured_scientific_context(root)
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        assert root.workflow.services.molecular_commission_assignment_matches(
            context(root), child, {}, decision_index=decision_index) is False
        unchanged(root, before_changes, before_rows)


def test_real_record_receipt_and_progress_selections_are_read_only(tmp_path):
    with actual_root(tmp_path) as root:
        actual = context(root)
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        services = root.workflow.services
        reference = root.scope['subject_refs'][0]
        assert services.read_record(reference) == root.store.get(reference)
        assert services.record_selection(actual) == root.workflow.record_selection(actual.episode_id)
        assert services.progress_selection(actual) == root.workflow.progress_selection(actual)
        assert services.own_outcomes(actual.episode_id, tools=None, offset=0, limit=2) == {
            'records': [], 'offset': 0, 'limit': 2, 'next_offset': None}
        for method, code in (('record_selection', 'record_selection_receiver_identity_mismatch'),
                             ('progress_selection', 'progress_selection_receiver_identity_mismatch')):
            with pytest.raises(ValueError, match='^' + code + '$'):
                getattr(services, method)(replace(actual, run_id='other-run'))
        unchanged(root, before_changes, before_rows)


def test_unconfigured_progress_and_role_credit_keep_original_unavailable_results(tmp_path):
    with actual_root(tmp_path) as root:
        services = root.workflow.services
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        assert services.describe_progress_target('not-exposed', root.scope) is None
        for method, arguments in (
            ('observe_progress', ('not-exposed', (), root.scope)),
            ('dependencies', ('not-exposed', root.scope)),
            ('read_progress', ('not-received', root.scope)),
        ):
            with pytest.raises(ValueError, match='^episode_progress_provider_not_bound$'):
                getattr(services, method)(*arguments)
        with pytest.raises(ValueError, match='^explicit_role_credit_binding_required:annotation$'):
            services.bound_role_credit(context(root), {})
        unchanged(root, before_changes, before_rows)


def test_saved_returned_outcome_fixtures_preserve_failed_invalid_unavailable_and_signed_credit(tmp_path):
    """Original Journal record fixtures; no tool execution or scientific success."""
    with actual_root(tmp_path) as root:
        identity = root.source.episode_id
        with root.store.transaction():
            for index, status in enumerate(('failed', 'invalid', 'unavailable')):
                root.workflow.journal.save('runtime_actions', {'episode_id': identity,
                    'decision_index': index, 'action': canonical({'kind': 'tool',
                        'tool': 'engineering.saved_outcome'}),
                    'result': canonical({'status': status, 'record_refs': [],
                        'changed_record_refs': [], 'progress_refs': []}),
                    'credit': -0.375, 'timing': None})
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        services = root.workflow.services
        first = services.own_outcomes(identity, tools=['engineering.saved_outcome'], offset=0, limit=2)
        assert first == {'records': [
            {'decision_index': index, 'selected_tool': 'engineering.saved_outcome', 'status': status,
             'record_refs': [], 'changed_record_refs': [], 'progress_refs': [], 'result_ref': None}
            for index, status in enumerate(('failed', 'invalid'))],
            'offset': 0, 'limit': 2, 'next_offset': 2}
        last = services.own_outcomes(identity, tools=None, offset=first['next_offset'], limit=2)
        assert [row['status'] for row in last['records']] == ['unavailable']
        assert last['records'][0]['decision_index'] == 2 and last['next_offset'] is None
        assert services.own_outcomes(identity, tools=[], offset=0, limit=2)['records'] == []
        assert all(root.workflow.journal.row('runtime_actions', identity, index)['credit'] == -0.375
                   for index in range(3))
        unchanged(root, before_changes, before_rows)


def test_async_tool_port_propagates_actual_injected_tool_failure_without_science(tmp_path):
    with actual_root(tmp_path) as root:
        before_changes, before_rows = root.store.db.total_changes, action_rows(root)
        with pytest.raises(RuntimeError, match='^engineering_fixture_has_no_acquisition_capability$'):
            asyncio.run(root.workflow.services.execute_tool('engineering.unavailable', {},
                scope=root.scope, operation_key='engineering-service-owner', permitted_record_refs=()))
        assert len(root.tools.execution_calls) == 1
        args, kwargs = root.tools.execution_calls[0]
        assert args == ('engineering.unavailable', {})
        assert kwargs == {'scope': plain(root.scope), 'operation_key': 'engineering-service-owner',
                          'permitted_record_refs': ()}
        assert root.store.db.total_changes == before_changes and action_rows(root) == before_rows
        assert root.provider.requests == []
