"""Supplied-stream Cooler schema-3 extraction, without acquisition or balancing."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import mmap
import os

import numpy as np

from .chromatin_interaction_contracts import TABLE_ROLES, validate_chromatin_record
from .chromatin_interaction_tables import (
    BINS_HEADER, CHUNK_ROWS, STATES_DTYPE, contacts_dtype, dtype_descriptor,
)


def failure(code, *, spec=None, population=None, locator=None, stage='native_parse', requirement='valid_native_structure', element_key=None):
    return {'code': code, 'stage': stage, 'input_key': None if spec is None else spec['input_key'],
            'population_key': None if population is None else population['population_key'],
            'element_key': element_key, 'pair_key': None,
            'artifact_ref': None if spec is None else spec['file']['artifact_ref'],
            'locator': locator, 'field_path': None, 'partial_artifact_refs': [],
            'requirement': requirement}


class NativeReadError(ValueError):
    def __init__(self, code, path=None):
        super().__init__(code)
        self.code, self.path = code, path


def _path(group, child=''):
    return (group.rstrip('/') + '/' + child).rstrip('/') or '/'


def _draft(population, role, *, availability='present', reason=None, shape=None, dtype=None, extent='complete', path=None):
    return {'table_key': population['population_key'] + ':' + role,
            'population_key': population['population_key'], 'role': role,
            'availability': availability, 'absence_reason': reason,
            'encoding': ('tsv' if role == 'bins' else 'npy') if availability == 'present' else None,
            'shape': shape if availability == 'present' else None,
            'dtype_descriptor': dtype if availability == 'present' else None,
            'row_count': shape[0] if availability == 'present' else None,
            'native_source_locator': {'kind': 'hdf5_path', 'value': path} if path else None,
            'extent': extent if availability == 'present' else 'unavailable'}


def _empty_population(population, normalization, code):
    return {'population_key': population['population_key'], 'selected_region': deepcopy(population),
            'extent': 'unavailable', 'bin_count': None, 'fixed_bin_size_bp': None,
            'native_storage_mode': None, 'data_table_keys': [population['population_key'] + ':' + role for role in TABLE_ROLES],
            'raw_cell_population': {**{key: None for key in ('directed_cells', 'unique_unordered_cells', 'stored_rows', 'explicit_zero_rows', 'implicit_zero_directed_cells', 'native_nonfinite_directed_cells', 'unavailable_directed_cells')}, 'validated_observed_row_count': 0},
            'normalization': {'specification': deepcopy(normalization), 'availability': 'not_requested' if normalization['kind'] == 'raw' else 'missing', 'vector_table_key': None, 'native_weight_dtype': None, 'valid_bin_count': None, 'masked_bin_count': None, 'invalid_bin_count': None},
            'read_evidence': {'axes_extent': 'unavailable', 'index_extent': 'unavailable', 'selected_records_extent': 'unavailable', 'required_native_row_ranges': [], 'expected_block_count': None, 'read_block_count': None, 'failed_block_ids': [], 'implicit_zero_semantics': 'not_established', 'symmetry': 'not_established'},
            'failures': []}


def _text(value):
    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode('utf-8', 'strict')
    if isinstance(value, str):
        return value
    raise NativeReadError('malformed_native_header')


def _integer(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise NativeReadError('malformed_native_header')
    return int(value)


def _safe_container(root, h5py):
    seen = set()
    def visit(group):
        address = h5py.h5o.get_info(group.id).addr
        if address in seen:
            return
        seen.add(address)
        for key in group:
            link = group.get(key, getlink=True)
            path = _path(group.name, key)
            if not isinstance(link, h5py.HardLink):
                # Never follow an unprovided external or indirect native target.
                raise NativeReadError('external_native_dependency_unbound', path)
            obj = group[key]
            if isinstance(obj, h5py.Group):
                visit(obj)
            elif isinstance(obj, h5py.Dataset) and (obj.is_virtual or obj.external):
                raise NativeReadError('external_native_dependency_unbound', path)
    visit(root)


def _dataset(group, path, *, integer=False):
    try:
        value = group[path]
        if value.ndim != 1 or value.dtype.hasobject and path != 'chroms/name':
            raise NativeReadError('malformed_native_header', _path(group.name, path))
        if integer and value.dtype.kind not in 'iu':
            raise NativeReadError('malformed_native_header', value.name)
        return value
    except KeyError as exc:
        raise NativeReadError('malformed_native_header', _path(group.name, path)) from exc


def _native_dtype(dtype):
    if dtype.kind == 'i' and dtype.itemsize <= 8:
        return '<i8'
    if dtype.kind == 'u' and dtype.itemsize <= 8:
        return '<u8'
    if dtype.kind == 'f' and dtype.itemsize in (4, 8):
        return '<f' + str(dtype.itemsize)
    raise NativeReadError('malformed_native_header')


def _attributes(group):
    result = []
    for name in group.attrs:
        value = group.attrs[name]
        array = np.asarray(value)
        decoded = array.ndim <= 1 and array.size <= 4096
        converted = None
        if decoded:
            try:
                values = array.reshape(-1)
                converted = []
                for item in values:
                    if isinstance(item, (str, bytes, np.bytes_)):
                        converted.append(_text(item))
                    elif isinstance(item, (bool, np.bool_)):
                        converted.append(bool(item))
                    elif isinstance(item, (int, np.integer)):
                        converted.append(int(item))
                    elif isinstance(item, (float, np.floating)) and np.isfinite(item):
                        converted.append(float(item))
                    else:
                        decoded = False
                        break
                if array.ndim == 0 and decoded:
                    converted = converted[0]
            except (UnicodeError, ValueError):
                decoded = False
        result.append({'path': _path(group.name) + '@' + name, 'dtype': str(array.dtype), 'shape': list(array.shape), 'value_state': 'decoded' if decoded else 'retained_only', 'value': converted if decoded else None})
    return result


def _header(root, spec):
    try:
        group = root[spec['group_path']]
        if _text(group.attrs['format']) != 'HDF5::Cooler':
            raise NativeReadError('unsupported_native_format', group.name)
        if _integer(group.attrs['format-version']) != 3:
            raise NativeReadError('unsupported_native_version', group.name)
        bin_type, storage = _text(group.attrs['bin-type']), _text(group.attrs['storage-mode'])
        if bin_type not in ('fixed', 'variable') or storage not in ('symmetric-upper', 'square'):
            raise NativeReadError('malformed_native_header', group.name)
        width = _integer(group.attrs['bin-size']) if bin_type == 'fixed' else None
        if width is not None and width <= 0 or spec['resolution_bp'] != width:
            raise NativeReadError('malformed_native_header', group.name)
        names, lengths = _dataset(group, 'chroms/name'), _dataset(group, 'chroms/length', integer=True)
        if len(names) != len(lengths):
            raise NativeReadError('malformed_native_header', _path(group.name, 'chroms'))
        chromosomes = [{'chromosome_index': i, 'chromosome': _text(name), 'length_bp': _integer(length)} for i, (name, length) in enumerate(zip(names[:], lengths[:]))]
        if len({c['chromosome'] for c in chromosomes}) != len(chromosomes) or any(c['length_bp'] <= 0 or not c['chromosome'] for c in chromosomes):
            raise NativeReadError('malformed_native_header', names.name)
        datasets = {path: _dataset(group, path, integer=path != 'pixels/count') for path in ('bins/chrom', 'bins/start', 'bins/end', 'pixels/bin1_id', 'pixels/bin2_id', 'pixels/count', 'indexes/chrom_offset', 'indexes/bin1_offset')}
        nbins, npixels = len(datasets['bins/start']), len(datasets['pixels/count'])
        if any(len(datasets[path]) != nbins for path in ('bins/chrom', 'bins/end')) or any(len(datasets[path]) != npixels for path in ('pixels/bin1_id', 'pixels/bin2_id')):
            raise NativeReadError('malformed_native_header', group.name)
        value_dtype = _native_dtype(datasets['pixels/count'].dtype)
        chrom_offset = datasets['indexes/chrom_offset'][:]
        bin_offset = datasets['indexes/bin1_offset'][:]
        if len(chrom_offset) != len(chromosomes) + 1 or len(bin_offset) != nbins + 1 or chrom_offset[0] != 0 or chrom_offset[-1] != nbins or bin_offset[0] != 0 or bin_offset[-1] != npixels or np.any(chrom_offset[1:] < chrom_offset[:-1]) or np.any(bin_offset[1:] < bin_offset[:-1]) or np.any(chrom_offset > nbins) or np.any(bin_offset > npixels):
            raise NativeReadError('malformed_native_index', _path(group.name, 'indexes'))
        reference = {'assembly_accession': None, 'assembly_label': None, 'contigs': [{'chromosome': c['chromosome'], 'length_bp': c['length_bp']} for c in chromosomes], 'source_ref': spec['source_ref']}
        if 'assembly' in group.attrs:
            reference['assembly_label'] = _text(group.attrs['assembly'])
        elif 'genome-assembly' in group.attrs:
            reference['assembly_label'] = _text(group.attrs['genome-assembly'])
        metadata = {'source_file': deepcopy(spec['file']), 'source_ref': spec['source_ref'], 'format': 'cooler_hdf5_v3', 'format_version': 3, 'group_path': spec['group_path'], 'coordinate_system': 'zero_based_half_open', 'bin_type': bin_type, 'bin_size_bp': width, 'storage_mode': storage, 'value_field': 'count', 'value_dtype': value_dtype, 'native_value_dtype': datasets['pixels/count'].dtype.str, 'value_kind': spec['value_kind'], 'value_unit': spec['value_unit'], 'attributes': _attributes(group), 'vectors': [], 'reference_assertion': reference}
        for name in group['bins']:
            if name not in ('chrom', 'start', 'end'):
                vector = group['bins'][name]
                if hasattr(vector, 'dtype') and vector.ndim == 1:
                    metadata['vectors'].append({'name': name, 'native_path': vector.name, 'chromosome_index': None, 'resolution_bp': width, 'dtype': vector.dtype.str, 'length': len(vector), 'extent': 'complete' if len(vector) == nbins else 'incompatible', 'meaning': 'normalization_weight'})
        return group, datasets, chromosomes, metadata, chrom_offset, bin_offset
    except (KeyError, UnicodeError, AttributeError, OverflowError) as exc:
        raise NativeReadError('malformed_native_header', spec['group_path']) from exc


def _npy_start(stream, dtype, rows):
    stream.seek(0)
    stream.truncate(0)
    np.lib.format.write_array_header_2_0(stream, {'descr': np.lib.format.dtype_to_descr(dtype), 'fortran_order': False, 'shape': (rows,)})
    return stream.tell()


def _finalize_sort(stream, dtype, count, offset, fields):
    stream.flush()
    if count < 2:
        return
    try:
        fd = stream.fileno()
    except (AttributeError, io.UnsupportedOperation):
        if not isinstance(stream, io.BytesIO) or count * dtype.itemsize > 16 * 1024 * 1024:
            raise NativeReadError('resource_limit')
        view = stream.getbuffer()
        array = np.ndarray((count,), dtype=dtype, buffer=view, offset=offset)
        array.sort(order=fields, kind='quicksort')
        del array
        view.release()
    else:
        with mmap.mmap(fd, 0, access=mmap.ACCESS_WRITE) as mapping:
            array = np.ndarray((count,), dtype=dtype, buffer=mapping, offset=offset)
            array.sort(order=fields, kind='quicksort')
            del array


def _population(group, datasets, chromosomes, metadata, chrom_offset, bin_offset, spec, normalization, selected, streams):
    result = _empty_population(selected, normalization, 'population_unavailable')
    failures = result['failures']
    def issue(code, path, row=None, requirement='valid_native_structure'):
        locator = {'kind': 'hdf5_path', 'value': path} if row is None else {'kind': 'native_row', 'value': {'table_path': path, 'row_index': int(row)}}
        failures.append(failure(code, spec=spec, population=selected, locator=locator, requirement=requirement))
    chromosome = next((c for c in chromosomes if c['chromosome'] == selected['chromosome']), None)
    if chromosome is None or selected['end_bp'] > chromosome['length_bp']:
        raise NativeReadError('population_unavailable', _path(group.name, 'chroms'))
    ci = chromosome['chromosome_index']
    first, last = int(chrom_offset[ci]), int(chrom_offset[ci + 1])
    starts, ends, chroms = (datasets[path][first:last] for path in ('bins/start', 'bins/end', 'bins/chrom'))
    if (not len(starts) or np.any(chroms != ci) or np.any(starts < 0) or np.any(ends <= starts)
            or np.any(starts[1:] != ends[:-1]) or starts[0] != 0 or ends[-1] != chromosome['length_bp']):
        raise NativeReadError('invalid_coordinate', _path(group.name, 'bins'))
    width = metadata['bin_size_bp']
    if width is not None and (np.any(starts % width != 0) or np.any((ends - starts != width) & ~((ends == chromosome['length_bp']) & (ends - starts < width)))):
        raise NativeReadError('invalid_coordinate', _path(group.name, 'bins'))
    left, right = int(np.searchsorted(starts, selected['start_bp'])), int(np.searchsorted(ends, selected['end_bp'])) + 1
    if left >= len(starts) or right > len(ends) or int(starts[left]) != selected['start_bp'] or int(ends[right - 1]) != selected['end_bp']:
        raise NativeReadError('population_boundary_not_bin_aligned', _path(group.name, 'bins'))
    low, high = first + left, first + right
    starts, ends = starts[left:right], ends[left:right]
    n = high - low
    result.update(bin_count=n, fixed_bin_size_bp=width, native_storage_mode=metadata['storage_mode'])
    evidence = result['read_evidence']
    evidence['axes_extent'] = 'complete'
    bins_stream = streams[(selected['population_key'], 'bins')]
    bins_stream.seek(0); bins_stream.truncate(0); bins_stream.write(BINS_HEADER)
    for ordinal in range(n):
        bins_stream.write(f'{low + ordinal}\t{ci}\t{int(starts[ordinal])}\t{int(ends[ordinal])}\n'.encode())
    drafts = [_draft(selected, 'bins', shape=[n, 4], dtype={'kind': 'scalar', 'dtype': 'utf8_tsv_int64'}, path=_path(group.name, 'bins'))]
    row_start, row_end = int(bin_offset[low]), int(bin_offset[high])
    evidence['required_native_row_ranges'] = [{'table_path': _path(group.name, 'pixels'), 'start_row': row_start, 'end_row': row_end}]
    dtype = contacts_dtype(metadata['value_dtype'])
    count = zero = nonfinite_directed = represented = invalid = 0
    state_count = 0
    previous = None
    complete = True
    blocks = []  # One range per bounded read, never one Python object per pixel.
    for begin in range(row_start, row_end, CHUNK_ROWS):
        stop = min(begin + CHUNK_ROWS, row_end)
        try:
            a, b, values = (datasets[path][begin:stop] for path in ('pixels/bin1_id', 'pixels/bin2_id', 'pixels/count'))
        except (OSError, RuntimeError):
            issue('native_chunk_unavailable', _path(group.name, 'pixels'), begin)
            complete = False
            continue
        blocks.append((begin, stop))
        for offset in range(len(a)):
            row, x, y = begin + offset, int(a[offset]), int(b[offset])
            if x < low or x >= high or row < bin_offset[x] or row >= bin_offset[x + 1] or y < 0 or y >= len(bin_offset) - 1:
                issue('malformed_native_index', _path(group.name, 'pixels'), row)
                complete = False
            if previous is not None and (x, y) <= previous:
                issue('duplicate_native_pixel' if (x, y) == previous else 'malformed_native_index', _path(group.name, 'pixels'), row)
                complete = False
            previous = (x, y)
            if not (low <= x < high and low <= y < high):
                continue
            count += 1
            directed = 2 if metadata['storage_mode'] == 'symmetric-upper' and x != y else 1
            represented += directed
            if metadata['storage_mode'] == 'symmetric-upper' and x > y:
                issue('malformed_native_index', _path(group.name, 'pixels'), row); complete = False
            v = values[offset]
            if not np.isfinite(v):
                state_count += 1; nonfinite_directed += directed
                issue('native_value_nonfinite', datasets['pixels/count'].name, row, 'finite_nonnegative_contact_values')
            elif v < 0 and spec['value_kind'] == 'contact_count':
                invalid += 1
                issue('native_value_negative', datasets['pixels/count'].name, row, 'finite_nonnegative_contact_values')
            else:
                zero += int(v == 0)
    contacts_stream, states_stream = (streams[(selected['population_key'], role)] for role in ('contacts', 'cell_states'))
    contact_offset = _npy_start(contacts_stream, dtype, count)
    state_offset = _npy_start(states_stream, STATES_DTYPE, state_count)
    written = written_states = 0
    for begin, stop in blocks:
        a, b, values = (datasets[path][begin:stop] for path in ('pixels/bin1_id', 'pixels/bin2_id', 'pixels/count'))
        keep = (a >= low) & (a < high) & (b >= low) & (b < high)
        indices = np.flatnonzero(keep)
        records = np.empty(len(indices), dtype=dtype)
        records['bin1_id'], records['bin2_id'], records['value'] = a[keep], b[keep], values[keep]
        records['source_block'], records['source_row'] = -1, indices + begin
        contacts_stream.write(records.tobytes())
        written += len(records)
        exceptional = ~np.isfinite(records['value'])
        if np.any(exceptional):
            states = np.empty(int(np.count_nonzero(exceptional)), dtype=STATES_DTYPE)
            states['bin1_id'], states['bin2_id'] = records['bin1_id'][exceptional], records['bin2_id'][exceptional]
            vals = records['value'][exceptional]
            states['state'] = np.where(np.isnan(vals), 2, np.where(vals > 0, 3, 4))
            states_stream.write(states.tobytes()); written_states += len(states)
    if written != count or written_states != state_count:
        raise NativeReadError('native_output_partial', _path(group.name, 'pixels'))
    _finalize_sort(contacts_stream, dtype, count, contact_offset, ['bin1_id', 'bin2_id', 'source_block', 'source_row'])
    _finalize_sort(states_stream, STATES_DTYPE, state_count, state_offset, ['bin1_id', 'bin2_id'])
    extent = 'complete' if complete else 'partial'
    drafts.extend([_draft(selected, 'contacts', shape=[count], dtype=dtype_descriptor(dtype), extent=extent, path=_path(group.name, 'pixels')),
                   _draft(selected, 'cell_states', shape=[state_count], dtype=dtype_descriptor(STATES_DTYPE), extent=extent, path=_path(group.name, 'pixels'))])
    evidence.update(index_extent=extent, selected_records_extent=extent,
                    implicit_zero_semantics='validated_sparse_absence' if complete else 'not_established',
                    symmetry='native_symmetric_upper' if metadata['storage_mode'] == 'symmetric-upper' else 'not_established')
    if metadata['storage_mode'] == 'square':
        # Retain actual square records. Exact reciprocal checking is performed on
        # the saved arrays by the sheet validator before symmetric calculations.
        issue('incompatible_matrix_symmetry', _path(group.name, 'pixels'))
    result['extent'] = extent
    result['raw_cell_population'] = {'directed_cells': n * n, 'unique_unordered_cells': n * (n + 1) // 2 if metadata['storage_mode'] == 'symmetric-upper' else None,
        'stored_rows': count, 'explicit_zero_rows': zero,
        'implicit_zero_directed_cells': n * n - represented if complete else None,
        'native_nonfinite_directed_cells': nonfinite_directed,
        'unavailable_directed_cells': 0 if complete else None,
        'validated_observed_row_count': count - state_count - invalid}
    if width is None:
        issue('incompatible_variable_bins', _path(group.name, 'bins'), requirement='fixed_bin_grid')
    if normalization['kind'] == 'raw':
        drafts.append(_draft(selected, 'weights', availability='not_requested'))
    else:
        name = normalization['weight_column']
        if '/' in name or name in ('.', '..') or name not in group['bins']:
            issue('normalization_missing', _path(group.name, 'bins/' + name), requirement='selected_weight_vector')
            drafts.append(_draft(selected, 'weights', availability='unavailable', reason='normalization_missing', path=_path(group.name, 'bins/' + name)))
        else:
            vector = group['bins'][name]
            if vector.ndim != 1 or len(vector) != len(bin_offset) - 1 or vector.dtype.kind != 'f' or vector.dtype.itemsize not in (4, 8):
                issue('normalization_weight_invalid', vector.name, requirement='finite_positive_weights')
                drafts.append(_draft(selected, 'weights', availability='unavailable', reason='normalization_weight_invalid', path=vector.name))
            else:
                weights = np.asarray(vector[low:high], dtype='<f8')
                target = streams[(selected['population_key'], 'weights')]
                target.seek(0); target.truncate(0)
                np.lib.format.write_array(target, weights, allow_pickle=False)
                valid = int(np.count_nonzero(np.isfinite(weights) & (weights > 0)))
                masked = int(np.count_nonzero(np.isnan(weights)))
                bad = n - valid - masked
                result['normalization'].update(availability='partial' if bad else 'available', vector_table_key=selected['population_key'] + ':weights', native_weight_dtype=vector.dtype.str, valid_bin_count=valid, masked_bin_count=masked, invalid_bin_count=bad)
                for ordinal in np.flatnonzero(~np.isfinite(weights) | (weights <= 0)):
                    issue('normalization_masked_bin' if np.isnan(weights[ordinal]) else 'normalization_weight_invalid', vector.name, low + int(ordinal), 'finite_positive_weights')
                drafts.append(_draft(selected, 'weights', shape=[n], dtype={'kind': 'scalar', 'dtype': '<f8'}, path=vector.name))
    drafts.append(_draft(selected, 'dense_values', availability='not_native_representation'))
    drafts.sort(key=lambda row: TABLE_ROLES.index(row['role']))
    return result, drafts


def read_cooler_contacts(stream, *, spec, normalization, populations, table_streams):
    spec = validate_chromatin_record('ContactSpec', spec)
    normalization = validate_chromatin_record('NormalizationSpec', normalization)
    populations = [validate_chromatin_record('PopulationSpec', row) for row in populations]
    if len({p['population_key'] for p in populations}) != len(populations):
        raise ValueError('duplicate_population_key')
    required = {(p['population_key'], role) for p in populations for role in TABLE_ROLES}
    if set(table_streams) != required or any(not target.seekable() or not target.writable() for target in table_streams.values()):
        raise ValueError('exact_seekable_output_streams_required')
    result = {'format': spec['format'], 'format_version': None, 'native_metadata': None, 'chromosomes': [], 'populations': [], 'table_drafts': [], 'failures': []}
    def unavailable(selected, code, path=None):
        population = _empty_population(selected, normalization, code)
        population['failures'] = [failure(code, spec=spec, population=selected, locator={'kind': 'hdf5_path', 'value': path} if path else None)]
        result['populations'].append(population)
        for role in TABLE_ROLES:
            availability = 'not_native_representation' if role == 'dense_values' else ('not_requested' if role == 'weights' and normalization['kind'] == 'raw' else 'unavailable')
            result['table_drafts'].append(_draft(selected, role, availability=availability, reason=code if availability == 'unavailable' else None))
        result['failures'].extend(population['failures'])
    try:
        if spec['format'] != 'cooler_hdf5_v3':
            raise NativeReadError('unsupported_native_format')
        if not stream.readable() or not stream.seekable():
            raise NativeReadError('input_unavailable')
        stream.seek(0)
        digest, size = hashlib.sha256(), 0
        while block := stream.read(1024 * 1024):
            digest.update(block); size += len(block)
        if digest.hexdigest() != spec['file']['sha256'] or size != spec['file']['size_bytes']:
            raise NativeReadError('input_digest_mismatch')
        stream.seek(0)
        try:
            import h5py
        except ImportError as exc:
            raise NativeReadError('native_dependency_unavailable') from exc
        with h5py.File(stream, 'r') as root:
            _safe_container(root, h5py)
            group, datasets, chromosomes, metadata, chrom_offset, bin_offset = _header(root, spec)
            result.update(format_version=3, native_metadata=metadata, chromosomes=chromosomes)
            for selected in populations:
                try:
                    population, drafts = _population(group, datasets, chromosomes, metadata, chrom_offset, bin_offset, spec, normalization, selected, table_streams)
                    result['populations'].append(population)
                    result['table_drafts'].extend(drafts)
                    result['failures'].extend(population['failures'])
                except NativeReadError as exc:
                    unavailable(selected, exc.code, exc.path)
                except (OSError, RuntimeError) as exc:
                    unavailable(selected, 'native_chunk_unavailable', group.name)
    except NativeReadError as exc:
        for selected in populations:
            unavailable(selected, exc.code, exc.path)
    except (OSError, RuntimeError, ValueError) as exc:
        for selected in populations[len(result['populations']):]:
            unavailable(selected, 'malformed_native_header', spec['group_path'])
    return validate_chromatin_record('ContactExtraction', result)


def unavailable_chromatin_extraction(*, spec, normalization, populations, code):
    """Actual no-data outcome for an input that could not be supplied to a reader."""
    spec = validate_chromatin_record('ContactSpec', spec)
    normalization = validate_chromatin_record('NormalizationSpec', normalization)
    result = {'format': spec['format'], 'format_version': None, 'native_metadata': None,
              'chromosomes': [], 'populations': [], 'table_drafts': [], 'failures': []}
    for selected in populations:
        validate_chromatin_record('PopulationSpec', selected)
        population = _empty_population(selected, normalization, code)
        issue = failure(code, spec=spec, population=selected, stage='input', requirement='supplied_contact_file')
        population['failures'].append(issue)
        result['populations'].append(population)
        result['failures'].append(issue)
        for role in TABLE_ROLES:
            availability = 'not_native_representation' if role == 'dense_values' else ('not_requested' if role == 'weights' and normalization['kind'] == 'raw' else 'unavailable')
            result['table_drafts'].append(_draft(selected, role, availability=availability, reason=code if availability == 'unavailable' else None))
    return validate_chromatin_record('ContactExtraction', result)
