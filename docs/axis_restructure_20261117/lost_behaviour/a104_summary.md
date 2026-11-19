# A104 lost behaviour: HEAD (97308b94c) against the working tree, 18 November 2026

Scope: the 4,162 files at HEAD under `gene_annotation_episode/episodic_workflow/root/a104/`. Rows: `a104.tsv` in this
folder (111 detailed rows, then count rows). Read-only work: no code, test or git change.

Short paths below: `a104/` is `gene_annotation_episode/episodic_workflow/root/a104/`, `ES/` is
`gene_annotation_episode/episodic_workflow/episode_support/`.

## Result

A104 lost its own science tools. The head `evolutionary_history_evidence` now runs over the base `ToolRegistry` only.
The eight `phylogeny.*` tools, the publication and grading of their measurements and the clade characterization are
in no file of the working tree. The credit code that reads those measurements is still there
(`ES/grading/evolutionary_history_evidence/credit.py`, `scoring.py`, `ES/jobs/hpc/evolutionary_history_evidence/hpc.py`),
but nothing can produce what it reads.

| verdict | files |
|---|---|
| lost capability | 83 rows: 77 deleted files and 6 kept files with functions removed |
| uncertain | 28 |
| present (identical content 200, placement target 370, same functions elsewhere or re-implemented 110) | 680 |
| intended removal: per-home episode class layers of the head subtree | 1,458 |
| intended removal: old runner support (runtime, registries, task/protocol layers, journals, receipts, receiving context) | 93 |
| intended removal: legacy_annotation homology job trio | 78 |
| intended removal: prompt and presentation renderers of the old decision protocol | 22 |
| intended removal: wait machinery | 8 |
| intended removal: extra yield estimators 4, per-axis model providers 3, vendor 4 | 11 |
| excluded: top-level duplicate home trees | 1,464 |
| excluded: tests 196, annotation_improvement 26, method_loop 15 | 237 |

The 1,464 duplicate-tree files were checked: each equals its head-subtree copy apart from the home path, except five
`episode.py` files. A per-home file listed as lost appears once in the TSV; its other copies are in the 1,458.

## How the losses happened

Five passes removed working code for a reason other than "this is runner code":

| pass | time (18 Nov) | criterion | record |
|---|---|---|---|
| broken-import cascade | 13:22 | a module whose import no longer resolved was deleted, repeatedly (612 modules) | `runs/claude_r2104_tools/deleted_cascade.txt`, `cascade.py` |
| hand deletions of the same port | about 13:15 | "the UniProt/BV-BRC/protein-view copies" | prose only: `runs/claude_ablate/a104_results.md` lines 102-105 |
| rp104 reachability prune | 15:02-15:05 | no importer anywhere | `runs/rp104-imports-c/stdout.log` (before), `runs/rp104-imports-d/stdout.log` (after) |
| custody reach | 16:52-17:03 | every function that called `run_record_custody` was removed, then the modules this orphaned | `runs/aa_custody_reach_20261118_r2/stdout.log`, `runs/aa_custody_reach_20261118_tools/new_orphans1.txt` |
| in-file removals | not recorded | functions cut from files that were then moved | none for `a104_attachments.py` and `alignment_site_native.py` |

`runs/aa_custody_reach_20261118_tools/tools.py.before` is the A104 `ToolRegistry` as it was before the custody pass
(with both protein tools). Every deleted file is recoverable with `git show HEAD:<path>`.

## Lost capabilities

### G01. Phylogeny tools, measurement publication and grading (the axis's own science)

- What it did:
  - `a104_tools.py` (287 lines): `A104ToolRegistry` with `phylogeny.prepare_analysis`, `request_analysis`, `import_hpc`,
    `inspect`, `measure_placement`, `compare_histories`, `clade_functions`, `compare_placements`; admits received HPC
    results and grades them on receipt.
  - `a104_publication.py` (119): publishes each measurement as a `native.a104.measurement` source with a recomputed,
    immutable grading sheet; publishes its native observation.
  - `a104_interpretation.py` (89): clade composition; stability of placements across analyses.
  - `a104_characterization.py` (207): attaches assayed constructs from received A105 worksheet links to clade members
    by identical amino-acid bytes; characterized/unknown clade sheet.
  - `a104_attachments.py` (133 -> 32 lines kept at `ES/records/evolutionary_history_evidence/attachments.py`): `install`,
    `_qualify`, `refresh` removed. These wrote the per-use attribution that the credit reads.
  - `a104_investigation.py` (193): the nine A104 tasks and the commission context, the report schema and
    `resolve_report`. `a104_scientific_report_validation.py` (22): rejects a report whose credit differs from the
    native credit. `evolutionary_history_evidence/task_projector.py` (16): task -> credit projector.
