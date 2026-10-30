# Workload 266: pure hmmemit generated-data sheet and calculations

This implements frozen `261/EMISSION_CONTRACT_001.md` (E1), using the exact
completed M1 extraction envelope. Owned production files are only
`gene_annotation_episode/hmmer_emission_data.py` and
`gene_annotation_episode/hmmer_emission_calculations.py`, with their two matching
test files and this verification directory. It does not complete an entire tool,
production result-path binding, selected child execution, typed return or episode
communication. Root owns those consumers. No library, registry, runtime,
annotation-credit or accounting file was changed.

## Ports and complete subshapes

```python
populate_hmmemit_sheet(*, operation, inputs, outputs, model_extraction) -> dict
calculate_hmmemit_components(sheet, *, parameters=None) -> dict
```

Both ports are pure. They read no paths, use no Store/network/LLM, submit no job
and invoke no native generator. The first validates the exact supplied M1
envelope by decoding the supplied model bytes with `extract_hmmer_models` and
comparing the result, including its occurrence. The calculator consumes the
saved sheet and explicit parameters. It never reacquires the models or outputs.

`operation` has exactly `{program: "hmmemit", mode, engine_version, settings}`.
Modes are `sample_core_unaligned`, `sample_core_aligned`, `consensus_simple`,
`consensus_thresholded`, `sample_profile`. `settings` preserves actual native
option names and supplied resolved values unchanged. Missing N, seed, profile
style, L and thresholds stay missing; no native defaults are inserted. Profile
`--local`, `--unilocal`, `--glocal` and `--uniglocal` remain distinct settings.

`inputs` and `outputs` are role maps to lists of `{occurrence, content: bytes}`.
One `inputs.models` payload is required. Output is `generated_sequences` FASTA,
except `sample_core_aligned`, which requires `generated_alignment` Stockholm.
Stdout/stderr have separate occurrences and retained raw lines. When stdout is
also the generated artifact, identical bytes and even the same artifact_ref are
allowed across distinct occurrences. They never become extra generated rows.

Each occurrence has exactly M1's eight fields:

```text
{occurrence_id: nonempty string, direction: "input"|"output", role: nonempty string,
 ordinal: nonnegative integer, artifact_ref: nonempty string,
 sha256: 64 hex digits, size_bytes: nonnegative integer,
 completeness: "complete"|"partial"|"unknown"}
```

Supplied size/digest must match bytes. Role/direction must match the payload map.
Repeated occurrence IDs or repeated direction/role/ordinal slots conflict. Data
from well-shaped payloads remain retained even when their digest/identity fails;
their model associations cannot claim validity. This is distinct from two
different occurrences containing identical bytes.

The sheet has exactly:

```text
{schema: "hmmer_emission_sheet_v1", operation,
 artifact_occurrences: [exact eight-field occurrence, ...],
 model_extraction: exact complete supplied M1 envelope,
 output_records: [record, ...], native_rows: [native_row, ...],
 associations: [record_association | model_population, ...], issues: [issue, ...]}

record = {
 record_key: occurrence_id + "#" + kind + "/" + zero_based_kind_ordinal,
 kind: "fasta"|"alignment"|"alignment_row",
 basis: "generated"|"model_derived",
 occurrence_id, locator, name: string|null, description: string|null,
 sequence: full case-preserved string|null, alphabet: M1 alphabet|null,
 model_record_key: M1 record key|null, sample_ordinal: positive integer|null,
 alignment_record_key: record key|null,
 fragments: [{native_row_key, value, locator, block_index?}, ...],
 state: "complete"|"incomplete"|"invalid", native: native_fields
}

locator = {artifact_ref, byte_start, byte_end, line_start, line_end, record_ordinal}

native_row = {record_key: occurrence_id + "#native/" + zero_based_line_ordinal,
 occurrence_id, kind, raw: exact original line including newline, locator,
 name?, tag?, value?, version?, output_record_key?}
```

Byte intervals are zero-based, half-open; lines are one-based, inclusive.
Stockholm row ordinals are global within one output occurrence, so the second
alignment cannot reuse a previous alignment row's key. `alignment` records have
null sequence/name/description and list their child row keys. Every original
output line remains in `native_rows`, including comments, RF/MM/GC/GS/GR,
malformed data, stdout and stderr. Invalid UTF-8 uses reversible surrogate escapes
there. A UTF-8 replacement string is used only when the shared Stockholm parser
needs to retain readable prefix records; the original bytes remain recoverable.

