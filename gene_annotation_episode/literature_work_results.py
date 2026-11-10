"""Purpose-specific results of the literature episode's completed own actions.

Only the original returned JSON enters these views. No Source is opened, no
scientific fact is inferred and no score, receipt or continuation is changed.
Search citations remain discovery metadata; deposited quantities remain the
original reported measurements, not an additional evidence assessment.
"""
from collections.abc import Mapping
from copy import deepcopy


DISCOVERY_TOOLS = (
    'public.literature.sequence_identity', 'source.sequence.references',
    'public.literature.search', 'public.ncbi.search', 'source.experimental.records',
)
DATABASE_PREFIXES = ('public.sabiork.', 'public.brenda.', 'public.bioassay.',
                     'public.chembl.', 'public.mavedb.')
_RECEIPT_FIELDS = (
    'source_ref', 'artifact_ref', 'subject_ref', 'sheet_ref', 'provider', 'status',
    'reason', 'http_status', 'capture_complete', 'captured_bytes', 'source_format',
    'representation', 'offset', 'end', 'returned_bytes', 'total_bytes', 'has_more',
    'scanned_range', 'retained_record_count', 'matching_retained_records',
    'reported_total', 'coverage', 'next_query', 'next_records_query',
    'read_query', 'records_query', 'projection_failure', 'text_decoding',
)
_CITATION_FIELDS = ('reference_index', 'source_pointer', 'citation_type', 'title',
    'date', 'journal', 'identifiers', 'reported_scope', 'reported_source')
_SEARCH_HIT_FIELDS = ('source', 'id', 'pmid', 'pmcid', 'doi', 'title',
    'authorString', 'journalTitle', 'pubYear', 'firstPublicationDate',
    'isOpenAccess', 'inPMC', 'hasPDF', 'hasSuppl', 'fullTextUrlList')


def _keep(value, fields):
    return {name: deepcopy(value[name]) for name in fields if name in value}


def _organism(value):
    return (_keep(value, ('scientificName', 'taxonId', 'name', 'ncbi_taxonomy_id'))
            if isinstance(value, Mapping) else deepcopy(value))


def _sequence_match(row):
    result = _keep(row, ('record_index', 'accession', 'entry_id', 'entry_type',
        'protein_names', 'gene_names', 'ec_numbers', 'citation_count',
        'experimental_database_links', 'sequence_comparison', 'references_query'))
    if 'organism' in row:
        result['organism'] = _organism(row['organism'])
    return result


def _experimental_record(provider, row):
    """Retain each provider's actual molecule, endpoint and condition fields."""
    if not isinstance(row, Mapping):
        return deepcopy(row)
    if provider == 'sabiork':
        result = _keep(row, ('record_index', 'id', 'enzyme_description',
            'experimental_conditions', 'publication', 'read_query'))
        general = row.get('general')
        if isinstance(general, Mapping):
            result['general'] = _keep(general, ('experiment_type', 'strain',
                'tissue', 'publication_id', 'comment'))
            if 'organism' in general:
                result['general']['organism'] = _organism(general['organism'])
        reaction = row.get('reaction')
        if isinstance(reaction, Mapping):
            result['reaction'] = _keep(reaction, ('equation',))
            result['reaction']['species'] = [_keep(species, ('compound', 'role',
                'stoch_value', 'protein_complex_names')) for species in reaction.get('species', ())]
        result['parameters'] = [_keep(parameter, ('name', 'parameter_type',
            'role', 'start_value', 'end_value', 'unit', 'standard_deviation',
            'species', 'comment', 'measurement_selector')) for parameter in row.get('parameters', ())]
        return result
    if provider == 'brenda':
        return _keep(row, ('record_index', 'section', 'table_id', 'headers',
            'columns', 'bindings', 'values', 'links', 'read_query', 'html_location'))
    if provider == 'chembl':
        result = deepcopy(dict(row))
        if isinstance(row.get('target_components'), (list, tuple)):
            result['target_components'] = [_keep(component, ('accession',
                'component_type', 'component_description', 'organism'))
                for component in row['target_components']]
        return result
    if provider == 'mavedb' and 'measurement_selectors' not in row and 'metadata_required' not in row:
        # Metadata identifies the score population and source definition. Full
        # abstract/method text remains in the acquired source, not every history row.
        result = _keep(row, ('record_index', 'urn', 'title', 'shortDescription',
            'numVariants', 'datasetColumns', 'primaryPublicationIdentifiers',
            'secondaryPublicationIdentifiers', 'metaAnalyzesScoreSetUrns',
            'scoreCalibrations', 'read_query'))
        if isinstance(row.get('targetGenes'), (list, tuple)):
            result['targetGenes'] = [_keep(gene, ('name', 'category', 'organism',
                'targetAccession', 'externalIdentifiers')) for gene in row['targetGenes']]
        return result
    # BioAssay description/readout rows and MaveDB score/count rows have native
    # named columns. They were already projected by their purpose-specific reader.
    # Keep every selected column and its original measurement address together.
    return deepcopy(dict(row))


