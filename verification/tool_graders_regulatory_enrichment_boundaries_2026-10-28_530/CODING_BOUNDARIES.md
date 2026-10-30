# Proposed coding boundaries for the four operations in packet 530

These are concrete proposals for root review, not an accepted interface, authorization to begin coding, or a replacement for the user's supplied goal. No production code exists as a result of this packet. Before any fresh assignment, read the original attachment in full, give that worker its exact owned files and accepted public types below, and require verbatim rereading of the objective/all ten principles after tools or substantial source/native examination and rereading of its current implementation contract before handoff. Historical 486/509/518 packets supply evidence and naming vocabulary only. Do not reactivate unrelated workers.

The dependency graph is by **specific typed outputs**, not by completion of whole families. First root freezes the three numerical contracts below. Parsers, pure calculations and producer/resource adapters can then be implemented independently against those ports. One host owner controls edits to shared execution/API/return-registration files. This is development file ownership, not a runtime coordinator, scheduler or new episode type.

## Common conventions, without a new universal grader

Use existing original-artifact retention, resource job custody and typed return mechanisms. Within the family records below, identifiers mean exact submitted/reference/native identities, never inferred names. Every full data artifact has byte identity, extent, actual producer/attempt and original operand association; host paths/hashes remain outside model-facing text.

Numerical cells have fixed keys `value: int|float|null`, `state: available|not_reported|missing_input|invalid|undefined|underflow|unbounded|partial`, `unit` from that family's enum, `source_fields` with native locator or component inputs, and explicit population/reference identity. Preserve native lexical tokens separately, including `-1`, `nan`, infinity and tiny values. JSON NaN/Infinity are forbidden. Zero means a measured/reported or defined derived zero, not a missing/error default. `quantity_origin` distinguishes native model prediction/fitted parameter/native report/derived quantity; “native reported” does not mean observed biology. Uncertainty is `not_reported` unless real data supply it.

Each parser/build result has fixed `status: ok|partial|failed`, `valid_records`, `invalid_records`, `artifacts`, `failures`, `requirements`, and the family sheet when buildable. Failure fields are `code` (family enum), `stage: input|acquisition|execution|capture|parse|join|calculate|projection|delivery`, `artifact_ref|null`, `row_locator|null` (original ordinal plus byte/line locator), `entity_key|null`, `field` (closed field enum), `requirement` (closed operand enum), and `retained_artifact_refs`. Unexpected implementation exceptions remain implementation failures; do not relabel them as missing biology. Valid rows survive one malformed row, one absent file or a later failed stage.

Requested returns are exact schemas with `additionalProperties:false`, bounded source-token labels, enumerated field selections, explicit row windows and completeness. Their values project saved sheet/components without a second scorer or an LLM restatement. A report of incomplete rows has unknown total population, not a convenient prefix count as total. No return grants access to unrequested raw inputs.

## M — One motif matrix / sequence-occurrence authority

### M1: shared records, parser and calculations

**Exact operation:** `identify_transcription_factor_binding_sites`; reusable for the same matrix/scan analysis only. **Exclusive files proposed:** `gene_annotation_episode/motif_contracts.py`, `motif_inputs.py`, `motif_calculators.py`, `motif_result_views.py`; `tests/test_motif_inputs.py`, `test_motif_calculators.py`, `test_motif_result_views.py`. No other task writes those files. HOMER may reference their matrix definition but may not fork it.

```python
parse_jaspar_matrix(raw: bytes, *, artifact: ArtifactIdentity,
    selected_matrix: JasparMatrixIdentity,
    format: Literal['jaspar_pfm_with_header', 'jaspar_pfm_four_rows'])
    -> MotifMatrixParseResultV1

parse_biopython_motif_scan(raw: bytes, *, artifact: ArtifactIdentity,
    request: MotifScanRequestV1, matrix: MotifMatrixV1,
    sequence: SuppliedSequenceV1) -> MotifScanParseResultV1

build_motif_scan_sheet(*, request: MotifScanRequestV1,
    matrix: MotifMatrixV1, sequence: SuppliedSequenceV1,
    native: MotifScanParseResultV1) -> MotifScanSheetBuildV1

calculate_motif_components(sheet: MotifScanSheetV1,
    *, parameters: MotifCalculationParametersV1) -> MotifComponentsV1

project_motif_result(sheet: MotifScanSheetV1, components: MotifComponentsV1,
    *, requested: MotifProjectionV1) -> MotifRequestedResultV1
```

