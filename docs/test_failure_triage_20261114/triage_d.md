# triage_d: literature and context test failures

Paths are abbreviated: `R/` = `gene_annotation_episode/episodic_workflow/root/`, `SEE/` =
`R/a105/scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/`.
"orig" = the pre-reorganisation revision `fb1e4d9ba` (parent of the snapshot commit `dfe3e6091`).

How each statement was established is marked:
- **[run]** reproduced through the launcher (slot `triage_d`, run directories `runs/claude_triage_triage_d_01` .. `_25`).
  Proposed test fixes were tried on copies of the test file kept outside the repository (scratchpad); no repository file was changed.
- **[read]** established by reading code, tracebacks and git history only.
- **[inferred]** a conclusion drawn from reading that was not exercised.

## 1. Headline: `local_resource_binding_conflict` hides a second failure in 11 of 14 cases

All 14 failures with this message have one cause, and it is not the 1 CPU / 5 GiB limit.

- Raised at `R/a105/local_resources.py:117` (13 cases) and `gene_annotation_episode/local_resources.py:129` (1 case, a103). [read]
- `LocalResources.configured()` (`R/a105/local_resources.py:137-145`, same in every copy) uses
  `<launcher run directory>/local-resources/capacity.sqlite3` whenever the launcher's `GENE_EPISODE_WORKFLOW_BUDGET_FILE`
  is set and `GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY` is not. `tools/run_tests_by_home.py:115-119` starts every test
  directory as a child of one launcher run, so every unit of the run shares that one file. [read]
- The first copy to open the file stamps its own `VERSION`; a copy with another `VERSION` refuses it. The copies differ:
  v1 = `gene_annotation_episode/local_resources.py` and `R/a105`; v2 = `R/a101, a102, a103, a104, a106, a108`;
  v3 = `R/a107, a110` (line 24 of each). The saved row in
  `runs/claude_tests_leaf_up_20261114_02/local-resources/capacity.sqlite3` reads `"version": "shared_local_resources_v2"`. [read]
- Each of the 7 affected test files, run alone in a fresh run directory, no longer raises the conflict (runs 01-07). [run]

So it is shared state between test units of one launcher run (a file, not in-process state), made fatal by the differing
version stamps in the per-axis copies. Classification: `environment`.

Two consequences beyond the test runner, both [inferred]:
- A test that mixes copies of different versions inside one unit will conflict even with per-unit isolation
  (see 1f: an a103 test using the top-level v1 `native_lifecycle` inside the v2 a103 unit).
- A real combined workflow in one launcher run that reaches both an a105 (v1) and another axis (v2/v3) `LocalResources`
  would raise the same error. I did not exercise this; it is a product question for the owner, not a proposed change.

Minimal fix for the test run: in `tools/run_tests_by_home.py:115-119` pass
`env={**os.environ, "GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY": str(run_dir / "local-resources" / f"{index:04d}")}` so each unit
has its own ledger. Not tried. About 30 test files reference that variable; check they set or clear it themselves before
relying on this. No scientific change.

### What is behind the conflict in each of the 14

