"""The grader and the sheet of A102's ``ligand_transplants``: which ligands and cofactors have a place in the target's model, as they
sit in solved homologs (AlphaFill, https://alphafill.eu, Hekkelman et al. 2023, https://www.nature.com/articles/s41592-022-01685-y).

INPUT. The answer of AlphaFill for the accession of one AlphaFold DB model the episode holds (``tools/.../ligand_transplants``),
as one of three outcomes: ``transplants`` (HTTP 200 with hits), ``no_transplants`` (HTTP 200 with ``hits`` null: the model exists and
nothing was transplanted) and ``no_alphafill_entry`` (HTTP 404 with AlphaFill's not-found body). Only AlphaFill's numbers are used,
never its coordinates, so the held model's frame does not enter.

THE RULE (design note ``docs/plan/designs/a102_ligand_transplants.md``). Per transplant (a row; facts copied from the response):
the donor ``pdb_id`` and ``pdb_asym_id``, ``compound_id`` (the donor's chemical component) and ``analogue_id`` (what AlphaFill
placed), the alignment ``identity`` and ``length``, ``global_rmsd_A``, ``local_rmsd_A``, ``clash_score_A``, ``clash_count``,
``transplant_atom_count``, ``pae_mean``, ``additive`` and ``target_residues`` (the distinct target residue numbers of the clash
distances: the model's residues near the placed ligand, UniProt numbering). Two degrees, each the axis's kernel
``1 / (1 + (x / s)^2)`` (``site_correspondence_sheet.kernel`` at ``x / s``): ``fit`` of ``local_rmsd_A`` and ``no_clash`` of
``clash_score_A``; a transplant's value is ``fit x no_clash``, in (0, 1]. A listed additive (BioLiP's list, applied by
``compound_id`` as ``partner_contacts`` applies it) is recorded and gets no value and no candidate. A candidate is
``ligand:<compound_id>`` (the same name ``partner_contacts`` gives a ligand); its value is the value of its BEST transplant (AlphaFill
places a compound again only when its centroid is at least 3.5 A from an identical one already placed, so several transplants of one
compound are different places, not replicates of one measurement), with the count of its transplants. The donor's identity, the global
RMSD and the PAE weigh nothing. The grader holds no boundary: it copies the facts and applies the two scales below.

The sheet is controlled data: numbers, booleans, vocabulary values (outcome), chemical component ids, PDB ids and chain ids, the
version and date AlphaFill states, and record references."""
import re

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.site_correspondence_sheet import (
    kernel)

SCHEMA = 'a102_ligand_transplants_sheet'
PROVIDER = 'ligand_transplants'
OUTCOMES = ('transplants', 'no_transplants', 'no_alphafill_entry')
# The scale of each degree is AlphaFill's own published boundary between high and medium confidence (paper, "Analysis of the quality
# of AlphaFill databank transplants": the local r.m.s.d. above the third quartile plus 1.5 interquartile ranges for transplants of 70%
# identity or higher, 0.92 A, and the transplant clash score likewise, 0.64 A; the web table colours by the same values), so a
# transplant at the boundary has degree one half and the fall is gradual, never a cut. (The paper's low-confidence boundaries are
# 3.10 A and 1.27 A, where the degrees are 0.081 and 0.203.)
FIT_SCALE_A = 0.92
NO_CLASH_SCALE_A = 0.64
# "Currently, we are transplanting 2,694 different compounds that represent over 95% of all ligand occurrences in the Protein Data
# Bank (PDB)" (the paper, same article): the most distinct compounds a response can hold. A response with more distinct
# non-additive compounds is a fault (``ValueError``), so the ceiling of the test, which rests on this number, holds by construction.
ELIGIBLE_COMPOUNDS = 2694
# What AlphaFill answers for an accession it has no entry for: HTTP 404 with exactly this body (probe of 2026-11-21).
NOT_FOUND_BODY = {'error': 'The requested web page was not found on this server.'}
RESPONSE_KEYS = {'alphafill_version', 'date', 'file', 'hits', 'id'}
MODEL_FILE = re.compile(r'-model_v(\d+)\.cif\.gz$')


def _require(condition, code):
    if not condition:
        raise ValueError('a102_ligand_transplants_' + code)


