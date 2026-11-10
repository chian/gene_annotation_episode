# A106 intervention investigation

The required outcome is an autonomous sequence-only investigation that discovers
intervention experiments, recovers or computes their measurements, preserves
design and provenance, assesses the evidence, and delivers the resulting A106
experimental subscore to its parent. Acquisition, analysis completion, saved
worksheets and parent receipt of individual measurements are intermediate steps.

The long case-01 investigation was stopped at the user's request. The subsequent
requested continuation review selected the original estimator with fixed cost
0.01 and alpha 0.05, accepting earlier partial returns so a parent can organize
another search. Nine retained episode traces were replayed and eight regression
checks passed. See [A106_YIELD_REPLAY.md](A106_YIELD_REPLAY.md) for the selected
profile, verification, reproduction command and estimator-version scope. This
completes that tuning request; it does not establish the broader scientific goal.

## Score operand map (2026-11-03)

The implemented `populate_source_restoration` calculation in
`literature_perturbation_calculations.py` has the following dependencies. Its
point and summary readers are `read_perturbation_inputs` and
`read_summary_measurements`. They consume the finite retained
`a106_source_measurements_v1/v2` formats. The new optional `source_measurements`
selection reads reported arm summaries directly from source spans and feeds the
same summary calculator; its execution checks are pending below. Native analysis
outputs retain their separate intervention-reader route and native scales.

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

The unresolved input question is where to get the numbers expected under each
competing explanation. For example, suppose deleting a gene leaves 20% survival
(a hypothetical example, not evaluation evidence). That supplies an observation.
The calculation also needs the survival expected under each explanation. A paper
saying that the gene affects survival does not supply those percentages.

The current reader accepts `source_number` and `source_table_number` selections
from retained sources, or `received_component` selections from supported existing
readers. These routes can supply published predicted values. The native and
application analysis selectors supply the measured effect and its variance;
they do not supply predictions. No general biological prediction calculator is
implemented, and no particular new calculation has been specified for addition.
The user requested clarification of the earlier vague proposal; there is no
pending permission question. First examine whether the selected experiment can
use predictions already available through the existing readers.

The `prediction_model` field has a different purpose: it selects the distribution
used to compare the measured result with each expected value. The implemented
choices are normal with known variance, normal with estimated variance, and
Student-t with an explicit variance interpretation and degrees of freedom.
Selecting one does not calculate biological predictions. The current prompt now
states this distinction; the frozen live run does not contain that clarification.

A proposal for an additional calculation must identify its formula and what
justifies its input numbers, such as measurements from a separate experiment.
It must also state its assumptions, such as applying measurements from one strain
to another. Seeing 20% survival and then choosing 20% as the prediction because of
that observation
cannot provide independent evidence through their agreement. Missing predictions
leave this ratio unavailable; the measured effect and experimental interpretation
remain usable. This issue is separate from the user's deferral of BV-BRC execution.
The current investigation prompt now explains those operands directly and
distinguishes prediction independence from publication identity: one paper can
report both an independently calculated prediction and the experiment testing
it. It also requires the competing claims to concern the tested molecule's
contribution. This is instruction clarification, not a new prediction calculator
or evidence that the frozen live run has used the revised instructions.

The retained Gawand source offers a concrete comparison to examine using existing
readers: Table 2 reports RELATCH growth predictions of 0.18 per hour for the
single `pgi` deletion and 0.35 per hour for wild type. Table 1 reports the deletion
measurement as 0.159 ± 0.001 per hour, with the error identified as SD and three
biological replicates documented in the methods. Using 0.35 as an alternative
for the deletion would add an explicit assumption that deleting `pgi` leaves
growth at the model's wild-type value. It is not a second published prediction
for that deletion, and the measurement is a mutant endpoint rather than a
WT-minus-mutant contrast. This possible comparison avoids borrowing the unknown
MOMA baseline, but still requires assessment of experimental attribution,
reference-condition transfer, prediction provenance and the measurement-error
model. The values are verified against the retained original XML; no such
comparison has been adopted, calculated, supplied to the episode or counted as a
positive evaluation. The separate candidate review records the proposed use and
its limits.

## Implemented path

`LiteratureEpisodes(..., rate_population=True, a106_intervention=True)` exposes
the intervention investigation, Entrez/GEO/SRA acquisition, existing numerical
readers, `literature.intervention_grading.populate` and
`literature.a106.finalize`. When an AppService execution binding is configured,
the main literature role can commission its existing launch and results roles.
This declaration makes no service-availability claim.
The assembled application and its saved case policy now accept an explicit
`literature_configuration`, using the same `LiteratureEpisodes` constructor
options. For an A106 investigation, supply:

```python
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE

services["literature_configuration"] = {
    "rate_population": True,
    "a106_intervention": True,
    "reference_parent_sources": [],
    "contract_information_profile": CONTRACT_INFORMATION_PROFILE,
}
```

The empty source list starts discovery from the supplied sequence. The policy
preserves this configuration for reconstruction, and the parent context labels
the investigation A106. The contract-information profile uses the repository's
default decision-exchange protocol. With TnSeq/RNASeq adapters explicitly bound
in `execution_resources`, the A106 literature episode can commission the existing
launch and results roles. Setup performs no authentication or service request.
Assembly verification passed six reconstruction/configuration/score-delivery
checks (`runs/a106_assembled_services_20261104_01/stdout.log`), all 80 existing
service-setup and case-policy checks
(`runs/a106_assembled_regression_20261104_01/stdout.log`), and the full parent
commissioning check with the published A106 instructions and configured native
adapters (`runs/a106_assembled_root_20261104_04/stdout.log`). Earlier versions of
the new commissioning test had fixture errors; the final check exercises the
ordinary pending-decision protocol and host-populated result fields. Network
access was forbidden in these new engineering checks.

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

Source review found that native-table selections checked the operand's role and
units but did not bind its column meaning to `quantity_kind`. For example, a
DESeq2 `baseMean` could be labelled an endpoint difference. The reader now
requires arm/base means to remain `native_endpoint`, TRANSIT's signed mean
difference to remain `endpoint_difference`, and log2 fold changes to remain
`log2_fold_change`. Native DESeq2 variance belongs to the matching log2 contrast.
Both retained-table and received-application paths use this check and expose the
mapping in their argument descriptions. This is a correction to interpreting
existing columns, not a new calculation or service route. Eighteen focused cases
in `tests/test_intervention_native_quantity_kind.py` are prepared but unrun while
`runs/a106_sequence_case01_20261105_02` occupies this window. The frozen live run
does not contain this correction; saved worksheets are not rewritten.
Four of these cases exercise the existing row-association check with two valid
DESeq2 rows: each row's effect/variance pair is readable, but the first row's
effect cannot use the second row's variance, including when their gene names
match. Both retained-file and received-application routes are covered by the
prepared checks. No new variance calculation or association rule was added.

The generic received-component path had another source-reviewed meaning gap:
it accepted the existing binding/kinetic model likelihood scores and signed
indices as if they were fresh experimental operands. A106 now rejects the
`source_profile_log_ratio`/`source_signed_index` components from the binding,
kinetic and relative-signal reader namespaces, and the corresponding
`signed_profile_log_ratio`/`signed_index` binding-interaction components, for
every input role. Their underlying measurements and uncertainty remain readable.
The follow-up review found the same inference components in rate, corrected
assay, compiled-assay v1/v2, native binding/kinetic and controlled-response
readers. The rejection now checks the scientific component name in the actual
validated returned row. This matters for controlled responses, whose selected
key can be `final:source_profile_log_ratio` rather than the component name.
The existing numerical definitions and underlying measurement access are
unchanged. This remains a check for defined inference outputs, not a complete
quantity-kind mapping for every shared A105 reader.
Thirty-two regression cases in `tests/test_intervention_received_score_operands.py`
are prepared: the original eight binding-model cases plus sixteen saved
rate/assay cases and eight scoped controlled-response cases. They check rejection
as effect, variance or either prediction, and preserve reading the same sheet's
underlying measurements. The controlled-response test uses a 32,864-byte reusable
source fixture under `tests/fixtures/a106_source_components/`, retaining the
original engineered source bytes rather than depending on historical execution
directories. These cases have not executed while the full workflow remains
active; its frozen source and saved sheets are unchanged.

The existing measurement-comparison reader also supplies A106 operands from
published specific-activity tables with shared header units. Native and converted
arm estimates, protocol differences and protocol ratios retain their measurement
identities and native units. Difference variance must accompany the protocol
difference from the same saved sheet; estimated covariance cannot become known
variance. Standardized discrepancies, weights, common-mean combinations and
conditional scenarios cannot supply an intervention effect. This connection
does not infer covariance from SD and a repetition count or supply missing
prediction, experimental-design or subject-correspondence support.

Original perturbation point and summary sheets can now supply the new
`literature_perturbation_operand_cells` view, selected with
`requested_perturbation_operand_components`. It carries the existing W, K and R
endpoints, W-K and R-K differences, and matching mean variances when available.
It preserves the original measurement identities, units, covariance interpretation
and sampling qualifications without recalculating the measurements. An additional
identity based on the original artifact and measurement ID identifies repeated
acquisition of identical data. Variance must match the selected effect and sheet;
an estimated variance cannot be declared known. Restoration indices, SD/SEM and
covariance bounds cannot be substituted for effect variance. Historical point
and summary return formats are unchanged, and receiving those older views does
not automatically provide the new view. This connection supplies measurements,
not missing predictions or a demonstrated autonomous numerical result.

The 2026-11-04 measurement connection passed 11 focused checks, including original
point sheets without variance, summary covariance, duplicate acquisition, exact
return validation, received-component access and read-only replay
(`runs/a106_perturbation_bridge_20261104_03/stdout.log`). Another 104 checks passed
for the existing point/summary readers, intervention storage, comparison inputs,
A106 finalization, episode binding and task selection
(`runs/a106_perturbation_bridge_regression_20261104_01/stdout.log`). These are
engineering checks using constructed data, not autonomous scientific evaluations.

The paper/dataset identity review confirms two separate protections in the
current code: assessment revisions retain a stable experiment reference, and
identical native-table rows share measurement identities across acquisitions
and application-result views. Different representations do not automatically
establish their biological correspondence; the investigation must identify the
same experiment from the study design. The prepared
`tests/test_a106_paper_dataset_identity.py` checks that a dataset-based revision
replaces a paper-based assessment through finalization and parent receipt,
preserves the old sheets, and cannot be added as a second contribution. A second
case checks that duplicate downloads cannot be summed even under distinct
experiment labels and an erroneous independence declaration. Both use synthetic
data and remain unrun behind the active workflow. They do not demonstrate
autonomous paper/dataset correspondence or satisfy the broader evaluation goal.

The direct paper-to-summary connection is now implemented but awaits execution
checks while the current autonomous workflow occupies this window. The existing
`literature.perturbation.populate` operation accepts optional `source_measurements`
with `data_source_ref=null`: exact number selectors, a printed unit witness,
reported summary/spread/count meanings and their supporting passages. It feeds
the existing summary reader and calculator, retaining numeric source spans and
using those spans as measurement identities across repeated acquisitions. It
does not require an intermediate hand-authored measurement JSON file. Existing
retained JSON inputs remain supported. The optional covariance selections pass
reported joint-mean covariance, its squared endpoint unit and source spans to the
same calculator. An explicitly selected uncorrelated relationship retains its
supporting passage and interpretation basis; no other pair is filled from it.
The existing covariance consistency checks still apply. Missing arms and
unreported cross-arm covariance remain unresolved; this connection supplies no
prediction numbers. The A106
operand projection normalizes `minutes` to the grader's `min` spelling while
retaining the original source cell. Regression checks are in
`tests/test_literature_perturbation_source.py`; they use constructed data and
must not be counted as a biological positive.

Source review on 2026-11-05 found that growth rates reported per hour were
rejected by the endpoint reader and direct prediction-unit reader. The A106
readers and return schemas now retain that scale as `per_h`, with variance and
covariance in `per_h_squared`. Printed `h^-1`, `h⁻¹` and `1/h` and their supported
squared forms are equivalent spellings; numerical values are not rescaled to
minutes. The common evidence-ratio calculation still requires matching
measurement/prediction units. Five source-to-summary-to-final-return
cases cover those spellings, reported covariance and a mismatched per-minute
prediction that must remain unscored. These constructed cases in
`tests/test_literature_perturbation_source.py` subsequently passed in
`runs/a106_pending_validation_20261105_01`; that run's twelve failures concerned
the separate UTF-8 feedback fixture and are described in the verification record
below. Reinspection of its command, output and five retained hourly-case
directories confirms this supersedes the earlier pending status. This extends
unit support, not prediction modeling; no new test execution was needed for
this documentation correction.

Further source review found that a received summary could retain `CFU_per_mL`
while A106's direct number reader marked the same density unit unsupported.
Both A106 source readers now share equivalent CFU-per-millilitre spellings and
explicit squared-density spellings, preserving the numeric scale. Static review
also found that the summary reader's generic suffix expansion incorrectly
accepted `CFU/mL^2` as squared density. Both readers now distinguish that spelling
from `(CFU/mL)^2`, while retaining the explicit `_squared` forms. A raw `count`
prediction cannot match a CFU-per-millilitre effect. Fourteen engineered cases in
`tests/test_intervention_cfu_units.py` cover summary-to-parent delivery, direct
measurement/variance operands, summary covariance and dimensional mismatches. They remain
unrun behind the original live workflow. The five existing hourly cases now
share the summary/grading/receipt helper and must also be rerun after that
workflow exits; their earlier passing evidence remains valid for the earlier
source. This correction neither changes the score formula nor supplies missing
biological predictions, and it is not loaded into the frozen live run.

