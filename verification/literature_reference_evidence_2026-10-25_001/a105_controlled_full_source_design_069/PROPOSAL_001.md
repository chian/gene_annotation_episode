# Full source design069 — proposed, not implemented

This packet supplies the next shared-stage/full-v2 implementation interface and a
separate active-companion proposal. It changes no production module, test,
source paper, model call, workflow, live run, credit or controller. Root accepted
the bounded068 pure calculator, not this source design or a scientific active
reconciliation policy. The complete literature goal remains unfinished.

The ten retained axes are A101–A108, A110 and A111. This is one source-response
component within A105. No A101–A104 grader, A107 computational grader, target
correspondence, final annotation aggregation or W05 work is included.

## Three responsibilities and the concrete question

The investigation determines what the experiment measured, on which molecule,
under which conditions, and what comparison and limitations the source supports.
The numerical sheet is the twelve-cell `controlled_response_owner_sheet_v2`.
The source functions populate its parsed input; accepted068 separately populates
the sheet. Source records and provenance do not substitute for numerical cells.

For fixed primitive order [protein_condition1, empty_condition1,
protein_condition0, empty_condition0], the coefficients are [1,-1,-1,1]. All
four scientific arms and actual applicability remain necessary. Present arms
with missing numbers differ from absent scientific arms. Known equal physical
owners group before their numerical operands are required. An established B
group can cancel with coefficient zero without selecting a B representation.

The source reader must not run008 `_resolve_control_alias` in v2: that function
turns disagreeing unused numeric readings into a scientific reuse conflict.
068 deliberately retains canceled numeric conflicts as qualifications. A real
source interpretation of conflicting owner, endpoint or actual applicability
remains a scientific limitation; arithmetic does not resolve it.

## Exact public and host boundaries

`API_001.json` declares all signatures. Preserve the four original008 public
functions, their exact v1 schema/results/errors and detached-copy behavior.
Existing historical pins are read-only. The new public v2 module has exactly:

```
controlled_response_v2_arguments_schema() -> dict
validate_controlled_response_v2_selection(arguments) -> dict
read_controlled_response_v2_inputs(arguments, *, read_source) -> dict
validate_controlled_response_v2_extraction(arguments, extraction) -> dict
```

Its request is the byte-exact061 `SELECTION_SCHEMA_V2_001.json`, copied as
`SELECTION_SCHEMA_V2_001.json` here. All original source, context, meaning,
uncertainty, covariance and model nominations survive, including axis.scale.
Do not feed v2 into v1 validation or import runtime schemas from verification.

Add these host stages to the shared source module, with one authoritative
implementation for meaning, uncertainty, source-C and saved-science logic:

```
open_controlled_response_sources(arguments, *, read_source) -> SourceContext
read_controlled_response_arm_science(context, selected_arm) -> ArmScience
read_controlled_response_text_measurement(context, selected, *, endpoint) -> MeasurementReading
finish_controlled_response_arm(context, arm_science, *, measurement) -> ArmExtraction
finish_controlled_response_inputs(context, *, arms) -> SourceExtraction
validate_controlled_response_saved_science(arguments, extraction, *, measurement_checks) -> SourceExtraction
```

`SourceContext` is an opaque context-managed HOST object. Its public methods are
`read_source(source_ref, representation)`, `close`, `__enter__`, `__exit__`.
It validates the whole v1/v2 request, records its immutable semantic profile,
prefetches the complete closure, and authenticates every selected witness even
if later source C or a graph is unsupported. Stages reject selections or staged
objects from another context. No callbacks, contexts, profiles or paths are
model-selected inputs. Context cleanup releases decoded frames on all exits.

`ArmScience` is exactly the corresponding `$defs/ArmScience` declaration.
`MeasurementReading` is a host value with exactly `selection`, `extraction`,
`operand_projection`, `unit_semantics`, `exact_response`,
`source_observation_id`, `graph_details`. Its detached payload types are the
selection, MeasurementExtraction, numeric subset of O_Arm, UnitCarrier,
ExactResponse, nullable ID, and nullable GraphResult in the extraction schema.
Stage ownership tokens remain host-private and do not enter the saved record.

