# AFA/A2M parser handoff

This packet records isolated implementation under root interface 001 and additive
clarifications 002. It does not amend the user's supplied goal or mark a tool,
resource, episode path or scientific calculation complete.

## Authored files and exact ports

- gene_annotation_episode/hmmer_alignment_input_types.py supplies the frozen
  NativeAlignmentLine, iter_native_alignment_lines(content: bytes) and
  alignment_input_diagnostic(...) APIs. It imports only standard-library types.
- gene_annotation_episode/hmmer_alignment_input_fasta.py supplies exactly
  decode_native_fasta_alignment(content: bytes, *, declared_format: str,
  alphabet: str) -> dict for afa and a2m.
- tests/test_hmmer_alignment_input_fasta.py contains 29 authored test functions,
  including parameterized cases. The root-selected test selector is that entire
  file. HANDOFF.json lists individual selectors, source anchors and file hashes.

The decoder accepts already-retained bytes and an explicit actual alphabet. It
returns the frozen DecoderBatch. It has no path I/O, acquisition, process or
model calls, Store access, provenance claims, scoring, weights, checksum or MAP
implementation. Existing Stockholm/Pfam parsing, numerical authorities, producer
profiles, observations, optional historical context, prompts, progress files and
literature paths are unchanged by this owner.

## Decoding and evidence preserved

Events retain consumed physical lines, including LF/CRLF terminators, reversible
UTF-8/surrogateescape text and original byte positions. Byte, physical-column and
aligned spans are zero-based half-open; lines are one-based. Duplicate names keep
separate row ordinals. Names and descriptions follow native space/tab/NUL token
behavior, without applying Unicode whitespace or letter classification.

AFA ignores leading C whitespace and internal literal spaces, rejects internal
tabs/control bytes, retains ordinary lexical alphabet aliases and converts an
accepted sequence NUL to X (amino) or N (DNA/RNA) with a source-located
symbol_alias. Empty and unequal rows remain failures. Accepted partial source
prefixes remain available with invalid geometry/symbol flags as appropriate.

A2M validates consensus counts before expanding format-defined insertion slots.
It retains surviving letter case, ignores native space/tab/dot/uppercase-O syntax,
generates left-justified insert slots and derived RF, and records every generated
gap with null source coordinates. Blank source lines and ignored bytes remain
source segments on complete expansions. A failed or unestablished expansion has
no aligned row/segment coordinates; its consumed Events and unconsumed trailing
range preserve the bytes.

Lowercase o, sequence NUL, and actual out-of-allocation zero-consensus insertion
accesses remain source-semantics-unestablished. The latter check tracks the last
first-row this_nins allocation instead of treating every zero-consensus mismatch
as unsafe. Defined mismatches still return source-equivalent status 7.
Non-ASCII bytes reached by native C character-classification calls also remain
unestablished; an internal AFA high byte after a safe ASCII prefix has the
digitizer's defined invalid-sequence status 7. Header names/descriptions only
passed through native token copying remain reversible bytes.

Native status equivalence is a source-derived fact, not a process returncode.
Zero-column A2M can have native status-equivalent 0 while geometry remains invalid.
Empty/initial-blank-only files produce no fabricated alignment occurrence.

## Examples encoded in tests, not test results

The two original cmemit files are read unchanged from packet 250. Their original
returncode-0 receipts establish emission provenance, not new input conformance:

| Input | Source-derived expected decoding |
| --- | --- |
| Native aligned_a2m/emitted.out | 3 rows, 12 columns, RF xxxxxxxxxxxx |
| Native a2m_insertions/emitted.out | 5 rows; 12 consensus columns; insert maxima at boundaries 2, 5, 8, 11 of 1, 1, 2, 1; 17 expanded columns; RF xx.xxx.xxx..xxx.x |
| Authored leading/trailing insertion input | 3 rows, 8 columns; rows aaACgTt-, c-A--Cgg, --A--T--; RF ..xx.x.. |
| Authored unequal AFA rows AC and A | status-equivalent 7; no row padding |
| Authored A2M lowercase-o input | no aligned geometry; explicit source-semantics diagnostic |

Correction to packet 534's descriptive wording: the authentic retained
a2m_insertions bytes contain internal inserts only. Leading/trailing insert
coverage here is deliberately authored test input, not an authentic emission.
Historical artifacts, receipts and packet 534 are preserved unchanged.

Packet 534 cases covered by the authored tests: N02 (native expansion and
generated/source mappings), N03 (AFA grammar), N04 (A2M counts/O/o), N13 (byte
line endings, control bytes, reversible names and classified non-ASCII paths),
and N14 (one failed whole-file alignment plus exact consumed/unconsumed bytes).
Closed-shape, argument-misuse and NUL/unsafe-source clarification cases accompany
those semantic checks.

## Actual validation and remaining work

Only source/artifact inspection and standard-library AST parsing were performed
by this owner. The three Python files parse as Python ASTs. No application module
was imported, no pytest test was run, and no compiler/native program or job was
launched by this owner.

Root owns bounded test/native conformance under 20 GiB RAM, 4 GiB scratch,
zero swap and no invented wall budget; saved-sheet adapter and validation;
existing shared digitization/checksum/calculator consumption; driver/publication
integration; selected typed returns and replay. Source inspection and this
parser handoff do not establish any of those completions.

OWNED.diff is the complete new-file diff for the two implementation modules and
the test module. HANDOFF.json records the exact inspected source and original
artifact identities without copying or regenerating their contents.
