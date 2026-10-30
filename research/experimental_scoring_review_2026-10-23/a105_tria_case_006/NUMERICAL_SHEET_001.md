# A105 numerical rows from the TriA/AtzA paper

This is a filled **component sheet for one source**, not a completed A105 axis.
It supplies numerical measurements and transformations that can enter the
user's sheet while exposing missing operands for compilation. Investigation
prompts and populating readers are separate responsibilities; neither is
implemented here. Source: [Seffernick et al., 2001](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/).

`SOURCE_RECORD_001.md` defines the assayed constructs, background contributors,
experimental conditions and inspection limits. All rows below refer to those
definitions. `paper_inputs_001.json` contains the manual source transcription;
`arithmetic_checked_001.json` contains results of `check_arithmetic_001.py`.

## Exact cells and units

| Cell | Definition / numerator / denominator | Meaning for numerical scoring |
|---|---|---|
| `reported_activity` q_s | Native Table 1 rate for substrate s, nmol product/min divided by mg total protein in the partially purified preparation | Measured preparation activity. Not purified-TriA turnover, blank-corrected activity, or confidence. |
| `reported_halfwidth` u_s | Printed ± quantity, same activity units | Retain uncertainty information without assigning it an unstated error model. |
| `relative_reported_halfwidth` | u_s / q_s | Size of the reported error term relative to its mean. It is **not** a CV or relative SE until u_s is defined. |
| `activity_ratio` r_(s,m) | q_s / q_m, using melamine q_m=245 in this sheet | Relative measured activity against a specific assayed comparator, dimensionless. |
| `log_activity_ratio` l_(s,m) | ln(q_s/q_m) | Signed activity separation on a logarithmic scale. Not a log likelihood ratio. |
| `activity_difference` | q_a − q_b | Absolute separation, nmol/min/mg total protein. |
| `reported_limit` L | 10 pmol/min/mg / 1000 = 0.01 nmol/min/mg | Analytical nondetection boundary, not zero, blank or statistical variance. |
| `inhibition_fraction` i | Reported percent inhibition / 100 | Fractional rate reduction relative to that enzyme's own no-competitor reaction. |
| `residual_rate_fraction` f | v_with / v_without = 1 − i | Activity remaining in the inhibitor experiment, dimensionless. |
| `identity_correspondence` | (475−9) / max(475,475) = 466/475 | Fraction of the full longer protein span covered by identical residues. |
| `independent_preparation_count` | Count distinct identified protein preparations | Unknown: sample n=2 or n=3 does not populate it. |
| `comparability_component` | A chosen continuous calculation on measured descriptors outside the intended changed variable | Unknown here as a complete number: missing assay descriptors and scale/covariance. |
| `effect_isolation_component` | Fraction of the measured rate quantitatively attributable to the assayed molecular subject, after measured backgrounds | Unknown: no quantitative partition or blank rates. |

These are distinct cells. `identity_correspondence`, purity, substrate-rate
selectivity and assay comparability must not be relabeled as one another.

## Table 1: every substrate row mapped to numerical components

All activity numbers and the twelve limits are **reported**; ratios, logs and
relative halfwidths are **calculated**. A01 denotes the shared substrate-range
assay context: natural-sequence TriA, partial purification, total-protein
denominator, duplicate positive-rate samples, substrate concentration and initial
rate temperature not explicit. The intended variable is substrate identity.
Experimental comparability excludes that identity; attribution remains subject
to unknown background activity and purity. Table 1 is the exact source location
for every T row.

