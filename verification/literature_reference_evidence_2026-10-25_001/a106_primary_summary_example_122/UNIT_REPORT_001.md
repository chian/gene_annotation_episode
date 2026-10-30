# Engineering handoff: absent amount unit

The resumed repair changes only validation in
`gene_annotation_episode/literature_perturbation_summary.py`. A v2 dataset may
now declare `exposure_unit="unreported"` when both A_reference/A_restored entries
contain no value, raw-unit table, image measurement, digitization, or numerical
spread/interval endpoint. Numerical zero also requires a physical unit. SD,
SEM, confidence intervals, detection limits and untyped spreads cannot conceal
an amount statistic behind a missing point value or transformed spread scale.
Dimensionless counts/coverage and nonnumerical descriptions remain available.
This adds no source-explicitness gate to W/K/R work.

Legacy v1 and every existing physical-unit path remain unchanged. The point
calculator, all statistical arithmetic, schemas and saved reconstruction code
are unchanged. `UNREPORTED_AMOUNT_UNIT_001.patch` records the exact narrow diff;
`UNREPORTED_AMOUNT_UNIT_CHANGE_001.json` shows only `_entry` and
`read_summary_measurements` function ASTs changed. Complete affected-reader and
consumer rereads are recorded in `AMOUNT_UNIT_READ_PROVENANCE_001.json`.

`UNIT_FINAL_TESTS_003.xml` reports342passed,2deselected in78.26s: previous304
checks plus38new missing-unit regressions. These cover hidden amounts/statistics
in either role, all spread scales, zero, graph rejection before image decoding,
all four physical-unit paths, v1 rejection, retained partial information and
actual selected binding/typed receipt/read-only saved replay. An initial four
new-test failures incorrectly left the fixture's amount_role unknown while
expecting a nuisance-comparability value; the fixture was corrected. No
production change was needed for those failures.

`example_005/` is the final engineering example, using the same retained image,
source witnesses, ROI choices and scientific premises as004. Both interpretation
scenarios return27typed rows with `exposure_unit="unreported"`. No placeholder
amount unit remains. Every one of the64cell values is unchanged, and every
nonamount cell is exactly unchanged. The typed schema is byte-identical to004.
Each scenario has1selected operation,1typed receipt and3ordinary scripted-action
observations; no model call. Fresh read-only reconstruction returns the exact
admitted rows with0source/recipe/image reopens and0database mutations.

`UNIT_FINAL_VERIFICATION_001.json`, `UNIT_FINAL_COMMAND_001.json`,
`EXAMPLE_COMMAND_003.json` and per-scenario `RECONSTRUCTION.json` record the
evidence. All2030files in the sealed `pin_002_unit/` match
`PIN_MANIFEST_002.json`. Earlier outputs and pins remain historical records.
This is an engineering validation update, with no new scientific paper
interpretation or full-A106/fixed-goal completion claim.

The separate requested covariance audit remains read-only. See
`covariance_custody_audit_001/RESULT.json` and
`covariance_custody_audit_001/CURRENT_RENDER_AUDIT_001.json`.
Three explicitly constructed fixtures use: a supplied mean covariance0,
an assumed uncorrelated relation, and an estimated paired-raw covariance0.
The paired vectors have5independent units, both mean variances1 and covariance0.
All three produce contrast variance2, identical typed scientific fields apart
from sheet/data custody references, and identical current-root parent STEERING.
The unknown-covariance case correctly returns an unavailable variance with an
explicit reason. The missing distinction is the selected cross-arm covariance
kind, interpretation basis and witnesses; retained covariance rows themselves
also lack a reported/inferred/conditional basis field. Each input, actual typed
form and presented parent text is saved under its scenario directory.

No covariance schema, metadata, numerical or production change was made. Root
will assign that remaining gap separately. The controlling handoff status is
`HANDOFF_STATUS_003.json`.
