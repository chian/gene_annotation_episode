# A108 organism and sample context ownership

A108 has its own scientific instructions, source interpretation, credit rules,
and saved scoring sheets. Root code routes an A108 commission to these A108
bindings. A108 evidence is counted by original contextual observation identity.

| A108 binding | Responsibility |
| --- | --- |
| `literature_episode.py` | A108's contextual episode construction, source custody, reports, credit, and continuation binding; it has no cross-axis dispatch |
| `literature_a108_prompt.py`, `literature_parent_prompt.py`, `literature_experimental_prompt.py`, `literature_reference_parent_prompt.py` | A108 child and parent instructions, source discovery wording, and full prompt presentation |
| `literature_task_credit.py` | A108 commission schema, source lead and screening validation, assessment credit, and continuation control |
| `literature_required_grading.py` | Grade each applicable contextual interpretation within its original action |
| `literature_a108_grading.py`, `literature_a108_grading_inputs.py`, `literature_a108_grading_storage.py` | Context grading criteria, input validation, and saved subscoring sheets |
| `literature_sheet_policy.py`, `literature_sheet_updates.py`, `literature_revision_aggregation.py` | A108 sheet publication, current-sheet projection, and revision handling |
| `literature_a108_aggregation.py`, `literature_a108_aggregation_storage.py` | Distinct original-observation unions and main scoring sheet |
| `literature_annotation_scalar.py` | A108 contribution and target-attribution binding |
| `literature_work_report.py`, `literature_work_results.py`, `literature_current_results.py` | A108-local work and saved-result presentation |
| `literature_a108_sources.py`, `literature_source_inputs.py`, `literature_assay_inputs.py` | Source access, witnesses, and contextual input validation |
| `literature_population_catalog.py`, `literature_task_families.py`, `scientific_process_task_projector.py` | A108 operations and commissioned scientific result projection |
| `literature_numerical_contracts.py` | A108's contextual sheet meanings, held beside its grading code |

The other modules in this directory are A108-local dependencies of those
bindings. A108 tests and reusable A108 test inputs live in [`tests/`](tests/)
beside the A108 code. Disposable execution output belongs under the repository
`runs/` directory.

## Scientific process binding copy (2026-11-11)

| Original symbol | Destination | Axis | Role and caller | Change |
| --- | --- | --- | --- | --- |
| `scientific_process_episodes.py::ScientificProcessEpisodes` | `scientific_process_episode.py::ScientificProcessEpisode` | A108 | Scientific process binding; caller-specific setup and descriptor reopening | Copied into a singular private binding with local credit, guidance, fact, report and decision routes. |

The A108 literature binding was narrowed on 2026-11-11 to its contextual
grading and aggregation operations. Foreign population flags, foreign
repositories, and cross-axis operation routes were removed. Its source and
sheet receipt checks still use original episode identities to preserve
scientific provenance and prevent a delivered subset from expanding into a
whole sheet.

### Private A108 source registry (2026-11-11)

The actual A108 literature access/acquisition declarations select source/state/document/image readers, taxonomy, NCBI/UniProt and publication/sequence-identity discovery. Independent copies below preserve those source operations. Experimental assay-database acquisition/reader branches are excluded because they are not in the A108 declared tool set. No homology/native alignment, read mapping, RNA, structural, flux-balance, variant or configured assay execution was copied. A108 context grading, original observation identities, subscoring sheets, typed findings and iterator behavior remain in their existing private bindings.

