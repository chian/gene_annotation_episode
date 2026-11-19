"""A104-only commissioned result shapes and commission checks."""
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import ContractError, REF, obj

def task_schema_variants(base, task_object, refs):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_quantity_storage import quantity_population_schema
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.evolutionary_history_evidence.literature_assay_grading import ASSAY_TYPES
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
