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
from .provider_dispatch_fixtures import observed_session_model


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
def test_connected_private_policy_preserves_current_frames_and_original_fact_guidance(tmp_path, home, role, scenario):
    from ..library.source_component_prompt import with_fact_contract_instructions
    presentation = importlib.import_module(PREFIX + home.replace('/', '.') + '.task_presentation')
    renderer = presentation.present_source_context
    assert renderer.presentation_protocol == 'episode_context_presentation_v1'
    original, private = session(tmp_path / 'original'), session(tmp_path / 'private')
    def forbidden_declared(*args, **kwargs):
        raise AssertionError('the original declared-renderer shortcut lost policy semantics')
    private._declared_presentation = forbidden_declared
    values = frames(scenario)
    expected = observations(original, deepcopy(values))
    # The exact original component fact guidance is a separately declared
    # restoration. Current frame, JSON fallback, state and error paths remain
    # exact; the original pure presentation helper decorates rendered states.
    for row in expected:
        if 'returned' in row and row['states']:
            text, instruction = row['returned']
            state = row['states'][('episode:original', 'REASONING')]
            row['returned'] = (with_fact_contract_instructions(text, state), instruction)
    assert observations(private, deepcopy(values), renderer=renderer) == expected


@pytest.mark.parametrize('home,role', HOMES)
def test_connected_actual_model_connection_forwards_policy_and_records_exact_input(tmp_path, home, role):
    presentation = importlib.import_module(PREFIX + home.replace('/', '.') + '.task_presentation')
    provider = providers.ModelConnection(CONFIG, tmp_path / 'model', tmp_path)
    provider.session_type = ControlledSession
    payload = frames('minimal')[0]
    assert asyncio.run(provider.complete_with_presentation('episode:original', 'REASONING',
        INSTRUCTION, payload, SCHEMA, prompt_renderer=presentation.present_source_context)) == REPLY
    request = json.loads((provider.directory / 'session-0001/call-00001/request.json').read_text())
    assert request['input'] == [{'type': 'text', 'text': json.dumps(payload, allow_nan=False)}]
    assert request['instructions'] == INSTRUCTION and 'model_instructions' not in request
    assert request['context'] == payload and request['output_schema'] == SCHEMA
    assert request['presentation'] == {'module': presentation.__name__, 'qualname': 'present_source_context'}
    assert provider.workers == {} and provider.retirement_index == 1


@pytest.mark.parametrize('home,role', HOMES)
@pytest.mark.parametrize('boundary', ('ordinary_experimental', 'experimental_update',
    'hpc_before_experimental', 'experimental_before_published_science'))
def test_connected_original_experimental_priority_and_qualified_payload(tmp_path, home, role, boundary):
    from ..library.source_component_prompt import (
        render_component_axis_literature_prompt, with_fact_contract_instructions)
    presentation = importlib.import_module(PREFIX + home.replace('/', '.') + '.task_presentation')
    value = {**ordinary(), 'literature_assignment': {'version': 'literature_assignment_v1',
        'question_context_refs': [], 'source_refs': []},
        'literature_experimental_work': {'version': 'literature_experimental_task_v1',
            'aspect': 'source_experimental_evidence'},
        'component_axis_source_access': {'version': 'component_axis_source_access_v1',
            'retained_fixture_limitation': 'Reference sample to target correspondence unresolved'}}
    if boundary == 'hpc_before_experimental':
        value['hpc_commission'] = {'objective': 'original higher-priority HPC task'}
    if boundary == 'experimental_before_published_science':
        value['scientific_process'] = {'evidence_axis': {
            'instruction_status': 'published_investigation_instructions'}}
    if boundary == 'experimental_update':
        updated = {**value, 'last_local_outcome': {'status': 'unavailable',
            'feedback': 'Actual returned acquisition failure is not evidence absence'}}
        supplied = [state_frame(value), state_frame(updated, value)]
        expected_state = updated
    else:
        supplied, expected_state = [value], value
    selected = render_hpc_prompt if boundary == 'hpc_before_experimental' else render_component_axis_literature_prompt
    expected_text = with_fact_contract_instructions(selected(expected_state, INSTRUCTION), expected_state)
    worker = session(tmp_path / 'experimental')
    result = observations(worker, deepcopy(supplied), renderer=presentation.present_source_context)[-1]
    assert result['returned'] == (expected_text, text_instructions(INSTRUCTION))
    assert result['states'] == {('episode:original', 'REASONING'): expected_state}
    limitation = 'Reference sample to target correspondence unresolved'
    if boundary == 'hpc_before_experimental':
        # The authentic higher-priority HPC renderer does not project this
        # lower-priority component field; the entire original state stays above.
        assert limitation not in result['returned'][0]
        assert result['states'][('episode:original', 'REASONING')][
            'component_axis_source_access']['retained_fixture_limitation'] == limitation
    else:
        assert limitation in result['returned'][0]


