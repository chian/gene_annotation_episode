"""The measurements of the candidate annotations of A101, read from the graded sources an episode holds, and the
table the head shows and returns (the owner's differential credit of 2026-11-20; ``differential_credit.py`` is the
arithmetic, this module only reads).

``candidate_measurements(reader, scope, sources)`` returns the measurements ``differential_credit`` takes, in the
order of ``sources`` (the order the episode obtained them: ``held_sources``). It reads only through ``reader`` (the
custody reader of the episode): the held sources and their retained gradings. One measurement is one reference's
graded result for one target of the scope, valued by the existing subscore of A101 (``compile_native_sheet`` over that
reference's alignments, the target's length and the scope's regions of the target); nothing is recalculated.

ONE TEST IS ONE GRADED SOURCE: one job or tool run, made under the same conditions for every candidate it measured.
Its name is the kind of test below followed by ``@<source reference>``, so two jobs of one method on different inputs
(two alignments of different candidate sets) are two tests and are never pooled as
replicates, and a later test never changes an earlier test's differentials. Replicates are the measurements of one
candidate within one test (the hits of one search that share a product).

The kinds of held graded source read, by the content of their retained sheet:

* a database search with names (a ``blast_database_sheet`` whose ``reference_metadata`` gives each hit its functions):
  test ``database_search:<provider>:<program>:<database>``; each hit names a candidate of vocabulary ``product``: its
  function as the sheet's reference metadata gives it (for BV-BRC that is the ``product`` of the feature, never its
  ``annotation`` field); its value is the subscore of that hit's alignments. A hit with no function names no candidate
  and is counted as unlabelled. Hits with the same function are replicates of that candidate in the test.
* a profile scan (``hmmer_search_sheet_v1`` of ``hmmscan``): test ``profile_scan:<database name>``; each matched family
  is a candidate of vocabulary ``profile_family`` (identifier: its accession, name: its name, as the profile database
  gives them); its value is the subscore of its domains.
* a pairwise comparison (``blast_pairwise_sheet_v1``): test ``pairwise:<program>``; the reference sequence record
  it was compared with is a candidate of vocabulary ``reference_sequence`` (identifier: its record reference, name: the
  record's name); its value is the subscore of its alignments.

* a multiple sequence alignment (``msa_alignment_sheet_v1``): test ``msa:<provider>:<aligner>:<alphabet>``; the owner's
  conserved-site count (2026-11-21): the residue conservation pattern of one candidate group against another
  differentiates function, so the same residue pattern on the same conserved sites adds nothing. A distinguishing site is
  identified by (target position, the group's conserved residue, the group's candidate), never by column or job
  (``msa_alignment_sheet.conserved_sites`` records them). Evidence is cumulative over the head's alignments, in arrival
  order: only the sites not identified by an earlier alignment count. For each candidate with at least one new
  distinguishing site, one measurement: value = (its number of NEW matched sites, where the target carries the group's
  conserved residue) x ``SITE_WEIGHT`` (= 1 / ``EXPECTED_DISTINGUISHING_SITES``), the owner's weighting. Mismatched sites
  give no value (the sheet records them). The measurement also records ``fraction`` (new matched / (new matched + new
  mismatched)), ``new_matched`` and ``new_mismatched``. An alignment that adds no new site gives no measurement. Unlike
  the other tests an alignment's value is not capped at 1: an alignment that finds the expected number of sites earns about 1,
  and a candidate's msa sheet cannot exceed (the target's length) x ``SITE_WEIGHT``, because a site counts once.
  ``unidentified_positions`` gives, per candidate, the target positions that no held alignment has yet identified as a site
  of it (what the ceiling reads).
* a graded clustering (``cluster_sheet_v1``, the all-vs-all child): test ``cluster:<method>`` (``cluster:mcl``; one test per
  graded clustering, as every test is named, so ``@<source>`` follows); the sheet's groups are the candidate groups (the
  sequences of one ``product`` candidate in the set; the target is in no group), and for each candidate group with a sequence
  in the set one measurement: its value is the SHARE of the group's sequences that fall in the target's cluster (0 to 1), the
  same scale as the other tests (about 1 for a strong typical result, as the other tests' values; the MSA's count is weighted
  by W = 1 / E to land there). A candidate with no sequence in the set gives no measurement. The measurement also records
  ``size`` and ``in_target_cluster``. ``cluster`` is a subscoring sheet like ``msa`` and ``database_search``: a candidate's
  value on it is the sum of its values in the clustering tests.
* a MetaCATS report (``metacats_sheet_v1``) gives no measurement: its significant positions are kept on its own sheet and
  confirm which distinguishing sites are statistically supported; they are not used as a filter of the sites.

A candidate is identified by its vocabulary and its identifier (its name when it has none). Candidates of different
vocabularies are different candidates: nothing merges a family with a product or a sequence.

Arrival order: ``held_sources`` is the order of the reader's ``refs()``, the receipt order of custody: the records
the parent passed in, in the order given, then those its own units produced or its children returned, in the order of
the units. The summary's ``held_record_refs`` is the same order. It is the same on every recomputation and on resume,
because the receipts are recorded once, in the journal's row order.

The measurements of different targets are never compared: ``candidate_table`` runs ``differential_credit`` on each
target of the scope and the credit is the sum over the targets."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    _regions)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.cluster_sheet import (
    SCHEMA as CLUSTER_SHEET, group_values)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.differential_credit import (
    differential_credit, standing)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    compile_native_sheet, hmmer_comparisons, route_native_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)

VOCABULARIES = ('product', 'profile_family', 'reference_sequence')
DATABASE_SHEETS = ('blast_database_sheet_v1', 'blast_database_sheet_v2', 'blast_database_sheet_v3')
PAIRWISE_SHEET = 'blast_pairwise_sheet_v1'
PROFILE_SHEET = 'hmmer_search_sheet_v1'
MSA_SHEET = 'msa_alignment_sheet_v1'
# The owner (2026-11-21): "if you expect 10 conserve sites per protein on average, you would make the weighting 0.1 -- now I
# don't know how many conserved regions there generally are, so you will have to figure that out".
# E is the expected number of distinguishing sites of one candidate in one alignment, derived from the stored real alignments
# (a direct check, 2026-11-21): 7 distinct alignments of E. coli CspA (70 residues) from runs a101_conserved_ws_C2,
# a101_returns_ws_R1, a101_msa_ws_M1, a101_msa_ws_M2 (also in metacats_ws_C1), graded by ``conserved_sites``: 23 candidate
# counts (matched + mismatched at a target position), 3 3 4 4 5 5 5 5 5 6 7 7 7 8 11 12 12 12 12 14 14 15 15, median 7, mean
# 8.3 (10 per 100 residues at the median). All targets had 70 residues, so whether length matters cannot be told from
# this data and E is the median count, not a per-residue figure. Re-derive E as more alignments (and targets of other
# lengths) accumulate: then a per-residue figure x the target's length may replace it.
EXPECTED_DISTINGUISHING_SITES = 7
SITE_WEIGHT = 1 / EXPECTED_DISTINGUISHING_SITES


def held_sources(reader):
    """The sources the episode holds, in the order it obtained them (receipt order)."""
    return [ref for ref in reader.refs() if ref.startswith('source_')]


def _measurement(target, test, vocabulary, name, identifier, value, source, extra=None):
    return {'target': target, 'test': test, 'candidate': vocabulary + ':' + (identifier or name), 'value': value,
            'vocabulary': vocabulary, 'name': name, 'identifier': identifier, 'source': source, **(extra or {})}


def _by(rows, key):
    grouped = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row)
    return grouped


def search_hits(grading, value_of):
    """The hits of a database search with names, one row per (hit, product name) in hit order: ``hit_index``, ``product``
    (the function the sheet's reference metadata gives it), ``value`` (the subscore of that hit's alignments), and the
    hit's ``accession``, ``aa_sequence_md5``, ``aa_length`` and ``feature_id`` (BV-BRC's feature fields; ``None`` where the metadata has
    none), plus ``unlabelled`` (a hit that names no product gives one row with ``product`` ``None``)."""
    sheet = grading['sheet']
    rows = _by(route_native_grading(grading), 'hit_index')
    found = []
    for hit in sheet['hits']:
        names = {}
        for association in hit['associations']:
            if association['metadata_index'] is None:
                continue
            metadata = sheet['reference_metadata'][association['metadata_index']]
            for function in metadata['functions']:
                if function['function']:
                    names.setdefault(function['function'], (metadata['accession'], function.get('bvbrc_feature', {})))
        value = value_of(rows.get(hit['hit_index'], []))
        if not names:
            found.append({'hit_index': hit['hit_index'], 'product': None, 'value': value, 'accession': None,
                          'aa_sequence_md5': None, 'aa_length': None, 'feature_id': None})
        found.extend({'hit_index': hit['hit_index'], 'product': name, 'value': value, 'accession': accession,
                      'aa_sequence_md5': feature.get('aa_sequence_md5'), 'aa_length': feature.get('aa_length'),
                      'feature_id': feature.get('feature_id')}
                     for name, (accession, feature) in names.items())
    return found


def _database_search(source, grading, value_of):
    search = grading['sheet']['normalized_result']['search']
    test = 'database_search:' + source['provider'] + ':' + search['program'] + ':' + search['request']['database']
    rows = search_hits(grading, value_of)
    found = [(test, 'product', row['product'], None, row['value']) for row in rows if row['product'] is not None]
    return found, sum(1 for row in rows if row['product'] is None)


def new_site_values(sites, seen, target):
    """The measurements of one alignment's conserved-site section (``msa_alignment_sheet.conserved_sites``) given the
    sites the head's earlier alignments already identified. ``sites`` is the section's ``sites``; ``seen`` is the set of
    identified sites (target, target position, the group's conserved residue, the group's candidate), which this call
    extends with the sites it counts (matched or mismatched). Only a distinguishing site not in ``seen`` and with a target
    position counts (a site at a target gap has no position and is identified by nothing). Returns ``[(candidate, value,
    fraction, new_matched, new_mismatched)]``: for each candidate with at least one new site, ``value`` = new matched x
    ``SITE_WEIGHT`` and ``fraction`` = new matched / (new matched + new mismatched); a candidate with no new site gives
    nothing."""
    new = {}
    for site in sites:
        key = (target, site['target_position'], site['residue'], site['candidate'])
        if site['target_position'] is None or key in seen:
            continue
        seen.add(key)
        new.setdefault(site['candidate'], []).append(site['matched'])
    return [(candidate, sum(found) * SITE_WEIGHT, sum(found) / len(found), sum(found), len(found) - sum(found))
            for candidate, found in new.items()]


def _held_msa(source, grading, seen):
    """A graded multiple sequence alignment (``msa_alignment_sheet_v1``): test ``msa:<provider>:<aligner>:<alphabet>``;
    one measurement per candidate with new distinguishing sites (``new_site_values``): its candidate is the ``product`` the
    search gave it (the same candidate identity, so the same candidate on the list); its value is its new matched sites x
    ``SITE_WEIGHT``; the measurement records ``fraction``, ``new_matched`` and ``new_mismatched`` too. Evidence is
    cumulative over the head's alignments in arrival order (``seen``): the same residue pattern on the same conserved
    sites adds nothing, and an alignment that adds no new site gives no measurement."""
    sheet = grading['sheet']
    test = 'msa:' + source['provider'] + ':' + sheet['aligner'] + ':' + sheet['alphabet']
    target = source['operand_refs'][0]
    return [(test, 'product', candidate, None, value,
             {'fraction': fraction, 'weight': SITE_WEIGHT, 'new_matched': matched, 'new_mismatched': mismatched})
            for candidate, value, fraction, matched, mismatched
            in new_site_values(sheet['conserved_sites']['sites'], seen, target)], 0


def _held_cluster(source, grading):
    """A graded clustering (``cluster_sheet_v1``): test ``cluster:<method>``; one measurement per candidate group with a
    sequence in the set (``cluster_sheet.group_values``), value = the share of its sequences in the target's cluster."""
    sheet = grading['sheet']
    test = 'cluster:' + sheet['method']
    return [(test, 'product', candidate, None, share, {'size': size, 'in_target_cluster': inside})
            for candidate, share, size, inside in group_values(sheet)], 0


