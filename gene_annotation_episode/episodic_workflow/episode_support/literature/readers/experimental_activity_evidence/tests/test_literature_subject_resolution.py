"""Subject resolution: offline tests over fake providers and a fake scoped store; the live tests call the public services
and run only when PUBLIC_SERVICE_TESTS=1 (so the offline suite skips them)."""
import hashlib
import json
import os
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from gene_annotation_episode.acquisition_types import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence import literature_subject_resolution as module
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_subject_resolution import resolve_subject

live = pytest.mark.skipif(os.environ.get('PUBLIC_SERVICE_TESTS') != '1', reason='calls a public service')


class FakeStore:
    def __init__(self):
        self.records, self.artifacts = {}, {}

    def put(self, kind, record, *, origin, scope=None):
        key = kind + '_' + hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:24]
        self.records[key] = {'id': key, 'record_type': kind, **record}
        return self.records[key]

    def artifact(self, data, media_type='application/octet-stream'):
        data = data.encode() if isinstance(data, str) else data
        key = 'artifact_' + hashlib.sha256(data).hexdigest()[:24]
        self.artifacts[key] = data
        return key


def snapshot(body, service='x'):
    return SourceSnapshot(service, 'https://example.org/x', {}, '2026-11-21T00:00:00+00:00', json.dumps(body).encode(),
                          'application/json', {'status': 200})


def uniprot_row(accession, sequence, name='Protein', organism='Org one'):
    return {'primaryAccession': accession, 'sequence': {'value': sequence}, 'organism': {'scientificName': organism},
            'proteinDescription': {'recommendedName': {'fullName': {'value': name}}}}


class FakeClients:
    def __init__(self, rows=(), missing=False):
        self.rows, self.missing, self.calls = list(rows), missing, []

    def uniprot_record(self, accession):
        self.calls.append(('record', accession))
        if self.missing:
            raise AcquisitionError('provider_http_404')
        return snapshot(self.rows[0], 'uniprot')

    def uniprot_search(self, query, *, size):
        self.calls.append(('search', query, size))
        return snapshot({'results': self.rows}, 'uniprot')


def resolve(clients, store=None, bvbrc_docs=(), organism_genomes=([], False), **given):
    """``bvbrc_docs`` are the feature rows every BV-BRC feature query returns; ``organism_genomes`` is what the organism
    lookup returns; the queries sent are kept in ``resolve.queries``."""
    arguments = {'name': None, 'database_id': None, 'database': None, 'organism': None, **given}
    resolve.queries = []

    def query(filters, genome_ids=None):
        resolve.queries.append((filters, genome_ids))
        return snapshot({}, 'bvbrc_data'), list(bvbrc_docs)
    with patch.object(module, '_clients', lambda: clients), patch.object(module, '_bvbrc_query', query), \
            patch.object(module, '_bvbrc_organism', lambda organism: organism_genomes), \
            patch.object(module, '_bvbrc_sequences', lambda md5s: {md5: SEQUENCE for md5 in md5s}):
        return resolve_subject(store or FakeStore(), **arguments)


SEQUENCE = 'MKVL'
SEQUENCE_MD5 = hashlib.md5(SEQUENCE.encode()).hexdigest()


def feature(patric_id, product='Polar protein'):
    return {'patric_id': patric_id, 'aa_sequence_md5': SEQUENCE_MD5, 'product': product, 'genome_id': '1.1'}


def test_database_id_fetches_the_record_and_stores_it_with_its_sequence():
    store = FakeStore()
    result = resolve(FakeClients([uniprot_row('A0A0H3C7Y4', 'MKV')]), store, name='x', database_id='A0A0H3C7Y4', database='uniprot')
    assert (result['resolution'], result['match_count'], result['provider']) == ('database_id', 1, 'uniprot')
    record = store.records[result['record_ref']]
    assert (record['accession'], record['length'], record['sequence_ref']) == ('A0A0H3C7Y4', 3, result['sequence_ref'])
    assert store.artifacts[result['sequence_ref']] == b'MKV'


def test_a_name_with_one_match_is_unique_and_several_matches_are_all_kept():
    unique = resolve(FakeClients([uniprot_row('P00001', 'MKV')]), name='PopZ', organism='Org one')
    assert (unique['resolution'], unique['match_count']) == ('name_unique', 1)
    several = resolve(FakeClients([uniprot_row('P00001', 'MKV'), uniprot_row('P00002', 'MKW')]), name='PopZ')
    assert (several['resolution'], several['match_count'], len(several['candidates'])) == ('name_ambiguous', 2, 2)
    assert several['record_ref'] == several['candidates'][0]['record_ref']


