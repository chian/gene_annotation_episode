# AppService selected-input binding verification

This work implements `AppServiceInputs(execution, *, records, custody,
read_acquisition=None).bind_inputs(context, name, arguments, *, operation_key)`
in `gene_annotation_episode/bvbrc_appservice_inputs.py`. Its output is the existing
closed `BoundInputs` / `ResolvedInputs` contract. The actual consumer is
`BVBRCAppServiceService.prepare`; the root-owned host delegates with the exact
saved operation key. No operation ordering, retry policy, model episode,
scientific score, or continuation rule was added.

## Authentication and retained information

The binder authenticates the current context and exact selected action before
retaining local definition material. It consumes `records.read(reference)` and
proves current possession through `AppServiceCustody`. A results assignment
obtains its original request, resource and task from the actually received
`TaskHandoff` and its saved producing `launch_api` assignment. Matching fields
from another original job or resource do not establish a binding.

Possession of a selected receipt permits inspection of that receipt's declared
dependencies in its actual producer's authenticated context. This validates the
source bytes and extraction that the receipt attests to; it does not deliver all
producer records as extra facts to the receiving episode. Content and evidence
use the existing custody checks for real source-to-artifact edges. There is no
Store-wide search for a plausible input or output.

Explicit original Workspace paths and inline values remain assignment operands.
An original input path can be inspected by a results metadata operation without
being reclassified as that task's output or requiring unused byte custody.
Submission input evidence can follow an authenticated earlier metadata row that
still names the exact original input. Retained byte inputs require the selected
successful matching upload evidence before submission.

Workspace row pointers select exactly one `WorkspaceReceipt.rows[].pointer`.
They retain native `/result/0/N` or escaped `ls` map-key/local-ordinal spelling;
`/rows/N`, guessed ordinals and duplicate projected pointers are rejected.
Native rows are reread and checked against the existing pure reader. A UUID-only
task-info selection retains `path: null`, and unknown type, size, expiry and
metadata stay unknown. `/reported_object_uuid` is explicitly a pointer into the
named typed receipt value, not a claim that the plain UUID HTTP body is JSON.

Original output paths remain unverified task associations. Manifest selection
requires an actual host `read_acquisition` callback. The binder verifies the
acquisition's retained selected operands, task, artifact and original object,
then passes authenticated retained bytes to `decode_job_result` and selects the
exact output ordinal. A valid member of a partial manifest remains usable;
malformed members, wrong task/application and invented ordinals are rejected.
Manifest membership leaves producer-byte version unknown.

Selected packaged definitions retain the actual source bytes and existing C3
envelope. Supplied and enumerated definitions retain the exact authenticated
source/pointer/index relationship and a local extraction. The action-local
`definition_inputs.json` stores `definition`, `definition_envelope`,
`original_evidence`, `retained_source`, and actual new `source_refs`. The host
publishes those refs with the completed selected preparation so subsequent
declared dependency checks can succeed. These local records are part of that
selected action, not new observations. No original parameters or defaults are
rewritten.

## Capability identity agreement

The binder supplies only authenticated path/UUID evidence to the root-owned
passive journal port:

```python
execution.selected_effects.resolve_object_identity(
    original_job_owner, resource_id, *, path, uuid, evidence_refs
) -> str
```

The journal retains proven aliases under the original owner and resource,
preserves earlier immutable effect descriptors, and checks aliases when reserving
and issuing effects. Observing a UUID after an earlier path-only capability
therefore cannot silently create another generation-zero slot. This was agreed
with root before implementation, and the real journal regression passes.

A generation predecessor must be a possessed actual CapabilityReceipt or
CommonReceipt whose declared effect refs resolve to the exact original
owner/resource/object and preceding generation. The actual unknown failure
receipt can establish a predecessor after a lost response. A bare effect ID does
not establish possession and is rejected. No receipt-name-to-effect inference or
metadata request is performed. A supplied capability URL is read from exact
original source evidence and compared with the selected original task/object
association. No URL or expiry is invented.

## Eleven operation branches

