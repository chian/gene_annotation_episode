# A102: capabilities at HEAD that exist nowhere in the working tree (18 November 2026)

Scope: `gene_annotation_episode/episodic_workflow/root/a102/` at HEAD (97308b94c), 3,441 files. Rows: `a102.tsv`
in this folder. Read-only work: `git ls-tree/show/grep/diff` on HEAD and `grep/find` on the working tree; no code
or test was changed and nothing was run.

A102 lost real capabilities (104 rows, six groups plus literature binding behaviour and small removals): the literature structural sheet, four of its five API
services with the MSA/MetaCATS/XMFA analysis code, the native protein-structure result route, the alignment-site
returns, the structural resource adapter, and a set of native BLAST/HMMER result hosts that A102 held but did not
offer. A further 23 rows are uncertain.

## How each file was judged

1. Current home by path: same path, the `runs/placement_plan/placement.tsv` target, or the merged shared copy.
2. Otherwise by content: every top-level `def`/`class` name of the HEAD file was looked up in all non-test `.py`
   files under `gene_annotation_episode/`, `episode_runtime/`, `method_loop/`, `yield_control/` and `tools/`.
   A file counts as present only when a same-named file defines the names.
3. Files kept by placement were diffed against HEAD to find removed functions.
4. Dotted operation and tool names (`literature.structure.populate`, `resource.inspect`, ...) in HEAD a102 were
   looked up in the whole tree; 52 names exist nowhere now.
5. "Offered at HEAD" was read from the HEAD import graph (static, function-level and string module references)
   and from the construction code of the HEAD homes, not from the prune logs.

Not done: the 1,058 per-home task/protocol files of the head tree were not compared operation by operation with
the ported runtimes, and the 177 same-named copies of other axes were compared by definition names and line
counts only (154 have equal line counts).

## Counts

| set | files | verdict |
|---|---|---|
| top level, `library/`, data folders | 599 | 193 present at placement target; 190 present as a shared or other-axis copy; 7 present under another name; 92 lost; 20 uncertain; 97 intended removal (79 runner, 10 yield/wait estimators, 2 model providers, 6 vendor and package marker) |
| `structural_homology_evidence/**` (non-test) | 1,216 | 71 at the same path (34 `episode.py` rewritten as ported bindings); 48 lost (7 rows); 39 uncertain (2 rows); 1,058 intended removal (per-home task/protocol layer) |
| function-level removals inside kept files | 6 rows | 5 lost, 1 uncertain |
| top-level duplicate trees (outside scope) | 1,170 | intended removal; 1,077 identical to the head tree at HEAD, 93 differ only in home-path lines |
| `annotation_improvement/`, `method_loop/` (outside scope) | 35 | intended removal |
| tests and fixtures (outside scope) | 421 | not assessed; 286 are fixtures |

## Lost capabilities

### G1. Literature structural sheet (former A111) and the head's typed structural return

- What it did: read a deposited structure model a publication names (coordinate CIF and validation XML), compute
  six geometry and local-fit components, store them as structure cells with source receipts, and deliver them
  into the A102 head's typed return, which was validated against the delivered evidence.
- HEAD files: `literature_structure_inputs.py` (466), `literature_structure_calculations.py` (263),
  `literature_structure_storage.py` (304), `literature_structure_types.py` (21), `a102_literature_bindings.py`
  (43), `a102_experimental_evidence.py` (177), `a102_structural_report.py` (127), `_structure_selected` in
  `literature_task_selection.py`; in the head tree `structural_sheet_operations.py` (7 homes),
  `received_structural_context.py`, `report_validation.py`. Fixtures `tests/fixtures/literature_structure` (3).
- Baseline tests: `test_literature_structure_inputs.py` 172/172, `_calculations.py` 62/62, `_storage.py` 37/37,
  `_assessments.py` 2/2, `_integration.py` 0/4 (4 failed at baseline), `test_source_role_partition.py` 490/490.
- Offered at HEAD: yes. Each of the seven literature homes mixed in `SourceStructuralSheetOperations` and its
  `source_operations.py` dispatched tool `literature.structure.populate`; the head's `internal_summary.py`,
  `received_evidence.py` and `to_parent.py` used the typed report.
