# RNA structure interface review, workload 353

Read-only review of PLAN.md and CONTRACT_ADDENDUM_001.md from workload 349, including the addendum's final consistency section. Scope is only B-L103-predict_rna_secondary_structure and B-L104-analyze_rna_secondary_structure_features. This packet is a review, not a new accepted design or implementation.

The three responsibilities are divided sensibly: lane 1 owns pure native reading, sheet population and calculations; lane 2 owns the selected local native operation and sealed attempt; lane 3 owns custody, requested projection and authenticated returns. Shared integration remains root-owned. No new episode type, workflow owner, annotation score, literature grader or evidence-axis change is needed.

**Immediate coding verdict:** pure topology and numerical calculation work can start independently. No unresolved topology formula was found after applying the addendum's final units, side-field and denominator corrections. The parser/populator contract needs the two small lane-1 clarifications C1 and C2 below. They do not depend on ViennaRNA, native execution or lane 3. The remaining delivery interfaces should be made explicit before assigning their implementation as a frozen contract.

## Contract findings

### C1 — Missing native bytes and nullable original input need an explicit lane-1 representation

Ports: NativeParse, RNASheet.native_input, populate_rna_prediction_sheet and populate_rna_feature_sheet.

Locations: ADDENDUM lines 218–252, 344–347, 805–819 and 881–886.

NativeParse requires raw_sha256:Sha and raw_byte_count:Count. RNASheet.native_input likewise requires a nonnull digest and count. The population signatures require original_input:dict, while RNASheet.original_input and the producer input may be null after malformed original JSON. The final section allows independently supplied valid topology to survive native parsing failure and says preparation can report a missing native_result. There is no typed representation of an absent native file that avoids pretending it is a retained empty file.

Freeze the absence case before the parser/populator handoff: allow original_input:RNAInput|null, and explicitly represent missing native bytes with null provenance or a discriminated missing variant. A retained zero-byte malformed file must keep its actual empty-file digest/count and remain different from a nonexistent file. Define the native Issue passed into the populator for the missing variant. If no original/native information permits a sheet, the worker may use its already-declared sheet_file:null path; do not invent input or a record.

This is an absence/provenance gap, not a defect in the supplied-topology formulas. Parsing actual retained bytes, including malformed bytes, can proceed.

### C2 — Name the pure model validator exports

Ports: lane-1 pure ModelSpec/EffectiveModel validators imported by lane 2 and lane 3.

Locations: ADDENDUM lines 331–359, 367–397 and 897–901.

The addendum assigns these shape checks to lane 1 and defines their fields, but its exact lane-1 export list does not name either function. Fresh implementations would have to coordinate an unstated import.

Freeze two ordinary exports, for example:

    validate_rna_model_spec(value: dict) -> ModelSpec
    validate_rna_effective_model(value: dict) -> EffectiveModel

They must be pure shape/relationship checks. Actual settings support, import identity and parameter loading remain lane-2 execution checks. The names above are a review proposal for root to accept, not an edit to the original contract.

### C3 — The lane-2 to lane-3 sealed-bundle locator is missing

Ports: RunPlan, run_rna_structure_driver, local_rna_structure_plan and capture_local_rna_structure_bundle.

Locations: ADDENDUM lines 443–469, 491–496 and 653–655; PLAN lines 157–170.

RunPlan supplies attempt_directory but neither a manifest filename nor a bundle-relative-path field. The producer returns BundleManifest in-process, while capture receives only target and directory and must independently locate the original serialized manifest. Neither reviewed planning file specifies bundle.json or another exact manifest filename.

Freeze one lane-2 exported constant such as BUNDLE_FILENAME = "bundle.json", or an exact RunPlan.bundle_relative_path field, with confinement and immutability requirements. Capture should obtain the original plan through local_rna_structure_plan and use that declared locator. It should not import an Infernal private helper or guess an analogous filename.

### C4 — Capture failures cannot reach the declared grading plan through the preparation signature

Ports: CaptureResult.failures -> prepare_rna_structure_grading -> GradingPlan.capture_failures.

Locations: ADDENDUM lines 528–542, 657–659 and 881–886.

GradingPlan contains capture_failures:Issue[]. The preparation function receives only digest-verified artifacts:list[CapturedFile], the bundle and selector. It does not receive CaptureResult.failures or invalid_artifacts. For example, a native_result omitted from verified artifacts might have been unreadable or have a digest mismatch. Those are different original capture outcomes; the supplied arguments cannot recover which occurred.

