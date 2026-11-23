"""The investigation finding of the A101 axis sheet (``a101_native_correspondence_015``): controlled features
that code reads from the sheet of each target, each with its validator (``INVESTIGATION_FINDING_FEATURES_a101.md``
sections 1 and 2.3).

One entry per target of the scope. The sheet's ``value`` is not a feature: it is the credit, and the credit is never
restated. A feature the sheet leaves without a value (an algorithm outside the profile, no comparison) is absent
from the entry; nothing is defaulted. The per-residue intervals, target symbols and residue pairs stay in the
sheet."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.feature_rules import validated

EVIDENCE_TYPE = 'native_correspondence_aggregate'
ALGORITHMS = ('blast', 'hmmer')
UNCERTAINTY_KIND = 'native_evalue'
SAMPLING_BASIS = 'native_search_space'
ALL = 2 ** 62    # every comparison row of the sheet (``read_details`` pages them)

# name -> validator: ('number', low, high[, 'optional']), ('count',), ('choice', options), ('boolean',)
FEATURES = {
    'evidence_type': ('choice', (EVIDENCE_TYPE,)),
    'blast_component': ('number', 0, 1, 'optional'),
    'hmmer_component': ('number', 0, 1, 'optional'),
    'algorithm_count': ('count',),
    'algorithms_agree': ('boolean',),
    'comparison_count': ('count',),
    'distinct_reference_count': ('count',),
    'max_bits': ('number', -math.inf, math.inf, 'optional'),
    'min_native_evalue': ('number', 0, math.inf, 'optional'),
    'max_reference_paired_fraction': ('number', 0, 1, 'optional'),
    'max_alignment_identity': ('number', 0, 1, 'optional'),
    'region_count': ('count',),
    'uncovered_region_count': ('count',),
    'uncertainty_kind': ('choice', (UNCERTAINTY_KIND,)),
    'uncertainty_magnitude': ('number', 0, math.inf, 'optional'),
    'uncertainty_sampling_basis': ('choice', (SAMPLING_BASIS,)),
    'function_specific_assessed': ('boolean',),
}
MEANINGS = {
    'evidence_type': 'The A101 evidence type: native_correspondence_aggregate (the axis sheet of one target)',
    'blast_component': 'Region-length-weighted BLAST component of the sheet, 0 to 1 (absent when BLAST is not in '
                       'the profile)',
    'hmmer_component': 'Region-length-weighted HMMER component of the sheet, 0 to 1 (absent when HMMER is not in '
                       'the profile)',
    'algorithm_count': 'Algorithms in the profile (0 to 2)',
    'algorithms_agree': 'Whether both algorithms are in the profile and both components are above zero',
    'comparison_count': 'Native comparisons the sheet scored',
    'distinct_reference_count': 'Distinct native references (hits) among the comparisons',
    'max_bits': 'Largest native bit score among the comparisons (bits)',
    'min_native_evalue': 'Smallest native E-value among the comparisons (expected chance hits)',
    'max_reference_paired_fraction': 'Largest paired fraction of a reference, 0 to 1',
    'max_alignment_identity': 'Largest BLAST alignment identity, 0 to 1',
    'region_count': 'Required regions of the target',
    'uncovered_region_count': 'Required regions with no correspondence (any makes the sheet zero)',
    'uncertainty_kind': 'The kind of uncertainty: native_evalue',
    'uncertainty_magnitude': 'The smallest native E-value (expected chance hits)',
    'uncertainty_sampling_basis': 'The sampling basis of the uncertainty: native_search_space',
    'function_specific_assessed': 'Whether the function-specific index was assessed (it is not, today)',
}


def validate_features(features):
    """Each feature against its validator; a violation raises ``ValueError``."""
    return validated(features, FEATURES, 'a101_axis_finding')


def _present(**values):
    return {name: value for name, value in values.items() if value is not None}


def target_features(summary, comparisons):
    """The features of one target's sheet: its summary (``read_details``'s ``a101_sheet.targets[t]``) and its
    comparison rows."""
    regions, profile = summary['regions'], summary['profile']
    total = sum(region['length'] for region in regions)
    components = {algorithm: math.fsum(region['algorithm_components'][algorithm] * region['length']
                                       for region in regions) / total
                  for algorithm in profile}
    evalues = [row['native_evalue'] for row in comparisons if row.get('native_evalue') is not None]
    identities = [row['alignment_identity'] for row in comparisons if row['algorithm'] == 'blast']
    references = {(row['grading_artifact_ref'], row['hit_index'] if row['algorithm'] == 'blast'
                   else row['target_name']) for row in comparisons}
    features = {'evidence_type': EVIDENCE_TYPE, 'algorithm_count': len(profile),
                'algorithms_agree': len(profile) == 2 and all(value > 0 for value in components.values()),
                'comparison_count': len(comparisons), 'distinct_reference_count': len(references),
                'region_count': len(regions),
                'uncovered_region_count': sum(1 for region in regions if region['value'] == 0),
                'uncertainty_kind': UNCERTAINTY_KIND, 'uncertainty_sampling_basis': SAMPLING_BASIS,
                'function_specific_assessed': summary['function_specific_index']['status'] != 'not_assessed',
                **_present(blast_component=components.get('blast'), hmmer_component=components.get('hmmer'),
                           max_bits=max((row['bits'] for row in comparisons), default=None),
                           min_native_evalue=min(evalues, default=None),
                           max_reference_paired_fraction=max((row['reference_paired_fraction']
                                                              for row in comparisons), default=None),
                           max_alignment_identity=max(identities, default=None),
                           uncertainty_magnitude=min(evalues, default=None))}
    return validate_features(features)


def axis_features(details):
    """The features of every target of a ``read_details`` result read with every comparison row
    (``details_limit=ALL``), in the order of the scope's targets."""
    rows = details['source_contributions']
    if len(rows) != details['detail_pages']['source_contributions_total']:
        raise ValueError('a101_axis_finding_requires_every_comparison')
    return [target_features(summary, [row for row in rows if row['target_ref'] == target])
            for target, summary in details['a101_sheet']['targets'].items()]
