"""Actual private credit/work/fact callbacks with explicit controlled ports.

Constructors are bypassed. No scientific worker, network, resource acquisition,
native receipt or autonomous run is performed. Golden observations come from
the unchanged canonical callbacks, including failed/invalid returned outcomes.
"""
from __future__ import annotations
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = [{'home': '/'.join(filter(None, (prefix, suffix))), 'role': role}
    for prefix in PREFIXES for suffix, role in (
        ('execution_job_submission', 'launch'),
        ('execution_job_submission/local_job_execution', 'launch_local'),
        ('execution_job_submission/hpc_job_execution', 'launch_hpc'),
        ('execution_result_acquisition', 'results'))]
PATH_ROLES = {'scientific_process': 'scientific_process', 'hpc_work_planning': 'hpc',
    'hpc_allocation_execution': 'hpc_execution', 'execution_job_submission': 'launch',
    'local_job_execution': 'launch_local', 'hpc_job_execution': 'launch_hpc',
    'execution_result_acquisition': 'results'}

def capture(call):
    try:
        return {'value': call()}
    except (ValueError, TypeError, KeyError) as error:
        return {'exception': type(error).__module__ + '.' + type(error).__name__, 'message': str(error)}

def observations(row):
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
    from gene_annotation_episode.episodic_workflow.root.a110.native_file_capture import NativeFileCaptureError
    module = importlib.import_module(AXIS + '.' + row['home'].replace('/', '.') + '.episode')
    owner = object.__new__(module.ExecutionEpisode)
    assert owner.roles == (row['role'],)
    context = BindingContext(run_id='controlled-run', episode_id='controlled-episode', role=row['role'],
        path=tuple((PATH_ROLES[part], 'controlled-' + str(index)) for index, part in enumerate(row['home'].split('/'))),
        scope={'subject_refs': []}, assignment={}, request={})
    events = []
    def port(name, result=None):
        def called(*args, **kwargs):
            events.append(name)
            return deepcopy(result)
        return called
    invalid = {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
        'feedback': {'category': 'arguments_or_reference', 'code': 'controlled_original_invalid'}}
    delegate_view = {'credit': 0.0, 'operational_credit': 0.0, 'status': 'failed', 'failure': 'controlled_unavailable'}
    async def delegate_execute(*args):
        events.append('delegate.execute')
        return deepcopy(invalid)
    delegate = SimpleNamespace(credit_view=port('delegate.credit_view', delegate_view),
        catalog=port('delegate.catalog', [{'name': 'controlled.native', 'input_schema': {'type': 'object'}}]),
        execute=delegate_execute, state=port('delegate.state', {'status': 'invalid'}),
        facts=port('delegate.facts', {'practical_receipt_refs': ['new', 'unavailable'], 'practical_completed': False}),
        completion_for_action=port('delegate.completion_for_action', None),
        initialize=port('delegate.initialize', {'status': 'unavailable'}))
    owner.native_flux_balance_results = None
    owner.native_flux_balance_returns = None
    owner.handoff_unit, owner.acquired_record_unit = 2.0, 3.0
    owner._delegate = lambda supplied: delegate
    owner._practical_context = lambda supplied: supplied
    owner._check_parent_inputs = port('check_parent_inputs')
    owner._closed_operational_credit_view = port('closed_credit.lookup', None)
    selected = {'initial_known_record_refs': ['prior'], 'known_record_refs': ['prior', 'new', 'duplicate', 'bad']}
    handoffs = {'prior': {'resource_id': 'one'}, 'new': {'resource_id': 'two'},
        'duplicate': {'resource_id': 'two'}, 'bad': {'resource_id': 'bad'}}
    results = {'result': {'windows': [{'path': 'result.txt'}], 'captured_files': [{'source_ref': 'source'}]}}
    owner._received = lambda *args, **kwargs: (deepcopy(selected), deepcopy(handoffs), deepcopy(results))
    def handoff_read(reference, scope):
        events.append('handoff.read:' + reference)
        if reference == 'unavailable': raise ValueError('controlled_missing_handoff')
        return deepcopy(handoffs[reference]), True, True
    owner.job_progress_provider = SimpleNamespace(targets=SimpleNamespace(
        usable_handoff=lambda target: target['resource_id'] != 'bad',
        _handoff_reader=lambda: handoff_read))
    owner.local_file_sources = SimpleNamespace(acquisition_counts=port('file.acquisition_counts', None),
        applies=lambda supplied: False, outcomes_for_context=port('file.outcomes', []))
    owner._generic_result_selector_progress = port('selector.progress', 0.25)
    owner._context_target = lambda supplied, target: target
    owner._native_results_complete = port('native.results_complete', False)
    owner.store = SimpleNamespace(read_snapshot=nullcontext)
    owner._target = port('target', {'resource_id': 'two'})
    owner._selector = port('selector', {})
    owner._flux_balance_selector = lambda assignment: False
    owner._result_directory = port('result_directory', 'controlled-directory')
    owner.resources = {'one': {'kind': 'local'}}
    owner.initial_information = {'one': {'status': 'unavailable'}}
    owner._resource_information = port('resource_information', {'resource_id': 'one', 'availability': 'unknown'})
    owner._launch = port('launch.decode', {'requests': {}, 'immutable_input_versions': []})
    owner._versions = port('launch.versions', [])
    owner._flux_balance_inputs = port('flux_balance.inputs')
    async def failed_result(*args):
        events.append('native.result.execute')
        raise ValueError('controlled_original_result_unavailable')
    owner._execute_native_results = failed_result
    output = {'role': row['role']}
    def observe(name, operation):
        events.clear()
        value = capture(operation)
        output[name] = {'outcome': value, 'ports': list(events)}
    observe('live_credit', lambda: owner.credit_view(context, selected))
    observe('live_facts', lambda: owner._live_facts(context, {}))
    observe('catalog', lambda: owner.catalog(context))
    observe('initialize', lambda: owner.initialize(context))
    if hasattr(owner, 'state'): observe('state', lambda: owner.state(context))
    observe('invalid_operation', lambda: asyncio.run(owner.execute(context, 'absent.operation', {}, 'controlled-operation')))
    actual_tool = 'controlled.native' if row['role'].startswith('launch_') else 'execution.capabilities' if row['role'] == 'launch' else 'execution.results.status'
    observe('selected_operation', lambda: asyncio.run(owner.execute(context, actual_tool, {}, 'controlled-operation')))
    observe('unmatched_completion', lambda: owner.completion_for_action(context, 'not-an-original-operation'))
    if row['role'] == 'results':
        owner.local_file_sources.acquisition_counts = port('file.acquisition_counts', (1, 2))
        observe('file_acquisition_credit', lambda: owner.credit_view(context, selected))
        async def unavailable_artifact(*args):
            events.append('file.execute')
            raise NativeFileCaptureError('retained_artifact_unavailable')
        owner.local_file_sources.applies = lambda supplied: True
        owner.local_file_sources.execute = unavailable_artifact
        observe('retained_artifact_unavailable', lambda: asyncio.run(owner.execute(context, 'execution.results.status', {}, 'controlled-operation')))
        assert output['retained_artifact_unavailable']['outcome'] == {'exception': NativeFileCaptureError.__module__ + '.NativeFileCaptureError', 'message': 'retained_artifact_unavailable'}
    owner._closed_operational_credit_view = port('closed_credit.lookup', {'credit': 7.0, 'saved_original': True})
    observe('closed_credit_short_circuit', lambda: owner.credit_view(context, selected))
    assert output['closed_credit_short_circuit']['ports'] == ['closed_credit.lookup']
    if row['role'].startswith('launch_'):
        assert output['selected_operation']['outcome'] == {'value': invalid}
        assert output['live_credit']['outcome'] == {'value': delegate_view}
    return output

@pytest.mark.parametrize('row', HOMES, ids=[row['home'] for row in HOMES])
def test_actual_owned_callbacks_preserve_observed_boundaries(row):
    fixture = Path(__file__).parent / 'fixtures/organization_preservation/a110_owned_callback_baseline.json'
    baseline = json.loads(fixture.read_bytes())
    assert observations(row) == baseline['observations'][row['home']]
