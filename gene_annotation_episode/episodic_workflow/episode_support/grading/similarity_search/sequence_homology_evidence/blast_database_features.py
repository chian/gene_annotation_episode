"""The investigation finding of a retained A101 BLAST database grading (``blast_database_sheet`` with its
``blast_database_probabilities``): controlled features that code reads from the saved grading artifact, each with
its validator (``INVESTIGATION_FINDING_FEATURES_a101.md`` sections 1 and 5.3).

One entry per saved grading: the evidence type (fixed by the sheet schema; the model never picks it), the grading
artifact's reference, whether the sheet is routed into the A101 axis sheet (``route_native_grading`` routes BLAST
only for ``blastp``), the population counts of the sheet and one row per explicit function of the sheet. A feature
that the sheet leaves null (no metadata, no adjustment, no target taxonomy) is absent from the entry: nothing is
defaulted. No source titles, descriptions, assumptions or meanings travel: they stay in the sheet. The module also holds
the identification context of the same grading (``context_features``, below)."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.feature_rules import (
    valid, validated)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_source_class import (
    DEFAULT_TABLES, SOURCE_CLASSES, source_class_counts)

EVIDENCE_TYPE = 'protein_database_homologs'
SHEET_SCHEMAS = ('blast_database_sheet', 'blast_database_sheet_record_locator', 'blast_database_sheet_population')
UNCERTAINTY_KIND = 'native_evalue'
SAMPLING_BASIS = 'native_search_space'
# The rank that fixes ``target_taxon_matching_fraction`` (owner point 3 of the feature table is open; genus is the
# table's example).
TAXON_RANK = 'genus'

# name -> validator: ('number', low, high), ('count',), ('choice', options), ('boolean',), ('refs',), ('text',);
# ``optional`` marks a feature absent when the sheet's value is null.
SHEET_FEATURES = {
    'evidence_type': ('choice', (EVIDENCE_TYPE,)),
    'sheet_refs': ('ref',),
    'routed_to_axis_credit': ('boolean',),
    'total_group_count': ('count',),
    'groups_without_function': ('count',),
    'duplicate_hit_count': ('count',),
    'sequence_identity_unresolved': ('boolean',),
    'search_limit_reached': ('boolean', 'optional'),
    'unannotated_fraction': ('number', 0, 1, 'optional'),
    'uncertainty_kind': ('choice', (UNCERTAINTY_KIND,)),
    'uncertainty_magnitude': ('number', 0, math.inf, 'optional'),
    'uncertainty_sampling_basis': ('choice', (SAMPLING_BASIS,)),
}
FUNCTION_FEATURES = {
    'function': ('text',),
    'supporting_group_count': ('count',),
    'max_bit_score': ('number', -math.inf, math.inf, 'optional'),
    'max_query_paired_coverage': ('number', 0, 1, 'optional'),
    'conditional_weight': ('number', 0, 1, 'optional'),
    'representation_adjusted_weight': ('number', 0, 1, 'optional'),
    'competing_function_count': ('count',),
    'target_taxon_matching_fraction': ('number', 0, 1, 'optional'),
    'uncertainty_magnitude': ('number', 0, math.inf, 'optional'),
}
MEANINGS = {
    'evidence_type': 'The A101 evidence type: protein_database_homologs (a protein query against a sequence database)',
    'sheet_refs': 'The saved grading artifact (one reference)',
    'routed_to_axis_credit': 'Whether this sheet enters the A101 axis sheet (blastp only)',
    'total_group_count': 'Reference sequence groups (hits collapsed by demonstrated identity)',
    'groups_without_function': 'Sequence groups without an explicit function',
    'duplicate_hit_count': 'Native hits collapsed into an existing sequence group',
    'sequence_identity_unresolved': 'Whether sequence identity across hits stays unresolved',
    'search_limit_reached': 'Whether the reported hits reached the requested hit limit (absent when unknown)',
    'unannotated_fraction': 'Fraction of the reference kernel mass on unannotated groups, 0 to 1',
    'uncertainty_kind': 'The kind of uncertainty: native_evalue',
    'uncertainty_magnitude': 'The smallest native E-value (expected chance hits)',
    'uncertainty_sampling_basis': 'The sampling basis of the uncertainty: native_search_space',
    'functions': 'One row per explicit function of the sheet',
    'function': 'The function annotation as the source reader gave it (a name or ID, taken as given)',
    'supporting_group_count': 'Sequence groups that carry the function',
    'max_bit_score': 'Largest bit score among the groups of the function (bits)',
    'max_query_paired_coverage': 'Largest query paired coverage among the hits of the function, 0 to 1',
    'conditional_weight': 'Conditional reference-kernel weight of the function, 0 to 1 (not a probability)',
    'representation_adjusted_weight': 'The weight adjusted by database representation, 0 to 1',
    'competing_function_count': 'Other functions with a conditional weight',
    'target_taxon_matching_fraction': 'Fraction of the function groups matching the target taxon at genus',
}
FUNCTION_MEANINGS = {**MEANINGS, 'uncertainty_magnitude': 'The smallest native E-value among the hits of the '
                                                          'function (expected chance hits)'}


def validate_features(features):
    """Each feature against its validator; a violation raises ``ValueError``."""
    sheet = {name: value for name, value in features.items() if name != 'functions'}
    validated(sheet, SHEET_FEATURES, 'blast_database_finding')
    for row in features['functions']:
        validated(row, FUNCTION_FEATURES, 'blast_database_function')
    return features


def _present(**values):
    return {name: value for name, value in values.items() if value is not None}


def grading_features(grading, sheet_ref):
    """The features of one retained database grading (``{'sheet', 'probabilities'}``)."""
    sheet, probabilities = grading['sheet'], grading['probabilities']
    if sheet['schema'] not in SHEET_SCHEMAS:
        raise ValueError('blast_database_sheet_required')
    hits = sheet['hits']
    evalues = [hit['measurements']['minimum_evalue'] for hit in hits
               if hit['measurements']['minimum_evalue'] is not None]
    unadjusted = probabilities['unadjusted_probabilities'] or {}
    adjusted = probabilities['representation_adjusted_probabilities'] or {}
    rows = []
    for row in sheet['functions']:
        groups = {group['group_index'] for group in sheet['sequence_groups'] if row['function'] in group['functions']}
        own = [hit['measurements']['minimum_evalue'] for hit in hits
               if hit['sequence_group_index'] in groups and hit['measurements']['minimum_evalue'] is not None]
        ranks = [rank for rank in row['taxonomy']['ranks'] if rank['rank'] == TAXON_RANK]
        rows.append({'function': row['function'], 'supporting_group_count': row['sequence_group_count'],
                     'competing_function_count': max(len(unadjusted) - 1, 0), **_present(
                         max_bit_score=row['bit_score']['maximum'],
                         max_query_paired_coverage=row['query_paired_coverage']['maximum'],
                         conditional_weight=unadjusted.get(row['function']),
                         representation_adjusted_weight=adjusted.get(row['function']),
                         target_taxon_matching_fraction=ranks[0]['target_matching_fraction'] if ranks else None,
                         uncertainty_magnitude=min(own) if own else None)})
    features = {'evidence_type': EVIDENCE_TYPE, 'sheet_refs': [sheet_ref],
                'routed_to_axis_credit': sheet['normalized_result']['search']['program'] == 'blastp',
                'total_group_count': sheet['coverage']['sequence_group_count'],
                'groups_without_function': sheet['coverage']['groups_without_explicit_function'],
                'duplicate_hit_count': sheet['dependence']['duplicate_native_hit_count'],
                'sequence_identity_unresolved': sheet['dependence']['unknown_cross_hit_sequence_identity'],
                'uncertainty_kind': UNCERTAINTY_KIND, 'uncertainty_sampling_basis': SAMPLING_BASIS,
                **_present(search_limit_reached=sheet['search_limits']['limit_reached'],
                           unannotated_fraction=probabilities['unannotated_reference_kernel_fraction'],
                           uncertainty_magnitude=min(evalues) if evalues else None),
                'functions': rows}
    return validate_features(features)


def saved_grading_features(reader, grading_ref):
    """The features of one retained grading artifact this Episode holds (``tool_grading_artifact``)."""
    body = json.loads(reader.get_artifact(grading_ref))
    return grading_features(body['grading'], grading_ref)


# -- The identification context of a retained database grading ---------------------------------------------------
#
# A database search identifies what a query most likely is from the whole hit list. The sheet keeps the pieces the
# owner named as data: how the hits' taxa sit together (taxon counts and same-taxon pair fractions at each rank, and
# agreement with the target's own taxon where it is known), where the references came from (sources, assembly
# measurements) and how often each annotated function occurs in the database. The probability model deliberately uses
# none of them. ``context_features(grading)`` reads those retained pieces and nothing else and returns them as numbers,
# counts, booleans and values of a fixed vocabulary, validated by the same ``validated``: it computes no weight, no
# probability and no verdict about an outlier or a horizontally transferred gene, a feature the sheet leaves without a
# value is absent, and counts are of sequence groups so a repeated hit adds no independent vote.
# The exact rank names the taxonomy source uses; the top rank is named ``superkingdom`` by older and ``domain`` by
# newer records, and a sheet holds whichever its taxonomy records carry. A rank outside this vocabulary is not read.
RANKS = ('superkingdom', 'domain', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species')
TOP_RANKS = ('superkingdom', 'domain')
QUALITY_FIELDS = ('completeness_fraction', 'contamination_fraction', 'contig_count', 'contig_n50',
                  'total_sequence_length')

# name -> rule: ('number', low, high), ('count',), ('choice', options), ('boolean',), ('text',), ('optional', rule)
RANK_RULES = {
    'rank': ('choice', RANKS),
    'unambiguous_group_count': ('count',),
    'ambiguous_group_count': ('count',),
    'unknown_group_count': ('count',),
    'distinct_taxon_count': ('count',),
    'dominant_taxon_share': ('optional', ('number', 0, 1)),
    'same_taxon_pair_fraction': ('optional', ('number', 0, 1)),
    'target_matching_fraction': ('optional', ('number', 0, 1)),
    'target_conflicting_group_count': ('optional', ('count',)),
}
QUALITY_RULES = {
    'field': ('choice', QUALITY_FIELDS),
    'quality_method': ('optional', ('text',)),
    'count': ('count',),
    'minimum': ('optional', ('number', -math.inf, math.inf)),
    'maximum': ('optional', ('number', -math.inf, math.inf)),
    'mean': ('optional', ('number', -math.inf, math.inf)),
}
CLASS_RULES = {'source_class': ('choice', SOURCE_CLASSES), 'sequence_group_count': ('count',)}
REPRESENTATION_ROW_RULES = {
    'function': ('text',),
    'database_sequence_count': ('optional', ('count',)),
    'database_total_sequence_count': ('optional', ('count',)),
    'database_fraction': ('optional', ('number', 0, 1)),
}
FUNCTION_RULES = {'function': ('text',)}
CONTEXT_MEANINGS = {
    'distinct_taxon_count': 'Distinct taxa at the rank among the sequence groups that have exactly one taxon there',
    'dominant_taxon_share': 'Share of those groups that fall in the most common taxon at the rank, 0 to 1',
    'same_taxon_pair_fraction': 'Fraction of group pairs that share a taxon at the rank, 0 to 1',
    'target_matching_fraction': 'Fraction of groups whose taxon at the rank is the target\'s own taxon, 0 to 1 '
                                '(absent when the target\'s taxon is not independently known)',
    'top_rank_mixing': 'Whether the groups fall in more than one taxon at the top rank (domain)',
    'source_class': 'The kind of source a reference came from, by the fixed vocabulary of blast_source_class',
    'adjustment_available': 'Whether database counts matching the searched database and release were supplied',
}


def rank_entry(row):
    """The features of one rank row of a sheet's taxonomy summary."""
    counts = row['taxon_group_counts']
    unambiguous = row['unambiguous_group_count']
    dominant = max(counts.values()) / unambiguous if counts and unambiguous else None
    return validated({'rank': row['rank'], 'unambiguous_group_count': unambiguous,
                    'ambiguous_group_count': row['ambiguous_group_count'],
                    'unknown_group_count': row['unknown_group_count'], 'distinct_taxon_count': len(counts),
                    **_present(dominant_taxon_share=dominant,
                               same_taxon_pair_fraction=row['same_taxon_pair_fraction'],
                               target_matching_fraction=row['target_matching_fraction'],
                               target_conflicting_group_count=row['target_conflicting_groups'])},
                   RANK_RULES, 'blast_database_rank')


