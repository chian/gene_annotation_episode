#078 exact additive shared host-stage contract

Supersedes the unspecified shared-extension dependency in PROPOSAL003.
Existing073 and076 remain accepted only in their original scopes.

## Exact stage API and profile handling

Preserve the original v1/v2 calls and results when added keywords are absent:

```
open_controlled_response_sources(arguments, *, read_source) -> SourceContext
read_controlled_response_arm_science(context, selected_arm, *, reading_selector=None) -> ArmScience
read_controlled_response_text_measurement(context, selected, *, endpoint, reading_selector=None) -> MeasurementReading
finish_controlled_response_arm(context, arm_science, *, measurement, reading_selector=None) -> ArmExtraction
read_controlled_response_covariance_document(context, scope_key) -> CovarianceDocumentStage | None
bind_controlled_response_covariance_scope(context, scope_key, document, *, readings) -> BoundCovarianceScope
finish_controlled_response_inputs(context, *, arms, companion_arms=None, covariance_scopes=None) -> SourceExtraction
validate_controlled_response_saved_science(arguments, extraction, *, measurement_checks) -> SourceExtraction
```

The four public v3 facade APIs and the independent local/population/native APIs
are in API_006. HOST stages are not model tools. No source/ref/callback/path is
supplied outside the original request/actual context. No new __all__ additions
are necessary in the original v1 source API. New host stages can be explicit
imports, like073's existing ones.

open dispatches by EXACT version enum, not endswith or unknown→legacy fallback:
source_selection_v1 → original v1 validator/profile; source_selection_v2 → exact
073 v2 validator/profile; source_selection_v3 → new closed006 v3 validator/profile.
Original v1/v2 invalid-version/error ordering remains exact; only the explicitly
new v3 entry admits v3. `context.profile` is immutable v1|v2|v3. Every branch that
means 'tagged text/graph carrier with joined uncertainty' handles v2 AND v3;
branches preserving v1 alias/covariance/legacy error behavior remain v1 only.
The original public v1/v2 facades continue rejecting each other's/new versions.

reading_selector is exactly `{role: one original primitive role, reading_key:
null|string}`. In v3 it is REQUIRED for the three arm/text/finish stages. null
selects the original arm, string selects an existing unique companion for THAT
role. In v1/v2 the new keyword must be absent/None; a supplied selector is a
specific unsupported-stage-selector error, not a changed interpretation. No
role replacement, temporary argument mutation or per-companion source context.

The host immutable reading registry is built at context creation in fixed
primitive order for primaries, then original companion nomination order. Registry
entry: selector → actual original Arm or null, immutable source selection path,
original nominal role, field path. Primary field paths retain `arms.<role>`;
companion paths are `companion_readings[i].reading`. Host tokens bind context,
profile, selector and exact selected Arm. These tokens stay outside saved JSON.

ArmScience and MeasurementReading retain their COMPLETE073 public payloads.
read_arm_science authenticates the actual selected Arm from that registry and
places its selector token on the stage object and its endpoint binding.
read_text_measurement requires the same selector/actual nomination/endpoint
identity; it calls the SAME original scalar/unit parser and shared semantics.
finish_arm requires the science/measurement/context/selector tokens agree, then
runs the SAME joined uncertainty/operand assembly with actual carrier. A graph
facade helper `_read_graph_v3(context, reading_selector, *, endpoint)` retrieves
the actual nominated GraphMeasurement, uses actual063 through the original
prefetched cache, and returns the same MeasurementReading with its selector
host token. It does not mutate063 output, transcribe source meanings again or
reopen sources. This helper must check the endpoint token, registry selection
and complete graph identity exactly as the text stage does.

## One complete original closure and custody

The ORIGINAL v3 request includes full v2, all companions, all joint/local scopes,
reconciliation and authority witnesses. Its complete recursive source closure
is prefetched exactly once per unique(source_ref,representation), sorted as073.
This precedes geometry/graph helpers. Include unused images, original/crop images,
axis.scale-only sources, every unit/definition/context/meaning/spread/count,
original/joint/local full-C and model/authority source. All selected witnesses
are authenticated even for scientific or capability partials. Existing callback
success/error/artifact-alias and availability contracts remain exactly073.

Helpers have only the cached closure; no fallback acquisition. Context.close
releases every native frame/cache/token/endpoint/reading/document registry on
success/error. Shared context opening is once per selected operation, not once
per reading/assignment. Parsing multiple retained readings is internal work,
not another episode or controller observation.

## Exact scope key and document/binding split

scope_key is HOST data, exactly `{kind:base|joint|local,index:null|nonnegativeInt}`:
base requires index=null; joint index is the ORIGINAL assignment index and has
exactly one `joint_scopes.assignment_index` record; local index is the ORIGINAL
local_pair_assignments index. Reject duplicates/holes/wrong indices and any
attempt to bind a stage object to another scope. These are source-selection
keys, not autonomous resource or experimental choices.

Context builds an immutable scope registry:

| Key | Actual source nomination | Actual reading map | Requested source model |
| --- | --- | --- | --- |
|base/null|original covariance|original four primaries|original variance_status/model_kind|
|joint/i|joint_scopes[i].covariance_selection|exact joint_reading_assignments[i].assignment|that joint scope's exact fields|
|local/i|local_pair_assignments[i].covariance_selection|ONLY that pair's protein/control selectors|that pair's variance_status; no local normal profile is proposed|

