"""Original/private provider presentation, with only transport ports controlled.

No provider/native process starts. _SessionConnection construction, frame
validation, presentation, request/response files, ModelConnection forwarding,
task.call, Journal persistence and completed replay are actual own-axis code.
"""
import asyncio
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace

import pytest

from .. import providers, runtime
from ..decision_context import INSTRUCTIONS, VERSION, state_frame
from ..episode_journal import Journal
from ..library.hpc_prompt import render_hpc_prompt
from ..receiver_prompt import render_receiver_prompt
from ..scientific_process_prompt import text_instructions
from .test_source_investigation_family import HOMES, PREFIX, case, family


CONFIG = {'connection': {'command': ['forbidden-controlled-presentation-provider']},
    'FAST': {'model': 'controlled', 'reasoning_effort': 'low'},
    'REASONING': {'model': 'controlled', 'reasoning_effort': 'low'}, 'routing': {}}
INSTRUCTION = 'Original caller instructions.\n' + INSTRUCTIONS
REPLY = {'selected': 'controlled'}
SCHEMA = {'type': 'object', 'properties': {'selected': {'const': 'controlled'}},
    'required': ['selected'], 'additionalProperties': False}


class ControlledSession(providers._SessionConnection):
    """Only process/RPC transport is replaced; all presentation code is actual."""
    async def __aenter__(self):
        self.process = SimpleNamespace(pid=-1, returncode=0)
        return self

    async def __aexit__(self, *exception):
        return None

    async def _session(self, episode_id, role, instructions):
        self.sessions[(episode_id, role)] = ('controlled-thread',)
        self.actual_model_instructions = instructions
        return 'controlled-thread'

    async def _rpc(self, method, parameters):
        assert method == 'turn/start'
        self.actual_turn = deepcopy(parameters)
        return {'turn': {'id': 'controlled-turn'}}

    async def _collect_turn(self, thread, turn_id, directory, episode_id, role):
        assert (thread, turn_id) == ('controlled-thread', 'controlled-turn')
        return json.dumps(REPLY)


def ordinary():
    scope = {'subject_refs': ['source:controlled']}
    return {'goal': {'objective': 'Read the supplied source and preserve unresolved correspondence'},
        'scope': scope, 'working_state': {'subjects': [], 'scope': deepcopy(scope)},
        'tools': [{'name': 'public.literature.read'}], 'requested_form': None,
        'controller': {}, 'current_report_update': {}, 'last_local_outcome': None,
        'qualified_findings': [{'source_claim': 'fixture source claim',
            'source_subject': 'fixture subject', 'target_correspondence': None}],
        'contract_information_profile': 'operation_contract_information_v1'}


SCENARIOS = ('ordinary', 'minimal', 'unrecognized_bootstrap', 'ordinary_update',
    'missing_unrecognized_delta', 'missing_recognized_delta', 'lookup_with_state',
    'lookup_without_state', 'restored_bootstrap', 'task_disappears',
    'hpc_precedence', 'invalid_revision')


def frames(name):
    state = ordinary()
    updated = {**state, 'last_local_outcome': {'status': 'unavailable',
        'feedback': 'controlled unavailable source; preserve this actual returned status'}}
    minimal = {'source_body': '<article>Original saved bytes</article>',
        'qualified_findings': [{'subject': 'fixture subject', 'target_correspondence': None}]}
    if name == 'ordinary': return [state]
    if name == 'minimal': return [minimal]
    if name == 'unrecognized_bootstrap': return [state, state_frame(minimal)]
    if name == 'ordinary_update': return [state_frame(state), state_frame(updated, state)]
    if name == 'missing_unrecognized_delta': return [state_frame(updated, state)]
    if name == 'missing_recognized_delta': return [state_frame(state, {'previous': 'absent'})]
    lookup = {'version': VERSION, 'kind': 'decision_lookup_result',
        'result': {'source_ref': 'source:controlled', 'body': 'retained lookup result'},
        'pending_contract_information': [{'schema_ref': 'exact-original-contract'}]}
    if name == 'lookup_with_state': return [state_frame(state), lookup]
    if name == 'lookup_without_state': return [lookup]
    if name == 'restored_bootstrap':
        return [{**state_frame(state), 'restored_public_exchanges': [
            {'lookup_result': {'source_ref': 'source:controlled', 'body': 'restored original reply'}}],
            'restored_pending_decision_index': 3}]
    if name == 'task_disappears': return [state_frame(state), state_frame(minimal, state)]
    if name == 'hpc_precedence':
        return [{**state, 'hpc_commission': {'objective': 'original higher-priority HPC task'},
            'scientific_process': {'evidence_axis': {
                'instruction_status': 'published_investigation_instructions'}}}]
    if name == 'invalid_revision': return [{**state_frame(state), 'revision': 'wrong-saved-identity'}]
    raise AssertionError(name)


