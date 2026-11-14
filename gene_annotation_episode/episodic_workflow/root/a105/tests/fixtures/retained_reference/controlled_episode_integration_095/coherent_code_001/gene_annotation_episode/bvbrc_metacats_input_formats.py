"""Read supplied original MetaCATS FASTA, preserving literal hash symbols.

An original '#' is a distinct missing-symbol input, not proof that a terminal
dash was masked by the native program. This reader performs no preprocessing,
metadata join, acquisition or scientific calculation. Its output uses the
existing saved AlignmentDocument contract.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from .phylogeny_formats import _Text
from .phylogeny_format_contracts import _artifact, validate_alignment_document


def _diagnostic(code, path='', *, severity='error', artifact=None,
                phase='native_decode'):
    return {'code': 'bvbrc_metacats_input_' + code, 'phase': phase,
        'path': path, 'severity': severity,
        'evidence_refs': [artifact['raw_artifact_ref']] if artifact is not None else []}


def _result(value, diagnostics, *, usable=False):
    errors = any(item['severity'] == 'error' for item in diagnostics)
    return {'status': ('partial' if usable else 'invalid') if errors else 'ok',
            'value': value, 'diagnostics': diagnostics}


def parse_metacats_input_fasta(data: bytes, *, artifact: dict,
                               id_rule: str = 'first_whitespace_token',
                               encoding: str = 'ascii') -> dict:
    """Preserve all original rows and symbols, including '#', with locations.

    No complete transport, alphabet, grouping or original coordinate map is
    inferred. Empty sequences remain empty and unequal rows remain unequal.
    Formatting spaces/tabs are qualified; other invalid characters are kept
    in partial rows so later code cannot silently treat them as removed bases.
    """
    try:
        _artifact(artifact)
    except ValueError:
        return _result(None, [_diagnostic('artifact_invalid', '/artifact', phase='association')])
    if type(data) is not bytes:
        return _result(None, [_diagnostic('bytes_required', artifact=artifact)])
    if hashlib.sha256(data).hexdigest() != artifact['sha256']:
        return _result(None, [_diagnostic('artifact_sha256_mismatch', '/artifact/sha256',
            phase='association', artifact=artifact)])
    if id_rule != 'first_whitespace_token' or encoding not in ('ascii', 'utf-8'):
        return _result(None, [_diagnostic('reader_parameter_invalid', artifact=artifact)])
    try:
        source = _Text(data, artifact, encoding)
    except UnicodeError:
        return _result(None, [_diagnostic('encoding_invalid', artifact=artifact)])
    value = {'alignment_id': artifact['raw_artifact_ref'] + '#alignment',
        'artifact': deepcopy(artifact), 'format': 'aligned_fasta', 'layout': 'fasta',
        'id_rule': id_rule, 'encoding': encoding, 'declared_row_count': None,
        'declared_column_count': None, 'observed_row_count': 0,
        'observed_column_count': None, 'completeness': 'unknown', 'rows': []}
    rows, diagnostics = value['rows'], []
    current, row_start, row_end = None, 0, 0
    for line, start, end in source.lines():
        if line.startswith('>'):
            if current is not None:
                current['source_location'] = source.loc(row_start, row_end)
            header = line[1:]
            tokens = header.split()
            current = {'row_index': len(rows), 'raw_header': header,
                'member_label': tokens[0] if tokens else '', 'sequence': '',
                'source_location': source.loc(start, end)}
            rows.append(current)
            row_start, row_end = start, end
            if not tokens:
                diagnostics.append(_diagnostic('alignment_label_missing',
                    f'/rows/{len(rows)-1}/member_label', artifact=artifact))
        elif line.strip():
            if current is None:
                diagnostics.append(_diagnostic('fasta_header_missing', '/rows', artifact=artifact))
                continue
            path = f'/rows/{len(rows)-1}/sequence'
            if any(char in ' \t' for char in line):
                diagnostics.append(_diagnostic('alignment_whitespace_ignored', path,
                    severity='qualification', artifact=artifact))
            sequence = line.replace(' ', '').replace('\t', '')
            if re.fullmatch(r'[A-Za-z*.?\-#]*', sequence) is None:
                diagnostics.append(_diagnostic('alignment_symbol_invalid', path, artifact=artifact))
            current['sequence'] += sequence
            row_end = end
    if current is not None:
        current['source_location'] = source.loc(row_start, row_end)
    value['observed_row_count'] = len(rows)
    lengths = {len(row['sequence']) for row in rows}
    if len(lengths) > 1:
        diagnostics.append(_diagnostic('alignment_lengths_unequal', '/rows', artifact=artifact))
    if not rows:
        diagnostics.append(_diagnostic('empty_input', '/rows', artifact=artifact))
    errors = any(item['severity'] == 'error' for item in diagnostics)
    value['completeness'] = 'partial' if errors else 'complete'
    value['observed_column_count'] = next(iter(lengths)) if len(lengths) == 1 and not errors else None
    validate_alignment_document(value)
    return _result(value, diagnostics, usable=bool(rows))


__all__ = ['parse_metacats_input_fasta']