`MotifMatrixV1`: exact matrix accession/version and source, name/taxon only when supplied, ordered alphabet `A,C,G,T`, positive width, full per-position count/probability/score arrays with a declared `matrix_kind`, original row order/lexemes, and no automatic count↔probability inference. For JASPAR PFM, rows are counts; `pseudocounts` is an explicit four-number vector, `background_probabilities` an explicit four-number normalized vector. The actual upstream defaults are zero pseudocounts and uniform background; an adapter records them rather than choosing smoothing. Selected source metadata and matrix header accession must agree. A four-row PFM missing its own accession is associated through the exact acquisition request, not a guessed motif name.

`MotifScanRequestV1`: operation, scoped sequence reference, exact selected matrix reference, `threshold={scale:'log2_odds', value:finite_number}`, `strands:both|forward`, actual symbol/case policy and output request. Preserve actual current behavior by naming raw score units; do not silently implement the historical misleading relative-threshold prose. A future explicitly selected relative cutoff requires a separately reviewed scale operand and finite score-range conversion. It is not this wrapper's current operation.

`SuppliedSequenceV1`: original sequence bytes/string, identity, length in bases, optional original contig/assembly/strand/offset mapping, mapping state. Unknown genome mapping stays unknown. A local sequence starts at 0 regardless of genome position. Preserve original symbols even when native search uppercases them.

**Required native capture format:** new versioned `biopython_motif_scan_native_v1`, containing exact input/matrix references, Biopython/native implementation version, selected parameters, actual PFM/PWM/PSSM arrays, native extrema, ordered full returned hit tuples (`native_ordinal`, signed native position, full-precision native float32 score), scan completion/exit state and any legacy reported fields separately. It also records tested strand policy and sequence length, so missing windows are not inferred from a truncated hit list. Raw matrix and sequence artifacts are retained independently. Optional legacy TSV is a lossy preview only and cannot substitute for this capture.

**Numerical fields and meanings:**

| Field | Inputs / exact calculation / unit / population | Missing and interpretation |
|---|---|---|
| `motif_width_bp`, `sequence_length_bp` | Checked matrix width and supplied sequence length; bases | Invalid/nonrectangular matrix rejected; unknown original genome coordinates do not invalidate local lengths |
| `pwm[b,j]` | `(count[b,j]+pseudo[b])/sum_b(count[b,j]+pseudo[b])`; fraction per column | Zero column total undefined; do not pad or invent counts |
| `pssm[b,j]` | `log2(pwm[b,j]/background[b])`; bits/log2 odds | Preserve zero/infinite/undefined states; no auto pseudocount |
| `score_min`, `score_max` | Sum per-column min/max PSSM entries; log2 odds | Extended-real/undefined range is explicit |
| `native_hit_score` | Full native tuple value; log2 odds, float32 output | Native model score, not probability; original bytes retained |
| `relative_score` | `(native_score-score_min)/(score_max-score_min)`; dimensionless | Only finite nonzero range; no clamping; discrepancy with native legacy rounded value retained |
| `start0,end0,strand` | Forward p: `[p,p+m)`; reverse p: `[L+p,L+p+m)`; local 0-based half-open | Require interval within sequence; original signed p remains native data |
| `forward_window`, `motif_oriented_window` | Exact local slice and reverse complement for minus orientation | Sequence extraction uses existing extraction/mapping definitions when publishing derived sequence records; no invented genome alignment |
| `reported_occurrences`, `distinct_local_loci` | All retained hit occurrences versus distinct `(sequence,matrix,start,end)` loci | Same locus/both strands are separate occurrences; duplicates not erased; completed total only for complete scan |
| `candidate_oriented_windows`, `unscorable_windows` | `max(0,L-m+1)` per selected strand, and actual invalid-symbol window population if captured/fully determinable | Only supported native scan dimensions; unsupported too-short/empty case remains explicit until native verification; occurrence density never a confidence score |

No p-value/q-value is available from this wrapper. Do not fabricate it from relative score. Optional replay validation of native window scores uses this same family calculator with declared double summation and float32 output, preserving the native result/conflict. It must not rerun acquisition or discover new matrices. A full native rescan is execution, not a hidden parser step.

**Failure codes:** `matrix_not_selected`, `matrix_identity_conflict`, `matrix_shape_invalid`, `matrix_counts_invalid`, `sequence_symbol_unscorable`, `scan_dimension_unsupported`, `native_scan_incomplete`, `native_position_invalid`, `score_range_undefined`, `legacy_geometry_conflict`, `dependency_unavailable`. Unscorable windows may coexist with valid sites; missing acquisition is not a completed zero-hit scan.

### M2: faithful capture and local binding

**Exclusive files proposed:** `native_motif_scan_contracts.py`, `native_motif_scan_driver.py`, `native_motif_scan_local.py`, `native_motif_scan_results.py`, `motif_scan_tool_info.py`; corresponding `tests/test_native_motif_scan_*.py`. Host registration belongs to I, not this owner.

