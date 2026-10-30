# AF2372 conversion into the proposed A102 sheet

This is a new interpretation of the retained primary-specific packet, not a new primary-paper inspection. The prior packet and source limitations remain intact. It supplies a published row for the eventual cross-case sheet; it does not complete A102, alter the ten-axis checklist, or adopt policy.

## Definitions before scoring

The target-side example is AF2372 from *Archaeoglobus fulgidus*; the reference is MJ0109 from *Methanococcus jannaschii*. The measured objects are separate experimental structure models. The target is expressed in *E. coli*; strain, detailed construct and exact between-protein comparison chains/states are not recovered. These proteins are not co-mingled in a measured activity preparation. The intended difference is protein identity; crystal packing, ligand/metal state, modelling and construct differences can also affect the geometric comparison. The endpoint is a reported SEQUOIA RMSD over a selected superposition, not catalytic rate or functional identity.

The inspected packet is [AF2372_A102_conversion_001.md](../a102_native_structure_case_011/AF2372_A102_conversion_001.md), with its complete [numeric companion](../a102_native_structure_case_011/af2372_components_001.json). Its primary is [Stieglitz et al., 2002](https://doi.org/10.1074/jbc.M201042200). Original text/figure inspection claims belong to that packet's author; this conversion did not independently inspect paper pixels or rerun a structure comparison.

## Numerical conversion

| Sheet cell | Input and unit | Arithmetic | Result | Meaning |
| --- | --- | --- | ---: | --- |
| `native.rmsd` | Reported paired deviation | Preserve | 1.5 Å | Structural correspondence of selected positions |
| `native.matched_residues` | Reported paired residue count | Preserve | 209 | Extent belonging to this RMSD |
| `scope.target_length`, `scope.reference_length` | Paper's complete monomer lengths | Preserve | 252, 252 residues | Explicit coverage denominators |
| `coverage.target`, `coverage.reference` | Count / each monomer length | 209/252 | 0.8293650794 each | Residue extent; same numerator, not two independent observations |
| `coverage.symmetric` | Two matched counts / sum of lengths | 418/504 | 0.8293650794 | One symmetric extent summary |
| `geometry.rmsd_kernel_2A` | Native RMSD and proposed half-response scale 2 Å | 1/[1+(1.5/2)^2] | 0.64 | Explicit proposed compression of deviation, not a native TM-score |
| `pair.global_descriptor` | Extent × proposed geometric compression | (209/252)×0.64 | 0.5307936508 | Bounded pair descriptor for the scoring draft |

The 2 Å scale is a proposed operational convention for user judgment, not a measurement or calibrated probability. It gives half response to a selected-region RMSD of 2 Å. The prior packet exposed sensitivity to other scales; this draft selects a concrete convention so the arithmetic is defined. Native RMSD remains the scored measurement, with the transformation visible rather than replaced by a grade. The cross-case sheet must retain the method and atom-definition mismatch rather than assert universal comparability.

No functional-site correspondence number is available. No compatible native comparison to a competing characterized function has a recovered matched count. Therefore function-specific A102 contribution is not filled by the global descriptor alone. Under the proposed later product/contrast convention, its admissible function-specific support is a bounded unknown from zero to the global descriptor; a positive point contribution cannot be claimed from this packet. This is missing-data propagation, not a statement that the proteins fail to match.

## Comparability, isolation and weaknesses

Comparability concerns the model pairs' states and structural scope outside the intended protein difference. The reported within-AF2372 apo comparison and local loop movement show that state/packing can alter coordinates; they are not additive homolog evidence. Exact interprotein structure states are missing, so no numerical state correction is invented.

Isolation here means the readout establishes coordinate correspondence for its selected models. It does not establish the cause of an activity difference or unique substrate specificity. A site-specific geometric comparison, matched-state comparison and explicit competing-function comparison would answer distinct missing questions. Reference activity and experimentally occupied contacts can define which site/function the structure comparison bears on, but remain A105/A111 evidence rather than being copied into A102 numerical cells.

The source's multiple crystal forms and alternative superposition regimes are dependent representations. Molecular replacement used reference coordinates, which also prevents treating two experimental models as automatically independent. Quality diagnostics remain separate measurements; neither resolution nor `1-Rfree` becomes a structural-homology score. Atom selection, exact RMSD atomic denominator, pair map, exact compared chains and uncertainty are unknown. In particular, `209×1.5²` is not an observed squared-distance sum, and this descriptor is not reconstructed TM-score.

## Source trace and outstanding operands

| Input | Retained packet trace | Source scope |
| --- | --- | --- |
| RMSD, matched residue count, both lengths | S06; primary pp. 22868, 22870 | Narrative result; matrix not independently inspected |
| Alternative SEQUOIA regimes | S07; Table V p. 22872 | Caption/footnote; regime assignment to the narrative pair unknown |
| State/packing and local differences | S03–S05 | Same-protein diagnostics; no numerical site-transfer score |
| Structure-quality and molecular-replacement dependence | S02–S03 | Model diagnostics; exact pair-to-model join unknown |

The full reset after packet inspection is recorded in `authority_reset_001.json`. Arithmetic is included in the eventual shared check artifact. Essential unpublished/unrecovered operands stay null; no alignment/search/scientific episode was run. Next work is a contrasting primary row and a completely specified cross-case numerical sheet, not a broader source catalogue.
