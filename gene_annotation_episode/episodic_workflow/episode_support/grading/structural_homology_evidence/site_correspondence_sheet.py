"""The grader and the sheet of A102's ``site_correspondence``: does the target have, in place, the functional residues of the
proteins that a graded structure search found? The fold search cannot tell the members of a family apart; this test can (a
matching fold with the catalytic residues present supports the candidate; a matching fold that lacks the candidate's
zinc-coordinating residues does not).

INPUTS. One held graded structure search (its sheet ``a102_structure_search_sheet``: the hits with accession, product, B and
the control flag; its parsed result: the aligned pairs and the hits' C-alpha coordinates; each hit's own sequence ``tSeq``;
the model's C-alpha by target position and the target's sequence as the server read it) and the site rows of the hits'
accessions of ONE site source (``annotated``: UniProt active-site, binding-site and site features; ``catalytic``: M-CSA
catalytic residues; ``tools/.../site_annotations``). The sites come as ``feature_row`` rows (a range is one required residue
per position).

THE RULE, per hit that is not a control, has a product and a B (the hits that can enter a candidate's mean) and has at least
one site residue:

* each required residue is a position ``r`` of the hit, with the hit's residue ``h = tSeq[r]``. A residue that cannot be read
  is DROPPED with its reason, never scored: ``position_beyond_hit_sequence`` (``r`` is past the hit's sequence),
  ``hit_numbering_is_an_isoform`` (the hit is an isoform model, ``AF-<accession>-<n>-F1-...``, whose numbering is not the
  entry's canonical numbering that both sources use), ``residue_differs_from_source`` (the source states the residue letter
  (M-CSA) and the hit has another one at ``r``), ``target_position_has_no_coordinate`` (aligned to a target position the
  model has no C-alpha for). A position covered by several features is one required residue (its feature types are listed).
* (a) ``r`` aligned to a target position ``q`` in the search's alignment? Not aligned: the residue is ABSENT in the target; its
  score is 0 and it STAYS in the denominator (missing machinery counts against the candidate). The sheet records WHERE it is
  absent (``absent``): ``outside_the_alignment`` (``r`` lies before the first or after the last aligned hit position: a part
  of the matched protein the target was not aligned to, for example another domain) or ``within_the_alignment`` (a gap inside
  the aligned span: the target lacks the residue there). The value rule is the same for both (the target lacks that machinery
  either way); per hit and per candidate the sheet counts both kinds.
* (b) class match: 1 when the target's residue at ``q`` equals ``h`` or shares a residue role class with it, else 0. The classes
  are ``CHEMICAL_ROLES`` of ``records/structural_homology_evidence/attachments.py`` (acidic DE, basic KR, aromatic FWY, hydroxyl
  STY, amide NQ, sulfur CM, small AGS; S belongs to two of them, so S matches T, Y, A and G); the role classes are defined by
  sequence: they are not a demonstration of charge or catalysis.
* (c) geometry: the distance ``d`` between the model's C-alpha at ``q`` and the hit's C-alpha at ``r`` AFTER the search's own
  superposition of all its usable aligned pairs: the same fit as ``structure_search_sheet._fit`` (the adapter of
  ``fit_ca_transform`` that ``measure_hits`` uses) on the same pairs (the pairs whose target residue the model covers), by
  ``superposed_distances``, which repeats its numerical operations without its record validation (same numbers). The site
  residues never enter the fit. The kernel is ``k = 1 / (1 + (d / 1 A)^2)`` (the formula inside ``scoring.feature_sheet``, with its feature
  scale of 1 A; ``feature_sheet`` itself needs a comparison grade and witness records of the old store and is not called).
* the residue score is the class match times ``k``; the hit's ``F`` is the mean of its residue scores (absent residues 0); its
  ``E = B * F`` with ``B`` the search sheet's B of that hit (the existing rule E = B F).

A candidate's value in the test is the mean ``E`` over its hits that have sites. A candidate none of whose hits has a site gets
NO measurement (``mean_E`` null), never a zero. The grader holds no threshold. Kept as facts, per hit: accession, product,
feature rows (type, positions, ChEBI id or null, evidence codes), per residue (hit position, hit residue, target position or
null, target residue or null, class match, distance, kernel, score), the dropped residues with their reasons, ``F``, ``B``,
``E``; per candidate: hits with sites, ``mean_E``, ``mean_F``; and the totals. The sheet is controlled data: numbers,
booleans, vocabulary values (site source, feature type, state, reason), residue letters, ChEBI and ECO identifiers, accessions
and the product names of UniProt.

The sheet names the search it grades (``search_source_ref``, ``search_database``, ``search_model_sha256``), so a repeat of the
same (search, site source) is recognised by the reader (``candidate_measurements.held_site_tests``)."""
import math