def transplant_rows(body, additives):
    """The rows of every transplant of a response with hits, hit by hit in the response's order."""
    rows = []
    for hit in body['hits']:
        alignment = hit['alignment']
        for transplant in hit['transplants']:
            clash = transplant['clash']
            additive = transplant['compound_id'] in additives
            fit, no_clash = kernel(transplant['local_rmsd'] / FIT_SCALE_A), kernel(clash['score'] / NO_CLASH_SCALE_A)
            rows.append({
                'pdb_id': hit['pdb_id'], 'pdb_asym_id': hit['pdb_asym_id'], 'compound_id': transplant['compound_id'],
                'analogue_id': transplant['analogue_id'], 'identity': alignment['identity'], 'length': alignment['length'],
                'global_rmsd_A': hit['global_rmsd'], 'local_rmsd_A': transplant['local_rmsd'], 'clash_score_A': clash['score'],
                'clash_count': clash['clash_count'], 'transplant_atom_count': clash['transplant_atom_count'],
                'pae_mean': transplant['pae'].get('mean'), 'additive': additive,
                'target_residues': sorted({row['poly_atom']['seq_id'] for row in clash['distances']}),
                'fit': None if additive else fit, 'no_clash': None if additive else no_clash,
                'value': None if additive else fit * no_clash})
    return rows


def candidates(rows):
    """The ligand candidates of the rows: per non-additive ``compound_id`` (first appearance first) its transplant count and the
    value of its best transplant (``best_row``: its index in ``rows``; the first on a tie)."""
    found = {}
    for index, row in enumerate(rows):
        if not row['additive']:
            found.setdefault(row['compound_id'], []).append(index)
    return [{'candidate': 'ligand:' + name, 'kind': 'ligand', 'identifier': name, 'transplant_count': len(indices),
             'best_value': rows[best]['value'], 'best_row': best}
            for name, indices in found.items() for best in [max(indices, key=lambda index: rows[index]['value'])]]


def grade_ligand_transplants(outcome, body, *, model, additives, additive_list):
    """The sheet of one answer of AlphaFill. ``outcome`` is one of ``OUTCOMES``; ``body`` the parsed JSON; ``model`` the held model
    ``{'model_ref', 'accession', 'sha256', 'version'}``; ``additives`` the BioLiP list (``{component id: name}``) and
    ``additive_list`` its facts (url, date, sha256, count)."""
    _require(outcome in OUTCOMES, 'outcome_unknown')
    common = {'schema': SCHEMA, 'provider': PROVIDER, 'model_ref': model['model_ref'], 'model_accession': model['accession'],
              'model_sha256': model['sha256'], 'held_model_version': model['version'], 'outcome': outcome,
              'fit_scale_A': FIT_SCALE_A, 'no_clash_scale_A': NO_CLASH_SCALE_A, 'eligible_compounds': ELIGIBLE_COMPOUNDS,
              'additive_list': additive_list}
    if outcome == 'no_alphafill_entry':
        _require(body == NOT_FOUND_BODY, 'not_found_body_differs')
        return {**common, 'alphafill_version': None, 'date': None, 'alphafill_model_version': None, 'model_version_differs': None,
                'hit_count': 0, 'transplant_count': 0, 'additive_count': 0, 'distinct_compound_count': 0, 'candidates_measured': 0,
                'rows': [], 'candidates': []}
    _require(set(body) == RESPONSE_KEYS, 'response_keys_differ')
    _require(body['id'] == 'AF-' + model['accession'] + '-F1', 'response_is_of_another_model')
    _require((body['hits'] is None) == (outcome == 'no_transplants'), 'outcome_does_not_match_the_hits')
    file = MODEL_FILE.search(body['file'])
    _require(file is not None, 'model_file_name_has_no_version')
    version = int(file.group(1))
    rows = [] if body['hits'] is None else transplant_rows(body, additives)
    found = candidates(rows)
    distinct = {row['compound_id'] for row in rows if not row['additive']}
    _require(len(distinct) <= ELIGIBLE_COMPOUNDS, 'more_compounds_than_alphafill_transplants')
    return {**common, 'alphafill_version': body['alphafill_version'], 'date': body['date'], 'alphafill_model_version': version,
            'model_version_differs': model['version'] != version,
            'hit_count': 0 if body['hits'] is None else len(body['hits']), 'transplant_count': len(rows),
            'additive_count': sum(row['additive'] for row in rows), 'distinct_compound_count': len(distinct),
            'candidates_measured': len(found), 'rows': rows, 'candidates': found}


__all__ = ['ELIGIBLE_COMPOUNDS', 'FIT_SCALE_A', 'NOT_FOUND_BODY', 'NO_CLASH_SCALE_A', 'OUTCOMES', 'PROVIDER', 'SCHEMA',
           'candidates', 'grade_ligand_transplants', 'transplant_rows']
