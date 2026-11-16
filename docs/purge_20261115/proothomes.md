# proothomes: shared-root episode homes and shared-root tests (15 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/` homes `execution_job_submission`, `execution_monitoring`,
`execution_result_acquisition`, `homology_job_monitoring`, `homology_job_submission`, `homology_result_acquisition`,
`hpc_coordination`, `hpc_job_execution`, `legacy_annotation`, `local_job_execution`,
`published_evidence_assessment`, `resource_job_submission`, `resource_result_acquisition`, `scientific_process`, and
`tests/`. Sub-agents could not be started (concurrent sub-agent limit reached), so the whole area was done by one agent.
Other agents (h3, h4, ptests and others) edited files inside this area at the same time; the totals from `git` below
include their edits.

## Specific item: `legacy_annotation` is live despite its name (left in place, not renamed)

It is the home of the current `improvement` role ("iterative scientific annotation improvement",
`legacy_annotation/goal.py`), whose grain the default runtime declares (`root/runtime.py:22`
`grain_names = ('annotation', 'improvement')`). Current composition paths that build episodes from it:

- `root/execution_family_composition.py:12,16-17,21,32-37,60-72,95-100,123-128,151-163,186-191` (launch/results families)
- `root/hpc_service_composition.py:4,12-15,33-36` (HPC coordination, prediction, allocation)
- `root/monitor_binding_catalogue.py:6,10-11,17` (monitor bindings)
- `root/predefined_parent_routes.py:10,13,18,62` (`HOST_PARENTS`, literature head, HPC routes)
- `root/task_selection.py:12-14`, `root/continuation_observation.py:17-19`, `root/credit_projection.py:13-14,44-45`
  (task source, controller and credit of an `improvement` path)
- `root/literature_families.py:12`, `root/literature_child_message_owners.py:31-37,51-55`,
  `root/operational_child_message_owners.py:76`, `root/predefined_child_message_owners.py:91,179`
- `root/episode_bindings.py:520,548-549`

Named after that home and therefore also left: classes `LegacyHomology*` and the stamp
`root_legacy_private_homology_v1` / error `original_legacy_improvement_identity_required` in
`legacy_annotation/homology_{job_submission,job_monitoring,result_acquisition}/` (selected by
`execution_monitoring/tests/test_private_context_parent_identity.py:77-79` for an `improvement` lineage).
No handoff rows were needed for it. Its backward-facing content was removed like every other home.

## Removed, by class

Product code (homes): 676 files changed, 2,131 lines removed / 1,408 rewritten (git, excluding inventories and tests).

1. Parameters, branches, names for the past
   - model-supplied quote acceptance: `_accept_legacy_quotes=True` at 146 `workflow.reasoning_action_schema(...)` /
     `catalog(...)` call sites; in the 21 literature `task.py` copies the `_accept_legacy_quotes` parameters of
     `reasoning_action_schema` and `catalog`, `accept_reasoning_action_schema`, and 42 `allow_legacy_quote=True` uses.
   - old expanded-assignment transport: `recorded_transport` (158), `_unproven_direct_response_index` (158),
     `unproven_replay=` (158).
   - old wait/completed-inputs mode: the `execution_binding / wait_inputs_binding_v2 / completed_action_inputs_version`
     condition around `pending_work_after_action` (158 `task_actions.py` copies) and the `None` capture alternative
     (`legacy_annotation/yield_estimator.py`).
   - flux control version selection `control_version=control['version']` (36 `operations.py` copies).
   - names only: `old_history_guidance` -> `history_guidance` (316), `historical` verdict variable (60).
2. More than the current record form (all in `scientific_process/`): `LEGACY_SELECTION_VERSION`,
   `LEGACY_RETURN_VERSION`, `_LEGACY_SELECTION` (schema `anyOf`), `_LEGACY_REVISION_ARGUMENTS`, the v2-return upgrade,
   the name-only tool resolution branches (`tools.py`, `assignments.py`, `report_generation.py`,
   `source_contracts.py`), `legacy_report_schema` of a102 / a103 / a104 and of the component report with its `paths`
   branch (`report_validation.py`, `received_component_reports.py`), and the names in 18 import lists.
