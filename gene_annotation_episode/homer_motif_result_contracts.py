"""Finite typed facts for the unchanged shared HOMER public projection.

The source-free packet shape removes only the two outer identity fields. It
does not project, interpret or recalculate scientific values.
"""
from copy import deepcopy
import hashlib

from jsonschema.exceptions import ValidationError

from . import homer_motif_contracts as core


TOOL = core.OPERATION
FACT_SOURCE = 'homer_motif_outcomes'
SOURCE_VERSION = 'ordinary_homer_motif_result_v1'
CAPTURE_VERSION = 'ordinary_homer_motif_native_capture_v1'
PACKET_VERSION = 'ordinary_homer_motif_public_packet_v1'


def _schema(kind):
    schema = core.homer_record_schema('Return')
    if kind == 'Value':
        record = schema['$defs']['Return']
        for name in ('version', 'source_ref'):
            del record['properties'][name]
            record['required'].remove(name)
    elif kind != 'Return':
        raise ValueError('homer_motif_schema_kind_invalid')
    return schema


def validate_homer_motif_return(value):
    """Validate the exact public DTO; producer and receipt proof stay separate."""
    try:
        return core.validated('Return', value)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        raise ValueError('homer_motif_return_invalid') from error


def validate_homer_motif_value(value):
    """Check a source-free packet without fabricating a Source for validation.

    Its values must already come from project_homer_return. Once the actual
    Source exists, homer_motif_return applies the full authoritative validator.
    """
    try:
        core.canonical(value)
        core._STRICT(_schema('Value')).validate(value)
    except (ValidationError, ValueError, TypeError, KeyError, OverflowError) as error:
        raise ValueError('homer_motif_value_invalid') from error
    return deepcopy(value)


def homer_motif_return(value, *, source_ref):
    return validate_homer_motif_return(dict(version=core.RETURN_VERSION,
        source_ref=source_ref, **validate_homer_motif_value(value)))


def homer_motif_fact_sources():
    schema = core.homer_record_schema('Return')
    report = {'$schema': schema['$schema'], '$defs': schema['$defs'],
        'type': 'array', 'items': {'$ref': schema['$ref']}, 'x-source': FACT_SOURCE}
    report['$id'] = 'urn:gene-annotation:homer-motif-return:' + hashlib.sha256(core.canonical(report)).hexdigest()
    return {FACT_SOURCE: dict(type='array', meaning=(
        'Retained final native HOMER motif measurements and reported-input-weight sums, '
        'preserving supplied series selection, native occurrence order, precision, '
        'populations, geometry and qualifications.'), report_schema=report)}


__all__ = ['TOOL', 'FACT_SOURCE', 'SOURCE_VERSION', 'CAPTURE_VERSION', 'PACKET_VERSION',
    'validate_homer_motif_return', 'validate_homer_motif_value', 'homer_motif_return',
    'homer_motif_fact_sources']