```python
prepare_motif_scan_job(request: MotifScanRequestV1, *, inputs: MotifInputBundleV1,
    runtime: MotifRuntimeV1, work_directory: str) -> MotifWorkerPlanV1
run_motif_scan_job(plan: MotifWorkerPlanV1) -> MotifNativeManifestV1
collect_motif_scan_result(manifest: MotifNativeManifestV1,
    *, inputs: MotifInputBundleV1, requested: MotifProjectionV1) -> MotifResultBundleV1
```

The selected worker receives the actual sequence, selected PFM, versioned Bio runtime and caller resource limits. It captures original tuples before any coordinate formatting or TSV rounding. Do not import the whole Biomni genetics module. A JASPAR primitive acquisition supplied by the R6 provider owner must output the exact request/search candidates/selected matrix/response bytes/HTTP state; M2 can already accept a parent-supplied PFM. Neither M2 nor the calculator picks the first candidate, changes the matrix, retries acquisition, or invents a taxonomy.

**Specific dependency:** M1's accepted `MotifMatrixV1`, `MotifScanRequestV1`, native capture shape and build/calculation signatures. R6 dependency, when remote motif selection is needed: `JasparMatrixIdentity + original selected matrix bytes + metadata + bounded acquisition receipt`, not “finish all databases.”

**Verification:** synthetic width-one counts `[7,1,1,1]`, uniform background and zero pseudocount give A score `log2(2.8)`, other bases `log2(0.4)`, relative A=1 and relative others=0; these are hand-check expectations, not results run here. Verify zero-count columns/infinite minima, flat motif/zero range, lower-case, ambiguous symbols, both strands/palindrome duplicates, forward and reverse positions including the L=20/m=4/p=−14 example, boundary/too-short/empty inputs, first-match ambiguity, missing native tuple, tiny/rounded conflicts, full hit retention, output-write failure retaining scan, saved-only replay and equality of published/requested components. Authentic cases must retain actual Bio output on supplied synthetic sequences, with a selected real PFM and its acquisition provenance clearly distinguished from synthetic motifs. No claim of experimental TF binding.

## P — Extract the existing common MACS2 peak authority, then bind ChIP

### P1: common peak format/sheet/components, preserving ATAC

**Exclusive existing files:** `atac_differential_contracts.py`, `atac_differential_inputs.py`, `atac_differential_sheet.py`, `atac_differential_result_views.py` for extraction/delegation of shared peak logic only; relevant peak imports in `atac_differential_result_worker.py` if required. **Proposed new files:** `macs2_peak_contracts.py`, `macs2_peak_inputs.py`, `macs2_peak_calculators.py`, `macs2_peak_result_views.py`. **Tests:** existing peak portions of `test_atac_differential_inputs.py`, `test_atac_differential_sheet.py`, `test_atac_differential_result_views.py`, plus `test_macs2_peak_*.py`. The host owner coordinates any later global import edits.

This is extraction of one implementation, not a second ChIP grader. Existing parse function names become compatibility imports/delegates to the shared reader. `_peak_row` checked geometry, `_peak_links` joins and representation counts currently in `native_counts` must have one authority. ATAC still owns its two-condition eligibility, four tracks and signed likelihood calculations. Historical saved sheets are not rewritten: a pure legacy adapter exposes their retained peak section to the common contract while preserving old version/bytes and original observations.

```python
parse_macs2_peaks_xls(content: bytes | BinaryIO | None, *,
    artifact: Macs2ArtifactV1, callpeak: Macs2CallpeakBindingV1) -> ParsedMacs2PeaksXls
parse_macs2_narrowpeak(content: bytes | BinaryIO | None, *,
    artifact: Macs2ArtifactV1, callpeak: Macs2CallpeakBindingV1) -> ParsedMacs2NarrowPeak
parse_macs2_summits_bed(content: bytes | BinaryIO | None, *,
    artifact: Macs2ArtifactV1, callpeak: Macs2CallpeakBindingV1) -> ParsedMacs2Summits
build_macs2_peak_sheet(*, run: Macs2CallpeakBindingV1, reference: ReferenceV1,
    samples: tuple[SampleV1,...], xls: ParsedMacs2PeaksXls,
    narrowpeak: ParsedMacs2NarrowPeak, summits: ParsedMacs2Summits)
    -> Macs2PeakSheetBuildV1
calculate_macs2_peak_components(sheet: Macs2PeakSheetV1,
    *, parameters: Macs2PeakCalculationParametersV1) -> Macs2PeakComponentsV1
project_macs2_peak_result(sheet: Macs2PeakSheetV1, components: Macs2PeakComponentsV1,
    *, requested: Macs2PeakProjectionV1) -> Macs2PeakRequestedResultV1
```

