"""Exact protein identity and publication leads, with retained source custody.

These operations find source records and citations. They never interpret a
database annotation as an experiment or assign experimental evidence credit.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import parse_qs, urlsplit

from .domain import ContractError, REF, obj
from .source_locations import received_source


IDENTITY_TOOL = 'public.literature.sequence_identity'
REFERENCES_TOOL = 'source.sequence.references'


def identity_schema():
    return obj({'subject_ref': REF,
        'size': {'type': 'integer', 'minimum': 1, 'maximum': 25},
        'cursor': {'type': 'string', 'minLength': 1},
        'reviewed': {'type': 'boolean'}}, ['subject_ref'])


def references_schema():
    return obj({'subject_ref': REF, 'source_ref': REF,
        'record_index': {'type': 'integer', 'minimum': 0},
        'offset': {'type': 'integer', 'minimum': 0},
        'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25}},
        ['subject_ref', 'source_ref', 'record_index'])


def protein_operand(registry, subject_ref, scope):
    registry._check_sequence_operand(subject_ref, scope)
    if registry.store.subject_molecule(subject_ref) != 'protein':
        raise ContractError('literature_sequence_requires_protein')
    sequence = registry._sequence(subject_ref).upper()
    if not sequence or not re.fullmatch('[A-Z]+', sequence):
        raise ContractError('literature_sequence_requires_residue_string')
    return sequence


def identity_request(registry, arguments, scope):
    sequence = protein_operand(registry, arguments['subject_ref'], scope)
    query = 'checksum:' + hashlib.md5(sequence.encode('ascii')).hexdigest().upper()
    if 'reviewed' in arguments:
        query += ' AND reviewed:' + str(arguments['reviewed']).lower()
    return registry.clients.uniprot_search, {'query': query,
        'size': arguments.get('size', 10),
        **({'cursor': arguments['cursor']} if 'cursor' in arguments else {})}


def _records(body):
    try:
        value = json.loads(body)
    except (ValueError, UnicodeDecodeError) as error:
        raise ContractError('sequence_identity_response_not_json') from error
    if not isinstance(value, dict) or not isinstance(value.get('results'), list):
        raise ContractError('sequence_identity_results_missing')
    return value['results']


def _sequence(row):
    value = row.get('sequence') if isinstance(row, dict) else None
    return value.get('value') if isinstance(value, dict) else None


def _summary(row, index):
    description = row.get('proteinDescription', {})
    names = []
    for entry in [description.get('recommendedName', {}),
                  *description.get('submissionNames', []), *description.get('alternativeNames', [])]:
        name = entry.get('fullName', {}).get('value')
        if isinstance(name, str) and name not in names:
            names.append(name)
    genes = []
    for gene in row.get('genes', []):
        for item in [gene.get('geneName', {}), *gene.get('synonyms', []),
                     *gene.get('orderedLocusNames', []), *gene.get('orfNames', [])]:
            if isinstance(item.get('value'), str) and item['value'] not in genes:
                genes.append(item['value'])
    references = row.get('references')
    ec_numbers = list(dict.fromkeys(item['value']
        for name in [description.get('recommendedName', {}), *description.get('alternativeNames', [])]
        for item in name.get('ecNumbers', []) if isinstance(item.get('value'), str)))
    experiment_links = [dict(item) for item in row.get('uniProtKBCrossReferences', [])
                       if item.get('database') in {'BRENDA', 'SABIO-RK', 'ChEMBL', 'MaveDB', 'PubChem'}]
    return {'record_index': index, 'accession': row.get('primaryAccession'),
        'entry_id': row.get('uniProtkbId'), 'entry_type': row.get('entryType'),
        'protein_names': names, 'gene_names': genes, 'organism': row.get('organism'),
        'ec_numbers': ec_numbers, 'experimental_database_links': experiment_links,
        'citation_count': len(references) if isinstance(references, list) else None,
        'sequence_comparison': 'full_string_equal'}


def publish_identity(registry, arguments, scope, snapshot):
    sequence = protein_operand(registry, arguments['subject_ref'], scope)
    source = registry._source('uniprot', None, snapshot=snapshot,
        operand_refs=[arguments['subject_ref']])
    records = _records(snapshot.content)
    matches, rejected = [], []
    for index, row in enumerate(records):
        # A checksum is only the retrieval key. Every actual sequence must agree.
        if _sequence(row) != sequence:
            rejected.append({'record_index': index, 'reason': 'full_sequence_not_equal'})
            continue
        summary = _summary(row, index)
        summary['references_query'] = {'subject_ref': arguments['subject_ref'],
            'source_ref': source['id'], 'record_index': index}
        matches.append(summary)
    transport = snapshot.transport or {}
    response = transport.get('response') or transport
    headers = {k.lower(): v for k, v in (response.get('headers') or {}).items()}
    next_cursor = None
    for link in headers.get('link', '').split(','):
        match = re.search(r'<([^>]+)>;\s*rel="?next"?', link)
        if match:
            next_cursor = parse_qs(urlsplit(match.group(1)).query).get('cursor', [None])[0]
    total = headers.get('x-total-results')
    return {'version': 'literature_sequence_identity_v1', 'subject_ref': arguments['subject_ref'],
        'source_ref': source['id'], 'query': snapshot.request['query'],
        'query_sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
        'query_length': len(sequence), 'matches': matches, 'rejected_records': rejected,
        'returned_records': len(records),
        'total_results': int(total) if isinstance(total, str) and total.isdigit() else None,
        'next_query': {**arguments, 'cursor': next_cursor} if next_cursor else None,
        'pagination_metadata_available': 'x-total-results' in headers,
        'qualification': 'Exact residue-string identity supplies publication leads; organism, construct and experimental attribution require source evidence.',
        'ambiguous_residue_symbols': sorted(set(sequence) & set('BXZJ')),
        'experimental_assessment': None}, [source['id']]


def references(registry, arguments, scope, permitted_inputs):
    sequence = protein_operand(registry, arguments['subject_ref'], scope)
    artifact = received_source(registry.store, arguments['source_ref'], 'original',
        permitted_inputs=permitted_inputs, scope=scope)
    records = _records(registry.store.get_artifact(artifact['id']))
    index = arguments['record_index']
    if index >= len(records):
        raise ContractError('sequence_identity_record_index_out_of_bounds')
    record = records[index]
    if _sequence(record) != sequence:
        raise ContractError('sequence_identity_full_sequence_not_equal')
    rows = record.get('references')
    if not isinstance(rows, list):
        return {'source_ref': arguments['source_ref'], 'references': [],
            'status': 'references_unavailable', 'next_query': None}, []
    start, size = arguments.get('offset', 0), arguments.get('limit', 10)
    if start > len(rows):
        raise ContractError('sequence_citation_offset_out_of_bounds')
    result = []
    for offset, row in enumerate(rows[start:start + size], start):
        citation = row.get('citation', {})
        result.append({'reference_index': offset,
            'source_pointer': f'/results/{index}/references/{offset}',
            'title': citation.get('title'), 'date': citation.get('publicationDate'),
            'journal': citation.get('journal'), 'citation_type': citation.get('citationType'),
            'identifiers': citation.get('citationCrossReferences', []),
            'reported_scope': row.get('referencePositions'),
            'reported_source': row.get('referenceComments')})
    end = start + len(result)
    return {'version': 'literature_sequence_references_v1',
        'subject_ref': arguments['subject_ref'], 'source_ref': arguments['source_ref'],
        'artifact_ref': artifact['id'], 'record': _summary(record, index),
        'references': result, 'total_references': len(rows),
        'next_query': {**arguments, 'offset': end} if end < len(rows) else None,
        'qualification': 'Database citation scopes are discovery metadata. Read the cited experiment and identify its actual assayed construct.'}, []
