"""Closed pure contracts for the two RNA scientific operations.

Validation is deterministic data validation, not a native-execution or biological
acceptance gate. No validator imports ViennaRNA or accesses files, Store, network,
subprocesses or a model service. Original invalid scientific strings remain valid
containers so they can be retained with specific input issues.
"""
from __future__ import annotations
from copy import deepcopy
from functools import wraps
import math
COORDINATE_SYSTEM = 'zero_based_sequence_indices_and_half_open_intervals'
MODES = ('mfe_prediction', 'supplied_features')
OPERATIONS = dict(zip(MODES, ('predict_rna_secondary_structure', 'analyze_rna_secondary_structure_features')))
RNA_SYMBOLS = 'ACGURYSWKMBDHVN'
PAIR_TYPES = tuple((a + b for a in 'ACGU' for b in 'ACGU'))
CELL_STATES = frozenset(('present', 'not_requested', 'not_produced', 'missing_input', 'invalid_input', 'incompatible', 'failed', 'truncated'))
UNCERTAINTY_REASON = 'selected_algorithm_does_not_produce_uncertainty'
RNA_ISSUE_MEANINGS = {'not_requested': 'The selected operation did not request this quantity.', UNCERTAINTY_REASON: 'Neither selected single-structure algorithm produces this uncertainty.', 'no_sequence_supplied': 'The optional original sequence is null.', 'zero_pair_denominator': 'The valid topology has zero pairs.', 'zero_stem_denominator': 'The valid topology has zero stems.', 'zero_closed_loop_denominator': 'The valid topology has zero closed loops.', 'zero_unambiguous_pair_denominator': 'No pair has two unambiguous RNA bases.', 'normalization_not_requested': 'The caller selected no energy normalization.', 'native_metadata_not_retained': 'The recorded legacy output did not retain native settings/version.', 'rna_empty_sequence': 'A supplied sequence is empty, rather than absent.', 'rna_empty_structure': 'The supplied structure is empty.', 'rna_invalid_sequence_symbol': 'A sequence symbol is outside the declared normalized alphabet.', 'rna_sequence_structure_length_mismatch': 'Sequence and structure lengths differ.', 'rna_unbalanced_structure': 'At least one opening or closing bracket has no partner.', 'rna_mismatched_bracket': 'A closing bracket has an incompatible opening token.', 'rna_crossing_pairs_unsupported': 'The balanced typed bracket pairs cross; no nested subset is emitted.', 'rna_native_dependency_missing': 'The selected native dependency was unavailable.', 'rna_software_identity_mismatch': 'The actual interpreter, worker or native import identity conflicts with an explicitly bound Software field.', 'rna_native_api_unsupported': 'The actual native API lacks a required operation or field.', 'rna_parameter_load_failed': 'The selected native parameter load/save operation failed.', 'rna_native_failed': 'The selected native operation failed.', 'rna_nonfinite_energy': 'The recorded energy was not a finite number.', 'rna_energy_structure_mismatch': 'A native energy is associated with a different structure/model.', 'rna_input_identity_mismatch': 'Supplied or recorded input identities/content disagree or are unavailable.', 'rna_topology_table_mismatch': 'Recorded topology disagrees with exact reconstruction.', 'rna_output_truncated': 'The declared output ends inside an incomplete serialized value.', 'rna_requested_metric_unavailable': 'A requested metric has no available value.', 'rna_subject_binding_conflict': 'Supplied subject binding and original binding disagree.', 'rna_invalid_native_schema': 'Native bytes or their container do not satisfy the declared format.', 'rna_invalid_parameter_schema': 'Calculator/model parameter container or operands are invalid.', 'rna_model_snapshot_missing': 'A required retained effective model snapshot is absent.', 'rna_native_result_missing': 'The native artifact is actually absent, not an empty file.', 'rna_native_result_incompatible': 'Recorded native fields cannot consistently describe the selected operation.', 'rna_requested_row_missing': 'The selected saved row does not exist.', 'rna_zero_length_denominator': 'A known zero nucleotide denominator cannot be divided.', 'rna_capture_unavailable': 'A selected original artifact could not be acquired.', 'rna_capture_digest_mismatch': 'Acquired bytes disagree with the original digest/size.', 'rna_original_attempt_mismatch': 'A receipt or artifact names another original attempt.', 'rna_unsealed_native_attempt': 'The original attempt is not sealed.', 'rna_unknown_native_setting': 'A requested native setting is not in the closed contract.', 'rna_output_path_conflict': 'Declared output paths conflict.', 'rna_region_side_not_defined': 'This region kind has no two-side definition.', 'rna_invalid_structure_symbol': 'A structure character is outside .()[]{}.', 'rna_invalid_input_schema': 'The input container, primitive types or coordinate convention is invalid.', 'rna_invalid_sheet_schema': 'The saved sheet has invalid or contradictory fields.', 'rna_invalid_component_schema': 'A saved component disagrees with its sheet/parameters or closed cell schema.', 'rna_legacy_context_missing': 'The selected legacy parser requires an independently supplied original sequence.'}
RNA_ISSUE_CODES = frozenset(RNA_ISSUE_MEANINGS)
TOPOLOGY_METRICS = ('n_nt', 'pair_count', 'paired_nt', 'unpaired_nt', 'paired_fraction', 'unpaired_fraction', 'mean_pair_span_nt', 'stem_count', 'longest_stem_pairs', 'mean_stem_pairs', 'stack_count', 'long_stem_count', 'long_stem_fraction', 'hairpin_count', 'bulge_count', 'internal_loop_count', 'multibranch_count', 'loop_mean_unpaired_nt', 'loop_max_unpaired_nt', 'external_unpaired_nt')
COMPOSITION_METRICS = ('unambiguous_pair_count', 'ambiguous_pair_count', 'accepted_pair_count', 'accepted_pair_fraction', *('pair_count_' + pair for pair in PAIR_TYPES))
ENERGY_METRICS = ('mfe_kcal_mol', 'evaluated_energy_kcal_mol', 'mfe_per_nt', 'evaluated_energy_per_nt')
ROW_METRICS = {'summary': TOPOLOGY_METRICS + COMPOSITION_METRICS + ENERGY_METRICS, 'pairs': ('pair_span_nt',), 'stems': ('stem_length_pairs', 'stack_count'), 'regions': ('loop_unpaired_nt', 'branch_count', 'five_prime_unpaired_nt', 'three_prime_unpaired_nt')}
METRIC_UNITS = {'n_nt': 'nt', 'pair_count': 'pairs', 'paired_nt': 'nt', 'unpaired_nt': 'nt', 'paired_fraction': 'dimensionless', 'unpaired_fraction': 'dimensionless', 'mean_pair_span_nt': 'nt', 'stem_count': 'stems', 'longest_stem_pairs': 'pairs', 'mean_stem_pairs': 'pairs/stem', 'stack_count': 'stacks', 'long_stem_count': 'stems', 'long_stem_fraction': 'dimensionless', 'hairpin_count': 'regions', 'bulge_count': 'regions', 'internal_loop_count': 'regions', 'multibranch_count': 'regions', 'loop_mean_unpaired_nt': 'nt', 'loop_max_unpaired_nt': 'nt', 'external_unpaired_nt': 'nt', 'unambiguous_pair_count': 'pairs', 'ambiguous_pair_count': 'pairs', 'accepted_pair_count': 'pairs', 'accepted_pair_fraction': 'dimensionless', **{'pair_count_' + p: 'pairs' for p in PAIR_TYPES}, 'mfe_kcal_mol': 'kcal/mol', 'evaluated_energy_kcal_mol': 'kcal/mol', 'mfe_per_nt': 'kcal/mol/nt', 'evaluated_energy_per_nt': 'kcal/mol/nt', 'pair_span_nt': 'nt', 'stem_length_pairs': 'pairs', 'loop_unpaired_nt': 'nt', 'branch_count': 'pairs', 'five_prime_unpaired_nt': 'nt', 'three_prime_unpaired_nt': 'nt'}

