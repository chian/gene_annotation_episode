# SAMstat native-output contract and implementation ports

Status: source and native evidence complete for the two pinned producers below; **no parser, calculator or integration has been implemented by this workload**. This is an additive contract for the existing FastqUtils operation. It does not establish which SAMstat version BV-BRC runs.

## 1. Evidence and the actual retained artifact

The official source is `https://github.com/TimoLassmann/samstat`. The retained 2.2.3 worktree is commit `86e05e4870fe782defea40f0c854e4e110e2e6f7`; the retained 2.5.0 checkout is commit `e41808fb7ad34cc9b2c97c3eed60ad8e5eed50be`. Their native HTML formats and some populations differ. A format claim must identify one of these observed contracts, not merely the executable name. An unknown release remains unsupported until its relevant implementation and native output have been examined.

The complete caller is `193/sources/p3_fqutils/lib/fastq_utils.py::run_alignment` (path prefix `verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193/`). It executes `samstat <prefix>.all.bam` with no JSON option, then deletes `.all.bam`. Its retained `.aligned.bam` was produced with `samtools view -F 4`, so it cannot supply the unmapped denominator. Its exception handler writes an HTML failure report for **every** `CalledProcessError`, even though the wording says “segfault.” The inspected caller Makefile, requirements and README do not pin SAMstat. No live service authentication or execution was performed.

The current 204 candidate path is:

`FastqUtilsBundleAdapter.consume_bundle` → `resolve_documents` → `parse_fastqutils_artifact` → `extract_fastqutils_metadata` → `populate_fastqutils_sheet` → `resolve_calculation_inputs` → `calculate_fastqutils` → `project_fastqutils_facts` → saved codec → `BVBRCFastqUtilsReturns` and the original typed request.

`parse_fastqutils_artifact` currently sends `samstat_html` to the unsupported-artifact reader. The existing `mapping_v1` calculator needs actual FASTQ/BAM record correspondence; it must not be repurposed for these aggregate reports. A report is not an observed record list.

## 2. Exact ordinary function interfaces

Future implementations must use these public signatures. Return objects are dictionaries validated against the existing named 204 schemas, with the finite additions below. No new episode, root tool, model call, workflow or score-expression interpreter is involved.

```python
# bvbrc_fastqutils_samstat_native.py — dispatch, shared document construction

def parse_samstat_html(raw: bytes, *, context: dict) -> dict:
    """ParseContext -> NativeDocument; no filesystem or network acquisition."""

# bvbrc_fastqutils_samstat_legacy.py — only the pinned legacy literal format

def parse_samstat_html_2_2_3(raw: bytes, *, context: dict) -> dict:
    """NativeDocument for the observed SAMStat 2.2.3 producer."""

# bvbrc_fastqutils_samstat_svg.py — current textual values and caller failure HTML

def parse_samstat_html_2_5_0(raw: bytes, *, context: dict) -> dict:
    """NativeDocument for 2.5.0 text/table/accessible labels, never SVG inversion."""

def parse_samstat_bvbrc_error_html(raw: bytes, *, context: dict) -> dict:
    """Recognized caller failure -> typed failed measurements, no scientific zero."""

# bvbrc_fastqutils_samstat_mapping.py — saved-sheet calculation only

def calculate_samstat_report_mapping(
    sheet: dict, *, job: dict, parameters_sha256: str
) -> list[dict]:
    """CalculationBinding -> two Component records for the selected report strata."""
```

The dispatch module may expose shared **document construction helpers only** to the two readers; it must not import the readers at module import time if that creates a cycle. Exact helper signatures are a first coding handoff, documented in `WORKLOADS_002.md`. Scientific data must not be encoded in renderer-dependent generic HTML helper objects returned across the public ports.

Invalid caller/context types, failed content binding, invalid canonical references or a schema-invalid job raise the existing `FastqUtilsContractError`. Missing scientific inputs, unsupported native versions, malformed sections, producer failure, truncation and undefined ratios are data returns, not uncaught exceptions. No function reads local source checkouts, invokes SAMstat, fetches Plotly/JSON/BAM, or consults an LLM.

## 3. Preserve existing envelopes; add finite scientific meanings

Retain the complete shapes of `NativeDocument`, `Cell`, `Population`, `NativeSection`, `NativeLabel`, `RawBlock`, `Locator`, `Component`, `Requirement`, `ParseContext` and the saved representation. This work does not propose an untyped sidecar for measurements.

