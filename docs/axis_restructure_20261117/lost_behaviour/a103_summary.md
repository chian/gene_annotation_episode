# A103 lost behaviour: HEAD (97308b94c) against the working tree (2026-11-18)

Scope: the 3,312 non-test files at HEAD under `gene_annotation_episode/episodic_workflow/root/a103/`.
Rows for every lost or uncertain file are in `a103.tsv` (this folder); everything else is summarised there by count.
Read-only work: `git ls-tree/show/grep`, `grep`, `find`. No code or test was run or changed.

## Result

- **90 HEAD files (31,270 lines) hold capabilities that exist nowhere in the working tree now** (11 groups, G1-G11).
- **56 more files (13,467 lines) are uncertain** (6 groups, U1-U6): the old file is gone and a rebuilt file covers part of it, or parity was not checked.
- 363 of the 574 flat `a103/*.py` modules are present (192 in A103's own homes, 139 as shared copies, 32 only as another axis's copy).
- All 34 bindings still exist and are constructed by `gene_context_evidence/home.py`; no binding still raises "not ported".
- No A103 baseline test covered groups G1-G6, G8, G10, G11. The same code was tested through `root/library` by 33 top-level
  `tests/test_*.py` files (1,471 tests, 1,450 passed at 7e662ea29); those 33 test files and the `root/library` copies are gone too.

How presence was decided: identical blob anywhere under `gene_annotation_episode/`; else the `placement.tsv` target;
else the file holding the same top-level function/class names, confirmed by line overlap. A name found only in an
unrelated module (for example `encode_reference`) was not counted as presence.

## Lost capabilities

