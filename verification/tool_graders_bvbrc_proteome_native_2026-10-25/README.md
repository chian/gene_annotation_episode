# GenomeComparison legacy native parser verification

This is useful native-format component work under accepted boundary 002. It is
not the complete GenomeComparison scientific capability. The inspected producer
discards full directional BLAST reports and keeps first-HSP/best-subject
summaries. There is no retained real GenomeComparison output in this work.
Every native-looking fixture here is **synthetic, reconstructed from the
inspected writer**. No native program, scientific API/HPC job, or model ran.

## Delivered interface and ownership

New package files are `bvbrc_proteome_native.py`,
`bvbrc_proteome_native_contracts.py`, and
`bvbrc_proteome_native_schemas.json`. The only test source is the new
`tests/test_bvbrc_proteome_native.py`. No existing Workflow imports these modules;
no existing source, registry, factory, library, estimator, runtime, evidence-axis,
literature or package configuration was edited by this workload.

```python
parse_genome_comparison(content: bytes, *, source: dict,
                        declared_format: str, source_contract: dict) -> dict
native_schema(name: str) -> dict
validate_native_projection(value: dict) -> dict
```

`parse_genome_comparison` returns exactly `status`, `value`, `requirements`,
`diagnostics`. `value` is a NativeProjection or null. `native_schema` returns a
detached entry-point schema with reachable definitions. The packaged JSON is
byte-for-byte identical to accepted NATIVE_CONTRACTS_002.json (16 definitions,
SHA256 `c84fecffe0170b7c77948f411593a55ae63e902f976e8a42463a0053c1a1f01d`).
`validate_native_projection` accepts the projection, not the envelope, checks
shape and internal relationships, and returns a detached copy. Invalid supplied
projections raise NativeValidationError, a ValueError with a fixed `code` and
`path`; no source value is interpolated into the exception text. Schema loading
occurs once from the sibling package file at module import. Parser/validator
calls perform no IO, acquisition, external execution or scientific calculation.

**Packaging handoff:** current pyproject.toml explicitly lists only the existing
AppService schema asset. Root's later integration must add this new schema asset
to package-data before a wheel can claim to include it. The frozen configuration
was intentionally not edited here.

## Field meanings

| Output | Exact meaning |
|---|---|
| `status=ok` | Supplied legacy document decoded without format/cell errors and the supplied body/object completeness is complete. HSP retention, deployment and name-only-track qualifications may remain. It is not scientific completion. |
| `status=partial` | Locally malformed/unsupported data or incomplete/unknown acquisition; retained valid cells and neighboring records remain available. |
| `status=invalid`, `value=null` | No projection from invalid UTF-8, malformed/duplicate-member JSON, incompatible top layout/version/format, ambiguous table headers or a content binding mismatch. No prefix JSON is invented. |
| `source.content` | Existing ContentBinding: source_ref, artifact_field, artifact_ref, sha256, byte_count. Digest and byte count match supplied bytes before decoding. This establishes byte correspondence only, not task custody or possession. |
| `source.body_complete`, `source.object_complete` | Separate transfer flag and exact yes/no/unknown object state. No boolean replacement of object completeness. |
| `source_contract` | Exact inspected application/dependency identities and caller-declared deployment status/evidence, preserved unchanged. The parser cannot authenticate deployment evidence. Different source identities/deployment declarations are rejected. |
| `tracks` | All declared JSON display tracks and emitted comparison tracks, or all exact TSV field blocks, in native order. Track keys are actual ref_genome / comp_genome_N identifiers; skipped N values are retained. Duplicate display labels are never identifiers. |
| `materialization` | Reference row set, explicit TSV field block, emitted JSON association, or unknown for a name-only JSON track. A display name does not prove a comparison ran. |
| `reference_rows` | Every source data record, including malformed/non-object JSON entries and malformed TSV physical rows. Data ordinals include malformed records but exclude the two detected TSV headers. |
| `associations` | Every emitted comparison-key group in JSON, including malformed groups; every nonblank TSV comparison block. All-blank TSV blocks do not manufacture associations. Exact reference and comparison ordinals remain attached. |
| `native_pointer`, `source_field` | Original JSON pointers or deterministic TSV `/rows/N/C` locations. N is the zero-based physical line, including header lines; source_field.row_ordinal is N for TSV. JSON scalar source row ordinals are the feature_matches index; genome_names fields have null row ordinal. source_ref is never replaced by artifact_ref. |
| `reference_row_key`, `association_key` | Stable keys local to the projection: ref_genome/row/N and comp_genome_K/row/N. They are native record identities, not inventory protein joins. |
| `NativeNumber.value` | Normalized finite plain-JSON number; null for non-value states. Its `lexeme` preserves original decimal spelling, including JSON numeric token exponent/case/trailing zeros. Bounds are checked using the decimal spelling before float rounding. Unsupported numeric overflow/underflow is invalid rather than becoming infinity or a false zero. |
| `NativeString.value` | Original string, including empty text for blank; null for omitted, explicit_null or invalid type. |
| `presence` | `value`, `omitted`, `explicit_null`, `blank`, `invalid` remain distinct. Numeric blank has value null and lexeme empty string; numeric omitted/null have null lexeme. A measured zero is value. |
| `gene`, `aa_length` | Native nonnegative integer values. gene is the producer's extracted peg identifier number; it is not a newly inferred genomic order. Missing length is never reconstructed from coordinates. |
| `percent_identity` | Native fraction, despite its name: first selected HSP's identical alignment columns / alignment columns, rounded to 3 decimals by the dependency. Original counts are unavailable. |
| `seq_coverage` | Native legacy fraction: abs(subject_end-subject_start)/subject_length, rounded to 3 decimals. The inclusive endpoint is omitted by the producer. It is not corrected span or paired-residue coverage. |
| `start`, `end`, `strand` | Native metadata or artificial drawing values; no inferred genomic coordinate convention or conversion. |
| `hit` | Native category bi (<->) or uni (->); other supplied strings are preserved with an invalid-category diagnostic. No orthology probability is assigned. |
| `valid`, row `diagnostics` | Local decoding/field validity. Invalid whole rows do not erase individually retained valid cells. Duplicate IDs receive ambiguity qualifications, remain separate records and are not deduplicated. Later joins/calculators must enforce their own population/whole-row requirements. |
| `physical_record_count` | Number of retained data records including malformed ones, excluding detected table headers; never an input proteome size. |
| `table_field_order` | Exact complete TSV field header sequence. Empty for JSON. |
| `projection_completeness` | complete_document for a complete received artifact, partial_or_unknown_artifact for syntactically valid incomplete/unknown JSON, complete_prefix_only for incomplete TSV. Local row validity remains separate. Fatal documents return no projection. |
| `unsupported_field_paths` | Exact paths for unknown JSON fields and extra TSV cells. The original bytes remain bound under source.content; no unknown values are silently treated as compatible measurements. |
| `diagnostics` | Closed code, severity (error/qualification), source path, typed scope and source fields. No unrestricted explanation or invented recorded fact. |
| `requirements` | Closed code, exact affected scope, required input kind and source fields. The parser does not acquire these inputs. |

