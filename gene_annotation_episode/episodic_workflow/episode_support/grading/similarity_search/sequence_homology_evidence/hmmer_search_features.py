"""The investigation finding of retained A101 HMMER search gradings (``hmmer_search_sheet`` with its
``hmmer_search_scores``): controlled features that code reads from the saved grading artifacts, each with its
validator (``INVESTIGATION_FINDING_FEATURES_a101.md`` sections 1 and 6.3).

One entry per hit (reference sequence): the gradings of one hit are its domains (a native phmmer grading holds one
printed alignment, so several domains of one hit are several gradings). The evidence type is fixed by the sheet
schema; the model never picks it. A feature that the sheet leaves null (no model cutoffs, no inclusion flag, an
unavailable measurement) is absent from the entry: nothing is defaulted. Native names, identifiers and definitions
stay in the sheet."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.feature_rules import validated

EVIDENCE_TYPE = 'protein_profile_match'
PROGRAMS = ('phmmer', 'hmmsearch', 'hmmscan', 'jackhmmer')
ROUTED = ('phmmer', 'hmmsearch', 'hmmscan')          # ``route_native_grading`` routes these into the axis sheet
UNCERTAINTY_KIND = 'native_evalue'
SAMPLING_BASIS = 'native_search_space'

# name -> validator: ('number', low, high[, 'optional']), ('count',), ('choice', options), ('boolean'[, 'optional']),
# ('refs',)
FEATURES = {
    'evidence_type': ('choice', (EVIDENCE_TYPE,)),
    'sheet_refs': ('refs',),
    'routed_to_axis_credit': ('boolean',),
    'program': ('choice', PROGRAMS),
    'domain_count': ('count',),
    'max_domain_score_bits': ('number', -math.inf, math.inf, 'optional'),
    'min_independent_evalue': ('number', 0, math.inf, 'optional'),
    'max_domain_bias_bits': ('number', 0, math.inf, 'optional'),
    'model_coverage': ('number', 0, 1, 'optional'),
    'sequence_coverage': ('number', 0, 1, 'optional'),
    'max_sequence_identity': ('number', 0, 1, 'optional'),
    'posterior_lower_mean': ('number', 0, 1, 'optional'),
    'gathering_cutoff_passed': ('boolean', 'optional'),
    'gathering_margin_bits': ('number', -math.inf, math.inf, 'optional'),
    'included': ('boolean', 'optional'),
    'dependent_round': ('boolean',),
    'uncertainty_kind': ('choice', (UNCERTAINTY_KIND,)),
    'uncertainty_magnitude': ('number', 0, math.inf, 'optional'),
    'uncertainty_sampling_basis': ('choice', (SAMPLING_BASIS,)),
}
MEANINGS = {
    'evidence_type': 'The A101 evidence type: protein_profile_match (a HMMER domain correspondence)',
    'sheet_refs': 'The saved grading artifacts of this hit (one per graded domain)',
    'routed_to_axis_credit': 'Whether these sheets enter the A101 axis sheet (phmmer, hmmsearch, hmmscan)',
    'program': 'The HMMER program of the search',
    'domain_count': 'Graded domains of the hit',
    'max_domain_score_bits': 'Largest native domain score (bits)',
    'min_independent_evalue': 'Smallest native independent E-value (expected chance hits)',
    'max_domain_bias_bits': 'Largest native domain bias (bits)',
    'model_coverage': 'Fraction of the query model positions covered by the union of the domains, 0 to 1',
    'sequence_coverage': 'Fraction of the reference sequence covered by the union of the domains, 0 to 1',
    'max_sequence_identity': 'Largest sequence identity fraction of a domain, 0 to 1',
    'posterior_lower_mean': 'Smallest lower mean posterior bound of a domain, 0 to 1',
    'gathering_cutoff_passed': 'Whether the sequence score passes the gathering cutoff (absent without model cutoffs)',
    'gathering_margin_bits': 'Sequence score minus the gathering cutoff (bits; absent without model cutoffs)',
    'included': 'Whether HMMER included the hit (absent when the native flag is unavailable)',
    'dependent_round': 'Whether the hit comes from a dependent iterative round (jackhmmer)',
    'uncertainty_kind': 'The kind of uncertainty: native_evalue',
    'uncertainty_magnitude': 'The smallest native independent E-value (expected chance hits)',
    'uncertainty_sampling_basis': 'The sampling basis of the uncertainty: native_search_space',
}


def validate_features(features):
    """Each feature against its validator; a violation raises ``ValueError``."""
    return validated(features, FEATURES, 'hmmer_search_finding')


def _union_positions(intervals):
    merged = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return sum(b - a for a, b in merged)


def _values(domains, name):
    return [row[name] for row in domains if row.get(name) is not None]


def _present(**values):
    return {name: value for name, value in values.items() if value is not None}


def hit_features(entries):
    """The features of one hit from its saved gradings (``[(grading_artifact_ref, grading)]``, every grading of
    the same hit)."""
    program = entries[0][1]['scores']['operation']['program']
    domains = [row for _, grading in entries for row in grading['scores']['domains']]
    hits = [row for _, grading in entries for row in grading['scores']['hits']]
    iterations = [row for _, grading in entries for row in grading['scores']['iterations']]
    coverage = {}
    for axis, length in (('model', 'model_length'), ('sequence', 'sequence_length')):
        lengths = set(_values(domains, length))
        spans = [row['intervals'][axis] for row in domains if row['intervals'].get(axis)]
        if len(lengths) == 1 and spans and next(iter(lengths)) > 0:
            coverage[axis] = _union_positions(spans) / next(iter(lengths))
    flags = {row['is_included'] for row in hits if row.get('is_included') is not None}
    margins = [value for row in hits for value in row['cutoff_margins']['values']
               if value['cutoff'] == 'GA' and value['scope'] == 'sequence' and value['margin_bits'] is not None]
    evalues = _values(domains, 'native_independent_evalue')
    features = {'evidence_type': EVIDENCE_TYPE, 'sheet_refs': [ref for ref, _ in entries],
                'routed_to_axis_credit': program in ROUTED, 'program': program, 'domain_count': len(domains),
                'dependent_round': any(row['dependent_round'] for row in iterations) if iterations
                else program == 'jackhmmer',
                'uncertainty_kind': UNCERTAINTY_KIND, 'uncertainty_sampling_basis': SAMPLING_BASIS,
                **_present(max_domain_score_bits=max(_values(domains, 'native_domain_score_bits'), default=None),
                           min_independent_evalue=min(evalues, default=None),
                           max_domain_bias_bits=max(_values(domains, 'native_domain_bias_bits'), default=None),
                           model_coverage=coverage.get('model'), sequence_coverage=coverage.get('sequence'),
                           max_sequence_identity=max(_values(domains, 'sequence_identity_fraction'), default=None),
                           posterior_lower_mean=min(_values(domains, 'posterior_lower_mean'), default=None),
                           gathering_cutoff_passed=min(margins) >= 0 if margins else None,
                           gathering_margin_bits=min(margins) if margins else None,
                           included=next(iter(flags)) if len(flags) == 1 else None,
                           uncertainty_magnitude=min(evalues, default=None))}
    return validate_features(features)


def saved_hit_features(reader, grading_refs):
    """The features of each hit among the retained gradings this Episode holds (``tool_grading_artifact``),
    one entry per hit in the order the hits first appear; failed gradings carry no sheet and are left out."""
    by_hit = {}
    for ref in grading_refs:
        grading = json.loads(reader.get_artifact(ref))['grading']
        if grading.get('failure') or grading['sheet'] is None:
            continue
        by_hit.setdefault(grading['scores']['domains'][0]['target_name'], []).append((ref, grading))
    return [hit_features(entries) for entries in by_hit.values()]
