# BLAST grader verification — 2026-10-24 checkpoint

## Implemented

The B01–B04 functions and the public `grade_blast_result` entrypoint are in the
application package. Native/source readers, both internal scoring sheets,
deterministic component calculators and the replaceable database calculation
are implemented. No scientific episode, resource-selection logic, model prompt,
existing annotation-credit formula or W05 aggregation was changed.

The actual two-sequence BLAST+ 2.17.0 invocation is recorded in
`native_pair/execution.json`; `run_native_pair.py` reproduces it. Official
binary source and verified checksum are in `blast_download.json`. The input
is the fixed public case sequence and an explicitly synthetic deletion/mutation
derivative. This is a real pairwise tool execution, not a database search.

Results: 253 alignment columns, 243 paired residues, 238 identical pairs, 10 gap
columns, query coverage 243/253 = .9604743083, reference coverage 1, paired
identity 238/243 = .9794238683, bit score 486.878 and raw score 1252. Native JSON
and tabular parsing agree on counts/coordinates; tabular bit-score rounding is
preserved. Both native formats are retained in test fixtures with provenance.

`synthetic_database` contains explicitly synthetic API and HPC-format native
inputs, metadata, database census, filled sheets and recalculated outputs.
`write_examples.py` regenerates them. Three sequence-group scores 10/F, 9/G,
10/F produce .8/.2 without representation adjustment and .5/.5 with sequence
counts F=200/G=50. Changing temperature to 2 using the saved sheet produces
.4142135624/.5857864376 after adjustment, without extraction or execution.
Taxonomic matching is 2/3 groups; same-species pair count is 1/3 comparable
pairs. Actual source-quality values and their denominators/methods are retained.
These synthetic probability figures are arithmetic demonstrations, not measured
annotation accuracy or fitted calibration.

Integration testing identified and repaired a real join defect: source quality
from a separately acquired assembly record was omitted from its reference's
function-specific numerical summary. The correction joins only the same native
descriptor with compatible taxonomy; a different alias/function does not inherit
that quality record. Separate tests cover unknown and independently ordered
tabular metadata, duplicate aliases, actual full-sequence groups, conflicting
identity, incomplete geometry, empty/missing results and parameter recalculation.

## Test evidence

Latest new-module invocation after preserving standard-tabular percent identity:

```
.venv/bin/python -m pytest -q tests/test_blast_grading_inputs.py \
 tests/test_blast_pairwise_grader.py tests/test_blast_database_grader.py \
 tests/test_blast_reference_metadata.py tests/test_blast_graders_integration.py
```

**120 passed in 0.36s.** Immediately preceding that small additive parser/
calculator change, the same suites plus `test_blast_result_views.py` and
`test_api_blast_service.py` passed **130 tests in 14.80s**. No full-project test
suite pass is claimed. The newest added case supplies standard 12-column
tabular output and verifies that reported 83.33% identity survives numerically
while exact identity count, residue correspondence and paired coverage remain
unknown.

## Live API test still pending at this checkpoint

Precision correction: the NCBI native `WAITING` status does not distinguish a
queued job from a running search. Earlier progress wording saying "queued"
described unreturned work but did not establish measured queue time. Saved
HTTP Date headers advanced with the observations, so those observations were
not simply replaying the first cached WAITING response.

Submitted one public `blastp` search of the 253-aa case sequence against
`swissprot`, requested hit list 50, using the repository's existing single-
request client and installed NCBI BLAST skill. The submission and each status
receipt are retained under `live_api`. RID: **DTKE1D4G016**. Submission time:
2026-10-24 15:24:49 UTC. Latest saved status at this checkpoint is **WAITING**
(`status_009.body`). This is not a completed live API grading demonstration.
No second query, automatic retry, local database search or HPC job was run.

Fresh UniProt metadata for P0AAW1 and NCBI target taxonomy 511145 were retrieved
and parsed; they are under `live_metadata`. The UniProt entry has no explicit
EC assignment, so its name was not converted into a fabricated function. Once
the BLAST job is READY, fetch its native JSON2 once, populate the common database
sheet, acquire only the metadata explicitly required for the test, and record
what remains unavailable. Actual database function-population counts are not
currently supplied for that public database: do not invent representation
adjustment. Keep the goal active until this live test is collected and reported.
The one-operation `observe_live_api.py status` / `fetch` helper can observe the
existing RID through the same client. It never resubmits or runs a polling loop.

HPC JSON/tabular parser coverage is tested with recorded-format/synthetic
fixtures. HPC scheduler submission, environment setup and credentials were not
tested by this grader work. Local database execution was not used.

The initial probability model explicitly does not yet weight taxonomy, source
quality, annotation evidence codes, coverage, identity or shared-study data.
Those data/components are retained and calculated for later model changes.
Missing metadata, database representation and uncaptured reference functions
remain unknown rather than numerical zero or invented source-quality grades.

## Final local verification checkpoint

After the standard-tabular percentage change, the five new suites plus
`tests/test_blast_result_views.py` and `tests/test_api_blast_service.py` were run
together again: **131 passed in 14.41s**. Exact output is `pytest-final.txt`.
This supersedes the earlier 130-check combined checkpoint for the current code.
The goal remains active for collection and grading of the existing live API
search; no new job or HPC execution is implied by these passing tests.

## External-result blocker — 2026-10-24 16:11 UTC

The live result remained unavailable across three consecutive continuation
turns. Both the latest status request and a direct result request returned
WAITING. The direct fetch receipt is retained as
`live_api/fetch_pending_20261024T160713Z.body`, not a completed native result.
All independent goal work is finished; the remaining live test needs NCBI to
make this job's output available. The goal is therefore recorded as blocked,
superseding the active-status instructions at the earlier checkpoints without
claiming completion. The original RID remains intact and B05 remains open.