| Original module | Private destination | Role/caller | Change |
|---|---|---|---|
| `tools.py` | `a108/tools.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `acquisition.py` | `a108/acquisition.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `api_error_feedback.py` | `a108/api_error_feedback.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `sequence_views.py` | `a108/sequence_views.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `library_targets.py` | `a108/library_targets.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `materials_packing.py` | `a108/materials_packing.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `source_locations.py` | `a108/source_locations.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `document_tools.py` | `a108/document_tools.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `spreadsheet_tools.py` | `a108/spreadsheet_tools.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `spreadsheet_worker.py` | `a108/spreadsheet_worker.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `literature_assets.py` | `a108/literature_assets.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `image_evidence.py` | `a108/image_evidence.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `literature_sequence_discovery.py` | `a108/literature_sequence_discovery.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `source_sequences.py` | `a108/source_sequences.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `ncbi_entrez_tools.py` | `a108/ncbi_entrez_tools.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `ncbi_entrez_acquisition.py` | `a108/ncbi_entrez_acquisition.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `api_uniprot.py` | `a108/api_uniprot.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `uniprot_native.py` | `a108/uniprot_native.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `uniprot_native_contracts.py` | `a108/uniprot_native_contracts.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `uniprot_publication.py` | `a108/uniprot_publication.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `public_configuration.py` | `a108/public_configuration.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `uniprot_service_support.py` | `a108/uniprot_service_support.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `native_json.py` | `a108/native_json.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `native_timing_information.py` | `a108/native_timing_information.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |
| `materials.py applicable artifact/source byte readers` | `a108/source_bytes.py` | Private A108 source registry and its direct source/document/identity helpers | Copied applicable implementation independently; fixed worker/client module paths to A108. |

The literature binding still calls `services.execute_tool`; root service construction remains an explicit unresolved dependency. Store/domain/communication types, local jobs/resources and some source storage/receipt infrastructure remain common boundaries to separate where behavioral. No compatibility forwarding or axis selector was added. No tests, Python or parse/import validation run.

2026-11-11 runtime binding: this axis's tools.workflow_services now supplies its private service to runtime. Provenance, current tool invocation, instruction libraries, tool retrieval and semantic receipts are constructed through that service. Original runtime investigation/action-delivery and decision-exchange instructions are independent runtime_prompt.py/decision_protocol_prompt.py copies. Original tool_knowledge.py, launch_instructions.py, scientific_tool_retrieval.py, boundary_validation.py and episode_receipts.py have private implementations and direct callers. Imports of already-present local helpers were rebound directly. Root message parsing, Store/domain/communication, numerical/execution infrastructure and remaining helper dependencies are still open; no execution validation is claimed.

| Original module/symbol | Destination | Role/caller | Change |
|---|---|---|---|
| investigation_progress.py, scientific_findings.py, finding_validity.py | Same descriptive filenames under a108/ | Original whole-axis finding credit; scientific_process_task_projector and literature credit | Copied independently; exact typed findings, replacement closure, target scope and receipt semantics retained |
| tools/replay_literature_sheet_publications.py: A108 branch | a108/tests/replay_sheet_publications.py | Retained context-grading publication replay | Fixed A108 repositories/constructor/tables and --state/--output; no axis selection; not run |


## 2026-11-11 private runtime, parsing, storage and numerical dependencies

These are independent A108 implementations. Runtime and frame callers bind local types directly. Source grading, saved sheets, typed scientific findings and the original iterator remain in their private episode paths. Foreign structure, restriction, homology-job and other-axis runtime dispatch were removed from these copies.

