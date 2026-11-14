"""Explicit caller connection; no default topology or independent worker claim."""
from copy import deepcopy
from pathlib import Path
import pytest
from .homology_family_boundaries import (HOMES, ROLES, Provider, options, own, registry,
    original_family_type, registry_rows, install_resource_inventory_guard)
from .test_homology_family_public_resume import run_to_actual_provider


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch, tmp_path):
    install_resource_inventory_guard(monkeypatch, tmp_path / 'execution-memory.sqlite3',
        'explicit_homology_factory_does_not_authorize_native_or_network_work')




def test_actual_public_saved_run_consumes_explicit_factory_restorer(tmp_path, record_property):
    import json
    directory = tmp_path / 'run'
    with registry(tmp_path / 'resources') as (store, jobs, policy, scope, job_ref):
        setup = own('homology_service_setup')
        family = setup.create_homology_family(jobs, **options(policy))
        descriptor = deepcopy(family.as_record())
        original_jobs = registry_rows(jobs)
        first, original_episodes = run_to_actual_provider(store, family, directory, Provider(), resume=False)
        assert first['job_episodes'] == descriptor and registry_rows(jobs) == original_jobs
        workspace, registry_directory = Path(store.path), jobs.directory
    reopened_jobs = own('homology_jobs').HomologyJobs(registry_directory)
    try:
        with own('state').Store(workspace) as reopened_store:
            # The actual saved settings supply the descriptor; names do not
            # construct calculators, policy, registry or private class objects.
            saved = json.loads((directory / 'run.json').read_bytes())
            restored = setup.restore_homology_family(saved['job_episodes'], reopened_jobs, **options(policy))
            resumed, episodes = run_to_actual_provider(reopened_store, restored, directory, Provider(), resume=True)
            assert resumed == first and episodes == original_episodes
            assert restored.as_record() == descriptor and registry_rows(reopened_jobs) == original_jobs
            with pytest.raises(own('method_loop.durable').DurableExecutionError) as refused:
                own('independent_execution')._standard_bindings(reopened_store, directory,
                    {key: value for key, value in saved.items() if key != 'run_id'})
            assert refused.value.failure['code'] == 'unavailable_binding'
            assert refused.value.failure['affected_refs'] == [saved['bindings']['controller']]
    finally:
        reopened_jobs.close()
    record_property('explicit_homology_factory_saved_connection', json.dumps({
        'actual_saved_job_descriptor': descriptor, 'registered_run': first,
        'original_episode_requests': original_episodes, 'completed_actions': 0,
        'native_work_claimed': False, 'independent_worker_restoration_claimed': False}, sort_keys=True))
