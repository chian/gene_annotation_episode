# Proposed shared decoding interface for root review

This is a proposed implementation boundary, not implemented API. It fixes one set of row/annotation/coordinate operands feeding the existing B1 numerical authority. Root owns acceptance of these ports before fresh coding. There is no additional scientific sheet or map implementation. No production API has been changed by packet 534.

## Ownership and signatures

Use one new shared pure input module, not driver-local copies. The following filenames are proposed separate ownership units; they do not yet exist as a result of this packet.

| Owner/file | Exact proposed functions | Required outputs before dependent work |
|---|---|---|
| Shared schema/adapter owner: `hmmer_alignment_input.py` | `read_hmmer_alignment_input(content: bytes, *, declared_format: str, occurrence: dict, explicit_alphabet: str | None, engine_version: str) -> dict`; `effective_hmmer_alignment_alphabet(alignment: dict, *, settings: dict) -> dict` | Closed DecoderBatch validation, occurrence-keyed B1 adapter, optional saved input-decoding facts, legacy absence behavior |
| Alphabet owner: `hmmer_alignment_input_alphabet.py` | `infer_hmmer_alignment_alphabet(content: bytes, *, declared_format: str) -> dict`; `classify_easel_alphabet_counts(counts: list[int]) -> dict` | AlphabetProbe shape below; byte scanner/checkpoint/whole-file behavior and exact classifier; no row parser or weights |
| FASTA owner: `hmmer_alignment_input_fasta.py` | `decode_native_fasta_alignment(content: bytes, *, declared_format: str, alphabet: str) -> dict` | DecoderBatch for only `afa` and `a2m`, with native expansion and derived RF |
| Block owner: `hmmer_alignment_input_blocks.py` | `decode_native_block_alignment(content: bytes, *, declared_format: str, alphabet: str) -> dict` | DecoderBatch for only `psiblast`, `selex`, `clustal`, `clustallike`; distinct native state machines, not one permissive block parser |
| PHYLIP owner: `hmmer_alignment_input_phylip.py` | `decode_native_phylip_alignment(content: bytes, *, declared_format: str, alphabet: str) -> dict` | DecoderBatch for only `phylip`, `phylips`, multiple-record/lookahead semantics and declared-vs-observed widths |
| Root integration owner | Existing data/calculation/driver/worker/view/publication ports | Adapter and infer helper outputs above; no parser owner edits these files or GSC/BLOSUM/PB math |

All functions are deterministic and side-effect free: no application Store, filesystem, installed-program lookup, process, network, model, scheduler, observations, or credit. `content` is the already-retained byte payload. Type/contract misuse raises ValueError with a closed argument-error code; malformed scientific content returns structured partial/invalid data and diagnostics. Helpers must not silently switch formats or alphabets. `explicit_alphabet` is `amino`, `DNA`, `RNA`, or None. Low-level decoders require one of those actual alphabet values. Non-Stockholm parsers can be implemented/verified independently using explicit alphabets while the inference helper is developed. Inference can be independently added to existing Stockholm/Pfam without waiting for the new format parsers.

The common byte-line helper must expose LF/CRLF-only lines and original offsets; it can live in the shared module with schema types. If that causes an import cycle, put only the closed data types and byte-line primitive in `hmmer_alignment_input_types.py`, owned by the shared-interface owner. Low-level parsers return data and never import the high-level sheet/calculation modules. This specific dependency must be resolved before parallel files are assigned.

## Low-level DecoderBatch: exact proposed shape

The format parser returns the following JSON-compatible dictionary (not an alternative scoring sheet):

```
{
  "version": "hmmer_native_alignment_decoding_v1",
  "format": <declared lower-case format>,
  "alphabet": "amino" | "DNA" | "RNA",
  "records": [DecodedAlignment, ...],
  "diagnostics": [Diagnostic, ...],
  "end_state": "eof" | "parse_error" | "source_semantics_unestablished",
  "next_byte_offset": int,
  "trailing_range": {"byte_start": int, "byte_end": int} | null
}
```

`next_byte_offset` is the first unread byte according to the parser after the last returned record/error. It is not bytes actually consumed by a native process. `trailing_range` preserves undecoded bytes when an error/unestablished source corner stops decoding; null means none. No fixed record/line/sample limit is permitted. Whole-file formats return at most one alignment; Stockholm/Pfam and PHYLIP variants can return sequential records. A malformed later record remains a distinct partial occurrence and does not alter a complete earlier record. No parser invents successful scientific data for a source corner whose native interpretation is unestablished.

