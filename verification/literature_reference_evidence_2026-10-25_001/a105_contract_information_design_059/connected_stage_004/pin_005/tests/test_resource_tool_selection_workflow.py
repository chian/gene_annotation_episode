"""Selected resource information through the real scientific/launch/result tree.

Retained phmmer output and synthetic hmmscan output use a synthetic transport.
Choices and the two scientific continuation operands are bounded fixtures. No
live service, native program, HPC submission or configured model is called.
"""
import asyncio
from copy import deepcopy
import json

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.decision_context import apply_state_frame
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.providers import ModelRole
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_information import selectors
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_hmmer_grading_publication import (QUERY, RetainedClient, numeric, synthetic_payload,
    prohibit_live_network_and_native_execution)
from test_published_axis_workflow import CapturedTransport, select
from test_resource_tool_selection import CONFIG, ResourceCase


@pytest.mark.parametrize('algorithm', ['phmmer', 'hmmscan'])
@pytest.mark.parametrize('retrieval', [None, CONFIG], ids=['literal', 'configured-fixture'])
def test_internal_retrieval_scientific_child_resource_results_typed_admission_and_replay(tmp_path, algorithm, retrieval):
    with Store(tmp_path/'state') as store:
        sequence = QUERY if algorithm == 'phmmer' else 'MACDEFGHIKLM'
        database = 'pdb' if algorithm == 'phmmer' else 'pfam'
        expected_domains, expected_pairs = (4, 88) if algorithm == 'phmmer' else (1, 3)
        client = RetainedClient(None if algorithm == 'phmmer' else synthetic_payload(algorithm),
                                algorithm=algorithm, database=database)
        case = ResourceCase(tmp_path, store, client=client, sequence=sequence, retrieval=retrieval)
        request = {'version': 'api_execution_assignment_v1', 'resource_id': 'ebi',
            'service': 'ebi_hmmer', 'subject_ref': case.target, 'algorithm': algorithm,
            'database': database, 'parameters': {}, 'page_size': 2,
            'endpoint': 'usable_handoff', 'constraints': {}}
        selected = [{'name': name, 'resources': 'api'} for name in ('api.hmmer.prepare',
            'api.hmmer.submit', 'api.hmmer.check_handoff', 'api.hmmer.result')]
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')

        class Choices:
            roles = {'FAST': ModelRole('gpt-6-luna', 'none')}

            def __init__(self):
                self.states, self.keys, self.calls, self.fast_calls = {}, {}, [], []
                self.root_count = self.scientific_count = self.api_count = 0
                self.handoff = None

            def conversation_key(self, episode_id, role):
                return self.keys.get((episode_id, role))

            async def complete(self, episode_id, role, instructions, context, schema):
                if role == 'FAST':
                    self.fast_calls.append(deepcopy(context))
                    assert all(set(row) == {'name', 'description', 'resources'} for row in context['catalog'])
                    names = {row['name'] for row in context['catalog']}
                    assert 'api.hmmer.result' in names
                    assert not {'api.uniprot.collect', 'api.blast.fetch', 'practical.job.start'} & names
                    return {'child_tool_info': deepcopy(selected)}
                self.keys.setdefault((episode_id, role), ('fixture-'+episode_id, 0))
                if context['kind'] in {'decision_bootstrap', 'decision_update'}:
                    self.states[episode_id] = apply_state_frame(self.states.get(episode_id), context)
                state = self.states[episode_id]
                self.calls.append({'episode_id': episode_id, 'instructions': instructions,
                    'context': deepcopy(context), 'state': deepcopy(state), 'output_schema': deepcopy(schema)})
                assert state.get('feedback') is None, state.get('feedback')
                execution = state.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    return select(child('launch_api', request, case.scope, handoff_form)['selection'])
                if execution.get('version') == 'api_execution_assignment_v1':
                    assert execution == request
                    tool = ['api.hmmer.prepare', 'api.hmmer.submit', 'api.hmmer.check_handoff'][self.api_count]
                    self.api_count += 1
                    return select({'kind': 'tool', 'tool': tool, 'arguments': {}})
                if execution.get('version') == 'execution_results_assignment_v1':
                    assert execution == {'version': 'execution_results_assignment_v1',
                        'handoff_ref': self.handoff, 'selector': {'page': 1}}
                    return select({'kind': 'tool', 'tool': 'api.hmmer.result', 'arguments': {}})
                if 'scientific_process' in state:
                    self.scientific_count += 1
                    canonical = workflow.scientific_process_binding.tool_library.resolve_tool_info(selected)
                    assert state['scientific_process']['child_tool_info'] == canonical
                    names = {row['name'] for row in state['tools']}
                    assert not {row['name'] for row in selected} & names
                    text = render_scientific_process_prompt(state, instructions)
                    task, steering = text.split('\n\nSTEERING\n')
                    assert all(row['instructions'] in task for row in canonical)
                    assert all(row['instructions'] not in steering for row in canonical)
                    assert 'invocation_route' not in text
                    if self.scientific_count == 1:
                        return select(child('launch', launch_assignment({'ebi': request}), case.scope, handoff_form)['selection'])
                    received = state['child_reports'][-1]
                    assert received['completed'] is True
                    self.handoff, = received['references']
                    return select(child('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': self.handoff, 'selector': {'page': 1}}, case.scope, result_form)['selection'])
                self.root_count += 1
                assert state['tools'] == []
                if self.root_count == 1:
                    return {'response': {'response_type': 'request_context', 'lookup': {
                        'view': 'composition_information', 'operation': 'process.tools',
                        'arguments': {'investigation': 'HMMER sequence profile measurements'}}}}
                result = context['result']
                assert context['kind'] == 'decision_lookup_result' and result['status'] == 'completed'
                found = selectors(result['result']['child_tool_info'])
                assert all(row in found for row in selected)
                assert not any(row['name'] in {'api.uniprot.collect', 'api.blast.fetch', 'practical.job.start'}
                               for row in found)
                assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
                assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
                assert client.calls == []
                return select(case.commission(selected))

            async def release(self, episode_id):
                self.keys.pop((episode_id, 'REASONING'), None)

        choices = Choices()
        workflow = case.workflow(choices)
        root = workflow.build('annotation', 'root', 'Investigate supplied protein with requested native measurements', case.scope)
        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record
        record = asyncio.run(run())
        archived = json.loads(''.join(iter_json(record.as_record())))
        scientific = archived['units'][0]['child']
        launch, results = [unit['child'] for unit in scientific['units']]
        api = launch['units'][0]['child']
        assert [row['units_consumed'] for row in (archived, scientific, launch, api, results)] == [1, 2, 1, 3, 1]
        for row, expected in ((archived, 1), (scientific, 2), (launch, 1), (api, 3), (results, 1)):
            count = store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
                                    (row['episode_id'],)).fetchone()[0]
            assert count == expected
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 8
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 8
        assert store.db.execute('SELECT count(*) FROM runtime_model_calls').fetchone()[0] == 8
        assert store.db.execute('SELECT count(*) FROM runtime_decision_exchanges').fetchone()[0] == 9
        assert len(choices.calls) == 9 and len(choices.fast_calls) == int(retrieval is not None)
        assert [call[0] for call in client.calls] == ['submit', 'status', 'result']
        returned = json.loads(workflow.journal.row('runtime_forms', scientific['episode_id'])['form'])
        observed = [ref for ref in returned['records'] if store.get(ref)['record_type'] == 'observation']
        assert len(observed) == expected_domains
        assert any(numeric(store, ref).get('paired_positions') == expected_pairs for ref in observed)
        assert all(store.get(ref)['subject_refs'] == [case.target] for ref in observed)
        assert set(observed) <= set(workflow.receipts.known(root.source.episode_id))
        assert not store.current_annotations()
        failures = store.db.execute('SELECT failure FROM runtime_report_attempts').fetchall()
        assert failures and all(row[0] is None for row in failures)

        # Exercise the real text renderer/transport boundary for scientific TASK.
        scientific_calls = [call for call in choices.calls if 'scientific_process' in call['state']]
        wire = CapturedTransport(tmp_path/'wire')
        async def render():
            for call in scientific_calls:
                await wire.complete(call['episode_id'], 'REASONING', call['instructions'],
                                    call['context'], call['output_schema'])
        asyncio.run(render())
        turns = [params for method, params in wire.sent if method == 'turn/start']
        canonical = workflow.scientific_process_binding.tool_library.resolve_tool_info(selected)
        assert len(turns) == 2
        for turn in turns:
            task = turn['input'][0]['text'].split('\n\nSTEERING\n')[0]
            assert all(row['instructions'] in task for row in canonical)

        # Preserve the known generic API/results presentation gap as a separate
        # assertion: the scientific child's selected instructions are not yet
        # rendered as a dedicated generic API/results TASK/STEERING template.
        resource_calls = [call for call in choices.calls if call['state'].get('execution_assignment', {}).get('version')
            in {'api_execution_assignment_v1', 'execution_results_assignment_v1'}]
        assert len(resource_calls) == 4
        assert all('scientific_process' not in call['state'] for call in resource_calls)
        assert all(not call['state'].get('selected_launch_instructions') for call in resource_calls)
        assert all(canonical[-1]['instructions'] not in call['instructions'] for call in resource_calls)
        assert not store.db.execute("SELECT 1 FROM runtime_actions WHERE json_extract(action,'$.tool') LIKE 'knowledge.%'").fetchone()

        # Replay the selected native-result receipt and original scientific
        # commission. No transport call, observation, or saved selection changes.
        before = [tuple(row) for row in store.db.execute('SELECT episode_id,unit_index,observation FROM runtime_observations ORDER BY episode_id,unit_index')]
        action = store.db.execute("SELECT * FROM api_execution_actions WHERE name='api.hmmer.result'").fetchone()
        manifest = store.db.execute('SELECT * FROM api_execution_episodes WHERE episode_id=?',
                                   (action['episode_id'],)).fetchone()
        original = BindingContext(workflow.run_id, action['episode_id'], 'results', (('results', 'replay'),),
            json.loads(manifest['scope']), json.loads(manifest['assignment']), {})
        owner = workflow.episode_bindings.for_role('results').api_execution
        assert asyncio.run(owner.execute(original, 'api.hmmer.result', {}, action['operation_key'])) == json.loads(action['result'])
        restored = case.workflow(Choices())
        restored_root = restored.build('annotation', 'root', 'Investigate supplied protein with requested native measurements', case.scope)
        restored_scientific = restored.selected(restored_root.source, case.commission(selected), 0).child
        actual_request = json.loads(workflow.journal.row('runtime_episodes', scientific['episode_id'])['request'])
        assert restored_scientific.request.as_record() == actual_request
        assert [tuple(row) for row in store.db.execute('SELECT episode_id,unit_index,observation FROM runtime_observations ORDER BY episode_id,unit_index')] == before
        assert [call[0] for call in client.calls] == ['submit', 'status', 'result']