The text constructor uses the authoritative original text parser and exact
source unit records. The graph constructor calls063
`read_controlled_response_rate_figure` with the original measurement and complete
declared image roster through the prefetched cache. `graph_details` now retains
the COMPLETE closed063 result, correcting065's insufficient scale/literals-only
proposal; `arm.measurement` must equal `graph_details.measurement` exactly.
This duplication is an equality-checked record, not a second interpretation.
It retains the actual graph outcome, image roster, unit, native projection,
axis literals, scale and pixel provenance needed for detached reconstruction.

`finish_controlled_response_arm` joins the selected reading BEFORE reported
uncertainty conversion. `finish_controlled_response_inputs` resolves
relationships, full source C, explicit owner projection, model support and
actual068 parsed inputs; it calls no sheet populator. Shared v1/v2 profiles
retain the existing v1 alias/covariance behavior versus the explicit v2 owner
delta. Mechanical parameterization is not permission to infer science.

## Complete source closure and exceptions

Traverse the ORIGINAL complete request, never a v1 projection. Include root
source_ref/original; every nested source_ref with explicit representation or
original default; every original_source_ref/original; ALL declared selected and
original images, including unused image nominations; graph tick/unit/axis.scale
witnesses; every context, meaning, owner, uncertainty and source-defined-unit
witness; requested variance/model witnesses; covariance source/original and all
its nominated label/owner/correspondence witnesses. Deduplicate only identical
(source_ref, representation) pairs, with deterministic sorted order as008.

Call the actual provider exactly once per pair before geometry helpers or063.
Validate exactly {artifact_ref: nonempty string, content: built-in bytes}.
Reject one artifact handle bound to different bytes across ANY closure pair.
The cache has no fallback acquisition. Helpers may ask only for prefetched keys.
Graph063 may build its own subset roster from this cache; this does not invoke
the original provider again. The saved root roster must equal the exact closure.

PermissionError, authorization/scope ContractError, wrong source quotes, clipped
tokens, malformed callback successes, unexpected exceptions and unselected
reads are direct errors. They must not be caught by a geometry helper and
reported as missing science. Explicit ENOENT/EIO/ETIMEDOUT and EOFError are the
established008 availability contract. Retain the original unavailable outcome
and diagnostic; translate cached EOFError to EIO ONLY at063's cache callback
boundary, because063 does not accept EOFError. Do not alter063's public contract.

Authentic unsupported syntax, unsupported graph scale/unit/image, unreadable or
ambiguous numeric reading, censored measurement, unavailable dependencies, bad
source C and unresolved scientific meanings are scientific/capability partials.
Keep every independently acquired fact. An unsupported format does not excuse
authenticating its nominated witnesses. Never make a missing value zero or one.

## Units, reported spread and a present missing-number arm

The tagged `UnitCarrier` is exactly {kind:text,record:TextUnitRecord} or
{kind:graph,record:GraphUnitRecord}. Original008 and063 unit records themselves
retain their original fields. A graph unit is authenticated by its actual graph
axis witness, not a fabricated text UnitSelection. Source-defined U/mg remains
unsupported in063; this design introduces no implicit U conversion.

Factor the uncertainty assembly into one implementation using actual parsed
unit semantics. Its explicit printed-unit check receives canonical_unit,
raw_unit and source_defined_unit from the real carrier; it must not call the
text unit reader on an AxisLiteral. Conversion is exact source quantity times
exact_scale, then a separately checked finite display. SD, SEM, CI, confidence,
count, repetition basis and fit basis keep separate meanings. Neither count
nor SD supplies a joint covariance, independence or known variance.

V2 `reported_uncertainty.effective_unit` uses the tagged carrier. A graph ordinate
in nmol/min and source SD1.2 with same_as_response yields SD0.0012 umol/min.
A reported CI[8,12] yields [0.008,0.012] umol/min. Those numbers do not come from
pixel bounds. Graph digitization still carries its own conditional domain.

