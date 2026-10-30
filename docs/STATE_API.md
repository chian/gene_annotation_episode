# State contract for the replacement annotator

This is the shared implementation contract, independent of the archived runner.
`domain.REASONING_SCHEMA` and `domain.RECORD_SCHEMAS` define the exact closed
representation. Mechanical validation checks types, references, scope, source
transcription and coordinate mappings; it does not judge scientific truth.

## Public interface

```python
Store(path)                         # context manager; .db is sqlite3.Row connection
store.transaction()                 # one atomic publication; nested SAVEPOINT
store.read_snapshot()               # consistent reads; respects existing transaction
store.artifact(bytes_or_text, media_type="application/octet-stream") -> str
store.get_artifact(artifact_ref) -> bytes
store.create_problem(input_path=None, *, raw_sequence=None,
    molecule="unspecified", role="unspecified", manifest_path=None,
    caller_context=None, format="auto") -> dict
store.register_material(input_path=None, *, data=None, source_ref=None,
    use="evidence", format="auto", **caller_declarations) -> dict
store.parse_material(material_ref, format=None) -> dict
store.material_members(collection_ref, offset=0, limit=50) -> dict
store.material_errors(parse_ref, offset=0, limit=50) -> dict
store.material_read(material_ref, offset=0, limit=12000) -> dict
store.material_member(member_ref, offset=0, limit=12000) -> dict
store.material_header(member_ref, offset=0, limit=12000) -> dict
store.material_annotations(parse_ref, record_ordinal=None, kind="record", offset=0, limit=50) -> dict
store.material_reference(member_ref) -> dict
store.problem() -> dict
store.targets() -> list[dict]        # immutable input subject metadata, never fake CDSs
store.subjects(scope=None) -> list[dict]
store.get_input(subject_ref) -> dict # metadata only; sequence through sequence_ref
store.put(kind, record, *, origin, scope=None) -> dict
store.get(ref) -> dict
store.list(kind, scope=None, limit=100, offset=0) -> list[dict]
store.query_records(kind, scope=None, limit=100, offset=0, *,
    current_only=False, references=None) -> dict
store.validate_scope(scope, parent_scope=None) -> dict
store.scope_contains(parent_scope, child_scope) -> bool
store.coverage(subject_ref) -> list[dict]
store.sequence_mapping(subject_ref) -> dict
store.map_segments(subject_ref, segments) -> list[dict]
store.references(scope=None) -> dict[str, list[str]]
store.current_annotations(scope=None) -> list[dict]
store.current_assessments(scope=None) -> list[dict]
store.reasoning_view(scope=None, limit=100) -> dict
store.reasoning_schema() -> dict
store.commit_reasoning(payload, scope, operation_key) -> dict
```

Scope is `{"subject_refs": [...]}` naming actual immutable input subjects. The
root uses `problem.subject_refs`. Feature/product membership resolves through
actual ancestry; an invented identifier or scope outside the parent is invalid.

## Inputs and derived identities

Original asset custody is separate from mechanical representation and fixed
sequence-target membership. Explicit raw sequence and FASTA target datasets are
supported alongside evidence-only assets and indexed FASTQ evidence. Automatic
recognition does not turn unknown reports or binary files into sequences.
GenBank has native sequence-record intake and source-bound record/feature
assertions, accessible through `material_annotations`; these do not become
current scientific annotations. Metadata-only records retain no invented bases.
Target FASTQ/read-role file collections now bind fixed original read libraries,
with lazy scientific read identities and member-local geometry. Nonsequence
biological target binding remains unresolved; retained evidence does not create
a substitute denominator. The exact APIs, manifest,
partial-result semantics and limits are in [MATERIAL_INTAKE.md](MATERIAL_INTAKE.md).
Read evidence uses explicit packed physical component descriptors and indexed
chunk spans; ordinary selected references still resolve real exact-content
artifacts. No target/credit scope is inferred from this storage representation.
See [PACKED_MATERIALS.md](PACKED_MATERIALS.md).

A supported sequence manifest is:

```json
{"schema_version":1,"entries":[
  {"path":"unknown.faa","format":"fasta","molecule":"protein","role":"protein"},
  {"sequence":"ACGUNN","format":"raw","molecule":"rna","role":"unspecified","name":"fragment"}
]}
```

Relative file paths resolve against the manifest's directory. Molecules are
`dna`, `rna`, `protein`, `unspecified`; role is a separate caller declaration.
Missing taxonomy/code/topology do not silently select defaults. Unexpected
sequence symbols remain recorded input issues. The caller's original material
is preserved, and hypotheses about what it represents remain revisable.

