"""HIC byte/coordinate witnesses for the existing chromatin numerical sheet.

These are closed data shapes and deterministic consistency checks, not scoring
rules. Native decoding and acquisition live elsewhere. Older Cooler records do
not gain fields or different meanings from this format extension.
"""
from __future__ import annotations

from copy import deepcopy


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _ref(name):
    return {"$ref": "#/$defs/" + name}


def _nullable(value):
    return {"anyOf": [value, {"type": "null"}]}


def _array(items):
    return {"type": "array", "items": items, "minItems": 0}


_UINT = {"type": "integer", "minimum": 0}
_POSITIVE = {"type": "integer", "minimum": 1}
_TEXT = {"type": "string", "minLength": 1}
_HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_EXTENT = {"enum": ["complete", "partial", "unavailable", "incompatible"]}
_BOOL = {"type": "boolean"}


def hic_record_definitions():
    """Return detached HIC-only definitions; all scientific arithmetic is separate."""
    definitions = {
        "HicByteRange": _object({
            "offset": _UINT, "size_bytes": _UINT,
            "sha256": _nullable(_HASH),
        }),
        "HicRuntimeFile": _object({
            "path": {"type": "string", "pattern": r"^/[^\\\u0000\r\n]+$"},
            "sha256": _HASH, "size_bytes": _UINT,
        }),
        "HicNativeRuntime": _object({
            "zlib_compile_version": _TEXT, "zlib_runtime_version": _TEXT,
            "files": _array(_ref("HicRuntimeFile")),
        }),
        "HicHeaderChromosome": _object({
            "chromosome_index": _UINT, "chromosome": _TEXT,
            "native_length": _UINT,
            "length_unit": {"enum": ["bp", "kb_proxy"]},
            "kind": {"enum": ["chromosome", "all_by_all"]},
        }),
        "HicHeader": _object({
            "version": {"const": "hic_native_header_v1"},
            "bin_id_space": {"const": "chromosome_local"},
            "source_version": {"type": "integer", "const": 9}, "byte_order": {"const": "little"},
            "header_range": _ref("HicByteRange"),
            "footer_position": _UINT, "normalization_index_position": _UINT,
            "normalization_index_length": _UINT,
            "genome_id": {"type": "string"},
            "chromosomes": _array(_ref("HicHeaderChromosome")),
            "bp_resolutions": _array(_POSITIVE),
            "frag_resolutions": _array(_POSITIVE),
        }),
        "HicBlockRead": _object({
            "block_id": _UINT, "compressed_range": _ref("HicByteRange"),
            "outcome": _EXTENT,
            "decoded_size_bytes": _nullable(_UINT),
            "decoded_sha256": _nullable(_HASH),
            "zlib_eof": _BOOL, "zlib_checksum_valid": _BOOL,
            "payload_consumed_exactly": _BOOL,
            "matrix_representation": _nullable({"type": "integer", "enum": [1, 2]}),
            "value_encoding": _nullable({"enum": ["int16", "float32"]}),
            "x_encoding": _nullable({"enum": ["int16", "int32"]}),
            "y_encoding": _nullable({"enum": ["int16", "int32"]}),
            "bin_x_offset": _nullable({"type": "integer"}),
            "bin_y_offset": _nullable({"type": "integer"}),
            "n_records_declared": _nullable(_UINT),
            "n_records_decoded": _nullable(_UINT),
            "dense_slot_count": _nullable(_UINT),
            "dense_width": _nullable(_POSITIVE),
            "dense_filler_slot_count": _nullable(_UINT),
            "retained_population_record_count": _nullable(_UINT),
            "record_ordinal_kind": _nullable({"enum": ["sparse_record", "dense_slot"]}),
        }),
        "HicVectorRead": _object({
            "normalization_type": _TEXT, "chromosome_index": _UINT,
            "unit": {"const": "BP"}, "resolution_bp": _POSITIVE,
            "index_extent": _EXTENT,
            "native_range": _nullable(_ref("HicByteRange")),
            "n_values_declared": _nullable(_UINT),
            "n_values_read": _nullable(_UINT),
            "native_dtype": _nullable({"const": "<f4"}),
            "selected_bin_start": _UINT, "selected_bin_end_exclusive": _UINT,
            "physical_chromosome_bin_count": _POSITIVE,
            "extra_terminal_values": _nullable(_UINT), "outcome": _EXTENT,
        }),
        "HicPopulationRead": _object({
            "version": {"const": "hic_population_read_v1"},
            "source_sha256": _HASH,
            "scan_scope": {"const": "all_indexed_blocks_selected_cis_zoom"},
            "matrix_key": _TEXT,
            "matrix_index_range": _ref("HicByteRange"),
            "matrix_metadata_range": _ref("HicByteRange"),
            "zoom_index_range": _ref("HicByteRange"),
            "chromosome1_index": _UINT, "chromosome2_index": _UINT,
            "unit": {"const": "BP"}, "resolution_bp": _POSITIVE,
            "block_bin_count": _POSITIVE, "block_column_count": _POSITIVE,
            "declared_block_count": _UINT,
            "blocks": _array(_ref("HicBlockRead")),
            "selected_normalization": _nullable(_ref("HicVectorRead")),
        }),
    }
    return deepcopy(definitions)


