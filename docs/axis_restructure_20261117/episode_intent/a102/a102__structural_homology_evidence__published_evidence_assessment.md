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

## Carried over

One row per old function, class or method of this episode folder at `97308b94c` (`runs/carry_over/functions/a102__structural_homology_evidence__published_evidence_assessment.tsv`). Kind is the old kind; the next column says whether the row is old-runner machinery (not carried, with its reason) or an episode function (with its new place). Functions of this folder that are not in the library already stay in the episode file that uses them (library candidates): `validate_source_lead`, `examined_spans`, `checked_strategy`, `source_custody`, `artifact_of` and the credit functions. Not placed (their route is not built) are listed in `docs/axis_restructure_20261117/carry_over_blocked/a102__structural_homology_evidence__published_evidence_assessment.md`.

| old file | kind | name | classification | new place or machinery reason |
|---|---|---|---|---|
| binding_record.py | class | SourceBindingRecord | machinery | binding record: the binding's own as_record() (README 3e); the settings are journaled by the system |
| binding_record.py | method | SourceBindingRecord.as_record | machinery | binding record: the binding's own as_record() (README 3e); the settings are journaled by the system |
| child_commissioning.py | class | SourceChildCommissioning | episode function | task.py CHILD_SLOTS = {literature_strategy: .../evidence_search_strategy_improvement} |
| child_commissioning.py | method | SourceChildCommissioning.allowed_children | episode function | task.py CHILD_SLOTS (the one child role literature_strategy, old allowed_children/child_roles) |
| child_commissioning.py | method | SourceChildCommissioning.child_roles | episode function | task.py CHILD_SLOTS (the one child role literature_strategy, old allowed_children/child_roles) |
| configuration.py | class | SourceConfiguration | machinery | contract-information profile of the old decision exchange (README 3a: no exchange; the profile applied only with structure_population, which is not built) |
| configuration.py | method | SourceConfiguration.contract_information_configuration | machinery | contract-information profile of the old decision exchange (README 3a: no exchange; the profile applied only with structure_population, which is not built) |
| configuration.py | method | SourceConfiguration.contract_information_profile | machinery | contract-information profile of the old decision exchange (README 3a: no exchange; the profile applied only with structure_population, which is not built) |
| credit.py | class | SourceCredit | episode function | credit.py (credit) and messages/internal_summary.py (credit_binding) |
| credit.py | method | SourceCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | SourceCredit.credit_view | episode function | credit.py credit(summary, records) (the number); the other fields of the old view are computed in messages/internal_summary.py |
| credit.py | method | SourceCredit.credit_projector | episode function | credit.py: private re-expression of LiteratureTaskCredit (credit, answers, lead_dispositions, screening_answers, assessment_answers, current_assessments, credit_binding) |
| decision_delivery.py | class | SourceDecisionDelivery | machinery | old decision call path (README 3a) |
| decision_delivery.py | method | SourceDecisionDelivery.call | episode function | task.py decide(summary, feedback, ctx) returns the ModelRequest (the model call itself and its journaling are the system's); the context fields it showed (goal, scope, assignment, custody, own outcomes, child reports, credit_binding, report update, tools, time, action_yields, tool_knowledge) |
| decision_delivery.py | method | SourceDecisionDelivery.instructions | episode function | task.py instructions(*, knowledge) |
| decision_delivery.py | method | SourceDecisionDelivery.conversation_key | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.interpretation_context | machinery | decision-exchange interpretation context (README 3a): no exchange |
| decision_delivery.py | method | SourceDecisionDelivery.exchange_schema | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.exchange_response | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.validate_contract_exchange_request | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.validate_contract_exchange_history | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.exchange_decision | machinery | decision-exchange loop, saved-exchange and contract-information validation, conversation key (README 3a: deleted) |
| decision_delivery.py | method | SourceDecisionDelivery.complete_decision | episode function | task.py decide(summary, feedback, ctx) returns the ModelRequest (the model call itself and its journaling are the system's); the context fields it showed (goal, scope, assignment, custody, own outcomes, child reports, credit_binding, report update, tools, time, action_yields, tool_knowledge) |
| decision_presentation.py | function | present_source_decision | machinery | state-frame prompt renderer selection of the old provider (README 3a: every ModelRequest carries the full context; the episode puts its context into ModelRequest.context) |
| episode.py | class | LiteratureEpisode | episode function | episode.py PublishedEvidenceAssessment(EpisodeBinding) |
| episode.py | method | LiteratureEpisode.__init__ | episode function | settings of the run (ctx.settings: structure_population, tool_registry, knowledge_library_directory); outcome_page_size is the constant OUTCOME_PAGE_SIZE in messages/internal_summary.py; private_yield_binding/yield_bindings are replaced by the commissioned task's credit_unit and the settings cost/parameters (yield_estimator.py); reference_parent_sources and contract_information_profile are root-only and not built |
| episode.py | method | LiteratureEpisode.reference_evidence | episode function | not placed: root-only constructor for a caller-assigned reference-source investigation (requires structure_population, not built); reported in unplaced_old_functions |
| episode.py | method | LiteratureEpisode._role | machinery | one binding per role: the role check is gone (README 3a BindingContext.role) |
| episode.py | method | LiteratureEpisode.permitted_common_actions | episode function | task.py offered/selection_schema: tool, reason, child; redeliver_report is deleted (README 3b R2) |
| episode.py | method | LiteratureEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child (slot literature_strategy) |
| episode.py | method | LiteratureEpisode.child_request_assembler | episode function | messages/msg_to_child.py msg_to_child (slot literature_strategy) |
| episode.py | function | create_binding_tree | machinery | home factory / table of bindings: builds the seven private bindings of the old tree from one configuration (README 3b C1: deleted; the registry is built by whoever links the run; no list of bindings is written) |
| from_child_evidence_search_strategy_improvement.py | function | receive_report | episode function | messages/read_from_child.py read_from_child; recorded admission, progress receipts, timing receipts and receipt bookkeeping are the system's (README 3b R1, R3, R5) |
| from_parent.py | class | SourceFromParent | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent, task_key) |
| from_parent.py | method | SourceFromParent.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (literature_assignment_v1 with source_refs; the child's own form states what it takes) |
| from_parent.py | method | SourceFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (literature_assignment_v1 with source_refs) |
| from_parent.py | method | SourceFromParent._validate_page | episode function | not placed: the page branch (source artifact and prior-delivery checks of a page assignment) serves the page role; this assignment has no page; reported in unplaced_old_functions. The held-record check of the model's chosen strategy is task.py checked_strategy (a rejection in action) |
| from_parent.py | method | SourceFromParent._validate_assignment | machinery | commission check: the scope/namespace tests of the assignment are the system's custody over record_refs fields (rule 1); the schema check is the form's admission; the finite task and kind checks are in messages/read_from_parent.py |
| from_parent.py | method | SourceFromParent.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (task checks, credit_unit); the private yield declaration lookup is replaced by the credit_unit in the task and the settings (yield_estimator.py); the proposed-annotation equality check of a commission is not carried (rule 1) |
| goal.py | class | SourceGoal | episode function | goal.py GOAL, UNIT, RESULT, BINDING_PATH |
| goal.py | method | SourceGoal.instructions | episode function | goal.py GOAL (the instruction text); the role check is gone |
| internal_summary.py | class | SourceInternalSummary | episode function | messages/internal_summary.py |
| internal_summary.py | method | SourceInternalSummary.initial_decision_context | episode function | not placed: root-only reference_evidence_parent context (requires structure_population and reference_parent_sources; not built); reported in unplaced_old_functions |
| internal_summary.py | method | SourceInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary (literature_assignment, literature_source_custody, own_literature_outcomes, literature_history_meaning) with source_custody, held_sources |
| internal_summary.py | method | SourceInternalSummary._owned_population_task_sources | episode function | not placed: structure population context (owned population sheets by raw SQL on runtime tables and sqlite_master; the route is not built; decide raises when structure_population is set); reported in unplaced_old_functions |
| internal_summary.py | method | SourceInternalSummary._population_task_context | episode function | not placed: structure population context (owned population sheets by raw SQL on runtime tables and sqlite_master; the route is not built; decide raises when structure_population is set); reported in unplaced_old_functions |
| presentation_selection.py | function | source_presentation_selection | machinery | predicate order of the old per-context prompt renderers (README 3a: the episode renders its own context in decide) |
| received_evidence.py | class | SourceReceivedEvidence | machinery | receiving a child report (README 3b R1, R3) |
| received_evidence.py | method | episode function | unplaced: structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens); the structure population route is not built (README 5 item 4); the use raises NotImplementedError('literature_structure_population_not_built') ; listed in carry_over_blocked unplaced_old_functions | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | episode function | unplaced: structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens); the structure population route is not built (README 5 item 4); the use raises NotImplementedError('literature_structure_population_not_built') ; listed in carry_over_blocked unplaced_old_functions | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | episode function | unplaced: structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens); the structure population route is not built (README 5 item 4); the use raises NotImplementedError('literature_structure_population_not_built') ; listed in carry_over_blocked unplaced_old_functions | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | episode function | unplaced: structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens); the structure population route is not built (README 5 item 4); the use raises NotImplementedError('literature_structure_population_not_built') ; listed in carry_over_blocked unplaced_old_functions | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | episode function | unplaced: structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens); the structure population route is not built (README 5 item 4); the use raises NotImplementedError('literature_structure_population_not_built') ; listed in carry_over_blocked unplaced_old_functions | structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens): receipts bookkeeping and the population route, not built (README 3b R3; item 4 of README 5) |
| received_evidence.py | method | episode function | unplaced: structure-population cells received from children (receive_cells, current_sheet_refs, evidence tokens); the structure population route is not built (README 5 item 4); the use raises NotImplementedError('literature_structure_population_not_built') ; listed in carry_over_blocked unplaced_old_functions | check of a child's return: the system admits the result against the child's own form (README 3b R1, D2); the child computes both answer and facts from one summary |
| report_delivery.py | class | SourceReportDelivery | episode function | messages/final_to_parent.py final_to_parent (facts and report); saving the form, release and pending_handles are deleted (README 3b D1, D3) |
| report_delivery.py | method | SourceReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (facts and report); saving the form, release and pending_handles are deleted (README 3b D1, D3) |
| source_contracts.py | function | _population_catalog | episode function | task.py (VERSION/ROLES dropped; _WINDOW/_PAGE as PAGE and WINDOW schemas; access and acquisition tool lists as ACCESS_NAMES, ACQUISITION_NAMES, HELD_SOURCE_TOOLS); the population catalog is the not-built literature_structure_populate tool |
| source_interpretation.py | class | SourceSourceInterpretation | episode function | task.py reason (tool), reason_schema, empty_commit |
| source_interpretation.py | method | SourceSourceInterpretation.reasoning_action_schema | episode function | task.py reason_schema |
| source_interpretation.py | method | SourceSourceInterpretation.reasoning_has_task_content | episode function | task.py action (a reason answer without a source_lead and with an empty commit is rejected, empty_commit) |
| source_interpretation.py | method | SourceSourceInterpretation.execute_reasoning | episode function | task.py reason (tool): witness read check, commit_reasoning and validate_source_lead in one transaction; invalid outcome returned |
| source_operations.py | class | SourceSourceOperations | episode function | task.py TOOLS (access and acquisition tools) and run_tool |
| source_operations.py | method | SourceSourceOperations.catalog | episode function | task.py catalog, offered, DESCRIPTIONS, INPUT_SCHEMAS (ncbi restricted to pubmed; execution.estimate only its xlsx branches) |
| source_operations.py | method | SourceSourceOperations.execute | episode function | task.py run_tool (library ToolRegistry.execute_async with ctx.store); literature.structure.populate raises (not built) |
| source_operations.py | method | SourceSourceOperations._tool_arguments | episode function | task.py run_tool schema check (no page, so no source boundary); the catalog-membership check is the offered schema |
| source_operations.py | method | SourceSourceOperations._materialize_text_arguments | episode function | not placed: text-witness materialization of literature.structure.populate arguments (needs LiteratureStructureRepository, not in the library); reported in unplaced_old_functions |
| source_references.py | class | SourceSourceReferences | episode function | README 3b D2: custody (records.holds) and task.py checked_strategy |
| source_references.py | method | SourceSourceReferences._require | machinery | reference_in_scope / resolver over the old services: custody (records.holds, README 3b D2) replaces it |
| source_references.py | method | SourceSourceReferences._artifact | episode function | task.py artifact_of |
| source_references.py | method | SourceSourceReferences._within_source | episode function | not placed: only bounded reads to an assigned page source and this assignment has no page (the function is unreachable here); reported in unplaced_old_functions |
| source_references.py | method | SourceSourceReferences.resolve | machinery | reference_in_scope / resolver over the old services: custody (records.holds, README 3b D2) replaces it |
| structural_sheet_operations.py | class | SourceStructuralSheetOperations | episode function | not placed: structure population repository (LiteratureStructureRepository, population_route) is not in the library; the tool literature_structure_populate raises NotImplementedError; reported in unplaced_old_functions |
| structural_sheet_operations.py | method | SourceStructuralSheetOperations.literature_structure_repository | episode function | not placed: structure population repository (LiteratureStructureRepository, population_route) is not in the library; the tool literature_structure_populate raises NotImplementedError; reported in unplaced_old_functions |
| structural_sheet_operations.py | method | SourceStructuralSheetOperations._population_routes | episode function | not placed: structure population repository (LiteratureStructureRepository, population_route) is not in the library; the tool literature_structure_populate raises NotImplementedError; reported in unplaced_old_functions |
| task.py | class | SourceTask | episode function | task.py (decide, action, tools) |
| task.py | method | SourceTask.next | episode function | task.py decide (the loop, replay, model call, exchange and journaling are the system's) |
| task.py | method | SourceTask.apply_response | episode function | task.py action (decode, schema check, empty-commit rejection, strategy and report-reference checks; Rejected(feedback)); the report update admission is the report tool; the wait/redelivery/job branches are not carried |
| task.py | method | SourceTask.execute | episode function | task.py TOOLS (tool calls), CHILD_SLOTS (child commission), reason, report; wait, redeliver_report and the credit-after-outcome bookkeeping are deleted |
| task_instructions.py | function | compose_instructions | episode function | task.py instructions(*, knowledge); the pending-delivery, wait, native-event and exchange paragraphs are not carried |
| task_state.py | class | SourceTaskState | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.__init__ | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.bind_execution_context | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.record_execution_failure | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.restore_checkpoint | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.restore | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.record_effect | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_state.py | method | SourceTaskState.checkpoint | machinery | source state, restore/checkpoint, record_execution_failure (README 3a/3e: tool returns failure_outcome; the system restores state) |
| task_waiting.py | class | SourceTaskWaiting | machinery | suspension machinery (README 3b: wait is deleted) |
| task_waiting.py | method | SourceTaskWaiting.suspension_changed | machinery | suspension machinery (README 3b: wait is deleted) |
| to_child_evidence_search_strategy_improvement.py | function | assemble_request | episode function | messages/msg_to_child.py msg_to_child (objective, strategy, assignment, selection); child goal/EpisodeRequest/knowledge inheritance are the system's (README 3b C3, C4) |
| to_parent.py | class | SourceToParent | episode function | messages/final_to_parent.py (RETURN_FORM, final_to_parent) |
| to_parent.py | method | SourceToParent.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM selectable fields SCREENING, LEADS (and STRUCTURE, not built) |
| to_parent.py | method | SourceToParent.facts | episode function | messages/final_to_parent.py final_to_parent (screening and leads from the summary; structure raises) |
| to_parent.py | method | SourceToParent.current_report_facts | episode function | messages/final_to_parent.py final_to_parent (returned no extra facts) |
| to_parent.py | method | SourceToParent._rate_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM selectable fields SCREENING, LEADS (and STRUCTURE, not built) |
| to_parent.py | method | SourceToParent._rate_facts | episode function | not placed: structure rate facts of the population route (LiteratureStructureRepository.fact_cells; not built); STRUCTURE selection raises; reported in unplaced_old_functions |
| to_parent.py | method | SourceToParent.validate_report | episode function | messages/final_to_parent.py validate_report (held references; then raises NotImplementedError validate_form_not_built:A102 where the old body called validate_form) |
| waiting.py | class | SourceWaiting | machinery | supports_wait = False: wait is deleted (README 3b) |
| waiting.py | method | SourceWaiting.supports_wait | machinery | supports_wait = False: wait is deleted (README 3b) |
| yield_estimator.py | class | SourceYield | episode function | yield_estimator.py |
| yield_estimator.py | method | SourceYield.continuation_task | episode function | messages/read_from_parent.py task_key (parent_input["task_key"]) |
| yield_estimator.py | method | SourceYield.yield_controller | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion with target credit_unit for a source answer; README 7b) |
