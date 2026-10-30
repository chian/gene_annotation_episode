# 001 — annotation__next_decision

Boundary: internal root scientific episode. This is a proposed model-facing text template for user steering, not an implementation or a global workflow review. No application, run, policy, or model call was changed.

## Receiver decision

The root chooses the next useful investigation or integrates already received scientific findings into the single annotation of the fixed ybhP/b0790 gene. It needs to distinguish broad family/domain support, molecular activity, physiological role and localization; choose which remaining distinction merits work; and commission that work with a typed return form. Annotation revisions are changes to that one entity, never candidate annotations competing for selection. Child scores are not additive root credit.

The root needs the substance and qualifications of findings it actually received. It does not need a literature child's private history or raw articles, including article text from a root-owned earlier read. Further source examination should be assigned to the appropriate investigation and return the requested scientific distinctions.

## Proposed complete text prompt

The following is the whole proposed message body. Braced headers are renderer fills, not requests for a model to compose summaries. Each row must be assembled from recorded typed fields and resolved semantic labels. Omit inapplicable tables or write their explicit empty state; do not fill missing scientific content by inference. The provider output contract can remain separately typed. An adapter must resolve the semantic names used here to internal operands; that adapter does not currently exist.

---

You own the investigation and integration of the annotation for **{gene name, organism, locus, original input extent}**. The objective is a high-quality, evidence-grounded account of its function and biological role. Preserve useful conclusions, alternatives, qualifications and uncertainty. A unique function or absence of uncertainty is not required.

Choose **one next action** from the available actions below. Use earlier outcomes to revise your approach. You may integrate received findings, commission a scoped iterative investigation, select a permitted operation, or wait on specified pending work. A one-off lookup is an operation. The configured numerical controller governs continuation; do not create a stopping gate, turn budget or prescribed investigation sequence.

### Assignment and limits

