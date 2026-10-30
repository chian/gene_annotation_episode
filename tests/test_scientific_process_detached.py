"""Real scientific-mother subprocess composition; scientific policy is a fixture."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil

from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionStore, canonical
from gene_annotation_episode.domain import identity, obj
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.scientific_process_records import (
    scientific_digest, scientific_invocation_ref, selector_selection)
from gene_annotation_episode.scientific_process_reports import report_sources, validate_process_result
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from detached_workflow_fixture import (ControllerFactory, ScriptedProvider,
    gate_paths, parent_credit, until)
from scientific_process_worker_fixture import ScientificFixtureTools, child_credit, make_binding
from test_scientific_process_runtime import FORM, Scenario as LibraryScenario, workflow_tools


class Scenario:
    def __init__(self, path):
        self.workspace = path / 'workspace'
        with Store(self.workspace) as store:
            catalog = LibraryScenario(path, store, tools=ScientificFixtureTools(store))
            self.directory, self.library, self.source = catalog.directory, catalog.library, catalog.source
            self.scope = catalog.scope
        with Store(self.workspace) as store:
            descriptor = prepare_scientific_binding(run_directory=self.directory,
                source_directory=self.source, tool_catalog=ScientificFixtureTools(store).catalog(),
                child_roles=['scientific_process'])
        self.descriptors = [descriptor]
        self.form = deepcopy(FORM)
        self.form['properties']['approaches'] = report_sources(self.library, workflow_tools(catalog))[
            'scientific_process_results']['report_schema']
        self.form['required'].append('approaches')
        self.binding = make_binding(self.workspace, self.directory, self.descriptors)
        self.backend = DurableExecutionStore(self.directory / 'episode-execution')
        self.tasks, self.received = [], []
        self.original_selection = catalog.filled_selection(tools=("fixture.publish",))
        self.original_selector = selector_selection(self.original_selection)
        self.original_assignment = {'selection': self.original_selection,
            'evidence_refs': list(self.scope['subject_refs']),
            'constraints': {'target_only': True}, 'context': {'condition': 'fixture'}}
        self.helper_selections = {operation: catalog.selection(tools=(tool_name,))
            for operation, tool_name in [('publish_parent_source', 'fixture.publish'),
                                        ('read_returned_source', 'fixture.read')]}
        self.helper_form = obj({'sources': {'type': 'array', 'items': {
            'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
            'x-source': 'committed_record_refs'}})
        # Neither root composition nor the worker may depend on the research source.
        shutil.rmtree(self.source)

    def commission(self):
        return {'selection': {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': 'Resolve the scoped fixture alternatives using changing outcomes',
            'scope': self.scope, 'purpose': 'Return the selected qualification and actual source refs',
            'schema_json': canonical(self.form), 'initial_report_json': '{"status":"unresolved"}',
            'assignment': {**deepcopy(self.original_assignment),
                'selection': deepcopy(self.original_selector)}}, 'report_update': {}}

    def helper_commission(self, operation, references):
        return {'selection': {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': {'publish_parent_source': 'Publish the assigned independent fixture source',
                     'read_returned_source': 'Read the source returned by the original child'}[operation],
            'scope': self.scope, 'purpose': 'Return the actual source references from the selected operation',
            'schema_json': canonical(self.helper_form), 'initial_report_json': '{}',
            'assignment': {'selection': deepcopy(self.helper_selections[operation]),
                'evidence_refs': list(references), 'constraints': {'target_only': True},
                'context': {'fixture_operation': operation}}}, 'report_update': {}}

    async def run(self, provider):
        with Store(self.workspace) as store:
            return await run_workflow(store, ScientificFixtureTools(store), provider=provider,
                run_dir=self.directory, controller_factory=ControllerFactory(6),
                project_credit=parent_credit, project_child_credit=child_credit,
                execution_binding=self.binding, episode_binding_descriptors=self.descriptors,
                episode_record_receipts=True, initial_known_record_refs=[],
                binding_definitions={
                    'credit': {'kind': 'fixture_received_source_count',
                               'unit': 'one_distinct_received_fixture_source'},
                    'scientific_child_credit': {'kind': 'fixture_received_source_count',
                               'unit': 'one_distinct_received_fixture_source'},
                    'controller': {'kind': 'fixture_completed_action_stop', 'completed_actions': 6}})

    def spec(self, operation=None):
        with Store(self.workspace) as store:
            rows = [json.loads(row[0]) for row in store.db.execute('SELECT spec FROM runtime_commission_intents')]
            rows = [spec for spec in rows if spec['child']['request']['message'][
                'episode_assignment']['context'].get('fixture_operation') == operation]
            assert len(rows) == 1
            return rows[0]

    @staticmethod
    def observations(store, identity):
        return [json.loads(row[0]) for row in store.db.execute(
            'SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',
            (identity,))]

    async def parent_work_while_child_live(self, context):
        assert context['current_credit'] == 0 and context['child_reports'] == []
        pending = context['pending_work']['items']
        assert len(pending) == 1
        handle = pending[0]['handle']
        ready, release = gate_paths(self.directory, handle)
        await until(ready.exists)
        status = self.backend.status(handle)
        assert status['liveness'] == 'live' and not status['return_available']
        assert status['execution_identity']['pid'] != os.getpid()
        assert json.loads(ready.read_text())['pid'] == status['execution_identity']['pid']
        assert not release.exists()
        spec = self.spec()
        with Store(self.workspace) as store:
            assert self.observations(store, spec['parent']['episode_id']) == []
            assert self.observations(store, spec['child']['episode_id']) == []
        return self.helper_commission('publish_parent_source', self.scope['subject_refs'])

    async def helper_wait(self, context, operation):
        spec = self.spec(operation)
        pending = context['pending_work']['items']
        matching = [item for item in pending if item['handle'] == spec['handle']]
        assert len(matching) == 1 and not matching[0]['return_available']
        expected = 0 if operation == 'publish_parent_source' else 2
        assert context['current_credit'] == expected and len(context['child_reports']) == expected
        assert len(pending) == (2 if operation == 'publish_parent_source' else 1)
        ready, release = gate_paths(self.directory, spec['handle'])
        await until(ready.exists)
        status = self.backend.status(spec['handle'])
        assert status['liveness'] == 'live' and not status['return_available']
        assert status['execution_identity']['pid'] == json.loads(ready.read_text())['pid'] != os.getpid()
        assert not release.exists()
        return self.wait_for(spec['handle'])

    async def wait_for_parent_source(self, context):
        return await self.helper_wait(context, 'publish_parent_source')

    async def wait_for_source_read(self, context):
        return await self.helper_wait(context, 'read_returned_source')

    async def select_wait(self, context):
        pending = context['pending_work']['items']
        assert len(pending) == 1 and not pending[0]['return_available']
        assert context['current_credit'] == 1 and len(context['child_reports']) == 1
        assert set(context['child_reports'][0]) == {'sources'}
        assert len(context['child_reports'][0]['sources']) == 1
        handle = pending[0]['handle']
        with Store(self.workspace) as store:
            observations = self.observations(store, self.spec()['parent']['episode_id'])
            assert [row['decision_index'] for row in observations] == [2, 1]
            assert store.get(context['child_reports'][0]['sources'][0])['accession'] == 'parent_one'
        assert handle == self.spec()['handle']
        return self.wait_for(handle)

    def wait_for(self, handle):
        async def release_after_selected_wait():
            def selected_wait():
                with Store(self.workspace) as store:
                    return store.db.execute('SELECT 1 FROM episode_waits WHERE outcome IS NULL '
                        "AND json_extract(request,'$.condition.events[0].handle')=?", (handle,)).fetchone()
            await until(selected_wait)
            gate_paths(self.directory, handle)[1].write_text('parent-selected-wait\n')
        self.tasks.append(asyncio.create_task(release_after_selected_wait()))
        return {'selection': {'kind': 'wait', 'condition': {
            'version': 'event_condition_v1', 'events': [
                {'handle': handle, 'event': 'returned', 'after_cursor': 0}],
            'reconsider_at': None}}, 'report_update': {}}

    def use_original_form(self, context):
        assert context['pending_work']['items'] == []
        assert context['current_credit'] == 2
        assert len(context['child_reports']) == 2
        report, = [item for item in context['child_reports'] if 'approaches' in item]
        assert set(report) == {'status', 'sources', 'approaches'}
        assert report['status'] == 'qualified' and len(report['sources']) == 1
        result, = report['approaches']
        assert validate_process_result(result, library=self.library) == result
        assert result['selection'] == {
            **self.original_selector, 'version': 'scientific_process_selection_report_v1',
            'source_version': self.original_selector['version']}
        assert result['initial_credit'] == 0 and result['credit'] == 1
        assert result['origin_kind'] == 'ordinary_child'
        assert result['preparation_operation_ref'] is None
        assert result['completed_actions'] == 3
        # A custom fixture controller has no numerical yield projection. The
        # source copies that existing null; it does not estimate a replacement.
        assert result['episode_yield'] is None
        self.received.append(deepcopy(report))
        with Store(self.workspace) as store:
            assert store.get(report['sources'][0])['accession'] == 'child_one'
        # The parent selects a follow-up using the returned source, not child history.
        return self.helper_commission('read_returned_source', report['sources'])

    async def cleanup(self):
        # Timeouts/gates synchronize the test; no runtime continuation rule is changed.
        with Store(self.workspace) as store:
            exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_commission_intents'").fetchone()
            if exists:
                for row in store.db.execute('SELECT handle FROM runtime_commission_intents'):
                    gate_paths(self.directory, row[0])[1].write_text('fixture-cleanup\n')
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)


def test_detached_filled_process_preserves_request_iteration_and_own_action_accounting(tmp_path, monkeypatch):
    tests = Path(__file__).resolve().parent
    monkeypatch.setenv('PYTHONPATH', os.pathsep.join(filter(None, [str(tests), str(tests.parent),
        os.environ.get('PYTHONPATH')])))
    scenario = Scenario(tmp_path)

    async def exercise():
        provider = ScriptedProvider([scenario.commission(), scenario.parent_work_while_child_live,
            scenario.wait_for_parent_source, scenario.select_wait, scenario.use_original_form,
            scenario.wait_for_source_read])
        try:
            summary = await scenario.run(provider)
            await asyncio.gather(*scenario.tasks)
            spec = scenario.spec()
            status = scenario.backend.status(spec['handle'])
            assert status['return_available'] and status['lifecycle_state'] == 'admitted'
            returned = scenario.backend.load_return(spec['handle'], status['return_id'])
            assert returned['outcome'] == 'closed' and returned['failure'] is None
            return summary, provider, spec, returned
        finally:
            await scenario.cleanup()

    summary, provider, spec, returned = asyncio.run(exercise())
    assert summary['state'] == 'yielded' and summary['pending_handles'] == []
    assert summary['completed_actions'] == 6 and summary['credit'] == 2
    assert summary['scientific_completion'] == 'not_established_by_termination'
    assert len(provider.contexts) == 6
    assert all(not {'fixture.publish', 'fixture.read'}.intersection(
        entry['name'] for entry in context['tools']) for context in provider.contexts)
    assert returned['completion']['units_consumed'] == 3
    assert returned['form'] == scenario.received[0]
    request = spec['child']['request']
    assert request['message']['episode_assignment'] == scenario.original_assignment
    assert request['report_contract']['measurements']['schema'] == scenario.form
    assert request['message']['scientific_invocation_ref'] == scientific_invocation_ref(
        spec['run_id'], spec['child']['path'])
    assert spec['runtime_binding'] == scenario.binding
    filled = request['message']['scientific_process']
    assert filled['selection'] == scenario.original_selection
    assert filled['assignment_sha256'] == scientific_digest(scenario.original_assignment)
    assert filled['invocation_sha256'] == scientific_digest({
        'objective': request['goal']['objective'], 'scope': scenario.scope,
        'purpose': request['report_contract']['decision'], 'report_schema': scenario.form,
        'initial_report': {'status': 'unresolved'}})
    assert filled['mechanics_binding'] == scenario.descriptors[0]
    assert all(operand['reference'].startswith('input_') for operand in spec['input_versions'])
    reconstruction = json.loads((scenario.directory / 'scientific-worker-reconstruction.json').read_text())
    assert reconstruction['request'] == request
    assert reconstruction['library'] == scenario.library.as_record()
    assert reconstruction['descriptor'] == scenario.descriptors[0]
    assert reconstruction['descriptor']['configuration']['tool_library'] == scenario.descriptors[0]['configuration']['tool_library']
    assert reconstruction['pid'] != os.getpid()
    assert not scenario.source.exists()

    calls = [json.loads(line) for line in
        (scenario.directory / 'scientific-worker-calls.jsonl').read_text().splitlines()]
    assert len(calls) == 3 and {row['pid'] for row in calls} == {reconstruction['pid']}
    assert all(row['episode_id'] == spec['child']['episode_id'] for row in calls)
    frames = [row['context']['scientific_process'] for row in calls]
    assert [frame['thought_pattern']['id'] for frame in frames] == ['P01', 'P01', 'P01']
    assert [[entry['name'] for entry in frame['child_tool_info']] for frame in frames] == [['fixture.publish']] * 3
    assert all(frame['child_tool_info'] == scenario.original_selection['child_tool_info'] for frame in frames)
    assert all(frame['selection'] == scenario.original_selector for frame in frames)
    assert all('revision' not in frame and 'revision_decision_index' not in frame for frame in frames)
    assert all(frame['assignment'] == {**scenario.original_assignment,
        'selection': scenario.original_selector} for frame in frames)
    assert calls[1]['context']['last_local_outcome']['result']['label'] == 'child_one'
    assert calls[2]['context']['last_local_outcome']['record_refs'] == []
    for field in ('episode_archive', 'result_archive', 'facts_archive'):
        descriptor = returned[field]
        assert ArchivedRecord(scenario.directory / 'archive' / descriptor['file'],
            descriptor['sha256'], descriptor['index_sha256']).load()
    with Store(scenario.workspace) as store:
        root_id, child_id = spec['parent']['episode_id'], spec['child']['episode_id']
        parent_observations = scenario.observations(store, root_id)
        child_observations = scenario.observations(store, child_id)
        assert [row['decision_index'] for row in parent_observations] == [2, 1, 3, 0, 5, 4]
        assert [row['step']['delta'] for row in parent_observations] == [0, 1, 0, 1, 0, 0]
        assert [row['decision_index'] for row in child_observations] == [0, 1, 2]
        assert [row['step']['delta'] for row in child_observations] == [1, 0, 0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 11
        outcomes = [json.loads(row[0]) for row in store.db.execute('SELECT result FROM runtime_actions '
            'WHERE episode_id=? ORDER BY decision_index', (child_id,))]
        assert len(outcomes) == 3 and outcomes[0]['changed_record_refs'] == returned['form']['sources']
        assert all(row['record_refs'] == row['changed_record_refs'] == [] for row in outcomes[1:])
        preparation = outcomes[1]
        assert preparation == calls[2]['context']['last_local_outcome']
        arguments = {'thought_pattern': scenario.library.reference('P77'),
            'child_tool_info': []}
        assert preparation['operation_ref'] == identity('operation', {
            'key': f'{spec["run_id"]}:{child_id}:1', 'name': 'process.revise', 'arguments': arguments})
        assert preparation['result'] == {
            'version': 'scientific_process_child_selection_v1',
            'parent_selection_sha256': scientific_digest(scenario.original_selection),
            'selection': {**scenario.original_selection, **arguments}}
        assert preparation['revision_origin'] == {
            'version': 'scientific_process_revision_origin_v1',
            'parent_invocation_ref': request['message']['scientific_invocation_ref'],
            'preparation_operation_ref': preparation['operation_ref']}
        frozen_facts = json.loads(store.db.execute('SELECT facts FROM runtime_forms WHERE episode_id=?',
            (child_id,)).fetchone()[0])
        process_result, = returned['form']['approaches']
        assert frozen_facts['scientific_process_results'] == [process_result]
        assert process_result['invocation_ref'] == request['message']['scientific_invocation_ref']
        assert process_result['parent_invocation_ref'] == scientific_invocation_ref(
            spec['run_id'], spec['parent']['path'])
        assert process_result['credit'] == frozen_facts['credit'] == 1
        assert process_result['episode_yield'] == frozen_facts['episode_yield'] is None
        assert process_result['credit_kind'] == 'scientific'
        assert process_result['credit_binding_ref'].startswith('scientific_credit_binding_')
        # Preparing an alternative did not create or return a revision episode.
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 4
        assert not store.list('observation') and not store.list('assessment')
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 3
        waits = [json.loads(row[0]) for row in store.db.execute('SELECT outcome FROM episode_waits')]
        assert len(waits) == 3
        assert all(wait['wake_reason'] == 'returned' and wait['measured_duration_seconds'] >= 0
                   for wait in waits)
        assert json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
            (child_id,)).fetchone()[0]) == request
        for operation, initial, gain, label in [('publish_parent_source', 0, 1, 'parent_one'),
                                               ('read_returned_source', 2, 0, 'child_one')]:
            helper = scenario.spec(operation)
            helper_id, helper_handle = helper['child']['episode_id'], helper['handle']
            status = scenario.backend.status(helper_handle)
            assert status['return_available'] and status['lifecycle_state'] == 'admitted'
            helper_return = scenario.backend.load_return(helper_handle, status['return_id'])
            assert helper_return['outcome'] == 'closed' and helper_return['failure'] is None
            assert helper_return['completion']['units_consumed'] == 1
            assert set(helper_return['form']) == {'sources'} and len(helper_return['form']['sources']) == 1
            source, = helper_return['form']['sources']
            assert store.get(source)['accession'] == label
            helper_observations = scenario.observations(store, helper_id)
            assert [row['decision_index'] for row in helper_observations] == [0]
            assert [row['step']['delta'] for row in helper_observations] == [gain]
            helper_outcomes = [json.loads(row[0]) for row in store.db.execute(
                'SELECT result FROM runtime_actions WHERE episode_id=?', (helper_id,))]
            assert len(helper_outcomes) == 1 and helper_outcomes[0]['record_refs'] == [source]
            if operation == 'read_returned_source':
                assert helper_return['form']['sources'] == returned['form']['sources']
                assert helper_outcomes[0]['changed_record_refs'] == []
                assert helper_outcomes[0]['result']['records'] == [store.get(source)]
            else:
                assert helper_outcomes[0]['changed_record_refs'] == [source]
            helper_request = helper['child']['request']
            assert helper_request['report_contract']['measurements']['schema'] == scenario.helper_form
            assert json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
                (helper_id,)).fetchone()[0]) == helper_request
            helper_reconstruction = json.loads((scenario.directory / (
                'scientific-helper-reconstruction-' + helper_handle + '.json')).read_text())
            assert helper_reconstruction['request'] == helper_request
            assert helper_reconstruction['library'] == scenario.library.as_record()
            assert helper_reconstruction['descriptor'] == scenario.descriptors[0]
            assert helper_reconstruction['pid'] != os.getpid()
            helper_calls = [json.loads(line) for line in (scenario.directory / (
                'scientific-helper-calls-' + helper_handle + '.jsonl')).read_text().splitlines()]
            assert len(helper_calls) == 1
            assert helper_calls[0]['pid'] == helper_reconstruction['pid']
            assert helper_calls[0]['episode_id'] == helper_id
            assert helper_calls[0]['context']['current_credit'] == initial
            helper_retirement = json.loads((scenario.directory / (
                'scientific-retired-' + helper_handle + '.json')).read_text())
            assert helper_retirement['active_controllers'] == helper_retirement['active_episodes'] == 0
            assert set(helper_retirement['released']) == {helper_id}
    retirement = json.loads((scenario.directory / ('scientific-retired-' + spec['handle'] + '.json')).read_text())
    assert retirement['active_controllers'] == retirement['active_episodes'] == 0
    assert set(retirement['released']) == {spec['child']['episode_id']}
