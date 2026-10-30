# Proposed flux-balance implementation boundary, 001

Status: boundary proposal only. No production implementation, solver execution, native-format verification, episode test, deployment, or progress-row change is claimed. This document specifies implementation interfaces; it does not restate or amend the user's goal. Authority is the complete user-supplied attachment whose SHA-256 is `f43e46c2433c44d320d1bbdb4e08f6cb85608a29d50911c2be28eb963581b6dc` and this agent's exact assigned task. Every proposed module, shape, name and signature below is **proposed**, not an existing callable.

Only fixed inventory key `biomni.tool.systems_biology.perform_flux_balance_analysis`, `/rows/238` in `research/tool_grader_inventory_2026-10-24/WORK_STATUS.json`, is mapped here. Its six implementation stages remain pending; its resource tests say `not established by this inventory`. No other systems-biology operation is included.

## 1. Source facts and the missing artifact seam

The complete installed source function is `reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/systems_biology.py:33–147`:

```text
perform_flux_balance_analysis(model_file, constraints=None,
                              objective_reaction=None,
                              output_file="fba_results.csv") -> str
```

It imports `cobra` and `pandas` inside the function. The import statements are outside its load/solve exception handlers. It chooses `cobra.io.read_sbml_model(model_file)` only for case-sensitive `.xml`/`.sbml`, `cobra.io.load_json_model(model_file)` only for `.json`, otherwise `cobra.io.load_model(model_file)`. Thus an arbitrary path suffix is not proof of a supported file format; the last branch is an identifier/loader branch. This inspection does not establish its repository resolution, download, cache, authentication, or default-model semantics: the required Cobra source is absent from the inspected environments. No model acquisition was performed.

For each supplied constraint, tuple unpacking occurs in the loop header, before its inner exception handler. Unknown reaction IDs or bound-setting failures are logged and the function proceeds with the remaining settings. An invalid objective is logged and the function proceeds with the model default. These are concrete request/effective-model mismatches, not successful application of the requested analysis. The function does not set `objective_direction`, a medium, an exchange convention, a solver, or a tolerance. Its message `maximize ...` is not evidence of the realized objective direction. Existing default objectives may have multiple terms; retain the actual realized coefficients and direction.

It makes one `model.optimize()` call. A returned status is logged without requiring `optimal`; optimization exceptions return the log early. The only objective retention is `solution.objective_value` formatted to six decimal places in that log. Dataframe creation, CSV writing, and later reporting occur outside the solve exception handler. A missing or invalid solution vector can therefore fail after optimization, and a CSV write failure is not necessarily returned as a structured result.

The CSV has exactly these native columns, in model-reaction order:

```text
reaction_id, reaction_name, flux, lower_bound, upper_bound
```

Fluxes are looked up as `solution.fluxes[r.id]`; bounds are the *effective* bounds after attempted modifications. The log reports active count from `abs(flux) > 1e-6` and at most ten reactions ranked by absolute flux, rounded to six places. Its text label omits the absolute-value qualification. This CSV/log pair omits stoichiometry, metabolite/gene associations, medium provenance, objective coefficients and direction, full-precision objective, solver identity/options/tolerances, complete load warnings, and a bound original-attempt manifest. No existing real native result was examined.

The source description in `biomni/tool/tool_description/systems_biology.py` matches those four parameters and describes a research-log return. It supplies neither a working episode binding nor the missing artifacts.

### Required producer repair

A mere outer wrapper around the returned string cannot recover the local `model` and `solution`. Do not call the original function and then optimize again to reconstruct omitted data. A source-derived native driver must retain the original and effective model plus the actual solution **within the same selected optimization attempt**, with exactly one optimize call for the selected ordinary FBA operation. It must preserve the actual source operation identity and publish the adapter implementation/version. It may reuse the same Cobra load/apply/optimize primitives; this is an artifact/result-path repair, not another numerical scoring implementation.

Bind supplied model bytes before parsing. Before solving, validate the complete selected set of bound/objective changes; if a requested change cannot be applied, return its specific failure and retained valid inputs rather than silently run a different/default problem. Historical source outputs with partial changes remain parsable and qualified by request/effective mismatch; they are not retroactively corrected. Resource infrastructure must never pick another model, objective, solver, medium, retry, or resource.

The new driver must not independently calculate active-count or residual summaries. `source_active_count` preserves an actual legacy supplied log value when present; new publication uses the shared calculator. The solver-reported objective remains a native value, separately checked by the shared calculator.

The driver must obtain and retain the selected solver implementation and actual available tolerances. Unknown remains null with a reason. Do not presume GLPK, a particular feasibility tolerance, biomass, maximum direction, `mmol/gDW/h`, or a default medium. Repository-identifier loading needs a separately selected and bound acquisition path retaining resolved bytes/version and source, before the ordinary calculation; it cannot hide acquisition in the pure reader/calculator. SBML and Cobra JSON are native input encodings feeding the *same* numerical contract.

## 2. Existing owners to reuse and explicit missing seams

A recursive source search in non-literature production Python for `perform_flux_balance_analysis`, `flux_balance`, `flux balance`, `reaction_flux`, `stoichiometric`, `linear_program`, `constraint_residual`, and `fba_` found no FBA sheet, calculator, result host, or binding. The only stoichiometry match was `chemistry.py`, whose complete Rhea/ChEBI source projections retain reaction equations/identities but do not solve or grade FBA. Its symbolic/implicit source coefficients cannot be substituted for a model's numerical stoichiometric matrix. `numerical.py` concerns yield estimation/continuation, not biochemical calculations. NMF residual components are a different numerical question and must not be relabeled as metabolic balance residuals.

Existing native NMF execution/result modules were inspected as the concrete lifecycle and return example, not as an FBA algorithm or a numerical authority to copy. They show the following existing seams:

