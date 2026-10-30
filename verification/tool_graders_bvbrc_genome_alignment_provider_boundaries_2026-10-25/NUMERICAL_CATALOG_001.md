# Numerical meanings and closed native-cell selectors

This catalog enumerates existing populated A/B/XMFA fields, not new scientific formulas. Every field remains the original `NumericCell` with its value/state/unit/origin/numerator/denominator/population/method/evidence/uncertainty/requirements. Provider calculations keep the complete native components; outward selectors copy only explicitly selected cells. No calibration/probability-of-function field is proposed.

## Exact numeric locator union

Each locator is a closed record with `family`, the indicated required location keys, and `field` restricted to that row's finite names. The request's kind must match. `member` is the unchanged `NativeMember`; `pair` is `{member_a:NativeMember,member_b:NativeMember}`. `original_member` is the full unchanged `Occurrence`, not an accession string. All indexes are UInt except XMFA member numbers, which are Positive. The only nonnumeric symbol is exactly one character admitted by the native DNA row alphabet, including gap and supported case; a nonexistent symbol-count row is unavailable, not a newly calculated zero.

| family | Required location keys besides family/field | Required request kind | Exact field enum |
| --- | --- | --- | --- |
| v4_member | interval_index,segment_index,member | mauve_v4_segments | alignment_columns, selected_column_count, selected_nongap_count, selected_gap_count, selected_canonical_count, selected_ambiguity_count, selected_other_count |
| v4_pair | interval_index,segment_index,pair | mauve_v4_segments | identical_canonical, substitutions, a_only_gap, b_only_gap, both_gap, ambiguous_or_other, comparable_canonical, identity_fraction |
| v4_coverage | member | mauve_v4_segments | known_union_bases, placement_bases, multiply_represented_bases, excess_placement_bases, denominator_bases, coverage_fraction, complement_bases |
| backbone_row | row_index | mauve_backbone | selected_member_count |
| backbone_span | row_index,member | mauve_backbone | span_bases |
| backbone_coverage | member | mauve_backbone | known_union_bases, placement_bases, multiply_represented_bases, excess_placement_bases, denominator_bases, coverage_fraction, complement_bases |
| bbcols_row | row_index | mauve_bbcols | selected_member_count, column_count |
| bbcols_interval | native_interval_index_0based | mauve_bbcols | union_columns, column_placements, multiply_represented_columns, excess_column_placements, bound_block_width, selected_block_fraction |
| xmfa_block | block_index | xmfa_alignment | selected_column_count, present_member_count, zero_member_count, omitted_member_count |
| xmfa_site | block_index,column_0based | xmfa_alignment | present_member_count, absent_member_count, gap_count, nongap_count, canonical_count, ambiguity_count, other_count, literal_entropy_bits, canonical_entropy_bits, canonical_majority_fraction |
| xmfa_symbol | block_index,column_0based,symbol | xmfa_alignment | count |
| xmfa_pair | block_index,member_a,member_b | xmfa_alignment | identical_canonical, substitutions, a_only_gap, b_only_gap, both_gap, ambiguous_or_other, comparable_canonical, identity_fraction |
| xmfa_coverage | member_number | xmfa_coverage | source_length, known_union_bases, placement_bases, multiply_represented_bases, excess_placement_bases, selected_coverage_fraction, complement_bases |
| xmfa_original_coverage | member_number,original_member | xmfa_coverage | original_length, known_union_bases, coverage_fraction |

Selection uses exact saved native keys, not a provider-created row offset. For v4 pair the selected cell lives in the matching `pair_segments[].counts[field]`; every other field is directly on its matching saved row (XMFA symbol: matching `symbol_counts[].count`). XMFA original coverage is inside the exact member's `original_coverage[]`. Duplicate/missing saved identities are errors or explicit missing projection states; no first-match fallback. Locations must be inside the original recorded request selection, even when the larger saved native document contains more data. A BBCols native interval can only be selected when its selected saved rows actually refer to that interval; there is no guessed interval ordinal before bytes arrive.

## Shared numerical meaning

All selected positions/ranges are explicit. Alignment-column positions and source positions are 0-based; source intervals are half-open. Native source integers retain their original 1-based/signed convention in parsed documents. A minus sign indicates orientation; it never negates a length. “All observed” refers to retained native rows under their declared completeness, not whole-genome completeness.

