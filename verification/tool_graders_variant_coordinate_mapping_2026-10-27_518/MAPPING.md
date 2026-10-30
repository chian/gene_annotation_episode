# Variant and coordinate operation mapping — source inspection 518

This is implementation evidence for the parent review, not a goal, a scope amendment, a frozen interface, or a coding assignment. The supplied user text remains authoritative, with R1–R7 intact. Only the six assigned operations are mapped here. No production code, tests, inventory rows, environments, or scientific results were changed. No application imports, native programs, tests, network calls, or resource jobs were run.

`SOURCE_INDEX.json` records exact source spans and hashes. `INSPECTION_RECEIPT.json` distinguishes inspections, limitations, and execution that did not occur. References below use `G` for `reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genetics.py`, `C` for the adjacent `cancer_biology.py`, and otherwise name files within `gene_annotation_episode/` explicitly.

## Findings for interface review

| Operation | Actual underlying analysis | Reuse boundary | Missing working path |
|---|---|---|---|
| `liftover_coordinates` | `pyliftover.LiftOver` using supplied hg19↔hg38 chain assets | Coordinate/reference metadata and original-coordinate conventions; not an alignment confidence calculation | Complete native mapping capture, explicit coordinate convention and chain identity, typed result binding |
| `detect_and_annotate_somatic_mutations` | GATK Mutect2 → FilterMutectCalls → SnpEff | Generic native variant representation should be shared with equivalent VCF producers; alignment/site measurements stay with existing calculators | Authentic native headers/records, tumor/normal sample joins, allele/annotation parser, numerical sheet and requested return |
| `detect_and_characterize_structural_variations` | samtools extraction → LUMPY → bcftools filter/query; annotation is a copy placeholder | VCF/reference provenance and interval primitives; SV event/breakend measurements are distinct from per-alignment differences | Extraction command repair, faithful SV parsing and event identities, genuine molecular annotation or explicit unavailable result, typed return |
| `analyze_copy_number_purity_ploidy_and_focal_events` | CNVkit batch/call; local length-weighted ratio summaries and explicitly heuristic purity/HRD-like calculations | Existing genomic-overlap sheet/calculators for equivalent region overlap, with an honest native-input adapter | CNVkit artifact/parser binding, validated reference/sample joins, explicit derived-vs-heuristic quantities, requested return |
| `analyze_cas9_mutation_outcomes` | Biopython `pairwise2.align.globalms` plus per-read indel categorization/grouping | Existing pairwise sheet/calculator, reference-site sheet/calculator, and BV-BRC MSA reference-difference components | Native traceback retention and adapter, parameter/symbol-policy ports, read/target/condition joins, aggregate outcome sheet/return |
| `analyze_crispr_genome_editing` | The same Biopython alignment plus guide-location and template-substring checks | Same pairwise/reference-site components as Cas9; no second alignment scorer | Correct coordinate selection, retained supplied sequence/guide/template relationships, qualified marker observations, typed return |

All six complete wrapper bodies and their matching descriptors were read. Their function-body hashes match the retained `gentner.json` values. A final exact-name search of current package and tests (`*.py`, `*.json`, `*.md`) found no occurrence of any of these six names. This supports “no direct binding found under these names,” not absence of the reusable analyses. The fixed `WORK_STATUS.json` rows remain pending and are preserved verbatim in the source index; those labels are not the basis for the mapping.

The current PATH resolves none of `gatk`, `snpEff`, `samtools`, `extractSplitReads_BwaMem`, `lumpyexpress`, `bcftools`, `cnvkit.py`, `cnvkit`, or `conda`. This was filesystem/PATH inspection only, not executable probing. Under the inspected retained Python 3.12 package directory, `Bio`, `pandas`, and `numpy` paths exist; `torch`, `pyliftover`, `cnvlib`, `pysam`, `cyvcf2`, and `vcf` paths do not. Normal import of the retained genetics module would encounter unconditional `torch` imports at G:76–77 even though the three assigned genetics operations do not need torch. No configured remote resource, alternate environment, version compatibility, or dependency loading was verified.

## Existing shared numerical and return interfaces

### Pairwise correspondence

Source-established signatures in `biopython_pairwise_grader.py`:

```python
build_biopython_pairwise_sheet(native: dict, *, molecule: str) -> dict
calculate_biopython_pairwise_scores(sheet: dict) -> dict
grade_biopython_pairwise(native: dict, *, molecule: str) -> dict
```

The sheet is `biopython_pairwise_sheet_v1`; calculated output is `biopython_pairwise_scores_v1`. The current producer `sequence_ops.align_pair(query, reference, *, molecule, mode='local', gap_open=-10.0, gap_extend=-0.5)` returns `biopython_pairwise_native_v2` with lengths, mode, matrix label, gap parameters, Biopython version, native score, aligned strings, coordinate path, and operand intervals (116–152). No-alignment is explicit. The sheet preserves original native fields, reported-value conflicts, whole-column counts, checked geometry, and residue correspondence. The calculator defines literal normalized identity, aligned/paired coverage and their denominators; null unavailable data is distinct from explicit no-alignment zero counts (184–282, 286–419).