TSV headers are found by their exact twelve-field reference sequence and complete
ten-field comparison blocks, then the matching sparse display-name row. They can
appear anywhere in the native sort. Multiple matching headers are ambiguous and
fatal. Wrong-width rows retain literal physical positions under the detected
columns, with invalid flags; tabs/newlines are never guessed, joined or repaired.
Incomplete TSV discards the unterminated final byte fragment before decoding the
complete prefix, so a transfer cut mid-codepoint does not destroy valid earlier
rows. Invalid UTF-8 in any retained complete line remains fatal. A complete body
and complete object can contain a final data row without a newline.

## Checkable numerical example

The synthetic JSON and sorted-header TSV both retain two reference rows and
three associations:

| Reference data ordinal | Actual comparison ordinal | Native subject | percent_identity | seq_coverage |
|---:|---:|---|---:|---:|
| 0 | 2 | subjectA | 0.875 | 0.990 |
| 0 | 4 | subjectB | 0.000 | 0.500 |
| 1 | 4 | subjectA | 0.875 | 0.990 |

Comparison 1 is not substituted for comparison 2. Equal comparison display
labels do not merge tracks. The TSV data lie at physical lines 0 and 2; its
display-name and field-name headers lie at physical lines 1 and 3. The last
association's identity source is exactly `/rows/2/30`. `0.990` remains numeric
0.99 with lexeme `0.990`, not 0.99 percent or corrected coverage 1.0. An artificial
100-aa drawing interval 1..303 remains 1..303, with omitted aa_length unchanged.
Another JSON fixture retains numeric spelling `8.750E-1` -> 0.875 and
`1.00e+02` -> 100 without discarding the spelling. These are preservation
examples, not executed alignments or aggregate calculator outputs.

## Verification and explicit unfinished work

Focused pytest runs are retained additively as TEST_RUN_001.log,
TEST_RUN_002.log and TEST_RUN_003.log: 78 tests passed in 2.28 s, then 85 tests
passed in 2.42 s after additional relationship checks, then **86 tests passed in
2.46 s** after covering an unsupported empty JSON member. No test failure was
overwritten. A setup read attempt using `python` failed because that command is
absent; subsequent reads and tests used python3 / .venv/bin/python. A requested
git-status inspection failed because this workspace has no git repository;
explicit file hashes and scoped write records establish the delivered files.
Neither inspection failure executed scientific work.

Coverage includes JSON/TSV measurement agreement; original numeric spelling;
strict numeric strings, booleans, NaN/Infinity, bounds and malformed cells;
zero/null/omitted/blank distinctions; skipped comparison numbers; source order;
moved, missing and ambiguous headers; native artificial coordinates; unknown
fields; malformed rows surviving among valid neighbors; duplicate JSON keys and
reference IDs; byte hash/size mismatch; source version mismatch; three-state
object completeness; truncated JSON; complete TSV prefixes and no-newline final
rows; detached copies; and pure calls with filesystem, socket and subprocess
entry points prohibited. All 16 schema entry points pass Draft 2020-12 structural
validation. Runtime validation additionally checks finite strict numeric types,
source bindings, record/track relationships, physical header/row locations,
lexeme/value agreement, duplicate qualifications and completeness relationships.

No complete scientific tool, tool-info binding, API adapter, inventory/metadata
join, numerical sheet, score calculator, producer retention repair, deployed
service compatibility, retained native job output, live execution or episode
return is established here. Required future producer work still includes exact
input FASTAs/metadata, complete stdout/stderr from both directional commands
before first-HSP/best-subject reduction, all emitted queries/hits/HSPs, actual
command/version/exit/completeness/limit facts and uploaded artifact associations.
The inspected hit limit 5 is not an uncensored database population. Root owns
integration and the fixed progress rows. Historical proposal001's future
manifest/report schemas are not installed by this component.
