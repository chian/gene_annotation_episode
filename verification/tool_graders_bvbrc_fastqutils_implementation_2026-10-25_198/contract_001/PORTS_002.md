# FastqUtils shared ports, additive revision 002

These are implementation contracts, not installed operations. `SCHEMAS_002.json`
is the complete companion asset; a name in backticks is its exact `$defs` name.
All scientific arguments/results are closed finite JSON. Python `bool` is not
an integer/count. No function below acquires bytes, launches a program, invokes
a model, selects a resource, changes credit or owns an episode loop.

The only original request input is the **existing** `Host_OriginalTask`:
`submitted_parameters` and `submitted_start_parameters` already contain the
submitted operands. `task_ref` is its `submission_receipt_ref`; the native
`task_id`, `submission_source_ref`, operation key, resource and application IDs
remain separately retained. No new full-request transport is introduced.
`input_pointer` is relative to `submitted_parameters`, exactly
`/paired_end_libs/N`, `/single_end_libs/N`, or `/srr_libs/N`; N is canonical
zero-based decimal. Recipe ordinals are zero-based, including repetitions.

## Sole common owner: root

Owned production files proposed:
`gene_annotation_episode/bvbrc_fastqutils_contracts.py`,
`gene_annotation_episode/bvbrc_fastqutils_schemas.json`,
`gene_annotation_episode/bvbrc_fastqutils_identity.py`, and
`gene_annotation_episode/bvbrc_fastqutils_metric_specs.py`.
These may import standard library, schema validation and existing generic
contract utilities. They **cannot import any parser, metadata extractor,
sheet constructor, calculator, provider or return implementation**.

```python
class FastqUtilsContractError(ValueError):
    code: str                 # ContractFailure.code
    path: str                 # canonical JSON Pointer; no operand echo
    diagnostics: list[dict]   # exactly [ContractFailure]

def validate_contract(name: str, value: object) -> dict | list: ...
def validate_parameters(value: dict) -> dict: ...  # ProviderParameters
def validate_native_document(value: dict) -> None: ...
def validate_metadata(value: dict) -> None: ...
def validate_sheet(value: dict) -> None: ...
def validate_components(value: dict, *, sheet: dict) -> None: ...
def validate_finite_json(value: object) -> None: ...
def canonical_json(value: object) -> str: ...
def json_sha256(value: object) -> str: ...
def bytes_sha256(raw: bytes) -> str: ...
def checked_bytes(raw: bytes, *, content: dict) -> bytes: ...  # ContentBinding
def pointer_value(value: object, pointer: str) -> object: ...
def encode_reference(kind: str, analysis_id: str, pointer: str) -> str: ...
def decode_reference(reference: str, *, expected_kind: str | None = None) -> dict: ... # ReferenceParts
def document_ref(analysis_id: str, document_id: str) -> str: ...
def artifact_ref(context: dict) -> str: ...                       # ParseContext
def native_ref(kind: str, context: dict, ordinal: int) -> str: ...
def population_ref(context: dict, key: str, ordinal: int) -> str: ...
def library_ref(analysis_id: str, task_ref: str, input_pointer: str) -> str: ...
def stage_ref(analysis_id: str, task_ref: str, recipe_ordinal: int) -> str: ...
def metadata_ref(kind: str, analysis_id: str, metadata_id: str) -> str: ...
def join_ref(kind: str, analysis_id: str, metadata_id: str, population_refs: list[str]) -> str: ...
def component_ref(analysis_id: str, sheet_sha256: str, parameters_sha256: str,
                  calculation_id: str, metric: str, threshold: int | None) -> str: ...
def requirement_ref(analysis_id: str, scope_pointer: str, code: str) -> str: ...
def literal_ref(analysis_id: str, record_ref: str, field_pointer: str) -> str: ...
def field_ref(analysis_id: str, field: str) -> str: ...
def metric_spec(metric: str) -> dict: ...       # exact row in METRIC_SPECS_002.json
def component_spec(metric: str) -> dict: ...    # exact row in COMPONENT_SPECS_002.json
def make_requested_schema(form: dict) -> dict: ...  # RequestedForm -> real JSON Schema
def validate_requested_form(schema: dict) -> dict: ... # actual schema -> RequestedForm
```

