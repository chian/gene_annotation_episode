"""Conservative sequence-block reading with original UTF-8 byte witnesses.

Candidates are literal residue strings, never an inferred biological identity.
Hard hyphens remain unresolved until explicitly selected as layout separators.
No substitutions, tags, unknown residues or gaps are silently corrected.
"""
from __future__ import annotations

import hashlib
import html
import re

from .domain import ContractError, REF, obj
from .literature_sequence_discovery import protein_operand
from .source_locations import received_source

TOOL = 'source.sequence.scan'
_BLOCK = re.compile(r'</?(?:p|div|td|th|tr|li|section|title|caption|table|pre)\b', re.I)
_LEX = re.compile(r'<!--.*?-->|<[^>]*>|&(?:#x[0-9a-fA-F]+|#\d+|[A-Za-z]+);|.', re.S)
_HARD_HYPHENS = '-\u2010\u2011\u2013'
_CANDIDATE = re.compile(r'[A-Z]{8,}(?:[\s\-\u00ad\u2010\u2011\u2013]*[A-Z]{2,})*|[a-z]{20,}(?:[\s\-\u00ad\u2010\u2011\u2013]*[a-z]{8,})*')
_ORIGIN_ROW = re.compile(r'[ \t]*(\d+)[ \t]+([A-Za-z]+(?:[ \t]+[A-Za-z]+)*)[ \t]*')


def scan_schema():
    return obj({'subject_ref': REF, 'source_ref': REF,
        'representation': {'enum': ['original', 'text']},
        'offset': {'type': 'integer', 'minimum': 0},
        'window_bytes': {'type': 'integer', 'minimum': 1024, 'maximum': 1048576},
        'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50},
        'minimum_length': {'type': 'integer', 'minimum': 8},
        'formatting_hyphen_offsets': {'type': 'array', 'uniqueItems': True,
            'items': {'type': 'integer', 'minimum': 0}}},
        ['subject_ref', 'source_ref', 'representation'])


def _origin_blocks(visible):
    """Locate numbered GenBank/GenPept residues before removing numbering.

    ORIGIN supplies the format boundary; ordinary lowercase prose keeps the
    conservative generic scanner. A missing row or non-sequence line ends a
    contiguous block, so separate fragments never become a complete sequence.
    """
    blocks, active, cursor = [], False, 0
    start = end = next_number = origin_start = None
    for line in visible.splitlines(keepends=True):
        line_start, cursor = cursor, cursor + len(line)
        content = line.rstrip('\r\n')
        row = _ORIGIN_ROW.fullmatch(content) if active else None
        if (row is not None and int(row[1]) > 0
                and (start is None or int(row[1]) == next_number)):
            number = int(row[1])
            if start is None:
                start = line_start + row.start(2)
            end = line_start + row.end(2)
            next_number = number + sum(char.isalpha() for char in row[2])
            continue
        if start is not None:
            blocks.append((start, end, origin_start))
            start = end = next_number = None
        active = content.strip(' \t') == 'ORIGIN'
        origin_start = line_start if active else None
    if start is not None:
        blocks.append((start, end, origin_start))
    return blocks


def _candidate_spans(visible, origin_blocks):
    cursor = 0
    for start, end, origin_start in origin_blocks:
        yield from ((*match.span(), match.start())
            for match in _CANDIDATE.finditer(visible, cursor, start))
        # Retain the format marker when candidate-count pagination resumes.
        yield start, end, origin_start
        cursor = end
    yield from ((*match.span(), match.start())
        for match in _CANDIDATE.finditer(visible, cursor))


def _visible(text, base):
    """Project markup text while preserving each character's original span."""
    offsets = [base]
    for char in text:
        offsets.append(offsets[-1] + len(char.encode('utf-8')))
    chars, spans = [], []
    for match in _LEX.finditer(text):
        token = match.group()
        if token.startswith('<!--'):
            value = '\0'
        elif token.startswith('<'):
            value = '\0' if _BLOCK.match(token) else ('\n' if re.match(r'<br\b', token, re.I) else '')
        elif token.startswith('&'):
            value = html.unescape(token)
        else:
            value = token
        for char in value:
            chars.append(char)
            spans.append((offsets[match.start()], offsets[match.end()]))
    visible = ''.join(chars)
    origin_blocks = _origin_blocks(visible)
    # FASTA descriptions and terminal numbering are not residue strings.
    removals = []
    for pattern, kind in ((r'(?m)^>[^\n]*', 'fasta_header'),
            (r'(?m)^[ \t]*\d+[ \t]+|[ \t]+\d+[ \t]*(?=\n|$)', 'line_number')):
        for match in re.finditer(pattern, visible):
            removals.append((match.start(), match.end(), kind))
    for start, end, kind in removals:
        for index in range(start, end):
            chars[index] = '\0' if kind == 'fasta_header' else ' '
    for match in re.finditer(r'\n[ \t]*\n', visible):
        chars[match.start()] = '\0'
    return ''.join(chars), spans, removals, origin_blocks


def _comparison(query, sequence):
    if sequence == query:
        return {'relationship': 'full_string_equal', 'query_start': 0, 'query_end': len(query),
            'source_start': 0, 'source_end': len(sequence)}
    start = sequence.find(query)
    if start >= 0:
        return {'relationship': 'source_contains_complete_query', 'query_start': 0,
            'query_end': len(query), 'source_start': start, 'source_end': start + len(query),
            'source_prefix': sequence[:start], 'source_suffix': sequence[start + len(query):]}
    start = query.find(sequence)
    if start >= 0:
        return {'relationship': 'source_is_query_fragment', 'query_start': start,
            'query_end': start + len(sequence), 'source_start': 0, 'source_end': len(sequence)}
    if len(query) == len(sequence) and not set(sequence).intersection(_HARD_HYPHENS):
        differences = [{'position': index, 'query': left, 'source': right}
            for index, (left, right) in enumerate(zip(query, sequence)) if left != right]
        return {'relationship': 'different_strings_equal_length',
            'comparison_basis': 'literal_positions_without_alignment',
            'difference_count': len(differences), 'differences': differences[:100],
            'differences_truncated': len(differences) > 100}
    return {'relationship': 'no_exact_containment', 'query_length': len(query),
        'source_length': len(sequence)}


