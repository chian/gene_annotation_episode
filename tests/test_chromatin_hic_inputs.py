"""Retained whole-native-file HIC checks and explicitly recorded corruptions.

454 fixtures have independent official-native dumps/byte audits. Scientific
values are synthetic. These tests neither acquire data nor launch a writer.
"""
from copy import deepcopy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

import numpy as np

from gene_annotation_episode.chromatin_interaction_contracts import (
    TABLE_ROLES, ChromatinValidationError, chromatin_record_digest,
)
from gene_annotation_episode.chromatin_hic_inputs import read_hic_contacts
from gene_annotation_episode.chromatin_hic_binary import decode_block
from gene_annotation_episode.chromatin_interaction_tables import (
    open_chromatin_contact_tables, read_chromatin_sheet_tables,
)
from gene_annotation_episode.chromatin_interaction_inputs import (
    parse_chromatin_elements, extract_chromatin_metadata, build_chromatin_sheet,
)
from gene_annotation_episode.chromatin_interaction_calculations import calculate_chromatin_components


REPO = Path('/home/chia/repos/gene_annotation_episode')
FIXTURES = Path(os.environ.get('HIC_FIXTURE_ROOT', REPO / 'verification/tool_graders_chromatin_hic_native_2026-10-27_454'))
V8 = Path(os.environ.get('HIC_V8_FIXTURE', REPO / 'verification/tool_graders_chromatin_hic_contract_2026-10-27_452/prerequisite002/testBp.hic'))
EXAMPLES = Path.cwd() / 'WORKED_RECORDS.json'


def example(name):
    return next(row['record'] for row in json.loads(EXAMPLES.read_text())['records'] if row['example_key'] == name)


def identity(raw, format):
    digest = hashlib.sha256(raw).hexdigest()
    return {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': len(raw), 'format': format}


def fixture(relative):
    path = FIXTURES / relative
    raw = path.read_bytes()
    audit = json.loads((path.parent / 'BYTE_AUDIT.json').read_text())
    assert identity(raw, 'hic_binary_v9')['sha256'] == audit['sha256']
    return raw, audit


def request_for(raw, *, weighted=False, chromosome='chrA', length=40, resolution=10):
    request = deepcopy(example('raw.sheet')['request'])
    request['contact'].update(file=identity(raw, 'hic_binary_v9'), format='hic_binary_v9', group_path=None, resolution_bp=resolution)
    request['populations'] = [{'population_key': 'p0', 'chromosome': chromosome, 'start_bp': 0, 'end_bp': length}]
    for reference in (request['supplied_metadata']['reference'], request['elements']['reference']):
        reference.update(assembly_label=None, assembly_accession=None,
                         contigs=[{'chromosome': chromosome, 'length_bp': length}])
    if weighted:
        request['normalization'] = {'kind': 'precomputed_weighted', 'weight_column': 'SYNTHETIC_DIVISIVE', 'convention': 'divisive'}
    return request


def extract(raw, request, label='native'):
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode() + raw).hexdigest()
    directory = Path.cwd() / 'hic_cases' / key
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'input.hic').write_bytes(raw)
    (directory / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    (directory / 'origin.txt').write_text(label + '\n')
    streams = {(p['population_key'], role): io.BytesIO() for p in request['populations'] for role in TABLE_ROLES}
    source = io.BytesIO(raw)
    try:
        out = read_hic_contacts(source, spec=request['contact'], normalization=request['normalization'],
                                populations=request['populations'], table_streams=streams)
    finally:
        for (population, role), stream in streams.items():
            if stream.getvalue():
                (directory / f'{population}.{role}.output').write_bytes(stream.getvalue())
    assert not source.closed and source.getvalue() == raw
    (directory / 'extraction.json').write_text(json.dumps(out, indent=2, allow_nan=False) + '\n')
    descriptors, supplied = [], {}
    for draft in out['table_drafts']:
        data = streams[(draft['population_key'], draft['role'])].getvalue()
        descriptors.append(draft | {'file': identity(data, 'chromatin_contact_tables_v1:' + draft['role']) if draft['availability'] == 'present' else None})
        if draft['availability'] == 'present':
            supplied[draft['table_key']] = io.BytesIO(data)
    (directory / 'descriptors.json').write_text(json.dumps(descriptors, indent=2, allow_nan=False) + '\n')
    return out, descriptors, supplied, directory


def sheet_for(raw, request, *, label='native', bed=None):
    request = deepcopy(request)
    if request['elements'] is not None:
        chromosome = request['populations'][0]['chromosome']
        bed = f'{chromosome}\t1\t2\tE\n{chromosome}\t21\t22\tP\n{chromosome}\t31\t32\tQ\n'.encode() if bed is None else bed
        request['elements']['file'] = identity(bed, 'bed_outer_span_v1')
        elements = parse_chromatin_elements(bed, spec=request['elements'])
    else:
        elements = None
    out, descriptors, streams, directory = extract(raw, request, label)
    metadata = extract_chromatin_metadata(request=request, native=out, supplied=request['supplied_metadata'], elements=elements)
    with open_chromatin_contact_tables(descriptors, streams=streams) as views:
        sheet = build_chromatin_sheet(request=request, contacts=out, elements=elements, metadata=metadata, tables=descriptors, table_views=views)
    (directory / 'sheet.json').write_text(json.dumps(sheet, indent=2, allow_nan=False) + '\n')
    return sheet, streams, directory


def calculate(sheet, streams, directory, *, insulation=False, parameters=None):
    parameters = deepcopy(example('insulation.components' if insulation else 'raw.components')['parameters']) if parameters is None else deepcopy(parameters)
    parameters['normalization'] = deepcopy(sheet['request']['normalization'])
    with read_chromatin_sheet_tables(sheet, streams=streams) as views:
        result = calculate_chromatin_components(sheet, tables=views, parameters=parameters)
    digest = chromatin_record_digest(result)
    (directory / f'components.{digest}.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result, parameters


def changed(raw, offset, replacement, name):
    value = raw[:offset] + replacement + raw[offset + len(replacement):]
    directory = Path.cwd() / 'mutations' / hashlib.sha256(value).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'input.hic').write_bytes(value)
    (directory / 'mutation.json').write_text(json.dumps({'name': name, 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'derived_sha256': hashlib.sha256(value).hexdigest(), 'offset': offset,
        'before_hex': raw[offset:offset + len(replacement)].hex(), 'after_hex': replacement.hex()}, indent=2) + '\n')
    return value


def changed_payload(raw, audit, change, name, *, compressed_suffix=b''):
    """Relocate one audited native block, recording every changed source byte.

    Used only for the single-block, empty-NVI fixture. No production decoder
    supplies offsets or expected records for the mutation.
    """
    assert len(audit['matrices']) == 1 and not audit['normalization_vectors']
    matrix = audit['matrices'][0]
    zoom = matrix['zooms'][0]
    assert len(zoom['blocks']) == 1
    block = zoom['blocks'][0]
    a, b = block['position'], block['position'] + block['compressed_size']
    before = zlib.decompress(raw[a:b])
    after = change(bytearray(before))
    encoded = zlib.compress(bytes(after)) + compressed_suffix
    delta = len(encoded) - (b - a)
    value = bytearray(raw[:a] + encoded + raw[b:])
    struct.pack_into('<q', value, 8, audit['footer_position'] + delta)
    nvi_field = raw.index(b'\0', 16) + 1
    struct.pack_into('<q', value, nvi_field, audit['normalization_index_position'] + delta)
    block_entry = zoom['zoom_index_position'] + zoom['zoom_index_size'] - 16 + delta
    struct.pack_into('<i', value, block_entry + 12, len(encoded))
    master_position = audit['footer_position'] + delta + 8 + 4 + len(matrix['key'].encode()) + 1
    struct.pack_into('<q', value, master_position, matrix['position'] + delta)
    directory = Path.cwd() / 'mutations' / hashlib.sha256(value).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'input.hic').write_bytes(value)
    (directory / 'before.payload').write_bytes(before)
    (directory / 'after.payload').write_bytes(after)
    (directory / 'mutation.json').write_text(json.dumps({'name': name, 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'derived_sha256': hashlib.sha256(value).hexdigest(), 'block_offset': a, 'old_compressed_size': b-a,
        'new_compressed_size': len(encoded), 'offset_shift_after_original_block': delta,
        'appended_compressed_suffix_hex': compressed_suffix.hex(),
        'changed_header_fields': [8, nvi_field], 'changed_zoom_size_field': block_entry+12,
        'changed_master_position_field': master_position}, indent=2) + '\n')
    return bytes(value)


