from copy import deepcopy
import unittest

from gene_annotation_episode.chromatin_interaction_inputs import (
    parse_chromatin_elements, extract_chromatin_metadata, build_chromatin_sheet,
)
from gene_annotation_episode.chromatin_interaction_tables import open_chromatin_contact_tables, read_chromatin_sheet_tables
from gene_annotation_episode.chromatin_interaction_contracts import ChromatinValidationError
from tests.test_chromatin_cooler_inputs import FIXTURES, identity, request_for, extract


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
    return sheet, streams


class InputsTest(unittest.TestCase):
    def test_genuine_native_sheet_and_saved_loading(self):
        sheet, streams = build_native_sheet(weighted=True)
        pairs = sheet['populations'][0]['pair_rows']
        self.assertEqual([p['raw_contact']['value'] for p in pairs], [6, 0])
        self.assertEqual([p['cell_origin'] for p in pairs], ['explicit_native', 'explicit_native'])
        self.assertEqual(pairs[0]['source_locators'][0]['value']['row_index'], 2)
        with read_chromatin_sheet_tables(sheet, streams=streams) as views:
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
