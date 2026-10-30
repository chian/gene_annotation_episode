# Finite follow-on evidence and verification cases

These are required outputs/cases for the implementation owner to schedule within the user's authorized work. None was run by packet 534. They do not increase completion counts, impose a runtime gate, authorize extra work independently, or restart completed GSC/BLOSUM/PB development.

## Available authentic bytes: reuse, do not regenerate

`EVIDENCE_INDEX.json` records hashes and existing returncode-0 cmemit receipts for seven groups under `verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native/`:

| Retained directory | Useful format coverage |
|---|---|
| `aligned_a2m` | FASTA-like A2M, three rows, common consensus width |
| `a2m_insertions` | Five native A2M rows with lower-case inserted residues, leading/trailing inserts and unequal compact lengths |
| `aligned_clustal` | Strict Clustal header, block and native consensus display |
| `clustal_long_interleaved` | Multi-block native Clustal with dots, case and sequence fragments |
| `aligned_phylip` | Native strict PHYLIP, three row-name truncation collisions (`fixture246`) |
| `phylip_interleaved` | Native PHYLIP output from different emitted sequence geometry; directory label is historical, actual bytes determine block count |
| `phylip_long_interleaved` | Multiple blocks, ten-byte name collisions (`tRNA5-samp`), stated alignment width 74 |

Each has original `emitted.out`, request, receipt, stdout/stderr and model source identity. Those prove authentic emission bytes and recorded prior execution, not successful consumption by the not-yet-implemented HMMER input parser. Do not relabel emission receipts as alignment-input conformance. Existing grading files under the same packet's `examples/` retain the earlier emission-reader interpretation; do not rewrite them.

42 retained upstream Easel files are indexed under `resources/software/infernal-1.1.5/easel/esl_msa_testfiles/{a2m,psiblast,selex,clustal,phylip,phylips}`. SELEX has a native upstream manifest of expected good/bad statuses and line errors. These are source fixtures, not this workflow's run receipts. Reuse their originals read-only; a new conformance run gets new receipts and separate outputs. No authenticity claim is made for generated malformed/unit-test bytes; label them authored edge cases.

Existing Stockholm/native MAP fixtures in packets 259/269/267 and completed weighting evidence in packets 524–529 are preserved. The root reported packet 529's 252 distinct passing tests + 34 subtests, 57 native comparisons, three actual weighting execution/return/replay paths and historical absent-context coverage; that statement is a root-provided result, not independently rerun in this packet. New tests should target these input changes and the necessary shared boundary rather than re-produce all completed weight experiments.

## Native conformance and pure decoder cases

| Case | Required comparison or preserved failure |
|---|---|
| N01 | Exact low-level rows, order, native alphabet, RF/MM/SS/SA and widths for one retained/upstream valid input in each of the eight declared formats. Compare against the retained native reader profile, not a generic library's interpretation. |
| N02 | Retained A2M insertion fixture: slot maxima, left alignment of inserts, generated gap coordinates, leading/trailing slots and derived RF; original compact source text remains recoverable. Dotful equivalent is separately labeled authored input. |
| N03 | AFA multiple physical sequence lines; leading vs internal tab; ignored internal spaces; empty row; unequal lengths; second set of headers remains same MSA. |
| N04 | A2M unequal consensus counts; uppercase O ignored; lowercase-o structural/input-map discrepancy remains unavailable until a stable native result is established. No padding of a failed row. |
| N05 | PSI-BLAST ordered blocks; same-position duplicate labels; mixed upper/lower nongap column error; all-gap RF '-'; physical start/end mismatch; forbidden dot/O/coordinate suffix. |
| N06 | SELEX physical-column expansion, blank data rows, internal spaces vs tabs, comments at column zero vs indented, RF/CS/SS/SA order/cardinality, MM multiplicity source corner, first-line missing-data leftmost arithmetic. |
| N07 | Strict vs Clustal-like headers; literal 'alignment' requirement; ignored trailing tokens; exact sequence start/width; reordered row; EOF directly after row vs terminating empty/consensus line; tabs in consensus. |
| N08 | Strict PHYLIP versus relaxed-looking names; exactly ten-byte names, internal-space underscore conversion, blank/truncated/duplicate names; later interleaved blocks have no names. Retained duplicate-label fixtures must not collapse rows. |
| N09 | PHYLIPS continuation lines and a first named line with zero decoded symbols; row/declared-width relationships. Last short row at EOF is retained as invalid geometry even where source return status is OK. Do not run a map over unequal native arrays. |
| N10 | PHYLIP digital 0–8 vs 9; '?' versus '~'; '_' rejection; DNA/RNA uppercase O gap vs lowercase o rejection; amino O/o residues; period gap and '*' nonresidue. |
| N11 | PHYLIP header base-0 numeric prefixes, extra tokens, overflow, positive dimensions; zero/negative dimensions remain source-safety analysis unless a safe bounded reader experiment establishes behavior. No fabricated valid alignment. |
| N12 | Two complete PHYLIP records; valid first plus malformed second; overwidth first with suffix vs EOF check; first-record alimask processing distinguished from hmmbuild all-record processing. |
| N13 | LF, CRLF, final line without LF, bare CR inside data, reversible names, non-ASCII sequence bytes. Do not substitute Unicode whitespace/alpha classifications. |
| N14 | Rejected whole-file suffix leaves partial diagnostic rows and original bytes, not a successful first alignment; rejected later PHYLIP/Stockholm record does not erase a valid earlier alignment. |