```
DecodedAlignment = {
  "record_ordinal": int,
  "reader_state": "complete" | "partial" | "invalid" | "source_semantics_unestablished",
  "native_status_equivalent": 0 | 3 | 7 | null,
  "byte_start": int, "byte_end": int,
  "line_start": int, "line_end": int,
  "header_valid": bool,
  "column_count": int | null,
  "declared_row_count": int | null,
  "declared_column_count": int | null,
  "block_count": int | null,
  "rows": [DecodedRow, ...],
  "column_annotations": {tag: Annotation, ...},
  "events": [Event, ...],
  "diagnostics": [Diagnostic, ...]
}
DecodedRow = {
  "row_ordinal": int,
  "name": str,
  "name_bytes_hex": str,
  "description": str | null,
  "aligned_sequence": str | null,
  "segments": [Segment, ...],
  "annotation_fragments": [Event, ...],
  "column_annotations": {tag: Annotation, ...},
  "geometry_valid": bool,
  "symbols_valid": bool,
  "identity_unambiguous": bool,
  "diagnostics": [Diagnostic, ...]
}
Annotation = {
  "text": str,
  "valid": bool,
  "basis": "native_input" | "native_format_derivation",
  "fragments": [Event, ...]
}
Event = {
  "event_ordinal": int,
  "kind": "header" | "dimensions" | "sequence" | "annotation" |
          "consensus" | "blank" | "comment" | "invalid",
  "block_index": int | null,
  "row_ordinal": int | null,
  "tag": str | null,
  "raw": str,
  "value": str | null,
  "locator": {"line": int, "byte_start": int, "byte_end": int}
}
Segment = {
  "event_ordinal": int | null,
  "byte_start": int | null, "byte_end": int | null,
  "column_start": int | null, "column_end": int | null,
  "aligned_start": int, "aligned_end": int,
  "operation": "copy" | "symbol_alias" | "ignore" | "native_gap",
  "basis": "input_symbol" | "input_ignored" | "a2m_insert_slot" |
           "selex_physical_columns",
  "source_text": str,
  "decoded_text": str
}
Diagnostic = {
  "code": <closed parser-specific error code>,
  "record_ordinal": int | null,
  "row_ordinal": int | null,
  "event_ordinal": int | null,
  "byte_start": int | null, "byte_end": int | null,
  "details": {
    "expected_count": int | null, "observed_count": int | null,
    "expected_bytes_hex": str | null, "observed_bytes_hex": str | null,
    "annotation_tag": "RF" | "MM" | "CS" | "SS" | "SA" | null,
    "native_corner": "a2m_lowercase_o" | "selex_first_data_missing" |
                     "phylip_nonpositive_dimensions" | "phylip_overwidth_lookahead" |
                     "phylips_last_row_eof" | "nonascii_ctype" | null
  }
}
```

The closed diagnostic codes proposed for the common owner to freeze are `invalid_header`, `missing_name`, `invalid_name_byte`, `invalid_sequence_byte`, `row_count_mismatch`, `row_order_mismatch`, `column_count_mismatch`, `block_geometry_mismatch`, `annotation_order_mismatch`, `annotation_cardinality_mismatch`, `missing_consensus_line`, `a2m_consensus_count_mismatch`, `psiblast_case_conflict`, `phylip_dimension_invalid`, `native_source_semantics_unestablished`. Unused detail fields are null; byte fields are even-length lower-case hexadecimal for original byte tokens, never prose. Counts are exact observed/required native quantities; negative values are allowed only for an original signed PHYLIP dimension or the native -1 missing-data position. Native-corner labels are restricted to the enumerated source discrepancies. These are parser facts carried inside existing `native_issues`; they are not unrestricted prose or new outer grading failures.

