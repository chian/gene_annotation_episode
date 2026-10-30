# A105 numerical cells: binding magnitude, specificity and shared controls

2026-10-23. Additive research proposal for the user's judgment. This is a
numerical conversion of one inspected binding experiment, not an adopted
annotation-score policy. A105 remains unfinished. It does not change permanent
records, production scoring, readers, episode behavior or library publication.

## What the numbers measure

Rajagopalan et al. measured competition for DNA binding by purified apo-IscR.
For the wild-type protein, Table 3 reports an IC50 of 32 ± 2 nM for hya DNA,
versus >510 nM for the 7C-to-G competitor, >740 nM for 8C-to-G and >1000 nM
for shuffled DNA and two further competitors. The errors are described as
standard deviations from a fit to averaged independent titrations.

These are assay-specific competition midpoints, not equilibrium dissociation
constants or cellular transcription rates. Each comparison below keeps the
same protein preparation/state and changes the competing DNA. The causal effect
of a protein mutation is not being scored as A105 evidence here. Genetic
perturbation/restoration conclusions remain outside this sheet.

Source: Rajagopalan et al., 2013, DOI 10.1038/nsmb.2568,
https://pmc.ncbi.nlm.nih.gov/articles/PMC3676455/.

## Exact numerical specificity cells

For the defined comparison, write

```
selectivity_ratio = IC50_other_DNA / IC50_reference_DNA
log_selectivity = ln(IC50_other_DNA) - ln(IC50_reference_DNA)
```

A positive log selectivity means the reference DNA competes more effectively
under these assay conditions. It is a measured specificity effect, not a
probability that an annotation is correct. Its magnitude remains visible even
when a later calculation evaluates the precision with which its sign is known.

| Other DNA | Native IC50 report | Derived ratio using the reference point estimate | Derived natural-log ratio |
| --- | ---: | ---: | ---: |
| Shuffled | >1000 nM | >31.25 | >3.442019376 |
| hya 7C-to-G | >510 nM | >15.9375 | >2.768674823 |
| hya 8C-to-G | >740 nM | >23.125 | >3.140914283 |
| hya 8C-to-A | >1000 nM | >31.25 | >3.442019376 |
| hya 8C-to-T | >1000 nM | >31.25 | >3.442019376 |

These inequalities are calculated from the published censoring and the
reference point estimate. They are not confidence bounds for the true ratio:
reference uncertainty and the original titration likelihood have not been
incorporated. The five rows also do not become five independent tests of the
reference binding measurement.

## Combining comparability, isolation and uncertainty

For a fully measured log contrast d, a proposed numerical common-condition
contrast is

```
d_common = d - measured_condition_effect - measured_unintended_effect
```

The first correction measures the change due to nuisance conditions outside the
intended ligand comparison. The second measures a contribution from unintended
molecules or signals. They are different operands, even if both can be expressed
in log-contrast units. A correction already included in the original fit is not
subtracted a second time. A mixed binding preparation may require a nonlinear
mixture model; a cluster-occupancy percentage cannot simply multiply a Kd.

For numerical input vector x and its covariance matrix:

```
variance(d_common) = gradient(d_common)^T * covariance(x) * gradient(d_common)
```

Only a separately estimated residual between-preparation variance is added on
top; the same preparation variance must not enter both through a fitted error
bar and as an extra replication term. Unknown condition effects, attribution or
covariance remain unknown. That limits the corresponding corrected result,
while preserving the native measured contrast and its scope.

For two fully observed midpoints C_other and C_reference, the first-order
variance before additional corrections is

```
variance(d) = variance(C_other)/C_other^2
            + variance(C_reference)/C_reference^2
            - 2*covariance(C_other, C_reference)/(C_other*C_reference)
```

The same reference appears in every ligand contrast. If the other fitted
midpoints are independent of one another and the reference, then two different
contrasts still share covariance

```
covariance(d_i, d_j) = variance(log(C_reference))
```

That is a conditional example, not an assumption inferred from missing source
covariance. If the reported reference spread of 2 nM were an applicable standard
uncertainty, its first-order log-variance contribution would be (2/32)^2 =
0.00390625. It must not be counted as independent five times.

## A finite measured comparison, with its uncertainty assumptions exposed

For the separately assayed apo-E43A protein, the same table gives 17 ± 3 nM for
the 7C-to-G competitor and 11 ± 1 nM for hya. Within THAT protein's assay:

```
selectivity_ratio = 17/11 = 1.545454545
d = ln(17/11) = 0.4353180713
```

This describes the variant's measured binding specificity. It is not a second
independent measurement of the wild-type protein and is not, by itself, a score
for the causal effect of substituting residue 43.

Conditionally treating the two quoted spreads as standard uncertainties gives
the following calculation in terms of their still-unknown correlation rho:

```
variance(d) = (3/17)^2 + (1/11)^2 - 2*rho*(3/17)*(1/11)
            = 0.03940633132 - 0.03208556150*rho
```

At an explicitly assumed rho=0, standard uncertainty is 0.1985102801. Allowing
rho to range from -1 to 1 gives variance from 0.00732076982 to 0.07149189282.
This shows exactly which missing relationship changes the numerical precision.
It does not assign an independence assumption or error-bar interpretation to
the paper. Native point contrasts can be populated while that uncertainty
calculation remains conditional.

## Contribution to annotation scoring: what is and is not established

These cells supply the specificity effect and, when available, its actual joint
likelihood or uncertainty to the proposed A105 contribution calculation. They
do not independently establish regulatory activity, physiological importance,
or correspondence to a different annotation target. Those claims need their
own measured relationship; strong evidence for a small affinity preference
does not make it a large biological effect.

A reported IC50 lower limit is retained as a limit. A likelihood for censored
data requires the actual observation rule and response/noise model. The string
">510" alone does not justify inventing a standard deviation or a Gaussian
survival probability. Replacing it with an exact 510 would discard the limit's
meaning. When raw titrations are available, their joint response model supplies
this calculation directly; an arbitrary categorical fallback is unnecessary.

The final common contribution is still being developed separately. No complete
A105 score or synthetic annotation-confidence value is assigned to this paper.

## Reader fields and source trace

The targeted reader needs the actual protein/state, competing ligand identity,
native fitted midpoint and unit, bound direction, fit/observation model,
uncertainty definition, replication unit, shared control relationships and
measured correction inputs. Literature and a dataset fit can populate the same
numerical cells. Source identifiers and prose explanations support inspection;
they are not scoring components and do not become evidence multiplicities.

The parent inspected the complete one-paper worker packet, primary binding
Results and Methods, Table 2 as text and Table 3 as an image. The supplement
and raw titrations were not inspected or refitted. The protein-preparation and
state distinctions in the source are retained; the crystallography construct is
not substituted for the binding preparation.

After that source read, the complete post-paper authority reset was performed
in six nontruncated reads: root AGENTS/GOAL; EPISODE_STRUCTURE/TASK_AND_STEERING;
TIME_AWARE_ESTIMATION/TOOL_KNOWLEDGE; both task/evidence amendments and both
verbatim decision records; evidence-axis-library instructions and the earlier
numerical example; then local AGENTS, the A105/A106 assignment brief and active
goal last. Current user direction remains that the goal and completion criteria
define the outcome; instructions and paper reviews are means, not completion.
