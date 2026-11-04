# A108 organism and sample compatibility

Authoritative goal: [A108_GOAL.md](A108_GOAL.md), retained unchanged from the
user's supplied goal text.

The active user goal requires autonomous microbial source discovery, evidence
assessment, the existing compatibility calculations, a claim-bound final A108
result and parent consumption. Full runs must cover capability and coverage,
support, incompatibility, missing context, multiple requirements/alternatives,
and useful literature and database evidence. Expected results stay outside
episode inputs. No targeted tests or externally imposed run cutoffs are used.

## Current full-workflow validation

On 2026-11-04 at 15:31 UTC, after the user approved one rerun's concrete
resource limits, the repaired implementation was frozen and launched as
[full-run-008](../runs/a108_repair_2026-11-04/full-run-008/case_01/launch.json).
It uses the unchanged anonymous case-01 sequence, reusable full-workflow
driver and existing interpreter. Evaluator identities and expectations are
absent from the episode's inputs. The earlier failed coordinator and provider
were stopped and their exit confirmed before launching this run.

The explicitly selected `a108-validation` launcher profile enforces 1 CPU,
3 GiB aggregate RAM, no swap, 128 processes/threads, 24 GiB run storage and
16 GiB per file, with no wall-clock timeout. Actual service and slice settings
were inspected after launch. The default launcher profile is unchanged;
this approval applies to the single rerun. The snapshot includes structured
reference rendering, recoverable partial addresses, question-scope recovery
guidance, numbered ORIGIN parsing and native dictionary-subclass conversion
repairs. These are implementation changes under full-workflow evaluation;
launch alone does not validate them or establish successful numerical scoring.

That launch exposed a provider-ownership error before its children could make
any model calls: a workflow-wide provider lease remained owned by the waiting
parent and rejected each durable child. The [startup failure review](../runs/a108_repair_2026-11-04/provider-startup-failure.md)
preserves the three failed commissions and controlled shutdown. Provider
ownership is now per coordinator, with the entire tree still under the same
single-workflow slot and aggregate budget. The resource description matches
that scope. At 15:36 UTC the same anonymous case was restarted as
[full-run-009](../runs/a108_repair_2026-11-04/full-run-009/case_01/launch.json),
after every process of attempt 008 exited. Its snapshot differs only in
provider ownership and that resource description; no scientific case hints
or decision scripts were introduced. The child has since completed sequence
identity, followed citations and independently acquired the expected primary
paper. See the [live-run evidence and prompt receipts](../runs/a108_repair_2026-11-04/full-run-009/progress.md).
Final scoring remains outstanding.

## Current implementation work

The existing context calculator already combines requirements within a route,
alternative routes and observed contexts. Its selected result answers either
organism capability or sample-context coverage. The implementation retains those
formulas and their qualifications, including logical versus sampling bounds.

`literature.context.populate` now accepts an episode-authored `source_selection`
alongside its existing retained-data route. The direct route binds a received
subject and functional hypothesis to an explicit biological question. Exact
source witnesses support requirement/route meanings, observations and design
interpretations. Native numeric selectors are parsed by existing readers.
Qualitative state relations remain explicitly model-interpreted evidence, and
the existing numerical calculator consumes their declared relation. Custody
validation is not proof that an interpretation is scientifically justified.

`literature.a108.finalize` currently publishes the selected question's existing numerical
answer, with its assertion, subject, scope, source assessment, conclusion,
limitations and revision identity. Multiple sources contribute to the assessed
requirements/contexts; they are not summed as independent paper scores. Final
rows retain logical bounds, nullable point and separate sampling quantities.
This is a scoped compatibility result, not a probability that the annotation is
correct and not W05 annotation credit. Full end-to-end proof remains outstanding.
Whether this scoped compatibility answer is the final A108 subscore, or a
separate experimental-evidence aggregation is required, is an explicit pending
scientific decision. The earlier completion correction in
`REMAINING_EXPERIMENTAL_AXES_COMPLETION.md` does not establish that policy.
Publication under a new name does not resolve it; completion remains open.

The A108-specific literature configuration supplies positive role instructions
to both parent and child and exposes existing NCBI record access in addition to
literature, sequence-identity, experimental database and ordinary source readers.
It does not install new database services or bioinformatics algorithms.

## Existing operations and evidence path

