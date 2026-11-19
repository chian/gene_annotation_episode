"""What the parent gives: one practical assignment (``practical_assignment_v1``) for a configured HPC resource.

Every field is a property of the old ``ASSIGNMENT_SCHEMA`` (``practical_execution_records``) under its own name;
``resource_kind`` is the one the old request schema fixed for this role (``hpc``), and ``resource_id`` was the
old schema's required resource choice. The old schema's nested shapes are checked by the library's
``validate_assignment`` in ``read_from_parent`` (a form has no union and no null). ``launch_instructions`` (a
selection) is optional (omitted when absent). ``native_flux_balance_execution`` is a property of the old schema
that ``validate_assignment`` refuses on an HPC resource (``native_flux_balance_local_resource_required``): it is
declared under its name and raises where the assignment is read.

The old episode also read its parent's own ``execution_launch_assignment_v1`` (``requests``,
``immutable_input_versions``, ``constraints``) and the parent's recorded request (``runtime_episodes``), and chose
its request among the parent's frozen HPC requests (``child_assignment_schema``,
``frozen_hpc_launch_request_missing``): a child cannot read its parent's assignment, the old runner tables are
gone, and every such check is a check of a commission, so none of that is carried (contract_misfits)."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    ASSIGNMENT_VERSION, validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The practical assignment version', ASSIGNMENT_VERSION),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_id': Field('text', 'The configured HPC resource the job runs on'),
    'resource_kind': DeclaredField('text', 'The kind of resource: an HPC resource', 'hpc'),
    'workspace': Field('text', 'The absolute workspace on the resource; inside the resource\'s configured workspace'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'requested_job': Field('record', 'The requested job: argv and environment'),
    'progress_requirements': Field('list', 'The requirements that earn credit: key, credit and predicate each'),
    'completion_keys': Field('list', 'The requirement keys whose joint satisfaction, with the endpoint, completes '
                             'the assignment'),
    'initial_context': Field('record', 'The initial working directory and environment (revision 0)'),
    'inventory_snapshot': Field('record', 'The recorded inventory of the resource, as context only'),
    'constraints': Field('record', 'The scheduler constraints: account, queue, resources, allocation'),
    'launch_instructions': Field('record', 'The selection of launch instructions from the frozen library',
                                 required=False),
    'native_flux_balance_execution': Field('record', 'The native flux balance environment selection (refused for '
                                           'an HPC resource)', required=False),
})


def request_yield_class(request):
    """The old ``ExecutionEpisodeYield._request_yield_class`` for a ``practical_assignment_v1`` request: the class
    of the original execution request without generated identities (copied; the ``compact_<version>`` class it
    gave other versions belonged to the compact flux balance assignments of the local sibling)."""
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def completion_target(assignment):
    """The credit the completion keys earn: the target of the completion controller (new: the old code had a
    completion proof, not a number)."""
    credits = {item['key']: item['credit'] for item in assignment['progress_requirements']}
    return math.fsum(credits[key] for key in assignment['completion_keys'])


def read_from_parent(assignment, message):
    admitted = validate_assignment(dict(assignment))
    return {'assignment': admitted, 'message': dict(message), 'task_yield_class': request_yield_class(admitted),
            'completion_target': completion_target(admitted)}