The independently discovered carbon-starvation article also reports
`CFU/iOD/mL`, with iOD denoting initial optical density. The source-number and
reported-summary readers now preserve this as `CFU_per_initial_OD_per_mL`,
distinct from ordinary CFU density. The point calculation and typed return
contracts accept that native unit without changing values or calculating an
OD normalization. Whole-unit squared labels remain distinct from squaring
only the volume denominator, and unspecified `OD` is not treated as `iOD`.
Ten cases in `tests/test_intervention_normalized_cfu_units.py` cover the
summary/grading/parent-return path, incompatible prediction normalization and
incorrect covariance units. This includes the exact `c.f.u./iOD/mL` spelling
in supplement page 58 and its lowercase-millilitre equivalent. The retained
page text (SHA-256
`21b9dc26f09f6a218f155e631183dd6ebdd3b0312f679ef15cf16ece4a5f2f32`)
explicitly expands that notation as CFU/mL normalized by initial OD at runout.
The aliases preserve that meaning without stripping arbitrary punctuation or
mapping unspecified OD to initial OD. They are prepared but unrun behind the current
workflow. The figure-calibration reader retains its own existing unit list;
this change does not establish support for digitizing the normalized endpoint.
The frozen run is unchanged and no biological prediction was supplied.

The retained Gawand tables also exposed a format gap: their per-hour header is
`h<sup>−1</sup>`, which the A106 readers previously left unsupported. Source
now normalizes numeric superscripts and entities inside those superscripts for
unit lookup while preserving the exact source witnesses and numeric scale.
It leaves unrelated XML elements and escaped tag examples unsupported. Six
engineered cases in `tests/test_intervention_xml_units.py` cover hourly/CFU
summary-to-parent paths, squared units, raw-witness retention and invalid markup.
They remain unrun behind the original workflow. Direct scalar selections still
require adjacent units; this correction does not establish a complete original-
table prediction path, model support or a numerical positive.

The subsequent table-association review identified a way to reuse the existing
scalar and XML geometry readers. A106 now exposes `source_table_number` with
the exact number, row label, column headers and printed unit. Its association
callback checks the same table and row, binds headers to the data column and
requires the selected headers/unit to resolve one column. The scalar reader
still owns numeric boundaries, censoring, units and physical measurement keys;
ordinary scalar selections keep their adjacency requirement. No prediction
calculation or scientific applicability decision was added.

`tests/fixtures/a106_source_tables/gawand_2015_table2.xml` retains the original
4,041-byte Table 2 fragment, verified byte-for-byte against the acquired article.
Its README records article/fragment hashes and original byte coordinates.
Eleven prepared cases in `tests/test_intervention_table_units.py` cover the published
MOMA/RELATCH values, repeated-acquisition identity, incorrect row/column choices,
ambiguous grouped headers, markup attributes, unchanged scalar adjacency,
censoring, saved A106 inputs with no invented score and implementation identity.
Source review caught the initially omitted table-reader file in the A106 binding
fingerprint; it is now included so a changed table association changes the saved
implementation identity. The existing rate binding already includes the shared
table-geometry implementation. These cases remain
unrun behind the original workflow. The source path is implemented but its
execution and the candidate's model qualification remain unverified.

The investigation guidance now explicitly connects ambiguous extracted table
labels to the existing original-page/image viewers. It asks the episode to check
headings and captions, retain the view used for the assignment and preserve any
remaining ambiguity. This follows reinspection of the retained supplement's
Table S1 text, whose column labels and caption do not consistently name the same
deletion. The current run has extracted text but no original-page image for that
table. This is prompt guidance only: no page was rendered, no measurement was
reassigned, and the frozen workflow has not received the changed instructions.

The current run's supplement navigation exposed another acquisition limitation:
`source.pdf.text` accepted one page even though its native adapter already
supports contiguous ranges. The operation now accepts optional `last_page`
(inclusive), with `page` as the first physical page. Without it, the existing
single-page behavior remains. A multi-page derivative has `page=null` rather
than being labelled as one page; the result and retained source provenance
identify the requested range, and native page breaks remain in the text.
Reversed ranges are rejected before native execution. The A106 prompt explains
using `source.pdf.info`, range extraction and `source.locate` to find a section,
while preserving the difference between physical pages, printed labels and
text-derivative byte offsets. Image rendering still selects one page.
Seven native/provenance/invalid-selection checks are prepared in
`tests/test_pdf_text_ranges.py`. They use the reusable synthetic PDF helper in
`tests/test_live_a106_binding.py`, extended to multiple pages; both files need
execution after the original workflow exits. Source and whitespace review only
has run. No PDF conversion was launched for this change and the frozen run is
unchanged; this is not yet a demonstrated acquisition or A106 result.

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

The current autonomous run exposed an acquisition-recovery gap at decision 641:
`public.ncbi.entrez` returned `ncbi_entrez_native_error_response` for
`YeaG K426A kinase activity`. Its retained original response reports 146 hits,
lists `K426A` in `errorlist.phrasesnotfound`, and omits it from `querytranslation`.
The false acquisition receipt and retained Source are correct; the feedback did
not explain how to inspect the provider's message. Current source now supplies
an explicit `source.read` request for this failure, using the already-received
Source and its original representation. It does not select a different query,
retry, accept the broadened hit set or grant the original File as acquired data.
The tool instructions explain checking the error list and translated query.
The original response remains under source `source_2d5d250ef98fbe6c1541eab6`
in `runs/a106_sequence_case01_20261105_02`, artifact SHA-256
`202a7d6ce7cfea0bb60593da6afae16352b9e34ec568fc6adcb159d8d60b5975`.
A new host regression follows the supplied read request and checks original
bytes, unchanged selected query, one HTTP request and unchanged receipt custody.
It remains unrun behind the active full workflow, alongside the existing
`tests/test_ncbi_entrez_acquisition_host.py` suite. The frozen live workflow is
unchanged; its later searches do not verify this source correction.

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

Inspection of an alternate HPC analysis route on 2026-11-05 found three concrete
binding limits. `LiteratureEpisodes.child_roles` delegates A106 analysis access
to `intervention_execution.analysis_children`; that helper exposes `launch` and
`results` only when a BV-BRC AppService is registered. The live driver's
`execution_factory` likewise accepts only AppService API resources. Finally,
`intervention_analysis_native.py` parses retained tables and calculates their
declared components; it does not execute TRANSIT or DESeq2. The shared
`hpc_scientific_commission.py` can describe frozen executable work, but supplies
no intervention-analysis worker. The inspected A107 component worker computes
declared expression-table components, not differential-expression analysis.
Consequently changing only the configured machine would not create an A106
dataset-analysis route. An alternate HPC backend would need an actual analysis
worker, authenticated input/output provenance and A106 commissioning/return
bindings, reusing the existing HPC planning and monitoring machinery. This is
an unimplemented alternative to the existing AppService route, not an executed
workaround for its deferral. No remote connection, job, local analysis or
execution-configuration change was made during this inspection.

`tests/live_a106_workflow.py` runs the repository's default model and controller
from an anonymous protein sequence, with no external cutoff. It freezes both
application packages under its run directory. Evaluator expectations in
`tests/fixtures/a106_evaluation/case-01-evaluator.json` are separate and are never
loaded by the driver. The first attempted launch omitted `method_loop` and
stopped before a model call. The corrected case-01 launch is in
`runs/a106_sequence_case01_2026-11-03_02/`; it completed sequence identity,
citation lookup, publication search and acquisition. It acquired and read
supplementary material, created anchored experiment and hypothesis records,
and attempted intervention grading. Repeated requests used
document references where anchored interpretation references are required and
were rejected. It finalized three unavailable scores, explicitly noting
the absent grading sheet as well as unresolved variance and predictions. This
does not demonstrate the complete reader-to-grader path. The current prompt,
schema and error feedback explain the reference requirement; existing evaluations
keep their frozen source.
The case-01 evaluation in `runs/a106_sequence_case01_2026-11-03_03/`
includes the anchored-support guidance and actionable error details.
It encountered the Unicode-space bug, recovered by selecting the printed
percentage contrast, and created two accepted intervention assessments and two
unavailable final scores. Neither case-01 run has a recorded parent receipt.
The separate `runs/a106_sequence_case01_2026-11-03_04/` evaluation includes the
whitespace and criterion-schema corrections; it created one accepted assessment
and no final score.

A read-only review on 2026-11-04 is retained under
`runs/a106_saved_state_review_20261104_01/`. All four saved evaluations still
lack `result.json`; the process check found no matching A106 driver or run
process. These are incomplete attempts, not currently running evaluations.
Database episode states do not override the missing live processes. Their
original files and frozen code have been preserved.

The anonymous evaluation inputs and separate expectations are retained in
`tests/fixtures/a106_evaluation/`. The driver never loads evaluator files.

The new sequence-only attempt in `runs/a106_sequence_case01_20261104_01/`
uses the updated readers and finalization guidance. Its first accepted assessment
retains the paper's reported 32-minute reduction in recovery lag after 24 hours
of nitrogen starvation, with the original passage and comparison direction.
Variance, fixed predictions and several design/attribution criteria remain
unresolved in that assessment. The attempt has since published and revised an
unavailable final sheet with both experiment assessments selected (decisions 32
and 44). Its literature child subsequently yielded through the default controller.
The annotation parent's `literature_a106_subscore_received` rows now contain both
the original final (`source_ddf158f2424a011b29aaedd3`) and its explicitly linked
revision (`source_afb9e8ea08ba0f917d38593c`), each retaining two assessments and a
null score. They are revision history, not two independent score contributions.
This demonstrates autonomous unavailable-score delivery with the assessment
links intact. The parent's intervention receipt also contains the measured
32-minute contrast for the original and revised assessment. A compact SQL
receipt checkpoint is retained in the run's `parent-receipt-checkpoint.json`;
it is a delivery inventory, not a completed scientific audit. The parent
commissioned a focused follow-up for missing lag means,
uncertainty and construct correspondence. That follow-up failed before its first
model turn: the native provider panicked while creating a thread, and its pending
startup request did not return. The panicked provider alone was terminated after
recording the failure; the parent received an execution failure and then commissioned a
separate investigation of the glucose-to-malate experiment. That investigation
has completed model decisions and source-reading actions; it is not a successful
retry of the failed nitrogen-starvation follow-up.
The original workflow handle and owned systemd service remain active; overall
evaluation completion is not yet shown.

The glucose-to-malate investigation has now revised its existing assessment
(`source_8ed3b7ce76ea9822a35ff6db`), retaining the original experiment identity.
It anchored the MG1655 deletion background and biological triplicates from
different colonies. It distinguished average growth curves from per-culture lag
estimates and did not infer a lag variance or a restoration arm from those
curves. Decision 22 finalized this separate biological scope with the assessment
selected and an unavailable score. `malate-finalization-checkpoint.json` inventories
that saved final. Decisions 50–51 subsequently revised that assessment and final
(`source_27f5bd2e42cc1b1b45231250`, `source_6e6e423b9ef2dfda1e3c7e61`) to retain
the article's DctA-expression observation as a possible downstream explanation,
without treating it as an experimentally established cause. The revised final
explicitly supersedes the earlier malate final and remains unavailable. An
earlier PDF request hit the same frozen launcher memory
default defect described below; this is an access failure, not evidence that the
source contains no useful data.

The malate child subsequently yielded through the default controller after
decision 59. Its last spreadsheet-read attempt also failed preflight against
the frozen 20-GiB request default. Its closed form contains both malate finals,
but delivery to the parent failed: `interpretation_basis_refs[6]` identified a
retained NCBI request artifact that the public-provider owner deliberately keeps
private. The artifact exists; this was not a missing download or a model-invented
identifier. The host's visible-reference list and report ownership checks
disagreed. `malate-delivery-failure-checkpoint.json` records the failure and the
undelivered score cells. The parent has since commissioned another focused
nitrogen-starvation investigation (`literature/child_8`). That child has now
yielded through the default controller after decision 62 (58 completed
estimator observations; upper estimated next credit 0.000953598 versus cost
0.001). Delivery `delivery_99e75e42a6e2f9612f26c004` succeeded, but its requested
`a106_subscore`, `intervention_assessments` and `perturbation_summary` arrays are
all empty. Its attempted assessment revision was rejected as stale, and it
published no replacement assessment or final subscore. It did retain a source
observation defining lag through OD600 = 0.1, but that observation was not in the
parent's received records at delivery. The compact
`nitrogen-followup-return-checkpoint.json` inventories this return; it does not
establish a successful scientific follow-up. The parent workflow remains active.
Its next commission (`literature/child_10`) seeks a distinct YeaG intervention
experiment outside the nitrogen-starvation recovery and glucose-to-malate lag
comparisons. It requests intervention assessments and an A106 result for that
experiment's own biological scope; this is continuing investigation within the
original workflow, not a new evaluation launch.

