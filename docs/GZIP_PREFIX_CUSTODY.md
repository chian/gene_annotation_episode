# Native gzip output retained before a wrapper failure

Parser `supplied_material_parsing_v5.biopython_<installed version>` preserves
bytes actually emitted by Python's gzip decoder before a later decoding or
trailer error. This extends representation recovery; it makes no biological
quality judgment or acceptance decision.

Previously, the one-MiB buffered `read` could raise on a missing trailer before
returning any available bytes for a smaller file. A generated two-record FASTQ
with only its trailer removed therefore produced zero parsed records, although
native `read1` emitted all 87 decoded bytes before the same EOF error. The new
ordinary parse uses `read1`, captures its actual output, and keeps the error.

The original compressed artifact is unchanged. The decoded-prefix source has
an explicit forward parent reference to that original source. Its request
metadata records decoder/mode, Python version, emitted byte count, whether the
decoder completed and, on failure, its actual exception type/message. These
are native provenance, not model-authored findings. The source is a decoded
prefix when completion is false; it is not described as a verified full file.

Structured parse feedback includes `gzip_decode_incomplete`, emitted-prefix
bytes, exception type, `unparsed_remainder="unknown"` and
`wrapper_integrity="not_established"`. The ordinary native format parser then
retains independently parseable records from that prefix. A missing FASTQ quality
tail remains unparsed; no record or quality symbols are invented. A FASTA tail
can describe a partial observed sequence and does not prove full feature length.
Any returned collection is incomplete when the wrapper failed, even when its
visible prefix happens to contain complete FASTQ records. Native member offsets
refer to the actual decoded source, never to compressed bytes.

A failure before any output preserves an explicitly empty decoded prefix and
the original wrapper, reports failed representation and creates no members.
It does not add a misleading empty-input parser error. A successful wrapper
remains completed with explicit complete decoder metadata. Native sequence
membership, qualities, declarations, parser framing and fixed target ownership
otherwise retain their meanings. In particular, a partial parse cannot expand
an active run's frozen membership when a later representation becomes available.

The parser version change gives this representation a new parse identity. Old
indexes are not silently backfilled, and running investigations retain their
existing executable versions. No new automatic retry, scientific gate, quality
cutoff, credit bonus, episode or continuation rule is added. Parsing evidence
alone earns no scientific credit; a successful partial parse is one completed
ordinary action, rather than one action per emitted read.

Focused local tests use generated native wrappers with missing trailers, a bad
CRC, a truncated concatenated member and malformed headers. They verify exact
original/prefix custody, retained complete read/quality rows, incomplete status,
reopen/reuse, portable provenance and one-action accounting. These are input
recovery checks, not annotation accuracy or a scientific model investigation.

This is not an interrupted-parse checkpoint implementation or a compressed-file
repair utility. It does not recover unreturned decoder bytes, establish the
integrity of a failed wrapper, infer a correct unseen suffix, or certify emitted
sequence as biologically error-free. File-opening/writing failures remain
operational failures. Decoder-read errors retain their emitted prefix and actual
cause. Original custody remains available for later investigation.
