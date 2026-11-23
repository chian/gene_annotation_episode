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

THE FOURTH TEST, ``ligand_transplant`` (``ligand_transplants_sheet``): one graded source is one held AlphaFold DB model's AlphaFill
answer and its name is ``ligand_transplant:alphafill@<source reference>``. A candidate is ``ligand:<compound id>``; its value is the
value of its BEST transplant (one row per candidate). A model with no transplant or no AlphaFill entry has no measurement.
``held_transplant_models`` gives the models already tested, so a repeat can be refused.

THE SEVENTH TEST, ``partner_cofolding`` (``partner_cofolding_sheet``): one graded source is one co-folding of the target with several
held ligands and its name is ``partner_cofolding:chai1@<source reference>``. A candidate is ``ligand:<compound id>``; its value is the
mean over its samples of ``iptm`` (0 for a clashing sample).

THE FIFTH TEST, ``rna_family_scan`` (``rna_family_scan_sheet``): one graded source is one scan of an RNA target against a covariance
database and its name is ``rna_family_scan:<database>@<source reference>``. A candidate is ``rna_family:<Rfam accession>`` (the name
shown is the family's identifier); its value is the value of its BEST hit. A scan with no family has no measurement.
``held_rna_scans`` gives the scans held per target. THE SIXTH TEST, ``rna_structure_agreement`` (``rna_structure_agreement_sheet``):
one graded source is the agreement of one held scan's families and its name is ``rna_structure_agreement:rfam@<source reference>``
(the source that holds the grading); a candidate is the same ``rna_family:<accession>``; its value is the share of the family's
consensus pairs the target can form. A family whose consensus has no pair has no measurement (null, never a zero).
``held_rna_agreements`` gives the scans already tested per target, so a repeat can be refused.

A GROUPING (``candidate_grouping``: the groups of candidates a commissioner passes down, members named as the head returned
them) can be asked of ``candidate_measurements``, ``candidate_standing`` and ``candidate_table``: every measurement row of a member
is then read under the key of its group before ``differential_credit`` runs, so the rows of the members of one group in one test
are replicates of that test. ``None`` is no grouping. ``candidate_credit`` gives, per target, the ADMISSION part of the credit (the
sum of the entry scores, as found, never changed by a grouping) and the DISCRIMINATION part (the sum of the differentials' values)
under a grouping, and the credit that takes the highest discrimination over no grouping and the groupings given. An annotation
score is how well one candidate is supported (recomputed under any grouping); credit is the progress, which changes only when
the highest discrimination or the admission changes.

The model's facts on the sheet weigh nothing and are not read here. A source whose target is not in the scope is skipped; a
retained grading of another sheet schema is not A102's round 1 and is skipped."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_grouping import (
    apply_grouping, group_lookup, member_key)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.differential_credit import (
    differential_credit, standing)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.ligand_transplants_sheet import (
    SCHEMA as TRANSPLANT_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.partner_contacts_sheet import (
    CONTACTS_SCHEMA, PARTNERS_SCHEMA)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.partner_cofolding_sheet import (
    SCHEMA as COFOLDING_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.rna_family_scan_sheet import (
    SCHEMA as RNA_SCAN_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.rna_structure_agreement_sheet import (
    SCHEMA as RNA_AGREEMENT_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.site_correspondence_sheet import (
    SCHEMA as SITE_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.structure_search_sheet import (
    SCHEMA as SEARCH_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)

VOCABULARIES = ('product', 'ligand', 'nucleic_acid', 'rna_family')


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
    """The ``(product, E)`` of the matched proteins of a site-correspondence sheet that have sites, in the sheet's order: one
    row per protein, so a candidate's value in the test is the mean over its proteins (the sheet's ``mean_E`` for it), and
    under a grouping the mean over the proteins of all the group's members."""
    return [(row['product'], row['E']) for row in sheet['hits'] if row['has_sites']]


def partner_contacts_test_name(sheet, source):
    """The test of the partner contacts graded in ``sheet`` made by the held source ``source``: a ``site_correspondence`` test
    (one family) of site source ``partner_contacts``."""
    return 'site_correspondence:partner_contacts@' + source


def bound_partner_test_name(sheet, source):
    """The test of the bound partners graded in ``sheet`` made by the held source ``source``."""
    return 'bound_partner:' + sheet['search_database'] + '@' + source


def ligand_transplant_test_name(sheet, source):
    """The test of the ligand transplants graded in ``sheet`` made by the held source ``source``."""
    return 'ligand_transplant:alphafill@' + source


def ligand_transplant_rows(sheet):
    """The ``(vocabulary, identifier, best_value)`` of the ligand candidates of a ligand-transplants sheet: one row per candidate,
    the value of its best transplant."""
    return [(row['kind'], row['identifier'], row['best_value']) for row in sheet['candidates']]


def partner_cofolding_test_name(sheet, source):
    """The test of the partner co-folding graded in ``sheet`` made by the held source ``source``."""
    return 'partner_cofolding:chai1@' + source


def partner_cofolding_rows(sheet):
    """The ``(vocabulary, identifier, value)`` of the ligand candidates of a partner-cofolding sheet: one row per candidate, the mean
    over its samples of ``iptm`` (0 for a clashing sample)."""
    return [(row['kind'], row['identifier'], row['value']) for row in sheet['candidates']]


def rna_family_scan_test_name(sheet, source):
    """The test of the RNA family scan graded in ``sheet`` made by the held source ``source``."""
    return 'rna_family_scan:' + sheet['database'] + '@' + source


def rna_family_scan_rows(sheet):
    """The ``(vocabulary, name, identifier, best_value)`` of the family candidates of an RNA family scan sheet, in its order."""
    return [(row['kind'], row['name'], row['identifier'], row['best_value']) for row in sheet['candidates']]


def rna_structure_agreement_test_name(sheet, source):
    """The test of the RNA structure agreement graded in ``sheet`` made by the held source ``source``."""
    return 'rna_structure_agreement:rfam@' + source


def rna_structure_agreement_rows(sheet):
    """The ``(vocabulary, name, identifier, value)`` of the family candidates of an RNA structure agreement sheet that have a value
    (a consensus with at least one pair), in its order."""
    return [(row['kind'], row['name'], row['identifier'], row['value']) for row in sheet['candidates']]


def partner_contacts_rows(sheet):
    """The ``(product, E)`` of the matched proteins of a partner-contacts sheet that have a functional partner, in the sheet's
    order: one row per protein, so a candidate's value in the test is the mean over its proteins (the sheet's ``mean_E`` for
    it), and under a grouping the mean over the proteins of all the group's members."""
    return [(row['product'], row['E']) for row in sheet['hits'] if row['product'] is not None and row['E'] is not None]


def bound_partner_rows(sheet):
    """The ``(vocabulary, identifier, mean_E)`` of the partner candidates of a bound-partner sheet: ``ligand`` with the chemical
    component id, ``nucleic_acid`` with ``dna`` or ``rna``."""
    return [(row['kind'], row['identifier'], row['mean_E']) for row in sheet['candidates']]


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
            if sheet['schema'] not in (SEARCH_SHEET, SITE_SHEET, CONTACTS_SCHEMA, PARTNERS_SCHEMA, TRANSPLANT_SHEET, RNA_SCAN_SHEET,
                                    RNA_AGREEMENT_SHEET, COFOLDING_SHEET):
                continue
            target = source['operand_refs'][0]
            if target not in scope['subject_refs']:
                continue
            if sheet['schema'] == CONTACTS_SCHEMA:
                measurements.extend(_measurement(target, partner_contacts_test_name(sheet, reference), 'product', product, None,
                                                 value, reference) for product, value in partner_contacts_rows(sheet))
                continue
            if sheet['schema'] == PARTNERS_SCHEMA:
                measurements.extend(_measurement(target, bound_partner_test_name(sheet, reference), vocabulary, identifier, None,
                                                 value, reference) for vocabulary, identifier, value in bound_partner_rows(sheet))
                continue
            if sheet['schema'] == RNA_SCAN_SHEET:
                measurements.extend(_measurement(target, rna_family_scan_test_name(sheet, reference), vocabulary, name, identifier,
                                                 value, reference) for vocabulary, name, identifier, value in rna_family_scan_rows(sheet))
                continue
            if sheet['schema'] == RNA_AGREEMENT_SHEET:
                measurements.extend(_measurement(target, rna_structure_agreement_test_name(sheet, reference), vocabulary, name,
                                                 identifier, value, reference)
                                    for vocabulary, name, identifier, value in rna_structure_agreement_rows(sheet))
                continue
            if sheet['schema'] == TRANSPLANT_SHEET:
                measurements.extend(_measurement(target, ligand_transplant_test_name(sheet, reference), vocabulary, identifier, None,
                                                 value, reference) for vocabulary, identifier, value in ligand_transplant_rows(sheet))
                continue
            if sheet['schema'] == COFOLDING_SHEET:
                measurements.extend(_measurement(target, partner_cofolding_test_name(sheet, reference), vocabulary, identifier, None,
                                                 value, reference) for vocabulary, identifier, value in partner_cofolding_rows(sheet))
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


LEADING_PROTEINS = 5


def matched_proteins(reader, scope, sources):
    """The proteins behind each product candidate, per target of the scope: ``{target: {product name: {'hit_count',
    'function_identifiers', 'identifier_sources', 'hits_without_identifier', 'hits_not_looked_up', 'leading_proteins'}}}``, over
    the hits of the held
    graded structure searches that carry that name and have a value (a protein hit by several searches counts once and takes
    its highest value). ``hit_count``: those proteins. ``function_identifiers``: ``[{'source', 'identifier', 'hit_count'}]``,
    one entry per (source, identifier) with the number of the candidate's proteins that carry it, the one most carry first
    (ties in the order found). ``identifier_sources``: ``[{'source', 'protein_count'}]``, per source the number of the
    candidate's proteins that carry ANY identifier of it (one protein can carry two identifiers of one source: with this number
    a parent tells that from proteins that split over two identifiers). ``hits_without_identifier``: the proteins that carry no identifier of any source (and whose
    BV-BRC family lookup was made). ``hits_not_looked_up``: the proteins whose BV-BRC family lookup was not made or failed (no
    family is not known for them). ``leading_proteins``: ``[{'source': 'uniprot', 'accession', 'value'}]``, the highest value
    first, at most ``LEADING_PROTEINS``. A parent reads what a candidate is from these, never from the name; nothing here merges
    two candidates."""
    scope = reader.validate_scope(scope)
    found = {target: {} for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            target = source['operand_refs'][0]
            if sheet['schema'] != SEARCH_SHEET or target not in found:
                continue
            for row in sheet['hits']:
                if row['product'] is not None and row['B'] is not None:
                    protein = found[target].setdefault(row['product'], {}).setdefault(
                        row['accession'], {'value': row['B'], 'identifiers': row['function_identifiers'],
                                           'looked_up': row['family_looked_up']})
                    protein['value'] = max(protein['value'], row['B'])
    table = {}
    for target, products in found.items():
        table[target] = {}
        for product, proteins in products.items():
            counts, carrying = {}, {}
            for protein in proteins.values():
                for item in protein['identifiers']:
                    key = (item['source'], item['identifier'])
                    counts[key] = counts.get(key, 0) + 1
                for name in dict.fromkeys(item['source'] for item in protein['identifiers']):
                    carrying[name] = carrying.get(name, 0) + 1
            order = list(counts)
            leading = sorted(proteins, key=lambda accession: (-proteins[accession]['value'], accession))[:LEADING_PROTEINS]
            table[target][product] = {
                'hit_count': len(proteins),
                'function_identifiers': [{'source': key[0], 'identifier': key[1], 'hit_count': counts[key]}
                                         for key in sorted(counts, key=lambda key: (-counts[key], order.index(key)))],
                'identifier_sources': [{'source': name, 'protein_count': count} for name, count in carrying.items()],
                'hits_without_identifier': sum(1 for protein in proteins.values()
                                               if protein['looked_up'] and not protein['identifiers']),
                'hits_not_looked_up': sum(1 for protein in proteins.values() if not protein['looked_up']),
                'leading_proteins': [{'source': 'uniprot', 'accession': accession, 'value': proteins[accession]['value']}
                                     for accession in leading]}
    return table


def candidate_measurements(reader, scope, sources, grouping=None):
    """The measurements (``{'test', 'candidate', 'value'}`` and what the head shows: ``target``, ``vocabulary``, ``name``,
    ``identifier``, ``source``) of the graded ``sources`` over ``scope``, in the order of ``sources``, read under ``grouping``
    (``None``: as found)."""
    return apply_grouping(_read(reader, scope, sources)[0], grouping)


def candidate_standing(reader, scope, sources, grouping=None):
    """Where each candidate stands, per target of the scope (``{target: differential_credit.standing(its
    measurements)}``), after the graded ``sources`` and under ``grouping``: what a further test's ceiling is computed from."""
    return {target: standing(rows) for target, rows in _by(candidate_measurements(reader, scope, sources, grouping), 'target').items()}


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


def held_partner_analyses(reader, scope, sources):
    """Per target of the scope, the search source references whose ``partner_contacts`` the episode holds (graded), in arrival
    order: a further ``partner_contacts`` of the same search is a repeat (it adds nothing) and the request check refuses it."""
    scope = reader.validate_scope(scope)
    held = {target: [] for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        target = source['operand_refs'][0] if source.get('operand_refs') else None
        if target not in held:
            continue
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            if sheet['schema'] == CONTACTS_SCHEMA:
                held[target].append(sheet['search_source_ref'])
    return held


def held_transplant_models(reader, scope, sources):
    """Per target of the scope, the model references whose ``ligand_transplants`` the episode holds (graded), in arrival order: a
    further ``ligand_transplants`` of the same model is a repeat (it adds nothing) and the request check refuses it."""
    scope = reader.validate_scope(scope)
    held = {target: [] for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        target = source['operand_refs'][0] if source.get('operand_refs') else None
        if target not in held:
            continue
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            if sheet['schema'] == TRANSPLANT_SHEET:
                held[target].append(sheet['model_ref'])
    return held


def held_rna_scans(reader, scope, sources):
    """Per target of the scope, the source references of the RNA family scans the episode holds (graded), in arrival order: a
    further scan of the same target is a repeat (it adds nothing) and the request check refuses it."""
    scope = reader.validate_scope(scope)
    held = {target: [] for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        target = source['operand_refs'][0] if source.get('operand_refs') else None
        if target not in held:
            continue
        for entry in source_tool_grading_entries(reader, reference):
            if entry['grading']['sheet']['schema'] == RNA_SCAN_SHEET:
                held[target].append(reference)
    return held


def held_rna_agreements(reader, scope, sources):
    """Per target of the scope, the scan source references whose ``rna_structure_agreement`` the episode holds (graded), in arrival
    order: a further agreement test of the same scan is a repeat (it adds nothing) and the request check refuses it."""
    scope = reader.validate_scope(scope)
    held = {target: [] for target in scope['subject_refs']}
    for reference in sources:
        source = reader.get(reference)
        target = source['operand_refs'][0] if source.get('operand_refs') else None
        if target not in held:
            continue
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            if sheet['schema'] == RNA_AGREEMENT_SHEET:
                held[target].append(sheet['scan_source_ref'])
    return held


def _entry(measurements, candidate):
    first = next(row for row in measurements if row['candidate'] == candidate)
    return {'vocabulary': first['vocabulary'], 'name': first['name'],
            **({} if first['identifier'] is None else {'identifier': first['identifier']})}


def _parts(rows):
    """The admission (sum of the entry scores) and the discrimination (sum of the differentials' values) of the rows of one target."""
    result = differential_credit(rows)
    return {'admission': math.fsum(result['entries'].values()),
            'discrimination': math.fsum(row['value'] for row in result['differentials']), 'credit': result['credit']}


def _target_parts(rows, groupings):
    """The admission as found and the discrimination of the rows of one target under each of ``groupings`` (``None`` among them: as
    found), and the credit as found."""
    if not rows:
        return {'admission': 0.0, 'discrimination': [0.0 for _ in groupings], 'credit': 0.0, 'as_found': 0.0}
    plain = _parts(rows)
    return {'admission': plain['admission'], 'credit': plain['credit'], 'as_found': plain['discrimination'],
            'discrimination': [plain['discrimination'] if not grouping else _parts(apply_grouping(rows, grouping))['discrimination']
                               for grouping in groupings]}


def admission_and_discrimination(reader, scope, sources, grouping=None):
    """Per target of the scope: ``{'admission': the sum of the entry scores read as found (a grouping never changes it),
    'discrimination': the sum of the differentials' values read under grouping}`` (``None``: as found)."""
    found = _by(_read(reader, scope, sources)[0], 'target')
    parts = {target: _target_parts(found.get(target, []), [grouping]) for target in reader.validate_scope(scope)['subject_refs']}
    return {target: {'admission': row['admission'], 'discrimination': row['discrimination'][0]} for target, row in parts.items()}


def candidate_credit(reader, scope, sources, groupings=()):
    """The credit of the held graded ``sources`` over ``scope``, given the groupings the head holds: per target of the scope
    (``targets``: target reference -> ``admission`` (the sum of the entry scores as found), ``discrimination`` (the highest sum of the
    differentials' values over no grouping and every grouping of ``groupings``) and ``credit`` (admission plus that
    discrimination: it is written as ``differential_credit``'s credit of the rows as found plus the rise of the highest
    discrimination over the discrimination as found, which is the same sum, so that with no grouping held it is exactly that credit))
    and ``credit``, the sum over the targets. It rises when the admission or the highest discrimination rises and never falls: going
    back to a grouping already held, or applying one again, leaves it where it was."""
    found = _by(_read(reader, scope, sources)[0], 'target')
    targets = {}
    for target in reader.validate_scope(scope)['subject_refs']:
        row = _target_parts(found.get(target, []), list(groupings))
        highest = max([row['as_found'], *row['discrimination']])
        targets[target] = {'admission': row['admission'], 'discrimination': highest,
                           'credit': row['credit'] + (highest - row['as_found'])}
    return {'targets': targets, 'credit': math.fsum(row['credit'] for row in targets.values())}


def candidate_table(reader, scope, sources, grouping=None):
    """What the head shows and returns, per target of the scope, read under ``grouping`` (``None``: as found) (``targets``: target
    reference -> ``candidates`` (one row per admitted candidate, highest score first, ties in arrival order: its vocabulary, name and
    identifier, its ``score``, the ``sheets`` and ``tests`` it has undergone, its ``measurement_count`` and its ``best_value``; under a
    grouping a candidate that is a group also carries ``members``, the group's members the target holds, each ``{vocabulary, name,
    identifier?}``, and is named by the member that names the group), ``tests`` (each test applied to the target with
    ``candidate_count``, the admitted candidates it measured), ``differentials`` (each: the ``test``, the two candidates and the
    ``value``), ``not_asked_hit_count`` (the hits of searches whose name was never asked: the naming stopped once the candidates
    settled), ``no_product_hit_count`` (the hits asked that carry no name), ``no_value_hit_count`` (the hits with a name and no
    value) and the target's ``credit``: the credit of the rows as read under this grouping alone, not the head's credit
    (``candidate_credit``)), and the ``credit`` of the scope: the sum over its targets."""
    measurements, unnamed = _read(reader, scope, sources)
    lookup = group_lookup(grouping)
    targets = {}
    for target, held in _by(measurements, 'target').items():
        rows = apply_grouping(held, grouping)
        held_keys = {row['candidate'] for row in held}
        result = differential_credit(rows)
        candidates = [{**_entry(rows, candidate), 'score': score,
                       'sheets': [{'sheet': kind, 'value': value} for kind, value in result['sheets'][candidate].items()],
                       'tests': list(dict.fromkeys(row['test'] for row in rows if row['candidate'] == candidate)),
                       'measurement_count': sum(1 for row in rows if row['candidate'] == candidate),
                       'best_value': max(row['value'] for row in rows if row['candidate'] == candidate)}
                      for candidate, score in result['scores'].items()]
        for row in candidates:
            key = row['vocabulary'] + ':' + row.get('identifier', row['name'])
            if key in lookup and lookup[key]['key'] == key:
                row['members'] = [member for member in lookup[key]['members'] if member_key(member) in held_keys]
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
