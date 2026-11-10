# A110 proposed numerical sheet — material to print for feedback

A110 scores the proposed chemical and pathway account: measured reaction proportions or atom sources, conservation, and quantified resource supply relative to demand. Balanced chemistry alone earns no positive evidence, and neither activity magnitude nor partner-homology scores are awarded again here.

For a measured chemical quantity y, the proposed account predicts c and a named alternative predicts a. Use the actual calibrated quantity and its denominator:

\[
e_c=\operatorname{mean}_i(y_i-c_i)^2,\qquad
e_a=\operatorname{mean}_i(y_i-a_i)^2,\qquad
s=\frac{e_a-e_c}{e_a+e_c}.
\]

Set s=0 when both errors are zero. Otherwise s ranges from −1 to +1. The errors stay visible: this is a signed comparison with a specific alternative, not a probability. For source summaries with known sample SD and n, include variability using `e_h=(mean−prediction)^2+(n−1)SD²/n`. Repeated portrayals and technical samples do not multiply the score.

Condition comparability and effect isolation enter separately through measured corrections. For an established linear readout model:

\[
y=\frac{(y_{read}-b_{iso})/r-(1-\lambda)y_{other}}{\lambda}
  -\sum_l\beta_l\Delta x_l.
\]

Here b_iso is measured background, r recovery, λ the signal-contributing fraction, and β_lΔx_l the measured effect of a condition difference. Unknown corrections remain unknown. The sheet does not turn “similar conditions” or “good attribution” into category numbers.

The NfnAB paper reports approximately 1 H2 per 2.2 NADPH supplied in one direction, and 0.10 net NAD(P)H increase per 0.11 NADH supplied in the other. The declared coupled chemistry predicts 0.5 and 1; the specified simple uncoupled accounts predict 1 and 0. These are molar ratios, not reaction-rate rewards. [Wang et al., DOI 10.1128/JB.00612-10](https://doi.org/10.1128/JB.00612-10)

| Chemical constraint | Observed ratio | Claim | Alternative | Proposed signed component |
|---|---:|---:|---:|---:|
| H2/NADPH supplied | 5/11 | 1/2 | 1 | 143/145 = 0.986206897 |
| Net NAD(P)H increase/NADH supplied | 10/11 | 1 | 0 | 99/101 = 0.980198020 |

With a declared half-weight for each direction:

\[
S_{stoich}=\tfrac12(143/145)+\tfrac12(99/101)
 = 14399/14645 = 0.983202458.
\]

This fully checked point calculation is **conditional** on the source's approximate ratios and the readout assumptions. The paper does not supply numerical recovery, actual consumption and between-preparation uncertainty sufficient for an unconditional confidence claim. The result applies to the specified purified-system reaction account. It is not a complete native pathway score.

For resources, use measured available amount or flux divided by required stoichiometry. In a simple budget, `z=min_i(U_i/a_i)` is the maximum supportable output; with stated required output v*>0:

\[
f=\min(1,z/v^*),\qquad s_{supply}=2f-1.
\]

A shared network budget preserves regeneration, alternative routes, measured capacities and resource competition. Gene presence alone does not supply a rate. The proposed `2f−1` transform makes the physical demand fraction numerical without a categorical ladder; its midpoint is a proposed scoring choice.

For conservation, calculate every atom residual and the declared charge/electron residual. Normalize each atom residual as `|product−reactant|/max(product,reactant)` and take D as the largest normalized atom/charge/electron deficit. Unknown terms in a purported complete net reaction leave D unknown. The proposed joined contribution is:

\[
S=\sum_g w_g s_g,\quad \sum_g w_g=1,\qquad
C_{A110}=(1-D)S-D.
\]

Weights split distinct physical questions, never papers. Unknown questions retain their weights and [−1,1] bounds. A single question with several alternatives uses the minimum signed comparison over its declared alternatives, retaining every pairwise value. For bounds, `L_question=min_a L_a` and `U_question=min_a U_a`. This is conservative comparison to that declared set, not proof that all other mechanisms were excluded.

The NfnAB formal reaction has D=0, so the conditional reaction-account contribution is **0.983202458**. If the requested account also includes native non-energy resource capacity and measured energy coverage, an equal three-block proposal retains the latter two as unknown:

\[
C_{pathway}\in[(0.983202458-2)/3,(0.983202458+2)/3]
=[-0.338932514,0.994400819],
\]

conditional on the nominal stoichiometry component and D=0. Its unconstrained measurement nuisances widen the honest unconditional result to [−1,1]. The paper's proposed 5−(2+2.5+0.5)=0 ferredoxin allocation and conditional ATP ceiling are model arithmetic, not measured native capacities. Energy is not scored twice if already included in a joint resource budget.

The UbiU/UbiV paper provides a contrasting oxygen-donor case. Supplied shikimate is 64% labeled; a three-oxygen model therefore predicts label-count fractions **[0.046656, 0.248832, 0.442368, 0.262144]**, and an expected **1.92 labeled O atoms/product**. Those are calculated model predictions, not measured product fractions. The paper's three independent isotope experiments and plotted mean quantities inform a separate fit; raw replicate peak arrays and intracellular donor enrichment remain missing. [Kazemzadeh Ferizhendi et al., DOI 10.1073/pnas.2321242121](https://doi.org/10.1073/pnas.2321242121)

A deliberately restricted two-bin calculation uses four visible Fig. 4D means, with coarse plot-reading bounds, and demonstrates the danger of choosing an easy comparator:

| Three-oxygen claim compared with | Conditional midpoint s | Bound from plot extraction and technical label variation only |
|---|---:|---:|
| No donor-label incorporation | 0.656156561 | [−0.187730,1] |
| Two donor oxygens | −0.991613412 | [−1,1] |
| Four donor oxygens | 0.620044791 | [−0.714186,1] |

These are dependent views of one reduced statistic. The full isotope pattern has a defined calculation in the sheet, but absent raw inputs prevent filling it precisely. These numbers are not the paper's full-pattern conclusion. The proposed mechanism also leaves an electron acceptor unidentified, so donor evidence does not establish redox closure or native resource capacity.

The concrete choices for feedback are the error-contrast transformation, minimum over declared alternatives, physical-question weights, demand-coverage normalization and conservation penalty. All arithmetic is defined; absent source values are explicitly missing. No available pathway model score was discarded. All targeted readers are marked UNIMPLEMENTED, and the research check script passed **150 arithmetic checks**. No prompt, production code, library publication, target scientific run or axis-completion status was changed.

An additional source-filled resource example uses the same NfnAB reverse endpoint: 2.2 µmol NADPH supplied / 2 required per H2 = 1.1 µmol H2 supply capacity, relative to the reported 1 µmol H2 endpoint. Thus f=1 and s_supply=1 for this supplied-reagent question. It does not measure consumption or native supply. Its separate weight is zero because it is the same Fig. 3B observation already used above. Five additional arithmetic checks verify this calculation and that dependence treatment.