def taxonomy_features(taxonomy):
    """The rank rows of one taxonomy summary in the vocabulary's order, and ``top_rank_mixing`` when the summary has
    a top rank with at least one group of exactly one taxon (absent otherwise: no mixing is not assumed)."""
    by_rank = {row['rank']: row for row in taxonomy['ranks'] if row['rank'] in RANKS}
    ranks = [rank_entry(by_rank[rank]) for rank in RANKS if rank in by_rank]
    out = {'ranks': ranks}
    top = next((entry for entry in ranks if entry['rank'] in TOP_RANKS and entry['unambiguous_group_count'] > 0),
               None)
    if top is not None:
        out['top_rank_mixing'] = top['distinct_taxon_count'] > 1
    return out


def quality_entries(source_quality):
    """The reported assembly measurements of the references, summarised by field and by the method that measured
    them (a measurement is never pooled across methods)."""
    rows = []
    for summary in source_quality['numerical_summaries']:
        if summary['field'] not in QUALITY_FIELDS:
            continue
        rows.append(validated({'field': summary['field'], 'count': summary['count'], **_present(
            quality_method=summary['quality_method'], minimum=summary['minimum'], maximum=summary['maximum'],
            mean=summary['mean'])}, QUALITY_RULES, 'blast_database_quality'))
    return rows


