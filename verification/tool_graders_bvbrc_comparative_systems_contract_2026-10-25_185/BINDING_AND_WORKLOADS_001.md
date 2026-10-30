# Proposed tool information, host connections and coding workloads

All proposed names/files are for review. No production names are registered by this package. Existing generic AppService support is reusable, while a ComparativeSystems scientific provider, tool-specific selection and typed return are absent.

## Four-field tool information

**Name:** `bvbrc.comparative_systems`

**Description:** Compare the stored pathway, subsystem and PLFam/PGFam assignments of explicitly selected BV-BRC genomes; retain the native reports, accepted feature-length/count measurements, explicit genome/component populations and qualified comparative components.

**Resources:** `api`. Actual configured resource_id and native AppService/Workspace endpoints come from caller configuration. This does not claim local/HPC execution or a successful live service job.

**Instructions:** Supply the intended genome IDs and genome-group paths, with both native arrays explicitly present. Preserve their original order and repetitions; the service deduplicates its executed genome union. Supply output_path and output_file explicitly. The service compares stored annotations of selected genomes; this selection need not include a candidate function/name. Raw sequence investigation can motivate genome/feature acquisition or annotation elsewhere under the existing parent. This operation does not silently submit annotation or replace the selected genomes. The native application always produces pathway, subsystem and protein-family views; select requested result views without inventing a native recipe switch.

Commission the existing launch episode with the selected job, scope, constraints and requested typed handoff. Its API child selects `api.bvbrc_appservice.prepare`, any necessary explicit Workspace input/output operations, then `submit` using the exact preparation receipt. Preparation submits nothing. Submission is one `AppService.start_app2` and retains original task identity. The API resource's generic monitoring task can select status or stdout/stderr. Preserve native state/time/log facts; no fixed polling, hidden retry, cancellation or stall interpretation belongs in these tools.

Commission the existing results episode for the original task. Select task_info(job_result_id), metadata for that job-result object, its actual manifest bytes, exact manifest_member entries, capabilities and downloads as needed. This describes available operations, not a prescribed action itinerary. A guessed basename/folder/HTML path is not artifact custody. Retain complete selected JSON/TSV/report artifacts. Select `bvbrc_comparative_systems` adapter version `1` with the declared native formats, explicit authoritative-document selections, calculation parameters and bounded requested fields. JSON tables contain TSV strings and are not generic molecular arrays or BLAST JSON. Each future artifact can be selected by the parent's requirement_id before acquisition; an already acquired document can use its possessed exact source/artifact pair.

Native pathway/subsystem reports from the inspected source drop an object from each nonempty API chunk. Retain those reports as source-defined reports with their actual represented populations. Their conservation values are observed assignment occupancy/density, not pathway completion. Hex family counts are decoded only when unambiguous; overflow remains unavailable for per-genome counts. Genome omissions, missing descriptions, duplicate representations, inner-join losses and unknown reference releases remain explicit. Select additional Data API records or reference membership only when the parent requests measurements that need them. Calculators consume the supplied saved sheet and explicit parameters; no parsing/calculation triggers acquisition. Return only requested original numerical facts and qualifications; full sheets/raw data remain stored. No annotation probability or independent scientific score is assigned to downloads, job receipts or status checks.

Tool information is `child_tool_info` support for an existing process. This proposal edits no model TASK/STEERING templates and creates no complete episode template.

## Existing implementation consumers to connect

These paths were inspected to locate integration boundaries; no live episode path was executed for this task.