def returned_result(tool, value):
    """Present facts actually returned by this one original selection."""
    tool = tool if isinstance(tool, str) else ''
    if not isinstance(value, Mapping):
        return deepcopy(value)
    result = _keep(value, _RECEIPT_FIELDS)
    if tool not in DISCOVERY_TOOLS and not tool.startswith(DATABASE_PREFIXES):
        # The narrow SQL metadata projection supplies null for absent fields;
        # those placeholders are not additional reported source facts.
        result = {name: child for name, child in result.items() if child is not None}
    if tool == 'public.literature.sequence_identity':
        result.update(_keep(value, ('query_length', 'returned_records', 'total_results',
            'pagination_metadata_available', 'rejected_records',
            'ambiguous_residue_symbols', 'experimental_assessment', 'qualification')))
        result['sequence_matches'] = [_sequence_match(row) for row in value.get('matches', ())]
    elif tool == 'source.sequence.references':
        result.update(_keep(value, ('total_references', 'qualification')))
        if isinstance(value.get('record'), Mapping):
            result['selected_sequence_record'] = _sequence_match(value['record'])
        result['citation_leads'] = [_keep(row, _CITATION_FIELDS)
            for row in value.get('references', ())]
    elif tool == 'public.literature.search':
        native = value.get('provider_result')
        if isinstance(native, Mapping):
            if native.get('error') or native.get('errors'):
                result['returned_provider_error'] = deepcopy(native)
            result.update(_keep(native, ('hitCount', 'nextCursorMark', 'nextPageUrl', 'request')))
            rows = native.get('resultList', {}).get('result', ())
            result['search_hits'] = [_keep(row, _SEARCH_HIT_FIELDS) for row in rows]
    elif tool == 'public.ncbi.search':
        native = value.get('provider_result')
        if isinstance(native, Mapping):
            if native.get('error') or native.get('errors'):
                result['returned_provider_error'] = deepcopy(native)
            search = native.get('esearchresult')
            if isinstance(search, Mapping):
                result['ncbi_search_results'] = _keep(search, ('count', 'retstart',
                    'retmax', 'idlist', 'querytranslation', 'warninglist', 'errorlist'))
    elif (tool == 'source.experimental.records' or tool.startswith(DATABASE_PREFIXES)):
        provider = value.get('provider')
        result.update(_keep(value, ('qualification', 'graph_variables',
            'record_links', 'record_links_scope', 'retained_link_count',
            'search_result_queries', 'next_links_query', 'query_translation',
            'provider_warnings')))
        result['returned_database_records'] = [_experimental_record(provider, row)
            for row in value.get('records', ())]
    elif tool == 'episode.history':
        # Original result-bearing action rows remain above. Repeating their
        # full payload inside each history receipt would obscure the actual work.
        result.update({name: deepcopy(value[name]) for name in
            ('view', 'total', 'has_more', 'unavailable_reasons')
            if name in value and value[name] is not None})
    if isinstance(value.get('cells'), (list, tuple)):
        # These are the original purpose-specific scientific return cells,
        # not provider/file bodies. Retain their custom criteria, intervals,
        # identities and conditions rather than imposing a generic cell view.
        result['saved_components'] = deepcopy(value['cells'])
    return result


def original_json_sql(path):
    """Keep the JSON type of one retained outcome field, including strings."""
    location = "'" + path + "'"
    return ("CASE WHEN json_type(a.result," + location + ") IS NULL THEN NULL "
        "WHEN json_type(a.result," + location + ")='true' THEN 'true' "
        "WHEN json_type(a.result," + location + ")='false' THEN 'false' "
        "ELSE json_quote(json_extract(a.result," + location + ")) END")


def result_projection_sql():
    """Fetch rich discovery results while excluding original page/file bodies."""
    tools = ','.join("'" + name + "'" for name in DISCOVERY_TOOLS)
    selected = 'json_extract(a.action,\'$.tool\')'
    rich = [selected + ' IN (' + tools + ')',
        *(selected + " LIKE '" + prefix + "%'" for prefix in DATABASE_PREFIXES)]
    body = "json_extract(a.result,'$.result')"
    fields = (*_RECEIPT_FIELDS, 'cells', 'view', 'total', 'unavailable_reasons')
    projection = 'json_object(' + ','.join("'" + name + "',json(" + original_json_sql('$.result.' + name) + ')'
        for name in fields) + ')'
    return 'CASE WHEN ' + ' OR '.join(rich) + ' THEN ' + body + ' ELSE ' + projection + ' END'
