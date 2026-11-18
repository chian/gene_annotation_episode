"""Private A108 goal for the original literature_table commission."""
from __future__ import annotations
from dataclasses import dataclass, replace
import json
import math
import heapq
from gene_annotation_episode.episodic_workflow.root.a108.communication import plain
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError, REF, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a108.numerical import NumericBand, STATUS_NORMAL, YieldController, YieldEstimate, YieldParameters, estimate_score_yield
VERSION = 'literature_local_task_v1'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
YIELD_TASKS = frozenset(('A108:' + task for task in ('verified_source_leads', 'source_answer:assessment', 'source_answer:screening')))

def _yield_kind(task):
    return 'accumulation' if task['kind'] == 'verified_source_leads' else 'remaining_commissioned_credit'

def _task_key(task):
    name = task['kind']
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name

def task_schema():
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']}, 'cutoff': {'type': 'number', 'minimum': 0, 'description': 'This commissioned episode stops when its available next-credit upper estimate is at or below this cutoff, measured in this task credit unit.'}, 'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A108'}, 'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        return obj(properties, required=[key for key in properties if key != 'yield_settings'])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})
    return {'description': 'The original commissioned A108 result and its explicit local credit unit. Select only a task whose typed result is requested by the original return contract. A108 score computation is automatic work, not an episode-credit task.', 'anyOf': [task_object({**base, 'kind': {'const': 'verified_source_leads'}}), task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'}, 'source_refs': refs}), task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'}, 'examined': {'type': 'array', 'minItems': 1, 'items': span}})]}

def _return_sources(schema):
    if isinstance(schema, dict):
        if isinstance(schema.get('x-source'), str):
            yield schema['x-source']
        for value in schema.values():
            yield from _return_sources(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _return_sources(value)

def _return_components(schema, namespace):
    if isinstance(schema, dict):
        if schema.get('x-source') == namespace:
            component = schema.get('items', {}).get('properties', {}).get('component', {})
            yield set(component.get('enum', [component['const']] if 'const' in component else []))
        for value in schema.values():
            yield from _return_components(value, namespace)
    elif isinstance(schema, list):
        for value in schema:
            yield from _return_components(value, namespace)

def commissioned_task(context):
    assignment, request = (plain(context.assignment), plain(context.request))
    task = assignment.get('literature_task')
    if task is None:
        raise ContractError('literature_original_task_credit_required')
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    proposed = assignment.get('proposed_annotation_ref')
    if not isinstance(proposed, str):
        raise ContractError('literature_original_proposed_annotation_required')
    if not request.get('goal') or not request.get('report_contract') or request.get('message', {}).get('episode_assignment') != assignment:
        raise ContractError('literature_task_original_commission_mismatch')
    schema = request['report_contract']['measurements']['schema']
    sources = set(_return_sources(schema))
    kind, answer = (task['kind'], task.get('answer_kind'))
    required = LEADS if kind == 'verified_source_leads' else 'changed_assessment_refs' if answer == 'assessment' else SCREENING if answer == 'screening' else None
    if required is not None and required not in sources:
        raise ContractError('literature_task_typed_return_mismatch')
    selected = task.get('metrics', task.get('components'))
    if selected is not None and (not any((set(selected) <= values for values in _return_components(schema, required)))):
        raise ContractError('literature_task_return_components_mismatch')
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    assigned_page = assignment.get('page', None)
    selected_sources = task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
    if assigned_page is not None and any((ref != assigned_page['source_ref'] for ref in selected_sources)):
        raise ContractError('literature_task_outside_assigned_source')
    if assigned_page is not None and answer == 'screening' and any((span['artifact_ref'] != assigned_page['artifact_ref'] for span in task['examined'])):
        raise ContractError('literature_task_screening_artifact_mismatch')
    return (task, proposed)

def continuation_task(context):
    task, _ = commissioned_task(context)
    return _task_key(task)
'goal for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.source_contracts import _ROLE_INSTRUCTIONS

class LiteratureGoal:

    def instructions(self, context):
        self._role(context.role)
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_prompt import A108_CONTEXT_TASK, A108_READING_TASK
        return '\n\n'.join((_ROLE_INSTRUCTIONS['literature_table'], A108_CONTEXT_TASK, A108_READING_TASK))

    def planning_context(self, context):
        task, annotation = commissioned_task(context)
        request = plain(context.request)
        return {'objective': request['goal'], 'proposed_annotation_ref': annotation, 'commissioned_result': task, 'progress_definition': self.credit_projector(context).as_record(), 'planning_question': self.instructions(context)}