`tools.py::_align_one` (1501–1548) publishes the sheet, projects convenience identity/coverage aliases from its calculated values, and stores original operands and intervals. `_publish_read_alignments` (837–864) preserves independent failures and successful rows. The existing public `sequence.align` / `reads.align` schemas (226–244) expose molecule and mode but not the gap penalty. Both editing wrappers use gap-open **−2**, whereas the current public path supplies `align_pair`'s default **−10**. Therefore a direct alias would change the computation. A shared parameter port or faithful retained-pairwise2 adapter is required before delegation.

There is a second policy gap: current `align_pair` uppercases and maps U→T for nucleotide alignment, and the sheet advertises that normalization (`biopython_pairwise_grader.py`:275–278). The upstream editing wrappers pass supplied strings unchanged to pairwise2. Retain actual case/U handling and exact native algorithm/version; do not claim normalization that was not performed. The shared contract must represent the distinct native parameter/symbol policies without copying its numerical implementation. A change of native implementation from pairwise2 to PairwiseAligner also needs equivalence verification, especially first-optimum selection/ties and terminal gaps; it is not established by equal match/mismatch constants.

### Selected reference positions and insertions

Source-established signatures:

```python
extract_biopython_reference_sites(native: dict, *, molecule: str, selection: dict,
    operands: dict, source: dict, original_mappings: dict | None = None) -> dict
calculate_reference_site_components(sheet: dict) -> dict
map_operand_interval(operand: dict, mapping: dict | None,
    interval: list[int] | None) -> dict
project_reference_site_return(sheet: dict, scores: dict,
    requested_fields: dict) -> dict
```

`alignment_site_inputs.py`:18, 78–100, 147–291 and `alignment_site_calculators.py`:1–116 define `reference_site_comparison_sheet_v1` / `reference_site_components_v1`. Source shape is exactly `{alignment_ref, source_ref, native_artifact_ref, provider, format, native_version, native_locator}`; the current Biopython reader requires provider `biopython.alignment`, format `biopython_pairwise_json`, and empty locator. `operands` has query/reference entries with `{subject_ref, length, unit, alignment_unit, molecule}`. Selection is either `{kind:'reference_positions', positions:[...]}` or `{kind:'reference_window', start, end}`. Coordinates are zero-based local positions/half-open intervals. Ordered requested duplicates are retained but counted once.

Site rows already preserve reference/query symbols, query gaps, substitutions, outside-alignment and unavailable states, original mapped intervals and mapping status. Contiguous insertions already have an event ordinal, reference boundary, query interval/sequence, and alignment-column interval. Shared counts include substituted positions, query-gap positions, insertion events, inserted query positions, and explicit coverage/identity denominators. No edit wrapper should reconstruct those counts from prose or write another alignment difference loop.

Actual consumers are more restrictive than the pure function: `alignment_site_native.reference_grading` (218–271) authenticates native sources/operands and supports current Biopython, phmmer and minimap2 providers. `tools.py::_alignment_sites` (1550–1641) retains the grading and publishes only calculated summary fields. `alignment_site_action_records.py`:19 recognizes **only** `sequence.sites` and `result.blast.hsp`; its own-action reader verifies journal, operation, source, artifact, selection and operand identity (35–217). `alignment_site_returns.py` (233–253, 547–717) projects requested rows/components and validates frozen values. `scientific_process_episodes.py` (502–554) gathers those specific owned actions into requested facts and validates the return.

A new wrapper action calling a pure site reader is therefore **not** already connected to the requested-return path. Reuse of the existing action path must retain real own-action identity; a wrapper result cannot be relabeled as a completed `sequence.sites` action. Otherwise an explicitly reviewed result adapter/consumer extension is needed. No extra model call is needed to restate records.

### Minimap2, BV-BRC and overlap boundaries

`minimap2_grading_inputs.py::parse_minimap2_paf_row(line: bytes | str, *, native_version: str | None=None)` and `build_minimap2_placement_sheet(native, *, preset, native_version, query_metadata=None, reference_metadata=None)` feed `minimap2_placement_sheet_v1`. `minimap2_grader.calculate_minimap2_placement_scores(sheet)` retains PAF native matching/block counts, mapping quality (255 unavailable), path insertion/deletion/skip counts, cs equality and native tags with their separate meanings (96–197). These are placement measurements, not somatic genotype, structural-variant event or function probabilities. Use the existing shared reference-site reader for equivalent requested site correspondence; do not reinterpret PAF `N` skips as deletions or `tp` as a SAM supplementary flag.

