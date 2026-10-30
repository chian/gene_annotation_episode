# C3 native execution and retained calculation handoff

This is implementation evidence for B-L124, not a new goal or a whole-tool completion claim. The original attachment is authoritative: `/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`, SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`. Its objective and all 16 principles were reread verbatim after the actual native/worker examination and again before this handoff. The current agreed request, numerical examples, native/worker contracts and 441 corrections were also reread. GOAL.md was not read or used. No literature, annotation-credit, goal, shared environment or episode-prompt file was changed.

## Implemented files and ports

Exact six production file hashes and test/runner pins are in [PRODUCTION_PINS.json](PRODUCTION_PINS.json). The files are under `gene_annotation_episode`:

* `native_chromatin_interaction_contracts.py`: closed software/job/input/attempt validators, pure output/compiler helpers, and original bundle/population-seal joins.
* `native_chromatin_interaction_driver.py`: finite selected Cooler extraction; immutable full source staging; one C1 population call at a time; closed table hashes and population seals before the next population; original outcome/log retention.
* `native_chromatin_interaction_local.py`: original pending PracticalState reservation and same-handle reconstruction under existing native_lifecycle.
* `chromatin_interaction_result_worker.py`: supplied retained data only; C1 table context and sheet construction followed by C2 calculation and exact projection; complete explicit output declarations.
* `native_chromatin_interaction_preparation.py`: explicit source/dependency freeze and the ordinary bounded worker lifecycle/capture. It does not admit scientific results or grant receipt authority.
* `native_chromatin_interaction_tool_info.py`: actual name/description/resources/instructions and launch → selected launch_local commission route, Cooler schema 3 only.

Public integration signatures are:

```python
validate_chromatin_software(value) -> dict
validate_chromatin_bindings(values) -> list[dict]
validate_chromatin_job(value) -> dict
validate_chromatin_requested_job(value) -> dict
chromatin_interaction_execution_schema(kind, *, bindings=None) -> dict
requested_job_from_chromatin(job, *, environment=None) -> dict
chromatin_output_files(request) -> list[dict]
validate_chromatin_run_plan(value) -> dict
chromatin_driver_argv(plan) -> list[str]
chromatin_environment(job, *, attempt_directory, environment=None) -> dict
validate_chromatin_population_seal(value, *, plan, population) -> dict
validate_chromatin_bundle(value, *, plan) -> dict

freeze_chromatin_software_binding(*, module_root: str,
    snapshot_directory: str, python_executable: str | None = None) -> dict
prepare_local_chromatin_interaction(state, operation_key: str, *,
    root: Path, policy: LocalJobPolicy) -> NativeJobHandle
local_chromatin_interaction_plan(assignment: dict, execution_id: str) -> dict
run_chromatin_interaction_driver(plan) -> dict

build_native_chromatin_worker_plan(*, directory, original_plan, bundle,
    files, selector, source_action_receipt_ref, writer_closure_receipt_ref,
    driver_state, failures) -> dict
build_saved_chromatin_worker_plan(*, directory, sheet_bundle, selector) -> dict
validate_chromatin_result_worker_plan(value) -> dict
validate_chromatin_result_worker_result(value) -> dict
run_chromatin_result_worker(plan) -> dict
prepare_chromatin_result_worker(store, *, plan, policy) -> dict
validate_prepared_chromatin_worker(store, value, *, plan) -> dict

chromatin_interaction_tool_contracts(bindings: list[dict], *,
    resource_kind: str, resource_id: str) -> list[dict]
chromatin_interaction_tool_information(bindings: list[dict], *,
    resource_kind: str, resource_id: str) -> list[dict]
