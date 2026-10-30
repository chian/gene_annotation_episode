# Direct Minhash service and retained-result publication

This directory records C4b in
`docs/TOOL_GRADER_BVBRC_ANALYSIS_BATCH_2026-10-24_003.md`. It does not claim a
live service, authenticated deployment, acquired biological metadata, or a
complete Minhash capability. Root owns shared dispatch, tool-library bindings
and receiver-specific communication integration.

`BVBRCMinhashService` implements the existing APIServicePrimitive ports for
`bvbrc_minhash`. Both genome-ID and Workspace FASTA-path modes have exactly eight
explicit native arguments. The original assignment holds their values; action
arguments and result selector are empty closed objects. Native integer flags
remain integers, including source-permitted nonbinary values. No scientific
parameter defaults, trimming, sorting, duplicate elimination or metadata
inference occurs. A FASTA path has `/owner/workspace/object` syntax; this neither
opens a local file nor proves Workspace existence/access. C1 also permits UUIDs
and some non-normal paths, but this concrete assignment contract calls for a
path and C2 requires the stricter syntax. No native string is normalized.

The caller supplies the actual HTTP(S) Minhash endpoint and optional timeout,
authorization environment-variable name, and authorization origins. Constructor
validation runs with a supplied test client too. No credential discovery or
native request occurs during construction. The request correlation ID is
`minhash_rpc_` followed by the first 24 hexadecimal SHA-256 characters of the
canonical original assignment. It correlates the response; it provides no
remote idempotency guarantee.

Launch is one `BVBRCAnalysisClient.rpc` invocation, marked `mutates_remote=true`
to retain the conservative Workspace-access effect and unknown-call recovery
semantics. A result selection sets `cache_original=true`, so the executor
reuses the original response. Monitoring returns the original response fact
without calling Minhash again. There is no AppService task or native job handle.

The response boundary validates transport service `bvbrc_analysis`, RPC kind,
the exact native request, configured endpoint, complete body, retained sent-body
length/digest, successful HTTP status and the C1 native envelope/correlation.
Malformed outer results cannot establish a handoff. A successful native array
is an immediate completed response even if individual rows have parse errors.

Publication calls `publish_existing_acquisition` before the parser/calculator
callback. Its existing transaction and saved tool-operation receipt therefore
replay the original publication before regrading. It retains full response
bytes, exact sent RPC bytes verified against the transport digest, the complete
request/transport snapshot, one source with provider `bvbrc_minhash`, and one
auxiliary tool-grading artifact. Within the ordinary artifact wrapper, the exact
grading envelope is `{schema, request, rpc_request, selector, parse_status,
sheet, components, diagnostics}`, with schema `bvbrc_minhash_grading_v1` and
selector `{}`. `request` is the assignment; `rpc_request` and `sheet.request`
are the full C1 `{version, method, params, id}` object. `diagnostics` preserves
the original C2 parse diagnostics; calculation diagnostics remain in
`components`. No numerical output is rewritten on replay.

C2 is called without `pair_metadata`. Native distance/p-value and the sampled
shared-hash fraction are retained, while recomputed distance/p-value remain
null with missing-metadata diagnostics. This intentionally leaves production
k/length/alphabet acquisition and binding unfinished. Missing metadata does not
make a correctly parsed native acquisition fail. Partial/invalid native rows
produce a partial publication with full original rows and `projection_errors`.
An empty valid array completes acquisition and keeps completeness unknown.

Verification commands:

```sh
.venv/bin/python -m pytest -q tests/test_api_bvbrc_minhash.py
.venv/bin/python verification/tool_graders_bvbrc_minhash_service_2026-10-24/verify_offline.py
```

The suite tests both modes, strict assignment/configuration, exact argument
order, empty selectors, wrong native requests/envelopes/status, incomplete
bodies, retained malformed rows, duplicates, empty arrays, zero denominators,
publication replay and conservative unknown-call recovery. Two controlled
localhost HTTP cases use the real urllib transport. Executor tests run actual
APIServiceExecution selected-action custody and recovery with direct test
binding of this service; they do not establish root-owned production dispatch
or a model-directed episode path. Recovery after committed publication fails
the test if either scientific parser/calculator is called again.

The focused suite passed **76 tests in 191.49 seconds**, recorded in
`pytest_service.txt`. The subsequently added producer-to-projector test passed
**1 test in 4.57 seconds**, recorded in `pytest_projection_interop.txt`: 77
distinct cases are verified across these two invocations. This latter test
reads the actual saved publication and verifies requested-only count/match
outputs, duplicate IDs, malformed cells and no regrading. The initial run had
58 passes and 18 failures caused by test assertions overlooking the input
source created by `Store.create_problem`; correcting those baseline-count
assertions required no service change. The offline script completed all six
examples with zero live HTTP calls and zero annotation observations.

The offline examples use the retained upstream Mash row
`genome1.fna reads 0.12101 4.48626e-214 41/1000` inside explicitly synthetic
BV-BRC envelopes. Its sampled shared fraction is `41/1000 = 0.041`; native
distance is `0.12101` and p-value is `4.48626e-214`. No BV-BRC execution is
claimed for these values. A synthetic valid row with `2/3` beside a malformed
distance retains fraction `0.6666666666666666` and null parsed distance.
The zero-denominator row preserves reported distance `0`, reported p-value `1`
and counts `0/0`, with all derived quantities null. Examples retain all rows
even when their count exceeds the selected `max_hits`.

Inspected paths include the immutable full goal and all sixteen principles,
AGENTS.md, GOAL.md, episode/time/practical direction, contracts 001/002/003,
APIServicePrimitive, the complete APIServiceExecution implementation, existing
publication/replay and artifact storage paths, C1 protocol, C2 grader, C4a
transport, the relevant fixed status row, retained Minhash spec and both full
native mode implementations/client methods/service dispatch, and the complete
native `minhash-search.pl`. The authoritative objective and sixteen principles
were reread after the native source study and before handoff. No permanent
historical direction or accounting file is edited here.
