# Source-bound four-cell binding population: proposed interface

Proposal only. No production, test, catalog, prompt, storage, runtime, pin or
live-run file was changed. All source bytes used in the two interface probes
are synthetic. No paper, paper-specific packet, source selection from a live
run, provider transcript or private model history was opened.

This connects the already defined A105 binding-discrimination component to
source selections in an ordinary LiteratureEpisode. It adds no axis, complete
A105 grade, paper classifier, investigation itinerary or annotation-credit rule.
The investigator chooses an experiment and four roles; this operation executes
that choice. The future search-to-component selection connection remains deferred.

## Numerical purpose and supported comparison

The four roles are rr, rt, tr, tt: reference molecular form/reference ligand,
reference form/test ligand, test form/reference ligand, test form/test ligand.
The molecular forms are separately assayed. A ligand tracer and competitor may
coexist without establishing that the two protein forms coexist. A protein
mixture cannot be silently represented as four separate-form assays.

Uniform IC50 or uniform reported Hill-fit Kd, normalized to nM, supports the
existing048 native meanings:

| Public numerical component | Exact meaning |
| --- | --- |
| parameter_rr, parameter_rt, parameter_tr, parameter_tt | Each actual source point or separately retained printed threshold |
| reference_subject_ratio | rt / rr |
| test_subject_ratio | tt / tr |
| interaction_ratio | D = (rt / rr) / (tt / tr) |
| log_interaction | e = -ln(rr) + ln(rt) + ln(tr) - ln(tt) |

Four invented points 5,40,2,4 give within-form ratios8 and2, D=4 and e=ln4.
These are dependent representations of one comparison. Different protocols
remain different; no protein-input ratio corrects IC50. Common-condition claims
require the explicitly supported relationships already enforced by048. Printed
limits remain descriptive threshold arithmetic, never confidence bounds or
points in a likelihood. Opposing limit directions give no invented bound.

The048 twelve-cell calculation also defines V=c'Cc, sqrt(V), S=e|e|/(2V) and
B=tanh(S/2), with c=(-1,1,1,-1). The source-model/covariance reader is unfinished.
This native route therefore exposes only the eight numerical meanings above,
retains the complete private calculation with model=None, and returns explicit
model_input_status=not_supplied_by_native_operation and
model_reader_capability=unimplemented. It does not call an unavailable source
model a paper omission. That remaining required reader is not removed from scope.

## Two concrete interface gaps and the smallest corrections

SYNTHETIC_INTERFACE_RECEIPT_001.json records an actual exit-zero probe of the
current frozen modules, not a scientific-source or Store-authentication test.

1. Public049 requires nonempty witnessed subject/state/experiment in every
   invocation. An honestly unknown state with no witness is rejected as
   interpretation_witness_required. Existing049 image/witness mechanics can
   still authenticate the same invented7.25±0.35 cell without that state.
   The new adapter will reuse those frozen deterministic mechanics directly;
   it will not invent an unknown source label or a witness merely to call the
   higher-level one-context049 interface. No public-helper refactor is needed.
2.048 currently requires a complete uncertainty object and requires a numerical
   confidence level for every CI. A source point with reported CI endpoints and
   an unreported confidence level is rejected even though the native ratios do
   not use that level. Unknown uncertainty interpretation has the same general
   representation problem. Relabeling a reported CI as unreported is incorrect.

Recommended separate, fresh bounded correction ownership for048:

* Permit operand.uncertainty=null, meaning the calculator was not supplied a
  resolved uncertainty description. It is explicitly different from the
  existing statistic=unreported source assertion. The native adapter retains
  the actual uncertainty selections/statuses beside this projection.
* Always validate reported_spread as null or a finite nonnegative number,
  including when uncertainty is null. An unreported parameter cannot carry a
  numerical spread. A real ± magnitude may survive an unresolved SD/SEM meaning;
  it does not become variance or a known sampling model.
* For statistic=confidence_interval, retain the required two ordered actual
  endpoints and permit confidence_level=null. A supplied level must still be
  finite and strictly between0 and1. Existing prohibition on a symmetric spread
  masquerading as a CI remains.
