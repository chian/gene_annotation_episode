"""Source-pinned scripted providers for connected native-event evidence.

Decisions, gates, zero credit units and controller stops are engineering
fixtures. Workers execute the ordinary Workflow/shared Episode loop; the native
executable and systemd exit hook in the connected test are real.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from method_loop import EpisodeCompletion
from method_loop.durable import DurableExecutionError, canonical, content_digest, validate_commission
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.homology_progress import HomologyProgressProvider
from gene_annotation_episode.independent_execution import implementation_sha256 as application_sha256
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_event_information import report_sources
from gene_annotation_episode.runtime import ReleasingContext, assemble_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from detached_workflow_fixture import FixtureController, until


VERSION = 'native_event_worker_fixture_v1'
EVENT_MODE = {'version': 'native_job_events_v1', 'resource_id': 'native-event-fixture-local'}
SERVICE_DEFINITION = {'fixture': VERSION, 'credit': 'zero_explicit_fixture_units'}
CONTROLLER_ACTIONS = {'annotation': 5, 'job_launch': 4, 'monitor': 1}
POLICY = LocalJobPolicy(128 * 1024**2, 4 * 1024**2)


def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields),
            'additionalProperties': False}


def implementation_sha256():
    return content_digest({'application': application_sha256(),
        'fixture': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def make_binding(workspace, directory, jobs_directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    configuration = {'version': VERSION, 'workspace': str(Path(workspace).resolve()),
        'run_directory': str(directory), 'jobs_directory': str(Path(jobs_directory).resolve()),
        'native_job_events': deepcopy(EVENT_MODE), 'services': deepcopy(SERVICE_DEFINITION),
        'controller_actions': deepcopy(CONTROLLER_ACTIONS)}
    path = directory / 'native-event-fixture.json'
    path.write_text(canonical(configuration) + '\n')
    return {'factory_module': 'native_event_worker_fixture', 'factory_name': 'open_commission',
        'arguments': {'version': VERSION, 'configuration_file': str(path)},
        'implementation_sha256': implementation_sha256(),
        'settings_sha256': content_digest(configuration)}


def gates(directory, name):
    root = Path(directory) / 'native-event-fixture-gates'
    root.mkdir(exist_ok=True)
    return root / (name + '.ready.json'), root / (name + '.release')


def zero_science(store, scope):
    return 0.0


def zero_operational(store, *, role, assignment, episode_id, run_id):
    return 0.0


def zero_monitor(context, receiver_selection):
    return {'credit': 0.0}


def job_episodes(jobs):
    definition = {'fixture': VERSION, 'credit': 'zero_explicit_fixture_units'}
    return HomologyEpisodes(jobs, parser_policy=POLICY,
        credit_projector=zero_operational, credit_binding=definition,
        monitoring_projector=zero_operational, monitoring_binding=definition)


def application_services(store, *, run_id, directory, job_episodes, resource_estimator):
    assert job_episodes.native_event_provider is not None
    assert job_episodes.native_event_provider.resource_id == EVENT_MODE['resource_id']
    return EpisodeApplicationServices([MonitorEpisodes(None).as_record()],
        {'monitor': {'definition': SERVICE_DEFINITION, 'project': zero_monitor}},
        HomologyProgressProvider(store, job_episodes.jobs, run_id=run_id,
            log_window_bytes=256, log_roles=('native_text',)))


class ControllerFactory:
    def __call__(self, path, initial):
        return FixtureController(path, initial, CONTROLLER_ACTIONS[path[-1][0]])


def binding_definitions():
    return {'credit': {'fixture': VERSION, 'unit': 'zero_scientific_fixture_credit'},
            'controller': {'fixture': VERSION, 'completed_actions': CONTROLLER_ACTIONS}}


def target_schema():
    return report_sources()['native_event_targets']['report_schema']


def launch(query, scope, *, requested=True):
    schema = obj({'job': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'homology_job', 'x-source': 'job_ref'},
        **({'notifications': target_schema()} if requested else {})})
    return {'selection': {'kind': 'job_child', 'role': 'job_launch', 'query_ref': query,
        'cpu': 1, 'search_mode': 'native_defaults', 'goal': 'Establish the tiny assigned native job',
        'scope': scope, 'purpose': 'Return exact assigned job and requested notification metadata',
        'schema_json': canonical(schema), 'initial_report_json': '{}'}, 'report_update': {}}


def monitor(job, scope, target):
    schema = obj({'selected_target': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'native_event_target'}, 'notifications': target_schema()})
    return {'selection': {'kind': 'episode_child', 'role': 'monitor',
        'assignment': {'version': 'monitor_assignment_v1', 'target_handle': job,
            'requested_fields': list(FIELDS), 'known_progress_refs': [],
            'permitted_committed_record_types': []},
        'goal': 'Retain the original assigned job relationship while the parent decides',
        'scope': scope, 'purpose': 'Return only the requested original target metadata',
        'schema_json': canonical(schema),
        'initial_report_json': canonical({'selected_target': target})}, 'report_update': {}}


def tool(name, arguments=None, *, report_update=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments or {}},
            'report_update': report_update or {}}


def wait(handle, *, event='state_changed', after_cursor=0):
    return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
        'events': [{'handle': handle, 'event': event, 'after_cursor': after_cursor}],
        'reconsider_at': None}}, 'report_update': {}}


class ChildProvider:
    def __init__(self, spec, directory):
        self.spec, self.directory, self.calls, self.released = spec, directory, 0, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING' and episode_id == self.spec['child']['episode_id']
        assert context['goal'] == self.spec['child']['request']['goal']
        assert context['scope'] == self.spec['child']['scope']
        index, self.calls = self.calls, self.calls + 1
        with (self.directory / ('native-event-calls-' + self.spec['handle'] + '.jsonl')).open('a') as stream:
            stream.write(canonical({'pid': os.getpid(), 'episode_id': episode_id,
                'handle': self.spec['handle'], 'context': context}) + '\n')
        child_role = self.spec['child']['role']
        if child_role == 'job_launch':
            if index == 3:
                row, = context['native_event_targets']
                assert row['after_cursor'] == 0
                ready, release = gates(self.directory, 'launch')
                ready.write_text(canonical({'pid': os.getpid(), 'handle': self.spec['handle'],
                    'episode_id': episode_id, 'targets': context['native_event_targets']}) + '\n')
                await until(release.exists, timeout=45)
            return tool(('homology.configure', 'homology.stage', 'homology.submit',
                         'homology.check_handoff')[index])
        assert child_role == 'monitor' and index == 0
        row, = context['native_event_targets']
        assert row['after_cursor'] == 0  # Inheritance is independent of event head.
        assert row['target']['job_ref'] == self.spec['child']['request']['message']['episode_assignment']['target_handle']
        selected = self.spec['child']['request']['message']['initial_report']['selected_target']
        assert selected == row['target']['handle']
        ready, release = gates(self.directory, 'monitor')
        ready.write_text(canonical({'pid': os.getpid(), 'handle': self.spec['handle'],
            'episode_id': episode_id, 'targets': context['native_event_targets']}) + '\n')
        await until(release.exists, timeout=45)
        return tool('episode.history', {'view': 'index', 'offset': 0, 'limit': 1},
                    report_update={'selected_target': selected})

    async def release(self, episode_id):
        self.released.append(episode_id)


@asynccontextmanager
async def open_commission(spec):
    spec = validate_commission(spec)
    binding = spec['runtime_binding']
    args = binding['arguments']
    if (binding['factory_module'] != 'native_event_worker_fixture'
            or binding['factory_name'] != 'open_commission'
            or args.get('version') != VERSION
            or binding['implementation_sha256'] != implementation_sha256()):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    configuration = json.loads(Path(args['configuration_file']).read_text())
    if (binding['settings_sha256'] != content_digest(configuration)
            or configuration['native_job_events'] != EVENT_MODE
            or configuration['services'] != SERVICE_DEFINITION
            or configuration['controller_actions'] != CONTROLLER_ACTIONS):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    directory = Path(configuration['run_directory'])
    with Store(configuration['workspace']) as store:
        from gene_annotation_episode.independent_execution import _check_assignment
        parent_goal, scope = _check_assignment(store, spec)
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
            (spec['run_id'],)).fetchone()[0])
        assert settings['native_job_events'] == EVENT_MODE
        jobs = HomologyJobs(configuration['jobs_directory'])
        workflow = None
        try:
            episodes = job_episodes(jobs)
            provider = ChildProvider(spec, directory)
            workflow = assemble_workflow(store, ToolRegistry(store), provider, directory,
                spec['run_id'], settings, controller_factory=ControllerFactory(),
                project_credit=zero_science, job_episodes=episodes, execution_binding=binding,
                native_job_events=EVENT_MODE, episode_service_factory=application_services,
                episode_service_binding=SERVICE_DEFINITION)
            assert episodes.native_event_provider is None
            assert workflow.job_episodes is not episodes
            assert workflow.job_episodes.as_record() == settings['job_episodes']
            workflow.configure_execution(binding, execution_handle=spec['handle'])
            child, message = spec['child'], spec['child']['request']['message']
            contract = workflow.returned_request(spec).report_contract
            episode = workflow.build(child['role'], child['key'], child['request']['goal']['objective'],
                scope, parent=parent_goal, parent_path=tuple(tuple(part) for part in spec['parent']['path']),
                contract=contract, initial=message['initial_report'],
                job_assignment=message.get('job_assignment'), episode_assignment=message.get('episode_assignment'))
            assert episode.request.as_record() == child['request']
            context = ReleasingContext.from_commission(tree=workflow.tree, run_id=spec['run_id'],
                parent_path=spec['parent']['path'], parent_goal_id=parent_goal.goal_id,
                child_goal_id=episode.goal.goal_id, grain=child['role'], key=child['key'])
            workflow.context = context

            def pack_result(record, result):
                facts = json.loads(workflow.journal.row('runtime_forms', child['episode_id'])['facts'])
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
                (directory / ('native-event-retired-' + spec['handle'] + '.json')).write_text(canonical({
                    'released': provider.released, 'active_controllers': len(workflow.context.runtime._controllers),
                    'active_episodes': len(workflow.context._active_episodes)}) + '\n')
            jobs.close()
