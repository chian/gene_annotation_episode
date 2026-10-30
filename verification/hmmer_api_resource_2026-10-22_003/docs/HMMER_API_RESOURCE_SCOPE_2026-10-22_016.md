# Adopted isolated API reported-duration implementation scope016

Root reviewed the complete concrete coding proposal002 and adopts its A/B/C
interfaces below for an isolated generation003. This is implementation work
within the fixed goal; it changes no scientific scoring formula, numerical
continuation rule, waiting horizon, information unit or active run. No user
answer/approval is inferred. The active fixed-target scientific process and all
prior source/evidence generations remain unchanged.

The exact reviewed proposal002 SHA256 is
4840f1857db2677a4e4a4b770a2bea6a9b95b4d40f5809c68f02766601725dc2.
It is copied verbatim after this adoption preface, retaining its historical
unadopted wording. This preface establishes adoption and resolves the following
cross-owner details before coding:

1. Every reference to a physical job in the A ledger paragraph means the
   explicitly declared logical provider-job reported-result unit. No physical
   attempt/retry-completeness claim is authorized for API statistics.
2. A owns and exports pure function reported_result_identity(registry_ref,
   remote_id). It validates a canonical UUID and returns exactly
   {observation_sha256, measurement_ref}. observation_sha256 hashes canonical
   JSON {version:hmmer_reported_result_observation_v1, registry_ref, remote_id,
   observation_unit:logical_provider_job_reported_result}. measurement_ref is
   api_reported_duration_ followed by that digest. B imports/reuses this actual
   function rather than inventing another identity. B's source_sha256 is the
   SHA256 of the canonical original complete first-witness JSON. Source IDs,
   receipt hashes, equal durations and later page hashes are not new identities.
3. C's ApiReportedTimingFactReader constructor is (ledger, *, ports), where
   ports is the actual PublicSearchPorts owner. It verifies the same ledger,
   Store/registry/resource identity and uses only existing read_operation,
   read_snapshot/open_scope/inspect ports for custody qualification. It does
   not guess private table layouts, recreate clients or infer source facts.
4. Exact A/B/C fields/functions, optional caller definition, ledger CAS,
   per-selected-POST condition provenance and union monitoring information
   semantics below are the shared coding contract. Any additional necessary
   consumer/file change must be reported concretely before expanding ownership.
   No agent edits another owner's source or the root's active live tree.
5. Generation003 is a new copy of frozen API002 at runtime pin
   9007ce019b0df13f122cdc53772b45e56684a39755b2e79c9027de2a451fbd1c,
   /tmp/gene-annotation-hmmer-api-20261022-003. A/B/C code can be developed in
   parallel against these declared interfaces. Coding dependencies name exact
   values; they do not require waiting for all producer implementations.
   Concurrent capacity, including already running curation work, determines
   dispatch timing. Root owns final join/review and connected verification.

The primary-source evidence is preserved read-only at
verification/hmmer_provider_elapsed_semantics_2026-10-22_001,
manifest SHA256
368790f69f5718828ab100ead3ac4d9a9e3a009fcf19f5f76e1159455d918fd0.
It proves documented provider-reported seconds and inspected compatible source
boundaries, not the deployed daemon commit or job turnaround. The old actual
service verification remains unregistered, unexported and unrescored.

---

# Unadopted HMMER reported-duration coding contract, 2026-10-22-002

This is proposal002 for root review, not an implementation claim. Proposal001 remains unchanged. Root has adopted the distinct reported-result statistical unit/table as the direction; adoption of this corrected exact contract remains pending. It changes no repository source or saved run. The inspected implementation baseline is `/tmp/gene-annotation-hmmer-api-20261022-002`. The live configured_development_002 source, state, processes and model sessions are outside this work.

## Fixed scope and meanings

- Consume the provider's source-qualified `result.stats.elapsed` for phmmer/hmmscan, using the conservative measure `hmmer_reported_search_elapsed_seconds`.
- The observable statistical unit is **one reported completed result per logical provider job UUID**. Provider retry history is unknown. It is not a proven physical attempt, and reported-result counts are not attempt/reliability counts.
- Preserve the original first acquisition's observation timestamp. It is not a provider execution-end timestamp. Do not invent start timestamps, queue time, HTTP time, turnaround, throughput or scaling.
- Initial prospective routing covers the existing Launch and launch_api decisions for their assigned job request, before order/POST where the original paths permit it. Scientific-parent information before its first launch commission remains open.
- Compatibility means the same **exposed technical configuration**, despite unknown remote build, allocation, database release/digest and corpus sizes. It does not guarantee identical remote execution. Missing remote operands remain null. Do not add result-only nseqs to a measured class or manufacture it for prospective classes.
- Use the caller's already supplied positive monitoring information unit. Do not add timing credit to scientific or operational controller credit, invent a new numeric unit, or introduce another completed action.
- Existing PublicSearchPorts fields and operation/order/claim/HTTP capture/receipt formats remain unchanged. Timing is an explicit opt-in side binding. Existing actual-service verification receives no registration, export or rescore.
- No endpoint instrumentation, waiting model, HPC change, support-library change, polling/retry/timeout/stopping policy, new episode or extra model call.

Primary meaning proof is retained at `/tmp/hmmer-provider-elapsed-semantics-20261022-001/FINDINGS.md`. API source pin is `a3d3421ba317e58131a009647b4697d09640004a`, `result/models.py:319-383,696-788`, `search/client.py:52-131`, `search/tasks.py:24-108`. Source-compatible daemon interval is master processing wall time, with queues and final forwarding excluded, but the actual deployed daemon build/clock remains unverified. The proposed conservative label makes no stronger deployed-boundary claim.

