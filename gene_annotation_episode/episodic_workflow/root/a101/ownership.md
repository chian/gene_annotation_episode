# A101 current ownership

The current inventory discovers all 40 declared A101 binding homes, including the scientific head and the standalone and nested episode families. Each home has its actual responsibilities, methods, directional endpoints, static dependencies, current library consumers and required input ownership.

The 25 operational homes are only the private-tail cleanup scope. They are not the scope of this inventory.

Original inventories and earlier prose remain historical provenance. Current source applications, scoped test results, shared-root integration, historical restoration and autonomous science remain separate claims. Failed or unavailable cases are retained without becoming prerequisites for unrelated implementation.

<details><summary>Historical ownership prose</summary>

# A101 ownership

A101 owns homology acquisition, BLAST/HMMER evidence preparation, native execution adapters, graders, credit, and work reports. Its required tests and fixtures live in `tests/` beside these modules. The root episode commissions A101 through `a101_scientific_process_binding.py`. A101 now also has a private singular execution binding and local terminal execution binding; application construction has not yet been routed to them.

`homology_recovery.py` validates returned native phmmer search receipts through A101's own `library/homology_search_receipt.py`. A103 and A107 hold their own copies of this reusable validator; A101 imports no A103 behavior.

Other reused BLAST parsers and `homology_query.py` participate in pinned native or episode source inventories with their current axis-root paths; moving them deeper in this gather would change those established bundle contracts. Single-task helpers remain beside their task modules.

The BV-BRC Homology binding moved here after the initial inventory. Its seven original top-level modules retain their basenames in this package: `bvbrc_homology_inputs.py` parses the returned native formats, `bvbrc_homology_metadata.py` binds explicit metadata, `bvbrc_homology_subject_binding.py` validates pairwise subjects, `bvbrc_homology_grader.py` calculates the scientific sheet, `bvbrc_homology_bundle_adapter.py` assembles and pins the bundle, `bvbrc_homology_returns.py` projects authenticated facts, and `bvbrc_homology_tool_info.py` describes selectable tool contracts. `bvbrc_appservice_adapters.py`, `api_service_execution.py`, `execution_episodes.py`, and A101 tests import these axis-local implementations. The bundle's implementation pin resolves A101-local BLAST dependencies here and shared BV-BRC contracts at the package root.

## Mixed-module splits

| Original owner | A101 destination | Owned symbols / purpose | Direct callers | Operation |
| --- | --- | --- | --- | --- |
| `gene_annotation_episode/execution_episodes.py` | `execution_episode.py` | A101 launch, result, BLAST/HMMER execution binding | A101 execution service construction to be routed | copied; private constructor pending |
| `gene_annotation_episode/terminal_execution_episodes.py` | `terminal_execution_episode.py` | A101 local/HPC command episode behavior used by its execution binding | `execution_episode.py` | copied |
| `gene_annotation_episode/execution_contracts.py` | `execution_contracts.py` | A101 execution declaration helpers | `execution_episode.py` | copied |
| `gene_annotation_episode/launch_instructions.py` | `launch_instructions.py` | A101 launch instructions | `execution_episode.py` | copied |
| `gene_annotation_episode/practical_execution_operations.py` | `practical_execution_operations.py` | A101 command operation semantics | `execution_episode.py`, `terminal_execution_episode.py` | copied |
| `gene_annotation_episode/practical_execution_records.py` | `practical_execution_records.py` | A101 execution request and completion records | `execution_episode.py`, `terminal_execution_episode.py` | copied |
| `gene_annotation_episode/practical_execution_state.py` | `practical_execution_state.py` | A101 execution state projection | `execution_episode.py`, `terminal_execution_episode.py` | copied |
| `gene_annotation_episode/practical_receipt_information.py` | `practical_receipt_information.py` | A101 command receipt projection | `execution_episode.py` | copied |
| `gene_annotation_episode/resource_records.py` | `resource_records.py` | A101 resource record schemas | `execution_episode.py` | copied |
| `gene_annotation_episode/terminal_execution.py` | `terminal_execution.py` | A101 terminal transport binding | `terminal_execution_episode.py` | copied |
| `gene_annotation_episode/terminal_scientific_evidence.py` | `terminal_scientific_evidence.py` | A101 terminal evidence paths | `terminal_execution_episode.py` | copied |
| `gene_annotation_episode/native_lifecycle.py` | `native_lifecycle.py` | A101 local native lifecycle | `practical_execution_operations.py` | copied |
| `gene_annotation_episode/execution_episodes.py` | `a101_blast_execution.py` | BLAST execution forms, handlers, and typed result returns | `ExecutionEpisodes`, API BLAST tests | split |
| `gene_annotation_episode/execution_episodes.py` | `a101_execution_bindings.py` | BLAST/HMMER resource validation, result-reader registration, requested-job and result-selector schemas, native and BV-BRC Homology operation contracts | `ExecutionEpisodes` | split |
| `gene_annotation_episode/episode_monitoring.py` | `a101_blast_monitoring.py` | BLAST-specific one-observation monitor rule | `episode_monitoring`, BLAST monitor tests | split |
| `gene_annotation_episode/resource_episodes.py` | `a101_homology_resource_adapter.py` | `HomologyResourceAdapter` and its dispatch | `resource_episodes`, homology episodes | split |
| `gene_annotation_episode/resource_episodes.py` | `a101_resource_implementation.py` | A101 homology implementation bytes in original pin order | `ResourceEpisodes.as_record` | split |
| `gene_annotation_episode/episodic_workflow/root/scientific_process_episodes.py` | `a101_scientific_process_binding.py` | A101 assignment and root-facing scientific return binding | root scientific process | split |
| `gene_annotation_episode/all_evidence_tools.py` | `a101_blast_catalog.py` | A101 BLAST catalog entries | root catalog composer | split |
| `gene_annotation_episode/episodic_workflow/root/a103/a103_detection.py` | `library/homology_search_receipt.py` | Native phmmer receipt authentication reused by A101 recovery | `homology_recovery.py` | copied |

## Original module map

The rows below map each physically owned A101 module to its original top-level module. `Moved` means the original implementation now lives here; `extracted` means an A101 portion was taken from a mixed module. Caller names are from the pre-move import inventory; root registration and tests also call these modules after import updates.

