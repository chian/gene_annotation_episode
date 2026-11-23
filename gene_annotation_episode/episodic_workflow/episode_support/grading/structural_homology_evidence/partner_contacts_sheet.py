"""The grader and the sheets of A102's ``partner_contacts``: what a solved structure shows bound to a protein that matches the
target, and whether the target has the contact residues of that binding in place.

INPUTS. One held graded ``pdb100`` structure search (its sheet ``a102_structure_search_sheet``: the hits with entry, chain,
product and B), the target's model (C-alpha by target position) and sequence, and, per solved entry file the unit fetched,
what the unit read from it (``tools/.../partner_contacts``): per hit chain its residues (C-alpha), its partners with their
contact residues, and the alignment of the target to that chain (``usalign_driver``: both TM-scores with their
normalisations, RMSD, aligned length, sequence identity, the aligned pairs in the files' own residue identifiers, the rotation
and the translation).

THE RULE (SOP Step 6; the test sister of ``site_correspondence``: same residue score, ``site_correspondence_sheet``).

* A PARTNER of a hit chain is a molecule of the entry's biological assembly other than the chain with a heavy atom within
  ``CONTACT_A`` of a heavy atom of the chain: (a) a hetero group that is not water, identified by its chemical component id
  (kind ``ligand``); (b) a nucleic-acid chain (kind ``dna`` or ``rna``); (c) another protein chain (kind ``protein``: a fact
  only, never a candidate). Partners of one key (``ligand:<id>``, ``nucleic_acid:dna``, ``nucleic_acid:rna``) are one partner
  of the hit chain: its contact residues are the residues of the hit chain within ``CONTACT_A`` of any of them.
* A ligand on the published artifact list of BioLiP (``additive: true``: crystallization and buffer components) is recorded and
  is neither a candidate nor a source of site residues. The functional partners of a hit are its non-additive ligand and its
  nucleic-acid partners.
* Per contact residue ``r`` of the hit chain with residue ``h``: (a) is ``r`` aligned to a target position ``q`` in the
  US-align alignment? No: ABSENT (``outside_the_alignment``: ``r`` is before the first or after the last aligned hit residue;
  ``within_the_alignment``: a gap inside), score 0, it stays in the denominator. (b) class match 1 when the target residue
  equals ``h`` or shares a role class with it (``site_correspondence_sheet.class_match``), else 0. (c) the distance ``d``
  between the target's C-alpha at ``q`` and the hit's C-alpha at ``r`` after US-align's own superposition of the target onto the
  chain (``X = t + u x``); the kernel is ``site_correspondence_sheet.kernel`` ``1 / (1 + (d / 1 A)^2)``. The residue's score is
  the class match times the kernel. A residue aligned to a target position the model has no C-alpha for is dropped with its
  reason and leaves the denominator. The target's numbering is the target sequence's (the model file's); no UniProt numbering
  is used.
* ``F(hit, partner)`` is the mean score over the partner's contact residues; ``F(hit)`` the mean over the union of the contact
  residues of the hit's functional partners; ``B(hit)`` is the search sheet's B of the hit; ``E = B F`` (the rule ``E = B F``).

TWO TESTS from one unit, each its own sheet (one test is one graded source):

* ``site_correspondence:partner_contacts@<source>`` (sheet ``a102_partner_contacts_sheet``): candidates are the PRODUCTS of
  the hits (``product:<name>``); a product's value is the mean ``E(hit)`` over its hits that have at least one functional
  partner; a product with no such hit has no measurement (``mean_E`` null, never a zero). Family ``site_correspondence``.
* ``bound_partner:pdb100@<source>`` (sheet ``a102_bound_partner_sheet``): candidates are the PARTNERS (``ligand:<id>``,
  ``nucleic_acid:dna``, ``nucleic_acid:rna``); a partner's value is the mean ``E(hit, partner) = B(hit) F(hit, partner)`` over
  the hits bound to it. Family ``bound_partner``.

The grader holds no threshold. The sheets are controlled data: numbers, booleans, vocabulary values (status, kind, state), residue
letters, chemical component ids, accessions, record references and the product names of UniProt."""
import math

import numpy as np

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.site_correspondence_sheet import (
    ABSENT_PLACES, CLASSES, FEATURE_SCALE_A, class_match, kernel)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.structure_search_sheet import (
    SCHEMA as SEARCH_SHEET)

