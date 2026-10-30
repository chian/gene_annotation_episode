"""Scientific TASK for the agreed reusable A105 assay assessments.

These instructions explain source interpretation and numerical operand meaning.
They do not expose a worksheet schema or infer scientific facts from discovery.
"""
from .literature_assay_grading import ASSAY_TYPE_LABELS, COMMON_CRITERIA, CRITERIA_BY_TYPE, CRITERION_QUESTIONS


_TYPE_LABELS = ASSAY_TYPE_LABELS


ASSAY_GRADING_TASK = """Evaluate the selected assay using its reusable protocol type, measured quantity and functional assertion. Follow A105 experimental evidence subscore → subscoring grader → subscoring reader. Select the applicable existing protocol group below, then select readers for the needed measurements and their actual source format. Molecule identities, reagents, conditions and source locations are operands and applicability evidence; a paper or protein–substrate example is not a grader type. Preserve the exact functional resolution of rates, finite conversion, composition, reaction accounting, binding, transport, protein signal and amount.

Populate the same reusable template separately for each actual experiment. Preserve its source-anchored experiment_ref and the original physical measurement keys. A different experiment supplies another instance; a repeated representation or revised extraction remains tied to its original experiment and does not establish independent evidence. Retain complementary assays and disagreements. Combine experiment scores in the existing literature parent with reliability SUM, validity SUM, relevance MAXIMUM, attribution MAXIMUM and overall SUM, using the actual selected saved components and the explicit A105 aggregation operation.

All groups feed the same reliability, validity, relevance and attribution dimensions. Keep comparability outside the intended experimental change explicit. For the selected estimate, examine these common questions: """ + " ".join(
    CRITERION_QUESTIONS[name] for name in COMMON_CRITERIA
) + "\n\n" + "\n\n".join(
    label + ' (' + kind + '): ' + ' '.join(
        CRITERION_QUESTIONS[name] for name in CRITERIA_BY_TYPE[kind] if name not in COMMON_CRITERIA)
    for kind, label in _TYPE_LABELS.items()
) + """

Apply only the questions relevant to the selected quantity and assertion. A descriptive rate comparison need not fit a kinetic model. A substrate-disappearance or completion-time result does not itself claim an identified product; an amount or time result need not be a conversion fraction. A finite composition need not be equilibrium. Where the contract permits not_applicable, support that interpretation from the actual question and source. Otherwise preserve supported, unknown and conflicting interpretations distinctly, with the applicable source witnesses. A control's label alone does not establish its adequacy, and a reported count alone does not establish independent preparations.

Reuse activity_rate for enzyme kinetics, substrate-specificity comparisons, optical rates and rate-based partner omission/addback. Choose the actual kinetic parameter or contrast quantity without interpreting higher Km as higher activity. An optical NADH-depletion rate remains its measured reporter endpoint unless the coupling and attribution evidence establishes the claimed reaction. For omission/addback contrasts use the partner quantity and examine the perturbation criteria; the partner's intended change is not a nuisance-condition penalty.

Use ligand_binding for binding parameters and discrimination, retaining IC50 versus Kd, fit/model meaning, ligand mapping and nonspecific controls. Use transport_response for the actual uptake, saturation, electrical or ion-discrimination quantity; a saturation correction is not an independently measured flux, and charge equivalents do not identify the transported ion. Use protein_signal for reported ratios or gel display measurements, preserving loading, exposure, ROI and detector limits; display darkness is not calibrated molecular occupancy. Use protein_amount for amount, preparation-composition and active-site measurements; mass fraction is not active fraction or contaminating activity. These supporting measurements can inform the same A105 assessment without becoming direct functional evidence by relabeling.

Select the grader by the experiment's protocol and question, not the reader's format. A controlled gel-shift binding experiment may use ligand_binding with its native band_display_fraction and binding-specific controls; it need not claim a fitted Kd or calibrated occupancy. A kinetic reader's actual Km may populate transport_response as transport_parameter when it belongs to the studied transport system and fit. Preserve that preparation and concentration scope rather than treating a shared reader as a fixed assay assignment.

Select effect as the already reported or calculated native quantity being assessed. Select effect_variance only as the variance of that exact estimate on its squared unit scale, retaining its corrections and shared inputs. Select recovery as an applicable measured recovery ratio; attributed_signal and total_signal as the supported same-endpoint contribution and denominator; and condition_test and condition_reference as a nuisance-condition comparison outside the intended experimental change. Keep the intended test/reference change out of that nuisance correction. These operands support separate diagnostics; do not multiply them into an effect that already includes their corrections or turn them into universal quality weights.

Select assertion_prediction and alternative_prediction only from explicit predictions for the same quantity, units, assertion and experimental conditions. Neither the observed effect nor a desirable result supplies an independent prediction. An overall experimental-evidence score is required. Select the applicable supported comparison model: known-variance normal, an explicitly justified normal approximation using estimated variance, or a Student-t residual model using estimated variance and source-supported degrees of freedom. A reported SD is not automatically the variance of the selected estimate, and estimated variance does not become known variance. Student-t degrees of freedom must belong to that estimator; a displayed sample count alone does not supply them. If the appropriate model, predictions, exact estimate variance or scientific support is unavailable, report the score as unresolved with its actual missing-input or unsupported-model reason while returning useful native measurements and supported diagnostics. Do not describe that limitation as an optional scoring requirement. The signed log evidence ratio is not a function probability, target-transfer weight or final annotation credit.

Preserve below-detection or other censored observations together with their actual limits, units and assay context. An observed upper or lower limit can enter the selected comparison through its event probability; it must not become zero or an observed threshold value. A confidence interval, error bar, graph-reading interval or range over ambiguous readings is not a censored observation. If no numerical limit or applicable reporting model is established, retain that specific unresolved limitation.

Use received numerical components or authenticated literal source spans as the operation permits; do not enter model-authored measurements. Preserve graph-reading uncertainty separately from experimental variation, shared observations across assays, complementary endpoints and contradictions. Return exactly the requested saved A105 components and necessary scientific qualifications through the parent's typed form. Distinguish unselected information, missing source evidence and unsupported readers/calculations/bindings. An extracted number alone does not complete the assay assessment, and unavailable fields are not zero scores."""

ASSAY_GRADING_OPERATION_DESCRIPTION = (
    'Populate the same A105 experimental evidence dimensions using one selected reusable assay type: '
    'activity/rate (including kinetics, optical rates and partner perturbations), endpoint conversion, '
    'product distribution, reaction coupling, binding, transport, protein signal or protein amount. '
    'Retain each actual experiment as its own instance of the same reusable template, with '
    'experiment identity and shared physical measurements preserved. '
    'Select scientific applicability by protocol, quantity and design, then select possessed reader '
    'components or authenticated source numbers by their actual capability and source format. '
    'Return requested native effect, reliability, validity, attribution, comparability and '
    'assertion-comparison components with source-supported interpretations. The overall log evidence '
    'ratio requires explicit fixed predictions and a supported known-normal, estimated-normal approximation '
    'or Student-t residual model. Preserve estimated uncertainty, actual degrees of freedom and observed '
    'censoring limits; do not treat reading ranges as censoring. Scores remain conditional, and missing '
    'inputs preserve partials. Existing corrections are not applied twice. '
    'No case-specific grader, general parser capability, target transfer or annotation credit is inferred.'
)

__all__ = ['ASSAY_GRADING_TASK', 'ASSAY_GRADING_OPERATION_DESCRIPTION']
