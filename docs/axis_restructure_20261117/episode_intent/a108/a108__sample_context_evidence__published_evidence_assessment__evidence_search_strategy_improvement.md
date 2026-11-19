# A108 evidence_search_strategy_improvement (role `literature_strategy`)

Source: `git show HEAD:gene_annotation_episode/episodic_workflow/root/a108/sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/<file>` at 97308b94c. Only this folder's own files and its `grading/` and `scoring/` subfolders were read. Child episode folders were not read.

Binding class `LiteratureEpisode`, which mixes in `LiteratureConfiguration, LiteratureBindingRecord, LiteratureAssignment, LiteratureGoal, LiteratureOperations, LiteratureSummary, LiteratureScientificRecords, LiteratureReferences, LiteratureReport, LiteratureReceivedEvidence, LiteratureCredit, LiteratureWaiting, LiteratureYield, ContextualInterpretation, ContextualSubscoring, ContextualMainSheet`. Fields:
- `binding_path = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'`
- `commissioning_parent = 'sample_context_evidence/published_evidence_assessment'`
- `roles = ('literature_strategy',)`
- `entry_roles = ()`
- `decision_source_type = LiteratureTask`
- `decision_prompt_renderer = render_literature_experimental_prompt`

Binding record version `literature_episode_binding_v1`. Binding doc: "Private A108 organism and sample context episode binding."

## What this episode is for (its goal, in its own words)

- Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_strategy']`): "Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination."
- Module doc (`source_contracts.py`): "This binding supplies operands, available ordinary operations, source custody, and the commissioned task's private yield binding when selected. The ordinary Episode loop owns decisions, reasoning commits, commissioning and report updates. In particular, a reading selection is information for an investigation, never a script that this binding executes."
- `LiteratureGoal.instructions` = the role instruction + `A108_CONTEXT_TASK` + `A108_READING_TASK`. The last two come from the old shared `a108.library.literature_a108_prompt`, which was not read.
- `planning_context` is shown as `literature_goal_plan` when the assignment carries `literature_task`. It holds `{objective, proposed_annotation_ref, commissioned_result, progress_definition: credit_projector.as_record(), planning_question: instructions}`.

In short: it works out which search approach is productive for the parent's question, keeping the information objective apart from literal provider queries. It revises terms and sources from actual search/read outcomes and can commission a source relevance assessment child. It answers one commissioned literature task.

## Task and instructions

- `task.py` / `task_decision.py` / `task_state.py` hold the old decision source `LiteratureTask(LiteratureTaskState, LiteratureTaskDecision)`. Most of it is old-runner machinery. Its own intent:
  - A reason commit that is entirely empty is rejected. The exceptions are `no_applicable_evidence` and a `source_lead` for a leads task (`reasoning_has_task_content`).
  - A reason action runs the binding's `execute_reasoning` (the grading-coupled path) before plain `commit_reasoning`.
  - Failed or invalid executed outcomes still enter the iterator with their credit.
  - A model failure ends the episode with `source_failed`.
  - A redelivery must keep `report_update`.
  - There is no wait branch: waiting is not offered.
  - Decisions go to the provider through `complete_with_presentation(..., prompt_renderer=render_literature_experimental_prompt)` when the provider is the original model class (`decision_completion`), otherwise through plain `complete`. This literature-specific prompt rendering is this episode's own intent.
- `task_instructions.py` builds the instructions from the base INSTRUCTIONS, the specialist instructions, REASONING_COMMIT_REQUIREMENT, tool knowledge, launch instructions, the pending_child_delivery repair text and the decision-exchange history replacement. The wait and native-event branches are `pass`.

## What it reads from its parent's assignment (`from_parent.py`)

Assignment form `{version: strategy_assignment_v1, question_context_refs[], prior_search_refs[]}` plus:
- `literature_task` (`goal.task_schema`, anyOf). Each case has `version literature_local_task_v1`, `evidence_axis A108`, `credit_unit > 0`, and optional `yield_settings{kind ∈ accumulation/remaining_commissioned_credit, cutoff ≥ 0, uncertainty_alpha ∈ (0,1)}`. The cases are:
  - `{kind: verified_source_leads}`
  - `{kind: source_answer, answer_kind: assessment, source_refs[≥1]}`
  - `{kind: source_answer, answer_kind: screening, examined[{source_ref, artifact_ref, start, end}]}`

  The model is told: "Select only a task whose typed result is requested by the original return contract. A108 score computation is automatic work, not an episode-credit task."
- `proposed_annotation_ref`.
- The requested A108 grading components and the requested aggregation components. Their names and enums come from the grading/aggregation storage `REQUESTED`/`COMPONENTS`.

Rules:
- Under `private_yield_binding`, `literature_task` and `proposed_annotation_ref` are required. `prepare_assignment` writes `credit_unit` and `yield_settings` from this binding's declared `_yield_bindings[task_key]` and rejects supplied values that differ (`literature_task_supplied_yield_binding_mismatch`).
- Every `*_refs` value must be in scope. `question_context_refs` may be any kind; the others must be sources.
- The child's `proposed_annotation_ref` must equal the parent's.
- `commissioned_task` also checks:
  - the finite unit;
  - that the request's `episode_assignment` equals the assignment;
  - that the return form carries the task's x-source (`literature_source_lead_dispositions`, `changed_assessment_refs` or `literature_screening_answers`) and the selected components;
  - that screening spans have `end > start`;
  - that a task stays within an assigned `page` source and artifact, when a page is present.

## Children it may commission

| Child role | Child episode | What it sends | What it takes back |
|---|---|---|---|
| `literature_search` | `source_relevance_assessment` | Scope inside this scope. The expanded return form must contain each required return source exactly once, and the initial report must be valid against its interpretation schema. The role must be allowed (`_CHILDREN['literature_strategy']`). The assignment comes from the child binding's `prepare_assignment(...)` applied to `selection.assignment` (the child's own form, with the literature_task and requested components). | Typed form admitted and received: the refs in the form plus `received_form_references`. That function stores every grading/aggregation cell row in the form in this episode's repositories (`receive_cells`) and adds the cell record refs. It also collects `literature_source_lead_dispositions` rows, which count toward this episode's own leads credit. The receipt kind is `child_form` / `report_redelivery`. |