def _profile_scan(source, grading, value_of):
    accessions = {hit['target_name']: hit['target_accession'] for hit in grading['sheet']['hits']}
    families = _by(hmmer_comparisons(grading), 'target_name')
    test = 'profile_scan:' + source['accession']
    return [(test, 'profile_family', name, accessions[name], value_of(rows)) for name, rows in families.items()], 0


def _pairwise(reader, source, grading, value_of):
    reference = source['operand_refs'][1]
    record = reader.get(reference)
    test = 'pairwise:' + grading['sheet']['input']['search']['program']
    return [(test, 'reference_sequence', record.get('name') or record.get('label'), reference,
             value_of(route_native_grading(grading)))], 0


def _read(reader, scope, sources):
    """The measurements in arrival order, the unlabelled hits of each target and the identified conserved sites (target,
    target position, residue, candidate name) of the held alignments."""
    scope = reader.validate_scope(scope)
    measurements, unlabelled = [], {target: 0 for target in scope['subject_refs']}
    identified = set()
    for reference in sources:
        source = reader.get(reference)
        for entry in source_tool_grading_entries(reader, reference):
            grading = entry['grading']
            sheet = grading['sheet']
            if sheet['schema'] in DATABASE_SHEETS and sheet['reference_metadata']:
                read = _database_search
            elif sheet['schema'] == PROFILE_SHEET and sheet['operation']['program'] == 'hmmscan':
                read = _profile_scan
            elif sheet['schema'] == MSA_SHEET:
                read = lambda s, g, v: _held_msa(s, g, identified)
            elif sheet['schema'] == CLUSTER_SHEET:
                read = lambda s, g, v: _held_cluster(s, g)
            elif sheet['schema'] == PAIRWISE_SHEET:
                read = lambda s, g, v: _pairwise(reader, s, g, v)
            else:
                continue
            target = source['operand_refs'][0]
            if target not in scope['subject_refs']:
                continue
            length, regions = reader.subject_length(target), _regions(reader, scope, target)
            found, missing = read(source, grading, lambda rows: compile_native_sheet(
                rows, supplied_length=length, regions=regions)['value'])
            unlabelled[target] += missing
            measurements.extend(_measurement(target, row[0] + '@' + reference, *row[1:5], reference, *row[5:]) for row in found)
    return measurements, unlabelled, identified


