"""Selected native kinetic estimates; exact saved return subsets, no credit.

Only the five native parameter/contrast meanings are exposed by this route.
The source model/covariance reader is unfinished work, not a paper finding.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import obj
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_kinetic_inputs import SUBJECT_FIELDS, CONTEXT_FIELDS, PARAMETER_UNITS, COMPARISON_VALUES, QUALIFICATIONS, COUNT_STATUSES, COUNT_REASONS, COUNT_NOTATIONS, COUNT_RELATIONS
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_kinetic_calculations import COMPONENTS as ALL_COMPONENTS, REASONS, CONDITIONAL_CODES
COMPONENTS = ALL_COMPONENTS[:5]
FORMULA_CODES = {name: 'kinetic_' + name for name in COMPONENTS}
UNIT_CODES = {'uM^-1min^-1': 'uM_inverse_min_inverse'}
EVALUATION_SCOPE = 'source_kinetic_parameter_contrast'
MODEL_INPUT_STATUS = 'not_supplied_by_native_operation'
MODEL_CAPABILITY = 'unimplemented'

def kinetic_cells_schema():

    def enum(values, nullable=False):
        return {'type': ['string', 'null'] if nullable else 'string', 'enum': [*values, None] if nullable else list(values)}

    def ref(namespace='reference', nullable=True):
        return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}
    refs = {'type': 'array', 'uniqueItems': True, 'items': ref(nullable=False)}
    number = {'type': ['number', 'null']}
    uncertain_reasons = ['source_uncertainty_unit_unavailable', 'source_numeric_range']
    input_reasons = ['source_measurement_unreported', 'source_parameter_kind_unknown', 'source_parameter_kind_conflicting', 'source_kinetic_unit_unreported', 'unsupported_source_kinetic_unit', 'source_numeric_range', 'source_operand_qualification_unknown', 'source_operand_qualification_conflicting']
    metadata = obj({'parameter_kind': enum([*PARAMETER_UNITS, 'unknown', 'conflicting']), 'parameter_kind_witness_refs': refs, 'measurement_ref': ref(), 'measurement_source_ref': ref('source'), 'physical_observation_ref': ref(), 'source_unit_ref': ref(), 'canonical_unit': enum([UNIT_CODES.get(u, u) for u in PARAMETER_UNITS.values()], True), 'qualification': enum(QUALIFICATIONS), 'qualification_witness_refs': refs, 'approximate': {'type': ['boolean', 'null']}, 'input_status': enum(['point', 'censored', 'missing', 'conflicting', 'unresolved']), 'observed_relation': enum(['point', 'lt', 'le', 'gt', 'ge'], True), 'source_origin': enum(['reported', 'synthetic'], True), 'converted_origin': enum(['reported', 'calculated', 'synthetic'], True), 'subject': obj({k: ref() for k in SUBJECT_FIELDS}), 'context': obj({k: ref() for k in CONTEXT_FIELDS}), 'numeric_tokens': {'type': 'array', 'items': obj({'ref': ref(nullable=False), 'source_ref': ref('source', False)})}, 'uncertainty': obj({'statistic': enum(['sd', 'sem', 'ci', 'unspecified', 'unreported']), 'count_reading_status': enum(COUNT_STATUSES), 'count_unavailable_reason': enum(COUNT_REASONS, True), 'count_notation': enum(COUNT_NOTATIONS, True), 'count_relation': enum(COUNT_RELATIONS, True), 'count_approximate': {'type': ['boolean', 'null']}, 'unit_ref': ref(), 'canonical_unit': enum([UNIT_CODES.get(u, u) for u in PARAMETER_UNITS.values()], True), 'repetition_basis': enum(['biological_preparations', 'technical_measurements', 'unspecified']), 'estimate_basis': enum(['fit_to_averaged_curve', 'between_fitted_parameters', 'unknown']), **{k + '_ref': ref() for k in ('magnitude', 'interval', 'confidence_level', 'count')}, 'unavailable_reason': enum(uncertain_reasons, True)}), 'uncertainty_values': obj({'delivery_status': enum(['requested', 'not_requested']), 'magnitude': number, 'interval': {'type': ['array', 'null'], 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2}, 'confidence_level': number, 'count': {'type': ['integer', 'null'], 'minimum': 1}, 'count_reported_value': {'type': ['integer', 'null']}}), 'input_unavailable_reasons': {'type': 'array', 'uniqueItems': True, 'items': enum(input_reasons)}})
    return {'type': 'array', 'x-source': 'literature_kinetic_cells', 'items': obj({'sheet_ref': ref('source', False), 'evidence_source_ref': ref('source', False), 'component': enum(COMPONENTS), 'value': number, 'threshold': number, 'unit': enum([*[UNIT_CODES.get(u, u) for u in PARAMETER_UNITS.values()], 'dimensionless'], True), 'status': enum(['populated', 'unavailable']), 'relation': enum(['eq', 'lt', 'le', 'gt', 'ge', 'none']), 'approximate': {'type': 'boolean'}, 'origin': enum(['reported', 'calculated', 'synthetic', 'derived']), 'unavailable_reason': enum(REASONS, True), 'formula_code': enum(FORMULA_CODES.values()), 'conditional_on': {'type': 'array', 'uniqueItems': True, 'items': enum(CONDITIONAL_CODES)}, 'evaluation_scope': enum([EVALUATION_SCOPE]), 'contrast_meaning': enum(['numerator_parameter_exceeds_denominator']), 'model_input_status': enum([MODEL_INPUT_STATUS]), 'model_reader_capability': enum([MODEL_CAPABILITY]), 'comparison': obj({k: obj({'value': enum(v), 'witness_refs': refs}) for k, v in COMPARISON_VALUES.items()}), 'numerator': metadata, 'denominator': deepcopy(metadata)})}
