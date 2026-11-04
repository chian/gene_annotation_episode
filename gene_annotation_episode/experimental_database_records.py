"""Bounded views of retained native experiment records; no evidence scoring."""
import csv
from html.parser import HTMLParser
import io
import json
import re
from urllib.parse import parse_qs, urljoin, urlsplit

from .domain import ContractError, REF, obj
from .source_locations import received_source


READER = 'source.experimental.records'


def reader_schema():
    return obj({'source_ref': REF, 'offset': {'type': 'integer', 'minimum': 0},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                'contains': {'type': 'string', 'minLength': 1, 'maxLength': 500},
                'contains_all': {'type': 'array', 'items': {'type': 'string',
                    'minLength': 1, 'maxLength': 500}, 'minItems': 1, 'maxItems': 10,
                    'uniqueItems': True}}, ['source_ref'])


class _HTML(HTMLParser):
    """Readable HTML projection and literal links/rows, retaining their order."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.rows = [], [], []
        self.hidden = 0
        self.link = None
        self.row = None
        self.cell = None
        self.heading = None
        self.section = ''
        self.div_depth = 0
        self.div_rows, self.div_cells = [], []
        self.table_headers = {}
        self.decoding = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'):
            self.hidden += 1
        if self.hidden:
            return
        if tag == 'div':
            self.div_depth += 1
            classes = a.get('class', '').split()
            if 'row' in classes:
                source_id = a.get('id')
                table = re.match(r'^(tab[0-9]+)', source_id or '')
                line, column = self.getpos()
                record = {'section': self.section, 'columns': [], 'column_ids': [],
                    'links': [], 'html_id': source_id, 'html_classes': classes,
                    'html_location': {'line': line, 'column': column},
                    'table_id': table.group(1) if table else None,
                    'is_header': bool(source_id and source_id.endswith('_head'))}
                self.div_rows.append({'depth': self.div_depth, 'record': record})
            if ('cell' in classes or 'header' in classes) and self.div_rows:
                self.div_cells.append({'depth': self.div_depth, 'parts': [],
                    'html_id': a.get('id'), 'row': self.div_rows[-1]['record']})
        if tag == 'a' and a.get('name') and not a.get('href'):
            # BRENDA labels its sections with literal named anchors.
            self.section = a['name']
        if tag in ('h1', 'h2', 'h3', 'h4'):
            self.heading = []
        if tag == 'a' and a.get('href'):
            self.link = {'href': a['href'], 'text': ''}
        if tag == 'tr':
            self.row = []
        if tag in ('td', 'th'):
            self.cell = []
        if tag in ('p', 'div', 'tr', 'h1', 'h2', 'h3', 'h4', 'li', 'br'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag in ('h1', 'h2', 'h3', 'h4') and self.heading is not None:
            self.section = ' '.join(''.join(self.heading).split())
            self.heading = None
        if tag == 'a' and self.link is not None:
            self.links.append(self.link)
            if self.div_rows:
                self.div_rows[-1]['record']['links'].append(dict(self.link))
            self.link = None
        if tag == 'div':
            while self.div_cells and self.div_cells[-1]['depth'] == self.div_depth:
                cell = self.div_cells.pop()
                cell['row']['columns'].append(' '.join(''.join(cell['parts']).split()))
                cell['row']['column_ids'].append(cell['html_id'])
                self.parts.append(' | ')
            while self.div_rows and self.div_rows[-1]['depth'] == self.div_depth:
                row = self.div_rows.pop()['record']
                if any(row['columns']):
                    self.rows.append(row)
                    if row['is_header'] and row['table_id']:
                        self.table_headers[row['table_id']] = list(row['columns'])
            self.div_depth = max(0, self.div_depth - 1)
        if tag in ('td', 'th') and self.cell is not None:
            if self.row is not None:
                self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
            self.parts.append(' | ')
        if tag == 'tr' and self.row is not None:
            if any(self.row):
                self.rows.append({'section': self.section, 'columns': self.row})
            self.row = None
        if tag in ('p', 'div', 'tr', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.parts.append('\n')

    def handle_data(self, data):
        if self.hidden:
            return
        self.parts.append(data)
        if self.heading is not None:
            self.heading.append(data)
        if self.cell is not None:
            self.cell.append(data)
        if self.div_cells:
            self.div_cells[-1]['parts'].append(data)
        if self.link is not None:
            self.link['text'] += data


def _html_decoding(raw):
    """Keep valid UTF-8 and show undecodable bytes as explicit hex escapes.

    Do not guess another encoding for a mixed-encoding scientific page. Original
    bytes remain the source; offsets below identify the limited projection loss.
    """
    decoded = raw.decode('utf-8-sig', 'surrogateescape')
    parts, spans, cursor = [], [], 0
    byte_offset = 3 if raw.startswith(b'\xef\xbb\xbf') else 0
    invalid_count, span_count = 0, 0
    for match in re.finditer(r'[\udc80-\udcff]+', decoded):
        prefix = decoded[cursor:match.start()]
        parts.append(prefix)
        byte_offset += len(prefix.encode('utf-8'))
        invalid = match.group().encode('utf-8', 'surrogateescape')
        if len(spans) < 100:
            spans.append({'start': byte_offset, 'end': byte_offset + len(invalid),
                          'hex': invalid.hex()})
        parts.append(''.join(f'\\x{value:02x}' for value in invalid))
        byte_offset += len(invalid)
        invalid_count += len(invalid)
        span_count += 1
        cursor = match.end()
    parts.append(decoded[cursor:])
    return ''.join(parts), {'encoding': 'utf-8', 'invalid_byte_count': invalid_count,
        'invalid_span_count': span_count, 'invalid_spans': spans,
        'invalid_spans_truncated': span_count > len(spans),
        'invalid_bytes_representation': 'literal_hex_escape; encoding_not_inferred'}


def _html(raw):
    parser = _HTML()
    decoded, parser.decoding = _html_decoding(raw)
    parser.feed(decoded)
    parser.close()
    for row in parser.rows:
        if row.get('table_id') in parser.table_headers:
            row['headers'] = parser.table_headers[row['table_id']]
    return parser


def html_projection(raw):
    parser = _html(raw)
    text = '\n'.join(line for line in (' '.join(line.split())
                     for line in ''.join(parser.parts).splitlines()) if line)
    return text, parser.decoding


def html_text(raw):
    return html_projection(raw)[0]


def _csv(raw, provider):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    fields = reader.fieldnames
    if not fields or len(fields) != len(set(fields)):
        raise ContractError('experimental_database_unique_csv_headers_required')
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ContractError('experimental_database_csv_row_width_mismatch')
    if provider == 'bioassay':
        # PubChem's annotation rows are not substance measurements.
        return [row for row in rows if str(row.get('PUBCHEM_SID', '')).isdigit()]
    return rows


def native_rows(raw, operation, arguments):
    provider = operation.split('.')[1]
    if operation == 'public.brenda.graph_search':
        return json.loads(raw)['results']['bindings']
    if provider == 'brenda':
        return _html(raw).rows
    if ((provider == 'mavedb' and arguments.get('section') in ('scores', 'counts'))
            or provider == 'bioassay' and arguments.get('section') == 'results'):
        return _csv(raw, provider)
    data = json.loads(raw)
    if provider == 'sabiork':
        return data['data']
    if provider == 'chembl':
        collection = arguments['collection']
        key = 'activities' if collection == 'activities' else collection + 's'
        return data[key] if key in data else [data]
    if provider == 'mavedb':
        return data['scoreSets'] if operation.endswith('.search') else [data]
    if operation.endswith('.search'):
        return [{'aid': int(value)} for value in data['esearchresult']['idlist']]
    if arguments['section'] == 'description':
        return [row['assay']['descr'] for row in data['PC_AssayContainer']]
    rows = data['AssaySummaries']
    return rows if isinstance(rows, list) else [rows]


def selector(source_ref, row, field, metadata_source_ref=None):
    return {'kind': 'database_measurement', 'source_ref': source_ref,
            'record_index': row, 'field': field, 'metadata_source_ref': metadata_source_ref}


def _keep(row, names):
    return {name: row[name] for name in names if name in row}


def summarize(row, index, operation, arguments, source_ref):
    provider = operation.split('.')[1]
    summary = {'record_index': index}
    if provider == 'sabiork':
        summary.update(_keep(row, ('id', 'general', 'enzyme_description', 'experimental_conditions', 'publication')))
        summary['reaction'] = _keep(row.get('reaction', {}), ('equation', 'species'))
        summary['parameters'] = [{**parameter,
            'measurement_selector': selector(source_ref, index, f'parameter:{i}')}
            for i, parameter in enumerate(row.get('kineticlaw', {}).get('parameter', []))]
        summary['read_query'] = {'entry_id': row['id']}
    elif provider == 'brenda':
        if operation == 'public.brenda.graph_search':
            values = {name: binding['value'] for name, binding in row.items()}
            summary.update(bindings=row, values=values)
            # The provider labels EC classes with enzyme names. Their native
            # identifiers carry the EC number used by the public page reader.
            ec = values.get('ec', '').removeprefix('https://purl.dsmz.de/brenda/ec/')
            if re.fullmatch(r'[0-9]+\.[0-9-]+\.[0-9-]+\.[0-9-]+', ec):
                summary['read_query'] = {'ec_number': ec}
                reference = values.get('reference', '').removeprefix(
                    'https://purl.dsmz.de/brenda/reference/')
                if reference.isdigit():
                    summary['read_query']['reference_id'] = int(reference)
        else:
            summary.update(row)
    elif provider == 'chembl':
        summary.update(_keep(row, ('target_chembl_id', 'pref_name', 'organism', 'target_type',
            'target_components', 'assay_chembl_id', 'description', 'assay_description', 'assay_type',
            'assay_organism', 'confidence_description', 'relationship_description', 'document_chembl_id',
            'assay_tax_id', 'target_organism', 'target_tax_id', 'assay_variant_accession',
            'assay_variant_mutation', 'assay_cell_type', 'assay_tissue', 'assay_subcellular_fraction',
            'src_id', 'src_assay_id', 'bao_format', 'confidence_score', 'relationship_type',
            'activity_id', 'molecule_chembl_id', 'standard_type', 'standard_value', 'standard_units',
            'standard_relation', 'type', 'value', 'units', 'relation', 'activity_comment',
            'data_validity_comment', 'potential_duplicate', 'title', 'doi', 'pubmed_id', 'year')))
        if 'activity_id' in row:
            summary['measurement_selector'] = selector(source_ref, index, 'standard_value')
        if 'target_components' in summary:
            summary['target_components'] = [_keep(component, ('accession', 'component_type',
                'component_description', 'organism', 'sequence')) for component in summary['target_components']]
    elif provider == 'mavedb':
        if arguments.get('section') in ('scores', 'counts'):
            summary.update(row)
            if arguments['section'] == 'scores':
                summary['measurement_selectors'] = {field: selector(source_ref, index, field)
                    for field in row if field not in ('accession', 'hgvs_nt', 'hgvs_splice', 'hgvs_pro')}
            summary['metadata_required'] = arguments['urn']
        else:
            summary.update(_keep(row, ('urn', 'title', 'shortDescription', 'abstractText', 'methodText',
                'numVariants', 'datasetColumns', 'targetGenes', 'primaryPublicationIdentifiers',
                'secondaryPublicationIdentifiers', 'metaAnalyzesScoreSetUrns', 'scoreCalibrations')))
            summary['read_query'] = {'urn': row['urn'], 'section': 'metadata'}
    elif provider == 'bioassay':
        summary.update(row)
        if arguments.get('section') == 'results':
            summary['measurement_selectors'] = {field: selector(source_ref, index, field)
                for field in row if not field.startswith('PUBCHEM_')}
            summary['metadata_required'] = arguments['aid']
    return summary


def _brenda_links(raw, *, parser=None):
    results, seen = [], set()
    for link in (parser if parser is not None else _html(raw)).links:
        url = urljoin('https://www.brenda.dsmz.de/', link['href'])
        parts = urlsplit(url)
        if parts.hostname not in ('www.brenda.dsmz.de', 'brenda.dsmz.de', 'www.brenda-enzymes.org'):
            continue
        q = parse_qs(parts.query)
        args = None
        if parts.path.endswith('/literature.php') and q.get('e') and q.get('r', [''])[0].isdigit():
            args = {'ec_number': q['e'][0], 'reference_id': int(q['r'][0])}
        elif parts.path.endswith('/enzyme.php') and q.get('ecno'):
            args = {'ec_number': q['ecno'][0]}
        if args is not None and json.dumps(args, sort_keys=True) not in seen:
            seen.add(json.dumps(args, sort_keys=True))
            results.append({'label': ' '.join(link['text'].split()), 'url': url, 'read_query': args})
    return results


def _brenda_search_links(parser, arguments):
    """Expose the provider's category-result links as selected search actions."""
    from .experimental_database_acquisition import BRENDA_FIELDS
    fields = {str(value): name for name, value in BRENDA_FIELDS.items()}
    results, seen = [], set()
    for link in parser.links:
        url = urljoin('https://www.brenda.dsmz.de/', link['href'])
        parts = urlsplit(url)
        q = parse_qs(parts.query)
        field = fields.get(q.get('a', [''])[0])
        if (parts.hostname not in ('www.brenda.dsmz.de', 'brenda.dsmz.de', 'www.brenda-enzymes.org')
                or not parts.path.endswith('/fulltext.php') or q.get('showhits') != ['1']
                or q.get('stype') != ['2'] or not q.get('Searchterm') or field is None):
            continue
        query = {'query': q['Searchterm'][0], 'result_field': field,
                 'include_text_mining': q.get('include_tm', [''])[0] in ('on', '1')}
        selected_fields = [fields[value] for key, values in q.items()
                           if key.startswith('tables[') for value in values if value in fields]
        if selected_fields:
            query['fields'] = list(dict.fromkeys(selected_fields))
        if 'max_bytes' in arguments:
            query['max_bytes'] = arguments['max_bytes']
        key = json.dumps(query, sort_keys=True)
        if key not in seen:
            seen.add(key)
            results.append({'label': ' '.join(link['text'].split()),
                            'url': url, 'search_query': query})
    return results