## Existing seams and incompatibilities

`ProviderJobOperations.read_operation(receipt_ref)` and `read_snapshot(receipt_ref)` supply actual immutable custody. `result_once` performs exactly the selected GET; cached/replayed receipts perform no new search. The selected result is published by `PublicSearchResultPublisher.publish` without network.

`ExecutionClass` currently rejects remote search phases, null memory/scratch and this measure. `RunStatistic` and its history table explicitly mean one physical phase attempt. **Do not insert a provider UUID into that type.** Add the separate typed statistical boundary below, while retaining native formats and meanings.

Existing pure projection seam is `capture_execution_scopes(path, scopes, *, assigned_execution_class_ref=None)` followed by `ResourceToolEstimator.estimate_context(capture)`. Existing forecast `job_ref` and `sample_ref` are native homology namespaces; both remain null for API forecast records. ResourceEpisodes already gathers adapter forecasts through `decision_context`; HmmerServiceResourceAdapter currently returns an empty list.

## Shared conventions

All JSON objects below are closed: every listed key is required, and additional keys are forbidden. Nullable keys remain present. Digest means lowercase 64-character SHA256. UTC means timezone-aware UTC ISO-8601. `seconds` means finite nonnegative JSON number. No NaN or infinity is accepted. Local references are nonempty constrained identities, not arbitrary explanatory prose. Record dictionaries are serialized with existing canonical JSON. Public source records use the existing Store `source` type; there is no new biological record type.

Disposition envelopes always have exactly:

```python
TimingDispositionV1 = {
    'version': 'api_timing_disposition_v1',
    'state': 'available' | 'unavailable' | 'not_applicable' | 'conflict',
    'code': None | (
        'not_opted_in_order' | 'timing_binding_unavailable' |
        'start_binding_unavailable' | 'start_condition_unknown' |
        'submission_binding_unavailable' | 'submission_binding_conflict' |
        'submission_binding_ambiguous' | 'reported_duration_missing' |
        'reported_duration_invalid' | 'reported_duration_identity_conflict' |
        'reported_duration_conflict' | 'timing_custody_unavailable' |
        'unsupported_statistics_configuration' | 'history_unavailable' |
        'history_schema_unavailable' | 'statistics_identity_conflict' |
        'timing_source_publication_unavailable'),
    'order_binding_ref': str | None,
    'intent_ref': str | None,
    'submission_binding_ref': str | None,
    'measurement_ref': str | None,
    'source_ref': str | None,
}
```

`available` requires code null and the references appropriate to that operation. `not_applicable` means no timing eligibility was established; it never authorizes a new submission. `conflict` preserves the first record and returns its measurement_ref. Dispositions are timing facts only; they do not replace the original operation outcome or its failure.

## A: local eligibility, pre-POST binding, source qualification and first witness

A owns new `gene_annotation_episode/api_timing_records.py` and the narrow opt-in hooks in `public_search_operations.py`. A does not own a forecast formula, credit projection, scientific publication or episode loop.

```python
@dataclass(frozen=True)
class ApiTimingBinding:
    ledger_path: Path
    history_path: Path
    resource_id: str
    monitoring_information_unit: float
    # as_record/from_record validate the exact caller configuration below.

class ApiTimingLedger:
    def __init__(self, *, run_id: str, registry: dict,
                 binding: ApiTimingBinding, statistics: ApiReportedStatistics): ...
    def as_record(self) -> dict: ...
    def register_new_order(self, order: dict, *, request: dict, scope: dict
                           ) -> TimingDispositionV1: ...
    def before_actual_submit(self, operations: ProviderJobOperations,
                             job_ref: str, *, operation_key: str
                             ) -> TimingDispositionV1: ...
    def bind_submission_receipt(self, operations: ProviderJobOperations,
                                receipt_ref: str) -> TimingDispositionV1: ...
    def resolve_submission_binding(self, operations: ProviderJobOperations,
                                   job_ref: str, remote_id: str
                                   ) -> TimingDispositionV1: ...
    def receive_result(self, operations: ProviderJobOperations,
                       receipt_ref: str) -> TimingDispositionV1: ...
    def read_measurement(self, measurement_ref: str) -> ApiReportedDurationWitnessV1: ...
    def retry_exports(self) -> ApiTimingRecoveryV1: ...
```

`ApiReportedStatistics` is B's typed helper described below. Imported types must be the actual classes in the single loaded gene_annotation_episode package; do not redeclare them in fixtures/adapters. Dependency imports can be guarded by TYPE_CHECKING where needed.

Keep `PublicSearchPorts` unchanged. Add only optional `timing: ApiTimingLedger | None = None` to ProviderJobOperations construction. Check matching Store/run/registry/resource bindings before installing the hook. Original methods retain their arguments and return shapes.

`register_new_order` runs only on the new-order path, once its exact order/request/scope exist, before that order is returned. Replaying an existing order must not retroactively register it. It writes an immutable eligibility marker to the separate timing ledger. An orphan marker after an interrupted Store transaction is harmless: every later use must revalidate the actual committed order through operations.open_order/open_scope. Timing journal failure is caught separately and must not roll back valid order creation.

