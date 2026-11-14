# r2c: a101/tests failures (runs `..._03_a101a`, `..._03_a101b`)

Scope: every `groups.tsv` row with `directory_list == a101`, minus the messages owned by r2a and r2b.
That is 554 rows, 1,751 failing cases, 198 distinct messages, 82 test modules.
Per-message causes: `r2c_causes.tsv` (198 rows, sums to 1,751).

Result of the test-side fixes: in the 96 files rerun or carried over, failing cases went from 1,820
(all agents' messages in those files) to 1,114; 36 of 85 failing files now pass completely; no test that
passed before fails now (checked per test name against `groups.tsv`). `test_native_blast_database_contracts.py`,
which produced no report, now reports 84 passed.

Paths below are relative to `gene_annotation_episode/episodic_workflow/root/` (`A` = `a101`, `T` = `a101/tests`).

## Causes

| # | Cause | Class | Cases before -> still failing | Evidence | Action | Scientific? |
|---|---|---|---|---|---|---|
| C01 | HMMER native-oracle inputs not staged. Fixtures require `HMMER_NATIVE_ORACLE_EASEL_DIR`, `HMMER_NATIVE_ORACLE_CC`, and (weight oracle) `HMMER_NATIVE_ORACLE_ALIMASK` | environment | 435 -> 435 (`test_hmmer_alignment_input_native_oracle` 201, `..._block_phylip_native` 177, `..._native_weight_oracle` 57) | `T/test_hmmer_alignment_input_native_oracle.py:53-59,99-101`; `T/test_hmmer_alignment_native_weight_oracle.py:49,98-100`; `environment` block of both `SOURCE_PINS.json` | Left failing, nothing faked. See "HMMER oracle" below | No |
| C02 | Synthetic producer-manifest fixture kept the pre-reorganisation `package_files` paths while its `entry_module` was already the a101 one; the validator requires the a101 roster (`A/library/native_blast_standard_database_contracts.py:641`, `native_blast_database_contracts.py:628`) | test_wiring | 233 -> 0 | Fixture at `T/test_native_blast_standard_database_metadata.py:98-104`, shared by 6 other modules through `fixture()`; sibling `test_current_private_producer_manifest_remains_valid_and_defensive` already builds the same roster and passed | Fixed (fixture paths) | No |
| C03 | Commit 22c1bab66 (automated re-pointing) rewrote the *original* `entry_module` literals inside the retained-manifest fixtures, so they no longer select the retained profile | test_wiring | 4 -> 0 | `git show 22c1bab66 -- T/retained_blast_manifest_fixtures T/test_private_retained_blast_manifest_identity.py` (3 literal lines; the only data literals that commit changed in `T`) | Fixed (restored to 3dd58552a text) | No |
| C04 | Local native job needs a 20 GiB `LocalJobPolicy`; the launcher budget is 5 GiB. The budget file IS found and authenticated; `workflow_budget.native_budget` then raises `native_request_exceeds_environment_bounds` (`gene_annotation_episode/workflow_budget.py:35,120-121`) and `prepare_job` reports every `ValueError` as `whole_workflow_budget_unavailable` (`A/native_lifecycle.py:113-118`) | environment | 189 -> 189, plus 165 cases that reach it once C05 is fixed (354 in total) | All 189 chained errors are `native_request_exceeds_environment_bounds` (tallied from junit). 20 GiB is fixed in product code, not only in tests: `A/native_blast_database_results.py:223,246`, `A/native_blast_standard_database_results.py:187`, `A/native_blast_database_result_publication.py:200`, `A/native_blast_standard_database_result_publication.py:185`, `A/library/native_blast_utility_contracts.py:571`. Same bound and check at 078b77668. Worker receipts of the rerun: 79 with that reason | Left failing; OWNER QUESTION 1 | No (resource policy) |
| C05 | Tests import top-level module copies (`domain.ContractError`, `local_jobs.LocalJobPolicy`, `acquisition.AcquisitionError/SourceSnapshot`, `state.Store`, `api_blast.NCBIBlastService`, `materials`, `practical_yield`, `form_reference_validation`, ...) while a101 code uses its private copies, so `isinstance`, `pytest.raises` and `except` never match | test_wiring | 530 -> 165 (all 165 now stop at C04) | e.g. `A/native_blast_result_publication.py:19,119-120` vs old `T/test_blast_pairwise_publication.py:20`; `A/homology_jobs.py:28,106`; top-level `api_blast.py:165` catching the top-level `AcquisitionError` while a101's is raised (`A/acquisition.py:315`) | Fixed: 109 import lines in 53 files re-pointed to the a101 copy (only where every imported name exists there) | No |
| C06 | Retained bundles (original producer identity) were validated with the live validator, whose schema now pins the a101 entry module; product readers all use `validate_retained_*_bundle` | test_wiring | 73 -> 0 | `T/test_native_blast_database_sidecar_metadata.py:73-77`; `A/library/native_blast_database_contracts.py:1085-1095,1105-1108`; product callers e.g. `A/native_blast_database_acquisition.py:186` | Fixed (test helper calls the retained validators) | No |
| C07 | Tests call `prepare_assignment`, `assignment_schema`, `fact_sources`, `facts`, `initialize`, `project_credit`, `entry_roles` on `ExecutionEpisodes`. At 078b77668 these were methods of that class; since dfe3e6091 they are on per-role classes (`execution_job_submission/*/from_parent.py`, `.../episode.py`) built by `execution_binding_catalogue.execution_bindings(owner)` | stale_test | 79 -> 79 (`test_native_hmmer_local_binding` 31, `test_blast_utility_episode_wiring_632` 24, `test_blast_vdb_episode_consumers_671` 23, `test_bvbrc_homology_tool_info` 1) | `execution_episodes.py:29`; `execution_binding_catalogue.py:9-52`; `git show 078b77668:gene_annotation_episode/execution_episodes.py` lines 758, 1468, 1734, 3556, 3888, 4639 | Left failing. Test-side repair: obtain the role binding (`LocalExecutionBinding(owner)` etc.) instead of calling the owner | No |
| C08 | Retained plans and bundles carry `policy.wall_seconds: null`; the product accepts exactly `{memory_bytes, scratch_bytes}` | stale_test | 41 -> 41 (`test_native_blast_retained` 20, `test_native_hmmer_driver_retained` 13, `618` 4, `test_hmmer_alignment_input_integration` 3, `630` 1) | `A/native_blast_driver.py:74-76`, `A/native_hmmer_driver.py:76`, `A/native_hmmer_preparation_acquisition.py:106-108`, `A/library/native_blast_masking_contracts.py:269-271`; all 20 `T/fixtures/blast_pairwise/*/plan.json` have the key and are byte-identical to 078b77668, where the driver check was the same, so these failed before the reorganisation too. Only `native_blast_utility_contracts.py:571` admits the old form | Left failing; OWNER QUESTION 2 | No |
| C09 | Needs `HMMER529_ATTEMPT`: an attempt directory with `selected_request.json`, created by `tests/bounded_execution/run_checks.py` (its "bounded529" 20 GiB runner, lines 188, 446, 463-473) | environment | 27 -> 27 (`test_vdb_validation_reuse_676` 20, `test_native_blast_masking_invocation` 4, `675` 2, `678` 1) | `T/test_vdb_validation_reuse_676.py:89`, `T/test_result_validation_cost_675.py:71` (also requires the attempt name to start with `check133`), `T/test_native_blast_masking_invocation.py:380` | Left failing, not faked. Nothing in the leaf-up runner provides it; the runner that does needs 20 GiB (C04) | No |
| C10 | `native_driver_runtime._source_closure` resolves relative imports from the file's own package. Functions moved into `A/library/source_return_admission.py`, `source_report_records.py`, `decision_source_admission.py` and `A/annotation_improvement/{from_parent,task,task_provider,to_child_annotation_improvement}.py` keep imports relative to `a101.runtime` (they are re-bound into that namespace by `A/library/live_runtime_functions.py`), so the closure finds 15 modules "missing" and raises `native_dependency_unavailable` | product_defect | 58 -> 58 (`test_native_hmmer_preparation_result_publication`: 27 setup errors, 31 `graded` false) | `A/native_driver_runtime.py:203-214`; `A/native_hmmer_preparation_result_publication.py:266-267`; e.g. `A/library/source_return_admission.py:10,23,28`. The 31 saved `prepared.json` of the rerun all carry `native_dependency_unavailable` | Left failing. Not an import-line fix under rule 1: `..x` would break the runtime binding. Options: absolute imports in those 7 modules (18 lines; they are hashed in `ownership_inventory.json`), or teach the closure about bound modules | No |
| C11 | Equality against a saved sheet, or between two parsers | stale_test | 45 -> 45 (`test_blast_vdb_function_census_relations` 25, `test_blast_explicit_associations` 9, `test_native_blast_vdb_function_metadata` 5, `test_blast_archive_member_digest` 3, `test_blast_database_context` 1, `test_blast_report_collection` 1, `test_native_blast_standard_database_metadata` 1) | `A/library/{blast_database_grader,blast_report_collection,blast_grading_inputs,blast_vdb_function_inputs}.py` equal 078b77668 apart from import lines (diff = 0 non-import lines); `fixtures/blast_explicit_associations/legacy_prechange.json` has the same sha256 as at 078b77668. Full diffs: current sheet has extra blocks (`endpoint_spans`, coverage) the snapshot lacks; one parser emits `hsp_source_map`, the other does not | Left failing; OWNER QUESTION 3 | Yes (graded sheet content) |
| C12 | `forbid_io` patch stayed active while pytest built the failure report, crashing pytest (file with no report) | test_wiring | 0 counted (84 tests hidden) | `forbid_io` helper and `test_producer_manifest_is_pure_defensive_and_closed` in `T/test_native_blast_database_contracts.py` | Fixed, see "forbid_io" below | No |
| C13 | Adapter implementation pin computed from the a101 library copy, but root `ExecutionEpisodes` installs the `root/library` copy; behind it the same stale interface as C07 | test_wiring | 10 -> 10 | `T/test_bvbrc_homology_tool_info.py:7,20-24`; `gene_annotation_episode/bvbrc_appservice_adapters.py:20-41` | Left failing (would still stop at C07) | No |
| C14 | Test patches `populate_hmmer_alignment_preparation_sheet`; the driver preflight calls `read_hmmer_alignment_input`, and already did at 078b77668 | stale_test | 4 -> 4 | `A/native_hmmer_preparation_driver.py:268,335`; `git show 078b77668:gene_annotation_episode/native_hmmer_preparation_driver.py` lines 273-291 | Left failing | No |
| C15 | sha256 pin of `ast.dump()` text of a saved copy of old source. File bytes match their pins, the dump hash does not: the text depends on the interpreter (venv is Python 3.12, system is 3.14) | stale_test | 2 -> 0 | `T/test_homology_prepare_source_identity.py` (old lines 38-49) | Retired the two `[pre_native]` cases; `[installed]` cases kept and pass | No |
| C16 | Stale module-path literal `gene_annotation_episode.alignment_correspondence`; the a101 workers pin `a101.library.alignment_correspondence` (`A/native_blast_standard_database_result_worker.py:103-107`) | test_wiring | 1 -> 0 (plus 1 hidden case in the standard worker file) | `T/test_native_blast_database_result_worker.py:217`, `T/test_native_blast_standard_database_result_worker.py:110` | Fixed (literal) | No |
| C17 | Required phrases (`GSC/BLOSUM`, `unsupported`) are not in the tool-info text; `GSC/BLOSUM` was not in it at 078b77668 either | stale_test | 2 -> 2 | `T/test_native_hmmer_preparation_tool_info.py:267,291`; `git grep -c "GSC/BLOSUM" 078b77668 -- gene_annotation_episode/*.py` = 0 | Left failing | No |
| C18 | Monitor homes only: presenter text and `decision_prompt_renderer` text differ in JSON key order | unclear | 4 -> 4 | `T/test_root_delivery.py:26,65`; fails for `execution_progress_assessment` and `scientific_process/execution_progress_assessment`, other homes pass | Left failing; which side should sort keys not established | No |
| C19 | Recorded `extractor.module` is `...a101.blast_native_iteration_records`, a module that does not exist (it is `a101.library...`); the convergence schema pins the same string | product_defect | 1 -> 1 | `A/library/blast_native_iteration_records.py:450`; `A/library/native_blast_database_convergence.py:88` | Left failing (file is being edited by another agent); OWNER QUESTION 4 | Yes (recorded provenance) |
| C20 | `test_blast_binding`: mixed copies (4 cases now pass). Remaining: `run_workflow` called without explicit root task credit (2; `A/default_scientific_binding.py:20-21`), `cli.main(['capabilities', ...])` returns 1 (2; not traced) | test_wiring / unclear | 8 -> 4 | `T/test_blast_binding.py:11-16,53,442` | Partly fixed. Not rerun after the outside-service rule (see below) | Credit part yes |
| C21 | `PROJECTION_FIELDS` lacks `paths`, `vdb_context`, `path_sections` that `FACT_SOURCES` has, inside one module identical to 078b77668; one historical-schema case does not raise | unclear | 2 -> 2 | `A/library/blast_utility_result_views.py:153-158,408`; `T/test_blast_utility_result_views_629.py:87`; `T/test_blast_utility_historical_forms_652.py:142` | Left failing | Possibly |
| C22 | Frozen tool information appends the execution-guidance recipe to `instructions`; test expects the raw text. Recipe text exists at 078b77668 | stale_test | 2 -> 2 | `T/test_native_blast_standard_database_tool_info.py:46-51`, `T/test_native_blast_database_tool_info.py:46`; `A/execution_guidance.py` | Left failing | No |
| - | `test_hmmer_alignment_map_context::test_driver_after_last_match_is_rejected...` (`assert False`) | unclear | 1 -> 1 | not examined | Left failing | - |

Visible only after C05 was fixed, not in the original counts: `test_hmmer_alignment_map_context::test_direct_saved_projection_rejects_illegally_placed_context[alimask-native_rows]`
(regex of the expected message does not match; not traced), and in `test_hmmer_model_binary2_views` three
`monkeypatch.setattr("...a101.hmmer_model_data...")` string targets that named a module location gone since dfe3e6091
(fixed to `a101.library.hmmer_model_data` / `a101.library.hmmer_model_calculations`; file now 18 passed).

## HMMER oracle (C01): what is needed, what exists
- `HMMER_NATIVE_ORACLE_EASEL_DIR`: absolute path of the Easel 0.49 tree of infernal-1.1.5, built (`libeasel.a`), every file pinned by sha256 in `SOURCE_PINS.json`.
  Nothing tracked in git provides it. The untracked, git-ignored `resources/software/infernal-1.1.5/easel` exists on this machine and
  its `libeasel.a` and `esl_vectorops.h` match the pins.
- `HMMER_NATIVE_ORACLE_ALIMASK`: `resources/software/infernal-1.1.5/hmmer/src/alimask` exists (same untracked tree).
- `HMMER_NATIVE_ORACLE_CC`: described only as "root-selected pinned compiler"; no path or hash is recorded anywhere.
- Verified by running the three files with those variables set to the local tree and `/usr/bin/gcc` (runs 128-130), still failing:
  the input oracle and the block/PHYLIP file stop at `compile_esl_alphabet` (gcc 15.2 rejects the implicit `isascii` under `-std=c99`,
  so an older compiler is required); the weight oracle stops because `SOURCE_PINS.json` "harnesses" still name
  `gene_annotation_episode/episodes/root/a101/tests/fixtures/...`, a directory that no longer exists (the files are under `episodic_workflow/`).
  That second point is a stale path in a fixture; I did not change it because it cannot be verified without a working compiler.
- The intended supplier was `tests/bounded_execution/run_checks.py --test-env HMMER_NATIVE_ORACLE_*=...` (lines 448-450).

## forbid_io
(a) Scoped the patch with `with monkeypatch.context() as patch:` around the calls under test at every unscoped site: `test_native_blast_database_contracts.py`
(2 sites), `test_native_blast_standard_database_contracts.py` (3), `test_native_blast_standard_database_driver.py` (2),
`test_native_blast_vdb_function_metadata.py` (2), `test_native_blast_standard_database_tool_info.py`, `test_blast_database_preparation_627.py`,
`test_prepared_blast_manifest_646.py`, `retained_blast_manifest_fixtures/database.py`, and the equivalent inline patch in `test_hmmer_fm_calculations.py`.
The other call sites (`test_native_blast_database_driver.py`, `test_native_blast_database_tool_info.py`, the two `test_private_retained_*` files)
were already scoped.
(b) The validator does no I/O, now or at 078b77668 (no `resolve`, `stat`, `open`, `listdir`, subprocess or socket call in either version; the only
change is the parameterised roster and entry-module constant). What happened: the fixture `manifest_for()` had the C02 stale roster, the validator
raised `ValueError(...producer_required_package_file_missing)`, and pytest's own report code then hit the still-active patch. So it is a stale
fixture, not a product regression and not a stale purity expectation. With the fixture corrected the test passes under `forbid_io` (run 039: 84 passed).

## Reaches outside services
- `T/test_blast_binding.py`: builds real `PublicClients` and calls `tools.execute('public.blast.search' / 'public.blast.collect', ...)` and
  `client.blast('submit' / 'status', ...)` (lines 134-480). Only monkeypatching of `subprocess.run` and `requests.Session.request` inside the test
  keeps it off the NCBI service, and `PublicClients._skill` reads the installed skill script from the real home (`A/acquisition.py:80`,
  `~/.codex/plugins/cache/...`). I ran this file twice (runs 011, 077) before the rule arrived, with the real home and no proxy block. In run 011 the
  HTTP test failed inside its stub before any request; in run 077 it passed against the stubbed entities. I saw no sign of a real request but did
  not capture network activity. It has not been run since and my runner now refuses it.
- No other file in the cluster executes a public provider tool; `test_bvbrc_homology_tool_info.py` patches the socket layer to raise.

## Runs
- 135 launcher runs, slot `r2c`, `runs/claude_r2_r2c_001` .. `_135`, one test file (or one test) each.
- Batch 1 (9 files): expected about 50 s, actual 55 s.
- Batch 2 (79 files): expected 20-40 min. Stopped by me after 18 files because I was about to change the imports those files use; its results
  were superseded by batch 3, except `test_blast_native_iteration_records.py` (281 s against 41.7 s measured; machine load average was 35-40).
- Batch 3 (92 files): expected 20 min to 2 h under that load, actual about 22 min for 88 files. I stopped the loop when the coordinator's isolation
  rule arrived; the last 5 files and batch 4 ran under it (about 7 min).
- Isolation deviation: the launcher refuses a run directory that already exists, so the empty home cannot be created inside it beforehand. I used
  `runs/claude_r2_r2c_homes/<NNN>/home` instead, with the proxy variables exactly as given. Runs 001-114 predate the rule (real home, no proxy block).
  No file was run unchanged both before and after the rule, so there is no direct comparison; nothing in the post-rule results points to the empty home or the proxy block.
- Previously passing files that use touched helpers, rerun and still passing: `test_native_blast_database_driver` (59), `test_native_blast_standard_database_driver` (56),
  `test_native_blast_standard_database_contracts` (137), `test_blast_vdb_tool_info_670` (48), `test_blast_preparation_tool_info_651` (105),
  `test_native_blast_database_metadata` (79), `test_prepared_blast_manifest_646` (17), `test_hmmer_fm_calculations` (30), `test_private_live_parser_locations` (6).

## Edits
68 files under `a101/tests/`, +286 -283, no product file. Two cases retired (`retired.tsv`, prefix `r2c:`).
Files in `a101/tests/` modified by other agents were not touched.

## Owner questions
1. C04: the a101 native BLAST/HMMER contracts and the bounded529 runner assume a 20 GiB local job; the launcher and `workflow_budget` allow 5 GiB.
   354 cases cannot pass under `tools/one_workflow.sh` until one side changes. Which is intended?
2. C08: should retained plans with `policy.wall_seconds: null` remain readable (one contract already admits them), or are those 41 retained-replay cases to be retired?
3. C11: the saved "prechange" sheets and the current graders disagree and did so before the reorganisation. Are the snapshots or the graders authoritative?
4. C19: which module path should a recorded extractor identity carry now that the module lives under `a101/library/`?

## Pin sites met
No A105-family `*_dependency_mismatch` pin in this cluster. Other source-identity pins met: `ownership_inventory.json` files hash `A/library/*.py`
(relevant to C10); the appservice adapter `implementation_sha256` configuration pin (C13); the retired AST-dump pin (C15).

## Verified by running vs inferred
- Run: every "now pass" figure; C04 reason (junit chain and 79 worker receipts); C10 outcome (31 saved records, `-l` run 127); C01 with variables set;
  the forbid_io fix; C11/C22 full diffs (runs 131-134).
- Read only: C07, C13, C14, C17, C19 (code and `git show`); the C10 list of 15 unresolved modules comes from a shell re-implementation of the closure walk,
  not from the product function; "failed before the reorganisation" for C08, C11, C14, C17, C21, C22 is inferred from identical code and fixtures at
  078b77668, since that revision cannot be run here.
- Not established: C18, C21, the two `cli capabilities` cases, the two `test_hmmer_alignment_map_context` leftovers, and whether C15's pin was made
  under Python 3.14 (inferred from matching file hashes and a differing dump hash).
