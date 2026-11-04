"""Closed ATAC result records, separate from readers and numerical functions.

The numerical declarations below freeze delivered 004/005/010/013 records.
They validate ordinary data; they are not an alternative calculation language.
Native execution failures retain the producer's one authoritative declaration.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from jsonschema import Draft202012Validator


ROLES = ('signal1', 'background1', 'signal2', 'background2')
CATEGORIES = ('condition1', 'condition2', 'common')
KINDS = ('summary', 'native_peak_rows', 'native_differential_rows', 'interval_components', 'derived_regions')
SHEET_FORMAT = 'atac_differential_native_sheet_v1'
TABLE_FORMAT = 'atac_bedgraph_rows_jsonl_v1'
PLAN_VERSION = 'atac_differential_worker_plan_v1'
RESULT_VERSION = 'atac_differential_worker_result_v1'
ISSUE_CODES = (
    'artifact_missing', 'captured_bytes_partial', 'identity_mismatch', 'identity_unverified',
    'producer_failed', 'writer_not_closed', 'unsupported_format', 'unsupported_mode',
    'unsupported_normalization', 'invalid_utf8', 'wrong_column_count', 'invalid_coordinate',
    'coordinate_outside_reference', 'unknown_chromosome', 'invalid_number', 'nonfinite_number',
    'numeric_out_of_range', 'negative_pileup', 'metadata_missing', 'metadata_conflict',
    'duplicate_record', 'overlapping_track_rows', 'unsorted_track_rows', 'unreported_interval',
    'reference_conflict', 'condition_binding_conflict', 'depth_population_conflict', 'zero_depth',
    'peak_representation_conflict', 'native_bdgdiff_coordinate_displacement', 'stream_read_failed',
    'missing_column_header', 'incomplete_track_table_row', 'invalid_atac_track_table_row',
    'invalid_ordered_track_geometry', 'unsorted_track_table_rows', 'track_table_row_count_mismatch',
    'atac_projected_track_order_required', 'invalid_atac_unlocated_row_count',
    'incomplete_bam_reference_dictionary', 'unlocated_bam_reference_row', 'sequence_identity_unknown',
)
ISSUE_REQUIREMENTS = ('none', 'complete_artifact', 'matching_artifact', 'compatible_native_mode',
    'explicit_reference_mapping', 'unambiguous_track_values', 'condition_mapping',
    'matching_count_population', 'original_native_metadata')
NUMERICAL_REASONS = ('operand_unavailable', 'numeric_operand_required', 'numeric_overflow',
    'nonfinite_operand', 'negative_operand', 'zero_depth', 'float32_overflow',
    'depth_factor_underflow', 'adjusted_value_overflow', 'adjusted_value_underflow', 'likelihood_overflow')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, code='atac_result_record_mismatch'):
    if not condition:
        raise ValueError(code)


def obj(**properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def arr(items, **kwargs):
    return {'type': 'array', 'items': items, **kwargs}


def ref(name):
    return {'$ref': '#/$defs/' + name}


def enum(*values):
    return {'enum': list(values)}


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


ID = {'type': 'string', 'minLength': 1, 'maxLength': 4096, 'pattern': '^[^\\x00-\\x1f\\x7f]+$'}
TEXT = {'type': 'string'}
INT = {'type': 'integer', 'minimum': 0}
SINT = {'type': 'integer'}
NUM = {'type': 'number'}
BOOL = {'type': 'boolean'}
NULL = {'type': 'null'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
EXTENT = enum('complete', 'partial', 'unavailable')
DEPTH_UNIT = enum('tags', 'fragments', 'million_tags', 'million_fragments')
ORIGIN = enum('supplied_measurement', 'synthetic_engineering_fixture', 'unknown')
COORDINATE_QUALIFICATION = enum('macs2_2_2_9_1_native_endpos_displacement_demonstrated', 'unverified_native_version')


def _native_definitions(definitions, kind):
    """Embed A's exact schema tree with local-reference namespacing only."""
    from .native_atac_differential_contracts import atac_execution_schema
    schema = atac_execution_schema(kind)
    def rewrite(node):
        if isinstance(node, dict):
            return {k: ('#/$defs/Native.' + v.removeprefix('#/$defs/')
                        if k == '$ref' and v.startswith('#/$defs/') else rewrite(v))
                    for k, v in node.items() if k not in ('$defs', '$schema', '$id')}
        if isinstance(node, list):
            return [rewrite(v) for v in node]
        return node
    for name, value in schema.get('$defs', {}).items():
        definitions['Native.' + name] = rewrite(value)
    return rewrite(schema)


