# Remaining HMMER alignment input boundary (packet 534)

This is source investigation for the two remaining R2 input gaps: native alphabet inference and the eight declared non-Stockholm/Pfam formats. It adds no completed tool/mode count. It changes no application, test, progress, goal, or native fixture. The original user attachment remains the goal authority; this document is implementation evidence, not a replacement objective or scope amendment.

The retained native sources are under `resources/software/infernal-1.1.5/`; all native paths below are relative to that root. The exact source hashes, authentic retained native emission receipts, and upstream reader fixtures are in `EVIDENCE_INDEX.json`. No application imports, native commands, compiler, tests, network calls, or jobs were run in this packet. Native behavior below is established from source except where explicitly identified as previously retained output. Source presence is not native conformance verification.

## Existing authority and exact gaps

Preserve `hmmer_alignment_preparation_sheet_v1` -> `calculate_hmmer_alignment_preparation_components` -> `reconstruct_alimask_model_map`. A new format supplies input records to this chain; it does not own weights, fragment marking, consensus thresholds, numerical scoring, credit, or continuation. GSC/BLOSUM/sampled-PB implementations currently being verified by the root are outside this packet's ownership.

The current complete paths inspected are the alignment preparation data/calculation modules; native preparation contracts/driver/worker; result worker grading; saved-view validation and joins; preparation publication validation; result facts/credit/completion; and typed return propagation. Relevant complete existing parser functions were inspected before proposing new code. `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, the tool-grader principles, relevant fixed inventory rows, AGENTS.md, and packet 516's `IMPLEMENTATION_CONTRACT.md` were read. No prompt or message template is proposed here; that work still requires its own TASK/STEERING trace and user feedback.

Current ports:

| Port | Current behavior | Required narrow change |
|---|---|---|
| `native_hmmer_preparation_contracts.py:28`, `FORMAT_ARGUMENTS`, `compile` | Declares Stockholm, Pfam, A2M, PSI-BLAST, SELEX, AFA, Clustal, Clustal-like, PHYLIP, PHYLIPS; compiler always sends explicit `--informat`; default alphabet is absent, not guessed by compiler | Keep exact selected format and flags; no autodetection or invented alphabet flag |
| `hmmer_alignment_preparation_data.py:_alignment_records` | Only Stockholm/Pfam decoded; others have unknown decoded population and `alignment_format_unsupported` | Dispatch new pure format decoders into the existing record/sheet adapter |
| `selected_alphabet(settings)` | Only explicit `--amino/--dna/--rna` | Keep that meaning; add a distinct effective-alphabet reader of saved input-decoding facts |
| `reconstruct_alimask_model_map` | Hand RF returns before alphabet use; fast path needs explicit alphabet | Fast path consumes validated saved inferred alphabet when no flag was selected; weighting/map math unchanged |
| `native_hmmer_preparation_driver.py:_alimask_preflight_shared` | Rejects all non-Stockholm/Pfam formats before splitting modes; invokes reconstruction only for `alignment_to_model` | Dispatch through the same source decoder; retain existing unsafe map/range protection only where needed |
| `native_hmmer_preparation_worker.py:grade_hmmer_preparation`, `recalculate_hmmer_preparation` | First grade parses retained source bytes; saved recalc consumes the sheet alone | Save all inference/decoding operands on the first grade; never reread input or resolve live software on saved recalc |
| Result worker/publication/views/returns | Original byte custody, selected rows and typed factual propagation; no new native acquisition during projection | Preserve this path; optional decoding fields need shape and relationship validation, not new scalar/credit policies |

## Native open/read order and byte grammar

`hmmer/src/alimask.c` main opens a digital MSA file, choosing an alphabet only when a flag is supplied, then calls `esl_msafile_Read` exactly once. It does not read a second MSA. `hmmbuild.c:1029` loops over MSAs; threaded/MPI paths also repeatedly read records. Thus first-record processing is an alimask property, not a common parser truncation rule.

`easel/esl_msafile.c:396` (`msafile_OpenBuffer`) guesses alphabet before installing a format input map and before parsing an MSA. Declared format bypasses format guessing. The compiler passes no extended PHYLIP format data, so declared PHYLIP/PHYLIPS uses name width 10. Relaxed PHYLIP name-width inference is not this execution contract.

`esl_buffer_GetLine:988`, `buffer_countline:1755`, `esl_memnewline:484` use LF or CRLF; a bare CR is data, and an unterminated final line is returned. Do not use Python's general `splitlines()` for new native byte scanners: it also splits bare CR and other control bytes. Native token delimiters are usually exactly space and tab; some loops use C `isspace` for leading/trailing whitespace. For ASCII that adds VT, FF, CR (and LF where present). Column offsets count bytes, not decoded Unicode characters.

Sequences are digitized through `esl_abc_dsqcat[_noalloc]`, which rejects non-ASCII sequence bytes and returns an invalid-character status; the rejected row is not a valid native MSA measurement. Native guess scanners call C `isalpha/toupper` directly on raw `char`; behavior outside ASCII depends on the C environment and is not established by this source pass. Preserve non-ASCII bytes and an unavailable/invalid analysis where needed; do not apply Unicode `isalpha()` and claim equivalence. New name decoding must be lossless and byte-located; UTF-8 plus `surrogateescape` is an exact internal text representation, not permission to change byte-based token/column logic. PHYLIP names have the stricter native graphical-character rules below.

Native status distinctions: `eslOK=0`, `eslEOF=3`, `eslEFORMAT=7`, `eslENOALPHABET=26` (`easel.h`). `esl_msafile_OpenFailure:280` and `ReadFailure:1045` print diagnostics and exit with the status. This packet has not run those failure cases. Partial parser records must retain actual bytes/events/row segments, but a format reader returning an error destroys its in-progress native MSA. Such partial data cannot be promoted to a complete alignment or padded to manufacture a map.

### Common digital alphabet

`esl_alphabet.c:create_rna:176`, `create_dna:222`, `create_amino:267`:

- DNA canonical `ACGT`, ambiguity `RYMKSWHBVDN`; RNA canonical `ACGU` with the same ambiguity symbols. In nucleic input `X -> N`, `I -> A`, and `T/U` are aliases according to chosen alphabet.
- Amino canonical `ACDEFGHIKLMNPQRSTVWY`; extra residue codes `BJZOUX`. B represents N/D, J I/L, Z Q/E, O K, U C; those remain their native residue codes, not an instruction to replace them with canonical letters in checksums.
- Common gap `-`, aliases `.` and `_`; nonresidue `*`; missing `~`. Case is insensitive in digital sequences. Each reader can reject or remap symbols before these defaults apply.
- Keep native residue/gap/missing/nonresidue distinctions. A lexical letter may be a format control (A2M O; nucleic PHYLIP O), and must not be counted as a residue merely because it is alphabetic.

## Per-format grammar, transformations, and termination

### Aligned FASTA (`afa`)

Sources: `esl_msafile_afa.c:SetInmap:40`, `GuessAlphabet:89`, `Read:182`.

Skip initial space/tab blank lines. Leading C whitespace is stripped before checking each header/sequence line. A header begins `>`; its first space/tab-delimited token is the required name, and the remaining bytes are the description. Following sequence lines are concatenated until the next header. Inside a sequence only literal space is ignored by the input map; an internal tab is illegal. Leading tabs have already been stripped. Other symbols follow the common digital alphabet. Empty rows and unequal row lengths fail. One file is one MSA through EOF, including all subsequent FASTA headers. A supposed second alignment is more rows, not an unprocessed suffix. Names and row order follow header occurrences; SetSeqName itself does not require unique names.

### A2M (`a2m`)

Sources: `esl_msafile_a2m.c:SetInmap:61`, `GuessAlphabet:113`, `Read:215`, `a2m_padding_digital:508`.

Headers and sequence-line framing are FASTA-like. The input map ignores space, tab, dot, and O/o; rejects `_`, `*`, `~`; `-` is a consensus gap. The structural pass classifies uppercase letters (except uppercase O) and `-` as consensus positions, lowercase letters as inserted residues. It requires equal consensus counts for all rows. Dots do not declare explicit insertion-column alignment; dotful and dotless input are both reconstructed by the same native expansion.

For each consensus boundary, including leading and trailing boundaries, take the maximum insertion length across rows. Each row's insertion residues are left justified in that slot, and native gaps occupy its remaining width. Then append the next consensus symbol. Native aligned width is `ncons + sum(max_insert_lengths)`; the RF string is `x` at consensus columns and `.` at inserted columns. This expansion is format decoding, not repair of an invalid alignment. Keep the source byte of every actual symbol and explicitly label each gap generated by native expansion. A2M reads the entire file as one MSA and sets default weights. Empty sequence rows have an explicit native allocation case; zero-column alignments still do not meet the existing numerical alignment contract.

Literal source discrepancy: input mapping ignores lowercase `o`, but the structural loop at 286–298 skips only uppercase `O`, counts lowercase `o` as an insert, then asserts structural length equals digitized length. Do not silently choose either intended interpretation. This packet does not establish a stable native result for lowercase-o input. A source-level discrepancy result must not contain invented aligned columns; native conformance evidence is required before claiming support for this corner.

### PSI-BLAST alignment (`psiblast`)

Sources: `esl_msafile_psiblast.c:SetInmap:38`, `GuessAlphabet:85`, `Read:184`.

This is the alignment format, not a PSI-BLAST search output parser. Blank space/tab lines separate blocks. In each sequence line, the first token is the name; the entire remaining tail after stripping trailing C whitespace is the sequence. Sequence starts and final physical byte columns must agree within a block. Internal whitespace and coordinate suffixes are not accepted. Only `-` is a gap; `.`, `_`, `*`, `~`, O and o are explicitly illegal. Other residues follow the chosen alphabet.

First-block row order is authoritative; each later block must reproduce the same name in the same position and have the same number of rows. Blocks append to each corresponding row. Duplicate names are not prohibited by SetSeqName; row ordinal, not a name-keyed dictionary, identifies the row. RF is generated from case: initial `-` for each column, uppercase residue sets `x`, lowercase sets `.`, mixed nongap cases in one column fail; an all-gap column stays `-`. The entire file is one MSA. Malformed later blocks invalidate that MSA, not merely a second record.

### SELEX (`selex`)

Sources: `esl_msafile_selex.c:SetInmap:98`, `GuessAlphabet:140`, `Read:234`, `selex_read_block:473`, `selex_first_block:536`, `selex_append_block:643`.

Blank space/tab lines delimit blocks. Ordinary comments start with `#` in physical column zero and are skipped; `#=` lines are retained. Indented comments are not equivalent. In first-block order, exact recognized prefixes are `#=RF`, `#=MM`, `#=CS`, `#=SS`, `#=SA`; other lines are parsed as sequence rows, even unrecognized `#=` prefixes. RF/CS occur at most once; SS/SA must follow a sequence and occur at most once for that row. The source counts MM but does not enforce a matching one-MM maximum. Later blocks reproduce every retained line's type/order and every sequence row name. RF, MM, consensus structure, and per-row SS/SA must remain their distinct annotations.

