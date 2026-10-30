# Future verification cases; none executed in this mapping

All values below are deliberately specified engineering examples or
source-derived expectations. They are not acquired biological observations or
evidence of a working native/episode binding. Authentic recorded provider/native
examples must additionally be retained, with access/resource status reported
separately. Each case must check the exact returned fields against retained
source facts; no confidence field should be created.

## Coding sequence

1. Selected local CDS over a 12-nt source `AAAATGAAATAA`, segment `[3,12)`,
   forward strand: expected extracted sequence `ATGAAATAA`, length 9. Reuse the
   existing extraction body/sheet; assert support output and requested return
   match it exactly. The numbers describe extraction, not gene correctness.
2. GenBank record with two CDS features sharing the same `gene` qualifier,
   different protein/transcript identifiers and distinct location ordinals:
   retain both when selected, and retain only the exact requested ordinal when
   one is selected. Search IDs and locus arrays must never be reduced to `[0]`.
3. Reverse-strand compound CDS: verify ordered native parts, complement/join
   operator and output mapping against authentic Biopython extraction. Reject
   applying one global reverse complement to a differently ordered compound
   path. This is not established by a forward single-segment example.
4. Fuzzy start, partial end, `codon_start=2`, non-ATG initiation or missing
   terminal stop: retain qualifiers and partialness without claiming an invalid
   protein function. Missing required extraction geometry is unavailable, not
   empty sequence. Remote segment with a missing supplied accession retains a
   specific missing-reference failure and any valid native feature data.
5. ESearch count 20 with five IDs returned: selected candidate page is partial,
   no exhaustive "no other gene" claim. Gene/taxon/accession conflict, empty
   valid page, provider error and malformed XML must remain distinct.
6. Saved GenBank and existing extraction result reproduce the typed output with
   acquisition disabled. Altered source accession, interval, source/feature
   ordinal or output sequence fails association validation.

## Plasmid sequence

1. Search UID `12345`, fetched FASTA/GenBank accession `AB123456.2`: retain both;
   do not call the UID the accession. No hit selection occurs without the
   episode's exact selected result.
2. Addgene page containing separate NGS and depositor records: preserve both
   native locators/labels and explicit selected record; no first-textarea rule.
   Sequence length is actual retained nucleotide count.
3. Numeric ID with explicit NCBI selection stays NCBI; explicit Addgene selection
   stays Addgene. A failed chosen provider does not trigger another provider.
4. Source-asserted circular topology is distinguishable from unknown topology.
   FASTA-only result does not infer circularity or complete plasmid length.
5. Non-200 response, authentication page, valid page with no sequence, malformed
   HTML, invalid alphabet, multiple FASTA records and truncated response are
   separate typed failures/qualifications. Retain native response when present.
6. Restriction/extraction consuming the result must bind its exact selected
   source/sequence/version and length. Saved parse/replay makes no acquisition.

## Shared restriction helpers

1. Source-derived expectation for EcoRI over `AAAAGAATTCTTTT`: length 14;
   recognition `[4,10)`; native one-based cut `[6]`; forward Watson boundary 5;
   Crick boundary 9; native `ovhg=-4`, 4-nt 5' overhang. Verify with a future
   actual native call and show identical fields through both aliases.
2. EcoRI over `AATTCAAAAG`: circular recognition `[9,10),[0,5)`, expected
   canonical native cut `[1]`, Watson boundary 0, Crick boundary 4. The linear
   run lacks this complete recognition site. Keep raw/wrapped coordinates and
   origin crossing distinct.
3. SmaI motif `CCCGGG`: catalog `fst5=3,fst3=-3,ovhg=0`; a flanked source must
   produce equal Watson/Crick boundaries, `blunt`, and the correct recognition
   interval. Do not report cut diagram `CCC^_GGG` as the IUPAC motif.
4. BsaI forward and reverse occurrences with sufficient flanking sequence:
   verify native type-IIS cuts outside recognition interval and correct
   orientation, including circular wraps. Exercise a native two-cut enzyme;
   retain both `pair_index` values even if cuts overlap other events.
5. Explicitly queried enzyme with no sites returns a complete empty event list.
   `CommOnly` non-hit enzymes are still in the searched batch snapshot. Unknown
   enzyme name, ambiguous/invalid input symbols, unknown cut geometry and
   unavailable catalog are not "zero sites".
