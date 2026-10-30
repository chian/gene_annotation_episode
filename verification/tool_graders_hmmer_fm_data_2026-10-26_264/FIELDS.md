# Workload264 F1 public subshapes and numerical meanings

The unchanged top-level ports and schemas are in
`verification/tool_graders_hmmer_preparation_2026-10-26_261/FM_DATA_CONTRACT_001.md`.
This document defines the concrete nested fields delivered to root's later
preparation result consumer. It is not a replacement for the immutable goal,
not an execution binding, and not an annotation-credit calculator.

## Supplied records and roles

Every payload is `{occurrence,content:bytes}`. The eight occurrence keys are
exactly `occurrence_id,direction,role,ordinal,artifact_ref,sha256,size_bytes,
completeness`. Occurrence identity is caller-supplied; identical bytes remain
separate occurrences. `ordinal` is the zero-based ordinal within that role's
list. Size/digest, role/direction and ordinal are checked. Completeness is
`complete|partial|unknown`. Bytes are never acquired or retained elsewhere by
these functions. The caller owns the original full artifact.

Build: inputs `sequences`; outputs `fm_database,stdout,stderr`.
Exactmatch: inputs `queries,fm_database,source_sequences`; outputs
`hits,stdout,stderr`. There must be exactly one database. An ambiguous multiple
database selection is reported; no first database is chosen. Non-FASTA
`--informat` is explicitly unsupported by this source reader.

The supplied operation has exactly `program,mode,engine_version,settings`.
Settings retain native spellings and caller-resolved values. Direction-sensitive
exhaustive comparison requires a Boolean `--fwd_only`. Paired-database presence
and that setting jointly determine available directions. An amino writer index
is decoded but `fm_readFMmeta` compatibility fails. No source input is silently
added to the native exactmatch argument list.

The supplied producer ABI has exactly `format,engine_version,byte_order,
uint8_bytes,uint16_bytes,uint32_bytes,uint64_bytes,int32_bytes`, with F1's
fixed values and explicit little or big byte order. There is no magic sniffing
or host-byte-order inference. No valid supplied ABI means unknown decoded counts.

`source_binding` has exactly `database_occurrence_id,source_occurrence_ids,
source_sha256s,producer_attempt_id`. Ordered occurrence IDs and hashes must match
the actual supplied source artifacts and database occurrence. An absent binding
remains unknown custody even when sequence comparison succeeds. A matched
binding validates the supplied declaration, not an independent investigation of
the producer attempt's history.

## Extracted database

`schema` is `hmmer_fm_extraction_v1`. The other top-level fields are exactly
`occurrence,producer_contract,metadata,segments,ambiguity_ranges,blocks,
population,issues`.

All locators have `byte_start,byte_end,line_start,line_end,record_ordinal`:
byte offsets are zero-based half-open, lines are one-based inclusive or null
for binary, and ordinals are zero-based. No locator is a host path lookup.

`metadata` is null before a complete declared header is available. Otherwise:

| Field | Native meaning |
| --- | --- |
| `fwd_only` | native uint8 availability flag |
| `alph_type,alph_size,charBits` | native alphabet category, symbol count and storage bits |
| `freq_SA,freq_cnt_sb,freq_cnt_b` | native uint32 sample/counter frequencies |
| `block_count` | native uint16 logical block count |
| `seq_count` | native uint32 stored segment count, not distinct source sequences |
| `ambiguity_range_count` | native uint32 serialized range count |
| `total_char_count` | native uint64 source symbols excluding block overlap |
| `alphabet_symbols` | fixed source-defined order `ACGT` or `ACDEFGHIKLMNPQRSTVWYBJZOUX` |
| `storage_encoding` | `dna_2bit|amino_uint8` |
| `dna_reader_compatibility` | `compatible|incompatible` for native DNA-only reader and source-derived header restrictions |
| `actual_bytes,header_locator` | actual supplied binary length and header location |

There are eleven serialized header fields (34 bytes), not twelve. All widths
are explicit in the code's native struct formats; no C padding is used.

