# Fresh064 — YeaG immunoblot case, before a gel reader

Research proposal only, 2026-10-26. No implementation, adopted scoring policy,
completed axis, model-backed LiteratureEpisode or scientific runtime execution.
Ten axes remain A101–A108, A110, A111. W05/target correspondence are outside this
workload. All pre-existing files remained read-only.

## Source packet and reset

One paper only: Figueira et al., *Adaptation to sustained nitrogen starvation by
Escherichia coli requires the eukaryote-like serine/threonine kinase YeaG*,
Scientific Reports 5:17524 (2015), DOI 10.1038/srep17524, PMC4664914.
Primary source identity: https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/ .
This was an offline cached-primary inspection, without a new literature search.

Read all text in `primary_yeag/PMC4664914_original.xml`, including Methods,
figure captions and references, as two complete sequential ElementTree itertext
portions, characters [0,35000) and [35000,53388). Actually viewed the original
`srep17524-f3.jpg` and `srep17524-f6.jpg`. Read complete
`supplement_layout.txt` only after the concrete unresolved questions: which
strain/allele and plasmid/tag were used, and does the supplement establish
loading, expression sample timing or calibration? The layout supplies Table S2
identities but no additional blot quantification protocol. The supplement PDF
was not opened or rendered. This report does not claim to have visually checked
the supplement's alignment figures or table typography against the PDF.

After this same-paper packet and before the proposals below, reread the complete
active goal, full authority set enumerated in the research AGENTS, complete
applicable current amount modules/contracts and A105 numerical proposals;
SOURCE_CORRECTIONS and the release brief's latest literal user instructions
were read last. READ_PROVENANCE_001.json gives actual portions and failures;
READ_HASHES_001.json records hashes. No old SOURCE_AND_COMPONENTS, old score
report, private history, credentials or provider log was read.

## The experiment, with definitions before conversion

**Organism and genotype.** Main Methods says E. coli K-12 derivatives. Supplement
Table S2 labels wild-type as E. coli K-12 substr. MG1655, then supplies
`[F-, lambda-, Δ(araD-araB)567, rph-1] (BW25113)`; ΔyeaG is labelled
`ΔyeaG780::km (JW1772-1)`. Retain those literal strain designations and their
inconsistent-looking MG1655/BW25113 attribution; do not silently repair pedigree
using outside knowledge. The experimental contrast is the paper's matched
ΔyeaG complementation series, not another organism expressing a mutant protein.

**Source molecule/construct.** Supplement Table S2: pBAD18-yeaG expresses
6xHis-YeaG under an arabinose-inducible promoter, AmpR. K116A, R232A and K426A
are separately expressed point variants in the corresponding pBAD18-yeaG
plasmid; Y382Stop introduces a stop at residue 382 and expresses the N-terminal
portion. Fig. 3A/B schematics place K116A/R232A in AAA+ and K426A in eSTK;
Y382Stop removes the C-terminal region. The article calls these catalytic
mutations based on alignments. Those labels are not measurements of catalytic
activity in this paper.

**Replacement versus coexistence.** Fig. 3A/B and Results identify ΔyeaG strains
complemented with separately selected plasmids. Chromosomal wild-type yeaG is
deleted; plasmid wild-type and plasmid mutant are alternative arms. This is
replacement of the missing source protein, not mutant and wild-type YeaG mixed
within the same strain. Other cell constituents and the rest of the adaptive
network still coexist. Fig. 3C lane labels name constructs, not independently
the genotype or sampling time of every blot lane; attachment of each blot lane
to the recovery culture/time relies on the Results linkage, and exact timing
remains unreported in the inspected packet.

**Intended changed variable and comparison arms.** Among ΔyeaG pBAD18-yeaG arms,
the intended change is variant sequence/domain integrity. Same host deletion,
vector/promoter, His tag and growth recipe aid comparability. Wild-type pBAD18
and ΔyeaG pBAD18 are phenotype controls; ΔyeaG with plasmid wild-type YeaG is
the complementation reference. The blot's denominator is plasmid-expressed,
His-tagged wild-type YeaG in the corresponding blot, NOT natural untagged
chromosomal YeaG abundance in wild-type bacteria. Sequence-dependent abundance,
folding, degradation, solubility, partner interactions and plasmid expression
can differ beyond catalytic function.

**Conditions and endpoints.** Methods: 37°C, 180 rpm; Gutnick minimal medium,
trace elements, 0.4% glucose; 10 mM NH4Cl precultures, 3 mM for pre-starvation
and recovery; starting OD600=0.05 in 50 ml; 50 µg/ml ampicillin where appropriate;
0.1% arabinose for complementation constructs. Recovery follows 24 h N starvation
and transfer to fresh medium. Fig. 3A/B measures OD600 versus time in hours;
error bars SD, n=3. Main statistical Methods default is at least three independent
experiments unless otherwise specified. That supports the stated growth-curve
replication, not a blot-specific replicate count or a shared-sample covariance.
The paper says similar starting viable-cell numbers were confirmed in recovery.

