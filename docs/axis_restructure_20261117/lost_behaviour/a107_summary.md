# A107 lost behaviour: HEAD (97308b94c) against the working tree (18 November 2026)

Scope: non-test files at HEAD under `gene_annotation_episode/episodic_workflow/root/a107/`.
One row per file in `a107.tsv` (columns: head_path, lines, what_it_did, baseline_tests, deleted_by, verdict,
who_used_it_at_HEAD, group). Read-only work: no code, test or git change.

Every lost file is still in HEAD (the deletions are uncommitted), so each can be read back with
`git show HEAD:<head_path>`.

## Counts

| part of the HEAD tree | files | treatment |
|---|---|---|
| top-level modules, `library/`, `knowledge/`, instruction libraries, specs, `vendor/` | 926 | one row each, judged |
| head tree `partner_presence_evidence/` (the 29 homes) | 971 | one row each: 59 same path, 912 old task/protocol mixins |
| top-level duplicate trees (`execution_*`, `hpc_work_planning`, `published_evidence_assessment`) | 928 | excluded by the task |
| `annotation_improvement/`, `method_loop/` | 35 | excluded by the task |
| `tests/` and fixtures | 757 | excluded by the task |

Verdicts over the 1,897 judged files:

| verdict | files | lines |
|---|---|---|
| lost_capability | 112 | 37,190 |
| uncertain | 33 | about 7,400 |
| present (identical content 140, placement target 275, same definitions in another file 135, same path 59, other 8) | 617 | |
| intended_removal | 1,135 | |

Intended removals by category: old runner (runtime, task/protocol mixins, journals, bindings, prompt renderers,
private reconstruction) 1,009; receiving_context / receipts inheritance 83; typed-return protocol modules
(`*_returns.py`) 23; old execution support that the port re-expressed 8; vendor 5; extra yield estimators 5;
per-axis model providers 2.

## How the lost files were deleted

- **Reachability prune `rp107`** (14:55 to 14:57 on 18 November). `runs/rp107-reach-145521/stdout.log` prints
  `ROOTS []` and 161 `UNREACHED` modules. Six were rescued by the third pass; `runs/rp107-reach4-145748/stdout.log`
  shows three left, so about 152 modules were deleted because nothing imported them. 58 of the 112 lost files and
  11 of the uncertain files are on that list. The list was computed after the second port had already deleted the
  callers, so "unreached" meant "its caller was just deleted".
- **Second port** ("old shared-root apparatus deleted"), recorded only in prose at
  `runs/claude_ablate/a107_needs.md:105-123`: all `*_returns`, `*_results`, `*_result_publication`, hosts,
  receipts, the received-execution FBA / genomic-overlap / fluorescence / NMF / ATAC / chromatin stacks and the
  lumpy / macs2 / flux-balance request bindings. The other 54 lost files are not on the `rp107` list and match
  these kinds. No per-file record exists, so the pass is inferred for them.

## Lost capabilities

Where a group says "same-named copy tests", the baseline tests exercised the `root/library` or generic copy of
the module, not the A107 copy. Counts are passed/tests from `docs/verification_20261116/results_per_file.tsv`.

### 1. Native result collection for the execution families A107 ran

At HEAD the `execution_result_acquisition` homes offered `execution.results.status` and
`execution.results.collect` per family. `ResultsConfiguration` (`execution_result_acquisition/configuration.py`)
admitted exactly these native bindings: native_blast, native_blast_masking, native_blast_utility,
native_blast_database, native_blast_standard_database, native_hmmer, native_hmmer_preparation, native_infernal,
native_infernal_preparation, native_rna_structure, native_expression_nmf. `work_operations.catalog()` chose the
family catalogue. Collect captured the sealed native bundle, ran the deterministic reader and grader in a worker,
filled the numerical sheet and published the assigned rows.

The current `execution_result_acquisition/acquisition_source.py` acquires only output snapshots of a receipt
(bytes checked against size and sha256) and API or AppService publications. No binding runs a family reader,
grader or publication.