| Original module/symbol | Private destination | Role/caller | Change |
|---|---|---|---|
| domain.py | a108/domain.py | Private runtime form and reference parsing | Copied applicable implementation and rebound direct callers |
| communication.py | a108/communication.py | Private runtime form and reference parsing | Copied applicable implementation and rebound direct callers |
| form_reference_validation.py | a108/form_reference_validation.py | Private runtime form and reference parsing | Copied applicable implementation and rebound direct callers |
| episode_contract_information.py | a108/episode_contract_information.py | Private runtime form and reference parsing | Copied applicable implementation and rebound direct callers |
| schema_information_text.py | a108/schema_information_text.py | Private runtime form and reference parsing | Copied applicable implementation and rebound direct callers |
| schema_support.py | a108/schema_support.py | Private runtime form and reference parsing | Copied applicable implementation and rebound direct callers |
| runtime.py | a108/runtime.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_bindings.py | a108/episode_bindings.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_admission.py | a108/episode_admission.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_journal.py | a108/episode_journal.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_application_services.py | a108/episode_application_services.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_source_failure.py | a108/episode_source_failure.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| default_scientific_binding.py | a108/default_scientific_binding.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| decision_context.py | a108/decision_context.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_return_records.py | a108/episode_return_records.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_commissions.py | a108/episode_commissions.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_completion.py | a108/episode_completion.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_report_acquisition.py | a108/episode_report_acquisition.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| episode_input_versions.py | a108/episode_input_versions.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| decision_exchanges.py | a108/decision_exchanges.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| decision_history.py | a108/decision_history.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| inprocess_replay.py | a108/inprocess_replay.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| pending_assignment.py | a108/pending_assignment.py | Private workflow, frame admission and return custody | Copied applicable implementation and rebound direct callers |
| state.py | a108/state.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| materials.py | a108/materials.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| context_masks.py | a108/context_masks.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| journal_metadata.py | a108/journal_metadata.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| sequence_mapping.py | a108/sequence_mapping.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| evidence_geometry.py | a108/evidence_geometry.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| material_parsing.py | a108/material_parsing.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| genbank_intake.py | a108/genbank_intake.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| library_targets.py | a108/library_targets.py | Private Store and material/context intake | Copied applicable implementation and rebound direct callers |
| numerical.py | a108/numerical.py | Private numerical estimator and typed execution receipts/forecasts | Copied applicable implementation and rebound direct callers |
| execution_timing.py | a108/execution_timing.py | Private numerical estimator and typed execution receipts/forecasts | Copied applicable implementation and rebound direct callers |
| run_statistics.py | a108/run_statistics.py | Private numerical estimator and typed execution receipts/forecasts | Copied applicable implementation and rebound direct callers |
| execution_recording.py | a108/execution_recording.py | Private numerical estimator and typed execution receipts/forecasts | Copied applicable implementation and rebound direct callers |
| execution_expectations.py | a108/execution_expectations.py | Private numerical estimator and typed execution receipts/forecasts | Copied applicable implementation and rebound direct callers |
| ordinary_execution.py | a108/ordinary_execution.py | Private numerical estimator and typed execution receipts/forecasts | Copied applicable implementation and rebound direct callers |
| resource_estimation.py | a108/resource_estimation.py | Private numerical estimator and typed execution receipts/forecasts | Copied applicable implementation and rebound direct callers |
| alignment_site_native.py: immutable_record; execution_contracts.py: canonical/digest | a108/record_identity.py | Frame receipt identity readers | Split exact record helpers without foreign native execution |
| _local_job_worker.py: atomic_json | a108/native_receipt_file.py | Native receipt publication | Split exact atomic writer |
| vendor/nano_rarefaction.py and source/license manifests | a108/vendor/ | Private numerical estimator | Copied formula and source metadata independently |

The active Store API and production callers use `account_invocation`. Historical `owner` and `account_owner` dictionary labels remain only in existing record/signature hashes to preserve immutable identities; they do not select an axis. Ordinary execution statistics retain the actual spreadsheet operations, with foreign alignment adapters removed.

Remaining dependencies include local execution/resources/lifecycle, waiting/completion monitoring, operational memory, provider construction, composition helpers and a PAF reader reachable through generic Store validation. Physical placement does not establish full separation or combined integration. No tests, parse/import checks, jobs or workflows were run.

## Private runtime event applicability — 2026-11-11

Removed the unused homology NativeEventInformation construction/configuration, prospective homology planning, context, wait, report, resolver and fact branches from A108 runtime. Removed legacy job-duration normalization and its unused native-job-event configuration helper. A108 has no producer for these homology job/event contracts. Its ordinary wait, receipt, resource-progress and iterator paths remain bound to private implementations. Only runtime.py, episode_bindings.py and this note changed in this pass; no tests, static validation or Python execution.


2026-11-11: `method_loop/` and its license/source manifests were independently copied to `a108/library/method_loop/`. A108 runtime, frame, numerical and evidence helpers import this private episode/record/controller protocol implementation directly. Its durable worker command names the private module; the repository root for subprocess imports was adjusted for placement. Original iterator, commission/return records and continuation behavior are unchanged. No execution validation was run.


## 2026-11-11 private execution, waiting, presentation and reconstruction

