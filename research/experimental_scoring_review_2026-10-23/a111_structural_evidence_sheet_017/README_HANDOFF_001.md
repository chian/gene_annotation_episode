# A111 proposed sheet handoff

This directory contains independently prepared **PROPOSED** A111 numerical scoring research. It does not claim user acceptance or axis completion. A105 remains first and 0/10 scoring sheets remain marked complete. The written formulas are complete for the stated diffraction/native-geometric measurement scope; broader experimental modalities remain explicitly outside its demonstrated conversion coverage.

Read these deliverables together, with the additive clarifications taking precedence where specified:

1. `PROPOSED_A111_SHEET_001.md` — numerical input cells, explicit products and complete whole-axis reducer; scope, missingness, uncertainty, replication, conflict and alternative interpretation handling.
2. `ARITHMETIC_SPECIFICATION_ADDENDUM_001.md` — exact multiple-question weighting expansion; calibrated nondetection fit scope; native-input verification clarifications.
3. `WORKED_EXAMPLES_001.md` — print-ready contrasting source rows plus a fully populated, clearly synthetic joined example and interval arithmetic.
4. `READER_IO_001.md` — exact proposed typed fields and targeted function inputs/outputs. All production readers remain unimplemented.
5. `SOURCE_TO_CELL_001.md` — source/component mapping, inspection limits, and additive interpretation correction to the first packet.
6. `MJ0577_conversion_001.md` and `Fuhrmann2013_conversion_001.md` — separate per-paper conversions, preserved as written. Apply the source-to-cell additive correction to the preliminary MJ0577 fit interpretation.
7. `receipts/MJ0577_reset_001.json` and `receipts/Fuhrmann2013_reset_001.json` — full initial/post-paper authority reread receipts and coverage. Source inspection truncations were repaired; latest human directions were read last.
8. `research_arithmetic_001.py`, `ARITHMETIC_RESULTS_001.json`, `1MJH_source_calculations_001.json` — research-only numerical reproducibility. The final joined run has 22 passing checks.

## Inspected sources and exact boundaries

| Source metadata | Actual inspection | Uninspected / unmeasured |
| --- | --- | --- |
| DOI 10.1073/pnas.95.26.15189; PDB 1MJH | Full five-page paper text; selected visual tables/figures; complete retained coordinate file parsed for selected geometry; local ligand/metal validation; core entry metadata | Raw maps and re-refinement; complete coordination-endpoint validation; occupancy uncertainty; target correspondence; independent solution assembly |
| DOI 10.1016/j.celrep.2013.05.023; PDB 4KK3 and 4KK4 | Full eight-page publication text plus repository cover; visual Figures 3–4; selected deposited construct/state/cell/refinement fields; selected atom geometry and local validation | Supplementary Methods/Tables S1–S2; raw maps; alternate ligand fitting; occupancy uncertainty; target correspondence; nuisance-effect bounds; exact figure/current-deposit atom correspondence beyond the calculated selectors |

No source-populated complete **target** score is claimed: neither source was mapped to the supplied project target. The published examples populate structural components; the complete target-level numerical example is synthetic. No current-target native search, annotation workflow, HPC work or source-history modification was performed.

## Verification and limitations

The final research calculator was run with `python3 research/experimental_scoring_review_2026-10-23/a111_structural_evidence_sheet_017/research_arithmetic_001.py` and completed with 22 checks passing. Checks include native coordinate distances/angles, validation-value reproduction, duplication invariance, contradictory evidence, fixed partial-site denominators, calibrated nondetection, interval propagation, signed support reconstruction and invalid native-score rejection. Initial script syntax/assertion issues were repaired before the final run; no failing check is passed off as validation. No production test suite, production reader/scorer path, model prompt or annotation-credit consumer was changed or tested.

The proposed local-fit transform is a declared numerical index, not a calibrated probability. Uncertainty and unknown identity/transfer remain visible. User judgment is still required on transforms, products, averaging, fixed feature weights, threshold definitions and nuisance scales. That is design feedback, not a runtime approval step.

**Bounded remaining work:** other structural modalities require an explicit native observation-support conversion before this same reducer produces their full scalar. This proposal does not claim universal cryo-EM/NMR/cross-linking coverage. Empirical calibration, actual target mappings, production readers, final prompt review, the complete library/credit consumer and user acceptance also remain unperformed. No essential arithmetic is left undefined within the documented diffraction case, but expanding its method scope is additional scoring design work.

The parent should print the substantive formulas and worked examples for the user after inspecting the source packets and completing the required authority reset. The parent-facing progress/final message deliberately contains only metadata, file paths and checks.
