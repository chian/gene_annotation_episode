from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from gene_annotation_episode.chromatin_interaction_inputs import (
    parse_chromatin_elements, extract_chromatin_metadata, build_chromatin_sheet,
)
from gene_annotation_episode.chromatin_interaction_tables import open_chromatin_contact_tables, read_chromatin_sheet_tables
from gene_annotation_episode.chromatin_interaction_contracts import ChromatinValidationError
from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_digest
from tests.test_chromatin_cooler_inputs import FIXTURES, identity, request_for, extract
from tests.test_chromatin_cooler_inputs import synthetic


def build_native_sheet(*, weighted=False, bed=None, assignments=None):
    raw = (FIXTURES / 'four-bin-raw-weighted.cool').read_bytes()
    request = request_for(raw, weighted=weighted)
    bed = b'chrA\t1\t2\tE\t0\t.\nchrA\t21\t22\tP\t0\t.\nchrA\t31\t32\tQ\t0\t.\n' if bed is None else bed
    request['elements']['file'] = identity(bed, 'bed_outer_span_v1')
    request['elements']['reference']['assembly_label'] = None
    if assignments is not None:
        request['elements']['assignments'] = assignments
    contacts, descriptors, streams = extract(raw, request)
    elements = parse_chromatin_elements(bed, spec=request['elements'])
    metadata = extract_chromatin_metadata(request=request, native=contacts, supplied=request['supplied_metadata'], elements=elements)
    with open_chromatin_contact_tables(descriptors, streams=streams) as arrays:
        sheet = build_chromatin_sheet(request=request, contacts=contacts, elements=elements, metadata=metadata, tables=descriptors, table_views=arrays)
    directory = Path.cwd() / 'saved_sheets' / chromatin_record_digest(sheet)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'sheet.json').write_text(json.dumps(sheet, indent=2, allow_nan=False))
    for key, stream in streams.items():
        (directory / (key + '.table')).write_bytes(stream.getvalue())
    return sheet, streams