Each `segments` element has `record_key,locator,target_id,target_start,fm_start,
length,name_length,acc_length,source_length,desc_length,name,acc,source,desc`.
`target_id` is the native zero-based original source ordinal. `target_start` is
one-based; `fm_start` is a zero-based block text offset. Strings are decoded
losslessly with Latin-1 and separately validated for native NUL framing. Names
and descriptions never form keys. Keys are `occurrence_id#segment/<ordinal>`.

Each `ambiguity_ranges` element has `record_key,locator,lower,upper`. Bounds are
native signed int32 zero-based inclusive block positions. A block owns its
range slice through `ambig_offset,ambig_cnt`; ranges are not global source
coordinates until the calculator maps them through segments.

`blocks` is the complete flat serialized section order. Each element has:

- `record_key,locator,block_ordinal,section`: `section` is `forward|reverse`;
  key is `occurrence_id#block/<ordinal>/<section>`.
- `header`: exactly `N,term_loc,seq_offset,ambig_offset,overlap,seq_cnt,ambig_cnt`.
  `N` includes one sentinel. `term_loc` identifies the BWT sentinel.
- `arrays`: forward has `T,BWT,SA,counters_b,counters_sb`; reverse has only
  `BWT,counters_b,counters_sb`. Missing T/SA in reverse means not serialized.
- Each array has `values,expected_count,element_bytes,row_width,complete,
  locator`. Packed byte and SA values are full ordered scalar lists; counters
  are full ordered rows in native alphabet order. Partial arrays retain every
  complete decoded element/row, with the expected count retained. No zero padding.
- `decoded`: `text,bwt,text_sentinel_index,bwt_sentinel_index,symbol_kind`.
  Text includes the final encoded `A` placeholder; exclude it from source
  comparisons. BWT likewise contains the alphabet-zero placeholder at `term_loc`.
  `symbol_kind` is `generated_index`; substituted ambiguous residues never become
  original source observations. Reverse sections have null `text`.
- `complete`: all arrays in that section were framed and decoded.

For DNA, byte count is ceil(N/4), high two bits first. Amino writer storage uses
one byte per symbol despite `charBits=5`. SA has `1+floor(N/freq_SA)` entries.
Counter arrays have `1+ceil(N/frequency)` rows. Input length bounds every actual
allocation and read loop; hostile native counts cannot allocate declared-sized
arrays from short data. Complete prefix segments, ranges, sections and partial
trailing arrays survive truncation.

`population` has `state,complete,decoded_segment_count,
decoded_ambiguity_range_count,decoded_block_section_count,body_complete`.
States are `decoded|partial|unsupported|invalid`. Unsupported/no header counts
are null. Counts from an incomplete tail count the retained decoded prefix only.
`complete` also requires declared artifact completeness, digest/size integrity,
and the concrete internal structural invariants below. `body_complete` records
complete framing even when structurally invalid data remain retained. Neither
field establishes native matching correctness or global native process safety.

### Native imported-index structural checks

Root and producer267 requested these concrete reader preconditions as an
additive consumer requirement. They run inside the existing pure extraction
port; no calculator, execution operation or new public port is called.
`NATIVE_STRUCTURE_ISSUE_CODES` is a closed exported subset of `ISSUE_CODES`:

| Issue code | Checked source-derived invariant |
| --- | --- |
| `native_index_bounds` | nonempty stored block has N>=2, N<=INT32_MAX and at least one segment; native FM intervals and LF positions use signed int |
| `native_segment_bounds` | segments partition each block's nonsentinel text from offset0, with positive lengths, positive source starts, no uint64 source-coordinate overflow, endpoints within native total source symbols, and target IDs representable by the native signed sort key |
| `native_ambiguity_bounds` | each owned range exists, is ordered/disjoint, and lies inside nonsentinel block text |
| `native_metadata_partition` | each forward block's metadata slices continue the prior slices and collectively refer once to all segment and ambiguity rows |
| `native_block_pair` | paired N, sequence/range offsets and counts agree; reverse-section overlap is zero |
| `native_counter_invalid` | every b/sb row equals the actual BWT prefix counts with native reset/wrap behavior; arbitrary in-range counters are rejected too |
| `native_bwt_invalid` | sentinel encoding, complete single LF cycle and each preceding symbol agree with the supplied original T in the correct section direction |
| `native_sa_invalid` | every active sampled LF suffix position equals the actual serialized sample and lies within the nonsentinel suffix population; first and unused trailing sample slots are zero |