| # | Test (count) | After removing the conflict | Classification of the hidden failure | Minimal fix | Scientific? |
|---|---|---|---|---|---|
| 1a | `test_a106_final_selection_feedback` (3 tests x 2 = 6) | `TypeError: LiteratureConfiguration.__init__() got an unexpected keyword argument 'rate_population'` (run 01). With the keywords removed, 1 passes and 5 fail `KeyError: 'detail'` (run 08). | First layer `stale_test`: `R/a106/published_evidence_assessment/configuration.py:7` has no `rate_population` / `a106_intervention`; the a106 home is always in that mode (orig `literature_episodes.py:300-331` had the flags). Second layer `product_defect`, older than the reorganisation: `R/a106/library/literature_a106_subscore_storage.py:398,456,476` build a `detail`, but `execute` (`R/a106/published_evidence_assessment/source_operations.py:114`) forwards `detail` only for three other codes; orig `literature_episodes.py:1549-1561` is the same text. `docs/A106_IMPLEMENTATION.md:1063,1150` calls these tests "prepared but unrun". | Test lines 26, 75, 117: drop the two keywords. Then decide whether `execute` should forward `detail` for `assay_grading_sheet_required`, `a106_current_assessment_required`, `a106_latest_subscore_revision_required` on `literature.a106.finalize`. | Keyword removal: no. Forwarding `detail`: yes, it changes what A106 feedback reports to the agent. Flag, do not change without the owner. |
| 1b | `test_literature_channel_original_294` (3) | 2 pass; `test_original_fluc_cold_saved_reconstruction_does_not_reparse_source` fails `ImportError ... gene_annotation_episode.literature_channel_storage` (run 02). | `test_wiring`: line 134 builds `monkeypatch.setattr(f'gene_annotation_episode.{module}.{name}', ...)`; the import rewriter did not touch this string. | Line 134: prefix `gene_annotation_episode.episodic_workflow.root.a105.library.`. 3 passed with this change (run 17). | No. |
| 1c | `test_literature_channel_binding_188::test_optional_binding_exact_registered_form_and_requested_omission` (1) | Passes (run 03). | none | none | No. |
| 1d | `test_literature_assay_grading_uncertainty_324::test_existing_summary_sd_variance_and_df_reach_t_scoring_without_reextraction` (1) | `status: invalid`, code `summary_precision_prospective_dependency_mismatch` (runs 06, 11). | `product_defect`, cause C3 below. | See C3. | Yes (A105). Flag. |
| 1e | `test_literature_a105_channel_ion_worksheet_298` (1) | `status: invalid`, code `ion_discrimination_prospective_dependency_mismatch` (runs 04, 10). | `product_defect`, cause C3 below. | See C3. | Yes (A105). Flag. |
| 1f | `test_literature_wst8_method_contrast_291::test_original_wst8_uv_selected_operation_returns_typed_cells` (1) | `assert '..._implementation_v4' == '..._implementation_v2'` (run 05). | `stale_test`: `R/a105/library/literature_measurement_comparison_storage.py:307` now writes `measurement_comparison_original_implementation_v4`; `R/a105/tests/test_measurement_comparison_attestation_v4.py:115` asserts v4. The orig code already wrote v3 (orig `literature_measurement_comparison_storage.py:380`), so the v2 assertion was out of date before the reorganisation. | Test line 189: `_v2` to `_v4`. 3 passed with this change (run 18). | No (receipt version label). |
| 1g | `test_a103_real_detection::test_real_complete_search_scoped_absence_unknown_and_cooccurrence` (1) | `TypeError: local_job_policy_required` at `R/a101/native_lifecycle.py` (run 07). With imports pointed at a103: `FileNotFoundError: .../gene_annotation_episode/phmmer_format.py` (run 12). | First layer `test_wiring`: line 24 imports `HomologyResults` from the **a101** copy while lines 25-26 take `LocalJobPolicy`, `prepare_job` from the top-level modules; a101's `prepare_job` rejects a policy object of another class. Second layer `product_defect`: `R/a103/homology_results.py:288` reads the six worker files from `Path(__file__).resolve().parents[3]`, which is the old package root; the files are in `R/a103/`. `R/a104/homology_results.py:288` uses `.parent`. | Test lines 22, 24-26: import `AcquisitionError`, `HomologyResults`, `NativePhmmerInput`, `LocalJobPolicy`, `prepare_job`, `start_prepared`, `wait_job` from the `R/a103` copies. Product: `R/a103/homology_results.py:288` `parents[3]` to `parent`. The product change was not tried. | No (path used for a worker fingerprint). |

## 2. Causes that explain the remaining groups

### C2. Test imports `ContractError` from the top-level module; the axis raises its own class (`test_wiring`)

