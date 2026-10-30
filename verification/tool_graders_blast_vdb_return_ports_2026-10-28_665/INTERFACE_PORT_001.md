# VDB utility selection, publication and typed-return port

Planning-only record 665/001, 2026-10-28. Root review precedes assignment of fresh coding owners. This record defines implementation boundaries under the original user goal; it does not amend that goal or establish an implemented, tested, installed or resource-bound capability. No application imports, tests, native execution, network calls, acquisition or runtime prompt construction were performed in this planning task.

The fixed common versions are `blast_utility_operation_v3`, `blast_sequence_extraction_v2`, `blast_database_inspection_v3` and `blast_vdb_utility_context_v1`. Ports 643/001, 643/002 and 643/003 define their meanings; implemented shared-core handoff 662/001 and parser handoff 663/002 supersede the provisional version numbers in the early 643 narrative. Formatters remain excluded. The active inventory is 305 operations; the `native/blast_vdb_cmd` row remains pending. This document must not change that row to complete.

## 1. Ownership and exact handoffs

The parent selects the result form and selector in the existing result-child assignment. Infrastructure validates and executes that choice. It does not choose a larger result, resolve a new dependency, infer a sample, launch another native operation, add a grader episode or compose a model restatement of recorded facts.

The native/context owner defined by planner 664 owns the **whole** `native_blast_utility_result_worker.py`, including qualified context, original parsing and saved-project worker delegation, plus its native/job/capture files and new `native_blast_vdb_utility_context.py`. The result owner owns these four production files:

- `gene_annotation_episode/blast_utility_result_views.py`;
- `gene_annotation_episode/native_blast_utility_result_publication.py`;
- `gene_annotation_episode/native_blast_utility_results.py`;
- `gene_annotation_episode/native_blast_utility_returns.py`.

Root owns generic consumers, historical registration, tool/library information and material access integration listed in 665/002. The result owner must not edit the worker or those root-owned consumers concurrently. Common schemas, 655 lexical reader, 662 shared symbol calculator and 663 parsers are reused as dependencies, not reassigned here.

Root's subsequent review split that result partition for coding: fresh 667 owns only `blast_utility_result_views.py` and its own tests; a separate fresh publication owner will own `native_blast_utility_result_publication.py`, `native_blast_utility_results.py` and `native_blast_utility_returns.py`. References to the result owner below mean the responsible owner of the named file, not shared edit permission. Root owns the five material/source consumer checks in 666. This adds no change to the pure interface assigned to 667.

The result owner receives the following exact values, with their existing meanings:

| Producer | Output consumed by this port |
| --- | --- |
| 664 selected native context | `qualified_utility_context(capture)` containing `operation`, `native_outcome`, `occurrences`, `database_binding`, `failures`, `operation_input_occurrences`, `vdb_context` for VDB; legacy context key sets unchanged |
| 663 extraction reader | `SequenceExtraction` version `blast_sequence_extraction_v2`: operation, primary binding, original outcome, stdout/stderr occurrences, operation inputs, closed VDB context, scope, records, missing selectors, unexpected records, completeness, checks, failures |
| 663 inspection reader | `DatabaseInspection` version `blast_database_inspection_v3`: same binding/outcome/input/context relationships, NativeFields, path sections/rows, checks, failures and completeness |
| Existing original-result publisher plus 664 manifest extension | `native_blast_utility_prepared_v1`, immutable `native_blast_utility_retained_v1` grading payload and its existing `worker_receipt_artifact_ref`; a VDB original worker manifest authenticates request-selected metadata/list claims inside that receipt |
| Existing result episode | Original assignment, scope, handoff, action/operation key, selected target, retained capture and earlier acquired-result receipts; none may be replaced by a newly constructed Store |

Keep prepared/retained v1 key sets and the bundle source version. The existing original worker receipt already retains the original plan and manifest; a separate context artifact or prepared-v2 envelope is unnecessary. The exact embedded authentication proof is the 664 handoff dependency. The result owner validates that proof and context identity using the original receipt; it does not read native metadata again. Failure to authenticate context cannot expose a claimed `vdb_context` as verified facts.

## 2. Selector versions

Preserve the exact existing `native_blast_utility_result_selector_v1` branch and its old operation meanings. Add `native_blast_utility_result_selector_v2`, applicable to operation v3 only. Export the existing public `NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA` as a closed `anyOf` of the two version branches. Keep separately named frozen v1/v2 schema constants so callers never mutate the legacy branch by extending a global properties dictionary.