`before_actual_submit` runs at the existing branch immediately before `_dispatch` of each eligible selected POST, outside the Store transaction. It does not run on cached/replayed/recovery paths. It obtains B's class/start-condition capture for this exact selected submission_operation_key, persists that immutable intent, and then permits the original selected dispatch to continue. Missing history yields unavailable-before-submission condition capture, which means UNKNOWN, never observed unspecified; it does not block POST. Timing-ledger failure must not block POST, but later numerical export remains unavailable without a persisted matched intent and known original condition. Never recapture conditions at result/export/recovery time. An intent records selected pre-dispatch provenance; executor failure may still establish that no POST was sent.

Keep original submission claims and receipts unchanged. A later explicit retry after a proven not_sent receipt has a NEW submission_operation_key and NEW pre-dispatch condition capture; retain every prior intent. Conditions may have changed between the not-sent selection and the selected retry. Do not reuse the first intent merely because job_ref is the same. A replay/recover operation creates no new intent and recaptures no condition. The reported-result contract still makes no physical-attempt-count claim.

After an actual successful original submit receipt is committed, ProviderJobOperations calls bind_submission_receipt with THAT original submit receipt_ref. The helper validates operation submit, completed outcome/no failure, original job/request identity, nonnull submission snapshot, canonical returned UUID equal to snapshot JSON id and receipt.remote_id, and the matching intent key (registry_ref, job_ref, receipt.operation_key). A cached later submit receipt with no original snapshot cannot establish a new binding. The winning immutable binding names the original receipt/key/UUID and its matching intent; it does not name the most recent intent.

Recovery hook: recover_submission already obtains or reconstructs original from the original submit claim and _finish_submit. After committing those existing records, call bind_submission_receipt(operations, original['receipt_ref']), never with the recover_submission wrapper receipt. Errors remain separate timing dispositions; returned public operation objects stay unchanged. Result import calls resolve_submission_binding if needed. That helper inspects only actual saved submit operations for this job/UUID via inspect/read_operation/read_snapshot, validates the original successful snapshot and exact operation_key, then binds its original intent. It never chooses a latest condition. Zero valid original receipts yield submission_binding_unavailable; multiple contradictory winning receipts/keys yield submission_binding_ambiguous, with no numerical export. An existing agreeing binding is reused; a conflicting one is preserved and reported.

Missing original intent may still permit a source-qualified submission binding whose intent_state is unavailable and intent_ref null. This preserves known receipt/UUID provenance without pretending a pre-POST condition was observed. Its local duration fact remains useful, while numerical export stays unavailable.

Separate ledger tables (a new SQLite file, not a second provider-job authority):

- `api_timing_bindings(run_id PRIMARY KEY, binding_ref, registry_ref, data)`: immutable exact opt-in configuration.
- `api_timing_orders(registry_ref, job_ref, data, PRIMARY KEY(registry_ref,job_ref))`: immutable eligibility, original order key/request digest/scope and binding_ref.
- `api_timing_submission_intents(registry_ref, job_ref, submission_operation_key, data, PRIMARY KEY(registry_ref,job_ref,submission_operation_key))`: one immutable pre-dispatch context per selected POST operation. No replay/recovery recapture. All not-sent predecessor intents remain retained.
- `api_timing_submission_bindings(registry_ref, remote_id, binding_ref UNIQUE, data, PRIMARY KEY(registry_ref,remote_id))`: immutable source-qualified winning submit receipt/key/job/UUID plus its matching intent_ref and intent_state. This is logical-provider-result provenance, not a physical attempt ledger.
- `api_timing_measurements(registry_ref, remote_id, measurement_ref UNIQUE, data, PRIMARY KEY(registry_ref,remote_id))`: first valid qualified reported duration and its original witness, immutable.
- `api_timing_export_dispositions(measurement_ref PRIMARY KEY, revision, data)`: derived recoverable export status only; it cannot change a witness or class/start context.

Writers use short BEGIN IMMEDIATE transactions and equality checks. First-witness insert is INSERT-if-absent followed by read/compare under the same lock. Equal physical-job reported duration and identity reuse the original data even when another page has a different receipt/entity hash. A differing elapsed value or identity is a structured conflict. Never replace the first witness. Export dispositions advance with revision CAS; a lost CAS rereads the winner. They cannot assert recorded unless B confirms the idempotent shared-history write.

```python
ApiTimingOrderBindingV1 = {
    'version': 'api_timing_order_binding_v1', 'binding_ref': str,
    'run_id': str, 'registry_ref': str, 'job_ref': str,
    'order_operation_key': str, 'request_sha256': digest,
    'scope': dict, 'scope_sha256': digest,
}

ApiTimingSubmissionIntentV1 = {
    'version': 'api_timing_submission_intent_v1', 'intent_ref': str,
    'order_binding_ref': str, 'registry_ref': str, 'job_ref': str,
    'submission_operation_key': str, 'request_sha256': digest,
    'start_context': ApiReportedStartContextV1,
}

ApiTimingSubmissionBindingV1 = {
    'version': 'api_timing_submission_binding_v1', 'binding_ref': str,
    'order_binding_ref': str, 'registry_ref': str, 'job_ref': str,
    'remote_id': canonical_uuid, 'request_sha256': digest,
    'submission_operation_key': str, 'submission_receipt_ref': str,
    'submission_snapshot_ref': str, 'submission_entity_sha256': digest,
    'observed_at': UTC,
    'intent_state': 'matched' | 'unavailable', 'intent_ref': str | None,
}

ApiReportedDurationWitnessV1 = {
    'version': 'hmmer_reported_duration_witness_v1', 'measurement_ref': str,
    'order_binding_ref': str, 'intent_ref': str | None,
    'submission_binding_ref': str | None,
    'registry_ref': str, 'resource_id': str, 'job_ref': str,
    'remote_id': canonical_uuid, 'request_sha256': digest,
    'acquisition_receipt_ref': str, 'snapshot_ref': str,
    'entity_sha256': digest, 'field_path': '$.result.stats.elapsed',
    'duration_measure': 'hmmer_reported_search_elapsed_seconds',
    'observation_unit': 'logical_provider_job_reported_result',
    'elapsed_seconds': seconds, 'observed_at': UTC,
    'semantics_version': 'hmmer_reported_elapsed_source_v1',
    'start_context': ApiReportedStartContextV1 | None,
}
```

