"""The measurements of the candidate annotations of A102, read from the graded sources an episode holds, and the table the head
shows and returns: A102's own copy of the reader pattern of A101's ``candidate_measurements`` (the owner's differential credit
of 2026-11-20; ``differential_credit.py`` beside this file is the arithmetic, this module only reads).

``candidate_measurements(reader, scope, sources)`` returns the measurements ``differential_credit`` takes, in the order of
``sources`` (the order the episode obtained them: ``held_sources``). It reads only through ``reader`` (the custody reader of
the episode): the held sources and their retained gradings (``tool_grading_artifacts.source_tool_grading_entries``, this
folder's own; its records have the shape A101's ``retain_tool_grading`` makes). One measurement is one hit's index B on a
graded structure-search sheet; nothing is recalculated.

ONE TEST IS ONE GRADED SOURCE: one search of one database with one model of the target. Its name is
``structure_search:foldseek:tmalign:<database>@<source reference>`` (the sheet's provider, mode and database, then the
source), so two searches (another database, another model) are two tests and are never pooled as replicates. Replicates are
the hits of one search that share a product. A candidate is a product, ``product:<name>`` (UniProt's recommended protein
name of the hit's accession); its value in the test is the mean B of its hits, which is the sheet's ``mean_B`` for it. A hit
that names no candidate gives no measurement: a hit never asked (``not_asked``: its name is unknown, not absent), a hit asked
that carries no name (``no_product``) and a hit with a name but no value (``no_value``: fewer than 3 usable pairs; never
read as a value of zero) are counted apart, per target.

THE SECOND TEST, ``site_correspondence`` (``site_correspondence_sheet``): one graded source is one (search, site source) and its
name is ``site_correspondence:<site source>@<source reference>`` (the source that holds the grading). A candidate is the same
``product:<name>``; its value is the sheet's ``mean_E`` for it (the mean E = B F of its hits with sites). A candidate none of
whose hits has a site has no measurement (``mean_E`` null), never a zero. ``held_site_tests`` gives the (search source
reference, site source) pairs already graded, so a repeat can be refused.

The model's facts on the sheet weigh nothing and are not read here. A source whose target is not in the scope is skipped; a
retained grading of another sheet schema is not A102's round 1 and is skipped."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.differential_credit import (
    differential_credit, standing)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.site_correspondence_sheet import (
    SCHEMA as SITE_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.structure_search_sheet import (
    SCHEMA as SEARCH_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)

VOCABULARIES = ('product',)


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


def test_name(sheet, source):
    """The test of the search graded in ``sheet`` made by the held source ``source``."""
    return ':'.join(('structure_search', sheet['provider'], sheet['mode'], sheet['database'])) + '@' + source


def site_test_name(sheet, source):
    """The test of the site correspondence graded in ``sheet`` made by the held source ``source``."""
    return 'site_correspondence:' + sheet['site_source'] + '@' + source


def site_rows(sheet):
    """The ``(product, mean_E)`` of the candidates of a site-correspondence sheet that have a value (at least one hit with
    sites), in the sheet's order."""
    return [(row['product'], row['mean_E']) for row in sheet['candidates'] if row['mean_E'] is not None]


def search_rows(sheet):
    """The hit rows of a search sheet that name a candidate: ``(product, B)`` in rank order, for the hits with a product
    and a value."""
    return [(row['product'], row['B']) for row in sheet['hits'] if row['product'] is not None and row['B'] is not None]


