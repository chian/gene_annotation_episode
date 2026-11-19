"""A104-only commissioned result shapes and earned-answer checks."""
import json
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

def measured_answers(binding, store, context, task, known):
    repository = binding.literature_quantity_repository()
    for ref in known:
        source = store.get(ref)
        if source.get('provider') != repository.provider:
            continue
        request = json.loads(store.get_artifact(source['request_ref']))
        if request.get('arguments') != task['selection']:
            continue
        repository.read(ref)
        rows = repository.fact_cells(context, [ref], components=task['components'])
        if {row['component'] for row in rows} != set(task['components']):
            continue
        if all((row['status'] == 'populated' or row.get('unavailable_reason') in {'reported_spread_unavailable', 'zero_reported_value'} for row in rows)):
            return [{'sheet_ref': ref, 'source_ref': task['selection']['source_ref'], 'components': task['components']}]
    return []

def graded_experiment_answers(store, context, task, proposed, known, current_assessments):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_sheet_updates import current_sheet_refs
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_assay_grading_storage import LiteratureAssayGradingRepository
    from gene_annotation_episode.episodic_workflow.episode_support.forms.required_evidence_contracts import _matches_grading
    repository = LiteratureAssayGradingRepository(store, context.run_id)
    assessments = list(current_assessments(store, context, proposed, known))
    wanted = {item['experiment_ref']: item['assay_type'] for item in task['experiments']}
    completed = {}
    for ref in current_sheet_refs(store, context, repository.provider):
        if ref not in known:
            continue
        saved = repository.read(ref)
        args = saved['selection']
        experiment = args.get('experiment_ref')
        if args['assertion_ref'] != proposed or wanted.get(experiment) != args['assay_type']:
            continue
        if not repository.fact_cells(context, [ref], components=repository.components):
            continue
        for assessment in assessments:
            if _matches_grading(store, assessment['id'], args, contextual=False):
                completed[experiment] = {'experiment_ref': experiment, 'assessment_ref': assessment['id'], 'sheet_ref': ref}
    return list(completed.values())

def assembled_answers(store, context, task, proposed, known):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_sheet_updates import current_sheet_refs
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_aggregation_storage import LiteratureA105AggregationRepository
    repository = LiteratureA105AggregationRepository(store, context.run_id)
    current_grades = set(current_sheet_refs(store, context, 'literature.a105.assay_grading'))
    for ref in current_sheet_refs(store, context, repository.provider):
        if ref not in known:
            continue
        saved = repository.read(ref)
        args = saved['selection']
        if args['assertion_ref'] != proposed or set(task['experiment_refs']) != {item['experiment_ref'] for item in args['experiments']}:
            continue
        selected = [experiment['metrics'][metric] for experiment in args['experiments'] for metric in task['metrics']]
        if any((item is None or item['sheet_ref'] not in current_grades for item in selected)):
            continue
        cells = repository.fact_cells(context, [ref], components=task['metrics'])
        if {row['component'] for row in cells} == set(task['metrics']):
            return [{'sheet_ref': ref, 'experiment_refs': task['experiment_refs'], 'metrics': task['metrics']}]
    return []
