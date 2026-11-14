"""Private goal for the original literature_ordered commission."""
from __future__ import annotations
import json
import math
import heapq
from gene_annotation_episode.episodic_workflow.root.a105.communication import plain
from gene_annotation_episode.episodic_workflow.root.a105.domain import REF, obj, validate_schema
from gene_annotation_episode.domain import ContractError
import json
from gene_annotation_episode.episodic_workflow.root.a105.domain import REF, obj
from gene_annotation_episode.domain import ContractError
VERSION = 'literature_local_task_v1'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
YIELD_TASKS = frozenset((f'A105:{task}' for task in ('verified_source_leads', 'source_answer:assessment', 'source_answer:screening'))) | frozenset(('A105:source_answer:measurement', 'A105:experiments', 'A105:assembly'))

def _yield_kind(task):
    return 'accumulation' if task['kind'] == 'verified_source_leads' else 'remaining_commissioned_credit'

def _task_key(task):
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name

def task_schema():
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']}, 'cutoff': {'type': 'number', 'minimum': 0, 'description': 'This commissioned episode stops when its available next-credit upper estimate is at or below this cutoff, measured in this task credit unit.'}, 'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A105'}, 'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        return obj(properties, required=[key for key in properties if key != 'yield_settings'])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})
    return {'description': 'The original commissioned result and its explicit local credit unit. Select only a task whose typed result is requested by the original return contract. A105 grading is a separate automatic operation, not earned by selecting a tool.', 'anyOf': [task_object({**base, 'kind': {'const': 'verified_source_leads'}}), task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'}, 'source_refs': refs}), task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'}, 'examined': {'type': 'array', 'minItems': 1, 'items': span}}), *task_schema_variants(base, task_object, refs)]}

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
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement import goal as a105_credit
    required = LEADS if kind == 'verified_source_leads' else 'changed_assessment_refs' if answer == 'assessment' else SCREENING if answer == 'screening' else a105_credit.required_source(task)
    if required is not None and required not in sources:
        raise ContractError('literature_task_typed_return_mismatch')
    selected = task.get('metrics', task.get('components'))
    if selected is not None and (not any((set(selected) <= values for values in _return_components(schema, required)))):
        raise ContractError('literature_task_return_components_mismatch')
    a105_credit.validate_commission(task, assignment)
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    assigned_page = assignment.get('page', assignment if context.role == 'literature_page' else None)
    selected_sources = task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])] + ([task['selection']['source_ref']] if answer == 'measurement' else [])
    if assigned_page is not None and any((ref != assigned_page['source_ref'] for ref in selected_sources)):
        raise ContractError('literature_task_outside_assigned_source')
    if assigned_page is not None and answer == 'screening' and any((span['artifact_ref'] != assigned_page['artifact_ref'] for span in task['examined'])):
        raise ContractError('literature_task_screening_artifact_mismatch')
    return (task, proposed)

def continuation_task(context):
    task, _ = commissioned_task(context)
    return _task_key(task)

def task_schema_variants(base, task_object, refs):
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_quantity_storage import quantity_population_schema
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading import ASSAY_TYPES
    return [task_object({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'measurement'}, 'selection': quantity_population_schema(), 'components': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'enum': ['reported_value', 'reported_spread', 'relative_reported_spread']}}}), task_object({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'a105_experiments'}, 'experiments': {'type': 'array', 'minItems': 1, 'items': obj({'experiment_ref': REF, 'assay_type': {'enum': list(ASSAY_TYPES)}})}}), task_object({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'a105_assembly'}, 'experiment_refs': refs, 'metrics': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'enum': ['reliability', 'validity', 'relevance', 'attribution', 'overall']}}})]

def required_source(task):
    if task.get('answer_kind') == 'measurement':
        return 'literature_quantity_cells'
    if task['kind'] == 'a105_experiments':
        return 'literature_assay_grading_cells'
    if task['kind'] == 'a105_assembly':
        return 'literature_a105_aggregation_cells'
    return None

def validate_commission(task, assignment):
    if task['kind'] == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if len(set(experiments)) != len(experiments):
            raise ContractError('literature_task_duplicate_experiment')
    if task['kind'] == 'a105_assembly' and (not set(task['metrics']) <= set(assignment.get('requested_a105_aggregation_components', ()))):
        raise ContractError('literature_task_requested_metrics_mismatch')
    if task.get('answer_kind') == 'measurement' and (not set(task['components']) <= set(assignment.get('requested_quantity_components', ()))):
        raise ContractError('literature_task_requested_measurement_mismatch')
'Private goal responsibility for literature_ordered.'
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.source_contracts import _ROLE_INSTRUCTIONS

class LiteratureGoal:

    def instructions(self, context):
        self._role(context.role)
        return _ROLE_INSTRUCTIONS['literature_ordered'] + "\nThis is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted child forms inform later choices; no child order, reading quota or complete-document requirement is prescribed. A one-off search/read is an ordinary tool. A supplied reading selector is context, not an automatically executed action. Preserve the source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors. Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications can advance the investigation. Commit interpretations with the common reasoning action and update only the parent's declared typed form in that same work call. Navigation, byte coverage and repeated reading earn no scientific credit by themselves. The commissioned task's own yield settings guide continuation."

    def planning_context(self, context):
        task, annotation = commissioned_task(context)
        request = plain(context.request)
        return {'objective': request['goal'], 'proposed_annotation_ref': annotation, 'commissioned_result': task, 'progress_definition': self.credit_projector(context).as_record(), 'planning_question': self.instructions(context)}