`Macs2CallpeakBindingV1` preserves the existing fields: run/producer, reference, treatment sample/input refs, supplied-control sample/input refs, selected argv, declared/resolved input format and paired-end state, selected parameters and artifact roles. Add explicitly known assay/target metadata only as supplied, not inferred from tool name. Controls are matched **control/input samples**, not “condition2.” Retain `genome_size_argument` separately from exact effective-size parameter and rounded native header. Effective size does not establish assembly identity. Sample, condition and biological replicate are distinct nullable associations.

General common-format support should authenticate MACS2 2.2.9.1 narrow outputs with supplied controls and model building, while preserving current ATAC 2.2.9.1 mode. Do not remove ATAC's eligibility restrictions globally. Broad peaks/other versions remain explicit unsupported inputs unless their actual native formats are independently established; the four-operation request does not authorize claiming every MACS mode finished.

`Macs2PeakSheetV1` contains all native rows/lexemes, native metadata/numbers, declared run/reference/sample associations, original row ordinals, complete or partial artifact states, and exact cross-representation links. Common fields/calculations:

| Field | Meaning / inputs / unit | Required qualification |
|---|---|---|
| `start0,end0,span_bp,summit0` | XLS conversion `(start1-1,end1)`, width `end0-start0`, summit `abs_summit1-1`; narrow summit `start0+offset`; bases | Cross-representation geometry checked once; no chosen winner for conflicts |
| `native_pileup`, `native_fold_enrichment` | Native XLS summit pileup and fold; narrow signal same fold | Native model outputs; do not infer unretained background value by inversion |
| `native_minus_log10_p`, `native_minus_log10_q` | Native XLS/narrow fields, exact exported precision | `-1` unavailable; no correction over emitted peaks |
| `native_display_score`, `native_summit_score` | Original integer and BED score with selected p/q basis | Never clamp to 1000 or regenerate from rounded logs |
| `p_from_reported_log`, `q_from_reported_log` if requested | `10**(-native_log_score)`; dimensionless, explicitly derived representation | Float underflow state distinguished from exact native zero; exported rounding retained |
| `representation_occurrence_counts` | Existing readable native occurrence counts, per run and representation | Never sum XLS+narrow+summit as separate biological peaks; partial total unknown |
| `unique_linked_peak_count`, `conflicting_link_count` | Exact native-name/run joins with original row lists | Duplicates/ambiguous names remain explicit; missing representation does not erase a valid row |
| `treatment/control total and postfilter tags/fragments`, `native redundancy rate`, `native fragment/model length` | Existing XLS metadata reader outputs | Preserve tags versus fragments, missing/not-measured, selected versus fitted lengths, and rounded native rate |

No peak confidence formula, FRiP, replicate concordance or calibrated uncertainty is implied by these three files. Requested interval overlap/union coverage must use the existing genomic-overlap authority through truthful native interval provenance; it is not a reason to add a private interval-union implementation here.

**Failure codes:** reuse existing located MACS parse/metadata issue vocabulary; add only exact needs such as `input_reference_conflict`, `sample_control_binding_conflict`, `unsupported_callpeak_mode`, `producer_output_incomplete`, `legacy_peak_section_incompatible`. Full controlled empty output can yield zero only with actual completed producer/closed writer/complete artifact evidence. The effective MACS2 writer emits the XLS column header even with no peaks; preserve the parser's missing-header validation.

**Required existing-consumer change:** ATAC's worker and `_native_peaks`/`native_counts` consume this shared result; `project_atac_result` retains its exact outer ATAC comparison contract. No synthetic second condition, no new ATAC differential formula. Saved-only calculations/published/returned widths/counts/aliases must equal the common components, including imported historical sheet adapters.

### P2: ChIP producer and result bundle

**Exclusive new files:** `native_macs2_peak_contracts.py`, `native_macs2_peak_driver.py`, `native_macs2_peak_local.py`, `native_macs2_peak_results.py`, `macs2_peak_tool_info.py`; corresponding producer/result tests. No P1/global edits.

```python
prepare_macs2_peak_job(request: ChipseqPeakRequestV1, *, inputs: ChipseqInputBundleV1,
    software: Macs2RuntimeV1, work_directory: str) -> Macs2PeakWorkerPlanV1
run_macs2_peak_job(plan: Macs2PeakWorkerPlanV1) -> Macs2PeakNativeManifestV1
collect_macs2_peak_bundle(manifest: Macs2PeakNativeManifestV1,
    *, inputs: ChipseqInputBundleV1, requested: Macs2PeakProjectionV1)
    -> Macs2PeakResultBundleV1
```

