"""Pure loss-preserving reader for explicitly declared Mauve1 DNA XMFA bytes.

Every defline creates a row; only '=' closes a block. Input source identity and
coverage are outside this reader. It neither repairs rows nor invents an EOF
terminator, gap padding, a source sequence, or a native alignment score.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Literal

from .bvbrc_alignment_values import diagnostic, document_id
from .xmfa_format_contracts import (
    DNA_SYMBOLS, _artifact, _block_facts, _document_completeness,
    _header_fields, _metadata_facts, _metadata_fields, _parameters,
    _record_facts, _require, validate_xmfa_document,
)


NATIVE_DIAGNOSTIC_CODES = frozenset({
    'digest_mismatch', 'encoding_invalid', 'empty_input', 'document_unrecognized',
    'version_missing', 'version_unsupported', 'header_malformed', 'member_invalid',
    'coordinate_invalid', 'strand_invalid', 'sequence_symbol_invalid',
    'sequence_before_header', 'span_mismatch', 'row_width_conflict',
    'zero_record_has_residues', 'all_zero_block', 'missing_block_terminator',
    'unparsed_line', 'duplicate_member_record', 'metadata_duplicate',
    'metadata_conflict', 'metadata_integer_invalid',
})


def parse_mauve_xmfa(data: bytes, *, artifact: dict,
    dialect: Literal['mauve1'], alphabet: Literal['dna'],
    encoding: Literal['ascii', 'utf-8']) -> dict:
    """Retain all readable native rows with finite diagnostics for malformed data.

    Bad explicit arguments raise xmfa_ ValueErrors. Unusable digest/encoding or
    an unrecognizable document gives invalid/null; local native malformations
    retain their exact text and any independently readable measurements.
    The function has no I/O, resource choice, native execution or model calls.
    """
    _parameters(dialect, alphabet, encoding)
    _require(type(data) is bytes, 'bytes_required')
    _artifact(artifact)
    artifact = deepcopy(artifact)
    diagnostics = []

    def issue(code, path='', severity='qualification'):
        diagnostics.append(diagnostic('xmfa_' + code, phase='native_decode', path=path,
            severity=severity, evidence_refs=(artifact['raw_artifact_ref'],)))

    def invalid(code):
        issue(code, severity='error')
        return {'status': 'invalid', 'value': None, 'diagnostics': diagnostics}

    if hashlib.sha256(data).hexdigest() != artifact['sha256']:
        return invalid('digest_mismatch')
    try:
        decoded = data.decode(encoding)
    except UnicodeError:
        return invalid('encoding_invalid')
    if not decoded.strip():
        return invalid('empty_input')
    value = {'schema_version': 'mauve_xmfa_document_v1',
        'document_id': document_id('mauve_xmfa', artifact=artifact,
            parameters={'dialect': dialect, 'alphabet': alphabet, 'encoding': encoding}),
        'artifact': artifact, 'dialect': dialect, 'alphabet': alphabet, 'encoding': encoding,
        'format_version_token': None, 'completeness': 'unknown',
        'metadata': [], 'blocks': [], 'unparsed': []}
    block, row = None, None

    def location(start, end, line):
        return {'artifact': deepcopy(artifact), 'byte_start_0based': start,
            'byte_end_0based_exclusive': end, 'line_start_1based': line,
            'line_end_1based_inclusive': line, 'xml_path': None}

    def extend(outer, inner):
        outer['byte_end_0based_exclusive'] = inner['byte_end_0based_exclusive']
        outer['line_end_1based_inclusive'] = inner['line_end_1based_inclusive']

    # Split bytes on actual CR/LF endings. Unicode characters such as U+2028
    # are retained text, not mistaken for native line boundaries.
    lines = re.finditer(rb'[^\r\n]*(?:\r\n|\r|\n|$)', data)
    for line_number, match in enumerate(lines, 1):
        if match.start() == len(data):
            break
        raw_bytes = match.group().rstrip(b'\r\n')
        raw = raw_bytes.decode(encoding)
        loc = location(match.start(), match.start() + len(raw_bytes), line_number)
        if block is not None:
            extend(block['source_location'], loc)
        if raw.startswith('#'):
            value['metadata'].append({'metadata_index': len(value['metadata']), 'raw_line': raw,
                **_metadata_fields(raw, loc, encoding), 'source_location': loc})
        elif raw.startswith('>'):
            if block is None:
                block = {'block_index': len(value['blocks']), 'source_location': deepcopy(loc),
                    'terminated': False, 'terminator_token': None, 'terminator_location': None,
                    'records': [], 'alignment_column_count': None, 'completeness': 'unknown'}
                value['blocks'].append(block)
            row = {'record_index': len(block['records']), 'header_token': raw,
                'header_location': deepcopy(loc), **_header_fields(raw, loc, encoding),
                'sequence': '', 'sequence_parts': [], 'source_location': deepcopy(loc)}
            block['records'].append(row)
        elif raw.startswith('=') and block is not None:
            block.update(terminated=True, terminator_token=raw, terminator_location=loc)
            block, row = None, None
        elif row is not None:
            row['sequence_parts'].append({'text': raw, 'source_location': loc})
            extend(row['source_location'], loc)
        elif raw:
            index = len(value['unparsed'])
            value['unparsed'].append({'raw_line': raw, 'source_location': loc,
                                      'block_index': None, 'record_index': None})
            issue('sequence_before_header' if all(s in DNA_SYMBOLS for s in raw) else 'unparsed_line',
                  '/unparsed/' + str(index))
    if not value['blocks'] and not any(m['kind'] == 'format_version' for m in value['metadata']):
        return invalid('document_unrecognized')
    version, metadata_issues = _metadata_facts(value['metadata'])
    value['format_version_token'] = version
    for code, index in metadata_issues:
        issue(code, '/metadata' + ('' if index is None else '/' + str(index)))
    for block in value['blocks']:
        path = '/blocks/' + str(block['block_index'])
        for row in block['records']:
            row['sequence'] = ''.join(part['text'] for part in row['sequence_parts'])
            facts, codes = _record_facts(row, supported=version == 'Mauve1')
            row.update(facts)
            for code in codes:
                issue(code, path + '/records/' + str(row['record_index']))
        width, completeness, codes = _block_facts(block, supported=version == 'Mauve1')
        block.update(alignment_column_count=width, completeness=completeness)
        for code in codes:
            issue(code, path)
    value['completeness'] = _document_completeness(value, metadata_issues)
    # Saved-object checks run on the same full retained representation. They
    # never reopen bytes or invoke this parser during later recalculation.
    validate_xmfa_document(value)
    return {'status': 'partial' if diagnostics else 'ok', 'value': value,
            'diagnostics': diagnostics}


__all__ = ['parse_mauve_xmfa']