| Need | Available repository operations | Evidence or output |
|---|---|---|
| Supplied-sequence correspondence | `public.literature.sequence_identity`, `source.sequence.scan`, `source.sequence.references`, `public.ncbi.entrez`, `public.ncbi.sequence` | Exact sequence equality, attributed molecular-record identity and organism, citation and cross-reference leads; the Entrez operation retrieves molecular databases, not PubMed/PMC articles |
| Literature discovery and acquisition | `public.literature.search`, `public.literature.read`, `public.ncbi.search`, `public.pmc.versions`, `public.pmc.files`, `public.pmc.asset` | Acquired original sources, separate bibliography metadata with paragraph citation links, and supplement provenance |
| Specialized database evidence | Existing SABIO-RK, BRENDA, BioAssay, ChEMBL and MaveDB `search`/`read` operations, plus BRENDA graph search | Applicable experiments, conditions and source citations; database presence itself supplies no compatibility score |
| Source inspection | `source.read`, `source.locate`, `source.experimental.records`, archive, XLSX and PDF readers, `image.view` | Retained original/text representations, exact spans, table or figure context |
| Requirement and context interpretation | Ordinary reasoning plus `literature.context.populate` with `source_selection` | Claim-bound requirements, routes, context units, native operands and interpretations with witnesses |
| Existing compatibility arithmetic | `literature_context_calculations.populate_context_compatibility` through the context repository | Logical bounds and point where identified; separate conditional sampling bounds |
| Scoped publication | `literature.a108.finalize` | Immutable selected result, claim and scope binding, original assessment, explicit supporting evidence references, limitations and revisions; final scoring-policy decision remains pending |
| Parent delivery | `literature_a108_subscore_cells` in a declared typed child form | Exact admitted saved rows, followed by the parent's own interpretation and use |

This table summarizes the A108 evidence path. The [complete recorded catalog](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-fourth-recovery-tool-map.json)
lists all 72 operations actually offered to the fourth recovery child, with
their exact names and descriptions. Its linked first request retains the full
argument contracts; the [prompt index](../runs/a108_integration_2026-11-03/full-run-007/case_01/prompt-receipts/complete-prompt-index.json)
links each actual first-request prompt and its hash. These are frozen-run
receipts, not a claim that later worktree changes have been exercised.

The inherited population operations also cover source quantities, concentration
windows, comparisons, calibration, validation, assays, rates and replicates,
ratios, coupling, binding, transport, perturbation, structure, reactions,
figures, partners, optical measurements and kinetic/interaction models. They
retain their existing source-experiment meanings. Their availability does not
make their outputs A108 subscores; the scoped A108 path still passes through
the requirement/context assessment and publication above. The catalog is not
limited to `literature.context.populate` and `literature.a108.finalize`.

`knowledge.*` and `launch.instructions.*` retrieve existing instructions;
instruction selection does not grant an additional execution capability or
provide scientific evidence. `episode.credit` reports investigation progress,
and `episode.estimate_wait` concerns waiting. Neither is an A108 compatibility
calculation. Ordinary reasoning and permitted child commissions are separate
episode actions, not additional tools hidden from this catalog.

The [recorded parent catalog](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-parent-tool-map.json)
is separate: it offers the five `shared.*` information request, publication,
resolution, reading and listing operations. The parent commissions literature
children for their source tools. The [parent trace review](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-parent-scope-review.md)
records its actual selections and a rejected form that launched no worker.

The source-selection reader is in `literature_context_source_inputs.py`; native
quantity parsing reuses `literature_context_native_inputs.py`. Witness custody
and exact-byte validation do not establish scientific truth. State relations
remain interpreted propositions, and native number selectors currently require
readings supported by the existing numerical grammar. A reported range must not
be bypassed by silently treating one endpoint as an exact observation.

The A108 role text is in `literature_context_prompt.py`, with parent composition
in `literature_reference_parent_prompt.py` and scoped publication instructions
in `literature_a108_subscore.py`. Full model-facing prompts are retained with
each actual run rather than inferred from these source fragments.

## Validation evidence required

Each completed full run must be reviewed against the independently recorded
expectation: actual source discovery and correspondence; requirement/context
support; interpretation and native operands; physical observation identity;
unchanged calculation; saved final result; admitted child return; and the
parent's use of that result. A tool completion, populated sheet or prose answer
alone does not prove this chain. Scientific interpretation errors and interface
errors both remain failures until diagnosed and addressed.

Reusable driver: `tests/live_a108_workflow.py`. Disposable implementation and
live-run artifacts: `runs/a108_integration_2026-11-03/`. The original user goal is
retained there unchanged in `user-goal.txt`.

