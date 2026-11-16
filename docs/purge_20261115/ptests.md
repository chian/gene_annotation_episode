# ptests — repository-level `tests/` and `tests_parked/` (15 November 2026)

## Result
- `tests_parked/` deleted whole (387 tracked files incl. `PARKED.tsv`, 130,382 lines); `tests_parked` removed from
  `norecursedirs` in `pyproject.toml` (confirmed after the restart: directory absent, name absent from `pyproject.toml`).
- `tests/`: 598 test files / 21,024 collected tests before -> 518 test files / 16,183 collected tests now.
  Against a0d9f1666: 88 files deleted (76 by ptests, 12 by agent h3, logged in `h3_deleted_tests.tsv`), 296 files
  edited, 48,329 lines removed, 238 added. 862 individually deleted test functions + 76 whole files are listed in
  `ptests_deleted_tests.tsv` (file, test or (whole file), reason).
- Final collection check (launcher, isolated form, run `runs/claude_ptests_056`):
  `pytest --collect-only -q tests` -> `16183 tests collected in 25.33s`, 0 collection errors.

## What was removed, by reason code in `ptests_deleted_tests.tsv` (rows in tests/)
| code | meaning | rows |
|---|---|---|
| D1 | reads the untracked `verification/` or `validation/` trees or dated `tool_graders_*` run directories | 105 |
| D2 | needs the old `tests/bounded_execution/run_checks.py` runner (`HMMER529_ATTEMPT`, `BVBRC480_ATTEMPT`, `HMMER_NATIVE_ORACLE_*`) | 37 |
| D3 | file-hash pins of product files, implementation digests, AST/import inspection of product source, where-code-lives asserts | 15 |
| D4 | replays or compares saved program outputs (retained/saved/worked/expected packets, frozen source copies, saved stores) | 231 |
| D5 | legacy/historical/deprecated/migration forms, retired categorical scorer, removed job-slot gates | 163 |
| D6 / removed name | test calls a name that no longer exists in current code (`project_credit`, `gene_annotation_episode.tools`, removed helpers) | 85 |
| ptop | only product subject is a deleted leftover top-level module | 203 |
| h4/owner | directly exercises the implementation-digest pin mechanism | 59 |
| class 5/6 | 32 whole files skipped unless `HMMER529_ATTEMPT` exists; the old runner (3 files) | 35 |
| prootlib | removed array-with-headers decoding and old RequestedForm grammars | 4 |

By class of the brief: class 5 (tests) all of the above; class 6: `tests/bounded_execution/` (3 files, 824 lines) and
the helper modules `fluorescence_flowio_test_support.py`, `native_fluorescence_prepared_test_support.py`,
`tool_attribution_native_fixture.py`, `inspect_a106_parent_prompt.py`; class 4: `tests/fixtures/` (one saved baseline
JSON; the directory is gone); class 7: old-runner narration removed from 10 docstrings/comments; classes 1-2 inside kept
tests: optional evidence-writing blocks keyed on `*_ATTEMPT` removed from 9 files (3 write-only helpers and their calls
deleted), `legacy=` parameter removed from one page builder, removed upgrade functions dropped from one forbid-list.

## Tests of current behaviour changed to the current input form (not deleted)
- leftover top-level module imports re-pointed to `episodic_workflow/root/...` in 66 files (a test was deleted only when
  every product name it used directly came from deleted modules; otherwise the import was re-pointed);
  `alignment_site_fact_sources` re-pointed to `root/library/alignment_site_projection_requests`.
- manifest `schema_version` 1 -> 2 at 6 sites (test_export, test_state x2, test_molecular_sequence_input_bindings,
  test_state_query x2).
- 20 GiB literals -> the 5 GiB bound (`5 * 1024 ** 3` / `5368709120`) everywhere in `tests/`.
- model-supplied `quote` removed from anchor inputs in 16 files (kept only where a before/after run of those files did
  not get worse; reverted in 5 files where stored witnesses still need it).

