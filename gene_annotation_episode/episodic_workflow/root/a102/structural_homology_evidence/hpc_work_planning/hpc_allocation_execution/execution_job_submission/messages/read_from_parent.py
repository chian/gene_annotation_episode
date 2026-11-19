"""What the commissioning parent gives (carried from ``from_parent.py`` and ``parent_input_custody.py``).

Old assignment properties of ``execution_launch_assignment_v1``, under the same names: ``version``, ``requests``
(one concrete execution request per bound ``resource_id``: ``practical_assignment_v1`` for a local or HPC
resource, an API assignment for an API service), ``immutable_input_versions``, ``constraints``
(``allowed_resource_ids``, ``allowed_kinds``, ``resource_id``, ``kind``) and ``launch_instructions``.

Fields the old code did not have (each is a "new field" in the carry-over record): ``scope`` (the old code took
it from its request), ``input_refs`` (the records the jobs read, passed in custody: the old code re-read them from
the parent's own assignment), ``handoff_unit`` (the credit one received usable handoff earns: the old code read it
from its configuration, and ``credit`` has no settings), ``already_handed_off`` (the resource ids that already had
a usable handoff when the commission began: the old code derived them from the records it had received),
``scientific_task`` (the ancestor's question and selected tool information, for a native protein-structure job:
the old code asked a services callback) and ``hpc_execution_job`` (the plan's job under an HPC parent: the old
code was handed it at its first decision).

``read_from_parent`` is the only place the assignment is read. It derives from it what ``yield_estimator.py`` and
``credit.py`` need: which requests are eligible, their yield class and the bounded maximum.
"""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    validate_assignment)

VERSION = 'execution_launch_assignment_v1'
PRACTICAL_VERSION = 'practical_assignment_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The launch assignment version', VERSION),
    'requests': Field('list', 'One concrete execution request per bound resource_id (at least one)'),
    'immutable_input_versions': Field('record', 'The pinned versions of the job\'s inputs'),
    'constraints': Field('record', 'allowed_resource_ids, allowed_kinds, resource_id and kind: which resources are '
                                   'permitted'),
    'launch_instructions': Field('record', 'A selection from the launch-instruction library, passed to the '
                                           'children', required=False),
    'scope': Field('record', 'The subject scope fixed by the commissioning parent (new field)'),
    'input_refs': Field('record_refs', 'The records the jobs read, passed in custody (new field)'),
    'handoff_unit': Field('number', 'The credit one received usable handoff earns (new field)'),
    'already_handed_off': Field('list', 'The resource ids that already had a usable handoff when the commission '
                                        'began (new field)'),
    'scientific_task': Field('record', 'The ancestor\'s scientific question and selected tool information for a '
                                       'native protein-structure job (new field)', required=False),
    'hpc_execution_job': Field('record', 'The frozen plan\'s job under an HPC parent: plan id, objective, '
                                         'scientific manifest, acceptance, supplied input file (new field)',
                               required=False),
})


def request_kind(request):
    """The resource kind of one request: ``api`` for an API assignment, else the practical request's kind."""
    if request['version'] == PRACTICAL_VERSION:
        return request['resource_kind']
    return 'api'


def permitted(request, constraints):
    """Whether the assignment's constraints permit the request's resource (reconstructed from the intent record:
    the old ``_permitted`` body could not be read)."""
    kind = request_kind(request)
    for name, value in (('allowed_resource_ids', request['resource_id']), ('allowed_kinds', kind)):
        allowed = constraints.get(name)
        if allowed is not None and value not in allowed:
            return False
    for name, value in (('resource_id', request['resource_id']), ('kind', kind)):
        wanted = constraints.get(name)
        if wanted is not None and value != wanted:
            return False
    return True


def request_yield_class(request):
    """The class of one original request, without generated identities (carried from the old
    ``ExecutionEpisodeYield._request_yield_class``, reconstructed from the intent record)."""
    version = request['version']
    if version == PRACTICAL_VERSION:
        native = sorted(key for key in request['requested_job'] if key.startswith('native_'))
        parts = ['practical', request['resource_kind'], *native]
        parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
        return '_'.join(parts)
    if version.startswith('api_'):
        parts = ['api', request['service']]
        parts.extend(request[name] for name in ('algorithm', 'database') if request.get(name) is not None)
        parts.append('handoff')
        return '_'.join(parts)
    return 'compact_' + version


def read_from_parent(assignment, message):
    requests = [dict(request) for request in assignment['requests']]
    if not requests:
        raise ValueError('execution_launch_requires_a_request')
    ids = [request['resource_id'] for request in requests]
    if len(set(ids)) != len(ids):
        raise ValueError('execution_launch_requests_must_name_distinct_resource_ids')
    for request in requests:
        if request['version'] == PRACTICAL_VERSION:
            validate_assignment(request)
    constraints = dict(assignment['constraints'])
    handed_off = list(assignment['already_handed_off'])
    eligible = [request for request in requests if permitted(request, constraints)]
    remaining = [request for request in eligible if request['resource_id'] not in handed_off]
    handoff_unit = assignment['handoff_unit']
    classes = sorted({request_yield_class(request) for request in eligible})
    return {'requests': requests, 'immutable_input_versions': assignment['immutable_input_versions'],
            'constraints': constraints, 'launch_instructions': assignment.get('launch_instructions'),
            'scope': assignment['scope'], 'input_refs': list(assignment['input_refs']),
            'handoff_unit': handoff_unit, 'already_handed_off': handed_off,
            'scientific_task': assignment.get('scientific_task'),
            'hpc_execution_job': assignment.get('hpc_execution_job'),
            'permitted_resource_ids': [request['resource_id'] for request in eligible],
            'yield_class': '+'.join(classes),
            'maximum_credit': math.fsum(handoff_unit for _ in remaining)}
