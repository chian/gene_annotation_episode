"""Resolve the protein a paper identifies to a database record and its sequence.

The leaf records how the paper identifies its protein (a name, a database id with its database, an organism). This module
turns that into a held ``reference`` record that carries the accession, a label and the ``sequence_ref``, so the sequence
can be compared with the target's (``literature_subject_closeness``). Order of resolution:

1. a stated database id with its database -> fetch that record: ``uniprot`` by accession (``uniprot_record``); ``genbank``
   and ``refseq`` protein accessions through the NCBI protein fetch (``ncbi_sequence``); ``bvbrc`` (a feature id) through
   BV-BRC's feature lookup by patric id;
2. a locus tag -> BV-BRC by ``refseq_locus_tag`` then ``alt_locus_tag``, restricted to the organism's genomes when the
   paper states the organism;
3. else the name with an organism: a UniProt search and, when the organism is a bacterium or an archaeon (its BV-BRC
   taxonomy lineage says so), BV-BRC by ``gene`` and by ``product`` within that organism's genomes.
   The organism is restricted through BV-BRC's taxonomy (``taxon_name`` -> taxon id) and the genomes under that taxon
   (``taxon_lineage_ids``); ``genome_feature`` holds no genome name field in the field registry.
   All BV-BRC requests are built by A105's own copy of the query layer (``literature_bvbrc_query``).

Candidates are counted by DISTINCT SEQUENCE (the same protein held by UniProt and by BV-BRC, or by many genomes, is one
candidate). One candidate -> ``database_id`` (id path) or ``name_unique``; several -> ``name_ambiguous`` (a locus tag with no
organism that matches several sequences is also ``name_ambiguous``) with every candidate stored, so the caller compares
each one (``candidates``); none -> ``unresolved`` (a normal outcome, not an exception). A transport or provider failure
raises: it is not an unresolved subject.

Everything is written through the scoped store the episode is handed; nothing here touches the Store directly.
"""
from __future__ import annotations
import hashlib
import json
import re

from gene_annotation_episode.acquisition import parse_genbank
from gene_annotation_episode.acquisition_types import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.experimental_activity_evidence.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_bvbrc import BVBRCDataClient, DEFAULT_BASE_URL
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence.literature_bvbrc_query import encode_native_query

# EXPERT_REVIEW (owner to confirm): at most 25 UniProt results are read for one name. Reason: a name that matches more
# than a handful of distinct proteins is already strongly ambiguous, and 25 is the largest page the existing UniProt
# search tool allows (identity_schema 'size' maximum), so the count cannot exceed what the project already reads.
UNIPROT_NAME_RESULTS = 25
# EXPERT_REVIEW (owner to confirm): at most 100 BV-BRC rows are read for one lookup (feature rows, and the genomes of one
# organism). Reason: the rows of one name are mostly the same protein in many genomes (collapsed by sequence), and 100
# is the batch size A101's BV-BRC reader (bvbrc_hit_metadata.BATCH) already uses against this service.
BVBRC_FEATURE_ROWS = 100
# At most 25 BV-BRC taxonomy rows are read for one organism name (a name matches one taxon, rarely several).
BVBRC_TAXON_ROWS = 25

_UNIPROT_ACCESSION = re.compile(r'^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?:-[0-9]+)?$')
_NCBI_PROTEIN = re.compile(r'^(?:(?:NP|WP|YP|XP|AP)_[0-9]+|[A-Z]{3}[0-9]{5,})(?:\.[0-9]+)?$')
_BVBRC_FEATURE = re.compile(r'^(?:fig\|)?[0-9]+\.[0-9]+\.[A-Za-z]+\.[0-9]+$')
_BVBRC_FIELDS = ['patric_id', 'feature_id', 'product', 'gene', 'genome_id', 'aa_sequence_md5', 'aa_length']
_LOCUS_TAG_FIELDS = ('refseq_locus_tag', 'alt_locus_tag')
_NAME_FIELDS = ('gene', 'product')


def _clients():
    return PublicClients()


def _bvbrc_client():
    return BVBRCDataClient()


def _quoted(text):
    return '"' + text.replace('"', ' ').strip() + '"'


def _source(store, provider, snapshot, accession):
    request = store.artifact(canonical({'request': snapshot.request, 'transport': snapshot.transport}), 'application/json')
    return store.put('source', {'provider': provider, 'accession': accession, 'uri': snapshot.url,
                                'artifact_ref': store.artifact(snapshot.content, snapshot.media_type), 'text_ref': None,
                                'request_ref': request, 'version': None, 'retrieved_at': snapshot.retrieved_at},
                     origin='external')


