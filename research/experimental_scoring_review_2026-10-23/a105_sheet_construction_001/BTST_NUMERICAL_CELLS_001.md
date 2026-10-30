# A105 numerical cells: measured condition response in BtsT

2026-10-23. Additive research proposal, not an adopted scoring policy. A105 and
the other nine sheets remain unfinished. This file extends the numerical
proposal in EXPERIMENTAL_RELIABILITY_001.md without replacing it or the user's
permanent instructions. The pending question about an additional mismatch
penalty remains unanswered; no approval is inferred.

## Numerical result and its meaning

The inspected BtsT study reports a whole-cell Michaelis constant of
16.5 ± 6.4 micromolar. The definition of that fitted uncertainty was not
established. It separately reports a purified-vesicle initial transport rate of
27.7 nanomoles per milligram of protein per minute. These belong to different
assay systems; the whole-cell concentration-response correction below is not
applied to the vesicle measurement.

Source: Kristoficova et al., 2018, DOI 10.1128/JB.00599-17,
https://pmc.ncbi.nlm.nih.gov/articles/PMC5738728/.

For the fitted Michaelis-Menten response, the fraction of maximal rate at
substrate concentration S is

```
fractional_rate(S) = S / (Km + S)
```

This is a rate fraction, not binding-site occupancy: Km is not automatically a
dissociation constant. For a comparison that changes only substrate
concentration within this same fitted assay system:

```
condition_correction = fractional_rate(S_reference) / fractional_rate(S_assay)
                    = S_reference * (Km + S_assay)
                      / [S_assay * (Km + S_reference)]

rate_at_reference = rate_at_assay * condition_correction
```

The following reference concentration is an illustrative choice for comparing
measurements, not a physiological target imposed on the investigation.

| Numerical cell | Value | Unit / calculation | Use in the sheet |
| --- | ---: | --- | --- |
| Fitted Km | 16.5 | micromolar | Native response parameter |
| Reported plus/minus amount | 6.4 | micromolar; uncertainty definition unknown | Retained as reported; not silently converted to SE |
| Assay substrate concentration in this comparison | 40 | micromolar | Declared comparison input |
| Reference substrate concentration | 10 | micromolar | Declared comparison input |
| Fractional rate at 40 | 0.707964602 | 40/(16.5+40) | Intermediate from the same fitted curve |
| Fractional rate at 10 | 0.377358491 | 10/(16.5+10) | Intermediate from the same fitted curve |
| Condition correction | 0.533018868 | 0.377358491/0.707964602 | Multiplies a compatible measured rate once |
| Response increase, 10 to 40 | 1.876106195 | Inverse of correction | Same information, not a second score |

The raw concentration ratio 10/40 = 0.25 would be an incorrect rate correction.
The measured response curve supplies the relationship. A change that is the
intended experimental variable is preserved as a contrast; it is not removed
as a nuisance difference.

## Shared uncertainty: two derived cells are not two measurements

Both fractional rates use the SAME Km. Their uncertainty is correlated. Let
`c(K) = 0.25 * (K + 40)/(K + 10)`; then

```
dc/dK = -7.5 / (K + 10)^2
```

At Km = 16.5, this derivative is -0.0106799573 per micromolar. The following
uncertainty calculation is explicitly CONDITIONAL: it illustrates the result
if 6.4 were a standard uncertainty. The source extraction has not established
that premise, so the resulting value is not a published error bar or a filled
unconditional uncertainty cell.

```
variance(c) = (dc/dK)^2 * variance(K)
            = 0.004671958528
standard_uncertainty(c) = 0.06835172659
```

Expanding through the two fractional rates gives the same result only if their
shared-Km covariance is retained:

| Conditional arithmetic component | Numerical value |
| --- | ---: |
| Sum of marginal variance terms, incorrectly assuming independence | 0.020216602765 |
| Shared-parameter covariance term | -0.015544644237 |
| Correct combined variance | 0.004671958528 |
| Standard uncertainty if independence were incorrectly assumed | 0.142185100361 |
| Standard uncertainty retaining the shared parameter | 0.068351726593 |

