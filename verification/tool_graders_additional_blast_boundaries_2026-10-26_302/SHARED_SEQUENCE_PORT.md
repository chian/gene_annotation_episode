# Proposed shared sequence-database port for the next additive contract

This is the concrete shared-code boundary extracted from302's read-only plan.
It supersedes preliminary message shorthand, including the initially omitted
`report_source` and `search_binding` arguments. It changes no existing contract
or implementation until the parent freezes a new additive coding assignment.

## Exports and exact outer shapes

New `gene_annotation_episode/blast_sequence_database.py`:

```python
populate_blast_sequence_database_sheet(
    search, *, report_source, search_binding, query_binding,
    reference_metadata, description_bindings, sequence_identity_bindings,
    target_context=None, database_profile=None,
) -> dict

calculate_blast_sequence_database_components(sheet, *, model=None) -> dict
```

The populated sheet has exactly these keys:

```text
schema: blast_sequence_database_result_sheet_v1
search: original complete 293 search envelope, unchanged
report_source: ReportSource
search_binding: SearchBinding
query_binding: QueryBinding|null
reference_metadata: array of complete supplied metadata records
description_bindings: array of {search_key:SearchKey,binding:DescriptionBinding}
sequence_identity_bindings: array of {search_key:SearchKey,binding:SequenceBinding}
target_context: existing supplied target-context object|null
database_profile: existing supplied population-profile object|null
```

It retains actual native numerical HSP data within `search`, not just identifiers
or claims. Population validates caller shape/finite JSON and copies these
inputs. Calculation qualifies native relationships and returns valid numerical
parts alongside explicit issues, preserving malformed siblings in the sheet.

The calculator output has exactly:

```text
schema: blast_sequence_database_result_components_v1
search_key: SearchKey
status: complete|partial|no_reported_hits|unavailable|incompatible
components:
  database_sheet: existing blast_database_sheet_v1 object|null
  function_weights: existing blast_database_probabilities_v1 object|null
  coordinate_context: CoordinateContext
  selected_query_coverage: array of SelectedCoverage
  row_keys: RowIndex
issues: array of Issue
```

`database_sheet` remains the complete existing numerical result with explicit
association mode and its unchanged schema constant. Preserve native numeric
fields in the original search even if this derived subobject is incompatible.
`model` is null or the existing finite object with only `temperature_bits` and
`function_priors`. The existing formula and parameter interpretation remain
unchanged. Calculator output is saved separately, allowing recalculation of the
saved sheet without acquisition or rewriting closed observations.

## Search/source qualification

```text
SearchKey = {
  artifact_key: nonempty string,
  member_ordinal: nonnegative integer|null,
  report_index: nonnegative integer,
  search_pointer: RFC6901 pointer string
}

ReportSource = {
  artifact_key: nonempty string,
  artifact_ref: nonempty retained-artifact reference,
  member_ordinal: nonnegative integer|null,
  member_sha256: lowercase 64-hex string|null
}

Provenance = {source_ref:nonempty string,pointer:RFC6901 string}

SearchBinding = {
  search_key: SearchKey,
  stage: sequence_database|domain_database|null,
  biological_round: positive integer|null,
  database_identity: DatabaseIdentity|null,
  input_pssm_key: nonempty string|null,
  provenance: Provenance|null
}

DatabaseIdentity = {
  namespace: nonempty string,
  value: nonempty string,
  version: nonempty string|null,
  release: nonempty string|null,
  scope: nonempty string|null,
  preparation_type: sequence_database|rps|delta|unknown,
  source: Provenance
}
```

The adapter compares every field of SearchBinding.search_key with the exact293
key. ReportSource matches its artifact key/member ordinal. A non-archive report
has both member fields null; an archived report needs both actual ordinal and
member digest. Validate the latter against the retained normalized native
member digest and ordinal. Acquisition is responsible for qualifying
`artifact_ref` against the actual captured artifact manifest; a pure function
cannot prove a Store reference by doing I/O. The adapter must not invent this
reference from an artifact name. Retain this custody dependency explicitly.

Require `stage=sequence_database` and actual binding provenance for sequence-
specific derived calculations. `domain_database` is incompatible here; null is
unresolved. Preserve either case's native data and return a specific issue.
Biological round may remain null even when stage is known. Provenance must
identify a record that establishes the relation; the adapter does not infer
stage/round from position, executable name or checkpoint filename.
Invocation-wide `reference_kind=sequence` does not establish a DELTA section's
stage. Do not mutate `search.stage` to pass this check.

The existing resolver must reproduce the supplied program_context from its
selected/native tokens, mode, query/reference kinds and version. A previously
unresolved context or incompatible native mode cannot be repaired by supplying
an override. Admission requires resolved `scientific_mode=database` and actual
sequence-target semantics. PSSM input is a query representation, not a change
of target population.

