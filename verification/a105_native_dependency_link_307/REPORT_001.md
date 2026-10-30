# A105 worksheet: source-bound reuse of one kinetic estimate

This is an opt-in V2 **context version of the same logical A105 worksheet**, not
another evidence axis, assay grader, or numerical confidence formula. The V1
context schema and default template retain their exact relation vocabulary for
saved forms and the frozen configured run. V2 adds one permitted relationship,
`same_physical_measurement`, between two delivered native kinetic parameter
cells from different contrast sheets. The parent explicitly returns the link;
the host validates it against the actual returned source witnesses.

## Pa0142 case and numerical meaning

The selected original-paper path in
`verification/a105_pa0142_kinetic_selected_303/REPORT_001.md` uses purified
Pa0142 from *Pseudomonas aeruginosa* PAO1. The pH 8 coupled ammonia assay
reports 8-oxoguanine, guanine, and isocytosine catalytic efficiencies of 1.2,
0.078, and 0.132 µM^-1min^-1 after explicit source-unit conversion. Its two
descriptive ratios are 200/13 and 100/11. Both reuse the **one** 8-oxoguanine
physical estimate. The ratios and their log views are dependent, so summing
two independent single-contrast scores would count that numerator twice. The
paper does not supply the three-estimate joint covariance, the meaning of its
reported ± spreads, or complete nonintended-condition matching. No combined
specificity score is populated. In a future model on log estimates X, Y, Z,
the dependence would require
`Cov(X−Y, X−Z) = Var(X)−Cov(X,Z)−Cov(Y,X)+Cov(Y,Z)`; none of these terms is
inferred from equal numbers or from the reported marginal spreads.

The extraction already supplies each parameter's exact source numeric token,
the broader physical-observation source witness, canonical value/unit, subject,
construct, assay context, uncertainty meaning, and source identity. The V2 link
uses the two delivered `numerator_parameter` rows, cites the shared physical
and measurement reference records, and verifies that the numeric token is
contained in the physical witness in the same source artifact. It requires the
same non-null physical identity, source measurement token, canonical parameter,
uncertainty and context. Equal numeric values with distinct physical identities
do not establish a link; conflicting values under one identity are rejected.
This relationship constrains later compilation and is not itself an extra score.

## Files and execution

- `gene_annotation_episode/literature_a105_worksheet.py`: V1 default unchanged;
  optional V2 context and source-bound native-to-native link validation added.
- `tests/test_literature_a105_native_dependency_307.py`: exercises original
  Pa0142 geometry-checked transcription through two selected
  `literature.kinetic.populate` operations, typed literature and annotation
  returns, six ordinary actions and six observations, semantic negative cases,
  and read-only SQLite reconstruction with primary source artifact access and
  population functions blocked. The separate Pa0142 test owns the PDF/SI and
  typography receipts; this test reuses them and does not collect a new paper.

Final focused command: `.venv/bin/python -B -m pytest -q
tests/test_literature_a105_native_dependency_307.py --tb=short -x` → **2 passed
in 30.92 s**. The joined V1 worksheet and V2 tests, before the final stricter
source-artifact block, passed **62 in 28.99 s**. No final A105 reliability,
validity, relevance, effect-isolation, target-transfer, or annotation-credit
compilation is claimed. The selected episode decisions used a scripted provider
and fixture controller, not a configured model.

## Post-paper authority reset

After reading the retained Pa0142 packet and before interpreting it, this
workload reread the complete immutable goal attachment, root `AGENTS.md`,
`docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`,
`docs/TOOL_KNOWLEDGE.md`, `docs/TASK_AND_STEERING.md`,
`docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md`,
`docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`, both
`VERBATIM_DIRECTION.md` and `VERBATIM_RECOVERY_002.md`,
`docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`,
`verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`,
the complete research `AGENTS.md`, and the complete current A105 worksheet,
kinetic input, calculation and storage contracts. The latest replacement user
AGENTS direction and parent assignment were applied last. `GOAL.md` was not
opened.
