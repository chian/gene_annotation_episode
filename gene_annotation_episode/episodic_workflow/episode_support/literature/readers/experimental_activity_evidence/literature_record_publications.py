"""The papers a database lists for a record, as extra hits for the search step of the experimental-activity axis.

The owner's goal for this arm (2026-11-21): find the exact sequence the experimental data belong to, so the evidence's
closeness to the target is known. "Some dbs will have a partial list of papers as well." A record whose sequence equals
the target's is the target's own record in that database; the papers the database lists for it are leads for the
search step, beside the hits of the provider search.

What a database's list is, and is not: the papers its curators cited for the record, with the scope each citation
reports (UniProt ``referencePositions`` and ``referenceComments``). It is partial: a protein is studied in more papers
than any entry cites. A listed paper is a lead to read, never an experiment result and never evidence of its own.

Reading: ``target_record_refs`` and ``record_publications`` read through the store the caller hands in (the scoped store
of a unit). ``target_record_refs`` holds the matching UniProt records as ``reference`` records through that store's
``put`` (the unit's custody); nothing else here writes. The lookup is the existing sequence-identity lookup
(``public.literature.sequence_identity``, ``literature_sequence_discovery``): a unit runs it and retains the response as a
``uniprot`` source; this module reads that retained response and verifies the complete residue string of each row."""
from __future__ import annotations

import hashlib
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    IDENTIFIERS, provider_hits)

# EXPERT_REVIEW (owner to confirm): the Europe PMC query that finds the PMCID of the listed papers names at most this
# many PubMed identifiers. Reason: 25 is the page size ``source.sequence.references`` already uses for a database's
# citation list, and a query of a few hundred identifiers is too long for one request. It is a request size, not a
# bound on how many listed papers are used: every listed paper is queried, in as many requests as it needs.
RESOLVE_BATCH = 25

LISTED_BY = 'uniprot'
PARTIAL_LIST = ('This is a database\'s list of papers for a record of the target\'s sequence. It is partial: it names '
                'the papers the database curators cited, not every paper that studied this protein. The reported '
                'scope is the database\'s own wording, not a result.')


def _sequence_of(store, record):
    return store.get_artifact(record['sequence_ref']).decode('ascii').upper()


def _query_of(store, source):
    return json.loads(store.get_artifact(source['request_ref']))['request']['query']


def _row_sequence(row):
    return row['sequence']['value'].upper()


def _row_label(row):
    description = row.get('proteinDescription', {})
    name = description.get('recommendedName', {}).get('fullName', {}).get('value')
    if name:
        return name
    submitted = description.get('submissionNames') or []
    return submitted[0]['fullName']['value'] if submitted else row['uniProtkbId']


def target_record_refs(store, *, subject_ref):
    """The ``reference`` records whose complete sequence equals the target's, from the sequence-identity lookup of the
    target (the retained ``uniprot`` response of ``public.literature.sequence_identity`` for its checksum query): each
    row's full residue string is compared with the target's (a checksum is a lead, not the equality), and each equal row
    is held as a ``reference`` record (accession, label, ``sequence_ref``) through ``store``. A record already held
    for the row is the same record. The lookup of the target not having run raises; a lookup that found no equal record
    returns an empty list."""
    sequence = _sequence_of(store, store.get(subject_ref))
    prefix = 'checksum:' + hashlib.md5(sequence.encode('ascii')).hexdigest().upper()
    sources = [store.get(ref) for ref in sorted(store.refs()) if ref.startswith('source_')]
    lookups = [source for source in sources
               if source['provider'] == LISTED_BY and source['request_ref']
               and _query_of(store, source).startswith(prefix)]
    if not lookups:
        raise ValueError('sequence_identity_lookup_not_held:' + subject_ref)
    refs = []
    for source in lookups:
        for row in json.loads(store.get_artifact(source['artifact_ref']))['results']:
            if _row_sequence(row) != sequence:
                continue
            record = store.put('reference', {
                'reference_type': 'protein', 'source_ref': source['id'], 'accession': row['primaryAccession'],
                'label': _row_label(row), 'sequence_ref': store.artifact(_row_sequence(row), 'text/plain'),
                'molecule': 'protein', 'length': len(_row_sequence(row)), 'term_refs': [], 'context_refs': []},
                origin='external')
            refs.append(record['id'])
    return list(dict.fromkeys(refs))


def _entry(store, record):
    source = store.get(record['source_ref'])
    body = json.loads(store.get_artifact(source['artifact_ref']))
    rows = body['results'] if 'results' in body else [body]
    matching = [row for row in rows if row['primaryAccession'] == record['accession']]
    if len(matching) != 1:
        raise ValueError('record_not_in_its_source:' + record['accession'])
    return matching[0]


def _scope_text(row):
    positions = row.get('referencePositions') or []
    positions = [positions] if isinstance(positions, str) else positions
    comments = [f"{item['type']}: {item['value']}" for item in row.get('referenceComments') or []]
    return '; '.join([*positions, *comments])


