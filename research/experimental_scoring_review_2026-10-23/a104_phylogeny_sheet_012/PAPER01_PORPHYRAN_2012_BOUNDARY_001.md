# Paper 01: porphyran source boundary for the A104 sheet

Status: source-specific review after the complete recorded authority reset. This
is an incomplete paper-filled A104 row, not an accepted score or completed axis.

Source: Hehemann et al. (2012), *Bacteria of the human gut microbiome catabolize
red seaweed glycans with carbohydrate-active enzyme updates from extrinsic
microbes*, PNAS 109:19786–19791. DOI
[10.1073/pnas.1211002109](https://doi.org/10.1073/pnas.1211002109),
[PMC primary text](https://pmc.ncbi.nlm.nih.gov/articles/PMC3511707/).

## Actual source coverage

The complete main text, figure legends, Methods and references were read from
`porphyran_primary_text_001.txt`, lines 1–510 and 511–1017. The PNAS web view was
also inspected initially but its long display was truncated; the retained main
text repaired that coverage. The PMC supplementary request returned HTML, not a
PDF (`porphyran_supp_response_001`); its scientific contents were not read.
This is fresh retrieval of an assigned existing corpus source, not a newly
discovered case. Only bibliographic fields of the corpus record were read.

## Comparison and attribution definitions

Subjects include the native *Bacteroides plebeius* DSM 17135 locus and the
related *B. thetaiotaomicron* VPI-5482 element. The paper identifies the first
locus as containing the porphyran-utilization genes; the second has different
cargo. The measured excision products concern the whole element. They do not
isolate the function or evolutionary placement of any one catalytic protein.
Recombinant catalytic domains and their substrate assays are separate molecular
measurements; those do not turn into branch lengths or bootstrap observations.
There is no coexpressed WT/mutant mixture relevant to the excision comparison.

## Native numerical observations and their allowed cells

| Source location | Reported number | Defined quantity / denominator | A104 use and limitation |
| --- | ---: | --- | --- |
| Results, PUL contained in an ICE | 18 bp | Length of each identical flanking repeat for the B. plebeius element; not a sample proportion | Supports the specified proposed mobility mechanism as a structural observation; no numeric HGT probability follows. |
| Same Results | 107,705 bp | Reported separation of that repeat pair | Candidate transferred element span; not a phylogenetic branch length or rate. |
| Same Results | 22 bp | Length of each repeat for the B. thetaiotaomicron element | A separate locus, with different cargo; not an independent replication of the B. plebeius transfer history. |
| Same Results | 90,450 bp | Separation of the second repeat pair | Different element extent. |
| Discussion, ICE paragraph | 36–70 additional PCR cycles | Extra amplification stated as necessary to detect excision; not an observed per-generation excision frequency | Preserve the detection limitation. No valid conversion to a transfer rate without calibration, cycle protocol, input molecules and assay efficiency. |
| Results, PUL contained in an ICE | unsuccessful transfer attempt | No numerically quantified detection limit or transfer count reported in inspected main text | A current attempted cross-species transfer failed under those conditions. This is neither a zero historical HGT probability nor a numeric function contradiction. |

The arithmetic `107705 - 90450 = 17255 bp` is a size difference only. It is not a
scoring component because size difference does not answer whether the target
belongs in a functional clade or agrees with organismal history. The sheet must
refuse this tempting irrelevant proxy.

## Paper-filled numerical sheet boundary

| Required A104 cell | Value from this inspection | Reason / complement |
| --- | --- | --- |
| Gene-tree topology and target attachment | unknown | No gene tree was provided in the inspected main text. Obtain the original tree-bearing primary source. |
| Target-to-characterized-function and alternative branch distances | unknown | A104 needs the actual tree, mapped reference tips and lengths. Sequence-identity prose is not a substitute. |
| Organism-tree versus gene-tree correspondence | unknown | Neither matched topology comparison nor a native congruence statistic is reported in the inspected main text. |
| Branch support type, value and denominator | unknown | No such tree statistic appears in inspected main text. |
| HGT explanation measurements | the element/PCR observations above, with no empirical transfer-rate estimate | These can qualify a specific HGT explanation but cannot populate a calibrated numerical likelihood. |
| Compiled A104 point contribution | unknown | Tree operands are missing. Preserve the observed mechanism context without manufacturing a score. |

The 2012 article explicitly cites its earlier source for the initial HGT account:
Hehemann et al. (2010), *Transfer of carbohydrate-active enzymes from marine
bacteria to Japanese gut microbiota*, Nature 464:908–912,
[10.1038/nature08937](https://doi.org/10.1038/nature08937).
That is a proposed extra primary read for actual phylogeny; it has not been
inspected in this packet. The numerical-sheet conversion and final formula must
keep biological explanation conditional on a demonstrated tree placement.

## Dependency and complements

The shared locus coordinates, mobility genes, repeated PCR representations and
main text/figure descriptions are one linked mechanistic evidence block. They
must not be multiplied as independent proofs. Sequence comparisons belong to
A101; neighborhood resemblance to A103; induction to A107. A104 may cite those records only for a specific explanation
of a phylogenetic discordance, with the dependency retained.

Complementary measurements are a gene tree including the target and functionally
characterized alternatives; an organism tree on matched taxa; support/resampling
outputs; and calibrated transfer experiments if an actual transfer frequency is
needed. No new experiment or alignment was run here. No lineage-specific genetic
code assumption is made.
