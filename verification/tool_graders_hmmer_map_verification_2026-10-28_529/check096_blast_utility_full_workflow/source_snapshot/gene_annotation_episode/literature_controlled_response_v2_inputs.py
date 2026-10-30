"""Full source-bound A105 controlled-response extraction.

Text science is shared with v1. Actual signed graph reading is delegated to063;
owner covariance and actual068 parsed inputs retain source scope. No sheet,
model, acquisition, runtime action or annotation-credit calculation occurs here.
"""
from __future__ import annotations

from copy import deepcopy as cp
from fractions import Fraction
import errno
import hashlib
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from . import literature_controlled_response_inputs as shared
from . import literature_controlled_response_figure_inputs as graph_reader
from .literature_controlled_response_owner_calculations import (
    controlled_response_owner_arguments_schema, validate_controlled_response_owner_inputs,
)
from .literature_experimental_contracts import ExperimentalContractError

obj, ref, null = shared.obj, shared.ref, shared.nullable
T, N, I, B = shared.TEXT, {"type": "number"}, shared.OFFSET, {"type": "boolean"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}

def arr(value, **kw):
    return {"type": "array", "items": value, **kw}

def enum(*values):
    return {"enum": list(values)}

def embed(schema, prefix, target):
    def rename(value):
        if isinstance(value, dict):
            return {k: ("#/$defs/" + prefix + v[8:] if k == "$ref" and v.startswith("#/$defs/") else rename(v)) for k,v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return value
    for key,val in schema.get("$defs", {}).items():
        target[prefix + key] = rename(val)
    return rename({k:v for k,v in schema.items() if k not in ("$defs", "$schema")})


def controlled_response_v2_arguments_schema():
    schema = shared.controlled_response_arguments_schema()
    schema["properties"]["version"] = {"const": "controlled_response_source_selection_v2"}
    axis_scale = obj({"status": enum("known", "unknown", "conflicting"),
        "kind": null(enum("linear", "logarithmic", "nonlinear")),
        "basis": enum("source_text_literal", "image_episode_interpretation", "unresolved"),
        "witnesses": arr(ref("Witness"))})
    axis_scale["allOf"] = [{"if": {"properties": {"status": {"const": "known"}}},
        "then": {"properties": {"kind": enum("linear", "logarithmic", "nonlinear"),
            "basis": enum("source_text_literal", "image_episode_interpretation"), "witnesses": {"minItems": 1}}},
        "else": {"properties": {"kind": {"type": "null"}, "basis": {"const": "unresolved"}}}}]
    schema["$defs"]["AxisScale"] = axis_scale
    measurement = schema["$defs"]["GraphMeasurement"]
    measurement["properties"]["axis"]["properties"]["scale"] = ref("AxisScale")
    measurement["properties"]["axis"]["required"].append("scale")
    measurement["properties"]["terminal_edge"] = enum("upper", "lower")
    measurement["required"].append("terminal_edge")
    return schema


def _graph_schema():
    D = cp(controlled_response_v2_arguments_schema()["$defs"])
    D['Rational'] = obj({
        'numerator': {'type': 'string', 'pattern': '^-?(0|[1-9][0-9]*)$'},
        'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})
    D['Diagnostic'] = obj({
        'code': enum('graph_image_unavailable', 'graph_image_unsupported', 'graph_nonopaque_roi', 'graph_scale_unknown', 'graph_scale_conflicting', 'graph_scale_unsupported', 'graph_scale_literal_unsupported', 'graph_tick_ambiguous', 'graph_tick_conflicting', 'graph_tick_unreadable', 'graph_tick_literal_unsupported', 'graph_tick_literal_numeric_range', 'graph_tick_projection_rounded', 'graph_unit_ambiguous', 'graph_unit_conflicting', 'graph_unit_unreadable', 'graph_unit_unknown', 'graph_unit_unsupported', 'graph_unit_defined_bridge_unselected', 'graph_no_bar_pixels', 'graph_ambiguous_bar_runs', 'graph_terminal_edge_clipped', 'graph_axis_degenerate', 'graph_pixel_bounds_outside_image', 'graph_numerical_model_range', 'graph_canonical_display_range', 'graph_image_label_interpretation', 'graph_axis_scale_interpretation', 'graph_conditional_digitization', 'graph_ordinate_projection_rounded', 'graph_opposite_edge_clipped', 'graph_axis_multiplier_unsupported'),
        'field': T,
        'domain': enum('source_representation', 'source_binding', 'reader_capability', 'source_interpretation', 'dependency'),
        'source_refs': arr(T)})
    D['TextLocator'] = obj({
        'kind': {'const': 'text'},
        'source_ref': T,
        'artifact_ref': T,
        'byte_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
        'start': I,
        'end': {'type': 'integer', 'minimum': 1}})
    D['ImageLocator'] = obj({
        'kind': {'const': 'image'},
        'original_source_ref': T,
        'original_artifact_ref': T,
        'original_byte_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
        'region': ref('Box')})
    D['WitnessRecord'] = obj({
        'selection': ref('Witness'),
        'artifact_ref': null(T),
        'byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}),
        'canonical_locator': null({'oneOf': [ref('TextLocator'), ref('ImageLocator')]}),
        'authentication': enum('exact_utf8_byte_span', 'image_bytes_and_geometry_only', 'unavailable'),
        'attribution': enum('literal_source_record', 'investigating_episode_interpretation'),
        'diagnostics': arr(ref('Diagnostic'))})
    D['SourceRecord'] = obj({
        'source_ref': T,
        'representation': enum('original', 'text'),
        'artifact_ref': null(T),
        'byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}),
        'state': enum('available', 'unavailable'),
        'diagnostics': arr(ref('Diagnostic'))})
    D['DependencyError'] = obj({
        'code': T,
        'field': T})
    D['ImageRecord'] = obj({
        'image_id': T,
        'source_ref': T,
        'artifact_ref': null(T),
        'byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}),
        'original_source_ref': T,
        'original_artifact_ref': null(T),
        'original_byte_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}),
        'actual_format': null(T),
        'actual_mode': null(T),
        'width': null(I),
        'height': null(I),
        'frame_count': null(I),
        'mapping': null(obj({
            'original_region': ref('Box'),
            'colour_conversion': enum('preserve', 'rgb')})),
        'pillow_version': T,
        'error': null(ref('DependencyError'))})
    D['AxisScaleRecord'] = obj({
        'selection': ref('AxisScale'),
        'witnesses': arr(ref('WitnessRecord')),
        'effective_kind': enum('linear', 'logarithmic', 'nonlinear', 'unknown', 'conflicting'),
        'support': enum('literal_source_text', 'episode_image_interpretation', 'unavailable', 'unresolved'),
        'diagnostics': arr(ref('Diagnostic'))})
    D['AxisLiteralRecord'] = obj({
        'selection': ref('AxisLiteral'),
        'candidates': arr(ref('WitnessRecord')),
        'fragments': arr(ref('WitnessRecord')),
        'raw_literal': null(T),
        'exact_value': null(ref('Rational')),
        'qualification': enum('source_text_literal', 'episode_image_transcription', 'unresolved'),
        'status': enum('parsed', 'ambiguous', 'unreadable', 'conflicting', 'unsupported', 'dependency_unavailable'),
        'diagnostics': arr(ref('Diagnostic'))})
    D['GraphUnitRecord'] = obj({
        'selection': ref('AxisLiteral'),
        'witness': null(ref('WitnessRecord')),
        'raw_unit': null(T),
        'canonical_unit': null(enum('umol/min', 'uM/min', 'per_min', 'umol/min/mg')),
        'exact_scale': null(ref('Rational')),
        'native_registry_unit': null(enum('umol/min', 'nmol/min', 'mmol/min', 'uM/min', 'nM/min', 'per_min', 'per_s', 'umol/min/mg', 'nmol/min/mg')),
        'definition_witnesses': {'type': 'null'},
        'status': enum('supported', 'unknown', 'unsupported', 'numeric_range', 'dependency_unavailable', 'endpoint_correspondence_unknown'),
        'diagnostics': arr(ref('Diagnostic'))})
    D['ExactBounds'] = obj({
        'lower': ref('Rational'),
        'upper': ref('Rational')})
    D['FloatBounds'] = obj({
        'lower': N,
        'upper': N})
    D['Run'] = obj({
        'top': I,
        'bottom': I})
    D['ExactPixelEdge'] = obj({
        'terminal_edge': enum('upper', 'lower'),
        'nominal': ref('Rational'),
        'bounds': ref('ExactBounds')})
    D['ExactAxis'] = obj({
        'first_pixel': ref('Rational'),
        'second_pixel': ref('Rational'),
        'first_value': ref('Rational'),
        'second_value': ref('Rational'),
        'unit': enum('umol/min', 'nmol/min', 'mmol/min', 'uM/min', 'nM/min', 'per_min', 'per_s', 'umol/min/mg', 'nmol/min/mg'),
        'slope': ref('Rational')})
    D['PixelResult'] = obj({
        'version': {'const': 'controlled_response_rate_pixels_v1'},
        'status': enum('measured', 'unreadable', 'ambiguous', 'unsupported', 'dependency_unavailable'),
        'image_id': T,
        'image_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}),
        'original_image_sha256': null({'type': 'string', 'pattern': '^[a-f0-9]{64}$'}),
        'mapped_roi': null(ref('ImageLocator')),
        'recipe': ref('BarSelection'),
        'terminal_edge': enum('upper', 'lower'),
        'image_size': null(obj({
            'width': I,
            'height': I})),
        'qualifying_runs': arr(ref('Run')),
        'pixel_edge': null(ref('ExactPixelEdge')),
        'axis': null(ref('ExactAxis')),
        'native_ordinate': null(ref('Rational')),
        'native_bounds': null(ref('ExactBounds')),
        'bound_kind': {'const': 'conditional_digitization_not_confidence_interval'},
        'diagnostics': arr(ref('Diagnostic')),
        'counter_version': {'const': 'controlled_response_bar_runs_v1'},
        'counter_module_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}})
    D['CanonicalDisplay'] = obj({
        'value': null(N),
        'threshold': null(N),
        'unit': null(enum('umol/min', 'uM/min', 'per_min', 'umol/min/mg')),
        'relation': enum('eq', 'lt', 'le', 'gt', 'ge', 'none'),
        'approximate': B,
        'diagnostics': arr(ref('Diagnostic'))})
    D['NativeProjection'] = obj({
        'value': null(N),
        'threshold': {'type': 'null'},
        'relation': enum('interval', 'none'),
        'approximate': B,
        'unit': null(enum('umol/min', 'nmol/min', 'mmol/min', 'uM/min', 'nM/min', 'per_min', 'per_s', 'umol/min/mg', 'nmol/min/mg')),
        'status': enum('point', 'missing', 'ambiguous', 'conflicting', 'unsupported'),
        'origin': {'const': 'graph_derived'},
        'digitization_interval': null(ref('FloatBounds'))})
    D['MeasurementExtractionV2'] = obj({
        'selection': ref('GraphMeasurement'),
        'candidates': {'type': 'array', 'maxItems': 0},
        'fragments': arr(ref('WitnessRecord')),
        'unit': null(ref('GraphUnitRecord')),
        'graph_witnesses': arr(ref('WitnessRecord')),
        'reading_status': enum('graph_digitized', 'ambiguous', 'unreadable', 'conflicting', 'unsupported', 'dependency_unavailable'),
        'source_observation_id': null(T),
        'canonical_display': ref('CanonicalDisplay'),
        'pixel_result': ref('PixelResult'),
        'diagnostics': arr(ref('Diagnostic'))})
    schema = obj({
        'version': {'const': 'controlled_response_rate_figure_extraction_v1'},
        'selection': obj({
            'version': {'const': 'controlled_response_rate_figure_selection_v1'},
            'images': arr(ref('Image')),
            'measurement': ref('GraphMeasurement')}),
        'sources': arr(ref('SourceRecord')),
        'images': arr(ref('ImageRecord')),
        'axis_scale': ref('AxisScaleRecord'),
        'axis_literals': obj({
            'first': ref('AxisLiteralRecord'),
            'second': ref('AxisLiteralRecord'),
            'unit': ref('AxisLiteralRecord')}),
        'measurement': ref('MeasurementExtractionV2'),
        'operand_projection': ref('NativeProjection'),
        'diagnostics': arr(ref('Diagnostic'))})
    schema.update({"$defs": D, "$schema": "https://json-schema.org/draft/2020-12/schema"})
    return schema


def _sheet_schema():
    D = {}
    D["OwnerInputs"] = embed(controlled_response_owner_arguments_schema(), "Input_", D)
    D['Cell'] = obj({
        'value': null(N),
        'lower': null(N),
        'upper': null(N),
        'relation': enum('none', 'eq', 'lt', 'le', 'gt', 'ge', 'interval'),
        'approximate': B,
        'unit': null(enum('umol/min', 'uM/min', 'per_min', 'umol/min/mg', '(umol/min)^2', '(uM/min)^2', '(per_min)^2', '(umol/min/mg)^2', '(umol/min)^-2', '(uM/min)^-2', '(per_min)^-2', '(umol/min/mg)^-2', 'dimensionless')),
        'status': enum('available', 'bounded', 'partial', 'unavailable', 'unsupported', 'conflicting'),
        'origin': enum('reported', 'graph_derived', 'synthetic', 'calculated'),
        'unavailable_reason': null(arr(enum('missing_arm', 'unknown_unit', 'incompatible_unit_dimension', 'unknown_endpoint', 'different_endpoint', 'conflicting_endpoint', 'unknown_normalization', 'different_normalization', 'conflicting_normalization', 'unknown_subject_correspondence', 'different_subject_correspondence', 'conflicting_subject_correspondence', 'unknown_control_application', 'conflicting_control_application', 'unknown_protein_arrangement', 'conflicting_protein_arrangement', 'incompatible_control_arrangement', 'unknown_condition_correspondence', 'different_condition_correspondence', 'conflicting_condition_correspondence', 'condition_levels_not_distinct', 'missing_intended_factor', 'conflicting_control_reuse', 'unsupported_source_expression', 'ambiguous_source_literal', 'conflicting_source_literal', 'unavailable_source_dependency', 'unknown_covariance', 'estimated_covariance', 'nonpositive_variance_for_model', 'observation_model_unselected', 'unresolved_censoring_model', 'unresolved_reading_model', 'numeric_range_failure', 'uninformative_bounds', 'incomplete_active_covariance', 'unresolved_active_reading_model', 'conflicting_owner_context', 'conflicting_source_owner_binding'), minItems=1, uniqueItems=True)),
        'formula_code': enum('condition_control_difference', 'four_arm_condition_difference', 'inverse_variance', 'linear_joint_covariance', 'signed_known_normal_profile', 'source_response', 'square_root_variance', 'tanh_half_signed_profile'),
        'conditional_on': arr(enum('synthetic_fixture', 'approximate_source_reading', 'conditional_digitization', 'nonintended_conditions_different', 'nonintended_conditions_unknown', 'nonintended_conditions_conflicting', 'unknown_control_reuse', 'estimated_covariance', 'known_normal_source_means', 'shared_reference_assumption', 'owner_cancellation', 'canceled_reading_unavailable', 'canceled_unit_unknown', 'canceled_representation_difference', 'canceled_graph_reading', 'canceled_source_reading_conflict', 'canceled_reading_domain_conflict'), uniqueItems=True),
        'bound_kind': enum('none', 'reported_limit', 'conditional_digitization', 'mixed'),
        'bound_state': obj({
            'lower': enum('unknown', 'unbounded', 'available', 'numeric_range_failure', 'not_applicable'),
            'upper': enum('unknown', 'unbounded', 'available', 'numeric_range_failure', 'not_applicable')})})
    D['ContrastDependencies'] = obj({
        'coefficient_order': {'const': ['protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0']},
        'role_coefficients': {'const': [1, -1, -1, 1]},
        'groups': arr(obj({
            'physical_observation_id': null(T),
            'roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), minItems=1, maxItems=4, uniqueItems=True),
            'coefficient': {'type': 'integer', 'minimum': -2, 'maximum': 2},
            'known_owner': B}), minItems=1, maxItems=4),
        'active_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True),
        'canceled_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True),
        'scientific_reasons': arr(enum('missing_arm', 'unknown_unit', 'incompatible_unit_dimension', 'unknown_endpoint', 'different_endpoint', 'conflicting_endpoint', 'unknown_normalization', 'different_normalization', 'conflicting_normalization', 'unknown_subject_correspondence', 'different_subject_correspondence', 'conflicting_subject_correspondence', 'unknown_control_application', 'conflicting_control_application', 'unknown_protein_arrangement', 'conflicting_protein_arrangement', 'incompatible_control_arrangement', 'unknown_condition_correspondence', 'different_condition_correspondence', 'conflicting_condition_correspondence', 'condition_levels_not_distinct', 'missing_intended_factor', 'conflicting_control_reuse', 'unsupported_source_expression', 'ambiguous_source_literal', 'conflicting_source_literal', 'unavailable_source_dependency', 'unknown_covariance', 'estimated_covariance', 'nonpositive_variance_for_model', 'observation_model_unselected', 'unresolved_censoring_model', 'unresolved_reading_model', 'numeric_range_failure', 'uninformative_bounds', 'incomplete_active_covariance', 'unresolved_active_reading_model', 'conflicting_owner_context', 'conflicting_source_owner_binding'), uniqueItems=True),
        'active_reading_reasons': arr(enum('missing_arm', 'unknown_unit', 'incompatible_unit_dimension', 'unknown_endpoint', 'different_endpoint', 'conflicting_endpoint', 'unknown_normalization', 'different_normalization', 'conflicting_normalization', 'unknown_subject_correspondence', 'different_subject_correspondence', 'conflicting_subject_correspondence', 'unknown_control_application', 'conflicting_control_application', 'unknown_protein_arrangement', 'conflicting_protein_arrangement', 'incompatible_control_arrangement', 'unknown_condition_correspondence', 'different_condition_correspondence', 'conflicting_condition_correspondence', 'condition_levels_not_distinct', 'missing_intended_factor', 'conflicting_control_reuse', 'unsupported_source_expression', 'ambiguous_source_literal', 'conflicting_source_literal', 'unavailable_source_dependency', 'unknown_covariance', 'estimated_covariance', 'nonpositive_variance_for_model', 'observation_model_unselected', 'unresolved_censoring_model', 'unresolved_reading_model', 'numeric_range_failure', 'uninformative_bounds', 'incomplete_active_covariance', 'unresolved_active_reading_model', 'conflicting_owner_context', 'conflicting_source_owner_binding'), uniqueItems=True),
        'canceled_reading_qualifications': arr(enum('synthetic_fixture', 'approximate_source_reading', 'conditional_digitization', 'nonintended_conditions_different', 'nonintended_conditions_unknown', 'nonintended_conditions_conflicting', 'unknown_control_reuse', 'estimated_covariance', 'known_normal_source_means', 'shared_reference_assumption', 'owner_cancellation', 'canceled_reading_unavailable', 'canceled_unit_unknown', 'canceled_representation_difference', 'canceled_graph_reading', 'canceled_source_reading_conflict', 'canceled_reading_domain_conflict'), uniqueItems=True),
        'reading_conflict_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True),
        'required_covariance_owner_ids': arr(T, uniqueItems=True),
        'provided_covariance_owner_ids': arr(T, uniqueItems=True),
        'covariance_state': enum('unavailable', 'available', 'incomplete_active_coverage', 'scientific_blocked'),
        'model_active_roles': arr(enum('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0'), uniqueItems=True)})
    schema = obj({
        'version': {'const': 'controlled_response_owner_sheet_v2'},
        'primitive_order': {'const': ['protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0']},
        'inputs': ref('OwnerInputs'),
        'cells': obj({
            'protein_condition1_response': ref('Cell'),
            'empty_condition1_response': ref('Cell'),
            'protein_condition0_response': ref('Cell'),
            'empty_condition0_response': ref('Cell'),
            'condition1_controlled_response': ref('Cell'),
            'condition0_controlled_response': ref('Cell'),
            'controlled_response_difference': ref('Cell'),
            'contrast_variance': ref('Cell'),
            'contrast_standard_uncertainty': ref('Cell'),
            'contrast_precision': ref('Cell'),
            'source_profile_log_ratio': ref('Cell'),
            'source_signed_index': ref('Cell')}),
        'contrast_dependencies': ref('ContrastDependencies')})
    schema.update({"$defs": D, "$schema": "https://json-schema.org/draft/2020-12/schema"})
    return schema


def _extraction_schema():
    selection = controlled_response_v2_arguments_schema()
    graph = _graph_schema()
    owner = controlled_response_owner_arguments_schema()
    sheet = _sheet_schema()
    D = cp(selection["$defs"])
    D["Selection"] = embed(selection, "S_", D)
    D["GraphResult"] = embed(graph, "G_", D)
    D["OwnerInputs"] = embed(owner, "O_", D)
    D["OwnerSheet"] = embed(sheet, "H_", D)
    T = {"type": "string", "minLength": 1}
    N = {"type": "number"}
    I = {"type": "integer", "minimum": 0}
    B = {"type": "boolean"}
    SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    rate = cp(D["G_GraphUnitRecord"]["properties"]["native_registry_unit"]["anyOf"][0])
    canonical = cp(D["G_GraphUnitRecord"]["properties"]["canonical_unit"]["anyOf"][0])
    for name in ("Rational", "TextLocator", "ImageLocator", "WitnessRecord", "SourceRecord", "ImageRecord", "CanonicalDisplay"):
        D[name] = cp(D["G_" + name])
    codes = sorted(set(['measurement_not_selected', 'source_literal_unreadable', 'source_literal_ambiguous', 'source_literal_conflicting', 'unsupported_complete_source_expression', 'source_numeric_range', 'numeric_projection_rounding', 'source_rate_unit_unknown', 'source_rate_unit_unsupported', 'source_defined_unit_definition_not_selected', 'unit_endpoint_correspondence_unknown', 'custom_unit_projection_unrepresentable', 'source_dependency_unavailable', 'source_text_encoding_unsupported', 'source_image_format_unsupported', 'source_image_decode_failed', 'source_uncertainty_meaning_conflict', 'source_uncertainty_piece_unsupported', 'source_uncertainty_unit_unknown', 'source_uncertainty_unit_conflicting', 'qualified_confidence_unsupported', 'source_confidence_sentence_stop_unsupported', 'unsupported_covariance_representation', 'source_json_duplicate_key', 'source_json_nonfinite', 'source_covariance_shape_invalid', 'source_covariance_asymmetric', 'source_covariance_not_psd', 'source_covariance_origin_invalid', 'covariance_owner_unresolved', 'covariance_owner_conflicting', 'covariance_shared_values_conflicting', 'covariance_shared_rows_conflicting', 'source_covariance_unit_unsupported', 'covariance_projection_numeric_range', 'covariance_projection_precision_invalid', 'variance_status_not_selected', 'source_variance_status_unknown', 'requested_source_variance_status_conflict', 'normal_model_not_selected', 'source_normal_model_unsupported', 'source_model_witness_unavailable', 'source_model_projection_rounding', 'synthetic_covariance_with_reported_operands', 'graph_rate_reader_unimplemented'] + D["G_Diagnostic"]["properties"]["code"]["enum"] + [
        "covariance_owner_subset", "covariance_incomplete_owner_binding", "covariance_owner_dimension_conflict",
        "unresolved_active_representation_model", "canceled_source_representation_difference",
        "source_reading_nomination_identity", "source_model_active_scope_unresolved",
        "source_covariance_full_scope_invalid", "source_covariance_projection_loss",
    ]))
    D["Diagnostic"] = obj({"code": enum(*codes), "field": T,
        "domain": enum("source_representation", "source_binding", "reader_capability", "source_interpretation", "dependency"),
        "source_refs": arr(T, uniqueItems=True)})
    AD = arr(ref("Diagnostic"))
    # Shared saved records point to the union diagnostic vocabulary.
    for name in ("WitnessRecord", "SourceRecord", "CanonicalDisplay"):
        D[name]["properties"]["diagnostics"] = cp(AD)
    
    interpret_values = sorted({v for name in ("Relationships", "Arm") for p in D[name]["properties"].values()
        if p.get("type") == "object" and "value" in p.get("properties", {})
        for v in p["properties"]["value"].get("enum", [])} | {
            "known", "estimated", "sd", "sem", "ci", "unspecified", "unreported", "same_as_response", "explicit_unit",
            "biological_preparations", "technical_measurements", "fit_to_averaged_curve", "between_fitted_parameters", "none",
            "known_joint_normal_source_means"})
    D["InterpretationExtraction"] = obj({"selection": obj({"value": enum(*interpret_values), "witnesses": arr(ref("Witness"))}),
        "witnesses": arr(ref("WitnessRecord")), "effective_value": enum(*interpret_values), "diagnostics": AD})
    D["MeaningExtraction"] = obj({"selection": ref("Meaning"), "witnesses": arr(ref("WitnessRecord")),
        "canonical_witness": null(ref("WitnessRecord")), "canonical_correspondence": ref("InterpretationExtraction"),
        "resolved_state": enum("known", "unknown", "conflicting"), "canonical_id": null(T), "diagnostics": AD})
    D["NumberCandidate"] = obj({"selection": ref("NumberSelector"), "witness": ref("WitnessRecord"),
        "raw_expression": null(T), "native_value": null(N), "relation": enum("point", "lt", "le", "gt", "ge", "unresolved"),
        "approximate": null(B), "source_locator": null(ref("TextLocator")),
        "status": enum("parsed", "unsupported", "numeric_range", "dependency_unavailable"), "diagnostics": AD})
    D["DefinitionWitnesses"] = obj({k: ref("NumberCandidate") if k == "amount" else ref("WitnessRecord")
        for k in ("bridge", "clause", "amount", "amount_unit", "time_unit", "endpoint", "endpoint_entity", "definition_entity")})
    D["TextUnitRecord"] = obj({"selection": null(ref("UnitSelection")), "witness": null(ref("WitnessRecord")),
        "raw_unit": null(T), "canonical_unit": null(canonical), "exact_scale": null(ref("Rational")),
        "native_registry_unit": null(rate), "definition_witnesses": null(ref("DefinitionWitnesses")),
        "status": enum("supported", "unknown", "unsupported", "numeric_range", "dependency_unavailable", "endpoint_correspondence_unknown"), "diagnostics": AD})
    D["UnitCarrier"] = {"oneOf": [obj({"kind": {"const": "text"}, "record": ref("TextUnitRecord")}),
        obj({"kind": {"const": "graph"}, "record": ref("G_GraphUnitRecord")})]}
    # Tags belong to the shared host carrier. Original v1/063 records stay unchanged.
    D["TextMeasurementExtraction"] = obj({"selection": null(ref("TextMeasurement")), "candidates": arr(ref("NumberCandidate")),
        "fragments": arr(ref("WitnessRecord")), "unit": null(ref("TextUnitRecord")), "graph_witnesses": arr(ref("WitnessRecord"), maxItems=0),
        "reading_status": enum("not_selected", "exact", "ambiguous", "unreadable", "conflicting", "unsupported", "dependency_unavailable"),
        "source_observation_id": null(T), "canonical_display": ref("CanonicalDisplay"), "pixel_result": {"type": "null"}, "diagnostics": AD})
    D["MeasurementExtraction"] = {"oneOf": [ref("TextMeasurementExtraction"), ref("G_MeasurementExtractionV2")]}
    piece_states = enum("parsed", "unsupported", "numeric_range", "dependency_unavailable")
    D["IntervalRecord"] = obj({"selection": ref("CISelector"), "witness": ref("WitnessRecord"),
        "raw_values": null(arr(T, minItems=2, maxItems=2)), "values": null(arr(N, minItems=2, maxItems=2)), "status": piece_states, "diagnostics": AD})
    D["ConfidenceRecord"] = obj({"selection": ref("NativeTextWitness"), "witness": ref("WitnessRecord"),
        "value": null({"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1}), "status": piece_states, "diagnostics": AD})
    # The native count reading is preserved exactly; lexical/dependent semantics are
    # checked by the shared saved validator rather than inferred from the numeral.
    D["NativeSavedWitness"] = obj({**cp(D["NativeTextWitness"]["properties"]), "artifact_ref": T})
    D["NativeSavedNumberSelector"] = obj({**cp(D["NumberSelector"]["properties"]), "witness": ref("NativeSavedWitness")})
    D["CountReading"] = obj({"selector": ref("NativeSavedNumberSelector"), "raw_number": T, "value": null({"type": "integer"}),
        "notation": enum("decimal_digits", "english_cardinal", "unsupported"), "relation": enum("point", "lt", "le", "gt", "ge", "unresolved"),
        "approximate": null(B), "status": enum("exact", "qualified", "not_positive", "unsupported", "range_or_alternatives"),
        "unavailable_reason": null(enum("count_range_or_alternatives", "unsupported_count_literal", "positive_count_required", "exact_count_qualified"))})
    D["CountRecord"] = obj({"selection": ref("NumberSelector"), "witness": ref("WitnessRecord"), "reading": null(ref("CountReading")), "diagnostics": AD})
    D["UncertaintyCanonical"] = obj({"statistic": enum("sd", "sem", "ci", "unspecified", "unreported", "unknown", "conflicting"),
        "magnitude": null({"type": "number", "minimum": 0}), "interval": null(arr(N, minItems=2, maxItems=2)),
        "confidence_level": null({"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1}),
        "count": null({"type": "integer", "minimum": 1}), "repetition_basis": cp(D["Uncertainty"]["properties"]["repetition_basis"]["properties"]["value"]),
        "estimate_basis": cp(D["Uncertainty"]["properties"]["estimate_basis"]["properties"]["value"])})
    D["UncertaintyExtraction"] = obj({"selection": ref("Uncertainty"),
        "meanings": obj({k: ref("InterpretationExtraction") for k in ("statistic", "unit_relationship", "repetition_basis", "estimate_basis")}),
        "magnitude": null(ref("NumberCandidate")), "interval": null(ref("IntervalRecord")), "unit": null(ref("TextUnitRecord")),
        "effective_unit": null(ref("UnitCarrier")), "confidence_level": null(ref("ConfidenceRecord")), "count": null(ref("CountRecord")),
        "canonical": ref("UncertaintyCanonical"), "diagnostics": AD})
    roles = list(selection["properties"]["arms"]["properties"])
    D["ArmScience"] = obj({"selection": ref("Arm"), "context": obj({k: null(ref("WitnessRecord")) for k in D["Arm"]["properties"]["context"]["properties"]}),
        "protein_arrangement": ref("InterpretationExtraction"), "meanings": obj({k: ref("MeaningExtraction") for k in
        ("endpoint", "normalization", "subject_construct", "condition", "physical_observation")}), "intended_factor_level": null(ref("WitnessRecord"))})
    D["ArmExtraction"] = obj({**cp(D["ArmScience"]["properties"]), "measurement": ref("MeasurementExtraction"),
        "reported_uncertainty": ref("UncertaintyExtraction"), "calculation_operand": null(ref("O_Arm")),
        "graph_details": null(ref("GraphResult")), "diagnostics": AD})
    D["RelationshipExtraction"] = obj({k: ref("MeaningExtraction") if k.endswith("_target") else null(ref("WitnessRecord")) if k == "intended_factor"
        else ref("InterpretationExtraction") for k in D["Relationships"]["properties"]})
    D["CovarianceBindingExtraction"] = obj({"selection": null(ref("CovarianceBinding")), "label_witness": null(ref("WitnessRecord")),
        "owner_witness": null(ref("WitnessRecord")), "correspondence": null(ref("InterpretationExtraction")),
        "source_variable_index": null(I), "resolved_owner_id": null(T), "state": enum("known", "unknown", "conflicting"), "diagnostics": AD})
    D["CovarianceSourceVariable"] = obj({"index": I, "label": T, "unit": T, "description": T,
        **{k + "_witness": ref("WitnessRecord") for k in ("label", "unit", "description")},
        "native_registry_unit": null(rate), "exact_scale": null(ref("Rational")), "diagnostics": AD})
    D["SourceModel"] = obj({"origin": enum("reported", "derived", "synthetic"), "variance_status": enum("known", "estimated", "unknown"),
        "model_kind": enum("none", "known_joint_normal_source_means")})
    D["OwnerProjection"] = obj({"physical_observation_id": T, "source_variable_index": I,
        "roles": arr(enum(*roles), minItems=1, uniqueItems=True), "native_registry_unit": rate})
    D["CovarianceExtraction"] = obj({"selection": cp(selection["properties"]["covariance"]["anyOf"][0]), "source_ref": T,
        "artifact_ref": null(T), "byte_sha256": null(SHA), "raw_text": null(T), "variables": arr(ref("CovarianceSourceVariable")),
        "matrix_tokens": null(arr(arr(T))), "exact_matrix": null(arr(arr(ref("Rational")))), "source_model": null(ref("SourceModel")),
        "bindings": obj({r: ref("CovarianceBindingExtraction") for r in roles}),
        "provided_owner_projection": arr(ref("OwnerProjection"), maxItems=4), "projected_exact_matrix": null(arr(arr(ref("Rational")))),
        "calculation_covariance": null({"oneOf": [ref("O_RoleCovariance"), ref("O_OwnerCovariance")]}),
        "source_validation": enum("valid", "invalid", "unassessed"),
        "projection_state": enum("available", "unavailable", "numeric_range", "precision_invalid", "source_invalid", "binding_unresolved", "binding_conflicting", "unsupported_format"),
        "diagnostics": AD})
    D["ExactResponse"] = obj({"point": null(ref("Rational")), "lower": null(ref("Rational")), "upper": null(ref("Rational")),
        "relation": enum("eq", "lt", "le", "gt", "ge", "interval", "none"), "approximate": B, "unit": null(canonical)})
    D["MeasurementReading"] = obj({"selection": null({"oneOf": [ref("TextMeasurement"),ref("GraphMeasurement")]}),
        "extraction": ref("MeasurementExtraction"), "operand_projection": obj({k: cp(D["O_Arm"]["properties"][k]) for k in
            ("value","threshold","relation","approximate","unit","status","origin","digitization_interval")}),
        "unit_semantics": null(ref("UnitCarrier")),"exact_response": null(ref("ExactResponse")),
        "source_observation_id": null(T),"graph_details": null(ref("GraphResult"))})
    D["RetainedRepresentation"] = obj({"role": enum(*roles), "source_reading_id": null(T), "exact_domain": null(ref("ExactResponse"))})
    D["ReconciliationRecord"] = obj({"physical_observation_id": null(T), "roles": arr(enum(*roles), minItems=1, uniqueItems=True),
        "readings": arr(ref("RetainedRepresentation"), minItems=1), "net_coefficient": {"type": "integer"},
        "method": enum("single_reading", "owner_cancellation", "exact_equivalence", "unresolved"),
        "state": enum("single", "exact_equivalent", "canceled_readings_retained", "unresolved_active_model", "conflicting_active_domains", "unresolved_science"),
        "canonical_source_reading_id": null(T), "qualifications": arr(enum("conditional_digitization_not_sampling", "canceled_numeric_conflict", "canceled_numeric_unavailable", "canceled_unit_unknown", "active_reconciliation_unimplemented"), uniqueItems=True), "diagnostics": AD})
    D["RequestedModel"] = obj({k: ref("InterpretationExtraction") for k in ("variance_status", "model_kind")})
    D["EffectiveModel"] = obj({"variance_status": enum("known", "estimated", "unknown"), "model_kind": enum("none", "known_joint_normal_source_means"), "diagnostics": AD})
    D["DependencyRecord"] = obj({"reader_contract_version": {"const": "controlled_response_source_extraction_v2"},
        "calculator_contract_version": {"const": "controlled_response_owner_inputs_v2"},
        "expected_module_fingerprints": obj({k: SHA for k in [*shared.DEPENDENCIES,
            "literature_controlled_response_inputs.py", "literature_controlled_response_v2_inputs.py",
            "literature_controlled_response_figure_inputs.py", "literature_controlled_response_owner_calculations.py"]})})
    root = obj({"version": {"const": "controlled_response_source_extraction_v2"}, "selection": ref("Selection"),
        "sources": arr(ref("SourceRecord")), "images": arr(ref("ImageRecord")), "arms": obj({r: null(ref("ArmExtraction")) for r in roles}),
        "relationships": ref("RelationshipExtraction"), "covariance": null(ref("CovarianceExtraction")),
        "requested_model": ref("RequestedModel"), "effective_model": ref("EffectiveModel"), "calculation_inputs": ref("OwnerInputs"),
        "representation_reconciliations": arr(ref("ReconciliationRecord")), "diagnostics": AD, "implementation_dependencies": ref("DependencyRecord")})
    root.update({"$defs": D, "$schema": "https://json-schema.org/draft/2020-12/schema"})
    return root


def validate_controlled_response_v2_selection(arguments):
    selected = shared._validate_selection(arguments, controlled_response_v2_arguments_schema())
    for arm in selected["arms"].values():
        if arm and arm["measurement"] and arm["measurement"]["kind"] == "linear_bar":
            graph_reader._validate(_graph_request(selected, arm["measurement"]))
    return selected


def _graph_request(selected, measurement):
    return {"version": "controlled_response_rate_figure_selection_v1", "images": cp(selected["images"]), "measurement": cp(measurement)}


def _dependencies():
    names = [*shared.DEPENDENCIES, "literature_controlled_response_inputs.py", "literature_controlled_response_v2_inputs.py",
        "literature_controlled_response_figure_inputs.py", "literature_controlled_response_owner_calculations.py"]
    return {name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names}


def _read_graph(context, selected):
    def cached(reference, representation):
        key = reference, representation
        context._active()
        if key not in context.cache:
            shared._fail("unselected_source_read", "source_ref")
        error = context.unavailable_errors.get(key)
        if error is not None:
            if isinstance(error, EOFError):
                raise OSError(errno.EIO, str(error)) from error
            raise error
        return context.read_source(reference, representation)
    result = graph_reader.read_controlled_response_rate_figure(_graph_request(context.arguments, selected), read_source=cached)
    return _graph_reading(context, selected, result)


def _graph_reading(context, selected, result):
    measurement = result["measurement"]
    return shared._StageValue(context, {"selection": selected, "extraction": measurement,
        "operand_projection": result["operand_projection"], "unit_semantics": {"kind": "graph", "record": measurement["unit"]},
        "exact_response": shared._exact_response(measurement, graph=True),
        "source_observation_id": measurement["source_observation_id"], "graph_details": result})


def read_controlled_response_v2_inputs(arguments, *, read_source):
    if not isinstance(arguments, dict) or arguments.get("version") != "controlled_response_source_selection_v2":
        validate_controlled_response_v2_selection(arguments)
    with shared.open_controlled_response_sources(arguments, read_source=read_source) as context:
        if context.profile != "v2":
            shared._fail("controlled_selection_schema_invalid", "arguments")
        arms = {}
        for role in shared.PRIMITIVE_ORDER:
            selected = context.arguments["arms"][role]
            if selected is None:
                arms[role] = None
                continue
            science = shared.read_controlled_response_arm_science(context, selected)
            nomination = selected["measurement"]
            measurement = (_read_graph(context, nomination) if nomination and nomination["kind"] == "linear_bar" else
                shared.read_controlled_response_text_measurement(context, nomination, endpoint=science["meanings"]["endpoint"]))
            arms[role] = shared.finish_controlled_response_arm(context, science, measurement=measurement)
        return shared.finish_controlled_response_inputs(context, arms=arms)


def validate_controlled_response_v2_extraction(arguments, extraction):
    def validate_measurement(selected, saved_measurement, *, source_records, image_records):
        if selected and selected["kind"] == "linear_bar":
            arms = extraction.get("arms", {})
            candidates = [arm for arm in arms.values() if arm is not None and arm["selection"]["measurement"] == selected and arm["measurement"] == saved_measurement]
            if not candidates or candidates[0]["graph_details"] is None or candidates[0]["graph_details"]["measurement"] != saved_measurement:
                shared._fail("saved_graph_measurement_mismatch", "measurement")
            sources = {(s["source_ref"],s["representation"]):s for s in source_records}
            return _validate_graph(selected, candidates[0]["graph_details"], sources=sources, images=image_records, request=arguments)
        return _validate_measurement(selected, saved_measurement, source_records=source_records, image_records=image_records)
    return shared.validate_controlled_response_saved_science(arguments, extraction, measurement_checks=validate_measurement)


__all__ = ["controlled_response_v2_arguments_schema", "validate_controlled_response_v2_selection",
    "read_controlled_response_v2_inputs", "validate_controlled_response_v2_extraction"]


def _saved_roster(selected, extraction):
    sources = {}
    artifacts = {}
    for source in extraction["sources"]:
        key = source["source_ref"], source["representation"]
        if key in sources:
            shared._fail("saved_duplicate_source", "sources")
        sources[key] = source
        if source["state"] == "available":
            if not source["artifact_ref"].strip() or not source["byte_sha256"]:
                shared._fail("saved_source_identity_mismatch", "sources")
            if source["artifact_ref"] in artifacts and artifacts[source["artifact_ref"]] != source["byte_sha256"]:
                shared._fail("artifact_content_conflict", "sources")
            artifacts[source["artifact_ref"]] = source["byte_sha256"]
        elif source["artifact_ref"] is not None or source["byte_sha256"] is not None:
            shared._fail("saved_source_state_mismatch", "sources")
    if list(sources) != shared._reference_closure(selected):
        shared._fail("saved_source_roster_mismatch", "sources")
    _saved_images(selected["images"], extraction["images"], sources)
    return sources


def _saved_images(nominated, images, sources):
    if len(images) != len(nominated):
        shared._fail("saved_image_roster_mismatch", "images")
    for spec,record in zip(nominated, images):
        if any(spec[k] != record[k] for k in ("image_id", "source_ref", "original_source_ref", "mapping")):
            shared._fail("saved_image_selection_mismatch", "images")
        for prefix, ref_key in (("", "source_ref"), ("original_", "original_source_ref")):
            source = sources[(spec[ref_key], "original")]
            # Original008 geometry may lose unavailable/decode-failed metadata;
            # independently retained graph records keep those bytes explicitly.
            if record[prefix+"artifact_ref"] is not None and (
                    record[prefix+"artifact_ref"] != source["artifact_ref"] or record[prefix+"byte_sha256"] != source["byte_sha256"]):
                shared._fail("saved_image_source_mismatch", "images")
        if not record["error"] and (not record["width"] or not record["height"] or record["frame_count"] != 1):
            shared._fail("saved_image_geometry_mismatch", "images")


def _check_witness(record, nominated, sources, images, field):
    shared._saved_witness(record, nominated, sources, field)
    if record is None or record["canonical_locator"] is None or record["selection"]["kind"] != "image":
        return
    selected = record["selection"]
    image = next(i for i in images if i["image_id"] == selected["image_id"])
    region = selected["region"]
    if image["error"] or not (0 <= region[0] < region[2] <= image["width"] and 0 <= region[1] < region[3] <= image["height"]):
        shared._fail("saved_image_geometry_mismatch", field)
    if image["mapping"]:
        original = image["mapping"]["original_region"]
        region = [region[0]+original[0], region[1]+original[1], region[2]+original[0], region[3]+original[1]]
    wanted = {"kind": "image", "original_source_ref": image["original_source_ref"],
        "original_artifact_ref": image["original_artifact_ref"], "original_byte_sha256": image["original_byte_sha256"], "region": region}
    if record["canonical_locator"] != wanted or record["artifact_ref"] != image["artifact_ref"] or record["byte_sha256"] != image["byte_sha256"]:
        shared._fail("saved_image_identity_mismatch", field)


def _validate_text(selected, measurement, sources, images):
    if measurement["selection"] != selected:
        shared._fail("saved_selection_mismatch", "measurement")
    if selected is None:
        expected = {"selection": None, "candidates": [], "fragments": [], "unit": None, "graph_witnesses": [],
            "reading_status": "not_selected", "source_observation_id": None,
            "canonical_display": shared._display(None, None), "pixel_result": None}
        if any(measurement[k] != v for k,v in expected.items()):
            shared._fail("saved_measurement_projection_mismatch", "measurement")
        return
    literal = selected["literal"]
    if len(measurement["candidates"]) != len(literal["candidates"]) or len(measurement["fragments"]) != len(literal["fragments"]):
        shared._fail("saved_selection_mismatch", "measurement")
    for record,nominated in zip(measurement["candidates"], literal["candidates"]):
        shared._saved_number(record, nominated, sources, "measurement.candidates")
    for record,nominated in zip(measurement["fragments"], literal["fragments"]):
        _check_witness(record, nominated, sources, images, "measurement.fragments")
    shared._saved_unit(measurement["unit"], selected["unit"], sources, "measurement.unit")
    state = literal["status"]
    if any(n["status"] == "dependency_unavailable" for n in measurement["candidates"]) or any(w["canonical_locator"] is None for w in measurement["fragments"]):
        state = "dependency_unavailable"
    elif state == "exact" and measurement["candidates"][0]["status"] != "parsed":
        state = "unsupported"
    locators = [n["source_locator"] for n in measurement["candidates"] if n["source_locator"] is not None]
    locators += [w["canonical_locator"] for w in measurement["fragments"] if w["canonical_locator"] is not None]
    reading_id = shared.identity("controlled_source_token", locators[0] if len(locators) == 1 else locators) if state != "dependency_unavailable" and locators else None
    if measurement["reading_status"] != state or measurement["source_observation_id"] != reading_id:
        shared._fail("saved_measurement_identity_mismatch", "measurement")
    number = measurement["candidates"][0] if state == "exact" else None
    expected_display = shared._display(number, measurement["unit"]) if state == "exact" else shared._display(None,None)
    if measurement["canonical_display"] != expected_display:
        shared._fail("saved_canonical_display_mismatch", "measurement")


def _validate_measurement(selected, saved_measurement, *, source_records, image_records):
    """Closed text check; graph checks additionally retain the complete063 result."""
    sources = {(s["source_ref"],s["representation"]):s for s in source_records}
    _validate_text(selected, saved_measurement, sources, image_records)
    return shared._reading_from_text(None, selected, saved_measurement)


def _validate_graph(selected, result, *, sources, images, request):
    Draft202012Validator(_graph_schema()).validate(result)
    if result["selection"] != _graph_request(request, selected) or result["version"] != "controlled_response_rate_figure_extraction_v1":
        shared._fail("saved_graph_selection_mismatch", "graph_details")
    closure = []
    for image in request["images"]:
        closure.extend([(image["source_ref"], "original"), (image["original_source_ref"], "original")])
    closure += [(w["source_ref"],w["representation"]) for w in graph_reader._witnesses(selected) if w["kind"] == "text"]
    closure = list(dict.fromkeys(closure))
    actual_closure = [(s["source_ref"],s["representation"]) for s in result["sources"]]
    if len(actual_closure) != len(set(actual_closure)) or set(actual_closure) != set(closure):
        shared._fail("saved_graph_source_roster_mismatch", "graph_details.sources")
    for source in result["sources"]:
        original = sources[(source["source_ref"], source["representation"])]
        if any(source[k] != original[k] for k in ("artifact_ref", "byte_sha256", "state")):
            shared._fail("saved_graph_source_identity_mismatch", "graph_details.sources")
    _saved_images(request["images"], result["images"], sources)
    actual_images = result["images"]
    for name,literal in result["axis_literals"].items():
        nominated = selected["axis"][name] if name == "unit" else selected["axis"][name]["tick"]
        if literal["selection"] != nominated:
            shared._fail("saved_graph_literal_selection_mismatch", "axis."+name)
        for part in ("candidates", "fragments"):
            if len(literal[part]) != len(nominated[part]):
                shared._fail("saved_graph_literal_selection_mismatch", "axis."+name)
            for saved,witness in zip(literal[part], nominated[part]):
                _check_witness(saved, witness, sources, actual_images, "axis."+name)
        available = all(w["canonical_locator"] is not None for part in ("candidates", "fragments") for w in literal[part])
        if literal["status"] == "parsed":
            if nominated["status"] != "exact" or not available or literal["raw_literal"] != nominated["candidates"][0]["quote"]:
                shared._fail("saved_graph_literal_mismatch", "axis."+name)
            witness = nominated["candidates"][0]
            qualification = "source_text_literal" if witness["kind"] == "text" else "episode_image_transcription"
            if literal["qualification"] != qualification:
                shared._fail("saved_graph_literal_mismatch", "axis."+name)
            if name != "unit":
                token = literal["raw_literal"].strip().replace("−", "-")
                if not graph_reader._LITERAL.fullmatch(literal["raw_literal"].strip()) or literal["exact_value"] != shared._rational(Fraction(token)):
                    shared._fail("saved_graph_tick_mismatch", "axis."+name)
        elif not available and literal["status"] != "dependency_unavailable" and nominated["status"] == "exact":
            shared._fail("saved_graph_literal_availability_mismatch", "axis."+name)
    scale = result["axis_scale"]
    if scale["selection"] != selected["axis"]["scale"] or len(scale["witnesses"]) != len(scale["selection"]["witnesses"]):
        shared._fail("saved_graph_scale_mismatch", "axis.scale")
    for saved,witness in zip(scale["witnesses"], scale["selection"]["witnesses"]):
        _check_witness(saved, witness, sources, actual_images, "axis.scale")
    if scale["support"] in ("literal_source_text", "episode_image_interpretation"):
        expected_support = "literal_source_text" if scale["selection"]["basis"] == "source_text_literal" else "episode_image_interpretation"
        if scale["support"] != expected_support:
            shared._fail("saved_graph_scale_mismatch", "axis.scale")
        if scale["selection"]["status"] != "known" or scale["effective_kind"] != scale["selection"]["kind"] or any(w["canonical_locator"] is None for w in scale["witnesses"]):
            shared._fail("saved_graph_scale_mismatch", "axis.scale")
        if scale["support"] == "literal_source_text" and any(graph_reader._SCALE_PHRASES.get(w["selection"]["quote"].strip().lower()) != scale["effective_kind"] for w in scale["witnesses"]):
            shared._fail("saved_graph_scale_literal_mismatch", "axis.scale")
    unit = result["measurement"]["unit"]
    literal = result["axis_literals"]["unit"]
    if unit["selection"] != selected["axis"]["unit"] or unit["raw_unit"] != literal["raw_literal"]:
        shared._fail("saved_graph_unit_mismatch", "axis.unit")
    if unit["status"] == "supported":
        parsed = shared._plain_unit(unit["raw_unit"])
        if parsed is None or parsed != (unit["canonical_unit"],shared._fraction(unit["exact_scale"])):
            shared._fail("saved_graph_unit_mismatch", "axis.unit")
        native = next((k for k in shared.RATE_UNITS if shared._plain_unit(k) == parsed), None)
        if native != unit["native_registry_unit"] or unit["witness"] != literal["candidates"][0]:
            shared._fail("saved_graph_unit_mismatch", "axis.unit")
    pixels = result["measurement"]["pixel_result"]
    spec = next(i for i in actual_images if i["image_id"] == selected["image_id"])
    if pixels["recipe"] != selected["bar_selection"] or pixels["terminal_edge"] != selected["terminal_edge"] or pixels["image_id"] != selected["image_id"]:
        shared._fail("saved_graph_recipe_mismatch", "pixels")
    if pixels["counter_module_sha256"] != _dependencies()["literature_controlled_response_figure_inputs.py"] or pixels["image_sha256"] != spec["byte_sha256"] or pixels["original_image_sha256"] != spec["original_byte_sha256"]:
        shared._fail("saved_graph_image_identity_mismatch", "pixels")
    recipe,edge = selected["bar_selection"],selected["terminal_edge"]
    roi = recipe["roi"]
    runs = pixels["qualifying_runs"]
    for i,run in enumerate(runs):
        if not roi["top"] <= run["top"] < run["bottom"] <= roi["bottom"] or run["bottom"]-run["top"] < recipe["minimum_run_rows"] or i and runs[i-1]["bottom"] >= run["top"]:
            shared._fail("saved_graph_runs_mismatch", "pixels.qualifying_runs")
    if pixels["mapped_roi"]:
        region = [roi[k] for k in ("left", "top", "right", "bottom")]
        if spec["mapping"]:
            ox,oy = spec["mapping"]["original_region"][:2]
            region = [region[0]+ox,region[1]+oy,region[2]+ox,region[3]+oy]
        wanted = {"kind":"image", "original_source_ref":spec["original_source_ref"], "original_artifact_ref":spec["original_artifact_ref"],
            "original_byte_sha256":spec["original_byte_sha256"], "region":region}
        if pixels["mapped_roi"] != wanted or pixels["image_size"] != {"width":spec["width"], "height":spec["height"]}:
            shared._fail("saved_graph_mapping_mismatch", "pixels")
    if pixels["pixel_edge"] is not None:
        if len(runs) != 1:
            shared._fail("saved_graph_edge_mismatch", "pixels")
        run = runs[0]
        clipped = run["top"] == roi["top"] if edge == "upper" else run["bottom"] == roi["bottom"]
        if clipped:
            shared._fail("saved_graph_terminal_clipping_mismatch", "pixels")
        tolerance = Fraction(recipe["edge_tolerance_pixels"])
        if edge == "upper":
            point,lo,hi = Fraction(run["top"])+Fraction(1,2), Fraction(run["top"])-tolerance, Fraction(run["top"]+1)+tolerance
        else:
            point,lo,hi = Fraction(run["bottom"])-Fraction(1,2), Fraction(run["bottom"]-1)-tolerance, Fraction(run["bottom"])+tolerance
        wanted = {"terminal_edge":edge, "nominal":shared._rational(point), "bounds":{"lower":shared._rational(lo),"upper":shared._rational(hi)}}
        if pixels["pixel_edge"] != wanted:
            shared._fail("saved_graph_edge_mismatch", "pixels")
    if pixels["status"] == "measured":
        if pixels["pixel_edge"] is None or scale["effective_kind"] != "linear" or scale["support"] not in ("literal_source_text", "episode_image_interpretation") or unit["status"] != "supported":
            shared._fail("saved_graph_calibration_mismatch", "pixels")
        p1,p2 = (Fraction(selected["axis"][k]["pixel"]) for k in ("first", "second"))
        v1,v2 = (shared._fraction(result["axis_literals"][k]["exact_value"]) for k in ("first", "second"))
        if p1 == p2 or v1 == v2 or not (0 <= lo <= hi < spec["height"]):
            shared._fail("saved_graph_calibration_mismatch", "pixels")
        slope = (v2-v1)/(p2-p1)
        axis = {"first_pixel":shared._rational(p1),"second_pixel":shared._rational(p2),
            "first_value":shared._rational(v1),"second_value":shared._rational(v2),"unit":unit["native_registry_unit"],"slope":shared._rational(slope)}
        ordinate = lambda p:v1+(p-p1)*slope
        lower,upper = sorted((ordinate(lo),ordinate(hi)))
        if pixels["axis"] != axis or pixels["native_ordinate"] != shared._rational(ordinate(point)) or pixels["native_bounds"] != {"lower":shared._rational(lower),"upper":shared._rational(upper)}:
            shared._fail("saved_graph_ordinate_mismatch", "pixels")
    measurement,projection = result["measurement"], result["operand_projection"]
    states = []
    if any(s["state"] == "unavailable" for s in result["sources"]) or any(w["authentication"] == "unavailable" for w in scale["witnesses"]):
        states.append("dependency_unavailable")
    states += [literal["status"] for literal in result["axis_literals"].values() if literal["status"] != "parsed"]
    if selected["axis"]["scale"]["status"] == "conflicting":
        states.append("conflicting")
    states.append("graph_digitized" if pixels["status"] == "measured" else pixels["status"])
    expected_status = next(status for status in ("dependency_unavailable","conflicting","ambiguous","unreadable","unsupported","graph_digitized") if status in states)
    if expected_status == "graph_digitized":
        try:
            graph_reader._finite_float(shared._fraction(pixels["native_ordinate"]))
            for side,direction in (("lower",-1),("upper",1)):
                graph_reader._outward(shared._fraction(pixels["native_bounds"][side]),direction)
        except OverflowError:
            expected_status = "unsupported"
    if measurement["reading_status"] != expected_status:
        shared._fail("saved_graph_status_mismatch", "measurement")
    expected_projection_status = "point" if expected_status == "graph_digitized" else "missing" if expected_status in ("dependency_unavailable","unreadable") else expected_status
    if projection["status"] != expected_projection_status or projection["approximate"] is not True or projection["unit"] != unit["native_registry_unit"]:
        shared._fail("saved_graph_projection_mismatch", "operand_projection")
    ordered_literals = [result["axis_literals"][name] for name in ("first","second","unit")]
    fragments = [w for literal in ordered_literals for w in literal["fragments"]]
    witnesses = [w for literal in ordered_literals for part in ("candidates", "fragments") for w in literal[part]] + scale["witnesses"]
    if measurement["selection"] != selected or measurement["fragments"] != fragments or measurement["graph_witnesses"] != witnesses or measurement["candidates"]:
        shared._fail("saved_graph_measurement_mismatch", "measurement")
    if projection["status"] == "point":
        if pixels["status"] != "measured" or measurement["reading_status"] != "graph_digitized":
            shared._fail("saved_graph_projection_mismatch", "measurement")
        native = shared._fraction(pixels["native_ordinate"])
        lower,upper = (shared._fraction(pixels["native_bounds"][s]) for s in ("lower","upper"))
        value = graph_reader._finite_float(native)
        interval = {"lower":min(graph_reader._outward(lower,-1),value), "upper":max(graph_reader._outward(upper,1),value)}
        expected = {"value":value,"threshold":None,"relation":"interval","approximate":True,"unit":unit["native_registry_unit"],"status":"point","origin":"graph_derived","digitization_interval":interval}
        if projection != expected:
            shared._fail("saved_graph_projection_mismatch", "operand_projection")
        identity_record = {"version":result["version"],"selection":result["selection"],"images":result["images"],
            "literals":result["axis_literals"],"scale":scale,"unit":unit,"pixels":pixels}
        expected_id = "controlled_response_graph_" + hashlib.sha256(json.dumps(identity_record,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()
        if measurement["source_observation_id"] != expected_id:
            shared._fail("saved_graph_identity_mismatch", "measurement.source_observation_id")
        display = {"value":None,"threshold":None,"unit":unit["canonical_unit"],"relation":"none","approximate":True,"diagnostics":[]}
        try:
            display["value"] = graph_reader._finite_float(native*shared._fraction(unit["exact_scale"]))
        except OverflowError:
            display["diagnostics"] = [graph_reader._diagnostic("graph_canonical_display_range","measurement.canonical_display")]
        else:
            display["relation"] = "eq"
        if measurement["canonical_display"] != display:
            shared._fail("saved_graph_display_mismatch", "measurement.canonical_display")
    elif any(projection[k] is not None for k in ("value","threshold","digitization_interval")) or projection["relation"] != "none" or measurement["source_observation_id"] is not None:
        shared._fail("saved_graph_projection_mismatch", "operand_projection")
    return _graph_reading(None, selected, result)