| Selected operation | Authenticated resolved operands |
| --- | --- |
| `enumerate_apps` | No inferred input; exact empty resolved branch. |
| `prepare` | Exact original inputs and selected retained C3 definition envelope. |
| `workspace_metadata` | Exact original or received object selection, native reference and optional actual metadata. |
| `workspace_create` | Only selected original data bindings; original target operands remain unchanged. |
| `upload` | Selected native create row, original retained bytes, actual Shock URL/node and original input target. |
| `submit` | Successful original preparation, retained definition bytes, exact native operands and selected input evidence. |
| `status` | Original possessed handoff and exact original task. |
| `task_info` | Original possessed handoff and exact task; selected filename remains unchanged. |
| `list_outputs` | Exact selected native references and original task associations. |
| `download_capability` | Exact object order, authenticated physical identities and selected predecessor effects. |
| `download` | Exact selected object, acquired/supplied capability evidence and original task. |

## Verification boundary

The tests compose real `Store` artifacts and records, saved runtime selected
actions and commissions, typed returns, `AppServiceCustody`, `AppServiceRecords`,
`SelectedAPIEffects`, `perform_selected_call`, `BVBRCAppServiceService`, and the
receipt builder. Native client responses are deliberately synthetic, retained
as actual test artifacts. Network entry points are forbidden by the test
fixture. The driver has a test-only exact target adapter and an explicitly
test-only authenticated acquisition callback. This establishes component
composition with actual local records, not full `method_loop`, production
acquisition publication, live BV-BRC access, or scientific result integration.

The create/upload/submit case exposed a real SQLite thread-affinity problem in
the root-owned invocation path. Root corrected the selected-call helper to read
only the exact selected artifact on the Store-owning thread and supply immutable
bytes to worker-thread invocation. The service rechecks digest and length.
`pytest-upload-001.txt` records the subsequent passing real Store regression.

Meaningful cases include all eleven operation branches; packaged, supplied and
enumerated definition extraction; changed or omitted selected action; omitted
upload evidence; foreign job, resource and unreceived sibling sources; exact
native and escaped row pointers; duplicate rows; missing definition bytes;
UUID-only task-info operands; null metadata; input metadata without an output
claim; conflicting output task metadata; path/UUID generation identity; actual
unknown capability predecessors; missing acquisition callback; manifest partial
members and wrong task/application; and exact original link/capability evidence.

Test logs are retained additively, including early failures and interrupted
development runs. They are not all runs of the final source. Observed results:

| Log | Observed result and scope |
| --- | --- |
| `pytest-fix-002.txt` | 14 passed, 1 deselected; upload excluded while its root-owned thread issue was unresolved. |
| `pytest-new-001.txt` | 6 passed, 15 deselected; manifest, supplied capability, duplicate row, task metadata and supplied link cases. |
| `pytest-upload-001.txt` | 1 passed, 20 deselected; actual Store upload repair regression. |
| `pytest-all-001.txt` | 24 passed in 146.47 seconds; intermediate full input suite. |
| `pytest-unknown-001.txt` | 1 passed, 24 deselected; actual unknown effect predecessor. |
| `pytest-final.txt` | 25 passed in 223.55 seconds; earlier full suite. |
| `pytest-final-002.txt` | 26 passed in 367.11 seconds; full suite including results metadata without an output claim. |
| `pytest-lineage.txt` | 1 passed, 26 deselected in 16.72 seconds; final metadata-lineage change. |

The separate `pytest-final-002.txt` run includes the 26 cases collected before
the last metadata-lineage regression was added. The final focused run exercises
that last source change. The current module contains 27 collected cases; this
report does not combine separate runs into a claim of one full 27-case run.

## Remaining integration and authority

The production host's acquisition publication and reader remain explicitly
unbound at inspection. A missing binder callback raises
`appservice_acquisition_reader_unbound` with the existing closed Failure
projection; configured callback failures propagate their exact code. Test
callbacks do not supply production capabilities. Root owns full host assembly,
result publication, episode integration and their verification. None of this
report claims live execution, native scientific measurements, completed tool
graders, or completed original objective.

`INSPECTION.json` distinguishes complete-file study from complete relevant
function/path study. `SOURCE_HASHES.json` records exact inspected source bytes
at capture time, including the immutable objective and final owned sources;
other workers may subsequently change their owned dependencies. After the last
production edit, the objective and all sixteen design principles were reread
verbatim from the immutable attachment, followed by the exact host-parts and
accepted service-input contracts. The original execution proposal was also
read completely. No authority, checklist, historical evidence, prompt, model
call, W05 scoring, literature work, live service, network or HPC work was changed
or performed by this input-binding implementation.
