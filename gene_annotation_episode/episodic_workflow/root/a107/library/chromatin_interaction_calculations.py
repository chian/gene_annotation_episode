"""A107 chromatin interaction calculations."""


from __future__ import annotations
from copy import deepcopy
import math
from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_interaction_contracts import chromatin_record_digest
_MAX = float.fromhex('0x1.fffffffffffffp+1023')

def _require(condition, code):
    if not condition:
        raise ValueError('chromatin_' + code)

def _state(reason):
    if reason in ('zero_denominator', 'zero_variance', 'no_valid_distance_pairs', 'no_full_windows', 'same_bin_not_evaluated', 'below_minimum_separation'):
        return 'undefined'
    if reason in ('reference_conflict', 'incompatible_variable_bins', 'incompatible_matrix_symmetry'):
        return 'incompatible'
    if reason in ('native_output_partial', 'incomplete_comparison_population', 'incomplete_window', 'boundary_neighbor_unavailable'):
        return 'truncated'
    if reason in ('native_value_nonfinite', 'native_value_negative', 'normalization_weight_invalid', 'duplicate_native_pixel', 'numerical_overflow'):
        return 'failed'
    return 'missing'

def _measurement(key, unit, source_unit, value=None, *, reason=None, state=None, numerator=None, denominator=None):
    if value is not None and (not math.isfinite(value) or abs(value) > _MAX):
        value, reason, state = (None, 'numerical_overflow', 'failed')
    if numerator is not None and (not math.isfinite(numerator) or abs(numerator) > _MAX):
        numerator = None
    if denominator is not None and (not math.isfinite(denominator) or abs(denominator) > _MAX):
        denominator = None
    return {'value': value, 'state': state or (_state(reason) if reason else 'derived'), 'unit': {'kind': unit, 'source_unit': source_unit if 'contact' in unit and unit != 'contact_pairs' else None}, 'reason': reason, 'population_key': key, 'numerator': numerator, 'denominator': denominator, 'uncertainty': {'kind': 'not_measured', 'value': None, 'unit': None}}

def _failure(sheet, key, reason, *, pair_key=None, field_path=None, stage='calculation'):
    requirements = {'zero_denominator': 'positive_denominator', 'normalization_missing': 'selected_weight_vector', 'normalization_masked_bin': 'finite_positive_weights', 'normalization_weight_invalid': 'finite_positive_weights', 'reference_conflict': 'compatible_reference', 'incompatible_variable_bins': 'fixed_bin_grid', 'incompatible_matrix_symmetry': 'valid_native_structure', 'native_value_negative': 'finite_nonnegative_contact_values', 'native_value_nonfinite': 'finite_nonnegative_contact_values', 'numerical_overflow': 'finite_numerical_result', 'duplicate_native_pixel': 'valid_native_structure', 'incomplete_window': 'complete_window', 'boundary_neighbor_unavailable': 'complete_window', 'requested_field_unavailable': 'requested_selected_field'}
    return {'code': reason, 'stage': stage, 'input_key': sheet['request']['contact']['input_key'], 'population_key': key, 'element_key': None, 'pair_key': pair_key, 'artifact_ref': None, 'locator': None, 'field_path': field_path, 'partial_artifact_refs': [], 'requirement': requirements.get(reason, 'complete_population')}

def _unique_failures(rows):
    result, seen = ([], set())
    for row in rows:
        identity = chromatin_record_digest(row)
        if identity not in seen:
            result.append(deepcopy(row))
            seen.add(identity)
    return result

def _table_identities(sheet):
    return [deepcopy(row['file']) for row in sheet['data_tables'] if row['file'] is not None]

def _source_keys(sheet, key):
    return [row['table_key'] for row in sheet['data_tables'] if row['population_key'] == key and row['file'] is not None]

def _pair_population_known(sheet, population):
    return sheet['elements'] is not None and sheet['elements']['extent'] == 'complete' and (population['read_evidence']['axes_extent'] == 'complete') and all((row['membership'] != 'unresolved' for row in population['element_anchor_rows'])) and (not any((f['code'] == 'element_assignment_missing' for f in sheet['elements']['failures'])))
