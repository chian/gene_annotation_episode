# Native evidence for MSA and MetaCATS

This is an implementation-boundary proposal, not acceptance or completion.
The original rows are retained in `ORIGINAL_WORK_STATUS_ROWS.json`. Source
presence, scientific grading, installed operation binding, native execution,
and live service verification remain separate claims.

## Exact sources and limits

`SOURCE_RECEIPTS.json` retains URLs, byte counts, SHA-256 and Git blob checks
for eight copied source files and twenty additional original-source downloads.
All twenty downloaded blobs matched the pinned native repository tree.
`DEPENDENCY_SOURCE_RECEIPTS.json` records the actual FastTree invocation helper
and BV-BRC XMFA reader. `READ_IDENTITIES.json` identifies inspected local code.
No live service definition, authenticated task or Workspace output was acquired.

The controlling producer revisions are:

| Application | Original repository/tree | Exact retained producer |
| --- | --- | --- |
| MSA | BV-BRC/p3_msa, d359353ff8ac9cbfa63dad8ad33135835b969f52 | `retained_sources/p3_msa/service-scripts/App-MSA.pl`, `lib/MSA_Sequence_Alignment.pm`, `scripts/snp_analysis.pl` |
| MetaCATS | BV-BRC/bvbrc_metacats, e18a52c5d9514604260fd303419fd0334bdcd477 | `retained_sources/bvbrc_metacats/service-scripts/App-MetaCATS.pl`, `scripts/metadata_parser.pl`, `scripts/Meta-CATS.R` |

These source trees do not establish the deployed service version. Original
packaged `MSA.json` and `MetaCATS.json` were read before their producer paths.
R 4.4.3's original `chisq.test.R` is separately retained to document its default
continuity correction; it does not establish BV-BRC's actual R version.

## MSA invocation and actual branches

The primitive service call remains `AppService.start_app2` with application
`MSA`, exact native parameters and original `start_parameters`. Preparation,
transfer, submission, observation and acquisition remain separately selected
existing API operations. Resource is API/service; no local or HPC deployment
of the complete application was established.

Native inputs include `fasta_files`, `fasta_keyboard_input`, `feature_groups`,
`feature_list`, `select_genomegroup`, and `genome_list`. The producer combines
applicable nonempty fields; the `input_type` label alone does not describe the
effective population. `alphabet` is `dna|protein`; aligners are
`Muscle|Mafft|progressiveMauve`; MAFFT strategies are
`auto|fftns1|fftns2|fftnsi|einsi|linsi|ginsi`. Reference choices are
`none|string|feature_id|genome_id|first`, with `ref_string` when applicable.

| Actual branch | Native behavior and retained distinction |
| --- | --- |
| Ordinary single aligned source | Bypasses the aligner only when a `fasta_files[].type` contains `aligned` and internal `file_count == 1`. `input_status` does not control this branch. |
| Ordinary unaligned/multiple sources | Generates random eight-character member labels, optionally strips `-_.~*`, optionally translates nucleotide input, then runs MUSCLE, MAFFT or progressiveMauve. Original IDs are restored in selected output formats. |
| Segment-aware genome input | Activated by nonempty `genome_selection.selected_segments` and genome group/list input. Other sequence input kinds are rejected. MUSCLE/MAFFT only. Queries `genome_sequence` for `sequence,contig,segment`; aligns each selected locus and writes per-segment outputs. |
| Concatenated selected segments | Adds a combined alignment only when `genome_selection.concat_segments` is true. Loci are sorted in `MSA_Sequence_Alignment`; absent member/locus combinations are gap-padded. Per-segment outputs remain separate. |
| progressiveMauve | Retains full `.xmfa`; the conversion to `.afa` stops at the first `=` and assigns FASTA headers by input order, ignoring XMFA member numbers/coordinates. SNP analysis and FastTree then operate on this projection. This is not complete whole-genome correspondence. |

