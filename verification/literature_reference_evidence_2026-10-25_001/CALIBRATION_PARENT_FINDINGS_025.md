# Parent interpretation of the HFP calibration case

The parent read the complete 175-line retained analysis and same-case agent
messages, then reread the full 20-document authority/assay-contract set before
interpreting it. CALIBRATION_PARENT_RESET_025.json records those actual reads.
The parent did not independently reread the entire primary article or the
uninspected supplement. The detailed source inspection and its access exception
remain in calibration_case_025/. These are research findings, not an actual
configured-model application run or newly adopted scoring policy.

## Actual contribution to A105 component design

The experiment must retain the studied HFP preparation separately from the
workflow's supplied annotation target. HFP and IMP are alternative reference
preparations in the one-pot vessels, while contaminants may coexist within
either preparation. A change in the intended candidate enzyme and a change in
its nominal amount are separate facts.

The source reports about 5 mg/ml target HFP versus 7 mg/ml total protein for a
described stock. The target/total estimate ratio is approximately 5/7 = 0.7143.
Its reciprocal 7/5 = 1.4 is a conditional mass-denominator conversion factor:
a rate expressed per total-protein mass could be expressed per estimated HFP
mass by multiplying by that factor, only after establishing the exact same
stock, original denominator and validity of the two estimates. No activity
was corrected in this review. Do not apply the factor to a reported molar
amount or another preparation without establishing its actual amount basis;
that could double-correct an amount already estimated for HFP.

These estimates use different measurement methods and include an approximate
gel estimate. They do not provide an active-protein fraction, quantitative
contaminant activity g, recovery k, uncertainty or annotation reliability.
The field proposal therefore needs actual quantity role, amount basis,
measurement method, stock/preparation identity, unit, approximation and
uncertainty alongside the numerical ratio/factor. They are supporting
denominator/calibration components, not a generic purity grade.

For the one-pot comparison, nominal amounts are 8.4 uM HFP and 8.8 uM IMP.
The ratio 8.4/8.8 = 0.954545... describes the amount difference accompanying
the intended identity change. It is not a correction for the functional effect.
An amount-response control or a defensible source-supported model is needed
to quantify the outcome attributable to this difference. The HFP/IMP effect
itself cannot be reused as nuisance-control u/v and corrected away.

The source's contaminant detection motivates an alternative catalyst for the
observed preparation chemistry. It does not measure a matched same-endpoint
contaminant contribution. The existing corrected activity
`(q-g) * v / (k*E*u)` consequently remains unavailable for the inspected inputs.
The optical pathway endpoint also needs its own calibration/coupling model;
the current rate correction cannot infer an initial rate from a final signal.

## Existing functions and unfinished functions

- Existing exact-witness amount input can preserve the reported nominal molar
  E values. The 025 pure-reader check did so with the immutable 023 runtime;
  q/g/k/u/v remained null. It did not exercise Store population or admission.
- Workload 026 now exercises that actual repository/typed-return/reopen path
  using controlled selections and the same immutable runtime. It preserves
  nominal-recipe qualification and the static endpoint; its results are pending.
- A targeted source reader/calculator for target-specific versus total-protein
  amount estimates and conditional normalization is not implemented by this
  paper review. The existing assay contract's E accepts molar concentration,
  not arbitrary mg/ml or a cross-method purity estimate.
- Raw optical calibration, matched blank, validated time slope and quantitative
  product-to-target coupling remain distinct missing functions where needed.
  Missing corresponding source measurements cannot be supplied by new code.

No use is made of the 4/5 panel fraction as an annotation probability, of a
duration ratio as a kinetic ratio, or of multiple readout methods as independent
replication. The supplement-access failure limits absence claims to the material
actually inspected. The original source's reported unit/volume inconsistencies
are preserved rather than silently repaired.

The parent printed the two amount conversions and their scientific limits in
conversation before further implementation. A105 still requires broader
experimental validity/isolation/uncertainty work. All other appropriate
literature responsibilities, numerical sheet review and actual-model proof
remain in the complete active goal. A101 and total-credit aggregation stay out
of this implementation.
