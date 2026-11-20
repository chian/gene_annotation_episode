"""The investigation finding of a retained A101 BLAST database grading (``blast_database_sheet_v1/v2/v3`` with its
``blast_database_probabilities_v1``): controlled features that code reads from the saved grading artifact, each with
its validator (``INVESTIGATION_FINDING_FEATURES_a101.md`` sections 1 and 5.3).

One entry per saved grading: the evidence type (fixed by the sheet schema; the model never picks it), the grading
artifact's reference, whether the sheet is routed into the A101 axis sheet (``route_native_grading`` routes BLAST
only for ``blastp``), the population counts of the sheet and one row per explicit function of the sheet. A feature
that the sheet leaves null (no metadata, no adjustment, no target taxonomy) is absent from the entry: nothing is
defaulted. No source titles, descriptions, assumptions or meanings travel: they stay in the sheet."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.feature_rules import validated

EVIDENCE_TYPE = 'protein_database_homologs'
SHEET_SCHEMAS = ('blast_database_sheet_v1', 'blast_database_sheet_v2', 'blast_database_sheet_v3')
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
    """The features of one retained grading artifact this Episode holds (``tool_grading_artifact_v1/v2``)."""
    body = json.loads(reader.get_artifact(grading_ref))
    return grading_features(body['grading'], grading_ref)