`R/a102/domain.py:15` and `R/a103/domain.py` define their own `ContractError`. The tests catch
`gene_annotation_episode.domain.ContractError`, so `pytest.raises` does not match and the axis error escapes.

| Group (count) | Evidence | Minimal fix | Verified |
|---|---|---|---|
| `test_literature_structure_storage` (28, all 7 rows) | Every traceback ends in `R.a102.domain.ContractError` raised inside the `pytest.raises` block; test line 8 `from gene_annotation_episode.domain import ContractError, obj, validate_schema`. | `R/a102/tests/test_literature_structure_storage.py:8` import from `...root.a102.domain`. | 37 passed (run 19). [run] |
| `test_a103_context`: `test_a_single_cds_cannot_mint_a_neighbor_association`, `test_coordinates_or_prose_cannot_mint_native_context_grades`, `test_same_genome_cannot_be_split_into_independent_sampling_groups` (3) | Same pattern, `R.a103.domain.ContractError`; test line 13. | `R/a103/tests/test_a103_context.py:13` import from `...root.a103.domain`. | These 3 pass, file 37 passed / 3 failed (run 24). [run] |
| `test_a103_channels::test_combined_string_score_cannot_create_context_measurement` (1) | Same; test line 7. | `R/a103/tests/test_a103_channels.py:7` import from `...root.a103.domain`. | 2 passed (run 25). [run] |

Scientific: no. 32 failures.

### C3. Pinned implementation hashes were not refreshed after the files were rewritten (`product_defect`, A105, flag)

The A105 storage modules refuse to populate unless named implementation files have a pinned sha256. The reorganisation
rewrote those files (absolute imports, reformatting), and the pins do not match the files as committed.

| Group (count) | Raise site | Pin table | Evidence [read] |
|---|---|---|---|
| `test_literature_assay_grading_inputs`: `test_actual_compiled_native_nondetection_does_not_become_measured_zero`, `test_compiled_native_component_does_not_inherit_unselected_estimate_owners` (2) | `R/a105/library/literature_product_coupling_storage.py:198` | `_FROZEN`, line 29 | Pins equal the orig file hashes (`fcf0115c...`, `d7f99c4b...`); current files hash to `b2f3fb2c...`, `ce3a7b05...`. |
| `test_literature_assay_grading_inputs::test_compiled_partial_variance_uses_selected_uncertainty_not_legacy_full_model` (1) | `R/a105/library/literature_optical_storage.py:59` | `_PINNED`, line 39 | Pins for `literature_optical_inputs.py` and `literature_optical_validation.py` match neither orig nor current; pin for `literature_optical_calculations.py` is the orig hash. |
| hidden behind 1e (1) | `R/a105/library/literature_ion_discrimination_storage.py:187` | `_FROZEN`, line 26 | 3 of 4 pins equal orig hashes; current files differ. |
| hidden behind 1d (1) | `R/a105/library/literature_kinetic_summary_precision_storage.py:227` | `_MOVED_HASHES`, line 29 | Pins match neither orig nor current. |

- The pinned files have one commit each (`dfe3e6091`), so the mismatch dates from the snapshot, not from the later import
  re-pointing commits. [read]
- A rough shell count over `R/a105` (non-test files, my own path resolution, so approximate): 178 pinned entries do not match
  the file on disk, 49 do. Some tables are historical maps that are not checked on populate. [read, approximate]
- Precedent in the same tree: measurement comparison was given a new receipt version with fresh pins and kept its historical
  maps (`R/a105/library/literature_measurement_comparison_storage.py:302-307, 628-634`).

Minimal repair: for each table that is checked on populate, replace the stale digests with the sha256 of the current
per-axis file (or add a new receipt version as measurement comparison did). I did not try this.