CONTACTS_SCHEMA = 'a102_partner_contacts_sheet'
PARTNERS_SCHEMA = 'a102_bound_partner_sheet'
CONTACTS_PROVIDER = 'partner_contacts'
PARTNERS_PROVIDER = 'bound_partner'
CONTACTS_TEST = 'site_correspondence:partner_contacts'
PARTNERS_TEST = 'bound_partner:pdb100'
# The conventional heavy-atom contact distance of ligand-interaction resources: a residue is in contact with a partner when a
# heavy atom of it lies within 4.0 angstrom of a heavy atom of the partner. Source of the figure: UNVERIFIED (BioLiP's own pages,
# read 2026-11-21, state no distance; its paper's rule is not in the pages read). The figure is the order's.
CONTACT_A = 4.0
KINDS = ('ligand', 'dna', 'rna', 'protein', 'other_polymer')
FUNCTIONAL_KINDS = ('ligand', 'dna', 'rna')
ADDITIVE_STATUSES = ('listed_by_biolip', 'not_listed_by_biolip', 'not_applicable')
HIT_STATUSES = ('graded', 'no_functional_partner', 'no_partner_in_entry', 'entry_contents_unknown', 'not_asked', 'file_too_large', 'file_not_obtained', 'file_unreadable',
                'chain_not_found', 'chain_ambiguous', 'chain_not_protein', 'chain_entity_differs_from_rcsb',
                'chain_too_long_for_pdb_format', 'chain_has_no_c_alpha', 'alignment_failed')
SKIPPED_FILE_STATUSES = ('no_partner_in_entry', 'entry_contents_unknown')
FILE_STATUSES = ('parsed', 'too_large', 'not_obtained', 'unreadable', 'no_partner_in_entry', 'entry_contents_unknown')


def _require(condition, code):
    if not condition:
        raise ValueError('a102_partner_contacts_' + code)


def asked_rows(search_sheet):
    """The hit rows of a ``pdb100`` search sheet this test asks, in rank order: not a control, with a B and an entry (a hit that
    can enter a product's mean or a partner's mean)."""
    _require(search_sheet['schema'] == SEARCH_SHEET and search_sheet['database'] == 'pdb100', 'search_sheet_required')
    return [row for row in search_sheet['hits'] if row['control'] is None and row['B'] is not None]


def partner_key(kind, identifier):
    """The candidate key of a partner: ``ligand:<component id>``, ``nucleic_acid:dna`` or ``nucleic_acid:rna``."""
    return ('ligand:' + identifier) if kind == 'ligand' else ('nucleic_acid:' + kind)


def _transform(alignment):
    return np.array(alignment['rotation'], dtype=float), np.array(alignment['translation'], dtype=float)


def residue_rows(ordinals, chain, alignment, target_ca, target_sequence):
    """The scored rows of the contact residues ``ordinals`` (hit chain positions in the chain file) of a hit chain: ``(rows,
    dropped)``. See the module. ``alignment`` is the driver's pair (status ``aligned``); the aligned pairs give hit position ->
    target position."""
    by_hit = {int(second): int(first) for first, second in alignment['aligned']}
    first, last = min(by_hit), max(by_hit)
    rotation, translation = _transform(alignment)
    rows, dropped = [], []
    for ordinal in ordinals:
        residue = chain['residues'][ordinal]
        base = {'hit_position': ordinal, 'hit_author_seq_id': residue['auth_seq_id'], 'hit_insertion_code': residue['insertion_code'],
                'hit_residue': residue['letter']}
        target = by_hit.get(ordinal)
        if target is None:
            rows.append({**base, 'state': 'absent', 'absent': 'outside_the_alignment' if ordinal < first or ordinal > last
                         else 'within_the_alignment', 'target_position': None, 'target_residue': None, 'class_match': None,
                         'distance_A': None, 'kernel': None, 'score': 0.0})
        elif target not in target_ca:
            dropped.append({'hit_position': ordinal, 'reason': 'target_position_has_no_coordinate'})
        else:
            moved = np.array(target_ca[target], dtype=float) @ rotation.T + translation
            distance = float(np.linalg.norm(moved - np.array(residue['ca'], dtype=float)))
            match = class_match(target_sequence[target - 1], residue['letter'])
            value = kernel(distance)
            rows.append({**base, 'state': 'aligned', 'absent': None, 'target_position': target,
                         'target_residue': target_sequence[target - 1], 'class_match': match, 'distance_A': distance,
                         'kernel': value, 'score': match * value})
    return rows, dropped


def _mean(values):
    return math.fsum(values) / len(values) if values else None


def _unscored(partner):
    """The sheet row of a partner that has no score: its facts and the count of its contact residues."""
    return {**{key: partner[key] for key in ('kind', 'identifier', 'additive', 'additive_status', 'instance_count')},
            'contact_residue_count': len(partner['ordinals']), 'in_place_count': None, 'absent_outside_count': None,
            'absent_within_count': None, 'F': None, 'E': None}