6. Duplicate numeric cut positions from distinct enzymes/sites retain distinct
   identities. No lossy `{position:enzyme}` join, ordinal renumbering after
   malformed native rows or implied methylation/activity measurement.
7. Linear sites whose opposite-strand cut lies outside the sequence must match
   native `_drop` semantics. Empty/too-short sequence and circular boundary
   normalization need explicit input validation.
8. Both aliases must call one producer/validator and retain one catalog schema.
   Saved native result validation/projection invokes no Biopython search,
   database request or second scoring implementation.

## ARCHS4

1. Retained native rows with values 0 and null: preserve measured zero and
   unavailable value separately. `native_field='median'` does not assign TPM
   unless provider metadata proves the unit/normalization.
2. A retained response has 12 tissue rows and request K=3: retain all 12, return
   exactly three under the declared source/sort order, next offset 3, and no
   "top" ranking unless the order is actually defined. Noninteger DataFrame
   indexes must not change the number of selected rows.
3. Native mean/median/quantile/count fields, if present, retain separate
   meanings, units and aggregation populations. Do not reduce the data to
   median prose or treat tissue aggregates as independent sample replicates.
4. Same symbol in two taxa: requested taxon and returned identity must match or
   be explicitly unresolved. Preserve provider gene namespace/version.
5. Provider total/token absent: total and exhaustion stay unknown. A truncated
   response cannot become complete just because K rows were formatted. Empty
   successful response differs from error, absent gget, malformed data or an
   unsupported native schema.
6. Frozen authentic native payload + verified field map reproduces the typed
   table and requested tissue page without provider access; confirm returned
   measurements equal retained native values, without a scientific score.

## Interspecies mapping

1. Ordered inputs `[A,A,B]`, native relations `A->X`, `A->Y`, `B->Z`: preserve
   three input rows and five input-associated relation rows (X/Y for each A,
   Z for B), with native relation identity shared where appropriate. Do not
   overwrite X with Y or count repeated input genes as independent evidence.
2. A native many-to-many row remains many-to-many; absent orthology-type and
   confidence fields remain `homolog_unspecified`/null. A pair of IDs alone
   cannot become one-to-one orthology or identical function.
3. No-mapping row in a complete selected response differs from a gene absent
   from a partial response, server failure, an unknown species or an invalid
   identifier/version. None produces a successful all-NaN mapping CSV.
4. Human-to-mouse request cannot consume reverse-species records, unrelated
   assembly/release or columns whose names merely resemble requested IDs.
   Validate every row's source and target namespaces/taxa and native ordinal.
5. `fly`/`drosophila` canonicalize only via an explicit supported identity map;
   same-species returns are labeled same-identifier, not cross-species
   orthology. A supplied version suffix is not silently stripped.
6. Empty/failed bounded query results in a typed error/next requirement. A spy
   must prove no unfiltered whole-dataset query, retry or hidden fallback.
7. Both saved BioMart and Ensembl native examples populate the one shared
   relation contract while preserving format-specific native fields. Requested
   returns equal retained selected relation rows; no fresh provider call.

## Enrichment-library list

1. Authentic selected-service library names, native order and provider context
   survive parse/return exactly. A library chosen by the enrichment operation
   resolves to that exact retained catalog record.
2. Same display name under different organisms/releases remains distinct.
   Library name suffixes such as years are not parsed into verified release
   fields without source metadata.
3. Empty complete catalog, partial page, provider failure, absent dependency,
   malformed payload, duplicate name rows and unknown organism are explicitly
   distinguishable. No record count becomes confidence or enrichment strength.
4. Missing provider default cannot be silently filled as human. Native bytes
   are retained even when only a partial list can be projected.
5. Saved catalog projection returns only requested names/IDs/count/page metadata,
   with no enrichment run, acquisition or LLM call.

## GEO series acquisition and matrix projection

1. Engineering bundle has samples GSM1/GSM2 and platform GPL1 feature keys P1/P2.
   Values are `[[0,5],[null,7]]` under explicit sample order `[GSM1,GSM2]`.
   Verify shape `[2,2]`, measured 0, missing null, metadata keyed by GSM and
   exact `(GPL1,ID_REF)` feature order. No sorted-array positional join.