| group | what it did | HEAD files (lines) | baseline tests | still present below it |
|---|---|---|---|---|
| Infernal preparation (13 files, 6,278) | readers of cmbuild / cmcalibrate / cmstat / cmemit output, model extraction, statistics and emission calculations, artifact sheet, bundle capture, grading worker, publication, results operation | `infernal_preparation_{artifacts,calculations,emission,emission_calculations,models,statistics,result_views}.py`, `native_infernal_preparation_{acquisition,worker,result_worker,result_publication,results,failure_views}.py` | same-named copy tests: 9 files 254/254 plus `root/tests/test_native_infernal_preparation_reference_visibility.py` 0/21; a107 `test_original_result_adapter_role_boundaries.py` 65/65 (retired as fake) | driver, tool info, contracts, job schema, local plan |
| Infernal search results (5 files, 2,142) | capture of the cmsearch / cmscan bundle, result views and selector, grading worker, publication of selected rows, results operation | `infernal_native_result_views.py`, `native_infernal_{acquisition,result_worker,result_publication,results}.py` | `tests/test_native_infernal_acquisition.py` 95/95, `tests/test_native_infernal_publication.py` 1/1 | driver, tool info, contracts, `infernal_search_grader`, inputs, cells |
| RNA structure (7 files, 2,004) | parser of native RNA records and Biomni prediction text, prediction and feature sheets, scan calculations, bundle capture, grading worker, publication, results operation, tool contracts | `rna_structure_native.py`, `rna_structure_scan_calculations.py`, `native_rna_structure_{acquisition,result_worker,result_publication,results,tool_info}.py` | `tests/test_native_rna_structure_worker.py` 20/20 (imports the A107 `rna_structure_native`), `tests/test_native_rna_structure_contracts.py` 40/40 | driver, local plan, worker, contracts, `rna_structure_calculations`, topology, result views |
| RNA structure comparison (5 files, 1,805) | site, pair and energy change calculations between two retained structures, operand authentication, worker, publication, results operation | `rna_structure_comparison_{calculations,operands,worker,publication,results}.py` | a107 `test_original_result_adapter_role_boundaries.py` 65/65 (retired as fake) names the results class; no test of the calculations found | comparison contracts, inputs, views |
| Expression NMF results (11 files, 2,277) | independent recalculation from saved W and H (reconstruction, residuals, component measurements), result worker, worker plan, native file capture, job-input validation, receipts and controls, tool contracts, results operation | `expression_nmf_{calculations,result_worker,operands,execution_information,result_receipts,receipt_control,runtime}.py`, `native_expression_nmf_{preparation,capture,tool_info,results}.py` | `tests/test_expression_nmf_numerics.py` 32/33, `root/tests/test_expression_nmf_execution_integration.py` 0/5 | driver, common, inputs, sheet, result views, storage, artifacts |
| BLAST database and standard database (6 files, 3,373) | bundle capture, grading preparation and publication of selected rows, results operation | `native_blast_{database,standard_database}_{acquisition,result_publication,results}.py` | a107 `test_original_result_adapter_role_boundaries.py` 65/65 (retired as fake) | both result workers, calculators, driver, tool info |
| HMMER preparation results (3 files, 1,283) | grading preparation and publication, failure views, results operation | `native_hmmer_preparation_{result_publication,results,failure_views}.py` | same test file as above | acquisition, result worker, result views |
| Results operations over kept publications (5 files, 2,164) | the collect operation for BLAST, HMMER, masking and utility; HMMER bundle capture | `native_{blast,hmmer,blast_masking,blast_utility}_results.py`, `native_hmmer_acquisition.py` | a107 `test_original_result_adapter_role_boundaries.py` 65/65, `test_cross_lineage_received_records.py` 108/108 (both retired as fake) | result workers and `*_result_publication` for BLAST, HMMER, utility; nothing calls them now |

To bring back: restore each file under the folder of its kind, beside its surviving siblings.

- readers: `episode_support/readers/profile_model_preparation/`, `readers/similarity_search/`, `readers/rna_structure/`
- calculations: `episode_support/calculations/profile_model_preparation/`, `calculations/` (RNA), `calculations/expression_and_perturbation/`
- capture: `episode_support/acquisition/{similarity_search,profile_model_preparation}/partner_presence_evidence/`
- workers: `episode_support/jobs/{similarity_search,profile_model_preparation}/partner_presence_evidence/`, `jobs/` (RNA, NMF)
- publication and receipts: `episode_support/records/similarity_search/partner_presence_evidence/`, `records/expression_and_perturbation/`
- tool contracts: `episode_support/tools/...` beside each driver

Offer it from `root/a107/partner_presence_evidence/execution_result_acquisition` (and its two nested copies under
HPC planning and allocation): a result-collection unit in `acquisition_source.py` that, for a local or HPC
handoff of a native family, runs that family's capture, worker and publication. The `*_results.py` classes are
written against the old `owner` object and need re-expressing; the readers, calculators, workers and publications
are not runner code.

### 2. Partner literature population is no longer offered