`bvbrc_msa_calculators.msa_reference_differences(alignment, *, analysis_id, population, reference, member_row_indices, alphabet, case_policy, original_correspondences)` (211–306) is a second existing relevant comparison contract. It uses actual reference row identity, ungapped offsets and original correspondences. It classifies both-gap, insertion/deletion relative to reference, canonical identical/substitution, and ambiguous/other columns. `bvbrc_msa_grader.calculate_msa(sheet, parameters)` actually dispatches to this function (22–110). It is explicitly a column comparison, not normalized variant alleles. Its canonical-symbol policy differs from the literal normalized pairwise/site contract; preserve that meaning in a common component design instead of silently treating the counts as identical. Parent review must settle reuse of these common difference components before new edit categorization code is assigned.

`bvbrc_genome_alignment_calculators.calculate_genome_alignment_components(data, *, calculation_plan)` and `recalculate_genome_alignment_sheet(sheet, *, calculation_plan)` (1–96) dispatch retained Mauve, backbone and XMFA calculations, including source coordinates and coverage. This is reusable for the same supplied formats, but not evidence of a chain-file liftover or LUMPY/GATK caller. BV-BRC `Variation` and `WholeGenomeSNPAnalysis` appear in pure application preparation definitions (`bvbrc_application_definitions.py`:1–16, 30–39, 416–475); preparation is not a completed scientific output parser. Future equivalent VCF outputs should share the molecular variant representation after authentic formats are inspected. `bvbrc_comparative_systems_sheet.py`:126–149 confirms its `variant_matrix` rows contain superclass/class/subclass/subsystem names; this is not a DNA variant matrix and must not be reused on that label alone.

Source-established genomic-overlap signatures:

```python
build_genomic_overlap_sheet(*, request: Request, sets: Sequence[ParsedRegionSet],
    native_pairs: Sequence[ParsedOverlapPairs],
    reference_relations: Sequence[ReferenceRelation]) -> Sheet
calculate_genomic_overlap_components(sheet: Sheet, *, parameters: Parameters) -> Components
```

The sheet is `genomic_region_overlap_sheet_v1`; calculation output is `genomic_region_overlap_components_v1` (`genomic_overlap_inputs.py`:743–776; `genomic_overlap_calculations.py`:1–202). It already owns exact-chromosome half-open overlap widths, occurrence identity, unions, fractions and partial-result populations. Its native-pair contract expects retained actual overlap evidence; it does not synthesize absent pairs from coordinates. The CNV wrapper's in-memory pandas overlaps are **not** currently accepted native pair documents. A format-specific adapter/shared contract extension must preserve true pair-generation provenance; do not fabricate bedtools output or copy the overlap calculator. Gene/segment joins must resolve assembly/contig identity before calculating an overlap. Existing overlap schema reference information does not establish the source wrapper's implicit coordinate convention.

## Per-operation evidence and missing ports

### `liftover_coordinates`

**Exact source signature and result:**

```python
liftover_coordinates(chromosome: str, position: int, input_format: str,
    output_format: str, data_path: str) -> str
```

G:1–68 and matching descriptor at `tool_description/genetics.py`:2–39. Supported source branches are only hg19→hg38 and hg38→hg19. Both files `data_path + '/liftover/hg19ToHg38.over.chain.gz'` and `.../hg38ToHg19.over.chain.gz` are constructed before branch selection (32–42). The call is `lo.convert_coordinate(f'chr{chromosome}', position)` (52), with no strand argument. The return is a prose log. Only the first native mapping's chromosome, position and strand are included (54–61); no mapping list, chain metadata or artifact is saved.

**Joins and numerical meaning:** The source carries the input build labels, chromosome string and position into a mapping call. Position base is not declared in its descriptor/docstring and no offset conversion is visible. Pyliftover is absent from the inspected retained environment, so its complete native mapping tuple, ambiguity behavior and coordinate convention have not been authenticated here. Do not invent a fourth tuple field, score calibration, assembly accession, or a one-based/zero-based conversion. Bind input coordinate and convention, exact source/target assembly/contig identities, selected chain bytes/version, and every returned mapping/strand to the same original input. Position is a coordinate, not a confidence score.

**Actual failures/partials:** `pyliftover` import is outside `try` (21,25) and can escape. Unsupported conversion returns error text only after loading both chains; missing unrelated reverse-chain data can prevent an otherwise selected direction. Empty mapping returns an error log. Other exceptions after import become log strings. Already-prefixed `chr1` becomes `chrchr1`; no type/range/assembly validation is implemented. Multiple mappings are silently truncated by the wrapper. No durable partial/native record exists.

**Missing ports:** selected-chain resource/input validation; raw mapping-list retention before first-result projection; explicit coordinate/reference contract; typed mapped/unmapped/ambiguous/unsupported/dependency-failure distinctions; original-input and artifact joins; requested-return publisher/consumer. Reuse general coordinate provenance concepts, but `sequence_mapping` maps an existing supplied path and does not perform assembly liftover. This operation needs validated typed coordinate output, not a new scientific confidence calculator.