Scientific: **yes, flag.** These pins are the implementation receipt saved with A105 records. Re-pinning asserts that the
rewritten files compute the same thing as the pinned originals; nobody has checked that here (I did not compare the files
beyond seeing that the diffs are large because of reformatting). Removing or bypassing the check would be a fallback and is
not proposed. 3 visible failures plus 2 hidden.

### C4. `test_literature_channel_binding_188`, remaining two

| Test | Classification | Cause | Minimal fix | Scientific? |
|---|---|---|---|---|
| `test_replay_and_readonly_reconstruction_never_reacquire_or_recalculate` | `test_wiring` | Line 226 `monkeypatch.setattr(f'gene_annotation_episode.{module}.{function}', ...)`, same un-rewritten string as 1b. All ten targets exist in `R/a105/library/`. [read] | Line 226: prefix `gene_annotation_episode.episodic_workflow.root.a105.library.`. Passes with this change (run 09: 26 passed, 1 failed). [run] | No. |
| `test_recurring_task_and_scoped_steering_for_own_return_history_lookup_and_parent` | `stale_test` | Line 362 asserts the substrings `'source_'` and `'artifact_'` are absent from the STEERING text. The token that trips it is `'source_'` in the fixed preamble "For text anchors, select the received source_ref, artifact_ref ..." (run 09 [run]) at `R/a105/library/literature_experimental_prompt.py:1016`. The same sentence is in orig `literature_experimental_prompt.py:1533`, so the assertion could not hold before the reorganisation either. [read] | Line 362: assert on identifier-shaped tokens (for example `source_` followed by hex) or drop the two bare prefixes. Owner's choice of intent. | No (prompt text check). |

### C5. `test_literature_native_rate_operand_information` (3)

| Test (count) | Classification | Cause | Minimal fix | Scientific? |
|---|---|---|---|---|
| `test_actual_catalog_schema_meanings_recur_in_task_and_feedback_stays_in_steering` (2) | `stale_test` | Line 147 `assert len(catalog) == 19`. `R/a105/published_evidence_assessment/source_contracts.py::_population_catalog()` returns 22. The orig default catalog had one initial list plus 28 unconditional appends (orig `literature_episodes.py:94-292`), so 19 was already out of date. [read] | Line 147: 22, or drop the count. With 22 both cases pass (run 23). [run] | No. |
| `test_actual_c7_dispatch_is_still_one_selected_native_repository_call` (1) | `stale_test` | The fake `Services` (line 178) supplies only `literature_*_repository`. (a) `_tool_arguments` builds the endpoint-signal repository from `self.services.workflow.store` for every tool when `rate_population` is set (`R/a105/published_evidence_assessment/source_operations.py:48-49`, `scientific_records.py:145-150`); orig `literature_episodes.py:1422-1423, 1624-1629` is the same, so `AttributeError: workflow` predates the reorganisation. (b) The rate repository is no longer taken from `services.literature_rate_repository` (orig line 1505); the episode builds it from the store (`R/a105/published_evidence_assessment/scientific_records.py:7-14`). Giving the fake a `workflow` moves the failure to `'NoneType' object has no attribute 'db'` (run 23). [run] | Rewrite the test with a real `Store` and replace the episode's `literature_rate_repository`, or retire it. | No. |

### C6. a102 cannot rebuild its own literature bindings from saved descriptors (`product_defect`)

`R/a102/episode_composition.py:85` (`_PRIVATE_RECONSTRUCTION`) and the instantiation chain from line 167 have no entry for
any `published_evidence_assessment` binding; line 144-145 raises `unavailable_binding` for them. But
`R/a102/published_evidence_assessment/binding_record.py:11` emits `binding_id: 'published_evidence_assessment'`, and
`A102ServiceFactory.__call__` (`R/a102/a102_investigation.py:124,150`) emits seven
`scientific_process/published_evidence_assessment...` descriptors. Orig `episode_composition.py:390-391` rebuilt the
literature binding; `R/a105/episode_composition.py:142-153` and `R/a108/episode_composition.py:137-148` still do. [read]