| Row | Substrate | Reported q_s, nmol/min/mg | u_s/q_s | q_s / 245 | ln(q_s/245) | Molecular endpoint / interpretation |
|---|---|---:|---:|---:|---:|---|
| T01 | Melamine | 245 ± 2 | 0.00816327 | 1 | 0 | Ammeline, with subsequent slower ammelide formation; reference identity ratio is not another experiment |
| T02 | CAAT | 135 ± 1 | 0.00740741 | 0.55102041 | −0.59598343 | Final ammelide; unstable CAOT is an inferred intermediate |
| T03 | Ammeline | 17 ± 1 | 0.05882353 | 0.06938776 | −2.66804487 | Ammelide |
| T04 | Aminoatrazine | 17 ± 1 | 0.05882353 | 0.06938776 | −2.66804487 | Corresponding hydroxylated product, hydroxyatrazine |
| T05 | Ammelide | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected; cyanuric acid not detected |
| T06 | Atrazine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T07 | Desethylatrazine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T08 | Desisopropylatrazine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T09 | Cyromazine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T10 | Fluoroatrazine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T11 | Azidoatrazine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T12 | Atratone | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T13 | Cyanoatrazine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T14 | 2,4,6-Triaminopyrimidine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T15 | 2-Amino-4,6-dichloropyrimidine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |
| T16 | 6-Chloro-2,4-diaminopyrimidine | <0.01 | unknown | <0.0000408163 | <−10.10642840 | No conversion detected |

For a nondetection, the positive rate is unknown in [0,L), and the ratio uses
the **printed melamine mean**. The displayed logarithmic bound is defined for a
positive unknown rate; exact zero has no finite logarithm. These boundaries do
not include the unspecified uncertainty of the reference mean and are not
confidence bounds on the true biological rate. The twelve repeated boundaries
are twelve tested chemical alternatives under one preparation protocol, not
twelve independent confirmations of one annotation.

Positive-rate comparisons, with every positive pair retained:

| Numerator / denominator | Difference, nmol/min/mg | Ratio | Natural log ratio | Arithmetic sensitivity using each printed ± endpoint |
|---|---:|---:|---:|---:|
| Melamine / CAAT | 110 | 1.81481481 | 0.59598343 | [1.78676471, 1.84328358] |
| Melamine / ammeline | 228 | 14.41176471 | 2.66804487 | [13.5, 15.4375] |
| Melamine / aminoatrazine | 228 | 14.41176471 | 2.66804487 | [13.5, 15.4375] |
| CAAT / ammeline | 118 | 7.94117647 | 2.07206143 | [7.44444444, 8.5] |
| CAAT / aminoatrazine | 118 | 7.94117647 | 2.07206143 | [7.44444444, 8.5] |
| Ammeline / aminoatrazine | 0 | 1 | 0 | [0.88888889, 1.125] |

The sensitivity column computes `[(x−u_x)/(y+u_y), (x+u_x)/(y−u_y)]`.
It demonstrates the effect of the printed ± sizes under endpoint perturbations.
It is **not a confidence interval, SE, or validated bound on true activity**.
No statistical significance, equivalence or replication conclusion follows from
these values. The natural-log endpoint calculations are retained in the JSON.

A focused leaving-group contrast is T04/T06: aminoatrazine and atrazine retain
the same alkyl substituents and differ at the amino/chloro substituent. Using
the reported positive mean and the analytical limit gives

```
q_aminoatrazine / q_atrazine > 17/0.01 = 1700
ln(q_aminoatrazine / q_atrazine) > 7.4383835300
```

This is an assay-condition selectivity component against a close chemical
alternative. It is not a 1700-fold affinity contrast or a confidence ratio.
Unknown substrate concentrations and saturation still qualify comparability;
unknown backgrounds still qualify isolation. It shares T04 and T06 with the
larger table and cannot be added as a new independent assay. Similarly,
melamine/atrazine gives >24500 and a log contrast >10.10642840, with a broader
chemical change than the aminoatrazine/atrazine contrast.

## Competition measurements: all seven reported contrasts

The exact denominator of every residual fraction is the initial rate for that
same enzyme and baseline reaction without the stated competitor. Methods specify
equimolar competitor and baseline substrate and triplicate samples; absolute
concentrations and raw rates are absent. TriA uses partially purified protein;
AtzA uses highly purified enzyme. Intended variable: competitor addition, then
competitor identity in comparisons between rows. Source locations: Results,
melamine-deaminase and AtzA competition sections.

