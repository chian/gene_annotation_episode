"""What the commissioner gives: the launch assignment (the old ``execution_launch_assignment_v1`` of ``from_parent.py``:
``requests``, ``immutable_input_versions``, ``constraints``, ``launch_instructions``, each under its old name) and the
records the job inputs name.

This is the only place the assignment is read. The old ``_launch`` check of the assignment itself (every request is a
closed concrete request, the request map key is the request's resource_id, the constraints are lists of text) is
made here and raises. The old ``prepare_assignment`` checks of the commission against the Store and the HPC parent
(``authenticate_launch``, ``validate_native_job_inputs``, ``validate_standard_blast_job_inputs``,
``validate_rna_structure_job_inputs``, ``_masking_inputs``, ``_utility_inputs``, ``_versions``) are checks of a
commission: a wrong commission fails and no episode checks it ahead (rule 1), so none is carried. What they stood
for in custody is the ``record_refs`` field.

Which requests may be commissioned, and on which slot, is decided here from the assignment alone (the old
``_permitted`` and ``allowed_children``, with the kind of the resource taken from the request: the configured kind is
compared with it in ``task.py``): ``parent_input['permitted']`` is what the task, the summary and the yield estimator
read. The old ``ExecutionEpisodeYield._request_yield_class`` is ``request_yield_class`` here (classes of the
continuation profile key).

New fields the final form needs, all listed in the carry-over record as ``new field``: ``record_refs`` (the old code
read the job inputs from the Store by their references), ``handoff_unit`` and ``acquired_record_unit`` (old
configuration values; ``credit`` has no settings), ``scientific_task`` (old ``services.scientific_parent_task``) and
``received_handoff_resources`` (the resources whose usable handoff the old receipts ledger already held at the
start)."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.execution_contracts import (
    validate_api_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import (
    validate_assignment)

LAUNCH_VERSION = 'execution_launch_assignment_v1'
PRACTICAL_VERSION = 'practical_assignment_v1'
API_VERSIONS = ('api_execution_assignment_v1', 'api_service_assignment_v1')
# The old ``ROLE_KINDS`` (``binding_roles.py``) inverted: the launch child that owns each kind of resource.
KIND_SLOTS = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The concrete execution requests by resource id, at least one: each is the closed '
                                'request of that resource (practical_assignment_v1, api_execution_assignment_v1 or '
                                'api_service_assignment_v1)'),
    'immutable_input_versions': Field('list', 'The input versions the job is pinned to: reference, version and '
                                              'content digest'),
    'constraints': Field('record', "The commissioner's resource constraints: allowed_resource_ids, allowed_kinds, "
                                   'resource_id and kind'),
    'launch_instructions': Field('record', 'The launch instruction sections selected for this launch',
                                 required=False),
    'record_refs': Field('record_refs', 'Every record the job inputs name (masking and utility inputs, pinned input '
                                        'versions, the query subject), passed in custody', required=False),
    'handoff_unit': Field('number', 'Operational credit for each new distinct usable handoff of a resource (old '
                                    'configuration handoff_unit)'),
    'acquired_record_unit': Field('number', 'Operational credit unit of an acquired record (old configuration '
                                            'acquired_record_unit); a launch acquires none'),
    'scientific_task': Field('record', 'The scientific parent task: its scientific_question and selected_tool_info '
                                       '(old services.scientific_parent_task)', required=False),
    'received_handoff_resources': Field('list', 'The resource ids that already had a usable handoff when this '
                                                'launch began (the old initial known handoff records)',
                                        required=False),
})


def _constraints(constraints):
    for key in ('allowed_resource_ids', 'allowed_kinds'):
        if key in constraints and (not isinstance(constraints[key], list)
                                   or any(not isinstance(item, str) or not item for item in constraints[key])):
            raise ValueError('invalid_execution_resource_constraints')


def _request(resource_id, request):
    """The old ``_validate_request`` of one request without the configured resource: the request is closed and
    names its resource."""
    if not isinstance(request, dict):
        raise ValueError('invalid_execution_launch_assignment')
    version = request.get('version')
    if version == PRACTICAL_VERSION:
        request = validate_assignment(request)
    elif version in API_VERSIONS:
        request = validate_api_assignment(request)
    else:
        # The old ``a107_blast_execution`` request (``BLAST_GRADED_REQUEST_VERSION`` checked against
        # ``BLAST_GRADED_REQUEST_SCHEMA``, resource service ``ncbi_blast``) has no module in the library today.
        raise NotImplementedError('unplaced:a107_blast_execution.BLAST_GRADED_REQUEST_SCHEMA:' + str(version))
    if request.get('resource_id') != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    return request


def kind_of(request):
    return 'api' if request['version'] in API_VERSIONS else request['resource_kind']


def request_yield_class(request):
    """The old ``ExecutionEpisodeYield._request_yield_class``: the class of the original execution request without
    generated identities."""
    version = request['version']
    if version != PRACTICAL_VERSION:
        parts = ['api', request.get('service', 'unknown')]
        for field in ('algorithm', 'database'):
            if field in request:
                parts.append(request[field])
        return '_'.join(parts) + '_handoff'
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def _permitted(constraints, resource_id, kind):
    """The old ``_permitted``: the resource's request may be commissioned under the constraints."""
    return (('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or kind == constraints['kind']))


def read_from_parent(assignment, message):
    """The validated launch assignment as the parent input, with the requests that may be commissioned."""
    requests = assignment['requests']
    if not requests:
        raise ValueError('invalid_execution_launch_assignment')
    for unit in (assignment['handoff_unit'], assignment['acquired_record_unit']):
        if unit <= 0 or not math.isfinite(unit):
            raise ValueError('explicit_positive_operational_credit_units_required')
    constraints = assignment['constraints']
    _constraints(constraints)
    requests = {resource_id: _request(resource_id, request) for resource_id, request in requests.items()}
    permitted = {resource_id: {'slot': KIND_SLOTS[kind_of(request)], 'kind': kind_of(request),
                               'yield_class': request_yield_class(request)}
                 for resource_id, request in requests.items() if _permitted(constraints, resource_id, kind_of(request))}
    if not permitted:
        raise ValueError('execution_no_permitted_request')
    launch = {'version': assignment['version'], 'requests': requests,
              'immutable_input_versions': list(assignment['immutable_input_versions']), 'constraints': constraints}
    if 'launch_instructions' in assignment:
        launch['launch_instructions'] = assignment['launch_instructions']
    parent_input = {'assignment': launch, 'message': dict(message),
                    'record_refs': list(assignment.get('record_refs', [])),
                    'handoff_unit': assignment['handoff_unit'],
                    'acquired_record_unit': assignment['acquired_record_unit'],
                    'received_handoff_resources': sorted(set(assignment.get('received_handoff_resources', []))),
                    'permitted': permitted}
    if 'scientific_task' in assignment:
        parent_input['scientific_task'] = assignment['scientific_task']
    return parent_input