class InputsTest(unittest.TestCase):
    def test_genuine_native_sheet_and_saved_loading(self):
        sheet, streams = build_native_sheet(weighted=True)
        pairs = sheet['populations'][0]['pair_rows']
        self.assertEqual([p['raw_contact']['value'] for p in pairs], [6, 0])
        self.assertEqual([p['cell_origin'] for p in pairs], ['explicit_native', 'explicit_native'])
        self.assertEqual(pairs[0]['source_locators'][0]['value']['row_index'], 2)
        with patch('h5py.File', side_effect=AssertionError('saved_reader_must_not_reacquire_native')), read_chromatin_sheet_tables(sheet, streams=streams) as views:
            self.assertEqual(views['populations']['p0']['weights'].tolist(), [1, 2, 1, 2])
        changed = deepcopy(sheet)
        changed['populations'][0]['pair_rows'][0]['raw_contact']['value'] = 99
        with self.assertRaises(ChromatinValidationError), read_chromatin_sheet_tables(changed, streams=streams):
            pass

    def test_occurrences_columns_lines_and_explicit_classes(self):
        bed = b'# original\r\ntrack name=synthetic\nchrA\t10\t11\tpromoter word\t0\t.\textra\n\nchrA\t39\t40\tdup\nchrA\t39\t40\tdup\nchrA\t50\t51\toutside\n'
        assignments = [{'element_key': 'E', 'source_data_row': 0, 'class': 'enhancer', 'gene_links': [], 'anchor': {'policy': 'interval_start'}},
                       {'element_key': 'P', 'source_data_row': 1, 'class': 'promoter', 'gene_links': [{'gene_key': 'gene1', 'relationship': 'promoter_of', 'source_ref': 'supplied:gene'}], 'anchor': {'policy': 'interval_start'}},
                       {'element_key': 'P2', 'source_data_row': 2, 'class': 'promoter', 'gene_links': [], 'anchor': {'policy': 'interval_start'}}]
        sheet, _ = build_native_sheet(bed=bed, assignments=assignments)
        elements = sheet['elements']
        self.assertEqual(elements['input_data_row_count'], 4)
        self.assertEqual(elements['rows'][0]['source_line'], 3)
        self.assertEqual(elements['rows'][0]['columns'][-1], 'extra')
        self.assertEqual(elements['rows'][0]['class'], 'enhancer')
        self.assertEqual(len(elements['other_lines']), 3)
        self.assertEqual(len(elements['rejected_rows']), 1)
        self.assertEqual(len(sheet['populations'][0]['pair_rows']), 2)
        self.assertEqual([p['promoter_bin_id'] for p in sheet['populations'][0]['pair_rows']], [3, 3])

    def test_metadata_exact_inputs_and_reference_conflict(self):
        raw = (FIXTURES / 'four-bin-raw-weighted.cool').read_bytes()
        request = request_for(raw)
        request['elements']['reference']['assembly_label'] = 'one'
        request['supplied_metadata']['reference']['assembly_label'] = 'two'
        contacts, _, _ = extract(raw, request)
        metadata = extract_chromatin_metadata(request=request, native=contacts, supplied=request['supplied_metadata'], elements=None)
        self.assertEqual(metadata['reference_relations'][0]['relation'], 'conflicting_assertions')
        other = deepcopy(request['supplied_metadata'])
        other['reference']['assembly_label'] = 'changed'
        with self.assertRaises(ChromatinValidationError):
            extract_chromatin_metadata(request=request, native=contacts, supplied=other, elements=None)
        self.assertEqual([a['input_key'] for a in metadata['reference_assertions']], ['contact0', 'contact0', 'elements0'])

    def test_missing_assignment_and_anchor_outside_not_inferred(self):
        raw = (FIXTURES / 'four-bin-raw-weighted.cool').read_bytes()
        request = request_for(raw)
        bed = b'chrA\t0\t1\tenhancer\nchrA\t20\t21\tpromoter\n'
        request['elements']['file'] = identity(bed, 'bed_outer_span_v1')
        request['elements']['assignments'] = []
        elements = parse_chromatin_elements(bed, spec=request['elements'])
        self.assertEqual([r['class'] for r in elements['rows']], [None, None])
        self.assertEqual(elements['extent'], 'partial')
        request['elements']['assignments'] = [{'element_key': 'E', 'source_data_row': 0, 'class': 'enhancer', 'gene_links': [], 'anchor': {'policy': 'supplied_position', 'position_bp': 1}}]
        elements = parse_chromatin_elements(bed, spec=request['elements'])
        self.assertEqual(elements['rejected_rows'][0]['failures'][0]['code'], 'anchor_outside_element')

    def test_saved_normalization_reference_element_and_population_tampering(self):
        sheet, streams = build_native_sheet(weighted=True)
        changes = [lambda s: s['populations'][0]['normalization'].__setitem__('valid_bin_count', 3),
                   lambda s: s['references']['relations'][0].__setitem__('relation', 'conflicting_assertions'),
                   lambda s: s['elements']['rows'][0].__setitem__('class', 'promoter'),
                   lambda s: s['populations'][0]['raw_cell_population'].__setitem__('directed_cells', 15),
                   lambda s: s['populations'][0]['raw_cell_population'].__setitem__('stored_rows', 9)]
        for change in changes:
            modified = deepcopy(sheet)
            change(modified)
            with self.assertRaises(ChromatinValidationError), read_chromatin_sheet_tables(modified, streams=streams):
                pass

    def test_retained_state_dense_and_locator_conflicts(self):
        import io
        import numpy as np
        from gene_annotation_episode.chromatin_interaction_tables import STATES_DTYPE
        sheet, streams = build_native_sheet()
        tests = [('cell_states', np.array([(0, 2, 2)], dtype=STATES_DTYPE)),
                 ('dense_values', np.zeros((4, 4), dtype='<i8'))]
        for role, array in tests:
            changed = deepcopy(sheet)
            supplied = dict(streams)
            descriptor = next(d for d in changed['data_tables'] if d['role'] == role)
            buffer = io.BytesIO(); np.save(buffer, array, allow_pickle=False)
            descriptor.update(availability='present', absence_reason=None, encoding='npy', shape=list(array.shape), row_count=len(array), extent='complete', file=identity(buffer.getvalue(), 'chromatin_contact_tables_v1:' + role))
            if role == 'dense_values':
                descriptor['dtype_descriptor'] = {'kind': 'scalar', 'dtype': '<i8'}
            supplied[descriptor['table_key']] = buffer
            with self.assertRaises(ChromatinValidationError), read_chromatin_sheet_tables(changed, streams=supplied):
                pass
        changed = deepcopy(sheet)
        descriptor = next(d for d in changed['data_tables'] if d['role'] == 'contacts')
        data = np.load(io.BytesIO(streams[descriptor['table_key']].getvalue()), allow_pickle=False)
        data['source_row'][0] = 99
        buffer = io.BytesIO(); np.save(buffer, data, allow_pickle=False)
        descriptor['file'] = identity(buffer.getvalue(), descriptor['file']['format'])
        supplied = dict(streams); supplied[descriptor['table_key']] = buffer
        with self.assertRaises(ChromatinValidationError), read_chromatin_sheet_tables(changed, streams=supplied):
            pass

    def test_located_malformed_lower_row_preserved_in_partial_sheet(self):
        raw = synthetic(pixels=[(0, 1, 2), (1, 0, 3)])
        request = request_for(raw)
        request['analysis_modes'] = ['cross_window_insulation_heuristic']
        request['elements'] = None
        extraction, descriptors, streams = extract(raw, request)
        metadata = extract_chromatin_metadata(request=request, native=extraction, supplied=request['supplied_metadata'], elements=None)
        with open_chromatin_contact_tables(descriptors, streams=streams) as arrays:
            sheet = build_chromatin_sheet(request=request, contacts=extraction, elements=None, metadata=metadata, tables=descriptors, table_views=arrays)
            self.assertEqual(arrays['populations']['p0']['contacts']['bin1_id'].tolist(), [0, 1])
            self.assertEqual(sheet['populations'][0]['extent'], 'partial')
            self.assertEqual(sheet['populations'][0]['raw_cell_population']['validated_observed_row_count'], 1)
