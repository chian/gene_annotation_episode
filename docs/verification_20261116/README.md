# Whole-tree verification after removing backward-facing code and code self-fingerprinting (16 November 2026)

Tree verified: commit `ce30170dd` (branch `first-full-draft-2026-11-10`).

- `home_summary.tsv`: one row per episode home (593) plus top-level `tests/`: test files, tests, passed, failed,
  errors, skipped, retired tests, modules, lines, identical copies, guard sites, modules failing import.
  Built by `tools/summarize_homes.py` from the run below.
- Collection: `pytest --collect-only` over `gene_annotation_episode` and `tests`: 50,582 tests, 0 collection errors.
- Imports: `tools/verify_episode_homes.py`, every home in its own interpreter, leaves first: 593 homes, 0 failures (`homes.json`).
- Test run: `tools/run_tests_by_home.py --per-file`, 4 shards, each through `tools/one_workflow.sh` under `eatmydata`,
  isolated HOME and blocked proxy; 1,634 files (all except `tests/test_bvbrc_proteome_host_integration.py`).
  Per-file results: `results_per_file.tsv`; failing tests with messages: `failing_tests.tsv`.
- Failures: every failing file (205) is named in a triage report (`docs/test_failure_triage_20261114/`) or a purge
  report (`docs/purge_20261115/`) that records its cause: `failing_files_and_cause_reports.tsv`. Compared per file with the
  latest measured result of each file during the purge, no file has fewer passes or more failures; 32 have more passes.
- Retired: `retired.tsv` = the 102 baseline retirements plus every test deleted during the purge (deleted whole files
  expanded into their test functions from the last commit that had them; parametrized cases count once).
- Dangling names: `dangling_names.tsv` (static scan); compared with the pre-reconciliation list, none were introduced;
  the 11 rows absent from that list are in `tools/` and were already broken at `a0d9f1666`.
