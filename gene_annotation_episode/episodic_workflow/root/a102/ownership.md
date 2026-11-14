# A102 ownership

The former A111 deposited-structure assessment is owned within A102; there is no separate A111 directory or selectable evidence axis.

| Original module or symbols | Destination in this directory | Change | Role and callers |
| --- | --- | --- | --- |
| Top-level `a102_attachments`, `a102_credit`, `a102_experimental_evidence`, `a102_investigation`, `a102_publication`, `a102_scoring`, `a102_structural_evidence`, `a102_structural_report`, `a102_structures`, `a102_work_report` | Same basenames | Moved | Structural evidence, grading, report and credit; A102 workflow, `episode_services`, shared scientific parent |
| Top-level `a102_hpc`, `a102_hpc_worker`, `a102_native_setup`, `a102_native_worker`, `a102_resources`, `a102_structural_bridge`, `a102_structural_workflow` | Same basenames | Moved | Native structure requests, workers and resource contracts; A102 tools and shared execution setup |
| Top-level `a102_tools` | `a102_tools.py` | Moved | A102 tool registry; combined `AllEvidenceToolRegistry` |
| Top-level `literature_structure_calculations`, `literature_structure_inputs`, `literature_structure_prompt`, `literature_structure_storage`, `literature_structure_types`, `literature_experiment_assessments` | Same basenames | Moved | Conditional deposited model reader and saved cells; `a102_experimental_evidence`, `a102_structural_report`, `episode_services`, literature dispatcher |
| A105 reader dependencies used by the structure repository: `literature_rate_storage`, `literature_rate_reader`, `literature_rate_calculations`, `literature_rate_native_inputs`, `literature_partner_source_fields`, `literature_partner_defined_units` | Same basenames | Copied | Local inherited receipt/storage methods and input parsing for `literature_structure_storage` and `literature_structure_inputs`; no A105 import remains in A102 runtime modules |
| A105 `literature_assay_inputs` parser reused by four A102 readers | `library/literature_assay_inputs.py` | Copied, then placed in library | Shared source witness and typed assay parsing for structure and local rate helpers |
| Shared literature value contracts: `literature_experimental_contracts` | Same basename | Copied | A102-local typed rate/unit contract for the structure-reader closure; uses the shared transport exception class from `literature_contract_error` |
| A101 region interval validator used by A102 native preparation | `library/a102_region_intervals.py` | Copied, then placed in library | Half-open region union for `a102_hpc` and `a102_tools` |
| Top-level `a102_structural_catalog.prepare_catalog` | `library/a102_structural_catalog.py` | Moved | Reusable original A111-to-A102 catalog preparation for standalone A102 and combined root setup |
| Shared `scientific_process_episodes.py` A102 branches | `a102_scientific_process_binding.py`, `a102_scientific_report_validation.py` | Split | Original task projector, guidance, received structure context, structural and investigation report validation; called by shared scientific parent |
| Shared `literature_episodes.py` and `literature_task_selection.py` A102 descriptors | `a102_literature_bindings.py` | Split | Catalog entry, task family, component schema, source/route metadata and repository selection; called by literature dispatcher |
| Root `literature_episodes.py` A102 binding and `literature_task_credit.py` source task policy | `literature_episode.py`, `literature_task_credit.py` | Copied and split | A102 structural-source assignment, population, returned cells and local task credit; called by A102 workflow/investigation constructors |

A102 tests and their reusable fixtures are beside A102 code in `tests/`.

A102 owns `literature_experimental_prompt.py`,
`literature_reference_parent_prompt.py`, and `literature_sheet_updates.py` for
its structural source presentation and saved sheet updates. Its local rate
storage uses that private sheet update copy.

`a102_credit.py` uses private A102 copies of native region mapping,
assessment-dependency lookup, and contribution scalar formatting in `library/`.

The private A102 literature binding and task selector now contain only A102
structure and source-reading paths. No workflow validation was run during this
file split.

## HPC episode ownership

| Original module or symbol | Private destination | Change | Role and callers |
| --- | --- | --- | --- |
| Top-level `hpc_episodes.py:HPCEpisodes` | `hpc_episode.py:HPCEpisode` | Copied and singularized | This axis's HPC parent binding; its workflow role declaration and the axis-specific execution factory descriptor. |
| Top-level `hpc_campaign.py`, `hpc_ledger.py`, `hpc_prediction.py`, `hpc_queue.py`, `hpc_allocation.py`, `hpc_monitoring.py`, `hpc_history.py`, `hpc_resource_prediction.py`, `hpc_commission_sources.py` | Same basenames in this directory | Copied | This axis's HPC planning, ledger, prediction, queue, monitoring, and saved commission behavior. |
| Top-level `execution_memory.py`, `execution_guidance.py`, `terminal_execution.py`, `terminal_execution_episodes.py` | Same basenames except `terminal_execution_episode.py` | Copied | Local execution memory and terminal action dependencies used by this axis's HPC binding. |

## Scientific process binding copy (2026-11-11)

| Original symbol | Destination | Axis | Role and caller | Change |
| --- | --- | --- | --- | --- |
| `scientific_process_episodes.py::ScientificProcessEpisodes` | `scientific_process_episode.py::ScientificProcessEpisode` | A102 | Scientific process binding; caller-specific setup and descriptor reopening | Copied into a singular private binding with axis-constrained assignment, local credit, guidance, fact, report and decision routes; generic package dependencies remain outside this axis. |

## Execution binding copy (2026-11-11)

| Original module or symbols | Destination | Change | Role and callers |
| --- | --- | --- | --- |
| `execution_episodes.py::ExecutionEpisodes` | `execution_episode.py::ExecutionEpisode` | Copied and singularized | A102 execution launch, structural result selection, and saved return handling; private binding contains only A102 protein-structure and ordinary launch/result paths. |
| `a101_execution_bindings.py` shared execution hooks | `a102_execution_bindings.py` | Replaced with A102-specific code | Native protein structure binding, job schema, and tool contracts used by the private execution binding. |
| Top-level `native_protein_structure*.py`, `protein_structure*.py` | Same basenames in A102 | Copied | Structural requests, native worker and results, validation, and typed return handling used by A102 execution. |
| Top-level execution, practical, receipt, terminal, and file-capture helpers | Same descriptive basenames in A102; `terminal_execution_episode.py` singular | Copied | A102 execution dependency files. Some copies still call generic host infrastructure. |

## Private terminal execution binding

| Original module or symbol | Destination | Applicable axis | Episode role and caller | Change |
| --- | --- | --- | --- | --- |
| terminal_execution_episodes.py, TerminalExecutionEpisodes | terminal_execution_episode.py, TerminalExecutionEpisode | A102 | Local or HPC launch command execution; this axis's execution episode and practical service factory | Copied and made singular |
| terminal_scientific_evidence.py | terminal_scientific_evidence.py | A102 | Source custody for this axis's applicable native command profiles | Copied and narrowed |
| practical_yield.py | practical_yield.py | A102 | Private command-result progress estimate | Copied |

## A102 execution narrowing (2026-11-11)

The A102 execution episode now rejects resource bindings for other native
operations, constructs only the native protein-structure result readers, and
publishes only its configured launch/results and protein-structure contracts.
Its copied sibling-axis assignment, selector, return, credit and completion
branches were removed. The HPC episode contains no evidence-axis dispatch;
its remaining job ledger identity identifies the originating HPC episode.
No workflow validation was run during this file split.
Its private execution_input_versions.py validates exact A102 input versions
and protected protein-structure references. Received reference resolution,
report validation, fact sources, live facts, and form admission now use A102
protein-structure and generic execution paths. Assignment, catalog, initial
reference, and other copied methods still contain behavior for other axes;
those methods are not counted as finished separation.

## 2026-11-11 monitor binding split

| Original module and symbol | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| episode_monitoring.py: MonitorEpisodes | monitor_episode.py: MonitorEpisode | This axis's monitor binding, commissioned by its execution service | Copied and made axis-private; generic progress infrastructure remains in episode_monitoring.py |

## 2026-11-11 resource binding split

| Original module and symbols | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| resource_episodes.py: ResourceEpisodes | resource_episode.py: ResourceEpisode | This axis's resource launch/results binding | Copied and made axis-private; old plural owner removed |
| resource_records.py, launch_instructions.py | Same basenames under this axis | Resource assignment schemas and selected launch instructions | Copied for private resource binding |

## 2026-11-11 private execution dependency copies

The copied execution operation, record, progress and API adapters still imported A101 implementations. Their referenced modules and local dependencies now have private A102 copies, and imports point directly at those copies. Existing scientific meanings and protocol identifiers are retained. No runtime or import validation was performed. The broad copied helper modules still need later internal narrowing to A102; this change removes their direct sibling-axis dependency.

| Original module | A102 destination | Change | Current role and caller |
| --- | --- | --- | --- |
| `a101/bvbrc_homology_returns.py` | `bvbrc_homology_returns.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_result_views.py` | `blast_result_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_result_publication.py` | `native_blast_standard_database_result_publication.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_acquisition.py` | `native_blast_standard_database_acquisition.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_contracts.py` | `native_blast_standard_database_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_program_context.py` | `blast_program_context.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_metadata.py` | `native_blast_database_metadata.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_fasta_record_identity.py` | `blast_fasta_record_identity.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_population_metadata.py` | `native_blast_database_population_metadata.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_database_population_associations.py` | `blast_database_population_associations.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_metadata.py` | `native_blast_standard_database_metadata.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_pssm_inputs.py` | `blast_pssm_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_pssm_master_inputs.py` | `blast_pssm_master_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_sequence_database.py` | `blast_sequence_database.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_database_grader.py` | `blast_database_grader.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_search.py` | `blast_search.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_pairwise_grader.py` | `blast_pairwise_grader.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_vdb_function_metadata.py` | `native_blast_vdb_function_metadata.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_convergence.py` | `native_blast_database_convergence.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_native_iteration_records.py` | `blast_native_iteration_records.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_iteration_inputs.py` | `blast_iteration_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_result_views.py` | `native_blast_standard_database_result_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_result_worker.py` | `native_blast_standard_database_result_worker.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_report_collection.py` | `blast_report_collection.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_result_worker.py` | `native_blast_database_result_worker.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_vdb_function_calculators.py` | `blast_vdb_function_calculators.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_vdb_function_inputs.py` | `blast_vdb_function_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_result_publication.py` | `native_hmmer_result_publication.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_native_result_views.py` | `hmmer_native_result_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_graders.py` | `hmmer_graders.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_search_inputs.py` | `hmmer_search_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_search_grader.py` | `hmmer_search_grader.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_contracts.py` | `native_hmmer_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_calculators.py` | `native_blast_standard_database_calculators.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_result_publication.py` | `native_blast_database_result_publication.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_acquisition.py` | `native_blast_database_acquisition.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_contracts.py` | `native_blast_database_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_result_views.py` | `native_blast_database_result_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_hsp_views.py` | `native_blast_hsp_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_pairwise_result_views.py` | `blast_pairwise_result_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_contracts.py` | `native_blast_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_pairwise_results.py` | `blast_pairwise_results.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_result_publication.py` | `native_blast_result_publication.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_result_worker.py` | `native_blast_result_worker.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_acquisition.py` | `native_blast_acquisition.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_local.py` | `native_blast_local.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_driver.py` | `native_blast_driver.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_utility_contracts.py` | `native_blast_utility_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_utility_contracts.py` | `blast_utility_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_preparation_contracts.py` | `blast_preparation_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_vdb_utility_contracts.py` | `blast_vdb_utility_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_database_extraction.py` | `blast_database_extraction.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_preparation_population.py` | `blast_preparation_population.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_database_preparation.py` | `blast_database_preparation.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_vdb_utility_context.py` | `native_blast_vdb_utility_context.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_preparation_inputs.py` | `blast_preparation_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_database_inspection.py` | `blast_database_inspection.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_utility_result_worker.py` | `native_blast_utility_result_worker.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_utility_acquisition.py` | `native_blast_utility_acquisition.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_acquisition.py` | `native_hmmer_preparation_acquisition.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_contracts.py` | `native_hmmer_preparation_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_driver.py` | `native_hmmer_preparation_driver.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_preparation_data.py` | `hmmer_alignment_preparation_data.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_model_data.py` | `hmmer_model_data.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_model_binary2.py` | `hmmer_model_binary2.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_model_binary.py` | `hmmer_model_binary.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_model_source_cells.py` | `hmmer_model_source_cells.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_model_legacy.py` | `hmmer_model_legacy.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_input_alphabet.py` | `hmmer_alignment_input_alphabet.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_input_types.py` | `hmmer_alignment_input_types.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_input_fasta.py` | `hmmer_alignment_input_fasta.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_input_blocks.py` | `hmmer_alignment_input_blocks.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_input_phylip.py` | `hmmer_alignment_input_phylip.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_input_validation.py` | `hmmer_alignment_input_validation.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_preparation_calculations.py` | `hmmer_alignment_preparation_calculations.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_model_calculations.py` | `hmmer_model_calculations.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_tree_weights.py` | `hmmer_alignment_tree_weights.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_alignment_pb_sampling.py` | `hmmer_alignment_pb_sampling.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_fm_data.py` | `hmmer_fm_data.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_local.py` | `native_hmmer_preparation_local.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_utility_local.py` | `native_blast_utility_local.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_utility_materializations.py` | `native_blast_utility_materializations.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_result_worker.py` | `native_hmmer_preparation_result_worker.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_worker.py` | `native_hmmer_preparation_worker.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/hmmer_preparation_result_views.py` | `hmmer_preparation_result_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_utility_result_views.py` | `blast_utility_result_views.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_vdb_utility_inputs.py` | `blast_vdb_utility_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_vdb_inputs.py` | `blast_vdb_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_preparation_result_assembly.py` | `blast_preparation_result_assembly.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_vdb_utility_execution.py` | `native_blast_vdb_utility_execution.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_masking_contracts.py` | `native_blast_masking_contracts.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_utility_tool_info.py` | `native_blast_utility_tool_info.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_masking_tool_info.py` | `native_blast_masking_tool_info.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_tool_info.py` | `native_blast_tool_info.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_tool_info.py` | `native_hmmer_tool_info.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_tool_info.py` | `native_hmmer_preparation_tool_info.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_preparation_job_schema.py` | `native_hmmer_preparation_job_schema.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_masking_local.py` | `native_blast_masking_local.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_local.py` | `native_hmmer_local.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_utility_driver.py` | `native_blast_utility_driver.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_database_driver.py` | `native_blast_database_driver.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_masking_driver.py` | `native_blast_masking_driver.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/blast_profile_inputs.py` | `blast_profile_inputs.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_blast_standard_database_driver.py` | `native_blast_standard_database_driver.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_driver.py` | `native_hmmer_driver.py` | Copied | Private dependency of A102 execution/source adapters |
| `a101/native_hmmer_result_worker.py` | `native_hmmer_result_worker.py` | Copied | Private dependency of A102 execution/source adapters |

