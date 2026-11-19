"""What the commissioner gives: the old ``execution_launch_assignment_v1`` (carried from ``from_parent.py``,
``parent_input_custody.py`` and ``execution_contracts.py``) and the values the old episode obtained from its runner.

Old assignment properties, under the same names: ``version``, ``requests`` (resource_id -> concrete request, at
least one: an API resource uses the API service's request form, a local or HPC resource the practical assignment),
``immutable_input_versions`` (a list), ``constraints`` (``allowed_resource_ids``, ``allowed_kinds``,
``resource_id``, ``kind``, each optional) and ``launch_instructions`` (a selection of the launch-instruction
library).

New fields (listed in the carry-over record as ``new field``): ``scope`` (the old context scope: the children's
assignments and the typed reasoning commit name it), ``input_refs`` (the records the requests name, which the old
``initial_references`` found: passed in custody), ``handoff_unit`` (the old ``configuration.handoff_unit``, which
the credit needs and ``credit`` has no settings), ``already_handed_off_resource_ids`` (the resource ids the old
``initial_known_record_refs`` already held a usable handoff for) and ``scientific_task`` (the old
``services.scientific_parent_task``: the scientific question and selected tool information of a native
protein-structure job).

This is the only place the assignment is read. It validates each request as the old ``_launch`` /
``_validate_request`` did as far as the request itself goes (the library's practical or API assignment check and
the identity of the resource) and derives what the continuation needs: the permitted (eligible) resources, the
kind of each request, the request classes and the credit the uncredited requests can earn. The checks the old
code made against the run's configuration (the resource is bound and of that kind, the workspace is inside the
configured one) need the settings, which this function is not handed: ``yield_estimator.py`` makes them where the
settings are. The old authentication of the launch against the commissioning parent, the protein-structure input
validation and the immutable-input-version check read the Store or the old journal and are not made here (see
the carry-over record)."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.structural_homology_evidence.execution_contracts import (
    validate_api_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    validate_assignment as validate_practical_assignment)

LAUNCH_VERSION = 'execution_launch_assignment_v1'
API_VERSIONS = ('api_execution_assignment_v1', 'api_service_assignment_v1')
PRACTICAL_VERSION = 'practical_assignment_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The permitted concrete execution requests: one per bound resource, resource_id -> '
                      'request (an API service assignment, or a practical assignment for a local or HPC '
                      'resource), at least one'),
    'immutable_input_versions': Field('list', 'The input versions that stay fixed while the work runs'),
    'constraints': Field('record', "The commissioner's constraints: allowed_resource_ids, allowed_kinds, "
                         'resource_id and kind, each optional'),
    'launch_instructions': Field('record', 'The pinned selection from the launch-instruction library, when the '
                                 'commissioner pinned one', required=False),
    'scope': Field('record', 'The subject scope fixed by the commissioner'),
    'input_refs': Field('record_refs', 'The records the requests name (protein-structure inputs and the like), '
                        'passed in custody', required=False),
    'handoff_unit': Field('number', 'The credit one usable handoff of a resource earns'),
    'already_handed_off_resource_ids': Field('list', 'The resource ids that already had a usable handoff when this '
                                             'commission was made; they earn nothing again', required=False),
    'scientific_task': Field('record', 'The scientific question and selected tool information of a native '
                             'protein-structure job, when the commissioner has one', required=False),
})


def request_kind(request):
    """The kind of resource a request is for: ``api`` for the API service versions, the request's own
    ``resource_kind`` for a practical assignment; any other version raises (the old ``_validate_request`` took the
    kind from the configuration; the request states it too)."""
    version = request.get('version')
    if version in API_VERSIONS:
        return 'api'
    if version == PRACTICAL_VERSION:
        return request['resource_kind']
    raise ValueError('invalid_execution_request_version:' + repr(version))


def request_yield_class(request):
    """The old ``ExecutionEpisodeYield._request_yield_class``: the class of the original execution request without
    generated identities."""
    if request['version'] != PRACTICAL_VERSION:
        parts = ['api', request.get('service', 'unknown')]
        for field in ('algorithm', 'database'):
            if field in request:
                parts.append(request[field])
        return '_'.join(parts) + '_handoff'
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind'], *native,
             {'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']]]
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
    """The old ``_validate_request`` as far as the request itself goes: the library's check of the API or the
    practical assignment, and the request names the resource it is filed under."""
    if not isinstance(request, dict):
        raise ValueError('invalid_execution_request')
    kind = request_kind(request)
    validated = (validate_api_assignment(request) if kind == 'api' else validate_practical_assignment(request))
    if validated.get('resource_id', resource_id) != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    return validated


def read_from_parent(assignment, message):
    """The parent input: every assignment field, the validated requests and their kinds, the eligible resources and
    what the continuation derives from them, and the commissioner's message."""
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
    kinds = {resource_id: request_kind(request) for resource_id, request in requests.items()}
    eligible = sorted(resource_id for resource_id in requests if permitted(constraints, resource_id, kinds[resource_id]))
    already = sorted(assignment.get('already_handed_off_resource_ids', []))
    remaining = sorted(set(eligible) - set(already))
    classes = sorted(request_yield_class(requests[resource_id]) for resource_id in eligible)
    return {'version': assignment['version'], 'requests': requests, 'request_kinds': kinds,
            'immutable_input_versions': list(assignment['immutable_input_versions']),
            'constraints': constraints, 'launch_instructions': instructions, 'scope': assignment['scope'],
            'input_refs': list(assignment.get('input_refs', [])), 'handoff_unit': handoff_unit,
            'already_handed_off_resource_ids': already, 'eligible_resource_ids': eligible,
            'task_yield_key': 'launch:' + '+'.join(classes),
            'remaining_credit': handoff_unit * len(remaining),
            'scientific_task': assignment.get('scientific_task'), 'message': dict(message)}
