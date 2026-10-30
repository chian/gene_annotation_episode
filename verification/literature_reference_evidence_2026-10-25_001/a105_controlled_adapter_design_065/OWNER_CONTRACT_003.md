# Exact first pure owner-calculator tranche003

This supersedes002's proposed reading_relationships/source_witness_refs addition
to the PURE input. Existing interpreted arm physical_observation_id,
meaning_statuses and source_observation_id already identify physical owners and
their readings. Source witnesses stay in the source reader/saved-source layer.
No duplicate pure assertion of same/unknown/conflicting ownership is needed.

OWNER_INPUT_SCHEMA_003.json and OWNER_OUTPUT_SCHEMA_003.json are complete CLOSED
JSON Schemas for this tranche. Dependent scientific/numerical invariants below
are required in addition to schema validation. No implementation is released.

New production ownership, if separately released, is ONLY:

- NEW gene_annotation_episode/literature_controlled_response_owner_calculations.py
- NEW tests/test_literature_controlled_response_owner_calculations.py
- One new owned verification directory.

No existing006/source/graph/runtime file changes. Public API:

    controlled_response_owner_arguments_schema() -> detached CLOSED schema
    validate_controlled_response_owner_inputs(inputs) -> detached parsed inputs
    populate_controlled_response_owner(inputs) -> CLOSED owner sheet

The input is already parsed, scientifically interpreted host data, not a native
model-selected operation. Source extraction remains separately owned. Numeric
constants are supplied only by actual readers or explicitly synthetic fixtures.

## Exact input delta and covariance representations

Version is controlled_response_owner_inputs_v2. Root still has exactly version,
arms,relationships,covariance,variance_status,model_kind. All four fixed role
arms and scientific relationship fields retain006 shapes/enums/meanings. There
is no new witness namespace or free-form interpretation field.

covariance is null, the original closed RoleCovariance over all4 roles, OR the
new closed OwnerCovariance with exactly physical_observation_ids,units,matrix.
OwnerCovariance has1..4 unique known owner IDs, one supported unit per owner and
a full NxN finite numeric matrix over those PROVIDED owners. It may cover only
active owners, e.g.[A,C], with no B row/column invented. This N is at most four
participating physical owners, not extra experimental arms. The source reader
still retains and validates its full original source matrix/label roster before
building this projection. The pure input does not consume original papers.

Null C requires variance_status=unknown; supplied C requires known or estimated.
Every provided covariance owner must match an actually known arm owner. Repeated
owners in RoleCovariance require equal normalized rows/columns and compatible
scientific contexts; their differently rendered numerical readings are NOT a
covariance validation failure. OwnerCovariance uses unique owners and needs no
duplicate rows. Both matrix unit factors apply. Any provided unit dimension
incompatible with its known arm/scientific endpoint remains a binding failure.

Validate the ENTIRE supplied matrix for finite values, exact symmetry and PSD,
including canceled/unneeded rows. A bad full matrix is invalid; do not rescue its
favorable active submatrix. A legitimately provided smaller owner matrix is a
different explicit input shape/scope, not a fabricated repair of bad full C.
Missing active owner coverage leaves V/SE/precision/model unavailable with
incomplete_active_covariance, while retaining a valid effect. No zero covariance
or independence is supplied for omitted owners.

## Owner dependence and scientific versus numeric requirements

For e use c=[1,-1,-1,1] in the declared four-role order. Group ONLY actually known
identical physical_observation_id values. Unknown-owner roles remain separate;
equal numerical/source labels, image or observation IDs do not establish owner
identity. Known source_observation_id assigned to two distinct known owners is
a source-owner binding conflict. An explicit conflicting physical-owner meaning
blocks e; it does not supply an arbitrary group.

Each group retains all original roles and source readings. Its coefficient is
the exact sum of role coefficients. A known group with coefficient0 is canceled.
No preferred reading, average, intersection midpoint or count is manufactured.

Scientific applicability requirements remain for ALL four present arms:
source-backed endpoint/normalization correspondence, protein/control arrangement,
actual condition targets, applicability/invariance, intended-factor distinction
and subject/construct correspondence. A known incompatible scientific context,
known incompatible unit dimension or contradictory source-owner binding blocks
the controlled contrast. Unknown owner or actual unresolved reference
applicability cannot be waived by saying a value cancels. Whole arm=None lacks
the scientific arm information and blocks that contrast.

A PRESENT canceled arm can have unreadable/missing/unsupported/ambiguous numeric
reading, null scalar, null digitization interval and null unit. Those are unused
numeric operands; they do NOT become additional scientific gates when owner,
endpoint/normalization and actual control applicability are genuinely established.
Missing canceled unit differs from an EXPLICIT incompatible dimension. Known
units are checked against the common active dimension; a null canceled unit is
retained with canceled_unit_unknown and is not inferred or used to convert its
unneeded scalar. Local pairs may remain unavailable while e=A-C remains valid.
Missing/unknown ACTIVE units/readings remain necessary numerical dependencies.