Qualification uses original `read_operation`, `read_snapshot`, `open_order`, `open_scope`, `inspect` and `validate_remote_identity`. Require result operation, completed outcome/no failure, SUCCESS response/result dictionary, stats dictionary, explicitly matching stats.id/algo/database, supported algorithm and finite nonnegative stats.elapsed. Use actual snapshot.sha256 and receipt.observed_at. Do not expose transport headers or read their contents for timing. Optional counts/CPU fields neither establish identity nor enter this contract.

measurement_ref is the digest of a closed identity tuple `{version,registry_ref,remote_id,observation_unit}`. It identifies a logical job's reported result, not a proven physical attempt. The frozen full witness is separately content-bound in the ledger. Equal values are never identities.

`receive_result` runs only for the original selected successful result receipt, after provider custody commit and independently of biological import success. It resolves the winning submit binding and matched original intent; if missing, retain a local witness with explicit null provenance/start context and a structured unavailable disposition, never a fabricated condition. It never calls result_once. Timing parse/conflict/storage/export errors add their disposition alongside the original outcome; they cannot convert completed/partial biological work to failed. Recovery reopens the saved receipt and first witness, never repeats HTTP or rewrites a completed action.

## B: exact exposed features, separate reported-result statistics and snapshots

B owns `run_statistics.py`, `resource_estimation.py`, `execution_expectations.py` only if its generic helper needs support, and new `api_reported_statistics.py`. Native statistical data/refs/attempt semantics remain unchanged.

```python
@dataclass(frozen=True)
class ReportedResultStatistic:
    observation_sha256: str
    source_sha256: str
    observed_at: str
    elapsed_seconds: float
    condition_ref: str | None

class ApiReportedStatistics:
    def __init__(self, binding: ApiTimingBinding, *, registry: dict): ...
    def execution_class(self, request: dict) -> ExecutionClass: ...
    def capture_start(self, request: dict) -> ApiReportedStartContextV1: ...
    def export(self, witness: ApiReportedDurationWitnessV1) -> ApiTimingExportV1: ...
    def capture(self, request: dict) -> dict: ...

RunHistory.record_reported_result(
    self, scope: ExecutionClass, statistic: ReportedResultStatistic
) -> str
```

`record_reported_result` requires the actual exact types, and only accepts the reported-result phase/measure. Store in a separate `reported_result_statistics` table with unique observation_sha256, class_ref, captured condition_state and canonical data. The old `run_statistics` table and `record(ExecutionClass, RunStatistic)` are untouched. Repeat equal writes succeed; changed class/source/value/condition for the same observation identity conflict. The source hash binds the first witness, not the latest page. A typed observed result says nothing about failed internal attempts or their cost.

Add `remote_protein_homology_search -> https` as an explicit phase/backend pair. For only this phase, allow null memory/scratch and `reference_state='unknown'`, require the chosen reported measure, and require remote CPU/implementation/corpus-size fields null. Local validation remains unchanged. No new dataclass field may silently alter old native ExecutionClass refs.

The closed input to parameters_sha256 is:

```python
ApiExposedTechnicalFeaturesV1 = {
    'version': 'hmmer_exposed_technical_features_v1',
    'provider': 'hmmer', 'algorithm': 'phmmer' | 'hmmscan',
    'database_name': str,             # actual service database selector
    'database_release': None, 'database_sha256': None,
    'provider_defaults': 'not_exposed',
    'parameters': dict,               # closed technical schema below
    'taxonomy_filter': 'none',
    'compatibility': 'same_exposed_technical_configuration_unknown_remote_revision',
}
```

parameters has no arbitrary keys: numeric finite `E,domE,incE,incdomE,T,domT,incT,incdomT,popen,pextend`; threshold is `evalue|bitscore`; mx is a matrix selector string matching `[A-Za-z0-9_.-]{1,64}`. Preserve absent vs explicitly supplied technical defaults. Empty include/exclude taxonomy lists normalize to taxonomy_filter none. Nonempty taxonomy filters yield unsupported_statistics_configuration for forecasts/export; they do not block the actual selected search or publication. No taxonomy IDs/count proxy, subject_ref, gene name, FASTA label, query/sequence digest/content, result UUID, page selector or source identity enters shared features. Query_residues is the original normalized request.query_length; page_size is a retrieval parameter, not search-duration compatibility.

Exact scope fields: phase remote_protein_homology_search; backend https; resource_id caller-bound actual resource; implementation_sha256 null; parameters_sha256 digest of the above; memory_bytes/scratch_bytes/cpu_threads/reference_residues/reference_records/wall_seconds null; query_residues positive actual request size; reference_state unknown; duration_measure hmmer_reported_search_elapsed_seconds. Different query lengths or technical options do not transfer numerically.