Subjects record `id`, `name`, `molecule`, `role`, `length`, `unit`, `sequence_ref`,
`source_ref`, source-record identity and input issues. The problem identity
contains only immutable input/source/context declarations. Acquiring references
or changing taxonomy cannot change it. A protein or single gene is an input
subject; neither needs a fabricated contig or CDS.
These are scalar sequence subjects. A read-library container instead records
fixed `member_count`, `position_mass`, membership digest and collection/source
identities, has no linear `length`/`unit`, and is not a sequence operand.
Selected lazy `read_subject` identities resolve from actual original membership.
See [READ_LIBRARY_TARGETS.md](READ_LIBRARY_TARGETS.md) for the exact APIs.

These are authoritative stored identities. Automatic reasoning views expose
explicit name/description/identifier previews for parsed inputs and member-bound
references, with exact registered member/title continuation. Full records and
exports remain intact; see [MATERIAL_HEADERS.md](MATERIAL_HEADERS.md).

Features are genuine located proposals with ordered half-open `segments`,
`strand`, `subject_ref`, feature kind and context references. Products identify
actual derivations and explicit mappings to original input units. Coverage
records are `{target_ref,start,end,unit}`; protein input uses amino-acid units.
Read-local footprints additionally require the exact original `member_ref`;
equal local coordinates on different original reads cannot merge.
Physical mapping paths instead use `{subject_ref,start,end,unit,strand}` and can
traverse external source sequences without becoming original-input targets.
Native derivations retain exact order, orientation, frame and scale.
An annotation's `whole_input_context` footprint informs context interpretation;
it does not turn one locus into whole-genome functional coverage.

## Source facts and reasoning

Host origins are `caller`, `external`, `tool`; scientific interpretations use
`reasoning`. Model extraction uses the separate origin `extracted`. Source rows
retain original artifact, optional text artifact, request/version/retrieval
provenance. Sources, terms, external references and contexts are append-only.
Source labels are retained by actual imports/adapters or anchored extraction;
they are not unrestricted model-created findings.

Observations preserve both `subject_refs` (the target attribution) and
`source_subject_refs` (the actual compared/assayed entities), `source_ref`, kind,
typed measurements, dependencies and optional exact extraction anchor. An assay
on a reference protein remains an assay on that reference. Measurements use
registered names and tagged atoms; arbitrary prose is not a metric.

Atoms are tagged `number` (with optional unit reference), `enum`, `term_ref`,
`reference`, or a closed structured relation of registered roles and references.
Initial observation kinds include sequence composition, predictions, alignments,
profiles, structure, source annotations/content, assays, phenotype/growth,
read support, coordinate mapping, mechanism, comparison and context. Exact names
and metric vocabularies live in `domain.py`.

`concentration` and `dissociation_constant` are registered measurement names.
Keep the actual chemical, sample, binding partners, assay construct and conditions
in the existing subject/source-subject, relation and context references. A reported
medium concentration, an added dose and a construct's binding constant are different
observations or conditions; none becomes an intracellular target measurement by
registration. For a chemical-specific observation, `sample_ref` or `medium_ref`
can identify the actual matrix. For a binding pair, a `relation_ref` can retain the
actual construct as `source` and ligand as `partner`, with its `condition_ref`.
These are available representations, not a required observation layout or task order.

Numeric atoms also allow optional `qualifier:"approximate"` when the source
explicitly reports an approximation, and optional source-reported uncertainty:

```json
{"type":"number","value":42.4,"unit_ref":"actual_unit_term_ref",
 "uncertainty":{"representation":"plus_minus","magnitude":1.2,"statistic":"unspecified"}}
```

The unit reference in this illustrative example must be an actual registered unit
term. Uncertainty magnitude is finite, nonnegative and in the enclosing number's
unit. The closed `statistic:"unspecified"` preserves an unexplained source ±;
it does not invent SD, SE, CI, a distribution or interval endpoints. Omit uncertainty
when none is reported. Omitted qualifier/uncertainty fields stay absent and add no
precision claim; an unqualified experimental number is not certified exact.
Existing numeric atoms keep their original required fields and identities when
these optional fields are absent. These fields supply no score bonus, penalty,
permission or continuation rule. Shared context/observation schemas, exact source
anchors, ordinary queries, semantic-reference forms and JSON export retain the
same recorded value and provenance.

A hypothesis is `{subject_refs,predicate,value,context_refs}`. Predicates cover
taxon/code, roles/families, chemistry, transport, locations, participation,
requirements, integrity/structure, membership, partner dependence, growth and
regulation. New scoped alternatives can be recorded through these semantic
types. The initial alternatives do not define a closed scientific answer set.

An assessment links one hypothesis to one observation, retaining its relation,
applicability, required `extent_basis`, conditions and examined assumptions. A changed interpretation
creates an immutable revision and advances an explicit current pointer. Each
annotation's `coherent_sets` explicitly groups compatible interpretations; the
store and credit projector do not infer compatibility from predicate names.
Each interpretation has disposition `supported`, `weakened` or `unresolved`
and its assessment references. These are revisable scientific judgments, never
execution permissions or acceptance gates.