def grade_chain(rank_row, chain, alignment, target_ca, target_sequence):
    """The sheet row of one hit chain. ``rank_row`` is its search-sheet row; ``chain`` what the unit read from the entry file
    (``None`` when the hit was not reached or the file was not obtained: ``chain`` then is the status string); ``alignment`` the
    driver's pair or ``None``."""
    row = {'rank': rank_row['rank'], 'entry': rank_row['pdb_entry'], 'chain': rank_row['pdb_chain'],
           'target_id': rank_row['target_id'], 'accession': rank_row['accession'], 'product': rank_row['product'],
           'B': rank_row['B'], 'status': None, 'usalign': None, 'partners': [], 'protein_partners': [], 'contact_residues': [],
           'dropped': [], 'F': None, 'E': None}
    if isinstance(chain, str):
        return {**row, 'status': chain}
    if chain['status'] != 'parsed':
        return {**row, 'status': chain['status']}
    row['protein_partners'] = chain['protein_partners']
    if alignment is None or alignment['status'] != 'aligned':
        return {**row, 'status': 'alignment_failed', 'partners': [_unscored(partner) for partner in chain['partners']]}
    row['usalign'] = {key: alignment[key] for key in ('tm_score_1', 'tm_score_2', 'rmsd_A', 'aligned_length', 'seq_id',
                                                       'length_1', 'length_2')}
    functional = sorted({ordinal for partner in chain['partners'] if not partner['additive'] and partner['kind'] in FUNCTIONAL_KINDS
                         for ordinal in partner['ordinals']})
    scored, dropped = residue_rows(functional, chain, alignment, target_ca, target_sequence)
    by_position = {item['hit_position']: item for item in scored}
    for item in scored:
        item['partners'] = sorted(partner_key(p['kind'], p['identifier']) for p in chain['partners']
                                  if not p['additive'] and p['kind'] in FUNCTIONAL_KINDS and item['hit_position'] in p['ordinals'])
    partners = []
    for partner in chain['partners']:
        base = _unscored(partner)
        if partner['additive'] or partner['kind'] not in FUNCTIONAL_KINDS:
            partners.append(base)
            continue
        items = [by_position[o] for o in partner['ordinals'] if o in by_position]
        score = _mean([item['score'] for item in items])
        partners.append({**base, 'in_place_count': sum(item['state'] == 'aligned' for item in items),
                         'absent_outside_count': sum(item['absent'] == 'outside_the_alignment' for item in items),
                         'absent_within_count': sum(item['absent'] == 'within_the_alignment' for item in items),
                         'F': score, 'E': None if score is None else rank_row['B'] * score})
    hit_score = _mean([item['score'] for item in scored])
    return {**row, 'status': 'graded' if scored else 'no_functional_partner', 'partners': partners,
            'contact_residues': scored, 'dropped': [*chain['dropped'], *dropped], 'F': hit_score,
            'E': None if hit_score is None else rank_row['B'] * hit_score}


def aggregate(hit_rows):
    """``(products, partners)``: the candidates of the two tests from the graded hit rows. ``products``: per product ``{'product',
    'hits_asked', 'hits_with_partners', 'mean_E', 'mean_F'}`` (``mean_E`` null when no hit has a functional partner); ``partners``:
    per key ``{'candidate', 'kind', 'identifier', 'hit_count', 'mean_E', 'mean_F', 'hits': [{'rank', 'B', 'F', 'E'}]}``, in the order
    the keys first appear (rank order)."""
    by_product, by_partner = {}, {}
    for row in hit_rows:
        if row['product'] is not None and row['status'] in ('graded', 'no_functional_partner', 'no_partner_in_entry'):
            by_product.setdefault(row['product'], []).append(row)
        for partner in row['partners']:
            if partner['E'] is not None:
                entry = by_partner.setdefault(partner_key(partner['kind'], partner['identifier']),
                                              {'kind': 'ligand' if partner['kind'] == 'ligand' else 'nucleic_acid',
                                               'identifier': partner['identifier'] if partner['kind'] == 'ligand' else partner['kind'],
                                               'hits': []})
                entry['hits'].append({'rank': row['rank'], 'entry': row['entry'], 'chain': row['chain'], 'B': row['B'],
                                      'F': partner['F'], 'E': partner['E'], 'contact_residue_count': partner['contact_residue_count']})
    products = []
    for product, members in by_product.items():
        with_partners = [member for member in members if member['E'] is not None]
        products.append({'product': product, 'hits_asked': len(members), 'hits_with_partners': len(with_partners),
                         'mean_E': _mean([m['E'] for m in with_partners]), 'mean_F': _mean([m['F'] for m in with_partners])})
    partners = [{'candidate': key, 'kind': entry['kind'], 'identifier': entry['identifier'], 'hit_count': len(entry['hits']),
                 'mean_E': _mean([h['E'] for h in entry['hits']]), 'mean_F': _mean([h['F'] for h in entry['hits']]),
                 'hits': entry['hits']} for key, entry in by_partner.items()]
    return products, partners


