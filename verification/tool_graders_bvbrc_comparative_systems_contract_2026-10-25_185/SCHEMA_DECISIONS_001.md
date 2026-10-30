# Shared-shape closure for root review, 2026-10-25

This additive contract closes the unspecified nested structures in the four original proposal documents. The original documents remain intact. `HANDOFF_SCHEMAS_001.json` is the normative proposed field/type/enum definition for N/C/D/P/I handoffs. This file supplies the relationship rules JSON Schema cannot express. These are proposed implementation contracts, not production code or an approval of the proposal.

Every object is closed except explicitly retained native JSON metadata and the provider's parent-named fact dictionary. Native arbitrary JSON exists only for lossless internal preservation. It is not a parent communication field. Each provider dictionary value has a closed typed shape. Plain JSON numbers must be finite; Python integers must have exact type `int`, not `bool` or integral `float`. Required nullable fields must be present. Unknown values use null plus the corresponding explicit state.

## Exact versions and ownership of the frozen handoff

The schema uses Draft 2020-12 and contains all transitive definitions. `Data__*` definitions are exact namespaced copies of existing `bvbrc_data_schema.schema('QualifiedResult')`, not a new Data API contract. The original retained schema is `DATA_QUALIFIED_RESULT_SCHEMA_001.json`; source `gene_annotation_episode/bvbrc_data_schema.py` SHA256 is `c1ed67b843cc54e06b03cf520fc4937736cd4caaaceeac61381f237fef5f2981`. The Data snapshot defines all `binding`, `grading`, `input_results`, native page/cell and `host_qualification` children.

N owns `SourceDocumentV1`, `NativeDocumentResultV1`, `NativeNumberV1`, native tables, `NumericCellV1`, `PopulationV1`, association/identity/row records, `OriginalRequestV1`, `DocumentSelectionV1`, `ReferenceMembershipV1`, and `ComparativeSystemsSheetV1`. D owns `QualifiedDataInputV1`, `DataPopulationSelectionV1` and `SuppliedRecordSetsV1`. C owns `CalculationParametersV1`, `ComponentRequestV1`, `RatioComponentV1` and `ComparativeSystemsComponentsV1`. P owns `ProviderParametersV1`, requested selection/projection and provider envelope shapes. I consumes these; it does not change their numerical meaning. These ownership labels correspond to the exact proposed files already listed in `BINDING_AND_WORKLOADS_001.md`.

Root reviews one frozen shared shape. The schema source is contract evidence in this directory, not a runtime dependency on `verification/`. N may package its assigned definitions; D/C/P package their assigned definitions and consume N's shared types. They must not each create incompatible versions of NumericCell/Population/Entity. An intentional schema delta requires one additive shared contract amendment and affected consumer changes. Independent workers can begin against the frozen schema and examples; only actual integration of delivered functions requires the corresponding completed implementation.

## Revised extractor and provider signatures

These replace the incomplete extractor signature in the initial document:

```python
extract_comparative_systems_data_inputs(
    qualified_inputs: tuple[QualifiedDataInputV1, ...], *,
    artifact_bytes: dict[str, bytes],
    selection: DataPopulationSelectionV1,
) -> SuppliedRecordSetsV1

consume_bundle(
    bundle: dict, *,
    artifact_bytes: dict[str, bytes],
    supplied_values: list[dict],
    qualified_data_inputs: tuple[QualifiedDataInputV1, ...],
    requested_form: dict,
    parameters: ProviderParametersV1,
) -> dict  # ProviderResultV1
```

The other parse/build/calculate/projection signatures keep their responsibilities. The `build_comparative_systems_sheet` output additionally retains `document_selection` and `native_documents`, as enumerated in the schema. Native documents retain complete TSV text, raw row tokens, source locations and raw numeric lexemes, permitting later interpretation without reacquisition. Full outer artifact bytes stay separately bound.

`QualifiedDataInputV1` is exactly:

```text
qualified_result: the existing full bvbrc_data_qualified_result_v1
raw_binding:
  source_ref: string
  raw_artifact_ref: string
  sha256: lowercase 64-hex string
  byte_count: nonnegative integer
  bytes_key: string
```

The actual Python bytes are `artifact_bytes[raw_binding.bytes_key]`; JSON does not pretend that bytes are strings or follow a filesystem path. `bytes_key` equals `raw_artifact_ref`. `raw_binding.source_ref`, `raw_artifact_ref`, and `sha256` must equal `qualified_result.binding.source_ref`, `native_artifact_ref`, and `native_sha256`. The actual bytes' length/digest must match. The same digest must equal `grading.parse_result.retained_native_sha256` and, where a sheet exists, `grading.parse_result.sheet.custody.native_sha256`. Data core, selected fields, filters, sort, page selectors, native schema and original population key come from `grading.prepared` and the existing saved Data sheet, not caller-restated labels.