- Tests at HEAD: `tests/test_a104_evolutionary_episode.py` 22/22, `tests/test_a104_relationship_correspondence.py` 4/4.
- Offered at HEAD: only partly. The head ran over the registry its caller passed in. No code in the axis folder
  constructed `A104ToolRegistry`; the one constructor, `examples/a104_evolutionary_investigation.py`, imported
  `gene_annotation_episode.a104_tools`, which did not exist at HEAD. The test used the catalog and the calculators.
- To bring back:
  - `ES/tools/evolutionary_history_evidence/` (the registry subclass and catalog), `ES/records/evolutionary_history_evidence/`
    (publication, full attachments), `ES/calculations/evolutionary_history_evidence/` (interpretation),
    `ES/readers/evolutionary_history_evidence/` (characterization), `ES/forms/evolutionary_history_evidence/` (tasks,
    report schema).
  - Binding: the head. `runtime_bindings.a104_home` must build the A104 registry; `runtime_source` must run the
    receipt grading after each unit and child return, select the credit by task, and check the report in its result.
  - The old code authenticated through `EpisodeReturnRecords` and the old action context. That part needs the
    episode recorder and the records the episode holds instead.

### G02. Protein conservation and protein phylogeny tools (MUSCLE, IQ-TREE)

- What it did: tools `analyze_protein_conservation` and `analyze_protein_phylogeny`: native run or saved-data
  calculation, result workers, publication, result views, fact catalog.
- HEAD files: `protein_conservation_{tools,publication,result_worker,result_views}.py` (730, 452, 430, 171),
  `protein_phylogeny_{tools,publication,result_worker,result_views}.py` (746, 435, 394, 130), `a104_action_custody.py`
  (315), `a104_native_worker.py` (195), `a104_native_controls.py` (141), `a104_worker_implementation.py` (42),
  `a104_record_identity.py` (25), `evolutionary_result_facts.py` (251), and the tool branches of `tools.py`.
- Still present: the two drivers (`ES/tools/sequence_alignment/muscle_alignment_driver.py`,
  `ES/tools/iqtree_phylogeny_driver.py`) and the two result contracts (`ES/forms/phylogeny/`).
- Tests at HEAD: none under a104. The shared-root copy of the same code had `tests/test_protein_conservation_tools.py`
  18/18, `..._publication.py` 19/19, `..._result_worker.py` 54/54, `tests/test_protein_phylogeny_native_and_retained.py`
  50/53; those test files are deleted too.
- Offered at HEAD: yes, by the A104 `ToolRegistry`, but only when a caller passed protein environments to
  `a104/execution_service_setup.ExecutionServiceFactory`. `A104ServiceFactory` did not.
- To bring back: tools into `ES/tools/phylogeny/`, workers into `ES/jobs/phylogeny/`, publication into
  `ES/records/phylogeny/`, views into `ES/readers/phylogeny/`; the registry branches from `tools.py.before`. Binding:
  the head's `ToolRegistry`, with environments under `services['a104']['tools']`.

### G03. Native phmmer result parsing

- What it did: `phmmer_format.py` (237), `phmmer_result_worker.py` (189), `phmmer_grading_worker.py` (243),
  `homology_results.py` (575): parse native phmmer output, extract measurements, grading rows, paged facts.
- Tests at HEAD: none found. Offered at HEAD: only by the legacy_annotation homology job trio.
- To bring back: `ES/readers/similarity_search/`, `ES/jobs/similarity_search/`; binding: `execution_result_acquisition`.

### G04. Collecting, grading and publishing native results in the results episode

- What it did: `execution.results.status` and `execution.results.collect` for native BLAST, HMMER, BLAST database,
  standard database, masking, BLAST utility and HMMER preparation attempts: capture the bundle, prepare grading,
  publish the selected rows.