Status: initial source-input/final-return wiring implemented; full autonomous
validation and the complete coverage set are not yet demonstrated.

After the user's machine reset, all eleven overlapping A108 workflow processes
were gone without complete workflow results. That concurrency was excessive.
The current `AGENTS.md` requires one local workflow at a time in this Codex
window, following predict, test, inspect the evidence, learn, then choose
the next test. Other windows may run their own separately bounded workflows.
The stable thread ID selects this window's launcher lock and resource boundary;
actual process inspection must also account for legacy workers and surviving
children. Only 007/case_01 was resumed from its saved state, under the original frozen
source, interpreter, driver and controller. The other ten attempts remain
interrupted and preserved. Earlier run observations below are historical;
neither their saved active-state labels nor old process receipts prove liveness.
The reset record and next-test prediction are in
`evaluator/post-reset-and-single-workflow-prediction.json` beneath the run directory.

## Full-run observations so far

`full-run-001/case_01` independently recovered the HucL sequence identity and its
primary publication. Its initial parent commission used a references-only form
after encountering an unregistered numerical return schema. Exact registration
was repaired in the worktree; the active run retains its original snapshot.

`full-run-002/case_02` and `case_03` successfully commissioned the registered
numerical return. The latter's parent nevertheless selected organism capability
although the original caller context requested sample coverage with missing
observations. The parent had received the context reference, but its prompt did
not show the contents. The worktree now presents a faithful bounded preview of
received caller context to the A108 parent and preserves the source handle for
complete reading. Generic role instructions preserve the caller's question when
required observations are missing. The frozen run continues unchanged; whether
its child recovers the original question must be judged from its eventual trace.

These are observed intermediate behaviors and diagnosed interface failures,
not completed scientific validation results. No active run was terminated or
given an external cutoff.

Fresh `full-run-003/case_01` and `case_03` attempts use a snapshot with both
interface repairs and the same unhinted inputs and generic driver. Earlier
attempts continue on their own frozen snapshots. Their eventual results and
these repairs must remain separately attributable in the final comparison.

The fresh missing-context parent's actual commission preserves the requested
sample-coverage question. This demonstrates the commissioning repair, not a
completed assessment or return.

The original capability run reached context population, received
`experimental_experiment_reference_required`, and independently created a new
assay reference. Its first proposed assessment remained scientifically
unresolved; it has not demonstrated the expected capability witness.

The culture-panel attempt reached population with six contexts, but received
`representation_error`. Inspection found that the context publisher copied
579-character paragraph witnesses directly into record labels limited to 512
characters. The worktree now uses the existing kinetic-sheet display convention:
an explicitly marked bounded preview in the label, with the complete unchanged
witness retained in the anchor. Schema-error feedback also retains the field
path and validator keyword instead of discarding them. These repairs are not in
the earlier snapshots. Batch 004 includes them; actual use of a long witness
must be established from its saved assessment rather than inferred from a
successful short-label publication.

The existing `public.literature.read` operation now exposes cited publications
from retained JATS back matter, separately from the acquired article's own
publication identifiers. Paragraph text and its byte projection remain
unchanged. This reader extension supplies discovery leads; it performs no
automatic follow-up or evidence grading. A108 instructions distinguish
attributable primary-abstract observations from metadata-only search hits and
retain the limits of unavailable methods or full text. They also distinguish a
source-supported functional-state witness from unresolved mechanistic details
that are not themselves requirements of the scoped claim.

Evaluator follow-up of the pre-recorded Huc expectation recovered the 2014
whole-cell study's primary abstract, including the strain, MSMEG_2262–2263
identity and reported atmospheric hydrogen oxidation. The original full-text
endpoint failed and the PMC open-access listing contained no copy. These
follow-up evaluator artifacts are under `evaluator/huc-whole-cell-followup*`
and are not episode inputs. The positive expectation has not been replaced by
an unresolved result or by an easier case.

The culture-panel episode subsequently repaired its labels autonomously and
published selected coverage 2/6, with no sampling interval for the descriptive
census. This number is not yet a validated scientific result: its incompatible
aerobic condition is based on absent reported competitive outgrowth, so the
necessary-exclusion interpretation still requires scrutiny. The corrected
missing-context episode published sample-coverage bounds [0,1] with no point,
retaining the missing frame and local observations. Neither publication alone
proves parent receipt or consumption. The worktree role text now explicitly
distinguishes prerequisite evidence from a map of positive assay readouts.

