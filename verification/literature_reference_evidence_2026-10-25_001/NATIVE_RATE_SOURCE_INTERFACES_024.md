# Workload 024: native source inputs for the existing rate sheet

## Purpose and ownership

The existing rate sheet has ten numerical components and a working retained
CSV/TSV route. It lacks direct selected-source operands. Implement that missing
input path to the same sheet; do not create a new evidence axis, statistical
index, annotation score, mandatory workflow or target-transfer calculation.

A fresh coding owner must first inspect complete affected paths and propose
the exact input/extraction/persistence interface to the parent. Resolve this
engineering interface before editing shared production files. This is design
coordination, not a runtime approval step or a new scientific gate.

The coding owner may edit only:

- New `gene_annotation_episode/literature_rate_native_inputs.py`.
- `gene_annotation_episode/literature_experimental_contracts.py`.
- `gene_annotation_episode/literature_rate_calculations.py`.
- `gene_annotation_episode/literature_rate_storage.py`.
- `gene_annotation_episode/literature_episodes.py` (only native rate declaration,
  dispatch and implementation fingerprint additions after interface agreement).
- New focused native-rate tests with distinct names.
- New artifacts under `native_rate_source_024/` in this verification directory.

No other owner is changing these files. The current 631-file 023 snapshot and
all running investigations are immutable. Do not copy unrelated worktree
changes into a runtime snapshot.

## Existing numerical meanings to preserve

`reference_rate`, `test_rate`, `reference_rate-test_rate`,
`test_rate/reference_rate`, `1-test_rate/reference_rate`, both mean standard
errors, their difference standard error, conditional signed profile log ratio
and the explicitly proposed signed index retain their current meanings,
formulas, units and assumptions. These are source-preparation endpoint
components, not isolated product formation or final annotation credit.

Concrete synthetic illustration of the required mapping: native source text
reports reference 12 nmol/min/mg and test 3 nmol/min/mg for the same stated
endpoint/normalization. The existing calculator should receive the literal
source numbers and return 0.012 and 0.003 umol/min/mg, difference 0.009,
retained fraction 0.25 and fractional decrease 0.75. With no uncertainty/model
information, uncertainty and profile cells remain unavailable with reasons.
These are synthetic values, not measurements from a paper.

## Required boundaries

- The model selects experimental meanings and exact source witnesses; numeric
  values, limits, spread magnitudes and counts must be parsed from source bytes.
  No prepared numeric dataset or model-authored scientific number is accepted.
- Preserve actual subject, preparation/experiment, arm, condition, endpoint,
  normalization, units, origin and source-bound identity. A verified quote proves
  custody, not that the selected passage establishes the claimed interpretation.
- Do not fabricate CSV row numbers for prose or construct an artificial received
  source merely to pass the retained-table eligibility checks. Use an explicit
  native provenance variant and preserve v1 table inputs/results exactly.
- Do not manufacture independent observations from two source representations.
  Physical measurement identity and byte-location identity are different facts.
- Retain partial inputs and censored observations; do not turn missing metadata
  into confident equal conditions, unknown quantities into zero, or limits into
  point contrasts. Propose explicit unknown behavior for missing meanings.
- Reuse deterministic witnessed-number/unit machinery only where its supported
  dimensions and lexical rules actually match the rate sheet. Never silently
  rescale across amount, concentration, turnover or protein-mass dimensions.
- Source-defined U requires its endpoint-specific source definition; either
  support that definition correctly or return a specific unsupported result.
  A universal U conversion is prohibited.
- Statistical assumptions remain explicit and source-supported. Untyped spread
  is not SEM/SD; count is not biological independence. The existing conditional
  model is not inferred from a source label or a repeat count.
- Original source scope/receipt eligibility, transactional operation identity,
  saved sheet replay, requested typed projections, received subsets and ordinary
  observations must be traced through the actual consumers.

## Verification and limits

Use synthetic sources, including contrasting arrangements, unit dimensions,
limits, partial numeric tokens, absent uncertainty, duplicate/contradictory
identity, interrupted/repeated operations, saved-only reopen and arbitrary
parent-selected field names. Preserve existing retained-table tests and original
outputs. Demonstrate actual shared-loop selected execution and one observation
per completed own action, with no numerical credit for extraction internals.

Do not acquire or interpret a primary paper, inspect private model/provider
history, launch another configured model, edit historical state or pins, change
controllers or global credit, or claim a completed axis. Existing primary-case
interpretation requires the separate full post-paper reset by its owner.

## Parent engineering reply to proposal 001

