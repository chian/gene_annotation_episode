"""Pinned engineering providers for detached native-progress consumer checks.

Only decisions, synchronization gates, explicit information units and controller
stops are fixtures. Every child runs an ordinary Workflow Episode in its own
durable worker; native status/logs come from the actual local phmmer registry.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

from method_loop import EpisodeCompletion
from method_loop.communication import ReportContract
from method_loop.durable import DurableExecutionError, canonical, content_digest, validate_commission
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices, service_binding
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, read_progress
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.homology_progress import HomologyProgressProvider
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.runtime import ReleasingContext, TypedReportContract, assemble_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from detached_workflow_fixture import FixtureController, until


VERSION = 'detached_native_progress_fixture_v1'
SERVICE_DEFINITION = {'fixture': VERSION, 'information_unit': .25,
    'log_window_bytes': 4096, 'log_roles': ['native_text', 'native_stderr']}
CONTROLLER_ACTIONS = {'annotation': 3, 'job_launch': 4, 'monitor_episode': 4, 'monitor_job': 2}


def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields),
            'additionalProperties': False}


def implementation_sha256():
    # This explicit caller binding pins its own immutable fixture. Concurrent
    # application implementation edits do not change this engineering identity.
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def make_binding(workspace, directory, jobs_directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    configuration = {'version': VERSION, 'workspace': str(Path(workspace).resolve()),
        'run_directory': str(directory), 'jobs_directory': str(Path(jobs_directory).resolve()),
        'services': SERVICE_DEFINITION, 'controller_actions': CONTROLLER_ACTIONS}
    path = directory / 'detached-progress-fixture.json'
    path.write_text(canonical(configuration) + '\n')
    return {'factory_module': 'detached_progress_fixture', 'factory_name': 'open_commission',
        'arguments': {'version': VERSION, 'configuration_file': str(path)},
        'implementation_sha256': implementation_sha256(),
        'settings_sha256': content_digest(configuration)}


def gates(directory, name):
    root = Path(directory) / 'progress-fixture-gates'
    root.mkdir(exist_ok=True)
    return root / (name + '.ready.json'), root / (name + '.release')


class SavedProgressReader:
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id

    def read_progress(self, reference, scope):
        return read_progress(self.store, self.run_id, reference, scope)


def application_services(store, *, run_id, directory, job_episodes, resource_estimator):
    """Bind literal services; acquire no progress and execute no selected work."""
    assert job_episodes is not None
    information = ProgressInformationCredit(SavedProgressReader(store, run_id),
        information_unit=SERVICE_DEFINITION['information_unit'])
    native = HomologyProgressProvider(store, job_episodes.jobs, run_id=run_id,
        log_window_bytes=SERVICE_DEFINITION['log_window_bytes'],
        log_roles=tuple(SERVICE_DEFINITION['log_roles']))
    return EpisodeApplicationServices([MonitorEpisodes(None).as_record()],
        {'monitor': {'definition': information.as_record(), 'project': information}}, native)


def operational_credit(store, *, role, assignment, episode_id, run_id):
    """Explicit zero operational fixture unit; no production score is selected."""
    return 0.0


def job_episodes(jobs):
    definition = {'fixture': VERSION, 'unit': 'zero_operational_fixture_credit'}
    return HomologyEpisodes(jobs, parser_policy=LocalJobPolicy(128 * 1024**2, 4 * 1024**2),
        credit_projector=operational_credit, credit_binding=definition,
        monitoring_projector=operational_credit, monitoring_binding=definition)


def received_refs(store, run_id, episode_id):
    return [row[0] for row in store.db.execute('SELECT progress_ref FROM runtime_progress_receipts '
        'WHERE run_id=? AND episode_id=? ORDER BY rowid', (run_id, episode_id))]


def parent_credit(store, scope):
    """Project only this parent's actual typed receipts through the real J unit."""
    row = store.db.execute('SELECT run_id,episode_id,path,request FROM runtime_episodes '
        'WHERE json_array_length(path)=1').fetchone()
    if row is None:
        return 0.0
    context = BindingContext(row['run_id'], row['episode_id'], 'annotation',
        tuple(tuple(part) for part in json.loads(row['path'])), scope, {}, json.loads(row['request']))
    return ProgressInformationCredit(SavedProgressReader(store, row['run_id']),
        information_unit=SERVICE_DEFINITION['information_unit'])(context, {
            'run_id': row['run_id'], 'episode_id': row['episode_id'],
            'initial_progress_refs': [], 'known_progress_refs': received_refs(
                store, row['run_id'], row['episode_id'])})


