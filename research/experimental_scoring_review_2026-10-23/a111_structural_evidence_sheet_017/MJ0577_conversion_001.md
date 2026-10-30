# MJ0577 source-to-sheet conversion, proposed

Source: Zarembinski et al., 1998, DOI [10.1073/pnas.95.26.15189](https://doi.org/10.1073/pnas.95.26.15189); [PDB 1MJH](https://www.rcsb.org/structure/1MJH), DOI 10.2210/pdb1mjh/pdb. This is a source example, not a result on the project's target. Full authority reset 001 preceded this conversion.

## Experimental definition and coverage

The native-sequence *M. jannaschii* protein was expressed in *E. coli* BL21(DE3) SJS1244 and purified. Crystallization contained MnCl2; ATP was not added. A selenium derivative supplied phasing. The final native diffraction model contains two protein copies and two ATP/metal sites. Those copies coexist in one crystal and share diffraction/refinement; they are not two independent preparations. The measured endpoint is scattering interpreted as atomic coordinates, not an affinity or catalytic rate. The comparison here is the physical ATP/coordination/assembly description against the coordinate and local-density data. No controlled ATP-versus-no-ATP structure series was reported.

Inspected: all five primary-paper PDF pages as text; visual pages 15190–15191 including Tables 1–2 and Figures 1–3; current 1MJH entry metadata; complete ATP/MN atom rows; validation Entry attributes and all ATP/MN ModelledSubgroup records. No re-refinement, raw diffraction reconstruction or independent electron-density inspection was performed. Figure 3 was viewed, but its alignment was not transcribed into a supplied-target mapping.

## Native and calculated cells

| Cell | Native input and location | Value / calculation | Meaning and qualification |
|---|---|---|---|
| Structural state | Paper Methods; 1MJH record | 100 K diffraction; Mn added during crystallization | State scope; not native intracellular occupancy |
| Model occupancy | `_atom_site.occupancy` for each ATP and MN atom | 1.00 at both sites | Model parameter. Independent occupancy refinement and uncertainty are not established by this inspection |
| Local density fit | Validation ATP A2001 / B3001 | RSCC 0.963 / 0.958; RSR 0.065 / 0.071 | Local calculated/observed map agreement; not an identity or function probability |
| Proposed local fit factor | `max(0,RSCC)^2` | 0.927369 / 0.917764; mean 0.9225665 | Squared correlation as a model/map agreement index, explicitly proposed; the two copies are averaged, never summed as replications |
| Metal coordination | Paper p15192; coordinate distances in `1MJH_source_calculations_001.json` | Six O neighbors per site within the declared research radius 2.6 Å; A range 2.2554–2.3823 Å, B 2.2765–2.3807 Å | Three phosphate and three water oxygen atoms. Geometry supports this contact description; it does not uniquely identify the metal |
| Proposed geometry compatibility | Six distances in [2.0,2.6] Å; 15 pair angles within 15° of 90° or 180° | 6/6 and 15/15 at both sites | Explicit example tolerances, not estimated errors or universal metal-bond thresholds |
| Modeled-residue fraction | 287 modeled / 324 deposited across both chains | 0.8858024691 | Missing-loop coverage. It must not be multiplied as a global penalty if the tested contact feature lies outside the missing loop |
| Crystal interface | Paper p15192 | 1,056 Å² per monomer; reported 15% buried | Geometric extent of the crystal dimer. Two chains in a deposit alone do not establish an obligate solution dimer |
| Native model statistics | Paper Table 2; current deposit | Paper Rwork 20.6%, Rfree 24.9%; deposit 0.210 / 0.254 | Preserve both versions. Never substitute `1-Rfree` for evidence reliability |

The paper's table and narrative differ in water count and rounded refinement statistics. Those representations are preserved, not averaged. Current atom records are the authority for this packet's coordinate calculations. Validation reports show local ligand geometry outliers; the inspected whole-entry statistics do not erase them.

## Conversion into the user's numerical sheet

The scored unit is one specified physical feature on the measured molecule, followed by a stated target correspondence. For the coarse feature “an ATP-shaped nucleotide is modeled at this pocket in this crystal state,” the proposed source-model index is the copy average of occupancy × squared RSCC × declared geometry compatibility. With the stored model occupancy and the example geometry definition it is `1 × 0.9225665 × 1 = 0.9225665`. This is conditional on the deposited atom assignment and model occupancy. It is **not** a 92.26% probability of ATP binding, catalysis, physiological ligand identity or any target function.

The joined target cell multiplies that source index by the measured fraction of the feature's mapped atom/residue roles retained in the supplied target, plus a separately evaluated state/comparison factor only when the inference requires a cross-state comparison. No target was supplied for this research example: the transfer cell is unknown, not an invented homolog weight. Its nominal target score is null; the logical envelope from the absent [0,1] transfer input is [0,0.9225665]. This bound is not a confidence interval.

The resolved physical feature can constrain an emerging annotation even if several functional interpretations remain. ATP occupancy does not distinguish an ATPase from a noncatalytic ATP-binding protein. The specific catalytic discrimination cell therefore receives zero difference from this feature for that stated pair of interpretations. That zero does not erase the measured occupancy information or manufacture a negative catalytic experiment. Any biochemical assay is a separate A105 measurement.

Comparability and effect isolation remain different. There is no controlled structural state comparison to justify an ATP-triggered conformational difference here. Isolation of the observed contacts is chain/atom specific, but physiological metal identity remains uncertain because the metal was supplied during crystallization and geometry is not elemental analysis. Independent anomalous/elemental evidence could resolve identity. A controlled structural comparison could address state changes; solution assembly measurements could address whether the crystal interface persists outside the crystal. These would complement this structural observation, not duplicate its diffraction dataset.

Missing inputs: target material/mapping; occupancy precision/refinement provenance; independently refined competing ligand/metal models; quantitative uncertainty of site distances and interface area; a controlled structural state comparison; independent solution assembly measurement. These omissions do not impose mandatory further experiments or stop an episode. The joined sheet must retain a conditional nominal value, unresolved intervals and the exact narrow feature supported.