```python
ApiReportedStartContextV1 = {
    'version': 'api_reported_start_context_v1',
    'execution_class': dict, 'execution_class_ref': str,
    'condition_ref': str | None,
    'condition_capture': 'captured_before_submission' | 'unavailable_before_submission',
}

ApiTimingExportV1 = {
    'version': 'api_reported_export_v1',
    'state': 'recorded' | 'unavailable' | 'conflict' | 'not_applicable',
    'code': None | 'history_unavailable' | 'history_schema_unavailable' |
        'statistics_identity_conflict' | 'start_binding_unavailable' |
        'start_condition_unknown' | 'submission_binding_unavailable' |
        'unsupported_statistics_configuration',
    'measurement_ref': str, 'observation_sha256': digest | None,
    'execution_class_ref': str | None,
}

ApiTimingRecoveryV1 = {
    'version': 'api_timing_recovery_v1',
    'scan_state': 'available' | 'unavailable',
    'pending_count': int, 'recorded_count': int,
    'unavailable_count': int, 'conflict_count': int,
}
```

capture_start reads only the configured shared history using a nonblocking reader and preserves unavailable condition capture. captured_before_submission plus condition_ref null means the history read actually established no configured condition (observed unspecified). unavailable_before_submission plus condition_ref null means UNKNOWN, not unspecified. export requires an exact winning submit binding, matched intent, and captured_before_submission context; otherwise return start_binding_unavailable/start_condition_unknown and retain the useful local duration fact without writing shared statistics. Never resolve a missing condition_ref with today's history. export may not create history or recapture a condition. The new table is installed only by explicit history initialization/upgrade, never by an episode forecast lookup. Missing table is a structured history-schema-unavailable disposition. A ledger retains pending witnesses; retry_exports uses the same IDs, source, class, condition and destination and never reruns work.

For reported scopes only, RunHistory.capture returns this distinct snapshot body; native capture bodies and hashes remain unchanged:

```python
ReportedResultStatisticsSnapshotV1 = {
    'version': 'reported_result_statistics_v1', 'class_ref': str,
    'execution_class': dict, 'history_through_sequence': int,
    'current_condition': dict,       # existing closed condition representation
    'observation_unit': 'logical_provider_job_reported_result',
    'statistics': [
        {'condition_state': 'unspecified' | 'normal' | 'degraded' | 'unavailable',
         'reported_result_count': int, 'mean_seconds': seconds,
         'min_seconds': seconds, 'max_seconds': seconds}
    ],
    'expectation_method': 'empirical_reported_result_duration_mean_by_condition_v1',
}
```

No attempt_count, failure/cancellation rate, retry count, unobserved lower bound, zero-time missing sample or physical-attempt outcome support is manufactured. The reported-only schema states the sampling limitation directly. Snapshot identity uses the existing execution_expectation content-addressing convention. The existing capture envelope remains `{version,execution_classes,status,code,snapshots}`.

Extend the exact ResourceToolEstimator class with explicit `with_reported_results()` configuration. Default construction/as_record/from_record retain v2 native behavior. An opted-in instance serializes a new version containing both named methods; no subclass or replacement estimator/controller is introduced. Add a reported-result projection branch and closed API estimate schema. Existing native ESTIMATE_SCHEMA remains intact; report_source accepts the union of existing native and new reported schemas.

API estimate has all existing ESTIMATE_SCHEMA fields, but method is `exact_exposed_configuration_current_condition_reported_duration_mean_v1`, job_ref/sample_ref/elapsed_seconds null, timing_relation unknown, outcome_support null. Add exactly:

```python
'observation_unit': 'logical_provider_job_reported_result',
'reported_result_support': None | {'reported_result_count': int},
'compatibility': 'same_exposed_technical_configuration_unknown_remote_revision',
```

successful_duration_samples equals the current-condition reported_result_count; expected_total_seconds is the mean of the named reported interval, never job turnaround. Empty available history produces count zero and no_matching_history; unavailable history leaves support null; original snapshots stay with decisions. Validate observation unit, class, snapshot digest, count/range relationships and current condition before projection. New support cannot be interpreted as failure/reliability evidence. The native support branch is not reinterpreted.

## C: explicit caller configuration, decision inputs, receiving source and one monitoring timing value

C owns `hmmer_resource_adapter.py`, `resource_episodes.py` (aggregation only), `resource_service_setup.py`, `assembled_service_setup.py`, `episode_composition.py`, `episode_services.py` (binding access only), `runtime.py`, and new `api_timing_information.py`. C consumes A/B contracts; it does not derive durations, reconstruct classes or choose configurations.

Caller configuration is exactly:

```python
ApiTimingBindingRecordV1 = {
    'version': 'hmmer_api_timing_binding_v1',
    'ledger_path': absolute_path, 'history_path': absolute_path,
    'resource_id': str,
    'duration_measure': 'hmmer_reported_search_elapsed_seconds',
    'observation_unit': 'logical_provider_job_reported_result',
    'compatibility': 'same_exposed_technical_configuration_unknown_remote_revision',
    'monitoring_information_unit': positive_finite_number,
    'scope': 'new_orders_in_this_bound_run',
}
```

The new explicit `bind_assembled_services_with_public_search_timing(..., api_timing, ...)` factory is opt-in. It receives the existing monitoring information unit and requires equality with the record and any supplied existing NativeTimingInformation unit; it supplies no default/replacement number. Keep existing factories unchanged. Bind this record in saved factory definition and a new `hmmer_service_resource_adapter_v2` descriptor; v1 reconstruction remains unchanged. v2 reconstruction reopens the exact ledger/history/resource/registry/unit and opted-in ResourceToolEstimator; mismatches fail binding reconstruction before work.

