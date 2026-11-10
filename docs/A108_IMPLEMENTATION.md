# A108 organism-context evidence

The rebuilt A108 assesses whether proposed protein functions fit the target
organism's physiology, environment, molecular availability and localization.
It starts with supplied material and received evidence, establishes the actual
organism/context, and discovers relevant literature and database sources.
Documented organism physiology in source prose is usable evidence; an assay
curve, concentration measurement or likelihood model is not required.

This implementation follows the user's approved organism-physiology example
and numerical observation-count approach. The earlier assay-copy implementation
and the earlier coverage/bounded-score implementation were removed. Neither
supplies the scientific criteria below.

## Numerical hierarchy

```
source search and acquisition
    -> source-specific reader with retained witnesses
    -> applicable purpose-specific subscoring grader
    -> saved numerical subscoring sheet
    -> selected authenticated numerical cells
    -> main A108 evidence scoring sheet
    -> admitted numerical return to the parent episode
```

This scientific hierarchy uses the existing literature episode role hierarchy
and receipt mechanics. It does not require a separate episode for every grader.
Each child receives the actual contextual question and a typed return requesting
the numerical components its parent needs.

## Purpose-specific subscoring sheets

[literature_a108_grading.py](../gene_annotation_episode/literature_a108_grading.py)
defines eleven graders with distinct source questions and criteria:

| Grader | Biological evidence assessed |
|---|---|
| `physiology_resource_response` | Organism-level resource use and responses, preserving resource role, endpoint and culture context |
| `physiology_metabolic_observation` | Documented organism metabolism, including respiratory, consumption, production and assimilation behavior |
| `environment_ph` | Relevant pH circumstance and compartment, with a supported relation to the proposed role |
| `environment_temperature` | Thermal circumstance, duration and state, distinguishing activity and stability |
| `environment_oxygen_redox` | Actual oxygen/redox property and exposure related to the proposed role |
| `environment_salinity_water` | The particular ionic/water property in its actual compartment and physiological context |
| `substrate_availability` | Actual chemical form, presence/supply and the claimed access scope |
| `cofactor_availability` | Active cofactor form, supply route and access scope |
| `localization_microscopy` | Actual molecule/construct, marker-supported location, spatial resolution and relevant access |
| `localization_fractionation` | Actual preparation, fraction markers, distribution and compartment relationship |
| `localization_curated_observation` | Native organism/molecule identity, evidence origin, location meaning and spatial relationship |

The episode supplies source-supported interpretations for the selected
criteria. These labels are not assigned quality weights. The grader determines
which selected relationships are established or remain unresolved and calculates
counts of their canonical original observations.

Every subscoring sheet has `support_count`, `conflict_count`, `overlap_count`,
`evidence_amount`, `net_support` and `unresolved_count`. For supporting observation
set S and conflicting set C, evidence amount is `|S union C|`, overlap is
`|S intersect C|`, and net support is `|S| - |C|`. Unknown relationships remain
separate. A known finding and an unresolved broader interpretation can coexist.
Predictions and repeated annotation leads do not become observed contextual
evidence merely because a database returned them.

## Sources and identity

[literature_a108_sources.py](../gene_annotation_episode/literature_a108_sources.py)
reads exact literature witnesses and selected native context fields from
UniProt, NCBI GenBank, supplied GenBank metadata and NCBI taxonomy. UniProt
evidence codes and citation links remain paired with their selected comments.
Taxonomic identity alone is not a physiological observation.

[literature_a108_grading_inputs.py](../gene_annotation_episode/literature_a108_grading_inputs.py)
authenticates actual received source selections and original observation
references. Each distinct observation has a source-anchored `literature_result`
reference; distinct findings in the same paper remain distinct. Observation and
assessment records provide evidence rather than alternative counting identities.
A source report and a repeated database representation reuse the original
observation identity. Explicit cross-source origin links require
witnesses. Canonical retained semantics and explicit equivalence identify
repeated observations; the code does not claim to recognize arbitrary
paraphrases or synonyms automatically.