Request preserves treatment/control, output basename/outdir separately, effective genome-size argument and q cutoff; actual native defaults/format resolution are recorded. Input bundle names every original file, sample/control relation and explicit reference dictionary/assembly evidence. Preserve native AUTO behavior where selected; do not guess a paired-end interpretation. First declared formats must include actual wrapper BAM/BED modes, each separately qualified. Other native formats stay unfinished unless explicitly bound and verified. Native manifest contains exact command/version, resolved output roles, all full logs, XLS/narrowPeak/summits, optional model R and only sidecars actually produced, exit/writer state and original request/input identity. Do not add `-B` silently, use the old 300-second wrapper timeout as policy, or fall back to no-model when fitting fails without an episode-owned selection.

**Specific dependencies:** P1 common binding/parse/build/calculation/result types; caller-selected MACS2 runtime pin and treatment/control/reference bundle. Reuse 460 runtime evidence where compatible, not its synthetic sample identities. Configuration is separate from source availability.

**Verification:** preserve 460 numbers in MAPPING as regression fixtures; require authentic supplied-control/model-building BAM and declared BED output, basename/outdir paths (relative/absolute/space), fitted fragment length, missing/stale sidecars, peak-file track headers, equal/duplicate peak names, geometry/native-number conflicts, sentinels and >1000 display values, malformed partial output, zero peaks versus failed model fit, reference mismatch and sample/control mismatch. Include an authentic completed zero-peak bundle with its XLS header and producer evidence. Retain all artifacts and compare common sheet/calculation/publication/return values. Recalculate saved sheet without BAM/native calls; then exercise real selected child and closed replay. No repeat of already verified ATAC likelihood work unless the shared extraction changes it.

## E — One enrichment component owner for compatible gene/motif populations

Reuse 486's proposed `enrichment_*` modules and interfaces, with the native/population distinctions below. They are still proposals, not implemented modules. Do not create parallel `homer_scores` and `enrichr_scores` for identical fractions/contingency calculations.

### E1: closed records, format readers and metadata joins

**Exclusive files:** `enrichment_contracts.py`, `enrichment_formats.py`, `enrichment_metadata.py`; `test_enrichment_formats.py`, `test_enrichment_metadata.py`. **Specific H1 dependency:** accepted common `EnrichmentSheetV1`, `EnrichmentPopulationV1`, `NativeEnrichmentRowV1` and failure types. H1 supplies HOMER documents; E1 owns the numerical sheet and metadata join once.

```python
parse_enrichr_response(raw: bytes, *, format: EnrichrFormatV1,
    request: EnrichmentRequestV1, capture: ResponseCaptureV1) -> EnrichmentParseResultV1
parse_gene_set_library(raw: bytes, *, format: Literal['gmt_unweighted_v1'],
    identity: LibraryIdentity) -> LibraryParseResultV1
join_enrichment_inputs(parsed: EnrichmentParseResultV1, *, foreground: EntityListV1,
    background: EntityListV1 | None, identities: EntityIdentityTableV1,
    library: ReferenceMembershipV1 | None, population: EnrichmentPopulationV1 | None,
    design: SelectionDesignV1 | None) -> EnrichmentSheetBuildV1
```

Preserve 486's gene occurrence list, many-to-one mapping, explicit namespace/taxon, original registration/library IDs, full response rows and legacy statistical columns, complete GMT memberships, source labels and optional supplied design. Exact accepted native row declaration/version is supplied by E3; no parser guesses a 7-column DataFrame is a 9-column wire record.

Extend the **same** sheet with declared `entity_kind: gene|region|sequence`, `membership_basis: unweighted_presence|weighted_presence|native_report_only`, `comparison_basis: foreground_subset_of_universe|separate_background_population|unknown`, exact target/background IDs/weights/overlap relationship and `native_statistical_method: documented_method_id|unknown`. Native methods and correction family are evidence-backed identifiers, not executable formula strings. For motif enrichment, term identity is exact matrix/library accession or fitted de novo motif identity; target/background membership refers to actually extracted sequence/region occurrences. Percent values are never promoted to exact counts by multiplying rounded percentages by totals.

**Shared numerical sheet fields:** raw foreground/background occurrence/unique counts; per-term actual membership count/weight and denominators; exact `N,n,K,k` and contingency cells when a common finite universe is known; native p/q/auxiliary/combined scores and native method/correction/family; complete tested-family list or its explicit unavailable state; all exclusions/mapping conflicts; native/fitted/predicted provenance. A table of claims alone does not satisfy this sheet.

For native-only data, available numerical p/q/counts remain inspectable while unavailable population-derived fields stay null. A missing universe is not a reason to discard authentic native p/q or overlap identities. Never fabricate integer counts for weighted HOMER output. Preserve sequence-to-original-peak and selected-reference joins before exposing motif presence/enrichment.

### E2: deterministic calculations and projection

**Exclusive files:** `enrichment_calculators.py`, `enrichment_result_views.py`; `test_enrichment_calculators.py`, `test_enrichment_result_views.py`.

