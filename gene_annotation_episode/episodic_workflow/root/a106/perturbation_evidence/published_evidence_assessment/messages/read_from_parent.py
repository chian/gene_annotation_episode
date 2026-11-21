"""What the parent gives: the literature assignment ``literature_assignment_v1`` (the records that give the assigned
question its context), the one commissioned literature task (``verified_source_leads``), the proposed annotation, the
Store scope of the commission and the records passed in custody. This is the only place the assignment is read.

``version``, ``question_context_refs``, ``literature_task`` and ``proposed_annotation_ref`` are the old assignment's
properties under their names (old ``from_parent.py`` ``assignment_schema`` for the role ``literature``). The old
``source_refs`` (sources assigned for reading) are not part of it: a paper reaches the chain only through a search, so
no source is handed down. ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from
its request and the records it received from its binding context; the new commission names both. The old
rate-population properties are not part of this assignment; a commission that sends one is refused by this form. Any
other task kind is a wrong commission and fails here."""
import math

from method_loop import DeclaredField, Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The literature assignment version', 'literature_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads), '
                             'evidence_axis and credit_unit'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The question context and the proposed annotation, passed in '
                                  'custody (new field: old binding-context received records)'),
})


def task_key(task):
    """The old ``_task_key``: ``<axis>:<kind>``."""
    return task['evidence_axis'] + ':' + task['kind']


def read_from_parent(assignment, message):
    """The parent input: the literature assignment, the task, the proposed annotation, the scope and the passed
    records, the task checked (the old ``commissioned_task`` check that needs no Store: a finite credit unit)."""
    literature = {name: assignment[name] for name in ('version', 'question_context_refs')}
    task = assignment['literature_task']
    if task.get('kind') != 'verified_source_leads' or task.get('evidence_axis') != 'A106':
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    return {'literature': literature, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
