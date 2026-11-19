"""What the commissioner gives: the launch assignment (the old ``execution_launch_assignment_v1`` of ``from_parent.py``
and ``from_parent_launch.py``: ``version``, ``requests``, ``immutable_input_versions``, ``constraints``,
``launch_instructions``, one field per property of the old assignment schema, under the same names) and the values
the old episode obtained from its runner.

This is the only place the assignment is read. The old ``_launch`` check of the assignment itself (every request is a
closed concrete API request, the request map key is the request's resource_id, the constraints are lists of text) is
made here and raises. The old ``prepare_assignment`` checks of the commission (the pinned input versions against the
Store, the native input custody) are checks of a commission: a wrong commission fails and nothing checks it ahead
(owner's rule 1), so none is carried. What they stood for in custody is the ``record_refs`` field. The concrete
request schema of each resource (the old ``api_execution.assignment_schema``) belongs to the job service: here a
request is checked against the closed API service envelope of the library (``validate_api_assignment``) and the
service's own check is the ``job_access`` call of ``task.py``.

Which requests may be commissioned is decided here from the assignment alone (the old ``_permitted``, every resource
here is of kind ``api``): ``parent_input['permitted']`` is what the task, the summary and the yield estimator read. The
old ``ExecutionEpisodeYield._request_yield_class`` is ``_yield_class`` here (the classes of the profile key of the
continuation).

New fields the final form needs, all listed in the carry-over record as ``new field``: ``record_refs`` (the old code
read the job inputs from the Store by reference), ``handoff_unit`` (an old configuration value: ``credit`` has no
settings, and the API child takes it as its completion target), ``scope`` (the subject scope the old runner passed to
``prepare_assignment``; the API child requires it) and ``received_handoff_resources`` (the resources whose usable
handoff the old receipts ledger already held at the start: the old ``initial_known_record_refs``)."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.execution_contracts import (
    validate_api_assignment)

LAUNCH_VERSION = 'execution_launch_assignment_v1'
# The old ``ROLE_KINDS`` inverted: the launch child that owns each kind of resource (the only kind is ``api``).
KIND_SLOTS = {'api': 'launch_api'}

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The concrete execution requests by resource id, at least one: each is the closed '
                                'API service request of that resource (api_service_assignment_v1)'),
    'immutable_input_versions': Field('list', 'The input versions the job is pinned to: reference, version and '
                                              'content digest'),
    'constraints': Field('record', "The commissioner's resource constraints: allowed_resource_ids, allowed_kinds, "
                                   'resource_id and kind'),
    'launch_instructions': Field('record', 'The launch instruction sections selected for this launch',
                                 required=False),
    # New fields the final form needs (the old code read them from the configuration, from the runner and from the
    # old receipts ledger).
    'record_refs': Field('record_refs', 'Every record the job inputs name (pinned input versions, the input '
                                        'subjects), passed in custody', required=False),
    'handoff_unit': Field('number', 'Operational credit for each new distinct usable handoff of a resource '
                                    '(old configuration handoff_unit)'),
    'scope': Field('record', 'The subject scope fixed by the commissioner (old runner scope); the API request is '
                             'commissioned with it'),
    'received_handoff_resources': Field('list', 'The resource ids that already had a usable handoff when this launch '
                                                'began (the old initial known handoff records)', required=False),
})


def _constraints(constraints):
    """The old ``_constraints``: the resource constraints are lists of non-empty text."""
    for key in ('allowed_resource_ids', 'allowed_kinds'):
        if key in constraints and (not isinstance(constraints[key], list)
                                   or any(not isinstance(item, str) or not item for item in constraints[key])):
            raise ValueError('invalid_execution_resource_constraints')


def _request(resource_id, request):
    """The old ``_validate_request`` of one request without the configured resource: the request is closed and names
    its resource."""
    if not isinstance(request, dict):
        raise ValueError('invalid_execution_launch_assignment')
    request = validate_api_assignment(request)
    if request.get('resource_id') != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    return request


def _yield_class(request):
    """The old ``ExecutionEpisodeYield._request_yield_class``: the class of the original execution request without
    generated identities."""
    parts = ['api', request.get('service', 'unknown')]
    for field in ('algorithm', 'database'):
        if field in request:
            parts.append(request[field])
    return '_'.join(parts) + '_handoff'


def _permitted(constraints, resource_id, kind):
    """The old ``_permitted``: the resource's request may be commissioned under the constraints."""
    return (('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or kind == constraints['kind']))


def read_from_parent(assignment, message):
    """The validated launch assignment as the parent input, with the requests that may be commissioned."""
    if not assignment['requests']:
        raise ValueError('invalid_execution_launch_assignment')
    unit = assignment['handoff_unit']
    if unit <= 0 or not math.isfinite(unit):
        raise ValueError('explicit_positive_operational_credit_units_required')
    constraints = assignment['constraints']
    _constraints(constraints)
    requests = {resource_id: _request(resource_id, request) for resource_id, request in assignment['requests'].items()}
    permitted = {resource_id: {'slot': KIND_SLOTS['api'], 'kind': 'api', 'yield_class': _yield_class(request)}
                 for resource_id, request in requests.items() if _permitted(constraints, resource_id, 'api')}
    if not permitted:
        raise ValueError('execution_no_permitted_request')
    parent_input = {'assignment': {'version': assignment['version'], 'requests': requests,
                                   'immutable_input_versions': list(assignment['immutable_input_versions']),
                                   'constraints': constraints},
                    'message': dict(message),
                    'record_refs': list(assignment.get('record_refs', [])),
                    'handoff_unit': unit,
                    'scope': assignment['scope'],
                    'received_handoff_resources': sorted(set(assignment.get('received_handoff_resources', []))),
                    'permitted': permitted}
    if 'launch_instructions' in assignment:
        parent_input['assignment']['launch_instructions'] = assignment['launch_instructions']
    return parent_input
