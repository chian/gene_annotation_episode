# API results, failures and timing

The `results` episode receives `execution_results_assignment_v1` with the
original `handoff_ref` and `selector` containing positive `page` and optional
`page_size`. Its `api.hmmer.result` action takes empty arguments: it cannot
change the job or substitute a different requested page. Another page can be
requested through another explicitly commissioned results assignment.

A successful result must contain a usable non-null result object and agree
with the saved UUID, algorithm, database and input identity where reported.
The implementation retains raw response bytes, request/transport provenance,
pagination, native statistics, accessions, scores, E-values and domain
coordinates. Valid partial publication survives a later failure. Malformed
responses, identity conflicts, not-ready results, provider failure and uncertain
submission remain distinct outcomes available for repair.

A completed page is not every page. `hmmscan` hits are profiles/families;
`phmmer` hits are reference proteins. Acquisition does not assign function or
lineage, and a no-hit page does not establish biological absence. The scientific
parent receives typed references and interprets the actual retained records.

Replay returns the original saved outcome without another HTTP request. Repeated
information does not manufacture credit. Complete acquisition of the requested
page establishes the results endpoint and immediately gives exact zero future
expected credit, preserving the final actual gain.

Provider-reported search time, HTTP time, queue wait and total turnaround are
different quantities. Use only measured intervals and keep unknowns unknown.
Monitoring records are separate from closed launch receipts and histories.
Instruction retrieval itself is neither a timing sample nor scientific evidence.

The historical service schema and database observations are documented in
source rows S2–S6 of the launch instruction source record. They do not establish
present service availability. Wiring verification uses controlled HTTP responses;
it does not establish a live configured-model API run.
