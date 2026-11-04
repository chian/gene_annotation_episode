"""Real scientific-mother subprocess composition; scientific policy is a fixture."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil

from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionStore, canonical
from gene_annotation_episode.domain import identity
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.scientific_process_records import scientific_digest, scientific_invocation_ref
from gene_annotation_episode.scientific_process_reports import report_sources, validate_process_result
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from detached_workflow_fixture import (ControllerFactory, FixtureTools, ScriptedProvider,
    child_credit, gate_paths, parent_credit, tool, until)
from scientific_process_worker_fixture import make_binding
from test_scientific_process_runtime import FORM, Scenario as LibraryScenario, workflow_tools


class Scenario:
    def __init__(self, path):
        self.workspace = path / 'workspace'
        with Store(self.workspace) as store:
            catalog = LibraryScenario(path, store, tools=FixtureTools(store))
            self.directory, self.library, self.source = catalog.directory, catalog.library, catalog.source
            self.scope = catalog.scope
        with Store(self.workspace) as store:
            descriptor = prepare_scientific_binding(run_directory=self.directory,
                source_directory=self.source, tool_catalog=FixtureTools(store).catalog(),
                child_roles=['scientific_process'])
        self.descriptors = [descriptor]
        self.form = deepcopy(FORM)
        self.form['properties']['approaches'] = report_sources(self.library, workflow_tools(catalog))[
            'scientific_process_results']['report_schema']
        self.form['required'].append('approaches')
        self.binding = make_binding(self.workspace, self.directory, self.descriptors)
        self.backend = DurableExecutionStore(self.directory / 'episode-execution')
        self.tasks, self.received = [], []
        self.original_selection = catalog.selection(tools=("fixture.publish",))
        self.original_assignment = {'selection': self.original_selection,
            'evidence_refs': list(self.scope['subject_refs']),
            'constraints': {'target_only': True}, 'context': {'condition': 'fixture'}}
        # Neither root composition nor the worker may depend on the research source.
        shutil.rmtree(self.source)

    def commission(self):
        return {'selection': {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': 'Resolve the scoped fixture alternatives using changing outcomes',
            'scope': self.scope, 'purpose': 'Return the selected qualification and actual source refs',
            'schema_json': canonical(self.form), 'initial_report_json': '{"status":"unresolved"}',
            'assignment': deepcopy(self.original_assignment)}, 'report_update': {}}

    async def run(self, provider):
        with Store(self.workspace) as store:
            return await run_workflow(store, FixtureTools(store), provider=provider,
                run_dir=self.directory, controller_factory=ControllerFactory(4),
                project_credit=parent_credit, project_child_credit=child_credit,
                execution_binding=self.binding, episode_binding_descriptors=self.descriptors,
                episode_record_receipts=True, initial_known_record_refs=[],
                binding_definitions={
                    'credit': {'kind': 'fixture_received_source_count',
                               'unit': 'one_distinct_received_fixture_source'},
                    'scientific_child_credit': {'kind': 'fixture_received_source_count',
                               'unit': 'one_distinct_received_fixture_source'},
                    'controller': {'kind': 'fixture_completed_action_stop', 'completed_actions': 4}})

    def spec(self):
        with Store(self.workspace) as store:
            rows = list(store.db.execute('SELECT spec FROM runtime_commission_intents'))
            assert len(rows) == 1
            return json.loads(rows[0][0])

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
        return tool('parent_one')

    async def select_wait(self, context):
        pending = context['pending_work']['items']
        assert len(pending) == 1 and not pending[0]['return_available']
        assert context['current_credit'] == 1 and context['child_reports'] == []
        handle = pending[0]['handle']
        with Store(self.workspace) as store:
            observations = self.observations(store, self.spec()['parent']['episode_id'])
            assert [row['decision_index'] for row in observations] == [1]
        async def release_after_selected_wait():
            def selected_wait():
                with Store(self.workspace) as store:
                    return store.db.execute('SELECT 1 FROM episode_waits WHERE outcome IS NULL').fetchone()
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
        assert len(context['child_reports']) == 1
        report = context['child_reports'][0]
        assert set(report) == {'status', 'sources', 'approaches'}
        assert report['status'] == 'qualified' and len(report['sources']) == 1
        result, = report['approaches']
        assert validate_process_result(result, library=self.library) == result
        assert result['selection'] == self.original_selection
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
        return {'selection': {'kind': 'tool', 'tool': 'fixture.read',
            'arguments': {'refs': report['sources']}}, 'report_update': {}}

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
            scenario.select_wait, scenario.use_original_form])
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
    assert summary['completed_actions'] == 4 and summary['credit'] == 2
    assert summary['scientific_completion'] == 'not_established_by_termination'
    assert len(provider.contexts) == 4
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
    assert [frame['thought']['id'] for frame in frames] == ['P01', 'P01', 'P01']
    assert [[entry['name'] for entry in frame['tools']] for frame in frames] == [['fixture.publish']] * 3
    assert all(frame['selection'] == scenario.original_selection for frame in frames)
    assert all('revision' not in frame and 'revision_decision_index' not in frame for frame in frames)
    assert all(frame['assignment'] == scenario.original_assignment for frame in frames)
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
        assert [row['decision_index'] for row in parent_observations] == [1, 2, 0, 3]
        assert [row['step']['delta'] for row in parent_observations] == [1, 0, 1, 0]
        assert [row['decision_index'] for row in child_observations] == [0, 1, 2]
        assert [row['step']['delta'] for row in child_observations] == [1, 0, 0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 7
        outcomes = [json.loads(row[0]) for row in store.db.execute('SELECT result FROM runtime_actions '
            'WHERE episode_id=? ORDER BY decision_index', (child_id,))]
        assert len(outcomes) == 3 and outcomes[0]['changed_record_refs'] == returned['form']['sources']
        assert all(row['record_refs'] == row['changed_record_refs'] == [] for row in outcomes[1:])
        preparation = outcomes[1]
        assert preparation == calls[2]['context']['last_local_outcome']
        arguments = {'thought_ref': scenario.library.reference('P77'),
            "tools": []}
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
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 2
        assert not store.list('observation') and not store.list('assessment')
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
        wait = json.loads(store.db.execute('SELECT outcome FROM episode_waits').fetchone()[0])
        assert wait['wake_reason'] == 'returned' and wait['measured_duration_seconds'] >= 0
        assert json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
            (child_id,)).fetchone()[0]) == request
    retirement = json.loads((scenario.directory / ('scientific-retired-' + spec['handle'] + '.json')).read_text())
    assert retirement['active_controllers'] == retirement['active_episodes'] == 0
    assert set(retirement['released']) == {spec['child']['episode_id']}
