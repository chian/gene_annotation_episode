# Compare selected reference positions in a retained alignment

`sequence.sites` reads one explicitly selected alignment observation. Supply
`alignment_ref` and exactly one of `positions` (a nonempty list of zero-based
reference coordinates) or `window` (`start` inclusive, `end` exclusive). The
reference positions belong to that observation's bound reference operand.
Duplicate positions remain in the requested row order; numerical site counts
use each selected reference position once.

This operation runs as a supplied-data reader in the existing scientific child.
It does not launch an aligner or select among alignments. Supported retained
results are local/global Biopython protein, DNA and RNA pairwise alignments,
the actual sequence-alignment result of native phmmer, and one minimap2 PAF
placement from the selected map-ont, map-pb, map-hifi, lr:hq, map-iclr or sr
mode. The original operation's resource, version, settings and complete output
remain its provenance. No API or HPC aligner execution is provided by this read.

The host supplies the exact original result and operand identities. Minimap2
needs its selected PAF row, actual original query and reference sequences and,
when available, the selected read member's original quality characters and
declared quality encoding. Repeated read titles do not identify a read member.
The numerical reader validates native names, lengths, complete geometry and
the original symbols against the native normalized traceback. Native N=N
does not establish equality between different original ambiguous symbols.

The retained numerical sheet separates identical and substituted paired
positions, query gaps, reference skips, positions outside the alignment and
unavailable correspondence. A skip is neither a deletion nor an alignment
column. Query intervals on reverse mappings keep ascending original bounds;
query strand and reference-facing symbols remain separate. Biopython's native
U-to-T normalization is explicit; it cannot restore an original RNA U from its
retained normalized traceback. phmmer sequence coordinates are not a physical
mapping for generic HMM profile consensus.

Consecutive query insertion columns form one event at the boundary between
reference positions. An event is selected once when either adjacent reference
position is requested. Its full query interval is retained, including leading
or trailing insertions adjacent to the selected positions. Original ancestry,
when supplied, preserves ordered segments, strand, repeated segments and split
codons. Missing ancestry leaves local correspondence usable and original
intervals unavailable; the query side of a gap or skip has an empty original
interval list with a not-applicable status.

The separate deterministic calculator reports counts and ratios with explicit
numerators and denominators. Paired identity divides identical positions by
paired positions. Selected alignment identity also includes query-gap columns
and selected insertion symbols in its denominator. Reference aligned/paired
fractions use the unique requested reference positions; query/reference paired
coverage uses the complete corresponding operand length. These are different
populations. Unknown full-request components remain null, with observed subset
counts separate. A validated no-alignment result has zero paired positions;
zero-denominator identity remains null.

Quality characters use original query indices, including reverse mappings.
phred33 subtracts 33; phred64 and solexa64 subtract 64, with separate Phred and
Solexa log-odds scales. Unspecified encoding preserves characters with null
numerical quality. Raw MAPQ 255 remains 255 and has unavailable usable MAPQ;
MAPQ 0 remains a measured zero. No quality-to-function-confidence conversion is
performed. Native alignment scores remain whole-alignment measurements and
are not apportioned to selected sites.

Complete rows and native inputs are retained even when a result preview shows
only 12 rows. Saved sheets can be recalculated without file access, network
access, native execution or a model. One selected read retains one comparison
observation; parsing, calculation and projection create no extra observations.
These measurements describe correspondence, not an annotation or biological
acceptance decision. A separately selected BLAST HSP column read uses its own
alignment-column population and its existing read-only result contract.
