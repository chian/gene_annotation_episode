# Pure controlled-response stage handoff

Implemented only two new files:

- gene_annotation_episode/literature_controlled_response_calculations.py
- tests/test_literature_controlled_response_calculations.py

This is a numerical experimental component within A105, one of the ten axis
sheets. It is neither a new axis nor completion of A105. Several appropriate
experimental components can apply to different claims/experiments in one paper;
paper routing is deferred. No scientific source, graph, model service, episode,
credit, native operation or prompt was launched or changed.

## Exact interface

The pure entry points are validate_controlled_response_inputs(inputs), returning
a detached validated input copy, and populate_controlled_response(inputs),
returning exactly version, primitive_order, inputs, cells. They do not consume
documents or authenticate source bytes. Reader/custody and source interpretation
must precede them in the future selected operation; model-selected scientific
numbers must not become its direct arguments.

Input version is controlled_response_inputs_v1; output version is
controlled_response_sheet_v1. API_006.json records the exact keys, enums, cell
codes and numerical meanings from this implementation. The complete frozen
synthetic input is INPUT_CONTRACT_EXAMPLE_003.json. CONTRACT_FREEZE_003.md,
BOUND_STATE_EXAMPLES_003.json and CONTRACT_CLARIFICATIONS_004.md record the
explicit root-reviewed clarifications before implementation/use.

The ordered four roles are protein_condition1, empty_condition1,
protein_condition0, empty_condition0. Four raw numerical response cells, two
within-condition controlled differences, the four-arm difference, variance,
standard uncertainty, precision and optional signed source profile/index are
twelve dependent representations of the same selected experimental inputs,
not twelve graders or independent observations.

The effect is e=x0-x1-x2+x3. Variance is l C l-transpose, l=[1,-1,-1,1].
Actual endpoint, unit dimensions, biological normalization, local condition
application and cross-condition protein/construct correspondence gate only the
derived cells that need them. The deliberate condition change is the signal.
Other cochanges remain finite qualifications and do not become quality weights.
This describes the actual controlled protocol contrast, conditional on those
interpretations, and does not prove protein purity, isolated causal action,
transport species, proton coupling or physiological function.

## Numerical behavior and checks

The synthetic root example stipulates the same positive paired-reference protein
mass for all four arms, including empty controls. It does not divide an empty
preparation by nonexistent assayed protein. Native [12,2,5,1] nmol/min/mg gives
e=6 and V=1.7 (nmol/min/mg)^2; canonical e=.006 umol/min/mg and V=1.7e-6
(umol/min/mg)^2. S/B are null when no source model is selected.

All arithmetic inputs are already parsed finite int/float JSON numbers; their
stable decimal spelling is used for exact rational linear/covariance operations.
Actual unit multipliers convert each response and both covariance coordinates
once. Symmetry and all fifteen principal minors check PSD without jitter or
scale tolerance, including singular matrices. Declared physical aliases require
consistent shared values/context and covariance rows in canonical units. Equal
numbers or source names cannot supply identity or independence.

Local pair0 failure never erases an applicable pair1. Different biological
denominators cannot become common because unit spelling matches. A known shared
control keeps its actual measured condition and can be applied elsewhere only
under the explicitly interpreted shared-reference assumption. Genuine aliases
can cancel jointly; unknown reuse alone cannot supply an alias. Independent known
owner identity with exact consistent data and applicable shared controls can
establish cancellation while retaining the unknown-reuse qualification. Missing
roles never get filled from that algebra.

Signed noisy values and zero remain valid observations. Printed limits remain
limits, with exact coefficient signs/strictness and joint alias constraints.
Graph reading intervals are distinct from sampling CI/spread, even though no
graph reader is built here. Each final numeric dependency has its own range
check. A representable bound survives another endpoint's range loss with partial
status and per-side bound_state; loss is not infinity or rounded zero. Exact
internal quantities can preserve a finite uncertainty/precision/profile when a
different displayed numerical component is outside float range.

Known or estimated supplied covariance can give V. Only a declared known-normal
source-mean model, known positive V, exact uncensored/nonapproximate/nongraph
operands allow S=e*abs(e)/(2V), B=tanh(S/2). These are source-level proposed
components, not probabilities or annotation credit. No empirical raw spread,
count, graph interval or duplicate record is converted to covariance.

Malformed direct inputs and invalid direct covariance raise the existing
ExperimentalContractError with a field/code. A source reader does not yet exist:
it must retain an authentic invalid covariance artifact/finite diagnosis and
pass explicitly unavailable covariance to preserve usable magnitude. The pure
calculator's direct error is not claimed as that future source-partial behavior.

## Verification actually run

The final targeted command was:

    .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_literature_controlled_response_calculations.py tests/test_literature_rate_calculations.py tests/test_literature_transport_calculations.py

It exited 0: 209 passed in 0.95s. This includes 93 dedicated new cases plus the
existing rate/transport regression cases. Those cases are wholly synthetic.
TEST_RUN_005.json records the observed command/result summary; it is not a new
test execution or a fabricated full stdout log.

The root found one real initial implementation error: internally valid pairs with
different dimensions could produce e with no unit. The baseline module and
dedicated failing regression are preserved in review_baseline_004 and
CROSS_DIMENSION_BEFORE_004.*. The correction blocks e and every dependent
variance/model cell while retaining both valid local pairs and raw values. The
final calculator hash matches the root's subsequent independent dimensional and
256 unit-representation invariance audit; that root-owned audit is separate
evidence, not additional experiments performed by this worker.

The actual standalone reproduction command was:

    .venv/bin/python -B verification/literature_reference_evidence_2026-10-25_001/a105_controlled_response_design_056/pure_stage_003/reproduce_calculator_005.py

It exited 0 and emitted 14 complete invented numerical fixtures plus their
summary table: NUMERICAL_FIXTURES_005.json and NUMERICAL_FIXTURES_005.md. It did
not measure a plot or invoke a scientific model. Artifacts are written only once;
the existing fixture files are never overwritten.

Current complete read paths before implementation were experimental contracts,
rate calculations and transport calculations. Only the unit registry and error
type are imported. Full existing transport/rate test files were also read.
An initially truncated aggregate display of transport tests was repaired by
complete bounded reads; no truncated read is claimed complete. All four original
dependency snapshots/hashes in BEFORE_003.json still match at handoff. Current
new files, before/after hashes, full snapshots and the new-file/review-delta
patches are recorded in DELIVERY_006.json. No existing production/test/shared
file was edited by this stage.

## Still unfinished

No targeted source reader, acquired covariance-model reader, graph rate-unit
extension, source authorization/custody, native selected-operation binding,
typed parent/child delivery, exact admitted subsets/masking, C4 proof or saved
read-only reconstruction is implemented by this stage. No configured-model
scientific extraction or primary-source example was run. The root owns primary
source conversion; this worker read no paper/retained scientific packet. W05
aggregation, A101 and routing remain separate. The full workload/goal remains
unfinished; this handoff completes only the bounded pure-calculator release.
