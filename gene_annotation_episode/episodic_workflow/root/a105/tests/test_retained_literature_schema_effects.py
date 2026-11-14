"""Original incoming scientific qualifications and closed schema meanings."""
from copy import deepcopy
from importlib import import_module

import pytest
from jsonschema import Draft202012Validator

AXES = ('a101', 'a108')


def reader(axis, name):
    if axis == 'a108' and name == 'literature_partner_defined_units':
        return import_module('gene_annotation_episode.episodic_workflow.root.a108.library.literature_partner_defined_units')
    return import_module('gene_annotation_episode.episodic_workflow.root.' + axis + '.library.retained_input_authority.' + name)


@pytest.mark.parametrize('axis', AXES)
def test_original_unavailable_assay_reasons_remain_reportable(axis):
    module = reader(axis, 'literature_assay_storage')
    schema = module.assay_cells_schema()['items']['properties']['unavailable_reason']
    validator = Draft202012Validator(schema)
    for reason in ('correction_inputs_not_supplied', 'primitive_covariance_not_supplied', 'distinct_residual_variance_not_supplied'):
        assert validator.is_valid(reason)
    assert not validator.is_valid('missing_evidence_proves_target_function')


@pytest.mark.parametrize('axis', AXES)
def test_electrical_schema_preserves_original_conditional_meaning(axis):
    module = reader(axis, 'literature_channel_storage')
    schema = module._cell_schema('chord_conductance')
    value = {'value': None, 'unit': 'pS', 'status': 'unavailable',
        'formula': '1000*abs(current)/(abs(applied_voltage-reversal_voltage))', 'origin': 'derived',
        'unavailable_reason': 'electrical_inputs_not_supplied', 'section': 'conditions_and_normalization',
        'meaning': module.MEANINGS['chord_conductance'],
        'conditional_on': ['reversal_condition_applicable_to_current_voltage', 'defined_chord_not_differential_conductance'],
        'operand_roles': ['current', 'applied_voltage', 'reversal_voltage'], 'measurement_keys': []}
    validator = Draft202012Validator(schema)
    assert validator.is_valid(value)
    invalid = deepcopy(value); invalid['conditional_on'] = []
    assert not validator.is_valid(invalid)
    assert module.CELL_CONDITIONS['charge_equivalent_rate'] == ['electrical_charge_equivalents_only']
    assert module.FORMULAS['charge_equivalent_rate'] == 'abs(current)*1e-12/1.602176634e-19'
    assert module.SECTIONS['charge_equivalent_rate'] == 'charge_attribution_limit'
    assert module.COMPONENT_ROLES['charge_equivalent_rate'] == ('current',)


@pytest.mark.parametrize('axis', AXES)
def test_compiled_meanings_preserve_scope_and_no_annotation_credit(axis):
    module = reader(axis, 'literature_compiled_assay_calculations')
    assert module.SECTIONS['corrected_activity'] == 'compiled_source_endpoint_effect'
    assert module.SECTIONS['recovery'] == 'validity'
    assert module.MEANINGS['measured_endpoint_per_selected_amount'] == 'Measured endpoint rate per selected molecular amount; not contaminant-isolated or nuisance-corrected.'
    assert module.MEANINGS['source_profile_log_ratio'] == 'Existing conditional known-normal nonnegative-presence profile; not a probability of function.'
    assert module.MEANINGS['source_presence_index'] == 'Existing proposed bounded transform of that conditional profile; not annotation credit.'
    assert module.MEANINGS_V2['source_presence_index'] == module.MEANINGS['source_presence_index']
    assert module.SECTIONS['effect_standard_uncertainty'] == 'uncertainty'


def interpretation(value):
    return {'value': value, 'witnesses': []}


def unresolved_meaning():
    return {'status': 'unknown', 'label': None, 'witnesses': [],
        'canonical_witness': None, 'canonical_correspondence': interpretation('unknown')}


