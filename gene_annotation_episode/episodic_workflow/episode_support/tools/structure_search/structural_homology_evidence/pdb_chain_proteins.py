"""What protein each hit of a ``pdb100`` structure search is: the UniProt accession of the hit's PDB chain, and from it the
product name (the same UniProt recommended protein name an ``afdb-swissprot`` hit gets, so the two searches measure the same
candidates).

THE REQUEST (verified live 2026-11-21, ``docs/plan/designs/a102_structure_search_episode.md``): one POST per batch to the RCSB
data API, ``https://data.rcsb.org/graphql``, ``Content-Type: application/json``, the query ``QUERY`` with the variable
``ids`` = the PDB entry ids of the batch (upper case). It is the ``entries`` root, not ``polymer_entity_instances``: the root
``polymer_entity_instances(instance_ids: ["1G29.A"])`` takes the LABEL asym id (``<entry>.<asym_id>``) and silently leaves out
an id it does not know (``1G29.1`` and ``4BTS.C0`` returned nothing, while ``1G29.A`` and ``7D5S.K`` answered), but the chain
label of a Foldseek pdb100 target is the AUTHOR chain id (``foldseek_result.PDB_TARGET``), so the lookup is by entry and the
instance is selected here by ``auth_asym_id``. For every polymer entity of the entry the query asks the entity's UniProt ids
(``rcsb_polymer_entity_container_identifiers.uniprot_ids``), its sequence alignments to reference databases
(``rcsb_polymer_entity_align``: the UniProt accession and the aligned regions, which give the residues each accession covers),
the polymer type (``entity_poly.rcsb_entity_polymer_type``), the sample sequence length and the description (kept as
metadata; never the product), and its instances with ``auth_asym_id``, ``asym_id`` and ``entity_id``; and, per ENTRY, its non-polymer entities' chemical
component ids (``nonpolymer_entities { nonpolymer_comp { chem_comp { id } } }``, verified live 2026-11-21 on 8GMS: AGS, MG; 3PF5: MG;
1MJC: none) which, with the polymer types of its polymer entities, are the partner metadata ``partner_contacts`` reads.

THE CHAIN'S PROTEIN. A chain whose entity has no UniProt accession (an antibody, a designed protein, a peptide, nucleic acid)
is asked and has NO product (it is not a candidate). A chimeric chain (an entity with more than one UniProt accession) keeps
every accession; it is named by the accession that covers most of the entity (the sum of the ``length`` of its aligned
regions) when the reply gives the coverage of every accession, else by the first accession in sorted order; it is flagged
(``chimeric``). The chain label's ``-<n>`` suffix (a further symmetry copy of the assembly, ``foldseek_result.pdb_target``) is
not part of the author chain id: the base chain is looked up.

THE NAMING RULE, stated once for both searches: the hits are looked up in RANK ORDER in batches of ``BATCH`` (100) hits; for
each batch the RCSB reply gives the accessions of its chains, then UniProt (``uniprot_hit_names.lookup``) gives the product
names of the accessions not named before. After each batch the candidate picture of the hits looked up so far is computed with
the axis's arithmetic (``differential_credit``: one test, a candidate's score is the mean B of ITS HITS, admitted when above 0).
The lookup STOPS when a batch admits no new product and moves no candidate's score by more than ``SETTLE``, or when all hits
are done; a hit never asked is NOT ASKED. For ``afdb-swissprot`` the same rule is ``uniprot_hit_names.name_hits``.

Request limits: spacing ``SPACING_SECONDS`` (3) before each request; no name, email or key; the browser-like User-Agent
constant of ``target_model_sources`` (one ``urllib`` request, no redirect, a socket timeout). A batch whose reply is not HTTP 200
or carries GraphQL errors is a failure of that batch (``rcsb_http_<status>``, ``rcsb_graphql_errors``,
``rcsb_request_failed:<error type>``): its hits were asked and have no accession."""
import hashlib
import json
import time

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    _request)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.differential_credit import (
    differential_credit)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.uniprot_hit_names import (
    BATCH, SETTLE, lookup as uniprot_lookup)

SPACING_SECONDS = 3
GRAPHQL_URL = 'https://data.rcsb.org/graphql'
SERVICE = 'rcsb_data_graphql'
QUERY = ('query($ids:[String!]!){entries(entry_ids:$ids){rcsb_id polymer_entities{'
         'rcsb_polymer_entity_container_identifiers{entity_id uniprot_ids} '
         'rcsb_polymer_entity{pdbx_description} entity_poly{rcsb_entity_polymer_type rcsb_sample_sequence_length} '
         'rcsb_polymer_entity_align{reference_database_name reference_database_accession '
         'aligned_regions{entity_beg_seq_id ref_beg_seq_id length}} '
         'polymer_entity_instances{rcsb_polymer_entity_instance_container_identifiers{entry_id auth_asym_id asym_id entity_id}}} '
         'nonpolymer_entities{nonpolymer_comp{chem_comp{id}}}}}')


