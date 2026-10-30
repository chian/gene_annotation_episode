# AF2372: a primary-paper conversion for A102 numerical cells

This packet supplies one worked source conversion for the active ten-sheet goal. A105 remains first and unfinished. It does not adopt an A102 aggregate, complete a scoring sheet, implement a reader, or establish a relationship to the current annotation target. The example uses AF2372 as the target-side protein and MJ0109 as its characterized reference. The inspection and reset receipts are `inspection_coverage_001.json` and `authority_reset_001.json`; the numerical companion is `af2372_components_001.json`.

**Experimental definitions come first.**

| Definition | What this source establishes | Remaining boundary |
| --- | --- | --- |
| Target-side protein | AF2372 from *Archaeoglobus fulgidus*, expressed in *E. coli* and examined by X-ray crystallography | Source/expression strains, complete construct/tag details and genotype are not specified here; cloning is referred elsewhere. No engineered AF2372 variant is described. |
| Reference protein | Previously structurally and biochemically characterized MJ0109 from *Methanococcus jannaschii* | Original MJ0109 activity papers were not independently reread. Their assay values are not structural-score inputs. |
| Structures | Experimental structures, not predictions; AF2372 has two apo crystal forms and three ligand/metal conditions in this paper | The selected AF2372 and MJ0109 coordinate entries, chains and ligand states for the reported between-protein superposition are not identified in the recovered narrative. |
| Depositions versus actual comparison operands | AF2372 deposition set: 1LBV, 1LBW, 1LBX, 1LBY, 1LBZ. MJ0109 1DK4 was the molecular-replacement probe used to solve AF2372. | A phasing-probe identifier is not proof that that entry or a particular chain was the Table V comparison operand. Keep these fields separate. |
| Whether both proteins coexist | The comparison concerns separate coordinate models of different proteins. AF2372 itself is dimeric. | This is not an AF2372/MJ0109 mixture experiment, replacement experiment, or coexpression experiment. |
| Intended comparison | Structural correspondence across the two proteins | This is not a controlled intervention isolating a residue's causal effect. Ligand state, lattice packing, experimental conditions and modelling can also influence coordinates. |
| Endpoint | SEQUOIA's reported RMSD and number of superposed residue positions | An RMSD is geometric agreement for the selected positions. It does not measure enzymatic activity, affinity, physiological role or probability of the same function. |

