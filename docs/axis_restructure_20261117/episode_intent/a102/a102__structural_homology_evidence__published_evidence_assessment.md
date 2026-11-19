# Episode intent: `a102/structural_homology_evidence/published_evidence_assessment`

Source: this episode's own files at commit `97308b94c` (28 Python files, 1,614 lines, directly in the folder; it has
no `tests/`, `grading/` or `scoring/` folder). Old role name: `literature`. Old class: `LiteratureEpisode` (fifteen
mixins), task class `SourceTask`. Old `binding_path`: `structural_homology_evidence/published_evidence_assessment`;
old `commissioning_parent`: `structural_homology_evidence` (the A102 axis head). It is also an old entry role.

## What this episode is for

It investigates which published evidence bears on the scientific question its parent assigned, reading and
searching sources itself or assigning a narrower search-strategy investigation to its child. Goal text, verbatim
from `goal.py`:

> Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches
> and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.
> This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted child forms
> inform later choices; no child order, reading quota or complete-document requirement is prescribed. A one-off
> search/read is an ordinary tool. A supplied reading selector is context, not an automatically executed action.
> Preserve the source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors.
> Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications can
> advance the investigation. Commit interpretations with the common reasoning action and update only the parent's
> declared typed form in that same work call. Navigation, byte coverage and repeated reading earn no scientific
> credit by themselves. The commissioned task's own yield settings guide continuation.

The module docstring of `source_contracts.py` states the division: the binding supplies operands, ordinary
operations, source custody and the commissioned task's yield binding; the decision source owns decisions, reasoning
commits, commissioning and report updates; a reading selection is information, never a script the binding executes.

## Task and instructions

One unit is one model-selected action of kind `tool`, `reason` (a reasoning commit, optionally with a
`source_lead`), `child` (commission the strategy child) or `redeliver_report` (repair a finished child's typed
return). It does not support waiting (`supports_wait` is false).

Instructions (`task_instructions.py`): the default (or job) instructions with this goal appended; the
reasoning-commit requirement; tool-knowledge and launch-instruction text when present; the pending-child
redelivery paragraph (use `redeliver_report` with a corrected form built only from saved child facts, preserving
`current_report_update`); the wait and native-event paragraphs only when wait is permitted (never, here); the
exchange-history wording under the exchange protocol.

Construction settings (`episode.py`): `outcome_page_size` (integer ≥ 1, default 8), `structure_population`
(boolean), `reference_parent_sources` (unique non-empty refs; requires structure population),
`contract_information_profile` (only the composition profile, and only with structure population),
`private_yield_binding` (boolean), `yield_bindings` (requires the private binding; validated by the old literature
task credit module). `reference_evidence(services, source_refs=...)` is an explicit entry that defaults to structure
population and on-demand contract information for a caller-assigned reference-source investigation.

## What it reads from its parent's assignment

Form `literature_assignment_v1` (`from_parent.py`):

| Field | Meaning |
|---|---|
| `version` | `literature_assignment_v1` |
| `question_context_refs` | References that state the question context (must be in scope) |
| `source_refs` | Sources assigned for reading (must be in-scope sources) |
| `literature_task` | The commissioned literature task (old `task_schema`); required with the private yield binding, where its `credit_unit` is filled from the declaration rather than supplied |
| `proposed_annotation_ref` | The annotation under assessment; required with the private yield binding and must equal the parent's |
| requested structure components | The field named by the old `a102_literature_bindings.REQUESTED` (which structure components the parent asks for) |

`prepare_assignment` (run when the parent commissions it): with the private yield binding, the task key selects a
declaration; `credit_unit` and `yield_settings` (`kind`, `cutoff`, `uncertainty_alpha`) are written into the task
from it, and a task that supplies different values is refused (`literature_task_supplied_yield_binding_mismatch`); a
missing declaration raises `literature_yield_binding_missing_for_task`.

## Children