The source/test contradiction is concrete: the original app definition's
`fasta_files[].type` enum contains only `feature_dna_fasta` and
`feature_protein_fasta`, whereas `tests/reference_aligned.json` selects
`aligned_dna_fasta`. Current pure preparation validates the original enum.
The prealigned mode must stay accounted for as source present but declaration
binding unresolved; do not silently widen the packaged service definition or
pretend that `input_status=aligned` bypasses alignment.

Ordinary genome input uses `get_genome_seqs`, which stops at the second FASTA
header and thus retains only the first contig. Source ID alone does not supply
that contig's identity, full genome coverage or the missing contigs. Ordinary
translation calls `SeedUtils::translate`; its implementation, actual genetic
code and input-to-output codon mapping were not established in this review.
The producer can infer/revise alphabet using an ACTGN fraction threshold of
0.75. Requested and actual alphabets therefore need separate evidence.

The random-label map is keyed by original ID and can overwrite repeated IDs;
restoration is textual replacement, not a retained occurrence-level mapping.
Repeated original IDs or generated collisions need explicit source-backed
mapping or an unresolved join. The contract must not guess by sorted order.

Segment `add_seq` suffixes duplicate IDs within a locus. All retained member IDs
are written at every locus, padding missing loci with `-`. The report's
`sequence_count` is captured before optional gap filtering. Internal
`trim_threshold` and `gap_threshold` are consumed but absent from the inspected
app definition. Actual trim/filter mappings and post-filter populations cannot
be recovered from report counts alone. Qualification added after direct Perl
execution: the all-gap boundary scans have no explicit index check, but they
terminate when an out-of-range element is `undef`, which does not equal `-`.
For `---`, the forward scan stopped at index 3 after 3 iterations; the reverse
scan stopped at index -4 after 6 iterations because Perl negative indices
traverse the row again. The earlier draft's description of these as unbounded
loops was unsupported and is withdrawn. This isolated check does not establish
how the complete helper handles an absent column or a completely empty count
population. Those cases still need direct output/failure verification.

## MSA outputs and numerical semantics

For each analysis, `process_alignment_outputs` uppercases sequence lines in a
temporary copy, invokes `snp_analysis -r DIR -x` (plus `-n` for DNA), converts
alignment formats, makes an entropy plot, writes the SNP table, and invokes
`p3x-build-gene-tree --program fasttree --alphabet DNA|protein`. Uploaded outputs
include `.afa`, `.snp.tsv`, `.consensus.fasta`, `.phy`, `.nexus`, `.pir`, `.aln`,
`.xmfa`, Newick, available logs and presentation files. Format conversions can
fail and remove individual files without failure of the converter parent.

The canonical numerical artifact is a position-frequency table, not a VCF:

* DNA header: `Position in Alignment`, `Score`, `Consensus`, `A`, `T`, `G`, `C`,
  `Deletion`, `Number of Sequences`.
* Protein header: `Position in Alignment`, `Score`, `Consensus`, `Detail`,
  `Number of Sequences`. Detail uses comma-delimited three-letter tokens such
  as `Asp=3,Glu=1`; `Del` is `-`, `Xaa` is `X`. Unmapped letters can lose their
  names in this native presentation; original alignment symbols remain needed.
* A non-`none` reference inserts `Position in Reference` after alignment
  position and `Reference Character` after Score. The producer reads the
  **first final aligned row** as its reference. Reference gaps have blank
  reference positions. Requested reference identity alone does not prove that
  final first row is the intended reference.

For row i, let its first/last non-`-` columns be a_i/b_i. At column j, the
native count population includes i iff a_i <= j <= b_i. Internal `-`, ambiguity
and any other literal symbols count. Terminal gaps do not. Let c_js be those
literal counts and n_j their sum. Native entropy is
`H_j = -sum_s (c_js/n_j) log2(c_js/n_j)`, and `Score` is
`100 * numeric(sprintf("%.2f", H_j))`. This is entropy in hundredths of a bit,
not percent identity, conservation confidence or annotation probability.
Consensus requires a **strict majority** over that population; otherwise DNA
uses `N`, protein uses `X`. Consensus FASTA removes consensus `-` columns.
No uncertainty estimate is emitted. DNA A/T/G/C/Deletion columns omit other
symbols even though they contribute to `Number of Sequences` and entropy.
Undefined native blanks must remain distinguishable from measured zero.

