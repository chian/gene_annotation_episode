# Finite A105 kinetic-parameter component proposal045

Prospective interface only. No production module, reader, prompt, selected
operation or scoring policy is installed by this document. This owner has read
no primary paper or retained paper-specific packet. The parent's standalone
scientific brief supplies the intended comparison; source truth is not proved
by this code design.

## Ownership and dependencies

Requested owned new files only:

- `gene_annotation_episode/literature_kinetic_calculations.py`
- `tests/test_literature_kinetic_calculations.py`
- this new `a105_kinetic_components_045/` verification directory.

No existing module changes. Existing rate units/meanings, binding calculators,
selected-operation catalog, typed projections and all033/035/037 dependencies
remain untouched. The only intended production import from existing code is
`ExperimentalContractError`; finite validation and arithmetic are local. No
new package, parser, source IO, Store, model, controller or episode dependency.

Read complete: active goal attachment; rootAGENTS; W04 correction/history;
experimental contracts; rate calculator; binding descriptive calculator;
binding conditional calculator; amount calculator; binding storage and
binding-model storage consumers. Latest040/039 instructions were read last.
Initial aggregate output truncated; rootAGENTS and W04 were fully reread in
separate bounded calls, not counted complete from that aggregate output.

## Supported experiment and finite scientific meanings

Compare already supplied kinetic parameter estimates for two substrates in
separate assays of the same actual molecule and construct. `Km`, `kcat` and
`catalytic_efficiency` are distinct parameter kinds; corresponding canonical
units are `uM`, `per_min` and `uM^-1min^-1`. The pure boundary accepts canonical
units only. A later targeted reader owns source syntax and unit conversion.
No quotient of reported kcat/Km means is substituted for a directly reported
efficiency, and no kinetic curve is fitted.

Use explicit numerator/denominator roles. A larger numerator parameter is the
positive mathematical direction; that is not automatically better binding,
activity, physiological specificity or annotation reliability (especially Km).

Closed input root:

    version: a105_kinetic_contrast_inputs_v1
    numerator: operand or null
    denominator: operand or null
    subject_relationship: same_molecule_and_construct|different|unknown|conflicting
    parameter_definition_relationship: same|different|unknown|conflicting
    substrate_arrangement: separate_assays|mixed_substrates|unknown|conflicting
    comparison_scope: reported_protocols|common_conditions|unknown|conflicting
    nonintended_conditions_relationship: matched|different|unknown|conflicting

Each closed operand:

    parameter_kind: Km|kcat|catalytic_efficiency
    unit: canonical unit for that parameter
    value: finite number or null
    status: point|censored|missing|conflicting
    relation: eq|lt|le|gt|ge|none
    approximate: boolean
    origin: reported|graph_derived|calculated|synthetic
    measurement_id: nonempty source-token identity
    physical_measurement_id: nonempty identity or null
    subject: {organism, genotype, molecule, construct} [nullable source labels]
    context: {substrate, preparation, experiment, experimental_system,
              conditions, endpoint, normalization} [nullable source labels]
    uncertainty: {statistic: sd|sem|ci|unspecified|unreported,
                  magnitude: finite nonnegative number or null,
                  interval: [finite lower,finite upper] or null,
                  count: positive integer or null,
                  repetition_basis: biological_preparations|technical_measurements|unspecified,
                  estimate_basis: fit_to_averaged_curve|between_fitted_parameters|unknown}
    source: {source_ref,artifact_ref,representation,start,end}

Source representations: original, text, retained_transcription, synthetic;
start/end are nonnegative byte offsets with end>start. The calculator preserves
them but cannot authenticate actual bytes/custody. Later readers must do so.
Source labels can be unknown/null; they are never synthesized from a paper name.
CI requires interval, not an assumed symmetric halfwidth. SD/SEM/unspecified
uses magnitude when present; unreported has no magnitude/interval. Neither
count nor uncertainty label generates a covariance or known-normal model.

## Numerical sheet

| Cell | Operand/calculation | Meaning and units |
|---|---|---|
| numerator_parameter | supplied point | actual selected parameter, native canonical unit |
| denominator_parameter | supplied point | actual comparison parameter, native canonical unit |
| parameter_difference | n-d | signed descriptive magnitude, same unit |
| parameter_ratio | n/d | descriptive parameter contrast, dimensionless |
| log_parameter_contrast | e=ln(n)-ln(d) | signed log magnitude, dimensionless |
| log_contrast_variance | V=Cnn+Cdd-2Cnd | variance of this log contrast, dimensionless squared |
| log_contrast_standard_uncertainty | sqrt(V) | conditional uncertainty of log contrast |
| source_profile_log_ratio | S=e*abs(e)/(2V) | conditional signed known-normal directional evidence |
| source_signed_index | B=tanh(S/2) | proposed bounded representation of the same S |