The source catalog uses existing repository literature search/read, exact
sequence-identity discovery, original-source access, UniProt search/record,
NCBI search/sequence/taxonomy and supplied-material metadata operations.
BioSample search supplies discovery leads; this build does not claim a dedicated
BioSample record-fetch or native BV-BRC context parser. No new external provider
or heavy biological algorithm was added.

## Main evidence scoring sheet

[literature_a108_aggregation.py](../gene_annotation_episode/literature_a108_aggregation.py)
accepts explicitly selected, possessed `evidence_amount` cells. It recomputes
the original-observation sets for physiology, environment, availability,
localization and overall. Each domain retains all six counts. An observation
used in two domains contributes once overall. Opposite revisions of the same
observation/claim cannot be selected as independent evidence.

Unavailable domains remain unavailable. Known counts survive alongside exact
unresolved relationships. There is no probability conversion, normalization,
coverage denominator, arbitrary score cap or hidden quality multiplier.

## Episode wiring and prompt

Enable `LiteratureEpisodes(a108_context_evidence=True, ...)`. This is independent
of A105's `rate_population` flag. A108 exposes its own two population operations:
`literature.a108_grading.populate` and `literature.a108.aggregate`.

The corresponding numerical return families are
`literature_a108_grading_cells` and `literature_a108_aggregation_cells`, selected
through `requested_a108_grading_components` and
`requested_a108_aggregation_components`. The source repositories retain the
original selections, saved calculations and exact owned/received component
subsets. The existing common reasoning action retains scientific findings;
parent delivery includes the requested numerical cells and relevant assessed
finding references. Evidence scores and the configured continuation-credit
binding retain separate meanings.

The exact investigation, parent, reading and scoring instructions are in
[literature_a108_prompt.py](../gene_annotation_episode/literature_a108_prompt.py).
The prompt contains no benchmark gene, organism, publication or expected answer.
The permitted common actions are tool use, reasoning, narrower children and
report redelivery; A108 has no wait action or added stopping gate.

## Known workflow defects and execution status

**The A108 build is incomplete.** The old frozen run delivered partial numerical
subscoring and main evidence scoring cells to its parent, then ended with an
operational resource failure. Its received evidence remained unresolved. The
fresh root-assignment test is now active on the subsequent repaired runtime;
its final scientific and lifecycle results remain unverified.

The reusable full-workflow driver is
[live_a108_workflow.py](../tests/live_a108_workflow.py). It accepts raw sequence
bytes and an optional root assignment with organism, proposed function and
biological question. It uses repository model/controller defaults and saves
output under runs/. Evaluator expectations remain separate and are never loaded
into the episode. The reusable [root assignment](../tests/fixtures/a108/root_assignment.json)
supplies *N. europaea* ATCC 19718 and an ammonia monooxygenase alpha-subunit
hypothesis; sample conditions and locus are unspecified. Its
[held-out evaluator](../tests/fixtures/a108/root_assignment_evaluator.json)
requires independently acquired contextual evidence, numerical sheets and actual
root receipt, without prescribing a paper, search or exact score total.
Run through `tools/one_workflow.sh`, one workflow at a time in this window.

Initial source integration and independent review corrected
the numerical receipt namespace and the original-observation identity contract.
Numerical custody is checked at population, component access, aggregation and
receipt. The child source-access guard does not establish a global prohibition
on parent access to saved bytes; parent numerical possession still requires the
actual selected receipt.

The first started sequence-only workflow at
`runs/a108_full_20261105_02` independently acquired exact-sequence records
and citation leads, then exposed a renderer crash on a nested native UniProt
`type` field. The parent received the failure and partial-record addresses and
commissioned follow-up work. Some child model processes also failed to create
threads. No A108 numerical sheet or
successful numerical parent return has yet been observed.

