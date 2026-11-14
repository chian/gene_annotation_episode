"""Pure, located readers for supplied BLAST preparation text.

These documents retain native observations, not preparation success, inferred
membership, effective defaults, or scientific scores. The caller retains the
exact bytes and joins literal references to selected inputs and captured files.
No reader opens paths, invokes a program, or resolves a database.
"""
from __future__ import annotations
import re
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_blast_database_extraction import _check, _check_bytes, _failure
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_blast_preparation_contracts import validate_blast_preparation_document
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_blast_utility_contracts import validate_blast_utility_record
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
_GRAMMARS = frozenset({'blast_database_lines', 'profile_whitespace_tokens'})

def _problem(document, code, line=None, *, stage='parse'):
    row = _failure(stage, code, document['occurrence_id'], line_number=line)
    if row not in document['failures']:
        document['failures'].append(row)

def _context(contents, occurrence, kind):
    occurrence = validate_blast_utility_record('ArtifactOccurrence', occurrence)
    check = _check_bytes(contents, occurrence)
    document = {'version': 'blast_preparation_document_v1', 'kind': kind, 'occurrence_id': occurrence['occurrence_id'], 'native_fields': [], 'rows': [], 'checks': [check], 'failures': []}
    if kind == 'profile_aux':
        document['parameter_observations'] = []
    if occurrence['completeness'] != 'complete':
        _problem(document, 'output_completeness_unestablished', stage='capture')
    lines, start = ([], 0)
    for number, match in enumerate(re.finditer(b'[^\\r\\n]*(?:\\r\\n|\\r|\\n|$)', contents), 1):
        raw = match.group()
        if not raw:
            continue
        body = raw.rstrip(b'\r\n')
        try:
            text = body.decode('utf-8')
            if any((ord(c) < 32 and c != '\t' for c in text)) or '\x7f' in text:
                raise ValueError('unsupported_native_control')
        except (UnicodeDecodeError, ValueError):
            text = None
            _problem(document, 'native_row_invalid', number)
        lines.append((number, start, text))
        start += len(raw)
    return (document, lines)

def _finish(document):
    parsed = [row for row in document['failures'] if row['stage'] == 'parse']
    invalid = [row for row in parsed if row['code'] != 'native_diagnostic_unrecognized']
    status = 'fail' if invalid else 'unknown' if parsed else 'pass'
    oid = document['occurrence_id']
    document['checks'].append(_check('syntax', status, [oid], 'native_format_parser', [oid], invalid[0]['code'] if invalid else parsed[0]['code'] if parsed else None))
    return validate_blast_preparation_document(document)

def parse_blast_preparation_list(contents: bytes, *, grammar: str, occurrence: dict) -> dict:
    """Locate literal entries without quoting, normalizing, or deduplicating them.

    Database lists contain one trimmed name per nonempty line; profile lists
    split on native ASCII spaces/tabs and line endings. Comments are not a
    feature of either native grammar: a '#' token remains a literal entry.
    """
    if type(grammar) is not str or grammar not in _GRAMMARS:
        raise ContractError('blast_utility_preparation_list_grammar')
    document, lines = _context(contents, occurrence, 'list')
    for number, start, line in lines:
        if line is None:
            continue
        if grammar == 'blast_database_lines':
            value = line.strip(' \t')
            spans = [(len(line) - len(line.lstrip(' \t')), value)] if value else []
        else:
            spans = [(match.start(), match.group()) for match in re.finditer('[^ \\t]+', line)]
        for token_ordinal, (position, value) in enumerate(spans):
            begin = start + len(line[:position].encode('utf-8'))
            document['rows'].append({'ordinal': len(document['rows']), 'line_number': number, 'token_ordinal': token_ordinal, 'original_token': value, 'start_byte': begin, 'end_byte': begin + len(value.encode('utf-8'))})
    if not document['rows']:
        _problem(document, 'native_document_invalid')
    return _finish(document)
