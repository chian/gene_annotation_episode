"""The papers a database lists for a record: offline over canned UniProt responses held in a small in-memory store with
the scoped store's read and write names, and one test of the real UniProt service (marked ``model_run``, the marker the
offline suite excludes; it sends no personal data and uses the client's generic request)."""
import hashlib
import json

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_record_publications import (
    RESOLVE_BATCH, listed_without_full_text, merge_listed, record_publications, resolve_queries, target_record_refs,
    with_full_text)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    hit_candidate, ranked_hits)

SEQUENCE = 'MAIDENKQKALAAALGQIEKQFGKGSIMRLGEDRSMDVETISTGSLSLDIALGAGGLPMGRIVEIYGPESSGKTTLTLQVIAAAQREGKTCAFIDAEHALDPIYARKLGVDIDNLLCSQPDTGEQALEICDALARSGAVDVIVVDSVAALTPKAEIEGEIGDSHMGLAARMMSQAMRKLAGNLKQSNTLLIFINQIRMKIGVMFGNPETTTGGNALKFYASVRLDIRRIGAVKEGENVVGSETRVKVVKNKIAAPFKQAEFQILYGEGINFYGELVDLGVKEKLIEKAGAWYSYKGEKIGQGKANATAWLKDNPETAKEIEKKVRELLLSNPNSTPDFSVDDSEGVAETNEDF'


def entry(accession='P0A7G6', references=None, sequence=SEQUENCE):
    return {'primaryAccession': accession, 'uniProtkbId': 'RECA_ECOLI', 'sequence': {'value': sequence},
            'proteinDescription': {'recommendedName': {'fullName': {'value': 'Protein RecA'}}},
            'references': references if references is not None else [
                {'referencePositions': 'FUNCTION', 'referenceComments': [{'value': 'K-12', 'type': 'STRAIN'}],
                 'citation': {'title': 'A', 'journal': 'J Bact', 'publicationDate': '2003',
                              'citationCrossReferences': [{'database': 'PubMed', 'id': '111'},
                                                          {'database': 'DOI', 'id': '10.1/a'}]}},
                {'referencePositions': ['NUCLEOTIDE SEQUENCE'],
                 'citation': {'title': 'B', 'journal': 'Nature', 'publicationDate': 'JUL-2010',
                              'citationCrossReferences': [{'database': 'PubMed', 'id': '222'}]}}]}


class MemoryStore:
    """The names of the scoped store these functions use, over dictionaries."""

    def __init__(self):
        self.records, self.artifacts = {}, {}

    def artifact(self, content, media_type):
        content = content.encode() if isinstance(content, str) else content
        ref = 'artifact_' + hashlib.sha256(content).hexdigest()[:12]
        self.artifacts[ref] = content
        return ref

    def get_artifact(self, ref):
        return self.artifacts[ref]

    def get(self, ref):
        return self.records[ref]

    def refs(self):
        return list(self.records)

    def put(self, kind, record, *, origin):
        ref = kind + '_' + hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:12]
        self.records[ref] = {**record, 'id': ref}
        return self.records[ref]

    def hold_source(self, body, query, provider='uniprot'):
        ref = 'source_' + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]
        self.records[ref] = {'id': ref, 'provider': provider, 'accession': None, 'uri': None,
                             'artifact_ref': self.artifact(json.dumps(body), 'application/json'),
                             'request_ref': self.artifact(json.dumps({'request': {'query': query}}), 'application/json')}
        return ref


def world(rows):
    store = MemoryStore()
    store.records['input_target'] = {'id': 'input_target', 'sequence_ref': store.artifact(SEQUENCE, 'text/plain')}
    md5 = hashlib.md5(SEQUENCE.encode()).hexdigest().upper()
    store.hold_source({'results': rows}, 'checksum:' + md5)
    return store


def test_target_records_are_the_rows_whose_full_sequence_equals_the_targets():
    store = world([entry(), entry('Q00001', sequence=SEQUENCE[:-1] + 'A')])
    refs = target_record_refs(store, subject_ref='input_target')
    assert len(refs) == 1
    record = store.get(refs[0])
    assert record['accession'] == 'P0A7G6' and record['label'] == 'Protein RecA'
    assert store.get_artifact(record['sequence_ref']).decode() == SEQUENCE


def test_the_lookup_not_having_run_raises():
    store = MemoryStore()
    store.records['input_target'] = {'id': 'input_target', 'sequence_ref': store.artifact(SEQUENCE, 'text/plain')}
    with pytest.raises(ValueError, match='sequence_identity_lookup_not_held'):
        target_record_refs(store, subject_ref='input_target')


