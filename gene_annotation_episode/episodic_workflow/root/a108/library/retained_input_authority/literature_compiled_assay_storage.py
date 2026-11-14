"""Selected saved-component compilation and exact scoped numerical returns.

Population alone reads source context and computes. Saved projection authenticates
original receipts and content-addressed snapshots without upstream acquisition,
unit conversion, scientific arithmetic or additional controller observations.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import obj
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_compiled_assay_inputs import ROLES, ALLOWLIST, ASSAY_LITERAL_FIELDS, ENDPOINTS, ARRANGEMENTS, STAGES, STAGE_VALUES, LINKS, LINK_LIMITS, source_schema, NS_ASSAY, NS_OPTICAL, NS_RECOVERY, NS_ACTIVE, NS_AMOUNT, NS_NATIVE, NS_REPLICATE
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_compiled_assay_calculations import COMPONENTS, SECTIONS, MEANINGS, REASONS, FORMULA_VARIANTS, QUALIFICATIONS, COMPONENTS_V2, MEANINGS_V2, REASONS_V2, FORMULAS_V2
NAMESPACE = 'literature_compiled_assay_cells'
NAMESPACE_V2 = 'literature_compiled_assay_v2_cells'
NAMESPACE_V3 = 'literature_compiled_assay_v3_cells'
COMMON_SCOPE = 'common_assertion_contrast'

def compiled_assay_v3_cells_schema():
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_compiled_assay_inputs import common_assessment_inputs_schema
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_compiled_assay_calculations import common_assessment_sheet_schema, COMMON_COMPONENTS
    sheet = common_assessment_sheet_schema()['properties']
    metadata = {name: deepcopy(schema) for name, schema in sheet.items() if name not in ('version', 'cells', 'evaluation_scope')}
    covariance = deepcopy(common_assessment_inputs_schema()['properties']['covariance_blocks']['items']['properties'])
    del covariance['matrix_exact']
    return {**_array(obj({**deepcopy(sheet['cells']['items']['properties']), **metadata, 'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'const': COMMON_SCOPE}, 'scientific_sheet_version': deepcopy(sheet['version']), 'formula_code': {'enum': [name + '_compiled_v3' for name in COMMON_COMPONENTS]}, 'covariance_provenance': {'anyOf': [obj(covariance), {'type': 'null'}]}})), 'x-source': NAMESPACE_V3}

def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _ref(namespace='source', nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}

def _text(nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'minLength': 1}

def _selector():
    return obj({'namespace': {'type': 'string', 'enum': list(dict.fromkeys((ns for choices in ALLOWLIST.values() for ns in choices)))}, 'sheet_ref': _ref(), 'component': {'type': 'string', 'enum': list(dict.fromkeys((name for choices in ALLOWLIST.values() for names in choices.values() for name in names)))}})

def _dependency():
    return obj({'role': {'type': 'string', 'enum': list(ROLES)}, 'selection': {'anyOf': [_selector(), {'type': 'null'}]}, 'component_key': _text(True), 'quantity_key': _text(True), 'canonical_physical_keys': _array(_text(), True), 'recorded_dependency_keys': _array(_text(), True), 'physical_identity_status': {'type': 'string', 'enum': ['partly_canonical', 'cross_component_identity_unknown', 'definition_identity']}, 'identity_stage': {'type': ['string', 'null'], 'enum': [*STAGES, None]}})

def _numerical_cell(version=1):
    return obj({'value': {'type': ['number', 'null']}, 'unit': {'type': ['string', 'null'], 'enum': ['uM/min', 'uM', 'dimensionless', 'per_min', 'per_min_squared', 'min_squared', 'nM', 'fraction', 'umol/min', 'nmol/min', 'mmol/min', 'nM/min', 'per_s', 'umol/min/mg', 'nmol/min/mg', 'mg/ml', None]}, 'status': {'type': 'string', 'enum': ['populated', 'unavailable']}, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *(REASONS_V2 if version == 2 else REASONS)]}, 'formula': {'type': 'string', 'enum': list(dict.fromkeys((*FORMULA_VARIANTS, *FORMULAS_V2.values()))) if version == 2 else list(FORMULA_VARIANTS)}, 'origin': {'type': 'string', 'enum': ['reported', 'derived', 'graph_derived', 'synthetic', 'proposed', 'definition_identity']}, 'section': {'type': 'string', 'enum': list(dict.fromkeys(SECTIONS.values()))}, 'meaning': {'type': 'string', 'enum': list(dict.fromkeys((MEANINGS_V2 if version == 2 else MEANINGS).values()))}, 'conditional_on': _array({'type': 'string', 'enum': ['first_order_covariance_propagation', 'known_variance', 'known_normal_nonnegative_presence']}), 'qualifications': _array({'type': 'string', 'enum': list(QUALIFICATIONS)})})

def _native_quantity_schema():
    properties = [source_schema(ns)['items']['properties'] for ns in (NS_ASSAY, NS_OPTICAL, NS_RECOVERY, NS_ACTIVE, NS_AMOUNT, NS_NATIVE, NS_REPLICATE)]

    def union(field, fallback):
        choices = [deepcopy(p[field]) for p in properties if field in p]
        return {'anyOf': [*choices, fallback]}
    return {'anyOf': [obj({'value': {'type': ['number', 'null']}, 'source_unit': union('unit', {'type': 'null'}), 'threshold': {'type': ['number', 'null']}, 'bound': {'type': 'string', 'enum': ['none', 'point', 'lt', 'le', 'gt', 'ge']}, 'approximate': {'type': ['boolean', 'null']}, 'reported_domain': union('reported_domain', {'type': 'null'}), 'exact_domain': union('exact_domain', {'type': 'null'}), 'meaning': {'type': 'string', 'const': 'unchanged_selected_native_component_domain'}, 'domain_conversion': {'type': 'string', 'const': 'not_converted'}}), {'type': 'null'}]}

def compiled_assay_cells_schema(version=1):
    if version == 3:
        return compiled_assay_v3_cells_schema()
    components = COMPONENTS_V2 if version == 2 else COMPONENTS
    schema = {**_array(obj({'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'type': 'string', 'const': 'compiled_source_endpoint'}, 'component': {'type': 'string', 'enum': list(components)}, **_numerical_cell(version)['properties'], 'formula_code': {'type': 'string', 'enum': [name + ('_compiled_v2' if version == 2 else '_compiled_v1') for name in components]}, 'dependencies': _array(_dependency()), 'native_quantity': _native_quantity_schema(), 'operand_meanings': obj({role: {'type': 'string', 'enum': [*LINKS[role], *LINK_LIMITS]} for role in ROLES}), 'assay_meanings': obj({name: _text(True) for name in ASSAY_LITERAL_FIELDS}), 'endpoint_kind': {'type': 'string', 'enum': list(ENDPOINTS)}, 'arrangement_kind': {'type': 'string', 'enum': list(ARRANGEMENTS)}, 'correction_stages': obj({name: {'type': 'string', 'enum': list(STAGE_VALUES)} for name in STAGES}), 'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']}, 'observation_model': {'type': 'string', 'enum': ['none', 'known_normal_nonnegative_presence']}, 'covariance_source_ref': _ref(nullable=True), 'residual_variance_source_ref': _ref(nullable=True), 'operand_eligibility': obj({role: {'type': ['string', 'null'], 'enum': [None, *REASONS]} for role in ROLES}), 'partial_uncertainty_status': {'type': 'string', 'const': 'unimplemented'}, 'covariance_input_status': {'type': 'string', 'enum': ['not_selected', 'selected_known', 'selected_estimated', 'selected_unknown']}, 'annotation_credit': {'type': 'null'}})), 'x-source': NAMESPACE_V2 if version == 2 else NAMESPACE}
    if version == 2:
        properties = schema['items']['properties']
        properties['partial_uncertainty_status'] = {'type': 'string', 'const': 'component_scoped'}
        properties['uncertainty'] = obj({'estimand_component': {'type': ['string', 'null'], 'enum': [None, 'measured_endpoint_per_selected_amount', 'calibrated_measured_endpoint_per_selected_amount', 'corrected_activity']}, 'scope': {'type': 'string', 'enum': ['not_applicable', 'operand_propagated', 'total_with_distinct_residual']}, 'covariance_source_ref': _ref(nullable=True), 'source_primitive_order': _array({'type': 'string', 'enum': list(ROLES)}, True), 'operand_order': _array({'type': 'string', 'enum': list(ROLES)}, True), 'operand_keys': _array(_text()), 'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']}, 'covariance_origin': {'type': ['string', 'null'], 'enum': [None, 'reported', 'derived', 'synthetic']}, 'propagation_model': {'type': 'string', 'enum': ['none', 'first_order_covariance_propagation']}})
        schema['items']['required'] = list(properties)
    elif version != 1:
        raise ValueError('unsupported_compiled_assay_population_version')
    return schema
