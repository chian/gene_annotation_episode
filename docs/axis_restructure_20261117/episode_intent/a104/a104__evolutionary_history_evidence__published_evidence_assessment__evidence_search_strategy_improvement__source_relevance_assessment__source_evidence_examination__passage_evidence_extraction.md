# a104/evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/<file>`, only the 48 files directly
in the folder (3108 lines). It has no `grading/` or `scoring/` subfolder; child folders and tests were not read.
Imports from the old shared `root/a104/...` tree are listed by name only (not read). Old-runner names are
listed per file below and in `runs/carry_over/calls/a104_07.tsv`.

## What it is for (its goal, in its own words)

Old role `literature_targeted`, commissioned by `.../source_evidence_examination` (role `literature_page`).
`goal.py`:

> "Investigate the supplied source-bound passages for the assigned question. Read neighboring context,
> qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate
> spans remain separate; never concatenate them into a fabricated quotation."

followed by the shared literature paragraph ("This is an iterative scientific investigation in the shared Episode
loop. ... The commissioned task's own yield settings guide continuation.").

## What it reads from its parent's assignment

`from_parent.py` + `parent_page_contract.py` + `assignment_fields.py`:

| Field | Meaning |
|---|---|
| `version` | const `reading_assignment_v1` |
| `page` | the parent's `_PAGE` (source, representation, artifact, question context, prior deliveries), validated |
| `selection.spans` | one or more windows `{source_ref, representation, offset, limit}`; each on the page's source and representation; offset within the artifact size |
| `literature_task`, `proposed_annotation_ref` | commissioned task and proposed annotation (private yield binding as above) |
| `requested_*_components` etc. | under `rate_population` |

`prepare_assignment` also validates the parent's own page assignment and refuses a page outside it
(`literature_reading_outside_assigned_source`). The spans are context, not an executed reading script.

## Children it may commission

None: `child_roles` is `()` and `episode.py` has no child assembler or receiver. (`permitted_common_actions`
still lists `child`; with no child roles it offers nothing.)

## Differences from similar episodes

- Sibling `source_coverage_improvement` is a byte-identical copy except: goal text (document-order reading vs
  targeted passages), role name, and the selection shape (`selection.spans` list here vs a single `selection`
  window there; `windows = selected['spans']` vs `[selected]`).
- No acquisition tools; page-bound reading through `assignment.get('page')`.

## Task and instructions

- `task_instructions.py` `INSTRUCTIONS` (shared verbatim by all four episodes in this group): "You own an iterative
  scientific annotation improvement, not a tool itinerary." Use the fixed caller material within the parent's fixed
  subject and original-coordinate segments ("Those bounds set this investigation's credit denominator"). Select one
  ordinary tool, one typed reasoning commitment or one substantive child improvement; no stop action, turn budget,
  approval review or quality gate. It then states the reading rules (registered source, exact UTF-8 byte span and
  quote, actual source-subject identity; "An assay on a reference protein is not an assay on the input target";
  image.view visual observations with `visual_anchor`), the `investigation_finding` rule, `same_source_claim_as_ref`
  and `replaces_refs`, `extent_basis` (observed vs inferred), context allocations, `report_update` filled inside the
  same reasoning response, `redeliver_report`, and history reading through `episode.history`.
- `REASONING_COMMIT_REQUIREMENT`: a reason action needs at least one commit row; all-empty is rejected before
  acquisition (no observation) unless the schema permits `evidence_processing.kind=no_applicable_evidence`.
- The composer (`instructions(source, context)`) replaced the defaults with the binding's own instructions when it
  declares `replaces_default_instructions` (these do not; the goal text is appended), then appends the reasoning
  requirement, tool knowledge, launch library, the `pending_child_delivery` repair paragraph, wait paragraphs (not
  used: `supports_wait=False`, `wait` is not a permitted action), native event guidance, and under
  `decision_exchange_v1` replaces the history paragraph with `request_context` guidance.
- `task.py` / `task_action.py`: one model decision per unit. The response is `{selection, report_update}`. An
  empty reasoning commit raises `empty_reasoning_commit` unless `no_applicable_evidence` or the binding finds task
  content (`source_lead` for a `verified_source_leads` task). A `reason` goes to the binding's `execute_reasoning`
  (required grading, see `evidence_grading.py`), else `Store.commit_reasoning`; a `tool` goes to the binding's own
  `execute` (`source_operations.py`). Invalid selections set `feedback` (`action_contract`, contract repair hints,
  `reads.map` parameter diagnostics) and create no executed action. After an observed outcome: automatic score
  updates, then credit from the source credit view; `shared.read_information` retains shared grading results. A
  returned failed/invalid outcome still enters the iterator with its credit (`record_execution_failure`). A model
  call failure ends the episode `source_failed`. `report_update` is admitted against the interpretation schema of
  the parent's report contract; a bad update keeps the scientific work and sets `report_format` feedback.

## Decision state and what the model sees

`decision_context.py` (verbatim in all four): goal, scope, working_state, visible_record_refs, current_credit and
current_evidence_vector, investigation_progress (when receipts project), credit_binding, time_accounting,
pending_work, last_local_outcome, feedback, visual_evidence (latest completed `image.view` `visual_inputs`),
report_deliveries, controller state and binding, tools, tool_knowledge, job_episode_options, available_report_facts
(`credit` number plus reference arrays), requested_report_purpose, requested_form, current_report_update,
current_report_basis_refs, report_lifecycle ("Interpretations are the last actual reasoning basis; later tool
outcomes are facts, not a new judgment."), annotation context, and the binding's own `decision_context`
(`internal_summary.py`): `literature_assignment`, `literature_source_custody` (version, artifact/text/stdout/stderr
refs, parent sources), `own_literature_outcomes` (own acquisition and read outcomes, page of
`outcome_page_size`=8), `literature_history_meaning`, plus population display contexts and
`literature_completed_work` / `literature_current_scoring_sheets` when assay grading is on. `task_decision.py` adds
resource_context, shared_information_context, launch_instruction_library, child_options, completed_action_reports,
pending_work, execution expectations/estimates, native events and the contract-information profile.
Presentation: `task_presentation.py` renders text tasks through `presentation_selection.py` (literature
experimental prompt, published-scientific A104 prompt, receiver prompt, ...) else JSON.

Decision state kept by the task (`task_state.py`): `calls`, `feedback`, `last_outcome` + index, `report_values`
(starts as the parent's `initial_report`), `report_basis`, restore/replay bookkeeping, `interpret_schema`.

## Tools it offers

`source_catalog.py` filters the services' tool catalog to `_ACCESS_TOOLS`: `state.query`, `source.read`,
`source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`, `image.view`,
`source.archive.members`, `source.archive.extract`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`,
`source.pdf.text`, `source.pdf.page`, `execution.estimate` (xlsx branches only). This role gets no acquisition tools. When
`rate_population` is on it adds the population tools from the A104 population catalog (`literature.*.populate`,
`literature.a105.aggregate`, ...), with contract argument transport under the contract-information profile.
Every input schema gets `source_location_inputs`. Admission (`source_admission.py`): only catalog tools; under a
page assignment every source reference (including nested population refs, archive members, visual/covariance refs)
must descend from the assigned page source (`literature_reading_outside_assigned_source`); population source and
record access authorization. Common actions: `tool`, `reason`, `child`, `redeliver_report` (no `wait`).

## How its credit is counted

`credit.py`: `credit_kind` is `scientific`; `credit_view` is the services' scientific credit view;
`credit_projector` is `LiteratureTaskCredit` over the commissioned `literature_task` (refuses a non-A105 task when
`assay_grading_population`). The relocated `episode_support/literature/grading/literature_task_credit.py` shows its
unit: one verified source for the original question (`verified_source_leads`), one answer to the original
commission (`source_answer`, assessment or screening), or one current graded assessment per original experiment
(`a105_experiments`); `revision_credit` and `activity_credit` are false; annotation support is separate. Required
grading (`evidence_grading.py`) must save its sheet inside the same reasoning action before credit projection.
Navigation, byte coverage and repeated reading earn nothing (goal text). Credit is never bounded here.

## Continuation

`yield_estimator.py`: `continuation_task(context)` is the task key (`<axis>:<kind>` from `literature_task`);
`yield_controller` returns `None` unless `private_yield_binding` is configured, then
`_private_yield_controller(context, initial_credit, epoch, declaration)` with the declaration configured for that
task key in `yield_bindings` (`credit_unit`, `kind`, `cutoff`, `uncertainty_alpha`). Mapping onto `yield_control/`:
`verified_source_leads` -> accumulation (`kind='accumulation'`); every other task -> completion with a target
(`kind='remaining_commissioned_credit'`, target = `credit_unit` x number of experiments for `a105_experiments`,
else `credit_unit`). Settings come from the binding's configuration, never from the model; the parent cannot supply
different ones (`literature_task_supplied_yield_binding_mismatch`). The old `None` (no private binding) case left
continuation to the old runner's default controller; the port must pick one explicitly.

## What it reports to its parent

`to_parent.py` + `task_report_delivery.py`: with a report contract, the typed form = `form_with_facts(report_values,
schema, facts)`; facts from `report_facts.py`: `SCREENING` answers (screening tasks), `LEADS` dispositions
(`verified_source_leads`), rate/population fact cells (`numerical_report_facts.py`) for the requested components,
`literature_completed_work` and `literature_current_scoring_sheets` (assay grading). The form is validated against
the original schema, every reference must resolve in this episode's context, and received numerical cells must be
exactly the requested subsets (`received_report_admission.py`). Without a report contract: `{credit,
pending_handles, report facts}`.

## Configuration (shared by the four copies)

`configuration.py`: `outcome_page_size` (8), `rate_population` and its dependent sub-populations (ratio source,
controlled response, gel, completion time, product partition, active site, parent depletion, stoichiometric
balance, compiled assay, channel, ion discrimination, assay grading), evidence origins, implementation descriptors,
`contract_information_profile`, `reference_parent_sources`, `private_yield_binding` and `yield_bindings`. All are
construction-time settings of this binding; `binding_record.py` records them with `binding_id` = `evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction`.

## File by file

Old-runner names: `self.workflow.<member>` (including `source.workflow` / `workflow` arguments and `self.services.workflow`),
`self.services.<member>` (old per-axis services), imports from the old shared `root/a104` tree (`runtime`, `providers`,
`episode_bindings`, `communication`, `composition_information`, `domain`, `library.*`, `literature_*` support
modules), and old journal tables (`runtime_*`). Every `decision_*`, `task*` file also rebinds its methods into the old
`runtime` namespace (`library.live_runtime_functions.bind_functions`). No `BindingContext`, `receiving_context` or
`task_values` names occur; `workflow.binding_context(...)` builds the old binding context.

| Old file | Lines | This episode's own intent | Old-runner names (uses) |
|---|---|---|---|
| `assignment_fields.py` | 108 | Adds `literature_task` (commissioned task with credit unit/yield settings; required with `proposed_annotation_ref` under the private yield binding, `credit_unit` then supplied by the binding) and, per enabled population flag, every `requested_*_components` / views / keys array the parent may ask for (rate, quantity, assay, ratio, binding, kinetic, figure, gel, controlled response, assay grading, A105 aggregation, ...). | 38 a104.literature_* module imports |
| `binding_record.py` | 40 | Records this binding's own identity (`binding_id` = its path) and its configuration (page size, population flags, contract profile, reference parent sources, private yield bindings, descriptors). | none |
| `configuration.py` | 121 | Constructor: validates every population flag (each sub-population requires `rate_population`), evidence origins (`reported_source`/`synthetic_fixture`), implementation descriptors for controlled response and gel, contract-information profile, reference parent sources, `outcome_page_size` (default 8), `private_yield_binding` + `yield_bindings`. `reference_evidence(...)` constructor for a caller-assigned reference-source investigation. | import:a104.composition_information x1, 3 a104.literature_* module imports |
| `contracts.py` | 42 | Role vocabulary (`ROLES`), the role tree `_CHILDREN` (literature -> strategy -> search -> page -> table/ordered/targeted), JSON shapes `_WINDOW`, `_TABLE`, `_PAGE`, tool lists `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS` (literature search/read, NCBI pubmed, PMC versions/files/assets, experiment database tools), `_READ_TOOLS`; population catalog entry point; grading-logic selector. | import:a104.communication x1, import:a104.composition_information x1, import:a104.domain x1, import:a104.episode_bindings x1, import:a104.experimental_database_acquisition x1, 1 a104.literature_* module imports |
| `credit.py` | 21 | Credit kind `scientific`; credit view from the services' scientific credit; credit projector `LiteratureTaskCredit` for the commissioned task, refusing a non-A105 task when assay grading is on. | self.services.scientific_credit x1, 1 a104.literature_* module imports |
| `decision_context.py` | 58 | What the model sees each decision: goal, scope, working_state, visible_record_refs, current_credit + evidence vector, investigation_progress, credit_binding, time_accounting, pending_work, last_local_outcome, feedback, visual_evidence (latest completed image.view), report_deliveries, controller state/binding, tools, tool_knowledge, job options, available_report_facts, requested purpose/form, current_report_update + basis, report_lifecycle; plus annotation context and the binding's own decision_context. Annotation-axis mode trims state. | import:a104.library.live_runtime_functions x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.annotation_context x1, self.workflow.binding_context x1, self.workflow.catalog x1, self.workflow.controller_binding x1, self.workflow.delivery_status x1, self.workflow.extra_report_sources x1, self.workflow.is_scientific_source x1, self.workflow.job_episode_options x1, self.workflow.journal x3, self.workflow.knowledge x1, self.workflow.local_outcome_preview x1, self.workflow.pending_work x1, self.workflow.receipt_projection x1, self.workflow.run_id x1, self.workflow.source_credit_binding x1, self.workflow.source_credit_view x1, self.workflow.specialist x1, self.workflow.store x3, self.workflow.tools x1, self.workflow.working_state x1, table:runtime_actions x2 |
| `decision_contracts.py` | 133 | Decision-exchange support: adds published references from lookups to visible refs; exchange envelope schema (`request_context` vs `select_action`); validation of recorded exchange frames/history against the original snapshot. | import:a104.library.live_runtime_functions x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.contract_information_reply x1, self.workflow.decision_exchanges x2, self.workflow.journal x1, self.workflow.store x2, self.workflow.validate_contract_information x2, table:runtime_model_calls x1 |
| `decision_exchange.py` | 113 | The `decision_exchange_v1` loop for one decision: repeated model calls that may look up child options, composition information or own attempts, until a `select_action`; each exchange recorded; yield table shown in the snapshot. | import:a104.library.live_runtime_functions x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.controller_binding x1, self.workflow.decision_exchanges x1, self.workflow.execute x1, self.workflow.journal x1, self.workflow.run_id x1, self.workflow.services x1, self.workflow.validate_contract_information x1, table:runtime_model_calls x2 |
| `decision_provider.py` | 60 | Model call wrapper: when the provider is the original model class, calls `complete_with_presentation` with this binding's `decision_prompt_renderer`; else plain `complete`. | import:a104.providers x2, import:a104.runtime x1, import:providers x1, self.workflow.provider x1, self.workflow.specialist x2 |
| `episode.py` | 34 | Composes the binding class from the mixins; `binding_path`, `commissioning_parent`, `roles`, `entry_roles=()`, decision source type, prompt renderer, child request assembler / report receiver per child role. This copy: leaf, no child assembler/receiver. | none |
| `evidence_grading.py` | 89 | Required evidence grading inside the reasoning action (AGENTS.md A105/A108 rule): applicable scientific rows need `evidence_processing`; `no_applicable_evidence` must be source-witnessed and cannot carry assessments; every assessment needs `investigation_finding`; each grading saves its sheet via the grading repository and every interpretation needing a sheet must be covered, else the action fails/invalid. | import:a104.library.required_evidence_contracts x1, 1 a104.literature_* module imports |
| `from_parent.py` | 69 | The assignment this episode requires from its parent and `prepare_assignment` (task key -> yield binding declaration injected into `literature_task`; proposed annotation must equal the parent's). This copy: `reading_assignment_v1` = `page` + `selection.spans` (one or more windows); every span on the page's source and representation, offset within the artifact; must lie inside the parent page's source. | self.services.read_record x1, 1 a104.literature_* module imports |
| `goal.py` | 8 | This episode's goal text (see "What it is for"). This copy: investigate supplied source-bound passages; spans stay separate. | none |
| `__init__.py` | 0 | Empty package marker. | none |
| `internal_summary.py` | 48 | Binding's own decision_context: validated assignment, source custody of the assigned page/sources, own literature outcomes page (`outcome_page_size`), history meaning, examined source inputs (assay grading), experimental work aspect and population display contexts, current report facts. | self.services.own_outcomes x1, self.workflow.store x1, 2 a104.literature_* module imports |
| `numerical_report_facts.py` | 74 | Projects saved population sheets (rate, figure, compiled assay, controlled response, gel, ...) into the requested component cells of the return form, refusing version mismatches. | self.services.read_record x3, self.workflow.store x1, 3 a104.literature_* module imports |
| `parent_context.py` | 42 | Initial decision context only when this binding is the reference-evidence entry under `annotation`; contract-information profile for literature roles. | 1 a104.literature_* module imports |
| `parent_page_contract.py` | 16 | Validates the parent's page assignment, so the child's reading stays within the parent's source. | none |
| `population_routes.py` | 74 | Route table (namespace, requested field, provider, default components, repository) for each enabled population. | 36 a104.literature_* module imports |
| `population_task_context.py` | 56 | Read-only classification of own completed population sheets, and the latest failed population tool attempt. | self.services.workflow x2, self.workflow.run_id x2, self.workflow.store x2, table:runtime_actions x2, 1 a104.literature_* module imports |
| `presentation_selection.py` | 34 | Chooses the text-task prompt renderer (HPC, literature experimental, published scientific, API launch, selected execution, monitor, receiver). | import:a104.evolutionary_history_evidence_prompt x2, import:a104.library.hpc_prompt x1, import:a104.library.monitor_prompt x1, import:a104.library.source_component_prompt x1, import:a104.native_profile_presentation x1, import:a104.providers x1, import:a104.receiver_prompt x1, 1 a104.literature_* module imports |
| `received_evidence.py` | 119 | References to admit from a received child form; tokens identifying validated received component subsets. | import:a104.method_loop.durable x1, self.workflow.store x1, 15 a104.literature_* module imports |
| `received_report_admission.py` | 115 | Validates a received child report: requested component subsets only, controlled-response/gel component keys, public record reads. | import:a104.domain x2, self.services.read_record x1, self.services.record_selection x4, self.workflow.store x1, 1 a104.literature_* module imports |
| `received_reports.py` | 49 | Received report sources/facts for non-literature roles; empty arrays for requested types with no cells (not zeros). | none |
| `report_facts.py` | 27 | Return facts: screening answers, verified source lead dispositions, rate facts, current scoring sheets and completed work. | self.workflow.store x4, 3 a104.literature_* module imports |
| `report_field_contracts.py` | 82 | The rate/population fact sources a return form may declare. | 38 a104.literature_* module imports |
| `report_fields.py` | 11 | Fact sources: rate facts plus SCREENING and LEADS schemas. | 1 a104.literature_* module imports |
| `report_reference_access.py` | 11 | Resolves a return-form reference in this episode's context. | none |
| `repository_display.py` | 190 | Possessed-only display contexts for concentration windows, comparisons, precision, endpoint signals, controlled response, gel, received facts and native rate rows. | self.services.read_record x5, self.workflow.store x1, 8 a104.literature_* module imports |
| `role_policy.py` | 21 | Role check, permitted common actions (`tool`, `reason`, `child`, `redeliver_report`), and which child roles it may commission. This copy: role `literature_targeted`; no child roles (but `child` is still listed as a permitted common action). | none |
| `scientific_interpretation.py` | 53 | Reasoning action schema with required grading and `source_lead`; `source_lead` counts as task content for verified_source_leads; executes reasoning with lead validation against a witnessed source.read. | self.workflow.store x1, 2 a104.literature_* module imports |
| `source_admission.py` | 63 | Tool argument admission: tool must be in this role's catalog; page-bound reading (all source refs inside the assigned source); population source access authorization. | self.services.read_record x4 |
| `source_catalog.py` | 33 | Tool catalog for this role: access tools, acquisition tools (search role only), PubMed-only NCBI search, xlsx-only execution.estimate, population tools. This copy: access tools only (no acquisition tools). | import:a104.composition_information x1, self.services.tool_catalog x1 |
| `source_custody.py` | 39 | Scope-checked record reads, representation artifacts, ancestry check `_within_source`, page validation. | self.services.read_record x1, self.services.reference_in_scope x1 |
| `source_operations.py` | 47 | Executes an admitted tool: population tools to their repositories with text witness materialization; others via services tool execution; post-query authorization. | self.services.execute_tool x1, 1 a104.literature_* module imports |
| `source_repositories.py` | 305 | Lazy constructors for every population repository bound to this episode's store and run. | self.workflow.run_id x36, self.workflow.store x36, 36 a104.literature_* module imports |
| `source_text_inputs.py` | 19 | Materializes text witnesses for population arguments after source.read authorization. | 1 a104.literature_* module imports |
| `task_action.py` | 160 | Admits the response (empty reasoning commit rejected unless no_applicable_evidence or task content), invalid/failed feedback recorded, report_update admission; `execute` runs reason/wait/tool, records outcome and credit. | import:a104.library.live_runtime_functions x1, import:a104.read_mapping x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.automatic_score_updates x1, self.workflow.binding_context x2, self.workflow.completions x1, self.workflow.controller_value x2, self.workflow.decision_exchanges x3, self.workflow.execute x1, self.workflow.execution_binding x5, self.workflow.journal x3, self.workflow.last_observed_credit x1, self.workflow.pending_work x1, self.workflow.perform_selected_wait x1, self.workflow.permits_common_action x1, self.workflow.reasoning_action_schema x1, self.workflow.receive_native_outcome x1, self.workflow.receive_outcome x1, self.workflow.resolver x1, self.workflow.retain_shared_grading_results x1, self.workflow.run_id x2, self.workflow.selected x1, self.workflow.source_credit_view x1, self.workflow.specialist x2, self.workflow.store x6, self.workflow.validate_report x1, table:runtime_actions x6, table:runtime_model_calls x1 |
| `task_decision.py` | 156 | Assembles the full decision request (resource, shared information, launch instructions, child options, initial binding context, completed action reports, pending work, execution expectations, estimates, native events, waiting support) and calls the model or the exchange loop. | import:a104.episode_work_report x2, import:a104.library.hpc_prompt x1, import:a104.library.live_runtime_functions x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.available_child_roles x1, self.workflow.binding_context x3, self.workflow.contract_information_profile x1, self.workflow.decision_exchanges x1, self.workflow.decision_protocol x3, self.workflow.episode_bindings x1, self.workflow.evolutionary_history_evidence_binding x1, self.workflow.execution_expectations x1, self.workflow.freeze_contract_information x1, self.workflow.freeze_literature_numerical_contracts x1, self.workflow.history_preview x1, self.workflow.is_job_source x3, self.workflow.job_episodes x4, self.workflow.journal x1, self.workflow.launch_instructions x2, self.workflow.native_estimation_context x1, self.workflow.native_event_information x2, self.workflow.numerical_contracts x1, self.workflow.pending_work x1, self.workflow.permits_common_action x1, self.workflow.provider x2, self.workflow.receipts x4, self.workflow.resource_context x1, self.workflow.resource_estimator x5, self.workflow.services x1, self.workflow.shared_information_context x1, self.workflow.store x2, self.workflow.uses_received_record_context x2, self.workflow.validate_contract_information x2, self.workflow.waiting_support x1, table:runtime_model_calls x5 |
| `task_instructions.py` | 26 | The episode's INSTRUCTIONS text, reasoning commit requirement and conditional paragraphs (redelivery, wait, native events, exchange history guidance). | self.workflow.binding_context x1, self.workflow.decision_protocol x1, self.workflow.is_job_source x1, self.workflow.job_episodes x1, self.workflow.knowledge x1, self.workflow.launch_instructions x1, self.workflow.native_event_information x1, self.workflow.permits_common_action x3, self.workflow.specialist x1 |
| `task_presentation.py` | 43 | Presentation state machine for text tasks across bootstrap/update/lookup frames. | import:a104.providers x1 |
| `task.py` | 97 | The decision source `next`: resume/replay paths, a model call per decision, source failure ends with `source_failed`, `apply_response` to a unit. | import:a104.episode_source_failure x1, import:a104.library.live_runtime_functions x1, import:a104.providers x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.action_schema x1, self.workflow.completed_unit x3, self.workflow.completions x2, self.workflow.delivery_resolution_inputs x1, self.workflow.execution_binding x2, self.workflow.inprocess_replay x4, self.workflow.journal x4, self.workflow.next_return x1, self.workflow.resolve_pending_deliveries x1, self.workflow.run_id x1, self.workflow.selected x2, self.workflow.store x3, table:runtime_actions x2, table:runtime_episodes x1, table:runtime_model_calls x1 |
| `task_report_delivery.py` | 32 | `finish`: rootless result (credit, pending handles, report facts) or the typed return form with saved facts. | import:a104.library.live_runtime_functions x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.binding_context x1, self.workflow.episode_bindings x1, self.workflow.facts x1, self.workflow.journal x2, self.workflow.pending_handles x1, self.workflow.release x2, self.workflow.source_credit_view x1, table:runtime_forms x2 |
| `task_state.py` | 117 | Decision-source state (calls, feedback, report values/basis) and failure recording that still enters the iterator with its credit. | import:a104.episode_source_failure x1, import:a104.library.live_runtime_functions x1, import:a104.runtime x1, import:a104.runtime(namespace) x1, self.workflow.archive x1, self.workflow.completions x4, self.workflow.context x1, self.workflow.controller_value x1, self.workflow.execution_binding x4, self.workflow.grains x1, self.workflow.inprocess_replay x7, self.workflow.journal x5, self.workflow.progress_provider x2, self.workflow.recover_commissions x1, self.workflow.run_id x1, self.workflow.source_credit_view x1, self.workflow.store x2, table:runtime_actions x5 |
| `task_suspension.py` | 9 | Records the suspension condition for the execution backend. | self.workflow.execution_backend x1, self.workflow.execution_handle x2 |
| `to_parent.py` | 14 | Validates the return form against the original schema and received report rules. | none |
| `waiting.py` | 8 | `supports_wait = False`. | none |
| `yield_estimator.py` | 22 | Continuation task key and private yield controller from the configured yield binding (None without private yield binding). | 1 a104.literature_* module imports |

Symbols imported from the old `root/a104/runtime`: task.py/decision_context.py `FACT_MEANINGS, FACT_SOURCES, SourceEnd,
WorkflowError, _plain, _references_in`; task_decision/decision_contracts/decision_exchange/decision_provider
`CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, _ASSIGNMENT_TRANSPORT,
_action_generation_schema, _category_yield_parameters, _digest, _json, _object, _recorded_action_generation_schema,
_recorded_assignment_transport, apply_state_frame, child_option_information, composition_lookup_schema,
instructional_model_context, is_contract_information, lookup_attempts, model_snapshot, requested_contract_information,
schema_failure_diagnostic, state_frame, yield_table`; task_state.py `ActionLeaf, EFFECT_VERSION, Episode, Record,
interpretation_schema`; task_action.py `AcquisitionError, ActionFailure, ContractError, ContractInformationError,
EventTargetError, ReportBoundaryError, ReportRedelivery, _decode_recorded_action_response, _wait_target_feedback,
observes_action_outcome, validate_form`; task_report_delivery.py `Record, form_with_facts`; to_child_*.py
`ContractInformationError, Episode, EpisodeGoal, EpisodeRequest, Record, validate_saved_fact_form`; from_child_*.py
`WorkflowError, _json, _references_in`. From old `providers`: `ModelCallError`, `_ORIGINAL_MODEL_*` identity checks,
`render_evolutionary_history_evidence_prompt`, `text_instructions`, ... From old `literature_task_credit` (now
`episode_support/literature/grading/literature_task_credit.py`): `task_schema, _task_key, validate_yield_bindings,
commissioned_task, continuation_task, _private_yield_controller, LiteratureTaskCredit, SCREENING, LEADS, screening_*,
lead_*, validate_lead`.

## Carried over

Carried over on 19 November 2026 (private binding, ten-file form). Old files at 97308b94c.

| old file | kind | name | machinery or episode function | new place or reason |
|---|---|---|---|---|
| assignment_fields.py | class | LiteratureAssignmentFields | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of the old schema; the rate-population properties are not declared, see unplaced) |
| assignment_fields.py | method | LiteratureAssignmentFields._assignment_fields | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of the old schema; the rate-population properties are not declared, see unplaced) |
| binding_record.py | class | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() |
| binding_record.py | method | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() |
| configuration.py | class | LiteratureConfiguration | machinery | binding configuration class |
| configuration.py | method | LiteratureConfiguration.__init__ | machinery | construction-time settings of the old binding; the episode's settings are ctx.settings (cost, parameters, tool_registry, knowledge_library_directory); outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py |
| configuration.py | method | LiteratureConfiguration.reference_evidence | episode function | not carried: root-only reference_evidence_parent context (not this episode's); see unplaced |
| configuration.py | method | LiteratureConfiguration.contract_information_configuration | machinery | report-contract information profile (decision-exchange / report_form machinery) |
| contracts.py | function | _required_grading_logic | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions (_required_grading_logic) |
| contracts.py | function | _population_catalog | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions (_population_catalog) |
| credit.py | class | LiteratureCredit | episode function | credit.py (module) |
| credit.py | method | LiteratureCredit.credit_kind | machinery | credit kind declaration of the old runner |
| credit.py | method | LiteratureCredit.credit_view | machinery | services.scientific_credit view; credit(summary, records) is called by the system |
| credit.py | method | LiteratureCredit.credit_projector | episode function | credit.py credit (and credit_binding, lead_dispositions, screening_answers, assessment_answers, answers: private re-expression of the library LiteratureTaskCredit, library candidate) |
| decision_context.py | class | SourceInvestigationTaskContext | episode function | task.py decide / messages/internal_summary.py |
| decision_context.py | method | SourceInvestigationTaskContext.assemble_decision_context | episode function | task.py decide (the context the model is shown) over messages/internal_summary.py internal_summary |
| decision_context.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| decision_contracts.py | class | SourceTaskDecisionContracts | machinery | decision-exchange loop and contract-information (report_form) machinery |
| decision_contracts.py | method | SourceTaskDecisionContracts.interpretation_context | machinery | decision-exchange loop and contract-information (report_form) machinery |
| decision_contracts.py | method | SourceTaskDecisionContracts.exchange_schema | machinery | decision-exchange loop and contract-information (report_form) machinery |
| decision_contracts.py | method | SourceTaskDecisionContracts.exchange_response | machinery | decision-exchange loop and contract-information (report_form) machinery |
| decision_contracts.py | method | SourceTaskDecisionContracts.validate_contract_exchange_request | machinery | decision-exchange loop and contract-information (report_form) machinery |
| decision_contracts.py | method | SourceTaskDecisionContracts.validate_contract_exchange_history | machinery | decision-exchange loop and contract-information (report_form) machinery |
| decision_contracts.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| decision_exchange.py | class | SourceTaskDecisionExchange | machinery | decision-exchange loop (exchange_decision) |
| decision_exchange.py | method | SourceTaskDecisionExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision) |
| decision_exchange.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| decision_provider.py | class | SourceTaskDecisionProvider | machinery | recorded model call (decision_completion); the system records ModelRequest calls |
| decision_provider.py | method | SourceTaskDecisionProvider.decision_completion | machinery | recorded model call (decision_completion); the system records ModelRequest calls |
| episode.py | class | LiteratureEpisode | episode function | episode.py class PassageEvidenceExtraction(EpisodeBinding) |
| evidence_grading.py | function | execute | episode function | not carried: required assay-grading logic of the A105-style population route (assay_grading_population); see unplaced |
| from_parent.py | class | LiteratureAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | LiteratureAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (checks that need no Store); the Store checks of the page are unplaced |
| from_parent.py | method | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (the within-parent-page check is unplaced: it reads the parent's own assignment) |
| goal.py | class | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | method | LiteratureGoal.instructions | episode function | goal.py GOAL |
| internal_summary.py | class | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | method | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| numerical_report_facts.py | class | LiteratureNumericalReportFacts | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions; fact cells not declared in RETURN_FORM |
| numerical_report_facts.py | method | LiteratureNumericalReportFacts._rate_facts | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions; fact cells not declared in RETURN_FORM |
| parent_context.py | class | LiteratureParentContext | episode function | task.py decide / messages/internal_summary.py (the initial decision context is the summary) |
| parent_context.py | method | LiteratureParentContext.initial_decision_context | episode function | task.py decide / messages/internal_summary.py (the initial decision context is the summary) |
| parent_context.py | method | LiteratureParentContext.contract_information_profile | machinery | report-contract information profile machinery |
| parent_page_contract.py | class | LiteratureParentPageContract | episode function | not carried: reads the parent's own page assignment (a child cannot read it); see unplaced |
| parent_page_contract.py | method | LiteratureParentPageContract._parent_page_assignment_schema | episode function | not carried: reads the parent's own page assignment (a child cannot read it); see unplaced |
| parent_page_contract.py | method | LiteratureParentPageContract._validate_parent_page_assignment | episode function | not carried: reads the parent's own page assignment (a child cannot read it); see unplaced |
| population_routes.py | class | LiteraturePopulationRoutes | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| population_routes.py | method | LiteraturePopulationRoutes._population_routes | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| population_task_context.py | class | LiteraturePopulationTaskContext | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| population_task_context.py | method | LiteraturePopulationTaskContext._owned_population_task_sources | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| population_task_context.py | method | LiteraturePopulationTaskContext._population_task_context | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| presentation_selection.py | function | source_presentation_selection | episode function | task.py decide (the context is presented as the closed JSON; the text-TASK renderers select on contexts of other shapes and not on this episode's) |
| received_evidence.py | class | LiteratureReceivedEvidence | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_evidence.py | method | LiteratureReceivedEvidence.received_form_references | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_evidence.py | method | LiteratureReceivedEvidence.received_evidence_tokens | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_report_admission.py | class | LiteratureReceivedReportAdmission | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_report_admission.py | method | LiteratureReceivedReportAdmission.validate_received_report | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_reports.py | class | LiteratureReceivedReports | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_reports.py | method | LiteratureReceivedReports.received_report_sources | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_reports.py | method | LiteratureReceivedReports.received_report_facts | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| received_reports.py | method | LiteratureReceivedReports._complete_requested_received_arrays | machinery | received-report admission of child returns (this episode has no child) / receipts bookkeeping |
| report_facts.py | class | LiteratureReportFacts | episode function | messages/final_to_parent.py final_to_parent (screening answers and lead dispositions as selectable fields) |
| report_facts.py | method | LiteratureReportFacts.facts | episode function | messages/final_to_parent.py final_to_parent (screening answers and lead dispositions as selectable fields) |
| report_facts.py | method | LiteratureReportFacts.current_report_facts | episode function | messages/final_to_parent.py final_to_parent (screening answers and lead dispositions as selectable fields) |
| report_field_contracts.py | class | LiteratureReportFieldContracts | episode function | messages/final_to_parent.py RETURN_FORM (SCREENING, LEADS fields); the rate fact sources are not declared |
| report_field_contracts.py | method | LiteratureReportFieldContracts._rate_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (SCREENING, LEADS fields); the rate fact sources are not declared |
| report_fields.py | class | LiteratureReportFields | episode function | messages/final_to_parent.py RETURN_FORM (fact sources) |
| report_fields.py | method | LiteratureReportFields.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (fact sources) |
| report_reference_access.py | class | LiteratureReportReferenceAccess | machinery | report reference resolver of the old runner; the held check is records.holds (report_source_held in messages/internal_summary.py) |
| report_reference_access.py | method | LiteratureReportReferenceAccess.resolve | machinery | report reference resolver of the old runner; the held check is records.holds (report_source_held in messages/internal_summary.py) |
| repository_display.py | class | LiteratureRepositoryDisplay | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._concentration_window_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._measurement_comparison_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._summary_precision_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._endpoint_signal_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._controlled_response_bindings | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._gel_bindings | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._gel_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._received_fact_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._native_rate_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._native_rate_domain_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| repository_display.py | method | LiteratureRepositoryDisplay._native_rate_meaning_display_context | episode function | not carried: display contexts of the rate-population route (population route not built); see unplaced |
| role_policy.py | class | LiteratureRolePolicy | episode function | task.py CHILD_SLOTS = {} and offered() (no child, no wait; permitted actions are tools) |
| role_policy.py | method | LiteratureRolePolicy._role | episode function | task.py CHILD_SLOTS = {} and offered() (no child, no wait; permitted actions are tools) |
| role_policy.py | method | LiteratureRolePolicy.permitted_common_actions | episode function | task.py CHILD_SLOTS = {} and offered() (no child, no wait; permitted actions are tools) |
| role_policy.py | method | LiteratureRolePolicy.allowed_children | episode function | task.py CHILD_SLOTS = {} and offered() (no child, no wait; permitted actions are tools) |
| role_policy.py | method | LiteratureRolePolicy.child_roles | episode function | task.py CHILD_SLOTS = {} and offered() (no child, no wait; permitted actions are tools) |
| scientific_interpretation.py | class | LiteratureScientificInterpretation | episode function | task.py reason tool (validate_source_lead; library candidate) |
| scientific_interpretation.py | method | LiteratureScientificInterpretation._required_grading_repository | episode function | not carried: required assay grading (population route); see unplaced |
| scientific_interpretation.py | method | LiteratureScientificInterpretation.reasoning_action_schema | episode function | task.py reason_schema |
| scientific_interpretation.py | method | LiteratureScientificInterpretation.reasoning_has_task_content | episode function | task.py action (a source_lead is the task content of a verified_source_leads commit) |
| scientific_interpretation.py | method | LiteratureScientificInterpretation.execute_reasoning | episode function | task.py reason tool (validate_source_lead; library candidate) |
| source_admission.py | class | LiteratureSourceAdmission | episode function | task.py admitted / within_source (page-source restriction); population source authorization not carried |
| source_admission.py | method | LiteratureSourceAdmission._tool_arguments | episode function | task.py admitted / within_source (page-source restriction); population source authorization not carried |
| source_catalog.py | class | LiteratureSourceCatalog | episode function | task.py catalog / offered / DESCRIPTIONS / INPUT_SCHEMAS (population catalog not carried) |
| source_catalog.py | method | LiteratureSourceCatalog.catalog | episode function | task.py catalog / offered / DESCRIPTIONS / INPUT_SCHEMAS (population catalog not carried) |
| source_custody.py | class | LiteratureSourceCustody | episode function | task.py within_source (reads through read_record_in_scope); page checks of the commission are unplaced |
| source_custody.py | method | LiteratureSourceCustody._require | episode function | task.py within_source (reads through read_record_in_scope); page checks of the commission are unplaced |
| source_custody.py | method | LiteratureSourceCustody._artifact | episode function | task.py within_source (reads through read_record_in_scope); page checks of the commission are unplaced |
| source_custody.py | method | LiteratureSourceCustody._within_source | episode function | task.py within_source (reads through read_record_in_scope); page checks of the commission are unplaced |
| source_custody.py | method | LiteratureSourceCustody._validate_page | episode function | task.py within_source (reads through read_record_in_scope); page checks of the commission are unplaced |
| source_operations.py | class | LiteratureSourceOperations | episode function | task.py run_access_tool and the per-tool wrappers (ToolRegistry.execute_async; the populate branch is not carried) |
| source_operations.py | method | LiteratureSourceOperations.execute | episode function | task.py run_access_tool and the per-tool wrappers (ToolRegistry.execute_async; the populate branch is not carried) |
| source_repositories.py | class | LiteratureRepositories | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_rate_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_calibration_recovery_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_rate_observation_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_rate_replicate_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_quantity_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_assay_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_amount_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_optical_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_kinetic_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_binding_interaction_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_ratio_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_binding_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_binding_model_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_transport_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_figure_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_ratio_source_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_controlled_response_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories.literature_gel_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._endpoint_signal_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._concentration_window_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._measurement_comparison_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._summary_precision_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._rate_grid_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._compiled_assay_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._compiled_assay_v2_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._compiled_assay_v3_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._product_coupling_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._measurement_validation_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._ion_discrimination_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._channel_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._completion_time_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._active_site_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._assay_grading_source_cells | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._assay_grading_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._a105_aggregation_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._parent_depletion_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._stoichiometric_balance_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._product_partition_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._binding_interaction_model_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._kinetic_model_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._ratio_source_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._controlled_response_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._gel_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_repositories.py | method | LiteratureRepositories._native_rate_meaning_repository | episode function | population route not built (rate_population and its populate tools); not carried, listed in unplaced_old_functions |
| source_text_inputs.py | class | LiteratureSourceTextInputs | episode function | not carried: text-witness materialization for the populate tools (population route) |
| source_text_inputs.py | method | LiteratureSourceTextInputs._materialize_text_arguments | episode function | not carried: text-witness materialization for the populate tools (population route) |
| task.py | class | SourceInvestigationTask | episode function | task.py decide / action / TOOLS (SourceInvestigationTask.next: one unit per decision; the restore/replay branches are machinery) |
| task.py | method | SourceInvestigationTask.next | episode function | task.py decide / action / TOOLS (SourceInvestigationTask.next: one unit per decision; the restore/replay branches are machinery) |
| task.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| task_action.py | class | SourceTaskAction | episode function | task.py TOOLS (reason, report, access tools) and credit.py; wait/redelivery/native-score branches are machinery |
| task_action.py | method | SourceTaskAction.apply_response | episode function | task.py action (selection validation; empty reasoning commit rejected; the report_update admission is the report tool) |
| task_action.py | method | SourceTaskAction.execute | episode function | task.py TOOLS (reason, report, access tools) and credit.py; wait/redelivery/native-score branches are machinery |
| task_action.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| task_decision.py | class | SourceTaskDecision | episode function | task.py decide (the model request); the journal/exchange/contract branches are machinery |
| task_decision.py | method | SourceTaskDecision.call | episode function | task.py decide (the model request); the journal/exchange/contract branches are machinery |
| task_decision.py | method | SourceTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | method | SourceTaskDecision.conversation_key | machinery | provider conversation key of the old runner |
| task_decision.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| task_instructions.py | function | instructions | episode function | task.py INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, instructions |
| task_presentation.py | function | present_source_context | episode function | task.py decide (the context is presented as the closed JSON; the text-TASK renderers select on contexts of other shapes and not on this episode's) |
| task_report_delivery.py | class | SourceTaskReportDelivery | machinery | report delivery attempts (runtime_report_attempts); the result is final_to_parent |
| task_report_delivery.py | method | SourceTaskReportDelivery.finish | machinery | report delivery attempts (runtime_report_attempts); the result is final_to_parent |
| task_report_delivery.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| task_state.py | class | SourceTaskState | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | method | SourceTaskState.__init__ | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | method | SourceTaskState.bind_execution_context | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | method | SourceTaskState.record_execution_failure | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | method | SourceTaskState.restore_checkpoint | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | method | SourceTaskState.restore | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | method | SourceTaskState.record_effect | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | method | SourceTaskState.checkpoint | machinery | old decision state, checkpoint/restore and replay bookkeeping; the state is the view |
| task_state.py | function | _bind_preserved_runtime_providers | machinery | provider patching of the old runner (bind_functions) |
| task_suspension.py | class | SourceTaskSuspension | machinery | suspension machinery |
| task_suspension.py | method | SourceTaskSuspension.suspension_changed | machinery | suspension machinery |
| to_parent.py | class | LiteratureReport | episode function | messages/final_to_parent.py validate_report |
| to_parent.py | method | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| waiting.py | class | LiteratureWaiting | machinery | wait support (supports_wait is False; no wait action) |
| waiting.py | method | LiteratureWaiting.supports_wait | machinery | wait support (supports_wait is False; no wait action) |
| yield_estimator.py | class | LiteratureYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py task_key (the old task key) |
| yield_estimator.py | method | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