Pass the actual capture or add an explicit capture_failures:list[Issue] argument. Copy its original issues into the worker plan and retain the relationship to the relevant manifest role. Do not derive a generic missing-file explanation and call it the original capture failure. Capture completeness and native success remain independent.

### C5 — Define the worker's projected-row artifact before its publication consumer

Ports: WorkerGradingResult.projected_rows_file -> PreparedGrading.selected_rows_artifact_ref -> publish_selected_rna_structure_rows.

Locations: ADDENDUM lines 543–555 and 585–644.

The file path is typed, but its content schema, serialization and row order are not defined. CommonRow is the final host row and requires source_ref, subject_ref and binding status. GradingPlan supplies no source_ref, and source publication occurs after preparation. A Store-free worker cannot emit a fully authenticated CommonRow.

Freeze a closed prepublication row union containing only saved sheet/component values and finite row metadata, with an explicit JSON/NDJSON format. State which host fields publication adds and how it validates them. Define deterministic ordinal order for offset/limit selection, especially stems and regions, and the no-row/selection-Issue representation. Keep the saved sheet and all component rows selector-independent. A final CommonRow must not be silently reused as the worker schema.

### C6 — Publication cannot call its required validator with the current arguments

Ports:

    validate_rna_structure_publication_inputs(store, context, *,
        original_input: RNAInput, capture: CaptureResult) -> SubjectBinding | None

    publish_selected_rna_structure_rows(store, *, source_ref: Ref,
        bundle: BundleManifest, prepared: PreparedGrading, scope: dict,
        selector: ResultSelector) -> Publication

Locations: ADDENDUM lines 666–670 and 893–896.

The final precondition says publication invokes host subject/reference qualification. The publisher receives neither context nor capture, both mandatory validator operands. Scope alone is not an authenticated receiving context, and PreparedGrading is not CaptureResult. Multiple receiving episodes can publish views of the same original native bundle, so context cannot be inferred from bundle identity.

Either add context and capture to the publisher signature, or perform the validation in NativeRNAStructureResults.execute and pass a specifically typed, original-receipt-bound validation result. Preserve the unbound partial numerical row on a subject-binding conflict. Do not construct a fake context or use source custody as permission to read unreceived subject data.

### C7 — Untrusted-bundle failures have no declared typed return path

Ports: ResultReceipt.failures/source_ref -> RNAFacts.execution_rna_structure_failure_rows -> NativeRNAStructureReturns.

Locations: ADDENDUM lines 622–627, 700–724 and 887–892.

The contract correctly forbids publishing an authenticated scientific source for a malformed/untrusted bundle, so ResultReceipt.source_ref is null. Every FailureRow nevertheless requires source_ref:Ref, and RNAFacts exposes no plain Issue[] failure source. As written, an untrusted-bundle failure is retained in the internal receipt but cannot be returned in the declared failure family without inventing a source.

Provide an authenticated receipt-derived failure projection that allows a null scientific source, or a separate closed Issue fact source. Bind operation/mode/record identity to the original target request and validate it through the original immediate-child return. The existing EpisodeReturnRecords mechanism can authenticate saved typed facts without a scientific source record. Complete capture must still be false; returning a specific capture failure does not claim native success or satisfy the complete-acquisition predicate.

### C8 — Correct the existing results-assignment validator reference and freeze the awaited adapter

Port: RNA ResultReceipt.assignment and the root's shared dispatch.

Location: ADDENDUM lines 914–916 and class ports at 676–688.

The addendum says the existing results assignment is accepted by ExecutionEpisodes._validate_request. That method actually requires a configured resource_id and validates practical/API resource assignments. RESULTS_SCHEMA is instead the closed {version:"execution_results_assignment_v1", handoff_ref, selector} object. prepare_assignment(..., role="results", ...) checks that schema, reads the original target and invokes _selector.

Use that actual results schema/selector path and compare the receipt assignment with the saved results episode request. Do not call the resource validator on a results assignment. Also state explicitly that NativeRNAStructureResults.execute is async: ExecutionEpisodes.execute awaits every family adapter. Define the lane-3 operation_catalog export, or explicitly allocate equivalent catalog construction to root, so the status/collect catalog import is not guessed.

Evidence: execution_episodes.py lines 54–56, 283–305, 372–395, 795–868 and 884–896. No shared file was changed.

### C9 — The existing scientific report renderer does not remove RNA source identities

Port: final typed RNA rows -> admitted child report -> scientific STEERING.

Locations: PLAN lines 515–522; ADDENDUM lines 600–620 and 638–644.

