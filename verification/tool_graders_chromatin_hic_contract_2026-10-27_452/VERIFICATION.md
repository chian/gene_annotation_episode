# Native prerequisites and verification handoff

All numbers below are independent authored expectations for future native
fixtures unless explicitly identified as observed packet452 facts. They are not
results of a HIC parser or calculator run.

## Actual retained native bytes

`prerequisite002/testBp.hic` is the complete1,908-byte upstream fixture from
aidenlab/hic-straw commit6cf5848480906f7a6ec32200b550236b5268cd1e,
`test/data/testFiles/testBp.hic`. Its SHA256 is
`707c22140377a8d87e5856fe728f2b329ec5cf926e0f3f6f40011ada658983bb`.
The GitHub tree declared its exact size and Git blob identity before acquisition;
the bounded job checked both exact size and Git blob SHA1, retained HTTP headers,
and computed SHA256. Magic was HIC\0; little-endian header version was8.
Only those header fields were examined. No population/count/normalization was
decoded, so this is a real-format version-rejection fixture, not v9 proof.

The tree also advertises testFrag.hic2,114bytes and test_chr22.hic2,186,320bytes;
neither was acquired. The earlier aidenlab/straw tree advertises test.hic770,604
bytes; it was not acquired or assigned an assumed version. Upstream live v9 tests
refer to a human file with a normalization index beyond201GB. hictk's documented
test collection includes a128MB v9 file inside a larger archive. Neither large
source was acquired. Their presence does not complete the missing fixture task.

## Exact supported native generator to prepare next

Official hictk release2.2.0 is pinned to commit
`473017312558cd805f470722c2c91a03b91df807` (retained API tag response).
Its native HiCFileWriter asserts version9 and writes actual zlib-compressed blocks,
master/zoom indexes, footer and normalization vectors. Retained official files:
`hictk-writer-api-v2.2.0.hpp`, `hictk-writer-v2.2.0.hpp`,
`hictk-writer-data-v2.2.0.hpp`, `hictk-reader-v2.2.0.hpp`,
`hictk-cli-load-v2.2.0.cpp`, `hictk-creating.rst`. No binary was installed,
built or run. No prepared hictk environment or successful invocation is claimed.

The next prerequisite workload should obtain an explicitly selected pinned native
binary or prepare this exact source using its documented build dependencies,
under the existing resource/installation policy. It must pin the actual resulting
binary, compiler/build and shared-library bytes; source tag alone is insufficient.
No broader corpus or HPC login is needed for this toy verification workload.

The official CLI accepts a deterministic pre-binned COO file and chrom.sizes.
The following is a concrete *proposed invocation*, not a run receipt:

```text
hictk load --format coo --output-fmt hic --bin-size 10 \
  --chrom-sizes four.chrom.sizes --assembly synthetic_four_bin \
  --zero-based --validate-pixels --no-transpose-lower-triangular-pixels \
  --skip-all-vs-all --threads 2 --chunk-size 32 --tmpdir <attempt>/tmp \
  four.coo four.hic
```

The thread option in the inspected2.2.0 CLI has minimum2, so do not propose1
from memory. All inputs/output/tmp/cache belong to the selected bounded attempt.
No --force overwrite or guessed binary path is prescribed. Native generation is
a finite supporting operation; it earns no gene-function confidence. Generated
values remain explicitly synthetic even when serialization is genuine.

`four.chrom.sizes` is exactly `chrA\t40\n`. `four.coo` contains these nine rows,
with fields bin1_id,bin2_id,count and one newline per row:

```text
0 0 4
0 1 2
0 2 6
1 1 4
1 2 2
1 3 2
2 2 4
2 3 2
3 3 4
```

Use actual tab delimiters in the retained input file. Expected complete matrix:

```text
4 2 6 0
2 4 2 2
6 2 4 2
0 2 2 4
```

The missing(0,3) must be established by complete matrix/index/block reads. It is
not a native NaN. Nine stored native records, four diagonal and five off-diagonal,
represent14 directed cells; two directed cells are implicit zero. Unique unordered
cells10, directed cells16. A generator may choose a dense block with padding;
do not demand a byte-for-byte layout from the abstract COO. Record actual block
encoding/cardinalities and compare independently decoded nonfiller records.