def lookup_entries(entries):
    """One request for the entries ``entries`` (PDB ids; at most ``BATCH``): ``{'failure': None, 'entries': {entry id:
    the reply's entry object}, 'reply': {'request', 'url', 'status', 'sha256', 'media_type', 'content'}}`` or ``{'failure':
    code, 'entries': {}, 'reply': None}``."""
    entries = list(dict.fromkeys(entry.upper() for entry in entries))
    time.sleep(SPACING_SECONDS)
    request = {'query': QUERY, 'variables': {'ids': entries}}
    try:
        reply = _request('POST', GRAPHQL_URL, body=json.dumps(request).encode('ascii'), content_type='application/json')
    except OSError as error:
        return {'failure': 'rcsb_request_failed:' + type(error).__name__, 'entries': {}, 'reply': None}
    if reply['status'] != 200:
        return {'failure': 'rcsb_http_' + str(reply['status']), 'entries': {}, 'reply': None}
    body = json.loads(reply['body'])
    if body.get('errors'):
        return {'failure': 'rcsb_graphql_errors', 'entries': {}, 'reply': None}
    return {'failure': None, 'entries': {entry['rcsb_id']: entry for entry in body['data']['entries'] if entry is not None},
            'reply': {'request': {'query': QUERY, 'ids': entries}, 'url': GRAPHQL_URL, 'status': reply['status'],
                      'sha256': hashlib.sha256(reply['body']).hexdigest(),
                      'media_type': reply['headers'].get('Content-Type', 'application/json'), 'content': reply['body']}}


def _coverage(entity):
    """``{accession: residues of the entity it covers}`` from the entity's UniProt alignments (``{}`` when it has none)."""
    covered = {}
    for align in entity.get('rcsb_polymer_entity_align') or ():
        if align['reference_database_name'] == 'UniProt':
            covered[align['reference_database_accession']] = (covered.get(align['reference_database_accession'], 0)
                                                              + sum(region['length'] for region in align['aligned_regions']))
    return covered


def chain_record(entry, chain, entry_reply):
    """The record of the chain ``chain`` (an author chain id) of ``entry_reply`` (the RCSB entry object, or ``None`` when the
    reply did not hold the entry): ``{'entry', 'chain', 'status', 'asym_id', 'entity_id', 'polymer_type', 'sample_length',
    'description', 'accessions' (sorted), 'coverage' ({accession: residues} or ``{}``), 'accession' (the one the chain is named
    by, or ``None``), 'chimeric', and what the ENTRY holds as RCSB lists it (the partner metadata of ``partner_contacts``): ``entry_nonpolymer_components``
    (the distinct chemical component ids of its non-polymer entities, sorted), ``entry_polymer_types`` (the distinct polymer types
    of its polymer entities, sorted: ``Protein``, ``DNA``, ``RNA``, ``NA-hybrid``, ``Other``); both ``None`` when the reply did not hold the entry or the request failed); ``status`` is ``accession`` (the chain has one or more UniProt accessions),
    ``no_uniprot_accession``, ``chain_not_in_entry``, ``chain_ambiguous`` (more than one instance has the author id) or
    ``entry_not_returned``. A record that is not ``accession`` has no product."""
    blank = {'entry': entry, 'chain': chain, 'asym_id': None, 'entity_id': None, 'polymer_type': None, 'sample_length': None,
             'description': None, 'accessions': [], 'coverage': {}, 'accession': None, 'chimeric': False,
             'entry_nonpolymer_components': None, 'entry_polymer_types': None}
    if entry_reply is None:
        return {**blank, 'status': 'entry_not_returned'}
    contents = {'entry_nonpolymer_components': sorted({entity['nonpolymer_comp']['chem_comp']['id']
                                                       for entity in entry_reply['nonpolymer_entities'] or ()}),
                'entry_polymer_types': sorted({entity['entity_poly']['rcsb_entity_polymer_type']
                                               for entity in entry_reply['polymer_entities']})}
    blank = {**blank, **contents}
    found = [(entity, instance['rcsb_polymer_entity_instance_container_identifiers'])
             for entity in entry_reply['polymer_entities'] for instance in entity['polymer_entity_instances']
             if instance['rcsb_polymer_entity_instance_container_identifiers']['auth_asym_id'] == chain]
    if not found:
        return {**blank, 'status': 'chain_not_in_entry'}
    if len(found) > 1:
        return {**blank, 'status': 'chain_ambiguous'}
    (entity, instance), = found
    coverage = _coverage(entity)
    accessions = sorted(set(entity['rcsb_polymer_entity_container_identifiers']['uniprot_ids'] or ()) | set(coverage))
    complete = bool(accessions) and all(accession in coverage for accession in accessions)
    named = (min(accessions, key=lambda accession: (-coverage[accession], accession)) if complete
             else (accessions[0] if accessions else None))
    return {**blank, 'status': 'accession' if accessions else 'no_uniprot_accession', 'asym_id': instance['asym_id'],
            'entity_id': instance['entity_id'], 'polymer_type': entity['entity_poly']['rcsb_entity_polymer_type'],
            'sample_length': entity['entity_poly']['rcsb_sample_sequence_length'],
            'description': entity['rcsb_polymer_entity']['pdbx_description'], 'accessions': accessions,
            'coverage': {accession: coverage[accession] for accession in accessions if accession in coverage},
            'accession': named, 'chimeric': len(accessions) > 1}


