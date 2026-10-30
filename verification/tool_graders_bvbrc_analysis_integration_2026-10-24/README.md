# BV-BRC direct MinHash integration checkpoint

The fixed goal remains active. This checkpoint does not include the separate
specific NCBI BLAST job verification and does not establish live BV-BRC access.

Root executed the C1/C2/C3/transport component group: 242 tests passed in 1.26s
(`test_bvbrc_analysis_protocol.py`, `test_bvbrc_minhash_grader.py`,
`test_bvbrc_application_definitions.py`, `test_bvbrc_analysis_transport.py`).
Those counts comprise 79 protocol, 90 numerical MinHash, 55 application
preparation and 18 transport cases. The original command output is in this
conversation's execution record; this note is not a retrospectively created
JUnit report.

The service and views workers separately retained 77 and 117 passing cases.
Their verification directories preserve original logs and populated examples.
Seven selected-process cases establish both genome/FASTA modes through actual
four-field tool information, scientific child, launch/API, original retained
synthetic response, results sheet/calculator and requested return. Root receives
only counts when that is its requested form. These are scripted in-process
episodes with intercepted synthetic HTTP, not a model, live service or detached
subprocess demonstration.

Integration exposed and fixed three concrete defects:

1. The host passed an empty tuple where the pure projector required a list when
   no MinHash fields were requested. This also affected unrelated API services.
2. A scientific episode could not pass on an actually received result source
   referenced by a numerical return. The resolver now proves the exact original
   immediate-child return; source-only forwarding does not expand measurements.
3. Two results episodes acquiring the same original response shared a source ID,
   while a source lookup picked the first indexed episode. Own MinHash reads now
   explicitly select their actual results owner. Existing unqualified lookup
   behavior is unchanged. The second acquisition earns zero extra operational
   credit and makes no second RPC.

The first root regression run had 9 failures and 28 passes while using the
pre-fix empty-container implementation. All failures reported that exact
qualified_results_array error. After that correction, 37 checks passed in
154.46s; logs and JUnit are retained here. The owner selection and strict generic
JSON comparison changes occurred during that run: its before/after hashes
explicitly differ, so it is not evidence that those final changes were tested.

After those changes, a fresh root follow-up passed 8 recovery/received-BV-BRC
checks in 37.21s with unchanged source hashes. The separate fresh boundary
worker verified ten MinHash cases, including duplicate owners, exact admission
timing, forged contexts/receipts/artifacts, and close/reopen with no HTTP,
regrading, decisions or historical changes. Its own records state the two
fresh-process commands. Do not add overlapping regression counts as unique tests.

Example: the native-shaped synthetic row
`["83333.1","0.02","0.001","41/1000"]` retains native distance 0.02 and p-value
0.001, with sampled shared-hash fraction 0.041. Duplicate genome rows retain
their distinct original indices. Population size and truncation are unknown.
The production path does not supply actual k-mer/length/alphabet metadata, so
recomputed distance/p-value remain unavailable. The separate pure calculator's
explicit-metadata cases are verified without implying that production binding.

All 24 exact application definitions and their derived counterparts load from
an isolated built wheel with original hashes verified. This establishes package
data inclusion, not application submission, native result formats or deployment.

The 24 AppService applications still require selected execution, actual
definition/input/output custody, artifacts and their scientific graders. The
primitive transport/protocol/preparation modules are implemented and tested;
their existence is not a complete AppService integration. No evidence-axis,
annotation-score or model-prompt change is included here.
