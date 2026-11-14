"""A106 retained summary statistics and explicit mean-covariance arithmetic.

The retained data are an input boundary, not a claim that a paper was parsed.
Reported spreads, raw-unit descriptive statistics, sampling variance estimates
and digitization constraints retain different meanings. No distributional fit,
confidence interval or causal/annotation score is invented here.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_perturbation_calculations import COMPONENTS as POINT_COMPONENTS
ROLES = ('W', 'K', 'R', 'A_reference', 'A_restored', 'B_pert', 'B_rest')
SUMMARY_KINDS = ('arithmetic_mean', 'geometric_mean', 'median', 'single_observation', 'unknown')
SCALES = ('endpoint', 'log10_endpoint', 'ln_endpoint', 'unknown')
SPREAD_KINDS = ('sd', 'sem', 'confidence_interval', 'detection_limit', 'untyped_pm', 'unreported')
VARIANCE_STATUSES = ('known', 'estimated', 'unknown')
VARIANCE_SCOPES = ('technical_mean_within_studied_unit', 'biological_unit_mean', 'preparation_mean', 'other_unit_mean', 'source_reported_unresolved_scope', 'mixed_estimator_scopes', 'unavailable', 'not_applicable')
UNIT_KINDS = ('culture', 'organism', 'preparation', 'biological_unit', 'technical_reading', 'other', 'unknown')
STATISTICS = ('summary_value', 'reported_spread', 'reported_count', 'sample_sd', 'mean_se', 'mean_variance')
STAT_COMPONENTS = tuple((role + '_' + name for role in ROLES for name in STATISTICS))
CONTRAST_COMPONENTS = ('perturbation_mean_variance', 'perturbation_variance_lower', 'perturbation_variance_upper', 'restoration_difference', 'restoration_mean_variance', 'restoration_variance_lower', 'restoration_variance_upper', 'shared_contrast_covariance')
COMPONENTS = (*POINT_COMPONENTS, *STAT_COMPONENTS, *CONTRAST_COMPONENTS)
INTERPRETATION_BASIS_FIELDS = ('summary_kind', 'summary_scale', 'spread_kind', 'spread_scale', 'count_n', 'count_unit', 'count_independence')
INTERPRETATION_BASES = ('source_reported', 'source_supported_inference', 'conditional_assumption', 'unresolved')
