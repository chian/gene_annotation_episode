# 016 — Annotation root → scientific process: initial commission

## Draft prompt for human steering

This is one commission boundary, before the child's first choice. Braced cells are filled from the exact producers and selection rules below; repeated rows expand only for explicitly selected items. The input is text and Markdown tables. The existing structured response and original typed return contract remain unchanged.

---

Investigate **{{child_question}}** for **{{fixed_target_and_original_scope}}**, supporting **{{assigned_annotation_candidate}}**. The parent needs **{{original_report_purpose}}** for its later annotation integration decision.

Each annotation candidate has its own stable global identity across revisions and its own annotation-support score. Compare other annotation candidates only when the parent explicitly assigns that comparison.

| Annotation candidate | Assigned claims | Parent-stated uncertainty | Existing candidate annotation-support score |
| --- | --- | --- | --- |
| {{explicitly_assigned_candidate}} | {{selected_predicates_and_values}} | {{selected_uncertainty}} | {{actual_candidate_score_or_unknown}} |

These cells are the scientific information actually supplied to this child. A citation identifies provenance; it supplies neither source contents nor access.

| Supplied fact or prior interpretation | Actual observed subject | Selected conditions and measured/reported result | Explicit qualification |
| --- | --- | --- | --- |
| {{exact_parent_selected_fact}} | {{actual_subject}} | {{exact_selected_conditions_and_result}} | {{explicit_limit_or_unknown}} |

Use the following problem-solving guidance. It is instruction, not scientific evidence about this target.

| Selected support question | Evidence operands and limits | Thought-pattern alternatives and outcome-sensitive guidance |
| --- | --- | --- |
| {{selected_support_proposition}} | {{selected_support_operands_qualifications_boundary}} | {{selected_thought_live_alternatives_guidance_contingencies_boundary}} |

| Binding constraint | Actual assigned value |
| --- | --- |
| {{explicit_scientific_scope_or_resource_constraint}} | {{bound_value}} |

Choose your next useful action using the actual tools and allowed child investigations below. A child is an available investigation, not a required stage. Use actual outcomes to revise later choices. Retain the selected support question, thought pattern and tool set throughout this episode. The ordinary configured controller owns continuation.

| Available action, callable or child | Purpose | Exact typed operands and permitted values |
| --- | --- | --- |
| {{bound_action_callable_or_allowed_child}} | {{bound_description}} | {{exact_fields_types_allowed_values_and_constraints}} |

Preserve the distinction between the observed source subject and applicability to the target. Useful negative findings and corrections can advance the investigation while lowering annotation support. Annotation-support scores, scientific investigation progress and duration expectations retain their separate meanings.

| Original requested return field | Declared type and allowed values | Parent's original field meaning | Initial interpretation value or recorded-fact owner |
| --- | --- | --- | --- |
| {{original_field_path}} | {{original_contract}} | {{original_description}} | {{original_initial_value_or_fact_source_meaning}} |

Use the existing structured response and the parent's unchanged typed form. Initial interpretation values are starting values, not a new child judgment. Recorded fields come from actual records. Commit interpretations through the existing reasoning action; retain valid partial results and actual limitations.

---

## Exact source → selection → receiving decision

The assigning root must select the facts and comparison question. Infrastructure formats those selected cells and preserves their custody. It does not choose biological context or write a new scientific summary. The selection described here is a proposed input presentation, not an implemented new assignment or output schema.