No PublicSearchPorts field changes. The resolver/factory creates ProviderJobOperations with A's optional timing binding, and the v2 adapter verifies the actual operations binding matches its saved descriptor. Root/direct factories and detached worker reconstruction resolve the same binding. `EpisodeComposition` may carry a default-null API duration-fact reader; Workflow composes the opt-in wrapper below with the actual NativeTimingInformation. If none was previously supplied, explicit opt-in constructs that existing native reader with the SAME caller-supplied unit. Native-only runs continue using the original NativeTimingInformation unchanged, with exactly their old binding definitions, outputs and numerical behavior. No new EpisodeApplicationServices decision layer is required.

Adapter hook signatures:

```python
HmmerServiceResourceAdapter(..., *, ports: PublicSearchPorts,
                            timing: ApiTimingLedger | None = None,
                            resource_estimator: ResourceToolEstimator | None = None)

decision_context(context: BindingContext) -> {
    'resource_tool_estimates': list[dict],
    'api_reported_execution_expectations': list[dict],
    'api_execution_options': list[ApiExecutionOptionV1],
    'api_timing_export_recovery': ApiTimingRecoveryV1 | None,
    'api_timing_planning_disposition': TimingDispositionV1 | None,
}

ApiExecutionOptionV1 = {
    'version': 'api_execution_option_v1', 'provider': 'hmmer',
    'subject_ref': str, 'algorithm': 'phmmer' | 'hmmscan',
    'database': str, 'parameters': dict,          # local actual operands only
    'execution_class_ref': str, 'proposal_ref': str,
}
```

Use existing read-only request_for_assignment normalization, which may inspect an existing order but must not create one. Launch and launch_api get the same class for identical assigned work, including before an order exists. Scope/constraints/input-version qualification remains authoritative. Failed statistics supply explicit missingness and never prevent the original launch choices. ResourceEpisodes aggregates these additional keys without replacing another adapter's fields. Exact snapshots/options are journaled with the decision.

Keep distinct context key api_reported_execution_expectations. Do not add these snapshots to commission expectation_snapshot_refs, waiting_support, WaitInputs or pending-job turnaround prediction. ExecutionContextController copies that key at the existing completed-action boundary, separately from at-selection/after-action forecasts and raw credit. No new observation. Replay uses original saved context without refresh.

C gets A's result disposition after provider receipt commit and independently attempts source publication. Biology retains original status/record_refs/changed_record_refs. Add api_timing_disposition and successfully published api_timing_refs to the outcome. Failed biological projection may still return valid timing information without becoming a completed failed action.

```python
ApiTimingSourceBodyV1 = {
    'version': 'api_reported_timing_source_v1', 'run_id': str,
    'scope': dict, 'subject_ref': str,
    'witness': ApiReportedDurationWitnessV1,
}

ApiTimingFactV1 = {
    'receipt_ref': source_reference,
    'job_ref': resource_execution_reference,
    'duration_measure': 'hmmer_reported_search_elapsed_seconds',
    'observation_unit': 'logical_provider_job_reported_result',
    'elapsed_seconds': seconds, 'observed_at': UTC,
}
```

Source metadata: provider episode.hmmer_reported_timing; accession measurement_ref; uri/text_ref/request_ref null; artifact_ref canonical closed body; version api_reported_timing_source_v1; retrieved_at witness.observed_at; operand_refs [original subject_ref]. Scope/subject originate from original order, never the receiving parent's broader scope. First source content is immutable; identity follows Store origin=tool rules. Validate source custody against A's first witness and original result body without another model call. Headers/arbitrary diagnostic text do not enter typed facts. Unknown pre-POST condition affects numerical export, not whether source-backed elapsed is useful received timing information.

The API reader returns FACTS AND IDENTITIES ONLY, no score and no numeric unit:

```python
class ApiReportedTimingFactReader:
    def __init__(self, ledger: ApiTimingLedger): ...
    def as_record(self) -> dict: ...
    def read_details(self, store, scope, *, known_record_refs: list[str],
                     initial_known_record_refs: list[str],
                     details_limit: int | None, details_offset: int
                     ) -> ApiTimingFactsV1: ...
    def validate_report(self, store, value, *, schema: dict) -> None: ...

ApiTimingFactsV1 = {
    'version': 'api_reported_timing_facts_v1',
    'new_information_identities': [
        {'kind': 'logical_provider_job_reported_result',
         'registry_ref': str, 'remote_id': canonical_uuid}
    ],
    'reported_result_count': int,
    'api_execution_measurements': [ApiTimingFactV1],
    'next_offset': int | None,
}

class ReceivedExecutionTimingInformation:
    def __init__(self, native: NativeTimingInformation,
                 api: ApiReportedTimingFactReader): ...
    def as_record(self) -> dict: ...
    def read_details(self, store, scope, *, known_execution_refs: list[str],
                     initial_execution_refs: list[str],
                     known_record_refs: list[str], initial_known_record_refs: list[str],
                     details_limit: int | None, details_offset: int) -> dict: ...
    def __call__(self, store, scope, **knowledge) -> dict: ...
    def report_sources(self) -> dict: ...
    def validate_report(self, store, value, *, schema: dict) -> None: ...
```

The wrapper is explicitly optional and derives its only information_unit from the supplied existing NativeTimingInformation. The opt-in configuration requires equality with the caller's existing unit; the API reader cannot assign another. Native details retain their original NativeTimingInformation qualification, attempt identity and frozen baseline. API facts qualify only actual received timing sources, using their original baseline. Typed information identities are disjoint:

- native: (native_physical_phase_attempt, attempt_sha256), using the existing native receipt reader;
- API: (logical_provider_job_reported_result, registry_ref, remote_id).

