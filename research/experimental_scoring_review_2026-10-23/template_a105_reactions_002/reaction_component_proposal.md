# Reaction-component reconciliation for the A105 numerical sheet

New research synthesis, 2026-10-23. This reconciles three newly inspected primary papers into proposed numerical cells and calculation interfaces for the parent's common sheet. It does not replace the user's three-part template or the parent's developing common calculation. `a105_sheet_construction_001/EXPERIMENTAL_RELIABILITY_001.md` is awaiting user feedback and is not adopted policy; this note does not claim to have inspected that file. No scorer, reader, prompt, library or scientific run was changed.

The three paper packets remain separate so the parent can perform the required complete authority reset after each packet:

1. `frsa_2013_review.md` — Kellett et al. 2013, DOI 10.1021/bi400093y; full main text and full supplement inspected.
2. `frsa_2011_review.md` — Lee et al. 2011, DOI 10.1038/nchembio.589; complete corrected supplement, original Table 1, original Figure 1/caption and indexed original main-page material inspected; full main article not recovered.
3. `moral_2011_review.md` — Moral et al. 2011, DOI 10.1016/j.ab.2011.06.031; complete main text, table, captions and Figures 2–5 inspected; supplement not recovered.

Each packet records its own full post-paper authority reread. The latest user goal was read last. The third reset's truncated initial output was repaired before interpretation. This synthesis uses the already completed interpretations; no new retained paper packet was opened while preparing it.

## Define the comparison before calculating a number

Every row needs the assayed organism and construct; target material if different; protein preparation identity; known coexisting species; intended changed variable; all other known differences; substrate, products and reaction equation; measured endpoint and time window; numerator/denominator; units; matched controls; uncertainty meaning; and shared-data identities.

These are supporting definitions, not numeric category scores. They determine which quantities can legitimately enter the same calculation. Examples of distinct comparisons are activity of two purified proteins under matched conditions, two detectors applied to the same reaction, and the same detector applied to different matrices. They do not imply the same nuisance corrections or the same independent replication.

The intended variable must stay visible. If the investigation deliberately changes substrate identity to measure specificity, correcting away the substrate response as a “nuisance difference” destroys the scientific comparison. By contrast, an unintended temperature mismatch needs its measured effect on rate considered. A nominal temperature ratio or a count of matching protocol fields does not quantify that effect.

## Numerical cells and exact operands

| Proposed cell | Definition / calculation | Meaning and missing-data treatment |
| --- | --- | --- |
| Calibrated channel rate `y_k` | `y_k = (s_k − b_k)/m_k` for a linear calibration, with a specified nonlinear inverse where required | Instrument slope `s`, matched blank `b`, calibration slope `m`; units become concentration/time. Missing matched calibration leaves the absolute rate unknown. |
| Signal and calibration uncertainty | Full input covariance propagated by `Σ_y = J Σ_inputs Jᵀ` | Includes blank, sample and calibration uncertainty. SD, SEM and fit SE are distinct inputs. Shared calibration terms create off-diagonal covariance. |
| Response correction `q_j` | Fraction of a defined rate/endpoint expected from a measured detector response and the actual time window | Correct by `v_j = y_j/q_j`, or fit the convolved model directly. Missing response data remain missing when the window is materially affected. Do not apply the loss again after correction. |
| Reaction isolation `I_reaction` | Target-reaction contribution divided by the calibrated total signal, from an explicit stoichiometric model | Separates chemical pathways. It is neither a protein purity fraction nor an annotation probability. The denominator must match the measured signal. |
| Unintended-catalyst contribution `h_j` | Measured rate of the target reaction assigned to other catalysts under the same assay conditions | Subtract from target-reaction rate once. Purity by protein mass does not populate this field. Missing attribution is not zero contamination. |
| Amount normalization `E_j` | Measured concentration of total assayed protein or directly measured active sites, explicitly distinguished | Produces turnover units. If active sites are the denominator, do not multiply by active fraction again. Unknown catalytic occupancy is not the ratio of measured metal to total possible metal sites. |
| Experimental-condition response `K_j` | `g(c_j)/g(c_reference)` from measured nuisance-response data with the intended variable excluded | Maps an observed rate to a reference condition. Its uncertainty quantifies residual comparability. Absent bridges are not set to one for different conditions. |
| Standardized activity `a_j` | `(r_target,j − h_j)/(E_j K_j)` after any necessary detector correction | A molecular-activity estimate in declared units, not by itself an evidence-strength score. |
| Independent-preparation variation | Variance or a covariance model fitted to genuinely separate preparations under the declared conditions | Technical repeats estimate a different error component. A publication count is not preparation count. |
| Consistency residual | Difference between comparable estimates divided by its full uncertainty; vector form `Q = (a − Xβ)ᵀ Σ⁻¹(a − Xβ)` | Describes disagreement with the specified common-parameter model. Report the residual and model; do not average away systematic differences. |
| Relation to annotation target | Measured correspondence inputs and an explicit relation model | Identity, structural/sequence correspondence, relevant molecular features or direct comparative activity can inform different relationships. Do not replace the model with a single intuitive grade. No such target relationship is established by these method examples. |

