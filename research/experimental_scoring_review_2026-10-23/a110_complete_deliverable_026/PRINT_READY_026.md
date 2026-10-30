# A110 material to print for the user's numerical-sheet judgment

A110 now has one coherent proposed sheet from measured chemistry to a candidate
chemical-account contribution. It keeps the full pathway's missing resource and
redox observations visible. A105 activity and A107 partner scores are not
counted again as independent chemical evidence.

For each experimental unit, correct the actual measured quantity with separate
comparability and isolation operands:

\[
q=\frac{(q_{read}-b_{iso})/r-(1-\lambda)q_{other}}{\lambda}
 -\underbrace{\sum_l\beta_l\Delta x_l}_{b_{comp}}.
\]

Correct numerator and denominator before taking a chemical ratio. Here background,
recovery, mixture contribution and condition-response coefficients are measured
inputs; an unreported correction stays unknown. They are not subjective grades.

For corrected quantity y and candidate/alternative predictions c and a:

\[
e_c=\operatorname{mean}_i(y_i-c_i)^2,\quad
e_a=\operatorname{mean}_i(y_i-a_i)^2,\quad
s_{c,a}=\frac{e_a-e_c}{e_a+e_c}.
\]

If both errors are zero, s=0. Retain both errors because a poor fit can beat a
worse fit. The question value is the minimum over its declared alternatives,
with every pairwise comparison visible. For a whole isotope vector, sum squared
bin residuals inside each experiment, then average across experiments. Bins are
not independent repetitions.

Measured resource supplies U_i and requirements a_i per product give maximum
output z=min_i(U_i/a_i), or the optimum of the sheet's explicit shared-resource
network. For stated demand v*>0:

\[
f=\min(1,z/v^*),\qquad s_{supply}=2f-1.
\]

Calculate normalized atom, charge and electron deficits after canceling identical
species; let D be their maximum. Balanced bookkeeping alone earns no positive
observation. Freeze the physical questions and weights, then compile:

\[
S=\sum_gw_gs_g,\quad \sum_gw_g=1,\qquad
C_{A110}=(1-D)S-D.
\]

Unknown questions retain their weights and [−1,1] bounds. If S∈[S_L,S_U] and
D∈[D_L,D_U], C∈[(1−D_U)S_L−D_U,(1−D_L)S_U−D_L]. This is a signed
chemical-account index, not a probability.

The NfnAB source supplies contrasting reaction-direction measurements:

| Physical question | Reported ratio y | Candidate c | Named alternative a | s |
|---|---:|---:|---:|---:|
| Reverse H2/NADPH supplied | 1/2.2=5/11 | 1/2 | 1, uncoupled transfer | 143/145=.986206897 |
| Forward net NAD(P)H increase/NADH supplied | .10/.11=10/11 | 1 | 0, simple transhydrogenation | 99/101=.980198020 |

With half-weight each and the stated formal redox equation's D=0:
**C=14399/14645=.9832024581768521**, conditional on the approximate source ratios
and readout assumptions. Actual substrate consumption, recovery and preparation
variance remain missing. For the broader native pathway, retaining separate
one-third weights for stoichiometry, native resource capacity and measured energy
gives **[−.338932514,.994400819]** conditional on that reaction point and D=0.
Unconstrained readout effects widen the unconditional result to [−1,1].
[NfnAB source](https://doi.org/10.1128/JB.00612-10).

The UbiUV source reports supplied precursor label fraction .64±.012. Three
independent donor draws predict **[.046656,.248832,.442368,.262144]** label-count
fractions and 1.92 labels/product. These are predictions, not measured product
fractions. The full sheet now explicitly calculates:

\[
b_{ij}=B_{ij}/\sum_jB_{ij},\quad y_{ij}=L_{ij}/\sum_jL_{ij},\quad
u_{mij}=\sum_k {m\choose k}p_{pool}^k(1-p_{pool})^{m-k}b_{i,j-k},\quad
\mu_{mij}=u_{mij}/\sum_ju_{mij}.
\]

Compare y with μ over the same measured windows. The full replicated B/L arrays,
donor-pool enrichment and isotope-specific recovery remain missing. A reduced
two-bin plot diagnostic gives **+.656156561** versus no-label incorporation,
**−.991613412** versus two donor oxygens, and **+.620044791** versus four.
They are dependent comparisons with broad bounds and do not replace the full
pattern. The full redox electron sink and native resource budget are also missing,
so the full account remains bounded by [−1,1].
[UbiUV source](https://doi.org/10.1073/pnas.2321242121).

Complete synthetic examples demonstrate the operations without inventing paper
data:

| Fully synthetic chain | Explicit numerical result |
|---|---|
| Separate condition/interference corrections | Product readouts 5.7,6.9 µmol, b_iso=.5, r=.8, lambda=.75, other=2 and b_comp=1 produce 7,9 µmol; corrected substrate consumption is 10 µmol each |
| Scalar measurement and alternatives | y=[.7,.9], c=1, alternatives .5 and 0; e_c=.05, e_a=.10/.65; minimum s=1/3 |
| Scalar budget and compilation | Usable resources support 6 of requested 10 µmol: f=.6, s_supply=.2. Half-weight each, D=0 gives **C=4/15=.266666667** |
| Full isotope convolution | Baseline [.8,.2,0,0,0,0], p_pool=.5, m=3 gives μ=[.1,.325,.375,.175,.025,0]. Two specified synthetic cultures give e_3=.0009 and e_0/e_2/e_4=.6784/.0484/.0324625 |
| Isotope budget and compilation | Minimum s=2525/2669. A fully specified synthetic acceptor closes the reaction, D=0; resources cover 2/3 of demand, s_supply=1/3. Half-weight each gives **C=5122/8007=.639690271** |

The synthetic acceptor is not an identification of UbiUV's unknown acceptor.
Repeated portrayals add no weight; independent units retain their variability;
opposing observations remain; nondetection requires a measured limit. A small
shared-resource LP example also gives a checked optimum and demand conversion.

The five explicit choices for judgment are the squared-error contrast, minimum
over declared alternatives, physical-question weights, 2f−1 coverage transform,
and conservation penalty. Their arithmetic is defined; their biological
calibration remains unvalidated and they remain unadopted.

Exact targeted reader inputs/outputs are specified separately; application readers
remain unimplemented. This consolidation inspected both retained source packets
with a complete authority reread after each. Primary inspection remains attributed
to the original worker; the parent's earlier review checked mathematics. The
new bounded check passed **29 assertions**. No production or annotation changes
were made, and this worker has not marked the axis or goal complete.
