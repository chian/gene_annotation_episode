# Amount027 initial core checkpoint

Implemented only within the parent's initial exclusive ownership:

- literature_amount_inputs.py: closed source-selector schema with all fields
  required, explicit unknown/null, plus a validated finite numerical contract.
- literature_amount_calculations.py: twelve numerical components, including
  real full-covariance calculations for difference, ratio and reciprocal.
- literature_amount_prompt.py: draft recurring AMOUNT_TASK, deliberately
  unwired pending the user's running template feedback and shared ownership
  release.
- New test_literature_amount_calculations.py and
  test_literature_amount_contracts.py: 61 passed in 0.36 seconds.

The tests supply explicitly synthetic numerical operands. Their 5/7 and8.4/8.8
examples mirror the retained025 numerical meanings; they do not establish that
the new reader parsed the primary source. No new primary source was acquired.

The nonzero correlated synthetic example uses n=5, d=7 and covariance
[[0.25,0.1],[0.1,0.49]]. It produces difference variance0.54 and reciprocal
variance0.028, with signed covariance terms preserved in ratio variance.
Estimated covariance remains estimated; a missing matrix stays unknown.
Duplicate physical observations require consistent covariance rows/columns and
do not become a new comparison or independent replication.

## Additive correction to proposal001

The initial proposal's blanket exclusion of a purity interpretation was too
strong. Target and total protein are deliberately different measurands. Their
difference is not automatically method disagreement or error. A target/total
ratio is a protein mass-fraction estimate under the stated methods and stock
relationship, and can inform protein-mass purity when measurands/calibration
support that interpretation. It is not automatically validated purity, active
fraction, contaminant activity or reliability. A ratio above one remains
visible as potentially inconsistent estimates; no clipping is applied.

The implemented draft uses 'reported_point' for source reporting rather than
measurement exactness, retains lexical approximation even when that meaning is
selected, and preserves unresolved qualification explicitly. Nonpositive/noisy
reported estimates survive as quantities and signed arithmetic, but do not
produce a usable physical mass-denominator factor. The factor is an alias of
the reciprocal and is never applied to a saved rate in this increment.

## Explicit unfinished work

The actual source reader, physical unit parsing/conversion, source-owned
covariance JSON parsing/owner/unit validation, saved repository, selected C7
operation, typed returns and reconstruction remain unfinished. The module's
schema is not advertised as an implemented reader. No placeholder read function
or permanently-null uncertainty calculator was introduced.

The reader awaits the finalized024 lexical API/hash. Shared C7/services and
experimental renderer remain owned by024. No shared file, existing source
record, saved run, code pin, history, global annotation credit or controller
was changed. These pure checks do not establish a complete workflow or any
completed evidence-axis sheet; the full active goal remains incomplete.