Source: [Stieglitz et al., JBC 277, 22863–22874 (2002)](https://doi.org/10.1074/jbc.M201042200), pp. 22863–22865 and 22868–22870. Bibliographic identifiers: DOI `10.1074/jbc.M201042200`; PMID `11940584`. The corpus entry was used for citation metadata only, not its earlier interpretation.

**The reported structural comparison supplies actual numbers.**

| Numerical cell | Reported input or calculation | Value | Meaning and limit |
| --- | --- | ---: | --- |
| Between-protein RMSD, `C01.value_angstrom` | AF2372 versus MJ0109; SEQUOIA superposition | 1.5 Å | Original comparison output, lower meaning closer geometry for its selected positions. Not a whole-protein RMSD or an annotation-confidence value. |
| Matched extent, `C01.superposed_residue_pairs` | Number of superposed positions reported alongside that RMSD | 209 residue pairs | Count of correspondence, not 209 independent experiments. The actual pair map is unavailable. |
| Target denominator | Paper-stated AF2372 monomer length | 252 residues | Explicitly reported length, not inferred from the aligned count. Not independently checked against a sequence or coordinate file. |
| Reference denominator | Paper-stated MJ0109 monomer length | 252 residues | Same denominator qualification. |
| Target coverage | 209 / 252 | 0.8293650794 | Fraction of the reported target length represented in this superposition. |
| Reference coverage | 209 / 252 | 0.8293650794 | Fraction of the reported reference length represented in this superposition. |
| Single symmetric coverage summary, proposed | 2 × 209 / (252 + 252) | 0.8293650794 | One extent term if a symmetric pair descriptor is useful. It does not create an additional observation. |
| Residues outside the reported superposition | 252 − 209, for either protein | 43 residues | No assertion that these residues are absent, unstructured, experimentally unresolved, or functionally dispensable. |

These operands occur in the paper's structural-comparison Results on pp. 22868 and 22870. [Primary source](https://doi.org/10.1074/jbc.M201042200).

For a geometric RMSD, the conceptual numerator is the sum of squared distances between paired coordinate points after superposition; the denominator is the number of those points, followed by a square root:

`r = sqrt(sum(j=1..M, ||R*x_j + t - y_j||^2) / M)`.

The inspected text gives a residue-position count but does not explicitly specify the atom selection or atomic-point denominator for this between-protein comparison. Therefore `M`, the atom selection, per-point distances and the summed squared distances remain null. In particular, do not compute `209 × 1.5²` as an observed atomic sum without establishing that the RMSD uses exactly one point for each of those positions. The C-alpha definition supplied for a different, within-AF2372 comparison cannot silently fill this gap.

Table V's footnote distinguishes an upper, final superposition at a 3 Å cutoff and 30° continuation from a lower, total superposition at an 8 Å cutoff and 80° continuation. Its matrix is an image. The available screenshot calls returned text markers rather than inspectable images, so that matrix was **not** visually read. The narrative's 1.5 Å/209 result cannot yet be assigned confidently to either parameter regime, exact coordinate entry or chain. The numerical narrative result itself is present and usable with that limitation. No structural alignment was rerun.

**An explicit proposed combination, confined to these source components.**

To show how the native geometry and its extent could enter numerical compilation, a component-level proposal is:

`c = 2*N/(L_target + L_reference)`

`g(r,d) = 1/(1 + (r/d)^2)`

`b(d) = c × g(r,d)`.

Here `N` is the reported number of matched residue pairs; the two `L` values are the reported complete monomer lengths; `r` is the reported RMSD in Å; and `d > 0` is an explicit distance scale in Å. The transformation and distance scale are **proposed scoring choices**, not measurements or a method adopted from this paper. `c` evaluates extent and `g` compresses the selected-region deviation. Their product is a pair descriptor, not an overall A102 grade or a probability of functional transfer.

| Illustrative scale, not a default | Geometry term `g(1.5,d)` | Coverage × geometry `b(d)` |
| --- | ---: | ---: |
| d = 1 Å | 4/13 = 0.3076923077 | 209/819 = 0.2551892552 |
| d = 2 Å | 16/25 = 0.64 | 836/1575 = 0.5307936508 |
| d = 3 Å | 4/5 = 0.8 | 209/315 = 0.6634920635 |

All paper inputs are unchanged across these rows. The variation exposes the uncalibrated scale choice; it is not evidence uncertainty. There is no selected default scale in the machine-readable packet. This function of a single RMSD is **not a TM-score**: that score cannot be reconstructed from an aggregate RMSD and a matched count alone. The descriptor also cannot replace a local functional-site comparison or solve the unknown structure-state pairing. Raw RMSD and coverage remain available without this proposed transformation.

Use the product as one numerical view of this comparison if its scale is later justified. Do not sum native RMSD, both coverages and the product as independent support. A complete A102 formula still needs function-specific discrimination and justified treatment of structure quality and local correspondence; this packet does not fill them with category grades.

**Local differences qualify what that correspondence can transfer.**

| Local cell | Reported operands | Derived value | What it evaluates |
| --- | --- | ---: | --- |
| AF2372 second N-terminal helix span | Residues 44–58, inclusive | 15 residues | Length of that reported structural element. |
| MJ0109 corresponding helix span | Residues 45–54, inclusive | 10 residues | Length of the compared structural element. |
| Helix span difference | 15 − 10 | 5 residues | An architectural difference despite the conserved overall structure. |
| Shorter/longer helix span | 10 / 15 | 0.6666666667 | Local length agreement only; not local RMSD or a penalty calibrated to function. |
| AF2372 mobile catalytic loop span | Residues 32–43, inclusive | 12 residues | The source-defined loop boundary; its reference-side residue map is not supplied here. |
| Between-homolog functional-site RMSD and coverage | No usable value or pair map recovered | unknown | Keep separate from the global 1.5 Å result. |

Sources: pp. 22865–22868. [Primary source](https://doi.org/10.1074/jbc.M201042200).

The source compares multiple IMPase-family proteins and reports an AF2372–human IPPase RMSD reaching 2.5 Å. The matched count for that comparison was not recovered from the image-only matrix; do not fabricate its coverage or rank it against the 209-position result as if their extents were known to match. Structural family membership encompasses different substrate/function descriptions and different lithium responses. The paper describes local loop groupings and explicitly leaves their broader predictive validity to further testing. These observations support a broad correspondence while limiting automatic transfer of one substrate specificity, exact inhibitor sensitivity, thermal behavior or physiological role. The original activity measurements belong to A105; the occupancy and contact measurements belong to A111. Neither becomes a structural-similarity cell. The structural discussion does not prove that a particular residue or helix-length difference causes a functional change.

Two additional reported values help separate comparability from effect isolation: the two AF2372 apo dimers differ by approximately 0.6 Å over C-alpha positions, while ligand-associated loop movement is described as approximately 2.5 Å. The former is a same-protein, different-packing comparison with no reported matched count; the latter is a conformation change, described in different passages as average movement and tip displacement. Neither is an additional AF2372–MJ0109 homology score. Exact local correspondence is still needed for a function-specific transfer.

**Structure-quality cells are measurable, and have a separate meaning.**

| AF2372 model condition | Resolution (Å), reported | Diffraction completeness (%), reported | R_work, all reflections | R_free, all reflections | Derived R_free − R_work |
| --- | ---: | ---: | ---: | ---: | ---: |
| Apo, P21 | 1.8 | 93.7 | 0.215 | 0.273 | 0.058 |
| Apo, P32 | 2.0 | 92.4 | 0.188 | 0.212 | 0.024 |
| D-Ins-1-P/Ca, P21 | 2.4 | 94.3 | 0.201 | 0.288 | 0.087 |
| FBP/Ca, P32 | 2.2 | 99.3 | 0.213 | 0.244 | 0.031 |
| F-6-P/phosphate/Mn, P32 | 2.25 | 96.7 | 0.175 | 0.210 | 0.035 |

The paper states a 4% held-out set for R_free. The gaps above are absolute fractions (equivalently 5.8, 2.4, 8.7, 3.1 and 3.5 percentage points). They compare model fit to held-out versus working reflections, not two proteins. Resolution describes the diffraction limit, and completeness is the observed-reflection fraction; neither is a similarity score. Table II's bond-geometry RMS deviations are also not between-protein RMSDs. [Table II, p. 22865](https://doi.org/10.1074/jbc.M201042200).

Further reported diagnostics are the apo P32 twin fraction of 0.499 and approximate mobile-loop/main-chain B-factor ratios of 2.8 for apo P21 and 1.2 for apo P32. The apo paragraph uses the entire structure in the denominator; the later ligand paragraph instead says the rest of the molecule. Do not silently compare them as one identically normalized series. B factors indicate disorder/mobility within a structural model, not a confidence probability for function.

These cells can inform reliability assessment after the actual compared structures are identified. The reference-side quality and the join to the selected AF2372 model are unknown here. No `1 − R_free`, inverse-resolution, twin-fraction or B-factor multiplier is supplied as an unvalidated reliability probability. The interprotein RMSD has no reported SE, SD or confidence interval; the matched positions are not independent samples from which to invent one. Nominal resolution is not a coordinate-error SD. Molecular replacement used MJ0109 as a probe, so independence of the two coordinate models is not established merely because both are experimental.

**Experimental comparability and isolation remain separate.**

Comparability asks which geometric differences might come from construct, ligand/metal state, lattice contacts, temperature or modelling, after allowing the intended protein difference. Here state pairing is unknown, while the same-protein measurements expose some packing/conformation sensitivity. A numerical mismatch penalty cannot be filled from those unknown conditions.

Isolation asks what the readout actually identifies. A coordinate superposition isolates a geometric relationship between the chosen models; it does not isolate the cause of a catalytic or physiological difference. A matched-state local-site superposition would address the missing local correspondence. An independent structure determination can address model dependence. Controlled biochemical comparisons and perturbation/restoration experiments address functional specificity and causality through A105/A106, while their numerical endpoints retain those meanings.

**Exact cells for targeted future population; no reader implementation claimed.**

| Field path or cell | Type and unit | Population/calculation | Missing-data treatment |
| --- | --- | --- | --- |
| `native_comparisons[C01].value_angstrom` | number ≥ 0, Å | Parse the explicitly paired native RMSD from the cited result | null if absent; retain qualifier and source |
| `native_comparisons[C01].superposed_residue_pairs` | integer ≥ 0, residue pairs | Parse the count belonging to that RMSD and alignment regime | null if count is absent; never use a protein length as the count |
| `comparison_subjects.*.paper_reported_monomer_length_residues` | positive integer, residues | Extract explicit complete-length definitions for each operand | null if only an aligned count, fragment or unspecified region is supplied |
| `comparison_subjects.*.comparison_pdb_id`, `.comparison_chain_ids`, `.comparison_ligand_state` | constrained identifier/string or arrays, nullable | Assign only when the source identifies actual superposition operands | null; do not use phasing-probe or deposition-list identities as substitutes |
| `native_comparisons[C01].matched_residue_map` | array of paired residue identifiers, nullable | Populate from an explicitly retained alignment output or source map | null here; no alignment job was run |
| `native_comparisons[C01].point_atom_selection`, `.number_of_atomic_points_in_rmsd_denominator` | atom-selection enum and integer, nullable | Read the definition for this specific RMSD | null here; do not borrow C-alpha from another comparison |
| `derived_components.*reported_length_coverage` | number in [0,1], fraction | N/L for each side; symmetric summary 2N/(L_target+L_reference) | null if relevant numerator/denominator is unknown; reject incompatible units or N larger than an operand length |
| `derived_components.local_functional_site_*` | number/integer, Å or residue pairs/fraction, nullable | Populate only for a source-defined functional-site map and comparison | null; no global-to-local substitution |
| `local_architecture.second_n_terminal_helix.*` | integers and fraction | Inclusive endpoint subtraction, difference and shorter/longer ratio | null if a boundary is not stated; no coordinate or functional inference from span alone |
| `structure_quality.rows[*]` | numerical resolution, completeness, R values and gap | Read each condition separately; subtract matching all-reflection R values | null for missing quality or unidentified pair-to-model join |
| `proposed_component_combination.adopted_distance_scale_angstrom` | positive number, Å, nullable | Requires a separately justified scale; no adopted value supplied | null; sensitivity examples are labelled illustrative |
| `native_comparisons[C01].uncertainty` | numerical SE/interval or null with reason | Use reported uncertainty with its statistical meaning | null, not zero, for unreported uncertainty |

These are part-2 component definitions. A future part-3 reader would populate these exact fields from literature or genuine comparison output. No generic reader, source scorer or production template was created here.

**Dependence, contradiction and nondetection.**

RMSD, matched count, coverage and the proposed product all describe the same comparison. Alternative table cutoff regimes would be dependent analyses, not new experiments. The five AF2372 structures vary state and packing; they are not five independent demonstrations of a shared function. A101 sequence correspondence, A102 geometry and A111 observations can reuse the same underlying protein/structure chain. Keep that shared chain identifiable instead of multiplying the number of independent proofs. Reference activity may ground a transfer but does not get copied into structural-score cells.

The same-protein apo RMSD, the interprotein RMSD and a loop displacement have different denominators and objects; their different values are not contradictory repetitions. If another result disagrees, preserve its structures, mapping, state and parameters before deciding whether the disagreement is substantive. An inaccessible table image, missing residue map or missing score is not a nondetection or a failed structural match. Independent replication count stays unknown.

**Trace to the inspected primary and remaining work.**

| Trace ID | Primary location | Components supported | Inspection limit |
| --- | --- | --- | --- |
| S01–S02 | pp. 22863–22864, deposit note and Experimental Procedures | Experimental structures, constructs, molecular-replacement dependence | Referenced cloning/activity papers not opened |
| S03 | p. 22865, Results and Table II | Within-protein apo RMSD; all quality table numbers | No coordinate-file verification |
| S04 | pp. 22866–22867 | Helix intervals and local length arithmetic | No causal residue-effect conclusion |
| S05 | pp. 22867–22868 | Loop boundary, relative B factors, ligand-associated movement | Figure pixels not inspected; not a homolog-specific site score |
| S06 | pp. 22868 and 22870, structural-comparison Results | Native 1.5 Å/209 result, explicit 252-residue lengths, additional family comparison | Exact chains and pair map unrecovered |
| S07 | p. 22872, Table V caption/footnote | Native comparison settings exist in two regimes | Matrix image not visually inspected; no regime assignment to the narrative result |
| S08 | pp. 22871–22874, cluster discussion, Figure 6 caption and final discussion | Specific-function/generalization qualifications | Caption/text read; no pixel-based measurement |

The author-copy PDF's complete extracted text was read through web retrieval, including repaired gaps; all 799 extract-line identifiers are covered by retained text captures. This is not a claim to have visually inspected all figures or the image-only Table V. Direct local PDF downloads failed. No second primary source, structure search, coordinate analysis, alignment run, production change or scientific execution was performed.

The post-paper reset reread the complete authority set and latest goal before this conversion. Arithmetic checking covers the reported-length fractions, local span calculations, all-reflection R gaps, and the explicitly illustrative component products. It does not validate the unobserved table matrix, missing comparison operands, functional transfer or a full scoring policy.

Remaining source work is to inspect the Table V matrix and recover exact comparison operands/mapping if those are needed for a reproducible structure-specific calculation. Remaining scoring work is the justified treatment of local-site correspondence, quality and function discrimination, contrasting cases, and the overall A102 sheet. This source packet does not close those tasks.
