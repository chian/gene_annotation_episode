# A105 HFP effect-isolation current audit

This additive audit follows the retained Aquifex HFP paper packet
`research/experimental_scoring_review_2026-10-23/a105_effect_isolation_case_234/REPORT_001.md`.
It changes neither the paper report nor the user's fixed goal. After reading
the packet, root reread the full goal and every complete per-paper authority
document in `research/experimental_scoring_review_2026-10-23/AGENTS.md`, then
the complete current `literature_compiled_assay_inputs.py`,
`literature_compiled_assay_calculations.py`, `literature_assay_inputs.py`,
`literature_product_partition_inputs.py`, and
`literature_product_partition_calculations.py` and its TASK. Latest human
instructions were the supplied root AGENTS text and "can you keep going".

HFP is the *A. aeolicus* protein expressed in *E. coli*; host proteins remain
in the assayed preparation. HFP and IMP are alternative preparations in the
reconstituted pathway vessels, while other pathway enzymes coexist in both.
31P-NMR measures a sugar-phosphate endpoint composition, not a catalyst-specific
rate. The reported R5P and Ru5P fractions are 0.603 and 0.397. The existing
product-partition reader and calculator select those original source numbers,
retain their shared preparation/endpoint/denominator, and calculate sum 1,
closure deviation 0, and R5P/Ru5P = 60.3/39.7 = 1.5188917. These are dependent
representations of one mixture. Closure of selected fractions does not establish
total phosphorus recovery or absence of unmeasured species.

The separate RpiA MS identification is a named plausible catalytic contributor,
not a measured `g` rate. The changed His tag, purification and heating also
change target recovery and conditions, so slower endpoint equilibration cannot
quantify RpiA's contribution or an HFP-specific effect. The existing compiled
sheet has the eligible same-endpoint `q−g` arithmetic, but this source does not
supply a matched initial-rate q and quantitative g under the same conditions.
Therefore HFP-specific corrected activity and isolated fraction remain unknown
from this source. The paper's reported chemistry remains useful at the
preparation level. The exact native NMR numbers and RpiA identification must
not be added as independent confirmations of HFP catalysis.

Focused command: `.venv/bin/python -B -m pytest -q` on
`test_original_primary_percentages_preserve_selected_partition_and_not_attribution`
in `tests/test_literature_product_partition_inputs.py` and
`test_original_source_selected_population_c7_exact_return_and_default_exclusion`
in `tests/test_literature_product_partition_integration.py`: **2 passed in
3.79 s**. This verifies original selected composition custody and delivery,
not quantitative molecular attribution. No production code changed here.

The focused synthetic compiler test
`test_missing_contaminant_keeps_quantitative_partial_normalizations` in
`tests/test_literature_compiled_assay_185.py` also passed (**1 in 3.92 s**).
It establishes missing-g behavior in the implemented arithmetic, not a
source-provided HFP contaminant measurement.