`BVBRCDataHost.read` (lines 296–328) returns only the qualified value. Its `_stored` (lines 231–280) already reads/verifies original bytes, receipt, original request, grading and publication-input custody, but does not put the bytes in the returned value. I's host input collector must use the existing **Python instance** `api.bvbrc_data.read(reference, context=context)` (or `APIServiceExecution.read_bvbrc_result`) and the verified `binding.native_artifact_ref` to obtain already retained bytes. This is not a new public `api.bvbrc_data.read` tool operation or a new external GET. It must recheck possession and exact original selected evidence/content bindings before passing the wrapper and bytes to P. In the initial consumer table, the resolver class name `_Binding` was inaccurate; the actual class is `_Inputs`, and `definition_input`, `submit_inputs`, `manifest_member`, and `download_capability` are its methods.

`AppServicePublications._grade` needs a ComparativeSystems-only input collector, analogous in placement to the existing retained-input hook. It adds `qualified_data_inputs` and the exact retained byte entries when this selected provider needs them. Native-only requests pass an empty tuple and need no Data bridge or Data result. P passes those values to D only for selected dependencies. Merely embedding a self-consistent QualifiedResult with true flags in `supplied_values` does not confer host qualification. The host, not D/P, owns that guarantee; a pure function can only validate supplied shapes and relationships. No parser/reader/calculator consults Store or selects a source.

The complete conforming wrapper example is in `FILLED_EXAMPLES_001.json`, `qualified_data_wrapper`. Its byte-map entry is listed in `raw_byte_inputs`, pointing to `SYNTHETIC_DATA_RESPONSE_001.json`. The hypothetical host flags are clearly labelled **NO REAL ADMISSION**; they do not claim an actual action, service response or communication test.

## Parameters, row identity and population refinements

`CalculationParametersV1` now has exactly `version`, `requests`, `duplicate_policy`, `absolute_tolerance`, `relative_tolerance`. This supersedes the initial parallel arrays (`selected_components`, `view_selections`, `population_selections`, etc.). Each `ComponentRequestV1` contains its own unique `component_id`, quantity enum, entity, selected native view or supplied record set, population ID, nullable PL/PG family kind, nullable explicit comparison pair, nullable reference membership, nullable category, and nullable native formula. This prevents misaligned selections across workers. It is a finite choice of ordinary functions, not executable formula text.

`ProviderParametersV1` now has exactly `analysis_id`, `document_selection`, `supplied_data_selection`, `reference_memberships`, `calculation_parameters`. `document_selection.documents` owns native document/profile/input selection, replacing the redundant `native_documents` provider parameter in the initial outline. Future documents use requirement_id; possessed documents use exact source/artifact references. `authoritative_views` maps each stable view ID to document/table; it is not inferred from first occurrence. More than one satisfying object remains ambiguous. Supplied reference membership must be materialized from explicitly selected, bound source records; it cannot become trusted merely because its caller supplied a complete-looking array.

`declared_query_genomes` is an added Population kind. It represents a selected Data query's genome IDs without calling them the genome union executed by the earlier AppService job. Populations store exact raw occurrence counts, valid distinct-member counts, source locations, unresolved members, completeness and relationship to the original execution. Complete-for-retained-artifact scope is compatible with unknown original-query completeness, because those scopes differ. A standalone unknown producer never receives `native_first_object_discard` solely because its filename/schema resembles the retained source; use `producer_version_unverified`. The source-loss diagnostic requires bound producer evidence or a source-executed witness. Never infer deployed version from the locally selected parser profile.

`SourceLocationV1.row_ordinal` and `column_ordinal` are zero-based within the named table's **data rows**, with the header excluded. JSON pointers obey RFC 6901. `NativeTableV1.headers` can retain both malformed variant header rows. `NativeFieldV1.raw_text` preserves original tabular tokens. Valid normalized identifiers are nullable, and the raw fields survive placeholders, unknown fields or conflicts. Coordinates have an explicit convention and are not transformed.

Entity fields are all present with irrelevant fields null. Family requires kind+family_id; pathway requires pathway_id; pathway_ec additionally EC; subsystem requires ID with preserved hierarchy/name; pair requires comparison_id and an explicit pair in the request. Entity strings are source identifiers/context, not unconstrained scientific conclusions. A subsystem ID/name collision prevents equality of views even when display text matches.

## Numerical and relational rules not expressible by shape alone

