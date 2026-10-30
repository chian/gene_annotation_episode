"""Authored HIC record/array witnesses; native-reader coverage is separate."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pytest

from gene_annotation_episode.chromatin_interaction_contracts import (
    ChromatinValidationError, TABLE_ROLES, validate_chromatin_record,
)
from gene_annotation_episode.chromatin_interaction_inputs import (
    build_chromatin_sheet, extract_chromatin_metadata, parse_chromatin_elements,
)
from gene_annotation_episode.chromatin_interaction_tables import (
    BINS_HEADER, STATES_DTYPE, contacts_dtype, dtype_descriptor,
    open_chromatin_contact_tables, read_chromatin_sheet_tables,
)
from gene_annotation_episode.chromatin_cooler_inputs import failure


EXAMPLES = Path(__file__).resolve().parents[1] / 'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json'


def identity(raw, format):
    sha = hashlib.sha256(raw).hexdigest()
    return {'artifact_ref': 'artifact_' + sha, 'sha256': sha, 'size_bytes': len(raw), 'format': format}


def byte_range(offset, size):
    return {'offset': offset, 'size_bytes': size, 'sha256': hashlib.sha256(bytes(size)).hexdigest()}


def authored_case(*, weighted=False, empty=False, terminal=40, start=0):
    """Symbolic parsing evidence, deliberately not a claim to have decoded HIC."""
    rows = json.loads(EXAMPLES.read_bytes())['records']
    base = deepcopy(next(row['record'] for row in rows if row['example_key'] == 'raw.sheet'))
    request = base['request']
    request['contact'].update(file=identity(b'authored_record_fixture' + bytes(1024), 'hic_binary_v9'),
                              format='hic_binary_v9', group_path=None, resolution_bp=10)
    request['populations'] = [{'population_key': 'p0', 'chromosome': 'chrA', 'start_bp': start, 'end_bp': terminal}]
    request['supplied_metadata']['reference'].update(assembly_label=None,
        contigs=[{'chromosome': 'chrA', 'length_bp': terminal}])
    request['supplied_metadata']['native_attribute_bindings'] = []
    request['normalization'] = ({'kind': 'precomputed_weighted', 'weight_column': 'SYNTHETIC_DIVISIVE', 'convention': 'divisive'}
                                if weighted else {'kind': 'raw', 'weight_column': None, 'convention': None})
    bed = b'chrA\t1\t2\tE\nchrA\t21\t22\tP\n'
    request['elements']['file'] = identity(bed, 'bed_outer_span_v1')
    request['elements']['reference'].update(assembly_label=None,
        contigs=[{'chromosome': 'chrA', 'length_bp': terminal}])
    request['elements']['assignments'] = [
        {'element_key': name, 'source_data_row': i, 'class': kind, 'gene_links': [], 'anchor': {'policy': 'interval_start'}}
        for i, (name, kind) in enumerate((('E', 'enhancer'), ('P', 'promoter')))]
    chrom = {'chromosome_index': 1, 'chromosome': 'chrA', 'length_bp': terminal}
    metadata = base['native']['metadata']
    metadata.update(source_file=deepcopy(request['contact']['file']), format='hic_binary_v9', format_version=9,
        group_path=None, bin_type='fixed', bin_size_bp=10, storage_mode='hic-symmetric', value_dtype='<f4',
        native_value_dtype='hic_v9_block_int16_or_float32', attributes=[], vectors=[])
    metadata['reference_assertion'].update(assembly_label=None, contigs=[{'chromosome': 'chrA', 'length_bp': terminal}])
    metadata['hic'] = {'version': 'hic_native_header_v1', 'bin_id_space': 'chromosome_local',
        'source_version': 9, 'byte_order': 'little', 'header_range': byte_range(0, 100),
        'footer_position': 600, 'normalization_index_position': 800, 'normalization_index_length': 50,
        'genome_id': 'unknown', 'chromosomes': [
            {'chromosome_index': 0, 'chromosome': 'All', 'native_length': 0, 'length_unit': 'kb_proxy', 'kind': 'all_by_all'},
            {'chromosome_index': 1, 'chromosome': 'chrA', 'native_length': terminal, 'length_unit': 'bp', 'kind': 'chromosome'}],
        'bp_resolutions': [10], 'frag_resolutions': []}
    contacts = np.array([] if empty else [(0, 0, 4, 0, 0), (0, 1, 2, 0, 1), (0, 2, 6, 0, 2),
        (1, 1, 4, 0, 3), (1, 2, 2, 0, 4), (1, 3, 2, 0, 5), (2, 2, 4, 0, 6),
        (2, 3, 2, 0, 7), (3, 3, 4, 0, 8)], dtype=contacts_dtype('<f4'))
    contacts = contacts[(contacts['bin1_id'] >= start // 10) & (contacts['bin2_id'] >= start // 10)]
    n = (terminal + 9) // 10 - start // 10
    bins = b''.join(f'{i}\t1\t{i * 10}\t{min((i + 1) * 10, terminal)}\n'.encode()
                    for i in range(start // 10, (terminal + 9) // 10))
    arrays = {'contacts': contacts, 'weights': np.array([1, 2, 1, 2][start // 10:], dtype='<f8') if weighted else None,
              'cell_states': np.empty(0, dtype=STATES_DTYPE), 'dense_values': None}
    block = {'block_id': 0, 'compressed_range': byte_range(100, 100), 'outcome': 'complete',
        'decoded_size_bytes': 120, 'decoded_sha256': hashlib.sha256(bytes(120)).hexdigest(),
        'zlib_eof': True, 'zlib_checksum_valid': True, 'payload_consumed_exactly': True,
        'matrix_representation': 1, 'value_encoding': 'float32', 'x_encoding': 'int32', 'y_encoding': 'int32',
        'bin_x_offset': 0, 'bin_y_offset': 0, 'n_records_declared': 9, 'n_records_decoded': 9,
        'dense_slot_count': None, 'dense_width': None, 'dense_filler_slot_count': None,
        'retained_population_record_count': len(contacts), 'record_ordinal_kind': 'sparse_record'}
    vector = {'normalization_type': 'SYNTHETIC_DIVISIVE', 'chromosome_index': 1, 'unit': 'BP',
        'resolution_bp': 10, 'index_extent': 'complete', 'native_range': byte_range(900, 24),
        'n_values_declared': 4, 'n_values_read': 4, 'native_dtype': '<f4',
        'selected_bin_start': start // 10, 'selected_bin_end_exclusive': 4,
        'physical_chromosome_bin_count': 4, 'extra_terminal_values': 0, 'outcome': 'complete'} if weighted else None
    witness = {'version': 'hic_population_read_v1', 'source_sha256': metadata['source_file']['sha256'],
        'scan_scope': 'all_indexed_blocks_selected_cis_zoom', 'matrix_key': '1_1',
        'matrix_index_range': byte_range(604, 20), 'matrix_metadata_range': byte_range(200, 100),
        'zoom_index_range': byte_range(212, 60), 'chromosome1_index': 1, 'chromosome2_index': 1,
        'unit': 'BP', 'resolution_bp': 10, 'block_bin_count': 5, 'block_column_count': 1,
        'declared_block_count': 0 if empty else 1, 'blocks': [] if empty else [block], 'selected_normalization': vector}
    population = {key: value for key, value in base['populations'][0].items() if key not in ('element_anchor_rows', 'pair_rows')}
    represented = sum(1 if row['bin1_id'] == row['bin2_id'] else 2 for row in contacts)
    population.update(selected_region=deepcopy(request['populations'][0]), extent='complete', bin_count=n,
        fixed_bin_size_bp=10, native_storage_mode='hic-symmetric', data_table_keys=['p0:' + role for role in TABLE_ROLES],
        raw_cell_population={'directed_cells': n*n, 'unique_unordered_cells': n*(n+1)//2,
            'stored_rows': len(contacts), 'explicit_zero_rows': 0, 'implicit_zero_directed_cells': n*n-represented,
            'native_nonfinite_directed_cells': 0, 'unavailable_directed_cells': 0, 'validated_observed_row_count': len(contacts)},
        normalization={'specification': deepcopy(request['normalization']), 'availability': 'available' if weighted else 'not_requested',
            'vector_table_key': 'p0:weights' if weighted else None, 'native_weight_dtype': '<f4' if weighted else None,
            'valid_bin_count': n if weighted else None, 'masked_bin_count': 0 if weighted else None, 'invalid_bin_count': 0 if weighted else None},
        read_evidence={'axes_extent': 'complete', 'index_extent': 'complete', 'selected_records_extent': 'complete',
            'required_native_row_ranges': [], 'expected_block_count': 0 if empty else 1,
            'read_block_count': 0 if empty else 1, 'failed_block_ids': [],
            'implicit_zero_semantics': 'validated_sparse_absence', 'symmetry': 'native_hic_symmetric', 'hic': witness}, failures=[])
    drafts, descriptors, streams = [], [], {}
    for role in TABLE_ROLES:
        present = role == 'bins' or arrays[role] is not None
        raw = BINS_HEADER + bins if role == 'bins' else None
        if present and role != 'bins':
            stream = io.BytesIO()
            np.save(stream, arrays[role], allow_pickle=False)
            raw = stream.getvalue()
        locator = {'kind': 'hic_bytes', 'value': {'offset': 212, 'size_bytes': 60, 'section': 'zoom_index'}}
        if role == 'weights':
            locator = {'kind': 'hic_vector', 'value': {'normalization_type': 'SYNTHETIC_DIVISIVE',
                'chromosome_index': 1, 'unit': 'BP', 'resolution_bp': 10, 'bin_index': None}}
        draft = {'table_key': 'p0:' + role, 'population_key': 'p0', 'role': role,
            'availability': 'present' if present else 'not_requested' if role == 'weights' else 'not_native_representation',
            'absence_reason': None,
            'encoding': ('tsv' if role == 'bins' else 'npy') if present else None,
            'shape': ([n, 4] if role == 'bins' else list(arrays[role].shape)) if present else None,
            'dtype_descriptor': ({'kind': 'scalar', 'dtype': 'utf8_tsv_int64'} if role == 'bins' else dtype_descriptor(arrays[role].dtype)) if present else None,
            'row_count': (n if role == 'bins' else len(arrays[role])) if present else None,
            'native_source_locator': locator if present else None, 'extent': 'complete' if present else 'unavailable'}
        drafts.append(draft)
        descriptors.append({**deepcopy(draft), 'file': identity(raw, 'chromatin_contact_tables_v1:' + role) if present else None})
        if present:
            streams[draft['table_key']] = io.BytesIO(raw)
    extraction = {'format': 'hic_binary_v9', 'format_version': 9, 'native_metadata': metadata,
        'chromosomes': [chrom], 'populations': [population], 'table_drafts': drafts, 'failures': []}
    return request, extraction, descriptors, streams, bed


def build_case(case):
    request, extraction, descriptors, streams, bed = case
    elements = parse_chromatin_elements(bed, spec=request['elements'])
    metadata = extract_chromatin_metadata(request=request, native=extraction, supplied=request['supplied_metadata'], elements=elements)
    with open_chromatin_contact_tables(descriptors, streams=streams) as arrays:
        sheet = build_chromatin_sheet(request=request, contacts=extraction, elements=elements,
            metadata=metadata, tables=descriptors, table_views=arrays)
    return sheet, streams


def replace_array(case, role, array):
    _, extraction, descriptors, streams, _ = case
    stream = io.BytesIO()
    np.save(stream, array, allow_pickle=False)
    descriptor = next(d for d in descriptors if d['role'] == role)
    descriptor.update(shape=list(array.shape), row_count=len(array), dtype_descriptor=dtype_descriptor(array.dtype),
                      file=identity(stream.getvalue(), 'chromatin_contact_tables_v1:' + role))
    next(d for d in extraction['table_drafts'] if d['role'] == role).update(
        {key: value for key, value in descriptor.items() if key != 'file'})
    streams[descriptor['table_key']] = stream


@pytest.mark.parametrize('weighted,expected,fold', [(False, 4, 1.5), (True, 3.25, 24/13)])
def test_authored_witness_saved_numerical_example(weighted, expected, fold, monkeypatch):
    from gene_annotation_episode.chromatin_interaction_calculations import calculate_contact_enrichment
    sheet, streams = build_case(authored_case(weighted=weighted))
    monkeypatch.setattr('gene_annotation_episode.chromatin_cooler_inputs.read_cooler_contacts',
                        lambda *args, **kwargs: pytest.fail('saved calculation read a native source'))
    with read_chromatin_sheet_tables(sheet, streams=streams) as tables:
        result = calculate_contact_enrichment(sheet, tables=tables, normalization=sheet['request']['normalization'],
            parameters={'minimum_separation_bins': 1, 'fold_threshold': 2, 'threshold_comparison': 'strict_gt',
                        'expectation': 'same_population_distance_mean',
                        'missing_policy': 'exclude_declared_masked_bins_require_complete_population'})
    pair = result['populations'][0]['pairs'][0]
    assert pair['measurements']['raw_contact']['value'] == 6
    assert pair['measurements']['expected_contact']['value'] == expected
    assert pair['measurements']['fold_enrichment']['value'] == pytest.approx(fold)


@pytest.mark.parametrize('change', ['missing_hic', 'source', 'missing_block', 'checksum', 'cardinality',
    'range', 'matrix', 'resolution', 'chromosome', 'global_id_space', 'all_unit', 'filler'])
def test_complete_claims_need_independent_hic_evidence(change):
    case = authored_case()
    metadata, population = case[1]['native_metadata'], case[1]['populations'][0]
    witness = population['read_evidence']['hic']
    if change == 'missing_hic': population['read_evidence']['hic'] = None
    elif change == 'source': witness['source_sha256'] = '0' * 64
    elif change == 'missing_block': witness['blocks'] = []
    elif change == 'checksum': witness['blocks'][0]['zlib_checksum_valid'] = False
    elif change == 'cardinality': witness['blocks'][0]['n_records_declared'] += 1
    elif change == 'range': witness['zoom_index_range']['sha256'] = None
    elif change == 'matrix': witness['matrix_key'] = '0_0'
    elif change == 'resolution': witness['resolution_bp'] = 20
    elif change == 'chromosome': case[1]['chromosomes'][0]['chromosome_index'] = 0
    elif change == 'global_id_space': metadata['hic']['bin_id_space'] = 'genome_global'
    elif change == 'all_unit': metadata['hic']['chromosomes'][0]['length_unit'] = 'bp'
    else: witness['blocks'][0]['dense_filler_slot_count'] = 1
    with pytest.raises(ChromatinValidationError): build_case(case)


@pytest.mark.parametrize('change', ['block', 'ordinal', 'duplicate_ordinal', 'float64', 'retained_count'])
def test_actual_arrays_must_match_native_occurrences(change):
    case = authored_case()
    array = np.load(io.BytesIO(case[3]['p0:contacts'].getvalue()))
    if change == 'block': array['source_block'][0] = 99
    elif change == 'ordinal': array['source_row'][0] = 9
    elif change == 'duplicate_ordinal': array['source_row'][1] = 0
    elif change == 'float64': array = array.astype(contacts_dtype('<f8'))
    else: case[1]['populations'][0]['read_evidence']['hic']['blocks'][0]['retained_population_record_count'] -= 1
    replace_array(case, 'contacts', array)
    with pytest.raises(ChromatinValidationError): build_case(case)


@pytest.mark.parametrize('change', ['name', 'chromosome', 'resolution', 'short', 'bytes', 'padding', 'nondivisive', 'value'])
def test_selected_normalization_requires_exact_native_vector(change):
    case = authored_case(weighted=True)
    vector = case[1]['populations'][0]['read_evidence']['hic']['selected_normalization']
    if change == 'name': vector['normalization_type'] = 'other'
    elif change == 'chromosome': vector['chromosome_index'] = 0
    elif change == 'resolution': vector['resolution_bp'] = 20
    elif change == 'short': vector.update(n_values_declared=3, n_values_read=3)
    elif change == 'bytes': vector['native_range']['size_bytes'] -= 1
    elif change == 'padding': vector['extra_terminal_values'] = 1
    elif change == 'nondivisive': case[0]['normalization']['convention'] = 'multiplicative'
    else: replace_array(case, 'weights', np.array([1, 1.00000000001, 1, 2], dtype='<f8'))
    with pytest.raises(ChromatinValidationError): build_case(case)


def test_complete_present_zero_matrix_and_physical_terminal_bins():
    sheet, streams = build_case(authored_case(empty=True, terminal=35, start=10))
    assert sheet['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'] == 9
    with read_chromatin_sheet_tables(sheet, streams=streams) as tables:
        assert tables['populations']['p0']['bins']['bin_id'].tolist() == [1, 2, 3]
        assert tables['populations']['p0']['bins']['end_bp'].tolist() == [20, 30, 35]


def test_partial_failed_range_keeps_original_declaration_and_valid_rows():
    case = authored_case()
    population = case[1]['populations'][0]
    population['extent'] = 'partial'
    population['raw_cell_population'].update(implicit_zero_directed_cells=None, unavailable_directed_cells=None)
    evidence = population['read_evidence']
    evidence.update(selected_records_extent='partial', expected_block_count=2, failed_block_ids=[1], implicit_zero_semantics='not_established')
    witness = evidence['hic']
    witness['declared_block_count'] = 2
    failed = {key: None for key in witness['blocks'][0]}
    failed.update(block_id=1, compressed_range={'offset': 9999, 'size_bytes': 100, 'sha256': None},
        outcome='unavailable', zlib_eof=False, zlib_checksum_valid=False, payload_consumed_exactly=False)
    witness['blocks'].append(failed)
    population['failures'] = [failure('native_chunk_unavailable', spec=case[0]['contact'],
        population=population, locator={'kind': 'hic_block', 'value': {'chromosome1_index': 1,
        'chromosome2_index': 1, 'resolution_bp': 10, 'block_id': 1, 'record_ordinal': None}})]
    sheet, _ = build_case(case)
    assert sheet['populations'][0]['pair_rows'][0]['raw_contact']['value'] == 6
    assert sheet['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'] is None
    population['failures'] = []
    with pytest.raises(ChromatinValidationError): build_case(case)


def test_header_attributes_preserve_duplicate_occurrences_and_locate_conflicts():
    request, extraction, _, _, _ = authored_case()
    attrs = extraction['native_metadata']['attributes']
    for index, value in enumerate(('one', 'two')):
        attrs.extend({'path': f'/hic/attributes/{index}/{part}', 'dtype': 'utf8', 'shape': [],
                      'value_state': 'decoded', 'value': text}
                     for part, text in (('key', 'assembly'), ('value', value)))
    supplied = request['supplied_metadata']
    supplied['reference']['assembly_label'] = 'different'
    supplied['native_attribute_bindings'] = [{'native_attribute_path': '/hic/attributes/1/value',
        'meaning': 'assembly_label', 'supplied_target_key': 'different'}]
    result = extract_chromatin_metadata(request=request, native=extraction, supplied=supplied, elements=None)
    assert result['failures'][-1]['locator'] == {'kind': 'hic_bytes',
        'value': {'offset': 0, 'size_bytes': 100, 'section': 'header'}}
    supplied['native_attribute_bindings'][0]['native_attribute_path'] = '/hic/attributes/1/key'
    with pytest.raises(ChromatinValidationError, match='value_binding'):
        extract_chromatin_metadata(request=request, native=extraction, supplied=supplied, elements=None)


@pytest.mark.parametrize('kind,field,value', [('HicHeader', 'source_version', 9.0),
    ('HicBlockRead', 'matrix_representation', True), ('HicBlockRead', 'matrix_representation', 1.0)])
def test_hic_numeric_flags_are_strict_integers(kind, field, value):
    case = authored_case()
    record = (case[1]['native_metadata']['hic'] if kind == 'HicHeader'
              else case[1]['populations'][0]['read_evidence']['hic']['blocks'][0])
    record[field] = value
    with pytest.raises(ChromatinValidationError):
        validate_chromatin_record(kind, record)


def test_later_weight_table_loss_preserves_original_native_vector_facts():
    case = authored_case(weighted=True)
    population = case[1]['populations'][0]
    population['normalization'].update(availability='missing', vector_table_key=None,
        valid_bin_count=None, masked_bin_count=None, invalid_bin_count=None)
    draft = next(d for d in case[1]['table_drafts'] if d['role'] == 'weights')
    draft.update(availability='unavailable', absence_reason='input_unavailable', encoding=None,
                 shape=None, dtype_descriptor=None, row_count=None, extent='unavailable')
    descriptor = next(d for d in case[2] if d['role'] == 'weights')
    descriptor.update(deepcopy(draft), file=None)
    case[3].pop('p0:weights')
    sheet, streams = build_case(case)
    assert sheet['populations'][0]['read_evidence']['hic']['selected_normalization']['outcome'] == 'complete'
    with read_chromatin_sheet_tables(sheet, streams=streams) as tables:
        assert tables['populations']['p0']['weights'] is None


@pytest.mark.parametrize('wrong_precision', [False, True])
def test_lost_contacts_still_validate_retained_native_weights(wrong_precision):
    from gene_annotation_episode.chromatin_interaction_result_worker import _lost_table
    case = authored_case(weighted=True)
    original_vector = deepcopy(case[1]['populations'][0]['read_evidence']['hic']['selected_normalization'])
    _lost_table(case[1], 'contacts', failure('input_unavailable', stage='capture',
        population=case[1]['populations'][0]))
    draft = next(d for d in case[1]['table_drafts'] if d['role'] == 'contacts')
    draft.update(availability='unavailable', absence_reason='input_unavailable', encoding=None,
                 shape=None, dtype_descriptor=None, row_count=None, extent='unavailable')
    next(d for d in case[2] if d['role'] == 'contacts').update(deepcopy(draft), file=None)
    case[3].pop('p0:contacts')
    if wrong_precision:
        replace_array(case, 'weights', np.array([1, 1.00000000001, 1, 2], dtype='<f8'))
        with pytest.raises(ChromatinValidationError, match='hic_weight_not_native_float32'):
            build_case(case)
    else:
        sheet, streams = build_case(case)
        assert sheet['populations'][0]['read_evidence']['hic']['selected_normalization'] == original_vector
        with read_chromatin_sheet_tables(sheet, streams=streams) as tables:
            assert tables['populations']['p0']['contacts'] is None
            np.testing.assert_array_equal(tables['populations']['p0']['weights'], [1, 2, 1, 2])


def test_genome_global_bins_cannot_replace_chromosome_local_identity():
    case = authored_case()
    raw = BINS_HEADER + b''.join(f'{i+100}\t1\t{i*10}\t{(i+1)*10}\n'.encode() for i in range(4))
    descriptor = next(d for d in case[2] if d['role'] == 'bins')
    descriptor['file'] = identity(raw, 'chromatin_contact_tables_v1:bins')
    case[3]['p0:bins'] = io.BytesIO(raw)
    array = np.load(io.BytesIO(case[3]['p0:contacts'].getvalue()))
    array['bin1_id'] += 100
    array['bin2_id'] += 100
    replace_array(case, 'contacts', array)
    with pytest.raises(ChromatinValidationError, match='chromosome_local'):
        build_case(case)


@pytest.mark.parametrize('tag', [1, 2, 5])
def test_missing_state_or_dense_filler_cannot_manufacture_complete_measurement(tag):
    case = authored_case(empty=True)
    replace_array(case, 'cell_states', np.array([(0, 1, tag)], dtype=STATES_DTYPE))
    with pytest.raises(ChromatinValidationError):
        build_case(case)


@pytest.mark.parametrize('weighted,relative,expected,fold', [
    (False, 'native004/four.hic', 4, 1.5),
    (True, 'native009/valid/output.hic', 3.25, 24/13),
])
def test_retained_native_hic_reader_to_saved_sheet_recalculation(weighted, relative, expected, fold, monkeypatch):
    from gene_annotation_episode.chromatin_hic_inputs import read_hic_contacts
    from gene_annotation_episode.chromatin_interaction_calculations import calculate_contact_enrichment
    root = Path(__file__).resolve().parents[1]
    fixture = root / 'verification/tool_graders_chromatin_hic_native_2026-10-27_454' / relative
    source = fixture.read_bytes()
    request, _, _, _, bed = authored_case(weighted=weighted)
    request['contact']['file'] = identity(source, 'hic_binary_v9')
    audit = json.loads((fixture.parent / 'BYTE_AUDIT.json').read_bytes())
    assert audit['sha256'] == request['contact']['file']['sha256']
    output = {(p['population_key'], role): io.BytesIO() for p in request['populations'] for role in TABLE_ROLES}
    with fixture.open('rb') as supplied:
        extraction = read_hic_contacts(supplied, spec=request['contact'], normalization=request['normalization'],
                                      populations=request['populations'], table_streams=output)
    descriptors, streams = [], {}
    for draft in extraction['table_drafts']:
        raw = output[(draft['population_key'], draft['role'])].getvalue()
        present = draft['availability'] == 'present'
        descriptors.append({**draft, 'file': identity(raw, 'chromatin_contact_tables_v1:' + draft['role']) if present else None})
        if present:
            streams[draft['table_key']] = io.BytesIO(raw)
    sheet, streams = build_case((request, extraction, descriptors, streams, bed))
    # Persist the sheet and exact canonical tables, then deny native reads.
    directory = Path.cwd() / 'native_hic_saved_examples' / ('divisive' if weighted else 'raw')
    directory.mkdir(parents=True, exist_ok=True)
    sheet_bytes = json.dumps(sheet, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    (directory / 'sheet.json').write_bytes(sheet_bytes)
    for key, stream in streams.items():
        (directory / (key.replace(':', '_') + '.table')).write_bytes(stream.getvalue())
    saved = json.loads(sheet_bytes)
    monkeypatch.setattr('gene_annotation_episode.chromatin_hic_inputs.read_hic_contacts',
                        lambda *a, **k: pytest.fail('saved recalculation invoked native parser'))
    original_open = Path.open
    def no_source(path, *args, **kwargs):
        if path == fixture:
            pytest.fail('saved recalculation reopened native input')
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', no_source)
    parameters = {'minimum_separation_bins': 1, 'fold_threshold': 2,
        'threshold_comparison': 'strict_gt', 'expectation': 'same_population_distance_mean',
        'missing_policy': 'exclude_declared_masked_bins_require_complete_population'}
    results = []
    with read_chromatin_sheet_tables(saved, streams=streams) as tables:
        for threshold in (2, 1.4):
            parameters['fold_threshold'] = threshold
            result = calculate_contact_enrichment(saved, tables=tables, normalization=request['normalization'], parameters=parameters)
            pair = result['populations'][0]['pairs'][0]['measurements']
            assert pair['raw_contact']['value'] == 6
            assert pair['expected_contact']['value'] == expected
            assert pair['fold_enrichment']['value'] == pytest.approx(fold)
            assert pair['above_fold_threshold']['value'] is (threshold < fold)
            results.append({'threshold': threshold, 'raw': pair['raw_contact']['value'],
                            'expected': expected, 'fold': pair['fold_enrichment']['value'],
                            'above': pair['above_fold_threshold']['value']})
    assert json.dumps(saved, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() == sheet_bytes
    (directory / 'TEST_EVIDENCE.json').write_text(json.dumps({'fixture': relative, 'native_identity': request['contact']['file'],
        'sheet_identity': identity(sheet_bytes, 'chromatin_interaction_sheet_v1'), 'results': results,
        'native_reader_disabled_during_recalculation': True, 'native_source_open_disabled_during_recalculation': True}, indent=2) + '\n')


@pytest.mark.parametrize('role', ['bins', 'contacts', 'cell_states', 'weights'])
def test_canonical_table_locators_match_their_population_witness(role):
    case = authored_case(weighted=True)
    draft = next(row for row in case[1]['table_drafts'] if row['role'] == role)
    descriptor = next(row for row in case[2] if row['role'] == role)
    field = 'chromosome_index' if role == 'weights' else 'offset'
    draft['native_source_locator']['value'][field] += 1
    descriptor['native_source_locator'] = deepcopy(draft['native_source_locator'])
    with pytest.raises(ChromatinValidationError, match='table_source_mismatch'):
        build_case(case)


def test_complete_index_order_requires_native_order_even_with_failed_block():
    case = authored_case(empty=True)
    population = case[1]['populations'][0]
    population['extent'] = 'partial'
    population['raw_cell_population'].update(implicit_zero_directed_cells=None, unavailable_directed_cells=None)
    evidence = population['read_evidence']
    evidence.update(selected_records_extent='partial', implicit_zero_semantics='not_established',
                    expected_block_count=2, read_block_count=0, failed_block_ids=[2, 1])
    template = authored_case()[1]['populations'][0]['read_evidence']['hic']['blocks'][0]
    template.update(outcome='partial', retained_population_record_count=0)
    evidence['hic'].update(declared_block_count=2, blocks=[dict(template, block_id=2), dict(template, block_id=1)])
    with pytest.raises(ChromatinValidationError, match='index_order'):
        build_case(case)
    evidence['index_extent'] = 'partial'
    sheet, _ = build_case(case)
    assert [row['block_id'] for row in sheet['populations'][0]['read_evidence']['hic']['blocks']] == [2, 1]