def test_listed_papers_carry_identifiers_scope_and_origin():
    store = world([entry()])
    hits = record_publications(store, record_ref=target_record_refs(store, subject_ref='input_target')[0])
    assert [(hit['pmid'], hit['doi'], hit['pmcid'], hit['year']) for hit in hits] == [
        ('111', '10.1/a', None, '2003'), ('222', None, None, '2010')]
    assert hits[0]['reported_scope'] == 'FUNCTION; STRAIN: K-12' and hits[1]['reported_scope'] == 'NUCLEOTIDE SEQUENCE'
    assert all(hit['listed_for_record_ref'] and hit['listed_by'] == 'uniprot' for hit in hits)
    assert 'Partial list' in hits[0]['abstract']


def test_a_non_uniprot_record_lists_nothing():
    store = MemoryStore()
    store.hold_source({}, 'x', provider='ncbi_entrez')
    source = next(iter(store.records))
    store.records['reference_a'] = {'id': 'reference_a', 'source_ref': source, 'accession': 'NP_1'}
    assert record_publications(store, record_ref='reference_a') == []


def europepmc(entries):
    return json.dumps({'resultList': {'result': entries}}).encode()


def test_pmcids_come_from_europe_pmc_and_merge_keeps_each_paper_once_after_the_search_hits():
    store = world([entry()])
    hits = record_publications(store, record_ref=target_record_refs(store, subject_ref='input_target')[0])
    requests = resolve_queries(hits)
    assert requests == [{'query': '(EXT_ID:111 OR EXT_ID:222) AND SRC:MED', 'size': 2}]
    response = europepmc([{'pmid': '111', 'pmcid': 'PMC9', 'doi': '10.1/a', 'title': 'A', 'abstractText': 'Abs A.',
                           'journalInfo': {'journal': {'title': 'J Bact'}}, 'pubYear': '2003'}])
    listed = with_full_text(hits, [response])
    assert [hit['pmcid'] for hit in listed] == ['PMC9', None] and listed_without_full_text(listed) == 1
    assert listed[0]['abstract'].startswith('[Listed by uniprot') and listed[0]['abstract'].endswith('Abs A.')
    search = ranked_hits([europepmc([{'pmid': '555', 'pmcid': 'PMC1', 'title': 'S', 'pubYear': 2020}])])
    merged = merge_listed(search, listed)
    assert [(hit['pmcid'], hit['provider_rank']) for hit in merged] == [('PMC1', 1), ('PMC9', 2)]
    # The same paper already among the search hits (by PMID) is that hit; listing it twice adds nothing.
    duplicate = ranked_hits([europepmc([{'pmid': '111', 'pmcid': 'PMC9', 'title': 'A', 'pubYear': 2003}])])
    assert [hit['pmcid'] for hit in merge_listed(duplicate, listed + listed)] == ['PMC9']
    assert hit_candidate(merged[1])['result_id'] == 'PMC9' and 'Listed by uniprot' in hit_candidate(merged[1])['description']


def test_many_listed_papers_are_queried_in_batches_without_dropping_any():
    hits = [{'pmid': str(index), 'pmcid': None} for index in range(1, 2 * RESOLVE_BATCH + 2)]
    requests = resolve_queries(hits)
    assert [request['size'] for request in requests] == [RESOLVE_BATCH, RESOLVE_BATCH, 1]


@pytest.mark.model_run
def test_real_uniprot_reference_list_of_reca():
    """The real service: UniProt's entry of E. coli RecA (P0A7G6) lists papers; the reader returns them as hits."""
    from gene_annotation_episode.acquisition import PublicClients
    snapshot = PublicClients().uniprot_record('P0A7G6')
    store = MemoryStore()
    source = store.hold_source(json.loads(snapshot.content), 'live')
    store.records['reference_live'] = {'id': 'reference_live', 'source_ref': source, 'accession': 'P0A7G6'}
    hits = record_publications(store, record_ref='reference_live')
    print('LISTED', len(hits), [(hit['pmid'], hit['year'], hit['reported_scope'][:40]) for hit in hits[:5]])
    # A database's list holds citations with no PubMed identifier too (submissions); those are leads that cannot be opened.
    assert hits and any(hit['pmid'] for hit in hits) and all(hit['reported_scope'] is not None for hit in hits)
    print('WITHOUT_ID', sum(1 for hit in hits if not hit['pmid'] and not hit['doi']))
