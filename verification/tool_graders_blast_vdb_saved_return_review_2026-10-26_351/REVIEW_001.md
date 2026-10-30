# 351 focused saved-generation and return-authority review

One concrete receiving-boundary defect is reproduced. No production, existing
tests, design records or accounting files were changed by 351. This packet is a
review of 347's integration and its actual consumers, not completion of either
VDB tool or a review of the scientific model.

## Finding: a source-only return admits unrequested native artifacts

The actual immediate-child form requested only
`execution_blast_database_result_refs` and contained one result source. It did
not request numerical rows, the saved-input descriptor, or any artifact. Native
return validation admitted exactly that source reference. The subsequent shared
receipt operation nonetheless added **10 previously unknown auxiliary native
artifacts** as `child_form` receipts, and `ExecutionEpisodes.resolve(parent,
artifact_ref, 'artifact')` returned true for all 10.

This is a receiver-authority change, not just full native bytes being retained
internally. The emitted source has provider `episode.execution_result`, version
`native_blast_database_bundle_v1`. Its auxiliary refs include the captured native
report and other original bundle files. The fixture's producer and PBS transport
are synthetic; the Store, typed return validation, original commission/action
records, receipt admission and execution resolvers are the production code.

The complete path is:

1. `native_blast_database_acquisition._source_payload`, line279, records every
   captured bundle artifact in `auxiliary_artifact_refs`. Retaining that custody
   is valid and should remain intact.
2. `NativeBLASTDatabaseReturns.record_admission`, line229, and
   `ExecutionEpisodes.received_form_references`, line1474, return only refs
   actually named in the authenticated form. In the probe that is one source.
3. `EpisodeReceipts.receive`, line97, recursively follows `Store._refs`,
   `state.py:638`. The existing source-only exceptions cover HMMER/Infernal
   preparation sources, but not this native BLAST database source. All ten
   auxiliary artifacts receive new durable parent ledger rows.
4. `NativeBLASTDatabaseReturns.resolve_received`, line243, does not handle the
   `artifact` namespace and returns `None`. General resolution falls through.
   The actual `ExecutionEpisodes.resolve` probe accepts each leaked artifact;
   the production `EpisodeServices.reference_in_context`, line213, likewise
   falls back to `reference_in_scope`, line198, when the received resolver gives
   no decision. That production service fallback was inspected, not executed by
   this probe (the existing synthetic host has `services=None`).

Evidence:

- `test_source_only_artifact_authority.py`: one independent integration probe.
- `probe001/temporary/test_source_only_return_does_n0/source-only-admission-evidence.json`:
  exact form/schema, explicitly admitted source, before/after artifact lists,
  resolver results and all ten `child_form` ledger rows.
- `probe001/stdout.txt`: the expected no-leak invariant fails; 1 failed in 17.94s.
- `probe001/receipt.json`: actual local lifecycle exit 1, elapsed 18.560386202s;
  20 GiB RAM, 4 GiB scratch, no wall cap, verified systemd limits.
- `probe001/source-before.json` and `source-after.json`: source unchanged during
  this probe, including the relevant acquisition and shared receipt code.

The leak does **not** itself bypass saved-generation authorization: the latter
still requires the exact descriptor received through an authenticated form. It
does violate the separately required requested-artifact boundary and grants
native-file possession to subsequent operations through `_known`.

The minimal repair boundary belongs in shared receipt admission and the native
receiver's artifact-resolution qualification. Preserve complete source/native
custody, explicit requested descriptor artifact access, and separately received
caller artifacts. Use the original selected version/form to scope any changed
semantics; do not delete old ledger entries, rewrite forms/history, or change the
original source identity. A `domain.py` or `state.py` schema change is unnecessary.
Root was sent the reproduced finding before this report; 351 makes no repair.

## Checked saved-generation invariants

These findings are source inspection plus inspection of 347's saved test
artifacts, unless explicitly identified above as 351 execution. No suite was
rerun and no new scientific-model review was performed.

- The new selector is VDB-only. Saved mode prohibits new metadata/source inputs.
  `resolve_saved_function_input` checks exact descriptor equality against real
  original immediate-child forms, walks the commissioning prefix for inheritance,
  and requires known selected refs. It does not authorize from source/hash
  possession alone. The original result context's commission is authenticated.