For a PRESENT source arm whose measurement is null or unavailable, retain all
ArmScience and project a present068 Arm with status=missing, null numeric fields,
relation=none and source_observation_id=null. Whole scientific arm=None is
reserved for the original absent-arm nomination. Authenticated ambiguous,
conflicting or unsupported nominations require a retained deterministic
nomination identity when068 needs a nonnull source_observation_id. That ID
identifies the actual retained reading attempt, not a successful measurement or
an independent physical observation. Never invent an authenticated identity
when its entire dependency is unavailable. Unreadable text may remain unsupported
with its actual fragment identity, consistent with008's distinction.

## Exact original-N covariance and PROVIDED owner projection

Read original structured C using008's strict exact JSON lexer. Retain raw UTF8
text, numeric lexical tokens, exact rationals, full original variable roster,
indices, decoded labels, exact label/unit/description token witnesses, actual
source model and status. Duplicate labels are legal. Index equality, a matching
decoded string, and physical owner equality are three different relationships.

Validate original N-by-N shape, finite lexical validity, EXACT symmetry and PSD
before any submatrix projection. All original rows are checked, including
unbound or canceled rows. Invalid FULL C leaves source_validation=invalid,
projection_state=source_invalid and calculation_covariance=null. A valid A/C
submatrix does not repair it. Singular PSD and zero variance are legal data,
with the calculator's separate positive-V requirements for precision/models.

For every nominated binding, authenticate the label at the actual selected
original variables[index].label token; out-of-range or another equal-label
token is a direct selection error. owner_witness must occur among that exact
role's physical-observation witnesses/canonical witness. Known binding requires
actual known role owner, available exact label and owner witnesses and actual
same correspondence. Missing canceled B bindings do not erase established A/C.

Create `provided_owner_projection` in increasing ORIGINAL source-index order,
one entry per established owner with exactly physical_observation_id,
source_variable_index, roles and native_registry_unit. Every known binding
remains in `bindings`, including aliases and unresolved/conflicting ones. A
single source variable bound to different known owners is a binding conflict.
For one owner bound at different original positions, require compatible known
unit dimensions and equality of unit-normalized FULL original rows/columns,
not merely the selected submatrix. Retain all original positions; choose the
least original index only after that equivalence is established. This is
canonical indexing, not favorable numerical-reading selection.

Project all usable explicitly bound PROVIDED owners, including canceled owners
when actually provided. Do not trim an invalid supplied row. A null canceled
mean-unit is permitted: the real source-C variable's independently witnessed
unit supplies its covariance dimension. An explicitly incompatible bound unit
remains a conflict. Missing active coverage stays incomplete; no zeros or
independence are supplied. Do not confuse the known required ID set with complete
active coverage when an active owner is unknown.

Use OwnerCovariance, with no primitive_order and unique owner IDs. Preserve
matrix entries in selected native row/column unit products;068 applies BOTH
unit factors. Exact source PSD and the finite decimal projected matrix's PSD,
range and repeated-owner equivalence are separate validations. Projection
rounding remains visible and cannot silently authorize the optional normal
model. Genuine A/C-only source C is the actual original two-variable document;
it is distinguishable from FULL-invalid C and from a valid FULL document with
only A/C bindings. The saved record retains all three situations faithfully.

Requested model witnesses, source model literals and effective model are
separate. Joint-normal support must actually concern the source-means/owner
scope whose marginal is used. A known full joint-normal model can support its
explicit active marginal; an SD+count assertion cannot. Derive variance status
and model kind from matching requested/source support and projection validity.
The source reader must not impose065's old blanket model-none rule merely
because canceled B is graphical.068 checks ACTIVE readings, positive known V,
actual scope and exact/nonapproximate/uncensored means for S/B. Graphical active
readings keep usable effect/V but leave S/B unresolved.

## Closed saved validation