These are nine meanings/representations, not nine independent experimental
contributions. Inputs, exact source uncertainty and contexts remain supporting
records. Every cell includes value/unit/status/formula/origin/unavailable_reason,
approximate and conditional_on; raw arm cells also keep threshold/relation.
S/B are not function probabilities or compiled annotation credit.

Point n/d/difference allow zero/negative noisy point estimates as arithmetic
where defined, but log contrast requires both strictly positive. Missing,
conflicting and censored operands retain raw partials and null derived point
contrasts; thresholds never substitute for points. Approximate point/descriptive
cells retain approximate=true; conditional normal scoring is withheld for
approximate operands. No censored likelihood is implemented in this variant.

Pair arithmetic additionally needs supported same subject/construct, same
parameter definition/kind/dimensions, separate-assay arrangement, and a known
comparison scope. Different protocols remain allowed only as reported-protocol
comparisons. Common-conditions scope requires explicitly matched nonintended
conditions. No numeric penalty or correction is guessed from protocol changes.
Identical measurement_id or known identical physical_measurement_id cannot
create a two-operand contrast. Distinct IDs establish neither independence nor
the truth of the scientific relationship. Raw arm cells survive pair failures.

## Optional explicitly owned log covariance/model

`populate_kinetic_contrast(inputs, model=None)` and
`kinetic_operand_keys(inputs)` are the proposed public functions.

Closed optional model:

    version: a105_kinetic_log_model_v1
    measurement_order: [numerator,denominator]
    measurement_keys: [exact numerator key,exact denominator key]
    covariance: full finite symmetric PSD2x2 matrix or null if status unknown
    variance_status: known|estimated|unknown
    observation_model: known_normal_log_parameters|unspecified
    log_basis: natural_log_canonical_parameter
    origin: reported|derived|synthetic

Measurement keys bind parameter kind and nonnull physical_measurement_id;
unknown physical identities cannot authorize a model merely from source-token
identity. Wrong order/owner/dimension, bools, nonfinite numbers and indefinite
matrices reject with repairable ExperimentalContractError(code,field). Use exact
Fraction arithmetic to validate PSD and calculate V without cancellation/jitter.
Known/estimated covariance yields V/sqrt(V). Unknown covariance yields nulls.
V=0 is retained as a degenerate variance, but S/B remain null; it is not infinite
certainty. Estimated covariance does not authorize a known-variance profile.
Only known covariance, explicit known-normal log model, exact positive operands
and V>0 authorize S. Rounded tanh endpoints or underflow remain numerical-range
unknowns while preserving finite S. Nearby unequal logs use log1p fallback.

Multiple calls sharing a physical numerator remain dependent. This single-pair
variant returns operand keys and covariance provenance/status, supplies no joint
score and never sums S across contrasts. A later comparison collection needs
the actual joint primitive covariance; marginal2x2 models do not supply it.

## Explicit numerical compilation and boundary to common A105

Within this finite component: e=(+1,-1)log(parameters),
V=(+1,-1)C(+1,-1)^T, S=e*abs(e)/(2V), B=tanh(S/2).
These explicit sums/multipliers yield conditional evidence for one mathematical
parameter distinction. They do not constitute experimental validity, isolation,
common-condition correction or an overall reliability number. Existing corrected
activity/rate/binding cells are not modified or multiplied into this result.
W05/final credit, target correspondence and cross-axis aggregation stay outside.

## Verification proposal

Synthetic tests only: all three parameter dimensions; positive/negative/equal
contrast; canonicalunit mismatch; separate protocols versus commoncondition
requirements; sameowner/unknownidentity; missing/censored/conflicting/approx
partials; untyped spread/technical count not generating covariance; known vs
estimated vsunknown covariance; correlated/anticorrelated/PSD/singular/invalid
matrices; swapped/forgedowner; bool/NaN/hugeints; finite extreme ratio/log behavior;
input immutability and JSONfinite outputs. Exact analytical fixtures validate
formulas rather than mirroring implementation. No episode/model/primary-source
completion is inferred from a passing pure-calculator suite.