def _definitions():
    d = {}
    d['NativeFileIdentity'] = obj(artifact_ref=ID, sha256=SHA, size_bytes=INT, format=ID)
    d['NativeFileDeclaration'] = obj(relative_path=ID, format=ID, state=enum('present', 'absent'),
        sha256=nullable(SHA), size_bytes=nullable(INT))
    d['NativeFileCapture'] = obj(declared=ref('NativeFileDeclaration'), observed=nullable(ref('NativeFileIdentity')),
        outcome=enum('verified', 'declared_absent', 'digest_mismatch', 'unavailable'),
        failure=enum(None, 'capture_file_unavailable', 'capture_file_digest_mismatch'))
    d['Locator'] = obj(line_number={'type': 'integer', 'minimum': 1}, byte_start=INT, byte_end=INT)
    d['AtacIssue'] = obj(code=enum(*ISSUE_CODES), artifact_ref=nullable(ID), binding_key=ID,
        row_ordinals=arr(INT), locations=arr(ref('Locator')), field=nullable(ID), requirement=enum(*ISSUE_REQUIREMENTS))
    d['AtacArtifact'] = obj(artifact_ref=nullable(ID), format=ID, expected_sha256=nullable(SHA),
        expected_size_bytes=nullable(INT), supplied_extent=enum('complete', 'partial', 'unknown'),
        producer_run_ref=nullable(ID), producer_outcome=enum('succeeded', 'failed', 'not_run', 'unknown'),
        writer_closed=nullable(BOOL), producer_name=nullable(ID), producer_version=nullable(ID),
        producer_source_ref=nullable(ID), origin=ORIGIN)
    d['HeaderRecord'] = obj(locator=ref('Locator'), kind=enum('comment', 'track', 'browser', 'blank', 'column_header', 'sam_header'), text=nullable(TEXT))
    d['InvalidRecord'] = obj(row_ordinal=INT, locator=ref('Locator'), fields=nullable(arr(TEXT)), reason_codes=arr(enum(*ISSUE_CODES)))
    d['AtacContig'] = obj(chromosome=ID, length_bp=nullable(INT), sequence_accession_version=nullable(ID),
        sequence_sha256=nullable(SHA), source_refs=arr(ID))
    d['AtacChromosomeAlias'] = obj(source_chromosome=ID, target_chromosome=ID, reference_id=ID, source_refs=arr(ID))
    d['AtacReference'] = obj(reference_id=ID, assembly_accession_version=nullable(ID), source_refs=arr(ID),
        contigs=arr(ref('AtacContig')), aliases=arr(ref('AtacChromosomeAlias')))
    d['AtacSample'] = obj(sample_id=ID, input_artifact_refs=arr(ID), reference_id=ID,
        biospecimen_id=nullable(ID), replicate_id=nullable(ID), origin=ORIGIN)
    d['AtacCondition'] = obj(condition_id=ID, label=nullable(ID), sample_ids=arr(ID))
    d['CallpeakParameters'] = obj(genome_size_argument=nullable(ID), effective_genome_size_bp=nullable(NUM),
        keep_duplicates={'anyOf': [INT, enum('all', 'auto', None)]}, nomodel=nullable(BOOL), shift_bp=nullable(SINT),
        extension_size_bp=nullable(INT), qvalue_cutoff=nullable(NUM), pvalue_cutoff=nullable(NUM), store_bedgraph=nullable(BOOL),
        spmr=nullable(BOOL), broad=nullable(BOOL), downsample=nullable(BOOL), small_local_window_bp=nullable(INT), large_local_window_bp=nullable(INT))
    d['AtacCallpeakBinding'] = obj(run_key=ID, condition_id=ID, sample_ids=arr(ID), reference_id=ID,
        treatment_input_refs=arr(ID), supplied_control_sample_ids=nullable(arr(ID)), supplied_control_input_refs=nullable(arr(ID)),
        selected_format=ID, paired_end=nullable(BOOL), selected_argv=arr(ID), selected_parameters=ref('CallpeakParameters'),
        artifact_roles=obj(**{k: nullable(ID) for k in ('peaks_xls', 'narrowpeak', 'summits', 'signal_track', 'background_track')}), producer_ref=ID)
    d['BdgdiffParameters'] = obj(depth1_lexeme=nullable(ID), depth2_lexeme=nullable(ID),
        depth_unit=enum('tags', 'fragments', 'million_tags', 'million_fragments', 'unknown'), cutoff_log10_lr=nullable(NUM),
        minimum_length_bp=nullable(INT), maximum_gap_bp=nullable(INT), native_pseudocount=nullable(NUM))
    d['AtacComparisonBinding'] = obj(comparison_key=ID, condition1_id=ID, condition2_id=ID, reference_id=ID,
        track_keys=obj(**{k: ID for k in ROLES}), selected_argv=arr(ID), selected_parameters=ref('BdgdiffParameters'),
        artifact_roles=obj(**{k: nullable(ID) for k in CATEGORIES}), producer_ref=nullable(ID))
    d['AtacTrackBinding'] = obj(track_key=ID, condition_id=ID, sample_ids=arr(ID), role=enum('signal', 'model_background'),
        callpeak_run_key=nullable(ID), reference_id=ID,
        value_unit=enum(None, 'extended_tag_pileup', 'model_expected_extended_tag_pileup', 'supplied_signal', 'supplied_model_background'),
        normalization=enum('raw_pileup', 'spmr', 'unknown'), background_origin=enum('self_model', 'supplied_control_model', 'explicit_supplied_track', 'unknown'),
        source_artifact_ref=nullable(ID))
    d['TrackChromosomeExtent'] = obj(chromosome=ID, first_reported_start=nullable(INT), last_reported_end=nullable(INT),
        readable_row_count=INT, has_unreported_leading_span=nullable(BOOL), has_unreported_internal_span=BOOL,
        has_unreported_tail=nullable(BOOL), reference_length_bp=nullable(INT))
    columns = ['row_ordinal', 'line_number', 'byte_start', 'byte_end', 'chromosome', 'start', 'end', 'value_numeric', 'value_lexeme']
    d['AtacRetainedTrackTable'] = obj(storage={'const': 'retained_table'}, artifact_ref=ID, format={'const': TABLE_FORMAT},
        columns={'const': columns}, row_count=INT, sha256=SHA, byte_count=INT,
        order=enum('native_file_order', 'chromosome_start_end_source_ordinal'), source_artifact_ref=ID)
    d['BedGraphRow'] = {'type': 'array', 'prefixItems': [INT, {'type': 'integer', 'minimum': 1}, INT, INT, ID,
        nullable(SINT), nullable(SINT), nullable(NUM), nullable(TEXT)], 'items': False, 'minItems': 9, 'maxItems': 9}
    d['PeakGeometry'] = obj(row_ordinal=INT, start0=nullable(INT), end0=nullable(INT), summit0=nullable(INT),
        span_bp=nullable(INT), status=enum('valid', 'partial', 'invalid'))
    d['PeakLink'] = obj(callpeak_run_key=ID, name=TEXT, xls_row_ordinals=arr(INT), narrowpeak_row_ordinals=arr(INT),
        summit_row_ordinals=arr(INT), status=enum('matched', 'missing_representation', 'ambiguous', 'conflicting'))
    base_row = dict(row_ordinal=INT, locator=ref('Locator'), original_fields=arr(TEXT), chromosome=TEXT)
    d['XlsRow'] = obj(**base_row, **{k: nullable(SINT) for k in ('start1', 'end1', 'length_bp', 'abs_summit1')},
        **{k: nullable(NUM) for k in ('pileup', 'minus_log10_pvalue', 'fold_enrichment', 'minus_log10_qvalue')}, name=TEXT)
    d['NarrowPeakRow'] = obj(**base_row, start0=nullable(SINT), end0=nullable(SINT), name=TEXT, display_score=nullable(SINT), strand=TEXT,
        signal_value=nullable(NUM), minus_log10_pvalue=nullable(NUM), minus_log10_qvalue=nullable(NUM), summit_offset0=nullable(SINT))
    d['SummitRow'] = obj(**base_row, start0=nullable(SINT), end0=nullable(SINT), name=TEXT, score=nullable(NUM))
    d['BdgdiffRow'] = obj(**base_row, reported_start0=nullable(SINT), reported_end0=nullable(SINT), name=TEXT, reported_score=nullable(NUM))
    d['AtacBamReferenceRow'] = obj(row_ordinal=INT, locator=ref('Locator'), chromosome=nullable(ID), length_bp=nullable(SINT),
        sequence_md5=nullable({'type': 'string', 'pattern': '^[0-9a-fA-F]{32}$'}), original_fields=arr(TEXT))
    d['ReportedNumber'] = obj(value=nullable(NUM), lexeme=nullable(TEXT), state=enum('present', 'missing', 'invalid', 'conflicting', 'not_measured'), locations=arr(ref('Locator')))
    number_fields = ('effective_genome_size_bp', 'band_width_bp', 'model_fold_lower', 'model_fold_upper', 'qvalue_cutoff',
        'pvalue_cutoff', 'large_local_window_bp', 'tag_size_bp', 'fragment_size_bp', 'treatment_total_tags', 'treatment_postfilter_tags',
        'treatment_max_duplicates', 'treatment_redundant_rate', 'control_total_tags', 'control_postfilter_tags', 'control_max_duplicates',
        'control_redundant_rate', 'treatment_total_fragments', 'treatment_postfilter_fragments', 'control_total_fragments',
        'control_postfilter_fragments', 'shift_bp', 'd_bp')
    metadata = dict(**{k: nullable(TEXT) for k in ('macs_version', 'command_line', 'name', 'format')},
        treatment_paths=nullable(arr(TEXT)), control_paths=nullable(arr(TEXT)), control_presence=enum('absent', 'present', 'unknown'),
        paired_end=nullable(BOOL), broad=nullable(BOOL), scaling_direction=enum('larger_to_smaller', 'smaller_to_larger', 'unknown'),
        local_lambda=enum('enabled', 'disabled', 'unknown'))
    metadata['field_locations'] = {'type': 'object', 'properties': {k: arr(ref('Locator')) for k in metadata}, 'additionalProperties': False}
    envelope = dict(artifact=ref('AtacArtifact'), binding_key=ID, state=obj(availability=enum('present', 'missing'),
        byte_extent=enum('complete', 'partial', 'unknown'), identity=enum('verified', 'unverified', 'mismatch'),
        format=enum('compatible', 'malformed', 'unsupported'), output_extent=enum('complete', 'partial', 'unknown')),
        parsed_sha256=nullable(SHA), parsed_byte_count=INT, physical_line_count=INT, data_row_count=nullable(INT),
        readable_data_row_count=INT, malformed_data_row_count=INT, headers=arr(ref('HeaderRecord')),
        invalid_records=arr(ref('InvalidRecord')), issues=arr(ref('AtacIssue')))
    d['ParsedAtacTrack'] = obj(**envelope, version={'const': 'atac_bedgraph_parsed_v1'},
        rows={'anyOf': [arr(ref('BedGraphRow')), ref('AtacRetainedTrackTable')]}, binding=ref('AtacTrackBinding'),
        coordinate_convention={'const': 'zero_based_half_open'}, numeric_storage={'const': 'native_decimal_lexeme_plus_binary64_parse'},
        native_writer_precision=enum('fixed_5_decimal_places', 'supplied_lexical', 'unknown'), row_order={'const': 'native_file_order'},
        ordered_row_index=nullable(arr(INT)), chromosome_extents=arr(ref('TrackChromosomeExtent')), overlap_groups=arr(arr(INT)),
        geometry_inspection=enum('complete', 'partial', 'unknown'), unlocated_invalid_row_count=INT)
    d['ParsedMacs2PeaksXls'] = obj(**envelope, version={'const': 'macs2_peaks_xls_parsed_v1'}, rows=arr(ref('XlsRow')),
        callpeak_run_key=ID, reported_metadata=obj(**metadata), reported_numbers=obj(**{k: ref('ReportedNumber') for k in number_fields}),
        coordinate_convention={'const': 'one_based_inclusive'}, peak_geometry=arr(ref('PeakGeometry')))
    for name, version, row in (('ParsedMacs2NarrowPeak', 'macs2_narrowpeak_parsed_v1', 'NarrowPeakRow'),
                             ('ParsedMacs2Summits', 'macs2_summits_parsed_v1', 'SummitRow')):
        d[name] = obj(**envelope, version={'const': version}, rows=arr(ref(row)), callpeak_run_key=ID,
            coordinate_convention={'const': 'zero_based_half_open'}, score_basis=enum('minus_log10_qvalue', 'minus_log10_pvalue', 'unknown'))
    d['ParsedMacs2Bdgdiff'] = obj(**envelope, version={'const': 'macs2_bdgdiff_parsed_v1'}, rows=arr(ref('BdgdiffRow')),
        comparison_key=ID, category=enum(*CATEGORIES), coordinate_convention={'const': 'zero_based_half_open_as_reported'},
        coordinate_qualification=COORDINATE_QUALIFICATION, score_precision=enum('native_float32_then_6_significant_decimal_digits', 'unknown'))
    d['ParsedAtacBamReference'] = obj(**envelope, version={'const': 'atac_bam_reference_parsed_v1'}, rows=arr(ref('AtacBamReferenceRow')),
        callpeak_run_key=ID, input_ordinal=INT, input_artifact_ref=ID)
    d['DepthCount'] = obj(condition_id=ID, sample_ids=arr(ID), callpeak_run_key=nullable(ID), count=nullable(INT), count_lexeme=nullable(TEXT),
        count_unit={'const': 'postfilter_single_end_tags'}, count_population={'const': 'macs2_loaded_treatment_tags_after_duplicate_filtering'},
        source_artifact_ref=nullable(ID), source_locations=arr(ref('Locator')), source_field={'const': 'treatment_postfilter_tags'},
        million_denominator={'const': 1000000}, state=enum('observed', 'missing', 'conflicting', 'incompatible_mode', 'zero'))
    d['DeclaredDepth'] = obj(condition_id=ID, sample_ids=arr(ID), value=nullable(NUM), value_lexeme=nullable(TEXT), unit=DEPTH_UNIT,
        population={'type': 'string', 'minLength': 1, 'pattern': '^[A-Za-z0-9_.:-]+$'}, source_ref=ID,
        origin=enum('synthetic_engineering_fixture', 'explicit_supplied_metadata'), state=enum('declared', 'missing', 'invalid'))
    for name, kind, row in (('AtacDepthCountSelection', 'native_postfilter_counts', 'DepthCount'),
                           ('AtacDeclaredDepthSelection', 'explicit_declared_depths', 'DeclaredDepth')):
        d[name] = obj(kind={'const': kind}, conditions=arr(ref(row), minItems=2, maxItems=2), compatible_population=BOOL, issues=arr(ref('AtacIssue')))
    d['DepthSelection'] = {'oneOf': [ref('AtacDepthCountSelection'), ref('AtacDeclaredDepthSelection')]}
    d['NativeSheet'] = obj(version={'const': SHEET_FORMAT}, tool_row={'const': 'B-L125-analyze_atac_seq_differential_accessibility'},
        reference=ref('AtacReference'), samples=arr(ref('AtacSample')), conditions=arr(ref('AtacCondition'), minItems=2, maxItems=2),
        callpeak_bindings=arr(ref('AtacCallpeakBinding')), comparison=ref('AtacComparisonBinding'), tracks=arr(ref('ParsedAtacTrack'), minItems=4, maxItems=4),
        peaks_xls=arr(ref('ParsedMacs2PeaksXls')), narrowpeaks=arr(ref('ParsedMacs2NarrowPeak')), summits=arr(ref('ParsedMacs2Summits')),
        peak_links=arr(ref('PeakLink')), native_differential=arr(ref('ParsedMacs2Bdgdiff')), bam_references=arr(ref('ParsedAtacBamReference')),
        depth_selection=ref('DepthSelection'), reference_relation=enum('same_supplied_reference', 'conflicting', 'unknown'),
        normalization_compatibility=enum('raw_compatible', 'incompatible', 'unknown'),
        coverage_completeness=enum('complete_declared_domain', 'partial_declared_domain', 'unknown'),
        data_status=enum('complete_reported_data', 'partial_reported_data', 'unavailable'), issues=arr(ref('AtacIssue')))
    d['Interval'] = obj(chromosome=ID, start=INT, end={'type': 'integer', 'minimum': 1, 'maximum': 2**63 - 1})
    d['Parameters'] = obj(pseudocount={'type': 'number', 'exclusiveMinimum': 0}, cutoff_log10_lr={'type': 'number', 'minimum': 0},
        minimum_length_bp={'type': 'integer', 'minimum': 1}, maximum_gap_bp=INT)
    d['Window'] = obj(offset=INT, limit={'type': 'integer', 'minimum': 1})
    d['SavedSheetBundle'] = obj(sheet=ref('NativeFileIdentity'), tables=arr(obj(track_key=ID, file=ref('NativeFileIdentity'))))
    d['ResultSelector'] = obj(version={'const': 'atac_differential_result_selector_v1'}, mode=enum('native_result', 'saved_sheet_recalculation'),
        comparison_key=ID, intervals=arr(ref('Interval')), parameters=ref('Parameters'),
        projection=obj(kind=enum(*KINDS), row_window=nullable(ref('Window')), run_keys=arr(ID, uniqueItems=True), categories=arr(enum(*CATEGORIES), uniqueItems=True)),
        saved_sheet_bundle=nullable(ref('SavedSheetBundle')))
    measurement = lambda unit: obj(value=nullable(NUM), state=enum('derived', 'missing', 'invalid', 'undefined'),
        reason=enum(None, *NUMERICAL_REASONS), unit={'const': unit})
    d['Scores'] = obj(method={'const': 'macs2_2_2_9_1_likelihoods_correct_track_intervals'},
        parameters=obj(pseudocount=NUM, depth_unit=DEPTH_UNIT, input_precision={'const': 'ieee754_binary32'},
            arithmetic_precision={'const': 'ieee754_binary64'}, score_precision={'const': 'ieee754_binary32'}),
        inputs=obj(**{k: nullable(NUM) for k in (*ROLES, 'depth1', 'depth2')}),
        native_input_values=obj(**{k: measurement('pileup') for k in ROLES}),
        depth_factors=obj(**{k: measurement('1') for k in CATEGORIES[:2]}),
        adjusted_values=obj(**{k: measurement('depth_scaled_pileup') for k in ROLES}),
        likelihoods=obj(**{name: obj(unrounded=measurement('signed_log10_likelihood_ratio'), native_float32=measurement('signed_log10_likelihood_ratio'),
            operands={'const': operands}) for name, operands in (
                ('condition1_vs_background', ['signal1', 'background1']), ('condition2_vs_background', ['signal2', 'background2']),
                ('condition1_vs_condition2', ['signal1', 'signal2']))}),
        input_issues=arr(obj(field=enum(*ROLES, 'depth1', 'depth2'), reason=enum(*NUMERICAL_REASONS))),
        uncertainty=obj(kind={'const': 'not_estimated'}, value=NULL))
    segment = dict(interval_ordinal=INT, population_ordinal=INT, chromosome=ID, start=INT, end=INT,
        values=obj(**{k: nullable(NUM) for k in ROLES}), states=obj(**{k: enum('observed', 'missing', 'invalid', 'ambiguous') for k in ROLES}),
        source_rows=obj(**{k: arr(INT) for k in ROLES}), source_extents=obj(**{k: enum('complete', 'partial', 'missing', 'failed') for k in ROLES}),
        unlocated_invalid_rows=obj(**{k: INT for k in ROLES}))
    d['Partition'] = obj(**segment)
    d['Component'] = obj(**segment, scores=ref('Scores'))
    d['Region'] = obj(category=enum(*CATEGORIES), population_ordinal=INT, chromosome=ID, start=INT, end=INT,
        span_bp=INT, qualifying_bp=INT, bridged_gap_bp=INT, qualifying_interval_ordinals=arr(INT), score_numerator=NUM,
        score_denominator_bp=INT, mean_score=NUM, native_float32_mean_score=nullable(NUM), score_unit={'const': 'signed_log10_likelihood_ratio'},
        left_boundary=enum('population_boundary', 'observed_gap', 'unknown_gap'), right_boundary=enum('population_boundary', 'observed_gap', 'unknown_gap'),
        source_extent=enum('complete', 'partial'), numerical_reason=enum(None, 'float32_overflow'))
    d['CalculatedTable'] = obj(table_key=enum('partitions', 'components', 'regions'), role=enum('partitions', 'components', 'regions'),
        file=ref('NativeFileIdentity'), row_count=INT, extent=enum('complete', 'partial'), source_table_keys=arr(ID))
    d['DepthOperands'] = obj(depth1=nullable(NUM), depth2=nullable(NUM), depth_unit=nullable(DEPTH_UNIT))
    d['Eligibility'] = obj(population=enum('usable', 'unavailable'), tracks=obj(**{k: enum('usable', 'missing', 'unavailable') for k in ROLES}), depths=enum('usable', 'unavailable'))
    d['Summary'] = obj(depth_selection=ref('DepthSelection'), depth_operands=ref('DepthOperands'), selected_population_bp=INT,
        partition_coverage=obj(all_four_observed_bp=nullable(INT), unavailable_or_invalid_bp=nullable(INT), extent=EXTENT),
        native_peak_counts=arr(obj(run_key=ID, representation=enum('xls', 'narrowpeak', 'summit'), count=nullable(INT), extent=EXTENT)),
        native_region_counts=arr(obj(category=enum(*CATEGORIES), count=nullable(INT), extent=EXTENT, coordinate_qualification=COORDINATE_QUALIFICATION)),
        derived_region_counts=arr(obj(category=enum(*CATEGORIES), count=nullable(INT), qualifying_bp=nullable(INT), span_bp=nullable(INT), extent=EXTENT)),
        reference_relation=d['NativeSheet']['properties']['reference_relation'], normalization_compatibility=d['NativeSheet']['properties']['normalization_compatibility'],
        coverage_completeness=d['NativeSheet']['properties']['coverage_completeness'], uncertainty=obj(kind={'const': 'not_estimated'}, value=NULL))
    d['NativePeakRow'] = {'oneOf': [obj(callpeak_run_key=ID, representation={'const': kind}, source=ref('AtacArtifact'),
        row=ref(row), geometry=ref('PeakGeometry') if kind == 'xls' else NULL, peak_link=nullable(ref('PeakLink')))
        for kind, row in (('xls', 'XlsRow'), ('narrowpeak', 'NarrowPeakRow'), ('summit', 'SummitRow'))]}
    d['NativePeakComponents'] = obj(version={'const': 'macs2_peak_components_v1'},
        reference=ref('AtacReference'), callpeak_bindings=arr(ref('AtacCallpeakBinding')),
        peaks_xls=arr(ref('ParsedMacs2PeaksXls')), narrowpeaks=arr(ref('ParsedMacs2NarrowPeak')),
        summits=arr(ref('ParsedMacs2Summits')), peak_links=arr(ref('PeakLink')),
        reference_relation=d['NativeSheet']['properties']['reference_relation'],
        data_status=d['NativeSheet']['properties']['data_status'], issues=arr(ref('AtacIssue')))
    d['NativePeakWindow'] = obj(row_window=ref('Window'), total_rows=nullable(INT),
        row_extent=EXTENT, rows=arr(ref('NativePeakRow')))
    d['NativeDifferentialRow'] = obj(category=enum(*CATEGORIES), source=ref('AtacArtifact'), row=ref('BdgdiffRow'), coordinate_qualification=COORDINATE_QUALIFICATION)
    d['Failure'] = _native_definitions(d, 'Failure')
    projection = dict(version={'const': 'atac_differential_projection_v1'}, comparison_key=ID, reference_id=ID,
        condition_ids=arr(ID, minItems=2, maxItems=2), selected_intervals=arr(ref('Interval')), parameters=ref('Parameters'),
        total_rows=nullable(INT), row_extent=EXTENT, qualifications=arr(ref('AtacIssue')), failures=arr(ref('Failure')))
    d['RequestedProjection'] = {'oneOf': [obj(**projection, kind={'const': kind}, row_window=NULL if kind == 'summary' else ref('Window'),
        rows=arr(ref(row)) if row else {'const': []}, summary=ref('Summary') if kind == 'summary' else NULL)
        for kind, row in (('summary', None), ('native_peak_rows', 'NativePeakRow'), ('native_differential_rows', 'NativeDifferentialRow'),
                         ('interval_components', 'Component'), ('derived_regions', 'Region'))]}
    d['Projection'] = ref('RequestedProjection')
    d['StreamState'] = obj(track_key=ID, extent=enum('complete', 'partial', 'missing', 'failed'), exhausted=BOOL)
    d['Calculations'] = obj(version={'const': 'atac_differential_calculations_v1'}, comparison_key=ID, reference_id=ID,
        condition_ids=arr(ID, minItems=2, maxItems=2), selected_intervals=arr(ref('Interval')), parameters=ref('Parameters'),
        depth_operands=ref('DepthOperands'), eligibility=ref('Eligibility'), issues=arr(ref('AtacIssue')), tables=arr(ref('CalculatedTable')),
        summary=ref('Summary'), stream_states=arr(ref('StreamState')), failures=arr(ref('Failure')), uncertainty=obj(kind={'const': 'not_estimated'}, value=NULL))
    d['Diagnostics'] = obj(version={'const': 'atac_differential_diagnostics_v1'}, mode=enum('native_result', 'saved_sheet_recalculation'),
        issues=arr(ref('AtacIssue')), failures=arr(ref('Failure')), stream_states=arr(ref('StreamState')))
    d['WorkerOutput'] = obj(role=enum('sheet', 'track_table', 'partitions', 'components', 'regions', 'calculations', 'projection', 'diagnostics'),
        table_key=nullable(ID), declaration=ref('NativeFileDeclaration'))
    d['WorkerResult'] = obj(version={'const': RESULT_VERSION}, mode=enum('native_result', 'saved_sheet_recalculation'),
        parameters=ref('Parameters'), state=enum('produced', 'partial', 'unavailable'), outputs=arr(ref('WorkerOutput')), failures=arr(ref('Failure')))
    d['WorkerCapture'] = obj(version={'const': 'atac_differential_worker_capture_v1'}, plan_file=ref('NativeFileIdentity'),
        execution_receipt_file=ref('NativeFileIdentity'), worker_result_file=nullable(ref('NativeFileIdentity')), result=nullable(ref('WorkerResult')),
        outputs=arr(obj(role=d['WorkerOutput']['properties']['role'], table_key=nullable(ID), capture=ref('NativeFileCapture'))), failures=arr(ref('Failure')))
    retained = obj(file=ref('NativeFileIdentity'), path=ID)
    capture_schema = _native_definitions(d, 'NativeCapture')
    # A exports a self-contained schema. Resolve its root reference for the exact
    # capture property declarations; no source-code introspection is involved.
    capture = capture_schema
    while '$ref' in capture:
        capture = d[capture['$ref'].removeprefix('#/$defs/')]
    native = obj(version={'const': PLAN_VERSION}, mode={'const': 'native_result'}, directory=ID,
        original_plan=_native_definitions(d, 'RunPlan'), selector=ref('ResultSelector'),
        **{k: deepcopy(capture['properties'][k]) for k in ('bundle', 'files', 'source_action_receipt_ref', 'writer_closure_receipt_ref', 'driver_state', 'failures')})
    saved = obj(version={'const': PLAN_VERSION}, mode={'const': 'saved_sheet_recalculation'}, directory=ID,
        sheet_bundle=obj(sheet=retained, tables=arr(obj(track_key=ID, file=ref('NativeFileIdentity'), path=ID))), selector=ref('ResultSelector'))
    d['WorkerPlan'] = {'oneOf': [native, saved]}
    return d