The parent read `native_rate_source_024/INTERFACE_PROPOSAL_001.md`. Proceed with
an explicit native extraction v2, preserved v1 inputs/results, the same existing
rate cells/provider, additive native missing-reason meanings and transactional
original-result replay. The new native operation may be appended after the
original 14 operations. Preserve every original entry and its relative order.

Additionally assign `tests/test_literature_parent_population_information.py`
only for additive new-operation checks. Preserve its historical 14-entry JSON
fixture and exact original-entry equality; do not rewrite the fixture to conceal
an unintended original-catalog change.

Support endpoint-defined U/mg in this workload through the existing actual
definition validator, converting its pmol/min/mg basis correctly into the rate
sheet's umol/min/mg basis. Do not edit the partner implementation. A generic
unsupported-unit placeholder is insufficient for this already exercised source
format. Other truly unsupported forms retain explicit partial results and
unfinished scope rather than invented factors.

Before shared edits, resolve two representation details in a concise addendum:

- Retain actual per-arm subjects, constructs and preparations when different.
  A deliberate construct/preparation change can be the comparison variable.
  Identical molecules or conditions cannot stand in for experimental
  comparability, and equal labels cannot establish common molecular identity.
  Do not flatten distinct subjects into an invented common subject merely to
  fit a singular existing binding. Raw endpoint contrast and causal effect
  isolation remain separate meanings.
- Unknown physical observation IDs do not veto an otherwise explicitly
  source-supported conditional independent-groups assumption. Unknown identity
  is unknown, not proof of dependence. Known reused byte/physical observations
  must prevent false independent-replicate claims. Measurement identity means
  the actual observation, not merely the preparation, protein or source paper.

This is implementation-interface coordination. It does not add a scientific
approval stage, require another user permission, or change runtime continuation.

The parent's subsequent reply approved the proposed addendum: native arms
retain nullable subject/construct/preparation witnesses, explicit source-backed
endpoint and normalization relations, and the intended-change witness. Raw pair
arithmetic requires the supported endpoint/basis relationships and compatible
dimensions; it does not require identical subjects or preparations.

Add optional native-only `reference_subject_ref`, `test_subject_ref`,
`reference_construct_ref`, `test_construct_ref`, `reference_preparation_ref`
and `test_preparation_ref` properties to the existing typed rate cells. Preserve
the v1 required set, emitted fields and results exactly. Native projection,
validation, admission, received subsets and saved reopen must carry these
bindings; they cannot exist only in the private sheet payload. Preserve the
shared assayed-subject binding only where explicitly supported as the same
subject. Verify meaningful provider text at both sides of the typed boundary;
report any necessary renderer ownership extension before editing that file.

The coding owner may now implement within these agreed interfaces. Its recorded
pre-change rate regression group passed 113 tests; those baseline checks are
not evidence that the new implementation has passed.

## Closed-return correction superseding the optional-field proposal

An actual storage/typed-form check rejected the optional native metadata with
`open_object`: this application's closed forms require every declared property.
The parent had approved optional fields before verifying that consumer. That
interface proposal is superseded; no shared communication relaxation is allowed.

Preserve the original `rate_cells_schema`, required set, unavailable-reason
enumeration and v1 emitted rows exactly. Add the distinct closed return source
`literature_rate_source_cells` for native v2 results, with all native per-arm
identity fields and the approximation flag required (nullable identities when
unknown). This is a return projection of the same numerical sheet and ten
components, calculator, provider and selected-operation table. It is not an
additional scoring sheet, axis or annotation-credit component.

The native return view may have its own received-subset table. Partition facts
by actual saved version, and validate/admit/forward/reopen through the matching
declared source. Native qualifications must never be silently stripped into the
legacy projection. The operation description identifies its actual return
source so the parent can choose a compatible requested form.

The ordinary own-action path must save a valid native result and its observation
before any later typed return mismatch. C7 fact collection runs after action
completion and must not reject useful intermediate native work. An attempted
incompatible numerical admission receives existing structured contract feedback
at `validate_received_report`, using only this child's original saved facts and
selected operations. A parent can explicitly select ordinary redelivery with
the appropriate native form. Do not rewrite the child history, duplicate credit,
leak unrequested values, impose a mandatory numerical family or alter continuation.
No numerical request, explicitly empty components and genuinely absent results
retain their ordinary semantics. Test both-family output selection separately.

The parent also assigned `literature_experimental_prompt.py` only to suppress
new generated `native_rate_` accessions alongside existing generated-accession
filtering. Preserve scientific labels/accessions and the full recurring TASK;
verify actual bootstrap/delta/reconstructed provider text carries requested
native per-arm bindings and approximation while omitting host bookkeeping.
