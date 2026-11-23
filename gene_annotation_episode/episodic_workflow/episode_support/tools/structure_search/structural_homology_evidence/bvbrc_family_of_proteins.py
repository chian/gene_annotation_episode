"""The BV-BRC global protein family of the UniProt proteins behind the named hits of a structure search.

For each UniProt accession the public BV-BRC Data API (no login is sent) is asked twice, in batches of ``BATCH`` at least
``SPACING_SECONDS`` apart (the request pattern of A101's ``bvbrc_hit_metadata``: ``encode_native_query`` and
``BVBRCDataClient.query_prepared``; the only shared pieces are those two client functions):

* collection ``id_ref`` filtered by ``uniprotkb_accession`` in the batch and ``id_type`` = ``RefSeq``: ``id_value`` is a RefSeq
  protein id (an accession can have several);
* collection ``genome_feature`` filtered by ``protein_id`` in those RefSeq ids: ``pgfam_id`` is the global family id (``PGF_...``).

The identifier of a protein is exactly the ``pgfam_id`` BV-BRC gives, source ``bvbrc_global_family``. A protein whose RefSeq
ids lead to features of more than one distinct ``pgfam_id`` carries each of them. A protein with no RefSeq id, or none whose
features carry a ``pgfam_id``, carries none: that is a lookup that was made and found no family. An accession whose request
failed (any of the two) is not looked up (``looked_up`` leaves it out): a failed request is not "no family". The replies are
kept as bytes (``replies``) for retention with the UniProt replies."""
import hashlib
import json
import time

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_query import (
    encode_native_query)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_bvbrc import (
    BVBRCDataClient, DEFAULT_BASE_URL)

BATCH = 100
SPACING_SECONDS = 10
SOURCE = 'bvbrc_global_family'
SERVICE = 'bvbrc_data'
REFSEQ = 'RefSeq'
ID_FIELDS = ['uniprotkb_accession', 'id_type', 'id_value']
FEATURE_FIELDS = ['protein_id', 'pgfam_id']


def _batches(values):
    return [values[start:start + BATCH] for start in range(0, len(values), BATCH)]


def _ask(client, collection, filters, limit, replies):
    """One public request: the documents, or ``None`` when the service did not answer (the code is returned as the second
    value). The reply's bytes are appended to ``replies``."""
    request = {'version': 'bvbrc_data_request', 'collection': collection, 'mode': 'page', 'filters': filters,
               'fields': ID_FIELDS if collection == 'id_ref' else FEATURE_FIELDS, 'limit': limit, 'offset': 0}
    prepared = encode_native_query(request, base_url=DEFAULT_BASE_URL)
    time.sleep(SPACING_SECONDS)
    try:
        snapshot = client.query_prepared(prepared)
    except AcquisitionError as error:
        return None, error.code
    replies.append({'collection': collection, 'request': request, 'sha256': hashlib.sha256(snapshot.content).hexdigest(),
                    'media_type': 'application/json', 'content': snapshot.content})
    return json.loads(snapshot.content)['response']['docs'], None


def lookup(accessions):
    """The global families of the proteins ``accessions``: ``{'families': {accession: [pgfam_id]}, 'looked_up': [accessions
    whose two requests answered], 'failures': [codes], 'replies': [{'collection', 'request', 'sha256', 'media_type',
    'content'}]}``. ``families`` has an entry (possibly empty) for each accession in ``looked_up`` only."""
    client = BVBRCDataClient()
    replies, failures, families, looked_up = [], [], {}, []
    for batch in _batches(list(dict.fromkeys(accessions))):
        found, code = _ask(client, 'id_ref', [{'field': 'uniprotkb_accession', 'operator': 'in', 'value': batch},
                                              {'field': 'id_type', 'operator': 'eq', 'value': REFSEQ}],
                           max(len(batch) * 20, 100), replies)
        if code is not None:
            failures.append(code)
            continue
        refseq = {accession: sorted({doc['id_value'] for doc in found if doc['uniprotkb_accession'] == accession})
                  for accession in batch}
        ids = sorted({value for values in refseq.values() for value in values})
        by_protein = {}
        for part in _batches(ids):
            features, code = _ask(client, 'genome_feature', [{'field': 'protein_id', 'operator': 'in', 'value': part}],
                                  max(len(part) * 50, 100), replies)
            if code is not None:
                failures.append(code)
                break
            for doc in features:
                if doc.get('pgfam_id'):
                    by_protein.setdefault(doc['protein_id'], set()).add(doc['pgfam_id'])
        else:
            for accession in batch:
                families[accession] = sorted({family for value in refseq[accession] for family in by_protein.get(value, ())})
                looked_up.append(accession)
    return {'families': families, 'looked_up': looked_up, 'failures': failures, 'replies': replies}


__all__ = ['BATCH', 'SOURCE', 'SERVICE', 'lookup']