## Decision state and what it shows the model (`decision_inputs.py`, `decision_presentation.py`, `internal_summary.py`)

The base context has the same fields as the head:
- goal, scope, working_state, visible_record_refs, current_credit, current_evidence_vector, investigation_progress;
- credit_binding, time_accounting, pending_work, last_local_outcome, feedback, visual_evidence, report_deliveries;
- controller, controller_binding, tools, tool_knowledge, job_episode_options, available_report_facts, requested_report_purpose/form, current_report_update/basis;
- annotation context, monitoring credit;
- `completed_action_reports`, which is skipped when `literature_completed_work` is present;
- the decision yield table.

The binding's own decision context adds:
- `literature_assignment` and `literature_source_custody` (version, artifact/text/stdout/stderr refs, parent_source_refs) for the page source or the `source_refs`;
- `own_literature_outcomes`: own outcomes of the acquisition and read tools, first page of size `outcome_page_size`, default 8;
- `literature_history_meaning`: "Own outcome metadata only. Read exact previous outcomes together through episode.history with view=records and selected decision_indices. Source delivery does not establish understanding, absence or resolved science.";
- `literature_examined_source_inputs`;
- `literature_experimental_work` = `{literature_experimental_task_v1, aspect source_experimental_evidence, evidence_axis A108}`;
- `literature_received_fact_display` (records of received reference/term/context/observation/hypothesis/assessment refs, plus source metadata);
- `literature_owned_population_sources` and `literature_selected_population_attempt` (the latest failed population tool call);
- current report facts (`literature_completed_work`, `literature_current_scoring_sheets`);
- `literature_goal_plan`.

A reference-evidence parent configuration (`reference_parent_sources`, `annotation` role at the root) instead supplies `reference_evidence_parent` custody and its population operations as the initial context.

## Tools it offers (`source_operations.py`, `source_contracts.py`, `grading/`, `scoring/`)

- Common actions: `tool, reason, child, redeliver_report` (no wait, `supports_wait = False`).
- Access tools: state.query, source.read, source.locate, source.sequence.references, image.view, source.archive.members/extract, source.xlsx.sheets/rows, source.pdf.info/text/page, material.annotations, material.parse, material.from_source, execution.estimate (xlsx tools only).
- Acquisition tools: public.literature.search/read/sequence_identity, public.ncbi.search (database ∈ pubmed/protein/nuccore/taxonomy/biosample/bioproject), public.pmc.versions/files/asset, public.uniprot.search/record, public.taxonomy, public.ncbi.sequence.
- Population tools from the A108 population catalogue: `literature.a108_grading.populate` (the grading/subscoring sheet) and `literature.a108.aggregate` (the main context sheet). Their text-witness inputs are materialized from authorized source reads.
- Argument rules: arguments are validated. With an assigned page, every read and every population source must lie within that page's source tree. The grading and aggregation repositories authorize each source and record access, including `state.query` results.
- Reason action (grading): the action schema comes from `literature_required_grading.action_schema(commit_schema, population_schema)` (provider `literature.a108.context_grading`). For a leads task, `source_lead` is added (`lead_schema`: proposed_annotation_ref, source_ref, subject_ref, disposition relevant/not_relevant, relevance_rationale, witness). `execute_reasoning`:
  - A `source_lead` reads the witness span, commits the reasoning or required grading in one transaction, then validates the lead.
  - Any other selection runs the required grading, coupling the purpose-specific grader with the saved subscoring sheet (AGENTS A108 rule).

## How its credit is counted (`credit.py`)

- `LiteratureTaskCredit` (`literature_local_task_v1`): `credit = credit_unit * len(answers)`, with no rescaling or clamping, and it must be finite. The policy record says: unit `one_verified_source_for_original_question` or `one_answer_to_original_commission`, `revision_credit False`, `activity_credit False`, `annotation_support separate`. The task status is `answered`, `unanswered` or `unresolved_contract`, and `source_contributions` lists the answers.
- `verified_source_leads`: relevant lead dispositions of this proposed annotation, taken from own reason results and admitted child forms. Only the latest disposition per normalized source is kept, in decision-index order.

  A lead counts only if it passes `validate_lead`:
  - the same proposed annotation;
  - witness source = lead source;
  - a non-empty rationale;
  - all refs received;
  - the subject anchored in the source and inside the witness span;
  - a source that is not a search page (`/search`, `/esearch.fcgi`).
- `source_answer:screening`: one `no_applicable_evidence` answer, given only when this episode's own `no_applicable_evidence` reasoning (with a reason) covers every requested span.
- `source_answer:assessment`: one answer, when a current, retained, target-eligible assessment of the proposed annotation has an anchored or visually anchored observation in a requested source.
- Credit refuses a mismatched commission, a proposed annotation outside the scope, and a hypothesis that is not rooted in a scope subject.

## Continuation (`yield_estimator.py`, `configuration.py`)

- Task keys: `A108:verified_source_leads`, `A108:source_answer:assessment`, `A108:source_answer:screening`.
- `yield_bindings[key] = {credit_unit, kind, cutoff, uncertainty_alpha}`. The kind must be `accumulation` for leads and `remaining_commissioned_credit` for answers.
- No private binding → `yield_controller` returns None (the old default controller).
- Leads → accumulation controller with that cutoff and alpha, which maps to `AccumulationYieldEstimator`.
- Answers → `_FiniteLiteratureYieldController`. Its forecast is `estimate_score_yield`, with the next-gain band capped at the remaining commissioned credit `max(0, credit_unit - current)`, and exactly zero once every requested answer is earned. The capacity is `credit_unit` (one answer). Initial credit above capacity is refused. This is a finite target, so it maps to `CompletionYieldEstimator(initial_credit, target=credit_unit)`. Credit itself is never capped; only the forecast is.

## What it reports to its parent (`to_parent.py`, `received_evidence.py`)

- Fact sources: `literature_a108_grading_cells` and `literature_a108_aggregation_cells` (arrays, with RETURN_MEANINGS), `literature_screening_answers` (screening_schema) and `literature_source_lead_dispositions` (lead_return_schema).
- Facts:
  - the grading/aggregation cells of the owned and received current sheets, limited to the requested components;
  - `literature_completed_work` and `literature_current_scoring_sheets`;
  - the screening answers (screening task);
  - the lead dispositions (leads task).
