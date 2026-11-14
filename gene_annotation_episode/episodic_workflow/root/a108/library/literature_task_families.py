"""Task-family instructions and metadata owned by A108."""
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_prompt import A108_CONTEXT_TASK, A108_GRADING_TASK, A108_AGGREGATION_TASK
_ROWS = {'literature_a108_grading_cells': ('literature_a108_grading_cells', A108_GRADING_TASK, 'library.literature_a108_grading_storage', 'LiteratureA108GradingRepository', 'requested_a108_grading_components', 'literature.a108_grading.populate'), 'literature_a108_aggregation_cells': ('literature_a108_aggregation_cells', A108_AGGREGATION_TASK, 'library.literature_a108_aggregation_storage', 'LiteratureA108AggregationRepository', 'requested_a108_aggregation_components', 'literature.a108.aggregate')}

def family_row(source):
    return _ROWS[source]

def population_task_metadata_specs():
    """A108's own saved population identities for prompt selection."""
    from importlib import import_module
    for source, _, module_name, class_name, _, _ in _ROWS.values():
        module = import_module('.' + module_name, 'gene_annotation_episode.episodic_workflow.root.a108')
        repository = getattr(module, class_name)
        yield (source, repository.operations_table, module.PROVIDER, (getattr(module, 'VERSION', repository.record_version),))
