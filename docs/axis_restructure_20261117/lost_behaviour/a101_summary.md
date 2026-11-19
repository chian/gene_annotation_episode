# A101 lost behaviour: HEAD (97308b94c) against the working tree (18 November 2026)

Scope: the 1,920 files at HEAD under `gene_annotation_episode/episodic_workflow/root/a101/`, excluding `tests/`,
`annotation_improvement/` and `method_loop/` (HEAD has no `scientific_process/` tree in this axis). 375,033 lines.
Per-file table: `a101.tsv` (one row per HEAD file, plus one row for a function removed inside a surviving file;
lost and uncertain rows first, with full detail).

Method (read-only: `git ls-tree/show/grep`, `grep`, `find`): each HEAD file was looked for at the same path, then by
file name anywhere in the live tree, then by its top-level `def`/`class` names in non-test code. Surviving homes of
top-level and `library/` files were also compared method by method with the HEAD file. Baseline test counts are the
rows of `docs/verification_20261116/results_per_file.tsv` for the HEAD test files that name the module (word match,
so a count is "tests in files that mention it", not "tests of it").

## Counts per verdict

| verdict | files | lines |
|---|---|---|
| present (same path 44; identical data files 84; code under `episode_support/` or another current home 518) | 646 | 227,512 |
| intended_removal: task/protocol layers | 577 | 49,370 |
| intended_removal: duplicate trees (six top-level copies of the head's child trees) | 453 | 34,049 |
| intended_removal: receipts inheritance | 51 | 16,415 |
| intended_removal: runtime (old per-axis runner and its support) | 23 | 6,153 |
| intended_removal: vendor folders | 5 | 2,894 |
| intended_removal: registries | 5 | 1,344 |
| intended_removal: extra yield estimators | 4 | 1,119 |
| intended_removal: per-axis model providers | 3 | 1,134 |
| intended_removal: journals | 1 | 195 |
| **lost_capability** | 59 files + 1 removed function | 17,368 |
| **uncertain** | 93 (9 A101 modules, 84 `library/retained_input_authority` modules) | 17,498 |

Of the 646 present files, 12 survive only as another axis's copy and 180 `retained_input_authority` files survive
as the same-named module they duplicated.

## Lost capabilities, by what they did

Nothing in groups 1 to 9 exists anywhere in the working tree under any name (class and function names searched in
`gene_annotation_episode/`, `episode_runtime/`, `method_loop/`, `yield_control/`).

### 1. Native result acquisition, grading publication and result stores of the results episode (6,837 lines)

At HEAD the head's `execution_result_acquisition` child (and the launch children that shared its mixins) acquired
and published native job results through one result store per job family, installed by
`a101_execution_bindings.install_primary_result_readers` / `install_preparation_result_readers`.

| family | HEAD files | baseline tests |
|---|---|---|
| native database BLAST on HPC (psiblast, deltablast, rpsblast, rpstblastn, blastn_vdb, tblastn_vdb) | `native_blast_database_acquisition.py` 293, `native_blast_database_result_publication.py` 1086, `native_blast_database_results.py` 437 | `tests/test_native_blast_database_acquisition.py` 29 tests / 24 passed |
| standard native database BLAST on HPC (`native.<program>.database`) | `native_blast_standard_database_acquisition.py` 293, `..._result_publication.py` 929, `..._results.py` 331 | `tests/test_native_blast_standard_database_acquisition.py` 30 / 24 |
| native HMMER preparation | `native_hmmer_preparation_result_publication.py` 687, `native_hmmer_preparation_results.py` 480, `library/native_hmmer_preparation_failure_views.py` 119 | `test_native_hmmer_preparation_result_publication.py` 29 / 3 (25 errors), `test_hmmer_original_request_environment.py` 18 / 18, `test_native_hmmer_preparation_workflow.py` 36 / 0 |
| native HMMER search | `native_hmmer_acquisition.py` 219, `native_hmmer_results.py` 290, `library/native_hmmer_result_policy.py` 74 | `test_native_results_policy_boundaries.py` 40 / 40 |
| native BLAST pairwise, masking and utility result stores | `native_blast_results.py` 331, `library/native_blast_result_policy.py` 83, `native_blast_masking_results.py` 586, `native_blast_utility_results.py` 599 | `test_blast_native_return_admission.py` 39 / 39, `test_native_blast_return_late_facts_port.py` 5 / 5, `test_blast_utility_result_views_629.py` 46 / 45, `test_blast_vdb_publication_returns_669.py` 26 / 26, `test_blast_vdb_capture_failure_674.py` 20 / 20, `test_blast_utility_episode_wiring_632.py` 35 / 11 |

- Offered at HEAD: yes, by the head's `execution_result_acquisition` and launch children.
- Deleted by: the dangling-import repair `runs/fx101_tools/b1.tsv` (result stores and database publications, after
  `episode_return_records` / `form_reference_validation` were deleted in the old-runner pass, `a101_needs.md` N12)
  and the reachability prune `runs/rp101-tools/deleted_round1..3.txt` (`native_hmmer_results`,
  `native_hmmer_acquisition`, the two result policies, the failure views). The two database acquisitions and the
  HMMER preparation publication were still listed as test-only in `runs/rp101-tools/orph3.txt`; no later record
  names their deletion.
- Still present: the drivers, contracts, result views, workers and worker values of every family, and the pairwise
  and HMMER-search publication steps (`episode_support/records/similarity_search/sequence_homology_evidence/
  native_blast_result_publication.py`, `native_hmmer_result_publication.py`). The current
  `execution_result_acquisition/acquisition_source.py` retains output snapshots of local/HPC receipts and publishes
  API results only; it calls none of them.
- To bring back: capture steps in `episode_support/acquisition/similarity_search/sequence_homology_evidence/`
  (HMMER preparation beside `acquisition/profile_model_preparation/sequence_homology_evidence/`), publication steps
  and result stores in `episode_support/records/similarity_search/sequence_homology_evidence/` (and
  `records/profile_model_preparation/`), re-based from the old `EpisodeReturnRecords` custody onto Store receipts.
  Offered by `sequence_homology_evidence/execution_result_acquisition` as a new unit kind of `acquisition_source.py`
  (publish the selected native result of a local/HPC handoff).

### 2. Local file source capture (829 lines)

`local_file_capture_results.py` 717 (`LocalFileSourceResults`: selected local files captured as Store sources with
exact byte identity, windows, per-file commits) and `file_capture_receipt_control.py` 112. A 35-line constants-only
file remains at `episode_support/records/local_execution/local_file_capture_results.py`.
- Tests: `tests/test_operational_private_boundaries.py` 160 / 114 mentions it.
- Offered at HEAD: yes (`native_input_custody._selector` of the results and launch children).
- Deleted by: `a101_needs.md` N12; `rp101 deleted_round1.txt` (control file).
- To bring back: `episode_support/records/local_execution/sequence_homology_evidence/`; offered by
  `execution_result_acquisition` (its `output_snapshot` unit covers receipt-declared outputs only).

### 3. Native phmmer homology job family (3,403 lines)

`homology_results.py` 575 (the `homology.extract` / `homology.coverage` / `homology.errors` / witnesses reads),
`phmmer_result_worker.py` 187, `phmmer_grading_worker.py` 97, `library/phmmer_format.py` 237,
`library/phmmer_grading_values.py` 164, `library/phmmer_alignment_values.py` 16, `homology_progress.py` 312,
`homology_recovery.py` 76, `a101_homology_resource_adapter.py` 549, `resource_information.py` 483, and the
operations, contracts, planning and native-event files of `homology_job_submission/`, `homology_job_monitoring/`,
`homology_result_acquisition/` (12 files, 707 lines).
- Tests: `test_homology_progress.py` 26 / 26, `test_homology_prepare_source_identity.py` 2 / 2,
  `test_private_homology_family.py` 9 / 9, `test_private_descriptor_reopening.py` 6 / 6.
- Offered at HEAD: yes for the family (`episode_composition.py` built `HomologyResourceAdapter` when job episodes
  were configured and gave it to the head's `resource_work_submission` / `resource_result_acquisition`).
  `homology_progress.py` and `homology_recovery.py` had no non-test importer in A101 at HEAD.
- Deleted by: the ablation (`runs/claude_ablate/a101_delete_paths.txt`, `a101_unreached.txt`; `a101_needs.md` N5
  called them copies of the shared root family, which is also gone).
- Still present: `episode_support/jobs/similarity_search/sequence_homology_evidence/homology_jobs.py` (job registry)
  and `knowledge/phmmer-*.md`, which still describe the deleted tools.
- To bring back: reader in `episode_support/readers/similarity_search/sequence_homology_evidence/`, workers in
  `jobs/similarity_search/sequence_homology_evidence/`, grading values in `grading/similarity_search/...`, result
  store in `records/similarity_search/...`; offered by `resource_work_submission/local_resource_work_execution`
  (launch) and `resource_result_acquisition` (paged results).

### 4. EBI HMMER web API job route (936 lines)

`api_execution.py` (`HMMERAPIExecution`, resource kind `hmmer_api`: `api.hmmer.databases/prepare/submit/status/
check_handoff/result`).
- Tests that mention it: `test_execution_parent_launch_admission.py` 30 / 30, `test_operational_private_boundaries.py`
  160 / 114, `test_hmmer_grading_publication.py` 30 / 30 (`api.hmmer.`).
- Offered at HEAD: yes (`api_job_execution/configuration.py` and the results child).
- Deleted by: `a101_needs.md` N12.
- To bring back: an API service with the `NCBIBlastService` interface in
  `episode_support/acquisition/similarity_search/sequence_homology_evidence/`, a `hmmer_api` kind in
  `execution_job_submission/api_job_execution/configuration.build_api_service`; results through the existing
  `acquisition_source.py` API path. `ToolRegistry.publish_hmmer_result` and its clients survive.

### 5. A101 API services other than NCBI BLAST (4,079 lines)

At HEAD `api_services.build_service` built five kinds (`uniprot`, `bvbrc_data`, `ncbi_blast`, `bvbrc_minhash`,
`bvbrc_appservice`) and `api_service_execution.py` 1111 ran them. Now `build_api_service` accepts `ncbi_blast` only
and raises `a101_api_job_service_has_no_a101_primitive` for the rest.
- Lost files: `api_service_execution.py`, `api_services.py::build_service` (removed inside the surviving file),
  `bvbrc_appservice_host.py` 245, `bvbrc_appservice_monitor.py` 414, `bvbrc_appservice_publication.py` 442,
  `bvbrc_homology_tool_info.py` 111, `bvbrc_proteome_tool_info.py` 183, `library/bvbrc_homology_return_values.py`
  160, `library/bvbrc_proteome_return_values.py` 251, `library/uniprot_return_projection.py` 714, and the
  GenomeComparison part of `library/bvbrc_application_definitions.py` (the merged shared copy keeps Homology only;
  `GenomeComparison.json` survives).
- Tests: `test_api_bvbrc_data_v2.py` 52 / 52, `test_bvbrc_proteome_private_route.py` 37 / 37,
  `test_bvbrc_homology_returns.py` 40 / 40, `test_bvbrc_proteome_returns.py` 10 / 10,
  `test_bvbrc_homology_tool_info.py` 11 / 0.
- Offered at HEAD: yes (configuration of the launch and results children; tool info through
  `a101_execution_bindings` and the children's `execution_operations`).
- Deleted by: `a101_needs.md` N12; `fx101 b1.tsv` (publication, the two tool-info modules); `rp101
  deleted_round1.txt` (`uniprot_return_projection`), `deleted_round2.txt` (`bvbrc_application_definitions`).
- Still present: the service clients (`UniProtService`, `BVBRCDataService`, `BVBRCMinhashService` shared;
  `BVBRCAppServiceService` in four other axes' copies), and A101's BV-BRC data, homology, MinHash, proteome and
  UniProt readers, graders and contracts.
- To bring back: service kinds in `api_job_execution/configuration.build_api_service` (and
  `api_resource_work_execution`, which shares it); AppService on the pattern of
  `root/a103/gene_context_evidence/execution_job_submission/api_job_execution/appservice_source.py`, with an A101
  `bvbrc_application_definitions.py` (Homology, GenomeComparison) in
  `episode_support/acquisition/service_calls/sequence_homology_evidence/`; tool info in
  `episode_support/tools/service_calls/sequence_homology_evidence/`; fact projections in `episode_support/readers/`
  (`similarity_search/`, `expression_and_perturbation/`, `sequence_and_context_sources/` under
  `sequence_homology_evidence/`).

### 6. BLAST graded-return request (228 lines)

`library/blast_return_contracts.py` 34 and the mixins `execution_job_submission/blast_request_custody.py` 43,
`execution_job_submission/api_job_execution/blast_request_custody.py` 61,
`execution_result_acquisition/blast_result_grading.py` 90: a parent could request a graded database BLAST result
for one query subject (and optional database); the launch children rejected a selected search whose query sha256
or database differed, and the results child returned only database-grader results matching the request.
- Tests: `tests/test_a101_scoring.py` 17 / 17 mentions the names; no test file is specific to it.
- Offered at HEAD: yes (head's `execution_job_submission`, `api_job_execution`, `execution_result_acquisition`).
- Deleted by: `rp101 deleted_round1.txt` (contract); the mixins with the old task layers (`a101_needs.md` N12).
- To bring back: form in `episode_support/forms/similarity_search/sequence_homology_evidence/`; checks in
  `execution_job_submission/submission_source.py`, `api_job_execution/runtime_source.py` and
  `execution_result_acquisition/acquisition_source.py`.

### 7. Head planning view and tool-information retrieval (339 lines)

`execution_planning.py` 70 and `sequence_homology_evidence/execution_planning.py` 36 (the head's
`process.execution` tool: host capacity, queue and inventory memory, timing history per profile), and
`scientific_tool_retrieval.py` 233 (`ScientificToolRetriever`).
- Tests: none found by name.
- Offered at HEAD: yes (`tool_selection.catalog` appended the planning tool; `tool_selection.create_tool_retriever`).
- Deleted by: `rp101 deleted_round1.txt` (both top-level files); the head file with N12.
- Still present: `ExecutionMemory` (`episode_support/records/sequence_homology_evidence/execution_memory.py`) and
  `ScientificToolLibrary` (`episode_support/tools/tool_catalog.py`); the head no longer receives either.
- To bring back: `episode_support/tools/sequence_homology_evidence/`; offered by the head
  (`sequence_homology_evidence/runtime_source.py` tool list).

### 8. Requested views of saved alignment-site results (717 lines)

`library/alignment_site_returns.py` (`alignment_site_fact_sources`, `requested_site_projections`).
- Tests: none found by name. Offered at HEAD: head `scientific_contracts.py`. Deleted by `rp101 deleted_round1.txt`.
- To bring back: `episode_support/readers/sequence_alignment/sequence_homology_evidence/`; offered by the head.

## Uncertain

A101 modules (9), owner judgement needed:
- `a101_execution_bindings.py` 197: which native BLAST/HMMER job kinds a launch request may name, their schemas and
  selector conditions. The individual contracts survive; this composition has no equivalent found.
- `execution_progress.py` 1365: live observation of an API or native target by the monitor (one status operation,
  bounded file window). The current job provider reads only what receipts already recorded.
- `shared_information.py` 332, `shared_information_results.py` 87: information needs and evidence deliveries
  between sibling episodes; reached only from the old runtime.
- `monitoring_credit.py` 203, `library/resource_operational_credit.py` 324 (`test_resource_operational_credit.py`
  81 / 81): old credit rules; the new bindings have their own, equivalence not checked.
- `hpc_launch_authentication.py` 24, `scientific_support_metadata.py` 76, `library/alignment_site_action_records.py` 272.

`library/retained_input_authority/` (84 modules, 14,618 lines): the tree was deleted by orchestrator ruling
(`runs/claude_ablate/a101_contract_requests.md`), and A101 offered no tool from it. These 84 have no same-named
module anywhere now, although every one also existed in other axes, `root/library` or the package at HEAD (for
example the BV-BRC genome-alignment, comparative-systems, Mauve and XMFA contracts, flux-balance, HOMER, TF-binding
and native capture modules). Each row names the HEAD copies; the owning scope must judge them.

## Removed inside surviving files

- `api_services.py`: `build_service` (group 5).
- `library/alignment_site_native.py`: `read_selected_reference_alignment` and its authority check.
- `terminal_scientific_evidence.py`: seven terminal handoff/native/observation functions (still in the
  `structural_homology_evidence` copy).
- `bvbrc_appservice_records.py`: class `AppServiceRecords` (publish, read, retain_snapshot).
- `communication.py`: 1,123 to 414 lines (`runs/fx101_tools/edit_comm.py` removed the branches that validated
  received facts of other axes).
- `tools.py`: `retained_molecular_reference_access`, `workflow_services`, `current_invocation`.
- `blast_result_views._original_hsp` no longer validates database observations (noted in
  `per_file_comparison/a101_summary.md`).

## Limits of this check

- Decision behaviour of the 19 old task layers was not compared line by line with the new sources; group 6 is the
  one difference found by searching for the old error codes.
- "Present" means the definitions exist; whether a current binding calls them was not traced.
