"""Source-backed operands and experimental design for the A106 assessment."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a105.domain import REF, obj
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_inputs import _witness_schema
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_inputs import assay_grading_population_schema
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.literature_intervention_grading import ROLES, REQUIRED_ROLES, intervention_grading_input_schema
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_perturbation_assessments import assessment_schema
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_perturbation_operands import NAMESPACE as PERTURBATION_NAMESPACE
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.literature_intervention_table import table_number_schema
DESIGN_FIELDS = ('molecule', 'strain', 'construct', 'intervention', 'reference_condition', 'restoration_arm', 'endpoint', 'measurement_scale', 'sampling_time', 'replication', 'shared_controls', 'reference_version', 'analysis_protocol', 'comparison_direction')
ANALYSIS_METRICS = ('reference_mean', 'intervention_mean', 'log2_fold_change', 'mean_difference', 'base_mean', 'standard_error', 'effect_variance', 'p_value', 'adjusted_p_value')
COMPARISON_NAMESPACE = 'literature_measurement_comparison_cells'

def sample_bindings_schema():
    witness = _witness_schema()
    nullable = {'anyOf': [deepcopy(witness), {'type': 'null'}]}
    return {'type': 'array', 'items': obj({'sample_id': {'type': 'string', 'minLength': 1}, 'identity': deepcopy(witness), 'file_refs': {'type': 'array', 'items': {**REF, 'x-reference-namespace': 'source'}, 'uniqueItems': True}, 'file_correspondence': {'type': 'array', 'items': deepcopy(witness), 'description': 'One source witness per file_refs entry, in the same order, linking that file to this sample.'}, 'arm': {'enum': ['reference', 'intervention', 'restoration', 'other', 'unknown']}, 'arm_definition': deepcopy(nullable), 'biological_unit': deepcopy(nullable), 'technical_unit': deepcopy(nullable), 'pairing': deepcopy(nullable), 'batch': deepcopy(nullable), 'sampling_time': deepcopy(nullable)})}

def intervention_population_schema():
    schema = intervention_grading_input_schema()
    props = schema['properties']
    del props['version']
    existing = assay_grading_population_schema()['properties']
    props.update({name: deepcopy(existing[name]) for name in ('source_ref', 'source_kind', 'experiment_ref')})
    props['experiment_assessment'] = assessment_schema()
    props['comparison_ref'] = {**deepcopy(REF), 'x-reference-namespace': 'hypothesis'}
    witness = _witness_schema()
    props['experimental_design'] = obj({key: {'anyOf': [deepcopy(witness), {'type': 'null'}]} for key in DESIGN_FIELDS})
    props['sample_bindings'] = sample_bindings_schema()
    native = obj({'kind': {'const': 'native_analysis'}, 'source_ref': deepcopy(REF), 'representation': {'enum': ['transit_resampling', 'deseq2']}, 'row_ordinal': {'type': 'integer', 'minimum': 0}, 'feature_id': {'type': 'string', 'minLength': 1}, 'metric': {'enum': list(ANALYSIS_METRICS)}})
    native['description'] = "Preserve the selected native column's meaning: reference_mean, intervention_mean and base_mean supply native_endpoint; mean_difference supplies endpoint_difference; log2_fold_change supplies log2_fold_change. Native effect_variance must accompany that same row's log2_fold_change. A mean is not a contrast, and a logarithmic fold change is not a linear ratio or difference."
    application = deepcopy(native)
    application['properties'].update(kind={'const': 'application_analysis'}, sheet_ref=application['properties'].pop('source_ref'), field={'type': 'string', 'minLength': 1})
    application['required'] = list(application['properties'])
    props['quantities'] = obj({role: {'anyOf': [*deepcopy(existing['quantities']['properties'][role]['anyOf'][:2]), deepcopy(native), deepcopy(application), {'type': 'null'}]} for role in ROLES}, required=list(REQUIRED_ROLES))
    for role in ROLES:
        choices = props['quantities']['properties'][role]['anyOf']
        received = choices[0]
        received['properties']['namespace']['enum'].append(COMPARISON_NAMESPACE)
        received['properties']['namespace']['enum'].append(PERTURBATION_NAMESPACE)
        received['description'] += ' A previously calculated likelihood ratio or signed evidence index is not an effect, prediction, control measurement or uncertainty operand. Select the underlying measurement and its applicable uncertainty instead.'
        received['description'] += ' Published specific-activity tables with shared header units can use literature.measurement_comparison.populate. Its native/converted left or right estimates supply native_endpoint; protocol_difference supplies endpoint_difference; protocol_ratio supplies endpoint_ratio. difference_variance supplies uncertainty only for protocol_difference from the same sheet. Standardized discrepancies, weights and conditional scenarios are not intervention effects.'
        received['description'] += ' literature.perturbation.populate can return literature_perturbation_operand_cells with requested_perturbation_operand_components. Select reference_endpoint/perturbed_endpoint/restored_endpoint as native_endpoint, or perturbation_difference (W-K)/restoration_difference (R-K) as endpoint_difference. Match W/K/R_mean_variance or perturbation/restoration_mean_variance to that exact effect in the same sheet. Restoration indices, covariance enclosures and SD/SEM are not effect variances.'
        choices[1]['description'] += ' number_start and number_end are character offsets within number.witness.quote, starting at zero. The witness start/end fields are absolute UTF-8 byte offsets in the source. Whitespace, including Unicode thin spaces, may separate the number and unit.'
        choices.insert(-1, table_number_schema(choices[1]))
    schema['required'] = [name for name in props if name != 'sample_bindings']
    return schema