## Kept, and why
- Tests that pin the sha256 of raw third-party INPUT data (PMC XML, HPA/NCBI/UniProt responses, native BLAST/RAxML/
  Mauve/VCF/HOMER outputs, the flux-balance `native_contract_probe`): the pin is on an input file, the expected values
  are stated in the test, nothing depends on a code state. If the owner wants these gone too, they are the remaining
  units with a literal 64-hex digest (about 30 files); `taint.py`/`prune.py` remove them in one pass.
- Helpers that only fill a required field with a digest computed at run time (`adapter.implementation_sha256()`,
  durable/detached fixtures): product code still defines these functions.
- `wall_seconds` negative tests (configuration refuses the key): they check current closed configuration.
- Domain uses of the words: codon-tree/phylogeny "historical" (pre-trim stage), Infernal `legacy_ascii`, SAMStat
  "legacy" report format, "retained"/"saved"/"original" within one run.
- Standalone scripts in `tests/` (inspect_*, report_*, run_semantic_retrieval_samples, provider probes,
  workflow_budget_probe): not tests, still import.

## Live despite its name
- `tests/test_bvbrc_fastqutils_samstat_legacy.py` — tests the current `root/library/bvbrc_fastqutils_samstat_legacy.py`
  reader (native SAMStat report format; imported at line 1 block of the test, module exists).
- `tests/test_bvbrc_genome_alignment_retained_records.py` — current `root/library/bvbrc_genome_alignment_retained_records.py`.
- `tests/test_bvbrc_annotation_bundle_adapter.py`, `test_bvbrc_annotation_native.py`,
  `test_bvbrc_genome_alignment_bundle_resolution.py`, `test_context_credit.py`,
  `test_scientific_hypervolume_runtime.py` — now contain no test, only builders imported by other test files
  (`test_bvbrc_application_returns.py`, `test_intervention_analysis.py`, `test_bvbrc_genome_alignment_bundle_contracts.py`,
  `test_investigation_progress.py`, `test_scientific_findings.py`, ...).

## Handoffs
Written (to `roothomes`): root/tests/fluorescence_prepared_workflow_support.py (imports the deleted old-runner helper);
root/tests/test_bvbrc_genome_alignment_host.py (built on the deleted verification-based `all_requests`);
root/tests/test_native_rna_structure_results_integration.py (`native=` packet branch removed from the shared builder).
Read: all 181 rows addressed to `ptests`/`tests(top-level)`. Applied: 128 deleted-module rows plus the 96-name
`ptop_work/deleted_modules.txt` (no test imports an absent product module any more), credit.py retired stubs, removed
acquisition helpers, `_LEGACY_DEFS`/`_CUTADAPT_DEFS`, array-with-headers decoding, saved-sheet upgrade functions,
job-slot/saved-limit forms, manifest v1, 20 GiB, protein_structure_operands_398. Static search finds no remaining use of
`unproven_replay`, `execution_status_v1`, `wait_inputs_*`, `*_dependency_mismatch`, `implementation_dependencies`,
`original_implementation`, `allow_legacy_quote`, `historical=`, `control_version=`.
Not applied: the pa106 row names `root/tests/monitor_task_behavior.py`, which is outside this area (roothomes).

## Not verified / residual
- Only collection was checked for the whole tree; tests were not run except the 21 quote-anchor files (173 failed /
  397 passed / 12 errors after the rewrite, 174 / 396 / 12 before; 121 of the failures are
  `local_resource_binding_conflict`, unrelated to this work).
- Rows that cannot be found statically were not acted on: Rfam envelopes without `transport["request"]`, BV-BRC
  download cases without `max_bytes` (no test names such a case), remaining anchors that still fail with quote removed.
- Three tests reference attributes that current modules do not define and were left as failing tests of current code:
  test_bvbrc_data_recovery (2, `api_service_execution._immutable`), test_runtime_history (1, `runtime.WorkflowError`).
- Three over-pruned RNA-structure files were restored from HEAD content and re-pruned precisely (only the two
  packet-dependent tests went).
- Tools used are in the session scratchpad (`ptests/scan.py`, `taint.py`, `prune.py`, `ptop_apply.py`,
  `missing_names.py`, `orphans.py`, `dequote.py`); run directories `runs/claude_ptests_001..056`.
