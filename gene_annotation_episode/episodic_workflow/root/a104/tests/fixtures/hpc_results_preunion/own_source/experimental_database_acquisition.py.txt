"""Selected experimental-database searches and records, with native custody.

Each invocation performs one public read request. Search terms, pages, assay
identities and sections remain episode decisions. No match is chosen or graded
as molecular-function evidence by the acquisition layer.
"""
from dataclasses import replace
import json
from urllib.parse import quote

from .acquisition import AcquisitionError, SourceSnapshot
from .domain import ContractError, obj


PROVIDERS = ('sabiork', 'brenda', 'bioassay', 'chembl', 'mavedb')
OPERATIONS = tuple(f'public.{provider}.{action}' for provider in PROVIDERS
                   for action in ('search', 'read')) + ('public.brenda.graph_search',)
MAX_BYTES = 64 * 1024 * 1024
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 4000}
LIMIT = {'type': 'integer', 'minimum': 1, 'maximum': 100}
OFFSET = {'type': 'integer', 'minimum': 0}
BYTE_LIMIT = {'type': 'integer', 'minimum': 1024, 'maximum': MAX_BYTES}
CHEMBL_ID = {'type': 'string', 'pattern': r'^CHEMBL[0-9]+$'}
URN = {'type': 'string', 'pattern': r'^urn:mavedb:[0-9]+-[a-z0-9]+-[0-9]+$'}
EC = {'type': 'string', 'pattern': r'^[0-9]+\.[0-9-]+\.[0-9-]+\.[0-9-]+$'}
BRENDA_FIELDS = {'enzyme_name': 9, 'recommended_name': 29, 'accession': 100,
                 'ec': 7, 'organism': 20, 'reference': 30, 'km': 12,
                 'turnover': 44, 'specific_activity': 34, 'variants': 8}