That child corrected an exact-quotation mismatch and saved a sustained-starvation
survival assessment at decision 18 (`source_221de0509bf0a0c0030785ab`). The
[assessment inventory](../runs/a106_sequence_case01_20261104_01/survival-assessment-checkpoint.json)
records null effect, variance and evidence-ratio cells and no parent receipt at
that observation. Its claimed genotype conflict needs further review: the
methods describe double-mutant construction but also explicitly identify a
single `ΔyeaG` donor strain. Those statements alone do not contradict the
figure's single-mutant label. The evaluator now checks this distinction and
requires the specific assay/strain correspondence; supplementary Table S2 has
not yet been verified. Decision 19 then saved an unavailable final
(`source_a159550b5b6cf1cc046e7b65`) selecting this one assessment. Its
[final inventory](../runs/a106_sequence_case01_20261104_01/survival-finalization-checkpoint.json)
also shows no parent receipt at the observation. No new final-score delivery is
claimed from these saved sheets.

Decision 23 revised the survival assessment to
`source_9ed08c83f7a6e0b365a99fe1`, retaining the same experiment and adding design
witnesses, but it retained the claimed genotype conflict. Separate evaluator
review also verified the main article's Figure 3C anti-His abundance controls;
their applicability to later survival conditions remains a question, not proof
that no controls exist. The current general prompt now distinguishes an
unverified correspondence from incompatible descriptions of the same tested
subject and asks the episode to retain reported abundance controls within their
measured conditions. These are general interpretation instructions, with no
case-specific findings added to episode inputs. The frozen evaluation does not
use them. The already acquired supplement is 739,960 bytes at
`artifact_f76ef0b7f4ef9017622548f74e0914514133bfac9af9025d314952eebfcbf058`;
its strain table is still unverified. The external browser reader could not open
it, and a separate local PDF read has not been launched alongside the workflow.

The survival child subsequently yielded through the default controller after
decision 64 (58 completed actions). Delivery
`delivery_70796a534536db5331277c5e` succeeded. The
[return inventory](../runs/a106_sequence_case01_20261104_01/survival-return-checkpoint.json)
verifies the parent's receipts for all five assessment revisions (15 requested
cells) and all five corresponding final revisions. Every final remains
unavailable and selects one assessment for the same experiment; the latest is
`source_409ee4c86955cefa8e449eb2`. These revisions do not constitute five
independent experiments. The separate restoration observation was not received;
the contract requested only the numerical fields, not scientific-finding
assessments. Delivery therefore does not establish that separate return path or
resolve the genotype, control-applicability and numerical-input limitations.
At parent decision 12, `shared.publish_information` cited the latest assessment
and final score and retained their unavailable status. It also repeated the
genotype-conflict claim under review. This is observed use of the received
result, not independent validation of that interpretation.

The parent then commissioned `literature/child_14` to examine the distinct
Salmonella double-deletion mouse competition experiment in Figure 6C. A separate
review of the retained article confirmed an actual disagreement between the
caption's wild-type/mutant index definition and the methods' mutant/wild-type
definition. The reported 0.64 and attenuation interpretation agree with the
methods' direction. The case-01 evaluator now checks preservation of both
definitions, the five individual-mouse observations, the distinction between a
p value and estimate variance, and the joint-deletion/cross-species attribution
limits. These retrospective checks are not episode inputs. The child remains
part of the original workflow; no second evaluation was launched.

That child saved assessment `source_009e6c68c02c24852c2f7016` at decision 11
and final `source_bae7663d377daacd3324d47e` at decision 12. The
[saved-result inventory](../runs/a106_sequence_case01_20261104_01/competition-finalization-checkpoint.json)
shows one selected assessment and an unavailable final. The assessment retains
the reported 0.64 in its conclusion, explicitly identifies both conflicting
ratio definitions, and preserves the double-deletion and sequence-correspondence
limits. Its effect, variance and evidence-ratio cells remain unavailable.
No parent receipt or report attempt existed at that observation. The subsequent
PDF-info request hit the known frozen resource-request mismatch.

The child later acquired the original Figure 6 JPEG and viewed it at decisions
39–40. Independent visual review confirms five mouse-level points on the
logarithmic CI axis and horizontal summary marks. The caption does not define
those marks as SD or SEM; panel A/B definitions cannot be transferred to panel C.
The evaluator now checks that distinction and requires logarithmic calibration
and digitization uncertainty for any recovered point estimates. The reviewed
image hash and source are retained in case-01's `figure_review`. No numerical
digitization was performed, and the image does not resolve the ratio-direction
conflict or supply the original input/output counts.

The competition child subsequently yielded through the existing controller
after 58 completed actions. Its
[return inventory](../runs/a106_sequence_case01_20261104_01/competition-return-checkpoint.json)
confirms successful parent receipt of four final-score revisions and twelve
assessment cells, all belonging to the same experiment. Each final selects one
assessment and remains unavailable. The latest revision cites the explicit
caption direction alongside the conflicting Methods convention.
The parent's next model request then failed with `input_too_large`: 1,174,008
characters exceeded the provider's 1,048,576-character input limit. The overall
workflow exited with failure; its successful child delivery is not a completed
overall investigation. The supervisor recorded no OOM or limit-hit events.
After confirming the service inactive and its entire cgroup empty, the prepared
regressions ran serially in `runs/a106_pending_validation_20261105_01`.
The first run passed 61 checks and failed twelve UTF-8 feedback cases because
their test incorrectly required `changed_record_refs` on an invalid tool result.
The established invalid-result contract omits that field. After correcting the
test assertion, all fifteen checks in that file passed in
`runs/a106_source_window_validation_20261105_01`. The other selected files passed
in the first run: provider resource/failure/frame behavior, private report-basis
filtering, revision feedback, direct source summaries and hourly units,
paper/dataset identity, parent rendering and real PDF/spreadsheet execution.
These results supersede the pending-test descriptions above for those specific
changes. They do not validate an autonomous numerical positive or fix the
oversized parent request. The real provider startup probe subsequently completed
initialize and thread/start in `runs/a106_provider_startup_20261105_01`; it did
not request a model turn. The read-only retained-run audit in
`runs/a106_completed_audit_20261105_01` verified the anonymous input hash and all
1,403 frozen source files without a mismatch. It found eleven received final
revisions and three latest received final heads, all unavailable. This verifies
saved custody and source identity, not scientific adequacy or overall completion.

The retained supplement was subsequently read with the existing native document
reader and Table S2 visually checked on physical PDF page 6. It explicitly lists
single `delta-yeaG780::km` (JW1772-1) and double `delta-yeaGH::km` constructs
separately. Thus the existence of a double-mutant construction paragraph does
not support the survival assessment's claimed contradiction with a single-mutant
figure label. The table also places MG1655 and BW25113 in the same wild-type
description; exact background/sequence correspondence remains unresolved.
Reader receipts and the page image are in
`runs/a106_supplement_review_20261105_02` and
`runs/a106_supplement_page_20261105_01`. The case-01 evaluator records these
findings separately from episode inputs and the immutable original assessments.

The oversized parent presentation is now corrected in
`literature_a106_render.py`. Received assessment cells share their identical
experimental metadata in the display; final selections refer to the same
displayed cells. All received revisions, order, field names, values, qualifications
and selection multiplicities remain represented. Different payloads with the
same sheet/component identifiers remain distinct. Saved sheets, receipts,
scoring and continuation behavior are unchanged.
The focused renderer suite passed 22 checks in
`runs/a106_parent_render_validation_20261105_02`. The initial run's two failures
were test setup issues: absent received-reference metadata in the new fixture,
and an older assertion rejecting the now-supported anonymous discovery input.
Read-only rendering of the actual failed call, with empty diagnostic instructions
in both comparisons, fell from 1,151,972 to 340,212 characters. The thirteen
assessment definitions reconstruct the original child reports exactly. Evidence
is in `runs/a106_parent_prompt_review_20261105_01` and `_02`; this is a rendering
check, not a resumed or completed autonomous workflow.

A fresh full sequence-only evaluation started in
`runs/a106_sequence_case01_20261105_01` after the previous checks exited and the
window's service and cgroups were confirmed empty. It freezes the updated source
and uses the same anonymous 644-aa input, default models/controller and original
machine bounds. Evaluator expectations are excluded and BV-BRC execution remains
deferred. At the initial checkpoint the literature child had completed its
sequence-identity lookup; no final assessment or numerical success is claimed.

The fresh run subsequently exposed a separate waiting regression. A108's removal
of its wait action had been applied to every literature binding and every
literature-only annotation parent. A106's parent consequently repeated shared
information checks while its child was still working. The current source scopes
that exclusion to A108, restores the existing wait/estimate path for A106 and
shows received timing/progress support in the literature prompt. The restricted
parent's tool catalog and dispatcher now both permit the existing estimate
operation; ordinary source tools remain delegated to the child. Waiting still
uses the original event backend, estimator and controller; no new scoring rule,
research deadline or forced wait was added. The A106 presentation module is also
included in its binding implementation fingerprint.
The frozen investigation has since exited with `yielded_with_pending_work`,
58 completed parent actions, zero credit and an unfinished child. It produced
no assessment or final sheet. The service is inactive and the entire owned
slice has no processes; the child's persisted `active` state does not mean it
is still running. This is an incomplete investigation, not a successful
unavailable-score return. Its search failures include actual Europe PMC HTTP 503 responses declaring the
search service temporarily unavailable and a PubMed HTTP 500; they are retained
provider failures, not evidence that relevant experiments do not exist.

After confirming process exit, the focused wait/render suite in
`runs/a106_wait_validation_20261105_01` passed 28 checks and failed one older
test whose fixture lacked the receipts required by the real parent dispatcher.
The fixture now uses the real Store and receipt configuration. All seven
wait checks passed in `runs/a106_wait_validation_20261105_02`, covering
axis-specific permissions, catalog/dispatch agreement, actual event-wait
execution, zero-gain accounting and visible prompt operands. The parent catalog
also checks receipt availability before advertising the estimate operation.
These checks use scripted decisions. Autonomous choice of waiting, continued
child execution and a completed investigation on this correction remain unproven.

The next full anonymous case-01 evaluation is running in
`runs/a106_sequence_case01_20261105_02`. It was launched only after the serial
source-review commands exited and the owned service/slice were empty. Its frozen
source includes the wait correction, and its input remains the same 644-aa
sequence with no evaluator expectations or preloaded findings. Default models,
the existing continuation controller, machine constraints and BV-BRC deferral
are unchanged. The service and coordinator were confirmed live after launch;
this launch alone did not establish waiting or scientific completion.
The parent subsequently chose the existing event wait at decision 1, immediately
after commissioning its child. The saved request targets that child's actual
pending handle and `returned` event, with no scheduled reconsideration. The
wait interval is open, its wake/outcome are unset, and the service/coordinator
and model processes are live while the child continues making model calls.
`autonomous-wait-checkpoint.json` retains the actual wait row. This demonstrates
autonomous selection and execution of waiting; child completion, waking,
report delivery and the final scientific result remain unproven. Its saved
estimate explicitly reports unavailable prediction support rather than
inventing a duration, event probability or scientific gain.
While this same run continued, its child encountered repeated Europe PMC 503
and PubMed 500 responses. BRENDA's eleven retained reference rows included
unrelated author-name matches to Yeager and duplicates; selected SABIO-RK and
MaveDB responses were successful but empty. The case-01 evaluator now checks
these distinctions and separates unacquired primary evidence from missing
quantities in an inspected experiment. These checks remain outside episode
inputs. No primary-paper assessment, final subscore or new parent receipt had
been produced at this checkpoint.