1. All non-null population/document/view/record/reference/component IDs resolve exactly once in the same supplied immutable sheet/parameter set. Cross-analysis references fail. OriginalRequest is derived from the original authenticated ComparativeSystems task; caller parameters cannot restate different genomes or output destination. All source documents bind that task, or are explicitly separate selected supplemental snapshots.
2. NumericCell available means finite numeric value; every other state has null value. Count fields require exact nonnegative integers; length statistics nonnegative finite values with min ≤ mean ≤ max; percent/fraction ranges apply only to their named coherent identities and denominators. A native token that violates an invariant survives in NativeNumber while the affected numeric cell is invalid. `uncertainty=null` is fixed here; population length SD is not mean uncertainty.
3. Row source locations and NativeNumber lexemes agree with exact retained bytes and declared TSV dialect. Width-mismatched rows retain raw tokens and invalid status. Manual unquoted summary fields cannot be repaired by pandas quoting assumptions. Duplicate JSON keys are detected before normal dictionary decoding can erase them. Selected raw TSV and joined genes are different views.
4. Raw occurrence counts, distinct valid identifiers and tuple association counts are separate. Counts over a retained table may be available while the requested complete original population remains unavailable. Duplicate identical representations do not add unique entities or independent evidence. Conflicting duplicates invalidate affected identity joins and complete-population calculations. A repeated page is not a second population interval. Repeated unique IDs within one Solr response are separately diagnosed; do not silently declare an exact unique-document total from duplicated native rows.
5. A two-digit hex decode requires exact full-token width 2N, hexadecimal symbols, explicit output genome order, non-conflicting positive membership, sum equal to reported occurrence count and positive-genome count agreement. With overflow/width mismatch, all per-genome count cells in that token are incompatible. Aggregate occurrence count, length statistics and explicit positive-genome membership remain separately evaluable. No guessed split, even if an aggregate would make one solution plausible.
6. Calculation requests validate applicable fields. A native view uses view_id and null record_set_id; supplied records use the converse. A family quantity requires exactly plfam or pgfam and matching entity/view. Jaccard requires the supplied exact two distinct genomes and one family namespace. Reference representation requires an explicitly selected compatible membership. Category count requires one literal category. Irrelevant selector fields must be null. No implicit population choice or silent default.
7. Native retained pathway/subsystem formulas retain the initial document's units and exact definitions. Added quantities `pathway_record_ec_occupancy_percent`, `pathway_record_feature_density`, `subsystem_record_role_occupancy_percent`, `subsystem_record_feature_density` use the same tuple-count formulas over **explicit supplied record sets**. Their names, population and acquisition identity differ from native retained quantities. `family_record_genome_occupancy` requires the supplied complete assignment population. Incomplete supplied data may yield a qualified retained-subset quantity, but cannot satisfy an available-complete-population request. Complete empty data means zero assignment records in that database population, not physical absence of a function.
8. A ratio retains numerator, denominator, scale and their units/population identities. Denominator product is exactly the selected observed component-set cardinality × selected declared genome cardinality; it is not the number of genomes with that one pathway. Denominator zero leaves a newly calculated ratio missing with `empty_denominator`. Source zero sentinels remain native measurements. Ratio output equals scale×numerator/denominator and may exceed 1 where its unit is density. Numerator and denominator carry distinct source/method records rather than claiming every number was measured directly.
9. `reported_formula_check` returns the absolute discrepancy `abs(native_reported − recomputed_source_formula)` in that native field's unit. Mismatch is `discrepancy > absolute_tolerance + relative_tolerance * abs(recomputed_source_formula)`. No clipping or score weighting. The request's native_formula enum selects the exact source formula in the initial contract, using the original native population and appropriate joined/unjoined operands. It cannot substitute a supplied later snapshot or arbitrary selected subset. Unrecoverable operands produce missing/qualified discrepancy. The parameters affect comparison only, never the native value or scientific ratios.
10. Explicit category count counts genomes whose retained category set is exactly the selected singleton. Contradictory category sets are preserved/qualified and do not contribute to a singleton count. No-record is never inactive. In the filled witness, native prop_active is 1.0, unambiguous active count is **0**, unambiguous likely count is **1**, and one genome has conflicting categories. That zero is a measured count under the stated rule, not missing.
11. Reference representation is the valid-ID intersection divided by the explicitly supplied reference membership cardinality. Unknown reference release remains qualified; incomplete membership does not establish the requested full reference denominator. There is no universal pathway-completion interpretation. PLFam/PGFam, pathway/EC and subsystem/role views are dependent where they describe the same genes.
12. Components store the exact full parameters, formula version and canonical saved-sheet SHA256. Canonical hashing is UTF-8 JSON with sorted object keys, separators `(',', ':')`, ensure_ascii=False, allow_nan=False; it is a local content identity, not a replacement for existing host identity functions. Recalculation produces a new component object; it never modifies a saved sheet or old result. References must resolve in that saved sheet, with no network or resource choice.