Every key below is required and objects reject additional properties. Arrays described as unique use `uniqueItems: true`; ordinals are integers >= 0. An empty selected array means explicitly select none, not select a default.

```text
version: const native_blast_utility_result_selector_v2
sequences: null | {
  selection: {kind: const selector_ordinals, values: unique uint[]}
           | {kind: const native_row_ordinals, values: unique uint[] | null},
  record_fields: unique enum[] from VDB_RECORD_FIELDS,
  sequence_fields: unique enum[original_sequence, normalized_sequence][],
  include_vdb_identity: boolean
}
database_fields: unique enum[] from the existing NativeField name union
integrity: null | existing v1 integrity selection
preparation: null | existing v1 preparation selection
prepared_database: boolean
include_checks: boolean
artifacts: existing unique {direction, role, ordinal:uint|null}[]
saved_data: existing unique enum[result, prepared_database][]
paths: null | {
  kinds: unique enum[vdb, vdb_alias, blast_db_alias][],
  native_path_ordinals: unique uint[] | null,
  include_sections: boolean
}
vdb_context: boolean
```

`VDB_RECORD_FIELDS` is exactly `native_oid`, `native_identifier`, `native_accession`, `native_reported_length`, `native_length_basis`, `returned_symbol_count`, `molecule`, `requested_range`, `effective_range`. Types are copied from the common extraction-v2 record schema. This is an explicit refinement of 643 section 6: ordinary text sequence fields and optional identity were already separately selected; individual native record measurements must also be selected. No identifier, native length or symbol count is silently included in a sequence-text-only request. The fixed row envelope described below provides only identity/locator/qualification needed to interpret the selected value.

Semantic validation is exact:

1. `sequences` is non-null only for VDB `extract_sequences`.
2. `selector_ordinals` is legal only for original `selection.kind=entries`; every requested ordinal must be in the **original ordered selector occurrences**. Duplicate literal entry values retain different ordinals. This validator rejects an ordinal outside the original request before acquisition; it does not silently create one.
3. `native_row_ordinals` is legal only for original `all_native_sequences` or `all_references`. `values=null` explicitly selects every row already retained from that original native enumeration. It never commissions another enumeration. Explicit ordinals select original `native_row_ordinal`, not a compacted result-array index. A requested native ordinal absent after malformed/skipped output produces a missing record; later valid rows keep their original ordinal.
4. A selected `native_reported_length` must also select `native_length_basis`, so the parent cannot receive an unlabeled length. Other record fields are independently selected. Shared VDB semantics fix the basis to `returned_sequence`, OID/ranges to null and molecule to dna; none establishes full unclipped or genomic extent.
5. Nonempty `database_fields` is legal only for `info` and can contain only the nine VDB NativeField names listed in section 4. Do not accept a classic sequence count as a synonym for a VDB population.
6. `paths` is legal only for `paths` or `paths_all`; kind/ordinal filters intersect. `paths` accepts only `vdb` kind; `paths_all` accepts all three section kinds. `native_path_ordinals=null` selects all retained rows of selected kinds. Sections are included only when `include_sections=true`, in original section order, independently of whether that section has a selected row.
7. `integrity` and `preparation` must be null, `prepared_database` false, and `saved_data` cannot contain `prepared_database` on v2. These old fields remain in the common selector shape without falsely claiming a VDB builder/integrity operation.
8. `vdb_context=true` requests the closed context, not its underlying metadata bytes. It is legal for all VDB modes.
9. Artifact roles are validated against the original VDB operation: original declared database/config/manifest/metadata/preparation inputs; `database_list` only if actually declared; `entry_batch` only for selected entry-batch input; original stdout/stderr/diagnostics output slots. No `extracted_sequences` output is invented when native data is managed stdout. `ordinal=null` explicitly selects all original occurrences of the chosen direction/role, retaining old slot semantics.

Selectors describe requested delivery, not whether native execution succeeded. Status-only, qualified-failure-only, or selected-artifact views remain legitimate choices.

## 3. Projection versions, fact sources and schemas

Keep the old `PROJECTION_FIELDS` tuple and old pure projection shape for v1. Add `PROJECTION_V2_FIELDS = (*PROJECTION_FIELDS, "paths", "path_sections", "vdb_context")` and a pure `blast_utility_projection_fields(selector: dict) -> tuple[str, ...]` version dispatcher. Never add keys to historical projection/publication bodies during replay.

The exact registered fact sources after this change are:

