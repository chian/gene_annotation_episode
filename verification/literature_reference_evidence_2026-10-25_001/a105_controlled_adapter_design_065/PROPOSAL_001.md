# Controlled-response composition proposal065

The arithmetic has four fixed primitive roles. N below counts source covariance
variables/owners projected into those roles, not arbitrary-N experimental arms.

Design only. No production file, reader registration, prompt, native operation,
model run or scientific policy was changed. Root must review the concrete
interface and examples before assigning a fresh coding workload. This is one
experimental component within A105, not a new axis or paper router.

## Recommendation and real interface constraints

Use an explicitly owned additive shared-stage refactor of the current source
reader, and a separately versioned full reader. Keep one implementation of
meaning extraction, reported uncertainty, full-N covariance validation and
saved consistency. Preserve exact old v1 requests/results/behavior and pins.
Call the accepted063 graph reader for graph observations, then join its result
BEFORE uncertainty, covariance and alias projection. Keep the separate006 sheet
calculator call after extraction. Do not monkeypatch either accepted reader.

008's public reader and detached validator are v1-only. Its measurement dispatch,
arm projection, uncertainty assembly and covariance projection are private and
coupled. In particular, graph measurement currently has unit=null. Replacing
only calculation_operand afterward leaves a valid same_as_response SD/CI null
and the full source C unusable. Its saved validator regenerates the original
text-only operand, so it rejects an injected graph operand. Such post-hoc
mutation is not an adapter.

An alternative public-API envelope can retain a v1 sub-result with graph
measurements explicitly projected to null and full graph results separately.
It must then duplicate unit-aware uncertainty assembly, full-N role projection,
alias checks and saved validation. Nulls in that intermediate are not scientific
missingness. This option is rejected as the preferred implementation: it creates
two authorities for those meanings and invites discarded valid information.

## Proposed ownership and callable stages

First coding owner, once separately released:

- Existing gene_annotation_episode/literature_controlled_response_inputs.py:
  additive public host stages and behavior-preserving internal extraction of
  repeated validation/uncertainty blocks. Existing exports remain available.
- NEW gene_annotation_episode/literature_controlled_response_v2_inputs.py:
  full v2 schema, dispatch, graph detached checks and joined result.
- NEW tests/test_literature_controlled_response_v2_inputs.py; bounded additive
  v1 compatibility checks in its tests, without rewriting frozen old fixtures.
- One new verification directory for that coding workload. All old pins,
  original source helpers,006 calculator,063 graph reader and unrelated runtime
  files stay unchanged in this tranche.

Exact new public HOST APIs in the existing source module:

    open_controlled_response_sources(arguments, *, read_source) -> SourceContext
    read_controlled_response_arm_science(context, selected_arm) -> ArmScience
    read_controlled_response_text_measurement(context, selected, *, endpoint) -> MeasurementReading
    finish_controlled_response_arm(context, arm_science, *, measurement) -> ArmExtraction
    finish_controlled_response_inputs(context, *, arms) -> SourceExtraction
    validate_controlled_response_saved_science(arguments, extraction,
                                             *, measurement_checks) -> SourceExtraction

SourceContext is an opaque, context-managed host object. Its only public methods
are read_source(source_ref, representation), close(), __enter__ and __exit__.
It retains selected arguments, complete authorized closure and shared witness
parsers. No source paths, callbacks or contexts are model-selected arguments.
Opening validates the complete v1/v2 closed request before invoking the actual
caller on its complete source closure; no image helper runs first. It exposes
only the prefetched immutable records and explicitly retained unavailable
exceptions. Shared stages validate that arms/measurement selections belong to
this exact context; objects from other requests/contexts are rejected.

The closure includes root source_ref/original, every nested source_ref with its
explicit representation or original default, every original_source_ref/original,
all declared selected/original image refs, covariance source and all actual
label/owner/model/meaning/uncertainty/axis.scale/tick/unit witnesses. Traverse the
FULL original v2 request, not a v1 projection. Deduplicate only identical
(source_ref,representation) calls. One validated immutable cache is shared by
scientific and graph stages;063 may prefetch its subset from that cache but may
not call the original provider again. An EOFError availability adapter for063
retains its original EOF diagnostic and raises documented EIO from that cached
dependency only; this translates an established availability outcome, not an
authorization error or a new acquisition.

measurement is a closed HOST MeasurementReading with fields:

    selection, extraction, operand_projection, unit_semantics,
    exact_response, source_observation_id, graph_details

