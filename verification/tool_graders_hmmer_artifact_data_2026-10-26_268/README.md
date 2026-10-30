# Workload268: pure HMMER artifact sheets and calculators, 261/A1

This implements the two pure ports frozen in
`verification/tool_graders_hmmer_preparation_2026-10-26_261/ARTIFACT_DATA_CONTRACT_001.md`.
The separate operations remain hmmconvert (`ascii`, `binary`, `legacy_hmmer2`),
hmmfetch (`single_key`, `key_file`, `index`) and hmmpress (`index`). Counts,
probability differences, field losses and bundle sizes validate transformations,
selection and index artifacts. None is gene-function confidence or new credit.

Only the two assigned modules, two matching tests and this verification directory
were written. M1 was reused unchanged. No registry, producer, execution behavior,
episode prompt, result publisher, annotation-credit policy or inventory row was
edited. Production integration remains root/267's work.

## Exact ports and top-level shapes

```python
from gene_annotation_episode.hmmer_artifact_data import populate_hmmer_artifact_sheet
from gene_annotation_episode.hmmer_artifact_calculations import calculate_hmmer_artifact_components

sheet = populate_hmmer_artifact_sheet(
    operation=operation, inputs=inputs, outputs=outputs,
    model_extractions=model_extractions, artifact_bindings=bindings)
components = calculate_hmmer_artifact_components(
    sheet, parameters={"probability_tolerance": 1e-4, "expected_revision": "3/f"})
```

`operation` has exactly `program`, `mode`, `engine_version`, `settings`.
The first three are strings; settings is the caller's explicit native flags and
resolved values as a dictionary. The sheet copies the operation unchanged.
Single-key retrieval requires `settings.key`. Neither port supplies an implicit
native call, retry, conversion, SSI discovery, receipt, exit code or model call.

`inputs` and `outputs` are maps from role to lists of
`{occurrence, content: bytes}`. Each occurrence has exactly the M1 fields:

```text
{occurrence_id: nonempty string, direction: input|output, role: nonempty string,
 ordinal: nonnegative integer, artifact_ref: nonempty string,
 sha256: 64 hexadecimal characters, size_bytes: nonnegative integer,
 completeness: complete|partial|unknown}
```

Ordinal order is zero-based, contiguous and unique within direction/role.
Different occurrences never merge because their bytes or names match. The
caller retains complete bytes; the sheet retains their exact supplied references,
independently measured digest/size, full decoded arrays and native facts.

Input roles: `models`; optional `ssi` for retrieval; `keys` for key-file mode.
Output model roles are `converted_models`, `fetched_models`, `binary_models`.
Index roles are `ssi` or the press bundle `binary_models`, `ssi_index`,
`msv_profiles`, `remaining_profiles`. Outputs can also retain `stdout`, `stderr`.
Hmmconvert stdout and converted_models must have identical bytes but distinct
occurrence identities; only converted_models supplies the output population.
Press binary_models is included in M1 extraction, with unsupported/null results
until M1 supplies a decoder. It is never silently excluded from accounting.

`model_extractions` is a list of exact six-field M1 envelopes. The reader reruns
the existing pure `extract_hmmer_models` on the supplied bytes, explicit format
and original occurrence and checks exact equality. It accepts no substituted or
edited envelope. Duplicate envelopes cannot double count an occurrence. Invalid
or absent envelopes are reported; independently valid envelopes survive.

```text
sheet = {
 schema: "hmmer_artifact_sheet_v1", operation,
 artifact_occurrences: [exact M1 occurrences],
 model_extractions: [exact checked M1 envelopes],
 input_records: [full M1 model records in occurrence/record order],
 output_records: [full M1 model records in occurrence/record order],
 native_rows: [the closed row union below],
 associations: [the closed association union below],
 artifact_bindings: [the supplied six-field metadata dictionaries],
 issues: [issue]
}
```

Every M1 header, calibration parameter, optional flag, cutoff, composition,
initial insert/transition cell, model position, annotation and native probability
token remains in the full records. No second probability parser exists. Exact
M1 nested shapes are unchanged from
`verification/tool_graders_hmmer_model_data_2026-10-26_262/README.md`.
Names/accessions are read from ordered native headers and are not identity keys.

## Exact native rows and joins