| Group | What it did | HEAD files (under `a103/`) | Lines | Offered to an episode at HEAD? | Deleted by |
|---|---|---|---|---|---|
| G1 | BV-BRC ComparativeSystems: readers for the six native formats, Data population extraction, numerical sheet, calculators, saved-fact projection, tool information | 16 `bvbrc_comparative_systems_*.py` | 4,968 | **Not in A103.** `a103/bvbrc_appservice_adapters.py` installed only the homology adapter and `APIServiceExecution` had no `comparative_systems_returns`. Offered through `root/library` and `a110/library/received_execution_dependencies` | rp103-reach-4, -5; fx103 round 1 (`host_inputs`) |
| G2 | BV-BRC GenomeAlignment (Mauve): XMFA reader, coordinates, source binding and calculators; Mauve v4 segment reader and calculators; backbone/bbcols readers and calculators; bundle resolution, sheet, tool information | 13 `bvbrc_genome_alignment_*.py`, 7 `mauve_*.py`, 7 `xmfa_*.py`, `bvbrc_alignment_values.py`, `genome_alignment_reference.py` | 9,920 | **Not in A103** (same evidence as G1). Offered through `root/library`, `a102/xmfa_formats.py`, `a110/library` | rp103-reach-4, -5; fx103 round 1 (`host_inputs`) |
| G3 | Genomic-overlap results: capture of native overlap output, bounded conversion worker, interval calculations (bp counts, unions, pair measures), saved-sheet views, result host, tool information | 6 `native_genomic_overlap_*.py`, 7 `genomic_overlap_*.py`, `terminal_native_file_capture.py` | 4,084 | **Launch side yes** (`terminal_scientific_evidence._PROFILES['native_genomic_overlap']`, `execution_progress.py`). **Result host no**: `NativeGenomicOverlapResults` and `native_genomic_overlap_tool_info` had no importer in A103 | rp103-reach-4, -5; fx103 round 1 |
| G4 | Projection of selected facts from an authenticated UniProt publication | `uniprot_return_projection.py` | 716 | Yes: `APIServiceExecution.uniprot_returns` (API job execution bindings) | rp103-reach-4 |
| G5 | Result hosts of the result-acquisition episode for native BLAST, BLAST database, standard database, masking, utility, HMMER and HMMER preparation (`execution.results.status` / `collect`), PBS-attempt and HMMER bundle capture, retained numerical publication | 7 `native_*_results.py`, 3 `*_result_publication.py`, 3 `*_acquisition.py`, `native_hmmer_preparation_failure_views.py` | 6,820 | Yes: `a103_execution_bindings.install_primary_result_readers`, dispatched by `execution_result_acquisition/acquisition_operations.py` at three levels | fx103 round 1; rp103-reach-4 |
| G6 | HMMER web API execution (`api.hmmer.databases/prepare/submit/check_handoff`) | `api_execution.py` | 936 | Yes: `APIServiceExecution` built it for resources of kind `hmmer_api` | rp103-reach-4 |
| G7 | phmmer homology results: native phmmer text parser, disk-backed extraction and grading worker, paged results tool, progress reader, recovery of unparsed searches, homology resource adapter | `phmmer_format.py`, `phmmer_grading_worker.py`, `phmmer_result_worker.py`, `homology_results.py`, `homology_progress.py`, `homology_recovery.py`, `a103_homology_resource_adapter.py` | 2,168 | Only by the legacy parent's homology children (intended removal) and the resource-work family's adapter. `tests/test_a103_real_detection.py` (2 passed) used `HomologyResults` | rp103-reach-4; adapter: no record |
| G8 | A103's binding of typed native BLAST/HMMER/masking/utility jobs and BV-BRC Homology and GenomeComparison service modes into the execution episodes (requested-job schemas, operation contracts, result selectors, BLAST grader rows) | `a103_execution_bindings.py`, `a103_homology_execution.py`, `bvbrc_homology_tool_info.py`, `bvbrc_proteome_tool_info.py` | 738 | Yes: imported by `contracts.py` of all 15 execution binding homes (`bvbrc_proteome_tool_info.py` had no importer) | fx103 round 1; rp103-reach-4, -5 |
| G9 | Shared information between episodes (`shared.request_information`, `publish_information`, `resolve_information_need`, `read_information`, `list_information`) | `shared_information.py`, `shared_information_results.py` | 408 | Yes: head common tools, executed by `a103/runtime.py`. `tests/test_a103_context.py` (37 passed) builds `SharedInformation` | fx103 round 1 |
| G10 | Execution planning views for a scientific parent (`process.execution`: execution memory per profile, host capacity) | `execution_planning.py` | 98 | Yes: `gene_context_evidence/operations.py` catalog | rp103-reach-4 |
| G11 | Monitor observation of one BV-BRC AppService job | `bvbrc_appservice_monitor.py` | 414 | Yes: `APIServiceExecution.observe_target` | claude_ablate fourth revision |

What the ported A103 offers instead, checked in the current code:
- Local and HPC job execution run model-written shell commands (`exec_command`) only. The typed native-tool job contracts
  are gone from A103: `a103_execution_bindings.py` was deleted and `native_blast_tool_contracts`,
  `native_hmmer_tool_contracts`, `native_blast_masking_tool_contracts` and `native_blast_utility_tool_contracts` were
  removed from the A103 tool-info copies as unused (`runs/rp103-remove-1`, `-2`).
- Result acquisition retains raw results (`result_request`, `result_publication`, `appservice_result`,
  `output_snapshot`). No unit grades or projects a native BLAST, HMMER, masking or overlap result.
- The head offers reason, tool and a narrower `gene_context_evidence` child. No `shared.*` or `process.execution` tool exists.

## Uncertain