PLAN assumes existing prompt builders can render the finite RNA rows while verification shows that no source hashes leak. Inspection establishes that _steering passes admitted reports to alignment_report_presentation, then recursively renders every supplied field. That presenter only recognizes BV-BRC alignment field rows; other reports are returned unchanged. The RNA CommonRow requires source_ref and several internal keys. infernal_receiver_context does not alter explicit child reports.

The proposed typed rows are usable host records, but the inspected renderer does not yet satisfy the RNA presentation constraint. Root should supply the required decision/information trace and a mechanical RNA presentation adapter before claiming this boundary complete. Keep source references, row identities, complete sheet artifacts and typed return validation unchanged in host state. Render only the selected numerical values, relationships, unavailable reasons and necessary readable associations.

Evidence: scientific_process_prompt.py lines 55–72, 377–417 and 458–463; alignment_result_presentation.py lines 24–43 and 75–98; infernal_result_presentation.py in full. This is a specific RNA consumer finding, not a general prompt audit.

## Interfaces inspected without a defect in the proposed reuse

- materials.artifact_file(store,path,media_type) and artifact_path(store,ref) exist. The former streams complete bytes into content-addressed Store custody; the latter verifies the digest before returning a path. RNA can reuse these for retained artifacts.
- Store.artifact and get_artifact exist with bytes/text and bytes return contracts; Store.put and validate_scope are present. Scope and receipt authority are not supplied by the pure calculation worker.
- retain_tool_grading(store,provider,native_artifact_ref,grading) and source_tool_gradings(store,source_ref) exist. They retain/resolve full grading envelopes without calculation or publication; source_tool_gradings explicitly leaves receipt/scope qualification to the caller.
- execution_contracts.canonical returns a finite canonical JSON string, digest returns its SHA-256, and validate_target checks the existing closed execution_target_v1 shape. The addendum's stated target fields match this shape.
- practical_execution_state._immutable and _read provide the declared immutable canonical-JSON receipt mechanism. _immutable requires an existing parent directory; this is an ordinary caller precondition.
- native_lifecycle.prepare_job reserves a command without dispatch. LocalJobPolicy and run_local_job are existing bounded local interfaces. prepare_local_infernal/local_infernal_plan were read in full as evidence of the reusable original-plan/lifecycle pattern; RNA still needs its own producer validators and binding.
- ExecutionTargetReader._native/read_target and _qualified/observe_target preserve original practical receipt, assignment and native identity. The separate failed-RNA returnable-handoff branch is already explicitly assigned to root in PLAN; its absence today is known integration work, not a newly discovered missing owner.
- NativeInfernalResults, NativeInfernalReturns, native_infernal_acquisition and native_infernal_result_publication were read in full. They supply concrete examples of selected-action authentication, saved capture, grading custody and immediate-child return validation. Their global numerical-completeness/native-success predicate must not be copied into RNA delivery completion; ADDENDUM already corrects that distinction.
- EpisodeReturnRecords was read in full. The adapter can reuse its saved context, original commission, immediate-child and frozen-return authentication. No new return authority or model-composed report is needed.
- EpisodeReceipts.receive was read in full. RNA source-only admission needs the already-planned RNA-specific no-expansion registration. The existing preparation-bundle exclusions show the exact mechanism; they do not automatically cover RNA.

The exact topology definitions, all-dot zero counts, mean/fraction denominators, explicit pair-composition parameters, separate native MFE/evaluation values, unavailable uncertainty and changed-parameter recalculation have no identified interface/formula defect in this review. Numerical correctness has not been tested here.

## Scope and verification record

Read the immutable attachment in full, AGENTS.md, GOAL.md, EPISODE_STRUCTURE.md, TIME_AWARE_ESTIMATION.md, PRACTICAL_EXECUTION.md, its original additive contract, TASK_AND_STEERING.md, TOOL_KNOWLEDGE.md and TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md. Read both current fixed rows and local binding rows from research/tool_grader_goal_2026-10-24/SCOPE.json and WORK_STATUS.json, plus the historical inventory rows named by AGENTS.md. Read all 552 lines of PLAN.md and all 949 lines of CONTRACT_ADDENDUM_001.md.

The immutable purpose and all 16 principles were reread after source inspection and again before final handoff. No scientific program, environment probe, test suite, configured model, network acquisition, API job or HPC work was run. Only text/file inspection and this new packet were performed. No production code, existing test, original plan, design file, accounting row, historical receipt or BLAST file was edited.

Neither RNA tool, live ViennaRNA execution nor complete episode integration is declared verified. ViennaRNA's absence is the recorded planning qualification and was not reprobed. Root owns acceptance of these corrections and fresh implementation assignments.