def _record(store, provider, snapshot, accession, label, sequence):
    source = _source(store, provider, snapshot, None)
    stored = store.put('reference', {
        'reference_type': 'protein', 'source_ref': source['id'], 'accession': accession, 'label': label,
        'sequence_ref': store.artifact(sequence, 'text/plain'), 'molecule': 'protein', 'length': len(sequence),
        'term_refs': [], 'context_refs': []}, origin='external')
    return {'record_ref': stored['id'], 'sequence_ref': stored['sequence_ref'], 'provider': {
        'uniprot': 'uniprot', 'ncbi_entrez': 'ncbi', 'bvbrc_data': 'bvbrc'}[provider],
        'md5': hashlib.md5(sequence.encode('ascii')).hexdigest()}


def _uniprot_label(row):
    description = row.get('proteinDescription', {})
    entry = description.get('recommendedName') or (description.get('submissionNames') or [{}])[0]
    name = entry.get('fullName', {}).get('value') or row['primaryAccession']
    organism = row.get('organism', {}).get('scientificName')
    return name + (' [' + organism + ']' if organism else '')


def _uniprot_candidates(store, snapshot, rows):
    return [_record(store, 'uniprot', snapshot, row['primaryAccession'], _uniprot_label(row), row['sequence']['value'])
            for row in rows]


def _bvbrc_rows(collection, filters, fields, limit=BVBRC_FEATURE_ROWS):
    request = {'version': 'bvbrc_data_request', 'collection': collection, 'mode': 'page',
               'filters': filters, 'fields': fields, 'limit': limit, 'offset': 0}
    snapshot = _bvbrc_client().query_prepared(encode_native_query(request, base_url=DEFAULT_BASE_URL))
    return snapshot, json.loads(snapshot.content)['response']['docs']


def _bvbrc_organism(organism):
    """``(genome_ids, prokaryote)`` of a stated organism: its BV-BRC taxonomy rows by ``taxon_name`` (a whole-name,
    case-insensitive match), whether their lineage holds Bacteria or Archaea, and the genomes under those taxa."""
    _, taxa = _bvbrc_rows('taxonomy', [{'field': 'taxon_name', 'operator': 'eq', 'value': organism}],
                          ['taxon_id', 'lineage_names'], BVBRC_TAXON_ROWS)
    if not taxa:
        return [], False
    prokaryote = any(name in ('Bacteria', 'Archaea') for taxon in taxa for name in taxon.get('lineage_names') or [])
    _, genomes = _bvbrc_rows('genome', [{'field': 'taxon_lineage_ids', 'operator': 'in',
                                         'value': [taxon['taxon_id'] for taxon in taxa]}], ['genome_id'])
    return [genome['genome_id'] for genome in genomes], prokaryote


def _bvbrc_query(filters, genome_ids=None):
    """The ``genome_feature`` rows matching ``filters`` (``(snapshot, docs)``), within ``genome_ids`` when they are given
    (an organism stated but with no genome in BV-BRC: an empty list, so no rows and no feature request)."""
    if genome_ids is not None:
        if not genome_ids:
            return None, []
        filters = filters + [{'field': 'genome_id', 'operator': 'in', 'value': genome_ids}]
    return _bvbrc_rows('genome_feature', filters, _BVBRC_FIELDS)


def _bvbrc_sequences(md5s):
    client = _bvbrc_client()
    request = {'version': 'bvbrc_data_request', 'collection': 'feature_sequence', 'mode': 'page',
               'filters': [{'field': 'md5', 'operator': 'in', 'value': md5s}],
               'fields': ['md5', 'sequence_type', 'sequence'], 'limit': max(len(md5s) * 4, 25), 'offset': 0}
    snapshot = client.query_prepared(encode_native_query(request, base_url=DEFAULT_BASE_URL))
    found = {}
    for row in json.loads(snapshot.content)['response']['docs']:
        # The sequence must be the one its md5 names (the A101 reader's own check).
        if hashlib.md5(row['sequence'].encode('ascii')).hexdigest() != row['md5']:
            raise ValueError('bvbrc_sequence_does_not_match_its_md5:' + row['md5'])
        found[row['md5']] = row['sequence']
    return found


def _bvbrc_candidates(store, snapshot, docs):
    """One candidate per distinct protein sequence: the first feature (by patric id) that carries it."""
    first = {}
    for doc in sorted((d for d in docs if d.get('aa_sequence_md5') and d.get('patric_id')), key=lambda d: d['patric_id']):
        first.setdefault(doc['aa_sequence_md5'], doc)
    if not first:
        return []
    sequences = _bvbrc_sequences(sorted(first))
    candidates = []
    for md5, doc in first.items():
        label = (doc.get('product') or doc.get('gene') or doc['patric_id']) + \
            (' [genome ' + doc['genome_id'] + ']' if doc.get('genome_id') else '')
        candidates.append(_record(store, 'bvbrc_data', snapshot, doc['patric_id'].removeprefix('fig|'), label, sequences[md5]))
    return candidates