Without assuming an uncertainty definition, a sensitivity calculation can still
be made: using K = 16.5 - 6.4 gives c = 0.623134328; using K = 16.5 + 6.4 gives
c = 0.477963526. These are evaluations at specified inputs, not a confidence
interval with claimed coverage.

If a compatible measured rate J and its joint uncertainty with K are available,
the sheet combines the numerical cells as follows:

```
J_reference = c(K) * J
variance(J_reference) = c(K)^2 * variance(J)
                      + [J * dc/dK]^2 * variance(K)
                      + 2 * c(K) * J * dc/dK * covariance(J, K)
```

The covariance is especially relevant if J and Km came from the same fit.
Neither zero covariance nor a precise Km is inferred from an omitted report.
This formula adjusts a rate and its precision. It is not yet a whole A105
annotation contribution or a target-correspondence score.

## Isolation and normalization remain separate numerical questions

For a measured transport rate U, matched background B and independently
quantified contaminating transport C, the attributable rate is `U - B - C`.
The activity-attribution fraction, where its denominator is meaningful, is
`(U - B - C)/(U - B)`. It must not be replaced by protein mass purity or by a
statement that the preparation contains the protein. Shared uncertainties enter
the covariance calculation just as for the condition correction.

The paper's purified-vesicle rate uses total measured protein as its
denominator. It does not establish active transporter amount or vesicle
orientation. Keep the reported specific rate in its stated unit; do not silently
convert it to turnover per active transporter. Missing normalization details
limit that conversion, not the existence of the observed measurement.

The paper's counterflow setup has 10 millimolar internal unlabelled pyruvate,
200-fold dilution and 4.7 micromolar added labelled pyruvate. The derived cold
carryover is 50 micromolar and the external total is 54.7 micromolar. Thus the
labelled fraction is 0.085923218 and total/labelled is 11.638297872. A count-to-
total conversion uses this ratio only when it has not already been included in
specific activity. It is a measurement conversion, not a second evidence score.
The accumulated endpoint and an initial rate remain different quantities.

## Exact reader outputs needed for these cells

The reader populates the measured quantity and its denominator, substrate
concentrations, fitted Km, parameter covariance when available, uncertainty
definition, actual replication unit, matched background/contaminating activity,
and any count-to-total normalization already applied. The deterministic
calculation evaluates the equations above. It does not ask a reader to grade
the assay as broadly reliable, comparable or relevant.

Raw native values and computable conditional results are retained even when a
different requested quantity cannot be calculated. Unknown quantities are not
filled with zero, and they do not create a blanket requirement that every assay
report every possible calibration. For this source, the known point correction
does not imply known error-bar coverage or an experimentally validated bridge
between whole cells and purified vesicles.

## Source-to-component trace and inspection limits

| Inspected material | Component informed | Limit |
| --- | --- | --- |
| Primary Results/Methods and the completed one-paper worker packet | Native concentration-response parameter and assay definitions | Parent did not reread the entire main article text |
| Primary Figure 5 image | Initial-rate unit and distinction from accumulated endpoint | Not digitized or refitted; a graph's points were not invented |
| Worker packet's additive arithmetic correction | Correct concentration-response ratio | Earlier erroneous 0.532806 is not used; correct value is 0.533018868 |
| Supplement index attempt | Access accounting | Recaptcha prevented parent supplement inspection |

After this paper packet, Results/Methods and Figure 5, the parent reread the
complete authority set before deriving these cells: root AGENTS.md and GOAL.md;
EPISODE_STRUCTURE.md; TIME_AWARE_ESTIMATION.md; TOOL_KNOWLEDGE.md;
TASK_AND_STEERING.md and its amendment; EVIDENCE_AXIS_REVIEW amendment;
VERBATIM_DIRECTION.md and VERBATIM_RECOVERY_002.md; the
EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS amendment; the earlier complete numerical
scoring example; local AGENTS.md and A105_REVIEW_ASSIGNMENTS; and finally the
active goal attachment. No new paper was interpreted between that reset and
this conversion.

These equations are our proposed conversion into the user's scoring template,
not a scoring system asserted by the BtsT authors. Remaining A105 work includes
the contribution of measured contrasts to inferred molecular functions,
source-to-target relevance, contrasting complete examples and user feedback.
