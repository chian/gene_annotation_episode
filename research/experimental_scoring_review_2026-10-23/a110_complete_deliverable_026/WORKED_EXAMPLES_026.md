# Filled A110 examples and complete numerical chains

Use the equations and cell names in
[the current sheet](A110_CURRENT_NUMERICAL_SHEET_026.md). Published numerical
inputs below come from retained paper-specific conversions inspected in this
workload. Primary reading belongs to the earlier worker; source coverage is
itemized in [the source record](SOURCE_AND_ASSESSMENT_026.md). All numbers in
examples 3–5 are synthetic. They fill otherwise missing operations without
filling any published observation or the project's annotation target.

## 1. Published NfnAB: two reaction-direction constraints

The retained source packet describes purified recombinant *Clostridium kluyveri*
DSM555 NfnAB expressed together in *E. coli*, with both tagged subunits and FeS
reconstitution. NfnA and NfnB coexist; this is not a mutant replacement or
wild-type/mutant mixture. Ferredoxin and hydrogenase were from *C. pasteurianum*.
Base assays were anaerobic at 37 °C and pH 7.0. Limiting cofactor amounts and
reaction direction change. Enzyme amounts, measurement technique and regeneration
systems differ between directions, which remain two complementary questions.
[Wang et al., DOI 10.1128/JB.00612-10](https://doi.org/10.1128/JB.00612-10).

The declared author reaction, in relative redox-charge notation, is:

    Fd_red(2−) + NADH + 2 NADP+ + H+ → Fd_ox + NAD+ + 2 NADPH.

Two donated ferredoxin electrons plus two from NADH supply four accepted by two
NADP+. The unchanged NAD and NADP skeletons cancel separately. Hydrogens added
to those skeletons total two on each side (one in NADH plus one H+, versus two
in NADPH). Relative formal charge is −2+0+2+1=+1 on the left and 0+1+0=+1 on the
right. Therefore every declared atom, charge and electron residual is zero and
D=0 **on that formal basis**. This is not a full pH-specific ionic-speciation
analysis or an observation that grants independent positive credit.

The reverse reaction yields one two-electron Fd reduction per two NADPH. The
coupled hydrogenase reports one H2 per two-electron Fd reduction, predicting
0.5 H2/NADPH consumed. Substitution of supplied NADPH is conditional on the
declared consumption/readout assumptions. The uncoupled alternative predicts
1 H2 per NADPH. In the forward direction the coupled reaction makes two NADPH
while consuming one NADH, so the net reduced-pyridine-nucleotide increase is
one per NADH; simple transhydrogenation makes one and consumes one, predicting
zero net change.

| Cell | Reverse, Fig. 3B | Forward, Fig. 4A |
|---|---:|---:|
| Reported numerator | ≈1 µmol H2 | ≈0.10 µmol net NAD(P)H increase |
| Reported denominator | ≈2.2 µmol NADPH supplied | ≈0.11 µmol NADH supplied |
| y, derived | 5/11 mol/mol | 10/11 mol/mol |
| Candidate c, model | 1/2 | 1 |
| Named alternative a, model | 1, uncoupled NADPH→Fd | 0, simple transhydrogenation |
| e_c, conditional squared ratio | 1/484 ≈0.002066116 | 1/121 ≈0.008264463 |
| e_a, conditional squared ratio | 36/121 ≈0.297520661 | 100/121 ≈0.826446281 |
| s, proposed transform | 143/145 ≈0.986206897 | 99/101 ≈0.980198020 |
| Fixed within-block weight | 1/2 | 1/2 |

Every operation from the reported quantities through the conditional contribution:

    S_stoich = (143/145 + 99/101)/2 = 14399/14645
    C_reaction = (1−0)*S_stoich−0 = 0.9832024581768521.

This point is conditional on the approximate central ratios, readout assumptions,
complete coupling, and uncorrected systematic effects. Gas recovery, actual
consumed substrate, between-preparation n/variance and calibration corrections
are missing. Unconstrained nuisance effects give the unconditional reaction
contribution [−1,1]; the decimal does not imply experimental precision.

Experimental comparability is handled by keeping the directions separate, not
averaging them as one common assay effect. Effect isolation is the distinct
readout mapping: hydrogenase/ferredoxin coupling for H2, and the net 380-nm
pyridine-nucleotide change for the forward assay. The retained packet reports
8 versus 23 U/mg and identified interference in another rate method; those rates
are not a stoichiometric contradiction or extra A110 activity credit.

Fig. 3A's 1/1.1 H2/NAD+ supplied and Fig. 4B's .10/.22 net signal/NADP+ supplied
are companion readouts of the same reactions, not new independent preparations.
They retain zero additional weight in this particular two-question compilation.

The reverse endpoint also gives a supplied-reagent diagnostic:

    U_NADPH=2.2 µmol; a=2 mol NADPH/mol H2; v_star=1 µmol H2
    z=2.2/2=1.1 µmol H2; f=min(1,1.1/1)=1; s_supply=1.

Its additional weight is zero because it reuses Fig. 3B. Calculated excess
2.2−2×1=.2 µmol is not measured residual substrate, and this retrospective
supplied-amount calculation says nothing about native intracellular capacity.

For the broader native pathway account, the declared block weights are 1/3
reaction stoichiometry, 1/3 native non-energy resource capacity, 1/3 measured
energy coverage. The two latter observations are missing. Conditional on the
nominal reaction block and D=0:

    C_pathway in [(14399/14645−2)/3,(14399/14645+2)/3]
              = [−0.3389325139410493,0.9944008193922841].

Unconstrained reaction readout nuisance terms widen this to [−1,1]. The author's
model allocation `5−(2+2.5+.5)=0` mol Fd equivalents and the energy scenario
`100/[80,60]=[1.25,1.666667]` ATP/turnover are model arithmetic, not measured
native branch capacities or an energy-coverage cell. They stay out of that sum.

## 2. Published UbiUV: atom-source evidence and a missing complete account

The retained packet describes *E. coli* FBE748, an MG1655-derived ΔaroD ΔubiIH
strain with endogenous UbiU/UbiV present. The matched comparison is anaerobic LB
with 10 µM unlabeled versus C4-[18O]shikimate. Precursor isotope is the intended
change. The separate 100 µM 4-HB arm and MG1655 WT are not this comparison's
baseline. There is no purified-enzyme or wild-type/mutant protein mixture here.
The measured endpoint is the UQ8 mass-isotopologue pattern, pmol/mg wet cells.
[Kazemzadeh Ferizhendi et al., DOI 10.1073/pnas.2321242121](https://doi.org/10.1073/pnas.2321242121).

Comparability concerns the matched strain, culture, supplementation, extraction
and response. Isolation concerns donor-label dilution, exchange, indirect
redistribution and isotope-specific recovery. These are separate operands and
assumptions. Knockout/rescue or partner evidence from other experiments is not
another oxygen-tracing observation.

| Published or derived cell | Number and exact meaning |
|---|---|
| Supplied precursor fraction | p_supplied=A175/(A175+A173)=.64±.012, two injections of 3 and 9 µL; ± type unspecified |
| Product isotope experiments | n=3 independent experiments, plotted means and SD; raw replicated arrays/covariance not obtained |
| Quantification method | UQ10 internal standard; UQ8 calibration 6.25–50 pmol; no supplied numerical isotope-specific recovery error |
| Candidate label-count prediction, conditional p_pool=.64 | Binomial(3,.64) = [.046656,.248832,.442368,.262144] for k=0,1,2,3 |
| Predicted mean count | 3×.64=1.92 labeled O/product; 3×.012=.036 is only technical sensitivity |
| Two-oxygen prediction | [.1296,.4608,.4096] |
| Four-oxygen prediction | [.01679616,.11943936,.31850496,.37748736,.16777216] |

The predicted arrays are not observed UQ fractions. The current sheet's Eq. 4
convolves each count prediction with the measured baseline before comparing it
to the measured full pattern. p_pool is not measured here. An empirical full
cell still needs per-experiment baseline/labeled bins, relevant baseline tail,
recovery/covariance and donor-pool fraction or a justified bound.

The earlier worker read four mean bars with deliberately coarse image-extraction
intervals, not biological CIs, SDs, LODs or raw replicates:

| Mean-bar input, same strain/no added 4-HB | Image interval, pmol/mg | Illustrative midpoint |
|---|---:|---:|
| Baseline B727 | [43,47] | 45 |
| Baseline B729 | [8,11] | 9.5 |
| Labeled L727 | [3,5] | 4 |
| Labeled L729 | [14,17] | 15.5 |

The reduced statistic uses `b=9.5/45=19/90`, `y=15.5/4=31/8`. At the explicit
assumption p_pool=p_supplied=.64, `prediction(m)=b+m*p/(1−p)` gives:

| Model | Prediction | Squared residual at y=3.875 | s for candidate m=3 versus this model |
|---|---:|---:|---:|
| Candidate m=3 | 5.544444444 | 2.787044753 | — |
| Alternative m=0 | .211111111 | 13.424081790 | .656156561 |
| Alternative m=2 | 3.766666667 | .011736111 | −.991613412 |
| Alternative m=4 | 7.322222222 | 11.883341049 | .620044791 |

These are dependent views of one reduced statistic. The declared minimum is
−179840/181361=−.9916134119242836, **a diagnostic only**, with zero extra weight
beside the full-pattern question. Selecting the no-label alternative alone
would conceal the two-oxygen comparison. Conversely, this restricted statistic
does not reproduce or refute the publication's full-pattern interpretation.

From the image intervals: y∈[2.8,17/3], b∈[8/47,11/43]. Treating .64±.012 only
as a declared technical sensitivity domain p∈[.628,.652], the earlier checked
enclosures are m=0: [−.187729791,1], m=2: [−1,1], m=4: [−.714185513,1]. Their
minimum enclosure is [−1,1]. It does not cover unmeasured donor-pool effects.

The proposed donor half-reaction from the retained source conversion is:

    R−H + C10H10O6 → R−OH + C9H8O3 + CO2 + 2 H+ + 2 e−.

After canceling the common R skeleton, both sides contain C10 H11 O6; 2 H+
and 2 e− cancel charge. The electron acceptor for a complete catalytic net is
unidentified. A balanced open half-reaction therefore leaves complete-net D
unknown, rather than proving a closed mechanism or receiving a fabricated
deficit. No donor/acceptor/regeneration supply per required native UQ flux was
measured in these inspected inputs.

For the full requested account, retain isotope fit and native budget questions
at the declared weights (e.g. one-half each), and complete-net D in [0,1]. Both
questions are unknown in [−1,1], so C∈[−1,1]. The source-populated label fraction,
prediction arrays and reduced diagnostic remain useful cells. The next example
fills the exact full operation synthetically; it does not fill these data gaps.

## 3. Complete synthetic scalar chain, including corrections and resource demand

Every datum in this section is invented for arithmetic. A hypothetical neutral
reaction `CH2O + O2 → CO2 + H2O` is the candidate. The question is CO2 formed per
CH2O consumed, candidate c=1; a specified partial-oxidation alternative predicts
0.5, and a no-CO2 alternative predicts 0. Two fictitious independent preparations
provide the following already calibrated quantities in µmol. All correction
operands are stipulated exact for this fixture; no biological CI is claimed.

| Operand | Preparation 1 | Preparation 2 |
|---|---:|---:|
| Product-channel q_read | 5.7 | 6.9 |
| b_iso; recovery r; intended fraction lambda | .5; .8; .75 | .5; .8; .75 |
| Other contributor q_other | 2 | 2 |
| Condition x_test−x_ref; beta | 2 condition units; .5 µmol/unit | Same |
| b_comp=beta×difference | 1 | 1 |
| Consumption-channel q_read; b_iso | 10.2; .2 | 10.2; .2 |
| Consumption r,lambda,b_comp | 1,1,0 | 1,1,0 |

    N1 = [(5.7−.5)/.8 − .25×2]/.75 − 1 = 7 µmol
    N2 = [(6.9−.5)/.8 − .25×2]/.75 − 1 = 9 µmol
    H1=H2=(10.2−.2)=10 µmol consumed CH2O
    y=[.7,.9]; mean=.8; sample variance=.02; sample SD=sqrt(.02).

    e_c=((.7−1)^2+(.9−1)^2)/2=.05
    e_half=((.7−.5)^2+(.9−.5)^2)/2=.10
    e_zero=(.7^2+.9^2)/2=.65
    s_c,half=(.10−.05)/(.10+.05)=1/3
    s_c,zero=(.65−.05)/(.65+.05)=6/7
    s_chem=min(1/3,6/7)=1/3.

Using only the mean would give e_c=.04 and incorrectly erase measured variability.
The exact summary identity gives `.04+(2−1)*.02/2=.05`.

A separate fictitious target batch has usable CH2O=12 µmol and O2=6 µmol, each
required one per CO2, with v_star=10 µmol CO2. These are distinct budget
observations, not quantities derived again from the assay ratio:

    z=min(12/1,6/1)=6 µmol CO2
    f=6/10=3/5; s_supply=2*(3/5)−1=1/5.

Atoms on each side are C1 H2 O3; all species are neutral. Carbon oxidation
donates four electrons and oxygen reduction accepts four per turnover. Hence
D=0. Freeze half-weight chemistry and half-weight resource questions:

    S=(1/3+1/5)/2=4/15
    C=(1−0)*4/15−0=4/15=0.266666667.

Every measurement correction, denominator, prediction, residual, alternative,
budget, conservation term and combination is populated. The two independent
units contribute to one error estimate, not two extra question weights.

## 4. Complete synthetic isotope, closed reaction and resource chain

This is a new synthetic dataset, not a reconstruction of UbiUV. The stipulated
assay uses six defined nonoverlapping singly charged windows j=0,...,5 with +2
mass-unit spacing, equally calibrated responses and a matching unlabeled
baseline. The exact central masses are arbitrary fixture coordinates
100,102,104,106,108,110. Readout background=0, recovery=1, lambda=1 and b_comp=0
are stipulated for every amount. p_pool=.5 is separately supplied for the
fixture, not inferred from the published shikimate measurement. Each row is a
fictitious independent culture with its own paired baseline.

| Amounts, synthetic pmol/mg | j0 | j1 | j2 | j3 | j4 | j5 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline B, culture 1 | 80 | 20 | 0 | 0 | 0 | 0 | 100 |
| Labeled L, culture 1 | 12 | 31 | 36 | 18 | 3 | 0 | 100 |
| Baseline B, culture 2 | 80 | 20 | 0 | 0 | 0 | 0 | 100 |
| Labeled L, culture 2 | 8 | 34 | 39 | 17 | 2 | 0 | 100 |

Zeros here are explicitly synthetic measurements. They license no zero for a
missing published bin. Normalization divides each row by 100, so b=[.8,.2,0,0,0,0].
For m=3, f=[1/8,3/8,3/8,1/8]. Convolution before normalization gives
`u0=.8/8=.1`, `u1=.2/8+.8*3/8=.325`, and the full array below. Its total is one.

| Prediction mu over the same six windows | j0 | j1 | j2 | j3 | j4 | j5 |
|---|---:|---:|---:|---:|---:|---:|
| Alternative m=0 | .8 | .2 | 0 | 0 | 0 | 0 |
| Alternative m=2 | .2 | .45 | .3 | .05 | 0 | 0 |
| Candidate m=3 | .1 | .325 | .375 | .175 | .025 | 0 |
| Alternative m=4 | .05 | .2125 | .35 | .275 | .1 | .0125 |

The candidate residual vector for culture 1 is
`[.02,−.015,−.015,.005,.005,0]`; culture 2 is its negative. Each sums in squares
to .0009. Thus the mean data vector fits perfectly but experiment-level e_c is
nonzero. Keep that variation:

| Account | Mean squared vector error e | s comparing candidate m=3 with alternative |
|---|---:|---:|
| Candidate m=3 | .0009 | — |
| Alternative m=0 | .6784 | 6775/6793=.997350213 |
| Alternative m=2 | .0484 | 475/493=.963488844 |
| Alternative m=4 | .0324625 | 2525/2669=.946047209 |

`s_isotope=min(all three)=2525/2669`. Bins and alternatives do not multiply n
or weights. If only windows j=0,...,3 were deliberately selected, candidate
sum(u)=.975 and the correctly renormalized prediction would be
`[4/39,1/3,5/13,7/39]`; both measured rows would also need renormalization over
those four windows. This check is a diagnostic, not another scored question.

To populate the missing chemical/resource operations, stipulate a wholly
synthetic three-hydroxylation account with **a hypothetical quinone acceptor**
Q=C6H4O2 and QH2=C6H6O2:

    R−H3 + 3 C10H10O6 + 3 Q
      → R−(OH)3 + 3 C9H8O3 + 3 CO2 + 3 QH2.

The three product oxygens are stipulated to come from the independent donor
draws. This equation is an illustrative chemical model; it does not identify the
published UbiUV electron acceptor or establish that the hypothetical reaction
occurs. With common R canceled, both sides contain C48 H45 O24. All species
are neutral. Three donor half-reactions release six electrons; three Q reductions
accept six. Thus D=0 for this fully specified fixture.

In a separate synthetic resource measurement for the declared batch, usable donor
C10H10O6 is 12 µmol and usable Q is 6 µmol. Required product v_star=3 µmol.
No regeneration or competing use occurs in this stipulated batch. Each product
requires 3 mol donor and 3 mol Q:

    z=min(12/3,6/3)=2 µmol product
    f=2/3; s_supply=1/3
    S=(2525/2669+1/3)/2=5122/8007
    C=(1−0)*S−0=5122/8007=0.6396902710128638.

This is the complete isotope→component→resource→conservation→candidate chain.
If the resource observation is instead missing, retain its half-weight and
[-1,1] domain: conditional on the synthetic isotope observation and D=0,
`C∈[(2525/2669−1)/2,(2525/2669+1)/2]=[−72/2669,2597/2669]`. If the closed
reaction is also unknown, D∈[0,1] widens the lower endpoint to −1. Do not replace
either missing cell with the numbers invented above in a real source record.

## 5. Additional bounded operations: a shared-resource LP and censoring

This synthetic budget isolates the network operation. Units are µmol/min for
flows v (target output), q (fresh Qox), g (Qred regeneration) and w (Qred export).
Target output consumes three Qox and produces three Qred per output unit.
There is zero Qox/Qred accumulation:

    maximize v
    q+g=3v; 3v=g+w
    q<=1; g<=2; v<=3; all flows>=0
    3v+g<=4.

The last row is the specified shared processing-resource capacity; its unit is
resource units/min, with coefficients 3 resource units per product unit and 1
per regeneration unit. The donor-only capacity v<=3 is already expressed in
product units. Separate optimistic route budgets would spend this resource twice.

The feasible point `(v,q,g,w)=(5/6,1,3/2,1)` meets every constraint. From
`g=3v−q>=3v−1` and `3v+g<=4`, obtain `6v−1<=4`, hence v<=5/6. The witness
attains the upper bound, proving z=5/6 without running an optimizer. At demand
v_star=2, `f=5/12`, `s_supply=−1/6`. This is a budget cell demonstration, not a
second score added to the earlier synthetic batch or a claim of a balanced
unprovided regeneration chemistry.

For a synthetic normalized quantity with a documented detection bound
`y∈[0,.1]`, c=1 and a=0, the error bounds are e_c∈[.81,1] and e_a∈[0,.01].
The signed bound is `[-1,(.01−.81)/(.01+.81)]=[−1,−40/41]`. It would be invalid
to use this bound if the assay had no quantified limit or if negative background
corrections had not been resolved. For genuine contradictory independent units
y=[0,1], both candidate/alternative errors are .5 and s=0; neither unit is dropped.

A final synthetic bookkeeping error uses `2 H2 + O2 → H2O`. H totals are 4
versus 2; O totals 2 versus 1; both normalized deficits are .5, so D=.5. If the
already declared numerical question sum is S=.6, Eq. 10 gives C=.5*.6−.5=−.2.
This illustrates the conservation penalty; balanced equations alone still add
no positive observation.

The bounded new check script passed **29 assertions**. It verifies final joins,
the two complete synthetic chains, window normalization, the LP witness/upper
bound, contradiction, censoring and the defective equation. It does not run
the earlier broad grid, validate primary measurements, fit biological weights,
or implement any source reader. See `final_join_receipt_026.json`.
