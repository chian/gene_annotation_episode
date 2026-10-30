# MinHash wording for user review — draft 001

This is a review draft, not an accepted template or an implementation. Root must
print the proposed wording in the conversation for the user's running feedback.
The original user-supplied goal remains authoritative. This packet changes no
production file, published library, test, progress row, or numerical contract.

## A. Result operation description

Replace only `BVBRCMinhashService.result_capabilities()[0].description` in
`gene_annotation_episode/api_bvbrc_minhash.py` with this exact text:

> Publish the retained BV-BRC MinHash response, or recalculate an explicitly selected saved sheet, using the same numerical sheet and deterministic calculator. The parent fixes the original handoff, result mode and any retained pair inputs in the results assignment; this action takes empty arguments. Preserve service-reported distance and p-value separately from calculated components. Supplied k-mer length, query/reference lengths and alphabet size require selected source, artifact and field evidence; their equivalence to remote service parameters remains unestablished. No search or metadata request is made. Return only the parent's requested matches, counts, calculations or diagnostics.

The operation name remains `api.bvbrc.minhash.result`, the resource remains `api`,
and its action `input_schema` remains the existing closed empty object. The two
launch operation descriptions already faithfully describe their one selected
RPC, eight native arguments and immediate response; leave them unchanged.

## B. MinHash manual result instructions

Keep the heading and the first two paragraphs of
`gene_annotation_episode/knowledge/bvbrc-minhash.md` unchanged. They already
explain the selected genome/Workspace-FASTA operands, resource, original native
arguments, immediate response, uncertain failure and lack of automatic retries.
Replace the current result section, beginning with
“`api.bvbrc.minhash.result` is available”, with the following exact text:

`api.bvbrc.minhash.result` runs in the results episode using the original handoff
and the parent's fixed selector. Its action arguments are empty. Legacy selector
`{}` remains valid: it publishes the retained native response without supplied
pair metadata. The versioned selector `bvbrc_minhash_result_selector_v2` also
supports these explicit choices:

| Selected mode | Required input | Work performed |
| --- | --- | --- |
| `native_result` | Original handoff; `saved_result_ref` is null | Parse the retained response and calculate components using the selected `pair_metadata`. |
| `saved_sheet` | Original handoff and a previously received MinHash `saved_result_ref` for that same request and response | Reuse that saved sheet and calculate components using the selected `pair_metadata`. |

Neither choice repeats the search or acquires metadata. A saved-sheet
recalculation is a new selected calculation of retained data, not a fresh native
acquisition. Replaying an already completed selected action returns its original
saved output. Earlier publications and returns retain their original values.

Each native row is `[genome_id, distance, pvalue, shared/union]`. Keep original
row order, duplicate genome rows, strings/numbers and malformed fields in the
retained output. The same numerical sheet keeps parsed quantities beside those
native values. Service-reported distance and p-value remain distinct from
recalculated distance and p-value.

Each selected pair-metadata record names both the zero-based `row_index` and
`genome_id`, and supplies all four fields `kmer_length`, `query_length`,
`reference_length` and `alphabet_size`. Each field is a positive integer or null
when unavailable. k-mer length counts sequence symbols per k-mer; query and
reference lengths are the explicitly supplied length operands; alphabet size is
the declared cardinality used by the calculation. It is not the number of
different letters observed in a sequence. An empty `pair_metadata` list supplies
no parameters. Numeric strings, booleans and assumed defaults are not inputs.

Use provenance kind `explicit_retained_pair_inputs` and the exact original
`query_mode` and `query_operand`. For each nonnull field, select exactly one
evidence item naming that `field`, its received `source_ref`, the source's
retained `artifact_ref`, and the RFC 6901 JSON pointer `record_path` to the same
integer. A null field has no evidence item. The selected artifact must belong to
that source as its original native or bound auxiliary artifact. A stored source
that this episode has not received is insufficient. Preserve every selected
metadata record; do not merge duplicate genome occurrences or silently choose
between two records for the same pair. The calculator joins by both row index
and genome ID and retains mismatch or ambiguity diagnostics.

The four-cell service response does not establish k-mer length, either length,
alphabet size or reference release. Current genome metadata, supplied sequence
lengths, upstream defaults or numerical agreement do not establish which
parameters the remote sketch used. Keep `native_parameter_equivalence` equal to
`unestablished` for supplied calculations.

The shared-hash fraction uses shared hashes divided by compared union hashes
for an identified row with valid counts and a positive denominator. It describes
the sampled hash union, not bases, genome coverage or the search population.
Recalculated distance requires those counts and k-mer length; recalculated
p-value also requires both lengths and alphabet size. `unsaturated_distance`
preserves the distance before the calculator's cap, where available. The
recalculated p-value is the existing binomial upper-tail calculation under the
explicit supplied model inputs. Missing inputs leave only the dependent
components null. A zero union leaves derived values null. Preserve saved
precision, saturation and numerical-range diagnostics. Native parse status and
calculation availability are separate.

Parents choose the needed typed return families:

| Requested family | Meaning |
| --- | --- |
| `bvbrc_minhash_matches` | Original row indices and genome IDs, service-reported distance/p-value, hash counts and saved shared-hash fraction. |
| `bvbrc_minhash_counts` | Actual returned array length and parse status; population size and truncation remain unknown. |
| `bvbrc_minhash_calculations` | Saved calculated components, their supplied pair inputs, unestablished native-parameter equivalence and row diagnostic codes. |
| `bvbrc_minhash_calculation_diagnostics` | Saved calculator codes, indexed field paths and severity, including metadata records that match no native row. |

