# A104 table_evidence_extraction: intent at 97308b94c

Episode path: `root/a104/evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction`.
Old role name: `literature_table`. Commissioning parent: `.../source_evidence_examination` (old role `literature_page`).
Source: `git show 97308b94c:<path>/<file>` for the 48 files directly in this folder. The folder has no `grading/` or `scoring/` subfolder and no child episode folders.

## Purpose (goal, in its own words)

`goal.py` `LiteratureGoal.instructions`:

> Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.

It then appends the shared literature paragraph. That paragraph says this is an iterative investigation. No child order, reading quota or complete-document requirement is prescribed. A supplied reading selector is context, not an action. The episode must preserve the source subject, conditions, representation, version and UTF-8 byte anchors, and keep source claims separate from how they apply to the target. Negative findings count. Interpretations are committed with the common reasoning action, which updates the parent's typed form in the same call. Navigation, byte coverage and rereading earn no credit. The commissioned task's own yield settings guide continuation.

In short, the episode extracts source-bound evidence from one assigned table or sheet (or one byte window) of one literature source page, and interprets it for the A104 evolutionary-history question.

## Task and instructions

- `task.py`: `SourceInvestigationTask` combines `decision_context`, `task_state`, `task_decision`, `task_suspension`, `task_action` and `task_report_delivery`, with `instruction_composer = task_instructions.instructions`. `next(view)` drives the loop:
  - stops with `SourceEnd('source_failed')` when an earlier completion failed at the source;
  - replays or resumes from the journal;
  - otherwise assembles the decision context and calls the model;
  - when the model call fails, records the source failure and returns `SourceEnd('source_failed')`.
- `task_instructions.py`: the full `INSTRUCTIONS` text, a long investigation prompt. It covers:
  - credit-denominator bounds;
  - one tool, one reasoning commit or one child per step;
  - no stop action and no budgets;
  - source-subject identity and image.view visual anchors;
  - `investigation_finding` and `same_source_claim_as_ref` / `replaces_refs`;
  - extent_basis and context_allocation;
  - aliases and commit section order;
  - report_update in the same response, and redeliver_report;
  - restored history.

  The text is the same in the sibling episodes. Additions depend on conditions:
  - `REASONING_COMMIT_REQUIREMENT` when `reason` is permitted;
  - tool_knowledge and launch-library text;
  - the pending_child_delivery repair note;
  - wait and native-event text when `wait` is permitted, which it is not here;
  - under `decision_exchange_v1`, replacement of the history paragraph with the request_context / episode.history guidance.

  When a specialist is present, its `instructions(binding_context)` output is appended, or replaces the text if `replaces_default_instructions` is set. That specialist output is this episode's goal text from `goal.py`.

## What it reads from its parent's assignment (`from_parent.py`, `assignment_fields.py`, `parent_page_contract.py`)

- Assignment schema `reading_assignment_v1`:
  - `page`: `page_assignment_v1`, with source_ref, representation (text/original/stdout/stderr), artifact_ref, question_context_refs and prior_delivery_refs;
  - `selection`: either `_TABLE` (source_ref, sheet_key, offset, limit, header_row, optional `where` {column A-Z, equals/contains, value, case_sensitive}) or `_WINDOW` (source_ref, representation, offset, limit).

  The table selection branch is what makes this episode differ from its siblings (see below).
- The assignment also carries:
  - `literature_task`: from `literature_task_credit.task_schema`. With `private_yield_binding`, `credit_unit` stops being required and `literature_task` plus `proposed_annotation_ref` become required.
  - `proposed_annotation_ref`.
  - When `rate_population` is set, about 30 optional `requested_*_components` arrays: rate, observation grid, replicate, calibration recovery, quantity, assay, ratio, binding, binding model, transport, endpoint signal, figure, amount, optical, kinetic, kinetic model, binding interaction (and its model), concentration window, measurement comparison, summary precision, product coupling, measurement validation.
  - Further arrays, each behind its own flag: ion discrimination, channel, compiled assay v1/v2/v3, assay grading and A105 aggregation, product partition, completion time, active site, parent depletion, stoichiometric balance, ratio source, controlled response (components/views/keys), and gel (components/views/keys).
