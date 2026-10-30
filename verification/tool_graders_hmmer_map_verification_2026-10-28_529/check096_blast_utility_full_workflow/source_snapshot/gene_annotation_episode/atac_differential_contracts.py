"""Ordinary data records for retained ATAC/MACS2 measurements.

These records contain native numbers, explicit associations and source locations.
They do not define executable scoring rules, acquire data, or assign credit.
Scientific incompatibilities are issues; impossible Python input shapes are errors.
"""
from __future__ import annotations

import math
import re
from typing import Literal, TypeAlias, TypedDict


Number: TypeAlias = int | float
Origin: TypeAlias = Literal['supplied_measurement', 'synthetic_engineering_fixture', 'unknown']
BedGraphRow: TypeAlias = tuple[int, int, int, int, str, int | None, int | None, float | None, str | None]
BEDGRAPH_COLUMNS = ('row_ordinal', 'line_number', 'byte_start', 'byte_end',
                    'chromosome', 'start', 'end', 'value_numeric', 'value_lexeme')
MAX_COORDINATE = 2**63 - 1


class Locator(TypedDict):
    line_number: int
    byte_start: int
    byte_end: int


class AtacArtifact(TypedDict):
    artifact_ref: str | None
    format: str
    expected_sha256: str | None
    expected_size_bytes: int | None
    supplied_extent: str
    producer_run_ref: str | None
    producer_outcome: str
    writer_closed: bool | None
    producer_name: str | None
    producer_version: str | None
    producer_source_ref: str | None
    origin: Origin


class AtacIssue(TypedDict):
    code: str
    artifact_ref: str | None
    binding_key: str
    row_ordinals: list[int]
    locations: list[Locator]
    field: str | None
    requirement: str


class HeaderRecord(TypedDict):
    locator: Locator
    kind: str
    text: str | None


class InvalidRecord(TypedDict):
    row_ordinal: int
    locator: Locator
    fields: list[str] | None
    reason_codes: list[str]


class AtacContig(TypedDict):
    chromosome: str
    length_bp: int | None
    sequence_accession_version: str | None
    sequence_sha256: str | None
    source_refs: list[str]


class AtacChromosomeAlias(TypedDict):
    source_chromosome: str
    target_chromosome: str
    reference_id: str
    source_refs: list[str]


class AtacReference(TypedDict):
    reference_id: str
    assembly_accession_version: str | None
    source_refs: list[str]
    contigs: list[AtacContig]
    aliases: list[AtacChromosomeAlias]


class AtacSample(TypedDict):
    sample_id: str
    input_artifact_refs: list[str]
    reference_id: str
    biospecimen_id: str | None
    replicate_id: str | None
    origin: Origin


class AtacCondition(TypedDict):
    condition_id: str
    label: str | None
    sample_ids: list[str]


class CallpeakParameters(TypedDict):
    genome_size_argument: str | None
    effective_genome_size_bp: Number | None
    keep_duplicates: int | Literal['all', 'auto'] | None
    nomodel: bool | None
    shift_bp: int | None
    extension_size_bp: int | None
    qvalue_cutoff: Number | None
    pvalue_cutoff: Number | None
    store_bedgraph: bool | None
    spmr: bool | None
    broad: bool | None
    downsample: bool | None
    small_local_window_bp: int | None
    large_local_window_bp: int | None


class CallpeakArtifactRoles(TypedDict):
    peaks_xls: str | None
    narrowpeak: str | None
    summits: str | None
    signal_track: str | None
    background_track: str | None


class AtacCallpeakBinding(TypedDict):
    run_key: str
    condition_id: str
    sample_ids: list[str]
    reference_id: str
    treatment_input_refs: list[str]
    supplied_control_sample_ids: list[str] | None
    supplied_control_input_refs: list[str] | None
    selected_format: str
    paired_end: bool | None
    selected_argv: list[str]
    selected_parameters: CallpeakParameters
    artifact_roles: CallpeakArtifactRoles
    producer_ref: str