def project(raw, operation, arguments, source_ref, *, offset=0, limit=10, contains=None,
            contains_all=None):
    provider = operation.split('.')[1]
    html_parser = _html(raw) if provider == 'brenda' and operation != 'public.brenda.graph_search' else None
    rows = html_parser.rows if html_parser is not None else native_rows(raw, operation, arguments)
    terms = ([contains] if contains is not None else []) + list(contains_all or ())
    selected = []
    for index, row in enumerate(rows):
        searchable = json.dumps(row, ensure_ascii=False).casefold() if terms else ''
        if all(term.casefold() in searchable for term in terms):
            selected.append((index, row))
    page = selected[offset:offset + limit]
    result = {'records': [summarize(row, index, operation, arguments, source_ref) for index, row in page],
              'retained_record_count': len(rows), 'matching_retained_records': len(selected),
              'next_records_query': ({'source_ref': source_ref, 'offset': offset + len(page),
                    'limit': limit, **({'contains': contains} if contains else {}),
                    **({'contains_all': contains_all} if contains_all else {})}
                    if offset + len(page) < len(selected) else None),
              'next_query': None, 'reported_total': None}
    if operation == 'public.brenda.graph_search':
        result['graph_variables'] = json.loads(raw)['head']['vars']
        result['coverage'] = 'selected prototype knowledge-graph query/page; discovery metadata, not kinetic measurements or exhaustive coverage'
        if len(rows) == arguments.get('limit', 10):
            result['next_query'] = {**arguments, 'offset': arguments.get('offset', 0) + len(rows)}
        return result
    if provider == 'brenda':
        links = _brenda_links(raw, parser=html_parser)
        result['record_links'] = links[offset:offset + limit]
        result['retained_link_count'] = len(links)
        result['record_links_scope'] = 'whole retained page; record text filters apply only to records'
        result['search_result_queries'] = _brenda_search_links(html_parser, arguments)
        result['next_links_query'] = ({'source_ref': source_ref, 'offset': offset + limit, 'limit': limit}
                                     if offset + limit < len(links) else None)
        result['coverage'] = 'retained_public_page; no exhaustive database absence claim'
        result['text_decoding'] = html_parser.decoding
        return result
    if arguments.get('section') in ('results', 'scores', 'counts'):
        if provider == 'mavedb' and len(rows) == arguments.get('limit', 100):
            result['next_query'] = {**arguments, 'offset': arguments.get('offset', 0) + len(rows)}
        result['coverage'] = 'retained result rows; scores and counts require matching assay metadata'
        return result
    data = json.loads(raw)
    next_args = None
    if provider == 'sabiork':
        meta = data['meta']
        result['reported_total'] = meta['total_count']
        if operation.endswith('.search') and meta['page'] < meta['total_pages']:
            next_args = {**arguments, 'page': meta['page'] + 1}
    elif provider == 'chembl' and 'page_meta' in data:
        meta = data['page_meta']
        result['reported_total'] = meta.get('total_count')
        if meta.get('next'):
            q = parse_qs(urlsplit(meta['next']).query)
            next_args = {**arguments, 'offset': int(q['offset'][0])}
    elif provider == 'mavedb' and operation.endswith('.search'):
        result['reported_total'] = data['numScoreSets']
        end = arguments.get('offset', 0) + len(rows)
        if end < data['numScoreSets']:
            next_args = {**arguments, 'offset': end}
    elif provider == 'bioassay' and operation.endswith('.search'):
        meta = data['esearchresult']
        result['reported_total'] = int(meta['count'])
        end = int(meta['retstart']) + len(rows)
        if end < int(meta['count']):
            next_args = {**arguments, 'offset': end}
        result['query_translation'] = meta.get('querytranslation')
        result['provider_warnings'] = meta.get('warninglist')
    result['next_query'] = next_args
    result['coverage'] = 'selected provider query and page'
    return result