def candidate_measurements(reader, scope, sources):
    """The measurements (``{'test', 'candidate', 'value'}`` and what the head shows: ``target``, ``vocabulary``,
    ``name``, ``identifier``, ``source``) of the graded ``sources`` over ``scope``, in the order of ``sources``."""
    return _read(reader, scope, sources)[0]


def candidate_standing(reader, scope, sources):
    """Where each candidate stands, per target of the scope (``{target: differential_credit.standing(its
    measurements)}``), after the graded ``sources``: what a further test's ceiling is computed from."""
    measurements, _, _ = _read(reader, scope, sources)
    return {target: standing(rows) for target, rows in _by(measurements, 'target').items()}


def unidentified_positions(reader, scope, sources):
    """Per target of the scope, ``{candidate: positions}`` for each candidate (``product:<name>``) that a held alignment has
    identified a site of: the number of the target's positions that no held alignment has identified as a matched or a
    mismatched site of it. A candidate absent from the result has all the target's positions."""
    scope = reader.validate_scope(scope)
    identified = _read(reader, scope, sources)[2]
    remaining = {}
    for target in scope['subject_refs']:
        taken = {}
        for site_target, position, _, candidate in identified:
            if site_target == target:
                taken.setdefault(candidate, set()).add(position)
        length = reader.subject_length(target)
        remaining[target] = {'product:' + candidate: length - len(positions) for candidate, positions in taken.items()}
    return remaining