Validation returns a detached value; no in-place mutation. Canonical JSON is
the existing `execution_contracts.canonical` spelling: sorted keys, `(',', ':')`
separators, `ensure_ascii=False`, `allow_nan=False`, strict UTF-8. SHA256 is of
that UTF-8 encoding, or exact raw bytes for `bytes_sha256`. No float rounding,
unicode normalization, lowercasing, numeric-string coercion or bool-to-int
coercion. `checked_bytes` checks both digest and exact length; it does not
authenticate source possession. JSON Pointer supports only RFC6901 `~0/~1`,
canonical integer array indices, no `-`, no percent decoding, and no implicit
field creation. Duplicate native JSON object keys are diagnosed by the reader.

`encode_reference` emits exactly
`bvbrc_fastqutils_{kind}:{pct(analysis_id)}/{pct(pointer)}`.
`pct` is UTF-8 percent encoding with `safe=''`, uppercase hex; unreserved
ASCII remains literal. `analysis_id` obeys `TOKEN` in the schema. Pointer is
empty or slash-prefixed and contains only canonical `~0/~1` escapes. Decoder
must validate UTF-8, kind, analysis ID, pointer and exact re-encoding equality;
reject lowercase escapes, encoded unreserved characters, extra separators,
trailing junk and invalid pointer escapes. It returns `ReferenceParts`.
`IDENTITY_VECTORS_002.json` fixes Unicode, percent and slash cases.

Helper pointer constructions (E is JSON-Pointer token escaping, not URL
escaping; all integers are zero-based canonical decimal):

| Helper | Exact pointer before percent encoding |
|---|---|
| document | `/documents/{E(document_id)}` |
| artifact | `/documents/{E(document_id)}/sha256/{content.sha256}` |
| native | artifact pointer + `/{collection}/{ordinal}`; kinds/collections: cell/cells, category/categories, label/labels, sequence/sequences, alignment/alignments, header/headers, lineage/lineage |
| population | artifact pointer + `/populations/{population_key}/{ordinal}` |
| library | `/tasks/{E(task_ref)}/inputs` + original input_pointer |
| stage | `/tasks/{E(task_ref)}/recipe/{recipe_ordinal}` |
| metadata | `/metadata/{E(metadata_id)}`; kind association or population only |
| join | `/metadata/{E(metadata_id)}/inputs/{sha256(canonical(sorted(population_refs)))}/{kind}`; kind population or cell, for observed pair correspondence |
| component | `/sheets/{sheet_sha256}/parameters/{parameters_sha256}/calculations/{E(calculation_id)}/{metric}/{threshold-or-none}` |
| requirement | scope_pointer + `/{code}` |
| literal | `/records/{E(record_ref)}` + field_pointer; kind label |
| field | `/facts/{E(field)}`; kind field |

Native arrays are in original section/member order, then row order, then native
column order. Synthetic summary fields use `METRIC_SPECS_002.json` order;
histogram axes ascend numerically, symbols use A,C,G,T,N,other_iupac,invalid.
No sorting by a generated hash. Identities distinguish repeated rows/sections.
Byte changes change artifact/native identities; metadata/formula changes change
sheet/component hashes. Caller document IDs and semantic selectors stay fixed.

`make_requested_schema` creates exactly the object structure in
`RESULT_SELECTOR_PRE_DOWNLOAD_002.json`: closed named fields, each with
`$ref: #/$defs/ProjectedField` and `x-bvbrc-fastqutils: FactSelection`, required
in input field order, and the transitive definition closure of ProjectedField.
`validate_requested_form` reconstructs and compares the entire generated schema;
foreign keywords, weakened unions or removed fields are rejected. JSON Schema
shape validation alone is insufficient for the semantic relationships below.

