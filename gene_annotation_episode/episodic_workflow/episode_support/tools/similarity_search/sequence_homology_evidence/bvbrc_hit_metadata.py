"""What each hit of a BV-BRC BLAST report is, from BV-BRC's own data service: the reference metadata of the database
grader (``blast_database_grader.build_database_sheet``, legacy association: one row per hit accession).

The hits of the ``bacteria-archaea`` database are named by feature ids: a description of the report has ``accession``
``<genome id>.peg.<n>`` and ``id`` ``gnl|fig|<genome id>.peg.<n>``; the feature's ``patric_id`` in the data service is
``fig|<accession>`` (verified against the live service: every one of 300 hits was found). The hits of the
``viral-reference`` database are named the same way, with ``CDS`` as well as ``peg`` as the feature kind
(``<genome id>.CDS.<n>``; one live search, 2026-11-24, 5 hits). The lookups are the public Data
API (no login is sent: the service answers them without one), three collections, each in batches of ``BATCH`` ids so that
300 hits take a handful of requests, at least ``SPACING_SECONDS`` apart:

* ``genome_feature`` by ``patric_id``: ``product``, ``annotation``, ``pgfam_id``, ``plfam_id``, ``genome_id``,
  ``taxon_id``, ``feature_id``, ``aa_length``, ``aa_sequence_md5``, and the hit's own feature annotation in its genome
  (the owner, 2026-11-25: "just like with organismal taxa ... you also have to extract this? we can decide how to use
  it later"): ``feature_type`` (the database's type of the feature), ``sequence_id`` and ``accession`` (the sequence of
  the genome it lies on: the service's id of it and its accession), ``start``, ``end``, ``strand`` and ``na_length``
  (its position, strand and length in nucleotides on that sequence). The names are those of the repository's field
  list of the collection (``bvbrc_data_fields``); the values are kept exactly as the service gives them and nothing
  here reads them (``grading/sequence_features/database_feature_types.py`` matches ``feature_type`` to our types);
* ``protein_family_ref`` by ``family_id`` (the family ids found): ``family_type``, ``family_product``;
* ``genome`` by ``genome_id``: ``genome_name``, ``taxon_id``.

BV-BRC's words and this project's: BV-BRC ``product`` is the name of the protein, which this project calls the function
(or annotation) of the hit; BV-BRC ``annotation`` names the SOURCE that assigned the name (for example ``PATRIC``) and is
kept as the source of the function assignment, never as a function or label; ``pgfam_id`` and ``plfam_id`` are the
cross-genus and the genus-level family ids; ``patric_id`` (with ``fig|``) is the hit's accession. The stored responses keep
BV-BRC's field names unchanged.

A hit whose feature the service did not return, or whose request failed, gets no row: the grader's metadata accounting
counts it as missing, never as a hit with no function. A feature that comes back more than once (under more than one
``annotation``) is reported (``duplicate_feature_ids``) and ONE record is taken by a stated rule: the record whose
``annotation`` sorts first as text (a rule independent of the order the service answered in).

What exists and is called: the request builder ``encode_native_query`` (with its field registry), the public data client
``BVBRCDataClient.query_prepared`` and ``blast_database_grading_inputs.metadata_accounting``."""
import hashlib
import json
import time

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_query import (
    encode_native_query)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.differential_credit import (
    differential_credit)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_bvbrc import (
    BVBRCDataClient, DEFAULT_BASE_URL)

BATCH = 100
SPACING_SECONDS = 10
FEATURE_FIELDS = ['patric_id', 'feature_id', 'product', 'annotation', 'pgfam_id', 'plfam_id', 'genome_id', 'taxon_id',
                  'aa_length', 'aa_sequence_md5', 'feature_type', 'sequence_id', 'accession', 'start', 'end', 'strand',
                  'na_length']
FAMILY_FIELDS = ['family_id', 'family_type', 'family_product']
GENOME_FIELDS = ['genome_id', 'genome_name', 'taxon_id']
SOURCE = 'bvbrc_data:genome_feature'


def _batches(values):
    return [values[start:start + BATCH] for start in range(0, len(values), BATCH)]


