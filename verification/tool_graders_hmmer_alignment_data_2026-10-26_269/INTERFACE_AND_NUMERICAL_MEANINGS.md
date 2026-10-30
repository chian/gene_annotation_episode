# B1 pure build/mask handoff

The two public ports are
`populate_hmmer_alignment_preparation_sheet(*, operation, inputs, outputs, model_extraction=None)`
and `calculate_hmmer_alignment_preparation_components(sheet, *, parameters=None)`.
The additional public pure port `reconstruct_alimask_model_map(alignment, *, settings)`
accepts a B1 alignment record and actual native flags. It performs no execution.

`operation` has exactly program, mode, engine_version and settings. Supported
program/mode pairs are hmmbuild/build_alignment, hmmbuild/build_single_sequence_matrix,
and alimask/mask_alignment, mask_model, model_to_alignment, alignment_to_model.
The original selected flags/settings remain unchanged in the sheet and result.
Input/output maps contain role -> list of `{occurrence, content: bytes}`. Each
occurrence has exactly M1's eight fields. A declared role with an empty list
expresses a selected role without a captured artifact; it does not create an
artifact or a measurement. This matters for a missing redirected summary:
`outputs['summary']=[]` prevents fallback to stdout even if -o is represented
separately from operation settings in the producer. Integration must preserve
that selected-role fact or provide an explicitly agreed interface extension.

The sheet has exactly schema, operation, artifact_occurrences, input_records,
output_records, model_extraction, native_rows, associations and issues. Its
schema is hmmer_alignment_preparation_sheet_v1. Artifact occurrences retain
the exact supplied identities; names and content hashes never identify records.
Input records are complete/partial Stockholm alignments. Output records are
alignments plus references to complete M1 model records kept in model_extraction.
Stockholm/Pfam framing preserves exact original lines, GF/GS/GC/GR events,
interleaved fragments, sequence case, weights and occurrence-specific locators.
All line coordinates are one-based; byte intervals are zero-based half-open.
Sequence and model/alignment coordinates below are one-based inclusive.

`native_rows` has four closed shapes exported as data.ROW_FIELDS:

- population: occurrence, declared/observed format, decoded_count, complete and
  decoded/partial/unsupported/invalid state. Unsupported count is null.
- build_summary: idx/name/nseq/alen/mlen/optional nucleotide W/eff_nseq/re_per_position/
  description, native tokens, raw line, valid flag and locator. Original native
  numbers remain separate from calculated numbers. Invalid tokens remain tokens.
- requested_interval: selected flag, original interval text, ordered request
  occurrence, endpoints, coordinate system and validity. Overlaps remain separate.
- mapping: ordered native row plus requested endpoints, actual returned source
  endpoints, target endpoints and native mapped/no_map/malformed state. For
  ali2model, returned source endpoints may differ from the requested interval.

Build associations join ordered input MSA, native summary index, ordered model
and optional resaved MSA. Native names, counts, alphabet, MAP and source custody
qualify the join. Missing summary rows do not shift model ordinals. Singlemx
with one source sequence uses the sequence name for model NAME, while the
summary retains the MSA name. Its native empty selected -O file does not become
a transformed MSA. Model extraction must exactly equal M1's deterministic
extraction of the supplied model bytes; matching a claimed digest alone is
insufficient. Native source checksum is an additional explicit calculator check.

Calculated envelope is schema hmmer_alignment_preparation_components_v1,
operation, parameters, rows, checks and issues. Rows use calculations.ROW_FIELDS;
numerical components are under components and use exported COMPONENT_FIELDS.
Each component is `{value, state, unit, inputs}`. Allowed states are present,
missing, incomplete, incompatible, nonfinite and failed. Checks use pass, fail,
unknown or not_applicable. Native/model checking failures never create confidence
values or controller observations. JSON roundtrip does not reacquire operands.

Defaults are background=null, probability_tolerance=0.0001 and
summary_rounding_tolerance={eff_nseq:0.005001,re_per_position:0.0006}.
The latter are explicit absolute comparison tolerances for the two-decimal
summary effective count versus six-decimal HMM EFFN and three-decimal summary
KL versus probabilities decoded from five-decimal log tokens. They do not round,
smooth or modify any measurement. Caller parameters are copied into the result.

## Numerical meaning

