"""Source-free TF input decoding and retained Biopython score measurements.

Native model construction/scoring and all I/O belong to the selected producer.
Original File locators are distinct from genuine captured native locations.
"""
from copy import deepcopy
import hashlib
import json
import math
import re
import struct
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.bvbrc_alignment_values import validate_numeric_cell
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import phylogeny_calculation_contracts as locations
NUMERIC_CONVENTION = 'numpy_array_compare_pythonfloat_scalar_relative_v1'
COMPONENTS_VERSION = 'tf_binding_components_v1'
RETURN_VERSION = 'tf_binding_return_v1'
_BASES = 'ACGT'
_HEX = re.compile('[a-f0-9]{64}\\Z')

def _need(condition, code):
    if not condition:
        raise ValueError('tf_binding_' + code)

def _shape(value, keys, code='shape_invalid'):
    _need(type(value) is dict and set(value) == set(keys), code)

def _text(value, *, nullable=False):
    _need(nullable and value is None or (type(value) is str and bool(value)), 'text_invalid')

def _integer(value, *, nullable=False):
    _need(nullable and value is None or (type(value) is int and value >= 0), 'integer_invalid')

def _finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))

def _hash(value):
    _need(type(value) is str and _HEX.fullmatch(value) is not None, 'digest_invalid')

def _same(first, second):
    return json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)