```text
execution.blast_utility_status
execution.blast_utility_sequences
execution.blast_utility_database_fields
execution.blast_utility_integrity
execution.blast_utility_preparation
execution.blast_utility_prepared_database
execution.blast_utility_checks
execution.blast_utility_failures
execution.blast_utility_missing
execution.blast_utility_artifacts
execution.blast_utility_saved_data
execution.blast_utility_paths
execution.blast_utility_path_sections
execution.blast_utility_vdb_context
```

Each registration is an array with exactly the existing `x-source` naming convention, constrained report schema and explicit meaning. Internally `projection.status` remains one object; result facts wrap it into the existing singleton array. The other fields remain arrays, and `record_refs` is internal custody metadata rather than a fact source. Current registrations accept exact frozen old fact branches plus the additions below. Historical whole report-schema documents remain byte-for-byte registered through the existing historical adapter; do not accept arbitrary caller-narrowed or relaxed schemas as historical.

### 3.1 Sequence fact v2

Register a closed union of the old sequence schema and this new branch, discriminated by new required `version`:

```text
version: const native_blast_utility_sequence_fact_v2
source_ref: existing execution_result reference
database_key: nonempty string
record_key: native_blast_utility_record reference
occurrence_id: native_blast_utility_occurrence reference
native_row_ordinal: uint
line_number: positive integer
selector_ordinals: unique uint[]                  # may be [] for all-mode
scope: exact common extraction-v2 scope {kind}
association: exact common extraction-v2 association
completeness: exact common row completeness
fields: closed object, optional properties exactly VDB_RECORD_FIELDS
sequences: closed object, optional properties original_sequence/normalized_sequence
field_qualifications: qualification[]
vdb_identity: optional closed object {
  member: common VDBMember | null,
  sample_links: common VDBUtilityContext.sample_links item[],
  qualifications: qualification[]
}
```

`qualification` is exactly `{pointer: string JSON pointer, reason: enum}` with no prose or artifact references. Reasons are `not_supplied`, `not_applicable`, `native_not_reported`, `native_row_invalid`, `sequence_symbol_invalid`, `sequence_length_conflict`, `supplied_binding_conflict`, `member_unresolved`. Arrays have unique objects, canonical order by pointer then reason. These are absence/validation meanings, not scores.

`fields` keys must equal `record_fields`; `sequences` keys must equal `sequence_fields`. `vdb_identity` exists iff explicitly selected. Values are copied from retained records, including nulls and raw/normalized strings. The projection never calls a parser or a new normalizer to fill them. `selector_ordinals` is the original matched-selector list intersected with the requested selector ordinals, retaining original selected order; all-mode has `[]`. Scope is copied from the common extraction result. `record_key` must equal `occurrence_id + "#/records/" + str(native_row_ordinal)`; line/ordinal positions must remain those of the common row.

Exact null qualification rules:

- selected null `native_oid` -> `/fields/native_oid`, `native_not_reported`;
- selected null `requested_range` or `effective_range` -> respective field pointer, `not_applicable`;
- selected null `native_accession` -> its field pointer, `native_not_reported`;
- selected null `native_reported_length` -> its field pointer, `native_row_invalid`, using the retained row parse failure;
- selected null `returned_symbol_count` -> its field pointer and the retained `sequence_length` check's reason (`native_row_invalid`, `sequence_symbol_invalid`, or `sequence_length_conflict`); do not recalculate a count or choose a replacement;
- when member is null, `/member` has `supplied_binding_conflict` when the authenticated context contains multiple matching member bindings and the retained row contains that failure; with no matching supplied member it has `not_supplied`. Do not confuse another association failure with a member conflict. A result with a conflicting claimed null/member relationship is rejected by the common validator;
- empty selected sample links have `/sample_links`=`member_unresolved` when member is null, or `not_supplied` when its sample_key is null. When sample_key is present, copy all context sample-link records with that **same dataset_key and sample_key**, preserving their supplied provenance and order; shared validation already requires consistent identities. Never join by run/accession spelling;
- selected non-null member nullable identity fields keep their nulls. Qualify missing identity version, spot ID, read index, full length, sequence hash, sample key and biosample identifier as `not_supplied`. A null read/reference identity is `not_applicable` only when its member kind excludes that type under the shared validator; otherwise `not_supplied`.

Pointers inside `vdb_identity.qualifications` are relative to that identity object; `field_qualifications` pointers are relative to the sequence fact. Only nulls/absences in selected fields are qualified. Empty native strings remain exact strings; they are not silently converted into identities or nulls. Failure/check facts still carry original row qualifications independently of this compact null explanation.

