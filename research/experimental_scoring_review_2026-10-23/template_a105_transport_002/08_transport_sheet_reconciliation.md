# Proposed transport components for the common A105 numerical sheet

Research reconciliation, 2026-10-23. This is the requested transport contribution to the user's sheet, not a new evidence axis, prompt, reader implementation, or adopted scoring policy. Seven assigned main papers have been reviewed one at a time with a complete authority reread after each. Their packets remain separate in files01–07. This document combines the resulting calculation requirements; no source packet was reopened as a batch. The parent's common sheet and its user feedback remain authoritative for the final design.

## What a transport row must measure

The row's subject is the actual molecular movement and the specific functional inference it can support. Retain substrate, source/destination compartment, membrane direction, initial versus interval rate versus endpoint amount, actual protein construct, coexisting proteins, native/reconstituted membrane, intended variable, background controls, sampling times and normalization. These fields define what numerical comparison is valid; they are not themselves binary scores.

A general measurable amount model is

`n_moved(t) = {n_measured(t) − n_surface(t) − n_trapped(t) − n_other_positive(t) + n_lost_after_entry(t)}/recovery(t)`.

Only include a term when it belongs to the actual assay and has a measured value or explicit bound. Terms may overlap: an empty-vesicle blank that already captures passive leakage and trapped label must not be subtracted again through separate leakage/trapping terms. Export, chemical degradation, isotope loss and binding may require separate balances. A tracer's specific activity must refer to the actual transported pool, including dilution by unlabeled substrate.

For a verified initial linear interval, fit `β = dn_moved/dt` with slope/intercept covariance. For an endpoint, retain `n_moved(t)` or an explicitly interval-averaged change; do not silently label `n(t)/t` an initial rate. A per-molecule component is `J = β/(N_total f_active f_orientation)` only where the active and orientation factors are identifiable, not redundant with N_total, and appropriate for the chosen direction. A whole-cell per-total-protein rate can remain a useful scoped measurement; absent active fraction does not make that native rate disappear, but prevents a per-active-transporter turnover claim.

## Numerical cells that evaluate the evidence

All formulas below are proposed transformations, not reported source scores. They use measurement units and propagated uncertainty instead of categorical ladders.

| User's consideration | Numerical cell | Deterministic calculation and interpretation |
| --- | --- | --- |
| Signal strength | Native net rate/amount `J`; signal-to-uncertainty `z` | Keep signed estimate and uncertainty. For a specified reference θ0, `z=(J−θ0)/u_J`. It is an evidence statistic under an error model, not annotation probability. |
| Isolation of effect | Net fraction `F=(U−B)/U` for U>0 | Numerator is measured signal after an applicable matched blank; denominator is raw signal. Specifies how much measured signal survives that subtraction. A genotype-deletion difference is not automatically such a blank or pure protein attribution. |
| Experimental comparability outside the intended variable | Standardization `h=g(x_ref)/g(x_assay)` and uncertainty from nuisance differences | Use an experimentally established response g, not a raw pH, temperature, expression or substrate-concentration ratio. The intended variable is omitted from the nuisance vector. Multivariable interactions require g(x), not an assumed product of independent responses. |
| Comparability as a numeric evidence component | `C_comp=V_U/(V_U+V_comp)` | Fraction of initial precision retained after uncertainty in measured nuisance corrections is propagated. This describes the effect of comparability limitations on the comparison. It is not standalone experimental quality. |
| Isolation uncertainty | `I_precision=(V_U+V_comp)/(V_U+V_comp+V_iso)` | Additional precision retained after uncertainty in measured blank/mixed contributions. The separate mean isolation fraction F and this variance contribution are not duplicate penalties. |
| Measurement validity/weakness | Calibration/recovery corrections and their uncertainties; unresolved bias interval | Correct the actual amount/rate once. Convert a demonstrated nuisance bound to an interval for J; do not invent a bound or replace missing background with zero. |
| Consistency/independence | Covariance, independent-preparation count, residual heterogeneity | Keep technical versus independent repeats distinct. Use variance/covariance in pooling; assess residual Q against the actual model before adding between-preparation variance. |
| Target/system relationship | Mapped target response `J_T=m(J_source, correspondence, system)` with prediction uncertainty | Identity, experimentally demonstrated equivalence, conserved molecular features, structural/sequence correspondence, membrane environment and substrate access may inform m. Available scores remain numerical inputs, not a blanket transfer weight. Missing m means target-level inference is unresolved. |

