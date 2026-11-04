"""Bounded HIC v9 byte decoding on a caller-supplied seekable stream.

No path is opened here. Indexes describe native bytes, and a block decoder
reports its actual completion separately from the records decoded before error.
"""
from __future__ import annotations

import hashlib
import math
import re
import struct
import zlib


CHUNK_BYTES = 65536


def byte_locator(offset, size, section):
    return {'kind': 'hic_bytes', 'value': {'offset': max(0, offset),
            'size_bytes': max(0, size), 'section': section}}


class HicReadError(ValueError):
    def __init__(self, code, locator=None, field=None):
        super().__init__(code)
        self.code, self.locator, self.field = code, locator, field


class Cursor:
    """An exact, bounded native range; no allocation from an unchecked count."""
    def __init__(self, stream, file_size, start=0, end=None, *, section='header'):
        self.stream, self.file_size = stream, file_size
        self.start = self.pos = start
        self.end = file_size if end is None else end
        self.section = section
        if start < 0 or self.end < start or self.end > file_size:
            self.fail('malformed_native_index', start, max(0, self.end - start))

    def fail(self, code, offset=None, size=0, field=None):
        raise HicReadError(code, byte_locator(self.pos if offset is None else offset,
                                            size, self.section), field)

    def read(self, count):
        if count < 0 or count > self.end - self.pos:
            self.fail('native_output_partial', self.pos, min(max(count, 0), self.end - self.pos))
        self.stream.seek(self.pos)
        data = self.stream.read(count)
        if not isinstance(data, bytes) or len(data) != count:
            self.fail('native_chunk_unavailable', self.pos, count)
        self.pos += count
        return data

    def get(self, fmt):
        values = struct.unpack('<' + fmt, self.read(struct.calcsize('<' + fmt)))
        return values[0] if len(values) == 1 else values

    def nonnegative(self, fmt='i'):
        offset = self.pos
        value = self.get(fmt)
        if value < 0:
            self.fail('malformed_native_index', offset, struct.calcsize('<' + fmt))
        return value

    def positive(self, fmt='i'):
        offset = self.pos
        value = self.nonnegative(fmt)
        if not value:
            self.fail('malformed_native_index', offset, struct.calcsize('<' + fmt))
        return value

    def string(self, *, retain_limit=None):
        # Attribute values can be large. Their exact bytes remain in the source;
        # retaining no decoded value is explicit, not a shortened string.
        chunks, size = [], 0
        while self.pos < self.end:
            data = self.read(min(CHUNK_BYTES, self.end - self.pos))
            stop = data.find(b'\0')
            consumed = len(data) if stop < 0 else stop
            size += consumed
            if retain_limit is None or size <= retain_limit:
                chunks.append(data[:consumed])
            else:
                chunks.clear()
            if stop >= 0:
                self.pos -= len(data) - stop - 1
                if retain_limit is not None and size > retain_limit:
                    return None
                try:
                    return b''.join(chunks).decode('utf-8', 'strict')
                except UnicodeError as exc:
                    raise HicReadError('malformed_native_header',
                                       byte_locator(self.pos - size - 1, size + 1, self.section)) from exc
        self.fail('native_output_partial')

    def skip(self, count):
        if count < 0 or count > self.end - self.pos:
            self.fail('native_output_partial', self.pos, self.end - self.pos)
        self.pos += count

    def range(self, start=None, end=None):
        return hashed_range(self.stream, self.file_size,
                            self.start if start is None else start,
                            (self.pos if end is None else end) - (self.start if start is None else start),
                            self.section)


def hashed_range(stream, file_size, offset, size, section):
    cursor = Cursor(stream, file_size, offset, offset + size, section=section)
    digest = hashlib.sha256()
    while cursor.pos < cursor.end:
        digest.update(cursor.read(min(CHUNK_BYTES, cursor.end - cursor.pos)))
    return {'offset': offset, 'size_bytes': size, 'sha256': digest.hexdigest()}