The wrapper projects the cardinality of the UNION of novel typed duration facts after subtracting the original typed baseline. It uses `information_unit * union_cardinality`, not the sum of two independently configured scores. Distinct kinds never collapse merely because hashes/numbers match. Same API result across pages, reads, return and redelivery adds no identity; inherited facts add none. Both native and API readers retain their existing semantic identities. Export availability does not decide local timing-information usefulness.

The opt-in read_details output is exactly:

```python
ExecutionTimingInformationV1 = {
    'credit': number,
    'monitoring_information_credit': number,       # same single value as credit
    'monitoring_information_binding': dict,
    'measured_attempt_count': int,                 # native only, original meaning
    'reported_result_count': int,                 # API logical result only
    'native_receipt_count': int,
    'api_receipt_count': int,
    'native_execution_measurements': list,         # existing closed native facts
    'api_execution_measurements': [ApiTimingFactV1],
    'native_next_offset': int | None,
    'api_next_offset': int | None,
}
```

Pagination applies the same requested details_offset/details_limit independently to each typed detail array; its two next offsets name those separate arrays. Counts and union credit always describe all qualified novel facts, independent of detail pagination. native_receipt_count retains the existing native reader's deduplicated receipt_count meaning; api_receipt_count is the analogous number of distinct qualified API duration facts after baseline subtraction, not the number of GET receipts or provider attempts.

The scalar's explicit saved opt-in definition is exactly:

```python
ExecutionTimingInformationBindingV1 = {
    'version': 'received_execution_timing_information_v1',
    'information_unit': positive_finite_number,
    'native_duration_facts': dict,                 # original native.as_record()
    'api_reported_duration_facts': dict,           # API reader.as_record(), no score/unit
    'contribution': 'existing_unit_per_new_typed_received_duration_fact',
    'baseline': 'union_of_original_inherited_native_and_api_duration_identities',
    'scientific_credit': False,
    'controller_effect': 'preserve_existing_controller_scalar_paths',
}
```

This augments the EXISTING monitoring_information_credit value and its existing numeric report source. Expose native_execution_measurements and api_execution_measurements as separate typed detail sources/counts. **Do not add api_timing_information_credit, reported_api_timing_information, a second timing scalar or another numeric report source.** Native-only bindings/outputs remain exactly unchanged. Existing source_credit_view composition of selected monitoring observations with received timing information remains its existing host path; the wrapper replaces only the native-duration component when explicitly opted in.

Preserve scientific and operational controller credit exactly. Preserve existing native job_monitor scalar supplementation using only its original native contribution; do not inject the new API count into any controller input. The one monitoring_information_credit view can include the newly received API duration under the explicit binding while the configured continuation paths/rule remain unchanged. No timers/fit/threshold/raw action observations change.

Runtime consumers to wire completely:

- Workflow construction installs the default-null API fact reader from composition and, only for opt-in, the generic wrapper over the actual NativeTimingInformation. Native-only branches stay untouched. Save/reconstruct the exact wrapper/component definition through original caller descriptors; reject mismatched unit/reader/resource before work.
- DecisionSource.execute receives recorded api_timing_refs even when science failed, analogous to receive_native_outcome, without completing failed actions. Combined wrapper knowledge uses existing native receipt refs plus generic record selection, each with its frozen original baseline.
- _receive_form receives only declared timing source refs after fact/schema validation. Existing EpisodeReceipts handles original baseline and duplicate delivery. Unrequested facts do not cross child boundaries.
- report_sources/facts/validate_report/resolver/episode.monitoring_information use the one active timing component. Opt-in replaces the original native-only monitoring_information_credit definition with the explicit UNION definition, rather than publishing a parallel score. Existing native fact validation is delegated unchanged; API facts validate original witness/job/scope. Parent-selected field names, forwarding and redelivery remain valid.
- Forecast refs resolve against original API journal declarations and scope, including forwarded original child declarations. No refresh or private child history inspection, and no provider handle in homology_job/job_sample fields.
- ExecutionContextController preserves original API snapshots/forecasts at the completed-action boundary. CompletionLedger, ordering, controller_value and method_loop remain unchanged unless connected tests reveal a necessary factual routing correction.
- Source publication, export recovery and union refresh create no observations and never rewrite closed forms/histories.

## Dependencies and disjoint ownership

Freeze A/B/C JSON and signatures before coding. A depends on B's class/start/export helper; B consumes A's witness as a closed value, not its ledger internals; C receives A's dispositions/witnesses and B's captures. Imports must avoid constructing Store/Workflow or performing HTTP at module import. Root owns joining only, plus temporary harness/verification artifacts; root does not silently edit agent-owned source while they work.

| Owner | Exclusive source files | Exclusive tests |
| --- | --- | --- |
| A | api_timing_records.py; public_search_operations.py | test_api_timing_custody.py |
| B | api_reported_statistics.py; run_statistics.py; resource_estimation.py; execution_expectations.py if needed | test_api_reported_statistics.py; narrow existing statistical regression corrections |
| C | api_timing_information.py (API fact reader and optional native/API union wrapper); hmmer_resource_adapter.py; resource_episodes.py; resource_service_setup.py; assembled_service_setup.py; episode_composition.py; episode_services.py; runtime.py | test_api_timing_runtime.py; test_api_timing_reconstruction.py |

NativeTimingInformation, ApiSearchOperationalCredit, ProgressInformationCredit, waiting.py, WaitInputs, numerical.py and method_loop have no planned source changes. The optional wrapper delegates native reading without editing NativeTimingInformation. Adding reported-result statistics does not reinterpret their physical/native facts. Every owner reports deviations before expanding its file set.