```python
calculate_enrichment_components(sheet: EnrichmentSheetV1,
    *, parameters: EnrichmentCalculationParametersV1) -> EnrichmentComponentsV1
project_enrichment_result(sheet: EnrichmentSheetV1, components: EnrichmentComponentsV1,
    *, request: EnrichmentProjectionRequestV1) -> EnrichmentProjectionV1
```

Parameters are an explicit supported sampling model, universe/exclusion policy, exact complete family IDs and `correction: none|benjamini_hochberg`. Projection contains exact term IDs or top-K with one declared available sort field, row window and requested metric enums. Top-K/alpha never change calculation family or episode continuation.

For a finite explicit universe U, foreground F⊆U and term set S: `N=|U|`, `n=|F|`, `K=|S∩U|`, `k=|F∩S∩U|`; cells `a=k,b=n-k,c=K-k,d=N-n-K+k`. Counts are unique entities in the declared namespace, not records/reads/replicates. Shared outputs are `k/n`, `k/K`, `K/N`, expected overlap `n*K/N`, fold `(k/n)/(K/N)`, odds `ad/(bc)` without pseudocount, and right-tail hypergeometric `sum_i C(K,i)C(N-K,n-i)/C(N,n)`. Nonnegative feasible cells are required. Fractions with zero denominator remain undefined; odds with positive numerator/zero denominator are unbounded; `0/0` is undefined. A complete valid k=0 yields p=1; absent k is not zero.

For a declared separate target/background population, share the **same component functions** for target presence fraction `t/T`, background presence fraction `b/B` and their ratio. Label units as fractions/ratio of the actual same-kind entities or explicit effective weights. Do not fill the finite-universe cells until a valid universe/overlap relation is supplied. Native significance stays native; no default Fisher/binomial/hypergeometric substitution. Weighted/generated backgrounds cannot be integer-cast. If H0 establishes a distinct native sampling calculation requiring new deterministic work, add it once to this owner's accepted model enum and functions with its exact sufficient statistics; never approximate it merely to unblock a parser.

BH is computed only over all M members of the declared calculation family: sorted p values use `min(1,min_{j>=i} M*p[j]/j)`, retaining ties/order/term identity. Native q is untouched. Enrichr's unknown fourth statistic and combined score are native numbers with unresolved scale; no assumed z-score/odds conversion or guessed combined formula. MACS peak q is outside this contract.

**Shared failures:** `unsupported_native_shape`, `invalid_numeric_value`, `response_incomplete`, `library_identity_mismatch`, `entity_mapping_ambiguous`, `foreground_outside_universe`, `missing_universe`, `incomplete_test_family`, `overlap_mismatch`, `registration_identity_mismatch`, `native_statistic_semantics_unknown`, `background_population_incompatible`, `weighted_count_not_integer`, `matrix_identity_unresolved`. Missing fourth-statistic semantics does not invalidate unrelated p/overlap fields.

**Numerical fixtures:** reuse 486's U=10,F=3 four-term case. `(K,k)` of A=(3,3), B=(4,2), C=(5,1), D=(1,0) give right-tail p `(1/120,1/3,11/12,1)` and full-family q `(1/30,2/3,1,1)`. For B: expected overlap 1.2, foreground fraction 2/3, term recovery 1/2, fold 5/3, odds 5. This is a hand-checkable proposed fixture, not an executed result. Separate-population example t=4/T=10,b=2/B=20 gives fractions .4/.1 and fold 4, with common-universe p unavailable. Weighted count 2.5 remains weighted, not rounded to 2 or 3. Test missing/partial universe, overlaps/duplicates/ambiguous mappings, empty foreground, zero denominator, native zero/tiny/nonfinite statistics, full versus returned-only family, wrong library/species/release, complete raw rows beyond top-K, native-versus-derived conflict and saved-only recalculation.

### E3: Enrichr primitive and durable native response

**Exclusive files:** `api_enrichr.py`, `enrichr_transport.py`, `enrichr_tool_information.py`, `enrichment_result_publication.py`; `test_enrichr_transport.py`, `test_api_enrichr_service.py`. Host registration I owns `api_services.py` and `api_service_execution.py`.

```python
prepare_enrichr_request(operation: EnrichrOperation, request: EnrichmentRequestV1,
    *, registrations: EnrichrRegistrationsV1) -> PreparedEnrichrRequestV1
EnrichrClient.invoke(prepared: PreparedEnrichrRequestV1) -> SourceSnapshot
# EnrichrService implements all existing APIServicePrimitive ports.
publish_enrichment_result(*, native: NativeEnrichmentEnvelopeV1,
    inputs: EnrichmentInputBundleV1, selector: EnrichmentProjectionRequestV1,
    publication_context: ExistingPublicationContext) -> EnrichmentResultBundleV1
```

