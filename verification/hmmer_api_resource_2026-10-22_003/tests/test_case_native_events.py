"""Caller pins and production reconstruction for optional native notifications.

The existing constant-policy fixture supplies configuration only. No Episode
loop, controller, model transport or native job runs. Reconstruction inspects
the actual host before the recording provider's entry boundary.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import subprocess

import pytest

from method_loop import Episode
from method_loop.durable import DurableExecutionError, content_digest, validate_commission
from gene_annotation_episode import case_execution, episode_composition, independent_execution as independent
from gene_annotation_episode import providers, runtime
from gene_annotation_episode.case_execution import (
    PolicyBindings, _load_policy, prepare_case_run, prepared_case_bindings, run_prepared_case,
)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.homology_jobs import HomologyJobs, digest
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.runtime import TypedReportContract, Workflow, assemble_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_case_execution import PARAMETERS, POLICY, prepared


EVENTS = {'version': 'native_job_events_v1', 'resource_id': 'fixture-host'}
EVENT_POLICY = POLICY + '''
from dataclasses import replace
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices

LAST_POLICY = None
SETUP_HOSTS = []
_original_create_policy = create_policy

def fixture_setup(store, *, run_id, directory, job_episodes, resource_estimator):
    SETUP_HOSTS.append({'store': store, 'run_id': run_id, 'directory': directory,
        'jobs': job_episodes})
    return EpisodeApplicationServices([], {})

def create_policy(parameters):
    global LAST_POLICY
    LAST_POLICY = replace(_original_create_policy(parameters),
        native_job_events=parameters.get('native_job_events'),
        episode_service_factory=fixture_setup,
        episode_service_binding={'kind': 'fixture_native_notification_setup'})
    return LAST_POLICY
'''


def forbidden(*args, **kwargs):
    raise AssertionError('Caller notification checks must not execute work')


class UnusedProvider:
    complete = forbidden


class SavedRuntimeProvider(providers.ModelConnection):
    """Select the real known-root binding path without provider side effects."""

    def __init__(self):
        pass

    __aenter__ = __aexit__ = complete = release = forbidden


class BeforeRoot(Exception):
    pass


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    monkeypatch.setattr(Episode, 'run_async', forbidden)
    for name in ('__init__', 'observe', 'state'):
        monkeypatch.setattr(YieldController, name, forbidden)
    for name in ('submit', 'resume_start', 'status', 'check_handoff', 'receive'):
        monkeypatch.setattr(HomologyJobs, name, forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)


def case_fixture(tmp_path, *, enabled=True):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    policy_file.write_text(EVENT_POLICY)
    directory = tmp_path / 'run'
    manifest = prepare_case_run(case, directory, configuration)
    parameters = {**PARAMETERS, **({'native_job_events': deepcopy(EVENTS)} if enabled else {})}
    return {'case': case, 'workspace': case / 'workspace', 'directory': directory,
        'policy_file': policy_file, 'manifest': manifest, 'parameters': parameters}


def assert_idle(store, directory, *, episodes=0):
    assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == episodes
    for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations'):
        assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    assert store.count('annotation') == store.count('assessment') == 0
    jobs = HomologyJobs(directory / 'native-jobs')
    try:
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()


def persist_run(tmp_path, monkeypatch, *, enabled=True):
    saved = case_fixture(tmp_path, enabled=enabled)
    with monkeypatch.context() as patch:
        def stop(*args, **kwargs):
            raise BeforeRoot()
        patch.setattr(Workflow, 'build', stop)
        with pytest.raises(BeforeRoot):
            asyncio.run(run_prepared_case(saved['directory'], policy_file=saved['policy_file'],
                parameters=saved['parameters'], provider=SavedRuntimeProvider()))
    manifest = json.loads((saved['directory'] / 'run.json').read_text())
    saved['run_id'] = manifest.pop('run_id')
    saved['settings'] = manifest
    saved['runtime_binding'] = json.loads((saved['directory'] / 'episode-execution-binding.json').read_text())
    assert saved['runtime_binding']['settings_sha256'] == content_digest(manifest)
    assert saved['runtime_binding']['arguments']['kind'] == 'fixed_case'
    with Store(saved['workspace']) as store:
        assert json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0]) == manifest
        assert_idle(store, saved['directory'])
    return saved


def commission(saved):
    """Use real build/request records; never select, dispatch or run a child."""
    directory, settings = saved['directory'], saved['settings']
    with Store(saved['workspace']) as store, prepared_case_bindings(store, directory) as (_, options):
        workflow = assemble_workflow(store, build_tools(store, saved['manifest']['configuration']),
            UnusedProvider(), directory, saved['run_id'], settings,
            **{key: value for key, value in options.items() if key != 'binding_definitions'})
        scope = store.validate_scope({'subject_refs': [saved['manifest']['target_ref']]})
        parent = workflow.build('annotation', 'root', settings['goal'], scope)
        schema = obj({'finding': {'type': 'string', 'enum': ['unknown', 'qualified']}})
        contract = TypedReportContract('Return the originally requested qualification', schema,
            workflow.resolver(scope, grain='improvement'))
        child = workflow.build('improvement', 'caller_child', 'Inspect the assigned fixture question',
            scope, parent=parent.goal, parent_path=parent.source.path,
            contract=contract, initial={'finding': 'unknown'})
        spec = {'version': 'episode_commission_v1', 'handle': 'episode:caller_native_fixture',
            'operation_key': saved['run_id'] + ':caller_native_fixture', 'run_id': saved['run_id'],
            'parent': {'episode_id': parent.source.episode_id, 'goal_id': parent.goal.goal_id,
                'path': [list(part) for part in parent.source.path]},
            'child': {'episode_id': child.source.episode_id, 'role': 'improvement', 'key': child.key,
                'path': [list(part) for part in child.source.path],
                'request': child.request.as_record(), 'scope': scope},
            'input_versions': [{'reference': saved['manifest']['target_ref'], 'version': None,
                'content_sha256': content_digest(store.get(saved['manifest']['target_ref']))}],
            'runtime_binding': deepcopy(saved['runtime_binding']),
            'constraints': {'fixture_only': True}, 'resource_selection': None,
            'expectation_snapshot_refs': []}
        assert_idle(store, directory, episodes=2)
        saved['job_descriptor'] = deepcopy(options['job_episodes'].as_record())
    return validate_commission(spec)


def recording_provider(monkeypatch, *, before_entry=None):
    events = []

    class Provider:
        def __init__(self, *args, **kwargs):
            events.append(('constructed', None))

        async def __aenter__(self):
            if before_entry is not None:
                before_entry()
            events.append(('entered', None))
            return self

        async def __aexit__(self, *exception):
            events.append(('exited', None))

        async def release(self, episode_id):
            events.append(('released', episode_id))

        complete = forbidden

    monkeypatch.setattr(providers, 'ModelConnection', Provider)
    return events


@pytest.mark.parametrize('definition', [
    {}, [], False, 'native_job_events_v1', {'version': 'native_job_events_v1'},
    {'resource_id': 'fixture-host'}, {**EVENTS, 'version': 'native_job_events_v2'},
    {**EVENTS, 'resource_id': ''}, {**EVENTS, 'resource_id': '  '},
    {**EVENTS, 'resource_id': 1}, {**EVENTS, 'extra': True},
])
def test_policy_requires_exact_explicit_native_notification_definition(definition):
    binding = {'kind': 'fixture_unexecuted_policy'}
    with pytest.raises(ValueError, match='invalid_native_job_events_binding'):
        PolicyBindings(forbidden, forbidden, forbidden, forbidden, forbidden,
            binding, binding, binding, binding, binding, native_job_events=definition)


def test_native_notification_is_optional_without_invoking_policy_functions():
    binding = {'kind': 'fixture_unexecuted_policy'}
    legacy = PolicyBindings(forbidden, forbidden, forbidden, forbidden, forbidden,
        binding, binding, binding, binding, binding)
    assert legacy.native_job_events is None
    supplied = replace(legacy, native_job_events=deepcopy(EVENTS))
    assert supplied.native_job_events == EVENTS and legacy.native_job_events is None


def test_optional_policy_pin_restores_original_source_and_exact_definition(tmp_path):
    saved = case_fixture(tmp_path)
    policy, recorded = _load_policy(saved['directory'], saved['policy_file'], saved['parameters'], resume=False)
    assert policy.native_job_events == recorded['native_job_events'] == EVENTS
    assert recorded['native_job_events'] is not policy.native_job_events
    assert 'native_job_events' not in recorded['definitions']
    assert recorded['source_sha256'] == digest(saved['policy_file'])
    assert (saved['directory'] / recorded['snapshot_file']).read_bytes() == saved['policy_file'].read_bytes()
    marker = saved['directory'] / 'policy-binding.json'
    before = marker.read_bytes()
    saved['policy_file'].unlink()
    restored, replay = _load_policy(saved['directory'], None, None, resume=True)
    assert replay == recorded and marker.read_bytes() == before
    assert restored.native_job_events == EVENTS
    assert restored.episode_service_factory.__globals__['SETUP_HOSTS'] == []


@pytest.mark.parametrize('change', ['added', 'removed', 'version', 'resource'])
def test_policy_pin_rejects_changed_notification_before_overwrite(tmp_path, change):
    saved = case_fixture(tmp_path, enabled=change != 'added')
    _, recorded = _load_policy(saved['directory'], saved['policy_file'], saved['parameters'], resume=False)
    if change == 'added':
        recorded['native_job_events'] = deepcopy(EVENTS)
    elif change == 'removed':
        del recorded['native_job_events']
    else:
        recorded['native_job_events']['version' if change == 'version' else 'resource_id'] = 'replacement'
    marker = saved['directory'] / 'policy-binding.json'
    marker.write_text(json.dumps(recorded))
    before = marker.read_bytes()
    with pytest.raises(ValueError, match='restored_policy_definition_changed'):
        _load_policy(saved['directory'], None, None, resume=True)
    assert marker.read_bytes() == before


@pytest.mark.parametrize('enabled', [False, True], ids=['legacy_absent', 'enabled'])
def test_case_entrypoint_forwards_native_mode_and_preserves_caller_binding(tmp_path, monkeypatch, enabled):
    saved = case_fixture(tmp_path, enabled=enabled)
    calls = []

    async def capture(store, tools, **options):
        original = options['job_episodes']
        assert original.native_event_provider is None
        assert original.statistics.resource_id == EVENTS['resource_id']
        if enabled:
            assert options['native_job_events'] == EVENTS
            policy = options['episode_service_factory'].__globals__['LAST_POLICY']
            assert options['native_job_events'] is not policy.native_job_events
        else:
            assert 'native_job_events' not in options
        assert options['episode_service_factory'].__globals__['SETUP_HOSTS'] == []
        calls.append(deepcopy(original.as_record()))
        return {'fixture_boundary': True}

    monkeypatch.setattr(case_execution, 'run_workflow', capture)
    assert asyncio.run(run_prepared_case(saved['directory'], policy_file=saved['policy_file'],
        parameters=saved['parameters'], provider=UnusedProvider())) == {'fixture_boundary': True}
    marker = saved['directory'] / 'policy-binding.json'
    before = marker.read_bytes()
    saved['policy_file'].unlink()
    assert asyncio.run(run_prepared_case(saved['directory'], resume=True,
        provider=UnusedProvider())) == {'fixture_boundary': True}
    assert len(calls) == 2 and calls[0] == calls[1]
    assert marker.read_bytes() == before
    assert ('native_job_events' in json.loads(before)) is enabled


@pytest.mark.parametrize('enabled', [False, True], ids=['legacy_absent', 'enabled'])
def test_production_factory_restores_original_mode_and_host_before_provider_entry(tmp_path, monkeypatch, enabled):
    saved = persist_run(tmp_path, monkeypatch, enabled=enabled)
    spec = commission(saved)
    original_spec = deepcopy(spec)
    before = {name: (saved['directory'] / name).read_bytes()
        for name in ('run.json', 'case-launch.json', 'policy-binding.json')}
    saved['policy_file'].unlink()
    assemblies, compositions = [], []
    actual_assemble = runtime.assemble_workflow
    actual_compose = episode_composition.compose_episode_bindings

    def compose(*args, **kwargs):
        compositions.append(kwargs['job_episodes'])
        return actual_compose(*args, **kwargs)

    def assemble(*args, **kwargs):
        original = kwargs['job_episodes']
        descriptor = deepcopy(original.as_record())
        host = actual_assemble(*args, **kwargs)
        assert original.native_event_provider is None
        assert original.as_record() == descriptor == saved['job_descriptor']
        setup = kwargs['episode_service_factory'].__globals__['SETUP_HOSTS']
        assert len(setup) == 1
        assert setup[0]['jobs'] is compositions[-1] is host.job_episodes
        assert setup[0]['store'] is host.store
        assert setup[0]['run_id'] == saved['run_id']
        assert host.job_episodes.as_record() == descriptor
        assemblies.append((host, original))
        return host

    def before_entry():
        host, original = assemblies[-1]
        assert host.native_job_events == saved['settings'].get('native_job_events')
        assert host.execution_binding == original_spec['runtime_binding']
        assert host.run_id == original_spec['run_id']
        if enabled:
            assert host.job_episodes is not original
            assert host.native_event_information.backend is host.execution_backend
            assert host.native_event_information.jobs is host.job_episodes.jobs
            assert host.job_episodes.native_event_provider.as_record() == {
                'version': 'native_event_provider_v1',
                'execution_directory': str(host.execution_backend.root_directory),
                'run_id': spec['run_id'], 'resource_id': EVENTS['resource_id']}
        else:
            assert host.job_episodes is original
            assert host.native_event_information is host.native_event_recovery is None
        row = host.store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
            (spec['child']['episode_id'],)).fetchone()
        assert json.loads(row[0]) == original_spec['child']['request']
        assert_idle(host.store, saved['directory'], episodes=2)

    monkeypatch.setattr(episode_composition, 'compose_episode_bindings', compose)
    monkeypatch.setattr(runtime, 'assemble_workflow', assemble)
    events = recording_provider(monkeypatch, before_entry=before_entry)

    async def inspect():
        async with independent.open_commission(spec) as reconstructed:
            child = reconstructed['episode']
            assert child.request.as_record() == original_spec['child']['request']
            assert child.source.path == tuple(map(tuple, original_spec['child']['path']))
            assert reconstructed['context'].path == tuple(map(tuple, original_spec['parent']['path']))
            assert child.source.workflow is assemblies[-1][0]

    asyncio.run(inspect())
    assert events == [('constructed', None), ('entered', None),
        ('released', spec['child']['episode_id']), ('exited', None)]
    assert spec == original_spec
    assert spec['runtime_binding']['settings_sha256'] == content_digest(saved['settings'])
    assert ('native_job_events' in saved['settings']) is enabled
    assert {name: (saved['directory'] / name).read_bytes() for name in before} == before


@pytest.mark.parametrize('change', ['added', 'removed', 'version', 'resource'])
def test_common_runtime_rejects_changed_resume_mode_before_transport(tmp_path, monkeypatch, change):
    saved = persist_run(tmp_path, monkeypatch, enabled=change != 'added')
    events = recording_provider(monkeypatch)
    with Store(saved['workspace']) as store, prepared_case_bindings(store, saved['directory']) as (_, options):
        if change == 'added':
            options['native_job_events'] = deepcopy(EVENTS)
        elif change == 'removed':
            del options['native_job_events']
        else:
            options['native_job_events']['version' if change == 'version' else 'resource_id'] = 'replacement'
        error = ValueError if change == 'version' else runtime.WorkflowError
        message = ('invalid_native_job_events_binding' if change == 'version'
            else 'resumption_requires_original_native_job_events')
        with pytest.raises(error, match=message):
            asyncio.run(runtime.run_workflow(store, build_tools(store, saved['manifest']['configuration']),
                run_dir=saved['directory'], resume=True, **options))
        assert_idle(store, saved['directory'])
    assert events == [] and not (saved['directory'] / 'providers').exists()


@pytest.mark.parametrize('change', ['added', 'removed', 'version', 'resource'])
def test_worker_rejects_changed_mode_before_constructing_transport(tmp_path, monkeypatch, change):
    saved = persist_run(tmp_path, monkeypatch, enabled=change != 'added')
    spec = commission(saved)
    settings = deepcopy(saved['settings'])
    if change == 'added':
        settings['native_job_events'] = deepcopy(EVENTS)
    elif change == 'removed':
        del settings['native_job_events']
    else:
        settings['native_job_events']['version' if change == 'version' else 'resource_id'] = 'replacement'
    # Agreeing file/Store copies and an updated envelope isolate the worker's
    # actual restored-policy comparison rather than just testing digest failure.
    (saved['directory'] / 'run.json').write_text(json.dumps({'run_id': saved['run_id'], **settings}))
    with Store(saved['workspace']) as store:
        with store.transaction():
            store.db.execute('UPDATE runtime_runs SET settings=? WHERE run_id=?',
                (json.dumps(settings), saved['run_id']))
    spec['runtime_binding']['settings_sha256'] = content_digest(settings)
    events = recording_provider(monkeypatch)

    async def inspect():
        with pytest.raises(DurableExecutionError) as error:
            async with independent.open_commission(spec):
                pytest.fail('Changed caller mode reconstructed')
        assert error.value.failure['code'] == 'identity_conflict'
        assert error.value.failure['affected_refs'] == ['native_job_events']

    asyncio.run(inspect())
    assert events == [] and not (saved['directory'] / 'providers').exists()
    with Store(saved['workspace']) as store:
        assert_idle(store, saved['directory'], episodes=2)


def test_actual_caller_resource_mismatch_fails_before_host_or_provider_entry(tmp_path, monkeypatch):
    saved = case_fixture(tmp_path)
    saved['parameters']['native_job_events']['resource_id'] = 'different-resource'
    events = recording_provider(monkeypatch)
    with pytest.raises(ValueError, match='native_event_resource_binding_mismatch'):
        asyncio.run(run_prepared_case(saved['directory'], policy_file=saved['policy_file'],
            parameters=saved['parameters'], provider=UnusedProvider()))
    assert events == []
    with Store(saved['workspace']) as store:
        assert_idle(store, saved['directory'])
    assert json.loads((saved['directory'] / 'case-launch.json').read_text())['configuration'][
        'resource_id'] == EVENTS['resource_id']
