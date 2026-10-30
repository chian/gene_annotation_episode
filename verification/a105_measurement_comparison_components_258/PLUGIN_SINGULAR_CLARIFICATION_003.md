# Additive clarification003: zero plugin variance is not a population constraint

This follows root's explicit estimated-versus-known refinement. It adds exact domain distinctions to correction002; all001 and002 bytes remain intact. The current exact schema proposal is now the five *_SCHEMA_003.json resources. Their structural shapes and formula bindings are those of002; only root resource identities and the shared reason-domain enum change. Function interfaces, TASK and scope remain unchanged. No production/test coding is released or performed.

A known actual covariance C=[[v,v],[v,v]] constrains the selected estimators' difference to have zero variance. Under the declared common unbiased-quantity model E[D]=0, this entails D=0 almost surely. Thus observed D!=0 is inconsistent_deterministic_constraint under that known model, as retained in correction002.

An estimated/plugin matrix with the same entries does not establish that the actual population Var(D) is zero. Its zero plugin V_D can make the original formulas undefined, but cannot establish a scientific contradiction. Actual population discrepancy variance remains unknown from that fact alone.

Exact prospective domain/behavior distinctions:

| Variance status and observed case | D variance / standard uncertainty | z and z² | Weight allocation | Combined value, variance and standard uncertainty |
|---|---|---|---|---|
| known, V_D=0, D=0 | Populated0;0 under the declared model | Unavailable, positive_discrepancy_variance_required | Unavailable, nonunique_gls_weights | Populated x;v;sqrt(v) with known_covariance_common_estimate |
| known, V_D=0, D!=0 with supported common unbiased model | Retain descriptive D, variance0 and uncertainty0 | Unavailable, inconsistent_deterministic_constraint | Unavailable, inconsistent_deterministic_constraint | Unavailable, inconsistent_deterministic_constraint |
| estimated, plugin V_D=0, D=0 | Populated plugin0;0; actual population variance is not identified | Unavailable, zero_plugin_difference_variance | Unavailable, nonunique_gls_weights, variance_status=estimated | Populated x;plugin v;sqrt(plugin v) with estimated_covariance_plugin_common_estimate |
| estimated, plugin V_D=0, D!=0 | Retain descriptive D, plugin variance0 and plugin uncertainty0; no scientific contradiction | Unavailable, zero_plugin_difference_variance | Unavailable, nonunique_gls_weights, variance_status=estimated | Unavailable, combined_estimate_not_identified_by_plugin_covariance |

Two reason values are added to the003 domain:

- zero_plugin_difference_variance: an estimated contrast variance is zero; standardized division is undefined and this is not a statement of population determinism.
- combined_estimate_not_identified_by_plugin_covariance: with unequal observed estimates and a singular shared plugin matrix, every unbiased allocation has the same plugin variance while giving potentially different combined values. No unique allocation or resulting combined estimate is identified by that plugin covariance.

The reason nonunique_gls_weights remains appropriate for plugin weight cells because the minimization using the plugin covariance does not select an allocation. Their uncertainty.variance_status=estimated preserves its meaning. The known-C inconsistent_deterministic_constraint reason must never be used just because a plugin variance is zero.

When D=0, the common value x and variance v under the selected covariance remain identifiable regardless of nonunique allocation, so neither combined-value/variance cell inherits the unavailable weight-cell reason. With v=0 and estimated covariance, the displayed plugin variance is0 but actual uncertainty is not thereby known to be0. No arbitrary averaging, epsilon, infinite precision or extra independence is introduced.

For unequal values under the plugin matrix, this proposal withholds combined_variance because that cell means the variance of the identified combined estimate; no such combined estimate has been selected. The constant plugin variance v of the whole family is recognized in the explanation, without adding a new family-variance component or choosing weights. This does not erase valid D=0 partials.

PLUGIN_SINGULAR_PARTIAL_EXAMPLES_003.json adds three synthetic mathematical illustrations: equal20 with plugin v4, equal20 with plugin v0, and20 versus22 with plugin v4. It records actual_population_difference_variance as unknown_from_zero_plugin_variance and scientific_contradiction_inferred=false. Known-C cases and the descriptive-protocol covariance example remain in SINGULAR_AND_PROTOCOL_PARTIAL_EXAMPLES_002.json. All are mathematical schema illustrations, not source-backed execution or newly authenticated scientific evidence.

The formulas and scalar component meanings are otherwise exactly COMPONENT_FORMULAS_AND_MEANINGS_002.json. In particular, difference_variance and difference_standard_uncertainty remain descriptive-protocol uncertainty components that do not require the common-mean model. The narrower common-estimand standardized comparison and combination still require their own declared model. Missing source covariance remains missing.

PLUGIN_CORRECTION_CHECKS_003.json records standalone metaschema checks, cell-schema validation of the three hand-constructed plugin examples and unchanged hashes for every previously existing001/002 file. No proposed component implementation or production test has run.
