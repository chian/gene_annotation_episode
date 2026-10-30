"""Explicit molecular sequence requests and source-preserving result selections.

These contracts choose no provider, candidate, locus, record or feature. They
contain no scientific score and perform no acquisition or native extraction.
"""
from copy import deepcopy
import re
from urllib.parse import urlencode

from .api_services import object_schema, validate_value

TEXT = {'type': 'string', 'minLength': 1}
INDEX = {'type': 'integer', 'minimum': 0}
FEATURE = object_schema({'record_ordinal': INDEX, 'feature_ordinal': INDEX},
                        ['record_ordinal', 'feature_ordinal'])
REQUEST_SCHEMA = object_schema({
    'operation': {'enum': ['ncbi_gene', 'get_gene_coding_sequence', 'get_plasmid_sequence']},
    'gene_ids': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT},
    'accession': TEXT, 'plasmid_id': TEXT, 'provider': {'enum': ['ncbi', 'addgene']},
    'molecule_model': {'enum': ['dna', 'rna']},
    'max_bytes': {'type': 'integer', 'minimum': 1},
}, ['operation', 'max_bytes'])
SELECTOR_SCHEMA = object_schema({
    'view': {'enum': ['gene', 'sequences', 'cds']},
    'record_ordinals': {'type': 'array', 'uniqueItems': True, 'items': INDEX},
    'features': {'type': 'array', 'items': FEATURE},
}, ['view'])


def _require(condition, code):
    if not condition:
        raise ValueError('sequence_support_' + code)


def validate_sequence_support_request(value):
    _require(type(value) is dict and type(value.get('max_bytes')) is int, 'request_invalid')
    if 'gene_ids' in value:
        _require(type(value['gene_ids']) is list and all(type(item) is str for item in value['gene_ids']), 'gene_ids_invalid')
    request = validate_value(value, REQUEST_SCHEMA, 'sequence_support_request_invalid')
    operation = request['operation']
    fields = {'operation', 'max_bytes'}
    if operation == 'ncbi_gene':
        fields.add('gene_ids')
        _require('gene_ids' in request and all(re.fullmatch(r'[0-9]+', item) for item in request['gene_ids']), 'gene_ids_invalid')
    elif operation == 'get_gene_coding_sequence':
        fields |= {'accession', 'molecule_model'}
    else:
        _require('provider' in request, 'explicit_provider_required')
        fields.add('provider')
        fields |= {'plasmid_id'} if request['provider'] == 'addgene' else {'accession', 'molecule_model'}
        if request['provider'] == 'addgene':
            _require(type(request.get('plasmid_id')) is str and re.fullmatch(r'[0-9]+', request['plasmid_id']), 'plasmid_id_invalid')
    _require(set(request) == fields, 'request_fields_conflict')
    if 'accession' in request:
        _require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.]*', request['accession']), 'accession_invalid')
    return request


def validate_sequence_support_selector(request, value):
    request = validate_sequence_support_request(request)
    _require(type(value) is dict, 'selector_invalid')
    selector = validate_value(value, SELECTOR_SCHEMA, 'sequence_support_selector_invalid')
    expected = {'ncbi_gene': 'gene', 'get_gene_coding_sequence': 'cds',
                'get_plasmid_sequence': 'sequences'}[request['operation']]
    fields = {'view'} | ({'features'} if expected == 'cds' else {'record_ordinals'} if expected == 'sequences' else set())
    _require(set(selector) == fields and selector['view'] == expected, 'selector_operation_conflict')
    original = value.get('features') if expected == 'cds' else value.get('record_ordinals')
    if expected != 'gene':
        _require(type(original) is list, 'selector_ordinals_invalid')
        for item in original:
            _require(all(type(item.get(key)) is int for key in ('record_ordinal','feature_ordinal'))
                     if expected == 'cds' and type(item) is dict else type(item) is int if expected == 'sequences' else False,
                     'selector_ordinals_invalid')
    return selector


def sequence_support_native_request(request):
    request = validate_sequence_support_request(request)
    if request['operation'] == 'ncbi_gene':
        return {'service': 'ncbi_entrez', 'url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
            'params': {'db': 'gene', 'id': ','.join(request['gene_ids']), 'retmode': 'xml', 'tool': 'gene-annotation-episode'},
            'representation': 'ncbi_gene_xml'}
    if request.get('provider') == 'addgene':
        return {'service': 'addgene', 'url': 'https://www.addgene.org/' + request['plasmid_id'] + '/sequences/',
                'params': {}, 'representation': 'addgene_html'}
    return {'service': 'ncbi_entrez', 'url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
        'params': {'db': 'nuccore', 'id': request['accession'], 'rettype': 'gbwithparts',
                   'retmode': 'text', 'tool': 'gene-annotation-episode'}, 'representation': 'genbank'}


def validate_sequence_support_snapshot(snapshot, *, request):
    native = sequence_support_native_request(request)
    _require(snapshot.service == native['service'] and snapshot.url == native['url']
             and snapshot.request == native['params'], 'snapshot_request_conflict')
    transport = snapshot.transport
    _require(type(transport) is dict and type(transport.get('status')) is int
             and 200 <= transport['status'] < 300, 'snapshot_status_invalid')
    _require(transport.get('body_complete') is True and type(snapshot.content) is bytes, 'snapshot_body_incomplete')
    _require(type(transport.get('response_byte_limit')) is int
             and transport['response_byte_limit'] == request['max_bytes']
             and len(snapshot.content) <= request['max_bytes'], 'snapshot_limit_conflict')
    selected = transport.get('request')
    address = native['url'] + ('?' + urlencode(native['params']) if native['params'] else '')
    _require(type(selected) is dict and selected.get('method') == 'GET'
             and selected.get('url') == address, 'snapshot_selected_request_conflict')
    return deepcopy(native)


__all__ = ['REQUEST_SCHEMA', 'SELECTOR_SCHEMA', 'validate_sequence_support_request',
           'validate_sequence_support_selector', 'sequence_support_native_request', 'validate_sequence_support_snapshot']
