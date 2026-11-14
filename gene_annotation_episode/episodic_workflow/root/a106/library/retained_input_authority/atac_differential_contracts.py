"""Ordinary data records for retained ATAC/MACS2 measurements.

These records contain native numbers, explicit associations and source locations.
They do not define executable scoring rules, acquire data, or assign credit.
Scientific incompatibilities are issues; impossible Python input shapes are errors.
"""
from __future__ import annotations
import re
from typing import Literal, TypeAlias, TypedDict
Origin: TypeAlias = Literal['supplied_measurement', 'synthetic_engineering_fixture', 'unknown']
BEDGRAPH_COLUMNS = ('row_ordinal', 'line_number', 'byte_start', 'byte_end', 'chromosome', 'start', 'end', 'value_numeric', 'value_lexeme')

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
    if type(value) is not list or any((type(x) is not str or not x for x in value)):
        raise ValueError(code)

def _int(value, code, minimum=0, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(code)

def _enum(value, allowed, code):
    if type(value) is not str or value not in allowed:
        raise ValueError(code)

def _sha(value, code, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError(code)

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
