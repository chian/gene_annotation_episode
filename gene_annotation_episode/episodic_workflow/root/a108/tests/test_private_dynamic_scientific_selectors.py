"""Dynamic A108 selectors resolve the same actual repositories and schemas."""
from gene_annotation_episode.episodic_workflow.root.a108.library import literature_numerical_contracts
from gene_annotation_episode.episodic_workflow.root.a108.library import literature_task_families
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_storage import LiteratureA108GradingRepository, grading_cells_schema
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import LiteratureA108AggregationRepository, aggregation_cells_schema

def test_dynamic_return_schemas_are_the_current_scientific_contracts():
    assert literature_numerical_contracts.registered_schema('literature_a108_grading_cells') == grading_cells_schema()
    assert literature_numerical_contracts.registered_schema('literature_a108_aggregation_cells') == aggregation_cells_schema()

def test_dynamic_population_metadata_uses_actual_original_storage():
    rows = list(literature_task_families.population_task_metadata_specs())
    assert [(row[0], row[1]) for row in rows] == [('literature_a108_grading_cells', LiteratureA108GradingRepository.operations_table), ('literature_a108_aggregation_cells', LiteratureA108AggregationRepository.operations_table)]