| Row | Enzyme / baseline substrate | Added competitor | Reported inhibition, % | Calculated residual v_with/v_without | ln(residual) |
|---|---|---|---:|---:|---:|
| I01 | TriA / melamine | Aminoatrazine | 71.0 ± 0.6 | 0.29 ± 0.006 | −1.23787436 |
| I02 | TriA / melamine | Atrazine | 12 ± 2 | 0.88 ± 0.02 | −0.12783337 |
| I03 | TriA / melamine | Ammeline | 47 ± 3 | 0.53 ± 0.03 | −0.63487827 |
| I04 | TriA / melamine | CAAT | 49 ± 4 | 0.51 ± 0.04 | −0.67334455 |
| I05 | AtzA / atrazine | Aminoatrazine | 73 ± 6 | 0.27 ± 0.06 | −1.30933332 |
| I06 | AtzA / atrazine | Melamine | 0 ± 2 | 1.00 ± 0.02 | 0 |
| I07 | AtzA / atrazine | CAAT | 0 ± 3 | 1.00 ± 0.03 | 0 |

The linear transformation preserves each reported error term's **unknown**
statistical meaning. The log has not been given an invented symmetric error.
Zero mean inhibition is not a proof of exact no effect. N=3 does not identify
whether samples share a preparation or a control denominator.

| Comparison | Exact arithmetic | Calculated value | Interpretation boundary |
|---|---|---:|---|
| I01−I02 inhibition | 71−12 | 59 percentage points | Increased inhibition upon amino-for-chloro competitor substitution, same TriA baseline; difference variance unknown |
| I01/I02 inhibition | 71/12 | 5.91666667; ln=1.77777323 | Source's rounded sixfold inhibition statement; **not** an activity or binding-affinity ratio |
| I01/I02 residual rate | 0.29/0.88 | 0.32954545; ln=−1.11004098 | Residual activity contrast, provided the control rates are appropriately comparable |
| I03−I04 inhibition | 47−49 | −2 percentage points | Observed difference; no equivalence test or interchangeable binding conclusion |
| I03/I04 residual rate | 0.53/0.51 | 1.03921569; ln=0.03846628 | Similar point estimates only |
| I05−I01 inhibition | 73−71 | 2 percentage points | Cross-enzyme arithmetic; different baseline substrates and purity prevent treating this as an isolated enzyme-identity effect |
| I05/I01 residual rate | 0.27/0.29 | 0.93103448; ln=−0.07145896 | Same cross-enzyme limitation; cannot calibrate transfer of catalytic function |

Competition may complement conversion evidence by examining recognition, but
these measurements do not fill a direct binding-affinity cell. One cannot infer
`Kd_atrazine/Kd_aminoatrazine = 71/12`. Unknown control sharing also prevents
using the apparent n values as independent likelihood multipliers.

## Other numerical rows and explicit unknowns

| Row | Inputs and calculation | Result | Source / what it evaluates |
|---|---|---:|---|
| Q01 | (475−9)/475 | 0.9810526316 | Figure 3; global sequence identity correspondence between the two natural proteins |
| Q02 | 475/475 for each span | 1 for each | Full-protein extent in the printed alignment; this coverage must not be multiplied again if using Q01's span-normalized convention |
| Q03 | 9/475 | 0.0189473684 | Fraction of differing amino acids; not probability of losing function |
| Q04 | (1425−9)/1425 | 0.9936842105 | Nucleotide identity; correlated with Q01, not another molecular experiment |
| Q05 | 124/12.4 μg/ml | 10 | Deliberately changed total-protein loading between ammeline and melamine ammelide-addition assays; rate normalization requirement, not relevance score 0.1 |
| Q06 | 100 μM added ammelide / 100 μM substrate | 1 | Measured concentration ratio for that competition control; inhibition itself remains numerically unknown |
| U01 | q_sample/q_blank | unknown | No measured numerical blank rate, so no sample/blank signal-strength value |
| U02 | q_sample−q_blank | unknown | No quantitative blank subtraction; printed specific activities must not be mislabeled net activities |
| U03 | measured calibration standard / expected standard | unknown | HPLC calibration recovery numbers absent |
| U04 | abs(m_obs−m_expected)/m_expected ×10^6 | unknown | Mass spectral claim lacks exact masses; ppm cannot be filled |
| U05 | SD_between-preparations / mean | unknown | No identified independent preparations or raw values |
| U06 | fraction of observed reaction rate assigned to TriA | unknown | Host and chemical background partition absent |
| U07 | predetermined matched functional sites / predetermined complete site set | unknown | Figure 3 gives differences but no experimentally established functional site denominator |

Missing rows are work still needed for a complete score. They do not become
zero, 0.5 or a label-coded substitute.

