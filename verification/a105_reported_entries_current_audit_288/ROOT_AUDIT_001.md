# A105 original-workbook reported entries: current implementation audit

This is an additive current-state audit of the retained Yang et al. BbPK
case164. It does not replace the original paper packet, the immutable supplied
goal or a scoring policy. The original supplementary workbook is
`research/experimental_scoring_review_2026-10-23/a105_raw_rate_primary_case_164/originals/S1Data.xlsx`.

## Current scientific input to numerical cells

The selected Fig. 2B workbook block labels parallel reported activity entries
for separate D-erythrulose, L-erythrulose and DHA substrate arms. They are
reported entries, not established independent enzyme preparations. The native
unit is U/mg; its physical U definition and the exact selected block's assay
method, blank, calibration and product linkage remain unresolved. The same
D-erythrulose entries are reused in two contrasts.

The current `read_rate_observations` operation already authenticates the
original XLSX bytes, worksheet, panel, subject, native unit, group headers,
observation labels and nonformula numerical cells. Its result retains source
entry identity and explicitly unknown physical grouping/conversion. The
current `populate_rate_observation_contrast` calculates flat descriptive
means, sample SD/CV and specified same-source differences/ratios, with partial
cells for incomplete/censored/duplicate selections. No preparation SE,
corrected molecular activity or assay reliability probability follows.

| Selected numerical cell | Current source-derived value | Meaning |
| --- | ---: | --- |
| D-erythrulose source-entry mean | 0.5044733333 U/mg | Descriptive mean of three selected workbook entries |
| L-erythrulose source-entry mean | 0.1889533333 U/mg | Same native reporting convention |
| D minus L | 0.3155200000 U/mg | Reported endpoint separation |
| L/D retained fraction | 0.3745556422 | Descriptive substrate contrast; not a molecular selectivity probability |
| D source-entry sample SD | 0.03403624735 U/mg | Variation among reported entries; physical n remains unknown |

The historical case164 proposal described the XLSX reader, native-unit
arithmetic and selected binding as unfinished. Those paths now exist. The
reader and calculator remain separate from the recurring
`RATE_OBSERVATION_TASK` instructions and the saved numerical sheet.

## Verification and open integration mismatch

Focused command:

```text
.venv/bin/python -B -m pytest -q \
  tests/test_literature_rate_observations_166.py::test_original_workbook_native_arithmetic_exact_lexemes_and_shared_reference \
  tests/test_literature_rate_observations_166.py::test_original_source_shared_episode_admission_and_cold_readonly_factory
```

Result: **one passed, one failed** in 13.61 s. The original-workbook
arithmetic/custody test passed. The shared-episode case reached the parent
decision and failed its assertion that the parent TASK excludes the child's
rate-observation TASK; the renderer currently includes that child-specific
TASK from admitted rows. This is a communication-boundary mismatch under
`docs/TASK_AND_STEERING.md`, which says the parent's TASK remains its own and
admitted child facts belong in concise STEERING. A separate bounded workload
is auditing/fixing the TASK selector. The failing test is not counted as
selected integration verification. No sheet or source-cell code was changed
by this root audit.

## Subsequent boundary correction

The bounded task-selection correction is recorded in
`verification/a105_parent_task_boundary_287/HANDOFF_001.md`. It prevents an
admitted child result from adding that child's method instructions to the
parent TASK, while preserving parent STEERING and the child's own recurring
TASK. The original failing case now passes. Root independently reran that case,
the nested reported-curve case, and all eight root reported-curve combinations
against the final files: **10 passed in 159.88 s**. The earlier one-pass,
one-failure result above remains the original observation; it is not silently
rewritten. This repair validates the selected return/prompt boundary for those
controlled paths, not an actual model-backed investigation or A105 adequacy.
