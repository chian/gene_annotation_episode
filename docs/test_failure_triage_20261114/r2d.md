# r2d: a105/tests failures (run `claude_tests_leaf_up_20261114_03_a105`)

Paths: `R/` = `gene_annotation_episode/episodic_workflow/root/`, `T/` = `R/a105/tests/`, `lib/` = `R/a105/library/`,
`PEA/` = `R/a105/published_evidence_assessment/`, `SEE/` =
`R/a105/scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/`.
"Original" = `078b77668`; the files discussed are byte-identical at `fb1e4d9ba`.

Marks: **[run]** reproduced through the launcher in slot `r2d`; **[read]** from code, tracebacks and git history;
**[inferred]** concluded from reading, not exercised. "Diagnostic run" means a launcher run with a throw-away pytest plugin
kept under `runs/claude_r2_r2d_scripts/` that only prints (or, for one plugin, makes one existing method reachable for the
duration of a test); no repository file is involved and none of it is a fix.

Scope: 809 failing cases, 59 distinct messages, 397 groups in a105. 14 messages (114 cases) belong to agents r2b and r2a and
are not diagnosed here. This report covers the other **45 messages, 695 cases**. Counts are a105 only: the groups.tsv rows
shared with a106 (`test_literature_optical_storage`, 76 cases) are counted as 38.

## 1. Causes

