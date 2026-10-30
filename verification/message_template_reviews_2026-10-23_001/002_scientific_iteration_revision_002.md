# 002 — scientific_process__next_decision — revision 002

## Proposed complete prompt

This is a proposed TEXT INPUT template. Every model dispatch, including a lookup continuation or reconstruction, contains the complete TASK below followed by the separately constructed STEERING. Braces are fill positions, not instructions to serialize their source objects. Existing typed JSON response and parent-return schemas remain unchanged.

---

# TASK

Investigate **{parent-assigned scoped scientific question}** for **{fixed target's biological name and identity}**. The parent requests this investigation to **{purpose of the requested result}**. Your responsibility is to investigate this question, interpret actual evidence, revise your scientific judgments when warranted, and return the information defined below.

Your scientific scope is **{complete assigned subjects, original positions or attribution scope, included question and exclusions}**. Your binding constraints are **{complete parent constraints, caller-owned allocations and actual resource limits relevant to this assignment}**. Supplied scientific context is **{parent-selected initial facts needed to understand the job, with their source subjects, conditions, provenance and limitations}**. A reference retained by the host for validation does not establish that you received the referenced content.

Other proteins, organisms, neighborhoods, assays and studies are evidence about the fixed target, unless the parent explicitly assigned them as targets. Preserve the distinction between what a source reports about its own subject and what can be inferred about this target. Check organism, construct, experimental conditions, sequence/structure correspondence and applicability before transferring a claim. Distinguish family membership, specific activity, physiological role, localization and experimental support. Negative findings, qualifications and corrections can advance the investigation while reducing annotation support. Preserve competing explanations and uncertainty rather than promoting an inherited annotation into an established result.

## Assigned scientific-support problem

**{Selected support name}: {complete selected support proposition}.**

{Complete selected description and support boundary. These are substantive instructions, not a score, a tool list or a verdict on the target.}

| Support operand | Full instruction | Observation kinds / hypothesis predicates | Assessment relation, applicability and extent meanings | Finding qualifications |
| --- | --- | --- | --- | --- |
| {each selected operand's meaningful name} | {complete operand instruction} | {all declared values and their meanings} | {all declared values and their meanings} | {all declared values and their meanings} |

{All selected support qualifications, in full.}

{Where the actual separate annotation policy is known: the relevant observation-kind routes and their declared meanings. Where unavailable: the recorded reason. An unmapped kind has no declared base-axis route in that known policy; unavailable metadata establishes no verdict on the evidence or score.}

## Assigned thought pattern

**{Selected thought-pattern name}.** {Complete selected description.}

**When to use it:** {complete selected use_when instructions}.

**Alternatives to keep live:**

| Alternative | Full meaning and conditions |
| --- | --- |
| {each actual selected alternative} | {complete associated instruction, if supplied} |

**How to decide:**

{All selected decision_guidance instructions, in full, preserving their order and distinctions.}

**How outcomes change the investigation:**

| Observed condition | Full selected consequence or guidance |
| --- | --- |
| {each actual selected outcome contingency's condition} | {complete associated guidance} |

**Limits:** {complete selected boundary}.

The selected support and thought instructions define ways to investigate; their instructional source cases are not evidence about this target. They prescribe no child order or compulsory action sequence. Keep this episode's originally assigned support problem, thought pattern and selected actual tool set. An explicitly selected process-revision preparation can prepare a different thought pattern/tool set for a separately commissioned child; it changes neither this episode's assignment nor its history and starts no child by itself.

## Decisions and actual capabilities

Choose the next useful action within this assignment using information you have actually received. Tool operations obtain or transform evidence; reasoning commits record scientific interpretations. If a child is useful, give it a scoped job, constraints, selected supplied facts and an exact typed return form. Its internal decisions remain its own. Integrate only the information admitted through the requested return. You can explicitly select a supported wait using relevant pending information; elapsed time alone establishes neither progress nor a stall. Timing expectations describe the measured interval and statistical support; they do not choose work or supply scientific credit.

| Actually available action or tool | Full relevant instruction / callable purpose | Exact typed fields, allowed values and relationships | Scope and capability limits |
| --- | --- | --- | --- |
| {each permitted common action} | {full bound instructions for reasoning, child commission, waiting or report repair as applicable} | {actual required/optional fields, nested fields, enums and relationship constraints} | {actual restrictions and permitted child choices} |
| {each selected actual primitive tool, once} | {complete actual callable description and selected instructions needed to use it} | {actual required/optional fields, nested fields, types, enums, ranges and relationship constraints} | {actual callable restrictions} |

These contracts describe only actual available capabilities. Instruction retrieval does not create a callable. Annotations can have distinct competing candidates. Each candidate is a persistent global entity through its revisions and has its own annotation-support score when supplied by the bound scorer. Revising one candidate does not create another candidate, and historical revisions are not additional candidates. Do not substitute a finding count, library focus or another candidate's score for its annotation score.

The configured local controller owns numerical continuation. Its saved signed completed-action gains exclude inherited baseline credit. Category expected yield is conditional on another completion of that category; its approximate working-model band is uncalibrated, not a probability of successful completion. Unavailable is not zero. Acquiring evidence can have zero immediate yield before a later interpretation earns yield. Timing information, annotation support and investigation progress retain their separate declared meanings. This task supplies no new scoring formula, stop action, turn cap or acceptance gate.

## Requested result and existing response contract

The parent needs **{complete requested return purpose}**.

| Exact requested field | Type and permitted values | Complete requested meaning | Reference and cross-field constraints | Source |
| --- | --- | --- | --- | --- |
| {every original form field} | {complete closed type/item/enum constraints} | {full parent-defined meaning} | {actual meaningful relationships and allowed reference meaning} | {recorded host fact / child interpretation} |

Keep this exact form. Recorded fact fields come from the actual records; do not compose substitutes for them. Interpretation fields use the permitted values and must retain qualifications through their declared meanings. A later tool result is not automatically a new scientific judgment. Preserve valid partial work and use specific structured feedback to repair a failed action or form.

Return the **existing typed JSON response required by the supplied output schema**, with its existing selection and report-update contracts. Where the existing decision-exchange protocol permits a context request, use that same typed request contract to retrieve this episode's already received attempts; this continues the same decision and creates no action observation. This text input does not change the output schema or authorize a free-form report. Host validation, scientific row admission and return admission retain their existing responsibilities.

# STEERING

| Received fact / finding | Actual subject and source location | Decision-relevant result | Conditions, applicability and qualification |
| --- | --- | --- | --- |
| {only facts needed for this next decision} | {scientific subject, source name and exact locator} | {actual received content} | {material limits, negative findings and uncertainty} |

| Candidate annotation | Current received formulation | Own annotation-support score | Qualification / unresolved alternative |
| --- | --- | --- | --- |
| {distinct candidate's meaningful label; one row per candidate} | {current decision-relevant content once} | {actual score for this candidate, or unavailable with reason} | {necessary qualification} |

| Latest action / relevant specific attempt | Actual discriminating inputs | Recorded status and useful result | Repair or unread information |
| --- | --- | --- | --- |
| {own action category and meaningful attempt label} | {specific query, subject, source window or configuration} | {completed/partial/failed/invalid/pending and actual outcome} | {actionable failure operands or explicit unread page} |

| Own action category | Completed observations | Total observed signed yield | Expected next yield | Uncertainty / availability | Attempts without a completed observation |
| --- | ---: | ---: | --- | --- | ---: |
| {actual selected operation or child role} | {actual count} | {saved signed gain total} | {existing conditional category estimate or unavailable} | {actual lower/upper band, status or recorded reason} | {actual count} |

| Current local quantity | Actual value | Declared meaning / uncertainty |
| --- | --- | --- |
| {local scientific credit / actual continuation estimate and cost; only when relevant} | {actual bound value or unavailable} | {actual binding meaning and estimate status; no replacement formula} |

| Admitted child result | Requested field | Received value | Necessary qualification |
| --- | --- | --- | --- |
| {direct child's semantic job label} | {original requested field} | {admitted value only} | {material limits or affected evidence} |

| Relevant pending work / proposed configuration | Received state or progress and observation time | Duration expectation / interval | Statistical support / limits |
| --- | --- | --- | --- |
| {only work affecting this next choice} | {actual received state, useful log/status facts} | {actual expectation or unavailable; actual measured interval and units} | {counts, censoring, lower bounds and unknowns as needed} |

| Requested interpretation field | Current admitted value | Necessary repair |
| --- | --- | --- |
| {only fields affecting the next update} | {last admitted value} | {actual validation feedback or none} |

---

## Exact fill and boundary trace

| Block | Existing producer → this receiver | Construction rule |
| --- | --- | --- |
| TASK: assignment | `Workflow.selected` → `ScientificProcessEpisodes.prepare_invocation`/`_assignment` → `Workflow.build` → `DecisionSource.next` | Child objective/scope/constraints, explicitly selected initial facts and original return purpose. No parent's private task/history/yield/source access. |
| TASK: support | `ScientificProcessEpisodes.decision_context`: resolved annotation `description` and complete `support`; `WorkflowServices.scientific_support_routes` | Render all selected proposition, operands, qualifications and boundary. Routes describe only the known actual separate policy. No invented axes, weighting or score. |
| TASK: thought | Same method: resolved `description`, `use_when`, `live_alternatives`, `decision_guidance`, `outcome_contingencies`, `boundary` | Render complete substantive instructions every call. Keep independent lists separate rather than inventing pairings. |
| TASK: capabilities and result | Effective `Workflow.catalog`/`action_schema`, selected `ScientificProcessEpisodes.catalog`, original `TypedReportContract` | Human-readable complete field meanings and relevant tool instructions. Keep existing output schema, independent scientific admission, `apply_response`, `validate_report` and `form_with_facts`. |
| STEERING: scientific state and outcomes | `Workflow.working_state` → receipt-selected `Store.reasoning_view`; `local_outcome_preview`; admitted `EpisodeView.child_reports` | Only received decision-relevant facts, result contents and material qualifications. No source inventory or automatic all-source inheritance. Distinct candidate rows retain identity across edits; per-candidate scores stay unavailable unless an actual bound producer supplies them. |
| STEERING: yield and specific attempts | `decision_history.yield_table` → saved `_observations`/`_expectation`; `lookup_attempts` and selected-input detail | Own saved signed gains/completion order only. Use existing expectation and band. Specific inputs distinguish repetitions; a fingerprint is not an outcome. |
| STEERING: pending, time, repairs | `DecisionSource.next/call`, original duration snapshots, `pending_work`, received progress, `feedback`, `report_values` | Include only what affects this choice. Preserve interval meanings and unknowns; no fit diagnostics or raw waiting histories. |
| Every dispatch | `DecisionSource.call`/`exchange_decision` → provider input | Build full TASK plus newly selected STEERING even after lookup/reconstruction. Freeze original dispatched input for replay. Do not rely on an earlier chat turn or a delta retaining the TASK. |

Omit host IDs, hashes, revisions, state-frame/session/library fingerprints, transport/configuration objects, parent yields, private child histories and unrelated stored records from both blocks. Retain them internally for identity, custody, recovery and validation. Required reference addressing must remain compatible with the existing typed schemas through a separately reviewed host presentation binding; this draft does not add schema fields or Markdown-response parsing.

## Corrections and review status

This new file preserves the original draft and supersedes its text-response proposal and one-annotation-per-subject wording. Input becomes text; existing typed JSON output and closed parent forms remain. Multiple candidate annotations may coexist, each persistent through its own revisions with its own actually supplied score. No candidate-scoring formula or unsupported per-candidate value is proposed.

The original path trace and inspection remain the basis for this revision. `docs/TASK_AND_STEERING.md` and the new `AGENTS.md` addendum were read for this correction. No application code, tests, model calls, network requests, run state or inventory were changed. This is a draft for the user's running feedback, not a settled template or implementation authorization.