| Original module | Destination | Role | Direct callers before relocation | Operation |
| --- | --- | --- | --- | --- |
| `a101_credit.py` | `a101_credit.py` | grading | a101_investigation, a101_replay, evidence_root, root_axis_receipts | moved |
| `a101_investigation.py` | `a101_investigation.py` | episode | — | moved |
| `a101_replay.py` | `a101_replay.py` | episode | — | moved |
| `a101_scoring.py` | `a101_scoring.py` | grading | a101_credit, a102_hpc, a102_tools, sequence_attribution | moved |
| `a101_work_report.py` | `a101_work_report.py` | results | — | moved |
| `blast_database_extraction.py` | `blast_database_extraction.py` | contracts | blast_database_inspection, blast_preparation_inputs, blast_preparation_result_assembly, blast_vdb_utility_contracts | moved |
| `blast_database_grader.py` | `blast_database_grader.py` | grading | blast_graders, blast_sequence_database, bvbrc_homology_grader | moved |
| `blast_database_inspection.py` | `blast_database_inspection.py` | contracts | blast_preparation_inputs, blast_vdb_utility_inputs, native_blast_utility_result_worker | moved |
| `blast_database_population_associations.py` | `blast_database_population_associations.py` | contracts | blast_database_grader, blast_iteration_inputs, blast_sequence_database, native_blast_database_population_metadata | moved |
| `blast_database_preparation.py` | `blast_database_preparation.py` | contracts | blast_preparation_population, blast_preparation_result_assembly, blast_utility_result_views, native_blast_utility_result_worker | moved |
| `blast_fasta_record_identity.py` | `blast_fasta_record_identity.py` | calculation | blast_database_grader, native_blast_database_metadata, native_blast_database_result_worker, native_blast_standard_database_calculators | moved |
| `blast_graders.py` | `blast_graders.py` | grading | tools | moved |
| `blast_grading_inputs.py` | `blast_grading_inputs.py` | contracts | blast_graders, bvbrc_homology_inputs | moved |
| `blast_hsp_site_calculators.py` | `blast_hsp_site_calculators.py` | calculation | alignment_site_native | moved |
| `blast_hsp_site_inputs.py` | `blast_hsp_site_inputs.py` | contracts | alignment_site_native, blast_hsp_site_calculators | moved |
| `blast_iteration_calculators.py` | `blast_iteration_calculators.py` | calculation | — | moved |
| `blast_iteration_inputs.py` | `blast_iteration_inputs.py` | contracts | blast_iteration_calculators, blast_native_iteration_records | moved |
| `blast_maskinfo_inputs.py` | `blast_maskinfo_inputs.py` | contracts | native_blast_masking_result_worker, sequence_masking_contracts | moved |
| `blast_native_iteration_records.py` | `blast_native_iteration_records.py` | execution | native_blast_database_convergence | moved |
| `blast_pairwise_grader.py` | `blast_pairwise_grader.py` | grading | blast_database_grader, blast_graders, blast_hsp_site_inputs, blast_pairwise_results | moved |
| `blast_pairwise_result_views.py` | `blast_pairwise_result_views.py` | results | execution_episodes, execution_progress, native_blast_hsp_views, native_blast_result_publication | moved |
| `blast_pairwise_results.py` | `blast_pairwise_results.py` | results | native_blast_hsp_views, native_blast_result_worker | moved |
| `blast_preparation_contracts.py` | `blast_preparation_contracts.py` | contracts | blast_preparation_inputs, blast_preparation_population, blast_utility_contracts, blast_vdb_utility_contracts | moved |
| `blast_preparation_inputs.py` | `blast_preparation_inputs.py` | contracts | blast_preparation_result_assembly, native_blast_utility_driver, native_blast_utility_materializations, native_blast_vdb_utility_context | moved |
| `blast_preparation_population.py` | `blast_preparation_population.py` | calculation | blast_database_preparation, blast_preparation_result_assembly, blast_utility_contracts | moved |
| `blast_preparation_result_assembly.py` | `blast_preparation_result_assembly.py` | results | native_blast_utility_result_worker | moved |
| `blast_profile_calculators.py` | `blast_profile_calculators.py` | calculation | — | moved |
| `blast_profile_inputs.py` | `blast_profile_inputs.py` | contracts | blast_profile_calculators | moved |
| `blast_program_context.py` | `blast_program_context.py` | calculation | blast_iteration_calculators, blast_pairwise_results, blast_profile_calculators, blast_report_collection | moved |
| `blast_pssm_calculators.py` | `blast_pssm_calculators.py` | calculation | — | moved |
| `blast_pssm_inputs.py` | `blast_pssm_inputs.py` | contracts | blast_pssm_master_inputs, native_blast_standard_database_metadata | moved |
| `blast_pssm_master_inputs.py` | `blast_pssm_master_inputs.py` | contracts | blast_pssm_calculators, native_blast_database_metadata, native_blast_standard_database_metadata | moved |
| `blast_reference_metadata.py` | `blast_reference_metadata.py` | contracts | — | moved |
| `blast_report_collection.py` | `blast_report_collection.py` | results | native_blast_database_result_worker, native_blast_hsp_views, native_blast_result_worker, native_blast_standard_database_result_worker | moved |
| `blast_result_views.py` | `blast_result_views.py` | results | alignment_site_action_records, alignment_site_native, api_service_execution, execution_episodes | moved |
| `blast_search.py` | `blast_search.py` | calculation | alignment_site_action_records, alignment_site_native, alignment_site_returns, blast_database_grader | moved |
| `blast_sequence_database.py` | `blast_sequence_database.py` | contracts | blast_vdb_calculators, native_blast_standard_database_metadata | moved |
| `blast_utility_contracts.py` | `blast_utility_contracts.py` | contracts | blast_database_extraction, blast_database_inspection, blast_database_preparation, blast_preparation_contracts | moved |
| `blast_utility_historical_fact_schemas.py` | `blast_utility_historical_fact_schemas.py` | contracts | communication | moved |
| `blast_utility_result_views.py` | `blast_utility_result_views.py` | results | communication, execution_episodes, execution_progress, native_blast_utility_capture_failure | moved |
| `blast_vdb_calculators.py` | `blast_vdb_calculators.py` | calculation | — | moved |
| `blast_vdb_function_calculators.py` | `blast_vdb_function_calculators.py` | calculation | native_blast_database_result_views, native_blast_database_result_worker | moved |
| `blast_vdb_function_inputs.py` | `blast_vdb_function_inputs.py` | contracts | native_blast_database_result_worker | moved |
| `blast_vdb_inputs.py` | `blast_vdb_inputs.py` | contracts | blast_vdb_calculators, blast_vdb_utility_inputs | moved |
| `blast_vdb_utility_contracts.py` | `blast_vdb_utility_contracts.py` | contracts | blast_utility_contracts, blast_utility_result_views, blast_vdb_utility_inputs, native_blast_utility_result_worker | moved |
| `blast_vdb_utility_inputs.py` | `blast_vdb_utility_inputs.py` | contracts | native_blast_utility_result_worker | moved |
| `hmmer_alignment_input_alphabet.py` | `hmmer_alignment_input_alphabet.py` | contracts | hmmer_alignment_input_validation, hmmer_alignment_preparation_data | moved |
| `hmmer_alignment_input_blocks.py` | `hmmer_alignment_input_blocks.py` | contracts | hmmer_alignment_preparation_data | moved |
| `hmmer_alignment_input_fasta.py` | `hmmer_alignment_input_fasta.py` | contracts | hmmer_alignment_preparation_data | moved |
| `hmmer_alignment_input_phylip.py` | `hmmer_alignment_input_phylip.py` | contracts | hmmer_alignment_preparation_data | moved |
| `hmmer_alignment_input_types.py` | `hmmer_alignment_input_types.py` | contracts | hmmer_alignment_input_alphabet, hmmer_alignment_input_blocks, hmmer_alignment_input_fasta, hmmer_alignment_input_phylip | moved |
| `hmmer_alignment_input_validation.py` | `hmmer_alignment_input_validation.py` | contracts | hmmer_alignment_preparation_calculations, hmmer_alignment_preparation_data, hmmer_preparation_result_views, native_hmmer_preparation_driver | moved |
| `hmmer_alignment_pb_sampling.py` | `hmmer_alignment_pb_sampling.py` | calculation | hmmer_alignment_preparation_calculations | moved |
| `hmmer_alignment_preparation_calculations.py` | `hmmer_alignment_preparation_calculations.py` | calculation | native_hmmer_preparation_driver, native_hmmer_preparation_result_worker | moved |
| `hmmer_alignment_preparation_data.py` | `hmmer_alignment_preparation_data.py` | contracts | hmmer_alignment_preparation_calculations, hmmer_preparation_result_views, native_hmmer_preparation_driver | moved |
| `hmmer_alignment_tree_weights.py` | `hmmer_alignment_tree_weights.py` | calculation | hmmer_alignment_preparation_calculations | moved |
| `hmmer_artifact_calculations.py` | `hmmer_artifact_calculations.py` | calculation | — | moved |
| `hmmer_artifact_data.py` | `hmmer_artifact_data.py` | contracts | hmmer_artifact_calculations | moved |
| `hmmer_emission_calculations.py` | `hmmer_emission_calculations.py` | calculation | — | moved |
| `hmmer_emission_data.py` | `hmmer_emission_data.py` | contracts | hmmer_emission_calculations | moved |
| `hmmer_fm_calculations.py` | `hmmer_fm_calculations.py` | calculation | — | moved |
| `hmmer_fm_data.py` | `hmmer_fm_data.py` | contracts | hmmer_fm_calculations, native_hmmer_preparation_acquisition, native_hmmer_preparation_driver | moved |
| `hmmer_graders.py` | `hmmer_graders.py` | grading | hmmer_native_result_views, homology_results, native_hmmer_result_worker, phmmer_grading_worker | moved |
| `hmmer_model_binary.py` | `hmmer_model_binary.py` | calculation | hmmer_model_binary2, hmmer_model_data | moved |
| `hmmer_model_binary2.py` | `hmmer_model_binary2.py` | calculation | hmmer_model_calculations, hmmer_model_data, hmmer_preparation_result_views | moved |
| `hmmer_model_calculations.py` | `hmmer_model_calculations.py` | calculation | hmmer_alignment_preparation_calculations, hmmer_artifact_calculations, hmmer_emission_calculations, hmmer_statistics_calculations | moved |
| `hmmer_model_data.py` | `hmmer_model_data.py` | contracts | hmmer_alignment_preparation_calculations, hmmer_alignment_preparation_data, hmmer_artifact_calculations, hmmer_artifact_data | moved |
| `hmmer_model_legacy.py` | `hmmer_model_legacy.py` | calculation | hmmer_model_data | moved |
| `hmmer_model_source_cells.py` | `hmmer_model_source_cells.py` | calculation | hmmer_model_binary, hmmer_model_binary2, hmmer_model_calculations, hmmer_model_legacy | moved |
| `hmmer_native_result_views.py` | `hmmer_native_result_views.py` | results | execution_episodes, execution_progress, native_hmmer_result_publication, native_hmmer_result_worker | moved |
| `hmmer_preparation_result_views.py` | `hmmer_preparation_result_views.py` | results | execution_episodes, execution_progress, native_hmmer_preparation_failure_views, native_hmmer_preparation_result_publication | moved |
| `hmmer_search_grader.py` | `hmmer_search_grader.py` | grading | hmmer_graders, native_hmmer_result_worker, phmmer_grading_worker | moved |
| `hmmer_search_inputs.py` | `hmmer_search_inputs.py` | contracts | hmmer_graders, hmmer_search_grader, native_hmmer_result_worker, phmmer_grading_worker | moved |
| `hmmer_simulation_calculations.py` | `hmmer_simulation_calculations.py` | calculation | — | moved |
| `hmmer_simulation_data.py` | `hmmer_simulation_data.py` | contracts | hmmer_simulation_calculations | moved |
| `hmmer_statistics_calculations.py` | `hmmer_statistics_calculations.py` | calculation | — | moved |
| `hmmer_statistics_data.py` | `hmmer_statistics_data.py` | contracts | hmmer_statistics_calculations | moved |
| `homology_episodes.py` | `homology_episodes.py` | episode | assembled_service_setup, case_execution, resource_episodes, runtime | moved |
| `homology_jobs.py` | `homology_jobs.py` | calculation | case_execution, episode_return_records, execution_expectations, execution_recording | moved |
| `homology_progress.py` | `homology_progress.py` | calculation | assembled_service_setup | moved |
| `homology_query.py` | `homology_query.py` | calculation | episode_return_records, homology_episodes, resource_information | moved |
| `homology_recovery.py` | `homology_recovery.py` | calculation | — | moved |
| `homology_results.py` | `homology_results.py` | results | homology_episodes, homology_recovery, resource_episodes, resource_information | moved |
| `native_blast_acquisition.py` | `native_blast_acquisition.py` | execution | execution_episodes, native_blast_result_publication, native_blast_results | moved |
| `native_blast_contracts.py` | `native_blast_contracts.py` | execution | blast_pairwise_result_views, blast_pairwise_results, blast_preparation_result_assembly, native_blast_acquisition | moved |
| `native_blast_database_acquisition.py` | `native_blast_database_acquisition.py` | execution | execution_episodes, native_blast_database_result_publication, native_blast_database_results | moved |
| `native_blast_database_contracts.py` | `native_blast_database_contracts.py` | execution | blast_database_preparation, blast_preparation_contracts, blast_utility_contracts, native_blast_database_acquisition | moved |
| `native_blast_database_convergence.py` | `native_blast_database_convergence.py` | execution | native_blast_database_metadata, native_blast_database_result_publication, native_blast_database_result_worker | moved |
| `native_blast_database_driver.py` | `native_blast_database_driver.py` | execution | native_blast_utility_driver | moved |
| `native_blast_database_metadata.py` | `native_blast_database_metadata.py` | execution | native_blast_database_population_metadata, native_blast_database_result_worker, native_blast_standard_database_contracts, native_blast_standard_database_metadata | moved |
| `native_blast_database_population_metadata.py` | `native_blast_database_population_metadata.py` | execution | native_blast_database_metadata, native_blast_database_result_worker, native_blast_standard_database_metadata | moved |
| `native_blast_database_result_publication.py` | `native_blast_database_result_publication.py` | results | alignment_site_native, blast_result_views, evidence_axis_contracts, evidence_geometry | moved |
| `native_blast_database_result_views.py` | `native_blast_database_result_views.py` | results | communication, execution_episodes, execution_progress, native_blast_database_result_publication | moved |
| `native_blast_database_result_worker.py` | `native_blast_database_result_worker.py` | results | native_blast_database_result_publication, native_blast_standard_database_calculators, native_blast_standard_database_result_worker | moved |
| `native_blast_database_results.py` | `native_blast_database_results.py` | results | execution_episodes, native_blast_database_returns | moved |
| `native_blast_database_returns.py` | `native_blast_database_returns.py` | results | execution_episodes | moved |
| `native_blast_database_tool_info.py` | `native_blast_database_tool_info.py` | execution | execution_episodes | moved |
| `native_blast_driver.py` | `native_blast_driver.py` | execution | native_blast_local, practical_execution_operations | moved |
| `native_blast_hsp_views.py` | `native_blast_hsp_views.py` | execution | alignment_site_native, blast_result_views | moved |
| `native_blast_local.py` | `native_blast_local.py` | execution | native_blast_acquisition, practical_execution_operations | moved |
| `native_blast_masking_acquisition.py` | `native_blast_masking_acquisition.py` | execution | execution_episodes, native_blast_masking_result_publication, native_blast_masking_result_worker, native_blast_masking_results | moved |
| `native_blast_masking_contracts.py` | `native_blast_masking_contracts.py` | execution | execution_progress, native_blast_masking_acquisition, native_blast_masking_driver, native_blast_masking_local | moved |
| `native_blast_masking_driver.py` | `native_blast_masking_driver.py` | execution | practical_execution_operations | moved |
| `native_blast_masking_local.py` | `native_blast_masking_local.py` | execution | native_blast_masking_acquisition, practical_execution_operations | moved |
| `native_blast_masking_result_publication.py` | `native_blast_masking_result_publication.py` | results | native_blast_masking_results | moved |
| `native_blast_masking_result_worker.py` | `native_blast_masking_result_worker.py` | results | native_blast_masking_result_publication | moved |
| `native_blast_masking_results.py` | `native_blast_masking_results.py` | results | execution_episodes | moved |
| `native_blast_masking_returns.py` | `native_blast_masking_returns.py` | results | execution_episodes | moved |
| `native_blast_masking_tool_info.py` | `native_blast_masking_tool_info.py` | execution | execution_episodes, practical_execution_operations | moved |
| `native_blast_result_publication.py` | `native_blast_result_publication.py` | results | native_blast_hsp_views, native_blast_results | moved |
| `native_blast_result_worker.py` | `native_blast_result_worker.py` | results | native_blast_hsp_views, native_blast_result_publication | moved |
| `native_blast_results.py` | `native_blast_results.py` | results | execution_episodes | moved |
| `native_blast_returns.py` | `native_blast_returns.py` | results | execution_episodes | moved |
| `native_blast_standard_database_acquisition.py` | `native_blast_standard_database_acquisition.py` | execution | execution_episodes, native_blast_standard_database_result_publication, native_blast_standard_database_results | moved |
| `native_blast_standard_database_calculators.py` | `native_blast_standard_database_calculators.py` | execution | native_blast_standard_database_result_publication | moved |
| `native_blast_standard_database_contracts.py` | `native_blast_standard_database_contracts.py` | execution | blast_database_preparation, blast_preparation_contracts, blast_preparation_population, blast_utility_contracts | moved |
| `native_blast_standard_database_driver.py` | `native_blast_standard_database_driver.py` | execution | — | moved |
| `native_blast_standard_database_metadata.py` | `native_blast_standard_database_metadata.py` | execution | native_blast_database_population_metadata, native_blast_standard_database_result_publication | moved |
| `native_blast_standard_database_result_publication.py` | `native_blast_standard_database_result_publication.py` | results | alignment_site_native, blast_result_views, evidence_axis_contracts, evidence_geometry | moved |
| `native_blast_standard_database_result_views.py` | `native_blast_standard_database_result_views.py` | results | communication, execution_episodes, execution_progress, native_blast_standard_database_result_publication | moved |
| `native_blast_standard_database_result_worker.py` | `native_blast_standard_database_result_worker.py` | results | native_blast_standard_database_result_publication | moved |
| `native_blast_standard_database_results.py` | `native_blast_standard_database_results.py` | results | execution_episodes, native_blast_standard_database_returns | moved |
| `native_blast_standard_database_returns.py` | `native_blast_standard_database_returns.py` | results | execution_episodes | moved |
| `native_blast_standard_database_tool_info.py` | `native_blast_standard_database_tool_info.py` | execution | execution_episodes | moved |
| `native_blast_tool_info.py` | `native_blast_tool_info.py` | execution | execution_episodes, practical_execution_operations | moved |
| `native_blast_utility_acquisition.py` | `native_blast_utility_acquisition.py` | execution | execution_episodes, native_blast_utility_capture_failure, native_blast_utility_result_publication, native_blast_utility_result_worker | moved |
| `native_blast_utility_capture_failure.py` | `native_blast_utility_capture_failure.py` | execution | native_blast_utility_results | moved |
| `native_blast_utility_contracts.py` | `native_blast_utility_contracts.py` | execution | episode_services, execution_progress, native_blast_utility_acquisition, native_blast_utility_capture_failure | moved |
| `native_blast_utility_driver.py` | `native_blast_utility_driver.py` | execution | practical_execution_operations | moved |
| `native_blast_utility_local.py` | `native_blast_utility_local.py` | execution | native_blast_utility_acquisition, practical_execution_operations | moved |
| `native_blast_utility_materializations.py` | `native_blast_utility_materializations.py` | execution | native_blast_utility_acquisition, native_blast_utility_contracts, native_blast_utility_driver | moved |
| `native_blast_utility_result_publication.py` | `native_blast_utility_result_publication.py` | results | native_blast_utility_results | moved |
| `native_blast_utility_result_worker.py` | `native_blast_utility_result_worker.py` | results | native_blast_utility_capture_failure, native_blast_utility_result_publication, native_blast_vdb_utility_context | moved |
| `native_blast_utility_results.py` | `native_blast_utility_results.py` | results | execution_episodes | moved |
| `native_blast_utility_returns.py` | `native_blast_utility_returns.py` | results | execution_episodes | moved |
| `native_blast_utility_tool_info.py` | `native_blast_utility_tool_info.py` | execution | execution_episodes, practical_execution_operations | moved |
| `native_blast_vdb_function_metadata.py` | `native_blast_vdb_function_metadata.py` | execution | native_blast_database_metadata, native_blast_database_result_worker | moved |
| `native_blast_vdb_utility_context.py` | `native_blast_vdb_utility_context.py` | execution | native_blast_utility_acquisition, native_blast_utility_contracts, native_blast_utility_driver, native_blast_utility_result_publication | moved |
| `native_blast_vdb_utility_execution.py` | `native_blast_vdb_utility_execution.py` | execution | native_blast_utility_contracts, native_blast_utility_driver | moved |
| `native_hmmer_acquisition.py` | `native_hmmer_acquisition.py` | execution | execution_episodes, native_hmmer_preparation_results, native_hmmer_results, native_infernal_preparation_results | moved |
| `native_hmmer_contracts.py` | `native_hmmer_contracts.py` | execution | hmmer_native_result_views, native_hmmer_acquisition, native_hmmer_driver, native_hmmer_local | moved |
| `native_hmmer_driver.py` | `native_hmmer_driver.py` | execution | — | moved |
| `native_hmmer_local.py` | `native_hmmer_local.py` | execution | native_hmmer_acquisition, practical_execution_operations | moved |
| `native_hmmer_preparation_acquisition.py` | `native_hmmer_preparation_acquisition.py` | execution | execution_episodes, native_blast_masking_acquisition, native_blast_masking_result_publication, native_blast_masking_result_worker | moved |
| `native_hmmer_preparation_contracts.py` | `native_hmmer_preparation_contracts.py` | execution | hmmer_preparation_result_views, native_hmmer_preparation_acquisition, native_hmmer_preparation_driver, native_hmmer_preparation_job_schema | moved |
| `native_hmmer_preparation_driver.py` | `native_hmmer_preparation_driver.py` | execution | native_hmmer_preparation_acquisition, native_hmmer_preparation_failure_views, native_hmmer_preparation_local, practical_execution_operations | moved |
| `native_hmmer_preparation_failure_views.py` | `native_hmmer_preparation_failure_views.py` | execution | native_hmmer_preparation_results | moved |
| `native_hmmer_preparation_job_schema.py` | `native_hmmer_preparation_job_schema.py` | execution | native_hmmer_preparation_tool_info, practical_execution_records | moved |
| `native_hmmer_preparation_local.py` | `native_hmmer_preparation_local.py` | execution | native_hmmer_preparation_acquisition, practical_execution_operations | moved |
| `native_hmmer_preparation_result_publication.py` | `native_hmmer_preparation_result_publication.py` | results | native_hmmer_preparation_results | moved |
| `native_hmmer_preparation_result_worker.py` | `native_hmmer_preparation_result_worker.py` | results | native_blast_masking_result_worker, native_blast_utility_result_worker, native_hmmer_preparation_result_publication, native_hmmer_preparation_results | moved |
| `native_hmmer_preparation_results.py` | `native_hmmer_preparation_results.py` | results | execution_episodes | moved |
| `native_hmmer_preparation_returns.py` | `native_hmmer_preparation_returns.py` | results | execution_episodes, runtime | moved |
| `native_hmmer_preparation_tool_info.py` | `native_hmmer_preparation_tool_info.py` | execution | execution_episodes, practical_execution_operations | moved |
| `native_hmmer_preparation_worker.py` | `native_hmmer_preparation_worker.py` | execution | native_hmmer_preparation_result_worker | moved |
| `native_hmmer_result_publication.py` | `native_hmmer_result_publication.py` | results | native_blast_database_result_publication, native_blast_result_publication, native_blast_standard_database_result_publication, native_hmmer_results | moved |
| `native_hmmer_result_worker.py` | `native_hmmer_result_worker.py` | results | — | moved |
| `native_hmmer_results.py` | `native_hmmer_results.py` | results | execution_episodes | moved |
| `native_hmmer_tool_info.py` | `native_hmmer_tool_info.py` | execution | execution_episodes, practical_execution_operations | moved |
| `phmmer_format.py` | `phmmer_format.py` | contracts | homology_results, phmmer_result_worker | moved |
| `phmmer_grading_worker.py` | `phmmer_grading_worker.py` | execution | homology_results, phmmer_result_worker | moved |
| `phmmer_result_worker.py` | `phmmer_result_worker.py` | results | — | moved |
| `resource_information.py` | `resource_information.py` | contracts | resource_episodes | moved |
| `bvbrc_homology_bundle_adapter.py` | `bvbrc_homology_bundle_adapter.py` | bundle_adapter | bvbrc_appservice_adapters, api_service_execution, A101 tests | moved |
| `bvbrc_homology_grader.py` | `bvbrc_homology_grader.py` | grader | bvbrc_appservice_adapters, api_service_execution, A101 tests | moved |
| `bvbrc_homology_inputs.py` | `bvbrc_homology_inputs.py` | inputs | bvbrc_appservice_adapters, api_service_execution, A101 tests | moved |
| `bvbrc_homology_metadata.py` | `bvbrc_homology_metadata.py` | metadata | bvbrc_appservice_adapters, api_service_execution, A101 tests | moved |
| `bvbrc_homology_returns.py` | `bvbrc_homology_returns.py` | returns | bvbrc_appservice_adapters, api_service_execution, A101 tests | moved |
| `bvbrc_homology_subject_binding.py` | `bvbrc_homology_subject_binding.py` | subject_binding | bvbrc_appservice_adapters, api_service_execution, A101 tests | moved |
| `bvbrc_homology_tool_info.py` | `bvbrc_homology_tool_info.py` | tool_info | bvbrc_appservice_adapters, api_service_execution, A101 tests | moved |