- Validation (`_validate_assignment`):
  - the selection's source_ref must equal the page's source_ref;
  - the representation must match;
  - the offset must lie within the artifact size;
  - the page artifact must match the source's representation (`source_custody._validate_page`).
- `prepare_assignment`:
  - an operation_key is required;
  - with `private_yield_binding`, the task key is looked up in `_yield_bindings`. The declared `credit_unit` and `yield_settings` {kind, cutoff, uncertainty_alpha} are injected, and a supplied value that does not match is rejected;
  - the child's `proposed_annotation_ref` must equal the parent's;
  - with a `literature_page` parent, the page must lie within the parent's assigned source (followed through `parent_source_refs`).

## Children

None. `role_policy.child_roles('literature_table')` returns `()`, and `_CHILDREN['literature_table'] = ()`. `permitted_common_actions` still lists `('tool', 'reason', 'child', 'redeliver_report')`, so `child` is permitted although the episode has no child roles. `redeliver_report` applies only to child deliveries, so it is also unused here. `wait` is not permitted, and `waiting.supports_wait` is False.

## Decision state and what the model sees

Episode-specific part (`internal_summary.decision_context`):
- `literature_assignment`: the validated assignment.
- `literature_source_custody`: for the page source, its version, artifact_ref, text_ref, stdout_ref, stderr_ref and parent_source_refs.
- `own_literature_outcomes`: own outcome metadata for the acquisition and read tools, paged by `outcome_page_size` (default 8).
- `literature_history_meaning`: tells the model to use episode.history for exact outcomes.
- When `assay_grading_population` is set: `literature_examined_source_inputs`.
- When `rate_population` is set:
  - `literature_experimental_work` {`literature_experimental_task_v1`, `source_experimental_evidence`};
  - the display contexts: native rate, rate domain, rate meaning, received facts, endpoint signal, summary precision, measurement comparison, concentration window;
  - `_population_task_context`: owned population sources, plus the latest failed population tool attempt read from `runtime_actions`.
- Behind their own flags: ratio-source return meanings, controlled-response return bindings, gel display.
- Always: `current_report_facts`, which gives completed work and current scoring sheets when assay grading is set.

`parent_context.initial_decision_context` applies only to an `annotation` root with `reference_parent_sources`, so it returns `{}` for this episode.

Generic part (`decision_context.assemble_decision_context`, which also uses `self.workflow`):
- goal, scope, working_state and visible_record_refs;
- current_credit and current_evidence_vector, investigation_progress when receipts project, and credit_binding;
- time_accounting, pending_work, last_local_outcome, feedback, visual_evidence from the last image.view, and report_deliveries;
- controller and controller_binding;
- tools, tool_knowledge, job_episode_options and available_report_facts;
- requested_report_purpose, requested_form, current_report_update, current_report_basis_refs and report_lifecycle;
- annotation context or proposed_annotations, and the `_completed_work_axis_results` sheets.

`task_decision.call` adds:
- resource and shared-information context, the launch instruction library, and selected launch instructions;
- child_options when child roles exist (none here), and the binding's initial context;
- completed_action_reports and requested_action_history (HPC);
- execution expectations, resource estimates, native expectations, native event targets and waiting_support;
- the contract-information profile, frozen literature numerical contracts, and the decision-exchange protocol;
- restored_episode_history.

Presentation (`task_presentation.present_source_context`, `presentation_selection`): the `decision_prompt_renderer` chooses a text renderer by context kind: HPC, literature-experimental (component-axis literature prompt), published-scientific (evolutionary_history_evidence prompt), API launch, selected execution, monitor, or receiver. Otherwise it sends JSON.

## Tools offered (`source_catalog.py`, `source_admission.py`, `source_operations.py`)

