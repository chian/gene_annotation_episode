# A105 independent-preparation precision: current implementation audit

The immutable user-supplied goal remains the authority. This is an additive
current-state correction to the historical case242 research proposal, not a
change to that proposal or a new scoring policy. The selected source is Sunden
et al., eLife 2015, DOI 10.7554/eLife.06181. The retained publisher PDF and
text are in `research/experimental_scoring_review_2026-10-23/a105_independent_preparation_case_242/sources/`.

## Source interpretation and numerical cells

Table 1 gives E. coli alkaline phosphatase D101A/E322Y catalytic efficiency
3.1 (SD 0.1) M^-1 s^-1. Its marked footnote and the Methods support two
independently expressed enzyme preparations. The same paper reports
D101A/E322Y/K328A as 1.1 (SD 0.1) M^-1 s^-1, but that row has no marked
independent-preparation footnote. Its preparation count is unknown. Both
constructs contain E322Y, so the Methods' MgCl2 omission applies to both.

The installed reader `read_kinetic_summary_precision_inputs` retains the
source meaning, explicit count, uncertainty statistic and units, then projects
exact calculator inputs. The installed `populate_kinetic_summary_precision`
returns these numerical cells for the first row:

| Component | Current result | Status |
| --- | ---: | --- |
| Reported catalytic efficiency | 3.1 M^-1 s^-1 = 0.000186 µM^-1 min^-1 | Source reported; deterministic unit conversion |
| Reported SD | 0.1 M^-1 s^-1 = 0.000006 µM^-1 min^-1 | Source reported; deterministic unit conversion |
| Independent physical preparations | 2 | Source supported |
| Relative reported SD | 0.1/3.1 = 0.0322581 | Descriptive, source supported |
| Statistical estimator count in source cells | unavailable | Physical n is not silently equated with estimator n |
| Estimated mean variance, scenario | 0.005 (M^-1 s^-1)^2 | Conditional on explicit preparation-to-estimator and IID/sample-SD assumptions |
| Estimated mean SE, scenario | 0.0707107 M^-1 s^-1 | Same conditional contribution |
| Relative mean SE, scenario | 0.0228099 | Also requires arithmetic-mean identity |
| Proposed 95% mean interval, scenario | [2.20154, 3.99846] M^-1 s^-1 | Also requires normality; df=1, t=12.7062 |

The contrasting K328A row remains usable as a point estimate and reported SD,
with physical-preparation count unavailable. Its descriptive reported-protocol
difference is 2.0 M^-1 s^-1 and retained fraction 1.1/3.1 = 0.354839. A
preparation-level SE for that difference and cross-construct covariance are
unavailable. Neither row establishes total assay uncertainty, an assay error
probability, target transfer or annotation credit. The multiple precision
representations are one dependent contribution, not independent evidence.

## Current path and verification

The present source reader, input validator, calculator, selected repository,
typed projection, common worksheet and parent return path exist. The
historical case242 statement that these precision cells and runtime binding
were unimplemented was accurate for its earlier proposal stage but is stale
for the current implementation. The saved sheet keeps source cells separate
from conditional scenario cells and a cold read reconstructs the selected
return without rereading scientific source bytes.

Focused current-code command:

```text
.venv/bin/python -B -m pytest -q \
  tests/test_literature_kinetic_summary_precision_components_248.py::test_actual_source_count_and_conditional_precision_match_independent_oracle \
  tests/test_literature_kinetic_summary_precision_components_248.py::test_actual_contrasting_construct_does_not_inherit_hash_preparation_count \
  tests/test_literature_kinetic_summary_precision_binding_251.py::test_original_source_narrow_identity_context_survives_parent_view_and_cold
```

Result: **3 passed in 8.56 s**. This verifies the actual retained original
source selection and selected cold-read delivery, not a configured model-backed
literature investigation or A105 adequacy as a whole. No production or test
code was changed for this audit. No new independent grader is warranted by
these two rows. Further source-level interpretation of construct-specific
activity and cross-construct uncertainty remains open.