That acquisition obstacle subsequently changed within the same running child:
decision 36's Europe PMC search succeeded and returned PMID 26621053 /
PMC4664914. Decision 37 acquired the full paper through `public.literature.read`,
and decision 38 began reading its ordered text. The 44,964-byte, 33-paragraph
projection has SHA-256
`498ea416ec9f259bd9092b0c8d8499d7b465c51a36e137cfb4e7bba8d3e0e924`, matching
the previously reviewed primary text. The run's
`primary-source-checkpoint.json` records these actual actions. This is autonomous
discovery and acquisition after transient failures, with no evaluator injection;
it does not establish an assessment, numerical result or parent delivery.
Decision 44 then saved a qualitative survival finding,
`assessment_4eadc999b13369ffc3b35b30`, anchored to the actual deletion and plasmid
complementation paragraph. Its persisted observation contains no numerical
measurements. It labels applicability as transfer from a different source
subject and uses inferred target extent, without asserting an exact experimental
strain match. The run's `survival-finding-checkpoint.json` retains the persisted
finding, observation and hypothesis. The child's investigation-progress credit
became 1; this is not an A106 evidence ratio or numerical final subscore. The
parent is still waiting, and no numerical worksheet or final return is yet proved.
Decision 48 added the mutant-complementation qualitative finding with mixed
support and an unestablished-assumption qualification. Decision 51 then saved
the Figure 6A intervention grading sheet
`source_91f6429b46a8a308d1f1d385` for
`reference_fc3769b433c7249d539d536f`. Its nine returned components are unavailable;
no numerical contrast, variance or predictions were manufactured. The assessment
retains the deletion/restoration conclusion, the caption's n=3/SEM statement,
unknown biological-unit/covariance details, unresolved exact subject
correspondence and limits on inferring a specific kinase reaction. The selected
passages do not supply numerical arm means or SEM magnitudes; the sheet does not
claim that the entire article lacks plotted measurements. The persisted sheet's
SHA-256 is `badac2a71572e729244b49e70217dc4650ace84e5856d3d43c3f8cd2e04d5b8b`.
`survival-grading-checkpoint.json` inventories these actual cells. Finalization
and actual parent delivery are still separate, unproven steps at this checkpoint.
Decision 52 subsequently saved final worksheet
`source_c8f0923da26e98ab91dbea13`, selecting the Figure 6A grading sheet once.
Its score and available subtotal are null, with the unavailable experiment score
explicitly named. The run's `survival-final-checkpoint.json` records this result.
The final's rationale groups the related Figure 6B observations with the CFU
experiment; common assay type alone does not establish whether panels reused
biological samples or controls. The evaluator now checks that distinction.
This selection avoids summing those observations but is not a full duplicate-
identity validation. The child then independently searched for and acquired the
glucose-to-malate paper (PMC8055822) at decisions 53/54. The same parent wait
remains active; no final parent receipt is established by these saved worksheets.
At decision 60 the child retained the paper's shorter-lag finding. Decision 64
saved intervention grading `source_32c573e8ae3fb27de2422893`; all nine components
are unavailable because the applicable numerical inputs remain unselected or
unsupported. Decision 65 saved final `source_65275bf84f98e6e838123b33`, selecting
that grading sheet once for experiment `reference_25f2c7ab6012b3ee2282ed00`.
The score and subtotal remain null. The final explicitly separates this
glucose-to-malate scope from nitrogen-starvation survival and retains the
no-shift control, absent restoration arm and unresolved target correspondence.
The selected caption distinguishes growth-profiler biological triplicates from
the scaled-up cultures' biological duplicates. Excluding Figure 1C from the sum
does not establish that these are the same biological observations or verify
their independence. The run's `malate-grading-checkpoint.json` and
`malate-final-checkpoint.json` preserve the actual actions and saved Sources;
both worksheet artifact hashes were verified. No report form or parent wake had
been recorded at this checkpoint. This is saved unavailable-result evidence,
not numerical-positive or parent-delivery completion.
The child next investigated recovery growth after nitrogen starvation. At
decision 73 it saved `source_23fbdbc29ef50e0d85964f01`, with `measured_effect`
populated as 32 min from the exact article span at bytes 7916–7924. The selected
comparison passage identifies a shorter mutant lag; the positive reduction is
wild-type lag minus mutant lag. Eight other components, including the evidence
ratio, remain unavailable. The sheet retains missing contrast variance and
predictions, unresolved exact subject correspondence and the absence of an
established restoration arm for this particular assay. It does not borrow the
separate CFU experiment's plasmid rescue. Verified the worksheet artifact hash
and retained `recovery-measurement-checkpoint.json`. Evaluator checks now
distinguish the same contrast's 13% description from another observation, and
the nearby 2.3-hour wild-type recovery/pre-starvation comparison from the
deletion contrast. This demonstrates autonomous retention of a real published
measurement; it does not establish a numerical final subscore or parent receipt.
Decision 74 then saved final `source_e0e5fefd7d224b6a9e1f2bbf`, selecting the
recovery grading sheet once. It retains the 32-minute conclusion and original
measurement key, with a null score/subtotal and the unavailable experiment score
named explicitly. Verified its artifact hash and retained
`recovery-final-checkpoint.json`; there was still no report form or parent wake.
The child continued inspecting the article after saving this final worksheet.
Evaluator-side review of the retained full article also confirms a separate
growth-complementation report in Figure 3A/B, with SD/n=3 specified for its growth
curves. The current recovery sheet's unestablished restoration input must not be
generalized to absence of growth rescue throughout the paper. Applying that
rescue to the selected contrast still requires checking conditions; pointwise
growth-curve SD is not lag-contrast variance. The existing supplement text
extraction identifies Table S1 columns for delta-yeaH and delta-yeaGH despite a
delta-yeaG mention in its prose. Original-page review is needed before assigning
its numbers; no uncertainty from those other deletion strains was substituted.
These evaluator checks are separate from the live episode, which is independently
listing the PMC archive assets. No episode inputs or saved assessments were changed.
The live child subsequently acquired that supplement autonomously at decision
80. Decisions 81/82 successfully ran `source.pdf.info` and page-1
`source.pdf.text`. Both native commands returned zero, with receipts identifying
this window's existing workflow owner, one CPU, 5-GiB memory bound and no swap.
The acquired PDF hash matches the previously reviewed original. Retained the
actions and complete execution provenance in `autonomous-pdf-checkpoint.json`.
This confirms the corrected PDF execution path in an autonomous run; it does
not yet establish Table S1 interpretation, dataset analysis or parent delivery.
After reading Table S1 and Table S2, the child retained three source-content
qualifications at decisions 101/105/108: the 6xHis rescue construct, the table's
delta-yeaH/delta-yeaGH subjects and the delta-yeaG780::km deletion marker. Their
qualifications are respectively limited transfer conditions, a different source
subject and unresolved confounding. The Table S1 finding explicitly does not
discriminate the single-yeaG claim. These observations contain no numerical
measurements and do not establish that the tag or cassette caused the phenotype.
`supplement-qualification-checkpoint.json` preserves the actual records/actions;
both retained page-text hashes were verified. Investigation progress reached 7,
which is separate from the evidence-ratio score. Incorporation into revised
grading/final worksheets and actual parent receipt remain unverified.
Decisions 111/116/125 subsequently retained the conflicting wild-type strain
identifiers, recovery suppression by a five-gene deletion, and the separate
Salmonella double-deletion competition finding. The last observation retains
reported CI 0.64 while its assessment is scope-limited and does not discriminate
the supplied-sequence claim. Verified all three source anchors against retained
bytes and both artifact hashes in `additional-controls-checkpoint.json`.
The recovery evaluator now distinguishes multigene suppression from restoring
YeaG. These findings have not yet been verified in a revised worksheet or parent
receipt; the existing competition evaluator still requires the caption/methods
ratio-direction conflict to be preserved.
Decision 133 then saved a separate Figure 6B variant-complementation assessment
(`source_daed63d1f42836e194e53e1e`) with its own SD/n=3 caption, construct and
reference-arm witnesses. All nine numerical components remain unavailable.
Decision 135 revised the survival final as `source_376f0ea20f6877de50551669`,
selecting that assessment and the existing Figure 6A assessment once each.
It explicitly leaves shared-control dependence unresolved and returns a null
score/subtotal. Both worksheet hashes and the exact selections are retained in
`survival-variant-final-checkpoint.json`; no parent report had been attempted at
capture. This demonstrates revised assessment selection and conservative
dependence handling, not a numerical positive or the complete paper/dataset
duplicate-identity case. The existing expression-control evaluator qualification
still applies: Figure 3C reports abundance measurements whose applicability to
the survival comparison needs assessment.
The child then retained the mutant/abundance and growth-rescue findings at
140/144 and saved a separate Figure 3 growth-complementation assessment at 146
(`source_27ce335665b9d1f0736b9818`). Its limitations preserve the anti-His
controls without treating protein abundance or failed rescue as catalytic
measurements. At 148, revised recovery final `source_976dfca36166b9a9ce6f2a05`
selects that assessment and the unchanged 32-minute lag assessment once each.
It preserves unknown cross-experiment dependence and a null score/subtotal.
The final's selected cells are the evidence-ratio components; the 32-minute
measured-effect cell remains in the linked original assessment and is described
in the final conclusion. Verified the three worksheet hashes and the new
finding anchors in `recovery-complementation-checkpoint.json`. No parent report
had been attempted at capture. This resolves the earlier selected-evidence
omission of growth complementation in this saved final, not the missing
variance/predictions or the broader numerical-positive requirement.
At 152 the child also corrected the Figure 6B survival assessment to retain
K426A/Y382Stop's reported 100%/96% protein signals while explicitly limiting
their applicability to later CFU sampling times. Revised sheet
`source_dbc1e145618eb9b19f6fe3b4` preserves the same experiment identity and
replaces `source_daed63d1f42836e194e53e1e`. Decision 153 propagated that revision
into survival final `source_aea9e16f67a6e8cd4d002072`, still selecting two
experiments, with unchanged scope, unknown dependence and null score/subtotal.
Verified both new and predecessor artifact hashes in
`survival-abundance-revision-checkpoint.json`; no parent report had been
attempted at capture. This verifies the saved revision path, not delivery or
the separate paper/dataset duplicate demonstration.
At 162 the existing relative-signal reader retained K426A's reported protein
signal ratio of 1.0, with derived log ratio and difference of zero. Calibrated
protein amount, functional effect and model scores remain unavailable.
Decisions 165/167 revised the growth assessment and recovery final to retain
this comparability qualification, without populating any intervention scoring
operand or adding an experiment. The ratio sheet is named in assessment text;
it is not a selected typed final component. Verified all three saved artifacts
in `relative-signal-control-checkpoint.json`. The final remains unavailable,
and no parent report had been attempted at capture.

The same child independently acquired Figure 3 at decision 294, viewed it at
295 and retained its printed K426A signal of 1.12 at 296. Evaluator review
confirmed that the right-hand immunoblot labels are 1.0, 1.12, 0.96 and 0 for
wild-type, K426A, Y382Stop and empty vector. The article prose instead reports
K426A at 100% (original XML bytes 23190–23194), which supplied the earlier
ratio reader. The separate evaluator now preserves this disagreement and
distinguishes the printed protein-control labels from growth effects, catalytic
activity and additional biological replicates. Original article/image and
episode-view hashes, exact prose bytes and the saved finding are retained in
`figure3-protein-control-checkpoint.json`. At capture no later grading or
finalization had propagated this finding, and no parent report existed.
No band intensities or growth curves were numerically extracted.

Decision 299 then requested the new observation through `state.query`'s
`references` filter and received no records: that filter finds records pointing
to an ID, not the record with that ID. The existing exact `refs` mode supports
the latter. Added this distinction directly to the `references` argument
description; query behavior is unchanged. This presentation edit is queued
source work and does not alter the frozen workflow. The child independently
corrected its request at decision 300 to exact `refs` and received the saved
observation. That recovery used the original frozen guidance, not this edit.

At decision 303 the child attempted to populate the ratio reader with both prose
and figure representations. Input validation rejected an array supplied where a
single image-witness object was required, before an action was executed. The
rejection is stored in `runtime_decision_effects`, not `runtime_actions`. The next
attempt at 304 reached the reader but failed its image-region check: the supplied
coordinates used width/height where the reader expects right/bottom coordinates.
Both actual attempts are retained in `ratio-request-rejections-checkpoint.json`.
The audit now inventories rejected decisions separately from executed action
failures. A prepared regression in `tests/test_a106_workflow_audit.py` covers that
distinction, a partial HTTP failure and a valid partial result. It has not run
while the live workflow occupies this window. The ratio operation description
now states the witness-object shape and `[left, top, right, bottom]` format;
the schema, geometry validation and calculations are unchanged. This queued
guidance does not alter the frozen child or establish a successful retry.

Decision 308 then saved revised growth assessment
`source_0d198476f2f9feddc59b74fd`, replacing
`source_f8f4545de47e850b5cdd6e72` under the same experiment and assessment key.
It retains prose 100% and Figure 3C 1.12 as protein-control representations,
keeps their physical measurement identity unresolved and does not convert
either into a growth effect or active-protein amount. All nine numerical cells
remain unavailable. `growth-control-discrepancy-revision-checkpoint.json`
retains the assessment, matching experiment/key, both worksheet hashes and ten
exact design-witness byte checks. Those checks establish literal source text,
not biological applicability. Both supporting scientific findings are selected
in the child's saved report state, but no parent report or later finalization
existed at capture. This is successful assessment revision after the ratio-reader
failures; it does not establish a successful ratio-reader retry or final delivery.

The next finalization attempt (309) selected a PMC version-listing source as its
lag-assessment sheet alongside the revised growth assessment. The existing
`assay_grading_sheet_required` rejection correctly prevented publication, but
did not identify the mistaken selection. The retained
`final-sheet-selection-failure-checkpoint.json` records the call and source
providers. The finalizer now adds the selected experiment/field/source and
expected versus actual provider to that same error, after the original
possession/scope checks. It explains that the input must be the received
intervention-grading worksheet; it does not substitute a worksheet or expose an
unreceived source's metadata. Two binding-level checks in
`tests/test_a106_final_selection_feedback.py` are prepared but unrun, covering
the diagnostic, rejection without publication, receipt isolation and correction
with the existing synthetic score. The frozen live run retains its original
feedback; this queued change does not establish recovery or parent delivery.

The frozen child subsequently read its prior final at 310 and corrected the
lag-sheet reference at 311. New final `source_517851da2a6158fb4a4f0501` replaces
`source_7c609d8d6f409c5b5a12a1cc`, selecting the unchanged lag worksheet
`source_23fbdbc29ef50e0d85964f01` and revised growth worksheet
`source_0d198476f2f9feddc59b74fd` once each. Its conclusion and limitations retain
the protein-control discrepancy; dependence, score and available subtotal remain
unresolved. Verified the new/predecessor final and lag-worksheet hashes in
`recovery-control-discrepancy-final-checkpoint.json`. No report attempt existed
at capture. This confirms autonomous correction and saved final selection under
the original frozen guidance, not validation of the pending feedback edit or
parent delivery.