class BdgdiffParameters(TypedDict):
    depth1_lexeme: str | None
    depth2_lexeme: str | None
    depth_unit: str
    cutoff_log10_lr: Number | None
    minimum_length_bp: int | None
    maximum_gap_bp: int | None
    native_pseudocount: Number | None


class AtacComparisonBinding(TypedDict):
    comparison_key: str
    condition1_id: str
    condition2_id: str
    reference_id: str
    track_keys: dict[str, str]
    selected_argv: list[str]
    selected_parameters: BdgdiffParameters
    artifact_roles: dict[str, str | None]
    producer_ref: str | None


class AtacTrackBinding(TypedDict):
    track_key: str
    condition_id: str
    sample_ids: list[str]
    role: str
    callpeak_run_key: str | None
    reference_id: str
    value_unit: str | None
    normalization: str
    background_origin: str
    source_artifact_ref: str | None


class TrackChromosomeExtent(TypedDict):
    chromosome: str
    first_reported_start: int | None
    last_reported_end: int | None
    readable_row_count: int
    has_unreported_leading_span: bool | None
    has_unreported_internal_span: bool
    has_unreported_tail: bool | None
    reference_length_bp: int | None


class AtacRetainedTrackTable(TypedDict):
    storage: Literal['retained_table']
    artifact_ref: str
    format: Literal['atac_bedgraph_rows_jsonl_v1']
    columns: list[str]
    row_count: int
    sha256: str
    byte_count: int
    order: str
    source_artifact_ref: str


class ParsedEnvelope(TypedDict):
    version: str
    artifact: AtacArtifact
    binding_key: str
    state: dict[str, str]
    parsed_sha256: str | None
    parsed_byte_count: int
    physical_line_count: int
    data_row_count: int | None
    readable_data_row_count: int
    malformed_data_row_count: int
    headers: list[HeaderRecord]
    rows: list | AtacRetainedTrackTable
    invalid_records: list[InvalidRecord]
    issues: list[AtacIssue]


class ParsedAtacTrack(ParsedEnvelope):
    binding: AtacTrackBinding
    coordinate_convention: str
    numeric_storage: str
    native_writer_precision: str
    row_order: str
    ordered_row_index: list[int] | None
    chromosome_extents: list[TrackChromosomeExtent]
    overlap_groups: list[list[int]]
    geometry_inspection: str
    unlocated_invalid_row_count: int


class AtacBamReferenceRow(TypedDict):
    row_ordinal: int
    locator: Locator
    chromosome: str | None
    length_bp: int | None
    sequence_md5: str | None
    original_fields: list[str]


class ParsedAtacBamReference(ParsedEnvelope):
    version: Literal['atac_bam_reference_parsed_v1']
    callpeak_run_key: str
    input_ordinal: int
    input_artifact_ref: str
    rows: list[AtacBamReferenceRow]


class ReportedNumber(TypedDict):
    value: Number | None
    lexeme: str | None
    state: str
    locations: list[Locator]


class Macs2ReportedMetadata(TypedDict):
    macs_version: str | None
    command_line: str | None
    name: str | None
    format: str | None
    treatment_paths: list[str] | None
    control_paths: list[str] | None
    control_presence: str
    paired_end: bool | None
    broad: bool | None
    scaling_direction: str
    local_lambda: str
    field_locations: dict[str, list[Locator]]


REPORTED_NUMBER_FIELDS = (
    'effective_genome_size_bp', 'band_width_bp', 'model_fold_lower', 'model_fold_upper',
    'qvalue_cutoff', 'pvalue_cutoff', 'large_local_window_bp', 'tag_size_bp',
    'fragment_size_bp', 'treatment_total_tags', 'treatment_postfilter_tags',
    'treatment_max_duplicates', 'treatment_redundant_rate', 'control_total_tags',
    'control_postfilter_tags', 'control_max_duplicates', 'control_redundant_rate',
    'treatment_total_fragments', 'treatment_postfilter_fragments',
    'control_total_fragments', 'control_postfilter_fragments', 'shift_bp', 'd_bp')