## Native readers: workers A and B

Every function below has this exact signature and result:

```python
def parse_NAME(raw: bytes, *, context: dict) -> dict: ...
# context: ParseContext; result: NativeDocument
```

| Owner | Export | Exact declared format |
|---|---|---|
| A | `parse_fastq` | fastq, including complete gzip members or plain bytes regardless of suffix |
| A | `parse_sam` | sam_1_6 |
| A | `parse_bam` | bam_1; BGZF using struct/zlib, no subprocess |
| B | `parse_fastqc_html` | fastqc_html_0_12_1 |
| B | `parse_fastqc_data` | fastqc_data_0_12_1 |
| B | `parse_fastqc_zip` | fastqc_zip_0_12_1; in-memory members only |
| B | `parse_trim_galore_report` | trim_galore_report_0_6_10 |
| B | `parse_fastq_pair_stderr` | fastq_pair_stderr_0_3 |
| B | `parse_hostile_json` | hostile_json_1_1_0 |
| C | `parse_unsupported_artifact` | bai, samstat_html, sra_metadata, native_text, native_json, unknown |

`context.content` binds actual supplied bytes. Metadata declarations are not
passed to native readers. FASTQ quality symbols/histograms are preserved even
without encoding. BAM has native numeric qualities. Native FastQC Encoding is
`NativeLabel.kind=encoding_inference`, never an encoding declaration.
`producer_version` in ParseContext is a caller expectation; reported version
and supported grammar must be checked independently and both retained. A
grammar match without native version evidence carries `producer_version_unproven`.

Malformed scientific bytes return a NativeDocument with valid prefix/siblings,
explicit parse_scope, requirements and diagnostics. They do not raise a global
exception that erases other documents. Bad API argument shape/digest/type is
`FastqUtilsContractError`. Reader dispatch does not try every format or choose
from filename; declared formats and exact byte/container checks determine it.
NativeSection, NativeLabel, AlignmentHeader and ReferenceEntry are the shared
ports for complete tables, text settings, reference/read-group/program metadata
and header dictionaries. Full original bytes remain bound by Artifact.
Unknown sections remain RawBlock records, never silently discarded.

Native artifact-local Population records exist without a biological sample,
task-stage association or instrument metadata. NativeDocument associations are
null. Reader-supplied native report edges have `scope=artifact_local` and
`task_stage_ref=null`. A report does not prove a requested recipe occurrence.

## Metadata, sheets and input resolution: worker C

```python
def resolve_documents(bundle: dict, *, artifact_bytes: dict[str, bytes],
                      parameters: dict) -> tuple[list[dict], list[dict], list[dict]]: ...
# returns (ParseContext[], ResolvedDocument[], Requirement[])
def parse_fastqutils_artifact(raw: bytes, *, context: dict) -> dict: ... # dispatcher
def select_metadata(inputs: dict) -> tuple[list[dict], list[dict], list[dict]]: ...
# MetadataInputs -> (SelectedMetadata[], Requirement[], Diagnostic[])
def extract_fastqutils_metadata(original_task: dict, *, analysis_id: str,
    metadata_bindings: list[dict], supplied_values: list[dict],
    documents: list[dict]) -> dict: ...                              # Metadata
def populate_fastqutils_sheet(documents: list[dict], *, metadata: dict,
                             document_resolutions: list[dict]) -> dict: ... # Sheet
def resolve_calculation_inputs(sheet: dict, *, requests: list[dict]) -> dict: ...
# CalculationRequest[] -> CalculatorParameters
```