3. Historical name table: `scientific_process/source_contracts.py` `_IMPLEMENTATION_FILES` ("retained original
   compatibility declaration", unused; 46 lines) and its 18 imports.
4. Saved copies of old source and captured outputs: 9 helper modules holding old module text
   (`operational_original_runtime.py`, `terminal_original_{checks,persistence,next,credit}.py`,
   `literature_execution_original_contract.py`, `fluorescence_original_intent.py`,
   `original_scientific_native_sequence.py`, `homer_original_argv.py`); 622 fixture files (`*.py.source`, `.sha256`
   lists, `*_identity`, `root_policy_original`, retained run stores such as `circular_dichroism_*`,
   `itc_parameter_delivery`, `retained_workflow`, `flux_balance/practical217` and `producer_emissions`, `rfam/*_workflow`,
   `restriction_mapping` pins, and the two home `tests/fixtures` trees).
5. Tests: 32 whole test files, 53 further test functions or parameter cases, 46 helper / probe modules (about 17,000
   lines of Python). List with reasons: `runs/claude_inputs/purge/proothomes_deleted_tests.tsv`.
6. Narratives and inventories: 158 `ownership.md`, 152 `ownership_inventory.json`, 6 `implementation_inventory.json`
   (no code reads them), `tests/FIXTURES.md`, `tests/fixture_locations.json` (about 18.6 million lines).
7. Narration: docstrings of three test modules and two comments in `scientific_process`. Comment-only edits of other
   product files were not made.

Totals for the area from git (all agents): 1,744 files deleted, 719 modified.

Renamed (plain `mv`): `test_root_historical_finding_progress.py` -> `test_root_finding_progress.py`,
`test_root_historical_scientific_binding.py` -> `test_root_scientific_binding_resume.py`,
`historical_scientific_support.py` -> `scientific_record_support.py` (behaviour tests of current resume and finding
progress; only the names were for the past).

## Live despite its name (kept, with evidence)

- `legacy_annotation` and the `LegacyHomology*` names: see above.
- Literature record "versions" that are produced side by side today, not successive forms:
  `literature_perturbation_record_v1/_v2` (`root/literature_perturbation_storage.py:22,112`),
  `literature_rate_population_record_v1/_v2` (`root/literature_rate_storage.py:23,31,231`),
  `literature_reported_rate_observation_record_v1/_v2` (`root/literature_rate_observation_storage.py:18`,
  `root/library/literature_rate_observation_return_contracts.py:27`), `literature_compiled_assay_record_v1/_v2/_v3`
  with separate namespaces (`root/library/literature_compiled_assay_declarations.py:3-10`); read in the 21
  `numerical_report_projection.py` copies.
- `native_blast_utility_result_selector_v1/_v2` in 12 `execution_result_acquisition/from_parent.py` copies: the
  shared library still selects a result form per selector version
  (`root/library/native_blast_utility_results.py:47,51`); follow whatever prootlib decides.
- `receipts.known(..., baseline=True)`, "historical cases" of the HPC time model, "older selections" in prompts:
  records of the same run.

## Kept, and why

- `scientific_process/saved_identity.py:46,60,109,114` calls of `scientific_binding_compatible` (digest compatibility
  table lives in `root/episode_composition.py:250`, area proot; notice row written).
- Entries `literature_assay_grading_legacy_cells_v1.json` and `literature_product_kinetic_relocation.py` in the three
  `definition_inputs.py` file lists: the files belong to area proot and the lists to the pin mechanism (agent h4).
- Library `entry_version` branches and `tool_library.supports_tool_info` in `scientific_process`: they depend on which
  forms proot's `scientific_tool_library` and the published library keep.
- Shared axis test stubs (`tests/hpc_*_behavior.py`, `tests/monitor_*_behavior.py`) still carry
  `wait_inputs_version=None, completed_action_inputs_version=None` next to the current `pending_work` port, because
  axis copies of `task_actions.py` may still read them. Remove once every axis has dropped the old mode.
- The text "distinct from the legacy table view" in 21 `numerical_report_fields.py` copies is model-facing contract
  text; left unchanged.

## Points to check

- A103 in `scientific_process/report_validation.py`: the only call of a103 `resolve_report` was for the legacy field
  set, so it went with it; the current a103 `report_schema()` form was never resolved here. If that resolution is
  wanted for the current form it has to be added deliberately.
- Product files were edited, so any fixed digest pin on them no longer matches (pins were not touched; h4 removes the
  mechanism).
- By mistake I ran one `git mv`, which staged a rename. I reversed it at once with `git restore --staged` on those
  two paths only; the index is as it was (nothing staged).
- Fixtures were deleted only when no Python file in the repository names them. Empty directories under
  `tests/fixtures` (untracked by git) were removed by the same sweep.
- 20 GiB test policies in nine test files now use `workflow_budget.ENVIRONMENT_BOUNDS['memory_bytes']`.

## Verification

- Import check, all 4,712 home modules: `{}` (runs `claude_proothomes_011` and, after the last edits, `_016`).
- `pytest --collect-only` over `root/tests` and `root/execution_monitoring`: 1,763 tests collected, 0 errors
  (`claude_proothomes_017`; five collection errors in the run before were fixed or were top-level helper modules that
  ptests repaired).
- Test files run one at a time (before = latest earlier result; after = now):

| file | before | after |
|---|---|---|
| test_annotation_task_boundaries.py | 12 passed (7 failing after proot's change) | 5 passed |
| test_annotation_iterator_boundaries.py | 6 passed (4 failing after proot's change) | 6 passed |
| test_root_registry_lineage.py | passed | 17 passed |
| test_private_binding_identity.py | 79 passed, 2 failed | 70 passed, 2 failed |
| test_shared_local_resource_admission.py | passed | 17 passed |
| test_root_descriptor_composition.py | passed | 21 passed |
| test_provider_private_presentation.py | passed | 24 passed |
| test_execution_closed_credit.py | 1 failed, 42 errors | 1 failed, 40 errors |
| test_root_finding_progress.py (renamed) | passed | 16 passed |
| test_root_scientific_binding_resume.py (renamed) | passed | 14 passed |
| test_shared_emdb_responses.py | passed | 24 passed |
| test_private_prompt_transport.py | passed | 21 passed |
| execution_monitoring/tests/test_private_context_parent_identity.py | passed | 33 passed |
| test_root_episode_boundary.py | 1 passed, 4 failed | 1 passed, 4 failed |
| test_execution_recorded_results_assignment.py | 27 failed | 26 failed |
| test_bvbrc_minhash_commission_replay.py | 31 failed | 30 failed |
| test_signed_evidence_root.py | 21 passed, 10 failed | 21 passed, 10 failed |
| test_tf_binding_tools.py | 19 passed, 5 failed | 19 passed, 5 failed |
| test_root_native_factory.py | passed | 7 passed |
| test_terminal_profile_dispatch.py | passed | 3 passed |

No file got worse; the remaining failures were failing before and were not investigated here.

## Handoffs

Applied (rows addressed to `roothomes` / `proothomes`, and the `proot` rows that name files of this area):
`_accept_legacy_quotes` and `control_version=` call sites; `unproven_replay` / `recorded_transport` /
`_unproven_direct_response_index`; `LEGACY_SELECTION_VERSION` / `LEGACY_RETURN_VERSION`; `legacy_report_schema`
(prootlib, pa102); `historical=` stub in `test_fluorescence_episode_routing.py`; `YieldParameters(100, 50)` in seven
test files; `tool_info=True` in `scientific_head_boundaries.py`; 51 imports of deleted top-level modules re-pointed to
`root` / `root.library` in 39 files; old-mode stubs in `test_annotation_task_boundaries.py` (3 tests deleted);
`fluorescence_prepared_workflow_support.py` and `test_bvbrc_genome_alignment_host.py` deleted;
`test_native_genomic_overlap_shared.py` (h3 notice) ended with no tests and was deleted;
`test_shared_local_resource_admission.py` older saved-form cases were already gone.

Written (14 rows): ptests (2: `fluorescence_workflow_support`, `evidence_root_fixture` importers), ptop (2:
`examples/a101_a102_root_mock.py`, `pyproject.toml` package-data and test paths), proot (2: `tool_info` parameter,
digest compatibility table notice), pa101-pa106 and pa108 (7: `tool_info` parameter), pa103 (1:
`legacy_report_schema`).