def extend_hic_definitions(definitions):
    """Extend the production-owned record grammar once, preserving old fields."""
    definitions.update(hic_record_definitions())
    definitions["NativeMetadata"]["properties"]["hic"] = _ref("HicHeader")
    definitions["PopulationReadEvidence"]["properties"]["hic"] = _nullable(_ref("HicPopulationRead"))
    definitions["SoftwareBinding"]["properties"]["native_runtime"] = _ref("HicNativeRuntime")
    definitions["Locator"]["oneOf"].extend([
        _object({"kind": {"const": "hic_bytes"}, "value": _object({
            "offset": _UINT, "size_bytes": _UINT,
            "section": {"enum": ["header", "footer", "matrix_index", "zoom_index",
                                   "normalization_index", "normalization_vector"]},
        })}),
        _object({"kind": {"const": "hic_vector"}, "value": _object({
            "normalization_type": _TEXT, "chromosome_index": _UINT,
            "unit": {"const": "BP"}, "resolution_bp": _POSITIVE,
            "bin_index": _nullable(_UINT),
        })}),
    ])
    codes = [
        "hic_matrix_absent", "hic_resolution_absent",
        "hic_pseudochromosome_unsupported", "hic_block_encoding_unsupported",
        "hic_normalization_index_unavailable",
    ]
    definitions["Failure"]["properties"]["code"]["enum"].extend(codes)
    for name in ('TableDraft', 'TableDescriptor'):
        definitions[name]['properties']['absence_reason']['anyOf'][0]['enum'].extend(codes)
        definitions[name]['allOf'][1]['then']['properties']['absence_reason']['enum'].extend(codes)


def _require(condition, code):
    if not condition:
        from .chromatin_interaction_contracts import ChromatinValidationError
        raise ChromatinValidationError(code)


def _complete_range(value):
    return value is not None and value['sha256'] is not None and value['size_bytes'] > 0


def _bounded_range(value, size, *, complete=False):
    # A null hash is a declared range, not evidence that these bytes were read.
    if complete or value['sha256'] is not None:
        _require(value['offset'] + value['size_bytes'] <= size, 'hic_read_range_outside_source')
    if complete:
        _require(_complete_range(value), 'hic_complete_range_required')


def _header(value):
    rows = value['chromosomes']
    _require([r['chromosome_index'] for r in rows] == list(range(len(rows))),
             'hic_original_chromosome_indices_required')
    _require(len({r['chromosome'] for r in rows}) == len(rows), 'hic_duplicate_chromosome')
    for row in rows:
        aggregate = row['chromosome_index'] == 0 and row['chromosome'] in ('All', 'all', 'ALL')
        _require((row['kind'], row['length_unit']) ==
                 (('all_by_all', 'kb_proxy') if aggregate else ('chromosome', 'bp')),
                 'hic_chromosome_unit_mismatch')
        if not aggregate:
            _require(row['native_length'] > 0, 'hic_invalid_chromosome_length')
    for name in ('bp_resolutions', 'frag_resolutions'):
        _require(len(set(value[name])) == len(value[name]), 'hic_duplicate_resolution')
    _require(value['header_range']['offset'] == 0 and _complete_range(value['header_range']),
             'hic_complete_header_required')