`EXTRACTION_SCHEMA_V2_001.json` is the exact closed detached shape proposed for
this tranche. It replaces the prose-only008 type declaration. Every object has
declared fields; field-specific interpretation enums and meaningful cross-field
checks additionally follow the original selection. calculation_inputs is exactly
actual `controlled_response_owner_inputs_v2`, not frozen006 and not an envelope.
No new numerical sheet implementation is hidden in the reader.

One shared saved-science validator, with closed text/graph measurement checks,
must verify selection equality, exact closure, image roster, artifact/digest
bindings, witness/locator relationships, meaning canonical IDs, original numeric
lexemes and unit factors, present-versus-absent arm projection, original reported
spread/count/CI meanings and effective UnitCarrier, all relationship selections,
exact original-N C validation, ORIGINAL token positions/owners, provided owner
scope/order, full-row alias consistency, finite C, requested/source/effective
model, representation records and exact actual068 parsed input projection.

For graphs, validate COMPLETE063 saved shape and measurement equality. Rebuild
the ORIGINAL identity_record with exact keys version,selection,images,literals,
scale,unit,pixels and063's sort_keys=True, ensure_ascii=True, allow_nan=False
serialization. Verify original/crop mapping, selected recipe/runs, upper/lower
terminal clipping, signed exact calibration, exact native ordinate/domain,
outward finite projection, actual unit/scale support and module identity. Saved
algebra can check those relationships; it cannot prove pixel counting from a
digest. Never decode, count pixels, call a source callback, reselect a canonical
reading or call a model during detached validation.

Uncertainty assembly and its saved projection must share the same deterministic
semantics, not independent rewritten formulas. V1's legacy schema/output/error
contract remains exact under the internal profile; additional v2 obligations
must not silently strengthen or repair v1 behavior. Original native custody
still binds the actual request, callback outcomes and immutable saved extraction.
A self-consistent replacement JSON document is not that custody proof.

## Reconciliation and the demonstrated active-companion gap

V2 records each known/unknown owner's original roles, readings, exact domains,
net coefficient and qualified reconciliation state. Canceled B may retain
disagreeing or missing domains without selecting one. Active single readings
or exact equivalent normalized readings can populate the existing068 input.
Compatible-but-distinct active representations remain a specific unresolved
scientific/model requirement, not an accepted permanent null policy.

Exact061 permits only ONE measurement per arm. Example: active A is reported10
and its graph is10.05[9.95,10.15]. Both concern the same source owner, endpoint,
normalization and conditions. The graph cannot be placed in empty_condition1
or protein_condition0 without inventing an experimental role.068 likewise has
one reading per role. This is the concrete missing nomination accepted by root
for a SEPARATE additive proposal, not permission to change the v2 base.

`COMPANION_SELECTION_SCHEMA_V3_PROPOSAL_001.json` preserves061's entire base,
changes the version to controlled_response_source_selection_v3, and adds required
companion_readings (possibly empty), each exactly {reading_key,primary_role,
reading: original Arm nomination}. A companion carries full source science and
uncertainty but is never a fifth primitive, new replicate or extra C owner. Keys
must be unique. Its actual known owner, endpoint, normalization, subject/construct,
condition and arrangement must correspond to the declared primary role, with
original witnesses checked. Unknown correspondence stays unresolved; a different
experiment must be investigated as another experiment, not mislabeled a companion.

V3 extraction retains every primary and companion ArmExtraction, exact source
closure and the original C. The closed proposal extends the reconciliation
reading records with each companion's reading_key. A ready projection can feed
068 ONLY when no active alternative is discarded or silently reinterpreted.
An unresolved active group returns projection_status=unresolved_active_reconciliation
and calculation_inputs=null, while retaining usable primary/companion native
measurements and reported uncertainty. This explicit partial must reach the
episode. Do not call068 on a favorable primary, claim a supported final sheet,
or replace a valid raw result with zero. Native raw/alternative delivery and any
new reconciled calculation interface require their own explicit release.