| Existing owner and function | Existing behavior to reuse | FBA-specific missing input/output |
| --- | --- | --- |
| `ExecutionEpisodes.resource_tool_contracts()` | Caller-bound operation information with `invocation_route` to launch/resource child | Real FBA binding and substantive tool instructions; no source descriptor auto-enablement |
| `practical_execution_records.REQUESTED_JOB_SCHEMA`, `validate_assignment()` | Closed selected requested-job variants; preserves parent allocation/endpoint | `native_flux_balance` requested-job variant and validation |
| `LocalPracticalOperations.__init__`, `validate_assignment`, `_handle` | Configured native variants; existing `practical.job.start/status/collect`; durable original handle | Validated FBA software/model request, preparation and original-attempt plan; no generic argv masquerading as a graded FBA operation |
| `native_expression_nmf_local.prepare_local_expression_nmf` and `local_expression_nmf_plan` | Exact pending start reservation, immutable plan, and original-attempt authentication | FBA counterparts supply FBA artifacts, software closure, selected inputs; reuse existing native lifecycle rather than create a new loop |
| `ExecutionEpisodes._selector`, `catalog`, `execute` | Dispatches selected results work to the correct host | FBA result selector, host and target authentication |
| `NativeExpressionNMFResults._original/_saved/_worker/execute` | Closed-writer capture versus explicitly received saved sheet; one selected result operation; retained worker output | FBA artifact roles/parser/sheet/calculator/projection, with feasible/infeasible/unbounded solver outcomes represented faithfully |
| `execute_expression_nmf_worker()` | A finite decoding/calculation worker, separately retained sheet/calculations/projection/diagnostics | `execute_flux_balance_result_worker` calling exactly the shared FBA calculator |
| `project_nmf_result()` and `expression_nmf_return_views` | Selection/windowing from retained numerical values; named `x-source` facts | Closed FBA diagnostic/reaction/metabolite views; no duplicated arithmetic in publication |
| `ExpressionNMFReturns` | Original immediate-child commission/form validation; closure prefix; received saved-sheet authority; frozen historical returns | FBA typed fact sources and equivalent original-return authentication |
| `ExecutionEpisodes.received_report_sources`, `received_report_facts`, `validate_received_report`, `validate_report` | Fact-source declaration, received scientific-parent facts, validation against records | Register and consume FBA values in scientific parent and results forms |
| `ExecutionEpisodes._native_results_complete` | Native scientific result hosts own their exact delivery receipt; generic file-window completion is insufficient | FBA completion proof tied to the original requested result, never a positive-flux/optimality acceptance gate |
| `tool_grading_artifacts.retain_tool_grading`, `source_tool_grading_entries` | Existing custody of complete native-linked grading objects | Reuse if FBA publishes a source record; no separate file-only success masquerading as scientific values |

The future integration owner must trace all corresponding constructor/request/schema/input-version/reference/fact/admission/completion consumers before editing those shared files. This boundary identifies the seam and inspected concrete owners; it does not establish an FBA path through them. Preserve `evidence_axis`, `thought_pattern`, `child_tool_info`, ordinary shared `method_loop`, durable independent execution, and original parent scopes/forms. No new episode type or autonomous workflow is proposed.

Resource plan: this source calls a local Python solver. A configured local resource child is the first concrete invocation shape; no local run is authorized by this analysis task. No API service or HPC FBA deployment was found or verified. If the caller later supplies a real supported HPC resource, its existing resource-specific launch/monitoring must remain distinct and feed this same parser/sheet/calculator. Do not require every resource or substitute a machine. Aurora storage/account rules remain binding.

## 3. Proposed artifact and pure-function interfaces

Exactly one family owns `flux_balance_sheet_v1` and `flux_balance_calculations_v1`. Format/provider/resource variants do not introduce another sheet/calculator.

```python
# Source-specific pure decoding; no filesystem/network/solver calls.
parse_biomni_fba_csv(raw: bytes, *, model: EffectiveFBAModel | None,
                     source: File) -> ParsedFluxRows
parse_fba_capture(payloads: FBAArtifactPayloads, *, expected: FBAAttemptIdentity
                  ) -> ParsedFBABundle

# Pure shared numerical owner.
populate_flux_balance_sheet(*, bundle: ParsedFBABundle) -> FluxBalanceSheet
validate_flux_balance_sheet(sheet: FluxBalanceSheet) -> FluxBalanceSheet
calculate_flux_balance_sheet(sheet: FluxBalanceSheet, *,
                             parameters: FBACalculationParameters
                             ) -> FluxBalanceCalculations
project_flux_balance_result(sheet: FluxBalanceSheet,
                            calculations: FluxBalanceCalculations, *,
                            selector: FBAProjectionSelector) -> FBAProjection

# Existing execution/result ownership pattern; these are not pure calculators.
run_flux_balance_native(plan: FBARunPlan) -> FBANativeManifest
capture_flux_balance_native_files(store, *, original_plan: FBARunPlan,
    source_action_receipt_ref: str, writer_closure_receipt_ref: str
    ) -> FBACapturedFiles
execute_flux_balance_result_worker(plan: FBAResultWorkerPlan) -> FBAWorkerResult
flux_balance_tool_contracts(bindings, *, resource_kind: str,
                            resource_id: str) -> list[dict]
flux_balance_fact_sources() -> dict
select_flux_balance_return_facts(groups: dict, *, schema: dict) -> dict
```

`raw` bytes are supplied to pure parsing with the exact retained `File`; the parser checks SHA/size against those supplied bytes without opening files. The capture owner alone opens selected files and checks confinement, byte hashes, writer closure and original-job relationships. The full saved sheet is self-contained for the calculations below. Later recalculation accepts only an explicitly received saved-sheet artifact; it does not reacquire model bytes, import Cobra, solve, inspect current settings, or rewrite an earlier sheet/calculation/observation.

Native bundle roles (all state `present|absent|truncated|incompatible`, with a byte identity when present):

