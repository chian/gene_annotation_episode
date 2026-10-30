# Controlled-response targeted source reader: proposal only

No production/test/shared file is changed. Calculator/test/006 artifacts remain
frozen. The proposed reader fills the accepted parsed four-arm contract; it does
not calculate a sheet or choose a scientific investigation. This remains an A105
experimental component within ten axis sheets. One paper can supply several
experiments/claims and applicable components. Routing, A101 and W05 are separate.
This worker read no paper, retained scientific packet, primary-source case or
provider history, and made no search or scientific model request.

## Proposed release and concrete interface

Future ownership, subject to root review: NEW
gene_annotation_episode/literature_controlled_response_inputs.py and NEW
tests/test_literature_controlled_response_inputs.py. No existing file ownership
is requested here. Proposed public functions:

    controlled_response_arguments_schema()
    validate_controlled_response_selection(arguments)
    read_controlled_response_inputs(arguments, *, read_source)
    validate_controlled_response_extraction(arguments, extraction)

The first validator checks closed selected arguments and semantic nomination
relationships before any I/O. The reader returns a detached JSON-safe extraction,
including calculation_inputs with the frozen controlled_response_inputs_v1 shape.
It never calls populate_controlled_response or any other scientific calculator.
The detached validator checks original selection/retained extraction association
without source acquisition or recalculation of a sheet. A later selected native
operation will invoke the reader and calculator separately; none is wired now.

Detached validation establishes saved consistency only. Original runtime custody
must bind the actual selected request, admitted sources, responsible operation,
immutable extraction and output; hashes/quotes supplied by a detached record
cannot independently authenticate those facts or authorize access. A self-
consistent fabricated record does not become source evidence by passing this
validator. Actual future reopening/typed-subset ownership still needs its native
runtime binding and tests, and does not reacquire source or reinterpret science.

SELECTION_SCHEMA_007.json is the complete proposed closed selected-argument
schema, not an installed operation. Its root fields are exactly:

    version, source_ref, images, arms, relationships, covariance,
    variance_status, model_kind

version is controlled_response_source_selection_v1. source_ref is the actual
received/scoped primary document reference; all supplemental witness/image/model
sources remain separately referenced. Scientific values, thresholds, spreads,
counts, matrix entries, normalizing masses and calculated ordinates are never
selected arguments. Selected numerical fields are byte/character offsets,
source-variable indices, pixel positions and mechanical pixel recipe settings.

### Source witnesses and canonical meanings

TextWitness is {kind:text,source_ref,representation,start,end,quote}. Outer spans
are exact UTF8 bytes in original|text retained bytes. NativeTextWitness omits only
kind, matching existing guarded scalar/unit selectors. ImageWitness is
{kind:image,image_id,region,quote}, using frozen049's actual original/crop map.
Image quotation remains investigating_episode_interpretation, authenticated as
image_bytes_and_geometry_only, never OCR or proof of textual/scientific truth.

Each Meaning has exactly status,label,witnesses,canonical_witness,
canonical_correspondence. Status is known|unknown|conflicting. Correspondence is
{value:same|unknown|conflicting,witnesses}. A known resolved ID requires an actual
authenticated canonical witness and explicit same interpretation; otherwise the
resolved state/ID is unknown/null or conflicting/null. Known interpretations
need a witness; conflicting needs two distinct actual witness locators. Own
witnesses survive alias selection. Labels are retained interpretations, never
identity evidence or numeric inputs.

Canonical IDs are generated only in the reader, from the meaning dimension and
the authenticated canonical locator. Text locator includes source_ref,
artifact_ref, actual byte hash and byte extent; representation aliases of that
same artifact/extent can share identity. Different source contexts or identical
labels/text do not establish identity. Image locator uses actual original source,
artifact/hash and mapped region. Condition aliases therefore require explicit
source-bound correspondence; spelling similarity never supplies it.

The physical_observation Meaning names the actual observation/fit mean, not
merely a shared preparation. It is separate from source_observation_id, generated
from the actual nominated numeric token/unsupported-expression location or
retained graph recipe. Neither one is a count or a new episode observation.

### Arms and finite experimental interpretation

arms has exactly the frozen four roles. Each is null or exactly:

    source_kind, context, protein_arrangement, subject_construct, condition,
    endpoint, normalization, physical_observation, intended_factor_level,
    measurement, reported_uncertainty