@pytest.mark.parametrize('home,role', HOMES)
@pytest.mark.parametrize('capable', (False, True))
def test_pending_saved_task_call_and_completed_replay_use_original_payload(family, tmp_path, home, role, capable):
    binding, context = case(family, home, 'pending-presentation-' + str(capable))
    task = object.__new__(getattr(binding, 'decision_source_type', runtime.DecisionSource))
    task.episode_id, task.path, task.calls = context.episode_id, context.path, 0
    task.instructions = lambda supplied: INSTRUCTION  # Explicit fixed instruction-composition port.
    journal = Journal(family.store, context.run_id)
    # Use the actual durable serialization order, which is part of the exact
    # JSON provider input when the original pending record is read again.
    payload = json.loads(runtime._json({**frames('minimal')[0],
        'restored_episode_history': {'saved': 'original metadata'}}))
    saved = {'context': payload, 'schema': SCHEMA, 'assignment_transport': {
        'version': runtime._ASSIGNMENT_TRANSPORT, 'action_schema_sha256': runtime._digest(SCHEMA)}}
    journal.save('runtime_model_calls', {'episode_id': context.episode_id, 'call_index': 0,
        'purpose': 'decision', 'request': runtime._json(saved), 'response': None})
    worker = session(tmp_path / 'actual-session')
    calls = []
    class LegacyProvider:
        def has_session(self, *args): return False
        async def complete(self, episode_id, purpose, instructions, supplied, schema):
            calls.append(('original', deepcopy(supplied), deepcopy(schema)))
            return await worker.complete(episode_id, purpose, instructions, supplied, schema)
    provider, workers = (observed_session_model(CONFIG, tmp_path / 'actual-model', tmp_path,
        ControlledSession, calls) if capable else (LegacyProvider(), []))
    task.workflow = SimpleNamespace(journal=journal,
        contract_information_profile=lambda source: None, decision_protocol=None,
        receipts=None, provider=provider,
        specialist=lambda source: binding)
    expected = (REPLY, 0, payload, SCHEMA)
    assert asyncio.run(task.call({'replacement': 'must not replace pending request'}, {})) == expected
    if capable:
        assert len(workers) == 1 and provider.retirement_index == 1 and provider.workers == {}
        worker = workers[0]
    request = json.loads((worker.directory / 'call-00001/request.json').read_text())
    assert request['input'] == [{'type': 'text', 'text': json.dumps(payload, allow_nan=False)}]
    assert request['instructions'] == INSTRUCTION and 'model_instructions' not in request
    assert calls == [('private' if capable and hasattr(binding, 'decision_source_type') else 'original',
        payload, runtime._action_generation_schema(SCHEMA))]
    saved_row = journal.row('runtime_model_calls', context.episode_id, 0)
    assert json.loads(saved_row['request']) == saved and json.loads(saved_row['response']) == REPLY
    task.calls = 0
    task.workflow.provider = SimpleNamespace()  # Completed replay must not dispatch.
    assert asyncio.run(task.call({'later': 'catalog'}, {})) == expected
    assert journal.row('runtime_model_calls', context.episode_id, 0) == saved_row
    assert worker.call_index == 1 and len(calls) == 1