Direct imports updated in `api_service_execution.py`, `execution_progress.py`, `literature_experimental_contracts.py`, `practical_execution_operations.py`, `practical_execution_records.py`, `native_blast_database_result_publication.py`, `native_blast_standard_database_result_publication.py`.

Worker launch module paths and named metadata parsers now also resolve within A102. Additional private copies:

| Original module | A102 destination | Change | Role and caller |
| --- | --- | --- | --- |
| `a101/native_blast_utility_results.py` | `native_blast_utility_results.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_utility_result_publication.py` | `native_blast_utility_result_publication.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_utility_capture_failure.py` | `native_blast_utility_capture_failure.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_masking_results.py` | `native_blast_masking_results.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_masking_acquisition.py` | `native_blast_masking_acquisition.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_masking_result_publication.py` | `native_blast_masking_result_publication.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_masking_result_worker.py` | `native_blast_masking_result_worker.py` | Copied | A102 private worker/parser dependency |
| `a101/blast_maskinfo_inputs.py` | `blast_maskinfo_inputs.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_standard_database_results.py` | `native_blast_standard_database_results.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_database_results.py` | `native_blast_database_results.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_database_returns.py` | `native_blast_database_returns.py` | Copied | A102 private worker/parser dependency |
| `a101/native_blast_results.py` | `native_blast_results.py` | Copied | A102 private worker/parser dependency |
| `a101/native_hmmer_results.py` | `native_hmmer_results.py` | Copied | A102 private worker/parser dependency |
| `a101/native_hmmer_acquisition.py` | `native_hmmer_acquisition.py` | Copied | A102 private worker/parser dependency |
| `a101/native_hmmer_preparation_results.py` | `native_hmmer_preparation_results.py` | Copied | A102 private worker/parser dependency |
| `a101/native_hmmer_preparation_result_publication.py` | `native_hmmer_preparation_result_publication.py` | Copied | A102 private worker/parser dependency |
| `a101/native_hmmer_preparation_failure_views.py` | `native_hmmer_preparation_failure_views.py` | Copied | A102 private worker/parser dependency |

## 2026-11-11 private practical execution narrowing

| Original mixed symbols | A102 destination | Role and caller | Change |
| --- | --- | --- | --- |
| Practical requested-job schema, assignment validation, receipt and completion validation | `practical_execution_records.py` | A102 structure launch/results and ordinary command records | Narrowed to protein-structure requests and generic commands; removed foreign native schemas, BLAST utility receipt logic, and FBA/MACS2/LUMPY role-path contracts |
| Local practical preparation, launch, retry, observation, output reads and action execution | `practical_execution_operations.py` | A102 structure and generic local execution | Retained A102 protein plan/identity checks, original native lifecycle and generic preparation; removed copied homology, RNA/Infernal, expression, genomic, chromatin, assay and FBA dispatch |
| Generic retained-file capture plus MACS2/LUMPY selectors | `local_file_capture_results.py` | A102 generic exact-file result capture | Kept generic capture and receipt behavior; removed foreign selector constants, resolvers and receipt branches and their deleted record imports |

No Python execution, parse/import validation or tests were run in this pass.
The extracted practical lifecycle remains unvalidated. Broader private API,
progress and terminal helper modules and generic root infrastructure still need
scope review; this entry claims only the three files listed above.

### Private native correspondence dependencies (2026-11-11)

| Original implementation | Private destination | Applicable role and callers | Change |
|---|---|---|---|
| `alignment_correspondence.py` | `a102/alignment_correspondence.py` | A102 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `biopython_pairwise_grader.py` | `a102/biopython_pairwise_grader.py` | A102 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `tool_grading_artifacts.py` | `a102/tool_grading_artifacts.py` | A102 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `blast_pairwise_grader.py` | `a102/blast_pairwise_grader.py` | A102 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `sequence_attribution.py` | `a102/sequence_attribution.py` | A102 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `a101/a101_scoring.py` | `a102/native_correspondence_scoring.py` | A102 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |

Updated direct imports in `a102_attachments.py`, `a102_publication.py`, `blast_database_grader.py`, `blast_pairwise_grader.py`, `blast_pairwise_results.py`, `blast_result_views.py`, `blast_sequence_database.py`, `blast_vdb_function_inputs.py`, `native_blast_database_result_publication.py`, `native_blast_hsp_views.py`, `native_blast_masking_result_publication.py`, `native_blast_result_publication.py`, `native_blast_result_worker.py`, `native_blast_standard_database_calculators.py`, `native_blast_standard_database_result_publication.py`, `native_blast_utility_result_publication.py`, `native_hmmer_preparation_result_publication.py`, `native_hmmer_result_publication.py`, `native_protein_structure_worker.py`, `protein_structure_contracts.py`, `protein_structure_correspondence.py`, `protein_structure_operands.py`. BLAST program units are private constants when only the grader needs them. Existing native sheet formats and scoring equations are preserved. No Python, tests or static validation run.

Native correspondence scoring was narrowed to `hmmer_comparisons`, `blast_comparisons`, `route_native_grading`, their private exception/require helper and `SCALES`. Copied A101 sheet aggregation, coverage and credit-facing compilation were removed; only applicable mapping readers remain.

### Private A102 monitoring information (2026-11-11)

| Original implementation | Destination | Role/caller | Change |
|---|---|---|---|
| `episode_progress_credit.py` | `a102/episode_progress_credit.py` | A102ServiceFactory received monitoring credit | Copied original projection and private progress validators. |
| `progress_records.py`, literal historical homology status shape | `a102/progress_records.py` | A102 resource/monitor saved progress | Copied status/receipt schema and validators without A101 job implementation import. |

Direct imports updated in `a102_investigation.py`, `a102_resources.py`, `monitor_episode.py`. Scientific earned-credit rules are unchanged; no tests or execution validation run.

### Private A102 tool registry and source binding (2026-11-11)

The A102 registry imports its own `tools.ToolRegistry`; it no longer inherits root `tools.ToolRegistry`. The source/sequence/homology publication mechanics were independently copied, with A102 structural hooks restored from the original dispatcher. Applicable structural configuration, prepared native work, saved-work replay, numerical publication, partial/unavailable outcomes and AlphaFold/RCSB/EMDB receipts remain distinct. No foreign flux, expression, assay-instrument, variant, regulation or RNA execution dispatch was copied.

| Original module/symbol | Private destination | A102 role/caller | Change |
|---|---|---|---|
| `tools.ToolRegistry`, source publication helpers and sequence worker record | `a102/tools.py` | Base for `A102ToolRegistry`; source/sequence/native structure operations | Split/copy of applicable methods; direct local structural hooks. |
| `acquisition.PublicClients`, `SourceSnapshot`, source parsers | `a102/acquisition.py` | Private provider calls and source bytes | Copied applicable clients plus original AlphaFold/RCSB/EMDB methods; worker observation import points to A102. |
| `molecular_measurement_tools.authenticate_itc_invocation`, unfinished action exception | `a102/structure_invocation.py` | Existing structural invocation, native unfinished action and source file authorization | Extracted private `authenticate_structure_invocation` and `StructureOperationUnpublished`; no assay implementation dependency. |

Additional independently copied direct source/native helper modules: `provider_jobs.py`, `api_error_feedback.py`, `sequence_ops.py`, `sequence_mapping.py`, `sequence_views.py`, `library_targets.py`, `materials_packing.py`, `read_mapping.py`, `source_locations.py`, `document_tools.py`, `spreadsheet_tools.py`, `spreadsheet_worker.py`, `literature_assets.py`, `image_evidence.py`, `literature_sequence_discovery.py`, `source_sequences.py`, `ncbi_entrez_tools.py`, `ncbi_entrez_acquisition.py`, `experimental_database_acquisition.py`, `experimental_database_records.py`, `alignment_site_native.py`, `alignment_site_inputs.py`, `alignment_site_calculators.py`, `sequence_composition_grader.py`, `sequence_composition_counts.py`, `sequence_extraction_grader.py`, `sequence_translation_grader.py`, `minimap2_grader.py`, `minimap2_grading_inputs.py`, `api_uniprot.py`, `uniprot_native.py`, `uniprot_native_contracts.py`, `uniprot_publication.py`, `public_configuration.py`, `sequence_worker.py`, `uniprot_service_support.py`, `native_json.py`, `native_timing_information.py`, `rcsb_acquisition.py`, `emdb_acquisition.py`, `alphafold_acquisition.py`, `alphafold_acquisition_host.py`, `data_acquisition_receipts.py`. Existing private structural and grading files were retained rather than overwritten. A102 worker module strings now resolve inside A102. The outer registry's two assignment-axis guards were removed; private directory/import binding supplies the scope. Its descriptor now records its own resource binding (the original root base provided no `as_record` implementation).

Remaining integration/dependencies: original Store/material parsing/storage and domain/communication/receipt types, resource/job execution and timing infrastructure still supply generic runtime mechanics. Root `AcquisitionError` is retained as the existing exception type used by local job infrastructure. Common workflow services, generic constructors and combined composition remain separate unresolved work. This edit does not claim a runnable combined workflow or native execution. No Python, tests, parse/import validation or HPC jobs were run.

Source-version handling is narrowed to the enabled A102 structural/NCBI providers; dormant STRING/chemical/context/variant-provider lists were removed from the private registry. AlphaFold file replay retains the original received-advertisement authentication, and structured acquisition failures retain the original provider-specific receipts.

## Private workflow service split — 2026-11-11

`ToolRegistry.workflow_services` constructs the A102-local `WorkflowServices`. This class directly retains source/tool dispatch, source-byte grants, original input receipts, progress, scientific credit and original result/provenance paths. It binds structural sequence alignment authentication, original result custody, received references and action facts to A102's existing private structural modules; it does not inherit from or forward to root WorkflowServices. Unrelated assay, variant, restriction-mapping and MACS service/report branches were removed. Structural received context and structural/investigation report validation remain connected. Alignment-site action records and returns are private copies.

Scientific provenance, records, reports, support metadata, resource tool information and received source/file readers now have private copies. Preparation reads use explicit current-invocation and parent-invocation methods, with explicit readers and expected paths at revision validation callsites. No ownership selector remains in those ports. Received input frame helpers contain only original selection/form readers; stable file-byte reads have no flux dependency.

Remaining root dependencies are runtime construction and projector/progress/native-event ports; Store/domain/communication and episode receipt/return infrastructure; original saved-frame transport decoding in runtime; native-file capture, source material windows and scientific library/tool schema infrastructure. Their remaining separation is not claimed complete here. Runtime wiring is handled separately. No tests, Python execution or static validation were run for this split.

A102 also has private scientific/tool library construction, evidence-entry contracts, tool information and schema validation. Its tool library uses the actual supplied callable/resource catalogs and does not inject the global all-service catalog. Tool-information knowledge and launch manifests contain only entries matching A102's declared operations, with their referenced markdown copied locally. Execution recipe assets are local. A102 investigation and structural-workflow constructors import these private library classes.

2026-11-11 runtime binding: this axis's tools.workflow_services now supplies its private service to runtime. Provenance, current tool invocation, instruction libraries, tool retrieval and semantic receipts are constructed through that service. Original runtime investigation/action-delivery and decision-exchange instructions are independent runtime_prompt.py/decision_protocol_prompt.py copies. Original tool_knowledge.py, launch_instructions.py, scientific_tool_retrieval.py, boundary_validation.py and episode_receipts.py have private implementations and direct callers. Imports of already-present local helpers were rebound directly. Root message parsing, Store/domain/communication, numerical/execution infrastructure and remaining helper dependencies are still open; no execution validation is claimed.

### Private A102 message, form and domain contracts (2026-11-11)

| Original behavior | Private destination | Retained A102 behavior |
|---|---|---|
| Closed typed forms, fact filling and generation | `communication.py` | Private grammar, finite values, detached payloads, exact registered protein-action and native protein-structure schemas, local-file capture schema, structural row validators, local definition resolution and reference semantics. Alignment-site and literature structure returns retain their original generic form and private binding validation paths. |
| Synchronous authenticated-value frame | `form_reference_validation.py` | Exact frame lifetime, immutable context key and detached values; no new custody grants or durable cache. |
| Frozen contract information and registered fact expansion | `episode_contract_information.py` | Original actual supplied catalogs/fact maps, schema fingerprints, closed form expansion and saved declarations. Removes foreign restriction/selected-UniProt special selectors and A105-specific native-literal bypass. |
| Schema text and traversal | `schema_information_text.py`, `schema_support.py` | Independent original schema rendering/parsing and traversal; binds the existing private boundary_validation helper. |
| Domain schemas, identities and parsing | `domain.py` | Exact original contract definitions, canonical serialization, identities, exceptions, sequence parsing and validation are copied privately. |

A102 production imports, including nested library callers, now bind these implementations. Structural/action/native meanings, frozen records, original action identities and existing custody are retained. The parser contains no foreign assay/intervention/restriction/NMF/FBA or other-axis scientific return dispatch. No score, scientific meaning, grading behavior or new enforcement was introduced.

No runtime.py was copied or edited in this scope. Root handles runtime parsing and exception routing using these independent private ContractError and ReportBoundaryError classes. Store/resource interfaces and BindingContext remain broader dependencies until their own integration is complete. No tests, Python, static validation or workflow jobs were run.

### Private A102 workflow runtime and admission (2026-11-11)

