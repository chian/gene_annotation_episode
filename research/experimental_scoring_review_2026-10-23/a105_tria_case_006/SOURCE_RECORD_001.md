# TriA/AtzA primary-source record

New research record, 2026-10-23. This reviews only DOI
[10.1128/JB.183.8.2405-2410.2001](https://doi.org/10.1128/JB.183.8.2405-2410.2001):
Seffernick, de Souza, Sadowsky and Wackett, *Melamine Deaminase and Atrazine
Chlorohydrolase: 98 Percent Identical but Functionally Different*, J Bacteriol
183:2405–2410. [Full primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/).

The measurement transcription is `paper_inputs_001.json`. The numerical sheet is
`NUMERICAL_SHEET_001.md`; its operands and arithmetic are checked separately. No
production reader, scoring policy, library entry, prompt or scientific run was
changed. The complete authority reset was performed after primary-source
inspection and before scoring interpretation; see `READ_PROVENANCE_001.md`.

## Experimental definitions before scoring

| Definition | TriA | AtzA |
|---|---|---|
| Natural source | Pseudomonas sp. NRRL B-12227 | Pseudomonas sp. ADP |
| Assayed molecular identity | Natural TriA coding sequence cloned from genomic DNA; not a designed amino-acid mutant | Natural AtzA reference enzyme; not a TriA point mutant |
| Expression construct | E. coli DH5α(pJS3); pJS3 is the triA PCR insert in pUC18 | E. coli DH5α(pMD4) is the stated atzA clone; detailed purification is referred to an earlier paper |
| Sequence check | Cloned sequence and three overlapping genomic PCR fragments agreed; duplicate sequencing in both directions | Comparison sequence printed in Figure 3 |
| Preparation for Table 1 / inhibitor assays | Partial purification by 0–20% ammonium sulfate fractionation, followed by dialysis | Purified / highly purified enzyme for the inhibitor comparison |
| Denominator of specific activity | mg of total protein in the partially purified preparation | Highly purified enzyme concentration for AtzA competition experiments |
| Do both enzymes coexist in the same assay? | No mixed TriA+AtzA experiment is described. Host proteins remain in TriA preparations. | Separate preparation; no deliberate mixture with TriA is described. |
| Intended changing variable in Table 1 | Substrate molecule, keeping the TriA preparation class fixed | Table 1 is not an AtzA rate table |
| Intended changing variable in each inhibitor experiment | Addition / identity of an equimolar triazine competitor, with melamine as reaction substrate | Addition / identity of competitor, with atrazine as reaction substrate |
| Additional differences in a TriA–AtzA comparison | Nine naturally occurring amino-acid differences together, source strain, construct, preparation purity, baseline substrate and potentially assay details | These differences do not isolate a single residue's effect |

Locations: Materials and Methods, bacterial strains / cloning / partial enzyme
purification / determination of substrate range / competition experiments;
Results, cloning / DNA sequence. The full DH5α genotype, protein purity fraction,
active TriA concentration and independent preparation identifiers are not supplied.
Plasmid antibiotic selection differs: pMD4 uses chloramphenicol, pUC18 derivatives
ampicillin. These expression conditions do not become numerical assay similarity
scores by themselves.

The protein sequence is natural even though expression is recombinant. The
paper's sequence verification directly addresses unwanted PCR changes; it is not
an engineered mutation screen. This distinction matters for the A105/A106 split.

## Actual A105 measurements and controls

Table 1 reports four positive specific activities and twelve nondetections for
partially purified TriA. The initial rates are from duplicate samples. The
screening protocol uses 8 μg total protein/ml and HPLC observations at 16 and
24 hours. Its stated sensitivity is 10 pmol/min/mg, equivalent to 0.01
nmol/min/mg. The paper labels compounds with no detected conversion after
24 hours as below that limit. It does not report a measured blank rate, its
variance or a probabilistic detection curve. [Table 1 and its Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/#T1).

Product checks are chemically informative but do not supply numerical calibration
scores. Melamine products coeluted with ammeline and ammelide; mass spectrometry
is reported but the spectra and exact masses are not shown. Ammeline produced
ammelide. With CAAT, the final observed product was ammelide; the intermediate
CAOT is proposed to hydrolyze spontaneously. The competing dechlorination route
would produce ammeline, which was not detected. The CAAT row therefore measures
net chemistry in the preparation, not the kinetic rate of an isolated, directly
observed CAOT intermediate. Aminoatrazine gave the corresponding hydroxylated
product, chemically hydroxyatrazine. No ppm mass error or calibration recovery
can be calculated from these statements. Locations: Results, hydrolysis products
and substrate specificity.

The ordinary E. coli DH5α control extract did not degrade melamine. This is
relevant to attribution of the melamine assay, but its numerical rate, detection
limit for that specific comparison, protein loading and variance are absent.
It cannot populate a sample/blank ratio or a fractional contaminant contribution.
The text does not establish the same negative host control for every Table 1
substrate. Western-blot controls establish immunoreactivity, not purity,
catalytic contribution or a quantitative expression denominator.

An ammelide-addition control used 100 μM melamine or ammeline with or without
100 μM ammelide at 22 °C. Total extract protein was 12.4 versus 124 μg/ml,
respectively, to obtain 8–10% conversion over 30 minutes. The tenfold loading
difference is deliberate and must be normalized before comparing raw volumetric
rates. The reported absence of an ammelide effect has no numerical inhibition
estimate or error term. It does not justify setting inhibition to exact zero.
The 22 °C temperature and 100 μM substrate concentrations belong to this
explicitly described experiment; the paper does not explicitly supply those
values for every initial-rate row in Table 1.

The competition results contain seven quantitative percentage-inhibition
measurements, each based on triplicate samples. They measure changes in reaction
rate. They do not provide binding curves, Kd, Ki, IC50, occupancy or a kinetic
inhibition mechanism. A stronger inhibitory effect can be consistent with
recognition, but converting the inhibition ratio into an affinity ratio would
require additional concentration dependence and kinetic assumptions. Locations:
Methods, melamine deaminase and AtzA competition; Results, corresponding two
competition sections.

## Comparability and isolation are separate

**Comparability outside the deliberately varied substrate:** within Table 1,
the protein identity, preparation class and total-protein normalization are
shared. Substrate concentration, saturation, initial-rate temperature, exact
reaction-buffer composition and per-substrate recovery are not explicitly given.
Different HPLC separations are described for alkylated and nonalkylated triazines.
Thus the rate ratios are usable measured preparation contrasts, but not
established kcat ratios or kcat/Km specificity ratios. A matched concentration
series with activity-normalized enzyme and explicit assay conditions would
resolve those distinctions.

**Isolation of the measured effect:** partial purification leaves potential
host-enzyme and chemical-background contributions. A matched preparation can
have excellent comparability yet incomplete attribution. Conversely, a highly
purified enzyme can be well attributed while compared under unmatched substrate
conditions. Quantitative blank rates, active protein concentration and purity or
cofractionation measurements would help measure attribution. The CAAT endpoint
also includes a spontaneous second step. No numerical proportion attributable
to TriA can be recovered here merely from the phrase “partially purified.”

Across TriA and AtzA inhibitor assays, baseline substrate and purity differ.
Their similar aminoatrazine inhibition percentages do not establish equal
affinity or equal catalytic function. An equimolar competitor/substrate ratio
does not establish equal [substrate]/Km across the enzymes.

## Sequence correspondence measured by this source

The printed full-length alignment has 475 amino acids per protein and nine
differences. The resulting identical-residue count is 466. Figure 3's boxed
positions are:

| Aligned position | AtzA | TriA |
|---:|:---:|:---:|
| 84 | F | L |
| 92 | V | L |
| 125 | E | D |
| 217 | T | I |
| 219 | T | P |
| 253 | I | L |
| 255 | G | W |
| 328 | N | D |
| 331 | S | C |

The nine positions are natural sequence differences, not a validated functional
site set. The source does not identify which one causes which activity change,
individual residue weights, epistasis, a structure comparison or phylogenetic
placement support. Counting all nine as mismatched “functional sites” would
select the denominator after seeing the mismatch and falsely import causal
information. Source: [Figure 3 and DNA-sequence Results](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/#F3).

The source reports nine nucleotide differences in a 1,425-nt coding region,
each producing an amino-acid substitution. Its rounded 99% nucleotide and 98%
protein identity descriptions are compatible with 1416/1425 and 466/475. These
are descriptive sequence fractions. Neither is a function probability.

## Uncertainty and inspection limits that affect the sheet

- Table 1's ± terms have no stated SD/SEM/CI interpretation in the inspected
  table, footnote or Methods. The inhibition ± terms likewise lack that
  definition. Figure 4 explicitly labels its own error bars SEM, n=2; that
  caption cannot silently supply the definition for Table 1 or the inhibition
  percentages.
- Duplicate and triplicate **samples** do not establish independent protein
  preparations, experiments or laboratories. The number of independent
  preparations is unknown.
- Figure 4's retained image visibly labels its y-axis **mM**, whereas the
  hydrolysis-product Results describe 100 μM starting melamine. This unit
  discrepancy is retained. No curve digitization or rate estimate was made
  from that figure. Its displayed time course and the Table 1 rates must not be
  treated as independent replication without preparation linkage.
- No Km, kcat, kcat/Km, Kd or Ki is reported in this paper. “Specific activity”
  is the available kinetic quantity; substituting one of those constants would
  fabricate information.
- The claim of AtzA's absence of deaminase activity points to an earlier
  specificity paper. That paper was not opened. The TriA table's detection
  limit is not borrowed for AtzA. This primary source supplies new AtzA
  inhibition percentages, but no paired Table 1-style AtzA specific-activity
  matrix.
- Exact mass spectra, chromatograms, raw replicate values, background rates,
  concentration series and protein purity fractions were not available in the
  inspected article. No extra source was assigned.

## A106 boundary

This paper contains no assayed engineered point-mutant series and no quantitative
restoration series. Nothing here establishes a single-substitution causal
effect. Any later engineered-mutant causality results belong to A106 and were
not imported. Cloning-associated expression and the host control can qualify
attribution of the actual A105 molecular assay; they are not counted again as a
separate A105 genetic-causality score. Growth and the native organism's ability
to metabolize a compound are not substituted for molecular conversion rates.