def atac_result_schema(kind: str) -> dict:
    if kind == 'Failure':
        from .native_atac_differential_contracts import atac_execution_schema
        return atac_execution_schema('Failure')
    definitions = _definitions()
    if kind not in definitions:
        raise ValueError('unknown_atac_result_record')
    # Include only reachable definitions. In particular model-facing fact trees
    # never include unrelated runtime/software/command declarations.
    needed, pending = {}, [kind]
    def references(node):
        if isinstance(node, dict):
            if '$ref' in node:
                yield node['$ref'].removeprefix('#/$defs/')
            for value in node.values():
                yield from references(value)
        elif isinstance(node, list):
            for value in node:
                yield from references(value)
    while pending:
        name = pending.pop()
        if name not in needed:
            needed[name] = definitions[name]
            pending.extend(references(definitions[name]))
    return deepcopy({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$defs': needed, '$ref': '#/$defs/' + kind})


def _identity(file):
    require(file['artifact_ref'] == 'artifact_' + file['sha256'], 'atac_file_identity_mismatch')


def _finite(value):
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _finite(item)
    elif type(value) is float:
        require(math.isfinite(value), 'atac_finite_json_required')


def validate_atac_result_record(kind: str, value: object) -> dict:
    _finite(value)
    try:
        Draft202012Validator(atac_result_schema(kind)).validate(value)
    except Exception as error:
        raise ValueError('invalid_atac_result_' + kind) from error
    if kind == 'ResultSelector':
        p, view = value['parameters'], value['projection']
        require(p['maximum_gap_bp'] < p['minimum_length_bp'], 'atac_positive_minimum_and_smaller_nonnegative_gap_required')
        require((view['row_window'] is None) == (view['kind'] == 'summary'), 'atac_result_window_required')
        require(not view['run_keys'] or view['kind'] == 'native_peak_rows', 'atac_result_run_selection_conflict')
        require(not view['categories'] or view['kind'] in ('native_differential_rows', 'derived_regions'), 'atac_result_category_selection_conflict')
        require((value['saved_sheet_bundle'] is None) == (value['mode'] == 'native_result'), 'atac_result_saved_bundle_required')
        previous = None
        for interval in value['intervals']:
            key = interval['chromosome'].encode('utf-8')
            require(interval['start'] < interval['end'] and (previous is None or key > previous[0] or key == previous[0] and interval['start'] >= previous[1]), 'atac_populations_out_of_order_or_overlapping')
            previous = key, interval['end']
        if value['saved_sheet_bundle'] is not None:
            validate_atac_result_record('SavedSheetBundle', value['saved_sheet_bundle'])
    elif kind == 'SavedSheetBundle':
        _identity(value['sheet'])
        require(value['sheet']['format'] == SHEET_FORMAT, 'atac_saved_sheet_format_required')
        require(len({r['track_key'] for r in value['tables']}) == len(value['tables']), 'atac_saved_track_keys_unique')
        for row in value['tables']:
            _identity(row['file'])
            require(row['file']['format'] == TABLE_FORMAT, 'atac_saved_table_format_required')
    elif kind == 'NativeFileIdentity':
        _identity(value)
    elif kind in ('Projection', 'RequestedProjection'):
        require(value['condition_ids'][0] != value['condition_ids'][1], 'atac_result_conditions_conflict')
        if value['kind'] == 'summary':
            require(value['total_rows'] == 0, 'atac_summary_row_count')
        else:
            require(len(value['rows']) <= value['row_window']['limit'], 'atac_projection_window_exceeded')
            if value['row_extent'] == 'complete':
                require(value['total_rows'] is not None and len(value['rows']) == min(value['row_window']['limit'],
                    max(0, value['total_rows'] - value['row_window']['offset'])), 'atac_projection_complete_population_mismatch')
            elif value['row_extent'] == 'unavailable':
                require(not value['rows'], 'atac_unavailable_projection_has_rows')
        require(value['row_extent'] == 'complete' or value['total_rows'] is None or value['kind'] == 'summary', 'atac_partial_total_unknown')
    elif kind == 'CalculatedTable':
        _identity(value['file'])
        require(value['role'] == value['table_key'], 'atac_calculated_table_role_conflict')
        expected = {'partitions': 'atac_interval_partitions_jsonl_v1', 'components': 'atac_interval_components_jsonl_v1', 'regions': 'atac_differential_regions_jsonl_v1'}
        require(value['file']['format'] == expected[value['role']], 'atac_calculated_table_format_conflict')
    return deepcopy(value)


__all__ = ['atac_result_schema', 'validate_atac_result_record', 'ROLES', 'CATEGORIES', 'KINDS',
    'SHEET_FORMAT', 'TABLE_FORMAT', 'PLAN_VERSION', 'RESULT_VERSION', 'ISSUE_CODES', 'ISSUE_REQUIREMENTS']
