# One source experiment: YeaG deletion/restoration,120-hour CFU survival

This is one experimental comparison from Figueira et al. (2015), *Scientific
Reports*5:17524, DOI10.1038/srep17524, PMC4664914, Figure6B. The two retained
interpretation scenarios use the SAME original image, arms, endpoint, time,
reported n and controls. They are not independent assays, replications or two
papers. The source below is retained locally; no new acquisition or model call
was used.

The experimental definitions come before the component conversion:

| Role | Studied arrangement | Selected endpoint |
|---|---|---|
| W | Wild-type E.coli carrying empty pBAD18; native chromosomal YeaG | CFU/mL after120h nitrogen starvation |
| K | ΔyeaG carrying empty pBAD18 | Same endpoint and time |
| R | ΔyeaG carrying pBAD18-yeaG | Same endpoint and time |

The restored copy replaces a missing native gene; it does not coexist with an
intact endogenous YeaG copy. The supplement describes6xHis-YeaG under an
arabinose-inducible promoter. Methods describe37°C/180rpm Gutnick minimal
medium,0.4%glucose,3mM ammonium for the relevant growth phases, ampicillin where
appropriate and0.1%arabinose for complementation. These are source methods,
not independently verified exposure measurements at120h.

The Figure6B caption calls its error bars **SD,n=3**. Figure6A instead reports
SEM and is not the selected dataset. General methods describe independent
experiments. The retained count is therefore3 independent experiments, coded
`other` rather than inventing a culture, plate, cell or technical-reading unit.
There are no supplied raw CFU replicates or cross-arm pairing/covariance data.

The exact primary image was visually inspected at1395×1279 pixels and then
read by the executable `read_summary_figure` through the selected
`literature.perturbation.populate` operation. Image SHA256:
`098ad8ff78351821e0fcc25dd67294c55b881e2a86451f9f03022cb01c884fdc`.
The retained recipe explicitly chooses native-coordinate black bar-edge and
upper-cap ROIs. A logarithmic display calibration maps y=807.5 to10^6CFU/mL
and y=551.5 to10^9CFU/mL. Its formula is
`CFU(y)=10^[6+(y−807.5)(9−6)/(551.5−807.5)]`.
Calibration, legend/arm assignment, threshold and ROIs are explicit investigator
interpretations. This is not a universal graph classifier or autonomous
arbitrary-paper extraction. Mean/error values are computed from original image
bytes; none is supplied as a manual numerical operand.

| Role | Read bar-edge y | Read upper-cap y | Bar ordinate,CFU/mL | Upper-cap ordinate,CFU/mL |
|---|---:|---:|---:|---:|
| W |671.5|660.0|39,241,897.6|53,519,940.9|
| K |730.5|713.0|7,986,265.6|12,806,247.0|
| R |669.5|658.0|41,417,845.1|56,487,600.2|

Pixel tolerance is±1native y pixel after the reader's half-pixel convention
and caller edge tolerance. For example W's ordinate enclosure is
[38,197,175.5,40,315,193.6]CFU/mL. These bounds are conditional digitization
bounds with the nominated calibration fixed; they are not confidence intervals
and do not cover all possible axis/calibration/figure-reading errors. No lower
cap is nominated; the selected upper cap is retained explicitly.

The paired extraction fields populate numerical A106 components:

| Extracted operands | Component and exact denominator | Populated value | Scoring meaning |
|---|---|---:|---|
| W,K,endpoint/time/arm meanings | D=W−K |31,255,632.0CFU/mL|Magnitude of the displayed deletion-associated endpoint change|
| Same W,K | θ=(W−K)/(W+K) |0.661800711|Symmetric endpoint contrast; not a functional probability|
| R,K | R−K |33,431,579.5CFU/mL|Magnitude of the restoration-associated endpoint change|
| Same W,K,R | (R−K)/(W−K) |1.069617775|Restoration relative to the deletion contrast; modest overshoot is retained|
| Same W,K,R | r=clip(1−abs(R−W)/abs(W−K),0,1) |0.930382225|Existing proposed restoration-agreement convention|
| Native/restored YeaG amounts A_reference,A_restored | C=min(A_reference,A_restored)/max(A_reference,A_restored) |unknown|Quantitative comparability outside the intended deletion/restoration|
| Supplied alternative-effect bounds B_pert,B_rest | I_pert=clip(1−B_pert/abs(W−K),0,1); I_rest=clip(1−B_rest/abs(R−K),0,1); I=min(I_pert,I_rest) |unknown|Isolation of endpoint changes from alternative contributors|