def _entry(measurements, candidate):
    first = next(row for row in measurements if row['candidate'] == candidate)
    return {'vocabulary': first['vocabulary'], 'name': first['name'],
            **({} if first['identifier'] is None else {'identifier': first['identifier']})}


def candidate_table(reader, scope, sources):
    """What the head shows and returns, per target of the scope (``targets``: target reference -> ``candidates``
    (one row per admitted candidate, highest score first, ties in arrival order: its vocabulary, name and
    identifier, its ``score``, the ``tests`` it has undergone, its ``measurement_count`` and its ``best_value``),
    ``tests`` (each test applied to the target with ``candidate_count``, the admitted candidates it measured),
    ``differentials`` (each: the ``test``, the two candidates and the ``value``), ``unlabelled_hit_count`` and the
    target's ``credit``), and the ``credit`` of the scope: the sum over its targets."""
    measurements, unlabelled, _ = _read(reader, scope, sources)
    targets = {}
    for target, rows in _by(measurements, 'target').items():
        result = differential_credit(rows)
        candidates = [{**_entry(rows, candidate), 'score': score, 'sheets': [{'sheet': kind, 'value': value} for kind, value in result['sheets'][candidate].items()],
                       'tests': list(dict.fromkeys(row['test'] for row in rows if row['candidate'] == candidate)),
                       'measurement_count': sum(1 for row in rows if row['candidate'] == candidate),
                       'best_value': max(row['value'] for row in rows if row['candidate'] == candidate)}
                      for candidate, score in result['scores'].items()]
        arrival = list(dict.fromkeys(row['candidate'] for row in rows))
        candidates.sort(key=lambda row: (-row['score'], arrival.index(row['vocabulary'] + ':' + row.get('identifier', row['name']))))
        tests = [{'test': test, 'candidate_count': len({row['candidate'] for row in rows
                                                        if row['test'] == test and row['candidate'] in result['scores']})}
                 for test in dict.fromkeys(row['test'] for row in rows)]
        differentials = [{'test': row['test'], 'first': _entry(rows, row['pair'][0]),
                          'second': _entry(rows, row['pair'][1]), 'value': row['value']}
                         for row in result['differentials']]
        targets[target] = {'candidates': candidates, 'tests': tests, 'differentials': differentials,
                           'unlabelled_hit_count': unlabelled[target], 'credit': result['credit']}
    for target, count in unlabelled.items():
        targets.setdefault(target, {'candidates': [], 'tests': [], 'differentials': [],
                                    'unlabelled_hit_count': count, 'credit': 0.0})
    return {'targets': targets, 'credit': math.fsum(row['credit'] for row in targets.values())}