def _picture(rows):
    return differential_credit(rows)['scores']


def name_pdb_hits(ordered):
    """Look up the chains of the hits of a ``pdb100`` search and name them, in RANK ORDER in batches of ``BATCH`` hits (see the
    module). ``ordered`` is ``[(entry, chain, B)]``, rank 1 first (the entry as in ``foldseek_result.pdb_target``, ``chain`` the
    base author chain id; ``B`` is ``None`` for a hit with no value). Returns ``{'hits': [chain record + 'asked' (bool) per
    hit, in order], 'products': {accession: {'product', 'name_source'}}, 'asked': [accessions asked of UniProt], 'metadata':
    {accession: {...}} (UniProt's), 'rcsb_replies': [...], 'uniprot_replies': [...], 'failures': [codes of RCSB batches],
    'uniprot_failures': [codes], 'naming': {'named', 'not_asked', 'batches', 'stopped'}}``; ``named`` counts the hits asked,
    ``not_asked`` those never asked. ``products`` and ``asked`` are the ``names`` that ``structure_search_sheet`` takes."""
    records, products, metadata, asked_accessions = {}, {}, {}, []
    rcsb_replies, uniprot_replies, failures, uniprot_failures = [], [], [], []
    done, before, batches, stopped = [], {}, 0, 'all_named'
    for start in range(0, len(ordered), BATCH):
        part = ordered[start:start + BATCH]
        found = lookup_entries([entry for entry, _, _ in part])
        if found['failure'] is not None:
            failures.append(found['failure'])
        else:
            rcsb_replies.append(found['reply'])
        for entry, chain, _ in part:
            if (entry, chain) not in records:
                records[(entry, chain)] = ({**chain_record(entry, chain, None), 'status': 'rcsb_request_failed'}
                                           if found['failure'] is not None
                                           else chain_record(entry, chain, found['entries'].get(entry)))
        new = [records[(entry, chain)]['accession'] for entry, chain, _ in part
               if records[(entry, chain)]['accession'] is not None]
        new = [accession for accession in dict.fromkeys(new) if accession not in asked_accessions]
        if new:
            names = uniprot_lookup(new)
            asked_accessions.extend(new)
            if names['failure'] is not None:
                uniprot_failures.append(names['failure'])
            else:
                products.update(names['products'])
                metadata.update(names['metadata'])
                uniprot_replies.append(names['reply'])
        done.extend(part)
        batches += 1
        after = _picture([{'test': 'structure_search:named_hits', 'candidate': products[accession]['product'], 'value': value}
                          for entry, chain, value in done
                          for accession in [records[(entry, chain)]['accession']]
                          if accession in products and value is not None])
        settled = (batches > 1 and set(after) <= set(before)
                   and all(abs(after[name] - before[name]) <= SETTLE for name in after))
        before = after
        if start + BATCH < len(ordered) and settled:
            stopped = 'settled'
            break
    hits = [{**records[(entry, chain)], 'asked': index < len(done)} if index < len(done)
            else {**chain_record(entry, chain, None), 'status': 'not_asked', 'asked': False}
            for index, (entry, chain, _) in enumerate(ordered)]
    return {'hits': hits, 'products': products, 'asked': asked_accessions, 'metadata': metadata,
            'rcsb_replies': rcsb_replies, 'uniprot_replies': uniprot_replies, 'failures': failures,
            'uniprot_failures': uniprot_failures,
            'naming': {'named': len(done), 'not_asked': len(ordered) - len(done), 'batches': batches, 'stopped': stopped}}


__all__ = ['GRAPHQL_URL', 'SERVICE', 'QUERY', 'SPACING_SECONDS', 'lookup_entries', 'chain_record', 'name_pdb_hits']
