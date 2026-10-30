# A105 kinetic-parameter comparison: parent case038 conversion

This is a case-grounded paired sheet/input proposal after the parent's complete
43-chunk post-packet reset. It is not a new axis, a raw-rate redefinition,
an adopted global scoring policy or a completed grader. Parent checked the
retained packet's16 manifest entries,18 exact spans and arithmetic; all17 case
files stayed unchanged. Parent reviewed the packet, not fresh figure pixels,
missing rendered equations or raw kinetic data. The source owner's coverage
and limitations remain in a105_specificity_case_038/PROVENANCE.md.

## Experimental meaning and numerical role

The studied reference construct is N-terminal His6-tagged Rv2131c/CysQ from
M. tuberculosis H37Rv, expressed in E. coli and purified. It is separately
assayed on PAP, myo-inositol1-phosphate (IMP) and fructose1,6-bisphosphate (FBP).
This is not a protein replacement/coexistence comparison or a mixed-substrate
competition assay. Preparation identity across all physical repeats is unknown.

Table1 reports apparent efficiencies42±8,.0027±.0015,.025±.001 in
uM^-1min^-1. The reported experiment count is3; the error statistic and number
of independent protein preparations remain unknown. Reported efficiency means
stay distinct from60*mean(kcat)/mean(Km), which gives40,.002616033755 and
.025441696113. Different summary operations do not create additional evidence.

The measured distinctions populate source specificity magnitude components:

| Component | PAP/IMP | PAP/FBP |
| --- | ---: | ---: |
| Efficiency difference,uM^-1min^-1 | 41.9973 | 41.975 |
| Efficiency ratio | 15555.555555555555 | 1680 |
| Log efficiency contrast e | 9.652173124255222 | 7.426549072397305 |
| Conditional profile numerator e*abs(e)/2 | 46.58222301029741 | 27.576815562362633 |
| Supported variance V,profile S,index B | unknown | unknown |

These describe comparison across the actual reported protocols. PAP usespH8.5,
.5mM MgCl2 and an AMP-assigned ESI-MS product readout; the alternatives usepH9,
10mM MgCl2 and phosphate colorimetry. Enzyme amounts,durations and substrate
ranges also differ. Numerical differences between those settings are descriptive
facts, not invented comparability penalties. There is no measured response map
to one common condition. Alternative activities are positive, not nondetections.

The supported narrow inference is PAP phosphatase activity and much greater
reported apparent efficiency for PAP in these protocols. Exclusive substrate
activity, identical-condition preference, exact phosphate-site/product-isomer
resolution and the dominant physiological reaction are separate assertions.
Preparation identity controls do not establish measured zero contaminating
catalysis. The paper's separate cellular complementation is a complementary
endpoint, not an additional kinetic replicate to average into these contrasts.

## Explicit compilation within the source model

For z=(ln etaP,ln etaI,ln etaF), let

    L=[[1,-1,0],[1,0,-1]], e=Lz, V=L Sigma_log_eta L-transpose.
    V_II=Sigma_PP+Sigma_II-2*Sigma_PI
    V_FF=Sigma_PP+Sigma_FF-2*Sigma_PF
    V_IF=Sigma_PP-Sigma_PF-Sigma_PI+Sigma_IF.

The same PAP numerator appears in both contrasts. Neither distinct printed
ratios nor distinct row labels establish independent observations. Original
efficiency-scale covariance would require the explicit first-order log transform
with D=diag(1/etaP,1/etaI,1/etaF),not a new normality assumption from arithmetic.

Under the existing proposed known-normal signed-effect route only,

    S_I=46.58222301029741/V_II; B_I=tanh(S_I/2)
    S_F=27.576815562362633/V_FF; B_F=tanh(S_F/2).

If the one source assertion requires both preferences, these positive observed
contrasts under an unrestricted joint known-normal effect model give

    S_both=min(S_I,S_F); B_both=tanh(S_both/2).

This is a conditional constrained joint-profile calculation,not a sum of
independently optimized evidence. Other directions/domains need their actual
constrained model. No profile is calculated here: untyped Table1 spreads,count3
and unknown fit/cross-row covariance do not supply that model. All V/S/B cells
remain null with reasons. No synthetic variance,quality multiplier,source-to-
target weight or final annotation credit is invented.

## Paired extraction and sheet requirements

| Source information to extract | Numerical contribution/relationship |
| --- | --- |
| Parameter kind Km,kcat or kcat/Km; exact value,unit,qualifier and row/substrate | Preserve fitted parameter type/dimensions; populate parameter point/limit before compatible contrasts |
| Actual molecule,construct,preparation,substrate identity and separate/mixed arrangement | Bind the functional comparison; no same-preparation or competing-substrate inference from a common paper |
| Per-row conditions,endpoint,detector,normalization and rate/fit validity | Qualify reported-protocol contrasts; populate a common-condition correction only from measured response mapping |
| Spread magnitude plus its actual statistic,count and repetition basis | Retain untyped spread; populate SE/covariance/model-based scoring only when the required meanings exist |
| Original fits/measurements,shared controls/calibration/numerator | Preserve dependence and original-identity reuse; assemble V from actual covariance without zero imputation |
| Directly reported efficiency versus quotient of reported means | Keep distinct representations/summary meanings; do not overwrite a reported estimate or count it twice |

The existing rate comparator does not accept catalytic-efficiency dimensions.
The reported-percent reader is not a kinetic-table reader. The optical and
corrected-activity input functions cannot turn eta into an unnormalized rate.
A targeted kinetic-parameter extraction/contrast variant is justified. It is
currently unimplemented; missing source uncertainty is a separate scientific
limitation. These are not interchangeable kinds of unfinished work.

Draft aspect-specific instruction,not wired TASK:

> Determine which substrate preference the reported kinetic experiments establish.
> Distinguish Km,kcat,kcat/Km and measured rates. Identify the actual molecule,
> substrate,arrangement,endpoint,per-row conditions and fit limitations. Select
> the reported parameter estimates and their actual uncertainty meanings and
> repetition basis. Distinguish reported-protocol preference from common-condition
> preference. Preserve positive alternative activities,unknown preparation/fit
> identity,shared measurements and unresolved systematic limitations.

Finite interpretation meanings proposed for later interface review include
parameter_kind,substrate_arrangement,comparison_scope and uncertainty_statistic,
with explicit unknown/conflicting forms. They describe scientific meanings,not
numeric category grades. The reader would parse operands; calculators perform
unit conversion and arithmetic. The future literature investigation selects
this component when it encounters relevant kinetic parameters. No paper router,
mandatory extraction sequence or new episode is implemented.

The one A105 sheet still needs contrasting experimental families and the full
validity,isolation,specificity,uncertainty,replication/complementarity treatment.
This source comparison does not complete that sheet or the broader goal.