selection is the original text/graph/null measurement nomination; extraction
is the corresponding old MeasurementExtraction or063 measurement. The numeric
projection is already parsed by the responsible source reader. unit_semantics
is null or exactly {canonical_unit, exact_scale, native_registry_unit,
raw_unit, source_defined_unit}; its source is the retained authenticated unit
record, never a made-up unit witness. exact_response is null or exactly
{point,lower,upper,relation,approximate,unit}, using rational pairs and nullable
point/bounds. It is for representation/alias checking, not model-selected data.
graph_details is null for text, else exactly {axis_scale,axis_literals} from063.

The text constructor uses the existing authoritative _measurement and
_operand_from_arm logic. Graph construction calls063 with the full declared
image roster and original graph nomination, through context.read_source. Its
projection supplies only numerical fields; shared scientific extraction supplies
endpoint/normalization/construct/condition/physical IDs, arrangement and states.
Failed graph results preserve their acquired facts and diagnostic status. They
do not enter a numerical operation as a fabricated zero. A retained nomination
identity must distinguish unsupported/ambiguous/conflicting readings from
missing ones because006 requires a nonnull source ID for those former states;
this identity is not a biological observation or graph success identity.

read_controlled_response_arm_science uses the EXISTING shared meaning/context
machinery and returns the closed arm science fields selection, context,
protein_arrangement, meanings and intended_factor_level. Its selected endpoint
is then available to the text measurement's source-defined unit reader.
finish_controlled_response_arm uses one shared uncertainty implementation. The
response unit is available before
same_as_response spread conversion. _uncertainty's explicit-unit suffix check
receives a semantic parsed-unit carrier, derived from the actual unit record;
the underlying native helper needs canonical_unit/raw_unit/source_defined_unit,
not a fictitious text source for a graphical unit label. Existing v1 units use
the identical old parser and conversion. Graph-defined U/mg remains the actual
063 unsupported capability, not factor1 or a new unit bridge.

finish_controlled_response_inputs performs existing relationship extraction,
exact alias checks, source covariance validation/bindings, effective model
selection and final frozen006 input validation. All graph-aware operands exist
before those steps. It calls no sheet calculator. Validation uses the same
shared saved-science functions for v1/v2, with tagged measurement checks that
never call a source reader, decoder or graph counter.

Exact public APIs in the new v2 module:

    controlled_response_v2_arguments_schema() -> detached schema
    validate_controlled_response_v2_selection(arguments) -> detached selection
    read_controlled_response_v2_inputs(arguments, *, read_source) -> extraction
    validate_controlled_response_v2_extraction(arguments, extraction) -> extraction

The new reader uses those shared stages and063's existing public read API.
It never feeds v2 arguments into frozen v1 validation. The refactor must show
exact v1 fixture/result equivalence; keeping a function name is insufficient.

## Closed request/result versions and field deltas

Request is exactly061 SELECTION_SCHEMA_V2_001.json, version
controlled_response_source_selection_v2. It changes007 only in root version,
required graph terminal_edge and required witnessed axis.scale. All existing
source/meaning/uncertainty/covariance nominations survive unchanged. No numbers,
matrix values, graph ordinates or biological IDs can be nominated directly.
The schema must be implemented in production code, not imported from verification.

Result version is controlled_response_source_extraction_v2. Begin with the
complete008 closed root and type fields, then the explicit061 graph delta:

- MeasurementExtraction permits063 reading statuses and actual PixelResult;
  GraphUnitRecord is a tagged union alongside unchanged text UnitRecord.
- Each nonnull ArmExtraction adds graph_details, null for text/null measurement,
  otherwise the exact063 {axis_scale,axis_literals}.
- calculation_operand remains exactly006 ARM_FIELDS; calculation_inputs remains
  exactly controlled_response_inputs_v1 unless a later reconciliation extension
  is explicitly adopted as described below.
- Root adds representation_reconciliations: array ReconciliationRecord, and
  implementation_dependencies binds the actual shared-stage/v2/063 generations
  as host provenance. Existing v1 output has neither addition.

ReconciliationRecord has exactly physical_observation_id, roles, source_reading_ids,
method, state, exact_domain, canonical_source_reading_id, canonical_operand,
qualifications and diagnostics. roles contains actual participating role names;
source_reading_ids identify retained actual readings. method is
identical_reading|reported_point_graph_check|conditional_domain_intersection|unresolved.
state is identical|compatible|conflicting_reported_points|incompatible_domains|
unresolved_meaning|unsupported_model. exact_domain is null or a closed rational
{point,lower,upper,unit}; canonical source/operand are nullable. Qualifications
distinguish conditional_digitization_agreement from sampling uncertainty.
Each of these semantics needs an explicit release; this proposal does not claim
the old006 contract already implements representation reconciliation.

## Full-N covariance, partials and one physical owner