| Slot (old role) | Child | What it sends | What it takes back |
|---|---|---|---|
| `literature_strategy` | `published_evidence_assessment/evidence_search_strategy_improvement` | A child goal refining its own; a message with scope, initial report, optional report-contract declaration (validated against the expanded contract), job and episode assignments, structural-homology context and knowledge inheritance (`to_child_…py`); the child's own assignment `strategy_assignment_v1` (question context, prior search refs, literature task, proposed annotation, requested components) | The child's typed form; the references in it, any structure cells it carries, native timing receipts and tool attributions are recorded as received by this episode (`from_child_…py`) |

How the child's admitted form enters this episode's credit is decided by the old services' scientific credit, not in
this folder; what this folder does is record the form's references and cells as received by this episode.

## Decision state and what the model sees

Per-episode state (`task_state.py`): call count, last outcome, feedback, report values and basis, restore state;
unfinished own actions of kind `tool` or `reason` are resumed.

Shown at each decision (`task.py`, `decision_delivery.py`): goal, scope, working state, visible record refs, current
credit (or the annotation-axis credit mode with root score and proposed annotations/comparisons), evidence vector,
investigation progress, credit binding, elapsed-time view, pending work, last outcome, feedback, visual evidence,
deliveries, controller, tools, tool knowledge, job options, available report facts, requested form, current report
update and basis; plus resource and shared-information context, launch-instruction library, child options,
completed action reports, execution expectations for `literature`, resource estimates and the contract-information
profile; literature numerical contracts are frozen with the decision when no profile is used.