- Report validation:
  - the assignment and form references are checked;
  - LEADS/SCREENING fields must equal the saved work;
  - grading/aggregation rows must be exactly the requested subset of owned sheets, with the receiver authenticated through `record_selection`.

## Differences from the sibling/similar episodes

- A normalized diff (module paths stripped) shows that the three literature episodes `published_evidence_assessment`, `evidence_search_strategy_improvement` and `source_relevance_assessment` are copies of one another. They differ only in these places:
  - role name and `_ROLE_INSTRUCTIONS` text;
  - assignment version and its ref field (`literature_assignment_v1/source_refs`, `strategy_assignment_v1/prior_search_refs`, `search_assignment_v1/search_result_refs`);
  - `_CHILDREN` and the child preparer/receiver (`literature_strategy`, `literature_search`, `literature_page`);
  - `binding_path`/`binding_id` and `commissioning_parent`;
  - `entry_roles`;
  - docstrings.

  Credit, yield, tools, grading/scoring, reporting and the decision source are identical. The copies are the intended private-binding duplication, so each one must be carried over into its own folder.
- `from_parent.assignment_schema` in every copy holds the same three-entry version table (`literature`, `literature_strategy`, `literature_search`) and indexes it with its own role.
- Against the head `sample_context_evidence`, a literature episode has no wait, no A/P selection and no `process.revise`. It credits commissioned literature answers (`credit_unit × answers`), where the head counts whole-axis finding progress. It has its own literature-task yield bindings, the grading/scoring mixins and the experimental prompt renderer.
- `entry_roles = ()`, and there is no `create_binding_tree`.
- `context_hook_applies` for roles outside ROLES evaluates `'literature_strategy' == 'literature'`, which is False. The parent `published_evidence_assessment` gets True from the same copied expression.