| Role | Required contents |
| --- | --- |
| `original_model` | Exact selected SBML/JSON bytes or exact acquired repository-model bytes; source format/version and acquisition receipt association |
| `selected_request` | Original supplied inputs, ordered constraint changes, objective choice, solver/configuration choice and explicit source metadata |
| `effective_model` | Complete reaction/metabolite/gene/compartment relationships, native model annotations, signed stoichiometry, effective bounds and objective; retained native export plus normalized numeric snapshot |
| `effective_problem` | Complete realized linear optimization problem or a preserved unsupported-form artifact; represented versus unrepresented constraints/variables explicit |
| `solution` | Full-precision native status/objective/flux values and actual solver identity/tolerances; any available solver diagnostics/claims, with explicit missing states |
| `flux_csv` | Original five-column CSV; exact rows retained including malformed rows and original indices |
| `native_log` | Exact returned research log when available; rounded summaries retain that precision. Original stdout/stderr retain their existing separate native-lifecycle custody |
| `manifest` | Sealed original-attempt identities, byte identities/formats of every role, actual source/software versions, request/application outcome and solver-call count |

The native producer must retain independent valid artifacts on error. Absent output never borrows an older run's file. The CSV and snapshot must join by the actual reaction ID within the same effective-model identity; original row position remains recorded for malformed/duplicate-row handling. A name, independently sorted array, or taxon does not establish a join. Gene-function association is only the source model's gene–protein–reaction (GPR) relationship; raw Boolean rule and exact gene IDs remain inspectable. Target sequence/gene links are optional supplied identities with provenance, never inferred from a reaction name.

## 4. Proposed closed data shapes

Notation: all record keys below are fixed (`additionalProperties: false`); arrays preserve stated source order. `Text` is bounded nonempty data text without control characters, not instructions/findings. `ID` is native identifier text. `Real` is a finite JSON number (booleans excluded); `Count` is a nonnegative integer. `?T` means null or T. Full unrestricted source metadata/log text lives only in retained artifacts. `Ref` is an existing authenticated artifact reference; referencing bytes does not grant episode access.

```text
ArtifactIdentity = {sha256: 64-lowercase-hex, size_bytes: Count}
File = {artifact_ref: Ref, sha256, size_bytes, format: ID}
SourceLocation = {file: File, record_index: ?Count, field: ID}
Unit = {native_text: ?Text, basis: supplied|native_model|unknown,
        source: ?SourceLocation}
Number = {value: ?Real, state: present|missing|nonfinite|invalid,
          native_token: ?Text, source: ?SourceLocation,
          precision: full_native|formatted_6dp|unknown}
Bound = {kind: finite|negative_infinity|positive_infinity|missing|invalid,
         value: ?Real, native_token: ?Text, source: ?SourceLocation}
# finite iff value is Real; infinities are explicit, never JSON NaN/Infinity.

Association = {database: ?ID, accession: ID, source: SourceLocation}
Compartment = {position: Count, id: ID, name: ?Text}
Gene = {position: Count, id: ID, name: ?Text, associations: [Association],
        supplied_target_refs: [Ref]}
Metabolite = {position: Count, id: ID, name: ?Text, compartment_position: Count,
              formula: ?Text, charge: Number, associations: [Association]}
Reaction = {position: Count, id: ID, name: ?Text,
            lower: Bound, upper: Bound, flux_unit: Unit,
            boundary_kind: exchange|demand|sink|internal|unknown,
            boundary_source: ?SourceLocation,
            gpr_native: ?Text, gene_positions: [Count],
            associations: [Association]}
Stoichiometry = {metabolite_position: Count, reaction_position: Count,
                 coefficient: Number, coefficient_unit: Unit}
LinearTerm = {reaction_position: Count, coefficient: Number}
Constraint = {id: ID, kind: metabolite_balance|additional_linear,
              metabolite_position: ?Count, terms: [LinearTerm],
              lower: Bound, upper: Bound, unit: Unit,
              source: SourceLocation}
Objective = {direction: max|min|unknown, constant: Number,
             terms: [LinearTerm], unit: Unit, source: ?SourceLocation}
MediumEntry = {reaction_position: Count, native_value: Number,
               native_meaning: cobra_medium_entry|supplied_exchange_bound|unknown,
               source: SourceLocation}
EffectiveFBAModel = {version: effective_fba_model_v1, model_id: ?ID,
  original_model_file: File, native_model_export_file: ?File,
  raw_annotations_file: ?File, compartments: [Compartment], genes: [Gene],
  metabolites: [Metabolite], reactions: [Reaction], stoichiometry: [Stoichiometry],
  constraints: [Constraint], objective: Objective, medium: [MediumEntry],
  medium_state: observed|not_retained|unavailable,
  constraint_coverage: complete_net_flux_linear_problem|partial|unsupported,
  unrepresented_problem_file: ?File}
```

All local IDs are unique within their own model/axis; positions are contiguous source-order indices and joins must match both ID and position. Duplicate source IDs/terms are preserved as invalid source rows rather than silently merged. `terms` coverage must explicitly describe the complete relevant expression: an omitted coefficient is not assumed zero unless the native complete sparse representation declares it absent. All actual metabolite constraints are retained, including extracellular/boundary-associated metabolites when constrained; compartment labels do not remove balance equations. Additional native linear constraints must be represented. Integer, nonlinear, split-variable-only or otherwise unrepresentable constraints/objectives remain retained with `unsupported`/`partial`; a net flux CSV cannot establish full-problem feasibility in their presence. FBA support here is a steady-state continuous linear model, not a whole-cell simulation.

`medium` is a source record, not a second way to change constraints. The original wrapper has no medium argument. Selected environment changes must be actual supplied model/bound operands and appear in the effective model. Do not convert a medium uptake magnitude to a signed exchange bound without the native direction/definition. Preserve both if supplied; conflicts are explicit.