class ControllerFactory:
    def __call__(self, path, initial):
        role = path[-1][0]
        key = ('monitor_job' if len(path) == 3 else 'monitor_episode') if role == 'monitor' else role
        return FixtureController(path, initial, CONTROLLER_ACTIONS[key])


def binding_definitions():
    return {'credit': {'fixture': VERSION, 'unit': SERVICE_DEFINITION['information_unit'],
                       'meaning': 'real J projection over received typed progress only'},
            'controller': {'fixture': VERSION, 'completed_actions': CONTROLLER_ACTIONS}}


def monitor_schema():
    declarations = MonitorEpisodes(None).fact_sources('monitor')
    return obj({'interpretation': {'type': 'string', 'enum': [
                    'unresolved', 'native_observed', 'dependency_received']},
        **{field: declarations[source]['report_schema'] for field, source in {
            'progress': 'monitoring_progress_refs', 'target': 'monitoring_target_handle',
            'state': 'monitoring_execution_state', 'result_available': 'monitoring_result_available',
            'observed_at': 'monitoring_observed_at_unix_seconds',
            'dependencies': 'monitoring_dependency_handles'}.items()}})


def assignment(handle):
    return {'version': 'monitor_assignment_v1', 'target_handle': handle,
        'requested_fields': list(FIELDS), 'known_progress_refs': [],
        'permitted_committed_record_types': []}


def monitor(handle, scope, *, purpose):
    return {'selection': {'kind': 'episode_child', 'role': 'monitor',
        'assignment': assignment(handle), 'goal': purpose, 'scope': scope, 'purpose': purpose,
        'schema_json': canonical(monitor_schema()),
        'initial_report_json': canonical({'interpretation': 'unresolved'})}, 'report_update': {}}


def launch(query, scope):
    schema = obj({'job': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'homology_job', 'x-source': 'job_ref'},
        'cpu': {'type': 'integer', 'minimum': 1, 'x-source': 'job_cpu'},
        'handoff_state': {'type': 'string', 'enum': ['usable', 'unavailable'],
                          'x-source': 'job_handoff_state'}})
    return {'selection': {'kind': 'job_child', 'role': 'job_launch', 'query_ref': query,
        'cpu': 1, 'search_mode': 'native_defaults',
        'goal': 'Establish this actual assigned tiny native job and its handoff', 'scope': scope,
        'purpose': 'Return original assigned job identity and recorded handoff availability',
        'schema_json': canonical(schema), 'initial_report_json': '{}'}, 'report_update': {}}


def tool(name, arguments=None, *, interpretation=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments or {}},
        'report_update': {} if interpretation is None else {'interpretation': interpretation}}


def observe(*, interpretation=None):
    return tool('progress.observe', {'requested_fields': list(FIELDS)}, interpretation=interpretation)


def wait(handle):
    return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
        'events': [{'handle': handle, 'event': 'returned', 'after_cursor': 0}],
        'reconsider_at': None}}, 'report_update': {}}