Exact inputs are Host_OriginalTask, MetadataBinding[], SuppliedValue[],
NativeDocument[] and ResolvedDocument[]. Host possession/authentication is
described in CONTRACT_002; the pure API cannot certify a fabricated bundle.
No extra OriginalTask transport or trust-me verified/completed boolean.
SelectedMetadata retains the exact selected SourceEvidence AND typed value.
Missing/malformed unrelated metadata adds local requirements and preserves
valid independent documents/counts. Library/stage creation reads only original
submitted operands, never scheduler-returned substitutions.

Document requirement selection matches `ArtifactMember.requirement_ids`, not
role, basename, glob or array position. Exact repeated ContentBindings are
deduplicated canonically; zero distinct bindings is missing, one is resolved,
more than one is ambiguous. Different byte versions remain distinct. Every
duplicate acquisition receipt stays in the original bundle. Possessed selection
requires exact ContentBinding membership in `bundle.supplied_contents` or an
exact matching artifact member, plus its bytes. Selection is not permission to
scan other supplied artifacts. Missing one document leaves other documents usable.

Metadata consumers are finite: encoding declaration -> population quality basis;
library annotation -> that exact original library's supplied identities;
association assertion -> explicitly asserted/unresolved association; pair
declaration -> observed unambiguous mate correspondence and pair population;
reference declaration -> retained asserted reference identity/completeness;
lineage declaration -> exact source-bound before/after scientific assumption.
Reference declarations do not turn a requested reference or a current download
into a complete producer reference. Every assertion remains inspectable.
`Metadata.measurements` contains only structurally counted `verified_pair_count`
cells derived from a PairDeclaration and unambiguous actual record correspondence.
Its join identity incorporates both actual population references. The cell uses
the left artifact as its locator anchor and the pair population names both
artifacts and complete matched member records. This is observed pairing, not
an invented native fastq-pair emitted count or recipe completion.

## Numerical functions: separate A/B files, C dispatcher

```python
def calculate_composition(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]: ... # A
def calculate_quality(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]: ...     # A
def calculate_mapping(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]: ...     # A
def calculate_retention(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]: ...   # B
def calculate_report_consistency(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]: ... # B
def calculate_fastqutils(sheet: dict, *, parameters: dict) -> dict: ... # C; Components
```

`job` is exactly CalculationBinding; `parameters` is CalculatorParameters.
The dispatcher validates every job and its hash once and concatenates results
in parameter order, metric registry order, ascending selected threshold.
Calculators import common contracts/identity/specifications only, never readers
or acquisition code. All17 component meanings in193 remain; source corrections
and explicit encoding assumptions are additive. An unavailable job produces
its selected formula family's typed null components with empty or actually
resolved operand references, never fake population/measurement records.
Component IDs use canonical complete sheet and full parameter hashes.

Retention and report-consistency jobs carry `lineage_basis`. A native report
edge and a source-bound `LineageDeclaration` are distinct admissible bases.
The latter permits arithmetic on explicitly selected compatible complete
populations as a stated assumption; it does not establish actual recipe
execution. Copy the exact declaration, selected evidence, relation and basis
into every derived component and requested payload. No assumption bypasses
zero-denominator, incompatible-unit, partial-population or after>before checks.
Mapping read correspondence still requires actual unambiguous record joins.

An encoding declaration is a **stated assumption**. Copy its exact value,
SourceEvidence, encoding and basis into the sheet, quality components and
requested quality projection. Do not rename it verified. Unknown encoding
makes quality-derived values unavailable; it does not destroy raw character,
base or read counts. BAM numeric quality representation is separate.

## Provider, saved storage and projection: worker C

