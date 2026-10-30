# A105 case167 current calibration audit

This is an additive current-state audit of the retained WST-8 G6PD paper packet at
`research/experimental_scoring_review_2026-10-23/a105_calibration_primary_case_167/REPORT.md`.
The packet's original implementation-gap wording remains historical. The user's
fixed goal and original paper are unchanged.

## Reset and current implementation inspected

After reading the retained case167 paper-specific report, root re-read the full
user-supplied goal; `AGENTS.md`; `docs/EPISODE_STRUCTURE.md`,
`docs/TIME_AWARE_ESTIMATION.md`, `docs/TOOL_KNOWLEDGE.md`,
`docs/TASK_AND_STEERING.md`; the TASK/STEERING and evidence-axis-review
amendments; the verbatim direction and recovery records; the evidence-axis
library amendment; the numerical sheet example; the complete per-paper
`AGENTS.md`; and `SOURCE_CORRECTIONS.md`. A first combined read of the last
three was truncated; each was then read completely before interpretation. The
latest human instructions were the supplied root AGENTS instructions and
"can you keep going".

Current `literature_calibration_recovery_inputs.py`,
`literature_calibration_recovery_calculations.py`, storage, rendering, prompt,
and the original-source binding test were inspected. The measurement-validation
calculator, relevant input contract and original-source tests were inspected
for coverage. Current calibration extraction is a source-span reader, the
calculator populates numerical cells, and storage returns selected typed rows.
It is a source-level A105 section, not final annotation credit.

## Paper measurements and sheet scope

The selected original-source test covers the buffer NADPH standard 8.6/8.72
nmol and FBS G6PD enzyme-activity spike 1.024/1.235 nmol/min. The source
reports the latter as 120.57%; direct arithmetic on displayed operands is
120.60546875%, a difference of 0.03546875 percentage points. Current rows
retain both. FBS measured SD 0.004 nmol/min yields descriptive measured CV
0.004/1.235 = 0.0032388664. The denominator's provenance, uncertainty and
covariance are unavailable, so recovery variance and a correction of another
sample remain unavailable.

The buffer standard and serum enzyme spike are distinct experiments. Neither
the 8.72/8.6 ratio nor its inverse is a justified reporter correction for the
serum or complete G6PD assay matrix. Recovery, bias and inverse reuse the same
two measured operands. The remaining Table 2 standards (4.3/4.39 and
12.9/12.98 nmol) can be selected by the same reader, but this audit did not
execute their selected binding. The separate measurement-validation section
does read original Table 2 within- and between-run CV and reported Z-prime;
its conditional squared-deviation calculation is not a verified independent
predictive error estimate.

Table 3's purified G6PD WST-8/UV specific activity contrast
12.51/14.88 = 0.8407258065 is not populated by this calibration reader or
measurement-validation reader. The enzyme concentrations differ by 4/3
between methods, so this is a descriptive protocol contrast, not an isolated
detector-gain factor. A selected source-level comparison with these protocol
conditions remains work to do. The article also lacks the numerical matched
sample/blank absorbance and product-identity or active-fraction measurements
needed for a corrected molecular activity and attribution.

## Verification

`.venv/bin/python -B -m pytest -q` on the two original-source tests in
`tests/test_literature_calibration_recovery_binding_173.py` passed: **2 passed
in 14.43 s**. Two initial attempts with system `pytest` failed during import
because the workspace package and then BioPython were absent from that
interpreter; they were not scientific or implementation test failures.

No production changes were made in this audit. A105 remains incomplete as a
general paper scoring sheet; the two tested recovery controls are implemented.

The current original Table 2 measurement-validation pure test was then run for
all three reported standard rows: `test_original_source_six_alternative_precision_models_and_reported_z`
in `tests/test_literature_measurement_validation_205.py` gave **3 passed in
0.69 s**. It verifies selected within-/between-run CV and reported Z-prime
handling, including conditional rather than falsely supported squared-error
interpretation. It does not establish an independent held-out calibration stock.