For supplied divisive weights use the public writer overload
`HiCFileWriter::add_norm_vector(type,chrom,"BP",r,balancing::Weights,...)`, with
explicit DIVISIVE weight identity and synthetic type `SYNTHETIC_DIVISIVE`.
The public API's exact argument types are retained. A future small C++ harness
may call that real writer for weights[1,2,1,2], NaN,zero,negative andInf variants.
It must use the official writer API and pin resulting bytes; do not hand-author
a pretend Python matrix and label it native format. The writer's shape validator
requires ceil(L/r) weights; shape-corruption tests should mutate retained native
bytes after generation with exact mutation provenance, not hide a failed writer.
Whether this writer successfully serializes each invalid-weight case must be
observed and reported; no unrun case is claimed as available.

Sparse versus dense and short versus float encodings require independently
retained writer fixtures. hictk2.2.0 writes float values and chooses sparse/dense
using actual geometry. It does not establish the short encoding merely because
the numbers are integers. Obtain an actual pinned Juicer writer for int16 and
mixed v9 position-width variants, or an explicitly documented native-format
fixture writer that emits valid whole HIC files and is checked by an independent
official reader. A test that directly instantiates H1's decoded block structure
does not establish a binary encoding. Tiny four-bin data alone cannot exercise
rotated v9 block boundaries; use an additional sparse multi-block input with
independently known coordinates, keeping files small.

## Checkable scientific numbers (future HIC fixtures)

| Selected case | Expected numerical result |
|---|---|
| Four bins, raw, anchor0→2 | Raw6; distance2 population[6,2], n2,sum8,sum_squares40,mean4,population variance4; fold1.5; strict threshold2 false. |
| Same raw data, population[0,30) only | Three bins; distance2 population[6],mean6,variance0; fold1. Exact selected population matters. |
| Four bins, divisive weights[1,2,1,2] | Distance2 normalized values[6,0.5],sum6.5,sum_squares36.25,mean3.25,variance7.5625; fold24/13≈1.8461538461538463. Raw contact remains6. This differs from439's multiplicative example. |
| Same vector missing | Raw6 retained; selected normalized value, expected and fold null/normalization_missing. No silent fold1.5 raw fallback. |
| Weight at bin1 is NaN | Its whole row/column masked, including sparse zeros. At d2 nominal2,masked1,valid1,expected6,fold1 for(0,2). A zero raw cell touching bin1 has unavailable normalized value. |
| Complete sparse empty four-bin matrix | Bins4,stored0,explicitzero0,directed16,unordered10,implicit-zero-directed16; raw0,expected0,fold null/zero_denominator. Requires actual present zero-block matrix/zoom witness. |
| Absent matrix or selected resolution | Raw values and observed/implicit-zero counts unavailable; no constructed1x1 or4x4 zero matrix. Known physical axes and nominal n*n cell population may survive separately; they assert no contact values. |
| Present dense block padding | Dense slot NaN/int16 sentinel counted only as encoding filler. Nonfiller count matches outer nRecords; canonical matrix/counts equal independent sparse representation. Generic row-list NaN and norm NaN must fail/mask differently. |
| Six bins, adjacent contacts[5,1,5,1,5], other cells zero,w1 | Five full cross-window sums;mean3.4,variance3.84; lows z=-3/sqrt6, highs2/sqrt6. Strict z<-1 minima at20/40bp; domain[20,40),20bp,0.02kb. At-1.3 no boundaries, same saved sheet. |
| chrB length35,resolution10 | Bins[0,10),[10,20),[20,30),[30,35); lastbase34→bin3; end35valid; end40invalid; start31unaligned; no extra bin at35. |

NaN mask, invalid weights and lower-support data do not become confidence scores.
Retain original counts, denominators, raw/normalized distinctions and specific
qualifications. Native matrix sumCounts is neither selected-region expected
contact nor a completion witness.

## Required native and failure verification matrix

1. Native identity/magic/endian/version, exact chromosome index order including
   All pseudochromosome, exact assembly assertions and physical terminal bins.
   Preserve genuine original v8 file for unsupported-version check.
2. Valid sparse v9 for all independent x/y width flags; dense int16 and float32
   fixtures; finite explicit0 versus absent0 versus dense filler; type1 NaN/Inf;
   unknown flag/type and nRecords/nPts mismatch. Inspect all bytes independently
   before comparing H1 output to source values.
3. Full master and zoom indexes, valid zero-block matrix, absent matrix, absent
   resolution, missing entire footer, short index entry, duplicate block ID,
   out-of-file offset/size, wrong matrix chromosome pair and FRAG-only input.