def session(directory):
    return ControlledSession(CONFIG, directory, directory.parent)


def observations(worker, supplied, *, renderer=None):
    rows = []
    for context in supplied:
        before = deepcopy(context)
        try:
            result = worker._presentation('episode:original', 'REASONING', INSTRUCTION,
                context, **({'prompt_renderer': renderer} if renderer is not None else {}))
            row = {'returned': result}
        except (TypeError, ValueError) as error:
            row = {'raised': (type(error), str(error))}
        assert context == before
        rows.append({**row, 'states': deepcopy(worker.scientific_prompt_states)})
    return rows


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_original_provider_presentation_oracle(tmp_path, scenario):
    values = frames(scenario)
    observed = observations(session(tmp_path / 'original'), values)
    final = observed[-1]
    if scenario in {'minimal', 'unrecognized_bootstrap', 'missing_unrecognized_delta',
            'lookup_without_state', 'task_disappears'}:
        assert final['returned'] == (json.dumps(values[-1], allow_nan=False), INSTRUCTION)
        assert final['states'] == {}
    elif scenario == 'missing_recognized_delta':
        assert final['raised'] == (TypeError, 'previous_model_state_requires_object')
    elif scenario == 'invalid_revision':
        assert final['raised'] == (ValueError, 'decision_frame_revision_conflict')
    elif scenario == 'hpc_precedence':
        assert final['returned'] == (render_hpc_prompt(values[-1], INSTRUCTION), text_instructions(INSTRUCTION))
    elif scenario == 'ordinary':
        assert final['returned'] == (render_receiver_prompt(values[-1], INSTRUCTION), text_instructions(INSTRUCTION))
    else:
        assert 'returned' in final and final['states']
        assert final['returned'][1] == text_instructions(INSTRUCTION)
        if scenario == 'lookup_with_state':
            assert 'exact-original-contract' in final['returned'][0]
            assert 'retained lookup result' in final['returned'][0]
        if scenario == 'restored_bootstrap':
            assert 'restored original reply' in final['returned'][0]


@pytest.mark.parametrize('home,role', HOMES)
@pytest.mark.parametrize('scenario', SCENARIOS)
def test_connected_private_policy_preserves_full_original_state_machine(tmp_path, home, role, scenario):
    presentation = importlib.import_module(PREFIX + home.replace('/', '.') + '.task_presentation')
    policy = importlib.import_module(PREFIX + home.replace('/', '.') + '.task_presentation_policy')
    renderer = presentation.render_receiver_prompt
    assert renderer.provider_presentation is policy.present_source_task
    original, private = session(tmp_path / 'original'), session(tmp_path / 'private')
    def forbidden_declared(*args, **kwargs):
        raise AssertionError('the original declared-renderer shortcut lost policy semantics')
    private._declared_presentation = forbidden_declared
    values = frames(scenario)
    assert observations(private, deepcopy(values), renderer=renderer) == observations(original, deepcopy(values))


@pytest.mark.parametrize('home,role', HOMES)
def test_connected_actual_model_connection_forwards_policy_and_records_exact_input(tmp_path, home, role):
    presentation = importlib.import_module(PREFIX + home.replace('/', '.') + '.task_presentation')
    provider = providers.ModelConnection(CONFIG, tmp_path / 'model', tmp_path)
    provider.session_type = ControlledSession
    payload = frames('minimal')[0]
    assert asyncio.run(provider.complete_with_presentation('episode:original', 'REASONING',
        INSTRUCTION, payload, SCHEMA, prompt_renderer=presentation.render_receiver_prompt)) == REPLY
    request = json.loads((provider.directory / 'session-0001/call-00001/request.json').read_text())
    assert request['input'] == [{'type': 'text', 'text': json.dumps(payload, allow_nan=False)}]
    assert request['instructions'] == INSTRUCTION and 'model_instructions' not in request
    assert request['context'] == payload and request['output_schema'] == SCHEMA
    assert request['presentation'] == {'module': presentation.__name__, 'qualname': 'render_receiver_prompt'}
    assert provider.workers == {} and provider.retirement_index == 1