**The gel measurement.** Fig. 3C is an anti-His immunoblot, not a total-protein
purity gel, zymogram, substrate conversion or kinase activity trace. Western
Methods specifies anti-polyHistidine-peroxidase A7058, 1:5000; it also lists
anti-RpoS/anti-DnaK and secondary antibody for another experiment. DnaK is not
shown as a Fig. 3C loading control and must not be borrowed from Fig. 5E.

Observed Fig. 3C labels and visible bands:

| Blot | Lane | Printed construct | Printed relative signal | Visible band information |
|---|---:|---|---:|---|
| Left | 1 | 6xHis-YeaG | 1.0 | Main band around the 70 kDa marker region |
| Left | 2 | 6xHis-YeaG K116A | 0.64 | Main band in the corresponding region |
| Left | 3 | 6xHis-YeaG R232A | 0.48 | Main band in the corresponding region |
| Left | 4 | pBAD18 vector | 0 | No comparable strong band visibly apparent |
| Right | 1 | 6xHis-YeaG | 1.0 | Main band around the 70 kDa marker region |
| Right | 2 | 6xHis-YeaG K426A | 1.12 | Main band in the corresponding region |
| Right | 3 | 6xHis-YeaG Y382Stop | 0.96 | Lower apparent-mobility position, between 25 and 35 kDa markers |
| Right | 4 | pBAD18 vector | 0 | No comparable strong band visibly apparent |

Values are **paper-printed signal summaries read from the image**, not newly
integrated pixel intensities. Band locations above are qualitative visual
observations against printed markers; no new mass fit or construct-length
inference was made. The truncated construct's apparent band position is not a
measurement of molar amount, integrity or catalytic competence.

Results reports abundance percentages 64%, 48%, 100%, 96% for K116A, R232A,
K426A, Y382Stop respectively. K426A therefore has an actual representation
conflict: Results 100% versus Fig. 3C 1.12 (112%). Preserve both; choose neither
a favorable value nor their average. Separate WT=1.0 denominators belong to the
two displayed blots; their physical identity, equivalence and covariance are
unknown. The printed vector zeros are author summaries, not proof of zero
background, zero molecules or a known detection limit.

**Loading/validity limitations.** No Fig. 3C loaded cell count, OD equivalent,
total-protein mass, loading-control band, lane volume, target standard,
background subtraction procedure, linear-response range, saturation test,
exposure time, independent blot/preparation count, dispersion or covariance is
reported in the selected packet. The image cannot establish these missing
relationships. Relative anti-His signal is thus supported; calibrated molecule
amount per cell, molar amount, purity and active fraction are not established.

## What the measurements establish for annotation evidence

Fig. 3A/B supports failure of tested variants to restore the paper's
recovery-growth phenotype while wild-type plasmid yeaG restores it. The blot
addresses a concrete alternative explanation: absence of detectable expressed
variant. K116A and R232A also have lower reported signal than the plasmid-WT
reference, leaving reduced expression as a confound. Y382Stop has near-reference
reported signal but differs in domain composition and apparent mobility.
K426A's reported signal is near reference in either representation, but the
100/112% conflict is real and the blot does not quantify active folded protein.

This is principally **A106 perturbation/restoration** evidence. The blot helps
characterize comparability of source-molecule amounts/signals across phenotype
arms. It cannot by itself populate A105 direct activity, specificity, product
identity or a numerical activity-reliability component. A105 can retain the
source construct/amount qualification if paired later with an applicable direct
assay; it cannot infer kinase or ATPase rates from these bands. The paper cites
prior in-vitro kinase work, but that cited paper was not opened and supplies no
new measured operands here.

**Comparability** asks how much the arms differ outside the intended sequence
change; a 0.64 reported expression signal quantifies one such difference.
**Effect isolation** asks whether the recovery change is caused specifically by
catalytic loss rather than abundance, folding, interaction or downstream changes.
The present blot does not measure those contributions; even signal equality
would not isolate catalysis. Complementary matched-dose WT/variant rescue,
loading-normalized calibrated abundance, solubility/folding checks and direct
ATPase/kinase assays repair different limitations. None is automatically an
independent replication of the growth experiment.

SOURCE_CORRECTIONS SC01 is applied: K116A/R232A abundance and failed rescue are
Fig. 3 recovery-growth facts. Fig. 6B prolonged-starvation CFU includes only
K426A/Y382Stop complementation variants, plus WT, deletion and WT rescue controls.
It does not test K116A survival. Fig. 6A uses SEM n=3; 6B SD n=3 at 20 min, 72 h,
120 h. Viewing Fig. 6 confirms that endpoint separation, not a new gel. No CFU
heights were digitized. Fig. 6C's competitive-index caption/method ratio direction
also differs in the full paper, but it is outside this bounded gel conversion;
no CI cell is nominated.

## Paired numerical proposal and future readers

See PAIRED_COMPONENTS_002.md for exact cells, operands, equations, sum/multiplier
roles, actual and explicitly synthetic arithmetic, interpretation questions and
reader requirements. The case supports reuse of scientific numerical meanings
across source formats, while exposing that current amount units/roles do not
include relative immunoblot signal. A future gel reader must not obtain an
activity assertion merely by recognizing bands.
