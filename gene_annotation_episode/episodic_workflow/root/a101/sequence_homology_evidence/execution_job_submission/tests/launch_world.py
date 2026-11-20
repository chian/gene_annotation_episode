"""The world of an API launch through the A101 launch episode: the world of its API child
(``api_job_execution/tests/api_world.py``: the Store with the protein query, the job services with the API route
bound as resource ``ncbi_blast``, the frozen libraries) with the launch episode's own settings and the launch
assignment a head commissions: the BLAST database grader request of that resource (the query, the database), the
query's records in custody and the credit units. The registry holds the launch episode and its three children; only
the API child is commissioned. Nothing is faked."""
from episode_runtime import BindingRegistry, link, resume

from ..api_job_execution.episode import ApiJobExecution
from ..api_job_execution.tests import api_world
from ..episode import ExecutionJobSubmission
from ..hpc_job_execution.episode import HpcJobExecution
from ..local_job_execution.episode import LocalJobExecution

PATH = ExecutionJobSubmission.binding_path
RESOURCE = api_world.RESOURCE
PROFILE = 'launch:compact_blast_database_grader_return_request_v1'
SELECTION = ['execution_handoff_refs', 'execution_completed']


def world(directory, route):
    made = api_world.world(directory, route)
    child = made['collaborators']['continuation'][api_world.PATH]
    settings = {'resources': {RESOURCE: {'kind': 'api'}}, 'initial_information': {},
                'coordinator_workspace': str(directory / 'coordinator'),
                'launch_instructions_directory': child['launch_instructions_directory'],
                'tool_knowledge_directory': child['tool_knowledge_directory'],
                'task_yield_profiles': {PROFILE: {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}}}
    request = {'version': 'blast_database_grader_return_request_v1', 'resource_id': RESOURCE,
               'return_type': 'blast_database_sheet_v1', 'query_subject_ref': made['subject'],
               'database': 'swissprot'}
    assignment = {'version': 'execution_launch_assignment_v1', 'requests': {RESOURCE: request},
                  'immutable_input_versions': [], 'constraints': {},
                  'record_refs': [made['subject'], made['store'].get(made['subject'])['sequence_ref']],
                  'handoff_unit': 1.0, 'acquired_record_unit': 1.0}
    made['child_entry'] = made['entry']
    made['entry'] = {'assignment': assignment, 'message': {'purpose': 'launch the BLAST search of the target'},
                     'selection': SELECTION}
    made['collaborators']['continuation'] = {
        PATH: settings, api_world.PATH: child, HpcJobExecution.binding_path: {}, LocalJobExecution.binding_path: {}}
    return made


def registry():
    return BindingRegistry([ExecutionJobSubmission(), ApiJobExecution(), HpcJobExecution(), LocalJobExecution()])


def linked(world, run_id):
    return link(registry(), PATH, world['entry'], run_id=run_id, journal=world['journal'],
                collaborators=world['collaborators'])


def resumed(world, run_id):
    return resume(registry(), run_id=run_id, journal=world['journal'], collaborators=world['collaborators'])


def path_of(run_id):
    return ((PATH.replace('/', '__'), run_id),)