```python
class FastqUtilsBundleAdapter:
    adapter_id = 'bvbrc_fastqutils'
    adapter_version = '2'
    def consume_bundle(self, bundle: dict, *, artifact_bytes: dict[str, bytes],
        supplied_values: list[dict], requested_form: dict, parameters: dict) -> dict: ...
# Host_ArtifactBundle, actual artifact-ref keyed bytes, SuppliedValue[], actual
# generated requested JSON Schema, ProviderParameters -> ProviderResult

def project_fastqutils_facts(sheet: dict | None, components: dict | None, *,
    requested_form: dict, parameters: dict, failure_context: dict) -> dict: ... # ProjectionResult
def encode_failures(requirements: list[dict], diagnostics: list[dict]) -> dict: ... # EncodedFailures
def encode_saved_components(calculations: dict | None, *, projection_failure_context: dict,
    native_requirements: list[dict], native_diagnostics: list[dict]) -> dict: ... # SavedComponents
def decode_saved_components(value: dict) -> dict: ... # validated detached SavedComponents
def validate_saved_projection(sheet: dict | None, saved_components: dict, *, facts: dict,
    status: str, missing_requirements: list[dict], diagnostics: list[dict],
    requested_form: dict, parameters: dict, original_task: dict, bundle: dict) -> None: ...
```

The current host `_grade` already uses exactly this provider keyword ABI.
It persists result.sheet and result.components independently. Native failure
arrays are stored in SavedComponents; the host's generic AcquisitionRequirement
and Diagnostic grammars are not replaced by native arrays. The original
projection_failure_context is retained separately and round-trips; saved
validation must not reconstruct it by subtracting final deduplicated arrays.
See CONTRACT_002 for the exact error codec and status semantics.

Saved validation checks hashes, IDs, references, selectors, original submitted
operands, formula parameters and exact requested projection against saved
records. It does **not** parse native bytes, rebuild the sheet or recalculate
science. Recalculation is a distinct explicit pure function over saved data.

## Existing return boundaries: root

Proposed `bvbrc_fastqutils_returns.py` exposes the existing return-owner pattern:

```python
def fastqutils_fact_sources() -> dict: ...
def requested_sources(schema: dict) -> tuple[str, ...]: ...
def project_fastqutils_return_facts(body: dict, *, requested_sources: tuple[str, ...],
    sheet: dict | None, components: dict | None) -> dict: ...
class BVBRCFastqUtilsReturns(EpisodeReturnRecords):
    def __init__(self, execution): ...
    def facts(self, context, schema) -> dict: ...
    def received_context(self, context) -> list[dict]: ...
    def received_facts(self, context, schema) -> dict: ...
    def validate_received_report(self, context, form, schema) -> None: ...
    def record_admission(self, context, form, schema, operation_key) -> list[str]: ...
    def resolve_own(self, context, reference, namespace) -> bool | None: ...
    def resolve_received(self, context, reference, namespace) -> bool | None: ...
```

Fact sources are exactly `bvbrc_fastqutils_measurements`, `_components`,
`_categories`, `_populations`, `_associations`, `_requirements`, `_request_status`.
Each row is `{source_ref: actual execution_result reference, field: field_ref,
value: ProjectedField}` restricted to its selected family. Parent forms use
these original descriptors. Raw text labels/tokens remain in saved documents;
projection uses source-validated native label identifiers. Semantic validation
enforces FactRecord unions even when the communication grammar renders a
nullable flat structure. No unrestricted findings/instructions are introduced.

Return failures use `FastqUtilsReturnError` with `.code`, `.path`, and
`.diagnostics=[{code,path}]`, stable prefix `bvbrc_fastqutils_return_`; suffixes
match the proteome pattern: publication_required, original_task_conflict,
original_selector_conflict, original_adapter_conflict, original_adapter_pin_conflict,
saved_projection_invalid, returned_facts_invalid, returned_facts_conflict,
publication_owner_conflict, original_commission_required, original_commission_conflict,
frozen_form_conflict, frozen_facts_conflict, unsupported_return_owner,
actual_source_required, duplicate_returned_field, admitted_form_conflict.
No error echoes native operands. Current own facts use the latest selected
publication, including latest partial failure; historical admitted facts use
their named original publication. Never resurrect an older success.