context has nullable authenticated subject,organism,genotype,construct,
preparation,experimental_system witnesses. source_kind is primary_source|
retained_extraction|synthetic_fixture, a declared source interpretation whose
authoritative provenance must later be checked by the native source owner.
protein_arrangement is witnessed protein_present|protein_free_control|
empty_vector_control|other_specified|unknown|conflicting. The five named Meaning
fields resolve to frozen per-role IDs/states. The reader preserves scientific
unknowns and conflicts; it does not interpret a bare protein name or publication
identity as a common endpoint, construct, condition or normalization.

relationships has exactly the nine frozen fields. condition1_target and
condition0_target are Meanings. condition_levels_relation and
subject_construct_across_conditions are witnessed same|different|unknown|
conflicting. The two control applications are witnessed matched_condition_control|
shared_reference_assumption|unknown|conflicting. control_reference_reuse is
witnessed distinct_observations|same_reference_with_stated_invariance|unknown|
conflicting. nonintended_conditions is witnessed matched|different|unknown|
conflicting; intended_factor is a nullable witness. Projection drops only saved
witness detail, producing the frozen finite relationships, without selecting or
grading their truth. Local pair applicability and e/V/S/B belong to the calculator.

A protein-free control does not automatically have positive assayed-protein mass.
Actual shared volume/lipid or a defined positive paired-reference input can
establish a common basis. Equal rate-unit spelling cannot. An intended condition
change is signal; other cochanges stay qualifications without numerical weights.

### Literal measurement and partials

measurement is null, a source_literal nomination, or the prospective linear_bar
nomination below. source_literal has exactly kind,literal,unit. literal has
status exact|ambiguous|unreadable|conflicting, candidates of native NumberSelector
{witness,number_start,number_end}, and authenticated fragments. Inner offsets are
Unicode positions inside the exact outer quote. Exact means one candidate and
no fragments. Ambiguous/conflicting need distinct actual nominated selectors;
equal numeric readings do not resolve uncertain experiment identity. Unreadable
has no candidate and retains its actual source fragments. No hidden consensus,
favorable candidate or density at a censor threshold is selected.

For each candidate, reuse rate-native _number(role=rate), _unit and
_check_explicit_unit. These retain signed points, recognized strict/non-strict
limits, approximation, actual units and source-defined endpoint-specific U/mg.
No activity/concentration-rate/per-molecule formula is substituted. A complete
source-defined definition must be linked by actual source endpoint witness to
this role's declared endpoint correspondence, not a generic U conversion.

For registered unit scales, pass the parsed native value and its corresponding
RATE_UNITS key to the frozen calculator. Do not convert first and then apply the
factor again. A supporting canonical display can fail numerical range without
erasing a valid native operand: the calculator can still evaluate exact joint
cancellation or another representable dependent quantity.

An arbitrary source-defined scale not representable by a registered native unit
can be converted once to the canonical unit if finite. Preserve raw definition,
native literal and exact rational scale. Any source digits lost in finite
projection are recorded as numeric_projection_rounding; the projected operand
is approximate for the frozen model restriction. An unrepresentable custom
scale/value is a reader numeric-contract limitation, not missing paper data or
an invented zero. No frozen calculator change is proposed.

The exact rounding convention is source-decimal rational versus the frozen
calculator's Fraction(str(projected_float)) interpretation, including the actual
declared unit factors on both sides. It is not Fraction.from_float and does not
classify every0.1 as approximate because of binary representation. Thus source
0.1 and float0.1 have the same interpreted rational; source
0.10000000000000000001 and float0.1 do not. Preserve every original lexeme and
exact rational whenever that roundtrip loses digits. Registered native operands
are compared in their actual native units; a failed supporting canonical display
does not itself create input-rounding or erase the native operand. For C compare
each exact source matrix coordinate, with both source-unit factors, against the
projected finite coordinate interpreted through Fraction(str(float)) and both
pure-unit factors. Source PSD checks use the original exact lexemes; finite
projection checks use exactly the frozen calculator interpretation.

Unknown/unsupported unit retains the authenticated native number and raw unit,
with unit=null in the parsed operand. Native source context/number remain useful
while comparison is unavailable. The same rule does not assign a factor of one.
No measurement selection means measurement_not_selected, never a claim the paper
did not measure/report it. Ambiguous/conflicting map to their frozen pure states.
Unreadable or a complete unsupported expression maps to unsupported with an
actual source_observation_id and a separate exact reader diagnostic; this means
this reader has no numerical operand, not that the source lacked an experiment.
An actual null measurement maps to missing/null source identity. The extraction
retains these different source meanings even where the pure state is coarser.