Let selected placement intervals be `I_j=[s_j,e_j)` with multiplicity function `m(x)`. `known_union_bases`/`union_columns = |union I_j|`; `placement_bases`/`column_placements = sum_j(e_j-s_j)`; `multiply_represented_bases/columns = |{x:m(x)>=2}|`; `excess_placement_bases/column_placements = sum lengths - union length`. Multiplicity and excess are distinct. Units are nucleotides or columns for union/multiplicity, nucleotide_placements or column_placements for placement/excess. Known subset union remains available when supported; uncertain population state remains attached. Complement is `[0,D)` minus known union only with an admissible positive known denominator and sufficient population/source consistency. Fractions retain actual numerator/denominator; zero denominator yields not_measured rather than zero or division by zero. Overlap is retained and diagnosed, never summed as independent source coverage.

For literal-symbol fields the explicit case policy is applied first. Canonical is exactly uppercase A/C/G/T; ambiguity is exactly R/Y/S/W/K/M/B/D/H/V/N; gap is `-`; remaining admitted symbols, including lowercase under preserve, count as other. `uppercase` changes counting/comparison, not stored native rows. Counts have units characters or columns as enumerated below; no fractional weighting of ambiguity is performed.

Pair categories partition selected comparable row columns in this priority: both gap; a only gap; b only gap; identical canonical; differing canonical (substitutions); ambiguous or other. `comparable_canonical = identical_canonical + substitutions`; `identity_fraction = identical_canonical/comparable_canonical`. Missing symbols, absent members, incomplete populations and incompatible native rows retain their distinct native states. No source sequence/column is filled from a related genome, taxon or consensus.

All native modules currently emit uncertainty=null for these fields. Provider projection preserves any future contract-admitted uncertainty but does not estimate or fabricate it. `method_id` is copied from the actual cell, not inferred from a label. Native_number token precision/NA/invalid status is retained in full parsed documents. Except the explicit native-observation cells below, these numbers are calculated summaries of native observations; none is fitted confidence.

## v4

`alignment_columns` is the complete segment's native width (columns), while `selected_column_count` is the summed length of explicitly selected column ranges (columns). The five selected symbol counts count actual selected row/source characters: nongap, gap, canonical, ambiguity, other (characters). A complete ungapped coordinate anchor has known selected nongap count and zero gaps even without source bytes, but canonical/ambiguity/other and pair identity remain missing until C-bound source symbols are extracted. Gapped rows already contain native symbols; source mismatch remains a separate qualification. Incomplete N-member gapped sections do not shift surviving row ordinals or confer trusted membership.

For nonzero start `t`, the forward interval begins `abs(t)-1`; width is native anchor length for coordinate anchors, actual nongap count for gapped rows. Source characters for reverse anchors are extracted/reverse-complemented only from bound C ordered source components. Native start0 is absent membership, never position0. Selected per-base placements follow full-row nongap offsets; selecting later columns does not reset position origin. Pair fields use the exact per-segment pair and selected ranges above; first six category counts and comparable count are columns.

Coverage uses those selected placements. `denominator=none` preserves union but denominator/fraction/complement are not_measured. `native_declared_length` uses only one unambiguous effective native `Sequence<N>Length`; `denominator_bases` is native_observation. `validated_staged_length` uses only a bound C member source_length and required source consistency; its denominator is calculated. Both units nucleotides. Neither denominator proves the entire genome's retrieved contig census. Missing/mismatching source inputs can make dependent denominator/fraction unavailable while native geometry/symbol quantities survive according to the existing A output; D/E do not repair or relabel it.

## Backbone and BBCols

Backbone `selected_member_count` counts selected members with native present spans (members). `span_bases` is the native normalized interval length (nucleotides); a valid absent0/0 pair is zero span with absent state. Signs on both endpoints establish orientation under the exact sidecar dialect. Eligibility is count>=explicit minimum_selected_multiplicity, subject to native unresolved-member rules; eligibility is Boolean/null, never a confidence number. Coverage includes eligible selected rows and members. Singleton rows participate when k1 is requested. `validated_staged_length` needs bound C source lengths; there is no native backbone length declaration. Do not align backbone rows to BBCols rows by index.

BBCols `selected_member_count` counts selected members present in the row's explicit member tokens (members). `column_count` copies the usable native width token (columns, native_observation). A positive row left `l` and width `w` correspond to `[l-1,l-1+w)` in that internal interval's alignment columns. Group only by the actual `native_interval_index_0based`, retaining every selected row. Union/placement/multiplicity/excess are computed only from eligible parsed selected rows. These interval columns have no whole-genome denominator. `bound_block_width` is the width of the one explicitly C-bound XMFA block (columns); `selected_block_fraction=union_columns/bound_block_width` only with that witness, valid member relationships and column bounds. If calculation was not requested, these two cells are not_measured. If witness absent/conflicting, their native missing/incompatible states survive while independent union remains usable. Equal ordinal, width or file count is not a join. BBCols member tokens are not an exhaustive genome/member census.

