"""Actual detached Workflow/native-progress consumer with recursive forms.

Scripted providers, gates, information units and controller stops are declared
engineering fixtures. The Store, C1-C4 worker execution, progress providers,
typed admission, J projection and tiny local phmmer execution are real.
"""
import asyncio
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionStore, canonical, content_digest
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, OUTPUTS, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.progress_records import JOB_STATUS_VERSION, validate_job_status
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from detached_workflow_fixture import ScriptedProvider, until
from detached_progress_fixture import (CONTROLLER_ACTIONS, SERVICE_DEFINITION, ControllerFactory,
    application_services, binding_definitions, gates, job_episodes, launch, make_binding,
    monitor, parent_credit, received_refs, tool, wait)


PROJECT = Path(__file__).resolve().parents[1]
PROGRAM = PROJECT / 'resources/software/infernal-1.1.5/hmmer/src/phmmer'
PROTEIN = 'MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE'


class Scenario:
    def __init__(self, path):
        self.workspace, self.directory = path / 'workspace', path / 'run'
        self.jobs_directory = path / 'jobs'
        database = path / 'tiny-reference.faa'
        database.write_text('>tiny_native_progress_reference\n' + PROTEIN + '\n')
        with Store(self.workspace) as store:
            store.create_problem(raw_sequence=PROTEIN, molecule='protein')
            self.query = store.targets()[0]['id']
            self.scope = store.validate_scope({'subject_refs': [self.query]})
        jobs = HomologyJobs.create(self.jobs_directory,
            executable=FileAsset(PROGRAM, digest(PROGRAM)),
            reference_database=FileAsset(database, digest(database)),
            policy=LocalJobPolicy(128 * 1024**2, 4 * 1024**2), max_cpu=1,
            search_modes=['native_defaults'])
        jobs.close()
        self.binding = make_binding(self.workspace, self.directory, self.jobs_directory)
        self.backend = DurableExecutionStore(self.directory / 'episode-execution')
        self.tasks = []

    async def run(self, provider, *, resume=False):
        with Store(self.workspace) as store:
            jobs = HomologyJobs(self.jobs_directory)
            try:
                return await run_workflow(store, ToolRegistry(store), provider=provider,
                    run_dir=self.directory, resume=resume, controller_factory=ControllerFactory(),
                    project_credit=parent_credit, job_episodes=job_episodes(jobs),
                    execution_binding=self.binding, binding_definitions=binding_definitions(),
                    episode_service_factory=application_services,
                    episode_service_binding=SERVICE_DEFINITION)
            finally:
                jobs.close()

    def specs(self):
        with Store(self.workspace) as store:
            return [json.loads(row[0]) for row in store.db.execute(
                'SELECT spec FROM runtime_commission_intents ORDER BY rowid')]

    def root(self, store):
        return dict(store.db.execute('SELECT * FROM runtime_episodes WHERE '
            'json_array_length(path)=1').fetchone())

    def observations(self, store, episode_id):
        return [json.loads(row[0]) for row in store.db.execute('SELECT observation '
            'FROM runtime_observations WHERE episode_id=? ORDER BY unit_index', (episode_id,))]

    async def target_live(self, context):
        ready, _ = gates(self.directory, 'target')
        await until(ready.exists)
        target = json.loads(ready.read_text())
        status = self.backend.status(target['handle'])
        assert status['execution_identity']['pid'] == target['pid'] != os.getpid()
        assert status['liveness'] == 'live' and status['lifecycle_state'] == 'executing'
        assert status['return_available'] is False
        assert target['native_status']['state'] == 'returned'
        assert target['native_status']['outcome'] == 'succeeded'
        assert context['child_reports'] == [] and context['current_credit'] == 0
        with Store(self.workspace) as store:
            root = self.root(store)
            assert self.observations(store, root['episode_id']) == []
            assert received_refs(store, root['run_id'], root['episode_id']) == []
        return monitor(target['handle'], self.scope,
            purpose='Return exact recursive progress while the assigned investigator remains live')

    async def selected_wait(self, context):
        ready, release = gates(self.directory, 'native-monitor')
        await until(ready.exists)
        boundary = self.directory / 'outer-before-native-receipt.json'
        await until(boundary.exists)
        native = json.loads(ready.read_text())
        assert context['current_credit'] == 0 and context['child_reports'] == []
        assert not any(reference in canonical(context) for reference in native['progress'])
        with Store(self.workspace) as store:
            root = self.root(store)
            assert received_refs(store, root['run_id'], root['episode_id']) == []
            assert self.observations(store, root['episode_id']) == []
            # Shared durable storage already contains the descendant facts;
            # storage visibility alone does not deliver them to an ancestor.
            saved = store.db.execute('SELECT snapshot FROM runtime_progress_observations '
                'WHERE progress_ref=?', (native['progress'][0],)).fetchone()
            assert saved is not None
            assert json.loads(saved[0])['execution_status']['version'] == JOB_STATUS_VERSION
        pending = {item['role']: item for item in context['pending_work']['items']}
        assert set(pending) == {'job_launch', 'monitor'}
        assert all(not item['return_available'] for item in pending.values())

        async def release_after_both_selected_waits():
            def selected():
                with Store(self.workspace) as store:
                    return store.db.execute('SELECT count(*) FROM episode_waits '
                        'WHERE outcome IS NULL').fetchone()[0] == 2
            await until(selected)
            release.write_text('both-original-waits-selected\n')
        self.tasks.append(asyncio.create_task(release_after_both_selected_waits()))
        return wait(pending['monitor']['handle'])

    def after_monitor_receipt(self, context):
        report, = context['child_reports']
        target = json.loads(gates(self.directory, 'target')[0].read_text())
        status = self.backend.status(target['handle'])
        assert status['liveness'] == 'live' and not status['return_available']
        assert report['target'] == target['handle'] and report['state'] == 'executing'
        assert report['result_available'] is False
        assert report['interpretation'] == 'dependency_received'
        assert report['dependencies'] == [target['job']]
        assert len(report['progress']) == 2
        assert context['current_credit'] == .5
        assert context['pending_work']['items'][0]['handle'] == target['handle']
        with Store(self.workspace) as store:
            root = self.root(store)
            assert received_refs(store, root['run_id'], root['episode_id']) == report['progress']
            assert [row['decision_index'] for row in self.observations(store, root['episode_id'])] == [2, 1]
        return tool('episode.history', {'view': 'records', 'decision_indices': [0]})

    async def returned(self, handle):
        await asyncio.wait_for(self.backend.wait_events({'version': 'event_condition_v1',
            'events': [{'handle': handle, 'event': 'returned', 'after_cursor': 0}],
            'reconsider_at': None}), 20)
        status = self.backend.status(handle)
        value = self.backend.load_return(handle, status['return_id'])
        if value['failure'] is not None:
            diagnostic = value['failure']['diagnostic_ref']
            raise AssertionError(Path(diagnostic).read_text() if diagnostic else value)
        assert value['outcome'] == 'closed'
        return value

    async def cleanup(self):
        # Release this test's selected work on every path. A yielded parent has
        # no cancellation side effect; tiny native work is allowed to finish.
        for name in ('target', 'native-monitor'):
            gates(self.directory, name)[1].write_text('fixture-cleanup\n')
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        returns = await asyncio.gather(*(self.returned(spec['handle']) for spec in self.specs()),
            return_exceptions=True)
        jobs = HomologyJobs(self.jobs_directory)
        try:
            for row in jobs.db.execute('SELECT job_ref,submission_requested FROM orders'):
                if row['submission_requested']:
                    await until(lambda: jobs.status(row['job_ref'])['state'] == 'returned')
        finally:
            jobs.close()
        for value in returns:
            if isinstance(value, BaseException):
                raise value


