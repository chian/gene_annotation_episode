"""Scripted shared-loop HMMER typed returns; retained output, no live service.

These tests exercise actual bound launch/API/results operations and admission.
The scripted decisions and explicit caller controller are test fixtures, not a
scientific investigation or a production itinerary. No grading model is used.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.api_execution import RESULT_DESCRIPTION
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tool_knowledge import ToolKnowledge
from gene_annotation_episode.tools import ToolRegistry
from api_execution_fixture import APIHarness
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_hmmer_grading_publication import (PAGE1, QUERY, RetainedClient, receiver, domain_refs,
    numeric, synthetic_payload, prohibit_live_network_and_native_execution,
    assert_span_aliases_equal_shared)


def fixture_controller(path, initial):
    # Only the scientific fixture parent's choices have a scripted stopping
    # point. Launch/results keep their actual validated-completion estimator.
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 3 else 1),
            parameters, {'fixture': 'three_explicit_parent_commissions'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=estimate if path[-1][0] == 'annotation' else None)


@pytest.mark.parametrize('algorithm', ['phmmer', 'hmmscan'])
def test_launch_api_native_page_numeric_records_and_parent_admission_repeated_delivery(tmp_path, algorithm):
    with Store(tmp_path/'state') as store:
        sequence = QUERY if algorithm == 'phmmer' else 'MACDEFGHIKLM'
        database = 'pdb' if algorithm == 'phmmer' else 'pfam'
        expected_domains, expected_pairs = (4, 88) if algorithm == 'phmmer' else (1, 3)
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        client = RetainedClient(None if algorithm == 'phmmer' else synthetic_payload('hmmscan'),
                                algorithm=algorithm, database=database)
        assignment = {'version': 'api_execution_assignment_v1', 'resource_id': 'ebi',
            'service': 'ebi_hmmer', 'subject_ref': target, 'algorithm': algorithm, 'database': database,
            'parameters': {}, 'page_size': 2, 'endpoint': 'usable_handoff', 'constraints': {}}
        factory = ExecutionServiceFactory({'ebi': {'kind': 'hmmer_api'}}, {}, 3, 2, .5)
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')

        class Choices:
            def __init__(self):
                self.root_count = self.api_count = 0
                self.contexts, self.result_episode_ids = [], []
                self.handoff = None
                self.first_return = None

            async def complete(self, episode_id, role, instructions, context, schema):
                self.contexts.append((episode_id, instructions, deepcopy(context)))
                assert context.get('feedback') is None, context.get('feedback')
                execution = context.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    assert context['execution_resource_capabilities'][0]['resource_id'] == 'ebi'
                    return child('launch_api', assignment, scope, handoff_form)
                if execution.get('version') == 'api_execution_assignment_v1':
                    assert execution == assignment
                    tool = ['api.hmmer.prepare', 'api.hmmer.submit', 'api.hmmer.check_handoff'][self.api_count]
                    self.api_count += 1
                    return selected(tool)
                if execution.get('version') == 'execution_results_assignment_v1':
                    assert execution['handoff_ref'] == self.handoff
                    assert execution['selector'] == {'page': 1}
                    actual_tool = next(t for t in context['tools'] if t['name'] == 'api.hmmer.result')
                    assert actual_tool['description'] == RESULT_DESCRIPTION
                    assert actual_tool['knowledge_entry_ids'] == ['hmmer-api-numerical-results']
                    self.result_episode_ids.append(episode_id)
                    return selected('api.hmmer.result')
                self.root_count += 1
                if self.root_count == 1:
                    assert 'api.hmmer.result' not in {t['name'] for t in context['tools']}
                    return child('launch', launch_assignment({'ebi': assignment}), scope, handoff_form)
                if self.root_count == 2:
                    received = context['child_reports'][-1]
                    assert received['completed'] is True
                    self.handoff, = received['references']
                else:
                    self.first_return = deepcopy(context['child_reports'][-1])
                    assert self.first_return['completed']
                    observed = [r for r in self.first_return['references']
                                if store.get(r)['record_type'] == 'observation']
                    assert len(observed) == expected_domains
                    assert set(observed) <= set(context['visible_record_refs'])
                    assert any(numeric(store, r).get('paired_positions') == expected_pairs for r in observed)
                    for reference in observed:
                        values = numeric(store, reference)
                        assert values['query_coverage'] == values[
                            'sequence_span_coverage' if algorithm == 'hmmscan' else 'model_span_coverage']
                        assert values['target_coverage'] == values[
                            'model_span_coverage' if algorithm == 'hmmscan' else 'sequence_span_coverage']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': {'page': 1}}, scope, result_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, ToolRegistry(store, clients=client), choices, tmp_path/'run',
            'hmmer-grading-typed-api', controller_factory=fixture_controller, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=('launch', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        episode = workflow.build('annotation', 'root', 'Obtain the selected original HMMER domain measurements', scope)
        async def run():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record
        record = asyncio.run(run())
        archived = json.loads(''.join(iter_json(record.as_record())))
        launch_record = archived['units'][0]['child']
        api_record = launch_record['units'][0]['child']
        first, second = [u['child'] for u in archived['units'][1:]]
        assert record.units_consumed == 3 and launch_record['units_consumed'] == 1
        assert api_record['units_consumed'] == 3
        assert first['units_consumed'] == second['units_consumed'] == 1
        for child_record in (launch_record, api_record, first, second):
            assert child_record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert first['units'][-1]['controller_step']['marginal_credit'] > 0
        assert second['units'][-1]['controller_step']['marginal_credit'] == 0
        assert [c[0] for c in client.calls] == ['submit', 'status', 'result', 'result']
        assert len(choices.contexts) == 9  # 3 parent + 1 launch + 3 API + 2 results decisions
        assert len(store.list('observation')) == expected_domains
        assert not store.current_annotations()
        for completed, count in ((record.as_record(), 3), (launch_record, 1), (api_record, 3),
                                 (first, 1), (second, 1)):
            episode_id = completed['episode_id']
            n = store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=? AND episode_id=?',
                (workflow.run_id, episode_id)).fetchone()[0]
            assert n == count
        returned = [json.loads(workflow.journal.row('runtime_forms', r['episode_id'])['form']) for r in (first, second)]
        assert returned[0]['references'] == returned[1]['references'] == choices.first_return['references']
        root_refs = set(workflow.receipts.known(archived['episode_id']))
        assert set(returned[0]['references']) <= root_refs
        observations = [store.get(r) for r in returned[0]['references'] if store.get(r)['record_type'] == 'observation']
        assert all(o['subject_refs'] == [target] for o in observations)
        assert all(any(m['value']['type'] == 'number' for m in o['measurements']) for o in observations)
        # New grading data remains auxiliary custody. It is not an automatic
        # raw sheet/alignment dump into the parent's next decision.
        serialized = json.dumps(choices.contexts)
        for forbidden in ('hmmer_search_sheet_v1', 'hmmer_search_scores_v1',
                          'domain_bias_nats', 'peghhgnavlsrypiehyenrdvsvdgaekrgvlycrivppmtgkaihvmcvhlg.'):
            assert forbidden not in serialized
        before = [tuple(row) for row in store.db.execute('SELECT episode_id,unit_index,observation FROM runtime_observations ORDER BY episode_id,unit_index')]
        # Reopening the same persisted action is an exact replay, not another
        # selected action. Exercise the actual family adapter without a model.
        action = store.db.execute("SELECT * FROM api_execution_actions WHERE name='api.hmmer.result' ORDER BY rowid LIMIT 1").fetchone()
        manifest = store.db.execute('SELECT * FROM api_execution_episodes WHERE run_id=? AND episode_id=?',
            (workflow.run_id, action['episode_id'])).fetchone()
        api = workflow.progress_provider.job_provider.targets.api_execution
        original_context = BindingContext(workflow.run_id, action['episode_id'], 'results',
            (('results', 'replay'),), json.loads(manifest['scope']), json.loads(manifest['assignment']), {})
        replay = asyncio.run(api.execute(original_context, 'api.hmmer.result', {}, action['operation_key']))
        assert replay == json.loads(action['result'])
        assert_span_aliases_equal_shared(store, replay, algorithm)
        assert set(r['id'] for r in observations) <= set(replay['record_refs'])
        assert [tuple(row) for row in store.db.execute('SELECT episode_id,unit_index,observation FROM runtime_observations ORDER BY episode_id,unit_index')] == before
        assert len(client.calls) == 4


def test_actual_catalog_metadata_and_substantive_results_instructions_agree(tmp_path):
    library = ToolKnowledge.freeze(tmp_path/'instructions')
    result = library.execute('knowledge.search', {'query': 'hmmer api', 'offset': 0, 'limit': 10})
    entry = next(e for e in result['result']['entries'] if e['entry_id'] == 'hmmer-api-numerical-results')
    assert entry['tool_names'] == ['api.hmmer.result'] and entry['resource_kinds'] == ['api']
    assert entry['title'] and 'phmmer/hmmscan' in entry['summary']
    read = library.execute('knowledge.read', {'entry_id': entry['entry_id'],
        'section_id': 'numerical-results', 'offset': 0, 'limit': 200})
    assert read['status'] == 'completed' and read['record_refs'] == []
    assert read['result']['next_query'] is None
    text = read['result']['text']
    for phrase in ('api.hmmer.result', 'consensus_identity_fraction', 'api_identity_fraction',
                   'sequence_identity_fraction', 'ln(2)', 'paired', 'page', 'original'):
        assert phrase in text
    with Store(tmp_path/'state') as store:
        _, _, _, result_owner = receiver(store)
        actual, = result_owner.api.catalog(result_owner.context)
        assert actual['name'] in entry['tool_names']
        assert actual['description'] == RESULT_DESCRIPTION
        assert actual['input_schema']['properties'] == {}


@pytest.mark.parametrize('field,value', [('id', '00000000-0000-4000-8000-000000000000'),
    ('algo', 'hmmscan'), ('database', 'swissprot')])
def test_result_original_identity_conflicts_never_become_received_measurements(field, value, tmp_path):
    body = json.loads(PAGE1.read_bytes())
    body['result']['stats'][field] = value
    with Store(tmp_path) as store:
        _, _, _, result_owner = receiver(store, body=body)
        outcome = result_owner.act('api.hmmer.result')
        assert outcome['status'] == 'failed'
        assert outcome['feedback']['code'] == 'remote_identity_conflict_' + field
        assert outcome['record_refs'] == [] and not store.list('observation')
        assert result_owner.api.facts(result_owner.context, {})['execution_result_refs'] == []


def test_handoff_rejects_different_original_query_even_when_length_matches(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence=QUERY, molecule='protein')
        client = RetainedClient()
        owner = APIHarness(ToolRegistry(store, clients=client), database='pdb')
        assert owner.act('api.hmmer.submit')['status'] == 'completed'
        actual_status = client.hmmer_status
        def wrong_query(job):
            snapshot = actual_status(job)
            body = json.loads(snapshot.content)
            body['input'] = '>synthetic_wrong_query\n' + 'Y'*len(QUERY)
            return replace(snapshot, content=json.dumps(body).encode())
        client.hmmer_status = wrong_query
        outcome = owner.act('api.hmmer.check_handoff')
        assert outcome['status'] == 'failed' and outcome['feedback']['code'] == 'remote_identity_conflict_input'
        assert owner.api.facts(owner.context, {})['execution_handoff_refs'] == []
        assert not store.list('observation')


def test_receiver_rejects_wrong_scope_run_and_unrelated_reference(tmp_path):
    with Store(tmp_path) as store:
        tools, _, _, result_owner = receiver(store)
        outcome = result_owner.act('api.hmmer.result')
        ref = domain_refs(outcome)[1]
        scope = plain(result_owner.context.scope)
        parent = BindingContext(result_owner.context.run_id, 'parent', 'annotation',
            (('annotation', 'parent'),), scope, {}, {})
        assert result_owner.api.resolve(parent, ref, 'execution_result')
        assert not result_owner.api.resolve(replace(parent, run_id='other-run'), ref, 'execution_result')
        assert not result_owner.api.resolve(parent, store.targets()[0]['id'], 'execution_result')
        source = store.get(outcome['result']['source_ref'])
        assert not result_owner.api.resolve(parent, source['auxiliary_artifact_refs'][0], 'execution_result')
        # Empty/foreign scope must not grant access to this acquired target.
        with pytest.raises(Exception):
            result_owner.api.read_result(ref, {'subject_refs': []})
        schema = form('execution_result_refs')
        facts = result_owner.api.facts(result_owner.context, {})
        # Use the service's constrained factual schema directly; a reference
        # that exists in Store is not necessarily this selected result.
        subset = {'type': 'object', 'properties': {'refs': schema['properties']['references']},
            'required': ['refs'], 'additionalProperties': False}
        with pytest.raises(Exception):
            result_owner.api.validate_report(result_owner.context,
                {'refs': facts['execution_result_refs'] + [store.targets()[0]['id']]}, subset)


def test_same_page_new_custody_has_no_inherited_gain_and_saved_observations_do_not_change(tmp_path):
    with Store(tmp_path) as store:
        tools, client, owner, result_owner = receiver(store)
        first = result_owner.act('api.hmmer.result')
        saved = [deepcopy(store.get(ref)) for ref in domain_refs(first).values()]
        original_snapshot = client.snapshot
        client.snapshot = lambda body: replace(original_snapshot(body), retrieved_at='2026-10-24T01:00:00+00:00')
        later = owner.results(first['result']['handoff_ref'], episode_id='later-results')
        second = later.act('api.hmmer.result')
        assert first['record_refs'] != second['record_refs']
        selection = later.received_selection(refs=first['record_refs']+second['record_refs'], initial=first['record_refs'])
        assert later.api.credit_view(later.context, selection)['credit'] == 0
        assert saved == [store.get(row['id']) for row in saved]
        assert source_tool_gradings(store, first['result']['source_ref'])[0]['scores']['domains'][1]['api_identity_fraction'] == 25/89