- Deleted by: reachability prune (`runs/rp102-reach2..5/stdout.log`, UNREACHED), because the ported
  `literature_binding.py` has no structural sheet operation.
- To bring back: reader to `episode_support/literature/inputs/`, calculations to
  `literature/calculations/`, repository to `literature/storage/` (one copy each, beside
  `literature/prompts/literature_structure_prompt.py`, which survived). The repository imported the deleted
  `a102.communication` and `episode_bindings` and must be ported off them; it also imports
  `literature_rate_storage` (which imports `literature_sheet_updates`); both survive only as other axes' copies.
  Report schema to `episode_support/forms/structural_homology_evidence/`. Offering bindings:
  `structural_homology_evidence/published_evidence_assessment/literature_binding.py` (add
  `literature.structure.populate` to its tools and dispatch it in `literature_source.py`) and the head
  (`contract_binding.py` report and `runtime_head.py` result) for the typed return and its validation.

### G2. API services other than NCBI BLAST, and the BV-BRC MSA / MetaCATS / XMFA analysis code

- What it did: A102's API job execution accepted five service kinds (`bvbrc_appservice`, `uniprot`,
  `bvbrc_data`, `bvbrc_minhash`, `ncbi_blast`). For each it kept custody of the selected operation, published
  the native result and returned typed facts. The AppService path covered Homology, MSA and MetaCATS: native
  table and XMFA parsers, entropy, contingency and group-effect calculators, graders and typed returns.
- HEAD files (55 rows, about 21,600 lines): `api_service_execution.py` (1,083), `api_execution.py` (936, HMMER
  API), `uniprot_returns.py`, `uniprot_return_projection.py`, `bvbrc_data_host.py`, `bvbrc_minhash_host.py`,
  `bvbrc_appservice_{host,monitor,custody,publication,records}.py`, `bvbrc_homology_returns.py`,
  `bvbrc_alignment_*` (8), `bvbrc_metacats_*` (14), `bvbrc_msa_*` (9), `xmfa_*` (7), `bvbrc_contingency_math.py`,
  three alignment presentation modules, and `build_service` plus four service validations removed from
  `api_services.py`. Fixtures `tests/fixtures/bvbrc` (243 native MSA/MetaCATS outputs).
- Baseline tests: none for the four services. `test_private_api_tasks.py` 216/216, `test_private_launch_tasks.py`
  252/252 and `test_private_results_tasks.py` 366/366 configured `ncbi_blast` only; no a102 test read the bvbrc
  fixtures.
- Offered at HEAD: by configuration only. `APIConfiguration` in every execution home built `APIServiceExecution`
  for the configured `kind: api` resources and `api_services.build_service` accepted all five kinds. No A102
  test or entry module configured one of the four. `bvbrc_alignment_tool_info.py` had no importer at all.
- Deleted by: fx102 (`runs/fx102/del_top.txt`, hosts and returns) and the reachability prune (`rp102-reach2..5`).
  The ported `api_job_execution/configuration.py` states "The only A102 API service is `ncbi_blast`".
- To bring back: contracts to `episode_support/forms/service_calls/`; parsers
  and inputs (`*_formats`, `*_inputs`, `xmfa_*`) to `readers/service_calls/` and `readers/sequence_alignment/`;
  calculators and `bvbrc_contingency_math` to `calculations/sequence_alignment/`; graders to
  `grading/sequence_alignment/`; hosts, custody, publication and returns to
  `records/service_calls/structural_homology_evidence/`. The service clients themselves survive as shared or
  other-axis copies (`acquisition/service_calls/api_bvbrc.py`, `.../partner_presence_evidence/api_bvbrc_appservice.py`,
  `acquisition/similarity_search/api_bvbrc_minhash.py`, `acquisition/sequence_and_context_sources/api_uniprot.py`).
  Offering bindings: `execution_job_submission/api_job_execution` (three homes) and
  `resource_work_submission/api_resource_work_execution` through `configuration.build_api_service`, and
  `execution_result_acquisition/acquisition_source.py` for publication. These modules exist in no other axis
  either, so one shared copy would serve all axes.