def _ask(client, collection, key, values, fields, state):
    """One public request for the records of ``collection`` whose ``key`` is in ``values``: the documents, or ``None``
    when the service did not answer (the code is kept in ``state['failures']``). Sleeps the spacing first."""
    request = {'version': 'bvbrc_data_request', 'collection': collection, 'mode': 'page',
               'filters': [{'field': key, 'operator': 'in', 'value': values}], 'fields': fields,
               'limit': max(len(values) * 4, 25), 'offset': 0}
    prepared = encode_native_query(request, base_url=DEFAULT_BASE_URL)
    time.sleep(SPACING_SECONDS)
    state['requests'] += 1
    try:
        snapshot = client.query_prepared(prepared)
    except AcquisitionError as error:
        state['failures'].append(error.code)
        return None
    body = json.loads(snapshot.content)['response']
    state['responses'].append({'collection': collection, 'requested': len(values), 'found': body['numFound']})
    return body['docs']


def lookup(accessions):
    """The BV-BRC records of the hits ``accessions`` (the report's ``accession`` of each hit): ``{'features', 'families',
    'genomes', 'requests', 'failures', 'responses', 'duplicate_feature_ids'}``. The records keep BV-BRC's field names."""
    client = BVBRCDataClient()
    state = {'requests': 0, 'failures': [], 'responses': []}
    chosen, duplicates = {}, 0
    for batch in _batches(['fig|' + accession for accession in accessions]):
        found = _ask(client, 'genome_feature', 'patric_id', batch, FEATURE_FIELDS, state)
        for record in found or []:
            known = chosen.get(record['patric_id'])
            if known is not None:
                duplicates += 1
            if known is None or record.get('annotation', '') < known.get('annotation', ''):
                chosen[record['patric_id']] = record
    features = [chosen[key] for key in sorted(chosen)]
    families = {}
    family_ids = sorted({record[name] for record in features for name in ('pgfam_id', 'plfam_id') if record.get(name)})
    for batch in _batches(family_ids):
        for record in _ask(client, 'protein_family_ref', 'family_id', batch, FAMILY_FIELDS, state) or []:
            families[record['family_id']] = record
    genomes = {}
    for batch in _batches(sorted({record['genome_id'] for record in features})):
        for record in _ask(client, 'genome', 'genome_id', batch, GENOME_FIELDS, state) or []:
            genomes[record['genome_id']] = record
    return {'features': features, 'families': families, 'genomes': genomes, 'requests': state['requests'],
            'failures': state['failures'], 'responses': state['responses'], 'duplicate_feature_ids': duplicates}


SETTLE = 0.01


def _merge(whole, part):
    """Add one batch's ``lookup`` result to the running one."""
    for record in part['features']:
        known = whole['_chosen'].get(record['patric_id'])
        if known is not None:
            whole['duplicate_feature_ids'] += 1
        if known is None or record.get('annotation', '') < known.get('annotation', ''):
            whole['_chosen'][record['patric_id']] = record
    whole['families'].update(part['families'])
    whole['genomes'].update(part['genomes'])
    whole['requests'] += part['requests']
    whole['failures'].extend(part['failures'])
    whole['responses'].extend(part['responses'])
    whole['duplicate_feature_ids'] += part['duplicate_feature_ids']


def _picture(chosen, values):
    """The candidate list the named hits give so far: product -> score, by the head's own arithmetic
    (``differential_credit``: one test, the score of a candidate is the mean of its hits' values; admitted when above 0)."""
    rows = [{'test': 'named_hits', 'candidate': chosen[accession]['product'], 'value': values[accession]}
            for accession in values if accession in chosen and chosen[accession].get('product')]
    return differential_credit(rows)['scores']