| Original implementation | Private destination | Retained A102 behavior |
|---|---|---|
| Workflow and decision-source implementation | `runtime.py` | Independent full implementation, directly bound to A102's service constructors, private parser/domain, BindingContext, journal and admission classes. Preserves original actions, returned outcomes, credit/controller entry, structural tool invocation and source/model/sequence attribution. No shared-runtime inheritance or forwarding. |
| Binding, service and composition records | `episode_bindings.py`, `episode_application_services.py`, `episode_composition.py`, `composition_information.py` | Local immutable context identities, original role bindings/descriptors, actual contract information and scientific construction. The unused A101 HomologyResourceAdapter import is removed. |
| Original return admission and journal | `episode_admission.py`, `episode_journal.py`, `journal_metadata.py`, `episode_source_failure.py`, `episode_completion.py`, `episode_commissions.py`, `episode_report_acquisition.py`, `local_return_history.py`, `pending_assignment.py` | Original typed forms, saved admissions, invocation identities, closed records, completion observations, commission receipts, restored histories and source-failure semantics. |
| Decision parsing and history | `decision_context.py`, `decision_exchanges.py`, `decision_history.py` | Private original model snapshots, action/lookup normalization, exchange history and decision-category observations. Removed unrelated Infernal receiver expansion. |
| Structural typed-report boundary | `protein_structure_report_boundary.py` | Preserves exact authenticated protein fields and internal custody identities after original form/semantic validation. Structural/model/sequence received attribution remains in runtime and the existing private services. |
| Default/restored finding credit | `default_scientific_binding.py`, `investigation_progress.py`, `scientific_findings.py`, `finding_validity.py` | Private original manifest restoration and finding identity/revision/credit behavior; no new default score or scientific rule. |
| Existing A102 sheet delivery | `literature_sheet_updates.py` | Runtime grading delivery reads this private structural-sheet implementation directly. |

A102 production Workflow, Record, exception and BindingContext imports are rebound locally, including nested library callers. Foreign restriction identifiers, A110 reaction repair, HMMER-preparation/MinHash/Addgene receipt branches and root sheet imports are removed. Existing protein structural report admission and native custody remain unchanged. The old A101-specific job binding type check is removed; the existing explicit controller/task-credit requirements remain.

Unfinished infrastructure imports are explicit relative imports to package-root timing, execution expectations, resource estimation, run statistics, wait estimation, provider/model transport, numerical controllers, Store, native event transport/recovery, and application execution setup where A102 has no private implementation yet. Their dependency closure is not claimed complete. External constructors that still manufacture root context/error types remain integration work; A102's own parser, runtime, journal, admission and production binding callers now agree on their local types. No root runtime or other axis was edited. No tests, Python, static validation or workflow jobs were run.

## 2026-11-11: private A102 Store, material intake and geometry

A102 now directly uses independent `state.py`, `materials.py`,
`material_parsing.py`, `material_gzip.py`, `genbank_intake.py` and
`context_masks.py`. Its application imports and commission Store constructor
bind locally. Existing private journal metadata, domain/errors, findings,
sequence mapping, library targets and material packing remain the actual
implementations. Original transactions, artifacts, source members, context
allocation, record validation, revision conflicts and input identities are
preserved.

The existing private `library/evidence_geometry.py` now also contains the
original Store assessment and observation extent helpers. Structural-match
semantics remain alongside exact native alignment/mapping, operand intervals,
bounded measurements and library-member dimensions. BLAST database observation
validators use A102's private implementations. Native measurement decoding is
copied into `native_measurement.py`; its existing ExecutionClass/RunStatistic
value types remain unchanged infrastructure dependencies. Structure input
access, native publication custody and receipt authority continue through the
existing A102 private structure services. Foreign Enrichr and unrelated
molecular-capture artifact dispatch was not copied into material access.

The Store API and private runtime/literature call sites now use
`account_invocation`, preserving the original run/episode tuple. The original
hash payload labels `owner` and `account_owner` remain only where required to
keep interpretation-account keys and reasoning signatures unchanged. They do
not select an axis. Attribution helper names and account-binding locals no
longer use owner names. No new factory, schema, score or enforcement was added.

This is dependency-placement work, not workflow validation. Existing numerical,
execution timing/statistics and machine-execution dependencies remain separate
work. No tests, static checks, Python, workflow or job execution were run.

## 2026-11-11: private A102 numerical and native-statistics implementation

A102 now has independent numerical estimation/controller, execution timing,
run-statistics and vendor source/license implementations. Original formulas,
source revision/hash, numerical parameters, measured-time operands and native
receipt identities remain unchanged. Runtime, journal, calculators and native
callers bind directly to matching local types.

Private execution recording, ordinary execution statistics, expectation
capture, resource estimation and native lifecycle implementations complete the
matching NativeStatistics/NativeMeasurement/ExecutionClass/RunStatistic path.
The temporary separate native-measurement decoder was removed; Store and native
callers use the same private recorder class. Existing A102 execution memory is
used directly. The original structural/native receipt, alignment, spreadsheet
and source-reading behavior remains. Original runtime journal, commissions and
application services already bind privately; commissions construct local Store.

Foreign HomologyStatistics and assigned-homology expectation construction,
lookup and prospective-planning dispatch were excluded. Actual A102 per-role
execution classes still capture their original expectation snapshots. The
historical serialized expectation field `homology: null` remains for unchanged
records; it carries no handler, selector or cross-axis implementation. Existing
phase-name literals in native data contracts remain historical data identities.

Machine job/resource primitives, atomic JSON writing, native-event transport,
providers and remaining waiting/planning/shared-information dependencies are
still explicit infrastructure integration work. Execution timing keeps its
original persisted process-liveness fields pending coordinated renaming; this
introduces no axis ownership. No tests, static checks, Python, workflow or job
execution were run. This records file/dependency separation, not validation.


2026-11-11: `method_loop/` and its license/source manifests were independently copied to `a102/library/method_loop/`. A102 runtime, frame, numerical and evidence helpers import this private episode/record/controller protocol implementation directly. Its durable worker command names the private module; the repository root for subprocess imports was adjusted for placement. Original iterator, commission/return records and continuation behavior are unchanged. No execution validation was run.

2026-11-11 acquisition class placement correction: the earlier local `acquisition.py` self-import was replaced with its independent original `AcquisitionError` class, preserving the original fields and RuntimeError base. No execution validation was run.

## 2026-11-11: private A102 waiting, frames and completion implementation

Waiting, wait-estimation inputs, local return history, completion evidence,
in-process waiting/replay, episode monitoring, input-version pinning and return
record readers now have independent A102 implementations. Existing input frames,
services and runtime import the local readers directly. The return reader keeps
A102's original structural prepared-assignment validation, source/file receipts
and immutable admitted-return relationships. Foreign homology prepared-job
handling was excluded.

Progress records, both existing private monitoring entrypoints and progress
credit retain actual structural resource/episode statuses and their native
measurements, outputs, logs and completion relationships. The unused homology
job schema and its progress-credit branch were removed. A102 exposes no actual
producer for the legacy NativeEventInformation channel, so its constructor,
configuration, wait/report/reference/fact routes and service resolver branch
were removed. Actual resource and native execution receipt handling remains.

A102's independent `library/method_loop/` includes the original license and
source/patch manifests. Production imports use matching private episode,
protocol, identity, archival and durable-error types. Its worker command names
the A102 module and locates repository-root imports directly. Original iterator,
continuation and commission/return behavior remains unchanged.

No tests, static checks, Python, workflow or job execution were run. This is
file/dependency separation; remaining provider/presentation, machine execution
and outer reconstruction integration work is separately tracked.

## 2026-11-11: private A102 provider and structural presentation

Provider transport/authentication, scientific and receiver prompts, selected
execution, ordinary API launch, HPC and monitor presentation now have independent
A102 implementations and direct production callers. Applicable model/controller/
progress/restoration defaults are local copies of the original settings. The
provider retains the original frame reconstruction and renderer ordering for
A102's actual scientific, API, HPC, selected native execution and monitoring
contexts. Foreign RNA, NMF, chemical, assay, gene-context and phylogeny renderer
dispatch was excluded.

Original structural/model/geometry values and native execution task operands
continue through their existing supplied-value presentation. Alignment reports
retain their original projection and canonical reference decoding; the exact
required alignment codecs were copied into private presentation helpers without
importing mixed API schema/adapter registries. These codecs only render already
admitted fields and confer no new access or scientific interpretation.

Completed-work and shared-information result presentation now call the original
private `a102_work_report` adapter directly. Original structural comparison,
functional/geometry and conditional experimental-structure quantities,
qualifications, selected sheet versions and delivered child-local progress are
preserved, separately from the original parent's earned credit. Existing A111
structural-result schema labels remain data identities understood by that A102
adapter; they do not introduce another episode or shared registry. Historical
A102 investigation/structural report forms retain their exact original projection.
Other axes' adapter selection and scoring-view lists were removed.

No new scorer, source reader, evidence filter or task-selection architecture was
added. Remaining machine-execution and outer reconstruction dependencies are
separate work. No tests, static checks, Python, workflow or job execution were
run; this records implementation separation rather than validation.

### 2026-11-11 — A102 private construction and execution prerequisites

Application binding/reconstruction, public/tool configuration, input versions, scientific setup, finding progress/validity, reports, HPC receipts/commission helpers and the local resource/native-worker dependencies now have direct A102 copies. Tool reconstruction uses the actual `A102ToolRegistry`; the direct private service factory configures its protein-structure resources and preserves explicit execution/HPC operands. AlphaFold, RCSB and EMDB source implementations remain in the private tool registry. Historical cross-episode compatibility hash aliases were removed from composition; explicit unresolved private reopening errors remain. No new reopening bridge, tests, Python or static validation. Further API/selected-result custody splitting is continuing separately below.

### 2026-11-11 — A102 private API and structural result custody

Original selected API effects/calls, AppService contracts/schema assets, receipt/source/frame custody, monitoring and publication helpers are now private. The A102 AppService registry contains homology, MSA and MetaCATS implementations only; its original source service implementations retain UniProt, BV-BRC data/MinHash and BLAST/HMMER support. Foreign Enrichr/Rfam/sequence-support and phylogeny/genome/proteome/comparative/FASTQ/application adapter dispatch was removed. Native execution progress retains actual protein-structure and generic local/PBS operations.

A102 now owns the original HMMalign/NHMMER and masking helpers used by its retained alignment code. Generic finite-record/file/source/interpreter helpers were extracted as `native_record_identity.py`, `native_worker_files.py` and `native_driver_runtime.py`; importing an Infernal or ATAC executor is no longer needed for these helper calls. Immutable local-file result controls are in `file_capture_receipt_control.py`; FBA/MACS/LUMPY receipt materialization branches were removed. Original source identities, scientific calculations and iterator semantics remain; this is not a validation claim. No Python, tests or static validation were run.

Adapter implementation hashes read A102 files only; root-file fallback was removed. Runtime and reconstruction controller descriptors now both name the private numerical implementation. Active AppService methods/variables use invocation terminology. Historical frozen `original_job_owner`/`OriginalJobOwner` schema keys, effect-ledger `owner.json` paths and hashed `owner` labels retain the original receipt identity; none select an axis or binding. Their migration is separate from this file split.

No-op preparation/foreign API bindings and passthrough launch-schema wrappers were removed; the remaining execution adapter contains the actual native protein-structure resource validation/catalog only.

2026-11-11 numerical-source retirement: this axis's numerical provenance names
its own private vendor source and MIT license. Its private numerical/timing
implementations and source manifest retain the original estimator, receipt-time
semantics and formulas. Former shared numerical/timing implementation paths were
retired; no tests or execution were run.

## 2026-11-11: retired original A102 structure and alignment-provider modules

Retired the following former top-level implementations after reading A102's
actual acquisition/tool, native execution/return and AppService adapter callers.
They bind directly to the independent A102 files. No other private axis imports
the removed implementations. Generic AppService/APIService editing sources and
the multi-destination native capture helper were left outside this retirement.

| Original | Private destination | Applicable role retained |
| --- | --- | --- |
| `gene_annotation_episode/alphafold_acquisition.py` | `gene_annotation_episode/episodic_workflow/root/a102/alphafold_acquisition.py` | Prediction/download association, acquisition and retained file custody |
| `gene_annotation_episode/alphafold_acquisition_host.py` | `gene_annotation_episode/episodic_workflow/root/a102/alphafold_acquisition_host.py` | Prediction/download association, acquisition and retained file custody |
| `gene_annotation_episode/bvbrc_alignment_associations.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_alignment_associations.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_alignment_bundle_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_alignment_bundle_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_alignment_bundle_projection.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_alignment_bundle_projection.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_alignment_bundle_resolution.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_alignment_bundle_resolution.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_alignment_provider_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_alignment_provider_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_alignment_returns.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_alignment_returns.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_alignment_values.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_alignment_values.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_contingency_math.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_contingency_math.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_adequacy.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_adequacy.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_association_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_association_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_associations.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_associations.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_biological_calculators.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_biological_calculators.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_biological_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_biological_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_bundle_adapter.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_bundle_adapter.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_calculation_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_calculation_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_calculators.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_calculators.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_format_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_format_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_formats.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_formats.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_grader.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_grader.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_input_formats.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_input_formats.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_inputs.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_inputs.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_metacats_provider_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_metacats_provider_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_bundle_adapter.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_bundle_adapter.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_calculation_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_calculation_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_calculators.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_calculators.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_format_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_format_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_formats.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_formats.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_grader.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_grader.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_inputs.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_inputs.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_provider_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_provider_contracts.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/bvbrc_msa_xmfa_inputs.py` | `gene_annotation_episode/episodic_workflow/root/a102/bvbrc_msa_xmfa_inputs.py` | Private MSA/MetaCATS alignment provider, selected saved facts and original grading |
| `gene_annotation_episode/emdb_acquisition.py` | `gene_annotation_episode/episodic_workflow/root/a102/emdb_acquisition.py` | Structural source acquisition and original HTTP receipt records |
| `gene_annotation_episode/native_protein_structure_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_contracts.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/native_protein_structure_driver.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_driver.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/native_protein_structure_local.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_local.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/native_protein_structure_preparation.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_preparation.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/native_protein_structure_results.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_results.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/native_protein_structure_returns.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_returns.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/native_protein_structure_tool_info.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_tool_info.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/native_protein_structure_worker.py` | `gene_annotation_episode/episodic_workflow/root/a102/native_protein_structure_worker.py` | Private structure worker, local launch, capture, qualification and requested return |
| `gene_annotation_episode/protein_structure_action_records.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_action_records.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_authority.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_authority.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_calculations.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_calculations.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_contracts.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_correspondence.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_correspondence.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_execution_information.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_execution_information.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_formats.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_formats.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_metadata.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_metadata.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_operands.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_operands.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_projection_publication.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_projection_publication.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_publication.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_publication.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_report_boundary.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_report_boundary.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_result_receipts.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_result_receipts.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_result_views.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_result_views.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_result_worker.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_result_worker.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_selection.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_selection.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_sequences.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_sequences.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_sheet.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_sheet.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/protein_structure_tools.py` | `gene_annotation_episode/episodic_workflow/root/a102/protein_structure_tools.py` | Structure identity, selected coordinates, calculations, saved sheets, publication and receipts |
| `gene_annotation_episode/rcsb_acquisition.py` | `gene_annotation_episode/episodic_workflow/root/a102/rcsb_acquisition.py` | Structural source acquisition and original HTTP receipt records |
| `gene_annotation_episode/xmfa_calculation_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/xmfa_calculation_contracts.py` | Original XMFA source, coordinate, format and alignment quantity semantics |
| `gene_annotation_episode/xmfa_calculators.py` | `gene_annotation_episode/episodic_workflow/root/a102/xmfa_calculators.py` | Original XMFA source, coordinate, format and alignment quantity semantics |
| `gene_annotation_episode/xmfa_coordinates.py` | `gene_annotation_episode/episodic_workflow/root/a102/xmfa_coordinates.py` | Original XMFA source, coordinate, format and alignment quantity semantics |
| `gene_annotation_episode/xmfa_format_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/xmfa_format_contracts.py` | Original XMFA source, coordinate, format and alignment quantity semantics |
| `gene_annotation_episode/xmfa_formats.py` | `gene_annotation_episode/episodic_workflow/root/a102/xmfa_formats.py` | Original XMFA source, coordinate, format and alignment quantity semantics |
| `gene_annotation_episode/xmfa_source_contracts.py` | `gene_annotation_episode/episodic_workflow/root/a102/xmfa_source_contracts.py` | Original XMFA source, coordinate, format and alignment quantity semantics |
| `gene_annotation_episode/xmfa_sources.py` | `gene_annotation_episode/episodic_workflow/root/a102/xmfa_sources.py` | Original XMFA source, coordinate, format and alignment quantity semantics |

