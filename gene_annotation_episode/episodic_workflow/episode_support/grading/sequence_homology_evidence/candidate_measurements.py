"""The measurements of the candidate annotations of A101, read from the graded sources an episode holds, and the
table the head shows and returns (the owner's differential credit of 2026-11-20; ``differential_credit.py`` is the
arithmetic, this module only reads).

``candidate_measurements(reader, scope, sources)`` returns the measurements ``differential_credit`` takes, in the
order of ``sources`` (the order the episode obtained them: ``held_sources``). It reads only through ``reader`` (the
custody reader of the episode): the held sources and their retained gradings. One measurement is one reference's
graded result for one target of the scope, valued by the existing subscore of A101 (``compile_native_sheet`` over that
reference's alignments, the target's length and the scope's regions of the target); nothing is recalculated.

Three kinds of held graded source are read, by the content of their retained sheet:

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
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.differential_credit import (
    differential_credit)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    compile_native_sheet, hmmer_comparisons, route_native_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)

VOCABULARIES = ('product', 'profile_family', 'reference_sequence')
DATABASE_SHEETS = ('blast_database_sheet_v1', 'blast_database_sheet_v2', 'blast_database_sheet_v3')
PAIRWISE_SHEET = 'blast_pairwise_sheet_v1'
PROFILE_SHEET = 'hmmer_search_sheet_v1'


def held_sources(reader):
    """The sources the episode holds, in the order it obtained them (receipt order)."""
    return [ref for ref in reader.refs() if ref.startswith('source_')]


def _measurement(target, test, vocabulary, name, identifier, value, source):
    return {'target': target, 'test': test, 'candidate': vocabulary + ':' + (identifier or name), 'value': value,
            'vocabulary': vocabulary, 'name': name, 'identifier': identifier, 'source': source}


def _by(rows, key):
    grouped = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row)
    return grouped


def _database_search(source, grading, value_of):
    sheet = grading['sheet']
    search = sheet['normalized_result']['search']
    test = 'database_search:' + source['provider'] + ':' + search['program'] + ':' + search['request']['database']
    rows = _by(route_native_grading(grading), 'hit_index')
    found, unlabelled = [], 0
    for hit in sheet['hits']:
        names = list(dict.fromkeys(
            function['function'] for association in hit['associations']
            for function in sheet['reference_metadata'][association['metadata_index']]['functions']
            if function['function']))
        unlabelled += not names
        value = value_of(rows.get(hit['hit_index'], []))
        found.extend((test, 'product', name, None, value) for name in names)
    return found, unlabelled


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
    """The measurements in arrival order and the unlabelled hits of each target."""
    scope = reader.validate_scope(scope)
    measurements, unlabelled = [], {target: 0 for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        for entry in source_tool_grading_entries(reader, reference):
            grading = entry['grading']
            sheet = grading['sheet']
            if sheet['schema'] in DATABASE_SHEETS and sheet['reference_metadata']:
                read = _database_search
            elif sheet['schema'] == PROFILE_SHEET and sheet['operation']['program'] == 'hmmscan':
                read = _profile_scan
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
            measurements.extend(_measurement(target, *row, reference) for row in found)
    return measurements, unlabelled


def candidate_measurements(reader, scope, sources):
    """The measurements (``{'test', 'candidate', 'value'}`` and what the head shows: ``target``, ``vocabulary``,
    ``name``, ``identifier``, ``source``) of the graded ``sources`` over ``scope``, in the order of ``sources``."""
    return _read(reader, scope, sources)[0]


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
    measurements, unlabelled = _read(reader, scope, sources)
    targets = {}
    for target, rows in _by(measurements, 'target').items():
        result = differential_credit(rows)
        candidates = [{**_entry(rows, candidate), 'score': score,
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