| Filled input | Authoritative producer | Exact inclusion rule | Child decision enabled |
| --- | --- | --- | --- |
| `child_question` | Selected `episode_child.goal`, preserved by `Workflow.selected` → `prepare_invocation` → `EpisodeGoal.child`. | Include this child's objective once. Do not duplicate the root objective or parent goal record. | Identify the uncertainty to investigate. |
| `fixed_target_and_original_scope` | Parent-selected `scope`, checked by `Store.validate_scope(..., parent_scope=source.scope)`; selected original input identity and any explicitly assigned original-coordinate intervals. | Include assigned target identity, molecule/extent and exact scope restrictions. For this repository's fixed case the target is ybhP/b0790, E. coli K-12 MG1655; the 762 nt/253 aa/P0AAW1 descriptions may be shown only where backed by the selected input/provenance. Do not add reference proteins as targets or display sequence hashes. | Choose work within the fixed target and coordinate bounds. |
| Assigned annotation and comparison rows | The parent's explicit commission context: assigned annotation candidate, selected claims and any explicitly selected competing annotations. Existing hypothesis records can supply exact `predicate`, `value`, subjects and selected conditions. | Always include the assigned annotation; include another annotation only if the parent commissions its comparison. Show each candidate separately. Revisions of one annotation retain the same global identity. Do not infer candidate membership from every annotation visible in shared state. | Understand whether to strengthen a candidate, qualify a claim or distinguish assigned annotations. |
| Candidate annotation score | An already supplied score computed for that exact annotation candidate by its actual bound scorer. | Include only a real candidate-specific value with its scope/meaning; otherwise show `unknown`. The current scope-wide `annotation_context` scalar is not evidence of separate candidate scores and must not be copied to every row. | Assess the assigned candidate using actual support information without inventing a score. |
| Exact selected scientific fact cells | Parent explicitly chooses each fact and its exact field values from recorded input, observation, hypothesis, assessment, context or previously received form. Custody retains the original records outside this prompt. | Each row requires an explicit parent-selected proposition/result, actual observed subject, selected conditions and qualification; missing cells remain unknown. Parent interpretation is marked as interpretation. Include no whole records, old record identifiers, source bodies or unselected neighboring facts. A source being cited or in scope is insufficient. | Select an investigation that can discriminate the assigned claims while respecting known limitations. |
| Source/condition qualifications | Exact selected observation/source-claim fields and parent-selected assessment relation, applicability, conditions, assumptions or finding qualification. | Display only fields the parent explicitly supplies. Host validation may follow references to check custody; that traversal neither supplies the referenced content nor makes it baseline knowledge. Do not fill unknown assay conditions from a source citation. | Distinguish target measurement, transfer, context and incomparable evidence. |
| Support question and operands | `library.resolve(selection.annotation_ref)`: selected entry's `support.proposition`, `operands`, `qualifications`, `boundary`. | Include the selected support body only. Expand operand meanings, observation kinds, predicates, applicability and extent restrictions as instruction. Omit library IDs, hashes and option audit records. | Identify what the support proposition can and cannot establish. |
| Thought guidance | `library.resolve(selection.thought_ref)`: `name`, `description`, `use_when`, `live_alternatives`, `decision_guidance`, `outcome_contingencies`, `boundary`. | Include this selected pattern's actual alternatives and conditional guidance. Do not substitute a tool manual or inject the library's case-study evidence into the scientific-fact table. | Decide how to investigate and how different outcomes could change the approach. |
| Binding constraints | Exact `assignment.constraints`, fixed scope and actual caller-bound resource restrictions applicable to the selected actions. | Include every binding restriction applicable to this commission; omit unrelated configuration. Keep caller-owned limits, allocations and availability. No invented action count, time budget, resource choice or completion gate. Aurora storage/account restrictions apply if Aurora execution is an allowed assigned possibility. | Choose feasible work without changing parent constraints or caller allocation. |
| Actual tools | `assignment.selection.tools` resolved against the frozen `ScientificToolLibrary` and current actual `services.tool_catalog(scope)`; permitted common tools/actions from this binding. | Include only names actually permitted by `catalog`/`common_tool_names`, with their existing descriptions and exact input field types/constraints rendered as table rows. Do not advertise imagined operations or manuals as execution capabilities. Zero selected scientific tools remains a valid selection. | Choose a real operation with valid operands. |
| Allowed child investigations | Actual bound `permitted_common_actions`, available child roles and the existing child commission field schema after caller restrictions. | Show only actual available choices. Preserve original field meanings for job, scope, constraints and typed form. This is a choice set, not child order or required fanout. | Commission a substantive narrower investigation when useful. |
| Prospective timing information, if supplied | Original actual forecast snapshots reaching this role before choice, or exact parent-selected measured facts with their measurement meaning. | Include only configurations relevant to available choices, with actual duration meaning, sample/censoring support and unknown status. No parent yield/history or workload-transfer extrapolation. No fabricated forecast for an unbound role. | Use available duration information without changing who chooses work. |
| Return purpose and field rows | `selection.purpose`, compiled original `schema_json`, `initial_report_json`; `TypedReportContract` and existing `FACT_MEANINGS`/registered source meanings. | Include every original field recursively: path, exact type, required structure, permitted values, original description, initial interpretation or actual fact owner. Do not invent missing meanings or add fields. Preserve separate original `scientific_process_results` fields only if the parent requested them. | Know exactly which scientific information the parent needs for later integration. |

For scientific context, “selected” means an explicit finite, ordered list of fact cells chosen by the assigning parent. Membership is not determined by lexical relevance, the child's scope alone, reachable references, receipt ancestry or a host-generated prose summary. The existing `assignment.context` is an unconstrained object; a fixed representation of those selections is a concrete missing construction input, not an established feature. This report does not install one.

The initial commission supplies facts, instructions and constraints. It grants no implicit read of a cited paper, reference protein record or source artifact. Any actual source-access operand must be explicitly commissioned through an existing authorized typed mechanism; otherwise a later child-selected acquisition/read is required. This report adds no alias-to-reference translation. Where an available tool requires a pre-existing Store reference, its current schema alone does not solve the requirement to omit old opaque identifiers from model input; operand presentation remains an implementation gap.

