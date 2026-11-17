# Whole-tree verification after removing backward-facing code and code self-fingerprinting (16 November 2026)

Tree verified: commit `f4a7e9788` (branch `first-full-draft-2026-11-10`); first verified at `ce30170dd`, re-run at
`a62a4d7cf` (identical per file) and at `f4a7e9788` (run `runs/claude_f4a_s0..3`; changes below).

- `home_summary.tsv`: one row per episode home (593) plus top-level `tests/`: test files, tests, passed, failed,
  errors, skipped, retired tests, modules, lines, identical copies, guard sites, modules failing import.
  Built by `tools/summarize_homes.py` from the run below.
- Collection: `pytest --collect-only` over `gene_annotation_episode` and `tests`: 50,585 tests, 0 collection errors
  (at `f4a7e9788`; 50,582 at `ce30170dd`).
- Imports: `tools/verify_episode_homes.py`, every home in its own interpreter, leaves first: 593 homes, 0 failures (`homes.json`).
- Test run: `tools/run_tests_by_home.py --per-file`, 4 shards, each through `tools/one_workflow.sh` under `eatmydata`,
  isolated HOME and blocked proxy; 1,634 files (all except `tests/test_bvbrc_proteome_host_integration.py`).
  Per-file results: `results_per_file.tsv`; failing tests with messages: `failing_tests.tsv`.
- Totals at `f4a7e9788`: 50,801 tests run, 49,147 passed, 1,127 failed, 420 errors, 107 skipped.
- Failures: every failing file (205) is named in a triage report (`docs/test_failure_triage_20261114/`) or a purge
  report (`docs/purge_20261115/`) that records its cause: `failing_files_and_cause_reports.tsv`. Compared per file with the
  latest measured result of each file during the purge, no file has fewer passes or more failures; 32 have more passes.
  (At `ce30170dd`. The `f4a7e9788` changes are listed under Owner decisions; `tests/test_molecular_acquisition_ordinary.py`
  is the one new failing file, so the count stays 205 with `test_root_task_declaration.py` now passing.)
- Per-test causes: `failing_test_causes.tsv` gives one row for each of the 1,547 failing tests (1,127 failures + 420
  errors): cause code, one-sentence cause, deciding code location and the report that already covered it (`new` if
  none). Each was established from that test's JUnit traceback and the current code at the deciding frame (six
  read-only shards A-F; per-code explanations, whether a fix would change scientific behaviour and the fix site are in
  `cause_codes/shard_*.md`). The last five (`test_wait_target_failures` durable cases, two `test_reference_edit_outcome_tools`
  read_stored cases) were settled by probe runs `runs/claude_cnf3`, `runs/claude_cnf4`. 0 rows are `cause_not_found`.
- Purge regression found and fixed: removing `implementation_sha256` from the nine
  `*/execution_monitoring/binding_identity.py` records made all nine monitor records equal, so
  `root/monitor_binding_catalogue.py` matched each saved descriptor to several parents (`identity_conflict`). Each
  record now carries its class's `commissioning_parent`. The 43 affected tests now pass that check and stop at the
  next, already recorded cause (mainly the role-only binding lookup); per-file counts of the five affected files and of
  the 23 files that build monitors are unchanged when each is run alone (`runs/claude_monitor_fix1`, `..._fix3_*`).
  At `f4a7e9788` their 43 rows were re-caused to that next cause (`role_only_binding_lookup`): the BV-BRC episode
  fixtures stop at the role-only `for_role('launch')` in `root/decision_information.py:32`, which
  `Episode.run_async` (`method_loop/episode.py:1273`) records as `source_failed` before the first model call, so those
  tests then see empty archives (probes `runs/claude_bvp4`, `runs/claude_bvp5`); the compact-custody fixture and
  compact-family tests stop at `root/report_validation.py:43` (`launch_api`); one macs2 test at its own
  `for_role('results')`.
- Owner decisions (16 November 2026, applied in `f4a7e9788`):
  - An unbound `improvement` role fails explicitly (`episode_role_not_bound:improvement`). The five decision sites
    that routed it to `legacy_annotation` are removed: `task_selection.py`, `continuation_observation.py`,
    `credit_projection.py` (twice) and `episode_bindings.for_path`. The two `test_root_task_declaration` cases now pass.
    37 tests that hosted an ordinary getter caller in an unbound `improvement` root (`episode_binding_factories=()`)
    now raise `episode_role_not_bound:improvement` before their own check (cause `unbound_improvement_host_removed`):
    `test_encode_tools` 25 (23 → 25 failing), `test_screen_tools` 4 (2 → 4), `test_molecular_acquisition_ordinary` 4
    (0 → 4), `test_jaspar_tools` 2, `test_episode_receipts` 1, `test_scientific_child_credit` 1. They need an explicit
    host binding.
  - The rest of the `legacy_annotation` route can no longer be reached but is still in the tree: the home itself, the
    `_implicit_parent == 'legacy_annotation'` branches in the `*_child_message_owners.py` files and
    `library/nominal_child_messages.py`, the arm copies (`a105`/`a108` `annotation_improvement/episode.py`, the a103
    standalone legacy parents in `a103/episode_bindings.py`). The owner directed (16 November 2026) that removing a
    fallback outranks avoiding restructuring, so the whole route and home are being removed in verified, committed steps,
    together with rebinding the 37 tests above.
  - Approximate figure axis ticks ("about 9", "approx. 9", "~9", "ca. 9") calibrate the axis at their printed value
    (`approximate_point=True` on the a105 shared number reader, used only by the tick reader); bounded ticks stay refused.
    `test_literature_controlled_response_v3_figure_refusals.py`: 41 passed + 1 xfail → 45 passed.
- Retired: `retired.tsv` = the 102 baseline retirements plus every test deleted during the purge (deleted whole files
  expanded into their test functions from the last commit that had them; parametrized cases count once), plus the two
  tick tests replaced by the owner decision in `f4a7e9788`.
- Dangling names: `dangling_names.tsv` (static scan); compared with the pre-reconciliation list, none were introduced;
  the 11 rows absent from that list are in `tools/` and were already broken at `a0d9f1666`.
