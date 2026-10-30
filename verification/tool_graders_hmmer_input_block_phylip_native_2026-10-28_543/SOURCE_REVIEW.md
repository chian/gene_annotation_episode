# Native source and verification review

Original native files are under `resources/software/infernal-1.1.5/easel/`.
Their exact retained source/header/archive hashes are inherited unchanged from
packet 539 `SOURCE_PINS.json`, itself pinned in this packet's `CASES.json`.
The following complete relevant function bodies were read before case authoring:

| File | Functions and anchors |
|---|---|
| esl_msafile_psiblast.c | SetInmap 38; GuessAlphabet 85; Read 184–294 |
| esl_msafile_clustal.c | SetInmap 44; GuessAlphabet 87; Read 188–304 |
| esl_msafile_selex.c | SetInmap 98–118; Read 234–272; block Create 342–382, Grow 385–412, Destroy 415–427; ErrorInBlock 441–448; read_block 473–524; first_block 536–600; other_block 609–640; append_block 643–731 |
| esl_msafile_phylip.c | SetInmap 84–118; Read 248–296; interleaved Read 414–486; sequential Read 547–606; rectify_input_name 1081–1095 |
| esl_mem.c | strtoi32 112–164; memtok 526–537; memspn 551–556; memstrcmp 582–594 |
| esl_msafile.c | GetLine 1207–1227; PutLine 1256–1265 |
| esl_alphabet.c | RNA/DNA/amino constructors 176–294; dsqcat 923–942; dsqcat_noalloc 961–991 |
| esl_msa.c | SetSeqName 1147–1155; complete esl_msa_Checksum body |

Also read in full: packet 539's `input_observer.c` and Python fixture/helper
module; both new production decoders and their complete pure test files; packet
534 SHARED_INTERFACE/SOURCE_MAP/VERIFICATION_CASES; packet 536 ROOT_INTERFACE_001
and ROOT_INTERFACE_002; packet 540 HANDOFF/AUTHORED_NATIVE_CASES/FIXTURE_INDEX;
packet 541 HANDOFF/EVIDENCE. The shared `_normalize`, `_alphabet`, alphabet
constants and `stockholm_digital_checksum` were inspected without importing
application code. Selected unchanged upstream fixtures were inspected as bytes.

Important observation boundaries:

- Native PSI and Clustal derive row framing before digital validation. PSI RF
  depends on source case. Name copying can retain NUL internally while string
  consumers see only the prefix; later full-token comparison can reject it.
- SELEX validates block line order, computes physical lpos/rpos, appends native
  gaps and literal annotations, and rewinds errors to content end. The observer
  reports the error line but not the reset byte offset. Annotations copied
  before a later row failure survive only in the Python partial record returned
  here; native error output supplies no partial MSA.
- Strict PHYLIP uses ten-byte names and base-0 prefix parsing. Invalid integer
  tokens return at lines 267–269 before allocation at 273. No accepted huge or
  nonpositive dimensions are selected for execution.
- PHYLIP overwidth at EOF rejects, but a nonblank lookahead can bypass that
  equality check. Its selected single-row overwidth example is fully initialized
  and safe to display, while its declared geometry remains invalid.
- PHYLIPS lines 587–598 permit a short final row at EOF and set alen to its
  length. The selected 4/2-row-length example permits safe prefix-only observer
  and checksum access. Longer final rows are not passed to this observer.
- `print_msa` and `esl_msa_Checksum` both loop through native msa->alen. The
  observer's `print_hex` stops at NUL. Neither exposes a whole record sequence
  length independent of msa->alen, an annotation's position-indexed NUL suffix,
  a byte cursor, or any second record.

No modified native source, substitute scientific calculator, repeated producer
execution or completed integration is hidden in this review. The new suite
compares only native facts actually emitted by the existing observer.
