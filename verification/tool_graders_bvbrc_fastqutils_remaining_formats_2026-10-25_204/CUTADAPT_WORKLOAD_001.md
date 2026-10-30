# Embedded Cutadapt workload 001

Implementation plan, not a claim of a finished grader or a new user decision.
This is additive to the frozen FastqUtils v2 work in 198. Do not edit 198,
its verification snapshots, the goal, historical instructions or receipts.

## Exact scope and evidence

Parse full Cutadapt 4.9 text reports embedded in a retained Trim Galore 0.6.10
report. The BV-BRC FastqUtils task remains the operation and API execution
remains its resource route. A local synthetic producer run proves this native
grammar; it does not prove the deployed BV-BRC producer version.

Authority for the grammar is the retained Cutadapt v4.9 `report.py`, including
`full_report`, `format_filter_report`, `histogram_rows`, `error_ranges`,
`AdjacentBaseStatistics` and `poly_a_report`; command/report placement is the
retained Trim Galore 0.6.10 source. `native_examples_001/receipt.json` records
five actual executions. Its JSON reports are numerical verification oracles,
not permission to invent JSON files in a real Trim Galore task.

Support single and paired Cutadapt reports; front, back, anchored, anywhere,
linked and repeated adapters; zero matches; empty input; quality/poly-A
trimming; reported filter categories; repeated invocations. Preserve the actual
reported mode. Trim Galore's paired operation may invoke Cutadapt separately
for each mate. A paired library declaration must never turn each of those
single-read counters into pair counters.

SAMstat and p3-sra metadata remain separate unfinished formats. Other Cutadapt
versions require their own source/format evidence. This workload does not
silently treat a matching-looking version as verified.

## Files and owners

Root owns the isolated candidate creation, common metric/schema extension,
`bvbrc_fastqutils_trim_reader.py` dispatch integration, source-pin registration,
tool information and production/episode integration. The parser workload owns
only `gene_annotation_episode/bvbrc_fastqutils_cutadapt_reader.py`,
`tests/test_bvbrc_fastqutils_cutadapt_reader.py`, and its new fixture/evidence
directory. No parser worker may change common contracts or existing consumers.

The later integration test workload owns a separate test file. Its contract
is the existing provider interface, populated native document and original
requested form below. It does not need to wait for unrelated format work.

## Native parser port

```python
def append_cutadapt_report(report, raw: bytes, *, start: int, end: int) -> None:
    ...
```

`report` is the existing `_Report` built for the entire Trim Galore artifact.
`raw` is those complete bytes. `start` and `end` delimit one embedded full
report using byte offsets into that same artifact. Check the supplied complete
bytes against `report.context['content']`; never bind a substring to the whole
artifact's digest. Verify bounded, ordered, line-boundary offsets. This helper
has no network, filesystem, subprocess, LLM, scoring or resource dependency.

The helper appends the existing closed `NativeSection`, `NativeLabel`, `Cell`,
`Population`, `RawBlock`, `NativeLineage`, `Requirement` and `Diagnostic` rows.
It does not finish the outer document. The outer parser calls `report.finish()`
once after all native sections and Trim Galore sections have been processed.

The outer report artifact remains producer `Trim Galore`, version expectation
0.6.10. Cutadapt's native `This is cutadapt 4.9 ...` supplies a version label in
its own section. Never pass 4.9 to `_Report.version`, which also compares the
outer expectation. Missing version yields `producer_version_unproven`; a
different version yields `unsupported_version` and retained unsupported raw
bytes, with no invented measurements. Headerless text must remain unverified.

Use new section keys `cutadapt_summary`, `cutadapt_adapter`,
`cutadapt_adapter_errors`, `cutadapt_adapter_histogram`, `cutadapt_adjacent_bases`
and `cutadapt_poly_a`. The existing `cutadapt_embedded` section retains the
invocation header, command, mode and complete segment boundaries. Section
ordinals increase independently per key in original byte order. All locators
use original-artifact byte offsets, not offsets into a sliced string.