`native_status_equivalent` is the status implied by the inspected source on a defined path, not an observed process status. Use null for an unestablished/unsafe source corner; preserve the actual captured process returncode only in the original bundle. The 0/3/7/null enum covers deterministic in-memory format-content outcomes, not every Easel allocation/I/O/exception status. All eight digital reader paths translate esl_abc_dsqcat[_noalloc] eslEINVAL into eslEFORMAT: AFA line 232, A2M 296, PSI-BLAST 265, SELEX 689, Clustal/Clustal-like 270, PHYLIP 447 and PHYLIPS 576. PHYLIP invalid-name helper eslEINVAL is likewise translated to eslEFORMAT at its reader call. Therefore sequence-byte eslEINVAL is not a separate returned format status here. Alphabet-open refusal (26) belongs to the separate probe/open result; a low-level decoder always receives an established alphabet. Do not map resource exceptions, programming misuse, or undefined native behavior to 7; those remain outside this content-status claim. `reader_state=complete` requires complete deterministic parsing and usable row geometry, independently of an observed returncode 0. PHYLIPS short-last-row/EOF may have status-equivalent 0 with invalid geometry; do not pretend the native source rejects it, and do not supply padded arrays. AFA/A2M/PHYLIPS have no row-aligned block count: use null rather than inventing a block measurement. PSI/SELEX/Clustal/PHYLIP interleaved record actual parsed block counts. Null native quantities remain missing in existing projection.

All byte/aligned/physical-column spans are zero-based half-open. Line numbers are one-based. Event.locator.byte_start is the first byte of its physical line, and Event.locator.byte_end includes that line's original LF or both CRLF bytes when present; Event.raw includes the same terminator bytes under the reversible text encoding. An unterminated final line ends at len(content). Segment byte/physical-column spans refer only to the actual payload bytes (no line terminator), and sequence physical columns exclude the terminator. This retains whole physical lines exactly while keeping sequence-coordinate spans independent of newline width. Numerical model/alignment coordinates remain the existing one-based inclusive convention. `raw` and name/description/source text use reversible UTF-8 with surrogateescape; the hex name is the exact native name bytes after format name transformation (PHYLIP trim/internal-space conversion), while the original header/name bytes remain in Events. The parser must not use decoded text character length for byte offsets.

`aligned_sequence` is the native coordinate-expanded row, preserving surviving source letter case and using '-' for format-created gaps, '~' for PHYLIP '?', and '-' for nucleic PHYLIP uppercase O. Ordinary alphabet aliases already handled by existing digitization (e.g. nucleic X/I/T/U and ._) can remain lexical characters; format-specific aliases must be resolved because existing residue-coordinate consumers count letters. Every ignored span has a zero-width aligned span; every generated gap has null source offsets and an explicit format basis. Copy/alias spans account for source symbols; non-ignore decoded spans concatenate exactly to aligned_sequence. No segment mapping may invent a source byte for a generated gap.

A2M-derived RF and PSI-derived RF use `basis=native_format_derivation`. Clustal consensus is an Event, never RF. SELEX RF/MM/CS become existing RF/MM/SS_cons column annotations, and SS/SA remain per-row annotations. The byte origin and native tag are retained. Default weights in these formats are not newly measured WT annotations: the adapter records missing weights; the existing `--wgiven` native-default branch alone supplies unit weights when all WT annotations are absent.

Row IDs are ordinal. Duplicate display names, PHYLIP truncation collisions, and empty rectified PHYLIP names remain distinct row occurrences. `identity_unambiguous` means the parser has an exact positional row/annotation join. It does not mean a display label is globally unique. A malformed later block cannot merge or shift rows by name.

## AlphabetProbe and effective alphabet

`classify_easel_alphabet_counts` accepts exactly 26 nonnegative integers ordered A–Z and returns `{ "alphabet": Alphabet | null, "status": "determined" | "undetermined", "rule": Rule }`, using the exact classifier in SOURCE_MAP. Closed Rule values: `short_sample`, `all_n_dna`, `aa_only_letter`, `dna_canonical_fraction`, `rna_canonical_fraction`, `amino_diversity`, `undetermined`. This helper only classifies a histogram; it does not sample rows or choose work.

`infer_hmmer_alignment_alphabet` returns:

```
{
  "version": "hmmer_native_alignment_alphabet_probe_v1",
  "format": <declared lower-case format>,
  "state": "determined" | "undetermined" | "source_semantics_unestablished",
  "alphabet": "amino" | "DNA" | "RNA" | null,
  "counts_az": [26 nonnegative integers],
  "counted_letters": int,
  "checkpoints": [
    {"threshold": 500 | 5000 | 50000 | null,
     "at_eof": bool, "line": int | null, "byte_end": int,
     "counts_az": [26 nonnegative integers],
     "state": "determined" | "undetermined", "alphabet": Alphabet | null,
     "rule": Rule}
  ],
  "scan_end_byte": int,
  "stopped_at": "checkpoint" | "eof" | "unestablished_byte_semantics",
  "diagnostics": [Diagnostic, ...]
}
```

