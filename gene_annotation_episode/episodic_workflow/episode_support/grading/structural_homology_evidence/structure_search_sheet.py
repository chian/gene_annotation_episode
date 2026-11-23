"""The grader and the sheet of one structure search of one database with one model of the target (A102, round 1: a
Foldseek ``tmalign`` search; ``readers/protein_structure/foldseek_result.py`` gives the hit rows).

One search is one test. The value of a hit is the existing A102 index B (``scoring.geometry``, unchanged):
``B = [2 n / (L_target + L_reference)] / [1 + (RMSD / 2 A)^2]``. What this module adds is only how its inputs are obtained:

* ``n`` and the distances are those of the aligned residue pairs the server reported (``qAln``/``dbAln``), once the hit's
  C-alpha atoms are superposed on the model's by least squares. The server returns the alignment and the hit's C-alpha
  coordinates but no superposition (``foldseek_result``), so the superposition is the EXISTING pure function
  ``calculations.protein_structure_calculations.fit_ca_transform`` (unweighted Kabsch/SVD; its transform is
  ``moving y @ R + t`` in the fixed frame; here fixed = the model's C-alpha, moving = the hit's). ``fit_ca_transform`` takes
  its pairs and its selection as the contract records of the protein-structure sheet, so ``_fit`` is only the call adapter
  that gives it those records for these pairs (one explicit selection of all of them, every C-alpha present); it is no new
  superposition. The distances are the lengths of ``y @ R + t - x`` of the fitted transform it returns, in angstroms.
* ``geometry`` takes the distances and the two lengths and nothing else (it computes n and the RMSD from the distances
  itself): ``target_length`` is the length of the supplied target sequence (the target stays the denominator) and
  ``reference_length`` is the hit's ``dbLen``. Nothing is passed that ``geometry`` does not take.
* The model's C-alpha coordinates are ``model_ca`` (``{residue index (1-based, the numbering of the query sequence the
  server read from the model file): (x, y, z)}``). The model may not cover every residue: an aligned pair whose query
  residue has no coordinate is dropped and COUNTED (``dropped_pairs``).
* A hit with fewer than 3 usable pairs, or whose superposition is not unique (collinear or degenerate pairs), gets NO value
  (``B`` null with a ``no_value_reason``), never a zero. A value of zero is a measured value; a missing one is not.

THE SELF CONTROL (``LIB/knowledge/structural_homology_evidence/native-structural-homology.md``: "Identical model copies are
controls"). When the model's origin is ``alphafold_db`` and a hit is the model's own entry (the hit's target id is
``AF-<the model's accession>-F<n>-model_v<n>``: the same entry, not one of its isoforms, which are other sequences), that hit is
the model compared with itself. Its row carries ``control`` ``model_itself`` and its measurement is kept as the facts
``control_B`` and ``control_rmsd_A``, but it names no candidate (``product`` null, ``named`` false, ``B`` null) and so gives no
value to any candidate: it is in no candidate's mean and in no candidate's hit count (``control_count`` counts it). Other
entries with the same sequence are separate models and count like any hit. A model of another origin has no control row (an
ESMFold model is in no database). In ``pdb100`` there is no copy of an AlphaFold model: experimental coordinates of the same
protein are a different structure and COUNT as hits, so a ``pdb100`` search has no control row whatever the model's origin
(``is_model_itself`` matches only an AlphaFold DB target id).

THE ``pdb100`` HITS. A hit is a chain of a PDB entry: the row carries ``pdb_entry``, ``pdb_chain`` (the author chain id,
without a symmetry-copy suffix) and ``accession`` (the UniProt accession the chain is named by, or null: a chain with no
UniProt accession is asked and has no product), and ``chain_accession_count`` (more than 1: a chimeric chain, named by one of its
accessions). The row's ``asked`` says the chain was looked up. The reference length of B is ``dbLen``, the length of the chain
in the structure file: a solved construct can be a fragment of the protein, and B then uses the construct's length. A row of
``afdb-swissprot`` has these three keys null.

The grader holds no threshold: it does not say a hit is good or bad. The server's ``score`` and ``eval`` are kept as
reported (``score_as_reported``: in ``tmalign`` mode the query-normalised TM-score x 100; ``eval_as_reported``: the mean of
the query- and target-normalised TM-scores; Foldseek README, quoted in ``foldseek_result``), beside ``seq_id``, ``prob`` and
the extent. The model's facts (origin, accession, mean pLDDT, residues covered) are kept as facts that weigh nothing: a
prediction's confidence describes the model and is not similarity.

The sheet is controlled data: numbers, booleans, a vocabulary value (database, mode, model origin) and names that come from
a looked-up list (a product name of UniProt, an accession). The value of a product candidate in the test is the mean B of
its hits (replicates inside one test, as in A101); ``candidate_measurements`` reads it from the hit rows.
"""
import math
import re