## Scientific process binding copy (2026-11-11)

| Original symbol | Destination | Axis | Role and caller | Change |
| --- | --- | --- | --- | --- |
| `scientific_process_episodes.py::ScientificProcessEpisodes` | `scientific_process_episode.py::ScientificProcessEpisode` | A101 | Scientific process binding; caller-specific setup and descriptor reopening | Copied into a singular private binding with axis-constrained assignment, local credit, guidance, fact, report and decision routes; generic package dependencies remain outside this axis. |

## Private terminal execution binding

| Original module or symbol | Destination | Applicable axis | Episode role and caller | Change |
| --- | --- | --- | --- | --- |
| terminal_execution_episodes.py, TerminalExecutionEpisodes | terminal_execution_episode.py, TerminalExecutionEpisode | A101 | Local or HPC launch command execution; this axis's execution episode and practical service factory | Copied and made singular |
| terminal_scientific_evidence.py | terminal_scientific_evidence.py | A101 | Source custody for this axis's applicable native command profiles | Copied and narrowed |
| practical_yield.py | practical_yield.py | A101 | Private command-result progress estimate | Copied |

## 2026-11-11 monitor binding split

| Original module and symbol | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| episode_monitoring.py: MonitorEpisodes | monitor_episode.py: MonitorEpisode | This axis's monitor binding, commissioned by its execution service | Copied and made axis-private; generic progress infrastructure remains in episode_monitoring.py |

## 2026-11-11 resource binding split

| Original module and symbols | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| resource_episodes.py: ResourceEpisodes | resource_episode.py: ResourceEpisode | This axis's resource launch/results binding | Copied and made axis-private; old plural owner removed |
| resource_records.py, launch_instructions.py | Same basenames under this axis | Resource assignment schemas and selected launch instructions | Copied for private resource binding |

## 2026-11-11 A101 execution helper split

| Original module or symbol | Destination | A101 use | Change |
| --- | --- | --- | --- |
| `hpc_episodes.py::authenticate_launch` | `hpc_launch_authentication.py` | Original HPC launch reservation authentication | Copied privately |
| `hpc_queue.py`, `hpc_ledger.py`, `hpc_prediction.py`, `hpc_resource_prediction.py` | Same basenames in `a101/` | Private HPC allocation and ledger helpers | Copied privately |
| `execution_input_versions.py` | `execution_input_versions.py` | Scope and content checks for A101 launch inputs | Copied and narrowed to A101 |
| BV-BRC proteome contract helpers | `bvbrc_proteome_tool_info.py`, `bvbrc_appservice_contracts.py`, `bvbrc_proteome_bundle_contracts.py`, `bvbrc_proteome_data_contracts.py`, `bvbrc_proteome_native_contracts.py`, `bvbrc_proteome_sheet_contracts.py` | A101 proteome tool descriptions | Copied privately |

## 2026-11-11 characterized-homolog source reading

| Original module and symbol | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| literature_episodes.py: source-reading LiteratureEpisodes methods | literature_episode.py: LiteratureEpisode | A101 source discovery and reading for characterized homolog evidence; assembled_service_setup binds the A101 owner | Copied and narrowed to A101; old mixed owner removed |

## 2026-11-11 A101 practical execution branches

| Original module or symbol | Destination | A101 role and caller | Change |
| --- | --- | --- | --- |
| Mixed practical execution operations and record contracts | `practical_execution_operations.py`, `practical_execution_records.py` | A101 practical actions, monitoring, completion and receipt interpretation | Private copies narrowed to generic execution, BLAST, HMMER, HMMER preparation, BLAST masking/utility and database request contracts; foreign scientific branches removed. Database execution remains in the existing A101 HPC path. Applicable retry, result observation, custody and progress hooks retained. |
| Native file receipt helpers formerly imported through the Infernal driver | `native_file_receipts.py` | A101 BLAST masking and utility sealed file custody | Copied only the applicable file helpers into A101; no Infernal dependency. |
| Execution inventory | `execution_inventory.py` | A101 practical inventory refresh | Private copy; no sibling fallback. |
| Generic file capture, receipt controls and received-file context | `local_file_capture_results.py`, `native_file_capture.py`, `received_native_file_inputs.py`, `file_capture_receipt_control.py` | A101 execution results and terminal source custody | Private generic copies without foreign LUMPY schemas/branches; direct local bindings. |

This change covers the listed practical and capture files only. Generic package infrastructure (Store/materials, binding/receipt services, local resource policy and process worker) remains outside A101; further split work outside this scope is not claimed complete. No Python, tests, imports or static validation were run. Combined-workflow integration and execution validation remain unperformed.

## 2026-11-11 A101 correspondence and received grading

| Original module or symbol | Destination | A101 role and caller | Change |
| --- | --- | --- | --- |
| `alignment_correspondence.py` | `alignment_correspondence.py` | A101 BLAST correspondence graders, calculators and native workers | Physical private copy; direct local imports and worker implementation inventory names. |
| `tool_grading_artifacts.py` | `tool_grading_artifacts.py` | A101 source grading custody, native result publication and sequence credit | Private copy using private correspondence and BLAST validation. |
| Saved Biopython correspondence validation/projection | `pairwise_source_correspondence.py` | Retained source grading reader | Applicable immutable-source validation copied; no alignment executor or whole new grading route added. |
| Native extent projection from `evidence_geometry.py` | `evidence_geometry.py` | A101 sequence credit and assessment lookup | Only merge/intersection/native-region projection copied; unrelated observation dispatch omitted. |
| Received assessment identity, revision, assignment and transfer helpers | `component_assessment_dependencies.py` | A101 credit assessment selection | Applicable helpers extracted with private extent projection; unrelated qualification dispatch omitted. |
| A101 contribution helpers in `root_axis_scalars.py` | `a101_contribution.py` | `a101_credit.py` | Private fixed-A101 scalar projection; no axis argument, axis switch or other-axis formula. |

A101 has no direct `sequence_attribution.py` caller, so no unused copy was introduced. Literature source operations still call the supplied services/tool dispatcher; that root service wiring is outside this edit and remains a separation task. Root `alignment_correspondence.py`, `tool_grading_artifacts.py`, `evidence_geometry.py` and assessment dependencies still have other callers and were not edited. No Python, tests or static validation ran.

## 2026-11-11 A101 standalone tool registry

| Original module or symbol | Destination | A101 role and caller | Change |
| --- | --- | --- | --- |
| `tools.py::ToolRegistry` | `tools.py::ToolRegistry` | A101 ordinary tools, execution registry hooks and characterized-homolog source reading | Standalone physical implementation; no shared-registry inheritance or forwarding. Retains original durable operation replay, partial publication, failure outcomes, sequence/BLAST/HMMER hooks, material/source/document reads and applicable public source acquisition. Foreign configured assay, structure, expression, variation, phylogeny, RNA/Infernal, context-calculation and chemical-provider dispatch removed. |
| `acquisition.py::PublicClients` and source response parsers | `acquisition.py` | A101 UniProt/NCBI/literature/PMC/BLAST/HMMER transport and native source parsing | Applicable client methods and parsers copied; unrelated provider endpoints removed. SourceSnapshot is private. Root AcquisitionError retained solely to interoperate with the existing local job boundary. |
| `provider_jobs.py` | `provider_jobs.py` | A101 retained BLAST remote handles and protocol collection | Private copy; RFAM submission/result branches removed. |
| Source location/sequence discovery, experimental source record projection, document/spreadsheet/image and UniProt/NCBI helpers | Corresponding private files plus `native_json.py` and `uniprot_service_support.py` | A101 source reader and acquisition result publication | Physical copies; direct private scientific imports. Native JSON token parsing extracted without UCSC behavior; UniProt service helpers omit foreign service dispatch. |
| Sequence operations/mapping/views, composition/translation/extraction and pairwise/site/minimap2 grading | Corresponding private files and `sequence_worker.py` | A101 sequence correspondence and preparation | Physical copies; private native worker launches only selected pairwise alignment; unrelated gene prediction and molecular worker branches removed. |