| Group (count) | Note |
|---|---|
| `test_literature_structure_integration::test_original_source_selected_cells_and_saved_only_binding_reconstruction` (2) | Fails at test line 111 on the descriptor from `binding.as_record()`. [read] |
| `test_a102_parent_coordination::test_parent_coordinates_missing_model_and_axes_stay_siblings` (1) | Fails in `create_a102_workflow` via `R/a102/runtime.py:2002`. Which descriptor is rejected is [inferred]: the junit has no locals; every non-literature id the factory emits is in the table. |

Minimal repair: add the a102 literature binding ids to `R/a102/episode_composition.py` in the a108 form (a module-path
table plus `LiteratureEpisode(services, **configuration)`). Not tried. I could not tell whether the omission was deliberate;
the docstring at line 110 ("Literature continues to use the separately supplied scientific service") is unchanged from orig.
Scientific: no.

### C7. `test_literature_structure_integration`, remaining four

| Test (count) | Classification | Cause | Minimal fix | Scientific? |
|---|---|---|---|---|
| `test_structure_selected_in_ordinary_child_and_received_once` (2) | `test_wiring`, then `unclear` | `KeyError: 'literature_strategy'` at `R/a102/runtime.py:2057`: line 164 binds only the top literature home, but the former single binding is now seven homes (`R/a102/published_evidence_assessment/episode.py:91-100`), and the top home declares children whose roles are unbound. [read] With all seven supplied the workflow starts but ends `source_failed` at decision 0 with `selected_operation_failed` / `ValueError` (runs 20, 21, read from `runtime_source_failures`). I did not find where that `ValueError` is raised. | Line 164: one `partial(<home>.LiteratureEpisode, structure_population=True)` per home. This is necessary but not sufficient. | No. |
| `test_structure_task_and_conditional_meanings_repeat_at_provider_boundary`, `test_parent_keeps_own_task_and_receives_physical_panel_once` (2) | `stale_test` | Lines 176 and 227 import `LiteratureWire, snapshot, complete` from `test_literature_experimental_prompt_delivery`, which is parked (`tests_parked/gene_annotation_episode/episodic_workflow/root/tests/`, reason in `tests_parked/PARKED.tsv:256`). With those three helpers copied out and pointed at a102, both tests fail `not enough values to unpack` on `text.split('\n\nSTEERING\n', 1)` (run 20 [run]): the orig provider detected a literature state itself (orig `providers.py:702-757`); `R/a102/providers.py:595-615, 686-692, 829` renders it only when the caller passes `prompt_renderer`. | Put the helpers in a module beside the a102 tests and have `complete` call `complete_with_presentation(..., prompt_renderer=<a102 literature renderer>)`. Not tried. | No. |

### C8. `test_literature_structure_assessments` (2) (`test_wiring`)

Line 12 `from test_literature_perturbation_integration import binding_for` resolves through the pytest `pythonpath` to
`R/a106/tests/test_literature_perturbation_integration.py:90-94`, which builds an **a106** `LiteratureEpisode`. a106 has no
structure storage, so the a102 arguments are rejected (`representation_error`, `additionalProperties`). Line 9 also imports
the top-level `ContractError` (C2). [read]

Minimal fix: build the binding in the test from a102, as `R/a102/tests/test_literature_structure_integration.py:76-78` does
(`LiteratureEpisode(WorkflowServices(host), structure_population=True)` with the a102 `ToolRegistry`,
`EpisodeBindingRegistry`), and import `ContractError` from `...root.a102.domain`. 2 passed with this change (run 22). [run]
Scientific: no.

### C9. `test_a103_context`, remaining three (`stale_test`, all older than the reorganisation)

The test file differs from orig only in import lines (`git diff fb1e4d9ba:tests/test_a103_context.py`), and the product
code on each path is the same text as orig. [read] That these failed before the reorganisation is [inferred]; orig was not run.

