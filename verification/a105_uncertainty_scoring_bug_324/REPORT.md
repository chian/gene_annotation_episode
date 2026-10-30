# A105 recorded uncertainty and censoring scoring correction

The common scoring path incorrectly discarded useful observation-bound metadata
and rejected every estimated variance from the overall comparison. This is a
correction to required A105 scoring, not a new assay category or an optional
scoring requirement.

## What changed

`literature_assay_grading.py` now retains a reported upper, lower or interval
observation bound in the measured-effect cell. A bound remains a bound; its
threshold is never substituted for an observed point, and nondetection is never
substituted with zero. The corresponding prediction-error cells retain shifted
bounds. Known variance or supplied estimated variance and inverse variance can
remain numerical when the observation is censored.

For the required overall experimental-evidence comparison, the selected model
can now be:

| Selected measurement model | Point observation | Censored observation |
| --- | --- | --- |
| Known-variance normal | Existing signed log-density ratio | Signed log ratio of probabilities of the observed upper/lower/interval event |
| Estimated-variance normal approximation | Plug-in signed log-density ratio, explicitly conditional on estimated variance | Plug-in event-probability comparison, with the same explicit approximation |
| Explicit Student-t residual model | Signed log-density ratio using supplied degrees of freedom and the estimated variance as squared scale | Signed log ratio of Student-t probabilities of the observed censoring event |

The estimated-normal comparison is labeled an approximation: it does not
integrate uncertainty in the variance estimator. The Student-t option is an
explicitly selected residual/predictive measurement model. The implementation
does not infer that model merely because a paper reports an SD or SE. The
Student-t scale squared is the supplied estimated mean variance; it is not
misidentified as the variance of the Student-t distribution itself.

Existing summary readers continue to calculate SD, variance of the mean and SE
under their supported meanings. Those calculations are reused, not repeated in
the common grader. Degrees of freedom are an additional optional input operand,
not another scoring sheet, experiment or evidence contribution. Existing
two-group unknown-variance profile calculations were inspected; their different
statistical question was not silently substituted for the selected comparison
between fixed predictions.

The input adapter changes were coordinated with agent 322. It now retains
authenticated literal and supported native censoring limits in canonical units,
preserves estimated-variance metadata, and accepts the actual delivered degrees
of freedom. Confidence intervals, ambiguous alternative readings and graph
display ranges are not automatically treated as observed censoring events.

One additional overly broad rejection was corrected: lack of a native physical
dependency identifier does not invalidate a single supported observation-model
comparison. The `physical_measurement_identity_unknown` qualification and saved
component identity remain in the result. No independent replication is inferred
and no experimental contribution is created by this correction.

## Retention and communication

New bound metadata and the degrees-of-freedom input are optional when validating
older saved records. The nine existing numerical components remain unchanged.
An explicitly requested measured-effect row carries its bound and `bounded`
status; requesting only the overall score does not expose unrequested numeric
observations. Saved rows retain experiment identity, source references, input
origins and physical measurement keys. No holistic aggregation or W05 scoring
was added here.

## Verification

Command:

```text
/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q \
  tests/test_literature_assay_grading.py \
  tests/test_literature_assay_grading_inputs.py \
  tests/test_literature_assay_grading_primary.py \
  tests/test_literature_assay_grading_uncertainty_324.py --tb=short
```

Result: **112 passed in 14.58 seconds**. The new file contains 28 tests.

The new tests cover explicit estimated-variance scoring; Student-t degrees of
freedom and scale; upper/lower/interval censoring; stable far-tail event
probabilities; malformed or unavailable limits; incompatible units; unknown or
conflicting variance; scientific applicability; and reuse of an observation as
its own purported independent prediction.

Three connections were exercised beyond pure arithmetic:

1. The existing summary reader/populator produced an effect of 600 per minute,
   estimated mean variance 36 per minute squared, and 3 degrees of freedom.
   Their actual native returned rows populated the selected Student-t comparison.
2. The existing source-rate reader retained a reported `<12` limit, converted it
   to `<0.012` in its canonical unit, and passed the bound into a numerical
   censoring-event comparison.
3. A selected estimated-variance censored assessment was saved and delivered to
   a parent as exactly three requested components. A cold, read-only reopen
   recovered the numerical score, bound and experiment identity while scientific
   source reads and recalculation were forbidden. Changing the returned bound
   failed saved-value validation.

The first two are existing native-reader paths with explicitly synthetic inputs;
the third is a synthetic custody/integration test. Existing retained-paper
examples passed unchanged. No new paper search or model-driven scientific run
was performed for this correction.

## Meaningful limits

A numerical censoring score needs a reported limit (or observation interval),
appropriate measurement-model uncertainty, explicit predictions and applicable
scientific interpretation. An unspecified detection limit is retained as
missing information, rather than converted to a fabricated probability. A
missing or conflicting variance remains missing or conflicting. The estimated
normal approximation is not represented as exact known-variance inference.

Normal and Student-t density/CDF/survival definitions and scale conventions were
checked against the primary [SciPy normal documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html)
and [Student-t documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html).
Normal tails use [SciPy's stable log-CDF](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.log_ndtr.html);
interval probabilities use stable log differences and the nearer tail.

No goal, amendment or scoring-template count was changed.
