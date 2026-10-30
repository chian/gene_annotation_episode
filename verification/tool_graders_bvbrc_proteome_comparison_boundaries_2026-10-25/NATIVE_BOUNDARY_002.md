# Accepted native-format boundary for GenomeComparison

This additive contract accepts the native-format workload from proposal001 with
the corrections below. Proposal001 and its full schema remain historical
proposals. This document does not accept its unimplemented producer manifest,
whole sheet, calculator or API return shapes as installed capabilities. The
immutable user goal retains the complete GenomeComparison requirement, including
full emitted alignments and exact input associations. A legacy summary parser
cannot complete that requirement.

## Why this boundary differs from the proposal

Root inspected the complete bidir_best_hits implementation, the application's
input/reference ordering, scientific comparison, numerical/table/JSON writers,
input acquisition and upload list. The actual writer emits a custom projection;
its dependency keeps only the first HSP of the chosen subject. The published
subject coverage is abs(end-start)/length, rounded to three decimal places; it
omits the inclusive endpoint. This value must retain that meaning and must not
be silently repaired or renamed paired coverage. The native identity value is
a fraction despite the field name percent_identity.

The proposal incorrectly couples its native parser to a new copy of API task
custody and collapses the existing three-state object completeness into a bool.
That is not accepted. A native parser receives bytes and their content identity;
the API adapter authenticates task, receipt, manifest membership and possession
through the existing service contracts. Keep those responsibilities separate.

## Exclusive ownership and exported interface

A fresh native-format worker owns only new:

- gene_annotation_episode/bvbrc_proteome_native.py
- gene_annotation_episode/bvbrc_proteome_native_contracts.py
- gene_annotation_episode/bvbrc_proteome_native_schemas.json
- tests/test_bvbrc_proteome_native.py
- verification/tool_graders_bvbrc_proteome_native_2026-10-25/

No shared registry, resource binding, existing source, method_loop, estimator,
evidence-axis, literature, tool information or deployment changes belong here.
No module imports this new parser into a current Workflow until root performs
the later integration. Existing source closures remain frozen during the two
ongoing alignment Workflow tests; the new unimported files are independent.

```python
def parse_genome_comparison(
    content: bytes, *, source: dict, declared_format: str,
    source_contract: dict,
) -> dict:  # NativeProjectionResult
    ...

def native_schema(name: str) -> dict:
    ...

def validate_native_projection(value: dict) -> dict:
    ...
```

The only declared formats are genome_comparison_json_v1 and
genome_comparison_tsv_v1. The accepted closed definitions are in the additive
NATIVE_CONTRACTS_002.json, generated from the explicitly named proposal subset.
This is a data contract, not a numerical scoring language. The implementation
uses ordinary functions, and must package its schema rather than load a file
from verification at runtime.

NativeSource is exactly {content, body_complete, object_complete}. content is
the existing ContentBinding shape, preserving source_ref, artifact_field,
artifact_ref, sha256 and byte_count. object_complete remains yes/no/unknown.
SourceField.source_ref is the content's source_ref, never its artifact_ref.
Validate the actual supplied byte digest and byte count before decoding. This
proves byte correspondence only; it does not prove possession or task custody.
The parser must not invent a task, receipt, deployment or producer witness.

SourceContract retains the exact inspected source identity and its separately
declared deployment status. Unobserved deployment stays unobserved. Recording
caller-supplied evidence here does not authenticate a deployment; that is a
later adapter responsibility. A different declared source version is rejected
as incompatible, not silently interpreted using the inspected writer.

## Complete native records and numerical meaning

Use the exact twelve reference fields and ten comparison fields in proposal001.
Preserve every reference record and every emitted comparison association in
source order, including malformed and duplicate rows. Preserve all tracks;
comparison ordinals come from native comp_genome_N keys/header blocks, never
display names or the compressed Circos filenames. A JSON display-name entry
alone does not establish that a track was compared.

Each native scalar retains value/null, presence and source location. Numeric
values additionally retain their original decimal spelling. JSON numeric
scalars and strictly numeric decimal strings may be normalized; booleans,
NaN/Infinity and unit-bearing strings are invalid. Lengths/gene numbers are
nonnegative integers; fractions are finite and in [0,1]. Coordinate values stay
native numbers with no inferred genomic convention. Missing/null/blank/invalid
and measured zero remain distinguishable. Do not fill missing values from the
other fields, derive alignment lengths, infer E-values or reconstruct HSPs.

