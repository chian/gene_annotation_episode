"""What the commissioning parent gives (carried from ``from_parent.py``; the only place the assignment is read).

Old assignment properties of ``execution_launch_assignment_v1``, under the same names: ``version``, ``requests``
(a map resource_id -> one concrete execution request: ``practical_assignment_v1`` for a local or HPC resource, an
``api_execution_assignment_v1`` or ``api_service_assignment_v1`` for an API service), ``immutable_input_versions``,
``constraints`` (``allowed_resource_ids``, ``allowed_kinds``, ``resource_id``, ``kind``) and
``launch_instructions``.

New fields (each is a "new field" in the carry-over record): ``input_refs`` (the records the jobs read, passed in
custody; the old code re-read them from the parent's own assignment), ``handoff_unit`` (the credit one received
usable handoff earns; the old code read it from its configuration and ``credit`` has no settings),
``already_handed_off`` (the resource ids that already had a usable handoff when the commission began; the old code
derived them from the records it had received), ``scientific_task`` (the ancestor's question and selected tool
information; the old code asked a services callback) and ``hpc_execution_job`` (the plan's job under an HPC parent;
the old code was handed it at its first decision).

``read_from_parent`` checks the original assignment (the old ``_launch``, ``_validate_request`` and
``_constraints``) and derives what ``credit.py`` and ``yield_estimator.py`` need: the permitted requests, the
yield class and the maximum credit of the launch endpoint."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.execution_contracts import (
    validate_api_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    validate_assignment)

VERSION = 'execution_launch_assignment_v1'
PRACTICAL_VERSION = 'practical_assignment_v1'
API_VERSIONS = ('api_execution_assignment_v1', 'api_service_assignment_v1')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The launch assignment version', VERSION),
    'requests': Field('record', 'One concrete execution request per bound resource_id, at least one'),
    'immutable_input_versions': Field('list', 'The pinned versions of the job inputs'),
    'constraints': Field('record', 'allowed_resource_ids, allowed_kinds, resource_id and kind: which resources are '
                                   'permitted'),
    'launch_instructions': Field('record', 'A selection from the launch-instruction library, passed to the '
                                           'children', required=False),
    'input_refs': Field('record_refs', 'The records the jobs read, passed in custody (new field)', required=False),
    'handoff_unit': Field('number', 'The credit one received usable handoff earns (new field)'),
    'already_handed_off': Field('list', 'The resource ids that already had a usable handoff when the commission '
                                        'began (new field)'),
    'scientific_task': Field('record', 'The ancestor\'s scientific_question and selected_tool_info (new field)',
                             required=False),
    'hpc_execution_job': Field('record', 'The frozen plan\'s job under an HPC parent (new field)', required=False),
})


def request_kind(request):
    """The resource kind of one request: ``api`` for an API assignment, else the practical request's kind."""
    if request['version'] == PRACTICAL_VERSION:
        return request['resource_kind']
    if request['version'] in API_VERSIONS:
        return 'api'
    raise ValueError('execution_request_version_not_carried:' + str(request['version']))


def validate_request(request, resource_id):
    """The old ``_validate_request``: the request's own contract, and the resource it names."""
    if request.get('resource_id') != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    if request.get('version') == PRACTICAL_VERSION:
        validate_assignment(request)
    elif request.get('version') in API_VERSIONS:
        validate_api_assignment(request)
    else:
        raise ValueError('execution_request_version_not_carried:' + str(request.get('version')))


def validate_constraints(constraints):
    """The old ``_constraints``."""
    for key in ('allowed_resource_ids', 'allowed_kinds'):
        if key in constraints and (not isinstance(constraints[key], list)
                                   or any(not isinstance(item, str) or not item for item in constraints[key])):
            raise ValueError('invalid_execution_resource_constraints')


def permitted(request, constraints):
    """The old ``_permitted``: whether the constraints permit the request's resource."""
    kind, resource_id = request_kind(request), request['resource_id']
    return (('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or kind == constraints['kind']))


def request_yield_class(request):
    """The old ``_request_yield_class``: classify the original request without generated identities."""
    version = request.get('version')
    if version != PRACTICAL_VERSION:
        if version in API_VERSIONS:
            parts = ['api', request.get('service', 'unknown')]
            for field in ('algorithm', 'database'):
                if field in request:
                    parts.append(request[field])
            return '_'.join(parts) + '_handoff'
        return 'compact_' + str(version)
    native = sorted(key for key in request['requested_job'] if key.startswith('native_'))
    parts = ['practical', request['resource_kind'], *native]
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def read_from_parent(assignment, message):
    requests = {resource_id: dict(request) for resource_id, request in assignment['requests'].items()}
    if not requests:
        raise ValueError('execution_launch_requires_a_request')
    for resource_id, request in requests.items():
        validate_request(request, resource_id)
    constraints = dict(assignment['constraints'])
    validate_constraints(constraints)
    eligible = [resource_id for resource_id, request in requests.items() if permitted(request, constraints)]
    handed_off = list(assignment['already_handed_off'])
    remaining = [resource_id for resource_id in eligible if resource_id not in handed_off]
    handoff_unit = assignment['handoff_unit']
    if not math.isfinite(handoff_unit) or handoff_unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    return {'requests': requests, 'immutable_input_versions': list(assignment['immutable_input_versions']),
            'constraints': constraints, 'launch_instructions': assignment.get('launch_instructions'),
            'input_refs': list(assignment.get('input_refs', [])), 'handoff_unit': handoff_unit,
            'already_handed_off': handed_off, 'scientific_task': assignment.get('scientific_task'),
            'hpc_execution_job': assignment.get('hpc_execution_job'),
            'permitted_resource_ids': eligible,
            'yield_class': '+'.join(sorted(request_yield_class(requests[resource_id]) for resource_id in eligible)),
            'maximum_credit': math.fsum(handoff_unit for _ in remaining)}
