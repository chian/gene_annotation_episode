# Workload 289 — alignment-site Workflow verification

This workload owns `tests/test_alignment_site_workflow.py` and this verification
directory. It changes no production code, annotation-credit formula, evidence
axis, episode role or permanent direction record.

## What the tests exercise

Parents explicitly select `scientific_process` children with A101, P01 and the
actual requested `child_tool_info` entries. Root has no direct execution tools.
The child executes `sequence.align` / `reads.map` followed by `sequence.sites`,
or executes `result.blast.hsp` on a result first acquired by a selected results
episode and received by its parent. No observation is preloaded into
`initial_known_record_refs`.

The tests use the actual Workflow, ScientificProcessEpisodes execution, retained
tool operation, grading artifact, requested fact-source projection, frozen
closure and immediate typed receiving boundary. Parent schemas explicitly
select `all_own_completed_results` or `matching_alignment_window`; they request
selected rows/components rather than the internal sheet or raw result.

Scripted choices and zero scientific credit are verification fixtures, not
claims about model reasoning or annotation quality. Test-only controller
factories end the assigned fixture after its explicitly selected work. No
production stopping behavior is introduced. Practical API/results episodes use
their existing endpoint behavior.

## Numerical examples and distinctions

- Actual local Biopython DNA/RNA/protein: requested positions `[2,0,2]` remain
  three ordered rows, but two unique positions determine the paired count.
  Identity is `2/2`, query coverage is `2/8`, and duplicate count is one.
- Actual local Biopython local no-alignment: four requested positions are
  outside the alignment. Paired count is zero, identity is undefined (`0/0`),
  and query coverage is measured zero (`0/4`).
- Injected pure grading-input failure: retained completed action is partial;
  unavailable rows/components are null and have explicit failure codes.
- Synthetic BLAST protocol window: columns 2–5 contain four paired positions,
  three identical pairs and one substitution: identity `3/4`, coverage `4/8`.
  A real empty terminal page returns `[]` and zero counts; absent alignment
  strings return null rows/counts instead.
- Actual retained NCBI second HSP: 86 columns, 71 paired positions, 31 identical
  pairs and 40 substitutions. Identity is `31/71`; query coverage is `71/253`.
  The seven original native hits/HSPs remain unchanged. The offline protocol
  fixture changes only the query-title field to this test's actual Store input
  identity. Its submission is a fixture; it does not claim admission of the
  historical RID or a new remote submission. Original archive and query bytes
  are included in before/after hashes.
- Actual local minimap2 `map-ont`: selected forward positions map to query
  positions `[1999,2003,null]`, with two paired sites, one query gap and one
  three-base insertion at boundary 2100. Alignment identity including that gap
  and insertion is `2/6`. Reverse positions map to `[4999,0]`; original symbols
  and original-coordinate intervals remain distinct from aligned orientation.
  Original quality characters are `I`/`?`; the unspecified encoding leaves
  numeric quality null. Both the insertion's `GGG`/`III` and its source interval
  `[2000,2003]` reach the explicitly requested parent fields.

Biopython creates two child own actions and one parent commission. The minimap2
case creates three child own actions and one parent commission. The BLAST chain
creates three root commissions and one selected HSP-reader action in the final
scientific child. Parsing, grading, closure and redelivery add no own actions.

## Replay and communication checks

Saved operation replay, duplicate typed receipt and ordinary report redelivery
must leave records, operations, runtime actions, observations and receipt rows
unchanged. Frozen return validation and redelivery run with live site-source
reads and the numerical calculator replaced by exceptions; they therefore
cannot silently recalculate or reconstruct a closed report from live actions.
An altered selected reference position is rejected.

When the parent requests no site fact source, no site-source host port is
called. When it requests sites but the child executes only sequence inspection,
the exact return is an empty group array rather than invented site measurements.

## Execution records

Every test invocation uses `run_local_job`, `.venv/bin/python`, 20 GiB RAM,
4 GiB scratch and no wall-time cap. Each check retains intent, before/after
source hashes, resource receipt, stdout/stderr, JUnit results, temporary stores
and filled admitted examples.

- `check001`: 7 passed, 3 failed. All failures were in this workload's fixture:
  it supplied mutually exclusive direct descriptors and a service factory.
  This was corrected by composing the actual application services in one
  test factory. The run also crossed changes to three shared production files.
- `check002`: 10 passed, 1 failed. The failing BLAST empty-window construction
  crossed a shared production change and correctly rejected a saved/live
  scientific binding hash mismatch. Actual minimap2 and frozen redelivery
  cases passed. All results are retained; this run is not final stable evidence.
- `check003`: **12 passed in 200.20 seconds**, exit 0, `changed_sources=[]`.
  This final run covers every case above against unchanged source files. Ten
  filled admitted examples are retained in `check003/examples/`; the two
  no-site-source tests assert their exact empty/unrequested results directly.

There is no live API request, new database BLAST, HPC execution or configured
LLM scientific decision in this verification. Literature and W05 remain outside
the workload.