Registry implementation is separated, but construction in root workflow setup is a separate integration change. Root Store/material storage methods, record schemas/communication, local resource/job machinery, timing scope infrastructure and the common AcquisitionError type remain explicit dependencies; this entry does not claim their separation. No Python execution, tests, imports or static validation were performed.

## 2026-11-11 A101 production construction boundary

`create_a101_workflow` in `a101_investigation.py` receives its tool registry from its caller; no A101-specific production caller constructing that registry or `PublicClients` exists in the searched production launch/example paths. The private `tools.py` constructs its own private `PublicClients` when clients are omitted. Construction of the private registry by an actual A101 workflow launcher remains unresolved, not validated or silently routed through a shared default.

The generic CLI, `case_execution.py` and `independent_execution.py` still use the shared `build_tools` path. The fixed-case harness accepts arbitrary policy/service composition, so its unconditional homology helper does not make its registry constructor exclusively A101. The Aurora BLAST example explicitly excludes A101; the A101/A102 root mock is combined composition. Those callers were not rebound, and no axis switch or new workflow entry point was introduced. Combined runtime composition remains deferred. No tests or static validation were run.

The private `_source` metadata publisher was narrowed to this registry's actually enabled special source providers; copied unavailable-provider exceptions were removed. Native source versions and original source custody remain unchanged for applicable acquisitions.

## Private workflow service split — 2026-11-11

A101 now constructs its own `WorkflowServices` through `ToolRegistry.workflow_services`. `episode_services.py` retains source/tool dispatch, source-byte grants, original input receipts, progress, scientific credit and the original scientific result/provenance paths. It does not inherit from or forward to the root WorkflowServices. Foreign structure, assay, variant, restriction-mapping and MACS service branches and their copied scientific report hooks were removed from A101. Its alignment-site action records and returns are private copies.

`scientific_process_provenance.py`, `scientific_process_records.py`, `scientific_process_reports.py`, `scientific_support_metadata.py` and `resource_tool_information.py` are private copies used by this service/binding. Preparation reads use separate current-invocation and parent-invocation methods; the revision validator receives the explicit reader and expected path. It has no ownership selector. `received_input_frames.py` contains only original selection/form readers; `received_file_storage.py` contains only stable regular-file byte reading, with no flux dependency. Received source/file contracts and bindings are local copies.

Remaining root dependencies are explicit: application runtime construction and its projector/progress/native-event ports; Store/domain/communication and episode receipt/return infrastructure; original saved-frame transport decoding in runtime; native-file capture; source material windows; and scientific library/tool information/schema infrastructure referenced by these private copies. This edit does not claim that those remaining infrastructure dependencies have been split. Runtime wiring is handled separately. No tests, Python execution or static validation were run for this split.
# 2026-11-11: private A101 scientific libraries and instruction assets

The scientific episode, investigation constructor, scientific records/reports,
support metadata and resource tool-information callers now import private
`scientific_process_library.py`, `scientific_tool_library.py`,
`scientific_tool_retrieval.py`, `tool_information.py`,
`tool_schema_validation.py`, `evidence_axis_contracts.py` and
`evidence_axis_instructions.py`. The original library snapshot, source-row
identities, option digests, callable contracts, selected-tool resolution and
homology/alignment measurement semantics are retained in these copies.

The private tool library builds information only from its actual supplied
direct catalog and supplied resource catalogs. It no longer imports or injects
the root global API capability list. A101's existing native BLAST observation
validators resolve directly inside this directory.

`ScientificProcessEpisode.create_tool_retriever(store, *, run_id, provider,
configuration)` constructs the private retriever with its actual frozen
`self.tool_library`. The retriever retains original action identity, durable
request/outcome handling, provider failure information and release behavior.
Its request records identify the `invocation`, without an owner selector.
Provider parse failures retain their original raw response and diagnostic even
when the supplied provider declares its own boundary exception type.

Private `boundary_validation.py`, `schema_information_text.py`,
`schema_support.py` and `composition_information.py` retain the needed parsing,
schema rendering/traversal and composition-information behavior. Actual A101
callers import those copies; the resource binding fingerprints its local
composition/schema files. `execution_guidance.py` reads private copies of the
planning, API, local, HPC and homology execution instruction documents.

The A101 `knowledge/` manifest and exact referenced document bytes were copied
for its actual source, sequence, BLAST/HMMER, alignment and homology topics.
Gene-context and structural-homology entries were excluded. Its
`launch_instruction_library/` manifest and referenced API/local/Aurora documents
were copied with original source provenance. These document copies grant no
capabilities and introduce no scientific records. Root runtime knowledge/launch
construction and the retriever factory wiring are being handled separately;
private `ToolKnowledge` and the existing private `LaunchInstructions` are
available for that integration.

Residual shared dependencies are domain/communication and runtime protocol
types, decision-history information, numerical controllers, execution planning
and the externally supplied provider/store/journal. This entry does not claim
those boundaries have been split or that a workflow has been validated. No
tests, static validation, Python, workflow or job execution were run. This pass
did not edit A101 `episode_services.py`, `tools.py`, root runtime or another axis.


2026-11-11 runtime binding: this axis's tools.workflow_services now supplies its private service to runtime. Provenance, current tool invocation, instruction libraries, tool retrieval and semantic receipts are constructed through that service. Original runtime investigation/action-delivery and decision-exchange instructions are independent runtime_prompt.py/decision_protocol_prompt.py copies. Original tool_knowledge.py, launch_instructions.py, scientific_tool_retrieval.py, boundary_validation.py and episode_receipts.py have private implementations and direct callers. Imports of already-present local helpers were rebound directly. Root message parsing, Store/domain/communication, numerical/execution infrastructure and remaining helper dependencies are still open; no execution validation is claimed.

## Private message and schema parsing — 2026-11-11

A101 now has private communication/form-reference validation, contract-information expansion, schema information/support, boundary parsing and domain implementations. Production callers within A101 import those private copies, including its original canonical identities, record keys, sequence parsing and schema validation. The private closed-form parser retains BLAST database/utility/masking, file capture, UniProt and MinHash return validation; unrelated scientific return registries and restriction-selection expansion were removed. Masking and UniProt contracts and the MinHash view/contract/calculation dependencies are copied locally. A101 AppService return declarations now expose its homology and support receipts only.

The private domain and communication copies also define private error classes; root runtime error/validation routing is separate work. Root runtime was not copied or edited. Remaining root infrastructure includes binding context, receipt/store/runtime adapters and additional native/service dependencies outside these parsing copies. No tests, Python execution or static validation were run.

## Private runtime and admission — 2026-11-11

A101 has a full private `runtime.py`, `episode_bindings.py` and `episode_admission.py`; its Workflow constructors and original recorded-response readers now import those copies directly. Private return-record, composition, admission/completion, replay and report-acquisition readers keep the same local BindingContext and parsing/error types; none forwards to root runtime. Existing local modules supply runtime imports wherever present. A101 private information delivery retains its homology scoring views without importing other axes' scoring sheets.

Foreign protein report/attribution, restriction-reference and A110 reaction-return branches were removed. Local ownership selector/variable names were replaced with invocation/binding names, including separate current/parent preparation ports. The root Store's existing `account_owner` commit keyword remains an explicit external dependency because it forms saved interpretation-account identity; it is not an axis selector. Remaining root infrastructure imports, including Store/journal/provider/execution/decision helpers and some generic bootstrap construction, are explicit unfinished dependencies for later splitting. Root runtime and other axes were not edited. No tests, static validation or Python execution were run.

Interpretation-account owner removal is unfinished on both sides of the Store API. The existing account identity must be preserved when the private Store and matching commit signature are split; no compatibility alias or ownership enforcement was added. External execution reconstruction and the old scientific-default resume policy remain explicit dependencies. The private default-resume helper uses A101 runtime directly.

## 2026-11-11: private A101 Store, material intake and numerical primitives

A101 now has independent Store, material registration/parsing, gzip decoding,
GenBank intake, context masks and evidence geometry implementations. Its direct
application imports use those local implementations. Existing private source
locations, material packing, library targets and sequence mappings remain the
actual input/custody path. Store-required journal metadata and typed finding
validation were copied where absent. Original artifact identities, transactions,
record/reference validation, interpretation revisions, mapping and source input
semantics remain unchanged.

The geometry copy retains original homology/alignment/profile extents, exact
native mappings, operand coordinates, library-member dimensions and bounded
measurement handling. Native BLAST database validators bind to A101's existing
private implementations. Unavailable structure-match extent and Enrichr/molecular
capture special artifact branches were excluded; existing native grants and
source-input receipt readers remain intact.

Private `numerical.py`, `execution_timing.py`, `run_statistics.py` and vendored
numerical implementation/license/source metadata preserve their original
formulas, estimator parameters, measured progress semantics and receipt values.
`execution_recording.py`, `ordinary_execution.py`, `execution_expectations.py`
and `resource_estimation.py` were copied with them so execution classes,
homology statistics and native measurement type checks use consistent local
implementations. The original numerical provenance strings identify the
unchanged source revision; they do not import or execute the root vendor copy.

The active Store API and A101 application callers now use `account_invocation`.
Only the historical hash payload labels `owner` (interpretation account key)
and `account_owner` (reasoning signature) remain in that Store path to preserve
saved keys, revisions and replay signatures exactly. There is no axis selector
or new factory wrapper. Execution timing retains its original process-liveness
metadata pending a coordinated persisted-field rename; it is not axis routing.

Root journal/commission/application-service runtime imports still need their
separate private-runtime glue pass. Execution recording's atomic JSON writer
and execution-memory export remain infrastructure dependencies, as do existing
local execution/resource machinery, providers and remaining waiting/planning/
shared-information helpers. No full-workflow completion claim is made. No
tests, static checks, Python, workflow or job execution were run.

### A101 native and runtime dependency closure (2026-11-11)

A101 ordinary/native execution now uses matching private local_jobs, local_resources, native_lifecycle, execution_recording/statistics and worker types. Existing local ordinary_execution and native_lifecycle copies were retained and rebound; local configuration defaults and execution-memory implementation are available beside their readers. The local completion worker imports A101's statistics publisher with the repository import root. Original homology query/native job handling, resource bounds, source bytes and measurement formulas are unchanged.

Runtime journal, commissions, application-service operands, decision context/exchanges/history, pending assignment and closed episode report facts now have independent implementations. Production runtime/frame/helper callers, including completion/admission callers, use local WorkflowError and the same local BindingContext/Store/numerical types. A101 decision snapshots retain original instruction projection, history tables and delta frames; the unrelated Infernal receiver expansion was removed. Composition metadata uses local decision history, knowledge, launch and scientific library implementations. No root runtime wrapper or unused constructor was added.

Execution-memory defaults and native worker imports resolve to the repository after relocation. Root workflow resource enforcement/native event interfaces remain explicit dependencies, along with waiting and broader service setup/external libraries. No tests, Python, static validation, imports or workflow/HPC jobs were run.


## 2026-11-11 private waiting and episode-loop dependencies

