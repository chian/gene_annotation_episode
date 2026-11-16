# h5 — what backward-facing apparatus remains (completeness check, 15 November 2026)

Read-only. No repository file was edited. Paths: `R/` = `gene_annotation_episode/episodic_workflow/root/`.

## 1. What was measured and how

| | tree | when |
|---|---|---|
| before | commit a0d9f1666, extracted with `git archive` (pre-purge) | scan `runs/claude_h5_011` |
| now | working tree = checkpoint e5c5ff9b6 + 744 modified, 29 deleted, 1 untracked file | scan `runs/claude_h5_012`, started 21:16:03 |

a105 and a110 were still editing at 21:16, so their rows can be lower by now.

- Scope: `gene_annotation_episode/` and top-level `tests/`; `verification/`, `runs/`, `tests_parked/`, `__pycache__` excluded.
  "tests" = any path with a `tests/` component; everything else is "product".
- Files are grouped by sha256. A **site** is one line of one distinct file content; "copies" is the number of
  byte-identical files carrying it. Per-area counts are distinct sites present in that area.
- Classes are regular expressions over every line of every distinct `.py` file, plus path rules and (for the
  self-hashing table) a per-function AST pass. The scanner is
  `scratchpad/h5/scan.py`; reclassification against the area reports is `scratchpad/h5/post.py`
  (both under `/tmp/claude-1000/-home-chia-repos-gene-annotation-episode/6505138e-b5fa-4641-9b42-c1589dca8429/`).
  Both ran only through the launcher, slot `h5`.
- Verdicts: **B** clearly backward-facing; **S** an item the coordinator asked to be counted (verdict given per item
  in section 3); **O** needs the owner or needs reading; **C** clearly current.
- A name is **C** when I sampled it as current vocabulary, or when an area report in `runs/claude_inputs/purge/*.md`
  traced it to a current writer. I did not re-trace those; I took the reports' word and spot-read only the cases
  named in sections 3 to 5. A legacy/historical-named identifier is **B** only if no area report mentions it and it
  is not in a family I read as live; a bare word `legacy`/`historical` (local variable, dictionary key, prose) is **O**.
- "Reachable" means statically importable from `gene_annotation_episode.cli` (imports at any depth, including lazy
  ones, plus string constants naming a module). It over-states liveness: a reachable module can hold a dead branch.

Inventory (files total / distinct contents): product `.py` 27,697 / 13,679 before, 27,565 / 13,634 now; product
other files 2,016 / 1,566 before, 558 / 169 now; test `.py` 4,752 / 3,238 before, 2,012 / 1,790 now; test other
files 15,084 / 6,643 before, 3,621 / 2,007 now. No `*.source` file remains (339 before).

## 2. Result in one paragraph

The named apparatus is gone or nearly gone in most areas: digest tables and digest literals beside `.py` names
(1,650 product sites before, 0 now), `PRIOR_VERSION`/`LEGACY_VERSION` (76 to 0), `historical=`/`legacy=` switches
(192 to 9), saved source copies (0 left), 20 GiB policies (156 to 10, of which 9 are prose). What remains is
concentrated: acceptance of older run settings in **a101, a102 and a103** (and a short tail in a107 and a110), the
path-less parent lookup in **a103**, in-place database upgrades in every area, the ownership records in
a101/a102/a103 `library/`, and the self-hashing machinery, which is everywhere and mostly untouched.

## 3. The items asked for, per area (product code unless stated)

Per-area numbers are in the "Per area, verdict S" tables of section 9; every site is in `h5_sites.tsv`.

**(a) Acceptance of older run settings — B.**
- `wait_inputs_binding_v1`: 6 sites, a101 3 (`R/a101/runtime.py:1066,3716,3719`) and a102 3 (`R/a102/runtime.py:5384` and two more).
- Branches on `wait_inputs_version == 'wait_inputs_binding_v2'`: 123 sites / 113 files — a101 48, a102 33, a103 33,
  a110 5, a107 4. Zero in a104, a105, a106, a108 and the shared root, where the only remaining mention is the
  refusal of anything else (7 sites, counted as current).
- `completed_action_inputs_version is None` / `is not None` / `in {None, …}`: 126 sites / 116 files — a101 48,
  a103 38, a102 33, a110 4, a107 3. Example: `R/a101/runtime.py:1069` accepts `{None, 'completed_action_inputs_binding_v1'}`.
  Tests still pass `None` doubles at 35 sites (a103 14, a102 13, a101 5, a107 2, a110 1).
- `episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE` (an "owned" versus not-owned branch): 126 sites / 78 files —
  a101 31, a102 27, a106 21, a103 16, a105 14, a108 14, and 1 each in a104, a107, a110. The `!=` form (28 sites,
  4 per axis in a101/a102/a103/a105/a106/a108, 1 in the others) I did not read line by line: where it is followed by
  a raise it is the current requirement. **Needs reading in a105, a106, a108**, whose reports do not list it.
- `unproven_replay`: 45 sites, all in a101 (44 files: `R/a101/runtime.py:337,350`, 42 home `task.py` files,
  `R/a101/bvbrc_appservice_custody.py:165`). Every other area has removed it.