The separately declared CovarianceDocument is the complete original-N SOURCE
facts, not a four-role projection. Its exact keys in006 are source_ref,
artifact_ref,byte_sha256,raw_text,variables,matrix_tokens,exact_matrix,source_model,
source_validation,diagnostics,document_state. document_state is available,
unavailable or unsupported_format; invalid C is an available document with
source_validation=invalid. It retains original label/unit/description witnesses,
lexical numbers, exact rationals, every row and source model. No source variable
is silently removed. Null scope nomination returns None, not a fake document.

read_covariance_document checks scope registry and source cache, invokes the
shared strict full source-N lexer/shape/symmetry/PSD logic before any binding or
marginal, and returns a context/scope-owned document stage. Actual parse results
can be memoized by the exact original source/representation/artifact/byte identity;
each scope still receives its own token. Different source keys are not merged by
same values. Wrong label/index nominations remain direct selection errors,
including unused nominated bindings, after authenticating their actual witnesses.
Bad authentic source C remains a retained partial, never a contract-valid fake C.

The source's structural lexer and exact C validation must be factored from the
existing `_covariance` implementation, not independently rewritten in the facade.
Original v1/v2 wrappers keep their exact legacy binding/projection/error behavior
and order; the new document stage exposes the same facts to new v3 consumers.
No accepted006/076 arithmetic/helper changes are implied.

bind_covariance_scope takes its exact document and an ORIGINAL-ORDER sequence
of `(ReadingSelector, actual ArmExtraction)` stage objects. For base/joint the
sequence covers exactly all four original roles under that exact assignment;
for local it covers EXACTLY its two selected pair readings. `readings` is not a
map with fabricated null/unrelated role entries. It checks every selector/token
and the source's actual covariance binding against that selected reading's
physical-owner witnesses and canonical owner; verifies label token ORIGINAL
indices, dimension, and all full-row repeated-owner relationships required for
any proposed projection. It retains unknown/conflicting binding meanings.

BoundCovarianceScope's exact closed keys are scope,document,bindings,
whole_projection. bindings contains exactly `{reading:ReadingSelector,
binding:CovarianceBindingExtraction}` per supplied reading. whole_projection is
null for a local scope; base/joint use actual original CovarianceExtraction
ONLY when that complete original role scope is meaningful. The full source doc
survives missing/invalid/partial projection. Local binding/variance never calls a
four-role owner validator on stand-ins. A binding problem outside a local pair
cannot create a fictitious pair binding failure; original full-N invalidity
still prevents all its marginals. Both source-C variable unit factors apply.

## Finish and exact dataflow

finish(context,arms=...) keeps its original v1/v2 behavior with new kwargs=None.
For v3, arms is the exact original four-role map of actual primary stage values;
companion_arms is the complete original-order list of `(ReadingSelector,
ArmExtraction)`; covariance_scopes is the complete original-order sequence of
context-owned BoundCovarianceScope values (base then joint then local). No
already composed sheet, guessed selected number or external covariance enters.

Finish validates completeness/token relationships, extracts actual source-backed
relations/authority and scope premises, and constructs:

1. Unchanged full primary rows; every complete companion row; original root
   relationships/requested/effective source fields and full root-C projection.
2. covariance_document_scopes, with exact scope keys and original complete docs;
   joint scope rows preserve their actual witnesses/model/full-C projection.
3. Representation reconciliation decisions and final_projection_basis. A ready
   actual068 input selects only source-supported actual readings with exact
   original origins/domains and C/model scope. Reconciliation policy is still
   the proposed scientific policy in003; no favorable primary or averaging.
4. Every supported explicit joint conditional input with exact actual map and
   original source/model/C scope. Unknown/conflicting compatibility adds none.
5. Only an actually representable reviewed homogeneous ambiguity-group partial
   may populate partial_calculation_inputs; otherwise retain precise origin/ID
   limits. No caller or method signature supplies arbitrary group IDs.
6. Independent LocalInputs: actual reading rows, explicit pair science and
   actual two-reading bindings, and CovarianceDocument facts. No whole four-arm
   input is required to populate unrelated raw/local cells.

The source reader calls no populator. Separate population invokes actual068 on
ready/valid partial/supported conditional actual inputs, and invokes the NEW
component-local populator once on its own input. Internal calculations create no
synthetic own-action observations. Original full-C documents validate before all
marginal calculations, including local ones.

## Exact source identities and detached validation

Original literal IDs and original063 graph IDs remain exactly their own
reader-generated values/serialization. Canonical owner/context IDs are the shared
original witness-locator identities; equality is not inferred from numeric labels.
Companion reading_key is merely the unique nomination label and never a physical
owner or independent experiment. Source registry order cannot depend on JSON
object-key order.

The proposed homogeneous group ID described in003 is reconstructed from the
actual original IDs/selector/nomination order/source-kind/method and original
canonical owner. It represents retained reading attempts, not a new measurement.
The saved validator must independently reconstruct it; a caller-authored string
is never a custody grant. Mixed/unavailable groups use local components instead.

validate_saved_science dispatches by exact saved version to original v1/v2 or the
new v3 path. The measurement_checks callback must receive
`validate_measurement(reading_selector, selected_measurement, saved_measurement,
*, source_records, image_records)` ONLY for v3; original v1/v2 measurement-check
calling convention stays exact. Matching by first equal selected measurement is
insufficient for two companions with equal nominations and different scope.
Validate every original source/image/witness relationship, complete actual063
record and identity, science/unit/spread/count, every original covariance doc,
source model, exact binding/assignment and every projected input using retained
facts. No callback, image decode/count, model, populator or canonical reselection
runs during detached validation. Rechecking retained original C raw_text is
permitted; it is not source acquisition. Native original-outcome custody remains
necessary beyond self-consistent saved JSON.

Missing implementation is unfinished function work, not unknown scientific evidence.
