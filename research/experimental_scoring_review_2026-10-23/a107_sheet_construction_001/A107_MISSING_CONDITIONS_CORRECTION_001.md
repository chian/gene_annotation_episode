# A107: corrected missing-condition calculation

This additive research correction replaces the missing-condition equation in
`a107_partner_sheet_014/A107_NUMERICAL_SHEET_001.md` sections 2.2, 2.4 and the
incomplete-panel example in section 5. It also corrects the corresponding
proposed reader outputs in sections 3 and 5 of `A107_READER_CONTRACTS_001.md`.
The original files remain permanent records. No production scorer, reader,
prompt, library, annotation or episode behavior is changed.

## The error

The draft used `E = H0 [ C D R + (1-C) U ]`, with `R=max(0,r)^2` computed over
the observed condition subset, `C=q/m`, and `U` in [0,1]. This does not bound
the expression score for the requested full condition panel. Correlation of
a union of observations is not a coverage-weighted average of its subset
correlations. The added conditions can change means, variances and covariance,
including the fitted growth correction and the sign of the correlation.

The draft's numerical missing-panel example also uses `D=.8` with 16 paired
condition cells, which would require 12.8 co-detected conditions. Its count
definition cannot produce that exact input. The separate complete synthetic
example uses 16/20 and is not affected by this count error.

## Concrete counterexample

The accompanying independent checker constructs 16 nonnegative log-expression
condition means whose growth-adjusted correlation is .6 and whose co-detection
fraction is 16/16. Four additional valid conditions have expression values
[17,3,3,17] for the target and [3,17,17,3] for its partner. All 20 conditions
are above the proposed threshold. Their growth rates are .1,.2,...,2 h^-1.
The full-panel adjusted correlation is -186.4/212 = -.879245283018868.

With H0=.9 and G=.75, the old missing-panel formula gives partner bounds
[.4722,.5397]. Completing the actual constructed panel gives R=0 and partner
score .375, outside those bounds. These are synthetic arithmetic inputs, not
measurements from PRECISE or a published experiment.

## Correct definition and conservative bounds

The requested panel consists of m declared, equally weighted condition cells.
Let a be the number of paired condition means observed above the co-detection
threshold, q_pair the number with valid paired expression measurements, and
u=m-q_pair. Then:

    D_full = co-detected condition count in the full panel / m
    D_full in [a/m, (a+u)/m]
    r_full = growth-adjusted correlation over the full requested panel
    R_full = max(0,r_full)^2
    E = H0 * D_full * R_full
    s = G * (.5 + .5 * E)

If any required expression or growth operand is unknown, r_full is not
replaced by the observed-subset r. Preserve that subset statistic under its
own scope. Without stronger justified constraints on the missing operands,
the valid conservative domain is r_full in [-1,1], R_full in [0,1]. Thus for
known H0 and G:

    E in [0, H0*(a+u)/m]
    s in [G/2, G*(.5 + .5*H0*(a+u)/m)]

These are outer missing-input bounds, not statistical confidence intervals
and not a claim that every endpoint is attainable with the known rows. Known
expression or growth constraints may narrow the feasible completions. Such
a narrower result must retain the actual joint constraints and its derivation.
Do not narrow it by treating the known subset correlation as an independent
weighted component of the full correlation.

For the counterexample the corrected outer bounds are [.375,.7125], with a
null point before completion. The completed .375 lies inside them. Coverage
16/20 remains a measured diagnostic and describes which inputs are missing;
it is not a multiplier on a subset correlation.

When every paired expression value is observed but some growth values are
unknown, D_full can be known even though r_full is unknown. Therefore retain
q_pair separately from q_adjusted, the count with paired expression and valid
growth data. Do not drop an observed non-detection from the D denominator
because its growth covariate is missing. If the adjusted statistic is
undefined because residual variance is zero, record that reason. It is not
observed negative association. If H0=0 or D_full=0 by valid measurements, E=0
is nevertheless fixed. Missing H0 or G propagates its stated domain through
these nonnegative formulas; no default point is inserted.

For a fully observed panel, use its actual D_full and r_full. The original
fully observed 12-condition calculation and complete 20-condition synthetic
example are unchanged. The same-scope source-block minimum and clause min/max
then operate on the corrected bounds. Their biological conventions remain
proposals, not validated probabilities.

## Exact additional/corrected sheet fields

These are proposed reader outputs, not an implemented reader or LLM prompt.

| Field | Type and meaning |
|---|---|
| `requested_condition_ids` | Unique nonempty condition IDs defining m |
| `paired_expression_condition_ids` | Requested cells with both valid expression means; defines q_pair |
| `adjustable_condition_ids` | Paired cells with valid growth covariates; defines q_adjusted |
| `codetection_observed_count` | Integer a, 0 <= a <= q_pair |
| `codetection_requested_denominator` | Integer m, preserved when data are missing |
| `D_observed_subset` | a/q_pair or null when q_pair=0; diagnostic only for an incomplete panel |
| `D_full_panel` | NumericCell: point when fixed, otherwise null with [a/m,(a+m-q_pair)/m] missing-input bounds |
| `partial_r_observed_subset` | NumericCell with the exact adjustable-condition scope and its own n/df/conditional statistical interval |
| `partial_r_full_panel` | NumericCell: actual full-panel statistic or null; defaults to [-1,1] as a domain for missing operands, not an estimate |
| `missing_expression_operands` | Exact gene/condition cells, units and any justified value constraints |
| `missing_growth_operands` | Exact condition cells, h^-1 units and any justified value constraints |
| `full_panel_missing_bound_method` | `complete_inputs`, `outer_domain`, or `derived_joint_completion_bounds`; null for an invalid definition |
| `joint_completion_constraints` | Typed constraints and their derivation for the last method; no prose quality grade |
| `R_positive_squared_full_panel` | Transform of the full-panel r or its domain; never the subset value relabelled |
| `E_full_panel` | H0*D_full_panel*R_positive_squared_full_panel with point/range and dependence retained |

Existing `matched_q`, `C`, native `partial_r`, and conditional statistical
intervals remain available as scoped observed diagnostics. The compiler's
`source_blocks:[{H0,C,D,r,R,E}]` is insufficiently explicit for an incomplete
panel and must instead carry the observed and full-panel fields above. The
scoring path reads `E_full_panel`. A conditional interval for the observed
subset cannot populate a full-panel statistical interval. Source/biological
unit identities and the original input records remain unchanged.

## Inspection and arithmetic scope

The parent read the complete joined mathematical proposal and proposed reader
contracts. No new primary paper or paper-specific conversion packet was opened
for this correction. Primary scientific interpretations remain attributed to
the worker's recorded source inspections. The parent independently checks the
retained public-input hashes, selects the 28 raw metadata records, recomputes
12 condition means from the retained matrix and reproduces all ten association
rows and three candidate coordinates without importing the worker calculator.
`parent_arithmetic_001.json` records actual results after the checker runs.

The checker does not reprocess sequencing reads, verify biological independence
from raw laboratory records, establish causal interactions, validate the .5/.5
weights or turn this research proposal into an adopted annotation scorer.