- `_legacy_episode_assignments`: 12 sites, a101 only (`R/a101/runtime.py:177,190,260`).
- `'legacy_grouped_v1'` progress-receipt order: `R/a101/runtime.py:1075,3733` and the default at `R/a104/runtime.py:3498`.
- `execution_status_v1`: 8 sites (a101 2, a102 2, a103 2, a108 1, top package 1). The reports say v1 and v2 are both
  written today; not re-traced, so **O**.
- Older estimator settings accepted and ignored: `window_size` / `subsample_size` "compatibility operands for saved
  caller definitions only", `R/a101..a104/numerical.py:65,74,75` (12 sites; the shared-root copy no longer has them).
- `supports_tool_info` "legacy snapshot" of the tool library: `R/a101/scientific_tool_library.py:235`,
  `R/a103/…:233`, `R/a108/…:236`.

**(b) `shared_local_resources_v1/_v2`, `PRIOR_VERSION`, `LEGACY_VERSION` — clean.** The two constants are gone (76
sites before). The 8 remaining literals are each axis's single `VERSION` (`local_resources.py:24`): `_v2` in
a101, a102, a103, a104, a106, a108; `_v1` in a105 and in the top-level package. No file accepts two. Whether a105
should differ from the others is an owner question, not a leftover.

**(c) Path-less binding lookups — B, a103 only.** 41 product sites in 24 files: `legacy_parent_for_path`
(`R/a103/runtime.py:2089`, called from 24 `to_child_*.py` files), `legacy_parent_types`
(`R/a103/homology_service_setup.py:3`, `R/a103/episode_bindings.py:408-452`), `legacy_request_assembler`
(`R/a103/runtime.py:3703-3708`), `legacy_parent_must_remain_unbound` (`R/a103/task_state.py:64`). 15 test sites use
them (a103 10, root tests 5). `binding_path is None` itself survives once, in
`R/a105/episode_binding_graph.py:166` (`duplicate_legacy_role`).

**(d) Database table upgrades — B, every area.** 42 sites in 23 distinct files (120 before): a103 16, a101 8,
a105 7, a106 7, a102/a104/a107/a110 3 each, root homes 2, a108 1, shared root 1. Three forms:
`method_loop/durable.py:400-401` adds `commissions.failure` (root and all nine axes);
`episode_journal.py`/`episode_receipts.py` rebuild or add columns (`R/a103/episode_journal.py:84` onward, 8 sites;
`R/a101/episode_receipts.py:45-72`); `homology_jobs.py` adds `orders.search_mode` (root, a101, a103, a104).
`shared_information.py:102` (`PRAGMA table_info(runtime_episodes)`, six axes) I did not read; it may be a
current-shape check.

**(e) 20 GiB literals — one value left.** 10 product sites: 9 are prose in tool descriptions that still say
"20 GiB RAM" while the policy is now 5 GiB (a103 `native_blast_database_tool_info.py:99`,
`native_blast_utility_tool_info.py:355,373`, `native_genomic_overlap_tool_info.py:24`,
`native_hmmer_preparation_tool_info.py:140`; `R/library/native_atac_differential_tool_info.py:24`,
`native_blast_utility_tool_info.py:355,373`, `native_chromatin_interaction_tool_info.py:32`). These now tell the
model something false. The one value is `R/a110/a110_fba_hpc.py:146` (HPC request features; h2 left it as an
owner question). Tests: `R/a110/tests/support/flux_balance/prepare_software.py:199` still expects 21474836480;
`R/a101/tests/test_hmmer_alignment_native_weight_oracle.py:9` is a match on unrelated text.

**(f) Ownership / relocation records — B.** 14 `*.ownership.json` files remain (9 distinct contents) in
`R/a101/library` (2), `R/a102/library` (6), `R/a103/library` (6). No Python file reads them. Each records an
`original_source` under `runs/…_20261111_…`, an `original_sha256` and a `historical_projector_identity`
(50 of the 56 "dated run" lines in product data are these). The other 4 lines are an a105 `README.md` and
`bvbrc_application_specs/MANIFEST.json` (`original_sha256` of upstream specifications, current).
`RELOCATION_REVIEW.md` is gone. Seven test files carry "ownership" in their name; I did not read them.

**(g) Tests tied to this instance of the code.**

| what | sites / files now | before | where |
|---|---|---|---|
| assert where code lives (`__module__`, `getsourcefile`) | 87 / 44 | 272 | a102 25, a103 25, root tests 11, a107 10, a101 7, a105 6, a110 3 |
| hash a product module's file | 5 / 5 | 46 | `R/a101/tests/test_native_blast_database_result_worker.py:210`, `…standard_database_result_worker.py:21`, `test_private_native_implementation_dependencies.py:24`, `R/a104/tests/execution_input_version_probe.py:88`; `tests/test_durable_episode.py:55` hashes its own fixture |
| read `.source` snapshots | 0 | 49 | — |
| read `verification/` | 2 / 2 | 88 | `R/a101/tests/test_api_bvbrc_data_v2.py:33`, `test_bvbrc_data_readers.py:19` (a copy kept under `fixtures/bvbrc_original/verification/`) |
| parse product source (`ast.parse`, `getsource`) | 1 | 208 | `R/a104/tests/test_a104_resume_adapter.py:14`; the other 6 hits load fixture helpers by path |
| test names saying moved / relocated / pinned / byte-identical / original-source | 74 / 69 | 116 | top tests 34, a101 14, a105 10 |
| files in fixture directories named for the past | 61 | 1,538 | `R/a105/tests/fixtures/retained_reference` 24, `research_reference` 9 (pa105: scientific source material); `R/tests/fixtures/bvbrc_fastqutils_samstat_legacy` 20 (external format) |

