# Signed evidence-axis root

The user authorized combining the axes and then explicitly requested establishing
their scalar mappings first. On 2026-11-09 the user selected signed functional
support where appropriate: an experiment against a claim is information, while
missing homology information is not evidence against the claim.

`SignedEvidenceRootSupport()` scores received proposed annotations, discovered
again at every decision. Each actual subject of each proposed annotation has
its own score. The existing `project_annotation_score` interface remains
available. The multi-annotation root keeps each axis's scientific contribution
separate from the credit earned by a returned child task. It compares competing
annotations without combining their task credits into one scalar.
The existing nonnegative `NativeEvidenceRootCredit` entry point is preserved for
its historical A101–A104 progress profile.

The mapping profile remains `signed_root_axis_scalar_mappings_v1`. The combination
is now `signed_evidence_split_product_v2`: supporting values and opposing
magnitudes are multiplied separately, then opposition is subtracted from support.
These bounded indices and their combination are explicit conventions, not calibrated
probabilities, independent Bayes factors or a proof of molecular function.

| Axis | Native input | Root contribution |
| --- | --- | --- |
| A101 | Existing received sequence-correspondence profile | Preserve the existing value in [0, 1]. A missing result stays unknown; an actual completed zero correspondence remains measured neutral. Neither is negative functional evidence. |
| A102 | Existing qualified comparative-structure profile | Preserve its existing nonnegative value. Experimental geometry remains distinct; this does not replace that profile with a different structural quantity. |
| A103 | Existing qualified gene-context profile | Preserve its existing nonnegative value and original regional attribution. |
| A104 | Existing qualified evolutionary profile | Preserve its existing nonnegative value and original phylogenetic qualification. |
| A105 | Complete current main-sheet `overall`, whose contributors are `source_log_evidence_ratio` | `tanh(overall / 2)`. Apply the transformation after the existing across-experiment sum, retaining positive and negative terms. A native rate, precision or incomplete subtotal is not a substitute. |
| A106 | Complete current claim-bound `experimental_subscore` in natural-log-ratio units | `tanh(experimental_subscore / 2)`. Keep the existing dependence requirements. A partial available subtotal remains partial rather than becoming the final scalar. |
| A107 | Actually received, current qualified omission/addback use | `min(softsign(partner_loss_fraction), softsign(restored_reference_fraction))`, with `softsign(x) = x / (1 + abs(x))`. Both original dimensionless diagnostics and their conditions remain available. |
| A108 | Main-sheet original support/conflict observation unions | `net_support / (1 + evidence_amount)`. Shared observations contribute once to evidence amount; an observation can retain both directional relations. Unresolved observations supply neither support nor opposition. |
| A110 | Actually received, current qualified reaction or resource comparison | Preserve the existing signed dimensionless `reaction_comparison` or `resource_comparison` for the selected component family. Raw energy, atom residuals and resource amounts are not silently converted into support. |

A105/A106 reuse the existing tanh-half-log-ratio convention. A107's signed
softsign/bottleneck and A108's one-observation softening are **new root
conventions**. They do not modify the native graders or their saved scores.
The extra unit in A108's denominator is a fixed saturation convention, not a
measured observation or an asserted Bayesian prior. Its original support,
conflict, overlap, unresolved and evidence-amount counts stay unchanged.

The A107 scalar profile covers the qualified experimental requirement use.
Genomic presence, matched expression and coexpression retain their native
results and per-use qualifications. A reference non-hit, a missing sample link
or an unevaluated expression threshold does not become a negative scalar.
Likewise, the A110 scalar profile covers the existing qualified experimental
comparison families. A balanced supplied equation is not automatically a
positive catalytic-function score. Extending these profiles to additional
computational components requires their particular signed scientific meaning.

