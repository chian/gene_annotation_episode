Final provider review on 2026-10-25 found a family completeness edge case after
the first 63-test full pass and the first complete example generation.

An actual retained complete empty unfiltered native table establishes its own
category's zero eligible tests. It cannot establish zero tests for an additional
declared category that has no selected table or complete statistical population.
The native-tables branch without eligibility statistics previously omitted this
category-coverage check. It now requires selected native table categories to
cover the whole declared all-eligible category population. An explicitly selected
test subset keeps its own subset semantics.

The new test initially used aa_two_groups; that passed because conserved native
NA rows already made eligibility unknown. This non-discriminating check is
retained as review-failure-008.log/XML (despite the filename, one test passed).
The corrected check uses the retained all_missing table and an explicitly
unobserved second category. review-failure-009.log/XML captures the actual
one-test failure before the fix. scoped-010.log/XML records all 36 scoped tests
passing after the fix. No mathematical calculator or historical record changed.

EXAMPLES_001 and EXAMPLE_MANIFEST_001.json remain the original generated files.
The additive replay_final_002.py and FINAL_REPLAY_002.json validate their exact
values against final source hashes, without rewriting saved examples. The
additional category is a negative validation fixture, not new scientific
evidence or a native execution.
