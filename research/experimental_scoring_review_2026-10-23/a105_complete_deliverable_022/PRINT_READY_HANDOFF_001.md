# A105 printable numerical handoff

The current A105 research sheet is numerically defined through a candidate
contribution. Its complete **synthetic** example gives **0.616595042762**.
The figures below are numerical components, not category grades or function
probabilities. The recommended conventions remain proposals; the pooling
question is unanswered.

| Step | Populated calculation | Result |
|---|---|---:|
| Preparation signal | 1.20−.20 | 1.00 µM/min |
| Isolated molecular signal | 1.00−.15 contaminating activity | .85 µM/min |
| Experimental comparability | Measured same-endpoint condition response 2.00/1.60 | 1.25 |
| Corrected activity | .85/(recovery 1×protein 1 µM×response 1.25) | **.68 min⁻¹** |
| Total propagated uncertainty | .0256+.0144+.001156+.004624+.00296225+.0625 | **V=.11124225 min⁻²** |
| Source contribution | S=.68²/(2V); B=tanh(S/2) | **S=2.078347030917; B=.777561486079** |
| Five measured correspondence components | Sequence 480/620; structure min(.90,.85); sites 8/10; placement 85/100; system exp[−.5(49/100+.25)] | .774193548387, .85, .80, .85, .690734330637 |
| Explicit correspondence mean | Sum of the five components/5 | **R=.792985575805** |
| Target activity contribution | B×R | **.616595042762** |

Comparability excludes the intentionally changed variable. Isolation identifies
which molecule supplied the observed signal. Their measured corrections and
uncertainties enter once; there is no extra generic reliability multiplier.

The separately populated calibrated specificity branch uses

\[
z=y-c-d+X\beta=(.8,.6,.9),\quad
C=\begin{pmatrix}.230&.115&.060\\.115&.300&.085\\.060&.085&.400\end{pmatrix}.
\]

Here c is the measured condition correction, d is the separate attribution
correction, and Xβ maps to the target. The full primitive covariance retains
shared source, target, family and calibration uncertainty. The common-target
fit gives θ̂=.773913043478, V=.155481634183, S=1.926084074217 and
**B=.745630704507**. Its correspondence is already in that mapping; R is not
applied again.

The candidate in this example expressly requires **activity AND specificity**.
The proposed required/sufficient reduction gives

\[
c_{A105}=\max\{0,\min(.616595042762,.745630704507)\}
=\mathbf{.616595042762}.
\]

Required claims use the minimum; genuinely sufficient alternative ways for the
same assertion use the maximum. Competing candidates keep separate scores.
This conventional combination is not a joint likelihood. One persistent
candidate retains its identity across evidence updates.

For several received findings about the **same statement**, the current
recommendation is

\[
D_{statement}=\max(0,\max D_i)-\max(0,\max[-D_i]).
\]

Use current fitted source results, not their historical maxima. A completed
calibrated joint block supplies one B row; distinct remaining uncalibrated
relationships supply D=RB rows. The same conventional formula combines them
without treating them as independent likelihoods. Constituent observations do
not reappear outside their joint block. Duplicate representations collapse;
competing fits of the same observations remain allowed alternatives or conflicts.

| Synthetic current evidence for one statement | Recommended strongest-side balance | Explicit unit-allocation accumulation alternative |
|---|---:|---:|
| Positive .771222064061 plus weaker positive .304637662382 | .771222064061 | .871181484985 |
| Positive .771222064061 plus contrary −.304637662382 | **.466584401678** | **.609869037957** |
| Ten distinct equal positive rows plus that contrary row | .466584401678 | .999999995150 |

The alternative is `tanh(sum atanh(Di))`, with all allocations explicitly 1.
It accumulates agreement; the recommendation does not. The user has not chosen
between them. A calibrated block .745630704507 plus a distinct uncalibrated
contrary −.304637662382 gives a conventional **.440993042125**, with no combined
profile likelihood claimed.

Real published examples populate native cells with their actual limits:

| Source | Filled numerical cells | Limit retained |
|---|---|---|
| CsiD, DOI 10.1038/s41467-018-07563-6 | Graph-derived oxygen rates ≈.16062−.10484=.05578 µmol/min | Preparation oxygen consumption is not isolated product formation |
| BtsT, DOI 10.1128/JB.00599-17 | Reported Km=16.5 µM; declared 10-to-40 µM same-system response [10/26.5]/[40/56.5]=.533018867925 | Scenario concentrations and model scope remain explicit; no transfer to a different preparation |
| IscR, DOI 10.1038/nsmb.2568 | Reported IC50 32 and >510 nM → point/limit selectivity >15.9375 | Not Kd, a confidence bound or an invented zero |
| TriA/AtzA, DOI 10.1128/JB.183.8.2405-2410.2001 | 466/475 identity=.981052631579; 17 versus .01 activity limit → preference >1700 | Global similarity and actual substrate selectivity remain separate |

Missing evolution in the complete synthetic example gives a full candidate
point of **unknown**, with defined bounds **[.484409590129,.639921887345]**.
Its conditional observed-family number is labeled separately. Unknown native
operands do not become zero, a midpoint, a new experiment quota or an unspecified
future calculation. Nondetection uses its actual censoring model; repeated and
shared observations are fitted once with their actual covariance.

All seven research-sheet criteria are now supplied **once this handoff is
printed for judgment**: numerical cells/uncertainty; explicit combinations;
contrasting published cases with checked arithmetic; shared-evidence and
nondetection handling; source trace; exact fields for targeted unimplemented
readers; and visible proposals/choices incorporating existing feedback.
**No essential undefined numerical operation remains in the current proposal.**
Policy adoption and production reader implementation are separate. The parent
retains completion authority; this worker has not marked A105 or the goal complete.

The full deliverable contains every intermediate activity/calibrated value,
measurement-model equation, exact reader-field crosswalk, source/inspection
reference and criterion assessment. **29 bounded arithmetic checks passed**.
This consolidation inspected cross-case mathematics, not new primary papers;
the earlier source conversions retain their inspection records. No production
tests, target annotation or native/HPC jobs ran.