The production renderer now checks that a scientific value's `type` is a
string before interpreting it. Other database JSON remains ordinary nested
data. After repeated renderer crashes prevented scoring, that failed run was
stopped explicitly for this code correction; its trace is retained. The whole
workload was confirmed exited before restarting. The subsequent full workflow was
`runs/a108_full_20261105_03`, using the original snapshot plus only this renderer
fix, the same raw sequence, established environment and resource limits. No
wall-clock or usage timeout was added. In run03, the episode passed the repaired
UniProt stage and retained its function description as a source annotation, not
physiological support. Retained failures show Europe PMC's actual temporary
search-service HTTP 503 and NCBI's HTTP 500 response. The episode tried other
acquisition routes. A secondary child also failed model-provider startup.
The final result is `yielded_with_pending_work`. The parent completed 58 actions,
including 55 empty shared-information polls, and yielded with its first child
still pending. Launcher cleanup then interrupted that child. Its first numerical
population call was rejected for supplying a literature-passage selector for
native UniProt data alongside the valid native selection. Selector instructions
now describe the native route; calculation and source requirements are unchanged.

The shared-information audit found that the root was offered upward requests
without a possible recipient. Current source exposes only actual communication
routes: a specific need or evidence offer goes to the immediate participating
parent, and a response goes to its original active requester. Empty polling,
ancestor-wide broadcasts and automatic generic evidence-availability messages
are removed. Literature retains its requested typed report path. Scientific,
literature and API parent renderers retain compact child completion/failure and
report-delivery status. Metadata supplies no evidence or continuation rule.
See [the communication map](A105_EPISODE_COMMUNICATION.md). These changes have
static source review only; the existing run uses its earlier frozen source.

Aggregate provider admission has a fair workflow-wide queue and releases the
native provider after each model call. The supervisor retains process ownership
until descendants exit after a successful driver return. Process ownership and
the logical episode lifecycle are separate requirements.

Process survival alone does not preserve an episode branch. The parent must
admit the child's typed return, project its own received credit, update its
iterator and report upward. The shared lifecycle repair uses
`owned_child_turn_taking_v2`: ordinary child work remains awaited; an actual
HPC or asynchronous API dependency can suspend its branch and release an
ancestor's iterator to select other useful work. Dependent ancestors retain
their original invocation edges. Numerical yield stops new selection while
owned returns and observations finish. Internal suspension and notification
wakeup supply no action or credit; a selected monitor or wait still receives
its own ordinary progress observation.

The original acquisition remains pending through typed-delivery repair.
Receipt, credit and original action identity stay together, and receiver
release/acknowledgment follows the recorded controller observation. Replay
uses saved outcomes and observations. A later selected acquisition of additional
saved evidence retains its own identity; a repeated representation supplies
no new evidence. Executed failures retain actual received progress, including
zero, in the owning iterator. Decision-source failure preserves already selected
children and returns typed partial-result status.

The durable backend can reconstruct the same lost receiver from its pinned
commission after its accepted-work/receipt checkpoint changes. This retains
original operation identities and does not resubmit scientific work. Persistent
storage or receipt failure remains explicit and unfinished. Earlier histories
require their original pinned implementation. The repair is implemented and
statically reviewed, including generic synchronous/asynchronous delivery,
failed-launch custody and finalization guards. The active frozen run still uses
the earlier lifecycle and does not validate these changes.

Credit belongs to the particular iterator and its decision. The current default
fit uses raw signed credit at immutable real progress-receipt times, with no
minimum history window. Category forecasts use the actual recorded query time;
HPC and practical active-work fits retain their own pending-value and endpoint
contracts. Each iterator's credit and configured cost units remain unchanged.
Missing historical timing remains unavailable. The explicit temporal prior and
replay contract are documented in [Real-time credit fitting](REAL_TIME_CREDIT_FITTING.md).
This implementation has static review only. The earlier proposed universal
credit-per-second conversion remains withdrawn; the current implementation
does not divide credit or cost by time.
Run03's specific SQLite-provider startup cause remains uncertain because the
error omits the underlying OS/SQLite failure.