- HEAD files: seven `library/native_*_result_records.py` (216-378 lines each), `native_blast_database_acquisition.py`
  (293), `native_blast_database_result_publication.py` (1,088), `native_blast_standard_database_acquisition.py` (293),
  `native_blast_standard_database_result_publication.py` (933), `native_hmmer_acquisition.py` (219),
  `native_hmmer_preparation_result_publication.py` (684), `a104_execution_bindings.py` (158), eleven per-home results
  modules, `LocalFileSourceResults` in `local_file_capture_results.py` (720 -> 35 lines) and others in the TSV.
- Still present but never called: `capture_local_bundle`, `prepare_native_blast_grading`,
  `publish_selected_native_blast_rows`, the HMMER equivalents, and the masking and BLAST utility publication modules.
- Tests at HEAD: `tests/test_a104_installed_result_readers.py` 12/12, `tests/test_a104_protected_reference_guards.py`
  60/60; results homes also run by five results test files (294 tests in total).
- Offered at HEAD: yes, by the three results episodes when the resource configuration declared the native family.
- Now: `execution_result_acquisition/acquisition_source.py` retains verified output bytes (`output_snapshot`) for an
  HPC or local handoff. It parses, grades and publishes nothing.
- To bring back: acquisition into `ES/acquisition/similarity_search/evolutionary_history_evidence/`, publication into
  `ES/records/similarity_search/evolutionary_history_evidence/` and `ES/records/profile_model_preparation/`; binding:
  `execution_result_acquisition` (a collect unit per native family, with the selector in its commission) and the
  local/HPC job bindings for the requested-job schemas.

### G05. UniProt and BV-BRC Data API jobs

- What it did: `api_services.build_service` built `uniprot` and `bvbrc_data` services for launch and results
  (now only `bvbrc_appservice` and `ncbi_blast`); `uniprot_returns.py` (739), `uniprot_return_projection.py` (716),
  `bvbrc_data_host.py` (517), `library/api_record_access.py` (501) selected and delivered their results.
- Still present: the clients `ES/acquisition/sequence_and_context_sources/api_uniprot.py` and
  `ES/acquisition/service_calls/api_bvbrc.py`, and the BV-BRC data readers.
- Tests at HEAD: none found by name. Offered at HEAD: yes, by the API job and results episodes.
- To bring back: the two service kinds in `ES/acquisition/service_calls/evolutionary_history_evidence/api_services.py`;
  projections into `ES/readers/sequence_and_context_sources/`; bindings: `api_job_execution` and
  `execution_result_acquisition`.

### G06. BV-BRC scientific tool information

- What it did: `library/bvbrc_homology_tool_info.py` (111), `library/bvbrc_proteome_tool_info.py` (183),
  `bvbrc_phylogeny_tool_info.py` (208): Homology, GenomeComparison and GeneTree/CodonTree modes as commission contracts.
- Tests at HEAD: none found. Offered at HEAD: Homology and GenomeComparison yes (launch homes' resource tool
  contracts, delivered to the head). GeneTree/CodonTree: nothing under a104 imported it.
- To bring back: `ES/tools/service_calls/evolutionary_history_evidence/`; binding: `api_job_execution`, whose
  assignment form the head fills.

### G07. Head services

- What it did: `shared_information.py` (332) and `shared_information_results.py` (89): information needs and
  evidence deliveries to the shared parent. `scientific_tool_retrieval.py` (233): tool-information retrieval call.
  `execution_planning.py` (97): execution memory, host capacity and planning read (`process.execution`).
- Tests at HEAD: none found. Offered at HEAD: yes, through the old A104 Workflow and the head's catalog.
- To bring back: `ES/records/evolutionary_history_evidence/`, `ES/tools/`, `ES/jobs/evolutionary_history_evidence/`;
  binding: the head.

### G08. Required grading and sheet populations in the A104 literature episodes

- What it did: `evidence_grading.py` (89), `scientific_interpretation.py` (53), `source_repositories.py` (305),
  `population_routes.py` (74), one copy per literature home: a source interpretation was saved together with its
  grading sheets in the same action; about 40 sheet repositories were available.
- Still present for other axes: `ES/literature/grading/experimental_activity_evidence/literature_required_grading.py`
  (and `sample_context_evidence`), `ES/literature/storage/literature_repositories.py` (used by A105, A106, A108).
  A104's own sheet modules are kept (38 storage, 33 calculation, 38 input files under
  `ES/literature/*/evolutionary_history_evidence/`) but no A104 binding imports them.
