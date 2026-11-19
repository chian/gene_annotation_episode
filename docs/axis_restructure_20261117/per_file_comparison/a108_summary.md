# A108 per-file comparison against 7e662ea29

Scope: the 36 baseline rows of `docs/verification_20261116/results_per_file.tsv` under
`gene_annotation_episode/episodic_workflow/root/a108/` (all in `a108/tests/`). Per-row detail: `a108.tsv`.
Compared on 2026-11-18. Each current file ran alone through `tools/one_workflow.sh --slot pf108`
(`runs/pf108_cmp/f_0001` to `f_0005`, empty HOME, blocked proxy).

## Counts

| | Baseline | Now |
|---|---|---|
| Test files | 36 | 5 |
| Tests | 529 | 12 |
| Passed | 526 | 12 |
| Failed | 3 | 0 |
| Errors | 0 | 0 |

| Status | Files |
|---|---|
| same | 2 |
| changed | 3 |
| retired (recorded) | 26 |
| retired-unrecorded | 5 |
| regression | 0 |

## Regressions

None. Every test that still exists passes. The 3 baseline failures (the `a105` parameter of
`test_original_molecular_material_port.py`, `local_resource_binding_conflict`) went with that deleted file.

## Current files and results

| Baseline file | Current path | Baseline | Now | Status |
|---|---|---|---|---|
| test_literature_context_scalar.py | `episode_support/literature/readers/sample_context_evidence/tests/test_literature_context_scalar.py` | 2/0 | 2/0 | same |
| test_private_unresolved_context.py | `episode_support/literature/storage/tests/test_private_unresolved_context.py` | 2/0 | 2/0 | same |
| test_canonical_workflow_resources.py | `tests/test_canonical_workflow_resources_sample_context_evidence.py` | 4/0 | 2/0 | changed |
| test_private_context_publication.py | `episode_support/literature/storage/tests/test_private_context_publication.py` | 4/0 | 3/0 | changed |
| test_resource_policy_reopening.py | `tests/test_resource_policy_reopening_sample_context_evidence.py` | 4/0 | 3/0 | changed |

Changed files:

- **test_private_context_publication** (4 → 3): 1 fake test deleted, recorded in
  `runs/claude_ablate/a108_fake_tests.tsv` line 18. The kept tests were retargeted to `LiteratureContext`, and
  one assertion changed from "`runtime_actions` has 0 rows" to "no `runtime_actions` table exists".
- **test_resource_policy_reopening** (4 → 3): 1 fake test deleted, recorded in `a108_fake_tests.tsv` line 8.
  Not recorded: the kept test now constructs the top-level `gene_annotation_episode.local_resources`
  instead of the deleted `a108/local_resources.py` copy.
- **test_canonical_workflow_resources** (4 → 2): the removal of 2 tests has no A108 record (see below).

## Retired-unrecorded files, with the reason worked out

Each of these was partly recorded; the unrecorded part is the last deletion that removed the file.

1. **test_original_molecular_material_port.py** (12 tests, 9 passed / 3 failed) — no retirement record at all.
   Every case built `<axis>/state.Store` and `<axis>/tools.ToolRegistry(store, clients=SimpleNamespace())` for
   a101/a105/a106/a108. The per-axis state modules are deleted and the clients object is a stand-in.
   **Behaviour no longer tested anywhere:** `materials.artifact_path` keeping private publication request and
   auxiliary files closed (`molecular_private_artifact_not_readable`). That code still exists at
   `episode_support/records/documents/sample_context_evidence/materials.py` line 136.
2. **test_no_count_resource_admission.py** (6 tests) — 5 recorded as fake (`a108_fake_tests.tsv` line 6). That
   row says `test_native_request_with_multiple_threads_retains_one_cpu_whole_window` was kept as real; it was
   then deleted without a record. It passed a `SimpleNamespace` policy stand-in to
   `workflow_budget.native_budget`. **Behaviour no longer tested anywhere:** `native_budget` (still called by
   `episode_support/jobs/local_execution/sample_context_evidence/native_lifecycle.py`).
3. **test_count_free_route_guidance.py** (11 tests) — 6 cases recorded as fake (`a108_fake_tests.tsv` line 7).
   The 5 kept `compare_routes` cases were deleted without a record. They tested `a108/execution_guidance.py`,
   which was deleted; no A108 copy exists under `episode_support/instructions`. `compare_routes` is still
   tested for other axes (`jobs/local_execution/{partner_presence_evidence,biochemical_feasibility_evidence}/tests/test_local_resource_count_free.py`).
4. **test_private_dynamic_scientific_selectors.py** (2 tests) — 1 recorded (`a108_retired.tsv` line 7).
   `test_dynamic_population_metadata_uses_actual_original_storage` was deleted without a record. It tested
   `a108/library/literature_task_families.population_task_metadata_specs`; that A108 module was deleted, and the
   surviving shared `literature_task_families.py` holds only the three A106 families.
5. **test_protected_reference_boundaries.py** (5 tests) — 4 resolver cases recorded (`a108_results.md` line 33).
   `test_actual_tool_registry_retains_metadata_guard_without_a_producer` was deleted without a record. It used
   `a108/state.Store` (deleted) and a `SimpleNamespace` clients stand-in, and checked
   `ToolRegistry.retained_molecular_reference_access`, which no longer exists anywhere in the code.

Also unrecorded, in a file that still exists:

- **test_canonical_workflow_resources**: `test_actual_registry_constructor_uses_authenticated_run_resources`
  and `test_original_native_memory_bound_rejects_oversized_request_without_launch` were deleted. Both used
  `SimpleNamespace` stand-ins; the same functions are recorded as fake for the A101/A105 copies
  (`a101_fake_tests.tsv` lines 146-147, `a105_fake_tests.tsv` lines 12-13). **Behaviour no longer tested
  anywhere:** `native_budget` rejecting an oversized request (`native_request_exceeds_environment_bounds`).

## Where the records are

Only 11 of the A108 retirements are recorded under `docs/`: `retired_tests.tsv` lines 285-295
(test_retained_disorder_score_schema, test_retained_uniprot_form_contract,
test_retained_restriction_form_contract). `retired_fake_tests.tsv` has no row for any `a108/tests` file. Every
other record cited in `a108.tsv` is in the git-ignored `runs/claude_ablate/`:

- `a108_retired.tsv` (10 rows);
- `a108_fake_tests.tsv` (17 rows);
- `a108_results.md` (first-pass table: 6 files retired with the runner/registry, 4 files halved when the 7
  duplicate literature homes were deleted, 4 resolver cases);
- `a108_needs.md` lines 91-95 (test_private_head_credit_selector.py, prose only).

## New tests in scope

None. `root/a108/` contains no test file now.

Two files were created after the baseline and deleted again, both recorded:

- `a108/tests/test_episode_runtime_head.py` — `retired_tests.tsv` line 365 and `a108_fake_tests.tsv` line 2;
- `a108/tests/test_literature_runtime.py` — `retired_tests.tsv` line 366. This was the named replacement for
  test_private_literature_boundaries.py and test_private_literature_progress.py (`a108_retired.tsv` lines
  10-11), so the literature role/children, assignment-schema, credit and continuation checks of those two
  files have no current test.