**Verification needed:** authenticated package/chain versions and native output shape; both selected directions; strand changes, multiple mappings, unmapped and boundary positions; mismatched/unknown assembly and chromosome naming; missing selected vs unrelated chain; exact coordinate convention; original input retained; saved conversion results can be reread without loading a chain; requested child return equals retained mappings. None was executed in this inspection.

### `detect_and_annotate_somatic_mutations`

**Exact source signature:**

```python
detect_and_annotate_somatic_mutations(tumor_bam, normal_bam, reference_genome,
    output_prefix, snpeff_database='GRCh38.105')
```

C:422–568; descriptor at `tool_description/cancer_biology.py`:49–89. Input paths are tumor BAM, matched normal BAM and reference FASTA; return is a log string. Native invocations are:

```text
gatk Mutect2 -R reference_genome -I tumor_bam -I normal_bam
    -normal basename(normal_bam).split('.')[0] -O output_prefix.unfiltered.vcf
gatk FilterMutectCalls -R reference_genome -V output_prefix.unfiltered.vcf
    -O output_prefix.filtered.vcf
snpEff -v snpeff_database output_prefix.filtered.vcf > output_prefix.annotated.vcf
```

The first two calls capture process output without persisting it; SnpEff uses a shell-joined command (465–520). Files named `.unfiltered.vcf`, `.filtered.vcf`, `.annotated.vcf` and `_mutation_summary.txt` are source-established artifacts. Additional native sidecars/stats and their necessity are unresolved until real native outputs are inspected. The final summary contains total text count and annotated path only.

**Algorithm/reuse:** Genuine external caller/filter/effect-annotation invocations are present, not a local mutation detector. Their internal models and authentic output fields are not installed/inspected here. Alignment/site scoring does not substitute for genotype likelihood or caller evidence. Shared generic VCF record/reference/allele parsing can serve both small-variant and SV producers and later BV-BRC Variation; distinct caller-native measurements and multiallelic/annotation relationships must remain explicit. There is no current somatic-call sheet/calculator/binding under this operation in the searched package.

**Joins and fields:** The normal sample identity is guessed from the filename, not checked against BAM read-group or VCF sample identity (475). The reference FASTA and SnpEff database default are never verified to describe the same assembly/contigs/transcripts. A faithful path must join original tumor/normal identities, sequencing sample/condition/replicate metadata when actually supplied, BAM header reference, selected reference sequence/assembly, original native variant record and allele identity, filter state, and molecular consequence transcript/gene identity. No condition/replicate input is declared. Native VCF headers must define the actual INFO/FORMAT cardinalities, missing tokens, units and sample relationships before a parser signature/schema is frozen. This source does not justify assuming particular depth, allele fraction, likelihood or annotation subfields are present.

**Actual summary defects:** `grep -v '^#' | wc -l` counts every non-header row; the wrapper performs no explicit PASS selection. Substring searches for `SNP`, `INS`, `DEL` and `HIGH` are not typed allele or consequence parsing (531–552). Such row/label counts are neither independent variant-event counts nor function-confidence scores. Shell joins do not quote paths. `CalledProcessError` returns a log at each main stage, while missing executables and other exceptions can escape. Failed row-count calculation can leave `total_variants` unset before file writing (560); pipelines can also hide an upstream read failure behind a successful `wc`. Earlier native files may remain, but no structured partial/failed stage or artifact manifest is returned.

**Missing ports:** execution/version/resource contract; full native retention with stage custody and input/sample identity; header-faithful VCF and SnpEff molecular consequence readers; shared native variant sheet with caller/filter/annotation populations kept distinct; explicit numerical definitions only for observed native fields or justified calculations; publisher and requested typed return that consume the saved sheet, not grep/log aliases. Calibration/uncertainty absent from actual fields must remain unavailable. Do not add clinical interpretation.

**Verification needed:** authentic selected caller versions/formats; mismatched BAM sample name; reference/database mismatch; multiallelic and multiple-transcript records; same native record across stages; missing/invalid INFO or FORMAT; FILTER states and no-call vs zero alternatives; partial/truncated files; command/stage failures; no false count from absent files; saved-only recalculation; exact sheet/publication/return equality and closed replay. Source strings and inventory are not any of that verification.

### `detect_and_characterize_structural_variations`

**Exact source signature:**

```python
detect_and_characterize_structural_variations(bam_file_path,
    reference_genome_path, output_dir, cosmic_db_path=None, clinvar_db_path=None)
```

C:571–818; descriptor 90–129. Returns a log string. It creates `discordant.bam` via `samtools view -b -F 1294 -o ... input.bam`. Intended split-read command is `samtools view -h BAM | extractSplitReads_BwaMem -i stdin | samtools view -Sb - > split.bam`, but passes this as a **list with `shell=True`** (642–662), not a correctly bound pipeline. It invokes `lumpyexpress -B BAM -S split.bam -D discordant.bam -o structural_variants.vcf` (675–688). `reference_genome_path` is logged, never passed to these commands or otherwise read.