`library/partner_source_contracts.py` registered `literature.partner.populate` and
`literature.partner.source.populate` for the seven literature homes (28 importing home files), with
`library/literature_partner_operand_information.py` (operand descriptions on the population schema) and
`library/partner_source_task.py` (lead instruction and family selection). All three were on the `rp107` list.

The repository, calculations, inputs and sheet records are present under `episode_support/literature/`, and the
9 population tests pass. But `published_evidence_assessment/literature_binding.py:26-27` states that no
`A107ToolRegistry` operation exposes the populations, while `axis_instructions.py:26-27` still tells the model to
use them.

To bring back: put the catalogue entries and operand information in `episode_support/literature/forms/` (or
`literature/readers/` beside `literature_task_families.py`) and register both operations in the literature
bindings' tool subset in `literature_binding.py`.

### 3. A107 component report

`component_axis_reports.py` (388 lines) built the head's report: `resolve_report`, `received_reports`,
`current_scoring_sheets`, and the dependence descriptions `dependence`, `native_dependence`, `cross_dependence`
(shared origins between literature partner sheets and native detection or expression components, never summed)
and `mark_native_execution`. Used by the head's `from_parent.py`, `internal_summary.py`, `report_integrity.py`
and `component_axis_workflow.py`. Test: `tests/test_component_native_return_instructions.py` 6/6.

The head now returns `{credit, finding}` with assessment references; nothing computes the dependence
descriptions.

To bring back: `episode_support/findings/partner_presence_evidence/`, called by `head_cycle.py` when it builds
the result.

### 4. API services dropped from A107

- `api_execution.py` (936 lines): HMMER web API launch and result-page operations (`HMMERAPIExecution`).
  Same-named copy test `tests/test_api_execution.py` 27/27.
- `uniprot_returns.py`, `uniprot_return_projection.py`, `bvbrc_data_host.py`, `bvbrc_minhash_host.py`: custody
  and fact projection for UniProt, BV-BRC Data and MinHash calls. `tests/test_uniprot_return_projection.py` 58/58.
- `bvbrc_homology_tool_info.py`: Homology service modes as launch and results contracts (on the `rp107` list).
- Narrowing inside a kept file: `api_services.py` built uniprot, bvbrc_data, ncbi_blast, bvbrc_minhash,
  rfam_batch and bvbrc_appservice at HEAD. The placed copy builds only bvbrc_appservice, ncbi_blast and
  rfam_batch. The three clients still exist in `episode_support`, but only gene_context_evidence builds them.

All were used through `api_service_execution.APIServiceExecution`, configured by every execution home.

To bring back: restore the three services in
`episode_support/acquisition/service_calls/partner_presence_evidence/api_services.py`; put the UniProt projection
in `episode_support/readers/sequence_and_context_sources/`; offer them from
`execution_job_submission/api_job_execution` and `execution_result_acquisition`.

### 5. Result stacks A107 reached only through received results

`ResultsConfiguration` rejected these native bindings as foreign, so A107 never launched them. Every home's
`received_execution_information` hook reached them through
`library/received_execution_information/historical_receiving_owner.py`, to re-read results produced elsewhere.
The receiving owner is an intended removal; the readers, calculators and workers below it are real code and
exist nowhere in the tree now.

| group | HEAD files (lines) | baseline tests |
|---|---|---|
| Flux balance (14 files, 4,104): `parse_biomni_fba_csv`, `parse_fba_capture`, `calculate_flux_balance_sheet`, result views, worker, capture, worker plan, model tools, contracts | `library/flux_balance_*.py`, `library/native_flux_balance_{capture,preparation}.py` | a107 `test_genuine_result_worker_boundaries.py` 11/11; same-named copy tests 10 files 406/406 |
| Genomic overlap (11 files, 3,277): overlap component calculations, result views, worker, selector validation, capture, worker plan, receipts | `library/genomic_overlap_*.py`, `library/native_genomic_overlap_{capture,preparation,local}.py`, `genomic_overlap_result_receipts.py` | same a107 test; `tests/test_genomic_overlap_calculations.py` 18/18, `tests/test_genomic_overlap_analytic_capture_loss.py` 50/50 |
| ATAC differential (7 files, 1,642): native capture, worker plan, local plan, receipts, selector, control JSON | `library/native_atac_differential_{capture,preparation,local}.py`, `library/atac_*.py` | a107 `test_retained_native_request_contracts.py` 10/10; `tests/test_atac_differential_result_worker.py` 25/25 |
| Chromatin interaction (6 files, 1,632): the same set | `library/native_chromatin_interaction_{capture,preparation,local}.py`, `library/chromatin_*.py` | none found |
| Fluorescence (7 files, 787): result receipts, worker preparation, results operation, tool contracts | `fluorescence_result_receipts.py`, `native_fluorescence_{results,preparation}.py`, `library/fluorescence_*.py` | `tests/test_fluorescence_result_worker.py` 18/18 |
| Request contracts (2 files, 255): lumpy request schema and validation, HOMER binding metadata | `library/lumpy_request_contracts.py`, `library/homer_binding_metadata.py` | a107 `test_retained_native_request_contracts.py` 10/10 |