| Group | What | Files | Lines | Why uncertain |
|---|---|---|---|---|
| U1 | Typed requested-fact returns across child boundaries | 12 `*_returns.py` | 4,703 | The custody half is old receipts inheritance (intended removal). The half that let a parent request selected saved numerical facts from a results child has no replacement; the ported return form is `{credit, finding}` |
| U2 | Decision presentation (prompt rendering) | `gene_context_evidence_prompt.py`, `execution_prompt.py`, `native_profile_presentation.py`, `alignment_result_presentation.py`, `alignment_reference.py`, `a103_work_report.py`, `library/hpc_prompt.py`, `library/monitor_prompt.py` | 2,125 | Each runtime source now assembles its own prompt. Content parity was not checked. The instruction text itself (`goal.py`, `runtime_prompt.py`) survives in `episode_support/literature/prompts/gene_context_evidence/literature_investigation_prompt.py` |
| U3 | Custody hosts for BV-BRC Data and MinHash | `bvbrc_data_host.py`, `bvbrc_minhash_host.py` | 1,172 | The service clients remain and are built by `api_services.build_service`. The hosts' delivery of received facts to parents has no counterpart |
| U4 | Rebuilt or partly rebuilt execution-side code | `api_service_execution.py`, `execution_progress.py`, `a103_investigation.py`, `scientific_tool_retrieval.py`, `resource_operational_credit.py`, `tool_configuration.py`, `execution_input_versions.py`, `hpc_launch_authentication.py`, `hpc_result_receipts.py`, five functions of `alignment_site_native.py` | 4,017 | See the note on each row. The ported progress provider watches local/HPC practical jobs only |
| U5 | Result-acquisition episode's own operation catalog and dispatch | 7 files in each of the 3 `execution_result_acquisition` homes | 1,233 | Its family dispatch pointed at G5, which is gone |
| U6 | Head operation catalog | `gene_context_evidence/operations.py`, `scientific_commission_catalog.py`, `tool_policy.py` | 217 | `process.revise` is covered by the child selection carrying its own thought pattern and tools; `process.execution` (G10) and the resource-tool commission catalogue are not |

## Present, but A103 can no longer reach it

- 32 flat modules exist only as another axis's copy: 23 `bvbrc_proteome_*` (A101/A104 copies), `a103_hpc.py`,
  `a103_hpc_worker.py`, `hpc_commission_sources.py`, `blast_profile_calculators.py`, `native_blast_masking_result_worker.py`,
  `sequence_masking_calculations.py`, `windowmasker_statistics.py`, `native_driver_runtime.py`, `native_file_capture.py`,
  `episode_receipts.py`, `finding_validity.py`, `investigation_progress.py`.
- 33 surviving A103 files no longer hold some of their HEAD functions, most through the rp103 symbol removals (`runs/rp103-remove-1..5`). The names
  still exist in other axes' copies. The largest: `HomologyJobs` (`homology_jobs.py`), `parse_nhmmer_artifacts` and
  `calculate_nhmmer_scores`, `parse_hmmer_search_artifacts`, `parse_blast_maskinfo`, `project_masking_result`,
  `choose_schedule` and `MonitorCronController` (`hpc_monitoring.py`), `compare_routes`, 10 terminal-handoff functions
  of `terminal_scientific_evidence.py`, `NativeEventProvider`, `NativeTimingInformation`, `ExecutionExpectations`.
- Three removed names exist nowhere: `read_selected_reference_alignment` (U4), `canonical_genomic_overlap_sheet_sha256`
  (`genomic_overlap_contracts.py`), `_without_pending` (`ensembl_acquisition_host.py`).

## Intended removals (counts)

| Category | Files |
|---|---|
| Per-binding task/protocol layer under `gene_context_evidence/**` | 1,134 |
| Duplicate top-level trees (every file has a `gene_context_evidence/` counterpart; 1,150 of 1,280 are identical blobs) | 1,222 |
| `legacy_improvement` and the legacy parent's homology job children | 189 + 2 flat |
| Old runner support, flat (runtime, registries, journals, decision exchange, admission, waiting, child protocol) | 67 |
| The axis's own root (legacy annotation parent), flat | 13 |
| Old task-layer helpers in `library/` | 7 |
| Receipts-inheritance custody adapters, flat | 6 |
| Extra yield estimators (29 per-binding, 2 flat, `library/hpc_continuation.py`) | 32 |
| `method_loop` copy | 15 |
| `vendor/` | 5 |
| Per-axis model provider | 2 |