@pytest.mark.parametrize('axis', AXES)
def test_controlled_response_schema_resolves_original_unresolved_relationships(axis):
    schema = reader(axis, 'literature_controlled_response_inputs').controlled_response_arguments_schema()
    value = {'version': 'controlled_response_source_selection_v1', 'source_ref': 'source_' + 'a' * 24,
        'images': [], 'arms': {role: None for role in ('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0')},
        'relationships': {'condition1_target': unresolved_meaning(), 'condition0_target': unresolved_meaning(),
            'condition_levels_relation': interpretation('unknown'), 'subject_construct_across_conditions': interpretation('unknown'),
            'condition1_control_application': interpretation('unknown'), 'condition0_control_application': interpretation('unknown'),
            'control_reference_reuse': interpretation('unknown'), 'nonintended_conditions': interpretation('unknown'), 'intended_factor': None},
        'covariance': None, 'variance_status': interpretation('unknown'), 'model_kind': interpretation('none')}
    validator = Draft202012Validator(schema)
    assert schema['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
    assert validator.is_valid(value)
    invalid = deepcopy(value); invalid['relationships']['condition_levels_relation']['value'] = 'proven_target_support'
    assert not validator.is_valid(invalid)


@pytest.mark.parametrize('axis', AXES)
def test_original_defined_unit_schema_accepts_selectors_not_supplied_scale(axis):
    schema = reader(axis, 'literature_partner_defined_units').defined_rate_unit_schema()
    witness = {'source_ref': 'source_' + 'a' * 24, 'representation': 'text', 'start': 0, 'end': 1, 'quote': '1'}
    definition = {name: deepcopy(witness) for name in ('bridge', 'clause', 'amount_unit', 'time_unit', 'endpoint', 'endpoint_entity', 'definition_entity')}
    definition['amount'] = {'witness': deepcopy(witness), 'number_start': 0, 'number_end': 1}
    value = {'kind': 'source_defined_rate_unit', 'witness': witness, 'definition': definition}
    validator = Draft202012Validator(schema)
    assert validator.is_valid(value)
    invalid = deepcopy(value); invalid['definition']['amount'] = 1.0
    assert not validator.is_valid(invalid)
    invalid = deepcopy(value); invalid['multiplier'] = 1000
    assert not validator.is_valid(invalid)


@pytest.mark.parametrize('axis', AXES)
def test_ion_schema_retains_unresolved_origin_and_zero_denominator_fields(axis):
    schema = reader(axis, 'literature_ion_discrimination_inputs').ion_discrimination_sheet_schema()
    cell_schema = {'$defs': schema['$defs'], **deepcopy(schema['$defs']['Cell'])}
    value = {'component': 'activity_ratio', 'value': None, 'threshold': None, 'unit': 'dimensionless',
        'status': 'unavailable', 'origin': 'derived', 'meaning': 'signed_activity_estimator_ratio',
        'reported_domain': None, 'nominal_domain': None, 'physical_domain': None, 'relation': 'none',
        'approximation': 'unknown', 'quantity_kind': 'unknown', 'scientific_applicability': 'unresolved',
        'unavailable_reasons': ['physical_domain_inconsistent', 'shared_activity_covariance_inconsistent'],
        'limitations': ['no_annotation_credit'], 'dependencies': [], 'variance_status': 'unknown',
        'annotation_credit': None, 'estimator_domain': None, 'formula_code': 'preferred_activity/alternative_activity',
        'zero_denominator_case': 'unknown', 'derivation': 'derived_activity_ratio',
        'source_qualifications': ['selected_qualification_unknown']}
    validator = Draft202012Validator(cell_schema)
    assert validator.is_valid(value)
    for key in ('zero_denominator_case', 'derivation', 'source_qualifications'):
        invalid = deepcopy(value); del invalid[key]
        assert not validator.is_valid(invalid)
    dependency = {'role': 'preferred', 'source_ref': 'source_' + 'a' * 24, 'component_ref': None,
        'namespace': None, 'component': None, 'physical_keys': [], 'opaque_dependency_keys': [],
        'physical_identity_status': 'cross_component_identity_unknown', 'origin': 'graph_derived'}
    validator = Draft202012Validator(schema['$defs']['Dependency'])
    assert validator.is_valid(dependency)
    invalid = deepcopy(dependency); del invalid['origin']
    assert not validator.is_valid(invalid)