This episode's own summary (`internal_summary.py`): `literature_assignment`, `literature_source_custody` (version,
artifact, text, stdout/stderr refs and parent sources of each assigned source), `own_literature_outcomes` (first
`outcome_page_size` acquisition/read outcomes of its own) with their meaning ("Own outcome metadata only... Source
delivery does not establish scientific understanding"); with structure population also
`literature_experimental_work` (`aspect: source_experimental_evidence`, axis A102), its own completed population
sheets (read-only metadata) and its latest failed population attempt. At a root-level reference-evidence entry it
shows `reference_evidence_parent` with source custody and the population operations.

Presentation (`decision_presentation.py`, `presentation_selection.py`): a text TASK prompt rendered by the first
matching renderer (HPC, published scientific, API launch, selected execution, monitor, receiver), with a prompt
state kept per (episode, role) across decision updates and lookups; otherwise the context as JSON.

## Tools

From the services' tool catalog, only:

- access: `state.query`, `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`,
  `source.experimental.records`, `image.view`, `source.archive.members`, `source.archive.extract`,
  `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`, `source.pdf.page`,
  `execution.estimate` (only its xlsx sheets/rows branches);
- acquisition: `public.literature.search`, `public.literature.read`, `public.literature.sequence_identity`,
  `public.ncbi.search` (database limited to `pubmed`), `public.pmc.versions`, `public.pmc.files`, `public.pmc.asset`,
  and the experiment-database tools;
- with structure population: `literature.structure.populate` (structure sheets from source-model geometry and
  local fits; text-witness inputs are materialised by reading the cited source windows).

Arguments are checked against the tool schema; reads outside an assigned page source are refused; locate, sequence
and experimental-record tools are limited to received records. Argument errors return an `invalid` outcome.

A reasoning commit may carry a `source_lead` when the task kind is `verified_source_leads`; its witness window must
be readable, and the lead is validated with the commit (`source_interpretation.py`).

## Credit

Credit kind `scientific`. The credit view is the old services' `scientific_credit(context, receiver_selection)`;
the projector is the old `LiteratureTaskCredit(self, context)`. The credit unit comes from the yield declaration
for the commissioned task. The rule itself is in the old support module (`literature_task_credit`), not in this
folder. Navigation, byte coverage and repeated reading earn nothing by themselves (goal text).

## Continuation

Without `private_yield_binding`: none of its own (the old runner's default). With it: `continuation_task(context)`
names the commissioned task's key; its declaration (`kind`, `cutoff`, `uncertainty_alpha`, `credit_unit`) builds
the old `_private_yield_controller`; a missing declaration raises. Which of the three current estimators each
declared `kind` maps to is decided in the old support module, not visible here.

## What it reports to its parent

| Fact | When |
|---|---|
| `literature_screening_answers` (SCREENING) | the task's `answer_kind` is `screening` |
| `literature_source_lead_dispositions` (LEADS) | the task's `kind` is `verified_source_leads` |
| structure cells (`a102_literature_bindings.SOURCE_NAME`) | structure population: cells from committed and received population sources, limited to requested components |

`validate_report` re-admits the assignment, the form and the received report: screening answers and lead
dispositions must equal the saved work (`literature_task_answer_differs_from_saved`); structure cells must come from
received sheets and requested components.

## Differences from similar episodes

- Against its child `evidence_search_strategy_improvement`: same file layout and nearly the same text. This one has
  role `literature`, is an entry role, takes `literature_assignment_v1` with `source_refs`, commissions
  `literature_strategy`, has the evidence-question goal, and defines `create_binding_tree` (builds this binding and its
  six descendants from one configuration). The child has the search-approach goal, takes `strategy_assignment_v1`
  with `prior_search_refs`, and commissions `literature_search`.
- Against the same episode in other axes: the A103 head prefixes the shared goal with A103-specific guidance (locus,
  genome, neighbour identity) and has a different file split; the A105 and A108 heads carry their own local task
  module in `goal.py` and their own `grading/` and `scoring/` folders. The A102 head has neither an axis-specific
  goal paragraph nor its own grading or scoring folder; its axis-specific content is the structure-population route
  (`literature.structure.populate`, structure cells) and the A102 experimental-work record.
- Carried text that has no role in this episode: the `page` branches (`_validate_page`, page confinement, page
  custody) serve the page role; the HPC, monitor and API-launch renderers in the presentation selection; job-source
  branches in the loop.

## Old support modules this episode imports

Looked up in `runs/placement_plan/placement.tsv` and by file name under `episode_support/` (the modules themselves
were not read). "Files" counts the files in this folder that import it.

| Old module (`root.a102.`...) | Files | Home now |
|---|---|---|
| `a102_literature_bindings` | 4 | no placed home found |
| `communication` | 1 | no structural_homology_evidence copy found (copies for other axes under episode_support/forms/AXIS/) |
| `composition_information` | 2 | no placed home found |
| `delivery_counterpart` | 1 | no placed home found |
| `domain` | 1 | episode_support/records/structural_homology_evidence/domain.py |
| `episode_bindings` | 1 | the deleted old per-axis binding table |
| `episode_return_records` | 1 | no placed home found |
| `episode_source_failure` | 2 | no placed home found |
| `episode_work_report` | 1 | no placed home found |
| `experimental_database_acquisition` | 1 | episode_support/acquisition/structural_homology_evidence/experimental_database_acquisition.py |
| `library.action_contracts` | 1 | no placed home found |
| `library.hpc_prompt` | 2 | no placed home found |
| `library.literature_assay_inputs` | 1 | no structural_homology_evidence copy found (copies for other axes under episode_support/literature/inputs/AXIS/) |
| `library.monitor_prompt` | 1 | no placed home found |
| `library.private_policy_call` | 2 | no placed home found |
| `library.report_fact_assembly` | 1 | no placed home found |
| `literature_contract_error` | 2 | episode_support/literature/forms/literature_contract_error.py (unqualified copy; axis copies for others) |
| `literature_sheet_updates` | 1 | no structural_homology_evidence copy found (copies for other axes under episode_support/literature/storage/AXIS/) |
| `literature_structure_storage` | 1 | no placed home found |
| `literature_task_credit` | 7 | episode_support/literature/grading/literature_task_credit.py (one unqualified copy; which axis it came from not checked) |
| `literature_task_selection` | 1 | no placed home found |
| `method_loop.durable` | 1 | top-level method_loop (the only method_loop) |
| `providers` | 3 | gene_annotation_episode/model_provider.py for ModelCallError; the rendering helpers have no placed home |
| `read_mapping` | 1 | episode_support/readers/sequence_alignment/structural_homology_evidence/read_mapping.py |
| `receiver_prompt` | 1 | no placed home found |
| `runtime` | 6 | the deleted old per-axis runner |
| `runtime_prompt` | 1 | episode_support/instructions/structural_homology_evidence/runtime_prompt.py |
| `structural_homology_evidence_prompt` | 1 | no placed home found |

## File by file

Counts are occurrences in the file text. `self.workflow` also covers `source.workflow`, `self.services.workflow`
and a `workflow` argument; "BindingContext fields" are attribute reads on the old context object (`context`,
`parent`, `child`); "old-runner callbacks defined" are methods the old runner called on the binding or task;
"old providers module" are names taken from the old `root.a102.providers`. The same rows, one per name and file, are
in `runs/carry_over/calls/a102_06.tsv` (423 rows, 738 uses in this episode).

| Old file | Lines | This episode's own intent in it | Old-runner names used (name×uses) |
|---|---|---|---|
| `__init__.py` | 0 | Nothing (package marker). | none |
| `binding_record.py` | 8 | Its configuration record (`literature_episode_binding_v1`): `outcome_page_size`, `structure_population`. | **old-runner callbacks defined**: `as_record` |
| `child_commissioning.py` | 12 | The one child role it may commission: `literature_strategy` (evidence_search_strategy_improvement). | **BindingContext fields**: `role`×2; **old-runner callbacks defined**: `allowed_children`, `child_roles` |
| `configuration.py` | 13 | On-demand contract information is offered to this role (and to a root `annotation` context when reference parent sources are configured). | **BindingContext fields**: `path`, `role`×2; **old-runner callbacks defined**: `contract_information_configuration`, `contract_information_profile` |
| `credit.py` | 17 | Credit kind `scientific`; the credit view is the old services' scientific credit; the projector is the old `LiteratureTaskCredit` over this binding and context. | **BindingContext fields**: `role`×2; **imports from old `root.a102`**: `literature_task_credit`; **old-runner callbacks defined**: `credit_kind`, `credit_projector`, `credit_view`; **self.services**: `scientific_credit`; **old support classes**: `LiteratureTaskCredit`×2 |
| `decision_delivery.py` | 346 | The model call and exchange protocol (old runner). Its own parts: execution expectations captured for role `literature`; completed action reports unless the annotation-axis credit mode applies; literature numerical contracts frozen with the decision when no contract-information profile is used. | **imports from old `root.a102`**: `episode_work_report`×2, `library.hpc_prompt`, `runtime`×2; **old-runner callbacks defined**: `call`, `complete_decision`, `conversation_key`, `exchange_decision`, `exchange_response`, `exchange_schema`, `instructions`, `interpretation_context`, `validate_contract_exchange_history`, `validate_contract_exchange_request`; **old provider interface**: `complete_with_presentation`, `has_session`×3, `prompt_renderer`; **old runtime**: `_action_generation_schema`×2, `apply_state_frame`, `_ASSIGNMENT_TRANSPORT`, `_category_yield_parameters`, `child_option_information`×2, `composition_lookup_schema`×2, `CONTRACT_INFORMATION_OPERATIONS`, `DECISION_CONTEXT_VERSION`×2, `DECISION_EXCHANGE_PROTOCOL`×5, `_digest`, `Draft202012Validator`, `instructional_model_context`×4, `is_contract_information`, `_json`×14, `json`×3, `lookup_attempts`, `Mapping`×4, `model_snapshot`×2, `_object`×3, `_plain`×2, `_recorded_action_generation_schema`, `_recorded_assignment_transport`, `_references_in`, `requested_contract_information`×2, `schema_failure_diagnostic`×2, `sqlite3`, `state_frame`, `ValidationError`×5, `WorkflowError`×14, `yield_table`; **self.workflow**: `available_child_roles`, `binding_context`, `contract_information_profile`, `contract_information_reply`, `controller_binding`, `decision_exchanges`×4, `decision_protocol`×3, `episode_bindings`, `execute`, `execution_expectations`, `freeze_contract_information`, `freeze_literature_numerical_contracts`, `history_preview`, `is_job_source`×3, `job_episodes`×2, `journal`×3, `launch_instructions`×2, `native_estimation_context`, `numerical_contracts`, `pending_work`, `permits_common_action`, `provider`×3, `provider.conversation_key`, `provider.has_session`, `receipts`×4, `resource_context`, `resource_estimator`×5, `run_id`, `services`×2, `shared_information_context`, `specialist`, `store`×2, `store.reference_subset`, `uses_received_record_context`×2, `validate_contract_information`×5, `waiting_support`; **journal/receipt tables**: `runtime_model_calls`×8; **old yield names**: `_category_yield_parameters`×2, `yield_table`×2 |
| `decision_presentation.py` | 43 | Prompt rendering: a text TASK prompt when the context is HPC, published-scientific, monitor, API launch, selected execution or ordinary receiver context, otherwise the context as JSON; keeps a prompt state per (episode, role) across decision updates and lookups. | **imports from old `root.a102`**: `providers`×2; **old-runner callbacks defined**: `present_source_decision`; **old provider interface**: `provider_presentation`, `scientific_prompt_states`×4; **old providers module**: `apply_state_frame`×3, `DECISION_CONTEXT_VERSION`, `deepcopy`, `json`, `text_instructions` |
| `episode.py` | 100 | The binding: path `structural_homology_evidence/published_evidence_assessment`, parent `structural_homology_evidence` (axis head), role `literature`, entry role `literature`; settings `outcome_page_size` (default 8, ≥ 1), `structure_population`, `reference_parent_sources` (needs structure population), contract-information profile (needs structure population), `private_yield_binding`, `yield_bindings` (need the private binding); `reference_evidence` entry for a caller-assigned reference-source investigation; permitted actions `tool`, `reason`, `child`, `redeliver_report`; child receiver and request assembler for `literature_strategy`; `create_binding_tree` builds this binding and its six descendants from one configuration. | **BindingContext fields**: `role`; **absolute imports inside the episode tree**: `published_evidence_assessment.evidence_search_strategy_improvement.episode`, `published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode`, `published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode`, `published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode`, `published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode`, `published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode`; **imports from old `root.a102`**: `literature_task_credit`; **old binding attributes**: `binding_path`, `commissioning_parent`, `decision_prompt_renderer`, `decision_source_type`, `entry_roles`, `roles`; **old-runner callbacks defined**: `child_report_receiver`, `child_request_assembler`, `create_binding_tree`, `permitted_common_actions`, `reference_evidence`; **old yield names**: `validate_yield_bindings`×2 |
| `from_child_evidence_search_strategy_improvement.py` | 45 | Receiving the strategy child's typed form: recorded admission refs on replay, progress-provider receipt, references in the form plus structure cells received, native timing receipts, tool attributions; all recorded as received by this episode. Nothing specific to the child beyond the role name. | **imports from old `root.a102`**: `delivery_counterpart`, `episode_return_records`, `runtime`×2; **old-runner callbacks defined**: `receive_report`; **old runtime**: `_json`, `json`, `_references_in`, `WorkflowError`; **self.workflow**: `binding_context`×4, `episode_bindings`, `is_job_source`×2, `job_episodes`×2, `native_timing_information`, `progress_provider`×4, `receipts`×3, `receive_tool_attributions`, `run_id`×6, `specialist`, `store`×7; **old support classes**: `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_report_attempts`×2 |
| `from_parent.py` | 72 | Assignment form `literature_assignment_v1`: `question_context_refs`, `source_refs`, `literature_task` (task schema; `credit_unit` filled from the yield declaration under the private binding), `proposed_annotation_ref` (required with the private binding), and the requested structure components. Every `_refs` entry must be in scope (`source_refs` as sources). Preparing the assignment fills `credit_unit` and `yield_settings` (kind, cutoff, uncertainty_alpha) from the declaration keyed by the task, refuses a supplied mismatch, and requires the parent's proposed annotation. | **BindingContext fields**: `assignment`; **imports from old `root.a102`**: `a102_literature_bindings`, `literature_task_credit`×2; **old-runner callbacks defined**: `assignment_schema`, `child_assignment_schema`, `prepare_assignment`; **self.services**: `proposed_annotation_for` |
| `goal.py` | 8 | The goal text: investigate which published evidence bears on the assigned scientific question, by searches and reads directly or by assigning a strategy investigation; plus the shared literature paragraph (no prescribed child order, reading quota or complete-document requirement; keep the source's subject, conditions, representation, version and byte anchors; separate source claims from applicability to the target; negative findings count; navigation and repeated reading earn no scientific credit). | **BindingContext fields**: `role`; **old-runner callbacks defined**: `instructions` |
| `internal_summary.py` | 83 | Per-decision summary: the admitted assignment, custody of the assigned sources (version, artifact, text, stdout/stderr, parent sources), its own literature outcome metadata (first `outcome_page_size` acquisition/read outcomes) and their meaning; with structure population also the experimental-work record, its own completed population sheets (read-only metadata) and the latest failed population attempt. A root-level reference-evidence context when reference parent sources are configured. | **BindingContext fields**: `assignment`, `episode_id`×4, `path`, `received_record_refs`×2, `role`×2, `run_id`×5, `scope`×4; **imports from old `root.a102`**: `literature_task_selection`; **old-runner callbacks defined**: `decision_context`, `initial_decision_context`; **self.services**: `own_outcomes`, `workflow`×2; **self.workflow**: `run_id`×2, `store`×2; **journal/receipt tables**: `runtime_actions`×2 |
| `presentation_selection.py` | 30 | Which text renderer applies, in predicate order: HPC, published scientific, API launch, selected execution, monitor, receiver. | **imports from old `root.a102`**: `library.hpc_prompt`, `library.monitor_prompt`, `providers`×2, `receiver_prompt`, `structural_homology_evidence_prompt`; **old providers module**: `is_api_launch_context`×2, `is_published_scientific_context`×2, `_ordinary_runtime_receiver_context`, `render_api_launch_prompt`, `render_structural_homology_evidence_prompt` |
| `received_evidence.py` | 73 | Received report facts and cells from children (structure population routes), filling requested empty arrays; references received in a form; received-cell tokens; checking a returned form: screening answers and lead dispositions must equal the saved work, structure cells must be received and requested. | **BindingContext fields**: `assignment`×2, `episode_id`, `received_record_refs`, `request`, `role`×2, `run_id`; **imports from old `root.a102`**: `literature_sheet_updates`, `literature_task_credit`, `method_loop.durable`; **old-runner callbacks defined**: `received_evidence_tokens`, `received_form_references`, `received_report_facts`, `received_report_sources`, `validate_received_report`; **self.services**: `record_selection`, `workflow`×2; **self.workflow**: `store`×2 |
| `report_delivery.py` | 25 | Closure: typed form built once from saved facts and last interpretation (same text as the other A102 copies). | **imports from old `root.a102`**: `library.private_policy_call`, `library.report_fact_assembly`, `runtime`×2; **old-runner callbacks defined**: `finish`; **old runtime**: `form_with_facts`, `_json`×2, `json`, `Record`×2; **self.workflow**: `binding_context`, `episode_bindings`, `facts`, `journal`×2, `pending_handles`, `release`×2, `source_credit_view`; **journal/receipt tables**: `runtime_forms`×2 |
| `source_contracts.py` | 38 | Its constants: role list of the seven literature roles, assignment fragments (window, table, page), the access tools (state query, source read/locate/sequence/experimental records, image view, archive, xlsx, pdf, `execution.estimate`), the acquisition tools (public literature search/read/sequence identity, NCBI search, PMC versions/files/asset, experiment-database tools), the read tools, `literature.structure.populate`. | **imports from old `root.a102`**: `a102_literature_bindings`, `communication`, `composition_information`, `domain`, `episode_bindings`, `experimental_database_acquisition` |
| `source_interpretation.py` | 43 | A reasoning commit may carry a `source_lead` when the task kind is `verified_source_leads`; the lead's witness window is read-checked and validated with the commit. | **BindingContext fields**: `assignment`, `episode_id`, `run_id`, `scope`; **imports from old `root.a102`**: `literature_contract_error`, `literature_task_credit`×3; **old-runner callbacks defined**: `execute_reasoning`, `reasoning_action_schema`, `reasoning_has_task_content`; **self.services**: `workflow`; **self.workflow**: `store`; **old support classes**: `ExperimentalContractError`×2 |
| `source_operations.py` | 94 | Its tools: the access and acquisition tools from the services catalog, NCBI search limited to `pubmed`, `execution.estimate` only for xlsx sheets/rows, and `literature.structure.populate` with structure population; argument checks; page confinement (reading outside an assigned page source is refused); text-witness inputs materialised for population. | **BindingContext fields**: `assignment`, `received_record_refs`, `role`×2, `scope`×6; **imports from old `root.a102`**: `composition_information`, `library.literature_assay_inputs`, `literature_contract_error`; **old-runner callbacks defined**: `catalog`, `execute`; **self.services**: `execute_tool`, `tool_catalog`; **old support classes**: `ExperimentalContractError`×2 |
| `source_references.py` | 35 | Scope checks for references, choice of artifact by representation, ancestry check that a source lies within an assigned root source, reference resolution. | **BindingContext fields**: `role`; **old-runner callbacks defined**: `resolve`; **self.services**: `read_record`, `reference_in_scope` |
| `structural_sheet_operations.py` | 17 | Access to the structure-sheet repository and the population route (when structure population is on). | **imports from old `root.a102`**: `a102_literature_bindings`, `literature_structure_storage`; **old-runner callbacks defined**: `literature_structure_repository`; **self.services**: `workflow`×2; **self.workflow**: `run_id`, `store`; **old support classes**: `LiteratureStructureRepository`×2 |
| `task.py` | 269 | The decision loop (old runner) with child delivery resolution, ready owned children, reasoning commits with lead content, job-child failure feedback; report grain name `literature`. | **imports from old `root.a102`**: `episode_source_failure`, `library.action_contracts`, `library.private_policy_call`, `providers`, `read_mapping`, `runtime`×2; **old binding attributes**: `instruction_composer`; **old-runner callbacks defined**: `apply_response`, `execute`, `next`; **old runtime**: `AcquisitionError`×2, `ActionFailure`, `ContractError`, `ContractInformationError`, `_decode_recorded_action_response`, `Draft202012Validator`×3, `EventTargetError`×2, `FACT_MEANINGS`, `FACT_SOURCES`, `inspect`, `_json`×5, `json`×10, `Mapping`×6, `nullcontext`×5, `observes_action_outcome`, `_plain`×2, `_references_in`, `ReportBoundaryError`, `ReportRedelivery`×2, `schema_failure_diagnostic`, `SourceEnd`×2, `sqlite3`×2, `subprocess`×2, `validate_form`, `ValidationError`×3, `_wait_target_feedback`×2, `WorkflowError`×2; **self.workflow**: `action_schema`, `annotation_context`, `automatic_score_updates`, `binding_context`×3, `catalog`, `completed_unit`×3, `completions`×3, `controller_binding`, `controller_value`×2, `decision_exchanges`×3, `delivery_resolution_inputs`, `delivery_status`, `execute`, `execution_binding`×7, `extra_report_sources`, `inprocess_replay`×4, `is_scientific_source`, `job_episode_options`, `journal`×10, `knowledge`, `last_observed_credit`, `local_outcome_preview`, `next_return`, `pending_work`×2, `perform_selected_wait`, `permits_common_action`, `reasoning_action_schema`, `receipt_projection`, `receive_native_outcome`, `receive_outcome`, `resolve_pending_deliveries`, `resolver`, `retain_shared_grading_results`, `run_id`×4, `selected`×3, `source_credit_binding`, `source_credit_view`×2, `specialist`×3, `store`×12, `store.reference_subset`, `tools`, `tools.model_contract_catalog`, `validate_report`, `working_state`; **journal/receipt tables**: `runtime_actions`×10, `runtime_episodes`, `runtime_model_calls`×2 |
| `task_instructions.py` | 26 | Instruction composer: default or job instructions plus this goal, the reasoning-commit requirement, tool knowledge, launch instructions, the pending-child redelivery paragraph, wait and native-event paragraphs when wait is allowed, exchange-history wording. | **imports from old `root.a102`**: `runtime_prompt`×2; **old-runner callbacks defined**: `compose_instructions`; **old runtime_prompt**: `DECISION_EXCHANGE_PROTOCOL`, `INSTRUCTIONS`×4, `REASONING_COMMIT_REQUIREMENT`; **self.workflow**: `binding_context`, `decision_protocol`, `is_job_source`, `job_episodes`, `knowledge`, `launch_instructions`, `native_event_information`, `permits_common_action`×3, `specialist` |
| `task_state.py` | 108 | Per-episode decision state and restore/checkpoint; unfinished own actions of kind `tool` or `reason`. | **imports from old `root.a102`**: `episode_source_failure`, `runtime`×2; **old-runner callbacks defined**: `bind_execution_context`, `checkpoint`, `record_effect`, `record_execution_failure`, `restore`, `restore_checkpoint`; **old runtime**: `ActionLeaf`, `EFFECT_VERSION`, `Episode`, `interpretation_schema`, `_json`×2, `json`×4, `_object`, `_plain`, `Record`; **self.workflow**: `archive`, `completions`×4, `context`, `controller_value`, `execution_binding`×4, `grains`, `inprocess_replay`×7, `journal`×5, `progress_provider`×2, `recover_commissions`, `run_id`, `source_credit_view`, `store`×2; **journal/receipt tables**: `runtime_actions`×5 |
| `task_waiting.py` | 9 | Records the suspension condition and passes it to the external executor. | **old-runner callbacks defined**: `suspension_changed`; **self.workflow**: `execution_backend`, `execution_handle`×2 |
| `to_child_evidence_search_strategy_improvement.py` | 29 | Building the strategy child's request: child goal refining its own, message with scope, initial report, report-contract declaration, job and episode assignments, structural-homology context and knowledge inheritance. Nothing specific to the child beyond the call. | **imports from old `root.a102`**: `runtime`×2; **old-runner callbacks defined**: `assemble_request`; **old runtime**: `ContractInformationError`, `Episode`×2, `EpisodeGoal`×2, `EpisodeRequest`, `_plain`×3, `Record`, `validate_saved_fact_form`; **self.workflow**: `context`×2, `grains`×2, `inprocess_completion_order`×2, `launch_instructions`, `receipts`×2 |
| `to_parent.py` | 41 | Report facts: screening answers when the task's answer kind is `screening`; lead dispositions when the task kind is `verified_source_leads`; with structure population, structure cells from committed and received sources; a report must pass assignment, form and received-report checks. | **BindingContext fields**: `assignment`×4, `received_record_refs`, `role`×2, `scope`; **imports from old `root.a102`**: `a102_literature_bindings`, `literature_task_credit`×2; **old-runner callbacks defined**: `current_report_facts`, `facts`, `fact_sources`, `validate_report`; **self.services**: `read_record`, `workflow`×2; **self.workflow**: `store`×2 |
| `waiting.py` | 8 | It does not support waiting (`supports_wait` is false). | **old-runner callbacks defined**: `supports_wait` |
| `yield_estimator.py` | 22 | Continuation: without the private binding none of its own; with it, the declaration keyed by the commissioned literature task (`continuation_task`) builds the old literature yield controller; a missing declaration raises. | **BindingContext fields**: `role`×2; **imports from old `root.a102`**: `literature_task_credit`×2; **old-runner callbacks defined**: `continuation_task`, `yield_controller`; **old yield names**: `_private_yield_controller`×2 |