| Original module/symbol | Destination | Role and caller | Change |
|---|---|---|---|
| `local_jobs.py` | `a108/local_jobs.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `local_resources.py` | `a108/local_resources.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `_local_job_worker.py` | `a108/_local_job_worker.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `native_lifecycle.py` | `a108/native_lifecycle.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `native_events.py` | `a108/native_events.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `workflow_budget.py` | `a108/workflow_budget.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `execution_memory.py` | `a108/execution_memory.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `waiting.py` | `a108/waiting.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `wait_estimation_inputs.py` | `a108/wait_estimation_inputs.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `local_return_history.py` | `a108/local_return_history.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `completion_evidence.py` | `a108/completion_evidence.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `episode_monitoring.py` | `a108/episode_monitoring.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `progress_records.py` | `a108/progress_records.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `inprocess_waiting.py` | `a108/inprocess_waiting.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `composition_information.py` | `a108/composition_information.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `resource_records.py` | `a108/resource_records.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `execution_contracts.py` | `a108/execution_contracts.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `execution_planning.py` | `a108/execution_planning.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `execution_guidance.py` | `a108/execution_guidance.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `shared_information.py` | `a108/shared_information.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `providers.py` | `a108/providers.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `provider_authentication.py` | `a108/provider_authentication.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `scientific_process_prompt.py` | `a108/scientific_process_prompt.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `episode_work_report.py` | `a108/episode_work_report.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `shared_information_results.py` | `a108/shared_information_results.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `episode_composition.py` | `a108/episode_composition.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `application_execution_binding.py` | `a108/application_execution_binding.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `independent_execution.py` | `a108/independent_execution.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `tool_configuration.py` | `a108/tool_configuration.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `material_gzip.py` | `a108/material_gzip.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `literature_contract_error.py` | `a108/literature_contract_error.py` | Private runtime, tool execution, completion, source presentation or saved construction | Copied applicable original code; direct local callers |
| `rna_structure_comparison_receiver_prompt.py`: generic task/goal/source/return display | `a108/receiver_prompt.py` | Ordinary source receiver TASK | Split generic supplied-task presentation; removed comparison-specific projection |
| `hpc_resource_prediction.py`: RESOURCE_UNITS, measured_value | `a108/hpc_resource_prediction.py` | ExecutionMemory measured input validation | Split original finite-value primitives; no scheduler/forecast code |

Source spreadsheet execution uses the same private statistics/policy classes through the native worker. Worker module paths and subprocess import roots follow A108 placement. The machine launcher resource envelope remains unchanged. Waiting and completion retain ordinary episode/resource status and original iterator/return custody; unsupported legacy homology job-status/event paths were removed. Provider text rendering retains the assigned A108 investigation, actual observations, original sheets, latest received outcomes and own earned credit without the former mixed RNA/MACS2/native renderer dispatch. The original source work report had no A108 native adapter; its generic saved-result/graded-sheet path remains. Presentation labels now name the credit episode/value source rather than an owner.

Saved-run construction has independent modules and worker identity. Foreign fixed-case/practical/native-service selection and unrelated fingerprint-repair exceptions were removed. Existing `private_binding_reopen_pending`, `private_scientific_reopen_pending` and private literature reopening errors remain explicit; reconstruction and combined integration are not validated or repaired by this placement pass. No tests, parse/import checks, jobs or workflows were run.


2026-11-11 source-observation dependency narrowing: the private Store/domain/evidence-axis observation readers no longer contain BLAST/database/HMMER/Infernal/Minimap marker dispatch or imports. These axes have no producer for those native markers; source-grounded observations, image anchors, typed findings, grading and actual measurement references retain their original paths. `material_gzip.py` and `literature_contract_error.py` are private original implementations, and their callers bind locally. No source/evidence processing was executed.

2026-11-11 acquisition class placement correction: the earlier local `acquisition.py` self-import was replaced with its independent original `AcquisitionError` class, preserving the original fields and RuntimeError base. No execution validation was run.

2026-11-11: controller and estimator descriptor module paths now name this axis's private numerical implementation, matching the existing private imports. Original numeric continuation and credit formulas are unchanged.

