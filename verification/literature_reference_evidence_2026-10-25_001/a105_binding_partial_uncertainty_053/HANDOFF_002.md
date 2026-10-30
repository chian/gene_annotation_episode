# 053 released partial uncertainty correction

This is the parent-reviewed additive correction to048's pure binding-interaction
input contract. It preserves valid reported parameters when individual source
uncertainty details are unresolved. It adds no experiment grader, evidence axis,
annotation-credit aggregation, source parser or runtime behavior.

## Exact released contract

`uncertainty=null` means unresolved/not supplied metadata, distinct from a supplied
object declaring `statistic=unreported`. A supplied SD/SEM/unspecified statistic
can retain a null magnitude. A CI can retain `interval=null`, `[null,null]`, or two
individually nullable finite endpoints; its confidence level is independently
nullable. Missing endpoints mean unknown, never infinity or censor bounds.
The exact supplied representation remains in detached returned inputs.

Known endpoints must be ordered; known confidence levels must be finite and
strictly between0and1. Symmetric spread is independently finite nonnegative or
null, even when the entire uncertainty object is null. Unreported parameters
cannot carry spread. CI and supplied-unreported statistics cannot carry spread;
non-CI statistics cannot carry interval/level. All original counts, source,
identity, relationship, covariance, normality and score prerequisites remain.

The four new qualification codes are finite and suffixed by an existing fixed
role: uncertainty_metadata_unresolved, reported_uncertainty_magnitude_unknown,
confidence_interval_endpoints_incomplete, confidence_level_unknown. They report
missing meanings without manufacturing a number or quality category.

A synthetic reported point5 with CI[4,6] and no confidence level is now preserved
alongside the other5,40,2,4 fixture parameters, yielding D=4. No model is inferred
from any CI, SD/SEM, count or physical-fit identifier. An independently supplied
applicable model still needs exact record owners, known covariance, normal log
observations and positive contrast variance for S/B. Unknown/estimated covariance
status is never upgraded. Printed limits remain thresholds, not point estimates
or confidence bounds.

## Stable bytes and historical boundary

| File | Original048 SHA256 | Released053 SHA256 |
|---|---|---|
| calculator | 26dffa5d6d9e4eb4b419f2243369344bebc6eee2c637a141edfaedb21cd3232e | ac7ea12c105e16df5085942090ec8e3f96c618b4f5866283325c46c92804b432 |
| dedicated tests | 0ed1dd22a04fcb691e6ba848c029bf2343e4aac8781e281c2d2532450c493c79 | 1a61ddd3126eec2293b75efdaac8e1ef77d4dfeab0cb3040bef31c13dccb60ed |

Original files were preserved in baseline_001/ before any edit and verified exact
after the terminal run. Final full files are in snapshot_002/. FULL_PATCH_002.diff
contains every change to the two released existing files. No historical048/049
artifacts, root reconstructions or checkpoints were edited. Old complete-metadata
requirements remain historical facts; only the reviewed partial-state contract
above intentionally supersedes that restriction for current code.

## Actual verification

TERMINAL_002.txt records the dedicated test command, actual output and exit0:
**99 passed in0.38s**. Test totals overlap and must not be added to prior runs or
the comparisons below. An initial development run exposed test-fixture mistakes
about the existing threshold representation and `not_matched` enum; those test
expectations were corrected, without changing the existing arithmetic or enum.

BASELINE_COMPARISON_002.json retains both full results for84 synthetic comparisons
(21 accepted inputs times no model/known/estimated/unknown model). Every complete
dictionary and its sorted finite JSON serialization matches048 exactly. Cases
cover point directions, extreme numeric scales, complete uncertainty/counts,
condition scopes/statuses, printed limits and both supported parameter kinds.

AST_UNCHANGED_PROOF_002.json proves all24 other original functions exact,
including arithmetic, PSD/model validation, identity, source/count validation,
relationships and scientific availability checks. `populate_binding_interaction`
is AST-exact after removing its one new partial-qualification extension. Only
`_uncertainty` validation changed; `_uncertainty_qualifications` is the sole new
function. Constants add only the finite code vocabulary.

Dedicated checks additionally cover partial preservation/contradictions, no
inferred model, exact owner mismatch, unknown/estimated status retention and an
independent constrained-normal optimization for both score directions with
complete and partial CI metadata. RELEASE_RECEIPT_002.json records artifact
hashes, source stability through the terminal run and verification boundaries.

## Integration boundary

The released contract and exact final hashes were sent to052's native adapter
owner for its own actual compatibility run. No052 files were edited. This053
receipt does not claim that adapter, paper interpretation, Store custody, source
acquisition, runtime or provider execution was verified here. No paper or
paper-specific source packet was read, so no paper reset applies. No W05,
annotation transfer or overall A105 completion is claimed.
