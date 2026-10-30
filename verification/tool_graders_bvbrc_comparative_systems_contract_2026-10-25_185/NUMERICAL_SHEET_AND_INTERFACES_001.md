# Proposed numerical sheet and deterministic interfaces

Review proposal; no production implementation. The independent functions below consume supplied values/bytes only. The native acquisition population defects in `REVIEW_CONTRACT_001.md` are part of each field's meaning, not a cosmetic disclaimer around a generic score.

## Typed records and identity

`ComparativeSystemsSheetV1` contains `version`, `analysis_id`, `original_request`, `source_documents`, `producer_evidence`, `populations`, `family_rows`, `pathway_rows`, `pathway_ec_rows`, `subsystem_rows`, `association_rows`, `overview_rows`, `variant_rows`, `supplied_record_sets`, `reference_memberships`, `duplicate_groups`, `join_results`, `requirements`, `diagnostics`. It stores actual numerical cells alongside all relevant intermediate associations. Full native artifacts remain external retained bytes bound by source/byte identity; a sheet records precise inner-document pointers and TSV row/column locations. No raw source is discarded merely because its selected scientific projection is unavailable.

Each source document has caller-selected `document_id`, exact role, parser profile, original `source_ref`/`raw_artifact_ref`, byte count/digest, transfer body/object completeness, original task binding, nullable producing version, and a `basis` enum (`service_artifact`, `source_executed_synthetic`, `synthetic_fixture`, `supplied_data_api`). Neither digest consistency nor a manifest basename confers host custody. That comes from the existing authenticated bundle.

Identities are scoped tuples, not independently sorted display names:

* family row: `(document_id, family_kind=plfam|pgfam, family_id, native_row_ordinal)`; logical family grouping separately preserves repeats/conflicts;
* pathway summary: `(document_id, pathway_id, native_row_ordinal)`; EC row additionally carries ec_number;
* subsystem: `(document_id, superclass_native, superclass_aggregation, class, subclass, subsystem_name, subsystem_id, native_row_ordinal)`;
* association occurrence: document/table/row plus all native genome, feature, PATRIC, pathway/EC, subsystem/role and family identifiers actually present;
* a supplied record: collection, native unique key, snapshot/population ID, original page and row occurrence. Same sequence across several features is several features. Same native unique key with conflicting payload is a conflict, not first-wins.

`PopulationV1` has `population_id`, `kind` (`requested_direct_genomes`, `executed_genomes`, `native_view_represented_genomes`, `native_retained_records`, `supplied_data_records`, `selected_component_membership`), `members` where evidenced, `source_locations`, `raw_occurrence_count`, `distinct_valid_member_count`, `completeness` (`complete_for_declared_population`, `partial`, `unknown`, `incompatible`), missing/unresolved members and qualifications. These count cells are operational/population descriptors, not function-confidence scores. A requested direct-genome count is computable if groups are empty; a group path or group basename does not supply the expanded original population.

`NumericCellV1` has exactly `state`, `value`, `unit`, `origin`, `population_id`, `method_id`, `input_refs`, `uncertainty`, `qualification_codes`. `state` is `available`, `missing`, `not_measured`, `failed`, `truncated`, `incompatible`, or `invalid`; `value` is finite number only for available, otherwise null. **Measured zero is available value 0**, never null. `uncertainty` is null for every native field here: no confidence intervals are emitted. A length SD is a separate dispersion measurement, not uncertainty attached to the mean. Raw original numeric lexemes and native field names remain in `NativeNumberV1` even when the numerical cell is invalid/unrepresentable. Numeric JSON booleans are invalid numbers.

`RatioComponentV1` adds inspectable numerator cell, denominator cell, scale (1 or 100), output cell, and the exact genome/component population IDs. Denominator zero makes a new calculated ratio missing with `empty_denominator`; it does not erase a producer-reported zero sentinel. No smoothing, clipping, priors, category weights, annotation probability or universal combined score is proposed. Proposed native descriptive ratios are evaluated only for the named retained population; they never imply all requested genomes were measured.