def catalog():
    definitions = {
        'sabiork.search': (
            'Search SABIO-RK reaction-kinetic experiments using a literal provider query, e.g. '
            'UniProtKB_AC:<accession>, Organism:"<name>", ECNumber:<EC>, or their AND combination. '
            'One page retains native parameters, assayed enzyme variant, conditions and publication links.',
            obj({'query': TEXT, 'page': {'type': 'integer', 'minimum': 1},
                 'limit': LIMIT, 'max_bytes': BYTE_LIMIT}, ['query'])),
        'sabiork.read': (
            'Read one SABIO-RK kinetic entry by its entry ID, including parameters, units, '
            'substrates, enzyme preparation, conditions and original publication.',
            obj({'entry_id': {'type': 'integer', 'minimum': 1}, 'max_bytes': BYTE_LIMIT}, ['entry_id'])),
        'brenda.search': (
            'Search BRENDA public full text for a literal enzyme name, accession, EC number, organism '
            'or phrase. Return linked enzyme and literature records. Optional fields select actual '
            'BRENDA categories; text-mined results are included only when explicitly selected. '
            'A category summary supplies search_result_queries; follow a selected result_field '
            'to read its hits. enzyme_name searches synonyms; recommended_name searches the recommended name. '
            'Read and filter retained results using source.experimental.records.',
            obj({'query': TEXT, 'include_text_mining': {'type': 'boolean'},
                 'fields': {'type': 'array', 'items': {'enum': list(BRENDA_FIELDS)},
                    'minItems': 1, 'uniqueItems': True},
                 'result_field': {'enum': list(BRENDA_FIELDS)},
                 'max_bytes': BYTE_LIMIT}, ['query'])),
        'brenda.read': (
            'Read a BRENDA enzyme page, or its selected literature record when reference_id is supplied. '
            'Retain original HTML and a readable text projection with table boundaries and source links. '
            'Enzyme pages can exceed several MB; max_bytes can be increased after a reported capture limit. '
            'The record supplies curated experimental leads and measurements; assess its cited experiment.',
            obj({'ec_number': EC, 'reference_id': {'type': 'integer', 'minimum': 1},
                 'max_bytes': BYTE_LIMIT}, ['ec_number'])),
        'brenda.graph_search': (
            'Search BRENDA\'s public structured knowledge graph for enzyme identifiers and linked '
            'publications. Select accession, EC number, enzyme name, organism or reference title. '
            'Accession and EC searches match identifiers; name/title searches use literal text. '
            'This is an additional search route when classic full-text access is unavailable. '
            'The prototype graph supplies discovery metadata, not kinetic measurements or complete '
            'database coverage. Follow returned enzyme-page reads and publication identifiers to assess experiments.',
            obj({'field': {'enum': ['accession', 'ec_number', 'enzyme_name', 'organism', 'reference_title']},
                 'query': TEXT, 'limit': LIMIT, 'offset': OFFSET, 'max_bytes': BYTE_LIMIT}, ['field', 'query'])),
        'bioassay.search': (
            'Search PubChem BioAssay (NCBI pcassay) for a literal indexed query. Enzyme names, '
            'protein accessions and organism terms can discover assay IDs. Read a selected assay '
            'description to establish target, protocol, result-column definitions and related assays.',
            obj({'query': TEXT, 'limit': LIMIT, 'offset': OFFSET, 'max_bytes': BYTE_LIMIT}, ['query'])),
        'bioassay.read': (
            'Read a selected PubChem AID description, summary or result table. Description contains '
            'protocol and result definitions; results are native CSV, optionally restricted to one SID. '
            'Retain inactive and inconclusive outcomes and all reported qualifiers. Use a suitable '
            'max_bytes for large result tables; an incomplete download is not an empty assay.',
            obj({'aid': {'type': 'integer', 'minimum': 1},
                 'section': {'enum': ['description', 'summary', 'results']},
                 'sid': {'type': 'integer', 'minimum': 1}, 'max_bytes': BYTE_LIMIT}, ['aid', 'section'])),
        'chembl.search': (
            'Search ChEMBL targets or assays. A literal query uses the provider text search; '
            'accession selects targets by UniProt accession; target_id selects assays for that target. '
            'Organism can restrict target discovery. One explicit page is returned with continuation.',
            obj({'collection': {'enum': ['target', 'assay']}, 'query': TEXT, 'accession': TEXT,
                 'target_id': CHEMBL_ID, 'organism': TEXT, 'limit': LIMIT,
                 'offset': OFFSET, 'max_bytes': BYTE_LIMIT}, ['collection'])),
        'chembl.read': (
            'Read a ChEMBL target, assay, document or a page of assay activities. For activities, '
            'record_id is the assay CHEMBL ID. Retain original and standardized measurements, '
            'relations, units, validity comments and publication links; IC50, Ki and Kd retain their meanings.',
            obj({'collection': {'enum': ['target', 'assay', 'document', 'activities']},
                 'record_id': CHEMBL_ID, 'limit': LIMIT, 'offset': OFFSET,
                 'max_bytes': BYTE_LIMIT}, ['collection', 'record_id'])),
        'mavedb.search': (
            'Search public MaveDB score sets by a literal gene, protein, organism or descriptive query. '
            'One page contains dataset URNs, measured phenotype descriptions, targets and publications. '
            'Read the selected metadata to determine the actual assay and experimental construct.',
            obj({'query': TEXT, 'limit': LIMIT, 'offset': OFFSET, 'max_bytes': BYTE_LIMIT}, ['query'])),
        'mavedb.read': (
            'Read a public MaveDB score-set metadata record or one page of deposited scores/counts. '
            'Metadata defines construct, assay and score columns. Preserve native variant identifiers '
            'and score scale; a deposited score requires its assay interpretation before A105 grading.',
            obj({'urn': URN, 'section': {'enum': ['metadata', 'scores', 'counts']},
                 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10000},
                 'offset': OFFSET, 'max_bytes': BYTE_LIMIT}, ['urn', 'section'])),
    }
    return {'public.' + name: {'description': description, 'input_schema': schema}
            for name, (description, schema) in definitions.items()}


def _brenda_graph_query(arguments):
    """Bounded literal search over the provider's published D3O schema.

    Schema and examples: https://sparql.dsmz.de/brenda . No caller-supplied
    SPARQL, inferred experiment or measurement calculation is accepted here.
    """
    literal = json.dumps(arguments['query'], ensure_ascii=False)
    field = arguments['field']
    filters = {
        'accession': f'FILTER(STR(?identifier) = {literal} || STRENDS(STR(?identifier), CONCAT("/", {literal})))',
        'ec_number': f'FILTER(STR(?ec_label) = {literal} || STRENDS(STR(?ec), CONCAT("/", {literal})))',
        'enzyme_name': '?ec (dcterms:description|d3o:hasSynonyms|d3o:hasSystematicName) ?matched_name .\n'
                       f'FILTER(CONTAINS(LCASE(STR(?matched_name)), LCASE({literal})))',
        'organism': f'FILTER(CONTAINS(LCASE(STR(?organism_label)), LCASE({literal})))',
        'reference_title': f'FILTER(CONTAINS(LCASE(STR(?title)), LCASE({literal})))',
    }
    return (
        'PREFIX d3o: <https://purl.dsmz.de/schema/>\n'
        'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n'
        'PREFIX dcterms: <http://purl.org/dc/terms/>\n'
        'SELECT DISTINCT ?enzyme ?identifier ?ec ?ec_label ?organism ?organism_label '
        '?reference ?title ?pubmed_id ?pmcid WHERE {\n'
        '?enzyme a d3o:Enzyme ; d3o:isClassifiedAs ?ec ; d3o:foundIn ?organism .\n'
        'OPTIONAL { ?enzyme d3o:hasIdentifier ?identifier . }\n'
        'OPTIONAL { ?ec rdfs:label ?ec_label . }\n'
        'OPTIONAL { ?organism rdfs:label ?organism_label . }\n'
        'OPTIONAL { ?enzyme d3o:hasReference ?reference .\n'
        '  OPTIONAL { ?reference dcterms:title ?title . }\n'
        '  OPTIONAL { ?reference d3o:hasPubMedID ?pubmed_id . }\n'
        '  OPTIONAL { ?reference d3o:hasPMCID ?pmcid . }\n'
        '}\n' + filters[field] + '\n}\n'
        'ORDER BY ?enzyme ?identifier ?ec ?organism ?reference ?title ?pubmed_id ?pmcid\n'
        f"LIMIT {arguments.get('limit', 10)} OFFSET {arguments.get('offset', 0)}")