Adapter identity is the native adapter occurrence, not its possibly repeated
name. Use separate histogram/error sections for each end of a linked/anywhere
adapter. Retain native sequence, type, name, mate/end headings and options as
labels at their native locations. Cells sharing a histogram row retain the
same section and row ordinal; each error bin retains its actual error index.
Never join sorted arrays or adapter names to reconstruct row membership.

## Populations and exact numerical fields

Root registers these additional population keys: `cutadapt_input_reads`,
`cutadapt_input_pairs`, `cutadapt_output_reads`, `cutadapt_output_pairs`,
`cutadapt_input_bases`, `cutadapt_output_bases`, `cutadapt_mate_input_bases`,
`cutadapt_mate_output_bases`, `cutadapt_adapter_reads`, `cutadapt_filtered`,
`cutadapt_reverse_complemented`, `cutadapt_quality_removed`,
`cutadapt_poly_a_removed`, `cutadapt_adapter_events`, `cutadapt_poly_a_events`.

Allocate the next unused ordinal per population key in original occurrence
order. A population belongs to its exact invocation and mate/end where
applicable. Adapter/filter/event populations refer to the invocation input
population through `parent_population_refs`; this describes origin, not
independence or a claim that event multiplicity equals unique reads. All native
associations and task-stage links remain null until actual external metadata
supplies a valid association. Do not use basenames to infer sample identity.

| Metric | Native field and unit | Meaning/denominator |
|---|---|---|
| cutadapt_processed_count | Total reads/read pairs processed; reads or pairs | Exact input population count, according to native mode |
| cutadapt_adapter_containing_reads | Reads with adapters / Read 1 or 2 with adapter; reads | Reads with at least one adapter, separated by mate |
| cutadapt_reverse_complemented_count | Reverse-complemented; reads or pairs | Native selected orientation count, separated from adapter event counts |
| cutadapt_filtered_count | Native read fate row; reads or pairs | Preserve the exact filter label; absent filter is not zero |
| cutadapt_written_count | Reads/Pairs written (passing filters); reads or pairs | This Cutadapt invocation's output, before possible later Trim Galore filtering |
| cutadapt_processed_bases | Total basepairs processed and per-mate Read 1/2; bases | All-input total and each explicitly printed mate population |
| cutadapt_quality_trimmed_bases | Quality-trimmed and printed mate rows; bases | Reported removed bases; no inferred per-mate split |
| cutadapt_poly_a_trimmed_bases | Poly-A-trimmed and printed mate rows; bases | Reported removed bases, distinct from quality removal |
| cutadapt_written_bases | Total written (filtered) and printed mate rows; bases | Output bases of this invocation |
| cutadapt_reported_percent | Parenthesized percentages on summary rows; percent | Native rounded value; denominator is the corresponding input reads/pairs or bases, never reverse-calculated into a count |
| cutadapt_adapter_length | Length in adapter header; bases | Native parameter; keep both ends of a linked adapter separate |
| cutadapt_adapter_trimmed_count | Trimmed / 5' trimmed / 3' trimmed; native_count | Adapter events, potentially multiple per read; not unique reads |
| cutadapt_adapter_reverse_complemented_count | Adapter Reverse-complemented; native_count | The native adapter-associated counter |
| cutadapt_minimum_overlap | Minimum overlap; bases | Native parameter; linked ends remain distinct |
| cutadapt_allowed_errors | No. of allowed errors; native_count | Allowed count for the native closed overlap-length interval; anchored single-value form has no invented length range |
| cutadapt_histogram_length | length; bases | Removed length, which can include flanking bases; not necessarily aligned adapter length |
| cutadapt_histogram_count | count; native_count | Event count at that removed length and adapter end |
| cutadapt_histogram_expected_count | expect; native_count | Native chance-model expected count, printed to one decimal; no calibrated function probability |
| cutadapt_histogram_max_errors | max.err; native_count | Nominal configured bound for the row, distinct from observed error bins |
| cutadapt_histogram_error_count | error counts; native_count | One value for every native error-index bin, including explicit zero bins |
| cutadapt_adjacent_base_percent | A/C/G/T/none-other; percent | Rounded adjacent-base proportions; the text does not supply their counts |
| cutadapt_poly_a_length | Poly-A table length; bases | Native removed poly-A length, separated by mate |
| cutadapt_poly_a_count | Poly-A table count; reads | Reported reads in that removed-length bin |