def test_the_same_sequence_found_twice_is_one_match():
    result = resolve(FakeClients([uniprot_row('P00001', 'MKV'), uniprot_row('P00002', 'MKV')]), name='PopZ')
    assert (result['resolution'], result['match_count']) == ('name_unique', 1)


def test_nothing_found_is_unresolved_with_its_own_value_not_an_error():
    result = resolve(FakeClients([]), name='NoSuchProtein', organism='Org one')
    assert result == {'record_ref': None, 'sequence_ref': None, 'resolution': 'unresolved', 'match_count': 0,
                      'provider': None, 'candidates': []}
    assert resolve(FakeClients([]))['resolution'] == 'unresolved'


def test_an_id_the_provider_does_not_hold_goes_on_to_the_name():
    clients = FakeClients([uniprot_row('P00001', 'MKV')], missing=True)
    result = resolve(clients, name='PopZ', database_id='P12345', database='uniprot')
    assert result['resolution'] == 'name_unique' and [call[0] for call in clients.calls] == ['record', 'search']


def test_an_id_of_the_wrong_shape_is_not_sent_to_the_provider():
    clients = FakeClients([])
    assert resolve(clients, database_id='not an accession', database='uniprot')['resolution'] == 'unresolved'
    assert clients.calls == []


def test_a_provider_failure_raises():
    class Broken(FakeClients):
        def uniprot_search(self, query, *, size):
            raise AcquisitionError('provider_http_500')
    with pytest.raises(AcquisitionError):
        resolve(Broken(), name='PopZ')


def test_bvbrc_features_are_collapsed_by_sequence_and_their_sequence_checked_by_md5():
    sequence = 'MKVL'
    md5 = hashlib.md5(sequence.encode()).hexdigest()
    docs = [{'patric_id': 'fig|1.2.peg.2', 'aa_sequence_md5': md5, 'product': 'Polar protein', 'genome_name': 'G2'},
            {'patric_id': 'fig|1.1.peg.2', 'aa_sequence_md5': md5, 'product': 'Polar protein', 'genome_name': 'G1'}]
    store = FakeStore()
    with patch.object(module, '_bvbrc_sequences', lambda md5s: {md5: sequence}):
        candidates = module._bvbrc_candidates(store, snapshot({}, 'bvbrc_data'), docs)
    assert len(candidates) == 1 and store.records[candidates[0]['record_ref']]['accession'] == '1.1.peg.2'


def test_a_locus_tag_is_looked_up_in_bvbrc_within_the_stated_organism():
    result = resolve(FakeClients([]), bvbrc_docs=[feature('fig|1.1.peg.5')], organism_genomes=(['1.1', '1.2'], True),
                     database_id='CCNA_01381', database='locus_tag', organism='Caulobacter vibrioides NA1000')
    assert (result['resolution'], result['match_count'], result['provider']) == ('database_id', 1, 'bvbrc')
    assert resolve.queries == [([{'field': 'refseq_locus_tag', 'operator': 'eq', 'value': 'CCNA_01381'}], ['1.1', '1.2'])]


def test_a_locus_tag_without_an_organism_is_not_restricted_and_falls_to_the_alternate_tag():
    calls = []

    def query(filters, genome_ids=None):
        calls.append((filters[0]['field'], genome_ids))
        return snapshot({}, 'bvbrc_data'), ([feature('fig|1.1.peg.5')] if filters[0]['field'] == 'alt_locus_tag' else [])
    with patch.object(module, '_bvbrc_query', query), patch.object(module, '_bvbrc_sequences', lambda md5s: {md5s[0]: SEQUENCE}):
        result = resolve_subject(FakeStore(), name=None, database_id='CC_1319', database='locus_tag', organism=None)
    assert calls == [('refseq_locus_tag', None), ('alt_locus_tag', None)] and result['match_count'] == 1


def test_a_name_with_a_bacterial_organism_is_looked_up_in_uniprot_and_in_bvbrc_by_gene_and_product():
    result = resolve(FakeClients([uniprot_row('P00001', SEQUENCE)]), bvbrc_docs=[feature('fig|1.1.peg.5')],
                     organism_genomes=(['1.1'], True), name='popZ', organism='Caulobacter vibrioides NA1000')
    assert [query[0][0]['field'] for query in resolve.queries] == ['gene', 'product']
    assert all(query[0][0]['value'] == 'popZ' and query[1] == ['1.1'] for query in resolve.queries)
    assert (result['resolution'], result['match_count']) == ('name_unique', 1)     # the same sequence in UniProt and BV-BRC