The child next retained the methods' qualitative confirmation of similar
starting viable-cell counts (316/317). At 319 it revised the lag assessment to
`source_b888416add6d3ee5942d169d`, retaining measured effect 32 min and its
original measurement key while adding that control's exact source witness.
The control supplies no numerical variance, prediction or complete isolation
bound. At 321 final `source_d9f1abe76e7c9b9b4fc5dadb` replaced
`source_517851da2a6158fb4a4f0501`, selecting the revised lag and growth
assessments once each. It preserves the protein-control discrepancy and unknown
dependence; score/subtotal remain null. Verified the new worksheet hashes,
literal witness and unchanged measurement identity in
`recovery-starting-cell-control-checkpoint.json`. The separate evaluator now
checks retention and limits of this control. No parent report existed at capture.

At 329/331 the child retained separate findings for Figure 6A's SEM and Figure
6B's SD, each with n=3. Both anchors match the original article bytes and the
article hash was independently verified in
`survival-spread-findings-checkpoint.json`. These findings preserve the reported
uncertainty definitions without inventing numerical spreads, arm covariance or
contrast variance. There was no parent report at capture; the findings' delivery
and use remain to be checked.

At 341–343 the child acquired and viewed the original Figure 6 image and
retained the panel B CFU-per-millilitre endpoint. Evaluator image review confirms
that finding and distinguishes B's density values on a logarithmic display from
A's explicitly labelled `log CFU/ml` quantity. Original/display hashes, the
typed endpoint finding and exact CFU-method witness are retained in
`survival-figure-scale-checkpoint.json`. The separate evaluator now checks those
panel-specific scales; no digitized measurements, variance or predictions were
produced. No parent report existed at capture.

Decision 348 saved Figure 6B assessment `source_955f584bf1ed630ed8cdebfb` with
the same experiment reference as the earlier variant-complementation assessment,
but another assessment key and no predecessor. It is a separate assessment of
the broader deletion/variant question, not a revision of the earlier sheet.
At 350 final `source_114bef60b9518a84001b83d9` revised
`source_aea9e16f67a6e8cd4d002072`, selecting the original Figure 6A assessment
and the new Figure 6B assessment once each. The prior Figure 6B sheet is not also
selected. Unknown dependence and null score/subtotal remain explicit. The
`survival-current-selection-checkpoint.json` verifies both new hashes, all nine
design witnesses and two distinct selected experiment references; it records
no parent report at capture. This is saved selection evidence, not autonomous
paper/dataset deduplication or completed delivery.

At 388 the child revised the malate Figure 1B assessment to
`source_2f0951a04380beb196b432a1`, replacing
`source_d53a96723bbf95d80bcd99cf` under the same assessment key and experiment.
It replaced a vague intervention excerpt with the actual glucose-to-malate
comparison and retained the MG1655 recipient and colony-derived triplicates.
All three design witnesses match the original article bytes. Decision 390
revised the malate final to `source_af2784a8757bc8df656c4184`, selecting that
new assessment once in place of its predecessor. The run's
`malate-corrected-assessment-final-checkpoint.json` records the four verified
worksheet hashes, revision links and exact-witness checks. All nine assessment
cells and the final score remain unavailable; effect, uncertainty, predictions
and exact sequence correspondence are still unresolved. No report attempt
existed at capture. This verifies saved correction and selection, not parent
delivery or a numerical positive.

Decision 395 subsequently tried to finalize survival evidence with the old
Figure 6A assessment, already revised at 359, and a final predecessor revised
at 360. The assessment check correctly rejected the call with
`a106_current_assessment_required`, but supplied no field or replacement
reference; the final-predecessor check was not reached. The separate
`final-stale-selection-checkpoint.json` records that rejection and both earlier
revision links. Current source feedback identifies the stale assessment field
and exact experiment/assessment key, adding its current reference only when
already received and within scope. The final-predecessor diagnostic follows
the same receipt rule. Neither selection is changed automatically. Four more
binding cases in `tests/test_a106_final_selection_feedback.py` cover visible
versus unreceived successors, another assessment key for the same experiment,
unchanged prior results and explicit correction. These are prepared but unrun;
the frozen workflow retains its original diagnostics.

The frozen child subsequently recovered without that feedback change. Decision
408 saved final `source_9b7f02604cbbc6fed3396ad4`, revising
`source_5cc2ed0c1ed3269f12ca3d92` and selecting the current Figure 6A sheet
`source_44c9fea76d5a02d401791e01` plus Figure 6B sheet
`source_dbc1e145618eb9b19f6fe3b4`, once per experiment. The score and available
subtotal remain null, with dependence unknown. Four worksheet hashes and both
dependence witnesses were verified in `survival-final-recovery-checkpoint.json`.
The revision reason incorrectly calls the replaced Figure 6B selection
superseded: assessment 348 and the selected 152 have different keys and no
revision link between them; 152 revises 133 within its own key. The checkpoint
and separate evaluator preserve that distinction rather than treating accepted
finalization as validation of its explanation. General prompt guidance now
distinguishes revision chains from switching assessment questions. No parent
report existed at capture; the frozen prompt is unchanged and pending executable
checks remain unrun.

Decision 415 retained Table S2's arabinose-inducible 6xHis-YeaG construct
description. The two quoted spans and the previously rendered original page
were verified separately, and the evaluator preserves the limits on inferring
protein amount or exact construct sequence. At 417 the child revised Figure 6A
assessment 359 to `source_2435c99a7c738acbb34bb9ee`, retaining its experiment
and assessment key while recording tag, dosage and induction limitations.
`survival-tagged-construct-revision-checkpoint.json` verifies both worksheet
hashes and all eleven design witnesses. All nine numerical cells remain
unavailable. This confirms propagation into the assessment; final selection
and parent delivery are separate, unverified steps at this checkpoint.

At 625 the child retained the methods' 0.1% (w/v) arabinose induction for
pBAD18 complementation, distinct from 0.2% for the fluorescence plasmid.
`complementation-induction-finding-checkpoint.json` verifies three records,
both exact source anchors and the article hash. The ordinary survival finding
uses `mixed`/`transfer` with `conditions_limit_transfer`. Its numeric context
attribute has no unit reference; percentage and w/v remain in the source, so
this is not a validated concentration conversion or protein-abundance operand.
Evaluator checks preserve the protocol mapping and its limits. The checkpoint
contains child-only receipts and zero report attempts; a numerical worksheet
revision or parent use remains unverified. No additional workflow ran.

Decisions 627/630 retain the anti-His immunoblot method and the separate Figure
5E RpoS/DnaK loading control as scope-limited findings for recovery growth.
`protein-control-scope-findings-checkpoint.json` verifies nine records and seven
exact anchors. Evaluator review additionally identifies the caption's conflicting
repetition counts: three for densitometry and four for SD bars. Both occur in
the original source; the child retained the quotation, but explicit handling of
that discrepancy remains unverified. The evaluator preserves the endpoint/control
distinction and does not choose a repetition count for an uncertainty calculation.
No numerical revision or parent delivery is established by these method findings.

At 637 the child retained the K116A/R232A/K426A design claim with
`prediction_not_measurement`. The variant-design checkpoint verifies six records,
five exact anchors and the article hash. The source explains selection through
sequence alignments; this passage alone supplies neither a direct activity
measurement on those variants nor numerical predictions of their growth effects.
The evaluator preserves that distinction without excluding separate biochemical
evidence. Only child receipts existed; no numerical revision or parent return
is established by this ordinary finding.

Decision 650 separately retains purified YeaG's reported autokinase and casein
kinase activities from the abstract of PMID 18276156. Its Source is a Europe PMC
search response containing the abstract, not acquired full text. The saved
finding is `scope_limited`/`does_not_discriminate` for recovery growth, qualified
by `different_source_subject`. The abstract's pET-21a/BL21(DE3) expression and
in-vitro manganese condition do not establish activity of the later variants
or their effect on growth. The observation has no numerical measurements, and
the descriptive protein reference does not establish exact construct sequence.
`purified-kinase-scope-finding-checkpoint.json` verifies five records, four exact
anchors, the source hash and child-only receipts, with zero report attempts.
Separate evaluator checks preserve this distinction from the design statement
at 637. No numerical worksheet revision or parent delivery is established.

Decisions 665/667 independently discovered GSE210382 through Entrez and acquired
its summary. The metadata describes a PA14 TnSeq biofilm study, links PMID
36312952 and BioProject PRJNA865538, and lists nine samples labelled T0,
planktonic and biofilm, each with r1/r2/r3 labels. The summary mentions YeaG;
this does not establish correspondence to the input's E. coli reference matches
or the actual PA14 experimental construct. The labels alone do not establish
biological independence or pairing. The TnSeq discovery checkpoint retains both
actions, Sources, original responses and child-only receipts, with zero report
attempts; both original hashes were verified. Evaluator checks preserve these
limits and the study's paper/dataset relationship. CSV/WIG files are advertised,
not inspected here. This establishes autonomous dataset discovery, not an
executed analysis, experimental assessment, numerical result or parent delivery.

At 670 the episode acquired the linked full text, PMC9611778. Evaluator review
verified the original and ordered-text hashes and retained the original method
passages. The paper establishes three biological TnSeq replicates, each with
four technical replicates, and a biofilm-versus-planktonic contrast separate
from T0 essentiality. Bio-TraDIS and TRANSIT analyze the same experiment; their
results are not independent replications. The reviewed YeaG validation uses a
transposon mutant; the described complementation is for BosR. Further checks
preserve the native table scale, Figure 3 medians versus geometric means and
competition normalization. The transposon libraries' sequencing alongside
RNASeq libraries does not establish an RNASeq expression experiment. This is
source review; episode interpretation, data analysis and parent delivery remain
unverified. No new workflow or scientific calculation ran.

Decision 674 retains the PA14 biofilm competition finding with
`incomparable`/`does_not_discriminate` and `different_source_subject` for a new
input biofilm-fitness hypothesis. The observation has no numerical measurements;
the source's group-level five-to-ten-fold range is not an exact YeaG effect.
The finding checkpoint verifies six records, four exact original anchors and
child-only receipts, with zero report attempts. Its descriptive references and
inferred input footprint do not establish sequence correspondence. This verifies
qualified scientific retention, not numerical grading, analysis or parent return.

After decision 686, evaluator review of original bytes 79943-81463 additionally
verified the `nusG` stop-codon insertion control and biofilm-deficient `flgM`
control. The former was compared with actual WT and reported as not significantly
different; it is neither untouched WT nor evidence of exact equality. Added
checks preserve these controls without treating them as YeaG complementation or
as exclusion of YeaG-specific polar effects. This source review alone did not
establish correct interpretation in an episode assessment.

At 687 the episode retained the insertion-control passage in an observation and
an `incomparable`/`does_not_discriminate` assessment with `confounding_unresolved`.
The insertion-finding checkpoint verifies two records, the exact quotation and
two child-only receipts. However, its source claim assigns
`feature_structure=mobile_element` to the descriptive YeaG reference: the
experiment's transposon insertion does not establish that native classification.
Evaluator checks flag this semantic error despite valid anchoring and progress
credit. The current prompt now distinguishes introduced material from native
gene properties and explains retaining design facts through observations and
condition/context references. This clarification is not loaded into the frozen
run. No numerical measurements or parent report were present at capture.
The frozen episode independently corrected the claim at 688: a new sample
reference names the transposon-library mutants, and the new assessment explicitly
replaces the 687 finding. The correction checkpoint verifies four new records,
three exact anchors and four child-only receipts. Both assessments have revision
1 under distinct identities; the `replaces_refs` link establishes the correction.
Progress credit remains 83. The finding still leaves confounding unresolved and
does not establish numerical scoring, complete interpretation of both controls,
sequence correspondence or parent delivery.

At 690 the episode explicitly retained Figure 3B's geometric means of competitive
indices under the 96-hour biofilm context. Verified five records, four exact
original anchors and five child-only receipts. The assay-level finding remains
`incomparable`/`does_not_discriminate` with no numerical measurements; the duration
is in the context name rather than typed numeric attributes. This preserves the
reported summary statistic without supplying an arithmetic mean, variance,
independent experiment, executed analysis or parent receipt.

Decision 734 retained the construction of BosR and PA14_56430 deletion mutants,
linked to the earlier transposon-library observation. Verified three records,
two exact anchors at original bytes 84874–84966, the original article hash and
three child-only receipts in
`tnseq-deletion-validation-scope-finding-checkpoint.json`. The finding remains
`incomparable`/`does_not_discriminate` with `different_source_subject` for the
input's biofilm hypothesis. Its quote establishes construction, not the later
phenotype or complementation results, and its observation has no measurements.
Evaluator checks prevent transferring those interventions to YeaG. Progress
credit increased to 85; no numerical score or parent return is established.
This separate finding does not repair the rejected length citations at 724/726.

Decisions 697-699 acquired the PMC archive version, file catalog and
`Table_4.xlsx`. Independent SHA-256 and advertised-MD5 checks passed. Inspection
of workbook metadata and relationships verified four named sheets for compiled
essential genes, Bio-TraDIS, TRANSIT and excluded genes; sheet IDs differ from
part numbers, so the relationship mapping is retained in the evaluator. The
article identifies this workbook with initial-pool essentiality rather than
the biofilm contrast. Source/material custody is child-only. Selected worksheet
cells, a newly executed analysis, numerical operands and parent delivery remain
unverified at that acquisition review; the other listed supplements were not
inspected there.