Paper-specific filled numbers and checked arithmetic are in their separate packets. The table is a proposed interface for readers to populate the numerical sheet; the readers are not implemented here.

## Explicit separation of comparability from isolation

**Comparability** asks what the same underlying molecular activity would produce under different incidental conditions. A measured response surface `g(c)` converts those conditions to expected rate changes. In a log-linear local model,

`log K_j = βᵀ(c_j − c_reference)`.

This is usable only over the experimentally supported range, with measured `β` and its covariance. Interactions require additional terms. Its variance includes uncertainty in the response coefficients and in the measured conditions. Multiplying separate pH, salt and temperature factors assumes separability and requires evidence; it is not the default.

**Isolation** asks what share of the measured chemical signal comes from the intended reaction and catalyst. Let the calibrated multi-channel rate vector satisfy

`y = S r + ε`,

where `S` is the stoichiometric response matrix and `r` contains rates of the possible chemical reactions. A direct inverse or generalized least-squares fit estimates the target-reaction rate when the channels identify it. The reaction's products and calibrated channels establish `S`; a proxy alone may leave it unidentifiable.

Attribution to the protein is an additional mixture model. For fractions or preparations `j`,

`r_target,j = k_target E_target,j + Σ_h k_h E_h,j + b_j`.

Independent variation of measured protein amounts can identify catalytic contributions if the design has sufficient rank and the rate coefficients apply over the compared conditions. A single purity estimate does not identify `k_h`. Even a small molar fraction of a fast contaminant can dominate the reaction. Conversely, an unintended chemical pathway catalyzed by the intended protein is a reaction-specificity issue without being protein contamination.

The two questions therefore have different measurements and different variance components. A perfectly matched assay matrix does not establish catalyst attribution. A chemically isolated reaction does not establish comparability to another temperature, pH or detector window.

## How the cells combine without counting a loss twice

For positive, sufficiently resolved rates, write `ell_j = log(a_j)`. The proposed uncertainty calculation is the propagated covariance of the corrected, normalized estimate:

`V_j = V_signal,j + V_calibration,j + V_comparability,j + V_isolation,j + V_amount,j + covariance_terms`.

This is bookkeeping by physical source of error, not a demand that every term be independent. Use the full Jacobian calculation when variables overlap. A target-correspondence model, if one is actually supported, contributes its own uncertainty and systematic relation rather than silently becoming another assay measurement.

For a single extra uncertainty source, a displayed comparability multiplier can be defined as a precision ratio:

`C_j = V_base,j/(V_base,j + V_comparability,j)`.

Its quantitative meaning is how much precision remains after including the measured bridge uncertainty. The corresponding weighted contribution is

`C_j / V_base,j = 1/(V_base,j + V_comparability,j)`.

Apply that relationship **once**. If the full variance is already in the denominator, multiplying the result by `C_j` again would penalize the same uncertainty twice. Likewise, if a measured isolation fraction corrects the rate, do not also apply it as another blanket penalty. The correction's uncertainty still belongs in the covariance.

For estimates of a genuinely common molecular parameter, the explicit combination is

`ell_combined = (1ᵀ Σ⁻¹ ell)/(1ᵀ Σ⁻¹ 1)`;

`V_combined = 1/(1ᵀ Σ⁻¹ 1)`.

This combines numerical evidence through sums and products while retaining dependence. It is not legitimate when the observations measure different endpoints, when their condition bridges are missing, or when the common-parameter model fails. A detected method difference may require separate method parameters or a separately measured bridge before pooling.

An annotation comparison requires one further explicit model layer. With specified molecular-function and alternative models, a potential interface is

`S_A105 = log L(all A105 measurements | function model) − log L(all A105 measurements | alternative model)`.