Only requested typed facts cross the child return. Source-only or counts-only
returns do not supply match or calculation facts. The complete response, sheet,
inputs and diagnostics remain retained. Usable partial measurements survive
missing or invalid neighbors; unavailable values are not zero. Empty results do
not establish a complete negative search. These measurements are dimensionless
except for the explicit integer counts and length operands, and none is a
calibrated probability of gene function.

## C. Discovery summary

Keep the MinHash entry identity, title, section identity, paths and tool names in
`gene_annotation_episode/knowledge/index.json`. Replace only its summary with:

> Direct genome or Workspace FASTA MinHash request; retained native measurements, sampled hash fractions, and explicit pair-metadata calculations from the native response or a selected saved sheet.

This summary permits discovery by “metadata”, “calculations” and “saved sheet”.
It does not claim live availability or deployed parameter equivalence.

## D. Generic results TASK: minimal correction for saved calculations

This is a separate concrete wording review from A–C. The current generic
`ExecutionEpisodes.instructions()` results branch calls every result operation
“acquisition”. That is misleading for the already implemented explicit
saved-sheet choice. Proposed exact replacement paragraph:

> Produce the parent's requested execution results through the original handoff and fixed result selection. Choose bounded status or requested file/page reads, or explicitly assigned calculations from retained data, using actual preceding outcomes and available operations. Preserve partial bytes and native scores. Native paths expose the current resource filesystem: the exact attempt observation does not establish that current file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets the returned records. Original work, resource and selector stay fixed. Completion means the original requested result work has been faithfully produced; recalculation of retained data is not a fresh native acquisition.

This text describes the result work. It changes no runtime endpoint proof,
credit, continuation or scientific-completion rule. The generic launch and API
TASK paragraphs in `ExecutionEpisodes.instructions()` need no wording edit for
this MinHash change. Retain their full instructions on every iteration.

## E. Concrete result-selection TASK sections for the common renderer

These are proposed deterministic text sections under the generic results TASK,
not new episode types or a per-tool episode implementation. They expand only
the already selected assignment. The generic TASK, full scoped assignment,
selected operation instructions, constraints and typed return meanings remain
present on every call, including lookup continuations and reconstruction.

For legacy `{}`:

> Selected result work: publish the original retained MinHash response. No pair inputs were supplied. Preserve service-reported values and return the requested recorded facts; distance and p-value recalculations remain unavailable without their required inputs.

For V2 `native_result`:

> Selected result work: calculate the requested MinHash components from the original retained response using the supplied pair inputs below. Keep every original native row and service-reported value. Use the assigned row index and genome ID together. The supplied inputs do not establish the remote service's parameters.

For V2 `saved_sheet`:

> Selected result work: recalculate the requested MinHash components from the explicitly selected received sheet using the supplied pair inputs below. The sheet belongs to the same original request and response as this handoff. Preserve the earlier sheet, calculated values and service-reported measurements. This action acquires no new native result, and supplied inputs do not establish the remote service's parameters.

The following table headings are exact proposed text; values come only from the
fixed selector. Show a literal `null` for absent operands. Do not calculate or
fetch values to fill this table.

| Native row index | Genome ID | k-mer length (symbols) | Query length (supplied) | Reference length (supplied) | Alphabet size | Native parameter equivalence |
| --- | --- | --- | --- | --- | --- | --- |

Selected field evidence is a separate table with headings:

| Native row index | Genome ID | Field | Selected retained input | JSON field pointer |
| --- | --- | --- | --- | --- |

The source/artifact associations stay in the typed assignment and host custody
records. A readable selected-input label may be displayed only if already
supplied; do not invent a provenance label or acquire content to decorate it.
Exact semantic operands needed for a permitted action remain available through
the existing typed contracts. Host hashes, record identities, revisions and
receipt envelopes are not the returned-value display.

## F. Illustrative returned-value display

This example uses the accepted contract's explicitly synthetic row and expected
values; it is not a live result or a new numerical verification. It illustrates
the display when the parent requested matches and calculations. Actual display
copies only admitted requested fields from the saved shared components.

**MinHash result — native row 0, genome 123.4**

| Quantity | Service-reported | Calculated from supplied inputs |
| --- | --- | --- |
| Distance | 0.223144 | 0.22314355131420976 |
| P-value | 0.259259 | 0.2592592592592592 |
| Shared/union hashes | 2/3 | Fraction: 0.6666666666666666 |

Supplied inputs: k-mer length 1 symbol; query length 2; reference length 2;
alphabet size 2. Native parameter equivalence: unestablished. Native parse
status: ok. Row diagnostic codes: none. Unsaturated distance equals the saved
calculated distance in this example.

For a k-only input, the p-value cell is `null` and the requested diagnostics name
the missing query length, reference length and alphabet size. Do not turn that
into a native parse failure. If the parent requested only counts, display only
the returned count, parse status and unknown population/truncation. If it
requested only a source reference, display no numerical table.

No internal source hashes, artifact digests, run IDs, episode IDs, revisions,
private histories, automatic source expansion or extra model report belongs in
this returned-value display.