## File by file
| Old file | Lines | This episode's own intent | Old-runner names used (name×uses) |
|---|---|---|---|
| `binding_record.py` | 16 | `as_record()`: VERSION `literature_episode_binding_v1`, `binding_id='sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'`, configuration outcome_page_size, private_yield_binding + yield_bindings when set, reference_parent_sources, contract_information_profile. | none |
| `configuration.py` | 31 | Settings: `outcome_page_size` (default 8, positive int; how many own outcomes are shown), `reference_parent_sources`, `contract_information_profile`, `private_yield_binding` (bool), `yield_bindings` (only with private binding) validated by `validate_yield_bindings`. `reference_evidence(...)` constructor for a reference-evidence parent. | none |
| `credit.py` | 221 | Own credit `LiteratureTaskCredit` (version `literature_local_task_v1`): credit = `credit_unit * len(answers)` for the commissioned task, never rescaled; must be finite. Answers: `verified_source_leads` -> relevant source-lead dispositions (own reason results + admitted child forms with x-source `literature_source_lead_dispositions`, latest per normalized source); `source_answer:screening` -> one `no_applicable_evidence` answer only when own reasoning examined every requested span; `source_answer:assessment` -> one retained, target-eligible assessment of the proposed annotation whose observation is anchored in a requested source. Lead validation: same proposed annotation, witness source = lead source, rationale non-empty, refs received, subject anchored in source and inside the witness quote, not a search page. Credit refuses mismatched commission, annotation outside scope or not a target annotation. Policy record: revision_credit False, activity_credit False, annotation_support separate. | `getattr:services.scientific_credit_for`×1, `import:a108.communication`×1, `import:a108.domain`×2, `import:a108.finding_validity`×1, `import:a108.library.literature_assay_inputs`×2, `import:a108.numerical`×1, `import:a108.scientific_findings`×1, `received_record_refs`×2, `services.annotation_task_required`×1, `services.proposed_annotation_for`×1, `services.scientific_credit`×1, `table:runtime_actions`×4, `table:runtime_report_attempts`×2, `table:sqlite_master`×3, `workflow.projection_view`×1, `workflow.projector_receipt_arguments`×1, `workflow.scientific_projector_for_context`×1 |
| `decision_inputs.py` | 36 | Model context: same base fields as the head (goal, scope, working_state, visible refs, current_credit, evidence vector, investigation_progress, credit_binding, time_accounting, pending_work, last outcome, feedback, visual_evidence, report_deliveries, controller, ...), annotation context, monitoring credit, binding decision_context, completed-work axis results (a101..a104 sheets, target_sheets, tool_attachments, source_contributions), contract catalog; returns context and action schema (or redelivery inputs). | `getattr:self.workflow.store.reference_subset`×1, `getattr:self.workflow.tools.model_contract_catalog`×1, `import:a108.runtime`×1, `runtime.FACT_MEANINGS`×1, `runtime.FACT_SOURCES`×1, `runtime.json`×1, `runtime.Mapping`×2, `runtime._plain`×2, `runtime._references_in`×1, `self.workflow.action_schema`×1, `self.workflow.annotation_context`×1, `self.workflow.binding_context`×1, `self.workflow.catalog`×1, `self.workflow.controller_binding`×1, `self.workflow.delivery_resolution_inputs`×1, `self.workflow.delivery_status`×1, `self.workflow.extra_report_sources`×1, `self.workflow.is_scientific_source`×1, `self.workflow.job_episode_options`×1, `self.workflow.journal`×2, `self.workflow.knowledge`×1, `self.workflow.local_outcome_preview`×1, `self.workflow.pending_work`×1, `self.workflow.receipt_projection`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_binding`×1, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×3, `self.workflow.tools`×1, `self.workflow.working_state`×1, `table:runtime_actions`×1, `view.child_reports`×2, `view.controller_state`×1, `view.model_inputs`×1 |
| `decision_presentation.py` | 21 | completed_action_reports unless literature_completed_work is present or credit is root annotation_axis_credit; decision yield table. | `import:a108.episode_work_report`×1, `import:a108.runtime`×1, `runtime._category_yield_parameters`×1, `runtime.Mapping`×2, `runtime.yield_table`×1, `self.workflow.controller_binding`×1 |
| `episode.py` | 70 | Class `LiteratureEpisode`: binding_path `sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement`, commissioning_parent `sample_context_evidence/published_evidence_assessment`, role `literature_strategy`, entry_roles `() (not an entry)`. Prompt rendered by `render_literature_experimental_prompt`. Child: `literature_search` (source_relevance_assessment). Mixes in grading `ContextualInterpretation`, `ContextualSubscoring` and scoring `ContextualMainSheet`. `context_hook_applies`: own role, or (for roles outside ROLES) `'literature_strategy' == 'literature'`. | `import:a108.library.literature_experimental_prompt`×1 |
| `from_child_source_relevance_assessment.py` | 19 | Receive the `literature_search` child's typed form: recorded admission refs, progress-provider receipt, refs in the form + `received_form_references` (which stores A108 grading/aggregation cells from the child form), receipts kind child_form/report_redelivery. | `import:a108.episode_return_records`×1, `import:a108.runtime`×1, `receipts`×3, `workflow.binding_context`×2, `workflow.episode_bindings`×1, `workflow.is_job_source`×2, `workflow.progress_provider`×2, `workflow.receipts`×3, `workflow.run_id`×3, `workflow.store`×3 |
| `from_parent.py` | 74 | Assignment form version `strategy_assignment_v1` with `question_context_refs` and `prior_search_refs`, plus `literature_task` (task_schema), `proposed_annotation_ref`, and requested grading/aggregation component arrays. With private yield binding, `literature_task` and `proposed_annotation_ref` are required and the parent's task gets credit_unit and yield_settings from the declared binding (supplied values must match). Refs must be in scope (sources for *_refs, any for question_context_refs). Child's proposed annotation must equal the parent's. Optional `page` assignment (page_assignment_v1) validation helper. | `getattr:services.proposed_annotation_for`×1, `import:a108.library.literature_a108_aggregation_storage`×1, `import:a108.library.literature_a108_grading_storage`×1 |
| `goal.py` | 104 | Commissioned task: `task_schema()` = one of `verified_source_leads`, `source_answer/assessment` (source_refs), `source_answer/screening` (examined spans), each with evidence_axis A108, credit_unit > 0, optional yield_settings {kind accumulation or remaining_commissioned_credit, cutoff >= 0, uncertainty_alpha in (0,1)}. `commissioned_task` checks finite unit, proposed annotation, request matches assignment, the return form carries the required x-source (LEADS / changed_assessment_refs / SCREENING) and components, spans valid, sources inside an assigned page. Instructions = `_ROLE_INSTRUCTIONS['literature_strategy']` + A108_CONTEXT_TASK + A108_READING_TASK. `planning_context`: objective, proposed annotation, commissioned_result, progress_definition, planning_question. | `import:a108.communication`×1, `import:a108.domain`×1, `import:a108.library.literature_a108_prompt`×1, `import:a108.numerical`×1 |
| `grading/contextual_interpretation.py` | 49 | Reason action for A108: when a grading repository exists the action schema comes from `literature_required_grading.action_schema` with the population schema; for a leads task adds `source_lead` (lead_schema). `reasoning_has_task_content`: a source_lead counts as content for a leads task. `execute_reasoning`: source lead -> read the witness span, commit reasoning or required grading, then validate the lead; otherwise run required grading (purpose-specific grader + saved subscoring sheet) with source-access authorization. | `import:a108.literature_contract_error`×1, `services.workflow.store`×1 |
| `grading/contextual_subscoring.py` | 14 | Constructs this episode's `LiteratureA108GradingRepository(store, run_id)` once; it is the required grading repository. | `import:a108.library.literature_a108_grading_storage`×1, `services.workflow.run_id`×1, `services.workflow.store`×1 |
| `grading/__init__.py` | 0 | Empty package marker. | none |
| `__init__.py` | 1 | Empty package marker. | none |
| `internal_summary.py` | 106 | Binding decision context: literature_assignment, literature_source_custody (version, artifact/text/stdout/stderr refs, parent sources), own_literature_outcomes (first `outcome_page_size` own acquisition/read outcomes), literature_history_meaning, literature_examined_source_inputs, literature_experimental_work (source_experimental_evidence, A108), received fact display (reference/term/context/observation/hypothesis/assessment records + source metadata), owned population sources and latest failed population attempt, current report facts, literature_goal_plan. `initial_decision_context` for a reference-evidence parent at the root (`annotation` role). | `import:a108.library.literature_source_inputs`×1, `import:a108.library.literature_task_families`×1, `import:a108.library.literature_work_report`×1, `received_record_refs`×5, `services.own_outcomes`×1, `services.workflow.store`×2, `table:runtime_actions`×2, `table:sqlite_master`×2, `workflow.run_id`×2, `workflow.store`×2 |
| `received_evidence.py` | 90 | Received report facts and arrays for grading/aggregation cells (non-literature roles); `received_form_references` stores cells received in a child form; evidence tokens; `validate_received_report`: LEADS/SCREENING fields must equal the saved work, grading/aggregation rows must be the requested subset of owned sheets. | `import:a108.domain`×1, `import:a108.library.literature_sheet_updates`×1, `import:root.method_loop.durable`×1, `received_record_refs`×2, `services.record_selection`×1, `services.workflow.store`×2 |
| `scientific_records.py` | 16 | Population routes (grading and aggregation namespaces/providers/requested fields); no automatic score judgments. | `import:a108.library.literature_a108_aggregation_storage`×1, `import:a108.library.literature_a108_grading_storage`×1 |
| `scoring/contextual_main_sheet.py` | 11 | Constructs this episode's `LiteratureA108AggregationRepository` reading cells from the grading repository (main context sheet). | `import:a108.library.literature_a108_aggregation_storage`×1, `services.workflow.run_id`×1, `services.workflow.store`×1 |
| `scoring/__init__.py` | 0 | Empty package marker. | none |
| `source_contracts.py` | 37 | Constants: VERSION, ROLES (seven literature roles), refs, window/table/page shapes, `_CHILDREN = {'literature_strategy': ('literature_search',)}`, `_A108_ACCESS_TOOLS`, `_A108_ACQUISITION_TOOLS`, grading namespaces, population catalog, required grading logic (`literature.a108.context_grading` provider), `_READ_TOOLS`, `_ROLE_INSTRUCTIONS['literature_strategy'] = 'Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.'`. | `import:a108.communication`×1, `import:a108.composition_information`×1, `import:a108.domain`×1, `import:a108.episode_bindings`×1, `import:a108.library.literature_population_catalog`×1 |
| `source_operations.py` | 111 | Common actions `tool, reason, child, redeliver_report` (no wait). Tools: host catalog filtered to A108 access + acquisition tools (ncbi.search restricted to pubmed/protein/nuccore/taxonomy/biosample/bioproject; execution.estimate only for xlsx tools) plus population operations `literature.a108_grading.populate` and `literature.a108.aggregate`. Arguments validated; reads stay inside an assigned page source; repositories authorize source and record access; text witness inputs materialized for population tools; state.query results checked by both repositories. | `import:a108.composition_information`×1, `import:a108.library.literature_assay_inputs`×1, `import:a108.literature_contract_error`×1, `received_record_refs`×1, `services.execute_tool`×1, `services.read_record`×1, `services.tool_catalog`×1 |
| `source_references.py` | 35 | `_require` (ref in scope then read), artifact by representation, `_within_source` (parent-source walk), `resolve`. | `services.read_record`×1, `services.reference_in_scope`×1 |
| `task_decision.py` | 351 | Old model-call machinery as the head, but decisions are sent through `complete_with_presentation(..., prompt_renderer=render_literature_experimental_prompt)` when the provider supports it (`decision_completion`); no waiting_support. | `getattr:self.workflow.provider.conversation_key`×1, `getattr:self.workflow.provider.has_session`×1, `getattr:self.workflow.store.reference_subset`×1, `import:a108.providers`×2, `import:a108.runtime`×1, `import:root.providers`×1, `receipts`×4, `runtime._action_generation_schema`×2, `runtime.apply_state_frame`×1, `runtime._ASSIGNMENT_TRANSPORT`×1, `runtime.child_option_information`×2, `runtime.composition_lookup_schema`×2, `runtime.CONTRACT_INFORMATION_OPERATIONS`×1, `runtime.DECISION_CONTEXT_VERSION`×2, `runtime.DECISION_EXCHANGE_PROTOCOL`×5, `runtime._digest`×1, `runtime.Draft`×1, `runtime.instructional_model_context`×4, `runtime.is_contract_information`×1, `runtime._json`×14, `runtime.json`×3, `runtime.lookup_attempts`×1, `runtime.Mapping`×2, `runtime.model_snapshot`×2, `runtime._object`×3, `runtime._plain`×2, `runtime._recorded_action_generation_schema`×1, `runtime._recorded_assignment_transport`×1, `runtime._references_in`×1, `runtime.requested_contract_information`×2, `runtime.schema_failure_diagnostic`×2, `runtime.sqlite`×1, `runtime.state_frame`×1, `runtime.ValidationError`×5, `runtime.WorkflowError`×14, `self.workflow.available_child_roles`×1, `self.workflow.binding_context`×1, `self.workflow.contract_information_profile`×1, `self.workflow.contract_information_reply`×1, `self.workflow.decision_exchanges`×4, `self.workflow.decision_protocol`×4, `self.workflow.episode_bindings`×1, `self.workflow.execute`×1, `self.workflow.execution_expectations`×1, `self.workflow.freeze_contract_information`×1, `self.workflow.freeze_literature_numerical_contracts`×1, `self.workflow.history_preview`×1, `self.workflow.is_job_source`×3, `self.workflow.journal`×3, `self.workflow.launch_instructions`×2, `self.workflow.native_estimation_context`×1, `self.workflow.numerical_contracts`×1, `self.workflow.pending_work`×1, `self.workflow.permits_common_action`×1, `self.workflow.provider`×3, `self.workflow.receipts`×4, `self.workflow.resource_context`×1, `self.workflow.resource_estimator`×4, `self.workflow.run_id`×1, `self.workflow.services`×2, `self.workflow.shared_information_context`×1, `self.workflow.specialist`×2, `self.workflow.store`×2, `self.workflow.uses_received_record_context`×2, `self.workflow.validate_contract_information`×5, `services.decision_exchange_instructions`×1, `services.instructions`×1, `table:runtime_model_calls`×8 |
| `task_instructions.py` | 28 | Instruction composition as the head but no wait or native-event text (literature episodes do not wait). | `getattr:specialist.replaces_default_instructions`×1, `import:a108.library.literature_investigation_prompt`×1, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL`×1, `runtime_prompt.INSTRUCTIONS`×4, `runtime_prompt.REASONING_COMMIT_REQUIREMENT`×1, `source.workflow.binding_context`×1, `source.workflow.decision_protocol`×1, `source.workflow.is_job_source`×1, `source.workflow.knowledge`×1, `source.workflow.launch_instructions`×1, `source.workflow.native_event_information`×1, `source.workflow.permits_common_action`×3, `source.workflow.specialist`×1 |
| `task.py` | 209 | Old decision source (same machinery as the head) without wait; reason/tool execute, credit after observed outcome. Own intent: failed/invalid outcomes enter the iterator; empty reasoning rejected unless task content (source_lead). | `getattr:binding.reasoning_has_task_content`×1, `getattr:specialist.execute_reasoning`×1, `import:a108.episode_source_failure`×1, `import:a108.providers`×1, `import:a108.runtime`×1, `runtime.ActionFailure`×1, `runtime.ContractError`×1, `runtime.ContractInformationError`×1, `runtime._decode_recorded_action_response`×1, `runtime.Draft`×3, `runtime.EventTargetError`×1, `runtime.form_with_facts`×1, `runtime.inspect`×1, `runtime._json`×7, `runtime.json`×9, `runtime.Mapping`×1, `runtime.nullcontext`×5, `runtime.observes_action_outcome`×1, `runtime.Record`×2, `runtime.ReportBoundaryError`×1, `runtime.ReportRedelivery`×2, `runtime.schema_failure_diagnostic`×1, `runtime.SourceEnd`×2, `runtime.validate_form`×1, `runtime.ValidationError`×2, `runtime._wait_target_feedback`×1, `runtime.WorkflowError`×2, `self.workflow.automatic_score_updates`×1, `self.workflow.binding_context`×3, `self.workflow.completed_unit`×3, `self.workflow.completions`×3, `self.workflow.controller_value`×2, `self.workflow.decision_exchanges`×3, `self.workflow.episode_bindings`×1, `self.workflow.execute`×1, `self.workflow.execution_binding`×7, `self.workflow.facts`×1, `self.workflow.inprocess_replay`×4, `self.workflow.journal`×9, `self.workflow.next_return`×1, `self.workflow.pending_handles`×1, `self.workflow.pending_work`×1, `self.workflow.permits_common_action`×1, `self.workflow.reasoning_action_schema`×1, `self.workflow.receive_native_outcome`×1, `self.workflow.receive_outcome`×1, `self.workflow.release`×2, `self.workflow.resolve_pending_deliveries`×1, `self.workflow.resolver`×1, `self.workflow.retain_shared_grading_results`×1, `self.workflow.run_id`×3, `self.workflow.selected`×3, `self.workflow.source_credit_view`×2, `self.workflow.specialist`×2, `self.workflow.store`×9, `self.workflow.validate_report`×1, `table:runtime_actions`×8, `table:runtime_episodes`×1, `table:runtime_forms`×2, `table:runtime_model_calls`×2, `view.units_consumed`×4 |
| `task_state.py` | 108 | Old per-episode state, identical to the head's. | `import:a108.episode_source_failure`×1, `import:a108.runtime`×1, `runtime.ActionLeaf`×1, `runtime.EFFECT_VERSION`×1, `runtime.Episode`×1, `runtime.interpretation_schema`×1, `runtime._json`×2, `runtime.json`×4, `runtime._object`×1, `runtime._plain`×1, `runtime.Record`×1, `self.workflow.archive`×1, `self.workflow.completions`×4, `self.workflow.controller_value`×1, `self.workflow.execution_backend`×1, `self.workflow.execution_binding`×4, `self.workflow.execution_handle`×2, `self.workflow.inprocess_replay`×7, `self.workflow.journal`×5, `self.workflow.progress_provider`×2, `self.workflow.recover_commissions`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_view`×1, `self.workflow.store`×2, `table:runtime_actions`×5, `workflow.context`×1, `workflow.grains`×1 |
| `to_child_source_relevance_assessment.py` | 25 | Commission `literature_search`: scope inside parent, expanded return form, required return sources, initial report valid, role allowed, `binding.prepare_assignment(...)` with the selection's assignment. | `getattr:binding.required_return_sources`×1, `import:a108.runtime`×1, `runtime.ContractError`×1, `runtime.interpretation_schema`×1, `runtime.parse_json_object`×1, `runtime.validate_form`×1, `services.capabilities`×1, `workflow.annotation_child_roles`×1, `workflow.available_child_roles`×1, `workflow.binding_context`×3, `workflow.child_initial_report_input`×1, `workflow.episode_bindings`×3, `workflow.expanded_contract_form`×1, `workflow.launch_instructions`×1, `workflow.run_id`×1, `workflow.services`×1, `workflow.specialist`×1, `workflow.store`×1 |
| `to_parent.py` | 64 | Fact sources: grading cells and aggregation cells (arrays), `literature_screening_answers`, `literature_source_lead_dispositions`. Facts: grading/aggregation cells for owned + received current sheets restricted to requested components, current report facts (literature_completed_work, current scoring sheets), screening answers for a screening task, lead dispositions for a leads task. Report validation: assignment, form references, received-report checks. | `getattr:services.workflow`×1, `import:a108.library.literature_a108_aggregation_storage`×1, `import:a108.library.literature_a108_grading_storage`×1, `import:a108.library.literature_numerical_contracts`×1, `import:a108.library.literature_sheet_updates`×2, `import:a108.library.literature_work_report`×1, `received_record_refs`×3, `services.read_record`×1, `services.workflow.store`×3, `workflow.store`×2 |
| `waiting.py` | 8 | `supports_wait = False`. | none |
| `yield_estimator.py` | 108 | `validate_yield_bindings`: keys only `A108:verified_source_leads`, `A108:source_answer:assessment`, `A108:source_answer:screening`; each `{credit_unit>0 finite, kind, cutoff, uncertainty_alpha}`; kind accumulation for leads, remaining_commissioned_credit for answers. Controller: leads -> accumulation controller; answers -> finite controller whose forecast is `estimate_score_yield` with the next-gain band capped at remaining commissioned credit (`credit_unit - current`, floor 0) and exact zero when earned. | `import:a108.communication`×1, `import:a108.domain`×1, `import:a108.numerical`×2 |

