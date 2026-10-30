# Masking retained results and selected publication

This is the frozen implementation contract for worker616 and the separate host
adapter owner. It implements610/001–006 and615/001–003; it is not a replacement
goal. The original user attachment remains authoritative. Root explicitly approved
the required capture and operation/native_outcome additions below before coding.

## Ownership and exact ports

616 owns only new sequence_masking_result_views.py,
native_blast_masking_result_worker.py, native_blast_masking_result_publication.py,
uniquely named focused tests and this verification directory. Shared dispatch,
results/returns adapters, prompts and progress rows belong to other owners.

```python
prepare_native_blast_masking_result(store, *, bundle, bundle_artifact_ref,
    artifacts, capture, directory, policy) -> Prepared
publish_selected_masking_result(store, *, source_ref, prepared, selector,
    directory, policy) -> Publication
validate_masking_publication(store, *, source_ref, prepared, selector,
    publication) -> Publication
validate_masking_prepared(prepared) -> Prepared  # pure closed shape
validate_prepared_masking_result(store, prepared, *, bundle=None) -> Prepared

validate_masking_result_selector(selector, *, operation) -> Selector
masking_fact_sources() -> dict[str, JSONSchema]
project_masking_result(*, source_ref, operation, native_outcome, sheet,
    calculations, statistics, occurrences, selector, failures) -> Projection
validate_masking_projection(projection, *, source_ref, operation, selector,
    occurrences) -> Projection  # pure typed selected-value validation
run(plan) -> WorkerManifest
```

The host passes the actual complete Capture to prepare, not a reconstructed
success-shaped capture. artifacts must equal capture.artifacts and the selected
bundle reference must equal capture.bundle_artifact_ref. Invalid or unauthenticated
bundle/capture arguments raise ContractError. The host owns original target/plan
and received-source admission. Preparation never initiates capture or native work.

## Closed shared records

All keys below are required. Nullable means explicit null. All retained values
are finite JSON and unknown keys are rejected. Operation, NativeOutcome,
Occurrence, Failure, Check, Count, Fraction and StatisticsBinding are the613 core
shapes, not new competing schemas or numerical policies.

```text
Prepared = {
 version: "native_blast_masking_prepared_v1",
 bundle_artifact_ref: string,
 source_grading_artifact_ref: string|null,
 sheet_artifact_ref: string|null,
 calculations_artifact_ref: string|null,
 statistics_artifact_ref: string|null,
 operation: Operation,
 native_outcome: NativeOutcome,
 occurrences: list[Occurrence],
 failures: list[Failure],
 worker_completed: boolean
}

Publication = {
 version: "native_blast_masking_publication_v1",
 source_ref: string,
 prepared_sha256: 64 lowercase hex,
 selector: Selector,
 projection_artifact_ref: string,
 status: Status,
 artifacts: list[Occurrence],
 quantities: list[Quantity],
 checks: list[Check + {source_ref:string}],
 statistics: list[StatisticsSelection],
 failures: list[Failure + {source_ref:string}],
 record_refs: list[string]
}

Projection = {status, artifacts, quantities, checks, statistics, failures, record_refs}
Status = {source_ref:string, state:"complete"|"partial"|"failed"|"unavailable",
          native_state:"succeeded"|"failed"|"incomplete"|"unknown",
          output_complete:boolean}
Quantity = {source_ref:string, record_key:string,
            quantity:QuantityName, value:Count|Fraction}
StatisticsSelection = {
 source_ref:string, statistics_ref:string, occurrence_id:string,
 reference_binding:StatisticsBinding|null,
 fields: object containing EXACTLY the requested statistics_fields,
 unit_counts:list[original core native unit-count rows],
 missing_unit_codes:list[integer>=0]
}
```

QuantityName is exactly input_length, native_interval_count,
merged_interval_count, masked_positions, unmasked_positions, changed_positions or
masked_fraction. The last name has a Fraction; all others have a Count with the
core's exact unit and missing reason. No quantity is calculated in a projector.

Selector has exactly version="native_blast_masking_result_selector_v1",
mode="native_result"|"saved_recalculation", records, quantities,
statistics_fields, statistics_unit_codes, include_checks, artifacts,
saved_sheet_ref. records and artifacts are exactly610/006's original-position and
direction/role/ordinal selectors. Statistics fields are format_version,
algorithm_version, unit_length, thresholds and percentiles; arrays are unique.
Counts creation accepts no quantities and no selected sequence entries. A
non-WindowMasker operation accepts no statistics selections. saved_sheet_ref is
null for native_result and the exact Prepared.sheet_artifact_ref for
saved_recalculation. Counts have no sequence sheet and cannot select that mode.
Export NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA for host request construction.

## Meaning and references

The six exact sources are execution.masking_status (Status object),
execution.masking_artifacts, execution.masking_quantities,
execution.masking_checks, execution.masking_statistics and
execution.masking_failures (the corresponding arrays). Export FACT_SOURCES,
IDENTIFIER_NAMESPACES and the individual *_SCHEMA constants for host integration.