`ROW_FIELDS` in the reader exports the closed field sets for each kind. Every
native row has `kind`, `row_key`, `occurrence_id` plus the fields shown below.

| Kind | Additional exact fields |
| --- | --- |
| `artifact_metadata` | `measured_size_bytes`, `measured_sha256`, `signature_hex`, `trailing_signature_hex`, `format`, `revision`, `byte_order`, `offset_width`, `framing_state`, `decoded_record_count`, `internal_content_state` |
| `requested_key` | `request_ordinal`, `key`, `tokens`, `raw_line`, `locator`, `request_source` |
| `index_summary` | `locator`, `text`, `tokens`, `model_count`, `primary_name_count`, `accession_count`, `accession_clause_supplied` |
| `reported_path` | `locator`, `text`, `role`, `path` |
| `diagnostic` | `locator`, `text`, `tokens`, `code` |

`artifact_metadata` measures supplied bytes. `signature_hex` is the first up to
four bytes; `trailing_signature_hex` is the last up to four. `format` is null or
`hmmer3_ascii`, `hmmer2_ascii`, `hmmer_binary`, `ssi`, `msv_profiles`,
`remaining_profiles`; `revision` is null, `3/a` through `3/f`, `2.0`, or SSI
`3.0`. `byte_order` is null, big or little; it describes decoded framing words,
not unverified contents or host architecture. `offset_width` is an SSI header
quantity (4/8 when recognized), otherwise null. `framing_state` is `unknown`,
`prefix_recognized`, `prefix_and_terminal_marker`, `truncated` or `invalid`.
`decoded_record_count` is always null in this framing-only row;
`internal_content_state` is always unknown. Real model populations come from M1.

Framing recognizes native model/SSI/SSE magic words. It checks minimum header
space (16 bytes for model header, 54+3*offset_width for SSI), and the expected
last magic word for optimized profiles. These checks do **not** decode all SSI
records, offsets, model bodies or optimized profiles and do not prove readiness
for a search. A well-framed opaque artifact still has unknown internal validity.

For file rows, locator is exactly
`{artifact_ref, line, byte_start, byte_end}`: line is one-based; byte intervals
are zero-based half-open. A requested-key locator additionally has
`token_byte_start`, `token_byte_end`. `raw_line` preserves the native line
excluding LF; `tokens` retains all its whitespace-delimited tokens, even though
only the first is the requested key. LF defines the native line; standalone CR
does not create another key request. Initial native whitespace is skipped.
A first token starting `#` marks a comment; an embedded `#` remains in the key.
Later tokens are ignored by native hmmfetch but retained here. Blank/comment
lines retain their byte positions through the caller's complete artifact.

Single-key rows use row_key `operation.settings.key`, occurrence_id/locator/
raw_line null, tokens `[key]`, request_source `single_key`. Key-file rows use
request_source `key_file`. Request ordinals count requested occurrences, not
unique tokens. Native names/aliases, repeated tokens, line order and duplicates
remain separate.

`index_summary` counts are actual native unsigned integers with source tokens.
The grammar must match the selected program's `Indexed` or `Pressed and indexed`
line. In this known grammar an omitted accession clause means actual zero
accession keys. It does not mean missing. More than one summary is ambiguous;
none gives missing counts, not zeros. Reported paths are native strings and do
not authenticate bindings. Diagnostic codes are `duplicate_key`, `missing_key`,
`native_error`, `native_message`, `invalid_index_summary`; the full native line
is retained. No process return code is inferred from silence or log strings.

Associations are separate from native rows:

```text
key_resolution = {
 kind: "key_resolution", association_id, key_row_key, key,
 source_record_keys: [all matching source occurrences],
 selected_source_record_keys: [source occurrences selected under native mode],
 output_record_keys: [label/order-compatible returned occurrences],
 state: resolved|missing|ambiguous|unknown,
 lookup_state: eligible|duplicate_error|blocked_after_error,
 basis: indexed_key_order|unindexed_source_order|first_source_match
}

model_pair = {
 kind: "model_pair", association_id, key_row_keys: [requested-key row keys],
 source_record_keys: [zero or one source record key],
 output_record_keys: [zero or one output record key],
 state: matched|mismatch|missing_output|unexpected_output|unavailable,
 basis: ordered_conversion|indexed_key_order|unindexed_source_order|first_source_match
}
```