Each index carries its exact native inputs, mapping formula, status, missing
operands and provenance. Multiple current final sheets or qualified uses leave
the collection's axis unresolved. Explicit single-proposal mode can select the
intended original sheet/use; the root never selects a favorable maximum or
blends different conditions.
Source-to-target applicability must hold for both supporting and opposing
evidence. An experiment on an unrelated molecule cannot refute the target.
The initial A105 receiving adapter admits the direct-target, original-experiment
link; it leaves transfers unresolved rather than inventing a universal kernel.
Every selected A105 experiment needs current received attribution covering the
candidate view. An A108 score pooled over multiple subjects remains unresolved
for an individual subject because no native per-subject division is defined.

## Product and missing values

For available scalar indices `C_a`, combine positive contributions and the
magnitudes of negative contributions separately:

```
support = product(1 + C_a for C_a > 0) - 1
opposition = product(1 + abs(C_a) for C_a < 0) - 1
H = support - opposition
```

An empty product is 1, so a side with no contributions has total 0. Both totals
are retained even when their difference is zero. Product terms never mix positive
and negative axes. Every opposing term, including a product of two opposing
magnitudes, is subtracted and has negative attribution in the combined score.

The signed axes are in [-1, 1]; the correspondence axes remain in [0, 1].
The root preserves three cases:

| Scientific state | Stored component | Arithmetic |
| --- | --- | --- |
| Unknown or unreceived result | `None`, with missing-input status | Neutral in both totals; never an opposing observation |
| Measured non-discrimination | 0, with measured-neutral status | Neutral in both totals, while retaining the measured datum |
| Valid opposing result | A negative index with original source/claim/scope | Its magnitude contributes to opposition, which is subtracted |

For example, A101 = 0.8 with unknown A106 gives H = 0.8. If A106 instead has
actual log evidence -2, its index is `tanh(-1)`: support is 0.8, opposition is
approximately 0.7616, and H is approximately 0.0384. Two opposing indices -0.5
and -0.5 give opposition 1.25 and H = -1.25. Contributions +0.5 and -0.5 give
support = opposition = 0.5 and H = 0; the nonzero totals preserve the conflict.
The configured nine-axis bounds are [-31, 511], because four axes are
nonnegative and only five can oppose. The generic signed combiner permits all
of its inputs to oppose, with bounds `[-(2**n-1), 2**n-1]` for n axes. This is
an evidence index, not a probability scale.

The functional-support collection has no scalar over different proposed
annotations or genes. The root's separate investigation-progress score is
described below.
Each row contains support, opposition, their difference, the nine-axis vector,
status and missing reasons. An entirely unknown vector has a null score; a
measured zero remains scored. Comparisons group the same actual subject,
original-input region, predicate and declared contexts. They retain exact ties
and unscored candidates separately; unknown candidates do not numerically outrank
negative evidence. The episode retains the annotation decision and next action.

For explicit single-proposal compatibility, supplying `assertion_ref` retains
the earlier length-weighted aggregation of that proposal's separate subject
products. The assigned region is the intersection of the subject's full original
footprint and the caller's fixed scope. Evidence only masks native measurements;
it never reduces this denominator. Derived proteins retain amino-acid coordinates
and their exact recorded nucleotide mapping. No nucleotide/amino-acid averaging
occurs within a native axis calculation.

## Receiving and runtime integration

The reader requires the actual saved receiver identity, original scope and
explicit known-record references. Final numerical cells come from the existing
admitted-cell repositories or the receiving owner's existing automatic main
sheet updates. A handle to a child Source alone cannot reveal its unreturned
cells. A107/A110 inputs come from the original graded per-use publications;
superseded qualifications cannot contribute.

A101–A104 require a current received supporting assessment naming the exact
proposed annotation and observation. The assessment establishes association and
extent, not a numeric weight. A101 selects the authentic tool observation's
native hit; sharing its source file does not select other hits. A102–A104 use
their existing authenticated native measurement or qualified attachment. An
ordinary source-grounded extracted observation can associate such a result with
a proposal; its transcribed measurements never replace the native grade.
Condition and assumption dependencies must be received, and declared
qualifications remain inspectable in paged contribution details. Weakening,
mixed, incomparable, withdrawn and unavailable assessments cannot invent
positive correspondence support or turn absent information into opposition.