import numpy as np

from gene_annotation_episode.episodic_workflow.episode_support.calculations.protein_structure_calculations import (
    fit_ca_transform)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.scoring import (
    geometry, VERSION as INDEX_VERSION)

SCHEMA = 'a102_structure_search_sheet'
PROVIDER = 'foldseek'
DATABASES = ('afdb-swissprot', 'pdb100')
MODES = ('tmalign',)
MODEL_ORIGINS = ('alphafold_db', 'esmfold', 'rcsb_pdb')
NAME_SOURCES = ('recommended', 'submitted')
MINIMUM_PAIRS = 3
# The numerical tolerances ``fit_ca_transform`` asks for (it has no defaults): double-precision roundoff scale for
# coordinates of tens of angstroms; they decide only whether a fit is declared degenerate.
NUMERICAL = {'svd_relative_tolerance': 1e-9, 'svd_absolute_tolerance_A2': 1e-9, 'geometry_absolute_tolerance_A': 1e-6,
             'rotation_orthogonality_tolerance': 1e-9, 'rotation_determinant_tolerance': 1e-9,
             'sse_roundoff_absolute_tolerance_A2': 1e-6, 'sse_roundoff_relative_tolerance': 1e-9}


def _require(condition, code):
    if not condition:
        raise ValueError('a102_structure_search_' + code)


def _vector(xyz):
    return {'value': [float(x) for x in xyz], 'state': 'present', 'reason': None, 'unit': 'angstrom', 'origin': 'observed'}


def _available(key):
    return {'candidate_atom_row_keys': [key], 'selected_atom_row_key': key, 'state': 'available', 'primary_reason': None,
            'qualifications': []}


def _fit(model_xyz, target_xyz):
    """The call adapter of ``fit_ca_transform``: ``model_xyz`` and ``target_xyz`` are the C-alpha coordinates of the same
    pairs, in pair order. Returns ``(distances in angstrom of the pairs after the fit, None)`` or ``(None, reason)``."""
    pairs, selectors, rows = [], [], []
    for index, (x, y) in enumerate(zip(model_xyz, target_xyz)):
        identifier = 'pair' + str(index)
        pairs.append({'correspondence_id': identifier, 'fixed_position_0based': index, 'moving_position_0based': index,
                      'fixed_atom_row_key': 'model:' + str(index), 'moving_atom_row_key': 'hit:' + str(index),
                      'fixed_xyz_A': _vector(x), 'moving_xyz_A': _vector(y),
                      'fixed_ca_state': _available('model:' + str(index)), 'moving_ca_state': _available('hit:' + str(index)),
                      'fixed_uncertainty_row_key': None, 'moving_uncertainty_row_key': None})
        selector = {'kind': 'correspondence_id', 'correspondence_id': identifier}
        selectors.append(selector)
        rows.append({'request_index_0based': index, 'selector': selector, 'correspondence_id': identifier,
                     'fixed_position_0based': index, 'moving_position_0based': index, 'available': True,
                     'primary_reason': None, 'qualifications': []})
    count = len(pairs)
    request = {'selection': {'kind': 'explicit', 'members': selectors}, 'rows': rows, 'requested_count': count,
               'resolved_pair_count': count, 'available_candidate_count': count}
    fit = fit_ca_transform(pairs, fit_request=request, missing_coordinate_policy='require_all',
                           numerical_parameters=NUMERICAL)
    if fit['state'] != 'performed':
        return None, 'superposition_not_unique' if fit['state'] == 'minimum_only' else 'superposition_' + fit['state']
    rotation = np.array(fit['transform']['rotation']['value'])
    translation = np.array(fit['transform']['translation']['value'])
    moved = np.array(target_xyz, dtype=float) @ rotation + translation
    return [float(d) for d in np.linalg.norm(moved - np.array(model_xyz, dtype=float), axis=1)], None


