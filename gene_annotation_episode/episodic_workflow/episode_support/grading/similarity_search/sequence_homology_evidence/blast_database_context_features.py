"""The identification context of a retained BLAST database grading, as controlled features read by code.

A database search identifies what a query most likely is from the whole hit list. The existing sheet already keeps
the pieces the owner named as data: how the hits' taxa sit together (taxon counts and same-taxon pair fractions at
each rank, and agreement with the target's own taxon where it is known), where the references came from (sources,
assembly measurements), and how often each annotated function occurs in the database. The existing probability
model deliberately uses none of them, and the existing finding features carry only the target's genus match.
This module reads those retained pieces and nothing else, and returns them as numbers, counts, booleans and values
of a fixed vocabulary, so that the parent can use them in the next decision. It computes no weight, no probability
and no verdict about an outlier or a horizontally transferred gene: coherence is given as the measurements it is made
of, and what the measurements mean is the scoring's.

Rules the owner set that hold here: deterministic and without a model; a feature the sheet leaves without a value is
absent from its entry, never defaulted; counts are of sequence groups (duplicate hits are already collapsed), so a
repeated hit adds no independent vote; and no title, description, assumption or meaning text travels.

``context_features(grading)`` takes the retained grading ``{'sheet', 'probabilities'}`` and returns
``{'taxonomy', 'source', 'representation', 'functions'}`` validated against the rules below.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.feature_rules import valid, validated

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_source_class import (
    DEFAULT_TABLES, SOURCE_CLASSES, source_class_counts)

SHEET_SCHEMAS = ('blast_database_sheet_v1', 'blast_database_sheet_v2', 'blast_database_sheet_v3')
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
MEANINGS = {
    'distinct_taxon_count': 'Distinct taxa at the rank among the sequence groups that have exactly one taxon there',
    'dominant_taxon_share': 'Share of those groups that fall in the most common taxon at the rank, 0 to 1',
    'same_taxon_pair_fraction': 'Fraction of group pairs that share a taxon at the rank, 0 to 1',
    'target_matching_fraction': 'Fraction of groups whose taxon at the rank is the target\'s own taxon, 0 to 1 '
                                '(absent when the target\'s taxon is not independently known)',
    'top_rank_mixing': 'Whether the groups fall in more than one taxon at the top rank (domain)',
    'source_class': 'The kind of source a reference came from, by the fixed vocabulary of blast_source_class',
    'adjustment_available': 'Whether database counts matching the searched database and release were supplied',
}


def _present(**values):
    return {name: value for name, value in values.items() if value is not None}


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


__all__ = ['SHEET_SCHEMAS', 'RANKS', 'TOP_RANKS', 'MEANINGS', 'rank_entry', 'taxonomy_features', 'quality_entries',
           'representation_entries', 'context_features']