Run03's service exited and its entire owned cgroup was confirmed empty. No
numerical A108 sheet or parent numerical return was produced. After the source
repairs and review, `runs/a108_full_20261105_04` started from the same raw sequence
and a new frozen snapshot. That run records the earlier
`owned_child_returns_before_close_v1` lifecycle. Its final retained state is
`operational_failure` at 2026-11-05 13:05:25 UTC: `BlockingIOError` while forking
`systemctl` during provider ownership verification.

Run04 saved six subscoring sheets and two main evidence scoring sheets. The
parent received two subscoring deliveries and one main-sheet delivery through
three report attempts. Original root actions 50 and 49 were observed as units
58 and 59; the latter resumed the root iterator, followed by parent reasoning.
The delivered main physiology/overall cells retained zero supporting/conflicting
and one unresolved observation because target organism/context linkage was
unestablished. Other main-sheet domains were unavailable. Thus typed numerical
parent delivery occurred, but a positive contextual fit result and successful
full run were not established. Run04 does not validate the subsequent runtime.

The first root-assignment test started automatically at 2026-11-05 13:05:30 UTC after
run04 released this window's workflow slot. Its launch plan and pinned source
are under `runs/a108_root_assignment_20261105_01_preparation`; active output is
under `runs/a108_root_assignment_20261105_01`. The saved launch confirms supplied
organism/strain and candidate hypothesis, repository controller/model defaults,
and no evaluator input or scripted model decisions. Other Codex windows did not
block this launch. It retrieved biological observations, but its selected sheet
left the supplied organism relationship unresolved and had not reached the
parent before the runtime replacement below. The trace shows the actual
caller assignment was delivered; the child chose not to use it as established
organism context. Fourteen failed HTTP attempts were observed at their original
action identities, providing actual evidence for that repaired accounting path.

The first root-assignment run was stopped to apply the requested runtime
correction, after preserving its complete trace and a consistent database
backup. Its entire workload exited before
`runs/a108_root_assignment_20261105_02` started with the same input and
assignment. The new runtime uses the ownership check that does not fork a helper.
The new service and actual model call are active; scientific success and final
parent delivery remain pending.

The preceding
launch stopped before an episode because the repository `.venv` points at a
Python version different from its installed packages. The later runs reused
the established matching workflow environment and frozen application source.

No successful full-workflow result is claimed. No targeted tests were run.
Repairing the diagnosed defects and demonstrating numerical parent delivery
remain required before the build can be called complete.

The user subsequently required grading to be a mandatory part of processing
relevant evidence. The A108 context and reading instructions now require routing
each relevant observation to its purpose-specific grader, saving a partial sheet
when inputs are missing, and omitting grading only for examined material without
applicable contextual evidence. Acquisition failure and unsupported processing
remain distinct from absence of evidence. Saving a sheet does not depend on cells
being requested for immediate parent delivery. The matching A105 selection and
assay instructions carry the same requirement for relevant experiments. The
existing graders, numerical definitions and sheet persistence are unchanged.

The old paired test was ended to apply this requested rule, preserving its frozen
source, complete traces and pre-replacement checkpoints. It had selected zero
numerical operations in either case. The corrected full A108 test is
`runs/a108_required_grading_20261106_01`; its source differs from the preceding
frozen source in exactly the three instruction files. The sequence, assignment,
driver and model/controller settings are unchanged. Actual transmitted model
requests contain the new rule. One full workflow is running; corrected A105
validation follows it. This establishes prompt delivery, not successful grading
or numerical parent delivery.

On 2026-11-06 the required-grading rule was made executable, beyond the earlier
instruction-only correction. A105/A108 evidence interpretation through `reason`
now couples accepted original-result identities/observations/assessments to the
selected existing purpose-specific grader in the same action and transaction.
Aliases resolve to actual committed records; coverage checks the grader's actual
hypothesis and original observation/experiment identity. Its saved sheet joins
the ordinary receipt/credit path before the iterator observes that action.
Executed grading failures are failed original actions, with no accepted ungraded
assessment; independent acquisitions are preserved. Candidate hypotheses and
entity metadata remain preparatory. Only source-witnessed no-applicable material
can bypass grading; it cannot contain an assessment or annotation conclusion.
Missing scientific operands remain the existing partial/unresolved grader inputs.
This adds no child, wait, queue, stopping gate or credit metric.