| Boundary | Existing consumer / requirement |
| --- | --- |
| Selectable scientific tool | `ExecutionEpisodes.resource_tool_contracts` in `execution_episodes.py` currently installs configured Homology, GenomeAlignment, GenomeComparison and alignment/phylogeny providers. Add ComparativeSystems only when its exact adapter implementation pin is configured. Retain the ordinary scientific tool map and commission routes. |
| Native preparation | `bvbrc_application_definitions.get_application_spec`, `prepare_application`, `_check_application_inputs`; the ComparativeSystems branch currently requires some genomes/groups, but generic list item schemas are only qualified. The tool-specific schema must require both arrays of valid strings plus output destination without rewriting originals. |
| Selected native operation | `BVBRCAppServiceService.prepare` / `invoke` / `decode` in `api_bvbrc_appservice.py`. `submit` calls start_app2 using exact prepared operands; status calls query_tasks. Do not add a separate service client. |
| Durable selected operation | `APIServiceExecution.execute` routes to `BVBRCAppServiceHost.execute_locked`; that calls `perform_selected_call`, retains original intent/snapshot/receipt, and publishes one original action outcome. Existing ownership/effect recovery stays intact. |
| Original input/task custody | `AppServiceInputs.bind_inputs`, `_Binding.definition_input`, `submit_inputs`, `manifest_member`, `download_capability`; `BVBRCAppServiceHost.read_handoff/read_target`. Definitions, parameter identity, task, manifest member and download capability are distinct bindings. |
| Result acquisition | `decode_job_result`, `qualify_download` in `bvbrc_appservice_readers.py`; `build_acquisition_value`, `build_artifact_bundle` in `bvbrc_appservice_bundle_values.py`. Byte-range completeness and full object completeness are distinct. |
| Provider registry | `bvbrc_appservice_adapters.bind_adapters` and `selected_adapter`. Add `bvbrc_comparative_systems_bundle_adapter` with ADAPTER_ID, ADAPTER_VERSION, complete transitive `implementation_sha256`, `validate_parameters`, `validate_requested_form`, `consume_bundle`. No automatic adapter choice. |
| Same-action numerical publication | `AppServicePublications._grade` gathers exact artifact bytes and supplied values; `publish` retains sheet/components as separate content bindings and records requested form status. Parsing/calculating here does not manufacture another action. An explicit ComparativeSystems supplied-Data host input collector may be needed; it must validate already selected results, not fetch. |
| Exact requested result status | `AppServicePublications._requested_status` has an explicit provider set that permits irrelevant optional missing dependencies without making the requested projection partial. Add the reviewed provider semantics only after finite fact-dependency tests. Original required missing artifacts still remain partial. No scientific truth gate is added. |
| Latest own result versus preserved history | `AppServicePublications.completion`, `read_latest_adapter_result` in `bvbrc_appservice_saved_results.py`, and the pattern in `BVBRCProteomeReturns.facts`. Latest partial/invalid acquisition must not revive an older successful result. Closed/admitted historical returns keep their named original source. |
| Typed closure/forwarding | Proposed `BVBRCComparativeSystemsReturns` follows the inspected `BVBRCProteomeReturns`: original saved facts, native identifiers, frozen requested schema, byte bindings and owner are checked; current `facts`, `received_facts`, `validate_received_report`, `record_admission`, `resolve_own`, `resolve_received` forward without parser/calculator/model calls. |
| Integration registration | `APIServiceExecution.__init__` and `resolve`; `BVBRCAppServiceHost.facts`; `ExecutionEpisodes._appservice_sources`, `received_report_facts`, `resolve_received_reference`, `validate_received_report`, `received_form_references`, and `resolve`. Register the exact new finite sources in those existing boundaries. |
| Receiving scientific episode | `Workflow.report_sources`, `validate_report`, and closing-facts assembly in `runtime.py` already call the episode bindings. These are consumers to verify, not files to redesign. Existing `EpisodeReturnRecords` retains admission identity and forwardable facts. No changes to method_loop, controller, scheduler, scientific credit or evidence-axis/W05. |

Existing generic operation information is complete in `bvbrc_appservice_tool_info.py`; reuse it. The parent route is `launch → launch_api` and `results → results`, with the configured resource_id. The scientific parent gets tool information and requested typed facts, not arbitrary remote-management permissions.

## Finite parent-return contract

Proposed fact source families:

* `bvbrc_comparative_systems_measurements`: one explicitly selected native/count/length/component field with a `NumericCellV1`.
* `bvbrc_comparative_systems_ratios`: one selected ratio with numerator, denominator, units and exact population/reference identity.
* `bvbrc_comparative_systems_populations`: selected requested/represented/acquired population counts and bounded completeness code.
* `bvbrc_comparative_systems_memberships`: selected genome–family/pathway–EC/subsystem–role relation, identifiers, presence state and source locations. This does not return all raw rows unless the finite original selector explicitly requests them.
* `bvbrc_comparative_systems_requirements`: exact missing input role/code and affected requested field IDs.
* `bvbrc_comparative_systems_qualifications`: finite source-defect/completeness/identity/category codes and affected field references.
* `bvbrc_comparative_systems_request_status`: `satisfied|partial|invalid|unavailable` for exactly the requested projection, not scientific success.

