# A105 parent aggregation implementation

Implemented the user's exact across-experiment rules in
`literature_a105_aggregation.py` and
`literature_a105_aggregation_storage.py`:

| Metric | Rule |
| --- | --- |
| Reliability | Sum |
| Validity | Sum |
| Relevance | Maximum |
| Attribution | Maximum |
| Overall | Sum |

Maximum is ordinary maximum: values `1, 2, 5, 4` produce `5`. Negative values
are not clamped to zero. There are no weights, rescaling, orthogonality
adjustments or dependency-based exclusions.

The parent selects one already-possessed numerical grading component for each
experiment and metric, using its saved sheet reference and component name.
The operation accepts no newly authored numerical inputs. Each selected row
must match the requested experiment, functional assertion and metric dimension.
Duplicate experiment identities are rejected, so a repeated report or revision
cannot count as another experiment. The parent selects which assessment of an
experiment to use; infrastructure does not choose the latest or highest one.

The operation retains the original selected component values, units, meanings,
source references, measurement dependencies and scientific qualifications. It
does not reinterpret an inverse variance as a probability, a recovery deviation
as a calibrated validity score, or a prediction residual as a relevance
probability. Mixed native units remain explicitly recorded; no conversion or
new quality scale is introduced. The parent's explicit component selection
therefore remains visible and reviewable.

Every rostered experiment has an explicit selection or null for each of the
five metrics. Missing or bounded non-scalar components remain missing for
scalar aggregation. A full `value` is unavailable if any rostered experiment
lacks that metric; `available_value` separately reports the ordinary sum or max
of the available values. An empty roster does not manufacture a zero score.

All contributions must concern the same `assertion_ref`. An optional
`comparison_ref` retains the parent's explicitly declared alternative
hypothesis. Existing native grading rows do not identify that alternative
hypothesis, so the operation does not claim that the native row independently
certifies the parent's comparison declaration. Each contributing native row
and its actual model remain attached to the corresponding aggregate metric.

## Persistence and custody

`LiteratureA105AggregationRepository.populate` reads components through the
parent's bound reader callback and validates them against the parent's actual
possessed grading rows. Mere possession of a child's source identifier does
not reveal undelivered numerical fields. Requests, selected source rows and
results are committed immutably using the existing source/operation mechanism.

Projection, parent receipt, admitted-subset validation and cold reconstruction
use the shared repository custody methods. Replaying a committed aggregation
does not recalculate a total, repeat grading, reread scientific source bytes or
create a new observation. The outer parent receives only the requested aggregate
metrics and their selected contributors.

This is the A105 parent combination, not another assay template or W05
annotation-credit implementation. Root owns the tool catalog, assignment,
worksheet, prompt, rendering and actual episode-loop connections.

## Verification completed in this subtask

```text
/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q \
  tests/test_literature_a105_aggregation_325.py --tb=short
```

**14 tests passed in 4.59 seconds.** Both modules imported successfully and their
JSON schemas passed schema validation.

The tests exercise exact sum/max rules, negative maxima, partial and empty
inputs, unchanged native units and dependencies, duplicate experiments,
incorrect assertion/experiment/dimension bindings, aggregation of two actual
saved and delivered synthetic experiment grades, narrowed delivery to another
parent, read-only cold replay with calculation functions forbidden, rejection
of altered saved values, and rejection of undelivered child components.

No new paper search, model-driven scientific investigation, goal change or
amendment was performed.