An actual received A106 assessment correction retires a final scalar that
depends on the old assessment, even before a replacement final sheet is
returned. Original cells and closed forms remain immutable. A105/A108 reuse
their existing automatic current-sheet projection. Reading the root does not
rerun measurements, graders or source acquisition, and creates no progress.

The runtime now supplies receipt-bound annotation projectors with their actual
receiver identity and receipts at decision, detail-read, closing-form and
summary boundaries. In explicit single-proposal mode the scalar, `annotation_support` and
`annotation_opposition` totals, and nine-element vector enter the ordinary
annotation-support context. The final run summary also retains both totals;
investigation credit still comes from its
separately supplied projector. Restricted roots keep their existing work
boundary and do not acquire general research tools. Collection mode exposes
`proposed_annotations` and `annotation_comparisons` instead of a singular
`annotation_score`, including in available closing report facts.

Callers can pass `SignedEvidenceRootSupport()`
as `project_annotation_score` to `run_workflow`, record its `as_record()` in
`binding_definitions['annotation_score']`, and enable actual episode receipts.
Proposed annotations arise from actual received scientific work; no function
name or proposed annotation ID is required at startup. For direct Workflow construction,
`create_signed_evidence_root_workflow` binds this channel while retaining the
caller's actual progress projector and controller.

The scorer binding is explicit. Existing frozen workflows and their
historical score/controller definitions are not rewritten. A105's separately
confirmed literature cutoff remains 0.075 for its next launch; it is unrelated
to any scalar in this document.

The combined run binds the root directly through `SignedRootEpisodeBinding`.
Its `annotation_support` section records the mapping version and claim
selection. Omitting `assertion_ref` enables the dynamic collection:

```json
{
  "annotation_support": {
    "version": "signed_root_axis_scalar_mappings_v1"
  }
}
```

Empty selections use a unique current
received result for that question; ambiguity stays explicit. A selection maps
an axis name to its intended current numerical-sheet or qualified-use Source.
Explicit `assertion_ref`, `comparison_ref` and `selections` remain available for
single-proposal mode. Global comparison or sheet selections are rejected in
collection mode so one proposal's selection cannot be copied onto all others.

## Task credit and root decisions

The approved root stopping rule is per proposed annotation, native subject,
scope and evidence axis: stop when every pair has an available forecast upper
bound at or below its applicable cutoff. Each forecast concerns another whole
axis invocation. It is fitted from that parent's actual completed invocations;
the child's forecast for its next internal action is not substituted for it.
The root also reports one progress score: sum the earned axis-child credit for
each proposed annotation, then take the highest annotation total. It never sums
credit across competing annotations. This maximum is a progress summary; the
per-pair forecasts and cutoffs still determine when the root stops.

A missing scientific score remains null. It supplies no evidence for or against
the annotation. Root task credit comes from the received child's own closing
credit minus its starting credit. An opposing experiment can therefore reduce
annotation support while earning positive task credit. A completed invocation
that earns no additional task credit supplies a zero credit observation.
Unknown forecasts remain unknown.
The root maximum uses child credits in their declared local units; changing
those units changes this summary, so each arm retains its credit definition.

The root binding enables this through `root_task.kind = "annotation_axis_credit"`
alongside the dynamic `annotation_support` configuration. `root_task.cutoffs`
must explicitly supply A101, A102, A103, A104, A105, A106, A107, A108 and A110.
These cutoffs use the corresponding returned child task's credit units for
another whole axis invocation. They are configured separately from each
child episode's own cutoff. The code does not copy another axis's threshold.
No production root cutoffs or biological calibration are established by the
synthetic checks.