For FASTA, `native={header: exact text after '>'}`. Fragments retain every
sequence line, including empty lines; wrapping whitespace is excluded from the
assembled sequence, while original bytes remain available. A header with no
following sequence line is incomplete. An explicit empty sequence line represents
a zero-length generated sample. FASTA gap/stop/missing markers are retained but
flagged invalid for hmmemit's native ungapped sequence output.

For Stockholm alignments, `native` has `column_count`, `block_count`, `terminated`,
`column_annotations`, `row_record_keys`, `parser_issues`. For alignment rows it
has `name_occurrence`, `identity_unambiguous`, `geometry_valid`,
`column_annotations`, `sequence_annotations`, `sequence_annotations_joined`,
`parser_issues`. Column annotation objects are `{text, valid, fragments}`;
fragments retain all shared parser events, including exact raw text, kind,
tag/value, name where present, block_index and their original line/byte locator.
Sequence annotation arrays retain GS events. Only one unambiguously joined DE
annotation becomes the convenience description. The shared parser's diagnostic
strings stay under `native.parser_issues`; authoritative keys are E1 record keys.
No hmmalign posterior/mapping score semantics are used.

```text
record_association = {kind: "record", record_key,
 state: "resolved"|"unresolved"|"conflicting", model_record_key, sample_ordinal,
 candidate_model_record_keys: [M1 key, ...], basis:
 "ordered_complete_population"|"native_name_suffix_and_order"|
 "alignment_row_population"|null}

model_population = {kind: "model_population", model_record_key,
 state: "complete"|"incomplete"|"conflicting", record_keys: [resolved row key, ...],
 expected_count: positive integer|null, captured_count: integer,
 output_available: boolean, output_complete: boolean}
```

Association uses actual ordered input model records and exact native
`<full-model-name>-sample<positive ordinal>` or `-consensus` suffixes. Names are
not split at arbitrary hyphens. Unique names plus exact sample ordinals can
retain trustworthy partial associations without shifting later rows. Repeated
source names can only bind through a complete ordered population matching every
expected slot, with complete output captures; aligned mode additionally requires
the expected per-model alignment groups. Thus expected repeated labels across
proven model occurrences are distinct, whereas duplicate sample slots within
one model conflict. Missing or malformed slots remove the complete-population
witness. Invalid identity and ambiguous interleaving never merge records.

`output_available` means a role-compatible occurrence with verified bytes was
supplied. `output_complete` additionally requires complete capture declarations.
Population `complete` also requires known expected count and complete rows.
`captured_count` counts resolved retained rows, including incomplete rows as
record occurrences; it is not a claim of completed native generation.

Extraction issues have `{code, stage:"extraction", occurrence_id, record_key,
field, details}`. Closed codes are declared in `ISSUE_CODES`. M1 issues remain
inside the complete extraction. Calculation issues additionally retain the
sheet's extraction issues and add `{code, stage:"calculation", record_key,
field, details}`. Unsupported M1 HMMER2/binary decoding remains unavailable;
this port never silently converts or generates replacements.

The calculation envelope is exactly:

```text
{schema:"hmmer_emission_components_v1", operation, parameters,
 rows:[generated_record | model | alignment | consensus, ...], checks, issues}
parameters = {consensus_thresholds: {minl,minu}|null,
              probability_rounding_tolerance: finite number in [0,1]}
component = {value: number|null,
 state:"present"|"missing"|"incomplete"|"incompatible"|"nonfinite"|"failed",
 unit:string, inputs:[explicit operand/reference dictionaries]}