Malformed shapes, forged quotes, invalid UTF8 boundaries in valid text, clipped
digits/signs/units, wrong declared image mapping and invalid selector extents are
repairable argument errors. They reject rather than become source limitations.
Authentic complete unsupported expressions, qualified source syntax, unreadable
fragments, unsupported units and numeric range are retained per dependency.
Known clipped arithmetic/scientific-exponent nominations reject; an authenticated
complete expression outside the literal grammar returns unsupported. Complete
unfamiliar syntax has no point interpretation; preserve the outer field witness
and explicit capability diagnostic rather than guess a number.

### Reported uncertainty is separate supporting evidence

reported_uncertainty has exactly statistic,magnitude,interval,unit,
unit_relationship,confidence_level,count,repetition_basis,estimate_basis.
The statistic is witnessed sd|sem|ci|unspecified|unreported|unknown|conflicting.
Magnitude/count are nullable native NumberSelectors; interval is a nullable
exact bracketed CI selector; confidence is a nullable exact percent witness.
Unit is nullable native/defined UnitSelection; unit_relationship is witnessed
same_as_response|explicit_unit|unknown|conflicting. Repetition basis is witnessed
biological_preparations|technical_measurements|unspecified|unknown|conflicting;
estimate basis is fit_to_averaged_curve|between_fitted_parameters|unknown|
conflicting. Each source piece is independent and may be missing or conflicting.

Reuse released055 _count_reading, _interval and _confidence, and rate-native
spread/unit guards. English-cardinal counts, qualified thresholds/ranges,
not-positive and unsupported count readings keep their exact source status,
notation, relation and witness. A reported count is not an independently prepared
sample count unless its separate source meaning establishes that. Reading SD,
SEM, CI, a count or the word noise never constructs C or a normal model.
Unsupported/qualified CI/confidence and incompatible global/local descriptions
preserve independent valid pieces plus the finite diagnostic. No kind mismatch
erases an actually reported spread or changes it to unreported.

The actual compatibility probe found a current released055 limitation: the
complete exact source confidence literal95% followed immediately by a sentence
period raises partial_source_confidence_level. Its selected bytes and punctuation
are authentic. First-stage reuse must retain that as a per-piece parser-capability
partial, not missing scientific confidence or clipped source data. A future
terminal-punctuation wrapper/regex needs an exact additive root-reviewed proposal;
this proposal neither changes the frozen helper nor rewrites source punctuation.

## Acquired covariance: source labels, then witnessed ownership

COVARIANCE_SOURCE_SCHEMA_007.json defines the first supported actual acquired
structured format, controlled_response_covariance_source_v1:

    version, variables, covariance, origin, variance_status, model_kind
    variable = {label,unit,description}

variables is an actual ordered nonempty source-variable list; covariance is its
full N by N joint matrix. Labels/descriptions are actual source strings and may
repeat; indices plus source/context witnesses distinguish them. Source format
contains no future internal host/canonical/measurement hash IDs. This artifact
must already be acquired/received from actual data/analysis; a model constructing
a numeric JSON table to bypass source reading is not allowed. Other formats are
explicit reader capabilities still missing, not a claim that covariance was
unreported. Full raw source artifact/text, numeric lexemes, labels, units, model
status and all source rows remain retained, even if only four role slots are used.

covariance in selected arguments is null or {source_ref,bindings}. bindings has
the exact four roles; each is null or exactly:

    variable_index, label_witness, owner_witness, correspondence

label_witness must authenticate the exact actual JSON label token at
/variables/variable_index/label, including its original quoting/escapes; the
reader's structural JSON lexer records that token's UTF8 extent. owner_witness
must be one of this role's actual known physical-observation witnesses/canonical
witness. correspondence is witnessed same|unknown|conflicting. Known binding
requires same plus actual witnesses establishing the source label/definition's
relationship to that physical observation. A label/index match never establishes
biological ownership or measurement identity on its own.

The deterministic role map m projects Crole[i,j]=Csource[m[i],m[j]], preserving
every selected cross term and the selected source unit per variable. A three-
variable source can bind [P1,E,P0,E] with m=[0,1,2,1]; it is one actual E mean
used twice, not two independent samples. Repeated index requires independently
known equal physical owners and consistent shared values/context. Same index
with unknown owners is unresolved; with declared different owners it is a
binding conflict. Distinct indices asserted to be one actual owner require
consistent exact values and full normalized source covariance rows/columns.
Projection cannot invent identity or independence. No unselected source row
is silently rewritten, pooled or discarded from retained model support.

