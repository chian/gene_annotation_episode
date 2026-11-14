# A105 selected correction-input availability repair

This is an implementation and verification record for the bounded 156 repair.
It does not replace or amend the original user-supplied goal. The parent retained
scientific-route and primary-source work; this workload used synthetic inputs.

Absent selected operands were previously returned as `*_unreported`, although
the operation contracts do not assess publication-level absence. Prospective
population now says precisely that the required calculation inputs were not
supplied. No source-absence assessment was added.

| Missing calculation input | Prospective unavailable reason |
| --- | --- |
| Any of q, g, k, E, u, v | `correction_inputs_not_supplied` |
| Complete primitive covariance | `primitive_covariance_not_supplied` |
| Distinct residual variance | `distinct_residual_variance_not_supplied` |

The existing dependency order remains: missing effect operands qualify all
dependent cells; covariance and residual-variance availability are considered
after a calculable effect. The assay adapter's q−g and u/v cells use the first
reason when their selected operands are null. Primitive source-value cells keep
the existing general `source_measurement_unavailable` reason.

The calculator publishes `a105_corrected_activity_v2`. Assay and quantity writers
publish `literature_assay_population_record_v2` and
`literature_source_quantity_record_v2`. Formulas, arithmetic, input schemas,
operand ownership, cell roster, units and uncertainty assumptions remain as
before. Both existing return schemas gain only the three finite reason values;
all legacy enum reasons remain valid. Original saved caller schemas are retained
as supplied: a caller whose original schema excludes the new reasons does not
silently acquire them.

The source-quantity adapter still cannot populate the correction primitives from
a reported normalized activity alone. It now accurately returns a missing-input
reason rather than a publication omission. The existing different-quantity
qualification remains applicable for apparent Km.

For the complete synthetic correction fixture,
q=1, g=0.15, k=1, E=1, u=2, v=1.6 gives corrected activity
(1−0.15)×1.6/(1×1×2)=0.68 per minute. Omitting the selected covariance preserves
0.68 while leaving variance and dependent statistics unknown with
`primitive_covariance_not_supplied`. Omitting the selected residual variance
instead yields `distinct_residual_variance_not_supplied`. The original synthetic
source text and covariance packet remain received in these omission tests;
therefore the tests distinguish an absent selection from an absent report.

The investigating child continues to select and interpret its operands. The
reader verifies the existing source witnesses, units and physical owners. The
calculator populates numerical cells. The adapter persists the result and the
ordinary typed boundary validates exactly the requested saved cells. This repair
adds no source reading, model call, action selection, controller decision,
additional observation or annotation-credit calculation.

Historical compatibility is explicit. Assay and quantity declare exactly their
v1/v2 readable record versions. The shared reader otherwise retains a singleton
current-version check. For the two explicitly versioned adapters, saved source
metadata and payload versions must agree. Unsupported versions are rejected.
Reading or operation-key replay returns the original payload, cells, identities
and outcomes; it does not upgrade a v1 record or call the revised calculator.

`legacy_v1/assay` and `legacy_v1/quantity` contain actual selected synthetic v1
operations created before the production edits. Adjacent JSON manifests retain
their original payloads, outcomes, caller schemas, admitted subsets and executable
binding descriptors. Regression checks copy these fixtures, forbid original
scientific artifact access and parser/calculator calls, and verify exact v1
projection, admission and replay, including read-only replay. The pre-change
executable descriptors intentionally fail the existing byte-identity check under
changed code. Compatibility of stored scientific returns does not authorize
running a different implementation under an old execution descriptor.

The shared reader change affects a dependency hash pinned by native binding
interaction storage. Its own read, population and projection override the changed
base methods; inherited custody and receipt methods remain identical. The
reviewed compatibility update permits the exact new base hash and accepts only
three complete dependency snapshots: original140, genuine previous142 and the
current implementation. The prior142 map is authenticated against untouched
`a105_primary_active_site_review_151/pin_001`; the original140 map retains its
existing untouched runtime. Unknown actual bytes and mixed historical maps are
rejected. Saved dependency maps are not rewritten.

`base_method_comparison.json` records the prior/current hashes and AST method
comparison. `base_read_change.diff` contains the exact changed base method.
Compared with the prior142 base, only `read` changes; there are no added or
removed base methods. The prior base SHA-256 is
`66f7b53adfb4fd873386fd04a3bff681c871f29a69848e94567c1792420be541`;
the repaired base SHA-256 is
`97d5a4e2bdfe5b3ed7bc106bf9b01ffd949563097a7a1da675b6954386b02621`.

Complete affected implementations were inspected: activity calculations, assay
inputs/storage, quantity storage, shared rate storage and LiteratureEpisodes.
The quantity-consuming transport storage, service repository binding,
episode-composition reconstruction and native binding-interaction storage were
also read. The investigation prompts, input reader, LiteratureEpisodes and
composition/fingerprint checks were not edited. No scientific paper packet,
provider conversation, model request/response or private log was read.

These checks establish availability semantics and bounded compatibility. They
do not validate scientific operand interpretation, the activity-correction model
for a particular experiment, a source-absence inference, or complete A105 assay
coverage. They are synthetic engineering checks, not new primary-source evidence
or configured-model scientific execution. W05 credit aggregation and episode
continuation remain outside this repair.