def _block(value):
    complete = value['outcome'] == 'complete'
    if value['zlib_checksum_valid']:
        _require(value['zlib_eof'], 'hic_checksum_without_eof')
    if value['decoded_sha256'] is not None:
        _require(value['decoded_size_bytes'] is not None, 'hic_payload_size_required')
    if complete:
        _require(_complete_range(value['compressed_range'])
                 and value['decoded_sha256'] is not None
                 and all(value[name] for name in ('zlib_eof', 'zlib_checksum_valid', 'payload_consumed_exactly')),
                 'hic_complete_block_bytes_required')
        _require(all(value[name] is not None for name in (
            'decoded_size_bytes', 'matrix_representation', 'value_encoding', 'x_encoding', 'y_encoding',
            'bin_x_offset', 'bin_y_offset', 'n_records_declared', 'n_records_decoded',
            'retained_population_record_count', 'record_ordinal_kind')),
            'hic_complete_block_fields_required')
        _require(value['n_records_declared'] == value['n_records_decoded'],
                 'hic_block_record_cardinality_mismatch')
    if value['retained_population_record_count'] is not None and value['n_records_decoded'] is not None:
        _require(value['retained_population_record_count'] <= value['n_records_decoded'],
                 'hic_retained_record_count_mismatch')
    representation = value['matrix_representation']
    if representation == 1:
        _require(all(value[name] is None for name in ('dense_slot_count', 'dense_width', 'dense_filler_slot_count')),
                 'hic_sparse_block_dense_fields')
        _require(value['record_ordinal_kind'] in (None, 'sparse_record'), 'hic_record_ordinal_kind_mismatch')
    elif representation == 2:
        _require(value['record_ordinal_kind'] in (None, 'dense_slot'), 'hic_record_ordinal_kind_mismatch')
        if complete:
            _require(all(value[name] is not None for name in ('dense_slot_count', 'dense_width', 'dense_filler_slot_count')),
                     'hic_dense_block_fields_required')
            _require(value['dense_slot_count'] == value['n_records_decoded'] + value['dense_filler_slot_count'],
                     'hic_dense_filler_cardinality_mismatch')
            width = 2 if value['value_encoding'] == 'int16' else 4
            # v9 block header (16 bytes), nPts/int32, width/int16, exact slots.
            _require(value['decoded_size_bytes'] == 22 + width * value['dense_slot_count'],
                     'hic_dense_payload_size_mismatch')


def _vector(value):
    _require(value['selected_bin_start'] < value['selected_bin_end_exclusive']
             <= value['physical_chromosome_bin_count'], 'hic_vector_selection_mismatch')
    declared, read = value['n_values_declared'], value['n_values_read']
    if declared is not None and read is not None:
        _require(read <= declared, 'hic_vector_read_count_mismatch')
    if value['extra_terminal_values'] is not None:
        _require(declared is not None and value['extra_terminal_values'] ==
                 max(0, declared - value['physical_chromosome_bin_count']), 'hic_vector_padding_mismatch')
    if value['outcome'] == 'complete':
        _require(value['index_extent'] == 'complete' and _complete_range(value['native_range'])
                 and declared is not None and declared == read
                 and declared >= value['physical_chromosome_bin_count']
                 and value['native_dtype'] == '<f4'
                 and value['extra_terminal_values'] == declared - value['physical_chromosome_bin_count'],
                 'hic_complete_vector_required')
        _require(value['native_range']['size_bytes'] == 8 + 4 * declared,
                 'hic_vector_byte_cardinality_mismatch')


def _witness(value):
    chromosome = value['chromosome1_index']
    _require(chromosome == value['chromosome2_index'] and value['matrix_key'] == f'{chromosome}_{chromosome}',
             'hic_cis_matrix_identity_mismatch')
    ids = [block['block_id'] for block in value['blocks']]
    _require(len(set(ids)) == len(ids), 'hic_ambiguous_block_identity')
    _require(len(ids) <= value['declared_block_count'], 'hic_declared_block_count_mismatch')
    for block in value['blocks']:
        _block(block)
    if value['selected_normalization'] is not None:
        _vector(value['selected_normalization'])


