# Decisions needed from the owner

Collected from the test diagnosis of 14–15 November 2026. Each item names the report in this directory that
holds the evidence (file and line references, runs). Case counts are failing test cases at the time of
diagnosis; they overlap where one test meets several causes in turn. Nothing listed here was changed.

## A. Scientific behaviour (evidence accepted, graded, credited or reported)

| # | Question | Cases | Report |
|---|---|---|---|
| A1 | **Implementation digest pins.** A105-family storage modules pin sha256 digests of implementation files that the reorganisation rewrote. Of 54 files pinned from `a105/library`: 9 identical to the original, 38 differ only in imports and formatting, 7 have statement changes (3 controlled-response files change which saved records are accepted). Two pin tables were re-pinned to values that match no file. Re-pin, issue new receipt versions, or restore the original bytes? Same sites exist in a104 and a106. | about 640 | `r2d.md`, `r2d_pin_inventory.tsv`, `r2d_pinned_file_differences.tsv` |
| A2 | **Original task credit in scripted literature commissions.** A105/A106 scripted tests are rejected with `literature_original_task_credit_required` because their commission carries no `literature_task`. Which credit declaration should each carry, or are the tests stale? | 38–54 | `r2d.md` (C2), `r4b.md`, `r4d.md` (D05, D09) |
| A3 | **A106 feedback detail.** `a106/published_evidence_assessment/source_operations.py:114` does not forward the `detail` that storage builds. Forward it? | 5 | `triage_d.md` |
| A4 | **Fluorescence saved sheet as execution input.** The a104 test expects a granted saved sheet to be admitted; the validator refuses anything outside the assigned scope (unchanged since before the reorganisation) and an older test asserts the refusal. Which is intended? With the expectation corrected the file needs about 12.7 CPU-hours. | 60 | `triage_e.md` |
| A5 | **Retained plans with `policy.wall_seconds`.** Saved genomic-overlap, Infernal, minimap2, protein-structure and chromatin plans carry `wall_seconds` (often `null`); every current policy schema forbids the key, as it did before the reorganisation. Keep old plans readable, regenerate the fixtures, or retire those replay tests? | about 330 | `r2f.md`, `r2a.md` (7), `r2c.md` (C08), `r4a.md` (Q1) |
| A6 | **`retained_policy(x, historical=...)`.** The split ATAC and chromatin receipt modules call a function, and a `historical=` argument, that exist nowhere. Writing them decides which saved policies are accepted. | 14 modules, 9+ cases | `triage_f.md` |
| A7 | **Saved "prechange" sheets versus current graders** in a101 (saved-sheet and parser equality tests). Which is authoritative? | 45 | `r2c.md` (C11) |
| A8 | **Genome-alignment download cap.** The validator accepts only uncapped download calls while the host requires a cap, so every result is `partial`. | 5 | `r4b.md` |
| A9 | **A105 controlled-response storage** rejects the a106 fixture with `literature_reading_outside_assigned_source`; a legacy assessment replay is blocked by an early `experiment_ref` check; reported-curve grid sheets are refused on registration. | about 27 | `r2b.md` (K27), `r2d.md` (G1, RC) |
| A10 | **Refusal codes and small scientific expectations**: which refusal code is intended in three tests where an earlier check now answers first; whether the ion return-contract text should list `formula_code`; a106 unit enums gained two units so frozen legacy schemas are refused; a110 legacy record ids pinned before a role change. | about 15 | `r4d.md` (D04, D06, D07, D18), `r2e.md` |

## B. Product defects that are not import lines

