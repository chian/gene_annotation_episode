# Additive representation clarification

Root directed this clarification on 2026-10-25 after B's numerical review:
`report_count_difference` remains exactly selected report count minus selected
independently observed count. Its `numerator` and `denominator` are both null
because subtraction is not a ratio. The two actual ordered measurement
references remain in `Component.operand_measurement_refs` and the originating
`CalculationBinding.operand_measurement_refs`; their complete values remain in
the saved Sheet. No formula, measurement, registry or frozen195 asset changed.

The signed difference fixture retains report1, observed2 and value−1 while
asserting both ordered operand references and null ratio fields. Missing
operands still yield a typed null result without finding hidden sheet operands.