The initial text-witness exception does not support retaining a visual-only
no-applicable observation. This is a stated scope limitation, not an inference
that an unavailable figure contains no evidence.

The prompt-only test and its consistent pre-replacement database are retained
under `runs/a108_required_grading_20261106_01`. It attempted the A108 grader twice;
both requests used a literature selector on native UniProt context and were
rejected. No numerical A108 sheet was saved. It was ended to run the requested
code correction, after confirming its owning service and every descendant had
exited. The replacement full test is `runs/a108_required_grading_20261106_02`,
with the same original sequence/assignment and model/controller settings.
Actual numerical scoring and final parent delivery remain unverified.

Full test A10802 exposed a transport defect before any literature action:
embedding the grader's complete argument schema in the reason response schema
exposed `allOf`, which the provider forbids. The boundary now sends grader
arguments as JSON, with the complete standalone contract retained for host
validation after alias resolution, matching the existing tool transport design.
A10802's provider error and trace are retained. Its entire workload exited before
starting the same full case as `runs/a108_required_grading_20261106_03`.
Numerical workflow validation remains pending.

A10803 has now exercised the corrected boundary successfully: literature action8
committed its original localization-result reference, observation and assessment
and synchronously saved `source_c57c822bb5a2a9cfa1352c21` using
`localization_curated_observation`. Its exact native UniProt comment was acquired
by the episode; no source/case hint was added. The automatic sheet reports
support0, conflict0, evidence_amount0 and unresolved1, retaining missing target
context and scientific criteria. The original action then received progress
credit1. This is the first demonstrated coupled grading action, not a positive
biological conclusion or completed main-sheet/parent-return validation. Its
complete action/receipt output is retained in
`runs/a108_required_grading_20261106_03/monitoring/first-coupled-grading.json`.

The first A10803 literature child subsequently returned normally at its
iterator's `yield_stop`: its marginal upper estimate was0.000933391376781208,
below its configured continuation cost0.001. The root's original action1 has an
admitted typed return (failure=null),24 grading cells from four sheet versions
covering two original observations, and two assessed findings. Root action1's
actual controller observation records credit1 before root action3 commissions
the next sequential literature child. The report, original parent observation
and root steering action are retained in A10803/monitoring. This demonstrates
subscoring return/credit custody. The first form requested grading cells rather
than main-sheet cells; no main sheet exists yet, and no positive physiological
count has been established. The root's follow-up remains active.

The second A10803 child exposed an overly strict link check: its action17
included a newly created hypothesis in interpretation_refs, and that hypothesis
was exactly the grader's context_claim_ref. The action was rejected as
required_grading_interpretation_not_in_commit even though the claim was part of
the commit. The working source now permits this actual claim link, while still
requiring every evidence record to be covered and rejecting unrelated or
uncommitted links. Its complete failed action and original credit are retained
in A10803/monitoring/context-claim-link-rejection.json. The frozen live source is
unchanged; its episode can repair the request through the ordinary iterator.
The A105 preparation includes the correction. Full validation of this source
change remains pending; no targeted test was run.

The same frozen-source restriction rejected second-child action27's source
condition, which was the grader's actual source_context_ref. The working helper
now handles the distinction as one rule: core evidence records require their
specific scientific identity/claim binding and complete sheet coverage;
committed supporting records may be linked when they occur in actual typed
reference positions in the grader's authenticated arguments. Quotes and labels
cannot supply those links. Diagnostics identify uncommitted, mismatched or
uncovered refs. No scientific criterion, numerical formula, credit path or
continuation rule changed.

A10803 was ended for this repeated concrete implementation defect, preserving a
consistent state backup, both rejected actions and its admitted first parent
return. All its owned processes exited before the unchanged full case was
restarted as A10804. The new source differs from03 only in
literature_required_grading.py. No full scientific success is claimed for03 or04;
the former did not produce a main evidence score. A105 remains prepared with the
same correction and will run after the A108 workload has completely exited.