The helper also attempts a per-member `snp.out` against consensus, but this file
is absent from the upload suffixes. It requires a `|` in headers and can return
early. It is not the uploaded `.snp.tsv`. No remote per-member call availability
is inferred. Correspondence/variants can be separately calculated from the
complete acquired alignment and explicit reference mapping, retaining their
derived identity.

The retained tree helper uses FastTree `-nt -gtr -gamma` for DNA; its default
protein branch is JTT when no LG/WAG model is selected. The MSA wrapper attempts
midpoint rooting and overwrites the original unrooted tree; rooting errors are
warnings. Native logs and exact tree representation must establish support
semantics. Raw unrooted bytes are not guaranteed uploaded after overwrite.

## MetaCATS invocation, membership and statistics

The application ID is `MetaCATS`, with exact `p_value`, `alphabet=na|aa`, output
destination, and `input_type=files|groups|auto`:

* `files`: stage `alignment_file` and `group_file`; no aligner is invoked.
* `groups`: acquire each selected feature group and its nucleotide/protein
  sequences, construct metadata with exact group path values, then MAFFT
  `--auto --preservecase`.
* `auto`: acquire exact `auto_groups[].id`, write `grp` assignments, then the
  same MAFFT command. `g_id`, `metadata`, `metadata_group`, `year_ranges` and
  `alignment_type` are not consumed by the inspected statistical path.

`files` supports multiple metadata columns: each category creates a separate
set of tests. This is a category/group design distinction, not a new episode.
The app replaces terminal `-` with `#`; internal `-` stays a tested state.
`metadata_parser` keys sequence rows by the first whitespace-delimited header
token, joins metadata column 1 to that exact token, sorts category/group names
and assigns group ordinals. Repeated metadata IDs overwrite; repeated FASTA
IDs append sequence text. Missing metadata can create an empty/Unlabeled group.
The file header detector uses the first metadata field as a regex against
headers, not exact membership. These hazards must be surfaced, not replicated
as silently trustworthy joins.

Additive group-identity qualification from the complete R/Perl path: metadata
ordinals use all metadata rows, but only rows with sequence data enter the R
matrix. R converts the whole matrix to character, and `table` constructs
columns from represented group tokens. `residueDiversity` labels these columns
by their positions (`group1`, `group2`, ...); the Perl exporters then interpret
those positions as the original metadata ordinals. A metadata-only group can
leave a missing ordinal; ten or more represented groups can have character
ordering such as 1,10,11,2 rather than numeric order. Thus exported group labels
can misidentify the underlying observations even when basenames are unique.
Retain original metadata ordinal, actual R column token/index and exported
label as separate identities. Actual R runtime/collation order must be evidenced;
this source trace alone is not an executed demonstration of every ordering.

Correction after root's separate native R 4.3.3 execution: the metadata-only
group mislabeling was reproduced, but the proposed >=10-group lexical-order
problem was **not** reproduced. `as.matrix` padded ordinals as `" 1"` through
`" 9"`, then `"10"`...`"12"`, preserving numeric order in that example. The
earlier unpadded `1,10,11,2` statement was a hypothesis, not an observed native
ordering, and must not be used as a proven defect. Preserve exact padded tokens
and runtime evidence. See root's `TWELVE_GROUP_ORDER_CHECK_001.json` below.

Each site's R contingency table has observed symbols as rows and group
ordinals as columns. The `#` row is removed. All-missing sites are skipped;
one-symbol sites get `chi-square=NA, p=1, df=NA, sparse=N` without an omnibus
test. Variable nucleotide sites add zero A/C/G/T rows when absent. Protein
sites do not pad an amino-acid alphabet. All cells then receive 0.001 before
the omnibus `chisq.test` and pairwise calculations.

