# A105 per-file comparison with the 7e662ea29 baseline (18 November 2026)

Scope: the 184 rows of `docs/verification_20261116/results_per_file.tsv` under
`gene_annotation_episode/episodic_workflow/root/a105/`. Table: `a105.tsv` (one row per baseline row).

Method: each current file ran in its own pytest process through `tools/one_workflow.sh --slot pf105`
(empty HOME, blocked proxy, eatmydata): `runs/pf105_cmp/f_0001` .. `f_0109`, list `runs/pf105_cmp/scope_current.txt`,
outcomes `runs/pf105_cmp/run_log.tsv`. Baseline test ids and outcomes were read from the retained baseline JUnit
files (`runs/claude_f4a_s0..3/junit`; their per-file counts equal the baseline rows exactly). Comparison is by test id.
Row numbers cited in `a105.tsv` are file line numbers (header = line 1; `runs/claude_r2105/pruned_tests.tsv` has no header).

## Counts per status

| status | files | baseline items | baseline failed |
|---|---|---|---|
| same | 77 | 4,038 | 0 |
| changed | 31 | 627 | 10 |
| retired | 72 | 1,096 | 45 |
| retired-unrecorded | 4 | 121 | 0 |
| regression | 0 | - | - |

Baseline: 5,882 items, 5,827 passed, 55 failed (31 files), 0 errors.
Now: 109 files, 4,527 items, 4,527 passed, 0 failed, 0 errors (4,522 in files with a baseline row, 5 in one new file).

1,362 baseline items are gone, 2 ids are new in existing files:

| where the removal is recorded | functions | items | of them failing at baseline |
|---|---|---|---|
| `runs/claude_ablate/a105_retired.tsv` (deleted A105 runner, registry/composition) | 125 | 361 | 42 |
| `runs/claude_ablate/a105_fake_tests.tsv`, action `deleted` (fake tests) | 108 | 474 | 11 |
| `runs/claude_r2105/pruned_tests.tsv` (deleted old-runner apparatus, runner-journal delivery, deleted copies) | 107 | 419 | 2 |
| no record: three duplicate-tree test files | 53 | 107 | 0 |
| no record: one test | 1 | 1 | 0 |

All 55 baseline failures were removed with their tests under a recorded reason; none was fixed and none remains.
No id that exists in both runs changed outcome.

## Regressions

None. No test that passed at the baseline fails or errors now.

## Retired-unrecorded (4 files)

1. `a105/scientific_process/.../source_evidence_examination/tests/test_episode_responsibilities.py` (14 passed).
   13 items are recorded (`a105_fake_tests.tsv` rows 2-8, `a105_retired.tsv` rows 121-122).
   `test_required_grading_keeps_typed_finding_in_same_action` has no row anywhere. It was the last test in the file and
   went when the `source_evidence_examination` duplicate tree was deleted. It asserted that
   `literature_required_grading.action_schema()` makes `investigation_finding` a required assessment field and adds
   `evidence_processing` to the reasoning action. `action_schema` survives unchanged in
   `episode_support/literature/grading/experimental_activity_evidence/literature_required_grading.py` and is called by
   `a105/experimental_activity_evidence/published_evidence_assessment/literature_source.py`; no current test asserts it.
   This is the one lost check of live code in scope (AGENTS.md requires the typed `investigation_finding`).
2. `.../source_evidence_examination/tests/test_literature_assay_grading.py` (55 passed)
3. `.../source_evidence_examination/tests/test_literature_assay_grading_inputs.py` (25 passed)
4. `.../source_evidence_examination/tests/test_literature_assay_grading_uncertainty_324.py` (27 passed)

   Files 2-4: no record names their deletion. Each was a copy of `a105/tests/<same name>` with the same test ids,
   importing the `source_evidence_examination/grading/` module copies instead of `a105/library`. Those module copies were
   deleted as a duplicate tree (README global plan, P2). The library-side files survive under
   `episode_support/literature/grading/experimental_activity_evidence/tests/` with the same ids, all passing (55, 25, 26;
   the 27th uncertainty test was pruned from both copies, `pruned_tests.tsv` row 98). The two module copies were not
   byte-identical at 7e662ea29 (`literature_assay_grading.py` 3+/277-, `literature_assay_grading_inputs.py` 7+/6-,
   `literature_required_grading.py` 4+/3-), so the deleted copies' own code is no longer exercised.

## Other things without a record

- `test_parent_receives_reprojected_child_cells_bound_by_digest` is new in
  `episode_support/literature/storage/experimental_activity_evidence/tests/test_literature_gel_storage.py` and
  `.../test_literature_controlled_response_storage_v3.py` (both pass; real repository/Store tests). No record of the addition.
- None of the A105 removals is in `docs/axis_restructure_20261117/retired_tests.tsv` or `retired_fake_tests.tsv`
  (0 A105 test rows). The records exist only under `runs/` (`claude_ablate/a105_retired.tsv`, `a105_fake_tests.tsv`,
  `claude_r2105/pruned_tests.tsv`); the last one is not among the record files listed for this verification.
- `a105_fake_tests.tsv` marks 206 rows `KEPT_FOR_REVIEW`; 8 of those rows (7 tests) were later removed, each with a
  `pruned_tests.tsv` row. The other kept tests are still present and pass.
- `a105/tests/test_private_scientific_process.py` was renamed `test_private_experimental_activity_evidence.py` at
  212a50868 and then deleted; its records use the later name.
- The test-file moves have no old-path/new-path table (`runs/placement_move/a105_moved.txt` has no test rows); the move
  is evidenced by `runs/placement_tests/a105_before.txt`, `a105_after.txt` and the `*_ids.txt` lists. Current ids equal
  `a105_after_ids.txt`.

## Current test files in scope with no baseline row

| file | tests/passed/failed/errors |
|---|---|
| `gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/tests/test_runtime_bindings.py` | 5/5/0/0 |

It checks the A105 home factory's required services and the literature population declarations on the shared Store.

Two current files carry a baseline row under another name or home:
`tests/test_canonical_workflow_resources_experimental_activity_evidence.py` (from `a105/tests/test_canonical_workflow_resources.py`, 4 -> 2)
and `episode_support/literature/calculations/tests/test_literature_rate_bound_calculations.py` (from `a105/tests/`, 30 = 30, no axis folder).
