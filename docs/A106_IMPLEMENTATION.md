# A106 intervention investigation

The required outcome is an autonomous sequence-only investigation that discovers
intervention experiments, recovers or computes their measurements, preserves
design and provenance, assesses the evidence, and delivers the resulting A106
experimental subscore to its parent. Acquisition, analysis completion, saved
worksheets and parent receipt of individual measurements are intermediate steps.

## Score operand map (2026-11-03)

The implemented `populate_source_restoration` calculation in
`literature_perturbation_calculations.py` has the following dependencies. Its
point and summary readers are `read_perturbation_inputs` and
`read_summary_measurements`. They currently consume the finite retained
`a106_source_measurements_v1/v2` formats; ordinary published tables and native
analysis outputs do not automatically become that format.

| Component | Required evidence | Implemented calculation / limitation |
| --- | --- | --- |
| Reference W, intervention K, restoration R | Distinct actual measurements; same endpoint, unit, condition and timing; calibrated nonnegative ratio scale | Retained point or summary means; an absent restoration arm remains missing |
| Perturbation difference | W, K and their measurement identities | W − K |
| Symmetric effect | W, K; nonzero sum | (W − K)/(W + K) |
| Restoration agreement | W, K, R; explicit deletion/restoration or selective perturbation/restoration design; nonzero perturbation difference | clip(1 − abs(R − W)/abs(W − K), 0, 1) |
| Amount comparability | Measured nuisance amounts A_reference and A_restored outside the intended intervention | min(A_reference, A_restored)/max(A_reference, A_restored); intended depletion cannot supply this nuisance comparison |
| Perturbation isolation | Source-supported bound B_pert in endpoint units on alternative contributions | clip(1 − B_pert/abs(W − K), 0, 1) |
| Restoration isolation | Source-supported bound B_rest in endpoint units on alternative contributions | clip(1 − B_rest/abs(R − K), 0, 1) |
| Effect isolation | Both isolation components | Their minimum |
| Source restoration index | Supported assertion orientation and all above components | orientation × symmetric effect × restoration agreement × amount comparability × effect isolation |
| Source-index uncertainty | Joint uncertainty across its inputs | Explicitly unimplemented; summary contrasts retain their own supported uncertainty and covariance |
| Experiment assessment | Source-backed assay identity, question, conclusion, limitations, latest predecessor for revisions | `intervention_response`; one current assessment per experiment/question; questions are not independent experiments |
| Final A106 experimental subscore | Supplied subject, assertion, explicit alternative, biological scope, current experiment assessments, supported predictions and uncertainty | `literature.a106.finalize` retains one signed log evidence ratio per original experiment; several ratios sum only under source-supported conditional independence |

The older research axis catalog contains a proposed −log10(p/q) route for a
claim-matched native test. It explicitly adopts no cross-route summation. Its
ordinal assurance routes have been withdrawn by `evidence_axis_scoring.py`.
Neither that research proposal nor A105's explicitly user-defined reducers
establishes a final A106 rule. A source restoration index is conditional evidence
about the experimental subject, not target correspondence or a function
probability. A log fold change, p/q value or screen fitness score cannot be
substituted for W, K or R, and nonsignificance cannot establish no contribution.

User decision (2026-11-03): reuse the existing A105 signed log evidence-ratio
calculation for supported predictions, variance and comparison models, retaining
restoration components as diagnostics. This determines the experiment-level
quantity without converting a screen statistic into a restoration endpoint.
Final aggregation preserves experiment and shared-measurement identities,
comparison scope, conflicts and unresolved inputs. Full autonomous numerical
demonstration remains required.

One prediction-input decision remains pending: may fixed predictions be derived
from an explicit, source-supported model independently of the observed effect,
or must the prediction numbers themselves be externally reported? The current
reader accepts reported source numbers and supported received reader components;
it has not been extended to accept model-derived constants. A measured mean and
its uncertainty do not supply the two fixed predictions. Any permitted derivation
would need to retain its assumptions and independence from the result being
scored. The observed effect cannot be reused as its own assertion prediction.
This decision is separate from the user's deferral of BV-BRC execution.

## Implemented path

`LiteratureEpisodes(..., rate_population=True, a106_intervention=True)` exposes
the intervention investigation, Entrez/GEO/SRA acquisition, existing numerical
readers, `literature.intervention_grading.populate` and
`literature.a106.finalize`. When an AppService execution binding is configured,
the main literature role can commission its existing launch and results roles.
This declaration makes no service-availability claim.
The local `literature.intervention_analysis.contract` helper is exposed only
for configured TnSeq/RNASeq adapters. It constructs their exact native result
schema from explicit document and field selections, rejects unbound resources,
adapters and documents, and performs no service request. The existing results
selector still owns acquisition requirements and the parent requests
`bvbrc_application_outcomes` through its typed report.