`matched` means native mode/order and NAME/ACC/alphabet/length are compatible.
The calculator separately compares the complete bodies. A matched label does
not itself prove numerical equivalence, custody or unique scientific identity.
Conversion keeps native record order. Indexed retrieval follows key order and
may represent one source occurrence several times through name/accession aliases.
An unindexed key-file scan follows source order and emits one model occurrence
once for any matching key. Unindexed single-key mode selects the first matching
source occurrence while retaining all candidates; it does not assert uniqueness.

An indexed later missing or repeated key stops the expected native output at the
valid prefix. Later requests are preserved with blocked_after_error. Unindexed
duplicate tokens fail before the scan. Unindexed missing keys can coexist with
successful native exit and still leave requests unfulfilled. With an unsupported
source decoder, absence of decoded matches becomes unknown/unavailable rather
than a fabricated missing key, zero selected population or unexpected output.

`model_label_duplicate` is a factual collision qualification. In particular,
repeated output NAME/ACC values are expected for indexed alias retrieval. A
nonempty issues list is not a blanket failure rule.

## Supplied bindings and authenticated custody

```text
artifact_binding = {
 artifact_occurrence_id, source_occurrence_id, source_sha256,
 producer_attempt_id, staged_source_stem, actual_relative_path
}
```

The agreed binding scope is input SSI, output SSI and the four pressed members.
Conversion/fetch model outputs use their explicit M1/original-bundle associations;
the pure validator does not require an extra generic binding for them.
All six are nonempty strings. Source must identify the supplied input models
occurrence and digest. Artifact must identify the appropriate supplied artifact
occurrence. Paths must be confined relative paths; index member paths must be
staged_source_stem plus the exact role suffix. Press members are also checked
for the same supplied source, source digest, attempt and staged stem.

These are equality/relationship checks on **supplied metadata only**. Missing
metadata gives unknown; inconsistent metadata gives fail. A coherent matching
dictionary cannot establish historical production, a current index's content,
or an authenticated receipt. `authenticated_artifact_custody` remains unknown
at the pure port. Root must join and authenticate the actual producer/capture
records before making a custody claim. A filename or success status alone is
insufficient. No native probe, conversion or search is launched to fill a gap.

## Exact calculation shapes and numerical meanings

```text
calculations = {
 schema: "hmmer_artifact_components_v1", operation, parameters,
 rows: [closed calculation row union], checks: [check], issues: [issue]
}

component = {value: number|null,
 state: present|missing|incomplete|incompatible|nonfinite|failed,
 unit: string, inputs: [operand dictionaries]}

check = {code: closed CHECK_CODES, state: pass|fail|unknown|not_applicable,
 row_key: string|null, field: string|null, inputs: [operand dictionaries]}

issue = {code: closed ISSUE_CODES, stage: extraction|calculation,
 occurrence_id: string|null, row_key: string|null, field: string|null, details: dict}
```

`parameters` stores the effective explicit probability_tolerance (default 1e-4)
and optional expected_revision (`3/a`..`3/f` or `2.0`). Invalid parameters are
reported without rescaling probabilities. Unknown additional parameters are
invalid. There is no combined confidence score. Every component identifies its
actual occurrence, record/field/cell, selected population or explicit parameter;
the mean difference identifies compared_cell_count as its denominator.

All calculation rows have `kind`, `row_key` plus these exact fields; names ending
in count, bytes, difference, length or sum below contain components, not scalars.

| Kind | Additional exact fields |
| --- | --- |
| `population` | `direction`, `record_keys`, `decoded_model_count`, `complete_model_count`, `primary_name_count`, `accession_count`, `distinct_primary_name_count`, `distinct_accession_count`, `model_artifact_bytes` |
| `model_comparison` | `association_id`, `source_record_key`, `output_record_key`, `relationship_state`, `source_length`, `output_length`, `length_difference`, `cell_differences`, `compared_cell_count`, `source_cell_count`, `output_cell_count`, `max_absolute_probability_difference`, `mean_absolute_probability_difference`, `optional_fields`, `retained_optional_field_count`, `lost_optional_field_count`, `changed_optional_field_count`, `gained_optional_field_count` |
| `key_population` | `requested_key_count`, `distinct_key_count`, `resolved_key_count`, `missing_key_count`, `ambiguous_key_count`, `unknown_key_count`, `fulfilled_key_count`, `duplicate_key_occurrence_count`, `selected_source_occurrence_count`, `returned_model_occurrence_count`, `expected_returned_model_occurrence_count`, `duplicate_representation_count` |
| `artifact` | `occurrence_id`, `size_bytes`, `format`, `revision`, `byte_order`, `offset_width`, `decoded_record_count`, `supplied_binding_state`, `authenticated_custody_state`, `internal_content_state` |
| `index_summary` | `native_row_key`, `native_model_count`, `native_primary_name_count`, `native_accession_count`, `decoded_input_model_count`, `decoded_input_primary_name_count`, `decoded_input_accession_count`, `model_count_difference`, `primary_name_count_difference`, `accession_count_difference` |
| `bundle` | `member_occurrence_ids`, `member_count`, `bundle_byte_sum` |