Filtering uses exactly `bcftools filter -i 'QUAL>=100 && SVLEN>=100' -o filtered_structural_variants.vcf structural_variants.vcf` (703–714). These are hardcoded native filters, not exposed parameters. Preserve the actual predicate. Signed SVLEN and missing QUAL semantics must be checked on authentic output: a negative native SVLEN cannot pass `>=100`; the intended “size” comment does not establish absolute-size filtering. The source counts `SVTYPE=DEL,DUP,INV,BND,INS` by grep, and queries `%CHROM\t%POS\t%INFO/SVTYPE\t%INFO/SVLEN\t%QUAL\n` into `sv_summary_report.tsv` (716–740, 783–801).

**Simulated branch:** C:748 constructs `annotate_sv.py` arguments, but **never runs them**. C:758–770 explicitly calls the step simulated and copies filtered VCF lines unchanged into `annotated_structural_variants.vcf`, then writes “SV annotation completed.” COSMIC/ClinVar supplied paths do not establish acquired/annotated molecular evidence. Do not promote this copied file or log to annotation measurements. No clinical annotation or recommendation is authorized by this molecular mapping.

**Joins/numerical meaning:** Preserve input sample and BAM reference identity; exact original VCF record order/IDs; chromosome/POS/ALT, type and signed native size; native sample fields and support/quality only if actual headers establish them; paired-breakend/event association and any uncertainty intervals when present; the selected filter population and original records it retains. The tabular query is only five fields and loses critical identity/allele/sample/relationship information, so it cannot replace full VCF. Coordinate basis/END/uncertainty/breakend encodings are not authenticated by this wrapper source; no invented closed SV parser schema is proposed. Read-pair/read support and VCF rows must not become probabilities of gene-function correctness.

**Actual failures/partials:** The pipeline binding is defective; extraction/LUMPY/filter failures return strings with no typed artifact state. File-not-found errors can escape. Grep nonzero statuses are all assigned zero, conflating no match with a read/execution error (728–731). A filtered result with zero counted types divides by zero in the final percentage loop (808). Breakend rows can be counted as separate SVs although event pairing is not read. Native files survive some failures but are not bound as validated partial output. Annotation-copy errors are caught separately.

**Missing ports:** selected native execution/extraction and parameter contract; actual reference/sample binding; complete LUMPY/native-VCF parser; native record-to-event/breakend association before any event summary; shared variant numerical fields plus SV-specific geometry/support, without reimplementing alignment scores; genuine molecular annotation acquisition/parser or explicit annotation-unavailable result; saved-sheet publication/child-return ports. Interval overlap can annotate supplied SV spans against supplied genes only after coordinate/reference resolution and honest native-pair provenance. It cannot manufacture the missing annotation.

**Verification needed:** actual split-read extraction, native LUMPY/bcftools version/output, signed size/missing QUAL, deletions/insertions/inversions/duplications and BND association, empty filtered output, malformed/truncated VCF, repeated/paired records, reference mismatch, missing annotation databases, simulated branch remaining visibly unavailable, stage partials, saved recalculation and child-owned return equality. No such run occurred here.

### `analyze_copy_number_purity_ploidy_and_focal_events`

**Exact source signature:**

```python
analyze_copy_number_purity_ploidy_and_focal_events(tumor_bam, reference_genome,
    normal_bam=None, output_dir='cn_analysis_results', targets_bed=None,
    antitargets_bed=None, gene_bed=None, focal_genes=None,
    log2_amp_threshold=1.0, log2_del_threshold=-1.0)
```

C:953–1292; descriptor 174–241. Indexed tumor BAM and reference FASTA are documented, with optional normal BAM, target/antitarget BED, four-column `chrom,start,end,gene` BED and selected gene names. Default genes are `MYC, ERBB2, CDKN2A` (1021–1022). These labels are selection defaults, not evidence that those genes occur or carry an event. Return is prose.

**Native computation and output:** Finds `cnvkit.py`/`cnvkit`, then probes conda environments `biomni_e1` and `bio_env_py310` (1030–1066). A found fallback in `bio_env_py310` nevertheless gets a later `biomni_e1` command prefix (1072), a source-demonstrated resource defect. Runs `batch tumor_bam -d output_dir -f reference_genome`, optional `-n/-t/-a`, and `--scatter --diagram`. It expects `<tumor-basename-with-final-extension-removed>.cns`, optionally calls `call ... -o <sample>.call.cns -m clonal`, then prefers that file on reported call success (1075–1111). Exact native formats/required CNVkit mode defaults beyond these arguments were not verified.

The parser lowercases column names and chooses log2 from `log2|log2ratio|cnlr|logr`, start from `start|chromstart|begin`, and end from `end|chromend|stop` (1124–1144). It writes `<sample>_cn_summary.tsv` with `purity_estimate`, `ploidy_estimate` and whatever heuristic metrics were obtained; writes `<sample>_focal_events.tsv` with `Gene,Event,Log2` only when events exist (1266–1284). No full invocation/input/segment manifest is returned. Genuine `.cns` bytes are needed for recalculation; the summary loses the operands.