```text
ConstraintChange = {reaction_id: ID, requested_lower: Bound,
  requested_upper: Bound, effective_reaction_position: ?Count,
  application: applied|rejected|not_attempted|unknown, issue_code: ?IssueCode}
ObjectiveRequest = {kind: model_default|single_reaction, reaction_id: ?ID}
Solver = {interface: ?ID, name: ?ID, version: ?Text, cobra_version: ?Text,
  optlang_version: ?Text, raw_status: ?Text,
  status: optimal|feasible|infeasible|unbounded|infeasible_or_unbounded|
          time_limit|iteration_limit|numerical_failure|error|unknown,
  feasibility_tolerance: Number, optimality_tolerance: Number,
  integrality_tolerance: Number, raw_parameters_file: ?File,
  diagnostic_file: ?File,
  alternate_optimum_claim: not_assessed|reported_alternate|reported_unique|conflicting,
  alternate_claim_source: ?SourceLocation}
FluxRow = {source_row_index: Count, reaction_id: ID,
  reaction_position: ?Count, reaction_name: ?Text, flux: Number,
  csv_lower: Bound, csv_upper: Bound, association: matched|unknown|duplicate|conflicting}
NativeFBAResult = {version: native_fba_result_v1,
  solver: Solver, objective: Number, flux_rows: [FluxRow],
  solve_call_count: Count, constraint_changes: [ConstraintChange],
  objective_request: ObjectiveRequest,
  objective_application: applied|model_default|rejected|not_attempted|unknown,
  request_realization: exact|mismatch|unknown,
  execution_outcome: completed|partial|failed|not_executed,
  source_active_count: ?Count, source_active_threshold: Number,
  source_log_file: ?File, issues: [Issue]}
FluxBalanceSheet = {version: flux_balance_sheet_v1,
  operation: perform_flux_balance_analysis,
  mode: steady_state_linear_fba,
  original_request_file: File, native_manifest_file: ?File,
  effective_model: ?EffectiveFBAModel, native: NativeFBAResult,
  retained_files: [File], issues: [Issue]}
```

Native solution values are model predictions; diagnostic formulas are derived model checks. None is an observed experimental function measurement. Missing standard errors, intervals or calibration stay missing. `alternate_optimum_claim` records an explicitly sourced solver claim only. The inspected upstream has no such claim, so it is `not_assessed`. No FVA, pFBA, knockout analysis, additional optimization or uniqueness inference is introduced.

```text
Tolerance = {subject_id: ID, value: Real, unit: Unit}  # value >= 0
FBACalculationParameters = {version: fba_calculation_parameters_v1,
  reaction_bound_tolerances: [Tolerance], constraint_tolerances: [Tolerance],
  active_flux_thresholds: [Tolerance], objective_absolute_tolerance: ?Real}
# Arrays select exact reaction/constraint IDs in this sheet; no duplicates.
# Missing tolerance leaves the numerical residual available and comparison unknown.
# No implicit solver-tolerance default; explicit native-unit thresholds only.

Cell = {value: ?Real, state: calculated|native|missing|invalid|incompatible|
        not_applicable|overflow, unit: Unit, issue_codes: [IssueCode]}
ReactionCheck = {reaction_position: Count, flux: Number,
  lower_slack: Cell, upper_slack: Cell,
  lower_violation: Cell, upper_violation: Cell,
  bound_comparison: passes|fails|unknown, active: ?bool}
ConstraintCheck = {constraint_id: ID, metabolite_position: ?Count,
  activity: Cell, equality_residual: Cell, lower_slack: Cell, upper_slack: Cell,
  lower_violation: Cell, upper_violation: Cell,
  comparison: passes|fails|unknown, expected_term_count: Count,
  available_term_count: Count}
FluxBalanceCalculations = {version: flux_balance_calculations_v1,
  sheet_sha256, parameters: FBACalculationParameters,
  reaction_checks: [ReactionCheck], constraint_checks: [ConstraintCheck],
  objective_calculated: Cell, native_objective: Number,
  native_minus_calculated_objective: Cell,
  objective_comparison: agrees|conflicts|unknown,
  expected_reaction_count: ?Count, valid_flux_count: ?Count,
  flux_coverage_fraction: Cell,
  evaluated_constraint_count: Count, expected_constraint_count: ?Count,
  violated_constraint_count: Count, constraint_comparison_unknown_count: Count,
  evaluated_reaction_bound_count: Count, violated_reaction_bound_count: Count,
  active_count: ?Count, active_population_count: Count,
  max_abs_balance_residual: Cell,
  candidate_feasibility: passes_recorded_checks|fails_recorded_checks|
                         partial_checks|unknown,
  native_solver_status: Solver.status,
  optimum_multiplicity: not_assessed|reported_alternate|reported_unique|conflicting,
  issues: [Issue]}
```

`expected_reaction_count`, `valid_flux_count` and `expected_constraint_count` are null when the effective model/population is unavailable. A known empty population is zero, which is different from unknown. `sheet_sha256` links calculations to immutable operands. A calculation result must preserve raw native versus calculated values separately. A new parameter set produces a new calculations artifact with the same original sheet. No format reader, publisher, display, or return function recomputes these components.

`Issue = {code: IssueCode, stage: selection|load|apply|solve|capture|parse|calculate|project|return, field: ?ID, source_row_index: ?Count, reaction_position: ?Count, metabolite_position: ?Count, detail_file: ?File}`. `IssueCode` is closed to: `input_missing`, `unsupported_model_format`, `model_load_failed`, `model_identity_conflict`, `reaction_id_unknown`, `duplicate_reaction_id`, `bound_invalid`, `constraint_rejected`, `objective_rejected`, `request_effective_mismatch`, `solver_unavailable`, `solver_exception`, `status_unrecognized`, `flux_missing`, `flux_nonfinite`, `artifact_missing`, `artifact_truncated`, `artifact_identity_conflict`, `schema_invalid`, `unsupported_problem_form`, `unknown_units`, `native_derived_conflict`, `missing_parameters`, `writer_not_closed`, `projection_invalid`, `saved_sheet_not_received`, `binding_unavailable`, `numeric_overflow`, `objective_unavailable`, `constraint_unavailable`, `zero_denominator`. Raw exception messages stay in `detail_file`, not unconstrained typed findings.

