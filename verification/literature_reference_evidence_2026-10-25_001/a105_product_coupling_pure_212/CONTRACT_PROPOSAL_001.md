# Pure product/cofactor coupling interface

Bounded implementation proposal under the unchanged supplied goal. Parent
acknowledged the plan and refinements before coding. Only three new production
modules, one new test file and this new212artifact directory are owned.
No integration, overall A105 score or adopted annotation-credit policy follows.

## Scientific meaning and quantities

For one selected source arm, P is the reported identified-product formation
rate and H the reported cofactor-consumption rate on the declared basis. The
descriptive ratio rho=P/H has product-per-cofactor meaning. It is retained when
detailed matching or stoichiometry is unresolved, with those qualifications.
Physical productive fraction eta=nu_cofactor_per_product*rho additionally needs
the appropriate chemical identity, endpoint, normalization and assay links.
The direction is explicit;207used the reciprocal convention, whereas this
interface follows the parent211cofactor-per-product convention.

Nu is a witnessed interpreted reaction-account model, not an invented raw
measurement or a global1default. An uncertain supplied estimate retains eta
conditional on fixing that estimate, with explicit missing-nu-uncertainty
qualification. Unknownnu without an estimate supplies noeta. Known incompatible
chemical pairing yields no physicaleta. Native measurements remain available.
No nu is estimated by fitting the source coupling percentage.

Native printed0is retained with its source semantic interpretation. A negligible
or nondetected source value supplies no physical point ratio or invented upper
limit. Reported coupling and displayed-rate arithmetic stay separate. Ratio,
fraction, percent display and reconstruction reuse the same inputs and never
become independent experimental verification.

## Public pure interfaces

- inputs: product_coupling_population_schema(),
  product_coupling_extraction_schema(),
  read_product_coupling_inputs(arguments, *, read_source),
  validate_product_coupling_extraction(data).
- calculations: COMPONENTS, FORMULAS, MEANINGS, REASONS, QUALIFICATIONS,
  product_coupling_cell_schema(component=None), product_coupling_sheet_schema(),
  populate_product_coupling(extraction).
- prompt: exact six-paragraph PRODUCT_COUPLING_TASK copied from the reviewed
  parent211TASK_PROPOSAL_001.txt, kept separate from the sheet.

Input version a105_product_coupling_inputs_v1; sheet version
a105_product_coupling_components_v1, axisA105, sectionproduct_coupling.
This pure workload has noStore, provider, model, selected operation, repository,
receipt admission, child return, controller observation or W05 operation.

## Closed selected input

The selected input carries source_ref/source_kind; nullable exact source-witness
context fields for actual molecule/system/conditions/partners/endpoints and
limitations; product/cofactor/optional reported-coupling quantities; separate
witnessed endpoint-role, measurement-semantic and normalization interpretations;
physical-identity/dependency witnesses; pairing, molecule, preparation,
normalization, condition, identity and attribution relationships; a witnessed
nu interpreted-model value and fixed/uncertain/unknown/conflicting status; and
an optional received covariance-source reference. Numeric measurements are
selected by verified source-byte/character offsets, never entered as free values.

The source callback authorizes a received reference and representation and
returns exactly artifact_ref/contentbytes. All source reads occur in extraction.
The reader verifies numeric, markup, column and unit boundaries. It reuses
the frozen205general numeric/column helpers and existing rate-unit helpers,
whose actual dependency hashes will be retained. The bounded grammar supports
text/XML/HTML selections, not arbitrary PDF/OCR. Complete source ND, bounds,
approximation/range and nonfinite representations preserve specific per-quantity
limitations. Invalid/clipped/borrowed selections are repair errors.

Extraction stores exact source witnesses, native/canonical numeric values,
unit conversion, measured endpoints, model interpretations, original dependency
identities, source origins and any covariance result. Its validator is pure and
performs nosourceIO. Future saved reconstruction must use its own original
structural/authentication path instead of invoking numeric population again.

## Eleven numerical components/views

| Component | Calculation / meaning |
| --- | --- |
| reported_product_activity | Source product report, converted to per_min where supported; native source number/unit retained |
| reported_cofactor_activity | Source cofactor report on its actual basis; native number/unit retained |
| product_per_cofactor | P/H descriptive endpoint relationship |
| productive_fraction | nu_cofactor_per_product*P/H with physical/conditional meanings separate |
| calculated_coupling_percent |100*eta, same contribution |
| reported_coupling_percent | Source coupling report with native source scale retained |
| displayed_coupling_difference_pp |100*eta-reportedpercent; discrepancy, not assumed rounding/error penalty |
| reconstructed_product_activity |rho*H=P for the same operands; aliases originalproduct contribution |
| product_per_cofactor_variance |J*Sigma*Jtranspose from an explicit compatible joint estimate model |
| productive_fraction_variance |nu²*Vrho for fixednu; conditional fixed-substitution arithmetic for uncertainnu |
| productive_fraction_standard_uncertainty |sqrt(previousvariance), same uncertainty contribution |

Cells have separate interpreted and conditional numeric/exact values, relation,
unit, source-native value/unit, status, interpretation, origin/input origins,
measurement/model dependencies, contribution identity, explicit assumptions,
physical fraction domain status and specific unavailable reasons. Exact rational
arithmetic survives binary float projection limits. Nonrational roots are not
labeled exact rational results. Physical values outside[0,1]are not clamped.
Within this operation, no second reporter assay is automatically calibrated.

## Basic uncertainty calculation

An optional actually received JSON record contains exact ordered selected-rate
measurement keys, canonical per_min units, explicit joint covariance of the
selected rate estimates, status known/estimated/unknown, origin and basis.
The matrix is2x2, finite, symmetric and positive semidefinite. No covariance
offdiagonal is filled by default; zero must be explicitly supplied.

For rho=P/H and fixednu:

    J=(1/H,-P/H²)
    Vrho=V(P)/H²+P²*V(H)/H⁴-2*P*Cov(P,H)/H³
    Veta=nu²*Vrho.

This is first-order uncertainty propagation for the specified estimates, not
raw population variability, a confidence interval, function probability or
unbiased ratio variance. RawSD/CV/counts are not silently converted into this
matrix. Wrong owners/units/basis or invalid covariance leave uncertainty cells
unavailable with a specific reason and preserve the native/descriptive pair.
An uncertainnu estimate retains conditional fixed-substitution Veta separately
from unavailable totaleta uncertainty; nu covariance propagation is explicitly
unimplemented. This source supplies noTable3uncertainty, so none is fabricated.

## Source examples and contrasts

Original Table3WT206/289,T252N92/216,double132/343min^-1 yield descriptive
rho0.7128027682,0.4259259259,0.3848396501. Reported percentages71,42,38remain
separate. Detailed matching is unknown, so physicaleta stays conditional for
the interpreted source nu1convention. T252Aprintedproduct0withnegligible/ND
meaning and NADH427retains no physical point ratio. Table1culture yield is not
the assay denominator; Table2kinetics/SDs are not borrowed.

Native product activity and this paired endpoint mapping address the specific
chemical-function inference. Authentic-standard identity, cofactor loss and
peroxide answer different scientific questions. Water is source-inferred
subtraction, not independent mass balance. The Fig4double-mutant label conflict,
no quantified no-P450 blank, unknown active fraction and experimental linkage
remain visible limitations. Full reliability/validity/attribution/compatibility
compilation and complete A105assay coverage remain unfinished.