def measure_hit(hit, model_ca, target_length):
    """The measurement of one hit row (``foldseek_result``): ``{'aligned_pairs', 'usable_pairs', 'dropped_pairs', 'rmsd_A',
    'B', 'reference_length', 'target_coverage', 'no_value_reason'}``; ``B`` and ``rmsd_A`` are ``None`` with a reason when
    the hit has no value."""
    usable = [(model_ca[p['query']], p['target_xyz']) for p in hit['pairs'] if p['query'] in model_ca]
    result = {'aligned_pairs': len(hit['pairs']), 'usable_pairs': len(usable),
              'dropped_pairs': len(hit['pairs']) - len(usable), 'reference_length': hit['target_length'],
              'rmsd_A': None, 'B': None, 'target_coverage': len(usable) / target_length, 'no_value_reason': None}
    if len(usable) < MINIMUM_PAIRS:
        return {**result, 'no_value_reason': 'fewer_than_3_usable_pairs'}
    distances, reason = _fit([m for m, _ in usable], [t for _, t in usable])
    if reason is not None:
        return {**result, 'no_value_reason': reason}
    index = geometry(distances, target_length, hit['target_length'])
    return {**result, 'rmsd_A': index['rmsd_A'], 'B': index['B']}


def measure_hits(hits, model_ca, target_length):
    """``[measure_hit(hit)]`` in hit order: what the naming of the hits (``name_hits``: the hits in rank order with their B)
    and ``grade_structure_search`` (its ``measured`` argument) both read, so the superposition is done once."""
    _require(type(target_length) is int and target_length > 0, 'target_length_required')
    _require(isinstance(model_ca, dict) and all(type(k) is int and k >= 1 and len(v) == 3 and all(
        type(c) in (int, float) and math.isfinite(c) for c in v) for k, v in model_ca.items()), 'model_ca_shape')
    return [measure_hit(hit, model_ca, target_length) for hit in hits]


def _facts(model_facts):
    _require(isinstance(model_facts, dict) and set(model_facts) == {'origin', 'accession', 'mean_plddt', 'residues_covered',
                                                                    'model_sha256'}, 'model_facts_fields')
    _require(model_facts['origin'] in MODEL_ORIGINS, 'model_origin')
    _require(model_facts['accession'] is None or type(model_facts['accession']) is str, 'model_accession')
    _require(model_facts['mean_plddt'] is None or (type(model_facts['mean_plddt']) in (int, float)
                                                   and 0 <= model_facts['mean_plddt'] <= 100), 'model_mean_plddt')
    _require(type(model_facts['residues_covered']) is int and model_facts['residues_covered'] > 0, 'model_residues_covered')
    _require(type(model_facts['model_sha256']) is str and len(model_facts['model_sha256']) == 64, 'model_sha256')
    return dict(model_facts)


def _names(names):
    _require(isinstance(names, dict) and set(names) == {'products', 'asked', 'function_identifiers', 'not_looked_up'}, 'names_fields')
    _require(isinstance(names['function_identifiers'], dict) and set(names['function_identifiers']) <= set(names['asked'])
             and all(isinstance(found, list) and all(isinstance(item, dict) and set(item) == {'source', 'identifier'}
                                                     and type(item['source']) is str and type(item['identifier']) is str
                                                     for item in found)
                     for found in names['function_identifiers'].values()), 'function_identifiers')
    _require(set(names['products']) <= set(names['asked']), 'named_but_not_asked')
    _require(set(names['function_identifiers']) == set(names['products']) and set(names['not_looked_up']) <= set(names['products']),
             'identifiers_of_the_named')
    for entry in names['products'].values():
        _require(isinstance(entry, dict) and set(entry) == {'product', 'name_source'} and type(entry['product']) is str
                 and entry['product'] and entry['name_source'] in NAME_SOURCES, 'name_entry')
    return names['products'], set(names['asked']), names['function_identifiers'], set(names['not_looked_up'])


def is_model_itself(hit, model_facts):
    """Whether ``hit`` is the entry the model itself is (the self control, see the module): the model is an AlphaFold DB model
    of the accession and the hit's target id is that entry's own model, ``AF-<accession>-F<n>-model_v<n>``."""
    return (model_facts['origin'] == 'alphafold_db' and model_facts['accession'] is not None
            and re.fullmatch('AF-' + re.escape(model_facts['accession']) + r'-F\d+-model_v\d+', hit['target_id']) is not None)


