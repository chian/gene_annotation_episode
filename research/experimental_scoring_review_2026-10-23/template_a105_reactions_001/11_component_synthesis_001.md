# Chemical-reaction contributions to the A105 numerical sheet

New immutable research synthesis, 2026-10-23. Nine distinct primary papers,
covering ten assigned case groups, were freshly checked at relevant Methods,
Results and figure/table descriptions. This supplies proposed numerical cells
and explicit arithmetic within the user's scoring-sheet responsibility. It is
not an adopted sheet, reader implementation, production policy or additional
evidence about the project's target. Zero whole sheets are completed by this
work. Assay controls remain A105; perturbation/restoration and organismal growth
conclusions remain set aside for A106.

The reusable point is not a score assigned to a whole paper. It is a series of
measured contributions to the reliability and relevance of a specified
molecular inference, which can emerge during investigation. The measurements,
their proposed transformations and their joint calculation must remain
distinguishable.

## Numerical cells and what they calculate

| Component in the user's sheet | Inputs and calculation proposal | What it evaluates; limits |
| --- | --- | --- |
| Net molecular rate and uncertainty | Convert instrument signal with the actual substrate/product calibration; subtract matched background. `v = vsample − vblank`; `Var(v) = Var(vsample) + Var(vblank) − 2 Cov(vsample,vblank)`. Retain rate units and sign. | The amount of controlled chemical conversion. It is not by itself an annotation-confidence number. Different chemistry can contribute to the same optical signal. |
| Residual quantitative calibration agreement | For an independently processed held-out standard, `r = recovered amount / known amount`; proposed `Rcal = min(r,1/r)`. | Residual quantitative accuracy after the native signal conversion. Extinction coefficients and instrument response factors are conversion inputs, not standard-recovery scores. The reciprocal transformation is a proposal, not empirically calibrated error probability. |
| Precision or reproducibility contribution | Proposed `Ru = 1/[1 + V/v²]`, where V has a declared meaning: variance of the estimated mean, or between-preparation predictive variability. | Relative uncertainty about the selected rate. The `1` sets the illustrative transformation's scale and is a design choice; it has no special scientific authority. Do not multiply two versions derived from the same noise. At zero/negative effects, retain direction/bounds separately; this positive-effect component is not a complete negative-evidence score. |
| Comparability outside the intended variable | For a measured nuisance-response function gj, proposed `Cj = min[gj(xa),gj(xb)] / max[gj(xa),gj(xb)]`; `C = product(Cj)` only for nonredundant separable responses. Equivalently `log C = −sum(abs(log(response ratio)))`. | Similarity of the experimental conditions' effects on the measurement. Exclude the intentionally varied substrate/protein/partner. pH, temperature or dose differences have no universal numerical penalty without their response model. A joint response replaces a product where effects interact. |
| Productive coupling of a proxy | `q = net identified-product equivalents / net proxy equivalents`, with reaction stoichiometry and common time interval explicit. | What fraction of the proxy readout is the named chemical conversion. Values outside expected physical bounds indicate measurement/model disagreement; do not silently clip them. Product identity without product quantity cannot fill q. |
| Attribution within a mixed preparation | `I = 1 − vother/vnet`, with vother measured or identified by a justified mixture model, in the same calibrated product-rate units. | The fraction of measured chemical activity attributable to the intended protein. A protein's mass purity is not its activity fraction. If vother and vnet do not identify a physical partition, I remains uncomputed. |
| Preference among a declared tested panel | For comparable calibrated rates, `Dj = vj/sum(vk)`; or for an efficiency question, `Dj = (kcat/Km)j / sum((kcat/Km)k)`. | Relative preference among the specified alternatives, under the stated concentration or kinetic definition. It does not score general capability, native substrate identity or untested alternatives. |
| Similarity of measured output in a different molecular system | Where the same products have calibrated fractions fs and fr, proposed `P = sum(min(fsj,frj)) = 1 − 0.5 sum(abs(fsj−frj))`. Rate and condition compatibility remain separately measured. | One possible operational comparison for a substituted versus relevant partner/system. Equal product distributions do not establish equal rates, identical molecules or universal transfer of function. This supplies a concrete non-sequence relationship measurement when data exist, not a general transfer grade. |

The letters are local formula symbols for individual measurable contributions;
they are not the rejected R/V/A/T categories. Missing operands stay missing.
No model judgment selects 0, .25, .5, .75 or 1 as an overall category score.

## What the contrasting papers establish