def _skill(client, provider, path, params, media_type, max_bytes):
    skill, base = {
        'chembl': ('chembl-skill', 'https://www.ebi.ac.uk/chembl/api/data'),
        'bioassay': ('pubchem-pug-skill', 'https://pubchem.ncbi.nlm.nih.gov/rest/pug'),
    }[provider]
    payload = {'base_url': base, 'path': path, 'params': params, 'max_items': 10,
               'timeout_sec': client.timeout,
               'response_format': 'text' if media_type == 'text/csv' else 'json'}
    _, raw, transport = client._skill(skill, 'rest_request.py', payload,
        capture_headers=True, service_name='experimental.' + provider, max_bytes=max_bytes)
    from datetime import datetime, timezone
    response = transport.get('response', transport)
    return SourceSnapshot('experimental.' + provider, response.get('url', base + '/' + path),
        payload, datetime.now(timezone.utc).isoformat(), raw, media_type, transport)


def request(client, operation, arguments):
    """Build a bounded request from the selected public operation only."""
    from .domain import validate_schema
    validate_schema(arguments, catalog()[operation]['input_schema'])
    _, provider, action = operation.split('.')
    a = arguments
    limit, offset = a.get('limit', 10), a.get('offset', 0)
    max_bytes = a.get('max_bytes', 8 * 1024 * 1024)
    media_type, params, body = 'application/json', {}, None
    path = None
    if provider == 'sabiork':
        url = 'https://sabiork.h-its.org/export-api/sabio/kinlaw-entry/json'
        params = {'q': a['query'] if action == 'search' else 'EntryID:' + str(a['entry_id']),
                  'page': a.get('page', 1), 'pageSize': limit if action == 'search' else 1}
    elif provider == 'brenda':
        media_type = 'text/html'
        if action == 'graph_search':
            media_type = 'application/sparql-results+json'
            url = 'https://sparql.dsmz.de/api/brenda'
            params = {'query': _brenda_graph_query(a)}
        elif action == 'search':
            url = 'https://www.brenda.dsmz.de/fulltext.php'
            params = {'Searchterm': a['query'], 'stype': 2}
            if a.get('fields'):
                params['tables[]'] = [BRENDA_FIELDS[field] for field in a['fields']]
            else:
                params['compl_db'] = 'on'
            if 'result_field' in a:
                params.update(showhits=1, a=BRENDA_FIELDS[a['result_field']])
            if a.get('include_text_mining', False):
                params['include_tm'] = 'on'
        elif 'reference_id' in a:
            url = 'https://www.brenda.dsmz.de/literature.php'
            params = {'e': a['ec_number'], 'r': a['reference_id']}
        else:
            url = 'https://www.brenda.dsmz.de/enzyme.php'
            params = {'ecno': a['ec_number']}
    elif provider == 'bioassay':
        if action == 'search':
            url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
            params = {'db': 'pcassay', 'term': a['query'], 'retmax': limit,
                      'retstart': offset, 'retmode': 'json', 'tool': 'gene-annotation-episode'}
        elif a['section'] == 'results':
            path = f"assay/aid/{a['aid']}" + (f"/sid/{a['sid']}" if 'sid' in a else '') + '/CSV'
            media_type = 'text/csv'
        else:
            if 'sid' in a:
                raise ContractError('bioassay_sid_requires_results')
            path = f"assay/aid/{a['aid']}/{a['section']}/JSON"
    elif provider == 'chembl':
        if action == 'search':
            collection = a['collection']
            if not any(a.get(key) for key in ('query', 'accession', 'target_id')):
                raise ContractError('chembl_search_selector_required')
            if 'accession' in a and collection != 'target' or 'target_id' in a and collection != 'assay':
                raise ContractError('chembl_search_selector_collection_mismatch')
            path = collection + ('/search.json' if 'query' in a else '.json')
            params = {'limit': limit, 'offset': offset}
            for selected, native in [('query', 'q'), ('accession', 'target_components__accession'),
                                     ('target_id', 'target_chembl_id'), ('organism', 'organism')]:
                if selected in a:
                    if selected == 'organism' and collection != 'target':
                        raise ContractError('chembl_organism_filter_requires_target_collection')
                    params[native] = a[selected]
        elif a['collection'] == 'activities':
            path = 'activity.json'
            params = {'assay_chembl_id': a['record_id'], 'limit': limit, 'offset': offset}
        else:
            path = a['collection'] + '/' + a['record_id'] + '.json'
    elif provider == 'mavedb':
        base = 'https://api.mavedb.org/api/v1/score-sets/'
        if action == 'search':
            url = base + 'search'
            body = {'text': a['query'], 'limit': limit, 'offset': offset}
        else:
            url = base + quote(a['urn'], safe=':')
            if a['section'] != 'metadata':
                url += '/' + a['section']
                params = {'start': offset, 'limit': a.get('limit', 100)}
                media_type = 'text/csv'
    else:
        raise ContractError('experimental_database_provider_unknown')
    try:
        snapshot = (_skill(client, provider, path, params, media_type, max_bytes) if path else
            client._http('experimental.' + provider, url, params, media_type,
                         json_body=body, max_bytes=max_bytes, follow_redirects=False))
    except AcquisitionError as error:
        if error.snapshot is None:
            raise
        snapshot = error.snapshot
        # Retained HTTP failures and partial responses are published as such.
    return replace(snapshot, service='experimental.' + provider,
        request={'operation': operation, 'arguments': dict(a), 'native_request': snapshot.request})


