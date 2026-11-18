"""Twelve actual A104 native owners retain their original parent's contract.

The reusable fixture builds a real HPC plan/ledger and own-axis bindings. Only
the selected existing test methods are reused; no Launch private-file naming
assertions or different-axis application implementation is inherited. Graded
BLAST uses the actual own-axis ToolRegistry/service preparation, so unresolved
default/API dependencies remain visible failures. No service/native dispatch.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import socket
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_launch_task_checks import LaunchTaskChecks
from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior

CHILDREN = {'api_job_execution': 'launch_api', 'local_job_execution': 'launch_local', 'hpc_job_execution': 'launch_hpc'}


def forbidden(*args, **kwargs):
    raise AssertionError('network_native_provider_dispatch_forbidden_in_contract_test')


class NoClientCalls:
    def __getattr__(self, name):
        return forbidden


class NativeContractChecks:
    axis = 'a104'
    module = LaunchTaskChecks.module
    launch_case = LaunchTaskChecks.launch_case
    case_registry = LaunchTaskChecks.case_registry
    test_original_native_parent_contract = LaunchTaskChecks.test_native_parent_contract_does_not_admit_parent_as_own_role
    test_original_runtime_native_commission = LaunchTaskChecks.test_runtime_commission_calls_launch_request_before_native_admission
    test_original_mutated_native_request = LaunchTaskChecks.test_mutated_native_request_rejected_before_native_execution

    @pytest.fixture(params=tuple(CHILDREN))
    def native_case(self, launch_case, request):
        value = launch_case
        home = self.binding_path + '/' + request.param
        child = self.module(home + '/episode').ExecutionEpisode(value.services, **value.execution_options)
        role = CHILDREN[request.param]
        path = value.context.path + ((role, 'original-native'),)
        context = replace(value.context, role=role, path=path,
            episode_id=self.module('method_loop.identities').EpisodeRef(value.context.run_id, path).episode_id)
        return SimpleNamespace(value=value, binding=child, context=context, home=home)

    @pytest.mark.parametrize('status', ('invalid', 'failed', 'unavailable'))
    def test_native_returned_outcome_and_saved_credit_preserve_full_payload(self, native_case, tmp_path, monkeypatch, status):
        case = native_case
        monkeypatch.setattr(case.binding, 'credit_view', lambda *args: {'credit': 3.25})
        adapter = SimpleNamespace(setup=lambda _: SimpleNamespace(binding=case.binding, context=case.context,
            c={'objective': 'Preserve returned native outcome'}), module=self.module)
        f = PlanningAllocationTaskBehavior.fixture(adapter, tmp_path)
        payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'result': {'original_child': case.home, 'qualification': {'executed': False, 'retained': ['full', 'payload']}},
            'feedback': {'code': 'controlled_original_return'}}
        calls = []
        async def returned(source, name, arguments, **kwargs):
            calls.append((name, deepcopy(arguments), kwargs['operation_key']))
            return deepcopy(payload)
        f.task.workflow.execute = returned
        selected = {'kind': 'tool', 'tool': 'controlled-original-tool', 'arguments': {'original': ['request']}}
        assert asyncio.run(f.task.execute(selected, 8)) == {'index': 8, 'credit': 3.25}
        assert asyncio.run(f.task.execute(selected, 8)) == {'index': 8, 'credit': 3.25}
        assert calls == [(selected['tool'], selected['arguments'], f'{case.context.run_id}:{case.context.episode_id}:8')]
        assert json.loads(f.saved[8]['action']) == selected and json.loads(f.saved[8]['result']) == {**payload, 'pending_work_after_action': f.task.workflow.pending_work(f.task)}
        assert f.receipts == [(8, status)] and len(f.projections) == 1
        # Replay the actual recorded credit even if a current projector changes.
        monkeypatch.setattr(case.binding, 'credit_view', forbidden)
        assert asyncio.run(f.task.execute(selected, 8)) == {'index': 8, 'credit': 3.25}
        assert len(calls) == len(f.receipts) == len(f.projections) == 1

    def test_nonempty_graded_blast_parent_operands_and_original_rejections(self, native_case, monkeypatch):
        case, value = native_case, native_case.value
        monkeypatch.setattr(subprocess, 'Popen', forbidden)
        monkeypatch.setattr(socket, 'create_connection', forbidden)
        tools = self.module('tools').ToolRegistry(value.store, clients=NoClientCalls())
        options = {**value.execution_options, 'resources': {**value.execution_options['resources'],
            'blast': {'kind': 'api', 'service': 'ncbi_blast'}}, 'tool_registry': tools}
        child = self.module(case.home + '/episode').ExecutionEpisode(value.services, **options)
        subject = value.context.scope['subject_refs'][0]
        request = {'version': 'blast_database_grader_return_request_v1', 'resource_id': 'blast',
            'return_type': 'blast_database_sheet_v1', 'query_subject_ref': subject, 'database': 'swissprot'}
        assignment = {'version': 'execution_launch_assignment_v1', 'requests': {'blast': request},
            'immutable_input_versions': [], 'constraints': {}}
        selected = child._launch(deepcopy(assignment), scope=value.context.scope)
        assert selected == assignment and selected is not assignment
        sequence = tools._sequence(subject, molecule_model=value.store.subject_molecule(subject))
        expected = {'return_type': 'blast_database_sheet_v1', 'query_subject_ref': subject,
            'query_length': len(sequence), 'query_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
            'database': 'swissprot'}
        assert child._blast_launch_requirement(selected['requests']['blast'], 'blast', value.context.scope) == expected
        api_request = {'version': 'api_service_assignment_v1', 'resource_id': 'blast', 'service': 'ncbi_blast',
            'request': {'subject_ref': subject, 'program': 'blastp', 'database': 'swissprot'},
            'endpoint': 'usable_handoff', 'constraints': {}}
        assert child._validate_blast_launch_selection(selected, api_request, value.context.scope) is None
        wrong_database = deepcopy(api_request)
        wrong_database['request']['database'] = 'nr_clustered_seq'
        with pytest.raises(ValueError, match='blast_grader_selected_database_conflict'):
            child._validate_blast_launch_selection(selected, wrong_database, value.context.scope)
        wrong_resource = deepcopy(assignment)
        wrong_resource['requests']['blast']['resource_id'] = 'other-resource'
        with pytest.raises(ValueError):
            child._launch(wrong_resource, scope=value.context.scope)
        with pytest.raises(ValueError, match='unknown_execution_episode_role'):
            child.assignment_schema('launch', internal=True)
        assert child.roles == (case.context.role,)


class TestA104HPCNativeContracts(NativeContractChecks):
    binding_path = 'hpc_work_planning/execution_job_submission'


class TestA104AllocationNativeContracts(NativeContractChecks):
    binding_path = 'hpc_work_planning/hpc_allocation_execution/execution_job_submission'


class TestA104ScientificHPCNativeContracts(NativeContractChecks):
    binding_path = 'evolutionary_history_evidence/hpc_work_planning/execution_job_submission'


class TestA104ScientificAllocationNativeContracts(NativeContractChecks):
    binding_path = 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