### 4.1 Proposed execution/capture envelope shapes

These records extend the existing practical assignment/lifecycle; they are not another workflow. Shared analytical shapes above remain owned by `flux_balance_contracts.py`. `native_flux_balance_contracts.py` owns only this execution envelope and imports the analytical definitions.

```text
FilePin = {path: absolute-path, sha256, size_bytes: Count}
Distribution = {name: ID, version: Text}
FBASoftware = {version: fba_software_v1, python: FilePin,
  python_version: Text, python_home: absolute-path, module_root: absolute-path,
  dependency_roots: [absolute-path], implementation_files: [FilePin],
  runtime_files: [FilePin], distributions: [Distribution],
  solver_interface: ID, solver_runtime_files: [FilePin]}
RequestedBoundChange = {reaction_id: ID, lower: Bound, upper: Bound}
RequestedSolverOptions = {feasibility_tolerance: ?Real,
  optimality_tolerance: ?Real, integrality_tolerance: ?Real}
# Null means no override; it does not mean the actual native tolerance is zero.
FBAJob = {version: native_flux_balance_job_v1,
  operation: perform_flux_balance_analysis, mode: steady_state_linear_fba,
  source_alias: biomni.tool.systems_biology.perform_flux_balance_analysis,
  model_input: {file: FilePin, artifact_ref: ?Ref,
    format: sbml|cobra_json, original_loader_selection: sbml_file|json_file|repository_identifier,
    repository_identifier: ?ID, acquisition_receipt_file: ?File},
  constraints: ?[RequestedBoundChange], objective: ObjectiveRequest,
  solver_options: RequestedSolverOptions, software: FBASoftware,
  output_prefix: relative-confined-path, flux_output_name: relative-confined-path}
FBARequestedJob = {argv: [Text], environment: {env-name: Text}, native_flux_balance: FBAJob}
# Environment is the existing typed environment mapping: valid env-name keys,
# exact caller-selected values, no new secret discovery or unrecorded defaults.
# argv is deterministically derived from the same software/driver/plan identity.
FBAAttemptIdentity = {run_id: ID, episode_id: ID, resource_id: ID,
  execution_id: absolute-path, attempt_id: ID, operation_key: ID,
  requested_job_sha256, assignment_sha256}
FBAAllocation = {memory_bytes: positive-int, scratch_bytes: positive-int,
  wall_seconds: null}
FBARunPlan = {version: flux_balance_run_plan_v1,
  identity: FBAAttemptIdentity, requested_job: FBARequestedJob,
  attempt_directory: absolute-confined-path, policy: FBAAllocation,
  outputs: [FBAOutputDeclaration]}
FBAOutputDeclaration = {role: ArtifactRole, relative_path: relative-confined-path,
  format: ID}
ArtifactRole = original_model|selected_request|effective_model|effective_problem|
               solution|flux_csv|native_log|manifest
ManifestFile = {role: ArtifactRole-except-manifest,
  relative_path: relative-confined-path, format: ID,
  state: present|absent|truncated|incompatible, identity: ?ArtifactIdentity}
FBANativeManifest = {version: flux_balance_native_manifest_v1, sealed: bool,
  attempt: FBAAttemptIdentity, software_sha256, model_identity: ArtifactIdentity,
  actual_distributions: [Distribution], actual_solver: Solver,
  source_function_sha256, effective_problem_sha256: ?hex64,
  files: [ManifestFile], solve_call_count: Count,
  execution_outcome: completed|partial|failed|not_executed,
  request_realization: exact|mismatch|unknown, issues: [Issue]}
CapturedFile = {role: ArtifactRole, expected: FBAOutputDeclaration,
  state: present|absent|truncated|incompatible,
  retained: ?{file: File, path: absolute-confined-path}, issues: [Issue]}
FBACapturedFiles = {version: flux_balance_capture_v1,
  attempt: FBAAttemptIdentity, original_plan_sha256,
  source_action_receipt_file: File, writer_closure_receipt_file: File,
  files: [CapturedFile], issues: [Issue]}
NativeWorkerInput = {mode: native_result, original_plan: FBARunPlan,
  capture: FBACapturedFiles}
SavedWorkerInput = {mode: saved_sheet_recalculation,
  sheet: {file: File, path: absolute-confined-path}}
FBAResultWorkerPlan = {version: flux_balance_worker_plan_v1,
  directory: absolute-confined-path, input: NativeWorkerInput|SavedWorkerInput,
  selector: FBAResultSelector}
WorkerOutput = {role: sheet|calculations|projection|diagnostics,
  relative_path: relative-confined-path, format: ID,
  state: present|absent, identity: ?ArtifactIdentity}
FBAWorkerResult = {version: flux_balance_worker_result_v1, plan_sha256,
  mode: native_result|saved_sheet_recalculation, outputs: [WorkerOutput],
  native_binding: bool, native_solver_status: Solver.status,
  original_result_acquired: bool, requested_delivery_complete: bool,
  issues: [Issue]}
```

The manifest lists seven producer artifacts, never its own recursive hash; capture retains the manifest as the eighth role. The effective-model artifact holds the complete native export/annotations and normalized snapshot in one versioned container; the parser's `native_model_export_file` and `raw_annotations_file` can reference that exact retained container, with source field locations pointing to the corresponding native payload. Separate original stdout/stderr remain in the existing native lifecycle/log custody and do not become calculation operands. No native output path may overlap the original input or another attempt.

Producer payloads cannot invent Store artifact references. At production time a `SourceLocation` uses `{role: ArtifactRole, record_index: ?Count, field: ID}` and file references use `{role: ArtifactRole, identity: ArtifactIdentity}`. `parse_fba_capture` replaces only these addresses with the exact validated retained `File` entries from the capture; it preserves all native data values. The driver and parser schema versions distinguish producer-local and retained addresses explicitly. Before capture, `FBANativeManifest.actual_solver`, issues and other source-bearing records use those producer-local locations; after capture `NativeFBAResult` and `EffectiveFBAModel` use the retained shapes in section 4. This is address binding, not a second sheet or calculation policy.

