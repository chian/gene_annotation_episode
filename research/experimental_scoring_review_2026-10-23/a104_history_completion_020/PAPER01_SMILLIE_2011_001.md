# Source conversion: quantitative ecology as HGT explanation

Goal: supply measurable environmental-history operands for A104's explanation
of a specified discordance, without treating ecology as function evidence or
manufacturing ancient donor–recipient contact time. This is a new proposal;
A105 remains first, no axis is completed, and no production code is changed.

Source: Smillie et al., *Ecology drives a global network of gene exchange
connecting the human microbiome*, Nature 480, 241–244 (2011),
https://doi.org/10.1038/nature10571. Primary supplement:
https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fnature10571/MediaObjects/41586_2011_BFnature10571_MOESM264_ESM.pdf.

Actual coverage: main abstract/landing page only (main full text paywalled);
supplement text lines 1–700, including complete Methods/references pp. 1–5,
all six figure captions pp. 6–11, Tables 1–2 and the start of Table 3. Only
Methods/abstract quantities are used below. Figure images were requested but
not visually inspected or digitized; no plotted values are extracted. Remaining
supplement lines 701–1554 and separate metadata/sequence files are uninspected.
The PDF parser emitted font/marked-content warnings; the relevant Methods
paragraphs were also inspected in the publisher's text rendition.

The complete local authority set, SOURCE_CORRECTIONS, assignment brief and
latest attachment were reread AFTER this inspection and BEFORE this conversion.
A clipped output boundary between TIME_AWARE_ESTIMATION and TOOL_KNOWLEDGE was
repaired by rereading time lines 351–388 and knowledge lines 1–50. The latest
human goal/criteria direction was read last. Full coverage is recorded separately.

## Experimental definitions and source quantities

This is a comparative genome analysis, not a protein transfer-rate experiment.
The compared subjects are bacterial genome pairs; neither a changed protein
construct nor a coexpressed wild-type/mutant mixture is present. Its intended
comparison is inferred recent gene exchange between ecological groups. It uses
2,235 genomes and a recent-transfer identity criterion above 99%. The outcome
is sharing an inferred transfer, not observed present-day donor-to-recipient
events or molecular activity of a characterized protein.

Comparability is addressed through phylogenetic-distance bins, clustering of
near-identical isolates, and conditioning on body site for further oxygen or
pathogenicity comparisons. Isolation is a separate limitation: retrospective
genome association does not isolate a causal environmental influence, date an
individual transfer, identify its direction, or demonstrate a contact route.
Different-center and non-cosmopolitan sensitivity analyses address particular
confounds; they are reanalyses of the same data, not independent replications.

| Source location | Actual quantity | Conversion relevant to this sheet |
| --- | --- | --- |
| Main abstract | 25-fold enrichment in human-associated versus diverse nonhuman isolates; reported P=3.0×10^-270 | Preserve ratio 25. Under a declared human-associated comparison benchmark, inverse relative frequency is 1/25=0.04. This is a study-scoped ecological frequency ratio, not a 0.96 historical-transfer probability. |
| Supplement, Counting HGT / Clustering similar genomes, pp. 4–5 | Pairwise indicator of at least one transfer; average genome-pair contribution within each species-cluster pair; clustering at <2% average 16S divergence | Each distinct cluster pair contributes once; fragment count, event length, repeated genomes and multiple papers do not create independent events. |
| Supplement, Statistical methods, pp. 4–5 | Comparison within bins of 1% 16S distance; expected frequency conditional on body-site pair and divergence before oxygen/pathogenicity analysis | A usable donor/recipient ecological score requires a matched reference stratum. Global 25-fold enrichment cannot be applied to every event or to ancient marine-to-gut history. |
| Supplement, error bars, p. 4 | Reported approximation Var[p]=p(1-p)/n, n independent cluster-pair comparisons | Preserve the source's uncertainty method; graph-derived or aggregate ratios do not supply absent event counts or joint covariance. |
| Supplement, quartet mapping, p. 1 | 23% lack enough non-HGT homologs for quartets; >99% support among analyzed events | Sparse comparator cases retain missing phylogeny; they do not receive zero. Percent support across events cannot populate one target's placement. |
| Supplement, limitations, p. 2 | Only recent, sufficiently divergent lineages; geography is isolation-site proxy | Transfer the method/definition, not its estimated ecological frequencies outside its measured population. |

## Proposed exact operand and numerical role

For a specified ecological predictor/route comparison, let each eligible
species-cluster pair a have y_a = (# genome pairs sharing ≥1 qualifying HGT) /
(# eligible genome pairs). For fixed matched stratum z and ecological profile e,
define h(e,z)=sum(y_a)/number of eligible cluster pairs. Let e* be a declared,
observed reference profile under the SAME ascertainment, distances and temporal
class. Then B(e,z)=min(1,h(e,z)/h(e*,z)), provided the reference is positive.
The unit is a relative conditional transfer-frequency coordinate in [0,1].
It evaluates how the ecological profile compares to the stated exchange-capable
benchmark. It does not estimate the event's occurrence probability.

The main abstract provides only an aggregate ratio: it permits the checked
ratio illustration B(nonhuman)=1/25=0.04 and B(human reference)=1 under that
aggregate benchmark. It does not populate per-event h, sample size, interval,
or the matching relationship to an annotation target. Those cells are null.
An ancient-event application without a supported population mapping remains
unknown, rather than accepting the abstract's ratio as universal calibration.

In the completed sheet this B coordinate will be one measurable way to
populate a specific environmental/route explanation component; it must not
be added to separate body-site, oxygen and geography grades using the same
pairs. Conditional multivariate strata or one explicitly chosen predictor
preserve the dependence. Exact HGT-explanation and candidate aggregation are
defined in the cross-case completion, not inferred from this paper's methods.

Complementary evidence would include event-linked donor/recipient ecological
observations, a supported physical introduction route, chronology, or direct
cargo mobility measurements. None of those measurements is fabricated here.
The source supplies a quantitative environmental method and a contrast; it
does not settle the user's scoring transformations or complete A104.