2026-11-11 numerical-source retirement: this axis's numerical provenance names
its own private vendor source and MIT license. Its private numerical/timing
implementations and source manifest retain the original estimator, receipt-time
semantics and formulas. Former shared numerical/timing implementation paths were
retired; no tests or execution were run.

## 2026-11-11 — Additional original-module placements

This supplement records original modules not named individually above. It maps their complete applicable module contents, including methods and constants; previous symbol-specific narrowing notes remain authoritative. Callers listed here are direct private imports or qualified worker module references, not execution receipts. It does not claim runtime validation.

| Original module/symbols | Destination | Current role/caller | Change |
|---|---|---|---|
| `gene_annotation_episode/episode_reports.py` (module contents) | `a108/episode_reports.py` | Private dependency used by `runtime.py`, `scientific_process_reports.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_services.py` (module contents) | `a108/episode_services.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_contracts.py` (module contents) | `a108/evidence_axis_contracts.py` | Private dependency used by `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py`, `scientific_support_metadata.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_instructions.py` (module contents) | `a108/evidence_axis_instructions.py` | Private dependency used by `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_a108_storage.py` (module contents) | `a108/literature_a108_storage.py` | Private dependency used by `literature_a108_aggregation_storage.py`, `literature_a108_grading_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_experimental_contracts.py` (module contents) | `a108/literature_experimental_contracts.py` | Private dependency used by `literature_assay_inputs.py`, `literature_partner_defined_units.py`, `literature_partner_source_fields.py`, `literature_rate_calculations.py`, `literature_rate_domains.py`, `literature_rate_native_inputs.py`, `literature_rate_reader.py`, `literature_rate_storage.py`, `literature_required_grading.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_partner_defined_units.py` (module contents) | `a108/literature_partner_defined_units.py` | Private dependency used by `literature_rate_native_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_partner_source_fields.py` (module contents) | `a108/literature_partner_source_fields.py` | Private dependency used by `literature_partner_defined_units.py`, `literature_rate_native_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_calculations.py` (module contents) | `a108/literature_rate_calculations.py` | Private dependency used by `literature_rate_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_domains.py` (module contents) | `a108/literature_rate_domains.py` | Private dependency used by `literature_rate_calculations.py`, `literature_rate_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_native_inputs.py` (module contents) | `a108/literature_rate_native_inputs.py` | Private dependency used by `literature_experimental_contracts.py`, `literature_rate_calculations.py`, `literature_rate_domains.py`, `literature_rate_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_reader.py` (module contents) | `a108/literature_rate_reader.py` | Private dependency used by `literature_rate_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_source_render.py` (module contents) | `a108/literature_rate_source_render.py` | Private dependency used by `literature_rate_domains.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_storage.py` (module contents) | `a108/literature_rate_storage.py` | Private dependency used by `literature_a108_storage.py`, `literature_rate_domains.py`, `literature_rate_source_render.py` | Copied/split; private implementation |
| `gene_annotation_episode/resource_tool_information.py` (module contents) | `a108/resource_tool_information.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_library.py` (module contents) | `a108/scientific_process_library.py` | Private dependency used by `composition_information.py`, `decision_context.py`, `episode_services.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_provenance.py` (module contents) | `a108/scientific_process_provenance.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_records.py` (module contents) | `a108/scientific_process_records.py` | Private dependency used by `evidence_axis_instructions.py`, `runtime.py`, `scientific_process_episode.py`, `scientific_process_library.py`, `scientific_process_prompt.py`, `scientific_process_provenance.py`, `scientific_process_reports.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_reports.py` (module contents) | `a108/scientific_process_reports.py` | Private dependency used by `scientific_process_episode.py`, `scientific_process_provenance.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_support_metadata.py` (module contents) | `a108/scientific_support_metadata.py` | Private dependency used by `episode_services.py`, `scientific_process_episode.py`, `scientific_process_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_tool_library.py` (module contents) | `a108/scientific_tool_library.py` | Private dependency used by `episode_services.py`, `scientific_process_records.py`, `scientific_tool_retrieval.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_information.py` (module contents) | `a108/tool_information.py` | Private dependency used by `resource_tool_information.py`, `scientific_process_prompt.py`, `scientific_process_records.py`, `scientific_process_reports.py`, `scientific_tool_library.py`, `scientific_tool_retrieval.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_schema_validation.py` (module contents) | `a108/tool_schema_validation.py` | Private dependency used by `resource_tool_information.py`, `scientific_tool_library.py` | Copied/split; private implementation |

