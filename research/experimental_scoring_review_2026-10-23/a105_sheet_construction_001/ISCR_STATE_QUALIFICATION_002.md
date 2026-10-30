# A105: numerical binding cells retain the state during measurement

2026-10-23. Additive source qualification and proposed numerical conversion.
No earlier record, score, prompt, reader or production function is changed.
A105 remains unfinished.

## Actual comparison and source limits

Banerjee et al. (2025), DOI 10.1111/mmi.70021, compare binding by purified
E. coli IscR under different treatment/readout conditions. Reported apparent
Kd values are 22 nM for untreated anaerobic protein, >1000 nM with PMS under
anaerobic conditions, and 26 nM after air exposure followed by anaerobic assay.
The paper interprets recovery after return to anaerobiosis as likely
auto-reduction, qualifying the earlier 2012 oxidation interpretation.

Source: https://doi.org/10.1111/mmi.70021

The intended condition change belongs in the measured contrast. A mechanistic
claim attributing that contrast specifically to cluster redox state is narrower
than a statement about the treated preparation's binding. Dynamic redox state,
mixed cofactor occupancy, effective dose and optical interference have different
numerical roles; a preparation label does not measure them.

The parent inspected the completed paper-specific packet, retained primary
Results 2.2–2.3, Discussion 3.1 and Methods 4.3–4.7, and Figure 4 as an image.
The supplement and raw replicate curves were not read/refitted. Direct web
access returned recaptcha/errors; the primary text retained by the completed
worker supplied the inspected sections. Nearby transcriptional passages were
not converted into A105 binding scores.

## Filled numerical cells

| Cell | Calculation | Result and meaning |
| --- | --- | --- |
| Treated/control apparent-affinity ratio | Kapp_PMS / Kapp_untreated | >1000/22 = >45.45454545, using reported values |
| Log apparent-affinity contrast | ln(Kapp_PMS/Kapp_untreated) | >3.816712826, derived bound before uncertainty |
| Returned-to-anaerobic/control ratio | 26/22 | 1.181818182 |
| Corresponding log contrast | ln(26/22) | 0.167054085 |
| Variance of either fitted-parameter contrast | Requires parameter uncertainties and covariance | Unknown from the inspected values |

The printed values alone imply >45.45, while the source describes the change as
at least 50-fold. Do not silently turn the source's rounded wording into an
exact calculated bound. None of these rows is a confidence interval. The 26/22
ratio is not evidence of statistical equivalence without its uncertainty.

The numerical molecular finding remains useful when an additional causal
attribution is unresolved. This does not import genetic/phenotypic perturbation
or restoration evidence from A106. Causal conclusions and direct binding
measurements are not duplicated as separate A105 replications.

## How the cells combine in the scoring sheet

For a log-affinity comparison whose nuisance effects are actually measured:

```
d = log(Kapp_treated) - log(Kapp_control)
d_corrected = d - measured_nuisance_condition_effect - measured_unintended_effect
variance(d_corrected) = gradient(d_corrected)^T * joint_covariance
                       * gradient(d_corrected)
```

The deliberately changed treatment is not subtracted as a nuisance. The
condition-effect operand concerns other differences, such as an independently
measured salt-response effect when comparing protocols. The unintended-effect
operand concerns distinct contributors such as an optical artifact or a
quantified inactive fraction. Unknown effects are not zero-valued corrections.

This source's parameter variance and censoring likelihood are unavailable in
the inspected material. Its actual contrasts and bounds can populate the sheet;
an unconditional standardized contrast or profile score cannot be fabricated.
The prior IC50 specificity cells from the 2013 paper remain their own assay
measurements. They are not pooled with these Kapp values as one repeated endpoint.

## Mixed-state dose is a model input, not a relevance grade

The source reports average cluster occupancy of 50–70%. That is a cofactor
measurement, not a measurement of active DNA-binding fraction. A state-specific
binding calculation would need the relevant mixture and binding model.

For illustration ONLY, suppose one component is active, the other is inert,
its active fraction f is known, and a one-component dose model is appropriate:

```
active_dose = f * total_dose
K_active = f * Kapp_total_dose
log(K_active_treated/K_active_control)
  = log(Kapp_treated/Kapp_control) + log(f_treated) - log(f_control)
```

With Kapp=22 and f in [0.5,0.7], this conditional model gives 11–15.4 nM.
That is NOT a corrected state-specific Kd reported by the paper. Dimerization,
mixed-state binding and state changes during readout can invalidate the model.
If f is truly common to both measurements, it cancels from the ratio. If its
values differ, their covariance belongs in the uncertainty calculation. It must
not also multiply an overall evidence score as a second cofactor penalty.

The exact additional numerical reader inputs are state fractions at the
measurement time, their uncertainty/covariance, total-dose measurements,
state-specific response-model operands and optical/background controls where
applicable. These are targeted missing operands for a broader inference, not a
mandatory checklist every binding experiment must satisfy.

## What this changes and what it preserves

The 2025 study qualifies the earlier 2012 interpretation that oxidation leaves
type-1 binding unchanged: the actual state during the earlier anaerobic assay
may have changed. That earlier result remains a historical measurement. It
cannot be counted as proof of equal binding by continuously oxidized and
reduced protein, and neither a blanket low-quality label nor averaging the two
studies solves the state mismatch.

No parent-derived numerical cell from ISCR_NUMERICAL_CELLS_001.md is overwritten.
Those are the 2013 competition observations; this new record makes the state
and endpoint requirements explicit before any cross-study inference.

## Verification and required reset

The arithmetic was executed using the repository virtualenv and written
exclusively to `iscr_state_arithmetic_002.json`. It checks the reported-value
ratios/logs and conditional dose range. It does not validate a likelihood or a
state-specific binding model.

Before this conversion, the parent reread the complete authority set in six
nontruncated calls: root AGENTS/GOAL; EPISODE_STRUCTURE/TASK_AND_STEERING;
TIME_AWARE_ESTIMATION/TOOL_KNOWLEDGE; the task/evidence amendments and both
verbatim direction/recovery records; the evidence-axis-library instructions
and earlier numeric example; then local AGENTS, the A105/A106 assignment and
the active goal last. The goal specifies ten completed numerical sheets;
this qualification and its arithmetic do not count as a completed sheet.