Accepted query kinds are exactly the resolver's sequence-target combinations:
`psiblast:sequence|pssm|msa`; `deltablast:sequence`; ordinary
`blastn|blastp|blastx|tblastx:sequence`; `tblastn:sequence|pssm` where already
source-qualified by the resolver. The work packet exercises PSI/DELTA; listing
the existing ordinary combinations does not claim their database deployment or
add unrelated inventory work. Reject RPS/RPSTBLASTN and both VDB programs from
this sequence-population adapter. Their separate sheets own their meanings.

## Exact query binding

```text
Operand = original 293 shape, exactly:
{
  role: query|subject|database|profile|msa|checkpoint,
  artifact_key: nonempty string|null,
  record_ordinal: nonnegative integer|null,
  native_id: string|null,
  native_title: string|null,
  subject_ref: string|null,
  molecule: dna|rna|protein|unknown,
  length: positive integer|null,
  selected_interval: [nonnegative start,positive end]|null,
  identity: {namespace:string,value:string,version:string|null}|null
}

QueryBinding = {
  operand: Operand,
  axis_kind: sequence|pssm_master|msa_master,
  full_length: positive integer,
  coordinate_unit: aa|nt,
  sequence_sha256: lowercase 64-hex string|null,
  pssm_key: nonempty string|null,
  master_mapping_ref: Provenance|null
}
```

For a qualified query axis, `operand.role=query` and the operand must equal the
293 `search.operand_binding`, not merely have the same length. If that original
binding is null, keep the supplied candidate descriptor and native measurements
but report the axis unbound; do not silently use it as a full-length or biological
binding. The upstream worker therefore decodes a selected PSSM/MSA master before
constructing293's invocation operands when that information is available.

`axis_kind` must match query kind exactly: sequence -> sequence, pssm ->
pssm_master, msa -> msa_master. Query molecule/coordinate unit must match the
resolved geometry. Full length equals the supplied operand's known full length.
Native reported length must equal that length or the exact explicit selected
interval span, with no contradictory native identifier/title. A selected
interval lies inside the full operand, start<end. The calculator never adds a
range offset to native endpoints. It validates HSP correspondence against the
full bounds and selected bounds.

For sequence input, an actually authenticated sequence digest is required for
publication as a biological observation. A missing digest leaves source-level
native quantities readable but no new biological identity claim. For PSSM/MSA,
`master_mapping_ref` identifies the actual input/master coordinate relationship;
`pssm_key` is required for PSSM kind and nullable for an MSA before a checkpoint
exists. Do not invent a checkpoint for an MSA. `sequence_sha256` is nullable
because a displayed/generated master need not be an authenticated biological
query. Do not publish a profile/master as a biological sequence merely because
its length and symbols are known. A genuine supplied sequence-to-master mapping
can separately establish that biological relation.

Null QueryBinding is a supported missing input. Native scores/counts and exact
target metadata remain retainable; full/selected query denominators and any
query biological observation are unavailable. Function weighting is qualified
by compatible search/program/sequence-target semantics and exact target links,
not a fabricated query sequence. Its returned status must disclose an unbound
query and cannot claim complete biological publication.

## Original row identities and source-locator construction

```text
RowKey = {
  search_key: SearchKey,
  hit_ordinal: nonnegative integer|null,
  hsp_ordinal: nonnegative integer|null,
  description_ordinal: nonnegative integer|null
}

RowIndex = {
  search: RowKey,  # all three ordinals null
  hits: [{
    component_index: nonnegative integer,
    row_key: RowKey,  # hit only
    source_locator: SourceLocator,
    hsps: [{component_index:nonnegative integer,row_key:RowKey,
            source_locator:SourceLocator}],
    descriptions: [{component_index:nonnegative integer,row_key:RowKey,
                    source_locator:SourceLocator}]
  }]
}

SourceLocator = {
  artifact_ref: nonempty string,
  report_index: nonnegative integer,
  pointer: RFC6901 string,
  search_key: SearchKey,
  member_ordinal: nonnegative integer|null,
  member_sha256: lowercase 64-hex string|null,
  native_format: json2|tabular,
  hit_index: nonnegative integer|null,
  description_index: nonnegative integer|null,
  hsp_index: nonnegative integer|null,
  line_numbers: array of positive integers|null,
  data_row_ordinals: array of nonnegative integers|null
}
```

Populate RowIndex in native report/hit/retained-row order, never by score.
The adapter must validate each row_map entry against the actual retained search
and normalized hit; array lengths and retained ordinals must agree. It may not
manufacture a missing map or silently compact a malformed native row. HSP
`component_index` is the position in the legacy `hsp_components` list; its
`row_key.hsp_ordinal` comes from293.row_map, and they need not equal.

For JSON, let P be the exact SearchKey.search_pointer, h the original native
hit ordinal, d the mapped original description ordinal and j the mapped HSP
ordinal. Use pointers P for the report/search adapter, `P/hits/h` for the hit,
`P/hits/h/description/d` for a description, and `P/hits/h/hsps/j` for an HSP.
Validate each against `search.normalized.native.document`, not a filtered
reconstruction. Use actual native singular `description`, not normalized plural
`descriptions`. JSON line/data-row arrays are null.