NativeReferenceRecord.row_ordinal is the zero-based reference data-record
ordinal, including malformed data rows. NativeAssociationRecord records that
same reference ordinal and the exact comparison ordinal. For JSON, source
pointers address the original object. For TSV, /rows/N/C addresses zero-based
physical line N and column C in the deterministic tabular parse; SourceField
row_ordinal is that physical line. The reference data ordinal excludes the two
identified header lines. NativeProjection.physical_record_count counts data
records including malformed ones, excluding headers. The explicit locations
prevent headers/sorting from changing a protein association.

Find the TSV field header by the exact full field sequence and ten-field
comparison blocks, allowing skipped comparison numbers. Identify the matching
display-name header without assuming either header is one of the first two
physical lines: the native producer sorts headers with data. Reject ambiguous
headers. Preserve malformed row locations and raw bytes; never recover an
unescaped embedded tab/newline by guessing columns or joining records.

Unknown native field paths remain listed, with exact raw bytes retained under
the supplied content binding. Do not silently drop them or claim full format
compatibility. Duplicate JSON members are rejected before dictionary creation.
Repeated reference IDs remain separate source rows with an ambiguity diagnostic;
they are not deduplicated into apparently independent protein observations.

## Completeness and failures

Result is exactly {status, value, requirements, diagnostics}. status describes
this parsing operation, not scientific completion or future expected credit.
Usable rows survive local malformed-row failures. Top-level malformed JSON,
invalid encoding, incompatible layout/profile or byte-binding mismatch returns
invalid with value null and specific fixed diagnostics. Raw bytes remain with
the original content record; do not invent a salvaged JSON object.

A syntactically valid JSON document may be parsed even when transfer/object
completion is no or unknown. Such a projection is partial_or_unknown_artifact,
with partial status and the exact completeness qualification; its observed
rows do not establish the entire source population. A complete received body
with object_complete=yes is complete_document, subject to row/layout checks.

For an incomplete TSV artifact, retain complete physical prefix lines only;
do not treat an unterminated final line as a complete record. A complete body
and object may have a final row without a newline. Its source bytes and layout
remain checkable. No absence, full population denominator or native search
completion follows from partial data.

Malformed cells must not become valid numeric values. A row-level invalid flag
does not erase individually recorded valid cells. Later sheet/calculator code
must explicitly decide whether an identity or count requires the whole row.
Qualifications about unavailable full HSPs or unobserved deployment do not turn
an otherwise successfully decoded legacy record into a fabricated failure.

## Handoffs and verification

The native worker supplies validated NativeProjectionResult objects, packaged
schemas, numerical lexeme examples, synthetic fixture origin and exact hashes.
The input/sheet worker will consume these unchanged reference/association
ordinals and ContentBindings plus the existing OriginalTask and separately
authenticated inventories. It owns protein/feature joins and denominators.
The calculator worker owns aggregate numerical components. The API adapter
owns task/manifest/receipt authority and projection of requested facts. No
whole group waits for a parser implementation to write against this contract.

Required native checks include exact JSON/TSV shared measurements; numeric vs
numeric-string values; measured zero vs omitted/null/blank; skipped comparison
numbers; reordered headers; artificial coordinates preserved without conversion;
unknown fields; malformed rows; duplicate keys/IDs; invalid fractions/lengths;
byte hash/length mismatch; partial body vs no/unknown complete object; truncated
JSON; complete TSV prefix; complete no-newline TSV; and detached output copies.
Prohibit network, subprocess, model, API client and scientific-calculator calls.

Fixtures reconstructed from the inspected writer must be called synthetic.
There is no retained actual GenomeComparison output in this investigation.
Passing synthetic format tests does not establish native deployment, execution,
full emitted HSP retention, numerical sheet integration or episode returns.

The parallel producer-retention workload remains required: exact input FASTAs
and metadata, full stdout/stderr for both directional commands before reduction,
all emitted queries/subjects/HSPs, command/version/exit/completeness/limit facts,
and actual uploaded artifact associations. Native hit limit5 remains explicit;
it must never be relabeled an uncensored database population. No existing API
or credential is assumed to permit installing that producer change.
