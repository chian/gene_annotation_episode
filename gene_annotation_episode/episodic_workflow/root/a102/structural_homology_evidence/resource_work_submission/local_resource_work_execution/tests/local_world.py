"""The real world the local resource work execution episode runs in: a Store that holds the work as a record (a
JSON artifact: a Python program that reads ``limit.txt`` and writes the sum of the squares of 1..limit to
``result.txt``) and the staged input file, and the run's job services with one local resource (detached systemd
jobs under a workspace of the test). The run's caller is the parent: it passes the work and its input in custody.
``later_fetch`` is what a later Episode does with the handoff row the launch returned: it waits for the job and
fetches its result (a run of the ``job_probe`` test episode of the job-services tests, no model). Nothing is faked:
the runner, journal, Store, job services and model provider are the real ones."""
import asyncio
import importlib
import json
import sys

from episode_runtime import BindingRegistry, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.job_probe.episode import JobProbe

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').LocalResourceWorkExecution
PATH = EPISODE.binding_path
RESOURCE = 'local'
PROGRAM = ("limit = int(open('limit.txt').read())\n"
           "open('result.txt', 'w').write(str(sum(i * i for i in range(1, limit + 1))))")
ANSWER = b'338350'
SETTINGS = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.05}, 'wait_seconds': {'minimum': 1, 'maximum': 60}}
UNITS = {'handoff_unit': 4.0, 'check_unit': 3.0}


class Switch:
    fail = False


def job_configuration(directory):
    capability = {'resource_id': RESOURCE, 'kind': 'local', 'availability': 'available',
                  'observed_at': '2026-11-19T00:00:00+00:00', 'provenance_refs': [], 'knowledge_entry_ids': [],
                  'tool_names': ['job.launch', 'job.check', 'job.fetch', 'job.cancel']}
    return {'local': {RESOURCE: {'workspace': str(directory / 'jobs'),
                                 'policy': {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2},
                                 'cpu_threads': 1}},
            'pbs': {}, 'capabilities': [capability], 'event_ledger_directory': str(directory / 'events'),
            'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
            'launch_instructions_directory': str(directory / 'unused_launch_library'),
            'tool_knowledge_directory': str(directory / 'unused_knowledge_library')}


def world(directory):
    """The Store with the work record and its input, the job services, and the references of the two records."""
    store = Store(directory / 'store')
    limit_ref = store.artifact(b'100', 'text/plain')
    work = {'command': [sys.executable, '-c', PROGRAM], 'environment': {}, 'inputs': {'limit.txt': limit_ref}}
    work_ref = store.artifact(json.dumps(work, sort_keys=True).encode(), 'application/json')
    return store, job_services(job_configuration(directory)), {'work_ref': work_ref, 'limit_ref': limit_ref}


def entry(records):
    """The commission of the launch: the resource, the work and its input in custody, and the credit units."""
    return {'assignment': {'version': 'resource_launch_assignment_v1', 'resource_id': RESOURCE,
                           'work_refs': [records['work_ref']], 'input_refs': [records['limit_ref']], **UNITS},
            'message': {}, 'selection': []}


def collaborators(store, directory, services, continuation):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': continuation, 'services': services}


def later_fetch(store, directory, services, journal, handoff_ref, name):
    """What a later Episode does with the returned handoff row: wait for the job, fetch ``name``; its bytes."""
    caller = directory / 'later'
    caller.mkdir()
    plan = [{'tool': 'wait', 'arguments': {'handoff_ref': handoff_ref}},
            {'tool': 'fetch', 'arguments': {'handoff_ref': handoff_ref, 'names': [name], 'cut': None}}]
    probe_entry = {'assignment': {'input_refs': [], 'job_refs': [handoff_ref]}, 'message': {'plan': plan},
                   'selection': []}
    probe = {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}
    linked = link(BindingRegistry([JobProbe()]), 'job_probe', probe_entry, run_id='later_fetch', journal=journal,
                  collaborators=collaborators(store, caller, {**services, 'switch': Switch}, probe))
    asyncio.run(linked.run())
    fetched = journal.units('later_fetch', (('job_probe', 'later_fetch'),))[1][2]['outcome']
    return store.get_artifact(fetched['result_refs'][0])