def absent_master_entry(raw, audit):
    """Explicit byte mutation of a valid file to a valid absent-matrix index."""
    footer = audit['footer_position']
    first = footer + 12
    entry_size = len(audit['master_index_entries'][0]['key'].encode()) + 1 + 12
    value = bytearray(raw[:first] + raw[first + entry_size:])
    struct.pack_into('<i', value, footer + 8, 0)
    struct.pack_into('<q', value, footer, audit['footer_nbytes_v5'] - entry_size)
    nvi_field = raw.index(b'\0', 16) + 1
    struct.pack_into('<q', value, nvi_field, audit['normalization_index_position'] - entry_size)
    directory = Path.cwd() / 'mutations' / hashlib.sha256(value).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'input.hic').write_bytes(value)
    (directory / 'mutation.json').write_text(json.dumps({'name': 'remove exact master entry; valid absence, not zero',
        'source_sha256': hashlib.sha256(raw).hexdigest(), 'derived_sha256': hashlib.sha256(value).hexdigest(),
        'deleted_offset': first, 'deleted_bytes_hex': raw[first:first + entry_size].hex(),
        'changed_fields': {'master_count': 0, 'footer_nbytes': audit['footer_nbytes_v5'] - entry_size,
                           'normalization_index_position': audit['normalization_index_position'] - entry_size}}, indent=2) + '\n')
    return bytes(value)


def rowlist_fields(payload):
    """Independent test mutation offsets for retained x32/y32 float32 fixture."""
    assert payload[12:16] == bytes([1, 1, 1, 1])
    position = 20
    rows = struct.unpack_from('<i', payload, 16)[0]
    fields = []
    for _ in range(rows):
        y_position = position
        columns = struct.unpack_from('<i', payload, position + 4)[0]
        position += 8
        for _ in range(columns):
            fields.append((position, y_position, position + 4))
            position += 8
    assert position == len(payload)
    return fields