| Test | Cause | Minimal fix | Scientific? |
|---|---|---|---|
| `test_synthesis_returns_received_retained_context_without_new_measurements` | Builds a legacy report from `{**initial_report(), 'context_summary': ...}`. `initial_report()` returns `{}` (`R/a103/a103_investigation.py:60-61`, same in orig) and `resolve_report` validates any report carrying `context_summary` against the full legacy schema (line 185-186), so `functional_support` is missing. | Supply every legacy field in the test, or retire the legacy-form case. | Test only. It concerns how A103 context credit is reported, so the owner should choose which form the test keeps. |
| `test_measurement_redelivery_keeps_credit_without_admitting_an_unsupported_function` | Same; `limitations` is missing, so the schema error precedes the `ContractError` the test expects. | Same. | Same. |
| `test_runtime_parent_receives_exact_component_operands_from_automatic_grading` | The hand-built `SimpleNamespace` workflow (test line 268) has no `shared_information_repository`, which `Workflow.receive_tool_attributions` calls (`R/a103/runtime.py:2705`; orig `runtime.py:3816-3845` the same). Adding it moves the failure to `StopIteration` on the expected need (run 24 [run]); not pursued further. | Rework the fake, or drive a real `Workflow`. | No. |

## 3. Counts

| Cause | Classification | Visible failures | Fix verified by running? |
|---|---|---|---|
| Shared capacity ledger across units, differing version stamps | environment | 14 | Conflict gone in 7 fresh runs; runner change not tried |
| C2 wrong `ContractError` class | test_wiring | 32 | Yes |
| C3 stale implementation pins (A105) | product_defect, flag | 3 (+2 hidden) | No |
| C4 monkeypatch string / steering substring | test_wiring 1, stale_test 1 | 2 | String fix yes |
| C5 catalog count / fake services | stale_test | 3 | Count yes; other no |
| C6 a102 literature reconstruction missing | product_defect | 3 | No |
| C7 structure integration | test_wiring+unclear 2, stale_test 2 | 4 | Partly; neither fully passes |
| C8 a106 helper used for a102 | test_wiring | 2 | Yes |
| C9 a103 legacy report / fake workflow | stale_test | 3 | No |

Hidden behind the 14 environment failures: 3 pass outright; 2 are test fixes that pass when applied (1b, 1f); 2 are C3;
6 are a106 feedback (stale keywords, then missing `detail` forwarding); 1 is a103 detection (wiring, then
`R/a103/homology_results.py:288`).

## 4. Not done

- No product file was changed, so none of the product repairs (C3, C6, 1a `detail`, 1g line 288) is tested.
- The `ValueError` in C7 row 1 and the `StopIteration` in C9 row 3 are not traced.
- Orig (`fb1e4d9ba`) was read, never run; "already failing before the reorganisation" is from identical code, not a result.
- Run directories `runs/claude_triage_triage_d_01` .. `_25` are disposable launcher output (run 21 was a single-test probe;
  runs 13-16 were invalid attempts where the copied test lost its fixture path and are superseded by 17-18).

## 5. Test-side fixes applied (2026-11-14, on the coordinator's instruction)

Test files only; no product file changed; no commit. Reruns: one file per launcher run, slot `triage_d`, each in its own
run directory (`runs/claude_triage_triage_d_26` .. `_40`), so no shared capacity ledger. Expected total written before
running: about 3 minutes. Measured: 137 s.

### Changes

