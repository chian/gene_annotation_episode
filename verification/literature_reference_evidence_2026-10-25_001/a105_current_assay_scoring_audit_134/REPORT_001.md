# Current A105 scientific-component audit134

This is a bounded implementation audit, not a replacement goal, amendment,
scoring policy or completion declaration. Only new files in this directory were
written. No paper, retained paper-specific source packet, primary run, original
test, production source or historical result was changed or scientifically
reinterpreted. The fixed goal and current user direction require A105 adequacy
before continuing A106. Prior completion cannot be inferred from an API count.

## Definite current missing path

The current native kinetic operation exposes only five of nine implemented pure
calculator components. `literature_kinetic_storage.py` sets
`COMPONENTS=ALL_COMPONENTS[:5]`, `MODEL_CAPABILITY='unimplemented'` and
`MODEL_INPUT_STATUS='not_supplied_by_native_operation'`. Its actual `populate`
calls `populate_kinetic_contrast(extraction['calculation_inputs'])` without the
optional model. The selected argument schema has no model/covariance source
argument. Its typed return cannot select any of the four model-dependent cells.
The existing episode catalog and fact-source meaning also explicitly describe
this limitation. This is unfinished implementation, not proof a paper lacks
uncertainty or covariance.

The four unavailable-to-the-episode components are:

- `log_contrast_variance` = Cnn+Cdd-2*Cnd.
- `log_contrast_standard_uncertainty` = sqrt(Cnn+Cdd-2*Cnd).
- `source_profile_log_ratio` = e*abs(e)/(2*V).
- `source_signed_index` = tanh(S/2).

The pure calculator already implements these expressions. The last two are
conditional signed evidence for the parameter contrast, not calibrated function
probabilities, assay-validity probabilities or extra independent experiments.
Higher Km is not automatically stronger function; the declared contrast means
numerator parameter exceeds denominator parameter.

## Actual synthetic illustration

`kinetic_model_gap_probe.py` was executed against the current implementation.
Its retained input/output is `KINETIC_MODEL_GAP_PROBE_001.json`. This is constructed
engineering evidence, not paper findings or an actual-model literature run.

Two separately assayed substrates of the same synthetic molecule/construct have
declared common conditions and catalytic efficiencies 12 and 3 uM^-1 min^-1.
The supplied synthetic covariance of their natural-log estimates is
[[0.09,0.02],[0.02,0.16]], with declared known-normal means.

| Component | Existing pure-calculator result | Current native selected path |
|---|---:|---|
| Parameter difference | 9 uM^-1 min^-1 | Exposed |
| Parameter ratio | 4 | Exposed |
| Log contrast e | 1.3862943611198906 | Exposed |
| Log contrast variance V | 0.21 | Not exposed; no model reader |
| Log contrast SE | 0.458257569495584 | Not exposed; no model reader |
| Signed profile S | 4.575742989697156 | Not exposed; no model reader |
| Proposed signed index | 0.9796126727409161 | Not exposed; no model reader |

Marking the same covariance estimated preserves V and SE, while the existing
known-normal profile/index remain unavailable with
`known_log_covariance_required`. That is a limit of this particular statistic,
not a ban on estimated-variance inference. Native reported SD/SEM/counts do not
themselves supply log covariance or independent preparations.

## Existing model contract to preserve

`literature_kinetic_calculations.py` validates this exact closed model:

- version `a105_kinetic_log_model_v1`.
- measurement_order exactly numerator, denominator.
- measurement_keys exactly `kinetic_operand_keys(inputs)` in that order. Keys
  derive from the full canonical operands; known/estimated variance requires
  non-null actual physical measurement identities. Different keys do not prove
  independent fits or preparations.
- 2x2 finite symmetric positive-semidefinite covariance, in
  `natural_log_canonical_parameter` basis. Variance status remains known,
  estimated or unknown; it is not inferred from fit spread.
- observation model known_normal_log_parameters or unspecified, and explicit
  source witness/origin. Model selection is an interpreted condition.
- The existing statistical score additionally requires exact positive
  uncensored point estimates, an applicable known model and V>0. Native partial
  quantities survive absent/unavailable models.

No new formula, threshold, prior, eligibility gate or universal reliability
transform is needed to connect this already defined finite statistical path.

## Finite repair proposal

Preserve the existing v2 native operation, original five-cell returns and frozen
saved results. Add a separate kinetic-model operation, following the existing
binding-model pattern, that receives an actually received committed native
kinetic sheet plus an authorized retained covariance/model source. Read that
source deterministically; authenticate the measurement order, canonical operand
keys, physical owners, log basis, source/origin and covariance. Use the original
saved `extraction.calculation_inputs` with the existing optional-model calculator.
Persist a new versioned model sheet and original request/outcome. A separate
closed typed return exposes the four missing model-dependent cells, their actual
parameter contrast, uncertainty basis/model qualifications and dependencies.

Explicit source receipt/scope is necessary: a globally known sheet ID or
covariance source ID is not possession. Saved return/reconstruction must validate
the original stored calculation and admitted subset without reopening the paper,
reparsing the model source, recalculating the statistic or adding observations.
Returned native/log/profile/index views are dependent representations of the
same two source estimates. The new operation is not another assay-specific
grader or new independent evidence.

