"""Actual own-A104 Launch constructors, provider state, pending Journal and replay.

Only provider process/RPC transport and the explicit instructions callback are
controlled. No native/model work is launched. Baseline and connected phases use
the same required test source and retain every returned/raised presentation.
"""
import asyncio
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from .. import providers, runtime
from ..decision_context import VERSION, state_frame
from gene_annotation_episode.episodic_workflow.root.tests.hpc_launch_task_checks import LaunchTaskChecks
from .provider_dispatch_fixtures import observed_session_model

HOMES = ('hpc_work_planning/execution_job_submission',
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
    'scientific_process/hpc_work_planning/execution_job_submission',
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission')
HOME_IDS = ('planning', 'allocation', 'scientific_planning', 'scientific_allocation')
SCENARIOS = ('minimal', 'ordinary_hpc', 'bootstrap', 'update', 'unrecognized_bootstrap',
    'missing_unrecognized_delta', 'missing_recognized_delta', 'lookup_with_state',
    'lookup_without_state', 'restored_bootstrap', 'task_disappears', 'invalid_revision')
PHASE = os.environ.get('A104_HPC_LAUNCH_PRESENTATION_PHASE', 'auto')
assert PHASE in {'baseline', 'connected', 'auto'}
OUTPUT = Path(os.environ['A104_HPC_LAUNCH_PRESENTATION_OUTPUT']).resolve() if 'A104_HPC_LAUNCH_PRESENTATION_OUTPUT' in os.environ else None
ROOT = Path(__file__).resolve().parents[5]
assert OUTPUT is None or OUTPUT.is_relative_to(ROOT / 'runs')
CONFIG = {'connection': {'command': ['forbidden-controlled-hpc-presentation-provider']},
    'FAST': {'model': 'controlled', 'reasoning_effort': 'low'},
    'REASONING': {'model': 'controlled', 'reasoning_effort': 'low'}, 'routing': {}}
INSTRUCTION = 'Original Launch instructions and supplied guidance.'
REPLY = {'selected': 'controlled'}
SCHEMA = {'type': 'object', 'properties': {'selected': {'const': 'controlled'}},
    'required': ['selected'], 'additionalProperties': False}


def own_module(name):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.a104.' + name.replace('/', '.'))


@pytest.fixture(params=HOMES, ids=HOME_IDS)
def launch(request, tmp_path):
    adapter = SimpleNamespace(axis='a104', binding_path=request.param, module=own_module)
    generator = LaunchTaskChecks.launch_case.__wrapped__(adapter, tmp_path)
    value = next(generator)
    connected = hasattr(value.binding, 'decision_source_type')
    if PHASE != 'auto':
        assert connected is (PHASE == 'connected')
    renderer = getattr(value.binding, 'decision_prompt_renderer', None)
    if connected:
        assert renderer.presentation_protocol == 'episode_context_presentation_v1'
        assert renderer.__module__ == 'gene_annotation_episode.episodic_workflow.root.a104.' + request.param.replace('/', '.') + '.presentation'
    value.test_home = request.param
    value.test_connected = connected
    value.test_output = OUTPUT or tmp_path / 'presentation-observations'
    try:
        yield value
    finally:
        with pytest.raises(StopIteration):
            next(generator)


class ControlledSession(providers._SessionConnection):
    async def __aenter__(self):
        self.process = SimpleNamespace(pid=-1, returncode=0)
        return self
    async def __aexit__(self, *exception): return None
    async def _session(self, episode_id, role, instructions):
        self.sessions[(episode_id, role)] = ('controlled-thread',)
        return 'controlled-thread'
    async def _rpc(self, method, parameters):
        assert method == 'turn/start'
        self.actual_turn = deepcopy(parameters)
        return {'turn': {'id': 'controlled-turn'}}
    async def _collect_turn(self, thread, turn_id, directory, episode_id, role):
        assert (thread, turn_id) == ('controlled-thread', 'controlled-turn')
        return json.dumps(REPLY)


def frames(name):
    minimal = {'retained_execution': {'status': 'unavailable', 'qualification': ['original']}}
    state = {**deepcopy(minimal), 'hpc_execution_job': {'original_request': 'retained'},
        'scientific_process': {'evidence_axis': {'instruction_status': 'published_investigation_instructions'}}}
    updated = {**deepcopy(state), 'retained_execution': {'status': 'failed', 'qualification': ['original']}}
    lookup = {'version': VERSION, 'kind': 'decision_lookup_result', 'result': {'retained': ['lookup']}}
    values = {
        'minimal': [minimal], 'ordinary_hpc': [state], 'bootstrap': [state_frame(state)],
        'update': [state_frame(state), state_frame(updated, state)],
        'unrecognized_bootstrap': [state, state_frame(minimal)],
        'missing_unrecognized_delta': [state_frame({**minimal, 'later': True}, minimal)],
        'missing_recognized_delta': [state_frame(state, {'previous': 'absent'})],
        'lookup_with_state': [state_frame(state), lookup], 'lookup_without_state': [lookup],
        'restored_bootstrap': [{**state_frame(state), 'restored_pending_decision_index': 3,
            'restored_public_exchanges': [{'lookup_result': {'original': 'restored'}}]}],
        'task_disappears': [state_frame(state), state_frame(minimal, state)],
        'invalid_revision': [{**state_frame(state), 'revision': 'wrong-retained-revision'}]}
    return values[name]


def observations(worker, episode_id, values, renderer=None):
    rows = []
    for value in values:
        before = deepcopy(value)
        try:
            result = worker._presentation(episode_id, 'REASONING', INSTRUCTION, value,
                **({'prompt_renderer': renderer} if renderer is not None else {}))
            row = {'returned': list(result)}
        except (TypeError, ValueError) as error:
            row = {'raised': [type(error).__module__, type(error).__qualname__, str(error)]}
        assert value == before
        rows.append({**row, 'states': sorted([list(key), deepcopy(state)]
            for key, state in worker.scientific_prompt_states.items())})
    return rows


def retain(launch, name, value):
    destination = launch.test_output / HOME_IDS[HOMES.index(launch.test_home)] / (name + '.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert not destination.exists()
    destination.write_text(json.dumps(value, indent=2) + '\n')


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_original_private_frames_and_precedence(launch, tmp_path, scenario):
    original = ControlledSession(CONFIG, tmp_path / 'original', tmp_path)
    selected = ControlledSession(CONFIG, tmp_path / 'selected', tmp_path)
    renderer = getattr(launch.binding, 'decision_prompt_renderer', None)
    if launch.test_connected:
        def forbidden(*args, **kwargs):
            raise AssertionError('private policy must not use the unconditional declared-renderer shortcut')
        selected._declared_presentation = forbidden
    values = frames(scenario)
    expected = observations(original, launch.context.episode_id, deepcopy(values))
    actual = observations(selected, launch.context.episode_id, deepcopy(values), renderer)
    retain(launch, scenario, {'input': values, 'expected': expected, 'actual': actual})
    assert actual == expected
    final = expected[-1]
    if scenario in {'minimal', 'unrecognized_bootstrap', 'missing_unrecognized_delta', 'lookup_without_state', 'task_disappears'}:
        assert final == {'returned': [json.dumps(values[-1], allow_nan=False), INSTRUCTION], 'states': []}
    elif scenario == 'missing_recognized_delta':
        assert final['raised'] == ['builtins', 'TypeError', 'previous_model_state_requires_object']
    elif scenario == 'invalid_revision':
        assert final['raised'] == ['builtins', 'ValueError', 'decision_frame_revision_conflict']
    else:
        assert 'returned' in final and final['states']
    if scenario == 'ordinary_hpc':
        from ..library.hpc_prompt import render_hpc_prompt
        from ..scientific_process_prompt import text_instructions
        assert final['returned'] == [render_hpc_prompt(values[-1], INSTRUCTION), text_instructions(INSTRUCTION)]


@pytest.mark.parametrize('capable', (False, True), ids=('legacy_provider', 'presentation_provider'))
def test_actual_pending_model_request_and_completed_replay(launch, tmp_path, capable):
    binding, context, journal = launch.binding, launch.context, launch.journal
    task = object.__new__(getattr(binding, 'decision_source_type', runtime.DecisionSource))
    task.episode_id, task.path, task.calls = context.episode_id, context.path, 0
    task.instructions = lambda supplied: INSTRUCTION
    payload = json.loads(runtime._json({**frames('minimal')[0], 'restored_episode_history': {'saved': 'original metadata'}}))
    saved = {'context': payload, 'schema': SCHEMA}
    journal.save('runtime_model_calls', {'episode_id': context.episode_id, 'call_index': 0,
        'purpose': 'decision', 'request': runtime._json(saved), 'response': None})
    worker, calls = ControlledSession(CONFIG, tmp_path / 'actual-session', tmp_path), []
    class LegacyProvider:
        def has_session(self, *args): return False
        async def complete(self, episode_id, purpose, instructions, supplied, schema):
            calls.append(('original', deepcopy(supplied), deepcopy(schema)))
            return await worker.complete(episode_id, purpose, instructions, supplied, schema)
    provider, workers = (observed_session_model(CONFIG, tmp_path / 'actual-model', tmp_path,
        ControlledSession, calls) if capable else (LegacyProvider(), []))
    task.workflow = SimpleNamespace(journal=journal, contract_information_profile=lambda source: None,
        decision_protocol=None, receipts=None, provider=provider, specialist=lambda source: binding)
    expected = (REPLY, 0, payload, SCHEMA)
    assert asyncio.run(task.call({'replacement': 'must not replace saved request'}, {})) == expected
    if capable:
        assert len(workers) == 1 and provider.retirement_index == 1 and provider.workers == {}
        worker = workers[0]
    request = json.loads((worker.directory / 'call-00001/request.json').read_text())
    assert request['input'] == [{'type': 'text', 'text': json.dumps(payload, allow_nan=False)}]
    assert request['instructions'] == INSTRUCTION and 'model_instructions' not in request
    assert calls == [('private' if capable and launch.test_connected else 'original', payload, runtime._action_generation_schema(SCHEMA))]
    saved_row = journal.row('runtime_model_calls', context.episode_id, 0)
    assert json.loads(saved_row['request']) == saved and json.loads(saved_row['response']) == REPLY
    task.calls, task.workflow.provider = 0, SimpleNamespace()
    assert asyncio.run(task.call({'later': 'catalog'}, {})) == expected
    assert journal.row('runtime_model_calls', context.episode_id, 0) == saved_row
    assert worker.call_index == 1 and len(calls) == 1
    retain(launch, 'pending-' + str(capable), {'saved_request': saved, 'actual_provider_input': request['input'],
        'instructions': request['instructions'], 'saved_response': REPLY, 'actual_calls': len(calls), 'completed_replay_exact': True})