- Tests at HEAD: none names these modules; the literature homes were run by three test files (513 tests).
- Offered at HEAD: yes. `A104ServiceFactory` built the literature tree with rate, compiled-assay and assay-grading
  populations.
- Now: `published_evidence_assessment/literature_source.py` offers source tools, reasoning commits and children only.
- To bring back: no new support folder; wire `literature_binding.py` / `literature_source.py` (seven bindings) to the
  repositories and the required-grading step.

### G09-G11. Smaller losses

- G09 `literature_kinetic_model_render.py` (54): display of saved kinetic model meanings. Gone from A104, A105 and
  A106. Used at HEAD only by the old literature prompt. Home: `ES/literature/rendering/`.
- G10 `read_selected_reference_alignment` in `alignment_site_native.py` (613 -> 362 lines): capture of a received
  nucleotide alignment from its saved action. Nothing called it at HEAD.
- G11 Result owners of other axes carried in the A104 library copy: fluorescence (5 files), protein structure
  (2 files), genomic overlap (1 file). Offered at HEAD by the results episodes' protected reference access;
  `tests/test_a104_protected_reference_guards.py` 60/60. They belong with the axes that own those result families.

## Uncertain (28 files)

- U1 (16 files): typed-form fact delivery (`*_returns.py`, `alignment_site_returns.py`, `bvbrc_appservice_custody.py`,
  literature rate facts). They copy saved facts through the old parent/child report forms and calculate nothing, so
  they read as old protocol. They also hold the only list of which result facts a parent could ask for.
- U2 (5 files): the legacy HMMER web API job, observer and result services (`hmmer_api` resources). Real service
  code, labelled legacy by its own caller.
- U3 (3 files): live observation of API and AppService jobs by the monitor. The new monitor reads recorded receipts
  only; status requests now belong to the API job and results episodes.
- U4 (4 files): launch rules: BLAST launch requirement checks, the HPC handoff return check, launch authentication,
  and the head's rejection of `sequence.align`.

One operation is declared not ported in the code itself: `hpc.monitor.wait`
(`a104/evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/allocation_runtime.py`, `NOT_PORTED`).
The other thirteen `hpc.*` names found at HEAD are all present.

## Kept but unreachable from any A104 binding

Not counted as lost, because the code exists. No binding or tool calls it:

- `ES/jobs/hpc/evolutionary_history_evidence/hpc.py` (`prepare_request`, `commission`, `import_result`) and
  `ES/grading/evolutionary_history_evidence/scoring.py` (`placement`, `history_comparison`).
- `A104PanelIdentityCredit`, `A104AlignmentSuitabilityCredit`, `A104RobustnessCredit` in `credit.py`: no task selects them.
- `ES/grading/assay_grading_read.py` (`A104AssayGradingReader`).
- `ES/jobs/evolutionary_history_evidence/practical_execution_operations.py` (`LocalPracticalOperations`, native BLAST,
  HMMER, masking and utility plans).

## Method and limits

- Each HEAD file was matched to the working tree by identical content, then by its `runs/placement_plan/placement.tsv`
  target, then by its top-level function and class names (names shared by more than three A104 files were ignored).
- Files with no match were read at HEAD and judged by what they do. The 1,458 per-home layer files were judged by
  module outline, not line by line.
- Kept files were compared by top-level names and line count; twelve had shrunk by 5% or more. Four of those are in
  the TSV; the losses in `tools.py` and `api_services.py` were found by reading their diffs. The other eight lost
  runner-related parts or parts that survive elsewhere: `ExecutionExpectations`, two literature yield controllers,
  the model settings in `defaults.toml`, three received-cell methods of the controlled-response storage, the prompt
  `instructions` function, `configured_tools` (kept in `ES/configuration/public_configuration.py`), the API entries
  of the merged launch index (A104's own index is intact under `ES/instructions/launch/evolutionary_history_evidence/`),
  and ten terminal handoff and observation readers of `terminal_scientific_evidence.py` (kept in the A102 copy
  only). A method removed inside a kept class would not show unless the file shrank by 5% or more.
- "Re-implemented" (AppService records, job and progress providers, API job source) means new code with the same
  job exists; it was not compared function by function.
- No test was run.