record_refs contains source_ref then explicitly selected artifact_ref values,
deduplicated in order. It is the Store delivery/grant list, not a claim that
internal record keys are Store records. Source-only selection grants no auxiliary
artifact. Statistics provenance references are typed relationships, not grants.

Virtual namespaces are native_blast_masking_record (exact core input record_key),
native_blast_masking_occurrence (Occurrence.occurrence_id), and
native_blast_masking_statistics (original statistics occurrence_id + "#/statistics").
The host result_identity/resolve/received resolver must resolve these only inside
an authenticated selected Publication: quantities and selected checks/failures
identify record keys; artifacts identify explicitly selected occurrences;
StatisticsSelection identifies its selected statistics reference. Resolution
returns only selected facts and must not hydrate unrequested full sheets or
artifacts. A virtual reference does not create a new scientific observation or
grant its underlying artifact. Scalar quantities do not grant full input FASTA.

The projector filters record checks/failures to selected original record positions
and retains relevant global diagnostics. Missing selected ordinal, artifact or
quantity produces a typed failure; no replacement record or fabricated zero.
Missing selected unit codes remain in missing_unit_codes and are never zero rows.
Known qualified nullable cells (hard_mask_ambiguous and not_applicable) retain
their meanings. Native status and requested result fulfillment remain distinct;
none of these states is a scientific acceptance threshold or continuation rule.

## Retention, authentication and failure behavior

The source_grading artifact is the existing tool_grading_artifact_v1 envelope,
provider episode.execution_result and native_artifact_ref=bundle_artifact_ref.
Its closed grading payload holds version="native_blast_masking_retained_v1",
the original Bundle, actual Capture, bundle_sha256, Operation, NativeOutcome,
occurrences, all Prepared artifact-reference fields except source_grading itself,
failures, worker_completed, numerical_artifacts (role -> exact artifact/hash/size
descriptors) and worker_receipt_artifact_ref. Exact producer and capture failure
objects, including diagnostic artifact references, survive in Bundle and Capture.
Only their deterministic core Failure projections cross the public boundary.

The full-Identity producer masking_occurrence_id helper is the sole current
occurrence identity constructor. Input statistics preserve the supplied original
statistics_binding.statistics_occurrence_id. That supplied declaration never
establishes authenticated_generation on its own: the host admits any received
generated relationship against its original producer source/artifact. Counts
use the actual generated output/reference/attempt binding; source_ref stays null
during source construction. References do not silently become masking targets.

All captured descriptors must match actual retained bytes and the original
bundle's expected/staged/final identity. Changed/unsealed diagnostic files never
enter parsing as originals. Missing capture rows preserve actual CaptureFailure
reasons, and independently missing native files preserve Bundle failures. No
diagnostic prose enters core Failure.code. Worker errors use restricted machine
codes, with original exception text retained only as worker diagnostics.

Parsing is bounded by caller LocalJobPolicy. parse_calculate reads only retained
authenticated file descriptors and calls613's parsers/calculator. It retains full
Sheet/Components for masks and full parsed statistics for either WindowMasker
mode. Native failure does not discard valid bytes. Partial output without an
explicitly proved mapping remains unassigned; it never acquires a guessed ordinal
binding or a zero measurement. Original input preflight failures remain recorded.
The worker can finish handling an incomplete native result: worker_completed
describes that deterministic stage, not native completion. Missing primary
artifacts legitimately leave numerical refs null, with precise failures.

project_saved reads actual retained Sheet/Components/statistics. native_result
copies retained components; saved_recalculation reads the exact authenticated
saved sheet and calls the one613 calculator, retaining recalculated components
with the selected projection. It never reruns native thresholds or acquisition.
These are internal stages of one selected results action, with no private
episode loop, additional observations or credit.

Publication authenticates the original source, Prepared envelope and exact
selector. The immutable projection artifact is itself a closed envelope tying
source_ref, prepared_sha256, selector, actual worker receipt and projection.
Replay validates this envelope and retained byte identities, with no parsing,
recalculation, worker launch, writes or original native-path dependency. A changed
supplied Prepared/Publication/selector/source is rejected. Incomplete prior worker
or publication intents are errors, never automatic restarts. A selected worker
failure is retained in an immutable receipt and raises a specific ContractError;
the host may make a later explicit repair selection.

## Verification boundary

Use529/run_checks.py check071_masking_result_core with check005 dependencies,
20GiB memory/4GiB scratch/zero swap/no wall cap. Only saved authentic612 outputs
and labelled synthetic fault fixtures; no repeated native commands, network,
HPC, authentication or local database work. Verify equality with core values,
position-based selection, strict source/artifact grants, hard-mask ambiguity,
statistics clipping versus native thresholds, partial/missing/error distinctions,
altered custody/selector rejection, actual saved-sheet recalculation and frozen
publication replay after native paths disappear. Separate host episode/return
integration and concrete prompt feedback remain explicit downstream work.