Verification should cover a real selected ordinary LiteratureEpisodes action,
known and estimated covariance, absent model, wrong source owners/order/log
basis, shared physical fits, censored/approximate operands, exact selected typed
delivery, partial results, and source-free read-only reconstruction. A primary
case with applicable source/model information is separate scientific work; this
synthetic probe does not establish its existence or validate model applicability.

## Current scientific coverage matrix

Rows below identify actual experimental readouts/designs rather than operation
counts. Status applies only to the stated numerical contribution. Broader assay
adequacy, scientific validity and primary-source verification are not inferred
from these functions.

| Readout/design | Implemented contribution inspected | Missing or limited scientific scoring relationship |
|---|---|---|
| Corrected concentration-rate activity in a source preparation | Exact q-g contamination subtraction, recovery/molecule/condition correction `(q-g)*v/(k*E*u)`, full first-order covariance, conditional presence statistic | Scientific control roles and productive endpoint attribution are supplied interpretations; no general numerical consequence of coexistence/replacement or unmeasured coupling follows from the arrangement label. This formula applies only when its actual operands have the required meanings. |
| NADH absorbance depletion | Matched blank subtraction and extinction/path conversion to net NADH rate; known or estimated covariance propagation | Does not itself measure productive coupling, isolated claimed product formation, active molecule amount or overall reliability. A source-specific coupling/control relationship is additional scientific work. |
| Target/total mass estimates and nominal between-arm molecule amounts | Actual source quantities, differences/ratios, conditional reciprocal mass-denominator factor and propagated uncertainty | Explicitly no rate correction or amount-response model. A nominal amount ratio is not a calibrated comparison of functional output or effect isolation. |
| Separately assayed substrate kinetic estimates | Km/kcat/efficiency descriptive contrasts; pure log-covariance/statistic exists | Four numerical precision/evidence cells cannot currently enter through the selected native reader. Common-condition preference is distinct from comparison under differing reported protocols. |
| Ligand IC50 or reported Hill-fit Kd comparisons | Descriptive contrast and separately selected conditional log-covariance model, including its specified threshold-censor mechanism | IC50 and Hill-fit Kd are not intrinsic affinity. Fit equilibrium, nonspecific interaction and concentration/calibration validity remain experimental questions, not established by parameter magnitude or source custody. |
| Two molecular forms crossed with two ligands | Four actual source parameters, within-form ratios and interaction/log interaction; pure optional model/variance exists | Current native selected storage exposes eight descriptive cells, declares model reader unimplemented and calls the optional-model calculator without a model. Thus its four model-dependent cells have the same integration gap as kinetics. This was inspected, not synthetically reproduced here. |
| Same-curve substrate-response correction | Conditional Michaelis-Menten saturations, response factor and covariance with shared Km once | Supplies a correction operand, not transport-assay reliability. Flux versus accumulation, passive leakage, driving force/coupling and actual common-curve applicability need assay-specific evidence. |
| Gel mobility-shift/competition display | Background-corrected shifted/free darkness, display fractions, baseline/competition contrasts and explicit ROI sensitivity/dependence | Calculator explicitly returns comparability/effect isolation as not established by display arithmetic. No detector-to-molecule calibration, molecular occupancy, sampling uncertainty or binding likelihood is supplied. Source-specific competition controls can address specificity but image subtraction alone does not establish it. |
| Protein-present/control response across conditions | Current local calculator enforces endpoint, normalization, condition/control roles and physical ownership; calculates within-condition differences and covariance | Numeric effects are conditional on those interpreted relationships. No generic assay-validity probability or replacement/coexistence mixture model is established by these controls. Full four-arm/owner implementation was not independently reread by134. |
| Native/table endpoint rates, relative-signal percentages, single reported quantities and bar ordinates | Current selected catalog/fact contracts expose numerical measurements, contrasts, explicit missing/censored/conflicting meanings and finite model/calibration limitations | These are reusable measurement/component routes, not proof of distinct assay-specific reliability graders. Their full parser/repository implementations were not independently reaudited by134; no new completeness claim is made. |

This identifies genuine components already built and genuine missing scoring
relationships. It is neither a claim of zero implemented scientific arithmetic
nor a defensible final count of assay-specific graders. A105 remains incomplete.
In particular, connecting kinetic precision is useful but does not finish
functional specificity, method validity, numerical consequences of nuisance
differences, or cross-experiment complementarity/contradiction/dependence.

## Read and execution scope

Read the full fixed attachment, root/research AGENTS and W04 instructions.
Complete production reads covered activity calculator, assay inputs/storage,
kinetic calculator/storage, amount/optical/transport calculators, binding native
calculator/model, binding-interaction calculator/storage, gel calculator, and
controlled-response local calculator. Kinetic input schema/early reader paths,
synthetic kinetic test helpers and affected selected episode dispatch/fact-source
sections were read. Some early combined outputs truncated; key complete files
were reread separately; any remaining partial read is not claimed complete.
No nonexistent kinetic_prompt.py/render.py content was inferred from failed cat
calls.134 did not inspect the complete shared loop, every source parser, every
saved validator or every existing test. The parent independently owns broader
execution/architecture and primary-case review.

One new synthetic probe ran successfully. No broad pytest suite, model call,
network request, paper acquisition, scientific reanalysis, live database or
controller was run. Source fingerprints are in `READ_FINGERPRINTS_001.json`.
