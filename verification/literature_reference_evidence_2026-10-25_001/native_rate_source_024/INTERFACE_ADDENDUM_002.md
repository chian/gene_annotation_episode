# Accepted 024 interface corrections before production edits

The parent reviewed proposal 001 and requested the following corrections, then
authorized implementation. This adds to that proposal; the earlier text remains
historical where it requires common subjects or known physical identities.

1. Parse source-defined U/mg now through the existing endpoint-specific
   definition reader. Preserve its validated source bridge, molecular endpoint,
   exact amount/time and denominator. Convert its exact pmol/min/mg scale into
   this sheet's umol/min/mg scale; do not edit partner helpers or define a
   universal U alias. Genuinely unsupported forms remain explicit partial data.
2. Native arms retain their own nullable subject, construct, preparation,
   experiment and condition witnesses. A deliberately different molecule,
   construct, preparation or condition can be the intended comparison. Equal
   labels establish neither shared identity nor nuisance comparability.
3. The comparison carries source-interpreted subject/endpoint/normalization
   relations (`same`, `different`, `unknown`) with witnesses, and a nullable
   intended-change witness. Same subject is not required for raw endpoint
   arithmetic; compatible endpoint/basis and dimensions are required. Causal
   isolation and attribution remain separate from those raw contrasts.
4. Native numerical rows include optional nullable per-arm subject, construct
   and preparation references through the existing rate-cell namespace. Existing
   v1 rows and their required field set stay exactly unchanged. The common
   assayed-subject binding is null unless a same-subject relationship is
   explicitly source-supported. Native bindings must pass projection,
   validation, typed admission, received-subset copying, reopen and actual
   provider text, not merely remain private payload fields.
5. Unknown physical observation IDs do not veto an explicitly source-supported
   conditional independent-groups model. Known reused numerical byte locations
   or known shared physical observation identity defeat false independence.
   Distinct locations, count and preparation identity do not prove independent
   observations. Sampling basis and selected model remain separate information.
6. The owner also receives narrow ownership of
   `tests/test_literature_parent_population_information.py` to assert an additive
   operation while preserving the exact historical 14-entry fixture.

The existing recurring experimental TASK remains substantive. The new operation
description and input schema expose its source selection. The owner will inspect
`_source_result`, `_received_returns`, and `_selected_records` in the existing
experimental text renderer and test provider bootstrap/delta/reconstructed text.
That renderer is not owned; report any required narrow fix to the parent first.

Baseline: 113 existing rate reader, calculation, storage, shared-loop integration
and specific-rate-unit tests passed in 26.09 seconds before production edits.
These are synthetic/scripted checks, not actual-model scientific evidence.

## Later parent-approved refinements

Native cells retain an `approximate` boolean. A useful reported point estimate
keeps its source qualifier; each derived cell inherits approximation only from
the actual operands it uses. Signed finite rates remain valid. Conditional
profile/model results do not claim an approximation's rounding error is known.

The real closed-schema boundary rejected optional projected fields. As recorded
in `CLOSED_RETURN_CORRECTION_003.md`, native per-arm bindings and `approximate`
are therefore required fields in a separate closed native return projection,
with nullable references where unknown. The legacy projection remains exact.
This supersedes item 4's optional-field placement, not the one-sheet design.

The parent later assigned only the renderer `_safe` generated `native_rate_`
prefix suppression; no TASK/STEERING redesign. A native field-aware lexical
context helper and thin owned defined-unit reader were also approved after
synthetic table diagnostics exposed cross-cell context in the shared reader.
They preserve source bytes, exact source identities and the unchanged pure
definition/endpoint/containment semantics without partner-module changes.
