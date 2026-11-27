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
  ``annotation`` field); its value is the subscore of that hit's alignments. A hit with no function names no candidate.
  It is counted as NOT ASKED when the naming of the search's hits stopped before it (``bvbrc_hit_metadata.name_hits``
  asks for the hits in the order of their value and stops once the candidates settle; its ``naming`` record, the
  ``search_hit_metadata`` product of the search, gives ``not_asked``): its function is unknown, not absent. Every other
  hit with no function was asked and carries no product (``no_product``). Hits with the same function are replicates of
  that candidate in the test. A function that is a label of ignorance ("hypothetical protein" and the other
  ``uncharacterized_labels.UNCHARACTERIZED_LABELS``; the owner, 2026-11-23: "a label of ignorance, not a label of
  positive knowledge") names no candidate either, in any test: a hit all of whose functions are such labels is counted
  as ``uncharacterized``.
  The function-level identity of a product candidate (the owner, 2026-11-23: an annotation is a function; two heads, and
  one head, name one function in several ways; among this head's own candidates the head joins the names itself
  (2026-11-26: "join this automatically and not use the root to decide"). A candidate keeps its name and its score exactly as above. It
  additionally carries ``function_identifiers``: the identifiers of the proteins behind it, read from its hits and
  never from a search by its name: for BV-BRC hits the global protein family of each hit's feature (``pgfam_id``,
  source ``bvbrc_global_family``), each with the number of its hits that carry it, ``identifier_sources`` (per source,
  the number of its hits that carry any identifier of that source: an identifier whose hit count equals it is carried
  by every hit that has the source; the same field the structural-homology head returns) and
  ``hits_without_identifier``.
  The uncharacterized hits are returned by family in the same way (``uncharacterized_families``: identifier, hit
  count and highest value), so that an unknown family is something a later investigation can start from.
  The organisms of the hits behind a product candidate (the owner, 2026-11-25: the head "should be capable of
  returning that organismal source info for sure"): the table gives, per target, ``hit_organisms``: for each candidate
  a database search named, the taxa its hits are from (``organisms``: the NCBI taxon id of each hit's feature, BV-BRC's
  ``taxon_id`` as the sheet's reference metadata keeps it, with the number of its hits of that taxon) and
  ``hits_without_taxon`` (its hits whose feature carries none). Ids and counts only; they enter no score and no
  credit.
  The feature type of the hits behind a product candidate (the owner, 2026-11-25: "just like with organismal taxa ...
  you also have to extract this? we can decide how to use it later"): the table gives, per target,
  ``hit_feature_kinds``: for each candidate a database search named, the types of the features its hits are
  (``feature_kinds``: one of ``feature_types.KINDS``, matched from BV-BRC's ``feature_type`` of each hit's feature by
  ``database_feature_types.bvbrc_feature_kind``, with the number of its hits of that type),
  ``hits_with_unmapped_feature_type`` (its hits whose database value has no type of ours yet: the table of the matching
  is to be extended; the value itself stays in the sheet) and ``hits_without_feature_type`` (its hits whose feature
  carries none). Types of the fixed list and counts only; they enter no score and no credit.
* a profile scan (``hmmer_search_sheet`` of ``hmmscan``): test ``profile_scan:<database name>``; each matched family
  is a candidate of vocabulary ``profile_family`` (identifier: its accession, name: its name, as the profile database
  gives them); its value is the subscore of its domains.
* a pairwise comparison (``blast_pairwise_sheet``): test ``pairwise:<program>``; the reference sequence record
  it was compared with is a candidate of vocabulary ``reference_sequence`` (identifier: its record reference, name: the
  record's name); its value is the subscore of its alignments.

* a multiple sequence alignment (``msa_alignment_sheet``): test ``msa:<provider>:<aligner>:<alphabet>``; the owner's
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
  ``matched_positions_taken`` gives, per candidate, the target positions whose matched site of it a held alignment has
  identified, and ``alignment_contexts`` the held alignments' inputs (what the ceiling reads).
* a graded clustering (``cluster_sheet``, the all-vs-all child): test ``cluster:<method>`` (``cluster:mcl``; one test per
  graded clustering, as every test is named, so ``@<source>`` follows); the sheet's groups are the candidate groups (the
  sequences of one ``product`` candidate in the set; the target is in no group), and for each candidate group with a sequence
  in the set one measurement: its value is the SHARE of the group's sequences that fall in the target's cluster (0 to 1), the
  same scale as the other tests (about 1 for a strong typical result, as the other tests' values; the MSA's count is weighted
  by W = 1 / E to land there). A candidate with no sequence in the set gives no measurement. The measurement also records
  ``size`` and ``in_target_cluster``, and its ``dataset``: the graded search the set is drawn from. The ``size`` is the
  candidate's evidence: the credit of a cluster test weighs each differential by the weaker side's ``size / (size + 4)`` and each
  entry by its own (``differential_credit.cluster_evidence``; the owner: "clusters with little data earn less"). The owner: "You only can
  earn one credit for one dataset - you can improve a clustering to earn more, but you cannot replicate". So all the
  clusterings of one dataset together earn the largest test credit among them (a later one earns only its improvement over the
  best so far; a replicate earns 0), and a candidate's value on the cluster sheet from one dataset is its largest value over
  that dataset's clusterings (``differential_credit``). ``dataset_bests`` gives each dataset's best so far (what the
  ceiling reads).
* a MetaCATS report (``metacats_sheet``): the owner (2026-11-21): "It's wrong that it has no credit. i told you it gains
  credit by confirming conserved sites in comparison to a gene family." MetaCATS ran on a held alignment with the alignment's
  candidate groups (each group one product candidate's reference sequences, a gene family) and reports the alignment positions
  where the groups' residue frequencies differ significantly (p fixed at ``bvbrc_metacats_analysis.P_VALUE``). The job took a
  DERIVED alignment (the held one without the target's row) with every column kept, so a reported ``Position`` is the 1-based
  column of the held alignment (verified on the stored real reports: the per-group residue counts of every significant row equal
  the held alignment's column of that number). A matched conserved site of a candidate (``msa_alignment_sheet.conserved_sites``
  of that alignment: identity (target position, residue, candidate), the group conserving the target's own residue there; the
  column is mapped to the target's residue position through the target's row, and a column where the target has a gap is
  identified by nothing) is CONFIRMED when its column is significant. The owner (2026-11-27): "metacats should perhaps only
  earn if it identifies new regions, not just runs on new MSAs"; "you must put regions in the grading report (and compare
  past grading sheets to see if regions are new or not)". A REGION is a window of ``REGION_RESIDUES`` consecutive target
  positions; the report's sheet lists, per candidate, the regions that hold a confirmed site (``confirmed_regions``). Test
  ``msa:bvbrc_metacats:confirmed_regions`` (family ``msa``, so the msa sheet weight applies), one test per report; for each
  candidate with a region in the sheet that no earlier held report's sheet has for it, one measurement: value = (those
  regions) x ``EXPECTED_DISTINGUISHING_SITES`` x ``SITE_WEIGHT`` (a region is worth its expected sites); it also records
  ``new_regions`` and ``regions``. A report on another alignment that confirms sites in regions already confirmed earns
  nothing. ``unconfirmed_regions`` gives, for an alignment, each candidate's regions with a matched site that no held
  report confirmed (what the ceiling reads).

A candidate is identified by its vocabulary and its identifier (its name when it has none). Candidates of different
vocabularies are different candidates: nothing merges a family with a product or a sequence.

Arrival order: ``held_sources`` is the order of the reader's ``refs()``, the receipt order of custody: the records
the parent passed in, in the order given, then those its own units produced or its children returned, in the order of
the units. The summary's ``held_record_refs`` is the same order. It is the same on every recomputation and on resume,
because the receipts are recorded once, in the journal's row order.

The measurements of different targets are never compared: ``candidate_table`` runs ``differential_credit`` on each
target of the scope and the credit is the sum over the targets."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    _regions)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.cluster_sheet import (
    SCHEMA as CLUSTER_SHEET, group_values)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.differential_credit import (
    GROUP_PREFIX, differential_credit, group_key, grouped_credit, regrouped, standing)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.database_feature_types import (
    bvbrc_feature_kind)
from gene_annotation_episode.episodic_workflow.episode_support.grading.uncharacterized_labels import is_uncharacterized_label
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.msa_alignment_sheet import (
    matched_regions)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    compile_native_sheet, hmmer_comparisons, route_native_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products

VOCABULARIES = ('product', 'profile_family', 'reference_sequence')
METACATS_SHEET = 'metacats_sheet'
METACATS_TEST = 'msa:bvbrc_metacats:confirmed_regions'
ALIGNMENT_KIND = 'multiple_sequence_alignment'
REPORT_KIND = 'alignment_position_report'
ALIGNMENT_PROVIDER = 'bvbrc_msa'
DATABASE_SHEETS = ('blast_database_sheet', 'blast_database_sheet_record_locator', 'blast_database_sheet_population')
PAIRWISE_SHEET = 'blast_pairwise_sheet'
PROFILE_SHEET = 'hmmer_search_sheet'
MSA_SHEET = 'msa_alignment_sheet'
# The data product of a search's hit metadata (``bvbrc_blast_search.METADATA_KIND``; that module imports this one).
HIT_METADATA_KIND = 'search_hit_metadata'
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
# The length of a region of the target: the 70 residues of the proteins E was derived on.
REGION_RESIDUES = 70


# The provider of the records in which an episode keeps its joinings of its candidates (one ``source``
# record per grouping, its artifact the grouping itself).
GROUPING_PROVIDER = 'candidate_grouping'


def member_key(member):
    """The candidate key of a member of a group, named as the head returned it: its vocabulary and its own identifier,
    or its name when it has none (the key ``_measurement`` gives a measurement)."""
    return member['vocabulary'] + ':' + (member.get('identifier') or member['name'])


def grouping_keys(grouping):
    """A grouping (``[{'members': [{'vocabulary', 'name', 'identifier'?}]}]``) as lists of candidate keys."""
    return [[member_key(member) for member in group['members']] for group in grouping]


def held_groupings(reader):
    """The groupings of its candidates the episode holds, in the order it obtained them (the owner, 2026-11-26: the
    head joins the names that are one function itself, by one automatic model call; it keeps
    each joining as a record, and its credit reads them)."""
    return [json.loads(reader.get_artifact(reader.get(ref)['artifact_ref'])) for ref in held_sources(reader)
            if reader.get(ref)['provider'] == GROUPING_PROVIDER]


def held_sources(reader):
    """The sources the episode holds, in the order it obtained them (receipt order)."""
    return [ref for ref in reader.refs() if ref.startswith('source_')]


def targets(reader, scope):
    """The sequences the head finds annotations for, in the order of the scope's subjects: each subject itself, or, when
    the episode holds feature records of it that name their protein (the candidate feature calls of feature calling),
    those proteins in the order the records were received."""
    features = [reader.get(ref) for ref in reader.refs() if ref.startswith('feature_')]
    found = []
    for subject in reader.validate_scope(scope)['subject_refs']:
        proteins = [record['protein_ref'] for record in features
                    if record['subject_ref'] == subject and 'protein_ref' in record and 'joined_ref' not in record]
        found.extend(proteins or [subject])
    return found


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
    (the function the sheet's reference metadata gives it), ``value`` (the subscore of that hit's alignments),
    ``aa_length`` (the hit's length as the search recorded it), and the
    hit's ``accession``, ``aa_sequence_md5``, ``feature_id``, ``pgfam_id``, ``taxon_id`` and ``feature_type`` (BV-BRC's feature fields,
    each exactly as the database gives it; ``None`` where the
    metadata has none); a hit that names no product (not asked, or asked and carrying none) gives one row with ``product`` ``None``."""
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
                          'aa_sequence_md5': None, 'aa_length': hit['length'], 'feature_id': None, 'pgfam_id': None,
                          'taxon_id': None, 'feature_type': None})
        found.extend({'hit_index': hit['hit_index'], 'product': name, 'value': value, 'accession': accession,
                      'aa_sequence_md5': feature.get('aa_sequence_md5'), 'aa_length': hit['length'],
                      'feature_id': feature.get('feature_id'), 'pgfam_id': feature.get('pgfam_id') or None,
                      'taxon_id': feature.get('taxon_id'), 'feature_type': feature.get('feature_type')}
                     for name, (accession, feature) in names.items())
    return found


def uncharacterized_hits(grading, value_of):
    """The values of the hits of a database search with names all of whose functions are labels of ignorance: one row
    per such hit: its ``value`` (the subscore of its alignments, on the scale of a candidate's value in that test) and
    the global protein family of its feature (``pgfam_id``, ``None`` where it carries none). The owner,
    2026-11-23: listing this evidence tells "if it's closer to something else unknown or closer to an actually named
    function and by how much"."""
    rows = [row for row in search_hits(grading, value_of) if row['product'] is not None]
    stated = {row['hit_index'] for row in rows if not is_uncharacterized_label(row['product'])}
    return list({row['hit_index']: {'value': row['value'], 'pgfam_id': row['pgfam_id']}
                 for row in rows if row['hit_index'] not in stated}.values())


def product_families(grading):
    """The global protein family of each hit of a database search with names, by the product the hit names: product ->
    one family identifier per hit (``None`` for a hit whose feature carries none)."""
    families = {}
    for row in search_hits(grading, lambda alignments: None):
        if row['product'] is not None and not is_uncharacterized_label(row['product']):
            families.setdefault(row['product'], []).append(row['pgfam_id'])
    return families


def product_taxa(grading):
    """The taxon of each hit of a database search with names, by the product the hit names: product -> one NCBI taxon
    id per hit (the ``taxon_id`` of the hit's feature; ``None`` for a hit whose feature carries none)."""
    taxa = {}
    for row in search_hits(grading, lambda alignments: None):
        if row['product'] is not None and not is_uncharacterized_label(row['product']):
            taxa.setdefault(row['product'], []).append(row['taxon_id'])
    return taxa


def product_feature_types(grading):
    """The feature type of each hit of a database search with names, by the product the hit names: product -> one
    value per hit (BV-BRC's ``feature_type`` of the hit's feature, exactly as the database gives it; ``None`` for a hit
    whose feature carries none)."""
    feature_types = {}
    for row in search_hits(grading, lambda alignments: None):
        if row['product'] is not None and not is_uncharacterized_label(row['product']):
            feature_types.setdefault(row['product'], []).append(row['feature_type'])
    return feature_types


def _database_search(source, grading, value_of):
    search = grading['sheet']['normalized_result']['search']
    test = 'database_search:' + source['provider'] + ':' + search['program'] + ':' + search['request']['database']
    rows = search_hits(grading, value_of)
    found = [(test, 'product', row['product'], None, row['value'], {'rank': row['hit_index'], 'taxon_id': row['taxon_id']})
             for row in rows if row['product'] is not None]
    return found, sum(1 for row in rows if row['product'] is None)


def hit_naming(reader, source):
    """The ``naming`` record (``{'named', 'not_asked', 'batches', 'stopped'}``, ``bvbrc_hit_metadata.name_hits``) of the hit metadata
    of the held search ``source``: the held ``search_hit_metadata`` product made from the search's report. ``None`` when none is
    held or it has no naming record (a search whose every hit was asked)."""
    rows = [row for row in products(reader, HIT_METADATA_KIND) if source['artifact_ref'] in row['used']]
    if not rows:
        return None
    (row,) = rows
    return json.loads(reader.get_artifact(row['artifact_ref'])).get('naming')


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
    """A graded multiple sequence alignment (``msa_alignment_sheet``): test ``msa:<provider>:<aligner>:<alphabet>``;
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
    """A graded clustering (``cluster_sheet``): test ``cluster:<method>``; one measurement per candidate group with a
    sequence in the set (``cluster_sheet.group_values``), value = the share of its sequences in the target's cluster. Its
    ``dataset`` is the graded search the set's sequences are drawn from (the commission's ``search_ref``): all the clusterings
    of one dataset earn one test's credit together (``differential_credit``, the owner's "You only can earn one credit for one
    dataset")."""
    sheet = grading['sheet']
    test = 'cluster:' + sheet['method']
    dataset = sheet['commission']['search_ref']
    return [(test, 'product', candidate, None, share, {'size': size, 'in_target_cluster': inside, 'dataset': dataset})
            for candidate, share, size, inside in group_values(sheet)], 0


def alignment_sheet(reader, alignment_ref):
    """The graded sheet (``msa_alignment_sheet``) of the held alignment data product ``alignment_ref``: the sheet of the held
    source of provider ``bvbrc_msa`` whose artifact the product row labels."""
    (row,) = [item for item in products(reader, ALIGNMENT_KIND) if item['id'] == alignment_ref]
    (source,) = [item for item in reader.list('source')
                 if item['provider'] == ALIGNMENT_PROVIDER and item['artifact_ref'] == row['artifact_ref']]
    (entry,) = source_tool_grading_entries(reader, source['id'])
    return entry['grading']['sheet']


def _held_metacats(source, grading, confirmed):
    """A graded MetaCATS report (``metacats_sheet``): test ``METACATS_TEST``; one measurement per candidate with a region in
    the sheet's ``confirmed_regions`` that no earlier report's sheet has for it. ``confirmed`` is the set of the regions the
    earlier reports confirmed (target, candidate, region number), which this call extends. The value is the new regions x
    ``EXPECTED_DISTINGUISHING_SITES`` x ``SITE_WEIGHT``."""
    target, found = source['operand_refs'][0], []
    for row in grading['sheet']['confirmed_regions']:
        regions = [(target, row['candidate'], region['region']) for region in row['regions']]
        new = [key for key in regions if key not in confirmed]
        confirmed.update(new)
        if new:
            found.append((METACATS_TEST, 'product', row['candidate'], None,
                          len(new) * EXPECTED_DISTINGUISHING_SITES * SITE_WEIGHT,
                          {'weight': EXPECTED_DISTINGUISHING_SITES * SITE_WEIGHT, 'new_regions': len(new),
                           'regions': len(regions)}))
    return found, 0


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
    """The measurements in arrival order, per target the hits of database searches that name no candidate
    (``{'not_asked', 'no_product', 'uncharacterized'}``: the hits whose function was never asked, those asked that carry
    no product, the values and families of those whose every function is a label of ignorance, under ``families``
    the family identifier of every hit of each product, under ``taxa`` the taxon id of every hit of each product and
    under ``feature_types`` the database's feature type of every hit of each product), the
    identified conserved sites (target, target position, residue, candidate name) of the held alignments and the regions
    the held MetaCATS reports confirmed (target, candidate name, region number)."""
    scope, wanted = reader.validate_scope(scope), targets(reader, scope)
    measurements, unnamed = [], {target: {'not_asked': 0, 'no_product': 0, 'uncharacterized': [], 'families': {},
                                          'taxa': {}, 'feature_types': {}}
                                 for target in wanted}
    identified, confirmed = set(), set()
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
            elif sheet['schema'] == METACATS_SHEET:
                read = lambda s, g, v: _held_metacats(s, g, confirmed)
            elif sheet['schema'] == PAIRWISE_SHEET:
                read = lambda s, g, v: _pairwise(reader, s, g, v)
            else:
                continue
            target = source['operand_refs'][0]
            if target not in wanted:
                continue
            length, regions = reader.subject_length(target), _regions(reader, scope, target)
            value_of = lambda rows: compile_native_sheet(rows, supplied_length=length, regions=regions)['value']
            found, missing = read(source, grading, value_of)
            if missing:
                naming = hit_naming(reader, source)
                not_asked = 0 if naming is None else naming['not_asked']
                if not_asked > missing:
                    raise ValueError('hits_not_asked_exceed_the_hits_without_a_function:' + reference)
                unnamed[target]['not_asked'] += not_asked
                unnamed[target]['no_product'] += missing - not_asked
            if read is _database_search:
                unnamed[target]['uncharacterized'].extend(uncharacterized_hits(grading, value_of))
                for product, families in product_families(grading).items():
                    unnamed[target]['families'].setdefault(product, []).extend(families)
                for product, taxa in product_taxa(grading).items():
                    unnamed[target]['taxa'].setdefault(product, []).extend(taxa)
                for product, feature_types in product_feature_types(grading).items():
                    unnamed[target]['feature_types'].setdefault(product, []).extend(feature_types)
            measurements.extend(_measurement(target, row[0] + '@' + reference, *row[1:5], reference, *row[5:]) for row in found
                                if not (row[1] == 'product' and is_uncharacterized_label(row[2])))
    return measurements, unnamed, identified, confirmed


def candidate_measurements(reader, scope, sources):
    """The measurements (``{'test', 'candidate', 'value'}`` and what the head shows: ``target``, ``vocabulary``,
    ``name``, ``identifier``, ``source``) of the graded ``sources`` over ``scope``, in the order of ``sources``."""
    return _read(reader, scope, sources)[0]


def candidate_standing(reader, scope, sources):
    """Where each candidate stands, per target of the scope (``{target: differential_credit.standing(its
    measurements)}``), after the graded ``sources``: what a further test's ceiling is computed from."""
    measurements = _read(reader, scope, sources)[0]
    return {target: standing(rows) for target, rows in _by(measurements, 'target').items()}


def dataset_bests(reader, scope, sources):
    """Per target of the scope, ``{dataset: best}``: for each dataset (the graded search a held clustering's set is drawn from)
    the largest test credit of its held clusterings (``differential_credit(...)['datasets']``), what the dataset already earned."""
    measurements = _read(reader, scope, sources)[0]
    return {target: {dataset: held['best'] for dataset, held in differential_credit(rows)['datasets'].items()}
            for target, rows in _by(measurements, 'target').items()}


def unconfirmed_regions(reader, scope, sources, alignment_ref):
    """``(target, {candidate name: count})`` for the held alignment data product ``alignment_ref``: per candidate, the
    regions in which that alignment has a matched site of it (``msa_alignment_sheet.matched_regions``) and that no held
    MetaCATS report's sheet has for it: the most a MetaCATS report of that alignment can confirm for it."""
    confirmed = _read(reader, scope, sources)[3]
    (source,) = [item for item in reader.list('source') if item['provider'] == ALIGNMENT_PROVIDER and item['artifact_ref']
                 == next(row['artifact_ref'] for row in products(reader, ALIGNMENT_KIND) if row['id'] == alignment_ref)]
    target = source['operand_refs'][0]
    held = matched_regions(alignment_sheet(reader, alignment_ref)['conserved_sites']['sites'], REGION_RESIDUES)
    return target, {candidate: sum(1 for region in regions if (target, candidate, region) not in confirmed)
                    for candidate, regions in held.items()}


def matched_positions_taken(reader, scope, sources):
    """Per target of the scope, ``{candidate: count}`` (candidate as ``product:<name>``) of the target positions ``p`` whose
    matched site of the candidate a held alignment has identified: the identity (target, ``p``, the target's own residue at
    ``p``, candidate) is in the identified set, so a later alignment can never count a matched site there again
    (``new_site_values``). A position identified only with another conserved residue (a mismatched site) is NOT counted: a
    different alignment can still find the target's own residue conserved there. A candidate absent has none taken."""
    scope = reader.validate_scope(scope)
    identified = _read(reader, scope, sources)[2]
    taken = {}
    for target in targets(reader, scope):
        sequence_ref = reader.get(target).get('sequence_ref')
        residues = None if sequence_ref is None else reader.get_artifact(sequence_ref).decode('ascii').strip().upper()
        found = {}
        for site_target, position, residue, candidate in identified:
            if site_target == target and residues is not None and residues[position - 1] == residue.upper():
                found.setdefault('product:' + candidate, set()).add(position)
        taken[target] = {name: len(positions) for name, positions in found.items()}
    return taken


def alignment_contexts(reader, scope, sources):
    """Per target of the scope, the held alignments' inputs: one tuple per held alignment of ``((candidate name, aa_sequence_md5),
    ...)`` for its reference sequences in the order they were given to the aligner (the sheet's order). Two alignments with
    the same tuple (the same candidates, sequences and order) are the same input."""
    scope = reader.validate_scope(scope)
    contexts = {target: [] for target in targets(reader, scope)}
    for reference in sources:
        source = reader.get(reference)
        target = source['operand_refs'][0] if source.get('operand_refs') else None
        if target not in contexts:
            continue
        for entry in source_tool_grading_entries(reader, reference):
            sheet = entry['grading']['sheet']
            if sheet['schema'] == MSA_SHEET:
                contexts[target].append(tuple((row['candidate'], row['aa_sequence_md5']) for row in sheet['references']))
    return contexts


def _entry(measurements, candidate):
    first = next(row for row in measurements if row['candidate'] == candidate)
    return {'vocabulary': first['vocabulary'], 'name': first['name'],
            **({} if first['identifier'] is None else {'identifier': first['identifier']})}


FAMILY_SOURCE = 'bvbrc_global_family'


def _uncharacterized(hits):
    """The count of the uncharacterized hits, the highest value among them when there is one, and the hits by family
    (``uncharacterized_families``: the family identifier, absent for hits whose feature carries none, the number of
    hits and their highest value; the family with the highest value first)."""
    families = {}
    for hit in hits:
        families.setdefault(hit['pgfam_id'], []).append(hit['value'])
    rows = [{**({} if family is None else {'source': FAMILY_SOURCE, 'identifier': family}),
             'hit_count': len(values), 'best_value': max(values)} for family, values in families.items()]
    return {'uncharacterized_hit_count': len(hits),
            **({'uncharacterized_best_value': max(hit['value'] for hit in hits)} if hits else {}),
            'uncharacterized_families': sorted(rows, key=lambda row: -row['best_value'])}


def _identity(candidate, families):
    """The function-level identity of a product candidate, from the families of its hits (the module text): nothing for
    a candidate no database search named."""
    if candidate['vocabulary'] != 'product' or candidate['name'] not in families:
        return {}
    carried = [family for family in families[candidate['name']] if family is not None]
    counts = {family: carried.count(family) for family in dict.fromkeys(carried)}
    return {'function_identifiers': [{'source': FAMILY_SOURCE, 'identifier': family, 'hit_count': count}
                                     for family, count in sorted(counts.items(), key=lambda item: -item[1])],
            'identifier_sources': [{'source': FAMILY_SOURCE, 'protein_count': len(carried)}] if carried else [],
            'hits_without_identifier': len(families[candidate['name']]) - len(carried)}


def _hit_organisms(candidates, taxa):
    """The organisms of the hits behind the candidates a database search named (the module text), in the order of
    ``candidates``: for each its vocabulary and name, ``organisms`` (one entry per NCBI taxon id with the number of its
    hits of that taxon, most hits first, ties by taxon id) and ``hits_without_taxon``. A candidate no database search
    named has no hits and no entry."""
    rows = []
    for candidate in candidates:
        if candidate['vocabulary'] != 'product' or candidate['name'] not in taxa:
            continue
        carried = [taxon for taxon in taxa[candidate['name']] if taxon is not None]
        counts = {taxon: carried.count(taxon) for taxon in dict.fromkeys(carried)}
        rows.append({'vocabulary': candidate['vocabulary'], 'name': candidate['name'],
                     'organisms': [{'taxon_id': taxon, 'hit_count': count}
                                   for taxon, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))],
                     'hits_without_taxon': len(taxa[candidate['name']]) - len(carried)})
    return rows


def _hit_feature_kinds(candidates, feature_types):
    """The feature types of the hits behind the candidates a database search named (the module text), in the order of
    ``candidates``: for each its vocabulary and name, ``feature_kinds`` (one entry per type of ``feature_types.KINDS``
    with the number of its hits whose database value matches that type, most hits first, ties by the type's name),
    ``hits_with_unmapped_feature_type`` (its hits whose database value is not in the table of the matching yet) and
    ``hits_without_feature_type`` (its hits whose feature carries no feature type). The three counts add up to the
    candidate's hits. A candidate no database search named has no hits and no entry."""
    rows = []
    for candidate in candidates:
        if candidate['vocabulary'] != 'product' or candidate['name'] not in feature_types:
            continue
        stated = [value for value in feature_types[candidate['name']] if value is not None]
        matched = [kind for kind in map(bvbrc_feature_kind, stated) if kind is not None]
        counts = {kind: matched.count(kind) for kind in dict.fromkeys(matched)}
        rows.append({'vocabulary': candidate['vocabulary'], 'name': candidate['name'],
                     'feature_kinds': [{'kind': kind, 'hit_count': count}
                                       for kind, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))],
                     'hits_with_unmapped_feature_type': len(stated) - len(matched),
                     'hits_without_feature_type': len(feature_types[candidate['name']]) - len(stated)})
    return rows