def read_header(stream, file_size):
    c = Cursor(stream, file_size)
    if c.read(4) != b'HIC\0':
        c.fail('unsupported_native_format', 0, min(4, file_size))
    if c.get('i') != 9:
        c.fail('unsupported_native_version', 4, 4)
    footer = c.nonnegative('q')
    genome = c.string()
    nvi, nvi_size = c.nonnegative('q'), c.nonnegative('q')
    attributes = []
    for ordinal in range(c.nonnegative()):
        for part in ('key', 'value'):
            value = c.string(retain_limit=65536)
            attributes.append({'path': f'/hic/attributes/{ordinal}/{part}', 'dtype': 'utf8',
                               'shape': [], 'value_state': 'retained_only' if value is None else 'decoded',
                               'value': value})
    raw_chromosomes, chromosomes, names = [], [], set()
    for ordinal in range(c.nonnegative()):
        start = c.pos
        name, length = c.string(), c.nonnegative('q')
        if not name or name in names:
            c.fail('malformed_native_header', start, c.pos - start)
        names.add(name)
        aggregate = name in ('All', 'all', 'ALL')
        if aggregate and ordinal != 0:
            c.fail('hic_pseudochromosome_unsupported', start, c.pos - start)
        if not aggregate and length == 0:
            c.fail('malformed_native_header', start, c.pos - start)
        raw_chromosomes.append({'chromosome_index': ordinal, 'chromosome': name,
                                'native_length': length, 'length_unit': 'kb_proxy' if aggregate else 'bp',
                                'kind': 'all_by_all' if aggregate else 'chromosome'})
        if not aggregate:
            chromosomes.append({'chromosome_index': ordinal, 'chromosome': name, 'length_bp': length})
    resolutions = []
    for _ in range(2):
        values = [c.positive() for _ in range(c.nonnegative())]
        if len(set(values)) != len(values):
            c.fail('malformed_native_header')
        resolutions.append(values)
    if resolutions[1]:
        for _ in raw_chromosomes:
            count = c.nonnegative()
            # Fragment coordinates are not selected by the BP adapter. Validate
            # their byte extent without manufacturing a BP interpretation.
            c.skip(count * 4)
    header = {'version': 'hic_native_header_v1', 'bin_id_space': 'chromosome_local',
              'source_version': 9, 'byte_order': 'little', 'header_range': c.range(),
              'footer_position': footer, 'normalization_index_position': nvi,
              'normalization_index_length': nvi_size, 'genome_id': genome,
              'chromosomes': raw_chromosomes, 'bp_resolutions': resolutions[0],
              'frag_resolutions': resolutions[1]}
    return header, chromosomes, attributes


def _vector_descriptor(name, path, chromosome, unit, resolution, length):
    return {'name': name, 'native_path': path, 'chromosome_index': chromosome,
            'resolution_bp': resolution if unit == 'BP' else None, 'dtype': '<f4',
            'length': length, 'extent': 'unavailable',
            'meaning': 'normalization_weight' if chromosome is not None else 'native_expected_not_used'}