A native oracle for N01 must retain actual reader rows/annotations/alphabet/return status and original source bytes. A map-only equality does not establish byte grammar, row identity or coordinate transformation. Instrumentation may expose those native facts, but it must not become a second scientific calculation implementation. Tests for known unsafe native array/map paths use source-established failures and shared preflight behavior; they do not execute undefined reads.

## Alphabet inference cases

| Case | Required exact behavior |
|---|---|
| A01 | n=10 vs 11; unknown remains unknown when no rule applies; explicit alphabet bypasses guessing without adding a probe. |
| A02 | All N at 2000 vs 2001; AA-only set includes O and I; exact code precedence, despite the comment's omitted O. |
| A03 | DNA and RNA all-four requirement and exact 2% boundary; DNA-first precedence when both tests could pass; amino diversity branch threshold and n3>n2. |
| A04 | Whole-line checkpoint counts at 500/501, 5000/5001, 50000/50001; one huge line crosses several thresholds but only one check occurs for that line. |
| A05 | All checkpoints unresolved, later EOF data determines alphabet; no fixed 50,000-letter cap. Preserve cumulative histogram and actual stopping byte. |
| A06 | Stockholm/Pfam first MSA too short or ambiguous, later record or malformed suffix supplies counted letters; guessed alphabet is for first processed MSA. Explicit flag path ignores the guess scanner entirely. |
| A07 | Per-format ignored header/name/comment regions; A2M O/o counted before ignored mapping; SELEX indented comments skipped by scanner despite parser difference; PHYLIP continuation first ten bytes skipped. |
| A08 | A selected no-alphabet flag job that native refuses returns actual status 26 if launched; shared parser returns undetermined evidence. No default alphabet, no invented native stdout, no extra observation. |

The pure classifier can be tested with exact histograms; it cannot by itself verify per-format scanner regions, first-MSA/suffix handling, or native open/read behavior. Keep those as separate comparisons.

## Existing numerical authority and episode/replay cases

| Case | Required output dependencies and checks |
|---|---|
| I01 | For defined explicit-alphabet new-format rows and an independently retained equivalent Stockholm view, feed both through existing B1 calculator; compare weights/MAP/masks/coordinate correspondence/checksum as applicable. The format decoder supplies no second weight/map formula. |
| I02 | Add successful inferred-alphabet cases on the existing Stockholm path and at least one new format; stored probe/classifier and saved effective alphabet agree with native result. Saved recalculation works with source file/installed executable access forbidden. |
| I03 | `mask_alignment` remains runnable without a model-map reconstruction; `mask_model` and `model_to_alignment` do not acquire a new map preflight; native refusal/partial output follows ordinary captured failure paths. |
| I04 | `alignment_to_model` calls the same decoder/saved alphabet/shared reconstruction as grading; retain actual empty-map failure and after-last-match failure. These cases must assert no native command is launched. |
| I05 | An actual new-format local selected job -> durable native attempt/capture -> original grading -> parent-selected quantities/artifacts -> typed child return -> receiving parent. Verify source occurrence, row IDs, aliases, RF and numerical operands survive the complete path. |
| I06 | An actual inferred-alphabet selected job through that same path, with the parent receiving only its requested typed numerical facts/qualifications. No full raw context dump or model-composed restatement. |
| I07 | Actual malformed-input native failure or preflight-unavailable map case -> retained bytes/partial records -> specific typed failure/repair information -> restart/replay without resubmitting native work. |
| I08 | Restart already closed successful I05/I06 paths: saved publications and selected returns unchanged; the inferred alphabet/parser calculation does not create a new acquisition observation, credit unit, or completion event. |
| I09 | Existing five-source map context and historically absent context publications remain readable with new parser registry present; effective_metadata digests and original missing maps remain unchanged. |
| I10 | New optional input_decoding tampering tests: source occurrence/hash mismatch, wrong format, explicit flag disagreement, reordered/negative histogram counts, impossible checkpoints, altered row/segment geometry. Reject the corrupted numerical context without reconstructing facts from current files. |
| I11 | hmmbuild declared-new-format source association checks actual output HMM MAP/alphabet/checksum and first/all-record identities. It never substitutes alimask reconstruction for native HMM MAP. |

I05/I06 are new, narrow episode proofs, not a claim that every resource branch is now complete. No new model-facing message template is designed in this packet. API/HPC/Aurora execution instructions, launch ownership, monitoring/log interpretation and TASK/STEERING information traces retain their separately unfinished status. A parser test, source catalog entry or local fixture does not close those paths.

## Specific prerequisites before coding and before claiming closure

Before parallel parser coding, the root must freeze the shared interface in SHARED_INTERFACE.md: low-level types/byte primitive module (to avoid cycles), exact diagnostic enum/details, source-to-B1 adapter ownership, native-position string semantics, and optional saved facts compatibility. Each parser then needs only that frozen output contract and its exact retained source files/fixtures; it need not wait for another format's implementation or for new weighting work.

Before inference coding, freeze the exact AlphabetProbe schema and classifier rule enum. Its format scanners operate on original bytes and are independent of decoded row output. The integration owner can consume an explicit-alphabet decoder first, then the probe; no missing guess may be represented by an explicit flag inserted into operation.settings.

Before native conformance, select a bounded native reader observation mechanism tied to the retained source/executable profile and specify the exact row/annotation/alphabet fields it records. Preserve the genuine files and receipts; do not regenerate them. Do not invoke any known undefined-read case as an oracle.

Before closure, require actual new-format/inferred-alphabet B1 quantities, driver safety behavior, saved recalculation, selected typed returns and historical publication replay. A successful mapping packet is not completed R2 implementation, and no count increase is permitted for this packet.