The dedicated `bvbrc_tnseq` and `bvbrc_rnaseq` version-1 adapters preserve the
original task, submitted parameters, reference/contrast information, input
bindings, retained table bytes and physical row locations. TRANSIT resampling
outputs retain insertion means, signed effects and native p/q values. DESeq2
outputs retain signed log2 effects and reported standard errors; estimate
variance is explicitly derived as `lfcSE²`. Missing, invalid, out-of-range and
underflowing numbers remain unavailable. A p/q value supplies no variance.
Count matrices, sample tables and quality reports can also be retained without
inventing a statistical interpretation.

The source reader accepts exact published numerical witnesses, existing
received reader components, directly retained native tables, or exact
`bvbrc_application_outcomes` fields delivered through the existing receipt
owner. The last route preserves the complete original task context in the
assessment's saved input rows and cannot widen a received field into a private
child sheet. Raw-table and AppService views of the same bytes and row share an
observed-measurement key. Experimental-design witnesses and sample bindings
retain file associations, arms, biological/technical units, pairing, batch and
time. A file association requires a literal source witness.

The existing measurement-comparison reader also supplies A106 operands from
published specific-activity tables with shared header units. Native and converted
arm estimates, protocol differences and protocol ratios retain their measurement
identities and native units. Difference variance must accompany the protocol
difference from the same saved sheet; estimated covariance cannot become known
variance. Standardized discrepancies, weights, common-mean combinations and
conditional scenarios cannot supply an intervention effect. This connection
does not infer covariance from SD and a repetition count or supply missing
prediction, experimental-design or subject-correspondence support.

The A106 grader reuses A105's numerical calculation, including supported normal,
estimated-normal, Student-t and censored-observation paths. It adds intervention,
subject-correspondence, contrast and independent-prediction criteria. For a
known-normal point estimate the score is
`((y − alternative_prediction)² − (y − assertion_prediction)²)/(2 × variance)`.
All model conditions remain attached to the saved score. A normal approximation
using estimated variance remains explicitly conditional.

Finalization binds this result to subject, assertion, alternative and scope.
It selects one current assessment per original experiment. Repeated experiment
references are rejected; shared observed-measurement keys and unsupported
between-experiment independence leave a multi-experiment score unresolved.
Shared fixed predictions are kept separate from shared observations. Negative
scores retain their sign. Missing experiment scores keep the final value null;
an available subtotal is separately labelled. An empty roster is unavailable,
not zero. “Complete” refers to the selected roster, not exhaustive discovery.
An existing unavailable assessment should still be selected so its design,
measurement identities and unresolved criteria reach the final result. A null
sheet reference is reserved for a missing applicable assessment. The original
prompt conflated these cases; its guidance and field description were corrected
after the BacA evaluation exposed the loss of the typed assessment link.
Final results and assessments retain explicit revision chains. Cold replay and
typed parent delivery copy authenticated saved values without rerunning science.

## Verification status