Counts are cumulative, `counted_letters=sum(counts_az)`, and final counts equal the last attempted classifier input when a determined/undetermined result is returned. EOF can have zero letters and a null line. A scan may inspect more bytes than the last checkpoint on the way to EOF; keep the actual scan extent and raw source occurrence. Whole-line strict-threshold behavior, one checkpoint per line, first success, and EOF fallback must be validated. This is sufficient saved evidence to revalidate the classifier without reading an artifact or installed source. Histograms and source positions do not become new scientific numerical components.

`read_hmmer_alignment_input` validates exact eight-field occurrence identity (`occurrence_id`, `direction`, `role`, `ordinal`, `artifact_ref`, `sha256`, `size_bytes`, `completeness`) against content before decoding. If an explicit alphabet was selected, it records `basis=explicit_flag`, no probe. Otherwise it computes one probe from the entire original byte source according to native scanner semantics; unknown is not replaced with a chosen alphabet. A refused native open can retain raw events/diagnostics but supplies no successful digital MSA record. It must not run a low-level decoder under an arbitrary placeholder alphabet.

High-level return is exactly:

```
{
  "version": "hmmer_alignment_input_result_v1",
  "input_decoding": InputDecoding,
  "records": [<existing B1 kind=alignment record>, ...],
  "population": <existing B1 population native row>,
  "issues": [<existing B1 issue object>, ...]
}
InputDecoding = {
  "version": "hmmer_alignment_input_decoding_v1",
  "reader_profile": "infernal_1_1_5_easel_alignment_input_v1",
  "source_occurrence_id": str,
  "source_sha256": str,
  "format": <declared lower-case format>,
  "alphabet_basis": "explicit_flag" | "native_source_inference",
  "explicit_alphabet": Alphabet | null,
  "effective_alphabet": Alphabet | null,
  "alphabet_probe": AlphabetProbe | null,
  "reader_state": "complete" | "partial" | "invalid" | "unavailable",
  "first_record_end_byte": int | null,
  "file_end_state": "eof" | "parse_error" | "source_semantics_unestablished" | "alphabet_undetermined"
}
```

The high-level adapter saves `input_decoding` as an optional property of each newly decoded B1 alignment record; source identity/format must agree. Where no successful alignment record exists, the source-level diagnostic and existing population row retain unknown/failed decoding; the original artifact always retains the bytes. The source opening/inference may be saved as a structured issue detail for that no-record case, without adding a tenth sheet field or changing population row's closed fields. Low-level declared-vs-observed dimensions/segments/native-status facts are retained in an optional record `native_input` property with the DecoderBatch record's fields; scientific rows remain the existing B1 row format.

`effective_hmmer_alignment_alphabet` returns exactly `{ "state": "present" | "missing" | "incompatible", "alphabet": Alphabet | null, "basis": "explicit_flag" | "native_source_inference" | null, "issue_code": null | "alphabet_missing" | "alphabet_undetermined" | "input_decoding_invalid" }`. Explicit settings and saved facts must agree; disagreement is incompatible, not precedence-based silent replacement. Without `input_decoding`, preserve legacy explicit-only semantics. Never infer from aligned rows, recompute a probe from event previews, read disk, or backfill saved history.

## Adapter to the existing B1 record and calculator

The common owner retains existing top-level nine sheet fields, existing operation/settings, all occurrence identities, existing requested-interval/mapping/summary rows, and existing numerical output shapes. It materializes each new alignment with:

- `record_key = occurrence_id + '#alignment/' + ordinal`, `kind='alignment'`, `occurrence_id`, `format`, `alignment_index`, `engine_version`, complete/header/width/block facts, row/column annotations, original events, native issues, B1 issues, and byte/line locator.
- Each row: existing `record_key=alignment_key+'/sequence/'+row_ordinal`, positional row index/occurrence, `name`, `aligned_sequence`, row locator, fragments, annotation_fragments, geometry/symbol/identity flags, row column_annotations, `sequence_annotations=[]`, `sequence_annotations_joined=True`, native_issues and issues. Add source `segments`, name byte identity, and description as optional decoding detail.
- `weight={"value":null,"state":"missing","events":[]}` for the eight formats. Do not fabricate GS WT events. Existing all-missing default and selected numerical weighting remain authoritative.
- Every annotation object remains compatible with `annotation(record,tag)` (`text`, `valid`, `fragments`), with additional explicit provenance only. Preserve original non-Stockholm event tags; do not fabricate Stockholm source lines to make `gf_value()` work.
- Headerless SELEX/PSI `header_valid=True` means their required initial structure parsed; it does not claim a physical header existed. Whole-file formats get `complete=True` only after their full grammar successfully ends. Native geometry anomalies remain invalid; no silent row extension.

