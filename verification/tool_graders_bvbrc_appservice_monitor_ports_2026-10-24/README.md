# AppService monitor ports verification

This workload implements explicit native-selection forwarding in the existing
monitor. It owns `execution_progress.py`, `episode_monitoring.py`,
`episode_services.py`, `episode_bindings.py`, the new monitor-ports test, and this
verification directory. It does not implement the AppService API observation
transport, host custody, result publication, factories, prompts, grading,
credit formulas, or a new episode/workflow.

The immutable attachment was read in full. Its objective and all sixteen design
principles were reread verbatim after substantial study and before handoff,
followed by the exact monitor/producer-consumer and resolved-input contracts.
The applicable AGENTS instructions and required design documents were read.
The full owned modules and affected observation, status, log, receipt, credit,
result-consumer and native service functions were inspected.

## Implemented boundary

`MonitorEpisodes.execute` passes the selected `query_tasks`, `stdout`, or
`stderr` through `WorkflowServices.observe_progress`, `ProgressProvider.observe`,
`ExecutionProgressProvider.observe`, and `ExecutionTargetReader.observe_target`
to the API reader. The optional keyword names are `native_operation` and
`observation_context`. The latter is the original immutable `BindingContext`.
The unchanged operation key is `run_id:episode_id:decision_index`; no suffix,
substituted action, inferred native operation, or additional observation is
created here. The API owner must authenticate the actual current selected
`progress.observe` and original monitor assignment/parent handoff possession.
The forwarding helper does not provide that authentication by itself.

Only the versioned AppService target advertises the closed
`selected_observation_schema`. Its request and resource version markers are
checked. The descriptor uses the API owner's authenticated handoff projection,
including `task_handoff.original_task` and `task_handoff.definition_evidence`,
instead of interpreting the new stored receipt as the old generic envelope.
It records actual submitted parameters, application identities, source-native
states and timing representation, available methods, log representation and
reader signatures. Support methods have no scientific-result fact sources.
Download publication requires an explicitly bound scientific adapter; configured
adapter names do not establish that integration. A missing AppService binding
cannot fall through to the old HMMER description.

Both durable provider selections add the native operation and
`observation_context.as_record()` only when explicitly supplied. Omission keeps
the exact old selection payload and hash expression, and forwards neither new
keyword to an old concrete reader. The existing executable implementation hash
still participates in the provider signature. No saved code pin or observation
is migrated or rewritten.

For new AppService targets, complete captures are retained before projection.
Returned `execution_status.native.logs` is always `[]`; requested log windows
carry retained artifact references separately. Unrequested stdout/stderr output
metadata and unrequested measured intervals are removed from that status
projection. Log-only state stays `unknown`, its lifecycle stays null, and the
explicit no-state-observed reason is preserved. Native metadata supplied by the
API owner must itself exclude raw task-info text/base64. UTF-8 log reads use
retained bytes; invalid UTF-8 returns `source_not_utf8_text` while preserving the
original bytes. No status or log transport is invoked by `progress.log`.

## Actual checks

| Check | Actual result | Evidence |
| --- | --- | --- |
| New ports suite after UTF-8 fixture correction | 26 passed in 121.78 s | `pytest_ports_final.txt`, `pytest_ports_final.xml` |
| Final missing-service descriptor guard plus affected forwarding/old-target cases | 7 passed, 20 deselected in 15.73 s | `pytest_descriptor_binding.txt`, `pytest_descriptor_binding.xml` |
| Unchanged BLAST, MinHash, API recovery and integration files | 97 passed in 443.72 s | `pytest_api_regression.txt` |
| Unchanged recursive/native/homology progress and receipt-order files | 79 passed, 1 failed in 391.00 s | `pytest_monitor_regression.txt`, `pytest_monitor_regression.xml` |

The first two rows overlap: they cover 27 distinct new test cases, not 33.
The final guard was added after the complete 26-case run and received the seven
targeted checks. The original `pytest_ports.txt`/XML retain an initial run's
24 passes and incorrect expectation that invalid UTF-8 was a completed text
read; that test expectation was corrected without changing `source.read`.

The historical recursive test's selected monitor actions and child returns
complete. Its final scripted root `episode.history` action is absent from the
current decision-exchange schema, produces `action_contract/schema_validation`
feedback, and exhausts its script. The actual action/schema evidence is retained
in `recursive_regression_failure.json`. Neither runtime nor the historical test
was changed. The complete regression group therefore remains failing, not a
claimed passing suite.

The new tests use a strict synthetic final API reader with real Store, monitor,
provider, descriptor and local retained-log code. They verify exact forwarding,
required/invalid selections, old keyword omission and signatures, changed-key
payload conflicts, replay before native access, recovery after later projection
failure, unknown log state, no raw-log projection leak, and authenticated-reader
handoff/dependency ports. They do not establish the real AppService host's
ancestor custody or one-RPC/one-GET transport guarantee. Existing regressions
also use controlled local HTTP responses and tiny local process/PBS fixtures;
the homology regression includes one tiny real local phmmer execution. No live
BV-BRC call, live HPC deployment, model call, or complete AppService episode path
was executed by this workload.