Each outer fact is `{source_ref, field, value}`. `source_ref` is an authenticated original execution-result source, and `field` is a validated identifier for an original requested field. Entity identifiers are validated against the exact selected saved sheet: family kind+ID, genome ID, pathway/EC or subsystem/role tuples. These identifiers are not arbitrary user prose or invented Store records. Quantity names, units, methods, states and qualifications are closed enums; descriptions/function claims are not unrestricted strings in a report. Each return selector names explicit fields/entity IDs and its expected cardinality; exceeding that cardinality fails rather than silently truncating. No universal runtime result quota is invented.

The requested-form grammar should resemble the existing reviewed scientific providers: top-level object with `additionalProperties=false`, exact required field names, each marked `x-bvbrc-comparative-systems` with finite kind+selector. Semantic validators require matching populations, references, units and numerator/denominator relationships. A parent cannot remove a missing-state qualification while forwarding an available number, change `program_reported_derived` into observed biology, replace a source-executed synthetic basis with service evidence, or substitute an unrelated same-taxon record.

Provider result shape is exactly the existing adapter result envelope: `adapter_id`, `adapter_version`, `status=ok|partial|invalid`, nullable full `sheet` and `components`, requested `facts`, `missing_requirements`, `diagnostics`. An invalid request/schema/identity can fail the whole selected provider; malformed one artifact/view preserves valid unrelated views. A finite failure exposes code, phase, affected source/pointer/entity/field and valid partial dependencies. No model-written failure summary is required. An accurate requested unknown can be a satisfied requested fact when that is the original contract; a requested **available** complete-population value remains partial until its declared input requirements are met.

## Proposed exclusive implementation workloads

Fresh coders receive this package plus the original verbatim objective/principles and must reread that authoritative text after substantial external/native work and before tool completion. Contracts must be reviewed by root before production coding. No coder changes fixed accounting, episode design or a sibling's files. All paths below are proposed production paths relative to the repository; only each workload's own named paths are editable. If shared integration files are occupied by D183/F184, stage I's exact integration delta separately until root assigns their ownership. This does not block independent N/C/D/P files.

### N — native readers and populated numerical sheet

Own `gene_annotation_episode/bvbrc_comparative_systems_native.py`, `bvbrc_comparative_systems_sheet.py`, `bvbrc_comparative_systems_sheet_contracts.py`, `bvbrc_comparative_systems_sheet_schemas.json`; `tests/test_bvbrc_comparative_systems_native.py`, `tests/test_bvbrc_comparative_systems_sheet.py` and its dedicated fixture subdirectory. Covers all six native source profiles and separately stored PLFam/PGFam/pathway/EC/subsystem views. Implements parse/build signatures in the numerical contract; no calculators or acquisitions.

Input: exact source-defined document bytes plus OriginalRequest, explicit DocumentSelection and supplied-record structure. Output: `NativeDocumentResultV1`, `ComparativeSystemsSheetV1`, validation exports. It can start against the frozen filled examples without waiting for D's extractor. Tests include manual versus pandas TSV dialects, JSON duplicate keys, unknown version, omitted/empty rows, placeholders, arbitrary order, ID/name collisions, hex255/256, join multiplicity and zero/missing distinction. Source-layout variant bytes are preserved even when unusable.

### C — deterministic quantities and recalculation

Own `gene_annotation_episode/bvbrc_comparative_systems_calculators.py`, `bvbrc_comparative_systems_calculation_contracts.py`, `bvbrc_comparative_systems_calculation_schemas.json`; `tests/test_bvbrc_comparative_systems_calculators.py`. Implements the explicit component formulas and parameter shape. No source parsing, host, network, inventory or original-query mutation.

Input: N's frozen sheet schema and saved filled sheet fixtures (schema contract is sufficient to begin). Output: `ComparativeSystemsComponentsV1`, parameter validation, selected component dependency records. Independent tests check 75%, 44.444…%, 2/3, 1.5, 81.649658 aa population SD interpretation, CV0.408248, density>1, Jaccard empty union, partial scope, conflicting duplicates, and changed explicit reference/population selection from the same saved sheet with acquisition forbidden.