def representation_entries(representation):
    """How often each function occurs in the searched database, as the independently supplied profile gave it.
    ``available`` is true only when the counts matched the database and release; otherwise the counts are absent."""
    rows = [validated({'function': row['function'], **_present(
        database_sequence_count=row['database_sequence_count'],
        database_total_sequence_count=row['database_total_sequence_count'],
        database_fraction=row['database_fraction'])}, REPRESENTATION_ROW_RULES, 'blast_database_representation')
        for row in representation['function_representation']]
    return {'adjustment_available': bool(representation['available_for_adjustment']),
            'unavailable_reason_count': len(representation['reasons']), 'rows': rows}


def context_features(grading, tables=DEFAULT_TABLES):
    """The identification context of one retained database grading (``{'sheet', 'probabilities'}``)."""
    sheet = grading['sheet']
    if sheet['schema'] not in SHEET_SCHEMAS:
        raise ValueError('blast_database_sheet_required')
    representation = representation_entries(sheet['database_representation'])
    fraction = {row['function']: row.get('database_fraction') for row in representation['rows']}
    functions = []
    for row in sheet['functions']:
        entry = validated({'function': row['function']}, FUNCTION_RULES, 'blast_database_function')
        entry['taxonomy'] = taxonomy_features(row['taxonomy'])
        if fraction.get(row['function']) is not None:
            entry['database_fraction'] = fraction[row['function']]
            if not valid(entry['database_fraction'], ('number', 0, 1)):
                raise ValueError('blast_database_function_feature_invalid:database_fraction')
        functions.append(entry)
    return {'taxonomy': taxonomy_features(sheet['taxonomy']),
            'source': {'class_counts': [validated(row, CLASS_RULES, 'blast_database_source_class')
                                        for row in source_class_counts(sheet, tables)],
                       'quality': quality_entries(sheet['source_quality'])},
            'representation': representation, 'functions': functions}