Add axis kind `edit_error_count` for histogram error-bin indices. Other axes
are existing `none`, `native_label`, `length_closed` and `symbol`. The histogram
length and error index are separate coordinates connected by section and row
ordinal. No scientific uncertainty is invented: counts are exact for the
retained native population, percentages are native-rounded, and expected
chance counts are native-estimator values with their reporting precision.

## Preserving failures and ambiguity

Malformed count tokens retain their native token and typed malformed state.
Keep valid independent sections and fields. Duplicate/conflicting required
summary rows are ambiguous; do not select the first. Truncated blocks retain
valid prefix rows and mark the relevant population partial. A zero denominator
is undefined for fractions; an absent denominator is missing.

`No reads processed!` explicitly establishes an input count of zero. It does
not print output, adapter, base or filtering counters. Do not borrow the zeros
in a separate test JSON oracle to populate missing fields in that text report.

Native error bins may exceed the histogram's nominal max.err due to an indel's
effect on the matching/removal lengths. Do not reject that alone. Check actual
row sums and retain inconsistent values with diagnostics instead of repairing
the observations. Repeated adapter events must not be rejected for exceeding
the number of unique input reads.

Preserve unknown nonempty native sections as unsupported raw blocks. Timing
lines may be retained as native text but must not become scientific credit,
annotation confidence or an extra local observation.

## Calculators and consuming path

The parser emits artifact-local input-to-output `NativeLineage` edges only for
the same invocation, same unit and corresponding total/mate population. It
does not assert that Cutadapt output equals Trim Galore's final output.

Reuse the existing separate `calculate_retention(sheet, *, job,
parameters_sha256)` and `calculate_fastqutils(sheet, *, parameters)` functions.
Their exact `CalculationBinding` selects the two count cells and populations,
uses method `retention_v1`, and supplies the matching native lineage. The
existing functions calculate after/before, before-after and removed/before.
Do not put these formulas into the parser or introduce a second scoring
language. The other native numbers remain available as individual sheet fields.

The full consumer sequence is unchanged: `parse_trim_galore_report` ->
`parse_fastqutils_artifact` -> `populate_fastqutils_sheet` ->
`resolve_calculation_inputs` -> `calculate_fastqutils` ->
`project_fastqutils_facts` -> `FastqUtilsBundleAdapter` ->
`BVBRCFastqUtilsReturns`. Root updates the content pin for the new source
closure. Existing schemas, original selected fields, custody checks and seven
typed return families remain enforced. There is no new episode or root tool.

## Required evidence and handoff

Use all five retained native cases. The single run is 4 reads/58 bases in,
4 reads/28 bases out, 4 quality-trimmed bases and 2 adapter-containing reads.
The filtered run is 3 reads/24 bases out. The paired run is 4 pairs/116 bases
in and 4 pairs/56 bases out, with 58 input and 28 output bases per mate.
Trim Galore embeds 4 Cutadapt output reads but its final FASTQ has 3 reads and
24 bases. Preserve those different counters. Empty text must not invent the
omitted JSON fields.

Run additional small actual producers for linked/anywhere/front/repeated
adapters, no matches and poly-A before claiming those branches verified.
Use deliberate mutations for unsupported version, truncated text, duplicate
rows, malformed counts, multibyte offsets and repeated names/invocations.
Compare native tables numerically to their actual JSON output where available.
Separate those native executions from synthetic corruption tests.

Provider/integration tests must show native metrics and exact 28/58 or 24/58
base retention reaching the original requested form; verify requested order,
unknown associations, partial-return behavior, and saved-sheet recalculation
with parsers/network/subprocesses disabled. Existing 198 checks remain relevant
but do not prove the added parser. No deployed-service claim without a real
authenticated BV-BRC artifact.

Every worker must read the original goal, reread its objective and entire
16-principle block after substantial source/native study and after each tool,
and return to this exact contract before claiming completion. New information
may require an additive contract correction; do not silently edit its meaning.
