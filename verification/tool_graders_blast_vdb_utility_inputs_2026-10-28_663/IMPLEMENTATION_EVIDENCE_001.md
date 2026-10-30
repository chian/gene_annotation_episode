# VDB utility parser implementation boundary 663

The original supplied user attachment and explicit directions remain authoritative. This records parser interfaces, not a goal, runtime prompt or scope change. Owned files are blast_vdb_utility_inputs.py, test_blast_vdb_utility_inputs_663.py and this evidence directory.

## Internal diagnostics payload (frozen before coding)

parse_blast_vdb_diagnostics returns a closed internal object with exactly: version=blast_vdb_utility_diagnostics_v1, occurrence (common ArtifactOccurrence), original_outcome (common NativeOutcome), input_identity={sha256,size_bytes}, native_bytes_hex (all original stderr bytes), native_text (exact UTF-8 text or null), diagnostics, checks, failures.

Each nonblank diagnostic line has exactly occurrence_id, line_number (one based), byte_start (inclusive), byte_end (exclusive, includes its original line ending), native_line (UTF-8 text without CR/LF or null on invalid encoding), category and native_prefix. Categories are bioseq_not_found, sequence_data_absent, empty_bioseq, iterator_error, retrieval_failed and unknown. Known literal messages come only from retained 620 native source. Native prefixes are retained verbatim; unfamiliar prefixes also remain qualified by native_diagnostic_unrecognized, without claiming fixture verification of their grammar. No identifier, selector, membership or count is inferred from diagnostics. Known skip/failure messages cause selection_incomplete even at native return code zero. Unknown content causes native_diagnostic_unrecognized. The shared outcome/capture helper supplies distinct execution and closure failures on the final common result.

Saved normalization reconstructs these diagnostics from native_bytes_hex and requires exact equality, original occurrence custody and the same original outcome. This payload is consumed only by these parsers/normalizer. Final results have the common SequenceExtraction v2 or DatabaseInspection v3 shapes and explicit stdout/stderr occurrences. Native bytes remain accessible through their supplied artifact occurrence; provenance references do not grant file access.

## Sources and consumers inspected

Read the complete 643/001-003 ports, lexical655 module and 001/002 ports, classic extraction and inspection modules, retained620 blast_vdb_cmd source/help, current shared contracts, current result worker and result views. Existing worker dispatch and selector/result views still need the root-owned VDB integration; parser-only work does not establish publication or requested returns. Existing legacy scientific VDB parser remains unchanged and is never supplied fabricated extraction/search context.

## Numerical and identity meanings

The shared655 lexical reader supplies native rows and native integer lengths. The core662 public normalize_blast_utility_sequence_symbols supplies the only sequence normalization/count authority. Native %l means returned sequence extent. Missing or conflicting native length makes the usable returned count null with a located reason; DNA-invalid symbols (including U under the existing declared-DNA rule) retain their original text and a null usable count. No OID, title, coordinates, dataset, read, spot or sample is inferred. Exact selector values retain every original selector occurrence. Explicit supplied row mappings cannot contradict exact matches. All enumeration rows have association not_applicable.

Information fields retain native integer lexemes and reported averages rather than recomputing averages. Duplicate values are retained; conflicts are qualified. Paths retain original section/row order and repeated paths, the native Blats spelling, explicit empty sections and missing sections. Dependency links use only the existing supplied DATABASE_DEPENDENCY_SCHEMA and literal path equality.

## Verification plan and limits

Use bounded529 check123_vdb_parsers663 with explicit check005/dependencies reuse, 20 GiB RAM, 4 GiB scratch, zero swap and no wall cap. Native extraction fixture is original661 stdout (594 bytes, SHA256 3be1e1b841530c2818893eb9a396ca8dcd5257203b4778bdda93719fdc47110c), plus its empty stderr. It contains two observed 250-base rows, already compared independently against the658 companion. No native operation is rerun. Info/path/edge cases are source-derived controlled examples only. Original661 postprocessing failed; saved-only121b verification passed. Offline resource closure, production binding, native info/paths, all/reference/filter/WGS/alias native modes and requested episode delivery remain unverified. Parser work adds no inventory completion count.