- `_read_saved_function_input` addresses run/episode/operation and receipt hash,
  authenticates the exact completed selected action and receipt file, checks
  source membership, exact generation descriptor, scope and immutable bytes.
  `_validate_body` resolves the original target and saved receipt chain, requires
  null fresh observation/capture, and validates the real saved intent/publication.
  Cycle and missing-original handling reject without acquisition fallback.
- `_saved_original`, `_saved_request`, `_validate_preparation` preserve the
  original bundle, native attempt, input descriptors, retained source identities,
  subject snapshots, sequence model and input interpretation. The original input
  implementation comes from the addressed manifest. Current implementation and
  explicit function model determine a new calculation identity.
- `_reuse` validates the retained manifest, sealed collection/sheets and saved
  calculations. `calculate_native_blast_database_sheets` copies retained base
  calculations and calls the separate function calculator in saved mode. No
  native parser, populator, base calculator, observation, transfer, network or
  new biological observation appears in that branch. Existing 347 purity tests
  instrument those ports in the bounded worker subprocess; their code and
  retained results were inspected, not independently rerun.
- Per-calculation storage adds the reused manifest hash for saved requests, so
  a scientific identity that intentionally excludes transport receipt identity
  does not overwrite a different reused generation's request. In 347 run006's
  saved-model-repair artifact, returning to the original model recovers the
  original calculation ID while retaining the intermediate receipt as authority.
- 347 run005's exact-generation artifact contains captured plus two saved
  generations. Both saved receipts have null observation/capture, retain the
  exact preceding receipt address and equal input interpretation IDs, and have
  distinct model-dependent calculation IDs. The new tests assert all three
  generations can be received; cell union is confined to the same calculation
  and row identity; forwarding keeps the authenticated cell set.
- New function rows and saved HSP projections are source-only. `result_identity`
  follows the addressed original bundle. The results credit consumer uses the
  original contribution identity, and the tests assert zero reacquisition credit,
  no added biological observations, one runtime own action per collect and
  unchanged original forms/actions/bytes. These are synthetic engineering facts,
  not configured-controller or model-science demonstration by 351.
- Projection completion does not require scientific completeness of every cell.
  Native failure remains unsuccessful; partial/calculator failures stay explicit.
  `ExecutionEpisodes.completion_for_action` and `verify_completion` delegate to
  the existing results proof; `practical_estimator` uses the ordinary exact-zero
  endpoint exception without a synthetic turn. No new scientific gate was found.

## Exact versions and review limits

`SOURCE_PINS_001.sha256` pins the initial 23 production/test files, with full
snapshots under `snapshot/`. `ADDITIONAL_SOURCE_PINS_001.sha256` pins acquisition,
episode service/binding consumers and the inspected Store reference traversal.
These additions also have snapshots. Input/calculator pins match root's supplied
`5be7856a...` and `31d88b0d...`; their scientific repairs were outside this review.

After the probe, 347 changed only the results operation catalog and its exact
ExecutionEpisodes call at this boundary, excluding native status selection in
saved mode. Those complete changed functions were inspected, not executed by
351. `SOURCE_CHANGES_002.sha256`, `snapshot002/`, `RESULTS_CHANGE_002.patch` and
`CATALOG_CHANGE_002.patch` preserve that distinction. The concurrently expanded
integration test was snapshotted separately; new cases added after the original
351 probe are not claimed tested or fully reviewed here.

`EVIDENCE_PINS_001.sha256` pins 338's contract/acceptance/addenda, 347's draft trace,
run005/run006 manifests/logs/receipts and the particular saved return artifacts
inspected. Run005 was not an all-pass run (21 passed, 2 failed); run006 is the
focused corrective selection (8 passed, 20 deselected). Its scope is preserved
and not added together as independent complete coverage.

No installation, network/API call, live scheduler, database BLAST or credentials
were used. Existing native-science/PBS emitters remained synthetic. No source
fix, tool-completion claim, W05 change or tally change follows from this review.
Before handoff, 351 reread the immutable purpose and all 16 design principles
verbatim. The accepted 338 saved-input/typed-return contract was read in full
within its complete production-handoff section. Goal requirements retain
authority over implementation behavior and test assertions.
