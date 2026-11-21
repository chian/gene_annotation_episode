"""Repeated launches of real detached local jobs: every launch the resource admits ends at its handoff.

A launch submits the job's systemd user service and then waits for the service's ready file
(``native_lifecycle.resume_start``). The start of the service is a job of the user manager, and the manager answers
the requests it has before it dispatches a queued start job: on a busy manager a submitted unit is still
``inactive``, with its start job queued, when the launch first asks for its state. A launch that takes that state
for a dead service refuses a job that is starting (``local_job_boundary_unavailable``, reason
``service_did_not_initialize``).

These tests launch many real jobs and fail on any refused launch: one after another through the real runner (the
``resource_local_probe`` test episode with a real ``Store``, ``RunJournal`` and model provider and the services
``job_services`` builds), and in bursts of concurrent ``LocalJobRoute.submit`` calls, which keep the manager busy
the way the other workflows of this machine do. Nothing is faked and no model is asked. They need the workflow
launcher (``tools/one_workflow.sh``): a local job runs inside the launcher's slice, under its one CPU and 5 GiB."""
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from episode_runtime.job_access import RouteRequestError
from gene_annotation_episode.local_job_policy import LocalJobPolicy
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_job_route import LocalJobRoute

from .resource_local_probe.episode import ResourceLocalProbe

SETTINGS = {'resource_local_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}
LOCAL = 'local_test'
# Small enough that every job of a test fits the resource's memory at once: no launch is refused for capacity.
POLICY = {'memory_bytes': 64 * 1024 ** 2, 'scratch_bytes': 16 * 1024 ** 2}
RUN = 'repeated'
PATH = (('resource_local_probe', RUN),)
COMMAND = ['/bin/true']
SEQUENCE = 30
BURSTS, BURST = 6, 5


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    configuration = {
        'local': {LOCAL: {'workspace': str(tmp_path / 'jobs'), 'policy': POLICY, 'cpu_threads': 1}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(tmp_path / 'not_used_launch'),
        'tool_knowledge_directory': str(tmp_path / 'not_used_knowledge')}
    yield {'store': store, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'services': {**job_services(configuration), 'switch': lambda: None},
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)}
    store.close()


def route(tmp_path):
    return LocalJobRoute(tmp_path / 'jobs', LocalJobPolicy.from_config(POLICY), tmp_path / 'events',
                         resource_id=LOCAL)


def test_launches_one_after_another_through_the_runner_all_end_at_handoff(world, tmp_path):
    step = {'resource_id': LOCAL, 'command': COMMAND, 'environment': {}, 'wait': False, 'inputs': {}, 'cut': False}
    entry = {'assignment': {'input_refs': []}, 'message': {'plan': [step] * SEQUENCE}, 'selection': []}
    linked = link(BindingRegistry([ResourceLocalProbe()]), 'resource_local_probe', entry, run_id=RUN,
                  journal=world['journal'],
                  collaborators={'store': world['store'], 'model_provider': world['provider'],
                                 'continuation': SETTINGS, 'services': world['services']})
    asyncio.run(linked.run())
    launches = [unit[2]['outcome'] for unit in world['journal'].units(RUN, PATH)]
    jobs = route(tmp_path)
    for launch in launches:
        if launch['status'] == 'completed':
            asyncio.run(jobs.wait(launch['job'], None))        # no test leaves a job running
    assert len(launches) == SEQUENCE
    assert [launch['failure'] for launch in launches if launch['status'] != 'completed'] == []


def test_launches_in_bursts_through_the_route_are_all_submitted(tmp_path):
    jobs = route(tmp_path)
    owner = {'run_id': 'bursts', 'episode_id': 'bursts'}

    def submit(handle):
        try:
            jobs.submit(handle, {'command': COMMAND, 'env': {}}, {}, owner)
        except RouteRequestError as error:       # what ``JobAccess.launch`` returns as the failed launch
            return handle, error.failure
        return handle, None

    refused = []
    with ThreadPoolExecutor(BURST) as pool:
        for burst in range(BURSTS):
            for handle, failure in pool.map(submit, [f'job_burst_{burst}_{index}' for index in range(BURST)]):
                if failure is None:
                    asyncio.run(jobs.wait(handle, None))
                else:
                    refused.append((handle, failure['code'], failure['detail']['operational']['reason']))
    assert refused == []
