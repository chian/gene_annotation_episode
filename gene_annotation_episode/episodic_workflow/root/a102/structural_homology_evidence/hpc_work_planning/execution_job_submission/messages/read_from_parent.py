"""What the commissioner gives: the old ``execution_launch_assignment_v1`` (carried from ``from_parent.py``,
``parent_input_custody.py`` and ``execution_contracts.py``) and the values the old episode obtained from its
runner.

Old assignment properties, under the same names: ``version``, ``requests`` (resource_id -> concrete request, at
least one), ``immutable_input_versions``, ``constraints`` (``allowed_resource_ids``, ``allowed_kinds``,
``resource_id``, ``kind``) and ``launch_instructions`` (a selection of the launch-instruction library; the old
schema allowed ``null``: omitted here).

New fields (listed in the carry-over record as ``new field``): ``scope`` (the old request message carried it and
the API child reads it), ``input_refs`` (the records the requests name, passed in custody: the old
``initial_references`` of the protein-structure job inputs), ``handoff_unit`` (the old ``configuration.handoff_unit``,
which the credit needs and ``credit`` has no settings), ``already_handed_off_resource_ids`` (the resource ids the old
``initial_known_record_refs`` already held a usable handoff for), ``scientific_task`` (the old
``services.scientific_parent_task`` that the local protein-structure child reads).

This is the only place the assignment is read. It validates each request as the old ``prepare_assignment`` /
``_launch`` did and derives what the continuation needs (the eligible resources, the request classes, the credit
the uncredited requests can earn). The old authentication of the launch against the commissioning parent
(``authenticate_launch``), the protein-structure job-input and immutable-input-version checks against the Store and
the resource-binding checks against the run's configuration are not made here (see the carry-over record)."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    ASSIGNMENT_VERSION, validate_assignment)

LAUNCH_VERSION = 'execution_launch_assignment_v1'
API_VERSIONS = ('api_execution_assignment_v1', 'api_service_assignment_v1')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The permitted concrete execution requests: one per bound resource, resource_id -> '
                      'request (a practical assignment for a local or hpc resource, an API service assignment for '
                      'an api resource), at least one'),
    'immutable_input_versions': Field('list', 'The input versions that stay fixed while the work runs'),
    'constraints': Field('record', 'The commissioner\'s constraints: allowed_resource_ids, allowed_kinds, '
                         'resource_id and kind, each optional'),
    'launch_instructions': Field('record', 'The pinned selection from the launch-instruction library, when the '
                                 'commissioner pinned one', required=False),
    'scope': Field('record', 'The subject scope fixed by the commissioner'),
    'input_refs': Field('record_refs', 'The records the requests name (protein-structure job inputs, pinned input '
                        'versions), passed in custody'),
    'handoff_unit': Field('number', 'The credit one usable handoff of a resource earns'),
    'already_handed_off_resource_ids': Field('list', 'The resource ids that already had a usable handoff when '
                                             'this commission was made; they earn nothing again', required=False),
    'scientific_task': Field('record', 'The scientific parent task (scientific_question, selected_tool_info) of a '
                             'native protein-structure job', required=False),
})


def request_kind(request):
    """The kind of resource a request is for: ``local``, ``hpc`` or ``api`` (the old ``KINDS`` of the resource's
    configured kind, read from the request: a practical request fixes ``resource_kind``)."""
    version = request.get('version')
    if version in API_VERSIONS:
        return 'api'
    if version == ASSIGNMENT_VERSION:
        return request['resource_kind']
    raise ValueError('execution_request_version_unknown:' + str(version))


def request_yield_class(request):
    """The old ``ExecutionEpisodeYield._request_yield_class``: the class of the original execution request
    without generated identities."""
    version = request.get('version')
    if version != ASSIGNMENT_VERSION:
        if version in API_VERSIONS:
            parts = ['api', request.get('service', 'unknown')]
            for field in ('algorithm', 'database'):
                if field in request:
                    parts.append(request[field])
            return '_'.join(parts) + '_handoff'
        return 'compact_' + str(version)
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def check_constraints(constraints):
    """The old ``_constraints``: the resource constraints are lists of non-empty strings."""
    for key in ('allowed_resource_ids', 'allowed_kinds'):
        if key in constraints and (not isinstance(constraints[key], list) or any(
                not isinstance(item, str) or not item for item in constraints[key])):
            raise ValueError('invalid_execution_resource_constraints')


def permitted(constraints, resource_id, kind):
    """The old ``_permitted`` for a resource that has a request: the constraints allow its id and its kind."""
    return (('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or kind == constraints['kind']))


def validate_request(resource_id, request):
    """The old ``_validate_request`` as far as the request itself goes: a practical request is the library's
    ``validate_assignment`` and names its own resource. An API request needs the API service execution of the
    old shared module ``api_service_execution``, which is not in the library (unplaced): it raises."""
    kind = request_kind(request)
    if kind == 'api':
        raise NotImplementedError('a102_api_service_execution_not_in_library:validate_assignment')
    validated = validate_assignment(dict(request))
    if validated['resource_id'] != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    return validated


def read_from_parent(assignment, message):
    """The parent input: every assignment field, the validated requests, the eligible resources and what the
    continuation derives from them, and the commissioner's message."""
    constraints = dict(assignment['constraints'])
    check_constraints(constraints)
    if not assignment['requests']:
        raise ValueError('execution_requests_required')
    handoff_unit = assignment['handoff_unit']
    if not handoff_unit > 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    instructions = assignment.get('launch_instructions')
    if instructions is not None:
        instructions = validate_selection(dict(instructions))
    requests = {resource_id: validate_request(resource_id, request)
                for resource_id, request in assignment['requests'].items()}
    eligible = sorted(resource_id for resource_id, request in requests.items()
                      if permitted(constraints, resource_id, request_kind(request)))
    already = sorted(assignment.get('already_handed_off_resource_ids', []))
    remaining = sorted(set(eligible) - set(already))
    classes = sorted(request_yield_class(requests[resource_id]) for resource_id in eligible)
    return {'version': assignment['version'], 'requests': requests,
            'immutable_input_versions': list(assignment['immutable_input_versions']),
            'constraints': constraints, 'launch_instructions': instructions, 'scope': assignment['scope'],
            'input_refs': list(assignment['input_refs']), 'handoff_unit': handoff_unit,
            'already_handed_off_resource_ids': already,
            'scientific_task': assignment.get('scientific_task'),
            'eligible_resource_ids': eligible,
            'request_kinds': {resource_id: request_kind(requests[resource_id]) for resource_id in requests},
            'task_yield_key': 'launch:' + '+'.join(classes),
            'remaining_credit': math.fsum([handoff_unit] * len(remaining)),
            'message': dict(message)}