| File | Change |
|---|---|
| `R/a105/published_evidence_assessment/tests/test_literature_channel_original_294.py:134` | monkeypatch string prefixed with `gene_annotation_episode.episodic_workflow.root.a105.library.` |
| `R/a105/published_evidence_assessment/tests/test_literature_channel_binding_188.py:226` | same prefix; the `'source_'` assertion at line 362 left failing as instructed |
| `R/a105/published_evidence_assessment/tests/test_literature_wst8_method_contrast_291.py:189` | `_v2` to `_v4` |
| `R/a106/published_evidence_assessment/tests/test_a106_final_selection_feedback.py:26,75,117` | removed `rate_population=True, a106_intervention=True` |
| `R/a103/tests/test_a103_real_detection.py:22,24-26` | `AcquisitionError`, `HomologyResults`, `NativePhmmerInput`, `LocalJobPolicy`, `prepare_job`, `start_prepared`, `wait_job` now from the `R/a103` copies |
| `R/a102/tests/test_literature_structure_storage.py:8`, `R/a103/tests/test_a103_context.py:13`, `R/a103/tests/test_a103_channels.py:7` | `ContractError` (and the names imported with it) from the axis `domain` |
| `R/a102/tests/test_literature_structure_assessments.py` | `binding_for` defined in the file from the a102 `LiteratureEpisode(..., structure_population=True)`; `ContractError` from `a102.domain`; the import from the a106 test module removed |
| `R/a102/tests/test_literature_structure_integration.py` | `literature_home_factories()` supplies one factory per a102 literature home (seven, in `create_binding_tree` order) at the former line 164; two tests retired |
| `R/a105/published_evidence_assessment/tests/test_literature_native_rate_operand_information.py` | one test retired; line 147 not changed (see below) |

`git diff --stat` for these files: 11 files changed, 44 insertions(+), 140 deletions(-).

### Not changed, with the reason

- `R/a103/homology_results.py:288` — **left as is.** The gate was "the worker files exist at exactly one place inside a103
  or shared root". Five of the six exist in two places: `R/a103/<name>` and `R/library/<name>` (`phmmer_result_worker.py`
  only in `R/a103/`). The two copies of each are byte-identical, and orig line 288 reads `Path(__file__).with_name(name)`
  (siblings of the module), so `parents[3]` to `parent` looks right, but the "exactly one place" condition is not met, so
  I did not edit product code. `test_a103_real_detection` therefore still fails there.
- `test_literature_native_rate_operand_information.py:147` (`== 19`) — **left failing.** The gate was "22 is the number of
  entries the test then checks individually". It checks one entry (`literature.rate.source.populate`), not 22. Also, "19"
  matches no state in the repository history: the catalog had 28 unconditional entries when the test was first imported
  (`b5d7c94e2`) and at orig. The a105 copy has 22: the orig 28 minus `literature.perturbation.populate`,
  `literature.structure.populate`, `literature.reaction.populate`, `literature.reaction.source.populate`,
  `literature.partner.populate`, `literature.partner.source.populate`. So no entry is "new"; six left a105.
- `R/a106/published_evidence_assessment/source_operations.py`, the pin tables (C3), `R/a102/episode_composition.py` (C6),
  the a103 legacy-report tests (C9): untouched as instructed.

### Retired tests (rows appended to `runs/claude_inputs/failure_triage/retired.tsv`)

| File | Test | Reason |
|---|---|---|
| `R/a105/published_evidence_assessment/tests/test_literature_native_rate_operand_information.py` | `test_actual_c7_dispatch_is_still_one_selected_native_repository_call` | Injects a fake repository through `services.literature_rate_repository`; the a105 episode now builds it from `services.workflow.store`, so the seam is gone. |
| `R/a102/tests/test_literature_structure_integration.py` | `test_structure_task_and_conditional_meanings_repeat_at_provider_boundary` | Helpers live only in a parked test and rely on the provider detecting literature state, which `R/a102/providers.py` no longer does. |
| `R/a102/tests/test_literature_structure_integration.py` | `test_parent_keeps_own_task_and_receives_physical_panel_once` | Same helpers, same reason. |

### Before / after per test module

"Before" is the full run `runs/claude_tests_leaf_up_20261114_02` (junit); "after" is the single-file rerun.

