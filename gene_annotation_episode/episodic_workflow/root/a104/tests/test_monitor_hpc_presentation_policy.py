"""Real own provider policy/cache controls; no Store, model or native execution."""
from copy import deepcopy
import importlib
import json
import pytest

from .. import providers
from ..decision_context import VERSION, INSTRUCTIONS, state_frame
from ..library.hpc_prompt import render_hpc_prompt
from ..library.monitor_prompt import render_monitor_prompt
from ..execution_prompt import render_api_launch_prompt
from ..scientific_process_prompt import render_scientific_process_prompt, render_selected_execution_prompt, text_instructions
from ..receiver_prompt import render_receiver_prompt

BASE = 'gene_annotation_episode.episodic_workflow.root.a104.'
HOMES = (
    ('execution_progress_assessment', 'MonitorEpisode'),
    ('hpc_work_planning', 'HPCEpisode'),
    ('hpc_work_planning/execution_progress_assessment', 'MonitorEpisode'),
    ('hpc_work_planning/hpc_allocation_execution', 'HPCEpisode'),
    ('hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'MonitorEpisode'),
    ('hpc_work_planning/hpc_resource_prediction', 'HPCEpisode'),
    ('scientific_process/execution_progress_assessment', 'MonitorEpisode'),
    ('scientific_process/hpc_work_planning', 'HPCEpisode'),
    ('scientific_process/hpc_work_planning/execution_progress_assessment', 'MonitorEpisode'),
    ('scientific_process/hpc_work_planning/hpc_allocation_execution', 'HPCEpisode'),
    ('scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'MonitorEpisode'),
    ('scientific_process/hpc_work_planning/hpc_resource_prediction', 'HPCEpisode'))
REPRESENTATIVES = HOMES[:2]
SCENARIOS = ('minimal', 'minimal_prior', 'monitor', 'hpc', 'ordinary', 'bootstrap', 'update',
    'unrecognized_bootstrap', 'missing_unrecognized_delta', 'missing_recognized_delta',
    'lookup_with_state', 'lookup_without_state', 'restored_bootstrap', 'task_disappears',
    'invalid_revision', 'hpc_over_monitor', 'scientific_over_monitor', 'api_over_monitor',
    'selected_over_monitor', 'lookup_contract_order')
GUIDANCE = 'Preserve original supplied monitoring information.\n' + INSTRUCTIONS
KEY = ('episode:presentation-control', 'REASONING')
OTHER = ('episode:unrelated', 'FAST')


def ordinary():
    scope = {'subject_refs': []}
    return {'goal': {'objective': 'Inspect supplied engineering state without inventing observations'},
        'scope': scope, 'working_state': {'subjects': [], 'scope': deepcopy(scope)},
        'tools': [], 'requested_form': None, 'controller': {}, 'current_report_update': {},
        'last_local_outcome': None}


def operands(scenario):
    plain = ordinary()
    monitor = {**plain, 'monitor_assignment': {'version': 'monitor_assignment_v1'}}
    minimal = {'unrecognized': 'original saved bytes'}
    updated = {**monitor, 'last_local_outcome': {'status': 'unavailable', 'feedback': 'fixture transport unavailable'}}
    selected = {'version': 'selected_execution_task_v1', 'scientific_question': 'Original supplied control question',
        'selected_tool_info': [], 'requests': [{'resource_id': 'controlled', 'resource': {}, 'job': {}}]}
    api = {'execution_assignment': {'version': 'api_service_assignment_v1', 'service': 'controlled', 'request': {}},
        'api_service': 'controlled', 'api_request': {}}
    science = {'scientific_process': {'evidence_axis': {'instruction_status': 'published_investigation_instructions',
        'investigation_instructions': 'Inspect supplied control fields; do not infer scientific results.'}}}
    lookup = {'version': VERSION, 'kind': 'decision_lookup_result', 'result': {'original': 'lookup'}}
    contract = {**monitor, 'contract_information_profile': 'operation_contract_information_v1'}
    if scenario == 'minimal': return [minimal]
    if scenario == 'minimal_prior': return [monitor, minimal]
    if scenario == 'monitor': return [monitor]
    if scenario == 'hpc': return [{**plain, 'hpc_commission': {'objective': 'Original supplied HPC control'}}]
    if scenario == 'ordinary': return [plain]
    if scenario == 'bootstrap': return [state_frame(monitor)]
    if scenario == 'update': return [state_frame(monitor), state_frame(updated, monitor)]
    if scenario == 'unrecognized_bootstrap': return [monitor, state_frame(minimal)]
    if scenario == 'missing_unrecognized_delta': return [state_frame({**minimal, 'later': True}, minimal)]
    if scenario == 'missing_recognized_delta': return [state_frame(monitor, {'previous': 'absent'})]
    if scenario == 'lookup_with_state': return [state_frame(monitor), lookup]
    if scenario == 'lookup_without_state': return [lookup]
    if scenario == 'restored_bootstrap': return [{**state_frame(monitor), 'restored_pending_decision_index': 3,
        'restored_public_exchanges': [{'lookup_result': {'original': 'restored'}}]}]
    if scenario == 'task_disappears': return [state_frame(monitor), state_frame(minimal, monitor)]
    if scenario == 'invalid_revision': return [{**state_frame(monitor), 'revision': 'wrong-original-revision'}]
    if scenario == 'hpc_over_monitor': return [{**monitor, **api, **science, 'selected_execution_task': selected,
        'hpc_commission': {'objective': 'Original highest priority'}}]
    if scenario == 'scientific_over_monitor': return [{**monitor, **api, **science, 'selected_execution_task': selected}]
    if scenario == 'api_over_monitor': return [{**monitor, **api, 'selected_execution_task': selected}]
    if scenario == 'selected_over_monitor': return [{**monitor, 'selected_execution_task': selected}]
    if scenario == 'lookup_contract_order': return [state_frame(contract), {**lookup,
        'pending_contract_information': [{'contract': 'first'}, lookup['result']]}]
    raise AssertionError(scenario)


def observe(values, renderer=None):
    worker = object.__new__(providers._SessionConnection)
    worker.scientific_prompt_states = {OTHER: {'unrelated': ['retained']}}
    if getattr(renderer, 'presentation_protocol', None) == 'episode_context_presentation_v1':
        def forbidden(*args, **kwargs): raise AssertionError('private full policy must bypass raw declared-renderer shortcut')
        worker._declared_presentation = forbidden
    rows = []
    for context in values:
        before = deepcopy(context)
        try:
            outcome = {'returned': worker._presentation(*KEY, GUIDANCE, context,
                **({'prompt_renderer': renderer} if renderer is not None else {}))}
        except (TypeError, ValueError) as error:
            outcome = {'raised': (type(error), str(error))}
        assert context == before
        assert worker.scientific_prompt_states[OTHER] == {'unrelated': ['retained']}
        rows.append({**outcome, 'cache': deepcopy(worker.scientific_prompt_states)})
    return rows




@pytest.mark.parametrize('home,class_name', REPRESENTATIVES)
@pytest.mark.parametrize('scenario', SCENARIOS)
def test_original_default_policy_and_private_context_cache_are_identical(home, class_name, scenario):
    binding = getattr(importlib.import_module(BASE + home.replace('/', '.') + '.episode'), class_name)
    values = operands(scenario)
    expected = observe(deepcopy(values))
    actual = observe(deepcopy(values), binding.decision_prompt_renderer)
    assert actual == expected
    final = expected[-1]
    if scenario == 'missing_recognized_delta':
        assert final['raised'] == (TypeError, 'previous_model_state_requires_object')
    elif scenario == 'invalid_revision':
        assert final['raised'] == (ValueError, 'decision_frame_revision_conflict')
    else:
        assert all('returned' in row for row in expected)
        if scenario in {'minimal', 'minimal_prior', 'unrecognized_bootstrap', 'missing_unrecognized_delta',
                'lookup_without_state', 'task_disappears'}:
            assert final['returned'] == (json.dumps(values[-1], allow_nan=False), GUIDANCE)
            assert (KEY in final['cache']) is (scenario == 'minimal_prior')
        else:
            assert KEY in final['cache'] and final['returned'][1] == text_instructions(GUIDANCE)
    renderers = {'monitor': render_monitor_prompt, 'hpc': render_hpc_prompt, 'ordinary': render_receiver_prompt,
        'hpc_over_monitor': render_hpc_prompt, 'scientific_over_monitor': render_scientific_process_prompt,
        'api_over_monitor': render_api_launch_prompt, 'selected_over_monitor': render_selected_execution_prompt}
    if scenario in renderers:
        assert final['returned'] == (renderers[scenario](values[-1], GUIDANCE, lookup_results=[]), text_instructions(GUIDANCE))
    if scenario == 'lookup_contract_order':
        assert final['returned'][0] == render_monitor_prompt(final['cache'][KEY], GUIDANCE,
            lookup_results=[{'contract': 'first'}, {'original': 'lookup'}])
