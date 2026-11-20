"""The held world of the job submission tests: a real Store, the real job services (the detached local route on a
workspace under the test's directory), the two instruction libraries of the axis frozen under the test's directory,
the settings of the submission episode and of its launch children, and a launch assignment with one request: a valid
``practical_assignment_v1`` for the local resource whose job writes ``answer.txt`` and whose handoff requirement has
a credit of 4. One usable handoff is worth 2 to the submission."""
import asyncio
import json
import sys
from pathlib import Path

from episode_runtime import BindingRegistry
from gene_annotation_episode.local_job_policy import LocalJobPolicy
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_job_route import LocalJobRoute
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

from ..api_job_execution.episode import ApiJobExecution
from ..episode import ExecutionJobSubmission
from ..hpc_job_execution.episode import HpcJobExecution
from ..local_job_execution.episode import LocalJobExecution

LIBRARY = Path(__file__).resolve().parents[5] / 'episode_support'
AXIS = 'sequence_homology_evidence'
RESOURCE_ID = 'local_test'
PATH = ExecutionJobSubmission.binding_path
POLICY = {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2}
HANDOFF_UNIT, CHILD_HANDOFF_CREDIT = 2.0, 4.0
JOB_CODE = "import pathlib; pathlib.Path('answer.txt').write_text('42'); print('a101 job done')"


def registry():
    return BindingRegistry([ExecutionJobSubmission(), LocalJobExecution(), ApiJobExecution(), HpcJobExecution()])


def practical_request(workspace):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'a101-local-1', 'resource_id': RESOURCE_ID,
            'resource_kind': 'local', 'workspace': workspace, 'endpoint': 'usable_handoff',
            'requested_job': {'argv': [sys.executable, '-c', JOB_CODE], 'environment': {}},
            'progress_requirements': [{'key': 'handoff', 'credit': CHILD_HANDOFF_CREDIT,
                                       'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}


def world(tmp_path):
    workspace = str(tmp_path / 'jobs')
    (tmp_path / 'coordinator').mkdir()
    launch = LaunchInstructions.freeze(tmp_path / 'frozen_launch', source=LIBRARY / 'instructions' / 'launch' / AXIS)
    knowledge = ToolKnowledge.freeze(tmp_path / 'frozen_knowledge', source=LIBRARY / 'knowledge' / AXIS)
    configuration = {
        'local': {RESOURCE_ID: {'workspace': workspace, 'policy': POLICY, 'cpu_threads': 1}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(tmp_path / 'events'),
        'estimate_table_path': str(tmp_path / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(launch.directory),
        'tool_knowledge_directory': str(knowledge.directory)}
    assignment = {'version': 'execution_launch_assignment_v1', 'requests': {RESOURCE_ID: practical_request(workspace)},
                  'immutable_input_versions': [], 'constraints': {}, 'handoff_unit': HANDOFF_UNIT,
                  'acquired_record_unit': 0.5}
    profile = {'cutoff': 0.5, 'parameters': {}}
    settings = {
        PATH: {'resources': {RESOURCE_ID: {'kind': 'local', 'workspace': workspace, 'policy': POLICY}},
               'initial_information': {}, 'coordinator_workspace': str(tmp_path / 'coordinator'),
               'launch_instructions_directory': str(launch.directory),
               'tool_knowledge_directory': str(knowledge.directory),
               'task_yield_profiles': {'launch:practical_local_handoff': profile}},
        LocalJobExecution.binding_path: {'task_yield_profiles': {'launch_local:practical_local_handoff': profile}},
        # The API and HPC launch children are in the subtree and are not commissioned by these runs.
        ApiJobExecution.binding_path: {}, HpcJobExecution.binding_path: {}}
    return {'store': Store(tmp_path / 'store'), 'services': job_services(configuration), 'workspace': workspace,
            'assignment': assignment, 'settings': settings, 'directory': tmp_path, 'launch_library': launch}


def entry(held):
    return {'assignment': held['assignment'], 'message': {'purpose': 'launch'},
            'selection': ['execution_handoff_refs', 'execution_completed']}


def collaborators(held, calls):
    return {'store': held['store'],
            'model_provider': ModelProvider(load_config(), held['directory'] / calls, held['directory']),
            'continuation': held['settings'], 'services': held['services']}


def job_ended(held, job):
    """Wait on the launched job itself until it has ended (no clock) and return its directory, so that a test sees
    what the job did and leaves no job running."""
    route = LocalJobRoute(held['workspace'], LocalJobPolicy.from_config(POLICY), held['directory'] / 'events',
                          resource_id=RESOURCE_ID)
    asyncio.run(route.wait(job, None))
    return held['directory'] / 'jobs' / job


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
