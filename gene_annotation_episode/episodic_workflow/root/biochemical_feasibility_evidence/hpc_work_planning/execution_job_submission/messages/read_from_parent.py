"""What the commissioner gives: the launch assignment (the old ``execution_launch_assignment``, one field per
property of the old assignment schema, under the same names) and what the new form needs besides.

This is the only place the assignment is read. ``read_from_parent`` admits it as the old ``prepare_assignment``
did (the launch assignment schema; each request as a practical assignment whose ``resource_id`` is its key) and
returns the parent input: the requests, the permitted ones (the old ``_permitted``), the handoff unit, and the
resources already handed off.

Not carried: the old compact flux-balance launch (``flux_balance_requests.preview`` reads the old runner's
request binding), ``authenticate_launch`` (a check of the commission against the planner's ledger: a wrong
commission fails), the check of the immutable input versions against the Store (library not placed) and the old
``_constraints`` validation (library not placed)."""
from copy import deepcopy

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.execution_contracts import (
    checked, obj)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    SELECTION_SCHEMA as LAUNCH_INSTRUCTION_SELECTION_SCHEMA)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    validate_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    INPUT_VERSION_SCHEMA)

LAUNCH_VERSION = 'execution_launch_assignment'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The launch assignment version', LAUNCH_VERSION),
    'requests': Field('record', 'The concrete execution requests by resource_id: each a practical assignment '
                                'with that resource_id (a local or an hpc request)'),
    'immutable_input_versions': Field('list', 'The immutable input versions (reference, version, content '
                                              'sha256) the requests were made against'),
    'constraints': Field('record', 'The caller constraints: allowed_resource_ids, allowed_kinds, resource_id, '
                                   'kind'),
    'launch_instructions': Field('record', 'The exact launch instruction sections the commissioner selected',
                                 required=False),
    # New fields the final form needs (the old code read them from configuration, the parent's ledger or the
    # run's receipts).
    'handoff_unit': Field('number', 'The credit of one usable handoff of one original request (old '
                                    'configuration handoff_unit)'),
    'handed_off_resource_ids': Field('list', 'The resource_ids whose usable handoff the commissioner already '
                                             'holds (the old initial known records)', required=False),
    'record_refs': Field('record_refs', 'Every record the job inputs name (the flux-balance input versions), '
                                        'passed in custody', required=False),
    'scientific_task': Field('record', 'The scientific parent task: its scientific_question and '
                                       'selected_tool_info (old services.scientific_parent_task)',
                             required=False),
    'hpc_execution_job': Field('record', 'The actual job inputs and acceptance the HPC planner froze for this '
                                         'launch (old LaunchPreparation.initial_decision_context)',
                               required=False),
})

KINDS = ('local', 'hpc')
_OLD_FIELDS = ('version', 'requests', 'immutable_input_versions', 'constraints', 'launch_instructions')


def launch_schema(request_ids):
    """The old ``assignment_schema('launch')`` for the requests it holds."""
    schema = obj({'version': {'type': 'string', 'const': LAUNCH_VERSION},
                  'requests': {'type': 'object', 'minProperties': 1, 'additionalProperties': False,
                               'properties': {key: {'type': 'object'} for key in request_ids}},
                  'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)},
                  'constraints': {'type': 'object'}})
    schema['properties']['launch_instructions'] = deepcopy(LAUNCH_INSTRUCTION_SELECTION_SCHEMA)
    return schema


def permitted(assignment, resource_id):
    """The old ``_permitted``: whether the launch constraints permit the request of ``resource_id``."""
    constraints = assignment['constraints']
    request = assignment['requests'][resource_id]
    kind = request['resource_kind']
    return (('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or kind == constraints['kind']))


def read_from_parent(assignment, message):
    launch = checked({name: assignment[name] for name in _OLD_FIELDS if name in assignment},
                     launch_schema(assignment['requests']), 'invalid_execution_launch_assignment')
    requests = {}
    for resource_id, request in launch['requests'].items():
        request = validate_assignment(dict(request))
        if request['resource_id'] != resource_id or request['resource_kind'] not in KINDS:
            raise ValueError('invalid_execution_request:' + resource_id)
        requests[resource_id] = request
    launch['requests'] = requests
    if assignment['handoff_unit'] <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    eligible = [resource_id for resource_id in requests if permitted(launch, resource_id)]
    parent_input = {**launch, 'eligible': eligible, 'handoff_unit': assignment['handoff_unit'],
                    'handed_off_resource_ids': list(assignment.get('handed_off_resource_ids', [])),
                    'record_refs': list(assignment.get('record_refs', []))}
    for name in ('scientific_task', 'hpc_execution_job'):
        if name in assignment:
            parent_input[name] = assignment[name]
    return parent_input
