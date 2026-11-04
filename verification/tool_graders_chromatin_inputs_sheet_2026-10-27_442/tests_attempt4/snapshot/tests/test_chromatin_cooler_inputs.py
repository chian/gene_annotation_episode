from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import h5py
import numpy as np

from gene_annotation_episode.chromatin_interaction_contracts import TABLE_ROLES
from gene_annotation_episode.chromatin_cooler_inputs import read_cooler_contacts
from gene_annotation_episode.chromatin_interaction_tables import open_chromatin_contact_tables
from tests.test_chromatin_interaction_contracts import examples

FIXTURES = Path('/home/chia/repos/gene_annotation_episode/verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures')


def identity(raw, format):
    digest = hashlib.sha256(raw).hexdigest()
    return {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': len(raw), 'format': format}


def request_for(raw, *, weighted=False, n=4):
    request = deepcopy(examples()['raw.sheet']['request'])
    request['contact']['file'] = identity(raw, 'cooler_hdf5_v3')
    request['populations'][0]['end_bp'] = n * 10
    request['supplied_metadata']['reference']['contigs'][0]['length_bp'] = n * 10
    request['supplied_metadata']['reference']['assembly_label'] = None
    if weighted:
        request['normalization'] = {'kind': 'precomputed_weighted', 'weight_column': 'weight', 'convention': 'multiplicative'}
    return request


def extract(raw, request):
    streams = {(p['population_key'], role): io.BytesIO() for p in request['populations'] for role in TABLE_ROLES}
    source = io.BytesIO(raw)
    extraction = read_cooler_contacts(source, spec=request['contact'], normalization=request['normalization'], populations=request['populations'], table_streams=streams)
    assert not source.closed
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    retained = Path.cwd() / 'native_cases' / key
    retained.mkdir(parents=True, exist_ok=True)
    (retained / 'input.cool').write_bytes(raw)
    (retained / 'request.json').write_text(json.dumps(request, indent=2))
    (retained / 'extraction.json').write_text(json.dumps(extraction, indent=2, allow_nan=False))
    tables, supplied = [], {}
    for draft in extraction['table_drafts']:
        data = streams[(draft['population_key'], draft['role'])].getvalue()
        tables.append(draft | {'file': identity(data, 'chromatin_contact_tables_v1:' + draft['role']) if draft['availability'] == 'present' else None})
        if draft['availability'] == 'present':
            supplied[draft['table_key']] = io.BytesIO(data)
            (retained / (draft['table_key'] + ('.tsv' if draft['encoding'] == 'tsv' else '.npy'))).write_bytes(data)
    (retained / 'descriptors.json').write_text(json.dumps(tables, indent=2, allow_nan=False))
    return extraction, tables, supplied


def mutate(raw, change):
    buffer = io.BytesIO(raw)
    with h5py.File(buffer, 'r+') as file:
        change(file)
    return buffer.getvalue()


def synthetic(*, n=4, pixels=None, weights=None, storage='symmetric-upper', variable=False, group='/'):
    buffer = io.BytesIO()
    if pixels is None:
        pixels = []
    a = np.array([row[0] for row in pixels], dtype='<i8')
    b = np.array([row[1] for row in pixels], dtype='<i8')
    values = np.array([row[2] for row in pixels], dtype='<f4')
    with h5py.File(buffer, 'w') as root:
        file = root if group == '/' else root.create_group(group)
        file.attrs.update({'format': 'HDF5::Cooler', 'format-version': 3, 'storage-mode': storage, 'bin-type': 'variable' if variable else 'fixed'})
        if not variable:
            file.attrs['bin-size'] = 10
        file.create_dataset('chroms/name', data=np.array([b'chrA']))
        file.create_dataset('chroms/length', data=[n * 10])
        file.create_dataset('bins/chrom', data=np.zeros(n, dtype='<i8'))
        file.create_dataset('bins/start', data=np.arange(n, dtype='<i8') * 10)
        file.create_dataset('bins/end', data=np.arange(1, n + 1, dtype='<i8') * 10)
        if weights is not None:
            file.create_dataset('bins/weight', data=np.array(weights, dtype='<f4'))
        file.create_dataset('pixels/bin1_id', data=a)
        file.create_dataset('pixels/bin2_id', data=b)
        file.create_dataset('pixels/count', data=values)
        file.create_dataset('indexes/chrom_offset', data=[0, n])
        file.create_dataset('indexes/bin1_offset', data=np.searchsorted(a, np.arange(n + 1), side='left').astype('<i8'))
    return buffer.getvalue()


class CoolerInputsTest(unittest.TestCase):
    def test_actual440_four_bin_native_dtypes_counts_locators_weights(self):
        raw = (FIXTURES / 'four-bin-raw-weighted.cool').read_bytes()
        request = request_for(raw, weighted=True)
        extraction, descriptors, streams = extract(raw, request)
        self.assertEqual(extraction['populations'][0]['extent'], 'complete', extraction['failures'])
        self.assertEqual(extraction['native_metadata']['native_value_dtype'], '<i4')
        self.assertEqual(extraction['native_metadata']['value_dtype'], '<i8')
        with open_chromatin_contact_tables(descriptors, streams=streams) as tables:
            p = tables['populations']['p0']
            self.assertEqual(p['contacts']['value'].tolist(), [4, 2, 6, 0, 4, 2, 2, 4, 2, 4])
            self.assertEqual(p['contacts']['source_row'].tolist(), list(range(10)))
            self.assertTrue(np.all(p['contacts']['source_block'] == -1))
            self.assertEqual(p['weights'].tolist(), [1, 2, 1, 2])
            self.assertFalse(p['contacts'].flags.writeable)
            self.assertIsNone(p['dense_values'])
        self.assertEqual(extraction['populations'][0]['raw_cell_population']['explicit_zero_rows'], 1)
        self.assertEqual(extraction['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'], 0)

    def test_actual440_sparse_omissions(self):
        raw = (FIXTURES / 'six-bin-all-full-windows.cool').read_bytes()
        extraction, descriptors, streams = extract(raw, request_for(raw, n=6))
        population = extraction['populations'][0]
        self.assertEqual(population['raw_cell_population']['implicit_zero_directed_cells'], 25)
        self.assertEqual(population['raw_cell_population']['stored_rows'], 6)
        self.assertEqual(population['read_evidence']['implicit_zero_semantics'], 'validated_sparse_absence')

    def test_genuine_empty_sparse_matrix_is_not_failed_read(self):
        raw = synthetic()
        extraction, descriptors, streams = extract(raw, request_for(raw))
        p = extraction['populations'][0]
        self.assertEqual(p['raw_cell_population']['implicit_zero_directed_cells'], 16)
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            self.assertEqual(len(views['populations']['p0']['contacts']), 0)
        bad = b'not HDF5'
        failed, _, _ = extract(bad, request_for(bad))
        self.assertIsNone(failed['native_metadata'])
        self.assertIsNone(failed['populations'][0]['bin_count'])
        self.assertIsNone(failed['populations'][0]['raw_cell_population']['directed_cells'])

    def test_missing_weight_keeps_raw_and_masks_stay_native(self):
        raw = synthetic(pixels=[(0, 1, 0), (1, 2, 2)])
        extraction, descriptors, streams = extract(raw, request_for(raw, weighted=True))
        self.assertEqual(extraction['populations'][0]['extent'], 'complete')
        self.assertEqual(extraction['populations'][0]['normalization']['availability'], 'missing')
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            self.assertIsNone(views['populations']['p0']['weights'])
            self.assertEqual(len(views['populations']['p0']['contacts']), 2)
        raw = synthetic(weights=[1, np.nan, 0, -2])
        extraction, descriptors, streams = extract(raw, request_for(raw, weighted=True))
        summary = extraction['populations'][0]['normalization']
        self.assertEqual((summary['valid_bin_count'], summary['masked_bin_count'], summary['invalid_bin_count']), (1, 1, 2))
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            self.assertTrue(np.isnan(views['populations']['p0']['weights'][1]))
            self.assertEqual(views['populations']['p0']['weights'][3], -2)

    def test_duplicate_negative_and_nonfinite_native_rows_preserved(self):
        raw = synthetic(pixels=[(0, 1, 2), (0, 1, 3), (1, 2, -4), (2, 3, np.nan)])
        extraction, descriptors, streams = extract(raw, request_for(raw))
        codes = {row['code'] for row in extraction['failures']}
        self.assertTrue({'duplicate_native_pixel', 'native_value_negative', 'native_value_nonfinite'} <= codes)
        self.assertEqual(extraction['populations'][0]['extent'], 'partial')
        self.assertEqual(extraction['populations'][0]['read_evidence']['implicit_zero_semantics'], 'not_established')
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            self.assertEqual(len(views['populations']['p0']['contacts']), 4)
            self.assertEqual(views['populations']['p0']['contacts']['value'][2], -4)
            self.assertEqual(views['populations']['p0']['cell_states']['state'].tolist(), [2])

    def test_index_boundary_external_version_and_partial_populations(self):
        raw = synthetic(pixels=[(0, 1, 2)])
        corrupt = mutate(raw, lambda f: f['indexes/bin1_offset'].__setitem__(-1, 999))
        out, _, _ = extract(corrupt, request_for(corrupt))
        self.assertEqual(out['failures'][0]['code'], 'malformed_native_index')
        external = mutate(raw, lambda f: f.__setitem__('outside', h5py.ExternalLink('/nonexistent/file', '/data')))
        out, _, _ = extract(external, request_for(external))
        self.assertEqual(out['failures'][0]['code'], 'external_native_dependency_unbound')
        version = mutate(raw, lambda f: f.attrs.__setitem__('format-version', 2))
        out, _, _ = extract(version, request_for(version))
        self.assertEqual(out['failures'][0]['code'], 'unsupported_native_version')
        request = request_for(raw)
        request['populations'].append({'population_key': 'p1', 'chromosome': 'chrA', 'start_bp': 1, 'end_bp': 30})
        out, _, _ = extract(raw, request)
        self.assertEqual([p['extent'] for p in out['populations']], ['complete', 'unavailable'])
        self.assertEqual(out['populations'][1]['failures'][0]['code'], 'population_boundary_not_bin_aligned')

    def test_explicit_group_variable_bins_and_terminal_short_bin(self):
        raw = synthetic(variable=True, group='/resolutions/10')
        request = request_for(raw)
        request['contact'].update(group_path='/resolutions/10', resolution_bp=None)
        out, _, _ = extract(raw, request)
        self.assertEqual(out['populations'][0]['bin_count'], 4)
        self.assertIn('incompatible_variable_bins', [f['code'] for f in out['failures']])
        raw = mutate(synthetic(), lambda f: (f['chroms/length'].__setitem__(0, 35), f['bins/end'].__setitem__(-1, 35)))
        request = request_for(raw)
        request['populations'][0]['end_bp'] = 35
        out, _, _ = extract(raw, request)
        self.assertEqual(out['populations'][0]['extent'], 'complete', out['failures'])

    def test_square_reciprocity_and_nonreciprocal_retention(self):
        for pixels, expected in (([(0, 1, 2), (1, 0, 2)], 'square_reciprocal_verified'), ([(0, 1, 2)], 'not_established')):
            raw = synthetic(storage='square', pixels=pixels)
            out, descriptors, streams = extract(raw, request_for(raw))
            self.assertEqual(out['populations'][0]['read_evidence']['symmetry'], expected)
            with open_chromatin_contact_tables(descriptors, streams=streams) as views:
                self.assertEqual(len(views['populations']['p0']['contacts']), len(pixels))

    def test_empty_corrupt_index_range_cannot_claim_zero(self):
        raw = synthetic(pixels=[(0, 1, 2), (1, 2, 3)])
        raw = mutate(raw, lambda f: f['indexes/bin1_offset'].__setitem__(1, 0))
        request = request_for(raw)
        request['populations'][0]['end_bp'] = 10
        out, descriptors, streams = extract(raw, request)
        self.assertEqual(out['populations'][0]['extent'], 'partial')
        self.assertEqual(out['populations'][0]['read_evidence']['implicit_zero_semantics'], 'not_established')

    def test_corrupt_native_chunk_retains_independent_read_rows(self):
        raw = synthetic(pixels=[(0, 0, 4), (0, 1, 2), (1, 2, 3), (2, 3, 4)])
        buffer = io.BytesIO(raw)
        with h5py.File(buffer, 'r+') as file:
            values = file['pixels/count'][:]
            del file['pixels/count']
            dataset = file.create_dataset('pixels/count', data=values, chunks=(2,), fletcher32=True)
            file.flush()
            chunk = dataset.id.get_chunk_info_by_coord((2,))
            offset = chunk.byte_offset
        data = bytearray(buffer.getvalue())
        data[offset] ^= 1
        raw = bytes(data)
        out, descriptors, streams = extract(raw, request_for(raw))
        self.assertEqual(out['populations'][0]['extent'], 'partial', out['failures'])
        self.assertEqual(out['populations'][0]['raw_cell_population']['stored_rows'], 2)
        self.assertIn('native_chunk_unavailable', [f['code'] for f in out['failures']])
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            self.assertEqual(views['populations']['p0']['contacts']['source_row'].tolist(), [0, 1])

    def test_corrupt_weight_chunk_preserves_complete_raw_counts(self):
        buffer = io.BytesIO(synthetic(pixels=[(0, 1, 2)], weights=[1, 1, 1, 1]))
        with h5py.File(buffer, 'r+') as file:
            del file['bins/weight']
            vector = file.create_dataset('bins/weight', data=np.ones(4), chunks=(4,), fletcher32=True)
            file.flush()
            offset = vector.id.get_chunk_info_by_coord((0,)).byte_offset
        data = bytearray(buffer.getvalue()); data[offset] ^= 1
        raw = bytes(data)
        out, descriptors, streams = extract(raw, request_for(raw, weighted=True))
        self.assertEqual(out['populations'][0]['extent'], 'complete')
        self.assertEqual(out['populations'][0]['normalization']['availability'], 'missing')
        with open_chromatin_contact_tables(descriptors, streams=streams) as views:
            self.assertEqual(views['populations']['p0']['contacts']['value'].tolist(), [2])
            self.assertIsNone(views['populations']['p0']['weights'])

    def test_input_identity_stream_aliases_and_unknown_version(self):
        raw = synthetic()
        request = request_for(raw)
        request['contact']['file']['sha256'] = '0' * 64
        out, _, _ = extract(raw, request)
        self.assertEqual(out['failures'][0]['code'], 'input_digest_mismatch')
        source = io.BytesIO(raw)
        streams = {('p0', role): io.BytesIO() for role in TABLE_ROLES}
        streams[('p0', 'contacts')] = source
        with self.assertRaises(ValueError):
            read_cooler_contacts(source, spec=request_for(raw)['contact'], normalization=request['normalization'], populations=request['populations'], table_streams=streams)
        self.assertEqual(source.getvalue(), raw)