The full probability and optional-field nested rows are:

```text
cell_difference = {
 field, position: native one-based position|0 for initial|null for composition,
 cell_index: zero-based integer, symbol: string|null,
 source_token: string|null, output_token: string|null,
 source_probability: component, output_probability: component,
 difference: component, absolute_difference: component
}

optional_field = {
 field, source_present: boolean, output_present: boolean,
 source_value, output_value,
 state: retained|changed|lost|gained|unknown
}
```

Positions in field paths (`positions.0.match`) are zero-based array indices;
the separate native position field is one-based. Header optional values are
ordered arrays of native token arrays, preserving repeats. Annotation values
are the original M1 `{token,value}` objects. STATS is retained before/after as
actual token arrays; incompatible legacy statistic meanings are not silently
equated. Field-count units count these inspectable header/annotation paths,
not biological evidence dimensions.

| Numerical component | Formula, population, unit and availability |
| --- | --- |
| Decoded/complete model counts | Counts of supplied decoded model occurrences / terminated issue-free records, with underflow alone not making native data incomplete. Unsupported decoder or absent artifact gives null, not zero. A partial population retains its available count with incomplete state. |
| Name/accession counts | Count actual scalar native NAME/ACC headers; distinct counts use exact tokens. Native missing ACC is no accession key. Duplicate records never collapse the model count. |
| Lengths/difference | Native LENG and output minus source LENG, in match states. Missing or invalid scalars remain unavailable. |
| Individual probability difference | Output probability minus source probability for corresponding composition, initial insert/transitions and every position's match/insert/transitions. M1 validates token/log/probability consistency. No normalization or rounding is inserted. |
| Compared-cell denominator | Number of cells for which both probabilities are available in a compatible proven model pair. Every comparable cell remains in the array; incompatible, underflow and missing cells have null differences. |
| Max/mean absolute differences | Max(abs(delta)); sum(abs(delta))/number of compared cells. A partial summary retains its actual value with incomplete/nonfinite/incompatible state and cannot pass whole-body equivalence. Whole-body equivalence needs all comparable arrays, all declared positions and termination. |
| Optional-field counts | Count retained/lost/changed/gained exact optional field paths, with their source/output values retained. Legacy unsupported records do not produce fake zero-loss or identical-field claims. |
| Requested/distinct keys | Number of requested key occurrences / number of distinct exact first-token strings. Duplicate occurrence count is their difference. |
| Resolved/missing/ambiguous/unknown keys | Counts of the four source-resolution states. This is source lookup against supplied decoded data, distinct from native execution and actual fulfilled requests. |
| Fulfilled keys | Number of request occurrences associated with at least one returned, label/order-compatible model. A valid output prefix is kept after later native failure. Numerical equivalence remains a separate check. |
| Selected/returned occurrences | Distinct selected source record keys; count actual decoded output records. The expected output count preserves native mode multiplicity. Unsupported source decoding leaves selected/expected populations unavailable. |
| Duplicate representations | Number of matched returned source references minus distinct matched source references. A partial/unmatched return population is marked incomplete. This never assumes different names/files are independent evidence. |
| Native index counts/differences | Actual summary counts versus full decoded input model/name/accession occurrence populations; difference is native minus decoded. Comparisons are unknown unless the full required source population is available. |
| Byte sizes/bundle sum | Exact supplied byte counts. Bundle sum is the sum of the four actual member sizes, 16,024 in the retained example; missing members retain a partial measured sum with incomplete state. Byte size is not a decoded record count. |

