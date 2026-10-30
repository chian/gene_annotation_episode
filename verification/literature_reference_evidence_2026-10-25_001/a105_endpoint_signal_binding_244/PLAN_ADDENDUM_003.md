# Additive schema and private-receipt correction before244 production release

PLAN001's promised component-specific checks were absent from its exact return
schema. Root reproduced a retained_fraction row accepting unit pixel^2 and the
total-amplitude formula. That mismatch is corrected by the exact additive002
schema below;001artifacts remain unchanged. This is still PLAN ONLY. Ownership,
the full fixed goal, pure005dependency, request schema, scientific example and
seven-paragraph TASK do not change.

## Exact schema correction

EXACT_SCHEMAS002 is a copy of001with exactly ONE added node:
`/return_schema/items/allOf`. EXACT_SCHEMA_DELTA002 records the complete literal
added value. It contains ten component-discriminated if/then branches. The base
row retains EVERY original field, explicit required roster and
additionalProperties=false. Its existing required component enum guarantees
exactly one discriminator applies. Each branch fixes that component's EXACT
unit, formula and meaning; unrelated fields inherit the original closed schema.

| Components | Exact unit |
|---|---|
| total_amplitude, corrected_amplitude, additional_amplitude | direction_oriented_pixel |
| retained_fraction, additional_fraction | dimensionless |
| total_amplitude_variance, corrected_amplitude_variance, additional_amplitude_variance | pixel^2 |
| retained_fraction_variance, additional_fraction_variance | dimensionless^2 |

Formula and meaning constants are exactly CELL_CONSTANTS002's entry for the
selected component. The pure241 component schema alone would not fix the unit;
the added explicit unit const is necessary. No calculation is repeated at the
boundary. PAIRED_SELECTED_INPUT002 and OUTPUT002 are byte-identical additive
copies of001: its scientific values and narrow context selections were correct
and need no relabelling or retrospective change.

`communication._compile_closed_schema` will recognize the whole exact registered
literature_endpoint_signal_cells field at depth1 and compare its complete JSON
tree to endpoint_signal_cells_schema(). It will reject altered/reduced unions
or a nested x-source. This finite exception permits the declared recorded type;
generic model-authored schema grammar remains unchanged. The chosen schema uses
base-closed-row + allOf(if/then), NO local or external $ref/$defs. Existing
_validate_form_semantics already visits allOf and applicable if/then branches
and reference annotations after Draft validation. No generic grammar relaxation
or local-resource resolver change is needed for this form. Original registered
alias snapshots/save/recovery rules remain as in PLAN001.

PLAN_SCHEMA_CHECK002 records actual domain.validate_schema checks: the paired
two-row return passes; all10component-specific valid unit/formula/meaning pairs
pass; all30single-field wrong-unit/wrong-formula/wrong-meaning mutations reject.
All inherited base closed fields are asserted identical. This is plan-schema
verification, not an installed selected operation or scientific run.

## Narrow private-receipt rule in the already owned paths

The rule applies ONLY to literature operations handled by this LiteratureEpisodes
binding with rate_population enabled, and ONLY to the new selected endpoint
implementation receipt/its byte-identical aliases. It does not change Tools,
runtime, WorkflowServices, shared method_loop, ordinary public-source permissions,
old barv1data or an episode's scientific continuation.

New storage helper `receipt_access_binding(context, source_ref, representation,
tool_name)` obtains the actual source/selected representation metadata and checks:

1. Direct receipt candidate: source provider is literature.experimental.figure
   AND source version is literature_figure_endpoint_signal_record_v1. Neither a
   provider alone nor a source label containing numbers identifies a receipt.
2. Alias candidate: the representation's actual artifact_ref exactly equals
   a payload or original request artifact of an authentic selected new-version
   endpoint receipt. For source.read, text fallback matches its actual existing
   fallback to original. source.locate's text representation has its original
   no-fallback semantics. A source whose original bytes are public but text_ref
   aliases private receipt bytes is checked for the selected representation.
3. Authenticate candidate ownership from the saved content identity, original
   request hash/run/episode/operation identity and actual selected operation
   outcome linking that exact sheet_ref. Reuse the existing selected-sheet
   ownership relationships; no scientific source reader, parser,241validator,
   calculator or current implementation attestation participates. An advertised
   endpoint record lacking its required selected binding fails with
   literature_endpoint_receipt_binding_invalid; it is not passed to generic
   source readers as an unrecognized public source.
