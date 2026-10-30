# Requested operation-contract information for literature decisions

Proposal only. No production/test edits or model/scientific execution are released.
This supports the existing LiteratureEpisodes choosing among actual experimental
readers/calculators. It does not classify a paper, select a grader, narrow an
episode's capabilities, add a sheet or change annotation credit. Ten axes remain;
A105 remains incomplete. One paper can supply several experiments/components.

## The implementation problem

057 and root independently measured the current child recurring text at1,986,251
UTF-8 bytes and provider output schema at743,740 serialized bytes, before source
evidence. The parent text was978,991 bytes. Those are measured synthetic request
shapes, not measured tokens, a provider rejection or proof of a backend limit.

Three different consumers expand contracts:

1. `LiteratureEpisodes.catalog` supplies all actual operations with full input
   schemas. `_task` in literature_experimental_prompt renders every schema into
   recursive tables. Requested components affect returns, not available tools.
2. `Workflow.action_schema` embeds actual tool schemas. For composed argument
   schemas, `_action_generation_schema` transports an outer JSON object as a
   string and puts its entire original schema in the string description.
3. The reference-parent renderer expands all literature fact-source schemas,
   including types the parent has not selected. A parent currently must then
   write an expanded closed form into `schema_json`; `_compile_form` has no
   existing named fact-schema reference expansion.

A manual lookup alone fixes none of those consumers. Keeping actual execution
contracts authoritative while changing their information delivery is the scope.

## Exact proposed opt-in and frozen transport

Add one optional C7 constructor operand:
`contract_information_profile=None | "operation_contract_information_v1"`.
The explicit profile requires rate_population=True. Omission retains the current
eager representation. Record a supplied profile in the existing C7 configuration
descriptor; known worker reconstruction already passes that configuration to
LiteratureEpisodes and compares actual descriptors. No default model, controller,
cost, estimator, role edge, source scope or execution setting changes.

The profile applies to C7's own roles and the explicitly assigned source-evidence
annotation parent. An optional pure registry hook reports that profile from
bound configuration/role/path; it reads no source and chooses no work. A conflict
between bound profile declarations is an ordinary configuration error. Other
roles and historical runs retain their own representation.

The actual host catalog retains every current operation, description and full
input schema. Catalog metadata for the opted-in19 population entries indicates
that argument instructions are available on request. It grants no capability.
`Workflow.action_schema` copies a versioned HOST-ONLY transport annotation onto
those tool-action branches, alongside their unchanged complete argument schemas:
`x-argument-transport="json_object_contract_information_v1"`. The annotation is
part of the original saved host schema, not a value supplied by the model.

For a marked branch, provider generation supplies kind/tool as before and
arguments as a JSON-object string with a short transport description. It does
not inline the full schema. Strip the annotation and all host fingerprints from
the provider schema and model-facing text. Unmarked branches retain their
current translation. All actual names remain selectable; retrieval is optional.

The authoritative decoder must recognize the marker in the ORIGINAL host schema,
including for simple operations that currently transport objects. Extend the
existing `_json_tool_arguments` predicate to recognize that exact marker only on
an actual tool branch; `_decode_action_response` then parses the outer transport
once with the existing strict `parse_json_object`. Preserve omission and explicit
null exactly. Do not recursively parse literal strings inside that object, choose
defaults, or infer transport by inspecting today's mutable catalog. Existing
object-valued fixture input can retain current handling. A tool whose declared
outer arguments are not an object must not be marked under this profile.

After decoding, the unchanged complete original argument schema and ordinary C7
scope/custody validation still apply. Malformed JSON, duplicate keys, nonfinite
numbers and incorrect source selections retain their current failures. Direct
invocation without a lookup is allowed and receives exactly the same validation.

## Two information requests inside the existing pending decision

Extend `composition_information.metadata_catalog` with two small closed metadata
operations only where the profile is bound. They are pending-decision information
handlers, not new completed-action tools in Workflow.catalog:

| Information operation | Exact arguments | Authorization and result |
| --- | --- | --- |
| episode.operation_contract | operation: actual callable name | Resolve only an operation in this episode's original pending-decision catalog. Return its exact description/input schema and lossless text. |
| episode.return_contract | role: permitted child role; source: declared fact-source name | Resolve only a fact projection available for that real child role. Return its exact meaning/report schema and lossless text. |

Queries use the existing response_type=request_context and view=composition_information
envelope. No semantic retriever or extra model composer is invoked. This does not
replace process.tools or turn C7 into the separate scientific-process tool slot.

Example request, as internal protocol data:

    response_type: request_context
    lookup.view: composition_information
    lookup.operation: episode.operation_contract
    lookup.arguments.operation: literature.kinetic.populate

Return an ordinary completed outcome with empty record_refs/changed_record_refs,
null feedback, and a result containing a finite information_kind, selected
operation or role/source, exact meaning, authoritative schema, content fingerprint
and rendered text. The schema/fingerprint remain HOST records. The actual model
receives the meaningful text/tables, never a raw schema/context JSON dump, host
hashes or a scoring sheet. The result says it is operation/return information,
not experimental evidence or a completed scientific operation.

Resolve operation metadata from the saved original logical-decision context's
tool entries and original host schema, checking their agreement, rather than
refreshing a catalog for an answered query. Return-source factories are pinned
by the original bound implementation/configuration; freeze their exact answer
and fingerprint into the existing lookup result before delivery. Replay reads
that immutable answer without resolving or formatting a different contract.
Wrong names/roles/source selectors and inconsistent definitions return existing
structured decision-exchange failures. No source artifacts are read to answer.

## Lossless text without recursive duplication

Represent each distinct repeated JSON object/array structure once using local
named definitions. Text gives the root, each definition's object/array kind,
each field or array position, explicit reference versus literal status, and all
literal values. It retains descriptions, enum members, required/optional lists,
nullability, reference meanings, all constraints, local $ref resources and array
order. It does not follow external references or acquire anything.

Definition1 etc are local grammar labels, not persistent record/tracking IDs.
Scalar spelling is explicit: a quoted string differs from null/false/0. Table
escaping preserves literal pipes/newlines and Unicode. An unknown keyword is
still represented exactly; no renderer silently drops it. Implementation should
prefer meaningful labels where unambiguous, without inventing scientific meaning.

Executed proposal002 parses the rendered tables back into the original schema:
all19 current operation contracts and18 current fact contracts roundtrip exactly.
It also checks literal strings that resemble definition names, quoted/newline/
pipe/Unicode text, booleans versus integers, nested constant data and empty values.
001 proved the intermediate graph only;002 explicitly repairs scalar/reference
ambiguity in that preliminary text.001 remains preserved, not relabeled as a
complete text-losslessness proof.

| Actual contract | Current expanded table | Complete lossless002 text |
| --- | ---: | ---: |
| Kinetic operation input |116,721 bytes|23,734 bytes|
| Binding interaction operation input |987,615 bytes|28,112 bytes|
| Kinetic fact projection |37,477 bytes|33,763 bytes|
| Binding interaction fact projection |459,853 bytes|51,052 bytes|

These are local UTF-8 text sizes. They prove neither model comprehension nor
configured-provider acceptance. Full selected definitions are delivered; there
is no implicit truncation, applicability filter or automatic operation choice.

## Concrete TASK and STEERING boundary

Keep all existing substantive scientific TASK constants and actual caller job,
scope, constraints and return meanings complete on every call. Replace only
eager API-schema expansion under the explicit profile. The initial TASK has the
same complete operation names/descriptions plus this proposed mechanical guidance:

> Choose among the listed operations for the assigned evidence question. Request
> an operation's full argument contract through request_context,
> composition_information, episode.operation_contract when useful. Select the
> actual operation name. All listed operations remain available. The lookup
> supplies instructions within this same decision and creates no completed action
> or observation. You may invoke an operation directly; the host validates its
> original complete argument contract.

The parent additionally sees all available fact-source names/meanings and may
request the full declared return type for a permitted child via
episode.return_contract. Its actual already-requested return contract is always
shown completely, using lossless definitions. It is never replaced by an index.

