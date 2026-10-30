# A105 P205 finite parent-removal worksheet section

## Authority and source

This bounded implementation follows the original user-supplied goal, the current root and research `AGENTS.md` instructions, and the original-paper audit in `verification/a105_matched_control_primary_306/REPORT_001.md`. After inspecting the P205 packet, I reread the original goal attachment and applicable instructions before implementing this section. It remains one section of the existing A105 worksheet; it does not create an eleventh evidence-axis sheet or combine A105 with A101 or W05 annotation credit.

The quantitative source is the authors' original `PLA55254_P205_subtrate_specificity_screening.xlsx`, SHA256 `24d5734e8a8643ab20306a1725843686460761362cb85a9ef0c1e6c25304a2ae`, selected by sheet `summary`, compound `Capecitabine`, submixture `Sub7`, time `24 h`; the unique result is row 5. The original article XML is `PMC11741061.xml`, SHA256 `1919a2a62baa2983b2bf9e9ccbde7c9631bdc2322c2951be68ecc1c798da4e1e`. The article and supplement identify purified P205, the S146A replacement construct and the abiotic arm; see the preceding audit for source-specific biological interpretation and limits.

## Three responsibilities

1. **Investigation TASK:** `literature_parent_depletion_prompt.py` gives source-specific questions about construct and control comparability, analyte, normalization, replication, covariance, and the difference between parent disappearance and product formation. The full general literature TASK remains present on each child decision; the parent retains its full source-evidence TASK after the child returns.
2. **Numerical worksheet section:** The existing A105 worksheet registers `literature_parent_depletion_cells` under `finite_parent_compound_removal`. It receives a constrained typed eight-component return. The parent STEERING displays all eight values, their workbook cells, and limitations. The section has no annotation-credit or product-coupling value.
3. **Reader and calculator:** The selected `literature.parent_depletion.populate` operation uses the existing XLSX `Workbook.rows` reader, binds native row-5 cells, and then calculates two contrasts with `Decimal`. It rejects a wrong workbook hash, missing or nonunique matching row, changed headers, nonnumeric arm cells and disagreement with workbook difference cells beyond `1e-12` fraction. It saves the selected sheet and native cell custody. Cold reads reconstruct the saved typed return without reopening the original workbook or rerunning extraction or arithmetic.

The operation is selected as an own action in a literature child. It returns through the parent's declared form rather than a model-written numerical summary. The full TASK and concise STEERING are separate rendered blocks. The deterministic calculation does not make an additional episode, independent experiment or scientific observation.

## Populated numerical components

All values are fractions of the source's reported parent-removal normalization; a negative removal estimate is preserved as reported. The source does not provide raw denominator values for this selected row.

| Component | Workbook source or calculation | Value |
| --- | --- | ---: |
| Active parent removal | `B5` (`Bio`) | 0.68800629778328803 |
| S146A parent removal | `F5` (`inactive_enzyme`) | 0.0987152898299202 |
| Abiotic parent removal | `D5` (`Ab`) | −0.038743056052261297 |
| Active reported SD | `C5` (`Stdev1`) | 0.0108692606063584 |
| S146A reported SD | `G5` (`Stdev3`) | 0.0274700307939434 |
| Abiotic reported SD | `E5` (`Stdev2`) | 0.076909642509430096 |
| Active minus S146A | `B5 − F5`; verified against `K5` | 0.58929100795336783 |
| Active minus abiotic | `B5 − D5`; verified against cached `L5` | 0.726749353835549327 |

The last two rows share the same active measurement key for `B5`; they are dependent descriptions of one active arm. `K5` is a literal numeric workbook cell and `L5` is a saved formula-result cache. The calculator verifies both against subtraction. Workbook differences deviate from the exact `Decimal` results only at the last printed decimals, below the declared tolerance. Per-arm SDs remain source-reported SDs; no SD, SE, confidence interval, independent replication count, or probability for either difference is inferred. Equality of active and mutant protein amounts, active-control covariance, P205-specific product identity, and quantitative product coupling remain unknown. These cells measure parent disappearance at 24 h, not a rate, catalytic yield, reliability score, target-transfer weight or final A105 credit.

## Verification

`.venv/bin/python -B -m pytest -q tests/test_literature_p205_parent_depletion_308.py --tb=short -x` passed: **2 tests**. They verify original author workbook values, cell origins and identities, both difference checks, wrong-hash and tampered-difference rejection; a real selected literature operation; typed child-to-parent delivery; all eight values and limitation labels in rendered parent STEERING while full parent and child TASK blocks remain present; and read-only cold reconstruction with workbook access and parser/calculator calls blocked. The source-specific operation reuses the production `Workbook.rows` implementation within one selected action; the test does not separately select `source.xlsx.rows` as an additional episode action.

The implementation is a bounded numerical section, not a complete P205 assay grade. Source normalization inputs, replication structure, mutant amount and P205-specific product measurements remain unverified. W05 aggregation and target correspondence remain outside this work.
