# a102 / structural_homology_evidence / execution_job_submission / local_job_execution

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/execution_job_submission/local_job_execution/<file>`. I read only the files directly in this folder. It has no `grading/` or `scoring/` subfolder. Its `tests/` folder was not read.

## Purpose (its own words)
It is the execution agent for one actual job on one assigned **local** resource. Its words: "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. ... If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. ... The episode iterator decides continuation from credit; add no stopping budget." (`terminal_goal.py`). It also adds any resource instructions from the frozen launch-instruction library.

## Task and instructions
- Role `launch_local` only. `entry_roles = ()`, so it can only be commissioned and cannot be an entry. Its commissioning parent is `structural_homology_evidence/execution_job_submission`, the `launch` role.
- The instruction composition (`instructions.py`) is: the specialist goal above (delegated to the per-resource `TerminalExecutionBehavior`, `goal.py`), then the reasoning-commit text when `reason` is permitted (it is not), tool-knowledge and launch-library instructions, report-repair text, wait text (wait is not permitted), and native-event text. Under the decision-exchange protocol it replaces the history guidance.
- `replaces_default_instructions = True`.

## What it reads from its parent's assignment
- One resource request (`from_parent.py`). The schema has one alternative per configured resource of kind `local`, with `resource_id`/`resource_kind` constants and `requested_job` anyOf: generic requested job, native protein-structure tool inputs, or resource-specific requested-job schemas (`requested_job_schemas`). It also carries the practical assignment fields (`workspace`, `endpoint` usable_handoff or completed_job_outputs, `initial_context`, `constraints`).
- `prepare_assignment` requires the parent role to be `launch`, matching kinds, and a valid original launch assignment (requests, constraints, immutable input versions). It also validates the protein-structure job inputs.
- On every `initialize` and `execute` (`operations.py`), it re-reads the parent's recorded `runtime_episodes.request.message.episode_assignment` and re-validates it.
- `initial_references` are the protein-structure job input references.

## Children
None. `child_roles` and `allowed_children` return `()`.

## Decision state shown to the model
- The generic decision state (`decision_context.py`): goal, scope, working state, visible record refs, current credit and credit binding, time accounting, pending work, last outcome/feedback, visual evidence, report deliveries, controller state/binding, tools, tool knowledge, job options, available report facts, requested purpose/form, current report update and basis.
- Then `internal_summary.decision_context`: the terminal context (execution assignment, resource info including workspace/policy/account/ssh_argv/python_executable/scheduler/inventory, coordinator workspace, `execution_progress` = practical state credit view, `execution_completion`). For a local native protein-structure job it adds `selected_execution_task` (the scientific parent's `scientific_question` and `selected_tool_info`, requests, constraints, selector).
- `initial_decision_context`: `execution_resource_capabilities` (availability `unknown`, no probe) and `execution_initial_information`.
- `decision_delivery.call` adds resource context, the launch-instruction library and selected instructions, completed action reports, `launch_local` execution expectations, resource and native estimates, and pending work.
- Prompt renderer: `present_native_task` (TASK + STEERING + current execution information). It is used only for a selected local execution context: not HPC, not published-scientific, not API launch (`decision_provider.py`).

## Tools
- `exec_command` (`terminal_contracts.operation_catalog`). Inputs: `cmd` (string or argv), `workdir`, `env`, and optional `target` resource/coordinator. Each call is one journaled action with a host receipt (`PracticalState.begin/finish`, `finalize_scientific_command`, validations), published as a practical receipt source.
- Common actions: `tool` only (`action_policy.py`).
- `resource_tool_contracts` describes the configured launch/results operations, for the parent's catalog.

## Credit
- Kind `operational`. Live credit is the terminal `PracticalState.credit_view()`: operational progress toward the assignment's endpoint predicates. For a native protein-structure job it is the native results credit view.
- After closure the parent receives exactly the closed view pinned in `runtime_forms` (`closed_credit.py`). Later deliveries never reprice it.
- No clamping is visible in this episode's files.

## Continuation
- Private yield binding required (`require_private_yield`).
- Settings: `task_yield_profiles['launch_local:' + request class]` → `{cutoff, parameters}`. The request class is `practical_local[_native_...]_handoff` or `_outputs` (`yield_estimator.py`).
- Old estimator: `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`. This is a completion-with-target estimate: verified completion gives an exact-zero next gain. It maps to the new **completion with a target** yield estimator.

## Report to parent
- Fact sources (`to_parent.py`):
  - the terminal facts: `practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`;
  - `execution_handoff_refs`: authenticated returnable handoffs, including those found in its own receipts;
  - `execution_result_refs`;
  - `execution_completed`;
  - `execution_result_origin`;
  - native protein-structure facts, empty unless applicable.
- Closed-credit facts are added at closure.
- `validate_report` requires every `x-source` field to equal the recorded fact.
- For annotation and structural receivers it supplies `received_report_sources/facts` (file sources/outcomes, protein-structure facts).

## Differences visible
- Compared with `execution_result_acquisition`, it shares the configuration, contracts, closed credit, result-record and reference-access code almost verbatim. The terminal behaviour is split into `terminal_*` mixins here, but is one monolithic `terminal_execution.py` there.
- The task loop (`task.py`) is the results copy except for grain `launch_local` and the decision-context method name (`assemble_decision_context`).
- Unlike the results episode, `required_return_sources` returns `()` in both branches.

## File by file

Old-runner names column: `imp:` = `import gene_annotation_episode.episodic_workflow.root.a102.<module>` (old runner or old shared non-episode module; see runs/placement_plan/placement.tsv and runs/placement_merge/plan.tsv for where non-episode modules went). `runtime.X` = name used through `_live_original_runtime` (root.a102.runtime). `table:` = old journal/receipt SQLite table. ×N = number of uses. Per-use detail: runs/carry_over/calls/a102_02.tsv.

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| action_policy.py | 7 | Permits only the `tool` common action (no reason, child, wait or redeliver). | none |
| binding_record.py | 9 | Binding identity `structural_homology_evidence/execution_job_submission/local_job_execution`, version `execution_episode_v1`, configuration record (resources, initial inventory, handoff/acquired-record credit units, log window/roles, private yield flag, results and task yield profiles). | none |
| child_eligibility.py | 10 | No children: `child_roles` and `allowed_children` return `()`. Leaf episode. | none |
| closed_credit.py | 117 | Once closed, the parent sees exactly the operational credit view captured at closure (pinned receipt prefix, completion, archive and history digests); later deliveries never reprice it. Raises `execution_closed_credit_*_conflict` on any mismatch. | EpisodeReceipts×2, EpisodeReturnRecords×2, imp:episode_receipts×1, imp:episode_return_records×3, table:runtime_episodes×2, table:runtime_forms×3, table:runtime_observations×1, table:runtime_receipt_inheritance×2, table:runtime_record_receipts×2 |
| completion.py | 49 | Practical completion proof for an action (native protein-structure results or delegated terminal state); verification reuses only an endpoint verification actually recorded in controller history (exactly one matching observation). | ESTIMATOR_VERSION×2, imp:episode_return_records×1, imp:method_loop.identities×1, imp:numerical×1, imp:practical_yield×1, NumericBand×2, table:runtime_observations×1 |
| configuration.py | 62 | Constructor: explicit resources (kinds local / pbs_ssh / api), rejects foreign `native_*` bindings except `native_protein_structure`, requires positive handoff and acquired-record units, log window bytes/roles, optional private yield; validates results and task yield profiles (`cutoff`, `parameters`); builds a per-resource `TerminalExecutionBehavior`, API execution, progress provider, local-file sources and native protein-structure results/returns. | imp:api_service_execution×1, imp:execution_progress×1, imp:native_protein_structure_results×1, imp:native_protein_structure_returns×1, imp:numerical×1, YieldController×3, YieldParameters×3 |
| contracts.py | 53 | Constants: versions, roles (`launch`, `launch_api`, `launch_local`, `launch_hpc`, `results`), KINDS, ROLE_KINDS, schemas (RESULTS_SCHEMA, NATIVE_SELECTOR_SCHEMA, NATIVE_RESULT_ORIGIN), `launch_operation_catalog` (`execution.capabilities`), `native_result_operation_catalog` (`execution.results.status/collect/read`), `_outcome`. Shared verbatim with execution_result_acquisition/execution_contracts.py. | imp:a102_execution_bindings×1, imp:communication×1, imp:domain×1, imp:execution_contracts×1, imp:launch_instructions×1, imp:local_file_capture_results×1, imp:native_protein_structure_acquisition×1, imp:practical_execution_operations×1, imp:practical_execution_records×1, imp:practical_execution_state×1, imp:practical_receipt_information×1, imp:resource_records×1, imp:structural_homology_evidence.execution_job_submission.local_job_execution.terminal_execution×1 |
| credit.py | 27 | Credit kind `operational`; projected credit = closed view if closed, else native protein-structure credit view or the delegated terminal state's `credit_view` (receipt-based operational progress). | none |
| decision_context.py | 45 | Assembles the model's decision state: goal, scope, working state, visible refs, current credit, credit binding, time accounting, pending work, last outcome/feedback, visual evidence, deliveries, controller state, tools, tool knowledge, job options, report facts, requested form, current report update; then the specialist's `decision_context`. Generic runner code with annotation-axis branches that do not apply here. | imp:runtime×2, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, self.workflow.binding_context×1, self.workflow.catalog×1, self.workflow.controller_binding×1, self.workflow.delivery_status×1, self.workflow.extra_report_sources×1, self.workflow.is_scientific_source×1, self.workflow.job_episode_options×1, self.workflow.journal×3, self.workflow.knowledge×1, self.workflow.local_outcome_preview×1, self.workflow.pending_work×1, self.workflow.receipt_projection×1, self.workflow.run_id×1, self.workflow.source_credit_binding×1, self.workflow.source_credit_view×1, self.workflow.specialist×1, self.workflow.store×3, self.workflow.tools×1, self.workflow.working_state×1, table:runtime_actions×2 |
| decision_contracts.py | 128 | Decision-exchange protocol helpers: interpretation context, exchange schema (request_context or select_action), envelope validation, replay validation of exchange history. Generic runner copy. | imp:decision_context×1, imp:execution_prompt×1, imp:library.hpc_prompt×1, imp:runtime×2, imp:structural_homology_evidence_prompt×1, runtime.apply_state_frame×1, runtime.composition_lookup_schema×2, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.Draft202012Validator×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.Mapping×2, runtime.model_snapshot×1, runtime._object×3, runtime._recorded_action_generation_schema×1, runtime._references_in×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, self.workflow.contract_information_reply×1, self.workflow.decision_exchanges×2, self.workflow.journal×1, self.workflow.store×2, self.workflow.validate_contract_information×2, table:runtime_model_calls×1 |
| decision_delivery.py | 137 | `call`: saves/replays the decision model call; adds resource context, launch-instruction library, child options, initial binding context, completed action reports, HPC requested-action history, pending work, `launch_local` execution expectations, resource/native estimates, waiting support; `instruction_composer = instructions`. Generic runner copy with role key `launch_local`. | imp:decision_context×1, imp:episode_work_report×2, imp:execution_prompt×1, imp:library.hpc_prompt×2, imp:runtime×2, imp:structural_homology_evidence_prompt×1, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.child_option_information×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime.Mapping×1, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, self.workflow.available_child_roles×1, self.workflow.binding_context×1, self.workflow.contract_information_profile×1, self.workflow.decision_exchanges×1, self.workflow.decision_protocol×3, self.workflow.episode_bindings×1, self.workflow.execution_expectations×1, self.workflow.freeze_contract_information×1, self.workflow.freeze_literature_numerical_contracts×1, self.workflow.history_preview×1, self.workflow.is_job_source×3, self.workflow.job_episodes×2, self.workflow.journal×1, self.workflow.launch_instructions×2, self.workflow.native_estimation_context×1, self.workflow.numerical_contracts×1, self.workflow.pending_work×1, self.workflow.permits_common_action×1, self.workflow.provider×2, self.workflow.receipts×4, self.workflow.resource_context×1, self.workflow.resource_estimator×5, self.workflow.services×1, self.workflow.shared_information_context×1, self.workflow.uses_received_record_context×2, self.workflow.validate_contract_information×2, self.workflow.waiting_support×1, table:runtime_model_calls×5 |
| decision_exchange.py | 108 | `exchange_decision`: own-attempt lookups during one pending decision (child_options, composition_information, own-attempt lookup), immutable per-dispatch records. Generic runner copy. | imp:decision_context×1, imp:execution_prompt×1, imp:library.hpc_prompt×1, imp:runtime×2, imp:structural_homology_evidence_prompt×1, runtime._action_generation_schema×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts×1, runtime.Mapping×1, runtime.model_snapshot×1, runtime._plain×2, runtime.requested_contract_information×1, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×4, runtime.yield_table×1, self.workflow.controller_binding×1, self.workflow.decision_exchanges×1, self.workflow.execute×1, self.workflow.journal×1, self.workflow.run_id×1, self.workflow.services×1, self.workflow.validate_contract_information×1, table:runtime_model_calls×2 |
| decision_presentation.py | 20 | `present_native_task`: renders the detached selected-execution TASK plus STEERING (yields, controller, credit, completed reports, last outcome, feedback, pending work, deliveries, waiting support, resource estimates) and current execution information (execution_progress.execution_completed, practical_progress credit/requirements, practical_completion). This episode's prompt renderer. | imp:structural_homology_evidence_prompt×1 |
| decision_provider.py | 20 | Uses `complete_with_presentation` with this episode's renderer only for a selected local execution context (not HPC, not published-scientific, not API launch); otherwise plain `provider.complete`. Role name `REASONING`. | imp:decision_context×1, imp:execution_prompt×1, imp:library.hpc_prompt×1, imp:runtime×1, imp:structural_homology_evidence_prompt×1, self.workflow.provider×1, self.workflow.specialist×1 |
| episode.py | 34 | Assembles the binding: `binding_path = structural_homology_evidence/execution_job_submission/local_job_execution`, `commissioning_parent = structural_homology_evidence/execution_job_submission`, `roles = ('launch_local',)`, `entry_roles = ()` (cannot be an entry), decision source `NativeTask`, renderer `present_native_task`, `replaces_default_instructions = True`. | none |
| from_parent.py | 111 | Assignment schema: one alternative per configured resource whose kind matches the role (`local`), with `resource_id` const, `resource_kind` const and `requested_job` anyOf generic job / native protein-structure tool inputs / resource-specific requested-job schemas. `prepare_assignment`: parent must be role `launch`, kinds must match, re-validates the parent's original launch assignment, protein-structure job inputs and immutable input versions. `initial_references`: the protein-structure job input refs. `required_return_sources` returns `()`. | imp:native_protein_structure_tool_info×1, imp:protein_structure_operands×3, self.services.annotation_task_required×1 |
| goal.py | 7 | `instructions` delegate to the practical terminal behaviour for the assigned resource. | none |
| instructions.py | 22 | Composes instructions: specialist instructions + reasoning commit (if permitted) + tool knowledge + launch-instruction library + report-repair text + wait text + native-event text; swaps history guidance under decision exchange. | imp:runtime_prompt×2, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×3, runtime_prompt.REASONING_COMMIT_REQUIREMENT×1, self.workflow.binding_context×1, self.workflow.decision_protocol×1, self.workflow.knowledge×1, self.workflow.launch_instructions×1, self.workflow.native_event_information×1, self.workflow.permits_common_action×3, self.workflow.specialist×1 |
| internal_summary.py | 101 | `initial_decision_context`: resource capabilities and initial inventory. `decision_context`: delegated terminal context plus `selected_execution_task` (scientific question and selected tool info from the scientific parent, requests, constraints, selector) when the job is a local native protein-structure job. Capabilities (availability `unknown`, no probe) and `resource_tool_contracts` (launch/results operations per resource, native protein-structure contracts, routes). | imp:native_protein_structure_tool_info×1, self.services.scientific_parent_task×1 |
| operations.py | 40 | `_delegate` picks API execution or the resource's terminal behaviour; `initialize`/`execute` first re-check the parent launch assignment from the recorded `runtime_episodes` row, protein-structure inputs and input versions; `state` only for launch_local/launch_hpc; `catalog` delegated. | imp:protein_structure_operands×1, table:runtime_episodes×1 |
| received_information.py | 37 | Fact sources/facts this episode supplies when an `annotation` or `structural_homology_evidence` receiver reads its return: protein-structure fact sources plus `execution_file_source_refs` / `execution_file_capture_outcomes`. | imp:protein_structure_result_views×1 |
| received_record_selection.py | 35 | `_received`: from the known record refs, split execution results (excluding native protein-structure bundles, matching assignment) and returnable practical/API handoffs whose target matches the context. | none |
| received_reference_custody.py | 35 | Resolve/validate references received through returns: local file sources, protected protein-structure access, native protein-structure returns; `received_form_references` qualifies handoff/result/receipt refs. | none |
| report_delivery.py | 25 | `finish`: without a report contract returns credit + pending handles + binding facts; with a contract, saves facts + interpretations + form once in `runtime_forms` and returns the form. Generic runner copy. | imp:library.private_policy_call×1, imp:library.report_fact_assembly×1, imp:runtime×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, self.workflow.binding_context×1, self.workflow.episode_bindings×1, self.workflow.facts×1, self.workflow.journal×2, self.workflow.pending_handles×1, self.workflow.release×2, self.workflow.source_credit_view×1, table:runtime_forms×2 |
| report_reference_access.py | 45 | `resolve(context, reference, namespace)`: protected protein access first, execution handles via services, practical receipts via delegate, local file sources, execution results (non-empty windows for `execution_result`), handoffs, practical receipt information, API, services, then store scope/namespace check. | imp:episode_bindings×2 |
| result_records.py | 158 | Results-role machinery present in this launch episode: `_versions`, `_target`, `_selector`, `_result_directory`, `_windows`, `_selected_result_action`, `_validate_result_body`, `_read_result`, `_selection` (received/known refs from services, receipts or own actions), `_context_target`. | EpisodeReceipts×2, imp:episode_receipts×1, imp:execution_input_versions×1, imp:protein_structure_selection×1, self.services.record_selection×1, table:runtime_actions×2, table:runtime_episodes×1, table:runtime_receipt_inheritance×2 |
| retained_protein_reader.py | 95 | `retained_protein_structure_reader` classmethod (uses `cls.__new__`) building a read-only native protein-structure returns reader; `_protein_reference_access` (protected denials cannot fall through); `_retained_protein_result` recovers target metadata from received saved sheets or own completed receipts. | imp:execution_contracts×1, imp:native_protein_structure_results×1, imp:native_protein_structure_returns×1, imp:protein_structure_contracts×1, imp:protein_structure_operands×1, imp:protein_structure_selection×1, imp:state×1, table:runtime_episodes×1 |
| task.py | 221 | `NativeTask.next`: replay / durable-execution resume, ready owned child, model call, source failure -> `SourceEnd('source_failed')`. `apply_response`: decode, validate selection, `workflow.selected`, rejection feedback (event target, job_child storage/control failures, action contract, reads.map parameter hints), report_update validation with grain `launch_local`. `execute`: journal action, run reason/wait/tool, pending work after action, receipts, automatic score updates, credit from `source_credit_view`, staged completion, `ActionFailure` for unobserved outcomes. | imp:episode_source_failure×1, imp:library.action_contracts×1, imp:library.private_policy_call×1, imp:providers×1, imp:read_mapping×1, imp:runtime×2, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime.ContractError×1, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×2, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×2, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×3, runtime._wait_target_feedback×2, runtime.WorkflowError×2, self.workflow.action_schema×1, self.workflow.automatic_score_updates×1, self.workflow.binding_context×1, self.workflow.completed_unit×3, self.workflow.completions×3, self.workflow.controller_value×2, self.workflow.decision_exchanges×3, self.workflow.delivery_resolution_inputs×1, self.workflow.execute×1, self.workflow.execution_binding×7, self.workflow.inprocess_replay×4, self.workflow.journal×7, self.workflow.last_observed_credit×1, self.workflow.next_return×1, self.workflow.pending_work×1, self.workflow.perform_selected_wait×1, self.workflow.permits_common_action×1, self.workflow.receive_native_outcome×1, self.workflow.receive_outcome×1, self.workflow.resolve_pending_deliveries×1, self.workflow.resolver×1, self.workflow.retain_shared_grading_results×1, self.workflow.run_id×3, self.workflow.selected×3, self.workflow.source_credit_view×1, self.workflow.specialist×1, self.workflow.store×8, self.workflow.validate_report×1, table:runtime_actions×8, table:runtime_episodes×1, table:runtime_model_calls×2 |
| task_state.py | 108 | Decision-source state (`calls`, feedback, last outcome, report values/basis, replay flags, interpret schema); `record_execution_failure` records a failed selected tool/reason action into the iterator with its credit; `restore`, `restore_checkpoint`, `record_effect`, `checkpoint`. | imp:episode_source_failure×1, imp:runtime×2, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, self.workflow.archive×1, self.workflow.completions×4, self.workflow.context×1, self.workflow.controller_value×1, self.workflow.execution_binding×4, self.workflow.grains×1, self.workflow.inprocess_replay×7, self.workflow.journal×5, self.workflow.progress_provider×2, self.workflow.recover_commissions×1, self.workflow.run_id×1, self.workflow.source_credit_view×1, self.workflow.store×2, table:runtime_actions×5 |
| terminal_assignment.py | 22 | Terminal assignment: validates assignment, resource kind matches role (`launch_local`->`local`), operations validate; schema `ASSIGNMENT_SCHEMA`. | none |
| terminal_contracts.py | 24 | Terminal constants: `VERSION terminal_execution_episode_v1`, ROLE_KINDS, `operation_catalog(kind)` = the single `exec_command` tool (cmd, workdir, env, target resource/coordinator). | imp:acquisition×1, imp:communication×1, imp:domain×1, imp:practical_execution_operations×1, imp:practical_execution_records×1, imp:practical_execution_state×1, imp:terminal_execution×1 |
| terminal_credit.py | 11 | Terminal credit view and completion proof from `PracticalState`. | none |
| terminal_execution.py | 41 | `TerminalExecutionBehavior` composed from terminal_* mixins: resources local/hpc only, `as_record` `terminal_execution`, no children, credit `operational`, only `tool`, `practical_estimator` = PracticalYieldEstimator over state completion. | imp:practical_yield×1, PracticalYieldEstimator×2 |
| terminal_goal.py | 18 | The execution-agent goal text: write and run shell code with `exec_command`, no prescribed setup sequence, preserve caller inputs/outputs/acceptance, inventory is not proof of usability, each command is one ordinary action with its credit, investigate uncertain submissions instead of duplicating, target=resource vs coordinator, ssh_argv transport, "add no stopping budget"; plus frozen-library resource instructions. | services.workflow (getattr)×1 |
| terminal_operations.py | 47 | `exec_command` execution: schema-validate, operations validate, `state.begin`/`finish` receipts, `finalize_scientific_command`, cwd/env revision, validations, publish practical receipt source; invalid arguments return status `invalid`. | imp:practical_receipt_information×1, imp:terminal_scientific_evidence×2 |
| terminal_report.py | 31 | Terminal facts: `practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`; resolve receipts; `validate_report` requires recorded-fact fields to equal facts. | imp:practical_receipt_information×2 |
| terminal_state.py | 18 | Practical state directory `practical-execution/<digest(run_id, episode_id)>`, `PracticalState` with initial validations. | none |
| terminal_summary.py | 16 | Terminal decision context: assignment, resource info (kind, workspace, policy, account, ssh_argv, python_executable, scheduler, inventory), coordinator workspace, execution progress, completion. | none |
| to_parent.py | 62 | Fact sources: for `results` role file/protein facts; for launch_local/launch_hpc the terminal facts; plus `execution_handoff_refs`, `execution_result_refs`, `execution_completed`, `execution_result_origin`. `facts` = live facts + closed credit facts; live facts add authenticated returnable handoffs from own practical receipts. `validate_report` checks fact fields equal recorded facts. | imp:local_file_capture_results×1, imp:protein_structure_result_views×2 |
| waiting.py | 9 | `suspension_changed`: tells the old execution backend about suspension. Wait is not permitted for this episode. | self.workflow.execution_backend×1, self.workflow.execution_handle×2 |
| yield_estimator.py | 48 | `yield_controller` requires the private yield binding; profile key `launch_local:` + request class (`practical_<kind>_<native...>_<handoff or outputs>`, or api/compact); `YieldController(epoch, initial_credit, cutoff, YieldParameters(...), estimate_with_context=PracticalYieldEstimator(verify_completion))`. | imp:numerical×1, imp:practical_yield×1, PracticalYieldEstimator×2, YieldController×2, YieldParameters×2 |

## Carried over

One row per row of `runs/carry_over/functions/a102__structural_homology_evidence__execution_job_submission__local_job_execution.tsv`. kind: machinery (not carried) or episode function. The old files could not be read (the checkout has no .git); placement follows the intent record above and the function list.

| old file | name | kind | new place / reason |
|---|---|---|---|
| action_policy.py | NativeActionPolicy | episode function | task.py ACTION_SCHEMA (the one selection is the tool exec_command; no reason, child, wait or redeliver) |
| action_policy.py | NativeActionPolicy.permitted_common_actions | episode function | task.py ACTION_SCHEMA (the one selection is the tool exec_command; no reason, child, wait or redeliver) |
| binding_record.py | NativeBindingRecord | machinery | binding_record / the binding's own as_record(): system records bindings; settings are ctx.settings |
| binding_record.py | NativeBindingRecord.as_record | machinery | binding_record / the binding's own as_record(): system records bindings; settings are ctx.settings |
| child_eligibility.py | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} (leaf episode, no children) |
| child_eligibility.py | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} (leaf episode, no children) |
| child_eligibility.py | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} (leaf episode, no children) |
| closed_credit.py | NativeClosedCredit | machinery | closed-credit snapshot over runtime_forms/receipts tables: the system hands completion['credit'] to final_to_parent |
| closed_credit.py | NativeClosedCredit._closed_credit_carrier | machinery | closed-credit snapshot over runtime_forms/receipts tables: the system hands completion['credit'] to final_to_parent |
| closed_credit.py | NativeClosedCredit._closed_credit_receipts | machinery | closed-credit snapshot over runtime_forms/receipts tables: the system hands completion['credit'] to final_to_parent |
| closed_credit.py | NativeClosedCredit._closed_credit_value | machinery | closed-credit snapshot over runtime_forms/receipts tables: the system hands completion['credit'] to final_to_parent |
| closed_credit.py | NativeClosedCredit._closed_credit_facts | machinery | closed-credit snapshot over runtime_forms/receipts tables: the system hands completion['credit'] to final_to_parent |
| closed_credit.py | NativeClosedCredit._closed_operational_credit_view | machinery | closed-credit snapshot over runtime_forms/receipts tables: the system hands completion['credit'] to final_to_parent |
| completion.py | NativeCompletion | episode function | messages/internal_summary.py _completion (completion proof over the receipts) |
| completion.py | NativeCompletion.completion_for_action | episode function | messages/internal_summary.py _completion; library candidate |
| completion.py | NativeCompletion._closed_completion_verdict | machinery | verdict from controller history (runtime_observations, ESTIMATOR_VERSION): the system journals controller steps |
| completion.py | NativeCompletion.verify_completion | machinery | estimator completion proof reading controller history: the controller input is the system's; target comes from parent_input |
| configuration.py | NativeConfiguration | episode function | task.py settings use (_resource_configuration) and yield_estimator.py settings |
| configuration.py | NativeConfiguration.__init__ | episode function | task.py _resource_configuration (kind and native-binding checks) and ctx.settings (resources, initial_information, coordinator_workspace, directories); yield profile validation in yield_estimator.py; API execution, progress provider, local-file and native result builders: unplaced (see blocked file) |
| contracts.py | launch_operation_catalog | episode function | UNPLACED: serves the launch parent's catalog (execution.capabilities); the parent states it in its own task.py |
| contracts.py | native_result_operation_catalog | episode function | UNPLACED: results-role catalog (execution.results.*); a launch acquires no results |
| contracts.py | _outcome | episode function | UNPLACED: helper of the two catalogs above |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (project_practical_credit, library) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit (the number); other fields in messages/internal_summary.py execution_progress |
| decision_context.py | NativeTaskContext | episode function | task.py decide context and messages/internal_summary.py |
| decision_context.py | NativeTaskContext.assemble_decision_context | episode function | task.py decide (context fields) over messages/internal_summary.py; the generic annotation-axis branches do not apply and are not carried |
| decision_contracts.py | NativeDecisionDeliveryContracts | machinery | decision-exchange protocol (exchange_decision loop and its replay validation): a lookup is a tool, the system compares model requests on resume |
| decision_contracts.py | NativeDecisionDeliveryContracts.interpretation_context | machinery | decision-exchange protocol (exchange_decision loop and its replay validation): a lookup is a tool, the system compares model requests on resume |
| decision_contracts.py | NativeDecisionDeliveryContracts.exchange_schema | machinery | decision-exchange protocol (exchange_decision loop and its replay validation): a lookup is a tool, the system compares model requests on resume |
| decision_contracts.py | NativeDecisionDeliveryContracts.exchange_response | machinery | decision-exchange protocol (exchange_decision loop and its replay validation): a lookup is a tool, the system compares model requests on resume |
| decision_contracts.py | NativeDecisionDeliveryContracts.validate_contract_exchange_request | machinery | decision-exchange protocol (exchange_decision loop and its replay validation): a lookup is a tool, the system compares model requests on resume |
| decision_contracts.py | NativeDecisionDeliveryContracts.validate_contract_exchange_history | machinery | decision-exchange protocol (exchange_decision loop and its replay validation): a lookup is a tool, the system compares model requests on resume |
| decision_delivery.py | NativeDecisionDelivery | episode function | task.py decide |
| decision_delivery.py | NativeDecisionDelivery.call | episode function | task.py decide (resource context, launch-instruction library, selected instructions); model-call saving/replay, child options, pending work, waiting support, HPC history are machinery |
| decision_delivery.py | NativeDecisionDelivery.instructions | episode function | task.py _instructions |
| decision_delivery.py | NativeDecisionDelivery.conversation_key | machinery | conversation state (conversation_key) is deleted |
| decision_exchange.py | NativeDecisionDeliveryExchange | machinery | exchange_decision: the decision-exchange loop is not carried |
| decision_exchange.py | NativeDecisionDeliveryExchange.exchange_decision | machinery | exchange_decision: the decision-exchange loop is not carried |
| decision_presentation.py | present_native_task | episode function | task.py _task_text |
| decision_provider.py | NativeDecisionDeliveryProvider | episode function | task.py decide (ModelRequest role REASONING) |
| decision_provider.py | NativeDecisionDeliveryProvider.complete_decision | episode function | task.py decide: ModelRequest('REASONING', ...); the provider call and complete_with_presentation are the system's |
| episode.py | ExecutionEpisode | episode function | episode.py LocalJobExecution (the one class) |
| from_parent.py | NativeAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | NativeAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the child's own form; the parent writes the assignment in its msg_to_child) |
| from_parent.py | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | NativeAssignment._permitted | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (DeclaredField resource_kind=local; the configured-resource alternatives are settings) |
| from_parent.py | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment, completion target); parent-role and launch-assignment re-validation over runtime_episodes is machinery |
| from_parent.py | NativeAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (requested_job record) |
| from_parent.py | NativeAssignment._validate_request | episode function | messages/read_from_parent.py read_from_parent (validate_assignment); immutable-input-version check UNPLACED (no module) |
| from_parent.py | NativeAssignment._launch | machinery | re-read of the parent's original launch assignment from runtime_episodes: old-runner table read |
| from_parent.py | NativeAssignment._constraints | episode function | messages/read_from_parent.py ASSIGNMENT_FORM constraints field |
| from_parent.py | NativeAssignment.required_return_sources | episode function | messages/final_to_parent.py RETURN_FORM (returned ()); the parent selects among the selectable fields |
| from_parent.py | NativeAssignment.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs (protein-structure job input references, passed in custody) |
| goal.py | NativeGoal | episode function | goal.py GOAL and task.py GOAL_INSTRUCTION |
| goal.py | NativeGoal.instructions | episode function | task.py _instructions / GOAL_INSTRUCTION |
| instructions.py | instructions | episode function | task.py _instructions (goal text, resource instructions, knowledge and launch paragraphs; reasoning, report-repair, wait and native-event paragraphs never apply) |
| internal_summary.py | NativeSummary | episode function | messages/internal_summary.py |
| internal_summary.py | NativeSummary.initial_decision_context | episode function | task.py _capabilities (execution_resource_capabilities, execution_initial_information) |
| internal_summary.py | NativeSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | NativeSummary._with_selected_execution_task | episode function | messages/internal_summary.py _selected_execution_task |
| internal_summary.py | NativeSummary._resource_information | episode function | task.py _resource |
| internal_summary.py | NativeSummary.capabilities | episode function | task.py _capabilities |
| internal_summary.py | NativeSummary.resource_tool_contracts | episode function | UNPLACED: describes the launch/results operations per resource for the parent's catalog |
| operations.py | NativeOperations | episode function | task.py tools |
| operations.py | NativeOperations._delegate | machinery | choice between API execution and terminal behaviour: not applicable to a local resource, no router object |
| operations.py | NativeOperations._practical_context | episode function | messages/internal_summary.py execution_context (working context after the last command) |
| operations.py | NativeOperations.initialize | machinery | re-check of the parent launch assignment from runtime_episodes on initialize: old-runner table read |
| operations.py | NativeOperations._check_parent_inputs | machinery | re-check of the parent launch assignment from runtime_episodes: old-runner table read; the input-version check is UNPLACED |
| operations.py | NativeOperations.state | episode function | job_access service state (BLOCKED-ON-JOB-SERVICE, see blocked file) |
| operations.py | NativeOperations.catalog | episode function | task.py EXEC_COMMAND (tool description) |
| operations.py | NativeOperations.execute | episode function | task.py exec_command |
| received_information.py | ReceivedExecutionInformation | episode function | messages/final_to_parent.py RETURN_FORM |
| received_information.py | ReceivedExecutionInformation.received_report_sources | episode function | messages/final_to_parent.py RETURN_FORM (execution_* fields); protein-structure fact sources and execution_file_source_refs UNPLACED |
| received_information.py | ReceivedExecutionInformation.received_report_facts | episode function | messages/final_to_parent.py _facts; protein-structure facts and file capture outcomes UNPLACED |
| received_information.py | ReceivedExecutionInformation.received_report_closure_facts | machinery | closed-credit facts at closure: credit is completion['credit'] |
| received_record_selection.py | NativeReceivedRecordSelection | machinery | receipts bookkeeping (known/received refs): system custody (README 3b P2, F2) |
| received_record_selection.py | NativeReceivedRecordSelection._received | machinery | receipts bookkeeping (known/received refs): system custody (README 3b P2, F2) |
| received_reference_custody.py | NativeReceivedReferenceCustody | machinery | receipt/custody checks of received references: system custody (README 3b R1, R3, F1) |
| received_reference_custody.py | NativeReceivedReferenceCustody.resolve_received_reference | machinery | receipt/custody checks of received references: system custody (README 3b R1, R3, F1) |
| received_reference_custody.py | NativeReceivedReferenceCustody.validate_received_report | machinery | receipt/custody checks of received references: system custody (README 3b R1, R3, F1) |
| received_reference_custody.py | NativeReceivedReferenceCustody.received_form_references | machinery | receipt/custody checks of received references: system custody (README 3b R1, R3, F1) |
| report_delivery.py | NativeReportDelivery | machinery | report_form machinery: runtime_forms save and release; the system admits the result against RETURN_FORM |
| report_delivery.py | NativeReportDelivery.finish | machinery | report_form machinery: runtime_forms save and release; the system admits the result against RETURN_FORM |
| report_reference_access.py | NativeReportReferenceAccess | machinery | reference resolver over receipts/practical receipts (custody, README 3b D2); records.holds(ref) |
| report_reference_access.py | NativeReportReferenceAccess.resolve | machinery | reference resolver over receipts/practical receipts (custody, README 3b D2); records.holds(ref) |
| result_records.py | ExecutionResultRecords | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._versions | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._target | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._selector | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._result_directory | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._windows | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._selected_result_action | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._validate_result_body | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._read_result | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._selection | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| result_records.py | ExecutionResultRecords._context_target | episode function | UNPLACED: results-role reading of acquired results of received handoffs; a launch acquires none |
| retained_protein_reader.py | NativeRetainedProteinReader | episode function | UNPLACED: retained protein-structure read authority over store.db and runtime_episodes; a launch retains none |
| retained_protein_reader.py | NativeRetainedProteinReader.retained_protein_structure_reader | episode function | UNPLACED: retained protein-structure read authority over store.db and runtime_episodes; a launch retains none |
| retained_protein_reader.py | NativeRetainedProteinReader._protein_reference_access | episode function | UNPLACED: retained protein-structure read authority over store.db and runtime_episodes; a launch retains none |
| retained_protein_reader.py | NativeRetainedProteinReader._retained_protein_result | episode function | UNPLACED: retained protein-structure read authority over store.db and runtime_episodes; a launch retains none |
| task.py | NativeTask | episode function | task.py decide, action, exec_command |
| task.py | NativeTask.next | machinery | decision loop: replay/durable-execution resume, ready child, model call, SourceEnd(source_failed): the system's |
| task.py | NativeTask.apply_response | episode function | task.py action (decode, schema and operations validation, Rejected feedback); report_update validation and reads.map hints are not applicable |
| task.py | NativeTask.execute | episode function | task.py exec_command (begin, run, finalize, assess, finish, publish); journaling, pending work, receipts, ActionFailure and staged completion are machinery |
| task_state.py | NativeTaskState | machinery | decision-source state, restore and checkpoint |
| task_state.py | NativeTaskState.__init__ | machinery | decision-source state (calls, feedback, replay flags): the system's |
| task_state.py | NativeTaskState.bind_execution_context | machinery | binding of the execution context to the old workflow |
| task_state.py | NativeTaskState.record_execution_failure | machinery | a failed command is the returned outcome of exec_command (status failed), journaled by the system |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | NativeTaskState.restore | machinery | checkpoint/restore |
| task_state.py | NativeTaskState.record_effect | machinery | record_effect: the attempts journal is the system's |
| task_state.py | NativeTaskState.checkpoint | machinery | checkpoint/restore |
| terminal_assignment.py | TerminalAssignment | episode function | messages/read_from_parent.py |
| terminal_assignment.py | TerminalAssignment._assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment, resource kind local) |
| terminal_assignment.py | TerminalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent; task.py _operations (operations validate_assignment) |
| terminal_assignment.py | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_contracts.py | operation_catalog | episode function | task.py EXEC_COMMAND |
| terminal_credit.py | TerminalCredit | episode function | credit.py credit |
| terminal_credit.py | TerminalCredit.credit_view | episode function | credit.py credit (project_practical_credit); messages/internal_summary.py execution_progress |
| terminal_credit.py | TerminalCredit.completion_for_action | episode function | messages/internal_summary.py _completion; library candidate |
| terminal_execution.py | TerminalExecutionBehavior | episode function | task.py, yield_estimator.py |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | task.py _resource_configuration, _operations (resource kind local, TerminalExecution over settings) |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | credit_kind is deleted (README 3d) |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py ACTION_SCHEMA (tool only) |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator: replaced by CompletionYieldController in yield_estimator.py (README 7b) |
| terminal_goal.py | TerminalGoal | episode function | task.py GOAL_INSTRUCTION |
| terminal_goal.py | TerminalGoal.instructions | episode function | task.py GOAL_INSTRUCTION, _instructions |
| terminal_goal.py | TerminalGoal._resource_instructions | episode function | task.py _instructions (LaunchInstructions.for_resource of the frozen library) |
| terminal_operations.py | TerminalOperations | episode function | task.py exec_command |
| terminal_operations.py | TerminalOperations._operations | episode function | task.py _operations |
| terminal_operations.py | TerminalOperations.catalog | episode function | task.py EXEC_COMMAND |
| terminal_operations.py | TerminalOperations.execute | episode function | task.py exec_command (state.begin/finish are the job_access service: BLOCKED-ON-JOB-SERVICE) |
| terminal_report.py | TerminalReport | episode function | messages/final_to_parent.py |
| terminal_report.py | TerminalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_report.py | TerminalReport.facts | episode function | messages/final_to_parent.py _facts |
| terminal_report.py | TerminalReport.resolve | machinery | resolver of practical receipt references over the old receipts: custody (records.holds) |
| terminal_report.py | TerminalReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| terminal_state.py | TerminalState | episode function | job_access service state (BLOCKED-ON-JOB-SERVICE) |
| terminal_state.py | TerminalState._state_directory | episode function | job_access service state: practical-execution/<digest(run_id, episode_id)> directory is the service's (BLOCKED-ON-JOB-SERVICE) |
| terminal_state.py | TerminalState.initialize | episode function | job_access service state: PracticalState with initial validations (BLOCKED-ON-JOB-SERVICE); initial validations are computed in messages/internal_summary.py |
| terminal_state.py | TerminalState.state | episode function | job_access service state (BLOCKED-ON-JOB-SERVICE) |
| terminal_summary.py | TerminalSummary | episode function | messages/internal_summary.py, task.py decide |
| terminal_summary.py | TerminalSummary.initial_decision_context | episode function | task.py _capabilities |
| terminal_summary.py | TerminalSummary._resource_information | episode function | task.py _resource |
| terminal_summary.py | TerminalSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| to_parent.py | NativeReport | episode function | messages/final_to_parent.py |
| to_parent.py | NativeReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (execution_handoff_refs, execution_result_refs, execution_completed, execution_result_origin and the terminal sources) |
| to_parent.py | NativeReport.facts | episode function | messages/final_to_parent.py _facts (closed-credit facts are credit = completion['credit']) |
| to_parent.py | NativeReport._live_facts | episode function | messages/final_to_parent.py _facts (handoff refs from the receipts of the commands run) |
| to_parent.py | NativeReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| waiting.py | NativeWaiting | machinery | suspension/wait machinery (wait is not permitted for this episode) |
| waiting.py | NativeWaiting.suspension_changed | machinery | suspension/wait machinery (wait is not permitted for this episode) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py _request_yield_class |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController, target from parent_input) |
| yield_estimator.py | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator(verify_completion): replaced by the completion controller (README 7b) |