Integration adds the actual formats `samstat_html_2_2_3`, `samstat_html_2_5_0`, `samstat_bvbrc_error_html` wherever format enums are mirrored. Keep `samstat_html` as an acquisition/dispatch declaration. A supplied generic declaration can resolve to a recognized versioned actual format. Supplied version and native version must agree; disagreement is `native_header_conflict`/`unsupported_version`, with both labels and raw bytes retained. A native version label is a producer assertion, not binary provenance. The receipt supplies binary provenance for the local examples only.

Each proposed metric in `NATIVE_FIELDS_001.json` needs an ordinary `metric_spec` and the relevant finite enum entries. Field families with multiple meanings must be split into the listed concrete metric specifications; a `Cell.meaning` never contains a slash-delimited choice. Add units `inverse_bp` and `events`. For native display SI counts, the `samstat_display_*` metrics store the displayed mantissa and original token with a dedicated **display** meaning in the ordinary metric specification; exact count metrics alone can be arithmetic operands. Their units remain `native_count`/`bases`, with `native_rounded`, and the token retains the suffix. They must not be passed to a calculator as an unscaled cardinality. An implementation can omit these redundant display cells only if it retains their full `NativeLabel` and raw-byte locators; exact sublabel cells remain mandatory.

Add section keys:

- `samstat_header`, `samstat_summary`, `samstat_mapping`, `samstat_pair_flags`, `samstat_length`;
- `samstat_base_start`, `samstat_base_end`, `samstat_base_relative`;
- `samstat_quality_start`, `samstat_quality_end`, `samstat_quality_relative`;
- `samstat_mismatch`, `samstat_insertion`, `samstat_deletion`, `samstat_identity`;
- `samstat_notes`, `samstat_plot_unavailable`, `samstat_failure`.

`section_ordinal` is the zero-based occurrence of that section key in native byte order. An R1 and R2 block are separate occurrences, not independently sorted lists. `Locator.block` preserves the actual HTML section or legacy variable name; `field` identifies the member, such as `y`, `error_y.array`, `mappingtableval[1]`, `dd`, or the specific table column. `row_ordinal` is its zero-based point/row index. Byte offsets are half-open offsets in the original supplied bytes; preserve HTML entity spellings in `native_token`, while label strings may be decoded. No invented offset when exact byte accounting is unavailable.

Add population keys `samstat_report_records`, `samstat_report_sequences`, `samstat_mapq_ge30`, `samstat_mapq_10_29`, `samstat_mapq_0_9`, `samstat_unmapped`, `samstat_excluded_secondary`, `samstat_excluded_supplementary`. Population ordinal is **0 = report-wide/all mates, 1 = native R1/unpaired stratum, 2 = native R2 stratum**. A population with no observations is created only when actually represented by a native table/section, not from a guessed mate count. Legacy per-mate mapping table counts live on ordinals 1/2. Current all-counts column lives on ordinal 0 and optional R1/R2 columns on 1/2. This is why legacy all-report calculation selects both represented mate populations rather than a parser-invented combined count.

All these populations have `kind=native_report_population`, `representation=native_report`, the current artifact as their member artifact, empty `member_record_refs`, null `association_ref` and `pair_key_rule`, and no reference dictionary or fabricated alignment/sequence records. Native mate/MAPQ subpopulations can reference their report parent and one another's actual disjoint strata. R1 and R2 are disjoint record strata; all-mates overlaps each. Different documents are never assumed disjoint. The quality encoding on these aggregate report populations remains `unknown`; a known native formula or producer offset is specified by its metric and source evidence, not a fabricated quality-character record set.

`Population.scope` is `partial` for an explicitly declared native prefix and otherwise `unknown` when only report bytes establish the result. Original input consumption is not proved by a closed HTML document or exit 0. `NativeDocument.parse_scope=complete` means complete parsing of the supported retained report, not a complete original experiment. An independently supplied, source-bound execution record may later establish input completeness through metadata; this parser does not acquire it or infer it from the filename.