Each child episode binds its own credit calculation, yield estimate, return
rule, and cutoff. Scientific-process tasks select a declared task binding and
check its exact credit definition. Literature tasks save their yield settings
with the original commission; open source discovery and finite requested
answers use different estimates. HPC can bind active and pending job yield
from each saved commission, but its current producers still need to supply
those settings. Ordinary execution and monitoring still need private
continuation bindings. There is no shared investigation policy or implicit
child cutoff.
A101–A104 retain their native measurements, and A107/A110 retain their
finding calculations. A105,
A106 and A108 whole-axis investigations count findings for the assigned
proposed annotation. Literature source leads, reading or screening, and A105
measurement, experiment grading and commissioned assembly use separate local
calculations. The A106 judgment and A108 score refresh are automatic updates,
not episodes commissioned solely to score. The root's per-axis yield cutoffs
remain separate from each child's own forecast and cutoff.

A102 feature geometry and functional contrast now count distinct resolved
received results for the commissioned proposed annotation, including a valid
measured zero. A104 robustness counts assessed resolved comparisons for that
annotation. A102 reference, trait and interface tasks and A104 panel/alignment
preparation still need their own local credit definitions. A101–A104 bounded
quality tasks also need a suitable bounded-improvement forecast.

The ordinary CLI accepts `[genome_investigation]` version
`combined_genome_investigation_v2`, with `root` and `services` tables. The
root table supplies the signed annotation collection, initial received refs,
and its nine axis yield cutoffs. Services supply the source publication,
scientific task bindings, literature setup, execution task bindings, and tool
retrieval. No production root cutoffs have been calibrated for the genome run.

The literature owner already distinguishes 43 requested output families in
`literature_task_selection.py`. Those are result families, not 43 episode roles
or automatically 43 separate credit policies. One child can request several
families and do source reading, grading and aggregation in the same episode.
Its original goal, purpose, assignment and typed return together define the
local task. These scored operations have different scientific meanings:

| Task owner | Result that its credit calculation must inspect |
| --- | --- |
| A105 assay grading | One source-bound experiment, one of eight assay types, nine diagnostic/evidence components and that assay type's required criteria. A negative evidence ratio is still an experimental result. |
| A105 aggregation | Five selected experiment metrics: reliability and validity sum, relevance and attribution max, overall sum. Missing metrics and partial totals stay distinct. |
| A106 intervention grading | The intervention/contrast experiment, required controls, prediction model and nine components, including a source-backed unavailable score. |
| A106 final subscore | Current assessment of each original experiment, plus witnessed independence to combine several signed ratios. A missing assessment differs from an assessed but unavailable ratio. |
| A108 context grading | One of eleven biological graders, original observation identities, qualified support/conflict/unresolved relations and six separate observation-count cells. |
| A108 aggregation | The union of original observations across selected domains; duplicate representations and unresolved relations stay explicit. |

These result contracts are not interchangeable progress units. The confirmed
A105 literature cutoff of 0.075 belongs to its previously replayed credit
unit; the new local task definitions do not inherit it. Search leads require an
acquired source, an anchored subject, an exact witness and a relevance decision;
withdrawal removes the lead's credit. Reading earns one answer to its original
question, and screening earns one witnessed answer while remaining neutral to
annotation support. A105 experiment credit requires a current, applicable
graded assessment; an empty aggregate scaffold earns zero. The measurement
mapping currently covers the reported-quantity reader only. Other measurement
families have no generic credit substitution and remain unconfigured.

`SignedEvidenceRootSupport(task_credit=True)` returns a collection of earned
credits from authenticated typed scientific-process returns. Each return must
include the child's own original credit calculation and starting/closing
values. The collection also retains each annotation's total and the root's
maximum. The numerical owner maintains each pair's estimator and cutoff. The
existing journal, completion and admission paths persist and replay this
collection alongside the separate annotation scores.

