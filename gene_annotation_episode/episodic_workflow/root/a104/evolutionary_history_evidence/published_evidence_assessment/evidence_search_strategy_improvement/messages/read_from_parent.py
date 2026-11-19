"""What the parent gives: the strategy assignment ``strategy_assignment_v1`` (the records that give the question its
context and the prior searches), the commissioned literature task, the proposed annotation, the Store scope of the
commission and the records passed in custody. This is the only place the assignment is read.

``version``, ``question_context_refs`` and ``prior_search_refs`` are the properties of the old strategy assignment
(old ``from_parent.py``), and ``literature_task`` and ``proposed_annotation_ref`` are the properties of the old
``assignment_fields.py``, under their names. ``scope`` and ``received_record_refs`` are new fields: the old episode
took the scope from its request and the records it had received from its binding context; the new commission names
both. The old rate-population properties (``requested_*_components``, ``requested_*_views``,
``requested_*_component_keys``) belong to the population route, which is not built: a commission that sends one is
refused by this form. The old checks that needed the Store (each prior search is a ``source`` in scope, every
reference in scope) and the old injection of the configured yield binding declaration into the task are not carried:
they were this episode's checks of its own commission, and a wrong commission fails."""
import math

from method_loop import DeclaredField, Field, RecordForm

STRATEGY_FIELDS = ('version', 'question_context_refs', 'prior_search_refs')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The strategy assignment version', 'strategy_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_search_refs': Field('record_refs', 'The prior searches, each a source record'),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads, '
                             'source_answer, a105_experiments or a105_assembly), evidence_axis, credit_unit and, '
                             'for a source answer, answer_kind with its source_refs (assessment), examined spans '
                             '(screening) or selection and components (measurement)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The prior-search sources, their artifacts and the sources they '
                                  'derive from, and the proposed annotation, passed in custody (new field: the old '
                                  'binding-context received records)'),
})

TASK_KINDS = ('verified_source_leads', 'source_answer', 'a105_experiments', 'a105_assembly')
ANSWER_KINDS = ('assessment', 'screening', 'measurement')


def task_key(task):
    """The old ``_task_key``: ``<axis>:<name>`` where the name is the kind (``a105_experiments`` is
    ``experiments``, ``a105_assembly`` is ``assembly``) and, for a source answer, ``:<answer_kind>`` follows."""
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def read_from_parent(assignment, message):
    """The parent input: the strategy assignment (the old assignment, flat), the task, the proposed annotation, the
    scope and the passed records, with the task checked (the old assignment validation that needs no Store)."""
    task = assignment['literature_task']
    if task.get('kind') not in TASK_KINDS or (task['kind'] == 'source_answer'
                                              and task.get('answer_kind') not in ANSWER_KINDS):
        raise ValueError('literature_original_task_invalid')
    if not isinstance(task.get('evidence_axis'), str) or not task['evidence_axis']:
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    if task['kind'] == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if not experiments or len(set(experiments)) != len(experiments):
            raise ValueError('literature_task_duplicate_experiment')
    return {'strategy': {name: assignment[name] for name in STRATEGY_FIELDS}, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