Use existing `Axis` kinds when exact: `none`, `mapq` with inclusive lower/upper bounds for the three mapped bins (unmapped uses `native_label` with null bounds), `base_closed_1` for native unclustered start positions, `quality_score` for native quality-bin indices, and `length_closed` with equal lower/upper for a native density x point. Add `base_offset_from_end_0` and `read_fraction_bin_0_100` to preserve optional legacy coordinate meanings. For relative bins the native display index 1..100 is retained as label, with lower=(index−1)/100 and upper=index/100 and a **half-open** interval meaning fixed by the new kind. For clustered legacy axes use `native_label` and null numeric bounds: labels such as `250-255` are not reliable closed intervals. Start, end and relative coordinates must never be conflated with reference coordinates.

Symbol-specific metrics (`samstat_base_A_count`, etc.) preserve base identity while the one available `Axis` carries position. The MAPQ/mate stratum is the population reference. Use the same pattern for mismatch-base fields. Clustered variants are separately named `_rounded_bin_mean`; do not put rounded averages into count metrics. The seven alignment-error metrics in the field catalog likewise require seven `_rounded_bin_mean` companions when clustered values occur.

`NativeLabel` preserves producer/version, reported input label, reported input format/mode, legends, missing-data explanations, native prefix statements, display tokens and caller error details. `Category` stays empty: SAMstat mapping bins and producer prose are not pass/warn/fail classes. `RawBlock` retains locators for every recognized block and every unsupported script/SVG section. The content-bound native bytes retain the actual payload; a label catalog alone is insufficient.

Add diagnostic codes with exact meanings:

| Code | Meaning |
|---|---|
| `samstat_input_scope_unproven` | HTML does not establish complete consumption of original input. |
| `samstat_native_prefix` | Producer explicitly reports a non-random prefix. |
| `samstat_fastx_quality_offset_defect` | Observed pinned 2.2.3 FASTX path leaves offset zero; native quality index is not a valid decoded Phred value. |
| `samstat_softclip_reconstruction_defect` | Pinned legacy CIGAR reconstruction has the source-established multi-base S cursor defect. |
| `samstat_svg_values_not_retained` | Requested numerical arrays are not supplied by this HTML format. |
| `samstat_caller_failure` | Recognized caller exception HTML, not a numerical success report. |
| `samstat_mapq255_merged` | Native high bin includes MAPQ255; it cannot be separated from available-quality high values. |
| `samstat_report_population_only` | Component describes contributing report records only. |

Existing diagnostics cover nonfinite tokens, rounded values, native estimates, unsupported sections, absent measurements, contradictory counts, missing denominators and version conflicts. Mirror finite additions in all selector, return, saved-codec and dependency validators; do not bypass validation with `additionalProperties=true`.

## 4. Safe parsing and full retention

Use an HTML tokenizer that treats scripts as inert text. For 2.2.3, parse only the known finite literal grammar needed by emitted `mappingtableval`, series objects, their `x`, `y`, `error_y.array`, `name`, and data-array references. Numeric literals, quoted strings, arrays, object punctuation and known variable identifiers can be lexed without evaluating any expression. Known nonfinite spellings such as `-nan` are explicit sentinel tokens, never ordinary JSON numbers. JavaScript evaluation, Python `eval`/`exec`/`literal_eval` over arbitrary JavaScript, browser execution, Node, script loading, and external Plotly requests are forbidden.

Only source-established series prefixes and native group identifiers map to fields. Validate variable uniqueness, array lengths, `data` references, native group/legend agreement, mate identity, finite values, monotonic applicable axes and nonnegative count relationships. A repeated or contradictory assignment is not resolved by “last one wins.” Preserve independent valid blocks when another block fails. Hidden or `legendonly` series are scientific payloads and must also be parsed. A non-emitted all-zero series remains absent unless native bytes themselves explicitly represent it; source knowledge is not permission to manufacture a new observation.

2.5.0 is parsed from the known header/cards/table/notes/footer text and accessible title/description/legend text. Exact counts can occur in the `span.sub` below rounded SI cards. Global length extrema and quality-bin extrema can repeat in per-mate SVG descriptions; they remain repeated representations of the same global quantity, not independent mate measurements. Geometry, axes/ticks, width/height, paths, colours and chart titles are not numerical measurements. The native report has no embedded original arrays to extract for its SVG curves. Full SVG stays retained; unavailable arrays become explicit missing requested measurements. The optional `--json` comparison run is a different acquired artifact, and the real caller does not request it.

No parser reconstructs a count from a rounded percentage or density, converts a legacy KDE to a histogram, converts SEM to SD without n, silently fixes known producer defects, deduplicates by sequence name that the report does not retain, or substitutes `.aligned.bam` for `.all.bam`.

