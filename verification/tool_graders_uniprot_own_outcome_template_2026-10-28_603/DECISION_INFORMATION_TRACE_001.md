# UniProt results: own acquisition outcome to next own decision — proposal 001

2026-10-28. One message boundary only. This is a source-inspected design for user
feedback, not application code, a newly approved template, a goal file, a scope
amendment, or evidence that the integrated path works. The original supplied goal
attachment is authoritative. No application imports, application tests, native
scientific execution, model calls, network requests, HPC operations, or host
database reads were performed for this proposal.

The input is a results episode's **own exact completed or partial
`api.uniprot.collect` outcome**. The receiver is that same episode, still carrying
its original assignment, scope, constraints and typed report contract. The parent
and ancestor receiving templates are outside this proposal.

## Contracts and owners

* P/B retain their existing parser/publication ownership under
  `../tool_graders_uniprot_alias_boundary_2026-10-28_597/CODING_HANDOFF_003.md`
  and `FROZEN_INTERNAL_CONTRACTS_003.json`. The entire
  `outcome.result.uniprot_publication` remains internal and unchanged.
* R's additive `../tool_graders_uniprot_requested_returns_2026-10-28_601/CONTRACT_002.md`
  and `PROPOSED_SELECTED_RETURN_SCHEMA_002.json` define the proposed
  `uniprot_selected_returns` facts and original `x-uniprot-selection`. R is still
  a proposal, not a currently installed return binding. This template consumes
  its selection/projector; it does not create a second selection language.
* The owning `DecisionSource` supplies `Workflow.binding_context(source)`.
  Selection comes from the original
  `context.request.report_contract.measurements.schema`, never a global latest
  result, current Store inventory, the API cursor/size selector, or model prose.
* The proposed ports are
  `UniProtReturns.own_outcome_view(context, outcome) -> dict` and
  `Workflow.local_outcome_preview(outcome, *, decision_index=None, source=None)`.
  The future caller passes its actual source. These functions select facts;
  they do not select work, acquire a page, write a receipt, or add an observation.

## Actual complete path inspected

Paths below are relative to `gene_annotation_episode/`. Function names name
actual source consumers. Line positions are descriptive pointers, not a code pin.

