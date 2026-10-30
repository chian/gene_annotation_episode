# A105: CsiD plotted dataset converted into numerical cells

2026-10-23. Research proposal, not adopted scoring or reader implementation.
This additive record follows the complete post-paper authority reread. Earlier
records remain unchanged. The native numerical values below were recovered from
a published vector plot, not an original instrument file and not synthetic data.

## Defined comparison

Knorr et al., 2018, DOI **10.1038/s41467-018-07563-6**, Supplementary Figure 5,
supplement PDF page 7: oxygen consumption by the CsiD preparation without added
inhibitor versus with **5 mM L-2-hydroxyglutarate**. The assayed construct is
N-terminal His-tagged E. coli CsiD. The comparison does not mix mutant and
wild-type proteins. The no-inhibitor arm is **not a no-enzyme blank**.

The endpoint is **micromoles oxygen per minute**, not a concentration rate or
rate per protein amount. The reported bars are means; error bars are SD;
the two selected arms each report three measurements. Separate preparation
identities and between-arm pairing are not specified. General electrode-method
conditions include 180 nM CsiD, 30 degrees C, MOPS buffer pH 7.2, ascorbate and
iron. Exact figure-specific substrate concentrations, reaction volume and stock
or vehicle differences are not established by the inspected text.

## Filled numerical cells

All extra digits are computational outputs from graph reconstruction, not
claimed instrument precision. Displayed means are approximately 0.161 and
0.105 micromoles/minute.

| Cell | Inputs/calculation | Value | Meaning and limitation |
|---|---|---:|---|
| Control mean | Bar position against labelled ordinate | 0.16062356 micromoles/min | No-inhibitor preparation rate |
| L2HG mean | Bar position against the same ordinate | 0.10483983 micromoles/min | Preparation rate with 5 mM L2HG |
| Control SD | Upper whisker minus mean | 0.01025723 micromoles/min | Reported measurement SD; not between-preparation SD |
| L2HG SD | Upper whisker minus mean | approximately 0.01091 micromoles/min | Same qualification |
| Rate difference | control minus L2HG | 0.05578373 micromoles/min | Observed preparation-level contrast |
| Retained rate fraction | L2HG/control | 0.65270518 | Observed activity fraction; not evidence-transfer weight |
| Fractional decrease | 1 minus preceding ratio | 0.34729482 | 34.73% lower observed oxygen rate |
| Control contribution to mean-difference variance | SD_control squared / 3 | 0.00003507028 | Conditional on independent measurement repeats |
| L2HG contribution to mean-difference variance | SD_L2HG squared / 3 | 0.00003967367 | Same assumption |
| Difference variance | Sum of preceding terms | 0.00007474395 | No shared covariance included under this stated example assumption |
| Difference standard error | Square root of variance | 0.00864546 micromoles/min | Conditional measurement error, not all experimental uncertainty |

The conditional Welch calculation gives t=6.45237, df=3.98488 and a 95%
interval [0.03174414, 0.07982332] micromoles/min. These are derived calculations,
not source-reported statistics. They do not establish independent preparations.
If the mean errors have unknown correlation rho, retain

`V_difference = V_control + V_L2HG - 2*rho*sqrt(V_control*V_L2HG)`.

Holding the two estimated variances fixed and varying rho from -1 to 1 produces
SE values from approximately 0.00037669 to 0.01222072. That range is algebraic
sensitivity, not an estimated confidence interval. Unknown calibration or
preparation variation is additional; it is not asserted to lie in that range.

## Proposed contribution for the exact measured statement

For the statement **the preparation's mean oxygen rate is higher without
L2HG than with 5 mM L2HG**, an explicitly conditional example uses independent
normal observations in each arm, with separately unknown arm variances.
For arm j, let n_j, m_j and s_j denote count, mean and sample SD and
`RSS_j = (n_j-1)*s_j^2`. The positive observed difference yields

`S = min_m sum_j (n_j/2)*log((RSS_j+n_j*(m_j-m)^2)/RSS_j)`.

The shared mean m is the best fit on the boundary of the opposing statement.
All located local minima were checked, rather than assuming a unimodal
optimization. This gives **S=5.50823000**, and the proposed normalized fit margin
`B=tanh(S/2)` gives **0.99192617**. B is not an annotation probability or a
probability that the causal explanation is correct. Reversing the ordered
statement reverses S and B. A common-variance model gives a different result;
similar displayed SDs alone do not select that model.

The bar/whisker reconstruction and the separate plotted-marker reconstruction
give B approximately 0.99193 and 0.99177. They are two reconstructions of the
same observations, not independent evidence or a guaranteed digitization bound.

## How this fits the user's scoring sheet

- **Signal and uncertainty:** the measured contrast and separate variance terms
  enter the defined calculation above. The ratio and difference are overlapping
  descriptions of one experiment, not two contributions to add.
- **Comparability outside the intended variable:** inhibitor addition is the
  deliberate contrast. Unknown arm-specific pH, vehicle or substrate differences
  are not assigned zero effects or a generic similarity grade. A measured
  condition response and its uncertainty would enter the correction calculation.
- **Isolation:** absent no-enzyme, contaminant and oxygen/product-coupling
  measurements prevent this contrast from becoming a quantified protein-specific
  product-formation contrast. A separate product-identification experiment does
  not measure simultaneous productive coupling in this electrode interval.
- **Target relationship:** this example supplies no sequence, structure, site,
  phylogenetic or system correspondence to a novel annotation target. Its
  target contribution remains unknown. This does not erase the measured source
  result or require every investigation to perform a new target assay.
- **Experiment boundary:** single-concentration inhibition is not a fitted Ki.
  Genetic, growth and restoration findings remain A106 rather than entering
  this A105 molecular-activity calculation.

## Inspection and arithmetic record

The parent inspected the retained paper packet, primary purification and CsiD
electrode/NMR/stereospecificity Methods, the supplement caption and the rendered
page 7 figure. The earlier web page response was truncated; complete article,
complete supplement and original electrode traces are not claimed inspected.

After the paper inspection the parent fully reread root AGENTS.md and GOAL.md;
EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION, TOOL_KNOWLEDGE and TASK_AND_STEERING;
their required task/axis amendments; VERBATIM_DIRECTION and VERBATIM_RECOVERY_002;
EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS; the numerical review002 template; local
AGENTS and A105 assignment; and the latest active goal, in six nontruncated reads.

The parent read and reran the source worker's vector-reconstruction/checker
without changing its source or prior output. Results are retained in
`parent_checked_csid_003.json`. Checks cover geometry agreement, unit scaling,
ordered statement reversal, multiple local boundary minima and preservation of
unknown fields. No production reader, scorer, annotation policy or run changed.