The runner-provided model tools `episode.history`, `episode.credit`, `episode.estimate_wait`, `episode.annotation_score`
and `episode.monitoring_information` went with the old runner and exist nowhere now. They are counted as intended removal.

## Bringing it back in the new layout

| Group | Support folder | Binding that would offer it |
|---|---|---|
| G1 | New `comparative_systems` domain: `readers/` (native, data_inputs, bundle_resolution, bundle_projection, sheet, bundle_adapter), `calculations/`, `forms/` (the `bvbrc_comparative_systems_handoff_schemas.json` file already sits in `episode_support/forms/`), `records/` (publication), `tools/` (tool_info) | Register the adapter in `episode_support/readers/service_calls/<axis>/bvbrc_appservice_adapters.py`; offered by `api_job_execution` (AppService source) and `execution_result_acquisition` (AppService publication). A103 did not offer it at HEAD, so the owner must name the axis |
| G2 | `sequence_alignment` domain: `readers/` (xmfa, mauve formats, inputs, associations, bundle resolution), `calculations/`, `forms/`, `tools/` | Same route as G1 |
| G3 | `sequence_and_context_sources` domain, beside the surviving `genomic_overlap_contracts.py`, `genomic_overlap_inputs.py` and `native_genomic_overlap_driver.py`: `calculations/`, `readers/` (result views), `jobs/` (result worker, preparation, local), `records/` (capture), `tools/` (tool_info) | `local_job_execution` for launch (the terminal profile is still there); a genomic-overlap result unit in `execution_result_acquisition/acquisition_source.py` |
| G4 | `readers/sequence_and_context_sources/` | Result publication of the `uniprot` service in `execution_result_acquisition` |
| G5 | `acquisition/similarity_search/` and `acquisition/profile_model_preparation/` (bundle capture), `records/similarity_search/` (publication). The result workers still exist under `episode_support/jobs/` | One result unit per family in `execution_result_acquisition/acquisition_source.py`, replacing the old hosts |
| G6 | `acquisition/similarity_search/gene_context_evidence/` as a service of `api_services.build_service` | `api_job_execution` |
| G7 | `readers/similarity_search/` (phmmer_format), `jobs/similarity_search/` (workers, and `HomologyJobs` restored to the A103 copy or shared), `tools/similarity_search/` (results) | `resource_work_submission/local_resource_work_execution` and `resource_result_acquisition` |
| G8 | Restore the four `*_tool_contracts` functions in the A103 tool-info copies under `episode_support/tools/`; restore `bvbrc_homology_tool_info.py` there | `execution_job_submission` (`submission_source.py`) and its three routes, as the typed requested-job alternatives |
| G9 | `episode_support/records/` (one shared copy; it is cross-axis) | Head tool set in `gene_context_evidence/runtime_source.py`; the root binding must supply the run-wide store |
| G10 | `episode_support/jobs/`, over the surviving `execution_memory.py` | Head tool set |
| G11 | `episode_support/jobs/service_calls/gene_context_evidence/progress_provider.py` (AppService target) | The three `execution_progress_assessment` bindings |

## Records used

- `runs/fx103_scripts/deleted_round1.txt`: 42 modules deleted because they imported already-deleted runner apparatus.
- `runs/rp103-reach-4`, `-5`, `-9/stdout.log`: modules deleted as unreachable from the A103 episode/home modules. That
  test followed static imports only; A103 loaded several of these by name (`terminal_scientific_evidence._PROFILES`,
  `native_database_terminal_custody`, `native_driver_runtime`).
- `runs/rp103-remove-1..5/stdout.log`: functions removed from surviving files.
- `runs/claude_ablate/a103_needs.md` ("Deleted first"): the fourth-revision deletions.
- Three files have no deletion record: `a103_homology_resource_adapter.py`, `hpc_result_receipts.py`, `tool_configuration.py`.
