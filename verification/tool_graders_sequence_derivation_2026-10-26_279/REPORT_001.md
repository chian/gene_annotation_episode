# Translation and extraction: integrated numerical grading

The two existing operations, `sequence.translate` and `sequence.view`, now
retain their complete native result and separate numerical sheet/calculation.
The selected effective request, actual input and exact original coordinate map
are supplied to the grader. Translation also captures the genetic-code table
used by that execution; recalculation does not consult a later installed table.
Tool information is registered with name, description, local resource and
substantive instructions. These remain transformations, not independent
annotation-confidence measurements.

Actual slotted scientific children select and execute these operations. The
existing coordinate observation receives the declared numerical quantities,
the full sheet stays in a source artifact, and the requested typed facts reach
the parent. Grading failure preserves the native product with a typed partial
outcome. Replay and repeated delivery preserve the original action and records.
Root's execution-tool catalog remains empty. No annotation scorer, literature
grader, continuation policy or new episode type was added.

## Verified numerical examples

* `GTGAAATAA`, code 11 with CDS semantics, produces `MK`: three consumed codons,
  two output amino acids, one omitted terminal stop and zero returned stops.
* `ATGTAGAAATAACC` produces `M*K*`: 14 input bases, 12 translated bases, two
  trailing bases, four codons, one internal stop and one returned terminal stop.
* Selecting original intervals `[1,3)` and `[5,12)` from `CATCCGAAATAACC`
  produces `ATGAAATAA`. Translation produces `MK`; its first codon spans the
  original intervals `[1,3)` and `[5,6)`, its second spans `[6,9)`, and the
  omitted stop spans `[9,12)`.
* Selecting protein positions 1, 0 and 1 from that product produces `KMK`:
  three protein-symbol occurrences at two distinct protein positions. Its
  original nucleotide path contains nine occurrences, six distinct positions
  and three repeated positions. Nucleotide ancestry is not relabeled as an
  amino-acid count.
* An external RNA reference keeps its actual ancestry without becoming an
  additional annotation target.

`FILLED_INTEGRATION_EXAMPLES_001.json` indexes ten actual completed operations
across eight publication cases, with exact native/grading artifact digests and
filled numerical values. These use explicitly synthetic input sequences and
real local operations; they are not biological discoveries or model-driven
scientific investigations.

## Executed verification

| Evidence | Result | Scope |
| --- | --- | --- |
| Translation workload 280, check002 | 67 passed | Native, missing/contradictory input, six frames, ambiguous and dual-coding codons, saved-data recalculation |
| Extraction workload 281, pytest_003 | 54 passed | DNA/RNA/protein, overlaps/repeats, reverse paths, original units, malformed input and saved-data recalculation |
| This workload, check003 | 93 passed, 9 failed | 102 tests; all 16 new publication/Workflow tests passed; nine pre-existing fixtures were obsolete |
| This workload, check004 | 8 passed | Corrected sequence-view regressions |
| Knowledge repair workload 283, check002 | 12 passed, 1 failed | All six knowledge and three recovery tests passed; the remaining root fixture still used the retired v2 commission |
| This workload, check005 | 4 passed | All root-boundary tests after correcting that fixture to the existing v3 commission |

This is not a claim that one rerun of all 102 tests passed. The original failed
results remain intact, and each corrected subgroup was rerun. The initial
publication failure in check001 exposed missing declared metric names; the
closed measurement schema was extended and check002 passed all 14 then-existing
integration cases. The later two coordinate/ownership cases passed in check003.

Seven obsolete sequence-view checks expected a number from the intentionally
retired categorical annotation scorer. They now check that no annotation is
created and that scoring is explicitly unavailable, rather than inventing zero.
Two knowledge fixtures expected tools at root. They now exercise the receiving
child and preserve exact durable records across recovery. One additional root
fixture used `scientific_process_selection_v2`; it now uses the existing v3
fields `evidence_axis`, `thought_pattern`, and `child_tool_info`. Production
root permissions and scoring behavior were not changed to make these pass.

All executions used the existing local_jobs binding, 20 GiB RAM, 4 GiB scratch
and no wall-time cap. Recorded source hashes remained stable within each run.
The two test files changed after check003 are covered by their later subgroup
runs. Full native/artifact retention, exact source correspondence, publication,
typed parent returns, replay and one observation per completed own action are
covered by the new integration cases. Pure recalculation tests prohibit native
execution, file/network access and installed-table lookup where applicable.

## Limits and remaining work

These two local transformation paths are verified under scripted decisions and
explicit engineering credit/controller fixtures. No configured-model scientific
run, API execution, HPC deployment, W05 annotation aggregation or literature
grading is claimed. An unavailable original map stays unavailable; the pure
grader does not authenticate a fabricated same-length source map on its own.
The host supplies and validates actual source custody. A formal global source
freeze is not claimed; the manifest records exact relevant file snapshots.

The original immutable objective, all sixteen design principles and the agreed
translation/extraction contract were reread before this handoff. The full fixed
308-row goal and its outstanding resource and communication work remain active.