Decisions 700-702 listed the sheets and completed literal `yeaG` searches in the
Bio-TraDIS and TRANSIT sheets with zero matches. Reader hashes, parent-Source
links and child-only receipts were verified. Independent original-XML inspection
found no `yeaG` shared string, but Bio-TraDIS row 4078 contains candidate
`PA14_50790`/`PA1050`, a blank Name cell and `hypothetical protein` description.
Its three values 1, 25 and 27 are headed Read count BR1/BR2/BR3, with a
`nonessential` final call for T0. They are not biofilm effects or uncertainty.
The title names annotation database v20.2 and Ortholuge 2.1, which are retained
separately from mapping-method versions. Evaluator checks preserve these facts
without equating a failed name lookup with absent experimental coverage or
resolving the candidate's relationship to the tested kinase. This independent
row review is not an episode finding, new analysis, numerical score or parent
return.

Decision 705 acquired a second XML representation of the same paper from the
PMC archive. Both original hashes and the archive's advertised MD5 were verified;
PMCID, PMID and DOI match. Five method/design passages match verbatim at different
byte offsets, while other reviewed fragments do not match as exact byte strings.
The evaluator now retains both Source identities and the five coordinate pairs.
It requires source-specific anchoring and preservation of underlying experiment
identity without treating a new artifact as a new experiment, collapsing all
experiments in one paper, or assuming complete content equivalence. New custody
remains child-only; this provides a repeated-source condition to evaluate, not
proof of episode deduplication, numerical scoring or parent delivery.

Decision 706 acquired `Data_Sheet_1.doc`; SHA-256, advertised MD5 and child-only
Source/material receipts were verified. File-format metadata identifies a legacy
Word compound document, and the retained Source has no text derivative. Current
and frozen document routes expose ZIP/TAR, PDF and XLSX readers but no legacy
Word conversion. The evaluator records this acquisition/reading distinction;
the supplement's contents remain uninspected. No converter was run or added,
and this format limitation is not evidence that the supplement lacks relevant
data or that an existing reader regressed.
At 707 the episode requested a text read from offset zero and received
`source_not_utf8_text`, with no result or new records. The reader correctly
selected the original binary because no text derivative exists. Current source
now adds the requested/selected representation, available representations,
artifact identity and invalid-byte offset to this error's feedback. It does
not decode, convert, select a different representation or suggest a byte retry.
Three new cases in `tests/test_source_window_feedback.py` check the missing-text
fallback and preservation of an explicitly selected unreadable original/text
representation despite a readable alternative. They remain unrun behind the
original workflow; the frozen run does not contain this feedback change.

Decisions 724 and 726 repeated an `anchor_transcription_mismatch` while trying
to retain the PA14 candidate's length. Verified the original hash and bytes for
`source_595555d71dc4fdfa513ab309`: the selected range was 0–753, while the quoted
text had 752 UTF-8 bytes and omitted the file's final newline. Both commits were
invalid, with no new records; rereading the source at 725 had not corrected the
second request. This was a citation failure, not a saved scientific finding.
Current `Store._anchor` feedback now reports the source/artifact, selected range,
artifact size and quote byte count, and distinguishes an out-of-bounds range,
different byte lengths and different text of equal length. Exact-byte validation,
full-artifact integrity checking and bounded reads are unchanged. It does not
rewrite either the quote or the range. Four cases in
`tests/test_anchor_transcription_feedback.py` cover the missing newline, UTF-8
character/byte confusion, different text and an invalid range, followed by a
separately requested valid commit. They and the existing `tests/test_state.py`
anchor/integrity checks remain unrun behind the original workflow. The frozen
run is unchanged; no recovery or parent delivery is claimed by this source edit.
Inspection of the retained native model requests after both failures confirms
that `anchor_transcription_mismatch` and the dependent unresolved-alias errors
were actually displayed. `citation-rejection-feedback-review.json` retains the
two request hashes and exact feedback lines. Immediate feedback loss is not
established, and later bootstrap prompts alone do not prove loss of conversation
history. No provider, history or continuation change was made from this review.

At 681 the episode acquired PA14 reference ABJ10214.1. Its original GenPept
labels PA14_50790 as `yeaG`, but annotates CdaR/Diacid_rec regions; its 370-residue
sequence differs in length from the 644-residue input. Original and sequence
hashes were verified, including reconstruction from ORIGIN. Evaluator checks
now require resolving this candidate's locus against the paper's tested kinase;
neither the name nor the annotation discrepancy establishes that correspondence
or rules out homology. No alignment, revised assessment or numerical use is
established by this acquisition.

At 716 the episode acquired a distinct candidate, WP_420472570.1, annotated as
P. aeruginosa protein kinase YeaG. Its original hash and reconstructed ORIGIN
sequence were checked: it has 644 residues but differs from the retained input's
sequence hash. The nonredundant RefSeq record supplies no PA14 strain, locus tag
or coding-location qualifier. Its name evidence is BlastRule NBR010993, its
PrkA-family annotation is provisional, and its two cited papers concern E. coli.
The evaluator preserves these limits without inferring lack of homology or
linking this candidate to the PA14 experiment. Source custody is child-only;
no alignment, assessment use, numerical result or parent delivery is established.
At 718 the episode's literal scan reported three differences at zero-based
positions 290, 324 and 415 (input/source S/A, Y/S and M/R). All 65 source spans
covering 644 residues and the three reported positions were checked against the
retained bytes; the source span is 2167-2975. The frozen implementation uses
zero-based positional comparison without alignment. The tool published no new
records and does not settle strain/construct correspondence or functional transfer.

At 419 the child revised Figure 6B assessment 152 to
`source_55ee7adae679558d23ff37dc`, preserving its experiment and assessment key
while clarifying the selected variant-versus-wild-type plasmid comparison in
the deletion background. The new limitations retain tagging, inducible
expression, uncertain sampling/covariance and limited transfer of Figure 3
protein signals. The survival-variant-comparator-revision checkpoint verifies
both worksheet hashes and nine exact design witnesses; all nine numerical
cells remain unavailable. The worksheet still quotes the Figure 3 prose's
100%/96% without carrying its previously reviewed K426A image/prose discrepancy
into these limitations. That omission remains an evaluator issue for the
combined parent return, not a reconciled conflict or a reader regression.
No parent report existed at capture.

Decision 420 saved final `source_4ea318c8ab6019e9aa270111`, revising final 408
and selecting assessments 417 and 419 once each for their original experiments.
`survival-current-revisions-final-checkpoint.json` verifies the new final,
predecessor and selected worksheet hashes, plus both exact dependence witnesses.
The selected sheets carry the tagged-construct and comparator qualifications;
the Figure 6B protein-control discrepancy omission remains unresolved. Score
and available subtotal remain null, dependence unknown, and no parent report
existed at capture. This establishes saved selection of the two revisions,
not their delivery or a numerical result. The frozen workflow has not used
the queued source changes.

At 423 the same autonomous child acquired PMC13684143, a separate carbon-
starvation study in NCM3722 that proposes renaming yeaG to spdA. Evaluator-only
review verified the original XML and text hashes and located explicit reuse
of Figure 2C measurements in Figure 4D and Figure 4B viability data in Figure 5F.
The case evaluator now checks those dependencies, gene naming, experimental
backgrounds, early versus later proteolysis, panel-specific replication and
the distinction between energy supplementation and genetic complementation.
It also records PXD060434 as a proteomics acquisition lead; the deposition and
supplementary files have not been inspected in this review. These expectations
remain outside episode inputs. Acquisition of this paper does not establish
its assessment, a numerical score, duplicate handling or dataset analysis.
At 435 the child retained its first scientific finding from that article:
reduced protein loss after yeaG deletion, linked to the NCM3722 background and
qualified for transfer to the supplied sequence. The carbon-starvation-first-
finding checkpoint verifies the article hash, all eight retained records and
six exact anchors covering two distinct passages. It preserves the general
starvation context and the need for later assessment of timing and experimental
scope. Investigation credit increased to 52; this is not an A106 evidence score.
No numerical worksheet or parent report was established by that finding.
At 440 it saved intervention assessment `source_8c08138575e5bfbd5369d934`
for the Figure 4C total-protein experiment. The assessment correctly separates
protein amount from the Figure 4D degradation flux and retains unresolved
allele correspondence, restoration and numerical inputs. All nine cells are
unavailable. Its scientific question names NCM3722 and its condition-scope
interpretation cites the retained strain reference, but the structured strain,
reference-condition, sampling-time and replication fields remain empty. Those
unfilled fields do not establish absence of that information from the source.
At 441 final `source_0c486275e09f259961771757` selects this assessment once,
explicitly scopes the comparison to glucose depletion and notes the cultures
shared with Figure 4B. Score and available subtotal remain null. The separate
carbon-protein-amount assessment and final checkpoints verify both worksheet
hashes, four exact design witnesses and the single experiment selection.
No parent report existed at capture. Neither this selection nor the dependence
discussion demonstrates the required paper/dataset duplicate-handling case.
At 444/448 the child separately retained the viability comparison and its
Figure 4B SEM/three-biological-replicate description. The carbon-viability-
findings checkpoint verifies twelve retained records and nine exact anchors
covering three passages. The observations distinguish the single yeaG and
dps deletions and the wild-type comparator; replication is retained as a
count, with an explicit qualification that it does not establish the claimed
effect. It supplies no numerical variance. Viability remains a distinct
endpoint from the Figure 4C protein amount, and their shared cultures still
matter for any later combination. No parent report existed at capture.
Decisions 450/451 then saved viability assessment
`source_6545d7f996ebe2918efeadb3` and final
`source_afcfabc62797bb0c1f574be1`. The final selects that experiment once,
retains its SEM/biological-replicate description and the same-culture
protein-amount limitation, and distinguishes glucose depletion from the
earlier nitrogen-starvation experiments. All nine assessment cells and the
final score/subtotal remain unavailable. The carbon-viability-assessment-final
checkpoint verifies both hashes and four exact witnesses. The grading assertion
uses the term viability; the earlier finding used loss of viability, with a
different hypothesis reference. Interpretation and parent-return review must
preserve that distinction. Several structured design fields remain unfilled;
no parent report existed at capture. This is saved assessment/finalization
evidence, not a numerical result or completed duplicate-handling demonstration.
At 456 the child acquired the new paper's original supplementary PDF as
`source_1513a6cd4a335d491185fa97`. Its 28,816,634 bytes and MD5
`94ce43ee6a2711a5e9a55a847b1efac1` match the article's advertised supplement;
the retained SHA-256 is
`5fdf7295c49ae211a8770929e9b545a7eb1adfc9b6f9b758143d9acb009b5064`.
This verifies acquisition, not interpretation of its methods, measurements or
uncertainty. No separate PDF parser or workflow was started for this review.
The child subsequently extracted supplement page 2 at decision 460 and located
the single-deletion construction paragraph at 463. Evaluator review verified
the page-text SHA-256
`87f1f3cf206f44ab9ff5c59ee5b22d01491245249db816e22f76cd5850f2cbe5`
and the exact witness at bytes 214–694. That paragraph identifies HE845 as the
NCM3722-derived YeaG deletion strain and distinguishes Keio donors from the
recipient. It reports cassette removal only "in some cases"; the specific
marker state still needs the named Table S3 or other explicit evidence.
The separate evaluator now checks those distinctions. This review used the
child's retained text, did not inspect Table S3 or run another PDF conversion,
and does not establish that a revised assessment or parent return includes
the construction details.
At 465/466 the child extracted and read supplement page 7. Its retained text
hash is `0e80d7404395b485803751dc0109e22b21bd4583176f6ab63aa59a52b9ac56e2`;
bytes 1323–1826 describe the degradation-flux fit and its uncertainty. The
reported error is the standard error of a slope fitted to four or five time
measurements, not a stated spread across that many biological replicates.
The evaluator now checks that distinction and preserves the qualification
"typically" in the description of independent cultures. Reused Figure 2C data
in Figure 4D remain the same measurements. This source review adds no numerical
variance, prediction, assessment or parent-delivery claim.
Decision 480 subsequently retained an ordinary scientific finding that the
Figure 4C amount endpoint does not establish the degradation-flux claim. This
agrees with the limitation already present in assessment 440; it is not a new
experiment. `carbon-protein-amount-scope-finding-checkpoint.json` retains the
four changed records, verified article hash and three exact anchors at bytes
65210–65270. The result reference is a `literature_result`, distinct from the
existing assay reference. No numerical sheet or parent report was added by
this finding.
Decision 484 then retained the direct degradation-flux endpoint in Figure 4D
and explicitly identified its wild-type measurements as reused from Figure
2C. `carbon-flux-reused-control-finding-checkpoint.json` retains seven records,
the verified original article hash and five exact anchors over bytes
65060–65674. This is autonomous recognition of source-measurement reuse,
separate from the earlier evaluator expectations. The caption identifies the
assay and reuse, not a numerical effect; it also contains adjacent Figure 4B
SEM/replication text that must retain its own panel scope. No final-score
dependence handling or parent delivery is established by these findings.
At 494 the child retained washing as an assay condition limiting transfer of
the flux-related evidence. `carbon-wash-condition-finding-checkpoint.json`
verifies five records and four exact page-3 text anchors at bytes 1937–2559;
the page SHA-256 is
`0da6ce3883ca66ffee49946f88d1aad1eaf25dc9f818b123810e0890ea038441`.
The general method reference does not establish a new independent experiment
or every panel's conditions. Separate evaluator review of bytes 767–3736
also preserves the runout-iOD definition (OD600 measured 15 minutes after
observed growth arrest), the distinct runout/wash time origins and the actual
acetate treatment. No numerical worksheet or parent report was added by the
finding; the broader method checks are not supplied to the episode.
The child next extracted supplement page 4 at 495 and read it at 496/497.
Evaluator review verified its text SHA-256
`ccc9e094f06e6c0a5cb1d13d58769afc97dcf769aaf346994fbff731fb8989eb`.
The evaluator now retains the actual order of plate averaging, within-replicate
6-hour normalization and across-biological-replicate mean/SEM calculation,
including the shared denominator and approximately 2-hour time bins. The
ampicillin assay uses its own pre-treatment 24-hour denominator. The lag
definition spanning pages 3/4 also uses the plating-based viable fraction,
so it cannot be presumed independent of viability; the authors' day-zero
zero-loss assumption remains an assumption. These are source-based evaluation
checks, not newly extracted numerical operands, model predictions or evidence
that the live assessment/return already preserves these distinctions.
Decisions 499/501 then retained two of these design facts independently: the
6-hour CFU/mL baseline for relative viability, and the three technical plates
averaged within each biological replicate. The
`carbon-viability-normalization-replication-checkpoint.json` verifies seven
saved records, the page-4 hash and all five exact anchors over two source spans.
Both findings qualify the viability hypothesis without discriminating between
the competing biological explanations. They do not add independent experiments
or numerical score operands. The full normalization order, shared-denominator
covariance and viability-dependent lag calculation still need examination in
the eventual numerical assessment and return; no parent report existed at
capture.
At 515/516 the child independently acquired the NCM3722 GenPept protein record
AKO57331.1 and found full-string equality with the supplied 644-residue sequence.
`carbon-ncm3722-reference-sequence-checkpoint.json` retains the operation details,
matched sequence block and original source qualifiers. Evaluator review verified
the record SHA-256
`01222c593cbb634e37f08c944f0f74565c87e4567f864b8384c15281febc8a00`
and reconstructed the sequence from all 65 mapped spans. Its normalized hash
matches the original anonymous input and launch pin. The record identifies
NCM3722, locus AA953_15590 and CP011495.1:3120382..3122316. The separate evaluator
now preserves this positive reference-sequence correspondence instead of
requiring that specific relationship to remain unknown. This does not establish
the actual laboratory construct sequence, independent functional evidence,
numerical scoring or parent delivery; no report existed at capture.
The follow-up at 523/525 acquired WP_020233075.1, which AKO57331.1 cites as a
similar sequence. The RefSeq record has 649 residues and no exact containment
with the 644-residue input. The similarity-qualification checkpoint verifies
the GenPept and normalized-sequence hashes and the two lengths. The evaluator
now distinguishes this annotation/literature lead from the exact NCM3722 match
and retains the need for actual residue correspondence before transferring
mutation coordinates. No alignment or evidence against YeaG function follows
from this difference, and neither record alone verifies a laboratory construct.
At 528 the child retained the RefSeq length as a source annotation and used it
to qualify the older nitrogen-starvation survival hypothesis with
`different_source_subject` and `does_not_discriminate`.
`related-refseq-subject-qualification-finding-checkpoint.json` verifies both
saved records and the exact source quotation at bytes 1583–1895. This demonstrates
use of the distinction in an ordinary scientific finding. Numerical-assessment
revision and parent delivery remain unverified, and the exact AKO57331.1
correspondence remains unchanged.

