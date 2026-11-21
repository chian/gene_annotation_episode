"""What each hit of a structure search of an AlphaFold database is, from UniProt: the product name of its accession.

The hits of ``afdb-swissprot`` are ``AF-<UniProt accession>-F1-model_v6`` (``foldseek_result.target_name`` gives the
accession), so the function name of a hit comes from UniProt by accession. The lookup is the one request the A102 public
client already makes, ``PublicClients.uniprot_search`` (``acquisition/structural_homology_evidence/acquisition.py``, the
installed UniProt skill client; the same recording as every other outside request of the library: a ``SourceSnapshot`` with
the request, the transport and the reply's bytes): ``GET https://rest.uniprot.org/uniprotkb/search?query=accession:A OR
accession:B OR ...&size=<n>&format=json`` (verified live 2026-11-21: 3 accessions, HTTP 200, ``X-Total-Results`` 3, the full
JSON entry of each; the same request form was verified in ``a102_services.md`` section 4 with ``fields=``; the client takes no
``fields``, so the replies are whole entries). The sibling form ``uniprotkb/accessions?accessions=A,B,C&fields=...`` also
answers (HTTP 200, 0.5 s) but is not used: its ``protein_name`` column joins the recommended, short and alternative names in
one string. No name, email or key is in the request; the client's headers are its own.

THE PRODUCT NAME of an accession is UniProt's RECOMMENDED protein name (``proteinDescription.recommendedName.fullName``).
An entry with no recommended name but a submitted one takes its first submitted name (``submissionNames[0]``) and is flagged
``name_source`` ``submitted``; an entry with neither has no name (asked, no product). The EC numbers (``ecNumbers`` of the
recommended name) and the GO ids (cross references of database ``GO``) are kept as metadata.

THE NAMING RULE is that of A101's ``bvbrc_hit_metadata.name_hits``: the hits are named in RANK ORDER in batches of ``BATCH``
(100). After each batch the candidate list of the hits named so far is computed with the axis's own arithmetic
(``differential_credit``: one test, a candidate's score is the mean of its hits' B, admitted when above 0; a hit with no B
makes no measurement). The naming STOPS when a batch, against the picture before it, admits no new product and moves no
existing candidate's score by more than ``SETTLE`` (stop reason ``settled``), or when every hit is named (``all_named``). The
first batch has no picture before it, so a second batch is always asked for when hits remain. A hit never asked is NOT ASKED
(its name is unknown, not absent); ``naming['not_asked']`` counts them. A batch whose request failed is recorded in
``failures`` (its hits were asked and carry no name)."""
import json
import time

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.structural_homology_evidence.acquisition import (
    AcquisitionError, PublicClients)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.differential_credit import (
    differential_credit)

BATCH = 100
SETTLE = 0.01
SPACING_SECONDS = 3
SOURCE = 'uniprot:uniprotkb_search'


def _batches(values):
    return [values[start:start + BATCH] for start in range(0, len(values), BATCH)]


def product_name(entry):
    """``(product, name_source)`` of one UniProt JSON entry: the recommended full name (``'recommended'``), else the first
    submitted name (``'submitted'``), else ``(None, None)``."""
    description = entry.get('proteinDescription', {})
    if 'recommendedName' in description:
        return description['recommendedName']['fullName']['value'], 'recommended'
    if description.get('submissionNames'):
        return description['submissionNames'][0]['fullName']['value'], 'submitted'
    return None, None


def _entry_metadata(entry):
    description = entry.get('proteinDescription', {})
    return {'ec': [ec['value'] for ec in description.get('recommendedName', {}).get('ecNumbers', ())],
            'go': sorted(ref['id'] for ref in entry.get('uniProtKBCrossReferences', ()) if ref.get('database') == 'GO'),
            'annotation_score': entry.get('annotationScore'),
            'reviewed': entry.get('entryType', '').startswith('UniProtKB reviewed')}


