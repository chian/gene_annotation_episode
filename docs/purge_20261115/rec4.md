# rec4: reconciliation of a104, a105, a106, a107, a108, a110 (15 November 2026)

Area: the six arms under `gene_annotation_episode/episodic_workflow/root/` (`R/` below). Nothing outside them was
edited except two appended rows in `handoffs.tsv`. No sub-agents. Scratch: `<scratchpad>/rec4/` (edit scripts
`lifecycle_runtime.pl`, `from_child.pl`, `versions.pl`, `migrations.pl`, `slot_alias.pl`, `support_form.pl`,
`head_task.pl`; gate `driver.sh`, `cmp.sh`, `results.tsv`, `before.tsv`, `dangling_after.tsv`).

## Read this first

1. **Not done: the controlled-response v1/v2 readers (task 4, second half).** Nothing was changed there. Reason,
   from reading `R/a105/library/literature_controlled_response_{inputs,v2_inputs,v3_inputs,v3_population}.py`:
   - v3 is defined as v2 plus fields, in code. `v3_inputs.py` imports the v2 module and builds its own argument and
     extraction schemas from `v2.controlled_response_v2_arguments_schema()`, `v2._extraction_schema()` (2 uses),
     `v2._sheet_schema()`, `v2.embed` (5 uses), and validates with `v2._graph_request`, `v2._validate_graph`,
     `v2._validate_measurement`, `v2.graph_reader`. So the "v2 module" cannot go; only its two entry points
     (`read_controlled_response_v2_inputs`, `validate_controlled_response_v2_extraction`) and what only they reach.
   - The v1/v2/v3 choice is a runtime attribute (`SourceContext._profile`, `inputs.py:1375`) branched at 36 lines of
     the 2,449-line shared module, inside functions v3 calls (`finish_controlled_response_arm`,
     `finish_controlled_response_inputs`, `_covariance(owner_profile=...)`, `validate_controlled_response_saved_science`).
     Removing v1 and v2 means collapsing each branch to its v3 side, then deleting what becomes unreachable. That is a
     reachability job over four modules, in five differently formatted copies (a105 `library/` and its
     `source_evidence_examination/tools` copy, a104, a106, a108 `retained_input_authority`).
   - The v3 tests do not have their own inputs: `tests/test_literature_controlled_response_v3_inputs.py:11` is
     `class Fixture(V2Fixture)` and sets `version='controlled_response_source_selection_v3'` on the v2 selection read
     from `fixtures/retained_reference/a105_controlled_full_source_design_069/CONSTRUCTED_SOURCE_CASES_001.json`.
     Rebuilding it "not through v2" means rewriting those 14 stored selections in v3 form.
   v3 can be separated without changing what it computes (it never calls the two v1/v2 readers), but not by
   deleting functions: it needs the branch collapse above, checked against the 9 `*_v3*` test files. Only a105 has
   tests for this family (17 files); a104, a106 and a108 have none, so their copies would be changed unverified.
2. **The slot alias had a live user the completeness check missed.** Three a106 fixtures froze the unpublished
   working copy `research/slotted_process_library` (its index declares `annotation_distinction`, count 0, and no
   `evidence_axis`), which was only accepted through the alias. With the alias gone 129 tests in 10 a106 files
   errored (`scientific_process_source_index_invalid`). I pointed the three fixtures at the publication
   `publications/2026-10-24-001`, as the other fixtures in a105, a106 and a108 already do. Result in the gate below.
3. **A resume path in a106 was broken before I started and is fixed**: `R/a106/runtime.py` `load` passed
   `episode_branch_lifecycle=episode_branch_lifecycle` with no such local (NameError on every resume).
4. **The support-entry form is removed, the module is not.** `scientific_support_metadata.py` also holds the
   annotation-route description that `scientific_process/internal_summary.py:26` computes for `evidence_axis`
   entries (`support_observation_kinds`, `annotation_policy_routes`, `ROUTES_VERSION`). Those stay.

## What was changed, by task