check = {code, state:"pass"|"fail"|"unknown"|"not_applicable", record_key, inputs}
```

Omitted calculation thresholds use only explicitly supplied `--minl` and `--minu`
operation settings; passing `consensus_thresholds=null` explicitly keeps them
unavailable. The documented, recorded absolute rounding tolerance defaults to
1e-5. Parameters are validated; no probability normalization occurs. Cell and
coordinate operands identify the model/output key, field, position, cell index
or alignment column as appropriate. Every calculated number, including positions
and denominators, uses the component wrapper. IDs and numeric parameter values
are references/configuration, not measured score components.

`rows` have these discriminants and fields:

| Kind | Fields beyond kind/identity/basis |
| --- | --- |
| generated_record | model_record_key, alphabet, sequence; length, case-sensitive symbol_counts, canonical_residue_count, ambiguous_residue_count, noncanonical_unambiguous_residue_count, ambiguous_fraction, gap_count, stop_count, missing_symbol_count, invalid_symbol_count; model_alignment |
| model | record_keys; input_model_length, selected_N, configured_expected_length, captured_sample_count, expected_output_count, count_difference, total_length, minimum_length, maximum_length, mean_length |
| alignment | model_record_key; alignment_width, rf_match_column_count, captured_row_count; match_columns and row_coordinates |
| consensus | actual_record_keys, expected_sequence, actual_sequence, positions; mismatch_count, certain_mismatch_count, ambiguous_position_count |

`model_alignment` for FASTA is `{state:"missing",reason:"no_native_trace_in_fasta"}`.
For aligned rows it supplies the alignment key. This is never fabricated domain
count, likelihood, coverage or observed biological correspondence.

Each alignment match-column entry contains components `alignment_column`,
`rf_match_ordinal`, `model_position`, `occupancy`, `sample_denominator`,
`occupancy_fraction`. Row coordinates are `{record_key, columns:[{symbol,
alignment_column, residue_position}, ...]}`. Model positions are available only
when RF match count equals the bound input M. RF match ordinals remain distinct
from model coordinates when that relation is incompatible.

Each consensus position has components `position`, `maximum_probability`,
`probabilities:[{symbol,probability}]`, `thresholds:{minl,minu}`; native strings
`maximum_symbols`, `mask`, `expected_symbol`, `possible_symbols`; and booleans
`masked`, `near_tie`, `near_threshold`, `ambiguous`. Full expected sequence is
unavailable when any required model position/probability/threshold is missing;
available position entries are retained without padding.

## Numerical meaning

| Quantity | Formula, population and unavailable behavior |
| --- | --- |
| Length | Count actual ASCII residue letters in one case-preserved generated sequence, excluding `-._*~`; protein/nucleotide meaning follows alphabet. Invalid symbols/alphabet or incomplete rows retain the captured count with explicit state. |
| Symbol counts | Exact case-sensitive occurrence counts in the supplied sequence, including non-residue symbols; no model-based inferred counts. |
| Ambiguity | BJZX for amino; RYMKSWBDHVN for DNA/RNA. Count/actual ungapped residue count. Amino O/U are separately retained noncanonical but unambiguous residues. Empty denominator gives missing fraction. |
| Captured sample count | Number of bound, retained generated row occurrences. Conflicting associations give unavailable count rather than an invented zero. Missing output differs from a complete empty artifact. |
| Expected output count | Selected N for samples; one per model for consensus. Unknown N stays unknown. |
| Count difference | Captured count minus expected count, preserving negative values; captured partial counts remain distinct from completion checks. |
| Total/min/max/mean | Sum/min/max of bound captured sequence lengths; mean denominator is captured row count, never configured L or selected N. A complete empty capture has total0, but missing min/max/mean. Any incomplete constituent makes the whole captured-length summary unavailable. |
| Input M and configured L | Native M1 model length and supplied `-L`, separately labeled; neither is observed sample length. |
| Alignment width | Full native alignment column count, requiring consistent complete geometry. |
| RF match count | RF symbols excluding `. - _ ~` and spaces; full raw RF retained. |
| Occupancy | Number of generated rows carrying a residue letter at each RF match column; fraction denominator is the actual captured row population. This is model sampling, not biological conservation. |
| Simple consensus | First maximum in the saved native alphabet order, with native mask `m` yielding uppercase X/N. |
| Thresholded consensus | If pmax<minl: lowercase x/n; otherwise if pmax>=minu: uppercase maximum; otherwise lowercase maximum. Mask always yields lowercase x/n. No assumption minl<=minu is inserted. |
| Nominal mismatches | Case-sensitive unequal nominal expected/actual positions plus absolute length difference; unavailable full expected sequence gives no whole-sequence mismatch number. Partial actual capture labels the captured comparison incomplete and cannot pass agreement. |
| Certain mismatches | Complete actual positions outside all rounding-compatible symbols plus exact full length difference. Unavailable for incomplete actual capture. |
| Rounding ambiguity | Each finite saved probability has interval [max(0,p-tol),min(1,p+tol)]; native structural-zero cells remain exact0. Potential winners/threshold branches supply possible symbols. Nominal first-maximum sequence is retained, but an ambiguous agreement check is unknown unless a certain mismatch proves failure. |

This preserves the nominal answer while refusing to prove exact native agreement
when saved decimal rounding permits another output. There is no generated-sample
likelihood, scientific-confidence score, annotation credit or synthetic turn.

## Verification and concrete examples

`examples003/examples/` contains full sheets and complete calculations for all
eight retained native output styles, including every model probability and every
generated sequence/annotation/column. It also has changed-threshold and
near-threshold recalculations, a numerical summary and a provenance manifest.
The manifest records full native argv, original receipt and executable hashes,
input/output hashes, native resource policy, exact operation settings source,
reused parser/source hashes, owned source/test hashes and immutable-goal hash.

| Retained mode/style | Independent expected lengths | Total | Mean |
| --- | --- | --- | --- |
| core | 12,12,12 | 36 | 12 |
| aligned core | 12,12,12; width12/RF12 | 36 | 12 |
| local profile, L20 | 15,72,39 | 126 | 42 |
| unilocal profile, L20 | 85,31,21 | 137 | 137/3 |
| glocal profile, L20 | 92,37,30 | 159 | 53 |
| uniglocal profile, L20 | 100,31,17 | 148 | 148/3 |

All 12 aligned match columns have occupancy3/3=1. Simple consensus is
`ACDEFGHIKLMN`; thresholded at minl0.8/minu0.9 is `ACDExGHIKLMN`, with ambiguous
residue count1 and denominator12. Native position5 maximum probability is
exp(-0.40547)=0.6666634054134197; the summary independently evaluates this with
60-digit Decimal arithmetic. Changed thresholds0.6/0.9 yield `ACDEfGHIKLMN` and
one mismatch to the retained output. At minl2/3, nominal mismatch remains0 but
rounding-compatible symbols include f/x, so agreement is unknown.

The final run passed 75 tests in 0.67 seconds. Its receipt is
`check005/receipt.json`; the final example receipt is
`examples003/receipt.json`. Tests use the existing `local_jobs.run_local_job` with
20 GiB RAM, 4 GiB scratch, wall_seconds=null, `.venv/bin/python` and
PYTHONDONTWRITEBYTECODE=1. Receipts retain actual cgroup memory/swap enforcement,
no wall deadline and monitored scratch. No native output was regenerated.

Tests cover every retained style; DNA/RNA model bodies with explicitly synthetic
emitted strings; repeated names, multiple models and alignments; missing/extra
and duplicate rows; wrong occurrence/digest/size; shared native paths with
separate role occurrences; complete empty versus missing output; malformed and
truncated FASTA/Stockholm; interleaving and complete GC/GS/GR retention; missing
settings/thresholds; masks, ties, threshold rounding and underflow; exact
sequence/coordinate/annotation reference validation; and saved JSON replay with
changed parameters while file/network/subprocess entry points are forbidden.

Earlier receipts remain historical facts. `examples001` failed during alignment
validation because the first implementation matched native annotation locators
by artifact_ref alone when stdout and generated_alignment shared one real path.
The correction uses occurrence identity and has a regression test. Later
example runs passed. No science was rerun to repair that validation.

## Remaining limits and handoff

Native executions belong to retained workload259. This workload verified pure
parsing/calculation/example replay only. Root still must connect the selected
tool through its actual resource child, retain output files, populate this exact
sheet, calculate components and project the parent's requested typed return.
No live child execution or complete episode communication was established here.

M1's unavailable HMMER2/binary decoders remain an explicit limit; this component
does not expand them. FASTA has no native alignment/trace, so domain count,
likelihood and model coverage remain unavailable. Omitted parameters remain
unknown; seed0 has no reproducibility guarantee. Malformed/ambiguous populations
retain their original data and specific issues instead of assigned zero scores.

The complete authoritative immutable goal and all16 principles were read
verbatim before coding, after native/source study, and before handoff. The exact
E1 contract was reread before handoff. These resets are implementation
discipline only, with no deployed gate, extra model call, action or credit.
