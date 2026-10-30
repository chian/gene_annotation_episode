# Pure product/cofactor numerical component handoff

This implements one source-paired product/cofactor component operation for A105.
Its eleven numerical cells are views/components, not eleven assay graders. It
does not establish complete A105 coverage, reliability/validity/attribution
compilation, annotation probability, annotation-credit policy or adequacy of
another evidence axis. There is no complex computational biology software.

## New files and separate responsibilities

- `gene_annotation_episode/literature_product_coupling_prompt.py` contains the
  exact reviewed six-paragraph TASK from the parent's 211 proposal.
- `gene_annotation_episode/literature_product_coupling_inputs.py` defines closed
  population/extraction formats and a source reader. The caller supplies its
  actually received source callback. Numeric fields are selected source spans;
  scientific interpretations and the stoichiometric model require witnesses.
- `gene_annotation_episode/literature_product_coupling_calculations.py` defines
  the numerical sheet and its deterministic population operation. It uses no
  source IO, model, persistence, receipt admission or annotation-credit function.
- `tests/test_literature_product_coupling_212.py` exercises original source cases
  and explicit synthetic contrasts. No selected episode or model was run.

Only these four new files and this new 212 artifact directory were written.
Existing 205, 209 integration, runtime, registration, storage, render, controller,
goal, amendment, W05 and other-axis files were not changed by this workload.
The original supplied goal remains authoritative. No repository goal was read.

## Supported numerical meaning

Native product and cofactor activity and reported coupling remain separate.
The descriptive ratio rho=P/H, productive fraction
eta=nu_cofactor_per_product*P/H, percent display and displayed-rate versus
reported-percent discrepancy are explicit. The direction of nu matters; no
global nu=1 default exists. The paper's nu=1 is a witnessed interpreted
reaction-account convention, supported by chemistry and the explicit Table 3
footnote balance, not a source-printed measured scalar or a parameter fitted to
the reported coupling percentage. Model identity is retained in contributions.

Unknown nu without a supplied estimate gives no eta. Unknown detailed assay
matching gives a conditional eta; known incompatible or contradictory pairing
gives none. Explicit conflicting quantity normalization also blocks eta.
Native and descriptive partials survive. A supplied uncertain nu estimate gives
conditional fixed-substitution point arithmetic; its variance/covariance
propagation remains unimplemented and the conditional fixed-nu variance is not
total eta uncertainty. Values outside [0,1] are retained with an explicit
unconstrained-estimate qualification and are not clamped.

Source ND, negligible activity, bounds, approximations, ranges, nonfinite tokens
and unsupported genuine units preserve native observations and precise
unsupported reasons. Printed zero with nondetection does not imply exact
physical absence. Clipped numbers, wrong source columns, incompatible explicit
units, markup selections and quote mismatches are repair failures. Exact
Fractions survive finite-float projection limits, including matching 1e400 or
1e-400 operands whose ratio remains one.

An explicitly supplied owned joint 2x2 covariance of the selected estimates
supports first-order J Sigma J-transpose ratio variance and fixed-nu variance
and standard uncertainty. Both covariance offdiagonal entries are required;
none defaults to zero. Ordered owners, canonical units, estimate basis,
known/estimated/unknown status, finite entries, symmetry and positive
semidefiniteness are checked. JSON decimal numbers and explicit decimal strings
are retained exactly. Raw SD, CV, counts or unrelated estimates are not treated
as the required covariance. Invalid or missing covariance leaves point cells
intact with an uncertainty-specific reason. Synthetic covariance origin remains
synthetic even when the selected source rates are reported primary values.

Same-operand rho*H reconstruction aliases the original product contribution.
Ratio, eta, percentage, uncertainty displays and reconstruction are dependent
views. Representation/reference aliases of identical content-addressed bytes
at identical coordinates cannot manufacture distinct conflicting witnesses,
physical measurements or stoichiometric model identities. Equal numbers in
different cells remain separate source spans without any independence claim.

## Source examples and verification

Four `SOURCE_POPULATED_*_001.json` examples contain exact selected inputs and
the populated sheet for original Table 3 WT, T252N, T252N/V253T and T252A.
Positive rho values come from 206/289, 92/216 and 132/343. Reported percentages
71,42,38 remain distinct. Detailed preparation/normalization/window linkage is
unknown, so physical eta remains conditional. T252A native product 0 and NADH
427 retain nondetection/negligible semantics and no physical point ratio.
No Table 3 covariance is invented or borrowed from Table 2/Figure 5.

`SOURCE_NUMERICAL_ORACLES_001.json` records separately hand-transcribed Decimal
oracles and the mutant/WT identity
92/206=(216/289)*((92/216)/(206/289)). The tests additionally verify covariance
by directional finite differences from two supplied error modes rather than
only mirroring the production matrix expression. `SOURCE_WITNESS_PROOF_001.json`
records all 128 enriched witness occurrences checked against original bytes.

`test_run_001.log` preserves the initial engineering failure: its alias fixture
selected the product number/label but retained a cofactor-column unit. The
corrected fixture selects the original product unit too; no column guard was
weakened. The next runs and final combined verification logs are retained.
`final_pure_and_dependency_002.log` also preserves an added test's insertion
mistake: part of the representation-alias test body was placed under the new
different-artifact test, causing a NameError. Moving it back corrected the test;
no production guard was changed for that failure.
Final test counts and exact production/dependency hashes are in
`RELEASE_MANIFEST_001.json`; this document makes no model/integration claim.

## Frozen dependencies and bounded grammar

`PROTECTED_DEPENDENCIES_001.json` captured existing scientific dependencies
before coding. `RELEASE_MANIFEST_001.json` contains the actual release hashes
and verifies those captured bytes remained equal. In particular, the new
reader imports private generic numeric/column/unit helpers from frozen
`literature_measurement_validation_inputs.py` (205),
`literature_partner_source_fields.py` and `literature_assay_inputs.py`.
Those private dependencies are prospective integration constraints: changes
require review of this reader and its source-boundary regression tests.

The supported grammar is selected UTF-8 text/XML/HTML with source-byte witnesses
and bounded numeric/unit/table-column recognition. This is not a general PDF,
OCR, gel, image-axis or arbitrary-graph interpreter. Structural validation of
retained arithmetic does not authenticate a previously saved artifact against
the original paper. Any future storage/replay path needs its separate source
authentication and structural reconstruction; it must not silently re-run this
numerical population operation during loading.

## Explicit remaining scope

No shared integration, operation registration, storage/fact admission,
model-facing selected call, rendered parent return, configured run, controller
credit or final annotation aggregation was implemented or tested. Cross-arm
uncertainty is explicitly unimplemented; the handoff only demonstrates the
single-arm decomposition without fabricating a separate assay count. Full
uncertain-nu joint propagation is unimplemented. Complete literature assay
coverage and quality compilation remain unfinished.

The original Figure 4 label conflict (image T252N/V253N versus text/table
T252N/V253T) is retained in the oracle artifact as a previously actually viewed
case qualification. This bounded reader does not extract image-internal text,
assign that panel silently or digitize its peak into a rate. No quantitative
no-P450 blank, active fraction, shared aliquot or independent repetition is
invented. Chemically identified product, NADH loss and peroxide answer different
questions; inferred water is not independent mass-balance validation, and
product identity alone does not establish protein-specific causality.