No uncertainty is fabricated; quantities reflect the precision of actual rounded
native tokens. Binary/legacy unknowns, missing values, malformed native values,
partial captures and measured zero remain separate.

## Numerical examples, receipts and limitations

`examples001/examples/` contains 24 full sheet/component pairs, all required
native conversion revisions and fetch/index/press cases, full provenance and
source hashes. The additional synthetic changed-probability example is explicitly
labeled and retains its supplied mutated HMM bytes. Its strict and relaxed
calculations use the same saved sheet. No new native HMMER execution occurred.

| Retained case | Checkable result |
| --- | --- |
| hmmconvert ASCII, all 3/a..f | One input and one output model; LENG 12, length difference 0; all 611 probability cells compared; max/mean absolute difference 0. |
| Annotated conversion 3/a | CONS/MM header and position annotation losses retained explicitly; actual STATS changes retained. VMU is -5.908600; modern VITERBI is -6.1309, not an equivalent invented value. |
| hmmconvert binary / HMMER2 | 2,725 / 5,175 actual bytes; decoded output counts null; body equivalence unknown. Explicit retained binary-to-ASCII native output is separate and does not fill the original binary's unavailable decoder. |
| Fetch two name/accession aliases, unindexed | 2 requested, 2 resolved, 1 selected source occurrence, 1 returned model occurrence, 0 repeated returned representations. |
| Same aliases, indexed | 2 requested, 2 resolved, 1 selected source occurrence, 2 returned model occurrences, 1 repeated representation. Each returned body compares all 611 cells. |
| Indexed/unindexed later missing key | 2 requested, 1 resolved, 1 missing, 1 fulfilled, 1 complete returned model. Native retained exits are respectively 1/0; exit status is provenance, not inferred by these ports. |
| Indexed repeated identical key | Two requested occurrences, one distinct key, duplicate-key error, retained complete first model. |
| hmmfetch index | 1 native model, 1 primary name, 1 accession; 165-byte SSI; decoded SSI internal population remains unknown. |
| hmmpress | Actual 2,725+165+9,918+3,216 = 16,024 bytes; 1 native model/name/accession. Four supplied associations match; actual custody and internal binary validation remain unknown. |
| Duplicate press input | Two distinct input model records, duplicate primary-name diagnostic, no successful output bundle. |

Independent 60-digit Decimal expectations for changing one native match token
from 0.40547 to 0.50547 are max absolute difference
0.063441410960080871915681712532032901186354461960509625579033 and mean
0.000103832096497677368110772033603981835002216795352716244810201 across
611 compared cells. Tolerance 0.001 fails equivalence; 0.1 passes it. Changing
expected_revision from 3/f to 3/e independently fails the revision check.
Raw cells and original stored calculations are not rewritten.

Verification uses the existing `local_jobs.run_local_job`, `.venv/bin/python`,
PYTHONDONTWRITEBYTECODE=1, 20 GiB RAM, 4 GiB scratch and no wall-time cap.
`check003/receipt.json` records 105 passed tests in 2.21s. The enforcement receipt
confirms cgroup memory/swap limits, unset wall deadline and monitored scratch.
`examples001/receipt.json` records successful bounded example generation. Earlier
receipts remain unchanged historical facts; check001's two failures were incorrect
test expectations (a calibration token and a substring matching “unindexed”).

Tests include retained native formats, duplicate identical occurrences and labels,
alias multiplicity, multiple source ordering, later failed prefixes, wrong/missing
source bindings, wrong attempts, byte/hash/role/ordinal errors, missing and empty
members, native magic/truncation failures, malformed probability cells and finite
log underflow, malformed saved references, independent quantitative differences,
changed parameters and forbidden file/native/network sentinels during pure work.

HMMER2, binary core models, complete SSI key/offset data and optimized profiles
remain without full decoders. Framing checks are not substitutes. There is no
authenticated Store/capture lookup, selected child execution, typed episode
return or production result-path test here. The actual consuming root/267 path
must supply exact occurrences, explicit formats and authenticated bindings, retain
all artifacts and distinguish component verification from production integration.

The authoritative goal, objective and all 16 principles are reread verbatim after
native/source study and at each tool handoff; the exact frozen A1 is reread before
handoff. This discipline is not a deployed runtime gate or source of credit.