2026-11-11: the private vendored numerical template now imports its completion/end-state types from this package's independent `library/method_loop/`, not the top-level repository loop. Upstream numerical code and constants are unchanged; this is the local import-placement patch.

## 2026-11-11 iterator package placement

Moved the independently copied `library/method_loop/` package to `method_loop/` beside the private workflow code. It contains episode bindings, continuation and return mechanics, so it is outside the standalone-helper library. Direct imports and durable-worker module paths now name this private location; the worker package-root depth follows the moved files. Original license and provenance manifests remain with the copy. No runtime behavior or stopping rule was added.

2026-11-11: The private contribution helper now fixes A108 in its record directly. Its aggregation and storage callers no longer pass an axis selector, and redundant private-axis guards were removed. Scientific range and attribution behavior are unchanged.

## 2026-11-11 recorded scientific-process episode destination

Before relocation: `scientific_process_episode.py:ScientificProcessEpisode` is
assigned to `scientific_process/episode.py` beneath this axis in
`gene_annotation_episode/episodic_workflow/root/`. Registered role: `scientific_process`;
commissioning parents: root annotation and the same recursive scientific-process
role. Keep the generic name: the assignment mixes task-selected investigation,
preparation/revision, tool choices and scientific result interpretation. A later
goal must divide those tasks and provide the missing dedicated axis head. This
pass must not manufacture either an axis head or infinitely nested recursion.

Supporting responsibilities: assignment/schema/preparation in `requests.py`;
typed reports, received results and references in `returns.py`; original task
projection in `credit.py`; task-selected continuation settings/estimator in
`yield_estimator.py`; registration, context, available actions/children and local assembly
in `episode.py`. Scientific scoring dependencies and their distinct descriptive
filenames remain as recorded above. Cross-episode tests/fixtures remain at this
axis's `tests/` until their precise local owner is established. Relocation is
pending; this entry fixes the chosen name before any binding moves.

### Scientific-process binding relocation applied

`scientific_process/episode.py` now owns the one `scientific_process` registration. The original module is removed; callers import the new binding directly. Each supporting class is private to this episode and has no registration.

- `scientific_process/episode.py`: `__init__`, `as_record`, `contract_information_profile`, `_role`, `child_roles`, `permitted_common_actions`, `allowed_children`, `instructions`, `_information_catalog`, `_closed_tool_resolution`, `_tool_resolution_for`, `_tool_resolution`, `catalog`, `common_tool_names`, `decision_context`, `execute`.
- `scientific_process/requests.py`: `assignment_schema`, `child_assignment_schema`, `_selection`, `_assignment`, `_invocation`, `prepare_assignment`, `_validate_origin`, `prepare_invocation`, `restore_closed_process`, `restore_saved_process`, `validate_context`, `validate_execution_context`, `_original_selection`, `_proposed_selection`.
- `scientific_process/returns.py`: `required_return_sources`, `fact_sources`, `facts`, `resolve`, `validate_report`, `initial_references`.
- `scientific_process/credit.py`: `credit_kind`, `credit_projector`, `credit_view`.
- `scientific_process/yield_estimator.py`: `private_yield_binding`, `continuation_task`, `yield_controller`.

Implementation fingerprinting continues to cover this axis's source tree, including the extracted files. No credit, yield, scientific scoring, report, waiting or request rule is changed. Descriptive scientific-process helper placement and test ownership remain to be completed in this pass.

## 2026-11-11 literature destinations recorded before splitting

The original `literature_episode.py:LiteratureEpisode` registers seven roles. These private replacements retain the current role-specific assignment, tools, source custody, grading, report, credit, yield and waiting semantics. Paths below are relative to this axis.