| Stage | Exact functions / data | Finding and required connection |
| --- | --- | --- |
| Immutable assignment and selected action | `runtime.DecisionSource.execute`; `Workflow.execute`; `Workflow.binding_context`; `execution_episodes.ExecutionEpisodes._target`, `catalog`, `execute`; `api_service_execution.APIServiceExecution._context`, `_manifest`, `_selected`, `catalog`, `execute` | The selected tool and arguments belong to one original results assignment and numerical decision index. The API target validates the handoff and original selector. R must use that assignment and exact selected action. |
| One acquisition | `APIServiceExecution._execute_locked`; `api_uniprot.UniProtService.prepare`, `invoke`, `decode`, `publish`; `parse_uniprot_snapshot` | Empty results selector republishes the retained original response. Explicit immutable cursor/size selects one page of the original query. `collect` takes empty action arguments. Decode is an immediate response, not a remotely running UniProt job. |
| Native preservation and bindings | `uniprot_native.parse_uniprot_native`; `api_services.publish_existing_acquisition`; `tools.ToolRegistry._import_uniprot`; `uniprot_publication.bind_uniprot_publication` | Native row positions survive malformed siblings. Parser-eligible count, actual bound count and outer `completed`/`partial` status differ. Full valid text and sequence remain in native publication/artifacts. `projection_errors` can mark outer partial even when P's parser state is complete. |
| Durable own outcome | `APIServiceExecution._index_result`, `_own_outcomes`, `read_result`; `DecisionSource.execute`, `restore` | The acquisition receipt, snapshot and original action qualify the saved result. Runtime stores the full result before receipt/credit projection, then stores `last_outcome` and `last_outcome_index`. Replay uses the original result. `read_result` presently copies `publication_result` only for Rfam; the UniProt copy is a specific missing R port. |
| Exact attempt authentication | `APIServiceExecution.read_result` and proposed `UniProtReturns.read_own` | The current result index can hold several actions for one source/ref. An episode filter alone does not choose the exact current acquisition. Contract002's proposed optional `operation_key` filter and full saved-outcome comparison must match `outcome.result.acquisition_receipt.operation_key`. Do not accept the first sorted index entry as a substitute. No new ledger is needed. |
| Own state before preview | `Workflow.working_state` (`runtime.py:2576`); `is_job_source`, `is_scientific_source` | This is the specialist `results` role, not historical `job_results` or a scientific role. Its working state is `{'assignment': original_episode_assignment}`. It contains no `Store.reasoning_view` native record list. Keep that distinction; do not add the publication there. |
| **Actual preview caller** | `DecisionSource.next` (`runtime.py:1447`) -> `Workflow.local_outcome_preview` (`runtime.py:2873`) | `next`, not `call`, invokes the preview before reference collection. Today only `published_batch.representation == native_publications_v1` is compacted. UniProt lacks that marker; the complete outcome is returned wholesale. Add the context-aware UniProt branch before this generic fallback; do not fake the native batch marker. |
| Visible-reference collection | `runtime._references_in`; `DecisionSource.next`; `Workflow.receive_outcome`; `DecisionSource.call` | `next` scans working state, presented outcome, visual input and admitted forms. `_ref`, `_refs`, `dependencies`, and typed forms can expose semantic handles; native ordinary `id` text alone is not a reference declaration. Compact first. The new view contains no source/reference/sequence handles or grants. Own acquisition receipt/credit remains based on the original full outcome, not the display. Existing assignment handoff operands and other explicitly received forms retain their original authority. |
| Additional decision context | `ExecutionEpisodes.decision_context`, `facts`; `APIServiceExecution.facts`, `decision_context`; `execution_progress.describe_execution_target`, `ExecutionTargetReader.describe_target` | Results context also contains `execution_assignment`, `execution_target`, `execution_target_description`, and `execution_progress.execution_result_refs`. These are not scientific native values and must not be dumped into text. The API `decision_context` path with latest event facts is called for `launch_api`, not this results role. It cannot repair the own-outcome leak. |
| Saved dispatch and reconstruction | `DecisionSource.call`, `instructions`, `exchange_decision`, `interpretation_context`; `decision_context.instructional_model_context`, `model_snapshot`, `state_frame`, `apply_state_frame` | `call` freezes/dispatches the assembled context. Existing saved calls retain their original contracts and observations. `model_snapshot` supplies the existing own category table and removes raw controller scores / private wait-training histories. It does not filter UniProt native data. Selection must be complete before snapshot/reference indexing, including restored source state. |
| Actual provider presentation | `providers._SessionConnection._presentation`, `complete`; `ModelConnection.complete` | UniProt results currently has no `has_text_task` match and falls back to `json.dumps(presented)`. `complete` records actual input text and sends it. A compact dictionary alone would still violate TASK/STEERING presentation. A narrowly matched UniProt results renderer must rebuild the full TASK for bootstrap, update, direct context and lookup continuation, using the existing frame reconstruction. No changes are implemented here. |
| Generic rendering consumers | `scientific_process_prompt.text_instructions`, `_received_records`, `_outcome`, `_information`, `_steering`, `render_episode_steering`, `_lookup`, `_schema_rows` | `_outcome` retains the full `result`; `_information` is not a UniProt filter. `_received_records` follows selected references only through supplied working-state records, which are absent here, but could re-expose data if a new implementation puts native records there. Do not call generic `_values` on `uniprot_publication`, `execution_progress`, raw forms, or `x-uniprot-selection` witnesses. Reuse mechanical table/band rendering after explicit selection only. |
| Own yield and continuation | `decision_history.category_for`, `yield_table`, `_expectation`; `Workflow.source_credit_view`; `APIServiceExecution.credit_view`, `_completion`, `completion_for_action`; `ExecutionEpisodes.practical_estimator`, `verify_completion`; `practical_yield.PracticalYieldEstimator.__call__` | One completed/partial own acquisition is one observation. Existing operational credit and actual category history remain distinct from scientific support. `api.uniprot.collect` category is `tool/api.uniprot.collect`. Counts are not invented confidence scores. Verified practical completion gives exact zero future gain through the existing controller. |
| Closure | `DecisionSource.finish`; `Workflow.facts`; existing typed form machinery | Recorded facts populate the original requested form at closure. There is no return tool, stop action, final model composer or additional zero-gain turn introduced by this template. |

