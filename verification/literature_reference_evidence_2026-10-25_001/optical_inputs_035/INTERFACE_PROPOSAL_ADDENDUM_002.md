# Source qualification correction to proposal001

Before implementation, Q additionally requires
`qualification:I(reported_point|source_qualified_approximate|unknown|conflicting)`.
R retains this as an enriched interpretation. This corrects proposal001's Q/R
definitions; its other fields remain proposed unchanged.

The source can qualify a value outside the native parser's immediate lexical
prefix, for example "an approximate coefficient of 5000 M^-1cm^-1". The caller
must select that scientific/source reporting meaning with an actual witness.
The reader combines `source_qualified_approximate` with lexical approximation
using OR. `reported_point` cannot erase a lexical bound or approximation.
Unknown/conflicting qualification leaves exact calculator input null and retains
`source_operand_qualification_unknown` or `source_operand_qualification_conflicting`
in the dependent reasons (after the lexical censor/approximation reasons).

Knownness of source reporting is separate from statistical certainty: a reported
point with SD may be a numerical operand when the selected central estimate is
an exact lexical point; this reader does not assert measurement exactness.
Neither SD nor SEM is parsed into covariance in this workload. Covariance remains
the separately source-bound full ordered matrix, never inferred from a spread.

Add synthetic contrasts for explicit nonadjacent approximation and unknown/
conflicting qualification. A reported_point assertion with an adjacent lexical
approximation still projects null. Qualifier custody is not truth validation.
