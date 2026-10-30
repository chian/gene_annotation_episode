# One live Rfam batch through the composed Workflow

The bounded live run completed with exit 0. It submitted exactly one new public
three-member batch, acquired the original job's table, delivered the requested
numerical facts through both scientific return boundaries, and replayed the
completed Workflow without network, parser, calculator or model calls.

The preserved native job is
`infernal_cmscan-R20261026-041949-0621-14761545-p2m`, at
<https://batch.rfam.org/result/infernal_cmscan-R20261026-041949-0621-14761545-p2m>.
No replacement submission or live rerun occurred.

The existing shared `method_loop` and actual `Workflow` ran annotation →
scientific_process → launch → launch_api. The scientific process then separately
commissioned results for the original handoff. Its three slots were the retained
A101 evidence-axis entry, P01 thought-pattern entry, and the actual selected
`api.rfam.submit`, `api.rfam.status`, `api.rfam.fetch` information. The actual
execution-family factory constructed `RfamBatchHTTP(timeout_seconds=90)`;
the transport and publication/admission implementations were not mocked.

This is engineering verification with scripted episode decisions, caller-owned
root/scientific continuation estimates and a zero root/scientific credit
projector. It establishes actual execution-role operational credit, not a
scientific credit formula or configured-model investigation. No W05 or
literature implementation changed. No production or shared test was edited by
this worker.

## Actual numerical example

Only the retained official public 119 nt input was used. Normal supplied FASTA
records contain the original and its DNA reverse complement; request v2 selects
the original subject twice, followed by the reverse subject. The generated
423-byte submitted FASTA has three unique native query names. Both repeated
selections retain the same original subject and distinct selection ordinals and
query occurrence keys. A repeat is not represented as independent evidence.

| Selected occurrence | Native name | Family | Strand | Native endpoints, 1-based inclusive | Query length | Span | Span fraction | Bits | E-value |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Original | rfam_query_00000000 | RF00001 | + | 1..119 | 119 | 119 | 1 | 104.6 | 1.4e-24 |
| Same original selected again | rfam_query_00000001 | RF00001 | + | 1..119 | 119 | 119 | 1 | 104.6 | 1.4e-24 |
| Reverse complement | rfam_query_00000002 | RF00001 | − | 119..1 | 119 | 119 | 1 | 104.6 | 1.4e-24 |

Score and E-value are native tool measurements. Query length comes from each
original submitted occurrence. Query span is `abs(end-start)+1`; its denominator
is the explicit submitted length, giving `119/119 = 1`. These values are not an
annotation-correctness probability. Full-model coverage is unavailable for all
three rows, with `model_length_unavailable`; native model coordinates 1..120 do
not provide a verified full-model length.

The observed native format is cmscan 1.1.5, table format 1, SCAN, with the original
job filename and terminal `# [ok]`. The complete 1,540-byte table is retained.
The Infernal sheet and wrapper parse have partial status solely because the
sheet reports three `length_denominator_missing` warnings for models. The
reported population is complete: three available rows, three requested rows,
`more_rows=false`, and one reported hit for each original selected occurrence.
Unavailable model coverage did not block practical completion.

The result return includes only `measurements`, `populations`, and the requested
operational `completed` boolean. The scientific return forwards the identical
measurements and populations; full sheets and native reports do not enter these
forms. Both actual saved admissions authenticate these values to their original
selected operations, sources, query occurrences, and numerical artifacts.

## Actions, credit, continuation and replay

Exactly three HTTP requests occurred, each retaining its wire request, full
response, original timestamps and native transport diagnostics. They were one
POST submission, one selected GET status returning `FINISHED`, and one selected
GET of `tblout`. There were no retries, redirects, polling loops, waits or
operator follow-up selections in this actual run. The harness's optional
operator-choice socket was never opened.

| Episode | Completed own actions | Actual operational gains | Observations |
| --- | --- | --- | ---: |
| annotation | Commission scientific_process | Fixture 0 | 1 |
| scientific_process | Commission launch; commission results | Fixture 0, 0 | 2 |
| launch | Commission launch_api | 3 | 1 |
| launch_api | api.rfam.submit | 3 | 1 |
| results | api.rfam.status; api.rfam.fetch | 0, 2 | 2 |

The seven actual completed own actions have seven saved decisions and seven
local observations. Five episodes and four original forms/admissions are
retained. The production completion proofs validate the original launch/API
handoffs and selected result acquisition. Each execution role's future expected
gain becomes exact zero immediately at its final successful action, preserving
the gains above and adding no terminal zero action or report-composition call.
The submission, native result and grading source count as one acquired result.
No annotation or scientific observation record was manufactured.

Saved calculation was recomputed with sockets forbidden and matched exactly.
Then a fresh Store, ToolRegistry, Workflow and execution binding reopened this
same completed run. Socket and real transport entry points, native table parsers,
score calculators and model completion were forbidden. Full archive and all six
history tables stayed equal, including forms, admissions, action outcomes and
completed observations. Each original API action also replayed its saved
outcome. No network call, parse, calculation or model completion happened during
that replay.

## Resource and source qualifications

The existing native runner enforced 20 GiB RAM with a cgroup, no swap, 4 GiB
scratch monitoring and per-file size limit, and no wall-time cap. All live run
files were under its monitored `live_001` cwd. Its successful receipt measured
24.886119286 seconds of local systemd service wall time and 12,275,712 allocated
scratch bytes. This duration includes the local client and verification; it is
not a remote computation or queue-time measurement. Scratch monitoring retains
the existing possible-overshoot qualification.

**The run is not an exact final-source pin.** Root concurrently changed the
imported `gene_annotation_episode/rfam_batch_publication.py`:

- Before: `643e3cc8763c33ec165d7536282f1f207e081cb0403fef4c0cb1be3021b0deb8`
- After: `ff13d94e1d9503ed2f55515e062ba9426f36f996e12bb641d07c8f29641227aa`

All other monitored source hashes were unchanged. The exact publisher bytes
loaded by the live Python process cannot be established from these before/after
hashes. `loaded-source-hashes.json` hashes files associated with loaded modules
at closure; it does not fingerprint already imported code objects. Root reports
that the concurrent extension adds table metrics and native-report support,
while preserving this selected v2 projection. That report is explanatory
context, not proof of the exact live source version. The actual live artifacts,
typed returns and replay remain retained facts. Final-source integration/replay
belongs to root; this worker does not resubmit for a source-pin refresh.

This run does not establish configured-model scientific choices, production
scientific credit, independent detached worker execution/recovery, timeout or
pending-state behavior, live zero-hit behavior, native report projection, full
model-length provenance, broad malformed-data behavior, or HPC execution.
Those limits do not erase the verified live submission, numerical publication,
operational continuation and original typed returns.

## Evidence handoff

`run_bounded.py` and `run_live.py` are the only new verification code. `live_001`
retains the native lifecycle receipt, before/after hashes, Store, original input
and submitted bytes, original handle, exact HTTP snapshots, complete native
result, parse/sheet/calculation, requested forms, saved returns/admissions,
scripted choices, action/observation histories, archived episodes, and replay
verification. `SUMMARY.json` contains the compact numerical values and original
associations. `CONTEXT_RESET.json` records the immutable authority and contract
identities read after source/native study and at closure.

The original objective and all sixteen principles were reread verbatim after
source/native examination and at closure, followed by LIVE_WORKLOAD_007.md.