| Item | Bound value |
| --- | --- |
| Scientific subject | {fixed original gene; reference proteins and studies are evidence subjects} |
| Scope | {original positions and units; optional assigned restrictions} |
| Required result | {the caller's actual annotation objective and qualifications to retain} |
| Constraints | {applicable caller constraints; available memory/scratch and other binding limits} |
| Existing reusable work | {semantic names of received evidence inventories and completed computations; any limitations} |

### Current annotation of this gene

| Scientific distinction | Current interpretation | Disposition | Evidence bearing on it | Conditions, qualifications and alternatives |
| --- | --- | --- | --- | --- |
| {family/domain, activity, role, localization or structural distinction} | {resolved hypothesis predicate and value} | {recorded disposition} | {semantic names of received assessments} | {their actual source subjects, relevance limits, assumptions and unresolved contrasts} |

{If no annotation has yet been recorded: “No annotation has yet been integrated.” Do not introduce a second annotation entity.}

### Received findings relevant to the next decision

| Finding | Actual source subject and conditions | Recorded proposition or measurement | Relevance to this gene | What this does and does not establish |
| --- | --- | --- | --- | --- |
| {semantic finding name; inherited/new/corrected status} | {organism, protein/construct/sample and recorded conditions} | {typed source claim or measured value with units; source title/accession as attribution} | {recorded target question, assessment relation and qualification} | {recorded limitations, negative findings and competing interpretations} |

{Include a correction that changes the available conclusion even when it reduces support. If a needed linked fact has not been received, say which fact is unavailable. Do not expose an unseen replacement interpretation.}

### What happened in the relevant prior attempts

| Own attempt | Selected work and distinguishing inputs | Actual outcome | Scientific gain on completion | Decision consequence |
| --- | --- | --- | --- | --- |
| {semantic attempt name} | {search question/query, source and section, comparison operands, child goal/scope, or changed interpretation} | {completed/partial/failed/pending; actual returned scientific fact, access failure or unchanged result} | {saved signed gain, or “no completed observation”} | {recorded correction or remaining distinction; “not yet interpreted” when applicable} |

{Include attempts needed to avoid repeating the proposed work and the latest outcome relevant to this choice. Additional own attempts are available on request by semantic work/topic/operand. Requesting them continues this same decision and creates no work observation. Never substitute hashes, database locators or a child's internal attempts for this table.}

### Your own action yields

| Action category | Completed own actions | Total observed yield | Expected yield if completed again | Approximate uncertainty band | Attempts without a completed observation |
| --- | ---: | ---: | --- | --- | ---: |
| {category's readable operation or child-role name} | {count} | {sum of original signed gains} | {value, or unavailable with reason} | {lower to upper, or unavailable} | {count} |

These are this episode's own completed-action observations, excluding inherited credit. Category expectations are conditional on completing that category again; the bands are approximate and uncalibrated. Unavailable is not zero. Acquiring evidence may have zero immediate gain before interpretation. Failed or unexecuted attempts have no completed-action gain.

### Scores and continuation information

| Quantity | Current value and meaning |
| --- | --- |
| Root goal/annotation score | {actual bound value and caller-declared arithmetic and operands; otherwise “Unavailable: no annotation score is bound.”} |
| Scientific investigation progress | {separately bound value and exact meaning; retain distinction from annotation support} |
| Next own-action yield | {current controller expectation and approximate band, with availability} |
| Continuation comparison | {actual configured cost and current comparison result; informational, not a model-selected stopping condition} |
| Monitoring information | {separate received timing-information value only when relevant; not scientific credit} |

Use the bound score meanings exactly. Do not convert a finding count into annotation quality, invent annotation arithmetic, rescale yields, or add a child's local score to this root's score.

### Pending work and execution expectations

| Selected work | Latest received progress | What remains unknown | Relevant duration expectation and support | Bound resource limits |
| --- | --- | --- | --- | --- |
| {semantic work name, or “No pending work”} | {actual received progress, with observation time and measurement meaning} | {unobserved progress, availability or remaining duration} | {compatible expected duration and sample/outcome/censoring support; otherwise unknown} | {actual allocation/constraints} |

{For prospective work under consideration, add its actual permitted configuration and the matching forecast. Distinguish queue wait, execution and turnaround; never transfer timing between workloads without a bound model. Omit unrelated historical execution classes.}

### Available next actions and return requirements

| Action | What you can select | Required operands or requested return |
| --- | --- | --- |
| Integrate received evidence | {permitted annotation/assessment commitment} | {semantic subjects, hypotheses, assessments, conditions and coherent alternatives; required fields only} |
| Commission investigation | {actually available scientific/literature/execution/monitoring roles} | {goal, scope, constraints, initial known context; closed typed fields needed for your later decision and their allowed meanings} |
| Perform an operation | {small relevant set from actual enabled capabilities, plus how to discover another capability} | {operation-specific required operands; unknown availability remains unknown} |
| Wait | {available selected reports/events or reconsideration time} | {explicit selected condition; expected useful information if known} |
| Repair a returned form | {only when an actual delivery failure exists} | {affected semantic work name, exact failed field relationship and permitted repair} |

{Any unavailable branch is stated explicitly; an empty scientific-support library does not create a constructible scientific-process child. There is no compulsory branch order.}

Return the declared typed response selecting one action and its operands. If an earlier own attempt is needed first, request that specific information and continue this decision when it arrives. The host executes selected work. Commit only supported recorded facts and your explicit scientific interpretations. Root has no parent report fields in this assignment; do not invent a report or a completion judgment.

---

## Exact field sources and gaps

| Prompt fill | Actual producer / usable existing path | Required rendering or missing producer |
| --- | --- | --- |
| Fixed objective, subject and scope | `DecisionSource.next`, `request.goal`, `source.scope`; `Store.reasoning_view` subjects | Deduplicate objective/task-context copies. Resolve biological labels, extent and actual constraints. Keep original target fixed. |
| One current annotation | `Store.current_annotations`; `reasoning_view` annotation rows and received revision membership | Render the root's received current integration once. Resolve coherent sets, hypothesis values and assessment meanings. Current received view exposes historical versions; selecting the correct current entity is a required presentation correction. A newer unreceived shared revision must not silently supply new scientific content. |
| Received findings and qualification | `working_state`, episode receipts, typed direct-child forms through `receive_form`; assessments → `investigation_finding`, hypothesis, observation, context and source subject | Resolve only actually received meanings and their linked scientific facts. Existing rows supply propositions and qualifiers; there is no already-built root semantic table. Do not fill missing linked content from arbitrary shared child records. |
| Prior attempt inputs/outcomes | `decision_history.lookup_attempts`, `_record`, `_selected_inputs`; own `runtime_actions` and admitted direct-child forms | Existing lookup preserves selected inputs, status and saved gain. It fingerprints outcome bodies rather than returning their scientific meaning. A factual renderer of relevant own received outcomes is missing; returning fingerprint metadata is inadequate. Child-private histories remain excluded. |
| Own category yields | `decision_history.yield_table`, joined original observation identity and completion order | Already useful: signed completed gains, counts, conditional next-yield estimate, band and unavailable reason. Render a Markdown table without version/status-code internals or unavailable numeric sentinels. Preserve all recorded signs and unknowns. |
| Actual bound progress | `Workflow.source_credit_view`, `source_credit_binding`, `ScientificFindingProgress` | Captured policy computes one configured unit per distinct current retained typed target finding known to this episode. Render that exact meaning as investigation progress, never root annotation quality. |
| Annotation goal credit | `Workflow.annotation_context` only when `project_annotation_score` is bound | The capture has **no annotation score binding or value**. No accepted replacement numeric formula was supplied. This fill must remain explicitly unavailable; the template cannot repair scoring by renaming the finding-count scalar or inventing arithmetic. |
| Controller next yield and cost | `view.controller_state` in `DecisionSource.next` | Present expectation/band, availability and actual cost only. Remove fitting parameters, epoch, diagnostics and duplicate copies. Category estimates never replace the controller estimate. |
| Pending work and progress | `Workflow.pending_work`, controlled child returns and selected progress observations | Present semantic work, actual received state/time, useful progress and unknowns. Empty pending work needs one sentence, not wait-history structures. |
| Prospective duration/resources | `DecisionSource.call`, `execution_expectations`, `job_execution_options`, `ResourceToolEstimator`, native expectation context | Select matching configurations relevant to the contemplated actions; retain duration measure and complete/failed/censored/unmeasured support. Forecasts do not establish availability, submission or science. |
| Actions and typed return needs | `Workflow.action_schema`, `catalog`, enabled episode bindings and actual return contract | Replace the wholesale schema/catalog dump with readable current action and operand rows. Preserve discovery for other available work. Semantic operand mapping and action-aware schema retrieval are proposed gaps, not claimed implemented features. |
| Last outcome / repair | `DecisionSource.last_outcome`, `local_outcome_preview`, feedback and delivery status | Retain concrete outcome, valid partial work and actionable failure. Raw source excerpts stay with the reading investigation. Root receives a source-grounded scientific result or explicitly “not yet interpreted.” |

## Captured evidence for this boundary

The inspected input capture is `annotation_quality_rerun_002/root-context-20261023T152857Z` (inputs and instruction files only). It contains a 458,744-byte bootstrap; 24 of 39 annotation versions, of which 23 shown versions are superseded; raw article XML from a root `source.read` covering bytes 10,000–20,000; large duplicate basis/reference arrays; the complete enabled tool schemas; and technical revision hashes. `providers._SessionConnection.complete` actually puts `json.dumps(context)` in the text input. JSON is therefore the current LLM-facing input, not merely an intermediate representation. `model_snapshot` removes controller score histories and two waiting histories, but otherwise copies the context; delta frames do not resolve the relevance problem.

The capture has no child reports and no pending work. It shows scientific progress **38**, total signed new own yield **18**, and **236** completed own actions. These are observed values from the current retained-finding binding, **not** a redefined annotation score. Example existing category rows to preserve:

| Own category | Completed | Total yield | Next yield | Approximate band | No completed observation |
| --- | ---: | ---: | ---: | --- | ---: |
| Scientific reasoning commitment | 38 | 18 | 0.370303 | 0–1.244667 | 3 |
| Literature search | 19 | 0 | 0.00360018 | 0–0.0147302 | 0 |
| Source reading | 107 | 0 | 0.0000012647 | 0–0.0000422619 | 0 |
| State query | 55 | 0 | 0.000117022 | 0–0.00194650 | 6 |

The full proposed category table also includes the other nine recorded categories. Their next yields are unavailable for insufficient completed actions, including an attempted BLAST search with no completed observation. These values do not estimate failure probability or establish that another reading cannot be useful.

Omit opaque IDs, hashes, versions, frame revisions, database locators, parse/archive bookkeeping, duplicate goal/basis data, old annotation bodies, raw literature, child-private work, unrelated execution classes, fit diagnostics and unselected capability manuals. None changes this receiver's scientific choice. Preserve internal durable identities and original saved inputs outside the prompt. Use readable semantic names for selectable facts/work, resolving them at the host boundary; do not merely prettify opaque IDs into table cells.

## Questions for user steering

1. Does this root-level set of tables contain the scientific distinctions you want the annotation owner to decide, with raw source reading assigned below it?
2. For the root goal-credit row, should it remain explicitly unavailable while the intended annotation-credit arithmetic is specified? There is no accepted replacement formula to insert now.
3. Are the current annotation and received-finding rows sufficient for normal root integration, with a specific own-attempt table supplied when needed, or should a particular additional scientific quantity always be present?

Read for this review: `AGENTS.md`, `GOAL.md`, the complete episode-structure and time-aware-estimation documents; complete `DecisionSource.next`, `call`, decision-exchange/lookup paths; `working_state`, `source_credit_view`, annotation context, catalog/action schema; `Store.reasoning_view`; category/attempt history and immutable exchange storage; provider input construction; progress projection and credit documentation. No tests, external services or model calls were run. The semantic renderer, action narrowing, name-to-operand mapping, new root source-reading ownership and any future score binding remain proposed and unverified.