Framed data with these issues retain complete arrays and `body_complete=true`,
but `population.state='invalid'` and `population.complete=false`. Native source
reads were extended to the complete relevant `fm_sse.c` functions and FM structs
in `hmmer.h`; their hashes join the retained provenance manifest.

`native_reader_header_incompatible` is separate from writer structural failure:
`fm_readFMmeta` rejects freq_SA>10000, and the SSE DNA counter path uses aligned
128-bit loads whose block boundaries require 64-symbol spacing. A writer can
emit bin_length32 or large SA spacing, but these carry this explicit reader
issue and `dna_reader_compatibility='incompatible'`. Writer decoding remains
available, just as amino decoding remains distinct from DNA reader use. No
native run with those incompatible headers is claimed here.

Producer267's consumer requires compatible reader metadata, complete population,
complete body and no extraction issues. These are specific input preconditions,
not a scientific acceptance score. They cannot correct native reverse-boundary
or post-free diagnostic bugs; source/query validation still has separate work.

## Populated sheet

Schema `hmmer_fm_sheet_v1`; exact top-level fields are in F1. `database` is the
extraction above or null for missing/multiple database payloads. Occurrences are
retained in role-map/list input order under `artifact_occurrences`.

`input_records` elements have exactly `kind,record_key,occurrence_id,locator,
source_ordinal,payload`.

- FASTA: kind `fasta`; payload `header,raw_header,name,description,sequence,
  sequence_lines,complete,valid`. Raw header and sequence lines preserve case,
  line endings and whitespace. `sequence` concatenates nonwhitespace symbols,
  preserving case. `source_ordinal` spans source FASTA records in original
  supplied artifact/record order. Key is `occurrence_id#fasta/<ordinal>`.
- Query: kind `query`; payload `text,raw_line,line_ending,valid,complete`.
  Only LF separates queries; CR stays present and invalid. Empty/long/invalid
  lines remain occurrences. Maximum accepted length is 254 symbols; canonical
  DNA and U are syntax-valid, but U requires explicit `rna_to_dna` comparison.
  Source ordinal is null; key is `occurrence_id#query/<ordinal>`.

`native_rows` has exactly `kind,record_key,locator,payload`; keys are
`occurrence_id#<kind>/<per-kind-ordinal>`. The exported `ROW_FIELDS` is closed:

| Kind | Exact payload fields |
| --- | --- |
| `index_parameters` | `parameter,token,value,state` |
| `exactmatch_hit` | `group_key,query_text,anchor,anchor_token,direction,target_name` |
| `exactmatch_counts` | `Q,H,R,Q_token,H_token,R_token,population` |
| `diagnostic` | `text,category,numerical_state` |

Parameter names are native `bin_length`, `suffix array sample rate`, `alphabet`,
`input is asserted to be`; numerical parameter states are `present|failed`.
Hit directions are exactly native `f|r`. Counts retain separate native lines:
the hit summary row has Q/H and null R; miss has R and null Q/H. Population is
`raw_fm_intervals|native_emitted_locations`; native R always counts queries with
no raw interval. Diagnostic categories are `native_text|runtime|
unsafe_post_free_statistic|malformed_hit`, with numerical state
`not_interpreted|incompatible|failed`. Runtime text is retained without timing
or throughput inference. Native `occ calls` and `occ/sec` remain unsafe post-free
diagnostics; neither supplies productive throughput.

`associations` has:

- `source_binding_state`: `unknown|matched|mismatch`.
- `segments`: `{segment_record_key,target_id,source_record_key,basis,
  custody_state}`. Basis is `supplied_source_order`; absent source key is null.
- `query_groups`: `{record_key,occurrence_id,query_text,query_record_keys,state,
  hit_record_keys,locator}`. State is `unique|ambiguous|unresolved`. Candidates
  are all viable ordered subsequence mappings of native groups onto original
  query occurrences. Duplicate query strings remain distinct. Omitted queries
  do not silently shift or collapse later identities.
