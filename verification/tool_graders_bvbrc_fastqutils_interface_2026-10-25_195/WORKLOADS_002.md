# Exclusive implementation workloads after root review

Scope remains `C-L209-FastqUtils::api` / `bvbrc/service/fastqutils` and all five
recipe steps. At most **three fresh coding workers A/B/C plus root** operate
simultaneously. This packet assigns no implementation now. Original193 stays
unchanged. No worker owns runtime/controller/accounting/authority edits.
Each fresh task receives the full authoritative goal, original constraints,
required verbatim reset instruction, this contract and exact owned files.

## Root: common ports and actual integration

Root exclusively owns the four common files in PORTS_002, common contract tests,
`bvbrc_fastqutils_returns.py`, `bvbrc_fastqutils_tool_info.py`, and necessary
FastqUtils-specific edits to `bvbrc_appservice_adapters.py`,
`bvbrc_appservice_host.py`, `bvbrc_appservice_publication.py`,
`api_service_execution.py`, and `execution_episodes.py`. Other files require an
explicit root reassignment. Generic ownership, resource choice, method_loop,
completion formula, credit and controller semantics do not change.

Root first supplies the common schema/identity/specification modules and
contract checks matching the fixture vectors. A/B/C can then implement against
the frozen ports independently. Root does not move format-specific parsing or
calculation into common helpers. Integration imports workers' public exports.

Concrete integration consumers: `_grade` invokes the adapter; `_requested_status`
uses its selected field satisfaction; `AppServicePublications.read` calls saved
projection validation; `completion` uses the newest own publication;
`BVBRCAppServiceHost.facts` adds selected FastqUtils facts;
`APIServiceExecution.__init__/resolve` installs/routes return ownership;
`ExecutionEpisodes._appservice_sources`, `received_report_facts`,
`resolve_received_reference`, `validate_received_report`,
`received_form_references` and `resolve` wire typed return/admission.
Use existing `EpisodeReturnRecords` and original-commission custody, not a new
return journal or an LLM restatement. Descriptor registration alone is insufficient.

## A: sequence/alignment native formats and their mathematical components

Exclusive proposed files:

- `gene_annotation_episode/bvbrc_fastqutils_fastq_reader.py`
- `gene_annotation_episode/bvbrc_fastqutils_sam_reader.py`
- `gene_annotation_episode/bvbrc_fastqutils_bam_reader.py`
- `gene_annotation_episode/bvbrc_fastqutils_composition.py`
- `gene_annotation_episode/bvbrc_fastqutils_quality.py`
- `gene_annotation_episode/bvbrc_fastqutils_mapping.py`
- `tests/test_bvbrc_fastqutils_sequence_formats.py`
- `tests/test_bvbrc_fastqutils_alignment_formats.py`
- `tests/test_bvbrc_fastqutils_sequence_calculators.py`
- `tests/fixtures/bvbrc_fastqutils/sequence/` and `/alignment/`

Inputs: selected plain/gzip FASTQ, SAM1.6, BAM1/BGZF; ParseContext. Outputs:
NativeDocument with record-preserving sequences/qualities, alignment records,
all supported native auxiliary fields, headers/references, local populations,
counts/distributions, partialness and raw-block/source associations. Native
formats cover retained TRIM/PAIRED_FILTER outputs, ALIGN artifacts and clean
reads without inferring their recipe occurrence. No acquisition or tool execution.

Calculators have the exact common signature in PORTS_002 and consume only saved
Sheet/CalculationBinding. They emit composition, Phred-model and mapping
components with explicit operands, denominators and assumptions. FASTQ readers
do not import those calculators; calculators do not import readers.

Required fixtures: multiline FASTQ, sequence/quality mismatch, quality lines
starting `@`, plain bytes under `.gz`, concatenated gzip, truncated member,
empty complete input, IUPAC/invalid symbols, absent/conflicting encoding,
Phred33/64 and BAM numeric quality distinctions, missing FF quality, MAPQ255,
secondary/supplementary flags, duplicate read-segment names, all auxiliary tag
types, nonfinite float tags, long CIGAR, malformed record with intact sibling
boundaries, BGZF CRC/ISIZE/BC/EOF failures and reference/header conflicts.
No new dependency or subprocess. No CRAM/reference fetch or BAI reconstruction.

Handoff: actual NativeDocument fixtures plus saved-sheet calculator fixtures to
C; root exercises them through host publication. A need not wait for B or the
host integration. Full native binary verification remains A's required work.

## B: FastQC and preprocessing reports; comparison components

Exclusive proposed files:

- `gene_annotation_episode/bvbrc_fastqutils_fastqc_reader.py`
- `gene_annotation_episode/bvbrc_fastqutils_trim_reader.py`
- `gene_annotation_episode/bvbrc_fastqutils_pair_report_reader.py`
- `gene_annotation_episode/bvbrc_fastqutils_hostile_reader.py`
- `gene_annotation_episode/bvbrc_fastqutils_retention.py`
- `gene_annotation_episode/bvbrc_fastqutils_consistency.py`
- `tests/test_bvbrc_fastqutils_report_formats.py`
- `tests/test_bvbrc_fastqutils_report_calculators.py`
- `tests/fixtures/bvbrc_fastqutils/reports/`

Inputs: actual supplied FastQC0.12.1 HTML/text/ZIP, TrimGalore0.6.10 reports,
fastq-pair0.3 stderr, Hostile1.1.0 JSON. Outputs: the same NativeDocument port,
all62 registry fields applicable to these formats, native categories and label
identities, complete raw unsupported sections, precise report populations and
report-local lineage. FASTQC HTML graphs never become fabricated tables.

B owns all retention and report-count-consistency functions, whether operands
came from A or B. The common saved Sheet is the only dependency. No parsing
inside a calculator and no calculation inside a reader. Missing stage evidence
does not invalidate an exact native report before/after relationship.

Required fixtures: all12 FastQC modules including absent/empty tables, grouped
positions, NaN, negative tile deviations, display truncation, smoothed GC,
bounded duplication/overrepresentation, adapter names, source-scaled kmer
counts/p-values; ZIP multiple members and path traversal; first/second Trim
report distinctions, paired two-decimal percentages and mixed N/length removal
counter, empty/N/A, separate unsupported Cutadapt sections; pairing four counts
without invented pairs; Hostile8/6/2/.25 and native zero fallback, multiple rows,
overwritten/partial source, version mismatch; unavailable denominators,
after>before, signed report difference and conflicting actual populations.

Handoff: NativeDocument fixtures (including complete unsupported raw sections)
and independent calculator oracles to C/root. B need not wait for A; A's public
schema fixtures suffice to test cross-format comparisons. No service reruns.

## C: joins, retained sheet, provider and exact projection

Exclusive proposed files:

- `gene_annotation_episode/bvbrc_fastqutils_native.py` (dispatch/unsupported only)
- `gene_annotation_episode/bvbrc_fastqutils_metadata.py`
- `gene_annotation_episode/bvbrc_fastqutils_sheet.py`
- `gene_annotation_episode/bvbrc_fastqutils_resolution.py`
- `gene_annotation_episode/bvbrc_fastqutils_calculators.py` (dispatch only)
- `gene_annotation_episode/bvbrc_fastqutils_bundle_adapter.py`
- `gene_annotation_episode/bvbrc_fastqutils_projection.py`
- `gene_annotation_episode/bvbrc_fastqutils_saved_codec.py`
- `tests/test_bvbrc_fastqutils_metadata.py`
- `tests/test_bvbrc_fastqutils_projection.py`
- `tests/test_bvbrc_fastqutils_provider.py`
- `tests/fixtures/bvbrc_fastqutils/bundle/`

Exact ports are in PORTS_002. C uses common helpers and imports public parser/
calculator exports only in dispatch/provider modules. Metadata/sheet/resolution
modules do not import parser or calculator implementations. NativeDocument
fixtures let C begin before A/B finish. C owns no hidden loop or acquisition.

Required tests: immutable pre-download ResultSelector; exact possessed binding;
zero/multiple matched output artifacts; reused/colliding native names; arrays
and repeated recipe entries from actual OriginalTask; typed source metadata,
pointer/value agreement and field-specific qualifications; asserted versus
observed lineage; encoding assumption preserved in calculated return; missing
unrelated metadata leaves counts; one-target null category/population/association;
typed_state versus available_value; exact_rows zero/excess without invented
rows or truncation; original selection/hash mismatch; saved-codec round-trip,
projection-failure-context round-trip and saved revalidation with all parser/
calculator calls disabled. A malformed document does not erase valid siblings.

## Required work that remains explicit

Cutadapt embedded sections need their own supported version/format review;
SAMstat numerical output and p3-sra metadata need actual producer review and
formats. This revision retains them as unsupported RawBlock/source artifacts
with exact acquisition/parser requirements. BAI remains a retained index, not a
read denominator. Native deployment versions, credentials, genuine retained
service output, live execution and full typed episode communication remain
unverified. Five recipe steps and all62/17 declared numerical quantities stay
in scope. No worker may relabel this contract-only packet as completed FastqUtils.
