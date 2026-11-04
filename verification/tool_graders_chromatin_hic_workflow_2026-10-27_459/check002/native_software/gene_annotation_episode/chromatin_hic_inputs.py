"""HIC v9 BP cis contacts from immutable supplied streams, without acquisition.

All indexed blocks of the selected matrix zoom are visited. Counts are made in
one bounded decode and the same bytes decoded again into caller-owned canonical
tables; sorting uses those supplied outputs, never a dense chromosome or a list
of all contacts. Normalization vectors are retained, not calculated or inverted.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import math
import os
import stat

import numpy as np

from .chromatin_interaction_contracts import (
    TABLE_ROLES, ChromatinValidationError, validate_chromatin_record,
)
from .chromatin_interaction_tables import (
    BINS_HEADER, CHUNK_ROWS, STATES_DTYPE, contacts_dtype, dtype_descriptor,
)
from .chromatin_cooler_inputs import (
    failure, _empty_population, _table_key, _npy_start, _finalize_sort,
    _read_written_array, NativeReadError,
)
from .chromatin_hic_binary import (
    Cursor, HicReadError, byte_locator, hashed_range, read_header, read_indexes,
    read_matrix, decode_block,
)


def _draft(population, role, *, availability='present', reason=None, shape=None,
           dtype=None, extent='complete', locator=None):
    present = availability == 'present'
    return {'table_key': _table_key(population, role), 'population_key': population['population_key'],
            'role': role, 'availability': availability, 'absence_reason': reason,
            'encoding': ('tsv' if role == 'bins' else 'npy') if present else None,
            'shape': shape if present else None, 'dtype_descriptor': dtype if present else None,
            'row_count': shape[0] if present else None, 'native_source_locator': locator,
            'extent': extent if present else 'unavailable'}


def _block_locator(chromosome, resolution, block, ordinal=None):
    return {'kind': 'hic_block', 'value': {'chromosome1_index': chromosome,
            'chromosome2_index': chromosome, 'resolution_bp': resolution,
            'block_id': block, 'record_ordinal': ordinal}}


def _vector_locator(name, chromosome, resolution, index=None):
    return {'kind': 'hic_vector', 'value': {'normalization_type': name,
            'chromosome_index': chromosome, 'unit': 'BP', 'resolution_bp': resolution,
            'bin_index': index}}


def _range_locator(value, section):
    return byte_locator(value['offset'], value['size_bytes'], section)


def _issue(result, spec, selected, code, locator, field=None, requirement='valid_native_structure'):
    row = failure(code, spec=spec, population=selected, locator=locator, requirement=requirement)
    row['field_path'] = field
    result['failures'].append(row)


def _absent_drafts(result, selected, normalization, drafts, code):
    present_roles = {row['role'] for row in drafts}
    for role in TABLE_ROLES:
        if role not in present_roles:
            availability = ('not_native_representation' if role == 'dense_values' else
                            'not_requested' if role == 'weights' and normalization['kind'] == 'raw' else 'unavailable')
            drafts.append(_draft(selected, role, availability=availability,
                                 reason=code if availability == 'unavailable' else None))
    drafts.sort(key=lambda row: TABLE_ROLES.index(row['role']))
    return result, drafts


def _native_metadata(spec, header, chromosomes, attributes, vectors):
    reference = {'assembly_accession': None,
                 'assembly_label': None if header['genome_id'] in ('', 'unknown') else header['genome_id'],
                 'contigs': [{'chromosome': row['chromosome'], 'length_bp': row['length_bp']} for row in chromosomes],
                 'source_ref': spec['source_ref']}
    return {'source_file': deepcopy(spec['file']), 'source_ref': spec['source_ref'],
            'format': 'hic_binary_v9', 'format_version': 9, 'group_path': None,
            'coordinate_system': 'zero_based_half_open', 'bin_type': 'fixed',
            'bin_size_bp': spec['resolution_bp'], 'storage_mode': 'hic-symmetric',
            'value_field': 'count', 'value_dtype': '<f4',
            'native_value_dtype': 'hic_v9_block_int16_or_float32',
            'value_kind': spec['value_kind'], 'value_unit': spec['value_unit'],
            'attributes': attributes, 'vectors': vectors, 'reference_assertion': reference,
            'hic': header}


def _weights(stream, size, indexes, spec, selected, result, low, high, physical, ci, target):
    normalization = result['normalization']['specification']
    name, resolution = normalization['weight_column'], spec['resolution_bp']
    locator = _vector_locator(name, ci, resolution)
    witness = {'normalization_type': name, 'chromosome_index': ci, 'unit': 'BP',
               'resolution_bp': resolution,
               'index_extent': 'complete' if indexes['normalization_complete'] else 'partial' if indexes['normalizations'] else 'unavailable',
               'native_range': None, 'n_values_declared': None, 'n_values_read': None,
               'native_dtype': None, 'selected_bin_start': low, 'selected_bin_end_exclusive': high,
               'physical_chromosome_bin_count': physical, 'extra_terminal_values': None,
               'outcome': 'unavailable'}
    result['read_evidence']['hic']['selected_normalization'] = witness
    code = 'normalization_missing'
    if not indexes['normalization_complete']:
        for error in indexes['normalization_errors']:
            _issue(result, spec, selected, error.code, error.locator, error.field)
        code = 'hic_normalization_index_unavailable'
    else:
        entry = indexes['normalizations'].get((name, ci, 'BP', resolution))
        if entry is not None:
            witness['native_range'] = deepcopy(entry)
            try:
                witness['native_range'] = hashed_range(stream, size, entry['offset'], entry['size_bytes'], 'normalization_vector')
                cursor = Cursor(stream, size, entry['offset'], entry['offset'] + entry['size_bytes'], section='normalization_vector')
                n = cursor.nonnegative('q')
                witness.update(n_values_declared=n, n_values_read=0, native_dtype='<f4',
                               extra_terminal_values=max(0, n - physical))
                exact_length = entry['size_bytes'] == 8 + n * 4
                compatible = n >= physical and exact_length
                if compatible:
                    _npy_start(target, np.dtype('<f8'), high - low)
                written = valid = masked = bad = 0
                while witness['n_values_read'] < n:
                    begin = witness['n_values_read']
                    take = min(CHUNK_ROWS, n - begin, (cursor.end - cursor.pos) // 4)
                    if not take:
                        raise HicReadError('native_output_partial', _range_locator(entry, 'normalization_vector'))
                    values = np.frombuffer(cursor.read(take * 4), dtype='<f4')
                    witness['n_values_read'] += take
                    a, b = max(0, low - begin), min(take, high - begin)
                    if compatible and a < b:
                        chosen = values[a:b].astype('<f8')
                        target.write(chosen.tobytes())
                        written += len(chosen)
                        valid += int(np.count_nonzero(np.isfinite(chosen) & (chosen > 0)))
                        masked += int(np.count_nonzero(np.isnan(chosen)))
                        bad += int(np.count_nonzero((~np.isfinite(chosen) & ~np.isnan(chosen)) | (chosen <= 0)))
                        for ordinal in np.flatnonzero(~np.isfinite(chosen) | (chosen <= 0)):
                            value = chosen[ordinal]
                            _issue(result, spec, selected, 'normalization_masked_bin' if np.isnan(value) else 'normalization_weight_invalid',
                                   _vector_locator(name, ci, resolution, begin + a + int(ordinal)),
                                   requirement='finite_positive_weights')
                if not compatible or cursor.pos != cursor.end or written != high - low:
                    witness['outcome'] = 'incompatible'
                    code = 'normalization_weight_invalid'
                else:
                    witness['outcome'] = 'complete'
                    result['normalization'].update(availability='partial' if bad else 'available',
                        vector_table_key=_table_key(selected, 'weights'), native_weight_dtype='<f4',
                        valid_bin_count=valid, masked_bin_count=masked, invalid_bin_count=bad)
                    return _draft(selected, 'weights', shape=[high - low], dtype={'kind': 'scalar', 'dtype': '<f8'}, locator=locator)
            except HicReadError as exc:
                code = exc.code
                witness['outcome'] = 'partial' if witness['n_values_read'] is not None else 'unavailable'
                _issue(result, spec, selected, code, exc.locator or locator, exc.field,
                       requirement='selected_weight_vector')
    _issue(result, spec, selected, code, locator, requirement='selected_weight_vector')
    return _draft(selected, 'weights', availability='unavailable', reason=code, locator=locator)


class _CanonicalWriter:
    def __init__(self, contacts, states, dtype):
        self.contacts, self.states, self.dtype = contacts, states, dtype
        self.rows = np.empty(CHUNK_ROWS, dtype=dtype)
        self.count = self.written = self.state_count = 0

    def add(self, x, y, value, block, ordinal):
        self.rows[self.count] = (x, y, value, block, ordinal)
        self.count += 1
        if self.count == len(self.rows):
            self.flush()

    def flush(self):
        rows = self.rows[:self.count]
        self.contacts.write(rows.tobytes())
        exceptional = ~np.isfinite(rows['value'])
        count = int(np.count_nonzero(exceptional))
        if count:
            states = np.empty(count, dtype=STATES_DTYPE)
            states['bin1_id'], states['bin2_id'] = rows['bin1_id'][exceptional], rows['bin2_id'][exceptional]
            values = rows['value'][exceptional]
            states['state'] = np.where(np.isnan(values), 2, np.where(values > 0, 3, 4))
            self.states.write(states.tobytes())
        self.state_count += count
        self.written += self.count
        self.count = 0


def _population(stream, size, spec, normalization, selected, table_streams, header, chromosomes, indexes):
    result = _empty_population(selected, normalization, 'population_unavailable')
    evidence = result['read_evidence']
    evidence['hic'] = None
    drafts = []
    try:
        raw_chromosome = next((c for c in header['chromosomes'] if c['chromosome'] == selected['chromosome']), None)
        if raw_chromosome is not None and raw_chromosome['kind'] == 'all_by_all':
            raise HicReadError('hic_pseudochromosome_unsupported', _range_locator(header['header_range'], 'header'))
        chromosome = next((c for c in chromosomes if c['chromosome'] == selected['chromosome']), None)
        if chromosome is None or selected['end_bp'] > chromosome['length_bp']:
            raise HicReadError('population_unavailable', _range_locator(header['header_range'], 'header'))
        ci, length, width = chromosome['chromosome_index'], chromosome['length_bp'], spec['resolution_bp']
        if selected['start_bp'] % width or selected['end_bp'] % width and selected['end_bp'] != length:
            raise HicReadError('population_boundary_not_bin_aligned', _range_locator(header['header_range'], 'header'))
        low, high, physical = selected['start_bp'] // width, (selected['end_bp'] + width - 1) // width, (length + width - 1) // width
        n = high - low
        result.update(bin_count=n, fixed_bin_size_bp=width)
        evidence['axes_extent'] = 'complete'
        result['raw_cell_population']['directed_cells'] = n * n
        target = table_streams[(selected['population_key'], 'bins')]
        target.seek(0); target.truncate(0); target.write(BINS_HEADER)
        for k in range(low, high):
            target.write(f'{k}\t{ci}\t{k * width}\t{min((k + 1) * width, length)}\n'.encode('ascii'))
        drafts.append(_draft(selected, 'bins', shape=[n, 4], dtype={'kind': 'scalar', 'dtype': 'utf8_tsv_int64'}, locator=_range_locator(header['header_range'], 'header')))
        for error in indexes['matrix_errors'] + indexes['auxiliary_errors']:
            _issue(result, spec, selected, error.code, error.locator, error.field)
        entry = indexes['matrices'].get(f'{ci}_{ci}')
        if entry is None:
            raise HicReadError('hic_matrix_absent' if indexes['matrix_complete'] else 'malformed_native_index',
                               _range_locator(indexes['matrix_range'], 'matrix_index') if indexes['matrix_range'] else byte_locator(header['footer_position'], 0, 'footer'))
        matrix = read_matrix(stream, size, header, entry, ci, width)
        for error in matrix['errors']:
            _issue(result, spec, selected, error.code, error.locator, error.field)
        zoom = matrix['zoom']
        if zoom is None:
            raise HicReadError('hic_resolution_absent' if matrix['complete'] else 'malformed_native_index',
                               _range_locator(matrix['metadata_range'], 'zoom_index'))
        result['native_storage_mode'] = 'hic-symmetric'
        evidence['symmetry'] = 'native_hic_symmetric'
        result['raw_cell_population']['unique_unordered_cells'] = n * (n + 1) // 2
        complete_index = indexes['matrix_complete'] and not indexes['auxiliary_errors'] and matrix['complete']
        evidence['hic'] = {'version': 'hic_population_read_v1', 'source_sha256': spec['file']['sha256'],
            'scan_scope': 'all_indexed_blocks_selected_cis_zoom', 'matrix_key': f'{ci}_{ci}',
            'matrix_index_range': indexes['matrix_range'], 'matrix_metadata_range': matrix['metadata_range'],
            'zoom_index_range': zoom['range'], 'chromosome1_index': ci, 'chromosome2_index': ci,
            'unit': 'BP', 'resolution_bp': width, 'block_bin_count': zoom['block_bin_count'],
            'block_column_count': zoom['block_column_count'], 'declared_block_count': zoom['declared_block_count'],
            'blocks': [], 'selected_normalization': None}
        counts = {'rows': 0, 'states': 0, 'zeros': 0, 'nonfinite': 0, 'observed': 0, 'represented': 0}
        coordinates_valid = True
        usable_entries = []
        previous_end = -1
        for native_entry in sorted(zoom['entries'], key=lambda row: row['offset']):
            if native_entry['offset'] < previous_end:
                complete_index = False
                _issue(result, spec, selected, 'malformed_native_index', native_entry['index_locator'], '/overlapping_block_ranges')
            previous_end = max(previous_end, native_entry['offset'] + native_entry['size_bytes'])
        for native_entry in zoom['entries']:
            block = native_entry['block_id']
            start, stop = native_entry['offset'], native_entry['offset'] + native_entry['size_bytes']
            # Out-of-file ranges get an unavailable block witness. Ranges that
            # point into unrelated native sections are excluded, never decoded
            # as if those sections were this matrix's contact values.
            metadata_overlap = any(start < item['position'] + item['size'] and stop > item['position']
                                   for item in indexes['matrices'].values())
            if stop <= size and (start < header['header_range']['size_bytes'] or stop > header['footer_position'] or metadata_overlap):
                complete_index = False
                _issue(result, spec, selected, 'malformed_native_index', native_entry['index_locator'])
                continue
            def count_record(x, y, value, ordinal):
                nonlocal coordinates_valid
                if not 0 <= x < physical or not 0 <= y < physical or x > y:
                    coordinates_valid = False
                    _issue(result, spec, selected, 'malformed_native_index', _block_locator(ci, width, block, ordinal), '/coordinates')
                if not (low <= x < high and low <= y < high):
                    return False
                directed = 1 if x == y else 2
                counts['rows'] += 1
                counts['represented'] += directed
                if not math.isfinite(value):
                    counts['states'] += 1
                    counts['nonfinite'] += directed
                    _issue(result, spec, selected, 'native_value_nonfinite', _block_locator(ci, width, block, ordinal), requirement='finite_nonnegative_contact_values')
                else:
                    counts['zeros'] += value == 0
                    if value < 0 and spec['value_kind'] == 'contact_count':
                        _issue(result, spec, selected, 'native_value_negative', _block_locator(ci, width, block, ordinal), requirement='finite_nonnegative_contact_values')
                    elif x <= y:
                        counts['observed'] += 1
                return True
            witness, errors = decode_block(stream, size, native_entry, count_record)
            evidence['hic']['blocks'].append(witness)
            usable_entries.append(native_entry)
            for error in errors:
                _issue(result, spec, selected, error.code, _block_locator(ci, width, block), error.field)
        contact_stream = table_streams[(selected['population_key'], 'contacts')]
        state_stream = table_streams[(selected['population_key'], 'cell_states')]
        dtype = contacts_dtype('<f4')
        offset = _npy_start(contact_stream, dtype, counts['rows'])
        state_offset = _npy_start(state_stream, STATES_DTYPE, counts['states'])
        writer = _CanonicalWriter(contact_stream, state_stream, dtype)
        for native_entry, previous in zip(usable_entries, evidence['hic']['blocks']):
            def write_record(x, y, value, ordinal):
                if low <= x < high and low <= y < high:
                    writer.add(x, y, value, native_entry['block_id'], ordinal)
                    return True
                return False
            actual, _ = decode_block(stream, size, native_entry, write_record)
            if actual != previous:
                raise HicReadError('input_digest_mismatch', _block_locator(ci, width, native_entry['block_id']))
        writer.flush()
        if writer.written != counts['rows'] or writer.state_count != counts['states']:
            raise HicReadError('native_output_partial', _range_locator(zoom['range'], 'zoom_index'))
        _finalize_sort(contact_stream, dtype, counts['rows'], offset, ['bin1_id', 'bin2_id', 'source_block', 'source_row'])
        _finalize_sort(state_stream, STATES_DTYPE, counts['states'], state_offset, ['bin1_id', 'bin2_id'])
        with _read_written_array(contact_stream, dtype, counts['rows'], offset) as rows:
            previous = None
            for row in rows:
                pair = (int(row['bin1_id']), int(row['bin2_id']))
                if pair == previous:
                    coordinates_valid = False
                    _issue(result, spec, selected, 'duplicate_native_pixel',
                           _block_locator(ci, width, int(row['source_block']), int(row['source_row'])))
                previous = pair
        blocks = evidence['hic']['blocks']
        complete = complete_index and coordinates_valid and len(blocks) == zoom['declared_block_count'] and all(row['outcome'] == 'complete' for row in blocks)
        extent = 'complete' if complete else 'partial'
        result['extent'] = extent
        evidence.update(index_extent='complete' if complete_index else 'partial', selected_records_extent=extent,
                        expected_block_count=zoom['declared_block_count'], read_block_count=sum(row['outcome'] == 'complete' for row in blocks),
                        failed_block_ids=[row['block_id'] for row in blocks if row['outcome'] != 'complete'],
                        implicit_zero_semantics='validated_sparse_absence' if complete else 'not_established')
        result['raw_cell_population'].update(stored_rows=counts['rows'], explicit_zero_rows=counts['zeros'],
            implicit_zero_directed_cells=n * n - counts['represented'] if complete else None,
            native_nonfinite_directed_cells=counts['nonfinite'], unavailable_directed_cells=0 if complete else None,
            validated_observed_row_count=counts['observed'])
        drafts[0]['native_source_locator'] = _range_locator(matrix['metadata_range'], 'zoom_index')
        drafts.extend([_draft(selected, 'contacts', shape=[counts['rows']], dtype=dtype_descriptor(dtype), extent=extent,
                              locator=_range_locator(zoom['range'], 'zoom_index')),
                       _draft(selected, 'cell_states', shape=[counts['states']], dtype=dtype_descriptor(STATES_DTYPE), extent=extent,
                              locator=_range_locator(zoom['range'], 'zoom_index'))])
        if normalization['kind'] != 'raw':
            drafts.append(_weights(stream, size, indexes, spec, selected, result, low, high, physical, ci,
                                   table_streams[(selected['population_key'], 'weights')]))
        return _absent_drafts(result, selected, normalization, drafts, 'population_unavailable')
    except (HicReadError, NativeReadError) as exc:
        if exc.code == 'input_digest_mismatch':
            raise
        _issue(result, spec, selected, exc.code, getattr(exc, 'locator', None), getattr(exc, 'field', None))
        result['extent'] = 'partial' if drafts else 'unavailable'
        result['read_evidence']['implicit_zero_semantics'] = 'not_established'
        witness = result['read_evidence']['hic']
        if witness is not None:
            evidence.update(index_extent='partial', selected_records_extent='unavailable',
                            expected_block_count=witness['declared_block_count'],
                            read_block_count=sum(b['outcome'] == 'complete' for b in witness['blocks']),
                            failed_block_ids=[b['block_id'] for b in witness['blocks'] if b['outcome'] != 'complete'])
        return _absent_drafts(result, selected, normalization, drafts, exc.code)


def _validate_streams(stream, populations, table_streams):
    if len({p['population_key'] for p in populations}) != len(populations):
        raise ChromatinValidationError('duplicate_population_key')
    required = {(p['population_key'], role) for p in populations for role in TABLE_ROLES}
    if set(table_streams) != required:
        raise ChromatinValidationError('exact_seekable_output_streams_required')
    all_streams = (stream, *table_streams.values())
    if len({id(s) for s in all_streams}) != len(all_streams):
        raise ChromatinValidationError('distinct_input_output_streams_required')
    identities = set()
    for selected in all_streams:
        try:
            if not selected.seekable() or (selected is stream and not selected.readable()) or (selected is not stream and not selected.writable()):
                raise ChromatinValidationError('binary_seekable_streams_required')
            if selected is stream:
                if not isinstance(selected.read(0), bytes):
                    raise ChromatinValidationError('binary_stream_required')
            elif isinstance(selected, io.TextIOBase):
                raise ChromatinValidationError('binary_stream_required')
            try:
                status = os.fstat(selected.fileno())
            except (AttributeError, io.UnsupportedOperation):
                if not isinstance(selected, io.BytesIO):
                    raise ChromatinValidationError('regular_file_or_small_memory_stream_required')
                continue
            if not stat.S_ISREG(status.st_mode):
                raise ChromatinValidationError('regular_file_required')
            identity = status.st_dev, status.st_ino
            if identity in identities:
                raise ChromatinValidationError('distinct_input_output_files_required')
            identities.add(identity)
        except (AttributeError, TypeError, OSError, ValueError) as exc:
            if isinstance(exc, ChromatinValidationError):
                raise
            raise ChromatinValidationError('binary_seekable_streams_required') from exc


def _identity(stream, identity):
    stream.seek(0)
    digest, count = hashlib.sha256(), 0
    while raw := stream.read(1024 * 1024):
        digest.update(raw)
        count += len(raw)
    if digest.hexdigest() != identity['sha256'] or count != identity['size_bytes']:
        raise HicReadError('input_digest_mismatch', byte_locator(0, count, 'header'))
    return count


def read_hic_contacts(stream, *, spec, normalization, populations, table_streams):
    """Finalize canonical tables and located native failures for supplied HIC v9."""
    spec = validate_chromatin_record('ContactSpec', spec)
    normalization = validate_chromatin_record('NormalizationSpec', normalization)
    populations = [validate_chromatin_record('PopulationSpec', value) for value in populations]
    if spec['format'] != 'hic_binary_v9' or spec['group_path'] is not None or spec['resolution_bp'] is None:
        raise ChromatinValidationError('hic_v9_bp_specification_required')
    if normalization['kind'] != 'raw' and normalization['convention'] != 'divisive':
        raise ChromatinValidationError('hic_requires_divisive_normalization')
    _validate_streams(stream, populations, table_streams)
    result = {'format': 'hic_binary_v9', 'format_version': None, 'native_metadata': None,
              'chromosomes': [], 'populations': [], 'table_drafts': [], 'failures': []}
    try:
        size = _identity(stream, spec['file'])
        header, chromosomes, attributes = read_header(stream, size)
        indexes = read_indexes(stream, size, header)
        result.update(format_version=9, chromosomes=chromosomes,
                      native_metadata=_native_metadata(spec, header, chromosomes, attributes, indexes['vectors']))
        for selected in populations:
            population, drafts = _population(stream, size, spec, normalization, selected, table_streams, header, chromosomes, indexes)
            result['populations'].append(population)
            result['table_drafts'].extend(drafts)
            result['failures'].extend(population['failures'])
        _identity(stream, spec['file'])
    except (HicReadError, MemoryError, OSError) as exc:
        code = exc.code if isinstance(exc, HicReadError) else 'resource_limit' if isinstance(exc, MemoryError) else 'native_chunk_unavailable'
        # A changed source identity invalidates its scientific association, even
        # if a syntactically valid output was written. Bytes remain caller-owned.
        if code == 'input_digest_mismatch':
            result.update(format_version=None, native_metadata=None, chromosomes=[], populations=[], table_drafts=[], failures=[])
        for selected in populations[len(result['populations']):]:
            population = _empty_population(selected, normalization, code)
            population['read_evidence']['hic'] = None
            _issue(population, spec, selected, code, getattr(exc, 'locator', None), getattr(exc, 'field', None))
            population, drafts = _absent_drafts(population, selected, normalization, [], code)
            result['populations'].append(population)
            result['table_drafts'].extend(drafts)
            result['failures'].extend(population['failures'])
    return validate_chromatin_record('ContactExtraction', result)
