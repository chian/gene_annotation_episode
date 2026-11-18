"""Source-bound v3 readers and closed parsed contracts for internal A105 sheets.

These host functions read experimental quantities and preserve source meanings.
"""
from __future__ import annotations
from copy import deepcopy as cp
import json
from fractions import Fraction
import errno
import hashlib
from functools import lru_cache
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.tools import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.tools import literature_controlled_response_figure_inputs as graph_reader
obj, ref, null = (shared.obj, shared.ref, shared.nullable)
T, N, I, B = (shared.TEXT, {'type': 'number'}, shared.OFFSET, {'type': 'boolean'})
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}

def arr(value, **kw):
    return {'type': 'array', 'items': value, **kw}

def enum(*values):
    return {'enum': list(values)}

def embed(schema, prefix, target):

    def rename(value):
        if isinstance(value, dict):
            return {k: '#/$defs/' + prefix + v[8:] if k == '$ref' and v.startswith('#/$defs/') else rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return value
    for key, val in schema.get('$defs', {}).items():
        target[prefix + key] = rename(val)
    return rename({k: v for k, v in schema.items() if k not in ('$defs', '$schema')})

def _graph_schema():
    D = cp(shared._selection_core_schema()['$defs'])
    D['Rational'] = obj({'numerator': {'type': 'string', 'pattern': '^-?(0|[1-9][0-9]*)$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})
    D['Diagnostic'] = obj({'code': enum('graph_image_unavailable', 'graph_image_unsupported', 'graph_nonopaque_roi', 'graph_scale_unknown', 'graph_scale_conflicting', 'graph_scale_unsupported', 'graph_scale_literal_unsupported', 'graph_tick_ambiguous', 'graph_tick_conflicting', 'graph_tick_unreadable', 'graph_tick_literal_unsupported', 'graph_tick_literal_numeric_range', 'graph_tick_projection_rounded', 'graph_unit_ambiguous', 'graph_unit_conflicting', 'graph_unit_unreadable', 'graph_unit_unknown', 'graph_unit_unsupported', 'graph_unit_defined_bridge_unselected', 'graph_no_bar_pixels', 'graph_ambiguous_bar_runs', 'graph_terminal_edge_clipped', 'graph_axis_degenerate', 'graph_pixel_bounds_outside_image', 'graph_numerical_model_range', 'graph_canonical_display_range', 'graph_image_label_interpretation', 'graph_axis_scale_interpretation', 'graph_conditional_digitization', 'graph_ordinate_projection_rounded', 'graph_opposite_edge_clipped', 'graph_axis_multiplier_unsupported'), 'field': T, 'domain': enum('source_representation', 'source_binding', 'reader_capability', 'source_interpretation', 'dependency'), 'source_refs': arr(T)})
    D['TextLocator'] = obj({'kind': {'const': 'text'}, 'source_ref': T, 'artifact_ref': T, 'byte_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}, 'start': I, 'end': {'type': 'integer', 'minimum': 1}})
    D['ImageLocator'] = obj({'kind': {'const': 'image'}, 'original_source_ref': T, 'original_artifact_ref': T, 'original_byte_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}, 'region': ref('Box')})
    D['WitnessRecord'] = obj({'selection': ref('Witness'), 'artifact_ref': null(T), 'byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}), 'canonical_locator': null({'oneOf': [ref('TextLocator'), ref('ImageLocator')]}), 'authentication': enum('exact_utf8_byte_span', 'image_bytes_and_geometry_only', 'unavailable'), 'attribution': enum('literal_source_record', 'investigating_episode_interpretation'), 'diagnostics': arr(ref('Diagnostic'))})
    D['SourceRecord'] = obj({'source_ref': T, 'representation': enum('original', 'text'), 'artifact_ref': null(T), 'byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}), 'state': enum('available', 'unavailable'), 'diagnostics': arr(ref('Diagnostic'))})
    D['DependencyError'] = obj({'code': T, 'field': T})
    D['ImageRecord'] = obj({'image_id': T, 'source_ref': T, 'artifact_ref': null(T), 'byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}), 'original_source_ref': T, 'original_artifact_ref': null(T), 'original_byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}), 'actual_format': null(T), 'actual_mode': null(T), 'width': null(I), 'height': null(I), 'frame_count': null(I), 'mapping': null(obj({'original_region': ref('Box'), 'colour_conversion': enum('preserve', 'rgb')})), 'pillow_version': T, 'error': null(ref('DependencyError'))})
    D['AxisScaleRecord'] = obj({'selection': ref('AxisScale'), 'witnesses': arr(ref('WitnessRecord')), 'effective_kind': enum('linear', 'logarithmic', 'nonlinear', 'unknown', 'conflicting'), 'support': enum('literal_source_text', 'episode_image_interpretation', 'unavailable', 'unresolved'), 'diagnostics': arr(ref('Diagnostic'))})
    D['AxisLiteralRecord'] = obj({'selection': ref('AxisLiteral'), 'candidates': arr(ref('WitnessRecord')), 'fragments': arr(ref('WitnessRecord')), 'raw_literal': null(T), 'exact_value': null(ref('Rational')), 'qualification': enum('source_text_literal', 'episode_image_transcription', 'unresolved'), 'status': enum('parsed', 'ambiguous', 'unreadable', 'conflicting', 'unsupported', 'dependency_unavailable'), 'diagnostics': arr(ref('Diagnostic'))})
    D['GraphUnitRecord'] = obj({'selection': ref('AxisLiteral'), 'witness': null(ref('WitnessRecord')), 'raw_unit': null(T), 'canonical_unit': null(enum('umol/min', 'uM/min', 'per_min', 'umol/min/mg')), 'exact_scale': null(ref('Rational')), 'native_registry_unit': null(enum('umol/min', 'nmol/min', 'mmol/min', 'uM/min', 'nM/min', 'per_min', 'per_s', 'umol/min/mg', 'nmol/min/mg')), 'definition_witnesses': {'type': 'null'}, 'status': enum('supported', 'unknown', 'unsupported', 'numeric_range', 'dependency_unavailable', 'endpoint_correspondence_unknown'), 'diagnostics': arr(ref('Diagnostic'))})
    D['ExactBounds'] = obj({'lower': ref('Rational'), 'upper': ref('Rational')})
    D['FloatBounds'] = obj({'lower': N, 'upper': N})
    D['Run'] = obj({'top': I, 'bottom': I})
    D['ExactPixelEdge'] = obj({'terminal_edge': enum('upper', 'lower'), 'nominal': ref('Rational'), 'bounds': ref('ExactBounds')})
    D['ExactAxis'] = obj({'first_pixel': ref('Rational'), 'second_pixel': ref('Rational'), 'first_value': ref('Rational'), 'second_value': ref('Rational'), 'unit': enum('umol/min', 'nmol/min', 'mmol/min', 'uM/min', 'nM/min', 'per_min', 'per_s', 'umol/min/mg', 'nmol/min/mg'), 'slope': ref('Rational')})
    D['PixelResult'] = obj({'version': {'const': 'controlled_response_rate_pixels_v1'}, 'status': enum('measured', 'unreadable', 'ambiguous', 'unsupported', 'dependency_unavailable'), 'image_id': T, 'image_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}), 'original_image_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}), 'mapped_roi': null(ref('ImageLocator')), 'recipe': ref('BarSelection'), 'terminal_edge': enum('upper', 'lower'), 'image_size': null(obj({'width': I, 'height': I})), 'qualifying_runs': arr(ref('Run')), 'pixel_edge': null(ref('ExactPixelEdge')), 'axis': null(ref('ExactAxis')), 'native_ordinate': null(ref('Rational')), 'native_bounds': null(ref('ExactBounds')), 'bound_kind': {'const': 'conditional_digitization_not_confidence_interval'}, 'diagnostics': arr(ref('Diagnostic')), 'counter_version': {'const': 'controlled_response_bar_runs_v1'}})
    D['CanonicalDisplay'] = obj({'value': null(N), 'threshold': null(N), 'unit': null(enum('umol/min', 'uM/min', 'per_min', 'umol/min/mg')), 'relation': enum('eq', 'lt', 'le', 'gt', 'ge', 'none'), 'approximate': B, 'diagnostics': arr(ref('Diagnostic'))})
    D['NativeProjection'] = obj({'value': null(N), 'threshold': {'type': 'null'}, 'relation': enum('interval', 'none'), 'approximate': B, 'unit': null(enum('umol/min', 'nmol/min', 'mmol/min', 'uM/min', 'nM/min', 'per_min', 'per_s', 'umol/min/mg', 'nmol/min/mg')), 'status': enum('point', 'missing', 'ambiguous', 'conflicting', 'unsupported'), 'origin': {'const': 'graph_derived'}, 'digitization_interval': null(ref('FloatBounds'))})
    D['GraphMeasurementExtraction'] = obj({'selection': ref('GraphMeasurement'), 'candidates': {'type': 'array', 'maxItems': 0}, 'fragments': arr(ref('WitnessRecord')), 'unit': null(ref('GraphUnitRecord')), 'graph_witnesses': arr(ref('WitnessRecord')), 'reading_status': enum('graph_digitized', 'ambiguous', 'unreadable', 'conflicting', 'unsupported', 'dependency_unavailable'), 'source_observation_id': null(T), 'canonical_display': ref('CanonicalDisplay'), 'pixel_result': ref('PixelResult'), 'diagnostics': arr(ref('Diagnostic'))})
    schema = obj({'version': {'const': 'controlled_response_rate_figure_extraction_v1'}, 'selection': obj({'version': {'const': 'controlled_response_rate_figure_selection_v1'}, 'images': arr(ref('Image')), 'measurement': ref('GraphMeasurement')}), 'sources': arr(ref('SourceRecord')), 'images': arr(ref('ImageRecord')), 'axis_scale': ref('AxisScaleRecord'), 'axis_literals': obj({'first': ref('AxisLiteralRecord'), 'second': ref('AxisLiteralRecord'), 'unit': ref('AxisLiteralRecord')}), 'measurement': ref('GraphMeasurementExtraction'), 'operand_projection': ref('NativeProjection'), 'diagnostics': arr(ref('Diagnostic'))})
    schema.update({'$defs': D, '$schema': 'https://json-schema.org/draft/2020-12/schema'})
    return schema

def _sheet_schema():
    D = {}
    D['OwnerInputs'] = embed(owner.controlled_response_owner_arguments_schema(), 'Input_', D)
    D['Cell'] = obj({'value': null(N), 'lower': null(N), 'upper': null(N), 'relation': enum('none', 'eq', 'lt', 'le', 'gt', 'ge', 'interval'), 'approximate': B, 'unit': null(enum('umol/min', 'uM/min', 'per_min', 'umol/min/mg', '(umol/min)^2', '(uM/min)^2', '(per_min)^2', '(umol/min/mg)^2', '(umol/min)^-2', '(uM/min)^-2', '(per_min)^-2', '(umol/min/mg)^-2', 'dimensionless')), 'status': enum('available', 'bounded', 'partial', 'unavailable', 'unsupported', 'conflicting'), 'origin': enum('reported', 'graph_derived', 'synthetic', 'calculated'), 'unavailable_reason': null(arr(enum('missing_arm', 'unknown_unit', 'incompatible_unit_dimension', 'unknown_endpoint', 'different_endpoint', 'conflicting_endpoint', 'unknown_normalization', 'different_normalization', 'conflicting_normalization', 'unknown_subject_correspondence', 'different_subject_correspondence', 'conflicting_subject_correspondence', 'unknown_control_application', 'conflicting_control_application', 'unknown_protein_arrangement', 'conflicting_protein_arrangement', 'incompatible_control_arrangement', 'unknown_condition_correspondence', 'different_condition_correspondence', 'conflicting_condition_correspondence', 'condition_levels_not_distinct', 'missing_intended_factor', 'conflicting_control_reuse', 'unsupported_source_expression', 'ambiguous_source_literal', 'conflicting_source_literal', 'unavailable_source_dependency', 'unknown_covariance', 'estimated_covariance', 'nonpositive_variance_for_model', 'observation_model_unselected', 'unresolved_censoring_model', 'unresolved_reading_model', 'numeric_range_failure', 'uninformative_bounds', 'incomplete_active_covariance', 'unresolved_active_reading_model', 'conflicting_owner_context', 'conflicting_source_owner_binding'), minItems=1, uniqueItems=True)), 'formula_code': enum('condition_control_difference', 'four_arm_condition_difference', 'inverse_variance', 'linear_joint_covariance', 'signed_known_normal_profile', 'source_response', 'square_root_variance', 'tanh_half_signed_profile'), 'conditional_on': arr(enum('synthetic_fixture', 'approximate_source_reading', 'conditional_digitization', 'nonintended_conditions_different', 'nonintended_conditions_unknown', 'nonintended_conditions_conflicting', 'unknown_control_reuse', 'estimated_covariance', 'known_normal_source_means', 'shared_reference_assumption', 'owner_cancellation', 'canceled_reading_unavailable', 'canceled_unit_unknown', 'canceled_representation_difference', 'canceled_graph_reading', 'canceled_source_reading_conflict', 'canceled_reading_domain_conflict'), uniqueItems=True), 'bound_kind': enum('none', 'reported_limit', 'conditional_digitization', 'mixed'), 'bound_state': obj({'lower': enum('unknown', 'unbounded', 'available', 'numeric_range_failure', 'not_applicable'), 'upper': enum('unknown', 'unbounded', 'available', 'numeric_range_failure', 'not_applicable')})})
    D['ContrastDependencies'] = obj({'coefficient_order': {'const': ['protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0']}, 'role_coefficients': {'const': [1, -1, -1, 1]}, 'groups': arr(obj({'physical_observation_id': null(T), 'roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), minItems=1, maxItems=4, uniqueItems=True), 'coefficient': {'type': 'integer', 'minimum': -2, 'maximum': 2}, 'known_owner': B}), minItems=1, maxItems=4), 'active_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True), 'canceled_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True), 'scientific_reasons': arr(enum('missing_arm', 'unknown_unit', 'incompatible_unit_dimension', 'unknown_endpoint', 'different_endpoint', 'conflicting_endpoint', 'unknown_normalization', 'different_normalization', 'conflicting_normalization', 'unknown_subject_correspondence', 'different_subject_correspondence', 'conflicting_subject_correspondence', 'unknown_control_application', 'conflicting_control_application', 'unknown_protein_arrangement', 'conflicting_protein_arrangement', 'incompatible_control_arrangement', 'unknown_condition_correspondence', 'different_condition_correspondence', 'conflicting_condition_correspondence', 'condition_levels_not_distinct', 'missing_intended_factor', 'conflicting_control_reuse', 'unsupported_source_expression', 'ambiguous_source_literal', 'conflicting_source_literal', 'unavailable_source_dependency', 'unknown_covariance', 'estimated_covariance', 'nonpositive_variance_for_model', 'observation_model_unselected', 'unresolved_censoring_model', 'unresolved_reading_model', 'numeric_range_failure', 'uninformative_bounds', 'incomplete_active_covariance', 'unresolved_active_reading_model', 'conflicting_owner_context', 'conflicting_source_owner_binding'), uniqueItems=True), 'active_reading_reasons': arr(enum('missing_arm', 'unknown_unit', 'incompatible_unit_dimension', 'unknown_endpoint', 'different_endpoint', 'conflicting_endpoint', 'unknown_normalization', 'different_normalization', 'conflicting_normalization', 'unknown_subject_correspondence', 'different_subject_correspondence', 'conflicting_subject_correspondence', 'unknown_control_application', 'conflicting_control_application', 'unknown_protein_arrangement', 'conflicting_protein_arrangement', 'incompatible_control_arrangement', 'unknown_condition_correspondence', 'different_condition_correspondence', 'conflicting_condition_correspondence', 'condition_levels_not_distinct', 'missing_intended_factor', 'conflicting_control_reuse', 'unsupported_source_expression', 'ambiguous_source_literal', 'conflicting_source_literal', 'unavailable_source_dependency', 'unknown_covariance', 'estimated_covariance', 'nonpositive_variance_for_model', 'observation_model_unselected', 'unresolved_censoring_model', 'unresolved_reading_model', 'numeric_range_failure', 'uninformative_bounds', 'incomplete_active_covariance', 'unresolved_active_reading_model', 'conflicting_owner_context', 'conflicting_source_owner_binding'), uniqueItems=True), 'canceled_reading_qualifications': arr(enum('synthetic_fixture', 'approximate_source_reading', 'conditional_digitization', 'nonintended_conditions_different', 'nonintended_conditions_unknown', 'nonintended_conditions_conflicting', 'unknown_control_reuse', 'estimated_covariance', 'known_normal_source_means', 'shared_reference_assumption', 'owner_cancellation', 'canceled_reading_unavailable', 'canceled_unit_unknown', 'canceled_representation_difference', 'canceled_graph_reading', 'canceled_source_reading_conflict', 'canceled_reading_domain_conflict'), uniqueItems=True), 'reading_conflict_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True), 'required_covariance_owner_ids': arr(T, uniqueItems=True), 'provided_covariance_owner_ids': arr(T, uniqueItems=True), 'covariance_state': enum('unavailable', 'available', 'incomplete_active_coverage', 'scientific_blocked'), 'model_active_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True)})
    schema = obj({'version': {'const': 'controlled_response_owner_sheet_v2'}, 'primitive_order': {'const': ['protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0']}, 'inputs': ref('OwnerInputs'), 'cells': obj({'protein_condition1_response': ref('Cell'), 'empty_condition1_response': ref('Cell'), 'protein_condition0_response': ref('Cell'), 'empty_condition0_response': ref('Cell'), 'condition1_controlled_response': ref('Cell'), 'condition0_controlled_response': ref('Cell'), 'controlled_response_difference': ref('Cell'), 'contrast_variance': ref('Cell'), 'contrast_standard_uncertainty': ref('Cell'), 'contrast_precision': ref('Cell'), 'source_profile_log_ratio': ref('Cell'), 'source_signed_index': ref('Cell')}), 'contrast_dependencies': ref('ContrastDependencies')})
    schema.update({'$defs': D, '$schema': 'https://json-schema.org/draft/2020-12/schema'})
    return schema

def _extraction_core_schema():
    selection = shared._selection_core_schema()
    graph = _graph_schema()
    owner_inputs = owner.controlled_response_owner_arguments_schema()
    sheet = _sheet_schema()
    D = cp(selection['$defs'])
    D['GraphResult'] = embed(graph, 'G_', D)
    D['OwnerInputs'] = embed(owner_inputs, 'O_', D)
    D['OwnerSheet'] = embed(sheet, 'H_', D)
    T = {'type': 'string', 'minLength': 1}
    N = {'type': 'number'}
    I = {'type': 'integer', 'minimum': 0}
    B = {'type': 'boolean'}
    SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    rate = cp(D['G_GraphUnitRecord']['properties']['native_registry_unit']['anyOf'][0])
    canonical = cp(D['G_GraphUnitRecord']['properties']['canonical_unit']['anyOf'][0])
    for name in ('Rational', 'TextLocator', 'ImageLocator', 'WitnessRecord', 'SourceRecord', 'ImageRecord', 'CanonicalDisplay'):
        D[name] = cp(D['G_' + name])
    codes = sorted(set(['measurement_not_selected', 'source_literal_unreadable', 'source_literal_ambiguous', 'source_literal_conflicting', 'unsupported_complete_source_expression', 'source_numeric_range', 'numeric_projection_rounding', 'source_rate_unit_unknown', 'source_rate_unit_unsupported', 'source_defined_unit_definition_not_selected', 'unit_endpoint_correspondence_unknown', 'custom_unit_projection_unrepresentable', 'source_dependency_unavailable', 'source_text_encoding_unsupported', 'source_image_format_unsupported', 'source_image_decode_failed', 'source_uncertainty_meaning_conflict', 'source_uncertainty_piece_unsupported', 'source_uncertainty_unit_unknown', 'source_uncertainty_unit_conflicting', 'qualified_confidence_unsupported', 'source_confidence_sentence_stop_unsupported', 'unsupported_covariance_representation', 'source_json_duplicate_key', 'source_json_nonfinite', 'source_covariance_shape_invalid', 'source_covariance_asymmetric', 'source_covariance_not_psd', 'source_covariance_origin_invalid', 'covariance_owner_unresolved', 'covariance_owner_conflicting', 'covariance_shared_rows_conflicting', 'source_covariance_unit_unsupported', 'covariance_projection_numeric_range', 'covariance_projection_precision_invalid', 'variance_status_not_selected', 'source_variance_status_unknown', 'requested_source_variance_status_conflict', 'normal_model_not_selected', 'source_normal_model_unsupported', 'source_model_witness_unavailable', 'source_model_projection_rounding', 'synthetic_covariance_with_reported_operands'] + D['G_Diagnostic']['properties']['code']['enum'] + ['covariance_owner_subset', 'covariance_incomplete_owner_binding', 'covariance_owner_dimension_conflict', 'unresolved_active_representation_model', 'canceled_source_representation_difference', 'source_reading_nomination_identity', 'source_model_active_scope_unresolved', 'source_covariance_full_scope_invalid', 'source_covariance_projection_loss']))
    D['Diagnostic'] = obj({'code': enum(*codes), 'field': T, 'domain': enum('source_representation', 'source_binding', 'reader_capability', 'source_interpretation', 'dependency'), 'source_refs': arr(T, uniqueItems=True)})
    AD = arr(ref('Diagnostic'))
    for name in ('WitnessRecord', 'SourceRecord', 'CanonicalDisplay'):
        D[name]['properties']['diagnostics'] = cp(AD)
    interpret_values = sorted({v for name in ('Relationships', 'Arm') for p in D[name]['properties'].values() if p.get('type') == 'object' and 'value' in p.get('properties', {}) for v in p['properties']['value'].get('enum', [])} | {'known', 'estimated', 'sd', 'sem', 'ci', 'unspecified', 'unreported', 'same_as_response', 'explicit_unit', 'biological_preparations', 'technical_measurements', 'fit_to_averaged_curve', 'between_fitted_parameters', 'none', 'known_joint_normal_source_means'})
    D['InterpretationExtraction'] = obj({'selection': obj({'value': enum(*interpret_values), 'witnesses': arr(ref('Witness'))}), 'witnesses': arr(ref('WitnessRecord')), 'effective_value': enum(*interpret_values), 'diagnostics': AD})
    D['MeaningExtraction'] = obj({'selection': ref('Meaning'), 'witnesses': arr(ref('WitnessRecord')), 'canonical_witness': null(ref('WitnessRecord')), 'canonical_correspondence': ref('InterpretationExtraction'), 'resolved_state': enum('known', 'unknown', 'conflicting'), 'canonical_id': null(T), 'diagnostics': AD})
    D['NumberCandidate'] = obj({'selection': ref('NumberSelector'), 'witness': ref('WitnessRecord'), 'raw_expression': null(T), 'native_value': null(N), 'relation': enum('point', 'lt', 'le', 'gt', 'ge', 'unresolved'), 'approximate': null(B), 'source_locator': null(ref('TextLocator')), 'status': enum('parsed', 'unsupported', 'numeric_range', 'dependency_unavailable'), 'diagnostics': AD})
    D['DefinitionWitnesses'] = obj({k: ref('NumberCandidate') if k == 'amount' else ref('WitnessRecord') for k in ('bridge', 'clause', 'amount', 'amount_unit', 'time_unit', 'endpoint', 'endpoint_entity', 'definition_entity')})
    D['TextUnitRecord'] = obj({'selection': null(ref('UnitSelection')), 'witness': null(ref('WitnessRecord')), 'raw_unit': null(T), 'canonical_unit': null(canonical), 'exact_scale': null(ref('Rational')), 'native_registry_unit': null(rate), 'definition_witnesses': null(ref('DefinitionWitnesses')), 'status': enum('supported', 'unknown', 'unsupported', 'numeric_range', 'dependency_unavailable', 'endpoint_correspondence_unknown'), 'diagnostics': AD})
    D['UnitCarrier'] = {'oneOf': [obj({'kind': {'const': 'text'}, 'record': ref('TextUnitRecord')}), obj({'kind': {'const': 'graph'}, 'record': ref('G_GraphUnitRecord')})]}
    D['TextMeasurementExtraction'] = obj({'selection': null(ref('TextMeasurement')), 'candidates': arr(ref('NumberCandidate')), 'fragments': arr(ref('WitnessRecord')), 'unit': null(ref('TextUnitRecord')), 'graph_witnesses': arr(ref('WitnessRecord'), maxItems=0), 'reading_status': enum('not_selected', 'exact', 'ambiguous', 'unreadable', 'conflicting', 'unsupported', 'dependency_unavailable'), 'source_observation_id': null(T), 'canonical_display': ref('CanonicalDisplay'), 'pixel_result': {'type': 'null'}, 'diagnostics': AD})
    D['MeasurementExtraction'] = {'oneOf': [ref('TextMeasurementExtraction'), ref('G_GraphMeasurementExtraction')]}
    piece_states = enum('parsed', 'unsupported', 'numeric_range', 'dependency_unavailable')
    D['IntervalRecord'] = obj({'selection': ref('CISelector'), 'witness': ref('WitnessRecord'), 'raw_values': null(arr(T, minItems=2, maxItems=2)), 'values': null(arr(N, minItems=2, maxItems=2)), 'status': piece_states, 'diagnostics': AD})
    D['ConfidenceRecord'] = obj({'selection': ref('NativeTextWitness'), 'witness': ref('WitnessRecord'), 'value': null({'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}), 'status': piece_states, 'diagnostics': AD})
    D['NativeSavedWitness'] = obj({**cp(D['NativeTextWitness']['properties']), 'artifact_ref': T})
    D['NativeSavedNumberSelector'] = obj({**cp(D['NumberSelector']['properties']), 'witness': ref('NativeSavedWitness')})
    D['CountReading'] = obj({'selector': ref('NativeSavedNumberSelector'), 'raw_number': T, 'value': null({'type': 'integer'}), 'notation': enum('decimal_digits', 'english_cardinal', 'unsupported'), 'relation': enum('point', 'lt', 'le', 'gt', 'ge', 'unresolved'), 'approximate': null(B), 'status': enum('exact', 'qualified', 'not_positive', 'unsupported', 'range_or_alternatives'), 'unavailable_reason': null(enum('count_range_or_alternatives', 'unsupported_count_literal', 'positive_count_required', 'exact_count_qualified'))})
    D['CountRecord'] = obj({'selection': ref('NumberSelector'), 'witness': ref('WitnessRecord'), 'reading': null(ref('CountReading')), 'diagnostics': AD})
    D['UncertaintyCanonical'] = obj({'statistic': enum('sd', 'sem', 'ci', 'unspecified', 'unreported', 'unknown', 'conflicting'), 'magnitude': null({'type': 'number', 'minimum': 0}), 'interval': null(arr(N, minItems=2, maxItems=2)), 'confidence_level': null({'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}), 'count': null({'type': 'integer', 'minimum': 1}), 'repetition_basis': cp(D['Uncertainty']['properties']['repetition_basis']['properties']['value']), 'estimate_basis': cp(D['Uncertainty']['properties']['estimate_basis']['properties']['value'])})
    D['UncertaintyExtraction'] = obj({'selection': ref('Uncertainty'), 'meanings': obj({k: ref('InterpretationExtraction') for k in ('statistic', 'unit_relationship', 'repetition_basis', 'estimate_basis')}), 'magnitude': null(ref('NumberCandidate')), 'interval': null(ref('IntervalRecord')), 'unit': null(ref('TextUnitRecord')), 'effective_unit': null(ref('UnitCarrier')), 'confidence_level': null(ref('ConfidenceRecord')), 'count': null(ref('CountRecord')), 'canonical': ref('UncertaintyCanonical'), 'diagnostics': AD})
    roles = list(selection['properties']['arms']['properties'])
    D['ArmScience'] = obj({'selection': ref('Arm'), 'context': obj({k: null(ref('WitnessRecord')) for k in D['Arm']['properties']['context']['properties']}), 'protein_arrangement': ref('InterpretationExtraction'), 'meanings': obj({k: ref('MeaningExtraction') for k in ('endpoint', 'normalization', 'subject_construct', 'condition', 'physical_observation')}), 'intended_factor_level': null(ref('WitnessRecord'))})
    D['ArmExtraction'] = obj({**cp(D['ArmScience']['properties']), 'measurement': ref('MeasurementExtraction'), 'reported_uncertainty': ref('UncertaintyExtraction'), 'calculation_operand': null(ref('O_Arm')), 'graph_details': null(ref('GraphResult')), 'diagnostics': AD})
    D['RelationshipExtraction'] = obj({k: ref('MeaningExtraction') if k.endswith('_target') else null(ref('WitnessRecord')) if k == 'intended_factor' else ref('InterpretationExtraction') for k in D['Relationships']['properties']})
    D['CovarianceBindingExtraction'] = obj({'selection': null(ref('CovarianceBinding')), 'label_witness': null(ref('WitnessRecord')), 'owner_witness': null(ref('WitnessRecord')), 'correspondence': null(ref('InterpretationExtraction')), 'source_variable_index': null(I), 'resolved_owner_id': null(T), 'state': enum('known', 'unknown', 'conflicting'), 'diagnostics': AD})
    D['CovarianceSourceVariable'] = obj({'index': I, 'label': T, 'unit': T, 'description': T, **{k + '_witness': ref('WitnessRecord') for k in ('label', 'unit', 'description')}, 'native_registry_unit': null(rate), 'exact_scale': null(ref('Rational')), 'diagnostics': AD})
    D['SourceModel'] = obj({'origin': enum('reported', 'derived', 'synthetic'), 'variance_status': enum('known', 'estimated', 'unknown'), 'model_kind': enum('none', 'known_joint_normal_source_means')})
    D['OwnerProjection'] = obj({'physical_observation_id': T, 'source_variable_index': I, 'roles': arr(enum(*roles), minItems=1, uniqueItems=True), 'native_registry_unit': rate})
    D['CovarianceExtraction'] = obj({'selection': cp(selection['properties']['covariance']['anyOf'][0]), 'source_ref': T, 'artifact_ref': null(T), 'byte_sha256': null(SHA), 'raw_text': null(T), 'variables': arr(ref('CovarianceSourceVariable')), 'matrix_tokens': null(arr(arr(T))), 'exact_matrix': null(arr(arr(ref('Rational')))), 'source_model': null(ref('SourceModel')), 'bindings': obj({r: ref('CovarianceBindingExtraction') for r in roles}), 'provided_owner_projection': arr(ref('OwnerProjection'), maxItems=4), 'projected_exact_matrix': null(arr(arr(ref('Rational')))), 'calculation_covariance': null({'oneOf': [ref('O_RoleCovariance'), ref('O_OwnerCovariance')]}), 'source_validation': enum('valid', 'invalid', 'unassessed'), 'projection_state': enum('available', 'unavailable', 'numeric_range', 'precision_invalid', 'source_invalid', 'binding_unresolved', 'binding_conflicting', 'unsupported_format'), 'diagnostics': AD})
    D['ExactResponse'] = obj({'point': null(ref('Rational')), 'lower': null(ref('Rational')), 'upper': null(ref('Rational')), 'relation': enum('eq', 'lt', 'le', 'gt', 'ge', 'interval', 'none'), 'approximate': B, 'unit': null(canonical)})
    D['MeasurementReading'] = obj({'selection': null({'oneOf': [ref('TextMeasurement'), ref('GraphMeasurement')]}), 'extraction': ref('MeasurementExtraction'), 'operand_projection': obj({k: cp(D['O_Arm']['properties'][k]) for k in ('value', 'threshold', 'relation', 'approximate', 'unit', 'status', 'origin', 'digitization_interval')}), 'unit_semantics': null(ref('UnitCarrier')), 'exact_response': null(ref('ExactResponse')), 'source_observation_id': null(T), 'graph_details': null(ref('GraphResult'))})
    D['RetainedRepresentation'] = obj({'role': enum(*roles), 'source_reading_id': null(T), 'exact_domain': null(ref('ExactResponse'))})
    D['ReconciliationRecord'] = obj({'physical_observation_id': null(T), 'roles': arr(enum(*roles), minItems=1, uniqueItems=True), 'readings': arr(ref('RetainedRepresentation'), minItems=1), 'net_coefficient': {'type': 'integer'}, 'method': enum('single_reading', 'owner_cancellation', 'exact_equivalence', 'unresolved'), 'state': enum('single', 'exact_equivalent', 'canceled_readings_retained', 'unresolved_active_model', 'conflicting_active_domains', 'unresolved_science'), 'canonical_source_reading_id': null(T), 'qualifications': arr(enum('conditional_digitization_not_sampling', 'canceled_numeric_conflict', 'canceled_numeric_unavailable', 'canceled_unit_unknown', 'active_reconciliation_unimplemented'), uniqueItems=True), 'diagnostics': AD})
    D['RequestedModel'] = obj({k: ref('InterpretationExtraction') for k in ('variance_status', 'model_kind')})
    D['EffectiveModel'] = obj({'variance_status': enum('known', 'estimated', 'unknown'), 'model_kind': enum('none', 'known_joint_normal_source_means'), 'diagnostics': AD})
    D['DependencyRecord'] = obj({'reader_contract_version': {'const': 'controlled_response_source_extraction_v3'}, 'calculator_contract_version': {'const': 'controlled_response_owner_inputs_v2'}})
    root = obj({'version': {'const': 'controlled_response_source_extraction_v3'}, 'selection': ref('V3Selection'), 'sources': arr(ref('SourceRecord')), 'images': arr(ref('ImageRecord')), 'arms': obj({r: null(ref('ArmExtraction')) for r in roles}), 'relationships': ref('RelationshipExtraction'), 'covariance': null(ref('CovarianceExtraction')), 'requested_model': ref('RequestedModel'), 'effective_model': ref('EffectiveModel'), 'calculation_inputs': ref('OwnerInputs'), 'representation_reconciliations': arr(ref('ReconciliationRecord')), 'diagnostics': AD, 'implementation_dependencies': ref('DependencyRecord')})
    root.update({'$defs': D, '$schema': 'https://json-schema.org/draft/2020-12/schema'})
    return root

def _graph_request(selected, measurement):
    return {'version': 'controlled_response_rate_figure_selection_v1', 'images': cp(selected['images']), 'measurement': cp(measurement)}

def _read_graph(context, selected):

    def cached(reference, representation):
        key = (reference, representation)
        context._active()
        if key not in context.cache:
            shared._fail('unselected_source_read', 'source_ref')
        error = context.unavailable_errors.get(key)
        if error is not None:
            if isinstance(error, EOFError):
                raise OSError(errno.EIO, str(error)) from error
            raise error
        return context.read_source(reference, representation)
    result = graph_reader.read_controlled_response_rate_figure(_graph_request(context.arguments, selected), read_source=cached)
    return _graph_reading(context, selected, result)

def _graph_reading(context, selected, result):
    measurement = result['measurement']
    return shared._StageValue(context, {'selection': selected, 'extraction': measurement, 'operand_projection': result['operand_projection'], 'unit_semantics': {'kind': 'graph', 'record': measurement['unit']}, 'exact_response': shared._exact_response(measurement, graph=True), 'source_observation_id': measurement['source_observation_id'], 'graph_details': result})

def _saved_roster(selected, extraction):
    sources = {}
    artifacts = {}
    for source in extraction['sources']:
        key = (source['source_ref'], source['representation'])
        if key in sources:
            shared._fail('saved_duplicate_source', 'sources')
        sources[key] = source
        if source['state'] == 'available':
            if not source['artifact_ref'].strip() or not source['byte_sha256']:
                shared._fail('saved_source_identity_mismatch', 'sources')
            if source['artifact_ref'] in artifacts and artifacts[source['artifact_ref']] != source['byte_sha256']:
                shared._fail('artifact_content_conflict', 'sources')
            artifacts[source['artifact_ref']] = source['byte_sha256']
        elif source['artifact_ref'] is not None or source['byte_sha256'] is not None:
            shared._fail('saved_source_state_mismatch', 'sources')
    if list(sources) != shared._reference_closure(selected):
        shared._fail('saved_source_roster_mismatch', 'sources')
    _saved_images(selected['images'], extraction['images'], sources)
    return sources

def _saved_images(nominated, images, sources):
    if len(images) != len(nominated):
        shared._fail('saved_image_roster_mismatch', 'images')
    for spec, record in zip(nominated, images):
        if any((spec[k] != record[k] for k in ('image_id', 'source_ref', 'original_source_ref', 'mapping'))):
            shared._fail('saved_image_selection_mismatch', 'images')
        for prefix, ref_key in (('', 'source_ref'), ('original_', 'original_source_ref')):
            source = sources[spec[ref_key], 'original']
            if record[prefix + 'artifact_ref'] is not None and (record[prefix + 'artifact_ref'] != source['artifact_ref'] or record[prefix + 'byte_sha256'] != source['byte_sha256']):
                shared._fail('saved_image_source_mismatch', 'images')
        if not record['error'] and (not record['width'] or not record['height'] or record['frame_count'] != 1):
            shared._fail('saved_image_geometry_mismatch', 'images')

def _check_witness(record, nominated, sources, images, field):
    shared._saved_witness(record, nominated, sources, field)
    if record is None or record['canonical_locator'] is None or record['selection']['kind'] != 'image':
        return
    selected = record['selection']
    image = next((i for i in images if i['image_id'] == selected['image_id']))
    region = selected['region']
    if image['error'] or not (0 <= region[0] < region[2] <= image['width'] and 0 <= region[1] < region[3] <= image['height']):
        shared._fail('saved_image_geometry_mismatch', field)
    if image['mapping']:
        original = image['mapping']['original_region']
        region = [region[0] + original[0], region[1] + original[1], region[2] + original[0], region[3] + original[1]]
    wanted = {'kind': 'image', 'original_source_ref': image['original_source_ref'], 'original_artifact_ref': image['original_artifact_ref'], 'original_byte_sha256': image['original_byte_sha256'], 'region': region}
    if record['canonical_locator'] != wanted or record['artifact_ref'] != image['artifact_ref'] or record['byte_sha256'] != image['byte_sha256']:
        shared._fail('saved_image_identity_mismatch', field)

def _validate_text(selected, measurement, sources, images):
    if measurement['selection'] != selected:
        shared._fail('saved_selection_mismatch', 'measurement')
    if selected is None:
        expected = {'selection': None, 'candidates': [], 'fragments': [], 'unit': None, 'graph_witnesses': [], 'reading_status': 'not_selected', 'source_observation_id': None, 'canonical_display': shared._display(None, None), 'pixel_result': None}
        if any((measurement[k] != v for k, v in expected.items())):
            shared._fail('saved_measurement_projection_mismatch', 'measurement')
        return
    literal = selected['literal']
    if len(measurement['candidates']) != len(literal['candidates']) or len(measurement['fragments']) != len(literal['fragments']):
        shared._fail('saved_selection_mismatch', 'measurement')
    for record, nominated in zip(measurement['candidates'], literal['candidates']):
        shared._saved_number(record, nominated, sources, 'measurement.candidates')
    for record, nominated in zip(measurement['fragments'], literal['fragments']):
        _check_witness(record, nominated, sources, images, 'measurement.fragments')
    shared._saved_unit(measurement['unit'], selected['unit'], sources, 'measurement.unit')
    state = literal['status']
    if any((n['status'] == 'dependency_unavailable' for n in measurement['candidates'])) or any((w['canonical_locator'] is None for w in measurement['fragments'])):
        state = 'dependency_unavailable'
    elif state == 'exact' and measurement['candidates'][0]['status'] != 'parsed':
        state = 'unsupported'
    locators = [n['source_locator'] for n in measurement['candidates'] if n['source_locator'] is not None]
    locators += [w['canonical_locator'] for w in measurement['fragments'] if w['canonical_locator'] is not None]
    reading_id = shared.identity('controlled_source_token', locators[0] if len(locators) == 1 else locators) if state != 'dependency_unavailable' and locators else None
    if measurement['reading_status'] != state or measurement['source_observation_id'] != reading_id:
        shared._fail('saved_measurement_identity_mismatch', 'measurement')
    number = measurement['candidates'][0] if state == 'exact' else None
    expected_display = shared._display(number, measurement['unit']) if state == 'exact' else shared._display(None, None)
    if measurement['canonical_display'] != expected_display:
        shared._fail('saved_canonical_display_mismatch', 'measurement')

def _validate_measurement(selected, saved_measurement, *, source_records, image_records):
    """Closed text check; graph checks additionally retain the complete063 result."""
    sources = {(s['source_ref'], s['representation']): s for s in source_records}
    _validate_text(selected, saved_measurement, sources, image_records)
    return shared._reading_from_text(None, selected, saved_measurement)

def _validate_graph(selected, result, *, sources, images, request):
    Draft202012Validator(_graph_schema()).validate(result)
    if result['selection'] != _graph_request(request, selected) or result['version'] != 'controlled_response_rate_figure_extraction_v1':
        shared._fail('saved_graph_selection_mismatch', 'graph_details')
    closure = []
    for image in request['images']:
        closure.extend([(image['source_ref'], 'original'), (image['original_source_ref'], 'original')])
    closure += [(w['source_ref'], w['representation']) for w in graph_reader._witnesses(selected) if w['kind'] == 'text']
    closure = list(dict.fromkeys(closure))
    actual_closure = [(s['source_ref'], s['representation']) for s in result['sources']]
    if len(actual_closure) != len(set(actual_closure)) or set(actual_closure) != set(closure):
        shared._fail('saved_graph_source_roster_mismatch', 'graph_details.sources')
    for source in result['sources']:
        original = sources[source['source_ref'], source['representation']]
        if any((source[k] != original[k] for k in ('artifact_ref', 'byte_sha256', 'state'))):
            shared._fail('saved_graph_source_identity_mismatch', 'graph_details.sources')
    _saved_images(request['images'], result['images'], sources)
    actual_images = result['images']
    for name, literal in result['axis_literals'].items():
        nominated = selected['axis'][name] if name == 'unit' else selected['axis'][name]['tick']
        if literal['selection'] != nominated:
            shared._fail('saved_graph_literal_selection_mismatch', 'axis.' + name)
        for part in ('candidates', 'fragments'):
            if len(literal[part]) != len(nominated[part]):
                shared._fail('saved_graph_literal_selection_mismatch', 'axis.' + name)
            for saved, witness in zip(literal[part], nominated[part]):
                _check_witness(saved, witness, sources, actual_images, 'axis.' + name)
        available = all((w['canonical_locator'] is not None for part in ('candidates', 'fragments') for w in literal[part]))
        if literal['status'] == 'parsed':
            if nominated['status'] != 'exact' or not available or literal['raw_literal'] != nominated['candidates'][0]['quote']:
                shared._fail('saved_graph_literal_mismatch', 'axis.' + name)
            witness = nominated['candidates'][0]
            qualification = 'source_text_literal' if witness['kind'] == 'text' else 'episode_image_transcription'
            if literal['qualification'] != qualification:
                shared._fail('saved_graph_literal_mismatch', 'axis.' + name)
            if name != 'unit':
                token = literal['raw_literal'].strip().replace('−', '-')
                if not graph_reader._LITERAL.fullmatch(literal['raw_literal'].strip()) or literal['exact_value'] != shared._rational(Fraction(token)):
                    shared._fail('saved_graph_tick_mismatch', 'axis.' + name)
        elif not available and literal['status'] != 'dependency_unavailable' and (nominated['status'] == 'exact'):
            shared._fail('saved_graph_literal_availability_mismatch', 'axis.' + name)
    scale = result['axis_scale']
    if scale['selection'] != selected['axis']['scale'] or len(scale['witnesses']) != len(scale['selection']['witnesses']):
        shared._fail('saved_graph_scale_mismatch', 'axis.scale')
    for saved, witness in zip(scale['witnesses'], scale['selection']['witnesses']):
        _check_witness(saved, witness, sources, actual_images, 'axis.scale')
    if scale['support'] in ('literal_source_text', 'episode_image_interpretation'):
        expected_support = 'literal_source_text' if scale['selection']['basis'] == 'source_text_literal' else 'episode_image_interpretation'
        if scale['support'] != expected_support:
            shared._fail('saved_graph_scale_mismatch', 'axis.scale')
        if scale['selection']['status'] != 'known' or scale['effective_kind'] != scale['selection']['kind'] or any((w['canonical_locator'] is None for w in scale['witnesses'])):
            shared._fail('saved_graph_scale_mismatch', 'axis.scale')
        if scale['support'] == 'literal_source_text' and any((graph_reader._SCALE_PHRASES.get(w['selection']['quote'].strip().lower()) != scale['effective_kind'] for w in scale['witnesses'])):
            shared._fail('saved_graph_scale_literal_mismatch', 'axis.scale')
    unit = result['measurement']['unit']
    literal = result['axis_literals']['unit']
    if unit['selection'] != selected['axis']['unit'] or unit['raw_unit'] != literal['raw_literal']:
        shared._fail('saved_graph_unit_mismatch', 'axis.unit')
    if unit['status'] == 'supported':
        parsed = shared._plain_unit(unit['raw_unit'])
        if parsed is None or parsed != (unit['canonical_unit'], shared._fraction(unit['exact_scale'])):
            shared._fail('saved_graph_unit_mismatch', 'axis.unit')
        native = next((k for k in shared.RATE_UNITS if shared._plain_unit(k) == parsed), None)
        if native != unit['native_registry_unit'] or unit['witness'] != literal['candidates'][0]:
            shared._fail('saved_graph_unit_mismatch', 'axis.unit')
    pixels = result['measurement']['pixel_result']
    spec = next((i for i in actual_images if i['image_id'] == selected['image_id']))
    if pixels['recipe'] != selected['bar_selection'] or pixels['terminal_edge'] != selected['terminal_edge'] or pixels['image_id'] != selected['image_id']:
        shared._fail('saved_graph_recipe_mismatch', 'pixels')
    if pixels['image_sha256'] != spec['byte_sha256'] or pixels['original_image_sha256'] != spec['original_byte_sha256']:
        shared._fail('saved_graph_image_identity_mismatch', 'pixels')
    recipe, edge = (selected['bar_selection'], selected['terminal_edge'])
    roi = recipe['roi']
    runs = pixels['qualifying_runs']
    for i, run in enumerate(runs):
        if not roi['top'] <= run['top'] < run['bottom'] <= roi['bottom'] or run['bottom'] - run['top'] < recipe['minimum_run_rows'] or (i and runs[i - 1]['bottom'] >= run['top']):
            shared._fail('saved_graph_runs_mismatch', 'pixels.qualifying_runs')
    if pixels['mapped_roi']:
        region = [roi[k] for k in ('left', 'top', 'right', 'bottom')]
        if spec['mapping']:
            ox, oy = spec['mapping']['original_region'][:2]
            region = [region[0] + ox, region[1] + oy, region[2] + ox, region[3] + oy]
        wanted = {'kind': 'image', 'original_source_ref': spec['original_source_ref'], 'original_artifact_ref': spec['original_artifact_ref'], 'original_byte_sha256': spec['original_byte_sha256'], 'region': region}
        if pixels['mapped_roi'] != wanted or pixels['image_size'] != {'width': spec['width'], 'height': spec['height']}:
            shared._fail('saved_graph_mapping_mismatch', 'pixels')
    if pixels['pixel_edge'] is not None:
        if len(runs) != 1:
            shared._fail('saved_graph_edge_mismatch', 'pixels')
        run = runs[0]
        clipped = run['top'] == roi['top'] if edge == 'upper' else run['bottom'] == roi['bottom']
        if clipped:
            shared._fail('saved_graph_terminal_clipping_mismatch', 'pixels')
        tolerance = Fraction(recipe['edge_tolerance_pixels'])
        if edge == 'upper':
            point, lo, hi = (Fraction(run['top']) + Fraction(1, 2), Fraction(run['top']) - tolerance, Fraction(run['top'] + 1) + tolerance)
        else:
            point, lo, hi = (Fraction(run['bottom']) - Fraction(1, 2), Fraction(run['bottom'] - 1) - tolerance, Fraction(run['bottom']) + tolerance)
        wanted = {'terminal_edge': edge, 'nominal': shared._rational(point), 'bounds': {'lower': shared._rational(lo), 'upper': shared._rational(hi)}}
        if pixels['pixel_edge'] != wanted:
            shared._fail('saved_graph_edge_mismatch', 'pixels')
    if pixels['status'] == 'measured':
        if pixels['pixel_edge'] is None or scale['effective_kind'] != 'linear' or scale['support'] not in ('literal_source_text', 'episode_image_interpretation') or (unit['status'] != 'supported'):
            shared._fail('saved_graph_calibration_mismatch', 'pixels')
        p1, p2 = (Fraction(selected['axis'][k]['pixel']) for k in ('first', 'second'))
        v1, v2 = (shared._fraction(result['axis_literals'][k]['exact_value']) for k in ('first', 'second'))
        if p1 == p2 or v1 == v2 or (not 0 <= lo <= hi < spec['height']):
            shared._fail('saved_graph_calibration_mismatch', 'pixels')
        slope = (v2 - v1) / (p2 - p1)
        axis = {'first_pixel': shared._rational(p1), 'second_pixel': shared._rational(p2), 'first_value': shared._rational(v1), 'second_value': shared._rational(v2), 'unit': unit['native_registry_unit'], 'slope': shared._rational(slope)}
        ordinate = lambda p: v1 + (p - p1) * slope
        lower, upper = sorted((ordinate(lo), ordinate(hi)))
        if pixels['axis'] != axis or pixels['native_ordinate'] != shared._rational(ordinate(point)) or pixels['native_bounds'] != {'lower': shared._rational(lower), 'upper': shared._rational(upper)}:
            shared._fail('saved_graph_ordinate_mismatch', 'pixels')
    measurement, projection = (result['measurement'], result['operand_projection'])
    states = []
    if any((s['state'] == 'unavailable' for s in result['sources'])) or any((w['authentication'] == 'unavailable' for w in scale['witnesses'])):
        states.append('dependency_unavailable')
    states += [literal['status'] for literal in result['axis_literals'].values() if literal['status'] != 'parsed']
    if selected['axis']['scale']['status'] == 'conflicting':
        states.append('conflicting')
    states.append('graph_digitized' if pixels['status'] == 'measured' else pixels['status'])
    expected_status = next((status for status in ('dependency_unavailable', 'conflicting', 'ambiguous', 'unreadable', 'unsupported', 'graph_digitized') if status in states))
    if expected_status == 'graph_digitized':
        try:
            graph_reader._finite_float(shared._fraction(pixels['native_ordinate']))
            for side, direction in (('lower', -1), ('upper', 1)):
                graph_reader._outward(shared._fraction(pixels['native_bounds'][side]), direction)
        except OverflowError:
            expected_status = 'unsupported'
    if measurement['reading_status'] != expected_status:
        shared._fail('saved_graph_status_mismatch', 'measurement')
    expected_projection_status = 'point' if expected_status == 'graph_digitized' else 'missing' if expected_status in ('dependency_unavailable', 'unreadable') else expected_status
    if projection['status'] != expected_projection_status or projection['approximate'] is not True or projection['unit'] != unit['native_registry_unit']:
        shared._fail('saved_graph_projection_mismatch', 'operand_projection')
    ordered_literals = [result['axis_literals'][name] for name in ('first', 'second', 'unit')]
    fragments = [w for literal in ordered_literals for w in literal['fragments']]
    witnesses = [w for literal in ordered_literals for part in ('candidates', 'fragments') for w in literal[part]] + scale['witnesses']
    if measurement['selection'] != selected or measurement['fragments'] != fragments or measurement['graph_witnesses'] != witnesses or measurement['candidates']:
        shared._fail('saved_graph_measurement_mismatch', 'measurement')
    if projection['status'] == 'point':
        if pixels['status'] != 'measured' or measurement['reading_status'] != 'graph_digitized':
            shared._fail('saved_graph_projection_mismatch', 'measurement')
        native = shared._fraction(pixels['native_ordinate'])
        lower, upper = (shared._fraction(pixels['native_bounds'][s]) for s in ('lower', 'upper'))
        value = graph_reader._finite_float(native)
        interval = {'lower': min(graph_reader._outward(lower, -1), value), 'upper': max(graph_reader._outward(upper, 1), value)}
        expected = {'value': value, 'threshold': None, 'relation': 'interval', 'approximate': True, 'unit': unit['native_registry_unit'], 'status': 'point', 'origin': 'graph_derived', 'digitization_interval': interval}
        if projection != expected:
            shared._fail('saved_graph_projection_mismatch', 'operand_projection')
        identity_record = {'version': result['version'], 'selection': result['selection'], 'images': result['images'], 'literals': result['axis_literals'], 'scale': scale, 'unit': unit, 'pixels': pixels}
        expected_id = 'controlled_response_graph_' + hashlib.sha256(json.dumps(identity_record, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()
        if measurement['source_observation_id'] != expected_id:
            shared._fail('saved_graph_identity_mismatch', 'measurement.source_observation_id')
        display = {'value': None, 'threshold': None, 'unit': unit['canonical_unit'], 'relation': 'none', 'approximate': True, 'diagnostics': []}
        try:
            display['value'] = graph_reader._finite_float(native * shared._fraction(unit['exact_scale']))
        except OverflowError:
            display['diagnostics'] = [graph_reader._diagnostic('graph_canonical_display_range', 'measurement.canonical_display')]
        else:
            display['relation'] = 'eq'
        if measurement['canonical_display'] != display:
            shared._fail('saved_graph_display_mismatch', 'measurement.canonical_display')
    elif any((projection[k] is not None for k in ('value', 'threshold', 'digitization_interval'))) or projection['relation'] != 'none' or measurement['source_observation_id'] is not None:
        shared._fail('saved_graph_projection_mismatch', 'operand_projection')
    return _graph_reading(None, selected, result)


@lru_cache(maxsize=1)
def _schemas():
    schemas = {}
    S = shared._selection_core_schema()
    ROLES = list(S['properties']['arms']['properties'])
    D = S['$defs']
    D['ReadingSelector'] = obj({'role': enum(*ROLES), 'reading_key': null(T)})
    D['Assignment'] = obj({r: null(T) for r in ROLES})
    D['ScopeRelation'] = obj({'value': enum('same', 'explicit_compatible', 'not_applicable', 'unknown', 'conflicting'), 'witnesses': arr(ref('Witness'))})
    D['Authority'] = obj({'status': enum('source_explicit', 'not_established', 'conflicting'), 'reading': null(ref('ReadingSelector')), 'witnesses': arr(ref('Witness'))})
    D['ReconciliationNomination'] = obj({'role': enum(*ROLES), 'relationship': obj({'value': enum('same_reported_mean_and_display', 'exact_duplicate', 'alternative_estimates', 'unknown', 'conflicting'), 'witnesses': arr(ref('Witness'))}), 'authority': ref('Authority'), 'normalization': ref('ScopeRelation'), 'calibration': ref('ScopeRelation'), 'revision': ref('ScopeRelation'), 'model_scope': ref('ScopeRelation')})
    S['properties']['companion_readings'] = arr(obj({'reading_key': T, 'primary_role': enum(*ROLES), 'reading': ref('Arm')}))
    S['properties']['joint_reading_assignments'] = arr(obj({'assignment': ref('Assignment'), 'admissibility': obj({'value': enum('compatible', 'unknown', 'conflicting'), 'witnesses': arr(ref('Witness'))})}))
    D['JointScope'] = obj({'assignment_index': I, 'normalization': ref('ScopeRelation'), 'calibration': ref('ScopeRelation'), 'revision': ref('ScopeRelation'), 'covariance_scope': ref('ScopeRelation'), 'model_scope': ref('ScopeRelation'), 'covariance_selection': cp(S['properties']['covariance']), 'variance_status': cp(S['properties']['variance_status']), 'model_kind': cp(S['properties']['model_kind'])})
    D['LocalPairNomination'] = obj({'pair_key': T, 'condition': enum('condition1', 'condition0'), 'protein': ref('ReadingSelector'), 'control': ref('ReadingSelector'), 'admissibility': obj({'value': enum('compatible', 'unknown', 'conflicting'), 'witnesses': arr(ref('Witness'))}), 'scope': ref('ScopeRelation'), 'covariance_selection': cp(S['properties']['covariance']), 'variance_status': cp(S['properties']['variance_status'])})
    for name, shape in [('joint_scopes', arr(ref('JointScope'))), ('reading_reconciliations', arr(ref('ReconciliationNomination'))), ('local_pair_assignments', arr(ref('LocalPairNomination')))]:
        S['properties'][name] = shape
    S['required'] += ['companion_readings', 'joint_reading_assignments', 'joint_scopes', 'reading_reconciliations', 'local_pair_assignments']
    schemas['SELECTION_SCHEMA_V3_007'] = S
    E = _extraction_core_schema()
    ED = E['$defs']
    ED['CovarianceExtraction']['properties']['raw_text'] = null({'type': 'string'})
    ED['V3Selection'] = embed(S, 'V3S_', ED)
    ED['ReadingSelector'] = cp(D['ReadingSelector'])
    ED['Authority'] = cp(D['Authority'])
    ED['ScopeRelation'] = cp(D['ScopeRelation'])
    ED['RetainedRepresentation']['properties']['reading_key'] = null(T)
    ED['RetainedRepresentation']['required'].append('reading_key')
    ED['Assignment'] = cp(D['Assignment'])
    ED['ScopeRelationExtraction'] = obj({'selection': cp(D['ScopeRelation']), 'witnesses': arr(ref('WitnessRecord')), 'effective_value': cp(D['ScopeRelation']['properties']['value'])})
    E['properties']['local_pair_extractions'] = arr(obj({'pair_key': T, 'admissibility': obj({'selection': cp(D['LocalPairNomination']['properties']['admissibility']), 'witnesses': arr(ref('WitnessRecord')), 'effective_value': enum('compatible', 'unknown', 'conflicting')}), 'scope': ref('ScopeRelationExtraction'), 'variance_status': ref('InterpretationExtraction')}))
    ED['CompanionExtraction'] = obj({'reading_key': T, 'primary_role': enum(*ROLES), 'reading': ref('ArmExtraction')})
    ED['ReconciliationDecision'] = obj({'role': enum(*ROLES), 'selection': cp(D['ReconciliationNomination']), 'witnesses': arr(ref('WitnessRecord')), 'reading_selectors': arr(ref('ReadingSelector'), minItems=1), 'scientific_correspondence': enum('same', 'unknown', 'conflicting'), 'method': enum('single', 'exact_equivalence', 'explicit_reported_mean_display', 'unresolved'), 'state': enum('ready', 'unknown_authority', 'conflicting_authority', 'different_domains', 'scientific_conflict', 'unsupported_group_projection', 'unimplemented_model'), 'selected_reading': null(ref('ReadingSelector')), 'normalized_domain_checks': arr(obj({'reading': ref('ReadingSelector'), 'relation_to_selected': enum('equal', 'contains', 'disjoint', 'unknown')})), 'model_state': enum('original_source_model', 'none', 'unresolved'), 'qualifications': arr(enum('conditional_digitization_not_sampling', 'source_explicit_reported_mean', 'same_representation_not_replication', 'mixed_original_origins_retained', 'unsupported_group_origin', 'unavailable_group_identity', 'source_scope_unresolved'), uniqueItems=True)})
    ED['ConditionalInput'] = obj({'reading_assignment': ref('Assignment'), 'scope_index': I, 'source_covariance': null(ref('CovarianceExtraction')), 'requested_model': ref('RequestedModel'), 'effective_model': ref('EffectiveModel'), 'calculation_inputs': ref('OwnerInputs')})
    E['properties']['calculation_inputs'] = null(ref('OwnerInputs'))
    for name, shape in [('companion_extractions', arr(ref('CompanionExtraction'))), ('projection_status', enum('ready', 'unresolved_active_reconciliation')), ('final_projection_basis', null(obj({'reading_assignment': ref('Assignment'), 'covariance_scope': enum('base', 'joint'), 'scope_index': null(I), 'reconciled_roles': arr(enum(*ROLES), uniqueItems=True)}))), ('reconciliation_decisions', arr(ref('ReconciliationDecision'))), ('joint_scope_extractions', arr(obj({'assignment_index': I, 'witnesses': arr(ref('WitnessRecord')), 'effective_admissibility': enum('compatible', 'unknown', 'conflicting'), 'source_covariance': null(ref('CovarianceExtraction')), 'requested_model': ref('RequestedModel'), 'effective_model': ref('EffectiveModel')}))), ('alternative_inputs', arr(ref('ConditionalInput'))), ('partial_calculation_inputs', null(ref('OwnerInputs'))), ('partial_projection_state', enum('not_required', 'ready', 'unsupported_origin_projection', 'unavailable_group_identity')), ('component_local_inputs', ref('LocalInputs'))]:
        E['properties'][name] = shape
    E['required'] += ['companion_extractions', 'local_pair_extractions', 'projection_status', 'final_projection_basis', 'reconciliation_decisions', 'joint_scope_extractions', 'alternative_inputs', 'partial_calculation_inputs', 'partial_projection_state', 'component_local_inputs']
    LD = cp(_extraction_core_schema()['$defs'])
    LD['CovarianceExtraction']['properties']['raw_text'] = null({'type': 'string'})
    LD['ReadingSelector'] = cp(D['ReadingSelector'])
    LD['CovarianceDocument'] = obj({k: cp(LD['CovarianceExtraction']['properties'][k]) for k in ['source_ref', 'artifact_ref', 'byte_sha256', 'raw_text', 'variables', 'matrix_tokens', 'exact_matrix', 'source_model', 'source_validation', 'diagnostics']})
    LD['CovarianceDocument']['properties']['document_state'] = enum('available', 'unavailable', 'unsupported_format')
    LD['CovarianceDocument']['required'].append('document_state')
    LD['LocalReading'] = obj({'reading': ref('ReadingSelector'), 'arm': null(ref('O_Arm')), 'reported_uncertainty': ref('UncertaintyCanonical'), 'source_kind': null(cp(D['Arm']['properties']['source_kind'])), 'measurement_method': enum('text', 'graph', 'not_selected')})
    LD['LocalReading']['allOf'] = [{'if': {'properties': {'arm': {'type': 'null'}}}, 'then': {'properties': {'source_kind': {'type': 'null'}, 'measurement_method': {'const': 'not_selected'}}}, 'else': {'properties': {'source_kind': cp(D['Arm']['properties']['source_kind'])}}}]
    LD['LocalPair'] = obj({'pair_key': T, 'condition': enum('condition1', 'condition0'), 'protein': ref('ReadingSelector'), 'control': ref('ReadingSelector'), 'target': cp(owner.controlled_response_owner_arguments_schema()['$defs']['Relationships']['properties']['condition1_target']), 'control_application': enum('matched_condition_control', 'shared_reference_assumption', 'unknown', 'conflicting'), 'joint_admissibility': enum('compatible', 'unknown', 'conflicting'), 'scope_state': enum('same', 'explicit_compatible', 'not_applicable', 'unknown', 'conflicting'), 'covariance_index': null(I), 'protein_binding': null(ref('CovarianceBindingExtraction')), 'control_binding': null(ref('CovarianceBindingExtraction')), 'variance_status': enum('known', 'estimated', 'unknown')})
    L = obj({'version': {'const': 'controlled_response_local_inputs_v1'}, 'readings': arr(ref('LocalReading')), 'pairs': arr(ref('LocalPair')), 'source_covariances': arr(ref('CovarianceDocument'))})
    L.update({'$defs': LD, '$schema': 'https://json-schema.org/draft/2020-12/schema'})
    ED['LocalInputs'] = embed(L, 'Local_', ED)
    ED['ScopeKey'] = obj({'kind': enum('base', 'joint', 'local'), 'index': null(I)})
    ED['CovarianceDocument'] = embed({'$defs': LD, **ref('CovarianceDocument')}, 'Document_', ED)
    E['properties']['covariance_document_scopes'] = arr(obj({'scope': ref('ScopeKey'), 'document': null(ref('CovarianceDocument'))}))
    E['required'].append('covariance_document_scopes')
    ED['BoundCovarianceScope'] = obj({'scope': ref('ScopeKey'), 'document': null(ref('CovarianceDocument')), 'bindings': arr(obj({'reading': ref('ReadingSelector'), 'binding': ref('CovarianceBindingExtraction')})), 'whole_projection': null(ref('CovarianceExtraction'))})
    schemas['EXTRACTION_SCHEMA_V3_007'] = E
    schemas['LOCAL_INPUT_SCHEMA_007'] = L
    RD = cp(LD)
    RD['Dependency'] = obj({'scientific_readings': arr(ref('ReadingSelector'), uniqueItems=True), 'numeric_readings': arr(ref('ReadingSelector'), uniqueItems=True), 'uncertainty_readings': arr(ref('ReadingSelector'), uniqueItems=True), 'covariance_index': null(I), 'covariance_owner_ids': arr(T, uniqueItems=True), 'source_variable_indices': arr(I, uniqueItems=True), 'model_readings': arr(ref('ReadingSelector'), uniqueItems=True), 'unresolved_readings': arr(ref('ReadingSelector'), uniqueItems=True), 'numeric_fields': arr(obj({'reading': ref('ReadingSelector'), 'fields': arr(enum('value', 'threshold', 'relation', 'approximate', 'unit', 'status', 'origin', 'digitization_interval', 'digitization_interval_presence'), uniqueItems=True)})), 'full_source_covariance_required': B})
    RD['LocalCell'] = cp(RD['H_Cell'])
    RD['LocalCell']['properties']['origin'] = null(cp(RD['LocalCell']['properties']['origin']))
    RD['LocalCell']['properties']['unavailable_reason']['anyOf'][0]['items']['enum'] += ['unknown_joint_applicability', 'conflicting_joint_applicability', 'unknown_covariance_owner', 'source_full_covariance_invalid', 'source_covariance_unassessed', 'local_covariance_binding_unknown', 'local_covariance_binding_conflicting', 'local_scope_unresolved']
    RD['LocalCell']['properties']['formula_code']['enum'] += ['local_joint_covariance', 'local_square_root_variance']
    RD['LocalPopulationInputs'] = embed(L, 'Parsed_', RD)
    R = obj({'version': {'const': 'controlled_response_local_sheet_v1'}, 'inputs': ref('LocalPopulationInputs'), 'raw': arr(obj({'reading': ref('ReadingSelector'), 'cell': ref('LocalCell'), 'reported_uncertainty': ref('UncertaintyCanonical'), 'dependencies': ref('Dependency')})), 'pairs': arr(obj({'pair_key': T, 'difference': ref('LocalCell'), 'variance': ref('LocalCell'), 'standard_uncertainty': ref('LocalCell'), 'dependencies': obj({k: ref('Dependency') for k in ['difference', 'variance', 'standard_uncertainty']})})), 'full_covariance_checks': arr(obj({'covariance_index': I, 'source_validation': enum('valid', 'invalid', 'unassessed'), 'document_state': enum('available', 'unavailable', 'unsupported_format')}))})
    R.update({'$defs': RD, '$schema': 'https://json-schema.org/draft/2020-12/schema'})
    schemas['LOCAL_OUTPUT_SCHEMA_007'] = R
    PD = cp(ED)
    PD['LocalSheet'] = embed(R, 'Result_', PD)
    components = list(_sheet_schema()['properties']['cells']['properties'])
    PD['ComponentDependency'] = cp(RD['Dependency'])
    P = obj({'version': {'const': 'controlled_response_conditional_population_v3'}, 'projection_status': enum('ready', 'unresolved_active_reconciliation'), 'final_sheet': null(ref('OwnerSheet')), 'partial_sheet': null(ref('OwnerSheet')), 'local_sheet': ref('LocalSheet'), 'unresolved_roles': arr(enum(*ROLES), uniqueItems=True), 'alternatives': arr(obj({'reading_assignment': ref('Assignment'), 'scope_index': I, 'sheet': ref('OwnerSheet')})), 'unaffected_components': arr(obj({'component': T, 'cell': ref('H_Cell'), 'dependencies': ref('ComponentDependency')})), 'conditional_components': arr(obj({'assignment_index': I, 'component': enum(*components), 'cell': ref('H_Cell'), 'dependencies': ref('ComponentDependency')}))})
    P.update({'$defs': PD, '$schema': 'https://json-schema.org/draft/2020-12/schema'})
    schemas['POPULATION_SCHEMA_V3_007'] = P
    FD = cp(RD)
    FD['SemanticContext'] = obj({'endpoint_id': null(T), 'normalization_id': null(T), 'subject_construct_ids': arr(T, uniqueItems=True), 'condition_ids': arr(T, uniqueItems=True), 'owner_ids': arr(T, uniqueItems=True), 'owner_state': enum('known', 'unknown', 'conflicting'), 'control_application': null(enum('matched_condition_control', 'shared_reference_assumption', 'unknown', 'conflicting')), 'condition_control_applications': obj({k: null(enum('matched_condition_control', 'shared_reference_assumption', 'unknown', 'conflicting')) for k in ['condition1', 'condition0']}), 'control_reuse': null(enum('distinct_observations', 'same_reference_with_stated_invariance', 'unknown', 'conflicting')), 'protein_arrangements': arr(enum('protein_present', 'protein_free_control', 'empty_vector_control', 'other_specified', 'unknown', 'conflicting'), uniqueItems=True), 'variance_status': enum('known', 'estimated', 'unknown'), 'model_kind': enum('none', 'known_joint_normal_source_means'), 'representation_state': enum('single', 'reconciled', 'unresolved', 'conditional'), 'source_kinds': arr(enum('primary_source', 'retained_extraction', 'synthetic_fixture'), uniqueItems=True), 'original_origins': arr(enum('reported', 'graph_derived', 'synthetic'), uniqueItems=True), 'measurement_methods': arr(enum('text', 'graph', 'not_selected'), uniqueItems=True), **{k + '_state': enum('known', 'unknown', 'conflicting') for k in ['endpoint', 'normalization', 'subject_construct', 'condition']}})
    FD['JointScopeWitness'] = obj({'witness_ref': dict(type='string', format='reference', **{'x-reference-namespace': 'reference'}), 'authentication': enum('exact_utf8_byte_span', 'image_bytes_and_geometry_only', 'unavailable'), 'attribution': enum('literal_source_record', 'investigating_episode_interpretation')})
    for name, selected_values, effective_values in [('JointScopeRelation', ['same', 'explicit_compatible', 'not_applicable', 'unknown', 'conflicting'], ['same', 'explicit_compatible', 'not_applicable', 'unknown', 'conflicting']), ('JointAdmissibility', ['compatible', 'unknown', 'conflicting'], ['compatible', 'unknown', 'conflicting']), ('JointVarianceRequest', ['known', 'estimated', 'unknown'], ['known', 'estimated', 'unknown']), ('JointModelRequest', ['none', 'known_joint_normal_source_means'], ['none', 'known_joint_normal_source_means', 'unknown'])]:
        FD[name] = obj({'selected_value': enum(*selected_values), 'effective_value': enum(*effective_values), 'witnesses': arr(ref('JointScopeWitness'))})
    FD['JointScopeContext'] = obj({'reading_assignment': cp(D['Assignment']), 'assignment_admissibility': ref('JointAdmissibility'), 'effective_admissibility': enum('compatible', 'unknown', 'conflicting'), **{name: ref('JointScopeRelation') for name in ['normalization', 'calibration', 'revision', 'covariance_scope', 'model_scope']}, 'requested_model': obj({'variance_status': ref('JointVarianceRequest'), 'model_kind': ref('JointModelRequest')}), 'effective_model': ref('EffectiveModel'), 'covariance_context': null(obj({'source_ref': dict(type='string', format='reference', **{'x-reference-namespace': 'source'}), 'source_validation': cp(ED['CovarianceExtraction']['properties']['source_validation']), 'projection_state': cp(ED['CovarianceExtraction']['properties']['projection_state']), 'source_model': null(ref('SourceModel'))}))})
    FD['NumericLocation'] = {'oneOf': [obj({'kind': {'const': 'utf8_span'}, 'source_ref': T, 'start': I, 'end': {'type': 'integer', 'minimum': 1}}), obj({'kind': {'const': 'image_region'}, 'source_ref': T, 'region': ref('Box')}), obj({'kind': {'const': 'unresolved'}, 'source_ref': T})]}
    FD['NativeReading'] = obj({k: cp(LD['O_Arm']['properties'][k]) for k in ['value', 'threshold', 'relation', 'approximate', 'unit', 'status', 'origin', 'digitization_interval', 'source_observation_id']})
    F = obj({'version': {'const': 'literature_controlled_response_component_fact_v3'}, 'sheet_ref': dict(type='string', format='reference', **{'x-reference-namespace': 'source'}), 'component_key': T, 'kind': enum('native_raw', 'local_difference', 'local_variance', 'local_standard_uncertainty', 'final', 'conditional'), 'component': enum(*components, 'local_difference', 'local_variance', 'local_standard_uncertainty'), 'reading': null(ref('ReadingSelector')), 'reading_assignment': null(cp(D['Assignment'])), 'pair_key': null(T), 'cell': ref('LocalCell'), 'native_reading': null(ref('NativeReading')), 'reported_uncertainty': null(ref('UncertaintyCanonical')), 'reported_uncertainty_unit': cp(FD['TextUnitRecord']['properties']['canonical_unit']), 'numeric_locations': arr(ref('NumericLocation')), 'context': ref('SemanticContext'), 'dependencies': ref('Dependency'), 'joint_scope_context': null(ref('JointScopeContext'))})
    F.update({'$defs': FD, '$schema': 'https://json-schema.org/draft/2020-12/schema'})
    schemas['NATIVE_FACT_SCHEMA_V3_007'] = F
    Return = {'type': 'array', 'items': {k: cp(v) for k, v in F.items() if k not in ('$defs', '$schema')}, '$defs': cp(FD), '$schema': 'https://json-schema.org/draft/2020-12/schema', 'x-source': 'literature_controlled_response_component_cells'}
    schemas['NATIVE_RETURN_SCHEMA_V3_007'] = Return
    return schemas

def controlled_response_v3_arguments_schema():
    return cp(_schemas()['SELECTION_SCHEMA_V3_007'])

def _extraction_schema():
    return cp(_schemas()['EXTRACTION_SCHEMA_V3_007'])

def validate_controlled_response_v3_selection(arguments):
    selected = shared._validate_selection(arguments, controlled_response_v3_arguments_schema())
    roster = {(role, None): arm for role, arm in selected['arms'].items()}
    keys = set()
    for row in selected['companion_readings']:
        key = row['reading_key']
        if key in keys:
            shared._fail('duplicate_companion_reading_key', 'companion_readings')
        keys.add(key)
        roster[row['primary_role'], key] = row['reading']

    def selector(value, field):
        if (value['role'], value['reading_key']) not in roster:
            shared._fail('controlled_reading_selector_unresolved', field)
    for arm in roster.values():
        if arm and arm['measurement'] and (arm['measurement']['kind'] == 'linear_bar'):
            graph_reader._validate(_graph_request(selected, arm['measurement']))
    maps = set()
    for row in selected['joint_reading_assignments']:
        key = tuple((row['assignment'][r] for r in shared.PRIMITIVE_ORDER))
        if key in maps:
            shared._fail('duplicate_joint_reading_assignment', 'joint_reading_assignments')
        maps.add(key)
        for role, reading_key in row['assignment'].items():
            selector({'role': role, 'reading_key': reading_key}, 'joint_reading_assignments')
    indices = [r['assignment_index'] for r in selected['joint_scopes']]
    if indices != list(range(len(selected['joint_reading_assignments']))):
        shared._fail('joint_scope_roster_mismatch', 'joint_scopes')
    roles = set()
    for row in selected['reading_reconciliations']:
        role = row['role']
        if role in roles:
            shared._fail('duplicate_reconciliation_role', 'reading_reconciliations')
        roles.add(role)
        auth = row['authority']
        if auth['status'] == 'source_explicit':
            if auth['reading'] is None or auth['reading']['role'] != role:
                shared._fail('authority_reading_role_mismatch', 'reading_reconciliations')
            selector(auth['reading'], 'reading_reconciliations.authority.reading')
        elif auth['reading'] is not None:
            shared._fail('authority_reading_without_designation', 'reading_reconciliations')
        minimum = 2 if auth['status'] == 'conflicting' else 1 if auth['status'] == 'source_explicit' else 0
        if len({shared._nomination_key(w) for w in auth['witnesses']}) < minimum:
            shared._fail('interpretation_witness_required', 'reading_reconciliations.authority')
    needed = {r['primary_role'] for r in selected['companion_readings']}
    if not needed <= roles:
        shared._fail('reading_reconciliation_missing', 'reading_reconciliations')
    pairs = set()
    for row in selected['local_pair_assignments']:
        if row['pair_key'] in pairs:
            shared._fail('duplicate_local_pair_key', 'local_pair_assignments')
        pairs.add(row['pair_key'])
        for name, prefix in (('protein', 'protein_'), ('control', 'empty_')):
            value = row[name]
            selector(value, 'local_pair_assignments.' + name)
            if value['role'] != prefix + row['condition']:
                shared._fail('local_pair_role_mismatch', 'local_pair_assignments.' + name)
    return selected

def _selector(role, key=None):
    return {'role': role, 'reading_key': key}

def read_controlled_response_v3_inputs(arguments, *, read_source):
    """Read every actual nomination in one authenticated shared source context."""
    validate_controlled_response_v3_selection(arguments)
    with shared.open_controlled_response_sources(arguments, read_source=read_source) as context:
        readings, arms, companions = ({}, {}, [])
        nominations = [(_selector(r), context.arguments['arms'][r]) for r in shared.PRIMITIVE_ORDER]
        nominations += [(_selector(row['primary_role'], row['reading_key']), row['reading']) for row in context.arguments['companion_readings']]
        for selector, selected in nominations:
            arm = None
            if selected is not None:
                science = shared.read_controlled_response_arm_science(context, selected, reading_selector=selector)
                endpoint = science['meanings']['endpoint']
                measurement = shared.read_controlled_response_graph_measurement(context, selector, endpoint=endpoint) if selected['measurement'] and selected['measurement']['kind'] == 'linear_bar' else shared.read_controlled_response_text_measurement(context, selected['measurement'], endpoint=endpoint, reading_selector=selector)
                arm = shared.finish_controlled_response_arm(context, science, measurement=measurement, reading_selector=selector)
            readings[selector['role'], selector['reading_key']] = arm
            if selector['reading_key'] is None:
                arms[selector['role']] = arm
            else:
                companions.append((selector, arm))
        scopes = []
        scope_selectors = [({'kind': 'base', 'index': None}, [_selector(r) for r in shared.PRIMITIVE_ORDER])]
        scope_selectors += [({'kind': 'joint', 'index': i}, [_selector(r, row['assignment'][r]) for r in shared.PRIMITIVE_ORDER]) for i, row in enumerate(context.arguments['joint_reading_assignments'])]
        scope_selectors += [({'kind': 'local', 'index': i}, [row['protein'], row['control']]) for i, row in enumerate(context.arguments['local_pair_assignments'])]
        for scope, selectors in scope_selectors:
            document = shared.read_controlled_response_covariance_document(context, scope)
            scopes.append(shared.bind_controlled_response_covariance_scope(context, scope, document, readings=[(s, readings[s['role'], s['reading_key']]) for s in selectors]))
        return shared.finish_controlled_response_inputs(context, arms=arms, companion_arms=companions, covariance_scopes=scopes)

def _relation(context, nomination, field):
    witnesses = [context.witness(w, field) for w in nomination['witnesses']]
    value = nomination['value']
    if any((w['canonical_locator'] is None for w in witnesses)):
        value = 'unknown'
    return {'selection': cp(nomination), 'witnesses': witnesses, 'effective_value': value}

def _same_science(members):
    if not members or any((a is None for _, a in members)):
        return 'unknown'
    arms = [a for _, a in members]
    if any((v['resolved_state'] == 'conflicting' for a in arms for v in a['meanings'].values())):
        return 'conflicting'
    if any((v['resolved_state'] != 'known' for a in arms for v in a['meanings'].values())):
        return 'unknown'
    first = arms[0]
    for arm in arms[1:]:
        if any((arm['meanings'][m]['canonical_id'] != first['meanings'][m]['canonical_id'] for m in shared._MEANINGS)):
            return 'conflicting'
        if arm['protein_arrangement']['effective_value'] != first['protein_arrangement']['effective_value']:
            return 'conflicting'
        if arm['context'] != first['context']:
            return 'unknown'
    return 'same'

def _domain(arm):
    return shared._exact_response(arm['measurement'], graph=bool(arm['graph_details'])) if arm else None

def _domain_relation(selected, other):
    if selected is None or other is None or selected['unit'] is None or (other['unit'] != selected['unit']):
        return 'unknown'
    if selected == other:
        return 'equal'
    if shared._response_domains_disjoint(selected, other):
        return 'disjoint'
    if selected['relation'] == 'eq' and selected['point'] is not None and other['lower'] and other['upper']:
        point = shared._fraction(selected['point'])
        if shared._fraction(other['lower']) <= point <= shared._fraction(other['upper']):
            return 'contains'
    return 'unknown'

def _reconcile(context, nomination, members):
    field = 'reading_reconciliations.' + nomination['role']
    relationship = _relation(context, nomination['relationship'], field + '.relationship')
    relations = {k: _relation(context, nomination[k], field + '.' + k) for k in ('normalization', 'calibration', 'revision', 'model_scope')}
    auth = nomination['authority']
    auth_witnesses = [context.witness(w, field + '.authority') for w in auth['witnesses']]
    science = _same_science(members)
    authority = auth['status'] if all((w['canonical_locator'] is not None for w in auth_witnesses)) else 'not_established'
    state, method, chosen = ('unknown_authority', 'unresolved', None)
    if science != 'same':
        state = 'scientific_conflict' if science == 'conflicting' else 'unsupported_group_projection'
    elif authority == 'conflicting' or relationship['effective_value'] == 'conflicting':
        state = 'conflicting_authority'
    elif any((r['effective_value'] in ('unknown', 'conflicting') for k, r in relations.items() if k != 'model_scope')):
        state = 'unsupported_group_projection'
    else:
        domains = [_domain(a) for s, a in members]
        if len(members) == 1:
            state, method, chosen = ('ready', 'single', members[0][0])
        elif relationship['effective_value'] == 'exact_duplicate' and domains[0] is not None and all((d == domains[0] for d in domains)):
            state, method, chosen = ('ready', 'exact_equivalence', members[0][0])
        elif authority == 'source_explicit' and relationship['effective_value'] == 'same_reported_mean_and_display':
            selected = next((a for s, a in members if s == auth['reading']), None)
            domain = _domain(selected)
            checks = [_domain_relation(domain, d) for d in domains]
            if domain and domain['relation'] == 'eq' and (not domain['approximate']) and all((c in ('equal', 'contains') for c in checks)):
                state, method, chosen = ('ready', 'explicit_reported_mean_display', cp(auth['reading']))
            elif 'disjoint' in checks:
                state = 'different_domains'
        elif any((shared._response_domains_disjoint(a, b) for i, a in enumerate(domains) if a for b in domains[:i] if b)):
            state = 'different_domains'
    selected_domain = _domain(next((a for s, a in members if s == chosen), None))
    qualifications = ['same_representation_not_replication'] if len(members) > 1 else []
    if any((a and a['graph_details'] for s, a in members)):
        qualifications.append('conditional_digitization_not_sampling')
    if method == 'explicit_reported_mean_display':
        qualifications.append('source_explicit_reported_mean')
    origins = {a['calculation_operand']['origin'] for s, a in members if a}
    if len(origins) > 1:
        qualifications.append('mixed_original_origins_retained')
    model_state = 'original_source_model' if state == 'ready' and relations['model_scope']['effective_value'] in ('same', 'explicit_compatible') else 'none' if relations['model_scope']['effective_value'] == 'not_applicable' else 'unresolved'
    return {'role': nomination['role'], 'selection': cp(nomination), 'witnesses': [w for r in [relationship, *relations.values()] for w in r['witnesses']] + auth_witnesses, 'reading_selectors': [cp(s) for s, a in members], 'scientific_correspondence': science, 'method': method, 'state': state, 'selected_reading': cp(chosen), 'normalized_domain_checks': [{'reading': cp(s), 'relation_to_selected': _domain_relation(selected_domain, _domain(a))} for s, a in members], 'model_state': model_state, 'qualifications': sorted(set(qualifications))}

def _requested(context, variance, model, field):
    return {'variance_status': shared._interpretation(context, variance, field + '.variance_status'), 'model_kind': shared._interpretation(context, model, field + '.model_kind')}

def _owner_projection(arms, relationships, covariance, requested, *, variance_scope=True, model_scope=True):
    effective = shared._effective_model(requested, covariance if variance_scope else None, arms)
    if not model_scope:
        effective['model_kind'] = 'none'
    parsed = shared._calculation_inputs(arms, relationships, covariance, effective)
    owner.validate_controlled_response_owner_inputs(parsed)
    return (parsed, effective)

def _group_mask(role, members):
    """A real retained unresolved group, never an invented union origin."""
    from gene_annotation_episode.episodic_workflow.root.a105.domain import identity
    actual = [a for s, a in members if a]
    if not actual or _same_science(members) != 'same':
        return (None, 'unavailable_group_identity')
    operands = [a['calculation_operand'] for a in actual]
    if len({a['origin'] for a in operands}) != 1:
        return (None, 'unsupported_origin_projection')
    if any((a['source_observation_id'] is None for a in operands)):
        return (None, 'unavailable_group_identity')
    dimensions = {shared.RATE_UNITS[a['unit']][0] for a in operands if a['unit']}
    if len(dimensions) != 1 or any((a['unit'] is None for a in operands)):
        return (None, 'unavailable_group_identity')
    payload = {'primary_role': role, 'primary_reading_id': operands[0]['source_observation_id'], 'companions': [{'reading_key': s['reading_key'], 'reading_id': a['calculation_operand']['source_observation_id']} for s, a in members[1:]], 'scientific_owner_id': operands[0]['physical_observation_id'], 'members': [{'source_kind': a['selection']['source_kind'], 'measurement_method': 'graph' if a['graph_details'] else 'text' if a['selection']['measurement'] else 'not_selected'} for a in actual]}
    mask = cp(operands[0])
    mask.update(value=None, threshold=None, relation='none', status='ambiguous', digitization_interval=None, approximate=any((a['approximate'] for a in operands)), source_observation_id=identity('controlled_active_reading_group_v3', payload))
    return (mask, 'ready')

def _finish_v3(context, *, arms, companion_arms, covariance_scopes):
    selected = context.arguments
    relationships = cp(context.relationships)
    roster = {(r, None): arms[r] for r in shared.PRIMITIVE_ORDER}
    roster.update({(s['role'], s['reading_key']): a for s, a in companion_arms})
    scopes = {(s['scope']['kind'], s['scope']['index']): s for s in covariance_scopes}
    base_covariance = cp(scopes['base', None]['whole_projection'])
    requested = _requested(context, selected['variance_status'], selected['model_kind'], 'model')
    decisions = []
    assignment = {r: None for r in shared.PRIMITIVE_ORDER}
    unresolved = []
    groups = owner._groups([arms[r]['calculation_operand'] if arms[r] else None for r in shared.PRIMITIVE_ORDER])
    canceled = {r for g in groups if g['known_owner'] and g['coefficient'] == 0 for r in g['roles']}
    for nomination in selected['reading_reconciliations']:
        role = nomination['role']
        members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
        decision = _reconcile(context, nomination, members)
        decisions.append(decision)
        if decision['state'] == 'ready':
            assignment[role] = decision['selected_reading']['reading_key']
        elif role not in canceled or _same_science(members) != 'same':
            unresolved.append(role)
    joint_rows, alternatives = ([], [])
    for i, nomination in enumerate(selected['joint_reading_assignments']):
        spec = selected['joint_scopes'][i]
        admissibility = _relation(context, nomination['admissibility'], 'joint_reading_assignments')
        relations = {k: _relation(context, spec[k], 'joint_scopes.' + k) for k in ('normalization', 'calibration', 'revision', 'covariance_scope', 'model_scope')}
        compatible = admissibility['effective_value']
        for k in ('normalization', 'calibration', 'revision'):
            if relations[k]['effective_value'] == 'conflicting':
                compatible = 'conflicting'
            elif relations[k]['effective_value'] == 'unknown' and compatible != 'conflicting':
                compatible = 'unknown'
        covariance = cp(scopes['joint', i]['whole_projection'])
        request = _requested(context, spec['variance_status'], spec['model_kind'], 'joint_scopes')
        joint_arms = {r: roster[r, nomination['assignment'][r]] for r in shared.PRIMITIVE_ORDER}
        parsed, effective = _owner_projection(joint_arms, relationships, covariance, request, variance_scope=relations['covariance_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'), model_scope=relations['model_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'))
        joint_rows.append({'assignment_index': i, 'witnesses': admissibility['witnesses'] + [w for rel in relations.values() for w in rel['witnesses']], 'effective_admissibility': compatible, 'source_covariance': covariance, 'requested_model': request, 'effective_model': effective})
        if compatible == 'compatible':
            alternatives.append({'reading_assignment': cp(nomination['assignment']), 'scope_index': i, 'source_covariance': covariance, 'requested_model': request, 'effective_model': effective, 'calculation_inputs': parsed})
    projection, basis = (None, None)
    effective = {'variance_status': 'unknown', 'model_kind': 'none', 'diagnostics': []}
    if not unresolved:
        matching = next((a for a in alternatives if a['reading_assignment'] == assignment), None)
        if all((v is None for v in assignment.values())):
            projection, effective = _owner_projection(arms, relationships, base_covariance, requested, model_scope=all((d['model_state'] == 'original_source_model' for d in decisions if d['state'] == 'ready')))
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'base', 'scope_index': None, 'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        elif matching:
            projection, effective = (cp(matching['calculation_inputs']), cp(matching['effective_model']))
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'joint', 'scope_index': matching['scope_index'], 'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        else:
            unresolved = [r for r, key in assignment.items() if key is not None]
    partial, partial_state = (None, 'not_required')
    if projection is None:
        masked_arms = {r: cp(dict(a)) if a is not None else None for r, a in arms.items()}
        partial_state = 'ready'
        for role in unresolved:
            members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
            mask, state = _group_mask(role, members)
            if state != 'ready':
                partial_state = state
                break
            masked_arms[role]['calculation_operand'] = mask
        if partial_state == 'ready':
            partial, unused_effective = _owner_projection(masked_arms, relationships, base_covariance, requested, model_scope=False)
    unknown_uncertainty = {'statistic': 'unknown', 'magnitude': None, 'interval': None, 'confidence_level': None, 'count': None, 'repetition_basis': 'unknown', 'estimate_basis': 'unknown'}
    local_readings = []
    for (role, key), arm in roster.items():
        local_readings.append({'reading': _selector(role, key), 'arm': cp(arm['calculation_operand']) if arm else None, 'reported_uncertainty': cp(arm['reported_uncertainty']['canonical']) if arm else cp(unknown_uncertainty), 'source_kind': arm['selection']['source_kind'] if arm else None, 'measurement_method': 'graph' if arm and arm['graph_details'] else 'text' if arm and arm['selection']['measurement'] else 'not_selected'})
    documents, source_indices = ([], {})
    for scope in covariance_scopes:
        document = scope['document']
        if document is not None and document['source_ref'] not in source_indices:
            source_indices[document['source_ref']] = len(documents)
            documents.append(cp(document))
    pairs, pair_extractions = ([], [])
    for i, pair in enumerate(selected['local_pair_assignments']):
        scope = scopes['local', i]
        document = scope['document']
        admissibility = _relation(context, pair['admissibility'], 'local_pair_assignments.admissibility')
        scope_relation = _relation(context, pair['scope'], 'local_pair_assignments.scope')
        bindings = [b['binding'] for b in scope['bindings']]
        variance = shared._interpretation(context, pair['variance_status'], 'local_pair_assignments.variance_status')
        pair_extractions.append({'pair_key': pair['pair_key'], 'admissibility': admissibility, 'scope': scope_relation, 'variance_status': variance})
        pairs.append({'pair_key': pair['pair_key'], 'condition': pair['condition'], 'protein': cp(pair['protein']), 'control': cp(pair['control']), 'target': shared._relationships_inputs(relationships)[pair['condition'] + '_target'], 'control_application': relationships[pair['condition'] + '_control_application']['effective_value'], 'joint_admissibility': admissibility['effective_value'], 'scope_state': scope_relation['effective_value'], 'covariance_index': source_indices[document['source_ref']] if document else None, 'protein_binding': cp(bindings[0]) if document else None, 'control_binding': cp(bindings[1]) if document else None, 'variance_status': variance['effective_value']})
    result = {'version': 'controlled_response_source_extraction_v3', 'selection': cp(selected), 'sources': cp(context.roster), 'images': cp(context.images), 'arms': {r: cp(dict(a)) if a else None for r, a in arms.items()}, 'relationships': relationships, 'covariance': base_covariance, 'requested_model': requested, 'effective_model': effective, 'calculation_inputs': projection, 'representation_reconciliations': shared._representations(arms), 'diagnostics': [], 'implementation_dependencies': {'reader_contract_version': 'controlled_response_source_extraction_v3', 'calculator_contract_version': 'controlled_response_owner_inputs_v2'}, 'companion_extractions': [{'reading_key': s['reading_key'], 'primary_role': s['role'], 'reading': cp(dict(a))} for s, a in companion_arms], 'projection_status': 'ready' if projection is not None else 'unresolved_active_reconciliation', 'final_projection_basis': basis, 'reconciliation_decisions': decisions, 'joint_scope_extractions': joint_rows, 'alternative_inputs': alternatives, 'partial_calculation_inputs': partial, 'partial_projection_state': partial_state, 'local_pair_extractions': pair_extractions, 'component_local_inputs': {'version': 'controlled_response_local_inputs_v1', 'readings': local_readings, 'pairs': pairs, 'source_covariances': documents}, 'covariance_document_scopes': [{'scope': cp(s['scope']), 'document': cp(s['document'])} for s in covariance_scopes]}
    for record in result['representation_reconciliations']:
        for reading in record['readings']:
            reading['reading_key'] = None
    result['diagnostics'] = shared._unique_diagnostics(result, stable=True)
    Draft202012Validator(_extraction_schema()).validate(result)
    json.dumps(result, allow_nan=False)
    return cp(result)

def validate_controlled_response_v3_extraction(arguments, extraction):

    def check(selector, selected, measurement, *, source_records, image_records):
        if selected and selected['kind'] == 'linear_bar':
            arm = extraction['arms'][selector['role']] if selector['reading_key'] is None else next((row['reading'] for row in extraction['companion_extractions'] if row['primary_role'] == selector['role'] and row['reading_key'] == selector['reading_key']))
            if arm['graph_details'] is None or arm['graph_details']['measurement'] != measurement:
                shared._fail('saved_graph_measurement_mismatch', 'measurement')
            return _validate_graph(selected, arm['graph_details'], sources={(s['source_ref'], s['representation']): s for s in source_records}, images=image_records, request=arguments)
        return _validate_measurement(selected, measurement, source_records=source_records, image_records=image_records)
    return shared.validate_controlled_response_saved_science(arguments, extraction, measurement_checks=check)
__all__ = ['controlled_response_v3_arguments_schema', 'validate_controlled_response_v3_selection', 'read_controlled_response_v3_inputs', 'validate_controlled_response_v3_extraction']
