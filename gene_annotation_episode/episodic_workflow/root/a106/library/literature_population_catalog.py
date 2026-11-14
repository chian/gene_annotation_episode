"""A106 perturbation and intervention population operations."""


def perturbation_entry():
    from gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_storage import perturbation_population_schema

    return {'name': 'literature.perturbation.populate',
        'description': 'Populate reference perturbation/restoration components from source-bound design interpretations and optional received quantitative data. Keep actual recipient, changed component, partner, endpoint calibration and real restoration arms distinct. Qualitative-only outcomes cannot supply numerical rates. Preserve nuisance comparability separately from effect isolation and leave missing inputs/uncertainty unknown. No target transfer, necessity inference from an unmeasured catalytic knockout, or final annotation credit.',
        'input_schema': perturbation_population_schema()}


def intervention_entries():
    from gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_inputs import intervention_population_schema
    from gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_storage import OPERATION_DESCRIPTION as intervention_description
    from gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore import population_schema as subscore_schema, TASK

    return [
        {'name': 'literature.intervention_grading.populate',
         'description': intervention_description,
         'input_schema': intervention_population_schema()},
        {'name': 'literature.a106.finalize', 'description': TASK,
         'input_schema': subscore_schema()},
    ]
