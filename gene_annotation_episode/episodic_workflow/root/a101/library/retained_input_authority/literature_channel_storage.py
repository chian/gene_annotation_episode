"""Selected electrical components, exact requested returns and saved custody.

Scientific source reading and arithmetic occur once at selected population.
Saved reads authenticate the original request, result and source associations;
they neither reopen scientific artifacts nor rerun their numerical conversion.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_channel_inputs import SOURCE_KINDS, LITERAL_FIELDS, ARRANGEMENT_KINDS, SPREAD_KINDS
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_channel_calculations import QUANTITIES, CURRENT_KINDS, ARRANGEMENT_RELATIONS, COMPONENTS, UNITS, MEANINGS, SECTIONS, PRIMITIVE_ORDER
NAMESPACE = 'literature_channel_cells'
FORMULAS = {name: name for name in QUANTITIES}
FORMULAS.update(
    absolute_driving_voltage='abs(applied_voltage-reversal_voltage)',
    chord_conductance='1000*abs(current)/(abs(applied_voltage-reversal_voltage))',
    charge_equivalent_rate='abs(current)*1e-12/1.602176634e-19',
    chord_conductance_variance='J*covariance*J_transpose; J=[1000*sign(I)/abs(D),-1000*abs(I)*sign(D)/D^2,1000*abs(I)*sign(D)/D^2]; D=V-E',
    chord_conductance_standard_uncertainty='sqrt(chord_conductance_variance)',
)
COMPONENT_ROLES = {name: (name,) for name in QUANTITIES}
COMPONENT_ROLES.update(absolute_driving_voltage=PRIMITIVE_ORDER[1:],
    chord_conductance=PRIMITIVE_ORDER, charge_equivalent_rate=('current',),
    chord_conductance_variance=PRIMITIVE_ORDER,
    chord_conductance_standard_uncertainty=PRIMITIVE_ORDER)
CONDITIONS = ('reversal_condition_applicable_to_current_voltage', 'defined_chord_not_differential_conductance', 'electrical_charge_equivalents_only', 'first_order_covariance_propagation')
CELL_CONDITIONS = {name: [] for name in QUANTITIES}
CELL_CONDITIONS.update(absolute_driving_voltage=list(CONDITIONS[:1]),
    chord_conductance=list(CONDITIONS[:2]), charge_equivalent_rate=[CONDITIONS[2]],
    chord_conductance_variance=[*CONDITIONS[:2], CONDITIONS[3]],
    chord_conductance_standard_uncertainty=[*CONDITIONS[:2], CONDITIONS[3]])
REASONS = ('electrical_measurement_not_supplied', 'electrical_inputs_not_supplied', 'numerical_model_range', 'different_electrical_arrangements', 'reversal_condition_applicability_not_supplied', 'reversal_condition_applicability_conflicting', 'current_kind_not_supplied', 'current_kind_conflicting', 'zero_driving_voltage', 'absolute_current_not_differentiable_at_zero', 'primitive_covariance_not_supplied', 'primitive_measurement_identity_not_supplied', 'primitive_variance_status_unknown')
INPUT_LIMITS = ('literal_custody_does_not_prove_applicability', 'matching_conditions_do_not_merge_measurements', 'reported_spreads_are_not_covariance', 'charge_equivalents_are_not_ion_flux', 'no_pore_normalization', 'no_replication_inference')
SHEET_LIMITS = ('no_ion_flux_attribution', 'no_pore_or_polypeptide_normalization', 'no_independent_preparation_count', 'no_overall_reliability_grade', 'no_annotation_credit')
ORIGINS = ('reported', 'derived', 'graph_derived', 'synthetic')

def _enum(values, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'enum': [*values, None] if nullable else list(values)}

def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _reference(namespace, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}

def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}

def _witness_schema():
    return obj({'source_ref': _reference('source'), 'artifact_ref': _reference('artifact'), 'representation': _enum(('original', 'text')), 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}, 'quote': {'type': 'string', 'minLength': 1}})

def _meaning_schema():
    return obj({'status': _enum(('selected', 'not_selected', 'withheld_electrical_operand')), 'witness': _nullable(_witness_schema())})

def _interpretation_schema(values):
    return obj({'value': _enum(values), 'support': _array(_meaning_schema())})

def _reading_schema():
    return _nullable(obj({'number': _witness_schema(), 'native_value': {'type': 'number'}, 'native_unit': {'type': 'string', 'minLength': 1}, 'canonical_unit': _enum(('pA', 'mV', 'pS')), 'origin': _enum(ORIGINS), 'conversion_origin': _enum(ORIGINS)}))

def _cell_schema(component=None):

    def specified(mapping):
        return {'type': 'string', 'const': mapping[component]} if component else _enum(tuple(dict.fromkeys(mapping.values())))
    return obj({'value': {'type': ['number', 'null']}, 'unit': specified(UNITS), 'status': _enum(('populated', 'unavailable')), 'formula': specified(FORMULAS), 'origin': _enum(ORIGINS), 'unavailable_reason': _enum(REASONS, True), 'section': specified(SECTIONS), 'meaning': specified(MEANINGS), 'conditional_on': {'const': CELL_CONDITIONS[component]} if component else _array(_enum(CONDITIONS), True), 'operand_roles': {'const': list(COMPONENT_ROLES[component])} if component else _array(_enum(QUANTITIES), True), 'measurement_keys': _array({'type': 'string', 'minLength': 1}, True)})

def channel_cells_schema():
    operand = obj({'role': _enum(QUANTITIES), 'context': _meaning_schema(), 'reading': _reading_schema(), 'spread_reading': _reading_schema(), 'spread_kind': _interpretation_schema(SPREAD_KINDS), 'measurement_key': {'type': ['string', 'null']}})
    return {**_array(obj({'sheet_ref': _reference('source'), 'evidence_source_ref': _reference('source'), 'evaluation_scope': {'type': 'string', 'const': 'source_electrical_activity'}, 'component': _enum(COMPONENTS), **_cell_schema()['properties'], 'source_kind': _enum(SOURCE_KINDS), 'source_meanings': obj({name: _meaning_schema() for name in LITERAL_FIELDS}), 'arrangement_kind': _interpretation_schema(ARRANGEMENT_KINDS), 'current_kind': _interpretation_schema(CURRENT_KINDS), 'arrangement_relation': _interpretation_schema(ARRANGEMENT_RELATIONS), 'operands': _array(operand), 'variance_status': _enum(('known', 'estimated', 'unknown')), 'covariance_origin': _enum(('reported', 'derived', 'synthetic'), True), 'covariance_source_ref': _reference('source', True), 'replication_status': {'type': 'string', 'const': 'not_evaluated_by_this_component'}, 'interpretation_limits': {'const': [*INPUT_LIMITS, *SHEET_LIMITS]}, 'annotation_credit': {'type': 'null'}})), 'x-source': NAMESPACE}