def _abstract(record, scope):
    mark = f"[Listed by {LISTED_BY} for {record['accession']}, a record of the target's sequence. Partial list.]"
    return mark + (f" Reported scope: {scope}." if scope else '')


def record_publications(store, *, record_ref):
    """The papers the database lists for the held ``reference`` record, in the database's order, as hits of the shape
    ``search_result_assessment.provider_hits`` returns (``pmcid``, ``pmid``, ``doi``, ``title``, ``journal``, ``year``,
    ``abstract``; ``hit_candidate`` reads them once the caller gives each its ``provider_rank``). UniProt lists PubMed
    and DOI identifiers, rarely a PMCID, so ``pmcid`` is None until ``with_full_text`` finds it. Each hit also carries
    ``listed_for_record_ref``, ``listed_accession``, ``listed_by`` and ``reported_scope`` (the database's own wording of
    what the citation covers). The abstract of a listed hit says where it came from and that the list is partial.
    A record whose source is not a UniProt response lists nothing here."""
    record = store.get(record_ref)
    if store.get(record['source_ref'])['provider'] != LISTED_BY:
        return []
    hits = []
    for row in _entry(store, record).get('references') or []:
        citation = row['citation']
        ids = {item['database']: item['id'] for item in citation.get('citationCrossReferences') or []}
        scope = _scope_text(row)
        date = str(citation.get('publicationDate') or '')
        hits.append({'pmcid': None, 'pmid': ids.get('PubMed'), 'doi': ids.get('DOI'),
                     'title': citation.get('title') or '', 'journal': citation.get('journal') or '',
                     'year': date[-4:], 'abstract': _abstract(record, scope), 'listed_for_record_ref': record_ref,
                     'listed_accession': record['accession'], 'listed_by': LISTED_BY, 'reported_scope': scope})
    return hits


def resolve_queries(hits):
    """The Europe PMC search requests that give the PMCID (and the abstract) of the listed hits that have a PubMed
    identifier and no PMCID, ``RESOLVE_BATCH`` identifiers per request."""
    pmids = list(dict.fromkeys(hit['pmid'] for hit in hits if hit['pmid'] and not hit['pmcid']))
    batches = [pmids[start:start + RESOLVE_BATCH] for start in range(0, len(pmids), RESOLVE_BATCH)]
    return [{'query': '(' + ' OR '.join('EXT_ID:' + pmid for pmid in batch) + ') AND SRC:MED', 'size': len(batch)}
            for batch in batches]


def with_full_text(hits, contents):
    """The listed ``hits`` with the PMCID and abstract Europe PMC returned for them (``contents``: the retained
    responses of ``resolve_queries``, bytes). A listed paper Europe PMC holds no full text for keeps ``pmcid`` None. The
    note of where the hit came from stays at the head of its abstract."""
    found = {}
    for content in contents:
        for hit in provider_hits(content):
            for name in ('pmid', 'doi'):
                if hit[name]:
                    found.setdefault((name, hit[name]), hit)
    result = []
    for hit in hits:
        match = next((found[(name, hit[name])] for name in ('pmid', 'doi') if (name, hit[name]) in found), None)
        if match is None:
            result.append(dict(hit))
            continue
        result.append({**hit, 'pmcid': match['pmcid'], 'journal': hit['journal'] or match['journal'],
                       'abstract': hit['abstract'] + ' ' + match['abstract']})
    return result


def merge_listed(ranked, listed):
    """The search hits ``ranked`` (with ``provider_rank``) followed by the listed hits that can be opened (those with a
    PMCID, which is what the full-text fetch takes) and are not already in the list: a listed paper that shares any
    identifier (PMCID, PMID, DOI) with a hit already there is that hit, the first keeps its place, and the same paper
    listed for two records is one. Listed hits take the ranks after the search hits, in the database's order."""
    seen = {name: {hit[name] for hit in ranked if hit[name]} for name in IDENTIFIERS}
    merged = [dict(hit) for hit in ranked]
    for hit in listed:
        if not hit['pmcid'] or any(hit[name] in seen[name] for name in IDENTIFIERS if hit[name]):
            continue
        for name in IDENTIFIERS:
            if hit[name]:
                seen[name].add(hit[name])
        merged.append({**hit, 'provider_rank': len(merged) + 1})
    return merged


def listed_without_full_text(listed):
    """How many distinct listed papers have no PMCID, so cannot be opened."""
    return len({(hit['pmid'], hit['doi'], hit['title']) for hit in listed if not hit['pmcid']})


__all__ = ['LISTED_BY', 'PARTIAL_LIST', 'RESOLVE_BATCH', 'listed_without_full_text', 'merge_listed',
           'record_publications', 'resolve_queries', 'target_record_refs', 'with_full_text']