## How numbers combine, and which combination is still unidentified

The measured quantities already combine through explicit sums, divisions and
multipliers. The activity cell is `q_s = v_s / M_total`; a net activity would be
`q_net,s = q_observed,s − q_background,s`. For a shared preparation a mechanistic
account could be written

```
q_observed,s = f_TriA * a_TriA,s + (1 − f_TriA) * a_background,s
isolation_s = (f_TriA * a_TriA,s) / q_observed,s
```

Here f_TriA is the protein mass fraction, each a is an activity per mg of its
corresponding protein fraction, and additive contributions are assumed. This
identity makes the purity/background operands and assumptions explicit. **It
does not set either f_TriA or isolation_s to a number**, and a pure mass fraction
is not automatically the same as the fraction of catalysis. If the background
terms were negligible and the same active fraction applied to both substrate
assays, f_TriA would cancel in a within-preparation rate ratio; those assumptions
are not measurements supplied here.

Experimental comparability can separately consume measured non-target
condition differences through the existing proposed convention:

```
r_system = exp[−0.5 * delta_c^T * inverse(Sigma_c) * delta_c]
```

The intended varied substrate or competitor is excluded from delta_c for an
assay-comparability question. Missing concentrations and assay-response scales
prevent a completed numerical comparability component here. Setting unknown
differences to zero would falsely make the comparison perfect. This equation
measures condition similarity, not the attributable fraction above.

For uncertainty of a log rate contrast, if x,y were estimates with known
sampling variances and covariance, first-order propagation would give

```
Var[ln(x/y)] ≈ Var[x]/x² + Var[y]/y² − 2*Cov[x,y]/(x*y)
```

The unidentified meaning of ± and unknown covariance prevent evaluating this
variance. It cannot be recovered by assuming all reported samples independent.

The inspected source-free A105 proposal then combines normalized correspondence
components as `R_available = Σ(w_j*r_j)/Σ(w_j)` over observed relevant components
and proposes `C_target_conventional = B_source * R_available`. For the natural
TriA–AtzA comparison, the sequence-only conditional component is numerically
`R_available = 466/475 = 0.9810526316`. **B_source is not populated here:** the
paper does not provide the sampling/error model and declared competing endpoint
models needed for a source log-likelihood contrast S. Thus neither
`B_source=tanh(S/2)` nor a final C is fabricated. An activity log ratio is not S.

These missing source-score operands are an essential unresolved conversion, not
an excuse to discard the real numerical rows or substitute a categorical grade.
`CONVENTION_COMPARISON_001.md` shows the existing convention's exact consequence
and which coefficients this paper cannot identify. No new total-score formula
or adopted policy is introduced.

## Shared evidence, nondetection and complementary work

One preparation's substrate profile is a joint observation. The six pairwise
ratios and the reference-normalized rows are alternative views of the same four
means; they are not summed as six additional experiments. Reversing a ratio
changes its sign on the log scale, not its evidential count. Common reference
means induce covariance. The text, HTML table, figure, archived image and JSON
transcription are representations of one study, not independent replication.

For a likelihood treatment of a nondetection, the term would be the probability
of observing a value below the assay threshold under the specified endpoint
model, integrating its sampling distribution up to L. That distribution and
the threshold's false-negative properties are not reported here. A nondetection
cannot be substituted by exact zero or L/2, and a ratio to L is a censoring-bound
calculation, not a sample/blank or likelihood statistic.

The mismatched molecular activities and the high sequence identity remain
separate observations. A transfer score cannot erase the directly measured
substrate limitation. Equal point means on two substrates do not mean complete
functional equivalence. Binding, catalytic turnover, product chemistry and native
physiological use are different endpoints; differences among them are not
automatically contradictory replications.

Targeted additional data that would resolve particular numerical cells are:
matched substrate concentration series for rate comparability and Km/kcat;
quantitative protein purity and host/chemical blanks for isolation; calibrated
product concentrations and raw spectra for measurement validity; distinct
preparations with raw repeated rates for sampling uncertainty; and an
independently justified functional site set for site correspondence. These are
identified missing measurements, not mandatory runtime gates or experiments
performed during this review. Engineered-mutant causal work remains A106.
