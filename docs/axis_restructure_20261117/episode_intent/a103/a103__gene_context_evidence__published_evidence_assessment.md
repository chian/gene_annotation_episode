# a103/gene_context_evidence/published_evidence_assessment — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/published_evidence_assessment/`
(35 files directly in the folder; no `grading/` or `scoring/` subfolder). The child folder
`evidence_search_strategy_improvement/` was not read for this page. Nothing from the old shared root was
read; where behaviour lives there, this page names only what the episode's own file asks of it.

Old binding: class `LiteratureEpisode`, `binding_path = 'gene_context_evidence/published_evidence_assessment'`,
`commissioning_parent = 'gene_context_evidence'`, role `literature`, entry role `literature`, version
`literature_episode_binding_v1`. Decision source: `SourceInvestigationTask`. Prompt renderer:
`render_receiver_prompt` (`task_presentation.py`).

## What this episode is for

It is the A103 head's literature investigation: it works out which published evidence bears on the
assigned gene-context question. In its own words (`goal.py`):

> For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene
> identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their
> source and scope.
>
> Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary
> searches and source reads directly, or assign a strategy investigation when that narrower question
> warrants iteration.

`internal_summary.py` adds: "source discovery alone is not A103 evidence."

## Task and instructions

- One unit is one model-selected action. The permitted common actions are only `tool`, `child` and
  `redeliver_report` (`action_policy.py`). It may not use `reason` (`source_interpretation.py`: reasoning
  schema `None`; executing one raises `a103_literature_reasoning_not_commissioned`) or `wait`
  (`waiting.py`: `supports_wait = False`).
- Instructions (`task_instructions.py`): the general `INSTRUCTIONS` text (one ordinary tool, one typed
  reasoning commitment or one substantive child; no stop action or turn budget; source-bound extraction
  with exact byte spans and quotes; image.view rules; primary methods and results needed for a scientific
  claim; same-source-claim and replacement rules; extent basis; context allocation; report_update rules;
  redeliver_report; restored history), then the binding's goal text above appended (this binding does not
  set `replaces_default_instructions`). It then adds tool knowledge, the launch instruction library, the
  pending-child-delivery paragraph, and the wait and native-event paragraphs when those actions are
  permitted. Under `decision_exchange_v1` the restored-history paragraph is replaced by the
  `request_context` guidance. `REASONING_COMMIT_REQUIREMENT` is added only when `reason` is permitted, and
  it never is here.

## What it reads from its parent's assignment

`from_parent.py`: form `{version: 'literature_assignment_v1', question_context_refs: [ref], source_refs: [ref]}`
(both unique reference arrays; the form is closed by `obj`). Every reference in a `*_refs` field must be
in the scope. `source_refs` must be in namespace `source`, while `question_context_refs` may be in any
namespace. `prepare_assignment` requires a non-empty `operation_key`. From the request it also reads
`initial_report` (the starting report values), the report contract, `job_assignment`,
`episode_assignment.launch_instructions` and the scope.

## Children

| Old role | Child episode | Sent | Taken back |
|---|---|---|---|
| `literature_strategy` | `evidence_search_strategy_improvement` | `to_child_evidence_search_strategy_improvement.py`: a goal (root goal with `result_contract={'role': name}` when there is no parent, otherwise a child goal of the parent with `result_contract = contract.schema`); message `{scope, initial_report}`, plus when present `inprocess_completion_order`, `report_contract_declaration` (validated against the expanded contract via `validate_saved_fact_form`), `job_assignment`, `episode_assignment` (launch instructions materialized), `gene_context_evidence`, and `knowledge_inheritance` (receipt binding to the parent episode). Child assignment form: `strategy_assignment_v1` (`question_context_refs`, `prior_search_refs`). | `from_child_evidence_search_strategy_improvement.py`: the admitted typed form. The parent reuses any recorded admission references, passes the form to the progress provider (a role-specific counterpart when the binding has one), collects the references in the form plus the binding's received-form references, adds native timing receipts saved on the report attempt, registers receipts (`child_form` or `report_redelivery`) and adds tool attributions. |

`_CHILDREN['literature'] = ('literature_strategy',)`. Its only child is the strategy episode.
`episode.py:create_binding_tree` builds this binding and the six descendant bindings: strategy, search
(`source_relevance_assessment`), page (`source_evidence_examination`), table, coverage and passage.

## Decision state and what it shows the model

State (`task_state.py`): call count, feedback, last outcome and its index, report values (from
`initial_report`) and the records they rest on, and replay and checkpoint bookkeeping.

Model inputs (`decision_state.py`): goal, scope, working state, visible record references, current
credit, current evidence vector, investigation progress (when the receipt projection applies), credit
binding, controller state, last outcome, feedback, visual evidence from the last `image.view`, child
reports, and annotation context. In annotation-axis credit mode the working state is emptied and
proposed annotations and comparisons are shown instead. It also shows available report facts and
`_completed_work_axis_results` (A103 sheet, target sheets, tool attachments, source contributions) for
the completed-action reports.

The binding's own block (`internal_summary.py`): `literature_assignment`, `literature_source_custody` (for
each assigned source: `version, artifact_ref, text_ref, stdout_ref, stderr_ref, parent_source_refs`),
`own_literature_outcomes` (this episode's own outcomes of the acquisition and read tools, first page of
`outcome_page_size`, default 8), and `literature_history_meaning`.

