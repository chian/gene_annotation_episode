# triage_e: a104/tests (retained authority tests, native receipts, evolutionary episode, 2 errors)

Slot `triage_e`. Nothing under the repository was edited except this file. Modified test copies used for
checking proposed fixes live outside the repository (scratchpad) and were run only through the launcher.

Paths below are relative to `gene_annotation_episode/episodic_workflow/root/` unless they start with
`gene_annotation_episode/`, `tests/`, `tools/` or `runs/`.

## Summary table

| # | Group | Count | Classification | Cause (evidence) | Minimal fix | Changes scientific behaviour? |
|---|-------|-------|----------------|------------------|-------------|-------------------------------|
| 1 | `a104/tests/test_a104_retained_fluorescence_authority.py::test_actual_fluorescence_readers_keep_saved_grants_denials_and_reopen` | 60 cases (1 run by me; 31 of 31 finished so far in the other slot are FAILED; the cause does not depend on home or operation, see section 1) | stale_test (wrong expectation; it has never matched any recorded version of the validator) | Test line 110 expects `owner._versions([{sheet}], scope, context=receiving) is None` for a context that was granted the saved sheet. The validator `a104/library/execution_input_versions.py:166-170` admits an artifact outside ordinary Store scope only when it is a selected file of an explicit native assignment; otherwise it raises `execution_input_outside_assigned_scope`. The sheet artifact is attributed by no record in either fixture database (sqlite query, section 1), and the test passes no assignment. The pre-reorganisation tests assert exactly this refusal (`root/tests/test_fluorescence_episode_routing.py`, last assertion of the commission test: `_versions(f.versions, f.scope, context=f.root)` must raise `outside_assigned_scope`). | In the test, lines 110-111 and 142-146: expect `ValueError` matching `execution_input_outside_assigned_scope` for the granted contexts (keep lines 118-120 and 147-149, the denial for the root). Product unchanged. Verified for one case: a scratch copy with only this change passed (run 13). | No, if the test is corrected. Yes, if instead the validator were changed to admit granted-but-unselected sheets: that would change which inputs an execution accepts, so it needs the owner's decision. |
| 2 | `a104/tests/test_a104_results_native_receipts.py` (both tests, all parameters) | 28 | test_wiring (three defects in the test's own controlled ports; no product change) | (a) line 35: the fake `read_target` asserts `scope == frame.scope`, but product passes the context's frozen scope (`mappingproxy` with tuples) as all of its 40+ `read_target` callers do, e.g. `a104/hpc_work_planning/execution_result_acquisition/result_publication.py:17,27`; (b) lines 79-80, 93-94, 114-115: outcome updates call `journal.save('runtime_actions', ...)` without `action`; SQLite checks `action TEXT NOT NULL` (`a104/episode_journal.py:53`) before the upsert clause, so the insert fails; product always re-supplies `action` (`a104/runtime.py:998,1000`); (c) line 106 rewrites the receipt without the trailing newline that `_immutable` writes, so `_read` (`a104/practical_execution_state.py:40-41`) raises `practical_record_bytes_changed` before the expected `execution_result_original_receipt_conflict`. | line 35: compare `plain(scope) == frame.scope`; lines 80, 94, 115: add `'action': own_module('runtime')._json(case.selected)`; line 106: `path.write_text(contracts.canonical(body) + '\n')`. Verified: a scratch copy with exactly these edits gives 28 passed (run 05). | No. Test doubles and test bookkeeping only. |
| 2b | `a104/tests/test_a104_results_progress.py` (not in my list; same fixture) | 12 (in `runs/claude_tests_leaf_up_20261114_03_a104_2`) | test_wiring | Imports the `native_receipt` fixture of group 2, fails on the same line-35 assertion (same message in that run's `logs/0017.log`). It has the same action-less saves at its lines 49-50 and 61-62. | Fix 2(a) repairs the first failure; its own two saves need `action` as in 2(b). Not run by me after the fix. | No. |
| 3 | `a104/tests/test_a104_evolutionary_episode.py::test_exact_request_has_one_real_target_and_no_local_scientific_execution` | 1 | product_defect (import mis-pointed by the automated re-pointing, commit 3dd58552a) | `gene_annotation_episode/hpc_campaign.py:40` imports `resource_identity` from `root/library/execution_guidance.py`, which defines only `recipe`. The function is in `root/library/execution_resource_identity.py:3`; sibling modules already import it from there (`gene_annotation_episode/hpc_history.py:9`, `gene_annotation_episode/hpc_scientific_commission.py:8`). | `gene_annotation_episode/hpc_campaign.py:40`: `from .episodic_workflow.root.library.execution_resource_identity import resource_identity`. Verified by simulation: with that function bound to the name the statement looks up, the test passes (run 06); it also passed in run 12 after someone else made this exact edit in the working tree at 10:31 (section 6). | No. Import path only; same function body as before the move. Note this affects every caller of `validate_commission` with an `execution_profile`, not only this test. |
| 4 | `...::test_native_tree_claim_requires_actual_received_execution` | 1 | stale_test | The test builds a legacy report from `initial_report()`, which returns `{}` (`a104/a104_investigation.py:78-79`); the legacy schema (`legacy_report_schema`, lines 48-69, all properties required) rejects it with "'function_scope' is a required property" before the check under test (lines 120-123) is reached. Same code and same test at 078b77668, so this predates the reorganisation. | Test lines 177-178: give the legacy report all its fields explicitly (`function_scope` and `history_interpretation` = `'not_assessed'`, `limitations`, `information_need_refs`, `hypothesis_refs`, `assessment_refs` = `[]`). Verified in the scratch copy (run 06): the expected `native_tree_statement_requires_received_original_execution` is then raised. | No. The product check is reached unchanged. |
| 5 | `...::test_received_dynamic_commission_uses_existing_hpc_owner_and_cannot_change_scope` | 1 | stale_test | Imports `gene_annotation_episode.hpc_episodes.HPCEpisodes`, deleted in dfe3e6091. The monolith was split into per-home owners: `a104/hpc_work_planning/episode.py:38` (`roles = ('hpc',)`) and `a104/hpc_work_planning/hpc_allocation_execution/episode.py:34` (`roles = ('hpc_execution',)`), same constructor signature. | Test line 350: import `HPCEpisode` from `a104.hpc_work_planning.episode`; line 374: prepare the `hpc_execution` assignment with an owner built from `a104.hpc_work_planning.hpc_allocation_execution.episode.HPCEpisode` (same arguments). Run 06 verified everything up to line 372 with the planning owner (it then fails at 374 with `unknown_hpc_role`, as expected for a planning-only owner); with the allocation-home owner at line 374 the test passes (run 12, section 3). | No. |
| 6 | `a104/tests/test_binding_context_owner.py` (`test_native_forwarding_preserves_instance_and_private_error`, `test_exact_cache_key_and_isinstance_remain_distinct`) | 2 errors | environment | Fixture `canonical_epoch` (lines 11-15) reads `os.environ['A104_CONTEXT_SOURCE_EPOCH']`; nothing in the repository sets it. In this tree `a104/episode_bindings.py:51` re-exports the root `BindingContext`, i.e. the `canonical` epoch. | Either export `A104_CONTEXT_SOURCE_EPOCH=canonical` in the test runner, or delete the fixture and the `original` branch (lines 61-64, 77) since the `original` source epoch no longer exists in this tree. Verified: `canonical` gives 13 passed, `original` gives 2 failed (run 07). | No. |

## 1. Fluorescence authority test: the failure

Run 01 (one case, `[execution_job_submission-perform_facs_cell_sorting]`, under cProfile, `-x`):
`runs/claude_triage_triage_e_01/stdout.log`.

```
test_a104_retained_fluorescence_authority.py:110
    assert owner._versions([{'reference': reference, 'version': None, 'content_sha256': None}],
        plain(receiving.scope), context=receiving) is None
a104/execution_job_submission/scientific_inputs.py:14: in _versions
a104/library/execution_input_versions.py:170: ValueError: execution_input_outside_assigned_scope
```

Everything before line 110 passed in that run: the three saved receipts re-read and compare equal, the sheet payload is
absent as expected, `authenticate_received_saved_sheet` returns the original episode, and the three access questions for
the first receiving context (`_fluorescence_reference_access`, `resolve_received_reference`, `resolve`) all return True.

Why line 110 cannot pass:

- `a104/library/execution_input_versions.py:138-170`: for each supplied version, a protected-reference host that
  answers `False` raises a denial; any other answer falls through to
  `owner.store.reference_subset([reference], scope)`. If that is empty, the reference must be in `selected_files`
  (filled only from `fluorescence_assignments` and the other `*_assignments` arguments), otherwise
  `execution_input_outside_assigned_scope`.
- `Store.reference_subset` (`a104/state.py:1787-1803`) accepts an artifact only if `_artifact_references`
  (lines 1756-1785) finds it attributed by a record, an input sequence, a material member or the problem.
  Read-only `sqlite3` query on both extracted fixture databases
  (`runs/claude_triage_triage_e_01/tmp/original049-fluorescence0/<operation>/state/state.sqlite3`): the artifact row
  `artifact_67d318098f0b...` exists, and 0 rows of `records`, `inputs` or `problem` mention it (each database has 5
  records: collection, material, parse_attempt, 2 sources).
- The test calls `_versions` with no assignment, and every a104 owner's `_versions` wrapper takes none
  (`a104/**/scientific_inputs.py:12-14`, `a104/**/request_validation.py:51-53`; all call the one library validator).
  So the outcome is the same for all 30 homes and both operations.
- The validator lines are identical to the pre-reorganisation `gene_annotation_episode/execution_input_versions.py`
  at 078b77668 (diff of lines 136-172: one import path differs). The test file and its fixture first appear in
  dfe3e6091; I found no record of it passing.
- The earlier tests assert the refusal: `root/tests/test_fluorescence_episode_routing.py` (last assertion of the
  commission test, also at 078b77668 `tests/test_fluorescence_episode_routing.py:225-226`) and
  `tests_parked/tests/test_fluorescence_prepared_resource_boundaries.py` (078b77668 lines 265-267).

Check of the proposed test correction (run 13): a scratch copy of the test in which only lines 110-111 and 142-146
expect `execution_input_outside_assigned_scope` passed for this case (1 passed in 759 s). So for this home and
operation those four expectations are the only mismatch; every other grant, denial and reopen assertion holds.
The other 59 cases were not run with the correction; that they behave the same is inferred from the shared validator
and the database query above.

Consequence for run time: a failing case stops at line 110 after about 160 s. A passing case runs the rest of the
test and took 759 s unprofiled. Sixty corrected cases would need about 12.7 hours of CPU, not the 2.8 hours planned
in `runs/claude_inputs/test_time_expectations_20261114.tsv`.

The protein counterpart passes its `_versions(...) is None` assertions because the protein sequence and sheet
artifacts are attributed by ordinary Store records; that is a difference in the saved data, not in the validator.

## 2. Where the time goes

Both profiles are of one case of home `execution_job_submission`, run with `python -m cProfile` through the
launcher. Profile files: `runs/claude_triage_triage_e_01/profile.out` (fluorescence, case stops at the line-110
failure) and `runs/claude_triage_triage_e_08/profile.out` (protein, case passes). Seconds below are profiled seconds;
the profiler inflates pure-Python call-heavy code more than C code, so shares are approximate.

In both files the time is in product code under `a104/library/`, not in the test helper, the fixture copy, digests
or SQLite. The repetition is avoidable in the sense that the same saved documents are re-validated or re-converted
hundreds to thousands of times inside one test; it is not inherent in the number of questions the test asks.

### 2a. Test helper and fixture cost (both files): negligible

| Item | Fluorescence (668 s total) | Protein (1512 s total) |
|------|----------------------------|-------------------------|
| `retained_native_disposable_store.open_store` (copy, snapshots, digests, seal checks) | 0.85 s, 2 calls | 2.19 s, 4 calls |
| of which `verify_unchanged` (sha256 of every pinned file) | 0.57 s | 1.58 s |
| of which `_snapshot` / `_read_snapshot` (whole-database reads) | 0.18 s (6 calls) / 0.11 s (3) | 0.32 s (12 calls) / 0.19 s (6) |
| archive unpack (module fixture) | 1.70 s | 0.38 s |
| transported control reads with per-read digest | 6.57 s, 393 reads | 3.49 s, 1016 reads |
| owner constructor (`actual_owner`) | 2.11 s, 1 call | 0.78 s, 2 calls |
| `a104/state.py` (all Store methods) | under 1 s | under 2 s |

The "about 800 s for the first store copy" in the planning file is not there: the first copy, its comparison with
the original and all later snapshot checks together cost 2.2 s in the protein case. The databases are small in rows
(protein: 13 episodes, 20 actions, 16 records; 50 MB because episode requests total 4.5 MB of JSON and model-call rows
are large). In the unprofiled shard run the first four protein cases finished in 51 minutes (about 765 s each), so
any first-case penalty is much smaller than 800 s.

### 2b. Fluorescence: one software-closure validator, called 1312 times

Top functions by cumulative time (profiled seconds, calls):

| cum s | calls | function |
|-------|-------|----------|
| 663.5 | 1 | the test function |
| 644.1 | 33 (18 non-recursive) | `fluorescence_result_receipts.py:421 read_completed` |
| 599.2 | 33 | `fluorescence_result_receipts.py:344 validate` |
| 505.3 | 25 | `fluorescence_result_receipts.py:443 completed_receipts` |
| 423.7 | 4 | `fluorescence_returns.py:241 authenticate_received_saved_sheet` |
| 411.1 | 1312 | `native_fluorescence_contracts.py:120 validate_fluorescence_software` |
| 326.8 | 839 | `native_fluorescence_contracts.py:283 validate_fluorescence_job` |
| 322.3 | 13 | `native_fluorescence_results.py:60 own_fact_groups` |
| 277.8 | 1,256,896 | generator at `native_fluorescence_contracts.py:138` |
| 263.5 | 1,303,310 | `pathlib.is_relative_to` |
| 147.8 | 473 | `native_fluorescence_contracts.py:314 fluorescence_environment` |
| 111.9 | 44.5 million (39,188 top-level) | `copy.deepcopy` |
| 87.5 | 2,118,880 | `native_fluorescence_contracts.py:114 _pin` |

What happens: the three saved receipts are fully re-authenticated 33 times (3 by the test directly, 15 through
`completed_receipts`, 5 through `owns_reference`, the rest nested). Each receipt authentication validates the same
saved software closure (about 1615 pinned files) about 40 times, because `validate_fluorescence_job` (839 calls) and
`fluorescence_environment` (473 calls) each validate it from scratch and return a deep copy, and their callers
(`requested_job_from_fluorescence` 443, `fluorescence_output_files` 270, `validate_fluorescence_selector` 126)
re-validate the whole job to read part of it. Inside one validation, line 138 tests each runtime file against
`python_home/lib` with `PurePosixPath(...).is_relative_to(...)` until the first match, about 957 files per call.

Minimal change (not made): `a104/library/native_fluorescence_contracts.py:138` (lines 137 and 139 use the same form but are cheap here: 15 and 1 checks per call):
compare the already-validated path strings by prefix (`path == root or path.startswith(root + '/')`) instead of
building a `PurePosixPath` per file. `path_value` (lines 99-103) has already required each string to be an absolute,
normalised POSIX path with no `..`, so the answer is identical. Attributed saving: 259 s of 668 profiled (39%).
Plumbing only; no change to what is accepted.

The larger remaining cost (1312 validations of one closure, 2.1 million `_pin` checks, the deep copies) comes from
validating at every layer. Reducing the call count means changing which layers validate; that is a design change
across `native_fluorescence_contracts.py` and `fluorescence_result_receipts.py`, not a one-line fix.

### 2c. Protein: whole request documents converted and compared again and again

Top functions by cumulative time (profiled seconds, calls):

| cum s | calls | function |
|-------|-------|----------|
| 1513.3 | 1 | the test function |
| 1473.4 | 1313 (148 non-recursive) | `native_protein_structure_returns.py:42` (the `_boundary` wrapper around every public method) |
| 1310.6 | 182 | `native_protein_structure_returns.py:306 _deliveries` |
| 1089.0 | 1207 | `native_protein_structure_returns.py:137 authenticate` |
| 993.3 | 42 | `native_protein_structure_returns.py:559 resolve_received` (from 44 `_protein_reference_access` calls) |
| 629.5 | 365 million (136,393 top-level) | `a104/communication.py:30 plain` |
| 555.4 | 102 | `protein_structure_result_receipts.py:781 completed_receipts` |
| 553.3 | 478 | `a104/episode_return_records.py:96 context` |
| 544.1 | 127 | `protein_structure_result_receipts.py:778 read_completed` |
| 472.2 | 924 million | `isinstance` |
| 411.8 | 3977 | `a104/episode_return_records.py:81 authenticate` |
| 368.1 | 2748 | `native_protein_structure_returns.py:105 _commission` |
| 344.8 | 164 million (36,355 top-level) | `a104/episode_return_records.py:44 equal` (inside `_same`) |
| 318.2 | 2746 | `native_protein_structure_returns.py:159 _saved_context` |
| 221.2 | 3224 | `root/receiving_context.py:40 BindingContext.__post_init__` |
| 182.6 | 4015 | `native_protein_structure_returns.py:100 _manifest` |
| 125.9 | 145,752 | `jsonschema` validation |

What happens: the test asks about 60 authority questions (14 direct reader calls, 14 `_protein_reference_access`,
10 each of `resolve`, `resolve_received_reference`, `_versions`, plus 2 `authenticate_saved_case`), about 25 s each.
Each question re-derives everything from saved rows: 3 receipts are fully authenticated 127 times, 13 saved episodes
are loaded 478 + 2746 times, and a `BindingContext` is built 3224 times. Every build parses a request (345 KB of
JSON on average), round-trips it through `json.dumps/loads` and freezes it; every `authenticate`, `_commission` and
`_manifest` then converts the whole frozen request back with `plain(...)` and deep-compares it with a freshly parsed
copy. `plain` alone is 630 s (42%), the deep comparison 345 s, context construction 221 s.

Minimal change (not made): `a104/library/native_protein_structure_returns.py:102` (`_manifest`) converts the whole
request to read one key: `plain(context.request)['message'].get('knowledge_inheritance')`. Converting only that
value, `plain(context.request['message'].get('knowledge_inheritance'))`, gives the same result. Attributed saving:
179 s of 1512 profiled (12%). Plumbing only.

Nothing comparably small removes the rest. The next step would be to build and authenticate each saved ancestor
once per public call instead of once per use (`_saved_context`, 2746 calls for at most 13 episodes). The docstring of
`_same` (`a104/episode_return_records.py:37-43`) says no successful authority verdicts are retained, so that reuse
conflicts with a stated rule and needs the owner's decision; I am not proposing it as a plumbing fix.

Inherent part: the test repeats the same questions for 30 owner homes (60 cases for fluorescence) although the
readers are shared `a104/library` code. That is the test's coverage choice, not waste in the helper.

## 3. Checks of proposed fixes (scratch copies outside the repository)

- Native receipts (group 2): scratch copy with fix (a) only: 28 failed on the next defect (run 03); with (a)+(b):
  24 passed, 4 failed on (c) (run 04); with (a)+(b)+(c): 28 passed (run 05).
- Evolutionary (groups 3-5): scratch copy with the three test edits, plus a scratch `conftest.py` that binds
  `execution_resource_identity.resource_identity` onto `root.library.execution_guidance` to stand in for the
  one-line product import repair. Run 06: tests 3 and 4 pass, test 5 passes up to line 372 then `unknown_hpc_role`
  at line 374. Run 12 with the allocation-home owner at line 374: 22 passed, 1 failed. The one failure is
  `test_only_particular_native_assay_criteria_qualify_reference_activity`, which imports the sibling module
  `test_literature_assay_grading` by bare name; that resolves through `pythonpath` in `pyproject.toml` in the real
  runner (it passed in `runs/claude_tests_leaf_up_20261114_03_a104_0`) and not from the scratch location.
- Binding context (group 6): the unmodified test file with the variable set (run 07).
- Fluorescence (group 1): run 13, described in section 1.

## 4. Launcher runs: expected and actual time

| Run directory (`runs/`) | What | Expected (basis) | Actual |
|-------------------------|------|------------------|--------|
| `claude_triage_triage_e_01` | fluorescence case 1 under cProfile, `-x` | 6-9 min (other slot: 5 cases in 17.5 min, times 1.5-2.5 for the profiler) | 11 min 7 s, failed at line 110 |
| `claude_triage_triage_e_02` | print profile statistics | under 10 s | 5 s |
| `claude_triage_triage_e_03`, `_04`, `_05` | scratch native receipts, three iterations | about 10 s each (original file 2.9 s) | 3-4 s each |
| `claude_triage_triage_e_06` | scratch evolutionary copy | about 8 s (original file 3.1 s) | 13 s |
| `claude_triage_triage_e_07_canonical`, `_07_original` | binding context test with the variable set | about 5 s each | about 1 s each |
| `claude_triage_triage_e_08` | protein case 1 under cProfile, `-x` | 50-80 min (25 min unprofiled for a first case per the planning file, times the 3.2 seen in run 01) | 25 min 16 s, passed |
| `claude_triage_triage_e_09`, `_10`, `_11` | print profile statistics | under 10 s each | 1-2 s each |
| `claude_triage_triage_e_12` | scratch evolutionary copy, second iteration | about 15 s | 10 s |
| `claude_triage_triage_e_13` | scratch fluorescence variant, one case, unprofiled | 5-8 min (158 s to the failure point, assumed to double) | 12 min 39 s, passed |

The two long estimates were wrong in opposite directions: the protein profile ran at about 2 times unprofiled speed,
not 3.2, and a passing fluorescence case does nearly five times the work of a failing one, not twice.

## 5. Verified versus inferred

Verified by running: the fluorescence traceback for one case; both profiles; the fix sets for groups 2, 4 and 5 and
the simulated repair for group 3; the environment variable for group 6; the corrected fluorescence expectations for
one case.

Verified by reading or querying: validator code and its history back to 078b77668; absence of any record
attributing the sheet artifact in both fixture databases; `Journal.save`, `_read` and `BindingContext` behaviour;
the deleted `hpc_episodes` module and its per-home successors.

Inferred, not run: that the other 59 fluorescence cases fail for the same reason and pass with the same correction;
that `test_a104_results_progress.py` passes once its own two saves also carry `action`; the unprofiled size of the
two proposed speed-ups (only profiled shares were measured).

## 6. Working tree changed by others while I worked

I edited nothing under the repository except this file. `git status` at the end shows 441 modified files that were
not modified when I started, from other work in progress. Two touch this cluster:

- `gene_annotation_episode/hpc_campaign.py` was changed at 10:31:11 to exactly the import proposed for group 3
  (`from .episodic_workflow.root.library.execution_resource_identity import resource_identity`). Run 06 (10:03)
  therefore tested the simulated repair, and run 12 (10:33) ran against the real edit; group 3's test passed in both.
- `a104/bvbrc_phylogeny_tool_info.py` changed at 10:09 (one import path), during the protein profile. It does not affect the
  profiled time: the edit only changes where one constant is imported from.

The junit results I diagnosed (`runs/claude_tests_leaf_up_20261114_03_a104_0`) predate those edits.

## 7. Test-side fixes applied on disk (coordinator instruction, after the triage above)

`git status --short` was empty for each of the three files immediately before its first edit. Test files only; no
product code; nothing staged or committed. Items 1 (fluorescence expectation) and 6 (environment variable) were left
as they are, and no speed-up was applied.

```
 .../root/a104/tests/test_a104_evolutionary_episode.py   | 17 +++++++++++++----
 .../a104/tests/test_a104_results_native_receipts.py     | 11 +++++++++--
 .../root/a104/tests/test_a104_results_progress.py       |  3 ++-
 3 files changed, 24 insertions(+), 7 deletions(-)
```

What changed:

- `test_a104_results_native_receipts.py`: import `plain`; the controlled `read_target` compares `plain(scope)`;
  the three outcome saves carry `action`; the rewritten receipt ends with a newline.
- `test_a104_results_progress.py`: its two outcome saves carry `action`.
- `test_a104_evolutionary_episode.py`: the legacy report lists all its fields (and the now unused `initial_report`
  import is dropped); the dynamic-commission test imports the planning-home `HPCEpisode` and prepares the
  `hpc_execution` assignment with the allocation-home `HPCEpisode`. Line 353 (`from hpc_helpers import ...`) is
  unchanged; it resolves through `pythonpath` in `pyproject.toml`.

Reruns, one launcher run per file, slot `triage_e`, empty home and blocked proxies:

| File | Before (passed / failed) | After (passed / failed) | Expected time | Actual | Run directory |
|------|--------------------------|-------------------------|---------------|--------|---------------|
| `test_a104_results_native_receipts.py` | 0 / 28 | 28 / 0 | about 10 s | 8 s | `runs/claude_triage_triage_e_16` |
| `test_a104_results_progress.py` | 0 / 12 | 12 / 0 | about 10 s | 6 s | `runs/claude_triage_triage_e_17` |
| `test_a104_evolutionary_episode.py` | 20 / 3 | 23 / 0 | about 20 s | 7 s | `runs/claude_triage_triage_e_18` |

The third evolutionary failure (item 3) is gone because someone else repaired `gene_annotation_episode/hpc_campaign.py:40`
at 10:31; I did not touch product code. Each rerun wrote `junit.xml` and a cProfile dump (`profile.out`) in its run
directory.

One deviation from the prescribed prefix: `tools/one_workflow.sh` refuses a run directory that already exists
(line 57, "A fresh run directory is required"), so `runs/<run>/home` cannot be created beforehand. I used an empty
sibling directory `runs/<run>_home` as `HOME`; it was still empty after each run. Everything else in the prefix is as given.

## 8. Reaches outside services

None found in this cluster.

- Dynamic evidence: I listed every socket, TLS, HTTP, child-process and home-directory function recorded in five
  cProfile dumps (runs 01 and 08 from before the rule, runs 16-18 under it; listings from runs 15 and 19). No
  `connect`, `getaddrinfo`, `urlopen`, `Popen`, `fork` or `exec` call appears in any of them. What does appear:
  module import of `socket`/`ssl`/`subprocess`/`http.client`; `socket.socketpair` from `asyncio.run` (a local
  self-pipe, runs 16-17); `sqlite3.connect`; `expanduser` called by pytest's junit plugin and by `sysconfig`.
- Limits of that evidence: the two retained-authority profiles cover one home each (`execution_job_submission`),
  and the fluorescence one stops at the line-110 failure. `test_binding_context_owner.py` was not profiled; it only
  builds `BindingContext` objects and reads one environment variable.
- By reading: 28 a104 product modules can start a process or open a connection (for example
  `hpc_work_planning/resource_discovery.py:23` runs the configured `ssh_argv`, `hpc_queue.py:190,196` runs ssh and
  fetches a URL, `a104_hpc_worker.py:107,118` downloads and runs native programs). None is called by the tests in this
  cluster: the results tests replace the three provider ports with test closures, and the evolutionary tests call
  only the constructor, `prepare_assignment`, `assignment_schema`, `state` and pure worker functions.
- My runs 01-13 predate the rule and ran without the empty home and proxy block.

Unrelated observation from that reading, not acted on: `hpc_work_planning/resource_discovery.py:23` passes
`timeout=90` to the ssh call and `hpc_queue.py:196` passes `timeout=20` to `urlopen`; AGENTS.md forbids elapsed-time
cutoffs in code.