No taxon, paired-read group, replicate, condition, inferred sample, read index, spot identity or reference coordinate is added. `record_key`, `native_row_ordinal` and path ordinals are locators, not biological identities. `member_kind=unknown` stays unknown.

### 3.2 Paths and sections

New `execution.blast_utility_paths` items are exactly:

```text
source_ref: execution_result reference
database_key: nonempty string
occurrence_id: native_blast_utility_occurrence reference
path_ref: native_blast_utility_path_record reference
kind, section_ordinal, native_path_ordinal, native_path, line_number,
matched_dependency_ordinals: exact common inspection-v3 path-record properties
```

New `execution.blast_utility_path_sections` items are exactly:

```text
source_ref: execution_result reference
database_key: nonempty string
occurrence_id: native_blast_utility_occurrence reference
section_ref: native_blast_utility_path_section reference
section_ordinal: uint
kind, header_line_number, presence: exact common inspection-v3 path-section properties
```

`path_ref = occurrence_id + "#/path_records/" + str(native_path_ordinal)` and `section_ref = occurrence_id + "#/path_sections/" + str(section_ordinal)`. The section ordinal is the retained section-array position. Copy rows, ordering, literal native tokens, missing header line, `reported_empty`/`reported_values`/`not_reported` and matched dependency ordinals. Do not parse native paths again, follow them, absolutize them, invent alias edges or read files at reported paths. Path occurrences must be the saved inspection stdout occurrence.

Every matched dependency ordinal refers to an exact tuple in the authenticated context's `declared_dependencies`; verify kind/path/index relationships through the common validator and context, even if the parent did not request context facts. Do not automatically return the whole dependency/context document to explain an ordinal; parent selection of `vdb_context` is explicit. A bare reported path can validly have no matched dependency; that is not permission to acquire one.

### 3.3 Closed context

New `execution.blast_utility_vdb_context` items are exactly:

```text
source_ref: execution_result reference
database_key: nonempty string
context: exact SCHEMAS["VDBUtilityContext"]
qualifications: qualification[]
```

The result has zero items unless context was selected and an authenticated parsed common result is available; otherwise exactly one. `context` is a deep copy of the retained result's entire closed context. No raw JSON document, unselected metadata dictionary, Store source record or prose extension is accepted.

Context qualification pointers are relative to `context`. For nullable identity/snapshot metadata, missing dataset key, identity version, release, snapshot_id, manifest_sha256, read/reference detail, sample key or biosample identifier, emit `not_supplied`; the shared kind exclusion determines `not_applicable` for a null read/reference identity. Null selection_kind in an inspection and null dependency list locators for non-list dependency sources are `not_applicable`. Nullable dependency binding identity version/release is `not_supplied`. A dataset_type/member_kind `unknown` is qualified as `not_supplied` at that exact pointer. No other computed or inferred identity is inserted. Provenance pointers, declared dependency tuples and supplied member/sample links remain unchanged.

The context's nested provenance `source_ref` strings stay ordinary constrained strings, as in the common schema. They are **not** annotated `format=reference` or recursively collected as access grants. A metadata provenance source_ref may be a captured artifact ID; that proves origin, not permission to open that artifact. Primary DatabaseBinding.source_ref is the actual capture source ID under 664; it is not the caller's biological source label.

## 4. Reused fact schemas, missing requests and status

Keep status, integrity, preparation, prepared-database, check and failure shapes unchanged. Add common extraction-v2 and inspection-v3 names to the **new/current** saved-data schema union, preserving frozen old schema documents. Existing ArtifactOccurrence schema additions already provide `entry_batch` and native VDB formats. Add current fact branches without rewriting old bodies or changing their recorded content.

The nine VDB database field names are exactly `vdb_selected_inputs`, `vdb_resolved_paths`, `vdb_sequence_count`, `vdb_total_unclipped_bases`, `vdb_longest_sequence_bases`, `vdb_average_sequence_bases`, `vdb_csra_inputs`, `vdb_reference_sequence_count`, `vdb_reference_total_bases`. Copy each complete selected common NativeField with its unit, value basis, native lexeme, line/pointer locator and missing_reason. Preserve zero, null, reported integer average and distinct native/CSRA populations. Do not derive average, normalize counts or treat any population as a search denominator or function score.

The new missing-fact branch adds a required `version: native_blast_utility_missing_fact_v2`, retains source_ref and the old reason enum, and admits these exact request variants in addition to applicable old variants:

```text
{type: sequence_selector, ordinal:uint}
{type: native_row, ordinal:uint}
{type: native_enumeration}
{type: path_row, ordinal:uint}
{type: path_population, kind:vdb|vdb_alias|blast_db_alias}
{type: path_section, kind:vdb|vdb_alias|blast_db_alias}
{type: vdb_context}
```