`ExecutionEpisodes.replaces_default_instructions = True` (`execution_episodes.py:90`).
The current recurring instructions are the complete results-role instructions,
applicable knowledge/launch instructions, optional native-event instructions and
the configured decision protocol. They are **not** runtime's generic scientific
annotation `INSTRUCTIONS`. `TASK_TEMPLATE_001.md` preserves the actual body and
shows the full additional assignment/selected-information sections required to
render it as a concrete TASK. It does not shorten the task to a role heading.

## The receiver's decision and necessary information

| Decision distinction | Facts needed beforehand | Already available / missing |
| --- | --- | --- |
| Is further acquisition useful for the same immutable assignment? | Actual last acquisition status; retained native response; parser status; native/eligible/bound counts; exact selected field availability and relevant failures; own completed-category yield/expectation/uncertainty | Status, counts, native retention, parser/publication issues and own table exist. Selected field projection and text route are proposed R/template work. |
| Is a partial result a malformed source or only an unavailable legacy representation? | Parser state separately from outer status and `result.count`; original error code and field; availability of the selected native text/window | P/B already preserve these distinctions. Do not silently relabel long valid native text invalid or claim selected valid fields are missing. |
| Can the original requested facts be returned? | Original requested page/record/field clauses; exact selected field replies and qualifications; constrained current report interpretation, if any | Original form persists. R's typed selected facts / exact own projection remain missing. The model does not compose recorded facts. |
| Does absence establish a negative result? | Complete/partial page; selected-page versus whole-query status; matched/indeterminate/unavailable/excluded counts; missing/null/invalid/empty distinctions | P page state exists; R collection semantics are proposed. No match with indeterminate records cannot establish absence. |
| Is waiting meaningful? | Actual pending work or selected wait condition; received progress and compatible time expectations only when present | Shared wait support exists. UniProt is an immediate response with no service status/poll operation. Never invent a remote job, pending page, retry delay, throughput or ETA. |
| What repairs are actually possible? | Specific field/selection/binding failure and the actual tool catalog; immutable original request/selector | Catalog has `api.uniprot.collect` with empty action arguments plus runtime information tools. This episode cannot change the assigned query/accession/cursor/size or invent a parser-repair tool. A new collect may reattempt only the same assigned work when selected; it is never automatic. |

Full source or sequence grants in the parent-selected return do not mean the
continuing results episode needs to read those bytes again in its prompt. Show
grant availability only. Keep scientific accession, GO/ECO identifiers, coordinates,
units, owner relationships and explicitly selected windows when they affect the
requested result. Custody IDs/digests, code module names, source paths and native
unselected text stay outside the message.

## Completion is not another prompt

A native complete page and an outer completed acquisition are separate facts.
When the existing validated practical endpoint closes this results episode,
there is **no next decision dispatch**. The complete-response example is a
rendering fixture / conditional next-decision view only; it must never create an
extra model call. A partial outer outcome can reach the next ordinary decision.
No completion result changes earlier gains, changes the parent form, or selects
more work. No approval, review or acceptance gate is added to runtime.

## Required verification when implementation is later authorized

1. Actual partial `collect` -> `DecisionSource.execute` -> `next` -> context-aware
   preview -> visible-reference scan -> provider input. Assert exact selected
   text/letters, qualifications and unchanged retained full publication.
2. No leak through `last_local_outcome`, duplicated `feedback.rows`, working
   state, execution progress, target metadata, return-schema traversal,
   reconstructed frames, or a generic JSON fallback. No publication/source or
   sequence handle introduced by the new preview.
3. Original contract selection survives replay and a partial continuation.
   Repeated same-source acquisitions are authenticated by their exact action;
   neither a newer nor an earlier snapshot silently replaces this outcome.
4. Original ordinals 0 / malformed 1 / valid 2; parser-complete with binding
   omission; legacy-label failure with selected native text available; missing
   headers; present empty collection; null/invalid collection; known accession,
   GO database and positional feature selectors without prior ordinals.
5. Complete native data stays recoverable internally. Metadata-only display
   creates no receipt, credit, lookup action, extra observation or source grant.
6. The complete endpoint uses the existing exact-zero estimate and ordinary
   comparison without dispatching a template for an extra final turn. Partial
   termination still returns valid requested partial facts through the original
   form. Historical saved calls/forms and their observations are unchanged.

Only source/document inspection and later stdlib artifact consistency checks are
within this design task. None of these integration checks has been run here.
