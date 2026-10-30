# Calibration-recovery reader/calculator increment169

This is a pure source-reader/calculator and proposed TASK increment. It does **not** register an operation, wire LiteratureEpisodes, persist sheets, implement a typed child return, establish assay-family coverage or complete A105. No existing production file, goal, amendment, controller, W05 or final credit formula was edited by169. All fixtures and populated examples in this directory are synthetic. No primary paper or retained paper-specific packet was opened in this coding increment.

## Owned files and interfaces

- `literature_calibration_recovery_inputs.py`: `calibration_recovery_population_schema()`, `calibration_recovery_extraction_schema()`, `read_calibration_recovery_inputs(arguments, *, read_source)`.
- `literature_calibration_recovery_calculations.py`: `populate_calibration_recovery(extraction)` and exported `VERSION`, `COMPONENTS`, `FORMULAS`, `REASONS`.
- `literature_calibration_recovery_prompt.py`: proposed `CALIBRATION_RECOVERY_TASK`. The root-printed three paragraphs are preserved with the later root-requested single-sentence correction assigning arithmetic to the deterministic calculator. Original prompt draft remains `PROPOSED_PROMPT_DRAFT_001.py`.
- `tests/test_literature_calibration_recovery_169.py`:62 synthetic cases.

The closed argument schema contains source_ref/source_kind; nullable exact witnesses for experiment, analyte, matrix, endpoint, blank_treatment and expected_quantity_basis; witnessed control_kind/applicability/spread_kind interpretations; nullable nominal/measured/measured_spread/reported_recovery numeric selectors; nullable shared_unit; and nullable reported_recovery_unit `{value: fraction|percent, witness}`. Numeric selectors contain only a source witness and character offsets within it. No entered scientific number is accepted as an operation argument.

The reader reuses the existing `_Sources` authorization callback boundary and `read_source_number` scalar guards. The callback returns exact authorized artifact_ref/content bytes for each selected reference and representation. The reader does not acquire a source or validate biological truth. Exact quotations establish bytes, not scientific role or comparison validity.

Supported common units are pmol/nmol/umol (including both micro symbols) and the corresponding `/min` activity units, with supported printed inverse-minute aliases. They normalize exactly to nmol or nmol/min. Partial units, hidden compound denominators, units split across separate table fields and explicit units contradicting the supplied shared scale are rejected. Dimensionless unit1 has separate numeric-token completeness checks; percentage and fraction headers need not be adjacent to their data values. Source field linkage remains an interpreted experimental relationship.

The extraction retains exact native lexemes/rationals, normalized rationals/numbers, actual byte spans, enriched witnesses, declared input origin and source references. Measurement keys bind artifact and original numeric byte span, independent of role or equal value. Aliases of the same artifact/span share identity; equal values at different positions remain separate. No physical or statistical independence follows.

## Numerical meaning

The component sheet returns nominal and measured quantities, signed difference `M-N`, recovery `M/N`, bias `M/N-1`, percent bias, positive inverse recovery, original measured spread, explicitly SD-only measured SD/CV, original reported recovery normalized to a fraction, and the difference between recovery calculated from displayed operands and the reported recovery. Original and derived representations remain separate. All recovery/bias/inverse components retain their shared operand dependencies.

Unknown/conflicting control kinds preserve descriptive pair arithmetic and literal measurements while marking the unresolved scientific scope. Known reporter-standard/amount and enzyme-activity-spike/activity meanings are distinct; a known control/dimension mismatch withholds interpreted recovery/bias but preserves source quantities and their difference. Negative measured quantities remain signed. Nonpositive nominal quantities cannot supply recovery, and nonpositive measured quantities cannot supply inverse correction or CV.

An SD is never inferred from SEM or an unspecified spread. Ratio variance remains unavailable because denominator uncertainty/covariance are not supplied. `correction_for_other_measurement` is always unavailable: there is no target measurement in this interface, even if applicability has been declared. This prevents transferring an inverse recovery to another assay solely from compatible units or a control label. No missing factor becomes1 or0; absence of an input is not reported as absence from the paper. No overall reliability grade, function probability or annotation credit is produced.

## Verification and dependency repair

`tests_005.xml`: **62 passed**,0 failed,0 skipped; final TASK bytes and numeric-unit clipping checks included. Command:

    .venv/bin/python -m pytest -q tests/test_literature_calibration_recovery_169.py --tb=short --junitxml=verification/literature_reference_evidence_2026-10-25_001/a105_calibration_recovery_169/tests_005.xml

Earlier failures are retained in tests001–003. They include fixture-selection corrections and the independently identified shared scalar issue: adjacent `<td>10</td><td>-2</td>` was misread as a numeric interval. Increment171 separately owns the shared helper repair. This reader contains no local bypass or masking of that rejection. The standalone synthetic reproducer remains `reproduce_shared_interval_001.py`. The final62-case suite passed using shared helper SHA2566683a39272203ff0b2844c951ab13b2333ae0ae16e3966c4eb932970f30764a8, subsequently read in full by169. Its broader regressions belong to171/root, not this receipt.

The three populated synthetic examples preserve source bytes, original selected arguments, extraction, numerical components and hashes. They contrast reporter-standard, enzyme-activity-spike and unresolved-control meanings. They are not original-source scientific examples or LiteratureEpisodes execution.

## Remaining handoff

Root must review this component definition and its source/role boundary, then separately integrate selected operation execution, persistence, exact scoped typed returns, recurring TASK/STEERING delivery and reconstruction without source reacquisition or recalculation. Original-paper examples, reported CV-only precision fields, calibration slope/intercept conversion, uncertainty of recovery, held-out calibration assessment and the complete logical A105 sheet/common subscore compilation are not completed by this increment. This implementation is one recovery-control component path, not a count of completed assay-specific graders.