The generic `gene_annotation_episode/` modules for ATAC and chromatin calculations, views and result workers
remain; the capture, plan and receipt layers above them do not. The canonical owners of FBA and genomic overlap
are other axes (A110, A103), so the restoring home is theirs: `episode_support/readers`, `calculations` and
`jobs` under the metabolic-feasibility and sequence-and-context functions. A107 would need them again only if
reading another axis's results is restored.

## Uncertain (33 files)

- **Head decision operations with no replacement (10 files, 2,561 lines).** `waiting.py`,
  `inprocess_waiting.py`, `decision_waiting.py`, `shared_information.py`, `shared_information_results.py`,
  `composition_information.py`, `episode_contract_information.py`, `decision_history.py`,
  `scientific_tool_retrieval.py`, `execution_planning.py`. They gave the head `wait`, `shared.*` information
  operations, `episode.return_contract`, `episode.operation_contract`, `episode.history`,
  `episode.estimate_wait` and `execution.estimate`. The modules are old-runtime code, but
  `head_cycle.py:47-48` says the cycle has none of these, and no file in the tree contains the `shared.*` or
  `episode.*` names. `execution.estimate` survives only for other axes.
- **Execution binding declarations (6 files).** `a107_execution_bindings.py`, `a107_blast_execution.py`,
  `execution_input_versions.py`, three small `library/` schema modules: the per-family job schemas, operation
  contracts and resource-binding validation of the old execution episode.
- **Request bindings and owners reachable only through received results (11 files).**
  `flux_balance_request_binding.py`, `lumpy_request_binding.py`, `macs2_peak_request_binding.py`,
  `molecular_sequence_{ordinary,results,input_bindings}.py`, two `library/molecular_*`,
  `native_protein_structure_results.py`, `protein_structure_result_receipts.py`,
  `library/protein_structure_configured_tool_contracts.py`. Tests: `test_molecular_sequence_ordinary_primer_owner.py`
  15/15, `test_retained_molecular_contracts.py` 16/16.
- **Local file results (2 files).** `local_file_capture_results.py` went from 718 lines to 35 (only the
  operation descriptions remain) and `file_receipt_control.py` is gone. The new output-snapshot unit covers whole
  files; windowed reads (`full_window_key`, `whole_file_bridge`) are not re-expressed.
- **Single files.** `library/hpc_handoff_report_contract.py` (HPC launch must return the original handoff fact;
  nothing calls an equivalent), `library/terminal_native_file_capture.py`, and
  `alignment_site_native.py` (kept, but `read_selected_reference_alignment` and its helpers were removed while
  its `__all__` still names it; nothing in A107 called it at HEAD).

## Limits

- The 912 old task/protocol mixin files of the 29 homes were classified by kind, not compared method by method
  with the ported runtime sources. Spot checks: all `hpc.*` operation names and all 36 tool names referenced by
  the HEAD registries still occur in the tree.
- "Present" for 135 files rests on every top-level definition name existing in one current file, not on a
  content comparison. Five such matches were coincidental and were reclassified by hand.
- 48 `library/received_execution_information/historical_*` files are counted as the intended receiving-context
  removal (34 more are present under their non-historical names). For the Mauve, XMFA, genome-alignment, comparative-systems, annotation, assembly, influenza-HA,
  subspecies and variation contracts among them, no non-historical original exists anywhere in the tree now;
  those originals belonged to other axes at HEAD (A103 and `root/library`), not to A107.
- Of 380 public names (12 characters or longer) defined by the lost and uncertain files, 365 occur nowhere in
  `gene_annotation_episode/`, `episode_runtime/`, `method_loop/` or `yield_control/`; the 15 that do are generic
  names such as `configuration` and `report_schema`.
- The 22 `*_returns.py` modules (requested-fact projection across the old typed returns) are counted as the
  intended protocol removal. With the `{credit, finding}` return form, a parent can no longer request a family's
  numerical facts from a results child.