## Native numerical cells

All cardinalities are nonnegative integers, with no coordinate convention. Native numbers are `program_reported_derived`; counts reproduced from explicit retained associations are separately `derived_retained_records`. Family lengths have unit amino_acid. Native tokens/labels/unknown release metadata are retained separately and are never numeric category weights.

| Sheet field | Exact native input or producer formula | Unit / population / valid range and missing behavior |
| --- | --- | --- |
| `family_rows[].reported_feature_occurrences` | TSV `feature_count`; accepted AA-length TSV occurrences with the family | occurrences; no deduplication; integer ≥0; missing/invalid token remains missing/invalid |
| `family_rows[].reported_genome_count` | TSV `genome_count`; number of distinct genome keys assigned the family | genomes represented by that family; ≥0; compare positive list if supplied |
| `family_rows[].reported_length_min`, `max`, `mean`, `population_sd` | `aa_length_min`, `aa_length_max`, `aa_length_mean`, `aa_length_std`; min/max, ΣL/n, sqrt(Σ(L−mean)^2/n) over the accepted family occurrences | amino_acid; min/max/mean ≥0 and ordered, SD ≥0; native zero-length data are not replaced; nonfinite/contradiction invalid; individual lengths unknown from JSON |
| `family_rows[].genome_counts[].reported_occurrences` | exactly two hex characters at the same output-genome ordinal, only when entire hex token has exactly 2N characters and consistency checks pass | occurrences for exact genome/family; integer 0…255 in this encoding; overflow/length mismatch incompatible, never guessed |
| `family_rows[].positive_genome_count_from_list` | distinct explicit members of `<kind>_genomes[family_id]` | genomes; derived list cardinality; repeated members retained and flagged; conflicting list/count or out-of-population ID prevents equivalent-view claim |
| `pathway_rows[].reported_genome_count` | `genome_count` | distinct genomes for pathway among processed rows |
| `pathway_rows[].reported_ec_token_count` | `ec_count` | distinct native EC tokens; blank placeholders may be counted upstream, so not silently called valid enzymes |
| `pathway_rows[].reported_feature_token_count` | `gene_count` | distinct native feature_id tokens, with same placeholder qualification |
| `pathway_rows[].reported_genome_ec_count` | `genome_ec` | distinct producer genome/EC concatenation keys |
| `pathway_rows[].reported_ec_conservation_percent` | `ec_conservation = 100 A/(E Np)`; Np is all represented pathway genomes | percent of observed EC×represented-genome opportunities; 0…100 only for coherent nonempty valid identities; report outside expected range retained as invalid/qualified, never clamped |
| `pathway_rows[].reported_gene_conservation` | `gene_conservation = F/(E Np)` | features per observed EC×represented-genome opportunity; ≥0, **not bounded by 1** |
| `pathway_ec_rows[].reported_genome_count`, `reported_ec_token_count`, `reported_feature_token_count`, `reported_genome_ec_count` | `genome_count`, `ec_count`, `gene_count`, `genome_ec` from native EC table | same units, scoped to pathway+EC; ec_count normally 1; EC rows are a dependent view |
| `subsystem_rows[].reported_role_token_count`, `reported_feature_token_count`, `reported_genome_count` | `role_counts`, `gene_counts`, `genome_count` | distinct tokens/genomes under the hierarchical aggregation key; placeholders and ID/name collisions qualified |
| `subsystem_rows[].reported_gene_conservation` | `gene_conservation = F/(R Ns)` | features per observed role×represented-genome opportunity; ≥0, no upper bound 1 |
| `subsystem_rows[].reported_role_conservation_percent` | `role_conservation = 100 J/(R Ns)`; J counts role×genome pairs in the native feature-inner-joined genes table | percent; retain join denominator identity and missing-feature joins; collisions can invalidate expected 0…100 range |
| `subsystem_rows[].reported_record_genome_fraction` | native `prop_active`; distinct genomes with **any** row for subsystem_id divided by Ns | fraction of represented genomes with a subsystem record; normally 0…1; never a strict active fraction |
| `overview_rows[].reported_subsystem_name_count`, `reported_feature_count` | native overview leaf unique sets; upper levels add children | named subgroup counts; preserve level/path; sums are not globally distinct feature counts |
| `variant_rows[].reported_active_occurrences`, `reported_likely_occurrences`, `reported_inactive_placeholder`, `reported_missing_genome_count` | pinned source row's two occurrence counters, fixed zero and extra imputed-no-record count | distinct semantic columns despite malformed header; raw source-layout only, unsafe identity mapping flagged; no category-to-confidence transform |