def grade_structure_search(hits, model_ca, target_length, names, *, database, mode, model_facts, measured=None):
    """The sheet ``a102_structure_search_sheet`` of one search.

    ``hits``: the parsed hit rows (``parse_foldseek_result(...)['hits']``); ``model_ca``, ``target_length``: see the module;
    ``names``: ``{'products': {accession: {'product', 'name_source'}}, 'asked': [accessions asked], 'function_identifiers':
    {accession: [{'source', 'identifier'}]} of each NAMED accession, 'not_looked_up': [named accessions whose BV-BRC family
    lookup was not made or failed]}`` (the function-level identifiers of the protein, kept on the row of a named hit as
    ``function_identifiers``, and ``family_looked_up`` false for an accession in ``not_looked_up``; what
    ``uniprot_hit_names.name_hits`` gives, or ``pdb_chain_proteins.name_pdb_hits``: a ``pdb100`` hit then carries its chain's
    ``pdb`` dict with ``entry``, ``chain``, ``accessions`` and ``asked``, ``accession`` being the one the chain is named by; a hit not in ``asked`` was NOT ASKED, a hit asked and not in ``products`` was asked
    and has no name); ``model_facts``: ``origin``, ``accession``, ``mean_plddt``, ``residues_covered`` and ``model_sha256`` (the
    hash of the model file searched: with the database it identifies the search); ``measured``: ``measure_hits`` of the same
    hits when the caller already holds it.

    The sheet: the schema, the index profile (``scoring.VERSION``), ``provider``, ``database``, ``mode``,
    ``target_length``, ``hit_count``, ``named_count`` (hits with a product), ``control_count`` (hits that are the model itself), ``not_asked_count`` (hits never asked,
    controls excepted),
    ``no_name_count`` (asked, no product, controls excepted), ``valued_count`` (hits with a B), ``model`` (the facts: weigh nothing),
    ``candidates`` (per product: ``hit_count`` of its hits with a B and the ``mean_B``: its value in this test; a product
    none of whose hits has a B is listed with ``mean_B`` null) and ``hits`` (the rows listed in the module docstring)."""
    _require(database in DATABASES and mode in MODES, 'database_or_mode')
    products, asked, identifiers, not_looked_up = _names(names)
    facts = _facts(model_facts)
    measured = measure_hits(hits, model_ca, target_length) if measured is None else measured
    _require(len(measured) == len(hits), 'measured_does_not_match_the_hits')
    rows = []
    for hit, value in zip(hits, measured):
        pdb = hit['pdb']
        _require((pdb is None) == (database == 'afdb-swissprot') and (pdb is not None or hit['accession'] is not None),
                 'hit_is_not_of_the_database')
        itself = is_model_itself(hit, facts)
        name = None if itself or hit['accession'] is None else products.get(hit['accession'])
        rows.append({'rank': hit['rank'], 'accession': hit['accession'], 'target_id': hit['target_id'],
                     'pdb_entry': None if pdb is None else pdb['entry'], 'pdb_chain': None if pdb is None else pdb['chain'],
                     'chain_accession_count': None if pdb is None else len(pdb['accessions']),
                     'control': 'model_itself' if itself else None, 'control_B': value['B'] if itself else None,
                     'control_rmsd_A': value['rmsd_A'] if itself else None,
                     'asked': pdb['asked'] if pdb is not None else hit['accession'] in asked, 'named': name is not None,
                     'product': None if name is None else name['product'],
                     'name_source': None if name is None else name['name_source'],
                     'function_identifiers': [] if name is None else identifiers[hit['accession']],
                     'family_looked_up': name is not None and hit['accession'] not in not_looked_up,
                     'B': None if itself else value['B'],
                     'no_value_reason': None if itself else value['no_value_reason'], 'aligned_pairs': value['aligned_pairs'],
                     'usable_pairs': value['usable_pairs'], 'dropped_pairs': value['dropped_pairs'],
                     'rmsd_A': value['rmsd_A'], 'target_length': target_length,
                     'reference_length': value['reference_length'], 'target_coverage': value['target_coverage'],
                     'seq_id': hit['seq_id'], 'score_as_reported': hit['score_as_reported'],
                     'eval_as_reported': hit['eval_as_reported'], 'prob': hit['prob']})
    candidates = {}
    for row in rows:
        if row['product'] is not None:
            candidates.setdefault(row['product'], []).append(row['B'])
    return {'schema': SCHEMA, 'profile': INDEX_VERSION, 'provider': PROVIDER, 'database': database, 'mode': mode,
            'target_length': target_length, 'hit_count': len(rows), 'named_count': sum(r['named'] for r in rows),
            'not_asked_count': sum(not r['asked'] and r['control'] is None for r in rows),
            'no_name_count': sum(r['asked'] and not r['named'] and r['control'] is None for r in rows),
            'control_count': sum(r['control'] is not None for r in rows),
            'valued_count': sum(r['B'] is not None for r in rows), 'model': facts,
            'candidates': [{'product': product, 'hit_count': sum(b is not None for b in values),
                            'mean_B': (math.fsum(b for b in values if b is not None) / sum(b is not None for b in values)
                                       if any(b is not None for b in values) else None)}
                           for product, values in candidates.items()],
            'hits': rows}


__all__ = ['grade_structure_search', 'measure_hits', 'measure_hit', 'SCHEMA', 'PROVIDER', 'DATABASES', 'MODES',
           'MODEL_ORIGINS', 'NAME_SOURCES', 'MINIMUM_PAIRS']
