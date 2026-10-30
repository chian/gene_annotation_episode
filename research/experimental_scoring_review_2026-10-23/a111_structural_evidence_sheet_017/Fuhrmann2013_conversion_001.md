# A111 source conversion: Fuhrmann 2013

PROPOSED scoring research, converted after the complete post-paper authority reread recorded in `receipts/Fuhrmann2013_reset_001.json`. No target annotation or axis acceptance is claimed. The paper supplies experimental facts; the formulas below are proposed conversions into numerical cells.

Source: [Fuhrmann et al., DOI 10.1016/j.celrep.2013.05.023](https://doi.org/10.1016/j.celrep.2013.05.023); [retained repository PDF source](https://www.diva-portal.org/smash/get/diva2:642408/FULLTEXT02.pdf). Depositions [4KK3](https://www.rcsb.org/structure/4KK3) and [4KK4](https://www.rcsb.org/structure/4KK4), including their mmCIF atom tables and wwPDB validation XML, are the sources of the coordinate-derived numbers. These are complementary representations of the two crystallographic determinations, not extra experiments.

## Experimental definitions

The measured molecule is Bacillus subtilis YwlE. Structural protein production used an E. coli expression system; this is not a measurement of the supplied annotation target. The wild-type phosphate complex, 4KK3, contains selenomethionine at four positions. The C7S construct, 4KK4, was preincubated with 10 mM phosphoarginine and is deposited with phosphoserine SEP7. An actual covalent modified serine in this mutant is distinct from direct observation of phosphocysteine in wild type. Neither deposited structure supplies an intact freely supplied phosphoarginine ligand occupying the active site.

Arg149 from a symmetry-related protein molecule enters the active-site region. This is a physically modeled intermolecular crystal contact and a substrate-recognition mimic; it is not an independent molecule of substrate demonstrated in solution. Each dataset has one protein molecule per asymmetric unit. Crystal copies are not experimental replicates.

For a **single-state feature**, the endpoint is a specified density-supported atom assignment or a specified distance in that construct and crystal state. The intentional comparison variable in a **between-state inference** is C7S versus wild type. Additional differences include pH, PEG concentration, methionine chemistry, and the extra terminal residue in the mutant deposition. These do not vanish because both structures concern YwlE. Isolation of a mutation's effect requires a separate estimate of the effects of those changes.

## Native and derived cells

| Cell | 4KK3 | 4KK4 | Definition and scoring use |
| --- | ---: | ---: | --- |
| Resolution | 1.7 Å | 1.8 Å | Dataset context, not a reliability probability or multiplier |
| Rwork / Rfree | 0.1857 / 0.2184 | 0.1725 / 0.2154 | Global refinement diagnostics, not local ligand support |
| Relevant ligand/modification | PO4 A201 | SEP A7 | Actual deposited identity; chemical identity alternatives have not been re-refined |
| Model occupancy | 1 | 1 | A coordinate-model parameter; uncertainty and whether occupancy was freely refined are unestablished here |
| Local RSCC | 0.967 | 0.934 | Correlation of calculated and observed local density reported by validation |
| Local RSR | 0.079 | 0.097 | Native local residual retained independently of RSCC |
| Proposed local fit index D = max(0, RSCC)² | 0.935089 | 0.872356 | Dimensionless local model/map agreement; explicitly not a function probability |
| Arg149 local RSCC | 0.773 | 0.907 | The contacting residue has its own density support |
| Contact D = min(ligand RSCC, Arg149 RSCC)² | 0.597529 | 0.822649 | A joint contact uses the weaker local endpoint support once; it is not the product of two independent experiments |
| Crystal pH | 7.7 | 6.2 | Nuisance difference 1.5 pH units for a C7S comparison |
| PEG400 | 25% | 30% | Nuisance difference 5 percentage points |
| Crystallization / diffraction temperature | 292 K / 100 K | 292 K / 100 K | Reported matching variables; these are distinct temperatures |
| Canonical deposited length | 151 | 152 | Full identity retains the additional terminal residue |

The following distances are calculated from retained atom coordinates, with Arg149 translated by one unit-cell b vector: `(x,y+40.749,z)` Å for 4KK3 and `(x,y+39.340,z)` Å for 4KK4. They are not newly measured solution distances. Values have coordinate precision, not a supplied standard error.

| Derived geometric cell | 4KK3 | 4KK4 |
| --- | ---: | ---: |
| Arg149 NH2 to ligand P | 4.262179 Å | 4.136354 Å |
| Arg149 NH1 to Thr11 OG1 | 3.813131 Å | 3.195249 Å |
| Arg149 NH2 to Asp118 OD2 | 2.458451 Å | 2.916031 Å |
| SEP7 P–OG internal bond | — | 1.681567 Å |
| Arg149 NH2–P–SEP7 OG angle | — | 145.871604° |

The internal P–OG bond rounds to the validation report's 1.68 Å, providing a coordinate/validation cross-check. The current deposited NH2–P–OG angle is **not** 180°. The paper's geometric illustration is not substituted for this explicitly named current-coordinate calculation. No claim that this reproduces a particular Figure 4 atom labeling, coordinate version, or reported superposition displacement is made. A search over the C2-related Arg149 guanidinium atoms and nearby cell translations found the stated y+b neighbor closest to the selected P atom; NH1 gives 142.859279° in 4KK4. Remaining figure/version correspondence is a source limitation, not an undefined calculation. In particular the between-structure P–NH2 distance difference, −0.125826 Å, is not the displacement of Arg149 after structural alignment. The paper's reported approximately 1.5 Å repositioning is not inferred from subtracting these two distances.

Validation also reports SEP7 P–OG bond Z = 2.63, bond RMSZ 1.91, angle RMSZ 3.69, a Cα–Cβ–OG angular Z = 8.49, and a phosphate-oxygen/backbone-N clash of 2.42 Å. These are relevant qualifications to the modeled covalent geometry. They do not become an invented universal truth probability, and a strained geometry need not disprove a catalytic intermediate. Raw local validation attributes are retained in `ARITHMETIC_RESULTS_001.json`. No complete mandatory validation-panel gate is proposed.

## Conversion into the sheet

For the limited feature **a deposited phosphate-bearing group with local map agreement in the specified crystal**, a model-conditional source component is `q_model × D`. It is 0.935089 for PO4 and 0.872356 for SEP. This is not chemical-identity certainty; the true occupancy interval remains unknown if free refinement and its uncertainty were not supplied. For a target contribution, a feature-specific correspondence factor T must also be populated; it is unknown here. Conditional target envelopes therefore remain `[0,0.935089]` and `[0,0.872356]` with no point score for an actual target.

For the narrow feature **the specified Arg149–Asp118 contact is within 3.2 Å**, the geometric predicate G equals 1 for both deposits. The 3.2 Å boundary defines this illustrative contact question; it is not a calibrated bond probability or a universal structural-quality threshold. The density support for a contact must include both ends: `D = min(RSCC_Arg149, RSCC_Asp118)²`, giving the same 0.597529 and 0.822649 values because Arg149 is weaker in both. This contact does not establish binding affinity. A predicate requiring a freely added phosphoarginine substrate at those atom roles receives **zero matching atom roles**, since Arg149 belongs to the crystal neighbor. That zero is an entity mismatch count, not a qualitative relevance grade.

The proposed paired-comparison calculations distinguish comparability and effect isolation:

- With declared illustrative nuisance scales τpH = 1 pH unit and τPEG = 10 percentage points, `c_pH = exp(−0.5×1.5²)`, `c_PEG = exp(−0.5×(5/10)²)`, and `C_two = sqrt(c_pH c_PEG) = 0.535261429`. These scales are proposal assumptions, not uncertainties reported by the paper.
- An explicitly declared four-component illustration additionally uses temperature agreement 1 and construct-chemistry matching `146/151`: exclude intended C7S; count the four MSE→MET differences and one terminal insertion among 151 non-intended union positions. Its geometric mean is `C_four = 0.725482518`. The changed denominator is visible. It is not claimed to cover every possible experimental difference or to estimate an effect size. Adding irrelevant perfectly matching conditions merely to raise C is prohibited by the declared comparison definition.
- Separately, `I = max(0, 1 − B/|Δ|)` would quantify how much of a measured between-state difference cannot be accounted for by a measured nuisance-effect bound B. B is absent. Thus **I is unknown**, and C cannot manufacture an isolated mutation-effect score. The actual within-state structural features remain usable with their limited meanings.

The same crystallographic observations inform the feature, contact and mechanistic illustration. They are one dependent evidence family; separate figures, depositions and prose representations do not create three independent supports. The two states are distinct diffraction datasets, but the mutant's molecular-replacement model and common construct/analysis make model dependence relevant; the joined sheet conservatively groups their structural attribution evidence together unless independence for a specific quantity is separately established. Biochemical substrate assays and mutation effects reported elsewhere in this paper are not inserted into A111 as duplicate structural confirmation. They belong to A105/A106 under their own measurements.

## What remains unmeasured here

No supplied-target mapping, local alignment ambiguity, raw-density reanalysis, alternative ligand identity fit, occupancy uncertainty, quantitative nuisance-effect bound, independent solution assembly measurement, or supplementary Tables S1–S2 inspection is available. Those omissions create named nulls and bounded intervals, not a request for a required experiment, an episode gate, or a guessed 0.5. Complementary anomalous/chemical identity measurements could address atom identity; alternate-model refinement could address model preference; solution binding/kinetics could address affinity or catalytic activity; matched-state structural controls could address the comparison's confounds. None has been fabricated.

The arithmetic is reproduced by `research_arithmetic_001.py` and retained in `ARITHMETIC_RESULTS_001.json`.