## 5. Typed success, partial and failure returns

Every supported reader returns all required `NativeDocument` arrays, even when empty. Identity and content bindings are supplied by `ParseContext` and checked with the current canonical identity helpers. Native scientific cells use stable `native_ref('cell', context, ordinal)` identifiers in source traversal order. Population and section identities are not based on filename-derived biological joins.

| Evidence | Typed return |
|---|---|
| Supported, closed report with complete numeric table | `parse_scope=complete`; valid cells `available`; population input scope `unknown`; input-scope diagnostic retained. |
| Native `--peek` prefix with closed report | `parse_scope=complete`; observed prefix values `available`; population `partial`; native-prefix diagnostic and count retained. |
| Truncated transfer or incomplete section | `parse_scope=partial`; independent closed cells retained; section `partial`/`malformed`; no fabricated array suffix. A complete literal can be `available` as an observation while projection carries the document/transfer qualification. |
| Legacy 0/0 native `-nan` fraction | Exact zero counts retained; fraction cell `undefined`, value null, native token `-nan`, `zero_denominator` and `nonfinite_native`. |
| Missing QUAL, missing SEQ, native `n/a` | Specific cell `not_measured` or `undefined` as defined in field catalog; absent quality series retained as absent; never zero-quality measurements. |
| Recognized caller exception HTML | `actual_format=samstat_bvbrc_error_html`, `parse_scope=complete` for recognition; `samstat_failure` section complete, `RawBlock.kind=error_report`; requested total/mapping measurement failure cells `failed`, null values; error code/command/output retained as labels. No fake populations or counts. |
| Unknown or conflicting version/layout | `parse_scope=unsupported` or malformed supported section; full raw block, version labels, `supported_parser`/`native_version` requirement; no speculative numeric interpretation. |
| No artifact returned after native process failure | Existing document resolution returns missing artifact and execution-evidence requirement; there is no HTML to parse. |

Requirements use existing typed fields, affected canonical refs and actual source refs. Missing exact modern histogram/position data uses `required_data=requested_measurement` and `samstat_svg_values_not_retained`; failure evidence uses `native_execution_evidence`; incomplete transferred bytes uses `complete_native_bytes`. These describe the information needed by the responsible episode. They do not choose a retry, acquire data or require a new approval step.

## 6. Ordinary report-bin calculator

Add `samstat_report_mapping_v1` as a `CalculationRequest` variant:

```json
{
  "calculation_id": "report_mapping",
  "method": "samstat_report_mapping_v1",
  "populations": [
    {"selection":"semantic", "document_id":"report",
     "population_key":"samstat_report_records", "population_ordinal":1},
    {"selection":"semantic", "document_id":"report",
     "population_key":"samstat_report_records", "population_ordinal":2}
  ]
}
```

The `populations` list has one or two unique exact selectors. It selects one report-wide population, one native mate population, or both disjoint native mate populations **from the same document and producer version**. No automatic mate discovery, cross-document summation or total-plus-mates double counting. Single-end legacy requests select ordinal 1; current all-report requests select ordinal 0. A missing requested R2 is a missing operand, not an instruction to silently use R1.

`resolve_calculation_inputs` resolves selectors to exact `CalculationBinding.population_refs` and binds the four `samstat_alignment_bin_count` cells per selected population in bin order ge30,10_29,0_9,unmapped. It can also bind an explicitly native `samstat_alignment_total_count` for validation when present; the calculator does not require a parser-derived mate total. `comparison_kind`, `read_key_rule`, `lineage_ref`, `lineage_basis` are null; `quality_thresholds=[]`. The request and resolved binding are both saved. No new numeric free parameter is needed because the native bins and chosen populations are explicit. No native high bin can be split at MAPQ255.

For each selected population, require exactly one finite nonnegative integer per bin, source/schema/version consistency, complete literal/bin coverage, and an input mode established as alignment report. If a native total is supplied it must equal the sum of its four bins. Require actual native mate-disjointness before summing two populations. FASTX mode is incompatible, even if its plots say “Unmapped.”

Let `T` be the sum of all four counts over the selected disjoint populations, `U` the selected unmapped count and `H` the selected ge30 count. Return exactly two `Component` objects:

