## A105 experimental evidence worksheet

Requested numerical sections retain their own experimental and uncertainty meanings. Shared reports and calculated views do not supply additional independent assays.

## Worksheet section 1: native parameter



## Requested native kinetic components

| Component | Value | Unit | Status | Relation | Threshold | Approximate | Unavailable reason | Origin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| numerator_parameter | 0.000186 | uM_inverse_min_inverse | populated | eq | None | False | None | calculated |

## Native kinetic experimental relationships

| Meaning | Selected interpretation |
| --- | --- |
| comparison_scope | unknown |
| nonintended_conditions_relationship | unknown |
| parameter_definition_relationship | unknown |
| subject_relationship | unknown |
| substrate_arrangement | unknown |

## Numerator parameter meaning

| Meaning | Value |
| --- | --- |
| parameter_kind | catalytic_efficiency |
| canonical_unit | uM_inverse_min_inverse |
| qualification | reported_point |
| input_status | point |
| observed_relation | point |
| source_origin | reported |
| converted_origin | calculated |

## Numerator subject and experimental context

| Meaning | Source definition |
| --- | --- |
| construct | source-bound meaning retained for scoped access |
| genotype | unknown |
| molecule | source-bound meaning retained for scoped access |
| organism | source-bound meaning retained for scoped access |
| conditions | source-bound meaning retained for scoped access |
| endpoint | source-bound meaning retained for scoped access |
| experiment | source-bound meaning retained for scoped access |
| experimental_system | source-bound meaning retained for scoped access |
| normalization | source-bound meaning retained for scoped access |
| preparation | source-bound meaning retained for scoped access |
| substrate | source-bound meaning retained for scoped access |

## Numerator uncertainty meanings

| Meaning | Value |
| --- | --- |
| statistic | sd |
| canonical_unit | uM_inverse_min_inverse |
| repetition_basis | biological_preparations |
| estimate_basis | unknown |
| count_reading_status | exact |
| count_relation | point |
| count_approximate | False |
| unavailable_reason | None |

## Numerator requested uncertainty values

| Quantity | Value |
| --- | --- |
| magnitude | 6e-06 |
| interval | None |
| confidence_level | None |
| count | 2 |
| count_reported_value | 2 |

## Worksheet section 2: precision



## Requested kinetic summary precision

| Population | Component | Value | Unit | Status | Qualification | Origin | Approximate | Unavailable reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source_cells | reported_parameter | 0.000186 | uM^-1min^-1 | populated | source_reported | derived | False | None |
| source_cells | reported_sd | 6e-06 | uM^-1min^-1 | populated | source_reported | derived | False | None |
| source_cells | independent_preparation_count | 2 | count | populated | source_reported | reported | False | None |
| source_cells | statistical_estimator_count | None | count | unavailable | unavailable | reported | False | statistical_estimator_count_unknown |
| source_cells | mean_standard_error | None | uM^-1min^-1 | unavailable | unavailable | derived | False | statistical_estimator_count_unknown |
| scenario_cells | mean_variance | 1.8e-11 | uM_inverse_squared_min_inverse_squared | populated | conditional_on_stipulated_assumptions | derived | False | None |
| scenario_cells | mean_standard_error | 4.242640687119285e-06 | uM^-1min^-1 | populated | conditional_on_stipulated_assumptions | derived | False | None |

## Source and sampling meanings

| Source kind | Parameter | Reported count meaning | Repetition basis | Estimate basis |
| --- | --- | --- | --- | --- |
| primary_source | catalytic_efficiency | physical_preparation_count | biological_preparations | unknown |

## Selected summary precision conditions

| Population | Component | Source condition states | Calculation premises | Explicit stipulations |
| --- | --- | --- | --- | --- |
| source_cells | reported_parameter |  |  |  |
| source_cells | reported_sd |  |  |  |
| source_cells | independent_preparation_count | row_footnote_applicability=source_supported |  |  |
| source_cells | statistical_estimator_count | row_footnote_applicability=source_supported; one_estimate_per_preparation=unknown; reported_sd_summarizes_counted_preparation_estimates=unknown |  |  |
| source_cells | mean_standard_error | row_footnote_applicability=source_supported; one_estimate_per_preparation=unknown; reported_sd_summarizes_counted_preparation_estimates=unknown; sample_sd_n_minus_one=unknown; iid_common_mean_finite_variance=unknown | sample_sd_n_minus_one, iid_common_mean_finite_variance |  |
| scenario_cells | mean_variance | row_footnote_applicability=source_supported; one_estimate_per_preparation=unknown; reported_sd_summarizes_counted_preparation_estimates=unknown; sample_sd_n_minus_one=unknown; iid_common_mean_finite_variance=unknown | one_estimate_per_preparation, reported_sd_summarizes_counted_preparation_estimates, sample_sd_n_minus_one, iid_common_mean_finite_variance | one_estimate_per_preparation, reported_sd_summarizes_counted_preparation_estimates, sample_sd_n_minus_one, iid_common_mean_finite_variance |
| scenario_cells | mean_standard_error | row_footnote_applicability=source_supported; one_estimate_per_preparation=unknown; reported_sd_summarizes_counted_preparation_estimates=unknown; sample_sd_n_minus_one=unknown; iid_common_mean_finite_variance=unknown | one_estimate_per_preparation, reported_sd_summarizes_counted_preparation_estimates, sample_sd_n_minus_one, iid_common_mean_finite_variance | one_estimate_per_preparation, reported_sd_summarizes_counted_preparation_estimates, sample_sd_n_minus_one, iid_common_mean_finite_variance |

## Selected source identity and experimental context

| Meaning | Source fragment |
| --- | --- |
| construct | D101A/E322Y# |
| molecule | AP mutant |

## Summary precision meaning

Sample-derived variance and SE estimate random mean precision. Source facts and explicit scenarios remain separate. SD, counts, variance, SE and interval parameters describe dependent views of one summary contribution; they are not additional experiments. Shared calibration and systematic uncertainty remain unknown.

## Relationships between requested quantities

| First quantity | Second quantity | Meaning |
| --- | --- | --- |
| section 1, returned set 1, numerator parameter / cell value | section 2, returned set 1, source reported parameter / cell value | same original parameter report; dependent views |
| section 1, returned set 1, numerator parameter / reported spread | section 2, returned set 1, source reported sd / cell value | same original spread report; dependent views |
| section 1, returned set 1, numerator parameter / reported count | section 2, returned set 1, source independent preparation count / cell value | same original count report; preserves repetition meaning |
| section 2, returned set 1, source reported sd / cell value | section 2, returned set 1, scenario mean variance / cell value | conditional precision of this report under stated premises |
| section 2, returned set 1, source independent preparation count / cell value | section 2, returned set 1, scenario mean variance / cell value | conditional precision of this report under stated premises |
