# HIC fields and exact consumer changes (proposal)

This mapping is additive to439/441. No field is an annotation probability.
`CURRENT_LITERAL_DEFINITIONS.json` in prerequisite002 was mechanically extracted
from the actual production literal with ast.literal_eval and json.loads, without
importing the production module. Actual current metadata extraction takes the
additional explicit `request=` argument absent from439's early .pyi; retain it.

| Existing record/field | HIC mapping, units and missing behavior |
|---|---|
| ContactSpec.file/source_ref/input_key | Original selected retained local identity and authorization; verify complete bytes before parsing. No path or URL discovery. |
| format/format_version | Selected hic_binary_v9; observed9 only after validated actual header. Unsupported version leaves scientific header unavailable, with located failure. |
| NativeMetadata.source_file/source_ref | Unchanged original identities; same across every population call and population seal. |
| group_path | null. No synthetic HDF5 group. |
| coordinate_system/bin_type/bin_size_bp | zero_based_half_open/fixed/explicit BP resolution. Bins are derived exactly from native chromosome length and resolution, not inferred from returned records. |
| storage_mode | hic-symmetric only with native cis orientation; every finite record uses native x<=y. |
| value_field/value_dtype | count/<f4. Both native int16 and float32 counts convert losslessly to float32, so mixed blocks have one stable population-independent canonical dtype. |
| native_value_dtype | fixed descriptive string hic_v9_block_int16_or_float32; HicBlockRead preserves each actual encoding/flag. Do not pretend all native blocks were float32. |
| value_kind/value_unit | Explicit supplied contact_count or supplied_contact_weight and source unit, retained separately from actual float encoding. Fractional storage does not prove a read count or a normalization. Signed supplied weights remain incompatible with existing count heuristics. |
| attributes | Original header key/value strings, dtype utf8, scalar shape, stable logical /hic/attributes/<ordinal> paths; retain duplicate attributes as occurrences or mark conflicting duplicates, never dictionary overwrite. Large string bytes remain in original artifact with retained_only state if necessary. No source string becomes an instruction. |
| vectors | Index descriptors for actual named normalization and native-expected vectors; stable paths /hic/normalization/<index> or /hic/expected/<index>. Unknown lengths null. Merely indexed bytes do not get extent complete. Native expected vectors are native_expected_not_used, not the selected denominator. |
| reference_assertion | genomeId retained as an assembly label when present; the documented hictk default unknown and an empty ID give label null with the original raw string retained in HicHeader. Accession remains null unless explicitly supplied elsewhere; actual biological contigs exact. A label match establishes consistent assertions only. |
| chromosomes | Original biological chromosome index/name/length in bp. All pseudochromosome retained only in proposed NativeMetadata.hic.chromosomes with kb_proxy unit. |
| proposed NativeMetadata.hic | Full typed raw header facts, byte order, source version, header/footer/NVI offsets, resolution lists and chromosome-local ID-space declaration. Independent of selected population. |
| PopulationExtraction.selected_region/order | Exact original requested population key/token/[start,end); no auto expansion or first chromosome. |
| extent/bin_count/fixed_bin_size_bp | Complete/partial/unavailable/incompatible as actually read; n=end_bin-start_bin when valid axes known, width selected r. No records returned is not a source of n. |
| native_storage_mode | hic-symmetric for validated cis matrix; otherwise null/unavailable. |
| data_table_keys | Exactly five keys, same stable population/role convention and role order as existing output compiler. |
| bins | TSV header/dtype unchanged. bin_id=native chromosome-local k; chromosome_index=original header index; start=k*r; end=min((k+1)*r,L). Native global IDs are not fabricated. |
| contacts | NPY structured bin1_id:<i8,bin2_id:<i8,value:<f4,source_block:<i8,source_row:<i8. Preserve all selected actual records, including explicit0/nonfinite/negative/duplicates; sort entire rows. source_block is actual indexed block ID. source_row is sparse flattened record ordinal or dense slot ordinal, as fixed by witness. |
| weights | NPY<float64>(n,), exactly selected chromosome-local vector entries aligned to bins. Preserve NaN/Inf/zero/negative. v9 float32 widening is exact; no inversion or square root in parser. |
| cell_states | Existing dtype/tags1..5. Type1 raw NaN/Inf uses2/3/4. Unresolved no-value uses1 and remains unavailable. Missing block facts remain primarily population extent; do not materialize n*n missing states. Validated type2 padding is an encoding witness, not a state1 missing measurement. |
| dense_values | not_native_representation for block-wise HIC. A native dense compressed block is not a whole selected n*n dense native array. Contacts retain all nonfiller slot values, original file retains each block payload. No whole-matrix materialization. |
| TableDraft.encoding/shape/dtype/row_count | Existing exact TSV/NPY encoding and canonical dimensions; present zero-row arrays have real NPY headers. No zero-byte pretend table. |
| TableDraft.native_source_locator | hic_bytes matrix/zoom range for bins/contacts, hic_vector for selected weights, or null for genuinely absent roles. Per-contact source row/block remains exact. |
| TableDescriptor.file | Supplied only by existing host capture after C3 closes each file. Parser never manufactures artifact identities. |
| raw_cell_population.directed_cells | n*n, from known physical axes. |
| unique_unordered_cells | n*(n+1)/2 only with established native cis symmetry. Not added to directed count. |
| stored_rows | Number of selected actual native contact records retained, excluding dense filler slots. Duplicates remain counted but prevent complete-population use. |
| explicit_zero_rows | Actual nonfiller native records whose finite numeric value is0. Dense fillers are excluded. |
| implicit_zero_directed_cells | For complete unique symmetric record population only, n*n-sum(1 for diagonal stored row else2). Type2 fillers and unindexed zero cells belong to this mathematical absence; rectangular filler count is never subtracted as a population count. Otherwise null. |
| native_nonfinite_directed_cells | Directed representation count of actual nonfinite records; exclude type2 filler NaNs. These cells are unavailable for arithmetic, not implicit zeros. |
| unavailable_directed_cells |0 only with complete native cell coverage; null for failed block unless exact affected population cells are independently established. |
| validated_observed_row_count | Count of validated finite nonnegative actual records with valid orientation/coordinates; excludes fillers and invalid native records. No independence or coverage inference. |
| NormalizationSummary.specification | Exact request unchanged. Raw → not_requested and no weights. Weighted missing/invalid → missing/partial; no raw fallback. |
| valid_bin_count/masked_bin_count/invalid_bin_count | Selected physical bins: finite positive / native NaN / other invalid. They sum to n when the complete selected vector exists. Unknown counts null. |
| PopulationReadEvidence.axes/index/selected_records_extent | Derived from exact physical axes, full selected zoom index, all required block outcomes, complete payload checks and uniqueness. Not inferred from contact list length. |
| expected_block_count/read_block_count/failed_block_ids | Declared indexed block count / completely decoded indexed blocks / exact unsuccessful IDs. Complete zero-block matrix has0/0/[] plus independent present matrix/zoom proof. |
| required_native_row_ranges | [] for HIC; do not invent HDF5 row ranges or apply pixel-table source_row bounds to block ordinals. |
| symmetry/implicit_zero_semantics | native_hic_symmetric / validated_sparse_absence only with required proof; otherwise not_established. |
| proposed PopulationReadEvidence.hic | Source identity, exact matrix/zoom byte ranges and closed block outcomes. Read-count equality without this evidence cannot authorize a complete HIC sheet. |
| elements/metadata/pair rows | Existing supplied BED assignments, exact anchors, source rows, reference checks, sample/condition/replicate and dependence joins. No biological class is inferred from native chromosome/name. |
| raw_contact/source_locators | Actual raw value or proven implicit0; native hic_block locator includes original chromosome indices, r, block ID and recorded ordinal. Missing matrix/cell gives qualified null, never a replacement matrix. |
| C2 components/projections | Existing explicit raw or divisive calculation and requested typed fields. All means, variance, fold and windows use saved canonical tables only. Native expected vectors and matrix sumCounts are retained but unused. |