| Test module | Before passed/failed | After passed/failed | Run |
|---|---|---|---|
| `test_a106_final_selection_feedback` | 0 / 6 | 1 / 5 | 26 |
| `test_literature_channel_original_294` | 0 / 3 | 3 / 0 | 27 |
| `test_literature_channel_binding_188` | 24 / 3 | 26 / 1 | 28 |
| `test_literature_assay_grading_uncertainty_324` | 27 / 1 | 27 / 1 | 29 |
| `test_literature_a105_channel_ion_worksheet_298` | 0 / 1 | 0 / 1 | 30 |
| `test_literature_wst8_method_contrast_291` | 2 / 1 | 3 / 0 | 31 |
| `test_a103_real_detection` | 1 / 1 | 1 / 1 | 32 |
| `test_literature_structure_storage` | 9 / 28 | 37 / 0 | 33 |
| `test_literature_structure_integration` | 0 / 6 | 0 / 4 (2 retired) | 34 |
| `test_literature_structure_assessments` | 0 / 2 | 2 / 0 | 35 |
| `test_literature_assay_grading_inputs` | 25 / 3 | 25 / 3 | 36 |
| `test_literature_native_rate_operand_information` | 9 / 3 | 9 / 2 (1 retired) | 37 |
| `test_a103_context` | 34 / 6 | 37 / 3 | 38 |
| `test_a103_channels` | 1 / 1 | 2 / 0 | 39 |
| `test_a102_parent_coordination` | 0 / 1 | 0 / 1 | 40 |
| **Total** | **132 / 66** | **173 / 22 (3 retired)** | |

### What still fails (22) and why

| Count | Test | Cause | Status |
|---|---|---|---|
| 5 | `test_a106_final_selection_feedback` (all but `...received_source...[False]`) | `KeyError: 'detail'`: `R/a106/published_evidence_assessment/source_operations.py:114` does not forward the `detail` the storage builds | Owner question (A106 feedback reporting) |
| 1 | `test_literature_channel_binding_188::test_recurring_task_and_scoped_steering_...` | Asserts `'source_'` absent from steering; the fixed preamble contains `source_ref` | Left failing as instructed |
| 1 | `test_literature_assay_grading_uncertainty_324::test_existing_summary_sd_variance_...` | `summary_precision_prospective_dependency_mismatch` (C3) | Owner question (A105 pins) |
| 1 | `test_literature_a105_channel_ion_worksheet_298` | `ion_discrimination_prospective_dependency_mismatch` (C3) | Owner question (A105 pins) |
| 3 | `test_literature_assay_grading_inputs` | `product_coupling_prospective_dependency_mismatch` x2, `literature_optical_implementation_dependency_mismatch` x1 (C3) | Owner question (A105 pins) |
| 1 | `test_a103_real_detection::test_real_complete_search_scoped_absence_unknown_and_cooccurrence` | `FileNotFoundError .../gene_annotation_episode/phmmer_format.py` from `R/a103/homology_results.py:288` | Product line not edited: gate not met (see above) |
| 2 | `test_literature_structure_integration::test_original_source_selected_cells_and_saved_only_binding_reconstruction` | `unavailable_binding`, `R/a102/episode_composition.py:144-145` (C6) | Left as instructed |
| 2 | `test_literature_structure_integration::test_structure_selected_in_ordinary_child_and_received_once` | Seven homes now bound, `KeyError` gone; workflow ends `source_failed` at decision 0 (`selected_operation_failed`, `ValueError`), origin not traced | Recorded failure |
| 2 | `test_literature_native_rate_operand_information::test_actual_catalog_schema_meanings_...` | `assert 22 == 19` | Left: gate not met (see above) |
| 3 | `test_a103_context` (`test_synthesis_...`, `test_measurement_redelivery_...`, `test_runtime_parent_receives_...`) | Legacy report built from `initial_report()` = `{}` (x2); fake workflow without `shared_information_repository` (x1) (C9) | Left as instructed |
| 1 | `test_a102_parent_coordination` | `unavailable_binding` (C6) | Left as instructed |