The original `full-run-001/case_01` child yielded under the unchanged controller
after 58 completed actions. Its parent admitted the declared references-only
form, which contains changed-record, assessment and hypothesis references but
no numerical cells. This is successful delivery of that defective contract,
not successful numerical A108 delivery. The parent process remains active.

The bibliography extension has executed in `full-run-004/case_01`: the acquired
2023 article's own three publication identifiers remain separate from 85 cited
publication entries. Those entries include titles, reported identifiers,
bibliography labels and paragraph citation links. The child independently
followed CR4 to the original whole-cell paper, encountered a full-text access
failure, and acquired a different primary whole-cell study. Its first saved
assessment cites supported culture states but leaves `routes` null, so the
existing calculator returns unresolved capability with `routes_unreported`.
This is useful discovery, but it has not yet supplied the expected point result.

The 002/case_03 child has now delivered all five saved numerical components to
its parent. The parent used their bounds and scientific limitations to commission
further work. This demonstrates numerical admission and follow-up use, while
the attempt remains scientifically incorrect for its original caller request:
it still answers organism capability instead of sample coverage.

The same child calculated capability 1 in a revised assessment, but publication
failed because it changed the exact scope text while revising the old question.
The worktree now explains the stable question binding and returns
`a108_revision_question_mismatch` with the changed fields and the two received
question bindings. It retains the original identity rule and numerical formulas.
The source-selection contract also explains that `routes: null` means unknown
route structure, while a single known combination is represented by one explicit
route. Neither repair fills in biological evidence or a route automatically.

Single-experiment assessment metadata is now explicitly optional. An assessment
combining different original experiments uses its claim/question binding while
retaining separate contexts, measurements and sources; it must not attribute the
composite to one contributing assay. These latest contract and prompt repairs
are included in the new batch 005 snapshot and await full-run validation. Earlier
active snapshots retain their original source.

The fresh 004/case_02 attempt preserved the caller's six equally weighted
conditions and census interpretation but returned [0,1] with no point after
finding only limited older evidence. Its long conjunctive searches had not
recovered the pre-recorded primary experiment when it published. This remains
incomplete discovery, not proof that the expected evidence is absent. The
worktree prompt now describes broadening or varying indexed search terms when
a long conjunction misses useful evidence, without naming cases or sources.

Batch 005 starts fresh complete case_01 and case_02 workflows using the same
anonymous inputs, generic driver and original A105 interpreter. Its source
manifest and launch receipts identify the route, revision, composite-identity
and search-guidance changes being evaluated. The two new process identities and
their initial autonomous activity have been verified; nine workflows are live
at the latest recorded inventory. No imposed cutoff or active-run termination
has been introduced.

The primary source actually acquired by 002/case_02 has also been reviewed
against its saved result. It supports the scoped substrate exclusion, but the
reported aerobic absence of competitive outgrowth alone does not justify that
condition's incompatible classification. The evaluator review is retained in
`runs/a108_integration_2026-11-03/evaluator/culture-panel-source-review.json`;
it is not supplied to the episodes and does not manually populate any score.

Batch 005/case_01 has now independently acquired the full 2014 growth/survival
study and saved organism-capability bounds [1,1] with point 1. Its assessment
uses one explicit jointly supported route, retains a species-level whole-cell
claim, and leaves optional single-assay metadata absent. The selected passage
attributes the whole-cell activity to earlier work, so the granularity of that
source attribution remains part of the scientific review. Publication and
parent consumption are not established by the assessment alone. The evaluator
review is `evaluator/positive-case-005-assessment-review.json` beneath the run
directory and is not an episode input.

An older 003/case_01 attempt supplied an empty route array, received the existing
`nonempty_array_required` error, and independently repaired it to one explicit
route on the next population action. The worktree schema now includes
`minItems: 1` for non-null route arrays, matching the existing reader and
calculator contract. No scientific condition or arithmetic changed. This small
schema correction is not present in any already-running snapshot.

The same 005/case_01 assessment was then published at action 22 as
`source_0837d1d135485d9b1d5876ec`, retaining point 1, its whole-cell scope and
source-attribution limits in the five final typed rows. Its parent has not yet
received those rows. Older 003/case_01 and 004/case_01 attempts also published
capability 1 under separate question bindings after their revision failures;
their final scope handling still requires review.