## Existing useful contracts to preserve

`ScientificProcessEpisodes.prepare_invocation` validates the original objective, scope, return purpose, closed report schema and initial interpretation; `_assignment` validates the selected A/P bodies and actual tool contracts. Selection and invocation are pinned for reconstruction. These are useful host guarantees and should stay outside the rendered scientific instructions.

The original parent form already distinguishes recorded facts from interpretation. `communication.interpretation_schema` removes `x-source` fields from model interpretation; `form_with_facts` fills them from the existing facts. `runtime.action_schema` gives optional existing examples: `interpreted_assessment_refs`, `unresolved_hypothesis_refs`, `changed_annotation_refs`, `interpretation_basis_refs` and `observations_after_report_basis`. The examples do not choose the real parent's fields. Source-bound assessment references retain actual hypothesis, observation, relation and applicability; the report-basis fields preserve the distinction between a prior judgment and later uninterpreted outcomes. No free-text response, second composer or new report schema is proposed here.

The current scientific mother also preserves the original support question, thought pattern and selected tools. Actual tool resolution narrows execution; `process.revise` prepares a separate child alternative. The original process-result source copies per-episode closed quantities when requested; those quantities are not candidate annotation scores and are not summed into a parent score.

## Concrete gaps at this boundary

1. **Whole-assignment presentation.** `scientific_process_episodes.py:314` returns `selection`, a selection digest, the complete `assignment`, support-route binding metadata and child-role metadata. `runtime.py:1120` onward also assembles goal records, controller/configuration, visible record references and other working state. The draft instead needs a deterministic projection of explicitly selected fields. Current `assignment.context` does not define that projection.

2. **Automatic parent knowledge inheritance.** `runtime.py:3403` calls `EpisodeReceipts.bind(child, parent)`. `episode_receipts.py:30` freezes the parent's entire receipt prefix; `selection` walks that lineage. That prefix becomes child knowledge irrespective of explicit `evidence_refs`. It violates the requested selected-facts boundary.

3. **References expand delivery.** `runtime.py:3428` onward receives initial report references and binding `initial_references`; `scientific_process_episodes.py:401` returns all assigned `evidence_refs`. `EpisodeReceipts.receive` recursively follows `store._refs(record)`. Whole referenced records and their dependencies become received even when the parent only supplied a particular fact or citation. Host relationship validation and byte pinning must remain distinct from delivery; forward-reference closure is not an acceptable child baseline.

4. **The inheritance affects both information and credit.** `Workflow.working_state` supplies `receipts.selection` to `Store.reasoning_view`; that view returns up to 24 records per type, not selected fact cells. `Workflow.projection_arguments` and `WorkflowServices.scientific_credit` pass known assessment references into receipt-based projectors. Hiding JSON alone would leave the child credited for unreceived information. Fact selection, received knowledge and the initial baseline must describe the same supplied contribution; this report changes no credit formula.

5. **Custody is currently coupled to inherited-receipt reconstruction.** `commission_child` pins references found in scope, assignment and initial interpretation using `pin_commission_inputs`; that helper records actual versions/byte identities without granting knowledge by itself. `CommissionCoordinator._validate_assignment` and `independent_execution.open_commission` separately require the frozen receipt-inheritance manifest. Correcting selected delivery therefore reaches producer and reconstruction consumers; preserving pins is necessary, but pinning is not delivery.

6. **Actual model input is JSON today.** `providers.py:188` writes host request metadata, then line 201 sends `json.dumps(context)` as the model's text input. A Markdown table stored inside that object would still be wrapped in the unwanted context. The selected projection must be the actual text sent at this boundary. Exact JSON host state and original structured output validation can remain unchanged. No model call is needed to format it.

7. **Candidate identity/score is not supplied by this commission contract.** `_ASSIGNMENT` names selection/evidence/constraints/context, but gives no typed assigned-annotation candidate or separately computed candidate scores. `annotation_context(scope)` projects the scope, not an explicit candidate. The prompt must not represent 24 saved revisions as 24 annotations or place all competing annotations inside one annotation. Candidate identity persists across revisions; competing annotations have separate scores. Values not actually available remain unknown; no mathematical change is proposed.

## Inspection and limits

Read `AGENTS.md`, `GOAL.md`, `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, practical execution directions and `docs/TOOL_KNOWLEDGE.md`. Traced the complete scientific binding, the relevant runtime selected/build/commission/initial-context and receipt-consumer functions, commission coordinator, input pinning, independent worker assignment/reconstruction, working-state projection, existing form implementation, scientific credit adapters, tool resolution and provider input construction. Examined selected library-body structure to distinguish instruction provenance from scientific evidence.

No application edits, tests, network requests, model calls or scientific processes were made. The only write is this review. This is a prompt draft and source trace for human steering, not an implementation or proof of corrected behavior.