def _read(reader, scope, sources):
    """The measurements in arrival order and, per target of the scope, the hits that name no candidate (``{'not_asked',
    'no_product', 'no_value'}``)."""
    scope = reader.validate_scope(scope)
    measurements = []
    unnamed = {target: {'not_asked': 0, 'no_product': 0, 'no_value': 0} for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            if sheet['schema'] not in (SEARCH_SHEET, SITE_SHEET):
                continue
            target = source['operand_refs'][0]
            if target not in scope['subject_refs']:
                continue
            if sheet['schema'] == SITE_SHEET:
                measurements.extend(_measurement(target, site_test_name(sheet, reference), 'product', product, None, value,
                                                 reference) for product, value in site_rows(sheet))
                continue
            test = test_name(sheet, reference)
            measurements.extend(_measurement(target, test, 'product', product, None, value, reference)
                                for product, value in search_rows(sheet))
            unnamed[target]['not_asked'] += sheet['not_asked_count']
            unnamed[target]['no_product'] += sheet['no_name_count']
            unnamed[target]['no_value'] += sum(1 for row in sheet['hits'] if row['product'] is not None and row['B'] is None)
    return measurements, unnamed


def candidate_measurements(reader, scope, sources):
    """The measurements (``{'test', 'candidate', 'value'}`` and what the head shows: ``target``, ``vocabulary``, ``name``,
    ``identifier``, ``source``) of the graded ``sources`` over ``scope``, in the order of ``sources``."""
    return _read(reader, scope, sources)[0]


def candidate_standing(reader, scope, sources):
    """Where each candidate stands, per target of the scope (``{target: differential_credit.standing(its
    measurements)}``), after the graded ``sources``: what a further test's ceiling is computed from."""
    return {target: standing(rows) for target, rows in _by(candidate_measurements(reader, scope, sources), 'target').items()}


def held_searches(reader, scope, sources):
    """Per target of the scope, the searches the episode holds, as ``(database, model_sha256)`` in arrival order: the pair
    that, with the target, identifies a search. A further search of the same target with the same database and model is a
    repeat (it adds nothing) and the head's request check refuses it: the options it needs to do so."""
    scope = reader.validate_scope(scope)
    held = {target: [] for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        target = source['operand_refs'][0] if source.get('operand_refs') else None
        if target not in held:
            continue
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            if sheet['schema'] == SEARCH_SHEET:
                held[target].append((sheet['database'], sheet['model']['model_sha256']))
    return held


def held_site_tests(reader, scope, sources):
    """Per target of the scope, the site-correspondence tests the episode holds, as ``(search source reference, site source)``
    in arrival order: the pair that identifies one such test. A further test of the same pair is a repeat (it adds nothing) and
    the request check refuses it."""
    scope = reader.validate_scope(scope)
    held = {target: [] for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        target = source['operand_refs'][0] if source.get('operand_refs') else None
        if target not in held:
            continue
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            if sheet['schema'] == SITE_SHEET:
                held[target].append((sheet['search_source_ref'], sheet['site_source']))
    return held


def _entry(measurements, candidate):
    first = next(row for row in measurements if row['candidate'] == candidate)
    return {'vocabulary': first['vocabulary'], 'name': first['name'],
            **({} if first['identifier'] is None else {'identifier': first['identifier']})}


def candidate_table(reader, scope, sources):
    """What the head shows and returns, per target of the scope (``targets``: target reference -> ``candidates`` (one row per
    admitted candidate, highest score first, ties in arrival order: its vocabulary, name and identifier, its ``score``, the
    ``sheets`` and ``tests`` it has undergone, its ``measurement_count`` and its ``best_value``), ``tests`` (each test applied
    to the target with ``candidate_count``, the admitted candidates it measured), ``differentials`` (each: the ``test``, the
    two candidates and the ``value``), ``not_asked_hit_count`` (the hits of searches whose name was never asked: the naming
    stopped once the candidates settled), ``no_product_hit_count`` (the hits asked that carry no name), ``no_value_hit_count``
    (the hits with a name and no value) and the target's ``credit``), and the ``credit`` of the scope: the sum over its
    targets."""
    measurements, unnamed = _read(reader, scope, sources)
    targets = {}
    for target, rows in _by(measurements, 'target').items():
        result = differential_credit(rows)
        candidates = [{**_entry(rows, candidate), 'score': score,
                       'sheets': [{'sheet': kind, 'value': value} for kind, value in result['sheets'][candidate].items()],
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
                           'not_asked_hit_count': unnamed[target]['not_asked'],
                           'no_product_hit_count': unnamed[target]['no_product'],
                           'no_value_hit_count': unnamed[target]['no_value'], 'credit': result['credit']}
    for target, counts in unnamed.items():
        targets.setdefault(target, {'candidates': [], 'tests': [], 'differentials': [],
                                    'not_asked_hit_count': counts['not_asked'], 'no_product_hit_count': counts['no_product'],
                                    'no_value_hit_count': counts['no_value'], 'credit': 0.0})
    return {'targets': targets, 'credit': math.fsum(row['credit'] for row in targets.values())}
