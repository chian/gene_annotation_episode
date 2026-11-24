"""What the commissioner gives: the old ``execution_launch_assignment`` (carried from ``from_parent.py``,
``LaunchAssignment.assignment_schema``, ``_launch``, ``_validate_request``, ``_constraints`` and ``_permitted``), and
the values the old episode obtained from its runner and configuration. This file is the only place the assignment
is read.

Old assignment properties, under the same names: ``version``, ``requests`` (resource_id -> one concrete request: a
``practical_assignment`` for a local or HPC resource, an ``api_execution_assignment`` or an
``api_service_assignment`` for an API resource; at least one), ``immutable_input_versions``, ``constraints``
(``allowed_resource_ids``, ``allowed_kinds``, ``resource_id``, ``kind``) and ``launch_instructions`` (a selection of
the launch-instruction library; the old schema allowed null: omitted here).

New fields (listed as ``new field`` in the carry-over record): ``input_refs`` (the old ``initial_references``: the
masking and utility input records of every request, now passed in custody and handed on to the children),
``handoff_unit`` (the old ``configuration.handoff_unit``; ``credit`` has no settings), ``already_handed_off_resource_ids``
(the resource ids the old ``initial_known_record_refs`` already held a usable handoff for) and ``scientific_task``
(the old ``services.scientific_parent_task``: the scientific question and the selected tool information).

Not made here, and why: the old authentication of the launch against the commissioning HPC plan
(``hpc_launch_authentication.authenticate_launch``), the native BLAST database / standard database job-input
validation against the Store, the masking and utility input checks, the immutable-input-version check and the
resource-binding checks against the run's configuration are checks of this episode's own commission against its
parent's records and the run's configuration: a wrong commission fails (rule 1) and the modules are not in the
library. A request of the old BLAST graded request version needs the old ``a103_homology_execution`` module, which
is not in the library: its version is unknown here and is refused."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.execution_contracts import (
    validate_api_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    ASSIGNMENT_VERSION, validate_assignment)

LAUNCH_VERSION = 'execution_launch_assignment'
API_VERSIONS = ('api_execution_assignment', 'api_service_assignment')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The permitted concrete execution requests: one per bound resource, resource_id -> '
                      'request (a practical assignment for a local or hpc resource, an API assignment for an api '
                      'resource), at least one'),
    'immutable_input_versions': Field('list', 'The input versions that stay fixed while the work runs'),
    'constraints': Field('record', "The commissioner's constraints: allowed_resource_ids, allowed_kinds, "
                         'resource_id and kind, each optional'),
    'launch_instructions': Field('record', 'The pinned selection from the launch-instruction library, when the '
                                 'commissioner pinned one', required=False),
    'input_refs': Field('record_refs', 'The masking and utility input records the requests name, passed in custody',
                        required=False),
    'handoff_unit': Field('number', 'The credit one usable handoff of a resource earns'),
    'already_handed_off_resource_ids': Field('list', 'The resource ids that already had a usable handoff when this '
                                             'commission was made; they earn nothing again', required=False),
    'scientific_task': Field('record', 'The scientific parent task (scientific_question, selected_tool_info)',
                             required=False),
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
    """The old ``ExecutionEpisodeYield._request_yield_class``: the class of the original execution request without
    generated identities."""
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
    """The old ``_validate_request`` as far as the request itself goes: the request's own contract and the
    resource it names."""
    kind = request_kind(request)
    validated = validate_api_assignment(dict(request)) if kind == 'api' else validate_assignment(dict(request))
    if validated.get('resource_id', resource_id) != resource_id:
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
    if not math.isfinite(handoff_unit) or handoff_unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    instructions = assignment.get('launch_instructions')
    if instructions is not None:
        instructions = validate_selection(dict(instructions))
    requests = {resource_id: validate_request(resource_id, request)
                for resource_id, request in assignment['requests'].items()}
    kinds = {resource_id: request_kind(request) for resource_id, request in requests.items()}
    eligible = sorted(resource_id for resource_id in requests if permitted(constraints, resource_id, kinds[resource_id]))
    already = sorted(assignment.get('already_handed_off_resource_ids', []))
    remaining = sorted(set(eligible) - set(already))
    classes = sorted(request_yield_class(requests[resource_id]) for resource_id in eligible)
    return {'version': assignment['version'], 'requests': requests,
            'immutable_input_versions': list(assignment['immutable_input_versions']),
            'constraints': constraints, 'launch_instructions': instructions,
            'input_refs': list(assignment.get('input_refs', [])), 'handoff_unit': handoff_unit,
            'already_handed_off_resource_ids': already, 'scientific_task': assignment.get('scientific_task'),
            'eligible_resource_ids': eligible, 'request_kinds': kinds,
            'task_yield_key': 'launch:' + '+'.join(classes),
            'remaining_credit': math.fsum([handoff_unit] * len(remaining)), 'message': dict(message)}