### D — explicit supplied Data API population extraction

Own `gene_annotation_episode/bvbrc_comparative_systems_data_inputs.py`, `bvbrc_comparative_systems_data_contracts.py`, `bvbrc_comparative_systems_data_schemas.json`; `tests/test_bvbrc_comparative_systems_data_inputs.py`. Implements the pure supplemental handoff in `DATA_POPULATION_HANDOFF_001.md`. No changes to the existing Data API service/query grammar/field registry without a separate reviewed source delta.

Input: selected authenticated `bvbrc_data_qualified_result_v1` objects, their retained source bytes/bindings, explicit PopulationSelection. Output: `SuppliedRecordSetsV1`, exact membership sets, duplicate/join/completeness qualifications and requirements. Can be implemented/tested independently using native Solr-envelope fixtures and the established Data sheet schema. Unavailable live authentication affects only real live evidence, not these functions. Tests exercise full/partial one-page, pagination gaps/overlaps, snapshot drift, unknown numFoundExact, unsupported pathway.annotation filter, local PATRIC selection, group snapshot mismatch and reference multivalued IDs/names.

### P — pure provider assembly and bounded projection

Own `gene_annotation_episode/bvbrc_comparative_systems_bundle_adapter.py`, `bvbrc_comparative_systems_bundle_contracts.py`, `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_bundle_projection.py`, `bvbrc_comparative_systems_fact_contracts.py`, `bvbrc_comparative_systems_bundle_schemas.json`; `tests/test_bvbrc_comparative_systems_bundle.py`, `tests/test_bvbrc_comparative_systems_projection.py`.

Input: existing ArtifactBundle plus exact selected bytes/supplied values, original task and original finite requested form. Output: host-compatible adapter envelope; sheet and components remain separate objects. Implements requirement_id/exact-binding document resolution, N→D→sheet→C consumption only as dependencies actually requested, and pure saved projection validation. It never picks a primary document by first occurrence or calls a network client. N/C/D signatures and fixtures let this be coded in parallel; integrated tests wait only for delivered functions, not all live resource qualifications. Missing supplemental populations do not block native descriptive requests. Full implementation pin must include all actual transitive code and JSON assets.

### I — tool information, receiving returns and host integration

Own new `gene_annotation_episode/bvbrc_comparative_systems_tool_info.py`, `bvbrc_comparative_systems_returns.py`, `bvbrc_comparative_systems_host_inputs.py`; `tests/test_bvbrc_comparative_systems_episode_flow.py`, `tests/test_bvbrc_comparative_systems_returns.py`; new launch knowledge file only if the existing resource library actually consumes it. Exclusive shared-file ownership, assigned by root after conflict review: `bvbrc_appservice_adapters.py`, `api_service_execution.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_publication.py`, `execution_episodes.py`, and package-data declaration only if needed.

Input: P's adapter/fact/parameter signatures; D's selected qualified input contract; exact existing return/custody paths. Output: selected scientific tool → launch/API child → retained artifacts → pure provider → stored sheet/components → bounded own/received typed facts. Implement closed-result admission, nested scientific forwarding, tamper rejection and latest-result semantics using existing return infrastructure. Do not edit runtime prompts/method_loop/controller, introduce a grade action, restore execution at root or write final annotation-credit formulas. Native live service evidence remains explicitly unverified until actual authorized service use occurs. Shared-file conflicts are exact merge/ownership dependencies only.

Root owns acceptance, reconciliation with ongoing shared-file work and fixed progress updates. No whole-row completion is implied by the source/package evidence or these proposed workload boundaries.


## Additive shared-contract closure

The nested handoff shapes and focused corrections are now specified in `HANDOFF_SCHEMAS_001.json`, `SCHEMA_DECISIONS_001.md`, and `HANDOFF_CLOSURE_002.md`. The latter supersedes incomplete parse/build/provider signatures, supplies explicit analysis/producer/population inputs, closes calculated/native fact selectors, and defines the acyclic shared-schema ownership graph. `FILLED_EXAMPLES_001.json` and `CONTRACT_VALIDATION_001.json` identify the exact conforming review examples and checks. This addition preserves the original proposal; it does not approve or implement it.