- Allowed set `_ACCESS_TOOLS`: state.query, source.read, source.locate, source.sequence.scan, source.sequence.references, source.experimental.records, image.view, source.archive.members, source.archive.extract, source.xlsx.sheets, source.xlsx.rows, source.pdf.info, source.pdf.text, source.pdf.page and execution.estimate.
- `execution.estimate` is limited to the branches for `source.xlsx.sheets` and `source.xlsx.rows`; it is dropped when neither branch exists.
- `_ACQUISITION_TOOLS` (public.literature.*, public.ncbi.search, PMC and experiment-database tools) are not in the allowed set. The `public.ncbi.search` pubmed restriction never applies.
- With `rate_population`, the population catalog's `literature.*.populate` tools are added (about 35 numerical populators, plus `literature.assay_grading.populate` and `literature.a105.aggregate`). Under a contract-information profile they carry `argument_transport`.
- Admission rules:
  - every `source_ref` (and an archive member's source) must lie within the assigned page source;
  - population arguments are walked for all source and sheet references, which must also lie within that source;
  - table-specific: `source.xlsx.rows` must use the assignment's `sheet_key` (`literature_table_sheet_mismatch`);
  - with `rate_population`, source reads and state.query refs are also authorized by the endpoint-signal, summary-precision, measurement-comparison and concentration-window repositories.
- Execution:
  - population tools go to their repository's `populate` (or `populate_native` / `populate_v3`), with text-witness arguments materialized through admitted `source.read`;
  - other tools go to `services.execute_tool`, with `permitted_record_refs` = received refs for the locate, sequence and experimental tools;
  - a returned state.query record is re-authorized;
  - argument errors return an `invalid` outcome.

## Reasoning and required grading (`scientific_interpretation.py`, `evidence_grading.py`)

- The `reason` schema is extended only when assay grading is set (the required-grading action schema) or the task kind is `verified_source_leads` (adds `source_lead`).
- `evidence_grading.execute`:
  - applicable scientific rows or original results require `evidence_processing`;
  - every assessment requires `investigation_finding`;
  - `no_applicable_evidence` must quote the examined witnesses, and its observations must lie inside them;
  - otherwise each grading's arguments are resolved and populated into a saved sheet (`sheet_ref` required), and every interpretation that needs a sheet must be covered (`required_grading_interpretation_uncovered`);
  - all of this runs in one transaction with the reasoning commit.

  This matches the AGENTS.md A105/A108 grading rule.
- `source_lead`: the lead's witness must be readable through admitted `source.read`, and is validated by `literature_task_credit.validate_lead`.

## Credit (`credit.py`)

- `credit_kind` = `'scientific'`.
- `credit_view` = `services.scientific_credit(context, receiver_selection)`.
- `credit_projector` = `LiteratureTaskCredit(self, context)` for the commissioned task (`commissioned_task(context)`). With `assay_grading_population`, the task's `evidence_axis` must be `A105`. That is an A105 requirement inside an A104 episode.
- No bounding or rescaling happens in these files.

## Continuation (`yield_estimator.py`)

- `continuation_task(context)` names the task key.
- `yield_controller` returns None unless `private_yield_binding`. Otherwise it looks up `_yield_bindings[task key]`, a declaration with kind, cutoff, uncertainty_alpha and credit_unit, raises `literature_yield_binding_missing_for_task` when it is missing, and builds `_private_yield_controller(context, initial_credit, epoch, declaration)`.
- The estimator kind and cutoff come from the configured `yield_bindings` (`configuration.py`). No values are written into this folder. Which of the three new estimators applies follows from each declaration's `kind`, which this folder does not record.

## Configuration (`configuration.py`, `binding_record.py`)

- `LiteratureConfiguration(services, outcome_page_size=8, ...)` takes:
  - the flags rate_population, assay_grading, channel, ion_discrimination, compiled_assay, completion_time, active_site, parent_depletion, stoichiometric_balance, product_partition, ratio_source, controlled_response and gel;
  - each population's evidence origin and descriptor;
  - reference_parent_sources and contract_information_profile;
  - private_yield_binding and yield_bindings.
- Every sub-population requires `rate_population`.
- `reference_evidence(...)` is the reference-source entry point.
- `as_record` records `binding_id` = this episode's path, with the flags that are set.

## Report to parent (`to_parent.py`, `report_fields.py`, `report_facts.py`, `numerical_report_facts.py`, `report_field_contracts.py`, `task_report_delivery.py`)

- Fact sources:
  - `SCREENING` (screening_schema) and `LEADS` (lead_return_schema);
  - with `rate_population`, the `_rate_fact_sources()` cell namespaces: rate, observation, replicate, grid, calibration, quantity, assay, ratio, binding, transport, figure, endpoint, etc., with their report schemas.
- Facts at completion:
  - screening answers when `answer_kind == 'screening'`;
  - lead dispositions for `verified_source_leads`;
  - with `rate_population`, the rate facts from committed refs and current sheets, plus the current report facts (`literature_completed_work` and `literature_current_scoring_sheets`).
- `validate_report`:
  - revalidates the assignment and the form against the original schema;
  - resolves references in context;
  - runs `validate_received_report`, under which screening and lead fields must equal the saved work.
- `finish`: when a report contract is present, builds the form from `report_values` plus the facts and saves it in `runtime_forms`. Otherwise it returns credit, pending handles and the current report facts.

## Received reports (`received_reports.py`, `received_evidence.py`, `received_report_admission.py`)

These handle the receiving side, which applies only to roles outside the literature `ROLES`. They are inert for this leaf because it receives no child reports. They are copies of the shared literature binding.

## Differences from sibling episodes

Siblings under `source_evidence_examination`: `passage_evidence_extraction` (`literature_targeted`) and `source_coverage_improvement` (`literature_ordered`). They differ from this episode only in:
- `goal.py`: the goal text. Passage extraction investigates supplied passages without concatenating spans; coverage improvement reads in document order using byte continuations. This episode deliberately selects table rows, headers and footnotes, with XLSX native identity.
- `from_parent.py`: this episode's selection is `_TABLE` or `_WINDOW`. Passage extraction uses `spans: [_WINDOW]`, and coverage improvement uses `_WINDOW`.
- `source_admission.py`: only this episode enforces the `sheet_key` check. In the siblings the same expression is a no-op statement.
- `role_policy.py`, `episode.py`, `binding_record.py` and the `defining_module` strings: the role name and path.

The other 34 files are identical across the three. The intent that belongs to this episode alone is therefore: the table goal, the table-or-window assignment, and the sheet-key lock.

## File by file

Old-runner names are listed with use counts. `a104.X` means an import from `gene_annotation_episode.episodic_workflow.root.a104.X`, the old shared a104 root. "lit storage/calc N" means N imports of `a104.literature_*_storage/calculations/models` modules.

| file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| `goal.py` | 8 | table goal text (above); the only goal source | none |
| `task_instructions.py` | 26 | full INSTRUCTIONS text and conditional additions | source.workflow.job_episodes, is_job_source, specialist, binding_context, permits_common_action x3, knowledge, launch_instructions, native_event_information, decision_protocol |
| `role_policy.py` | 21 | role `literature_table`; actions tool/reason/child/redeliver_report; no child roles | none |
| `episode.py` | 34 | composition; binding_path, commissioning_parent, roles, decision_source_type, decision_prompt_renderer | none (mixin composition only) |
| `contracts.py` | 42 | role list, `_CHILDREN`, `_TABLE`/`_WINDOW`/`_PAGE` schemas, `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, `_READ_TOOLS`, grading-logic hook | a104.communication, a104.composition_information, a104.domain, a104.episode_bindings (reference_in_context), a104.experimental_database_acquisition, a104.literature_population_catalog |
| `configuration.py` | 121 | population flags and their dependencies; yield_bindings; reference_evidence entry | a104.literature_task_credit (validate_yield_bindings), a104.composition_information, lit storage 2 (controlled_response, gel) |
| `binding_record.py` | 40 | binding_id and recorded configuration | none |
| `from_parent.py` | 69 | assignment schema (table or window), validation, yield-declaration injection, proposed-annotation equality, within-parent-source check | a104.literature_task_credit (_task_key); BindingContext (parent.role/assignment/scope) |
| `assignment_fields.py` | 108 | literature_task, proposed_annotation_ref, requested_* component arrays by flag | a104.literature_task_credit (task_schema), lit storage/calc 38 |
| `parent_page_contract.py` | 16 | validation of the parent's page assignment | none |
| `parent_context.py` | 42 | reference-evidence parent context (not used by this leaf); contract-information profile | a104.literature_ratio_source_render; BindingContext fields |
| `internal_summary.py` | 48 | literature decision-context fields (above) | a104.literature_source_inputs, a104.literature_ratio_source_render, services.workflow.store; BindingContext fields |
| `population_task_context.py` | 56 | owned population sources and last failed population attempt | a104.literature_task_selection, services.workflow x2 (store.db, run_id), sqlite_master x2, table 'runtime_actions' x2 |
| `source_custody.py` | 39 | reference-in-scope, artifact by representation, within-source walk, page validation | none (services.reference_in_scope/read_record) |
| `source_catalog.py` | 33 | allowed tools, execution.estimate limit, population tools | a104.composition_information (CONTRACT_ARGUMENT_TRANSPORT) |
| `source_admission.py` | 65 | within-source checks, **sheet_key lock**, population source walk, repository access authorization | none beyond BindingContext fields |
| `source_operations.py` | 47 | population routing to repositories; tool execution; state.query re-authorization | a104.literature_contract_error |
| `source_text_inputs.py` | 19 | text-witness materialization through admitted source.read | a104.literature_assay_inputs |
| `source_repositories.py` | 305 | one repository per numerical population; assay-grading cell reader | services.workflow.store x36, services.workflow.run_id x36, a104.literature_rate_meaning_delivery, lit storage 36 |
| `repository_display.py` | 190 | display contexts for rate, rate domain, rate meaning, received facts, endpoint, precision, comparison, window, controlled response, gel | a104.literature_rate_source_render x3, a104.literature_received_fact_render, a104.literature_work_report, services.workflow.store, lit storage 5 |
| `population_routes.py` | 74 | namespace, requested field, provider, defaults and repository tuples | lit storage/calc 37 |
| `scientific_interpretation.py` | 53 | reasoning schema extension; source_lead; delegation to required grading | a104.literature_task_credit x3, a104.literature_contract_error, services.workflow.store |
| `evidence_grading.py` | 89 | required grading in the original action (above) | a104.library.required_evidence_contracts, a104.literature_assay_inputs |
| `credit.py` | 21 | scientific credit; LiteratureTaskCredit projector; A105 check under assay grading | a104.literature_task_credit |
| `yield_estimator.py` | 22 | private yield controller from the declared binding | a104.literature_task_credit x2, `_private_yield_controller` x2 |
| `waiting.py` | 8 | supports_wait False | none |
| `to_parent.py` | 14 | report validation | BindingContext fields |
| `report_fields.py` | 11 | fact sources (screening, leads, rate) | a104.literature_task_credit |
| `report_reference_access.py` | 11 | reference resolution in context | none (contracts.reference_in_context, from a104.episode_bindings) |
| `report_facts.py` | 27 | screening and leads facts; completed work and scoring sheets | a104.literature_task_credit, a104.literature_sheet_updates, a104.literature_work_report, services.workflow.store x2 |
| `numerical_report_facts.py` | 74 | rate facts from committed and current sheets, with version checks | a104.literature_sheet_updates, services.workflow.store, lit storage 2 |
| `report_field_contracts.py` | 82 | `_rate_fact_sources` cell namespaces and schemas | a104.literature_numerical_contracts, a104.literature_rate_domains, a104.literature_rate_meaning_delivery, lit storage 36 |
| `received_reports.py` | 49 | receiver-side cell facts (inert for this leaf) | none |
| `received_evidence.py` | 119 | receiver-side cell intake and evidence tokens (inert) | a104.literature_sheet_updates, a104.method_loop.durable, services.workflow.store, lit storage 15 |
| `received_report_admission.py` | 115 | receiver-side report admission (inert) | a104.literature_task_credit, a104.literature_a105_worksheet, a104.domain x2, services.workflow.store |
| `task.py` | 97 | loop order: failed-source end, model-call failure gives SourceEnd | a104.runtime x2 (FACT_MEANINGS, FACT_SOURCES, SourceEnd, WorkflowError, ...), a104.providers (ModelCallError), a104.episode_source_failure, a104.library.live_runtime_functions/bind_functions; self.workflow.journal x4, inprocess_replay x4, execution_binding x2, completions x2, completed_unit x3, selected x2, next_return, resolve_pending_deliveries, action_schema, delivery_resolution_inputs, store x3, run_id; tables runtime_episodes, runtime_actions x2, runtime_model_calls |
| `task_state.py` | 117 | report_values starts as the parent's initial_report; interpretation schema from report contract | a104.runtime (ActionLeaf, EFFECT_VERSION, Episode, Record, interpretation_schema), a104.episode_source_failure, bind_functions; workflow.context, workflow.grains; self.workflow.journal x5, completions x4, inprocess_replay x7, execution_binding x4, progress_provider x2, recover_commissions, archive, source_credit_view, controller_value, store x2, run_id; runtime_actions x5 |
| `task_decision.py` | 156 | decision context additions; A104 head validation | a104.runtime (many), a104.episode_work_report x2, a104.library.hpc_prompt, bind_functions; self.workflow.evolutionary_history_evidence_binding, episode_bindings (initial_decision_context), binding_context x3, receipts x4, resource_estimator x5, job_episodes x4, decision_protocol x3, is_job_source x3, launch_instructions x2, native_event_information x2, provider x2, validate_contract_information x2, uses_received_record_context x2, and others (see TSV); runtime_model_calls x5 |
| `decision_provider.py` | 60 | use the episode's prompt renderer with the model provider | a104.providers x2 (_ORIGINAL_MODEL_* identities), root.providers (_ORIGINAL_* identities), a104.runtime; self.workflow.provider, specialist x2 |
| `decision_exchange.py` | 113 | request_context exchange loop | a104.runtime x2, bind_functions; self.workflow.decision_exchanges, journal, execute, services, controller_binding, validate_contract_information, run_id; runtime_model_calls x2 |
| `decision_contracts.py` | 133 | exchange schema and response validation | a104.runtime x2, bind_functions; self.workflow.decision_exchanges x2, validate_contract_information x2, contract_information_reply, journal, store x2; runtime_model_calls |
| `decision_context.py` | 58 | generic decision fields (above) | a104.runtime x2, bind_functions; self.workflow.working_state, journal x3 (db.execute, elapsed_view, row), store x3, source_credit_view, source_credit_binding, receipt_projection, pending_work, delivery_status, controller_binding, catalog, knowledge, job_episode_options, extra_report_sources, annotation_context, is_scientific_source, specialist, binding_context, tools, local_outcome_preview, run_id; runtime_actions x2 |
| `task_action.py` | 160 | empty-commit rejection; report_update admitted with every action; reason via the binding's execute_reasoning | a104.runtime x2, a104.read_mapping, bind_functions; self.workflow.journal x3, execution_binding x5, store x6, decision_exchanges x3, specialist x2, binding_context x2, controller_value x2, selected, execute, perform_selected_wait, receive_outcome, receive_native_outcome, automatic_score_updates, source_credit_view, last_observed_credit, retain_shared_grading_results, pending_work, resolver, validate_report, reasoning_action_schema, permits_common_action, completions, run_id x2; runtime_actions x6, runtime_model_calls |
| `task_suspension.py` | 9 | records the suspension condition | self.workflow.execution_handle x2, execution_backend |
| `task_report_delivery.py` | 32 | form = report_values plus facts | a104.runtime (Record, form_with_facts), bind_functions; self.workflow.journal x2, facts, release x2, source_credit_view, pending_handles, episode_bindings (current_report_facts), binding_context; runtime_forms x2 |
| `task_presentation.py` | 43 | prompt state machine across bootstrap, update and lookup frames | a104.providers (DECISION_CONTEXT_VERSION, apply_state_frame, renderers, text_instructions) |
| `presentation_selection.py` | 34 | renderer choice by context kind | a104.providers, a104.library.hpc_prompt, a104.library.monitor_prompt, a104.library.source_component_prompt, a104.receiver_prompt, a104.literature_experimental_prompt, a104.native_profile_presentation, a104.evolutionary_history_evidence_prompt x2 |

Each of the `task*`, `decision_contracts`, `decision_exchange` and `decision_context` files ends by rebinding its methods into `a104.runtime` through `a104.library.live_runtime_functions.bind_functions` (`_bind_preserved_runtime_providers`). This is old-runner machinery, not intent.

Per-name use counts are in `runs/carry_over/calls/a104_08.tsv`.
