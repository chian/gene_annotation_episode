# A105 Kaster contributor and endpoint current audit

This additive audit follows the retained Kaster paper packet
`research/experimental_scoring_review_2026-10-23/a105_quantitative_contributor_case_238/REPORT_001.md`.
It does not change the paper report or the fixed user goal. After reading that
packet, root reread the complete goal and per-paper authority set specified by
`research/experimental_scoring_review_2026-10-23/AGENTS.md`, in sequential
untruncated parts; the relevant complete current endpoint-signal input,
calculator and TASK contracts were then read. Latest user instructions were
the supplied root AGENTS text and "can you keep going".

The studied subject is purified native *M. marburgensis* MvhADG/HdrABC complex,
with constituent subunits coexisting. Fig. 4 follows MTZ reduction at 320 nm
after adding the complex, under a limiting CoM-S-S-CoB condition. The displayed
late extrapolated trace is a source correction model, not a matched independently
measured contaminant rate. Under the selected reading, y(initial)=39,
y(baseline at addition)=170, and y(late)=181: total amplitude 142 pixels,
baseline-corrected amplitude 131, additional amplitude 11, and retained
fraction 131/142 = 0.9225352. The enclosures are manual reading bounds, not
experimental confidence intervals. The actual selected sheet marks the
retained fraction **conditional** because baseline applicability and fast
completion are scenarios, not established by the image alone. The original
source reader and selected repository/typed-return tests both passed.

The separately reported route under two homodisulfides is strictly below
2 nmol/min in 0.75 mL, hence below 8/3 µM/min. Its substrate regime and
endpoint differ from the Fig. 4 trace. It cannot populate the within-assay
`g` subtraction for that trace, and the 131/142 fraction must not be applied
again to the paper's already-corrected approximately 0.6 MTZ/CoM-S-S-CoB
ratio. No path length is supplied to turn graph pixels into absolute moles.

The source-level numerical sheet can use the retained fraction as a multiplier
on the *same uncorrected amplitude* under the explicitly stated baseline
model: corrected = (131/142) × total = 131 pixels. This is one dependent
decomposition, not two independent confirmations or an overall reliability
probability. In the user's template this evaluates a named readout-validity
weakness. It does not isolate activity of HdrA from the complex or identify a
chemical product. A matched physical background rate and corresponding sample
rate would be needed for a separate molecular `q−g` contribution.

Focused command: `.venv/bin/python -B -m pytest -q` for
`test_original_source_exact_manual_reading_and_shared_enclosure` in
`tests/test_literature_endpoint_signal_components_241.py` and
`test_exact_schema_discovery_selected_sheet_and_requested_rows` in
`tests/test_literature_endpoint_signal_binding_244.py`: **2 passed in 4.59 s**.
No production code changed in this audit.
