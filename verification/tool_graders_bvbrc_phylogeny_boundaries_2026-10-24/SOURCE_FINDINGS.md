# GeneTree and CodonTree native boundary study

This is source and retained-example evidence for fixed rows **C-L194-GeneTree**
and **C-L193-CodonTree**, not a production implementation or completion claim.
The original user goal is unchanged. Neither a native service job nor episode
communication was exercised. Proposed interfaces are in BOUNDARY_PROPOSAL.md;
they are deliberately separate from the facts below.

The original objective and all sixteen principles were read in full before the
study and reread verbatim from the original attachment after substantial source
and native-output examination, before writing the proposal. The goal SHA256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
No goal, permanent decision, checklist, production file, existing test, or prompt
was changed. Literature graders and W05 are outside this workload.

## Evidence locations

Paths abbreviated below are local, retained files:

- **G/** = `../tool_graders_bvbrc_application_artifacts_2026-10-24/sources/bvbrc_gene_tree/`.
- **C/** = `../tool_graders_bvbrc_application_artifacts_2026-10-24/sources/codon_trees/`.
- **AG/** = `additional_sources/bvbrc_gene_tree/`.
- **AC/** = `additional_sources/codon_trees/`.
- **E/** = `official_example/test9_genome_dir/`.

`READ_SOURCE_IDENTITIES.json` records all seven original implementation file
SHA256s and both packaged original definitions. `ADDITIONAL_SOURCE_RECEIPTS.json`
records pinned URLs, Git tree and blob identities, byte counts and SHA256s for
additional sources and examples. Downloaded Git blobs were checked against the
already retained official tree. A Git tree identity is not a deployed version.
`PRIMARY_DOC_RECEIPTS.json` separately identifies unpinned official engine
documentation; these documents are semantic references, not runtime proof.

The previous artifact study was read first. Its APPLICATIONS.json truthfully
reported no native job bytes. The missing native examples acquired here are
official repository examples, **not** AppService result receipts. The existing
study has not been rewritten.

## GeneTree: actual producer path

1. The packaged definition permits DNA/Protein; aligned or unaligned FASTA,
   feature groups, genome groups and feature IDs; RAxML, PhyML and FastTree;
   optional viral segment selection/concatenation. The enum does not include RNA
   despite the alphabet description mentioning it.
2. `App-GeneTree.pl:324–463` gathers the supplied sequence sources. FASTA is
   downloaded and read; feature groups fetch aa or na according to the request;
   genome groups fetch genome_sequence rows. The feature_ids branch calls
   `retrieve_protein_feature_sequence` unconditionally, including when DNA was
   requested (`436–444`). The returned feature-ID keys are marked as feature_id;
   this is a source behavior, not independently validated identity.
3. Genome retrieval selects `sequence,contig` but tests `record.segment` to select
   and label segments (`413–430`). Selected segment operation therefore needs
   actual returned records; the request does not prove selection occurred.
4. `Sequence_Alignment.pm:163–284` keeps the first whitespace-delimited FASTA ID,
   drops empty sequence entries, and derives the locus from the basename before
   its first dot. `add_seq:74–125` removes spaces and suffixes duplicate IDs at a
   locus `_2`, `_3`, etc. Locus names are sorted. There is no uploaded original-ID
   map. Distinct same-named files can merge into one locus after local basename
   handling; original file/member identity must be supplied independently.
5. A single declared aligned input skips alignment; otherwise `align()` is called
   with no selected program (`App:504–515`). `Sequence_Alignment::align:390–434`
   always invokes `mafft --auto [--thread P3_ALLOCATED_CPU] <locus>_unaligned.fa`.
   The advertised alignment_program parameter does not select Muscle here.
   Return status from that native aligner call is not checked before reading its
   output. The grader must not repair a failed/malformed alignment by padding.
6. Optional end trimming changes the stored rows (`Sequence_Alignment:460–528`).
   The threshold is minimum non-gap occupancy; gap-only counting treats only
   `-` as gap. Original residue offsets are not emitted in a structured sidecar.
   The App saves the returned trim strings as a report command line, while the
   per-locus detail aggregation has a shadowed variable. Preserve actual output
   and actual trim evidence; do not reconstruct an original map from settings.
7. Gap filtering deletes a row from a locus but never removes its ID from the
   global `_ids` array (`555–597`). Output writing loops over global IDs and fills
   a missing locus with all gaps (`286–362`). A post-filter all-gap row can be a
   native missing-locus representation. It is not proof of a biological deletion
   or of an originally absent sequence. These source facts qualify measurements
   of the final matrix; do not imitate this behavior on a parser error.
8. App output is one tree/alignment per locus, plus a concatenated tree when
   requested (`557–601`). A locus-specific alignment still uses the global ID
   set. Concatenation follows sorted locus order, filling missing loci with `-`.
   PhyML receives relaxed sequential PHYLIP (full IDs, not ten-character
   truncation); the other engines receive FASTA. RAxML-specific sanitization and
   restoration methods exist in Sequence_Alignment, but this App calls
   `write_fasta`, not `write_fasta_for_raxml`.

### GeneTree commands and support

`App:541–547` selects LG for Protein or GTR for DNA unless supplied. However,
`Tree_Builder->new($alignment_file)` receives no explicit alphabet (`App:583`).
The builder infers it by counting A/C/G/T versus other selected letters
(`Tree_Builder:76–89`), so requested alphabet is not proof of executed datatype.

| Native path | Actual command behavior | Scientific consequence |
| --- | --- | --- |
| `Tree_Builder:265–304` | `raxmlHPC-PTHREADS-SSE3 -T 2 -p 12345 -x 12345 -N 100 -m <model> -s <alignment> -n <base> -f a`; DNA forced GTRGAMMA, proteins PROTCAT plus accepted model or LG | Rapid bootstrap plus ML; selects RAxML_bipartitions, renamed `<base>_raxml.nwk`. The fixed 100 comes from source. Runtime logs/commands are needed to attest a particular run. |
| `Tree_Builder:306–359` | `phyml -i <alignment> -d nt|aa -m <model> -b -5` unless `_bootstrap` set | `-5` is approximate Bayes support, not bootstrap or SH-aLRT. |
| `Tree_Builder:361–386` | `FastTree -out ... -log ...`; DNA adds `-nt -gtr -gamma`; Protein adds `-lg` or `-wag` when applicable, otherwise native JTT | FastTree 2 local support is SH-like on a 0–1 scale; a deployed version is still required to establish semantics. DNA Gamma20 likelihood and site-likelihood logs are produced locally when this command/version is used. |

`App:591–594` comments out the bootstrap setter. Thus the App's bootstrap request
does not control any of these three branches in this source. The standalone
`p3x-build-gene-tree.pl` passes bootstrap as an argument to build_* methods, but
those methods only shift `$self`; that wrapper also does not establish a working
bootstrap override. The App reads allocated threads into a variable but never
passes it to the RAxML builder. PhyML separately receives PHYMLCPUS from the
environment. Source defaults must not overwrite native run evidence.

The model request also cannot label output by itself: RAxML replaces DNA HKY85
with GTRGAMMA, and FastTree accepts only its implemented protein choices. Preserve
requested/effective/observed settings and conflicts separately.

### GeneTree uploaded versus merely produced artifacts

The authoritative list is built at `App:571–600,604–685` and uploaded at
`698–725`; missing files are warned and skipped rather than creating content.

| Artifact | Destination/type | Retention limitation |
| --- | --- | --- |
| `<base>[_<locus>]_aligned.fa` | detail_files, `aligned_${alphabet}_fasta` | Final aligned/trimmed/gap-filled rows; original input and trim map are not included. |
| Same base `_aligned.phy` for PhyML | detail_files, txt | Relaxed sequential PHYLIP; Workspace txt is not a format selector. |
| Returned `_raxml.nwk`, `_phyml.nwk`, `_fasttree.nwk` | detail_files, nwk | Preserve exact raw IDs, labels, comments and branch lengths. |
| SVG | detail_files | Presentation, no independent scientific score. |
| Per-tree `.phyloxml` | result root | Metadata-enriched derivative, not a replacement for raw Newick. |
| Report HTML | result root | Contains steps, commands, engine stdout/stderr, rounded lengths/occupancy. Do not use rounded report tables in place of alignment bytes. |
| RAxML_info; PhyML stats/log; FastTree log | moved back to local App directory by builder | They are **not added to `@outputs`**, so this source does not upload them. No guaranteed per-site likelihood artifact is available through the normal output list. |

### GeneTree metadata and phyloXML conversion

App chooses the most frequent database_link across all retained IDs and invokes
one `p3x-newick-to-phyloxml -l <link> ...` for every tree (`620–667`). It tries
regex-based identification of uploaded IDs (`349–364`) and does not independently
establish that a user header is a BV-BRC accession. Multiple source groups may
produce `data_source.tsv`, but that file is not itself in the upload list.

The additionally retained converter is `AG/scripts/p3x-newick-to-phyloxml.pl`:

- It reads raw Newick and optional explicit translation TSV (`136–164`).
- Metadata TSV joins by exact tip ID; repeated metadata can overwrite earlier
  values (`166–200`). Actual feature lookup joins on supplied feature_id or
  patric_id, then collects feature→genome→genome-field links (`202–297`). Array
  values are flattened with commas. The grader must retain observed fields and
  their lost multiplicity as unknown, never split a flattened product blindly.
- App supplies a removal regex `[^(,)]+\_\@\_`; the converter applies it to the
  entire serialized XML (`332–335`). It is not an invertible identity mapping.
- `Phylo_Tree.pm:347–387` emits BVBRC property keys by default and always writes
  `rooted="true"`. It does not establish a biologically rooted tree.
- `Phylo_Node.pm:27,144–181,265–297` initializes absent branch lengths to zero,
  treats numeric internal labels as support, and writes generic
  `<confidence type="support">`. A zero support value is discarded by its truthy
  check. These derived XML zero/absence conventions must not repair missing raw
  measurements. Newick is the preferred branch/support source.

The official two XML examples retained under AG/tests each contain 17 tips,
14 generic support elements, and 17 explicit product properties for the same
recorded enzyme label. This is a usable example of source-attached function
composition. It is not a measured probability that an unknown target has that
function. Filename `hky85` or `rell` cannot supply missing model/support evidence.

## CodonTree: actual producer path

CodonTree estimates relationships among supplied bacterial genomes from a
selected collection of homolog families; each leaf is a genome. It concatenates
aligned coding nucleotides and amino acids from the same genes. It is not a gene
tree in which each leaf is an independent feature. The protein and its codons
are dependent representations, not two independent pieces of annotation
evidence. Even with allowed missing/duplicate genes this remains a selected
multigene genome-relationship analysis, not an automatically established full
species tree or a functional classification of each genome.

### Application inputs and modes

`C/service-scripts/App-CodonTree.pl:24–116` calls `p3x-build-codon-tree` with main
genome IDs, genome groups, --writePhyloxml, --maxGenes, --bootstrapReps,
--maxGenomesMissing, --maxAllowedDups, explicit RAxML executable/output, optional
metadata fields and threads. It writes opt_genomes.in, but **does not pass it**;
the commented --outgroupIdsFile would not be the CLI's actual
--optionalGenomeIdsFile anyway (`51–60`). Requested optional IDs do not prove
they affected this service analysis.

The CLI exposes additional modes (`C/scripts/p3x-build-codon-tree.py:26–67`), but
the packaged service definition does not expose them. These must remain accounted
as source modes, not advertised as bound AppService options:

- default both codons and proteins (`171–179`), service path;
- --analyzeCodons only;
- --analyzeProteins only;
- optional --analyzePos3Codons branch-length fitting;
- PGFam global default or PLFam local, explicit family list/matrix or GTO input;
- --deferRaxml and --exitBeforeAlignment preparation/debug paths, no inferred tree.

The CLI mutates `allGenomeIds = genomeIds` by adding optional IDs (`216–217`), so
its later claim that optional IDs do not participate in selection needs to be
checked against actual data. The App's absent optional forwarding and the CLI's
aliasing are distinct problems; do not claim either is fixed here.

### Family selection, sequence transformations, and identities

- Family acquisition keeps explicit genome_id, patric_id, PGFam/PLFam triples
  (`AC/lib/patric_api.py:276–325`). It uses per-genome `limit(25000)` with no
  pagination proof. A returned matrix is not automatically the entire genomic
  family population. `genesPerGenome` counts families with a row, not every CDS
  or every duplicated copy (`C/script:248–282`).
- Zero-data genomes are removed before family selection (`255–273`). Eligible
  families require present genomes >= population minus allowed missing and
  total extra copies <= allowed duplicates (`phylocode:82–103`). Initial ranking
  is present_genomes − extra_copies; a subset is selected for alignment using
  `int(maxGenes * (1 + excessGenesProp) + excessGenesFixed)`.
- Retrieved feature FASTA IDs are truncated to the first two `|` pieces and
  duplicate IDs suppressed (`patric_api:159–203`). The main script changes J to X
  in protein sequence text (`314–323`). Preserve raw input→staged sequence
  evidence instead of treating transformations as literal original identity.
- MAFFT or Muscle returns actual FASTA (`phylocode:277–317`). Duplicate handling
  derives genome IDs from the fig|... identifier. In `resolveDuplicatesPerPatricGenome`
  the loop over candidate seqIds evaluates the stale `record.seq` (`450–497`),
  so all candidates in a group get the same query in that calculation. Actual
  inclusion is retainable; the claimed optimal paralog selection is not verified.
  Resolving duplicates also realigns with Muscle even if MAFFT was requested.
- `gapCdsToProteins:499–553` fetches DNA for retained protein IDs, walks three
  bases per nongap amino acid, inserts `---` at protein gaps and substitutes
  `---` when a full codon cannot be obtained. It has an additional short-DNA
  padding branch. Translation mismatch checking occurs only in Debug and uses
  table11; it does not enforce a correct translation in normal execution.
  A gap here is therefore not proof of biological deletion or successful codon
  correspondence. Original CDS/protein bytes plus a validated coordinate map
  are needed for those facts.
- Relabeling to genome IDs stores the original feature ID in in-memory
  `annotations.original_id` (`619–630`). The durable included-members table
  emits these originals. The mapping rule may be applied only as an evidenced
  producer transformation, not as a general accession-from-display-name guess.
- Both alignments are end-trimmed separately (`script:438–461`,
  `phylocode:397–448`). Trim lengths are not retained in the annotation—the line
  is commented out. Original residue/CDS positions cannot be recovered from
  final ungapped coordinates alone.

### Actual numerical quantities in CodonTree

The source calculates pre-trim protein alignment statistics at `script:349–366`.
`phylocode::calcAlignmentStats:319–364` uses all n rows as the frequency denominator,
counts every literal nongap symbol (including X/ambiguities) as a state, and omits
only `-` from the squared-frequency sum. With column counts c[j,s]:

- `gaps` = total `-` cells; `prop_gaps = gaps / (n * L)`;
- `sum_squared_freq = sum_j sum_(s != '-') (c[j,s]/n)^2`;
- `mean_squared_freq = sum_squared_freq / L`;
- per-sequence mean log frequency = `sum_j log2(c[j,row_symbol]/n) / L`,
  including gap states; invariant sites contribute zero;
- ranking score = `sum_squared_freq / sqrt(L)` (`script:353–358`).

These are conservation/selection statistics, not phylogenetic likelihoods or
annotation probabilities. Ambiguous characters can increase this literal
conservation score; canonical-state conservation needs a separately named
calculation. The derived worst-sequence ratio uses a genome's mean across
evaluated families, with a literal `-1e-5` denominator adjustment, and marks
ratios >8 (`371–410`). Its full evaluated-family population matters. Selected
final alignments cannot reproduce that historical denominator.

The native homologAlignmentStats header concatenates `worstSeqScore` and
`used_in_tree` without a tab (`528–541`), but data rows contain both columns.
Extra `bad seqs:` and `disqualification:` lines follow some rows. This is a
producer-specific table with a documented defect, not a generic rectangular TSV.
Only an explicitly declared source dialect can recognize that exact defect;
other malformed headers must be rejected/retained as partial. Do not silently
repair arbitrary tables. Pre-trim values must remain distinct from recomputed
final-alignment values.

### Concatenation, native trees, and uploaded artifacts

`script:574–622` optionally samples protein columns to choose an AUTO protein
model (default sample proportion 0.5). The sampled columns are random and not
mapped in a sidecar; save the sampled alignment but do not invent its source
column correspondence. The subsequent combined alignment is all sorted codon
families, then all sorted protein families (`phylocode:748–798`). Missing family
rows are represented with gaps. Service default output is FASTA `.afa` plus four
partition rows: three stride-3 DNA ranges and one protein range (`624–639`).
Codon-only/protein-only CLI modes emit relaxed interleaved PHYLIP (`641–655`,
`phylocode:639–683`). Counts in `.analysisStats` do not by themselves identify
the actual aligned characters or preserve the per-family coordinate boundaries.

RAxML main command uses selected `GTRCAT`/`GTRGAMMA` and partitions in mixed/codon
mode or `PROT<rate><model>` for Protein; threads and seed are retained. With
bootstrapReps>0 it adds `-f a -x 12345 -N n`; otherwise `-f D`
(`script:668–676`). `-f D` produces RELL bootstrap trees; if present a further
`-f b` maps those supports (`701–717`). RELL is a distinct method from ordinary
rapid bootstrap. An HTML method heading is emitted even if the expected support
file never existed (`873–876`), so it is not sufficient proof of computed support.

The chosen raw tree is copied to `<base>_tree.nwk`. A separately relabeled
`_treeWithGenomeNames.nwk` replaces IDs using an unescaped regex and double-quoted
names (`phylocode:146–152`, `script:742–755`). No one-to-one names map is emitted
as a dedicated JSON sidecar. Duplicate display names remain possible. Raw
genome-ID Newick plus explicit metadata joins should be authoritative. The
NEXUS translation table can be retained as mapping evidence when actually
produced. A separate `-f I` balanced-root derivative is retained when successful;
it is not the raw tree and not a biological outgroup-rooting claim (`725–740`).

The optional Pos3 path is a material source defect: `concatenate_codons_proteins`
uses `range(0, len(fullseq), 3)` whenever codonPos is nonzero (`761–765`), so it
extracts position 1 even for codonPos=3. Its filename cannot establish third-
position measurements. This CLI mode is not exposed by the current App.

The App recursively copies all non-hidden entries in output (`App:225–262`).
The script first moves listed details and deletes remaining `RAxML*` and
`*.reduced` unless debug (`993–1017`). Consequently:

| Artifact | Normal source path/status |
| --- | --- |
| `<base>_tree.nwk`, `.phyloxml`, HTML report | Output root. Raw tree/metadata derivative/report distinct. |
| Final `.afa` or `.phy`, `.partitions`, `.raxmlCommand.sh` | detail_files. Mixed service mode is current FASTA; older example is PHYLIP. |
| `.homologsAndGenesIncludedInAlignment.txt` | detail_files; family + Proteins/Codons + feature IDs; optional deletedParalogs/lacking CodonAlignment markers. |
| `.genesPerGenome.txt` | detail_files; exact header Genome, AllGenes, SingleCopy, Filtered_SingleCopy. Units are family counts at different selection stages. |
| `.homologAlignmentStats.txt` | detail_files; pre-trim table and defect/qualifiers above. |
| `.analysisStats` | detail_files. Num_CDS_alignments incorrectly uses len(proteinAlignments); command_line is the last RAxML command, possibly rooting, not necessarily inference. |
| `RAxML_info.<base>`, model-selection info, sampled `_proteins.afa` | Details when present. Retain engine version, settings, likelihood and partition model values. |
| `_treeWithGenomeNames.nwk`, `_tree_rooted.nwk`, NEXUS, groupsPerGenome.tsv | Details when actually produced; never replace the raw tree silently. |
| protein_alignments/*.afa; dna_alignments/*.afn; homologMatrix/countMatrix | Only with CLI flags. App does not set these flags; do not require them as if normal service output always includes them. |
| Bootstrap replicate trees/bestTree/bipartitionsBranchLabels and most RAxML internals | Deleted by normal script after final selected tree is copied, unless debug. |
| alignment_perseq_meanlogfreq.txt | Written before chdir(outputDirectory), not added to moved/uploaded files. No guaranteed per-sequence historical score sidecar. |

No current service artifact provides general per-site phylogenetic likelihoods.
Conservation is calculable from complete retained alignments. Per-site likelihood
remains missing/not produced, not zero. GeneTree FastTree DNA could produce it
in an unuploaded log; other versions/explicitly supplied artifacts require their
own observed format before adding a parser.

## Official example observations, distinct from proposals

The pinned CodonTree repository archive contains 12 files plus one directory.
`OFFICIAL_EXAMPLE_MEMBERS.json` is the exact archive listing. It includes a
RAxML 8.2.9 native log, mixed PHYLIP alignment, partition file, command, raw best
tree, supported tree, branch-label tree, 100 bootstrap trees, a historical
genome–gene–family triples file and included-family/member table. It does not
contain current pre-trim stats, current `.afa`, raw CDS/protein acquisitions or
AppService task custody.

`inspect_retained_examples.py` was run with the existing local Biopython 1.88.
It invokes no scientific executable or network request. The observed answers
are in NATIVE_EXAMPLE_INSPECTION.json:

- **9** member IDs, **15,300** final columns, despite `8taxa` in filenames.
- **11,475** coding nucleotide columns and **3,825** protein columns; each codon
  partition contains **3,825** sites. Mixing nt/aa is explicit.
- **17,308** literal `-` cells out of **137,700** cells. Native RAxML reports
  rounded gap/fully-undetermined proportion **12.57%**, a different retained
  definition/precision from exact literal gap counting.
- Native final log likelihood **−56958.397755**, **1,953** distinct patterns,
  joint branch-length optimization across four partitions.
- **100** retained bootstrap trees; six nontrivial splits each appear in
  **100/100** replicates and match native support labels **100**.
- Raw best versus supported tree have **0** differing unrooted splits; Newick
  root placement differs. The sum of branch lengths is retained separately.
- Each of ten family membership rows has eight included features. Nine tree
  leaves does not imply every family has all nine genomes.

Two official GeneTree XML fixtures contain **17** leaves and **14** generic
support values each. Their historical model/algorithm versions and support
methods remain unknown. This is format inspection, not validation of new code.

`SYNTHETIC_NUMERICAL_EXAMPLES.json` is explicitly synthetic arithmetic. No
synthetic data is described as native or scientific execution evidence.

## Engine semantics checked in primary documentation

Retained primary docs are supplemental and do not establish a deployed version.

- [FastTree official documentation](https://morgannprice.github.io/fasttree/):
  local SH-like support uses the local alternative topologies; native values
  are 0–1. `-log` with `-gamma` writes per-site likelihoods. Identical sequences
  can yield polytomies and absent support for their shared parent.
- [RAxML manual](https://raw.githubusercontent.com/stamatak/standard-RAxML/master/manual/NewManual.pdf):
  `-f a` rapid bootstrap+ML; `-f D` RELL; `-f I` subtree-length balancing.
  See retained text lines 685–697, 801–810 and 882–888.
- [PhyML manual](https://raw.githubusercontent.com/stephaneguindon/phyml/master/doc/phyml-manual.pdf):
  `-b -5` approximate Bayes, `-4` SH-like, positive values bootstrap; expected
  substitutions per site describes branch lengths (retained text 505–577,
  1204–1225). These statistics remain different quantities.

For branch lengths, preserve the native fitted number, actual engine/model,
site population and optimization regime. Unknown units stay unknown. A mixed
nt/aa joint-model length is not a per-nucleotide divergence, codon rate, time or
organismal phenotype. No branch support is calibrated annotation confidence.

## Remaining native evidence and implementation work

No current deployed definition, authentication, original task→artifact binding,
new service execution, production parser/calculator, selected-tool commission,
or typed return has been verified for these rows. Required native examples still
missing include current GeneTree alignments+raw trees+engine command evidence
for all three recipes; current CodonTree default FASTA, malformed-header stats,
zero-bootstrap RELL path, incomplete inputs and actual group/optional handling;
and original sequence/trim/family-boundary maps for residue-aware facts.

Pure syntax and arithmetic can proceed using the retained examples and explicit
partial states. A missing RELL sample or original coordinate map blocks that
particular parser/measurement proof, not all parsing or all numerical work.