Semantic validation must additionally compare every plan/manifest/capture identity with the original requested job and closed writer, check every supplied SHA/size and role/format, enforce unique output names and complete role declarations, and verify that selected model, software, source function and actual solver match their recorded realization. An absent/unreadable original input may leave `FBANativeManifest.model_identity` as the original selected pin, but must not claim its bytes were acquired; the corresponding role remains absent and a specific failure is retained. Repository-identifier mode requires actual resolved bytes and its acquisition receipt; it remains unfinished until a concrete provider/deployment contract is available.

For the intended local binding, `FBAAllocation` is exactly 20 GiB memory and 4 GiB scratch with null wall limit and the existing zero-swap policy. This is not an autonomous allocation choice. Existing constrained parent allocations/resource requirements cannot be overwritten to make it fit. A future different actual resource uses its own caller-owned execution envelope while sharing the analytical shapes.

## 5. Numerical definitions and missing-data behavior

| Shared numerical component | Exact dependency/formula | Meaning, unit/population and missing behavior |
| --- | --- | --- |
| Reaction flux | Native solution/CSV value joined to exact reaction ID and effective model | Predicted net flux on that model's recorded scale; preserve negative and zero; no native unit assumption |
| Bound slacks | `v_j - l_j`, `u_j - v_j` | Native reaction-flux units; unbounded side is `not_applicable`, not zero or missing |
| Bound violations | `max(l_j - v_j, 0)`, `max(v_j - u_j, 0)` | Nonnegative numerical infeasibility of this candidate at that bound; comparison uses supplied per-reaction absolute tolerance |
| Constraint activity | Stable sum of every `a_ij * v_j` | Actual native constraint unit/scale; complete sparse expression required; missing nonzero operand makes this row unavailable |
| Equality residual | `sum(a_ij*v_j) - b_i` only when lower = upper = `b_i` | For actual metabolite balances, signed steady-state residual `S_i v - b_i`; no balancing equation inferred from a compartment |
| General linear-constraint violations/slacks | Same lower/upper formulas using activity | Retains additional inequality/equality constraints; all relevant constraints must be represented for full candidate-check coverage |
| Maximum absolute balance residual | Maximum `abs(residual_i)` over evaluated metabolite equalities, with evaluated/expected counts | Diagnostic only; if any required row is missing, mark the aggregate partial via issues and candidate status. An empty population has unavailable maximum, never fabricated zero. Aggregate only compatible native scales; incompatible units give unavailable aggregate but retain row checks |
| Objective | `constant + sum(c_j * v_j)` | Exact supplied effective linear objective and direction; coefficients/constant missing means unknown; missing flux in a proven zero-coefficient term does not block this particular sum |
| Native/calculated objective difference | Full native objective minus calculated value | Objective units; both values remain retained. Six-decimal log value is rounded source data, not full precision; objective agreement uses its recorded rounding envelope plus the explicit comparison tolerance. Unknown precision/tolerance gives unknown agreement |
| Flux coverage | `valid uniquely matched finite fluxes / expected reactions` | Dimensionless completeness, not confidence; 0 expected gives unavailable fraction; malformed or duplicate rows do not shift original IDs |
| Active count | Count of matched finite fluxes with `abs(v_j) > supplied threshold_j` | Native source default threshold was 1e-6; new calculations require explicit thresholds. Report the available population; if any required value/threshold is missing the full-population count is null, not an extrapolation |
| Violation counts | Count of rows whose numerical violation exceeds their explicit tolerance | Alongside evaluated/expected/unknown counts; no model feasibility conclusion from a partial candidate |

Native physical units may be unknown while arithmetic in a single explicitly captured native optimization coordinate system remains available; label that lack of physical interpretation. Do not perform cross-unit arithmetic/aggregation without supplied conversion/compatibility. Solver numerical tolerance and user-selected diagnostic tolerance remain different records. No rescaling, clipping, smoothing, probability, confidence score, likelihood, support hypervolume, or W05 aggregation is introduced.

`passes_recorded_checks` requires complete represented linear problem, complete necessary candidate values, explicit relevant tolerances, and no violation. It establishes only a candidate satisfying the retained constraints within those tolerances. A violating candidate does **not** establish that the problem is infeasible. Missing fluxes do **not** establish zero flux or infeasibility. A returned finite vector does **not** establish boundedness, optimality, uniqueness, experimental function or gene causality. Native `infeasible`, `unbounded`, `infeasible_or_unbounded`, time/iteration limits and numerical errors are preserved as separate solver claims even if no usable vector/objective exists. Solver claims and independent residual checks may conflict and both remain visible.

## 6. Requested typed returns and ownership

Proposed `x-source` facts are exactly `flux_balance_measurements`, `flux_balance_saved_sheets`, and `flux_balance_failures`. They use the existing original-parent-form machinery, not a model-composed summary. `flux_balance_saved_sheets` contains `[File]` restricted to `format=flux_balance_sheet_v1`; it grants only the explicitly returned saved sheet through existing receipt/scope checks. Failure facts contain `[Issue]`.

```text
FBAProjectionSelector = {version: fba_projection_selector_v1,
  view: diagnostics|reaction_fluxes|constraint_checks|model_associations,
  reaction_positions: [Count], constraint_ids: [ID],
  fields: [FieldName], row_window: {offset: Count, limit: positive-int}}
FBAResultSelector = {version: flux_balance_result_selector_v1,
  mode: native_result|saved_sheet_recalculation,
  saved_sheet_file: ?File, calculation_parameters: FBACalculationParameters,
  projection: FBAProjectionSelector}
FBAProjection = {version: flux_balance_projection_v1,
  selector: FBAProjectionSelector, native_solver_status: Solver.status,
  candidate_feasibility: FluxBalanceCalculations.candidate_feasibility,
  optimum_multiplicity: FluxBalanceCalculations.optimum_multiplicity,
  request_realization: NativeFBAResult.request_realization,
  total_available_rows: Count, selected_row_count: Count,
  row_offset: Count, returned_row_count: Count, has_more: bool,
  rows: [DiagnosticRow|ReactionRow|ConstraintRow|AssociationRow], issues: [Issue]}
```

