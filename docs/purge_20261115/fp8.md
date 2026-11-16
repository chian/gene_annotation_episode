# fp8 — a108 and a110: code that fingerprints the codebase removed (16 November 2026)

Areas: `gene_annotation_episode/episodic_workflow/root/a108/` (`R8/`) then `.../root/a110/` (`R10/`). Brief: `FP_BRIEF.md`;
shapes: `fp_recipe.md` sections 1-21 (a108/a110 additions appended as section 22). Comparison base: commit `e8bf4820f`
(HEAD at start). No git writes, no sub-agents, one launcher command at a time (slot `fp8`). Deleted tests:
`fp8_deleted_tests.tsv` (1 parametrized case, 2 orphan helper files). Per-file gate table: `fp8_gate_results.tsv`.
The untracked `R10/tests/fixtures/genuine_fba360/` was not touched.

Change against `e8bf4820f`: a108 66 files (+104 −456; 3 modules deleted); a110 167 files (+321 −3,218; 4 product modules,
1 JSON table, 2 test helpers deleted).

## How
Three-way merges (`git merge-file`, arm name replaced) from the sibling whose pre-task file is closest
(scratch `<scratchpad>/fp8/plan_merge.sh`, `do_merge.sh`; a110 also by basename across siblings and the shared root,
`basename_cands.sh`). Every clean merge diff was read before it was taken. Files whose a108/a110 copy had no fingerprint
content (a110 `execution_job_submission/**/episode.py`, `binding_roles.py`, `*_job_execution/binding_record.py`,
`scientific_process/episode.py`, `saved_scientific_state.py`; a108 `scientific_process/episode.py`, cr1 files that came
in through a101's range) were not merged. One clean merge was reverted: a110 `component_assessment_dependencies.py`
(a104 removed a `deepcopy` import that a110 still uses — not a fingerprint change).

## a108
- Merged clean (taken): `application_execution_binding`, `composition_information`, `decision_history`, `numerical`,
  `ordinary_execution`, `vendor/SOURCE.nano-graphrag.json` (2 fields), `scientific_process/scientific_contracts`, and 19
  `library/retained_input_authority` readers (13a/13b/19 pins, FBA `source_function_sha256`, BV-BRC adapter schema +
  relation check, protein-disorder and fluorescence profile constants, RNA `COMPATIBILITY_FIELDS`).
- Resolved by hand: `runtime.py` (pending-work branch + estimator pin), `independent_execution.py`, `episode_composition.py`
  (field set and three digest clauses; the multi-version list there is not a fingerprint and is untouched),
  `flux_balance_request_binding.py`, `chromatin_interaction_contracts.py`, `scientific_process/{binding_record,
  invocation_state}.py` (a104 shape; code `scientific_closed_implementation_identity_invalid` gone).
- Scripted: 14 literature binding records + 14 `source_contracts.py` hubs (`m1.pl`), `acquisition.py` (`m2.pl`).
- Deleted roster modules: `receiving_context_sources.py`, `shared_infrastructure_sources.py`, `runtime_assets.py`.
- A105/A108 grading rules: no grader, subscoring sheet, `investigation_finding`, credit or iterator code edited.
- Suspects carried over: 17 directories save a decision, the same 17 add `pending_work`; journal/ledger tables created by
  `episode_journal.py:65`, `episode_completion.py:137,142`, ledger built at `runtime.py:1025`; `Workflow.__init__`
  refuses other boundaries (`runtime.py:987-988`).
- Inventory: 75 `h5` rows: 70 gone (4 by file deletion); 5 still match textually but carry nothing removed (kept
  `_TRACKING` name filter; truncated texts whose digest part is gone; `.py` path-name check of the NMF intent).

## a110
- Class 1: 30 binding records (14 literature, 4 hpc, 12 execution job/result: conflicts resolved by `resolve.pl`), 6
  progress records, 14 `contracts.py` + 12 `execution_contracts.py` hubs, `scientific_process/binding_record.py`,
  `private_reconstruction_protocol`, `private_scientific_literature_reconstruction` (15 rows), `private_execution_hpc_
  reconstruction` (36 catalog rows lose `fingerprinted`, check and docstring), `episode_composition`,
  `independent_execution`, `method_loop/durable`, `application_execution_binding`, `execution_progress`,
  `historical_execution_progress.as_record`, `ordinary_execution`; roster modules `information_sources.py`,
  `received_reader_sources.py` deleted with their consumers (`factory_readers`, `information_readers`,
  `received_configuration`: `ReceivedExecutionSetup` loses `source_record`/`implementation`).
- Class 2: acquisition observer/transport digests; BV-BRC adapter pin incl. the a110-only `adapter_source_identity.py/.json`
  table (14 adapter owners, 5 re-exports, `bind_adapters`, `api_bvbrc_appservice`, publication reader, 6 `*_returns.py`,
  2 schema JSONs, `historical_appservice_contracts` relation check); native BLAST database values/publications (recipe 7)
  and producer manifest on the reader contracts + terminal custody (recipe 12); HMMER preparation result publication and
  ATAC driver-runtime producer (13a; `_copy_exact` byte-compares an existing read-only copy); 13b/19 readers (ATAC `_DRIVER`,
  chromatin, RNA software incl. `_RECOGNIZED_SOFTWARE.worker_source_sha256`, NMF, fluorescence `PIN_SCHEMA`, genomic
  overlap, protein structure, terminal evidence); component HPC worker + `a110_fba_hpc` code manifest (recipe 18).
- Class 3: estimator pin; FBA `SOURCE_FUNCTION_SHA256` (contracts, 3 producers, result worker, readers, driver manifest);
  molecular deployment `SOURCE_SHA256`/`GLYCO_SOURCE_SHA256` + `original_source_pin_required`; fluorescence report
  `PROFILE_SOURCES` digests.
- FBA producer chain (a110 only): software files path-only, `flux_balance_worker_staging` without digests,
  `native_flux_balance_preparation` without `_verify_pins`/re-hash (scratch budget by `stat().st_size`),
  `flux_balance_model_execution` existence check.
- Class 4: `tests/test_bound_received_inputs.py` fixture path-only software, no `source_function_sha256`;
  `tests/test_composed_dependency_repairs.py` deployment module pin any digest, the `source` case deleted.
- Inventory: 233 `h5` rows: 208 gone (6 by file deletion); 25 still match textually and carry nothing removed (kept
  `run_statistics.implementation_sha256`; truncated texts; request digests; `Path(__file__)` used to locate files).
  `pa110_self_hashing.txt`: all 70 rows gone. `pa110_remaining_lines.tsv`/`_versions.tsv`: no fingerprint row
  (backward-vocabulary items of the pa110 task; nothing to do here).
- Suspects carried over: 54/54 directories; same producer evidence (`episode_journal.py:67`, `episode_completion.py:137,142`,
  `runtime.py:735`, `runtime.py:689`).

## Kept (both arms)
`ExecutionClass.implementation_sha256` (`run_statistics.py`, `ordinary_execution.py`, `execution_memory.py:219`);
`_TRACKING` name filters; `_MACS` MACS2 and LUMPY external pins, `rna_module_sha256`/`rna_extension_sha256`; molecular
deployment record file pins and `software_files` manifest (`molecular_sequence_execution_contracts.file_pin` etc.,
operator deployment, as a107/a105); data `FilePin`s (FBA model input), `native_flux_balance_storage.file_pin` for outputs;
`R10/a110_fba_hpc.py:138` Aurora 20 GiB feature request; `vendor/SOURCE.*.json` other fields; `_copy_exact` names.

## Gate (measured)
| | a108 | a110 |
|---|---|---|
| syntax | 962 files, 0 errors (`claude_fp8_001`) | 2,569 files, 0 errors (`claude_fp8_007`) |
| bound names, changed files | 0 undefined; unused imports only shrank (vs base, `_002`) | 0 undefined (`_007`); new unused only `Path` in 12 `execution_contracts.py` hubs (re-exported, as a107) |
| import check, all product modules | 921 modules `{}` (`_003`) | 2,450 modules `{}` (`_006`) |
| expected (written before launch) | 36 files, 529 = 526 passed + 3 failed, ~31 s | 95 files, 1,459 = 1,439 passed + 20 failed, ≤237 s |
| measured | 36 files, 529 = **526 passed, 3 failed**, 0 errors, 28 s (`_101.._136`, rerun `_137`) | 95 files, 1,458 = **1,438 passed, 20 failed**, 0 errors, 119 s (`_201.._295`, rerun `_301`) |

- a108: `tests/test_private_literature_decision_boundaries.py` failed 14 tests (`no such table: runtime_decision_effects`)
  after the `decision_history._tables` removal — an arm-owned fixture opened a `Journal` without the `CompletionLedger`
  every `Workflow` builds; fixed in the fixture (one line), file passes 62/62. Remaining 3 failures
  (`test_original_molecular_material_port.py`, `local_resource_binding_conflict`) identical to rec4.
- a110: 1 new failure from my change (the source-pin refusal case) — deleted as identity-mechanism test. The 20 failing
  ids are identical to rec4 (4 `test_launch_connected.py` ×2, literature reaction integration files 12).
- **0 tests that passed before fail now** in either arm. Awaiting top-level fixtures: none.
- Edited code no arm test names (approximation: module basename not mentioned in the arm's tests): a108 53 modules
  (24 besides binding records and hubs; mostly `library/retained_input_authority` readers, `independent_execution`, `invocation_state`); a110 110 modules (about 75 besides binding records and hubs) incl.
  the whole BV-BRC adapter family, BLAST database readers, FBA producer chain, `a110_fba_hpc`, component HPC worker,
  HMMER publication, ATAC runtime — covered only by syntax, name and import checks.

## Site counts (lines/files, `e8bf4820f` → now)
a108: `implementation_sha256` 41/25→6/4, `_binding_source_bytes` 42/28→0, `_AXIS_DIRECTORY` 56/28→0, `rglob('*.py')`
30/16→0, `SOURCE_.*SHA256` 12/7→0, `adapter_sha256` 4→0, `script_sha256` 3→0, `template_sha256` 2→0,
`source_function_sha256` 4/3→0, `python_sha256` 7/5→1/1 (`_MACS`). Table: `<scratchpad>/fp8/a108_counts.tsv`.
a110: `implementation_sha256` 174/89→5/3, `implementation_record` 16/5→0, `SOURCE_PATHS` 12/2→0, `_binding_source_bytes`
54/34→0, `_AXIS_DIRECTORY` 54/40→0, `fingerprinted` 57/4→1/1 (comment), `adapter_implementation_sha256` 18→0,
`producer_verification` 12→0, `package_files` 6→0, `code_manifest` 13/4→0, `worker_sha256` 7/4→0,
`source_function_sha256` 12/10→0, `SOURCE_.*SHA256` 20/9→0, `worker_source_sha256` 5/4→0, `python_sha256` 13/10→1/1,
`_verify_pins` 3→0, `file_pin` 55/13→31/9 (data/deployment), `source_pins` 39/8→32/7 (field names, rows `{path}`).
Table: `<scratchpad>/fp8/a110_counts.tsv`.

## Handoffs
- Applied: row 482 (shared helpers; no a108/a110 file failed on them). No other row addressed to fp-a108/fp-a110.
- Written: 1 row `fp8 → fp-top` (`tests/test_scientific_hpc_environment.py:54-55` still builds the component worker
  request with `code_manifest*`). Producers already covered: FBA (463, 468), BLAST database (431-432), ATAC/RNA/
  fluorescence/NMF/genomic overlap/HMMER (430, 447-450, 457-459, 467, 470, 472-474), BV-BRC adapter configuration (fp1).

## Notes
- One command used `timeout 30` around a perl edit script after a self-replacing substitution looped (stopped with
  TaskStop); no other limit was set. Recipe section 22 records both perl pitfalls met here (a literal `$1` from a
  variable replacement corrupted two schema lines in a110; repaired from HEAD and verified equal to the intended line).

## Left for decision
None.