Decisions 534–536 exposed a separate record-type issue while retaining that
match. A descriptive source subject had no sequence bytes, so the attempted
coordinate-bearing observation was rejected. The child independently acquired
AKO57331.1 through `public.ncbi.sequence`, obtaining a reference with a non-null
`sequence_ref`. The recovery checkpoint verifies the original source hash and
the 644-byte sequence against the anonymous input and launch pin. Its next
observation was rejected for a missing source anchor. The saved
`sequence-reference-acquisition-recovery-checkpoint.json` therefore establishes
acquisition recovery, not a successfully recorded comparison or parent receipt.
The current A106 prompt now explains the distinction between descriptive
source subjects, scanned sequence blocks and sequence-backed references, and
retains the exact-anchor requirement for extracted observations. This is
source-only guidance; the frozen workflow did not receive it. No calculator,
record contract or execution control changed, and no additional workflow ran.

The frozen child subsequently recovered fully at 540/542: it repeated the
literal sequence scan and saved an exact-correspondence observation with both
full-length operand intervals and the original source anchor. The retained
`reference-sequence-correspondence-assessment-checkpoint.json` verifies the
644-residue scan against acquired bytes, the launch hash, the exact source
quotation and the saved records. Its ordinary scope-limited assessment states
`does_not_discriminate` for the viability hypothesis; it has no
`investigation_finding` object and progress credit remains 66. This establishes
recorded reference correspondence after the earlier rejected attempts, while
laboratory-construct identity, numerical-assessment incorporation and parent
delivery remain unverified. The queued prompt clarification was not used.

At 566 the child retained the proteomics sampling hierarchy: one overnight
pre-culture per experiment was split into multiple 10 ml cultures harvested at
different times. The sampling-finding checkpoint verifies three saved records,
both exact anchors, the page-8 text hash and its physical-page provenance.
The finding qualifies the protein-loss hypothesis without discriminating
between explanations. Separate evaluator checks preserve the hierarchy, the
proteomics steady-state time-zero definition and the distinction between
processing groups A/B/C and biological replicate counts. The statement does
not establish one biological replicate for the entire study or numerical
covariance. Numerical-assessment incorporation and parent delivery remain
unverified; no new analysis or independent experiment is claimed.

Decision 569 restated the Figure 4D reuse of Figure 2C wild-type measurements
already retained at 484. The repeated-claim checkpoint verifies both saved
assessments and observations against exact anchors in the same article.
The subject references, predicate and reference-valued object are unchanged;
source-claim context and qualification fields differ, without an equivalence
or replacement link. The configured identity includes those typed fields, so
the investigation-progress increase from 67 to 68 is not evidence of another
measurement or successful numerical deduplication. The evaluator now preserves
that distinction, and the current A106 prompt explains linking an interpreted
or corrected existing claim through the existing equivalence/replacement
fields. No identity, reward or continuation calculation changed. The frozen
workflow has not received this guidance; final duplicate handling and parent
delivery remain unverified.

At 581 the child retained the reported growth rescue by inducible plasmid-borne
YeaG and linked the earlier recovery-lag observation. The
`recovery-plasmid-restoration-finding-checkpoint.json` verifies seven saved
records, all three selected source anchors and the original article hash.
The finding strengthens the lag-phase hypothesis with transfer applicability
and a `different_source_subject` qualification. The evaluator preserves the
comparison direction: the deletion shortened recovery lag, so restoration of
wild-type behavior does not mean faster growth. The statement supplies no
numerical restored lag, uncertainty or fixed prediction. Its source-local
lag-phase term does not merge the recovery and malate experiments. No numerical
assessment revision or parent delivery is established by this finding.

The child subsequently qualified that finding at 589, after an optimistic-
revision conflict at 588. The retained
`recovery-plasmid-restoration-revision-checkpoint.json` verifies the partial
term creation, successful retry, five records, three exact anchors and revision
2 as the current assessment. It keeps the same observation and hypothesis,
explicitly replaces the earlier finding, and uses the paper's broader term
"growth characteristics" with `mixed`/`measurement_does_not_establish_claim`.
The complementation observation remains intact; this qualification does not
supply a particular restored lag or its uncertainty. Progress credit remains
69. This demonstrates an ordinary finding correction, not numerical experiment
deduplication, a new grading sheet or parent delivery. The frozen child used
the existing mechanism without the pending prompt clarification.

The audit now separately inventories ordinary assessment receipts from
`runtime_record_receipts`, including each receiver, first receipt kind,
revision, correction links and whether that exact record is the database's
current revision. It does not promote saved-only revisions to parent receipts,
expand inherited availability or infer interpretation from possession. The
existing failure-inventory test covers traces without these tables, and a new
prepared case distinguishes an old parent receipt from a newer child-only
revision and a saved-only assessment. Both audit cases remain unrun behind the
active workflow. This is audit-source coverage, not a new delivery milestone.

Decisions 595/598/604 retain the Salmonella double-deletion mouse competition
result and both opposing index definitions. The
`competition-scope-direction-findings-checkpoint.json` verifies eight saved
records, five exact source anchors and the article hash. The caption defines
wild-type/mutant and the methods mutant/wild-type, each output divided by input.
The orientation finding links the same source claim as the scope finding;
the methods observation names the same assay. All three ordinary assessments
are `incomparable`/`does_not_discriminate` for the supplied E. coli nitrogen-
starvation hypothesis. This preserves the discrepancy without resolving its
direction, computing an inverse index or supplying variance/predictions. No
new numerical grading sheet, independent experiment or parent delivery is
established by these records. The separate evaluator already checks this
source conflict; its expectations were not supplied to the live episode.

Decisions 614/615/617 acquired the BW25113 reference AIN32220.1, scanned its
original GenPept sequence and saved full equality to the anonymous 644-residue
input. The `bw25113-reference-sequence-checkpoint.json` verifies four records,
both artifact hashes, all 65 mapped sequence spans, the reconstructed ORIGIN
sequence, launch identity and the saved observation anchor. It retains the
BW25113 sub-strain, BW25113_1783 locus, JW1772 synonym and CP009273.1 coding
coordinates. The ordinary assessment is `scope_limited`/`does_not_discriminate`
for the recovery-growth hypothesis; progress credit rises from 72 to 73.
Reference equality does not resolve the paper's conflicting strain labels or
identify the actual laboratory constructs. The separate evaluator now records
this supported correspondence without discarding those limits. The checkpoint
contains only child receipts and zero report attempts; numerical-assessment
incorporation and parent delivery remain unverified. No additional workflow or
scientific calculation ran.

An earlier malate review retained eleven findings covering the MG1655
recipient and separate Keio donor, biological replication, glucose control,
larger SILAC cultures, DctA expression, phosphorylation responses, the separate
AceA assay and the common WT glucose/Lys0 reference. The run's
`malate-methods-findings-checkpoint.json` retains the selected actions and
39 changed records; all 28 source anchors match the retained article bytes,
whose SHA-256 was independently checked. These are saved findings: no grading
or finalization action after decision 167 and no report attempt existed at
capture. A partial assessment rejection at 214 was corrected at 216 using the
retained observation. The audit script now includes detailed errors, partial
validation failures and surviving record references; execution of that change
remains queued behind this workflow. Evaluator-only checks preserve donor versus
recipient, qualitative absence versus numerical zero, direct versus indirect
phosphorylation, and SILAC normalization versus physical sample reuse. They
were not supplied to the live episode and do not establish numerical completion.

The pending runtime correction filters the host-generated interpretation basis
through the same reference resolver used for explicit report values. It retains
the allowed Source and original data references while excluding private request
metadata. A controlled Entrez acquisition/child-return regression is prepared
in `tests/test_report_basis_custody.py`; it has not run while the live workflow
occupies the window. The evaluation audit now inventories report-delivery
attempts, including failures, separately from saved child forms and actual
parent receipts. The live snapshot is unchanged and its failed return has not
been repaired by these working-tree edits.
The parent's decision 7 attempted `redeliver_report` with an `admission_...`
identifier instead of the actual `delivery_ref`; the saved feedback is
`unknown_report_delivery_for_parent`. The current runtime instructions and
operand description now identify `report_deliveries` and
`report_delivery_failure` as the places to copy that exact reference. The
original context already contained the correct reference; this clarification
does not establish that the failed live return was repaired.

The nitrogen follow-up's decisions 20 and 25 queried Source metadata using
experiment reference IDs and received no matches. Inspection confirmed that the
earlier revised assessment still exists (`source_7523e52902450811042eff8e`): its
Source record links original sources, while the experiment identity is inside
its worksheet artifact. This is the query's documented metadata behavior, not
a lost assessment. Current A106 instructions now explain finding the sheet by
its received ID or provider metadata, then reading the experiment/assessment
and revision fields with the existing source readers. The live frozen prompt
is unchanged; use of the clarification remains unverified.
The live child independently recovered at decision 27 by filtering on the
original paper's source ID, which returned five Source records, then read the
existing restoration assessment at decision 28. This confirms that the saved
assessment remains accessible through the existing tools.

Decision 36 exposed a separate reading problem: an arbitrary byte offset inside
a UTF-8 character produced only `source_offset_not_utf8_boundary`. The current
source reader now attaches the enclosing character's byte boundaries and an
explicit retry query when those nearby bytes form a valid character. The
original read still fails, no text is returned in the error, and the caller
chooses whether to make the suggested read. Invalid or truncated UTF-8 yields
no invented boundary. `tests/test_source_window_feedback.py` prepares checks
for two-, three- and four-byte characters in original/text representations,
unchanged failed requests and replay, and malformed bytes. These checks are
pending the live workflow's exit. The frozen child recovered independently
with `source.locate` at decisions 37–38.