Do not add artificial missing requests for unrequested values. A null NativeField is a delivered qualified fact, not an absent projection row. A selected null sequence measurement is delivered with the qualification above, not replaced by zero. Selected entries/native rows absent from an available parsed result use `selection_unavailable`; absent parsed result uses `result_unavailable`. An absent explicitly requested path ordinal uses `selection_unavailable`. No parsed path result uses `result_unavailable` for each selected ordinal or, when null selects the whole population, each selected kind. A retained `reported_empty` section is a genuine empty population and is delivered successfully, not missing. `not_reported` selected population/section uses `field_unavailable`. Closed context unavailable after parse/context failure uses `result_unavailable`.

For an available common extraction result and `native_row_ordinals.values=null`, zero valid rows is still a delivered enumeration whose actual completeness/native outcome/failures remain visible. An entirely absent result adds `native_enumeration/result_unavailable`; it does not claim a zero-sized population. Similarly, requesting an explicitly empty ordinal list produces no missing rows. Valid rows from failed/partial output are never discarded.

Delivery status uses the existing meaning: `complete` when all requested facts/artifacts are delivered with qualifications, even if native_state is failed; `partial` when something useful was delivered and another requested part is missing; otherwise existing failed/unavailable distinction. Preserve native_state, writer_closed, inventory_complete and result_completeness separately. No numerical scientific acceptance condition is added. Preserve 638 captured-bytes completeness and legacy no-discriminator behavior.

## 5. Exact callable ports

Existing functions keep their names and legacy behavior. Add optional keyword context only where the VDB relationship checks need it:

```python
validate_blast_utility_result_selector(selector: dict, *, operation: dict) -> dict
blast_utility_projection_fields(selector: dict) -> tuple[str, ...]
project_blast_utility_result(
    *, source_ref: str, operation: dict, native_outcome: dict,
    result: dict | None, prepared_database: dict | None, occurrences: list,
    selector: dict, failures: list, saved_data: list,
    context: dict | None = None,
) -> dict
validate_blast_utility_projection(
    projection: dict, *, source_ref: str, operation: dict,
    native_outcome: dict, selector: dict, occurrences: list,
    context: dict | None = None,
) -> dict
projection_identifiers(projection: dict, namespace=None) -> list[str]
blast_utility_fact_sources() -> dict
validate_blast_utility_fact_values(source: str, values: list) -> list
```

Here `context` means the full qualified VDB worker context listed in section 1, not merely its nested `vdb_context`. VDB projection with a non-null parsed result requires it. Legacy calls may omit it. Selector validation remains usable before capture and does not need the context. A failure-only VDB projection with no parsed result may use qualified selection/outcome/occurrences, but cannot emit unverified context/member facts.

The standalone pure projector must continue to invoke `validate_blast_utility_result` on the full common record. This may invoke the **same shared** symbol calculation to validate retained relationships. That is not an independent numerical implementation and does not replace the published values. Do not weaken common validation, accept unchecked records, add a second numerical implementation or derive a fresh count in projection to avoid validation work. Projection copies values after validation. The shared validator can legitimately reject a forged retained count, normalized sequence, association, dependency relation or completeness value.

Additional external relationship checks compare result.operation, original_outcome, primary database_binding, operation_input_occurrences and vdb_context to the qualified context exactly, and bind stdout/stderr to retained occurrences. All operation/database/metadata/list occurrence references must resolve in that exact original context. A record self-consistent under a different request is not acceptable. `validate_blast_utility_projection` checks field-selection equality, original row/section/path references, context/sample/dependency relations, failure/check locations, missing population and exact grants without running a parser. Store-backed publication then supplies frozen byte/receipt authentication; pure validation alone does not establish captured-byte provenance.

Preserve existing publication signatures:

```python
validate_utility_prepared(prepared)
validate_prepared_utility_result(store, prepared)
prepare_native_blast_utility_result(store, *, capture, directory, policy)
publish_selected_utility_result(store, *, source_ref, prepared, selector, directory, policy)
validate_utility_publication(store, *, source_ref, prepared, selector, publication)
```

For VDB, `validate_prepared_utility_result` must additionally authenticate the embedded 664 proof in the original parse worker receipt. It validates original plan/context identity, original manifest/plan hash, selected file descriptors and result output hash. Saved projection reads only retained result/prepared artifacts and frozen receipt/context data. It does not reacquire metadata, open reported native paths, reparse native output or rerun native. No additional unchecked validation path is proposed.