Here `U` and `B` denote comparable raw signal rates or amounts, `V_U` is propagated uncertainty from the principal measured signal, `V_comp` from measured nuisance conditions/corrections, and `V_iso` from background/mixed contributions. The scalar partition assumes independent uncertainty blocks. With correlated blocks, preserve the full covariance matrix and its cross terms; do not manufacture nonnegative independent components by ignoring covariance. A total `V=∇fᵀΣ∇f` remains well-defined where f is identifiable. Nonnormal or poorly identified fits require intervals or likelihoods instead of a nominal Gaussian z.

The component combination is explicit. For `J=G(U−B)` with `G=h/(r N f_orientation)` and the variance partition above,

`z = (U/u_U) × [(U−B)/U] × sqrt(C_comp × I_precision)`

when θ0=0, the first-order variance propagation applies, and G is positive. Equivalently `z=J/sqrt(V_U+V_comp+V_iso)`. These are two algebraic descriptions of the same calculation. **Do not subtract B, compute z from the corrected rate, then multiply z by F again.** Correcting a known bias changes the estimate; propagating uncertainty in that correction changes its uncertainty. These are different effects, not a second penalty for the same known loss.

The fractions C_comp and I_precision are information retained relative to a stated measurement baseline. A noisy experiment can have C_comp near one simply because additional nuisance uncertainty is small compared with its already large noise. Its final z remains small. Thus these fractions must be interpreted alongside signal and total uncertainty, not ranked as independent universal quality scores.

Earlier per-paper notes also propose `min(g_A,g_B)/max(g_A,g_B)` as a response-similarity diagnostic. That is useful for describing expected uncorrected mismatch, but it must not also multiply evidence after the same mismatch has been standardized and propagated. The variance-based C_comp above is the proposed combination cell for the corrected measurement. Likewise the earlier `F_resolved` lower-bound examples are bounded descriptive quantities, not a replacement for signed estimates, contradictory findings, or an overall annotation probability.

## Fully calculated synthetic example

The following values are **invented solely to demonstrate the combination**, not BtsT, MurJ, PxpT, or any paper's observations. Consider a purified transporter reconstituted in vesicles, validated initial flux, and a matched protein-free-vesicle blank under the same gradient. The target is the identical assayed molecule. Assume these independent standard uncertainties, with every listed calibration measured and no additional unresolved contribution:

| Input | Synthetic value |
| --- | ---: |
| Raw uptake U | 6.00 ± 0.30 pmol/s per aliquot |
| Matched background B | 1.00 ± 0.10 pmol/s per aliquot |
| Recovery r | 0.80 ± 0.02 |
| Total inserted transporter N | 0.50 ± 0.025 pmol |
| Correctly oriented active fraction o | 0.60 ± 0.03 |
| Measured nuisance-response standardization h | 1.25 ± 0.05 |

The stated o already includes the transport-active fraction, so no separate unknown active fraction is multiplied. h is a hypothetical measured response correction; it is not a subjective resemblance score.

`G=1.25/(0.80×0.50×0.60)=5.2083333 pmol⁻¹`.

`J=G(6−1)=26.0416667 s⁻¹`.

`V_U=(G×0.30)²=2.4414063 s⁻²`.

`V_iso=(G×0.10)²=0.2712674 s⁻²`.

`V_comp=J²[(.02/.80)²+(.025/.50)²+(.03/.60)²+(.05/1.25)²]=4.8997667 s⁻²`.

`V_total=7.6124403 s⁻²`; `u_J=2.7590651 s⁻¹`.

`F=5/6=0.8333333`; `C_comp=0.3325635`; `I_precision=0.9643653`.

The explicit score-component product is

`z=20×0.8333333×sqrt(0.3325635×0.9643653)=9.4385836`.

Direct calculation `26.0416667/2.7590651` gives the same result. Calibration recovery is divided out, not multiplied in as an extra 0.8 reliability penalty; orientation is in the molecule denominator and its uncertainty is propagated, not reused as a 0.6 annotation penalty. Arithmetic was checked with Python's standard library and retained in 08_synthetic_arithmetic.json. This z assumes the complete synthetic error model; it is not a universal transport cutoff or posterior confidence.

## Interface to annotation scoring and multiple evidence items

One possible numerical interface is a likelihood contribution for a **declared molecular claim**, using the completed measurement and target-response model. For observed vector J with covariance Σ and specified predictions μ_H and μ_0 under competing claims,

`ell_A105 = −0.5[(J−μ_H)ᵀΣ⁻¹(J−μ_H) − (J−μ_0)ᵀΣ⁻¹(J−μ_0)]`.

Equal covariances are assumed in that expression; differing models require their log-determinant and normalization terms. For independent experiments, likelihoods multiply and their log contributions sum. Shared controls, source-to-target corrections, and repeated representations require the joint covariance/measurement model, not independent sums. The sheet must not add F, C_comp, affinity, replication count and ell as independent evidence after they have already contributed to the same likelihood.

