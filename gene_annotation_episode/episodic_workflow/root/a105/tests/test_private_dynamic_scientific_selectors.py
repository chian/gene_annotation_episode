"""Dynamic A105 selectors retain actual repository and schema identities."""
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_numerical_contracts
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_task_selection
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import LiteratureAssayGradingRepository, assay_grading_cells_schema
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import LiteratureA105AggregationRepository, aggregation_cells_schema

def test_dynamic_return_schemas_match_selected_scientific_contracts():
    assert literature_numerical_contracts.registered_schema('literature_assay_grading_cells') == assay_grading_cells_schema()
    assert literature_numerical_contracts.registered_schema('literature_a105_aggregation_cells') == aggregation_cells_schema()

def test_dynamic_population_metadata_resolves_original_storage():
    rows = {row[0]: row[2] for row in literature_task_selection.population_task_metadata_specs()}
    assert rows['literature_assay_grading_cells'] == LiteratureAssayGradingRepository.operations_table
    assert rows['literature_a105_aggregation_cells'] == LiteratureA105AggregationRepository.operations_table