* Keep all other existing dictionary rules, formulas, uncertainty identities,
  model-owner checks and known-normal prerequisites unchanged. A complete CI
  with unknown level remains statistic=confidence_interval with the same
  endpoints and null level. An unreadable interval can use uncertainty=null
  while the witnessed CI claim and all candidates survive in the adapter record.

Meaningful correction tests should preserve the source point and D for unknown
uncertainty and unknown CI level, preserve exact reported SD/SEM/CI distinctions,
reject nonfinite/negative spread and invalid supplied levels, keep default model
cells unknown, retain complete operand-key ownership, and establish unchanged
known-input numerical results. These are proposed changes, not implemented ones.

## Proposed closed source-selection request

Callable: read_binding_interaction_inputs(arguments, read_source=...). The callback
returns exactly {artifact_ref, content:bytes} after caller-owned receipt, scope
and page/source-ancestry authorization. The reader never invents those facts.
No scientific number, covariance matrix, numerical quality category or prepared
numeric table is a direct tool argument.

All structures below are closed and all listed keys are required. Null is
explicit. The full module contract/schema would be frozen before storage coding.

    arguments = {
      version: binding_interaction_source_inputs_v1,
      source_ref, source_kind: primary_source|synthetic_fixture,
      images: [Image049],
      parameter_kind: EnumMeaning(ic50|reported_hill_kd|unknown|conflicting),
      comparison_scope: reported_protocols|common_conditions,
      roles: {rr: null|Role, rt: null|Role, tr: null|Role, tt: null|Role},
      relationships: {name: Relationship for name in048.RELATIONS}
    }

    Role = {
      parameter_kind: EnumMeaning(ic50|reported_hill_kd|unknown|conflicting),
      definitions: {name: Meaning for name in048.ID_FIELDS},
      physical_fit: null|SourceIdentity,
      measurement: null|{
        image_id, cell_region:Box,
        expression: Literal, unit: Literal
      },
      uncertainty: UncertaintySelection
    }

Image049 is the existing source_ref/original_source_ref/integer crop mapping
contract, with actual single-frame PNG/JPEG L/RGB/RGBA validation. Witness is the
existing049 tagged text/image union. A Literal has status exact, ambiguous,
unreadable or conflicting, candidates:[Witness], fragments:[Witness]. Exact
has exactly one candidate, unreadable none, and ambiguous/conflicting at least
two different quotes. Numeric source expressions use the full current binding
grammar; source units are supported concentration spellings. Text spans are
exact UTF-8 bytes; image quotes remain episode-interpreted text on authenticated
bytes/geometry. Unsupported forms remain raw with explicit reasons.

Meaning has exactly status:known|unknown|conflicting, label:null|string,
witnesses:[Witness], canonical_witness:null|Witness. Known requires actual
supporting witnesses and one authenticated canonical witness; unknown has no
canonical witness; conflicting requires at least two distinct source witnesses
and no canonical witness. Null labels are legitimate. It supplies a literal
source description separately from a declared scientific identity. Equal labels
do not establish identity. A deterministic canonical ID derives from the actual
canonical witness locator and meaning dimension. Aliases use the same explicitly
selected canonical witness only when the investigator establishes that mapping.
Unknown constructs/states/conditions produce null IDs, never stable-looking
fabricated known IDs. Own witnesses are retained even when a canonical witness
is reused to express a scientifically interpreted correspondence.

EnumMeaning has exactly value and witnesses. Unknown/unreported meanings may
have no witnesses; substantive known claims require support and conflicting
claims require distinct witnesses. Relationship uses048's existing status
vocabulary and supporting Witness selections. Its canonical output is the
existing source/artifact/byte-span or mapped-image-region witness union. Literal
source text and image extents are authenticated; scientific interpretation is
explicitly attributed to the investigating episode, not proved by the parser.

