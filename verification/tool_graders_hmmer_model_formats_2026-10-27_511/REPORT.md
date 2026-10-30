# HMMER binary/HMMER2 model-format verification

This is implementation evidence for a bounded part of R2, not a goal or scope
amendment. The original user attachment remains authoritative. The overall
HMMER/Infernal/Rfam R2 group is still unfinished.

## Implemented and verified boundary

The explicit `hmmer_binary` and `hmmer2_ascii` branches now decode into the
existing `hmmer_model_extraction_v1` contract. Binary records retain original
float bytes, field bounds and native metadata. HMMER2 records retain integer
scores, their actual null references, configured states and unavailable fields.
Both feed the existing shared model/artifact/statistics/emission calculators.
There is no format-specific scoring sheet or competing numerical policy.

The shared validators check source values and relationships during saved
recalculation. Binary counts agree with retained native scalars and probability
locators agree with the selected field/position/slot. HMMER2 nominal values
outside probability range remain inspectable and unavailable as probabilities;
they are not clamped or normalized. Missing and ambiguous null references differ.
HMMER2 topology and conversion limitations do not erase valid native counts or
unaffected per-position quantities. Historical unsupported saved envelopes are
not silently re-extracted or rewritten.

Existing producer, result worker, publication and authenticated requested-return
paths consume those shared outputs. Unrequested fields remain in retained data.
The corresponding field descriptions were corrected without introducing new
message templates or changing episode ownership, credit or continuation.

## Actual attempts

| Attempt | Outcome | Meaning |
| --- | --- | --- |
| check001 | Staging failed before any handle or test | Archived negative-test named pipes could not be copied as regular artifacts. The staging copier now records skipped special files and aliases. Original failure evidence is retained. |
| check002 | 1,022 passed; 80 failed; 562.42 seconds | First integrated check, including both actual local native conversion/Workflow cases. |
| check003 | 80 passed; 415.73 seconds | The 78 fixture-dependent failures, plus corrected supported/unsupported binary statistics cases. |
| check004 | 10 passed; 2.51 seconds | Both native metadata directions and eight explicitly constructed command-log cases. |

All 80 original failures were accounted for. Seventy-eight lacked the archived
producer267/check002/temporary fixture tree in the frozen snapshot. One test
still expected a supported binary model to be unsupported. One test invented
a COM header in a native fixture whose command-log length is zero. These repairs
changed test setup and assertions, not production code. The original failures
were retained. The restored fixtures reuse native outputs; their producers were
not rerun. The two successful check002 conversion jobs were not repeated.

There are 1,112 distinct current cases with passing outcomes across these three
executed attempts, with no overlap in their passing node identities. This is
not a claim that one fresh 1,112-case suite ran. The two obsolete failed test
definitions were replaced with explicit supported/unsupported and absent/present
metadata coverage. Other passing test definitions were retained.

The original handles for check002, check003 and check004 were collected only
after terminal/quiescent status. Every receipt confirms unchanged frozen source,
dependencies, interpreter and standard library. Every execution audit has empty
outside-module and unbound-native-mapping lists and unchanged native pins. Each
selected job used 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time limit.

## Native numerical and episode examples

The binary and HMMER2 Workflow cases each selected one actual tiny `hmmconvert`
job. Decisions were scripted, while native work, storage, calculation,
publication, requested results and onward scientific-parent returns followed
production paths. They do not establish biological annotation accuracy or live
external-service/HPC behavior.

Both outputs decode one model with 12 positions and native NSEQ=3. Binary bytes
have the original SHA256
`4d3f4b96321b7383137f3b19814fb1c1d7310e247da4dc0b84d2f879a2cd565c`.
Its comparison contains 611 probability cells with maximum absolute difference
`9.008887857930858e-09` from the retained rounded ASCII view.

HMMER2 output SHA256 is
`37a65d6515e1d4b657ff8ea3ce70cc002e6fedfec9abcb43d9bced646b87de7b`.
The original NULE(A)=656 and first-position A score=3666 are retained. Their
nominal reconstruction exceeds one, so no valid probability is fabricated.
The conversion comparison retains 526 comparable core cells and qualifies the
whole-model equivalence as incompatible rather than asserting a pass.

Every returned quantity equals its saved component's value, state and units.
Both boundaries return exactly the selected rows and population. Saved-only
recalculation succeeds with acquisition, parsers and native work disabled;
changing the explicit tolerance leaves original artifacts unchanged. Replay
and redelivery preserve observations and receipts and do not hydrate unrequested
full numerical artifacts. Each completed own action still has one observation.

## Review and limits

Root reviewed the full 508 format contract, 511 coding handoff, shared-consumer
production diff, source-cell implementation, 514 boundary review, focused repair
diff, new Workflow test and its accounting/projection/replay helpers, all final
receipts/audits and original JUnit failures. The 514 review inspected complete
decoders and consumers and supplied seven concrete defects repaired before
check002. Worker515 independently traced native COM reader/writer semantics and
the full extraction/comparison path. No broad unperformed audit is claimed.

All affected HMMER production files still match the verified check002 snapshot;
the two final repaired test files match their corresponding follow-up snapshots.
Two literature files outside this workload differ from the check002 package
snapshot. They were not modified by this workload, and this report does not
claim a fresh integration check of those unrelated current bytes.

Authentic native evidence here establishes little-endian HMMER3/f and generated
HMMER2 ASCII. Older HMMER3 revisions and big-endian layouts have source-defined
synthetic grammar checks, not authentic producer coverage. Historical HMMER2
binary/EVD and earlier formats remain explicitly unestablished. Index/profile
internals and unavailable provenance remain unknown.

Remaining R2 work includes native alignment-map cases, task/steering and resource
instruction presentation, and the outstanding authentic-format/resource checks.
The alignment-map review additionally identified duplicate driver calculations
and an ordered-summation mismatch; those are open work under the shared-scoring
requirement, not repaired by this packet. Other R1–R7 obligations remain intact.

The authoritative goal objective and all ten operating principles, followed by
the complete 508 contract, were reread before this final evidence record.