The focused final-score run passed 22 checks, including a scripted full runtime
that delivered a numerical A106 final score to its parent. Subsequent focused
checks exercised the received-analysis selector and sample/file witnesses; a
test expected the wrong error class for a rejected quotation and was corrected.
The final focused regression passed all 123 checks across the A106 readers,
grading, final-score storage/runtime, shared A105 grading and application returns
(`runs/a106_integration_2026-11-03/final-regression.xml`).
These are synthetic engineering checks, not the required autonomous biological
demonstration. The controlled AppService integration additionally exercises
preparation, submission, manifest acquisition, partial publication and typed
receipts; it exposed adapter validation exports and duplicate missing-requirement
entries, which were repaired. Both controlled routes then passed (2 tests in
277.51 seconds): the RNASeq fixture reached the final sheet with its engineered
log evidence ratio of 8, and the TnSeq fixture remained unavailable without an
estimate variance. These fixtures make no biological or live-service claim.
After adding the configured-adapter contract helper, both controlled routes
passed again alongside two helper checks (4 tests, 319.33 seconds), and the
scripted final-score parent-delivery check passed (1 test, 44.71 seconds).
An additional runtime check passed after improving rejected-support feedback
(1 test, 70.42 seconds). It verifies that the offending interpretation field and
record are identified, a corrected request is accepted, and the final score is
delivered. This remains a controlled engineering test.
The published-table connection passed nine focused checks
(`runs/a106_integration_2026-11-03/comparison-bridge-04.xml`), covering shared
header units, selected-cell custody, known versus estimated covariance, rejection
of incompatible quantities, and an unavailable final score retaining its
assessment through typed parent delivery and replay without recalculation.
The fixtures are explicitly synthetic.
The subsequent regression passed all 76 checks across intervention grading,
assessment storage, final-score runtime delivery and the shared A105 calculator
(`runs/a106_integration_2026-11-03/comparison-regression.xml`).
The next autonomous YeaG trace exposed rejection of a valid Unicode thin space
between a printed number and unit. The scalar reader now checks decoded UTF-8
whitespace, while still rejecting intervening content and invalid byte sequences.
The A106 schema also excludes `not_applicable`, which its required-criterion
grader never supported, and explains relative character versus absolute byte
offsets. The focused spacing/grading run passed 23 checks, followed by a passing
scripted runtime recovery and final parent-delivery check
(`unit-spacing.xml` and `unit-spacing-runtime.xml` beneath the same run directory).
Subsequent trace failures distinguished two finalization repairs: keep a supplied
assessment sheet while clearing `missing_reason`, and retain the predecessor's
exact question binding when revising a result. These errors now return the
relevant field or differing question fields instead of a misleading generic
error. Five focused finalization/custody checks passed, including correction
without losing the unavailable assessment or rewriting its predecessor
(`final-feedback.xml`).

The broader integration run had 95 passes and one older prompt-delivery mock
failure (`EmptyServices` lacks the provider metadata used by the existing rate
meaning projection). Earlier A105 input tests still omit required experiment
identities; representative failures were reproduced with pre-change readers.
Those failures are not reported as passing A106 verification.

The user deferred BV-BRC access on 2026-11-03 while repairing the service. No
further authentication probes or live jobs are being attempted. Packaged
definitions, controlled transport and downloaded data do not establish live
service success.

`tests/live_a106_workflow.py` runs the repository's default model and controller
from an anonymous protein sequence, with no external cutoff. It freezes both
application packages under its run directory. Evaluator expectations in
`tests/fixtures/a106_evaluation/case-01-evaluator.json` are separate and are never
loaded by the driver. The first attempted launch omitted `method_loop` and
stopped before a model call. The corrected case-01 launch is in
`runs/a106_sequence_case01_2026-11-03_02/`; it has completed sequence identity,
citation lookup, publication search and acquisition, and is reading the discovered
source. It remains under observation and has not established final-score delivery.
It has since acquired and read supplementary material, created anchored experiment
and hypothesis records, and attempted intervention grading. Repeated requests used
document references where anchored interpretation references are required and
were rejected. It subsequently finalized an unavailable score, explicitly noting
the absent grading sheet as well as unresolved variance and predictions. This
does not demonstrate the complete reader-to-grader path. The current prompt,
schema and error feedback explain the reference requirement; existing evaluations
keep their frozen source.
The fresh case-01 evaluation in `runs/a106_sequence_case01_2026-11-03_03/`
includes the anchored-support guidance and actionable error details. It is
running independently; the original evaluation has not been stopped or changed.
It encountered the Unicode-space bug, recovered by selecting the printed
percentage contrast, and created an accepted intervention assessment with an
unavailable score. The separate `runs/a106_sequence_case01_2026-11-03_04/`
evaluation includes the whitespace and criterion-schema corrections. All earlier
evaluations retain their frozen code and remain under observation.

The anonymous evaluation inputs and separate expectations are retained in
`tests/fixtures/a106_evaluation/`. The driver never loads evaluator files.

| Case | Evaluation purpose | Current evidence |
| --- | --- | --- |
| 01: 644-aa YeaG | Intervention evidence with unresolved quantitative inputs | Original run active; unavailable final sheet created after rejected grading requests; parent delivery still being checked |
| 02: 273-aa UppP/BacA | Quantitative intervention/complementation candidate | Literature child yielded; parent receipt of two unavailable final results confirmed. Both omit typed assessment selections on the older frozen code; overall workflow remains active |
| 03: 859-aa NA1000 ClpB | Deposited intervention RNASeq | Input and evaluator prepared using GSE312471 metadata; service run deferred |
| 04: 257-aa B. subtilis YlmH/rqcP2 | Deposited TnSeq and genetic-background comparison | Four single-end archives identified; bounded read prefixes and public pipeline code inspected; full mapping compatibility and service run remain unverified |

