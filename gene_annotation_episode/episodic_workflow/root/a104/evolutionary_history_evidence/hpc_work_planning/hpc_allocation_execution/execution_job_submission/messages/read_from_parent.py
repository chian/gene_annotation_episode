"""What the parent gives: the launch assignment (the old ``execution_launch_assignment``, one field per property
of the old assignment schema, under the same names), and the records the job inputs name.

This is the only place the assignment is read. The old ``_launch`` check of the assignment itself (every request
is a closed concrete request of its resource, the request map key is the request's resource_id, the constraints
are lists of text) is made here and raises. The old ``prepare_assignment`` checks of the commission (the HPC
parent's ``authenticate_launch``, the masking, utility, native and standard BLAST database inputs, the pinned input
versions) are checks of a commission: a wrong commission fails and nothing checks it ahead (rule 1), so they are
not carried.

Which requests may be commissioned, and on which slot, is decided here from the assignment alone (the old
``_permitted`` and ``allowed_children``, with the resource kind taken from the request instead of the configured
resource): the result is ``parent_input['permitted']``, which the task, the summary and the yield estimator read."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.execution_contracts import (
    validate_api_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import (
    validate_assignment)

LAUNCH_VERSION = 'execution_launch_assignment'
# The old ROLE_KINDS: the launch child that owns each resource kind.
KIND_SLOTS = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The concrete execution requests by resource id, at least one: each is the closed '
                                'request of that resource (practical_assignment, api_execution_assignment or '
                                'api_service_assignment)'),
    'immutable_input_versions': Field('list', 'The input versions the job is pinned to: reference, version and '
                                              'content digest'),
    'constraints': Field('record', "The commissioner's resource constraints: allowed_resource_ids, allowed_kinds, "
                                   'resource_id and kind'),
    'launch_instructions': Field('record', 'The launch instruction sections selected for this launch',
                                 required=False),
    # New fields the final form needs (the old code read them from the configuration, from the commissioning
    # request and from the old receipts ledger).
    'record_refs': Field('record_refs', 'Every record the job inputs name (masking and utility inputs, pinned '
                                        'input versions, the query subject), passed in custody', required=False),
    'handoff_unit': Field('number', 'Operational credit for each new distinct usable handoff of a resource '
                                    '(old configuration handoff_unit)'),
    'acquired_record_unit': Field('number', 'Operational credit unit of an acquired record (old configuration '
                                            'acquired_record_unit); an API launch child is commissioned with it'),
    'scientific_task': Field('record', 'The scientific parent task: its scientific_question and selected_tool_info '
                                       '(old services.scientific_parent_task)', required=False),
    'received_handoff_resources': Field('list', 'The resource ids that already had a usable handoff when this launch '
                                                'began (the old initial known handoff records)', required=False),
})


def _constraints(constraints):
    for key in ('allowed_resource_ids', 'allowed_kinds'):
        if key in constraints and (not isinstance(constraints[key], list)
                                   or any(not isinstance(item, str) or not item for item in constraints[key])):
            raise ValueError('invalid_execution_resource_constraints')


def _request(resource_id, request):
    """The old ``_validate_request`` without the configured resource: the request is closed and names its resource."""
    if not isinstance(request, dict):
        raise ValueError('invalid_execution_launch_assignment')
    if request.get('version') == 'practical_assignment':
        request = validate_assignment(request)
    else:
        request = validate_api_assignment(request)
    if request.get('resource_id', resource_id) != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    return request


def _kind(request):
    return 'api' if request['version'] != 'practical_assignment' else request['resource_kind']


def _yield_class(request):
    """Classify the original execution request without generated IDs (old ``_request_yield_class``)."""
    version = request['version']
    if version != 'practical_assignment':
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
    permitted = {resource_id: {'slot': KIND_SLOTS[_kind(request)], 'kind': _kind(request),
                               'yield_class': _yield_class(request)}
                 for resource_id, request in requests.items() if _permitted(constraints, resource_id, _kind(request))}
    parent_input = {'assignment': {'version': assignment['version'], 'requests': requests,
                                   'immutable_input_versions': list(assignment['immutable_input_versions']),
                                   'constraints': constraints},
                    'record_refs': list(assignment.get('record_refs', [])),
                    'handoff_unit': assignment['handoff_unit'],
                    'acquired_record_unit': assignment['acquired_record_unit'],
                    'received_handoff_resources': sorted(set(assignment.get('received_handoff_resources', []))),
                    'permitted': permitted}
    if 'launch_instructions' in assignment:
        parent_input['assignment']['launch_instructions'] = assignment['launch_instructions']
    if 'scientific_task' in assignment:
        parent_input['scientific_task'] = assignment['scientific_task']
    return parent_input
