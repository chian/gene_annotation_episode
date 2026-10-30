"""HIC witness/array consistency, without native reads or scientific scoring."""
from __future__ import annotations

import numpy as np

from .chromatin_interaction_contracts import ChromatinValidationError


def _require(condition, code):
    if not condition:
        raise ChromatinValidationError(code)


def located_hic_row_failure(population, row, code='malformed_native_index'):
    witness = population['read_evidence'].get('hic')
    if witness is None:
        return False
    expected = {'chromosome1_index': witness['chromosome1_index'],
                'chromosome2_index': witness['chromosome2_index'],
                'resolution_bp': witness['resolution_bp'],
                'block_id': int(row['source_block']), 'record_ordinal': int(row['source_row'])}
    return any(problem['code'] == code and problem['stage'] == 'native_parse'
               and problem['population_key'] == population['population_key']
               and problem['locator'] == {'kind': 'hic_block', 'value': expected}
               for problem in population['failures'])


def validate_hic_population_arrays(population, arrays, chromosomes):
    bins, contacts, states = (arrays[role] for role in ('bins', 'contacts', 'cell_states'))
    evidence = population['read_evidence']
    witness = evidence.get('hic')
    if bins is not None:
        width = population['fixed_bin_size_bp']
        _require(width is not None and np.all(bins['bin_id'] == bins['start_bp'] // width),
                 'hic_chromosome_local_bin_ids_required')
    _require(arrays['dense_values'] is None, 'hic_dense_values_not_native_representation')
    weights = arrays['weights']
    if weights is not None:
        vector = None if witness is None else witness['selected_normalization']
        _require(vector is not None and vector['outcome'] == 'complete', 'hic_weights_without_vector_proof')
        # Weight custody is independent of whether the contact table survived.
        # The canonical float64 vector widens the native float32 values exactly.
        widened = weights.astype('<f4').astype('<f8')
        _require(np.all((weights == widened) | (np.isnan(weights) & np.isnan(widened))),
                 'hic_weight_not_native_float32')
    if contacts is None:
        _require(evidence['selected_records_extent'] != 'complete', 'hic_complete_contact_array_required')
        return
    _require(contacts.dtype.fields['value'][0].str == '<f4', 'hic_canonical_float32_required')
    if witness is None:
        _require(not len(contacts), 'hic_contacts_without_matrix_witness')
        return
    blocks = {block['block_id']: block for block in witness['blocks']}
    retained = {key: 0 for key in blocks}
    for row in contacts:
        block_id, ordinal = int(row['source_block']), int(row['source_row'])
        _require(block_id in blocks, 'hic_contact_block_not_read')
        block = blocks[block_id]
        _require(block['outcome'] in ('complete', 'partial') and block['n_records_decoded'] is not None,
                 'hic_contact_from_unavailable_block')
        retained[block_id] += 1
        if block['record_ordinal_kind'] == 'sparse_record':
            _require(0 <= ordinal < block['n_records_decoded'], 'hic_sparse_record_ordinal_outside_block')
            _require(block['matrix_representation'] == 1, 'hic_record_ordinal_kind_mismatch')
        elif block['record_ordinal_kind'] == 'dense_slot':
            _require(block['matrix_representation'] == 2 and block['dense_slot_count'] is not None
                     and block['dense_width'] is not None and 0 <= ordinal < block['dense_slot_count'],
                     'hic_dense_slot_ordinal_outside_block')
            _require(int(row['bin1_id']) == block['bin_x_offset'] + ordinal % block['dense_width']
                     and int(row['bin2_id']) == block['bin_y_offset'] + ordinal // block['dense_width'],
                     'hic_dense_slot_coordinate_mismatch')
            filler = (np.isnan(row['value']) if block['value_encoding'] == 'float32'
                      else row['value'] == -32768)
            _require(not filler, 'hic_dense_filler_is_not_contact')
        else:
            raise ChromatinValidationError('hic_contact_ordinal_kind_required')
        if int(row['bin1_id']) > int(row['bin2_id']):
            _require(population['extent'] == 'partial' and located_hic_row_failure(population, row),
                     'lower_triangular_native_pixel')
    for block_id, block in blocks.items():
        count = block['retained_population_record_count']
        _require((count is None and retained[block_id] == 0) or count == retained[block_id],
                 'hic_retained_record_array_mismatch')
    # The canonical sort is by coordinates. Check source occurrence uniqueness
    # separately using an integer permutation, without one Python object per row.
    if len(contacts) > 1:
        order = np.lexsort((contacts['source_row'], contacts['source_block']))
        for start in range(1, len(order), 65536):
            end = min(start + 65536, len(order))
            right, left = order[start:end], order[start - 1:end - 1]
            _require(not np.any((contacts['source_block'][right] == contacts['source_block'][left])
                               & (contacts['source_row'][right] == contacts['source_row'][left])),
                     'hic_duplicate_source_occurrence')
        del order
    if states is not None:
        for state in states:
            if state['state'] in (1, 5):
                _require(evidence['implicit_zero_semantics'] == 'not_established'
                         and evidence['selected_records_extent'] != 'complete'
                         and population['extent'] != 'complete', 'hic_unresolved_state_claimed_complete')
            lo = int(np.searchsorted(contacts['bin1_id'], state['bin1_id'], side='left'))
            hi = int(np.searchsorted(contacts['bin1_id'], state['bin1_id'], side='right'))
            local = contacts[lo:hi]
            begin = int(np.searchsorted(local['bin2_id'], state['bin2_id'], side='left'))
            end = int(np.searchsorted(local['bin2_id'], state['bin2_id'], side='right'))
            rows = local[begin:end]
            if state['state'] in (2, 3, 4):
                matches = (np.isnan(rows['value']) if state['state'] == 2 else
                           np.isposinf(rows['value']) if state['state'] == 3 else np.isneginf(rows['value']))
                _require(np.any(matches), 'hic_nonfinite_state_has_no_native_record')
            if int(state['bin1_id']) > int(state['bin2_id']):
                _require(population['extent'] == 'partial'
                         and any(located_hic_row_failure(population, row) for row in rows),
                         'lower_triangular_native_pixel')
def hic_duplicate_nonfinite_state(population, rows, state):
    """A retained finite/nonfinite duplicate is a diagnostic, never sparse zero."""
    if population['extent'] != 'partial' or len(rows) < 2:
        return False
    tag = int(state['state'])
    if tag not in (2, 3, 4):
        return False
    matches = (np.isnan(rows['value']) if tag == 2 else
               np.isposinf(rows['value']) if tag == 3 else np.isneginf(rows['value']))
    return bool(np.any(matches) and any(located_hic_row_failure(population, row, 'duplicate_native_pixel')
                                       for row in rows))


def validate_hic_table_locators(population, metadata, descriptors):
    """Bind canonical table provenance to the same saved native byte witnesses."""
    witness = population['read_evidence'].get('hic')
    def byte_locator(value, section):
        return {'kind': 'hic_bytes', 'value': {'offset': value['offset'],
                'size_bytes': value['size_bytes'], 'section': section}}
    for descriptor in descriptors:
        if descriptor['availability'] != 'present':
            continue
        role, locator = descriptor['role'], descriptor['native_source_locator']
        if role == 'bins':
            allowed = [] if metadata is None else [byte_locator(metadata['hic']['header_range'], 'header')]
            if witness is not None:
                allowed += [byte_locator(witness[name], 'zoom_index')
                            for name in ('matrix_metadata_range', 'zoom_index_range')]
            _require(locator in allowed, 'hic_bin_table_source_mismatch')
        elif role in ('contacts', 'cell_states'):
            _require(witness is not None and locator == byte_locator(witness['zoom_index_range'], 'zoom_index'),
                     'hic_contact_table_source_mismatch')
        elif role == 'weights':
            vector = None if witness is None else witness['selected_normalization']
            expected = None if vector is None else {'kind': 'hic_vector', 'value': {
                name: vector[name] for name in ('normalization_type', 'chromosome_index', 'unit', 'resolution_bp')}}
            if expected is not None:
                expected['value']['bin_index'] = None
            _require(expected is not None and locator == expected, 'hic_weight_table_source_mismatch')
