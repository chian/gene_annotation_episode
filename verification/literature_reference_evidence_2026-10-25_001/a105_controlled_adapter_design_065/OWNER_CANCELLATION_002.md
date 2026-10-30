# Additive002: cancel one actual owner without choosing its representation

Root proposed this alternative after001: A10, C8, shared control B rendered as
printed4 and graph4.05 with conditional bounds[3.95,4.15]. The representations
have matching source-backed underlying reference context and a stated shared
invariance application. This is a synthetic contract example, not a paper.

The preferred path first separates experimental meanings from source readings,
then performs physical-owner dependence algebra. It does not need to select a
preferred B reading to compute e when B's net coefficient is0.

|Requested component|Retained representation-specific result|Meaning|
|---|---|---|
|P1 raw|10|Reported point for owner A|
|E1 raw|4|Reported point for owner B|
|P0 raw|8|Reported point for owner C|
|E0 raw|4.05,[3.95,4.15]|Graphical representation of the SAME owner B|
|d1|6|10 minus the printed4 rendering|
|d0|3.95,[3.85,4.05]|8 minus the graphical rendering|
|e|2|A-B-C+B=A-C, independent of the B reading|

Do not compute e by subtracting the rendered d0 from d1; these local summaries
have different representation errors of the same control. The cross effect is
a direct owner-level linear expression. Canceled graph uncertainty is retained
with its raw/local results but contributes no numerical width to this contrast.
This is dependence algebra, not a precision gain from independent evidence.

## Minimal explicitly versioned contract change

Keep controlled_response_inputs_v1 and controlled_response_sheet_v1 unchanged.
Propose controlled_response_owner_inputs_v2 and controlled_response_owner_sheet_v2
in NEW modules, with one authoritative source-reading/meaning implementation.
Input root retains version,arms,relationships,covariance,variance_status,model_kind
and adds exactly reading_relationships. Each role retains its original arm
fields. reading_relationships is an array of closed records:

    {physical_observation_id, roles,
     relation: same_physical_observation | unknown | conflicting,
     source_witness_refs, conditional_reading_domains}

The source reader constructs these records from retained authenticated meanings;
they are parsed calculator inputs, never selected numerical evidence or model
handwritten matrices. source_witness_refs refer to exact retained extraction
witness identities. conditional_reading_domains name the retained graph/text
reading records rather than duplicate or rewrite their numbers. A complete
declaration must define those namespaces and validate the source-record linkage
before coding. This document is a concrete proposed delta, not a released schema.

The new calculator separates:

1. Scientific applicability: compatible actual endpoint/normalization/unit
   dimensions, protein/empty arrangements, intended factor/conditions, actual
   control applicability/invariance, subject correspondence and physical-owner
   meanings. These conditions do NOT disappear just because a coefficient is0.
2. The role coefficient vector c=[1,-1,-1,1] and source-owned groups. Only known
   same-owner relations can form a group. Unknown owner roles remain separate;
   equal labels/values, a shared image or repeated reading IDs do not establish
   physical identity. Conflicting owner interpretations leave cross-e unknown.
3. Numerical reading requirements for ACTIVE groups after coefficients sum.
   A group with coefficient0 requires no chosen scalar or common digitization
   interval. Keep its source alternatives, graph assumptions and any source
   conflicts as qualifications. They do not create an artificial B value.
4. For nonzero groups, use consistent canonical readings or an explicit accepted
   reading model/reconciliation. Do not select a favorable sign/size or average
   source representations. Point/domain options001 remain alternatives here.

The distinction between same-owner context and reading difference must be typed:
different scientific context or unresolved reference applicability can invalidate
the comparison; compatible graphical tolerance versus printed rounding is not
that contradiction. A real reported-value conflict must remain visible even
when canceled algebraically. Root must settle whether such a conflict challenges
the established owner relation in each concrete case; infrastructure cannot
resolve an ambiguous owner by ignoring the conflict. Once owner identity and
scientific applicability genuinely hold, the canceled reading is not a numeric
operand of e. No blanket policy can equate tolerance agreement with proven
biological identity.

## Covariance cancellation without inventing control precision

For source owner order[A,B,C], consider the constructed full covariance

    [[1,   0.05, 0.10],
     [0.05,0.16, 0.02],
     [0.10,0.02, 0.25]]

Its role projection uses[A,B,C,B]. The owner coefficient vector is[1,0,-1],
so V=C_AA+C_CC-2*C_AC=1+0.25-0.20=1.05. Every B variance/cross term cancels.
Keep and validate the entire original full-N source matrix, exact labels/tokens,
PSD and owner relationships before any projection; this example has N3. The
larger065 fixture has N6 projected into the same four fixed roles. No independent
control-copy variance and no C derived from digitization tolerance is allowed.

If a full matrix was supplied but invalid, retain its actual invalidity and all
raw/local facts; do not silently declare its active submatrix authoritative.
If genuine source covariance support for active owners alone is supplied, its
scope can support the reduced contrast without inventing B precision. This
requires the separately versioned covariance projection contract: current006
requires four role units/owners and rejects a mixed-reading alias first. Missing
active C leaves V unavailable while e can remain2. Known versus estimated C and
requested/source/effective model remain separate. Whether the reduced A/C-only
source model supports normal S/B requires explicit dependency-scoped eligibility;
the current006 all-arm graph restriction cannot silently be removed.

## Why an adapter-only patch is insufficient

Current006 _effect_reasons first unions both local pair-data reasons, then
_common_alias_reasons rejects relation/approximation/interval differences. Its
_validate_covariance also calls _alias_reasons before any cell is populated.
Changing only input values, clearing B's owner ID or copying one B rendering
would lose meaning, dependence or provenance. The minimal proper new calculator
keeps original raw roles/local pairs, separates scientific/reading reasons,
groups known owners before cross numerical requirements, and evaluates original
owner coefficients/covariance. It must not claim e=d1-d0 using independently
rounded representation-specific summaries.

The saved validator must reconstruct owner groups, coefficient sums, applicability
and active reading/covariance dependencies from the retained original request,
source/reading records and operator definition. It must preserve local results,
canceled alternatives and exact active-source scope without rereading images or
selecting a new representation. Typed derived cells need the cancellation and
scientific qualifications, not unrequested B numbers. Parent admission still
copies only the requested components. No helper adds an observation or changes
W05 annotation aggregation.

Root already executed the unchanged006 counterexample in
controlled_adapter_parent_review_065/probe_shared_representations_001.py, with
results in shared_representation_probe_001/RESULT_001.json.065 read that complete
script and inspected its relevant actual result fields; it does not rerun the
same probe. Root's covariance is a different synthetic example: A/C variance0.25,
covariance0.10 and Bvariance0.04 give V0.30(nmol/min)^2=3e-7(umol/min)^2; B cancels.
The matrix above separately illustrates nonzero A/B and B/C cross terms also
canceling. Neither example implements this proposed new calculator. Complete
closed input/output schemas and a dedicated release remain necessary before coding.
