"""The investigation finding of a retained pairwise BLAST grading (``blast_pairwise_sheet_v1``): controlled features
that code reads from the saved grading artifact, each with its validator.

A pairwise sheet records which residues of the query and of the subject correspond and how many, so the features are
counts and fractions of paired residues. The native E-value is a feature too, with the context that makes it
interpretable: the lengths of the two operands and the search-space statistics the report itself gives (the effective
search space, the effective alignment length and the Karlin-Altschul parameters of the scoring system) and the
E-value threshold the search was run with. What the E-value means for scoring is not decided here. The evidence type
is fixed by the sheet schema (the model never picks it) and the sheet stays in the grading artifact, whose reference
the entry carries; per-residue pairs and issue texts travel nowhere. A value the sheet or the report does not hold is
absent from the entry: nothing is defaulted."""
import json
import math

EVIDENCE_TYPE = 'pairwise_residue_correspondence'
SHEET_SCHEMA = 'blast_pairwise_sheet_v1'

# name -> validator: ('number', low, high), ('count',), ('choice', options), ('boolean',), ('refs',); ``optional``
# marks a feature absent when the sheet or the report holds no value for it.
SHEET_FEATURES = {
    'evidence_type': ('choice', (EVIDENCE_TYPE,)),
    'sheet_refs': ('refs',),
    'routed_to_axis_credit': ('boolean',),
    'traceback_complete': ('boolean',),
    'hsp_count': ('count',),
    'issue_count': ('count',),
    'query_length': ('count',),
    'reference_length': ('count',),
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
MEANINGS = {
    'evidence_type': 'The evidence type: pairwise_residue_correspondence (one query against one subject)',
    'sheet_refs': 'The reference of the saved grading artifact the features were read from',
    'routed_to_axis_credit': 'Whether the A101 axis sheet takes this grading (route_native_grading takes protein '
                             'BLAST, program blastp, only)',
    'traceback_complete': 'Whether every reported alignment carried its aligned residues, so every pair is known',
    'hsp_count': 'Reported alignments (high-scoring pairs) of the one query against the one subject',
    'issue_count': 'Issues the grader recorded on the sheet (a missing traceback, a malformed field)',
    'query_length': 'Residues in the query operand',
    'reference_length': 'Residues in the subject operand',
    'paired_query_positions': 'Distinct query positions that pair with a subject position in some alignment',
    'paired_reference_positions': 'Distinct subject positions that pair with a query position in some alignment',
    'identical_residue_pairs': 'Distinct residue pairs whose two residues are identical',
    'query_paired_coverage': 'Paired query positions over the query length, 0 to 1',
    'reference_paired_coverage': 'Paired subject positions over the subject length, 0 to 1',
    'paired_identity': 'Identical residue pairs over distinct residue pairs, 0 to 1 (absent when no residue pairs)',
    'min_native_evalue': 'Smallest native E-value among the reported alignments (expected chance alignments of at '
                         'least that score in the effective search space; absent when none reports one)',
    'expect_threshold': 'The E-value threshold the search was run with (absent when the report does not give it)',
    'effective_search_space': 'The effective search space the report gives (absent when it does not)',
    'effective_hsp_length': 'The effective alignment length the report gives for the length adjustment (absent '
                            'when it does not)',
    'karlin_lambda': 'Lambda of the scoring system the report gives (absent when it does not)',
    'karlin_kappa': 'Kappa of the scoring system the report gives (absent when it does not)',
    'karlin_entropy': 'Relative entropy H of the scoring system the report gives (absent when it does not)',
}
# the report's own names for the search-space statistics, and the feature each fills
STATISTICS = {'eff_space': 'effective_search_space', 'hsp_len': 'effective_hsp_length', 'lambda': 'karlin_lambda',
              'kappa': 'karlin_kappa', 'entropy': 'karlin_entropy'}


def _valid(value, rule):
    if rule[0] == 'number':
        return type(value) in (int, float) and math.isfinite(value) and rule[1] <= value <= rule[2]
    if rule[0] == 'count':
        return type(value) is int and value >= 0
    if rule[0] == 'choice':
        return value in rule[1]
    if rule[0] == 'boolean':
        return type(value) is bool
    return type(value) is list and len(value) == 1 and type(value[0]) is str


def validate_features(features):
    """Each feature against its validator; a violation raises ``ValueError``."""
    required = {name for name, rule in SHEET_FEATURES.items() if rule[-1] != 'optional'}
    if not required <= set(features) <= set(SHEET_FEATURES):
        raise ValueError('blast_pairwise_finding_features_mismatch')
    for name, value in features.items():
        if not _valid(value, SHEET_FEATURES[name]):
            raise ValueError('blast_pairwise_finding_feature_invalid:' + name)
    return features


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def grading_features(grading, sheet_ref):
    """The features of one retained pairwise grading (``{'sheet', ...}``)."""
    sheet = grading['sheet']
    if sheet['schema'] != SHEET_SCHEMA:
        raise ValueError('blast_pairwise_sheet_required')
    union = sheet['union']
    counts, fractions = union['counts'], union['fractions']
    search = sheet['input']['search']
    evalues = [value for value in (_number(row['components']['native_scores'].get('evalue'))
                                   for row in sheet['hsps']) if value is not None]
    statistics = search.get('statistics') or {}
    features = {'evidence_type': EVIDENCE_TYPE, 'sheet_refs': [sheet_ref],
                'routed_to_axis_credit': search['program'] == 'blastp',
                'traceback_complete': counts['hsps_without_geometry'] == 0 and bool(union['complete_for_reported_hsps']),
                'hsp_count': len(sheet['hsps']), 'issue_count': len(sheet['issues']),
                'query_length': sheet['query']['length'], 'reference_length': sheet['reference']['length'],
                'paired_query_positions': counts['paired_query_positions'],
                'paired_reference_positions': counts['paired_reference_positions'],
                'identical_residue_pairs': counts['identical_residue_pairs'],
                'query_paired_coverage': fractions['query_paired_coverage'],
                'reference_paired_coverage': fractions['reference_paired_coverage']}
    optional = {'paired_identity': fractions.get('paired_identity'),
                'min_native_evalue': min(evalues, default=None),
                'expect_threshold': _number((search.get('parameters') or {}).get('expect')),
                **{feature: _number(statistics.get(name)) for name, feature in STATISTICS.items()}}
    features.update({name: value for name, value in optional.items() if value is not None})
    return validate_features(features)


def saved_grading_features(reader, grading_ref):
    """The features of one retained grading artifact this Episode holds (``tool_grading_artifact_v1/v2``)."""
    body = json.loads(reader.get_artifact(grading_ref))
    return grading_features(body['grading'], grading_ref)