003/case_03 retained the correct unresolved coverage numbers but introduced a
false distinction between the M. smegmatis Huc complex and Hyd1 in its revised
explanation. Retained primary evidence explicitly connects those names and
separately identifies the E. coli comparator called Hyd1. The evaluator's exact
witnesses are in `evaluator/alias-and-comparator-review.json`. The worktree
prompt now requires source-supported name correspondence within organism,
strain, locus, sequence and construct context, with comparator identities kept
separate. This generic instruction has no case identifiers and has not been
exercised in a full run; active snapshots remain unchanged.

005/case_02 later suffered a child-execution failure after a successful
`episode.credit` action. The next prompt attempted to display expanded subject
records inside `subject_refs` as string reference handles, raising an unhashable
dictionary `TypeError`. The parent received the failure and retained partial
record references, then independently commissioned a recovery child. Its main
workflow remained live; that does not imply every child execution succeeded.
The actual diagnostic and operand paths are recorded in
`evaluator/expanded-reference-renderer-failure.json`.

`ReceivedFactDisplay` now recursively preserves structured entries in reference
collections while keeping the existing display for string/null handles. This is
a presentation repair; score and continuation calculations are unchanged. The
read-only inventory now reports child execution failures explicitly alongside
process identity and workflow status. A fresh full culture-panel workflow in
batch 006 uses the same inputs, driver, interpreter and controller, with a frozen
copy of batch 005 plus this repair and the two latest A108 prompt/schema changes.
Its process and root initialization are verified; use of the repaired renderer
and completed scientific validation remain outstanding.

Further actual-run evidence now shows a positive numerical parent return:
004/case_01's child yielded naturally after 58 actions, and the parent admitted
both the earlier unresolved culture scope and the later capability-1 lineage
scope. Its next commission explicitly distinguishes those values and scopes
and asks for their reconciliation under the original claim. This demonstrates
receipt and follow-up use, not a completed final conclusion.

005/case_01 independently acquired the original primary abstract and replaced
its earlier introductory attribution with the reported Hyd1-only whole-cell
witness. Population action 36 and publication action 37 retain point 1 while
preserving the exact original question binding and naming the predecessor.
The primary-revision review is
`evaluator/positive-case-005-primary-revision-review.json`. The full-methods and
caller-sample limitations remain explicit. In parallel, 004/case_02 saved
coverage [1/3,1] with no point after recovering the expected experiment and
retaining two supported and four unresolved conditions. Action 57 subsequently
published that result as an explicit same-question revision; parent use remains
outstanding. See `evaluator/culture-panel-004-publication-review.json`.

Batch 006/case_02 independently saved and published coverage [1/3,1/2] with no
point: two supported conditions, three scoped substrate exclusions and one
unresolved aerobic condition. The same acquired primary source explicitly
distinguishes thiosulfate from the tetrathionate electron acceptor. Its six-unit
census, physiological endpoint, source preparation and strain uncertainty
remain material qualifications. The second declared predicate summarizes the
observed physiological state rather than establishing a necessary oxygen domain.
This is an intermediate scientific result, not completed parent consumption;
see `evaluator/culture-panel-006-publication-review.json`.

005/case_01's child has now yielded naturally and delivered both publications,
including the primary-source revision, in ten complete typed rows. Inspection
of the parent's actual next prompt exposed a presentation defect: the received
rows were grouped as ordinary context components, and the generic renderer
omitted their fixed claim/scope, conclusion, limitations and revision. The next
parent commission described these published results as unfinished context
sheets. The admitted data were intact; their model-facing presentation was not.
`evaluator/a108-publication-display-loss.json` retains the actual form, request,
response and diagnosis without asserting the model's private reasoning.

The worktree renderer now presents those existing A108 publication fields and
exact claim, assessment and predecessor references alongside the original
numbers. It handles both own finalize outcomes and admitted context-family
rows. It changes no scientific definition, calculation, schema or continuation
rule. One fresh complete anonymous positive-case workflow in batch 007 uses
batch 006 plus that single source-file repair, with the same driver, interpreter
and controller. All earlier workflows retained their frozen snapshots. Eleven
workflow processes had been launched before the machine reset; the repaired
parent presentation remains to be exercised by a full return.

The older 003/case_03 workflow independently found the explicit Huc/Hyd1 alias
and replaced its erroneous scientific assessment at action 123. Publication
action 125 then corrected the explanation while preserving coverage [0,1] and
the null point. Parent delivery was not observed before the reset. This snapshot
lacks the newer alias paragraph, so its correction is not evidence that the
prompt change caused the result. See
`evaluator/missing-context-autonomous-alias-correction.json`.