| Registered role | Chosen directory / binding | Commissioning parent |
| --- | --- | --- |
| `literature` | `scientific_process/published_evidence_assessment/episode.py` | `scientific_process` |
| `literature_strategy` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | `scientific_process/published_evidence_assessment` |
| `literature_search` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` |
| `literature_page` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` |
| `literature_table` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` |
| `literature_ordered` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` |
| `literature_targeted` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` |

Each binding retains its own local methods: `requests.py` for assignments and request-derived schemas; `returns.py` for source/fact/report delivery; `credit.py` for task progress; `yield_estimator.py` for existing forecast behavior; `waiting.py` for existing wait declarations; `episode.py` for registration, construction, actions, and selected grader/repository assembly. Files are created only for existing responsibilities. Descriptive calculators, graders and sheet storage retain their names and current axis ownership pending the dependency-placement review.

The current source-reading roles also perform applicable interpretation/population and grading work. That task mixture is preserved here; a later goal must decide task-specific divisions. Root evidence assessment can search/read directly as well as commission the nested strategy/search/source chain. Cross-role literature tests and shared fixtures remain at their common owner until the test-placement review.

### Literature role separation applied

The former multi-role class has been removed. Each recorded directory now has one independently implemented `LiteratureEpisode` with a singleton registration role; child-only bindings have empty entry roles. Their request/report/credit/yield/wait methods are private local supporting classes. The published-evidence episode exposes `create_binding_tree` only as caller assembly of seven separate instances, with copied existing caller configuration. It is not a registered binding, continuation policy or forwarding replacement. Existing scientific method bodies are preserved, including applicable A105/A108 grading and typed findings.

`literature` support map:

- `scientific_process/published_evidence_assessment/episode.py`: `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `_required_grading_repository`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_a108_grading_repository`, `_a108_aggregation_repository`, `_received_fact_display_context`, `_population_routes`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_a108_fact_sources`, `_a108_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/waiting.py`: `supports_wait`.

`literature_strategy` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py`: `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `_required_grading_repository`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_a108_grading_repository`, `_a108_aggregation_repository`, `_received_fact_display_context`, `_population_routes`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_a108_fact_sources`, `_a108_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/waiting.py`: `supports_wait`.

`literature_search` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py`: `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `_required_grading_repository`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_a108_grading_repository`, `_a108_aggregation_repository`, `_received_fact_display_context`, `_population_routes`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_a108_fact_sources`, `_a108_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/waiting.py`: `supports_wait`.

`literature_page` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py`: `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `_required_grading_repository`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_a108_grading_repository`, `_a108_aggregation_repository`, `_received_fact_display_context`, `_population_routes`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_a108_fact_sources`, `_a108_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/waiting.py`: `supports_wait`.

`literature_table` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py`: `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `_required_grading_repository`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_a108_grading_repository`, `_a108_aggregation_repository`, `_received_fact_display_context`, `_population_routes`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_a108_fact_sources`, `_a108_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/waiting.py`: `supports_wait`.

`literature_ordered` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py`: `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `_required_grading_repository`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_a108_grading_repository`, `_a108_aggregation_repository`, `_received_fact_display_context`, `_population_routes`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_a108_fact_sources`, `_a108_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/waiting.py`: `supports_wait`.

`literature_targeted` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py`: `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `_required_grading_repository`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_a108_grading_repository`, `_a108_aggregation_repository`, `_received_fact_display_context`, `_population_routes`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_a108_fact_sources`, `_a108_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/waiting.py`: `supports_wait`.


### Literature extraction verification

`runs/episode_literature_checks_20261111/checks.json` verifies this axis's seven
new private bindings: each imports, constructs with the original defaults, keeps
its original assignment schema/child roles/credit kind/wait declaration, and
registers alongside the other six without a role collision. Original method
bodies are preserved after import/path normalization; source-fingerprint and
singleton registration identity changes are checked separately. The axis's
scientific grading behavior is retained, with no new scientific run claimed.
Remaining task-specific test placement and descriptive dependency ownership
must still be reviewed before the full relocation goal can be complete.

## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/published_evidence_assessment` | `published_evidence_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement` | private copy | published_evidence_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | private copy | published_evidence_assessment/evidence_search_strategy_improvement |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/published_evidence_assessment` | `published_evidence_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement` | private copy | published_evidence_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | private copy | published_evidence_assessment/evidence_search_strategy_improvement |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

## 2026-11-11 binding test ownership

Current direct literature tests now import the private role matching their explicit context; standalone parent contexts use the standalone copy. Tests that construct root/runtime workflows stay at the common axis test owner. Scientific graders, sheets and fixtures are shared by the independent standalone/scientific copies and retain the common axis owner. Historical combined tests with already-retired top-level imports remain unavailable; source placement does not repair their missing runtime.

| Original test | Private episode test home | Roles |
| --- | --- | --- |
| `tests/replay_sheet_publications.py` | `published_evidence_assessment/tests/replay_sheet_publications.py` | literature |

Shared required fixtures stay in `tests/fixtures/`; reusable named test helpers remain in `tests/` when imported by other tests. No fixture or helper is moved into disposable runs. The detailed support/test inventory records the final owners.

## 2026-11-11 final role and supporting-code index

The [complete ownership inventory](ownership_inventory.json) is the exact appendix to this record: it maps every original binding class to its singleton role, actual parent, final home, local method symbols and responsibility files. It also records every descriptive support module, its owner, imports, direct callers and consuming episodes; every library symbol and its explicit importing modules; and each test/helper and required fixture file. Unreferenced retained modules are recorded with empty consumers, not represented as active evidence or bindings. Shared scientific graders, readers, sheets and calculators keep their descriptive names at the common axis owner. Their functions are not merged with investigation credit.

| Original binding | Role | Final home | Parent | Supporting files |
| --- | --- | --- | --- | --- |
| `literature_episode.py:LiteratureEpisode` | `literature` | `published_evidence_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `scientific_process_episode.py:ScientificProcessEpisode` | `scientific_process` | `scientific_process/episode.py` | root annotation; scientific_process self-recursion (not expanded) | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `scientific_process/published_evidence_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | scientific_process/published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |

The old scientific_process_episode.py, literature_episode.py and applicable operational *_episode.py modules have been removed. The tables above supersede earlier temporary-retention notes. The terminal operative behavior is private in the corresponding execution home and has no independent role registration. Generic scientific-process recursion and the missing task-specific axis head remain explicit. Scientific process still mixes target interpretation, tool selection and child commissioning; launch still mixes preparation, native/API execution and recovery. Their later scientific divisions are not redesigned here.

The role-only registry still cannot address equal role tokens under different parents. Existing axis service factories construct the scientific-parent family; standalone homes are independent source owners. The retained top-level A101 resource service explicitly constructs its five standalone private roles. Saved composition/reopening and the original legacy multi-role homology interface remain unavailable for complete composition. Every monitoring binding also retains its original monitor-to-monitor recursive edge; this reuses its owner home rather than expanding directories without end. No working whole-axis scientific workflow is claimed by the relocation. Consumer lists in the appendix describe static import reachability, not evidence of execution or scientific use.


## 2026-11-11 complete private implementation scope: parent identity

The full requested responsibility split remains incomplete. The earlier
structural completion claim is limited to the placement review. The
[current requirement audit](../../../../docs/EPISODE_PRIVATE_IMPLEMENTATION_PROGRESS.md)
records the complete specification and remaining work.

The axis-local registry now resolves explicit binding paths and original
commissioning parents. Core runtime selection, private task construction,
credit/continuation and child contracts use those identities. Ambiguous
role-only lookup fails; legacy bindings without private paths retain their
existing selection. This is reusable dispatch infrastructure, not a new episode
or scientific policy. The matching inventory entry names functions and callers.

Retained controlled verification: `runs/private_binding_identity_20261111_final/comparison.json` — 184 passes and the same 23 A105
baseline failures, with identical failure messages. All nine scientific-process
method bodies are preserved. Resource-route lookup, native replay ownership,
saved reopening and complete responsibility splits remain separate outstanding
work. No autonomous scientific workflow or full restoration is claimed.
