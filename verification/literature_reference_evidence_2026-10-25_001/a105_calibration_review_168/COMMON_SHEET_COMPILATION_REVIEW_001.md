# A105 numerical sections: proposed compilation and current gaps

This is a review artifact, not a goal replacement or accepted scoring policy. It answers the current human architecture question with concrete numerical behavior. Exactly ten evidence axes remain. A105 component stores are separately implemented modules; the common whole-A105 sheet has not yet been assembled.

## Logical sheet versus modules

The logical sheet evaluates a particular functional assertion about the actually studied molecule under its experimental scope. Multiple experiments and numerical component records can contribute. Investigation instructions establish scientific meanings; readers retain the supported operands; calculators populate the numerical sections. Technical record boundaries do not create extra axes or independent assays.

Supporting source/experiment relationships remain separate from numerical cells. An exact source quote verifies custody, not the truth of an interpreted experimental relation. A functional assertion may emerge during investigation; neither a target annotation nor a searchable public name is a prerequisite.

## Numerical compilation for one supported activity design

The existing activity calculator implements a restricted concentration-rate design:

    a = (q-g) * v/(k*E*u)
    V = J * Sigma * J_transpose + distinct_residual_variance
    standard_uncertainty = sqrt(V)
    precision = 1/V, for V > 0.

q is an already established net sample-minus-blank endpoint rate. g is a separately measured contaminating contribution to that same endpoint, not the blank again. k is an established dimensionless recovery applicable to that measured quantity and matrix. E is the assayed molecule's molar concentration. u and v are measured test/reference responses in a separate same-endpoint condition control outside the deliberately changed variable. Each relationship needs scientific evidence; the calculator does not infer it from compatible numbers.

The subtraction addresses quantified effect isolation. Multiplication/division address established calibration, normalization and a measured condition-response difference. These are numerical compilation within the source experiment, not target correspondence or W05 credit.

The uncertainty compilation uses original shared measurement ownership and cross-covariances. Sigma must not silently become diagonal. Distinct residual variance must represent additional corrected-scale uncertainty, not error already propagated from the same operands. A source SD, SEM, confidence limit and calibration systematic error have different meanings. Missing uncertainty does not become zero. The existence of technical repetitions does not establish independently prepared samples.

SYNTHETIC_SECTION_COMPILATION_001.json supplies an explicitly synthetic numerical example, independently checked using exact decimal Fraction arithmetic:

| Numerical component | Value | Role |
|---|---:|---|
| q-g | 1.6 uM/min | Quantified same-endpoint subtraction |
| 1/k | 1.020408163265306 | Applicable recovery correction, assumed for this illustration |
| v/u | 1.111111111111111 | Separate measured condition-response correction, assumed for this illustration |
| Corrected a | 0.9070294784580499 per_min | Compilation of the supported source-activity operands |
| First-order variance V | 0.007659702892498086 per_min_squared | Synthetic uncertainty including all declared primitive errors |
| Standard uncertainty | 0.0875197285901761 per_min | Spread of the first-order propagated quantity |
| Precision 1/V | 130.55336662984672 min_squared | Dimensional precision, not a calibrated reliability probability |

The example explicitly supplies mutually uncorrelated synthetic primitive errors and zero additional residual variance. Those are fixture assumptions, not defaults for papers. No normal observation model is supplied. The existing optional normal-model profile and proposed presence-index outputs therefore remain unavailable; they do not fill a generic overall reliability score. Neither precision nor activity measures product specificity by itself.

## Sections need their own scientific meanings

| Meaning being evaluated | Numerical contribution when supported | Relationship that arithmetic cannot invent |
|---|---|---|
| Reliability / precision | Replicate-design SD or SE; propagated variance and precision; independently grounded uncertainty | Sampling units, independent preparations, covariance and applicable error model |
| Calibration / method validity | Measured/expected recovery, signed bias, applicable physical conversion and correction | Correct analyte/standard, validation relation, matching matrix, interference controls |
| Comparability outside intended change | Same-endpoint measured response ratio for a non-intended condition difference | Which variable was intended; whether the response control actually isolates the other change |
| Attribution / effect isolation | Quantified subtraction, mixture partition or product-attributed fraction in a defined model | Actual contributors; blank versus contaminant versus partner; quantitative linkage to the same endpoint |
| Functional relevance / specificity | Defined substrate/product or alternative-function contrast; productive fraction where quantified | Which functional assertion is tested; endpoint versus proxy; chemical identity and resolution |
| Complementarity / consistency | Comparable-effect contrasts or joint-uncertainty calculations when relationships are established | Same underlying quantity versus distinct endpoints; dependence or independent verification; conditions that explain differences |

Attribution contributes to validity but is not a synonym for functional relevance. A well-supported binding constant cannot be treated as equally direct evidence for turnover. A common numerical format should preserve these different meanings rather than force unrelated assays into the activity formula above.

## What remains before adequacy

The activity equation and readers for individual assay components do not implement the whole logical sheet. Still required are concrete claim/experiment bindings and a common saved representation of appropriate section components; verified source-driven cross-component linkage and uncertainty/dependence; and assay-specific compilation where the activity equation does not apply. Alternative input readers do not count as additional assay-specific grading.

The paired recovery workload169 addresses one identified gap in the calibration section. It is currently pure reader/calculator work, without LiteratureEpisodes integration. Its source recovery, bias and inverse are algebraic views of the same operands and must not be counted as independent evidence. Other unresolved conversions and coverage gaps remain in the inherited progress records. Unknown source facts and unimplemented readers must remain separately identified.

No equal section average, fixed category weight, universal quality threshold, calibrated function probability or completed whole-A105 score is adopted here. The required later-credit handoff is a populated scientifically scoped numerical sheet with explicit formulas, actual operands, uncertainty and dependencies. Target correspondence and final annotation-credit aggregation remain outside this work.