def _position_map(positions):
    result = []
    for index, (start, end) in enumerate(positions):
        if (result and result[-1]['source_end'] == start and end - start == 1
                and result[-1]['source_end'] - result[-1]['source_start'] ==
                    result[-1]['sequence_end'] - result[-1]['sequence_start']):
            result[-1].update(sequence_end=index + 1, source_end=end)
        else:
            result.append({'sequence_start': index, 'sequence_end': index + 1,
                'source_start': start, 'source_end': end})
    return result


def scan(registry, arguments, scope, permitted_inputs):
    query = protein_operand(registry, arguments['subject_ref'], scope)
    source_ref, representation = arguments['source_ref'], arguments['representation']
    artifact = received_source(registry.store, source_ref, representation,
        permitted_inputs=permitted_inputs, scope=scope)
    offset, window = arguments.get('offset', 0), arguments.get('window_bytes', 262144)
    total = artifact['size']
    if offset > total:
        raise ContractError('source_sequence_offset_out_of_bounds')
    path = registry.store.path / 'artifacts' / artifact['sha256'][:2] / artifact['sha256']
    with path.open('rb') as stream:
        if stream.seek(0, 2) != total:
            raise ContractError('source_sequence_artifact_size_conflict')
        stream.seek(offset)
        raw = stream.read(window)
    if offset == 0 and len(raw) == total and hashlib.sha256(raw).hexdigest() != artifact['sha256']:
        raise ContractError('source_sequence_artifact_identity_conflict')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as error:
        if error.reason != 'unexpected end of data' or offset + len(raw) == total:
            raise ContractError('source_sequence_requires_utf8_text') from error
        raw = raw[:error.start]
        text = raw.decode('utf-8')
    if '\x00' in text:
        raise ContractError('source_sequence_requires_utf8_text')
    visible, spans, line_removals, origin_blocks = _visible(text, offset)
    approved = set(arguments.get('formatting_hyphen_offsets', []))
    available_hyphens = {spans[index][0] for index, char in enumerate(visible) if char in _HARD_HYPHENS}
    if approved - available_hyphens:
        raise ContractError('formatting_hyphen_not_in_selected_window')
    candidates, used, next_offset = [], set(), offset + len(raw)
    limit, minimum = arguments.get('limit', 10), arguments.get('minimum_length', 20)
    for match_start, match_end, resume_start in _candidate_spans(visible, origin_blocks):
        block = visible[match_start:match_end]
        if sum(char.isalpha() for char in block) < minimum:
            continue
        if len(candidates) >= limit:
            next_offset = spans[resume_start][0]
            break
        start, end = spans[match_start][0], spans[match_end - 1][1]
        chars, positions, removed, unresolved = [], [], [], []
        for index in range(match_start, match_end):
            char, (left, right) = visible[index], spans[index]
            if char.isalpha():
                chars.append(char.upper())
                positions.append((left, right))
            elif char in _HARD_HYPHENS and left not in approved:
                chars.append(char)
                positions.append((left, right))
                unresolved.append(left)
            else:
                kind = ('declared_formatting_hyphen' if char in _HARD_HYPHENS else
                        'soft_hyphen' if char == '\u00ad' else 'layout_whitespace')
                removed.append({'start': left, 'end': right, 'kind': kind})
                if char in _HARD_HYPHENS:
                    used.add(left)
        sequence = ''.join(chars)
        for left, right, kind in line_removals:
            if kind == 'line_number' and match_start <= left < right <= match_end:
                removed.append({'start': spans[left][0], 'end': spans[right - 1][1], 'kind': kind})
        candidate = {'start': start, 'end': end, 'normalized_sequence': sequence,
            'original_text': raw[start - offset:end - offset].decode('utf-8'),
            'position_map': _position_map(positions), 'removed_formatting': removed,
            'unresolved_hyphen_offsets': unresolved,
            'comparison': _comparison(query, sequence),
            'touches_window_boundary': (start == offset and offset > 0) or
                (end == offset + len(raw) and end < total)}
        if unresolved:
            candidate['conditional_comparison_if_hyphens_are_formatting'] = _comparison(query,
                ''.join(char for char in sequence if char not in _HARD_HYPHENS))
            candidate['qualification'] = 'Inspect source layout to distinguish formatting from biological gaps before selecting formatting_hyphen_offsets.'
        candidates.append(candidate)
    if approved - used:
        raise ContractError('formatting_hyphen_not_in_recognized_sequence')
    return {'version': 'source_sequence_blocks_v1', 'subject_ref': arguments['subject_ref'],
        'source_ref': source_ref, 'artifact_ref': artifact['id'], 'representation': representation,
        'start': offset, 'examined_end': offset + len(raw), 'total_bytes': total,
        'candidates': candidates, 'normalization': 'case_whitespace_numbering_soft_hyphens_and_explicitly_selected_hard_hyphens',
        'next_query': {**arguments, 'offset': next_offset, 'formatting_hyphen_offsets': []}
            if next_offset < total else None,
        'qualification': 'Candidate blocks and literal correspondence require source interpretation. Numbered GenBank/GenPept blocks require the ORIGIN marker in the selected window. Boundary fragments may need an overlapping read. Tags, residue differences and unknown symbols remain explicit; no experimental assessment is assigned.'}, []