Name/tag and following whitespace establish each data start byte. Right edge is the last non-whitespace data byte. A block's alignment width comes from the leftmost data start through rightmost data end. Native gaps fill absent leading/trailing row positions; internal literal spaces also map to gaps; internal tabs are illegal sequence characters. Annotation edges use dots; annotation interiors retain their bytes. Do not strip all row whitespace, token-split the sequence, or align rows by token length. Preserve source physical columns and native expanded alignment positions. Blank sequence data is allowed in a block; it can become native gap columns from the other rows. Blocks with no data append no columns.

Literal source corner: `leftmost` starts from the first retained line's data start even when that start is -1; the later min comparison ignores other -1 starts. Consequently a missing-data first line can affect the computed width differently from a clean mathematical minimum. Preserve this arithmetic in the conformance specification; do not silently repair it. Whole-file, single-MSA semantics apply. Incomplete/bad blocks are not successful partial native MSAs.

### Clustal / Clustal-like (`clustal`, `clustallike`)

Sources: `esl_msafile_clustal.c:SetInmap:44`, `GuessAlphabet:87`, `Read:188`.

First nonblank line supplies the header. Strict Clustal requires first token with prefix `CLUSTAL` and requires the remaining header to contain case-sensitive `alignment`. Clustal-like relaxes the first-token requirement but still requires that substring. A header alone fails. Each sequence row takes name then sequence as space/tab-delimited tokens. Native ignores every later token, not only a numeric coordinate. Sequence-token start byte and length must match within a block. Subsequent blocks must reproduce row names/order/count. Duplicate labels are positional occurrences.

