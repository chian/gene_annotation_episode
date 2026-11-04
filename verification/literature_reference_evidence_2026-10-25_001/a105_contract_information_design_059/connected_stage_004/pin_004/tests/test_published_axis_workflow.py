"""Actual publication and Workflow integration, with explicitly scripted decisions.

Only sequence.inspect and a retained-source read perform scientific-tool work
here. The fixed continuation fixture and zero-credit projector are engineering
inputs, not a scoring policy or a configured-model investigation.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.decision_context import apply_state_frame, state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.providers import _SessionConnection, load_config
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
AXES = tuple(f'A{number}' for number in (*range(101, 109), 110, 111))
THOUGHTS = tuple(f'P{number:02}' for number in range(1, 20))
PROTEIN = 'MACDEFGHIKLMNPQRSTVWY'
FORM = obj({
    'status': {'type': 'string', 'enum': ['unresolved', 'composition_measured'],
        'description': 'Whether the supplied sequence composition has actually been measured; no function is asserted.'},
    'records': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
        'x-source': 'committed_record_refs',
        'description': 'Actual records returned by this child\'s completed work.'},
})
PURPOSE = 'Return the measured-composition status and actual acquired records, with function unresolved.'
OBJECTIVE = 'Determine what can be learned about the supplied unnamed protein within the assigned evidence axis.'


def select(selection, status=None):
    return {'response': {'response_type': 'select_action', 'selection': selection,
        'report_update': {} if status is None else {'status': status}}}


def tool(name, arguments, status='unresolved'):
    return select({'kind': 'tool', 'tool': name, 'arguments': arguments}, status)


def lookup(option_id):
    return {'response': {'response_type': 'request_context', 'lookup': {
        'view': 'composition_information', 'operation': 'process.entry',
        'arguments': {'option_id': option_id}}}}


class StopBeforeDecision(Exception):
    """A capture-only fixture, before any selected scientific action."""


class ScriptedDecisions:
    def __init__(self, script):
        self.script = iter(script)
        self.calls, self.states, self.keys, self.released = [], {}, {}, []

    def conversation_key(self, episode_id, role):
        return self.keys.get((episode_id, role))

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING'
        self.keys.setdefault((episode_id, role), ('fixture-' + episode_id, 0))
        if context['kind'] in {'decision_bootstrap', 'decision_update'}:
            self.states[episode_id] = apply_state_frame(self.states.get(episode_id), context)
        call = deepcopy({'episode_id': episode_id, 'instructions': instructions,
            'context': context, 'output_schema': output_schema, 'state': self.states[episode_id]})
        self.calls.append(call)
        response = next(self.script)
        if isinstance(response, BaseException):
            raise response
        return response(call) if callable(response) else deepcopy(response)

    async def release(self, episode_id):
        self.released.append(episode_id)
        self.keys.pop((episode_id, 'REASONING'), None)


class CapturedTransport(_SessionConnection):
    """Exercise the real provider presentation and turn input without a server."""
    def __init__(self, directory):
        super().__init__(load_config(), directory, directory.parent)
        self.sent = []
        self.turns = 0

    async def _rpc(self, method, params):
        self.sent.append((method, deepcopy(params)))
        if method == 'thread/start':
            return {'thread': {'id': 'integration-thread'}, 'model': params['model'],
                'reasoningEffort': 'medium'}
        assert method == 'turn/start'
        self.turns += 1
        turn_id = 'integration-turn-' + str(self.turns)
        self.pending.extend([
            {'method': 'item/completed', 'params': {'threadId': 'integration-thread',
                'item': {'type': 'agentMessage', 'text': '{"fixture":true}'}}},
            {'method': 'turn/completed', 'params': {'threadId': 'integration-thread',
                'turn': {'id': turn_id, 'status': 'completed'}}},
        ])
        return {'turn': {'id': turn_id}}


def table_count(store, table):
    return store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]


class PublishedCase:
    def __init__(self, tmp_path, store):
        self.store, self.directory = store, tmp_path / 'run'
        self.source = tmp_path / 'published-source'
        shutil.copytree(PUBLICATION, self.source)
        self.tools = ToolRegistry(store)
        self.target, = store.create_problem(raw_sequence=PROTEIN, molecule='protein')['subject_refs']
        self.scope = store.validate_scope({'subject_refs': [self.target]})
        self.descriptor = prepare_scientific_binding(run_directory=self.directory,
            source_directory=self.source, tool_catalog=self.tools.catalog(),
            child_roles=('scientific_process',))
        self.library = ScientificProcessLibrary(self.directory / 'scientific-process-library')
        self.controllers = {}

    def commission(self, axis='A101', thought='P01'):
        return {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': OBJECTIVE, 'scope': deepcopy(self.scope), 'purpose': PURPOSE,
            'schema_json': json.dumps(FORM), 'initial_report_json': '{"status":"unresolved"}',
            'assignment': {'selection': {'version': 'scientific_process_selection_v3',
                'evidence_axis': self.library.reference(axis),
                'thought_pattern': self.library.reference(thought),
                'child_tool_info': [{'name': 'sequence.inspect', 'resources': 'local'}]},
                'evidence_refs': [self.target],
                'constraints': {'preserve_sequence_boundaries': True, 'no_external_acquisition': True},
                'context': {'supplied_sequence': PROTEIN, 'molecule': 'protein',
                    'complete': True, 'label_is_public_identity': False}}}

    def workflow(self, provider, *, stops=None):
        stops = {1: 1, 2: 2} if stops is None else stops
        def controller(path, initial):
            # The ordinary controller makes its unchanged upper-band/cost
            # comparison. Only its expected-gain input is a bounded fixture.
            def estimate(history, parameters, contexts):
                future = 0 if len(history) >= stops[len(path)] else 1
                return YieldEstimate(len(history), NumericBand.exact(future), parameters,
                    {'engineering_fixture': True})
            result = YieldController(str(path), initial, 0, estimate_with_context=estimate)
            self.controllers[path] = result
            return result
        workflow = Workflow(self.store, self.tools, provider, self.directory,
            'published-axis-fixture', controller, lambda *_: 0,
            episode_binding_descriptors=[self.descriptor], episode_record_receipts=True,
            initial_known_record_refs=[], decision_protocol='decision_exchange_v1')
        def forbidden_routes(*args, **kwargs):
            pytest.fail('Published investigation instructions must not dispatch scoring-route metadata')
        workflow.services.scientific_support_routes = forbidden_routes
        return workflow


def assert_complete_task(text, case, axis, *, thought='P01'):
    body = case.library.resolve(case.library.reference(axis))
    pattern = case.library.resolve(case.library.reference(thought))
    assert text.startswith('TASK\n\n') and text.count('\n\nSTEERING\n') == 1
    task, steering = text.split('\n\nSTEERING\n')
    assert body['investigation_instructions'] in task
    assert body['investigation_instructions'] not in steering
    assert OBJECTIVE in task and PURPOSE in task and PROTEIN in task
    for guidance in pattern['decision_guidance']:
        assert guidance in task
    for contingency in pattern['outcome_contingencies']:
        assert contingency['if_observed'].replace('|', '\\|') in task
        assert contingency['then_consider'].replace('|', '\\|') in task
    for field in ('preserve_sequence_boundaries', 'no_external_acquisition', 'return.status', 'return.records'):
        assert field in task
    for key in ('annotation_support_routes', 'axis_judgment_contract', 'scoring_rubric',
                'reader_bindings', 'initial_selection_sha256', 'mechanics_binding',
                'decision_bootstrap supplies', 'base_revision', 'removed_fields'):
        assert key not in text
    assert 'request scientific_process_results' not in text
    for row in body['evidence']:
        assert row['observation'] not in text


def test_actual_publication_freezes_all_entries_and_retains_source_custody(tmp_path):
    source = tmp_path / 'publication'
    shutil.copytree(PUBLICATION, source)
    library = ScientificProcessLibrary.freeze(tmp_path / 'frozen', source=source)
    assert {row['option_ref']['option_id'] for row in library.headers()} == set(AXES + THOUGHTS)
    provenance = json.loads((PUBLICATION / 'SOURCE_PROVENANCE.json').read_text())['entries']
    assert {row['option'] for row in provenance} == set(AXES + THOUGHTS)
    expected, row_count = {}, 0
    for row in provenance:
        option = row['option']
        original_bytes = (ROOT / row['retained_source']).read_bytes()
        assert hashlib.sha256(original_bytes).hexdigest() == row['source_sha256']
        original = json.loads(original_bytes)
        reference = library.reference(option)
        body = library.resolve(reference)
        assert body['evidence'] == original['evidence']
        frozen_bytes = (library.directory / 'entries' / (option + '.json')).read_bytes()
        assert frozen_bytes == (PUBLICATION / 'entries' / (option + '.json')).read_bytes()
        if option in THOUGHTS:
            assert frozen_bytes == original_bytes
        else:
            assert set(body) == {'entry_version', 'id', 'slot', 'name', 'description',
                'investigation_instructions', 'evidence'}
            outcome = library.execute('process.entry', {'option_id': option})
            assert outcome['result']['entry'] == instruction_view(body)
            assert outcome['record_refs'] == outcome['changed_record_refs'] == []
        rows = library.sources(option_ref=reference, offset=0, limit=1000)['rows']
        assert [{key: value for key, value in item.items() if key not in {'option_id', 'evidence_id'}}
                for item in rows] == original['evidence']
        row_count += len(rows)
        expected[option] = (reference, body, rows, frozen_bytes)
    assert row_count == 344
    descriptor = library.as_record()
    shutil.rmtree(source)
    reopened = ScientificProcessLibrary.freeze(library.directory, source=source)
    assert reopened.as_record() == descriptor
    for option, (reference, body, rows, original_bytes) in expected.items():
        assert reopened.resolve(reference) == body
        assert reopened.sources(option_ref=reference, offset=0, limit=1000)['rows'] == rows
        assert (reopened.directory / 'entries' / (option + '.json')).read_bytes() == original_bytes


@pytest.mark.parametrize('axis', AXES)
def test_every_published_axis_commissions_from_supplied_material_without_candidate(tmp_path, axis):
    with Store(tmp_path / 'state') as store:
        case = PublishedCase(tmp_path, store)
        commission = case.commission(axis)
        original = deepcopy(commission)
        provider = ScriptedDecisions([select(commission), StopBeforeDecision()])
        workflow = case.workflow(provider)
        before = {kind: store.count(kind) for kind in ('source', 'observation', 'annotation', 'hypothesis', 'assessment')}
        root = workflow.build('annotation', 'root', 'Investigate the supplied protein', case.scope)
        with pytest.raises(StopBeforeDecision):
            asyncio.run(root.run_async(workflow.context))
        call = provider.calls[-1]
        state, process = call['state'], call['state']['scientific_process']
        assert state['requested_form'] == FORM
        assert state['requested_report_purpose'] == PURPOSE
        assert state['current_report_update'] == {'status': 'unresolved'}
        assert state['scope'] == case.scope
        for key in ('context', 'constraints', 'evidence_refs'):
            assert process['assignment'][key] == original['assignment'][key]
        assert process['evidence_axis'] == instruction_view(case.library.resolve(case.library.reference(axis)))
        assert process['thought_pattern']['id'] == 'P01'
        tool_info, = process['child_tool_info']
        assert tool_info == workflow.scientific_process_binding.tool_library.resolve_tool_info(
            original['assignment']['selection']['child_tool_info'])[0]
        assert tool_info['description'] == case.tools.catalog()['sequence.inspect']['description']
        assert set(tool_info) == {'name', 'description', 'resources', 'instructions'}
        assert set(original['assignment']['context']) == {'supplied_sequence', 'molecule', 'complete', 'label_is_public_identity'}
        text = render_scientific_process_prompt(state, call['instructions'])
        assert_complete_task(text, case, axis)
        assert tool_info['instructions'] in text
        assert {kind: store.count(kind) for kind in before} == before
        assert before['annotation'] == before['hypothesis'] == before['assessment'] == 0
        assert table_count(store, 'runtime_episodes') == 2
        assert table_count(store, 'runtime_observations') == table_count(store, 'tool_operations') == 0
        assert commission == original


def test_actual_workflow_lookup_inspection_typed_return_and_text_reconstruction(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = PublishedCase(tmp_path, store)
        commission = case.commission('A101')
        commission['assignment']['selection']['child_tool_info'].append(
            {'name': 'source.read', 'resources': 'local'})
        def choose_child(call):
            result = call['context']['result']
            assert result['status'] == 'completed' and result['record_refs'] == []
            assert result['result']['entry']['id'] == 'A101'
            return select(commission)
        def after_measurement(call):
            assert call['state']['last_local_outcome']['result']['length'] == len(PROTEIN)
            return lookup('A101')
        def read_recorded_measurement(call):
            outcome = call['state']['last_local_outcome']
            source_ref, = [ref for ref in outcome['record_refs'] if ref.startswith('source_')]
            return tool('source.read', {'source_ref': source_ref, 'representation': 'original',
                'offset': 0, 'limit': 4096}, 'composition_measured')
        provider = ScriptedDecisions([lookup('A101'), choose_child,
            tool('sequence.inspect', {'subject_ref': case.target}), after_measurement,
            read_recorded_measurement])
        workflow = case.workflow(provider)
        root = workflow.build('annotation', 'root', 'Investigate the supplied protein', case.scope)
        record = asyncio.run(root.run_async(workflow.context))
        result = asyncio.run(root.build_result(record)).as_record()
        assert record.units_consumed == 1 and result['credit'] == 0
        assert sorted(controller.state().history for controller in case.controllers.values()) == [(0,), (0, 0)]
        assert table_count(store, 'runtime_observations') == table_count(store, 'runtime_actions') == 3
        assert table_count(store, 'runtime_model_calls') == 3
        assert table_count(store, 'runtime_decision_exchanges') == 5
        assert table_count(store, 'tool_operations') == 2
        measured = json.loads(store.db.execute(
            "SELECT result FROM tool_operations WHERE name='sequence.inspect'").fetchone()[0])
        assert measured['status'] == 'completed' and measured['result']['length'] == len(PROTEIN)
        assert store.count('observation') == 1 and store.count('annotation') == store.count('assessment') == 0
        observation = store.get(measured['result']['observation_ref'])
        assert observation['kind'] == 'sequence_composition'
        retained_read = json.loads(store.db.execute(
            "SELECT result FROM tool_operations WHERE name='source.read'").fetchone()[0])
        assert retained_read['status'] == 'completed'
        assert set(retained_read['record_refs']) <= set(measured['record_refs'])
        assert {source['provider'] for source in store.list('source')} == {'caller', 'sequence.inspect'}
        returned = store.db.execute('SELECT form,failure FROM runtime_report_attempts').fetchone()
        assert returned['failure'] is None
        assert json.loads(returned['form']) == {'status': 'composition_measured', 'records': measured['record_refs']}
        assert set(measured['record_refs']) <= set(workflow.receipts.known(root.source.episode_id))
        root_observations = store.db.execute('SELECT observation FROM runtime_observations WHERE episode_id=?',
            (root.source.episode_id,)).fetchall()
        assert len(root_observations) == 1
        child_calls = [call for call in provider.calls if 'scientific_process' in call['state']]
        assert [call['context']['kind'] for call in child_calls] == [
            'decision_bootstrap', 'decision_update', 'decision_lookup_result']
        assert 'scientific_process' not in child_calls[1]['context']['fields']
        child_id = child_calls[0]['episode_id']
        child_request = json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
            (child_id,)).fetchone()[0])
        assert child_request['report_contract']['measurements']['schema'] == FORM
        assert child_request['message']['episode_assignment']['context'] == commission['assignment']['context']
        assert child_request['message']['episode_assignment']['selection']['version'] == 'scientific_process_selection_v3'

        wire = CapturedTransport(tmp_path / 'wire')
        async def present_actual_calls():
            for call in child_calls:
                await wire.complete(child_id, 'REASONING', call['instructions'], call['context'], call['output_schema'])
        asyncio.run(present_actual_calls())
        turns = [params for method, params in wire.sent if method == 'turn/start']
        assert len(turns) == len(child_calls)
        for turn, call in zip(turns, child_calls):
            text = turn['input'][0]['text']
            assert_complete_task(text, case, 'A101')
            assert turn['outputSchema'] == call['output_schema']
        assert '| tool/sequence.inspect | 1 | 0' in turns[1]['input'][0]['text']
        assert 'sequence_composition' in turns[1]['input'][0]['text']
        assert 'Requested information; continue the same decision' in turns[2]['input'][0]['text']

        # Rebuild a fresh provider from the actual latest frame and answered
        # lookup, using the existing frame protocol rather than a new history.
        restored = state_frame(child_calls[-1]['state'])
        restored.update(restored_pending_decision_index=1, restored_public_exchanges=[{
            'exchange_index': 0, 'response': lookup('A101'),
            'lookup_result': child_calls[-1]['context']['result']}])
        fresh = CapturedTransport(tmp_path / 'fresh-wire')
        asyncio.run(fresh.complete(child_id, 'REASONING', child_calls[-1]['instructions'],
            restored, child_calls[-1]['output_schema']))
        fresh_turn = next(params for method, params in fresh.sent if method == 'turn/start')
        assert_complete_task(fresh_turn['input'][0]['text'], case, 'A101')
        assert 'Requested information; continue the same decision' in fresh_turn['input'][0]['text']
        assert table_count(store, 'runtime_observations') == 3
        assert table_count(store, 'tool_operations') == 2
