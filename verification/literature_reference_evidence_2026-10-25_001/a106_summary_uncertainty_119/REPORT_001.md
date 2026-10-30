# A106 source summaries, uncertainty and selected graph reading119

This is an implementation/verification report, not a new goal, governing
amendment, scoring policy or runtime approval mechanism. No paper or retained
paper-specific packet was read by119; all examples and tests here are constructed.

## Implemented behavior

The existing `literature.perturbation.populate` operation now also reads the
closed retained `a106_source_measurements_v2` data format. Its seven original
roles remain W, K, R, A_reference, A_restored, B_pert and B_rest. Each role retains
the value/measurement identity plus summary kind, value and statistical scales,
reported spread kind/scale/numbers/coverage, variance status, actual repetition
count/unit/independence, optional raw-unit rows, optional source-image recipe,
separate digitization constraints and source-checked meaning quotations.

The source-only point calculator remains unchanged. The v2 extension populates
64 components: the original14 point meanings,42 per-role summary/spread/count/
descriptive-SD/mean-SE/mean-variance components, and8 contrast/covariance
components. These are one A106 sheet's numerical components, not64 graders,
extra evidence axes or independent experiments. The proposed source-index product
still requires its actual effect/restoration/comparability/isolation operands.
Missing amount or alternative-effect bounds keep that product unknown.

Raw technical readings are averaged within their declared unit. Equal-unit means
and sample SD remain useful with unknown independence. A justified independent
unit basis permits sample-variance/n; reported SD similarly supplies SD²/n.
Reported SEM supplies SEM² without dividing by n again. CI, detection-limit and
untyped-plus-minus numbers remain in their declared forms. Unsupported conversion
does not erase the point, spread, count or source meaning.

The closed variance-scope field distinguishes technical-mean precision within
the studied unit, biological-unit means, preparation means, other-unit means,
source-reported unresolved scope, mixed estimator scopes and unavailable or
inapplicable variance. Supported technical-mean SE is retained; it does not
establish biological replication or between-unit variation. Source-reported SEM
never manufactures an independence assertion.

Reported mean covariance, explicitly uncorrelated means, and paired raw-unit
identities have separate input meanings. Matching paired unit IDs produce the
sample covariance of the means. Complete known three-arm covariance matrices
must satisfy all principal PSD conditions. Reused K contributes once to
Cov(W−K,R−K)=Cov(W,R)−Cov(W,K)−Cov(K,R)+Var(K). Missing W or W=K does not erase
a separately valid R−K contrast or its variance.

With unknown covariance, marginal mean variances yield a conditional outer
enclosure of contrast variance. Exact Fraction/integer-isqrt arithmetic and
directed float projection avoid near-equal-variance cancellation. These are
conditional enclosures using retained marginal variance values/estimates, not
confidence intervals, true-variance coverage guarantees or experimental-validity
probabilities. Variance status remains known/estimated/unknown explicitly.

## Reader and source custody

The new image reader supports explicit fill-edge/cap-centre selections with
linear or log10 display calibration. It reuses the original validated image
decoder/threshold-row machinery and leaves the old bar reader unchanged. It
reads actually received image bytes through the same scope/page source custody
checks before decoding, saves their exact artifact/digest and complete recipe,
and keeps source quotation meanings separate from pixel arithmetic.

Logarithmic display does not determine the statistical summary scale. Mean and
error-cap ordinates are retained separately. Both selected caps survive: compatible
symmetric readings have an explicitly conditional digitization estimate; asymmetric
readings retain their two caps/ranges without a selected symmetric spread. CI
endpoints are transformed to their declared scale without requiring them to
contain the point. Missing ink, clipping, unknown scale and numerical-range
failures remain reader/interpretation limitations, not claims of paper omission.

Scientific numbers still come from the actually received retained data source;
v2 graph recipes additionally read the actual source image. This does not
establish autonomous creation of those records from arbitrary primary prose,
tables or figures. Native source-operand selection/retained-record construction
remains explicit unfinished work. No universal graph classifier is supplied.

## Typed delivery and compatibility

`literature_perturbation_summary_cells` is a separate closed55-field return view
over the same original A106 operation/sheet store. Requested components use
`requested_perturbation_summary_components`. Its constructor performs no DDL;
only actual incoming admission creates its receipt table. Original point-view
possession cannot upgrade to the new view or unrequested components. Runtime
receipt validation authenticates the original successful form and attempt.

The old v1 dataset, point calculator,14-cell return schema and original receipts
remain exact. New v2 source records use their own version and projection. Replay
copies the original saved results without primary-source reads, arithmetic,
model calls or migration of historical outputs. No new selected operation,
episode, private loop, controller observation, credit rule or computational
biology suite was added.

Shared integration preserves116 scientific-display and117 reported-domain work.
It adds only the new assignment/fact/route/version guards and implementation
fingerprints. The user's existing basic-statistics correction also required one
explicitly authorized parent-TASK sentence repair; the exact before/after is in
PARENT_TASK_CORRECTION_001.json. Other parent TASK text is preserved. The new
source-summary paragraph is recurring investigation guidance, not the sheet.

## Verification

Final actual command in immutable `pin_002`: **285 passed,2 explicitly
deselected original-paper cases in67.70s**, exit0. This comprises47 new pure
checks,5 new integration checks,225 original input/calculator checks and8
constructed legacy integration checks. All2027 pinned files remained unchanged;
all12 changed/added current files match the tested pin.666 runtime modules were
equal in main-before, main-after and copied snapshots.

The ordinary shared workflow test executes one selected summary operation,
admits one actual child form and reaches the parent's next decision. It records
three ordinary observations for the three actual completed actions, with zero
scientific credit and no fabricated observation/assessment. The first fresh
mode=ro reconstruction uses the original saved descriptor and actual runtime
receipt; source bytes, parsers, calculators, model connection and mutations are
disabled. Its exact subset returns with zero DB changes; extra known sheet
components remain unavailable to the receiver. This is scripted engineering
evidence, not actual-model scientific use.

Original failures and narrower earlier passes remain recorded in FINAL_RESULTS_001.json
and their available raw logs/XML. In particular, the parent found an unsound
decimal cancellation bound after an earlier36-pass run. The exact rational repair
is covered by the real source-reader large-count example and independent600-digit
containment checks, including zero, subnormal and overflow behavior. No sample
count was capped. The later fresh-readonly fixture failure was repaired only in
the NEW test's journal binding, preserving its failed log/XML.

The API/schema, reported-uncertainty and paired-raw examples, and constructed log
image/recipe are retained alongside the final diff and manifests. Whole-index
nonlinear sampling uncertainty, direct native primary-source extraction and new
actual-model scientific use remain unfinished. A106 and the full fixed literature
goal are not claimed complete.