### 1. Non-owned branch lifecycle (class 1)
- `runtime.py` of a105, a106, a108: 14 sites each cut to the owned side (`_stop_end_async`, `recover_commissions`,
  `settle_unclaimed_child_failures`, `pending_delivery`, `defer_failed_delivery=True`, the `pending_handles`
  meaning, `admitted_report`, `credit`, `report` (the whole non-owned admission body, 12 to 14 lines), `owned`,
  `TimedChildUnit(...)`, `elif pending is not None`, `old['state'] == 'active'`). a104, a107, a110:
  `defer_failed_delivery=True`. All six `load` functions pass the constant; none keeps a local.
- 24 `from_child_*.py` (a105 6, a106 12, a108 6): `owned` removed, `admit_unowned_return` deleted (11 to 14 lines
  each) with its entries in the bound-function name lists.
- Owner tuples lose the non-owned member: `child_message_owners.py` (a105, a106, a108),
  `a106/annotation_improvement/episode.py`, `a106/scientific_process/child_message_owners.py` (4-tuple to 3-tuple;
  `a106/report_receiving.py:24` index 3 to 2), `a106/scientific_process/incoming_message_owners.py` (returns the
  one function; `a106/runtime.py` calls it directly).
- Test stubs: `episode_branch_lifecycle=None` and the two `*_version = None` attributes removed from
  `a107/tests/launch_connected.py`, `a110/tests/launch_connected.py`, `a107/tests/literature_task_checks.py`.
- Kept: `Workflow.__init__` parameter with its refusal and `independent_execution.py:4xx` refusal of saved settings
  without the owned lifecycle (same as the shared root).

### 2. Older run settings, switches, table upgrades (classes 1 and 2)
- a107, a110: `wait_inputs_version` / `completed_action_inputs_version` reads removed at 9 files
  (`decision_waiting.py` x2, `continuation.py`, `yield_estimator.py`, `task_outcomes.py`, `action.py`,
  `library/decision_source_outcomes.py`, `episode_report_acquisition.py` x2); `pending_work_after_action` is written
  unconditionally. Constructor parameters and their single-value checks kept, as in the shared root.
