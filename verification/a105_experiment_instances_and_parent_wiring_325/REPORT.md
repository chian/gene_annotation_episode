# A105 experiment instances and parent combination

Implementation milestone, 2026-10-29: the agreed A105 assay connections,
recorded-uncertainty/censoring correction, experiment-instance retention and
parent aggregation are connected. This is implementation readiness for A105
testing, not completion of scientific validation or the larger literature goal.

## Experiment retention

Every new common grading operation requires a possessed, authenticated,
source-anchored assay reference identifying its experiment. The saved record
and every delivered component retain `experiment_ref` alongside `sheet_ref`,
functional assertion, assay type and the original measurement dependencies.
Another experiment using the same template produces another populated instance.
Another assessment of the same experiment retains that experiment identity.

The existing append-only operation and receipt tables retain all instances.
Receipt deduplication uses sheet and component identity, so repeated delivery
does not create additional experiment evidence. The new
`LiteratureAssayGradingRepository.experiment_sheets(context)` view groups the
possessed assessments by experiment, preserving revisions and only the numerical
components actually delivered to that parent. It does not select a preferred
revision or sum duplicate assessments.

Historical v1 records and their original four-type closed return schema remain
readable without inventing experiment identities. New records use v2. The frozen
legacy contract is packaged as `literature_assay_grading_legacy_cells_v1.json`.
Cold reconstruction does not rerun extraction or grading.

## Exact user-defined arithmetic

| Metric | Across-experiment operation |
| --- | --- |
| Reliability | Sum |
| Validity | Sum |
| Relevance | Maximum |
| Attribution | Maximum |
| Overall | Sum |

Maximum is ordinary maximum: `max(1, 2, 5, 4) = 5`. Overall sums experiment
overall scores; it is not an invented combination of the four aggregate
dimensions. No weights, normalization, clamping or orthogonality adjustment
are applied. Dependence metadata is retained without changing these rules.

The parent explicitly binds a possessed saved numerical component to each
metric for each experiment. The operation verifies experiment, assertion and
metric-dimension correspondence and retains each selected value's actual units,
formula and meaning. It accepts no model-authored numerical scores. In
particular, combining components does not rebrand a calibration deviation or
prediction residual as a probability or introduce a new quality scale.

Missing components remain explicit. The complete result remains unavailable
when an experiment lacks a selected metric; a separately labeled available
partial sum or maximum remains useful without inserting a zero.

## Selected parent execution and return

`literature.a105.aggregate` is available under the existing
`assay_grading_population` capability in `LiteratureEpisodes`. An existing
literature parent can combine its own saved assessments and possessed child
returns, then deliver individual assessments and the combined metrics to its
caller. This adds no episode type, private investigation loop or automatic
workflow stage.

The connection includes the tool catalog, assignment roster,
`literature_a105_aggregation_cells` numerical source, original typed contract,
receipt validation, record-reference closure, recurring selected TASK,
worksheet composition, rendering and descriptor reconstruction. Requested
aggregate components use `requested_a105_aggregation_components`. The default
component-selection rules do not expand unrequested private child data.

The aggregation repository persists the exact selection, possessed inputs and
calculated results. Reconstruction authenticates the saved contribution without
repeating arithmetic or scientific acquisition. Ordinary episode action and
observation accounting remains unchanged. No A101, W05, final annotation credit,
goal file, goal text or amendment was changed.

## Completed focused checks

- Experiment retention, historical compatibility and prior common-grader
  integration: **19 passed** in 27.86 seconds before the aggregate connection.
- Aggregate arithmetic, actual saved-input custody and read-only replay:
  **14 passed** in 4.59 seconds in the delegated aggregation work.
- Final selected aggregate operation through the actual parent episode loop,
  exact five-metric return, retained individual experiments, reconstruction and
  display: **1 passed** in 13.21 seconds. This used controlled decisions and
  synthetic measurements, not a live model's scientific judgments.

These counts describe separate overlapping checks and are not added together.
The final combined integration/declaration command passed **267 tests in 83.02
seconds** after all production connections and packaging changes:

```text
/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q \
  tests/test_literature_assay_experiment_instances_323.py \
  tests/test_literature_a105_aggregation_325.py \
  tests/test_literature_a105_aggregation_binding_325.py \
  tests/test_literature_numerical_declarations_203.py --tb=line
```

The four observed actions in the final loop test were the actual parent child
assignment and the child's two grading operations plus aggregation; no internal
reader or report operation manufactured additional observations or credit.

Related completed implementation reports:

- [Existing assay-type connections](../a105_existing_type_connections_323/REPORT.md)
- [Uncertainty and detection-limit scoring correction](../a105_uncertainty_scoring_bug_324/REPORT.md)
- [Aggregation arithmetic and persistence](../a105_aggregation_325/REPORT.md)

Full A105 scientific validation, including live model interpretation of source
papers and broad assay coverage, remains the testing phase. The earlier retained
paper examples remain partial when actual source inputs are missing; no missing
scientific measurement was invented to declare implementation readiness.