A block is terminated by a line consisting entirely of bytes in ` .:*`; an empty blank line qualifies. A tab-only line does not. After each sequence line the reader requires another line, so EOF directly after the final sequence is an error for missing consensus line. Consensus display is not RF and must not become a hand map. Skip blank lines between blocks, then continue through EOF. A second CLUSTAL header is not a second MSA. Common alphabet symbols apply; input-map whitespace is not ignored inside sequence tokens.

### PHYLIP / PHYLIPS (`phylip`, `phylips`)

Sources: `esl_msafile_phylip.c:SetInmap:84`, `GuessAlphabet:141`, `Read:248`, `phylip_interleaved_Read:414`, `phylip_sequential_Read:547`, `phylip_rectify_input_name:1081`; integer token conversion in `esl_mem_strtoi32:112`.

The header's first two space/tab tokens are sequence count and stated alignment width; remaining tokens are ignored. Conversion is base 0, accepts a minus sign (not a plus sign), supports lowercase `0x` hexadecimal and leading-zero octal, and reports success after a valid numeric prefix even with unused suffix bytes because the reader does not request consumed length. Overflow is an error. Do not replace this with a decimal-only whole-token regex. The reader itself does not explicitly impose positive dimensions before allocation/read; zero/negative-dimension safety behavior is not established here and must not be represented as a successful numerical alignment.