A102 native structure driver/worker constants, typed module identities, required
grader module names, result-worker launch and execution-information descriptions
now identify A102's own modules. Copied worker package roots resolve the actual
repository module root rather than the old file depth. Original structural
quantities, residue/correspondence identities, selected fit/evaluation semantics,
source custody, saved grading and failure/partial-output handling are retained.
The worker descriptors identify private code; old top-level descriptors are not
silently redirected through a compatibility wrapper. Required private schema
and application assets, source provenance and licenses were preserved; no data
assets were removed. Historical combined callers/examples/tests require their
later private entry-point migration.

No tests, static check suite, Python commands, workflows or jobs were run.

2026-11-11: native BLAST implementation inventories and the separate publication subprocess now load only this axis's qualified private modules, including its own `domain` and alignment correspondence helpers. Removed the old name-prefix switch that selected top-level helpers. The embedded subprocess uses an absolute private worker import; native byte/scoring logic is unchanged.

2026-11-11 API-original retirement: original mixed API/AppService behavioral
modules were removed after private callers were bound. Applicable private
publication predicates and parser-module descriptions were narrowed, with exact
original custody and outcome semantics retained. A102 additionally retains its
previously missing declared application assets. Full original-to-private mapping
is recorded in root/ownership.md. No tests or execution were run.

## 2026-11-11 — Additional original-module placements

This supplement records original modules not named individually above. It maps their complete applicable module contents, including methods and constants; previous symbol-specific narrowing notes remain authoritative. Callers listed here are direct private imports or qualified worker module references, not execution receipts. It does not claim runtime validation.