def name_hits(ordered):
    """Name the hits of a graded search in the order of their value, in batches of ``BATCH``. ``ordered`` is
    ``[(accession, value)]``, highest value first, ties by accession (the per-hit value the head's credit reads). After each
    batch the candidate list and scores of the hits named so far are computed (``_picture``); the naming STOPS when a
    batch, against the picture before it, admits no new product and moves no existing candidate's score by more than
    ``SETTLE`` (stop reason ``settled``), or when every hit is named (``all_named``). The first batch has no picture
    before it, so a second batch is always asked for when hits remain. Returns the merged ``lookup`` result (as
    ``lookup`` gives it, for the hits named) with ``naming``: ``{'named', 'not_asked', 'batches', 'stopped'}``; a hit not
    named is NOT ASKED (not asked-and-missing)."""
    whole = {'_chosen': {}, 'families': {}, 'genomes': {}, 'requests': 0, 'failures': [], 'responses': [],
             'duplicate_feature_ids': 0}
    values, before, batches = {}, {}, 0
    stopped = 'all_named'
    for start in range(0, len(ordered), BATCH):
        part = ordered[start:start + BATCH]
        _merge(whole, lookup([accession for accession, _ in part]))
        values.update(dict(part))
        batches += 1
        after = _picture(whole['_chosen'], values)
        settled = (batches > 1 and set(after) <= set(before)
                   and all(abs(after[name] - before[name]) <= SETTLE for name in after))
        before = after
        if start + BATCH < len(ordered) and settled:
            stopped = 'settled'
            break
    chosen = whole.pop('_chosen')
    named = len(values)
    return {'features': [chosen[key] for key in sorted(chosen)], **whole,
            'naming': {'named': named, 'not_asked': len(ordered) - named, 'batches': batches, 'stopped': stopped}}


def sequences_by_md5(md5s):
    """The protein sequences of the BV-BRC ``feature_sequence`` collection (public Data API, no login; its key ``md5``
    is a hit feature's ``aa_sequence_md5``), in batches of ``BATCH`` at least ``SPACING_SECONDS`` apart: ``{'sequences':
    {md5: sequence}, 'requests', 'failures', 'responses'}``. A sequence is kept only when the MD5 of its text is the md5
    it was asked for (``ValueError`` with the md5 otherwise); an md5 the service did not return is absent."""
    client = BVBRCDataClient()
    state = {'requests': 0, 'failures': [], 'responses': []}
    found = {}
    for batch in _batches(sorted(set(md5s))):
        for record in _ask(client, 'feature_sequence', 'md5', batch, ['md5', 'sequence_type', 'sequence'], state) or []:
            if hashlib.md5(record['sequence'].encode('ascii')).hexdigest() != record['md5']:
                raise ValueError('bvbrc_sequence_does_not_match_its_md5:' + record['md5'])
            found[record['md5']] = record['sequence']
    return {'sequences': found, 'requests': state['requests'], 'failures': state['failures'],
            'responses': state['responses']}


def reference_metadata(found):
    """The grader's reference-metadata rows (legacy association, matched by ``accession`` and the native ``taxid``) from
    the records ``lookup`` found: one row per feature that has a ``product``. A feature without one has a row without
    functions. ``source`` of a function is BV-BRC's ``annotation`` of the feature (who assigned the name).
    ``bvbrc_feature`` of a function is the feature's record as the service gave it (every one of ``FEATURE_FIELDS`` it
    returned: the taxon id and the feature's own type, sequence, position, strand and length among them), which the
    graded sheet keeps with the function."""
    rows = []
    for record in found['features']:
        families = [found['families'][record[name]] for name in ('pgfam_id', 'plfam_id') if record.get(name)]
        genome = found['genomes'].get(record['genome_id'], {})
        function = ({'function': record['product'], 'source': record.get('annotation'),
                     'bvbrc_feature': {name: record[name] for name in FEATURE_FIELDS if name in record},
                     'bvbrc_families': [dict(family) for family in families]}
                    if record.get('product') else None)
        rows.append({'accession': record['patric_id'].removeprefix('fig|'), 'taxid': record.get('taxon_id'),
                     'source': SOURCE, 'functions': [] if function is None else [function],
                     'origin': {'genome_id': record['genome_id'], 'genome_name': genome.get('genome_name'),
                                'feature_id': record['feature_id']}})
    return rows


__all__ = ['BATCH', 'SOURCE', 'SPACING_SECONDS', 'SETTLE', 'lookup', 'name_hits', 'reference_metadata', 'sequences_by_md5']