Each scientific commission in this mode names its `proposed_annotation_ref`.
The parent must actually have received it, and a root commission must select
exactly one corresponding subject/scope/axis. Descendants inherit that original
annotation; changing it requires returning to the parent that compares
annotations. A101–A104 retain their native task metrics while selecting evidence
for that annotation. A task that explicitly selects the typed-finding metric
counts only that annotation's findings. Process returns retain the annotation
reference.

The root's ordinary decision view contains each arm's credit, expected
additional credit and cutoff, plus compact transfer status. Transfer status is
separate from scalar availability: an established link can still have missing
numerical inputs. Status distinguishes established, unresolved, explicitly
invalid and withdrawn links, with link and needed-reference identities.
Dependencies can be coordinated through the existing shared-information
operations. A changed dependency status or required input resets that pair's
old forecast; a new audit reference alone does not. Child histories, native
measurements and generic completed-work narratives are not automatically
expanded into this root decision view.

The root chooses its next axis iteratively. It is not a sequential pipeline.
Axis-specific measurement selection, applicability and mapping reside in the
existing credit owners, numerical repositories and qualification modules.
`root_axis_receipts` binds their readers to the actual receiver. The single
`LiteratureEpisodes` owner selects its A105/A106/A108 capabilities from the
original commission; the forwarding `AxisLiteratureEpisodes` class is removed.

## Verification scope

The tests use actual native calculators, immutable numerical repositories,
manual admitted-cell APIs and the shared runtime with explicitly synthetic
scientific inputs. They distinguish negative experiments, measured zero and
unknown information; enforce actual receiving ownership; retain original
receipts after revisions; and check that annotation support creates no new
investigation progress. The earlier **70** checks for the original combination passed in
`runs/all_axes_root_final_checks_20261109_02/` (`results.xml` and
`workflow-result.json`, return code 0 with descendant drain confirmed).

For the separate support/opposition combination, **78** focused checks pass in
`runs/split_signed_contributions_checks_20261109_01/` (`results.xml`, 25.42 seconds;
`workflow-result.json`, return code 0 and descendant drain confirmed). These
cover balanced conflict with nonzero totals, negative interaction attribution,
generic and configured bounds, per-target aggregation, and both totals in the
ordinary decision context and final summary. The runtime checks use explicitly
synthetic inputs and scripted decisions. They do not validate the ten-genome
launch path or a biological investigation, and no genome run was started.

For received proposed-annotation association and dynamic collection, the final
**23** focused tests pass in `runs/proposed_annotation_scoring_checks_20261109_04/`
(52.16 seconds, return code 0, descendant drain confirmed). Across the task's
four sequential check runs, **188 distinct tests** were exercised: **184 pass**
and **4 existing failures** reproduce in the isolated baseline copy. Counts use
each test's latest outcome rather than adding overlapping reruns. Retained
JUnit, baseline import paths, source hashes and distinct-test accounting are in
`runs/proposed_annotation_scoring_checks_20261109_02/` and
`runs/proposed_annotation_scoring_review_20261109_01/`.

Native A101 hit selection, published A102 geometry with ordinary extracted
observations, translated-protein coordinates, and an existing A103 native
context fixture exercise the real calculators. A104 interval/status and
A107/A110 subject/region checks use explicitly synthetic receiving-port fixtures.
The ordinary three-decision runtime discovers a proposal, receives its assessment,
updates its score and closes normally. The existing `annotation_score_read`
method is then checked against that saved receiver; this is not a root-selected
detail action, and the restricted root's permissions remain unchanged.

In the earlier scalar-mapping integration, nine broader root-boundary and receipt failures
reproduce in an isolated source copy with only that integration's runtime changes
removed. The identical failure sets are recorded in
`runs/all_axes_root_final_checks_20261109_01/prechange-comparison.json`.
These checks do not constitute a fresh autonomous nine-axis biological
investigation, or complete the deferred per-axis scopes in
[the evidence-axis ledger](EVIDENCE_AXIS_LEDGER.md).
