# Similar Genome Finder: numerical reader and calculator verification

This directory verifies the pure C2 reader/calculator boundary in
`docs/TOOL_GRADER_BVBRC_ANALYSIS_BATCH_2026-10-24_001.md`. It does not establish a
live BV-BRC service, authenticated access, selected-tool binding, receipt custody,
or complete episode communication. Those are separate C4 integration work.

## Implemented interfaces

* `parse_minhash_result(value, *, mode, request, provenance)` returns
  `{status, sheet, diagnostics}`. `value` is the synchronous native RPC
  `result[0]`, an ordered array of `[genome_id, distance, pvalue, counts]` rows.
* `calculate_minhash_components(sheet, *, pair_metadata=None)` returns
  `{schema, rows, diagnostics}` without modifying any supplied object. Its
  schema is `bvbrc_minhash_components_v1`.

Mode `genome` is bound to `Minhash.compute_genome_distance_for_genome2`; mode
`fasta` is bound to `Minhash.compute_genome_distance_for_fasta2`. Both requests
retain all eight arguments in order: genome ID or Workspace FASTA path,
`max_pvalue`, `max_distance`, `max_hits`, `include_reference`,
`include_representative`, `bacterial`, `viral`. Request extras are also retained.
No default argument is inserted. A FASTA operand is a Workspace path, not
inline sequence, a URL, or a client-local input. Pure validation checks the
absolute `/owner/workspace/object` syntax; the same string could name a local
file, so syntax cannot prove Workspace existence or permission. The operation's
declared semantics and C4's selected request establish its namespace. No local
file is opened or resolved by this module.

The sheet schema is `bvbrc_minhash_sheet_v1`. It contains mode, exact request,
structured provenance, complete native result, rows, and `search_metadata`.
Search population size, reference release, truncation, k, seed, and sketch size
are null because the native response does not report them. Supplied provenance
is copied, never interpreted as measurements. Pair metadata affects only the
new calculation; it does not rewrite those native unknowns.

Each row contains `row_index`, `genome_id`, `native_row`, `reported_distance`,
`reported_pvalue`, `counts_token`, `shared_hashes`, `compared_union_hashes`, and
diagnostics. Row index is zero-based response order. It is not biological rank
or a confidence component. The genome identifier is never inferred from taxa
or assigned to a native Mash filename. Original numeric types/strings, zero,
null, extra fields, duplicate rows and count-token spelling remain retained.

`ok` means the native format and cells parsed, not biological completeness.
`partial` preserves associated usable cells alongside missing/invalid cells.
`invalid` marks a bad outer contract or no usable associated numerical cells.
Every received row still occupies its original sheet position. An empty list
is a valid format with `empty_result_completeness_unknown`, not a verified
negative search. Diagnostics include a code, indexed path, and `error` or
`warning` severity. Missing and explicit null have different codes. Rejected
numeric cells are null; their original content remains in the native row.
Syntactically valid counts greater than their denominator are retained as
observed integers, qualified as invalid, and cannot generate calculations.

## Numerical meanings

All components concern the compared sequence/sketch pair. They have no residue
coordinates and no gene-function confidence interpretation. No uncertainty
interval, taxonomic concordance, HGT inference, source-quality score, database
prevalence correction, or annotation-credit formula is supplied.

| Cell | Inputs, meaning and formula | Units / population | Missing or boundary behavior |
| --- | --- | --- | --- |
| `reported_distance` | Native row position 1; Mash mutation-distance estimate | Dimensionless derived estimate for this pair | Missing/invalid stays null. A native numeric string is parsed without altering its saved lexeme. Valid range 0–1. |
| `reported_pvalue` | Native row position 2; native random-overlap tail | Dimensionless probability under Mash's null, not a database E-value or function probability | Same parsing rules. Reported zero is preserved with precision unknown; it may be printed rounding/underflow. |
| `shared_hashes` | Integer numerator of native `x/s` token | Count of sampled shared hashes | No inferred count. Malformed tokens retain their original value. |
| `compared_union_hashes` | Integer denominator of native `x/s` token | Count of sampled union hashes actually compared | Not nominal sketch size, sequence length, reads, coverage, or number of genomes. Zero remains zero. |
| `shared_hash_fraction` | `x/s` | Dimensionless sampled Jaccard estimate, denominator `s` | Requires valid counts and `s > 0`; never assumes 1000. |
| `recomputed_distance` | `0` when `x=s`; `1` when `x=0`; otherwise `min(1, -ln(2*j/(1+j))/k)` | Dimensionless Mash distance with explicit actual k | Requires positive integer k and `s > 0`, including boundary cases. No default k=21. |
| `unsaturated_distance` | Before the `min(1, ...)` cap, evaluated as `log1p((s-x)/(2*x))/k` for positive partial overlap | Dimensionless; algebraically the same native formula | Zero at full overlap; null for the native no-overlap special case. Saturation is separately diagnosed. |
| `kmer_space` | `alphabet_size ** k` | Number of strings under the declared alphabet/k model | Actual explicit inputs only. If the float overflows, null with retained finite `log_kmer_space`. |
| `query_random_kmer_probability`, `reference_random_kmer_probability` | `r_i = length_i / (length_i + alphabet_size**k)` | Model probability of a particular k-mer under the native random model | Requires actual positive integer lengths, alphabet cardinality and k. Lengths are native sequence/sketch length quantities, not inferred alignment coverage. |
| `random_jaccard` | `r1*r2/(r1+r2-r1*r2)` | Dimensionless native null-overlap probability | Computed equivalently as `1/(1 + A/query_length + A/reference_length)` using log-space arithmetic, avoiding premature product underflow. |
| `recomputed_pvalue` | `P[Binomial(s, random_jaccard) >= x]` | Dimensionless upper tail with `s` trials | Uses `scipy.stats.binom.sf(x-1, s, random_jaccard)`, not `1-cdf`. Requires all explicit metadata and `s > 0`; `x=0` gives 1. |