| Component/data | Inputs and exact meaning | Units, population and missing behavior |
| --- | --- | --- |
| input/resaved_sequence_count | Number of complete decoded sequence rows, including duplicate label occurrences | Sequence count, all rows of the particular MSA; malformed/incomplete geometry is unavailable |
| input/resaved_column_count | Validated common alignment row width | Columns in that exact coordinate system; no inference from model length |
| rf_consensus_count | Number of RF symbols other than native gap symbols `-._` | RF consensus columns; absent/invalid RF is missing |
| model_length | M1 LENG, separately from number of decoded position rows | Match-state count; truncated body remains separately incomplete |
| model_alignment_fraction | model_length / input_column_count | Match states per source column; explicit source denominator, incompatible association unavailable |
| effective_sequence_count | Native HMM EFFN via M1 | Effective weighted sequences, not confidence or independent observations |
| effective_input_sequence_ratio | Native EFFN / actual source sequence count | Effective sequences per source sequence; zero denominator nonfinite |
| native_relative_entropy | Native hmmbuild re/pos token | Bits per match position, native reported statistic, distinct from recalculation |
| mean_match_entropy / relative_entropy | M1 complete per-position arrays; entropy `-sum(p log2 p)`, KL `sum(p log2(p/q))`, means over declared M positions | Bits per match position; q is explicit, absent q missing, q=0 with positive p nonfinite; probabilities are not renormalized |
| model_components | Entire M1 row, every match/insert/transition probability mass/residual and per-position entropy/KL | Includes separate M/I/D outgoing transition groups, explicit probability tolerance; no compressed substitute for arrays |
| source_symbol_counts | Literal source symbols and counts at each column, all source row keys and nseq denominator | Unweighted observed input symbol counts; not matrix-derived model frequencies or weighted emission estimates |
| coordinates | Native model MAP to source, RF to resaved, each source/resaved residue ordinal pair and per-source-column set of resaved columns | One-based inclusive. A source column may have multiple resaved targets; all-gap columns have no residue-based target. No assertion of byte/column identity |
| requested_interval_count | Length of retained request occurrence list | Intervals, preserving duplicates and overlaps |
| requested_union_count | Cardinality of union of mapped inclusive alignment spans | Distinct alignment columns; model ranges include insertion columns between endpoint mappings; unavailable map is missing |
| input_masked_count | Count of actual source MM `m` symbols; absent MM means empty mask | Source alignment columns; malformed MM is incompatible |
| actual_masked_count | Count of actual output MM `m` symbols | Output alignment columns; missing output/MM is missing, never zero |
| newly/removed/retained_masked_count | `output_mask - input_mask`, `input_mask - output_mask`, `intersection` sizes | Columns in matched equal-width MSA coordinates; incompatible geometry unavailable |
| masked_fraction | actual_masked_count / actual input_column_count | Masked columns per alignment column, never divided by sum of range lengths |
| inclusive_span | mapped_end - mapped_start + 1 for each interval | Alignment columns, inclusive endpoints; independent of the interval union |
| returned_source_span / returned_target_span | Actual returned native endpoint difference +1, per requested mapping occurrence | Alignment columns or model positions according to direction; retained independently of reconstruction. Native no-map has no target interval, so target span is missing. Requested1-6 returning2-5 -> model1-2 has requested span6, returned source span4 and target span2 |
| input_alignment_count | Decoded input MSA occurrence count plus population completeness | Complete population versus known partial prefix remain separate |
| processed/unprocessed_alignment_count | One first MSA only when a valid output MSA or native mapping supplies processing evidence; remaining decoded MSA count | Native alimask does not transform later records. Without output evidence these quantities are unavailable, not assumed completed |
| mapped_model_position_count | Length of independently reconstructed map | Native model positions; missing algorithm/input is null, known empty map is zero |
| native_mapping_row_count | Number of decoded native mapping rows in captured stdout | Missing stdout is missing. A malformed/incomplete captured population retains its decoded count with incomplete state |

No uncertainty estimate is fabricated. Native rounded measurements, model
probabilities and deterministic reconstruction remain labelled as such. Native
simulation/calibration uncertainty not supplied by M1 remains unavailable.

## Alimask reconstruction boundary

Hand maps use actual RF nongap columns and do not depend on weighting. Fast maps
require an explicit amino/DNA/RNA alphabet. Supported weighting: --wnone,
--wgiven (actual WT values, or Easel's actual all-ones default if no WT exists),
and --wpb with at most 50,000 sequences. These calculations retain row weights,
marked strings, every column's weighted residue numerator, residue+gap denominator,
float32 occupancy, effective threshold and the PB consensus-column list.

PB uses Easel's fixed .5 span-based fragment rule and strict gap_fraction < .5
consensus rule, ignoring RF in fast mode. Canonical residue counts supply PB
weights; degeneracies are not canonical counts. Weights are length-normalized
and then scaled to nseq by native double arithmetic. Alimask then independently
marks sequences with residue_count <= selected_fragthresh * alignment_width,
converting terminal nonresidue/gap symbols to missing symbols. Final occupancy
uses C float32 accumulation and comparison. These details were read from native
alimask.c, esl_msaweight.c, esl_msa.c, esl_vectorops.c and esl_alphabet.c.

GSC/BLOSUM and PB subsampling remain explicit unavailable reconstruction
branches. Non-Stockholm/Pfam grammars remain unavailable readers; no conversion
or inferred population is substituted. Native ali2model ranges entirely after
the last mapped position remain unsafe-native diagnostics, not invented no-map
results. Range-array capacity100 and bounds are pure diagnostics; the producer
owns safety preflight. Full production execution/result/typed-return integration
is owned by root/D1 and is not established by these pure checks.