For augmented counts O, expected E_rg = rowTotal_r * groupTotal_g / N. The
omnibus statistic is Pearson chi-square, with R's default Yates correction
when the table is exactly 2 by 2. The pinned R reference uses
`delta=min(0.5,min(abs(O-E)))` there and `sum((abs(O-E)-delta)^2/E)`; otherwise
delta=0. Degrees of freedom are `(R-1)*(K-1)`. The p-value is the chi-square
upper tail. Native `Fewer_5=Y` means **any positive raw observed cell <5**;
it is not the expected-cell adequacy criterion. Native warnings are suppressed.

For pair (g,h), `mcFunc` uses the two group columns and recomputes E, without
Yates. Nucleotide df is R-1. Protein df is `(K-1)*(R-1)` using the **original
total group count**, even though each comparison has two groups. The code
changes a numerically zero pairwise p-value to **1**. Preserve any such native
observation and qualify it; an offline mathematical p-value must be a separate
field. Neither omnibus nor pairwise p-values are multiplicity adjusted. The
term `Multiple_comparison_p-value` does not establish correction.

`copy_to_tsv` retains only p-values strictly less than the submitted cutoff,
independently for omnibus and pairwise outputs. It deletes complete temporary
R tables. The upload list retains only `*Table.tsv`, `.log`, and `.afa`.
Generated `metadata.tsv`, adjusted sequences, category matrices and unfiltered
R results are not normal uploaded artifacts. Acquiring significant tables
alone cannot establish the number or values of all performed tests.

Additional source qualification: `files` mode stages its original alignment
outside `work`, does not copy it to a work `.afa`, and later deletes the staged
input. The output suffix list therefore does not establish an uploaded alignment
for that mode; retain the exact original input binding. `groups|auto` create
`work/output.afa`. Their sequences are explicitly uppercased before MAFFT;
`files` mode preserves case. Statistical counts must follow actual supplied
symbols, not assume uppercasing for every MetaCATS input.

Current exported headers are:

* `Position`, `Chi-square_value`, `P-value`, `Degrees_of_freedom`, `Fewer_5`,
  followed by dynamic group labels and residue count strings such as `8 A`.
* `Position`, `Multiple_comparison_p-value`, `Groups`, where group names are
  comma joined. Basenames replace full group paths, and commas are unescaped.
  Colliding basenames or comma-containing groups cannot be disambiguated from
  the output alone. Bind full original labels and their source-backed ordinals.

## Filled examples actually examined

`NATIVE_EXECUTION_RECEIPTS.json` records two successful executions of the exact
retained Perl SNP helper on explicitly synthetic aligned inputs. No aligner,
AppService job, downstream tree, production parser or episode was executed.
The DNA helper attempts a hardcoded `/usr/local/bin/getorf`; its availability
was not established and coding information is not part of the emitted table.

| Example | Actual native cells | Separately derived meaning |
| --- | --- | --- |
| DNA column 2 of `AACGT--`, `AATGTT-`, `--CGTAA`, `A-CGTAA` | A=2, Deletion=1, Number of Sequences=3, Score=92, Consensus=A | H=0.9182958340544896 bits; whole-matrix gaps=2/4; canonical entropy=0 over 2 bases. One terminal gap is excluded from the native denominator. |
| DNA column 3 | C=3, T=1, n=4, Score=81 | H=0.8112781244591328 bits; canonical majority=3/4. |
| Protein column 4 of the retained four-row example | `Del=2,Gly=2`, n=4, Score=100, Consensus=Xaa | H=1 bit; canonical-only entropy=0 over two G residues. Strict-majority tie remains X. |

The original MetaCATS repository's `docs/example_output.tsv` is a **legacy
schema**, not evidence of current exported schema. Its first row is position
`14*`, chi-square 7.139, p=0.007543, df=1, group counts C13/S9 and C4/S20.
Those quantities are native example observations. Their original input pairing,
correction version, significance-family denominator and star semantics are not
established; do not join them to a same-sized FASTA merely by coincidence.