- `waiting.py` → `a101/waiting.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `wait_estimation_inputs.py` → `a101/wait_estimation_inputs.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `local_return_history.py` → `a101/local_return_history.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `completion_evidence.py` → `a101/completion_evidence.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `inprocess_waiting.py` → `a101/inprocess_waiting.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `episode_monitoring.py` → `a101/episode_monitoring.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `progress_records.py` → `a101/progress_records.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `episode_source_failure.py` → `a101/episode_source_failure.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `episode_input_versions.py` → `a101/episode_input_versions.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `native_events.py` → `a101/native_events.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `native_event_information.py` → `a101/native_event_information.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.
- `workflow_budget.py` → `a101/workflow_budget.py`: independent applicable implementation for A101 runtime/frame/native progress callers; existing private copies retained.

A101 retains its actual homology job status/event reader, bound to its private HomologyJobs and resource schemas. The vendored `method_loop/` package and license/source manifests are copied to `a101/library/method_loop/`; production imports and durable child-worker commands bind directly to that private package. Original continuation, native observations and return identities are preserved. Provider/prompt/reconstruction and other helper separation remain unfinished. No tests or static checks were run.

2026-11-11 acquisition class placement correction: the earlier local `acquisition.py` self-import was replaced with its independent original `AcquisitionError` class, preserving the original fields and RuntimeError base. No execution validation was run.


## 2026-11-11 private provider and native helper dependencies

Provider/authentication and scientific/ordinary receiver/selected-execution/API/HPC/monitor prompts are now private. Original A101 work reports call the A101 adapter directly and retain the private legacy/current report schema projection. HMMER and HMMER preparation presentation remains; unrelated RNA, NMF, chemical, structure and assay dispatch is omitted. Alignment presentation has exact independent reference codecs. Own sequence scoring, characterizations, attachments and received BV-BRC values remain visible.

- `alignment_site_mapping.py` → `a101/alignment_site_mapping.py`: independently copied original applicable implementation, bound to A101 callers.
- `hmmalign_grader.py` → `a101/hmmalign_grader.py`: independently copied original applicable implementation, bound to A101 callers.
- `hmmalign_inputs.py` → `a101/hmmalign_inputs.py`: independently copied original applicable implementation, bound to A101 callers.
- `nhmmer_grader.py` → `a101/nhmmer_grader.py`: independently copied original applicable implementation, bound to A101 callers.
- `nhmmer_inputs.py` → `a101/nhmmer_inputs.py`: independently copied original applicable implementation, bound to A101 callers.
- `sequence_masking_calculations.py` → `a101/sequence_masking_calculations.py`: independently copied original applicable implementation, bound to A101 callers.
- `sequence_masking_inputs.py` → `a101/sequence_masking_inputs.py`: independently copied original applicable implementation, bound to A101 callers.
- `windowmasker_statistics.py` → `a101/windowmasker_statistics.py`: independently copied original applicable implementation, bound to A101 callers.
- `monitoring_credit.py` → `a101/monitoring_credit.py`: independently copied original applicable implementation, bound to A101 callers.
- `practical_execution_credit.py` → `a101/practical_execution_credit.py`: independently copied original applicable implementation, bound to A101 callers.
- `execution_progress.py` → `a101/execution_progress.py`: independently copied original applicable implementation, bound to A101 callers.
- `native_database_terminal_custody.py` → `a101/native_database_terminal_custody.py`: independently copied original applicable implementation, bound to A101 callers.
- `hpc_result_receipts.py` → `a101/hpc_result_receipts.py`: independently copied original applicable implementation, bound to A101 callers.
- `execution_planning.py` → `a101/execution_planning.py`: independently copied original applicable implementation, bound to A101 callers.
- `investigation_progress.py` → `a101/investigation_progress.py`: independently copied original applicable implementation, bound to A101 callers.

Original `native_infernal_contracts.py` finite JSON/digest primitives were separated into `native_record_identity.py`; required native attempt/file/scratch/identity helpers from `native_infernal_driver.py` are in `native_worker_files.py`. No Infernal execution is imported for these helpers. The original Python source/interpreter custody primitives from `native_atac_differential_contracts.py`, its driver and software modules are in `native_driver_runtime.py`, used directly by the HMMER preparation result worker without ATAC/MACS2 execution or software selection. `sequence_masking_calculations.py` carries its own original interval-ratio primitive. Foreign FBA/MACS2/LUMPY practical receipt branches and the A102 results-preparation branch were removed. Remaining API/AppService and construction dependencies are unfinished. No tests, static checks, Python or workflows were run.

## 2026-11-11 — A101 private API execution and custody

Root `api_service_execution.py` was split into A101-local HMMER/BLAST, UniProt and BV-BRC source/homology execution. Root AppService adapter installation, publication and application definitions now have independent A101 copies retaining Homology only; the corresponding native Homology specs and manifest are retained beside the private code. Foreign result resolvers and proteome catalog injection were removed from A101 `execution_episode.py`. A101 execution monitoring retains its actual BLAST/HMMER/preparation and API paths; RNA, structural, gene-overlap, FBA and other unrelated native branches were removed.

The copied root modules below serve A101 execution, source custody/publication, native monitoring or saved construction and are called directly by the private API service, execution episode, runtime and their local helpers. Their original basenames are preserved; none is a forwarding wrapper.

- `gene_annotation_episode/application_execution_binding.py` → `a101/application_execution_binding.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/independent_execution.py` → `a101/independent_execution.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/tool_configuration.py` → `a101/tool_configuration.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_service_execution.py` → `a101/api_service_execution.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_services.py` → `a101/api_services.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_bvbrc_appservice.py` → `a101/api_bvbrc_appservice.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_adapters.py` → `a101/bvbrc_appservice_adapters.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_publication.py` → `a101/bvbrc_appservice_publication.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/scientific_process_setup.py` → `a101/scientific_process_setup.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/episode_progress_credit.py` → `a101/episode_progress_credit.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_execution.py` → `a101/api_execution.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_selected_effects.py` → `a101/api_selected_effects.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_host.py` → `a101/bvbrc_data_host.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_minhash_host.py` → `a101/bvbrc_minhash_host.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_host.py` → `a101/bvbrc_appservice_host.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/uniprot_returns.py` → `a101/uniprot_returns.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_tool_info.py` → `a101/bvbrc_appservice_tool_info.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_records.py` → `a101/bvbrc_appservice_records.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_schema.py` → `a101/bvbrc_data_schema.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_blast.py` → `a101/api_blast.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_monitor.py` → `a101/bvbrc_appservice_monitor.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_publication.py` → `a101/bvbrc_data_publication.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_bvbrc_minhash.py` → `a101/api_bvbrc_minhash.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_bvbrc.py` → `a101/api_bvbrc.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_analysis_transport.py` → `a101/bvbrc_analysis_transport.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_application_definitions.py` → `a101/bvbrc_application_definitions.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_readers.py` → `a101/bvbrc_appservice_readers.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_bundle_values.py` → `a101/bvbrc_appservice_bundle_values.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_views.py` → `a101/bvbrc_data_views.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/api_selected_call.py` → `a101/api_selected_call.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_custody.py` → `a101/bvbrc_appservice_custody.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_inputs.py` → `a101/bvbrc_appservice_inputs.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_appservice_receipt_values.py` → `a101/bvbrc_appservice_receipt_values.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/uniprot_return_projection.py` → `a101/uniprot_return_projection.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_calculators.py` → `a101/bvbrc_data_calculators.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_feature_sequences.py` → `a101/bvbrc_data_feature_sequences.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_fields.py` → `a101/bvbrc_data_fields.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_molecular.py` → `a101/bvbrc_data_molecular.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_query.py` → `a101/bvbrc_data_query.py` (copied/split; private execution or construction dependency).
- `gene_annotation_episode/bvbrc_data_readers.py` → `a101/bvbrc_data_readers.py` (copied/split; private execution or construction dependency).

`episode_composition.py` retains exact descriptor identity and its existing explicit private reopening failure; the copied mixed implementation-compatibility list was removed. A101 workflow resource construction remains caller-supplied. Active local `owner` parameters and AppService context-reader methods now describe original context directly. Historical receipt/schema keys such as `original_job_owner` and `owner_episode_id` remain literal custody identities, not axis selection; changing these would rewrite existing hashed evidence. The combined root path remains incomplete. No tests, parse/import checks or workflows were run.

A101 adapter fingerprints read only private dependency bytes; the root source-file fallback was removed. Controller descriptors, monitoring implementation references and the HMMER preparation worker program now name their private A101 implementation paths directly.

A101 standalone `native_record_identity.py` and `native_worker_files.py` helpers now live in `a101/library/`: multiple BLAST masking/utility and HMMER preparation tasks use these exact digest/file/scratch primitives. Their callers and embedded worker imports bind directly to those private library files. Graders, request/return bindings and the single preparation runtime-custody helper stay beside their tasks. This supersedes the earlier top-level destinations for these two extracted helpers.

2026-11-11 numerical-source retirement: this axis's numerical provenance names
its own private vendor source and MIT license. Its private numerical/timing
implementations and source manifest retain the original estimator, receipt-time
semantics and formulas. Former shared numerical/timing implementation paths were
retired; no tests or execution were run.

2026-11-11: native BLAST implementation inventories and the separate publication subprocess now load only this axis's qualified private modules, including its own `domain` and alignment correspondence helpers. Removed the old name-prefix switch that selected top-level helpers. The embedded subprocess uses an absolute private worker import; native byte/scoring logic is unchanged.

2026-11-11 API-original retirement: original mixed API/AppService behavioral
modules were removed after private callers were bound. Applicable private
publication predicates and parser-module descriptions were narrowed, with exact
original custody and outcome semantics retained. Full original-to-private mapping
is recorded in root/ownership.md. No tests or execution were run.

## 2026-11-11 — Additional original-module placements

This supplement records original modules not named individually above. It maps their complete applicable module contents, including methods and constants; previous symbol-specific narrowing notes remain authoritative. Callers listed here are direct private imports or qualified worker module references, not execution receipts. It does not claim runtime validation.

| Original module/symbols | Destination | Current role/caller | Change |
|---|---|---|---|
| `gene_annotation_episode/_local_job_worker.py` (module contents) | `a101/_local_job_worker.py` | Private dependency used by `execution_recording.py`, `homology_jobs.py`, `homology_results.py`, `local_jobs.py`, `native_blast_driver.py`, `native_events.py`, `native_hmmer_driver.py`, `native_lifecycle.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_result_presentation.py` (module contents) | `a101/alignment_result_presentation.py` | Private dependency used by `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_action_records.py` (module contents) | `a101/alignment_site_action_records.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_calculators.py` (module contents) | `a101/alignment_site_calculators.py` | Private dependency used by `alignment_site_native.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_inputs.py` (module contents) | `a101/alignment_site_inputs.py` | Private dependency used by `alignment_site_calculators.py`, `alignment_site_native.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_native.py` (module contents) | `a101/alignment_site_native.py` | Private dependency used by `alignment_site_action_records.py`, `blast_result_views.py`, `episode_return_records.py`, `native_blast_database_result_publication.py`, `native_blast_hsp_views.py`, `native_blast_standard_database_result_publication.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_returns.py` (module contents) | `a101/alignment_site_returns.py` | Private dependency used by `alignment_site_action_records.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_error_feedback.py` (module contents) | `a101/api_error_feedback.py` | Private dependency used by `api_execution.py`, `api_service_execution.py`, `episode_work_report.py`, `execution_prompt.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_uniprot.py` (module contents) | `a101/api_uniprot.py` | Private dependency used by `api_services.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/biopython_pairwise_grader.py` (module contents) | `a101/biopython_pairwise_grader.py` | Private dependency used by `alignment_site_inputs.py`, `alignment_site_native.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_analysis_protocol.py` (module contents) | `a101/bvbrc_analysis_protocol.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py`, `bvbrc_analysis_transport.py`, `bvbrc_application_definitions.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_readers.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_minhash_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_contracts.py` (module contents) | `a101/bvbrc_minhash_contracts.py` | Private dependency used by `api_bvbrc_minhash.py`, `api_service_execution.py`, `bvbrc_minhash_host.py`, `bvbrc_minhash_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_grader.py` (module contents) | `a101/bvbrc_minhash_grader.py` | Private dependency used by `api_bvbrc_minhash.py`, `bvbrc_minhash_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_views.py` (module contents) | `a101/bvbrc_minhash_views.py` | Private dependency used by `bvbrc_minhash_host.py`, `communication.py`, `execution_episode.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/communication.py` (module contents) | `a101/communication.py` | Private dependency used by `a101_blast_execution.py`, `a101_contribution.py`, `a101_homology_resource_adapter.py`, `a101_investigation.py`, `alignment_site_action_records.py`, `alignment_site_native.py`, `alignment_site_returns.py`, `api_execution.py`, `api_selected_call.py`, `api_service_execution.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_monitor.py`, `bvbrc_appservice_publication.py`, `bvbrc_appservice_records.py`, `bvbrc_data_host.py`, `bvbrc_data_views.py`, `bvbrc_homology_returns.py`, `bvbrc_minhash_host.py`, `episode_admission.py`, `episode_contract_information.py`, `episode_monitoring.py`, `episode_return_records.py`, `episode_services.py`, `execution_contracts.py`, `execution_episode.py`, `execution_input_versions.py`, `execution_progress.py`, `homology_episode.py`, `homology_jobs.py`, `homology_progress.py`, `hpc_launch_authentication.py`, `hpc_result_receipts.py`, `literature_episode.py`, `local_file_capture_results.py`, `local_return_history.py`, `molecular_sequence_input_bindings.py`, `monitor_episode.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_database_returns.py`, `native_blast_masking_results.py`, `native_blast_masking_returns.py`, `native_blast_results.py`, `native_blast_returns.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_standard_database_returns.py`, `native_blast_utility_results.py`, `native_blast_utility_returns.py`, `native_event_information.py`, `native_hmmer_preparation_results.py`, `native_hmmer_preparation_returns.py`, `native_hmmer_results.py`, `native_profile_presentation.py`, `native_timing_information.py`, `pending_assignment.py`, `practical_receipt_information.py`, `progress_records.py`, `received_input_frames.py`, `received_native_file_inputs.py`, `resource_episode.py`, `resource_estimation.py`, `resource_information.py`, `resource_records.py`, `resource_tool_information.py`, `runtime.py`, `scientific_process_episode.py`, `scientific_process_provenance.py`, `scientific_process_reports.py`, `shared_information.py`, `terminal_execution_episode.py`, `terminal_scientific_evidence.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/context_masks.py` (module contents) | `a101/context_masks.py` | Private dependency used by `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_context.py` (module contents) | `a101/decision_context.py` | Private dependency used by `providers.py`, `runtime.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_exchanges.py` (module contents) | `a101/decision_exchanges.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_history.py` (module contents) | `a101/decision_history.py` | Private dependency used by `composition_information.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/default_scientific_binding.py` (module contents) | `a101/default_scientific_binding.py` | Private dependency used by `application_execution_binding.py`, `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/document_tools.py` (module contents) | `a101/document_tools.py` | Private dependency used by `spreadsheet_tools.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/domain.py` (module contents) | `a101/domain.py` | Private dependency used by `a101_homology_resource_adapter.py`, `a101_investigation.py`, `acquisition.py`, `alignment_site_action_records.py`, `alignment_site_native.py`, `api_bvbrc.py`, `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py`, `api_execution.py`, `api_service_execution.py`, `api_services.py`, `blast_database_extraction.py`, `blast_database_inspection.py`, `blast_database_preparation.py`, `blast_fasta_record_identity.py`, `blast_maskinfo_inputs.py`, `blast_pairwise_result_views.py`, `blast_preparation_contracts.py`, `blast_preparation_inputs.py`, `blast_result_views.py`, `blast_utility_contracts.py`, `blast_utility_result_views.py`, `blast_vdb_utility_contracts.py`, `blast_vdb_utility_inputs.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_monitor.py`, `bvbrc_appservice_records.py`, `bvbrc_data_host.py`, `bvbrc_data_publication.py`, `bvbrc_data_query.py`, `bvbrc_minhash_host.py`, `bvbrc_minhash_views.py`, `completion_evidence.py`, `context_masks.py`, `document_tools.py`, `episode_admission.py`, `episode_bindings.py`, `episode_commissions.py`, `episode_composition.py`, `episode_input_versions.py`, `episode_monitoring.py`, `episode_return_records.py`, `episode_services.py`, `evidence_axis_contracts.py`, `evidence_geometry.py`, `execution_episode.py`, `execution_progress.py`, `experimental_database_acquisition.py`, `experimental_database_records.py`, `finding_validity.py`, `genbank_intake.py`, `hmmer_native_result_views.py`, `hmmer_preparation_result_views.py`, `homology_episode.py`, `homology_jobs.py`, `homology_progress.py`, `homology_results.py`, `hpc_result_receipts.py`, `image_evidence.py`, `independent_execution.py`, `investigation_progress.py`, `library_targets.py`, `literature_assets.py`, `literature_episode.py`, `literature_sequence_discovery.py`, `local_file_capture_results.py`, `material_parsing.py`, `materials.py`, `materials_packing.py`, `molecular_sequence_input_bindings.py`, `monitor_episode.py`, `native_blast_acquisition.py`, `native_blast_database_acquisition.py`, `native_blast_database_metadata.py`, `native_blast_database_result_publication.py`, `native_blast_database_result_views.py`, `native_blast_database_result_worker.py`, `native_blast_database_results.py`, `native_blast_database_returns.py`, `native_blast_hsp_views.py`, `native_blast_masking_contracts.py`, `native_blast_masking_result_publication.py`, `native_blast_masking_result_worker.py`, `native_blast_masking_results.py`, `native_blast_result_publication.py`, `native_blast_result_worker.py`, `native_blast_results.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_calculators.py`, `native_blast_standard_database_metadata.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_result_views.py`, `native_blast_standard_database_result_worker.py`, `native_blast_standard_database_results.py`, `native_blast_utility_capture_failure.py`, `native_blast_utility_contracts.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_result_worker.py`, `native_blast_utility_results.py`, `native_blast_vdb_utility_context.py`, `native_blast_vdb_utility_execution.py`, `native_database_terminal_custody.py`, `native_file_capture.py`, `native_hmmer_acquisition.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_failure_views.py`, `native_hmmer_preparation_result_publication.py`, `native_hmmer_preparation_result_worker.py`, `native_hmmer_preparation_results.py`, `native_hmmer_result_publication.py`, `native_hmmer_results.py`, `native_profile_presentation.py`, `native_timing_information.py`, `practical_receipt_information.py`, `progress_records.py`, `provider_jobs.py`, `read_mapping.py`, `received_native_file_inputs.py`, `resource_episode.py`, `resource_information.py`, `runtime.py`, `scientific_findings.py`, `scientific_process_episode.py`, `scientific_process_provenance.py`, `scientific_process_records.py`, `scientific_process_reports.py`, `scientific_support_metadata.py`, `scientific_tool_retrieval.py`, `sequence_masking_contracts.py`, `sequence_masking_inputs.py`, `sequence_masking_result_views.py`, `shared_information.py`, `source_locations.py`, `source_sequences.py`, `state.py`, `terminal_execution_episode.py`, `tool_grading_artifacts.py`, `tools.py`, `uniprot_publication.py`, `uniprot_returns.py`, `uniprot_service_support.py`, `windowmasker_statistics.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_application_services.py` (module contents) | `a101/episode_application_services.py` | Private dependency used by `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_commissions.py` (module contents) | `a101/episode_commissions.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_completion.py` (module contents) | `a101/episode_completion.py` | Private dependency used by `completion_evidence.py`, `decision_history.py`, `episode_admission.py`, `inprocess_replay.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_contract_information.py` (module contents) | `a101/episode_contract_information.py` | Private dependency used by `bvbrc_appservice_custody.py`, `episode_return_records.py`, `received_input_frames.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_journal.py` (module contents) | `a101/episode_journal.py` | Private dependency used by `bvbrc_appservice_custody.py`, `completion_evidence.py`, `decision_exchanges.py`, `decision_history.py`, `episode_admission.py`, `episode_commissions.py`, `episode_completion.py`, `episode_report_acquisition.py`, `inprocess_replay.py`, `received_input_frames.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_report_acquisition.py` (module contents) | `a101/episode_report_acquisition.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_reports.py` (module contents) | `a101/episode_reports.py` | Private dependency used by `runtime.py`, `scientific_process_reports.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_return_records.py` (module contents) | `a101/episode_return_records.py` | Private dependency used by `alignment_site_action_records.py`, `alignment_site_native.py`, `api_service_execution.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_records.py`, `bvbrc_data_host.py`, `bvbrc_homology_returns.py`, `bvbrc_minhash_host.py`, `episode_services.py`, `execution_episode.py`, `hpc_result_receipts.py`, `inprocess_replay.py`, `local_file_capture_results.py`, `molecular_sequence_input_bindings.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_database_returns.py`, `native_blast_hsp_views.py`, `native_blast_masking_returns.py`, `native_blast_results.py`, `native_blast_returns.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_standard_database_returns.py`, `native_blast_utility_returns.py`, `native_hmmer_preparation_returns.py`, `received_input_frames.py`, `received_native_file_inputs.py`, `runtime.py`, `scientific_process_episode.py`, `shared_information.py`, `terminal_scientific_evidence.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_work_report.py` (module contents) | `a101/episode_work_report.py` | Private dependency used by `execution_prompt.py`, `hpc_prompt.py`, `monitor_prompt.py`, `runtime.py`, `scientific_process_prompt.py`, `shared_information_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_memory.py` (module contents) | `a101/execution_memory.py` | Private dependency used by `execution_planning.py`, `execution_recording.py`, `native_lifecycle.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_prompt.py` (module contents) | `a101/execution_prompt.py` | Private dependency used by `providers.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/experimental_database_acquisition.py` (module contents) | `a101/experimental_database_acquisition.py` | Private dependency used by `experimental_database_records.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/experimental_database_records.py` (module contents) | `a101/experimental_database_records.py` | Private dependency used by `experimental_database_acquisition.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/finding_validity.py` (module contents) | `a101/finding_validity.py` | Private dependency used by `investigation_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/form_reference_validation.py` (module contents) | `a101/form_reference_validation.py` | Private dependency used by `communication.py`, `native_blast_database_results.py`, `native_blast_database_returns.py`, `native_blast_masking_results.py`, `native_blast_masking_returns.py`, `native_blast_results.py`, `native_blast_returns.py`, `native_blast_standard_database_results.py`, `native_blast_standard_database_returns.py`, `native_blast_utility_contracts.py`, `native_blast_utility_results.py`, `native_blast_utility_returns.py`, `native_hmmer_preparation_results.py`, `native_hmmer_preparation_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/genbank_intake.py` (module contents) | `a101/genbank_intake.py` | Private dependency used by `material_parsing.py`, `materials.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_prompt.py` (module contents) | `a101/hpc_prompt.py` | Private dependency used by `providers.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/image_evidence.py` (module contents) | `a101/image_evidence.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/inprocess_replay.py` (module contents) | `a101/inprocess_replay.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/journal_metadata.py` (module contents) | `a101/journal_metadata.py` | Private dependency used by `episode_journal.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/library_targets.py` (module contents) | `a101/library_targets.py` | Private dependency used by `alignment_site_native.py`, `context_masks.py`, `materials.py`, `state.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_assets.py` (module contents) | `a101/literature_assets.py` | Private dependency used by `acquisition.py`, `state.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_sequence_discovery.py` (module contents) | `a101/literature_sequence_discovery.py` | Private dependency used by `source_sequences.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_jobs.py` (module contents) | `a101/local_jobs.py` | Private dependency used by `document_tools.py`, `homology_episode.py`, `homology_jobs.py`, `homology_recovery.py`, `homology_results.py`, `native_blast_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_driver.py`, `native_blast_local.py`, `native_blast_masking_contracts.py`, `native_blast_masking_local.py`, `native_blast_masking_result_publication.py`, `native_blast_masking_results.py`, `native_blast_result_publication.py`, `native_blast_results.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_utility_contracts.py`, `native_blast_utility_local.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_results.py`, `native_driver_runtime.py`, `native_hmmer_driver.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_driver.py`, `native_hmmer_preparation_local.py`, `native_hmmer_preparation_result_publication.py`, `native_hmmer_preparation_results.py`, `native_hmmer_result_publication.py`, `native_hmmer_results.py`, `native_lifecycle.py`, `practical_execution_operations.py`, `read_mapping.py`, `spreadsheet_tools.py`, `terminal_execution.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_resources.py` (module contents) | `a101/local_resources.py` | Private dependency used by `a101_homology_resource_adapter.py`, `native_lifecycle.py`, `resource_episode.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/material_gzip.py` (module contents) | `a101/material_gzip.py` | Private dependency used by `materials.py` | Copied/split; private implementation |
| `gene_annotation_episode/material_parsing.py` (module contents) | `a101/material_parsing.py` | Private dependency used by `materials.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/materials.py` (module contents) | `a101/materials.py` | Private dependency used by `a101_homology_resource_adapter.py`, `alignment_site_native.py`, `episode_services.py`, `homology_episode.py`, `homology_results.py`, `image_evidence.py`, `library_targets.py`, `local_file_capture_results.py`, `materials_packing.py`, `molecular_sequence_input_bindings.py`, `native_blast_acquisition.py`, `native_blast_database_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_hsp_views.py`, `native_blast_result_publication.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_event_information.py`, `native_file_capture.py`, `native_hmmer_acquisition.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_result_publication.py`, `resource_information.py`, `state.py`, `terminal_scientific_evidence.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/materials_packing.py` (module contents) | `a101/materials_packing.py` | Private dependency used by `alignment_site_native.py`, `library_targets.py`, `materials.py`, `native_hmmer_result_publication.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/minimap2_grader.py` (module contents) | `a101/minimap2_grader.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/minimap2_grading_inputs.py` (module contents) | `a101/minimap2_grading_inputs.py` | Private dependency used by `alignment_site_action_records.py`, `alignment_site_inputs.py`, `alignment_site_mapping.py`, `alignment_site_native.py`, `blast_hsp_site_inputs.py`, `minimap2_grader.py`, `read_mapping.py` | Copied/split; private implementation |
| `gene_annotation_episode/molecular_sequence_input_bindings.py` (module contents) | `a101/molecular_sequence_input_bindings.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/molecular_sequence_input_contracts.py` (module contents) | `a101/molecular_sequence_input_contracts.py` | Private dependency used by `bvbrc_data_host.py`, `molecular_sequence_input_bindings.py` | Copied/split; private implementation |
| `gene_annotation_episode/monitor_prompt.py` (module contents) | `a101/monitor_prompt.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_profile_presentation.py` (module contents) | `a101/native_profile_presentation.py` | Private dependency used by `execution_episode.py`, `providers.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_timing_information.py` (module contents) | `a101/native_timing_information.py` | Private dependency used by `homology_episode.py`, `independent_execution.py`, `runtime.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/ncbi_entrez_acquisition.py` (module contents) | `a101/ncbi_entrez_acquisition.py` | Private dependency used by `ncbi_entrez_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/ncbi_entrez_tools.py` (module contents) | `a101/ncbi_entrez_tools.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/pending_assignment.py` (module contents) | `a101/pending_assignment.py` | Private dependency used by `episode_commissions.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/provider_authentication.py` (module contents) | `a101/provider_authentication.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/providers.py` (module contents) | `a101/providers.py` | Private dependency used by `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/public_configuration.py` (module contents) | `a101/public_configuration.py` | Private dependency used by `acquisition.py`, `tool_configuration.py` | Copied/split; private implementation |
| `gene_annotation_episode/read_mapping.py` (module contents) | `a101/read_mapping.py` | Private dependency used by `runtime.py`, `state.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_findings.py` (module contents) | `a101/scientific_findings.py` | Private dependency used by `finding_validity.py`, `investigation_progress.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_prompt.py` (module contents) | `a101/scientific_process_prompt.py` | Private dependency used by `execution_prompt.py`, `providers.py`, `receiver_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_composition_counts.py` (module contents) | `a101/sequence_composition_counts.py` | Private dependency used by `sequence_composition_grader.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_composition_grader.py` (module contents) | `a101/sequence_composition_grader.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_extraction_grader.py` (module contents) | `a101/sequence_extraction_grader.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_mapping.py` (module contents) | `a101/sequence_mapping.py` | Private dependency used by `alignment_site_mapping.py`, `sequence_extraction_grader.py`, `sequence_translation_grader.py`, `state.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_contracts.py` (module contents) | `a101/sequence_masking_contracts.py` | Private dependency used by `blast_maskinfo_inputs.py`, `native_blast_masking_contracts.py`, `native_blast_masking_driver.py`, `native_blast_masking_result_publication.py`, `native_blast_masking_result_worker.py`, `native_blast_masking_results.py`, `native_blast_masking_tool_info.py`, `sequence_masking_calculations.py`, `sequence_masking_inputs.py`, `sequence_masking_result_views.py`, `windowmasker_statistics.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_result_views.py` (module contents) | `a101/sequence_masking_result_views.py` | Private dependency used by `a101_execution_bindings.py`, `communication.py`, `execution_episode.py`, `execution_progress.py`, `native_blast_masking_result_publication.py`, `native_blast_masking_result_worker.py`, `native_blast_masking_results.py`, `native_blast_masking_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_ops.py` (module contents) | `a101/sequence_ops.py` | Private dependency used by `ordinary_execution.py`, `sequence_worker.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_translation_grader.py` (module contents) | `a101/sequence_translation_grader.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_views.py` (module contents) | `a101/sequence_views.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information.py` (module contents) | `a101/shared_information.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information_results.py` (module contents) | `a101/shared_information_results.py` | Private dependency used by `episode_work_report.py`, `runtime.py`, `shared_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/source_locations.py` (module contents) | `a101/source_locations.py` | Private dependency used by `episode_services.py`, `experimental_database_records.py`, `literature_sequence_discovery.py`, `source_sequences.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/source_sequences.py` (module contents) | `a101/source_sequences.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/spreadsheet_tools.py` (module contents) | `a101/spreadsheet_tools.py` | Private dependency used by `ordinary_execution.py`, `spreadsheet_worker.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/spreadsheet_worker.py` (module contents) | `a101/spreadsheet_worker.py` | Private dependency used by `spreadsheet_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_native.py` (module contents) | `a101/uniprot_native.py` | Private dependency used by `acquisition.py`, `api_uniprot.py`, `tools.py`, `uniprot_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_native_contracts.py` (module contents) | `a101/uniprot_native_contracts.py` | Private dependency used by `uniprot_native.py`, `uniprot_publication.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_publication.py` (module contents) | `a101/uniprot_publication.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_return_contracts.py` (module contents) | `a101/uniprot_return_contracts.py` | Private dependency used by `communication.py`, `episode_contract_information.py`, `execution_episode.py`, `uniprot_return_projection.py`, `uniprot_returns.py` | Copied/split; private implementation |

2026-11-11 placement closure: `hpc_campaign.py:timestamp,memory_bytes` are extracted into private `hpc_resource_fields.py`, used by `hpc_resource_prediction.pbs_resource_metrics`; no campaign configuration/controller was copied for this field reader. BLAST implementation inventories now name the private A101 domain module with no top-level exception. Masking/parser descriptors name their existing A101 files. No algorithm or resource bounds changed.

2026-11-11: the private vendored numerical template now imports its completion/end-state types from this package's independent `library/method_loop/`, not the top-level repository loop. Upstream numerical code and constants are unchanged; this is the local import-placement patch.

## 2026-11-11 iterator package placement

Moved the independently copied `library/method_loop/` package to `method_loop/` beside the private workflow code. It contains episode bindings, continuation and return mechanics, so it is outside the standalone-helper library. Direct imports and durable-worker module paths now name this private location; the worker package-root depth follows the moved files. Original license and provenance manifests remain with the copy. No runtime behavior or stopping rule was added.

### 2026-11-11: retained helper physical placement

Moved `library/homology_search_receipt.py` intact to `homology_search_receipt.py` and rebound the private caller (homology_recovery.search_receipt use). This receipt-binding helper serves one task and therefore does not belong in `library/`. No receipt/hash changes or execution claim.

### 2026-11-11: retained GenomeComparison extension physically separated

Existing A101 proteome tool-description and contract copies referred to original GenomeComparison schema assets and pure projection/calculation helpers still outside A101. Their original implementation/assets are now independent A101 files below. Existing contract files were retained; no service/adapter registration, combined host, saved-reopening glue or new scientific policy was added. These are retained callable extensions, not a claim of an active A101 workflow capability. The v2 implementation digest reads only A101 files, including the existing local BLAST geometry helpers.

| Original top-level file | Independent A101 destination | Role/disposition |
| --- | --- | --- |
| `bvbrc_proteome_bundle_adapter.py` | `a101/bvbrc_proteome_bundle_adapter.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_bundle_adapter_v2.py` | `a101/bvbrc_proteome_bundle_adapter_v2.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_bundle_projection.py` | `a101/bvbrc_proteome_bundle_projection.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_bundle_resolution.py` | `a101/bvbrc_proteome_bundle_resolution.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_bundle_schemas.json` | `a101/bvbrc_proteome_bundle_schemas.json` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_bundle_v2_contracts.py` | `a101/bvbrc_proteome_bundle_v2_contracts.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_bundle_v2_resolution.py` | `a101/bvbrc_proteome_bundle_v2_resolution.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_bundle_v2_schemas.json` | `a101/bvbrc_proteome_bundle_v2_schemas.json` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_calculators.py` | `a101/bvbrc_proteome_calculators.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_data_schemas.json` | `a101/bvbrc_proteome_data_schemas.json` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional.py` | `a101/bvbrc_proteome_directional.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_calculators.py` | `a101/bvbrc_proteome_directional_calculators.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_contracts.py` | `a101/bvbrc_proteome_directional_contracts.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_fact_contracts.py` | `a101/bvbrc_proteome_directional_fact_contracts.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_geometry.py` | `a101/bvbrc_proteome_directional_geometry.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_numerical_contracts.py` | `a101/bvbrc_proteome_directional_numerical_contracts.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_numerical_schemas.json` | `a101/bvbrc_proteome_directional_numerical_schemas.json` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_projection.py` | `a101/bvbrc_proteome_directional_projection.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_saved_validation.py` | `a101/bvbrc_proteome_directional_saved_validation.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_schemas.json` | `a101/bvbrc_proteome_directional_schemas.json` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_directional_sheet.py` | `a101/bvbrc_proteome_directional_sheet.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_fact_contracts.py` | `a101/bvbrc_proteome_fact_contracts.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_inputs.py` | `a101/bvbrc_proteome_inputs.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_joins.py` | `a101/bvbrc_proteome_joins.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_native.py` | `a101/bvbrc_proteome_native.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_native_schemas.json` | `a101/bvbrc_proteome_native_schemas.json` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_numerical_sheet.py` | `a101/bvbrc_proteome_numerical_sheet.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_returns.py` | `a101/bvbrc_proteome_returns.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_sheet.py` | `a101/bvbrc_proteome_sheet.py` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |
| `bvbrc_proteome_sheet_schemas.json` | `a101/bvbrc_proteome_sheet_schemas.json` | Retained GenomeComparison native/parser/schema/sheet/calculation/projection/return chain; copied directly for the existing proteome description/contracts |

No Python, tests, static suites or workflow execution. Top-level retirement is coordinated with the independent A103 copy.

### 2026-11-11: remaining original homology execution helpers retired

These top-level originals now have applicable independent private implementations. Original source/module strings remain in retired history, not as shared fallbacks. The old combined top-level tool_information catalog and native_lifecycle original are not newly wired; their private replacements are the actual caller paths.

| Original | Private destination | Actual role |
| --- | --- | --- |
| `api_bvbrc_minhash.py` | `a101/api_bvbrc_minhash.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_contracts.py` | `a101/bvbrc_minhash_contracts.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_grader.py` | `a101/bvbrc_minhash_grader.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_host.py` | `a101/bvbrc_minhash_host.py` | Private API service/host factual-return and grading chain |
| `bvbrc_minhash_views.py` | `a101/bvbrc_minhash_views.py` | Private API service/host factual-return and grading chain |
| `hmmalign_grader.py` | `a101/hmmalign_grader.py` | Private HMMER alignment/search result parser and grader chain |
| `hmmalign_inputs.py` | `a101/hmmalign_inputs.py` | Private HMMER alignment/search result parser and grader chain |
| `nhmmer_grader.py` | `a101/nhmmer_grader.py` | Private HMMER alignment/search result parser and grader chain |
| `nhmmer_inputs.py` | `a101/nhmmer_inputs.py` | Private HMMER alignment/search result parser and grader chain |
| `sequence_masking_calculations.py` | `a101/sequence_masking_calculations.py` | Private native masking result/worker calculation and provenance chain |
| `sequence_masking_contracts.py` | `a101/sequence_masking_contracts.py` | Private native masking result/worker calculation and provenance chain |
| `sequence_masking_inputs.py` | `a101/sequence_masking_inputs.py` | Private native masking result/worker calculation and provenance chain |
| `sequence_masking_result_views.py` | `a101/sequence_masking_result_views.py` | Private native masking result/worker calculation and provenance chain |
| `windowmasker_statistics.py` | `a101/windowmasker_statistics.py` | Private native masking result/worker calculation and provenance chain |
| `native_profile_presentation.py` | `a101/native_profile_presentation.py` | Private native execution/provider lifecycle or scientific result presentation |
| `native_event_information.py` | `a101/native_event_information.py` | Private native execution/provider lifecycle or scientific result presentation |
| `native_events.py` | `a101/native_events.py` | Private native execution/provider lifecycle or scientific result presentation |

No runtime integration or execution validation was performed.

### 2026-11-11: preserved top-level extension source dispositions

The following original top-level implementations already have independent applicable A101 copies. They were not deleted in this placement pass because remaining unassigned top-level extension source still names their literal import paths. The private axis does not delegate to these originals. In particular: molecular/assay/variant/restriction extension originals name alignment identity or coordinate helpers; coding-sequence/ORF/primer and assembly/annotation extensions name sequence grading helpers; the original acquisition/state/worker modules name UniProt/read-mapping/sequence operations. Those original callers must receive their applicable independent dependencies when assigned; they are not a new shared scientific service and are not an enabled combined workflow.

| Preserved original | Applicable private implementation | Disposition |
| --- | --- | --- |
| `gene_annotation_episode/alignment_correspondence.py` | `a101/alignment_correspondence.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_result_presentation.py` | `a101/alignment_result_presentation.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_action_records.py` | `a101/alignment_site_action_records.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_calculators.py` | `a101/alignment_site_calculators.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_inputs.py` | `a101/alignment_site_inputs.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_mapping.py` | `a101/alignment_site_mapping.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_native.py` | `a101/alignment_site_native.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/alignment_site_returns.py` | `a101/alignment_site_returns.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/biopython_pairwise_grader.py` | `a101/biopython_pairwise_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/minimap2_grader.py` | `a101/minimap2_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/minimap2_grading_inputs.py` | `a101/minimap2_grading_inputs.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_composition_counts.py` | `a101/sequence_composition_counts.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_composition_grader.py` | `a101/sequence_composition_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_extraction_grader.py` | `a101/sequence_extraction_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_translation_grader.py` | `a101/sequence_translation_grader.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_mapping.py` | `a101/sequence_mapping.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_ops.py` | `a101/sequence_ops.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/sequence_worker.py` | `a101/sequence_worker.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/read_mapping.py` | `a101/read_mapping.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_native.py` | `a101/uniprot_native.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_native_contracts.py` | `a101/uniprot_native_contracts.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_publication.py` | `a101/uniprot_publication.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |
| `gene_annotation_episode/uniprot_return_contracts.py` | `a101/uniprot_return_contracts.py` | Private axis implementation already copied; original retained only for remaining extension-source accounting |

