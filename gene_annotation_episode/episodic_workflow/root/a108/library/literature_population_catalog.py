"""A108 operations for contextual-observation evidence."""

def population_catalog():
    from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_inputs import grading_population_schema
    from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_storage import OPERATION_DESCRIPTION as grading_description
    from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import aggregation_population_schema
    from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import OPERATION_DESCRIPTION as aggregation_description
    return [{'name': 'literature.a108_grading.populate', 'description': grading_description, 'input_schema': grading_population_schema()}, {'name': 'literature.a108.aggregate', 'description': aggregation_description, 'input_schema': aggregation_population_schema()}]