Current `_alignment_records` unconditionally adds duplicate_sequence_name, and `reconstruct_alimask_model_map` treats it as invalid. The new adapter must not apply that name-only rule to positional native formats. Preserve Stockholm's existing conservative annotation-join behavior and historical saved issues. A new valid positional source may still have an ambiguous Stockholm output; that output's failed correspondence stays explicit rather than being silently merged. This difference needs a targeted integration test, especially for genuine cmemit PHYLIP label collisions.

Existing consumers requiring review at integration:

1. `valid_alignment` / `_saved_sheet_shape`: optional new context shape plus record-to-occurrence and geometry consistency. No requirement that old records carry it. Do not let `native_status_equivalent=0` override missing rows/width.
2. `reconstruct_alimask_model_map`: use effective alphabet in the fast branch; retain hand behavior and all new GSC/BLOSUM/PB implementations. Return reason for undetermined new probe without changing historical absent-probe results.
3. `_coordinate_correspondence`: use the same effective alphabet and native-coordinate row strings; lexical PHYLIP O must already be gap. Existing numeric residue positions and aliases remain one implementation.
4. `_build` / build associations / checksum: explicit-or-inferred source alphabet is a qualification; actual output HMM alphabet/MAP/checksum remain native evidence. Use existing `stockholm_digital_checksum`, never a format-specific checksum or model map.
5. Source symbol counts/masks/output correspondence: they must count the decoded native aligned rows, not ignored source syntax. Raw symbols remain in events/segments for audit; do not reinterpret historical raw-row counts.
6. `_alimask_preflight_shared`: use the same population/first record and reconstruction APIs. It cannot import a second simplified reader. Only ali2model uses map safety. Source inference can inspect suffix independently of first-record parse safety.
7. `grade_hmmer_preparation` and `recalculate_hmmer_preparation`: initial read saves decoding facts; saved recalculation reads only the sheet. No new envelope metadata needed for parser algorithm facts.
8. `_Saved._context`, `_map_context`, `_embedded_records`, `allowed`, and projection quantities: unchanged selected record/occurrence relationships, optional decoding validation only. No extra model-facing unstructured findings.
9. `qualified_occurrences`, result worker `_grade`, publication custody checks: same exact staged/final/source hashes and immutable numerical artifacts; no re-acquisition or automatic historical upgrade.
10. `Native...Results.facts`, `_complete`, `credit_view`, `completion`; returns `_validate_historical`, `_received`, `validate_received_report`: retain practical completion and one acquired bundle unit. Parsing, inferred alphabet, generated columns and extra quantities earn no extra observation/credit.

## Context/source-profile compatibility

Current `ALIMASK_PROFILE` is an exact five-source dictionary, and both `alimask_map_context_shape` and `alimask_map_context_valid` depend on it. `resolve_alimask_map_context` creates that context from the authenticated original executable digest. Do not append parser sources to this existing object, change its name, change the resolver's output for the same old bundle, or loosen it to a current-registry union.

The new `reader_profile` identifies a deterministic decoding algorithm. Its independently versioned source manifest is the 15-source evidence index in this packet; it is not a claim that a newly observed executable was used. Original producer custody remains in the bundle/map context. If a future implementation needs an explicit extended producer/parser profile, add a new immutable profile identity and preserve lookup/validation of the old identity; select by saved identity, not by what the newest registry currently contains. No need exists to replace the five-source context merely to store the alphabet probe.

`native_hmmer_preparation_result_publication.py:validate_prepared_grading` deliberately calls `effective_metadata(..., include_map_context=...in saved metadata)`. Preserve this behavior. Historical absent contexts remain absent. Existing saved contexts compare equal to their original five-source shape. New optional `input_decoding` stays in new sheets, not in envelope metadata regenerated by this path; consequently merely installing a decoder cannot change a historical publication's effective_metadata digest.

Compatibility cases must include present old five-source context, historically absent context, explicit-alphabet old sheets without input_decoding, no-alphabet old sheets whose map was unavailable, sealed publication/restart, and a registry with an additional unrelated parser profile. Old numerical artifacts, selected returns, acquired credit and completion observations must remain identical. There is no history rewrite/migration step.