For tabular reports there is no native JSON hit/HSP array. Keep pointer P
(`/sections/N`) and original line/data-row membership explicitly. HSP j indexes
every original data row in that section, including malformed rows; line is
`search.native.line_numbers[j]`. Hit locators retain every actual HSP row in the
group. A description locator retains only rows with the actual explicit
description association after validating the retained field mapping. Do not
invent `P/hits/h` or a native JSON description pointer for a table. Plural
independently sorted metadata remains unpaired; a partial raw row cannot be
upgraded to an exact description relation by list position.

The detached normalized calculation input receives the search/hit/description
source locators expected by existing `_explicit_inputs`; all extra full-key and
member fields stay present. Description bindings' `description_index` is d,
never a compact normalized position. The legacy inner validators omit member
and round fields; the new wrapper must validate the full outer SearchKey before
stripping only the outer link envelope for that per-search call. No shared
global lookup indexed only by `(report_index,hit_index)` is permitted.

CoordinateContext is exactly
`{query:{axis_kind,reported_length,full_length,selected_interval,coordinate_unit},
references:[{row_key,reported_length,full_length,coordinate_unit}]}` with unknown
lengths/selection null. Native reference length and a source-bound full length
must agree before a full-reference denominator is used. Each SelectedCoverage
has exactly `{row_key,numerator:int|null,denominator:int|null,value:number|null,
unit:'fraction',complete_for_reported_hsps:bool,unavailable_reason:string|null}`.
One entry per native hit describes the paired-query union for that hit; never
union unrelated reference sequences into an alleged global alignment.

## Exact legacy geometry and context extension

One sole shared-code owner may propose the following backward-compatible
signature extension for `build_database_sheet`:

```python
build_database_sheet(result, *, reference_metadata=None, target_context=None,
    database_profile=None, description_bindings=None,
    sequence_identity_bindings=None, geometry_program=None,
    calculation_context=None)
```

Validation rules:

1. Null keyword preserves the existing behavior for all existing callers; it
   does not infer geometry for an extended program. This prevents retroactive
   reinterpretation of old saved inputs.
2. A supplied keyword must be one of the existing five geometry programs.
3. If `result.search.program` is one of those five, an override must be exactly
   equal or raise `blast_database_geometry_program_conflict`. This holds even
   if the two programs happen to have some equal coordinate units.
4. For the extended sequence-target names, the supplied geometry must match
   the source-established existing resolver map (`psiblast`/`deltablast` ->
   `blastp`), or raise the same conflict. Do not add RPS/VDB sequence-population
   support via this keyword. New adapter qualification still checks the full
   native program_context and per-search semantics before calling this function.
5. Pass this qualified geometry to both `alignment_components` and
   `_sequence_links`; keep the selected execution program unchanged in every
   retained input/output. Missing versus invalid resolved context cannot be
   repaired by the legacy function itself.

The adapter uses a detached input for qualified full lengths, as292/003 already
does for pairwise calculations. It retains original reported values in the saved
outer sheet and CoordinateContext. The adapter should not fabricate keys in the
original `search.request` to satisfy legacy limit/population logic. A narrow
explicit context port is required for the existing database sheet's search
limits and `_database_profile` if supplied identity/release/scope is not already
present in its original normalized request. Proposed second optional keyword:

```text
calculation_context = null or {
  reporting: original search.reporting object,
  database_identity: DatabaseIdentity|null
}
```

This keyword is additive, has default null and preserves original behavior when
omitted. The adapter passes it explicitly. Requested hit/HSP limits come from
actual reporting fields; population comparison uses source-bound database
identity/release/scope. An unknown release/scope does not inherit a current
database's release or a convenient default scope for correction. Retain this
context as a separate member of the resulting database sheet. Contradiction
with an explicitly present original request/report identity is an issue that
disables representation adjustment; it does not change original data or the
uncorrected reference-kernel model. The owner should freeze this optional
keyword together with geometry rather than silently synthesizing request data.

## Failures and focused tests

Structural caller errors use specific ValueErrors, including wrong shape,
nonfinite JSON, duplicate source bindings, absent required full SearchKey, or
unsupported declared mode. Native conflict/missingness is retained as issues
with source location and surviving quantities. Issue fields are exactly
`{code,search_key,hit_ordinal,hsp_ordinal,source_pointer,details}`.

Required test oracles: same report_index/hit_index in two archive members and
two native iterations never cross-link; malformed first HSP leaves later native
HSP ordinal unchanged; tabular original data-row ordinal differs from compact
component index; contradictory override rejected for each ordinary program;
extended compatible geometry preserves executable identity; unresolved native
token cannot be rescued; DELTA null-stage cannot enter sequence weighting;
sequence/PSSM/MSA full-query and selected-range bindings remain separate;
missing master or wrong same-length sequence cannot qualify biological identity;
limit/release context never mutates the native request; exact existing model
numbers, provenance and reported precision survive recalculation. Use retained
native paired artifacts only to test shared format/geometry; label fabricated
database/iteration contexts synthetic. No new database search belongs to this
shared owner.