After an explicit query, place the complete requested operation/return contract
under a clearly labeled TASK subsection, separate from the scientific directions
and source evidence. Keep STEERING limited to the current own yields, estimates,
actual outcomes/received results and necessary finite information status. Current
`_source_result` would label a generic text result as selected source evidence;
therefore the new finite information_kind needs a dedicated mechanical display,
not that source-evidence fallback.

Every exchange in this same pending decision must receive the completed contract
information explicitly requested so far, even after another kind of lookup or
provider reconstruction. Derive it from existing immutable public exchange rows,
not a private model history or hidden cache. An explicit optional
pending_contract_information field on the lookup frame carries those recorded
replies separately from the scientific snapshot. It is journaled in that exact
request, excluded from scientific state revisions, and projected into text only.
Bootstrap restoration derives the same information from restored_public_exchanges.
Never alter a saved prior frame/revision or hash one scientific view and send
another. A later completed-action decision need not preload every older manual;
its scientific TASK stays complete and it can explicitly request information.

The synthetic initial TASK examples retain all current scientific bodies and
all19 names/descriptions. They measure45,708 child bytes and24,569 parent bytes.
They omit real source/working-state/selected-form data and common nonpopulation
tools, so these are not replacement whole-request measurements or model runs.

## Parent-chosen compact fact-schema references

On-demand return information alone leaves the parent copying a large schema into
schema_json. Propose a bounded optional standard-schema reference representation:
an entire top-level field node may be exactly
`{$ref: "episode-fact:literature_kinetic_cells"}`. Resolve only this semantic
scheme against that permitted child's actual declared fact map, clone the exact
registered report_schema and attach its exact x-source selector. Other form
nodes remain explicit parent-chosen constrained types. Reject siblings, nested
fact refs, unknown/disallowed selectors, remote URIs and conflicting definitions.
No external schema resolution, inferred field name or initial fact value exists.

Expand before the unchanged `_compile_form`/validate_closed_schema checks. The
resulting original child contract is the same fully explicit closed schema as a
literal copy. The parent still chooses the child, form field names, fact sources,
scope, requested components and separate constrained interpretations. Complete
expanded forms remain accepted. This interprets copying the declared projection
as either a literal copy or an explicit reference to that exact declaration;
it does not weaken the saved-numerical-return instructions or bound facts.

The synthetic parent field measured_comparison chooses the kinetic source:
167 compact bytes expand to18,168 bytes of the unchanged fully typed closed form.
That is a schema-only illustration; no scientific number or form value is filled.

Preserve the submitted compact selection and the exact expanded original as one
commission identity. Existing runtime_commission_intents.selection already keeps
the complete original selected action, while child.request.report_contract and
runtime_episodes keep the expanded typed contract. Add a HOST-ONLY declaration
record to the child's original message containing the supplied compact form,
selected source-contract fingerprints and expanded-schema fingerprint. It is
part of the existing frozen request/spec identity, excluded from model TASK and
scientific facts. No second report model, observation or scientific record is
created. The existing C1 comparison authenticates the full original request.

On recovery, use the original saved expanded report_contract and declaration;
never expand against current factories. Verify compact selection/declaration/
expanded-schema agreement. For the ordinary blocking fallback, find the existing
stable child request before attempting expansion on replay, so it has the same
invariant. Original C4 admission, exact requested/admitted subsets, validators
and read-only scientific reconstruction continue using the original expanded
schema. Do not relax communication.KEYWORDS or base044 to allow unresolved refs.

## Proposed file ownership and implementation sequence

Nothing in this proposal grants production ownership. Root must assign these
exact interfaces/shared files before implementation. Prefer one integration owner
because decoder, frozen profile, lookup and rendering must describe one contract.

