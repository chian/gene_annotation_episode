# Additive native-source clarifications

This preserves 001 and packet 534. These are precise input-port corrections
from complete native source examination, not a goal or scope change.

## Integer conversion and empty scanner behavior

`esl_abc_GuessAlphabet` takes int64 counts but narrows the counts in
`EFIJLOPQZ`, `ACG` and `DHKMRSVWY` to C int. Do not represent unrestricted
Python arithmetic as proven native behavior beyond that defined source domain.
The classifier retains all normal branches and now also permits
`status=source_semantics_unestablished`, `alphabet=null`, and
`rule=native_count_range_unestablished`. Use this result when any narrowed count
exceeds 2147483647, or the total exceeds 9223372036854775807. It is an explicit
native integer-semantics limitation, not a resource or sample cap. Do not guess
wraparound behavior. N/T/U/X/B counts are not in the narrowing loops.

AlphabetProbe checkpoint state also permits source_semantics_unestablished;
`stopped_at` additionally permits `unestablished_count_semantics`. Retain actual
raw-letter counts and the inspected byte extent, and emit the existing
native_source_semantics_unestablished diagnostic. Expected/actual identify the
integer bound and observed count. Classifier results are not native observations.

The non-PHYLIP guess scanners use C int nres; an unresolved whole-line scan whose
total exceeds 2147483647 therefore also has unestablished native count semantics,
even if every narrowed count fits. PHYLIP uses int64 nres. Preserve those source
domains separately from the standalone classifier's input domain. This does not
introduce an arbitrary prefix limit or a default alphabet.

Entirely blank Clustal/Clustal-like/PHYLIP/PHYLIPS input exits its native header
scan before classification: checkpoints=[], zero histogram, undetermined, eof.
Other formats retain their actual EOF classification attempt. The amino-diversity
branch remains in source order even though earlier aa-only precedence makes its
15-distinct-letter threshold unreachable for ordinary nonnegative counts; tests
must not fabricate an input that falsely claims to reach it.

## NUL and partial A2M geometry

Native esl_memtok/esl_memspn use strchr on the delimiter string. A source NUL
therefore matches its terminator even for the literal space/tab delimiter set.
The C isspace calls do not treat NUL as whitespace. Preserve that distinction in
the relevant scanner and header operations; do not use a blanket whitespace rule.

AFA SetInmap maps sequence NUL to the alphabet's unknown residue. Store a
symbol_alias from the exact source byte to X for amino, N for DNA/RNA. A2M's
digital map likewise accepts it, but its structural csflag loop never counts it.
This is an additional unestablished structural/digital corner, like lowercase o.
Emit native_source_semantics_unestablished with actual=a2m_nul, token_hex=00 and
native_status_equivalent=null; do not invent a stable native aligned row.

When failed or unestablished A2M expansion has no valid aligned coordinates,
retain aligned_sequence=null, segments=[], geometry_valid=false. Original
consumed header/sequence/blank Events remain lossless, and trailing_range retains
the exact unconsumed bytes. Do not put raw offsets into aligned coordinate fields
or generate gaps to make a failed alignment rectangular. Complete validated
expansions retain the normal source/ignore/native-gap segment contract.

## Empty native input has no alignment occurrence

For both empty and initial-blank-only AFA/A2M input, native returns EOF with no
MSA. DecoderBatch therefore uses records=[], end_state=eof,
next_byte_offset=len(content), trailing_range=null. A top-level empty_alignment
diagnostic identifies byte_start=0, byte_end=len(content), actual=0. Do not
invent a one-line or invalid alignment record merely to hold blank Events.
The original retained artifact preserves those bytes. The adapter receives an
empty decoded population rather than a false failed alignment occurrence.

For A2M first-row zero-consensus source corners, distinguish actual invalid
array access from a defined consensus mismatch. The first row can allocate and
initialize extra this_nins slots from its raw line length; a later insert into
those defined slots still reaches the ordinary EFORMAT row-end mismatch.
Only a later structural access outside the allocated/initialized slots has
unestablished native semantics. No such unsafe case is executed as an oracle.

## C character classification in row readers

Use the same source-domain distinction as the alphabet scanner. A first
non-space high byte passed to native isspace, and any A2M structural high byte
passed to isupper/islower, have unestablished signed-char/locale semantics here.
Retain a native_source_semantics_unestablished diagnostic with
actual=nonascii_ctype and no claimed native status. An AFA internal high byte
after a safe ASCII non-space prefix reaches the digital validator and can
retain the defined invalid_sequence_byte/status7 outcome. Names/descriptions
handled only as byte tokens remain reversible source data; no Unicode ctype
behavior is substituted.

## Block reader source-specific cursor and name behavior

SELEX selex_ErrorInBlock resets the native buffer to the offending line's
content_end, before its LF/CRLF terminator. For this case next_byte_offset is
that reset cursor, not the later read extent. Original inspected Events retain
their full byte spans, including any block lookahead; record.byte_end records
the maximum inspected Event extent. trailing_range starts at the reset cursor
and may overlap already inspected Events. Do not discard facts or report a
false native cursor merely to make the intervals disjoint.

SELEX missing-data lpos/rpos arithmetic follows the source literally, including
rightmost name/tag extent. A first missing-data line that forms an unsafe
line-1 pointer, and negative-ntext copy/consistency paths, remain unavailable
source semantics rather than fabricated gaps or a claimed ordinary status7.
An ordinary non-first missing-data row can still receive defined native gaps.
Repeated MM annotations overwrite the same interval: the last one in the block
supplies its value; retain all original fragments and tags.

PSI/Clustal name tokenization can include NUL. SetSeqName copies the complete
token, while native string consumers see the prefix before the first NUL.
Store that visible prefix in name/name_bytes_hex, possibly empty, with the
complete source token still in the original Event. Subsequent esl_memstrcmp
compares the full new token length and contents against that stored C-string
prefix: a repeated NUL-containing token therefore fails, while an otherwise
matching plain prefix can succeed. This is defined source behavior, not a
reason to invent name uniqueness or reject every such first-block name.

## Block annotation bytes and native array bounds

SELEX annotation text retains the entire copied byte span, including NUL, in
reversible text. The native observer's C-string display is not authority to
truncate position-indexed stored bytes. Geometry uses encoded byte length.
The existing character-indexed consumers do not yet establish interpretation
of surviving NUL or non-ASCII annotation bytes. Preserve that annotation with
valid=false and the existing native_source_semantics_unestablished diagnostic,
actual=annotation_byte_interpretation, and its exact byte/token. Safely decoded
rows can retain native_status_equivalent=0. A completely overwritten MM value
does not invalidate the later surviving value; retain every original fragment.
Commit annotations in native append order so a subsequent sequence failure
does not erase already parsed annotation data.

For PSI/Clustal extra rows in later blocks, distinguish a still-allocated null
name from an access beyond the native growable row array. The former reaches
the defined comparison failure/status7. The latter has unavailable source
semantics: actual=block_row_storage_overrun, native status null. Do not execute
that undefined-access corner as a native oracle.

## Retained A2M fixture correction

The retained a2m_insertions emission has internal insertions only. Packet 534's
description of that fixture as also covering leading/trailing insertions was
incorrect. Preserve the fixture unchanged and retain its actual five rows,
17 columns and RF xx.xxx.xxx..xxx.x. Separate explicitly authored examples
cover leading/trailing insertions; they are not original native emissions.