- `hit_targets`: `{hit_record_key,state,candidates}`. Each candidate is
  `{target_id,source_record_key,segment_record_keys}`. All native name-compatible
  index targets are retained; source ordinal maps to supplied original records.
  No arbitrary first duplicate name is selected. Without an index, source-name
  candidates alone do not establish index membership.

Issues everywhere have `code,record_key,field,stage,detail`. `ISSUE_CODES` in
`hmmer_fm_data.py` is the closed exported vocabulary. Stages are
`extract|populate|calculate`; detail retains the concrete conflicting fields or
available/required sizes. Issues are not turns, observations or credit.

## Calculated components

Schema `hmmer_fm_components_v1`; top-level `operation,parameters,rows,checks,
issues`. Parameters resolve explicit defaults `alphabet_normalization='none'`,
`coordinate_policy='native_one_based'`, `exhaustive_literal_check=False`.
Only `none|rna_to_dna` normalization is accepted. Native case folding applies
for comparison while original source strings remain unchanged. Unknown
parameter fields or values produce a structured failure and no calculations.

Every numerical result cell is `{value,state,unit,inputs}`. States:
`present|missing|incomplete|incompatible|nonfinite|failed`. A decoded partial count
can have a value with state incomplete; a whole-population unavailable count is
null. No uncertainty estimate is invented: these are exact integer diagnostics,
native rounded tokens, or deterministic ratios, not statistical confidence.
`inputs` names the original record keys, exact fields and denominator/formula.
No recalculation changes the saved sheet or native output.

Each row has `kind,record_key,components,details`:

| Kind | Numerical components / details |
| --- | --- |
| `database_summary` | populations below; source coverage intervals |
| `block_validation` | details: mismatching counter row indices, mismatching suffix sample indices, BWT symbol mismatch count, LF visited row count |
| `segment_validation` | `compared_symbols,mismatching_symbols`; source key and every mismatch coordinate |
| `location_validation` | `native_anchor,query_length,interval_start,interval_end`; state, direction, candidate source text and associations |
| `query_validation` | per-query emitted `valid_location_count,invalid_location_count,unresolved_location_count`; original query text |
| `exactmatch_summary` | raw and validated populations below; exhaustive tuple sets |

`database_summary.components` numerical meanings:

| Component | Definition / denominator |
| --- | --- |
| `source_occurrence_count` | number of supplied FASTA record occurrences |
| `source_artifact_count` | number of supplied source artifact occurrences |
| `stored_segment_count` | number of decoded segment rows; not source occurrence count |
| `distinct_target_count` | cardinality of decoded target IDs |
| `source_symbol_total` | sum of original FASTA sequence lengths |
| `declared_total_char_count` | native header total excluding duplicated block overlap |
| `actual_database_bytes` | actual supplied database length, validated against occurrence size |
| `indexed_symbols` | sum of N-1 across forward sections; includes block overlap |
| `indexed_unique_symbols` | sum of N-1-overlap across forward sections |
| `sentinel_count` | count of logical forward text blocks |
| `stored_bwt_sentinel_count` | count of serialized BWT sections |
| `ambiguity_range_count` | count of serialized range rows, including repeated block representations |
| `covered_source_symbols` | sum of source-coordinate interval union lengths |
| `ambiguity_union_symbols` | sum of per-source mapped ambiguity interval union lengths |
| `ambiguity_fraction` | ambiguity_union_symbols/source_symbol_total; empty denominator is missing |

`database_summary.details.source_coverage` retains each source key and complete
`covered_intervals,ambiguity_intervals` arrays with wrapped one-based inclusive
start/end coordinates. Union calculation avoids manufacturing new source symbols
from overlapping stored segments. Missing sources leave source values unavailable.
Unavailable ABI leaves decoded populations unavailable, never zero. Every check
has its scope; numerical storage totals are not annotation evidence.