The concrete model question for the owning literature investigation is:
“Do these source representations describe the same measured mean, and does the
source establish that the printed point is authoritative while the graph is a
conditional digitization of it? Which reported rounding, graph selection, unit,
endpoint, normalization or source revision differences explain the alternatives?”
Return original source witnesses and allowed same/unknown/conflicting meanings,
source-authority/rounding support and each reading domain; do not return an
invented mean, SD or reliability grade. For example a supported future policy
could retain a common reported point only if all exact reported points agree
and lie in EVERY graph domain, independently of effect sign. That policy is
UNADOPTED here. Overlapping graph domains have no uniquely measured midpoint;
their intersection is not sampling precision. A reported point outside a graph
domain is initially incompatibility of retained reading assumptions, not
automatically a biological contradiction. Reread/repair is the episode's choice.

Actual active reconciliation, its model support, any corresponding calculator
extension and its native partial/ready typed return remain REQUIRED unfinished
work. This design does not redefine success as the easy single-reading subset.
063 supplies nominated signed linear-bar reading only: no OCR, densitometry,
automatic diagram/axis recognition or representation selection is implied.

## Constructed numerical sheet, not primary evidence

`CONSTRUCTED_SOURCE_CASES_001.json` has fourteen artificial source cases, complete
nominations, hand-projected actual068 inputs and ACTUAL068 sheet outputs. It is
not an execution of a new source reader. The source matrix has four original
variables in order[B,C,A,unused], with duplicate labels for B/C, to distinguish
actual token positions from labels and from four primitive roles.

For A10, C8 nmol/min; B printed4 and graph4.05[3.95,4.15]:

| Numerical cell | Operation and evaluation | Value |
| --- | --- | --- |
| four raw responses | original parsed source magnitudes, separate representations | .010,.004,.008,.00405 umol/min |
| condition1 controlled response | A minus its applicable B | .006 umol/min |
| condition0 controlled response | C minus retained graphical B | .00395 [.00385,.00405] umol/min |
| controlled response difference | group owners in A−B−C+B; B coefficient0 | .002 umol/min |
| contrast variance | active g=[1,−1], actual C_A/C=[[.16,.03],[.03,.20]] (nmol/min)^2; gCgᵀ | 3e−7 (umol/min)^2 |
| contrast standard uncertainty | sqrt(V), source joint-means uncertainty | .0005477225575051661 umol/min |
| contrast precision | 1/V, only for positive V | 3333333.3333333335 (umol/min)^−2 |
| source profile log ratio | e·abs(e)/(2V), conditional known-normal active means | 6.666666666666667 |
| source signed index | tanh(S/2), signed model evidence, not probability of function | .9974579674738373 |

The fixture supplies synthetic C/model premises explicitly; no source discovery
or real variance claim follows. The exact arithmetic table is generated by068;
display precision is not a new formula. d1−d0=.00205 would be the WRONG owner
effect because it subtracts independently rendered B alternatives. Missing both
B numerical readings and units retains e/V with canceled qualifiers. B4 versus5
also retains e/V conditional on genuinely established science. Actual conflicting
physical-owner meaning blocks e. Unknown active owner can leave a conditional
four-term magnitude while V stays incomplete even when all listed known IDs are
covered. Graph active A preserves its physical-unit SD/CI/source C but excludes
the optional normal model. FULL-invalid C is not rescued; true A/C-only source C
is valid different evidence. Zero V and source/projection numeric range remain
separate results. These cases do not supply independent experiments or credit.

## Verification and ownership

`IMPLEMENTATION_AND_NATIVE_HANDOFF_001.md` owns the next implementation/test and
complete native-consumer contracts. Declaration reconstruction checks schema
closure, actual068 interface identity and original061 equality. Passing these
checks proves design consistency only. The fourteen arithmetic executions prove
only accepted068 behavior on HAND-projected fixtures. No new reader, saved v2
validator, native selected operation, typed C1/C4 delivery, source-free runtime
reopening or configured-model literature path is implemented by this packet.