def _grouped(rows, in_force):
    """The candidates of one target rescored under the grouping in force: one entry per candidate of the table read
    under it (a candidate in no group is a group of one), its ``members`` named as the head returned them, its ``score``
    and its ``sheets``, the highest score first."""
    result = differential_credit(regrouped(rows, grouping_keys(in_force)))
    members = {group_key(keys): group['members'] for group, keys in zip(in_force, grouping_keys(in_force))}
    return sorted(({'members': members[candidate] if candidate.startswith(GROUP_PREFIX) else [_entry(rows, candidate)],
                    'score': score,
                    'sheets': [{'sheet': kind, 'value': value} for kind, value in result['sheets'][candidate].items()]}
                   for candidate, score in result['scores'].items()), key=lambda entry: -entry['score'])


def candidate_table(reader, scope, sources, in_force=None):
    """What the head shows and returns, per target of the scope (``targets``: target reference -> ``candidates``
    (one row per admitted candidate, highest score first, ties in arrival order: its vocabulary, name and
    identifier, its ``score``, the ``tests`` it has undergone, its ``measurement_count`` and its ``best_value``),
    ``tests`` (each test applied to the target with ``candidate_count``, the admitted candidates it measured),
    ``differentials`` (each: the ``test``, the two candidates and the ``value``), ``not_asked_hit_count`` (the hits of
    database searches whose function was never asked: the naming stopped once the candidates settled), ``no_product_hit_count``
    (the hits asked that carry no product), ``uncharacterized_hit_count`` (the hits whose every function is a label of
    ignorance) with ``uncharacterized_best_value`` (the highest value among them, on the scale of a candidate's
    ``best_value``; absent when there is none) and ``uncharacterized_families`` (those hits by family) and the target's
    ``credit``), and the ``credit`` of the scope: the sum over its targets. A product candidate also carries its
    ``function_identifiers`` and ``hits_without_identifier`` (the module text). Beside the candidates the target has
    ``hit_organisms``: the organisms of the hits behind each candidate a database search named (``_hit_organisms``),
    in the order of the candidates, and ``hit_feature_kinds``: the feature types of those hits
    (``_hit_feature_kinds``), in the same order.

    Groupings (the owner, 2026-11-26: the head joins the names that are one function itself, "automatically and not
    use the root to decide"; 2026-11-23: a grouping is there
    "to make the arms annotation scores honest"). The
    ``candidates`` stay as found, by name. The target's ``credit`` is ``differential_credit.grouped_credit`` over the
    groupings the episode holds (``held_groupings``): with none held, the credit as before. With ``in_force`` (the
    latest joining the episode made, when it joins any) the target also carries ``grouped_candidates`` (its
    candidates rescored under that grouping, ``_grouped``) and ``grouping_in_force``."""
    measurements, unnamed = _read(reader, scope, sources)[:2]
    groupings = [grouping_keys(grouping) for grouping in held_groupings(reader)]
    targets = {}
    for target, rows in _by(measurements, 'target').items():
        result = differential_credit(rows)
        candidates = [{**_entry(rows, candidate), **_identity(_entry(rows, candidate), unnamed[target]['families']),
                       'score': score, 'sheets': [{'sheet': kind, 'value': value} for kind, value in result['sheets'][candidate].items()],
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
                           'hit_organisms': _hit_organisms(candidates, unnamed[target]['taxa']),
                           'hit_feature_kinds': _hit_feature_kinds(candidates, unnamed[target]['feature_types']),
                           'not_asked_hit_count': unnamed[target]['not_asked'],
                           'no_product_hit_count': unnamed[target]['no_product'],
                           **_uncharacterized(unnamed[target]['uncharacterized']),
                           **({} if in_force is None else {'grouped_candidates': _grouped(rows, in_force),
                                                           'grouping_in_force': in_force}),
                           'credit': grouped_credit(rows, groupings)}
    for target, counts in unnamed.items():
        targets.setdefault(target, {'candidates': [], 'tests': [], 'differentials': [], 'hit_organisms': [],
                                    'hit_feature_kinds': [],
                                    'not_asked_hit_count': counts['not_asked'], 'no_product_hit_count': counts['no_product'],
                                    **_uncharacterized(counts['uncharacterized']),
                                    'credit': 0.0})
    return {'targets': targets, 'credit': math.fsum(row['credit'] for row in targets.values())}
