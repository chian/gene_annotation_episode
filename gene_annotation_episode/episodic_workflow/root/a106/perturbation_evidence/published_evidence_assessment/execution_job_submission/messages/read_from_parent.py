"""What the commissioner gives: the old ``execution_launch_assignment_v1`` (carried from ``from_parent.py``,
``from_parent_launch.py`` and ``execution_contracts.py``) and the values the old episode obtained from its runner.

Old assignment properties, under the same names: ``version``, ``requests`` (resource_id -> concrete API request,
at least one), ``immutable_input_versions``, ``constraints`` (``allowed_resource_ids``, ``allowed_kinds``,
``resource_id``, ``kind``) and ``launch_instructions`` (a selection of the launch-instruction library; the old
schema allowed ``null``: omitted here).

New fields (listed in the carry-over record as ``new field``): ``scope`` (the old context scope: the typed
reasoning commit names it), ``input_refs`` (the records the requests name and the reasoning commit reads, passed in
custody), ``handoff_unit`` (the old ``configuration.handoff_unit``, which the credit needs and ``credit`` has no
settings) and ``already_handed_off_resource_ids`` (the resource ids the old ``initial_known_record_refs`` already
held a usable handoff for).

This is the only place the assignment is read. It validates each request as the old ``_launch`` /
``_validate_request`` did as far as the request itself goes (the library's envelope check and the identity of the
resource) and derives what the continuation needs (the eligible resources, the request classes, the credit the
uncredited requests can earn). The old authentication of the launch against the commissioning parent, the
immutable-input-version check against the Store (``_versions``) and the resource-binding checks against the run's
configuration are not made here (see the carry-over record): the bound-resource test is made in ``task.action``
where the settings are."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.execution_contracts import (
    validate_api_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    validate_selection)

LAUNCH_VERSION = 'execution_launch_assignment_v1'
KIND = 'api'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The permitted concrete execution requests: one per bound resource, resource_id -> '
                      'API service assignment, at least one'),
    'immutable_input_versions': Field('list', 'The input versions that stay fixed while the work runs'),
    'constraints': Field('record', "The commissioner's constraints: allowed_resource_ids, allowed_kinds, "
                         'resource_id and kind, each optional'),
    'launch_instructions': Field('record', 'The pinned selection from the launch-instruction library, when the '
                                 'commissioner pinned one', required=False),
    'scope': Field('record', 'The subject scope fixed by the commissioner'),
    'input_refs': Field('record_refs', 'The records the requests name and the reasoning commit reads, passed in '
                        'custody', required=False),
    'handoff_unit': Field('number', 'The credit one usable handoff of a resource earns'),
    'already_handed_off_resource_ids': Field('list', 'The resource ids that already had a usable handoff when this '
                                             'commission was made; they earn nothing again', required=False),
})


def request_yield_class(request):
    """The old ``ExecutionEpisodeYield._request_yield_class``: the class of the original execution request without
    generated identities."""
    parts = ['api', request.get('service', 'unknown')]
    for field in ('algorithm', 'database'):
        if field in request:
            parts.append(request[field])
    return '_'.join(parts) + '_handoff'


def check_constraints(constraints):
    """The old ``_constraints``: the resource constraints are lists of non-empty strings."""
    for key in ('allowed_resource_ids', 'allowed_kinds'):
        if key in constraints and (not isinstance(constraints[key], list) or any(
                not isinstance(item, str) or not item for item in constraints[key])):
            raise ValueError('invalid_execution_resource_constraints')


def permitted(constraints, resource_id):
    """The old ``_permitted`` for a resource that has a request (every resource of this episode is of kind
    ``api``): the constraints allow its id and its kind."""
    return (('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or KIND in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or KIND == constraints['kind']))


def validate_request(resource_id, request):
    """The old ``_validate_request`` as far as the request itself goes: the library's check of the API service
    assignment, and the request names the resource it is filed under. The concrete closed request schema of the
    bound resource (old ``api_execution.assignment_schema`` / ``validate_assignment``) is not in the library: the
    request is an open record here (BLOCKED-ON-JOB-SERVICE, see the carry-over record)."""
    validated = validate_api_assignment(request)
    if validated.get('resource_id') != resource_id:
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
    eligible = sorted(resource_id for resource_id in requests if permitted(constraints, resource_id))
    already = sorted(assignment.get('already_handed_off_resource_ids', []))
    remaining = sorted(set(eligible) - set(already))
    classes = sorted(request_yield_class(requests[resource_id]) for resource_id in eligible)
    return {'version': assignment['version'], 'requests': requests,
            'immutable_input_versions': list(assignment['immutable_input_versions']),
            'constraints': constraints, 'launch_instructions': instructions, 'scope': assignment['scope'],
            'input_refs': list(assignment.get('input_refs', [])), 'handoff_unit': handoff_unit,
            'already_handed_off_resource_ids': already, 'eligible_resource_ids': eligible,
            'task_yield_key': 'launch:' + '+'.join(classes),
            'remaining_credit': handoff_unit * len(remaining),
            'message': dict(message)}
