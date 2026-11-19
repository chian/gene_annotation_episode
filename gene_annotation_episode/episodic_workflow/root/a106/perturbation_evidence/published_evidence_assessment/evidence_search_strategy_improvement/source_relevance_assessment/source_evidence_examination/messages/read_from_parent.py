"""What the parent gives: the page assignment ``page_assignment_v1`` (the one source to examine and the artifact of
the representation to read), the commissioned literature task, the proposed annotation, the Store scope of the
commission and the records passed in custody. This is the only place the assignment is read.

``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs``,
``prior_delivery_refs``, ``literature_task`` and ``proposed_annotation_ref`` are the old assignment's properties
under their names (old ``from_parent.py`` ``assignment_schema``: the page schema ``_PAGE`` plus the two task
properties; the assignment is the page itself). ``scope`` and ``received_record_refs`` are new fields: the old
episode took the scope from its request and the records it received from its binding context; the new commission
names both. The old rate-population properties (``requested_*_components``, ``requested_*_views``,
``requested_*_component_keys``) are not part of this assignment: the saved sheets are read whole by the population route
(``literature_population_route``) and the finding is read from them by code; a commission that sends one is
refused by this form."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source to examine'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads, '
                             'or source_answer), evidence_axis, credit_unit and, '
                             'for a source answer, answer_kind with its source_refs (assessment) or examined spans '
                             '(screening)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody (new field: old binding-context '
                                  'received records)'),
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
    """The parent input: the page, the task, the proposed annotation, the scope and the passed records, the task
    checked against the page (the old ``commissioned_task`` checks that need no Store: a finite credit unit, spans
    that run forward, a task confined to the assigned source and artifact)."""
    page = {name: assignment[name] for name in ('version', 'source_ref', 'representation', 'artifact_ref',
                                                'question_context_refs', 'prior_delivery_refs')}
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
    selected = task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
    if any(reference != page['source_ref'] for reference in selected):
        raise ValueError('literature_task_outside_assigned_source')
    if task.get('answer_kind') == 'screening' and any(span['artifact_ref'] != page['artifact_ref']
                                                      for span in task['examined']):
        raise ValueError('literature_task_screening_artifact_mismatch')
    return {'page': page, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