## 6. Frozen envelopes and saved-only behavior

Dispatch versions explicitly:

| Record | Legacy | New VDB selected path |
| --- | --- | --- |
| Selected publication | `native_blast_utility_publication_v1` | `native_blast_utility_publication_v2` |
| Frozen projection artifact | `native_blast_utility_projection_artifact_v1` | `native_blast_utility_projection_artifact_v2` |
| Acquired result body | `native_blast_utility_acquired_result_v1` | `native_blast_utility_acquired_result_v2` |
| Prepared / retained / worker-receipt outer envelope | existing v1 | same v1 key sets; versioned nested worker plan/manifest per 664 |

A publication-v2 has the same identity fields `version, source_ref, prepared_sha256, selector, projection_artifact_ref` plus exactly PROJECTION_V2_FIELDS. The frozen projection-artifact-v2 has the same keys as v1: `version, source_ref, prepared_sha256, selector, projection, worker_receipt_artifact_ref, selected_projection_artifact_ref`, with projection-v2 content. The acquired-v2 body has exactly the current acquired-v1 keys, replacing the version value and its flattened projection keys with PROJECTION_V2_FIELDS; no new capture, acquisition or credit field is invented.

Those acquired body identity/state keys are exactly `version, run_id, episode_id, scope, assignment, operation_key, tool_name, arguments, target, observation, capture, prepared, source_ref, reused_from, operational_failures, complete`, plus the applicable projection fields. `arguments` remains `{}` for the selected status/collect operation. Original target/assignment/scope, observation, captured-byte custody and reuse ancestry keep their existing validators. When dispatching current fact-source arrays, an old body contributes `[]` to the three new sources; never index missing new keys directly or write them back into the old body.

Original prepared, stable grading envelope, original parse receipt, original common result artifact, selected projection worker receipt, selected projection artifact, acquired body and immediate-child form are distinct records. `prepared_sha256` binds the unchanged original prepared body; selected projection's worker plan binds exact source_ref, selector, context and input result descriptors. `validate_utility_publication` verifies frozen selected bytes/hash and original selection/worker relationships; it does not rebuild a replacement projection to compare with history.

The existing `PAYLOAD_REFS` stays the three original outputs. Context authentication lives inside the original receipt's manifest, so it adds no new automatically granted artifact or saved_data kind. `saved_data=result` still returns the original common result JSON artifact **only if selected**. The core JSON is internal typed storage; selecting that artifact is explicit data access, not permission to put its whole JSON into model context.

An incomplete original worker intent remains an immutable attempted action. Same-key replay returns exactly its old result and cannot secretly rerun. Preserve 659: a separately selected new collect may retry parsing a retained capture when the old prepared result has no parsed result artifact; it uses a new action directory, reuses the original capture/observation, gets zero new acquisition credit and does not rewrite the original failure. An existing parsed result, including partial/failed native results with usable rows, is reused rather than reparsed. Current view may select the later repaired body under the existing rule; history is unchanged.

Ordinary validated practical completion sets future expected credit to exact zero while preserving final actual gain and previous observations. One selected new collect supplies one ordinary own-action observation; parse internals, projection, receipt validation and controller refresh add none. No new zero turn, model-composed completion or stopping gate is introduced.

## 7. References, grants and frozen typed returns

Retain `native_blast_utility_record` and `native_blast_utility_occurrence`; add exactly `native_blast_utility_path_record` and `native_blast_utility_path_section`. Do not introduce a source/member/sample namespace that implies a Store record exists. `projection_identifiers` enumerates logical references only from selected facts, and handles legacy projections with no new fields.

`record_refs` is exactly the deduplicated original source_ref plus artifact_ref from explicitly selected `artifacts` and `saved_data` rows. Neither nested source provenance, all input occurrences in context, matched dependencies, selected record/section locators, nor authentication receipt descriptors expand it. Preserve distinct typed resolution: top-level source_ref is execution_result/source; artifact_ref is artifact; logical row/path references are their specific namespaces.

The return reader continues to authenticate the actual immediate child's original commission/action, purpose, assignment, scope, report schema and frozen form. It validates current facts and exact registered historical schema documents; semantic source claims alone do not confer custody. A supplied form cannot substitute another source/database/operation, splice metadata from another attempt, add a nonselected path or field, invent a reason/value or grant an unselected artifact. Forwarded forms can contain only actually received matching facts. Frozen old forms and admission receipts remain unchanged.