SourceIdentity has exactly canonical_witness and witnesses. It names an actual
reported physical fit/measurement, not the table cell, construct, preparation,
row number, value or source-label hash. The adapter derives its ID from that
authenticated identity witness. Null means unknown. Table-cell identity is
always a separate mapped original-image locator. Shared controls preserve both
identities across calls; neither distinct cell boxes nor physical IDs establish
independence.

UncertaintySelection has exactly statistic, basis, repetition_basis,
interval, confidence_level, exact_count and minimum_count. The first three are
EnumMeaning using048's meanings plus unknown/conflicting where appropriate.
The symmetric spread is read from the complete measurement expression and is
not supplied again as a number. Interval is null or {literal:Literal,
unit_relationship:EnumMeaning(same_as_parameter|explicit_unit|unknown|conflicting),
unit:null|Literal}. Confidence level and counts are null or Literal. The new
targeted reader parses only complete supported interval/probability/integer
tokens, preserves explicit units/qualifications and missingness, and does not
derive SD/SEM, counts or covariance. A CI's missing level stays null. An
ambiguous/unreadable interval retains all candidates while the calculator's
uncertainty projection is null. Exact/minimum counts remain separate; source
counts never become independent protein preparations by default.

This is one selected same-definition comparison. Known per-role kinds that
differ from the selected common kind remain actual raw measurements with their
own kinds, but are not inserted into that common-kind048 calculation. The
affected comparison is explicitly definition-incompatible. A separately selected
comparison can examine another definition; no automatic family routing is added.

## Reader result and calculation bridge

The closed result retains version, selection, all actual source refs, resolved
image/witness results, per-role literal and scientific meanings/statuses,
canonical calculator inputs, input-unavailable reasons and implementation
dependencies. The repository retains this complete result; the old049 partial
compatibility table is never passed bare to existing binding.populate.

The new reader reuses frozen049 _Inputs image/decode/location/witness mechanics
and the existing binding literal parser, under exact dependency hashes. It
owns the new nullable-context selection semantics, full four-role alias/conflict
check, uncertainty literals and mapping to048. That is a deterministic one-off
operation, with no model calls, hidden iterative workflow or source acquisition.

All four role selections are processed together. Same canonical source cell
with different readings, ligands or declared subject contexts is conflicting.
An unreadable/ambiguous rereading cannot be ignored in favor of an exact copy.
Overlapping boxes alone establish neither sameness nor independence. Actual
original crop mappings use checked pixel equality; arbitrary byte-equal sources
are not automatically common scientific originals. Real ancestry remains the
repository's responsibility.

A parsed source point can survive unknown construct/state/uncertainty.048
receives its real concentration, null canonical IDs and null uncertainty where
unresolved; it retains raw parameter cells and withholds only affected derived
comparisons. A missing/ambiguous/unreadable/conflicting numeric expression maps
to no048 operand, with the specific source status and candidates retained beside
the calculation. Exact n.d. maps to an unavailable source operand and keeps the
literal n.d.; it is never expanded into not-determined or nondetected.

Unknown units preserve the native literal number and raw unit candidates, with
canonical value unavailable. Unknown/incompatible kinds similarly preserve the
raw result without fabricating a common-kind operand. The public raw role view
is projected from the saved extraction so these distinctions are not replaced
with048's generic missing-operand reason. Derived views preserve both the
calculator reason and their role-specific source causes. Native numbers are
never silently treated as canonical nM.

## Prospective files and shared ownership

New files, after root reviews this contract and assigns implementation ownership:

* literature_binding_interaction_inputs.py and its targeted reader tests.
* literature_binding_interaction_storage.py and its selected Store/runtime tests.
* literature_binding_interaction_validation.py and detached association tests.
* An optional small literature_binding_interaction_render.py may isolate pure
  factual rendering; otherwise equivalent scoped functions belong to the shared
  experimental renderer after explicit ownership transfer.

The separate048 correction must have its own fresh owner and frozen delivery.
049/old binding/base044/kinetic047/optical modules remain read-only dependencies.
The bounded input-reader and storage work can be sequential under one assigned
owner, or split only after exact request/result/status interfaces are frozen.
No additional parallel owner is assumed in this proposal.