## Required connected verification, without a new service/model run

1. Build prospective Launch/launch_api contexts for an assigned actual normalized request while no provider order exists; assert no HTTP/order/staging, same technical class before/after order, explicit unknown remote fields, original frozen snapshot in selected action. Scientific-parent precommission coverage is explicitly not asserted.
2. Script a future opted-in selected submit/status/result path through actual ProviderJobOperations and adapter, with fixture HTTP only. Preserve original closed receipts/claims/port descriptors. Verify each selected POST operation's original condition, the actual winning submit receipt/key/UUID-to-intent binding, exact source body, separately committed timing result and ordinary biology publication.
3. Proven not_sent selection under condition A, explicit retry under changed condition B: two retained intents keyed by their selected operation keys, actual successful submit receipt/UUID matched only to retry intent B. Replaying either selection and recover_submission recapture neither condition. Cut after successful receipt commit but before binding; recovery binds that original receipt/key and B, not the first/latest arbitrary intent. Missing/ambiguous/conflicting bindings preserve local fact usefulness and exclude numerical export.
4. Same result/page twice, another page, cached acquisition, recover_submission and action replay: one logical-result witness, one shared reported-result row, one received timing contribution, no duplicate HTTP or action observation. Equal elapsed for two different actual UUIDs remains two observations.
5. Same UUID with conflicting elapsed/algorithm/database: retain first witness and global sample; structured conflict alongside valid independent biological work. Malformed/missing/negative/nonfinite elapsed never invents duration; foreign identity never qualifies.
6. Cancel parent after actual dispatch starts; existing shielded capture survives. Recovery imports the original receipt/witness without POST/GET repetition. Crash cuts before/after eligibility marker, start intent, first witness, shared export, source publication and runtime outcome admission preserve valid work and explicit missingness.
7. Missing/locked history, absent new history table and export storage failure: selected API work continues, witness retained, original condition preserved, idempotent later export changes only disposition. A condition read that was unavailable at the winning pre-POST point remains UNKNOWN; later history recovery may not turn null into unspecified or recapture a condition, and that witness remains locally useful but numerically unexported. No repricing of prior context/action/closed child and no synthetic observation.
8. Source receipt typed child-to-parent delivery through actual resolver/validator/EpisodeReceipts: requested facts arrive, unrequested facts do not; inherited/repeated/redelivered duration earns zero; body tampering and cross-scope refs reject. Failed biological projection preserves timing information without a completed failed action.
9. Scientific credit, annotation-support credit, operational handoff/acquisition credit, native timing, raw local yield observations/controller decisions and wait estimator inputs are unchanged. The optional wrapper uses exactly one caller unit and one monitoring_information_credit over the typed UNION of native and API duration facts. Assert no api_timing_information_credit/reported_api_timing_information or other extra numeric source. Native-only output/binding equality is exact; mixed native/API inherited/repeated/new identities yield the expected union count without summing independent scores.
10. Two isolated opted-in runs can learn an exposed-config reported-duration forecast through the same shared history. Different length/mode/technical controls/resource are incompatible; taxonomy-filtered configs return explicit unsupported statistics, not a launch gate. No biological identities or query/taxonomy digests enter shared class/statistic data. Reported-result count must never appear as physical attempt/reliability support.
11. Saved factory/adapter reconstruction in a real detached fixture worker preserves original timing paths/config/unit/registry and rejects replacements before transport. No live configured_development_002 object/process/workspace is used. Native v2 estimator serialization, old class refs/snapshots, existing native regressions and no-API assembly remain unchanged.

Root joins these paths at one immutable isolated generation after A/B/C tests, then runs the existing public-search/resource/forecast/native/typed-admission groups plus the new connected tests. Test counts are per invocation and overlap is disclosed. Actual service verification, configured-model timing-informed decisions, deployed daemon attestation and broad scientific-parent prospective routing remain unverified unless separately authorized and run.

## Adoption condition

Root has adopted the distinct ReportedResultStatistic/history/snapshot/forecast observation unit and exposed-config grouping as the direction. Proposal002 incorporates the required single existing monitoring-information value and exact per-selected-POST/winning-submit condition provenance. No source coding is authorized by this file itself; root must review/adopt these corrected exact cross-owner shapes before assignments. There is no new numeric/unit/wait decision, and no API logical UUID is coerced into native physical attempt_count semantics.

## Inspection record

Read requirements in immutable attachment, repository AGENTS.md/GOAL.md, complete EPISODE_STRUCTURE.md and TIME_AWARE_ESTIMATION.md. Read complete run_statistics, resource_estimation, execution_expectations, execution_timing, execution_recording, ordinary_execution, native_timing_information, public_search_operations, public_search_publication, hmmer_resource_adapter, hmmer_resource_information, hmmer_progress, resource_episodes, resource_operational_credit, api_resource_credit, episode_progress_credit, progress_records, wait_estimation_inputs, resource_service_setup, assembled_service_setup, episode_services, episode_composition, episode_application_services and method_loop/runtime. Read complete affected runtime classes/methods: DecisionSource, ExecutionContextController, Workflow construction, configure_execution/commission_child, native receipt/form admission, source credit/report sources/facts/validation/resolver, execute/controller_value, relevant saved-binding checks, and complete method_loop Episode class. Read complete relevant PublicClients HTTP/HMMER and provider request/identity/snapshot methods. Read semantics worker's full pinned-source findings. Only the specifically authorized credential-free actual response.entity was inspected; no transport metadata or live workspace database was read.