Keep original C over ALL N source variables, exact lexical tokens/rationals,
source labels at actual token positions, per-variable native units, source
model and known/estimated status. Check full exact symmetry/PSD before selecting
four roles. Projection uses the selected original variable indices, not labels
or a fixed four-row source. Duplicate labels and singular PSD remain legal.
Every index has a witnessed binding to the same physical owner as its arm.

Both unit factors apply to each covariance entry. Exact source PSD versus finite
projection PSD/range are separate states. Missing or invalid C leaves magnitudes
and reported SD/SEM/CI/count pieces intact. SD plus count does not supply a joint
C, independence or known variance. Source, requested and effective models remain
separate. Any graph quantity actually used in the contrast retains graph origin,
digitization intervals and the existing exclusion from006's optional normal S/B.

A shared graph control used twice is one owner, one exact graph reading and one
source covariance variable. Its repeated coefficients cancel in e and V; do not
subtract independently computed interval endpoints or add two control variances.
Unavailable one control leaves the other local pair and all raw facts intact.
Source alias checks must use exact normalized text lexemes OR exact graph native
values/bounds, not float-equal values and not the current text-only _cross_control_alias_conflict.

## Mixed text/graph aliases: a real requirement, not a permanent null policy

**Additive priority clarification:** OWNER_CANCELLATION_002.md, prepared after
root's follow-up, recommends owner-level symbolic cancellation before selecting
a representative of a canceled owner. The point/domain reconciliation options
below concern active, noncanceling owners or requested local canonical readings.
They must not be imposed on a control that cancels exactly. A minimal explicitly
versioned calculator/input extension is needed;006 remains unchanged here.

006's _alias_reasons compares status, relation, approximate and interval fields,
in addition to values/meaning. Thus a printed point2 and graph1.95[1.85,2.05]
assigned the same owner currently conflict at that input boundary. They need
not contradict the source: the graph conditional domain includes2. Do not call
them independent observations, choose the favorable number, average them, or
turn the conditional domain into SD/SEM/CI. Retain both original readings.

Recommended reconciliation option A, requiring explicit scientific acceptance:
when source-witnessed same-owner/endpoint/normalization/context meanings hold,
all exact reported point representations agree after exact unit conversion,
and that common point lies in every participating graph conditional domain,
retain the reported point as the canonical source reading. This rule is
independent of effect sign or magnitude. It does not improve sampling precision
or add a replicate. Each role then refers to the SAME canonical reading/owner.
Preserve graph details and a reported_point_graph_check record showing each
exact domain and its conditional assumptions. A new typed return must carry
that qualification even when it returns only a derived cell.

This point-based canonicalization can feed existing006 arithmetic, but006 does
not carry companion-reading qualifications or reconciliation in its inputs.
A separately versioned wrapper/result contract must retain them; if they affect
model eligibility, use an explicit controlled_response_inputs_v2 with a
reconciliation/reading-qualification block and a separately versioned calculator
wrapper. Do not post-hoc erase graph limitations or silently enable S/B because
canonical origin was relabeled reported. For the initial option A release,
conservatively keep model none whenever graph readings participated; preserve
the actual requested/source model and the specific eligibility reason.

Option B is a conditional-domain intersection for all same-owner representations,
without invoking independence. If there is an exact common reported point it
reduces to A's domain check. Graph-only overlapping domains can have no unique
reported point: e.g.[1.85,2.05] intersect[1.90,2.10]=[1.90,2.05]. Inventing a
midpoint is not a source measurement. A minimal separately versioned calculator
input would permit value=null, status=interval, relation=interval with finite
conditional bounds, and preserve the one physical owner. Its range algebra must
allow a point-free conditional interval to cancel exactly when a shared owner
has net coefficient0. V depends on actual C; profile evidence additionally needs
a supported reading model. Such a calculator change is OUTSIDE the accepted006
contract and requires its own release/verification; no covert006 change is proposed.

Reported points that disagree are retained as conflicting alternatives. A text
point outside a graph conditional domain is initially an incompatibility of
retained reading assumptions/nomination, not automatically a biological or
publication contradiction. Preserve source, graph and extraction uncertainties
separately and permit the episode to reread/repair. Incomplete ownership/units
leave the reconciliation unresolved. The full objective remains incomplete until
the needed reconciliation is implemented and delivered, not merely recorded.

For an unresolved cross-comparison alias, withhold unusable projected C before
calling006 so its strict validation cannot erase valid raw/local pair results.
This is an intermediate compatibility behavior, not the final intended owner
algebra. The versioned contract must preserve those local results while allowing
properly established canceled owners to leave the cross effect. No unknown
owner, unit/normalization mismatch or unsupported control application can be
silently canceled merely because two values or labels look alike.