For the synthetic example only, fixed predictions μ_H=20 s⁻¹ and μ_0=0 s⁻¹ give `ell=42.1459243`. The number 20 is an explicitly synthetic claim prediction, **not a default definition of transport activity**. Choosing a fitted positive-rate alternative produces a likelihood-ratio test, not automatically a Bayes factor; integrating over unspecified alternatives requires an explicit model/prior. The parent's common sheet must decide its claim interface before this can be treated as the final axis contribution. No 0–100 confidence or annotation-credit conversion is adopted here.

To pool rates representing the same quantity under a valid common-response model, `Jbar=(1ᵀΣ⁻¹J)/(1ᵀΣ⁻¹1)` with variance `1/(1ᵀΣ⁻¹1)`. Residual disagreement `Q=(J−Jbar1)ᵀΣ⁻¹(J−Jbar1)` tests that model under its assumptions. If justified independent-preparation heterogeneity is modeled with τ², add it to the appropriate covariance rather than also multiplying by a separate consistency penalty. Different endpoints or gradients do not become contradictory replicates until a response relation connects them.

For a calibrated nondetection at threshold L with known Gaussian measurement uncertainty σ, use a censored likelihood `P(Y<L|H)=Φ((L−μ_H)/σ)` rather than assigning J=0. With no threshold or noise model, nondetection cannot be converted into an exact exclusion score. Preserve negative net estimates and upper bounds. They may weaken a compatible transport claim. Missing components are unknown; return conditional results or explicit intervals, without defaulting missing terms to 0/1 or dropping independent evidence through a maximum.

## Source-to-component trace and actual limits

| Reviewed source | Component developed | Separate packet |
| --- | --- | --- |
| PMC3067607 / JB.01252-10 | Growth/colonization versus actual transport boundary | 01_fucp_2011_boundary.md |
| PMC5738728 / JB.00599-17 | Initial rate, blank applicability, saturation response, gradients, isotope dilution, reconstitution/orientation | 02_btst_2018_components.md, including additive arithmetic correction |
| PMC5847655 / JB.00771-17 | Extracellular disappearance, interval endpoint, population loading and metabolic confounding | 03_csta_ybdd_2018_endpoint.md |
| PMC6349089 / JB.00610-18 | Mixed physiological populations, total-protein normalization, nonzero time zero, label loss | 04_vbnc_pyruvate_2019_components.md |
| PMC3215060 / pnas.1104209108 | Fraction-specific concentration denominators, recovery/contamination matrix, localization versus movement | 05_hpnn_2011_localization_boundary.md |
| PMC4163187 / science.1254522 | Coupled reporter access, membrane protection, calibrated count units and reporter-versus-transport kinetics | 06_murj_2014_accessibility_components.md |
| PMC13274462 / aem.02181-25 | No direct PxpT transport; separate PxpR binding stoichiometry, heat blank, identifiability and nondetection | 07_pxpt_pxpr_2026_binding_boundary.md |

These papers motivate specific operands rather than numerical grades for assay names. Prior worker sources BioY/Fluc/YjeH and the other FucP source were deliberately not reopened; their reconciliation with this block remains the parent's combined work. Supplementary material remained inaccessible for HpnN, MurJ and PxpT/PxpR. MurJ's graph interval is visibly estimated and explicitly not a sampling interval. No raw primary dataset was downloaded, no full assay was refitted, and no independent source-to-target calibration dataset was inspected. Main-paper measurement uncertainties and technical/biological replication ambiguities remain exactly as recorded.

## Exact remaining design/measurement work

1. Select the common sheet's annotation-facing numeric meaning: the proposed likelihood contribution requires defined claim predictions/alternatives or an explicit calibrated transformation. z alone is not annotation confidence.
2. Define and validate source-to-target response/correspondence models. Sequence/structure/context scores may contribute, but none can be multiplied into a probability without a demonstrated relationship. Native identity does not erase altered membrane/assay conditions.
3. Populate actual calibration, nuisance-response, background and covariance inputs for at least one fully worked transport dataset; the fully combined example above is synthetic. The papers supply useful real components and important unknowns, not all operands for one universal complete score.
4. Resolve uncertainty type and independent-preparation identities where the source is ambiguous; retain exact partial results meanwhile. Recover raw counts/time series and inaccessible supplementary data where needed for quantitative claims.
5. Establish how common-sheet covariance/evidence identity represents linked assay controls and cross-axis reuse. A105 movement and A106 causal perturbation may refer to one experiment; they cannot become independent duplicate observations.
6. Obtain the user's feedback on the explicit component meaning/combination before treating this research proposal as settled. No scorer, reader, prompt, publication or scientific-run change was made.
