"""Actual public assembly/resume boundary with caller-owned Homology resources.

The provider raises before returning a selected unit. This proves no completed
work or scientific progress; it exposes actual registration and replay admission
without native work, a fabricated response, or a replacement Workflow.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace
import pytest
from .homology_family_boundaries import (ROLES, ContinuationObserved, Provider, controller_factory,
    options, own, registry, registry_files, registry_rows, task_credit, install_resource_inventory_guard)


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch, tmp_path):
    install_resource_inventory_guard(monkeypatch, tmp_path / 'execution-memory.sqlite3',
        'homology_public_resume_does_not_authorize_native_or_network_work')


def run_to_actual_provider(store, family, directory, provider, *, resume):
    with pytest.raises(ContinuationObserved, match='^actual_original_continuation_boundary$'):
        asyncio.run(own('runtime').run_workflow(store, own('tools').ToolRegistry(store),
            provider=provider, run_dir=directory, resume=resume,
            controller_factory=controller_factory, project_credit=task_credit,
            job_episodes=family, episode_binding_factories=(),
            annotation_child_roles=(), decision_protocol=None))
    # This explicit KeyboardInterrupt subtype reaches the runtime's original
    # interrupted-state handler. Ordinary source exceptions retain source_failed;
    # no selected action, source/controller replacement or completion is invented.
    assert len(provider.calls) == 1
    manifest = json.loads((directory / 'run.json').read_bytes())
    row = store.db.execute('SELECT * FROM runtime_runs WHERE run_id=?', (manifest['run_id'],)).fetchone()
    assert json.loads(row['settings']) == {key: value for key, value in manifest.items() if key != 'run_id'}
    assert row['state'] == 'interrupted'
    assert json.loads(row['summary']) == {'error_type': 'ContinuationObserved',
        'detail': 'actual_original_continuation_boundary'}
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE run_id=?', (manifest['run_id'],)).fetchone()[0] == 0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_observations WHERE run_id=?', (manifest['run_id'],)).fetchone()[0] == 0
    episodes = [dict(item) for item in store.db.execute(
        'SELECT episode_id,path,request FROM runtime_episodes WHERE run_id=? ORDER BY episode_id',
        (manifest['run_id'],))]
    assert len(episodes) == 1 and json.loads(episodes[0]['path']) == [['annotation', 'root']]
    return manifest, episodes


def test_actual_public_registration_and_resume_with_reopened_family(tmp_path, record_property):
    directory = tmp_path / 'run'
    with registry(tmp_path / 'resources') as (store, jobs, policy, scope, job_ref):
        Family = own('homology_binding_family').HomologyBindingFamily
        family = Family(jobs, **options(policy))
        descriptor = deepcopy(family.as_record())
        saved_jobs = registry_rows(jobs)
        first_provider = Provider()
        first_manifest, first_episodes = run_to_actual_provider(store, family, directory,
            first_provider, resume=False)
        assert first_manifest['job_episodes'] == descriptor
        assert first_manifest['controller'] is None and first_manifest['episode_bindings'] == []
        assert registry_rows(jobs) == saved_jobs
        workspace = Path(store.path)
        registry_directory = jobs.directory
    # Both original real handles have now exited their owning fixture contexts.
    saved_files = registry_files(registry_directory)
    reopened_jobs = own('homology_jobs').HomologyJobs(registry_directory)
    try:
        with own('state').Store(workspace) as reopened_store:
            restored = own('homology_family_restore').restore_homology_family(descriptor,
                reopened_jobs, **options(policy))
            assert type(restored) is Family and restored.jobs is reopened_jobs
            second_provider = Provider()
            second_manifest, second_episodes = run_to_actual_provider(reopened_store, restored,
                directory, second_provider, resume=True)
            assert second_manifest == first_manifest and second_episodes == first_episodes
            assert restored.as_record() == descriptor and registry_rows(reopened_jobs) == saved_jobs
            for role in family.roles:
                assert type(restored.for_role(role)) is type(family.for_role(role))
                assert restored.for_role(role)._job_credit_calculator is family.for_role(role)._job_credit_calculator
                assert restored.for_role(role).monitoring_projector is family.for_role(role).monitoring_projector
            # Standard C1 cannot infer the original custom executable family.
            # Keep its exact refusal; successful same-process reconstruction
            # does not authorize a generic independent-worker factory.
            with pytest.raises(own('method_loop.durable').DurableExecutionError) as rejected:
                own('independent_execution')._standard_bindings(reopened_store, directory,
                    {key: value for key, value in second_manifest.items() if key != 'run_id'})
            assert rejected.value.failure['code'] == 'unavailable_binding'
            assert rejected.value.failure['affected_refs'] == [second_manifest['bindings']['controller']]
    finally:
        reopened_jobs.close()
    assert registry_files(registry_directory) == saved_files
    record_property('actual_public_homology_family_resume', json.dumps({
        'saved_manifest': first_manifest, 'original_episode_requests': first_episodes,
        'first_provider_call': first_provider.calls[0], 'resumed_provider_call': second_provider.calls[0],
        'same_store_directory_and_typed_reopened_registry': True,
        'saved_family_record_and_original_callables_preserved': True,
        'actual_public_workflow_registration_and_resumption_reached_provider': True,
        'completed_actions': 0, 'completed_workflow_claimed': False,
        'independent_worker_restoration_claimed': False}, sort_keys=True))


@pytest.mark.parametrize('role', ROLES)
def test_actual_private_job_request_and_failed_action_survive_store_and_registry_reopen(tmp_path, role, record_property):
    """Three actual private carriers, with truthful unsubmitted native outcomes.

    These standalone assignments exercise original runtime reconstruction and
    cached action replay. They do not assert a positive parent handoff, native
    submission, ordinary provider decision, or completed scientific iterator.
    """
    directory = tmp_path / 'job-workflow'
    run_id = 'explicit-homology-saved-private-' + role
    action = {'kind': 'tool', 'tool': {'job_launch': 'homology.configure',
        'job_monitor': 'homology.sample', 'job_results': 'homology.extract'}[role],
        'arguments': {'limit': 1} if role == 'job_results' else {}}

    def forbidden(*args, **kwargs):
        raise AssertionError('saved_job_replay_does_not_authorize_native_or_model_work')

    def host(store, family):
        return own('runtime').Workflow(store,
            own('tools').ToolRegistry(store, clients=SimpleNamespace(request=forbidden)),
            SimpleNamespace(complete=forbidden), directory, run_id,
            controller_factory=controller_factory, project_credit=task_credit,
            job_episodes=family, annotation_child_roles=(), root_role=role,
            episode_binding_factories=(), wait_inputs_version='wait_inputs_binding_v1',
            completed_action_inputs_version=None)

    with registry(tmp_path / 'resources') as (store, jobs, policy, scope, job_ref):
        Family = own('homology_binding_family').HomologyBindingFamily
        family = Family(jobs, **options(policy))
        descriptor = deepcopy(family.as_record())
        assignment = {'job_ref': job_ref, 'query_ref': scope['subject_refs'][0], 'cpu': 1}
        if 'search_modes' in jobs.config: assignment['search_mode'] = jobs._row(job_ref)['search_mode']
        if role != 'job_launch':
            assignment['handoff'] = {'job_ref': job_ref, 'registry_ref': jobs.config['registry_ref'],
                'backend': own('homology_jobs').VERSION, 'status_interface': 'homology.status.v1',
                'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
        if role == 'job_monitor': assignment.update(prior_sample_refs=[], prior_samples=[])
        workflow = host(store, family)
        episode = workflow.build(role, 'original-private-request', 'Retain actual assigned work', scope,
            job_assignment=deepcopy(assignment))
        assert type(episode.source) is family.for_role(role).decision_source_type
        first = asyncio.run(episode.source.execute(deepcopy(action), 0)).as_record()
        episode_id = episode.source.episode_id
        request = episode.request.as_record()
        saved_action = dict(workflow.journal.row('runtime_actions', episode_id, 0))
        payload = json.loads(saved_action['result'])
        assert payload['status'] == 'failed' and json.loads(saved_action['action']) == action
        assert first['credit'] == 0.
        assert payload['feedback']['code'] == ('configured_executable_unavailable_or_changed'
            if role == 'job_launch' else 'job_submission_handoff_unresolved')
        assert not jobs._row(job_ref)['submission_requested']
        saved_jobs = registry_rows(jobs)
        workspace, jobs_directory = Path(store.path), jobs.directory
    original_files = registry_files(jobs_directory)
    reopened_jobs = own('homology_jobs').HomologyJobs(jobs_directory)
    try:
        with own('state').Store(workspace) as reopened_store:
            restored = own('homology_family_restore').restore_homology_family(descriptor,
                reopened_jobs, **options(policy))
            resumed = host(reopened_store, restored)
            rebuilt = resumed.build(role, 'original-private-request', 'Retain actual assigned work', scope,
                job_assignment=deepcopy(assignment))
            assert rebuilt.source.episode_id == episode_id and rebuilt.request.as_record() == request
            assert type(rebuilt.source) is restored.for_role(role).decision_source_type
            assert type(rebuilt.source) is type(episode.source)
            assert restored.as_record() == descriptor
            assert dict(resumed.journal.row('runtime_actions', episode_id, 0)) == saved_action
            # The real Workflow cache must supply the saved action. If it
            # incorrectly invokes the underlying operation, this explicit port
            # rejects it; the application replay implementation is unchanged.
            restored._execute = forbidden
            replayed = asyncio.run(rebuilt.source.execute(deepcopy(action), 0)).as_record()
            assert replayed == first
            assert dict(resumed.journal.row('runtime_actions', episode_id, 0)) == saved_action
            assert registry_rows(reopened_jobs) == saved_jobs
    finally:
        reopened_jobs.close()
    assert registry_files(jobs_directory) == original_files
    record_property('actual_private_family_saved_action', json.dumps({'role': role,
        'descriptor': descriptor, 'request': request, 'episode_id': episode_id,
        'saved_action': saved_action, 'returned': first, 'replayed': replayed,
        'actual_store_and_registry_closed_and_reopened': True,
        'parent_handoff_admission_claimed': False, 'native_submission_claimed': False,
        'complete_iterator_claimed': False}, sort_keys=True))