**Calibration affects apparent selectivity before scoring begins.** FolM's
composite optical coefficients at pH 6 are 6,028 for dihydromonapterin and
12,300 M⁻¹ cm⁻¹ for dihydrofolate. A reported 16-fold molar-rate preference at
50 µM corresponds to only `16 × 6028/12300 = 7.84130` times the optical slope.
The preference proposal gives `D = 16/17 = 0.941176`; the raw slope cannot be
substituted for it. The substrate's intended chemical difference is excluded
from nuisance comparability. A no-enzyme blank corrects background oxidation
but does not isolate direct use of an unstable quinonoid substrate that
rearranges into the ordinary substrate. [FolM, 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2805310/).

**Large selectivity ratios need compatible experiments.** CysQ's reported
efficiencies are 42 for PAP, .0027 for IMP and .025 for FBP, in µM⁻¹ min⁻¹.
The raw PAP/IMP ratio is 15,555.6 and the raw three-substrate share is .999341.
However, the PAP and alternative assays differ in pH, Mg concentration, enzyme
dose, incubation and measurement chemistry. The 20-fold Mg difference is not
a `1/20` penalty: measured response to Mg would determine its effect. Enzyme
dose already used to normalize kcat is not penalized again. Substrate depletion
is separately relevant to initial-rate validity: conditional integrated
Michaelis–Menten arithmetic with 25 µM starting PAP, 15.75 µM ending PAP and
Km 8.1 µM gives an average/initial-rate factor .942622. Reusing a Km fitted from
the same data is not independent validation. [CysQ, 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2711008/).

**A positive artificial-substrate reaction is not native-function specificity.**
FrsA hydrolyzed p-nitrophenyl acetate with reported Km 18.6 ± 1.3 mM and kcat
.67 s⁻¹. Its highest tested substrate concentration was 6 mM: `Smax/Km =
.32258`, corresponding to `Smax/(Km+Smax) = .24390` of fitted Vmax. Those
numbers expose extrapolation; neither is an automatic validity grade.
The efficiency kcat/Km may be better identified than either parameter alone,
so its uncertainty requires their covariance:
`Var(log(kcat/Km)) = Var(log kcat) + Var(log Km) − 2 Cov(log kcat,log Km)`.
A proposed uncertainty component then uses that propagated variance. Gel
purity above 95% cannot fill 95% attribution. Native substrate relevance is
unfilled by an artificial-substrate result. [FrsA, 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6450606/).

**Matched experimental conditions do not resolve contamination.** Aquifex HFP
preparations contained E. coli RpiA, with ribulose/ribose-5-phosphate
isomerization contributing to a multienzyme assay. Four of five preparations
showed isomerization; `.8` is preparation prevalence, not the fraction of
activity caused by the contaminant. A purification-stage estimate of 5 mg/mL
HFP in 7 mg/mL total protein is a .7143 mass fraction, not I = .7143, and
cannot be transplanted to a later purification stage. An equilibrium
composition of 39.7% Ru5P and 60.3% R5P is not a catalytic partition either.
An activity-attribution fraction needs matched contaminant quantity and
activity or an experiment that resolves its flux. [HFP, 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/).

**The measured enzyme system can change an apparent preference.** With one
CofC/CofD pair, the F420 study reports final-product rate shares of 65%, 26.5%
and 8.5% for 3-PG, 2-PL and PEP. Changing the downstream partner changed the
observed preference. The final rate for substrate j is not the isolated CofC
rate: a useful model is `vfinal,j = aactivation,j × qpartner,j`. Synthetic
partner conversion fractions `(1,.5,.1)` would turn final rates `(65,26.5,8.5)`
into activation-rate estimates `(65,53,85)`, whose shares are `.320197,
.261084,.418719`, reversing the apparent ranking. Those q values are invented
to demonstrate identifiability, not measurements from the paper. In the
partner-swap experiment, partner identity is the intended change and excluded
from C. When carrying an assay result to a system with a different partner,
measured output overlap P can instead help quantify that relationship. These
are different questions, not two penalties for the same swap. [F420 precursor
selection, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8764529/).

