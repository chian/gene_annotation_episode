# C-L204-MSA: native XMFA boundary evidence

This is an additive proposal for root acceptance, not a completed MSA capability.
Only this new verification directory was written. The authoritative attachment,
permanent decisions, production modules and fixed progress rows are unchanged.
No scientific aligner, service task, HPC job or episode was run. This task does
not implement the separate GenomeAlignment application.

## Sources and what was actually established

`SOURCE_RECEIPTS.json` contains the original URLs, pinned revisions, retained
paths, byte counts and SHA-256 values. The source files and authentic upstream
format examples remain byte-for-byte copies. The examples are upstream fixtures;
this review did not witness their original native execution or establish a
BV-BRC task association.

* The [Mauve format guide](https://darlinglab.org/mauve/user-guide/files.html)
  defines independently delimited collinear subalignments and the GUI dialect's
  singleton and zero-coordinate representations.
* The [input guide](https://darlinglab.org/mauve/user-guide/aligning.html) and
  [progressiveMauve invocation guide](https://darlinglab.org/mauve/user-guide/progressivemauve.html)
  distinguish one multi-FASTA input from several genome files.
* Native `koadman/libMems` revision
  `1f067601ae48f898dc3c9b92a3b7bf636d04fc70`, complete
  `IntervalList.h`, establishes the actual `WriteStandardAlignment` syntax;
  complete `LoadMFASequences`, `LoadSequences` and `LoadAndCreateRawSequences`
  functions in `MatchList.h` establish loading choices.
* Complete `koadman/mauveAligner` revision
  `3e8293836119a8a6cc883b48f234947cf55387c5`,
  `src/progressiveMauve.cpp`, traces arguments through loading, backbone
  processing and `WriteStandardAlignment`. This source is evidence of its own
  behavior, not the deployed BV-BRC executable version.
* `biopython/biopython` revision
  `2fbe8755bb44731e60b7bd1e2cc55cf34d94e15b` provides
  `Tests/Mauve/combined.xmfa`, `separate.xmfa`, original source FASTAs and the
  test file with original generating-command comments. The retained current
  `Bio/Align/mauve.py` and `Bio/AlignIO/MauveIO.py` were read completely.
* The previously retained complete BV-BRC `App-MSA.pl` at p3_msa revision
  `d359353ff8ac9cbfa63dad8ad33135835b969f52` and complete
  `MSA_Sequence_Alignment.pm` were read. The latter's segment branch excludes
  progressiveMauve. The complete p3_mauve `xmfa-parser.js` and its
  `mauve-parser.js`, `p3-mauve.js`, `utils.js` and `App-GenomeAlignment.pl`
  callers were also read at `fb37db96bef0dd7c87c5274b95a43d2b9078b505`.

The retained Java parser and tests are supplemental source copies, not a
claimed complete Java-code review. A missing historical Biopython test path
returned HTTP 404 and remains recorded in the receipts. Technical documentation
was used; literature searches and literature graders were outside this task.

## Exact native coordinate facts

The native writer emits `#FormatVersion Mauve1` and one-based member numbers.
For a nonempty component with native left coordinate `s` and ungapped length
`n`, the writer emits `s-(s+n-1)`. Coordinates are positive and increasing for
both strands; strand is a separate `+` or `-`. Its minus component is displayed
in alignment orientation, requiring reverse complementation to compare to the
forward source interval. `Bio.Align.mauve` independently uses `start-1,end`
and reverses coordinate traversal for minus components.

For a valid residue at zero-based block column `c`, let `k(c)` be the count of
non-dash characters strictly before `c` in that record's complete aligned text:

* plus: forward source position is `s-1+k(c)`;
* minus: forward source position is `e-1-k(c)`;
* dash: no residue position;
* interval: `[s-1,e)` for either strand, length `e-s+1`.

The first and last residues of a minus record map to `e-1` and `s-1`.
No source-length subtraction is part of this conversion. In particular, these
are not MAF minus-strand start coordinates. The displayed symbol is already
oriented for comparing columns; complement it only when comparing to the
forward source. Non-gap count must equal the native interval span before a
whole row can supply a trusted map. A gapped column index is never added
directly to a source coordinate.

`0-0` means that this member contributes no source sequence in that block. It
is not `[0,0)` at the start of a chromosome, not a residue at position zero, and
not evidence of a deleted whole genome. A zero record can contain an empty
sequence in the documented format or an all-dash row in actual retained output.
Only the latter supplies observed dash characters. An omitted member in a
terminated block and an explicit zero record are different native records with
the same lack of source-coordinate contribution. Neither becomes a fabricated
alignment row. Positive-coordinate empty/all-dash rows are incompatible.

`=` terminates one block. Blank lines do not. A final `=` without a final
newline is complete syntax. EOF inside an unterminated block is partial syntax;
retain its readable rows and qualify the missing delimiter. Block order is file
order, not coordinate order. A nucleotide can occur in a later singleton block;
not appearing in a multi-member block is not the same as being absent from the
file. The file's block number is not the header's member number.

The native C++ reader has historical accommodations for reversed minus
endpoints. The inspected writer does not emit them. The proposed strict Mauve1
reader will preserve such tokens and report an unsupported/incompatible record;
it will not silently swap endpoints. Supporting an additional historical
dialect requires a separate declared format contract and authentic examples.

## Member numbers, source entries and actual input identity

The member number `N` joins to metadata keys `SequenceNFile`,
`SequenceNEntry` when present, and `SequenceNFormat`. It is not the ordinal of
the current block's row. Comments after the strand are retained text; in native
Mauve output they commonly repeat a source filename. They are not reliable
sequence identifiers. Metadata lines must remain ordered with duplicates;
neither a map that silently overwrites conflicts nor independently sorted arrays
preserves the necessary association.

The native one-file loader takes each source-file sequence entry separately.
Its writer repeats the same File token and writes Entry indices beginning at
one. The native multiple-file loader takes one concatenated sequence per input
file. Coordinates then belong to that file's concatenation, not directly to a
contig. Recovering a contig requires the exact original file's ordered entries,
lengths and content. A path basename, genome name or freshly retrieved genome
cannot establish the original offset map. Mixed, absent or conflicting header
metadata remains unresolved unless explicit run-backed input evidence supplies
the missing relationship.

For App-MSA the actual inspected command is one staged `input.fasta`, so native
members refer to its entries. The wrapper prepends a supplied reference where
applicable, generates random labels for other entries, may remove gaps or
translate, and can retain only the first contig for ordinary genome inputs.
The original member and genomic coordinate map is therefore a separate supplied
transformation chain. Duplicate IDs can overwrite the wrapper's rename map.
Even successful native-member mapping does not prove original genome coverage.

## Blocks, duplicates and first-block FASTA

The documented Mauve GUI representation expects each source nucleotide once,
including singleton blocks for unaligned intervals. This is a property to
check against complete supplied sources, not a completeness flag inferred from
the `.xmfa` suffix. General XMFA content may omit source intervals or repeat
them. Retain every record and detect overlapping placements. Distinguish:

1. distinct coordinates with the same sequence text (possible sequence repeats);
2. the same native-member coordinate represented twice (overlapping placement);
3. repeated member records within a block (ambiguous block membership);
4. duplicated source entries or original IDs (dependent input occurrences).

A repeated record does not create another biological member or independent
measurement. Coverage uses coordinate unions, with multiplicity/overlap reported
separately. Inverse coordinate lookup returns every matching placement. Native
LCB membership expresses the aligner's correspondence hypothesis, not a
confirmed function, structural variant, orthology assignment or calibrated
annotation probability. Singleton blocks must not be counted as multi-member
LCBs. XMFA block boundaries are retained; concatenating all blocks creates a
different representation requiring an explicit transformation and population.

App-MSA's conversion stops at the first `=`. It substitutes headers from the
staged FASTA in encounter order and never checks XMFA member numbers. SNP
tables and FastTree in that branch use this first-block projection. XMFA is
uploaded without ID restoration; AFA and certain converted files are restored.
The full staged `input.fasta` and occurrence map are not among the specified
upload suffixes. The task stdout's rename lines alone do not prove full sequence
custody or resolve repeated original IDs. The `.xmfa` and `.afa` associations
must remain separate. AFA reference positions are offsets in its first final
aligned row, even if that row came from a minus native interval.

The standalone BV-BRC JS reader is not a lossless scientific reader. Its
`lcb_idx` field is the native member number. It drops an intermediate `0-0`
record while treating the final record differently, treats blank lines as block
endings, and does not finalize an unterminated no-newline EOF. Its caller normally
deletes sequence strings and reduces paths to basenames. Its optional gap
extractor does not close a trailing gap run. The retained native script was
executed only as a parser: combined.xmfa block 0 returned members 1 and 3,
omitting the actual explicit zero-member 2. This lossy JSON is not a substitute
for the complete native XMFA. It belongs to the separate GenomeAlignment
producer path; no claim is made that App-MSA itself calls that JS path.

## Worked retained examples and independent checks

`inspect_native_examples.py` is a fixture-specific offline arithmetic check,
not an implemented production parser. It retained every per-column position
and native source span in `NATIVE_ARITHMETIC.json`. Biopython 1.88 independently
read the full fixtures; the unmodified BV-BRC JS reader was also exercised.
No aligner or service was launched.

`combined.xmfa` has six terminated blocks. Its 50-, 41- and 49-base source
entries map to native members 1=`equCab1`, 2=`mm9`, 3=`canFam2` by original
Entry numbers, not labels in the XMFA comments. Block 0 has 49 columns:

| Native member | Interval/strand | Nongap bases | Observed dash characters | Full-file represented union | Multi-member-block union | Cooccupied-column union |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `2-49 -` | 48 | 1 | 50/50 | 48/50 | 46/50 |
| 2 | `0-0 +` | 0 | 49 | 41/41 | 0/41 | 0/41 |
| 3 | `2-48 +` | 47 | 2 | 49/49 | 47/49 | 46/49 |

Here cooccupied means the selected member and at least one other selected
member both have non-gap residues at that block column. Member 2's 41 bases
occur only in block 3. All 140 input bases appear somewhere in the complete
file, but only 95 appear in a multi-member block and only 92 participate in
cooccupied columns. These different denominators answer different questions.

For the selected pair (1,3), block 0 has 39 canonical identities, 7 canonical
substitutions, 1 member-1-only gap and 2 member-3-only gaps. Comparable canonical
columns are 46; identity is `39/46 = 0.8478260869565217`. A whole-genome percent
identity is not supplied by this fraction. Sample zero-based maps are:

| Block column | Member 1 forward source position | Member 3 forward source position |
| ---: | ---: | ---: |
| 0 | 48 | 1 |
| 8 | 40 | 9 |
| 9 | 39 | null, gap |
| 10 | 38 | null, gap |
| 11 | 37 | 10 |
| 27 | 21 | 26 |
| 28 | null, gap | 27 |
| 29 | 20 | 28 |
| 48 | 1 | 47 |

`separate.xmfa` has two blocks, with different member order:
1=`equCab1.fa`, 2=`canFam2.fa`, 3=`mm9.fa`. Its first block has 52 columns;
member 3 contributes minus interval `1-19`, then plus interval `20-41` in a
22-column singleton. Its represented coverage is 41/41, multi-member-block
coverage 19/41, and cooccupied coverage 18/41. Different runs/input modes are
not merged despite containing the same source strings.

`simple.xmfa` supplies five complete blocks and a larger minus-strand interval;
all positive spans match nongap counts. Its `unknown.fa` metadata does not
itself bind to the neighboring `simple.fa`; that source association is left
unresolved in the arithmetic report. `simple_short.xmfa` is an authentic
upstream **abbreviated, coordinate-inconsistent counterexample**. Its first
positive record declares 552 bases but contains 159; another declares 601 but
contains 180. Later records contain 23 versus declared 47, and 46 versus
declared 48. Its last block lacks `=`. Biopython's coordinate-aware reader
raises `AssertionError`; an upstream parser accepting its rectangular text
would not establish valid coordinates. Never use it as a source of scientific
span measurements or guess missing bases from its headers.

Remaining work is implementation of the accepted proposal, native/synthetic
failure verification, provider acceptance/binding and actual original task/input
custody. Deployed progressiveMauve version, successful App-MSA execution and
complete episode communication are still unverified.
