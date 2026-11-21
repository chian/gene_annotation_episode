"""The real world the result acquisition episode runs in: a Store, the run's job services with one local resource
(detached systemd jobs under a workspace of the test), and a real job the run's caller launched: a Python program
that sums the squares of 1..100 and writes ``answer.txt`` (``PROGRAM``: the caller waits for its end; ``SLOW``: it
sleeps first and the caller does not wait, so the acquisition meets a job that is still running). The caller's
launch is a run of the ``job_probe`` test episode of the job-services tests (no model). Nothing is faked: the
runner, journal, Store, job services and model provider are the real ones."""
import asyncio
import importlib
import sys

from episode_runtime import BindingRegistry, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.job_probe.episode import JobProbe

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').ResourceResultAcquisition
PATH = EPISODE.binding_path
RESOURCE = 'local'
PROGRAM = "import pathlib\npathlib.Path('answer.txt').write_text(str(sum(i * i for i in range(1, 101))))"
SLOW = 'import time\ntime.sleep(6)\n' + PROGRAM
ANSWER = b'338350'
SETTINGS = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.05}, 'wait_seconds': {'minimum': 1, 'maximum': 60}}


class Switch:
    fail = False


def world(directory):
    """The Store and the job services of the run (one bound local resource, declared available)."""
    store = Store(directory / 'store')
    capability = {'resource_id': RESOURCE, 'kind': 'local', 'availability': 'available',
                  'observed_at': '2026-11-19T00:00:00+00:00', 'provenance_refs': [], 'knowledge_entry_ids': [],
                  'tool_names': ['job.launch', 'job.check', 'job.fetch', 'job.cancel']}
    configuration = {
        'local': {RESOURCE: {'workspace': str(directory / 'jobs'),
                             'policy': {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2},
                             'cpu_threads': 1}},
        'pbs': {}, 'capabilities': [capability], 'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'unused_launch_library'),
        'tool_knowledge_directory': str(directory / 'unused_knowledge_library')}
    return store, job_services(configuration)


def collaborators(store, directory, services, continuation):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': continuation, 'services': services}


def launched_job(store, directory, services, journal, program=PROGRAM):
    """The caller's own real job, its results not fetched: the reference of its handoff row. The caller waits for
    the end of ``PROGRAM``; it returns at the handoff of any other program."""
    caller = directory / 'caller'
    caller.mkdir()
    plan = [{'tool': 'launch', 'arguments': {
                'resource_id': RESOURCE, 'job': {'command': [sys.executable, '-c', program], 'env': {}},
                'inputs': {}, 'estimates': None, 'cut': None}}]
    if program == PROGRAM:
        plan.append({'tool': 'wait', 'arguments': {'handoff_ref': {'from': 0, 'field': ['handoff_ref']}}})
    entry = {'assignment': {'input_refs': [], 'job_refs': []}, 'message': {'plan': plan}, 'selection': []}
    probe = {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}
    linked = link(BindingRegistry([JobProbe()]), 'job_probe', entry, run_id='caller_launch', journal=journal,
                  collaborators=collaborators(store, caller, {**services, 'switch': Switch}, probe))
    asyncio.run(linked.run())
    return journal.units('caller_launch', (('job_probe', 'caller_launch'),))[0][2]['outcome']['handoff_ref']


def entry(handoff_ref, names, selection=()):
    """The commission of the acquisition: the job's handoff row in custody and the requested result file names."""
    return {'assignment': {'version': 'resource_results_assignment_v1', 'job_refs': [handoff_ref],
                           'requested_names': list(names)},
            'message': {}, 'selection': list(selection)}