| Original module/symbols | Destination | Current role/caller | Change |
|---|---|---|---|
| `gene_annotation_episode/_local_job_worker.py` (module contents) | `a102/_local_job_worker.py` | Private dependency used by `execution_recording.py`, `local_jobs.py`, `native_blast_driver.py`, `native_events.py`, `native_hmmer_driver.py`, `native_lifecycle.py`, `native_worker_files.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_experimental_evidence.py` (module contents) | `a102/a102_experimental_evidence.py` | Private dependency used by `a102_structural_report.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_hpc.py` (module contents) | `a102/a102_hpc.py` | Private dependency used by `a102_structural_report.py`, `a102_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_hpc_worker.py` (module contents) | `a102/a102_hpc_worker.py` | Private dependency used by `a102_hpc.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_native_setup.py` (module contents) | `a102/a102_native_setup.py` | Private dependency used by `a102_hpc.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_native_worker.py` (module contents) | `a102/a102_native_worker.py` | Private dependency used by `a102_hpc.py`, `a102_hpc_worker.py`, `a102_structural_bridge.py`, `a102_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_scoring.py` (module contents) | `a102/a102_scoring.py` | Private dependency used by `a102_attachments.py`, `a102_credit.py`, `a102_hpc.py`, `a102_native_worker.py`, `a102_publication.py`, `a102_resources.py`, `a102_structural_bridge.py`, `a102_structures.py`, `a102_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_structural_bridge.py` (module contents) | `a102/a102_structural_bridge.py` | Private dependency used by `a102_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_structural_evidence.py` (module contents) | `a102/a102_structural_evidence.py` | Private dependency used by `a102_experimental_evidence.py`, `a102_scientific_process_binding.py`, `a102_scientific_report_validation.py`, `a102_structural_report.py`, `a102_structural_workflow.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_structural_report.py` (module contents) | `a102/a102_structural_report.py` | Private dependency used by `a102_scientific_process_binding.py`, `a102_scientific_report_validation.py`, `a102_structural_workflow.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_structural_workflow.py` (module contents) | `a102/a102_structural_workflow.py` | Retained original public factory `create_a102_structural_evidence_workflow`, with its `A102StructuralEvidenceServiceFactory` and `A102StructuralEvidenceSubtree`; no current repository production caller invokes this factory. Existing factory/class relationships remain intact; no new integration was added. | Copied/split; private implementation |
| `gene_annotation_episode/a102_structures.py` (module contents) | `a102/a102_structures.py` | Private dependency used by `a102_attachments.py`, `a102_hpc.py`, `a102_native_worker.py`, `a102_structural_bridge.py`, `a102_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a102_work_report.py` (module contents) | `a102/a102_work_report.py` | Private dependency used by `episode_work_report.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_result_presentation.py` (module contents) | `a102/alignment_result_presentation.py` | Private dependency used by `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_action_records.py` (module contents) | `a102/alignment_site_action_records.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_mapping.py` (module contents) | `a102/alignment_site_mapping.py` | Private dependency used by `alignment_site_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_returns.py` (module contents) | `a102/alignment_site_returns.py` | Private dependency used by `alignment_site_action_records.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_blast.py` (module contents) | `a102/api_blast.py` | Private dependency used by `api_service_execution.py`, `api_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_bvbrc.py` (module contents) | `a102/api_bvbrc.py` | Private dependency used by `api_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_bvbrc_appservice.py` (module contents) | `a102/api_bvbrc_appservice.py` | Private dependency used by `api_services.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_bvbrc_minhash.py` (module contents) | `a102/api_bvbrc_minhash.py` | Private dependency used by `api_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_execution.py` (module contents) | `a102/api_execution.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_selected_call.py` (module contents) | `a102/api_selected_call.py` | Private dependency used by `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_selected_effects.py` (module contents) | `a102/api_selected_effects.py` | Private dependency used by `api_service_execution.py`, `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_services.py` (module contents) | `a102/api_services.py` | Private dependency used by `api_blast.py`, `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py`, `api_service_execution.py`, `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/application_execution_binding.py` (module contents) | `a102/application_execution_binding.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/blast_grading_inputs.py` (module contents) | `a102/blast_grading_inputs.py` | Private dependency used by `blast_report_collection.py`, `blast_sequence_database.py`, `bvbrc_homology_inputs.py`, `native_blast_hsp_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_analysis_protocol.py` (module contents) | `a102/bvbrc_analysis_protocol.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py`, `bvbrc_analysis_transport.py`, `bvbrc_application_definitions.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_readers.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_minhash_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_analysis_transport.py` (module contents) | `a102/bvbrc_analysis_transport.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_application_definitions.py` (module contents) | `a102/bvbrc_application_definitions.py` | Private dependency used by `api_bvbrc_appservice.py`, `bvbrc_appservice_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_adapters.py` (module contents) | `a102/bvbrc_appservice_adapters.py` | Private dependency used by `api_bvbrc_appservice.py`, `bvbrc_appservice_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_bundle_values.py` (module contents) | `a102/bvbrc_appservice_bundle_values.py` | Private dependency used by `bvbrc_appservice_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_contracts.py` (module contents) | `a102/bvbrc_appservice_contracts.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_selected_call.py`, `api_selected_effects.py`, `api_services.py`, `bvbrc_alignment_bundle_contracts.py`, `bvbrc_alignment_bundle_resolution.py`, `bvbrc_alignment_provider_contracts.py`, `bvbrc_alignment_returns.py`, `bvbrc_appservice_bundle_values.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_monitor.py`, `bvbrc_appservice_publication.py`, `bvbrc_appservice_readers.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_appservice_records.py`, `bvbrc_appservice_tool_info.py`, `bvbrc_homology_bundle_adapter.py`, `bvbrc_homology_returns.py`, `bvbrc_msa_xmfa_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_custody.py` (module contents) | `a102/bvbrc_appservice_custody.py` | Private dependency used by `bvbrc_alignment_returns.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_monitor.py`, `bvbrc_homology_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_host.py` (module contents) | `a102/bvbrc_appservice_host.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_inputs.py` (module contents) | `a102/bvbrc_appservice_inputs.py` | Private dependency used by `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_monitor.py` (module contents) | `a102/bvbrc_appservice_monitor.py` | Private dependency used by `api_service_execution.py`, `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_publication.py` (module contents) | `a102/bvbrc_appservice_publication.py` | Private dependency used by `bvbrc_alignment_returns.py`, `bvbrc_appservice_host.py`, `bvbrc_homology_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_readers.py` (module contents) | `a102/bvbrc_appservice_readers.py` | Private dependency used by `api_bvbrc_appservice.py`, `bvbrc_appservice_bundle_values.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_appservice_records.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_receipt_values.py` (module contents) | `a102/bvbrc_appservice_receipt_values.py` | Private dependency used by `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_records.py` (module contents) | `a102/bvbrc_appservice_records.py` | Private dependency used by `api_service_execution.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_saved_results.py` (module contents) | `a102/bvbrc_appservice_saved_results.py` | Private dependency used by `bvbrc_alignment_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_tool_info.py` (module contents) | `a102/bvbrc_appservice_tool_info.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_service_execution.py`, `bvbrc_appservice_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_calculators.py` (module contents) | `a102/bvbrc_data_calculators.py` | Private dependency used by `bvbrc_data_publication.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_feature_sequences.py` (module contents) | `a102/bvbrc_data_feature_sequences.py` | Private dependency used by `bvbrc_data_publication.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_fields.py` (module contents) | `a102/bvbrc_data_fields.py` | Private dependency used by `bvbrc_data_feature_sequences.py`, `bvbrc_data_molecular.py`, `bvbrc_data_publication.py`, `bvbrc_data_query.py`, `bvbrc_data_readers.py`, `bvbrc_data_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_host.py` (module contents) | `a102/bvbrc_data_host.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_molecular.py` (module contents) | `a102/bvbrc_data_molecular.py` | Private dependency used by `bvbrc_data_publication.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_publication.py` (module contents) | `a102/bvbrc_data_publication.py` | Private dependency used by `api_bvbrc.py`, `api_service_execution.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_query.py` (module contents) | `a102/bvbrc_data_query.py` | Private dependency used by `api_bvbrc.py`, `bvbrc_data_publication.py`, `bvbrc_data_readers.py`, `bvbrc_data_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_readers.py` (module contents) | `a102/bvbrc_data_readers.py` | Private dependency used by `api_bvbrc.py`, `bvbrc_data_calculators.py`, `bvbrc_data_publication.py`, `bvbrc_data_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_schema.py` (module contents) | `a102/bvbrc_data_schema.py` | Private dependency used by `api_bvbrc.py`, `api_service_execution.py`, `bvbrc_data_calculators.py`, `bvbrc_data_feature_sequences.py`, `bvbrc_data_host.py`, `bvbrc_data_molecular.py`, `bvbrc_data_publication.py`, `bvbrc_data_readers.py`, `bvbrc_data_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_views.py` (module contents) | `a102/bvbrc_data_views.py` | Private dependency used by `api_bvbrc.py`, `bvbrc_data_host.py`, `bvbrc_data_publication.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_bundle_adapter.py` (module contents) | `a102/bvbrc_homology_bundle_adapter.py` | Private dependency used by `bvbrc_appservice_adapters.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_grader.py` (module contents) | `a102/bvbrc_homology_grader.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_inputs.py` (module contents) | `a102/bvbrc_homology_inputs.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py`, `bvbrc_homology_grader.py`, `bvbrc_homology_metadata.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_metadata.py` (module contents) | `a102/bvbrc_homology_metadata.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_subject_binding.py` (module contents) | `a102/bvbrc_homology_subject_binding.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_contracts.py` (module contents) | `a102/bvbrc_minhash_contracts.py` | Private dependency used by `api_bvbrc_minhash.py`, `api_service_execution.py`, `bvbrc_minhash_host.py`, `bvbrc_minhash_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_grader.py` (module contents) | `a102/bvbrc_minhash_grader.py` | Private dependency used by `api_bvbrc_minhash.py`, `bvbrc_minhash_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_host.py` (module contents) | `a102/bvbrc_minhash_host.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_views.py` (module contents) | `a102/bvbrc_minhash_views.py` | Private dependency used by `bvbrc_minhash_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/completion_evidence.py` (module contents) | `a102/completion_evidence.py` | Private dependency used by `hpc_monitoring.py`, `practical_yield.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/ensembl_acquisition.py` (module contents) | `a102/ensembl_acquisition.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_input_versions.py` (module contents) | `a102/episode_input_versions.py` | Private dependency used by `api_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_reports.py` (module contents) | `a102/episode_reports.py` | Private dependency used by `runtime.py`, `scientific_process_reports.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_return_records.py` (module contents) | `a102/episode_return_records.py` | Private dependency used by `a102_resources.py`, `a102_structural_report.py`, `a102_tools.py`, `alignment_site_action_records.py`, `alignment_site_native.py`, `alphafold_acquisition_host.py`, `api_service_execution.py`, `bvbrc_alignment_returns.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_records.py`, `bvbrc_data_host.py`, `bvbrc_homology_returns.py`, `bvbrc_minhash_host.py`, `episode_services.py`, `execution_episode.py`, `hpc_episode.py`, `hpc_result_receipts.py`, `inprocess_replay.py`, `local_file_capture_results.py`, `molecular_sequence_input_bindings.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_database_returns.py`, `native_blast_hsp_views.py`, `native_blast_results.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_protein_structure_returns.py`, `protein_structure_action_records.py`, `protein_structure_tools.py`, `received_input_frames.py`, `received_native_file_inputs.py`, `runtime.py`, `scientific_process_episode.py`, `shared_information.py`, `structure_invocation.py`, `terminal_scientific_evidence.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_services.py` (module contents) | `a102/episode_services.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_work_report.py` (module contents) | `a102/episode_work_report.py` | Private dependency used by `execution_prompt.py`, `hpc_prompt.py`, `monitor_prompt.py`, `runtime.py`, `scientific_process_prompt.py`, `shared_information_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_contracts.py` (module contents) | `a102/evidence_axis_contracts.py` | Private dependency used by `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py`, `scientific_support_metadata.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_instructions.py` (module contents) | `a102/evidence_axis_instructions.py` | Private dependency used by `a102_investigation.py`, `a102_structural_evidence.py`, `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_contracts.py` (module contents) | `a102/execution_contracts.py` | Private dependency used by `alignment_site_native.py`, `api_execution.py`, `api_selected_call.py`, `api_selected_effects.py`, `api_service_execution.py`, `bvbrc_alignment_returns.py`, `bvbrc_appservice_bundle_values.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_monitor.py`, `bvbrc_appservice_publication.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_appservice_records.py`, `bvbrc_appservice_saved_results.py`, `bvbrc_data_host.py`, `bvbrc_data_views.py`, `bvbrc_homology_returns.py`, `bvbrc_minhash_host.py`, `episode_receipts.py`, `episode_return_records.py`, `execution_episode.py`, `execution_planning.py`, `execution_progress.py`, `file_capture_receipt_control.py`, `hpc_episode.py`, `local_file_capture_results.py`, `native_blast_acquisition.py`, `native_blast_database_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_database_returns.py`, `native_blast_masking_acquisition.py`, `native_blast_masking_results.py`, `native_blast_results.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_utility_acquisition.py`, `native_blast_utility_results.py`, `native_database_terminal_custody.py`, `native_hmmer_acquisition.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_failure_views.py`, `native_hmmer_preparation_results.py`, `native_hmmer_results.py`, `native_protein_structure_acquisition.py`, `native_protein_structure_contracts.py`, `native_protein_structure_driver.py`, `native_protein_structure_local.py`, `native_protein_structure_preparation.py`, `native_protein_structure_results.py`, `native_protein_structure_returns.py`, `native_protein_structure_worker.py`, `protein_structure_action_records.py`, `protein_structure_calculations.py`, `protein_structure_contracts.py`, `protein_structure_operands.py`, `protein_structure_projection_publication.py`, `protein_structure_publication.py`, `protein_structure_result_receipts.py`, `protein_structure_result_views.py`, `protein_structure_result_worker.py`, `protein_structure_selection.py`, `protein_structure_sheet.py`, `protein_structure_tools.py`, `terminal_scientific_evidence.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_expectations.py` (module contents) | `a102/execution_expectations.py` | Private dependency used by `independent_execution.py`, `runtime.py`, `tools.py`, `wait_estimation_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_inventory.py` (module contents) | `a102/execution_inventory.py` | Private dependency used by `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_planning.py` (module contents) | `a102/execution_planning.py` | Private dependency used by `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_prompt.py` (module contents) | `a102/execution_prompt.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_recording.py` (module contents) | `a102/execution_recording.py` | Private dependency used by `_local_job_worker.py`, `native_lifecycle.py`, `native_timing_information.py`, `ordinary_execution.py`, `state.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_service_setup.py` (module contents) | `a102/execution_service_setup.py` | Private dependency used by `a102_structural_workflow.py`, `independent_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_timing.py` (module contents) | `a102/execution_timing.py` | Private dependency used by `decision_exchanges.py`, `decision_history.py`, `episode_journal.py`, `numerical.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmalign_grader.py` (module contents) | `a102/hmmalign_grader.py` | Private dependency used by `hmmer_graders.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmalign_inputs.py` (module contents) | `a102/hmmalign_inputs.py` | Private dependency used by `hmmalign_grader.py`, `hmmer_alignment_preparation_calculations.py`, `hmmer_alignment_preparation_data.py`, `hmmer_graders.py`, `native_hmmer_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_prompt.py` (module contents) | `a102/hpc_prompt.py` | Private dependency used by `providers.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_result_receipts.py` (module contents) | `a102/hpc_result_receipts.py` | Private dependency used by `a102_hpc.py`, `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_scientific_commission.py` (module contents) | `a102/hpc_scientific_commission.py` | Retained original callable `commission`; no current A102 production caller. Actual A102 HPC requests and commissions are produced by `a102_hpc.request` and `a102_hpc.commission`. | Copied/split; private implementation |
| `gene_annotation_episode/independent_execution.py` (module contents) | `a102/independent_execution.py` | Private dependency used by `application_execution_binding.py` | Copied/split; private implementation |
| `gene_annotation_episode/inprocess_replay.py` (module contents) | `a102/inprocess_replay.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/inprocess_waiting.py` (module contents) | `a102/inprocess_waiting.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_contract_error.py` (module contents) | `a102/literature_contract_error.py` | Private dependency used by `literature_episode.py`, `literature_experimental_contracts.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_current_results.py` (module contents) | `a102/literature_current_results.py` | Retained original read-only `current_scoring_view`, `current_findings_view`, `current_interpretation_view` and rendering callables; no current A102 production caller. `runtime.py` uses the private `episode_work_report` presentation path. | Copied/split; private implementation |
| `gene_annotation_episode/literature_experiment_assessments.py` (module contents) | `a102/literature_experiment_assessments.py` | Private dependency used by `literature_structure_inputs.py`, `literature_structure_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_partner_defined_units.py` (module contents) | `a102/literature_partner_defined_units.py` | Private dependency used by `literature_rate_native_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_partner_source_fields.py` (module contents) | `a102/literature_partner_source_fields.py` | Private dependency used by `literature_partner_defined_units.py`, `literature_rate_native_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_calculations.py` (module contents) | `a102/literature_rate_calculations.py` | Private dependency used by `literature_rate_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_native_inputs.py` (module contents) | `a102/literature_rate_native_inputs.py` | Private dependency used by `literature_experimental_contracts.py`, `literature_rate_calculations.py`, `literature_rate_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_reader.py` (module contents) | `a102/literature_rate_reader.py` | Private dependency used by `literature_rate_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_storage.py` (module contents) | `a102/literature_rate_storage.py` | Private dependency used by `literature_structure_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_structure_calculations.py` (module contents) | `a102/literature_structure_calculations.py` | Private dependency used by `a102_literature_bindings.py`, `a102_work_report.py`, `literature_structure_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_structure_inputs.py` (module contents) | `a102/literature_structure_inputs.py` | Private dependency used by `literature_structure_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_structure_prompt.py` (module contents) | `a102/literature_structure_prompt.py` | Private dependency used by `a102_literature_bindings.py`, `literature_experimental_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_structure_storage.py` (module contents) | `a102/literature_structure_storage.py` | Private dependency used by `a102_experimental_evidence.py`, `a102_literature_bindings.py`, `a102_scientific_process_binding.py`, `a102_scientific_report_validation.py`, `a102_structural_report.py`, `literature_episode.py`, `literature_task_selection.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_structure_types.py` (module contents) | `a102/literature_structure_types.py` | Private dependency used by `literature_structure_inputs.py`, `literature_structure_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_work_report.py` (module contents) | `a102/literature_work_report.py` | Retained original `completed_work`, `source_metadata`, `render_completed_work` and `render_scoring_sheets` callables; no current A102 production caller. The current completed-work adapter is `a102_work_report` called by `episode_work_report`. | Copied/split; private implementation |
| `gene_annotation_episode/literature_work_results.py` (module contents) | `a102/literature_work_results.py` | Private dependency used by `literature_work_report.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_jobs.py` (module contents) | `a102/local_jobs.py` | Private dependency used by `a102_native_setup.py`, `a102_tools.py`, `document_tools.py`, `native_blast_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_driver.py`, `native_blast_local.py`, `native_blast_masking_contracts.py`, `native_blast_masking_local.py`, `native_blast_masking_result_publication.py`, `native_blast_masking_results.py`, `native_blast_result_publication.py`, `native_blast_results.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_utility_contracts.py`, `native_blast_utility_local.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_results.py`, `native_driver_runtime.py`, `native_hmmer_driver.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_driver.py`, `native_hmmer_preparation_local.py`, `native_hmmer_preparation_result_publication.py`, `native_hmmer_preparation_results.py`, `native_hmmer_result_publication.py`, `native_hmmer_results.py`, `native_lifecycle.py`, `native_protein_structure_driver.py`, `native_protein_structure_local.py`, `native_protein_structure_preparation.py`, `native_protein_structure_results.py`, `practical_execution_operations.py`, `protein_structure_tools.py`, `read_mapping.py`, `spreadsheet_tools.py`, `terminal_execution.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_resources.py` (module contents) | `a102/local_resources.py` | Private dependency used by `native_lifecycle.py`, `resource_episode.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/molecular_sequence_input_bindings.py` (module contents) | `a102/molecular_sequence_input_bindings.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/molecular_sequence_input_contracts.py` (module contents) | `a102/molecular_sequence_input_contracts.py` | Private dependency used by `bvbrc_data_host.py`, `molecular_sequence_input_bindings.py` | Copied/split; private implementation |
| `gene_annotation_episode/monitor_prompt.py` (module contents) | `a102/monitor_prompt.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_database_terminal_custody.py` (module contents) | `a102/native_database_terminal_custody.py` | Private dependency used by `native_blast_database_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_result_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_events.py` (module contents) | `a102/native_events.py` | Private dependency used by `_local_job_worker.py`, `native_lifecycle.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_file_capture.py` (module contents) | `a102/native_file_capture.py` | Private dependency used by `execution_episode.py`, `local_file_capture_results.py`, `molecular_sequence_input_bindings.py`, `terminal_native_file_capture.py`, `terminal_scientific_evidence.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_lifecycle.py` (module contents) | `a102/native_lifecycle.py` | Private dependency used by `a102_resources.py`, `a102_tools.py`, `local_jobs.py`, `local_resources.py`, `native_blast_local.py`, `native_blast_masking_local.py`, `native_blast_utility_local.py`, `native_events.py`, `native_hmmer_local.py`, `native_hmmer_preparation_local.py`, `native_hmmer_preparation_result_publication.py`, `native_protein_structure_local.py`, `native_protein_structure_preparation.py`, `ordinary_execution.py`, `practical_execution_operations.py`, `protein_structure_tools.py`, `terminal_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_protein_structure_acquisition.py` (module contents) | `a102/native_protein_structure_acquisition.py` | Private dependency used by `execution_episode.py`, `native_protein_structure_preparation.py`, `native_protein_structure_results.py`, `protein_structure_action_records.py`, `protein_structure_execution_information.py`, `protein_structure_operands.py`, `protein_structure_projection_publication.py`, `protein_structure_publication.py`, `protein_structure_result_receipts.py`, `protein_structure_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/nhmmer_grader.py` (module contents) | `a102/nhmmer_grader.py` | Private dependency used by `hmmer_graders.py`, `native_hmmer_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/nhmmer_inputs.py` (module contents) | `a102/nhmmer_inputs.py` | Private dependency used by `hmmer_graders.py`, `native_hmmer_result_worker.py`, `nhmmer_grader.py` | Copied/split; private implementation |
| `gene_annotation_episode/numerical.py` (module contents) | `a102/numerical.py` | Private dependency used by `completion_evidence.py`, `decision_history.py`, `episode_admission.py`, `episode_completion.py`, `episode_journal.py`, `episode_monitoring.py`, `episode_reports.py`, `execution_episode.py`, `hpc_campaign.py`, `hpc_episode.py`, `hpc_monitoring.py`, `independent_execution.py`, `literature_task_credit.py`, `monitor_episode.py`, `practical_yield.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/ordinary_execution.py` (module contents) | `a102/ordinary_execution.py` | Private dependency used by `tool_configuration.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/phylogeny_calculation_contracts.py` (module contents) | `a102/phylogeny_calculation_contracts.py` | Private dependency used by `bvbrc_alignment_provider_contracts.py`, `bvbrc_alignment_values.py`, `bvbrc_contingency_math.py`, `bvbrc_metacats_biological_calculators.py`, `bvbrc_metacats_biological_contracts.py`, `bvbrc_metacats_calculation_contracts.py`, `bvbrc_metacats_calculators.py`, `bvbrc_metacats_provider_contracts.py`, `bvbrc_msa_calculation_contracts.py`, `bvbrc_msa_calculators.py`, `bvbrc_msa_provider_contracts.py`, `phylogeny_calculators.py`, `xmfa_calculation_contracts.py`, `xmfa_source_contracts.py` | Copied/split; private implementation |
| `gene_annotation_episode/phylogeny_calculators.py` (module contents) | `a102/phylogeny_calculators.py` | Private dependency used by `bvbrc_metacats_grader.py`, `bvbrc_msa_calculators.py`, `bvbrc_msa_grader.py` | Copied/split; private implementation |
| `gene_annotation_episode/phylogeny_format_contracts.py` (module contents) | `a102/phylogeny_format_contracts.py` | Private dependency used by `bvbrc_alignment_provider_contracts.py`, `bvbrc_contingency_math.py`, `bvbrc_metacats_biological_calculators.py`, `bvbrc_metacats_biological_contracts.py`, `bvbrc_metacats_calculators.py`, `bvbrc_metacats_format_contracts.py`, `bvbrc_metacats_formats.py`, `bvbrc_metacats_input_formats.py`, `bvbrc_msa_calculators.py`, `bvbrc_msa_format_contracts.py`, `bvbrc_msa_formats.py`, `bvbrc_msa_provider_contracts.py`, `phylogeny_calculators.py`, `phylogeny_formats.py`, `xmfa_format_contracts.py`, `xmfa_source_contracts.py` | Copied/split; private implementation |
| `gene_annotation_episode/phylogeny_formats.py` (module contents) | `a102/phylogeny_formats.py` | Private dependency used by `bvbrc_alignment_bundle_resolution.py`, `bvbrc_metacats_input_formats.py`, `bvbrc_msa_xmfa_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/practical_execution_credit.py` (module contents) | `a102/practical_execution_credit.py` | Private dependency used by `practical_execution_state.py` | Copied/split; private implementation |
| `gene_annotation_episode/practical_execution_state.py` (module contents) | `a102/practical_execution_state.py` | Private dependency used by `api_selected_call.py`, `api_selected_effects.py`, `api_service_execution.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_monitor.py`, `bvbrc_appservice_publication.py`, `bvbrc_appservice_records.py`, `bvbrc_data_host.py`, `bvbrc_minhash_host.py`, `execution_episode.py`, `hpc_episode.py`, `native_blast_acquisition.py`, `native_blast_database_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_local.py`, `native_blast_masking_acquisition.py`, `native_blast_masking_local.py`, `native_blast_masking_result_publication.py`, `native_blast_masking_result_worker.py`, `native_blast_masking_results.py`, `native_blast_results.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_utility_acquisition.py`, `native_blast_utility_capture_failure.py`, `native_blast_utility_local.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_result_worker.py`, `native_blast_utility_results.py`, `native_hmmer_acquisition.py`, `native_hmmer_local.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_local.py`, `native_hmmer_preparation_result_publication.py`, `native_hmmer_preparation_result_worker.py`, `native_hmmer_preparation_results.py`, `native_hmmer_results.py`, `terminal_execution.py`, `terminal_execution_episode.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/practical_receipt_information.py` (module contents) | `a102/practical_receipt_information.py` | Private dependency used by `execution_episode.py`, `execution_progress.py`, `native_blast_database_result_publication.py`, `native_blast_standard_database_result_publication.py`, `protein_structure_result_receipts.py`, `terminal_execution_episode.py`, `terminal_scientific_evidence.py` | Copied/split; private implementation |
| `gene_annotation_episode/provider_authentication.py` (module contents) | `a102/provider_authentication.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/providers.py` (module contents) | `a102/providers.py` | Private dependency used by `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/received_native_file_inputs.py` (module contents) | `a102/received_native_file_inputs.py` | Private dependency used by `local_file_capture_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/resource_estimation.py` (module contents) | `a102/resource_estimation.py` | Private dependency used by `independent_execution.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/resource_tool_information.py` (module contents) | `a102/resource_tool_information.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/run_statistics.py` (module contents) | `a102/run_statistics.py` | Private dependency used by `execution_expectations.py`, `execution_recording.py`, `ordinary_execution.py`, `resource_estimation.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_library.py` (module contents) | `a102/scientific_process_library.py` | Private dependency used by `a102_investigation.py`, `a102_structural_workflow.py`, `composition_information.py`, `decision_context.py`, `episode_services.py`, `scientific_process_episode.py`, `scientific_process_setup.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_prompt.py` (module contents) | `a102/scientific_process_prompt.py` | Private dependency used by `execution_prompt.py`, `literature_experimental_prompt.py`, `providers.py`, `receiver_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_provenance.py` (module contents) | `a102/scientific_process_provenance.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_records.py` (module contents) | `a102/scientific_process_records.py` | Private dependency used by `a102_investigation.py`, `a102_scientific_report_validation.py`, `episode_services.py`, `evidence_axis_instructions.py`, `native_protein_structure_returns.py`, `runtime.py`, `scientific_process_episode.py`, `scientific_process_library.py`, `scientific_process_prompt.py`, `scientific_process_provenance.py`, `scientific_process_reports.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_reports.py` (module contents) | `a102/scientific_process_reports.py` | Private dependency used by `scientific_process_episode.py`, `scientific_process_provenance.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_setup.py` (module contents) | `a102/scientific_process_setup.py` | Private dependency used by `a102_investigation.py`, `a102_structural_workflow.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_support_metadata.py` (module contents) | `a102/scientific_support_metadata.py` | Private dependency used by `episode_services.py`, `scientific_process_episode.py`, `scientific_process_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_tool_library.py` (module contents) | `a102/scientific_tool_library.py` | Private dependency used by `a102_investigation.py`, `a102_structural_workflow.py`, `episode_services.py`, `scientific_process_records.py`, `scientific_process_setup.py`, `scientific_tool_retrieval.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_calculations.py` (module contents) | `a102/sequence_masking_calculations.py` | Private dependency used by `native_blast_masking_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_contracts.py` (module contents) | `a102/sequence_masking_contracts.py` | Private dependency used by `blast_maskinfo_inputs.py`, `native_blast_masking_contracts.py`, `native_blast_masking_driver.py`, `native_blast_masking_result_publication.py`, `native_blast_masking_result_worker.py`, `native_blast_masking_results.py`, `native_blast_masking_tool_info.py`, `sequence_masking_calculations.py`, `sequence_masking_inputs.py`, `sequence_masking_result_views.py`, `windowmasker_statistics.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_inputs.py` (module contents) | `a102/sequence_masking_inputs.py` | Private dependency used by `blast_maskinfo_inputs.py`, `native_blast_masking_driver.py`, `native_blast_masking_result_worker.py`, `windowmasker_statistics.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_result_views.py` (module contents) | `a102/sequence_masking_result_views.py` | Private dependency used by `native_blast_masking_result_publication.py`, `native_blast_masking_result_worker.py`, `native_blast_masking_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information.py` (module contents) | `a102/shared_information.py` | Private dependency used by `a102_tools.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information_results.py` (module contents) | `a102/shared_information_results.py` | Private dependency used by `episode_work_report.py`, `runtime.py`, `shared_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/source_display_labels.py` (module contents) | `a102/source_display_labels.py` | Retained original callable `source_literal_label`; no current A102 production caller. | Copied/split; private implementation |
| `gene_annotation_episode/terminal_native_file_capture.py` (module contents) | `a102/terminal_native_file_capture.py` | Retained original `capture_execution_file`, `capture_execution_declarations` and `validate_execution_file` callables; no current A102 production caller. Native structure capture uses its direct private acquisition/custody path. | Copied/split; private implementation |
| `gene_annotation_episode/tool_configuration.py` (module contents) | `a102/tool_configuration.py` | Private dependency used by `independent_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_information.py` (module contents) | `a102/tool_information.py` | Private dependency used by `resource_tool_information.py`, `scientific_process_prompt.py`, `scientific_process_records.py`, `scientific_process_reports.py`, `scientific_tool_library.py`, `scientific_tool_retrieval.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_schema_validation.py` (module contents) | `a102/tool_schema_validation.py` | Private dependency used by `resource_tool_information.py`, `scientific_tool_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_return_contracts.py` (module contents) | `a102/uniprot_return_contracts.py` | Private dependency used by `uniprot_return_projection.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_return_projection.py` (module contents) | `a102/uniprot_return_projection.py` | Private dependency used by `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_returns.py` (module contents) | `a102/uniprot_returns.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/wait_estimation_inputs.py` (module contents) | `a102/wait_estimation_inputs.py` | Private dependency used by `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/waiting.py` (module contents) | `a102/waiting.py` | Private dependency used by `alphafold_acquisition_host.py`, `local_file_capture_results.py`, `local_return_history.py`, `native_protein_structure_returns.py`, `protein_structure_result_receipts.py`, `runtime.py`, `wait_estimation_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/windowmasker_statistics.py` (module contents) | `a102/windowmasker_statistics.py` | Private dependency used by `native_blast_masking_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/workflow_budget.py` (module contents) | `a102/workflow_budget.py` | Private dependency used by `local_jobs.py`, `local_resources.py`, `native_lifecycle.py`, `providers.py`, `runtime.py`, `terminal_execution.py` | Copied/split; private implementation |


