from __future__ import annotations
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_driver import _absolute_directory, _validate_identity
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_preparation_contracts import compile_native_hmmer_preparation_job, validate_native_hmmer_preparation_requested_job
PLAN_VERSION = 'native_hmmer_preparation_run_plan_v1'
OWNER_NAME = '.native-hmmer-preparation-owner.json'
MODEL_STAGING_PATH = 'inputs/models.hmm'
SSI_STAGING_PATH = 'inputs/models.hmm.ssi'
_PREFIX = 'native_hmmer_preparation_'
_FAILURES = {'invalid_alimask_input': ({'preflight'}, {'reason': 'preflight_reason'}), 'unsupported_alimask_model_map': ({'preflight'}, {'reason': 'preflight_reason'}), 'unsafe_alimask_range': ({'preflight'}, {'start': 'uint', 'end': 'uint', 'last_match': 'uint'}), 'invalid_exactmatch_queries': ({'preflight'}, {'ordinal': 'uint', 'reason': 'preflight_reason'}), 'incompatible_fm_abi': ({'preflight'}, {'reason': 'preflight_reason'}), 'invalid_fm_database': ({'preflight'}, {'reason': 'preflight_reason', 'issue_codes': 'fm_issue_codes'}), 'invalid_model_format': ({'preflight'}, {'reason': 'preflight_reason'}), 'source_binding_digest_mismatch': ({'preflight'}, {'reason': 'preflight_reason'}), 'software_digest_mismatch': ({'software'}, {}), 'software_not_executable': ({'software'}, {}), 'software_unavailable': ({'software'}, {'reason': 'reason', 'errno': 'errno'}), 'input_missing': ({'inputs'}, {'ordinal': 'uint'}), 'input_io_error': ({'inputs'}, {'ordinal': 'uint', 'errno': 'errno'}), 'input_not_regular': ({'inputs'}, {'ordinal': 'uint'}), 'input_identity_mismatch': ({'inputs'}, {'ordinal': 'uint'}), 'working_copy_not_staged': ({'staging'}, {'operand_ordinal': 'uint', 'relative_path': 'path'}), 'working_copy_io_error': ({'staging'}, {'operand_ordinal': 'uint', 'relative_path': 'path', 'errno': 'errno'}), 'working_copy_identity_mismatch': ({'staging'}, {'operand_ordinal': 'uint', 'relative_path': 'path'}), 'scratch_limit': ({'staging', 'execution'}, {'observed_bytes': 'uint', 'limit_bytes': 'uint', 'relative_path': 'nullable_path'}), 'nonzero_returncode': ({'execution'}, {'returncode': 'int'}), 'command_unavailable': ({'execution'}, {'errno': 'errno'}), 'immutable_input_changed': ({'execution'}, {'ordinal': 'uint'}), 'immutable_working_copy_changed': ({'execution'}, {'operand_ordinal': 'uint', 'relative_path': 'path'}), 'input_final_unavailable': ({'inputs', 'execution'}, {'ordinal': 'uint', 'reason': 'reason', 'errno': 'errno'}), 'working_copy_final_unavailable': ({'staging', 'execution'}, {'operand_ordinal': 'uint', 'relative_path': 'path', 'reason': 'reason', 'errno': 'errno'}), 'missing_output': ({'outputs'}, {'relative_path': 'path'}), 'invalid_output': ({'outputs'}, {'relative_path': 'path', 'reason': 'reason', 'errno': 'errno'})}
FAILURE_CODES = frozenset((_PREFIX + code for code in _FAILURES))
PREFLIGHT_REASONS = frozenset({'alignment_format_not_established', 'malformed_stockholm', 'multiple_alignments', 'rf_required', 'empty_model_map', 'weighted_map_not_established', 'pb_subsampling_not_established', 'map_configuration_unavailable', 'explicit_alphabet_required', 'unsupported_alignment_symbols', 'invalid_weights', 'range_outside_alignment', 'query_requires_final_lf', 'query_empty', 'query_exceeds_254_symbols', 'query_requires_literal_canonical_dna', 'producer_byte_order_mismatch', 'producer_integer_width_mismatch', 'invalid_fm_framing', 'dna_only_reader', 'fm_reader_header_incompatible', 'invalid_fm_arrays', 'invalid_fm_segments', 'invalid_fm_ambiguities', 'source_sha256_order_mismatch', 'wrong_model_signature', 'no_model_bytes', 'malformed_alignment', 'alphabet_undetermined', 'alphabet_source_semantics_unestablished', 'decoder_source_semantics_unestablished'})
PREFLIGHT_FAILURE_CONTEXT = {'invalid_alimask_input': {'role': 'alignment', 'programs': frozenset({'alimask'}), 'reasons': frozenset({'malformed_stockholm', 'malformed_alignment', 'multiple_alignments', 'invalid_weights', 'range_outside_alignment', 'empty_model_map'})}, 'unsupported_alimask_model_map': {'role': 'alignment', 'programs': frozenset({'alimask'}), 'reasons': frozenset({'alignment_format_not_established', 'rf_required', 'weighted_map_not_established', 'pb_subsampling_not_established', 'map_configuration_unavailable', 'explicit_alphabet_required', 'unsupported_alignment_symbols', 'invalid_weights', 'alphabet_undetermined', 'alphabet_source_semantics_unestablished', 'decoder_source_semantics_unestablished'})}, 'unsafe_alimask_range': {'role': 'alignment', 'programs': frozenset({'alimask'}), 'reasons': None}, 'invalid_exactmatch_queries': {'role': 'queries', 'programs': frozenset({'hmmerfm-exactmatch'}), 'reasons': frozenset({'query_requires_final_lf', 'query_empty', 'query_exceeds_254_symbols', 'query_requires_literal_canonical_dna'})}, 'incompatible_fm_abi': {'role': 'fm_database', 'programs': frozenset({'hmmerfm-exactmatch'}), 'reasons': frozenset({'producer_byte_order_mismatch', 'producer_integer_width_mismatch'})}, 'invalid_fm_database': {'role': 'fm_database', 'programs': frozenset({'hmmerfm-exactmatch'}), 'reasons': frozenset({'invalid_fm_framing', 'dna_only_reader', 'fm_reader_header_incompatible'})}, 'invalid_model_format': {'role': 'models', 'programs': frozenset({'hmmconvert', 'hmmemit', 'hmmfetch', 'hmmpress', 'hmmsim', 'hmmstat'}), 'reasons': frozenset({'wrong_model_signature', 'no_model_bytes'})}, 'source_binding_digest_mismatch': {'role': 'source_sequences', 'programs': frozenset({'hmmerfm-exactmatch'}), 'reasons': frozenset({'source_sha256_order_mismatch'})}}
NATIVE_ABI_FIELDS = frozenset({'byte_order', 'float_format', 'bytes_per_float', 'uint8_bytes', 'uint16_bytes', 'uint32_bytes', 'uint64_bytes', 'int32_bytes', 'c_int_bytes', 'c_long_bytes', 'c_float_bytes'})