Closed row variants:

- `DiagnosticRow = {field: DiagnosticField, value: Cell|Number|Count|null}`. `DiagnosticField` is exactly `objective_calculated`, `native_objective`, `native_minus_calculated_objective`, `expected_reaction_count`, `valid_flux_count`, `flux_coverage_fraction`, `evaluated_constraint_count`, `expected_constraint_count`, `violated_constraint_count`, `constraint_comparison_unknown_count`, `evaluated_reaction_bound_count`, `violated_reaction_bound_count`, `active_count`, `active_population_count`, and `max_abs_balance_residual`. Each field has the fixed matching Cell/Number/Count/null type declared above; it is not an unrestricted key/value map.
- `ReactionRow = {reaction: Reaction, numerical: ReactionCheck}`; selected `fields` are drawn only from `ReactionCheck` numerical fields. Unrequested cells are omitted in the closed view-specific schema generated from the selection, not populated by free text.
- `ConstraintRow = {constraint: Constraint, numerical: ConstraintCheck}` with the analogous closed selection.
- `AssociationRow = {reaction_position: Count, reaction_id: ID, gpr_native: ?Text, genes: [Gene], associations: [Association]}`; source meanings only, not candidate annotations.

`FieldName` is a view-indexed closed enumeration: diagnostics uses `DiagnosticField`; reaction_fluxes uses `flux`, `lower_slack`, `upper_slack`, `lower_violation`, `upper_violation`, `bound_comparison`, `active`; constraint_checks uses `activity`, `equality_residual`, `lower_slack`, `upper_slack`, `lower_violation`, `upper_violation`, `comparison`, `expected_term_count`, `available_term_count`; model_associations uses `gpr_native`, `genes`, `associations`. A nonempty unique field list is required; a field from another view is invalid. `reaction_positions` must be nonempty exactly for reaction_fluxes/model_associations and empty otherwise; `constraint_ids` must be nonempty exactly for constraint_checks and empty otherwise. Diagnostics requests neither axis. The returned row variant must match the selected view.

All selected fields/indices must exist with the same model/row identity. Inapplicable selectors fail specifically; do not pick a first row. Metadata tied to selected rows remains necessary qualification; full matrices/GPR/source files remain retained rather than dumped into context. Original TASK/STEERING templates are not edited here; later receiver-facing presentation needs its own decision/information trace and user feedback before coding.

`FBAAttemptIdentity` and run/worker plans must use the existing original practical assignment, resource ID, run/episode/operation/attempt identity, request digest, model byte identities, software pin and writer-closure relationships. These stay internal. `ParsedFBABundle = {model: ?EffectiveFBAModel, native: NativeFBAResult, original_request_file: File, native_manifest_file: ?File, retained_files: [File], issues: [Issue]}`; its source files must be exactly those in the validated captured manifest. `ParsedFluxRows = {rows: [FluxRow], issues: [Issue]}`. `FBAArtifactPayloads` is a role-indexed closed record of the eight bundle roles above, each `{file: ?File, bytes: ?bytes, state: present|absent|truncated|incompatible}`; bytes exist only at the host parser call boundary.

An authenticated finite result worker calls parser → populate → calculate → project and retains all four outputs. Published and returned scalar values must be byte/numerically equal to the selected calculated cells, with native values distinct. Complete, qualified, partial and failed native outcomes can return their specific typed information. Delivery of a legitimate infeasible/unbounded solver result must not require a positive objective or active reaction; completion validates the original practical assignment/output contract, not biological success. A failed requested configuration cannot silently satisfy a different analysis. Existing controller and immediate exact-zero practical-completion behavior remain unchanged; no parser or calculator adds observations or credit.

## 7. Exclusive proposed coding ownership and dependencies

This agent has written only this assigned verification directory. The following are future exclusive assignments, not current authorization or edits:

| Owner | Exclusive proposed files | Exact dependencies/deliverables |
| --- | --- | --- |
| Numerical contract/calculator owner | `gene_annotation_episode/flux_balance_contracts.py`, `flux_balance_sheet.py`, `flux_balance_calculations.py` | Own every field/enum, pure validation, numerical definition and saved recalculation. Publish the exact shape/signatures above before others code; no I/O/scientific imports |
| Native/parser owner | `flux_balance_readers.py`, `native_flux_balance_driver.py`, `native_flux_balance_capture.py`, `native_flux_balance_contracts.py`, `native_flux_balance_local.py`, `native_flux_balance_storage.py` | Consumes frozen model/native/sheet shapes. Produces complete exact-attempt artifact bundle and source-specific parsing; actual Cobra/solver acquisition/capture APIs must be resolved from a real configured deployment first. No scientific calculator duplicates |
| Result/return owner | `flux_balance_result_contracts.py`, `flux_balance_result_views.py`, `flux_balance_return_views.py`, `flux_balance_result_worker.py`, `flux_balance_result_receipts.py`, `flux_balance_returns.py`, `native_flux_balance_results.py`, `native_flux_balance_preparation.py` | Consumes captured bundle, shared sheet/calculations and selected original form. Produces authenticated native/saved worker outputs, closed partial/failure returns, frozen replay and exact calculated-value projections |
| Shared integration owner (coordinator only) | Existing `execution_episodes.py`, `practical_execution_records.py`, `practical_execution_operations.py`, `execution_progress.py`, `execution_input_versions.py`; new `native_flux_balance_tool_info.py`, `flux_balance_execution_information.py` | Adds one actual tool/resource binding and all affected input/target/fact/reference/closure consumers. Uses result owner outputs and existing shared lifecycle; no numerical arithmetic here |
| Verification owner | New FBA-specific tests/fixtures in separately assigned paths | Consumes all frozen contracts; verifies arithmetic, artifacts and the actual selected child-owned return path. No simultaneous edits to production modules |