def publish(registry, operation, arguments, snapshot):
    from .experimental_database_records import project, html_projection
    if snapshot.request.get('operation') != operation or snapshot.request.get('arguments') != arguments:
        raise ContractError('experimental_database_selected_request_mismatch')
    transport = snapshot.transport or {}
    response = transport.get('response', transport)
    status = response.get('status', transport.get('status'))
    capture = transport.get('capture', response.get('capture', {}))
    complete = response.get('body_complete') is True and not any(
        transport.get(key) or response.get(key) or capture.get(key)
        for key in ('truncated', 'capture_failure', 'body_capture_error', 'body_limit_exceeded'))
    media_type = snapshot.media_type.partition(';')[0].strip().lower()
    text, projection_failure, text_decoding = None, None, None
    if media_type == 'text/html' and status == 200 and complete:
        try:
            text, text_decoding = html_projection(snapshot.content)
        except Exception as error:
            # A provider representation error must not discard the response or
            # masquerade as invalid caller arguments. Retain original custody
            # below even when its optional readable projection cannot be made.
            projection_failure = {'stage': 'html_text',
                'exception_type': type(error).__name__,
                'diagnostic_ref': registry.store.artifact(
                    f'{type(error).__name__}: {error}', 'text/plain')}
    accession = next((str(arguments[key]) for key in ('entry_id', 'aid', 'record_id', 'urn')
                      if key in arguments), None)
    source = registry._source(snapshot.service, None, snapshot=snapshot, text=text, accession=accession)
    result = {'version': 'experimental_database_source_v1', 'provider': operation.split('.')[1],
              'operation': operation, 'source_ref': source['id'], 'artifact_ref': source['artifact_ref'],
              'http_status': status, 'captured_bytes': len(snapshot.content), 'capture_complete': complete,
              'source_format': snapshot.media_type, 'next_query': None,
              'read_query': {'source_ref': source['id'], 'representation': 'text' if text is not None else 'original'},
              'records_query': {'source_ref': source['id']},
              'qualification': 'Source discovery and deposited measurements. Assess actual construct, protocol, controls and original experiment before A105 scoring.'}
    if text_decoding is not None:
        result['text_decoding'] = text_decoding
    if status != 200 or not complete:
        capture_failure = response.get('body_capture_failure', transport.get('body_capture_failure'))
        result.update(status='unavailable', reason=(capture_failure or
            ('http_response_unsuccessful' if status != 200 else 'http_response_incomplete')))
        if response.get('response_byte_limit') is not None:
            result['response_byte_limit'] = response['response_byte_limit']
    elif projection_failure is not None:
        result.update(status='unavailable', reason='source_text_projection_failed',
                      projection_failure=projection_failure)
    else:
        try:
            result.update(project(snapshot.content, operation, arguments, source['id']))
            result['status'] = 'available'
        except (ValueError, TypeError, KeyError) as error:
            result.update(status='unavailable', reason='provider_representation_unrecognized',
                          parser_error=type(error).__name__,
                          diagnostic_ref=registry.store.artifact(
                              f'{type(error).__name__}: {error}', 'text/plain'))
    return result, [source['id']]
