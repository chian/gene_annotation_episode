"""What the parent gives: the search assignment ``search_assignment_v1`` (the records that give the assigned question its
context and ONE query: ``search_query_ref``, a record of the strategy that holds the provider search request, read
through custody), the commissioned literature task (the one kind, ``verified_source_leads``), the proposed annotation,
the persisted sheet states, the articles already examined, the Store scope of the commission and the records passed in
custody. This is the only place the assignment is read.

``scope`` and ``received_record_refs`` are new fields of the paradigm: the old episode took the scope from its request
and the records it received from its binding context; the new commission names both. Not carried (a wrong commission
fails, rule 1): every other task kind, the requested components of the cell families, named sources, and the reference
checks against the Store."""
import json
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    ContractError, obj, validate_schema)

VERSION = 'literature_local_task_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The search assignment version', 'search_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'search_query_ref': Field('text', 'The query to run: the record of the strategy that holds one provider search '
                              'request, whose results are to be assessed for their relevance to the assigned '
                              'question'),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads), '
                             'evidence_axis A105 and credit_unit'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'sheet_state_refs': Field('record_refs', 'The persisted subscoring-sheet states the commissioner holds before this '
                              'run (the whole sheet), passed on to its first page; absent for the first run of a '
                              'sheet', required=False),
    'examined_article_refs': Field('record_refs', 'The article sources a page of an earlier run of this literature '
                                   'search already examined: their hits are not offered again; absent when none was',
                                   required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The query and its artifact, the proposed annotation and the records '
                                  'of the commissioned task, and every record the commissions to the child will name, '
                                  'passed in custody (new field: old binding-context received records)'),
})


def task_schema():
    """The commissioned task and its explicit local credit unit: the one kind, ``verified_source_leads``."""
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
                          'cutoff': {'type': 'number', 'minimum': 0},
                          'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    properties = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A105'},
                  'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings,
                  'kind': {'const': 'verified_source_leads'}}
    return obj(properties, required=[key for key in properties if key != 'yield_settings'])


def task_key(task):
    """``<axis>:<name>`` where the name is the kind."""
    return task['evidence_axis'] + ':' + task['kind']


def read_from_parent(assignment, message):
    """The parent input: the search assignment, the task, the proposed annotation, the scope and the passed records."""
    task = json.loads(json.dumps(assignment['literature_task']))
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    search = {name: assignment[name] for name in ('version', 'question_context_refs', 'search_query_ref')}
    return {'search': search, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'examined_article_refs': list(assignment['examined_article_refs'])
            if 'examined_article_refs' in assignment else [],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'sheet_state_refs': list(assignment['sheet_state_refs']) if 'sheet_state_refs' in assignment else [],
            'message': message}