4. Corrupt/truncate compressed block, zlib checksum failure, incomplete stream,
   trailing compressed payload, inflated size beyond ordinary resource fit,
   native row coordinate outside physical bins, duplicates across blocks and
   reversed native cis rows. Preserve valid earlier blocks/populations; never
   grant complete sparse absence after a missing block.
5. Exact divisive normalization type/chromosome/BP/resolution. Missing type,
   missing NVI versus broken NVI, truncated vector, declared/actual length
   mismatch, selected range beyond vector, valid terminal padding, NaN/0/negative/
   Inf and insufficient readable bytes. Raw can remain valid when selected
   weighted results are unavailable. No use of native OE/expected as raw contacts.
6. Same native bin IDs on two biological chromosomes, duplicate names rejected,
   explicit element occurrence joins, native token chr1 vs1 conflict, wrong
   assembly assertions, same-bin anchors, chromosome boundary and subpopulation
   boundary tests. No public gene name required.
7. C1 real arrays → loader → sheet → C2 unchanged scientific arithmetic → selected
   projection. Recalculate saved bundle with changed threshold/window and raw
   versus already-retained divisive weights with source HIC removed/inaccessible,
   no network and no parser/executable call. Original hashes/history unchanged.
8. Actual selected library route → launch/local original attempt → source staging
   and immutable software pins → producer → exact seals/capture → worker → received
   typed form, including unavailable requested weights and interrupted later
   population. Existing credit/controller/endpoint/replay mechanics remain.

For corrupted fixtures retain original file, mutation offset/before/after bytes,
derived hash and declared expected failure. A corrupted file is an explicit test
input, never a partial biological download represented as complete. Complete
empty-matrix fixture construction must retain the native writer's actual output:
if the writer omits the matrix entirely, that tests absence, not genuine zero.

## Actual bounded attempts in packet452

| Attempt | Actual outcome | Evidence |
|---|---|---|
| prerequisite001 | Terminal/quiescent exit1 before acquisition or schema extraction; built-in zlib has no __file__. Original failed snapshot retained. | handle.json,receipt.json,stderr.txt,source_pins_before/after.json |
| prerequisite002 | Explicit repaired metadata probe; terminal/quiescent exit0; actual imports/metadata and native v8 bytes above; literal schema extraction without production import. | Same files plus DEPENDENCIES.json,FIXTURE_ACQUISITION_REQUEST/RECEIPT.json,CURRENT_LITERAL_DEFINITIONS.json |

Both were launched/collected through copied440 packet-local calls to the existing
local_jobs/native_lifecycle, with actual enforcement memory_max21474836480,
memory_swap_max0,runtime_max infinity, scratch policy4294967296. Scratch is
monitored with possible overshoot, not a hard aggregate quota. Original handles
and failed evidence remain. Probe002 elapsed1.268401084s and observed scratch
143,360bytes. No automatic retry occurred: the failed terminal attempt was
inspected, the built-in-module pin assumption corrected, and a new named attempt
explicitly selected. Source/interpreter pins remained unchanged in both attempts.

Native parsing, v9 generation, scientific calculator tests and full episode
integration are **not executed** in this packet. Do not infer them from the probe.

## Later return-schema prerequisite checks

schema001 statically traversed the production schema literal and retained all
three complete field-schema trees, their exact transitive definitions and source
hashes. schema002 then actually invoked `chromatin_fact_sources()` under the
explicit `.venv/bin/python` interpreter and compared the complete exports with
those static trees: all three exact canonical-JSON comparisons passed. Actual
exports and individual schemas are retained in schema002. Both jobs reached
terminal/quiescent exit0 with unchanged source/interpreter pins and the same
20GiB/4GiB/zero-swap/no-wall lifecycle constraints. schema002 elapsed0.638025146s;
observed scratch794624bytes. Failed preliminary infrastructure invocations remain
documented in SCHEMA_LAUNCH_FAILURES.md; they created no job or handle.

HISTORICAL_SCHEMA_COMPATIBILITY.md defines the precise two-schema amendment,
unchanged value semantics, ownership and pending old-form replay/rejection tests.
No changed-production compatibility test or HIC integration test was executed.
Separate packet454's native v9 fixture is acknowledged in HANDOFF.md as root-
reported external workload evidence, not a452 native parse.