## One reasoning acquisition

The closed reasoning payload has arrays `structural_proposals`, `terms`,
`source_subjects`, `observations`, `hypotheses`, `assessments`,
`annotation_updates`, plus optional source-anchored `contexts`. New rows have
simple local aliases; `@alias` resolves within the same acquisition. Returned
references are actual semantic IDs, not those aliases.

Extracted terms/observations require an anchor with `source_ref`, `artifact_ref`,
UTF-8 byte `start`/`end`, and exact `quote`. The artifact must belong to that
registered source. This checks transcription/provenance; there is no additional
LLM reviewer or truth-approval call. Extraction retains its actual origin.

Assessment and annotation updates name `expected_revision`. A stale update is
preserved as a proposal with structured conflict feedback; it cannot overwrite
a newer interpretation. Valid independent rows survive a malformed dependent
row. Result fields are `status`, `record_refs`, `changed_record_refs`, `aliases`,
`conflicts`, `errors`, informational `notices`, `error_code`. Reusing an action key replays the committed
result; it cannot manufacture another contribution. Private operation identities
and aliases stay outside parent scientific forms.

The store awards no credit for record/resource counts and applies no biological
stopping rule. Current state, reasoning views, forms and credit project this same
authority. Closed histories and raw source bodies stay on disk and load only
through explicit queries.

## Exact implementation details

Stored records are flattened: `id`, `record_type`, `origin`, followed by the
schema's scientific fields. `record_type` always identifies the row schema;
`kind` retains its scientific meaning (`CDS`, `alignment`, `assay_report`, etc.).
`store.get(ref)` takes one actual reference and returns this record. It never
implicitly loads source text or sequence bytes.

Scope optionally includes `segments`, an array of the same footprint rows.
When omitted, each declared scalar input contributes its full original range;
a library contributes its fixed original member-position mass, narrowed by any
immutable `read_selection_refs`. There is no implicit joined-library interval.
When supplied, segments define the complete eligible union, every selected
subject must have an interval, units/bounds are checked against the immutable
input and overlapping intervals are merged. A child's union must be contained
by its parent's. Feature/product/annotation writes must fit the assigned union.
Scientific input and source context remains readable across a root problem;
write ownership and credit scope do not impose an invented blanket reading ban.
`store.scope_coverage(scope)` returns explicit small or scalar normalized
footprints. An implicit full-library scope requires `iter_scope_coverage` when
enumeration is actually needed; projection uses compact dimensions and fixed
mass without expanding unexamined reads.

An annotation interpretation must refer to a hypothesis with the same mapped
original footprint as its subject. A feature and its translated product can
therefore share an account; a locus hypothesis cannot be promoted to a whole
assembly annotation merely because both descend from one input. Whole-input
context hypotheses can be used through a local account's `context_refs`.
Within one coherent set, each hypothesis appears once. Other coherent sets can
retain competing interpretations of that hypothesis.

Native derivation tools now record exact source paths for translated products
and explicit sequence views. Subregion features can follow these paths back to
original or external material, including reverse and compound traversals. An
older product with only an aggregate footprint still reports
`subregion_mapping_unavailable`; no residue-to-genome map is guessed from length
ratios. Physical coordinates and eligible credit footprints remain separate.
Native observation `operand_intervals` retain each actual aligned operand
independently. A gap never receives an invented query-residue coordinate.

The required reasoning arrays are `structural_proposals`, `terms`,
`source_subjects`, `observations`, `hypotheses`, `assessments`,
`annotation_updates`. Optional `contexts` descriptors retain the actual anchored
context type, literal name, typed attributes and related references.
Extracted term descriptors contain
`{alias,label,term_type,source_ref,anchor}`. Their namespace is `source_local`;
the store derives their accession from the actual source, label and anchor.
External ontology identities come from actual acquisitions, not model-invented
accessions. Extracted source-subject descriptors contain
`{alias,reference_type,label,source_ref,anchor}` and create source-local reference
entities with no fabricated sequence or length. A paper's actual assayed
construct can thus be represented even when no sequence accession exists.

An extraction anchor establishes the exact supplied text span and origin.
Whether an extracted observation correctly interprets that text remains a
scientific question for iterative reasoning; passing a transcription check does
not certify its truth. Direct empirical attribution additionally requires the
actual assayed subject identity, so an external construct cannot silently become
an experiment on the unknown input. Transfer and contextual assessments retain
that distinction.

Assessment and annotation writes require `expected_revision` through both
`put` and `commit_reasoning`. Current-pointer conflicts preserve a proposal and
return feedback without overwriting the current record. Identical current
interpretations are reused; acquiring the same object does not create a new
semantic contribution. `current_annotations` and `current_assessments` accept
optional `limit`/`offset`; omission returns the complete current projection for
credit and explicit host queries. `store.count(kind,scope,current=False)` counts
records without loading their bodies.

