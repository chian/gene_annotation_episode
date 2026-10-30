# Additive parent review and completion boundary

The parent read `NATIVE_SCORE_CONTRACT.md`, `COMPILATION_PROPOSAL.md`, and `SYNTHETIC_EXAMPLES.md` completely and retained the latter calculation as an arithmetic proposal, without selecting its coefficients. This note preserves the original files and makes the concrete limitation explicit.

For the expanded synthetic polynomial, holding the alternative-function scores and all other numerical cells fixed:

    ∂z_F/∂b_F = βb + βΔb + βbh h_F
               = 0.025 + 0.040 − 0.0002 h_F
               = 0.065 − 0.0002 h_F

    ∂z_F/∂h_F = βh + βΔh + βbh b_F
               = 0.020 + 0.050 − 0.0002 b_F
               = 0.070 − 0.0002 b_F.

Consequently the first derivative is negative for h_F>325 bits and the second is negative for b_F>350 bits. At equality the corresponding derivative is zero. The logistic transform has positive derivative for finite z, so it preserves these signs. The convention can therefore decrease the proposed contribution when a concordant native score increases, with no measured justification supplied here.

This is a concrete defect for using the toy coefficients as a default, not a newly adopted score cutoff or a reason to block evidence collection. It is not repaired by silently clipping scores or imposing those two thresholds. The parent will choose a clearer monotone numerical convention for review. The numerical example remains a checked synthetic illustration, not a completed sheet, a selected formula, or a calibrated probability. No further paper search, calibration project, implementation, or scientific run was requested or performed in response.

The parent also emphasized that absent coefficients/calibration and unspecified multi-group aggregation mean the contract alone cannot finish A101. `COMPILATION_PROPOSAL.md` makes one group contribution computable under explicitly supplied synthetic convention coefficients; the whole-sheet and real-evidence boundaries remain as stated. Unknown arithmetic inputs describe an unavailable numerical output, not a runtime gate or a prescribed investigation action.

The derivative arithmetic and declared output-file/source checks are recorded in `final_check_results.json`. Two pure synthetic arithmetic scripts passed. A preliminary source-download command using `python` failed because that executable was unavailable; the successful source retrieval and all arithmetic checks used `python3`. That failed command did not execute a scientific program or populate any successful-check claim.
