# Additive clarifications and final arithmetic checks

2026-10-23. The proposal remains unadopted and the count remains 0/10. No
earlier file is edited by these clarifications.

## Two precise clarifications to proposal 001

1. Proposal 001's semantic-input paragraph has the typographical text
   `while “either sufficient”+gives`. Read it as
   `while “either sufficient” gives`. The intended result is 0.84.
2. The `formula.expression` field's exact JSON grammar is:

   ```text
   expression := canonical_statement_id_string
               | {"all_of": [expression, ...]}
               | {"any_of": [expression, ...]}
   ```

   Every ID string and operator array is nonempty. A leaf is a string, not an
   additional object with a `statement` key. Aliases resolve to an existing
   canonical input row before normalization. Cyclic/dangling aliases or two
   conflicting current numeric rows for one canonical statement are specific
   unresolved representation inputs; they do not get averaged or maximized.
   These are field validity conditions, not scientific acceptance gates.

The support-result status values proposed by this design are
`complete_conventional_point`, `complete_joint_profile_point`,
`identified_projection_with_missing_input`, `conditional_only`,
`interval_only`, `no_data`, `semantic_input_missing`, and
`representation_conflict`. The actual missing fields and conditional
assumptions accompany the status. A status code is not a numeric score.

## Compose the parent's already-derived numerical statement outputs

The parent supplied two earlier **synthetic numerical outputs**, rather than
new qualitative statement grades:

| Explicitly asserted required statement | Input already calculated upstream | Numerical value |
|---|---|---:|
| Molecular activity in the scoped target relationship | Conventional target contribution from the existing corrected-activity/source/correspondence calculation | 0.616595042762 |
| The declared specificity comparison | Calibrated target profile contribution from the existing covariance-aware mapping | 0.745630704507 |

For the candidate that explicitly asserts both, and without a full joint target
observation model covering both inputs:

\[
D_{A105}=\min(0.616595042762,\;0.745630704507)
        =0.616595042762,
\quad c_{A105}=0.616595042762.
\]

The result is `complete_conventional_point` **conditional on those complete
upstream inputs and this explicit candidate definition**; it is not a joint
likelihood just because one input originated in a calibrated model. Its
`profile_log_ratio` is null. The two native calculation routes, their original
measurement dependencies and their qualifications remain separate provenance.
This operation neither treats them as independent proof nor manufactures new
scientific measurements. The parent owns printing their complete upstream
numerical chain and actual input qualifications in the joined presentation.

If either incoming number is only conditional or has unresolved required
operands, the full-candidate point must instead use that availability/bound
contract. This illustrative calculation does not upgrade either input's status.

## Final checks actually run

In addition to the two standalone research scripts recorded in
`INSPECTION_AND_LIMITS_001.md`, a read-only `python3` check parsed
`synthetic_sheet_001.json` and verified:

- The conventional candidate's declared sufficient clause gives exactly 0.42.
- Its essential members, excluded related binding row, coverage count of three,
  original measurement union and shared-observation map are consistent.
- The exact linear transform of native log-rate values `(3,1,0)` gives `(2,3)`.
- Transforming native covariance I gives `[[2,1],[1,2]]`; the joint output is
  `tanh((7/3)/2)=0.8232006455858831`.
- The supplied parent-output conjunction gives `0.616595042762`.

These checks passed. No production model, reader, scorer, annotation-store
adapter, scientific run or full ten-axis hypervolume computation was executed.