**Exact current arithmetic and meaning (C:1146–1196):**

| Quantity | Source formula/population | Qualification |
|---|---|---|
| `seg_length` | `end - start` per parsed segment | Coordinate convention and valid positive span not checked |
| `abs_cn` | `2 * 2**log2` | Derived under fixed diploid baseline 2; does not consume native `cn` |
| `ploidy_est` | `sum(abs_cn * seg_length) / sum(seg_length)` | Length-weighted derived ratio surrogate, not a fitted purity/ploidy model; no uncertainty |
| `mad_log2` | Median of `abs(log2)` over non-NaN segment values | Median absolute value, not median-centered MAD |
| `purity_est` | `min(1, max(.2, 1 - mad_log2/1.5))` | Explicitly naive heuristic clamp; no allele-specific inputs/calibration |
| `LST_like` | Adjacent iterated segments both at least 10 Mb and absolute log2 difference > .2 | Sorts by one chromosome-like column only, not coordinates; does not reset at chromosome boundaries |
| `HRD_LOH_like` | Count of log2 < −.3 and length >15 Mb | Copy-ratio threshold proxy, not observed allelic LOH |
| `Simplified_HRD_score` | Sum of the preceding two counts | Heuristic composite, not annotation support or validated HRD; clinical extrapolation is outside this task |

**Focal joins (1209–1248):** Reads four BED fields; normalizes both chromosome strings by removing every occurrence of `chr`; selects **only the first** gene-BED row per name. Uses inclusive endpoint comparisons, then chooses the segment with largest `min(end)-max(start)` overlap; an endpoint-touching zero-width candidate may be selected. Calls amplification if log2 ≥ supplied amplification threshold, else deletion if log2 ≤ supplied deletion threshold. Only gene/status/log2 are retained; selected segment, overlap width, assembly and native row identity are lost. This is threshold-defined copy-ratio association, not proof of gene dosage/function. Reuse existing exact overlap components, retaining explicit alias/assembly handling and all native occurrences; do not reproduce the permissive source join as a second overlap authority.

**Missing/failure behavior:** Missing CNVkit returns only a log. Batch failure proceeds and may read an existing same-named `.cns` from the output directory without proving it belongs to the current attempt. `start_col/end_col` may be unassigned if columns are absent. Empty/invalid/nonfinite segment data, zero total length, overlapping segments and pandas omission of missing values are not validated. Exceptions in heuristic/focal sections are appended to the log and other work proceeds; summary null/NaN and errors are not typed. A missing normal is only a batch-input difference; the heuristic formula never uses a matched-normal or allele-specific quantity directly.

**Missing ports:** actual CNVkit deployment/resource and assay/mode invocation contract; retained bins/segments/call outputs and explicit source stage; authentic native format parser; tumor/normal/reference/target/antitarget/gene/segment/condition joins; shared interval adapter; numerical sheet preserving native reported `cn` if present separately from diploid-derived `abs_cn`; validated ratio/weight/missing-input semantics; exact parameterized focal classification; typed partial/errors and return projection. The source establishes the heuristic formulas but not their calibration. Do not replace them silently with an invented purity model or present them as measured purity. A defensible additional fitted model remains unresolved work requiring its actual inputs, algorithm and calibration; this mapping does not select one.

**Verification needed:** authentic CNVkit `.cns`/`.call.cns` fields/version and provenance; normal/no-normal and selected target/antitarget modes; fallback-environment identity; stale-file rejection; chromosome/assembly mismatch; multi-row genes, ties, adjacent intervals and empty genes; zero/negative/missing lengths/log2; duplicate and overlapping segments; chromosome-boundary/order transitions; threshold boundary values; preserve valid partial native rows; saved recalculation and return equality. No CNVkit fit/run was performed.

### `analyze_cas9_mutation_outcomes`

**Exact signature/data shapes:**

```python
analyze_cas9_mutation_outcomes(reference_sequences, edited_sequences,
    cell_line_info=None, output_prefix='cas9_mutation_analysis')
# reference_sequences: {sequence_id: reference_DNA_string}
# edited_sequences: {sequence_id: {read_id: edited_DNA_string}}
# cell_line_info: {sequence_id: cell_line_information} (optional)
```

G:323–507; descriptor 90–126. For each reference ID, each edited read is aligned by `pairwise2.align.globalms(ref_seq, edited_seq, 2, -1, -2, -.5)`; only `alignments[0]` is used (389–398). The retained Bio source describes dynamic programming, affine open/extension penalties, global terminal-gap penalties and multiple-optimum return behavior (`Bio/pairwise2.py`:10–100, 414–502, 520–637). The wrapper neither selects a different resource nor invokes a new predictor.