def _error(reason):
    raise ValueError(_PREFIX + reason)

def _staged_relative(operand):
    if operand['role'] == 'models':
        return MODEL_STAGING_PATH
    if operand['role'] == 'ssi':
        return SSI_STAGING_PATH
    return 'inputs/' + operand['role'] + '/' + str(operand['ordinal'])

def _compile(job, root):
    paths = {}
    for row in job['operands']:
        paths.setdefault(row['role'], []).append(str(root / _staged_relative(row)))
    return compile_native_hmmer_preparation_job(job, input_paths=paths, output_directory=str(root))

def validate_preparation_plan(value):
    """Validate the separate preparation plan; perform no native execution."""
    plan = finite_json_copy(value)
    if type(plan) is not dict or set(plan) != {'version', 'identity', 'requested_job', 'attempt_directory', 'policy'} or plan['version'] != PLAN_VERSION:
        _error('run_plan_required')
    request = validate_native_hmmer_preparation_requested_job(plan['requested_job'])
    _validate_identity(plan['identity'], request)
    policy = plan['policy']
    if type(policy) is not dict or set(policy) != {'memory_bytes', 'scratch_bytes'}:
        _error('explicit_policy_required')
    LocalJobPolicy(**policy)
    root = _absolute_directory(plan['attempt_directory'])
    job = request['native_hmmer_preparation']
    if any((Path(row['path']).is_relative_to(root) for row in job['operands'])):
        _error('supplied_operand_inside_attempt')
    if Path(job['software']['executable']).is_relative_to(root):
        _error('supplied_software_inside_attempt')
    _compile(job, root)
    return plan