def read_indexes(stream, file_size, header):
    """Read native index facts independent of any requested population/vector.

    A coherent prefix remains available after a truncated index. Ambiguous keys
    are removed altogether; no first duplicate is selected as authoritative.
    """
    result = {'matrices': {}, 'matrix_range': None, 'matrix_complete': False,
              'matrix_errors': [], 'vectors': [], 'normalizations': {},
              'normalization_complete': False, 'normalization_errors': [],
              'auxiliary_errors': []}
    c = None
    ambiguous = set()
    try:
        footer = header['footer_position']
        c = Cursor(stream, file_size, footer, section='footer')
        nbytes = c.nonnegative('q')
        footer_end = c.pos + nbytes
        start = c.pos
        c.section = 'matrix_index'
        count = c.nonnegative()
        for _ in range(count):
            begin = c.pos
            key, position, size = c.string(), c.get('q'), c.get('i')
            entry = {'key': key, 'position': position, 'size': size,
                     'entry_locator': byte_locator(begin, c.pos - begin, 'matrix_index')}
            match = re.fullmatch(r'(0|[1-9][0-9]*)_(0|[1-9][0-9]*)', key)
            if (match is None or any(int(v) >= len(header['chromosomes']) for v in match.groups())
                    or position < header['header_range']['size_bytes'] or size < 12
                    or position + size > footer):
                result['matrix_errors'].append(HicReadError('malformed_native_index', entry['entry_locator']))
                continue
            if key in result['matrices'] or key in ambiguous:
                ambiguous.add(key)
                result['matrices'].pop(key, None)
                result['matrix_errors'].append(HicReadError('malformed_native_index', entry['entry_locator']))
            else:
                result['matrices'][key] = entry
        result['matrix_range'] = c.range(start)
        result['matrix_complete'] = not result['matrix_errors']
        if footer_end < c.pos or footer_end > file_size:
            c.fail('malformed_native_index', footer, 8)
        c.section = 'footer'
        c.end = footer_end
        _expected_vectors(c, result['vectors'], normalized=False)
        if c.pos != footer_end:
            c.fail('malformed_native_index', c.pos, footer_end - c.pos)
        nvi = header['normalization_index_position']
        c.end = nvi if c.pos <= nvi <= file_size else file_size
        _expected_vectors(c, result['vectors'], normalized=True)
        # Some writers leave unrelated normalization data before a rewritten
        # index. Only the declared expected-vector records are interpreted.
    except HicReadError as exc:
        target = 'auxiliary_errors' if result['matrix_range'] is not None else 'matrix_errors'
        result[target].append(exc)
        if c is not None and result['matrix_range'] is None and c.pos >= c.start + 8:
            result['matrix_range'] = c.range(c.start + 8)
    try:
        position, size = header['normalization_index_position'], header['normalization_index_length']
        if not position or not size:
            raise HicReadError('hic_normalization_index_unavailable', byte_locator(0, 0, 'normalization_index'))
        c = Cursor(stream, file_size, position, position + size, section='normalization_index')
        count = c.nonnegative()
        ambiguous = set()
        for ordinal in range(count):
            begin = c.pos
            name, chromosome, unit, resolution = c.string(), c.get('i'), c.string(), c.get('i')
            offset, length = c.get('q'), c.get('q')
            locator = byte_locator(begin, c.pos - begin, 'normalization_index')
            if not name or not 0 <= chromosome < len(header['chromosomes']) or unit not in ('BP', 'FRAG') or resolution <= 0 or offset < 0 or length < 8:
                result['normalization_errors'].append(HicReadError('malformed_native_index', locator))
                continue
            key = (name, chromosome, unit, resolution)
            result['vectors'].append(_vector_descriptor(name, f'/hic/normalization/{ordinal}', chromosome, unit, resolution, None))
            if key in result['normalizations'] or key in ambiguous:
                ambiguous.add(key)
                result['normalizations'].pop(key, None)
                result['normalization_errors'].append(HicReadError('malformed_native_index', locator))
            else:
                result['normalizations'][key] = {'offset': offset, 'size_bytes': length, 'sha256': None}
        if c.pos != c.end:
            c.fail('malformed_native_index', c.pos, c.end - c.pos)
        result['normalization_complete'] = not result['normalization_errors']
    except HicReadError as exc:
        result['normalization_errors'].append(exc)
    return result


def _expected_vectors(c, descriptors, *, normalized):
    for _ in range(c.nonnegative()):
        name = c.string() if normalized else 'NONE'
        unit, resolution, count = c.string(), c.positive(), c.nonnegative('q')
        if unit not in ('BP', 'FRAG') or not name:
            c.fail('malformed_native_index')
        c.skip(count * 4)
        c.skip(c.nonnegative() * 8)
        descriptors.append(_vector_descriptor(name + ':' + unit + ':' + str(resolution),
                           f'/hic/expected/{len(descriptors)}', None, unit, resolution, count))