Later shared additions require explicit ownership transfer:

* C7: append literature.binding.interaction.populate, add optional
  requested_binding_interaction_components, dispatch/repository route and
  literature_binding_interaction_cells fact namespace, include dependency bytes.
* episode_services.py: one lazy repository accessor.
* literature_experimental_prompt.py: mechanically expose the requested-component
  assignment field, select the dedicated admitted-return view and suppress
  unrequested numeric/candidate source expansions.
* The existing parent capability test gets only the additive catalog expectation;
  new integration tests are preferred for this new family.

050 currently owns C7's native-rate operand-information delta. This proposal
does not edit it or assume047's historical full catalog-schema equality still
describes current050 work. No runtime/controller/C4/base044 modification is
proposed. Existing18 operation names and meanings remain; this prospective
addition is one callable component route, not another scoring sheet.

## Durable state and custody

Use a new LiteratureRateRepository subclass with its own operations/received/
delivery tables and a new provider/version. Retain the original run, episode,
operation key, selected tool, scope, assignment, requested components and complete
source selection in the immutable request/signature.

Before bytes are exposed, authorize every actually selected source, original
image, wrapper and text witness against the episode's received refs, scope and
assigned-page ancestry. Preflight unauthorized references as an invalid action;
do not turn an unreceived source into a scientific missing value. Actual read or
decode failures on authorized dependencies remain local source-failure partials.
Retain actual source artifact identities and original parent lineage for all
used inputs. Provider labels or equal bytes alone do not authorize lineage.

One Store transaction publishes exact source-bound references, request/payload
artifacts, numerical output and the original successful operation outcome.
References for image cells/transcriptions use actual source IDs and a separately
saved canonical image locator; they do not fake UTF-8 byte anchors for pixels.
Use stable deterministic publication order independent of sorted JSON keys.
The actual successful operation authenticates all published references/values.

The saved payload contains the full raw/typed extraction,048 input/output,
native public projection, role/relationship bindings, all dependencies and
request linkage. It may retain a derived compatibility-table representation for
explicit later access, but must not claim an invented input-source receipt or
use that representation to erase withheld statuses. No such extra table is
needed for this native path.

## Closed typed return and automatic rendering

Each requested numerical row includes sheet/source references, component,
value, separate threshold, unit, relation/status, formula code, native meaning,
comparison scope, explicit source-vs-implementation unavailable reasons and
the four role metadata structures. There are eight supported component codes;
requesting the unimplemented model-dependent cells is an explicit capability
error, not an empty scientific result.

Per-role metadata preserves:

* Exact source state: not_selected, parsed, reported_unavailable, ambiguous,
  unreadable, conflicting, unsupported_expression/unit, or source_unavailable.
* Witness/candidate/fragment/canonical-cell references, interpreted subject,
  construct, state, preparation, ligand/tracer, readout/normalization/conditions
  statuses and canonical-definition references. Physical fit is separate/null.
* Actual parameter kind, unit/qualification status, uncertainty statistic/basis,
  exact versus minimum count meanings and specific incomplete-field statuses.
* Native/canonical numerical values, parsed alternative candidate values,
  spreads, CI endpoints/level and counts ONLY on the corresponding explicitly
  requested raw parameter row. Other rows retain statuses/references and
  delivery_status=not_requested with those numbers null.

All form fields are declared finite enums, numbers, booleans or actual typed
references, with closed nested objects. Raw quotations/unsupported strings stay
in referenced immutable evidence records; there is no unrestricted findings or
instructions field. Parsed ambiguous alternatives remain explicitly candidate
values, never a chosen measurement or an average. Their raw witness references
remain even when a candidate cannot be parsed.

The renderer displays the scientific four-role meanings and only admitted
numerical rows. It withholds automatic expansion of raw numeric/candidate
references and broad overlapping source labels. Text overlap uses actual byte
anchors; image overlap uses actual original-cell regions where available.
Missing location metadata suppresses only the affected source's expansions.
Safe unrelated labels remain available. Later explicit source.read/image.view
access is preserved. Source-cell/fit hashes, operation identities and software
fingerprints do not enter model-facing text.

