"""Original commissioned-task admission and typed continuation identity."""
import math
from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.library.literature_task_schema import task_schema
from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import LEADS, SCREENING

def _task_key(task):
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


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
    assignment, request = plain(context.assignment), plain(context.request)
    task = assignment.get('literature_task')
    if task is None:
        raise ContractError('literature_original_task_credit_required')
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    proposed = assignment.get('proposed_annotation_ref')
    if not isinstance(proposed, str):
        raise ContractError('literature_original_proposed_annotation_required')
    if (not request.get('goal') or not request.get('report_contract')
            or request.get('message', {}).get('episode_assignment') != assignment):
        raise ContractError('literature_task_original_commission_mismatch')
    schema = request['report_contract']['measurements']['schema']
    sources = set(_return_sources(schema))
    kind, answer = task['kind'], task.get('answer_kind')
    required = (LEADS if kind == 'verified_source_leads' else 'changed_assessment_refs' if answer == 'assessment' else
        SCREENING if answer == 'screening' else 'literature_quantity_cells' if answer == 'measurement' else
        'literature_assay_grading_cells' if kind == 'a105_experiments' else
        'literature_a105_aggregation_cells' if kind == 'a105_assembly' else None)
    if required is not None and required not in sources:
        raise ContractError('literature_task_typed_return_mismatch')
    selected = task.get('metrics', task.get('components'))
    if selected is not None and not any(set(selected) <= values
            for values in _return_components(schema, required)):
        raise ContractError('literature_task_return_components_mismatch')
    if kind == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if len(set(experiments)) != len(experiments):
            raise ContractError('literature_task_duplicate_experiment')
    if kind == 'a105_assembly' and not set(task['metrics']) <= set(
            assignment.get('requested_a105_aggregation_components', ())):
        raise ContractError('literature_task_requested_metrics_mismatch')
    if answer == 'measurement' and not set(task['components']) <= set(
            assignment.get('requested_quantity_components', ())):
        raise ContractError('literature_task_requested_measurement_mismatch')
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    assigned_page = assignment.get('page', assignment if context.role == 'literature_page' else None)
    selected_sources = (task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
        + ([task['selection']['source_ref']] if answer == 'measurement' else []))
    if assigned_page is not None and any(ref != assigned_page['source_ref'] for ref in selected_sources):
        raise ContractError('literature_task_outside_assigned_source')
    if assigned_page is not None and answer == 'screening' and any(
            span['artifact_ref'] != assigned_page['artifact_ref'] for span in task['examined']):
        raise ContractError('literature_task_screening_artifact_mismatch')
    return task, proposed


def continuation_task(context):
    task, _ = commissioned_task(context)
    return _task_key(task)