Canceled source readings with usable known-unit domains are compared only for
actual incompatibilities. A printed point inside a graphical conditional domain
is compatible; the range is not a sampling CI. Exact reported points that
disagree or provably disjoint known-unit domains are retained as source-reading
conflicts and block e in this first explicit contract. Missing unit/conversion
does not create a false numeric contradiction. A canceled arm already marked
conflicting blocks e; missing/ambiguous/unsupported alone can be bypassed with
qualifications, not silently reclassified as a numerical observation. The episode
continues to own whether an apparent source conflict challenges owner identity.

For ACTIVE groups, a sole reading or exactly equivalent normalized readings
can be used. Compatible but distinct active graph/text readings require an
explicit reading model/reconciliation and return unresolved_active_reading_model
in this FIRST tranche. The source-stage integration must later implement that
remaining requirement; do not call this limitation the full intended final state.

Raw response and each local pair preserve their original006 reading-dependent
calculation and qualifications. Compute e directly from its original owner
expression, never by subtracting independently rendered d1 and d0. Reuse006's
exact rational range/cell primitives read-only where useful, but do not call its
entire sheet populator on dummy/modified scientific values and discard results.
Keep original inputs in the new sheet, including all canceled reading alternatives.

## Dependency-scoped covariance and optional model

For valid effect semantics, let g be active owner coefficients, and C the actual
provided matrix reduced/reordered to those owners. V=g C g^T. Canceled B precision
and its cross terms are not needed. If supplied they were validated above;
if genuinely absent they stay absent. Numeric C is never obtained from graph
digitization bounds, SD/count or an independence default. Unknown active physical
owners prevent a source-owned joint-C model but do not make equal values aliases.

SE=sqrt(V), precision=1/V use the existing exact/range/positive-V restrictions.
Known/estimated C remain distinct. Optional signed normal S=e*abs(e)/(2V),
B=tanh(S/2), requires a valid point effect, positive known V, the explicitly
selected supported joint-normal source-means model, and exact uncensored
non-graph/non-approximate readings for ACTIVE owners. Canceled graph/error/limit
readings remain visible but do not become active reading-model inputs. This
dependency-scoped eligibility is an explicit v2 semantic delta, never an
unannounced change to006's all-arm restriction. Actual source support and its
scope must still be established by the reader; pure arithmetic cannot infer it.

Derived e/V approximation, numeric origin and bound kind refer to active numeric
dependencies. Preserve canceled_graph_reading/canceled_reading_unavailable and
owner_cancellation as separate conditional qualifications; do not misleadingly
assign nonzero digitization width to a canceled term. Synthetic active inputs
remain labeled synthetic. Raw/local origins and uncertainty remain unchanged.

## Exact output and detached consistency

Output has exactly version,primitive_order,inputs,cells,contrast_dependencies.
Version is controlled_response_owner_sheet_v2. cells has the SAME12 component
names and all006 CELL_FIELDS, with declared additional reasons/qualifications.
contrast_dependencies exposes the exact original coefficient order/vector,
known owner groups, active/canceled role sets, scientific reasons, active reading
reasons, canceled qualifications, conflict roles, covariance owner coverage/state
and model-active roles. It contains no narrative interpretation or invented score.
Schemas close every nested field; meaningful invariants must match original inputs.

An eventual source saved-validator reconstructs this dependence record from the
original authenticated science/reading records, and compares original selected
operation, request, payload, output cells and expected dependencies. A pure
validator alone grants no source custody. It must not read a paper/image, select
a replacement canonical reading, call another model or manufacture an observation.

## Required first-tranche fixtures and limits

- A10,C8,B text4 and graph4.05[3.95,4.15], same established owner/reference:
  raw/local cells stay as rendered; e=2 rather than null or2.05. With root's
  active A/C covariance, V=0.30(nmol/min)^2=3e-7(umol/min)^2.
- Both B numeric readings missing but present known scientific arms, unit known:
  local pairs unavailable; e=2. Also test BOTH canceled units null: e still2
  with qualification. No B number/unit/covariance is invented.
- OwnerCovariance[A,C] supports V without B. Full supplied matrix with invalid
  B diagonal rejects as invalid, even though B cancels.
- Unknown B owner, whole B arm absent, explicit incompatible B endpoint/
  normalization/dimension, and unsupported invariance block the appropriate
  cross comparison. Raw and independently valid local results survive.
- Disjoint known-unit readings/contradictory source-owner IDs block. Mere
  compatible graph tolerance does not. Active unresolved mixed representations
  remain explicit required follow-up, not an adopted null-only final workflow.
- Graph A or C still blocks normal S/B. Canceled graph B alone does not after
  source model/active C/positive V are established. Known versus estimated,
  zero V, reported limits, source numeric range and unknown active covariance
  stay distinguishable.

These pure contracts are implementable independently after review. They do not
constitute a source reader, shared-stage refactor, native repository, typed/C4
integration or real model-backed evidence. Those remain the complete objective.