def _id(kind, values):
    raw = json.dumps(values, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return 'tf_' + kind + '_' + hashlib.sha256(raw).hexdigest()

def _issues(values):
    _need(type(values) is list, 'issues_invalid')
    for value in values:
        _shape(value, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
        _text(value['code'])
        _need(value['phase'] in ('custody', 'prepare', 'transport', 'native_decode', 'association', 'publication', 'recovery', 'return'), 'issue_phase_invalid')
        _need(type(value['path']) is str and (not value['path'] or value['path'].startswith('/')), 'issue_path_invalid')
        _need(value['severity'] in ('error', 'qualification') and type(value['evidence_refs']) is list, 'issue_invalid')
        for ref in value['evidence_refs']:
            _text(ref)

def _selection(value):
    _need(type(value) is dict, 'scan_selection_invalid')
    if value.get('mode') == 'all_supplied_occurrences_both_strands':
        _shape(value, ('mode',))
    else:
        _shape(value, ('mode', 'requests'))
        _need(value['mode'] == 'explicit' and type(value['requests']) is list, 'scan_selection_invalid')
        for row in value['requests']:
            _shape(row, ('sequence_input_id', 'sequence_record_ordinal_0based', 'matrix_input_id', 'matrix_record_ordinal_0based', 'strands'))
            _text(row['sequence_input_id'])
            _text(row['matrix_input_id'])
            _integer(row['sequence_record_ordinal_0based'])
            _integer(row['matrix_record_ordinal_0based'])
            _need(type(row['strands']) is list and bool(row['strands']) and (len(set(row['strands'])) == len(row['strands'])) and all((v in ('+', '-') for v in row['strands'])), 'strand_selection_invalid')
    return deepcopy(value)

def _parameters(value):
    _shape(value, ('background', 'pseudocounts'))
    for field in ('background', 'pseudocounts'):
        _shape(value[field], _BASES)
        _need(all((_finite(v) and v >= 0 for v in value[field].values())), 'parameter_number_invalid')

def _spec(value):
    _shape(value, ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id', 'strand', 'possible_positions'))
    for field in ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id'):
        _text(value[field])
    _need(value['strand'] in ('+', '-'), 'strand_invalid')
    _integer(value['possible_positions'], nullable=True)

def _capture(value, retained_size):
    _shape(value, ('state', 'byte_start_0based', 'byte_end_0based_exclusive', 'original_size_bytes'))
    _need(value['state'] in ('complete', 'truncated', 'missing') and type(value['byte_start_0based']) is int and (value['byte_start_0based'] == 0), 'capture_invalid')
    _integer(value['byte_end_0based_exclusive'])
    _integer(value['original_size_bytes'], nullable=True)
    _need(value['byte_end_0based_exclusive'] == retained_size, 'capture_size_conflict')
    if value['state'] == 'missing':
        _need(retained_size == 0, 'missing_capture_has_bytes')
    _need(value['original_size_bytes'] is None or value['original_size_bytes'] >= retained_size, 'capture_size_conflict')
    if value['state'] == 'complete':
        _need(value['original_size_bytes'] in (None, retained_size), 'capture_size_conflict')

def validate_tf_binding_selection(value):
    _shape(value, ('version', 'scan_ids', 'raw_threshold', 'offset', 'limit'))
    _need(value['version'] == 'tf_binding_selection_v1' and type(value['scan_ids']) is list, 'selection_invalid')
    for scan_id in value['scan_ids']:
        _text(scan_id)
    _need(len(set(value['scan_ids'])) == len(value['scan_ids']), 'duplicate_selected_scan')
    _need(_finite(value['raw_threshold']), 'threshold_not_finite')
    _integer(value['offset'])
    _integer(value['limit'])
    result = deepcopy(value)
    try:
        result['raw_threshold'] = float(result['raw_threshold'])
    except (OverflowError, ValueError) as error:
        raise ValueError('tf_binding_threshold_not_finite') from error
    _need(math.isfinite(result['raw_threshold']), 'threshold_not_finite')
    return result

def _validate_extended(value, *, relative=False, public=False):
    fields = ('classification', 'value', 'dtype', 'byte_order', 'bits_hex', 'unit', 'origin', 'state', 'reason_code')
    if not public:
        fields += ('location',)
    if relative:
        fields += ('relative_normalization_id',) + (() if public else ('operand_evidence',))
    _shape(value, fields)
    _need(value['dtype'] in ('float32', 'float64') and value['byte_order'] in ('little', 'big'), 'extended_dtype_invalid')
    _need(type(value['bits_hex']) is str, 'extended_bits_invalid')
    try:
        raw = bytes.fromhex(value['bits_hex'])
    except ValueError as error:
        raise ValueError('tf_binding_extended_bits_invalid') from error
    size = 4 if value['dtype'] == 'float32' else 8
    _need(len(raw) == size and raw.hex() == value['bits_hex'], 'extended_bits_invalid')
    observed, = struct.unpack(('<' if value['byte_order'] == 'little' else '>') + ('f' if size == 4 else 'd'), raw)
    classification = 'nan' if math.isnan(observed) else 'positive_infinity' if observed == math.inf else 'negative_infinity' if observed == -math.inf else 'finite'
    _need(value['classification'] == classification, 'extended_classification_conflict')
    if classification == 'finite':
        _need(_finite(value['value']) and struct.pack('>d', float(value['value'])) == struct.pack('>d', observed), 'extended_value_conflict')
    else:
        _need(value['value'] is None, 'extended_nonfinite_value')
    _need(value['state'] in ('available', 'undefined') and (classification != 'nan' or value['state'] == 'undefined'), 'extended_state_invalid')
    _text(value['reason_code'], nullable=True)
    _need(value['origin'] in ('native_observation', 'calculated') and value['unit'] in ('bits', 'dimensionless'), 'extended_meaning_invalid')
    if not public and value['location'] is not None:
        locations.location(value['location'])
    if relative:
        _text(value['relative_normalization_id'])
        _need(value['unit'] == 'dimensionless' and value['origin'] == 'calculated' and (public or value['location'] is None), 'relative_meaning_invalid')
        if not public:
            evidence = value['operand_evidence']
            _shape(evidence, ('score_location', 'score_operand_dtype', 'normalization_id'))
            _need(evidence['score_operand_dtype'] == 'numpy_float32' and evidence['normalization_id'] == value['relative_normalization_id'], 'relative_operand_conflict')
            if evidence['score_location'] is not None:
                locations.location(evidence['score_location'])

def _validate_tf_binding_values(value, *, public=False):
    """One numerical/cross-field authority for stored and public records."""
    _shape(value, (() if public else ('version',)) + ('status', 'parameters', 'selection', 'execution', 'numeric_authority', 'available_scans', 'relative_normalizations', 'inputs', 'sequences', 'matrices', 'selected_scans', 'totals', 'raw_threshold_matches', 'hits', 'issues'))
    _need((public or value['version'] == COMPONENTS_VERSION) and value['status'] in ('complete', 'partial', 'unavailable'), 'components_version_invalid')
    _parameters(value['parameters'])
    selection = validate_tf_binding_selection(value['selection'])
    if public:
        _need(type(value['issues']) is list, 'issues_invalid')
        for issue in value['issues']:
            _shape(issue, ('code', 'phase', 'path', 'severity'))
        _issues([{**issue, 'evidence_refs': []} for issue in value['issues']])
    else:
        _issues(value['issues'])
    _shape(value['execution'], ('native_outcome', 'returncode'))
    _need(value['execution']['native_outcome'] in ('succeeded', 'failed', 'not_run', 'unknown') and value['execution']['returncode'] is None, 'components_execution_invalid')
    authority = value['numeric_authority']
    _shape(authority, ('convention', 'numpy_version', 'biopython_version', 'threshold_operand', 'threshold_binary64_hex', 'comparison', 'relative', 'relative_bounds'))
    _text(authority['numpy_version'])
    _text(authority['biopython_version'])
    _need(authority['convention'] == NUMERIC_CONVENTION and authority['threshold_operand'] == 'python_float' and (authority['threshold_binary64_hex'] == struct.pack('>d', selection['raw_threshold']).hex()) and (authority['comparison'] == 'float32_ndarray_ge_python_float') and (authority['relative'] == 'numpy_float32_scalar_minus_python_float_div_python_float') and (authority['relative_bounds'] == 'forward_pssm_bounds_for_both_strands'), 'numeric_authority_conflict')
    for key in ('inputs', 'sequences', 'matrices', 'available_scans', 'selected_scans', 'relative_normalizations', 'raw_threshold_matches', 'hits'):
        _need(type(value[key]) is list, 'components_rows_invalid')
    inputs = {}
    for row in value['inputs']:
        _shape(row, ('input_id', 'role', 'format', 'artifact_id', 'sha256', 'size_bytes', 'upstream_source_id', 'capture'))
        _text(row['input_id'])
        _hash(row['sha256'])
        _integer(row['size_bytes'])
        _text(row['upstream_source_id'], nullable=True)
        _need(row['role'] in ('dna', 'matrix') and row['format'] in (('fasta', 'raw_dna') if row['role'] == 'dna' else ('jaspar_json', 'jaspar_pfm', 'acgt_count_json')), 'input_format_invalid')
        _need(row['artifact_id'] == 'artifact_' + row['sha256'] and row['input_id'] not in inputs, 'component_input_identity_conflict')
        _capture(row['capture'], 0 if row['capture']['state'] == 'missing' else row['size_bytes'])
        inputs[row['input_id']] = row
    catalogs = []
    for field, kind in (('sequences', 'sequence'), ('matrices', 'matrix')):
        catalog = {}
        for row in value[field]:
            fields = ('sequence_id', 'input_id', 'record_ordinal_0based', 'identifier', 'length', 'state') if kind == 'sequence' else ('matrix_occurrence_id', 'model_id', 'input_id', 'record_ordinal_0based', 'native_matrix_id', 'name', 'length', 'state')
            _shape(row, fields)
            _integer(row['record_ordinal_0based'])
            _integer(row['length'], nullable=True)
            _need(row['input_id'] in inputs and inputs[row['input_id']]['role'] == ('dna' if kind == 'sequence' else 'matrix'), 'component_occurrence_input_conflict')
            _need(row['state'] in ('available', 'unavailable') and (row['state'] != 'available' or row['length'] is not None), 'component_occurrence_state_invalid')
            for key in ('identifier',) if kind == 'sequence' else ('native_matrix_id', 'name'):
                _need(row[key] is None or type(row[key]) is str, 'component_occurrence_label_invalid')
            key = _id(kind, [row['input_id'], inputs[row['input_id']]['sha256'], row['record_ordinal_0based']])
            _need(row['sequence_id' if kind == 'sequence' else 'matrix_occurrence_id'] == key and key not in catalog, 'component_occurrence_identity_conflict')
            if kind == 'matrix':
                _need(row['model_id'] == _id('model', [key]), 'component_model_identity_conflict')
            catalog[key] = row
        catalogs.append(catalog)
    sequences, matrices = catalogs
    scans = {}
    for row in value['available_scans']:
        _shape(row, ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id', 'strand', 'possible_positions', 'coverage'))
        _spec({k: row[k] for k in row if k != 'coverage'})
        _need(row['sequence_id'] in sequences and row['matrix_occurrence_id'] in matrices and (row['scan_id'] not in scans), 'component_scan_identity_conflict')
        matrix = matrices[row['matrix_occurrence_id']]
        _need(row['model_id'] == matrix['model_id'] and row['scan_id'] == _id('scan', [row['sequence_id'], row['model_id'], row['strand']]), 'component_scan_identity_conflict')
        sequence = sequences[row['sequence_id']]
        possible = max(0, sequence['length'] - matrix['length'] + 1) if sequence['state'] == matrix['state'] == 'available' else None
        _need(row['possible_positions'] == possible, 'component_scan_geometry_conflict')
        coverage = row['coverage']
        _shape(coverage, ('state', 'expected_positions', 'declared_count', 'captured_complete_elements', 'usable_elements', 'trailing_bytes', 'excess_elements'))
        _need(coverage['state'] in ('complete', 'partial', 'zero_possible', 'unavailable') and coverage['expected_positions'] == row['possible_positions'], 'coverage_state_invalid')
        for key in ('expected_positions', 'declared_count'):
            _integer(coverage[key], nullable=True)
        for key in ('captured_complete_elements', 'usable_elements', 'trailing_bytes', 'excess_elements'):
            _integer(coverage[key])
        _need(coverage['trailing_bytes'] <= 3 and coverage['usable_elements'] <= coverage['captured_complete_elements'], 'coverage_extent_invalid')
        scans[row['scan_id']] = row
    _need(set(selection['scan_ids']) <= set(scans), 'selected_scan_unknown')
    _need(_same(value['selected_scans'], [{'scan_id': k, 'coverage': scans[k]['coverage']} for k in selection['scan_ids']]), 'selected_scan_coverage_conflict')
    normalizations = {}
    for row in value['relative_normalizations']:
        _shape(row, ('normalization_id', 'model_id', 'bounds_strand', 'operand_dtype', 'scientific_state', 'reason_code', 'minimum', 'maximum', 'span') + (() if public else ('operand_evidence',)))
        _text(row['normalization_id'])
        _text(row['model_id'])
        _text(row['reason_code'], nullable=True)
        _need(row['normalization_id'] not in normalizations and row['model_id'] in {m['model_id'] for m in matrices.values()} and (row['bounds_strand'] == '+') and (row['operand_dtype'] == 'python_float_binary64') and (row['scientific_state'] in ('defined', 'undefined')) and ((row['reason_code'] is None) == (row['scientific_state'] == 'defined')), 'relative_normalization_invalid')
        for key in ('minimum', 'maximum', 'span'):
            _validate_extended(row[key], public=public)
            _need(row[key]['dtype'] == 'float64' and row[key]['unit'] == 'bits' and (row[key]['origin'] == ('calculated' if key == 'span' else 'native_observation')), 'relative_bounds_meaning_invalid')
        _need(row['minimum']['byte_order'] == row['maximum']['byte_order'] and (public or row['span']['location'] is None) and (row['normalization_id'] == _id('relative', [row['model_id'], hashlib.sha256(bytes.fromhex(row['minimum']['bits_hex'] + row['maximum']['bits_hex'])).hexdigest()])), 'relative_bounds_identity_conflict')
        if not public:
            evidence = row['operand_evidence']
            _shape(evidence, ('bounds_location', 'bounds_json_pointer', 'minimum_element_ordinal_0based', 'maximum_element_ordinal_0based'))
            _need(type(evidence['bounds_json_pointer']) is str and evidence['bounds_json_pointer'].startswith('/models/') and (evidence['minimum_element_ordinal_0based'] == 0) and (evidence['maximum_element_ordinal_0based'] == 1), 'relative_bounds_evidence_invalid')
            if evidence['bounds_location'] is not None:
                locations.location(evidence['bounds_location'])
            _need(_same(evidence['bounds_location'], row['minimum']['location']) and _same(row['minimum']['location'], row['maximum']['location']), 'relative_bounds_evidence_conflict')
        normalizations[row['normalization_id']] = row
    total_fields = ('raw_complete_elements', 'observed_window_scores', 'finite_scores', 'nan_scores', 'positive_infinity_scores', 'negative_infinity_scores', 'extended_scorable_scores', 'possible_strand_windows', 'possible_unique_windows', 'matched_observed_scores', 'raw_full_threshold_matches', 'full_matched_scores', 'model_eligible_candidate_sites', 'returned_raw_threshold_rows', 'returned_candidate_rows')
    _shape(value['totals'], total_fields)
    numbers = {}
    for key, cell in value['totals'].items():
        if public:
            _shape(cell, ('value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_id', 'method_id', 'uncertainty'))
            validate_numeric_cell({**cell, 'evidence': [], 'requirement_ids': []})
        else:
            validate_numeric_cell(cell)
        _need(cell['unit'] == 'count' and cell['origin'] == 'calculated' and (cell['method_id'] == 'tf_binding_' + key), 'total_meaning_invalid')
        _integer(cell['value'], nullable=key not in total_fields[:7])
        numbers[key] = cell['value']
    _need(numbers['observed_window_scores'] == sum((numbers[k] for k in ('finite_scores', 'nan_scores', 'positive_infinity_scores', 'negative_infinity_scores'))) and numbers['extended_scorable_scores'] == numbers['observed_window_scores'] - numbers['nan_scores'] and (numbers['raw_complete_elements'] >= numbers['observed_window_scores']), 'score_population_count_conflict')
    _need(len(value['raw_threshold_matches']) == numbers['returned_raw_threshold_rows'] and len(value['hits']) == numbers['returned_candidate_rows'] and (len(value['raw_threshold_matches']) <= selection['limit']), 'returned_row_count_conflict')
    hit_ids = set()
    for row in value['raw_threshold_matches']:
        _shape(row, ('hit_id', 'scan_id', 'sequence_id', 'matrix_occurrence_id', 'sequence_record_ordinal_0based', 'matrix_record_ordinal_0based', 'start_0based', 'end_0based_exclusive', 'strand', 'forward_sequence', 'model_normalization_eligible', 'motif_oriented_sequence', 'score', 'relative_score'))
        _need(row['scan_id'] in selection['scan_ids'] and row['hit_id'] not in hit_ids, 'hit_selected_scan_conflict')
        scan = scans[row['scan_id']]
        _need(all((row[k] == scan[k] for k in ('sequence_id', 'matrix_occurrence_id', 'strand'))), 'hit_population_conflict')
        sequence, matrix = (sequences[row['sequence_id']], matrices[row['matrix_occurrence_id']])
        for key in ('start_0based', 'end_0based_exclusive', 'sequence_record_ordinal_0based', 'matrix_record_ordinal_0based'):
            _integer(row[key])
        _need(row['sequence_record_ordinal_0based'] == sequence['record_ordinal_0based'] and row['matrix_record_ordinal_0based'] == matrix['record_ordinal_0based'] and (row['end_0based_exclusive'] - row['start_0based'] == matrix['length']) and (row['end_0based_exclusive'] <= sequence['length']) and (row['hit_id'] == _id('hit', [row['scan_id'], row['start_0based']])), 'hit_interval_conflict')
        _need(type(row['forward_sequence']) is str and row['forward_sequence'].isascii() and (len(row['forward_sequence']) == matrix['length']) and (type(row['model_normalization_eligible']) is bool), 'hit_sequence_invalid')
        _need(row['motif_oriented_sequence'] == (row['forward_sequence'] if row['strand'] == '+' else row['forward_sequence'].translate(str.maketrans('ACGT', 'TGCA'))[::-1]), 'hit_orientation_conflict')
        _validate_extended(row['score'], public=public)
        _validate_extended(row['relative_score'], relative=True, public=public)
        _need(row['score']['dtype'] == 'float32' and row['score']['origin'] == 'native_observation' and (row['score']['unit'] == 'bits') and (row['score']['classification'] != 'nan'), 'hit_score_meaning_invalid')
        relative = row['relative_score']
        descriptor = normalizations.get(relative['relative_normalization_id'])
        _need(descriptor is not None and descriptor['model_id'] == scan['model_id'] and (public or _same(relative['operand_evidence']['score_location'], row['score']['location'])), 'hit_relative_operand_conflict')
        if descriptor['scientific_state'] == 'undefined':
            _need(relative['state'] == 'undefined' and relative['reason_code'] == descriptor['reason_code'], 'relative_state_conflict')
        hit_ids.add(row['hit_id'])
    _need(_same(value['hits'], [row for row in value['raw_threshold_matches'] if row['model_normalization_eligible']]), 'candidate_row_conflict')
    _need(value['status'] != 'complete' or value['execution']['native_outcome'] == 'succeeded', 'complete_execution_conflict')
    return deepcopy(value)

def validate_tf_binding_public_value(value):
    """Validate the literal source-free public value, without inventing custody."""
    return _validate_tf_binding_values(value, public=True)