## Provider versus parent-return shapes

The existing host expects provider `facts` to be an object, not an array. The schema now specifies `ProviderFactsV1`: exactly the parent's field names, each mapped to a closed `ProjectedFieldV1 {field_id, values, status}`. `values` contains only closed NumericCell, RatioComponent, PopulationFact, MembershipFact, Requirement, Diagnostic or RequestStatus values. `PopulationFactV1` returns counts/completeness; it does not dump all population members. The scientific closure returns `{source_ref, field, value}` with that saved ProjectedField as value, from the original result source. This is a distinction between provider-local projection and the existing outer communication record, not an additional numerical calculation.

`RequestedSelectionV1` freezes each field's finite selector, exact expected cardinality and availability requirement. Stable scientific selectors use named entities/components/populations, not guessed future row positions or artifact hashes. Selector kinds determine value shape. A missing measurement can return one typed missing NumericCell when `typed_state` was requested. It cannot satisfy `available_value` or `available_complete_population`. No extra or omitted field names, unrequested entity substitution, silent truncation or prose side-channel is allowed.

P's `requested_form_schema` must render each named ProjectedField node into the existing JSON Schema requested-form convention, with `additionalProperties=false`, required field names, and `x-bvbrc-comparative-systems` equal to that field's exact `RequestedFieldV1`. The field_id must equal the property name. The allowed `values.items` is narrowed to the selector kind and entity; its minItems/maxItems equal expected_cardinality. The renderer does not require an LLM or put the entire schema into a model prompt. Existing validation still checks source namespaces and semantic identities.

Saved projection validation copies/checks selected saved numerical fields and qualifications; it does not parse or calculate again. P checks exact original task and selected artifact/member bindings against the supplied original ArtifactBundle. I authenticates that bundle and saved sheet/component content through existing host receipt/content readers. Latest invalid/partial own results remain latest; an older success cannot be substituted. Nested forwarding validates the originally admitted form/source and retains provenance. None of these lookups earns an action or scientific credit.

## Filled examples and remaining limits

`FILLED_EXAMPLES_001.json` includes 25 conforming examples: three populated source-executed synthetic sheets (pathway/subsystem, family, overflow), their separately calculated proposed component objects, the exact Data wrapper, Data selection and supplied records, source document result, document selection, explicit calculator/provider parameters, finite requested selection, provider/parent result, a specific unmet requirement, and all seven numeric states.

The pathway native value is 3/(2×2)×100 = 75%. The separate synthetic later Data response contains five distinct document IDs (the producer witness retains six occurrences including one exact duplicate); its population is three genomes and three ECs, with four distinct genome–EC pairs, giving 4/(3×3)×100 = 44.444…%. The hypothetical later response is assembled from source-witness inputs, with one document per ID. It is not an observed Data API response or a reconstruction of a real historical lost row. The saved-sheet reference example recalculates 2/4=0.5 from retained native rows and 3/4=0.75 from the explicitly selected supplied rows, with the same saved sheet and a different parameter object.

Family input lengths 100,200,300 produce mean 200 amino acids and population SD 81.64965809277261, CV 0.4082482904638631, returned-genome occupancy 2/3 and occurrences per positive genome 3/2. Native 00 for the third genome is preserved as reported zero with unknown full-query completeness. The overflow case preserves `10001`, 257 reported occurrences and two positive genomes, but both per-genome count cells are incompatible/null.

Shape conformity, independent arithmetic checking and source execution are distinct from a production ComparativeSystems parser/calculator test. No real service job, successful public native response, authenticated artifact acquisition or actual ComparativeSystems episode communication was run. Those limits stay open.


## Additive shared-contract closure

The nested handoff shapes and focused corrections are now specified in `HANDOFF_SCHEMAS_001.json`, `SCHEMA_DECISIONS_001.md`, and `HANDOFF_CLOSURE_002.md`. The latter supersedes incomplete parse/build/provider signatures, supplies explicit analysis/producer/population inputs, closes calculated/native fact selectors, and defines the acyclic shared-schema ownership graph. `FILLED_EXAMPLES_001.json` and `CONTRACT_VALIDATION_001.json` identify the exact conforming review examples and checks. This addition preserves the original proposal; it does not approve or implement it.


## Final mapping and parent boundary

`FINAL_MAPPING_AND_PARENT_BOUNDARY_003.md` adds the required nullable per-document producer_evidence_id mapping and specifies the separate closed parent-form rendering boundary. `PARENT_RATIO_FORM_EXAMPLE_001.json` passes the existing communication schema validator; this is structural validation, not actual episode communication. The final schema/examples/check receipts and their hashes are listed in `DELIVERY_MANIFEST_001.json`.