The BacA evaluation has now delivered two unavailable final results to its
annotation parent, covering the 2015 complementation experiment alone and a
broader scope including the 2022 compound intervention. Both preserve null scores
and state the absent effect, variance, independent predictions and observation
model; the broader scope also retains unresolved between-experiment dependence.
Neither is a numerical positive. Both final results have empty
`selected_components`, despite saved intervention assessments, because the older
guidance led the episode to use null sheet selections. Thus parent delivery is
observed, but the complete assessment-to-final evidence connection remains to be
demonstrated autonomously with the corrected guidance. The child yielded through
the default controller; no external cutoff was imposed, and the overall workflow
remains under observation.

`tests/audit_a106_workflow.py` inventories actions, failures, numerical publications,
returned forms and recorded parent receipts through a read-only SQLite connection.
Its result summaries retain each scope, unavailable reason and selected assessment
count, distinguishing a returned form from confirmed parent receipt. Its optional
snapshot checks verified all four evaluations' frozen files and anonymous-input hashes.
The inventory does not infer process liveness or grade scientific adequacy.
The live driver also accepts an explicit `--execution-config` for the existing
BV-BRC execution roles when service evaluation resumes. Its default still leaves
BV-BRC execution disabled. Configuration construction passed a local test with
network access forbidden; it is not a service demonstration.

The TnSeq evaluator now records four PRJDB17234 archive runs and their sample
labels, lengths, sizes and advertised checksums. Inspection of the first 65,536
compressed bytes of each file yielded 14,312 complete 15-base reads in total;
this does not verify the complete files or establish biological independence.
The reviewed [TPP implementation](https://github.com/mad-lab/transit/blob/50e23d6bec2605a24835fbd67f33691e330f3361/src/pytpp/tpp_tools.py)
accepts 15-base MmeI reads, and its [documentation](https://transit.readthedocs.io/en/latest/tpp.html)
describes an empty primer for pretrimmed reads. Consequently `mme1` with an
explicit empty primer is a candidate, pending full trimming/orientation and
reference-mapping checks. The t1/t2 labels and collection dates alone do not
prove independent biological replication. This evaluator information is never
passed into anonymous episodes.

The native reader headers were also checked against pinned public source:
[TRANSIT resampling](https://github.com/mad-lab/transit/blob/50e23d6bec2605a24835fbd67f33691e330f3361/src/pytransit/analysis/resampling.py)
and [BV-BRC DESeq2 output](https://github.com/BV-BRC/bvbrc_rnaseq/blob/e7127fc34a16969c165dbda06bf4fb186cd8feb9/scripts/run_deseq2_bvbrc.R).
Both match the implemented tab-separated column mappings. That source inspection
establishes format compatibility with the reviewed code, not the currently
deployed service version or successful execution.

## Implementation and verification obligations

1. Describe A106's investigation responsibility and available operations in its
   prompt, including deciding whether published measurements suffice or deposited
   data would resolve an uncertainty.
2. Preserve experimental identity, actual molecule/strain/construct, supplied
   sequence correspondence, intervention, reference/restoration arms, endpoint,
   units/scales, time, biological/technical units, shared controls and files.
3. Add dedicated TnSeq and RNASeq result adapters to existing AppService
   execution, with native values, statistical meanings, quality information,
   selected parameters/reference versions and typed parent delivery. Check live
   service availability separately from packaged application definitions.
4. Connect acquisition, analysis readers/sheets and intervention assessment
   without counting paper/dataset representations or revisions twice.
5. Implement the agreed final-score connection, including useful partials,
   conflicts, missing evidence and authentic parent return.
6. Run full autonomous sequence-only episodes for a quantitative microbial
   intervention/restoration case, a useful TnSeq data-analysis case, an
   intervention RNASeq case and an insufficient/conflicting case. Keep evaluator
   expectations out of episode inputs. Let runs reach their own terminal state;
   do not impose a cutoff or represent a stopped run as complete.

Completion requires an observed positive numerical subscore delivered to the
parent, an observed dataset-analysis route, demonstrated duplicate handling and
an appropriately unresolved insufficient-evidence result. Current status:
implementation and engineering verification have advanced through final-score
delivery. Autonomous unavailable-score parent delivery is observed, with the
assessment-link limitation above. A supported numerical positive, dataset-analysis
route, complete duplicate handling and unresolved result retaining its applicable
assessment selections remain to be demonstrated.
Disposable execution evidence belongs beneath `runs/a106_integration_2026-11-03/`.