This renderer adds no scientific TASK. Necessary binding-discrimination TASK
drafts remain separately printed for user feedback before adoption. Callable
descriptions explain exact operands/capabilities; they do not dump the numerical
sheet or determine the investigation's next action.

## Exact possession, admission and reconstruction

Reuse unchanged base044 fact_cells/validate_fact_values/receive_cells/
received_cells. Own selected output authorizes its selected projection; another
episode holding the sheet receives only the exact admitted row subset. C7's
existing validation checks the reporting child; the distinct parent records
its admitted subset. Original successful runtime form/contract authentication
must reject a forged receipt even with a forged matching delivery digest.

Detached validation checks closed saved structures, exact original selections,
literal/witness/canonical associations, qualification and status consistency,
source-cell versus fit ownership, units, role reuse, raw cells, formula codes
and original output linkage. It must never reread source pixels/text, parse
literal syntax, convert a new value, rerun048, infer covariance or call a model.
Immutable original-operation artifacts supply numerical truth. Published binding
records and original source metadata supply custody; source artifacts are not
reacquired on reopening. Actual read-only SQLite reopening must preserve all SQL.

The ordinary runtime owns action execution, receipts, parent credit projection
and continuation. One selected population produces one own-action observation.
Internal primitive reads/calculations, publishing references, constructing a
typed form and reconstructing it create no additional observations. Parent
admission completes its original child action; child-internal work never becomes
multiple parent observations. This path writes no scientific assessment or W05
annotation credit merely because parsing succeeded.

## Bounded verification and honest completion boundary

After implementation is assigned, verify the actual supported path:

1. Source-only selections, units/limits/±/CI/counts, unknown context and incomplete
   uncertainty; useful raw values and the unaffected within-form pair survive.
2. Four-role original/crop identity and conflict; shared controls across calls,
   reused table cell versus actual physical fit, no inferred independence.
3. Actual source receipt/scope/page ancestry and authorized local read failures;
   no unauthorized source is silently accepted as a scientific partial.
4. Real selected LiteratureEpisodes/shared-loop population, exact requested
   typed rows at two boundaries, one selected action per observation and zero
   annotation credit from fixture acquisition/calculation alone.
5. Actual provider text for raw-only and derived-only returns, including broad
   and off-page text/image witnesses, uncertainty/candidate number suppression,
   preserved scientific statuses and safe unrelated source labels.
6. C4 interruption rollback, original contract/subset authentication, original
   successful report repair, tampered snapshot/binding/receipt rejection and
   actual read-only reopen with source/reader/calculator/model functions forbidden.

These synthetic/controlled checks do not prove visual transcription correctness,
scientific interpretation, source sampling/censor models or live-model component
selection. A primary-source example and an actual configured-model investigation
remain separate required demonstrations. The full A105 validity/isolation/
relevance/dependence compilation, later appropriate literature responsibilities,
and the source-model reader remain unfinished. A101/W05 aggregation and the
deferred search-to-component routing link remain outside this workload.

## Inspection record

Read the full active goal, root AGENTS/GOAL, EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION,
TASK_AND_STEERING and complete W04 amendment. One initial combined tool output
truncated; TIME_AWARE_ESTIMATION and TASK_AND_STEERING/W04 were reread in full.
Read full048 calculator/tests and proposal/refinements/handoff; one combined
code display truncated and the omitted calculator tail/test opening were reread.
Read full049 module/tests/proposal/handoff; existing binding reader, calculator,
model inputs, model calculator, both storage modules and scientific prompt;
base044 rate storage; full current C7, services, experimental renderer, kinetic047
storage/validator and final006 handoff; full C4 admission and communication.
Read complete relevant runtime methods for selected ordinary execution, selected
child construction/delivery, received facts, report validation/admission,
redelivery, form closure, receipt publication and observation construction.
The entire4197-line runtime was not read and is not claimed reviewed.
Latest039/040 human direction was read last before this proposal. No primary
source/paper packet was opened, so no per-paper reset was required for052.