The existing proposed combination is
`source_index=orientation × θ × r × C × I`, with orientation=+1 for the
directional survival contribution under these conditions. C and I have no
measurements here, so the source index and its full-index bounds remain null.
No missing factor becomes1, no universal quality category is assigned, and no
A101 correspondence or W05 annotation credit is calculated. The partial
numerical components remain usable.

There are two explicitly qualified statistical readings:

1. **Primary unresolved scale.** Keep the bar ordinates, upper-cap ordinates,
   reported SD label and n=3. The article does not explicitly resolve the scale
   on which its mean and SD were computed. Log DISPLAY does not resolve that
   statistical question. Mean/SD summary-scale meanings remain unknown, the
   numerical SD magnitude and SE stay null, and the descriptive point
   components above remain populated. This is a useful partial return.
2. **Conditional arithmetic raw-CFU mean/SD.** If bar values are arithmetic
   means and SDs on the raw CFU scale, SD=upper_cap−bar and SE=SD/sqrt(3).
   This is a declared conditional premise, not an additional source claim.

| Role | Conditional raw-scale SD,CFU/mL | Conditional SE,CFU/mL |
|---|---:|---:|
| W |14,278,043.3|8,243,432.1|
| K |4,819,981.4|2,782,817.6|
| R |15,069,755.1|8,700,527.2|

For the conditional raw-scale reading, V_W=SD_W²/3 and V_K=SD_K²/3.
Without cross-arm covariance, Var(W−K) remains unknown; only the conditional
Cauchy enclosure `[(sqrt(V_W)−sqrt(V_K))²,(sqrt(V_W)+sqrt(V_K))²]` is available:
approximately[2.9818311463×10^13,1.2157818263×10^14](CFU/mL)².
That enclosure conditions on the retained central marginal variance estimates;
it is not a confidence interval, probability coverage, total uncertainty or a
full propagation of digitization bounds. Shared-contrast covariance remains
null. The same K and W/R measurements recur in the contrasts and cannot earn
independent experimental credit repeatedly. Nonlinear sampling uncertainty for
θ/r and whole-index uncertainty are not established by this example.

The source case exposed one necessary paired extraction/interface refinement:
each newly qualified measurement supplies a closed seven-field
`interpretation_basis` object. Its codes distinguish `source_reported`,
`source_supported_inference`, `conditional_assumption` and `unresolved`.
Actual requested typed rows carry the exact contributing-role map as
`statistical_interpretation_basis`, including W/K premises on D and θ and W/K/R
premises on restoration components. The conditional raw-scale assumption thus
survives the real parent receipt. Existing saved v2 rows with no basis are
unchanged; absence is not silently backfilled as reported or unresolved. The
older55-field closed form rejects new rows that contain the extra metadata;
removing supplied metadata fails exact saved-row validation. No number or
eligibility rule changes because of these basis codes.

Experimental comparability and effect isolation remain different questions.
The supplement mixes MG1655 and BW25113/JW1772-1 nomenclature in its strain
descriptions; clean background equivalence is not established by relabeling
them. Plasmid restoration also changes promoter, copy context, tag and possible
protein amount relative to native WT. These differences matter to C and can
confound attribution; they are not reasons to discard CFU measurements or
invent a numerical penalty. A matched-background/chromosomal restoration and
native-versus-restored YeaG abundance measurements under the actual120h
conditions would address specific comparability gaps. Appropriate additional
controls/measurements would be needed to quantify alternative-effect bounds.

The phenotype supports a contribution of YeaG to survival during sustained
nitrogen starvation in the studied system. These CFU contrasts do not isolate
a particular catalytic reaction or substrate specificity. No target protein's
sequence, structural correspondence or functional transfer is established.

Retained source corrections still apply: Figure3 recovery growth is not
Figure6B survival; K116A has no selected Figure6B survival bar; Figure3 variant
abundance cannot supply native-WT/restored-YeaG amounts at120h. The source's
K426A100%prose versus1.12image disagreement remains an explicit discrepancy,
not an averaged or repaired number. No such value enters this example.

This is primary-source numerical extraction with a manually retained recipe,
executed through ordinary LiteratureEpisodes using a declared scripted
provider and test continuation controller. It is engineering integration
evidence, not actual model-backed scientific decision behavior. Direct
paper-span selection and automatic retained-recipe construction remain
separate unfinished interface work.
