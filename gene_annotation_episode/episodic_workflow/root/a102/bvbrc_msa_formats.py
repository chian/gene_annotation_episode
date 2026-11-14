"""Parse supplied native BV-BRC MSA frequency bytes without any I/O.

The table's original bytes remain the caller's retained artifact. Literal
numeric tokens, protein detail fragments and byte ranges survive decoding.
No reference identity, missing base count or producer version is inferred.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Literal

from .bvbrc_alignment_values import diagnostic, document_id, native_number
from .bvbrc_msa_format_contracts import (
    PROTEIN_SYMBOLS, _require, frequency_header, validate_msa_frequency_table,
)
from .phylogeny_format_contracts import _artifact


def parse_msa_frequency_table(data: bytes, *, artifact: dict,
    alphabet: Literal['dna', 'protein'],
    layout: Literal['current_without_reference', 'current_with_reference'],
    encoding: Literal['ascii', 'utf-8']) -> dict:
    """Read one explicitly declared native header and preserve usable rows.

    Structural data failures return invalid/null or partial with retained rows.
    Incorrect caller argument types/layouts raise ValueError. A final missing
    newline is valid; a short row is explicit truncation evidence. Blank native
    DNA cells remain missing, including producer omissions for absent bases.
    """
    expected_header = frequency_header(alphabet, layout)
    _require(encoding in ('ascii', 'utf-8'), 'encoding_invalid')
    _require(type(data) is bytes, 'bytes_required')
    _artifact(artifact)
    artifact = deepcopy(artifact)
    diagnostics = []
    def issue(code, path='', severity='qualification'):
        diagnostics.append(diagnostic('bvbrc_msa_' + code, phase='native_decode',
            path=path, severity=severity, evidence_refs=(artifact['raw_artifact_ref'],)))
    def invalid(code):
        issue(code, severity='error')
        return {'status': 'invalid', 'value': None, 'diagnostics': diagnostics}
    if hashlib.sha256(data).hexdigest() != artifact['sha256']:
        return invalid('artifact_digest_conflict')
    try:
        data.decode(encoding)
    except UnicodeError:
        return invalid('encoding_conflict')
    lines = list(re.finditer(rb'[^\r\n]*(?:\r\n|\r|\n|$)', data))
    lines = [match for match in lines if match.start() < len(data)]
    if not lines:
        return invalid('native_header_conflict')
    header = lines[0].group().rstrip(b'\r\n').decode(encoding).split('\t')
    if header != expected_header:
        return invalid('native_header_conflict')
    value = {'table_id': document_id('msa_frequency_table', artifact=artifact,
        parameters={'alphabet': alphabet, 'layout': layout, 'encoding': encoding}),
        'artifact': artifact, 'alphabet': alphabet, 'layout': layout, 'encoding': encoding,
        'header_tokens': header, 'completeness': 'complete', 'rows': []}
    def location(start, end, line):
        return {'artifact': deepcopy(artifact), 'byte_start_0based': start,
            'byte_end_0based_exclusive': end, 'line_start_1based': line,
            'line_end_1based_inclusive': line, 'xml_path': None}
    seen_positions = set()
    truncated = False
    for row_index, match in enumerate(lines[1:]):
        raw = match.group().rstrip(b'\r\n')
        tokens = raw.split(b'\t')
        path = '/rows/' + str(row_index)
        if len(tokens) != len(header):
            truncated |= len(tokens) < len(header)
            issue('ragged_native_row', path, severity='error')
            continue
        starts, cursor = [], match.start()
        for token in tokens:
            starts.append(cursor)
            cursor += len(token) + 1
        texts = [token.decode(encoding) for token in tokens]
        fields = dict(zip(header, range(len(header))))
        def number(field, *, integer=False, minimum=None):
            index = fields[field]
            result = native_number(texts[index], integer=integer, minimum=minimum,
                source_location=location(starts[index], starts[index] + len(tokens[index]), row_index + 2))
            if result['state'] != 'available':
                if field != 'Position in Reference' or texts[fields['Reference Character']] != '-':
                    issue('malformed_native_number' if result['state'] in ('failed', 'incompatible')
                          else 'native_number_unavailable', path + '/' + field)
            return result
        row = {'row_index': row_index, 'source_location': location(match.start(), match.end(), row_index + 2),
            'alignment_position': number('Position in Alignment', integer=True, minimum=1),
            'reference_position': None, 'reference_character': None,
            'score': number('Score', minimum=0), 'consensus_token': texts[fields['Consensus']],
            'n_sequences': number('Number of Sequences', integer=True, minimum=0),
            'dna_counts': None, 'protein_detail': None}
        position = row['alignment_position']
        if position['state'] == 'available':
            if position['value'] in seen_positions:
                issue('duplicate_native_coordinate', path + '/alignment_position')
            seen_positions.add(position['value'])
        if layout == 'current_with_reference':
            row['reference_position'] = number('Position in Reference', integer=True, minimum=1)
            row['reference_character'] = texts[fields['Reference Character']]
            ref_position, ref_character = row['reference_position'], row['reference_character']
            if (len(ref_character) != 1 or ref_character == '-' and ref_position['raw_token'] != ''
                    or ref_character != '-' and ref_position['state'] != 'available'):
                issue('reference_coordinate_conflict', path)
        if alphabet == 'dna':
            row['dna_counts'] = {base: number(base, integer=True, minimum=0)
                                 for base in ('A', 'T', 'G', 'C', 'Deletion')}
            if len(row['consensus_token']) != 1 or row['consensus_token'] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ-*?.':
                issue('native_consensus_unresolved', path + '/consensus_token')
        else:
            details, seen_symbols = [], set()
            detail_index = fields['Detail']
            detail_start = starts[detail_index]
            cursor = 0
            for fragment in texts[detail_index].split(','):
                parts = fragment.split('=', 1)
                residue = parts[0]
                count_token = parts[1] if len(parts) == 2 else ''
                count_start = detail_start + cursor + len(residue.encode(encoding)) + (len(parts) == 2)
                count = native_number(count_token, integer=True, minimum=0,
                    source_location=location(count_start, count_start + len(count_token.encode(encoding)), row_index + 2))
                symbol = PROTEIN_SYMBOLS.get(residue) if len(parts) == 2 else None
                details.append({'raw_token': fragment, 'raw_residue_token': residue,
                                'symbol': symbol, 'count': count})
                if len(parts) != 2:
                    issue('malformed_detail', path + '/protein_detail/' + str(len(details) - 1))
                elif symbol is None:
                    issue('native_residue_unresolved', path + '/protein_detail/' + str(len(details) - 1))
                elif symbol in seen_symbols:
                    issue('duplicate_native_residue', path + '/protein_detail/' + str(len(details) - 1))
                if symbol is not None:
                    seen_symbols.add(symbol)
                if count['state'] != 'available':
                    issue('malformed_native_number' if count['state'] in ('failed', 'incompatible')
                          else 'native_number_unavailable', path + '/protein_detail/' + str(len(details) - 1) + '/count')
                cursor += len(fragment.encode(encoding)) + 1
            row['protein_detail'] = details
            if row['consensus_token'] not in PROTEIN_SYMBOLS:
                issue('native_consensus_unresolved', path + '/consensus_token')
        if row['n_sequences']['state'] == 'available':
            displayed = (list(row['dna_counts'].values()) if alphabet == 'dna'
                         else [entry['count'] for entry in row['protein_detail']])
            if all(count['state'] == 'available' for count in displayed):
                displayed_total = sum(count['value'] for count in displayed)
                if displayed_total > row['n_sequences']['value'] or (
                        alphabet == 'protein' and displayed_total != row['n_sequences']['value']):
                    issue('native_count_total_conflict', path)
        value['rows'].append(row)
    if diagnostics:
        value['completeness'] = 'truncated' if truncated else 'partial'
    # A document with a valid header is still readable when it has no rows.
    validate_msa_frequency_table(value)
    return {'status': 'partial' if diagnostics else 'ok', 'value': value,
            'diagnostics': diagnostics}


__all__ = ['parse_msa_frequency_table']