4. Owner means BOTH original run_id and episode_id match the actual receiving
   BindingContext. The owner may explicitly read/locate its own output. A
   nonowner returns the existing normal invalid tool outcome, result=null,
   empty record_refs/changed_record_refs and arguments_or_reference feedback
   code literature_endpoint_receipt_private. Knowing/admitting sheet_ref, even
   all requested scalar rows, does not admit original coordinates/caption/
   extraction/matrix/implementation JSON. The required safe scalar view remains
   available through the normal typed requested-row path.

Candidate/index discovery uses SELECT on existing tables only, guarded by
sqlite_master existence checks. New adapter construction, discovery, composer
and cold reads create NO tables or bindings. The new private artifact index is
derived only from actual saved selected endpoint operations; it reads original
saved custody artifacts/metadata, not source science or provider traffic.

LiteratureEpisodes._tool_arguments invokes this helper for source.read and
source.locate after original schema/page checks and BEFORE execute_tool. Thus
neither a raw window nor locate match/context reaches the service, own outcome,
receipt admission or next prompt on denial. The existing invalid-attempt path
records specific repair feedback; it adds no completed scientific observation,
automatic retry, approval or stopping rule. Owner access still goes through the
ordinary original source operation. Non-endpoint/public original sources and
aliases of public originals pass this additional check unchanged.

There is also an actual anchored-reference alias path: a source-reading owner
can commit an exact source_subject/reference witness through ordinary reasoning;
state.query can later return that record's anchor/label. The new storage metadata
predicate recognizes only records whose actual source_ref/anchor/visual_anchor
source or artifact binds the SAME private endpoint receipt described above.
It does not classify arbitrary labels or original-paper anchors by their numbers.
Exact-ref state.query checks those selected record metadata before dispatch.
Paged state.query verifies its actual read-only result before returning it; if
that page includes a nonowned private receipt-derived record, this scoped
operation returns the same normal invalid feedback with no exposed rows/refs.
The attempted page can be repaired explicitly. No generic state-query policy,
new automatic query or substitute scientific work is introduced. Merely reading
an endpoint source's ordinary provider/version/artifact metadata does not expose
its implementation JSON and need not be prohibited.

The endpoint renderer additionally withholds private receipt-derived aliases
from automatic working-record/historical/lookup closure using actual receipt
bindings. It continues showing exactly admitted numerical rows and their narrow
source-context fragments. Original-source anchored aliases stay available when
explicitly requested; their existence does not authorize automatic expansion of
a narrower numerical return. Owner API access does not insert raw host IDs or
implementation bookkeeping into the recurring TASK.

This is a source-custody boundary for a specific derived return record, not a
scientific acceptance gate. Operations outside the owned LiteratureEpisodes
path are not claimed protected by this increment. Root need not approve a
generic Tools/runtime extension to implement the requested narrow rule.

## Added verification after release

After an ACTUAL selected endpoint population and normal typed closure, test a
different literature recipient owning only the admitted requested fraction:
direct source.read and source.locate on its sheet_ref reject before byte access;
original owner read/locate succeeds; explicit new original-public-source reads
remain allowed. Test payload and request artifact aliases, representation-specific
text aliases, authentic anchored-reference aliases via exact/paged state.query,
forged/missing selected bindings and a public original alias containing numbers.
Spy on underlying service/source IO to establish which action really executed.
Check invalid feedback, unchanged completed-action/observation/receipt counts
for rejected attempts and ordinary single observations for successful reads.

Retain typed projection and every automatic renderer subset test from001,
including raw receipt JSON/alias sentinel coordinates and covariance. Repeat
FIRST read-only composer tests with the custody helper/alias index present and
no tables/attestation/scientific IO/receive writes. Add the30schema mutations
through literal and registered forms, actual report admission and saved-schema
reconstruction, preserving all required new closed fields.

Controlled004 remains only a generic engineering probe with explicitly scripted
data. It is NOT an actual installed endpoint typed-delivery leakage test; the
new selected endpoint/recipient tests above are still required after release.
The original001–003probe failures and root's original schema-mismatch finding
remain preserved. No production or test file has been edited by244.
