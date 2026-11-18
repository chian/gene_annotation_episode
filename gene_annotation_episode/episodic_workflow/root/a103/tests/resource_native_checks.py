"""Actual A103 job constructors/order/reopen with explicit controlled execution ports.

No subprocess, detached job or scientific search is run. No usable native handoff
is fabricated. The real resource and original HomologyEpisode execute methods
remain connected; only jobs.environment is controlled to exercise its original
returned value / exception translation. Real order identities are retained.
"""
import asyncio
from dataclasses import replace
from copy import deepcopy
from importlib import import_module
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103'

def own(name):
    return import_module(PACKAGE + '.' + name)
NATIVE_MODES = ('returned', 'value_error', 'key_error', 'os_error', 'sqlite_error', 'subprocess_error', 'type_error')

def native_fixture(directory, store, journal):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    module = own('homology_jobs')
    policy = own('local_jobs').LocalJobPolicy(128 * 1024 ** 2, 32 * 1024 ** 2)
    executable = directory / 'constructor-only-program'
    database = directory / 'constructor-only-reference.faa'
    for path, raw in ((executable, b'not executed\n'), (database, b'>original-reference\nMACDEFGHIK\n')):
        if path.exists():
            assert path.read_bytes() == raw
        else:
            path.write_bytes(raw)
    registry = directory / 'homology-registry'
    jobs = module.HomologyJobs(registry) if registry.exists() else module.HomologyJobs.create(registry, executable=module.FileAsset(executable, module.digest(executable)), reference_database=module.FileAsset(database, module.digest(database)), policy=policy, max_cpu=1)
    assert jobs.config['executable'] == module.FileAsset(executable, module.digest(executable)).as_record()
    assert jobs.config['reference_database'] == module.FileAsset(database, module.digest(database)).as_record()
    assert jobs.config['job_limits'] == policy.to_dict()
    assert jobs.config['version'] == module.CONFIGURATION_VERSION
    assert jobs.config['historical_forecast_configuration'] == {'max_cpu': 1}
    binding = own('homology_job_submission.episode').HomologyEpisode(jobs, parser_policy=policy, credit_projector=lambda *a, **k: 0.0, credit_binding={'kind': 'controlled_original_operational_projector'}, monitoring_projector=lambda *a, **k: 0.0, monitoring_binding={'kind': 'controlled_original_monitoring_projector'})
    adapter = own('a103_homology_resource_adapter').HomologyResourceAdapter(binding, store, journal, own('resource_estimation').ResourceToolEstimator())
    assert adapter.homology['job_launch'] is binding and adapter.jobs is jobs
    assert all((b.jobs is jobs and b.parser_policy is policy for b in adapter.homology.values()))
    return (jobs, adapter)

def native_trace(v, mode='returned'):
    assert mode in NATIVE_MODES
    adapter = v.native
    query = v.scope['subject_refs'][0]
    prefix = 'gene_context_evidence/' if v.home.startswith('gene_context_evidence/') else ''
    home = prefix + 'resource_work_submission/local_resource_work_execution'
    path = (('annotation', 'root'),) + ((('gene_context_evidence', 'science'),) if prefix else ()) + (('launch', 'child_0'), ('launch_local', 'child_0'))
    identity = v.runtime.EpisodeRef(v.journal.run_id, path).episode_id
    original = {'version': 'resource_launch_assignment_v1', 'job_request': {'query_ref': query, 'cpu': 1}, 'immutable_input_versions': [], 'constraints': {}, 'resource_selection': adapter._selection(1), 'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    services = SimpleNamespace(record_selection=lambda context: {'run_id': context.run_id, 'episode_id': context.episode_id, 'known_record_refs': [query], 'initial_known_record_refs': [query]})
    binding = own(home.replace('/', '.') + '.episode').ResourceEpisode(services, resource_adapters=(adapter,))
    context = replace(v.context, episode_id=identity, role='launch_local', path=path, assignment=original)
    key = v.journal.run_id + ':' + identity + ':original-commission'
    assigned = adapter.prepare_assignment(context, 'launch_local', original, v.scope, key)
    assert adapter.prepare_assignment(context, 'launch_local', original, v.scope, key) == assigned
    request = {'goal': {'objective': 'Original A103 homology construction'}, 'message': {'scope': v.scope, 'episode_assignment': assigned, 'initial_report': {}}}
    context = replace(context, assignment=assigned, request=request)
    v.journal.save('runtime_episodes', {'episode_id': identity, 'path': v.runtime._json(path), 'request': v.runtime._json(request), 'initial_credit': 0.0, 'state': 'active', 'completion': None, 'archive': None})
    job_ref = assigned['adapter_assignment']['job_ref']
    before = dict(v.jobs._row(job_ref))
    calls = []
    markers = {'value_error': ValueError('original_environment_failure'), 'key_error': KeyError('original_environment_key'), 'os_error': OSError('original_environment_io'), 'sqlite_error': sqlite3.OperationalError('original_environment_db'), 'subprocess_error': subprocess.SubprocessError('original_environment_transport'), 'type_error': TypeError('original_environment_programming_error')}
    value = {'original_controlled_environment': True, 'job_ref': job_ref}

    def environment(reference):
        assert reference == job_ref
        calls.append(reference)
        if mode != 'returned':
            raise markers[mode]
        return value
    operation = v.journal.run_id + ':' + identity + ':0'
    with patch.object(v.jobs, 'environment', environment):
        try:
            outcome = asyncio.run(binding.execute(context, 'homology.environment', {}, operation))
        except TypeError as error:
            assert mode == 'type_error' and error is markers[mode]
            observed = {'raised_type': 'builtins.TypeError', 'message': str(error), 'same_exception': True}
        else:
            if mode == 'returned':
                assert outcome == {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': value, 'feedback': None}
            else:
                error = markers[mode]
                code = {'value_error': str(error), 'key_error': 'job_operation_failed', 'os_error': 'job_operation_failed', 'sqlite_error': 'job_storage_failed', 'subprocess_error': 'job_control_failed'}[mode]
                assert outcome == {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': code, 'exception_type': type(error).__name__, 'operation': 'homology.environment', 'job_ref': job_ref}}
            observed = {'returned': outcome}
    assert calls == [job_ref] and dict(v.jobs._row(job_ref)) == before
    reopened = own('homology_jobs').HomologyJobs(v.jobs.directory)
    try:
        assert reopened.config == v.jobs.config and dict(reopened._row(job_ref)) == before
    finally:
        reopened.close()
    return {'constructor_classes': {r: type(b).__module__ + '.' + type(b).__qualname__ for r, b in adapter.homology.items()}, 'jobs_type': type(v.jobs).__module__ + '.' + type(v.jobs).__qualname__, 'registry': v.jobs.config, 'assignment': assigned, 'context': {'episode_id': identity, 'path': v.runtime._plain(path), 'run_id': v.journal.run_id}, 'job': before, 'observation': observed, 'calls': calls, 'descriptor': adapter.as_record(), 'controlled_port': 'HomologyJobs.environment', 'native_science_executed': False, 'native_handoff_established': False}