| metric | numerator | denominator | value | meaning |
|---|---:|---:|---:|---|
| `samstat_report_mapped_record_fraction` | T−U | T | (T−U)/T | Mapped fraction of contributing alignment records in selected report strata. |
| `samstat_report_ge30_record_fraction` | H | T | H/T | Fraction in native ge30 bin, including MAPQ255. |

Both use `unit=fraction`, `method=samstat_report_mapping_v1`, `meaning=native_report_derived`, `uncertainty=not_estimated`, `threshold=null`, explicit population refs, **all actual count operands used**, integer numerator/denominator, the supplied parameter hash, and canonical `component_ref` using the saved sheet hash. `encoding_basis` and `lineage_basis` are null. Neither is annotation confidence. Native rounded percentages remain separately selectable cells and are not the arithmetic input.

`T=0` returns `undefined`, value null and `zero_denominator`. Missing one bin returns `missing`/`truncated` with null value, while retaining available operand refs. Conflicting/overlapping populations or contradictory totals return `incompatible`, null value. A known native prefix can yield a finite `partial` component explicitly labeled `samstat_native_prefix`; no full-input fraction is claimed. With an otherwise closed report but unproven original input scope, the report-population fraction is `available` and retains `samstat_input_scope_unproven` and `samstat_report_population_only`. Incomplete HTML that happens to retain a closed complete table can produce only a `partial` component. Requirements/diagnostics flow through existing `calculate_fastqutils` and projection validation.

Concrete expected results from retained native reports:

- 2.2.3 `mixed.sam`: selected R1+R2 counts `[5,3,2,1]`, T=11, mapped=10/11, ge30=5/11. Supplementary contributes, secondary does not.
- 2.5.0 same input: all-counts `[4,3,2,1]`, T=10, mapped=9/10, ge30=4/10. Both secondary and supplementary are excluded.
- Two Q0/Q40 bases: legacy native arithmetic mean 20.000000 and native SEM 14.142136; modern error-probability mean 3.0. None of these is a substitute for the other.
- Legacy lengths 4,8,8: density values 0.090324 and 0.169574 are native estimates, not count values 1 and 2.

No composition, quality, retention or distinct-read mapping calculator is reused for these aggregates unless a future explicit input satisfies that calculator's existing populations and operand semantics. The native measurements do not need artificial recomputation to become legitimate numerical sheet cells.

## 7. Metadata, saved state and existing consumers

`extract_fastqutils_metadata` receives the original task, native documents and source-bound supplied values. Report filename and `<h1>` are labels only. Do not infer library, input pointer, recipe stage, reference accession, paired read correspondence, aligner or successful prior stage from them. Report R1 includes unpaired records; this is not proof of a paired-library association. A reference dictionary is absent from HTML. The original submitted reference name alone cannot reconstruct actual report/reference correspondence.

Any explicit library/stage/reference declaration follows the existing declared-but-unproved association handling. It cannot invent record correspondences or make the filtered retained BAM the original denominator. Native parent/subpopulation relationships are artifact-local, and no before/after lineage is emitted.

`populate_fastqutils_sheet` concatenates native cells/populations/labels/sections and metadata without silently changing measurements. `resolve_documents` needs the generic-to-versioned-format acceptance rule. `resolve_calculation_inputs`, `calculation_requirements`, semantic selectors and `calculate_fastqutils` need explicit SAMstat branches rather than the existing fallback to report consistency. `project_fastqutils_facts`, `project_fastqutils_return_facts`, `BVBRCFastqUtilsReturns`, schema builders and saved-codec validation must accept the added finite metrics/populations/diagnostics and preserve the existing requested-form boundaries.

Extend the adapter's saved dependency manifest with all new parser/spec/calculator modules. A saved sheet plus explicit calculation parameters must suffice for offline recalculation; no native source checkout, executable, HTML execution, Workspace lookup or input reacquisition is required. Recalculation creates a new components/parameter identity and preserves earlier returned observations. Saving only selected cells would violate the full-native-retention contract.

## 8. Open implementation facts

The schema additions, enum mirroring, public helper handoff, dispatch, selectors, calculator and saved-return tests are unimplemented. A native report and this contract do not prove that the child-owned selected Workspace path, provider, saved sheet and requested return work together. That integration belongs to the existing Fastq owner. The deployed BV-BRC version remains unknown and cannot be inferred from the retained caller repository or this upstream checkout.
