# A108 main evidence scoring sheet and numerical communication

Replacement design, 2026-11-05 UTC. The user approved the organism-physiology
example and directed the build. Its observation-count approach is implemented
in the purpose-specific subscoring sheets and main evidence scoring sheet.
Implementation and workflow validation remain separate; see
[the implementation record](A108_IMPLEMENTATION.md) for current execution status.

## Scientific starting point

Start with a proposed functional assertion and the actual target organism,
strain and sample context supplied or established through received evidence.
A gene name or proposed function cannot supply that organism identity.
Source observations must have an explicit relationship to that target context.
An unrelated assay mentioning the same chemical supplies no contextual score.

The Winter/ttrA figure comparison was removed: target-context applicability had
not been established. The preceding prose-only scoring plan was removed because
it omitted numerical scoring. Requiring every A108 source to supply an assay
likelihood model was also incorrect. The user's original A108 instruction
explicitly calls for literature-based assessment, including measurable
source-evidence terms; see the original quotes in the
[instruction audit](../runs/scoring_instruction_count_20261105/COUNT_AUDIT.md).

## Numerical meaning

The main evidence score measures the amount of distinct, assessed contextual
evidence. Supporting and conflicting observations remain separate. It is not
annotation probability, an arbitrary quality category, a fraction of required
conditions checked, or the episode's progress scalar.

The purpose-specific scientific criteria and readers are specified in
[A108_NUMERICAL_SUBSCORING_PLAN.md](A108_NUMERICAL_SUBSCORING_PLAN.md).
Each applicable subscoring grader assesses actual source observations against
the selected contextual claim. Numerical units are original biological
observations, not satisfied checklist items, search hits, citations, downloaded
records, repeated statements or newly created internal finding IDs.

A documented physiological property can supply evidence without extracting an
assay curve. Native measurements and statistics remain separate numerical
components when the actual contextual question calls for them. They are not
added to observation counts.

## Explicit arithmetic

For each domain d, define S_d as the set of original observations with assessed
supporting relations, C_d as the set with conflicting relations and U_d as the
set whose selected relationship remains unresolved. The domains are physiology,
environment, availability and localization.

```
support_count[d]    = |S_d|
conflict_count[d]   = |C_d|
overlap_count[d]    = |S_d intersect C_d|
evidence_amount[d]  = |S_d union C_d|
                   = support_count[d] + conflict_count[d] - overlap_count[d]
net_support[d]      = support_count[d] - conflict_count[d]
unresolved_count[d] = |U_d|

S = union of all S_d
C = union of all C_d
U = union of all U_d
overall_evidence_amount = |S union C|
overall_support_count = |S|
overall_conflict_count = |C|
overall_overlap_count = |S intersect C|
overall_net_support = |S| - |C|
overall_unresolved_count = |U|
```

One observation may support one relation and conflict with another. It then
belongs to both sets but contributes once to evidence amount. A narrower
relationship may be established while a broader one remains unresolved.
Unresolved counts are not added to assessed evidence amount. Net support is
separate, so cancellation cannot erase the amount of assessed evidence.

The main sheet recomputes these unions from authenticated admitted observation
identities. It must not sum child totals and thereby count shared observations
again. There are no normalization weights, maxima, arbitrary score bounds or
coverage denominators. Uninvestigated domains are not negative evidence.

## Identity, applicability and source qualifications

Preserve original study/record identity, observation or contrast, studied
subject, endpoint, conditions and original measurement identifiers. Different
citations, source IDs and repeated representations do not make new observations.
Several publications repeating one known physiological property cannot become
several independent experiments. A secondary account retains its original
attribution and source role. Unknown underlying independence is not asserted.

Direct evidence, qualified transfer and conditional inference retain the actual
organism/strain/sample relationship and supporting witnesses. Unknown target
identity or an unsupported transfer remains unresolved. Source method and
reliability qualifications accompany the result without becoming invented
numeric quality weights.

## Communication and integration

[A105_EPISODE_COMMUNICATION.md](A105_EPISODE_COMMUNICATION.md) documents the
actual custody mechanism to reuse. The scientific contents are A108-specific.

| Sender → receiver | What is communicated | Numerical work |
|---|---|---|
| Scientific parent → A108 episode | Candidate function, received target context, relevant findings, requested components | Define the actual contextual question |
| A108 episode → search/source child | Narrow question, actual organism/context, source leads and typed requested return | Find observations bearing on that question |
| Source-specific reader → appropriate subscoring grader | Authenticated observations, subject/context, source role/attribution; measurements when needed | Apply that observation type's distinct criteria |
| Subscoring grader → saved subscoring sheet | Assessed observation relations, source identities, support/conflict/unresolved sets | Compute defined counts and separately requested native quantities |
| Child → receiving episode | Requested numerical cells, original observation identities and necessary qualifications | Authenticate and admit those exact cells |
| A108 episode → main evidence scoring sheet | Selected possessed subscoring components | Recompute the set-union arithmetic |
| Main evidence scoring sheet → scientific parent | Requested scores, contributor/source refs and relevant unresolved relationships | Steer subsequent investigation from actual assessed evidence |

The identities needed for union are delivered with numerical components;
source bytes, transcripts and unrequested operands remain local. Registering
an `x-source` namespace without its reader, calculation and receipt path does
not complete scoring. Catalog, assignment roster, population route, saved
repository, return schema and receipt validation must agree. Shared-information
advertisements cannot confer private numerical-cell access.

The available tools and missing A108 exposure are documented in
[A108_SOURCE_AND_READER_PLAN.md](A108_SOURCE_AND_READER_PLAN.md).
This literature subtree has no `wait` action or new continuation gate.

## Evidence and continuation

These counts describe scientific evidence for the selected contextual question.
They cannot be populated by reading the episode's progress scalar. Current A105
separately binds finding progress for continuation and returns numerical
evidence-sheet components. A108 must expose its actual bindings and preserve
that distinction. This proposal installs no new continuation rule and does not
claim higher-level annotation-credit wiring is complete.