def read_matrix(stream, file_size, header, entry, chromosome, resolution):
    c = Cursor(stream, file_size, entry['position'], entry['position'] + entry['size'], section='zoom_index')
    result = {'zoom': None, 'complete': True, 'errors': [], 'metadata_range': None}
    try:
        ci, cj, zooms = c.get('i'), c.get('i'), c.nonnegative()
        if ci != chromosome or cj != chromosome:
            c.fail('malformed_native_index', c.start, 8)
        seen = set()
        for _ in range(zooms):
            begin = c.pos
            unit, res_index = c.string(), c.get('i')
            c.get('fiff')  # native summary facts remain in the exact source range
            width, block_bins, block_columns, count = c.get('i'), c.get('i'), c.get('i'), c.nonnegative()
            options = header['bp_resolutions'] if unit == 'BP' else header['frag_resolutions'] if unit == 'FRAG' else []
            valid = 0 <= res_index < len(options) and options[res_index] == width and block_bins > 0 and block_columns > 0
            selected = unit == 'BP' and width == resolution
            duplicate_zoom = (unit, width) in seen
            seen.add((unit, width))
            zoom = {'unit': unit, 'resolution': width, 'block_bin_count': block_bins,
                    'block_column_count': block_columns, 'declared_block_count': count,
                    'entries': [], 'range': None}
            if selected and valid and not duplicate_zoom:
                result['zoom'] = zoom
            if not valid or duplicate_zoom:
                result['complete'] = False
                result['errors'].append(HicReadError('malformed_native_index', byte_locator(begin, c.pos - begin, 'zoom_index')))
                if selected and duplicate_zoom:
                    result['zoom'] = None
            ambiguous, seen_blocks, previous = set(), set(), None
            try:
                for _ in range(count):
                    start = c.pos
                    block, offset, length = c.get('i'), c.get('q'), c.get('i')
                    locator = byte_locator(start, c.pos - start, 'zoom_index')
                    if block < 0 or offset < 0 or length <= 0:
                        result['complete'] = False
                        result['errors'].append(HicReadError('malformed_native_index', locator))
                        continue
                    if previous is not None and block <= previous:
                        result['complete'] = False
                        result['errors'].append(HicReadError('malformed_native_index', locator))
                    previous = block
                    if block in seen_blocks:
                        ambiguous.add(block)
                        result['complete'] = False
                        result['errors'].append(HicReadError('malformed_native_index', locator))
                        continue
                    seen_blocks.add(block)
                    zoom['entries'].append({'block_id': block, 'offset': offset, 'size_bytes': length,
                                            'index_locator': locator})
            finally:
                zoom['entries'] = [row for row in zoom['entries'] if row['block_id'] not in ambiguous]
                zoom['range'] = c.range(begin)
        if c.pos != c.end:
            c.fail('malformed_native_index', c.pos, c.end - c.pos)
    except HicReadError as exc:
        result['complete'] = False
        result['errors'].append(exc)
    result['metadata_range'] = c.range()
    return result


class InflatedCursor:
    """Incremental zlib decoding with bounded compressed and decoded buffers."""
    def __init__(self, stream, file_size, entry):
        self.source = Cursor(stream, file_size, entry['offset'], entry['offset'] + entry['size_bytes'], section='zoom_index')
        self.z = zlib.decompressobj()
        self.buffer, self.position, self.decoded_size = bytearray(), 0, 0
        self.compressed_hash, self.decoded_hash = hashlib.sha256(), hashlib.sha256()
        self.pending = b''
        self.done = self.broken = False

    def _fill(self):
        if self.broken:
            raise HicReadError('native_chunk_unavailable')
        if self.done:
            return False
        try:
            while True:
                data = self.pending
                self.pending = b''
                if not data and self.source.pos < self.source.end:
                    # Keep the checksum trailer in a later read so observations
                    # already decoded before a bad trailer remain explicit.
                    remaining = self.source.end - self.source.pos
                    take = min(CHUNK_BYTES, remaining - 4 if remaining > 4 else remaining)
                    data = self.source.read(take)
                    self.compressed_hash.update(data)
                out = self.z.decompress(data, CHUNK_BYTES)
                self.pending = self.z.unconsumed_tail
                if out:
                    self.buffer.extend(out)
                    self.decoded_hash.update(out)
                    self.decoded_size += len(out)
                if self.z.eof:
                    self.done = True
                    if self.z.unused_data or self.pending or self.source.pos != self.source.end:
                        raise HicReadError('malformed_native_index')
                elif not out and not self.pending and self.source.pos == self.source.end:
                    raise HicReadError('native_output_partial')
                if out or self.done:
                    return bool(out)
        except (zlib.error, HicReadError) as exc:
            self.broken = True
            if isinstance(exc, HicReadError):
                raise
            raise HicReadError('native_chunk_unavailable') from exc

    def read(self, count):
        while len(self.buffer) < count:
            if not self._fill():
                raise HicReadError('native_output_partial')
        value = bytes(self.buffer[:count])
        del self.buffer[:count]
        self.position += count
        return value

    def get(self, fmt):
        values = struct.unpack('<' + fmt, self.read(struct.calcsize('<' + fmt)))
        return values[0] if len(values) == 1 else values

    def nonnegative(self, fmt='i'):
        value = self.get(fmt)
        if value < 0:
            raise HicReadError('malformed_native_index')
        return value

    def finish(self):
        exact = not self.buffer
        self.buffer.clear()
        while not self.done:
            if self._fill():
                exact = False
                self.buffer.clear()
        return exact