### 2026-11-11 — Final A102 physical placement accounting

This entry supersedes earlier staged dependency lists above for current file-placement status; those earlier entries remain dated history. The original scientific subtree milestones and retained execution results in the central ledger are not reopened by this source-placement pass.

| Original module/symbol | A102 destination | Current episode role and concrete caller | Change |
| --- | --- | --- | --- |
| `blast_hsp_site_inputs.extract_blast_hsp_columns`, supporting validators | `blast_hsp_site_inputs.py` | Structural sequence attribution; `alignment_site_native` reads selected HSP columns | Copied independently |
| `blast_hsp_site_calculators.calculate_blast_hsp_column_components` | `blast_hsp_site_calculators.py` | Structural sequence attribution; `alignment_site_native` calculates the original column components | Copied independently |
| `blast_graders.grade_blast_result` | `blast_graders.py` | Original BLAST result import used by `tools.ToolRegistry._import_blast` | Copied independently |
| `literature_rate_domains` original domain functions and constants | `literature_rate_domains.py` | Retained local rate calculation/storage calls in `literature_rate_calculations` and `literature_rate_storage`; no new A102 rate registration | Copied independently |
| `literature_rate_source_render` | `literature_rate_source_render.py` | Rendering helpers referenced by retained `literature_rate_domains` callables; no new runtime presentation route | Copied independently |
| Numerical template import | `vendor/nano_rarefaction.py` | `numerical.py` imports template types; template now imports A102’s own `library.method_loop` completion/constants | Rebound directly; formulas/provenance unchanged |
| Resource descriptor source reads | `resource_episode.ResourceEpisode.as_record` | Resource binding descriptor used by A102 workflow construction | Hashes its own `composition_information.py` and `schema_information_text.py`, preserving the original descriptor structure |
| Generic driver-runtime source/dependency primitives formerly imported from ATAC modules | `native_driver_runtime.py` | `native_hmmer_preparation_result_publication` runtime validation/freezing and dependency roots | Bound to already-copied local functions; no ATAC scientific module imported |
| Actual API execution presentation descriptors | `execution_progress.py` | Private execution progress information | HMMER, BLAST and MinHash implementation strings now name the existing A102 methods |
| A102 native HPC code snapshot | `a102_hpc.request` and private `native_driver_runtime._source_closure` | `a102_tools` requests native work; `a102_hpc_worker` stages and imports `a102_native_worker` | Source files and package markers now retain their actual private package paths; original request/manifest/hash fields preserved |
| Original structure terminal-result admission | `terminal_scientific_evidence.read_terminal_handoff` | Private native structure result custody | Preserved original ordinary receipt matching; removed the foreign FBA compact-request branch whose module is absent from A102 |

The six previously unspecified caller rows now explicitly identify retained original callable entry points with no current repository production caller. They were not wired into a new workflow or silently counted as used behavior. `literature_current_results` also now imports its own `domain.canonical`.

Worker module commands point to the A102 namespace. Source-root `parents[4]` values used as Python package search roots identify the repository’s package container; they do not import another axis’s implementation. The driver source snapshot includes plain parent package markers and this axis’s concrete imported modules, including relative module-alias imports. The machine supervisor string `gene_annotation_episode.workflow_budget` is deliberately retained only as the exact external command identity used by `tools/one_workflow.sh`: A102 executes its private resource reader and does not import supervisor behavior from that name. Existing CPU/RAM/swap policy is unchanged.

**Remaining physical-placement blockers: none identified in the actual A102 imports, worker paths and caller rows covered here.** The existing `private_scientific_reopen_pending` and `private_binding_reopen_pending` errors still make saved binding reconstruction unavailable; this is explicit later integration work, not an absent file, a shared behavioral fallback or a claim of runnable combined-root integration. No Python, tests, import/parse validation, linters, static suite, native jobs or workflow execution were run.

## 2026-11-11 iterator package placement

Moved the independently copied `library/method_loop/` package to `method_loop/` beside the private workflow code. It contains episode bindings, continuation and return mechanics, so it is outside the standalone-helper library. Direct imports and durable-worker module paths now name this private location; the worker package-root depth follows the moved files. Original license and provenance manifests remain with the copy. No runtime behavior or stopping rule was added.

### 2026-11-11: remaining original and library placement

- Moved `library/a102_axis_scalars.py` to `a102_axis_scalars.py`, retaining its original formulas and record fields for `a102_credit.A102Credit`. Calls are fixed A102: removed the redundant axis argument and selector guard; emitted axis remains A102.
- Moved `library/component_assessment_dependencies.py` to `component_assessment_dependencies.py` for the existing `a102_credit.py` received-assessment lookup. Its geometry lookup uses the same private `library/evidence_geometry.py` implementation.
- Moved `library/a102_structural_catalog.py` to `a102_structural_catalog.py` for the retained `a102_structural_workflow.py` source-catalog migration callable. No current production call is newly installed.
- Moved original top-level `bvbrc_alignment_tool_info.py` to A102. Its retained `alignment_tool_contracts` callable describes original MSA/MetaCATS commission modes; it has no current private caller. The results schema now comes directly from A102 `execution_episode.py`, replacing the old A103 reference. No new host registration.
- Retired top-level `native_protein_structure_acquisition.py`; A102 `execution_episode.py`, `execution_progress.py` and native structure capture/publication use its existing independent private copy.

No Python, tests, static suite or live workflow was run.

### 2026-11-11: remaining original homology execution helpers retired

These top-level originals now have applicable independent private implementations. Original source/module strings remain in retired history, not as shared fallbacks. The old combined top-level tool_information catalog and native_lifecycle original are not newly wired; their private replacements are the actual caller paths.