Read numeric lexemes exactly before finite conversion. Reject duplicate JSON
keys and nonfinite constants as source representation errors; preserve the
original artifact and finite diagnosis. Source shape/order/unit interpretation,
full symmetry and exact PSD are checked without jitter/tolerance. For arbitrary
N, exact rational symmetric elimination with nonnegative pivots and a zero-row
condition for zero pivots checks PSD, including singular shared-variable models.
Only selected variables need known rate-unit conversion, but all source matrix
entries and its full joint PSD are validated. Source matrix units are distinct
from each arm's literal unit and are converted in both coordinates exactly once.

Source-invalid non-PSD/asymmetric/inconsistent-owner data is different from exact
valid source data that cannot fit the frozen finite numeric interface. Lexical
1e-500 is finite source mathematics, not zero: finite-contract failure is a
reader capability. Retain exact source lexemes, and independently validate the
finite projected matrix; rounding cannot turn a singular valid source into a
purported bad experiment. No numerical repair or diagonal-only fallback occurs.
Projection rounding is explicit; unresolved rounding disables the optional
normal model. A nonrepresentable/non-PSD finite projection makes C unavailable
with a representation diagnostic, preserving actual source model facts.

### Requested, source and effective model states

variance_status and model_kind selected arguments are separately witnessed
interpretations; source JSON independently supplies its actual literal statuses.
The reader retains both and does not promote one from error-bar/count wording.
Valid actual known/estimated covariance is passed with that exact status only
when the nominated interpretation agrees; unknown or a mismatch retains C as
source support but leaves effective C=null/variance_status=unknown/model_kind=none
with the actual finite reason. It does not silently choose a new model.

A matching selected none model stays none even if a source offers normality.
A selected normal model requires matching actual source normal-model support,
authenticated model witnesses and no unresolved covariance-projection rounding.
Missing/conflicting/unsupported normal support alone leaves valid source C and
V available but effective model_kind=none. Estimated C can remain estimated
under an explicitly specified normal family; the frozen calculator still refuses
S/B without positive known V and exact uncensored/nongraph inputs. Per-arm
approximation, censoring and graph provenance remain their actual operand flags;
they do not rewrite a separately supported source model family.

Authentic bad covariance produces a retained finite covariance diagnostic,
effective C=null, variance_status=unknown and model_kind=none. Requested fields
and original source fields remain unchanged in extraction. Raw rates, native
units, uncertainty pieces and local pair meanings are never erased. Source
synthetic covariance combined with reported scientific operands is not silently
passed as a reported scientific model: preserve it as incompatible provenance
pending an explicit appropriate scientific source. This is a source/input meaning
check, not a new approval, scientific acceptance gate or credit rule.

## Source authorization, images and graph boundary

read_source(ref,representation) returns exactly {artifact_ref,content:bytes}; its
authoritative caller owns actual received scope/page ancestry/provenance. Before
interpreting any source or invoking frozen049 helpers, validate the complete
argument structure/reference roster and prefetch every selected source/image/
original/model dependency through that callback. Authorization ContractError and
malformed callback records propagate; only explicit I/O/unavailable dependencies
become local finite failures. Cache actual bytes, artifact refs and content hashes.
Frozen049 then sees only this preauthorized cache, so its broad catch cannot turn
a scope violation into missing science. No extra access decision or review gate
is created. A source read callback cannot authorize itself by returning bytes.

Text quotes use _Sources.witness directly. Image format/decode failures become
dependency partials; invalid caller regions/mappings remain repairable errors.
Use only frozen049 geometry/crop/witness primitives, not its binding/table reader.
No current image quotation supplies an exact text rate or an OCR attestation.

The full target still requires graph ordinates. The closed linear_bar nomination
reserves image_id, mechanical bar_selection, and axis tick/unit literal witnesses.
It accepts no scientific tick values or bar heights as numeric arguments. The
first text/JSON reader records/authenticates the nomination and reports
graph_rate_reader_unimplemented; it produces no graph ordinate. This is missing
implementation, not missing paper measurement. Existing rate-unit graph guards
remain unchanged and do not support the branch.

