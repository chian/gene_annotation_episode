"""The world of a file result of a local job: a real Store, the job services of ``job_services`` and a real
detached local job, launched through ``JobAccess.launch`` by the job probe test episode (a launch needs a unit
context). The handoff row the launch writes is held in the Store; the entry assignment passes it in custody
(``handoff_ref``, exactly one) and requests a path inside the job's directory, as the commissioner that holds the
row would. Nothing is faked."""
import asyncio
import sys
import time
from pathlib import Path

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import JOB_LEDGER
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.job_probe.episode import JobProbe
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

from ..episode import ExecutionResultAcquisition

LIBRARY = Path(__file__).resolve().parents[6] / 'episode_support'
PATH = ExecutionResultAcquisition.binding_path
LOCAL = 'local_test'
KIND = 'hpc'
PROBE_SETTINGS = {'job_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}
RESULT_TEXT = 'reaction\tflux\tfeasible\nR_PGK\t1.25\ttrue\nR_PYK\t0.00\tfalse\n'
SELECTION = ('execution_handoff_refs', 'execution_job_record_refs')


def python_job(code):
    return {'command': [sys.executable, '-c', code], 'env': {}}


def finishing_job():
    return python_job("import pathlib\npathlib.Path('result.txt').write_text(" + repr(RESULT_TEXT) + ")")


def waiting_job(release):
    return python_job("import pathlib,time\n"
                      "while not pathlib.Path(" + repr(str(release)) + ").exists(): time.sleep(0.05)\n"
                      "pathlib.Path('result.txt').write_text('late\\n')")


def world(directory, *, log_window_bytes=4096):
    """The Store, the journal, the job services and the settings of the acquisition episode."""
    probe_knowledge = ToolKnowledge.freeze(directory / 'pk', source=LIBRARY / 'knowledge')
    probe_launch = LaunchInstructions.freeze(directory / 'pl', source=LIBRARY / 'instructions' / 'launch')
    configuration = {
        'local': {LOCAL: {'workspace': str(directory / 'jobs'),
                          'policy': {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2},
                          'cpu_threads': 1}},
        'pbs': {},
        'capabilities': [{'resource_id': LOCAL, 'kind': 'local', 'availability': 'available',
                          'observed_at': '2026-11-19T00:00:00+00:00', 'provenance_refs': [],
                          'knowledge_entry_ids': [],
                          'tool_names': ['job.launch', 'job.check', 'job.fetch', 'job.cancel']}],
        'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(probe_launch.directory),
        'tool_knowledge_directory': str(probe_knowledge.directory)}
    profile = {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}
    return {'directory': directory, 'jobs': directory / 'jobs', 'store': Store(directory / 'store'),
            'journal': RunJournal(directory / 'journal.sqlite3'),
            'services': {**job_services(configuration), 'switch': lambda: type('S', (), {'fail': False})()},
            'provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'settings': {'log_window_bytes': log_window_bytes,
                         'results_yield_profiles': {'native_unbounded_' + KIND: profile},
                         'task_yield_profiles': {'results:native_finite_' + KIND: profile}}}


def launch_job(w, job, *, wait_for_end):
    """The launching child's work, done as the run's caller: a real local job, its handoff row in the Store."""
    plan = [{'tool': 'launch', 'arguments': {
        'resource_id': LOCAL, 'job': job, 'inputs': {}, 'cut': None,
        'estimates': {'gain': {'value': 2.0, 'lower': 1.0, 'upper': 4.0}, 'done_about': '16:00'}}}]
    if wait_for_end:
        plan.append({'tool': 'wait', 'arguments': {'handoff_ref': {'from': 0, 'field': ['handoff_ref']}}})
    run_id = 'launch-' + str(int(time.time() * 1000))
    entry = {'assignment': {'input_refs': [], 'job_refs': []}, 'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([JobProbe()]), 'job_probe', entry, run_id=run_id, journal=w['journal'],
                  collaborators={'store': w['store'], 'model_provider': w['provider'],
                                 'continuation': PROBE_SETTINGS, 'services': w['services']})
    result = asyncio.run(linked.run())['result'].as_record()
    return run_id, result['outstanding_job_refs'][0]


def entry_input(w, launch_run, handoff_ref, *, selector=None, selection=SELECTION):
    """The results commission, built as the commissioner builds it: the handoff row it holds, passed in custody,
    and a requested path inside the job's directory."""
    launched = w['journal'].units(launch_run, (('job_probe', launch_run),))[0][2]['outcome']
    w['result_path'] = str(w['jobs'] / launched['job']) + '/result.txt'
    assignment = {'version': 'execution_results_assignment', 'handoff_ref': [handoff_ref],
                  'selector': {'paths': [w['result_path']]} if selector is None else selector(w['result_path']),
                  'acquired_record_unit': 1.0, 'resource_kind': KIND}
    return {'assignment': assignment, 'message': {}, 'selection': list(selection)}


def collaborators(w):
    return {'store': w['store'], 'model_provider': w['provider'], 'continuation': {PATH: w['settings']},
            'services': w['services']}


def linked(w, run_id, entry):
    registry = BindingRegistry([ExecutionResultAcquisition()])
    return registry, link(registry, PATH, entry, run_id=run_id, journal=w['journal'], collaborators=collaborators(w))


__all__ = ['JOB_LEDGER', 'KIND', 'LOCAL', 'PATH', 'RESULT_TEXT', 'collaborators', 'entry_input', 'finishing_job',
           'launch_job', 'linked', 'waiting_job', 'world']