Keep `_reference_pairs` deliberately shallow: top-level source_ref for each selected fact; artifact_ref only for selected artifact/saved-data facts; existing authenticated generic execution_result_refs under its original rules. Do not recursively collect every `source_ref`/`artifact_ref` in context/member/dependency structures. Runtime source expansion already has utility-specific handling through the preserved bundle version. The material consumer exception requiring the same existing access check is detailed in 665/002.

## 8. Required verification after implementation

These are future meaningful tests, not tests performed by this planning task. Root selects a bounded verification owner after coding; use the existing local accounting and exact original episodes. No fresh episode or new fixture is a substitute for historical replay.

1. Selector applicability: old v1 byte-identical branch; v2 entry versus all mode, duplicate selected literal entries, wrong original ordinal, native-row gaps, all-references context, null versus empty selection, record-field exactness and required native-length basis. Reject unsupported classic field names and artifact roles before native work.
2. Shared values: project lowercase/invalid/U symbols and length-conflict examples from common records; assert original and normalized strings/count/nulls/qualifications are exact retained values. Mutate a retained count/string/association and require standalone common validation to reject it. Do not assert that validation cannot invoke the shared calculator.
3. Identity: exact ID/accession association; duplicate request occurrences; no member binding; unique supplied binding; conflicting bindings; same sample_key in different dataset; supplied sample/biosample provenance; missing identity fields remain null with closed reasons. No inferred spot/read/group/sample/taxon.
4. Partial native result: good rows around malformed rows, real retained native nonzero, open writer, missing stdout/stderr, parse failure, zero-exit missing selector, zero versus missing NativeField, reported integer average retained. Qualified useful facts can complete selected delivery while native_state remains failed.
5. Paths: all three section kinds, reported-empty versus not-reported, repeated/bare path tokens, original section/row ordinals, exact dependency ordinal matches and undeclared path. Changing path/dependency tuple or occurrence fails; reported paths trigger no file read/acquisition.
6. Context authentication: selected metadata/list claim mismatch, cross-capture source/artifact/pointer splice, altered original worker proof, altered plan context and result output hash. Original parse rejects unauthenticated claims before producing a result. Saved projection succeeds with original native/metadata paths unavailable when retained authenticated inputs exist, and never reruns native or metadata extraction.
7. Selection-only return: one sequence text, one selected length+basis, one sample identity, selected path section, explicitly selected context, selected artifacts/saved result, empty selections. No unsolicited fields/checks/context/byte grants appear. Necessary failures remain structured.
8. Frozen publication: v1/v2 exact key sets; old v1 bodies are not enriched during replay; selected projection artifact/worker receipt binding; current union recognizes old exact facts; forged/sibling/disconnected immediate-child forms fail. Test each of four logical reference namespaces and cross-database/source mismatch.
9. Byte grants: source-only return cannot read its unselected bundle via material.from_source/material.parse; explicitly selected bundle/output/result artifact remains usable; old independently supplied material still works. Nested metadata provenance with an artifact ID grants no bytes. Existing received source expansion must stay narrow.
10. Replay/repair: same key replays byte-identically and cannot rerun original parse; new selected collect repairs missing parsed result from same original capture once, preserves prior failure and original acquisition identity, grants zero new acquisition credit; a usable partial parsed result is never reparsed. Validate final actual gain, earlier observations and exact future-zero without an extra turn.
11. Historical 652: replay all six actual prior child deliveries from check096 (five result returns and one scientific forwarded return), all original report-schema documents, original source/artifact permissions and numerical facts. check101 masking schemas are separate preservation evidence, not extra utility deliveries.
12. Original preparation 654: use its exact original Store/journal/catalog/assignment and selected pending request, not a re-created case; preserve repaired original result receipts and all prior closed history. The authoritative request SHA256 is `8ecce26702ea1ac4d52975087c436d10236cfcadc878eabb315895260f348310`. Its final `VERIFICATION_013.json`, read during this plan, records three passing Workflow tests and ten unchanged result-action replays; this is existing 654 evidence to preserve, not tests run by 665 or VDB verification.
13. Authentic VDB integration: consume actual 661 selected two-read extraction through the real selected local child/capture/result/publication/accepted parent return. Existing actual stdout has two 250-base rows, 594 bytes, SHA256 `3be1e1b841530c2818893eb9a396ca8dcd5257203b4778bdda93719fdc47110c`; stderr is empty. Use the retained actual data and 664-bound original input context, without claiming its source IDs or samples from identifier spelling.

## 9. Current authentic gaps and completion limits