It scans gap runs but ignores substitutions (400–424). Total inserted/deleted bases across the whole alignment determine category: both positive→`indel`; deletion only→1–10/11–30/>30; insertion only→1/>1; otherwise `no_mutation` (426–438). These are totals per read, not largest-event size. It computes target-site percentages using **all supplied reads for the target**, including skipped unalignable reads (380,458). Cell-line percentages use only accumulated successful classified reads (472–474). Missing cell-line labels become the literal `Unknown`, collapsing absent metadata into one group.

**Exact stored output:** `_detailed_results.csv` has `sequence_id,read_id,cell_line,mutation_type,deletion_count,insertion_count`; `_summary.csv` has `cell_line,mutation_type,count,percentage` (441–486). The return is a log. Local insertion/deletion run positions are alignment-column offsets and are discarded, as are native score, traceback strings, start/end, alternative alignments, original sequences and failure records. No empty-result table schema is explicitly supplied to pandas. Orphan edited-sequence keys not present in the reference dictionary are ignored. Missing reads for a reference only add a log line. No FASTQ qualities, biological replicate/sample unit, molecular molecule counts or editing frequencies beyond the supplied read collection are supplied.

**Reuse and genuinely different numerical work:** Use the shared alignment sheet and checked residue/site correspondence. The new scientific quantity, if implemented, is an explicitly defined distribution of supplied read outcomes by original target and supplied condition/cell-line association, not new alignment scoring. Shared site counts already supply inserted bases and reference query-gap positions; both editing operations must consume the same event representation. Preserve the legacy category result as such where needed, but do not equate substitution-only reads with biological “no mutation.” Specify all-supplied versus successfully analyzed denominators and invalid/unavailable membership; do not fabricate zero-frequency categories for unknown populations. The broad normalizing and gap-penalty ports described above remain unresolved.

**Missing ports:** source adapter retaining actual pairwise2 tuple and mapping ref/read roles (edited read is query, supplied target is reference); native coordinate path derivation checked against traceback; all target/read outcomes including empty/missing/failure; exact sequence identity and cell-line mapping; extension of the one shared correspondence/event representation for any necessary contiguous deletion events; one aggregate outcome sheet/calculator with explicit category policy and denominators; CSV/log consumers projecting that sheet; actual child-owned output capture and return adapter. No proposed new function signature is frozen here: first settle the common component and symbol policies with the parent.

**Verification needed:** substitutions only, identical reads, separated vs contiguous indels, deletion totals at 10/11/30/31 and insertion 1/2, mixed edits, terminal indels, ties, lower-case/U/ambiguous symbols, empty read/alignment, missing target and orphan read IDs, missing/duplicate condition relationships, denominator changes from failed reads, result-order/identity stability, native score preservation, existing sheet equality, saved-only aggregation, full requested return and replay. Existing base alignment/site tests are reusable evidence, not verification of this wrapper.

### `analyze_crispr_genome_editing`

**Exact source signature:**

```python
analyze_crispr_genome_editing(original_sequence, edited_sequence,
    guide_rna, repair_template=None)
```

G:510–643; descriptor 127–158. All supplied molecular sequences are strings; output is a log with no artifact writes. The guide is searched by exact `str.find` in the original, then its reverse complement only if the forward search fails; first match wins and the guide variable is replaced with its reverse complement when found (542–553). There is no genomic assembly, sample/read identifier, quality, replicate or separate reference coordinate input. Any parent-provided identities must remain explicit joins rather than being guessed.

The exact same `globalms(2,-1,-2,-.5)` first alignment is used (559–560). Per-column substitutions and single-base insertions/deletions are reported at the number of non-gap original characters preceding the alignment column (576–583), a zero-based original-local position/boundary. Native strings, score, run geometry and reference association are discarded. This duplicates work already available in shared pairwise/site and BV-BRC reference-difference components.

**Source-demonstrated defects/heuristics:** Target-region membership is tested by searching decimal position strings inside mutation-description prose, not by comparing coordinates (603–606,634–635). The region is `range(target_site-3, target_site+len(guide_rna)+3)`, not an experimentally supplied cut window. Repeated/ambiguous guide matches and empty guide are not diagnosed. No-alignment raises on `[0]`. With a supplied repair template, a central marker is chosen with `marker_size=min(10,len(template)//3)` and a symmetric half-size slice (619–621); odd marker sizes can yield shorter/empty markers. Marker presence in edited but not original produces “HDR likely successful”; otherwise a statement about NHEJ is generated (623–628). These substring observations do not establish repair mechanism, editing causality or success probability. No template/guide design is required or proposed.

**Missing ports:** native alignment and all supplied operand identities; shared substitution/gap/insertion geometry rather than a second scan; explicit guide orientation and selected location/ambiguity state; typed numerical coordinate comparisons using a declared window rule; retained template marker selection and actual string-presence observations, with no inferred repair-mechanism confidence; partial/invalid input handling; shared numerical components in publication/display and requested return. A new separate alignment or mutation confidence score is not justified. Any truly additional quantity is a selected site/event membership or observed marker match under a recorded rule, calculated from supplied data with missing/ambiguous states.