def source_request(store, source):
    try:
        payload = json.loads(store.get_artifact(source['request_ref']))['request']
        operation, arguments = payload['operation'], payload['arguments']
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError('experimental_database_request_unavailable') from error
    if source['provider'] != 'experimental.' + operation.split('.')[1]:
        raise ContractError('experimental_database_source_provider_mismatch')
    return operation, arguments


def read_records(registry, arguments, scope, permitted_inputs):
    artifact = received_source(registry.store, arguments['source_ref'], 'original',
                               permitted_inputs=permitted_inputs, scope=scope)
    source = registry.store.get(arguments['source_ref'])
    operation, selected = source_request(registry.store, source)
    payload = json.loads(registry.store.get_artifact(source['request_ref']))
    transport = payload['transport']
    response = transport.get('response', transport)
    if response.get('status') != 200 or response.get('body_complete') is not True:
        raise ContractError('experimental_database_complete_successful_source_required')
    result = project(registry.store.get_artifact(artifact['id']), operation, selected, source['id'],
                     offset=arguments.get('offset', 0), limit=arguments.get('limit', 10),
                     contains=arguments.get('contains'), contains_all=arguments.get('contains_all'))
    return {'version': 'experimental_database_records_v1', 'provider': operation.split('.')[1],
            'source_ref': source['id'], 'artifact_ref': artifact['id'], **result}, []