661 establishes actual selected extraction of two 250-base reads and saved-output parsing evidence. Its first check failed after native success in trace parsing; saved check121b repaired verification without a native rerun. It did not establish production offline closure (22 reported unselected interface/IPC events remained), full result-child integration or every VDB mode. Identity-preserving read-only DB/config binding is a planned production correction owned by 664; strace is verification evidence, not a new runtime authority.

Authentic info/paths/paths_all, all-native/all-reference enumeration, filtered reads, CSRA references, WGS, multi-source selection, actual aliases, nonempty stderr/partial native failures, and independently supplied sample/clipping/reference relationships remain unverified unless later resource evidence establishes them. Synthetic core/parser edge tests do not close those native format/resource gaps. The supported planned formats remain fixed four-column table, native info and native paths text; no generic custom format, FASTA or formatter is added. No local/HPC/API VDB utility integration is claimed from source availability or this contract; local two-read native evidence is narrower than a complete installed binding, and no remote resource branch is established here.

The complete task remains the original user goal. This document establishes an implementation boundary for one unfinished supporting operation and preserves completed work. It supplies no new numerical policy, scientific score, workflow, hidden renderer, root tool, tool_ref, approval mechanism or runtime prompt. Any concrete TASK/STEERING template and its running user feedback is a separate requirement under TASK_AND_STEERING; the internal fact schemas here are not model-facing context text.

## 10. Frozen 664-to-665 authentication handshake

Read against `verification/tool_graders_blast_vdb_native_ports_2026-10-28_664/IMPLEMENTATION_PORT_001.md` section 4. That source is the owning definition of these new request-byte authentication records, not a dependency on an unspecified future context layer.

The original VDB plan version is `native_blast_utility_result_worker_plan_v2`; parse_original retains exactly `{version, task, directory, context, files, capture, bundle_file}`. Its v2 manifest retains existing `version, task, plan_sha256, completed, outputs, failures` and adds exactly `context_authentication`. VDB parse outputs are empty or `{result: descriptor}`; project_saved outputs are `{projection: descriptor}` on completion. Descriptor is exactly `{filename, sha256, size_bytes}`.

The closed successful proof is:

```text
version: native_blast_vdb_context_authentication_v1
passed: true
bundle_artifact_ref: actual original bundle artifact ID
request_sha256: native_blast_digest(capture.plan.requested_job)
context_sha256: native_blast_digest(full qualified context)
documents: [{document_key, selection, occurrence_id, artifact_ref, sha256, size_bytes}]
provenance: [{context_pointer, origin, source_ref,
              source_namespace:source|artifact, pointer}]
lists: [{occurrence_id, grammar, sha256, size_bytes,
         entries:[{ordinal,line_number,token_ordinal,byte_start,byte_end,value}]}]
dependencies: [{ordinal,declaration,list_occurrence_id}]
```

Document selection, Origin/SampleOrigin and dependency declaration types are exactly 664 section 3, not arbitrary mappings. Their fields retain original request-selected addresses; no provenance entry is a grant. Document/provenance/list/dependency ordering and occurrence identities are exactly the deterministic rules in 664 section 4. All original bundle/capture/input hashes are checked by the bounded original worker before fixed field extraction. A failure leaves context_authentication null, completed false and no parsed result; explicitly selected captured artifacts/failures can still be delivered.

The exact shared receipt validator is:

```python
validate_vdb_context_authentication(value: dict, *, capture: dict, context: dict) -> dict
```

It lives in `native_blast_vdb_utility_context.py`, is pure, validates claimed original identities/list positions/mappings, and never reads metadata. `validate_prepared_utility_result` first authenticates the existing immutable original worker receipt/plan/manifest/output artifact identities, then calls this validator for non-null VDB result. This combination proves that the recorded original bounded authentication ran over the selected bytes and that this retained context/result is the same one; the pure proof validator by itself is not a new admission path.

`publish_selected_utility_result` builds VDB project_saved plan-v2 using the existing keys plus exactly `context_authentication`, copied from that original authenticated parse receipt. Existing files keys remain `result, prepared_database, prepared_manifest` (latter two null). With no result, proof is null; otherwise passed proof is required. `_projection_context` reconstructs the expected qualified context from retained capture without document reads. The worker validates/copies this proof, runs the pure projector with that full context, and copies the same proof into its project_saved manifest. `validate_utility_publication` authenticates the selected worker receipt and checks proof equality with the original authenticated proof, in addition to existing selector/source/prepared/result/projection byte relationships.

This handshake agrees on all callable names, full-context keys and version boundaries. There is no new context artifact, no prepared-v2 record and no projection bypass of common result validation.
