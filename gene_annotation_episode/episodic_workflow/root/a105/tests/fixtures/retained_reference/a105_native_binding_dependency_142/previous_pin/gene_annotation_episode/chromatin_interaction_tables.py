"""Read-only, repeatable views over explicitly supplied canonical table streams."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import io
import mmap
import os
import re
import stat
from types import MappingProxyType

import numpy as np

from .chromatin_interaction_contracts import (
    TABLE_ROLES, ChromatinValidationError, validate_chromatin_record,
)

BINS_DTYPE = np.dtype([('bin_id', '<i8'), ('chromosome_index', '<i8'),
                       ('start_bp', '<i8'), ('end_bp', '<i8')])
STATES_DTYPE = np.dtype([('bin1_id', '<i8'), ('bin2_id', '<i8'), ('state', '|u1')])
BINS_HEADER = b'bin_id\tchromosome_index\tstart_bp\tend_bp\n'
CHUNK_ROWS = 65536


def contacts_dtype(value_dtype):
    if value_dtype not in ('<i8', '<u8', '<f4', '<f8'):
        raise ChromatinValidationError('unsupported_contact_dtype')
    return np.dtype([('bin1_id', '<i8'), ('bin2_id', '<i8'), ('value', value_dtype),
                     ('source_block', '<i8'), ('source_row', '<i8')])


def dtype_descriptor(dtype):
    if dtype.names is None:
        return {'kind': 'scalar', 'dtype': dtype.str}
    return {'kind': 'structured', 'fields': [
        {'name': name, 'dtype': dtype.fields[name][0].str} for name in dtype.names]}


def _expected_dtype(descriptor):
    role, value = descriptor['role'], descriptor['dtype_descriptor']
    if role == 'bins':
        if value != {'kind': 'scalar', 'dtype': 'utf8_tsv_int64'}:
            raise ChromatinValidationError('invalid_bins_dtype')
        return BINS_DTYPE
    if value['kind'] == 'scalar':
        dtype = np.dtype(value['dtype'])
    else:
        fields = [(row['name'], row['dtype']) for row in value['fields']]
        if len({name for name, _ in fields}) != len(fields):
            raise ChromatinValidationError('duplicate_dtype_field')
        dtype = np.dtype(fields)
    if role == 'contacts':
        if dtype.names != ('bin1_id', 'bin2_id', 'value', 'source_block', 'source_row') or dtype != contacts_dtype(dtype.fields['value'][0].str):
            raise ChromatinValidationError('invalid_contacts_dtype')
    elif role == 'cell_states' and dtype != STATES_DTYPE:
        raise ChromatinValidationError('invalid_cell_states_dtype')
    elif role == 'weights' and dtype != np.dtype('<f8'):
        raise ChromatinValidationError('invalid_weights_dtype')
    elif role == 'dense_values' and (dtype.names or dtype.str not in ('<i8', '<u8', '<f4', '<f8')):
        raise ChromatinValidationError('invalid_dense_dtype')
    return dtype


def _identity(stream, identity):
    if not stream.seekable() or not stream.readable():
        raise ChromatinValidationError('seekable_readable_stream_required')
    stream.seek(0)
    digest, size = hashlib.sha256(), 0
    while block := stream.read(1024 * 1024):
        if not isinstance(block, bytes):
            raise ChromatinValidationError('binary_stream_required')
        digest.update(block)
        size += len(block)
    if size != identity['size_bytes'] or digest.hexdigest() != identity['sha256']:
        raise ChromatinValidationError('artifact_digest_mismatch')
    stream.seek(0)
    return size


def _read_npy(stream, descriptor, size, mappings):
    version = np.lib.format.read_magic(stream)
    if version == (1, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
    elif version == (2, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_2_0(stream)
    else:
        raise ChromatinValidationError('unsupported_npy_version')
    expected = _expected_dtype(descriptor)
    offset = stream.tell()
    if dtype != expected or list(shape) != descriptor['shape'] or fortran or dtype.hasobject:
        raise ChromatinValidationError('npy_header_mismatch')
    count = 1
    for dimension in shape:
        count *= dimension
    if size != offset + count * dtype.itemsize:
        raise ChromatinValidationError('npy_length_mismatch')
    try:
        fd = stream.fileno()
    except (AttributeError, io.UnsupportedOperation):
        if not isinstance(stream, io.BytesIO) or size > 16 * 1024 * 1024:
            raise ChromatinValidationError('regular_file_or_small_memory_stream_required')
        # Tiny explicit test streams only. No unbounded production fallback.
        buffer = stream.getbuffer().toreadonly()
        mappings.append(buffer)
    else:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ChromatinValidationError('regular_table_file_required')
        buffer = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        mappings.append(buffer)
    array = np.ndarray(shape, dtype=dtype, buffer=buffer, offset=offset)
    array.flags.writeable = False
    return array


def _read_bins(stream, descriptor):
    _expected_dtype(descriptor)
    if stream.readline() != BINS_HEADER:
        raise ChromatinValidationError('invalid_bins_header')
    result = np.empty(descriptor['shape'][0], dtype=BINS_DTYPE)
    for index in range(len(result)):
        line = stream.readline(1024)
        if not line.endswith(b'\n'):
            raise ChromatinValidationError('incomplete_bins_row')
        fields = line[:-1].split(b'\t')
        if len(fields) != 4 or any(re.fullmatch(rb'0|[1-9][0-9]*', field) is None for field in fields):
            raise ChromatinValidationError('invalid_bins_integer')
        try:
            result[index] = tuple(int(field) for field in fields)
        except (OverflowError, ValueError) as exc:
            raise ChromatinValidationError('bins_integer_overflow') from exc
    if stream.read(1):
        raise ChromatinValidationError('extra_bins_rows')
    result.flags.writeable = False
    return result


def _ordered(array, fields):
    previous = None
    for start in range(0, len(array), CHUNK_ROWS):
        block = array[start:start + CHUNK_ROWS]
        for row in block:
            key = tuple(int(row[field]) for field in fields)
            if previous is not None and key < previous:
                raise ChromatinValidationError('unordered_contact_table')
            previous = key


def validate_population_arrays(population, arrays, chromosomes):
    """Validate retained axes and source locators before scientific values are used."""
    bins = arrays['bins']
    evidence = population['read_evidence']
    if 'hic' in evidence or population['native_storage_mode'] == 'hic-symmetric':
        from .chromatin_hic_table_validation import validate_hic_population_arrays
        validate_hic_population_arrays(population, arrays, chromosomes)
    if bins is None:
        if evidence['axes_extent'] == 'complete':
            raise ChromatinValidationError('unavailable_axes_claimed_complete')
        return
    if len(bins) != population['bin_count']:
        raise ChromatinValidationError('bin_count_mismatch')
    region = population['selected_region']
    chromosome = next((row for row in chromosomes if row['chromosome'] == region['chromosome']), None)
    if chromosome is None or not len(bins):
        raise ChromatinValidationError('unknown_population_chromosome')
    if (np.any(bins['chromosome_index'] != chromosome['chromosome_index'])
            or np.any(bins['start_bp'] < 0) or np.any(bins['end_bp'] <= bins['start_bp'])
            or np.any(bins['end_bp'] > chromosome['length_bp'])
            or np.any(np.diff(bins['bin_id']) != 1)
            or np.any(bins['start_bp'][1:] != bins['end_bp'][:-1])):
        raise ChromatinValidationError('invalid_population_axes')
    if int(bins['start_bp'][0]) != region['start_bp'] or int(bins['end_bp'][-1]) != region['end_bp']:
        raise ChromatinValidationError('population_boundary_not_bin_aligned')
    width = population['fixed_bin_size_bp']
    if width is not None:
        lengths = bins['end_bp'] - bins['start_bp']
        terminal = (bins['end_bp'] == chromosome['length_bp']) & (lengths < width)
        if np.any((lengths != width) & ~terminal) or np.any(bins['start_bp'] % width != 0):
            raise ChromatinValidationError('invalid_fixed_bin_grid')
    low, high = int(bins['bin_id'][0]), int(bins['bin_id'][-1])
    for role in ('contacts', 'cell_states'):
        array = arrays[role]
        if array is None:
            continue
        for start in range(0, len(array), CHUNK_ROWS):
            block = array[start:start + CHUNK_ROWS]
            if np.any(block['bin1_id'] < low) or np.any(block['bin1_id'] > high) or np.any(block['bin2_id'] < low) or np.any(block['bin2_id'] > high):
                raise ChromatinValidationError('contact_bin_reference_mismatch')
            if population['native_storage_mode'] == 'symmetric-upper' and np.any(block['bin1_id'] > block['bin2_id']):
                for row in block[block['bin1_id'] > block['bin2_id']]:
                    if role == 'contacts':
                        source_rows = [int(row['source_row'])]
                    else:
                        contacts = arrays['contacts']
                        source_rows = []
                        if contacts is not None:
                            lo = int(np.searchsorted(contacts['bin1_id'], row['bin1_id'], side='left'))
                            hi = int(np.searchsorted(contacts['bin1_id'], row['bin1_id'], side='right'))
                            local = contacts[lo:hi]
                            a = int(np.searchsorted(local['bin2_id'], row['bin2_id'], side='left'))
                            b = int(np.searchsorted(local['bin2_id'], row['bin2_id'], side='right'))
                            source_rows = local['source_row'][a:b]
                    located = any(
                        problem['code'] == 'malformed_native_index' and problem['stage'] == 'native_parse'
                        and problem['population_key'] == population['population_key'] and problem['locator'] is not None
                        and problem['locator']['kind'] == 'native_row'
                        and problem['locator']['value']['row_index'] in source_rows
                        and problem['locator']['value']['table_path'] in {r['table_path'] for r in evidence['required_native_row_ranges']}
                        for problem in population['failures'])
                    if population['extent'] != 'partial' or not located:
                        raise ChromatinValidationError('lower_triangular_native_pixel')
            if role == 'contacts' and (np.any(block['source_row'] < 0) or np.any(block['source_block'] < -1)):
                raise ChromatinValidationError('invalid_native_locator')
            if role == 'cell_states' and np.any((block['state'] < 1) | (block['state'] > 5)):
                raise ChromatinValidationError('invalid_cell_state')
    weights = arrays['weights']
    if weights is not None and len(weights) != len(bins):
        raise ChromatinValidationError('weights_axis_mismatch')
    dense = arrays['dense_values']
    if dense is not None and dense.shape != (len(bins), len(bins)):
        raise ChromatinValidationError('dense_axis_mismatch')
    if evidence['implicit_zero_semantics'] == 'validated_sparse_absence' and any(evidence[field] != 'complete' for field in ('axes_extent', 'index_extent', 'selected_records_extent')):
        raise ChromatinValidationError('unproven_sparse_absence')


@contextmanager
def open_chromatin_contact_tables(descriptors, *, streams):
    descriptors = [validate_chromatin_record('TableDescriptor', row) for row in descriptors]
    if len({row['table_key'] for row in descriptors}) != len(descriptors):
        raise ChromatinValidationError('duplicate_table_key')
    populations, mappings, positions = {}, [], []
    required = {row['table_key'] for row in descriptors if row['availability'] == 'present'}
    if set(streams) != required:
        raise ChromatinValidationError('supplied_table_streams_mismatch')
    for descriptor in descriptors:
        population = populations.setdefault(descriptor['population_key'], {'population_key': descriptor['population_key']})
        if descriptor['role'] in population:
            raise ChromatinValidationError('duplicate_table_role')
        population[descriptor['role']] = None
    if any(set(population) != {'population_key', *TABLE_ROLES} for population in populations.values()):
        raise ChromatinValidationError('exact_five_table_roles_required')
    try:
        for descriptor in descriptors:
            if descriptor['availability'] != 'present':
                continue
            stream = streams[descriptor['table_key']]
            positions.append((stream, stream.tell()))
            size = _identity(stream, descriptor['file'])
            if descriptor['role'] == 'bins':
                array = _read_bins(stream, descriptor)
            else:
                array = _read_npy(stream, descriptor, size, mappings)
                if descriptor['role'] == 'contacts':
                    _ordered(array, ('bin1_id', 'bin2_id', 'source_block', 'source_row'))
                elif descriptor['role'] == 'cell_states':
                    _ordered(array, ('bin1_id', 'bin2_id'))
            populations[descriptor['population_key']][descriptor['role']] = array
        yield {'version': 'chromatin_contact_arrays_v1', 'populations': MappingProxyType({
            key: MappingProxyType(value) for key, value in populations.items()})}
    finally:
        # No supplied stream is closed, including on validation failure.
        for population in populations.values():
            for role in TABLE_ROLES:
                population[role] = None
        for mapping in reversed(mappings):
            if isinstance(mapping, memoryview):
                mapping.release()
            else:
                mapping.close()
        for stream, position in positions:
            stream.seek(position)


@contextmanager
def read_chromatin_sheet_tables(sheet, *, streams):
    sheet = validate_chromatin_record('ContactSheet', sheet)
    with open_chromatin_contact_tables(sheet['data_tables'], streams=streams) as views:
        from .chromatin_interaction_inputs import validate_chromatin_sheet_arrays
        validate_chromatin_sheet_arrays(sheet, views)
        yield views
