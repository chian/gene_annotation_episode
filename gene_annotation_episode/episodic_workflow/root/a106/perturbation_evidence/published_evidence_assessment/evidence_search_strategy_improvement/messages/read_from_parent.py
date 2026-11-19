"""What the parent gives: the strategy assignment ``strategy_assignment_v1`` (the records that give the assigned
question its context and the earlier searches' results), the commissioned literature task, the proposed annotation,
the Store scope of the commission and the records passed in custody. This is the only place the assignment is read.

``version``, ``question_context_refs``, ``prior_search_refs``, ``literature_task`` and ``proposed_annotation_ref``
are the old assignment's properties under their names (old ``from_parent.py`` ``assignment_schema`` for the role
``literature_strategy``: ``strategy_assignment_v1`` with ``question_context_refs`` and ``prior_search_refs``, plus the
two task properties). ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its
request and the records it received from its binding context; the new commission names both. The old
rate-population properties (``requested_*_components``, ``requested_*_views``, ``requested_*_component_keys``)
are not part of this assignment: the saved sheets are read whole by the population route
(``literature_population_route``) and the finding is read from them by code; a commission that sends one is
refused by this form."""
import math

from method_loop import DeclaredField, Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The strategy assignment version', 'strategy_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_search_refs': Field('record_refs', 'The records of earlier searches whose approach is to be improved'),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads, '
                             'or source_answer), evidence_axis, credit_unit and, '
                             'for a source answer, answer_kind with its source_refs (assessment) or examined spans '
                             '(screening)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The earlier search records, the question context and the proposed '
                                  'annotation, passed in custody (new field: old binding-context received '
                                  'records)'),
})

TASK_KINDS = ('verified_source_leads', 'source_answer')
ANSWER_KINDS = ('assessment', 'screening')


def task_key(task):
    """The old ``_task_key``: ``<axis>:<name>`` where the name is the kind and, for a source answer,
    ``:<answer_kind>`` follows."""
    name = task['kind']
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def read_from_parent(assignment, message):
    """The parent input: the strategy assignment, the task, the proposed annotation, the scope and the passed
    records, the task checked (the old ``commissioned_task`` checks that need no Store: a finite credit unit and
    spans that run forward; this role has no assigned page, so the old page-confinement checks do not apply)."""
    strategy = {name: assignment[name] for name in ('version', 'question_context_refs', 'prior_search_refs')}
    task = assignment['literature_task']
    if task.get('kind') not in TASK_KINDS or (task['kind'] == 'source_answer'
                                              and task.get('answer_kind') not in ANSWER_KINDS):
        raise ValueError('literature_original_task_invalid')
    if task.get('evidence_axis') != 'A106':
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ValueError('literature_task_screening_span_invalid')
    return {'strategy': strategy, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