Added before each decision (`decision_inputs.py`): resource context, shared information context, the
launch instruction library and selected launch instructions, child options, the binding's initial
context (empty here), completed action reports, requested action history (HPC context only), pending
work, execution expectations for grain `literature`, resource and native estimates, native event
targets, and the contract-information profile.

Presentation (`task_presentation.py`, `task_presentation_policy.py`): a text TASK prompt (see the table
below) followed by episode steering. The renderer is chosen by context kind, and prompt state is kept
per episode across decision frames.

Admission (`task.py`): an invalid selection gives feedback and a `rejected` effect with no unit. The
report update is admitted separately (grain `literature`), so an invalid report keeps the selected work.

## Tools it offers

`source_operations.py`: from the actual scoped tool catalog, only these:

- access: `state.query, source.read, source.locate, source.sequence.scan, source.sequence.references,
  source.experimental.records, image.view, source.archive.members, source.archive.extract,
  source.xlsx.sheets, source.xlsx.rows, source.pdf.info, source.pdf.text, source.pdf.page,
  execution.estimate`;
- acquisition: `public.literature.search, public.literature.read, public.literature.sequence_identity,
  public.ncbi.search, public.pmc.versions, public.pmc.files, public.pmc.asset`.

Restrictions: `public.ncbi.search` database is restricted to `pubmed`. `execution.estimate` keeps only
its `source.xlsx.sheets`/`source.xlsx.rows` branches, and is dropped when it has neither. Input schemas
go through `source_location_inputs`. `source.locate`, `source.sequence.scan`, `source.sequence.references`
and `source.experimental.records` are authorized only on records this episode received. Argument or
reference failures return an `invalid` outcome with the error code. Any other tool raises
`tool_not_available_to_a103_literature_role`.

## How its credit is counted

Credit kind `scientific`. `credit_view` delegates to `services.scientific_credit(context, receiver_selection)`
(old shared root). `credit_projector` is `None`. In the task, credit is measured after every observed
outcome and enters the iterator (`controller_value`). A wait would carry the last credit. A failed tool
still enters with its measured credit (`task_state.record_execution_failure`). No automatic score
judgments (`scientific_records.py`).

## Continuation

`yield_estimator.py`: `continuation_task` returns `None` and `yield_controller` returns `None`. This
binding has no private yield estimator. The old runner's recorded controller decided continuation. When
carried over, the episode needs one of today's three estimators chosen by its settings. The old folder
does not name one.

## What it reports to its parent

`to_parent.py`: no own fact sources (`{}`). The report is the parent's typed form filled from the model's
`report_update` values. It is validated against the parent's original schema with this episode's
resolver, then `validate_received_report` (no-op). `report_delivery.py`: with no report contract it
returns `{credit, pending_handles, current facts}`. Otherwise it assembles facts once, builds the form
with `form_with_facts` and saves it (`runtime_forms`).

## Differences from similar episodes

- Its child `evidence_search_strategy_improvement` is a near-verbatim copy. The only differences are the
  role (`literature_strategy`), the assignment form (`strategy_assignment_v1` with `prior_search_refs`),
  the child it commissions (`literature_search`), the binding id and parent, no entry roles, and no
  `create_binding_tree`.
- Compared with the HPC prediction and results episodes, it is a scientific-credit episode with a child,
  without private yield, and it appends rather than replaces the default instructions.

## Files