Macs2ReportedNumbers: TypeAlias = dict[str, ReportedNumber]
class PeakGeometry(TypedDict):
    row_ordinal: int
    start0: int | None
    end0: int | None
    summit0: int | None
    span_bp: int | None
    status: str


class PeakLink(TypedDict):
    callpeak_run_key: str
    name: str
    xls_row_ordinals: list[int]
    narrowpeak_row_ordinals: list[int]
    summit_row_ordinals: list[int]
    status: str


class ParsedMacs2PeaksXls(ParsedEnvelope):
    callpeak_run_key: str
    reported_metadata: Macs2ReportedMetadata
    reported_numbers: Macs2ReportedNumbers
    coordinate_convention: str
    peak_geometry: list[PeakGeometry]


class ParsedMacs2NarrowPeak(ParsedEnvelope):
    callpeak_run_key: str
    coordinate_convention: str
    score_basis: str


class ParsedMacs2Summits(ParsedMacs2NarrowPeak):
    pass


class ParsedMacs2Bdgdiff(ParsedEnvelope):
    comparison_key: str
    category: str
    coordinate_convention: str
    coordinate_qualification: str
    score_precision: str


class DepthCount(TypedDict):
    condition_id: str
    sample_ids: list[str]
    callpeak_run_key: str | None
    count: int | None
    count_lexeme: str | None
    count_unit: str
    count_population: str
    source_artifact_ref: str | None
    source_locations: list[Locator]
    source_field: str
    million_denominator: int
    state: str


class DeclaredDepth(TypedDict):
    condition_id: str
    sample_ids: list[str]
    value: Number | None
    value_lexeme: str | None
    unit: str
    population: str
    source_ref: str
    origin: str
    state: str


class AtacDepthCountSelection(TypedDict):
    kind: Literal['native_postfilter_counts']
    conditions: list[DepthCount]
    compatible_population: bool
    issues: list[AtacIssue]


class AtacDeclaredDepthSelection(TypedDict):
    kind: Literal['explicit_declared_depths']
    conditions: list[DeclaredDepth]
    compatible_population: bool
    issues: list[AtacIssue]


AtacBedGraphEvent: TypeAlias = dict
ParsedTrackEnvelopeWithoutRows: TypeAlias = dict
class AtacNativeSheet(TypedDict):
    version: Literal['atac_differential_native_sheet_v1']
    tool_row: Literal['B-L125-analyze_atac_seq_differential_accessibility']
    reference: AtacReference
    samples: list[AtacSample]
    conditions: list[AtacCondition]
    callpeak_bindings: list[AtacCallpeakBinding]
    comparison: AtacComparisonBinding
    tracks: list[ParsedAtacTrack]
    peaks_xls: list[ParsedMacs2PeaksXls]
    narrowpeaks: list[ParsedMacs2NarrowPeak]
    summits: list[ParsedMacs2Summits]
    peak_links: list[PeakLink]
    native_differential: list[ParsedMacs2Bdgdiff]
    bam_references: list[ParsedAtacBamReference]
    depth_selection: AtacDepthCountSelection | AtacDeclaredDepthSelection
    reference_relation: str
    normalization_compatibility: str
    coverage_completeness: str
    data_status: str
    issues: list[AtacIssue]


class AtacTableReadError(ValueError):
    """A failed supplied stream, after zero or more rows have been emitted."""

    def __init__(self, issue: AtacIssue, rows_read: int, bytes_read: int):
        super().__init__(issue['code'])
        self.issue = issue
        self.rows_read = rows_read
        self.bytes_read = bytes_read


