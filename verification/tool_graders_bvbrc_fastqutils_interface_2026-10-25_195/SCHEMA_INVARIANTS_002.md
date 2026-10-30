# Semantic checks accompanying the full schema

These are ordinary implementation validation duties, not a runtime review gate.
Use full004 plus explicit003 native representation corrections. Frozen002
remains historical. Schema shape, integer/finite checks and the following
relationships are separate from host original-commission/source authentication.

1. **Identity and references.** IDs are unique within their namespace and exact
   analysis. Use PORTS_002 encoder/decoder and pointer constructions; broad JSON
   string shape is not sufficient. Every artifact/source/content relationship
   must match. `Artifact.content_ref == content_binding.artifact_ref`, and all
   digest/length/source fields agree. No guessed filename identity. Native
   record references belong to their actual document and byte version. Sheet
   population/association annotations may extend native data, never rewrite
   native numeric values/tokens. Component references bind actual sheet and
   complete explicit parameter hashes. Actual per-component operand references
   identify consumed quantities; retained but unused measurements stay in Sheet.

2. **Finite semantics.** Validate Python types without bool-as-integer coercion,
   nonfinite floats, duplicate JSON object keys, noncanonical pointers or
   non-UTF-8 strings. Cell/Component available and partial states require finite
   numbers; other states require null. Exact counts are nonnegative integers.
   Invalid negative/native overflow tokens remain retained but unavailable;
   negative tile deviations and signed report differences remain valid. Apply
   metric units/axes/meaning/precision from registry and explicit corrections.

3. **Native scope.** Byte transfer completeness and native parse completeness
   are separate. Matching a partial transfer's hash does not prove complete
   native data. Preserve complete prefix/valid siblings plus partial scope,
   raw unsupported sections and native locators. No guessed recovery at an `@`
   quality character. A damaged bounded BAM record may preserve later intact
   framed siblings; an unbounded/truncated record cannot invent their positions.
   BGZF missing EOF qualifies completeness without discarding intact records.
   No HTML graph reconstruction, archive extraction, reference fetch or process
   invocation. A BAI cannot create read/quality counts.

4. **Locator coordinates.** `byte_start/byte_end`, when provided, are zero-based
   half-open offsets in the logical decompressed native stream. For ZIP they
   are within the exact named member. Gzip/BGZF offsets refer to concatenated
   decoded native bytes, not physical remote ranges or BAM virtual offsets.
   Null offsets are allowed where row/field locators suffice. Sequence/base
   bins preserve closed one-based native positions; SAM POS is converted to
   zero-based position_0, with absent coordinate null. Original lexical values
   remain in bytes/labels, not converted into invented coordinates.

5. **Semantic selector matching.** Match exact caller document_id, section_key,
   section_ordinal, metric, row ordinal/all, and exact axis/all. Axis equality
   includes all kind/label/lower/upper fields. A scalar summary has row_ordinal
   null; `rows=all` may select it, while `rows=ordinal` cannot. Exact record
   selectors match only an actual existing ID of the selected family. More
   than one match for one_target is ambiguous; do not use an arbitrary match.
   Slot absence and actual records with missing values remain distinct.

6. **Population ordinal stability.** FASTQ and BAM fixed summary populations
   use ordinal0. Hostile populations use their actual native JSON row ordinal;
   repeated report sections use their original section occurrence. FastQC's
   population_key fastqc_module uses a stable module slot: basic_statistics0,
   per_base_quality1, per_tile_quality2, per_sequence_quality3,
   per_base_content4, per_sequence_gc5, per_base_n6, length_distribution7,
   duplication8, overrepresented9, adapter_content10, kmer_content11.
   For repeated same-named sections, ordinal = slot + 12*section_ordinal.
   Absent modules do not shift later module slots. No population is fabricated
   to occupy an absent slot. C-derived verified_read_pairs uses the ordinal of
   the exact PairDeclaration among selected pair declarations; failed earlier
   declarations do not renumber later ones. Both member document IDs remain.

7. **Metadata joins.** Original submitted parameter pointers and recipe
   occurrences define libraries/stages; scheduler/effective substitutions do
   not replace them. Selected evidence matches whole ContentBinding+pointer.
   Values must satisfy their exact selected typed metadata grammar. Bare source
   possession proves neither an association nor execution. Reused input paths,
   colliding sanitized basenames, missing mates and conflicting assertions add
   local requirements. Counts with no stage association remain usable. Source-
   bound pair declarations require actual unique read-key correspondence; no
   join by two sorted lists, equal counts, accession similarity or half-count.

8. **Encoding basis.** Unknown requires encoding unknown and no declaration,
   evidence or native locator. Explicit_source_bound_declaration requires exact
   selected EncodingDeclaration/evidence/metadata_id, encoding phred33 or
   phred64, and null native_locator. Native_bam_phred requires bam_phred and
   native locator, all supplied declaration fields null. Native_sam_phred
   requires phred33 and native locator, no declaration. FastQC inference never
   silently fills either explicit or native-alignment basis. Every quality
   component/projection retains its exact basis; missing native QUAL remains
   missing even when encoding is format-specified.

9. **Lineage basis.** Native_report or observed_record_correspondence references
   an actual saved NativeLineage record; it does not identify a task stage by
   filename. Explicit_source_bound_declaration has the exact selected
   LineageDeclaration and its evidence; native_lineage_ref is null. It may
   support retention with successor_population/subset_population, or consistency
   with same_population. The resolved declaration targets must equal that
   job's exact before/after populations. Unknown basis cannot yield an available
   comparison. Multiple contradictory matching declarations remain conflicting;
   do not choose the most convenient. Assumption never sets observed_state to
   completed and never supplies execution or scientific credit.

10. **Arithmetic inputs.** Complete compatible actual counts are required for
    whole-population ratios. Known partial counts remain partial, never scaled
    up. Zero denominators yield null undefined fractions; valid zero numerators
    remain zero. Invalid symbols invalidate composition fractions that depend
    on a valid DNA alphabet, while length/count measurements survive. The
    declared Phred model computes expected errors, not observed sequencing
    mistakes. Do not exponentiate FastQC's mean quality as a substitute for
    the actual quality histogram. Retention after>before is incompatible,
    not clamped; signed report difference remains signed. No report-native
    rounded percent becomes an exact count denominator.

11. **Projection and save/read.** Fields repeat their exact immutable selection.
    One-target missing envelopes have null record_ref/payload; exact_rows never
    invent rows and retains excess matches. Exact zero requires an actually
    available complete selection, not missing source. available_value requires
    available payload/number; typed_state may accept honest absent/partial
    values, not invalid or ambiguous target selection. A complete empty module
    differs from one absent in this artifact. Preserve requirement records and
    typed requested statuses even if the parent's chosen return is satisfied.
    Requested_status names a real non-status field. No cyclical status queries.

12. **Saved validation.** Validate separate sheet/components content bindings,
    original task, adapter ID/version/implementation pin, original selector,
    requested field selection, all component population/operand links,
    assumptions, generic/native failure codec equality and exact projection.
    Keep the original projection_failure_context, not a guessed set difference.
    Do not reconstruct records by parsing bytes or recalculate values during
    admission/read. Historical admitted facts keep named original publications;
    latest failed/partial own publication supersedes older own success. No
    extra model call, runtime episode action or synthetic observation.
