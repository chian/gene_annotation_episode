# TASK

Determine whether **{specific evidence or comparison}** supports annotating **{gene, organism}** as **{candidate function}**. Resolve **{the parent's exact biological question}** so the parent can **{the biological judgment this result will inform}**.

Evaluate **{the assigned gene, protein, sequence region or attribution scope}** for **{the precise activity, family relationship, physiological role, localization or other property at issue}**. Address **{included questions}**. Keep **{explicit exclusions}** outside this assignment. Follow **{the parent's full relevant constraints, including actual resource limits and allocations}**.

## Establish what the evidence supports for {gene}

{Full instructions describing what would support or weaken this particular candidate annotation, expressed directly about the named gene and candidate function.}

| Question about {gene} or {candidate function} | Evidence needed | How to interpret that evidence | Limits and qualifications |
| --- | --- | --- | --- |
| {each substantive question in the assigned evidence assessment} | {all relevant evidence requirements} | {complete instructions for relating the observation to the candidate function} | {complete applicability, extent and qualification instructions} |

{All remaining instructions about evaluating this candidate, including the evidence distinctions, misleading cues and boundaries required for this question.}

Distinguish evidence for **{the broad relationship at issue}** from evidence for **{the more specific claim being considered}**. A source's annotation is a reported claim; identify what experiment, comparison or reasoning supports it before applying it to **{gene}**. Keep the measured activity, the organism's physiological role and the proposed annotation separate wherever the evidence establishes different things.

When using a result from another protein, organism, construct or assay, identify the actual subject and conditions. Explain why that result applies to **{gene}**, and retain any differences that limit the inference. A neighborhood association, sequence match or shared domain supports only the conclusions justified by that evidence. Do not turn an inferred target property into a direct measurement of the target.

## Compare the explanations for {gene}

{Full instructions explaining the comparison or reasoning approach for this biological question, including when it is useful.}

| Candidate explanation for {gene} | What it claims | What would distinguish it from the alternatives |
| --- | --- | --- |
| {each actual candidate function or explanation to keep live} | {its complete meaning and conditions} | {the specified distinguishing evidence, when supplied} |

{All instructions for deciding which evidence to obtain, how to compare the explanations and how to revise the judgment. Name the gene, candidate functions, source subjects and comparisons where they matter. Retain the complete reasoning instructions rather than replacing them with an approach name.}

| If the evidence shows… | Consequence for annotating {gene} and the next comparison |
| --- | --- |
| {each specified biological result or condition} | {the full corresponding interpretation and follow-up guidance} |

{All limits on what this reasoning can establish for the candidate annotation.}

Keep distinct candidate functions separate. When evidence changes the assessment of one candidate, update that candidate's existing annotation; its earlier wording is not an additional candidate. Retain negative results, unresolved alternatives and qualifications that affect the conclusion. Examples explaining how to evaluate evidence are instructions; they are not observations about **{gene}**.

## Obtain and assess the next evidence

Choose the next action that can answer **{the unanswered biological question named in the assignment}** using the results available below. Record evidence with its source subject, exact location and conditions. State the inference to **{gene}** separately from the source observation. Record your assessment of **{candidate function}** through the work and return fields assigned by the parent.

| Available action | What it can establish for {gene} | Required inputs and allowed values | Important limits |
| --- | --- | --- | --- |
| {each actually available action or selected tool, once} | {complete relevant description and instructions, grounded in this gene/candidate question} | {exact required and optional fields, types, nested fields and permitted values} | {actual reference, scope and field-relationship constraints} |

If a narrower investigation would help, specify **{gene}**, the precise evidence or comparison it should examine, the relevant supplied facts and constraints, and the exact information to return. Use only the listed capabilities. If a comparison needs a different approach or tools, prepare that alternative using the available action and commission the narrower investigation separately. Follow the returned evidence when deciding how it affects **{candidate function}**.

{When waiting is available and relevant: instructions for selecting a wait for the assigned computation or requested evidence, using the actual permitted conditions. Preserve the distinction between elapsed time, observed progress and a completed result.}

## Return the answer to {the parent's biological question}

Return **{the complete requested biological result and its purpose}**. Preserve the distinction between **{the result-specific distinctions required by the parent}**.

| Exact result field | Type and permitted values | Meaning for this biological question | Required relationships and qualifications |
| --- | --- | --- | --- |
| {every field in the original requested form} | {complete closed field/item/enum constraints} | {full parent-defined meaning, expressed directly about the requested result} | {actual reference meanings, conditions and cross-field constraints} |

Use the supplied output schema to return the existing typed JSON response, including the next action and the required result updates. Keep the exact fields and permitted values. Where a field is supplied from recorded facts, leave its construction to that declared source. Where the response contract permits an information request, use it to obtain the needed prior attempt or result before selecting the next action.

# STEERING

| Evidence relevant to {gene / candidate function} | Actual subject and source location | Received result | Conditions and qualification |
| --- | --- | --- | --- |
| {only relevant initially supplied or subsequently received evidence} | {actual scientific subject, source and exact locator} | {the factual result needed for the next comparison} | {negative result, uncertainty or applicability limit} |

| Candidate annotation for {gene} | Current formulation | Own annotation-support score | Unresolved qualification |
| --- | --- | --- | --- |
| {one meaningful label per distinct candidate} | {current relevant contents once} | {actual candidate-specific score, or unavailable with reason} | {necessary alternative or limitation} |

| Own action category | Completed actions | Total signed yield | Expected next yield, conditional on completion | Uncertainty / availability | Uncompleted attempts |
| --- | ---: | ---: | --- | --- | ---: |
| {actual selected operation or child role} | {actual count} | {saved signed yield excluding inherited baseline} | {existing category estimate or unavailable} | {actual approximate uncalibrated band, status or reason} | {actual count} |

| Latest action / relevant prior attempt | Specific inputs | Actual result or failure | Remaining question / repair |
| --- | --- | --- | --- |
| {own action and meaningful attempt label} | {query, biological subject, source window or configuration} | {recorded status and useful content} | {necessary repair operands or unread information} |

| Returned answer to {delegated biological question} | Requested field | Received value | Qualification |
| --- | --- | --- | --- |
| {directly returned investigation's meaningful question} | {original requested field} | {received value only} | {relevant evidence limits} |

| Running work relevant to {gene / candidate function} | Observed progress and time | Duration estimate and interval | Support / unknowns |
| --- | --- | --- | --- |
| {only relevant work or proposed configuration} | {received state and useful log/status facts with observation time} | {actual estimate or unavailable; measured interval and units} | {relevant sample counts, censoring and lower bounds} |

| Result field needing attention | Current value | Required repair |
| --- | --- | --- |
| {only a field affecting the next response} | {last accepted interpretation} | {actual actionable feedback or none} |

---

## Construction notes — outside the model prompt

This revision preserves revision 002 and applies the user's directness correction throughout. The opening must name the actual biological decision. If the assignment is a different biological question, use the parent's question verbatim instead of forcing it into an evidence-for-function question. Fill the instructions with the actual gene, candidate functions, evidence and comparisons; do not manufacture an annotation candidate merely to populate the template.

TASK is delivered in full on every call, including after a lookup or reconstruction. It contains the detailed assignment and instructions. Initial observations and current findings appear only as concise STEERING facts. Empty optional STEERING tables are omitted. Missing required information says unavailable. No history budget shortens TASK, and no narrative recap expands STEERING.

| Existing source | Destination | Required treatment |
| --- | --- | --- |
| Original child objective, scope, constraints and requested purpose through `prepare_invocation` → `Workflow.build` → `DecisionSource.next` | Direct opening, scope and requested biological answer | Preserve the actual parent question and constraints. Exclude the parent's private task/history/yield and unsupplied source contents. |
| Resolved annotation description, support proposition, operands, qualifications and boundary in `ScientificProcessEpisodes.decision_context` | “Establish what the evidence supports for {gene}” | Preserve every substantive requirement and limitation; express it as a judgment about the assigned gene/candidate. Slot names, operand identifiers and policy routes are not prompt instructions. |
| Resolved thought description, `use_when`, `live_alternatives`, `decision_guidance`, `outcome_contingencies`, `boundary` | “Compare the explanations for {gene}” | Preserve complete instructions and conditions. Instantiate biological subjects and comparisons only from the assignment. Do not pair independent lists or invent follow-up experiments. |
| Effective `Workflow.catalog` and `action_schema`; original `TypedReportContract` | Available actions and result-field tables | Preserve exact actual capabilities, typed fields and result meanings. Existing typed JSON output, independent scientific row admission and return validation remain unchanged. No Markdown-response parser. |
| Explicit initial supplied facts, received working state, latest own outcome and requested direct-child returns | STEERING evidence, candidate and attempt/result tables | Only information this receiver actually received and needs. Referencing a source does not inherit its contents. Separate candidate entities persist across edits; previous revisions are not candidates. |
| `decision_history.yield_table`, saved own observations and existing category expectation; scoped own-attempt lookup | STEERING yield and specific-attempt tables | Preserve signed yield, completion order, uncertainty and unavailable status. No new scoring math or finding-count relabeling. Candidate scores remain unavailable unless an actual producer supplies that candidate's score. |
| Relevant `pending_work`, original duration snapshots, received progress and actionable feedback | STEERING running-work and repair tables | Preserve measured interval, units, observation time and relevant statistical support. Exclude unrelated work, raw histories and fitting diagnostics. |

Host identities, hashes, revisions, custody, session/library fingerprints, transport and validation bookkeeping stay outside the prompt. Scoring-policy and controller implementation details were removed from the model instructions; the existing calculations and continuation behavior are unchanged. Reference presentation must preserve existing typed contracts through the separately reviewed host binding, without exposing opaque tracking values or adding output fields.

Read the appended directness section of `docs/TASK_AND_STEERING.md` for this revision. No application code, tests, model calls, network requests or run state were changed. This remains a print-ready draft for the user's running feedback, not a settled or implemented template.