The actual provider-selection inventory reviewed 1,093 saved model responses,
including selections recorded before action validation. Their selected tools,
child roles and requested contracts stayed within the supplied evidence and
A108 operations. This is a trace inventory, not a grader or a claim about
unrecorded future turns. The audit is
`evaluator/provider-selection-scope-inventory.json`.

In the sole resumed 007/case_01 workflow, action 17 saved capability 1 and action
18 published it for the declared mc2155 ambient-air whole-cell scope. The actual
next child model request contains the publication's scope, rationale, conclusion,
all limitations and exact claim/assessment/revision references. This exercises
the own-result presentation repair through the full workflow; it is not a
targeted renderer replay. The child preserves the selected paper's attribution
to earlier whole-cell work and its own phenotypic endpoint limits, then continues
source investigation. Parent delivery and completed workflow validation remain
pending. The actual source, saved result and prompt evidence are linked from
`evaluator/positive-case-007-first-publication-review.json`.

The same episode subsequently acquired the primary study's attributable
abstract, anchored its Hyd1-only whole-cell observation at action 27, and
explicitly revised the publication at action 28. The original question,
assessment and capability point remain unchanged. The revision corrects the
source-access limitation without counting the later representation as another
context unit; it preserves the limits of abstract evidence, complex/whole-cell
identity and the distinction between kinetic parameters and necessary domains.
The new abstract is linked in ordinary investigation records, while the
publication operation still references the original numerical assessment and
its sources. Whether the strengthened evidence remains accessible through the
actual parent return is therefore an open provenance question. See the retained
actions and review in
`evaluator/positive-case-007-primary-revision-review.json`. No additional
workflow was launched for this inspection.

The audit exporter now retains the recorded provider `instructions` field,
which includes the actual incremental-state/history protocol, alongside its
text inputs. Earlier exports used the pre-transformation `model_instructions`
field. Prompt filenames now identify provider and session as well as episode,
preserving the original and resumed parent requests separately. The complete
recorded first-request prompts for 007 are indexed in
`full-run-007/case_01/prompt-receipts/complete-prompt-index.json`; the index links
the unchanged raw requests, their output-schema fields and SHA-256 digests.
The existing partial exports remain preserved. This is an audit-export repair;
it does not change the frozen episode prompt or its execution.

At action 61 the same episode explicitly retained the 2023 paper's statement
that nominal 0% oxygen buffer contained trace oxygen. It treated that
purified-Huc observation as condition-limited and non-discriminating for the
existing whole-cell hypothesis, rather than supplying an oxygen-free cellular
witness. The actual action and source-bound assessment are retained in
`evaluator/positive-case-007-oxygen-scope-review.json`. Final numerical and
parent treatment of the additional evidence remain to be reviewed.

The resumed child's selection audit at 2026-11-03 22:49 UTC contains 92 saved
provider responses: 83 action selections and nine requests for supplied
contracts or its own history. Reviewed selections stayed within the available
literature/database, source-reader, interpretation, context-assessment and
publication operations. This includes selections recorded before validation,
not only successful tool completions. The snapshot and original response paths
are in `evaluator/positive-case-007-selection-review.json` and its linked record
inventory. Later selections and the parent return still require review.

The same full run subsequently retained partner-deletion and complementation
findings from an independently acquired 2019 study. Those findings increased
the existing investigation-progress counter, not the A108 compatibility value.
The actual controller request after action 102 has a predicted marginal-credit
upper bound of 0.06341968762630254 against the unchanged cost of 0.001, and
therefore continues. Publication does not itself end an episode. The distinction
and the new source's whole-cell, gas-saturated assay limits are documented in
`evaluator/positive-case-007-continuation-review.md`, with saved request and action
evidence. Parent delivery, final scientific treatment and final scoring policy
remain open. No controller or frozen running source was changed.

The attempted-operation review now extends through actual provider response
121. The additional 29 selections use literature search/read, source
locate/read and scientific interpretation; none requests additional contracts.
They are retained separately in
`evaluator/positive-case-007-selection-continuation-121.json`, preserving the
earlier 92-response snapshot. Scientific correctness and final parent use are
separate validation questions.

