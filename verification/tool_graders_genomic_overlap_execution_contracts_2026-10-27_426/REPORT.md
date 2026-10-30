# Native genomic-overlap records and tool information

Component handoff, 2026-10-27. Scope is packet422/EXECUTION_WORKLOADS_004.md's
records/tool-information workload only. The immutable attached goal remains the
authority. This component does not complete B-L123 or increment the 112/308
scientific-tool tally.

## Implemented ports and ownership

`gene_annotation_episode/native_genomic_overlap_contracts.py` exposes all twelve
packet425 functions and its five fixed filename constants plus POLICY.
`gene_annotation_episode/native_genomic_overlap_tool_info.py` exposes both
four-field-information and commissioning-contract functions. The only other
files edited by this workload are its two named tests and this packet.

The seventeen G2 definitions are fixed Python data constants copied from the
frozen schema. Referenced G1 definitions come from its existing in-code schema
export and remain unchanged. Production never loads verification files.
Schemas are detached, self-contained local resources and retain reference scope
inside nested commissioning alternatives. Only supplied software bindings narrow
RequestedJob; no bindings means no exposed operation. Real resource routing is
the exact commission route `launch -> launch_local` at the supplied resource ID.
This is tool information, not a model prompt or an additional episode type.

Pure validators check closed shapes, required nulls, finite JSON, strict integer
fields, all ordered i<j comparisons, original source/format/set relationships,
input paths and identity-preserving reuse, fixed output lists, nominal and
realized commands, environment, policy, original hashes, set/pair/batch joins,
declared native outcomes, closed file declarations, seal hashes, timestamp order
and located failure indices. All APIs return detached objects.

The pair validator cannot inspect an occurrence count because SetOutput does
not carry one. It checks supplied parse extents and invocation facts. The batch
validator additionally checks canonical declarations, including zero-byte
canonical files for analytic emptiness and exact per-pair declaration joins.
Actual bytes, source access, selected-action authority, observed executable
identity and assignment-digest authentication remain driver/host responsibilities.
A matching declared digest is not source permission or a live observation.

The implementation preserves distinct successful invoked zero-byte output,
uninvoked analytic empty, invalid verified input, missing/mismatched source,
unavailable native software, nonzero native exit and publication failure. An
implementation/interpreter mismatch follows additive root clarification005:
verified originals may survive, but no G1 parse extent or invocation is invented.
Canonical publication failure may retain the complete parsed set while its
affected pairs remain unavailable. Independent sealed pairs remain unchanged.

## Inspected consumers and immutable inputs

Read AGENTS.md, the complete immutable attachment, EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION, PRACTICAL_EXECUTION and its original additive contract,
TASK_AND_STEERING, the tool-grader goal/principles and the fixed overlap status
row. Read the accepted workload and complete frozen425 contract/schema, the
relevant G1 types/validation/reader ports and accepted root clarifications.
Inspected the existing protein/RNA tool contracts and ExecutionEpisodes'
commissioning-schema and resource-tool consumers. Read the new parallel driver's
staging/normalization/software/native/sealing consumers to check handoff semantics.

Frozen425 CONTRACT.md SHA-256:
`10974e07f6509a9413db6634ecd1febcd26e1cc9165ef53ab974388dcb33c384`.
Frozen425 DATA_CONTRACT.json SHA-256:
`4b8f38595549bd32484121129132474bc6fd3f5e9f7be1130433a6b3a208c00e`.
Immutable goal SHA-256:
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.

## Actual verification

Both attempts are retained, with original source snapshots, selected requests,
before/after source pins, complete stdout/stderr, JUnit reports, lifecycle files
and receipts. These are overlapping test runs, not 204 unique tests.

| Attempt | Pytest result | Pytest duration | Executed-source pins | Checkout drift |
| --- | --- | --- | --- | --- |
| check001 | 100 passed | 10.52 s | unchanged | none |
| check002 | 104 passed | 11.62 s | unchanged | none |