All observed/source values have no measured uncertainty unless explicitly supplied
in MetadataSpec; parser error/missing states are not uncertainty intervals.

## Consumer edits that a later implementation must trace

| Actual function/module | Required narrow change |
|---|---|
| chromatin_interaction_contracts._DEFINITIONS/_relationships | Add the proposed optional closed HIC header/evidence variants and locator/failure enums. Require HIC proof on complete HIC populations and original native/version/unit/ID-space relationships. Keep existing saved Cooler records valid. |
| chromatin_interaction_tables.validate_population_arrays | Validate HIC chromosome-local bin IDs, original chromosome membership, source block/ordinal domains and native orientation. Its current lower-triangle diagnostic recognizes only Cooler native_row, so HIC failures need hic_block matching; do not transpose malformed rows. |
| chromatin_interaction_inputs._check_sources/extract_chromatin_metadata | Preserve actual native/header assertions and exact original request; select hic_bytes/hic_vector locators for HIC metadata failures instead of unconditional hdf5_path. No lookup/acquisition. |
| chromatin_interaction_inputs._raw_cell | Existing hic-symmetric and hic_block branches mostly apply. Fix dense source ordinal contract; accept proven omitted filler zeros via existing sparse absence only after HIC witness validation. Existing state1 still unavailable. |
| chromatin_interaction_inputs.validate_chromatin_sheet_arrays | Check every HIC row against its block witness, exact source ordinal and physical chromosome grid; require source_sha256 match. Existing code checks only Cooler row ranges. Include HIC in orientation validation; reject forged complete HIC witnesses and count inconsistencies. |
| native_chromatin_interaction_contracts.validate_chromatin_software/bindings/job | Make dependency/source requirements format-specific, allow HIC only with actual accepted binding. Current unconditional h5py/Cooler module assumptions cannot be treated as HIC proof. Backward-compatible API: validate_chromatin_software(value, *, supported_formats=None); caller must supply selected format set for HIC. |
| native_chromatin_interaction_driver._extract_one | Explicit dictionary/branch by selected validated format: Cooler reader or HIC reader. Preserve supplied source stream, exact five output streams, one-population closure/seal and all failures. No filename guessing or try-Cooler-then-HIC fallback. |
| native_chromatin_interaction_driver.verify_software/merge_extractions | Verify proposed SoftwareBinding.native_runtime zlib versions and actual runtime FilePin bytes as well as the HIC module/interpreter. Native common header equality still enforced. Per-population block evidence stays in populations. |
| native_chromatin_interaction_preparation._dependency_bindings/freeze_chromatin_software_binding | Add keyword supported_formats=('cooler_hdf5_v3',) to the explicit freeze helper; pass selected formats through checks. Pin HIC implementation, struct/zlib runtime/interpreter and actual loaded libraries; no new distribution is required by direct reader. Native h5py is required only for selected Cooler support; existing worker needs NumPy/schema packages. |
| native_chromatin_interaction_tool_info.chromatin_interaction_tool_contracts/_INSTRUCTIONS | Render truthful bound formats and HIC supplied-byte instructions from validated binding. Do not advertise unresolved v9 dense or v8 support. This is tool information under existing prompts, not a new model template. |
| chromatin_interaction_result_worker native/saved paths | Signatures/output roles unchanged; consumes amended extraction through H2. Validate witness and use actual retained tables. Saved path must never reopen HIC or require hictk/hic-straw/h5py. |
| native_chromatin_interaction_capture/results and return/receipt consumers | Existing source authorization, output paths and producer/worker custody remain. Review their complete path during H4; test missing bundle with earlier HIC seal, partial blocks and requested weighted-unavailable fields. No speculative shared-policy edits authorized by this plan. |
| chromatin_interaction_calculations._Population.explicit_pairs / projection | No formula or API change proposed. It already recognizes hic-symmetric and explicit divisive weights. Existing malformed-lower-triangle branch uses Cooler locator; H4 must add the HIC hic_block diagnostic match so retained located malformed rows can be skipped as malformed while valid rows remain partial. Keep projection signatures unchanged. |

The proposed lower-triangle choice is to retain original bytes and canonical
malformed rows with exact hic_block locators, keep valid upper rows partial, and
add the located diagnostic branch through exclusive H4 ownership. This is an
explicit consumer gap, not permission for H1 to discard malformed data or edit C2.

H5 additionally owns the narrow chromatin exact-schema alternative branch in
communication._compile_closed_schema and recorded-field validation in
chromatin_interaction_return_views.select_chromatin_return_facts. See
HISTORICAL_SCHEMA_COMPATIBILITY.md for exact transitive definitions, unchanged
old value semantics, alternatives, signatures and file/test ownership. Existing
return-authority and receipt/host paths require regression coverage, not
speculative revision arguments. No production edits to them are proposed.