Pair metadata is a list of records with BOTH `row_index` and `genome_id`, the
four positive integer inputs (`kmer_length`, `query_length`, `reference_length`,
`alphabet_size`), and structured `provenance`. Matching never uses list position
or genome ID alone. Wrong IDs/indices are diagnosed. Multiple matching records
are ambiguous even when identical; none is chosen. Duplicate native genome
rows are still distinct pairs. Missing lengths/alphabet leave distance usable
when k is available, but the p-value unavailable. Metadata and its provenance
are retained in `calculation_inputs`; ambiguous candidates are retained there
as well. Calculated reported values stay equal to their numerical sheet cells;
their original raw types remain in the corresponding native row.

SciPy is an existing declared project dependency (`scipy>=1.14,<2`); this work
adds no dependency or custom statistical distribution implementation. The
verification environment uses the version recorded in `OFFLINE_VERIFICATION.json`.
Positive tails too small for floating point remain zero with an explicit
underflow diagnostic; this is not exact probability zero. Likewise, values
rounded to one are qualified. Log null inputs remain inspectable. Counts above
`2**53` remain exact integer cells, but the double-precision binomial call is
unavailable with a specific diagnostic; they are not silently rounded for that
calculation. No interval or calibration is invented.

## Source observations and contract boundary

Both complete native method implementations, their generated client methods
and service dispatch, the complete `minhash-search.pl`, and the complete Mash
distance implementation were inspected from retained official sources:

* BV-BRC `p3_minhash` revision `2220db387ee6b068993e1765138ac76b853ccde4`:
  `Minhash.spec`, `lib/Bio/P3/Minhash/MinhashImpl.pm`, `Client.pm`, `Service.pm`,
  and `scripts/minhash-search.pl`.
* Mash revision `5df1f984a06d568b4c47540042a0e619fd1f7bdd`:
  `src/mash/CommandDistance.cpp`, `doc/sphinx/distances.rst`,
  `doc/man/mash-dist.1`, and `test/ref/genomes.dist`.

They remain under
`verification/tool_graders_bvbrc_native_rpc_contract_2026-10-24/sources/`.
Source hashes/URLs and both complete mode rows are retained in that directory's
`CONTRACT_CANDIDATES.json`; this verification does not change that record.

The source can emit `max_hits+1` rows and then genome mode can drop IDs absent
from its Data API check. The search script can omit unmappable IDs and does not
deduplicate across reference collections. Exit-status handling does not prove
that empty output is a completed negative search. No result is trimmed here,
and no truncation/population completeness flag is inferred.

The native Mash source first checks `common == denom`, so `0/0` can produce
reported distance 0, and its `x == 0` p-value branch produces 1. This was
reported to the integration owner before implementation. The agreed contract
requires all derived quantities unavailable for zero denominator. The parser
therefore preserves native `0` and `1`; the calculator returns null derived
quantities with `zero_union_calculations_unavailable`. It does not alter native
values to make them match the derived availability policy.

## Reproducible examples and verification limits

Run from the repository root:

```sh
.venv/bin/python -m pytest -q tests/test_bvbrc_minhash_grader.py
.venv/bin/python verification/tool_graders_bvbrc_minhash_2026-10-24/verify_offline.py
```

The second command writes `FILLED_EXAMPLES.json` and
`OFFLINE_VERIFICATION.json` in this directory, using only retained local data
and deterministic calculations. Each example retains its request, synthetic
RPC envelope, parser result and complete numerical calculation. The generator
is not service transport or production fixture data.

* The upstream Mash fixture's first row is
  `genome1.fna reads 0.12101 4.48626e-214 41/1000`; `41/1000 = 0.041`.
  Its numbers are retained in a **synthetic BV-BRC wrapper**, with invented
  identifiers explicitly labeled. There is no claim that BV-BRC returned that
  row or that an actual user input was measured. Both input modes are covered.
  Its missing k/length/alphabet metadata remains missing.
* Synthetic `x=2,s=3,k=1,lengths=2/2,alphabet=2` gives `r1=r2=1/2`,
  `random_jaccard=1/3`, distance `ln(5/4)=0.2231435513`, and upper tail
  `3*(1/3)^2*(2/3)+(1/3)^3 = 7/27 = 0.2592592593`.
* Recalculating the saved sheet with explicit k=2 gives distance
  `ln(5/4)/2=0.1115717757`, `random_jaccard=1/5`, and tail
  `13/125 = 0.104`. Native reported values remain unchanged.
* Zero overlap, full overlap, zero denominator, duplicates, missing metadata,
  mixed valid/invalid rows, malformed/missing values, wrong metadata joins,
  count limits, underflow and numerical saturation are covered explicitly.

The tests disable socket connections and subprocess launches. They do not call
a model, service, or job and do not inspect credentials. This verifies parser
and calculator behavior with retained upstream-native values in synthetic
wrappers and explicit synthetic examples. No successful retained BV-BRC RPC
response, live deployment, provider receipt chain, or episode return was
verified by this C2 workload.