Only the first row is a real remainder; a102 and a103 hold 50 of its 87 sites.

**(h) Code that hashes this codebase's own files.** `h5_self_hashing.tsv` has 1,945 rows (distinct contents, with
copies, areas, enclosing function and whether an area agent's list has the line). 853 rows match a line in the six
agent lists; 1,092 do not — the agent lists cover a103 to a107 and a110 only.

| kind | distinct sites | meaning |
|---|---|---|
| `computes_and_compares_or_refuses` | 114 | a function hashes own files and the same function compares or raises |
| `compares_stored_identity` | 171 | compares a stored `*_sha256` / fingerprint without hashing there |
| `computes_identity_only` | 348 | hashes own files and only records the result |
| `carries_identity_field` | 1,146 | passes such a field through |
| `tool_source_pin_*` | 166 | see (i) |

"Compares" is decided per function by a regular expression (a comparison, `raise`, `require` or `assert` on a line
that mentions a digest); it was not confirmed line by line. The largest single mechanism is the 406
`binding_record.py` files, whose `implementation_sha256` is a hash over the home's own `.py` files
(743 sites, unchanged by the purge). h4 removed the digest tables; this computing side is intact in every area.

**(i) Pins of tool source** (`SOURCE_SHA256`, `SOURCE_FILE_SHA256`, `SOURCE_FUNCTION_SHA256`, `CALLABLE_SHA256` and
prefixed forms). 166 product sites in 72 distinct files, unchanged by the purge: root library 31, a105 25,
top package 24, a110 18, a107 14, a101 13, a106 13, a108 13, a103 8, a102 6, a104 6, shared root 6. 16 of them
compare. Tests: 21 sites (top tests 19, a110 2). I did not establish for each constant whether the pinned source is
third-party or this repository's.

## 4. `LEGACY_EVIDENCE_SLOT` — verdict: backward-facing alias, no current writer

- Code: `LEGACY_EVIDENCE_SLOT = "annotation_distinction"`, `ALL_SLOTS`, `_PREFIXES` and `canonical_slot()` map the
  name onto `evidence_axis` (`R/scientific_process_records.py:26-28,39-41`); `R/scientific_process_library.py:155-161,213,491,527`
  accept it in an index and rewrite it in `process.search`; `R/composition_information.py:127` and
  `R/scientific_process/configuration.py:16` accept either name. 221 product lines in 71 files (22 lines / 7 files
  in each of the nine axes, 23 lines / 8 files in the shared root and root homes).
- Data: the published library, `research/slotted_process_library/publications/2026-10-24-001/`, declares only
  `evidence_axis` (32 slot entries) and `thought_pattern` (40). Every caller that passes a library directory (49 lines in tests,
  examples and tools) names that publication; none passes the working copy. The unpublished working copy (`research/slotted_process_library/index.json`)
  still declares `annotation_distinction` with `count: 0` and the status "first scientific support slot unavailable
  pending scoring-axis review".
- No code in the repository writes a record with slot `annotation_distinction`. The only producers of it are test
  inputs (`tests/test_scientific_support_library.py:46`, `test_scientific_process_library.py:31,86`,
  `test_scientific_process_frozen_results.py:46`, `R/a104/scientific_process/tests/test_head_task.py:103,131`).
- One thing blocks a plain deletion: `R/scientific_support_metadata.py:53,103` defines the support-entry form
  (`scientific_support_entry_v1`) with `slot` fixed to `annotation_distinction`. No JSON file anywhere in the
  repository carries that entry version. So either the support-entry form is itself unused (delete both), or it is
  planned work and its slot name should become `evidence_axis`. **That choice is the owner's.** The area reports
  that called the constant live cited the working-copy index and this schema, not a writer.

## 5. Other remaining backward-facing sites (B)

- `legacy=` switches, 9 sites: `_locator(…, legacy=True)` in `R/a107/infernal_search_contracts.py:169,341,357,399`
  and `R/a110/library/received_execution_dependencies/infernal_search_contracts.py:95,252,266,308`;
  `intervention_population_schema(*, legacy=False)` at
  `R/a105/library/retained_input_authority/literature_intervention_inputs.py:19` (the root library copy has lost
  the parameter). Four test helpers keep a `legacy=False` parameter (`tests/test_decision_history.py:54`,
  `test_protease_kinetics_result_contracts.py:52`, `test_scientific_support_library.py:19`, `test_uniprot_returns.py:49`).