Before implementing graph reading, submit a separate bounded proposal for a new
rate-figure wrapper/pixel-core interface or a versioned helper extension, with
explicit ownership. Axis values must be parsed from authenticated tick labels;
units retain physical and biological denominator meaning. Actual pixel reading
must retain source-image/crop identity, geometry/recipe, nominal signed ordinate
and conditional digitization bounds. Those bounds are never C or biological CI.
No edit of frozen049 or existing figure modules is authorized by this proposal.

## Exact extraction result and partial model

Proposed result controlled_response_source_extraction_v1 has exactly:

    version, selection, sources, images, arms, relationships, covariance,
    requested_model, effective_model, calculation_inputs, diagnostics,
    implementation_dependencies

selection is the original unmodified closed request. sources records each actual
(source_ref,representation), artifact/hash when read, and finite dependency state.
images contains actual frozen049 geometry records. Each nonnull arm records its
original selection, authenticated context/meaning witnesses and resolved states,
every literal candidate/fragment and native/raw unit/definition, separate display
canonical values/range reasons, separate uncertainty pieces, actual source/physical
IDs, frozen calculation_operand and dependency diagnostics. No alternatives are
silently dropped. relationships retains full witnessed source interpretations
and their exact frozen parsed forms.

covariance retains original artifact/reference/hash/text and exact numeric
lexemes; actual parsed variables and model fields; witnessed role bindings;
projection indices and both source/pure units; exact-source and finite-projection
validation states; full source matrix and projected matrix when usable; origin
and finite diagnostics. JSON-safe exact lexemes/rational records, not NaN/Infinity,
represent unprojectable native values. requested_model retains both witnessed
selected meanings; effective_model records only actual accepted source status,
model kind and reason codes. calculation_inputs has exactly the frozen v1 fields,
with native operands wherever possible and the valid projected full covariance
or explicit unknown/null. It is internal output, never selected model arguments.

Diagnostics have exactly code,field,domain,source_refs. Domain is
source_representation|source_binding|reader_capability|source_interpretation|
dependency. No model-composed prose findings or replacement selections appear.
Full exact subrecord fields/codes are in RESULT_INTERFACE_007.json. Any currently
unresolved schema distinction is a proposal issue for root review before coding,
not a claim that the reader already exists or works.

## Reuse, proof and remaining work

The audit fully read current assay source custody, full rate-native reader and
saved validation paths, transport covariance parser, frozen049 visual paths,
figure input/measurement modules, released055 kinetic/count/CI/confidence reader,
and complete transitive partner scalar/defined-unit and binding-reader modules.
Relevant domain identity/object/schema-validator function paths were read; the
whole domain module was not newly read. Optical input was only captured during
discovery, not used or claimed fully inspected. BASELINE_007/008 record exact
current bytes/hashes. The first discovery assumed a nonexistent standalone count
module; capture was completed against the actual released kinetic module and
retained partial snapshots were verified. No failed read is claimed complete.

Source-level covariance custody/parsing patterns can be reused conceptually,
but existing public assay/transport readers require generated measurement keys
inside source data and different dimensions/roles. They cannot serve this
source-label binding or four-role projection. The old public two-arm rate reader
and independent two-arm uncertainty are also unsuitable. No cloning of their
scientific calculator or hidden table/JSON fabrication is proposed.

The synthetic compatibility reproduction uses actual existing source literal/
unit/count helpers and the frozen calculator's public validator. A separate
composition call demonstrates the same e/V interface; the reader does not call
the calculator. These are invented code probes, not a reader implementation,
configured-model extraction, scientific source coverage or installed operation.
After review/release, meaningful source tests must exercise exact schema and
preauthorization; Unicode and clipped/qualified literals; unknown units and
independent uncertainty partials; real label/owner binding and source shared
control projection; exact/finite PSD distinction, covariance/model mismatches,
and graph capability partials. Native selected execution, typed delivery,
masking/subsets, C4 and saved read-only reconstruction remain later shared work.

For NumberCandidate dependency_unavailable, source_locator and raw_expression
are explicitly null. Original nominated source_ref/quote/offsets survive only
in selection; they are not authenticated source facts. No artifact/hash/location
or source_observation_id is fabricated from that nomination. An arm without an
authenticated numerical dependency has calculation_operand=null, while the
ArmExtraction retains all independent context/meaning/uncertainty evidence and
the actual dependency diagnosis. This is a missing computational operand, not a
claim that the source omitted the experiment or that its nomination was malformed.

This proposal stops for root review. The full controlled-response workload and
A105 remain unfinished.