check002 is the current production-source verification. Its service-wall
duration was 12.490638897 s; that is not native bedtools runtime. Receipt
enforcement reports memory_max=21474836480, memory_swap_max=0 and runtime infinity.
Scratch limit is 4294967296 bytes, monitored allocated bytes with possible
overshoot, plus the existing hard per-file limit. It is not a hard aggregate
filesystem quota or filesystem sandbox. Observed scratch was 22315008 bytes.

Tests cover exact frozen records, all seventeen schema definitions, unchanged G1
definitions, two-/three-set fixed outputs, shape/type/format/order/path errors,
original plan/command/allocation mismatches, pair/batch/source joins, failure
index leakage, empty/invalid/missing/mismatched C with unchanged AB, unavailable
software, unverified implementation, canonical publication failure, nonzero
pair output with later independent successes, analytic-only no-probe batches,
successful present zero-byte native stdout, detached objects, and nested schemas
for distinct explicitly bound deployments. A guarded pure-port test makes file
opening, stat, process launch and sockets unavailable while validation succeeds.

Executed production SHA-256 pins from check002:

| File | SHA-256 |
| --- | --- |
| native_genomic_overlap_contracts.py | 63938c3d1de175a5bfae7d0006468c596ed0b951e2409a38c353bf846f23d6f0 |
| native_genomic_overlap_tool_info.py | 669b61bdf1ced1d7cf670b0b82288c1fb414013bc11ead9e6cd5cb331b1a282a |

## Numerical example and meaning

`check002/FILLED_EXAMPLE.json` retains a complete G1 sheet and component snapshot
recalculated from packet425's supplied synthetic strings. It is explicitly
hand_worked_synthetic_supplied_data, with native_execution_claim=false. This
workload made no bedtools call and observed no new native format.

Inputs are A=[0,10),[5,15), B=[7,12), C=[10,20), all on chr1. Coordinates are
zero-based half-open. Every input occurrence is retained, with reference relation
unknown. Exact unfiltered results are:

| Pair | Native pair count | Sum of native overlap widths (bp) | Unique shared bases (bp) | Combined covered bases (bp) | Jaccard |
| --- | ---: | ---: | ---: | ---: | ---: |
| AB | 2 | 8 | 5 | 15 | 5/15 = 1/3 |
| AC | 1 | 5 | 5 | 20 | 5/20 = 1/4 |
| BC | 1 | 2 | 2 | 13 | 2/13 |

Pair count counts valid native occurrence pairs. Width sum adds their supplied
native bp widths, each checked by G1 against min(end)-max(start); overlapping
occurrences can count shared bases repeatedly. Unique shared bases measure the
union of pair intersections. Combined covered bases equal union(A)+union(B)
minus the unique intersection. Jaccard divides unique intersection bases by
combined-union bases; its numerator and denominator remain inspectable. A zero
denominator is undefined, not confidence zero. These are deterministic geometry
quantities with no invented uncertainty or annotation probability.

The retained minimum-overlap=4 snapshot has AB selected count1, selected width
sum5 bp and A affected-occurrence fraction1/2. The full native population remains
two AB pairs with width sum8 bp. Thresholds belong to the separate saved-sheet
calculator; they do not change the acquisition command.

## Remaining integration and evidence limits

Packet427 owns native driver/local lifecycle verification. Root owns shared
resource registration, assignment/source authority, original-action dispatch,
observation/output consumers, full capture and retained-only replay, result-worker
binding, typed return/admission and complete Workflow verification. Those paths
are not established by this pure component's 104 tests. No new configured-model
episode, scientific credit, literature grader or W05 aggregation was run or
changed. No live-resource or whole-tool completion is claimed.

The objective and all sixteen design principles were reread verbatim after
substantial source/native-record examination and at handoff, followed by the
accepted contract. These are implementation checks, not runtime gates or credit.
