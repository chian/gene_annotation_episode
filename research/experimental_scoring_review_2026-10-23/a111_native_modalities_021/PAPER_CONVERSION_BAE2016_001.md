# Bae 2016 conversion: local NMR restraint agreement

Research proposal, after reset R2. Goal: fill A111 D with a calculation grounded in actual local experimental restraints and preserve ensemble ambiguity.

[Bae et al., eLife 2016](https://elifesciences.org/articles/11273), DOI 10.7554/eLife.11273, NMR Results and Methods: synthetic isolated K1/K2 toxin lobes were measured separately at 1 mM, pH 4, 90% H₂O/10% D₂O. NOESY mixing time was 250 ms; acquisition used 298 or 310 K. Full-length labeled DkTx was a separate 0.4 mM sample. No WT/mutant coexistence is involved. NOE restraints came from assigned peaks; disulfide restraints came from homology. Twenty retained conformers per lobe were selected from 100 calculated models. These models are not twenty experiments. K1/K2 have different sequences and lengths; a single-residue causal contrast is not isolated. Ensemble spread is not population occupancy or independent precision.

## Native local cells

Use a declared two-restraint panel supporting a local Trp geometry and its cross-loop approach: (1) Trp11 HA–HD1 and (2) Trp11 HE1–Ile HA. K1 Ile is residue28; K2 is residue26 in the deposit (Ile68 in full DkTx). K2 Trp11 is full DkTx Trp53; the coordinate offset is explicit. All four selected assignments name one proton per endpoint, avoiding an unverified methyl/OR averaging convention. The selected restraints are not a complete validation of the whole knot.

| Native cell | K1, 2N9Z | K2, 2NAJ |
| --- | ---: | ---: |
| Deposited scalar restraint bounds, internal Trp | [0,4.43] Å | [0,4.18] Å |
| Deposited scalar restraint bounds, cross-loop | [0,5.50] Å | [0,4.73] Å |
| Representative model from validation XML (medoid) | 9 | 3 |
| Internal Trp distance in that model | 4.078006375669366 Å | 4.516511596353982 Å |
| Cross-loop distance in that model | 3.1168435956909994 Å | 3.531800957018955 Å |
| Internal restraint violation | 0 Å | .336511596353982 Å |
| Cross-loop restraint violation | 0 Å | 0 Å |
| Internal Trp distance across 20 models | 3.0913894934155417–4.4708640104570385 Å | 4.474157574337319–4.529279633672445 Å |
| Cross-loop distance across 20 models | 2.203830755752356–5.466535557370866 Å | 2.6956501998590245–4.225209817275350 Å |

Native restraint files: [2N9Z](https://files.rcsb.org/download/2n9z.mr), lines186 and569; [2NAJ](https://files.rcsb.org/download/2naj.mr), lines211 and39. `assign ... t l u` specifies [t−l,t+u], so these displayed 4.43/4.43/0 and 4.18/4.18/0 operands are upper bounds, not a measured central distance with ±0 error. The current [2NAJ validation XML](https://www.ebi.ac.uk/pdbe/entry-files/2naj_validation.xml) independently reports restraint175 at model3 as a .34 Å violation (printed precision), consistent with coordinate-derived .3365116 Å. This does not treat absence from a thresholded violation list as exact zero. The zeros above were calculated from the selected complete restraint/coordinate pairs.

## Explicit proposed conversion and chain

For each required experimental restraint j and one named model m, `v_jm=max(0,L_j−d_jm,d_jm−U_j)` in Å; `s_jm=exp[−v_jm²/(2τ_j²)]`, with the explicit proposal τ_j=.50 Å. `D_m=(s_1m+s_2m)/2`. This is local restraint agreement conditional on the selected assignments/model. τ is a scoring tolerance, not an experimental SD; no probability calibration is claimed. D is not deduced from ensemble RMSD or total restraint count.

K1 representative D=1. K2 representative D=(1+exp[−.336511596353982²/.5])/2; the exact checked value is in ARITHMETIC_RESULTS_001.json. For an illustrative physical predicate “cross-loop proton distance ≤4.0 Å”, G=1 for both representative models. That threshold is a declared geometry question, not an activity threshold. q=C=I=1 are strictly conditioned on that deposited model and its assigned atoms. T remains unknown without actual target mapping, so each target contribution remains null with [0,D] bounds.

Across the entire ensemble, some models exceed 4 Å in both cases, so the physical G envelope is [0,1]; do not choose the shortest conformer. Any model-conditional point must retain its model identity, and a model-independent point is null. The 20 model scenarios contribute one experimental dataset, not twenty cluster means. Use the minimum/maximum of complete scenario products, varying shared atoms/restraints jointly. An NMR ensemble selected for fit does not determine physical conformer weights.

Complementary measurements that address the remaining weaknesses include measured peak intensities/uncertainties and alternative assignments for ambiguous NOEs, independent experimental restraints withheld from model fitting, and matched full-length measurements if inferring full-length behavior. Homology-imposed disulfides and generic force-field terms never become experimental D inputs. Chemical-shift similarity can inform measured condition/construct comparability when numeric values are available; a prose claim of near identity cannot populate those values.

These local structural restraints do not measure affinity, efficacy or transport. The paper’s functional assays remain on their own axes. Its reuse of original cryo-EM maps and of these NMR restraints in docking is dependent reuse, not new independent experimental support.