A name occupies exactly ten bytes at each row's first named line. Trim literal spaces at its ends and change internal spaces to `_`; tabs and nongraphical characters in that name are rejected. The native helper permits an empty rectified name, and SetSeqName accepts a non-NULL empty string. Long tokens are not relaxed IDs: bytes after ten belong to the sequence. Names may collide after truncation/rectification; preserve positional row identity. Authentic cmemit PHYLIP fixtures already contain repeated `fixture246` or `tRNA5-samp` labels.

Digital input map ignores spaces, tabs and digits **0 through 8** (the source loop is `sym < '9'`, so digit 9 remains illegal); maps `? -> ~`; explicitly rejects `_` and `~`; accepts common period gap and `*` nonresidue. For DNA/RNA only, uppercase `O -> -`; lowercase o stays illegal. Amino O/o are ordinary amino codes. Text-mode digit handling differs and must not be copied for this digital execution path.

Interleaved PHYLIP: first block has ten-byte names; later blocks consist of unnamed full sequence lines. Each block has exactly nseq rows and equal decoded added lengths. Blank lines are allowed only between blocks. Read until observed width reaches/exceeds stated width or EOF. The lookahead line after the final block is put back when nonblank data remains, so another MSA can follow. If EOF occurs, stated and observed widths must match. Literal source corner: if a lookahead line exists, the final width-equality check is bypassed. Preserve both stated and observed widths and the native return status; do not pretend an overwidth first record with a suffix is rejected by the source.