A10804 has now exercised the corrected link handling in a real compound action.
Its nested literature_strategy child action28 saved the original physiological
result, observation, assessment, and two linked assertion/context hypotheses,
then saved physiology_metabolic_observation sheet
source_42aee9e12eefc6ea681815ff in the same action. The independently acquired
primary study reports ammonia-oxidation activity of N. europaea ATCC19718 on
floating filters. Both linked hypotheses are real grader inputs; the former
unnecessary rejection did not occur. The sheet remains partial:
support0/conflict0/unresolved1 because this child left the target identity and
context relationship unknown. Its full action is retained in
A10804/monitoring/first-coupled-grading.json. This proves the repaired link path,
not the expected positive physiological relationship, main score, or parent
return. The full investigation remains active.

The A10804 nested strategy child and its literature parent have now both yielded
naturally and delivered admitted typed returns. Each return contains12 grading
cells (two versions of one physiological observation), with no aggregation
cells. Both original child actions have their recorded parent credit0 before
further parent work. The root's next action3 explicitly targets the existing
finding's missing target-context relationship and requests distinct additional
context observations and aggregation. Exact returns, observations and root
steering are retained under A10804/monitoring. Return/credit custody is exercised
through both levels; the positive physiological/main-score outcome remains
unverified, and A105 is still unstarted.

A10804 also exposed a target-scope interpretation problem. The root assignment
provides the organism and strain, and the first literature child read that
caller source, but saved graders treated target context as unknown while
qualifying the unlabelled protein's molecular/sample provenance. The nested
strategy child did not receive the caller source. Its parent then returned the
unresolved finding; the root's next commission again sought sequence-to-organism
provenance. A supplied organism-context question must remain distinct from
proof of an individual protein's origin/function and from unspecified sample
conditions or locus.

The A108 task/handoff instructions now require preserving source-bound supplied
target-context records through question_context_refs before delegation, and
resolving returned gaps with known caller facts. Input descriptions for
target_context_ref, target_identity, target_relationship and identity evidence
state their organism-context meaning. They permit explicit caller context as an
assigned-context operand without counting it as positive biological evidence.
Unknown/conditional identity, conditions and locus remain qualified. Criterion
sets, arithmetic, tools and continuation rules are unchanged. No case identifier,
organism, query, paper or expected result was inserted into these instructions.

A10804 was ended for that concrete scope correction, preserving its complete
state, actual input/grading evidence and admitted two-level returns. Its whole
owned workload exited before the prepared full A105 raw-sequence workflow
started as runs/a105_required_grading_20261106_01. After A105 exits, the same A108
case is prepared as runs/a108_required_grading_20261106_05. That source differs
from04 only in the three A108 task/input-description files. The full scientific
and main-score outcome remains unvalidated; these launches do not complete it.

The first A105 mandatory-grading full run recovered the expected DHFR kinetic
record but failed its first literature source at model decision12. History
reads3,6,11 recursively embedded previous history responses; the provider
reported input_too_large for1335867 characters against its own1048576-character
transport maximum. The root received an admitted partial form/credit0 and
commissioned another child, but the root's actual next request had
last_local_outcome=null and no source failure/cause. The ordinary child credit
callback had saved the journal result without updating the parent's presented
last own outcome.

The shared runtime now presents earlier history-read bodies as references to
original decision indices. Original journal data and direct scientific outcomes
remain exact; no research counter, truncation cap or stopping rule was added.
The normal child credit callback updates/checkpoints the actual own outcome
before the next parent decision. Structured provider input-error metadata is
retained as controlled cause/size fields rather than raw rejected input or
private history. A10501's error, history copies, parent visibility and state
backup remain under its monitoring directory. Its complete workload exited
before the unchanged full case restarts as A10502. A10805's prepared source
includes the same shared repairs. Execution of these repairs remains pending.