`reasoning_view(scope,limit=100)` bounds each scientific-record category,
including current annotations and assessments. Original `subjects` are still
provided in full; that separate input-growth limitation is not solved here.
`pages[field]` records `offset`, `limit`, `total`, `next_offset`, `current_only`
and executable `next_query`. Pass `next_query` to ordinary `state.query` to
continue the same current or historical selection and order. Exact semantic
reference filters expose dependent rows and matched field paths without inferring
truth or invalidating measurements. Virtual `kind:"subject"` queries page the
input/feature/product inventory without materializing it. See
[STATE_QUERY.md](STATE_QUERY.md) for modes, reference meaning and examples. Supplied raw context is registered as an
ordinary caller source, exposed by `problem.caller_context_source_ref` and
`reasoning_view.supplied_context_source_refs`. Dataset entries can include
`sample` (a caller sample identifier) and `context` (original supplied JSON).
Entries sharing the same declared sample link to one sample context identity;
other samples remain distinct. Collection membership alone never merges them.

Scientific artifact references are reachable from actual registered source,
sequence and semantic records. Unattached execution diagnostics remain durable
audit artifacts and cannot resolve as parent-facing scientific artifact values.

## Measured extent and inferred target attribution

Every new assessment declares `extent_basis` as `observed_extent` or
`inferred_extent`. This is required, with no source-identity-dependent default.
`target_footprint` remains optional and nullable; a non-null value is a nonempty
array of actual original-input segments, for example:

```python
{"extent_basis": "inferred_extent", "applicability": "transfer",
 "target_footprint": [
    {"target_ref": original_input_ref, "start": 40, "end": 80, "unit": "aa"}
 ]}
```

With `observed_extent`, credit uses actual mapped observation/source extent.
An optional target footprint restricts that extent; it cannot expand a measured
alignment or turn a gap into an observed query residue. Exact native operand maps
retain factor one. A legacy product with no residue map retains its explicitly
labeled fractional coverage proxy, without inventing coordinates. A native empty
operand list remains empty. A real assayed/source subject's mapped extent still
constrains direct observed support.

With `inferred_extent`, the reasoning owner attributes the existing source
observation to the explicit target footprint. The footprint is intersected with
the hypothesis, current annotation and fixed assigned scope, independently of
source coordinates. The same rule applies whether the source is another original
input, a sibling locus on the same input, an external sequence or a derived
product. This does not create a target measurement or residue map. The source
observation, actual subjects and measured coordinates remain unchanged.

Inference contributes once per assessment, rather than once per physical source
operand. For alignment, profile-match, comparison and structure-match observations,
the existing query-role `query_coverage` proxy scales that contribution once when
reported. If unreported, the factor is one and explicitly labeled as such; other
observation kinds retain factor one. Exact *source* mapping does not remove this
inference factor. These are versioned operational proxies, not calibrated accuracy.

An inferred assessment without `target_footprint` is valid recorded science with
no invented target extent or credit. Its completed reasoning result includes an
informational notice with `record_ref`, `field_path:["target_footprint"]` and code
`inferred_extent_requires_target_footprint`. The current projection identifies
the same assessment and reason in `inactive_dependencies`. The existing ordinary
outcome carries that notice to the responsible Episode; no reviewer, retry or
additional reporting call is introduced. Omission and null canonicalize to the
same absence and do not create a revision merely by representation.

`direct` applicability together with `inferred_extent` contradicts the declared
representation. The affected row returns
`assessment_inferred_extent_cannot_be_direct` with the exact `extent_basis` field
path and compatible applicability values. Independent valid rows still commit.
Direct external empirical attribution also retains its existing actual-assayed-
subject identity check. An explicit target footprint cannot make an external
experiment a direct experiment on the unknown input.

The Store checks original input IDs, bounds, units, hypothesis coverage and assigned
scope for every non-null target footprint. Proper subsets are allowed. An
external-only hypothesis cannot donate input coverage. No input extent is filled
in from source coordinates, chromosome length or the Episode's scope.

Changing extent basis or footprint uses the existing immutable revision/CAS
mechanism. Current queries, model views, parent-requested semantic references and
exports retain those same fields. Projection version
`source_bound_coherent_interpretation_coverage_v6` retains v5 observed/inferred
attribution and adds sparse original-read geometry and explicit operand paging.
Older run histories retain their exact bindings; numerical yield, weights,
hypervolume and continuation are
unchanged. The source contribution records `extent_basis`, target attribution,
actual source operand intervals and exact physical source paths separately from
`contributing_segments`, which are target units. Neither a measured gap nor an
unexamined site is assigned a biological verdict by infrastructure; typed
scientific relation, applicability and disposition remain the Episode's work.
