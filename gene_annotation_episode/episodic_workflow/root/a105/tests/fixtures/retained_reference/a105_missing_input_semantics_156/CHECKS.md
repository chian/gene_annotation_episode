# 156 executed checks

Commands use `.venv/bin/python -m pytest -q` in the repository. Results overlap;
these counts are engineering checks, not counts of assays or scientific coverage.

1. Initial focused invocation:
   `tests/test_literature_missing_input_semantics_156.py tests/test_literature_activity_calculations.py tests/test_literature_assay_inputs.py tests/test_literature_assay_integration.py tests/test_literature_quantity_integration.py -k 'not primary_original_xml'`
   returned **155 passed, 2 failed, 1 deselected in 156.35 s**. Both failures
   were in the new cold helper, whose assertion incorrectly required absence
   of the `runtime_observations` table. Journal creates that table. The helper
   was corrected to require zero observation rows. No production correction
   was needed for these failures. The primary-source case was not run.

2. The corrected cold cases plus inherited-reader consumers:
   `tests/test_literature_missing_input_semantics_156.py::test_fresh_v2_selected_operation_typed_subset_and_cold_descriptor_reconstruction tests/test_literature_cell_possession.py tests/test_literature_rate_storage.py tests/test_literature_source_locations.py`
   returned **40 passed in 279.85 s**. These include synthetic selected source
   lookup, assay population and ordinary typed parent return, plus saved-cell
   possession/replay across existing repository implementations. The later
   native binding dependency update has its separate checks below.

3. Bounded native binding compatibility:
   `tests/test_a105_native_binding_dependency_142.py tests/test_literature_binding_interaction_storage.py::test_eight_actual_native_cells_closed_schema_and_full_source_custody`
   returned **19 passed in 56.52 s**. These authenticate exact untouched140/142
   dependency maps, reject mixed maps and unknown actual bytes, create a current
   selected synthetic binding operation, and generate actual typed receipts in
   both untouched historical runtimes before reopening them read-only in the
   current implementation without source/image reads or recalculation.

4. New synthetic quantity shared-loop case:
   `tests/test_literature_missing_input_semantics_156.py::test_synthetic_quantity_shared_loop_returns_missing_input_meaning_without_extra_observations`
   returned **1 passed in 16.00 s**. One child population returns the exact
   requested numerical subset with `correction_inputs_not_supplied`; parent
   commissioning, child population and parent reasoning produce exactly three
   actual controller observations. No annotation assessment is created.

5. Completed 156 file under the final five production files:
   `tests/test_literature_missing_input_semantics_156.py`
   returned **13 passed in 103.02 s**. This includes genuine pre-edit v1
   operations/schemas, omission-of-present-selected-input distinctions,
   unsupported-version rejection, v2 cold reconstruction and the synthetic
   quantity shared-loop case. During this invocation, root review requested
   moving the cold scientific-artifact guard before composition. The explicit
   subsequent two-case invocation below verifies that strengthened whole path.

6. Strengthened cold composition guard:
   `tests/test_literature_missing_input_semantics_156.py::test_fresh_v2_selected_operation_typed_subset_and_cold_descriptor_reconstruction`
   returned **2 passed in 25.16 s**. Scientific-artifact access is forbidden
   before host construction and `compose_episode_bindings`, through selected
   operation replay, typed validation and exact admitted-subset forwarding.
   Only the declared saved sheet payload/request artifacts may be read;
   parser/calculator calls are forbidden before composition as well.

No configured-model investigation, primary paper reading, W05 aggregation or
new scientific assay coverage is established by these checks.