Sequential PHYLIPS: read each named first line and full continuation lines until its decoded length reaches stated width; skip blank lines after each sequence; then read the next named sequence. The source tests `alen == 0` to decide whether to consume a name, so a first line contributing no symbols changes how the next line is handled. It supports multiple MSAs with lookahead/pushback. Literal source corner: at EOF on the last row, it does not check that row's width against the header and sets `msa->alen` to that final row length. Unequal row arrays can therefore coexist with a native OK return in this malformed case. This is not permission to fill missing symbols or calculate a safe map. Preserve observed rows, declared width and discrepancy; report geometry invalid/unavailable to numerical consumers.

## Native alphabet inference

This is a source-derived deterministic decoder property, not a scientific inference, a model call, a confidence score, or a new scoring sheet. Explicit alphabet bypasses it. One alphabet is chosen for the opened file and used across every subsequent MSA.

Each format scanner counts case-insensitive ASCII letters A–Z from its selected raw byte regions. It checks after a whole data line when cumulative count is strictly greater than the next threshold in `[500, 5000, 50000]`; it attempts at most one checkpoint per line and advances one checkpoint after an unresolved result. First success stops. If no checkpoint succeeds it reads to EOF and tries once more. These are native early checks, not fixed sample limits; do not cap the scan at 50,000, 10,000 rows, the first MSA, or an arbitrary prefix.

| Format | Raw bytes counted by scanner |
|---|---|
| AFA, A2M | Strip leading C whitespace; skip blank or `>` header; count letters in the rest. A2M O/o count here even when its reader ignores them. |
| Stockholm, Pfam | First space/tab token; skip blank or a token starting `#`; count letters in remaining line. No stop at `//`. |
| PSI-BLAST | Skip first space/tab token of each nonblank line; count rest. No comment-line exception. |
| SELEX | Same token skip, but skip token starting `#` (including an indented comment, unlike its parser). |
| Clustal, Clustal-like | Skip first nonblank line without validating header; then skip first token of every line and count rest. |
| PHYLIP, PHYLIPS | Skip first nonblank header, then skip the first ten bytes of every nonblank line before counting, including continuation lines. Do not use declared nseq/width to bound scan. |

Thus later records and malformed suffixes can influence the alphabet for alimask's first MSA. The scanner then rewinds; no suffix bytes become processed scientific alignments merely because they affected guessing. PHYLIP continuation scanning is intentionally not the same as its sequence parser.

Exact classification (`esl_abc_GuessAlphabet:1251`, code takes precedence over its comments):

Let n be total A–Z count. n1/x1 count residues/distinct letters in `EFIJLOPQZ` (including O); n2/x2 in `ACG`; n3/x3 in `DHKMRSVWY`; nn, nt, nu, nx count N,T,U,X; xn,xt,xu are presence bits for N,T,U. Apply the following in order:

1. n <= 10: unknown.
2. n > 2000 and nn == n: DNA.
3. n1 > 0: amino.
4. `n-(n2+nt+nn) <= 0.02*n` and `x2+xt == 4`: DNA.
5. `n-(n2+nu+nn) <= 0.02*n` and `x2+xu == 4`: RNA.
6. `n-(n1+n2+n3+nn+nt+nx) <= 0.02*n`, `n3 > n2`, and `x1+x2+x3+xn+xt >= 15`: amino.
7. Otherwise unknown / `eslENOALPHABET`.

Use the native floating comparison, precedence, counts and scanner checkpoints. Unknown stays unknown; no fallback to amino/DNA, no guessing from a filename, selected function, model annotation, or a small-job transfer. All-N >2000 is a native special case, not a general default.

## Existing analyses and reuse boundary

