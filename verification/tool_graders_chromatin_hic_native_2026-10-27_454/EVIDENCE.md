# Native HIC prerequisite evidence

`FIXTURES.json` records27 actual complete native files, each with input identities,
observed version/encodings, original lifecycle receipt, independent hictk dump,
byte audit, numerical expectations and limitations. All values are deliberately
synthetic; native serialization and decoding were actually executed. No
production reader/calculator/episode result is claimed by this packet.

## First fixture and scientific variants

| Case | Retained native evidence | Independent expectation |
|---|---|---|
| `native004/four.hic` | Official hictk CLI; version9;297bytes; one float32 dense block, nRecords9,nPts16,w4;7 filler slots; exact9-row dump. | Raw0→2=6;d2=[6,2],n2,sum8,sum-squares40,mean4,variance4,fold1.5. Subpopulation[0,30) gives mean6,variance0,fold1. |
| `native005/six_insulation/output.hic` | Official CLI; original adjacent contacts5,1,5,1,5; full native dump and block audit. | w1 has5 windows,mean3.4,variance3.84; strict z<-1 boundaries20/40bp; domain20bp=0.02kb. At-1.3 no boundaries. |
| `native005/terminal_two_chromosomes/output.hic` | Official CLI; chrA index0 and chrB index1; chrB actual length35. | Physical chrB bins[0,10),[10,20),[20,30),[30,35);base34→bin3;end35valid,end40invalid,start31unaligned. Native local bin IDs remain separate by chromosome. |
| `native005/terminal_with_all/output.hic` | Official CLI; genuine All entry at0, biological chrA1/chrB2 retained. | Preserve original indices; All's native length is not biological bp. chrB terminal bin remains[30,35). |
| `native005/sparse_multiblock/output.hic` | Official CLI;7 actual blocks;40,590bytes; all source rows match native dump. | Resolution1000;10000 physical bins;actual blockBinCount910,blockColumnCount11. Rows straddle x+y1820 pad and distance1286/1287 depth boundaries. Actual block ownership agrees with the reviewed v9 formula. |
| `native005/empty_input/output.hic` | Official CLI accepted empty input and produced121bytes with **no master-index matrix entries**. | Matrix absence; cannot authorize raw/implicit-zero values. It is not a zero-block fixture. |

The first file's7 dense fillers comprise6 opposite-triangle padding positions
and the omitted(0,3) slot. They do not become7 missing measured contacts.
Nine actual records represent14 directed cells, leaving2 implicit-zero directed
cells in the4×4 mathematical matrix. Dense slot ordinals remain in the audit.

## Official divisive normalization

`native009/valid/output.hic` was modified by the actual official writer API to
contain `SYNTHETIC_DIVISIVE` float32 values[1,2,1,2]. The independent official
normalized dump gives d2=[6,0.5]. Thus sum6.5,sum-squares36.25,mean3.25,
population variance7.5625 and fold24/13≈1.8461538461538463. Raw0→2 remains6.
`evidence011/NUMERICAL_CROSSCHECKS.json` checks these and the insulation moments
by independent scalar arithmetic, without production imports.

The official writer also actually serialized variants `nan`, `zero`, `negative`
and `inf`, each with its own native file, request and byte audit. Native NaN at
bin1 excludes that bin's normalized cells, including raw sparse-zero cells;
d2 has nominal2,masked1,valid1,mean6,fold1. Zero, negative and infinite weights
remain invalid supplied weights. Native hictk's numerical output for them is
retained as decoding evidence and does not authorize scientific arithmetic.

Requests for3 or5 weights were rejected with `weight shape mismatch: expected
4 values, found 3/5`. Their copied source files and errors remain under
`native009/short` and `native009/long`; no normalization fixture is claimed from
those failed requests.

Initial `--table weights --balance SYNTHETIC_DIVISIVE` commands were invalid:
hictk requires `--balance` only with `--table pixels`. Their original failures
remain. All6 corrected commands in `evidence011` use `--table weights` without
`--balance` and exit0; their complete vector dumps are retained.

## Actual independently serialized format cases

All16 cases below are real complete v9 files written by the separately documented
packet serializer, then validated and read by the official hictk binary. Each
raw dump exactly matches its independently declared input rows. They are not
misrepresented as hictk- or Juicer-generated outputs.

- `native010/rowlist_{i16,f32}_x{16,32}_y{16,32}/output.hic`: all8 independent
  count/x/y-width combinations. Width flags were observed from bytes.
- `dense_i16_fillers` and `dense_f32_fillers`:9 nonfiller contacts,16 slots,7
  respective int16 -32768 or float32 NaN fillers, independently read as the
  original9 contacts.
- `rowlist_explicit_zero` and `dense_explicit_zero`: all10 unordered contacts
  explicitly stored, including(0,3)=0; no implicit-zero directed cells remain.
  Their baseline matrix and d2 arithmetic match native004, but their storage
  cardinalities differ. In FIXTURES.json, `expected_rows`/INPUT.json describe
  the actual10 rows; the reused `upper_rows` field is the original9-row baseline
  reference, not the modified native record population.
- `present_zero_block`: actual matrix0_0 with BP10 zoom and blockCount0;220
  bytes; official native dump empty, with the present index/zoom independently
  established. Four bins,0 stored records,16 implicit-zero directed cells;
  raw/expected0 and fold unavailable due to zero denominator. This is separate
  from the official writer's absent-matrix file.
- `rowlist_nonfinite`: actual encoded NaN,+Inf,-Inf,negative and explicit-zero
  values survive independent native decoding. These are actual row-list values,
  not dense fillers or normalized-bin masks.
- `rowlist_i16_minus32768`: type1 -32768 survives as an actual negative contact;
  only its type2 use is a filler sentinel.
- `normalization_terminal_padding`: native vector[1,2,1,2,99] with declared
  length5 and four physical bins. Byte audit retains all5; official weighted
  pixel dump succeeds and corrected native weights dump returns the4 physical
  values. Extra vector storage does not create a fifth bin. This case was
  serialized by the packet writer; the official API's5-value request was rejected.

## What remains unverified here

- No H1 production parsing, H2 sheet/custody validation, H3 producer binding,
  saved-sheet recalculation or full configured episode communication path was
  exercised by this prerequisite packet. Their owners must use the retained
  actual native files and independent expectations.
- No Juicer short-encoding build was installed. Int16 and independent width
  coverage has the explicit whole-native-file serializer provenance above.
- The source-derived and byte-audited encoding cases do not replace corruption,
  truncation, duplicate/index/coordinate failures, malformed cardinalities,
  missing resolution/normalization, FRAG, or unsupported-version parser tests.
  No broad corpus was downloaded. The genuine version8 rejection file remains
  separately retained in packet452 and was not relabeled.
- hictk `validate` is retained with its actual native scope; the exact native
  pixel dump and byte audit, rather than a successful validation exit alone,
  establish the fixture record comparisons.

All native attempts, including three failed prerequisite/build attempts, are
closed and quiescent. Resource allocations remained20GiB RAM/4GiB scratch,
zero swap and no wall budget. Preparation/fixture generation earns no
gene-function confidence. No fixed tally changed.
