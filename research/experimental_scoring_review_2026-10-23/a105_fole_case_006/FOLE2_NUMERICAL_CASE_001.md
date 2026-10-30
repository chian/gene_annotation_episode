# FolE2: a measured condition response in the A105 numerical sheet

2026-10-23 research case. One primary paper: Sankaran et al., DOI
[10.1128/JB.00287-09](https://doi.org/10.1128/JB.00287-09),
[PMC2772490](https://pmc.ncbi.nlm.nih.gov/articles/PMC2772490/).
This is a paper-to-sheet conversion for review. It supplies numerical cells and
their combination, not a completed A105 sheet, a new grading framework, a reader,
a prompt, or production annotation credit. The complete authority set was read
after source inspection and before this interpretation; see the provenance file.

## Define the experiments first

| Item | Metal-activation comparison | Substrate-kinetic comparison |
| --- | --- | --- |
| Actual assayed molecule | Recombinant **B. subtilis GCYH-IB**, encoded by folE2/yciA, expressed in E. coli and purified | The same named recombinant B. subtilis enzyme; the paper does not establish that this is the same physical preparation as the metal panel |
| Construct qualification | No engineered amino-acid substitution is reported for this assay. The exact cloned sequence, expression strain, affinity-tag state of this activity preparation, purification purity, and clone's B. subtilis strain are not specified in the inspected Methods; the protocol points to reference 12 | Same limitation. Do not substitute the paper's separately described N. gonorrhoeae crystallography or gel-filtration construct |
| Whether comparison proteins coexist | No second GCYH protein was intentionally added. Separate reactions contain the same named enzyme preparation with different metal conditions. Unknown contaminants remain possible contributors, not demonstrated contaminants | Separate reaction mixtures with different GTP concentrations; no deliberate protein change |
| Intended variable | **Metal condition**, including ion identity and concentration in Table 2. It is not an equal-concentration metal-identity experiment | GTP concentration, 3–50 µM, at fixed reported MnCl2 concentration |
| Fixed reported quantities | Apoenzyme 2 µM; HEPES 100 mM, pH 8.0; KCl 100 mM; metal preincubation 10 min at 37 °C; general fluorescence assay uses GTP 0.1 mM | Enzyme 0.5 µM; HEPES 100 mM, pH 8.0; KCl 100 mM; MnCl2 0.5 mM; DTT 1 mM; initial velocities |
| Additional differences/unknowns | Fe(II) assays used FeSO4 and anaerobic, degassed conditions, while other listed metals were supplied as chlorides. Actual free-metal/species concentrations, assay calibration and residual contaminant activity are not supplied | Assay temperature and fitted-parameter covariance are not specified in the kinetic paragraph. Do not silently copy the metal preincubation temperature into this assay |
| Endpoint | Fluorescence-based GCYH activity, expressed relative to the maximum Mn(II) condition. The bacterial reaction is GTP conversion to dihydroneopterin triphosphate; this paper refers to the earlier assay/product protocol rather than providing a new quantitative product-identification calibration | Apparent steady-state GTP kinetic parameters from that molecular assay, under the stated conditions |

The B. subtilis deletion/complementation growth experiments, including Fig. 2,
are parked for **A106**. They supply no rate, purity factor, or molecular-activity
score here. Their strain genotypes do not establish the identity of the purified
activity-assay construct.

## Filled measured-response cells

Table 2 reports optimum metal concentrations and relative activity. The denominator
for all positive values is the **same Mn(II) reference activity at 500 µM metal**,
not protein abundance, metal occupancy, a native-cell rate, or a separate
reference enzyme. A value of 100 is the normalization, not an error-free assay.

| Condition | Metal, µM | Reported activity, % of Mn reference | Derived target/reference response `r` | Printed spread divided by 100 |
| --- | ---: | ---: | ---: | ---: |
| Mn(II) reference | 500 | 100 | 1 by definition of the normalization | Unknown |
| Fe(II) | 1,000 | 75 ± 8 | 0.75 | 0.08 |
| Mg(II) | 100 | 43 ± 4 | 0.43 | 0.04 |
| Co(II) | 100 | 24 ± 3 | 0.24 | 0.03 |
| Zn(II) | 50 | 14 ± 1 | 0.14 | 0.01 |
| Ni(II) | 100 | 9.8 ± 1.3 | 0.098 | 0.013 |

The last column is a unit conversion of the printed ± quantities. Table 2 does
not define their statistical kind. Fig. 3 separately states that its plotted
points average four sets of triplicate assays and that the bars are SDs. The
sampling unit used to calculate those SDs and the number of independent protein
preparations are unspecified. Do not label the Table 2 column SEM, divide it by
sqrt(12), or report a confidence interval. The printed Zn spread/mean is
`1/14 = 0.07142857`; it becomes a coefficient of variation only if the spread is
established to be an SD. No measured spread is available for the 100 reference
in the table.

For this exact same-protein, condition-to-condition comparison:

```
r_Zn50/Mn500 = 14/100 = 0.14
r_Mn500/Zn50 = 100/14 = 7.1428571429
d_Zn50/Mn500 = log(r) = -1.9661128564
r_Zn50/Fe1000 = (14/100)/(75/100) = 14/75 = 0.1866666667
```

These measure a response to the specified joint change of metal conditions. A
7.14-fold response is neither a 7.14-fold change in annotation confidence nor a
metal-binding affinity. In particular, 50 and 500 µM are activity optima, not
Kd values. Fig. 3 was visually inspected; its descending branches also make a
monotone activation-only model inappropriate across the entire metal range.
No unreported points were digitized or treated as exact values.

The table prints zero with no added metal and for Ca(II), Cd(II), Cu(II), Co(III),
and Fe(III); its footnote identifies the latter conditions as no activity
detected throughout the tested concentration range. Retain `nondetected` and an
unknown detection limit. The observations are not exact physical zeroes, and
neither an infinite positive/negative contrast nor a detection-limit likelihood
can be calculated from them.

## How the condition response enters the sheet

Use the existing measured-mapping proposal's physical quantity port. Let `a_s`
be the defined source molecular response, `r_system` the measured response at
the target condition divided by the response at the source condition, and
`r_molecule` a separately established molecular correspondence when the molecule
actually changes:

```
a_t = a_s * r_molecule * r_system
log(a_t/a_unit) = log(a_s/a_unit) + log(r_molecule) + log(r_system)
```

For the metal experiment the molecule is unchanged: the molecular-transfer step
is absent, so `r_molecule=1` is an identity cancellation, not an assigned grade.
In the paper's own relative units, `100 * 1 * 0.14 = 14`. That calculation is a
complete numerical example of condition response entering the A105 sheet. It
reconstructs the same observed Zn datum; it is **not** an additional independent
prediction or experiment.

The correction is conditional on this enzyme, this assay and these metal
conditions. It does not correct activity on an unassayed homolog or predict
native-cell flux. A high measured response at one metal concentration cannot be
used to score every possible system as equally compatible. Conversely, a smaller
response does not make the evidence for the narrow statement “activity occurs
under this condition” 86% less reliable.

For positive responses and a justified joint error model, the mean correction
and its uncertainty combine explicitly:

```
z_t = z_s + d_molecule + d_system
V_t = V_s + V_molecule + V_system
      + 2*Cov(z_s,d_molecule) + 2*Cov(z_s,d_system)
      + 2*Cov(d_molecule,d_system)
```

The source experimental-reliability calculation supplies `z_s,V_s` (or its full
likelihood) after calibration/background/isolation; the system calculation
supplies its measured correction and covariance. The contribution calculation
then evaluates the resulting target endpoint once. The source-free interface
proposes, for a relevant approximately normal contrast `theta` with known
variance and a meaningful zero comparison,
`S=sign(theta)*theta^2/(2*V)` and optional `B=tanh(S/2)`. These remain unadopted
score transformations, not paper results. **No numerical S or B is filled here:**
the source data do not identify the necessary full uncertainty or isolated net
activity. A condition response cannot be relabeled as an experimental-reliability
score to fill that gap. The same response must not also multiply B as a second
overall relevance penalty.

If `d_system=log(a_Zn)-log(a_Mn)` reuses the source measurement `z_s=log(a_Mn)`,
then `z_s+d_system=log(a_Zn)`. The Mn error cancels algebraically. Similarly,
`log(r_Zn)-log(r_Fe)` cancels the common Mn denominator. Unknown covariance is
not permission to treat these ratios as independent observations.

## A second, condition-specific calculation from the reported kinetics

The same paper reports **kcat = 0.0011 s^-1** and **Km = 9.87 µM** at 500 µM
MnCl2. Under the ordinary Michaelis–Menten interpretation of those reported
parameters, evaluate the model at the two ends of the stated measured GTP
range. These are **model-derived values**, not recovered raw data points:

```
v(S) = E*kcat*S/(Km+S)
E = 0.5 µM
Vmax = E*kcat = 0.00055 µM/s
```

| Numerical cell | Calculation | Filled result |
| --- | --- | ---: |
| Apparent catalytic efficiency | 0.0011 / (9.87 × 10^-6) | 111.4488349 M^-1 s^-1 |
| Fraction of fitted maximum at 3 µM GTP | 3/(9.87+3) | 0.2331002331 |
| Fraction of fitted maximum at 50 µM GTP | 50/(9.87+50) | 0.8351428094 |
| Predicted rate at 3 µM GTP | 0.5 × 0.0011 × 0.2331002331 | 0.0001282051282 µM/s = 0.007692307692 µM/min |
| Predicted rate at 50 µM GTP | 0.5 × 0.0011 × 0.8351428094 | 0.0004593285452 µM/s = 0.02755971271 µM/min |
| Response for 50 → 3 µM GTP | [3/(9.87+3)]/[50/(9.87+50)] | 0.2791142191 |

Thus `0.02755971271 µM/min * 0.2791142191 = 0.007692307692 µM/min` is another
filled system-response combination within the stated substrate range. The
reverse correction is 3.5827626524. It does not require an invented response
coefficient, and it does not claim a new measured rate. Fitted-model adequacy,
residuals, parameter errors and concentration errors remain unknown here.

The uncertainty calculation also has an explicit form. In a consistent unit
system, the gradient of `log(v)` with respect to `(E,kcat,Km,S)` is

```
g = (1/E, 1/kcat, -1/(Km+S), Km/[S*(Km+S)])
Var(log(v)) ≈ g^T * Cov(E,kcat,Km,S) * g
```

For the 3/50 response the common E and kcat cancel exactly. Holding the declared
substrate concentrations fixed, its derivative with respect to Km is
`1/(Km+50)-1/(Km+3) = -0.06099722151 µM^-1`. The Km contribution is the square
of this derivative times `Var(Km)`, with concentration-error terms and covariance
added when measured. Fitting both endpoints with the same kcat and Km does not
provide two independent kinetic experiments. No variance is filled with zero.

Do **not** combine the 0.14 metal response with this kinetic calculation as if
factorization had been measured: the metal assay used 2 µM protein and 100 µM
GTP, whereas kinetics used 0.5 µM protein, 3–50 µM GTP and a separately stated
DTT condition. Zn-specific kcat/Km, matched mixed-metal response and the joint
metal-by-substrate surface are not supplied. The paper explicitly leaves free
versus metal-complexed GTP as the reacting substrate unresolved.

## Comparability and isolation remain separate numerical questions

**Comparability** asks whether differences besides the deliberately tested
variable change the response. The substrate panel holds the reported enzyme,
buffer and metal quantities fixed. The optimum-metal comparison deliberately
changes both metal identity and concentration; it therefore cannot isolate
identity alone. Fe(II) adds counterion and oxygen-condition differences. The
source supplies no measured response corrections for those nuisance changes.
Their numerical corrections and uncertainties remain unknown, not 1.0.

**Isolation** asks how much observed activity belongs to the intended protein:

```
v_observed(condition) = v_GCYH_IB(condition)
                        + v_other_proteins(condition)
                        + v_chemical_background(condition)
```

The paper's no-metal/EDTA controls support metal dependence, but do not identify
the three terms. A contaminating metal-dependent enzyme or a metal-dependent
fluorescence/background process could also respond to those controls. No
contribution from either is demonstrated here, and neither is proven zero.
Purity measurements, matched no-protein and process blanks, product standards,
orthogonal product quantitation and an appropriate contaminant control would
address different terms. This assignment does not open the referenced earlier
purification/assay paper; exact calibration recovery, sample-to-blank signal,
protein-specific active fraction and net-rate uncertainty are therefore unfilled.

ICP-MS metal/protein ratios are 0.048 Zn and 0.002 Mn after purification, and
0.043 Zn and 0.002 Mn after reconstitution followed by removal of loosely bound
metal. Those measurements refer to the washed preparation, not occupancy during
the reaction with added metal. They must not divide kcat to manufacture an
“active enzyme” turnover, nor become a second isolation or compatibility weight.

## Preserve the contrasting molecular relationships

The paper also gives useful **measured correspondence**, without supplying a
numerical activity calibration for a new protein:

| Comparison | Reported measurement | Limited derived cell | What cannot be inferred |
| --- | --- | --- | --- |
| B. subtilis versus N. gonorrhoeae GCYH-IB | 35% sequence identity, 64% sequence similarity; biochemical similarity described with data not shown | Retain reported percentages; exact aligned count, denominator and scoring configuration are unavailable here | A 0.35 or 0.64 target/source activity ratio; quantitative transfer of the B. subtilis metal response |
| N. gonorrhoeae GCYH-IB versus N. europaea DUF198 | 56% identity; RMSD 1.6 Å over 238 Cα atoms | 238/257 = 0.9260700389 of the reported full N. gonorrhoeae monomer span | Target-normalized coverage, active-site correspondence, activity or a calibrated functional probability |
| N. gonorrhoeae GCYH-IB versus A. flavus urate oxidase | RMSD 3.4 Å over 197 Cα atoms; reported best structural fit | 197/257 = 0.7665369650 of the N. gonorrhoeae span | Same reaction from structural similarity; urate oxidase is a different molecular activity |
| N. gonorrhoeae GCYH-IB versus E. coli GCYH-IA | RMSD 3.2 Å over 94 Cα atoms in a common core | 94/257 = 0.3657587549 of the N. gonorrhoeae span | Same metal dependence or same rate merely because the two proteins perform the same named bacterial reaction |

The coverage fractions use the paper's full 257-residue N. gonorrhoeae monomer,
not the number of resolved atoms, and describe only that side of each mapping.
The measured structure can match a different reaction over more residues than
it matches the same reaction. This is why the native RMSD/counts must remain
separate from an activity-response multiplier. No arbitrary RMSD scale,
sequence-to-rate coefficient or unmeasured target correspondence is generated.
N. gonorrhoeae Zn/Mn structures, oligomeric-mass evidence and modeled ligand
contacts are not additional B. subtilis activity replicates or binding curves.

## Exact sheet operands and remaining work

| Field group | Populating input and calculation | Present value/status | Relation to compilation |
| --- | --- | --- | --- |
| `system.response_numerator`, `response_denominator`, `relative_unit`, `condition_pair` | Table 2 values with actual metal/concentration and shared Mn normalization | Filled above | Ratio multiplies the corresponding molecular response; its log adds to the source log endpoint |
| `system.response_spread`, `spread_kind`, `shared_reference`, `joint_covariance` | Printed ± values, caption, raw paired observations if available | Spread values filled; Table 2 kind/covariance unknown | Supplies uncertainty only when its statistical interpretation is known |
| `kinetic.kcat_s_inv`, `Km_uM`, `enzyme_uM`, `substrate_uM`, `parameter_covariance` | Reported parameters/conditions; deterministic evaluation of v(S) and its gradient | Point values/model evaluations filled; covariance unknown | Supplies a separate, explicitly scoped substrate-condition mapping |
| `source.net_activity`, `calibration_recovery`, `background_rate`, `isolation_fraction` | Actual standards, blanks, purity/contribution measurements | Not numerically identified here | Must establish the source effect and its uncertainty before an annotation-evidence contribution can be claimed |
| `correspondence.identity`, `similarity`, `rmsd_A`, `aligned_Ca_count`, `source_full_length` | Reported comparisons, preserving the measured proteins and spans | Native values and one-sided fractions above | Describes source/target correspondence; no calibrated activity mapping supplied |
| `nondetection.reported_value`, `detection_limit`, `observation_kind` | Table 2 and its footnote | Printed 0; limit unknown; nondetected | No exact-zero rate or uncensored normal observation substituted |
| `replication.assay_sets`, `technical_replicates_per_set`, `independent_preparations` | Fig. 3 caption and actual preparation identities | 4, 3, unknown | Assay counts describe support; do not multiply contribution by 12 |

Reader/grader functions are **not implemented**; these are the exact proposed
cells they would populate. Table 2, Fig. 3, this report and the JSON are
representations of one metal-response dataset. Shared-reference dependence is
retained. Different metal conditions are not contradictory repeats. A genuinely
conflicting measurement under the same molecule/condition/endpoint would retain
its signed contrast and uncertainty in the same likelihood; it would not be
dropped in favor of the largest positive row. The paper's nondetections lack
limits needed for quantitative contradiction strength.

This case completes the requested worked point arithmetic for a measured
condition response and a parameter-based substrate response. It leaves native
system mapping, isolation and score uncertainty explicit. It does not make any
of the ten general sheets complete or settle a final score transformation.

## Inspected source trace and checks

| Component | Exact inspected location |
| --- | --- |
| Activity constructs, fluorescence, protein normalization | Methods: “Enzyme activity assays”; retained primary text lines 310–313 |
| Apoenzyme, metal panel, reconstitution and ICP-MS | Methods: “Apoenzyme preparation”, “Metal activation studies”, “Reconstitution of B. subtilis GCYH-IB with Mn2+ or Zn2+”; primary text lines 314–320 |
| Relative activity and nondetection | [Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC2772490/#t2), corresponding Results; primary text lines 346–391 |
| Curve form, replication and SD caption | [Fig. 3](https://pmc.ncbi.nlm.nih.gov/articles/PMC2772490/#f3), image retained as `primary_figure3.jpg`, caption and adjacent Results |
| Kinetic values, metal-content qualification | Results immediately after Fig. 3; primary text lines 394–395 |
| Source/target sequence and structure distinctions | Results: “Crystal structure of GCYH-IB reveals a T-fold”, structural search paragraph, and “Comparison of GCYH-IA and GCYH-IB structures” |
| A106 boundary | Methods strain construction; Results first subsection; Fig. 2, inspected but excluded from A105 operands |

`fole2_numerical_cells_001.json` retains the measured/derived distinction.
`check_fole2_arithmetic_001.py` checks unit conversions, kinetic mapping,
derivatives, shared-denominator cancellation, and missing/nondetection
semantics. It is a research arithmetic checker, not a production reader/scorer.
No scientific run, new assay, model fit, sequence alignment or production test
suite was performed.