Unassigned top-level `api_sequence_support.py`, `sequence_support_contracts.py`, `sequence_support_publication.py` and molecular acquisition extensions have no new A101 registration. This pass preserves their source and does not infer scientific ownership from generic sequence terminology. GenomeAlignment, ComparativeSystems and Mauve originals are separately accounted by the A103 placement task; A101 GenomeComparison has its own retained independent copy.

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

- `scientific_process/episode.py`: `__init__`, `as_record`, `contract_information_profile`, `_role`, `child_roles`, `permitted_common_actions`, `allowed_children`, `instructions`, `_information_catalog`, `_closed_tool_resolution`, `_tool_resolution_for`, `_tool_resolution`, `catalog`, `create_tool_retriever`, `common_tool_names`, `decision_context`, `execute`.
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

- `scientific_process/published_evidence_assessment/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/waiting.py`: `supports_wait`.

`literature_strategy` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/waiting.py`: `supports_wait`.

`literature_search` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/waiting.py`: `supports_wait`.

`literature_page` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/waiting.py`: `supports_wait`.

`literature_table` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/waiting.py`: `supports_wait`.

`literature_ordered` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/waiting.py`: `supports_wait`.

`literature_targeted` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/yield_estimator.py`: `continuation_task`, `yield_controller`.
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
| `resource_episode.py:ResourceEpisode` | `launch` | `scientific_process/resource_work_submission` | `scientific_process` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `scientific_process/resource_work_submission/api_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `scientific_process/resource_work_submission/local_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `scientific_process/resource_work_submission/hpc_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `results` | `scientific_process/resource_result_acquisition` | `scientific_process` |
| `homology_episode.py:HomologyEpisode` | `job_launch` | `scientific_process/homology_job_submission` | `scientific_process` |
| `homology_episode.py:HomologyEpisode` | `job_monitor` | `scientific_process/homology_job_monitoring` | `scientific_process` |
| `homology_episode.py:HomologyEpisode` | `job_results` | `scientific_process/homology_result_acquisition` | `scientific_process` |

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

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/api_job_execution` (`launch_api`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield_estimator.py`: `yield_controller`.
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

`scientific_process/homology_job_submission` (`job_launch`):

- `episode.py`: `__init__`, `with_native_events`, `recover_native_events`, `bind_job_native_events`, `as_record`, `recover_statistics`, `instructions`, `describe`, `prospective_execution_classes`, `prospective_execution_options`, `working_state`, `binding_for`, `has_information_channel`, `catalog`, `execute`, `_execute`, `_validate_launch_return`, `_validate_monitor_return`, `_validate_results_return`, `_validate_role_return_sources`, `_validate_recorded_return`.
- `requests.py`: `commission_schemas`, `_query`, `assign`, `assignment`.
- `returns.py`: `fact_sources`, `resolve`, `facts`, `validate_report`.
- `credit.py`: `_launch_credit`, `_monitor_credit`, `_results_credit`, `initial_credit`, `credit_kind`, `credit_view`.
- `waiting.py`: `latest_sample`, `recorded_sample`, `latest_checked_status`, `received_timing_records`.

`scientific_process/homology_job_monitoring` (`job_monitor`):

- `episode.py`: `__init__`, `with_native_events`, `recover_native_events`, `bind_job_native_events`, `as_record`, `recover_statistics`, `instructions`, `describe`, `prospective_execution_classes`, `prospective_execution_options`, `working_state`, `binding_for`, `has_information_channel`, `catalog`, `execute`, `_execute`, `_validate_launch_return`, `_validate_monitor_return`, `_validate_results_return`, `_validate_role_return_sources`, `_validate_recorded_return`.
- `requests.py`: `commission_schemas`, `_query`, `assign`, `assignment`.
- `returns.py`: `fact_sources`, `resolve`, `facts`, `validate_report`.
- `credit.py`: `_launch_credit`, `_monitor_credit`, `_results_credit`, `initial_credit`, `credit_kind`, `credit_view`.
- `waiting.py`: `latest_sample`, `recorded_sample`, `latest_checked_status`, `received_timing_records`.

`scientific_process/homology_result_acquisition` (`job_results`):

- `episode.py`: `__init__`, `with_native_events`, `recover_native_events`, `bind_job_native_events`, `as_record`, `recover_statistics`, `instructions`, `describe`, `prospective_execution_classes`, `prospective_execution_options`, `working_state`, `binding_for`, `has_information_channel`, `catalog`, `execute`, `_execute`, `_validate_launch_return`, `_validate_monitor_return`, `_validate_results_return`, `_validate_role_return_sources`, `_validate_recorded_return`.
- `requests.py`: `commission_schemas`, `_query`, `assign`, `assignment`.
- `returns.py`: `fact_sources`, `resolve`, `facts`, `validate_report`.
- `credit.py`: `_launch_credit`, `_monitor_credit`, `_results_credit`, `initial_credit`, `credit_kind`, `credit_view`.
- `waiting.py`: `latest_sample`, `recorded_sample`, `latest_checked_status`, `received_timing_records`.


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
| `scientific_process/homology_job_monitoring` | `homology_job_monitoring` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_job_submission` | `homology_job_submission` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_result_acquisition` | `homology_result_acquisition` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
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
| `scientific_process/homology_job_monitoring` | `homology_job_monitoring` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_job_submission` | `homology_job_submission` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_result_acquisition` | `homology_result_acquisition` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
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

`homology_service_setup.py:create_homology_bindings` owns the plain legacy job construction helper formerly placed in scientific_process/episode.py; it registers no binding and supplies no shared task policy. The actual private classes remain in the three recorded homology homes.

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
- `scientific_process/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.

## 2026-11-11 final role and supporting-code index

The [complete ownership inventory](ownership_inventory.json) is the exact appendix to this record: it maps every original binding class to its singleton role, actual parent, final home, local method symbols and responsibility files. It also records every descriptive support module, its owner, imports, direct callers and consuming episodes; every library symbol and its explicit importing modules; and each test/helper and required fixture file. Unreferenced retained modules are recorded with empty consumers, not represented as active evidence or bindings. Shared scientific graders, readers, sheets and calculators keep their descriptive names at the common axis owner. Their functions are not merged with investigation credit.

| Original binding | Role | Final home | Parent | Supporting files |
| --- | --- | --- | --- | --- |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `execution_job_submission/api_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `execution_job_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `execution_job_submission/hpc_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `execution_job_submission/local_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `execution_progress_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `execution_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `homology_episode.py:HomologyEpisode` | `job_monitor` | `homology_job_monitoring/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py` |
| `homology_episode.py:HomologyEpisode` | `job_launch` | `homology_job_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py` |
| `homology_episode.py:HomologyEpisode` | `job_results` | `homology_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `published_evidence_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `resource_episode.py:ResourceEpisode` | `results` | `resource_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `resource_work_submission/api_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch` | `resource_work_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `resource_work_submission/hpc_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `resource_work_submission/local_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `scientific_process_episode.py:ScientificProcessEpisode` | `scientific_process` | `scientific_process/episode.py` | root annotation; scientific_process self-recursion (not expanded) | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/execution_job_submission/api_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/execution_job_submission/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/execution_job_submission/local_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/execution_progress_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/execution_result_acquisition/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `scientific_process/published_evidence_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | scientific_process/published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
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


## 2026-11-11 A101 scientific-process monitor responsibility split

The monitor now connects its private task, state, decision exchange, goal, operations, reporting, credit and yield modules. Recursive dependency requests and progress receipts have directional files; the original scientific parent message split remains open. The unused local progress provider copy was removed after matching all 21 methods to active infrastructure. The episode ownership record and inventory are under `a101/scientific_process/execution_progress_assessment/` relative to the root. Source checks validate 21 binding methods, 21 task methods under fixed monitor specialization, 22 module imports, exception identities and the current fingerprint. The focused check has 91 passes; receipts are in `runs/monitor_responsibilities_20261111_final/` and `runs/monitor_responsibilities_20261111_audit02/`. This is controlled validation, not autonomous monitoring or whole-workflow restoration. The episode and broader goal retain their explicitly recorded remaining work.


## 2026-11-11 remaining monitor responsibility extraction

Each existing monitor now has its own goal, task, decision exchange, state, operations, reports, credit and yield files, plus recursive directional messages and tests. Per-episode ownership files and inventories describe current files, dependencies and remaining parent-message/applicability work. The whole monitor check has 426 passes and two inherited A106 Store initialization failures; original-binding reproduction is retained. See `runs/monitor_tree_20261111_audit/`, `runs/monitor_tree_20261111_behavior/` and `runs/monitor_tree_20261111_a106_baseline/`. This is controlled connection validation, not autonomous monitoring or full restoration.

## 2026-11-11 private monitor task narrowing

Monitor decision snapshots and fresh input preparation now have private implementation files. Inapplicable scientific/job/read-mapping/shared-grading branches were removed with their destinations or non-applicability recorded. Baseline 272 checks pass; expanded validation has 698 passes and the same two inherited A106 Store failures. Source audit and current inventories are under `runs/monitor_task_narrowing_20261111_{audit,records}/`. Private instructions, prompt rendering, caller credit presentation and the full episode-tree organization remain open.

## 2026-11-11 monitor instructions and renderer ownership

Each private monitor now composes applicable instructions in `task_instructions.py` and selects `library/monitor_prompt.py` explicitly. The old root formatter moved; its consumers are recorded in `library/monitor_prompt.ownership.json`. Provider transport accepts the declared renderer through an optional interface, preserving default behavior. Binding fingerprints include the selected library source. The expanded suite has 1,032 passes and two inherited A106 failures; all 340 affected instruction checks pass after the final guidance preservation. Source and current identity receipts are under `runs/monitor_prompt_ownership_20261111_{audit02,records}/`. Earlier instruction/rendering limitations are superseded for these monitors. Caller credit-shape presentation, restoration and the full episode-tree organization remain unfinished.

## 2026-11-11 monitor credit calculator ownership

Private monitor credit files now select `library/progress_information_credit.py` with explicit caller operands; custom projectors remain unchanged. Consumers, source provenance, actual projector names and per-axis branch accounting are in `library/progress_information_credit.ownership.json`. A104 restores its original missing shared dependency; A107 removes an unsupported legacy job branch. Stale public-reader imports in affected setup paths were repaired. Validation has 1,302 passes and two unchanged A106 Store failures, plus 34 passing actual-outcome/runtime-credit connections. Full service construction, saved reopening, caller-specific presentation and wider organization remain open.

</details>


The existing annotation parent has substantive task, goal, summary, credit, report and continuation owners plus ten configured parent exchanges. The original conditional improvement has its private annotation_improvement home; recursive reuse retains original credit/graph rejection and actual root-level Homology child custody. Six Scientific incoming admissions preserve their existing outgoing/projection owners. Shared original protocols and public/custom fallback retain explicit custody. All forty registrations and historical evidence are preserved in `implicit_annotation_improvement_parent_source_20261113`. This prepared source join is not an installation, configured descriptor observation, scientific validation or full saved-workflow result.


## Improvement test physical ownership

The 24 exact improvement host and original-source compatibility cases now live in `annotation_improvement/tests/test_implicit_improvement.py`. The two original annotation/improvement commissioning cases remain in `tests/test_a101_implicit_improvement.py`. Both consume the single construction helper `tests/a101_implicit_parent_test_context.py` and the unchanged parent protocol/oracle fixture.

Source79 and historical accepted98/current54 observations remain at their original epochs. The exact path/body bijection is recorded by runs/fourth_a101_improvement_test_placement_02/prepared/PLACEMENT_PROOF.json (4c76af6d8c58cdb615c84509676b8906fe1cf44dad4cdd6364ada451bad3ec89). This placement does not claim another behavioral run or canonical application.


Policy ownership successor, 2026-11-13: current source definitions, import consumers and applicable dependency closures are recorded by runs/fourth_a101_policy_metadata_generation_02/prepared/CURRENT_POLICY_ACCOUNT.json (f9d910f0a0cba3b6eab010f38fc7068a1077cfb66f5c51a90d565e9dfadbfc34). The actual20 controls and six cold orders retain their exact new source epoch. Earlier98/54/recursive24 observations and descriptor/configuration histories remain unchanged. No configured descriptor was evaluated by this metadata preparation.


Incoming-owner and Monitor-record successor, 2026-11-13: runs/fourth_a101_incoming_metadata_generation_02/prepared/CURRENT_ACCOUNT.json (57dec0b2844923d1ea99e3d5eb11b8e285f31a0b87b8fb72604b46445aafaa9c) records the exact constructor moves, explicit improvement/task_state retirement, current dependency/source membership and both ends of the existing two recursive Monitor edges. Only the two incoming owners have the new13/39/four-cold controlled receipt. All previous98/54/20/recursive24 observations and configuration values retain their source epochs; no configured descriptor or autonomous/restored Workflow is evaluated here.


Final current-provider source and asset join, 2026-11-14: runs/fourth_a101_final_current_metadata_02/prepared/CURRENT_ACCOUNT.json (ea35388e9d6bece25f4d9102ff50fdc06694f64c543af45681cfc553776daeeb) records current selected class/method spans and live namespaces, authentic unchanged descriptor domains, named private/shared controls and complete pending92 assets. Actual new72/216/four-cold evidence retains its exact source scope; earlier incoming13, Scientific24,98/54/20 and recursive24 results remain at their original epochs. No configured descriptor or full autonomous Workflow is evaluated; canonical installation is separate.


## Retained Homology compatibility API (2026-11-14)

Current exact account: `runs/fourth_a101_homology_compatibility_metadata_01/prepared/COMPATIBILITY_ACCOUNT.json` (`1344263bc91078f5603071c6794b8d4b87167654016d33d94ce4777ec32bb9fb`). This supplements the installed444 metadata; executable code and prior controlled evidence are unchanged.

- `homology_job_submission`: nominal `job_launch` dispatch selects only its own credit/report helpers. The four other-role helpers retain original direct or overridable custom API behavior; they are not alternate scientific role execution. Actual helper definitions, original body provenance, constructor callback operands and selectors are recorded in the machine account.
- `homology_job_monitoring`: nominal `job_monitor` dispatch selects only its own credit/report helpers. The four other-role helpers retain original direct or overridable custom API behavior; they are not alternate scientific role execution. Actual helper definitions, original body provenance, constructor callback operands and selectors are recorded in the machine account.
- `homology_result_acquisition`: nominal `job_results` dispatch selects only its own credit/report helpers. The four other-role helpers retain original direct or overridable custom API behavior; they are not alternate scientific role execution. Actual helper definitions, original body provenance, constructor callback operands and selectors are recorded in the machine account.

Exact-family construction rejects subclasses, while normalization intentionally preserves custom/subclass objects. Both callbacks and all three constructor credit-binding operands remain required by actual family normalization. Foreign report helpers reject nominal roles before schema/record callbacks; custom hooks remain overridable. No external invocation is claimed, and absence of repository callers does not justify deleting protected compatibility APIs. Every earlier metadata byte is retained with a suffix/removal inverse.
