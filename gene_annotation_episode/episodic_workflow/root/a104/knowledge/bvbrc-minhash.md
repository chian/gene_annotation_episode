# BV-BRC Similar Genome Finder operations

Use the caller-configured BV-BRC Minhash API resource through launch/API execution.
`api.bvbrc.minhash.genome` accepts the assigned native genome ID;
`api.bvbrc.minhash.fasta` accepts the assigned Workspace FASTA file path. FASTA
mode does not upload a local file or accept inline sequence. The assignment
supplies mode, query, max_pvalue, max_distance, max_hits, include_reference,
include_representative, bacterial and viral. Preserve all supplied values;
there are no inserted search defaults. The selected operation's arguments are
empty because the original assignment already fixes the request.

Both operations make one direct RPC and retain its entire response. A valid
response supplies a completed-request handoff, not an AppService job. A missing
response leaves the issued call's outcome unknown. No automatic resubmission,
polling, different endpoint or resource substitution occurs. The caller supplies
the actual endpoint and any authorization configuration; an available operation
description does not establish authentication or deployment.

`api.bvbrc.minhash.result` runs in the results episode using the original handoff
and the parent's fixed selector. Its action arguments are `{}`. Legacy selector
`{}` remains valid: it records the retained native response without supplied
pair metadata. The explicit selector also supports these choices:

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
evidence item naming that `field`, its `source_ref`, the source's retained
`artifact_ref`, and the RFC 6901 JSON pointer `record_path` to the same integer.
The source must be available through completed own work, a received child
return or the parent's selected inputs. A null field has no evidence item. The
selected artifact must belong to that source as its original native or bound
auxiliary artifact. A stored source alone is insufficient. Preserve every selected
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
| `bvbrc_minhash_calculations` | Saved calculated components, the four saved pair input fields, unestablished native-parameter equivalence and row diagnostic codes. |
| `bvbrc_minhash_calculation_diagnostics` | Saved calculator codes, indexed field paths and severity, including metadata records that match no native row. |

Only requested typed facts cross the child return. Source-only or counts-only
returns do not supply match or calculation facts. The complete response, sheet,
inputs and diagnostics remain retained. Usable partial measurements survive
missing or invalid neighbors; unavailable values are not zero. Empty results do
not establish a complete negative search. These measurements are dimensionless
except for the explicit integer counts and length operands, and none is a
calibrated probability of gene function.