Independent preparation contributions add on this log scale; observations sharing controls or calibrations enter a joint likelihood. This is a **proposed interface**, not an adopted score or a calculation completed by these sources. The null/alternative models, their parameter ranges and the treatment of incomplete target correspondence still need definition and user review. A large measured rate is not automatically stronger annotation support than a smaller, better isolated rate.

## Contradiction, nondetection and missing fields

An assay reports a nondetection only relative to a demonstrated measurement range and decision rule. A valid negative-data likelihood needs the actual assay's threshold, response model and uncertainty, plus the expected signal under the proposed molecular activity. Under a specifically justified normal model it can take the form

`L_negative = Φ[(L_detection − μ_predicted)/σ]`.

This does not authorize using a threshold from a cited method paper without measuring its transfer to the actual apparatus, matrix, channel, temperature and window. A time-integrated prediction also needs the reaction's substrate depletion, stability and detector-response treatment. A positive spike establishes that a detector can respond; an unspecified spike amount and response do not establish numerical sensitivity.

A positive result and a later nondetection should both remain in the evidence model. Their numerical contradiction cannot be calculated when essential detection or condition-response inputs are missing. Do not replace those missing inputs by a fixed disagreement grade or discard the less convenient result through an unexplained maximum.

Unknown and zero are distinct. Unknown off-target activity is not zero; unknown calibration variance is not perfect calibration; and unknown cross-system correspondence is not absence of correspondence. The sheet should retain the known components and mark exactly which combined calculations cannot yet be evaluated. These gaps keep the sheet unfinished under the user's criteria.

## Source-to-component reconciliation

| Primary source | What it contributes to the numerical sheet | Essential limit |
| --- | --- | --- |
| Kellett et al. 2013 | Distinct negative assays, assay/exposure definitions, control interpretation, and the need to define numerical detection sensitivity before assigning negative weight | No numerical detection limit, blank dispersion or quantitative spike recovery for the reported FrsA assays; incomplete preparation-by-assay mapping |
| Lee et al. 2011 | Positive kinetic estimates with stated SD, actual reaction/proxy comparisons, and a measured condition-response figure that reveals protocol dependence | No full raw replicate covariance, quantified catalyst attribution, matched response bridge to the later assays, or complete recovered main text |
| Moral et al. 2011 | Calibration dispersion, detector response, simultaneous chemical-pathway partition and quantitative comparison of two assay configurations | No transfer of its detection threshold to FrsA; incomplete raw paired covariance and supplementary retrieval; chemical isolation does not establish protein attribution |

The sources address complementary gaps. The calibration source does not retroactively complete the FrsA negative assay; the positive product evidence does not by itself assign the activity to pure FrsA; and the negative assays do not become a fully calibrated numerical refutation merely because their signals were reported absent.

## Exact remaining calculation gaps for the parent

1. **FrsA nondetection:** actual thresholds, matched blank distributions, quantitative spike recovery and response time for each 2013 assay. These are needed for a false-negative likelihood or rate upper bound.
2. **FrsA comparability:** measured nuisance-response bridges for the differing salt, temperature, reporter concentration, solvent/pD and timing conditions, with uncertainty. Nominal condition ratios cannot fill these cells.
3. **FrsA attribution:** quantitative rates assigned to FrsA versus possible contaminants, with activity tracking across informative fractionation or other selective biochemical measurements. Gel purity cannot supply activity purity.
4. **Independent units and covariance:** preparation/batch identities, exact replicate counts, shared standards/controls, and raw or fitted covariance. Current errors mix fit SE and assay SD and cannot all be pooled as the same uncertainty.
5. **Moral method reconciliation:** paired raw rates under matched conditions and a measured bridge separating detector method from the additional mixture/timing differences. The observed method ratio is not a pure calibration correction.
6. **Target relation:** a measured connection from the assayed molecule/system to the actual target for the inferred function. None of these papers supplies a ybhP/OxDC or ybhP/FrsA relationship.
7. **Common annotation interface:** the parent's reviewed definition of how the component likelihood/precision quantities enter annotation support, including alternative models and missing essential inputs. This note proposes arithmetic but does not adopt policy or complete that decision.

Additional primary papers should be selected only for one of these missing component calculations. These are not missing inputs that can be filled by reading more unrelated enzyme abstracts. The current three-source research contribution is complete within the inspected coverage; A105 and the ten-sheet goal are not complete.