**Verification needed:** same basic shared alignment cases as Cas9; forward/reverse/repeated/absent/empty guide; insertions at target boundaries; guide near original ends; substitutions at positions whose decimal digits collide with target positions; short/even/odd templates and marker already in original; no alignment; multiple or partial records if a future batch wrapper is selected; exact saved-sheet, display and child-return equality. None was run.

## Source-only examples for review, not measured outputs

- Given a supplied no-gap traceback `ACG` vs `ATG`, the Cas9 wrapper's loop increments neither insertion nor deletion count and labels the read `no_mutation`, despite the substitution. The shared pairwise/site components explicitly count a substituted position.
- If guide start is 10 and guide length is 3, its source window is integer positions 7–15. The text `C→T at position 107` passes its substring test because it contains `7` and `10`, although 107 is outside that interval.
- A valid positive-length segment with log2=0 gives source-derived `abs_cn=2`, length-weighted value 2 and heuristic purity 1.0. That last number is a consequence of the formula, not a measured purity.
- A supplied native `SVLEN=-500` does not satisfy the source predicate `SVLEN>=100`; zero counted SV rows make its final percentage expression divide by zero.

These examples follow the inspected statements. They are not native runs, scientific numerical verification, or claims that all actual native formats behave as assumed in the examples.

## Proposed ownership boundaries to freeze before coding

1. **Shared correspondence owner:** resolve pairwise2/PairwiseAligner native format, exact penalties, normalization and tie policy; extend the existing shared sheet/readers if needed. Settle shared site/MSA symbol-category semantics and event geometry. No new pairwise identity, coverage, substitution or indel-position calculator belongs in either editing wrapper.
2. **Editing adapters and aggregate outcomes:** after that contract is fixed, separate native tuple/data capture from one per-read/condition aggregate calculator and its result publisher. Aggregate input must name the shared correspondence outputs, original target/read joins, failure membership and explicit denominator/category policies. The wrappers are independent only after those dependencies are concrete.
3. **Native variant document owner:** authenticate real GATK/SnpEff/LUMPY headers and artifacts before freezing parser signatures. Establish shared reference/record/allele/sample identities and partial/error shapes. Small-variant evidence and SV event geometry may remain separate analysis sections while using the same native record and common component definitions. Coordinate/quality counts cannot replace unavailable caller measurements.
4. **Copy-number owner:** authenticate the CNVkit output contract and source identity; retain measured log2/native calls separately from derived diploid ratios and uncalibrated heuristics. Coordinate the gene overlap adapter with the existing overlap owner; do not invent bedtools provenance or clone interval calculations.
5. **Liftover adapter owner:** first authenticate dependency return shape, coordinate basis and selected chain identity. This is a bounded typed conversion result; no confidence-scoring work is justified.
6. **Shared result-consumer owner:** freeze how each actual child-owned action contributes retained artifacts/sheets and requested typed fields. Existing site action records only accept their two named operation paths. Test exact source, operand, sample/condition, selection and result identities through parent receipt and closed replay. Parsing/aggregation/reporting must not create synthetic episode actions or new scientific observations.

New filenames, new function signatures, and new frozen schemas are intentionally unresolved where native evidence is missing. This pass provides specific source-supported ports for the parent to review; it does not authorize a parallel implementation wave.

## Verification state and remaining work

| Evidence dimension | State for these six names |
|---|---|
| Retained wrapper source and matching descriptor | Complete bodies/descriptors inspected; hashes match inventory |
| Underlying algorithm availability | Biopython Python dispatcher and native source/object paths retained; external caller/liftover/CNVkit dependencies not verified |
| Shared numerical implementation | Existing pairwise, selected-site, minimap2, BV-BRC MSA/XMFA and overlap implementations identified; exact extension gaps above |
| New wrapper sheet/parser/calculator | No completed bindings located; no new implementation made |
| Authentic native outputs | No relevant `.vcf`, `.cns` or `.chain` fixtures found in searched test trees; other artifact stores were not exhaustively searched |
| Numerical verification | No tests or scientific calculations executed; existing test source inspected only |
| Episode result/parent delivery | Shared site path inspected; no matching named wrapper child-return path established |
| Live resource | Not attempted; no login, service, environment, native executable or job run |

Useful existing verification source includes `tests/test_biopython_shared_projection.py`:88–163 (conflicting legacy fields through requested return/replay), `tests/test_alignment_site_graders.py`:498–511 (saved-only recalculation), and the discovered overlap/input/return workflow tests. Their test bodies demonstrate available verification patterns, not newly passing results. Preserve completed baseline evidence and reopen only the stated parameter, format, consumer and native-source gaps. Molecular effect/mapping/support measurements remain distinct from annotation credit; no literature grader or W05 aggregation is part of this mapping.