def issue(code, artifact_ref, binding_key, *, row_ordinals=(), locations=(),
          field=None, requirement='none') -> AtacIssue:
    return dict(code=code, artifact_ref=artifact_ref, binding_key=binding_key,
                row_ordinals=list(row_ordinals), locations=[dict(x) for x in locations],
                field=field, requirement=requirement)


def _keys(value, fields, code):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(code)


def _str(value, code, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or not value:
        raise ValueError(code)
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError(code) from error


def _strings(value, code, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not list or any(type(x) is not str or not x for x in value):
        raise ValueError(code)


def _int(value, code, minimum=0, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not int or minimum is not None and value < minimum:
        raise ValueError(code)


def _number(value, code, nullable=False):
    if nullable and value is None:
        return
    if type(value) not in (int, float) or type(value) is float and not math.isfinite(value):
        raise ValueError(code)


def _bool(value, code, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not bool:
        raise ValueError(code)


def _enum(value, allowed, code):
    if type(value) is not str or value not in allowed:
        raise ValueError(code)


def _sha(value, code, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError(code)


def validate_atac_artifact(value, *, missing=False):
    code = 'invalid_atac_artifact'
    _keys(value, AtacArtifact.__annotations__, code)
    _str(value['artifact_ref'], code, missing)
    _str(value['format'], code)
    for key in ('producer_run_ref', 'producer_name', 'producer_version', 'producer_source_ref'):
        _str(value[key], code, True)
    _sha(value['expected_sha256'], code, True)
    _int(value['expected_size_bytes'], code, nullable=True)
    _enum(value['supplied_extent'], ('complete', 'partial', 'unknown'), code)
    _enum(value['producer_outcome'], ('succeeded', 'failed', 'not_run', 'unknown'), code)
    _bool(value['writer_closed'], code, True)
    _enum(value['origin'], ('supplied_measurement', 'synthetic_engineering_fixture', 'unknown'), code)


def validate_atac_track_binding(value, *, missing=False):
    code = 'invalid_atac_track_binding'
    _keys(value, AtacTrackBinding.__annotations__, code)
    for key in ('track_key', 'condition_id', 'reference_id'):
        _str(value[key], code)
    _str(value['source_artifact_ref'], code, missing)
    _strings(value['sample_ids'], code)
    _str(value['callpeak_run_key'], code, True)
    _enum(value['role'], ('signal', 'model_background'), code)
    if value['value_unit'] is not None or not missing:
        _enum(value['value_unit'], ('extended_tag_pileup', 'model_expected_extended_tag_pileup',
                                   'supplied_signal', 'supplied_model_background'), code)
    _enum(value['normalization'], ('raw_pileup', 'spmr', 'unknown'), code)
    _enum(value['background_origin'], ('self_model', 'supplied_control_model',
                                      'explicit_supplied_track', 'unknown'), code)


def validate_atac_callpeak_binding(value):
    code = 'invalid_atac_callpeak_binding'
    _keys(value, AtacCallpeakBinding.__annotations__, code)
    for key in ('run_key', 'condition_id', 'reference_id', 'selected_format', 'producer_ref'):
        _str(value[key], code)
    for key in ('sample_ids', 'treatment_input_refs', 'selected_argv'):
        _strings(value[key], code)
    for key in ('supplied_control_sample_ids', 'supplied_control_input_refs'):
        _strings(value[key], code, True)
    _bool(value['paired_end'], code, True)
    p = value['selected_parameters']
    _keys(p, CallpeakParameters.__annotations__, code)
    _str(p['genome_size_argument'], code, True)
    for key in ('nomodel', 'store_bedgraph', 'spmr', 'broad', 'downsample'):
        _bool(p[key], code, True)
    for key in ('effective_genome_size_bp', 'qvalue_cutoff', 'pvalue_cutoff'):
        _number(p[key], code, True)
    for key in ('extension_size_bp', 'small_local_window_bp', 'large_local_window_bp'):
        _int(p[key], code, nullable=True)
    _int(p['shift_bp'], code, minimum=None, nullable=True)
    if p['keep_duplicates'] not in ('all', 'auto', None):
        _int(p['keep_duplicates'], code)
    _keys(value['artifact_roles'], CallpeakArtifactRoles.__annotations__, code)
    for ref in value['artifact_roles'].values():
        _str(ref, code, True)


def validate_atac_comparison_binding(value):
    code = 'invalid_atac_comparison_binding'
    _keys(value, AtacComparisonBinding.__annotations__, code)
    for key in ('comparison_key', 'condition1_id', 'condition2_id', 'reference_id'):
        _str(value[key], code)
    _str(value['producer_ref'], code, True)
    _strings(value['selected_argv'], code)
    _keys(value['track_keys'], ('signal1', 'background1', 'signal2', 'background2'), code)
    for ref in value['track_keys'].values():
        _str(ref, code)
    _keys(value['artifact_roles'], ('condition1', 'condition2', 'common'), code)
    for ref in value['artifact_roles'].values():
        _str(ref, code, True)
    p = value['selected_parameters']
    _keys(p, BdgdiffParameters.__annotations__, code)
    for key in ('depth1_lexeme', 'depth2_lexeme'):
        _str(p[key], code, True)
    _enum(p['depth_unit'], ('tags', 'fragments', 'million_tags', 'million_fragments', 'unknown'), code)
    for key in ('cutoff_log10_lr', 'native_pseudocount'):
        _number(p[key], code, True)
    for key in ('minimum_length_bp', 'maximum_gap_bp'):
        _int(p[key], code, nullable=True)


def validate_atac_reference(value):
    code = 'invalid_atac_reference'
    _keys(value, AtacReference.__annotations__, code)
    _str(value['reference_id'], code)
    _str(value['assembly_accession_version'], code, True)
    _strings(value['source_refs'], code)
    if type(value['contigs']) is not list or type(value['aliases']) is not list:
        raise ValueError(code)
    for contig in value['contigs']:
        _keys(contig, AtacContig.__annotations__, code)
        _str(contig['chromosome'], code)
        _int(contig['length_bp'], code, nullable=True)
        _str(contig['sequence_accession_version'], code, True)
        _sha(contig['sequence_sha256'], code, True)
        _strings(contig['source_refs'], code)
    for alias in value['aliases']:
        _keys(alias, AtacChromosomeAlias.__annotations__, code)
        for key in ('source_chromosome', 'target_chromosome', 'reference_id'):
            _str(alias[key], code)
        _strings(alias['source_refs'], code)


def validate_atac_sample(value):
    code = 'invalid_atac_sample'
    _keys(value, AtacSample.__annotations__, code)
    for key in ('sample_id', 'reference_id'):
        _str(value[key], code)
    for key in ('biospecimen_id', 'replicate_id'):
        _str(value[key], code, True)
    _strings(value['input_artifact_refs'], code)
    _enum(value['origin'], ('supplied_measurement', 'synthetic_engineering_fixture', 'unknown'), code)


def validate_atac_condition(value):
    code = 'invalid_atac_condition'
    _keys(value, AtacCondition.__annotations__, code)
    _str(value['condition_id'], code)
    _str(value['label'], code, True)
    _strings(value['sample_ids'], code)


def valid_track_geometry(row):
    return (type(row[5]) is int and type(row[6]) is int
            and 0 <= row[5] < row[6] <= MAX_COORDINATE)


def track_row_key(row):
    return row[4].encode('utf-8'), row[5], row[6], row[0]


def validate_bedgraph_row(row):
    code = 'invalid_atac_track_table_row'
    if not isinstance(row, (list, tuple)) or len(row) != 9:
        raise ValueError(code)
    for index in range(4):
        _int(row[index], code, minimum=1 if index == 1 else 0)
    if row[3] <= row[2]:
        raise ValueError(code)
    _str(row[4], code)
    for index in (5, 6):
        _int(row[index], code, minimum=None, nullable=True)
    _number(row[7], code, True)
    _str(row[8], code, True)


def validate_atac_retained_track_table(value):
    code = 'invalid_atac_retained_track_table'
    _keys(value, AtacRetainedTrackTable.__annotations__, code)
    if value['storage'] != 'retained_table' or value['format'] != 'atac_bedgraph_rows_jsonl_v1':
        raise ValueError(code)
    if value['columns'] != list(BEDGRAPH_COLUMNS):
        raise ValueError(code)
    _enum(value['order'], ('native_file_order', 'chromosome_start_end_source_ordinal'), code)
    for key in ('artifact_ref', 'source_artifact_ref'):
        _str(value[key], code)
    for key in ('row_count', 'byte_count'):
        _int(value[key], code)
    _sha(value['sha256'], code)


def validate_atac_depth_selection(value):
    code = 'invalid_atac_depth_selection'
    _keys(value, ('kind', 'conditions', 'compatible_population', 'issues'), code)
    _enum(value['kind'], ('native_postfilter_counts', 'explicit_declared_depths'), code)
    _bool(value['compatible_population'], code)
    if type(value['conditions']) is not list or len(value['conditions']) != 2 or type(value['issues']) is not list:
        raise ValueError(code)
    for row in value['conditions']:
        native = value['kind'] == 'native_postfilter_counts'
        _keys(row, DepthCount.__annotations__ if native else DeclaredDepth.__annotations__, code)
        _str(row['condition_id'], code)
        _strings(row['sample_ids'], code)
        if native:
            _str(row['callpeak_run_key'], code, row['state'] in ('missing', 'conflicting'))
            _int(row['count'], code, nullable=True)
            _str(row['count_lexeme'], code, True)
            _str(row['source_artifact_ref'], code, True)
            if (row['count_unit'] != 'postfilter_single_end_tags'
                    or row['count_population'] != 'macs2_loaded_treatment_tags_after_duplicate_filtering'
                    or row['source_field'] != 'treatment_postfilter_tags'
                    or type(row['million_denominator']) is not int or row['million_denominator'] != 1000000):
                raise ValueError(code)
            _enum(row['state'], ('observed', 'missing', 'conflicting', 'incompatible_mode', 'zero'), code)
            if (row['state'] == 'observed' and (row['count'] is None or row['count'] <= 0)
                    or row['state'] == 'zero' and row['count'] != 0):
                raise ValueError(code)
            if row['callpeak_run_key'] is None and (row['count'] is not None or row['source_artifact_ref'] is not None):
                raise ValueError(code)
        else:
            _number(row['value'], code, True)
            _str(row['value_lexeme'], code, True)
            _str(row['source_ref'], code)
            _str(row['population'], code)
            if re.fullmatch(r'[A-Za-z0-9_.:-]+', row['population']) is None:
                raise ValueError(code)
            _enum(row['unit'], ('tags', 'fragments', 'million_tags', 'million_fragments'), code)
            _enum(row['origin'], ('synthetic_engineering_fixture', 'explicit_supplied_metadata'), code)
            _enum(row['state'], ('declared', 'missing', 'invalid'), code)
            if row['state'] == 'declared' and (row['value'] is None or row['value'] <= 0):
                raise ValueError(code)


def atac_track_extent(track):
    """The narrower extent vocabulary consumed by the interval calculator."""
    if track['state']['availability'] == 'missing':
        return 'missing'
    if track['artifact']['producer_outcome'] == 'failed':
        return 'failed'
    if track['state']['output_extent'] == 'complete' and track['state']['identity'] == 'verified':
        return 'complete'
    return 'partial'


def validate_atac_locator(value):
    code = 'invalid_atac_locator'
    _keys(value, Locator.__annotations__, code)
    _int(value['line_number'], code, 1)
    _int(value['byte_start'], code)
    _int(value['byte_end'], code)
    if value['byte_end'] <= value['byte_start']:
        raise ValueError(code)


def validate_atac_bam_reference_row(value):
    code = 'invalid_atac_bam_reference_row'
    _keys(value, AtacBamReferenceRow.__annotations__, code)
    _int(value['row_ordinal'], code)
    validate_atac_locator(value['locator'])
    _str(value['chromosome'], code, True)
    # A negative native LN stays a retained integer with a source issue.
    _int(value['length_bp'], code, minimum=None, nullable=True)
    if value['sequence_md5'] is not None and (type(value['sequence_md5']) is not str
            or re.fullmatch('[0-9a-fA-F]{32}', value['sequence_md5']) is None):
        raise ValueError(code)
    fields = value['original_fields']
    if (type(fields) is not list or not fields or fields[0] != '@SQ'
            or any(type(field) is not str for field in fields)):
        raise ValueError(code)


def validate_atac_parsed_table(value, *, version=None):
    """Validate a supplied reader record without copying its numerical table.

    Relationship conflicts in actual native data remain issues. Impossible
    counters/types and unsatisfied stream seals are programming input errors.
    A retained table's bytes are verified by its separate exhausted reader.
    """
    code = 'invalid_atac_parsed_table'
    versions = {'atac_bedgraph_parsed_v1': ParsedAtacTrack,
                'macs2_peaks_xls_parsed_v1': ParsedMacs2PeaksXls,
                'macs2_narrowpeak_parsed_v1': ParsedMacs2NarrowPeak,
                'macs2_summits_parsed_v1': ParsedMacs2Summits,
                'macs2_bdgdiff_parsed_v1': ParsedMacs2Bdgdiff,
                'atac_bam_reference_parsed_v1': ParsedAtacBamReference}
    if not isinstance(value, dict) or value.get('version') not in versions or version is not None and value.get('version') != version:
        raise ValueError(code)
    _keys(value, versions[value['version']].__annotations__, code)
    state = value['state']
    _keys(state, ('availability', 'byte_extent', 'identity', 'format', 'output_extent'), code)
    _enum(state['availability'], ('present', 'missing'), code)
    for field in ('byte_extent', 'output_extent'):
        _enum(state[field], ('complete', 'partial', 'unknown'), code)
    _enum(state['identity'], ('verified', 'unverified', 'mismatch'), code)
    _enum(state['format'], ('compatible', 'malformed', 'unsupported'), code)
    validate_atac_artifact(value['artifact'], missing=state['availability'] == 'missing')
    _str(value['binding_key'], code)
    _sha(value['parsed_sha256'], code, True)
    for field in ('parsed_byte_count', 'physical_line_count', 'readable_data_row_count', 'malformed_data_row_count'):
        _int(value[field], code)
    _int(value['data_row_count'], code, nullable=True)
    for field in ('headers', 'invalid_records', 'issues'):
        if type(value[field]) is not list:
            raise ValueError(code)
    for header in value['headers']:
        _keys(header, HeaderRecord.__annotations__, code)
        validate_atac_locator(header['locator'])
        kinds = ('comment', 'track', 'browser', 'blank', 'column_header')
        if value['version'] == 'atac_bam_reference_parsed_v1':
            kinds += ('sam_header',)
        _enum(header['kind'], kinds, code)
        if header['text'] is not None and type(header['text']) is not str:
            raise ValueError(code)
    invalid_ordinals = []
    for row in value['invalid_records']:
        _keys(row, InvalidRecord.__annotations__, code)
        _int(row['row_ordinal'], code)
        validate_atac_locator(row['locator'])
        if row['fields'] is not None and (type(row['fields']) is not list or any(type(v) is not str for v in row['fields'])):
            raise ValueError(code)
        _strings(row['reason_codes'], code)
        invalid_ordinals.append(row['row_ordinal'])
    if isinstance(value['rows'], dict):
        if value['version'] != 'atac_bedgraph_parsed_v1':
            raise ValueError(code)
        validate_atac_retained_track_table(value['rows'])
        readable = value['rows']['row_count']
        ordinals = []
    elif type(value['rows']) is list:
        readable = len(value['rows'])
        ordinals = []
        for row in value['rows']:
            if value['version'] == 'atac_bedgraph_parsed_v1':
                validate_bedgraph_row(row)
                ordinals.append(row[0])
            elif value['version'] == 'atac_bam_reference_parsed_v1':
                validate_atac_bam_reference_row(row)
                ordinals.append(row['row_ordinal'])
            else:
                if not isinstance(row, dict):
                    raise ValueError(code)
                _int(row.get('row_ordinal'), code)
                validate_atac_locator(row.get('locator'))
                ordinals.append(row['row_ordinal'])
                fields = row.get('original_fields')
                if type(fields) is not list or any(type(v) is not str for v in fields):
                    raise ValueError(code)
                for field, number in row.items():
                    if field not in ('row_ordinal', 'locator', 'original_fields', 'chromosome', 'name', 'strand'):
                        _number(number, code, True)
    else:
        raise ValueError(code)
    if readable != value['readable_data_row_count'] or len(set(ordinals + invalid_ordinals)) != len(ordinals + invalid_ordinals):
        raise ValueError(code)
    inspected = readable + len(invalid_ordinals)
    if value['malformed_data_row_count'] > inspected or value['data_row_count'] is not None and value['data_row_count'] != inspected:
        raise ValueError(code)
    artifact = value['artifact']
    if state['identity'] == 'verified' and (value['parsed_sha256'] != artifact['expected_sha256']
            or value['parsed_byte_count'] != artifact['expected_size_bytes'] or value['parsed_sha256'] is None):
        raise ValueError(code)
    if state['output_extent'] == 'complete' and (state['availability'] != 'present'
            or state['byte_extent'] != 'complete' or state['identity'] != 'verified' or state['format'] != 'compatible'
            or value['version'] != 'atac_bedgraph_parsed_v1' and artifact['producer_run_ref'] is None
            or artifact['producer_run_ref'] is not None and (artifact['producer_outcome'] != 'succeeded' or artifact['writer_closed'] is not True)):
        raise ValueError(code)
    if value['version'] == 'atac_bedgraph_parsed_v1':
        validate_atac_track_binding(value['binding'], missing=state['availability'] == 'missing')
        _int(value['unlocated_invalid_row_count'], code)
        if value['unlocated_invalid_row_count'] > inspected:
            raise ValueError(code)
        _enum(value['geometry_inspection'], ('complete', 'partial', 'unknown'), code)
    elif value['version'] == 'atac_bam_reference_parsed_v1':
        _str(value['callpeak_run_key'], code)
        _int(value['input_ordinal'], code)
        _str(value['input_artifact_ref'], code)
        if value['binding_key'] != value['callpeak_run_key'] + ':input:' + str(value['input_ordinal']):
            raise ValueError(code)
    elif value['version'] == 'macs2_peaks_xls_parsed_v1':
        _keys(value['reported_metadata'], Macs2ReportedMetadata.__annotations__, code)
        _keys(value['reported_numbers'], REPORTED_NUMBER_FIELDS, code)
        for number in value['reported_numbers'].values():
            _keys(number, ReportedNumber.__annotations__, code)
            _number(number['value'], code, True)
            _str(number['lexeme'], code, True)
            _enum(number['state'], ('present', 'missing', 'invalid', 'conflicting', 'not_measured'), code)
            for locator in number['locations']:
                validate_atac_locator(locator)
    elif value['version'] == 'macs2_bdgdiff_parsed_v1':
        _enum(value['category'], ('condition1', 'condition2', 'common'), code)