| Original | Private destination | Actual role |
| --- | --- | --- |
| `api_bvbrc_minhash.py` | `a102/api_bvbrc_minhash.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_contracts.py` | `a102/bvbrc_minhash_contracts.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_grader.py` | `a102/bvbrc_minhash_grader.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_host.py` | `a102/bvbrc_minhash_host.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_views.py` | `a102/bvbrc_minhash_views.py` | Private API service/host factual-return and grading chain |
| `hmmalign_grader.py` | `a102/hmmalign_grader.py` | Private HMMER alignment/search result parser and grader chain |
| `hmmalign_inputs.py` | `a102/hmmalign_inputs.py` | Private HMMER alignment/search result parser and grader chain |
| `nhmmer_grader.py` | `a102/nhmmer_grader.py` | Private HMMER alignment/search result parser and grader chain |
| `nhmmer_inputs.py` | `a102/nhmmer_inputs.py` | Private HMMER alignment/search result parser and grader chain |
| `sequence_masking_calculations.py` | `a102/sequence_masking_calculations.py` | Private native masking result/worker calculation and provenance chain |
| `sequence_masking_contracts.py` | `a102/sequence_masking_contracts.py` | Private native masking result/worker calculation and provenance chain |
| `sequence_masking_inputs.py` | `a102/sequence_masking_inputs.py` | Private native masking result/worker calculation and provenance chain |
| `sequence_masking_result_views.py` | `a102/sequence_masking_result_views.py` | Private native masking result/worker calculation and provenance chain |
| `windowmasker_statistics.py` | `a102/windowmasker_statistics.py` | Private native masking result/worker calculation and provenance chain |
| `native_events.py` | `a102/native_events.py` | Private native execution/provider lifecycle or scientific result presentation |

No runtime integration or execution validation was performed.

### 2026-11-11: preserved top-level extension source dispositions

The following original top-level implementations already have independent applicable A102 copies. They were not deleted in this placement pass because remaining unassigned top-level extension source still names their literal import paths. The private axis does not delegate to these originals. In particular: molecular/assay/variant/restriction extension originals name alignment identity or coordinate helpers; coding-sequence/ORF/primer and assembly/annotation extensions name sequence grading helpers; the original acquisition/state/worker modules name UniProt/read-mapping/sequence operations. Those original callers must receive their applicable independent dependencies when assigned; they are not a new shared scientific service and are not an enabled combined workflow.

| Preserved original | Applicable private implementation | Disposition |
| --- | --- | --- |
| `gene_annotation_episode/alignment_correspondence.py` | `a102/alignment_correspondence.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_result_presentation.py` | `a102/alignment_result_presentation.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_action_records.py` | `a102/alignment_site_action_records.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_calculators.py` | `a102/alignment_site_calculators.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_inputs.py` | `a102/alignment_site_inputs.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_mapping.py` | `a102/alignment_site_mapping.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_native.py` | `a102/alignment_site_native.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_returns.py` | `a102/alignment_site_returns.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/biopython_pairwise_grader.py` | `a102/biopython_pairwise_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/minimap2_grader.py` | `a102/minimap2_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/minimap2_grading_inputs.py` | `a102/minimap2_grading_inputs.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_composition_counts.py` | `a102/sequence_composition_counts.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_composition_grader.py` | `a102/sequence_composition_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_extraction_grader.py` | `a102/sequence_extraction_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_translation_grader.py` | `a102/sequence_translation_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_mapping.py` | `a102/sequence_mapping.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_ops.py` | `a102/sequence_ops.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_worker.py` | `a102/sequence_worker.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/read_mapping.py` | `a102/read_mapping.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_native.py` | `a102/uniprot_native.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_native_contracts.py` | `a102/uniprot_native_contracts.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_publication.py` | `a102/uniprot_publication.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_return_contracts.py` | `a102/uniprot_return_contracts.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |

Unassigned top-level `api_sequence_support.py`, `sequence_support_contracts.py`, `sequence_support_publication.py` and molecular acquisition extensions have no new A102 registration. This pass preserves their source and does not infer scientific ownership from generic sequence terminology. GenomeAlignment, ComparativeSystems and Mauve originals are separately accounted by the A103 placement task; A101 GenomeComparison has its own retained independent copy.

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
`yield.py`; registration, context, available actions/children and local assembly
in `episode.py`. Scientific scoring dependencies and their distinct descriptive
filenames remain as recorded above. Cross-episode tests/fixtures remain at this
axis's `tests/` until their precise local owner is established. Relocation is
pending; this entry fixes the chosen name before any binding moves.

### Scientific-process binding relocation applied

`scientific_process/episode.py` now owns the one `scientific_process` registration. The original module is removed; callers import the new binding directly. Each supporting class is private to this episode and has no registration.

- `scientific_process/episode.py`: `__init__`, `as_record`, `contract_information_profile`, `_role`, `child_roles`, `permitted_common_actions`, `allowed_children`, `instructions`, `_information_catalog`, `_closed_tool_resolution`, `_tool_resolution_for`, `_tool_resolution`, `catalog`, `common_tool_names`, `decision_context`, `execute`, `initial_decision_context`.
- `scientific_process/requests.py`: `assignment_schema`, `child_assignment_schema`, `_selection`, `_assignment`, `_invocation`, `prepare_assignment`, `_validate_origin`, `prepare_invocation`, `restore_closed_process`, `restore_saved_process`, `validate_context`, `validate_execution_context`, `_original_selection`, `_proposed_selection`.
- `scientific_process/returns.py`: `required_return_sources`, `fact_sources`, `facts`, `received_report_sources`, `received_report_facts`, `_validate_protein_structure_action_report`, `validate_received_report`, `resolve`, `validate_report`, `initial_references`, `received_form_references`, `resolve_received_reference`.
- `scientific_process/credit.py`: `credit_kind`, `credit_projector`, `credit_view`.
- `scientific_process/yield.py`: `private_yield_binding`, `continuation_task`, `yield_controller`.

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

Each binding retains its own local methods: `requests.py` for assignments and request-derived schemas; `returns.py` for source/fact/report delivery; `credit.py` for task progress; `yield.py` for existing forecast behavior; `waiting.py` for existing wait declarations; `episode.py` for registration, construction, actions, and selected grader/repository assembly. Files are created only for existing responsibilities. Descriptive calculators, graders and sheet storage retain their names and current axis ownership pending the dependency-placement review.

The current source-reading roles also perform applicable interpretation/population and grading work. That task mixture is preserved here; a later goal must decide task-specific divisions. Root evidence assessment can search/read directly as well as commission the nested strategy/search/source chain. Cross-role literature tests and shared fixtures remain at their common owner until the test-placement review.

### Literature role separation applied

The former multi-role class has been removed. Each recorded directory now has one independently implemented `LiteratureEpisode` with a singleton registration role; child-only bindings have empty entry roles. Their request/report/credit/yield/wait methods are private local supporting classes. The published-evidence episode exposes `create_binding_tree` only as caller assembly of seven separate instances, with copied existing caller configuration. It is not a registered binding, continuation policy or forwarding replacement. Existing scientific method bodies are preserved, including applicable A105/A108 grading and typed findings.

`literature` support map:

- `scientific_process/published_evidence_assessment/episode.py`: `literature_structure_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/waiting.py`: `supports_wait`.

`literature_strategy` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py`: `literature_structure_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/waiting.py`: `supports_wait`.

`literature_search` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py`: `literature_structure_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/waiting.py`: `supports_wait`.

`literature_page` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py`: `literature_structure_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/waiting.py`: `supports_wait`.

`literature_table` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py`: `literature_structure_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/waiting.py`: `supports_wait`.

`literature_ordered` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py`: `literature_structure_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/waiting.py`: `supports_wait`.

`literature_targeted` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py`: `literature_structure_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/waiting.py`: `supports_wait`.


## 2026-11-11 operational episode destinations recorded before relocation

The following plan follows declared child roles and the existing configured scientific parent. Resource-backed and direct execution bindings are alternative existing implementations; their distinct task homes do not imply simultaneous registration. Parent-specific copies preserve original request, report, operational/monitoring credit, yield and waiting behavior.

| Original class | Registered role | Chosen home (`episode.py`) | Commissioning parent |
| --- | --- | --- | --- |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/execution_job_submission` | `scientific_process` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/execution_job_submission/api_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/execution_job_submission/local_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/execution_job_submission/hpc_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/execution_result_acquisition` | `scientific_process` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/execution_progress_assessment` | `scientific_process` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `scientific_process/hpc_work_planning` | `scientific_process` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `scientific_process/hpc_work_planning/hpc_resource_prediction` | `scientific_process/hpc_work_planning` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/execution_job_submission` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/execution_result_acquisition` | `scientific_process/hpc_work_planning` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/execution_progress_assessment` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `resource_episode.py:ResourceEpisode` | `launch` | `scientific_process/resource_work_submission` | `scientific_process` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `scientific_process/resource_work_submission/api_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `scientific_process/resource_work_submission/local_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `scientific_process/resource_work_submission/hpc_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `results` | `scientific_process/resource_result_acquisition` | `scientific_process` |

The HPC prediction and allocation-execution episodes are siblings. HPC planning and allocation execution each commission their own submission, monitoring and result-acquisition copies. No generic children directory is introduced. Repeated run invocations reuse these source homes. Generic execution roles currently mix environment preparation, native/API work, recovery and result delivery under their original assignment; this mixture remains, with task-specific scientific divisions deferred.

Existing supporting methods will be extracted into local requests, returns, credit, yield and waiting files where present. Native parsers, calculators, graders and scientific sheets retain descriptive names. Monitor observation calculators retain their descriptive implementation file; monitoring information credit is not scientific scoring.

The existing `TerminalExecutionEpisode` is delegated inside `ExecutionEpisode` for the same `launch_local`/`launch_hpc` iteration; it is not a commissioned child. Its operative methods belong to each corresponding local/HPC job-execution home in `terminal_execution.py`, with the single private registration supplied by that home's `episode.py`. The old two-role operative class must not create a second registration or a fictitious nested episode.

Runtime limitations: saved composition currently raises `private_binding_reopen_pending`, and the registry indexes only a role token. Parent-specific duplicate-role registration and legacy monolithic homology runtime/adapter interfaces must be reported explicitly until a caller can address their private paths. Do not choose one parent's binding as a fallback for another.

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

### Operational private implementations written

Each planned home now contains one singleton-role class with its original methods split into private responsibility files. Descriptor binding IDs name the stable source home so repeated-parent copies have distinct ownership; registered role tokens and scientific return contents retain their existing meanings. The original modules are temporarily retained only until their callers and receipt-source references are rebound; they must be removed before this pass is complete.