At decision 51 the child attempted to revise the original deletion assessment
(`source_9978676397170b71e3fe87ff`) rather than its latest saved revision
(`source_7523e52902450811042eff8e`). The repository correctly rejected this as
`intervention_latest_revision_required`; no revised assessment was saved by
that attempt. Current feedback now identifies the latest sheet only when it
is already received by the caller and within scope. Otherwise the original
failure shape remains unchanged. `tests/test_intervention_revision_feedback.py`
prepares checks through the actual literature binding for correcting a stale
update, preserving old sheets, and withholding an unreceived latest reference.
These checks have not run; the live child retains the original feedback.

The recovery restricted the existing coordinators to one already-permitted CPU,
so their replacement processes inherit the workflow's one-CPU allowance as CPU
affinity as well as a cgroup quota. The replacement coordinator and provider both
report that affinity. No memory/task bound was increased, no research stopping
rule was added, and the frozen application source was not edited. The operational
record is `provider-panic-recovery.json` in the run directory. The provider launch
code now applies this affinity before native startup and records it in
`transport-launch.json`. A stderr reader now preserves the native diagnostic and
surfaces this explicit thread-creation panic as a `ModelCallError`, even if the
provider leaves its RPC pipe open. Silence and elapsed time do not trigger it.
Its subprocess checks use a fixture that emits the captured diagnostic without
creating threads or making model calls; those checks and the affinity checks are
pending the live run's exit. The failure fixture now includes the process-ID
suffix from the observed diagnostic. The pending real startup probe also opens
an ephemeral conversation through `thread/start`, exercising the operation that
failed rather than stopping after `initialize`; it requests no model turn.
Successful subsequent startup supports the recovery but does not by itself
prove that the pending production-code change fixes every thread-exhaustion case.

That attempt also exposed a launcher defect: native PDF requests inherited a
20-GiB default despite the window's enforced 5-GiB memory allowance. Its
`source.pdf.info` request failed preflight with
`native_request_exceeds_environment_bounds`; image acquisition and viewing
succeeded afterward. The launcher now derives native memory and local-capacity
settings from the authenticated workflow environment, and resumption reads the
original saved tool configuration. Verification of this correction is pending
the current workflow's exit; its tests now cover both PDF and spreadsheet
execution. This access failure must remain distinct from
scientifically missing data. The original launcher source is retained with a
hash matching the launch record.
This correction supplies explicit caller settings to the production tool builder
for new A106 evaluation runs. It does not change the package-wide 20-GiB defaults
in `defaults.toml`; other callers still need compatible local resource settings.
The pending native-document checks exercise `build_tools` with those explicit
settings and the real document workers.
The nitrogen follow-up's later PDF page-render request (decision 55) hit the
same frozen memory-request mismatch. The pending tiny-document regression now
covers both PDF metadata and actual page rendering, alongside the spreadsheet
check; these checks remain unrun.
The survival child's later `source.pdf.text` request (decision 37) also failed
with `native_request_exceeds_environment_bounds`, recorded in the
[text-reader preflight inventory](../runs/a106_sequence_case01_20261104_01/pdf-text-preflight-checkpoint.json).
The prepared document regression now includes actual text extraction from a
small PDF containing selectable text, checking its returned text and page
selection under the authenticated workflow memory allowance. All three PDF
operations and the spreadsheet check remain queued behind the live workflow.

The new parent named its final-score field `a106_subscore`. The audit reader has
been corrected to locate final-score fields through each saved return contract;
the field name is chosen by the parent. It preserves the entire receipt history
and separately inventories the latest received revision for each linked chain,
without combining scores. Its focused regression checks are also pending the
current workflow's exit.

A read-only progress audit also found no semantic `assessment` records in the
current run, and zero finding credit for its completed actions. A106 worksheet
assessments are saved `source` records; they do not automatically become the
`assessment.investigation_finding` records counted by the existing progress
policy. The general runtime instructions already expose that reasoning action.
The A106 instructions now explicitly connect useful experimental results and
limitations to those source-bound reasoning records, including equivalence and
correction handling and `changed_assessment_refs` when commissioning a child.
No per-sheet reward, new numerical weight or controller rule was added. The live
run retains its original instructions; autonomous use of this clarification has
not yet been demonstrated.

Further source review found a parent-instruction gap: the reference-evidence
parent renderer selected A105's investigation instructions when its descriptor
identified A106. Both the frozen evaluation source and the pre-correction
working tree had that fallback. The current renderer now selects
`A106_PARENT_TASK`, which describes intervention assessment and finalization,
original-experiment identity, configured dataset analysis and the ordinary
scientific assessments a child should return alongside numerical cells.
`tests/test_a106_parent_prompt.py` checks selection before a child return,
retention of the parent task afterward, and preservation of the A105 default.
These rendering checks remain unrun behind the live workflow. This instruction
correction changes neither the continuation controller nor the numerical score,
and it is not evidence that the live parent has received additional findings.

The case-01 evaluator now separately labels retrospective checks from the
discovered malate-shift paper (PMC8055822). These distinguish growth triplicates
from proteomic duplicates, averaged growth curves from lag-estimate variance,
and the DctA association from a causal intervention. They also check that adding
that interpretation revises the original experiment rather than contributing a
second score. These checks are evaluator-only and were not supplied to the live
investigation; the complete trace audit remains outstanding.

| Case | Evaluation purpose | Current evidence |
| --- | --- | --- |
| 01: 644-aa YeaG | Intervention evidence with unresolved quantitative inputs | Current attempt delivered the first unavailable final and its revision, each with both assessments. A nitrogen follow-up failed during provider startup. The malate child's report failed delivery because the host included a private request reference. The next nitrogen follow-up yielded with empty requested result arrays after a rejected stale revision. The survival child then delivered five assessment/final revisions for one experiment, all scores unavailable. The overall workflow is incomplete |
| 02: 273-aa UppP/BacA | Quantitative intervention/complementation candidate | Parent receipt of two unavailable final results confirmed. Both omit typed assessment selections on the older frozen code; overall workflow is incomplete and no process is running |
| 03: 859-aa NA1000 ClpB | Deposited intervention RNASeq | Input and evaluator prepared using GSE312471 metadata; service run deferred |
| 04: 257-aa B. subtilis YlmH/rqcP2 | Deposited TnSeq and genetic-background comparison | Four single-end archives identified; bounded read prefixes and public pipeline code inspected; full mapping compatibility and service run remain unverified |

The BacA evaluation has now delivered two unavailable final results to its
annotation parent, covering the 2015 complementation experiment alone and a
broader scope including the 2022 compound intervention. Both preserve null scores
and state the absent effect, variance, independent predictions and observation
model; the broader scope also retains unresolved between-experiment dependence.
Neither is a numerical positive. Both final results have empty
`selected_components`, despite saved intervention assessments, because the older
guidance led the episode to use null sheet selections. This older case therefore
does not demonstrate the complete assessment-to-final evidence connection; the
new YeaG receipt described above does retain that connection. The child yielded through
the default controller; no external cutoff was imposed by its launcher. The
overall workflow has no saved completion result and is not currently running.

`tests/audit_a106_workflow.py` inventories actions, failures, numerical publications,
returned forms and recorded parent receipts through a read-only SQLite connection.
It also retains explicit acquisition `failure_code` values when a tool labels
its outcome `partial`. Decision 275 in the live November 5 run exposed this case:
NCBI Entrez reported `acquired=false` and `ncbi_entrez_http_not_success` inside
the result. The audit now inventories that declared failure without treating
every partial data result as a failed action. This correction has source review
and diff checking only; audit execution remains queued behind the live workflow.
Its result summaries retain each scope, unavailable reason and selected assessment
count and revision predecessor, distinguishing a returned form from confirmed parent receipt. Its optional
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

Positive-case review remains open. In the
[crowding-model study](https://pmc.ncbi.nlm.nih.gov/articles/PMC1937523/),
the average crowding coefficient was fitted to wild-type growth measurements;
the paper separately reports deletion-mutant comparisons. Those mutant
comparisons require their own check of calibration separation rather than a
blanket claim that every prediction was fitted to its test result. Figure 1's
error bars describe variation over model parameter sets and cannot supply the
experimental sampling variance. The detailed mutant measurements and their
uncertainty have not been verified from the supplement; no evaluation fixture
or numerical score has been created from this candidate.
The accessible [author copy](https://www.barabasi.com/media/pub_imports/files/222.pdf)
places the reported triplicate means and standard deviations in Figure 2's
mixed-substrate growth experiment. That statement does not establish the
sampling variance of Figure 1's knockout-growth measurements.

The [MOMA study](https://pmc.ncbi.nlm.nih.gov/articles/PMC137552/) supplies
another model-comparison lead. Its PB25 experiment deletes both pyruvate-kinase
genes (`pykA:kan pykF:cat`), and the FBA/MOMA comparison concerns how the metabolic
network responds to that joint intervention. It does not separately attribute
the response to either protein. The models also use measured nutrient uptake
as an input, so the independence and shared normalization of any selected
prediction/measurement pair need checking. These findings concern the PB25
comparison, not every experiment in the paper. No positive fixture or score
has been established from this lead.

The [parallel-glycolysis study](https://doi.org/10.1038/s41589-023-01395-2)
uses iAF1260 FBA for steady growth and separately measures growth acceleration
after nutrient shifts. Its reported FBA setup uses a glucose uptake constraint
from earlier work. A steady-growth prediction cannot supply an expected growth
acceleration. The authors' [public code and data repository](https://github.com/richardlaw517/Parallel_Glycolysis)
identifies figure source data, but a complete pair of numerical hypothesis
predictions and matching experimental uncertainty has not yet been established.
This remains a candidate, not a demonstrated positive.

The [LacI mutation study](https://www.pnas.org/doi/pdf/10.1073/pnas.1907869116)
predicts double-mutant responses from separate single-mutant experiments. It is
a clearer candidate for checking separation of fitting and evaluation. However,
the inspected [Figure 5 script](https://www.rpgroup.caltech.edu/mwc_mutants/code/Chure2019_Fig5_DBL_mutants.py)
generates prediction intervals from parameter samples, not a table of two fixed
expectations. The summary CSV explicitly excludes inference as an intended use;
the separate replicate CSV needs preparation and shared-control checks. The
experimental construct also adds three N-terminal residues, shifting data-file
mutation positions relative to canonical labels. The
[candidate review](../runs/a106_candidate_review_20261105_02/laci-review.md)
records the inspected assets and hashes. No model calculation, evaluation fixture
or numerical score has been produced; this does not resolve the open decision
about calculating missing predictions.

The [Gawand et al. candidate](../runs/a106_gawand_review_20261105_01/review.md)
now has an acquired original PMC archive XML, with its advertised checksum
verified. Table T1 gives delta-pgi growth 0.159 ± 0.001 per hour (SD, three
biological replicates); T2 gives FBA/MOMA/RELATCH growth predictions
0.34/0.65/0.18 per hour. The original grouped headers are preserved. FBA uses
measured mutant uptake; the other models use WT inputs, and RELATCH adds prior
flux and expression data. Later Figure 3 fits add experimental constraints and
cannot supply independent predictions of those same outcomes. A106 can compare
explicit claims about the response to changing a molecule; it does not require
two competing enzyme-function annotations. Reading these published predictions
would use existing values, without adding a prediction calculator. Reinspection
identified a concrete calibration issue: measured WT growth is 0.351 per hour,
while T2 gives WT FBA 0.82, RELATCH 0.35 and MOMA `n.a.`. The MOMA reference FBA
flux must be identified before assigning a WT expectation or attributing the
mutant-model difference to Pgi's contribution. The retained review distinguishes
this issue from simple relative closeness and records a conditional contrast
diagnostic. It also identifies the separate per-hour XML table headers as the
next concrete reader check. No score or positive fixture has been created.
Further original-source inspection identifies a concrete reference mismatch:
T1 reports WT acetate secretion of 3.78 ± 0.90 mmol/gDW/h, and P12 says MOMA
uses WT uptake and acetate secretion as reference inputs. The displayed WT FBA
row in T2 instead predicts zero acetate secretion; the MOMA mutant rows report
3.78. That FBA row therefore does not establish MOMA's reference configuration
or its starting growth rate. The earlier conditional equal-reduction diagnostic
remains unverified. The needed evidence is the actual MOMA reference flux or
complete configuration. Publisher search results advertise supplementary PDF
and XLSX assets, but this review's web requests did not acquire them. No local
conversion, model execution or numerical scoring was performed.
The RNASeq methods also explicitly use only one WT replicate despite biological
duplicates for other strains; this qualification must survive any dataset use.

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
delivery. Autonomous unavailable-score parent delivery with its applicable
assessment selections is now observed in the first yielded YeaG child. Its final
revision preserves the same two experiment identities. The workflow later
delivered the survival and competition assessments, then failed on an oversized
parent model request. A supported numerical positive, dataset-analysis route and complete
paper/dataset duplicate handling remain to be demonstrated. The focused reader,
provider and audit checks above have passed; the oversized parent presentation
has passed focused and retained-request checks. Full autonomous behavior on the
updated code remains to be demonstrated.
Disposable execution evidence belongs beneath a separate directory in `runs/`.