The overview and malformed variant numeric fields are preservable reported quantities, not required inputs to the main comparative calculations. Each can remain unavailable while family/pathway/subsystem quantities are returned. A missing optional artifact never makes a valid unrelated requested field disappear.

## Separate calculated components

These functions return new immutable `ComparativeSystemsComponentsV1` with parameters/formula version and per-component dependencies. Recalculation does not change the native sheet or old publication. Every expression below is ordinary deterministic code, not a runtime formula interpreter.

| Component | Exact proposed formula and input population | Conditions and interpretation |
| --- | --- | --- |
| `family_returned_genome_occupancy` | positive distinct genome membership / selected native family-view genome count | Exact ratio over returned native population. Missing group expansion does not block it. It is not full-genome absence/completeness; a missing represented list blocks it. If a separately selected declared population is used, return a separately named `family_record_genome_occupancy` only with complete qualified records for that population. |
| `family_occurrences_per_positive_genome` | native feature_occurrences / native positive-genome count | Mean accepted record occurrences per positive genome; duplicate sensitive. Empty denominator missing. |
| `family_length_cv` | native population SD / native mean | Dimensionless descriptive dispersion; mean zero missing; no confidence interpretation; no independent evidence credit. |
| `pathway_retained_ec_occupancy_percent` | 100 × valid distinct (genome_id,ec_number) pairs for p / (valid distinct observed EC IDs for p × selected retained-view genome count) | Recompute from **declared authoritative association table**, with token/duplicate/join diagnostics. Do not mix summary numerator and a different retained population. Only a report consistency check can use native aggregate fields; it is explicitly named `reported_formula_check`. |
| `pathway_retained_feature_density` | valid distinct (genome_id,feature_id) for p / (valid observed EC IDs for p × selected retained-view genome count) | Features per EC×genome opportunity; may exceed 1; explicit feature-ID normalization, differs from native token count if malformed/duplicate IDs. Missing/malformed IDs make whole-population measurement partial rather than a silent clean denominator. |
| `subsystem_retained_role_occupancy_percent` | 100 × valid distinct (genome_id,role_id) for subsystem_id / (valid distinct observed roles for that ID × selected retained-view genome count) | Uses one explicit association population, not the source's mixed hierarchy/join formula. Distinct name/ID collisions are flagged. Native report remains separate. |
| `subsystem_retained_feature_density` | valid distinct (genome_id,feature_id) / (valid observed roles × selected retained-view genome count) | Same units/partial rules as pathway density. |
| `subsystem_explicit_category_genome_count` | distinct genomes whose set of supplied/retained active tokens is exactly the selected category | Category is one of the literal native `active`, `likely`, `inactive`. Mixed categories are counted separately as conflicting, never last-wins. Absence-of-record is separate and is never `inactive`. No activity probability. |
| `observed_family_set_intersection_count`, `observed_family_set_union_count`, `observed_family_set_jaccard` | for a declared pair of genomes and a selected PLFam **or** PGFam universe, positive family sets A,B; intersection count, union count, |A∩B|/|A∪B| | Observed-positive-set comparison only; union zero missing, not 1. Retained native/supplied populations cannot be mixed. Whole selected-genome gene-content comparison additionally needs complete matching records. Do not pool PLFam and PGFam or claim family independence. |
| `reference_component_representation` | |observed valid selected EC/role IDs ∩ explicitly supplied reference IDs| / |explicitly supplied reference IDs| | Optional explicitly requested descriptive representation of that reference snapshot. Name full denominator and membership source. Missing reference set → not_measured/missing. Empty set → missing. Does not establish pathway completion, essentiality or biochemical feasibility. |