The parser can be built against explicit saved captured fixtures once these types are frozen; the calculator can be built against declared numerical fixtures without an installed solver. Actual native producer verification alone needs the real solver/software/model APIs and runtime. Episode integration alone needs the concrete result host/return sources, not completion of unrelated tool groups. No general blocking dependency on the representation/support-operation agents is created.

## 8. Required verification cases (all unrun here)

Hand-checkable examples below are deliberate fixtures/specifications, not native measurements or verification results.

1. A two-metabolite model has reactions `IN: -> A`, `AB: A -> B`, `OUT: B ->`, `S=[[1,-1,0],[0,1,-1]]`, bounds `[0,10]`, `[0,1000]`, `[0,1000]`, and max objective `OUT`. Supplied vector `[10,10,10]` gives residuals `[0,0]`, objective 10, zero bound violations, 3/3 finite flux coverage and active count 3 at explicit 1e-6. Check output equality through the real publication/return path. Do not claim a solver was run from this arithmetic example.
2. Same model, vector `[10,12,12]`: residuals `[-2,0]`, calculated objective 12. Native objective 10 must remain separate (difference -2). Candidate checks fail; do not label the entire model infeasible.
3. Same model, missing `AB` flux: coverage 2/3; both metabolite residuals unavailable, objective can still be 10 if its complete expression uses only `OUT`. No zero fill. Valid IN/OUT cells survive. Duplicate IDs, unknown IDs, reordered rows and one malformed CSV row preserve original identities/positions.
4. Two parallel A-to-B reactions allow supplied vectors `[10,10,0,10]` and `[10,0,10,10]`, both satisfying the model at objective 10. Their separate checks must not produce a uniqueness claim. No new FVA/alternate-solution solver is invoked.
5. Authentic native optimal, feasible-but-limited, infeasible, unbounded, infeasible-or-unbounded, numerical-error and unavailable-solver outputs retain their exact raw statuses. A final finite vector may coexist with a limit or unbounded status. Absence of a vector cannot prove infeasibility.
6. Signed reverse flux and negative bounds; explicit positive/negative infinite bounds; zero flux versus null/NaN; unknown physical units; conflicting CSV/effective bounds; equalities with nonzero RHS; explicit extra linear constraints; unrepresented nonlinear/integer/split-variable constraints; missing/unknown objective direction; multi-term minimization/default objective. Unsupported portions must prevent a false full-problem residual verdict while preserving computable rows.
7. Constraint application error and invalid objective cannot proceed as a successful different/default requested analysis. Historical logs from swallowed errors retain mismatch. Test malformed tuple arity, missing model, case-sensitive suffix fallback, output write failure and truncated/missing CSV independently.
8. Native source 6-decimal objective/top-reaction log versus full native numeric artifacts: retain both and precision; do not invent full precision or flag a mere rounding difference as a conflict. Active-count output must use the shared calculator's explicit absolute threshold and population.
9. SBML and Cobra JSON encoding the same effective model must yield the same shared sheet meanings and calculator values, preserving exact different source artifacts/metadata. Repository identifier loading must first establish actual source resolution, retained bytes and cache/storage behavior; no assumed availability.
10. Save full sheet, shut off acquisition/solver access, and recalculate residuals/objective/thresholds from only the saved sheet plus explicit parameters. Change a diagnostic tolerance/active threshold without changing retained native values. Changing medium/bounds/objective for a new optimized vector requires a separately selected analysis, not relabeling saved recalculation as a new solve.
11. Exact selected-tool information → scientific parent → ordinary launch → correct configured resource child → one original native handle → closed-writer capture → parser → shared calculator → requested results child → scientific-parent form. Test unselected tool exclusion, wrong attempt/model/software, wrong resource, malformed return, no unsolicited fields and measured/counted values equal to calculated sheet cells.
12. Partial capture with a usable model or some valid flux rows; missing manifest/changed bytes; wrong source identity; received saved-sheet versus unreceived artifact; repeated collect/status; parent closure/restart before delivery; closed replay after source files disappear. Reuse original handle/receipt, do not resubmit/solve, preserve earlier facts/observations/credit, and distinguish frozen historical authority from current artifact availability.
13. Record configured deployment/library/solver inspection, actual source-format runs and actual episode-return runs as separate evidence. No standalone import, fixture, catalog entry, CSV file, or native solver success completes the full row.

## 9. Inspection result and concrete handoff

Inspection used host standard-library source reads, AST parsing, directory/metadata inspection and hashes only. No application/scientific imports, tests, solver/native execution, network/download/install, prompts, production code, inventory, or progress files were changed. `python` was unavailable; subsequent read-only scripts used `python3`. An initial overly broad file listing was discarded as non-evidence; bounded source searches supply the findings above.

Both `reference/episode_tools/.venv/lib/python3.12/site-packages` and `.venv/lib/python3.12/site-packages` exist. No `cobra`, `optlang`, `swiglpk`, `gurobi`, or `cplex` package entries were present in either inspected directory. The reference environment contains Biomni 0.0.8 source/metadata. This is a limited filesystem observation, not a search of every remote environment or proof that a solver cannot exist elsewhere. `resources/local-tools.toml` binds Infernal/PDF utilities, not FBA. No real model or configured solver execution was established.

Concrete unresolved producer dependency: inspect the *actual chosen deployment's* Cobra model loading/export, objective setter/direction, model constraints/medium, solver selection/status/tolerance and solution extraction APIs before implementing/certifying the native capture. Source-only inspection here cannot determine those absent implementation details. The pure shared arithmetic contract and reader of explicitly captured fixtures are independent of that runtime dependency.

Handoff: retain one new shared FBA numerical owner; repair the native artifact seam inside the same selected solve; add one real resource/result/typed-return binding using existing episode owners; verify the exact native/saved/partial/replay paths above. All existing fixed-row completion stages remain unchanged and unfinished.