| # | Defect | Cases | Report |
|---|---|---|---|
| B1 | **20 GiB native-job policy versus the 5 GiB launcher bound.** a101 product contracts and several retained plans hard-code 20 GiB; `workflow_budget.native_budget` rejects it and `prepare_job` reports `whole_workflow_budget_unavailable`. Root's protein launch policy says 5 GiB while a102 and other axis copies say 20 GiB. Which side is intended? | about 400 | `r2c.md` (C04), `r2a.md` (8), `r4d.md` (D23) |
| B2 | **Missing private copies.** a102 lacks four BLAST calculator modules (15 modules cannot import); a102 and a107 each lack nine HMMER modules. The a103/a104 copies are byte-identical to the originals. Copy them in? | 17 modules | `triage_f.md` |
| B3 | **a101, a105 and a108 have no private execution-service setup** (six other axes do), so tests hand root descriptors to the axis `Workflow`. | 121+ | `r2a.md` (5), `r4c.md` (R1) |
| B4 | **Shared-root `ExecutionEpisodes` / `ResourceEpisodes` are shells** (3 methods where there were 22) and fail root's own binding protocol; root `EpisodeReturnRecords` lost four methods its callers still use. Restore or retire with their tests? | about 290 | `r2e.md`, `r2f.md`, `r2a.md` |
| B5 | **Role-only `for_role` lookups** in `root/composition_information.py:110` and `root/decision_information.py:32` raise for roles bound at several homes; all nine axis copies use `for_child`. | about 120 | `r2f.md` (C07), `r4a.md` (P3) |
| B6 | **Two `BindingContext` classes and two `method_loop` packages** (top-level and root): `molecular_reference_privacy.py` denies every source the root Workflow received. 26 modules exist both top-level and in root. Which should code and tests use? | about 150 | `r4a.md` (P4), `r2a.md`, `r2f.md` |
| B7 | **Shared code importing modules that exist only per axis**: `api_uniprot`, `independent_execution`, `scientific_process_prompt`, `tools`; `root/library/native_infernal_result_publication.py` launches a worker that exists only in a107. | about 130 | `r2b.md` (K15), `r2a.md` |
| B8 | **Cross-axis capacity ledger.** `LocalResources` copies stamp ledger versions v1 (top-level, a105), v2 (a101–a104, a106, a108) and v3 (a107, a110) and refuse each other's ledger in one run directory. | 5 confirmed | `triage_d.md`, `r2e.md` |
| B9 | **Source-closure walk** cannot resolve imports in functions moved into `a101/library` and `annotation_improvement`. | 61 | `r2c.md` (C10) |
| B10 | **Enrichr** refuses `timeout` at fresh construction and also requires it, so no fresh service can be built. | 87 | `r2a.md` (3b) |
| B11 | **Handle checks** do not expect the two workflow environment keys that `native_lifecycle.prepare_job` now adds. | 70 | `r4a.md` (P1) |
| B12 | **Unfinished publisher-binding receipts**: tests expect `binding_registry` / receipt v2 that no product file implements. | 15 | `r2d.md` (PB) |
| B13 | **Smaller**: a102 registry lacks the `context_hook_applies` filter; `a102/episode_composition.py` has no `published_evidence_assessment` entries; a108 `task_instructions.py` calls a removed `is_job_source`; a104 lacks the GenomeComparison application identity; a103 `allocation_limits` no longer carries CPU; a107/a110 Launch accepts redelivery from another Launch's child and enforces the frozen request only at decision admission. | about 130 | `r4b.md`, `triage_d.md`, `r2e.md`, `triage_c.md`, `triage_a.md` |
| B14 | **27 path expressions in product code point at files that do not exist** (and 14 more resolve to `root/` where the repository root was meant). | — | `r2b_path_scan.md` |
| B15 | **Elapsed-time arguments in product code**: `a104/hpc_work_planning/resource_discovery.py:23` and `a104/hpc_queue.py:191,196` pass `timeout=` to ssh calls, which `AGENTS.md` forbids. | — | `triage_e.md` |
| B16 | **Repeated work in product code** makes two a104 saved-data test files take 5 and 2.3 CPU-hours (`validate_fluorescence_software` called 1,312 times on one closure; `communication.plain` 365 million recursive calls). Two one-line speed-ups are identified. | — | `triage_e.md` |

## C. Inputs that are not in the repository

| # | Need | Cases | Report |
|---|---|---|---|
| C1 | HMMER oracle tests need `HMMER_NATIVE_ORACLE_EASEL_DIR`, `_CC`, `_ALIMASK`; the untracked `resources/software/infernal-1.1.5` matches the pins but does not compile under gcc 15.2. | 435 | `r2c.md` (C01) |
| C2 | Files that survive only under untracked `verification/` or `validation/` (Infernal `selected-job.json` files are gone entirely; HMMER packet 273 survives as a 3.4 MB copy). Copy into tracked fixtures or retire the tests? | about 450 | `r2b.md` (K01, K11…), `r4c.md` (R2) |
| C3 | `GENE_DIRECT_TASK_PHASE` (the guard was added in the reorganisation; `connected` makes 276 of 280 pass), `HMMER529_ATTEMPT`, `A104_CONTEXT_SOURCE_EPOCH`, `GENE_OPERATIONAL_LEGACY_PREPARATION`, `NMF488_SOFTWARE`. Set them in the runner, or drop the guards? | about 340 plus 755 skips | `r2e.md`, `r2f.md`, `triage_e.md`, `triage_c.md` |
| C4 | Packages and tools: `scikit-learn`, `flowio`, ViennaRNA; a BLAST skill client read from the real home directory. | under 10 | `r4a.md`, `r4d.md` (D03) |

## D. Test intent

| # | Question | Cases | Report |
|---|---|---|---|
| D1 | How should a107/a110 tests compose the split literature tree under a root (`KeyError: 'literature_strategy'`)? | 23 | `r2e.md`, `r4d.md` (D10) |
| D2 | Tests that depend on helpers in parked test modules: park them too? | 108 | `r2b.md` (K07) |
| D3 | Tests of `ExecutionEpisodes.prepare_assignment` and similar methods that moved to per-role binding classes: rewrite against the binding classes or retire? | 79+ | `r2c.md` (C07) |
| D4 | The census exclusion of two function-only homes in the a107/a110 `test_private_reconstruction.py` files is right only if those homes never own bindings. | 2 | `r4b.md` |
| D5 | About 33 test files still build `'gene_annotation_episode.' + module` guard strings at pre-move paths. | — | `r3.md`, `r4b.md` |

## E. Placement (answers needed before any code is moved between files)

1. `credit.py` in 59 homes also holds lead schemas and validation (`lead_schema`, `validate_lead`, `lead_return_schema`). Do they belong in `to_parent.py` or `goal.py`?
2. Are `closed_credit.py`, `terminal_credit.py`, `native_credit.py` and `resource_state_credit.py` intended as separate files per credit kind, or should each home have one `credit.py`?
3. Should the credit methods in `episode.py` (66 homes) and `terminal_execution.py` (124 homes) move into `credit.py`?

## F. One event to know about

On 14 November one test (`tests/test_sequence_support_739.py`) made a live authenticated request to Addgene with the
credential stored in `~/.config/gene_annotation_episode/credentials.json`. The test is fixed and the runner now gives
every test process an empty home directory and blocks outside HTTP.