def _metadata(value):
    if value['format'] != 'hic_binary_v9':
        _require('hic' not in value, 'hic_header_on_other_format')
        return
    _require(value.get('hic') is not None, 'hic_native_header_required')
    header = value['hic']
    _header(header)
    _bounded_range(header['header_range'], value['source_file']['size_bytes'], complete=True)
    _require(type(value['format_version']) is int and value['format_version'] == 9 and value['group_path'] is None
             and value['bin_type'] == 'fixed' and value['bin_size_bp'] is not None
             and value['storage_mode'] == 'hic-symmetric' and value['value_dtype'] == '<f4'
             and value['native_value_dtype'] == 'hic_v9_block_int16_or_float32',
             'hic_native_metadata_mismatch')
    expected_paths = [f'/hic/attributes/{index}/{part}'
                      for index in range(len(value['attributes']) // 2) for part in ('key', 'value')]
    _require([row['path'] for row in value['attributes']] == expected_paths,
             'hic_attribute_occurrence_mismatch')
    _require(all(row['dtype'] == 'utf8' and row['shape'] == [] for row in value['attributes']),
             'hic_attribute_scalar_required')


def _located_block_failure(population, block_id):
    return any(row['stage'] == 'native_parse' and row['population_key'] == population['population_key']
               and row['locator'] is not None and row['locator']['kind'] == 'hic_block'
               and row['locator']['value']['block_id'] == block_id for row in population['failures'])


def validate_hic_population_records(population, metadata, chromosomes):
    """Validate saved relationships without opening or decoding any native file."""
    evidence, counts = population['read_evidence'], population['raw_cell_population']
    witness = evidence.get('hic')
    _require(not evidence['required_native_row_ranges'], 'hic_has_no_native_pixel_row_ranges')
    complete = (population['extent'] == 'complete'
                or evidence['implicit_zero_semantics'] == 'validated_sparse_absence')
    complete_reads = complete or evidence['selected_records_extent'] == 'complete'
    if witness is None:
        _require(not complete_reads and evidence['implicit_zero_semantics'] == 'not_established',
                 'hic_complete_population_witness_required')
        _require(counts['implicit_zero_directed_cells'] is None, 'hic_unproven_sparse_count')
        return
    _witness(witness)
    _require(metadata is not None, 'hic_witness_header_required')
    chromosome = next((row for row in chromosomes
                       if row['chromosome'] == population['selected_region']['chromosome']), None)
    _require(chromosome is not None and witness['chromosome1_index'] == chromosome['chromosome_index'],
             'hic_population_chromosome_mismatch')
    _require(witness['source_sha256'] == metadata['source_file']['sha256'], 'hic_witness_source_mismatch')
    _require(witness['resolution_bp'] == population['fixed_bin_size_bp'] == metadata['bin_size_bp'],
             'hic_resolution_mismatch')
    _require(witness['resolution_bp'] in metadata['hic']['bp_resolutions'], 'hic_resolution_not_in_header')
    _require(population['native_storage_mode'] == 'hic-symmetric', 'hic_storage_mode_mismatch')
    size = metadata['source_file']['size_bytes']
    for name in ('matrix_index_range', 'matrix_metadata_range', 'zoom_index_range'):
        _bounded_range(witness[name], size, complete=complete_reads)
    blocks = witness['blocks']
    if evidence['index_extent'] == 'complete':
        ids = [row['block_id'] for row in blocks]
        _require(len(ids) == witness['declared_block_count'] and ids == sorted(ids),
                 'hic_complete_index_order_or_count_mismatch')
        for name in ('matrix_index_range', 'matrix_metadata_range', 'zoom_index_range'):
            _bounded_range(witness[name], size, complete=True)
    successful = sum(row['outcome'] == 'complete' for row in blocks)
    failed = {row['block_id'] for row in blocks if row['outcome'] != 'complete'}
    _require(evidence['expected_block_count'] == witness['declared_block_count']
             and evidence['read_block_count'] == successful
             and failed <= set(evidence['failed_block_ids']), 'hic_aggregate_block_counts_mismatch')
    for block in blocks:
        _bounded_range(block['compressed_range'], size, complete=block['outcome'] == 'complete')
        if block['compressed_range']['offset'] + block['compressed_range']['size_bytes'] > size:
            _require(block['outcome'] == 'unavailable' and block['compressed_range']['sha256'] is None
                     and _located_block_failure(population, block['block_id']),
                     'hic_unavailable_range_failure_required')
    if complete_reads:
        _require(all(evidence[name] == 'complete' for name in ('index_extent', 'selected_records_extent'))
                 and len(blocks) == witness['declared_block_count'] == successful
                 and not evidence['failed_block_ids'] and evidence['symmetry'] == 'native_hic_symmetric',
                 'hic_complete_population_evidence_required')
    if complete:
        _require(evidence['axes_extent'] == 'complete', 'hic_complete_population_axes_required')
    if evidence['implicit_zero_semantics'] == 'validated_sparse_absence':
        _require(counts['unavailable_directed_cells'] == 0, 'hic_sparse_absence_has_unavailable_cells')
    else:
        _require(counts['implicit_zero_directed_cells'] is None, 'hic_unproven_sparse_count')
    normalization = population['normalization']
    selected = normalization['specification']
    vector = witness['selected_normalization']
    if selected['kind'] == 'raw':
        _require(vector is None and normalization['availability'] == 'not_requested', 'hic_unrequested_vector')
    else:
        _require(selected['convention'] == 'divisive', 'hic_requires_divisive_normalization')
        if vector is not None:
            region, resolution = population['selected_region'], witness['resolution_bp']
            physical = (chromosome['length_bp'] + resolution - 1) // resolution
            _require(vector['normalization_type'] == selected['weight_column']
                     and vector['chromosome_index'] == chromosome['chromosome_index']
                     and vector['resolution_bp'] == resolution
                     and vector['physical_chromosome_bin_count'] == physical
                     and vector['selected_bin_start'] == region['start_bp'] // resolution
                     and vector['selected_bin_end_exclusive'] == (region['end_bp'] + resolution - 1) // resolution,
                     'hic_normalization_identity_mismatch')
            if vector['native_range'] is not None:
                _bounded_range(vector['native_range'], size, complete=vector['outcome'] == 'complete')
        if normalization['availability'] in ('available', 'partial'):
            _require(vector is not None and vector['outcome'] == 'complete'
                     and normalization['native_weight_dtype'] == '<f4', 'hic_available_vector_proof_required')


def validate_hic_record_relationships(kind, value):
    if kind == 'HicHeader':
        _header(value)
    elif kind == 'HicBlockRead':
        _block(value)
    elif kind == 'HicVectorRead':
        _vector(value)
    elif kind == 'HicPopulationRead':
        _witness(value)
    elif kind == 'NativeMetadata':
        _metadata(value)
    elif kind in ('ContactExtraction', 'ContactSheet', 'NativeSheetHeader'):
        if kind == 'ContactExtraction':
            metadata, chromosomes = value['native_metadata'], value['chromosomes']
            hic = value['format'] == 'hic_binary_v9'
        elif kind == 'ContactSheet':
            metadata, chromosomes = value['native']['metadata'], value['native']['chromosomes']
            hic = value['request']['contact']['format'] == 'hic_binary_v9'
        else:
            metadata, chromosomes = value['metadata'], value['chromosomes']
            hic = metadata is not None and metadata['format'] == 'hic_binary_v9'
        if metadata is not None:
            _metadata(metadata)
        if not hic:
            return
        if metadata is not None:
            expected = [{'chromosome_index': row['chromosome_index'], 'chromosome': row['chromosome'],
                         'length_bp': row['native_length']} for row in metadata['hic']['chromosomes']
                        if row['kind'] == 'chromosome']
            _require(chromosomes == expected, 'hic_biological_chromosome_rows_mismatch')
        else:
            _require(not chromosomes, 'hic_chromosomes_without_header')
        for population in value.get('populations', []):
            validate_hic_population_records(population, metadata, chromosomes)
