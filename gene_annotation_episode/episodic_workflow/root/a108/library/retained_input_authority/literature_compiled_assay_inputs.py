"""Source relationships and possessed saved operands for within-assay arithmetic.

Scientific meanings are explicit episode interpretations. A selected component
is authorized through its own repository's exact fact view; a source reference
alone never grants the private numerical contents of an upstream child sheet.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import REF, obj
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_assay_inputs import ASSAY_LITERAL_FIELDS, ARRANGEMENTS, ENDPOINTS, PRIMITIVE_ORDER, _nullable, _witness_schema
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_experimental_contracts import ExperimentalContractError
ROLES = PRIMITIVE_ORDER
NS_ASSAY = 'literature_assay_cells'
NS_OPTICAL = 'literature_optical_cells'
NS_RECOVERY = 'literature_calibration_recovery_cells'
NS_ACTIVE = 'literature_active_site_cells'
NS_AMOUNT = 'literature_amount_cells'
NS_NATIVE = 'literature_rate_source_meaning_cells'
NS_REPLICATE = 'literature_rate_replicate_cells'
RATE_NAMES = ('reference_rate', 'test_rate', 'rate_difference')
ALLOWLIST = {'q': {NS_ASSAY: ('net_rate', 'corrected_activity'), NS_OPTICAL: ('net_rate',), NS_NATIVE: RATE_NAMES, NS_REPLICATE: RATE_NAMES}, 'g': {NS_ASSAY: ('contaminant_rate',), NS_NATIVE: RATE_NAMES, NS_REPLICATE: RATE_NAMES}, 'k': {NS_ASSAY: ('recovery',), NS_RECOVERY: ('recovery',)}, 'E': {NS_ASSAY: ('protein_amount',), NS_ACTIVE: ('active_site_concentration', 'total_monomer_concentration'), NS_AMOUNT: ('numerator_amount', 'denominator_amount')}, 'u': {NS_ASSAY: ('condition_test_rate',), NS_NATIVE: RATE_NAMES[:2], NS_REPLICATE: RATE_NAMES[:2]}, 'v': {NS_ASSAY: ('condition_reference_rate',), NS_NATIVE: RATE_NAMES[:2], NS_REPLICATE: RATE_NAMES[:2]}}
LINKS = {'q': ('net_background_corrected_assay_endpoint', 'already_normalized_assay_activity'), 'g': ('additional_contaminant_contribution',), 'k': ('applicable_reporter_standard',), 'E': ('same_assay_active_molecules', 'same_assay_total_molecules'), 'u': ('test_nuisance_control_excludes_intended_change',), 'v': ('reference_nuisance_control_excludes_intended_change',)}
LINK_LIMITS = ('different_assay_or_endpoint', 'unknown', 'conflicting')
STAGES = ('background', 'contaminant', 'recovery', 'molecule_amount', 'nuisance_condition')
STAGE_VALUES = ('not_applied', 'already_applied', 'unknown', 'conflicting')

def _fail(code, field):
    raise ExperimentalContractError(code, field)

def interpretation_schema(values):
    return obj({'value': {'enum': list(values)}, 'witnesses': {'type': 'array', 'items': _witness_schema()}})

def source_schema(namespace):
    if namespace == NS_ASSAY:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_assay_storage import assay_cells_schema
        return assay_cells_schema()
    if namespace == NS_OPTICAL:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_optical_storage import optical_cells_schema
        return optical_cells_schema()
    if namespace == NS_RECOVERY:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_calibration_recovery_storage import calibration_recovery_cells_schema
        return calibration_recovery_cells_schema()
    if namespace == NS_ACTIVE:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_active_site_storage import active_site_cells_schema
        return active_site_cells_schema()
    if namespace == NS_AMOUNT:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_amount_storage import amount_cells_schema
        return amount_cells_schema()
    if namespace == NS_NATIVE:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_rate_meaning_delivery import rate_source_meaning_cells_schema
        return rate_source_meaning_cells_schema()
    if namespace == NS_REPLICATE:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_rate_replicate_storage import rate_replicate_cells_schema
        return rate_replicate_cells_schema()
    _fail('unsupported_compilation_namespace', 'namespace')
COMMON_REQUEST = 'a105_common_assessment_request_v1'
COMMON_POPULATION = 'a105_common_assessment_population_v1'
COMMON_INPUTS = 'a105_common_assessment_inputs_v1'
COMMON_ARMS = ('reference', 'test')
COMMON_BASE_ROLES = ('product', 'reporter', 'kcat', 'Km', 'Kd', 'free_substrate', 'background', 'recovery', 'active_fraction', 'nuisance_response')
COMMON_ROLES = tuple((base + '_' + arm for base in COMMON_BASE_ROLES for arm in COMMON_ARMS))
COMMON_CONTEXT = ('organism', 'molecule', 'construct', 'substrate', 'product_or_ligand', 'system', 'conditions')
COMMON_ARM_CONTEXT = ('construct', 'assay', 'endpoint', 'denominator', 'preparation', 'conditions', 'sampling_unit', 'intended_change', 'additional_differences')
COMMON_GROUPS = ('product', 'reporter', 'kinetic', 'binding', 'correction')
COMMON_LINKS = ('same_estimand', 'compatible_supported', 'different_with_declared_model', 'incompatible', 'unknown', 'conflicting')
COMMON_ASSUMPTIONS = ('equilibrium', 'one_site', 'free_substrate_treatment', 'binding_catalysis_applicability', 'turnover_proportional_to_occupancy', 'fixed_post_binding_rate', 'equal_recovery', 'equal_active_fraction', 'equal_nuisance_response')
COMMON_MODEL_STATUSES = ('supported', 'stipulated_sensitivity', 'unknown', 'conflicting')
COMMON_PARAMETER_KINDS = dict(Kd='reported_spectral_binding_Kd', free_substrate='free_substrate_concentration', background='same_scale_other_contribution_rate', recovery='applicable_reporter_recovery', active_fraction='active_molecules_per_nominal_molecule', nuisance_response='nuisance_response_excluding_intended_change')
COMMON_REASONS = ('estimate_not_selected', 'source_number_unavailable', 'source_unit_unsupported', 'native_nondetection_not_point', 'bounded_estimate_unsupported', 'approximate_estimate_unsupported', 'source_parameter_meaning_unknown', 'source_parameter_meaning_conflicting', 'native_component_unavailable', 'received_parameter_kind_mismatch', 'received_parameter_unit_mismatch', 'received_construct_unresolved', 'source_construct_mismatch', 'normalization_relationship_unknown', 'endpoint_relationship_unknown', 'relationship_incompatible', 'relationship_conflicting', 'subject_relationship_unresolved', 'model_not_selected', 'model_assumption_unknown', 'model_assumption_conflicting', 'positive_operand_required', 'zero_denominator', 'numerical_model_range', 'joint_covariance_not_selected', 'joint_covariance_incomplete', 'covariance_status_unknown', 'positive_variance_required', 'correction_factorization_unresolved', 'correction_applicability_unresolved', 'correction_conversion_unimplemented', 'exact_source_conversion_unimplemented', 'unrequested_numerical_scope_unresolved', 'no_independent_replication_inferred')

def _common_array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _common_exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})

def _common_meaning_schema(values):
    return interpretation_schema(values)

def _common_selection_schema():
    from gene_annotation_episode.episodic_workflow.root.a108.library.literature_partner_source_fields import number_selector_schema
    native = {'anyOf': [obj({'kind': {'const': 'received_component'}, 'namespace': {'const': ns}, 'sheet_ref': deepcopy(REF), 'component': {'enum': list(names)}}) for ns, names in (('literature_product_coupling_cells', ('reported_product_activity', 'reported_cofactor_activity')), ('literature_kinetic_cells', ('numerator_parameter', 'denominator_parameter')), ('literature_calibration_recovery_cells', ('recovery',)))]}
    parameter = obj({'kind': {'const': 'source_parameter'}, 'source_kind': {'enum': ['primary_source', 'supplied_model', 'synthetic_fixture']}, 'parameter_kind': _common_meaning_schema(tuple(COMMON_PARAMETER_KINDS.values())), 'layout': {'enum': ['table', 'single_record']}, 'record': _nullable(_witness_schema()), 'number': _nullable(number_selector_schema()), 'row_label': _witness_schema(), 'quantity_label': _witness_schema(), 'unit': _witness_schema(), 'semantics': _common_meaning_schema(('reported_point', 'reported_nondetection', 'unknown', 'conflicting')), 'method': _nullable(_witness_schema()), 'assay': _nullable(_witness_schema()), 'conditions': _nullable(_witness_schema()), 'normalization': _nullable(_witness_schema()), 'population': _nullable(_witness_schema()), 'physical_identity': _nullable(_witness_schema()), 'reported_spread': _nullable(number_selector_schema())})
    return {'anyOf': [native, parameter]}

def common_assessment_population_schema():
    """Prospective closed scientific request, separate from episode TASK text."""
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_compiled_assay_calculations import COMMON_COMPONENTS
    links = obj({name: _common_meaning_schema(COMMON_LINKS) for name in ('endpoint', 'normalization', 'preparation', 'conditions')})
    model = obj({'kind': {'const': 'one_site_equilibrium'}, 'scope': {'enum': ['supported_physical', 'conditional_sensitivity']}, 'substrate_ownership': {'enum': ['shared_owner', 'separate_owners']}, 'substrate_uncertainty': {'enum': ['fixed_scenario', 'selected_estimate_covariance']}, 'assumptions': obj({name: _common_meaning_schema(COMMON_MODEL_STATUSES) for name in COMMON_ASSUMPTIONS})})
    return obj({'version': {'const': COMMON_REQUEST}, 'population_version': {'const': COMMON_POPULATION}, 'source_ref': deepcopy(REF), 'source_kind': {'enum': ['primary_source', 'synthetic_fixture']}, 'assertion': obj({**{name: _nullable(_witness_schema()) for name in COMMON_CONTEXT}, 'resolution': {'enum': ['identified_product_formation', 'saturation_turnover', 'low_substrate_efficiency', 'binding_occupancy_alternative']}, 'question': {'enum': ['existence', 'relative_effect', 'named_alternative']}}), 'arms': obj({arm: obj({name: _nullable(_witness_schema()) for name in COMMON_ARM_CONTEXT}) for arm in COMMON_ARMS}), 'subject_relationship': _common_meaning_schema(('same_construct_supported', 'intended_variant', 'different', 'unknown', 'conflicting')), 'relationships': obj({group: deepcopy(links) for group in COMMON_GROUPS}), 'product_reporter_relationship': _common_meaning_schema(('author_assigned_pair', 'different', 'unknown', 'conflicting')), 'sampling_relationship': _common_meaning_schema(('shared_units', 'paired_units_supported', 'independent_units_supported', 'unknown', 'conflicting')), 'estimates': obj({role: _nullable(_common_selection_schema()) for role in COMMON_ROLES}), 'model': _nullable(model), 'correction_factorization': _common_meaning_schema(COMMON_MODEL_STATUSES), 'covariance_source_refs': _common_array(REF, True), 'requested_cells': _common_array({'enum': list(COMMON_COMPONENTS)}, True)})

def _common_location_schema():
    return obj({'source_ref': deepcopy(REF), 'artifact_ref': deepcopy(REF), 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})

def common_assessment_inputs_schema():
    """Host-only retained inputs; not a parent return or a model-facing sheet."""
    estimate = obj({'role': {'enum': list(COMMON_ROLES)}, 'selection': _common_selection_schema(), 'value': {'type': ['number', 'null']}, 'exact_value': _nullable(_common_exact_schema()), 'native_value': {'type': ['number', 'null']}, 'native_exact_value': _nullable(_common_exact_schema()), 'native_unit': {'type': ['string', 'null']}, 'unit': {'type': ['string', 'null']}, 'status': {'enum': ['point', 'unavailable']}, 'native_semantics': {'enum': ['reported_point', 'reported_nondetection', 'reported_negligible', 'unknown', 'conflicting']}, 'origin': {'enum': ['reported', 'derived', 'calculated', 'synthetic', 'proposed']}, 'numeric_origin': {'enum': ['received_exact_component', 'original_source_token', 'saved_canonical_decimal']}, 'owner_key': {'type': 'string'}, 'physical_owner_key': {'type': ['string', 'null']}, 'population_key': {'type': ['string', 'null']}, 'assay_key': {'type': ['string', 'null']}, 'dependency_keys': _common_array({'type': 'string'}, True), 'locations': _common_array(_common_location_schema()), 'source_missing_reasons': _common_array({'enum': list(COMMON_REASONS)}, True), 'implementation_reasons': _common_array({'enum': list(COMMON_REASONS)}, True), 'reported_spread': _nullable(obj({'exact_value': _nullable(_common_exact_schema()), 'statistic': {'enum': ['unspecified', 'sd', 'sem']}, 'unit': {'type': ['string', 'null']}, 'location': _common_location_schema()}))})
    covariance = obj({'source_ref': deepcopy(REF), 'artifact_ref': deepcopy(REF), 'roles': _common_array({'enum': list(COMMON_ROLES)}, True), 'owner_keys': _common_array({'type': 'string'}), 'units': _common_array({'type': 'string'}), 'dependency_keys': _common_array(_common_array({'type': 'string'})), 'matrix_exact': _nullable(_common_array(_common_array(_common_exact_schema()))), 'variance_status': {'enum': ['known', 'estimated', 'unknown']}, 'origin': {'enum': ['reported', 'derived', 'synthetic']}, 'basis': {'const': 'joint_covariance_of_selected_estimates'}})
    return obj({'version': {'const': COMMON_INPUTS}, 'request': common_assessment_population_schema(), 'estimates': obj({role: _nullable(estimate) for role in COMMON_ROLES}), 'covariance_blocks': _common_array(covariance), 'source_refs': _common_array(REF, True), 'source_artifacts': _common_array(obj({'source_ref': deepcopy(REF), 'representation': {'enum': ['original', 'text']}, 'artifact_ref': deepcopy(REF)})), 'numerical_scope_locations': _common_array(_common_location_schema()), 'component_snapshots': _common_array({'anyOf': [_common_snapshot_schema('literature_product_coupling_cells'), _common_snapshot_schema('literature_kinetic_cells'), _common_snapshot_schema('literature_calibration_recovery_cells')]})})

def _common_snapshot_schema(namespace):
    if namespace == 'literature_product_coupling_cells':
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_product_coupling_storage import product_coupling_cells_schema
        row = product_coupling_cells_schema()['items']
    elif namespace == 'literature_kinetic_cells':
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_kinetic_storage import kinetic_cells_schema
        row = kinetic_cells_schema()['items']
    else:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_calibration_recovery_storage import calibration_recovery_cells_schema
        row = calibration_recovery_cells_schema()['items']
    return obj({'selection': _common_selection_schema(), 'row': row})