**Sequence identity is not an activity-transfer percentage.** TriA and AtzA
differ at nine of 475 positions, giving 98.1053% identity, while their reported
substrate activities differ substantially. TriA melamine activity is
245 ± 2 nmol min⁻¹ mg⁻¹ total preparation protein. The atrazine nondetection
limit is 10 pmol min⁻¹ mg⁻¹, or .01 in the same units. If initial positive and
extended negative assays are shown comparable, the limited ratio is greater
than 24,500 and the two-substrate fractional preference is greater than
`245/(245+.01) = .999959`. This is a conditional bound, not a zero alternative
rate or a 99.9959% probability of function. Partial purification and total
protein normalization also prevent direct comparison with a highly purified
AtzA rate without protein fraction/activity attribution. [TriA/AtzA, 2001](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/).

**Stoichiometric normalization must follow the reaction.** QueF reduces a
nitrile to an amine using two NADPH per product. Its productive-coupling
fraction is `q = 2 × product formed / NADPH consumed`. With .5 mM substrate
and .5 mM NADPH in the NMR setup, the maximum product is .25 mM: 50% substrate
conversion would exhaust NADPH, not demonstrate 50% defective activity.
Product yield must use `min(substrate, NADPH/2)` as its stoichiometric maximum.
The paper's at-least-three replicates with relative standard errors below 10%
would imply `Ru > 1/(1+.1²) = .990099` **for uncertainty of the mean** under
that proposed transformation. It does not establish independent-preparation
consistency. NMR and product coelution address chemical identity without
supplying a matched calibrated product/cofactor balance. [QueF, 2005](https://pmc.ncbi.nlm.nih.gov/articles/PMC555470/).

**A coupled system's increased endpoint is not the added enzyme's flux.** RidA
and IlvA coexist, while spontaneous hydrolysis produces the same ketoacid.
Adding RidA gives approximately twofold ketoacid rate at pH 7.5 and four- to
fivefold at pH 9.5. A twofold rate does not identify 50% of product as direct
RidA turnover: reducing intermediate accumulation can also change IlvA's
generation rate. A minimal partition is `dI/dt = vIlvA − vspontaneous −
vRidA − vtrap`, with ketoacid production `vK = vspontaneous + vRidA`.
Ferricyanide trapping and ketoacid measurements supply complementary
constraints. A proposed mass-balance cell is
`B = (ketoacid + trapped intermediate equivalents)/substrate consumed`, with
`Rbalance = min(B,1/B)` for quantitative closure. It cannot by itself fill
vRidA or I. Common time windows and measured blanks address comparability;
flux partition addresses isolation. [RidA, 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3270999/).

**Orthogonal chemical identity and productive coupling are different cells.**
CsiD oxygen consumption was measured at 53 ± 3 µmol min⁻¹ mg⁻¹; NMR and
stereochemical LC-MS identify L-2-hydroxyglutarate, but under different assay
conditions. Those measurements do not fill a simultaneous product/O2 coupling
fraction. Conditional substrate-saturation similarity across the kinetic/NMR
conditions gives .942478 × .918182 = .865366, assuming separable responses
and transferable apparent Km values; other condition differences remain.
LhgO's direct UQ1 reduction, .33 ± .002 µmol min⁻¹ mg⁻¹, measures an immediate
quinone reaction. Membrane oxygen consumption measures a multicomponent
electron-transfer pathway and cannot replace that immediate-acceptor
measurement. Undefined published ± values cannot be silently treated as SD or
SEM. [CsiD/LhgO, 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6265302/).

## Explicit combination and a filled arithmetic example

A candidate compilation for a **proxy-based positive chemical inference** is
`Eproxy = C × Rcal × Ru × q × I`. This explicitly compiles measured
comparability, calibration, uncertainty, productive fraction and attribution.
It is a proposed index of the specified evidence, not a probability, universal
complete A105 formula or score on a whole paper. Its transformations and product
need user review; a product alone does not establish statistical independence.

The following is an entirely new **synthetic** numerical example, not paper
data or a target experiment. Suppose independent preparations give proxy rates
1.4, 1.6 and 1.8 µM/min with respective matched blanks .2, .2 and .2. Net rates
are 1.2, 1.4 and 1.6, mean 1.4 and sample SD .2. Define Ru to evaluate
preparation variability here, not precision of the mean.

| Numerical cell | Explicit synthetic input and arithmetic | Result |
| --- | --- | ---: |
| Comparability, nuisance response 1 | Measured response ratio .95 between the two conditions | .95 |
| Comparability, nuisance response 2 | Measured response ratio .90; assume demonstrated separability from response 1 | .90 |
| Combined condition comparability C | .95 × .90; intended substrate/protein difference excluded | .855 |
| Residual calibration Rcal | Held-out 10.0 µM standard recovered as 9.8 µM; min(.98,1/.98) | .98 |
| Preparation consistency Ru | 1/[1+(.2/1.4)²] | .98 |
| Productive coupling q | 9 µM calibrated product equivalents / 10 µM proxy equivalents in one matched interval | .90 |
| Attribution I | 8.55 µM intended-protein product / 9 µM total identified product, independently resolved | .95 |
| Explicit combined proposed Eproxy | .855 × .98 × .98 × .90 × .95 | .70207641 |

Here q and I partition different successive quantities: all proxy signal into
productive chemistry, then productive chemistry into intended-protein versus
other-protein contribution. They can multiply because their denominators are
defined that way. If one measured control already estimates the final combined
fraction, use it once instead. The corresponding physically attributed rate
would be `1.4 × .9 × .95 = 1.197 µM/min`; this is a corrected native estimate,
not another score multiplier. If the sheet bases its inference directly on
that corrected rate with propagated uncertainty, q and I must not be applied
again as penalties for the same loss. The alternative is to retain the proxy
and explicitly score the limitation, as this illustration does.

A preference inference can use a D component after the underlying rates are
made comparable and chemically defined. Do not require D for an inference that
the protein merely performs a reaction. If D already incorporates a correction,
do not penalize that same loss again in E. A result that does not isolate a
reaction remains a named missing cell; defaulting an unavailable q or I to 1
would falsely complete the calculation.

## Sums, replication and complementary measurements

Independent comparable preparations can first be pooled at the native-rate
level. An explicit candidate model is `wi = 1/(si² + tau²)` and
`vbar = sum(wi × vi)/sum(wi)`, where si² is uncertainty of preparation i's mean
and tau² is separately estimated between-preparation variance. Use a justified
model for estimating tau²; no tau estimate is supplied merely by knowing n.
For prediction of a new preparation, a model may use
`Vpredictive = Var(vbar) + tau²`. The relevant variance then enters the chosen
Ru once. Repeated traces, multiple figures, multiple analyses of one sample
and repeated publications do not each supply new preparation observations.

Complementary experiments fill the particular missing number. Calibrated
product/cofactor time courses address q; matched contaminant rate measurements
address I; nuisance titrations address C; independent standards address Rcal;
new protein preparations address between-preparation variation. Merely counting
the methods does not make these numbers known, and counting independent papers
is not a substitute for identifying independent experiments.

Chemical identity remains an explicit design gap when only compatible mass,
retention time or an endpoint proxy is available. A 2 ppm mass error measures
mass agreement, not a universal probability of unique product identity. A
calibrated spectral mixture can estimate the fraction attributable to a named
product; distinguishing isomers may need standards or a different measurement.
No universal identity probability is proposed from the inspected examples.

## Remaining relationships and limits

The assayed protein/construct, actual partner system and supplied annotation
target remain distinct objects. The 98.1% TriA/AtzA sequence identity cannot be
used as a 98.1% function-transfer coefficient. Measured sequence alignment,
structural correspondence, mapped relevant features and direct chemical
interchangeability can contribute numerical relationship information where
available; a single ordinal transfer grade cannot replace them. This workload
did not acquire the project's target-to-assayed-protein data and therefore
fills no target relevance factor. Output-distribution overlap is one concrete
proposal for an experimentally measured system relationship, not a solution
for all transfer evidence.

Negative evidence requires numerical sensitivity bounds, active preparation
checks and comparable exposure. A ratio lower bound can be computed when
positive and nondetection limits share a valid denominator. “Not detected”
alone cannot become rate zero, infinite specificity or a categorical H value.

No production tests or scientific runs were performed. Calculator arithmetic
was checked; the three earlier arithmetic corrections remain separate
addenda. Raw curves, spectra and source datasets were not reanalysed, and
the earlier source papers quoted by the reviewed papers were not all freshly
opened. Methods/Results reading does not turn reported replicates into known
independent preparations.

Each paper note records its full post-paper authority reset. The startup-order
audit is recorded separately in 10_startup_order_audit_001.md: initial evidence
extraction was restricted to the two case groups from the same CsiD/LhgO paper,
not a bulk multi-paper packet. The audit itself exposed that first retained
note again, so all fourteen authority documents were fully reloaded and read
again, latest local instructions last, before this synthesis. All writes by
this workload are new files under template_a105_reactions_001; previous records
remain unchanged. This is one research contribution toward the first of ten
scoring sheets, with formulas still unadopted and no complete sheet claimed.