One `invoke` performs the selected primitive request and retains its full response. Standard/background registration and enrichment selection preserve original request/native IDs. The episode owns successive selected operations; no private workflow/poll/retry loop or tool-owned first-list selection. Reuse the existing immediate API response/custody behavior with exact stage-specific IDs and no resubmission on replay. A specific current host port remains: generic `APIServiceExecution._execute_locked` rejects any second remote-mutating action in an episode through `api_original_submission_already_exists` (lines 397–404), and `_submission_snapshot` returns the first retained mutating snapshot (323–332). The presence of `SelectedAPIEffects` in the host does not change these generic branches; BV-BRC AppService is separately delegated. The integration owner must provide selected-stage identity/custody for foreground registration, optional background registration and the selected analysis response, or another explicitly scoped use of existing episode boundaries. Do not hide several remote mutations inside one `invoke` or merely disable the mutation guard. The selected final analysis response is the scientific artifact, not a registration receipt. E3 must supply E1 a pinned service/client format declaration and real untruncated responses for both standard and custom-background routes, including empty/error cases. The old unpinned 486 web inspection does not satisfy that dependency.

Input library/species/identifier choices are explicit; unsupported taxon/route is a configuration failure. Restrict library usage to the current molecular goal; do not expose historical disease/drug-prioritization defaults as an accepted biological interpretation. Listing libraries/GMT acquisition/mapping is supporting typed work with no independent score. A minimal direct primitive client may avoid absent heavyweight Biomni imports, but it must verify authentic response semantics. Missing service universe/correction information remains unknown and blocks only matching derived claims.

## H — HOMER native evidence and parser/producer adapter

**First exact dependency H0:** before H1 semantic parsing is assigned, obtain the selected HOMER version/source or primary format specification plus an authentic closed tiny run bundle with original target/background BED, exact genome sequence/masking assets, actual extracted target/background sequence memberships and weights, selected known motif library, complete known/de novo tables/matrices, stdout/stderr and invocation. Required facts are the actual output layout, header/column definitions and scales, integer versus effective populations, sampling/correction methods and tested motif family. These are not currently supplied by this repository packet. H0 may be an evidence task; it must not label a simulation/placeholder a scientific measurement. No installation/network/run was performed here.

**H1 exclusive files proposed:** `homer_inputs.py`, `native_homer_contracts.py`, `native_homer_driver.py`, `native_homer_local.py`, `native_homer_results.py`, `homer_tool_info.py`; `test_homer_inputs.py`, `test_native_homer_*.py`. It does not own enrichment/motif calculations.

```python
parse_homer_bundle(*, artifacts: tuple[HomerArtifactV1,...],
    request: HomerRequestV1, format: AuthenticatedHomerFormatV1,
    reference: ReferenceV1, sequence_population: HomerSequencePopulationV1)
    -> HomerEnrichmentParseResultV1
prepare_homer_job(request: HomerRequestV1, *, inputs: HomerInputBundleV1,
    runtime: HomerRuntimeV1, work_directory: str) -> HomerWorkerPlanV1
run_homer_job(plan: HomerWorkerPlanV1) -> HomerNativeManifestV1
collect_homer_result(manifest: HomerNativeManifestV1, *, inputs: HomerInputBundleV1,
    requested: EnrichmentProjectionRequestV1) -> EnrichmentResultBundleV1
```

`HomerRequestV1` preserves peak/background artifacts, exact genome resource, original region IDs/coordinate convention, fixed selected search size 200 bp, motif lengths as parsed positive integers, native motif-number option and caller-owned thread allocation. H0 defines the actual centering/clipping/deduplication/masking semantics; H1 records original region→extracted sequence occurrences and never substitutes original interval width for the searched population. Supplied/generated background mode is explicit; generated background is an actual retained native product, not an invented random set.

`HomerEnrichmentParseResultV1` yields E1's native enrichment records and population evidence plus M1's matrix data only where definitions match. Native columns receive exact source labels/units with `unknown` permitted. Until H0 establishes meanings, raw header/table fields may be retained but no putative p-value or population cell is populated from a guessed column. Known TF matches, de novo fitted matrix identity and statistical test identity remain separate joins. Every file/row survives the preview limit; lexical file order is not a significance ranking. Missing expected output is typed incomplete output, never “no significant motifs.”

**Verification:** authentic known+de novo outputs and actual header semantics; supplied versus generated background with captured membership/weights; original peaks versus 200-bp windows and edge clipping; masked/ambiguous sequence/exclusion counts; exact matrix/reference joins; output in native subdirectories; files present without HTML; lexical motif10/motif2 order; no discoveries with completed native output; native failure with partial known results; duplicate regions/motifs; unavailable q/correction/test family; weighted background refusing integer-model calculations; native/table/calculated/requested equality and saved-only replay without HOMER/genome loading. The absence of H0 blocks only native semantic adapters/model-reproduction claims, not E1/E2's supplied-population calculations.