### G3. Native protein-structure results and local file capture

- What it did: the results episode acquired a selected native protein-structure result,
  qualified it with the result worker, published the requested typed rows with immutable receipts, and
  later episodes read them back under an explicit receiving authority. `LocalFileSourceResults` captured selected
  output files of a local job as source records.
- HEAD files: `native_protein_structure_results.py` (666), `native_protein_structure_returns.py` (701),
  `protein_structure_result_receipts.py` (1,228), `protein_structure_projection_publication.py` (75),
  `protein_structure_execution_information.py` (106), `a102_execution_bindings.py` (31), class
  `ProteinStructureActionRecords` (663 lines removed from `protein_structure_action_records.py`),
  `local_file_capture_results.py` (717; 35 lines of constants remain), `file_capture_receipt_control.py` (112),
  `received_native_file_inputs.py` (84), `terminal_native_file_capture.py` (71),
  `molecular_sequence_input_bindings.py` (288), `received_input_frames.py` (157), and
  `retained_protein_reader.py` (15 homes). Fixtures `tests/fixtures/protein_structure_result_worker_393` (9).
- Baseline tests: `test_private_results_tasks.py` 366/366; `test_native_task.py` 31/31 in each of six homes.
- Offered at HEAD: yes. `APIConfiguration` built the result hosts in every execution home, the results home
  offered `protein_result_catalog()`, and the old services wrapped every tool call in
  `protein_structure_invocation(ProteinStructureActionRecords(...))`. `terminal_native_file_capture.py` alone had
  no importer.
- Effect now: nothing calls `protein_structure_invocation`, so the protein-structure tools that use saved or received inputs (`_prepare_saved_protein_work`) and any replay of a saved structure operation return
  `protein_structure_input_authority_required` (`tools/protein_structure/protein_structure_tools.py:900-901`, `tools/structural_homology_evidence/tools.py:660-662`).
- To bring back: hosts, receipts, returns and the records class to `episode_support/records/` beside `protein_structure_publication.py`
  (the class subclassed the deleted `EpisodeReturnRecords`, so its receiving checks need a Store-based form);
  file capture to `records/local_execution/`. Offering bindings: `execution_result_acquisition/acquisition_source.py`
  (a protein-result unit beside `output_snapshot`), the local job runtime for the `native_protein_structure`
  resource binding, and `runtime_head.py`, which must set the input authority around `execute_async`.

### G4. Alignment-site returns

- What it did: requested finite views of saved alignment-site results as fact sources of the head's typed
  return, and exact own site-operation results for parent-requested facts.
- HEAD files: `alignment_site_returns.py` (717), `alignment_site_action_records.py` (274).
- Baseline tests: head `test_private_head_task.py` 87/87, `test_private_scientific_boundaries.py` 14/14.
- Offered at HEAD: yes, by the head (`scientific_contracts.py`) and the old services.
- To bring back: `episode_support/readers/sequence_alignment/structural_homology_evidence/` and
  `records/structural_homology_evidence/`; offering binding: the head.

### G5. Native BLAST database, masking, utility and HMMER result hosts (held but not offered by A102)

- HEAD files (15, about 7,200 lines): `native_blast_{database,standard_database}_{acquisition,result_publication,results}.py`,
  `native_blast_database_returns.py`, `native_blast_{masking,utility}_results.py`, `native_blast_results.py`,
  `native_hmmer_{acquisition,results}.py`, `native_hmmer_preparation_{failure_views,result_publication,results}.py`.
- Offered at HEAD: no. No A102 home or registry constructed them, and `APIConfiguration` rejected every `native_*`
  resource binding except `native_protein_structure` (`a102_execution_foreign_native_binding`). No a102 test.
- They exist nowhere in the tree now, so the loss is real for the axes that run native BLAST and HMMER
  (A101, A103, A104, A107); it belongs in their reports, not in an A102 binding.

### G6. A102 structural resource adapter

