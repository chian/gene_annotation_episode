# 053: preserve incomplete reported binding uncertainty

Proposal only. No production or test edits are released yet. This is a bounded
correction of048's pure input contract, not a new scoring sheet, reader, native
operation or source interpretation. No papers, paper packets, source-specific
selections, live state or private provider histories were opened.

## Established gap

048's validator requires every reported CI to carry both finite endpoints and
a confidence level. It also requires a numeric spread whenever the declared
statistic is SD, SEM or unspecified. A valid reported parameter consequently
cannot reach descriptive D when one uncertainty detail is unavailable, although
neither D nor its log uses those uncertainty values. The whole uncertainty
object cannot be null, forcing an unresolved interpretation toward a potentially
false `statistic=unreported` declaration.

The synthetic baseline script uses only the existing synthetic5,40,2,4 fixture.
It confirms D=4 for complete accepted metadata, captures the complete optional
known-model result, and reproduces rejection of nine partial states. The receipt
does not diagnose a primary paper or bypass Store/outcome authentication.

The currently frozen module/test bytes are preserved before any potential edit:

- module:26dffa5d6d9e4eb4b419f2243369344bebc6eee2c637a141edfaedb21cd3232e
- tests:0ed1dd22a04fcb691e6ba848c029bf2343e4aac8781e281c2d2532450c493c79

BASELINE_001.json and baseline_001/ retain exact full-file copies. Original048
artifacts and the parent's immutable reconstruction remain untouched.

## Proposed exact closed contract

No top-level, operand, uncertainty-object, model or cell keys change. Existing
finite enums retain their meanings. `uncertainty` becomes an explicit union of
null and the existing closed object. Null means unresolved/not supplied metadata;
it does not assert that the source omitted uncertainty. The existing object
with `statistic=unreported` remains a distinct supplied interpretation.

Always validate `reported_spread` before handling nullable metadata: it is null
or a finite nonnegative number, excluding booleans. An unreported parameter
cannot carry a spread, including when uncertainty metadata is null. No interval,
spread, sample-size or likelihood value is synthesized.

| Declared statistic | Symmetric reported spread | Interval | Confidence level |
|---|---|---|---|
| sd / sem / unspecified | null or finite nonnegative magnitude; null preserves known statistic with unavailable magnitude | null | null |
| confidence_interval | null, as now | null or exactly two ordered-position entries, each finite number or null | null or finite probability strictly between0and1 |
| unreported | null, as now | null | null |
| whole metadata null | independently retain valid reported spread, whose statistic is unresolved | no object-level fields exist | no object-level fields exist |

For a CI, position0 is its reported lower endpoint and position1 its upper
endpoint. Missing entries mean unknown endpoints, never minus/plus infinity or
a source-reported censor bound. If both are known, lower≤upper remains required.
`interval=null` and `[null,null]` are both explicit allowed partial representations
and remain exactly as supplied; no normalization manufactures equivalence or
information. A finite endpoint can remain outside the positive parameter domain
as in048; no log-interval conversion occurs.

Known confidence levels remain strictly0<level<1. Bad lengths, strings,
booleans, NaN/infinity, negative symmetric spreads, reversed known endpoints,
non-CI interval/level fields and unreported nonnull spreads remain rejected.
The existing exact/minimum-count checks, basis/repetition enums, source/witness
shapes and `unreported_parameter_uncertainty` guard remain unchanged for supplied
objects. Unknown counts remain null and are not inferred from spread/statistic.

## Explicit partial meanings

Retain every supplied source uncertainty field in the returned detached inputs.
Add only finite role-qualified strings to the existing qualifications list:

- `uncertainty_metadata_unresolved:<role>` for whole metadata null.
- `reported_uncertainty_magnitude_unknown:<role>` for SD/SEM/unspecified with
  null symmetric spread.
- `confidence_interval_endpoints_incomplete:<role>` for CI interval null or at
  least one null endpoint.
- `confidence_level_unknown:<role>` for CI confidence level null.

`<role>` is one of the existing four fixed ROLES, so the vocabulary is finite.
These describe missing meanings; they are not numeric grades, penalties,
source-absence claims or a new observation. Complete previously accepted inputs
receive none of these additional qualifications and retain their entire output.

## Numerical and identity behavior stays exact

The four raw parameters, two within-subject ratios, D, logD, V, sqrtV, S and B
formulas and all arithmetic helpers remain unchanged. Native measurements survive
when an uncertainty descriptor is partial. No model supplied still means null
model-dependent cells. Partial CI/spread/counts never supply a covariance,
normality, physical fit owner, independence or replication.

If an independently supplied, applicable model already satisfies the exact owner,
known covariance, normal log observation and positive-V requirements, those
requirements still govern S/B. An unavailable descriptive CI detail does not
override that distinct actual model; the calculator neither verifies scientific
model truth nor infers it from the partial metadata. Conversely, a complete CI
does not authorize S/B without that model.

Operand keys continue hashing the complete exact operand record. Existing fully
specified records therefore retain exact keys. New partial records get their
own distinct keys; model owners must be generated for those exact records. No
physical-fit IDs, reused-source safeguards or relationship checks change.

## Ownership and implementation boundary if accepted

Only these existing files would change:

1. gene_annotation_episode/literature_binding_interaction_calculations.py:
   docstring, `_uncertainty` validation, a small finite qualification helper and
   its invocation; optionally exported finite qualification-code constant.
2. tests/test_literature_binding_interaction_calculations.py: replace only the
   obsolete interval-null rejection expectation, add partials/contradictions/
   preserved numerical outputs/owner binding tests.

All other writes remain under this053 directory. No acquisition, parser,
storage, catalog, services, renderer, prompt, runtime, controller, W05 or source
packet edit is proposed. 052 may consume the reviewed corrected contract later;
053 will not implement its source adapter or native integration.

## Verification after release

- Compare full result dictionaries for every previously accepted synthetic
  fixture against the preserved048 implementation, including known/estimated/
  unknown model paths, censor arithmetic and numerical range cases.
- Verify each partial preserves its actual point/threshold, D and logD and
  detached metadata, with null model-dependent cells without a model.
- Check nullable uncertainty does not admit nonfinite/negative spread or spread
  on unreported parameters; reject malformed/contradictory CI/statistic/count
  inputs and preserve unknown versus reported-unavailable meaning.
- Verify actual explicit models still need exact estimate/physical owners and
  unchanged known-normal prerequisites; partial metadata never invents a model.
- Confirm arithmetic/model/identity helper ASTs remain exact and only the
  reviewed validator/qualification plumbing differs. Run the dedicated binding
  interaction tests; broaden only for a concrete affected consumer.
- Deliver complete patch, stable source snapshot/hashes, terminal evidence,
  baseline comparison receipt and additive correction handoff. Do not add old
  and new overlapping test totals.

## Inspection record

Read the complete active goal attachment, root AGENTS and W04 amendment; full
606-line048 calculator and466-line tests; complete048 proposal,002 refinements,
handoff and root parent receipt. Read the complete461-line kinetic calculator
as a code-only uncertainty-contract comparison. Latest039/040 human directions
were read before this proposal and are reread last below the implementation
decision in the accompanying authority receipt. No paper reset applies because
no paper or paper-specific packet was inspected. No production tests were run.