class ChildProvider:
    """Scripted engineering choices inside one ordinary assigned Episode."""
    def __init__(self, store, jobs, spec, directory):
        self.store, self.jobs, self.spec, self.directory = store, jobs, spec, directory
        self.calls, self.released = 0, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING' and episode_id == self.spec['child']['episode_id']
        assert context['goal'] == self.spec['child']['request']['goal']
        assert context['scope'] == self.spec['child']['scope']
        index, self.calls = self.calls, self.calls + 1
        with (self.directory / ('progress-calls-' + self.spec['handle'] + '.jsonl')).open('a') as stream:
            stream.write(canonical({'pid': os.getpid(), 'episode_id': episode_id,
                'handle': self.spec['handle'], 'call_index': index, 'context': context}) + '\n')
        child_role = self.spec['child']['role']
        if child_role == 'job_launch':
            tools = ['homology.configure', 'homology.stage', 'homology.submit', 'homology.check_handoff']
            if index == 3:
                job = self.spec['child']['request']['message']['job_assignment']['job_ref']
                # A test readiness check, not an Episode action/cadence: the
                # physical job may finish while this owning Episode is live.
                native = await until(lambda: terminal(self.jobs, job))
                ready, release = gates(self.directory, 'target')
                ready.write_text(canonical({'pid': os.getpid(), 'handle': self.spec['handle'],
                    'episode_id': episode_id, 'job': job, 'native_status': native}) + '\n')
                await until(release.exists, timeout=45)
            return tool(tools[index])

        assert child_role == 'monitor'
        target = self.spec['child']['request']['message']['episode_assignment']['target_handle']
        if target.startswith('homology_job_'):
            if index == 1:
                assert len(context['monitor_received_progress_refs']) == 1
                assert context['current_credit'] == SERVICE_DEFINITION['information_unit']
                ready, release = gates(self.directory, 'native-monitor')
                ready.write_text(canonical({'pid': os.getpid(), 'handle': self.spec['handle'],
                    'episode_id': episode_id, 'progress': context['monitor_received_progress_refs']}) + '\n')
                await until(release.exists, timeout=45)
            assert index in (0, 1)
            return observe(interpretation='unresolved' if index == 0 else 'native_observed')

        if index == 0:
            return observe()
        if index == 1:
            snapshot = context['last_local_outcome']['result']
            dependency, = snapshot['dependencies']
            assert dependency['kind'] == 'job'
            return monitor(dependency['handle'], context['scope'],
                purpose='Return the selected native dependency observations through this original form')
        if index == 2:
            ready, _ = gates(self.directory, 'native-monitor')
            await until(ready.exists)
            deeper = json.loads(ready.read_text())
            assert context['child_reports'] == []
            assert not set(deeper['progress']) & set(context['monitor_received_progress_refs'])
            assert not set(deeper['progress']) & set(received_refs(self.store, self.spec['run_id'], episode_id))
            own = context['monitor_received_progress_refs']
            assert len(own) == 1
            assert read_progress(self.store, self.spec['run_id'], own[0])['target_handle'] == target
            (self.directory / 'outer-before-native-receipt.json').write_text(canonical({
                'episode_id': episode_id, 'received': own, 'deeper_progress': deeper['progress'],
                'current_credit': context['current_credit']}) + '\n')
            pending, = context['pending_work']['items']
            return wait(pending['handle'])
        assert index == 3
        report, = context['child_reports']
        assert report['target'].startswith('homology_job_') and report['state'] == 'returned'
        assert report['interpretation'] == 'native_observed'
        assert context['current_credit'] == 2 * SERVICE_DEFINITION['information_unit']
        reference, = report['progress']
        original = read_progress(self.store, self.spec['run_id'], reference, context['scope'])
        assert report['observed_at'] == datetime.fromisoformat(original['observed_at']).timestamp()
        return tool('progress.read', {'progress_ref': reference}, interpretation='dependency_received')

    async def release(self, episode_id):
        self.released.append(episode_id)


def terminal(jobs, job):
    value = jobs.status(job)
    return value if value['state'] == 'returned' else None


