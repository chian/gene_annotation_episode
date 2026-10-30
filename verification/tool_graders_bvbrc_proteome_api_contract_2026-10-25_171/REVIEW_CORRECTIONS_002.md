# Additive corrections and shared failure contract

This file supersedes the identified interface details in proposal001; it does
not alter the authoritative goal or claim implementation. Root reviewed the
provider ABI/raw-path separation and will own projection separately. Parsed
assertions still require actual constructor/source provenance.

## Reviewed corrections

1. The real `read_latest_adapter_result` accepts adapter IDs, not ID/version
   tuples. Call it with `adapter_ids=("bvbrc_proteome",)`, then separately
   require the saved adapter version to be `"1"`. Its latest matching owned
   result is authoritative; no fallback to older success after newer partial.
2. The pure projector's `status=ok` means its requested facts are available.
   It does **not** assert required-artifact completeness. Existing
   `AppServicePublications._requested_status` owns the conjunction with bundle
   required-artifact status. `validate_saved_projection` receives a bundle hash,
   not the entire bundle, and must not invent that missing knowledge.
3. `ProviderSheet.supplied_values` is the exact deep-copied host list of
   `{evidence,value}` rows, including unused raw SuppliedData and rejected
   parsed assertions. Keep the complete values, not just pointers or error
   codes. All construction-result envelopes are retained unchanged as well.
4. Missing selected targets use `availability="unavailable"`; their
   `population_ref`/`parameter_ref` are null if no actual saved target exists.
   Use a missing numeric CellFact with `state="missing_input"`, `value=null`,
   empty copied-native `reason_codes`/`source_field_refs`, and a separate typed
   provider requirement. Do not insert a new provider code into B4's frozen
   PReason enum. Missing association category_presence/selection are null;
   an existing unrecognized native category is `unrecognized` with the actual
   source field retained. It is not a missing row.
5. Exact existing B1 names are FeatureSnapshotResult, GenomeSnapshotResult,
   FeatureSequenceSnapshotResult, PopulationDescriptor and CoordinateConvention.
   Existing AssociationComponents condition enum is exactly
   `identity | subject_endpoint_difference | category`.

## One finite binding/selection failure vocabulary

The provider contract owner declares these constants; projection imports or
duplicates the exact frozen values until its import handoff is complete.
Neither side derives a code from exception text. Prefix is `proteome_`.

| Suffix (finite enum) | AcquisitionRequirement.kind | Role | Phase |
|---|---|---|---|
| bundle_invalid, application_mismatch, original_task_conflict | original_task | null | association |
| parameters_invalid, requested_form_invalid, source_contract_incompatible | parser_binding | proteome_native_projection | publication |
| document_missing, primary_document_missing, artifact_bytes_missing | output_bytes | proteome_native_projection | association |
| document_ambiguous, primary_document_invalid, artifact_format_incompatible, nonzero_range_unsupported | parser_binding | proteome_native_projection | association |
| artifact_digest_mismatch, artifact_binding_conflict | byte_version_evidence | proteome_native_projection | association |
| supplied_data_missing, supplied_data_ambiguous, supplied_data_invalid | scientific_metadata | proteome_supplied_data | association |
| input_bytes_missing, input_binding_missing, input_binding_ambiguous | input_bytes | proteome_supplied_input | association |
| parameter_source_unbound, parameter_source_conflict | original_task | proteome_original_input_index | association |
| completeness_evidence_unverified, parsed_construction_evidence_unverified | byte_version_evidence | proteome_supplied_input | association |
| supplied_source_conflict, source_field_unbound | scientific_metadata | proteome_supplied_input | association |
| deployment_evidence_unverified | byte_version_evidence | proteome_native_projection | association |
| parsed_result_invalid, parsed_result_mismatch, supplied_reader_incompatible | parser_binding | proteome_supplied_input | native_decode |
| projection_parameters_invalid, projection_requested_form_invalid | parser_binding | proteome_requested_projection | publication |
| saved_sheet_invalid, saved_components_invalid, saved_identity_conflict, saved_projection_conflict | parser_binding | proteome_requested_projection | return |
| requested_target_missing, requested_target_ambiguous, requested_value_unavailable, requested_population_unavailable, requested_reference_unresolved | scientific_metadata | proteome_requested_projection | publication |

Global invalid parameters/form/bundle/application and saved corruption are
validation errors. Provider construction may package its own validation failure
as invalid; the return binder must reject saved corruption, never republish or
recalculate it. An unavailable target/operand is a scoped requirement; independent
available facts survive. Diagnostics use severity `error` for invalid/conflict
and `qualification` for absent/unverified/partial data. Source-byte digest
conflict is an error even when other data remain useful.

Concrete host-facing shapes are unchanged existing contracts:

```text
AcquisitionRequirement = {
 requirement_id: identifier,
 kind: existing finite kind from the table,
 role: stated role | null,
 source_refs: unique references in first-occurrence order,
 reason_code: one full "proteome_" code above, or actual pure requirement code
}
Diagnostic = {
 code: same finite full code or actual pure diagnostic code,
 phase: existing phase from table,
 path: exact supplied-value/selection/saved-object JSON pointer,
 severity: error | qualification,
 evidence_refs: unique references in first-occurrence order
}
```

For a projector-created requirement, derive its stable ID as
`"proteome_requirement_" + SHA256(canonical(payload))`, where payload is exactly:

```text
{version:"bvbrc_proteome_requirement_v1", analysis_id,
 reason_code, role, field: requested field identifier | null,
 selection: exact finite selector | null,
 source_refs: ordered unique actual references,
 pure_requirement: actual unchanged native/PRequirement | null}
```

Canonical means sorted keys, compact separators, ensure_ascii=False,
allow_nan=False. A repeated ID with different content is invalid. Passing
missing_requirements/diagnostics to the projector uses tuples as specified;
deduplicate identical entries without dropping distinct scopes.

Pure A/B1/B2/B3/B4 requirements remain unchanged in their result envelopes.
For host AcquisitionRequirement conversion, use their `required_input` rather
than interpreting job labels: complete native artifact bytes → output_bytes;
complete/exact input FASTA, complete_bytes → input_bytes; producer manifest,
execution witness → task_manifest; producer/version/occurrence witness →
byte_version_evidence; feature/genome/sequence metadata, membership, identifier
mapping or coordinate convention → scientific_metadata; requested calculation
field/format/structural contract → parser_binding. Record the explicit finite
mapping keyed by the actual enums in the new contracts module; fail a newly
unknown enum rather than silently selecting a catch-all. Keep the entire
original requirement in the ID payload and saved result, including its scope
and SourceFields. This translation adds no scientific facts.

For RequirementsFact, `code` is the actual pure code or one binding code above;
`required_input` is the actual pure enum, or the AcquisitionRequirement.kind
for a provider-created requirement. The returned finite union must be declared
explicitly. Provider requirements have an empty pure Scope unless the selected
target yields actual track/association/row fields. Requirement refs resolve to
the saved host-facing requirement plus its retained pure source, not to newly
composed prose.

Root's new projection module/tests and the provider owner's four new modules
have disjoint ownership. The shared execution/registry/library integration can
be staged separately; it must not mutate the original live verification.