The action-28 publication also exposed missing custody for evidence used only
in its revised explanation. The worktree `literature.a108.finalize` now accepts
optional `supporting_evidence_refs` for received, scoped sources, observations,
assessments and contexts. These references are retained in direct provenance,
typed return metadata and the publication display. The reference schemas use
the existing semantic reference format so the standard receipt traversal can
admit them and their forward dependencies. The existing claim, assessment and
revision handles receive that format as well. This changes no compatibility
operand or calculation and adds no experimental aggregation. Revised operands
still require a revised assessment. Older saved requests and rows remain valid
without fabricated additional evidence. The full-run diagnostic and outstanding
validation are in `evaluator/positive-case-007-publication-provenance-review.md`.
The repair is not in the frozen running 007 snapshot and has not been executed
in a new workflow or targeted test.

The same full run later exposed an exact-source presentation defect at action
313: `source.locate` returned literal line breaks, but the prompt's generic
table renderer displayed them as `<br>`. The episode copied the displayed
excerpt and exact-anchor validation rejected it. The worktree now displays
location results as JSON strings with their original offsets and handles.
Source validation and scoring are unchanged. The actual request, response,
source bytes and subsequent autonomous read are preserved in
`evaluator/positive-case-007-anchor-presentation-review.md`. This repair is
also absent from the frozen running snapshot and awaits full-workflow
validation; no extra workflow or targeted test was launched.

Actions 483 and 576 exposed a repeated identifier-scope error: PubMed article
IDs were passed to the molecular protein-summary operation. The worktree A108
catalog now describes its existing PubMed-only search accurately, explains
article discovery/read operations, and gives the molecular lookup's `ids`
operand a database-identity description. The guidance accepts identifiers from
legitimate supplied context, appropriate search results or explicit source
cross-references. It contains no case identities, publications, expected
answers or forced queries. The clarification is conditional on `a108_context`
and changes no accepted operands, retrieval behavior, receipt or scoring rule.

The actual repeated selections, empty response and review are retained in
`evaluator/positive-case-007-identifier-scope-review.md`. This clarification is
also worktree-only and has not been exercised by the running frozen workflow.
Its rendered catalog and autonomous identifier use require a later full-run
observation; no targeted test or additional workflow was launched.

The original 007 child subsequently failed after `episode.credit` action 698
requested detailed finding rows. The existing expanded-reference-list repair
did not cover typed reference atoms: their `ref` field contained an expanded
semantic record, which `ReceivedFactDisplay.ref` treated as a dictionary key.
The worktree now displays expanded mappings/lists recursively at the shared
reference and identity display boundaries, retaining native handle lookup
for actual handles. This also covers expanded units and relation roles without
changing evidence, credit or compatibility calculations.

The actual payload, traceback, frozen/worktree hashes and autonomous parent
recovery are documented in
`runs/a108_integration_2026-11-03/evaluator/positive-case-007-typed-reference-renderer-failure.md`.
This additional repair remains unvalidated by a full run. The live workflow's
frozen source is unchanged, and its parent started a replacement child only
after the failed child exited. No second test or targeted replay was launched.

The subsequent recovery traces exposed a separate handoff problem: raw source
reads did not give a new child numerical possession of another child's sheet.
One recovery returned an empty A108 array; another recreated a context
assessment but yielded before finalization. The worktree A108 task now explains
owned cells versus exact typed admission, the existing population/finalization
path for retained work, and how to establish the latest publication across
immutable source records and query pages. It preserves the fixed question,
original evidence identities and dependence. No operation, arithmetic,
possession enforcement or continuation policy changed.

The actual second-recovery prompt contained the complete pagination controls;
they were not omitted by the renderer. See
`runs/a108_integration_2026-11-03/evaluator/positive-case-007-empty-recovery-return-review.md`
for the evidence and current limitations. The new recovery instructions are
worktree-only and unvalidated by a full run; subsequent autonomous behavior in
the unchanged frozen workflow is not validation of those instructions.

The third recovery publishes point 1 under a new context-bound hypothesis and
question, omitting the original assessment's unresolved Hyd1 requirement from
its route. It does not revise or explicitly relate that publication to the
original [0,1]/null result. Its parent commission describes finishing the same
question but asks the child to form the assertion/question again and supplies
only the paper and culture context. The exact scopes, records, source selection
and actual prompt are retained in
`runs/a108_integration_2026-11-03/evaluator/positive-case-007-third-recovery-question-review.md`.

The A108-specific parent instructions in `literature_reference_parent_prompt.py`
now explicitly carry the received question binding and retained assessment or
publication sources into recovery commissions. If only retained records are
available, the parent asks the child to recover their question before extending
the assessment. Changed biological questions must be related to the previous
result. This is generic guidance using existing operations, with no case clues,
new scoring rule, automatic semantic-equivalence inference or controller change.
It is worktree-only and remains unvalidated by a full autonomous run. The
single running workflow retains its frozen instructions.