## I — Shared host publication, selected returns and episode verification

**One exclusive integration owner** reserves `tools.py` if needed, `api_services.py`, `api_service_execution.py`, `episode_return_records.py` only if a shared change is necessary, `execution_episodes.py`, `scientific_process_episodes.py`, shared result-source/schema registration and native worker dispatch actually touched by the accepted paths. New family receipt/return modules may be `motif_scan_returns.py`, `macs2_peak_returns.py`, `enrichment_returns.py` with exact source registration. Do not copy the entire ATAC workflow or change its scientific ownership. Integration tests belong here: `test_motif_scan_episode_path.py`, `test_macs2_peak_episode_path.py`, `test_enrichr_episode_path.py`, `test_homer_episode_path.py`. Leaf owners provide pure projectors/typed bundles, not global registry edits.

**Specific inputs to I:** M2 `MotifResultBundleV1`, P2 `Macs2PeakResultBundleV1`, E3/H1 `EnrichmentResultBundleV1`; each carries original selected operation/attempt/input scope, retained original artifacts, family sheet, calculated components, requested projection and located failures. I does not accept opaque prose logs or unvalidated dictionaries as successful results.

Before edits read complete affected consumers, including `ExecutionEpisodes.__init__`, `_request_schema`, `assignment_schema`, `resource_tool_contracts`, `fact_sources`, `facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `initial_references`, `resolve`, `resolve_received_reference`, `validate_report`, `validate_received_report`; `APIServiceExecution.assignment_schema`, `operation_contracts`, `catalog`, `_execute_locked`, `_submission_snapshot`, `_publish_handoff`, `read_target`, `read_result`, `facts`, `credit_view`, `_completion`; `EpisodeReturnRecords` and service-specific returns such as `RfamBatchReturns` for received authority; `NativeAtacDifferentialResults`/`AtacDifferentialReturns` when extracting common mechanisms. This mapping read selected full functions and identified longer consumers; it does not claim that all were audited. Read `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, `docs/PRACTICAL_EXECUTION.md`, its original additive contract, and `docs/TASK_AND_STEERING.md` before changes in their domains. No model-facing template was designed or approved in this packet.

Register the actual named scientific tool info/alias with detailed operations/resource instructions and existing `evidence_axis`, `thought_pattern`, `child_tool_info` slots. Launch only selects approaches left open by the parent; the selected resource child retains its iterative ownership. Results record actual work before projection; parsing, hashing, report construction and scientific sheet storage create no extra actions/observations. `retain_tool_grading`/`publish_existing_acquisition` provide custody/idempotency, not numerical validation. `APIServiceExecution.facts` and native return sources need explicit projection/validation/admission so scientific parents receive selected measurements, not just artifact IDs.

Verify each full route: selection → correct resource child → original native artifact/manifest → format reader → shared sheet/calculator → exact requested return → receiver admission → saved-only recalculation → closed replay. Use the real configured execution/provider for live claims; controlled fixtures prove only their stated path. Verify source/operand/reference/sample/library/term/hit identities; partial rows/failures; exact equality of sheet/calculated/display/returned numeric fields; repeated delivery no new scientific contribution; no unauthorized fallback, hidden retry or extra turn. Preserve historical source/calculation snapshots; no future learning rewrites past values. No W05 aggregation or controller policy change. Practical validated completion uses the existing exact-zero expectation rule, without an extra scientific acceptance gate.

## Work that remains specifically unresolved before coding claims

1. Root acceptance of the common peak extraction/admission/legacy adapter port and three numerical owners; parallel tasks must receive those public types, not merely this document's headings.
2. Authentic supplied-control/model-building ChIP and completed-empty XLS format evidence; correct actual default/format metadata for each declared binding.
3. Exact JASPAR selected-matrix acquisition input (or supplied PFM), operational Bio runtime and explicit raw-threshold wording; lossless native tuples replace the defective legacy coordinate preview.
4. H0's complete HOMER native bundle and column/population/model definitions. The wrapper does not provide enough information to freeze a scientific header parser.
5. E3's pinned native Enrichr standard/custom response declaration and route identity; unknown universe/auxiliary statistic/correction family stay unknown until evidenced.
6. Registered real child-owned result/receiver paths and actual resource configuration for all four names. Existing ATAC tests/runtime and the prior 486 proposal do not complete them.

These are individual concrete outputs needed by dependent work. They neither halt independent pure implementation against accepted inputs nor mark any operation complete. The only completed deliverable of 530 is the source mapping and proposed boundary packet.