def _by_database_id(store, database_id, database, organism):
    """The candidates of a stated database id, or [] when the id is not of the stated database's shape or the provider
    does not hold it."""
    if database == 'uniprot':
        if not _UNIPROT_ACCESSION.fullmatch(database_id):
            return []
        try:
            snapshot = _clients().uniprot_record(database_id)
        except AcquisitionError as error:
            if error.code in ('provider_http_404', 'provider_http_400'):
                return []
            raise
        return _uniprot_candidates(store, snapshot, [json.loads(snapshot.content)])
    if database in ('genbank', 'refseq'):
        if not _NCBI_PROTEIN.fullmatch(database_id):
            return []
        try:
            snapshot = _clients().ncbi_sequence(database_id, database='protein')
        except AcquisitionError as error:
            if error.code in ('provider_http_404', 'provider_http_400'):
                return []
            raise
        return [_record(store, 'ncbi_entrez', snapshot, row['accession'], row['description'], row['sequence'])
                for row in parse_genbank(snapshot.content) if row['sequence_available']]
    if database == 'bvbrc':
        if not _BVBRC_FEATURE.fullmatch(database_id):
            return []
        value = database_id if database_id.startswith('fig|') else 'fig|' + database_id
        snapshot, docs = _bvbrc_query([{'field': 'patric_id', 'operator': 'eq', 'value': value}])
        return _bvbrc_candidates(store, snapshot, docs)
    if database == 'locus_tag':
        genome_ids = _bvbrc_organism(organism)[0] if organism else None
        for field in _LOCUS_TAG_FIELDS:          # the lookup order: RefSeq's locus tag, then the alternate tag
            snapshot, docs = _bvbrc_query([{'field': field, 'operator': 'eq', 'value': database_id}], genome_ids)
            if docs:
                return _bvbrc_candidates(store, snapshot, docs)
        return []
    return []


def _by_name(store, name, organism):
    """UniProt by name (with the organism); and, for a bacterial or archaeal organism, BV-BRC by gene name and by product
    name within the organism's genomes."""
    quoted = _quoted(name)
    query = '(gene:' + quoted + ' OR protein_name:' + quoted + ')' + \
        (' AND organism_name:' + _quoted(organism) if organism else '')
    snapshot = _clients().uniprot_search(query, size=UNIPROT_NAME_RESULTS)
    candidates = _uniprot_candidates(store, snapshot, json.loads(snapshot.content)['results'])
    if organism:
        genome_ids, prokaryote = _bvbrc_organism(organism)
        if prokaryote:
            for field in _NAME_FIELDS:
                snapshot, docs = _bvbrc_query([{'field': field, 'operator': 'eq', 'value': name}], genome_ids)
                candidates += _bvbrc_candidates(store, snapshot, docs)
    return candidates


def _distinct(candidates):
    """One candidate per distinct sequence, in the order found (UniProt first)."""
    seen, result = set(), []
    for candidate in candidates:
        if candidate['md5'] not in seen:
            seen.add(candidate['md5'])
            result.append(candidate)
    return result


def resolve_subject(store, *, name, database_id, database, organism):
    """The reference record and sequence of the protein a paper identifies: ``{'record_ref', 'sequence_ref',
    'resolution', 'match_count', 'provider', 'candidates'}``. ``candidates`` lists every distinct-sequence record found
    (``record_ref``, ``sequence_ref``, ``provider``); ``record_ref`` and ``sequence_ref`` are the first one's (the only one
    unless ``resolution`` is ``name_ambiguous``) and are None when ``resolution`` is ``unresolved``."""
    candidates, resolution = [], None
    if database_id and database:
        candidates = _distinct(_by_database_id(store, database_id, database, organism))
        resolution = 'database_id' if len(candidates) == 1 else None
    if not candidates and name:
        candidates = _distinct(_by_name(store, name, organism))
        resolution = 'name_unique' if len(candidates) == 1 else None
    if not candidates:
        resolution = 'unresolved'
    elif resolution is None:
        resolution = 'name_ambiguous'
    shown = [{key: candidate[key] for key in ('record_ref', 'sequence_ref', 'provider')} for candidate in candidates]
    return {'record_ref': shown[0]['record_ref'] if shown else None, 'sequence_ref': shown[0]['sequence_ref'] if shown else None,
            'resolution': resolution, 'match_count': len(shown), 'provider': shown[0]['provider'] if shown else None,
            'candidates': shown}