- `hmmalign_inputs.py:iter_hmmalign_stockholm_records`, its event/fragment/annotation parser, and `stockholm_digital_checksum` are the existing pure shared Stockholm and checksum interfaces. Keep and reuse them; do not build a second Stockholm scientific reader or checksum algorithm. Add raw-byte inference as a separate pre-read pass. Existing Stockholm records/history remain byte-for-byte interpretable as before.
- `phylogeny_formats.py:parse_aligned_fasta` is pure but has different header, whitespace, symbol and empty-alignment semantics. `parse_relaxed_phylip` is a distinct relaxed format and rejects multiple matrices; it cannot stand in for strict ten-byte native PHYLIP. Shared low-level helpers are reusable only where actual byte semantics match.
- `blast_pssm_inputs.py:read_blast_msa_master` / `_clustal_checks` and Biopython Clustal parsing answer a different master-alignment task: stricter coordinate/header handling, duplicate rejection and no Easel alphabet semantics. Do not change its scoring or adopt it as the native decoder.
- `infernal_preparation_emission.py` has writer-specific FASTA/A2M, Clustal and PHYLIP readers. Its compact A2M intentionally leaves inserted columns unavailable; its Clustal and PHYLIP framing differ from Easel input. Preserve that completed work and genuine fixtures. Shared future decoding may be reused only after independent verification of those emission consumers; that work is not required to close this input gap.
- `infernal_preparation_statistics.py:_alignment_records` already reuses the Stockholm helper/checksum and explicitly supports only Stockholm. It is not a hidden general native input decoder.

No already-existing pure helper found in these inspected paths implements the required native inference plus all eight input grammars. The new work is format decoding plus saved inference facts feeding the existing numerical authority, not a new family of scientific graders.

## Mode-specific safety and failures

`mask_alignment` calls no model map or weights. `mask_model` and `model_to_alignment` can run their selected native operation without a reconstructed-map safety decision; reconstruction is useful later to check output. Only `alignment_to_model` requires the existing safety preflight map: alimask scans `model2ali_map` forward without a bound when finding alignment-to-model coordinates. Preserve `map=[]` as an actually empty map (not missing); preserve the `empty_model_map` preflight failure and the `unsafe_alimask_range` failure when requested start exceeds the last match. Never run those undefined-read cases to obtain a supposed oracle. `hmmbuild` uses its actual native HMM MAP output and must not substitute reconstructed alimask maps.

Current driver failure map is retained history:

| Shared result | Existing preflight failure/reason |
|---|---|
| unsupported declared decoder | `unsupported_alimask_model_map/alignment_format_not_established` |
| invalid/malformed alignment | `invalid_alimask_input/malformed_stockholm` |
| no RF for hand | `unsupported_alimask_model_map/rf_required` |
| no explicit alphabet | `unsupported_alimask_model_map/explicit_alphabet_required` |
| incompatible symbols | `unsupported_alimask_model_map/unsupported_alignment_symbols` |
| invalid weights | `unsupported_alimask_model_map/invalid_weights` (some earlier row validation uses `invalid_alimask_input/invalid_weights`) |
| unavailable/invalid PB context | `unsupported_alimask_model_map/map_configuration_unavailable` |
| map empty | `invalid_alimask_input/empty_model_map` |
| start after last match | `unsafe_alimask_range` with integer start/end/last_match |

Future decoder integration should add precise `malformed_alignment` and `alphabet_undetermined` reasons only where the existing preflight actually needs an unavailable input/map result. Retain all old reason values for sealed attempts; don't relabel old Stockholm failures. `PREFLIGHT_REASONS` and `PREFLIGHT_FAILURE_CONTEXT` are the single closed source used by bundle/acquisition validation and must change together. New source-level unresolved/unsafe decoder corners can retain the existing unavailable-map failure plus explicit sheet diagnostic; do not invent a native exit code or a fabricated map. A safely launched native operation's status 7/26 remains the actual native failure, wrapped by the ordinary `nonzero_returncode` execution result. Parser/scientific checks must not become practical completion gates for safe modes.

Removing the broad format gate does not authorize a retry, alternate resource, format conversion, additional native call, or changed CLI options. Native bytes and settings remain the selected job's facts. First-MSA versus suffix parsing needs separate statuses so alimask's valid first record is not rejected because an unprocessed later PHYLIP/Stockholm record is malformed. Whole-file formats have no such successful first-record exception.