class HicNativeInputsTest(unittest.TestCase):
    def test_native004_complete_dense_counts_and_exact_locators(self):
        raw, audit = fixture('native004/four.hic')
        out, descriptors, streams, _ = extract(raw, request_for(raw), 'official hictk 2.2.0; synthetic values')
        p = out['populations'][0]
        self.assertEqual(p['extent'], 'complete', out['failures'])
        self.assertFalse(out['failures'])
        self.assertEqual(p['raw_cell_population'], {'directed_cells': 16, 'unique_unordered_cells': 10,
            'stored_rows': 9, 'explicit_zero_rows': 0, 'implicit_zero_directed_cells': 2,
            'native_nonfinite_directed_cells': 0, 'unavailable_directed_cells': 0, 'validated_observed_row_count': 9})
        witness = p['read_evidence']['hic']['blocks'][0]
        native = audit['matrices'][0]['zooms'][0]['blocks'][0]
        self.assertEqual(witness['decoded_size_bytes'], 86)
        self.assertEqual(witness['decoded_sha256'], native['decoded_sha256'])
        self.assertEqual(witness['dense_filler_slot_count'], 7)
        self.assertEqual(witness['retained_population_record_count'], 9)
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            arrays = views['populations']['p0']
            rows = arrays['contacts']
            wanted = sorted(native['records'], key=lambda row: (row['x'], row['y']))
            self.assertEqual(rows['value'].tolist(), [row['value'] for row in wanted])
            self.assertEqual(rows['source_row'].tolist(), [row['ordinal'] for row in wanted])
            self.assertEqual(rows['source_block'].tolist(), [0] * 9)
            self.assertEqual(len(arrays['cell_states']), 0)
            self.assertIsNone(arrays['dense_values'])
            self.assertFalse(rows.flags.writeable)

    def test_all_eight_native_rowlist_width_encodings_and_dense_short(self):
        for value in ('i16', 'f32'):
            for x in (16, 32):
                for y in (16, 32):
                    name = f'rowlist_{value}_x{x}_y{y}'
                    with self.subTest(name=name):
                        raw, audit = fixture(f'native010/{name}/output.hic')
                        sheet, streams, directory = sheet_for(raw, request_for(raw), label='independent native serializer, official-reader checked')
                        block = sheet['populations'][0]['read_evidence']['hic']['blocks'][0]
                        self.assertEqual((block['value_encoding'], block['x_encoding'], block['y_encoding']),
                                         ('int16' if value == 'i16' else 'float32', f'int{x}', f'int{y}'))
                        result, _ = calculate(sheet, streams, directory)
                        self.assertEqual(result['contact']['populations'][0]['pairs'][0]['measurements']['fold_enrichment']['value'], 1.5)
        for name in ('dense_i16_fillers', 'dense_f32_fillers', 'rowlist_explicit_zero', 'dense_explicit_zero'):
            with self.subTest(name=name):
                raw, _ = fixture(f'native010/{name}/output.hic')
                sheet, streams, directory = sheet_for(raw, request_for(raw))
                result, _ = calculate(sheet, streams, directory)
                self.assertEqual(result['contact']['populations'][0]['pairs'][0]['measurements']['raw_contact']['value'], 6)
                count = sheet['populations'][0]['raw_cell_population']
                self.assertEqual(count['explicit_zero_rows'], int('explicit_zero' in name))
                self.assertEqual(count['implicit_zero_directed_cells'], 0 if 'explicit_zero' in name else 2)

    def test_raw_and_divisive_numbers_and_saved_recalculation(self):
        raw, _ = fixture('native009/valid/output.hic')
        sheet, streams, directory = sheet_for(raw, request_for(raw, weighted=True), label='official writer supplied synthetic divisive weights')
        result, parameters = calculate(sheet, streams, directory)
        contact = result['contact']['populations'][0]
        pair, distance = contact['pairs'][0]['measurements'], contact['distance_expectations'][1]['measurements']
        self.assertEqual(pair['raw_contact']['value'], 6)
        self.assertEqual(distance['expected_contact']['value'], 3.25)
        self.assertEqual(distance['distance_population_variance']['value'], 7.5625)
        self.assertAlmostEqual(pair['fold_enrichment']['value'], 24 / 13)
        before = chromatin_record_digest(sheet)
        parameters['normalization'] = {'kind': 'raw', 'weight_column': None, 'convention': None}
        with patch('gene_annotation_episode.chromatin_hic_inputs.read_hic_contacts', side_effect=AssertionError('no_native_reparse')), patch('socket.socket', side_effect=AssertionError('no_network')):
            with read_chromatin_sheet_tables(sheet, streams=streams) as views:
                raw_result = calculate_chromatin_components(sheet, tables=views, parameters=parameters)
        (directory / 'saved_raw_components.json').write_text(json.dumps(raw_result, indent=2) + '\n')
        raw_contact = raw_result['contact']['populations'][0]
        self.assertEqual(raw_contact['distance_expectations'][1]['measurements']['expected_contact']['value'], 4)
        self.assertEqual(raw_contact['pairs'][0]['measurements']['fold_enrichment']['value'], 1.5)
        self.assertEqual(chromatin_record_digest(sheet), before)

    def test_native_masks_invalid_vectors_and_missing_vector(self):
        for variant, counts in [('nan', (3, 1, 0)), ('zero', (3, 0, 1)), ('negative', (3, 0, 1)), ('inf', (3, 0, 1))]:
            with self.subTest(variant=variant):
                raw, _ = fixture(f'native009/{variant}/output.hic')
                sheet, streams, directory = sheet_for(raw, request_for(raw, weighted=True))
                summary = sheet['populations'][0]['normalization']
                self.assertEqual(tuple(summary[key] for key in ('valid_bin_count', 'masked_bin_count', 'invalid_bin_count')), counts)
                result, _ = calculate(sheet, streams, directory)
                distance = result['contact']['populations'][0]['distance_expectations'][1]['measurements']
                self.assertEqual(distance['expected_contact']['value'], 6 if variant == 'nan' else None)
                if variant == 'nan':
                    self.assertEqual(distance['masked_distance_pair_count']['value'], 1)
        raw, _ = fixture('native004/four.hic')
        sheet, streams, directory = sheet_for(raw, request_for(raw, weighted=True))
        result, _ = calculate(sheet, streams, directory)
        pair = result['contact']['populations'][0]['pairs'][0]['measurements']
        self.assertEqual(pair['raw_contact']['value'], 6)
        self.assertIsNone(pair['fold_enrichment']['value'])
        self.assertEqual(pair['fold_enrichment']['reason'], 'normalization_missing')

    def test_present_zero_block_and_absent_matrix_are_different(self):
        raw, _ = fixture('native010/present_zero_block/output.hic')
        sheet, streams, directory = sheet_for(raw, request_for(raw))
        p = sheet['populations'][0]
        self.assertEqual(p['extent'], 'complete')
        self.assertEqual(p['raw_cell_population']['implicit_zero_directed_cells'], 16)
        self.assertEqual(p['read_evidence']['expected_block_count'], 0)
        result, _ = calculate(sheet, streams, directory)
        pair = result['contact']['populations'][0]['pairs'][0]['measurements']
        self.assertEqual(pair['raw_contact']['value'], 0)
        self.assertEqual(pair['fold_enrichment']['reason'], 'zero_denominator')
        raw, audit = fixture('native010/present_zero_block/output.hic')
        raw = absent_master_entry(raw, audit)
        sheet, streams, directory = sheet_for(raw, request_for(raw))
        p = sheet['populations'][0]
        self.assertEqual(p['bin_count'], 4)
        self.assertIsNone(p['raw_cell_population']['implicit_zero_directed_cells'])
        self.assertIsNone(p['raw_cell_population']['stored_rows'])
        self.assertIsNone(p['pair_rows'][0]['raw_contact']['value'])
        self.assertIn('hic_matrix_absent', {f['code'] for f in sheet['failures']})
        raw, audit = fixture('native005/empty_input/output.hic')
        self.assertEqual(audit['footer_nbytes_v5'], -8)
        out, _, _, _ = extract(raw, request_for(raw), 'official hictk empty-input file has invalid negative footer size')
        self.assertIn('malformed_native_index', {f['code'] for f in out['failures']})
        self.assertIsNone(out['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'])

    def test_terminal_bins_native_indices_and_population_independent_header(self):
        for name, indices in [('terminal_two_chromosomes', [0, 1]), ('terminal_with_all', [1, 2])]:
            raw, _ = fixture(f'native005/{name}/output.hic')
            request = request_for(raw, chromosome='chrB', length=35)
            out, descriptors, streams, _ = extract(raw, request)
            self.assertEqual([c['chromosome_index'] for c in out['chromosomes']], indices)
            with open_chromatin_contact_tables(descriptors, streams=streams) as tables:
                self.assertEqual(tables['populations']['p0']['bins']['end_bp'].tolist(), [10, 20, 30, 35])
                self.assertEqual(tables['populations']['p0']['bins']['bin_id'].tolist(), [0, 1, 2, 3])
            request['populations'] = [{'population_key': 'a', 'chromosome': 'chrA', 'start_bp': 0, 'end_bp': 40}]
            other, _, _, _ = extract(raw, request)
            self.assertEqual(out['native_metadata'], other['native_metadata'])
            if name.endswith('all'):
                first = out['native_metadata']['hic']['chromosomes'][0]
                self.assertEqual((first['kind'], first['length_unit']), ('all_by_all', 'kb_proxy'))
        raw, _ = fixture('native005/terminal_with_all/output.hic')
        for region, code in [({'start_bp': 31, 'end_bp': 35}, 'population_boundary_not_bin_aligned'),
                             ({'start_bp': 0, 'end_bp': 40}, 'population_unavailable')]:
            request = request_for(raw, chromosome='chrB', length=35)
            request['populations'][0].update(region)
            out, _, _, _ = extract(raw, request)
            self.assertIn(code, {f['code'] for f in out['failures']})

    def test_padding_and_short_normalization_preserve_raw(self):
        raw, audit = fixture('native010/normalization_terminal_padding/output.hic')
        sheet, _, _ = sheet_for(raw, request_for(raw, weighted=True))
        witness = sheet['populations'][0]['read_evidence']['hic']['selected_normalization']
        self.assertEqual((witness['n_values_declared'], witness['extra_terminal_values']), (5, 1))
        raw, audit = fixture('native009/valid/output.hic')
        position = audit['normalization_vectors'][0]['position']
        short = changed(raw, position, struct.pack('<q', 3), 'vector declared shorter than physical chromosome')
        out, _, _, _ = extract(short, request_for(short, weighted=True))
        p = out['populations'][0]
        self.assertEqual(p['raw_cell_population']['stored_rows'], 9)
        self.assertEqual(p['normalization']['availability'], 'missing')
        self.assertEqual(p['extent'], 'complete')
        subregion = request_for(short, weighted=True)
        subregion['populations'][0]['end_bp'] = 20
        out, _, _, _ = extract(short, subregion, 'short chromosome vector remains unavailable before its missing tail')
        self.assertEqual(out['populations'][0]['normalization']['availability'], 'missing')

    def test_six_bin_insulation_values_from_native_bytes(self):
        raw, _ = fixture('native005/six_insulation/output.hic')
        request = request_for(raw, length=60)
        request.update(analysis_modes=['cross_window_insulation_heuristic'], elements=None)
        sheet, streams, directory = sheet_for(raw, request)
        result, parameters = calculate(sheet, streams, directory, insulation=True)
        p = result['insulation']['populations'][0]
        self.assertEqual([row['measurements']['cross_contact_sum']['value'] for row in p['windows']], [5, 1, 5, 1, 5])
        self.assertEqual(p['statistics']['z_population_mean']['value'], 3.4)
        self.assertAlmostEqual(p['statistics']['z_population_variance']['value'], 3.84)
        self.assertEqual([row['measurements']['boundary_position_bp']['value'] for row in p['windows'] if row['measurements']['is_boundary']['value']], [20, 40])
        self.assertEqual(p['domains'][0]['measurements']['domain_length_bp']['value'], 20)
        parameters['insulation']['z_threshold'] = -1.3
        changed_result, _ = calculate(sheet, streams, directory, parameters=parameters)
        self.assertEqual(changed_result['insulation']['populations'][0]['domains'], [])

    def test_native_nonfinite_values_are_not_dense_fillers(self):
        for name in ('rowlist_nonfinite', 'rowlist_i16_minus32768'):
            raw, audit = fixture(f'native010/{name}/output.hic')
            out, descriptors, streams, _ = extract(raw, request_for(raw))
            with open_chromatin_contact_tables(descriptors, streams=streams) as views:
                arrays = views['populations']['p0']
                native = audit['matrices'][0]['zooms'][0]['blocks'][0]
                self.assertEqual(len(arrays['contacts']), native['n_records'])
                if name.endswith('nonfinite'):
                    self.assertEqual(sorted(arrays['cell_states']['state'].tolist()), [2, 3, 4])
                    self.assertTrue(np.isnan(arrays['contacts']['value']).any())
                else:
                    self.assertIn(-32768, arrays['contacts']['value'].tolist())
                    self.assertIn('native_value_negative', {f['code'] for f in out['failures']})

    def test_real_v8_new_version_digest_and_stream_alias_rejection(self):
        raw = V8.read_bytes()
        out, _, _, _ = extract(raw, request_for(raw), 'genuine retained upstream v8 rejection fixture')
        self.assertEqual(out['failures'][0]['code'], 'unsupported_native_version')
        self.assertIsNone(out['native_metadata'])
        raw, _ = fixture('native004/four.hic')
        version = changed(raw, 4, struct.pack('<i', 10), 'unsupported future version')
        out, _, _, _ = extract(version, request_for(version))
        self.assertEqual(out['failures'][0]['code'], 'unsupported_native_version')
        request = request_for(raw)
        request['contact']['file']['sha256'] = '0' * 64
        out, _, _, _ = extract(raw, request)
        self.assertEqual(out['failures'][0]['code'], 'input_digest_mismatch')
        source = io.BytesIO(raw)
        streams = {('p0', role): io.BytesIO() for role in TABLE_ROLES}
        streams[('p0', 'contacts')] = source
        with self.assertRaises(ChromatinValidationError):
            read_hic_contacts(source, spec=request['contact'], normalization=request['normalization'], populations=request['populations'], table_streams=streams)
        self.assertEqual(source.getvalue(), raw)

    def test_native_multiblock_exact_records_and_corrupt_block_preserves_partial(self):
        raw, audit = fixture('native005/sparse_multiblock/output.hic')
        zoom = audit['matrices'][0]['zooms'][0]
        length = audit['chromosomes'][0]['native_length']
        request = request_for(raw, length=length, resolution=zoom['resolution'])
        request.update(elements=None, analysis_modes=['cross_window_insulation_heuristic'])
        out, descriptors, streams, _ = extract(raw, request)
        native_rows = sorted((r['x'], r['y'], r['value'], b['block_id'], r['ordinal']) for b in zoom['blocks'] for r in b['records'])
        self.assertEqual(out['populations'][0]['read_evidence']['read_block_count'], 7)
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            self.assertEqual([tuple(row) for row in views['populations']['p0']['contacts']], native_rows)
        block = zoom['blocks'][-1]
        offset = block['position'] + block['compressed_size'] - 1
        corrupt = changed(raw, offset, bytes([raw[offset] ^ 1]), 'last native block zlib checksum byte corrupted')
        request['contact']['file'] = identity(corrupt, 'hic_binary_v9')
        sheet, _, _ = sheet_for(corrupt, request, label='declared native checksum corruption')
        population = sheet['populations'][0]
        self.assertEqual(population['extent'], 'partial')
        self.assertEqual(population['read_evidence']['read_block_count'], 6)
        self.assertEqual(population['read_evidence']['failed_block_ids'], [block['block_id']])
        self.assertIsNone(population['raw_cell_population']['implicit_zero_directed_cells'])
        self.assertGreaterEqual(population['raw_cell_population']['stored_rows'], len(native_rows) - block['n_records'])

    def test_truncated_duplicate_and_out_of_range_block_indexes_keep_coherent_prefix(self):
        raw, audit = fixture('native005/sparse_multiblock/output.hic')
        matrix, entry = audit['matrices'][0], audit['master_index_entries'][0]
        zoom = matrix['zooms'][0]
        index_start = zoom['zoom_index_position'] + zoom['zoom_index_size'] - 16 * len(zoom['blocks'])
        master_size_field = audit['footer_position'] + 12 + len(entry['key'].encode()) + 1 + 8
        mutations = [
            ('truncated zoom index', master_size_field, struct.pack('<i', entry['size'] - 8), 6),
            ('duplicate block ID excludes both ambiguous entries', index_start + 16, struct.pack('<i', zoom['blocks'][0]['block_id']), 5),
            ('out of file block offset', index_start + 6 * 16 + 4, struct.pack('<q', len(raw) + 100), 6),
        ]
        for name, offset, replacement, read_count in mutations:
            with self.subTest(name=name):
                altered = changed(raw, offset, replacement, name)
                request = request_for(altered, length=audit['chromosomes'][0]['native_length'], resolution=zoom['resolution'])
                request.update(elements=None, analysis_modes=['cross_window_insulation_heuristic'])
                sheet, _, _ = sheet_for(altered, request, label=name)
                p = sheet['populations'][0]
                self.assertEqual(p['extent'], 'partial')
                self.assertEqual(p['read_evidence']['expected_block_count'], 7)
                self.assertEqual(p['read_evidence']['read_block_count'], read_count)
                self.assertGreater(p['raw_cell_population']['stored_rows'], 0)
                self.assertIsNone(p['raw_cell_population']['implicit_zero_directed_cells'])

    def test_duplicate_reversed_and_nonfinite_duplicate_rows_are_retained(self):
        raw, audit = fixture('native010/rowlist_f32_x32_y32/output.hic')
        def modify(payload, kind):
            fields = rowlist_fields(payload)
            if kind == 'reversed':
                struct.pack_into('<i', payload, fields[0][0], 1)
            else:
                struct.pack_into('<i', payload, fields[2][0], 0)
                if kind == 'nonfinite_duplicate':
                    struct.pack_into('<f', payload, fields[2][2], math.nan)
            return payload
        for kind in ('duplicate', 'reversed', 'nonfinite_duplicate'):
            with self.subTest(kind=kind):
                altered = changed_payload(raw, audit, lambda p: modify(p, kind), kind)
                sheet, streams, directory = sheet_for(altered, request_for(altered), label='explicit native row corruption: ' + kind)
                population = sheet['populations'][0]
                self.assertEqual(population['extent'], 'partial')
                self.assertEqual(population['raw_cell_population']['stored_rows'], 9)
                self.assertIsNone(population['raw_cell_population']['implicit_zero_directed_cells'])
                code = 'malformed_native_index' if kind == 'reversed' else 'duplicate_native_pixel'
                self.assertIn(code, {f['code'] for f in sheet['failures']})
                with read_chromatin_sheet_tables(sheet, streams=streams) as views:
                    self.assertEqual(len(views['populations']['p0']['contacts']), 9)
                result, _ = calculate(sheet, streams, directory)
                pair = result['contact']['populations'][0]['pairs'][0]['measurements']
                self.assertEqual(pair['raw_contact']['value'], 6)
                self.assertIsNone(pair['fold_enrichment']['value'])
                if kind == 'reversed':
                    self.assertEqual(population['raw_cell_population']['validated_observed_row_count'], 8)

    def test_invalid_flags_cardinality_short_and_trailing_payloads(self):
        raw, audit = fixture('native004/four.hic')
        def field(payload, offset, fmt, value):
            struct.pack_into('<' + fmt, payload, offset, value)
            return payload
        cases = [('unknown value flag', lambda p: field(p, 12, 'B', 2), 'hic_block_encoding_unsupported', 0),
                 ('unknown representation', lambda p: field(p, 15, 'B', 3), 'hic_block_encoding_unsupported', 0),
                 ('record cardinality mismatch', lambda p: field(p, 0, 'i', 8), 'malformed_native_index', 9),
                 ('dense slot cardinality mismatch', lambda p: field(p, 16, 'i', 15), 'malformed_native_index', 8),
                 ('trailing decoded payload', lambda p: p + b'\0\0', 'malformed_native_index', 9),
                 ('truncated decoded payload', lambda p: p[:-4], 'native_output_partial', 8)]
        for name, modify, code, count in cases:
            with self.subTest(name=name):
                altered = changed_payload(raw, audit, modify, name)
                out, _, _, _ = extract(altered, request_for(altered), name)
                self.assertEqual(out['populations'][0]['extent'], 'partial')
                self.assertIsNone(out['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'])
                self.assertEqual(out['populations'][0]['raw_cell_population']['stored_rows'], count)
                self.assertIn(code, {f['code'] for f in out['failures']})
        zoom = audit['matrices'][0]['zooms'][0]
        compressed_size_field = zoom['zoom_index_position'] + zoom['zoom_index_size'] - 4
        shortened = changed(raw, compressed_size_field, struct.pack('<i', zoom['blocks'][0]['compressed_size'] - 2),
                            'indexed compressed stream ends before its checksum trailer')
        out, _, _, _ = extract(shortened, request_for(shortened))
        block = out['populations'][0]['read_evidence']['hic']['blocks'][0]
        self.assertFalse(block['zlib_eof'])
        self.assertFalse(block['zlib_checksum_valid'])
        self.assertEqual(out['populations'][0]['extent'], 'partial')
        self.assertIsNone(out['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'])

    def test_high_compression_ratio_is_streamed_without_dense_population_allocation(self):
        raw, audit = fixture('native004/four.hic')
        def extended(payload):
            struct.pack_into('<i', payload, 16, 200000)
            return payload + struct.pack('<f', math.nan) * (200000 - 16)
        altered = changed_payload(raw, audit, extended, 'large dense filler payload, deliberately over 10:1 compression')
        out, _, _, _ = extract(altered, request_for(altered), 'explicit high-compression native-format stress mutation')
        block = out['populations'][0]['read_evidence']['hic']['blocks'][0]
        self.assertGreater(block['decoded_size_bytes'] / block['compressed_range']['size_bytes'], 10)
        self.assertEqual(block['n_records_decoded'], 9)
        self.assertEqual(block['dense_filler_slot_count'], 199991)
        self.assertEqual(out['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'], 2)

    def test_trailing_compressed_payload_preserves_decoded_records_without_zeros(self):
        raw, audit = fixture('native004/four.hic')
        altered = changed_payload(raw, audit, lambda p: p, 'trailing compressed-range bytes', compressed_suffix=b'JUNK')
        out, _, _, _ = extract(altered, request_for(altered), 'valid first zlib stream followed by illegal bytes in same indexed block')
        p = out['populations'][0]
        self.assertEqual(p['extent'], 'partial')
        self.assertIsNone(p['raw_cell_population']['implicit_zero_directed_cells'])
        self.assertEqual(p['raw_cell_population']['stored_rows'], 9)
        self.assertIn('malformed_native_index', {f['code'] for f in out['failures']})

    def test_regular_supplied_files_inode_alias_and_no_hdf5_import(self):
        import sys
        raw, _ = fixture('native004/four.hic')
        request = request_for(raw)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            path = Path(tmp) / 'source.hic'
            path.write_bytes(raw)
            with path.open('rb') as source:
                outputs = {('p0', role): (Path(tmp) / role).open('w+b') for role in TABLE_ROLES}
                try:
                    result = read_hic_contacts(source, spec=request['contact'], normalization=request['normalization'], populations=request['populations'], table_streams=outputs)
                    self.assertEqual(result['populations'][0]['extent'], 'complete')
                    self.assertFalse(source.closed)
                    self.assertTrue(all(not f.closed for f in outputs.values()))
                    with path.open('r+b') as alias:
                        with self.assertRaises(ChromatinValidationError):
                            read_hic_contacts(source, spec=request['contact'], normalization=request['normalization'], populations=request['populations'], table_streams=outputs | {('p0', 'contacts'): alias})
                finally:
                    for output in outputs.values():
                        output.close()
            self.assertEqual(path.read_bytes(), raw)
        self.assertNotIn('h5py', sys.modules)

    def test_missing_resolution_pseudochromosome_truncated_footer_and_bad_header(self):
        raw, audit = fixture('native005/terminal_with_all/output.hic')
        request = request_for(raw, resolution=20)
        out, _, _, _ = extract(raw, request, 'selected BP resolution absent')
        self.assertIn('hic_resolution_absent', {f['code'] for f in out['failures']})
        self.assertIsNone(out['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'])
        request = request_for(raw, chromosome='All', length=1)
        out, _, _, _ = extract(raw, request, 'reserved aggregate is not BP chromosome')
        self.assertIn('hic_pseudochromosome_unsupported', {f['code'] for f in out['failures']})
        duplicate = changed(raw, raw.index(b'chrB\0'), b'chrA\0', 'duplicate native chromosome name')
        out, _, _, _ = extract(duplicate, request_for(duplicate))
        self.assertIsNone(out['native_metadata'])
        self.assertIn('malformed_native_header', {f['code'] for f in out['failures']})
        raw, audit = fixture('native004/four.hic')
        for cut in (3, 7, audit['header_end'] - 1, audit['footer_position'], audit['footer_position'] + 10):
            with self.subTest(cut=cut):
                truncated = raw[:cut]
                out, _, _, directory = extract(truncated, request_for(truncated), f'explicit truncation of native004 at byte {cut}')
                (directory / 'truncation.json').write_text(json.dumps({'original_sha256': hashlib.sha256(raw).hexdigest(), 'cut_offset': cut}) + '\n')
                self.assertTrue(out['failures'])
                self.assertIsNone(out['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'])

    def test_exact_normalization_identity_broken_index_truncated_vector_and_raw_independence(self):
        raw, audit = fixture('native009/valid/output.hic')
        request = request_for(raw, weighted=True)
        request['normalization']['weight_column'] = 'KR'
        out, _, _, _ = extract(raw, request, 'different exact native normalization type')
        self.assertEqual(out['populations'][0]['normalization']['availability'], 'missing')
        vector = audit['normalization_vectors'][0]
        nvi_field = raw.index(b'\0', 16) + 1
        absent_nvi = changed(raw, nvi_field, struct.pack('<qq', 0, 0), 'header declares no normalization index')
        variants = [
            changed(raw, vector['position'], struct.pack('<q', 5), 'declared normalization values exceed actual vector bytes'),
            changed(raw, audit['normalization_index_position'], struct.pack('<i', 2), 'truncated normalization index entry list'),
            raw[:-2],
            absent_nvi,
        ]
        for altered in variants:
            with self.subTest(sha256=hashlib.sha256(altered).hexdigest()):
                out, descriptors, streams, _ = extract(altered, request_for(altered, weighted=True), 'explicit normalization damage')
                p = out['populations'][0]
                self.assertEqual(p['normalization']['availability'], 'missing')
                self.assertEqual(p['extent'], 'complete')
                self.assertEqual(p['raw_cell_population']['stored_rows'], 9)
                with open_chromatin_contact_tables(descriptors, streams=streams) as views:
                    self.assertIsNone(views['populations']['p0']['weights'])
                    self.assertEqual(len(views['populations']['p0']['contacts']), 9)
                raw_out, _, _, _ = extract(altered, request_for(altered), 'raw mode does not decode unused damaged normalization payload')
                self.assertEqual(raw_out['populations'][0]['extent'], 'complete')
                self.assertEqual(raw_out['populations'][0]['normalization']['availability'], 'not_requested')
                if altered == absent_nvi:
                    self.assertIn('hic_normalization_index_unavailable', {f['code'] for f in out['failures']})
                    self.assertEqual(p['read_evidence']['hic']['selected_normalization']['index_extent'], 'unavailable')
        request = request_for(raw, weighted=True)
        request['normalization']['convention'] = 'multiplicative'
        with self.assertRaises(ChromatinValidationError):
            extract(raw, request, 'invalid API normalization convention')

    def test_native004_selected_population_controls_denominator(self):
        raw, _ = fixture('native004/four.hic')
        for end, expected, variance, fold in ((40, 4, 4, 1.5), (30, 6, 0, 1)):
            with self.subTest(end=end):
                request = request_for(raw)
                request['populations'][0]['end_bp'] = end
                sheet, streams, directory = sheet_for(raw, request, label='official native004 exact selected comparison population')
                result, _ = calculate(sheet, streams, directory)
                contact = result['contact']['populations'][0]
                pair, distance = contact['pairs'][0]['measurements'], contact['distance_expectations'][1]['measurements']
                self.assertEqual(pair['raw_contact']['value'], 6)
                self.assertEqual(pair['fold_enrichment']['value'], fold)
                self.assertEqual(distance['expected_contact']['value'], expected)
                self.assertEqual(distance['distance_population_variance']['value'], variance)
                self.assertEqual(distance['nominal_distance_pair_count']['value'], 2 if end == 40 else 1)

    def test_terminal_anchor_and_two_chromosome_local_bin_namespaces(self):
        raw, _ = fixture('native005/terminal_with_all/output.hic')
        request = request_for(raw, chromosome='chrB', length=35)
        request['elements']['assignments'] = [row for row in request['elements']['assignments'] if row['source_data_row'] < 2]
        for row in request['elements']['assignments']:
            row['anchor'] = {'policy': 'interval_start'}
        sheet, _, _ = sheet_for(raw, request, bed=b'chrB\t1\t2\tE\nchrB\t34\t35\tP\n')
        self.assertEqual(sheet['populations'][0]['pair_rows'][0]['promoter_bin_id'], 3)
        self.assertEqual(sheet['populations'][0]['pair_rows'][0]['promoter_anchor_bp'], 34)
        request['populations'] = [request['populations'][0] | {'population_key': 'B'},
            {'population_key': 'A', 'chromosome': 'chrA', 'start_bp': 0, 'end_bp': 40}]
        for reference in (request['elements']['reference'], request['supplied_metadata']['reference']):
            reference['contigs'] = [{'chromosome': 'chrA', 'length_bp': 40}, {'chromosome': 'chrB', 'length_bp': 35}]
        sheet, streams, _ = sheet_for(raw, request, bed=b'chrB\t1\t2\tE\nchrB\t34\t35\tP\n')
        self.assertEqual([p['population_key'] for p in sheet['populations']], ['B', 'A'])
        with read_chromatin_sheet_tables(sheet, streams=streams) as views:
            self.assertEqual([int(views['populations'][p]['bins'][0]['bin_id']) for p in ('B', 'A')], [0, 0])
            self.assertEqual([int(views['populations'][p]['bins'][0]['chromosome_index']) for p in ('B', 'A')], [2, 1])


if __name__ == '__main__':
    unittest.main()