| File | Bounded responsibility |
| --- | --- |
| NEW schema_information_text.py | Pure complete named-definition text and losslessness checks; no source/science/runtime dependencies. |
| NEW episode_contract_information.py | Closed information catalogs/results, exact frozen definition resolution, pure fact-ref expansion/declaration validation. |
| composition_information.py | Append the two optional metadata operations under the bound profile; preserve existing lookup branches. |
| episode_bindings.py | Optional pure profile hook aggregation only; no change to scientific interface ownership. |
| literature_episodes.py | Optional profile constructor/descriptor, pure role applicability hook and19 catalog transport metadata; include new implementation bytes. No operation dispatch/source validation change. |
| runtime.py | Frozen branch marker generation/strict decoding; metadata-only handlers; exact pending lookup delivery; pre-validation form expansion and original declaration preservation at selected build/replay. |
| providers.py | Render explicitly supplied pending information through the ordinary existing frame path; no provider/model/routing/configuration changes. |
| independent_execution.py | Forward only the original host report-contract declaration from the saved child message into Workflow.build; no new factory or settings path. |
| literature_experimental_prompt.py | Profile-only schema-index/complete requested-type rendering and dedicated requested-information subsection. Preserve scientific TASK/masking/received projection functions exactly. |
| literature_reference_parent_prompt.py | Profile-only fact-source index and full requested-type rendering. Preserve parent science and own STEERING selection. |
| NEW focused tests | Lossless display/strict transport; actual pending-decision lookup/provider frames; original compact→expanded commission/C4/recovery and all-capability preservation. |

Current generic independent_execution already hashes every application/shared-loop
.py file and reconstructs C7 from its saved configuration. It should need no new
factory or settings pathway. Its bounded declaration-forwarding addition is
necessary because Workflow.build compares the whole reconstructed immutable
message. Application binding, episode_commissions, durable
backend, shared method_loop, communication closed guard, base044 and every
scientific reader/calculator remain read-only consumers. If full implementation
tracing exposes a required edit there, stop and return the concrete delta for
root ownership review instead of expanding this scope implicitly.

Stage1 can implement the two new pure modules and tests, freezing interfaces and
examples first. Stage2 wires all listed shared consumers coherently after root
transfer. Stage3 verifies the actual selected pending-decision→native operation→
typed parent admission→saved reconstruction path in one immutable generation.
Pure formatting or small payloads alone do not finish this workload. The full
goal still requires a subsequent actual configured-model numerical paper run.

## Meaningful verification and limits

Verify both simple and composed operations through the actual provider-generation
and authoritative decode paths, including required/omitted/null fields, literal
JSON-looking strings, duplicate/nonfinite/malformed outer JSON and original
conditional/reference schema checks. Prove every actual tool name and host input
schema remains exact, direct invocation without lookup works, and wrong names
receive structured failures. No information request may execute a population.

Run actual pending-decision exchanges with two different contracts, an intervening
own-history lookup, provider loss/compaction and interrupted request/lookup replay.
Assert full recurring science, correct complete selected information and no raw
schema/hashes in model text. Original queries/results/frames/output schemas stay
immutable. Information requests add zero runtime_actions/observations/credit.

Verify parent-defined literal and referenced schemas expand to the same exact
types; preserve different field names, components, mixed interpretation fields,
original source hashes and rejected wrong-role refs. Exercise selected native
population, original C4 interruption/forgery rejection, owner/admitted subsets,
real mode=ro first projection with source/reader/calculator/receive/reprice
forbidden, whole SQL unchanged and one observation per actual completed action.

Finally refresh057's complete child/parent/provider request measurements in the
actual joined generation, verify scientific TASK equality and descriptor/pin
reconstruction, and report configured-provider acceptance/model science only
after an actual run. Do not infer those from current synthetic bytes.

Executed here: two proposal-only pure schema/text scripts, exit0.37 actual
contracts plus a scalar/text edge fixture roundtrip exactly through rendered
text. The illustrative population-only provider schema is627,561→10,291 compact
bytes with all19 tool names and the unchanged host schema. No provider, Store,
episode, controller, source, model, test suite or scientific operation was run.
Only this new059 verification directory was written. No actual boundary wiring,
compact-form compiler, source truth, configured-model extraction, A105 completion,
paper routing, target correspondence or W05 credit is claimed.