def test_a_name_with_a_non_bacterial_organism_or_no_organism_is_not_sent_to_bvbrc():
    resolve(FakeClients([]), organism_genomes=([], False), name='Tp53', organism='Homo sapiens')
    assert resolve.queries == []
    resolve(FakeClients([]), organism_genomes=(['1.1'], True), name='recA')
    assert resolve.queries == []


def test_the_copy_of_the_query_layer_allows_phrase_filters_on_text_fields_and_builds_the_native_request():
    from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import literature_bvbrc_query as query
    request = {'version': 'bvbrc_data_request_v2', 'collection': 'genome_feature', 'mode': 'page', 'limit': 5,
               'filters': [{'field': 'gene', 'operator': 'eq', 'value': 'recA'},
                           {'field': 'genome_id', 'operator': 'in', 'value': ['83333.1']}], 'fields': ['patric_id']}
    prepared = query.encode_native_query(request, base_url='https://www.bv-brc.org/api')
    assert prepared['native_request']['url'].startswith('https://www.bv-brc.org/api/genome_feature/?q=')
    assert dict((p['name'], p['value']) for p in prepared['native_request']['query_parameters'])['q'] == \
        '(gene:"recA") AND (genome_id:("83333.1"))'
    with pytest.raises(Exception, match='bvbrc_exact_filter_field_not_supported'):     # a raw-text field stays refused
        query.validate_data_query({**request, 'collection': 'feature_sequence', 'fields': ['md5'],
                                   'filters': [{'field': 'sequence', 'operator': 'eq', 'value': 'x'}]})


@live
def test_live_bvbrc_locus_tag_and_gene_name_in_organism():
    store = FakeStore()
    for label, given in (
            ('CCNA_01381 Caulobacter', dict(name=None, database_id='CCNA_01381', database='locus_tag', organism='Caulobacter vibrioides NA1000')),
            ('CC_1319 Caulobacter', dict(name=None, database_id='CC_1319', database='locus_tag', organism=None)),
            ('b2699 E. coli', dict(name=None, database_id='b2699', database='locus_tag', organism='Escherichia coli K-12')),
            ('popZ in Caulobacter', dict(name='popZ', database_id=None, database=None, organism='Caulobacter vibrioides NA1000')),
            ('recA in E. coli K-12', dict(name='recA', database_id=None, database=None, organism='Escherichia coli K-12'))):
        result = resolve_subject(store, **given)
        print('LIVE', label, {key: result[key] for key in ('resolution', 'match_count', 'provider')})
        for candidate in result['candidates']:
            record = store.records[candidate['record_ref']]
            print('   ', candidate['provider'], record['accession'], record['label'], record['length'])
        assert result['match_count'] >= 1


@live
def test_live_uniprot_accession_and_name():
    store = FakeStore()
    by_id = resolve_subject(store, name=None, database_id='A0A0H3C7Y4', database='uniprot', organism=None)
    print('LIVE uniprot id:', {key: by_id[key] for key in ('resolution', 'match_count', 'provider')})
    assert by_id['resolution'] == 'database_id' and by_id['sequence_ref']
    by_name = resolve_subject(store, name='PopZ', database_id=None, database=None, organism='Caulobacter vibrioides')
    print('LIVE name:', {key: by_name[key] for key in ('resolution', 'match_count', 'provider')}, [c['provider'] for c in by_name['candidates']])
    assert by_name['match_count'] >= 1


@live
def test_live_ncbi_and_bvbrc():
    store = FakeStore()
    ncbi = resolve_subject(store, name=None, database_id='NP_414542.1', database='refseq', organism=None)
    print('LIVE ncbi:', {key: ncbi[key] for key in ('resolution', 'match_count', 'provider')})
    assert ncbi['provider'] == 'ncbi' and ncbi['sequence_ref']
    bvbrc = resolve_subject(store, name=None, database_id='fig|83332.12.peg.1', database='bvbrc', organism=None)
    print('LIVE bvbrc:', {key: bvbrc[key] for key in ('resolution', 'match_count', 'provider')})
    assert bvbrc['provider'] == 'bvbrc'
    tag = resolve_subject(store, name=None, database_id='b0001', database='locus_tag', organism='Escherichia coli K-12')
    print('LIVE locus tag:', {key: tag[key] for key in ('resolution', 'match_count', 'provider')})
    missing = resolve_subject(store, name=None, database_id='P99999', database='uniprot', organism=None)
    print('LIVE uniprot id that is held:', missing['resolution'])