`location_validation.details` contains `state,direction,query_record_keys,
candidates`. State is `valid|invalid|unresolved`. Candidate fields are
`source_record_key,segment_record_keys,state,source_interval_text,compared_text`.
Bounds, literal equality, ambiguity, index membership and source-label agreement
are checked separately per candidate. A valid row requires a unique query/source
association and complete compatible input populations. Native `r` compares the
reversed source string, never its reverse complement. Anchors are preserved even
when intervals are invalid. Repeated valid tuples remain literal matches but
their repetition is separately detected and counted.

`exactmatch_summary.components`:

| Component | Definition / population |
| --- | --- |
| `query_occurrence_count` | count of every supplied query line, including duplicates |
| `native_Q` | native queries with any raw interval in count-only; with retained locations in location mode |
| `native_H` | native raw FM interval sizes in count-only; emitted deduplicated tuples in location mode |
| `native_R` | native queries with zero raw intervals in both modes |
| `native_unclassified_queries` | N-Q-R; location filters can leave this positive; contradictory native inputs produce failed arithmetic cells |
| `emitted_location_count` | all parsed emitted native rows |
| `valid_location_count` | emitted rows with uniquely established valid literal intervals |
| `invalid_location_count` | emitted rows with uniquely established invalid intervals/symbols/membership |
| `unresolved_location_count` | emitted rows whose required association or supplied validation data remain unresolved |
| `duplicate_location_count` | resolved tuple occurrences after their first occurrence for the same query/source/direction/anchor |
| `valid_location_fraction,invalid_location_fraction,unresolved_location_fraction` | respective emitted counts/emitted_location_count; empty or incomplete denominator is unavailable |
| `expected_literal_location_count` | optional complete-source literal enumeration over every query occurrence and enabled direction |
| `missing_literal_location_count,extra_literal_location_count` | multiset subtraction of actual tuples and expected tuples, retaining duplicate multiplicity |

All count-only location measurements are missing, not zero. An explicitly
selected exhaustive comparison can return expected tuples for count-only, but
native locations remain unmeasured and no missing/extra count is invented.
Empty complete location output is a measured zero, distinct from a missing file.
Per-query native raw interval counts do not exist in count-only and are not inferred.

`details.exhaustive` is `{requested,state,expected_tuples,missing_tuples,
extra_tuples}` with state `not_requested|unavailable|expected_only|compared`.
Every tuple contains `query_record_key,source_record_key,direction,anchor` and
the anchor is a numerical cell. All query/source occurrences and all overlaps
are included. The optional check is an explicit pure literal comparison on saved
source strings; it is not a native rerun and does not replace native results.

Checks have exactly `name,record_key,state,scope,inputs`; states are
`pass|fail|unknown|not_applicable`. Build checks include layout, custody, DNA reader
compatibility, complete metadata partitioning, block offsets/coverage/overlap,
segment coordinates and names, source coverage, source symbols outside recorded
ambiguities, and ambiguity membership. Array checks independently cover:

- Cached decoded strings versus actual packed arrays; calculations use arrays.
- Every b/sb counter row, including alphabet-zero sentinel and native uint16 wrap.
- A complete LF cycle and every BWT preceding symbol against actual stored T.
- All suffix-array sample positions, the native sample-zero convention and the
  unused trailing zero slot when N is divisible by sample frequency.

Exactmatch checks add query count identities with the native mode distinction,
native H versus emitted rows, Q versus groups, per-candidate bound/symbol/
ambiguity/membership/name validation, duplicate tuples and optional exact multiset
agreement. Matching total expected/emitted counts alone never passes the latter.
These checks do not certify native search completeness on other jobs or formats.

## Explicit limits

The only native ABI implemented is supplied HMMER 3.4, uint widths 1/2/4/8,
int32 width4, little or big endian. Native examples are retained little endian;
big endian verification uses an explicitly synthetic byte-order conversion.
FASTA source input only. Queries use the restricted safe grammar above. Header
and malformed native text stay diagnostics; no arbitrary format fallback occurs.
Malformed/truncated records retain complete prefixes; partial byte fragments that
cannot form a scalar/counter row remain solely in the caller's original artifact.
No native process, filesystem, network, Store or LLM is called by either module.
No resource decisions, annotation confidence, observations, turns or credit exist.
Execution receipts, capture, selected child binding, publication and typed episode
returns remain root's separate production integration work.