```

The environment arguments are required in practice; `None` raises `explicit_runtime_environment_required`. The exact closed requested Environment has PYTHONPATH, PYTHONHOME, PYTHONNOUSERSITE, PYTHONSAFEPATH, PYTHONDONTWRITEBYTECODE, TMPDIR, TMP, TEMP, XDG_CACHE_HOME, PIP_CACHE_DIR, OPENBLAS_NUM_THREADS and OMP_NUM_THREADS. Realized temporary/cache paths are confined to the original attempt. The realized environment also fixes HDF5_PLUGIN_PATH to an unbound attempt-local directory. The nominal and realized commands use the approved `-B -S -m gene_annotation_episode.native_chromatin_interaction_driver` with the exact original plan path.

`PopulationSeal.native` retains the C1 header, so earlier sealed populations require no original HDF5 reread. Seal validation checks selected region, population key, normalization, original input files, source/header identity, all five roles and exact declarations. Every producer path is under the selected output_prefix. Progress stdout is visible and fsynced after each seal, with actual timestamp, ordinal, extent and observed stored-row count. It is hashed only after closure. Unsealed attempts cannot be silently rerun.

Native worker inputs must have exactly `original_plan.outputs[:-1]` order. An actual valid bundle supplies all exact bundle declarations; earlier valid population seals supply their exact table declarations if the final bundle is missing. All retained file identities are checked against the supplied bytes. The worker preserves complete independent populations when another retained table is lost. Missing weights leave raw measurements intact and make the selected normalization unavailable; lost axes/contact/state data revoke complete-read/implicit-zero claims. Original seals and controls are unchanged.

The saved plan has only version, mode, directory, sheet_bundle and selector. It contains no original native input path, producer executable or resolver. When the authentic saved sheet is available, missing table attachments leave that sheet unchanged and prevent recalculation, while every selected table gets an explicit present/absent output declaration. Worker output order is sheet, components, projection, diagnostics, then all five table roles per population in sheet order. The final worker-result.json is a separate closed record. Produced describes emitted files, not scientific completion.

## Actual dependency binding

The selected interpreter is the existing reference Python 3.12.3, binary SHA256 `e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`. No shared environment was modified. Source snapshots and every selected installed distribution file are pinned by actual bytes. The final native binding records 112 project implementation files and the actual packages below:

| Distribution | Loaded version |
| --- | --- |
| numpy | 2.5.0 |
| h5py | 3.16.0 |
| jsonschema | 4.26.0 |
| attrs | 26.1.0 |
| referencing | 0.37.0 |
| rpds-py | 2026.9.1 |
| jsonschema-specifications | 2025.9.1 |
| typing-extensions | 4.15.0 |
| idna | 3.18 |
| jsonpointer | 3.1.1 |

Reference site-packages precedes the auxiliary root schema packages. Standalone modules have explicit import-directory handling. The producer verifies loaded module paths, installed versions, interpreter and all source/dependency byte pins before and after extraction; an external module loaded from site-packages but absent from the binding rejects. The result worker uses its own actual frozen source/interpreter/dependency intent; it does not require h5py to calculate from retained tables. Full file lists are in each `SOFTWARE_BINDING.json`, not symbolic future hashes.

## Executed evidence

Every import/test/native execution used existing local_jobs/native_lifecycle with 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time allocation. Each check directory retains its immutable source snapshot, selected request, original handle, stdout/stderr, terminal receipt and before/after source/binary pins. Native child handles were followed to terminal; observation delay caused no restart. All completed check receipts report unchanged pins. C1/C2 source versions are embedded in the selected software bindings.

`check007` passed 14 tests in 199.73 seconds. It exercised real serialized synthetic HDF5 from packet440 through the actual pinned producer and C1, actual complete Store capture, this worker, C1's table loader/sheet and C2's calculations/projections. Verified values include raw contact 6 / distance mean 4 = fold 1.5, weighted contact 6 / mean 7 = 6/7, and all five insulation windows with mean 3.4, variance 3.84 and a 20 bp adjacent-boundary domain. The actual occurrence keys and unknown insulation-only element-reference relation are retained rather than replaced by the symbolic439 fixture labels.

That run also verified:

* A real saved worker execution with original native inputs and producer attempt removed, changed fold threshold, unchanged original sheet bytes and no native reexecution; explicit missing saved data and strict native/saved plan isolation.
* Actual worker prepare/start/wait/capture and replay using the original handle.
* Actual changed/missing supplied inputs with unknown population shape/counts and no zero matrix.
* Real PracticalState.begin → LocalPracticalOperations.execute(start) → recorded original receipt, reopened original execution, status/collect, exact-identity observe_execution and bounded read_output. Unbound software/mode, foreign owner and non-original path reject; reopening cannot dispatch a duplicate job. These are component checks, not parent scientific delivery.
* Loss of bins, contacts or weights in one of two different selected populations, preserving the other complete population and exact failure/normalization qualifications.
* Actual cancellation after the first of 30 originally selected populations was sealed, visible progress log, byte-identical surviving seal, no final bundle, refusal to rerun an unsealed attempt and retained partial result processing.

`check008` exercised the final stricter population joins and secure preparation lock. Five targeted tests passed: actual wrong Python/dependency pins, worker lifecycle/replay, strict original-plan joins and the real bound tool commission schema. Its sixth test failed because the test expected a scientific negative count to make a completed native read return nonzero. The actual bundle correctly preserved complete read extent plus a located native_value_negative qualification. This mistaken assertion was corrected; no production behavior was weakened.

`check009` passed the malformed-native test in 21.00 seconds. It edits a copied HDF5 native count to -3 before capture, executes the actual producer, and confirms the worker retains the negative value and original source row 1/source_block -1 with the located scientific failure. Execution success and numerical validity remain separate.

`check010` passed one final targeted check in 21.43 seconds with the final production bytes. It removes one actual canonical contacts table before original Store capture, verifies the actual capture outcome is unavailable, and confirms the worker reports input_unavailable while preserving the independent complete population. This covers the final correction that distinguishes an unavailable capture from an observed digest mismatch. No signatures, numerical formulas or schemas changed.

Earlier failed attempts remain retained: check001 exposed the exact closed Environment mismatch; check002/003 compared symbolic fixture keys/reference assertions with actual C1 occurrence facts; check004 used an exact float comparison for a final-bit square-root difference; check006 supplied an incomplete Binding fixture that omitted required operation/resource_kind. check005 passed 10 earlier checks. The final test file collects 19 cases. Their successful evidence is distributed across check007, the five successful check008 cases, check009 and check010; this is not a claim that one final 19-test suite was run.

## Boundaries and remaining work

Only supplied Cooler schema3 is supported here. HIC is unfinished. Cooler the Python package is not installed or claimed; extraction uses the actual selected h5py implementation. Inputs in these tests are synthetic matrices serialized as real HDF5 native files, not independent biological experiments. Production memory/scratch kill paths were not deliberately forced; actual resource enforcement and explicit policy rejection were observed.

Preparation authenticates each supplied retained path through the existing `retained_native_file` helper before staging. A Store artifact already missing or corrupt at that custody check raises its existing NativeFileCaptureError; the owning host must record that explicit input failure. This preflight does not invent a worker execution receipt, retry the producer or reacquire data. The worker's structured partial path covers missing supplied table streams when a worker plan can actually be executed.

Root and its capture owner still own complete original-action/received-input authority, actual capture admission, result-host validation of sheet/table/component/projection joins, requested typed parent delivery, credit, practical endpoint and full Workflow verification. C3 fixture source-action labels deliberately do not claim that authority. Parent selection must use the appropriate name/description/resources while the selected child receives substantive instructions and callable contracts. No new TASK/STEERING template or per-tool monitoring judge was coded. Worker-produced files, native success, numerical qualifications, requested delivery and completion remain separate. No whole-tool tally was incremented.
