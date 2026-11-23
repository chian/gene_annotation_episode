"""The two sheets of an all-vs-all result: the similarity graph and the family context. Pure; no tool, no model.

The graph sheet holds what the report says (directed edges, completeness by chunk and by query) and the numbers read
from it; the family-context sheet holds the clusters under recorded thresholds and the controlled features of the
target's place in them. Both are kept through custody by the episode (``retain_tool_grading``) and the features are
read back from the saved sheet by code (``saved_*_features``), never restated from a tool's own words. Neither sheet
assigns support or credit: the sheet's own scorer decides what the numbers mean.

The family-context features are the ones ``blast_all_vs_all_features`` reads plus four measures of the owner's
decision D18 that it does not give: how near the closest member of the cluster's top function is, how near the closest
member of another function is, the share of the cluster the target links to directly (core versus outlier) and how
near the closest sequence outside the cluster is (separation). A feature that cannot be computed is absent."""
from __future__ import annotations

import json

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.feature_rules import (
    validated)

GRAPH_SCHEMA = 'blast_all_vs_all_graph_sheet'
CONTEXT_SCHEMA = 'blast_all_vs_all_context_sheet'
GRAPH_PROVIDER = 'native.blast.all_vs_all.graph'
CONTEXT_PROVIDER = 'native.blast.all_vs_all.context'
_OPT = 'optional'

GRAPH_RULES = {
    'graph_status': ('choice', ('complete', 'incomplete')), 'searched_fraction': ('number', 0, 1),
    'record_count': ('count',), 'total_letters': ('count',), 'edge_count': ('count',),
    'missing_chunk_count': ('count',), 'missing_query_count': ('count',), 'partial_self_hit_count': ('count',)}
CONTEXT_RULES = {
    'graph_status': ('choice', ('complete', 'incomplete')), 'searched_fraction': ('number', 0, 1, _OPT),
    'cluster_count': ('count',), 'largest_cluster_size': ('count',), 'singleton_cluster_count': ('count',),
    'target_in_set': ('boolean', _OPT), 'cluster_size': ('count', _OPT), 'singleton': ('boolean', _OPT),
    'independent_member_count': ('count', _OPT), 'neighbor_count': ('count', _OPT),
    'cluster_density': ('number', 0, 1, _OPT), 'neighbor_identity_min': ('number', 0, 1, _OPT),
    'neighbor_identity_median': ('number', 0, 1, _OPT), 'neighbor_identity_max': ('number', 0, 1, _OPT),
    'neighbor_coverage_min': ('number', 0, 1, _OPT), 'annotated_member_count': ('count', _OPT),
    'independent_annotated_count': ('count', _OPT), 'top_annotation': ('text', _OPT),
    'annotation_agreement': ('number', 0, 1, _OPT), 'distinct_annotation_count': ('count', _OPT),
    'nearest_top_annotation_identity': ('number', 0, 1, _OPT),
    'nearest_other_annotation_identity': ('number', 0, 1, _OPT), 'core_fraction': ('number', 0, 1, _OPT),
    'nearest_outside_cluster_identity': ('number', 0, 1, _OPT)}


def graph_grading(edges, completeness, *, whole, parameters, chunks):
    """The graph sheet. ``whole`` is the set's digest, record count and total letters; ``chunks`` is
    ``{'expected', 'present'}``; ``completeness`` is the record of ``blast_all_vs_all_graph.completeness``."""
    expected = completeness['expected_queries']
    features = validated({
        'graph_status': completeness['status'],
        'searched_fraction': round(completeness['searched_queries'] / expected, 6) if expected else 0.0,
        'record_count': whole['record_count'], 'total_letters': whole['total_letters'], 'edge_count': len(edges),
        'missing_chunk_count': len(completeness['missing_chunks']),
        'missing_query_count': len(completeness['missing_queries']),
        'partial_self_hit_count': len(completeness['partial_self_hits'])}, GRAPH_RULES, 'blast_all_vs_all_graph')
    return {'sheet': {'schema': GRAPH_SCHEMA, 'input': {'set': whole, 'parameters': parameters, 'chunks': chunks},
                      'graph': {'edges': edges, 'completeness': completeness}, 'features': features}}


def _identity_to(target, edges):
    """For each sequence the target meets in the graph, the highest identity of an edge between them, either way."""
    best = {}
    for edge in edges:
        if edge['self'] or target not in (edge['query'], edge['subject']):
            continue
        other = edge['subject'] if edge['query'] == target else edge['query']
        best[other] = max(best.get(other, 0.0), edge['identity'])
    return best


def separation_features(target, edges, cluster, annotations, top_annotation, neighbor_count):
    """The four D18 measures of ``target`` in ``cluster`` (a record of ``cluster_components``). ``annotations`` maps a
    member to an annotation identifier or ``None``; ``top_annotation`` is the cluster's commonest, or ``None``."""
    identity = _identity_to(target, edges)
    members = set(cluster['members'])
    found = {}
    if top_annotation is not None:
        same = [identity[m] for m in identity if m in members and annotations.get(m) == top_annotation]
        other = [identity[m] for m in identity
                 if annotations.get(m) is not None and annotations.get(m) != top_annotation]
        if same:
            found['nearest_top_annotation_identity'] = max(same)
        if other:
            found['nearest_other_annotation_identity'] = max(other)
    if cluster['size'] > 1:
        found['core_fraction'] = round(neighbor_count / (cluster['size'] - 1), 6)
    outside = [identity[m] for m in identity if m not in members]
    if outside:
        found['nearest_outside_cluster_identity'] = max(outside)
    return found


def context_grading(*, features, clusters, groups, thresholds, strict, target):
    """The family-context sheet: the recorded thresholds, the clusters (with their independent member counts) and the
    controlled features. ``features`` is already read from the clustered graph."""
    checked = validated(features, CONTEXT_RULES, 'blast_all_vs_all_context')
    return {'sheet': {'schema': CONTEXT_SCHEMA,
                      'input': {'thresholds': thresholds, 'strict_thresholds': strict, 'target': target},
                      'clusters': clusters, 'groups': groups, 'features': checked}}


def _saved_sheet(reader, grading_ref, schema):
    sheet = json.loads(reader.get_artifact(grading_ref))['grading']['sheet']
    if sheet['schema'] != schema:
        raise ValueError('blast_all_vs_all_saved_sheet_schema_conflict:' + str(sheet['schema']))
    return sheet


def saved_graph_features(reader, grading_ref):
    """The controlled features of one retained graph grading this episode holds."""
    return validated(_saved_sheet(reader, grading_ref, GRAPH_SCHEMA)['features'], GRAPH_RULES, 'blast_all_vs_all_graph')


def saved_context_features(reader, grading_ref):
    """The controlled features of one retained family-context grading this episode holds."""
    return validated(_saved_sheet(reader, grading_ref, CONTEXT_SCHEMA)['features'], CONTEXT_RULES,
                     'blast_all_vs_all_context')


__all__ = ['CONTEXT_PROVIDER', 'CONTEXT_RULES', 'CONTEXT_SCHEMA', 'GRAPH_PROVIDER', 'GRAPH_RULES', 'GRAPH_SCHEMA',
           'context_grading', 'graph_grading', 'saved_context_features', 'saved_graph_features',
           'separation_features']