## Carried over

Old files read at 97308b94c (through `git -C /home/chia/repos/gene_annotation_episode_disk show`; the working repository has no `.git`). This episode is a private copy of the finished literature episodes of the same family (the intent record above: the three literature episodes are copies of one another) adapted to its role `literature_strategy`, its assignment `strategy_assignment_v1` (`prior_search_refs`), its role instruction and its one child slot `source_relevance_assessment` (old role `literature_search`). Library candidates are marked in the new-place column. Machinery is not carried. The old per-episode files outside the ten-file set (including the hook-era `episode.py`, class on `LiteratureBinding`) were deleted from the folder. The grading/ and scoring/ library modules called by `task.py` are in `episode_support/literature/` under the same names; their old Store form is listed in the blocked file.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record(): deleted (README 3d/3e: the run journal records the binding) |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record(): deleted (README 3d/3e: the run journal records the binding) |
| configuration.py | LiteratureConfiguration | episode function | settings (ctx.settings) and file constants: OUTCOME_PAGE_SIZE in messages/internal_summary.py; cost/parameters in yield_estimator.py; tool_registry/knowledge_library_directory read in task.py |
| configuration.py | LiteratureConfiguration.__init__ | episode function | same: outcome_page_size -> messages/internal_summary.py OUTCOME_PAGE_SIZE; private_yield_binding/yield_bindings/validate_yield_bindings -> machinery (the controller is always built from the task, yield_estimator.py); contract_information_profile -> machinery (contract-information freezing, README 5 item 16) |
| configuration.py | LiteratureConfiguration.reference_evidence | episode function | not carried: the root-only reference-evidence-parent constructor (this episode is not the annotation role); listed in unplaced_old_functions |
| credit.py | _resolve | episode function | task.py resolve_aliases (private copy; library candidate) |
| credit.py | lead_schema | episode function | task.py lead_schema (private copy; library candidate) |
| credit.py | lead_return_schema | episode function | messages/final_to_parent.py RETURN_FORM field literature_source_lead_dispositions (a selectable list field; the row schema is not restated) |
| credit.py | validate_lead | episode function | task.py validate_lead (re-expressed on ctx.store; library candidate) |
| credit.py | lead_dispositions | episode function | credit.py lead_dispositions (over the summary and records) |
| credit.py | screening_schema | episode function | messages/final_to_parent.py RETURN_FORM field literature_screening_answers (selectable list field) |
| credit.py | _current_assessments | episode function | credit.py current_assessments |
| credit.py | screening_answers | episode function | credit.py screening_answers |
| credit.py | LiteratureTaskCredit | episode function | credit.py credit / answers / credit_binding |
| credit.py | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding (episode content; the credit definition the model is shown) |
| credit.py | LiteratureTaskCredit.__call__ | episode function | credit.py credit and answers (the commission-mismatch comparison and store.read_snapshot are not carried) |
| credit.py | LiteratureTaskCredit._answers | episode function | credit.py answers, assessment_answers |
| credit.py | LiteratureCredit | machinery | credit-view/projector wiring (README 3d: credit_view, credit_projector, credit_kind): replaced by credit(summary, records) |
| credit.py | LiteratureCredit._scientific_credit_invocation | machinery | services.scientific_credit / projector_receipt_arguments invocation (README 3d) |
| credit.py | LiteratureCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | LiteratureCredit.credit_view | machinery | credit_view deleted: credit(summary, records) returns the number; the other view fields are shown by the summary (README 3d) |
| credit.py | LiteratureCredit.credit_projector | machinery | credit_projector deleted (README 3d) |
| decision_inputs.py | build_decision_inputs | episode function | task.py decide (the context shown to the model) over messages/internal_summary.py; the controller/time/pending-work/delivery fields are the system (README 3a/3d) |
| decision_presentation.py | prepare_completed_work | episode function | unplaced: old literature_work_report.completed_work is not in episode_support/; the selectable return literature_completed_work raises where selected (messages/final_to_parent.py) |
| decision_presentation.py | decision_yield_table | episode function | messages/internal_summary.py action_yields (library yield_table), shown by task.py decide |
| episode.py | LiteratureEpisode | episode function | episode.py EvidenceSearchStrategyImprovement (the one EpisodeBinding class) |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | contract-information freezing (README 5 item 16) |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | contract-information freezing (README 5 item 16) |
| episode.py | LiteratureEpisode._role | machinery | role check of the shared mixins: each role is its own episode |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | hook-era context hook (role test): not carried |
| episode.py | LiteratureEpisode.child_request_preparer | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | LiteratureEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| from_child_source_relevance_assessment.py | receive_report | episode function | messages/read_from_child.py read_from_child (the references and cells of the admitted form); recorded-admission/receipts/progress_provider/receive_form_references (a write) are machinery or not carried |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment.child_assignment_schema | machinery | child_assignment_schema: the parent states what the child takes in msg_to_child; the child declares its own form (README 3b C3) |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (strategy_assignment_v1, question_context_refs, prior_search_refs, literature_task, proposed_annotation_ref, requested components) |
| from_parent.py | LiteratureAssignment._validate_page | episode function | not carried: only reachable for an assigned page (a strategy assignment has none) and a check of a commission; listed in unplaced_old_functions |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (commissioned_task); the in-scope/source-kind checks are checks of a commission and are not carried |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent; the yield-binding fill and mismatch check are machinery (settings, yield_estimator.py); the child side is messages/msg_to_child.py |
| goal.py | _yield_kind | episode function | yield_estimator.py yield_controller (the controller kind follows the task kind) |
| goal.py | _task_key | episode function | messages/read_from_parent.py task_key (private copy; library candidate) |
| goal.py | task_schema | episode function | messages/read_from_parent.py task_schema (private copy; library candidate) |
| goal.py | _return_sources | machinery | report_form machinery: the return contract is the child form RETURN_FORM (README 3b C4) |
| goal.py | _return_components | machinery | report_form machinery: the requested components are a selection (README 3b C4) |
| goal.py | commissioned_task | episode function | messages/read_from_parent.py commissioned_task (the request/return-contract and page checks are not carried) |
| goal.py | continuation_task | episode function | yield_estimator.py yield_controller (task read from parent_input) |
| goal.py | LiteratureGoal | episode function | goal.py GOAL and task.py instructions; messages/internal_summary.py literature_goal_plan |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL (ROLE_INSTRUCTION + A108_CONTEXT_TASK + A108_READING_TASK) |
| goal.py | LiteratureGoal.planning_context | episode function | messages/internal_summary.py literature_goal_plan |
| grading/contextual_interpretation.py | ContextualInterpretation | episode function | task.py reason tool, reason_schema, reasoning_has_task_content |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_action_schema | episode function | task.py reason_schema |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_has_task_content | episode function | task.py reasoning_has_task_content (used in action) |
| grading/contextual_interpretation.py | ContextualInterpretation.execute_reasoning | episode function | task.py reason (grading coupled with the commit, library literature_required_grading.execute) |
| grading/contextual_subscoring.py | ContextualSubscoring | episode function | task.py repositories (library LiteratureA108GradingRepository) |
| grading/contextual_subscoring.py | ContextualSubscoring._required_grading_repository | episode function | task.py repositories (grading repository) |
| grading/contextual_subscoring.py | ContextualSubscoring._a108_grading_repository | episode function | task.py repositories |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary.initial_decision_context | episode function | not carried: root-only reference_evidence_parent context; listed in unplaced_old_functions |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | messages/internal_summary.py population_sheets / literature_owned_population_sources |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | messages/internal_summary.py literature_selected_population_attempt |
| internal_summary.py | LiteratureSummary._received_fact_display_context | episode function | messages/internal_summary.py received_fact_display (source metadata of the old display unplaced) |
| received_evidence.py | LiteratureReceivedEvidence | episode function | messages/read_from_child.py, messages/final_to_parent.py validate_report |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | received-report source ledger (README 3b R3, 3e F5) |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | episode function | messages/read_from_child.py read_from_child (source_leads, the screening answers and the cell arrays; the screening answers join this episode's own in internal_summary) |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | episode function | messages/read_from_child.py (a field the child was not asked for reads as empty) |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | episode function | not carried: receive_cells is a write in read_from_child (README 5 item 4); listed in unplaced_old_functions |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | received evidence tokens (receipts ledger F1/F4) |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py validate_report (answers equal the saved work); the grading/aggregation requested-subset check is BLOCKED-ON-STORE-ACCESS and not carried |
| scientific_records.py | LiteratureScientificRecords | episode function | task.py (population routes: POPULATION_NAMES, populate) |
| scientific_records.py | LiteratureScientificRecords._population_routes | episode function | task.py POPULATION_NAMES, populate, repositories |
| scientific_records.py | LiteratureScientificRecords.automatic_score_judgments | episode function | not carried: returned nothing for A108 (no automatic judgments) |
| scientific_records.py | LiteratureScientificRecords.complete_score_judgment | episode function | not carried: returned nothing for A108 (no automatic judgments) |
| scoring/contextual_main_sheet.py | ContextualMainSheet | episode function | task.py repositories (library LiteratureA108AggregationRepository) |
| scoring/contextual_main_sheet.py | ContextualMainSheet._a108_aggregation_repository | episode function | task.py repositories |
| source_contracts.py | _a108_population_catalog | episode function | task.py catalog (library population_catalog) |
| source_contracts.py | _required_grading_logic | episode function | task.py reason_schema / reason (library literature_required_grading) |
| source_operations.py | LiteratureOperations | episode function | task.py tools |
| source_operations.py | LiteratureOperations.permitted_common_actions | episode function | task.py offered (wait and redeliver_report are not carried) |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py catalog, offered, DESCRIPTIONS, INPUT_SCHEMAS |
| source_operations.py | LiteratureOperations.execute | episode function | task.py run_access_tool, populate, reason, report (the TOOLS) |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py admitted and authorize_source (the page restriction is not carried) |
| source_operations.py | LiteratureOperations._materialize_text_arguments | episode function | task.py populate (library materialize_text_witness_inputs) |
| source_references.py | LiteratureReferences | machinery | reference resolution is custody (records.holds/get/require) |
| source_references.py | LiteratureReferences._require | machinery | custody read (records.require) |
| source_references.py | LiteratureReferences._artifact | episode function | not carried: only used for an assigned page; listed in unplaced_old_functions |
| source_references.py | LiteratureReferences._within_source | episode function | not carried: only used for an assigned page; listed in unplaced_old_functions |
| source_references.py | LiteratureReferences.resolve | machinery | custody read (records.holds/get) |
| task.py | LiteratureTask | episode function | task.py decide / action / TOOLS |
| task.py | LiteratureTask.next | episode function | task.py decide and action |
| task.py | LiteratureTask.apply_response | episode function | task.py action (rejection via Rejected) |
| task.py | LiteratureTask.execute | episode function | task.py tools (run_access_tool, populate, reason, report) and the ChildCall in action |
| task.py | LiteratureTask.finish | machinery | finish/report-form saving: deleted (D1); the report is the report tool and messages/final_to_parent.py |
| task_decision.py | LiteratureTaskDecision | episode function | task.py decide (instructions, context, output schema) |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py decide (ModelRequest); the model call itself is the system |
| task_decision.py | LiteratureTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | LiteratureTaskDecision.decision_completion | episode function | task.py decide; the prompt renderer render_literature_experimental_prompt is not in episode_support/ (unplaced_old_functions) |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange interpretation context (README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | saved-request checks (README 3a) |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | saved-request checks (README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop |
| task_instructions.py | instructions | episode function | task.py instructions (decision-exchange, pending-delivery, wait and native-event text not carried) |
| task_state.py | LiteratureTaskState | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.__init__ | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.suspension_changed | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.record_execution_failure | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.restore | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.record_effect | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| task_state.py | LiteratureTaskState.checkpoint | machinery | task state, checkpoint/restore, record_effect, suspension (README 3e) |
| to_child_source_relevance_assessment.py | prepare_request | episode function | messages/msg_to_child.py msg_to_child (expanded return form -> selection; scope/initial report -> message; prepare_assignment -> assignment) |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py RETURN_FORM and final_to_parent |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (selectable fields under their old names) |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py (literature_completed_work: unplaced, raises; literature_current_scoring_sheets: BLOCKED-ON-STORE-ACCESS, raises) |
| to_parent.py | LiteratureReport._a108_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | LiteratureReport._a108_facts | episode function | messages/final_to_parent.py final_to_parent with messages/internal_summary.py (cells, answers); saved_cells BLOCKED-ON-STORE-ACCESS |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (called before the result is returned; its validate_form step raises NotImplementedError validate_form_not_built:a108) |
| waiting.py | LiteratureWaiting | machinery | supports_wait = False: no wait action (README 3b) |
| waiting.py | LiteratureWaiting.supports_wait | machinery | supports_wait = False: no wait action (README 3b) |
| yield_estimator.py | validate_yield_bindings | machinery | checked the owner yield declarations when the binding was constructed; replaced by the controllers own checks (README 3d) |
| yield_estimator.py | _RemainingCommissionedCredit | episode function | yield_estimator.py: CompletionYieldController with target credit_unit (README 7b) |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | episode function | yield_estimator.py: CompletionYieldController (the estimator of the remaining commissioned credit) |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | machinery | as_record of an episode-local estimator: deleted |
| yield_estimator.py | _private_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | episode function | yield_estimator.py: CompletionYieldController with target credit_unit (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | episode function | yield_estimator.py yield_controller (cost, target from parent_input) |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | machinery | transitioned(epoch): deleted (README 3d) |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | yield_estimator.py yield_controller (task read from parent_input) |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller (None for no private binding is not carried) |
