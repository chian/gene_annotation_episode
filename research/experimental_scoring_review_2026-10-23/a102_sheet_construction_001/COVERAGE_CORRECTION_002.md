# Correction to the parent AF2372 record

The parent record AF2372_PARENT_CONVERSION_001.md incorrectly attributed
`n/max(L_target,L_reference)` to the current worker draft's general extent
formula. The current worker draft, A102_numerical_sheet_draft_002.md, uses:

    symmetric_coverage = 2*n/(L_target + L_reference)

Both give 209/252 for AF2372–MJ0109 because both lengths are 252. Thus the
reported AF2372 arithmetic and the 2-angstrom descriptor 0.530793650794 are
unchanged. They differ for unequal lengths and must not be interchanged.
For 100 matched positions with lengths 100 and 200, the former gives 1/2 and
the current worker convention gives 2/3.

The parent check_af2372_001.py tested the former descriptor. Its 17-check
receipt remains a valid receipt of that calculation, not a verification of
the worker's general symmetric-coverage formula. The new parent checker
check_a102_review_002.py explicitly tests the latter formula and this
distinction. This correction preserves the erroneous attribution for audit
instead of silently changing the earlier record. Neither extent convention
is adopted as production scoring by this correction.