| # | Cause | Class | Cases | Evidence | Action | Scientific? |
|---|---|---|---|---|---|---|
| P1 | Implementation-digest pins do not match the rewritten files | product_defect | 555 = 473 with a `*_dependency_mismatch` message + 82 behind another message | Section 2. The 82: 66 of the 76 `{'status': 'invalid', ...}` cases (codes read in runs 009-014: endpoint 25, summary precision 29, kinetic 1, concentration window 10, ion 1), 6 of the 9 `'invalid' == 'invalid'` cases (the pin code replaces the expected code), 4 `'NoneType' object is not subscriptable`, 2 `'invalid' == 'completed'`, 2 `Regex pattern did not match`, 1 `summary_prec...`, 1 raised from the `SEE` copy. [run] for the first 78 (outcome codes printed in runs 009-014 and 119-159); the last 4 show the pin code in their junit message [read] | Not changed. Inventory in section 2 | Yes, owner question |
| W1 | Tests bind one literature home; a105 has seven | test_wiring | 54 (`KeyError: 'literature_strategy'`, 33 tests in 32 files) | `R/a105/runtime.py:1158` needs every declared child role; `PEA/episode.py:90` `create_binding_tree` builds the seven; three sibling tests already use `T/runtime_fixtures.py:61` `literature_binding_factories`. | **Fixed** in 41 files (all 49 single-home sites in `T/`). The tests then reach C1 | No |
| C1 | `_scientific_credit_invocation` is defined on the wrong class | product_defect | 3 directly (`assert 0 == 1`, `assert (0 == 1)`, `assert (1 == 4)`) and now the first failure of all 54 W1 cases | `PEA/credit.py:283` `LiteratureCredit.credit_view` calls `self._scientific_credit_invocation`; the method is at `PEA/credit.py:144` inside the dataclass `LiteratureTaskCredit`, which `LiteratureEpisode` does not inherit. Same in 13 a105 literature `credit.py` files plus `SEE/credit.py` (`SourceCredit`), and in all 14 a108 ones; the 14 a106 files define it on `LiteratureCredit`. The root episode saves only `exception_type: AttributeError`; the traceback was printed in runs 016-018 [run]. With the method made reachable in a diagnostic run, `test_literature_assay_integration` (11 passed) and `test_literature_a105_aggregation_binding_325` (1 passed) pass (runs 019, 021) [run]. | Not changed (product code, credit path). Repair: move the method to `LiteratureCredit` / `SourceCredit` in the 14 a105 files (and a108) | Yes: credit path. No logic change intended, but owner question |
| C2 | Behind C1: the scripted tests do not supply the original task credit | stale_test | 0 visible; it is what the 54 W1 cases reach after C1 | See section 3.1 | Not changed | Yes: credit rule |
| W2 | Repository accessors moved from `WorkflowServices` to the episode | test_wiring | 18 (17 `'WorkflowServices' object has no attribute 'literature_*_repository'` + 1 `monkeypatch.setattr(binding.services, ...)`) | Original `gene_annotation_episode/episode_services.py:254-433` had them; now `PEA/scientific_records.py:8-135`. `T/test_literature_assay_integration.py:99` already calls `binding.literature_assay_repository()`. | **Fixed** in 9 files. 14 of the 18 now pass; the other 4 (two tests of `test_literature_missing_input_semantics_156`, each for two kinds) reach the failures in 3.2 | No |
| W3 | Fake workflow lacks `is_job_source` | test_wiring | 15 | `PEA/task_instructions.py:5` (every home's composer) calls `source.workflow.is_job_source(source)`; the branch body is `pass` in all 15 homes. `T/test_private_instruction_service_dispatch.py:83` builds the workflow as a `SimpleNamespace`. | **Fixed** (`is_job_source=lambda value: False`); 47 passed | No |
| PB | Publisher-binding receipts expected by tests, absent from product | product_defect | 15 (14 `no attribute 'binding_registry'`, 1 `assert None == {...}`) | `T/test_private_publisher_receipts.py:30,71-75` expects `repository.binding_registry`, receipt version `concentration_window_original_implementation_v2` and a `publisher_binding`. No product file contains `binding_registry`; `lib/literature_publisher_binding.py` exists but nothing imports it. Receipts still select `binding_id == 'literature'` (`lib/literature_concentration_window_storage.py:296`, `lib/literature_measurement_comparison_storage.py:300`) while the homes now record path ids (`PEA/binding_record.py:86` `'published_evidence_assessment'`), so `bound_descriptor` is always `None`. [read] | Not changed | Yes: receipt saved with A105 records |
| RC | Reported-curve grid sheet cannot be registered | unclear | 10 (in the `{'status': 'invalid', ...}` group, `test_literature_reported_curve_binding_231`) | Code `literature_rate_observation_sheet_required` [run 012, 117]. `LiteratureRateObservationRepository.populate` delegates a grid request to the reported-curve repository (`lib/literature_rate_observation_storage.py:104`), which saves the sheet; the outer publication wrapper then calls `_register` with the outer repository, whose `read` refuses a grid sheet (`lib/literature_sheet_updates.py:268,98`, `lib/literature_rate_observation_storage.py:155`). `_register`, the wrapper and `read` have the same syntax tree as the original apart from the A105 policy lookup, and the test helper is unchanged, so this may predate the reorganisation. Not established. | Not changed | Sheet registration for A105; owner question |
| W4 | `literature_page` context sent to the top home | test_wiring | 6 (3 `'representation_error' == 'literature_r...signed_source'`, 3 of the `'invalid' == 'invalid'` cases) | The top home serves only role `literature` (`PEA/episode.py:52`) and validates the assignment as a literature assignment (`PEA/source_operations.py:9`); the page role is owned by `PEA/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py:60`. | **Fixed** with a new test helper `T/runtime_fixtures.py` `literature_binding_for_role` at the 6 call sites. 5 pass; the reported-curve one then stops at RC | No |
| I1 | Import of `REPORTED_CURVE_SCOPE_TASK` dropped | product_defect | 4 (`NameError`) | `lib/literature_task_selection.py:188` uses the name; the original imported it (`gene_annotation_episode/literature_task_selection.py:47` at `078b77668`). Same gap in `SEE/prompts/literature_task_selection.py` and in `R/a104/literature_task_selection.py`. | **Fixed** in both a105 copies (one import line each, the permitted product exception). a104 not touched | No (restores the original prompt text) |
| S1 | Operation schemas compared with retained JSON fixtures | stale_test | 5 | Visible difference: `'maxLength': 256` on reference strings, which `domain.REF` already had at `078b77668` (`gene_annotation_episode/domain.py:64`). Fixtures `SELECTION_SCHEMA_007.json`, `EXACT_SCHEMAS_002.json`, `OPERATION_UNION_SCHEMA_002.json` and two more. [inferred from the truncated assertion diff; the full diff was not printed] | Left failing | No |
| W5 | Wrong `DurableExecutionError` class | test_wiring | 2 | `T/test_private_binding_restoration.py:46,75` took the class from `a105.method_loop.durable`; `R/a105/episode_composition.py:16` raises the shared-root `method_loop.durable` class. | **Fixed**; 5 passed | No |
| G1 | Legacy saved assessment cannot be replayed | product_defect | 1 (`assay_grading_experiment_reference_required`) | `lib/literature_assay_grading_storage.py:101` requires `experiment_ref` before the saved-operation lookup at `:109`; the second check at `:118` shows the replay was meant to be reachable. The original has the same two checks in the same order (`literature_assay_grading_storage.py:133,155`) and the same test, so this predates the reorganisation. [inferred] | Not changed | Yes: A105 grading identity (AGENTS.md) |
| V1 | `_validate_graph` gained a required keyword | stale_test | 1 (`TypeError`) | `lib/literature_controlled_response_v2_inputs.py` `_validate_graph(..., implementation_fingerprints)`; product callers pass `extraction['implementation_dependencies']['expected_module_fingerprints']`. | **Fixed** in `T/test_literature_controlled_response_v3_stages.py:319` (same argument as the product callers); 41 passed. The product change is listed in 2.3 | Test: no. The product change: yes |
| M1 | Delivery to a literature-role receiver through the wrong entry point | test_wiring | 1 (`assert [] == [...]`) | `PEA/to_parent.py:325` `received_form_references` returns `[]` for literature roles (line added in the reorganisation; the original `literature_episodes.py:2580` had no such guard); a literature home now receives a child's rows through `receive_child_result` (`PEA/episode.py:80`). | **Fixed** in `T/test_literature_measurement_comparison_binding_268.py` (`binding.receive_child_result(parent, 'literature_strategy', ...)`); passes [run 114]. | Routing of delivered rows changed in the product; owner should confirm it is intended |
| S2 | `len(FAMILIES) == 9` | stale_test | 1 | `T/test_literature_concentration_window_binding_281.py:151`; `lib/literature_a105_worksheet.py:21` has 17 and the original module already had more than nine. | Left failing | No |
| S3 | Steering must not contain `artifact_` | stale_test | 1 | `T/test_literature_rate_observations_166.py:283`; the fixed preamble contains `artifact_ref` (round one, C4). | Left failing | No |
| S4 | `literature_perturbation_cells` expected in a105 | stale_test | 1 | `T/test_literature_numerical_declarations_203.py:54`; no a105 product file registers that source type (perturbation left a105). | Left failing | No |
| S5 | Task text expected absent | stale_test | 1 | `T/test_literature_product_partition_integration.py:80` removes only the legacy work flag; the assignment still requests product-partition components, and selection follows requested work (`lib/literature_task_selection.py` docstring, same in the original). | Left failing | No (prompt text) |
| S6 | `ACTIVE_SITE_TASK` expected in a reference parent's TASK | unclear | 1 | `T/test_literature_active_site_integration.py:203`. Prompt selection code differs from the original only in per-axis family tables. Not traced. | Left failing | No (prompt text) |

Class totals: product_defect 578 (P1 555, PB 15, I1 4, C1 3, G1 1), test_wiring 96 (W1 54, W2 18, W3 15, W4 6, W5 2, M1 1),
unclear 11 (RC 10, S6 1), stale_test 10 (S1 5, V1 1, S2-S5 4). Sum 695. C2 has no visible cases of its own.
`environment`: none in this cluster.

## 2. Implementation-digest pins: inventory for the owner (nothing changed)

Data files (complete, one row per pinned entry or per pinned file; produced by a read-only script run through the launcher,
`runs/claude_r2_r2d_scripts/pin_inventory.py`, runs `claude_r2_r2d_001`/`_002`):

- `runs/claude_inputs/failure_triage/r2d_pin_inventory.tsv` — 698 entries (`'<file>.py': '<sha256>'`) in non-test code of
  a101..a108: pin file, line, table, pinned name, pinned digest, the file the axis resolver actually hashes, its current digest,
  the digest of `gene_annotation_episode/<name>` at `078b77668` and at `fb1e4d9ba`, three yes/no match columns, where else the
  digest was found, and the difference class of the current file against `078b77668`. a110 has no such entries.
- `runs/claude_inputs/failure_triage/r2d_pinned_file_differences.tsv` — 246 pinned files, difference class and detail.
- `runs/claude_inputs/failure_triage/r2d_pinned_file_statement_differences.txt` — for the 52 files whose statements differ,
  the per-function diff (syntax-tree text, imports removed).
- `runs/claude_inputs/failure_triage/r2d_pinned_file_line_diff_counts.tsv` — plain `diff` line counts per file.

How the difference class was computed: both versions parsed with `ast`; every `import`/`from ... import` statement (at any depth)
replaced by `pass`; top-level statements compared by `ast.dump`. `imports_and_formatting_only` = every non-import statement
has the same syntax tree. This says nothing about whether the *imported* modules behave the same (import targets changed from
`.x` to an absolute per-axis module); it also treats comments and layout as formatting.

### 2.1 What the comparison shows

1. **The pinned files at `078b77668` and `fb1e4d9ba` are byte-identical** (no row differs between the two columns), so either
   revision is "the original".
2. **Every a105 pinned file was rewritten whole** by the reorganisation (plain `diff` touches 150-3,400 lines per file: quotes,
   wrapping, comments dropped), so no digest of a rewritten file can equal the original. Of the 54 distinct files pinned from
   `a105/library`: 9 are byte-identical to the original (all `*_prompt.py` / `*_render.py`), **38 differ in imports and
   formatting only**, 7 have statement differences (2.3). The `SEE/` copies (54 files) are the same except that 20 of them also
   gained `from __future__ import annotations`.
3. **Most pin tables are literally unchanged from the original** (same set of 64-hex literals at `078b77668` and now): they still
   name the original files' digests. That is the whole cause of the mismatch for binding interaction inputs, product coupling,
   kinetic, measurement validation, ion discrimination, concentration window and endpoint signal.
4. **Three tables were re-pinned during the reorganisation** (literals not present at `078b77668`):
   - `a105/library/literature_measurement_comparison_storage.py:627` `_V4_PURE_HASHES` (new receipt version v4): **20 of 20 equal
     the current files**. This is the only live table in a105 that passes. The `SEE/scoring` copy has no v4 table and still checks
     the original `_PURE_HASHES_V3` (line 307).
   - `literature_optical_storage.py:36` `_PINNED` (both copies): the entries for `literature_optical_inputs.py` (`226e466e...`) and
     `literature_optical_validation.py` (`42d63308...`) replaced the original pins (`6e956a39...`, `4340cce4...`, which did equal
     the original files). The new values equal **no** file: not the current files, not the originals, and no blob of that name in
     the trees of `dfe3e6091` or `HEAD` (76 blobs checked).
   - `literature_kinetic_summary_precision_storage.py:29` `_MOVED_HASHES` (both copies): 6 of 9 entries equal no file anywhere
     (same check); 3 equal the original.
   So these two were pinned to an intermediate state of the files that was never committed.
5. **One table was already inconsistent before the reorganisation**: `literature_binding_interaction_storage.py:30` `_FROZEN`
   and `:31` `_COMPATIBLE_RATE_STORAGE` list four digests for `literature_rate_storage.py`; the file at `078b77668` hashes to
   `e891fa45...`, which is none of them. The 9 `literature_binding_interaction_implementation_dependency_mismatch` failures
   would therefore have occurred on the original tree too. [inferred from digests; the original tree was not run]
6. The digests in historical maps that match neither the original nor the current file are older releases: a partial scan of
   `verification/` source snapshots found 8 of the 45 such digests (for example `52069b7d...` `literature_assay_inputs.py`,
   `66f7b53a...` `literature_rate_storage.py`). The scan was stopped early (146 GB tree), so "not found" for the other 37 is
   not evidence of absence.

### 2.2 Live checks in a105 (raise on populate) — one row per table

`lib` = `R/a105/library/`, `SEE` = the pilot copy (`SEE/scoring/` for `*_storage.py`, `SEE/tools/` for `*_inputs.py`). The two
copies have the same tables one line apart. "cur" / "orig" = number of entries whose pinned digest equals the file the resolver
reads now / the file at `078b77668`. Resolver: `R/a105/literature_implementation_sources.py:4` for `lib`
(`a105/<name>` then `a105/library/<name>`), `SEE/implementation_sources.py:6` for `SEE` (its `LOCAL_IMPLEMENTATIONS` map first).

| Raise site (lib ; SEE) | Code | Table (lib line ; SEE line) | Entries | cur lib / SEE | orig | Pinned files and how each differs from the original |
|---|---|---|---|---|---|---|
| `literature_binding_interaction_inputs.py:225,230` ; same | `binding_interaction_frozen_dependency_mismatch` | `_FROZEN` 71 + `CALCULATOR_SHA256` 72 ; same | 3 + 1 | 0 / 0 | 4 | `literature_binding_visual_inputs.py`, `literature_binding_reader.py`, `literature_binding_interaction_calculations.py`: imports+reformat. `literature_experimental_contracts.py`: class `ExperimentalContractError` moved out to `a105/literature_contract_error.py` and imported back. |
| `literature_binding_interaction_storage.py:56,59` ; `:57,60` | `literature_binding_interaction_implementation_dependency_mismatch` | `_FROZEN` 30, `_COMPATIBLE_RATE_STORAGE` 31 ; 31, 32 | 6 | 0 / 0 | 5 | as above plus `literature_binding_interaction_inputs.py` (its own `_dependencies` changed, 2.3) and `literature_rate_storage.py` (imports+reformat; **pin never matched the original either**). Lines 32-34 (`_ORIGINAL_`, `_PREVIOUS_`, `_PRE_CONNECTION_DEPENDENCIES`) are saved-record maps, compared only with a saved receipt. |
| `literature_optical_storage.py:59` ; same | `literature_optical_implementation_dependency_mismatch` | `_PINNED` 36 ; 36 | 3 | 0 / 0 | 1 | `literature_optical_inputs.py`, `literature_optical_validation.py`: imports+reformat, **pins changed in the reorganisation to values that match no file**. `literature_optical_calculations.py`: imports+reformat, pin = original. |
| `literature_product_coupling_storage.py:198` ; `:199` | `product_coupling_prospective_dependency_mismatch` | `_FROZEN` 29 ; 30 | 3 | 1 / 0 | 3 | `..._inputs.py`, `..._calculations.py`: imports+reformat. `..._prompt.py`: identical in lib; SEE copy adds `from __future__ import annotations`. |
| `literature_kinetic_storage.py:55` ; `:56` | `literature_kinetic_implementation_dependency_mismatch` | `_SOURCE_LOCATION_FROZEN` 32 (built from 30, 31) ; 33 | 6 | 0 / 0 | 6 | `literature_kinetic_calculations.py`, `literature_kinetic_inputs.py`, `literature_assay_inputs.py`, `literature_rate_native_inputs.py`, `literature_partner_source_fields.py`: imports+reformat. `literature_experimental_contracts.py`: class moved (above). `_LEGACY_FROZEN` 30 and `_LEGACY_SAVED_IMPLEMENTATION` 33 are saved-record maps (`:66,71`). |
| `literature_measurement_validation_storage.py:127` ; `:128` | `measurement_validation_prospective_dependency_mismatch` | `_FROZEN` 25 ; 26 | 3 | 1 / 0 | 3 | `..._inputs.py`, `..._calculations.py`: imports+reformat. `..._prompt.py`: identical in lib. |
| `literature_ion_discrimination_storage.py:187` ; `:188` | `ion_discrimination_prospective_dependency_mismatch` | `_FROZEN` 26 ; 27 | 4 | 1 / 0 | 4 | `..._numbers.py`, `..._inputs.py`, `..._calculations.py`: imports+reformat. `..._prompt.py`: identical in lib. |
| `literature_concentration_window_storage.py:305` ; `:306` | `concentration_window_prospective_dependency_mismatch` | `PURE_HASHES` 25 ; 26 | 3 | 1 / 0 | 3 | `..._inputs.py`, `..._calculations.py`: imports+reformat. `..._prompt.py`: identical in lib. |
| `literature_endpoint_signal_storage.py:147` ; `:148` | `endpoint_prospective_dependency_mismatch` | `_PURE_HASHES` 26 ; 27 | 3 | 1 / 0 | 3 | `..._calculations.py`, `..._inputs.py`: imports+reformat. `..._prompt.py`: identical in lib. |
| `literature_kinetic_summary_precision_storage.py:227` ; `:228` | `summary_precision_prospective_dependency_mismatch` | `_MOVED_HASHES` 29 ; 30 | 9 | 1 / 0 | 3 | `..._inputs.py`, `literature_kinetic_inputs.py`, `literature_assay_inputs.py`, `literature_rate_native_inputs.py`, `literature_partner_source_fields.py`, `literature_experimental_contracts.py`: **pins added in the reorganisation, match no file**. `..._calculations.py`, `literature_kinetic_calculations.py`: pin = original. `..._prompt.py`: identical. The original tables `_PURE_HASHES` 27 / `_PURE_HASHES_V2` 28 (8 of 9 and 1 of 1 = original) are now saved-record maps. |
| `literature_measurement_comparison_storage.py:306` ; `:307` | `measurement_comparison_prospective_dependency_mismatch` | lib: `_V4_PURE_HASHES` 627 ; SEE: `_PURE_HASHES_V3` 30 (from 27, 29) | 20 | **20** / 0 | 2 / 20 | lib passes (re-pinned to the current files, receipt version v4): 17 files imports+reformat, 2 identical prompts, 1 with a statement difference (`literature_experimental_contracts.py`, class moved). SEE still pins the 20 originals. |

Not live-checked against files (declared constants written into records and compared with saved records only):
`literature_optical_inputs.py:27` `LEXICAL_DEPENDENCY`, `literature_optical_validation.py:25`, `literature_amount_inputs.py:31-32`,
`literature_kinetic_inputs.py:32-33` (`sha256_at_release` / `custody_sha256` values; their `module`
fields still say `gene_annotation_episode.literature_rate_native_inputs`, a module that no longer exists at top level — the a104
copies of these constants were rewritten to `...root.a104.literature_rate_native_inputs`, a data change);
`literature_controlled_response_inputs.py:75` `DEPENDENCIES`, `literature_controlled_response_v2_inputs.py:472` and
`_v3_inputs.py:451` `_RETAINED_SAVED_DEPENDENCY_RELEASES` (added in the reorganisation), and
`R/a105/episode_composition.py:42` `_SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY` (pairs of whole-binding digests accepted when
reopening a saved run). These are in the TSV but cause no failure in this cluster.

### 2.3 Pinned a105 files whose statements differ from the original (all seven, both copies)

| File | Difference |
|---|---|
| `literature_binding_interaction_inputs.py`, `literature_binding_interaction_storage.py`, `literature_kinetic_storage.py` | `_dependencies()` only: `Path(__file__).with_name(name)` became `source_file(name)`. |
| `literature_experimental_contracts.py` | class `ExperimentalContractError` removed and imported from `a105/literature_contract_error.py` (same body there not compared). |
| `literature_controlled_response_v2_inputs.py` | `_dependencies()` as above; `_validate_graph` gained a required keyword `implementation_fingerprints` and compares `counter_module_sha256` with it instead of with the live file digest; new table `_RETAINED_SAVED_DEPENDENCY_RELEASES`. |
| `literature_controlled_response_v3_inputs.py` | `_dependencies()` as above; `_finish_v3` and the v3 validator pass the saved fingerprints; same new table. |
| `literature_controlled_response_inputs.py` | `_SavedV3SourceContext` keeps the saved dependencies; `_validate_v2_saved_science` / `_validate_v3_saved_science` now also accept a saved record whose `expected_module_fingerprints` equal a retained release. |

The three controlled-response changes alter which saved records are accepted; they are not formatting.

### 2.4 Identical pin sites in other axes (counted, not analysed further)

| Axis copy | Live check sites | Entries: equal current / equal original / neither |
|---|---|---|
| `R/a104/literature_*_storage.py`, `*_inputs.py` (12 pin files) | 7 `*_prospective_dependency_mismatch` sites + binding interaction, kinetic, optical | 95 entries: 60 / 70 / 25. The a104 files keep relative imports and 44 of the 54 pinned a104 files are byte-identical to the original, so most a104 pins hold. Among those that do not: `literature_optical_storage.py:56,58` (the same re-pinned values as a105). The a104 tables are multi-line, so the TSV identifies entries by line, not by table name. |
| `R/a106/library/literature_*_storage.py`, `*_inputs.py`, `controlled_response_retained_profiles.py` (13 pin files) | same 7 sites + binding interaction, kinetic, optical | 173 entries: 10 / 131 / 42. Same state as a105: files rewritten, tables original. `a106/tests/test_literature_optical_storage.py` fails 38 times on `a106/library/literature_optical_storage.py:53-55`. |
| `R/a101/library/retained_input_authority/literature_controlled_response_inputs.py:112`, `R/a108/library/retained_input_authority/...:112` | none raising `*_dependency_mismatch` | 8 entries each: 0 / 5 / 3 |
| `blast_utility_historical_fact_schemas.py:21-37` in a101 (library), a103, a104, a107 | none (historical schema facts) | 12 entries each: 0 / 6 / 6 |
| a102, a110 | none | no entries |

### 2.5 What this means for re-pinning

- For the 38 `imports_and_formatting_only` files, replacing a stale pin by the current digest asserts only that the import
  re-pointing is behaviour-preserving; the statements are the same syntax tree as the pinned original.
- For the 7 files in 2.3 the current digest covers a real code change; three of them change saved-record acceptance.
- Two a105 tests written with the reorganisation already expect refreshed receipts that the product does not produce:
  `R/a105/tests/test_private_scientific_attestations.py:30` expects `summary_precision_original_implementation_v4` (product
  writes `_v3`, `literature_kinetic_summary_precision_storage.py:228`), and
  `R/a105/tests/test_private_publisher_receipts.py:71` expects `concentration_window_original_implementation_v2` with a
  `publisher_binding` (product writes `_v1`, `literature_concentration_window_storage.py:306`). Neither string exists in
  any product file in the tree. So the intended end state (new receipt versions, as was done for measurement comparison v4)
  is visible in the tests, but the product side is absent.
- `R/a105/ownership_inventory.json` and `SEE/ownership_inventory.json` also record a sha256 per file. No Python code reads
  them; they go stale with any product edit (including the two import lines added in this round, section 4).

## 3. Detail on the layered failures

### 3.1 `KeyError: 'literature_strategy'` (54 cases): three layers

1. **W1, test wiring (fixed).** `episode_binding_factories=(partial(LiteratureEpisode, ...),)` binds only the top home.
2. **C1, product (not changed).** With seven homes bound the root episode's first decision fails inside the loop and the run
   ends `source_failed` with `selected_operation_failed` / `AttributeError`; the tests then fail on their first count
   assertion (`assert 0 == 1`, `assert (0.0 == 0 and 0 == 1)`, `assert 0 == 4`, `IndexError`, ...). Printed traceback
   (run 016): `R/a105/runtime.py:3474 build` -> `:2257 source_credit_view` -> `PEA/credit.py:283 credit_view` ->
   `AttributeError: 'LiteratureEpisode' object has no attribute '_scientific_credit_invocation'`. [run]
3. **C2, behind C1 (not changed).** In a diagnostic batch with the method made reachable (runs 161-201), none of the 53 cases
   examined passes. In **43** the root's child commission is rejected with
   `{'category': 'action_contract', 'detail': 'literature_original_task_credit_required'}` (raised at
   `R/a105/scientific_process/published_evidence_assessment/goal.py:61` and its copies; the code existed in the original as
   `literature_task_credit.py:230`), after which the scripted provider is out of step. The two sibling tests that do pass at
   this point (`test_literature_assay_integration`, `test_literature_a105_aggregation_binding_325`) were rewritten in the
   reorganisation to put a `literature_task` (kind, answer kind, `credit_unit`) and a `proposed_annotation_ref` in the child
   assignment and to expect `summary['credit'] == 0`; the 43 were not. Choosing those values per test is a statement about
   what A105 credit each scripted action earns, so it is left to the owner. [run]
   The other 10 cases (6 tests: `test_a105_partition_time_joined_149` x2 tests, `test_literature_a105_assay_type_binding_322`,
   `test_literature_assay_experiment_instances_323`, `test_literature_ion_discrimination_binding_199`,
   `test_literature_p205_parent_depletion_308`) fail differently behind C1 and were not traced.

### 3.2 `test_literature_missing_input_semantics_156` after W2

- `test_fresh_v2_selected_operation_typed_subset_and_cold_descriptor_reconstruction` (2): the fixture script
  `T/fixtures/retained_reference/a105_missing_input_semantics_156/cold_reconstruct.py` imported nine top-level modules that
  no longer exist and took the repository from `services`. **Fixed** (imports to the a105 copies, accessor on the binding);
  both pass [run 202].
- `test_exact_prechange_v1_replay_projection_original_schema_and_admission` (2): expects `DurableExecutionError`
  `identity_conflict` when a saved pre-reorganisation descriptor is reopened; `R/a105/episode_composition.py:142-155` now
  answers `unavailable_binding` because the saved `binding_id` is `literature`, which is not among the registered ids. Both are
  refusals; which code is intended for a pre-reorganisation run is an owner question. Left failing.

### 3.3 `test_literature_active_site_integration::test_controlled_child_population_parent_return_and_reconstruction_are_single_actions`

Uses the seven-home helper already. Fails on C1; with C1 out of the way the third scripted response receives no child report
(`not enough values to unpack`), the same shape as 3.1 layer 3. Not traced further.

## 4. Edits (test side, plus two import lines)

`git diff --stat` restricted to the files below: **48 files changed, 143 insertions(+), 85 deletions(-)**. No commit.
Nothing retired (0 rows added to `retired.tsv`).

| Files | Change |
|---|---|
| 41 files in `T/` (list: `runs/claude_r2_r2d_scripts/edit_files.txt`) | `(partial(LiteratureEpisode, <config>),)` -> `literature_binding_factories(<config>)` at 49 sites, plus the import |
| `T/runtime_fixtures.py` | new helper `literature_binding_for_role(binding, role)`: builds the home that owns `role` from the configuration the binding records; unknown role raises `KeyError` |
| `T/test_literature_missing_input_semantics_156.py`, `test_literature_amount_integration.py`, `test_literature_amount_range_scope_integration.py`, `test_literature_calibration_recovery_binding_173.py`, `test_literature_native_rate_domain_integration.py`, `test_literature_a105_assay_type_binding_322.py`, `test_literature_rate_source_semantic_integration.py`, `test_literature_rate_observations_166.py`, `test_literature_ion_discrimination_binding_199.py` | `literature_<kind>_repository()` taken from the binding instead of `services` (W2). In `..._ion_discrimination_binding_199.py:515` the forbidden-accessor list drops `literature_perturbation_repository` and `literature_reaction_repository`, which a105 no longer has |
| `T/test_literature_endpoint_signal_binding_244.py`, `..._calibration_recovery_binding_173.py`, `..._concentration_window_binding_281.py`, `..._reported_curve_binding_231.py`, `..._rate_observations_166.py`, `..._measurement_comparison_binding_268.py` | page-role call goes to `literature_binding_for_role(binding, 'literature_page')` (W4) |
| `T/test_literature_measurement_comparison_binding_268.py` | `received_form_references(parent, ...)` -> `receive_child_result(parent, 'literature_strategy', ...)` (M1) |
| `T/test_private_instruction_service_dispatch.py` | `is_job_source=lambda value: False` on the fake workflow (W3) |
| `T/test_private_binding_restoration.py` | shared-root `DurableExecutionError` (W5) |
| `T/test_literature_controlled_response_v3_stages.py` | `implementation_fingerprints=result['implementation_dependencies']['expected_module_fingerprints']` (V1) |
| `T/fixtures/retained_reference/a105_missing_input_semantics_156/cold_reconstruct.py` | nine imports re-pointed to a105; accessor on the binding (3.2) |
| `lib/literature_task_selection.py`, `SEE/prompts/literature_task_selection.py` (**product**) | one import line each: `from <same directory>.literature_rate_observation_prompt import REPORTED_CURVE_SCOPE_TASK` (I1). This changes both files' sha256; no pin table names them, but `R/a105/ownership_inventory.json` and `SEE/ownership_inventory.json` record the old digests |

Not edited although they show the same patterns, because they fail earlier on P1 and the result could not be checked:
page-role calls in `T/test_literature_kinetic_model_integration.py:101,113`,
`T/test_literature_binding_interaction_model_integration.py:99,111`, `T/test_literature_common_assessment_binding_223.py:98`.

**Coordination.** 89 of agent r2b's cases (missing parked helper modules, un-rewritten `monkeypatch` strings, one fixture path)
are in 19 test files that are now modified by r2d, so r2b will find them modified and skip them. Two a105 test files were
modified by another agent during this work and were not touched here: `T/test_literature_binding_model_storage.py`,
`T/test_literature_missing_input_semantics_177.py`.

## 5. Runs

All through `tools/one_workflow.sh --slot r2d`, one test file per run, each in a new directory
`runs/claude_r2_r2d_001` .. `_203` (108 and 109 were never used; 113 was interrupted, see below).

| Batch | Purpose | Expected | Actual |
|---|---|---|---|
| 001-002 | pin inventory script (not pytest) | under 2 min | 16 s each |
| 003-014 | 6 files twice, to read the hidden outcome codes | about 80 s per pass | about 60 s per pass |
| 015-021 | assay / aggregation / active-site files with diagnostic plugins | about 1 min | about 2 min |
| 022-062 (plain A) | 41 files after the W1 edit | 444 s of test time, 8-9 min | 615 s |
| 064-107 (plain C) | 44 files after all edits but M1, V1, W5 and the fixture script | about 11 min | 586 s |
| 110-112 | first three files of a diagnostic batch, stopped when the coordinator's outside-services rule arrived | - | - |
| 063, 114-118, 160, 202, 203 | single files and two read-only scripts; from 114 on with the new prefix | under 1 min each | 7-27 s each |
| 119-159, 161-201 | two diagnostic batches of 41 files, with the new prefix | about 9 min each | 514 s, 452 s |

From run 114 on, every run used an empty `HOME` inside its run directory and the eight proxy variables pointing at
`127.0.0.1:9`. One deviation from the coordinator's wording: the launcher refuses an existing run directory
(`tools/one_workflow.sh`, "A fresh run directory is required"), so `HOME` could not be created before launching; the wrapped
command is `env HOME=... <proxies> bash -c 'mkdir -p "$HOME" && exec "$@"' _ eatmydata .venv/bin/python -m pytest ...`
(`runs/claude_r2_r2d_scripts/run1.sh`, `batch2.sh`). The three files run under both conditions with the same plugins (110-112 and 119-121) and `test_literature_reported_curve_binding_231` (012 and 117) gave the same pass/fail counts, so nothing here is classified `environment` on that account.

### Before / after (plain runs, no plugin)

"Before" = `runs/claude_tests_leaf_up_20261114_03_a105/results.tsv`. Columns are passed / failed.

| Test file | Before | After | Run |
|---|---|---|---|
| `test_literature_a105_assay_type_binding_322.py` | 9 / 5 | 10 / 4 | `r2d_065` |
| `test_literature_amount_integration.py` | 1 / 4 | 2 / 3 | `r2d_070` |
| `test_literature_amount_range_scope_integration.py` | 1 / 2 | 2 / 1 | `r2d_071` |
| `test_literature_calibration_recovery_binding_173.py` | 9 / 4 | 11 / 2 | `r2d_077` |
| `test_literature_concentration_window_binding_281.py` | 6 / 22 | 7 / 21 | `r2d_082` |
| `test_literature_endpoint_signal_binding_244.py` | 9 / 38 | 10 / 37 | `r2d_083` |
| `test_literature_ion_discrimination_binding_199.py` | 3 / 22 | 4 / 21 | `r2d_085` |
| `test_literature_measurement_comparison_binding_268.py` | 20 / 7 | 22 / 5 | `r2d_114` |
| `test_literature_missing_input_semantics_156.py` | 0 / 13 | 10 / 3 | `r2d_202` |
| `test_literature_numerical_declarations_203.py` | 231 / 16 | 235 / 12 | `r2d_092` |
| `test_literature_rate_observations_166.py` | 15 / 4 | 16 / 3 | `r2d_099` |
| `test_literature_rate_source_semantic_integration.py` | 0 / 3 | 1 / 2 | `r2d_100` |
| `test_private_instruction_service_dispatch.py` | 32 / 15 | 47 / 0 | `r2d_105` |
| `test_private_binding_restoration.py` | 3 / 2 | 5 / 0 | `r2d_115` |
| `test_literature_controlled_response_v3_stages.py` | 40 / 1 | 41 / 0 | `r2d_116` |
| 31 other files, unchanged counts | | | |
| **Total (46 files)** | **492 / 426** | **536 / 382** | |

Previously passing files rerun as a check on the touched helper and module: `T/test_literature_assay_prompt.py` 1 / 0 ->
1 / 0, `T/test_private_literature_provider_routing.py` 28 / 0 -> 28 / 0 (both import the prompt code that imports
`literature_task_selection.py`). No previously passing a105 test file imports `T/runtime_fixtures.py`, so there was none to
rerun for that helper; the helper change only adds a function.

## 6. Owner questions

1. **Pins (P1, 555 cases).** Section 2. Re-pin to the current files (possibly with new receipt versions, as measurement
   comparison v4 did and as two tests already expect), or restore the pinned bytes?
2. **Credit method placement (C1).** May `_scientific_credit_invocation` be moved from `LiteratureTaskCredit` to
   `LiteratureCredit` / `SourceCredit` in the 14 a105 `credit.py` files (and the 14 in a108), as a106 has it?
3. **Original task credit in scripted tests (C2, 43 cases).** Which `literature_task` should each scripted child commission
   carry, or should a caller-supplied `project_credit` be accepted without one as before?
4. **Publisher binding in receipts (PB, 15 cases).** Is the product side of `test_private_publisher_receipts` (registry on the
   repositories, `publisher_binding`, receipt v2) still to be written? Meanwhile `bound_descriptor` is `None` in new
   concentration-window and measurement-comparison receipts because the lookup still uses the id `literature`.
5. **Reported-curve grid registration (RC, 10 cases).** Should the outer rate-observation repository register a sheet it
   delegated to the reported-curve repository?
6. **Legacy replay without `experiment_ref` (G1).** `lib/literature_assay_grading_storage.py:101` blocks the replay that
   `:118` allows.
7. **Delivery routing (M1)** and **legacy descriptor refusal code (3.2)**: confirm that `received_form_references` returning
   `[]` for literature roles and `unavailable_binding` for a saved `literature` descriptor are intended.
8. **Controlled-response saved-record acceptance (2.3)**: three pinned files changed logic in the reorganisation.
9. Stale expectations left failing (S1-S6, 10 cases): update or retire.

## Reaches outside services

None found in this cluster. Checked by search over the 46 test files that were run and the fixture scripts they start: no
use of `PublicClients` methods, `urllib`, `requests`, sockets, ssh or the real home directory. Four of the files start a
local Python subprocess on a retained fixture script (`first_cold_process_001.py`, `cold_reconstruct.py`); these read only
the test's own store. `ToolRegistry(store)` constructs `PublicClients()` (`R/a105/tools.py:66`), which is inert until a public
acquisition tool is selected; the tools named in these tests are `literature.*.populate`, `source.read`, `source.locate` and `state.query`, which
work on the test store. `PublicClients` would look for skills under `Path.home() / '.codex/...'`
(`R/a105/acquisition.py:60`) if such a tool were selected. `tests/test_sequence_support_739.py` is not in this cluster and
was not run.

## Not done

- No pin, credit, grading or receipt code was changed, so P1, C1, C2, PB, RC and G1 remain failing (about 640 cases).
- The original tree was read, never run; every "predates the reorganisation" is from identical code or digests.
- S1: the full schema diffs were not printed; S6, 3.3 and the 10 non-credit cases in 3.1 were not traced.
- The partial `verification/` digest scan (section 2.1 item 6) was stopped early.
- `R/a104/literature_task_selection.py` has the I1 gap and was not edited (other axis).
- Throw-away scripts and plugins are in `runs/claude_r2_r2d_scripts/` (disposable).