- What it did: launch children executed an exact structural job and returned a checked handoff; results children
  collected its native numerical publications (`a102.native.execute`, `.status`, `.collect`,
  `a102.progress.snapshot`), with `A102ResourceCredit` and `A102ProgressProvider`.
- HEAD file: `a102_resources.py` (302).
- Baseline tests: `test_private_resource_tasks.py` 1,400/1,400, `test_operational_configuration.py` 44/44; the
  three whole-workflow files were skipped or failing at baseline.
- Offered at HEAD: yes, to the five resource homes through `resource_adapters`.
- To bring back: `episode_support/jobs/local_execution/structural_homology_evidence/`; offering bindings:
  `resource_work_submission/local_resource_work_execution` and `resource_result_acquisition`. Those now run
  model-written `exec_command` units on `A102LocalJobRuntime`, so the owner should say whether the typed adapter
  is still wanted beside it.

### Behaviour of the A102 literature bindings (code survives for other axes, not offered by A102)

- `source_operations.py` and `source_contracts.py` (7 homes): pubmed-only `public.ncbi.search`,
  `execution.estimate` for the xlsx readers, the experimental-database tools, confinement of reads to the
  assigned page. `source_interpretation.py` (7 homes): the `verified_source_leads` reasoning action.
  `commissioning_page_assignment.py` (3 homes): the page assignment of reading children.
- Baseline tests: `test_private_source_family.py` 738/738, `test_source_role_partition.py` 490/490,
  `test_literature_task_fact_boundary.py` 11/11.
- The ported A102 `literature_binding.py` has a scope, a question and a tool subset only. The A105, A106 and
  A108 ported `literature_source.py` / `literature_binding.py` still carry page assignment, source leads and
  `execution.estimate`, so the A102 binding can follow the same form; `lead_schema` and `validate_lead` are in
  `episode_support/literature/grading/literature_task_credit.py`.

### Smaller removals inside kept files

- `structure.model_request` tool removed from `evidence_operations.py` (was `a102_tools.py`).
- `read_received_result` removed from `hpc_result_receipts.py`; it fed HPC results into A102 attributions.
- `read_selected_reference_alignment` and four helpers (250 lines) removed from `alignment_site_native.py`;
  nothing used it at HEAD.

## Uncertain (23 rows)

- Literature credit: the homes projected `LiteratureTaskCredit` with a per-task controller; the port credits
  `A102StructuralCredit`. This changes what an A102 literature episode is measured by.
- Received attributions: the old runner called `received_structural_attributions` and `received_attributions`
  after a child return. Both hooks still exist in `evidence_operations.py` and no A102 binding calls them; the
  A103 port does call its hook.
- Resource operations `resource.capabilities`, `resource.inspect`, `resource.check_handoff` (5 homes).
- `execution_progress.py` (976): rewritten as `job_provider.py`; AppService, minhash and HMMER targets not carried.
- `shared_information.py` (321) and its five `shared.*` tools; `scientific_tool_retrieval.py` (225);
  `execution_planning.py` and `planning_selection.py` (`process.execution`); `a102_structural_catalog.py`;
  `structural_homology_evidence_reports.py` (typed process-result facts; `a102_needs.md` item C5).
- Decision-text presentation (7 modules, about 2,200 lines) that fixed what each A102 model was shown, and five
  literature presentation modules that nothing imported at HEAD.

## Already recorded elsewhere and not repeated as rows

- `local_resources.py`: A102's private v2 (`cpu_threads` limit) is replaced by the shared v3 (see
  `per_file_comparison/a102_summary.md`).
- `library/tests/test_hpc_calculations.py` (7 passed) was retired although `hpc_prediction`,
  `hpc_resource_prediction` and `hpc_monitoring` still exist; the code is present, only the checks are gone.

## Deletion records

- `runs/claude_ab102/deleted.txt` (1,340 paths): runner layer and duplicate trees.
- `runs/fx102/del_top.txt`, `del_top2.txt`, `deleted_round1.txt` (457 paths): result hosts, returns and head home files.
- `runs/rp102-reach2..5/stdout.log`: modules listed UNREACHED and then deleted.
- 40 top-level modules and several head files have no deletion record in any of these.