Names: `self.workflow.<m>` = old runner member; `runtime.<x>` = `_live_original_runtime.<x>` (old `root.a103.runtime`); `import:root.a103.<m>` = import from the old shared root; `table:<t>` = old journal/receipt table; `yield:<n>` = old yield name; `BindingContext.<f>` = old binding-context field; `services.<m>` = old binding services callback. Every row is also in `runs/carry_over/calls/a103_06.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names (uses) |
|---|---|---|---|
| `action_policy.py` | 16 | `_role` guard over the seven literature roles; permitted common actions `tool`, `child`, `redeliver_report` (no `reason`, no `wait`) | `BindingContext.role`×1 |
| `binding_record.py` | 8 | binding record: version, binding id `gene_context_evidence/published_evidence_assessment`, `outcome_page_size` | none |
| `call.py` | 79 | one decision call: saved-request reuse, contract-information profile, literature numerical contract freeze, exchange protocol dispatch, history restore on fresh session | `import:root.a103.runtime`×2, `runtime._action_generation_schema`×1, `runtime._ASSIGNMENT_TRANSPORT`×1, `runtime.DECISION_EXCHANGE_PROTOCOL`×5, `runtime._digest`×1, `runtime.instructional_model_context`×1, `runtime._json`×4, `runtime.json`×2, `runtime._recorded_assignment_transport`×1, `runtime.WorkflowError`×5, `self.workflow.contract_information_profile`×1, `self.workflow.decision_exchanges`×1, `self.workflow.decision_protocol`×3, `self.workflow.freeze_contract_information`×1, `self.workflow.freeze_literature_numerical_contracts`×1, `self.workflow.history_preview`×1, `self.workflow.journal`×1, `self.workflow.numerical_contracts`×1, `self.workflow.provider`×1, `self.workflow.provider.has_session`×1, `self.workflow.receipts`×4, `self.workflow.services`×1, `self.workflow.uses_received_record_context`×2, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls`×5 |
| `child_commissioning.py` | 25 | children = `_CHILDREN['literature']` = (`literature_strategy`); request assembler and report receiver for that one child | none |
| `configuration.py` | 16 | only setting `outcome_page_size` (default 8, positive int); no contract-information profile | none |
| `credit.py` | 16 | credit kind `scientific`; credit view delegated to `services.scientific_credit`; `credit_projector` returns `None` | `services.scientific_credit`×1 |
| `decision_contracts.py` | 35 | exchange envelope schema (`request_context` or `select_action`) and its validation | `import:root.a103.runtime`×2, `runtime.composition_lookup_schema`×2, `runtime.Draft202012Validator`×1, `runtime._object`×3 |
| `decision_exchange.py` | 115 | pending-decision lookup loop: child options, composition information, own-attempt lookups; yield table for the model | `import:root.a103.runtime`×2, `runtime._action_generation_schema`×1, `runtime._category_yield_parameters`×1, `runtime.child_option_information`×1, `runtime.DECISION_CONTEXT_VERSION`×1, `runtime.instructional_model_context`×2, `runtime._json`×2, `runtime.lookup_attempts`×1, `runtime.Mapping`×3, `runtime.model_snapshot`×1, `runtime._plain`×2, `runtime._references_in`×1, `runtime.requested_contract_information`×1, `runtime.schema_failure_diagnostic`×2, `runtime.sqlite3`×1, `runtime.state_frame`×1, `runtime.ValidationError`×4, `runtime.yield_table`×1, `self.workflow.controller_binding`×1, `self.workflow.decision_exchanges`×1, `self.workflow.execute`×1, `self.workflow.journal`×1, `self.workflow.run_id`×1, `self.workflow.services`×1, `self.workflow.store`×2, `self.workflow.store.reference_subset`×1, `self.workflow.validate_contract_information`×1, `table:runtime_model_calls`×2 |
| `decision_inputs.py` | 65 | context additions: resource, shared information, launch library, child options, initial binding context, completed action reports, HPC history, pending work, execution expectations (grain `literature`), resource/native estimates, native event targets, profile | `import:root.a103.episode_work_report`×2, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×2, `runtime.child_option_information`×1, `runtime.Mapping`×1, `self.workflow.available_child_roles`×1, `self.workflow.binding_context`×2, `self.workflow.episode_bindings`×1, `self.workflow.execution_expectations`×1, `self.workflow.job_episodes`×2, `self.workflow.launch_instructions`×2, `self.workflow.native_estimation_context`×1, `self.workflow.native_event_information`×2, `self.workflow.pending_work`×1, `self.workflow.resource_context`×1, `self.workflow.resource_estimator`×4, `self.workflow.shared_information_context`×1, `self.workflow.store`×2 |
| `decision_provider.py` | 17 | provider dispatch with this episode's prompt renderer; conversation key | `import:root.a103.runtime`×1, `self.workflow.provider`×2, `self.workflow.provider.conversation_key`×1, `self.workflow.specialist`×1 |
| `decision_state.py` | 48 | model inputs: goal, scope, working state, visible refs, credit, evidence vector, controller state (annotation-axis mode trimmed), image.view visual evidence, annotation context, binding block, `_completed_work_axis_results`, available report facts | `import:root.a103.runtime`×2, `runtime.FACT_MEANINGS`×1, `runtime.FACT_SOURCES`×1, `runtime.json`×2, `runtime.Mapping`×3, `runtime._plain`×2, `runtime._references_in`×1, `self.workflow.annotation_context`×1, `self.workflow.binding_context`×1, `self.workflow.catalog`×1, `self.workflow.controller_binding`×1, `self.workflow.delivery_status`×1, `self.workflow.extra_report_sources`×1, `self.workflow.job_episode_options`×1, `self.workflow.journal`×3, `self.workflow.knowledge`×1, `self.workflow.local_outcome_preview`×1, `self.workflow.pending_work`×1, `self.workflow.receipt_projection`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_binding`×1, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×3, `self.workflow.store.reference_subset`×1, `self.workflow.tools`×1, `self.workflow.tools.model_contract_catalog`×1, `self.workflow.working_state`×1, `table:runtime_actions`×2 |
| `episode.py` | 45 | `LiteratureEpisode` composed from the mixins; `binding_path`, `commissioning_parent='gene_context_evidence'`, roles/entry roles `literature`; `create_binding_tree` builds this and six descendant bindings | none |
| `from_child_evidence_search_strategy_improvement.py` | 45 | receives the child's typed form: recorded admission refs, progress-provider hand-off, reference collection from the form, native timing receipts, receipt registration, tool attributions | `import:root.a103.delivery_counterpart`×1, `import:root.a103.episode_return_records`×1, `import:root.a103.runtime`×2, `runtime._json`×1, `runtime.json`×1, `runtime._references_in`×1, `runtime.WorkflowError`×1, `self.workflow.binding_context`×4, `self.workflow.episode_bindings`×1, `self.workflow.is_job_source`×2, `self.workflow.job_episodes`×2, `self.workflow.native_timing_information`×1, `self.workflow.progress_provider`×4, `self.workflow.receipts`×3, `self.workflow.receive_tool_attributions`×1, `self.workflow.run_id`×6, `self.workflow.specialist`×1, `self.workflow.store`×7, `table:runtime_report_attempts`×2 |
| `from_parent.py` | 34 | assignment form `literature_assignment_v1` {`question_context_refs`, `source_refs`}; every `*_refs` must be in scope (`source_refs` in namespace `source`); `prepare_assignment` requires a non-empty `operation_key` | none |
| `goal.py` | 9 | the A103 prefix (locus/genome identity, neighbour order/orientation/spacing/fusion/cooccurrence) + `_ROLE_INSTRUCTIONS['literature']` | none |
| `__init__.py` | 0 | empty package marker | none |
| `internal_summary.py` | 17 | model block: `literature_assignment`, `literature_source_custody` (version/artifact/text/stdout/stderr/parent refs of each assigned source), `own_literature_outcomes` (first `outcome_page_size` own outcomes of acquisition+read tools), `literature_history_meaning` | `BindingContext.assignment`×1, `BindingContext.episode_id`×1, `BindingContext.scope`×2, `services.own_outcomes`×1 |
| `received_evidence.py` | 20 | receives no report sources/facts/tokens from children (all empty) | none |
| `report_delivery.py` | 25 | finish: without a report contract returns credit + pending handles + current facts; with one, builds the form from report values + assembled facts once and saves it | `import:root.a103.library.private_policy_call`×1, `import:root.a103.library.report_fact_assembly`×1, `import:root.a103.runtime`×2, `runtime.form_with_facts`×1, `runtime._json`×2, `runtime.json`×1, `runtime.Record`×2, `self.workflow.binding_context`×1, `self.workflow.episode_bindings`×1, `self.workflow.facts`×1, `self.workflow.journal`×2, `self.workflow.pending_handles`×1, `self.workflow.release`×2, `self.workflow.source_credit_view`×1, `table:runtime_forms`×2 |
| `saved_decision_exchange.py` | 81 | authenticates saved exchange requests/history against frozen contract information | `import:root.a103.runtime`×2, `runtime.apply_state_frame`×1, `runtime.CONTRACT_INFORMATION_OPERATIONS`×1, `runtime.DECISION_CONTEXT_VERSION`×1, `runtime.instructional_model_context`×1, `runtime.is_contract_information`×1, `runtime._json`×8, `runtime.json`×1, `runtime.model_snapshot`×1, `runtime._recorded_action_generation_schema`×1, `runtime.requested_contract_information`×1, `runtime.ValidationError`×1, `runtime.WorkflowError`×9, `self.workflow.contract_information_reply`×1, `self.workflow.decision_exchanges`×2, `self.workflow.journal`×1, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls`×1 |
| `scientific_records.py` | 11 | no automatic score judgments; completing one raises `a103_automatic_judgment_unavailable` | none |
| `source_contracts.py` | 26 | shared constants of the literature family as copied into this folder: `VERSION='literature_episode_binding_v1'`, the seven literature `ROLES`, the `_CHILDREN` chain, `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, `_READ_TOOLS`, and all seven `_ROLE_INSTRUCTIONS` texts (this episode uses the `literature` one) | `import:root.a103.communication`×1, `import:root.a103.composition_information`×1, `import:root.a103.domain`×1, `import:root.a103.episode_bindings`×1 |
| `source_interpretation.py` | 14 | no reasoning action: schema `None`, executing reasoning raises `a103_literature_reasoning_not_commissioned` | none |
| `source_operations.py` | 44 | tool catalog: `_ACCESS_TOOLS` + `_ACQUISITION_TOOLS` from the scoped catalog; `public.ncbi.search` restricted to `pubmed`; `execution.estimate` kept only for `source.xlsx.*`; source-location inputs; `source.locate`/`source.sequence.*`/`source.experimental.records` limited to received records | `BindingContext.assignment`×1, `BindingContext.received_record_refs`×1, `BindingContext.scope`×3, `services.execute_tool`×1, `services.tool_catalog`×1 |
| `source_references.py` | 14 | `_require` (in scope or `literature_reference_unavailable`), `resolve` via `reference_in_context` | `BindingContext.role`×1, `services.read_record`×1, `services.reference_in_scope`×1 |
| `task_instructions.py` | 26 | the long general investigation `INSTRUCTIONS`, `REASONING_COMMIT_REQUIREMENT`, and the composer (binding text appended, tool knowledge, launch library, pending-delivery, wait and native-event paragraphs, exchange-protocol history replacement) | `self.workflow.binding_context`×1, `self.workflow.decision_protocol`×1, `self.workflow.is_job_source`×1, `self.workflow.job_episodes`×1, `self.workflow.knowledge`×1, `self.workflow.launch_instructions`×1, `self.workflow.native_event_information`×1, `self.workflow.permits_common_action`×3, `self.workflow.specialist`×1 |
| `task_presentation_policy.py` | 69 | chooses the renderer (HPC, published scientific, API launch, selected execution, monitor, receiver) and keeps per-episode prompt state across decision frames; JSON fallback | `import:root.a103.decision_context`×1, `import:root.a103.execution_prompt`×1, `import:root.a103.gene_context_evidence_prompt`×2, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.library.monitor_prompt`×1, `import:root.a103.native_profile_presentation`×1 |
| `task_presentation.py` | 171 | text prompt: TASK (instructions, assigned work, fixed scope, constraints, parent context/evidence, supplied material, callable Sources table, evidence-axis/thought-pattern/tool guidance, launch manuals, operations and operands, permitted children, child options, requested return, selection operands) + episode steering | `import:root.a103.gene_context_evidence_prompt`×1 |
| `task.py` | 199 | decision loop: replay/restore, model call, admission (`selected`), report-update admission with grain `literature`, action execution (reason/wait/tool), outcome receipt, automatic scoring, credit after every observed outcome, shared grading retention on `shared.read_information` | `import:root.a103.episode_source_failure`×1, `import:root.a103.library.action_contracts`×1, `import:root.a103.library.private_policy_call`×1, `import:root.a103.providers`×1, `import:root.a103.runtime`×2, `runtime.ActionFailure`×1, `runtime.ContractInformationError`×1, `runtime._decode_recorded_action_response`×1, `runtime.Draft202012Validator`×2, `runtime.EventTargetError`×2, `runtime.inspect`×1, `runtime._json`×5, `runtime.json`×8, `runtime.Mapping`×2, `runtime.nullcontext`×5, `runtime.observes_action_outcome`×1, `runtime.ReportBoundaryError`×1, `runtime.ReportRedelivery`×2, `runtime.schema_failure_diagnostic`×1, `runtime.SourceEnd`×2, `runtime.validate_form`×1, `runtime.ValidationError`×2, `runtime._wait_target_feedback`×2, `runtime.WorkflowError`×2, `self.workflow.action_schema`×1, `self.workflow.automatic_score_updates`×1, `self.workflow.binding_context`×1, `self.workflow.completed_unit`×3, `self.workflow.completions`×3, `self.workflow.controller_value`×2, `self.workflow.decision_exchanges`×3, `self.workflow.delivery_resolution_inputs`×1, `self.workflow.execute`×1, `self.workflow.execution_binding`×7, `self.workflow.inprocess_replay`×4, `self.workflow.journal`×7, `self.workflow.last_observed_credit`×1, `self.workflow.next_return`×1, `self.workflow.pending_work`×1, `self.workflow.perform_selected_wait`×1, `self.workflow.receive_native_outcome`×1, `self.workflow.receive_outcome`×1, `self.workflow.resolve_pending_deliveries`×1, `self.workflow.resolver`×1, `self.workflow.retain_shared_grading_results`×1, `self.workflow.run_id`×3, `self.workflow.selected`×3, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×8, `self.workflow.validate_report`×1, `table:runtime_actions`×8, `table:runtime_episodes`×1, `table:runtime_model_calls`×2 |
| `task_state.py` | 108 | source state: calls, feedback, last outcome, report values (from `initial_report`) and basis; failure recording that still enters the iterator with credit; restore/checkpoint | `import:root.a103.episode_source_failure`×1, `import:root.a103.runtime`×2, `runtime.ActionLeaf`×1, `runtime.EFFECT_VERSION`×1, `runtime.Episode`×1, `runtime.interpretation_schema`×1, `runtime._json`×2, `runtime.json`×4, `runtime._object`×1, `runtime._plain`×1, `runtime.Record`×1, `self.workflow.archive`×1, `self.workflow.completions`×4, `self.workflow.context`×1, `self.workflow.controller_value`×1, `self.workflow.execution_binding`×4, `self.workflow.grains`×1, `self.workflow.inprocess_replay`×7, `self.workflow.journal`×5, `self.workflow.progress_provider`×2, `self.workflow.recover_commissions`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_view`×1, `self.workflow.store`×2, `table:runtime_actions`×5 |
| `task_suspension.py` | 9 | records suspension condition on the execution handle | `self.workflow.execution_backend`×1, `self.workflow.execution_handle`×2 |
| `to_child_evidence_search_strategy_improvement.py` | 32 | assembles the child request: goal (root or child of parent goal with the contract schema), message {scope, initial_report, optional in-process order, report contract declaration, job/episode assignment, `gene_context_evidence`}, episode identity, receipt inheritance | `import:root.a103.episode_contract_information`×1, `import:root.a103.runtime`×2, `runtime.ContractInformationError`×1, `runtime.Episode`×2, `runtime.EpisodeGoal`×2, `runtime.EpisodeRequest`×1, `runtime._plain`×3, `runtime.Record`×1, `runtime.validate_saved_fact_form`×1, `self.workflow.context`×2, `self.workflow.grains`×2, `self.workflow.inprocess_completion_order`×2, `self.workflow.launch_instructions`×1, `self.workflow.receipts`×2 |
| `to_parent.py` | 21 | no own fact sources (`fact_sources`/`facts`/`current_report_facts` return `{}`); report validated against the parent's form with this episode's resolver, then `validate_received_report` | `BindingContext.assignment`×1, `BindingContext.scope`×1 |
| `waiting.py` | 8 | `supports_wait = False` | none |
| `yield_estimator.py` | 12 | `continuation_task` and `yield_controller` both return `None` (no private continuation; the runner's recorded controller decides) | none |

## Carried over

One row per row of `runs/carry_over/functions/a103__gene_context_evidence__published_evidence_assessment.tsv`. Old file names are the files at 97308b94c. The old sources could not be read in this run (no git history is reachable from the working directory, so `git show 97308b94c` was unavailable): the classification rests on this record's own file table, the function list and the carried child episode. Library pieces named are existing `episode_support/` functions called by this episode; none was added or moved. Pieces without a home in this episode are marked unplaced and are listed in `docs/axis_restructure_20261117/carry_over_blocked/a103__gene_context_evidence__published_evidence_assessment.md`. Functions that are not in the library stay in the episode file that uses them (`task.py`: `instructions`, `catalog`, `admitted`, `run_operation`, `source_operands`, `section`, `present`; library candidates, since the sibling A103 and A101 episodes carry copies).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_policy.py | SourceActionPolicy | machinery | old class shell of the old runner; its methods have their own rows |
| action_policy.py | SourceActionPolicy._role | machinery | old runner role check of the seven literature roles; the class-definition checks and the binding path replace it |
| action_policy.py | SourceActionPolicy.permitted_common_actions | machinery | old runner action-kind permission (tool, child, redeliver_report); task.py decide/action offer tool and child units (redelivery does not exist) |
| binding_record.py | SourceEpisodeBindingRecord | machinery | binding_record.py / the binding's own as_record() (README 3e) |
| binding_record.py | SourceEpisodeBindingRecord.as_record | machinery | binding_record.py / the binding's own as_record() (README 3e) |
| call.py | SourceTaskCall | machinery | old decision call: replay of saved requests, contract-information checks, receipts, exchange protocol |
| call.py | SourceTaskCall.call | machinery | old decision call: replay of saved requests, contract-information checks, receipts, exchange protocol; the model request is task.py decide |
| call.py | SourceTaskCall.instructions | episode function | task.py instructions(knowledge=, launch=) |
| child_commissioning.py | SourceChildCommissioning | machinery | old class shell of the old runner; its methods have their own rows |
| child_commissioning.py | SourceChildCommissioning.allowed_children | episode function | task.py CHILD_SLOTS (the one slot evidence_search_strategy_improvement) |
| child_commissioning.py | SourceChildCommissioning.child_roles | episode function | task.py CHILD_SLOTS |
| child_commissioning.py | SourceChildCommissioning.child_request_assembler | episode function | messages/msg_to_child.py msg_to_child |
| child_commissioning.py | SourceChildCommissioning.child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| configuration.py | SourceEpisodeConfiguration | machinery | old configuration class; outcome_page_size is the constant OUTCOME_PAGE_SIZE of messages/internal_summary.py, the run settings are ctx.settings |
| configuration.py | SourceEpisodeConfiguration.__init__ | episode function | messages/internal_summary.py OUTCOME_PAGE_SIZE = 8 (the one setting the episode owned) |
| configuration.py | SourceEpisodeConfiguration.contract_information_configuration | machinery | contract-information freezing (old shared root content, returned None); README 5 item 16 |
| configuration.py | SourceEpisodeConfiguration.contract_information_profile | machinery | contract-information freezing (old shared root content, returned None); README 5 item 16 |
| credit.py | SourceInvestigationCredit | machinery | old class shell of the old runner; its methods have their own rows |
| credit.py | SourceInvestigationCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | SourceInvestigationCredit.credit_view | episode function | credit.py credit (library episode_support/grading/gene_context_evidence/credit.py A103ContextCredit; already in library) |
| credit.py | SourceInvestigationCredit.credit_projector | episode function | credit.py (A103ContextCredit named there; the old method returned None) |
| decision_contracts.py | SourceDecisionContracts | machinery | decision-exchange loop (request_context / select_action envelope) |
| decision_contracts.py | SourceDecisionContracts.exchange_schema | machinery | decision-exchange loop |
| decision_contracts.py | SourceDecisionContracts.exchange_response | machinery | decision-exchange loop |
| decision_exchange.py | SourceDecisionExchange | machinery | decision-exchange loop |
| decision_exchange.py | SourceDecisionExchange.interpretation_context | machinery | decision-exchange loop (published_references of lookup results); a lookup is a tool unit whose outcome is in the summary |
| decision_exchange.py | SourceDecisionExchange.exchange_decision | machinery | decision-exchange loop; lookups are tools (tool_catalog and the access tools); the yield table is internal_summary action_yields |
| decision_inputs.py | SourceTaskDecisionInputs | machinery | old class shell of the old runner; its methods have their own rows |
| decision_inputs.py | SourceTaskDecisionInputs.decision_inputs | episode function | task.py decide (tool knowledge, launch-instruction library from settings, child options in present) and messages/internal_summary.py; the other pieces are unplaced (blocked file) |
| decision_provider.py | SourceDecisionProvider | machinery | provider call and conversation key; ModelRequest and the system's recorded call replace it |
| decision_provider.py | SourceDecisionProvider.conversation_key | machinery | conversation state (README 3a) |
| decision_provider.py | SourceDecisionProvider.complete_decision | machinery | model call through the provider; decide returns ModelRequest('REASONING', ...) |
| decision_state.py | SourceTaskDecisionState | machinery | old class shell of the old runner; its methods have their own rows |
| decision_state.py | SourceTaskDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (catalog, visual_evidence, child_reports, action_yields, report, report_lifecycle) and task.py decide; root-only and report-delivery pieces unplaced (blocked file) |
| episode.py | LiteratureEpisode | episode function | episode.py PublishedEvidenceAssessment (binding_path, goal, unit, result, child_slots from goal.py / task.py) |
| episode.py | create_binding_tree | episode function (unplaced) | Built the head binding and its six descendant bindings: a table of bindings. Not carried and not replaced: no table or list of bindings exists (AGENTS.md); the registry is built by the caller of link. Listed in the blocked file |
| from_child_evidence_search_strategy_improvement.py | receive_evidence_search_strategy_improvement_report | episode function | messages/read_from_child.py read_from_child (credit and finding of the child); recorded admission references, progress-provider hand-off, reference collection, native timing receipts, receipt registration (child_form, report_redelivery), runtime_report_attempts and tool attributions are machinery |
| from_parent.py | SourceAssignment | machinery | old class shell of the old runner; its methods have their own rows |
| from_parent.py | SourceAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | SourceAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (version literature_assignment_v1, question_context_refs, source_refs, plus the new scope, received_record_refs, gene_context_evidence) |
| from_parent.py | SourceAssignment._validate_assignment | episode function (unplaced) | Store checks of the commission (each ref in scope, each source_refs entry a source record, an operation key): a wrong commission fails (rule 1); read_from_parent has no records. Listed in the blocked file |
| from_parent.py | SourceAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (the operation-key check is not carried: the system journals units) |
| goal.py | SourceInvestigationGoal | machinery | old class shell of the old runner; its methods have their own rows |
| goal.py | SourceInvestigationGoal.instructions | episode function | goal.py GOAL (the A103 sentence and the literature role sentence) |
| internal_summary.py | SourceInvestigationSummary | machinery | old class shell of the old runner; its methods have their own rows |
| internal_summary.py | SourceInvestigationSummary.initial_decision_context | episode function | messages/internal_summary.py internal_summary (returned {}; nothing to carry) |
| internal_summary.py | SourceInvestigationSummary.decision_context | episode function | messages/internal_summary.py internal_summary (assignment, source_custody built from source_refs, own_literature_outcomes via library outcome_page, history meaning) |
| received_evidence.py | SourceReceivedEvidence | machinery | received-report hooks, all empty or None |
| received_evidence.py | SourceReceivedEvidence.received_report_sources | machinery | received-report hook returning {}; child fields are declared by the child |
| received_evidence.py | SourceReceivedEvidence.received_report_facts | machinery | received-report hook returning {} |
| received_evidence.py | SourceReceivedEvidence.received_form_references | machinery | received-form references hook returning []; records come back in custody |
| received_evidence.py | SourceReceivedEvidence.received_evidence_tokens | machinery | received-evidence hook returning [] |
| received_evidence.py | SourceReceivedEvidence.validate_received_report | machinery | received-report validation (no-op); the system admits the child result against its form |
| report_delivery.py | SourceTaskReportDelivery | machinery | old class shell of the old runner; its methods have their own rows |
| report_delivery.py | SourceTaskReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (RETURN_FORM credit + finding); runtime_forms saving, pending_handles and release are machinery |
| saved_decision_exchange.py | SourceSavedDecisionExchange | machinery | saved-request replay checks |
| saved_decision_exchange.py | SourceSavedDecisionExchange.validate_contract_exchange_request | machinery | saved-request replay checks (the system compares a rebuilt model request with its record) |
| saved_decision_exchange.py | SourceSavedDecisionExchange.validate_contract_exchange_history | machinery | saved-request replay checks |
| scientific_records.py | SourceScientificRecords | machinery | old class shell of the old runner; its methods have their own rows |
| scientific_records.py | SourceScientificRecords.automatic_score_judgments | machinery | hook returning []; no automatic score judgments |
| scientific_records.py | SourceScientificRecords.complete_score_judgment | machinery | hook that raised a103_automatic_judgment_unavailable; nothing to carry |
| source_interpretation.py | SourceInterpretation | machinery | no reasoning action in this episode (all hooks None / False / raising) |
| source_interpretation.py | SourceInterpretation.reasoning_action_schema | machinery | no reasoning action (returned None) |
| source_interpretation.py | SourceInterpretation.reasoning_has_task_content | machinery | no reasoning action (returned False) |
| source_interpretation.py | SourceInterpretation.execute_reasoning | machinery | no reasoning action (raised a103_literature_reasoning_not_commissioned) |
| source_operations.py | SourceOperations | machinery | old class shell of the old runner; its methods have their own rows |
| source_operations.py | SourceOperations.catalog | episode function | task.py catalog (access + acquisition lists, ncbi limited to pubmed, execution.estimate cut to xlsx branches, source_location_inputs) and tool_catalog |
| source_operations.py | SourceOperations.execute | episode function | task.py run_operation and the 22 module-level tools (invalid outcome with arguments_or_reference feedback; permitted_record_refs = ctx.store.refs() for the four source-locating tools) |
| source_operations.py | SourceOperations._tool_arguments | episode function | task.py admitted (offered operation and schema; the per-call assignment re-validation is not carried) |
| source_references.py | SourceReferences | machinery | old class shell of the old runner; its methods have their own rows |
| source_references.py | SourceReferences._require | episode function (unplaced) | Store check in scope then read of an episode's own commission; custody (records.holds / get) replaces it, a wrong commission fails |
| source_references.py | SourceReferences.resolve | episode function | messages/final_to_parent.py validate_report (references of the report held by this episode, records.holds in internal_summary report_sources_held) |
| task.py | SourceInvestigationTask | machinery | old decision-source class: replay/restore, exchange, credit hand-off to the controller |
| task.py | SourceInvestigationTask.next | episode function | task.py decide (first unit is the tool_catalog lookup, then the model request); replay branches, call counting and source_failed are machinery |
| task.py | SourceInvestigationTask.apply_response | episode function | task.py action (rejection of an invalid answer through Rejected; report update admission is the report tool) |
| task.py | SourceInvestigationTask.execute | episode function | task.py TOOLS and ChildCall (tool and child branches; reason and wait branches never offered); outcome recording and credit hand-off are the system's |
| task_instructions.py | instructions | episode function | task.py instructions(knowledge=, launch=) over library literature_investigation_prompt.INSTRUCTIONS (already in library); reasoning, wait, redelivery and exchange paragraphs dropped |
| task_presentation.py | _text | machinery | helper of the old renderer; not needed (task.py section / present use json.dumps) |
| task_presentation.py | render_requested_return | episode function | task.py present, section Return (the child return form is FINDING_FORM.as_record()) |
| task_presentation.py | _goal | episode function | task.py present, section Assigned work |
| task_presentation.py | _guidance | episode function (unplaced) | evidence-axis, thought-pattern, child-tool-info and annotation-support guidance and launch manuals: no home here; listed in the blocked file |
| task_presentation.py | _source_operands | episode function | task.py source_operands |
| task_presentation.py | _task | episode function | task.py present (assigned work, scope, parent constraints, context, evidence operands, sources, operations, child investigation) |
| task_presentation.py | render_receiver_prompt | episode function | task.py present |
| task_presentation_policy.py | _ordinary_runtime_receiver_context | machinery | renderer-choice helper of the old policy (HPC, API launch, monitor renderers); this episode has one prompt |
| task_presentation_policy.py | present_source_task | machinery | renderer choice per state frame (decision_bootstrap / update / lookup frames); the single prompt is task.py present |
| task_state.py | SourceTaskState | machinery | decision-source state: checkpoint, restore, replay |
| task_state.py | SourceTaskState.__init__ | machinery | decision-source state (call count, feedback, last outcome, report values); state is the view: internal_summary |
| task_state.py | SourceTaskState.bind_execution_context | machinery | execution-context binding of the old runner |
| task_state.py | SourceTaskState.record_execution_failure | machinery | record_execution_failure; a tool returns its failure as its outcome (failure_outcome in task.py run_operation) |
| task_state.py | SourceTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | SourceTaskState.restore | machinery | checkpoint/restore |
| task_state.py | SourceTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | SourceTaskState.checkpoint | machinery | checkpoint/restore |
| task_suspension.py | SourceTaskSuspension | machinery | wait/suspension machinery |
| task_suspension.py | SourceTaskSuspension.suspension_changed | machinery | wait/suspension machinery |
| to_child_evidence_search_strategy_improvement.py | EvidenceSearchStrategyImprovementRequest | machinery | old class shell of the old runner; its method has its own row |
| to_child_evidence_search_strategy_improvement.py | EvidenceSearchStrategyImprovementRequest._assemble_evidence_search_strategy_improvement_request | episode function | messages/msg_to_child.py msg_to_child (objective, scope, strategy assignment with the question context, the model-chosen prior-search sources and every held record in received_record_refs, gene_context_evidence); the goal/report-contract wiring, inprocess_completion_order, report_contract_declaration (validate_saved_fact_form), job_assignment, episode_assignment, initial_report and the receipt inheritance (knowledge_inheritance) are machinery or unplaced (blocked file) |
| to_parent.py | SourceInvestigationReport | machinery | old class shell of the old runner; its methods have their own rows |
| to_parent.py | SourceInvestigationReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (the old fact sources were empty; the form declares credit and finding, finding being the assessment) |
| to_parent.py | SourceInvestigationReport.facts | episode function | messages/final_to_parent.py final_to_parent (old facts were {}; returns credit and finding) |
| to_parent.py | SourceInvestigationReport.current_report_facts | machinery | hook returning {}; no report facts |
| to_parent.py | SourceInvestigationReport.validate_report | episode function | messages/final_to_parent.py validate_report (form check and held-reference check of the assessed sources; the first-line assignment re-validation against the Store is unplaced, blocked file) |
| waiting.py | SourceInvestigationWaiting | machinery | wait machinery (waiting not supported) |
| waiting.py | SourceInvestigationWaiting.supports_wait | machinery | wait machinery (returned False) |
| yield_estimator.py | SourceInvestigationYield | machinery | old class shell of the old runner; its methods have their own rows |
| yield_estimator.py | SourceInvestigationYield.continuation_task | machinery | returned None; continuation_task is deleted (README 3d) |
| yield_estimator.py | SourceInvestigationYield.yield_controller | episode function | yield_estimator.py yield_controller (old returned None = default; BoundedQualityYieldController chosen from A103ContextCredit) |
