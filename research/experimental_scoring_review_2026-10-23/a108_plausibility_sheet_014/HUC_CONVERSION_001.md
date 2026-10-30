# Huc primary-to-sheet conversion, after full reset 01

Primary: Grinter et al., 2023, *Structural basis for bacterial energy extraction
from atmospheric hydrogen*, DOI [10.1038/s41586-023-05781-7](https://doi.org/10.1038/s41586-023-05781-7).
Read through Europe PMC full-text XML. This is a selected Results/Methods read,
not a claim to have inspected all figures, supplements or source-data workbooks.

## Experimental definitions

Studied material is purified Huc from *Mycobacterium smegmatis* mc2 155 PRC1,
with a chromosomal HucS 2×StrepII tag. The production strain has a gylR frameshift
and inactivated hhyS; it is not unmodified wild type. Huc and comparison E. coli
Hyd1 are in separate vials, not a mixture. The comparison deliberately changes
the enzyme. It does not isolate an organism-level survival contribution.

For Huc plus menadione, Methods specify 5 mL buffer in a 120 mL vial, pH 8,
0.3 mg/mL BSA, 200 µM menadione, 100 nM Huc, room temperature with stirring, and
an initial headspace of 3 ppm H2 in an atmospheric gas mixture. The measured
endpoint is residual gas H2, with a detector limit of about 40 ppbv. No-enzyme
controls showed no H2 loss. Biological replication is four Huc preparations
per acceptor; three replicate vials per preparation are technical replication.
The plotted Fig. 1a,b errors are SD of three technical replicates from one
preparation, not SD across four preparations.

The paper's main text compares Huc depletion below about 40 ppbv with Hyd1
cessation around 4 ppmv. However, the comparison Methods specify 50 nM enzyme,
200 µM NBT and 10 or 100 ppm H2 in N2, rather than the menadione/atmospheric-gas
conditions above. Hyd1 has one preparation and three technical vials; it was
preactivated under 7% H2 in N2 for 18 h. Do not silently call that matched proof
about Hyd1 in air. This qualification is experimental comparability. Separately,
enzyme purification plus no-enzyme controls address attribution of depletion;
they do not establish the sampled organism's environmental access or maintenance
energy sufficiency.

## Numerical conversion

The reported atmospheric benchmark is 530 ppbv H2 with about 21% oxygen. It is
background context cited by the paper, not a new habitat measurement made in
this review and not the measured habitat of the project's target.

| Cell | Native operand and unit | Calculation | Result and meaning |
|---|---|---|---|
| `context_h2_benchmark` | 530 ppbv | 530/1000 | 0.530 ppmv; unit conversion |
| `huc_depletion_bound` | residual H2 <~40 ppbv | retain censoring | upper bound on observed residual, not zero H2 |
| `huc_context_margin_lower` | 530 ppbv / 40 ppbv | ratio | >~13.25; atmospheric benchmark exceeds the residual bound |
| `hyd1_context_margin` | 530 ppbv / ~4000 ppbv | ratio | ~0.1325; only a conditional comparison under the NBT/N2 experiment |
| `huc_tested_start` | 3 ppmv | 3×1000 | 3000 ppbv |
| `huc_independent_preparations` | independent preparations | count unique preparation units | 4; not 12 |
| `hyd1_independent_preparations` | independent preparations | count unique preparation units | 1; not 3 |

Proposed scoring use: define a **condition-specific supported exposure domain**
from a measured operating endpoint, retaining both gas and liquid conditions.
For a narrow Huc benchmark calculation, monotone depletion provides a proposed
interpolation domain from approximately 40 to 3000 ppbv at the matched buffer,
acceptor, gas mixture and temperature. The 530 ppbv benchmark lies within it.
This membership becomes one operand of the joint exposure-compatibility
calculation in the current sheet. The ratio 13.25 is an interpretable margin,
not annotation confidence and not an extra contribution to be added to domain
membership. The quantitative molecular assay remains A105 evidence; A108 uses
its range only as a referenced condition requirement.

Huc oxygen experiments used 0%, 10% and 100% O2 saturation, with the last two
reported as approximately 0.12 and 1.2 mM. These are solution saturation levels,
not 0%, 10% and 100% atmospheric O2 volume fractions. The main text reports no
significant rate/affinity difference; no numerical equivalence interval follows
without the replicate values. Therefore no invented O2 retention multiplier is
filled. Likewise Km=129 nM is not a minimum ecological concentration, and the
fraction C/(Km+C) would not by itself measure whether atmospheric H2 can supply
a maintenance role.

## Remaining operands and boundaries

No target sample's H2/O2 distribution, microenvironment, local accessibility,
temperature distribution, intracellular effective exposure or maintenance flux
has been supplied. A full target A108 score remains unknown; the narrow source
benchmark can be filled conditionally. The current draft must demonstrate a
complete calculation with clearly synthetic matched context observations.

Measurements of physical access and exposure would address the environmental
gap. Separate whole-cell measurements could address native system transfer, but
none are commissioned here. The paper's cited older whole-cell kinetics are
secondary mentions, not newly inspected primary evidence. Cryo-EM occupancy,
the menaquinone transport mechanism, partner subunits and thermodynamic redox
accounting do not earn additional A108 components: those belong to A111, A107
and A110 as appropriate. No artificial phylogenetic/clade score is assigned.
