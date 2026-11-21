"""The held world of the local job execution tests: a real Store, the real job services (the detached local route
on a workspace under the test's directory), the episode's settings, and a valid ``practical_assignment_v1`` whose
requested job writes ``answer.txt`` and whose one requirement gives the handoff a credit of 4."""
import asyncio
import json
import sys

from gene_annotation_episode.local_job_policy import LocalJobPolicy
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_job_route import LocalJobRoute

from ..episode import LocalJobExecution

RESOURCE_ID = 'local_test'
PATH = LocalJobExecution.binding_path
PROFILE = 'launch_local:practical_local_handoff'
POLICY = {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2}
# More memory than any machine this runs on has: the resource refuses every launch (a real refusal).
REFUSING_POLICY = {'memory_bytes': 1024 ** 6, 'scratch_bytes': 64 * 1024 ** 2}
HANDOFF_CREDIT = 4.0
SETTINGS = {'task_yield_profiles': {PROFILE: {'cutoff': 0.5, 'parameters': {}}}}
JOB_CODE = "import pathlib; pathlib.Path('answer.txt').write_text('42'); print('a104 job done')"


def practical_assignment(workspace, **changes):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'a104-local-1', 'resource_id': RESOURCE_ID,
            'resource_kind': 'local', 'workspace': workspace, 'endpoint': 'usable_handoff',
            'requested_job': {'argv': [sys.executable, '-c', JOB_CODE], 'environment': {}},
            'progress_requirements': [
                {'key': 'handoff', 'credit': HANDOFF_CREDIT, 'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}, **changes}


def world(tmp_path, policy=POLICY):
    workspace = str(tmp_path / 'jobs')
    configuration = {
        'local': {RESOURCE_ID: {'workspace': workspace, 'policy': policy, 'cpu_threads': 1}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates' / 'table.sqlite3'),
        # No episode of these runs declares the instruction libraries, so they are never built.
        'launch_instructions_directory': str(tmp_path / 'no_launch_instructions'),
        'tool_knowledge_directory': str(tmp_path / 'no_tool_knowledge')}
    return {'store': Store(tmp_path / 'store'), 'services': job_services(configuration), 'workspace': workspace,
            'assignment': practical_assignment(workspace), 'directory': tmp_path, 'policy': policy}


def entry(held, **changes):
    return {'assignment': {**held['assignment'], **changes}, 'message': {'resource_id': RESOURCE_ID},
            'selection': ['execution_handoff_refs', 'execution_completed']}


def collaborators(held, calls, settings=None):
    return {'store': held['store'],
            'model_provider': ModelProvider(load_config(), held['directory'] / calls, held['directory']),
            'continuation': {PATH: SETTINGS} if settings is None else settings, 'services': held['services']}


def job_directory(held, job):
    return held['directory'] / 'jobs' / job


def job_ended(held, job):
    """Wait on the launched job itself until it has ended (no clock) and return its directory, so that a test sees
    what the job did and leaves no job running."""
    route = LocalJobRoute(held['workspace'], LocalJobPolicy.from_config(held['policy']),
                          held['directory'] / 'events', resource_id=RESOURCE_ID)
    asyncio.run(route.wait(job, None))
    return job_directory(held, job)


def dump(journal, run_id):
    """Print the journal facts of the run: every episode, its units, model decisions and controller steps."""
    print('RUN STATE', journal.run_state(run_id)[0], 'FAILURE', journal.run_failure(run_id))
    for episode in journal.episodes(run_id):
        path = tuple(tuple(item) for item in episode['path'])
        print('EPISODE', episode['binding_path'], episode['state'], 'completion', episode['completion'])
        for label, _, outcome, _ in journal.units(run_id, path):
            print('  UNIT', label, json.dumps(outcome, default=str)[:900])
        for call in journal.model_calls(run_id, path):
            print('  MODEL', call['position'], json.dumps(call['response'], default=str)[:500])
        for step in journal.controller_steps(run_id, path):
            print('  STEP', json.dumps(step, default=str)[:300])
