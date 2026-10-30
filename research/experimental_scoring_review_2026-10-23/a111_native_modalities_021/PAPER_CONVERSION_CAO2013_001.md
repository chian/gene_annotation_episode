# Cao 2013 conversion: cryo-EM local observation, distinct agonist states

Research proposal, after reset R1. Goal: populate the existing A111 observation/physical-feature cells from two contrasting structures while preserving what is missing for transfer.

Source: [Cao et al., Nature 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC4023639/), DOI 10.1038/nature12823, especially Results “Structures of TRPV1-ligand complexes”, outer-pore section, Extended Data Fig.8, and Online Methods. The paper studies purified minimal rat TRPV1 in amphipols: 5 µM channel plus either 50 µM RTX and 10 µM DkTx, or 50 µM capsaicin, incubated 30 min. This is no WT/mutant competition. The intended contrast is agonist condition; a toxin-specific effect is not isolated because both small ligand and DkTx change. Resolutions 3.8/4.2 Å and final particle counts 36,158/33,238 describe whole reconstructions, not local occupancy or independent biological replicates. Models share the apo starting structure. The paper explicitly lacks detailed ligand poses; the toxin was initially polyalanine.

## Native dataset cells and precise geometry

The selected physical predicate is deliberately narrow: “the model-assigned diagonally opposed G643 carbonyl oxygens are separated by at least 6.0 Å.” The 6.0 Å threshold defines this illustrative structural question; it is not a calibrated conduction threshold. Both opposing diagonal pairs are included, with equal within-dataset weights.

| Deposit / pair of author chain labels | Current retained O–O distance, Å | Local residue Q-scores from retained validation XML | Proposed D = min(max(0,Q))² | Physical event | G for that event |
| --- | ---: | --- | ---: | --- | ---: |
| 3J5Q D/E, RTX+DkTx | 7.73105458524256 | .385 / .395 | .148225 | supports distance ≥6.0 | 1 |
| 3J5Q B/G, RTX+DkTx | 7.768594918001582 | .374 / .430 | .139876 | supports distance ≥6.0 | 1 |
| 3J5R B/C, capsaicin | 4.157251375608648 | .337 / .338 | .113569 | incompatible distance <6.0 | 1 |
| 3J5R A/D, capsaicin | 4.713740446821399 | .315 / .372 | .099225 | incompatible distance <6.0 | 1 |

Dataset copy means: 3J5Q D=.1440505; 3J5R D=.106397. The [3J5Q validation XML](https://www.ebi.ac.uk/pdbe/entry-files/3j5q_validation.xml) and [3J5R validation XML](https://www.ebi.ac.uk/pdbe/entry-files/3j5r_validation.xml) provide `ModelledSubgroup/@Q_score`, keyed by model/chain/resnum/icode/altcode. Residue-level Q is the granularity actually available; it does not establish the individual oxygen or side-chain assignment as an independent measurement. The Q² transform is an uncalibrated proposed local resolvability index, not a correctness probability.

The original paper reports G643 separations 7.6 Å versus 4.6 Å. Those are retained as a different representation from the exact current deposited coordinate calculations above; they are not averaged, and paper geometry is not silently joined to a newer model validation. For this table, the explicit reconciliation choice is the retained current coordinate/validation pair. Coordinates: [3J5Q](https://files.rcsb.org/download/3j5q.pdb), [3J5R](https://files.rcsb.org/download/3j5r.pdb). Source-native global Q (.217/.200), global FSC and map thresholds are diagnostics only.

## Existing chain, scope and missing inputs

For each named deposited state, q=1 means conditional model state, C=1 is the empty comparison, and I=1 means conditional on those model atom identities. Thus the source-local products are .1440505 and .106397 in magnitude. No target material/mapping was supplied to this source case: T remains null [0,1]. The target contributions are therefore null [0,.1440505] and null [−.106397,0], respectively. These are different agonist states, not contradictory repetitions of the same conditional proposition. An explicitly declared broader “both agonist states have this width” question may retain both with their distinct scopes and equal state weights; it may not erase the conditions.

For a toxin-causes-widening comparison, nuisance similarity C can include documented matched concentration and timing with any explicit positive τ (differences zero give component 1), but the causal I is null without a bound on the RTX-versus-capsaicin contribution. High C cannot supply I. A toxin-only matched comparison would address that limitation; new such measurements are not invented. Refined occupancy or an unbiased particle denominator is absent: neither selected-class fraction nor fixed atom occupancy is a solution-state occupancy estimate. Physiological transport is A105; mutations are A106.

D uses actual local validation. G evaluates the declared physical spacing. T evaluates the specific target feature correspondence. Their product remains one chain. Symmetry copies, paper/renderings and validation do not add independent experiments. Missing ligand density without calibrated sensitivity cannot populate N. Alternative ligand identities and model bias remain explicit qualifications; a binding affinity is not inferred.
