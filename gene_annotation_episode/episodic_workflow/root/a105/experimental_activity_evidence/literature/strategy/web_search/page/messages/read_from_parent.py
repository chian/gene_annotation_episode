"""What the parent (the search) gives: the page assignment ``page_assignment`` (the ONE paper the search's picked hit
named, in one of its representations, with its artifact), the commissioned literature task (``verified_source_leads``,
the only task), the proposed annotation, the references of the articles already examined, the Store scope of the
commission and the records passed in custody. This is the only place the assignment is read.

The page fields (``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs``,
``prior_delivery_refs``) are the old ``_PAGE`` schema of ``source_contracts.py``. ``scope`` and ``received_record_refs``
are fields of the new runner: the commission names both. Any other task kind, and every ``requested_*`` array of a
population family, is a wrong commission and fails (rule 1)."""
import json
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    ContractError, obj, validate_schema)

VERSION = 'literature_local_task'
REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

# The commissioner's objective (``message['objective']``): one value of this fixed vocabulary and nothing else
# (controlled messaging: no text of the commissioner's model reaches this episode's model). The value says where the
# commissioner expects the evidence of the claim in the assigned paper.
OBJECTIVES = {
    'evidence_in_table': 'The evidence of the claim is reported in a table, a sheet or a tabular block '
                         'of numbers of this paper.',
    'evidence_in_passages': 'The evidence of the claim is stated in particular passages of the running '
                            'text of this paper.',
    'evidence_location_unknown': 'Where this paper holds evidence of the claim, or whether it holds '
                                 'any, is not known.',
}

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment'),
    'source_ref': Field('text', 'The one paper to examine'),
    'representation': ChoiceField('text', 'The representation of the paper that is examined', REPRESENTATIONS),
    'artifact_ref': Field('text', "The paper's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier examinations of this paper'),
    'examined_article_refs': Field('record_refs', 'The article sources already examined by earlier pages',
                                   required=False),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads), '
                             'evidence_axis A105 and credit_unit'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'sheet_state_refs': Field('record_refs', 'The persisted subscoring-sheet states the commissioner holds before this '
                              'page (one record per row, the whole sheet), passed in custody; absent for the first '
                              'page of a sheet', required=False),
    'scope': Field('record', 'The Store scope of the commission'),
    'received_record_refs': Field('record_refs', 'The paper, its artifact, the sources it derives from, the '
                                  'proposed annotation and the records of the commissioned task, passed in custody'),
})


def task_schema():
    """The commissioned task and its explicit local credit unit: ``verified_source_leads`` only."""
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
                          'cutoff': {'type': 'number', 'minimum': 0},
                          'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A105'},
            'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings,
            'kind': {'const': 'verified_source_leads'}}
    return obj(base, required=[key for key in base if key != 'yield_settings'])


def task_key(task):
    return task['evidence_axis'] + ':' + task['kind']


def read_from_parent(assignment, message):
    """The parent input: the commissioner's objective (its vocabulary value and this episode's meaning of it; a
    value outside ``OBJECTIVES`` is a wrong commission and fails here), the page, the task, the proposed annotation,
    the scope and the passed records."""
    task = json.loads(json.dumps(assignment['literature_task']))
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    page = {name: assignment[name] for name in ('version', 'source_ref', 'representation', 'artifact_ref',
                                                'question_context_refs', 'prior_delivery_refs')}
    return {'objective': {'value': message['objective'], 'meaning': OBJECTIVES[message['objective']]},
            'page': page, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'examined_article_refs': list(assignment['examined_article_refs'])
            if 'examined_article_refs' in assignment else [],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'sheet_state_refs': list(assignment['sheet_state_refs']) if 'sheet_state_refs' in assignment else []}
