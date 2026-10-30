The new composed report verification passed all 18 checks in `tests_002`
(121.62 seconds pytest; 122.84 seconds monitored service wall time). Every
tracked source hash was unchanged between that run's start and finish. The
owned test is `tests/test_rfam_report_composed_workflow.py`. No production,
existing-test or inventory file was edited by worker245.

The one authorized live format acquisition is separate evidence. The actual
`RfamBatchHTTP(timeout_seconds=90).result(original_job, representation="out")`
performed exactly one GET for
`infernal_cmscan-R20261026-041949-0621-14761545-p2m`. It returned HTTP 200 with a
complete 9,760-byte response, SHA256
`c0b73fb36c2e679b57888fb1ecc0dec734b13ba834ab588d2c482dd4ed084f16`.
`original_job_out_001` retains the complete body, SourceSnapshot fields and
base64 body, exact HTTP request, transport metadata, command and resource
receipt. No POST, new job, retry or polling request was made. This acquisition
is not a new live composed Workflow.

The controlled Workflow uses that exact native report and the original243
submission/status snapshots, multipart HTTP request bytes, supplied FASTA and
423-byte submitted FASTA with the three original generated query names.
Original snapshots remain unchanged. The transport fixture removes only the
old host `input_operand` so the production service rebuilds it from the current
Store; wire requests, response bytes, query names and sequences remain intact.
The empty/truncated report bodies are explicitly synthetic and have separate
synthetic transport metadata rather than copied live response lengths.

| Controlled case | Requested return | Complete internal data |
| --- | --- | --- |
| Retained original report | Occurrences 1 and 2: repeat on `+`, reverse complement on `-`; two selected rows from three, `more_rows=true` | All three native rows and displays, original input occurrences, full sheet and calculation |
| Synthetic complete zero | Empty hit list; available/selected counts 0; population complete; `completed=true` | Six occurrence/strand aggregates with observed zero row counts and zero unions |
| Synthetic truncated prefix | One selected valid row from two retained rows; population incomplete; `completed=false` | Exact original prefix through the second query; third occurrence absent; missing strand populations stay unknown |

Each selected native row preserves `model_name=5S_rRNA` in the `rfam_model`
identifier namespace and nullable RF accession. Values are 104.6 bits,
E-value 1.4e-24, bias 0 bits, query span 119 nt, native model span 120 positions,
represented model/query positions 120/119, consensus comparisons/equalities 118/75,
one query insertion and two model deletions. Full model length and model
coverage stay unavailable. A model endpoint 120 is not used as a full-model
denominator. The reverse-complement row preserves native query endpoints 119→1.

The actual Workflow constructs the scientific episode from A101 evidence-axis
information, P01 thought-pattern information and the selected Rfam submit,
status and fetch tool information. The scientific episode commissions launch;
launch commissions its API child; the API child selects submission. The
scientific episode separately commissions results with v2 `sequence_batch`
request and explicit v3 `out` selector. Results selects acquisition. Production
source custody, native parser, sheet, deterministic calculator, requested
projection and immediate-parent admission carry `rfam_report_rows` and
`rfam_result_populations` through results→scientific_process→annotation.
No Rfam execution operation is restored to annotation or scientific_process.

Both forms are closed, preserve the exact selected query/model/metric
associations, and contain no raw report, full sheet or unrequested calculated
metrics. Recurring substantive task instructions are present in rendered TASK;
raw report/sheet content is absent from scientific STEERING. Report-only fields
do not enter the old row schema. Earlier saved JSON/table forms validate under
the old form and remain byte-identical, as do the protected historical
archives, histories and original243 state database.

Each complete case has six model decisions, six completed own actions and six
observations: annotation 1, scientific 2, launch 1, API launch 1 and results 1. The
production practical completion branch immediately sets future credit to exact
zero for launch, API launch and results, retaining final actual operational
gains 3, 3, 2. The three publication sources constitute one acquired result.
No parser, calculator, report-construction or terminal-zero observation is added.

The partial case has seven decisions/actions/observations because its results
episode explicitly selects a retained original FINISHED status after the
incomplete fetch. It does not fetch again. Results retains gains 2, 0 and no
practical completion proof. The unmodified production estimator uses declared
caller fixture parameters W=2, m=1, cost=1e6; its forecast is 1.0451797995287622 with
band [0, 3.106707212839038], and the ordinary comparison closes the episode.
That nonzero forecast is not replaced with a completion-zero forecast. The
reported job status cannot complete the missing requested result. Scientific
credit is a zero caller fixture and no annotation/scientific observation record
is fabricated. Model choices and root/scientific continuation are engineering
fixtures, not a configured-model investigation.

Each saved sheet recalculates identically with network/process operations
forbidden. A fresh Store, ToolRegistry, Workflow and service binding reopen the
same completed run with transport, native parser, calculator, publication and
model calls forbidden. All three archives, original action outcomes and full
episode/action/model/observation/admission/form histories remain identical.
The complete-zero and partial cases pass both scientific return boundaries too.

Both the operator acquisition and tests ran under the existing systemd-backed
20 GiB RAM / 4 GiB scratch policy with no wall-time cap. All generated runs,
temporary files and caches were inside each monitored cwd. `tests_002` observed
27,885,568 allocated scratch bytes. Its receipt preserves the existing scratch
monitor's possible-overshoot semantics, hard per-file bound and memory cgroup
enforcement.

`tests_001` is retained: five checks passed and one harness assertion failed.
That assertion incorrectly classified native bias and native model span as
report-only fields; the separately authorized TABLE_METRICS009 contract also
adds them to table selections. The corrected assertion checks actual report-only
geometry/accuracy/rank fields. `rfam_batch_returns.py` also changed during that
first development run; its results are not the stable source verification.
`tests_002` has no changed tracked sources and contains the final passing cases.
No production defect was exposed by this workload.

This establishes the controlled in-process shared-method_loop report path and
replay against the sources pinned in `tests_002/receipt.json`. The new report
selector was not exercised by another live remote Workflow, no configured
scientific model was run, and detached process recovery, HPC, literature and
W05 are not claimed. Root owns combined final verification and fixed-row
accounting. Original objective and all sixteen principles were reread verbatim
from the immutable attachment after native/source study and at closure,
followed by the current report contracts; context-reset receipts retain those
source identities.