Population numerator/denominator cardinalities are retained even when their ratio is unavailable. The known native source-loss population and later complete Data API population never become equivalent just because values happen to match. Duplicate exact source records count once for **unique-entity** metrics and retain all occurrence rows; native occurrence metrics continue to count as the producer did. Conflicting duplicate identities invalidate affected joins and full-population metrics while preserving unrelated components.

Each positive/absence cell uses an explicit `presence_state`: `recorded_positive`, `zero_in_qualified_record_population`, `no_record_completeness_unknown`, `not_measured`, `failed`, `truncated`, `incompatible`, `conflicting`. `zero_in_qualified_record_population` means absence of an assignment in the named complete data population, never physical gene/function absence. Native hex `00` is a reported zero occurrence count; without full service-query provenance it does not establish the qualified-population absence state.

Coordinates retained in `genes` include original `start`, `end`, `strand`, accession and sequence_id when present. Their declared `genome_feature` convention is one-based inclusive only when the schema/source binding establishes that origin; unknown standalone-table coordinate origin remains unknown. No interval union, residue comparison or coordinate transformation is introduced here.

## Pure function signatures and exact handoffs

```python
# N: read original bytes; no scientific formulas
parse_comparative_systems_document(
    content: bytes, *, document: SourceDocumentV1,
    format_profile: str,
) -> NativeDocumentResultV1

# D: qualify supplied records/populations; never reads Store or network
extract_comparative_systems_data_inputs(
    qualified_results: tuple[dict, ...], *, selection: DataPopulationSelectionV1,
) -> SuppliedRecordSetsV1

# N: merge explicit originals and preserve numerical cells/associations
build_comparative_systems_sheet(
    documents: tuple[NativeDocumentResultV1, ...], *,
    original_request: OriginalRequestV1,
    document_selection: DocumentSelectionV1,
    supplied_record_sets: SuppliedRecordSetsV1 | None,
    reference_memberships: tuple[ReferenceMembershipV1, ...],
) -> ComparativeSystemsSheetV1

# C: ordinary functions with explicit fixed parameter schema
calculate_comparative_systems_components(
    sheet: ComparativeSystemsSheetV1, *, parameters: CalculationParametersV1,
) -> ComparativeSystemsComponentsV1

# P: bounded copies from saved values, no recalculation
project_comparative_systems_facts(
    sheet: ComparativeSystemsSheetV1 | None,
    components: ComparativeSystemsComponentsV1 | None, *,
    requested_form: dict,
) -> RequestedFactsV1
validate_saved_comparative_systems_projection(
    sheet, components, *, facts, status, missing_requirements,
    diagnostics, requested_form, parameters, original_task, bundle,
) -> None

# P: compatible with existing AppServicePublications._grade
consume_bundle(
    bundle: dict, *, artifact_bytes: dict[str, bytes],
    supplied_values: list[dict], requested_form: dict, parameters: ProviderParametersV1,
) -> dict  # adapter_id, adapter_version, status, sheet, components, facts,
           # missing_requirements, diagnostics
```