- Identifiers named `legacy`/`historical` that no report mentions: 76 product sites / 59 files after removing the
  families I read as live. By reading one site of each: clearly backward-facing are the `numerical.py` and
  `scientific_tool_library.py` sites in (a) and the a103 names in (c); `unsupported_historical_hmmer_request`
  (`provider_jobs.py:24`, six areas) labels a refusal of an older request identity. The rest are field names, codes
  and labels of current records (`legacy_nonnegative_difference_percentage_points`, `legacy_custody_variant`,
  `native_rate_return_view_cannot_publish_legacy_table`, `_LEGACY_LIMIT`, `historical_cause`, …): renames, not
  removals. Full list with areas: `h5_past_named_tokens.tsv`.
- Prose, 152 product comment/docstring lines that speak of older forms ("older immutable definitions remain
  readable", "the compatibility branch deliberately retains the old …"). In a sample of 14, about 8 described a
  compatibility behaviour and 3 an external tool format. Treat as leads: `R/evidence_axis_contracts.py:116`,
  `R/a101/runtime.py:342`, `R/a101/uniprot_returns.py:85`, `R/library/flux_balance_result_receipts.py:40`.

## 6. Needs the owner or needs reading (O)

| class | sites now (before) | note |
|---|---|---|
| `_live_original_runtime` / `_original_runtime` aliases | 14,844 (14,818) | name of the axis runtime module inside homes; a rename, current behaviour |
| path literals naming product `.py` files | 8,189 (10,259) in 136 files | either the input of a source fingerprint (h) or a list of files shipped to a worker; not separated |
| `inprocess_replay` | 4,245 | resume within one run; current per the brief |
| other `replay` | 1,385 | not separated into same-run and saved-run |
| bare `legacy` / `historical` | 2,741 (3,420) in 1,201 files | local names, keys and prose; the big families were traced live by the area reports |
| older `_vN` literal beside a newer one in the same file | 1,106 (1,308) | reports say the remaining families are distinct current kinds; a110 still on its second pass |
| membership tests over several versions | 348 + 369 | same |
| `as _old` wrappers | 494 in 13 files | `literature_controlled_response_owner_calculations.py` delegates to the earlier calculations module under the alias `_old`; no report mentions it |
| version-suffixed sibling modules | 30 files | `bvbrc_proteome_bundle_*` beside `*_v2`, `literature_controlled_response_inputs` beside `_v2_`/`_v3_` |
| legacy/historical identifiers discussed in a report | 139 (1,361) | kept by the area agent with a stated reason |
| `old_*` names, `predecessor`, `superseded`, 64-hex literals without a `.py` name | 348 / 286 / 183 | sampled as mostly in-run or data digests |

Duplicated modules (top-level package and `R/`): 8 pairs remain of 27 (`boundary_validation`,
`bvbrc_fastqutils_returns`, `credit`, `episode_bindings`, `evidence_geometry`, `molecular_result_facts`,
`progress_records`, `terminal_native_file_capture`); both sides of each are reachable from the CLI, so neither is a
leftover (ptop's `ptop_kept_duplicates.tsv` gives the importer of each).

Product modules nothing reaches: 1,789 are imported by neither the CLI closure nor any test, and 1,432 only by
tests (`h5_unreached_product_modules.tsv`). a101 has 627 unreferenced; a106 373 + 357; a107 223 + 522; a110
186 + 449. These numbers barely moved in the purge (1,810 and 1,486 before). They are not backward-facing by name;
they are candidates for a separate dead-code pass. `local_example/` is reached only from `tests/test_detached_job_service.py`.

## 7. Clearly current, despite the vocabulary (C)

`legacy_annotation` and `a103/legacy_improvement` (the current `improvement` role; 2,181 sites); external tool
formats (HMMER2, Infernal, BLAST `old_style_index`, SAMstat 2.2.3, `pgfams_legacy`; 315); in-run history in HPC
prediction and codon-tree records (62); the names the area reports traced to current writers (`self.legacy` for
`hmmer_api`, `legacy_uniprot_records`, `_validate_historical`, `legacy_returns`, `_LEGACY_SOURCES`,
`_LEGACY_PROFILE`, `LEGACY_MODES`, `hmmer_model_legacy`, the `historical_*.py` receiving modules; 2,612 sites and
141 files); `retained_input_authority` and `received_execution_*` packages (1,537 files). `LEGACY_EVIDENCE_SLOT` is
in that masked group in the tables below; section 4 is my verdict on it.

Words left unclassified after every rule above, as counts of product lines: `original` 68,000, `snapshot` 21,800,
`retained` 10,300, `before` 8,300, `frozen` 6,800, `previous` 4,600, `prior` 4,000, `baseline` 2,100. Token lists
were read at the start: commission/request "original", in-run "retained" and "snapshot", statistical "prior",
assay "baseline". They are not evidence of backward-facing code and were not searched further.

## 8. Proposed order of removal passes, safest first

| pass | what | where | tests that would show a regression |
|---|---|---|---|
| 1 | delete the 14 `*.ownership.json` files; correct the 9 "20 GiB" sentences | a101/a102/a103 `library`; a103 and `R/library` `*_tool_info.py` | none read the JSON; tool-info text tests of BLAST/HMMER/overlap in a103 |
| 2 | tests that assert module locations (87 sites) | a102, a103 `tests/*_task_checks.py`, `R/a102/tests/test_private_api_tasks.py`, `R/a107/tests/literature_task_checks.py` | the files themselves |
| 3 | `legacy=` switches and the `numerical.py` / tool-library compatibility operands | a107, a110 `infernal_search_contracts.py`; a105 RIA; a101..a104 `numerical.py` | `tests/test_infernal_*`, a107 Infernal result tests; `tests/test_numerical*` and each axis's yield tests |
| 4 | older run settings in a101, then a102, a103, then the a107/a110 tail (follow what a104 did) | `runtime.py` and about 110 home `task.py`-family files | the 35 test files that pass `None` doubles (`R/a10{1,2,3}/**/tests/test_*task*.py`, `*_task_checks.py`, `R/a107/tests/launch_connected.py`, `R/a110/tests/launch_connected.py`) |
| 5 | path-less parents in a103 | `R/a103/runtime.py`, `episode_bindings.py`, `homology_service_setup.py`, 24 `to_child_*.py` | `R/a103/tests/{api,launch,native,resource,results}_task_checks.py`, `R/a103/homology_job_monitoring/tests/test_homology_monitor_task.py` |
| 6 | database upgrades | `method_loop/durable.py`, `episode_journal.py`, `episode_receipts.py`, `homology_jobs.py`, all areas | 32 test files import those modules, e.g. `R/a103/tests/test_source_investigation_family.py`, `R/a101/tests/test_blast_native_return_admission.py`; any test that opens a store built by an earlier schema will fail and should go |
| 7 | evidence-slot alias, after the owner's choice in section 4 | 71 files, same lines in every axis | `tests/test_scientific_support_library.py`, `test_scientific_process_library.py`, `test_scientific_process_frozen_results.py`, `R/a104/scientific_process/tests/test_head_task.py` |
| 8 | self-hashing: comparing sites first (285), then the computing side including `binding_record.py` | everywhere | 106 test files import a module with a self-hash site (`R/a101/tests/test_blast_binding.py`, `R/a102/tests/test_operational_configuration.py`, `tests/test_scientific_hpc_environment.py`, …); records carry the field, so schemas change with it |
| 9 | owner decisions: renames (`_live_original_runtime`, `legacy_annotation`), `_old` wrappers and `_v2` siblings, unreached modules | — | — |

Passes 1 to 3 touch no live decision path. Passes 4 to 6 are in the runtime that every run uses. Pass 8 changes
record shapes.

## 9. Tables

Files beside this one: `h5_sites.tsv` (3,728 rows: every B and S site now, with copies, areas, reachability and
the reports that mention the name), `h5_self_hashing.tsv`, `h5_class_area.tsv` (every class and verdict by area),
`h5_past_named_tokens.tsv`, `h5_unreached_product_modules.tsv`.

Reading the tables: "sites before purge" uses the same rules on a0d9f1666. A line can fall in more than one class.
`S_h_*` rows are the line-level view of (h); `B_prose_marker` is described in section 5.

### Clearly backward-facing (pattern matched, not named live in any area report) — product

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| B_prose_marker | 203 | 152 | 140 | 191 |
| B_past_named_identifier_unreported | 167 | 76 | 59 | 90 |
| B_past_named_identifier_removed_in_other_areas | 173 | 53 | 25 | 56 |
| B_past_flag_parameter | 192 | 9 | 3 | 9 |
| B_saved_source_copy_reference | 6 | 0 | 0 | 0 |
| P_saved_source_copy_file | 211 | 0 | 0 | 0 |
| B_past_version_named_constant_unreported | 3 | 0 | 0 | 0 |

### Clearly backward-facing (pattern matched, not named live in any area report) — tests

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| B_past_named_identifier_unreported | 707 | 126 | 59 | 126 |
| T_test_name_past | 116 | 74 | 69 | 74 |
| P_past_named_directory | 1538 | 61 | 61 | 63 |
| B_prose_marker | 71 | 27 | 22 | 27 |
| B_past_named_identifier_removed_in_other_areas | 24 | 15 | 12 | 15 |
| T_runs_or_dated_artifact_reference | 22 | 10 | 8 | 10 |
| T_source_text_inspection | 208 | 7 | 7 | 7 |
| B_past_flag_parameter | 16 | 4 | 4 | 4 |
| P_past_named_file | 19 | 1 | 1 | 1 |
| B_past_version_named_constant_unreported | 2 | 0 | 0 | 0 |
| B_saved_source_copy_reference | 47 | 0 | 0 | 0 |
| P_saved_source_copy_file | 108 | 0 | 0 | 0 |

### Specific items requested for counting (verdict per class in the text) — product

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| S_h_impl_digest_pin_mechanism | 1968 | 1113 | 629 | 1203 |
| S_h_impl_source_bytes_fingerprint | 743 | 743 | 425 | 843 |
| S_i_tool_source_pin | 166 | 166 | 72 | 177 |
| S_a_branch_lifecycle_equal_branch | 173 | 126 | 78 | 133 |
| S_a_completed_action_inputs_none | 356 | 126 | 116 | 219 |
| S_a_wait_inputs_version_check | 356 | 123 | 113 | 213 |
| S_h_source_self_hash | 136 | 120 | 91 | 121 |
| S_f_dated_run_or_original_reference_in_data | 3156 | 56 | 11 | 93 |
| S_a_unproven_replay | 312 | 45 | 44 | 45 |
| S_d_db_table_migration | 120 | 42 | 23 | 54 |
| S_c_pathless_binding_lookup | 42 | 41 | 24 | 44 |
| S_a_branch_lifecycle_not_equal_check | 40 | 28 | 10 | 28 |
| S_a_branch_lifecycle_other_reference | 10 | 10 | 10 | 10 |
| S_e_20_gib_literal | 156 | 10 | 8 | 10 |
| S_f_ownership_or_relocation_record_file | 1216 | 9 | 9 | 14 |
| S_b_shared_local_resources_v1_v2 | 25 | 8 | 8 | 8 |
| S_a_execution_status_v1 | 17 | 8 | 8 | 8 |
| S_a_wait_inputs_binding_v1 | 30 | 6 | 2 | 6 |
| S_a_progress_receipts_legacy_grouped_v1 | 20 | 3 | 2 | 3 |
| S_h_impl_digest_pin_literal | 1650 | 0 | 0 | 0 |
| S_b_prior_or_legacy_version_const | 76 | 0 | 0 | 0 |

### Specific items requested for counting (verdict per class in the text) — tests

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| S_h_impl_digest_pin_mechanism | 550 | 91 | 54 | 91 |
| S_g_test_asserts_module_location | 272 | 87 | 44 | 87 |
| S_f_dated_run_or_original_reference_in_data | 3368 | 47 | 17 | 47 |
| S_a_completed_action_inputs_none | 128 | 35 | 35 | 35 |
| S_i_tool_source_pin | 43 | 21 | 8 | 21 |
| S_c_pathless_binding_lookup | 24 | 15 | 12 | 15 |
| S_h_source_self_hash | 88 | 10 | 9 | 10 |
| S_b_shared_local_resources_v1_v2 | 64 | 7 | 7 | 7 |
| S_f_ownership_or_relocation_record_file | 154 | 7 | 7 | 7 |
| S_g_test_hashes_product_source | 46 | 5 | 5 | 5 |
| S_e_20_gib_literal | 73 | 2 | 2 | 2 |
| S_g_test_reads_verification | 88 | 2 | 2 | 2 |
| S_d_db_table_migration | 20 | 1 | 1 | 1 |
| S_b_prior_or_legacy_version_const | 3 | 0 | 0 | 0 |
| S_a_execution_status_v1 | 5 | 0 | 0 | 0 |
| S_a_wait_inputs_binding_v1 | 20 | 0 | 0 | 0 |
| S_a_progress_receipts_legacy_grouped_v1 | 4 | 0 | 0 | 0 |
| S_a_branch_lifecycle_equal_branch | 5 | 0 | 0 | 0 |
| S_g_test_reads_source_snapshot | 49 | 0 | 0 | 0 |
| S_a_wait_inputs_version_check | 13 | 0 | 0 | 0 |
| S_h_impl_digest_pin_literal | 66 | 0 | 0 | 0 |

### Needs the owner / needs reading — product

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| O_original_runtime_alias | 14818 | 14844 | 1448 | 43630 |
| O_source_path_literal | 10259 | 8189 | 136 | 8198 |
| O_replay_inprocess | 4246 | 4245 | 705 | 7187 |
| O_legacy_or_historical_bare_word | 3420 | 2741 | 1201 | 4575 |
| O_replay_other | 1661 | 1385 | 945 | 1845 |
| O_older_record_version_literal | 1308 | 1106 | 464 | 1469 |
| O_old_module_alias | 494 | 494 | 13 | 494 |
| O_version_membership_other | 413 | 369 | 295 | 704 |
| O_multi_version_membership | 410 | 348 | 205 | 578 |
| O_old_named | 346 | 348 | 90 | 499 |
| O_predecessor_superseded | 256 | 286 | 78 | 353 |
| O_hex_digest_literal | 691 | 183 | 59 | 347 |
| O_past_named_identifier_discussed_in_area_report | 1361 | 139 | 82 | 164 |
| O_original_named_past | 132 | 127 | 26 | 127 |
| O_older_version_sibling_file | 30 | 30 | 30 | 37 |
| P_past_named_directory | 24 | 24 | 24 | 36 |
| O_past_version_named_constant | 427 | 9 | 6 | 9 |
| O_past_named_file_discussed_in_area_report | 13 | 1 | 1 | 1 |

### Needs the owner / needs reading — tests

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| O_replay_other | 1596 | 776 | 347 | 776 |
| O_legacy_or_historical_bare_word | 1396 | 356 | 113 | 356 |
| O_old_named | 386 | 132 | 42 | 132 |
| O_hex_digest_literal | 363 | 120 | 64 | 120 |
| O_test_hashes_some_file | 374 | 88 | 63 | 88 |
| O_predecessor_superseded | 114 | 68 | 23 | 68 |
| O_older_record_version_literal | 182 | 50 | 35 | 50 |
| O_replay_inprocess | 100 | 43 | 38 | 43 |
| O_original_named_past | 80 | 27 | 19 | 27 |
| P_retained_named_directory | 674 | 19 | 19 | 42 |
| O_source_path_literal | 62 | 19 | 16 | 19 |
| O_past_named_identifier_discussed_in_area_report | 158 | 10 | 8 | 10 |
| O_older_version_sibling_file | 14 | 4 | 4 | 4 |
| O_version_membership_other | 55 | 4 | 4 | 4 |
| O_multi_version_membership | 31 | 3 | 3 | 3 |
| O_past_named_file_discussed_in_area_report | 13 | 1 | 1 | 1 |
| O_original_runtime_alias | 7 | 1 | 1 | 1 |
| O_past_version_named_constant | 49 | 0 | 0 | 0 |
| O_old_module_alias | 70 | 0 | 0 | 0 |

### Clearly current (sampled vocabulary or traced live by an area agent) — product

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| C_traced_retained_authority_package | 5373 | 5355 | 1476 | 6246 |
| C_traced_live_by_area_agents | 2745 | 2612 | 767 | 3476 |
| C_frozenset | 2633 | 2601 | 1201 | 3834 |
| C_role_name_legacy | 2185 | 2181 | 335 | 2347 |
| P_traced_retained_authority_package_file | 1619 | 1408 | 1408 | 1537 |
| C_external_tool_legacy_format | 306 | 315 | 121 | 393 |
| C_same_family_as_traced_live_name | 202 | 194 | 78 | 356 |
| P_traced_live_historical_module | 141 | 141 | 141 | 142 |
| C_in_run_history_named_historical | 63 | 62 | 23 | 92 |
| C_requires_current_wait_inputs_version | 0 | 7 | 7 | 7 |
| C_requires_current_completed_action_inputs_version | 0 | 6 | 6 | 6 |

### Clearly current (sampled vocabulary or traced live by an area agent) — tests

| class | sites before purge (a0d9f1666) | sites now | distinct files now | site copies now |
|---|---|---|---|---|
| C_traced_retained_authority_package | 127 | 54 | 22 | 56 |
| C_external_tool_legacy_format | 88 | 39 | 23 | 39 |
| C_traced_live_by_area_agents | 230 | 35 | 13 | 35 |
| C_role_name_legacy | 86 | 21 | 9 | 21 |
| C_in_run_history_named_historical | 14 | 12 | 7 | 12 |
| C_frozenset | 450 | 8 | 8 | 8 |
| C_same_family_as_traced_live_name | 92 | 5 | 3 | 5 |

### Per area, verdict B — product (distinct sites present in each area now; a site shared by copies in two areas counts in both)

| class | a101 | a102 | a103 | a104 | a105 | a106 | a107 | a108 | a110 | root_library | root_shared | top_package |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B_past_flag_parameter |  |  |  |  | 1 |  | 4 |  | 4 |  |  |  |
| B_past_named_identifier_removed_in_other_areas | 12 |  | 41 |  |  |  |  |  |  |  |  |  |
| B_past_named_identifier_unreported | 9 | 8 | 14 | 11 | 5 | 4 | 13 | 5 | 8 | 10 | 3 |  |
| B_prose_marker | 24 | 21 | 19 | 22 | 14 | 15 | 18 | 11 | 14 | 15 | 13 | 5 |

### Per area, verdict B — tests (distinct sites present in each area now; a site shared by copies in two areas counts in both)

| class | a101 | a102 | a103 | a104 | a105 | a106 | a107 | a108 | a110 | root_tests | top_tests |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B_past_flag_parameter |  |  |  |  |  |  |  |  |  |  | 4 |
| B_past_named_identifier_removed_in_other_areas |  |  | 10 |  |  |  |  |  |  | 5 |  |
| B_past_named_identifier_unreported | 17 | 7 | 4 | 11 | 21 | 3 | 4 |  | 5 | 21 | 33 |
| B_prose_marker | 7 | 1 | 1 | 1 | 3 |  | 1 |  |  | 4 | 9 |
| P_past_named_directory |  |  | 1 |  | 33 |  | 3 |  |  | 25 |  |
| P_past_named_file | 1 |  |  |  |  |  |  |  |  |  |  |
| T_runs_or_dated_artifact_reference |  | 3 | 4 |  |  |  |  |  |  |  | 3 |
| T_source_text_inspection |  |  |  | 1 |  |  |  |  |  |  | 6 |
| T_test_name_past | 14 | 2 | 2 | 4 | 10 | 2 | 1 | 1 |  | 4 | 34 |

### Per area, verdict S — product (distinct sites present in each area now; a site shared by copies in two areas counts in both)

| class | a101 | a102 | a103 | a104 | a105 | a106 | a107 | a108 | a110 | root_homes | root_library | root_shared | top_package | top_package/bvbrc_application_specs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S_a_branch_lifecycle_equal_branch | 31 | 27 | 16 | 1 | 14 | 21 | 1 | 14 | 1 |  |  |  |  |  |
| S_a_branch_lifecycle_not_equal_check | 4 | 4 | 4 | 1 | 4 | 4 | 1 | 4 | 1 |  |  | 1 |  |  |
| S_a_branch_lifecycle_other_reference | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |  |  | 1 |  |  |
| S_a_completed_action_inputs_none | 48 | 33 | 38 |  |  |  | 3 |  | 4 |  |  |  |  |  |
| S_a_execution_status_v1 | 2 | 2 | 2 |  |  |  |  | 1 |  |  |  |  | 1 |  |
| S_a_progress_receipts_legacy_grouped_v1 | 2 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |
| S_a_unproven_replay | 45 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| S_a_wait_inputs_binding_v1 | 3 | 3 |  |  |  |  |  |  |  |  |  |  |  |  |
| S_a_wait_inputs_version_check | 48 | 33 | 33 |  |  |  | 4 |  | 5 |  |  |  |  |  |
| S_b_shared_local_resources_v1_v2 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 |  |  |  |  | 1 |  |
| S_c_pathless_binding_lookup |  |  | 41 |  |  |  |  |  |  |  |  |  |  |  |
| S_d_db_table_migration | 8 | 3 | 16 | 3 | 7 | 7 | 3 | 1 | 3 | 2 |  | 1 |  |  |
| S_e_20_gib_literal |  |  | 5 |  |  |  |  |  | 1 |  | 4 |  |  |  |
| S_f_dated_run_or_original_reference_in_data | 5 | 41 | 41 |  | 4 |  |  |  |  |  |  |  |  | 2 |
| S_f_ownership_or_relocation_record_file | 2 | 6 | 6 |  |  |  |  |  |  |  |  |  |  |  |
| S_h_impl_digest_pin_mechanism | 112 | 107 | 134 | 114 | 86 | 76 | 145 | 54 | 156 | 35 | 115 | 31 | 38 |  |
| S_h_impl_source_bytes_fingerprint | 130 | 111 | 141 | 56 | 35 | 77 | 74 | 47 | 74 |  |  |  |  |  |
| S_h_source_self_hash | 36 | 7 | 8 | 7 | 4 | 22 | 11 | 4 | 8 |  | 9 |  | 5 |  |
| S_i_tool_source_pin | 13 | 6 | 8 | 6 | 25 | 13 | 14 | 13 | 18 |  | 31 | 6 | 24 |  |

### Per area, verdict S — tests (distinct sites present in each area now; a site shared by copies in two areas counts in both)

| class | a101 | a102 | a103 | a104 | a105 | a106 | a107 | a108 | a110 | root_tests | top_tests |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S_a_completed_action_inputs_none | 5 | 13 | 14 |  |  |  | 2 |  | 1 |  |  |
| S_b_shared_local_resources_v1_v2 | 1 | 1 | 1 | 1 |  | 1 |  | 1 |  | 1 |  |
| S_c_pathless_binding_lookup |  |  | 10 |  |  |  |  |  |  | 5 |  |
| S_d_db_table_migration |  |  |  |  |  |  |  |  |  |  | 1 |
| S_e_20_gib_literal | 1 |  |  |  |  |  |  |  | 1 |  |  |
| S_f_dated_run_or_original_reference_in_data |  | 3 |  | 11 |  | 21 | 10 |  | 1 | 1 |  |
| S_f_ownership_or_relocation_record_file |  |  |  |  | 1 | 3 |  | 1 |  |  | 2 |
| S_g_test_asserts_module_location | 7 | 25 | 25 |  | 6 |  | 10 |  | 3 | 11 |  |
| S_g_test_hashes_product_source | 3 |  |  | 1 |  |  |  |  |  |  | 1 |
| S_g_test_reads_verification | 2 |  |  |  |  |  |  |  |  |  |  |
| S_h_impl_digest_pin_mechanism | 22 |  |  | 1 |  | 3 | 3 |  | 3 | 6 | 53 |
| S_h_source_self_hash | 3 |  |  | 2 |  |  |  |  |  | 1 | 4 |
| S_i_tool_source_pin |  |  |  |  |  |  |  |  | 2 |  | 19 |

### Self-hashing and identity sites in product code, distinct sites per area (ALL = distinct sites over the tree)

| kind | a101 | a102 | a103 | a104 | a105 | a106 | a107 | a108 | a110 | root_homes | root_library | root_shared | top_package | ALL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carries_identity_field | 111 | 131 | 153 | 133 | 55 | 76 | 164 | 44 | 152 | 29 | 118 | 30 | 25 | 1146 |
| compares_stored_identity | 15 | 16 | 18 | 23 | 14 | 13 | 25 | 7 | 19 | 7 | 12 | 7 | 2 | 171 |
| computes_and_compares_or_refuses | 9 | 8 | 10 | 11 | 11 | 7 | 17 | 4 | 9 | 6 | 14 | 2 | 7 | 114 |
| computes_identity_only | 37 | 49 | 57 | 26 | 19 | 22 | 51 | 19 | 47 | 20 | 17 | 3 | 7 | 348 |
| tool_source_pin_compared | 1 |  | 1 |  | 4 | 1 | 1 | 1 | 1 |  | 5 |  | 3 | 16 |
| tool_source_pin_constant_or_field | 12 | 6 | 7 | 6 | 21 | 12 | 13 | 12 | 17 |  | 26 | 6 | 21 | 150 |
