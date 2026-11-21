"""The real world the resource work submission episode runs in: a Store that holds the work as a record (a JSON
artifact: a Python program that reads ``limit.txt`` and writes the sum of the squares of 1..limit to
``result.txt``) and its staged input, and the run's job services with two declared resources: ``local`` (a bound
local resource: detached systemd jobs under a workspace of the test) and ``cluster`` (an HPC resource that is
declared, needs authentication and is not bound in this run). The run's caller is the scientific parent: it passes
the work and its input in custody. ``caller_launch`` is a launch the caller made earlier (to pass its handoff row
back); ``later_fetch`` is what a later Episode does with a returned handoff row. Both are runs of the ``job_probe``
test episode of the job-services tests (no model). Nothing is faked: the runner, journal, Store, job services and
model provider are the real ones."""
import asyncio
import importlib
import json
from pathlib import Path
import sys

from episode_runtime import BindingRegistry, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.job_probe.episode import JobProbe
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').ResourceWorkSubmission
LOCAL = importlib.import_module(PACKAGE + '.local_resource_work_execution.episode').LocalResourceWorkExecution
API = importlib.import_module(PACKAGE + '.api_resource_work_execution.episode').ApiResourceWorkExecution
HPC = importlib.import_module(PACKAGE + '.hpc_resource_work_execution.episode').HpcResourceWorkExecution
PATH = EPISODE.binding_path
PROGRAM = ("limit = int(open('limit.txt').read())\n"
           "open('result.txt', 'w').write(str(sum(i * i for i in range(1, limit + 1))))")
ANSWER = b'338350'
YIELD = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.05}}
LOCAL_SETTINGS = {**YIELD, 'wait_seconds': {'minimum': 1, 'maximum': 60}}
LIBRARY = Path(importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support').__file__).parent
SETTINGS = {PATH: YIELD, LOCAL.binding_path: LOCAL_SETTINGS, API.binding_path: YIELD, HPC.binding_path: YIELD}
TOOLS = ['job.launch', 'job.check', 'job.fetch', 'job.cancel']
PROBE = {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}


class Switch:
    fail = False


def capability(resource_id, kind, availability):
    return {'resource_id': resource_id, 'kind': kind, 'availability': availability,
            'observed_at': '2026-11-19T00:00:00+00:00', 'provenance_refs': [], 'knowledge_entry_ids': [],
            'tool_names': TOOLS}


def world(directory):
    """The Store with the work record and its input; the job services with the two frozen instruction libraries;
    the references of the two records."""
    store = Store(directory / 'store')
    limit_ref = store.artifact(b'100', 'text/plain')
    work = {'command': [sys.executable, '-c', PROGRAM], 'environment': {}, 'inputs': {'limit.txt': limit_ref}}
    work_ref = store.artifact(json.dumps(work, sort_keys=True).encode(), 'application/json')
    launch = LaunchInstructions.freeze(directory / 'frozen_launch', source=LIBRARY / 'instructions' / 'launch')
    knowledge = ToolKnowledge.freeze(directory / 'frozen_knowledge', source=LIBRARY / 'knowledge')
    configuration = {
        'local': {'local': {'workspace': str(directory / 'jobs'),
                            'policy': {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2},
                            'cpu_threads': 1}},
        'pbs': {}, 'capabilities': [capability('local', 'local', 'available'),
                                    capability('cluster', 'hpc', 'authentication_required')],
        'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(launch.directory),
        'tool_knowledge_directory': str(knowledge.directory)}
    return store, job_services(configuration), {'work_ref': work_ref, 'limit_ref': limit_ref}


def registry():
    return BindingRegistry([EPISODE(), LOCAL(), API(), HPC()])


def entry(records, *, kinds=('local', 'hpc'), job_refs=None, selection=('check_refs',)):
    """The commission of the submission: the work and its input in custody, the permitted kinds, the target."""
    assignment = {'version': 'resource_launch_assignment_v1', 'work_refs': [records['work_ref']],
                  'input_refs': [records['limit_ref']], 'allowed_kinds': list(kinds), 'completion_target': 7.0}
    if job_refs is not None:
        assignment['job_refs'] = list(job_refs)
    return {'assignment': assignment, 'message': {}, 'selection': list(selection)}


def collaborators(store, directory, services, continuation):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': continuation, 'services': services}


def _probe(store, directory, services, journal, run_id, plan, *, input_refs=(), job_refs=()):
    caller = directory / run_id
    caller.mkdir()
    probe_entry = {'assignment': {'input_refs': list(input_refs), 'job_refs': list(job_refs)},
                   'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([JobProbe()]), 'job_probe', probe_entry, run_id=run_id, journal=journal,
                  collaborators=collaborators(store, caller, {**services, 'switch': Switch}, PROBE))
    asyncio.run(linked.run())
    return [unit[2]['outcome'] for unit in journal.units(run_id, (('job_probe', run_id),))]


def caller_launch(store, directory, services, journal, limit_ref):
    """A launch of the same work the caller made earlier: the reference of its handoff row."""
    plan = [{'tool': 'launch', 'arguments': {
        'resource_id': 'local', 'job': {'command': [sys.executable, '-c', PROGRAM], 'env': {}},
        'inputs': {'limit.txt': limit_ref}, 'estimates': None, 'cut': None}}]
    return _probe(store, directory, services, journal, 'caller_launch', plan,
                  input_refs=[limit_ref])[0]['handoff_ref']


def later_fetch(store, directory, services, journal, handoff_ref, name):
    """What a later Episode does with the returned handoff row: wait for the job, fetch ``name``; its bytes."""
    plan = [{'tool': 'wait', 'arguments': {'handoff_ref': handoff_ref}},
            {'tool': 'fetch', 'arguments': {'handoff_ref': handoff_ref, 'names': [name], 'cut': None}}]
    fetched = _probe(store, directory, services, journal, 'later_fetch', plan, job_refs=[handoff_ref])[1]
    return store.get_artifact(fetched['result_refs'][0])