def decode_block(stream, file_size, entry, consume):
    """Call consume(x,y,value,ordinal) for each actual encoded record.

    Returns a closed read witness and located-error candidates. Callers add
    chromosome/resolution identity to block errors. Dense sentinels are not
    records; failed completeness never establishes sparse zeros.
    """
    witness = {'block_id': entry['block_id'], 'compressed_range': {
        'offset': entry['offset'], 'size_bytes': entry['size_bytes'], 'sha256': None},
        'outcome': 'unavailable', 'decoded_size_bytes': None, 'decoded_sha256': None,
        'zlib_eof': False, 'zlib_checksum_valid': False, 'payload_consumed_exactly': False,
        **{name: None for name in ('matrix_representation', 'value_encoding', 'x_encoding',
            'y_encoding', 'bin_x_offset', 'bin_y_offset', 'n_records_declared',
            'n_records_decoded', 'dense_slot_count', 'dense_width', 'dense_filler_slot_count',
            'retained_population_record_count', 'record_ordinal_kind')}}
    errors, cursor, decoded, retained, fillers = [], None, 0, 0, 0
    parsed = False
    try:
        witness['compressed_range'] = hashed_range(stream, file_size, entry['offset'], entry['size_bytes'], 'zoom_index')
        cursor = InflatedCursor(stream, file_size, entry)
        n = cursor.nonnegative()
        witness['n_records_declared'] = n
        xoff, yoff = cursor.get('i'), cursor.get('i')
        witness.update(bin_x_offset=xoff, bin_y_offset=yoff)
        if xoff < 0 or yoff < 0:
            errors.append(HicReadError('malformed_native_index', field='/bin_offset'))
        vf, xf, yf, representation = cursor.get('BBBB')
        if vf not in (0, 1) or xf not in (0, 1) or yf not in (0, 1) or representation not in (1, 2):
            raise HicReadError('hic_block_encoding_unsupported')
        vfmt, xfmt, yfmt = ('f' if vf else 'h'), ('i' if xf else 'h'), ('i' if yf else 'h')
        witness.update(matrix_representation=representation, value_encoding='float32' if vf else 'int16',
                       x_encoding='int32' if xf else 'int16', y_encoding='int32' if yf else 'int16',
                       record_ordinal_kind='sparse_record' if representation == 1 else 'dense_slot')
        if representation == 1:
            for _ in range(cursor.nonnegative(yfmt)):
                relative_y, columns = cursor.get(yfmt), cursor.nonnegative(xfmt)
                for _ in range(columns):
                    relative_x, value = cursor.get(xfmt), cursor.get(vfmt)
                    retained += bool(consume(xoff + relative_x, yoff + relative_y, value, decoded))
                    decoded += 1
                    if relative_x < 0 or relative_y < 0:
                        errors.append(HicReadError('malformed_native_index', field='/relative_position'))
        else:
            slots, width = cursor.nonnegative(), cursor.get('h')
            witness['dense_slot_count'] = slots
            if width <= 0:
                raise HicReadError('malformed_native_index', field='/dense_width')
            witness['dense_width'] = width
            for ordinal in range(slots):
                value = cursor.get(vfmt)
                if math.isnan(value) if vf else value == -32768:
                    fillers += 1
                else:
                    retained += bool(consume(xoff + ordinal % width, yoff + ordinal // width, value, ordinal))
                    decoded += 1
            witness['dense_filler_slot_count'] = fillers
        parsed = True
        if decoded != n:
            errors.append(HicReadError('malformed_native_index', field='/n_records_declared'))
    except HicReadError as exc:
        errors.append(exc)
    if cursor is not None:
        try:
            exact = cursor.finish()
            witness['payload_consumed_exactly'] = parsed and exact
            if parsed and not exact:
                errors.append(HicReadError('malformed_native_index', field='/payload_length'))
        except HicReadError as exc:
            errors.append(exc)
        witness.update(decoded_size_bytes=cursor.decoded_size,
                       decoded_sha256=cursor.decoded_hash.hexdigest() if not cursor.broken and cursor.done else None,
                       zlib_eof=cursor.z.eof, zlib_checksum_valid=cursor.z.eof,
                       n_records_decoded=decoded, retained_population_record_count=retained)
        if witness['matrix_representation'] == 2:
            witness['dense_filler_slot_count'] = fillers
    witness['outcome'] = ('complete' if not errors else 'incompatible' if
                           any(e.code == 'hic_block_encoding_unsupported' for e in errors) else
                           'partial' if cursor is not None else 'unavailable')
    return witness, errors
