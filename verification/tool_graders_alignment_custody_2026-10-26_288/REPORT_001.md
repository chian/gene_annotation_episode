# Selected-site host boundary verification

This record describes tests written by workload 288. It does not change the
fixed goal, numerical contract, production implementation, annotation credit,
literature work or completion accounting.

Owned files are `tests/test_alignment_site_action_records.py` and this
verification directory. Production corrections belong to root.

## Executed checks

All pytest runs use the existing `local_jobs.run_local_job`, the checkout's
`.venv/bin/python`, 20 GiB RAM, 4 GiB scratch and no wall-time cap. Complete
stdout, stderr, JUnit, intent, resource metadata and before/after source hashes
are retained in each numbered directory.

| Run | Result | Meaning |
| --- | --- | --- |
| run_001 | 34 passed, 13 failed; 115.82 s | All thirteen failures trace to the host port passing frozen `context.scope` into `_original_hsp`, whose scope validator requires plain dict/list JSON. Root corrected that call to `plain(context.scope)`. Tested source hashes did not change. |
| run_002 | 61 passed; 95.24 s | The original cases plus native minimap2 quality/geometry tests all passed. Tested source hashes did not change. |
| run_003 | 2 failed; 10.30 s | Additional same-length source-reassignment counterexamples both exposed a real missing original-source/operand binding. A fresh valid alignment observation reusing the original Biopython source was accepted after substituting either operand. Tested source hashes did not change. Root was notified; these cases remain failures at this checkpoint. |

`run_002` is the passing evidence for its 61 tests, not evidence that the two
subsequently added source-reassignment cases passed. The current suite contains
63 cases. Later corrections and verification must be recorded separately.

## Boundary exercised

Tests use actual `ToolRegistry` operations and their actual retained artifacts,
with real `Store`, `Journal`, `BindingContext`, `EpisodeReceipts`, and
`AlignmentSiteActionRecords` instances. Journal fixtures explicitly save the
selected own action and original assignment. They do not simulate a complete
model-driven or scripted `Workflow` commission, parent admission or yield
controller. Those checks remain root's integration responsibility.

Two tiny Biopython pairwise alignments are run once per test invocation. One
actual `reads.map` operation supplies native forward and reverse minimap2
placements in run_002. Closed fixture Stores are copied for independent cases,
so test isolation does not repeat native mapping. The BLAST fixture is an
explicit offline synthetic native response passed through the actual API
publication code. No NCBI request, new remote BLAST, API deployment or HPC
execution is claimed.

Verified cases include:

- Complete unique position-set selection before hydration and pagination,
  preserving actual request order and duplicate rows without duplicate numerical
  population counts.
- Explicit all-own, matching-alignment and matching-window policies, with
  unrelated own and sibling operations excluded.
- Original episode/path/request/scope ownership, integer pagination, and refusal
  of a broadened selector or an unrequested result source.
- Exact durable operation name, arguments, scope and identity; a missing saved
  operation fails rather than disappearing. Runtime-only pending-work metadata
  is accepted; changing an integer result to a boolean fails.
- BLAST receipt authority from original/decision-input/own-action/child-return
  receipts, including action-index ordering and frozen parent-prefix limits.
  Context-provided handles cannot replace the authoritative receipt ledger.
- Wrong BLAST native HSP ordinal, requested window, native body, same-length
  reference identity, original mapping and alignment unit are rejected.
- Real empty BLAST windows, explicit retained grading failure, missing native
  strings and simulated older reads without grading remain distinct.
- Native minimap2 forward/reverse coordinates and original member quality;
  changed quality, quality encoding, sequence, length, parsed PAF, preset,
  native version, locator or alignment unit are rejected.
- Frozen facts preserve absent closure versus absent source versus actual empty
  arrays. They reject non-array sources, omit unrequested sources and remain
  unchanged after later actions. Frozen validation reads no native artifacts
  and reruns no scientific grader.

## Retained numerical examples

`FILLED_EXAMPLES_001.json` copies seven complete saved grading envelopes and
their selected actions/outcomes from closed run_002 Stores. The extractor
`save_examples.py` only reads those Stores and verifies retained artifact hashes;
it does no regrading. File SHA-256:
`134601eb34dd39ccf7ce1e9546e0162f9527b7dee7b3c39c9bad128b377a1fd9`.

| Example | Actual saved values |
| --- | --- |
| Pairwise positions `[2,0,2]` | Three requested rows, two unique positions, two paired and identical positions; identity 2/2. |
| BLAST four-column reverse window | Two identical paired columns, one query-gap and one reference-gap column; alignment identity 2/4; query coverage 2/12 and reference coverage 2/18. |
| Minimap2 positions `[2099,2100,3600]` | Two paired identical positions, one query gap, three inserted query positions; paired identity 2/2, selected alignment identity 2/6; insertion quality `III`, encoding unspecified. |
| Reverse minimap2 positions `[500,5499]` | Query positions `[4999,0]`, quality characters `?`, encoding unspecified, therefore no invented numerical quality score. |
| Explicit grader failure | Sheet and score are null; original `site_native_geometry_conflict` code retained. |
| Actual empty BLAST terminal window | Zero paired columns and zero coverage; identity remains null because its denominator is zero. |
| Simulated older BLAST read | No grading pointer and no grading; returned as unavailable legacy data, never recalculated during closure. |

The immutable objective and all sixteen design principles were read in full
before coding and reread verbatim after the native/retained-result examination.
Permanent requirements and previously retained failures were not modified.