`scientific_process/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/api_job_execution` (`launch_api`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/hpc_work_planning` (`hpc`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/hpc_resource_prediction` (`hpc_prediction`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/hpc_allocation_execution` (`hpc_execution`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` (`launch_api`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` (`launch_api`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `retained_protein_structure_reader`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_protein_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_retained_protein_result`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/resource_work_submission` (`launch`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_work_submission/api_resource_work_execution` (`launch_api`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_work_submission/local_resource_work_execution` (`launch_local`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_work_submission/hpc_resource_work_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_result_acquisition` (`results`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.


## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/execution_job_submission/api_job_execution` | `execution_job_submission/api_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission` | `execution_job_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_job_submission/hpc_job_execution` | `execution_job_submission/hpc_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission/local_job_execution` | `execution_job_submission/local_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_progress_assessment` | `execution_progress_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_result_acquisition` | `execution_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning` | `hpc_work_planning` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` | `hpc_work_planning/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission` | `hpc_work_planning/execution_job_submission` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `hpc_work_planning/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `hpc_work_planning/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_progress_assessment` | `hpc_work_planning/execution_progress_assessment` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_result_acquisition` | `hpc_work_planning/execution_result_acquisition` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution` | `hpc_work_planning/hpc_allocation_execution` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_resource_prediction` | `hpc_work_planning/hpc_resource_prediction` | private copy | hpc_work_planning |
| `scientific_process/published_evidence_assessment` | `published_evidence_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement` | private copy | published_evidence_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | private copy | published_evidence_assessment/evidence_search_strategy_improvement |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/resource_result_acquisition` | `resource_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/api_resource_work_execution` | `resource_work_submission/api_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission` | `resource_work_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/hpc_resource_work_execution` | `resource_work_submission/hpc_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission/local_resource_work_execution` | `resource_work_submission/local_resource_work_execution` | private copy | resource_work_submission |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/execution_job_submission/api_job_execution` | `execution_job_submission/api_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission` | `execution_job_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_job_submission/hpc_job_execution` | `execution_job_submission/hpc_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission/local_job_execution` | `execution_job_submission/local_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_progress_assessment` | `execution_progress_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_result_acquisition` | `execution_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning` | `hpc_work_planning` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` | `hpc_work_planning/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission` | `hpc_work_planning/execution_job_submission` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `hpc_work_planning/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `hpc_work_planning/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_progress_assessment` | `hpc_work_planning/execution_progress_assessment` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_result_acquisition` | `hpc_work_planning/execution_result_acquisition` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution` | `hpc_work_planning/hpc_allocation_execution` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_resource_prediction` | `hpc_work_planning/hpc_resource_prediction` | private copy | hpc_work_planning |
| `scientific_process/published_evidence_assessment` | `published_evidence_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement` | private copy | published_evidence_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | private copy | published_evidence_assessment/evidence_search_strategy_improvement |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/resource_result_acquisition` | `resource_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/api_resource_work_execution` | `resource_work_submission/api_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission` | `resource_work_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/hpc_resource_work_execution` | `resource_work_submission/hpc_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission/local_resource_work_execution` | `resource_work_submission/local_resource_work_execution` | private copy | resource_work_submission |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

## 2026-11-11 binding test ownership

Current direct literature tests now import the private role matching their explicit context; standalone parent contexts use the standalone copy. Tests that construct root/runtime workflows stay at the common axis test owner. Scientific graders, sheets and fixtures are shared by the independent standalone/scientific copies and retain the common axis owner. Historical combined tests with already-retired top-level imports remain unavailable; source placement does not repair their missing runtime.

No reviewed direct binding test is exclusive to one private episode: existing tests retain the common axis owner.

Shared required fixtures stay in `tests/fixtures/`; reusable named test helpers remain in `tests/` when imported by other tests. No fixture or helper is moved into disposable runs. The detailed support/test inventory records the final owners.

## 2026-11-11 final request-responsibility placement

The following existing incoming-assignment/schema/constraint methods move unchanged from each private episode.py class into that same home's requests.py mixin. These are method placements, not additional bindings or a change to admission behavior.

- `execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.

## 2026-11-11 final role and supporting-code index

The [complete ownership inventory](ownership_inventory.json) is the exact appendix to this record: it maps every original binding class to its singleton role, actual parent, final home, local method symbols and responsibility files. It also records every descriptive support module, its owner, imports, direct callers and consuming episodes; every library symbol and its explicit importing modules; and each test/helper and required fixture file. Unreferenced retained modules are recorded with empty consumers, not represented as active evidence or bindings. Shared scientific graders, readers, sheets and calculators keep their descriptive names at the common axis owner. Their functions are not merged with investigation credit.

| Original binding | Role | Final home | Parent | Supporting files |
| --- | --- | --- | --- | --- |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `execution_job_submission/api_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `execution_job_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `execution_job_submission/hpc_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `execution_job_submission/local_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `execution_progress_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `execution_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `hpc_work_planning/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `hpc_work_planning/execution_job_submission/api_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `hpc_work_planning/execution_job_submission/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `hpc_work_planning/execution_job_submission/hpc_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `hpc_work_planning/execution_job_submission/local_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `hpc_work_planning/execution_progress_assessment/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `hpc_work_planning/execution_result_acquisition/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `hpc_work_planning/hpc_allocation_execution/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `hpc_work_planning/hpc_resource_prediction/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `published_evidence_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `resource_episode.py:ResourceEpisode` | `results` | `resource_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `resource_work_submission/api_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch` | `resource_work_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `resource_work_submission/hpc_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `resource_work_submission/local_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `scientific_process_episode.py:ScientificProcessEpisode` | `scientific_process` | `scientific_process/episode.py` | root annotation; scientific_process self-recursion (not expanded) | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/execution_job_submission/api_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/execution_job_submission/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/execution_job_submission/local_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/execution_progress_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/execution_result_acquisition/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `scientific_process/hpc_work_planning/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/execution_job_submission/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/execution_progress_assessment/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/execution_result_acquisition/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `scientific_process/hpc_work_planning/hpc_resource_prediction/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `scientific_process/published_evidence_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | scientific_process/published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `resource_episode.py:ResourceEpisode` | `results` | `scientific_process/resource_result_acquisition/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `scientific_process/resource_work_submission/api_resource_work_execution/episode.py` | scientific_process/resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch` | `scientific_process/resource_work_submission/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `scientific_process/resource_work_submission/hpc_resource_work_execution/episode.py` | scientific_process/resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `scientific_process/resource_work_submission/local_resource_work_execution/episode.py` | scientific_process/resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |

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


## 2026-11-11 remaining monitor responsibility extraction

Each existing monitor now has its own goal, task, decision exchange, state, operations, reports, credit and yield files, plus recursive directional messages and tests. Per-episode ownership files and inventories describe current files, dependencies and remaining parent-message/applicability work. The whole monitor check has 426 passes and two inherited A106 Store initialization failures; original-binding reproduction is retained. See `runs/monitor_tree_20261111_audit/`, `runs/monitor_tree_20261111_behavior/` and `runs/monitor_tree_20261111_a106_baseline/`. This is controlled connection validation, not autonomous monitoring or full restoration.

## 2026-11-11 named monitor parent exchanges

Each existing scientific/HPC parent of a progress monitor now has connected
`to_child_execution_progress_assessment.py` and
`from_child_execution_progress_assessment.py`. Current parent and child
inventories record both endpoints and their saved action/report-attempt identity.
The parent methods retain their original bodies; HPC implementation fingerprints
include the new message files. The seven missing legacy parent homes across the
axes remain explicit. Retained verification and the corrected test exception
assertions are in `runs/monitor_parent_tree_20261111_records/validation.json`:
530 current passing checks and two inherited A106 Store-construction failures.
The parents' larger task divisions and the full organization remain incomplete.

## 2026-11-11 private monitor task narrowing

Monitor decision snapshots and fresh input preparation now have private implementation files. Inapplicable scientific/job/read-mapping/shared-grading branches were removed with their destinations or non-applicability recorded. Baseline 272 checks pass; expanded validation has 698 passes and the same two inherited A106 Store failures. Source audit and current inventories are under `runs/monitor_task_narrowing_20261111_{audit,records}/`. Private instructions, prompt rendering, caller credit presentation and the full episode-tree organization remain open.

## 2026-11-11 monitor instructions and renderer ownership

Each private monitor now composes applicable instructions in `task_instructions.py` and selects `library/monitor_prompt.py` explicitly. The old root formatter moved; its consumers are recorded in `library/monitor_prompt.ownership.json`. Provider transport accepts the declared renderer through an optional interface, preserving default behavior. Binding fingerprints include the selected library source. The expanded suite has 1,032 passes and two inherited A106 failures; all 340 affected instruction checks pass after the final guidance preservation. Source and current identity receipts are under `runs/monitor_prompt_ownership_20261111_{audit02,records}/`. Earlier instruction/rendering limitations are superseded for these monitors. Caller credit-shape presentation, restoration and the full episode-tree organization remain unfinished.

## 2026-11-11 monitor credit calculator ownership

Private monitor credit files now select `library/progress_information_credit.py` with explicit caller operands; custom projectors remain unchanged. Consumers, source provenance, actual projector names and per-axis branch accounting are in `library/progress_information_credit.ownership.json`. A104 restores its original missing shared dependency; A107 removes an unsupported legacy job branch. Stale public-reader imports in affected setup paths were repaired. Validation has 1,302 passes and two unchanged A106 Store failures, plus 34 passing actual-outcome/runtime-credit connections. Full service construction, saved reopening, caller-specific presentation and wider organization remain open.

## 2026-11-11 canonical workflow resource infrastructure

This axis now imports machine ownership/enforcement directly from the canonical module. Its own Policy, AcquisitionError and scientific/native implementation bodies remain unchanged.

The same actual launcher/owner now serves these consumers. The canonical checker, launcher, one-CPU/5-GiB/no-swap bounds and authentication guards are unchanged. Four axes previously failed sixteen owner checks; after the import repair their eight default Policy/Resources boundaries and three ToolRegistries return, and all five redundant copies are retired. A104's ToolRegistry now exposes a separate missing `local_tools` KeyError. A102 retains its three separately observed missing-default KeyErrors. These are constructor diagnostics, not a test-pass count or native/scientific workflow validation.

Original checker sources, metadata, fingerprints and receipts remain historical. Any source changes predating this repair are listed separately from its exact delta. The existing CPU/thread gate is documented by a separate no-native diagnostic and remains open; no count limit or stopping rule was added. Full private splitting and saved-workflow restoration remain incomplete. Complete scoped evidence: `runs/workflow_resource_infrastructure_20261111_records_prepare`.

## 2026-11-12 current private binding reconstruction

The axis composition reconstructs an explicit set of 43 current private binding identities and preserves complete descriptors, actual Store/run/services operands and caller-supplied credit. Before repair all direct constructors returned but composition raised `private_binding_reopen_pending`; after repair the identical construction and required identity/rejection checks pass. This controlled diagnostic does not establish the full application factory, historical migration, receiving authority, all private tasks/messages, independent saved reopening or autonomous science. Historical descriptors and earlier scientific milestones remain unchanged.

## 2026-11-12 private API execution tasks and parent receipts

Six original API homes now select their own concrete task with original decisions, saved action outcomes, state, instructions, waiting, credit and report delivery. The exact source audit accounts for complete binding/task modules, incoming assignment authentication, retired requests/returns and six parent API receiver selectors. Original task instruction-service callbacks remain intact; the default own-axis service selects each task class's explicit private composer, preserving custom service return and exception identity. Actual six-owner baseline comparison and 216 exact passing tests preserve original outcomes, identity and exceptions, including all eighteen instruction-service observations per home and the exact declared composer transitions. Workflow request assembly, provider frame dispatch and original receiving-reader declaration remain explicit dependencies. This controlled engineering stage proves neither full saved restoration nor autonomous science; historical descriptors and prior scientific milestones remain unchanged.

## 2026-11-12 Existing private task instruction callback correction

The recorded 24-file two-axis correction restores each original instruction service callback and declares its unchanged private composer as a static class selection. All 392 exact instruction-boundary cases pass in the linked actual evidence, preserving private default text and generic nonparticipant fallback. Scope is actual task/service methods with controlled ports; constructors, native/scientific work, full restoration and autonomy are not established. Earlier validation and descriptors remain historical. Current source fingerprints and explicit old/new source transitions are recorded separately.

## 2026-11-12 private Launch tasks and original child receipts

Six original Launch homes now own their concrete task, original action/replay paths, ancestry-dependent instructions, state, waiting, credit and report delivery. Their original instruction-service callbacks and complete lexical yield modules remain intact. Six existing API receivers remain exact while twelve private local/HPC receivers preserve the original incoming fallback; selector merging retains the actual child role. Actual six-owner baseline comparison and 252 exact passing tests preserve original outcomes, identity and exceptions, including eighteen instruction-service observations per home. Workflow.selected/build still owns outgoing request assembly. Cross-context receiving readers, original service declarations, provider dispatch and historical terminal policies remain explicit dependencies. This engineering stage proves neither full saved restoration nor autonomous science. Earlier API metadata, historical descriptors and scientific milestones remain unchanged.

## 2026-11-12 Native child private task connections

Twelve original local/HPC child private tasks and messages; preserved six Launch receiver portfolios; four unchanged HPC descriptor footprint transitions. Actual evidence is linked below in the corresponding inventory stage; this controlled engineering validation is not native/scientific execution or full restoration. Historical stages and descriptors are retained.

## 2026-11-12 private Results tasks and retained result receipts

Six original A102 Results private tasks, original retained acquisition and cross-context receipt callbacks, lexical yield and service dispatch preserved. Actual 366-case original/installed evidence and six-owner raw comparison are recorded in the inventory. Controlled organizational validation supplies neither new scientific credit nor independent native handoff authority. Earlier metadata remains recoverable.

## Installed private Resource ownership (2026-11-13)

Ten Resource homes have installed private tasks and bindings. Their current inventories record the exact installed source epoch and original destinations. The final behavioral union remains pending; implementation ownership and scientific workflow validation are separate.

Current selected private ownership reconciliation: exact finite source authority `runs/root_a102_a103_installed_prompt_selection_preparation_01/SOURCE_SELECTION.json` supplies the current head, private source, Resource and parent-private records. The earlier request/return-era current catalogues and three former top-level Homology bindings have explicit historical custody in the inventory. Actual current methods, source membership, source fingerprints, import consumers and message endpoints are recorded there. Candidate implementation and canonical installation remain separate; this metadata preparation executes no tests.

Installed execution24 ownership:162 new modules,264 surviving replacements and12 retired modules; complete own catalogues grow768 to918. The axis has2611 Python sources, including12 separately retained framework sources. Shared next36 selection: `runs/root_next36_verification_preparation_01/EXPECTED_SOURCE_SELECTION.json`. Actual source application: `runs/root_next36_source_application_01/applied/application.json`. Current rich descriptors, consumers, endpoints and all retired beforeimages are explicit; prior source and validation records remain historical.

Installed execution30 ownership:150 new modules,168 surviving replacements and no module retirement; complete own catalogues grow1116 to1266. The axis has2761 Python sources, including12 separately retained framework sources. Shared execution60 selection: `runs/root_execution60_verification_preparation_01/EXPECTED_SOURCE_SELECTION.json`. Actual source application: `runs/root_execution60_source_application_01/applied/application.json`. Current rich descriptors, consumers, actual parent request owners and66 Results callable retirements are explicit; all prior retirement/source/validation records remain historical.

Resource10 current ownership records326 direct source files,126 additions,160 actual movements and six retired helper copies. All earlier source/history/retired-module records remain historical; current A102 axis map has2887 files. Source application: `runs/root_remaining40_source_application_01/applied/application.json`.


## 2026-11-13 prepared complete existing parent ownership

The existing implicit annotation host has35 substantive private sources in the axis-root home, and the existing conditional improvement host has20 in its descriptive annotation_improvement home (runtime role improvement). Neither receives an invented registered binding or descriptor hash. Eighteen actual directional pairs cover nine annotation choices, eight admitted Scientific choices and recursive improvement, retaining original allowed-role/Scientific guards and unavailable contexts. Actual60,20,36,39 and affected3 remain separate bounded original/current controls with explicit external ports. The original Scientific whole-axis formula now has2953 proposed operands. This is the prepared source/current-ownership record; actual installation is recorded separately in docs/EVIDENCE_AXIS_LEDGER.md with source and metadata application receipts. Completed child milestones and all prior raw source/ownership values are preserved. Fingerprint account: `runs/main_a102_final_metadata_generation_01/prepared/FINGERPRINT.json`.


## 2026-11-13 private report, action and commissioning policy

Current private callers select their actual same-axis policy definers through the original bound-method override interface. The particular Scientific snapshot has one private owner and retains all three late guarded consumers; root commissioning policy keeps its original callback, saved-action and credit gates. The current machine-readable inventory records actual source members, formulas, private configurations and shared helper consumers. Focused33 and cold30 retain their explicit provider and import-only limits; prior60/20/36/39/3 and earlier child science remain separate measured scopes. This is a preparation record. Actual canonical application status is supplied separately by the central ledger and real installation receipts. No configured digest is invented for configuration-only or unregistered homes.


## 2026-11-13 Scientific definitions and invocation-time providers

The current machine-readable inventory identifies the actual private Scientific definers, complete selected source members, original namespace consumers and unchanged own-axis source formulas. Actual provider48 and Scientific16 retain their separately measured boundaries and source epochs. Earlier parent, policy and scientific results are retained without a rerun or an expanded claim. The eight private HPC handoff consumers select their actual same-axis policy at the original late boundary; actual11 checks its native getter and ordering semantics, while actual4 checks the four declared descriptor maps against copied library bytes. The shared provider helper and original fixtures live under the axis library tests with their exact private consumer roster. These preparation records do not assert installation or a full scientific/restoration workflow. Current installation status is supplied by the central ledger and actual source/metadata application postchecks.