def body(store, reference):
    return json.loads(store.get_artifact(store.get(reference)['request_ref']))


def test_real_detached_recursive_native_progress_and_original_return_replay(tmp_path):
    scenario = Scenario(tmp_path)

    async def exercise():
        provider = ScriptedProvider([launch(scenario.query, scenario.scope), scenario.target_live,
            scenario.selected_wait, scenario.after_monitor_receipt])
        try:
            summary = await scenario.run(provider)
            await asyncio.gather(*scenario.tasks)
            specs = scenario.specs()
            assert len(specs) == 3
            target, outer, inner = specs
            assert [spec['child']['role'] for spec in specs] == ['job_launch', 'monitor', 'monitor']
            assert inner['parent']['episode_id'] == outer['child']['episode_id']
            assert target['parent'] == outer['parent']
            identities = {spec['handle']: scenario.backend.status(spec['handle'])['execution_identity']
                for spec in specs}
            assert len({identity['pid'] for identity in identities.values()}) == 3
            assert os.getpid() not in {identity['pid'] for identity in identities.values()}
            outer_return, inner_return = await asyncio.gather(
                scenario.returned(outer['handle']), scenario.returned(inner['handle']))
            assert scenario.backend.status(target['handle'])['liveness'] == 'live'
            assert summary['state'] == 'yielded_with_pending_work'
            assert summary['pending_handles'] == [target['handle']]
            assert summary['completed_actions'] == 3 and summary['credit'] == .5
            assert summary['scientific_completion'] == 'not_established_by_termination'
            assert len(provider.contexts) == 4

            with Store(scenario.workspace) as store:
                root = scenario.root(store)
                frozen_root = deepcopy(root)
                observations = deepcopy(scenario.observations(store, root['episode_id']))
                root_actions = [dict(row) for row in store.db.execute('SELECT * FROM runtime_actions '
                    'WHERE episode_id=? ORDER BY decision_index', (root['episode_id'],))]
                root_slots = [dict(row) for row in store.db.execute('SELECT * FROM runtime_completion_slots '
                    'WHERE episode_id=? ORDER BY sequence', (root['episode_id'],))]
                assert json.loads(root_actions[0]['result'])['status'] == 'pending'
                assert root_actions[0]['credit'] is None
                archive = json.loads(root['archive'])
                archive_path = scenario.directory / 'archive' / archive['file']
                archive_bytes = archive_path.read_bytes()
                assert [row['decision_index'] for row in observations] == [2, 1, 3]
                assert [row['step']['delta'] for row in observations] == [0, .5, 0]
                assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 2
                waits = [json.loads(row[0]) for row in store.db.execute('SELECT outcome FROM episode_waits')]
                assert len(waits) == 2 and all(value['wake_reason'] == 'returned' for value in waits)
                assert all(value['measured_duration_seconds'] >= 0 for value in waits)

            gates(scenario.directory, 'target')[1].write_text('parent-yield-preserves-descendant\n')
            target_return = await scenario.returned(target['handle'])
            returns = [target_return, outer_return, inner_return]
            for spec, returned in zip(specs, returns):
                assert returned['commission_sha256'] == content_digest(spec)
                assert spec['runtime_binding'] == scenario.binding
                assert spec['child']['scope'] == spec['child']['request']['message']['scope']
                assert spec['child']['request']['goal']['parent_goal_id'] == spec['parent']['goal_id']
                assert scenario.backend.start(spec['handle'])['execution_identity'] == identities[spec['handle']]
                assert scenario.backend.load_commission(spec['handle']) == spec
                assert scenario.backend.load_return(spec['handle'], returned['return_id']) == returned
                assert returned['completion']['units_consumed'] == CONTROLLER_ACTIONS[
                    'job_launch' if spec is target else 'monitor_episode' if spec is outer else 'monitor_job']
                calls = [json.loads(line) for line in (scenario.directory / (
                    'progress-calls-' + spec['handle'] + '.jsonl')).read_text().splitlines()]
                assert len(calls) == (2 if spec is inner else 4)
                assert {call['pid'] for call in calls} == {identities[spec['handle']]['pid']}
                assert {call['episode_id'] for call in calls} == {spec['child']['episode_id']}
                assert all(call['context']['goal'] == spec['child']['request']['goal']
                    and call['context']['scope'] == spec['child']['scope'] for call in calls)
                for field in ('episode_archive', 'result_archive', 'facts_archive'):
                    descriptor = returned[field]
                    assert ArchivedRecord(scenario.directory / 'archive' / descriptor['file'],
                        descriptor['sha256'], descriptor['index_sha256']).load()
                retirement = json.loads((scenario.directory / ('progress-retired-' + spec['handle'] + '.json')).read_text())
                assert retirement['active_controllers'] == retirement['active_episodes'] == 0
                assert set(retirement['released']) == {spec['child']['episode_id']}

            unused = ScriptedProvider([])
            assert await scenario.run(unused, resume=True) == summary
            assert unused.contexts == []
            with Store(scenario.workspace) as store:
                assert scenario.root(store) == frozen_root
                assert scenario.observations(store, root['episode_id']) == observations
                assert [dict(row) for row in store.db.execute('SELECT * FROM runtime_actions '
                    'WHERE episode_id=? ORDER BY decision_index', (root['episode_id'],))] == root_actions
                assert [dict(row) for row in store.db.execute('SELECT * FROM runtime_completion_slots '
                    'WHERE episode_id=? ORDER BY sequence', (root['episode_id'],))] == root_slots
                assert archive_path.read_bytes() == archive_bytes
                assert store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0] == 3
                assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 2
            return specs, returns, identities
        finally:
            await scenario.cleanup()

    specs, returns, identities = asyncio.run(exercise())
    target, outer, inner = specs
    target_return, outer_return, inner_return = returns
    assigned = target['child']['request']['message']['job_assignment']
    assert target_return['form'] == {'job': assigned['job_ref'], 'cpu': 1, 'handoff_state': 'usable'}
    assert scenario.backend.status(target['handle'])['lifecycle_state'] == 'returned'
    assert scenario.backend.status(outer['handle'])['lifecycle_state'] == 'admitted'
    assert scenario.backend.status(inner['handle'])['lifecycle_state'] == 'admitted'
    assert outer_return['form']['progress'][1:] == inner_return['form']['progress']

    with Store(scenario.workspace) as store:
        saved = {json.loads(row[0])['target_handle']: json.loads(row[0]) for row in store.db.execute(
            'SELECT snapshot FROM runtime_progress_observations')}
        assert set(saved) == {target['handle'], assigned['job_ref']}
        episode_progress, native_progress = saved[target['handle']], saved[assigned['job_ref']]
        assert episode_progress['execution_status']['version'] == 'execution_status_v1'
        assert episode_progress['execution_status']['lifecycle_state'] == 'executing'
        assert episode_progress['execution_status']['liveness'] == 'live'
        assert episode_progress['execution_status']['execution_identity'] == identities[target['handle']]
        assert native_progress['execution_status']['version'] == JOB_STATUS_VERSION
        status = validate_job_status(native_progress['execution_status'])
        native = status['native']
        assert native == json.loads(gates(scenario.directory, 'target')[0].read_text())['native_status']
        assert native['job_ref'] == assigned['job_ref'] and native['state'] == 'returned'
        assert native['native_returncode'] == 0 and native['outcome'] == 'succeeded'
        assert native['elapsed_seconds'] > 0 and native['duration_measure'] == 'systemd_service_wall_seconds'
        assert all(value['available'] and value['writer_closed'] for value in native['outputs'])
        assert native_progress['measurements'][0]['value'] == native['elapsed_seconds']
        assert native_progress['measurements'][0]['measured_at'] == status['observed_at']
        assert {value['name']: value['value'] for value in native_progress['measurements'][1:]} == {
            value['role'] + '_bytes': value['bytes'] for value in native['outputs']}
        assert native_progress['result_available'] is True
        assert native_progress['committed_record_refs'] == native_progress['dependencies'] == []
        assert native_progress['log_windows']
        for window in native_progress['log_windows']:
            metadata = body(store, window['source_ref'])
            retained = Path(metadata['path']).read_bytes()[
                metadata['original_start_byte']:metadata['original_end_byte']]
            assert store.get_artifact(window['artifact_ref']) == retained
            assert hashlib.sha256(retained).hexdigest() == window['content_sha256']
            assert metadata['whole_file_atomic_snapshot'] is False
            assert metadata['job_ref'] == assigned['job_ref']
            assert metadata['status_source_ref'] in native_progress['provenance_refs']
        relation, = episode_progress['dependencies']
        assert relation['handle'] == assigned['job_ref'] and relation['kind'] == 'job'
        assert relation['state'] == 'pending'  # Assignment fact is not a fresh native poll.
        relation_record = body(store, relation['relation_ref'])
        assert relation_record['commission_sha256'] == content_digest(target)
        assert relation_record['owner_episode_id'] == target['child']['episode_id']
        assert relation_record['query_ref'] == assigned['query_ref'] == scenario.query
        assert relation_record['cpu'] == assigned['cpu'] == 1
        assert relation_record['search_mode'] == assigned['search_mode'] == 'native_defaults'
        assert outer_return['form']['observed_at'] == datetime.fromisoformat(episode_progress['observed_at']).timestamp()
        assert inner_return['form']['observed_at'] == datetime.fromisoformat(native_progress['observed_at']).timestamp()
        assert inner_return['form']['progress'] == [native_progress['progress_ref']]

        expected = [(target, [0, 1, 2, 3], [0, 0, 0, 0]),
            (outer, [0, 2, 1, 3], [.25, 0, .25, 0]), (inner, [0, 1], [.25, 0])]
        for spec, indices, deltas in expected:
            episode_id = spec['child']['episode_id']
            observations = scenario.observations(store, episode_id)
            assert [value['decision_index'] for value in observations] == indices
            assert [value['step']['delta'] for value in observations] == deltas
            assert len({value['decision_index'] for value in observations}) == len(indices)
            actions = list(store.db.execute('SELECT decision_index FROM runtime_actions '
                "WHERE episode_id=? AND json_extract(result,'$.status') IN ('completed','partial')",
                (episode_id,)))
            assert {value[0] for value in actions} == set(indices)
            form = json.loads(store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?',
                (episode_id,)).fetchone()[0])
            assert form == returns[specs.index(spec)]['form']
        assert store.db.execute('SELECT count(*) FROM runtime_homology_progress_operations '
            "WHERE json_extract(result,'$.version')='progress_snapshot_v1'").fetchone()[0] == 2
        # The two native observe actions retained one C8 reference and timestamp.
        native_actions = [json.loads(row[0]) for row in store.db.execute('SELECT result '
            "FROM runtime_actions WHERE episode_id=? AND json_extract(action,'$.tool')='progress.observe'",
            (inner['child']['episode_id'],))]
        assert len(native_actions) == 2
        assert native_actions[0]['progress_refs'] == native_actions[1]['progress_refs'] == [native_progress['progress_ref']]
        assert native_actions[0]['result'] == native_actions[1]['result'] == native_progress
        assert not store.list('observation') and not store.list('assessment')
    jobs = HomologyJobs(scenario.jobs_directory)
    try:
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        native_text = (scenario.jobs_directory / assigned['job_ref'] / OUTPUTS['native_text']).read_text()
        assert 'phmmer' in native_text and '[ok]' in native_text
    finally:
        jobs.close()
