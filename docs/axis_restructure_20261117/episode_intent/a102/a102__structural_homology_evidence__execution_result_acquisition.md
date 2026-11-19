# a102 / structural_homology_evidence / execution_result_acquisition

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/execution_result_acquisition/<file>`. I read only the files directly in this folder. It has no `grading/`, `scoring/` or `tests/` subfolder.

## Purpose (its own words)
"Acquire the original selected execution results through the original handoff. Choose bounded status or requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the current resource filesystem: the exact attempt observation does not establish that current file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes this endpoint." (`goal.py`)

## Task and instructions
- Role `results`, which is also an entry role. Its commissioning parent is `structural_homology_evidence`. `replaces_default_instructions = True`.
- Instructions (`instructions.py`, the same composition as local_job_execution): goal + reasoning commit if permitted + tool knowledge + launch library + repair + wait (only for an API service target) + native event + exchange-history swap.

## What it reads from its parent's assignment
- `execution_results_assignment_v1`: `handoff_ref` and `selector`.
- The selector is one of:
  - native `{paths[] / path, offset, limit}`, confined to the handoff's workspace;
  - `local_file_source_selector_v1`;
  - `protein_structure_result_selector_v1`, including a `retained_sheet_only` saved-sheet descriptor;
  - an API result selector.
- `prepare_assignment`:
  - first restores a successfully returned original results commission recorded under the parent (`saved_result_commission.py`);
  - otherwise reads the target from the handoff, or from the retained protein receipt;
  - validates the selector, admits local file sources and validates protein-structure inputs.
- `required_return_sources` = `('execution_result_refs',)` when the parent is `structural_homology_evidence` and `services.annotation_task_required()`.
- `initial_references` = `[handoff_ref]`, or the protein-structure selected inputs.

## Children
None.

## Decision state shown to the model
- The generic decision state plus `internal_summary.decision_context`: `execution_assignment`, `execution_progress` (its own facts), `execution_target` (local files, retained protein target or handoff target) and `execution_target_description`. For local native protein-structure jobs it adds `selected_execution_task`.
- `initial_decision_context`: resource capabilities and initial inventory.
- `decision_inputs` adds resource context, shared information context, the launch library, completed action reports, HPC requested-action history (when an HPC context), `results` execution expectations, job/resource/native estimates and waiting support.
- Renderer: `render_selected_execution_prompt`. It is used only for a selected execution context that is not HPC, published-scientific or API launch.

## Tools
- Native targets:
  - `execution.results.status`: observe the exact handed-off attempt once;
  - `execution.results.collect`: observe and read first windows of the requested paths, each window up to min(log_window_bytes, 1 MiB, length);
  - `execution.results.read`: one window inside the requested path/interval.
- Native protein-structure, local-file and API targets use their own catalogs.
- The results are immutable intent/observation/window/receipt files, published as an `episode.execution_result` source.
- A result action after a verified completion is refused (`execution_results_assignment_already_completed`).
- Common actions: `tool`, plus `wait` for an `api_service_assignment_v1` target.

## Credit
- Kind `operational`.
- Native selector credit is `acquired_record_unit × (fraction of requested byte positions newly covered)` (`execution_received_selector_coverage_credit_v2`). Bytes already present in the initial known refs are excluded, and each position is credited once regardless of read boundaries. `handoff_unit` is multiplied by a handoff count fixed at 0.
- Mixed local-file sources: `acquired_record_unit × acquisition count` (`execution_received_records_credit_v1`).
- Protein-structure and API credit views are delegated.
- The closed view is pinned at closure, as in the local episode.

## Continuation
- Private yield required.
- Native finite selector:
  - profile `results:native_finite_<kind>`;
  - bounded credit estimate with `maximum_credit = acquired_record_unit × (1 - already received fraction)`;
  - exact zero once nothing remains;
  - practical endpoint estimate on verified completion.
  - This maps to the new **bounded quality** yield estimator.
- Native unbounded selector (a path without length): `results_yield_profiles['native_unbounded_<kind>']` with a plain YieldController. This corresponds to accumulation.
- API (`results:api_<service>[_version]`) and typed (`results:typed_<kind>_<version>`) targets use the completion-target estimate with PracticalYieldEstimator. This maps to **completion with a target**.

## Report to parent
- Fact sources: `execution_file_source_refs`, `execution_file_capture_outcomes`, protein-structure facts, `execution_handoff_refs`, `execution_result_refs` (only results with windows), `execution_completed` (`_native_results_complete`), `execution_result_origin` (native origin semantics, or null), plus closed-credit facts.
- `validate_report` requires fact fields to equal the recorded facts.

## Differences visible
- It shares the launch episode's configuration, contracts and custody code. It adds:
  - its own result acquisition, publication and recorded-commission restoration;
  - selector-coverage credit;
  - a three-way yield selection (finite, unbounded, typed/API).
- `required_return_sources` returns `('execution_result_refs',)` here, but `()` in the launch episode.
- Its terminal behaviour copy is one monolithic `terminal_execution.py`, used only as the per-resource delegate.

## File by file

Old-runner names column: `imp:` = `import gene_annotation_episode.episodic_workflow.root.a102.<module>` (old runner or old shared non-episode module; see runs/placement_plan/placement.tsv and runs/placement_merge/plan.tsv for where non-episode modules went). `runtime.X` = name used through `_live_original_runtime` (root.a102.runtime). `table:` = old journal/receipt SQLite table. ×N = number of uses. Per-use detail: runs/carry_over/calls/a102_02.tsv.

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| acquisition_operations.py | 37 | Tool catalog by target: native protein-structure result catalog, API catalog, or `execution.results.status/collect/read`; `execute` routes to local file sources, protein-structure results, API execution or native results; errors become an `invalid` outcome (retained-artifact capture errors re-raise). | imp:native_file_capture×1, imp:native_protein_structure_results×1 |
| action_policy.py | 13 | `tool` only, except `tool, wait` for an API target with `api_service_assignment_v1`. | none |
| binding_record.py | 8 | Binding identity `structural_homology_evidence/execution_result_acquisition`, same configuration record as the launch episode. | none |
| child_commissioning.py | 11 | No children. | none |
| closed_credit.py | 116 | Closed operational credit view (same rule as local_job_execution). | EpisodeReceipts×2, EpisodeReturnRecords×2, imp:episode_receipts×1, imp:episode_return_records×3, table:runtime_episodes×2, table:runtime_forms×3, table:runtime_observations×1, table:runtime_receipt_inheritance×2, table:runtime_record_receipts×2 |
| completion.py | 116 | `_native_results_complete`: every requested path window covered contiguously by completed returncode-0 observations; `_proof_for_action` builds `practical_completion_v1` (endpoint `usable_handoff`, validation keys) from own completed result bodies; API delegated; verification with recorded-history reuse. | ESTIMATOR_VERSION×2, imp:episode_return_records×1, imp:method_loop.identities×1, imp:numerical×1, imp:practical_yield×1, NumericBand×2, table:runtime_actions×2, table:runtime_observations×1 |
| configuration.py | 61 | Same constructor as local_job_execution (resources, units, log selection, yield profiles, terminal/API/progress/local-file/protein components). | imp:api_service_execution×1, imp:execution_progress×1, imp:native_protein_structure_results×1, imp:native_protein_structure_returns×1, imp:numerical×1, YieldController×3, YieldParameters×3 |
| credit.py | 65 | Operational credit: `handoff_unit × 0 + acquired_record_unit × new selector byte-coverage fraction` (`execution_received_selector_coverage_credit_v2`), or for mixed local-file acquisitions `acquired_record_unit × count` (`execution_received_records_credit_v1`); protein-structure or API views delegated. Bytes already in the initial known refs earn nothing. | none |
| decision_contracts.py | 127 | Generic decision-exchange helpers. | imp:decision_context×1, imp:execution_prompt×1, imp:library.hpc_prompt×1, imp:runtime×2, imp:structural_homology_evidence_prompt×1, runtime.apply_state_frame×1, runtime.composition_lookup_schema×2, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.Draft202012Validator×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.Mapping×2, runtime.model_snapshot×1, runtime._object×3, runtime._recorded_action_generation_schema×1, runtime._references_in×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, self.workflow.contract_information_reply×1, self.workflow.decision_exchanges×2, self.workflow.journal×1, self.workflow.store×2, self.workflow.validate_contract_information×2, table:runtime_model_calls×1 |
| decision_exchange.py | 107 | Generic `exchange_decision`. | imp:decision_context×1, imp:execution_prompt×1, imp:library.hpc_prompt×1, imp:runtime×2, imp:structural_homology_evidence_prompt×1, runtime._action_generation_schema×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts×1, runtime.Mapping×1, runtime.model_snapshot×1, runtime._plain×2, runtime.requested_contract_information×1, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×4, runtime.yield_table×1, self.workflow.controller_binding×1, self.workflow.decision_exchanges×1, self.workflow.execute×1, self.workflow.journal×1, self.workflow.run_id×1, self.workflow.services×1, self.workflow.validate_contract_information×1, table:runtime_model_calls×2 |
| decision_inputs.py | 58 | Decision inputs: resource context, shared information context, launch-instruction library, child options, initial binding context, completed action reports, HPC requested history, pending work, `results` execution expectations, job/resource/native estimates, waiting support. | imp:episode_work_report×2, imp:library.hpc_prompt×1, imp:runtime×2, runtime.child_option_information×1, runtime.Mapping×1, self.workflow.available_child_roles×1, self.workflow.binding_context×1, self.workflow.episode_bindings×1, self.workflow.execution_expectations×1, self.workflow.is_job_source×1, self.workflow.job_episodes×2, self.workflow.launch_instructions×2, self.workflow.native_estimation_context×1, self.workflow.pending_work×1, self.workflow.permits_common_action×1, self.workflow.resource_context×1, self.workflow.resource_estimator×5, self.workflow.shared_information_context×1, self.workflow.waiting_support×1 |
| decision_provider.py | 19 | Presentation renderer only for selected execution contexts (not HPC / published-scientific / API launch). | imp:decision_context×1, imp:execution_prompt×1, imp:library.hpc_prompt×1, imp:runtime×1, imp:structural_homology_evidence_prompt×1, self.workflow.provider×1, self.workflow.specialist×1 |
| decision_state.py | 45 | Generic decision-state assembly. | imp:runtime×2, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, self.workflow.binding_context×1, self.workflow.catalog×1, self.workflow.controller_binding×1, self.workflow.delivery_status×1, self.workflow.extra_report_sources×1, self.workflow.is_scientific_source×1, self.workflow.job_episode_options×1, self.workflow.journal×3, self.workflow.knowledge×1, self.workflow.local_outcome_preview×1, self.workflow.pending_work×1, self.workflow.receipt_projection×1, self.workflow.run_id×1, self.workflow.source_credit_binding×1, self.workflow.source_credit_view×1, self.workflow.specialist×1, self.workflow.store×3, self.workflow.tools×1, self.workflow.working_state×1, table:runtime_actions×2 |
| episode.py | 38 | `binding_path structural_homology_evidence/execution_result_acquisition`, `commissioning_parent structural_homology_evidence`, roles/entry_roles `('results',)`, decision source `ResultsTask`, renderer `render_selected_execution_prompt`, `replaces_default_instructions`. | imp:structural_homology_evidence_prompt×1 |
| execution_contracts.py | 47 | Same constants as local `contracts.py`, but imports its own `terminal_execution` copy. | imp:a102_execution_bindings×1, imp:communication×1, imp:domain×1, imp:execution_contracts×1, imp:launch_instructions×1, imp:local_file_capture_results×1, imp:native_protein_structure_acquisition×1, imp:practical_execution_operations×1, imp:practical_execution_records×1, imp:practical_execution_state×1, imp:practical_receipt_information×1, imp:resource_records×1, imp:structural_homology_evidence.execution_result_acquisition.terminal_execution×1 |
| execution_state.py | 39 | `initialize`: local file selector check, selector check, protein-structure input refs, API initialize, result directory with immutable `assignment.json`. | none |
| from_parent.py | 57 | Assignment = RESULTS_SCHEMA (`execution_results_assignment_v1`, `handoff_ref`, `selector`) with local-file and protein-structure selector branches; `prepare_assignment` restores a recorded results commission, else reads the target from the handoff, validates selector, admits local file sources, protein inputs. `required_return_sources` = `('execution_result_refs',)` when parent is `structural_homology_evidence` and an annotation task is required. `initial_references` = handoff ref or protein inputs. | imp:protein_structure_operands×3, imp:protein_structure_selection×1, self.services.annotation_task_required×1 |
| goal.py | 9 | Goal: acquire the original selected execution results through the original handoff; bounded status or requested reads chosen from preceding outcomes; preserve partial bytes and native scores; current filesystem is not proof the attempt produced those bytes; separate windows are not atomic; the scientific parent interprets; work/resource/selector fixed; only complete acquisition establishes the endpoint. | none |
| instructions.py | 23 | Same composition as local `instructions.py`. | imp:runtime_prompt×2, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×3, runtime_prompt.REASONING_COMMIT_REQUIREMENT×1, self.workflow.binding_context×1, self.workflow.decision_protocol×1, self.workflow.knowledge×1, self.workflow.launch_instructions×1, self.workflow.native_event_information×1, self.workflow.permits_common_action×3, self.workflow.specialist×1 |
| internal_summary.py | 40 | Decision context: assignment, `execution_progress` = own facts, target (local files / retained protein result / handoff target) and its description, plus `selected_execution_task` for local native protein-structure jobs. | imp:local_file_capture_results×1, imp:protein_structure_execution_information×1, self.services.scientific_parent_task×1 |
| parent_input_custody.py | 39 | `_validate_request`, `_launch`, `_constraints` (re-validate the original launch request behind the handoff). | none |
| received_record_selection.py | 35 | Same `_received` as local. | none |
| received_records.py | 37 | Same received facts for annotation/structural receivers as local. | imp:protein_structure_result_views×1 |
| received_reference_custody.py | 37 | Same as local. | none |
| report_delivery.py | 25 | Generic finish. | imp:library.private_policy_call×1, imp:library.report_fact_assembly×1, imp:runtime×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, self.workflow.binding_context×1, self.workflow.episode_bindings×1, self.workflow.facts×1, self.workflow.journal×2, self.workflow.pending_handles×1, self.workflow.release×2, self.workflow.source_credit_view×1, table:runtime_forms×2 |
| report_fields.py | 19 | Fact sources: file source refs/outcomes, protein-structure facts, `execution_handoff_refs`, `execution_result_refs`, `execution_completed`, `execution_result_origin`. | imp:local_file_capture_results×1, imp:protein_structure_result_views×1 |
| report_reference_access.py | 47 | Same `resolve` as local. | imp:episode_bindings×2 |
| resource_information.py | 82 | Resource information, initial decision context, capabilities, resource tool contracts (same as local internal_summary parts). | imp:native_protein_structure_tool_info×1 |
| result_selection.py | 75 | `_target`, `_selector`, `_windows`, `_selection`, `_context_target` (same as local result_records parts). | EpisodeReceipts×2, imp:episode_receipts×1, imp:protein_structure_selection×1, self.services.record_selection×1, table:runtime_actions×1, table:runtime_receipt_inheritance×2 |
| retained_protein_reader.py | 94 | Same as local. | imp:execution_contracts×1, imp:native_protein_structure_results×1, imp:native_protein_structure_returns×1, imp:protein_structure_contracts×1, imp:protein_structure_operands×1, imp:protein_structure_selection×1, imp:state×1, table:runtime_episodes×1 |
| retained_result_acquisition.py | 70 | `_execute_native_results`: the selected action must match; read windows only inside requested paths/intervals; collect = first windows up to min(log_window_bytes, 1 MiB, length); refuses after completion; immutable intent/observation/window/receipt files; publish result source. | table:runtime_actions×2 |
| retained_result_publication.py | 59 | `_publish_result`, `_validate_result_body` (identity, scope, target, selector, saved action, episode row, window bounds, receipt file), `_read_result`. | table:runtime_episodes×1 |
| saved_result_commission.py | 45 | `_recorded_results_assignment`: restores a successfully returned original results commission from the parent's receipt manifest and report attempt. | EpisodeReceipts×2, EpisodeReturnRecords×2, imp:episode_receipts×1, imp:episode_return_records×1, table:runtime_actions×1, table:runtime_episodes×1, table:runtime_report_attempts×1 |
| task.py | 223 | Generic loop, grain `results`, `instruction_composer = instructions`. | imp:episode_source_failure×1, imp:library.action_contracts×1, imp:library.private_policy_call×1, imp:providers×1, imp:read_mapping×1, imp:runtime×2, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime.ContractError×1, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×2, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×2, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×3, runtime._wait_target_feedback×2, runtime.WorkflowError×2, self.workflow.action_schema×1, self.workflow.automatic_score_updates×1, self.workflow.binding_context×1, self.workflow.completed_unit×3, self.workflow.completions×3, self.workflow.controller_value×2, self.workflow.decision_exchanges×3, self.workflow.delivery_resolution_inputs×1, self.workflow.execute×1, self.workflow.execution_binding×7, self.workflow.inprocess_replay×4, self.workflow.journal×7, self.workflow.last_observed_credit×1, self.workflow.next_return×1, self.workflow.pending_work×1, self.workflow.perform_selected_wait×1, self.workflow.permits_common_action×1, self.workflow.receive_native_outcome×1, self.workflow.receive_outcome×1, self.workflow.resolve_pending_deliveries×1, self.workflow.resolver×1, self.workflow.retain_shared_grading_results×1, self.workflow.run_id×3, self.workflow.selected×3, self.workflow.source_credit_view×1, self.workflow.specialist×1, self.workflow.store×8, self.workflow.validate_report×1, table:runtime_actions×8, table:runtime_episodes×1, table:runtime_model_calls×2 |
| task_decision.py | 88 | Generic `call` with literature numerical freezing and `is_job_source` receipt guard. | imp:decision_context×1, imp:execution_prompt×1, imp:library.hpc_prompt×1, imp:runtime×2, imp:structural_homology_evidence_prompt×1, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, self.workflow.contract_information_profile×1, self.workflow.decision_exchanges×1, self.workflow.decision_protocol×3, self.workflow.freeze_contract_information×1, self.workflow.freeze_literature_numerical_contracts×1, self.workflow.history_preview×1, self.workflow.is_job_source×2, self.workflow.journal×1, self.workflow.numerical_contracts×1, self.workflow.provider×2, self.workflow.receipts×4, self.workflow.services×1, self.workflow.uses_received_record_context×2, self.workflow.validate_contract_information×2, table:runtime_model_calls×5 |
| task_state.py | 108 | Generic state (tool and reason failures). | imp:episode_source_failure×1, imp:runtime×2, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, self.workflow.archive×1, self.workflow.completions×4, self.workflow.context×1, self.workflow.controller_value×1, self.workflow.execution_binding×4, self.workflow.grains×1, self.workflow.inprocess_replay×7, self.workflow.journal×5, self.workflow.progress_provider×2, self.workflow.recover_commissions×1, self.workflow.run_id×1, self.workflow.source_credit_view×1, self.workflow.store×2, table:runtime_actions×5 |
| terminal_execution.py | 242 | Monolithic copy of `TerminalExecutionBehavior` (same content as the local episode's terminal_* mixins) used for the native resource delegates. | imp:acquisition×1, imp:communication×1, imp:domain×1, imp:practical_execution_operations×1, imp:practical_execution_records×1, imp:practical_execution_state×1, imp:practical_receipt_information×3, imp:practical_yield×1, imp:terminal_execution×1, imp:terminal_scientific_evidence×2, PracticalYieldEstimator×2 |
| to_parent.py | 37 | `facts`: live + closed credit; API facts; native facts with `execution_completed = _native_results_complete`. `validate_report` checks fact fields. | imp:protein_structure_result_views×1 |
| waiting.py | 9 | `suspension_changed`. | self.workflow.execution_backend×1, self.workflow.execution_handle×2 |
| yield_estimator.py | 79 | Private yield required. Native finite selector: profile `results:native_finite_<kind>`, `estimate_bounded_credit_yield` with `maximum_credit = acquired_record_unit × (1 - already-received fraction)`, exact-zero once exhausted, practical endpoint estimate on verified completion. Native unbounded selector: `results_yield_profiles['native_unbounded_<kind>']` with plain YieldController. API: `results:api_<service>[_<selector version>]`; typed: `results:typed_<kind>_<version>`; both with PracticalYieldEstimator. | estimate_bounded_credit_yield×2, imp:numerical×1, imp:practical_yield×2, NumericBand×2, PracticalYieldEstimator×5, YieldController×4, YieldEstimate×2, YieldParameters×4 |
