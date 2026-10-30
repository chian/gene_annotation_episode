# Synthetic pure-calculator fixture table

Every operand/model here is invented. Graph flags are parsed-input scenarios; no image was measured.
All displayed values are actual calls to the new pure calculator. Null is unavailable, never zero.

The root example's native e=6 nmol/min/mg and V=1.7 (nmol/min/mg)^2 become .006 and .0000017 in canonical units.

| Synthetic case | d1 | d0 | e | V | sqrt(V) | S | B | e reasons |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| native_root_example_model_none | 0.01 | 0.004 | 0.006 | 1.7e-06 | 0.00130384048104 | null | null |  |
| stipulated_known_normal_model | 0.01 | 0.004 | 0.006 | 1.7e-06 | 0.00130384048104 | 10.5882352941 | 0.99994957953 |  |
| signed_negative_effect | -0.001 | 0.004 | -0.005 | 1.7e-06 | 0.00130384048104 | -7.35294117647 | -0.998719410162 |  |
| estimated_covariance_not_known_likelihood | 0.01 | 0.004 | 0.006 | 1.7e-06 | 0.00130384048104 | null | null |  |
| covariance_unavailable_not_independent | 0.01 | 0.004 | 0.006 | null | null | null | null |  |
| known_different_biological_denominator | null | 0.004 | null | null | null | null | null | different_normalization |
| unknown_second_pair_normalization | 0.01 | null | null | null | null | null | null | unknown_normalization |
| root_review_different_pair_dimensions | 10 | 4 | null | null | null | null | null | incompatible_unit_dimension |
| actual_shared_control_joint_cancellation | 0.01 | 0.003 | 0.007 | 1.36e-06 | 0.00116619037897 | null | null |  |
| shared_censored_control_no_threshold_likelihood | null | null | 0.007 | 1.36e-06 | 0.00116619037897 | null | null |  |
| unknown_identity_equal_limits_do_not_cancel | null | null | null | null | null | null | null | uninformative_bounds |
| invented_graph_nominal_and_reading_interval | 0.01 | 0.004 | 0.006 | 1.7e-06 | 0.00130384048104 | null | null |  |
| one_graph_endpoint_out_of_numeric_range | null | 0.004 | null | null | null | null | null | incompatible_unit_dimension |
| variance_range_does_not_erase_uncertainty_or_profile | 2e-163 | 1e-163 | 1e-163 | null | 2e-163 | 0.125 | 0.0624187467475 |  |

Each row's exact actual input, units, bound states, finite reasons and full cells are in NUMERICAL_FIXTURES_005.json.
For the range-partial scenario inspect protein_condition1_response: value=1e308, lower=1, upper=null, status=partial, upper bound_state=numeric_range_failure.
No selected operation, source reader, typed runtime handoff, W05 aggregation or annotation credit is implemented by this table.
