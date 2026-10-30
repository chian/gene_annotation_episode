"""Proposed recurring scientific TASK, separate from sheet definitions and math."""

CALIBRATION_RECOVERY_TASK = """Evaluate the selected recovery experiment supporting the reference molecule’s assay. Establish what was added or prepared, what was measured, the matrix, endpoint, blank treatment and source of the expected quantity. Distinguish a reporter-standard recovery from an enzyme-activity spike. A common unit or nearby table row does not establish that the quantities form the intended comparison.

Select exact source spans for the measured numerator, expected denominator, units and any reported spread. Preserve the original measurement identities and whether a spread is SD, SEM or unspecified. Calculate recovery, signed difference and relative bias from the supported pair. An inverse correction requires positive recovery, but its use on another measurement additionally requires evidence that the recovery applies to that measurement’s matrix and endpoint.

Keep precision, calibration bias and functional attribution separate. A precise recovery result does not establish product identity, eliminate interference or prove an independently validated calibration. Preserve discrepancies between reported recovery and calculations from displayed operands. Do not assume a missing uncertainty, blank or correction factor. Return the requested numerical components and their qualifications; do not produce a probability of function or annotation credit."""

__all__ = ["CALIBRATION_RECOVERY_TASK"]
