"""What the parent (the search) gives: the page assignment ``page_assignment`` (the ONE paper the search's picked hit
named, in one of its representations, with its artifact), the commissioned literature task (``verified_source_leads``,
the only task), the proposed annotation, the Store scope of the commission and the records passed in custody. This is
the only place the assignment is read.

The page fields (``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs``,
``prior_delivery_refs``) are the old ``_PAGE`` schema. ``scope`` and ``received_record_refs`` are fields of the new
runner: the commission names both. Any other task kind is a wrong commission and fails (no other task exists)."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment'),
    'source_ref': Field('text', 'The one paper to examine'),
    'representation': ChoiceField('text', 'The representation of the paper that is examined', REPRESENTATIONS),
    'artifact_ref': Field('text', "The paper's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier examinations of this paper'),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads), '
                             'evidence_axis A106 and credit_unit'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission'),
    'received_record_refs': Field('record_refs', 'The paper, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody'),
})


def task_key(task):
    return task['evidence_axis'] + ':' + task['kind']


def read_from_parent(assignment, message):
    """The parent input: the page, the task, the proposed annotation, the scope and the passed records."""
    page = {name: assignment[name] for name in ('version', 'source_ref', 'representation', 'artifact_ref',
                                                'question_context_refs', 'prior_delivery_refs')}
    task = assignment['literature_task']
    if task.get('kind') != 'verified_source_leads' or task.get('evidence_axis') != 'A106':
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    return {'page': page, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