def _require(condition, code='rna_invalid_native_schema'):
    if not condition:
        raise ValueError(code)

def _object(value, keys, code='rna_invalid_native_schema'):
    _require(type(value) is dict and set(value) == set(keys), code)

def _count(value):
    return type(value) is int and value >= 0

def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))

def _contract_errors(code):
    """Normalize malformed container failures to the declared validator error."""

    def decorate(function):

        @wraps(function)
        def checked(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
                raise ValueError(code) from error
        return checked
    return decorate

@_contract_errors('rna_invalid_parameter_schema')
def validate_rna_parameters(value: dict) -> dict:
    code = 'rna_invalid_parameter_schema'
    _object(value, ('schema', 'topology', 'pair_composition', 'energy'), code)
    _require(value['schema'] == 'rna_calculation_parameters_v1', code)
    _object(value['topology'], ('long_stem_min_pairs', 'include_exterior_in_loop_size_statistics'), code)
    _require(type(value['topology']['long_stem_min_pairs']) is int and value['topology']['long_stem_min_pairs'] >= 1, code)
    _require(value['topology']['include_exterior_in_loop_size_statistics'] is False, code)
    _object(value['pair_composition'], ('accepted_ordered_pair_types', 'denominator'), code)
    accepted = value['pair_composition']['accepted_ordered_pair_types']
    _require(type(accepted) is list and all((type(p) is str and p in PAIR_TYPES for p in accepted)), code)
    _require(len(accepted) == len(set(accepted)) and value['pair_composition']['denominator'] == 'unambiguous_pairs', code)
    _object(value['energy'], ('normalization',), code)
    _require(value['energy']['normalization'] in ('none', 'per_nt'), code)
    return deepcopy(value)
_MODEL_FIELDS = ('temperature_c', 'dangles', 'noLP', 'noGU', 'noGUclosure', 'special_hp', 'logML', 'min_loop_size', 'max_bp_span', 'circ', 'gquad')

def _model_settings(value):
    code = 'rna_invalid_parameter_schema'
    _require(_number(value['temperature_c']) and value['temperature_c'] > -273.15, code)
    _require(type(value['dangles']) is int and value['dangles'] in range(4), code)
    _require(all((type(value[k]) is bool for k in ('noLP', 'noGU', 'noGUclosure', 'special_hp', 'logML'))), code)
    _require(_count(value['min_loop_size']), code)
    _require(type(value['max_bp_span']) is int and (value['max_bp_span'] == -1 or value['max_bp_span'] >= 1), code)
    _require(value['circ'] is False and value['gquad'] is False, code)

@_contract_errors('rna_invalid_parameter_schema')
def validate_rna_model_spec_shape(value: dict) -> dict:
    """Check selected model shape only; no parameter file or native API is opened."""
    code = 'rna_invalid_parameter_schema'
    _object(value, ('schema', *_MODEL_FIELDS, 'hard_constraints', 'soft_constraints', 'parameters'), code)
    _require(value['schema'] == 'vienna_rna_model_spec_v1', code)
    _model_settings(value)
    _require(value['hard_constraints'] is None and value['soft_constraints'] is None, code)
    _object(value['parameters'], ('kind', 'operand_role'), code)
    _require(value['parameters'] in ({'kind': 'turner2004', 'operand_role': None}, {'kind': 'supplied_parameter_file', 'operand_role': 'model_parameter_input'}), code)
    return deepcopy(value)