import numpy as np

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.structure_search_sheet import (
    SCHEMA as SEARCH_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.foldseek_result import (
    ALPHAFOLD_TARGET)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.attachments import (
    CHEMICAL_ROLES)

SCHEMA = 'a102_site_correspondence_sheet'
PROVIDER = 'site_correspondence'
SITE_SOURCES = ('annotated', 'catalytic')
FEATURE_SCALE_A = 1.0
STATES = ('aligned', 'absent')
ABSENT_PLACES = ('outside_the_alignment', 'within_the_alignment')
DROP_REASONS = ('position_beyond_hit_sequence', 'hit_numbering_is_an_isoform', 'residue_differs_from_source',
                'target_position_has_no_coordinate', 'location_not_exact')
CLASSES = tuple(CHEMICAL_ROLES.values())


def _require(condition, code):
    if not condition:
        raise ValueError('a102_site_correspondence_' + code)


def kernel(distance_A):
    """The kernel of one residue: ``1 / (1 + (d / 1 A)^2)``, in (0, 1]."""
    return 1 / (1 + (distance_A / FEATURE_SCALE_A) ** 2)


def class_match(target_residue, hit_residue):
    """1 when the residues are equal or share a residue role class (``CHEMICAL_ROLES``), else 0."""
    return int(target_residue == hit_residue or any(target_residue in letters and hit_residue in letters for letters in CLASSES))


def asked_hits(search_sheet):
    """The hit rows of a search sheet this test asks sites for: not a control, with a product and a B (the hits that can enter a
    candidate's mean), in rank order."""
    _require(search_sheet['schema'] == SEARCH_SHEET, 'search_sheet_required')
    return [row for row in search_sheet['hits']
            if row['control'] is None and row['product'] is not None and row['B'] is not None]


def required_positions(features):
    """``({position: [feature types covering it]}, [dropped rows for features whose location is not exact])``: the required
    residues of a hit from its feature rows (each position of a range is one residue)."""
    required, dropped = {}, []
    for index, feature in enumerate(features):
        if feature['start'] is None:
            dropped.append({'hit_position': None, 'reason': 'location_not_exact', 'feature_index': index})
            continue
        for position in range(feature['start'], feature['end'] + 1):
            types = required.setdefault(position, [])
            if feature['type'] not in types:
                types.append(feature['type'])
    return required, dropped


def superposed_distances(model_xyz, target_xyz):
    """The distances in angstrom of the pairs after the least-squares superposition of ``target_xyz`` onto ``model_xyz``: the
    numerical core of ``structure_search_sheet._fit`` (``fit_ca_transform``), with the same operations in the same order (centroids,
    SVD of the cross-covariance, the reflection sign, ``R = U diag(1, 1, sign) Vt``, ``t = xb - yb R``, ``y R + t``), so the numbers
    are those of ``_fit``. ``_fit`` also builds and validates, for every pair, the record shapes of the general fit result; that
    is about nine tenths of its 0.23 s per hit of 353 pairs and does not change a number. A hit asked here has a B, so the same
    pairs were fitted by ``measure_hits`` and that fit was unique: the checks of ``fit_ca_transform`` that refuse a fit (fewer than
    3 pairs, a rank below 2, a tie of singular values) cannot occur."""
    x, y = np.array(model_xyz, dtype=float), np.array(target_xyz, dtype=float)
    xb, yb = x.mean(axis=0), y.mean(axis=0)
    u, _, vt = np.linalg.svd((y - yb).T @ (x - xb), full_matrices=True)
    sign = 1 if float(np.linalg.det(u @ vt)) >= 0 else -1
    rotation = u @ np.diag([1.0, 1.0, float(sign)]) @ vt
    translation = xb - yb @ rotation
    moved = y @ rotation + translation
    return [float(d) for d in np.linalg.norm(moved - x, axis=1)]


def _hit_distances(hit, model_ca):
    """``{query position: distance in angstrom after the search's superposition}`` for the usable aligned pairs of ``hit`` (the
    pairs ``structure_search_sheet.measure_hit`` fits), by ``superposed_distances``."""
    usable = [pair for pair in hit['pairs'] if pair['query'] in model_ca]
    distances = superposed_distances([model_ca[pair['query']] for pair in usable], [pair['target_xyz'] for pair in usable])
    return {pair['query']: distance for pair, distance in zip(usable, distances)}


def grade_hit(row, hit, hit_sequence, model_ca, query_sequence, features):
    """The sheet row of one asked hit: ``row`` its search-sheet row, ``hit`` its parsed hit (``foldseek_result``), ``hit_sequence``
    its ``tSeq``, ``features`` its ``feature_row`` list."""
    found = ALPHAFOLD_TARGET.match(hit['target_id'])
    isoform = found is not None and found.group(2) is not None
    required, dropped = required_positions(features)
    by_target = {pair['target']: pair['query'] for pair in hit['pairs']}
    first, last = min(by_target), max(by_target)
    distances = None
    residues = []
    letters = {}
    for feature in features:
        if feature['residue'] is not None and feature['start'] is not None:
            letters[feature['start']] = feature['residue']
    for position in sorted(required):
        base = {'hit_position': position, 'feature_types': required[position]}
        if isoform:
            dropped.append({'hit_position': position, 'reason': 'hit_numbering_is_an_isoform'})
            continue
        if position > len(hit_sequence):
            dropped.append({'hit_position': position, 'reason': 'position_beyond_hit_sequence'})
            continue
        residue = hit_sequence[position - 1]
        if position in letters and letters[position] != residue:
            dropped.append({'hit_position': position, 'reason': 'residue_differs_from_source'})
            continue
        query = by_target.get(position)
        if query is None:
            residues.append({**base, 'hit_residue': residue, 'state': 'absent',
                             'absent': 'outside_the_alignment' if position < first or position > last else 'within_the_alignment',
                             'target_position': None,
                             'target_residue': None, 'class_match': None, 'distance_A': None, 'kernel': None, 'score': 0.0})
            continue
        if query not in model_ca:
            dropped.append({'hit_position': position, 'reason': 'target_position_has_no_coordinate'})
            continue
        if distances is None:
            distances = _hit_distances(hit, model_ca)
        target_residue = query_sequence[query - 1]
        match = class_match(target_residue, residue)
        value = kernel(distances[query])
        residues.append({**base, 'hit_residue': residue, 'state': 'aligned', 'absent': None, 'target_position': query,
                         'target_residue': target_residue, 'class_match': match, 'distance_A': distances[query],
                         'kernel': value, 'score': match * value})
    has_sites = bool(residues)
    score = math.fsum(item['score'] for item in residues) / len(residues) if has_sites else None
    return {'rank': row['rank'], 'accession': row['accession'], 'product': row['product'], 'B': row['B'],
            'features': features, 'has_sites': has_sites, 'residues': residues, 'dropped': dropped,
            'residue_count': len(residues), 'absent_count': sum(item['state'] == 'absent' for item in residues),
            'absent_outside_count': sum(item['absent'] == 'outside_the_alignment' for item in residues),
            'absent_within_count': sum(item['absent'] == 'within_the_alignment' for item in residues),
            'F': score, 'E': None if score is None else row['B'] * score}


def grade_site_correspondence(search_sheet, hits, hit_sequences, model_ca, query_sequence, sites, *, site_source,
                              search_source_ref):
    """The sheet ``a102_site_correspondence_sheet`` of one (search, site source).

    ``search_sheet``: the retained sheet of the graded search; ``hits``: the parsed hits of its result (``parse_foldseek_result(
    ...)['hits']``, rank order); ``hit_sequences``: each hit's ``tSeq``, in the same order; ``model_ca``: ``{target position:
    (x, y, z)}`` (``foldseek_search.model_positions``); ``query_sequence``: the sequence the server read from the model
    (``parsed['query_sequence']``), whose position ``q`` is the target position ``q``; ``sites``: ``{accession: [feature_row]}``
    for every accession of ``asked_hits`` (an accession without an entry is an error: unknown is not siteless);
    ``site_source``; ``search_source_ref``: the held source of the search.

    The sheet: schema, ``provider``, ``site_source``, the search it grades (``search_source_ref``, ``search_database``,
    ``search_model_sha256``), ``kernel_scale_A``, ``residue_classes``, the totals ``hits_asked``, ``hits_with_sites``,
    ``candidates_measured`` and ``candidates_without_site``, ``candidates`` (per product: ``hits_asked``, ``hits_with_sites``,
    ``mean_E`` and ``mean_F``, null when no hit has a site, and the sums over its hits with sites of ``absent_outside_count`` and
    ``absent_within_count``) and ``hits`` (one row per asked hit, see ``grade_hit``)."""
    _require(site_source in SITE_SOURCES, 'site_source')
    _require(len(hits) == len(hit_sequences) == search_sheet['hit_count'], 'hits_do_not_match_the_search_sheet')
    rows = []
    for row in asked_hits(search_sheet):
        hit = hits[row['rank'] - 1]
        _require(hit['rank'] == row['rank'] and hit['accession'] == row['accession'], 'hit_is_not_the_sheet_hit')
        _require(row['accession'] in sites, 'sites_not_asked_for:' + row['accession'])
        rows.append(grade_hit(row, hit, hit_sequences[row['rank'] - 1], model_ca, query_sequence, sites[row['accession']]))
    by_product = {}
    for row in rows:
        by_product.setdefault(row['product'], []).append(row)
    candidates = []
    for product, members in by_product.items():
        with_sites = [member for member in members if member['has_sites']]
        candidates.append({'product': product, 'hits_asked': len(members), 'hits_with_sites': len(with_sites),
                           'absent_outside_count': sum(m['absent_outside_count'] for m in with_sites),
                           'absent_within_count': sum(m['absent_within_count'] for m in with_sites),
                           'mean_E': math.fsum(m['E'] for m in with_sites) / len(with_sites) if with_sites else None,
                           'mean_F': math.fsum(m['F'] for m in with_sites) / len(with_sites) if with_sites else None})
    return {'schema': SCHEMA, 'provider': PROVIDER, 'site_source': site_source, 'search_source_ref': search_source_ref,
            'search_database': search_sheet['database'], 'search_model_sha256': search_sheet['model']['model_sha256'],
            'kernel_scale_A': FEATURE_SCALE_A, 'residue_classes': list(CLASSES), 'hits_asked': len(rows),
            'hits_with_sites': sum(row['has_sites'] for row in rows),
            'candidates_measured': sum(c['hits_with_sites'] > 0 for c in candidates),
            'candidates_without_site': sum(c['hits_with_sites'] == 0 for c in candidates),
            'candidates': candidates, 'hits': rows}


__all__ = ['ABSENT_PLACES', 'CLASSES', 'DROP_REASONS', 'FEATURE_SCALE_A', 'PROVIDER', 'SCHEMA', 'SITE_SOURCES', 'STATES', 'asked_hits',
           'class_match', 'grade_hit', 'grade_site_correspondence', 'kernel', 'required_positions', 'superposed_distances']
