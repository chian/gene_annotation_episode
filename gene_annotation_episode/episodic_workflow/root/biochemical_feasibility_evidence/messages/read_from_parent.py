"""What the commissioner gives (carried from ``from_parent.py`` and ``scientific_assignment_contracts.py``).

``ASSIGNMENT_FORM`` has one field per property of the old ``_ASSIGNMENT`` schema under its old name
(``selection``, ``proposed_annotation_ref``, ``evidence_refs``, ``constraints``, ``context``, ``revision_origin``).
``evidence_refs`` and ``proposed_annotation_ref`` are references to records: the form types them ``record_refs`` so
that the commissioned records are passed in custody (``proposed_annotation_ref`` held exactly one reference, the old
text, because the old head required it whenever yield bindings were configured and a run always has them). Two
fields are new, because the final form needs them: ``scope`` (the old request scope the head read from its
commissioning request) and ``received_record_refs`` (every record the proposed annotation and the evidence name:
a pass carries only the records named). ``read_from_parent`` is the one place the assignment is read.

Carried here from ``ScientificFromParent._assignment``: the closed schema of the selection, of the evidence task and of
the revision origin (``validate_schema``). Not carried (rule 1, a wrong commission fails and nothing checks it
ahead): the resolution of the selection against the process library and tool library
(``ScientificFromParent._selection``, ``tool_library.resolve_tool_info``), the proposed annotation being in scope as a
hypothesis and received by the parent, the authentication of ``revision_origin`` against the parent's recorded
``process.revise`` (``_validate_origin``), the invocation checks (``_invocation``, ``prepare_invocation``,
``required_return_sources``) and the closed-commission authentication. The old ``a110_task`` check against
``task_context(name)`` is kept: it decides the continuation task (``task.task_context``)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    ContractError, obj, validate_schema)

from ..task import task_context

AXIS = 'A110'
# The old A110 projector was ``finding_progress()``: one credit unit per distinct retained finding, unit 1 (the old
# ``component_axis_workflow`` is not placed; the unit is the one of the earlier port's copy of ``finding_progress``).
FINDING_UNIT = 1
ARCHETYPE = 'received_scientific_finding_progress'

_SHA256 = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
_TEXT = {'type': 'string', 'minLength': 1}


def _ref_schema(slot, prefix):
    return obj({'version': {'const': 'biochemical_feasibility_evidence_option_ref'}, 'library_id': _SHA256,
                'slot': {'const': slot}, 'option_id': {'type': 'string', 'pattern': '^' + prefix + '[0-9]+$'},
                'entry_sha256': _SHA256})


_EVIDENCE_AXIS = _ref_schema('evidence_axis', 'A')
_EVIDENCE_AXIS['properties']['option_id'] = {'const': AXIS}
_THOUGHT_REF = _ref_schema('thought_pattern', 'P')
_TOOL_SELECTOR = obj({'name': _TEXT, 'resources': {'enum': ['api', 'local', 'hpc']}})
_TOOL_INFO = obj({**_TOOL_SELECTOR['properties'], 'description': _TEXT, 'instructions': _TEXT})
# The old selection carried a version (``SELECTION_VERSION``, in the old ``biochemical_feasibility_evidence_records``
# which is not placed): here it is any text. A selected tool is a selector or, once the tool library resolved it,
# a selector with its description and instructions.
SELECTION = obj({'version': _TEXT, 'evidence_axis': _EVIDENCE_AXIS, 'thought_pattern': _THOUGHT_REF,
                 'child_tool_info': {'type': 'array', 'items': {'anyOf': [_TOOL_SELECTOR, _TOOL_INFO]},
                                     'uniqueItems': True}})
REVISION_ORIGIN = obj({'version': {'const': 'biochemical_feasibility_evidence_revision_origin'},
                       'parent_invocation_ref': {'type': 'string', 'pattern': '^scientific_invocation_[a-f0-9]{24}$'},
                       'preparation_operation_ref': {'type': 'string', 'pattern': '^operation_[a-f0-9]{24}$'}})
EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task'}, 'kind': {'const': 'whole_axis_findings'},
                     'evidence_axis': {'const': AXIS},
                     'credit_unit': {'type': 'number', 'exclusiveMinimum': 0,
                                     'description': 'Use the finding unit in the explicitly configured credit '
                                                    'definition for this exact task; do not select or change its '
                                                    'cutoff.'}})
CONTEXT = {'type': 'object', 'properties': {'evidence_task': EVIDENCE_TASK}}

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The parent-selected investigation: the evidence axis option (A110), the thought '
                                 'pattern option and the child tool selectors (name and resources api, local or hpc)'),
    'proposed_annotation_ref': Field('record_refs', 'The proposed annotation this task evaluates: exactly one '
                                                    'hypothesis record, passed in custody'),
    'evidence_refs': Field('record_refs', 'The evidence records the parent selected, passed in custody'),
    'constraints': Field('record', "The parent's constraints"),
    'context': Field('record', 'The parent-supplied context; optionally the evidence_axis_task task and the A110 '
                               'task name (a110_task)'),
    'revision_origin': Field('record', 'The origin of an alternative process this episode revises, when it is one',
                             required=False),
    # New fields the final form needs.
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'Every record the proposed annotation and the evidence name, '
                                                 'passed in custody (new field: a pass carries only the records '
                                                 'named)', required=False),
})


def read_from_parent(assignment, message):
    """The parent input: the admitted assignment fields, the scope, the continuation task and the credit unit."""
    selection = validate_selection(plain(assignment['selection']))
    context = plain(assignment['context'])
    validate_schema(context, CONTEXT)
    if len(assignment['proposed_annotation_ref']) != 1:
        raise ContractError('scientific_task_proposed_annotation_required')
    revision = plain(assignment['revision_origin']) if 'revision_origin' in assignment else None
    if revision is not None:
        validate_schema(revision, REVISION_ORIGIN)
    task = context.get('a110_task')
    if task is not None and (not isinstance(task, dict) or task != task_context(task.get('name'))):
        raise ContractError('component_axis_original_task_context_mismatch')
    continuation_task = AXIS + ':' + (task['name'] if task is not None else ARCHETYPE)
    return {'selection': selection, 'proposed_annotation_ref': assignment['proposed_annotation_ref'][0],
            'evidence_refs': list(assignment['evidence_refs']), 'constraints': plain(assignment['constraints']),
            'context': context, 'revision_origin': revision, 'scope': plain(assignment['scope']),
            'received_record_refs': list(assignment.get('received_record_refs', [])),
            'finding_unit': FINDING_UNIT, 'continuation_task': continuation_task, 'message': plain(message)}


def validate_selection(selection):
    """The closed selection record (the old ``validate_selection`` of the records module is not placed; the schema
    is the old ``_SELECTION``)."""
    validate_schema(selection, SELECTION)
    return selection
