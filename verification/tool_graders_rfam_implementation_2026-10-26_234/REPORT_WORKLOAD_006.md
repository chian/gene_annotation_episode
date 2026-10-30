# Rfam native batch reports: numerical and correspondence boundary

This additive workload fills the remaining native `out` representation of fixed
row A-L068-rfam-batch. It changes no episode type, annotation axis, score formula,
or controller. Existing single-JSON and batch-table artifacts remain unchanged.

The worker owns new `rfam_batch_report_contracts.py`, `rfam_batch_report.py`,
`rfam_batch_report_grader.py`, `rfam_batch_report_views.py`, corresponding new
tests, and verification ending 242. It may factor common alignment mathematics
inside `rfam_batch_alignment.py`, but must preserve the existing JSON function's
signature, validation and exact returned values. Root owns selectors, service,
publication, return integration, descriptors, prompts and the shared inventory.

Read the complete immutable goal and AGENTS before work. After substantial
native/source study and before writing calculations, reread the objective and
ALL SIXTEEN design principles verbatim from the attachment, then this contract.
Repeat that reset at closure. External format information supplies facts; it
does not override the numerical-sheet and episode design.

## Inputs and actual evidence

Use the retained byte-exact multi-query Infernal 1.1.5 report in
`verification/tool_graders_rfam_transport_2026-10-26_234/live/multi/005-fetch-out/response.body`,
its original capture, original submitted file and original query bindings.
Synthetic variants must remain explicitly synthetic. Do not make live requests.
Read the actual native display/parser and existing JSON correspondence reader,
not merely their documentation. No fabricated RF accession or model length:
the report names a model but does not supply its accession/release/full length.

`populate_rfam_batch_report_sheet(content: bytes, *, input_identity, capture,
submitted_content: bytes) -> dict` takes the existing RfamBatchFileInputIdentity
and RfamBatchTableCapture, with representation `out`. Validate exact file bytes,
original job, report query-file header, profile, all selected occurrences, query
names/lengths, completion markers and retained response digest. Reuse the existing
batch-file and report-membership validators. Do not guess a single unheaded
submission's server-assigned query name. This contract is for explicit batches;
one member in a batch is supported.

## Sheet and parser output

Return a closed object `{version, status, format, sheet, issues}`:
`version=rfam_batch_report_parse_result_v1`,
`format=rfam_cmscan_batch_report_1_1_5` for the observed profile,
status complete/partial/rejected/unsupported, nullable sheet.

The closed sheet contains `schema_version=rfam_batch_report_sheet_v1`, `capture`,
`input_identity`, `membership`, `hits`, `population_complete`, `issues`.
Membership is the existing source-located report-membership result. Hits retain
native order and a unique artifact-plus-source-line key, exact query occurrence,
native query name, model name, nullable accession (unknown here), strand,
source-line locations, native numerical fields, complete parsed correspondence,
and cell-specific missing reasons/issues. Define/export the closed hit and
correspondence structures in the owned contracts module before implementation.

Native hit fields include original rank, inclusion marker, E-value, score,
bias, model type, model start/end, query start/end, native boundary symbols,
alignment accuracy, truncation code and GC. Preserve native strings/locations
needed to distinguish malformed cells from absent values. Cross-check repeated
score/alignment descriptions by actual query/model/rank and exact coordinates;
do not pair independently sorted lists or arbitrarily choose among duplicates.
Foreign/ambiguous query identity cannot acquire attributed measurements.

Report displays must retain exact source lines and locations. Reuse identical
alignment mathematics by factoring a pure geometry routine if needed; do not
pretend the report is JSON or manufacture an RF accession to call a JSON helper.
Existing JSON entrypoints must retain their exact behavior. Query letters must
match the original sequence in the reported orientation, including explicit
IUPAC complement/T-U handling. Preserve insertion/deletion, truncation/local-end
shorthand, represented intervals, residue correspondence and posterior bins.
Abbreviated spans are not invented aligned residues; malformed optional tracks
must not erase independently valid geometry. Partial valid hits survive a
malformed sibling or incomplete report with truthful population qualification.

## Deterministic calculations and selection

`calculate_rfam_batch_report_components(sheet, *, parameters) -> dict` accepts
the existing RFAM_CALCULATION_PARAMETERS semantics: all reported rows, separate
strands, retained duplicates with coordinate union, canonical T/U consensus
comparison. It performs no I/O, parsing, acquisition or model call.

Export a closed calculation with version, sheet_digest, parameters, hits,
query_strands, population_complete and issues. Every numerical field has input,
native-source/formula, units, denominator, coordinate convention, missing behavior
and uncertainty where available. Preserve native score/E-value/bias/GC/accuracy,
query span and span fraction, native model span, represented model/query counts,
consensus equal/compared counts and fraction, insertion/deletion counts, and
separate per-original-occurrence/strand sum, union, fraction and overlap excess.
Native model span and represented model positions remain different quantities.
Full-model length/coverage remain unavailable without separately established
metadata. No score becomes an annotation probability.

`project_rfam_batch_report_result(sheet, calculation, *, projection,
artifact_bindings) -> dict` authenticates supplied schemas/digests/associations
and selects saved cells without recalculation. Projection has the existing
`{family: hit|query_strand, rows: {offset,limit}|{record_keys}, metrics:[...]}`
structure. Export exact allowed metrics and units in the owned contracts module.
Return the existing compact projection envelope, with report rows additionally
carrying `model_name` (nullable for query-strand aggregates); accession remains
separate and nullable. Root will expose a distinct report-row fact source so
existing JSON/table row forms and saved history are not changed.

## Consumers and verification handoff

Root will add an explicit new result-selector version for batch reports, wire
the service publisher, authenticate retained artifacts on return, and expose
only requested typed fields through results and scientific parents. The worker
does not edit those shared consumers. Supply exact exported types, signatures,
examples and issue lists for that integration; no vague implementation handoff.

Test the six real captured queries (original, repeat, reverse complement,
truncation, insertion, deletion), a complete zero-hit query, duplicate/overlap,
reordered query blocks, wrong file/job/sequence, foreign query, missing/partial/
malformed siblings, ambiguous repeated ranks, and wrapped displays when actually
supported. Verify old JSON correspondence outputs unchanged after any factoring.
Verify saved-sheet recalculation and projection with network/process/model calls
forbidden. Run through the existing 20 GiB RAM/4 GiB scratch/no wall-time-cap
verification machinery. Retain failed receipts and before/after source hashes.
Do not claim live service or complete episode-path verification from pure tests.