The fourth recovery then populated and published a separate capability-1
question using the primary abstract's Hyd1-only whole-cell experiment. It
reuses the original hypothesis but broadens the scope beyond the earlier
ambient-air culture question, without relating the two publications. The
actual operands, source identity and limits are reviewed in
`runs/a108_integration_2026-11-03/evaluator/positive-case-007-fourth-recovery-publication-review.md`.
Numerical parent delivery remains pending.

The worktree A108 task now explicitly separates the claim's permitted
biological states from an experiment's observed conditions. The latter limit
the witness; they do not alone define the whole organism-capability question.
Question changes still require an explicit explanation. This is generic
interpretation guidance, not a new numerical rule or a case-specific answer,
and has not been exercised by a full run.

The fourth recovery subsequently introduced an incorrect method-absence claim,
then independently corrected its publication at action 75 after locating the
reported method in the retained abstract. It reused assessment 46, whose
question rationale and observation interpretation still contain the old claim.
The finalizer correctly copies that assessment's rationale into the typed rows,
leaving contradictory current metadata despite the corrected limitations.
The linked fourth-recovery review preserves both the error and self-correction.

The worktree task and finalization `source_ref` description now explain this
existing data flow: correcting an assessment's rationale or interpretation
requires populating a corrected assessment before publication, even when its
numerical values remain unchanged. Publication prose accompanies the selected
assessment. No calculation, reference, revision rule or continuation policy
changed. This clarification remains unvalidated and is absent from the running
frozen workflow; the observed self-correction is independent of it.

At actions 76–77, the unchanged frozen workflow then independently corrected
the assessment itself and published that replacement. The question binding,
requirements, routes and selected point remain unchanged; all five new rows
now carry the corrected rationale. The linked review preserves the earlier
contradiction and its complete assessment/publication correction. This resolves
that interpretation inconsistency but still leaves original-question continuity
and numerical parent consumption outstanding.

The fourth recovery subsequently failed after action 204 at the same typed
reference renderer boundary, without delivering a numerical form. Its parent
started a fifth sequential recovery within the sole resumed workflow. The
[failure review](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-typed-reference-renderer-failure.md)
and [fifth-child prompt and identity review](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-fifth-recovery-review.md)
preserve those outcomes. The running frozen implementation remains unchanged.

Inspection of the parent's actual post-failure request also identified a
[recovery-address display gap](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-parent-failure-reference-review.md):
141 retained references, including the saved assessment and publication,
were present in runtime feedback but displayed as unresolved labels without
their handles. The worktree renderer now preserves `partial_record_refs`
as explicit recovery addresses, and A108 parent guidance explains their use
through the child's existing readers. The records still require authorized
reading, interpretation and typed delivery; displaying their addresses does
not admit their contents or assign a score. This repair remains unvalidated
by a full autonomous workflow, along with the earlier renderer and recovery
guidance changes. No additional workflow or targeted replay was run.

The sixth sequential recovery exposed a separate existing source-reader gap:
`source.sequence.scan` missed a complete GenPept ORIGIN sequence because its
lowercase detector required twenty contiguous letters while the record grouped
residues in tens. The worktree reader now recognizes explicitly numbered ORIGIN
blocks with continuous row numbering, retaining byte provenance and the existing
literal comparison rules. It does not relax generic prose recognition or add
an analysis operation. The operation description and result qualification now
explain that the selected GenBank/GenPept window must contain the ORIGIN marker.
The [actual-call diagnosis and diff](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-genpept-sequence-reader-review.md)
record the independent child behavior, format-context limits and expected later
validation. This repair is worktree-only and has not been exercised by a full
workflow; the active frozen implementation remains unchanged.

The seventh child's existing Entrez batch route also exposed a native-document
conversion defect. Biopython retains GenPept structured comments as defaultdict
objects, while the shared plain-to-native helper accepted only exact dicts.
The worktree helper now preserves dict subclasses through its existing member
conversion. The [actual response and static diagnosis](../runs/a108_integration_2026-11-03/evaluator/positive-case-007-genpept-native-mapping-review.md)
record the supported request, retained native bytes, unchanged parsing/scoring
boundaries and the one type-check repair. This change remains unvalidated by
a full workflow and is absent from the live source snapshot.