`NativeDocumentResultV1`: `status=ok|partial|invalid|failed`, original document identity, original bytes binding, native JSON keys/TSV strings/tokens, correctly parsed tables, invalid-row locations, reported numeric cells, diagnostics. No network retry or silent truncated-JSON prefix salvage. Malformed outer JSON retains bytes and an invalid result; independently acquired sibling documents remain usable. Malformed rows of a structurally intact TSV retain row occurrences and permit valid other rows.

`DocumentSelectionV1` explicitly names one authoritative document/table for each requested calculation and separately names representations to compare. The provider never chooses the first available JSON/TSV or sums them. A source role can resolve through a parent `requirement_id` **before acquisition** or a possessed exact source/artifact pair afterward. Zero/multiple candidates are missing/ambiguous. Source/view redundancy is recorded as dependent representation, never new evidence.

`CalculationParametersV1` requires `version`, `selected_components`, explicit `view_selections`, `population_selections`, `family_kind` where applicable, `entity_selection`, `comparison_pairs`, `reference_membership_selections`, and `duplicate_policy`. `selected_components` is a finite list of the named components above; no arbitrary formula text. Entity selections contain exact native IDs, not unrestricted claims. Population selection names one saved population for each component. `duplicate_policy` is a fixed enum `preserve_native_occurrences_and_deduplicate_identical_record_ids`; it does not permit silently dropping conflicts. Parameters may select a different supplied reference membership or a different explicitly saved genome subset; they may not turn missing history into complete history. Empty-denominator behavior is fixed, not a tuning parameter.

`ProviderParametersV1` requires `analysis_id`, `native_documents`, `document_selection`, `supplied_data_selection`, `reference_memberships`, `calculation_parameters`. Each native selection includes role/profile and either requirement_id or exact possessed source/artifact references. Original task application must be `ComparativeSystems`; original request parameters come from the authenticated task, not a second caller restatement. Supplied metadata must name an authenticated selected evidence binding; provider code does not discover it by searching storage.

Diagnostics and requirements are bounded records: `code` enum, `phase=decode|association|population|calculation|projection`, `document_id|null`, `row_ordinal|null`, `field` enum|null, affected source references and required input role. Initial code set: `outer_json_invalid`, `duplicate_json_key`, `format_incompatible`, `tsv_header_mismatch`, `tsv_row_width_mismatch`, `numeric_token_invalid`, `nonfinite_number`, `artifact_truncated`, `original_task_mismatch`, `producer_version_unverified`, `native_first_object_discard`, `native_query_completeness_unknown`, `group_membership_unknown`, `native_identifier_placeholder`, `identity_conflict`, `duplicate_identical_representation`, `duplicate_record_conflict`, `inner_join_missing`, `inner_join_many_to_many`, `variant_matrix_extra_column`, `genome_name_collision`, `conflicting_native_categories`, `hex_count_width_ambiguous`, `native_formula_mismatch`, `reference_release_unknown`, `reference_membership_missing`, `population_incomplete`, `population_incompatible`, `empty_denominator`, `unrequested_dependency_missing`. Raw messages/native data stay in artifacts, not free-form parent failure prose.

The formula consistency checker compares explicit native numerators/denominators to retained reported values under recorded numerical tolerance parameters `absolute_tolerance` and `relative_tolerance`, both finite nonnegative numbers supplied explicitly. Those tolerances qualify floating-point agreement only; they do not alter measurements, round scores or fabricate uncertainty.


## Additive shared-contract closure

The nested handoff shapes and focused corrections are now specified in `HANDOFF_SCHEMAS_001.json`, `SCHEMA_DECISIONS_001.md`, and `HANDOFF_CLOSURE_002.md`. The latter supersedes incomplete parse/build/provider signatures, supplies explicit analysis/producer/population inputs, closes calculated/native fact selectors, and defines the acyclic shared-schema ownership graph. `FILLED_EXAMPLES_001.json` and `CONTRACT_VALIDATION_001.json` identify the exact conforming review examples and checks. This addition preserves the original proposal; it does not approve or implement it.