`OFFICIAL_INPUT_ARITHMETIC_INSPECTION.json` is explicitly **offline Python/SciPy
arithmetic on official retained input**, not native R output. `na_test.afa` has
14 rows of 765 columns. `metadata.na.1.tsv` joins all exact IDs once, with group
sizes 8 and 6. There are 312 variable-site tests under the inspected native
counting/padding rule. At site 28, counts are A8 versus C6. Adding 0.001 to four
symbol rows gives X²=13.995751481999479, df=3,
p=0.0029109414412902606. Bonferroni over those 312 tests gives
0.9082137296825613; BH gives 0.007397967443134484. All variable-site arithmetic
is retained, including the correction population. No independent-sample or
calibrated gene-function claim follows. `Rscript`, MAFFT and MUSCLE were not
available on the inspected PATH; the current MetaCATS R producer was not run.

## Concrete unresolved dependencies

1. Actual service definitions/versions, successful task receipts, authenticated
   member expansion and complete Workspace bytes for both apps remain absent.
2. Prealigned MSA declaration mismatch; actual translation code/coordinate map;
   random ID occurrence mappings; segment/locus post-filter and original maps.
3. A retained real multi-block XMFA example and authoritative native coordinate
   specification. BV-BRC's reader establishes syntactic block/member/strand
   fields but alone does not prove all coordinate semantics or boundaries.
4. Current MetaCATS native output from complete R/Perl execution, including
   conserved/all-missing sites, multi-category cases and label collisions.
5. Exact resolved metadata for group/auto MetaCATS jobs, especially membership
   before sequence acquisition and retained group data after source mutation.
6. Actual deployed R behavior/version and FastTree output/support provenance.
   These missing facts constrain their dependent cells, not independent parser
   and calculator development for known formats.

## Additive native R evidence supplied by root

After the initial review, root ran seven unchanged retained Perl/R producer
cases using a private R 4.3.3 runtime, under
`../tool_graders_bvbrc_metacats_native_execution_2026-10-25/`.
`NATIVE_RUNS_001.json` records all seven exit-zero runs, exact input/source/output
hashes and explicit Python terminal-gap preprocessing. Raw R tables were copied
before the unchanged Perl producer deleted them. This worker read those receipts
and actual small output tables; it did not execute these runs or change that
directory. Exact cross-references/hashes are retained in
`ROOT_NATIVE_EVIDENCE_REVIEW.json`.

| Native case | Actual observations |
| --- | --- |
| Official NA 14×765 | 143 exported omnibus rows and 143 pair rows at cutoff .05. Site 28: X²=13.9957514819995, p=0.00291094144129027, df=3, native Fewer_5=N, counts 8 A vs 6 C. This agrees with separate unrounded Python arithmetic within native print precision. |
| Two AA groups, 6 A vs 6 C | Site 2 omnibus X²=8.33055648117294, p=0.00389837142433717, df=1; pair p=0.000533148220906465. The different native values retain the omnibus continuity versus pair no-continuity distinction. |
| Three AA groups, 6 A/6 C/6 D | Site 2 omnibus X²=35.9820089955022, p=2.91846143844549e-07, df=4; all three native pair p-values=0.0173810251352965. Preserve the native K-dependent AA pair df contract. |
| Metadata-only first group A; actual B and C present | Exported headings A/B/C show 6 A, 6 C, blank, while true source groups B/C contain those observations. Native pair is mislabeled A,B. This confirms ordinal/column identity failure, not absence of scientific difference. |
| Twelve AA groups | Exported columns correctly retain g01...g12 in this runtime; padded R group tokens preserve numeric order. The unpadded lexical-order hypothesis was not reproduced. |
| 2000 A vs 2000 C | Omnibus X²=3995.997004003, native p=0. Raw pair table contains p=1 under the source zero-to-one rule, so the pair disappears from the significant-only export. This demonstrates why absence from the exported pair file cannot imply no association. |
| All missing | Header-only exported omnibus/pair tables, no raw test rows, exit 0. These are zero performed tests in this proved input, unlike a significant-only empty file with unknown input population. |

This narrows initial unresolved item 4 for these exact current-source inputs and
runtime. Current deployed BV-BRC versions, full AppService/aligner execution,
multi-category/other label cases and original live task custody remain unverified.
The earlier statement about Rscript being absent on the inspected PATH remains
a historical fact; it is not a claim that root's later private runtime was absent.
