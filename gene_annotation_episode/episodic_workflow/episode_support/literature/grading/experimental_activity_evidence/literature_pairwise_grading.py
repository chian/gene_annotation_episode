"""A105's own grading of one pairwise BLAST report (a copy of what A101's pairwise comparison does, owned by A105).

The one native JSON report of the comparison of two sequences is graded into the pairwise sheet
(``blast_pairwise_sheet``), the graded result is kept through the scoped store (the grading artifact and its data-product
row) and the controlled features of the sheet are read by code. The features are counts and fractions of paired residues
(a count, a number in a range, a boolean, a value of a fixed vocabulary or a record reference); nothing is prose.

When BLAST reports no alignment between the two sequences the sheet is the graded "no reported alignment" result: it holds
no reference record and no residue pair, its coverages are 0 and it has no ``paired_identity`` (and no ``reference_length``,
which only a reported hit carries). That is a normal outcome, not an error."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.blast_grading_inputs import (
    parse_blast_json)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.blast_pairwise_grader import (
    build_pairwise_artifacts, validate_blast_correspondence_instance)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_alignment.alignment_correspondence import (
    ARTIFACT_SCHEMA, validate_correspondence_artifacts)

EVIDENCE_TYPE = 'pairwise_residue_correspondence'
SHEET_SCHEMA = 'blast_pairwise_sheet'
PROVIDER = 'native.blast.pairwise'
GRADING_SCHEMA = 'tool_grading_artifact_with_correspondence'
GRADING_MEDIA_TYPE = 'application/vnd.gene-annotation.tool-grading+json'
GRADING_KIND = 'tool_grading_sheet'

# name -> validator: ('number', low, high), ('count',), ('choice', options), ('boolean',), ('ref',); a last item
# 'optional' marks a feature absent when the sheet or the report holds no value for it.
SHEET_FEATURES = {
    'evidence_type': ('choice', (EVIDENCE_TYPE,)),
    'sheet_refs': ('ref',),
    'traceback_complete': ('boolean',),
    'hsp_count': ('count',),
    'issue_count': ('count',),
    'query_length': ('count',),
    'reference_length': ('count', 'optional'),
    'paired_query_positions': ('count',),
    'paired_reference_positions': ('count',),
    'identical_residue_pairs': ('count',),
    'query_paired_coverage': ('number', 0, 1),
    'reference_paired_coverage': ('number', 0, 1),
    'paired_identity': ('number', 0, 1, 'optional'),
    'min_native_evalue': ('number', 0, math.inf, 'optional'),
    'expect_threshold': ('number', 0, math.inf, 'optional'),
    'effective_search_space': ('number', 0, math.inf, 'optional'),
    'effective_hsp_length': ('number', 0, math.inf, 'optional'),
    'karlin_lambda': ('number', 0, math.inf, 'optional'),
    'karlin_kappa': ('number', 0, math.inf, 'optional'),
    'karlin_entropy': ('number', 0, math.inf, 'optional'),
}
# the report's own names for the search-space statistics, and the feature each fills
STATISTICS = {'eff_space': 'effective_search_space', 'hsp_len': 'effective_hsp_length', 'lambda': 'karlin_lambda',
              'kappa': 'karlin_kappa', 'entropy': 'karlin_entropy'}


def _optional(rule):
    return rule[-1] == 'optional'


def _valid(value, rule):
    kind = rule[0]
    if kind == 'number':
        return type(value) in (int, float) and math.isfinite(value) and rule[1] <= value <= rule[2]
    if kind == 'count':
        return type(value) is int and value >= 0
    if kind == 'choice':
        return value in rule[1]
    if kind == 'boolean':
        return type(value) is bool
    if kind == 'ref':
        return type(value) is list and len(value) == 1 and type(value[0]) is str
    raise ValueError('feature_rule_kind_unknown:' + repr(kind))


def validate_features(features):
    """Each feature against its validator; a violation raises ``ValueError``."""
    required = {name for name, rule in SHEET_FEATURES.items() if not _optional(rule)}
    if not required <= set(features) <= set(SHEET_FEATURES):
        raise ValueError('blast_pairwise_finding_features_mismatch')
    for name, value in features.items():
        if not _valid(value, SHEET_FEATURES[name]):
            raise ValueError('blast_pairwise_finding_feature_invalid:' + name)
    return features


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def grading_features(grading, sheet_ref):
    """The controlled features of one graded pairwise result (``{'sheet', ...}``); ``sheet_ref`` is the reference of its
    saved grading artifact."""
    sheet = grading['sheet']
    if sheet['schema'] != SHEET_SCHEMA:
        raise ValueError('blast_pairwise_sheet_required')
    union = sheet['union']
    counts, fractions = union['counts'], union['fractions']
    if sheet['status'] == 'no_reported_alignment':
        # nothing is paired: the union has no rows, so the sheet leaves these unavailable; the graded result is zero
        counts = {**counts, 'identical_residue_pairs': 0}
        fractions = {**fractions, 'query_paired_coverage': 0.0, 'reference_paired_coverage': 0.0}
    search = sheet['input']['search']
    evalues = [value for value in (_number(row['components']['native_scores'].get('evalue'))
                                   for row in sheet['hsps']) if value is not None]
    statistics = search.get('statistics') or {}
    reference = sheet['reference']
    features = {'evidence_type': EVIDENCE_TYPE, 'sheet_refs': [sheet_ref],
                'traceback_complete': counts['hsps_without_geometry'] == 0 and bool(union['complete_for_reported_hsps']),
                'hsp_count': len(sheet['hsps']), 'issue_count': len(sheet['issues']),
                'query_length': sheet['query']['length'],
                'paired_query_positions': counts['paired_query_positions'],
                'paired_reference_positions': counts['paired_reference_positions'],
                'identical_residue_pairs': counts['identical_residue_pairs'],
                'query_paired_coverage': fractions['query_paired_coverage'],
                'reference_paired_coverage': fractions['reference_paired_coverage']}
    optional = {'reference_length': None if reference is None else reference['length'],
                'paired_identity': fractions.get('paired_identity'),
                'min_native_evalue': min(evalues, default=None),
                'expect_threshold': _number((search.get('parameters') or {}).get('expect')),
                **{feature: _number(statistics.get(name)) for name, feature in STATISTICS.items()}}
    features.update({name: value for name, value in optional.items() if value is not None})
    return validate_features(features)


def graded_report(report, program, query, subject):
    """The grading of the fetched native JSON ``report`` (bytes) as the pairwise sheet of the two operands. A report of
    another sheet type or of sequences of other lengths raises ``ValueError``. A report with no alignment gives the graded
    "no reported alignment" result."""
    normalized = parse_blast_json(report, mode='pairwise', resource='local', request={'program': program, 'query_length': len(query)})
    sheet, common_sheet, calculated = build_pairwise_artifacts(normalized)
    grading = {'sheet': sheet, 'probabilities': None, 'correspondence': {
        'version': ARTIFACT_SCHEMA, 'instances': [{'source_pointer': '/sheet', 'axis_basis': 'reported',
                                                    'sheet': common_sheet, 'components': calculated}]}}
    if sheet['schema'] != SHEET_SCHEMA:
        raise ValueError('blast_pairwise_result_type_conflict')
    if sheet['query']['length'] != len(query) or (
            sheet['reference'] is not None and sheet['reference']['length'] != len(subject)):
        raise ValueError('blast_pairwise_result_operand_conflict')
    return grading


def retain_grading(store, *, native_artifact_ref, grading):
    """Keep the graded result as one artifact through the scoped store and return its reference. The correspondence of the
    sheet travels with it and is validated first."""
    if store.get(native_artifact_ref).get('record_type') != 'artifact':
        raise ValueError('tool_grading_native_artifact_required')
    body = dict(grading)
    correspondence = body.pop('correspondence')
    validated = validate_correspondence_artifacts(correspondence, admission=True)
    (instance,) = validated['instances']
    validate_blast_correspondence_instance(body['sheet'], instance)
    record = {'schema': GRADING_SCHEMA, 'provider': PROVIDER, 'native_artifact_ref': native_artifact_ref,
              'grading': body, 'correspondence': correspondence}
    return store.artifact(json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False), GRADING_MEDIA_TYPE)


def record_grading_product(store, *, grading_ref, grading, source_ref, used):
    """Label the kept grading as a ``tool_grading_sheet`` data product, generated by the comparison's source record over
    the graded report, and return its row."""
    return record_product(store, artifact_ref=grading_ref, kind=GRADING_KIND, generated_by=source_ref, used=list(used),
                          derived_from=[], settings={'provider': PROVIDER, 'sheet_schema': grading['sheet']['schema']})


__all__ = ['PROVIDER', 'SHEET_SCHEMA', 'graded_report', 'grading_features', 'record_grading_product', 'retain_grading',
           'validate_features']