def picture_rows(hit_rows):
    """The measurements of both tests of the hits graded so far, as ``differential_credit`` takes them (``test``, ``candidate``,
    ``value``): the candidate picture the unit's settling rule compares between batches."""
    products, partners = aggregate(hit_rows)
    return ([{'test': CONTACTS_TEST + '@picture', 'candidate': 'product:' + row['product'], 'value': row['mean_E']}
             for row in products if row['mean_E'] is not None]
            + [{'test': PARTNERS_TEST + '@picture', 'candidate': row['candidate'], 'value': row['mean_E']} for row in partners])


def grade_partner_contacts(search_sheet, file_rows, hit_chains, alignments, target_ca, target_sequence, *, search_source_ref,
                           additive_list, files_not_reached):
    """The two sheets of one (search): ``(contacts_sheet, partners_sheet_without_source)``.

    ``file_rows``: per entry file the unit asked, in order: ``{'entry', 'assembly', 'url', 'status' (FILE_STATUSES), 'reason',
    'download_bytes', 'download_sha256', 'unpacked_bytes', 'file_ref', 'chain_count_asked'}``; ``hit_chains``: ``{rank:
    chain facts or a status string}`` for the hits of the asked files; ``alignments``: ``{rank: driver pair}``; ``additive_list``:
    the facts of the retained list (url, date, sha256, count); ``files_not_reached``: the number of entry files the settling rule
    never asked. Returns the contacts sheet (its ``partners`` are not in it: they are the second sheet's) and the second sheet's
    body; the caller adds ``contacts_source_ref`` once the first source exists."""
    rows = []
    for rank_row in asked_rows(search_sheet):
        chain = hit_chains.get(rank_row['rank'], 'not_asked')
        rows.append(grade_chain(rank_row, chain, alignments.get(rank_row['rank']), target_ca, target_sequence))
    products, partners = aggregate(rows)
    hits_with = [row for row in rows if row['E'] is not None]
    additive_counts = {}
    for row in rows:
        for partner in row['partners']:
            if partner['additive']:
                additive_counts.setdefault(partner['identifier'], set()).add(row['rank'])
    protein_partner_hits = sum(1 for row in rows if row['protein_partners'])
    common = {'search_source_ref': search_source_ref, 'search_database': search_sheet['database'],
              'search_model_sha256': search_sheet['model']['model_sha256'], 'contact_A': CONTACT_A,
              'kernel_scale_A': FEATURE_SCALE_A, 'residue_classes': list(CLASSES), 'absent_places': list(ABSENT_PLACES)}
    contacts = {'schema': CONTACTS_SCHEMA, 'provider': CONTACTS_PROVIDER, **common, 'additive_list': additive_list,
                'entries_asked': sum(f['status'] not in SKIPPED_FILE_STATUSES for f in file_rows),
                'entries_skipped_no_partner': sum(f['status'] == 'no_partner_in_entry' for f in file_rows),
                'entries_skipped_contents_unknown': sum(f['status'] == 'entry_contents_unknown' for f in file_rows),
                'entries_parsed': sum(f['status'] == 'parsed' for f in file_rows),
                'entries_too_large': sum(f['status'] == 'too_large' for f in file_rows),
                'entries_not_obtained': sum(f['status'] == 'not_obtained' for f in file_rows),
                'entries_unreadable': sum(f['status'] == 'unreadable' for f in file_rows),
                'entries_not_asked': files_not_reached, 'hits_asked_count': len(rows),
                'hits_not_asked_count': sum(row['status'] == 'not_asked' for row in rows),
                'hits_with_partners': len(hits_with), 'hits_with_protein_partners': protein_partner_hits,
                'candidates_measured': sum(row['mean_E'] is not None for row in products),
                'candidates_without_partner': sum(row['mean_E'] is None for row in products),
                'entries': file_rows, 'candidates': products, 'hits': rows}
    bound = {'schema': PARTNERS_SCHEMA, 'provider': PARTNERS_PROVIDER, **common,
             'hits_with_partners': len(hits_with), 'candidates_measured': len(partners),
             'additive_partners': [{'identifier': name, 'hit_count': len(ranks)} for name, ranks in sorted(additive_counts.items())],
             'candidates': partners}
    return contacts, bound


__all__ = ['ADDITIVE_STATUSES', 'CONTACT_A', 'CONTACTS_PROVIDER', 'CONTACTS_SCHEMA', 'CONTACTS_TEST', 'FILE_STATUSES',
           'FUNCTIONAL_KINDS', 'HIT_STATUSES', 'KINDS', 'SKIPPED_FILE_STATUSES', 'PARTNERS_PROVIDER', 'PARTNERS_SCHEMA', 'PARTNERS_TEST', 'aggregate',
           'asked_rows', 'grade_chain', 'grade_partner_contacts', 'partner_key', 'picture_rows', 'residue_rows']