## Saved validation, custody and ordinary native integration

Shared detached checks recompute consistency from retained records only:
original selection/roster equality; witness locators and artifact/digest mapping;
meaning canonical IDs; text exact numbers/units and reported uncertainty;
graph unit/literal/scale qualifications; original/crop mapping; selected runs,
terminal clipping, signed exact calibration and outward finite projections;
source reading identity; covariance full-N validation and owner/index projection;
reconciliation exact-domain checks and canonical reading assignment; effective
model; final frozen or explicitly versioned calculator inputs. Reconstruct the
graph identity with063's exact identity_record keys/JSON settings, not a new UID.
measurement_checks is a host-only callable with signature
validate_measurement(selected, saved_measurement, *, source_records, image_records)
-> MeasurementReading. Its text path delegates the unchanged shared text checks;
the v2 graph path uses the full closed063 record and detached algebra checks.
It is never selected by a model or loaded from a request. Saved validation never
redecodes pixels or attests pixel counting from a hash.
Pixel truth is bound by the original selected request, actual outcome and source
custody. A self-consistent replacement JSON document is not that proof.

SourceContext prefetches actual caller closure before helpers. Callback errors
and malformed records propagate; accepted explicit availability signals remain
typed partials. For the composed reader, use the source reader's documented
ENOENT/EIO/ETIMEDOUT/EOFError availability contract and normalize retained EOFError
to a documented unavailable signal at the063 cache boundary; do not broaden063
itself. Reject same artifact handle/different bytes in the combined cache. This
is an additive v2 guard, while063's pure callback precondition remains unchanged.

Later native owner needs NEW literature_controlled_response_storage.py and its
test file; it also exclusively owns additions to literature_episodes.py,
episode_services.py and the experimental/parent return renderers. Propose
operation literature.controlled_response.populate and x-source
literature_controlled_response_cells, provider literature.a105.controlled_response,
record version literature_controlled_response_record_v1, independent operation/
received/delivery-binding tables. Do not overload two-arm native-rate payloads.

The repository can reuse LiteratureRateRepository's owned/admitted-subset
fact_cells, validate_fact_values, receive_cells, received_cells and actual
runtime-form admission proof. It must override populate/read/project_cells for
the12 controlled cells, bound/relation fields, list-valued unavailable reasons
and exact scientific qualifications. populate invokes extraction and THEN the
separate calculator once, publishes source/request/result transactionally, and
replays an identical operation without parsing or calculating again. Every source
callback checks actual episode receipt, scope, assigned-page ancestry and uses
Store.get_artifact, which verifies content identity. Replay/reopening validates
request/selection/output ownership, saved source-record bindings and exact cells.

LiteratureEpisodes additions reach catalog/execute/page-ancestry checks,
requested_controlled_response_components, fact-source schemas, population routes,
exact child validation and received-form subset receipt. Binding as_record must
include new reader/stage/graph/calculator/repository/renderer code identities.
Existing factories in independent_execution._saved_episode_factories and
episode_composition restore configuration through LiteratureEpisodes; verify the
saved descriptor before model transport. An explicit opt-in binding configuration
is preferable for new work; its exact field belongs to the native-owner release,
not a guessed modification in this pure-reader tranche.

Typed rows preserve the selected cell's complete CELL_FIELDS and necessary
meaning, physical-owner, graph/reconciliation and model qualifications. A raw
cell may expand its own response/uncertainty; a derived-only return must not leak
unrequested raw arm numbers, covariance entries or hidden companion values.
Forward only received components; owning a sheet reference is not possession of
all its cells. Render complete recurring scientific TASK and curt requested facts
in STEERING, not the whole extraction/schema. A separate aspect-specific TASK
needs root chat review; this proposal writes no production prompt.

The native owner must verify C1 source/operation ownership, actual selected
LiteratureEpisode work, C4 original typed form validation, exact admitted subset
and read-only reopening with source/decoder/calculator disabled. Source reads,
calculation helpers, contracts and reporting add no synthetic observations.
Do not alter shared method_loop, scientific/monitor credit, continuation costs,
parent-child relationships, ten axes, A101 correspondence or W05 aggregation.

## Verification scope and next action

EXAMPLES_001.json and EXPECTED_CELLS_001.md contain constructed numerical cases
calculated through immutable006 only. They are not captures of a new adapter.
The complete v1/v2 stage code and graph-aware saved checks remain to be written.
First review the shared-stage API and reconciliation options, print those
examples to the user, then issue a fresh coding release with explicit ownership.
Native integration follows the coherent pure interface; it remains required,
along with actual model-backed primary evidence, before this goal can complete.