- `a104/runtime.py`: the `'legacy_grouped_v1'` default is gone (missing setting reaches the constructor's refusal).
- `legacy=` switches: `_locator(..., legacy=True)` in a107 and a110 `infernal_search_contracts.py` (8 sites) and the
  unused `legacy=False` parameter of a105 `intervention_population_schema`. See "live despite its name".
- `binding_path is None` at `a105/episode_binding_graph.py:166`: already gone when I started.
- Table upgrades removed: `method_loop/durable.py` `ALTER TABLE commissions ADD COLUMN failure` (a104, a105, a106,
  a107, a110; the `CREATE TABLE` declares the column); `episode_receipts.py` `received_report_prefix` upgrade (a105,
  a106) and, in all six, a NULL prefix is now refused (`episode_receipts_not_bound`; `bind` always writes it), the
  shared-root form; `shared_information.py` missing-`state`-column tolerance (a105, a106, a107, a108, a110).

### 3. Dangling names
`rec1_dangling.tsv` has 68 rows in these arms. Scan rerun after my edits (run `claude_rec4_016`,
`rec4/dangling_after.tsv`): 63 rows.
- Fixed (2): `retained_read=True` at `a108/library/retained_input_authority/native_protein_structure_acquisition.py:81`
  and `protein_structure_result_receipts.py:354` (the only rows caused by the purge).
- Deleted (3 rows): `a107/tests/fixtures/rna_structure_core_354/` (see deleted-tests file).
- False positives (52: a104 36, a106 16): the functions are rebound to the axis `runtime` namespace by
  `library/live_runtime_functions.bind_functions`, so `from .x import y` inside them resolves from the axis root,
  where every one of the 52 modules exists (checked by path). Read, and exercised by the passing per-home tests.
- Left, all present at a0d9f1666, each needs code brought into the arm (a placement decision, not an import path):
  `a106/library/literature_kinetic_model_render.py:43` (`_kinetic_received`; defined only in a104, a105 and
  `R/library/literature_component_value_display.py`); `a107/a107_genomic_detection_hpc.py:57` (`a103_hpc.SOURCES`);
  `a107/flux_balance_request_binding.py:176` (`flux_balance_role_paths`; a110 has it);
  `a107/independent_execution.py:172` (`episode_bindings.native_job_event_configuration`; a104 and the shared root
  have it); `a107/library/primer_placement_result_contracts.py:135` (`molecular_sequence_fact_sources`);
  `a108/library/retained_input_authority/genomic_overlap_result_receipts.py:220` (`a108.native_file_capture`; no
  `capture_native_file` anywhere in a108); `a110/literature_rate_domains.py:201,254,259,266,277`
  (`literature_rate_storage`, `literature_rate_source_render`; not in a110).

### 4. Modules with no product caller
- a106: `library/literature_publisher_binding.py` (103 lines) deleted; `episode_binding_graph.py` reduced to
  `BindingPathResolver` (160 to 70 lines, now byte-identical to a105's); `tests/test_private_publisher_binding.py`
  deleted (6 tests). No other arm has `snapshot_graph` / `SavedBindingGraph`.
- Controlled-response v1/v2 readers: not done (item 1 above).

### 5. `LEGACY_EVIDENCE_SLOT` and the support-entry form (classes 1 and 2), all six arms
- Alias: `LEGACY_EVIDENCE_SLOT`, `ALL_SLOTS`, `canonical_slot` and every use (`scientific_process_records.py`,
  `scientific_process_library.py` index check, entry check, tool schema, search filter and the `process.search`
  argument rewrite, `scientific_process_reports.py`); two-name acceptance in `composition_information.py`,
  `scientific_process/configuration.py`, and the selection schema (`scientific_assignment_contracts.py` /
  `scientific_contracts.py`: `_EVIDENCE_AXIS` is built for `evidence_axis` only).
- Entry form `scientific_support_entry_v1`: `SUPPORT_ENTRY_VERSION`, `validate_support_entry`, three TypedDicts,
  `_OPERAND_SCHEMA`, `_ENTRY_SCHEMA` and helpers removed from `scientific_support_metadata.py` (179 to 76 lines);
  `scientific_process_library._validate_entry` refuses an unknown `entry_version`; `from_parent._selection` accepts
  only the instruction and evidence-axis entry versions; `episode_services.execute_scientific_library` (and the
  a105, a108 `scientific_process/library_services.py` copies) no longer adds routes for a support entry;
  `internal_summary.py` raises instead of projecting a `support` field; the "Assigned scientific support and its
  operands" prompt section is gone (`receiver_prompt.py`, a107 `rna_structure_comparison_receiver_prompt.py`).
- Tests: `a104/scientific_process/tests/test_head_task.py`, case `legacy` deleted, case `mixed` builds its plain
  `evidence_axis` entry directly.
- Same sites elsewhere, not edited (27 files, all in a101, a102, a103; none left in the shared root, the top
  package or `tests/`), per axis: `scientific_process_records.py` 8 lines, `scientific_process_library.py` 14,
  `scientific_process_reports.py` 3, `composition_information.py` 1, `scientific_process/configuration.py` 1 (a101,
  a103; a102 has `scientific_process/episode.py` 1), `scientific_process/from_parent.py` 3,
  `scientific_process/scientific_contracts.py` 3 (a103: `contracts.py`), `episode_services.py` 2,
  `scientific_support_metadata.py` 9. Row written to `handoffs.tsv`.
- Left in place and now always true: guards `'received_report_prefix' in manifest` in the
  `retained_input_authority` return modules (the shared root kept its 17 too).

### 6. "20 GiB RAM" sentences
None in these arms. `a110/a110_fba_hpc.py:146` left as instructed. `a110/tests/support/flux_balance/prepare_software.py:199`
still expects 21474836480 in a fake worker's request; not examined.

## Live despite its name
- Infernal locator without `kind`: `a107/infernal_search_inputs.py:105,223` (the current tblout reader) writes
  `{artifact_id, artifact_index, line}`. The `legacy=True` switch was passed by all three callers, so it was a
  constant; the parameter is gone and `kind` defaults to `tblout`, the form the shared root already has.
- `a104/homology_jobs.py:129` `ALTER TABLE orders ADD COLUMN search_mode`: runs when a new registry is created with
  `search_modes`, an optional current case setting (`gene_annotation_episode/case_execution.py:196,248`). Kept.
- `support_observation_kinds`, `annotation_policy_routes` (see item 4 at the top).

## Gate
By running (launcher, slot `rec4`, runs `runs/claude_rec4_001`..`720`; per-file table
`runs/claude_inputs/purge/rec4_gate_results.tsv`):
- Import check over every product module of each arm, after the last product edit: `{}` six times (runs 010 to
  015: a104 3,900 modules, a105 1,289, a106 1,537, a107 2,795, a108 925, a110 2,453).
- `pytest --collect-only` per arm (runs 101 to 106): 14,082 tests collected, 0 errors (a104 2,107, a105 5,914,
  a106 1,912, a107 2,161, a108 529, a110 1,459).
- Every test file in the six arms, one launcher run per file (578 files, runs 107 to 684; the 10 a106 files that
  use the corrected fixtures rerun as 701 to 710): 13,863 passed, 185 failed, 0 errors.

  | arm | files | passed | failed | failing files |
  |---|---|---|---|---|
  | a104 | 87 | 2,041 | 66 | 1 (`tests/proteome_partner/test_proteome_saved_host.py`, 0 passed / 66 failed before the purge too) |
  | a105 | 181 | 5,859 | 55 | 31 (same totals as pa105's final gate) |
  | a106 | 86 | 1,869 | 9 | 4 |
  | a107 | 93 | 2,129 | 32 | 9 (pa107's own final table had 86 failed; no file is worse than in it) |
  | a108 | 36 | 526 | 3 | 1 |
  | a110 | 95 | 1,439 | 20 | 8 |

  Comparison (`rec4/cmp.sh`): no file has more failed plus errors than its latest row in the pre-purge tables
  (`runs/claude_tests_final_*`), and every failing file failed there with the same failed count. I have no
  per-test table from just before my edits, so a test that an earlier agent fixed and I broke inside an already
  failing file would not show; the a105 and a107 comparisons with those agents' final gates rule that out there.
- `R/tests/test_private_binding_identity.py` (not edited): 70 passed, 2 failed, both `[a103]`
  (`a103/runtime.py:3871`, `legacy_parent_for_path`); every a104, a105, a106, a107, a108, a110 case passes
  (runs 004 and 720; 67 passed / 5 failed before).
- `a104/scientific_process/tests/test_head_task.py` after its edit: 67 passed (68 before, one case deleted).
- Pass to fail found and closed during the gate: the 129 a106 errors of item 2 at the top (10 files; all pass now,
  223 tests).
- Dangling-name scan over the six arms (run 016): 63 rows, described in task 3.

By reading only: that no product code calls `snapshot_graph` / `SavedBindingGraph` / the publisher binding; that
the kind-less Infernal locator is what the current tblout reader writes; that `EpisodeReceipts.bind` always writes
the report prefix; that `commissions.failure` and `received_report_prefix` are in the `CREATE TABLE` statements;
that neither `instruction_view` nor `evidence_axis_instruction_view` produces a `support` field (grep); the 52
dangling false positives (by path, not by executing each import); everything in item 1 at the top. Not exercised
by any test I know of: the a106 `load` fix, the a105/a106/a108 owner-tuple change beyond what the per-home tests
reach, and resume of a saved run in any arm (no whole-workflow run was made).


## Counts
Files edited 143 (a104 15, a105 24, a106 36, a107 22, a108 24, a110 22), of which 7 are test files or test helpers;
files deleted 4 (1 product module, 1 test file, 2 fixture files); tests deleted 6 functions and 1 parametrized case
(`rec4_deleted_tests.tsv`); 3 fixtures repointed. Sites are counted per task in the sections above (classes 1 and 2 for tasks 1, 2 and 5; classes 5 and 6 for
task 4); I did not tally them again by class. Lines removed were not measured separately from the earlier
uncommitted work in the same files.


## Handoff rows
Written: to rec1 (its a105/a106/a108 lifecycle row is applied); to pa101, pa102, pa103 (slot alias and support-entry
form, with what to keep). Applied: rec1's row above. The 45 older rows addressed to these arms' agents were not
re-checked.