2. Two platforms both contain ID_REF `P1`: retain `(GPL1,P1)` and `(GPL2,P1)`
   separately. Do not pivot them onto one row or infer a shared gene. A feature
   mapping to two genes remains one-to-many.
3. Duplicate `(GSM,GPL,ID_REF,VALUE)` native rows cause a retained conflict or
   long-form output; no first/mean collapse. Different legitimate value
   columns retain units/scale/normalization independently.
4. Non-VALUE measurement column: return acquired source plus exact unavailable
   pivot requirement, allowing the episode to select another column. Do not
   reacquire or declare the acquisition failed. Raw native SOFT metadata lists
   and column descriptions remain available even if CSV writing fails.
5. GSM conditions, channels and biological/technical replicate labels join by
   original sample ID. Missing unit, replicate, normalization and correction
   remain unknown; no TPM/count/log assumptions from VALUE or title.
6. Native GSE lists 10 samples, only seven complete sample blocks are retained:
   partial, with explicit seven IDs/missing three and parse coverage. A page of
   two among seven parsed rows is a display page, not another acquisition or
   evidence of complete original series retrieval.
7. Truncated gzip/SOFT, decompression over budget, oversized native metadata,
   malformed encoding, inaccessible file, hash mismatch, stale file by name,
   read-only output directory and invalid GSE ID have specific results.
   Successfully retained parts remain inspectable. No supplementary file/SRA
   download occurs without a separate selected request.
8. Saved native SOFT plus exact selected sample/platform/column inputs reproduce
   the same bundle/matrix with network disabled. Future actual local/API child
   return binds original selection and received artifacts; paths alone fail.

## Supplied-file inspection

1. Selected 1,000-byte retained text, offset 10, limit 20 returns exactly bytes
   `[10,30)`, bytes_read 20, total 1000, next offset 30. UTF-8 character boundary
   behavior matches existing source_window; no whole-file read for preview.
2. CSV request three rows/two columns: at most requested rows/columns and
   explicit byte limits. File total rows is unknown unless metadata or a
   separately selected bounded count establishes it. Very wide headers and
   huge single cells cannot defeat byte limits.
3. Parquet with many row groups uses bounded batches; only selected columns are
   loaded. H5AD inspection preserves obs/var dimension and metadata identities
   without densifying X or reading every metadata value; handles are closed.
4. Invalid CSV may return an explicitly labeled bounded raw preview. JSON text
   preview is not a validated full JSON parse; malformed/truncated JSON, binary
   data and empty file remain distinct. No format inferred solely from suffix.
5. `.pkl` inspection returns opaque/unsupported metadata and byte preview under
   the selected bounds; a payload that would execute on pickle.load must never
   execute. No application object deserialization.
6. Attempts to use `../`, absolute unselected paths, glob, symlink, directory,
   FIFO, socket or a changed retained digest fail selection/custody validation.
   Tool lists no surrounding directory and reads no unselected file.
7. Compressed input with small compressed size but over-budget expanded content
   stops at the explicit limit and returns qualified partial/unsupported data.
   Header/schema parsing also respects metadata-byte limits.
8. Closed typed return contains only the requested selected-source metadata and
   preview/page references; it does not expose the filesystem path as an
   authorization to access other files or invent scientific measurements.

## Integration cases common to all nine

1. Select real tool information and explicit API/local/HPC resource permitted
   by the original parent assignment; execute in the correct resource child.
   Confirm the selected operation, request, retained native result and requested
   typed return all reference the same original inputs and actual outcome.
2. A resource failure preserves valid partial work and has a specific structured
   reason. Infrastructure does not silently substitute a provider/resource,
   retry, page, cancel or add an investigation step.
3. Both the scientific parent and annotation-root receiving paths consume only
   the admitted fields. Do not leak unrequested child state or source prose as
   unrestricted findings. Preserve complete TASK and concise factual STEERING;
   presentation template work requires its separate current feedback path.
4. Saved replay/reconstruction verifies source identity and returns the same
   originally recorded fields, including partial results. No live acquisition,
   original algorithm rerun, historical rescore or new observation is added.
5. One completed own action remains one local observation. Parsing/projection/
   source capture does not manufacture extra completed actions or credit. No
   fabricated supporting-operation confidence, master score, new continuation
   gate or W05 aggregation is introduced.
