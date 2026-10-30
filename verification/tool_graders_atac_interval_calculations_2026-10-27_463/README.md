The contract005/006 interval-calculation component for fixed row
`B-L125-analyze_atac_seq_differential_accessibility` is implemented and verified.
This packet does not complete the scientific tool, resource binding or episode
path. The original supplied goal remains authoritative; no repository goal
file was read, created or changed.

Owned production changes are
`gene_annotation_episode/atac_differential_calculations.py` and
`tests/test_atac_differential_calculations.py`. The module exports exactly:

| Function | Supplied input and saved numerical output |
| --- | --- |
| `iter_atac_track_segments(tracks, *, intervals)` | Four ordered native nine-column row iterables and explicit disjoint populations; actual boundary intervals, values/states, native row ordinals and source extents. |
| `iter_atac_interval_components(segments, *, depth1, depth2, depth_unit, pseudocount)` | Every segment plus the unchanged result shape of the parent-owned `calculate_atac_interval_scores` leaf. |
| `iter_atac_differential_regions(components, *, cutoff, min_length_bp, max_gap_bp)` | Separate derived regions with qualifying lengths, bridged lengths, weighted numerators/denominators, binary64 and binary32 means, boundary reasons and source extent. |

The source follows the accepted
[interval contract005](../tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_CALCULATION_CONTRACT_005.md),
[edge clarifications006](../tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_EDGE_CLARIFICATIONS_006.md),
[numerical leaf004](../tool_graders_atac_differential_plan_2026-10-27_460/NUMERICAL_LEAF_CONTRACT_004.md)
and [native row/depth contract461](../tool_graders_atac_native_contract_2026-10-27_461/CONTRACT.md).
The parent resolved concrete boundary/three-valued-logic questions before their
implementation and recorded the answers additively in006.

The single bounded scientific check, `check001`, passed **87 tests** with no
failures or errors, pytest duration0.27s, native process exit0. The original
durable handle is
`check001/handle.json`; its unit is
`gene-local-job-5352366ed01e4606ba07ce15f19cfac2.service`.
[receipt.json](check001/receipt.json), [stdout.txt](check001/stdout.txt) and
[junit.xml](check001/junit.xml) retain the actual result. RAM was enforced at
21474836480 bytes, swap0, no wall budget; scratch policy4294967296 bytes with
23486464 bytes observed. The existing lifecycle reports scratch monitoring as
visible allocated bytes with possible overshoot and a hard per-file limit;
this packet does not claim a new filesystem quota. Immutable source, native
input and interpreter/administration-script pins matched before and after;
checkout drift was empty at collection. No job was restarted or replaced.

Retained-native verification used the actual files from packet460/native001.
It verified all15 native likelihood values against the separately retained
`NATIVE_DIAGNOSTIC.json`, complete track partitions and corrected derived
regions. For declared synthetic depths1 and2 `million_tags`, pseudocount0.01,
cutoff3, minimum50bp and gap0, the filled numerical example is:

| Derived category | Actual track interval | Numerator | Qualifying denominator, bp | Mean, signed-log10-LR units |
| --- | --- | ---: | ---: | ---: |
| condition1 | chrToy[100,200) | 1774.08447265625 | 100 | 17.7408447265625 |
| common | chrToy[200,300) | 0.00005425064273367752 | 100 | 0.0000005425064273367752 |
| condition2 | chrToy[300,400) | 1214.8710250854492 | 100 | 12.148710250854492 |

[FILLED_NATIVE_EXAMPLE.json](check001/FILLED_NATIVE_EXAMPLE.json) retains all
five input segments, raw nine-column tables, all component measurements and
the derived regions. It also preserves the original native BED text separately:
condition1[0,100) score17.7408, common[100,200) score5.42506e-07 and
condition2[200,300) score12.1487. No native coordinates or rounded scores were
rewritten. Declared fixture depths remain declared values; no observed count
of1000000/2000000 was fabricated.

A second retained-native test verified all actual BAM-derived boundary unions
from110/35/210/69 rows in the four tracks, including the unequal source-row
lengths. Its depth inputs100 and200 tags came from the native post-filter XLS
headers, separately from pre-filter105/200. Condition1 stays unknown after8060;
all four tracks stay unknown after10060 within the explicit12000bp population.
The valid condition2/background component survives the missing condition1 tail.
This test does not assert BAM-native region coordinates or newly executed BAM
analysis.

Verification categories remain separate: two retained-native oracle/geometry
tests; one saved-native-table recalculation test with changed cutoff and
pseudocount, subprocess/network acquisition forbidden and input immutability
checked; and84 synthetic numerical, structural, failure and streaming checks.
Synthetic cases cover clipping, disjoint populations, exact chromosome tokens,
measured zero, missing/invalid/negative cells, duplicates/overlaps, unlocated
corruption, out-of-order rows, late stream failures, independent valid
components, inclusive category ties, threshold lengths/gaps, unknown-boundary
behavior and weighted means excluding bridges. A10000-interval stream checks
one-row lookahead without materialization; a2**63-1 coordinate span checks
boundary-based work without per-base expansion.

Only the deterministic three-function calculation chain was exercised here.
Tests decode known-valid saved fixtures into the agreed tuple port; this helper
is explicitly not the production native parser. There was **no new MACS2 run,
network acquisition, production parser/sheet integration, worker receipt,
typed-return or episode-communication verification** in this workload.

The parent-owned sheet/result consumer must still supply and validate actual
reference/sample/condition/normalization compatibility and depth provenance,
retain every result and late failure, and connect the stream to the durable
result/return path. These pure functions cannot establish those metadata joins
from row tokens. Paired-end, matched-control, SPMR, other native versions and
biological replicate uncertainty are not verified by this component.

The partition sweep retains only active overlapping rows and one lookahead per
track. Region processing retains three current category accumulators and each
open region's required qualifying-ordinal list; that list necessarily grows
with the region's output population. The caller continues to own bounded
storage of complete results. Early iterator termination or a later exception
cannot establish full table identity/completion. No output truncation, resource
substitution or hidden retry was introduced.

The original objective and all16 principles were read verbatim after native
inspection and before coding, then again after the successful check and source
review. The complete agreed contracts004/005/006 and461 were reread before this
component handoff. These are development records, not runtime gates or credit.
The parent-owned leaf, native parser/sheet, catalog, trackers, W05, literature,
evidence-axis and episode execution code were not edited by this workload.