@asynccontextmanager
async def open_commission(spec):
    """Reconstruct exactly one original C1 child, without rebuilding a root."""
    spec = validate_commission(spec)
    binding = spec['runtime_binding']
    args = binding['arguments']
    if (binding['factory_module'] != 'detached_progress_fixture'
            or binding['factory_name'] != 'open_commission'
            or set(args) != {'version', 'configuration_file'} or args['version'] != VERSION
            or binding['implementation_sha256'] != implementation_sha256()):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    configuration = json.loads(Path(args['configuration_file']).read_text())
    if (binding['settings_sha256'] != content_digest(configuration)
            or configuration['services'] != SERVICE_DEFINITION
            or configuration['controller_actions'] != CONTROLLER_ACTIONS):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    directory = Path(configuration['run_directory'])
    with Store(configuration['workspace']) as store:
        from gene_annotation_episode.independent_execution import _check_assignment
        parent_goal, scope = _check_assignment(store, spec)
        saved_run = store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
            (spec['run_id'],)).fetchone()
        settings = json.loads(saved_run[0])
        assert settings['directory'] == str(directory)
        jobs = HomologyJobs(configuration['jobs_directory'])
        workflow = None
        try:
            episodes = job_episodes(jobs)
            assert episodes.as_record() == settings['job_episodes']
            provider = ChildProvider(store, jobs, spec, directory)
            workflow = assemble_workflow(store, ToolRegistry(store), provider, directory,
                spec['run_id'], settings, controller_factory=ControllerFactory(),
                project_credit=parent_credit, job_episodes=episodes, execution_binding=binding,
                episode_service_factory=application_services,
                episode_service_binding=SERVICE_DEFINITION)
            workflow.configure_execution(binding, execution_handle=spec['handle'])
            assert workflow.episode_application_services_binding == settings['episode_application_services'] == service_binding(application_services, SERVICE_DEFINITION)
            assert workflow.episode_bindings.as_record() == settings['episode_bindings']
            assert workflow.episode_job_progress_provider_binding == workflow.progress_provider.job_provider.as_record() == settings['episode_job_progress_provider']
            role_descriptor = settings['episode_role_credit_bindings']['monitor']
            assert role_descriptor['definition'] == plain(workflow.role_credit_definitions['monitor'])
            assert role_descriptor['projector'] == 'gene_annotation_episode.episode_progress_credit.ProgressInformationCredit'
            child = spec['child']
            original = ReportContract.from_record(child['request']['report_contract'])
            schema = original.as_record()['measurements']['schema']
            message = child['request']['message']
            assigned_job = message.get('job_assignment')
            contract = TypedReportContract(original.decision, schema,
                workflow.resolver(scope, grain=child['role'], assignment=assigned_job),
                lambda form: workflow.validate_report(form, scope, grain=child['role'],
                    assignment=assigned_job, schema=schema))
            episode = workflow.build(child['role'], child['key'], child['request']['goal']['objective'],
                scope, parent=parent_goal, parent_path=tuple(tuple(part) for part in spec['parent']['path']),
                contract=contract, initial=message['initial_report'], job_assignment=assigned_job,
                episode_assignment=message.get('episode_assignment'))
            assert episode.request.as_record() == child['request']
            context = ReleasingContext.from_commission(tree=workflow.tree, run_id=spec['run_id'],
                parent_path=spec['parent']['path'], parent_goal_id=parent_goal.goal_id,
                child_goal_id=episode.goal.goal_id, grain=child['role'], key=child['key'])
            workflow.context = context

            def pack_result(record, result):
                saved = workflow.journal.row('runtime_forms', child['episode_id'])
                facts = json.loads(saved['facts'])
                facts.pop('interpretations', None)
                return {'completion': EpisodeCompletion.from_record(record).as_record(),
                    'episode_archive': (record.archived_record or workflow.archive.store(record)).descriptor(),
                    'result_archive': workflow.archive.store(result).descriptor(),
                    'form': result.as_record()['form'], 'facts_archive': workflow.archive.store(facts).descriptor(),
                    'pending_handles': workflow.pending_handles(episode.source)}

            yield {'episode': episode, 'context': context, 'pack_result': pack_result}
        finally:
            if workflow is not None:
                await workflow.release(spec['child']['episode_id'])
                (directory / ('progress-retired-' + spec['handle'] + '.json')).write_text(canonical({
                    'episode_id': spec['child']['episode_id'], 'released': provider.released,
                    'active_controllers': len(workflow.context.runtime._controllers),
                    'active_episodes': len(workflow.context._active_episodes)}) + '\n')
            jobs.close()
