# A108 exact reported-uncertainty fields — 2026-10-24

This additive correction completes the uncertainty population contract used by
`A108_COMPLETE_NUMERICAL_SHEET_003.md`. It leaves the numerical equations,
source measurements and every earlier record unchanged. The current exact
reader contract consists of the two retained reader specifications referenced
by that sheet **with these additional fields and constraints**. This document
is a separate populating-reader specification, not an investigation prompt,
new scoring factor or implemented function.

The previous sample reader permitted `uncertainty_kind=SD|SEM` without a field
for the actual magnitude. The organism-trait reader similarly named uncertainty
without specifying its numerical population. That was a real field omission.
The following extension applies to **both NumericObservation and
OrganismTraitObservation**, including derived corrected observations.

| Additional field | Exact type and meaning |
|---|---|
| `reported_sd` | Finite nonnegative real or null; actual reported/calculated standard deviation in the observation's own declared unit and normalization. |
| `reported_sem` | Finite nonnegative real or null; actual reported/calculated standard error of the named mean in that same unit and normalization. |
| `reported_sd_basis` | `ReportedErrorBasis` or null; exact basis for the SD magnitude, with explicit unknown members when incompletely reported. |
| `reported_sem_basis` | `ReportedErrorBasis` or null; exact basis for the SEM magnitude, kept separate when it differs from the SD basis. |
| `reported_plusminus` | Finite nonnegative real or null in the observation's unit; retains a reported ± magnitude whose type is actually unspecified. It cannot automatically fill SD, SEM or a bound. |
| `reported_plusminus_basis` | `ReportedErrorBasis` or null, with `measure_kind=unspecified_plusminus` until the source defines it. |
| `error_magnitude_status` | `reported`, `calculated_from_declared_data`, `type_only_magnitude_unavailable`, `unreported`, `conflicting`, or `not_applicable`; this status supplies no numerical weight. |

`ReportedErrorBasis` contains exactly:

```
measure_kind: standard_deviation | standard_error_of_mean | unspecified_plusminus
estimand_ref
sampling_unit_kind: organism | specimen | independent_collection | independent_cluster |
                    biological_preparation | technical_measurement | timepoint |
                    other_declared | unknown
sampling_unit_definition_ref
sampled_unit_refs[]
reported_count: nonnegative_integer | null
count_relation: exact | at_least | at_most | unknown
count_basis_ref
dependence_refs[]
calculation_method_ref
source_ref
locator
origin: source_reported | calculated | synthetic
missing_basis_fields[]
```

`estimand_ref` identifies the quantity whose spread/error is reported, including
its population, variable scale and normalization. `sampling_unit_definition_ref`
and `count_basis_ref` identify actual source/data definitions or remain null
with explicit missingness. Unknown actual unit identities permit an empty
`sampled_unit_refs` list; they do not justify inventing specimens. A reported
lower bound n≥3 remains `reported_count=3,count_relation=at_least`, never an
exact n=3 for SEM or confidence calculations. Time points and technical readings
are not independent organisms/collections merely because there are several rows.

The existing numerical observation fields `lower/upper` retain admissible
instrument, censoring, rounding, model or actual statistical-interval meanings.
SD and SEM belong in the magnitude fields above, **not in lower/upper as an
automatic mean±error interval**. A source defining error-bar type without a
readable magnitude gives null magnitude and `type_only_magnitude_unavailable`.
A reported ± value of unspecified type uses its own field; source disagreement
retains the conflicting values with distinct locators and no silent average.

The sample-context literature/dataset readers and the organism-trait
literature/dataset readers populate these same fields. The calibration/local
conversion reader preserves the original error cells; a propagated SD/SEM
requires the actual conversion and covariance/sampling model and is stored as
a derived observation with its input dependencies. Unknown covariance is not
zero. Unsupported propagation leaves the derived uncertainty unavailable.

The membership and capability/coverage calculators consume admissible value
sets with their declared meanings. A reported SD alone cannot supply such a
set or a confidence level. A statistical interval may be calculated only from
an explicitly defined valid sampling model and actual independent-unit basis;
its coverage and assumptions remain separate. The equal-weight Hoeffding
formula in sheet003 uses its own independent sample denominator, not a count
copied from an arbitrary error-bar label. If analytical bounds themselves have
statistical coverage, the resulting combined coverage requires that declared
joint model; two marginal 95% statements do not automatically yield 95% jointly.

These fields close the named omission without creating measurements or
increasing any score. They apply to literature and dataset observations equally.
Current source-derived and synthetic arithmetic remains unchanged. Readers
remain unimplemented, and no production scoring or episode behavior changed.
