"""What the commissioner gives: the old ``_ASSIGNMENT`` of ``scientific_contracts.py`` (``from_parent.py``,
``ScientificAssignment.assignment_schema``), one field per property under its name. This is the only place the
assignment is read.

- ``selection``: the evidence axis (the library option ``A105``), the thought pattern (a library ``P...`` option) and
  ``child_tool_info`` (the tools of this head, by name and resource), the old ``_SELECTION``. The library is the
  frozen experimental-activity library (``settings['library_directory']``): the option references are resolved
  against it where the model is shown them (``task.py``).
- ``proposed_annotation_ref``, ``evidence_refs`` (the records the commissioner gives, passed in custody),
  ``constraints``, ``context`` (the declared whole-axis finding task and its credit unit, the old
  ``_EVIDENCE_TASK``) and ``revision_origin`` (the old ``_REVISION_ORIGIN``, which ``process.revise`` prepares).
- ``scope`` is a new field: the old episode took the scope from its request. The Store scope the commission is about;
  the records of its subjects, the proposed annotation record and the other records the head reads must be named in
  ``evidence_refs`` (the old head received the subjects of its scope by itself).

Not carried (the system's, or a check of a commission, which fails where the commission is read, rule 1): the
authentication of ``revision_origin`` against the parent's preparation (``_validate_origin``), the library-id match
and the retrieval of the tool info against the run's tool catalog, the scope containment of the references
(``reference_in_scope``), the inherited-proposed-annotation fill-in (``proposed_annotation_for``) and the filled
request identity digests (``validate_context``, ``validate_execution_context``)."""
from method_loop import DeclaredField, Field, RecordForm

AXIS = 'A105'
TASK_VERSION = 'evidence_axis_task_v1'
OPTION_REF_VERSION = 'experimental_activity_evidence_option_ref_v1'
REVISION_ORIGIN_VERSION = 'experimental_activity_evidence_revision_origin_v1'

OPTION_REF_FORM = RecordForm({
    'version': DeclaredField('text', 'The option reference version', OPTION_REF_VERSION),
    'library_id': Field('text', 'The digest of the frozen library the option is in'),
    'slot': Field('text', 'The library slot of the option (evidence_axis or thought_pattern)'),
    'option_id': Field('text', 'The option id (A105 for the evidence axis, P<n> for a thought pattern)'),
    'entry_sha256': Field('text', 'The digest of the option entry'),
})
TOOL_SELECTOR_FORM = RecordForm({
    'name': Field('text', 'The name of a tool of this head, as the tool library names it (for example source.read)'),
    'resources': Field('text', 'The resource kind of the tool: api, local or hpc'),
})
SELECTION_FORM = RecordForm({
    'version': Field('text', 'The selection version'),
    'evidence_axis': Field('record', 'The evidence axis option (A105)', form=OPTION_REF_FORM),
    'thought_pattern': Field('record', 'The thought pattern option', form=OPTION_REF_FORM),
    'child_tool_info': Field('list', 'The tools of this head the commissioner selected', items=TOOL_SELECTOR_FORM),
})
EVIDENCE_TASK_FORM = RecordForm({
    'version': DeclaredField('text', 'The evidence task version', TASK_VERSION),
    'kind': DeclaredField('text', 'The task kind', 'whole_axis_findings'),
    'evidence_axis': DeclaredField('text', 'The evidence axis the findings are of', AXIS),
    'credit_unit': Field('number', 'The credit of one distinct retained finding: the finding unit of the configured '
                         'credit definition for this exact task'),
})
CONTEXT_FORM = RecordForm({
    'evidence_task': Field('record', 'The whole-axis finding task of this commission', form=EVIDENCE_TASK_FORM),
})
REVISION_ORIGIN_FORM = RecordForm({
    'version': DeclaredField('text', 'The revision origin version', REVISION_ORIGIN_VERSION),
    'parent_invocation_ref': Field('text', 'The invocation that prepared the revised selection'),
    'preparation_operation_ref': Field('text', 'The process.revise operation that prepared it'),
})

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The evidence axis, thought pattern and tools this head investigates with',
                       form=SELECTION_FORM),
    'proposed_annotation_ref': Field('text', 'The proposed annotation this task evaluates, when there is one',
                                     required=False),
    'evidence_refs': Field('record_refs', 'The records the commissioner gives, passed in custody: the records of the '
                           'scope\'s subjects, the proposed annotation and the evidence'),
    'constraints': Field('record', 'The commissioner\'s constraints'),
    'context': Field('record', 'The commissioner\'s context: the whole-axis finding task and its credit unit',
                     form=CONTEXT_FORM),
    'revision_origin': Field('record', 'The process.revise preparation this selection came from, when it is a '
                             'revised selection', required=False, form=REVISION_ORIGIN_FORM),
    'sheet_state_refs': Field('record_refs', 'The persisted subscoring-sheet states the commissioner holds before this '
                              'run (the whole sheet), passed on to the children; absent for the first run of a sheet',
                              required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
})


def read_from_parent(assignment, message):
    """The parent input: the selection, the proposed annotation, the records given, the constraints, the finding
    task and its unit, the revision origin, the scope and the commissioner's message."""
    if assignment['selection']['evidence_axis']['option_id'] != AXIS:
        raise ValueError('a105_selection_requires_the_A105_evidence_axis')
    unit = assignment['context']['evidence_task']['credit_unit']
    if unit <= 0:
        raise ValueError('explicit_positive_finding_unit_required')
    return {'selection': assignment['selection'],
            'proposed_annotation_ref': assignment.get('proposed_annotation_ref'),
            'evidence_refs': assignment['evidence_refs'], 'constraints': assignment['constraints'],
            'evidence_task': assignment['context']['evidence_task'],
            'revision_origin': assignment.get('revision_origin'), 'scope': assignment['scope'],
            'sheet_state_refs': list(assignment['sheet_state_refs']) if 'sheet_state_refs' in assignment else [],
            'message': message}