## XMFA

Block `selected_column_count` counts explicitly selected columns (columns). Present/zero/omitted member counts count selected members by native row state (members), with conflicts/incomplete membership retaining native unavailable states. Site present/absent member counts have units members. Gap/nongap/canonical/ambiguity/other and per-symbol count have units characters and count only the appropriate actual rows at that selected column. Literal entropy is `-sum_s p_s log2(p_s)` over literal observed symbols, including gap; canonical entropy uses only A/C/G/T, normalized by their sum. Units bits; empty population is not_measured. Canonical-majority fraction is maximum canonical count / total canonical count, with those quantities retained. Selected pair counts follow the exact partition above; no pair is manufactured for an unrequested pair or missing row.

Coverage bases are distinct explicit parameters: represented uses selected native residue placements; multi_member_block requires a block containing at least two selected present members; cooccupied_column requires at least two selected nongap members at that particular selected column. Native placements remain available independently of source binding. Source length/fraction/complement require actual validated neutral bindings and source checks. Original coverage further requires explicit source-to-Occurrence maps; mapped intervals are unioned in the original forward coordinate system, original_length is the explicit known denominator, and partial/conflicting maps retain their native limitations. There is no gene/contig inference from FASTA header names.

Coordinates and inverse coordinates are retained typed integer/enum records, not NumericCells. Forward mapping counts nongaps preceding the column in the **full** native row; reverse uses the actual reversed source axis and complements the literal symbol. Gap/absent/incompatible have no invented source position. Source coordinate requires bound/check-matched actual source record; original coordinate requires the explicit map. Inverse returns every physical native cell matching that requested member/position; multiple placements are not deduplicated. `none_in_document` means no retained native match under complete document search, not absence from a genome. Incomplete search is unknown even if it has useful partial matches.

## Executed small offline examples

`offline_probe_001.py` and `OFFLINE_EXAMPLES_001.json` call the real existing public functions. Native document bytes are the retained upstream Mauve examples. All task/source/path/interval binding envelopes in the old verification fixtures are synthetic offline evidence, **not an authentic BV-BRC run**. The separate XMFA source fixture is used directly because B's C fixture correctly has `xmfa_source_inputs=null`; no new C projection was invented.

| Native example / explicit parameter | Actual result |
| --- | --- |
| Official v4 small.mauve, all observed segments, native lengths | member0 union690 / declared693 =0.9956709956709957, complement[578,581); member1 2000/2000=1 |
| v4 complete gapped segment | width269; nongaps4/269; gaps265/0; canonical pair identity4/4; coordinate-only anchors retain missing identity |
| Separate backbone k2 | unions50,49,19 / staged lengths50,49,41; fractions1,1,19/41 |
| Same saved backbone k3 | unions18,18,19; fractions18/50,18/49,19/41 |
| Separate BBCols k2, synthetic explicit block witness | union52, placements52, overlap0, bound width52, fraction1 |
| Same saved BBCols k3 | union19, bound width52, fraction19/52 |
| BBCols without XMFA/association inputs | native union52 remains available; bound-block width/fraction missing |
| XMFA block0 pair1/2 | canonical identical40, substitutions8, comparable48, identity40/48; a-only gap1,b-only gap2,both gap1 |
| XMFA block0 pairs1/3 and2/3 | identical14, substitutions4, comparable18, identity14/18 each |
| XMFA represented | coverage50/50,49/49,41/41 |
| XMFA multi_member_block | coverage50/50,49/49,19/41 |
| XMFA cooccupied_column | coverage48/50,48/49,18/41 |
| XMFA block0,row0,column0 | literalT, reverse, native0based49/1based50, forwardA, source record position49; no original map fabricated |
| XMFA member1 position49 | unique retained match at block0,row0,column0 |

The probe reproduces A/B saved numerical results exactly, changes explicit k without reparsing, and validates saved neutral components with scientific entry points disabled. Third-party bundled JSON schemas were warmed before the I/O barrier. This verifies neutral inputs/outputs and the proposed separation, not a D provider, E facade, F custody path, live service or complete episode integration; those implementations are still required.