def lookup(accessions, client):
    """One request for the entries of ``accessions`` (at most ``BATCH``): ``{'products': {accession: {'product',
    'name_source'}}, 'metadata': {accession: {'ec', 'go', 'annotation_score', 'reviewed'}}, 'reply': {...}}`` or, when the
    service did not answer, ``{'failure': code, ...}``. An entry is matched to the accession asked by its primary
    accession or one of its secondary accessions. The ``reply`` keeps the request, the URL, the status and the reply's
    bytes (``content``) for retention."""
    accessions = list(dict.fromkeys(accessions))
    time.sleep(SPACING_SECONDS)
    query = ' OR '.join('accession:' + accession for accession in accessions)
    try:
        snapshot = client.uniprot_search(query, size=len(accessions))
    except AcquisitionError as error:
        return {'failure': error.code, 'products': {}, 'metadata': {}, 'reply': None}
    entries = json.loads(snapshot.content)['results']
    asked, products, metadata = set(accessions), {}, {}
    for entry in entries:
        for accession in [entry['primaryAccession'], *entry.get('secondaryAccessions', ())]:
            if accession in asked:
                product, source = product_name(entry)
                metadata[accession] = _entry_metadata(entry)
                if product is not None:
                    products[accession] = {'product': product, 'name_source': source}
    return {'failure': None, 'products': products, 'metadata': metadata,
            'reply': {'request': snapshot.request, 'url': snapshot.url, 'status': snapshot.transport['response']['status'],
                      'sha256': snapshot.sha256, 'media_type': snapshot.media_type, 'content': snapshot.content}}


def _picture(products, values):
    """The candidate list the named hits give so far: product -> score (one test, the mean of its hits' B)."""
    rows = [{'test': 'structure_search:named_hits', 'candidate': products[accession]['product'], 'value': values[accession]}
            for accession in values if accession in products and values[accession] is not None]
    return differential_credit(rows)['scores']


def name_hits(ordered, client=None):
    """Name the hits of a search in RANK ORDER, in batches of ``BATCH``. ``ordered`` is ``[(accession, B)]``, rank 1 first (B
    is ``None`` for a hit with no value). Returns ``{'products': {accession: {'product', 'name_source'}}, 'asked':
    [accessions asked], 'metadata': {accession: {'ec', 'go', 'annotation_score', 'reviewed'}}, 'replies': [the replies
    of ``lookup`` that answered, with their bytes], 'failures': [codes], 'naming': {'named', 'not_asked', 'batches',
    'stopped'}}``; ``named`` counts the hits asked (the A101 meaning of its ``named``), ``not_asked`` those never asked.
    ``products`` and ``asked`` are the ``names`` that ``structure_search_sheet.grade_structure_search`` takes."""
    client = PublicClients() if client is None else client
    products, metadata, replies, failures, asked, values = {}, {}, [], [], [], {}
    before, batches, stopped = {}, 0, 'all_named'
    for start in range(0, len(ordered), BATCH):
        part = ordered[start:start + BATCH]
        found = lookup([accession for accession, _ in part], client)
        if found['failure'] is not None:
            failures.append(found['failure'])
        else:
            products.update(found['products'])
            metadata.update(found['metadata'])
            replies.append(found['reply'])
        asked.extend(accession for accession, _ in part)
        values.update(dict(part))
        batches += 1
        after = _picture(products, values)
        settled = (batches > 1 and set(after) <= set(before)
                   and all(abs(after[name] - before[name]) <= SETTLE for name in after))
        before = after
        if start + BATCH < len(ordered) and settled:
            stopped = 'settled'
            break
    return {'products': products, 'asked': asked, 'metadata': metadata, 'replies': replies, 'failures': failures,
            'naming': {'named': len(asked), 'not_asked': len(ordered) - len(asked), 'batches': batches, 'stopped': stopped}}


__all__ = ['BATCH', 'SETTLE', 'SOURCE', 'lookup', 'name_hits', 'product_name']
